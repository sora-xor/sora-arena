#include "SoraGameMode.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Combat/SoraDamage.h"
#include "Combat/SoraStealth.h"
#include "SoraCatalog.h"
#include "SoraEnemyTestArena.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameEvents.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"

// The stealth zone in real game worlds: crouching lowers the hero behind low
// cover and softens his steps; a rear takedown knocks a guard out on a tap,
// kills on a hold and only ever strikes a conscript with the back of the
// blade; a found body sends the whole zone searching without detecting the
// hero, and a body can be dragged out of sight; an auditor raises the zone's
// alarm only at a lectern; and detection is announced once with the zone's
// answer on its difficulty, with the HUD's readout following the guards.
namespace SoraStealthAutomation
{
using SoraEnemyTest::FArena;
using EState = SoraStealthRules::EState;

const TCHAR* Name(EState State)
{
    switch (State)
    {
    case EState::Unaware: return TEXT("Unaware");
    case EState::Suspicious: return TEXT("Suspicious");
    case EState::Alert: return TEXT("Alert");
    case EState::Search: return TEXT("Search");
    case EState::Combat: return TEXT("Combat");
    case EState::Retreat: return TEXT("Retreat");
    }
    return TEXT("Unknown");
}

// What the zone announced during a case.
struct FRecord
{
    TArray<FSoraStealthDetection> Detected;
    TArray<ASoraEnemy*> Alarms;
    TArray<TPair<ASoraEnemy*, ASoraEnemy*>> Bodies;
    TArray<FSoraEnemyCueEvent> Cues;
    TArray<FSoraDiedEvent> Died;
    int32 CueCount(const AActor* Enemy, ESoraEnemyCue Cue) const
    {
        int32 Count = 0;
        for (const FSoraEnemyCueEvent& Event : Cues)
            Count += Event.Enemy == Enemy && Event.Cue == Cue ? 1 : 0;
        return Count;
    }
};

TSharedRef<FRecord> Record(UWorld* World)
{
    const TSharedRef<FRecord> Log = MakeShared<FRecord>();
    if (USoraStealth* Zone = USoraStealth::Get(World))
    {
        Zone->OnDetected.AddLambda([Log](const FSoraStealthDetection& Event) { Log->Detected.Add(Event); });
        Zone->OnAlarm.AddLambda([Log](ASoraEnemy* By) { Log->Alarms.Add(By); });
        Zone->OnBodyFound.AddLambda([Log](ASoraEnemy* Body, ASoraEnemy* Finder) { Log->Bodies.Add({Body, Finder}); });
    }
    if (USoraGameEvents* Events = USoraGameEvents::Get(World))
    {
        Events->OnEnemyCue.AddLambda([Log](const FSoraEnemyCueEvent& Event) { Log->Cues.Add(Event); });
        Events->OnDied.AddLambda([Log](const FSoraDiedEvent& Event) { Log->Died.Add(Event); });
    }
    return Log;
}

// The chapter's director answers a defeat with a fresh hunter; each case keeps
// only the opponents it placed, removing the rest before every frame.
bool Tick(FArena& Arena, int32 Frames, const TArray<ASoraEnemy*>& Keep)
{
    for (int32 Index = 0; Index < Frames; ++Index)
    {
        for (TActorIterator<ASoraEnemy> It(Arena.Get()); It; ++It)
            if (!Keep.Contains(*It))
                It->Destroy();
        if (!Arena.Tick(1))
            return false;
    }
    return true;
}

bool Until(FArena& Arena, int32 MaxFrames, const TArray<ASoraEnemy*>& Keep, TFunctionRef<bool()> Done)
{
    for (int32 Index = 0; Index < MaxFrames && !Done(); ++Index)
        if (!Tick(Arena, 1, Keep))
            return false;
    return true;
}

bool Press(FArena& Arena, const FKey& Key, bool bDown)
{
    return Arena.World->InjectKey(Key, bDown ? IE_Pressed : IE_Released);
}

// A guard at its post, facing Yaw.
ASoraEnemy* Guard(const FArena& Arena, const TCHAR* Archetype, int32 Slot, const FVector& At, float Yaw)
{
    FSoraPatrolRoute Post;
    Post.Points.Add(FVector(At.X, At.Y, 90.f));
    return Arena.SpawnKind(Archetype, Slot, At, Yaw, &Post);
}

float Floor(const ASoraPlayerCharacter& Hero)
{
    return Hero.GetActorLocation().Z - Hero.GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
}
} // namespace SoraStealthAutomation

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraStealthCrouchAndCoverTest,
    "SoraArena.Stealth.CrouchAndCover",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraStealthCrouchAndCoverTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraStealthAutomation;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FArena Arena(*this, TEXT("StealthCrouch"));
    if (!Arena.Start())
        return false;
    USoraStealth* Zone = USoraStealth::Get(Arena.Get());
    if (!TestNotNull(TEXT("The stealth zone exists in a game world"), Zone))
        return false;
    Zone->BeginZone(FSoraStealthZone());
    ASoraPlayerCharacter* Hero = Arena.Hero();

    // The hero crouches a metre behind a 125 cm wall: a lower capsule and,
    // once it settles, a lower eye.
    Arena.PlaceHero(FVector(700.f, 0.f, 0.f), 180.f);
    const float Ground = Floor(*Hero);
    AActor* Wall = Arena.Wall(FVector(600.f, 0.f, Ground + 62.5f), FVector(40.f, 400.f, 125.f));
    TArray<ASoraEnemy*> Keep;
    if (!Tick(Arena, 2, Keep))
        return false;
    const float StandingEye = Hero->GetCamera()->GetComponentLocation().Z;
    if (!Press(Arena, EKeys::C, true) || !Tick(Arena, 1, Keep) || !Press(Arena, EKeys::C, false) || !Tick(Arena, 40, Keep))
        return false;
    const float CrouchedEye = Hero->GetCamera()->GetComponentLocation().Z;
    AddInfo(FString::Printf(TEXT("Crouched: capsule half-height %.0f, eye %.0f cm lower"),
        Hero->GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight(), StandingEye - CrouchedEye));
    TestTrue(TEXT("C crouches the hero"), Hero->IsCrouched());
    TestEqual(TEXT("The crouched capsule is 88 cm tall"), Hero->GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight(), 44.f);
    TestTrue(TEXT("The eye settles well below standing height"), StandingEye - CrouchedEye >= 60.f);
    TestTrue(TEXT("The feet stay on the floor"), FMath::Abs(Floor(*Hero) - Ground) < 3.f);

    // A sentry beyond the wall looks straight at him and sees nothing.
    ASoraEnemy* Sentry = Guard(Arena, TEXT("enforcer_rifle"), 20, FVector::ZeroVector, 0.f);
    ASoraEnemyController* Brain = FArena::Brain(Sentry);
    Keep = {Sentry};
    if (!TestNotNull(TEXT("A sentry spawns with its brain"), Brain) || !Tick(Arena, 1, Keep))
        return false;
    TestFalse(TEXT("Crouched behind the low wall, the hero is hidden"), Brain->CanSee(*Hero));
    if (!Tick(Arena, 120, Keep))
        return false;
    TestEqual(TEXT("Two seconds crouched behind cover leave the sentry unaware"), static_cast<int32>(Brain->State()), static_cast<int32>(EState::Unaware));
    TestEqual(TEXT("Its meter stays empty"), Brain->AwarenessPermille(), 0);
    TestTrue(TEXT("The HUD readout shows the crouch"), Zone->Readout(*Hero).bCrouched);

    // C again stands him up, and his head shows over the wall.
    if (!Press(Arena, EKeys::C, true) || !Tick(Arena, 1, Keep) || !Press(Arena, EKeys::C, false) || !Tick(Arena, 3, Keep))
        return false;
    TestFalse(TEXT("C again stands the hero up"), Hero->IsCrouched());
    TestTrue(TEXT("Standing, the hero's head shows over the low wall"), Brain->CanSee(*Hero));

    // Footsteps: from seven metres behind a second sentry to two and a half,
    // a crouch-walk is not heard; a walk over the same ground is.
    Wall->Destroy();
    Sentry->Destroy();
    ASoraEnemy* Listener = Guard(Arena, TEXT("enforcer_rifle"), 21, FVector(-1200.f, 0.f, 0.f), 0.f);
    ASoraEnemyController* Ears = FArena::Brain(Listener);
    Keep = {Listener};
    Arena.PlaceHero(FVector(-1900.f, 0.f, 0.f), 0.f);
    if (!TestNotNull(TEXT("A listening sentry spawns"), Ears) || !Press(Arena, EKeys::C, true) || !Tick(Arena, 1, Keep) ||
        !Press(Arena, EKeys::C, false) || !Tick(Arena, 30, Keep) || !TestTrue(TEXT("The hero crouches again"), Hero->IsCrouched()) ||
        !Press(Arena, EKeys::W, true))
        return false;
    float Fastest = 0.f;
    if (!Until(Arena, 300, Keep, [&]() { Fastest = FMath::Max(Fastest, Hero->GetVelocity().Size2D()); return Hero->GetActorLocation().X >= -1450.f; }) ||
        !Press(Arena, EKeys::W, false))
        return false;
    AddInfo(FString::Printf(TEXT("Crouch-walk: %.0f cm/s; the sentry is %s at %d permille"), Fastest, Name(Ears->State()), Ears->AwarenessPermille()));
    TestTrue(TEXT("The crouch-walk reached the sentry's back"), Hero->GetActorLocation().X >= -1450.f);
    TestTrue(TEXT("A crouch-walk is slower than a walk"), Fastest > 150.f && Fastest < 300.f);
    TestEqual(TEXT("The crouch-walk is not heard"), Ears->AwarenessPermille(), 0);
    TestEqual(TEXT("The sentry stays unaware"), static_cast<int32>(Ears->State()), static_cast<int32>(EState::Unaware));

    if (!Press(Arena, EKeys::C, true) || !Tick(Arena, 1, Keep) || !Press(Arena, EKeys::C, false) || !Tick(Arena, 20, Keep) ||
        !TestFalse(TEXT("The hero stands to walk"), Hero->IsCrouched()))
        return false;
    Arena.PlaceHero(FVector(-1900.f, 0.f, 0.f), 0.f);
    if (!Tick(Arena, 30, Keep) || !Press(Arena, EKeys::W, true))
        return false;
    int32 Heard = 0;
    if (!Until(Arena, 300, Keep, [&]() { Heard = FMath::Max(Heard, Ears->AwarenessPermille()); return Hero->GetActorLocation().X >= -1450.f; }) ||
        !Press(Arena, EKeys::W, false))
        return false;
    AddInfo(FString::Printf(TEXT("Walk: the sentry's meter rose to %d permille"), Heard));
    TestTrue(TEXT("A walk over the same ground is heard"), Heard > 0);
    return Tick(Arena, 2, Keep);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraStealthRearTakedownTest,
    "SoraArena.Stealth.RearTakedown",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraStealthRearTakedownTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraStealthAutomation;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FArena Arena(*this, TEXT("StealthTakedown"));
    if (!Arena.Start())
        return false;
    USoraStealth* Zone = USoraStealth::Get(Arena.Get());
    if (!TestNotNull(TEXT("The stealth zone exists in a game world"), Zone))
        return false;
    const TSharedRef<FRecord> Log = Record(Arena.Get());
    FSoraStealthZone Rules;
    Rules.bRearTakedowns = true;
    Rules.bLethalDefault = false;
    Zone->BeginZone(Rules);
    ASoraPlayerCharacter* Hero = Arena.Hero();

    // Guards stand in a column facing east; the hero steps in behind each.
    ASoraEnemy* Knocked = Guard(Arena, TEXT("enforcer_rifle"), 30, FVector(0.f, 0.f, 0.f), 0.f);
    ASoraEnemy* Killed = Guard(Arena, TEXT("blade_retainer"), 31, FVector(0.f, -700.f, 0.f), 0.f);
    ASoraEnemy* Conscript = Guard(Arena, TEXT("bound_conscript"), 32, FVector(0.f, 700.f, 0.f), 0.f);
    TArray<ASoraEnemy*> Keep{Knocked, Killed, Conscript};
    if (!TestTrue(TEXT("Three guards spawn"), Knocked && Killed && Conscript) || !Tick(Arena, 2, Keep))
        return false;

    // No takedown from the front, on a drone, on a guard that knows, or outside a zone.
    ASoraEnemy* Facing = Guard(Arena, TEXT("enforcer_rifle"), 33, FVector(0.f, 1400.f, 0.f), 180.f);
    Arena.PlaceHero(FVector(-120.f, 1400.f, 0.f), 0.f);
    TestTrue(TEXT("No takedown on a guard facing the hero"), Facing && Zone->TakedownTarget(*Hero) == nullptr);
    if (Facing)
        Facing->Destroy();
    ASoraEnemy* Drone = Guard(Arena, TEXT("drone"), 34, FVector(0.f, 2100.f, 0.f), 0.f);
    Arena.PlaceHero(FVector(-120.f, 2100.f, 0.f), 0.f);
    TestTrue(TEXT("No takedown on a drone"), Drone && !Drone->CanBeTakenDown() && Zone->TakedownTarget(*Hero) == nullptr);
    if (Drone)
        Drone->Destroy();
    // Roused, a guard shouts; this one stands beyond a shout from the column.
    ASoraEnemy* Knowing = Guard(Arena, TEXT("enforcer_rifle"), 35, FVector(2400.f, -2200.f, 0.f), 0.f);
    Arena.PlaceHero(FVector(2280.f, -2200.f, 0.f), 0.f);
    if (ASoraEnemyController* Brain = FArena::Brain(Knowing))
        Brain->Rouse(FVector(2900.f, -2200.f, 0.f));
    TestTrue(TEXT("No takedown on an alerted guard"), Knowing && Zone->TakedownTarget(*Hero) == nullptr);
    if (Knowing)
        Knowing->Destroy();
    Arena.PlaceHero(FVector(-120.f, 0.f, 0.f), 0.f);
    Zone->EndZone();
    TestTrue(TEXT("No takedown outside a stealth zone"), Zone->TakedownTarget(*Hero) == nullptr);
    Zone->BeginZone(Rules);
    TestTrue(TEXT("Behind an unaware guard in the zone, the takedown is offered"), Zone->TakedownTarget(*Hero) == Knocked);
    TestTrue(TEXT("The HUD readout offers it, non-lethal by default"), Zone->Readout(*Hero).bTakedown && !Zone->Readout(*Hero).bLethalDefault);

    // A tap: 当て身. The guard is held, then out cold; the hero stands committed.
    const FVector HeroAt = Hero->GetActorLocation();
    if (!Press(Arena, EKeys::RightMouseButton, true) || !Press(Arena, EKeys::RightMouseButton, false) || !Tick(Arena, 1, Keep))
        return false;
    TestTrue(TEXT("The tap starts a takedown"), Zone->IsHeroBusy() && Knocked->IsSeized());
    TestFalse(TEXT("It is not a committed strike"), Hero->GetEquipment()->IsCommittedStrike());
    if (!Press(Arena, EKeys::W, true) || !Tick(Arena, 30, Keep) || !Press(Arena, EKeys::W, false))
        return false;
    TestTrue(TEXT("A tap knocks the guard out"), Knocked->IsUnconscious() && Knocked->IsBody() && !Knocked->IsAlive());
    TestEqual(TEXT("It is announced as knocked out"), Log->CueCount(Knocked, ESoraEnemyCue::KnockedOut), 1);
    TestEqual(TEXT("Nobody died"), Log->Died.Num(), 0);
    TestTrue(TEXT("The hero cannot walk off during the takedown"), FVector::Dist2D(Hero->GetActorLocation(), HeroAt) < 5.f);
    TestTrue(TEXT("The hero is still committed"), Zone->IsHeroBusy());
    if (!Tick(Arena, 70, Keep))
        return false;
    TestFalse(TEXT("After 1.5 s the hero is free again"), Zone->IsHeroBusy());
    if (!Tick(Arena, 180, Keep))
        return false;
    TestTrue(TEXT("The body stays where it fell"), IsValid(Knocked) && !Knocked->IsActorBeingDestroyed() && Knocked->IsBody());

    // A hold past 400 ms: the lethal thrust, whatever the retainer's poise.
    Arena.PlaceHero(FVector(-120.f, -700.f, 0.f), 0.f);
    AddInfo(FString::Printf(TEXT("Before the second takedown the retainer is %s"), Name(FArena::Brain(Killed)->State())));
    TestTrue(TEXT("Behind the retainer, the takedown is offered"), Zone->TakedownTarget(*Hero) == Killed);
    if (!Press(Arena, EKeys::RightMouseButton, true) || !Tick(Arena, 30, Keep) || !Press(Arena, EKeys::RightMouseButton, false) ||
        !Tick(Arena, 2, Keep))
        return false;
    TestTrue(TEXT("A hold kills"), !Killed->IsAlive() && !Killed->IsUnconscious() && Killed->IsBody());
    TestEqual(TEXT("One death, dealt by the hero"), Log->Died.Num(), 1);
    TestTrue(TEXT("The death is the retainer's"), Log->Died.Num() == 1 && Log->Died[0].Victim == Killed && Log->Died[0].Killer == Hero);
    if (!Tick(Arena, 120, Keep))
        return false;
    TestFalse(TEXT("The lethal takedown takes 2.2 s"), Zone->IsHeroBusy());

    // A conscript, even on a hold, is struck with the back of the blade.
    Arena.PlaceHero(FVector(-120.f, 700.f, 0.f), 0.f);
    TestTrue(TEXT("The HUD names the 峰打ち"), Zone->Readout(*Hero).bTakedownSubdues);
    if (!Press(Arena, EKeys::RightMouseButton, true) || !Tick(Arena, 30, Keep) || !Press(Arena, EKeys::RightMouseButton, false) ||
        !Tick(Arena, 2, Keep))
        return false;
    TestTrue(TEXT("The conscript is knocked down, not killed"), Conscript->IsSubdued());
    TestEqual(TEXT("Still only one death"), Log->Died.Num(), 1);

    // The scuffle is heard close by: a guard two metres from the next takedown wonders.
    if (!Tick(Arena, 100, Keep))
        return false;
    ASoraEnemy* Victim = Guard(Arena, TEXT("enforcer_rifle"), 36, FVector(-1500.f, 0.f, 0.f), 0.f);
    ASoraEnemy* Neighbour = Guard(Arena, TEXT("enforcer_rifle"), 37, FVector(-1440.f, 160.f, 0.f), 90.f);
    ASoraEnemy* Distant = Guard(Arena, TEXT("enforcer_rifle"), 38, FVector(-1440.f, 1060.f, 0.f), 90.f);
    Keep.Append({Victim, Neighbour, Distant});
    Arena.PlaceHero(FVector(-1620.f, 0.f, 0.f), 0.f);
    if (!TestTrue(TEXT("A victim and two listeners spawn"), Victim && Neighbour && Distant) || !Tick(Arena, 2, Keep))
        return false;
    AddInfo(FString::Printf(TEXT("The victim is %s at (%.0f, %.0f, %.0f); the hero at (%.0f, %.0f, %.0f)"), Name(FArena::Brain(Victim)->State()),
        Victim->GetActorLocation().X, Victim->GetActorLocation().Y, Victim->GetActorLocation().Z,
        Hero->GetActorLocation().X, Hero->GetActorLocation().Y, Hero->GetActorLocation().Z));
    if (!TestTrue(TEXT("Behind the victim, the takedown is offered"), Zone->TakedownTarget(*Hero) == Victim))
        return false;
    if (!Press(Arena, EKeys::RightMouseButton, true) || !Press(Arena, EKeys::RightMouseButton, false) || !Tick(Arena, 28, Keep))
        return false;
    const EState Near = FArena::Brain(Neighbour)->State();
    const EState Far = FArena::Brain(Distant)->State();
    AddInfo(FString::Printf(TEXT("After the takedown the neighbour is %s, the distant guard %s"), Name(Near), Name(Far)));
    TestTrue(TEXT("The victim is out"), Victim->IsUnconscious());
    TestTrue(TEXT("The neighbour hears the scuffle"), Near != EState::Unaware);
    TestEqual(TEXT("A guard nine metres off does not"), static_cast<int32>(Far), static_cast<int32>(EState::Unaware));
    return Tick(Arena, 2, Keep);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraStealthBodyDiscoveryTest,
    "SoraArena.Stealth.BodyDiscovery",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraStealthBodyDiscoveryTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraStealthAutomation;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FArena Arena(*this, TEXT("StealthBodies"));
    if (!Arena.Start())
        return false;
    USoraStealth* Zone = USoraStealth::Get(Arena.Get());
    if (!TestNotNull(TEXT("The stealth zone exists in a game world"), Zone))
        return false;
    const TSharedRef<FRecord> Log = Record(Arena.Get());
    Zone->BeginZone(FSoraStealthZone());
    ASoraPlayerCharacter* Hero = Arena.Hero();

    // A guard out cold on the road, and the hero beside it.
    ASoraEnemy* Body = Guard(Arena, TEXT("enforcer_rifle"), 40, FVector::ZeroVector, 0.f);
    TArray<ASoraEnemy*> Keep{Body};
    Arena.PlaceHero(FVector(-110.f, 0.f, 0.f), 0.f);
    if (!TestNotNull(TEXT("A guard spawns"), Body) || !Tick(Arena, 2, Keep))
        return false;
    Body->KnockOut(Hero);
    if (!Tick(Arena, 2, Keep))
        return false;
    TestTrue(TEXT("It is a body"), Body->IsBody() && Zone->UnfoundBodies().Contains(Body));
    TestTrue(TEXT("Facing it within reach, the hero may drag it"), Zone->DragTarget(*Hero) == Body && Zone->Readout(*Hero).bDrag);

    // Hold E and back away: the body follows at half pace; let go and it stays.
    const FVector Start = Body->GetActorLocation();
    if (!Press(Arena, EKeys::E, true) || !Tick(Arena, 1, Keep))
        return false;
    TestTrue(TEXT("Holding E drags the body"), Zone->IsDragging());
    if (!Press(Arena, EKeys::S, true))
        return false;
    float Fastest = 0.f;
    for (int32 Frame = 0; Frame < 90; ++Frame)
    {
        if (!Tick(Arena, 1, Keep))
            return false;
        Fastest = FMath::Max(Fastest, Hero->GetVelocity().Size2D());
    }
    const float Moved = FVector::Dist2D(Body->GetActorLocation(), Start);
    const float Rope = FVector::Dist2D(Body->GetActorLocation(), Hero->GetActorLocation());
    AddInfo(FString::Printf(TEXT("Dragging: the body moved %.0f cm on a %.0f cm rope; the hero's pace %.0f cm/s"), Moved, Rope, Fastest));
    TestTrue(TEXT("The body is dragged along"), Moved > 250.f && Rope < 110.f);
    TestTrue(TEXT("Dragging halves the hero's pace"), Fastest > 150.f && Fastest < 300.f);
    if (!Press(Arena, EKeys::E, false) || !Tick(Arena, 1, Keep))
        return false;
    TestFalse(TEXT("Letting go of E drops the body"), Zone->IsDragging());
    const FVector Dropped = Body->GetActorLocation();
    if (!Tick(Arena, 30, Keep) || !Press(Arena, EKeys::S, false))
        return false;
    TestTrue(TEXT("A dropped body stays put"), FVector::Dist2D(Body->GetActorLocation(), Dropped) < 1.f);

    // A sentry nine metres off turns out to face the body; another guard far
    // across the road cannot see it. The hero waits behind the sentry.
    Arena.PlaceHero(FVector(Dropped.X + 2000.f, 400.f, 0.f), 0.f);
    ASoraEnemy* Finder = Guard(Arena, TEXT("enforcer_rifle"), 41, FVector(Dropped.X + 900.f, 0.f, 0.f), 180.f);
    ASoraEnemy* Across = Guard(Arena, TEXT("enforcer_rifle"), 42, FVector(Dropped.X + 900.f, -2400.f, 0.f), -90.f);
    Keep.Append({Finder, Across});
    ASoraEnemyController* FinderBrain = FArena::Brain(Finder);
    ASoraEnemyController* AcrossBrain = FArena::Brain(Across);
    if (!TestTrue(TEXT("Two guards spawn"), FinderBrain && AcrossBrain))
        return false;
    int32 Frames = 0;
    if (!Until(Arena, 120, Keep, [&]() { ++Frames; return Log->Bodies.Num() > 0; }))
        return false;
    AddInfo(FString::Printf(TEXT("The body was found after %d frames; the finder is %s, the far guard %s"), Frames,
        Name(FinderBrain->State()), Name(AcrossBrain->State())));
    TestEqual(TEXT("The body is found once"), Log->Bodies.Num(), 1);
    TestTrue(TEXT("By the sentry facing it"), Log->Bodies.Num() == 1 && Log->Bodies[0].Key == Body && Log->Bodies[0].Value == Finder);
    TestEqual(TEXT("The finder calls out the knocked-out guard"), Log->CueCount(Finder, ESoraEnemyCue::BodyFound), 1);
    TestTrue(TEXT("The call names an unconscious body"), Log->Cues.ContainsByPredicate([Finder](const FSoraEnemyCueEvent& E)
        { return E.Enemy == Finder && E.Cue == ESoraEnemyCue::BodyFound && E.Detail == FName(TEXT("unconscious")); }));
    TestEqual(TEXT("The finder searches"), static_cast<int32>(FinderBrain->State()), static_cast<int32>(EState::Search));
    TestTrue(TEXT("Around the body"), FVector::Dist2D(FinderBrain->LastKnownLocation(), Dropped) < 50.f);
    TestEqual(TEXT("The whole zone searches"), static_cast<int32>(AcrossBrain->State()), static_cast<int32>(EState::Search));
    TestTrue(TEXT("Every guard stays wary"), FinderBrain->IsWary() && AcrossBrain->IsWary());
    TestTrue(TEXT("A found body is not a detection"), !Zone->IsDetected() && Log->Detected.IsEmpty());
    TestFalse(TEXT("A found body is not found again"), Zone->UnfoundBodies().Contains(Body));
    return Tick(Arena, 2, Keep);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraStealthAlarmLecternTest,
    "SoraArena.Stealth.AlarmLectern",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraStealthAlarmLecternTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraStealthAutomation;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FArena Arena(*this, TEXT("StealthAlarm"));
    if (!Arena.Start())
        return false;
    USoraStealth* Zone = USoraStealth::Get(Arena.Get());
    if (!TestNotNull(TEXT("The stealth zone exists in a game world"), Zone))
        return false;
    const TSharedRef<FRecord> Log = Record(Arena.Get());
    FSoraStealthZone Rules;
    Rules.OnDetected = SoraStealthRules::EOnDetected::Reinforce;
    const FVector Lectern(700.f, 300.f, 90.f);
    ASoraPlayerCharacter* Hero = Arena.Hero();

    // An auditor at its desk sees the hero; a trooper stands beyond a shout.
    Zone->BeginZone(Rules);
    Zone->AddAlarmPoint(Lectern);
    Arena.PlaceHero(FVector(-600.f, 0.f, 0.f), 0.f);
    ASoraEnemy* Auditor = Guard(Arena, TEXT("auditor"), 50, FVector::ZeroVector, 180.f);
    ASoraEnemy* Trooper = Guard(Arena, TEXT("enforcer_rifle"), 51, FVector(-400.f, 2400.f, 0.f), 90.f);
    TArray<ASoraEnemy*> Keep{Auditor, Trooper};
    ASoraEnemyController* TrooperBrain = FArena::Brain(Trooper);
    if (!TestTrue(TEXT("An auditor and a trooper spawn"), Auditor && TrooperBrain) || !Until(Arena, 60, Keep, [&]() { return !Log->Detected.IsEmpty(); }))
        return false;
    TestEqual(TEXT("The auditor's detection is announced once"), Log->Detected.Num(), 1);
    TestTrue(TEXT("With the zone's answer: reinforcements"), Log->Detected.Num() == 1 &&
        Log->Detected[0].By.Get() == Auditor && Log->Detected[0].Response == SoraStealthRules::EOnDetected::Reinforce);
    TestTrue(TEXT("Its shout does not reach the trooper beyond eighteen metres"),
        FVector::Dist(Auditor->GetActorLocation(), Trooper->GetActorLocation()) > SoraStealthRules::NoiseRadiusCm(SoraStealthRules::ENoise::Callout));
    if (!Tick(Arena, 20, Keep))
        return false;
    TestEqual(TEXT("On its way to the lectern, no alarm yet"), Log->Alarms.Num(), 0);
    TestEqual(TEXT("The trooper has not heard"), static_cast<int32>(TrooperBrain->State()), static_cast<int32>(EState::Unaware));
    int32 Frames = 0;
    if (!Until(Arena, 600, Keep, [&]() { ++Frames; return !Log->Alarms.IsEmpty(); }))
        return false;
    AddInfo(FString::Printf(TEXT("The auditor raised the alarm %d frames later, %.0f cm from the lectern; the trooper is %s"), Frames,
        FVector::Dist2D(Auditor->GetActorLocation(), Lectern), Name(TrooperBrain->State())));
    TestEqual(TEXT("At the lectern the auditor raises the zone's alarm once"), Log->Alarms.Num(), 1);
    TestTrue(TEXT("It ran there"), FVector::Dist2D(Auditor->GetActorLocation(), Lectern) <= 120.f);
    TestTrue(TEXT("The alarm cue names the lectern"), Log->Cues.ContainsByPredicate([Auditor](const FSoraEnemyCueEvent& E)
        { return E.Enemy == Auditor && E.Cue == ESoraEnemyCue::Alarm && E.Detail == FName(TEXT("lectern")); }));
    TestTrue(TEXT("The alarm reaches the trooper"), TrooperBrain->State() == EState::Alert || TrooperBrain->State() == EState::Combat);
    TestTrue(TEXT("It knows where the hero was"), FVector::Dist2D(TrooperBrain->LastKnownLocation(), Hero->GetActorLocation()) < 300.f);
    TestTrue(TEXT("And stays wary"), TrooperBrain->IsWary());
    TestTrue(TEXT("The zone and the HUD know"), Zone->IsAlarmRaised() && Zone->Readout(*Hero).bAlarm);
    TestEqual(TEXT("Still one detection"), Log->Detected.Num(), 1);

    // Again, but the hero cuts the auditor down on its way: no alarm at all.
    for (ASoraEnemy* Enemy : Keep)
        Enemy->Destroy();
    Log->Detected.Reset();
    Log->Alarms.Reset();
    Zone->BeginZone(Rules);
    Zone->AddAlarmPoint(Lectern);
    ASoraEnemy* Runner = Guard(Arena, TEXT("auditor"), 52, FVector::ZeroVector, 180.f);
    ASoraEnemy* Sentry = Guard(Arena, TEXT("enforcer_rifle"), 53, FVector(-400.f, 2400.f, 0.f), 90.f);
    Keep = {Runner, Sentry};
    if (!TestTrue(TEXT("A second auditor and trooper spawn"), Runner && Sentry) ||
        !Until(Arena, 60, Keep, [&]() { return !Log->Detected.IsEmpty(); }) || !Tick(Arena, 20, Keep))
        return false;
    TestTrue(TEXT("It is running"), FArena::Brain(Runner)->State() != EState::Unaware && Log->Alarms.IsEmpty());
    FHitResult Trace;
    Trace.ImpactPoint = Runner->GetActorLocation();
    FSoraHit Hit = FSoraHit::Ranged(Hero->GetActorLocation(), 1);
    SoraDamage::Strike(Runner, 1000.f, Hit, FVector::ForwardVector, Trace, Hero->GetController(), Hero);
    TestFalse(TEXT("The hero stops the auditor"), Runner->IsAlive());
    if (!Tick(Arena, 300, Keep))
        return false;
    TestTrue(TEXT("Stopped before the lectern, it raises no alarm"), Log->Alarms.IsEmpty() && !Zone->IsAlarmRaised());
    TestEqual(TEXT("The trooper never hears of it"), static_cast<int32>(FArena::Brain(Sentry)->State()), static_cast<int32>(EState::Unaware));
    return Tick(Arena, 2, Keep);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraStealthDetectionTest,
    "SoraArena.Stealth.Detection",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraStealthDetectionTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraStealthAutomation;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FArena Arena(*this, TEXT("StealthDetection"));
    if (!Arena.Start())
        return false;
    USoraStealth* Zone = USoraStealth::Get(Arena.Get());
    if (!TestNotNull(TEXT("The stealth zone exists in a game world"), Zone))
        return false;
    const TSharedRef<FRecord> Log = Record(Arena.Get());
    ASoraPlayerCharacter* Hero = Arena.Hero();

    // A restart_checkpoint zone on Easy: the guard sees the hero, and the
    // zone answers with combat, once.
    FSoraStealthZone Rules;
    Rules.OnDetected = SoraStealthRules::EOnDetected::Restart;
    Rules.Difficulty = SoraStealthRules::EDifficulty::Easy;
    Zone->BeginZone(Rules);
    Arena.PlaceHero(FVector(-1200.f, 0.f, 0.f), 0.f);
    ASoraEnemy* Sentry = Guard(Arena, TEXT("enforcer_rifle"), 60, FVector::ZeroVector, 0.f);
    ASoraEnemyController* Brain = FArena::Brain(Sentry);
    TArray<ASoraEnemy*> Keep{Sentry};
    if (!TestNotNull(TEXT("A sentry spawns"), Brain) || !Tick(Arena, 10, Keep))
        return false;
    FSoraStealthReadout Calm = Zone->Readout(*Hero);
    TestTrue(TEXT("Unseen: the readout is calm and empty"), Calm.bZone && Calm.Worst == EState::Unaware && Calm.MeterPermille == 0 &&
        Calm.Marks.IsEmpty() && !Calm.bSeen);
    TestFalse(TEXT("Work under guard goes on"), Zone->IsWorkPaused());
    Arena.PlaceHero(FVector(900.f, 0.f, 0.f), 180.f);
    int32 MostMarks = 0;
    int32 FirstMeter = 0;
    if (!Until(Arena, 120, Keep, [&]()
        {
            const FSoraStealthReadout Now = Zone->Readout(*Hero);
            MostMarks = FMath::Max(MostMarks, Now.Marks.Num());
            if (FirstMeter == 0 && Now.MeterPermille > 0 && Now.Worst != EState::Combat)
                FirstMeter = Now.MeterPermille;
            return !Log->Detected.IsEmpty();
        }))
        return false;
    AddInfo(FString::Printf(TEXT("Detected: the meter first read %d permille; the sentry is %s"), FirstMeter, Name(Brain->State())));
    TestEqual(TEXT("Detection is announced once"), Log->Detected.Num(), 1);
    TestTrue(TEXT("On Easy a restart zone falls back to combat"),
        Log->Detected.Num() == 1 && Log->Detected[0].Response == SoraStealthRules::EOnDetected::Combat && Log->Detected[0].By.Get() == Sentry);
    TestTrue(TEXT("The meter filled over frames before detection"), FirstMeter > 0 && FirstMeter < 1000);
    const FSoraStealthReadout Seen = Zone->Readout(*Hero);
    TestTrue(TEXT("The readout marks the sentry, full"), MostMarks == 1 && Seen.Marks.Num() == 1 && Seen.Marks[0].Enemy.Get() == Sentry &&
        Seen.MeterPermille == 1000 && Seen.bSeen && Seen.bDetected);
    TestTrue(TEXT("Work under guard pauses"), Zone->IsWorkPaused());
    if (!Tick(Arena, 60, Keep))
        return false;
    TestEqual(TEXT("A fight that goes on is not detected again"), Log->Detected.Num(), 1);

    // The same zone on Normal restarts from the checkpoint.
    Sentry->Destroy();
    Log->Detected.Reset();
    Rules.Difficulty = SoraStealthRules::EDifficulty::Normal;
    Zone->BeginZone(Rules);
    TestFalse(TEXT("A new zone starts undetected"), Zone->IsDetected());
    Arena.PlaceHero(FVector(-1200.f, 0.f, 0.f), 0.f);
    ASoraEnemy* Second = Guard(Arena, TEXT("enforcer_rifle"), 61, FVector::ZeroVector, 0.f);
    Keep = {Second};
    if (!TestNotNull(TEXT("A second sentry spawns"), Second) || !Tick(Arena, 5, Keep))
        return false;
    Arena.PlaceHero(FVector(900.f, 0.f, 0.f), 180.f);
    if (!Until(Arena, 120, Keep, [&]() { return !Log->Detected.IsEmpty(); }))
        return false;
    TestTrue(TEXT("On Normal it restarts from the checkpoint"),
        Log->Detected.Num() == 1 && Log->Detected[0].Response == SoraStealthRules::EOnDetected::Restart);

    // Carryover: after a detection the next zone's guards start suspicious and
    // wary, both those already posted and those posted after it opens.
    Second->Destroy();
    Arena.PlaceHero(FVector(-2500.f, 0.f, 0.f), 0.f);
    ASoraEnemy* Before = Guard(Arena, TEXT("enforcer_rifle"), 62, FVector(0.f, 600.f, 0.f), 0.f);
    Keep = {Before};
    if (!TestNotNull(TEXT("A guard is posted"), Before) || !Tick(Arena, 2, Keep))
        return false;
    FSoraStealthZone Next;
    Next.bCarriedOver = true;
    Zone->BeginZone(Next);
    ASoraEnemy* After = Guard(Arena, TEXT("enforcer_rifle"), 63, FVector(0.f, -600.f, 0.f), 0.f);
    Keep.Add(After);
    if (!TestNotNull(TEXT("A guard is posted after the zone opens"), After) || !Tick(Arena, 1, Keep))
        return false;
    TestTrue(TEXT("The guard posted before starts suspicious and wary"),
        FArena::Brain(Before)->State() == EState::Suspicious && FArena::Brain(Before)->IsWary());
    TestTrue(TEXT("So does the guard posted after"), FArena::Brain(After)->State() == EState::Suspicious && FArena::Brain(After)->IsWary());
    // A hunting wave never obeys a zone: it starts alert and its detections do not count.
    ASoraEnemy* Hunter = Arena.Spawn(64, FVector(0.f, 1800.f, 0.f), 180.f);
    Keep.Add(Hunter);
    if (!Tick(Arena, 1, Keep))
        return false;
    TestTrue(TEXT("A hunter is not a guard"), Hunter && !FArena::Brain(Hunter)->IsGuard());
    TestFalse(TEXT("A hunter's alert is not a detection"), Zone->IsDetected());
    return Tick(Arena, 2, Keep);
}
#endif
