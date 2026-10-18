#pragma once

// Offline opponent awareness rules shared by ASoraEnemyController, the stealth
// zone (USoraStealth) and a host-compiled acceptance driver, with the combat
// roles and the stuck clock the same brain walks by. Distances are
// integer centimetres, view angles are cosines in thousandths, light is a
// permille proxy and time is integer milliseconds, so what an opponent notices
// never depends on a dice roll or on a floating-point frame boundary.
namespace SoraStealthRules
{
// Unaware: on its patrol or at its post. Suspicious: turns toward something it
// half noticed, then walks over to look. Alert: knows the hero is near and goes
// to the last place he was seen or heard. Search: checks around that place.
// Combat: sees the hero and fights. Retreat: badly hurt, falls back to cover once.
enum class EState { Unaware, Suspicious, Alert, Search, Combat, Retreat };
// Footsteps (walking, sprinting or crouch-walking) are heard for as long as
// they last; the others are single events. A call-out is an ally shouting
// where the hero is; a takedown is the scuffle of one guard going down; a
// lure is a thrown stone landing or a float line ringing, which sends a guard
// to look but never tells it the hero is there (SoraFieldcraftRules::LureImpulsePermille);
// a landing is the thud of a drop off a roof.
enum class ENoise { Footstep, Sprint, Melee, Shot, Explosion, Callout, CrouchStep, Takedown, Lure, Landing };
// Blades close in with footwork; cover shooters hold a box and peek to fire;
// flankers circle to the hero's side before taking cover.
enum class ERole { Blade, CoverShooter, Flanker };
// The hero crouching lowers his outline and softens his steps.
enum class EStance { Standing, Crouched };
// The campaign difficulty as stealth sees it (Easy is the Story setting).
enum class EDifficulty { Easy, Normal, Hard };

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
// A crouched figure shows a little over half the outline of a standing one.
constexpr int CrouchedOutlinePermille = 550;

constexpr int LookMs = 900;
constexpr int CombatMemoryMs = 1500;
constexpr int SearchMs = 12000;
constexpr int RetreatHealthPermille = 350;
constexpr int RetreatMinMs = 1500;
constexpr int RetreatMaxMs = 5000;
// A hunting wave's relay repeats the hero's position this often while the
// hunter cannot see him.
constexpr int IntelMs = 1500;
// A guard that has searched once, or heard an alarm, or found a body, stays
// wary for the rest of its beat: evidence fills its meter this much faster.
constexpr int WaryPermille = 1200;

constexpr int Clamp(int Value, int Low, int High)
{
    return Value < Low ? Low : Value > High ? High : Value;
}

struct FSight
{
    int DistanceCm;
    // Cosine between the observer's facing and the direction to the target, x1000.
    int FacingMilli;
    // How much of the target's head, chest and hips a line from the eye
    // reaches, x1000: zero is hidden (a crouch behind low cover), 1000 is in
    // the open. See ExposurePermille.
    int ExposurePermille;
    // 0 darkness to 1000 daylight where the target stands.
    int LightPermille;
    bool TargetMoving;
    bool Crouched = false;
    // What the target carries: a lit candle 2000, a cupped one 1200, nothing 1000.
    int VisibilityPermille = 1000;
};

// The share of a body's sample points (head, chest, hips) with a clear line.
constexpr int ExposurePermille(int Visible, int Samples)
{
    return Samples <= 0 ? 0 : Clamp(Visible, 0, Samples) * 1000 / Samples;
}

// What one kind of opponent perceives (Content/Data/enemies.json). Standard()
// is the enforcers' reference and the values the constants above name.
struct FPerception
{
    int SightRangeCm;
    // A target in darkness is seen only this far; light between darkness and
    // daylight scales between the two ranges.
    int DarkSightRangeCm;
    int ViewConeMilli;
    int FocusConeMilli;
    // How far a sprint is heard; every noise's reach scales with it.
    int HearingCm;
    // Reluctant opponents notice everything more slowly.
    int SuspicionPermille;
    // An alarmist reports whatever it half-notices: it skips suspicion.
    bool Alarmist;
};

// A sprint's reach (NoiseRadiusCm(ENoise::Sprint)) for a standard listener.
constexpr int StandardHearingCm = 1100;

constexpr FPerception Standard()
{
    return {SightRangeCm, SightRangeCm, ViewConeMilli, FocusConeMilli, StandardHearingCm, 1000, false};
}

constexpr int SightRangeAt(FPerception Perception, int LightPermille)
{
    const int Dark = Clamp(Perception.DarkSightRangeCm, 0, Perception.SightRangeCm);
    return Dark + (Perception.SightRangeCm - Dark) * Clamp(LightPermille, 0, 1000) / 1000;
}

constexpr bool InView(FSight Sight, FPerception Perception = Standard())
{
    return Sight.ExposurePermille > 0 && Sight.DistanceCm >= 0 &&
        Sight.DistanceCm <= SightRangeAt(Perception, Sight.LightPermille) && Sight.FacingMilli >= Perception.ViewConeMilli;
}

// Awareness permille per second of unbroken view: fastest close and in the
// focus cone, slower with distance, in the dark and at the edge of view, and
// faster when the target moves. Only the part of the body a line reaches
// counts, a crouched outline is smaller, and a carried light gives the
// target away.
constexpr int SightGainPerSecond(FSight Sight, FPerception Perception = Standard())
{
    if (!InView(Sight, Perception))
        return 0;
    const int Reach = SightRangeAt(Perception, Sight.LightPermille);
    const int Range = Sight.DistanceCm <= CloseSightCm || Reach <= CloseSightCm ? 4000 :
        4000 - (Sight.DistanceCm - CloseSightCm) * 3700 / (Reach - CloseSightCm);
    const int Light = DarkFloorPermille + (1000 - DarkFloorPermille) * Clamp(Sight.LightPermille, 0, 1000) / 1000;
    const int Cone = Sight.FacingMilli >= Perception.FocusConeMilli ? 3 : 1;
    const int Motion = Sight.TargetMoving ? 3 : 2;
    const int Outline = Sight.Crouched ? CrouchedOutlinePermille : 1000;
    return Range * Light / 1000 * Cone / 3 * Motion / 2 * Perception.SuspicionPermille / 1000 *
        Clamp(Sight.ExposurePermille, 0, 1000) / 1000 * Outline / 1000 * Clamp(Sight.VisibilityPermille, 0, 4000) / 1000;
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

// The chapters' player noise (ch06: sprint 1500, walk 600, crouch-walk 250,
// takedown 300) scaled to the standard listener's 1100 cm reference.
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
    case ENoise::CrouchStep: return 180;
    case ENoise::Takedown: return 220;
    // ch06: a tsubute's impact and the moat's float line, 1,400.
    case ENoise::Lure: return 1400;
    // ch03.b03: the drop off the board roof, 900.
    case ENoise::Landing: return 900;
    }
    return 0;
}

