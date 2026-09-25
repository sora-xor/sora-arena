#include "SoraStealthRules.h"
#include <cassert>

using namespace SoraStealthRules;

namespace
{
constexpr int Frame = 17;

FSenses Quiet()
{
    return {0, 0, 0, 1000, false, true};
}

// Steps until the state changes or Limit milliseconds pass; returns the time taken.
int RunUntilChange(FMind& Mind, FSenses Senses, int Limit)
{
    const EState Start = Mind.State;
    int Elapsed = 0;
    while (Mind.State == Start && Elapsed < Limit)
    {
        Mind = Step(Mind, Senses, Frame);
        Elapsed += Frame;
    }
    return Elapsed;
}
}

int main()
{
    // Sight: only in the view cone, within range and unobstructed.
    const FSight Front{800, 1000, true, 1000, false};
    assert(InView(Front));
    assert(!InView({800, 1000, false, 1000, false}));
    assert(!InView({800, ViewConeMilli - 1, true, 1000, false}));
    assert(!InView({800, -1000, true, 1000, false}));
    assert(!InView({SightRangeCm + 1, 1000, true, 1000, false}));
    assert(InView({SightRangeCm, ViewConeMilli, true, 1000, false}));
    assert(SightGainPerSecond({800, 1000, false, 1000, true}) == 0);
    // Nearer, brighter, centred and moving targets are noticed faster.
    assert(SightGainPerSecond({400, 1000, true, 1000, false}) > SightGainPerSecond({2000, 1000, true, 1000, false}));
    assert(SightGainPerSecond(Front) > SightGainPerSecond({800, 1000, true, 100, false}));
    assert(SightGainPerSecond({800, 1000, true, 0, false}) > 0);
    assert(SightGainPerSecond(Front) > SightGainPerSecond({800, 500, true, 1000, false}));
    assert(SightGainPerSecond({800, 1000, true, 1000, true}) > SightGainPerSecond(Front));

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
    Glimpse.SightGain = SightGainPerSecond({2600, 400, true, 80, false});
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
}
