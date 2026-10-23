#include "SoraStealthRules.h"
#include "SoraMillisecondClock.h"
#include <cassert>
#include <initializer_list>
#include <limits>

using namespace SoraStealthRules;

namespace
{
constexpr int Frame = 17;

FSenses Quiet()
{
    return {0, 0, 0, 1000, false, true};
}

// Steps until the state changes or Limit milliseconds pass; returns the time taken.
int RunUntilChange(FMind& Mind, FSenses Senses, int Limit, FVigilance Vigilance = Watchful())
{
    const EState Start = Mind.State;
    int Elapsed = 0;
    while (Mind.State == Start && Elapsed < Limit)
    {
        Mind = Step(Mind, Senses, Frame, Vigilance);
        Elapsed += Frame;
    }
    return Elapsed;
}
}

int main()
{
    // The real adapter receives float frame deltas. Search and gallery hint
    // thresholds must track active seconds at common and variable frame rates.
    for (const int Fps : {30, 60, 120, 144})
    {
        FSoraMillisecondClock Clock;
        const float Dt = 1.f / Fps;
        int Elapsed = 0;
        FMind Searcher = Enter(Hunting(), EState::Search, 0);
        const FVigilance Vigil = [] { auto V=Watchful(); V.SearchDurationMs=20000; return V; }();
        for (int FrameIndex = 1; FrameIndex <= Fps * 60; ++FrameIndex)
        {
            const int Delta = Clock.Advance(Dt);
            Elapsed += Delta;
            const double ActiveMs = static_cast<double>(Dt) * FrameIndex * 1000.;
            assert(Elapsed <= ActiveMs + 1.e-7 && ActiveMs - Elapsed < 1.);
            if (FrameIndex < Fps * 20)
            {
                Searcher = Step(Searcher, Quiet(), Delta, Vigil);
                assert(Searcher.State == EState::Search);
            }
            else if (FrameIndex == Fps * 20)
            {
                Searcher = Step(Searcher, Quiet(), Delta, Vigil);
                assert(Searcher.State == EState::Unaware && Elapsed == 20000);
            }
            if (FrameIndex < Fps * 60) assert(Elapsed < 60000);
        }
        assert(Elapsed == 60000);
    }
    FSoraMillisecondClock MixedClock;
    double ActiveSeconds = 0.;
    int ActiveMs = 0;
    const float MixedFrames[] = {1.f/30, 1.f/60, 1.f/120, 1.f/144, .0004f, .125f};
    for (int Index = 0; Index < 6000; ++Index)
    {
        const float Dt = MixedFrames[Index % 6];
        ActiveSeconds += Dt;
        ActiveMs += MixedClock.Advance(Dt);
        assert(ActiveMs <= ActiveSeconds * 1000. + 1.e-7 && ActiveSeconds * 1000. - ActiveMs < 1.);
    }
    FSoraMillisecondClock PauseClock;
    assert(PauseClock.Advance(.00075) == 0);
    // Paused owners do not feed wall time; zero/invalid deltas also preserve
    // the fraction so resuming cannot lose or invent active milliseconds.
    for (int FrameIndex = 0; FrameIndex < 1000; ++FrameIndex) assert(PauseClock.Advance(0) == 0);
    assert(PauseClock.Advance(-1) == 0);
    assert(PauseClock.Advance(std::numeric_limits<double>::quiet_NaN()) == 0);
    assert(PauseClock.Advance(std::numeric_limits<double>::infinity()) == 0);
    assert(PauseClock.Advance(.0005) == 1);
    PauseClock.Reset();
    assert(PauseClock.Advance(.00075) == 0);
    // A sub-millisecond frame still delivers its one-off noise impulse.
    FSenses InstantNoise = Quiet();
    InstantNoise.NoiseImpulse = 1000;
    FMind InstantGuard = Step(Calm(), InstantNoise, 0);
    assert(InstantGuard.State == EState::Alert && InstantGuard.StateMs == 0);
    InstantGuard = Step(InstantGuard, Quiet(), PauseClock.Advance(.0005));
    assert(InstantGuard.State == EState::Alert && InstantGuard.StateMs == 1);

    // Sight: only in the view cone, within range and unobstructed.
    const FSight Front{800, 1000, 1000, 1000, false};
    assert(InView(Front));
    assert(!InView({800, 1000, 0, 1000, false}));
    assert(!InView({800, ViewConeMilli - 1, 1000, 1000, false}));
    assert(!InView({800, -1000, 1000, 1000, false}));
    assert(!InView({SightRangeCm + 1, 1000, 1000, 1000, false}));
    assert(InView({SightRangeCm, ViewConeMilli, 1000, 1000, false}));
    assert(SightGainPerSecond({800, 1000, 0, 1000, true}) == 0);
    // Nearer, brighter, centred and moving targets are noticed faster.
    assert(SightGainPerSecond({400, 1000, 1000, 1000, false}) > SightGainPerSecond({2000, 1000, 1000, 1000, false}));
    assert(SightGainPerSecond(Front) > SightGainPerSecond({800, 1000, 1000, 100, false}));
    assert(SightGainPerSecond({800, 1000, 1000, 0, false}) > 0);
    assert(SightGainPerSecond(Front) > SightGainPerSecond({800, 500, 1000, 1000, false}));
    assert(SightGainPerSecond({800, 1000, 1000, 1000, true}) > SightGainPerSecond(Front));

    // The light proxy: overcast day is full daylight, a dusk street is dark
    // except under its lanterns.
    assert(AmbientPermille(250) == 1000);
    assert(AmbientPermille(18) < 100);
    assert(LampPermille(0, 530) == 700);
    assert(LampPermille(530, 530) == 0);
    assert(LampPermille(100, 530) > LampPermille(400, 530));
    assert(LightPermille(AmbientPermille(18), LampPermille(50, 530)) > LightPermille(AmbientPermille(18), 0));
    assert(LightPermille(900, 900) == 1000);

    // Hearing: a nearby shot alerts at once; distant or muffled noises only
    // raise suspicion or are lost.
    assert(HeardPermille(ENoise::Shot, 1500, false) == 1000);
    assert(HeardPermille(ENoise::Shot, NoiseRadiusCm(ENoise::Shot), false) == 400);
    assert(HeardPermille(ENoise::Shot, NoiseRadiusCm(ENoise::Shot) + 1, false) == 0);
    assert(HeardPermille(ENoise::Shot, 2500, true) == 0);
    assert(HeardPermille(ENoise::Explosion, 2500, false) == 1000);
    assert(HeardPermille(ENoise::Sprint, 800, false) > HeardPermille(ENoise::Footstep, 400, false));
    assert(HeardPermille(ENoise::Footstep, 600, false) == 0);
    assert(IsContinuous(ENoise::Footstep) && IsContinuous(ENoise::Sprint) && !IsContinuous(ENoise::Shot));
    // A stone's landing carries 14 m and draws a look, less than a blade's clash.
    assert(NoiseRadiusCm(ENoise::Lure) == 1400 && !IsContinuous(ENoise::Lure));
    // A drop off a roof thuds 9 m around, as loud as a blade.
    assert(NoiseRadiusCm(ENoise::Landing) == 900 && !IsContinuous(ENoise::Landing) &&
        NoisePeakPermille(ENoise::Landing) == NoisePeakPermille(ENoise::Melee));
    assert(HeardPermille(ENoise::Lure, 600, false) == 600 && HeardPermille(ENoise::Lure, 1401, false) == 0);
    assert(HeardPermille(ENoise::Lure, 600, false) * AwarenessScale >= SuspiciousAt &&
        HeardPermille(ENoise::Lure, 600, false) * AwarenessScale < AwarenessMax);

    // An unaware guard that sees the hero close by in daylight: suspicious,
    // then straight into combat because it still sees him.
    FMind Guard = Calm();
    FSenses Seen = Quiet();
    Seen.SightGain = SightGainPerSecond(Front);
    const int ToSuspicion = RunUntilChange(Guard, Seen, 5000);
    assert(Guard.State == EState::Suspicious && ToSuspicion < 200);
    const int ToCombat = RunUntilChange(Guard, Seen, 5000);
    assert(Guard.State == EState::Combat && ToCombat < 500);
    // A dim, distant, peripheral glimpse takes seconds even to raise suspicion.
    FMind Distant = Calm();
    FSenses Glimpse = Quiet();
    Glimpse.SightGain = SightGainPerSecond({2600, 400, 1000, 80, false});
    assert(RunUntilChange(Distant, Glimpse, 60000) > 4000 && Distant.State == EState::Suspicious);

    // Nothing seen or heard: the guard stays unaware.
    FMind Idle = Calm();
    assert(RunUntilChange(Idle, Quiet(), 10000) >= 10000 && Idle.State == EState::Unaware);

    // One nearby shot alerts an unaware guard in a single step; it goes to
    // the place, searches, then gives up and becomes unaware again.
    FMind Sentry = Calm();
    FSenses Shot = Quiet();
    Shot.NoiseImpulse = HeardPermille(ENoise::Shot, 1500, false);
    Sentry = Step(Sentry, Shot, Frame);
    assert(Sentry.State == EState::Alert);
    FSenses Arrived = Quiet();
    Arrived.Reached = true;
    Sentry = Step(Sentry, Arrived, Frame);
    assert(Sentry.State == EState::Search && Sentry.Awareness == 0);
    const int Searched = RunUntilChange(Sentry, Quiet(), SearchMs * 2);
    assert(Sentry.State == EState::Unaware && Searched >= SearchMs && Searched < SearchMs + Frame * 2);

    // A single footstep noise only builds suspicion over time; the guard
    // keeps its interest until it has looked, then calms down.
    FMind Listener = Calm();
    FSenses Steps = Quiet();
    Steps.NoisePerSecond = HeardPermille(ENoise::Footstep, 150, false);
    RunUntilChange(Listener, Steps, 5000);
    assert(Listener.State == EState::Suspicious);
    Listener = Step(Listener, Quiet(), 3000);
    assert(Listener.State == EState::Suspicious);
    RunUntilChange(Listener, Arrived, 10000);
    assert(Listener.State == EState::Unaware);

    // In search, fresh evidence sends the opponent back to the hunt, and sight
    // brings it straight into combat.
    FMind Searcher = Enter(Hunting(), EState::Search, 0);
    Searcher = Step(Searcher, Shot, Frame);
    assert(Searcher.State == EState::Alert);
    Searcher = Enter(Hunting(), EState::Search, 0);
    Searcher = Step(Searcher, Seen, Frame);
    assert(Searcher.State == EState::Combat);

    // Combat: losing sight for the memory span means hunting the last known
    // place; badly hurt ranged opponents retreat once, blades never do.
    FMind Fighter = Enter(Hunting(), EState::Combat, AwarenessMax);
    const int Lost = RunUntilChange(Fighter, Quiet(), 10000);
    assert(Fighter.State == EState::Alert && Lost >= CombatMemoryMs && Lost < CombatMemoryMs + Frame * 2);
    FMind Hurt = Enter(Hunting(), EState::Combat, AwarenessMax);
    FSenses Wounded = Seen;
    Wounded.HealthPermille = RetreatHealthPermille;
    Hurt = Step(Hurt, Wounded, Frame);
    assert(Hurt.State == EState::Retreat && Hurt.Retreated);
    Wounded.Reached = true;
    const int Fled = RunUntilChange(Hurt, Wounded, 10000);
    assert(Hurt.State == EState::Combat && Fled >= RetreatMinMs);
    Hurt = Step(Hurt, Wounded, Frame);
    assert(Hurt.State == EState::Combat);
    FMind Blade = Enter(Hunting(), EState::Combat, AwarenessMax);
    Wounded.CanRetreat = CanRetreat(ERole::Blade);
    Blade = Step(Blade, Wounded, Frame);
    assert(Blade.State == EState::Combat);
    // A retreat with nowhere to reach still ends.
    FMind Cornered = Enter(Hunting(), EState::Retreat, AwarenessMax);
    assert(RunUntilChange(Cornered, Quiet(), 20000) >= RetreatMaxMs && Cornered.State == EState::Alert);

    // A hunting wave starts alert and closes straight to combat on sight.
    FMind Hunter = Hunting();
    assert(Hunter.State == EState::Alert);
    Hunter = Step(Hunter, Seen, Frame);
    assert(Hunter.State == EState::Combat);

    // Roles, flanking sides, reactions and peeks follow slots, never dice.
    assert(Role(0, true) == ERole::Blade);
    assert(Role(1, false) == ERole::Flanker && Role(4, false) == ERole::Flanker);
    assert(Role(2, false) == ERole::CoverShooter && Role(3, false) == ERole::CoverShooter);
    assert(FlankSide(1) == -FlankSide(4));
    assert(ReactionMs(1) != ReactionMs(2) && ReactionMs(0) == ReactionMs(3));
    int PeekingSlots = 0;
    for (int Slot = 1; Slot <= 5; ++Slot)
        PeekingSlots += Peeking(0, Slot) ? 1 : 0;
    assert(PeekingSlots > 0 && PeekingSlots < 5);
    for (int Now = 0; Now < PeekCycleMs * 3; Now += Frame)
        assert(Peeking(Now, 2) == Peeking(Now + PeekCycleMs, 2));

    // Cover preference: nearby cover at a firing distance beats distant cover;
    // too close or too far from the hero is rejected; retreat cover is far away.
    assert(CoverScore(300, 900) < CoverScore(900, 900));
    assert(CoverScore(300, 900) < CoverScore(300, 1800));
    assert(CoverScore(300, 300) < 0 && CoverScore(300, 2500) < 0);
    assert(RetreatScore(300, 800) < 0 && RetreatScore(300, 1500) == 300);

    // Each archetype perceives with its own senses (Content/Data/enemies.json).
    // The standard perception is exactly the constants above.
    const FPerception Standard = SoraStealthRules::Standard();
    assert(StandardHearingCm == NoiseRadiusCm(ENoise::Sprint));
    assert(InView({SightRangeCm, ViewConeMilli, 1000, 0, false}, Standard));
    assert(SightGainPerSecond(Front, Standard) == SightGainPerSecond(Front));
    assert(HeardPermille(ENoise::Shot, 2000, false, Standard) == HeardPermille(ENoise::Shot, 2000, false));
    // A dark range: a target in darkness is seen only close; light restores the range.
    FPerception Watch = Standard;
    Watch.DarkSightRangeCm = 800;
    assert(SightRangeAt(Watch, 0) == 800 && SightRangeAt(Watch, 1000) == SightRangeCm);
    assert(!InView({1500, 1000, 1000, 0, false}, Watch) && InView({1500, 1000, 1000, 1000, false}, Watch));
    assert(InView({700, 1000, 1000, 0, false}, Watch));
    // A narrow drone cone and a long marksman's eye.
    FPerception Drone = Standard;
    Drone.ViewConeMilli = 866;
    Drone.FocusConeMilli = 866;
    assert(!InView({800, 800, 1000, 1000, false}, Drone) && InView({800, 900, 1000, 1000, false}, Drone));
    FPerception Marksman = Standard;
    Marksman.SightRangeCm = Marksman.DarkSightRangeCm = 4000;
    assert(InView({3500, 1000, 1000, 1000, false}, Marksman) && !InView({3500, 1000, 1000, 1000, false}));
    // Hearing scales every noise's reach; a deaf drone hears nothing.
    FPerception Keen = Standard;
    Keen.HearingCm = StandardHearingCm * 2;
    assert(HeardRadiusCm(ENoise::Footstep, Keen) == NoiseRadiusCm(ENoise::Footstep) * 2);
    assert(HeardPermille(ENoise::Footstep, 600, false, Keen) > 0 && HeardPermille(ENoise::Footstep, 600, false) == 0);
    FPerception Deaf = Standard;
    Deaf.HearingCm = 0;
    assert(HeardPermille(ENoise::Explosion, 10, false, Deaf) == 0);
    // A reluctant conscript notices everything a fifth more slowly: even a close
    // shot only makes it suspicious.
    FPerception Reluctant = Standard;
    Reluctant.SuspicionPermille = 800;
    assert(SightGainPerSecond(Front, Reluctant) == SightGainPerSecond(Front) * 800 / 1000);
    assert(HeardPermille(ENoise::Shot, 1500, false, Reluctant) == 800);
    FMind Conscript = Calm();
    FSenses Startled = Quiet();
    Startled.NoiseImpulse = HeardPermille(ENoise::Shot, 1500, false, Reluctant);
    Conscript = Step(Conscript, Startled, Frame);
    assert(Conscript.State == EState::Suspicious);
    // An alarmist auditor skips suspicion: what it half-notices, it reports.
    FMind Auditor = Calm();
    FSenses Noticed = Quiet();
    Noticed.Alarmist = true;
    Noticed.NoisePerSecond = HeardPermille(ENoise::Footstep, 150, false);
    RunUntilChange(Auditor, Noticed, 5000);
    assert(Auditor.State == EState::Alert && Auditor.Awareness == AwarenessMax);

    // Exposure: only the part of the hero a line reaches counts. A crouch
    // behind low cover is hidden; a standing head above it is seen slowly.
    assert(ExposurePermille(3, 3) == 1000 && ExposurePermille(1, 3) == 333 && ExposurePermille(0, 3) == 0);
    assert(!InView({800, 1000, ExposurePermille(0, 3), 1000, false}));
    const FSight Head{800, 1000, ExposurePermille(1, 3), 1000, false};
    assert(InView(Head) && SightGainPerSecond(Head) > 0 && SightGainPerSecond(Head) * 3 <= SightGainPerSecond(Front) + 3);
    // A crouched outline is seen more slowly; a lit candle gives the hero away,
    // a cupped one less. The defaults are the standing, empty-handed hero.
    FSight Crouched = Front;
    Crouched.Crouched = true;
    assert(SightGainPerSecond(Crouched) == SightGainPerSecond(Front) * CrouchedOutlinePermille / 1000);
    FSight Candle = Front;
    Candle.VisibilityPermille = 2000;
    assert(SightGainPerSecond(Candle) == SightGainPerSecond(Front) * 2);
    Candle.VisibilityPermille = 1200;
    assert(SightGainPerSecond(Candle) > SightGainPerSecond(Front) && SightGainPerSecond(Candle) < SightGainPerSecond(Front) * 2);
    // In the dark a crouch nearly doubles the time to suspicion, and past a
    // tuned guard's dark range (ch06: 900 cm) a crouch in the dark is unseen.
    FMind DimStanding = Calm(), DimCrouched = Calm();
    FSenses DarkStand = Quiet(), DarkCrouch = Quiet();
    DarkStand.SightGain = SightGainPerSecond({1000, 1000, 1000, 40, true});
    DarkCrouch.SightGain = SightGainPerSecond({1000, 1000, 1000, 40, true, true});
    const int StandMs = RunUntilChange(DimStanding, DarkStand, 60000);
    const int CrouchMs = RunUntilChange(DimCrouched, DarkCrouch, 60000);
    assert(DimCrouched.State == EState::Suspicious && CrouchMs * 1000 > StandMs * 1700);
    FPerception Ch06Guard = SoraStealthRules::Standard();
    Ch06Guard.SightRangeCm = 2400;
    Ch06Guard.DarkSightRangeCm = 900;
    assert(!InView({1000, 1000, 1000, 40, true, true}, Ch06Guard) && InView({1000, 1000, 1000, 1000, true, true}, Ch06Guard));

    // Footsteps by stance: a sprint stands the hero up; crouch-walking is
    // quieter than walking and unheard a few metres off.
    assert(SoraStealthRules::Steps(true, EStance::Crouched) == ENoise::Sprint);
    assert(SoraStealthRules::Steps(false, EStance::Crouched) == ENoise::CrouchStep && SoraStealthRules::Steps(false, EStance::Standing) == ENoise::Footstep);
    assert(IsContinuous(ENoise::CrouchStep) && !IsContinuous(ENoise::Takedown));
    assert(HeardRadiusCm(ENoise::CrouchStep) < HeardRadiusCm(ENoise::Footstep));
    assert(HeardPermille(ENoise::CrouchStep, 300, false) == 0 && HeardPermille(ENoise::Footstep, 300, false) > 0);
    assert(HeardPermille(ENoise::CrouchStep, 80, false) > 0 && HeardPermille(ENoise::CrouchStep, 80, false) < HeardPermille(ENoise::Footstep, 80, false));
    // Floors: puddles carry half again as far; a nightingale floor sings even
    // under a crouch, except along its silent edge strip. Loudness 1000 is plain ground.
    const FSurface Puddle{1500, 1500}, Nightingale{3000, 3600}, EdgeStrip{3000, 0};
    assert(StepLoudnessPermille(ENoise::Footstep, Plain()) == 1000 && StepLoudnessPermille(ENoise::CrouchStep, Plain()) == 1000);
    assert(HeardRadiusCm(ENoise::Footstep, SoraStealthRules::Standard(), 1000) == HeardRadiusCm(ENoise::Footstep));
    assert(HeardRadiusCm(ENoise::Footstep, SoraStealthRules::Standard(), StepLoudnessPermille(ENoise::Footstep, Puddle)) == NoiseRadiusCm(ENoise::Footstep) * 3 / 2);
    assert(HeardRadiusCm(ENoise::Footstep, SoraStealthRules::Standard(), StepLoudnessPermille(ENoise::Footstep, Nightingale)) == NoiseRadiusCm(ENoise::Footstep) * 3);
    assert(HeardPermille(ENoise::CrouchStep, 300, false, SoraStealthRules::Standard(), StepLoudnessPermille(ENoise::CrouchStep, Nightingale)) > 0);
    assert(HeardPermille(ENoise::CrouchStep, 10, false, SoraStealthRules::Standard(), StepLoudnessPermille(ENoise::CrouchStep, EdgeStrip)) == 0);
    assert(HeardPermille(ENoise::Footstep, 10, false, SoraStealthRules::Standard(), StepLoudnessPermille(ENoise::Footstep, EdgeStrip)) > 0);
    // A takedown's scuffle makes a guard beside it wonder, and carries no farther than a couple of metres.
    assert(HeardPermille(ENoise::Takedown, 100, false) * AwarenessScale >= SuspiciousAt);
    assert(HeardPermille(ENoise::Takedown, NoiseRadiusCm(ENoise::Takedown) + 1, false) == 0);

    // Vigilance. Outside a zone the standard guard is exactly as before.
    FMind Plainly = Calm(), Watched = Calm();
    for (int Elapsed = 0; Elapsed < 600; Elapsed += Frame)
    {
        Plainly = Step(Plainly, Seen, Frame);
        Watched = Step(Watched, Seen, Frame, Watchful());
    }
    assert(Plainly.State == Watched.State && Plainly.Awareness == Watched.Awareness);
    // A zone's detection block: ch06's suspicious_at 0.35 and 25 s search.
    const FVigilance Ch06 = Detection(1000, 350, 25000);
    assert(Ch06.SuspicionThreshold == 350 * AwarenessScale && Ch06.SearchDurationMs == 25000 && Ch06.WaryRatePermille == WaryPermille);
    // A slower zone rate (the moat's 0.8) takes longer to raise suspicion.
    FSenses Distant2 = Quiet();
    Distant2.SightGain = SightGainPerSecond({2000, 1000, 1000, 100, false});
    FMind Standard1 = Calm(), Moat = Calm();
    const int AtStandard = RunUntilChange(Standard1, Distant2, 60000, Detection(1000, 250, 20000));
    const int AtMoat = RunUntilChange(Moat, Distant2, 60000, Detection(800, 250, 20000));
    assert(Standard1.State == EState::Suspicious && Moat.State == EState::Suspicious && AtMoat > AtStandard);
    // Difficulty: Easy notices at 0.7 and searches 0.8 as long; Hard 1.25 and 1.2.
    assert(OnDifficulty(Ch06, EDifficulty::Easy).RatePermille == 700 && OnDifficulty(Ch06, EDifficulty::Easy).SearchDurationMs == 20000);
    assert(OnDifficulty(Ch06, EDifficulty::Hard).RatePermille == 1250 && OnDifficulty(Ch06, EDifficulty::Hard).SearchDurationMs == 30000);
    assert(OnDifficulty(Ch06, EDifficulty::Normal).RatePermille == 1000 && OnDifficulty(Ch06, EDifficulty::Normal).SearchDurationMs == 25000);

    // A search runs the zone's search_s, then the guard stands down wary for the rest of the beat.
    FMind Sweep = Enter(Calm(), EState::Search, 0);
    const int Swept = RunUntilChange(Sweep, Quiet(), 60000, Ch06);
    assert(Sweep.State == EState::Unaware && Sweep.Wary && Swept >= 25000 && Swept < 25000 + Frame * 2);
    assert(RatePermille(Sweep, Ch06) == WaryPermille && RatePermille(Calm(), Ch06) == 1000);
    FMind Fresh = Calm();
    FMind Wary = Sweep;
    assert(RunUntilChange(Wary, Distant2, 60000, Ch06) < RunUntilChange(Fresh, Distant2, 60000, Ch06));
    // Faint evidence in a search fades: two faint noises a second apart do not
    // add up to a hunt, where together they would.
    FMind Faded = Enter(Calm(), EState::Search, 0);
    FSenses Faint = Quiet();
    Faint.NoiseImpulse = 200;
    Faded = Step(Faded, Faint, Frame, Ch06);
    assert(Faded.State == EState::Search && Faded.Awareness == 200 * AwarenessScale);
    for (int Elapsed = 0; Elapsed < 1000; Elapsed += Frame)
        Faded = Step(Faded, Quiet(), Frame, Ch06);
    assert(Faded.Awareness < 50 * AwarenessScale);
    Faded = Step(Faded, Faint, Frame, Ch06);
    assert(Faded.State == EState::Search);
    FMind Doubled = Enter(Calm(), EState::Search, 0);
    Doubled = Step(Doubled, Faint, Frame, Ch06);
    Doubled = Step(Doubled, Faint, Frame, Ch06);
    assert(Doubled.State == EState::Alert);

    // Carryover: a zone entered after the hero was detected posts its guards
    // suspicious and wary; otherwise they start calm.
    assert(Posted(false).State == EState::Unaware && !Posted(false).Wary);
    assert(Posted(true).State == EState::Suspicious && Posted(true).Wary && Posted(true).Awareness == SuspiciousAt);

    // Detection: a calm guard that comes to know where the hero is. A search
    // or suspicion is not detection, nor is a hunt that goes on.
    assert(Detects(EState::Unaware, EState::Alert) && Detects(EState::Suspicious, EState::Combat) && Detects(EState::Search, EState::Alert));
    assert(!Detects(EState::Unaware, EState::Suspicious) && !Detects(EState::Unaware, EState::Search));
    assert(!Detects(EState::Alert, EState::Combat) && !Detects(EState::Combat, EState::Alert) && !Detects(EState::Retreat, EState::Combat));
    // The zone's answer; on Easy every zone falls back to combat (bible §12.2).
    assert(Response(EOnDetected::Restart, EDifficulty::Normal) == EOnDetected::Restart);
    assert(Response(EOnDetected::Reinforce, EDifficulty::Hard) == EOnDetected::Reinforce);
    assert(Response(EOnDetected::Combat, EDifficulty::Normal) == EOnDetected::Combat);
    assert(Response(EOnDetected::Restart, EDifficulty::Easy) == EOnDetected::Combat && Response(EOnDetected::Reinforce, EDifficulty::Easy) == EOnDetected::Combat);
    assert(RestartDelayMs >= 1000);

    // The zone alarm: calm guards go to it, fighting ones fight on; all are wary.
    assert(Alarmed(Calm()).State == EState::Alert && Alarmed(Calm()).Wary && Alarmed(Calm()).Awareness == AwarenessMax);
    assert(Alarmed(Enter(Calm(), EState::Search, 0)).State == EState::Alert);
    const FMind Fighting = Enter(Hunting(), EState::Combat, AwarenessMax);
    assert(Alarmed(Fighting).State == EState::Combat && Alarmed(Fighting).Wary);
    // A shout carries eighteen metres, half that through walls; an auditor's
    // alarm carries its own radius through them.
    assert(CalloutReaches(1800, false, 0) && !CalloutReaches(1801, false, 0));
    assert(CalloutReaches(900, true, 0) && !CalloutReaches(901, true, 0));
    assert(CalloutReaches(3000, true, 3000) && !CalloutReaches(3001, false, 3000));

    // A body found: unaware and suspicious guards search, a hunt goes on; all are wary.
    assert(BodyFound(Calm()).State == EState::Search && BodyFound(Calm()).Wary && BodyFound(Calm()).Awareness == 0);
    assert(BodyFound(Enter(Calm(), EState::Suspicious, SuspiciousAt)).State == EState::Search);
    assert(BodyFound(Hunting()).State == EState::Alert && BodyFound(Fighting).State == EState::Combat);
    assert(!Detects(EState::Unaware, BodyFound(Calm()).State));
    // Evidence of a body gathers while it stays in view and starts over when
    // it is lost; a lit body is found at once, one in the dark takes longer.
    const int LitBody = SightGainPerSecond({1000, 1000, 1000, 1000, false, true});
    const int DarkBody = SightGainPerSecond({1000, 1000, 1000, 40, false, true});
    assert(BodyEvidence(0, 0, 1000, Frame) == 0 && BodyEvidence(100000, 0, 1000, Frame) == 0);
    assert(BodyEvidence(0, LitBody, 1000, Frame) == LitBody * Frame);
    int LitMs = 0, DarkMs = 0;
    for (int Evidence = 0; !FindsBody(Evidence, Ch06); LitMs += Frame)
        Evidence = BodyEvidence(Evidence, LitBody, 1000, Frame);
    for (int Evidence = 0; !FindsBody(Evidence, Ch06); DarkMs += Frame)
        Evidence = BodyEvidence(Evidence, DarkBody, 1000, Frame);
    assert(LitMs < 300 && DarkMs > LitMs * 3);

    // Work under guard (ch06.b08) pauses while seen and while any guard is
    // alert, searching or fighting; a merely suspicious guard lets it go on.
    assert(!WorkPaused(false, EState::Unaware) && !WorkPaused(false, EState::Suspicious));
    assert(WorkPaused(true, EState::Unaware) && WorkPaused(false, EState::Search) && WorkPaused(false, EState::Alert));
    assert(WorkPaused(false, EState::Combat) && WorkPaused(false, EState::Retreat));

    // The detection meter and the most alarmed guard.
    assert(Meter(Enter(Calm(), EState::Suspicious, 500 * AwarenessScale), Ch06) == 500);
    FMind HalfSearched = Enter(Calm(), EState::Search, 0);
    HalfSearched.StateMs = 12500;
    assert(Meter(HalfSearched, Ch06) == 500 && Meter(Hunting(), Ch06) == 1000 && Meter(Calm(), Ch06) == 0);
    assert(Severity(EState::Unaware) < Severity(EState::Suspicious) && Severity(EState::Suspicious) < Severity(EState::Search));
    assert(Severity(EState::Search) < Severity(EState::Alert) && Severity(EState::Alert) < Severity(EState::Combat));

    // Rear takedowns: from within reach behind an unsuspecting guard of a kind
    // that can be taken down, facing it, in a zone that allows them.
    assert(CanTakedown(true, true, EState::Unaware, 120, -1000, 1000));
    assert(CanTakedown(true, true, EState::Suspicious, TakedownReachCm, TakedownRearMilli, TakedownAimMilli));
    assert(CanTakedown(true, true, EState::Search, 100, -900, 900));
    assert(!CanTakedown(false, true, EState::Unaware, 120, -1000, 1000));
    assert(!CanTakedown(true, false, EState::Unaware, 120, -1000, 1000));
    assert(!CanTakedown(true, true, EState::Alert, 120, -1000, 1000) && !CanTakedown(true, true, EState::Combat, 120, -1000, 1000));
    assert(!CanTakedown(true, true, EState::Unaware, TakedownReachCm + 1, -1000, 1000));
    assert(!CanTakedown(true, true, EState::Unaware, 120, TakedownRearMilli + 1, 1000));
    assert(!CanTakedown(true, true, EState::Unaware, 120, 1000, 1000));
    assert(!CanTakedown(true, true, EState::Unaware, 120, -1000, TakedownAimMilli - 1));
    // A tap does the zone's default, a hold the other; a debt-bound conscript
    // is always struck with the back of the blade.
    assert(Takedown(false, false, false) == ETakedown::Knockout && Takedown(false, false, true) == ETakedown::Lethal);
    assert(Takedown(false, true, false) == ETakedown::Lethal && Takedown(false, true, true) == ETakedown::Knockout);
    assert(Takedown(true, true, true) == ETakedown::Subdue && Takedown(true, false, false) == ETakedown::Subdue);
    assert(TakedownMs(ETakedown::Lethal) == 2200 && TakedownMs(ETakedown::Knockout) == 1500 && TakedownMs(ETakedown::Subdue) == 1500);
    assert(TakedownHoldMs < TakedownMs(ETakedown::Knockout));
    assert(DragSpeedPermille == 500 && CrouchSpeedPermille < 1000);

    // A walk that makes no progress gives up after two seconds of requests.
    // The request after that starts a fresh clock rather than giving up at
    // once, so a guard body-blocked for a moment walks on to its next goal.
    FProgress Clock;
    assert(Progress(Clock, 5000, 0) == EProgress::Restarted);
    int Now = 5016;
    EProgress Last = EProgress::Walking;
    for (; Last == EProgress::Walking; Now += 16)
        Last = Progress(Clock, Now, 10);
    const int StuckAt = Now - 16;
    assert(Last == EProgress::Stuck && StuckAt - 5000 > StuckMs && StuckAt - 5000 <= StuckMs + 16);
    assert(Progress(Clock, StuckAt + 16, 10) == EProgress::Restarted);
    assert(Progress(Clock, StuckAt + 32, 10) == EProgress::Walking);
    // A pause between requests, or moving away, restarts the clock too.
    assert(Progress(Clock, StuckAt + 32 + AskGapMs + 1, 10) == EProgress::Restarted);
    assert(Progress(Clock, StuckAt + 160, StuckCm + 1) == EProgress::Restarted);
    assert(Progress(Clock, StuckAt + 176, StuckCm) == EProgress::Walking);
    // The first request of a late-spawned walker is never stuck, wherever it stands.
    FProgress Late;
    assert(Progress(Late, 2000000000, 0) == EProgress::Restarted && Progress(Late, 2000000016, 0) == EProgress::Walking);
}