constexpr int NoisePeakPermille(ENoise Noise)
{
    switch (Noise)
    {
    case ENoise::Footstep: return 320;
    case ENoise::Sprint: return 500;
    case ENoise::Melee:
    case ENoise::Takedown: return 650;
    case ENoise::Shot:
    case ENoise::Explosion:
    case ENoise::Callout: return 1000;
    case ENoise::CrouchStep: return 200;
    case ENoise::Lure: return 600;
    case ENoise::Landing: return 650;
    }
    return 0;
}

constexpr bool IsContinuous(ENoise Noise)
{
    return Noise == ENoise::Footstep || Noise == ENoise::Sprint || Noise == ENoise::CrouchStep;
}

// The steps the hero makes at his pace and stance; a sprint stands him up.
constexpr ENoise Steps(bool Sprinting, EStance Stance)
{
    return Sprinting ? ENoise::Sprint : Stance == EStance::Crouched ? ENoise::CrouchStep : ENoise::Footstep;
}

// A floor's effect on footsteps, x1000 (a chapter's noise_surfaces): puddles
// and gravel 1500, tatami and running water 500. A nightingale floor sings
// under any step (walk 3000, crouch-walk 3600) except along its edge strip,
// which is silent to a crouch-walk (0).
struct FSurface
{
    int StepPermille;
    int CrouchPermille;
};

constexpr FSurface Plain()
{
    return {1000, 1000};
}

constexpr int StepLoudnessPermille(ENoise Steps, FSurface Surface)
{
    return Clamp(Steps == ENoise::CrouchStep ? Surface.CrouchPermille : Surface.StepPermille, 0, 10000);
}

// How far this listener hears a noise made at Loudness (x1000).
constexpr int HeardRadiusCm(ENoise Noise, FPerception Perception = Standard(), int LoudnessPermille = 1000)
{
    return NoiseRadiusCm(Noise) * Clamp(LoudnessPermille, 0, 10000) / 1000 * Clamp(Perception.HearingCm, 0, 100000) /
        StandardHearingCm;
}

