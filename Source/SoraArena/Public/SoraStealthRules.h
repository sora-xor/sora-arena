#pragma once

// Offline opponent awareness rules shared by ASoraEnemyController and a
// host-compiled acceptance driver. Distances are integer centimetres, view
// angles are cosines in thousandths, light is a permille proxy and time is
// integer milliseconds, so what an opponent notices never depends on a dice
// roll or on a floating-point frame boundary.
namespace SoraStealthRules
{
// Unaware: on its patrol or at its post. Suspicious: turns toward something it
// half noticed, then walks over to look. Alert: knows the hero is near and goes
// to the last place he was seen or heard. Search: checks around that place.
// Combat: sees the hero and fights. Retreat: badly hurt, falls back to cover once.
enum class EState { Unaware, Suspicious, Alert, Search, Combat, Retreat };
// Footsteps and sprinting are heard for as long as they last; the others are
// single events. A call-out is an ally shouting where the hero is.
enum class ENoise { Footstep, Sprint, Melee, Shot, Explosion, Callout };
// Blades close in with footwork; cover shooters hold a box and peek to fire;
// flankers circle to the hero's side before taking cover.
enum class ERole { Blade, CoverShooter, Flanker };

// Awareness is kept in thousandths of a permille so slow, distant detection
// still accumulates at a 60 Hz step. Permille values are the public scale.
constexpr int AwarenessScale = 1000;
constexpr int AwarenessMax = 1000 * AwarenessScale;
constexpr int SuspiciousAt = 250 * AwarenessScale;
constexpr int DecayPermillePerSecond = 160;

constexpr int SightRangeCm = 2800;
constexpr int CloseSightCm = 600;
// cos 35 degrees: the focus of attention; cos 70 degrees: the edge of a
// 140-degree view. Nothing behind that edge is seen at all.
constexpr int FocusConeMilli = 819;
constexpr int ViewConeMilli = 342;
// A silhouette in darkness is still noticed, only slowly.
constexpr int DarkFloorPermille = 200;

constexpr int LookMs = 900;
constexpr int CombatMemoryMs = 1500;
constexpr int SearchMs = 12000;
constexpr int RetreatHealthPermille = 350;
constexpr int RetreatMinMs = 1500;
constexpr int RetreatMaxMs = 5000;
// A hunting wave's relay repeats the hero's position this often while the
// hunter cannot see him.
constexpr int IntelMs = 1500;

constexpr int Clamp(int Value, int Low, int High)
{
    return Value < Low ? Low : Value > High ? High : Value;
}

struct FSight
{
    int DistanceCm;
    // Cosine between the observer's facing and the direction to the target, x1000.
    int FacingMilli;
    // Nothing blocks a line from the observer's eye to the target's head or chest.
    bool Clear;
    // 0 darkness to 1000 daylight where the target stands.
    int LightPermille;
    bool TargetMoving;
};

constexpr bool InView(FSight Sight)
{
    return Sight.Clear && Sight.DistanceCm >= 0 && Sight.DistanceCm <= SightRangeCm &&
        Sight.FacingMilli >= ViewConeMilli;
}

// Awareness permille per second of unbroken view: fastest close and in the
// focus cone, slower with distance, in the dark and at the edge of view, and
// faster when the target moves.
constexpr int SightGainPerSecond(FSight Sight)
{
    if (!InView(Sight))
        return 0;
    const int Range = Sight.DistanceCm <= CloseSightCm ? 4000 :
        4000 - (Sight.DistanceCm - CloseSightCm) * 3700 / (SightRangeCm - CloseSightCm);
    const int Light = DarkFloorPermille + (1000 - DarkFloorPermille) * Clamp(Sight.LightPermille, 0, 1000) / 1000;
    const int Cone = Sight.FacingMilli >= FocusConeMilli ? 3 : 1;
    const int Motion = Sight.TargetMoving ? 3 : 2;
    return Range * Light / 1000 * Cone / 3 * Motion / 2;
}

// The light proxy: the key light's share of daylight from its illuminance in
// tenths of a lux, plus each lamp whose attenuation radius reaches the target.
constexpr int AmbientPermille(int KeyLightDeciLux)
{
    return Clamp(KeyLightDeciLux * 4, 40, 1000);
}

constexpr int LampPermille(int DistanceCm, int RadiusCm)
{
    if (RadiusCm <= 0 || DistanceCm < 0 || DistanceCm >= RadiusCm)
        return 0;
    const int Near = RadiusCm - DistanceCm;
    return 700 * Near / RadiusCm * Near / RadiusCm;
}

constexpr int LightPermille(int Ambient, int Lamps)
{
    return Clamp(Ambient + Lamps, 0, 1000);
}

constexpr int NoiseRadiusCm(ENoise Noise)
{
    switch (Noise)
    {
    case ENoise::Footstep: return 450;
    case ENoise::Sprint: return 1100;
    case ENoise::Melee: return 900;
    case ENoise::Shot: return 3500;
    case ENoise::Explosion: return 5000;
    case ENoise::Callout: return 1800;
    }
    return 0;
}

constexpr int NoisePeakPermille(ENoise Noise)
{
    switch (Noise)
    {
    case ENoise::Footstep: return 320;
    case ENoise::Sprint: return 500;
    case ENoise::Melee: return 650;
    case ENoise::Shot:
    case ENoise::Explosion:
    case ENoise::Callout: return 1000;
    }
    return 0;
}

constexpr bool IsContinuous(ENoise Noise)
{
    return Noise == ENoise::Footstep || Noise == ENoise::Sprint;
}

// Awareness permille a noise adds (per second for a continuous one): its peak
// within half its radius, falling to two fifths of the peak at the edge. A
// blocked path between the noise and the listener halves the radius.
constexpr int HeardPermille(ENoise Noise, int DistanceCm, bool Occluded)
{
    const int Radius = Occluded ? NoiseRadiusCm(Noise) / 2 : NoiseRadiusCm(Noise);
    if (Radius <= 0 || DistanceCm < 0 || DistanceCm > Radius)
        return 0;
    const int Peak = NoisePeakPermille(Noise);
    const int Half = Radius / 2;
    return DistanceCm <= Half ? Peak : Peak - (Peak - Peak * 2 / 5) * (DistanceCm - Half) / (Radius - Half);
}

struct FMind
{
    EState State;
    // AwarenessScale units. Unaware and Suspicious: the detection meter.
    // Search: fresh evidence gathered since the search began. Otherwise full.
    int Awareness;
    int StateMs;
    // Combat only: time since the target was last in view.
    int UnseenMs;
    // A retreat is taken once per life.
    bool Retreated;
};

struct FSenses
{
    // SightGainPerSecond this step; zero when the target is not in view.
    int SightGain;
    // Continuous noise, permille per second, and single noises, permille.
    int NoisePerSecond;
    int NoiseImpulse;
    int HealthPermille;
    // The state's move goal is reached or cannot be reached: the place being
    // investigated, the last known place, or the retreat cover.
    bool Reached;
    bool CanRetreat;
};

constexpr FMind Calm()
{
    return {EState::Unaware, 0, 0, 0, false};
}

constexpr FMind Hunting()
{
    return {EState::Alert, AwarenessMax, 0, 0, false};
}

constexpr FMind Enter(FMind Mind, EState State, int Awareness)
{
    Mind.State = State;
    Mind.Awareness = Awareness;
    Mind.StateMs = 0;
    Mind.UnseenMs = 0;
    return Mind;
}

// One step of DtMs milliseconds.
constexpr FMind Step(FMind Mind, FSenses Senses, int DtMs)
{
    const bool Sees = Senses.SightGain > 0;
    const int Gain = (Senses.SightGain + Senses.NoisePerSecond) * DtMs + Senses.NoiseImpulse * AwarenessScale;
    Mind.StateMs += DtMs;
    switch (Mind.State)
    {
    case EState::Unaware:
    case EState::Suspicious:
    {
        // A suspicious opponent keeps its interest until it has looked where it went.
        const bool Decays = Gain <= 0 && (Mind.State == EState::Unaware || Senses.Reached);
        Mind.Awareness = Clamp(Mind.Awareness + (Decays ? -DecayPermillePerSecond * DtMs : Gain), 0, AwarenessMax);
        if (Mind.Awareness >= AwarenessMax)
            return Enter(Mind, Sees ? EState::Combat : EState::Alert, AwarenessMax);
        if (Mind.State == EState::Unaware && Mind.Awareness >= SuspiciousAt)
            return Enter(Mind, EState::Suspicious, Mind.Awareness);
        if (Mind.State == EState::Suspicious && Mind.Awareness <= 0)
            return Enter(Mind, EState::Unaware, 0);
        return Mind;
    }
    case EState::Alert:
        if (Sees)
            return Enter(Mind, EState::Combat, AwarenessMax);
        if (Senses.Reached)
            return Enter(Mind, EState::Search, 0);
        return Mind;
    case EState::Combat:
        Mind.UnseenMs = Sees ? 0 : Mind.UnseenMs + DtMs;
        if (Senses.CanRetreat && !Mind.Retreated && Senses.HealthPermille > 0 &&
            Senses.HealthPermille <= RetreatHealthPermille)
        {
            Mind = Enter(Mind, EState::Retreat, AwarenessMax);
            Mind.Retreated = true;
            return Mind;
        }
        if (Mind.UnseenMs >= CombatMemoryMs)
            return Enter(Mind, EState::Alert, AwarenessMax);
        return Mind;
    case EState::Search:
        if (Sees)
            return Enter(Mind, EState::Combat, AwarenessMax);
        Mind.Awareness = Clamp(Mind.Awareness + Gain, 0, AwarenessMax);
        if (Mind.Awareness >= SuspiciousAt)
            return Enter(Mind, EState::Alert, AwarenessMax);
        if (Mind.StateMs >= SearchMs)
            return Enter(Mind, EState::Unaware, 0);
        return Mind;
    case EState::Retreat:
        if ((Senses.Reached && Mind.StateMs >= RetreatMinMs) || Mind.StateMs >= RetreatMaxMs)
            return Enter(Mind, Sees ? EState::Combat : EState::Alert, AwarenessMax);
        return Mind;
    }
    return Mind;
}

// Slots 1, 4, 7... flank; every other ranged slot takes cover.
constexpr ERole Role(int Slot, bool Blade)
{
    return Blade ? ERole::Blade : Slot % 3 == 1 ? ERole::Flanker : ERole::CoverShooter;
}

constexpr bool CanRetreat(ERole Role)
{
    return Role != ERole::Blade;
}

// A flanker circles to this side of the hero, relative to its squad.
constexpr int FlankSide(int Slot)
{
    return Slot / 3 % 2 == 0 ? 1 : -1;
}

constexpr int FlankDistanceCm = 800;

// A ranged opponent that has just seen the hero holds its ground and fires for
// this long before it moves to cover or a flank.
constexpr int ReactionMs(int Slot)
{
    return 1200 + Slot % 3 * 200;
}

// At cover a shooter stays hidden, then steps out past the box's edge to fire.
// The phase is offset by slot so a group does not peek in unison.
constexpr int PeekCycleMs = 3400;
constexpr int PeekHiddenMs = 1900;

constexpr bool Peeking(int NowMs, int Slot)
{
    return (NowMs + Slot * 700) % PeekCycleMs >= PeekHiddenMs;
}

// Preference for a cover spot, lower first; negative rejects it. Fighting
// cover is near the shooter and near nine metres from the hero; retreat cover
// is near the shooter and at least twelve metres from the hero.
constexpr int CoverScore(int TravelCm, int TargetCm)
{
    if (TravelCm < 0 || TargetCm < 450 || TargetCm > 2000)
        return -1;
    return TravelCm + (TargetCm > 900 ? TargetCm - 900 : 900 - TargetCm) / 2;
}

constexpr int RetreatScore(int TravelCm, int TargetCm)
{
    return TravelCm < 0 || TargetCm < 1200 ? -1 : TravelCm;
}
} // namespace SoraStealthRules