// Awareness permille a noise adds (per second for a continuous one): its peak
// within half its radius, falling to two fifths of the peak at the edge. A
// blocked path between the noise and the listener halves the radius.
constexpr int HeardPermille(ENoise Noise, int DistanceCm, bool Occluded, FPerception Perception = Standard(),
    int LoudnessPermille = 1000)
{
    const int Full = HeardRadiusCm(Noise, Perception, LoudnessPermille);
    const int Radius = Occluded ? Full / 2 : Full;
    if (Radius <= 0 || DistanceCm < 0 || DistanceCm > Radius)
        return 0;
    const int Peak = NoisePeakPermille(Noise);
    const int Half = Radius / 2;
    const int Level = DistanceCm <= Half ? Peak : Peak - (Peak - Peak * 2 / 5) * (DistanceCm - Half) / (Radius - Half);
    return Level * Perception.SuspicionPermille / 1000;
}

// A stealth zone's detection block (story bible §12.2 `detection`) as the
// guards apply it. Outside a zone, and for a hunting wave, Watchful() holds.
struct FVigilance
{
    // How fast sight and continuous noise fill the meter, x1000 (suspicion_rate).
    int RatePermille;
    // Awareness (AwarenessScale units) at which an unaware guard becomes
    // suspicious, and fresh evidence sends a searching one back on the hunt
    // (suspicious_at). Alert is always the full meter (alert_threshold 1.0).
    int SuspicionThreshold;
    // How long a search lasts after contact is lost (search_s).
    int SearchDurationMs;
    // A wary guard's rate multiplier, x1000 (wary_after_search).
    int WaryRatePermille;
};

constexpr FVigilance Watchful()
{
    return {1000, SuspiciousAt, SearchMs, WaryPermille};
}

// A zone's block from its data: suspicion_rate and suspicious_at in
// thousandths, search_s in milliseconds.
constexpr FVigilance Detection(int RatePermille, int SuspiciousAtPermille, int SearchDurationMs, int WaryRatePermille = WaryPermille)
{
    return {Clamp(RatePermille, 100, 4000), Clamp(SuspiciousAtPermille, 50, 950) * AwarenessScale,
        Clamp(SearchDurationMs, 1000, 120000), Clamp(WaryRatePermille, 1000, 4000)};
}

// The difficulty's scaling (ch06 stealth_defaults.difficulty): Easy notices at
// 0.7 of the rate and searches 0.8 as long; Hard 1.25 and 1.2.
constexpr FVigilance OnDifficulty(FVigilance Zone, EDifficulty Difficulty)
{
    if (Difficulty == EDifficulty::Easy)
        return {Zone.RatePermille * 700 / 1000, Zone.SuspicionThreshold, Zone.SearchDurationMs * 800 / 1000, Zone.WaryRatePermille};
    if (Difficulty == EDifficulty::Hard)
        return {Zone.RatePermille * 1250 / 1000, Zone.SuspicionThreshold, Zone.SearchDurationMs * 1200 / 1000, Zone.WaryRatePermille};
    return Zone;
}

struct FMind
{
    EState State;
    // AwarenessScale units. Unaware and Suspicious: the detection meter.
    // Search: fresh evidence gathered since the search began, which fades
    // when nothing new comes. Otherwise full.
    int Awareness;
    int StateMs;
    // Combat only: time since the target was last in view.
    int UnseenMs;
    // A retreat is taken once per life.
    bool Retreated;
    // Wary for the rest of the beat (WaryPermille).
    bool Wary;
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
    // FPerception::Alarmist.
    bool Alarmist;
};

constexpr FMind Calm()
{
    return {EState::Unaware, 0, 0, 0, false, false};
}

constexpr FMind Hunting()
{
    return {EState::Alert, AwarenessMax, 0, 0, false, false};
}

constexpr FMind Enter(FMind Mind, EState State, int Awareness)
{
    Mind.State = State;
    Mind.Awareness = Awareness;
    Mind.StateMs = 0;
    Mind.UnseenMs = 0;
    return Mind;
}

// A guard's first state in a zone. When the hero was detected in the zone
// before (x_on_detected_carryover) it starts suspicious and wary.
constexpr FMind Posted(bool CarriedOver)
{
    if (!CarriedOver)
        return Calm();
    FMind Mind = Enter(Calm(), EState::Suspicious, SuspiciousAt);
    Mind.Wary = true;
    return Mind;
}

constexpr int RatePermille(const FMind& Mind, FVigilance Vigilance)
{
    return Vigilance.RatePermille * (Mind.Wary ? Vigilance.WaryRatePermille : 1000) / 1000;
}

// One step of DtMs milliseconds.
constexpr FMind Step(FMind Mind, FSenses Senses, int DtMs, FVigilance Vigilance = Watchful())
{
    const bool Sees = Senses.SightGain > 0;
    const int Gain = (Senses.SightGain + Senses.NoisePerSecond) * RatePermille(Mind, Vigilance) / 1000 * DtMs +
        Senses.NoiseImpulse * AwarenessScale;
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
        if (Mind.State == EState::Unaware && Mind.Awareness >= Vigilance.SuspicionThreshold)
            return Senses.Alarmist ? Enter(Mind, EState::Alert, AwarenessMax) : Enter(Mind, EState::Suspicious, Mind.Awareness);
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
        // Faint evidence that stops coming fades, so scattered noises over a
        // long search do not add up to a hunt.
        Mind.Awareness = Clamp(Mind.Awareness + (Gain > 0 ? Gain : -DecayPermillePerSecond * DtMs), 0, AwarenessMax);
        if (Mind.Awareness >= Vigilance.SuspicionThreshold)
            return Enter(Mind, EState::Alert, AwarenessMax);
        if (Mind.StateMs >= Vigilance.SearchDurationMs)
        {
            Mind = Enter(Mind, EState::Unaware, 0);
            Mind.Wary = true;
            return Mind;
        }
        return Mind;
    case EState::Retreat:
        if ((Senses.Reached && Mind.StateMs >= RetreatMinMs) || Mind.StateMs >= RetreatMaxMs)
            return Enter(Mind, Sees ? EState::Combat : EState::Alert, AwarenessMax);
        return Mind;
    }
    return Mind;
}

// Detection: a guard that was calm (unaware, suspicious or searching) now
// knows where the hero is. A search set off by a found body is not detection.
constexpr bool IsCalm(EState State)
{
    return State == EState::Unaware || State == EState::Suspicious || State == EState::Search;
}

constexpr bool Detects(EState Previous, EState Next)
{
    return IsCalm(Previous) && (Next == EState::Alert || Next == EState::Combat);
}

// A zone's alarm (a lectern reached, a bell rung) reaches every guard in it:
// calm guards go to where the alarm says the hero is, and all stay wary.
constexpr FMind Alarmed(FMind Mind)
{
    Mind.Wary = true;
    return IsCalm(Mind.State) ? Enter(Mind, EState::Alert, AwarenessMax) : Mind;
}

// A body found anywhere in a zone sends every unaware or suspicious guard to
// search (the finder around the body, the others where they stand); all stay
// wary for the rest of the beat. A guard already searching or hunting goes on.
constexpr FMind BodyFound(FMind Mind)
{
    Mind.Wary = true;
    return Mind.State == EState::Unaware || Mind.State == EState::Suspicious ? Enter(Mind, EState::Search, 0) : Mind;
}

// A calm guard gathers evidence of a body in view as it would of a still,
// crouched figure (SightGainPerSecond at its rate); a body lost from view
// starts over. It has found the body once the evidence reaches suspicion.
constexpr int BodyEvidence(int Evidence, int GainPerSecond, int RatePermille, int DtMs)
{
    return GainPerSecond > 0 ? Clamp(Evidence + GainPerSecond * RatePermille / 1000 * DtMs, 0, AwarenessMax) : 0;
}

constexpr bool FindsBody(int Evidence, FVigilance Vigilance)
{
    return Evidence >= Vigilance.SuspicionThreshold;
}

// A shout carries NoiseRadiusCm(Callout), half as far through walls; an
// auditor's alarm carries its own radius (AlarmRadiusCm > 0) through them.
constexpr bool CalloutReaches(int DistanceCm, bool Occluded, int AlarmRadiusCm)
{
    if (AlarmRadiusCm > 0)
        return DistanceCm >= 0 && DistanceCm <= AlarmRadiusCm;
    const int Radius = NoiseRadiusCm(ENoise::Callout);
    return DistanceCm >= 0 && DistanceCm <= (Occluded ? Radius / 2 : Radius);
}

// What a stealth zone does when the hero is detected (bible §12.2
// on_detected): the guards simply fight, the checkpoint is restored, or a
// reinforcement wave comes. On Easy every zone falls back to combat.
enum class EOnDetected { Combat, Restart, Reinforce };

constexpr EOnDetected Response(EOnDetected Zone, EDifficulty Difficulty)
{
    return Difficulty == EDifficulty::Easy ? EOnDetected::Combat : Zone;
}

// A zone that restarts from its checkpoint waits this long after detection,
// so the player sees who saw him, before the checkpoint is restored.
constexpr int RestartDelayMs = 2000;

// Work under guard (a production task with stealth: true, ch06.b08) pauses
// while any guard sees the hero, and stays paused while any guard is alert,
// searching or fighting: it resumes once every guard is calm and unaware or
// suspicious again, when the search times out or the guard is dealt with.
constexpr bool WorkPaused(bool AnySees, EState MostAlarmed)
{
    return AnySees || !(MostAlarmed == EState::Unaware || MostAlarmed == EState::Suspicious);
}

// How alarmed a state is, for the most alarmed guard and the detection meter.
constexpr int Severity(EState State)
{
    switch (State)
    {
    case EState::Unaware: return 0;
    case EState::Suspicious: return 1;
    case EState::Search: return 2;
    case EState::Alert: return 3;
    case EState::Retreat: return 3;
    case EState::Combat: return 4;
    }
    return 0;
}

// The detection meter, x1000: an unaware or suspicious guard's fill toward
// alert; a search's remaining time; full while it hunts or fights.
constexpr int Meter(FMind Mind, FVigilance Vigilance)
{
    switch (Mind.State)
    {
    case EState::Unaware:
    case EState::Suspicious: return Clamp(Mind.Awareness / AwarenessScale, 0, 1000);
    case EState::Search:
        return Clamp(1000 - Mind.StateMs * 1000 / (Vigilance.SearchDurationMs > 0 ? Vigilance.SearchDurationMs : 1), 0, 1000);
    case EState::Alert:
    case EState::Combat:
    case EState::Retreat: return 1000;
    }
    return 0;
}

// Rear takedowns. The hero stands inside the victim's rear 120 degrees,
// within reach, facing it; the victim has not placed him (unaware,
// suspicious or searching). A tap does the zone's default (lethal_default);
// the melee input held past TakedownHoldMs does the other. A debt-bound
// conscript is always struck with the back of the blade (峰打ち).
enum class ETakedown { Knockout, Lethal, Subdue };

constexpr int TakedownReachCm = 170;
// cos 120 degrees: the victim's facing to the hero; cos 60: the hero's to it.
constexpr int TakedownRearMilli = -500;
constexpr int TakedownAimMilli = 500;
constexpr int TakedownHoldMs = 400;

constexpr bool Unsuspecting(EState State)
{
    return IsCalm(State);
}

constexpr bool CanTakedown(bool ZoneAllows, bool Susceptible, EState VictimState, int DistanceCm, int VictimFacingMilli,
    int HeroFacingMilli)
{
    return ZoneAllows && Susceptible && Unsuspecting(VictimState) && DistanceCm >= 0 && DistanceCm <= TakedownReachCm &&
        VictimFacingMilli <= TakedownRearMilli && HeroFacingMilli >= TakedownAimMilli;
}

constexpr ETakedown Takedown(bool Nonlethal, bool LethalDefault, bool Held)
{
    return Nonlethal ? ETakedown::Subdue : LethalDefault != Held ? ETakedown::Lethal : ETakedown::Knockout;
}

// How long the hero is committed to each takedown from the press: a hilt
// strike to the collar-node (当て身), the ch03 gorget thrust, a 峰打ち.
constexpr int TakedownMs(ETakedown Kind)
{
    return Kind == ETakedown::Lethal ? 2200 : 1500;
}

// Moving a body: within reach and at half pace (ch06 bodies.drag_speed_mult).
constexpr int DragReachCm = 160;
constexpr int DragSpeedPermille = 500;
// A crouch-walk's pace against the hero's walk.
constexpr int CrouchSpeedPermille = 450;

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

// Progress on a walk. An opponent asked to move every frame that stays within
// StuckCm of where its clock started for StuckMs gives up on that goal
// (Stuck). The clock starts afresh (Restarted) on the first request, after
// a gap of more than AskGapMs without one (a pause, a stagger), after it
// has moved StuckCm, and on the request after it gave up, so one blocked
// walk never blocks the next.
enum class EProgress { Restarted, Walking, Stuck };
constexpr int StuckMs = 2000;
constexpr int StuckCm = 40;
constexpr int AskGapMs = 100;

struct FProgress
{
    bool Running = false;
    int AskedMs = 0;
    int SinceMs = 0;
};

// MovedCm is the distance from where the clock last started.
constexpr EProgress Progress(FProgress& Clock, int NowMs, int MovedCm)
{
    if (!Clock.Running || NowMs - Clock.AskedMs > AskGapMs || MovedCm > StuckCm)
    {
        Clock = {true, NowMs, NowMs};
        return EProgress::Restarted;
    }
    if (NowMs - Clock.SinceMs > StuckMs)
    {
        Clock.Running = false;
        return EProgress::Stuck;
    }
    Clock.AskedMs = NowMs;
    return EProgress::Walking;
}
} // namespace SoraStealthRules
