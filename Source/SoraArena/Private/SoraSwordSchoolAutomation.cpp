#include "SoraGameMode.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Combat/SoraDamage.h"
#include "Combat/SoraDefense.h"
#include "Combat/SoraEnemyCatalog.h"
#include "SoraCatalog.h"
#include "SoraCombatRules.h"
#include "SoraEnemyTestArena.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameEvents.h"
#include "SoraHistoricalArms.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/DamageType.h"
#include "Misc/ScopeExit.h"

// The sword school's hand in real game worlds (story bible §3.2), each
// driven through the project's key mappings: the Sheathe key puts the blade
// away and draws it again (mutō-dori needs the sheathed hand); Left or Right
// with Jump after an awase rolls to the opponent's flank (転); a guard held
// after a defeat restores stamina (残心); and the maai read (水月) lights
// only at the drawn blade's cutting distance.
namespace SoraSwordSchool
{
using SoraEnemyTest::FArena;
namespace Rules = SoraCombatRules;

bool Press(FArena& Arena, const FKey& Key, bool bDown)
{
    return Arena.World->InjectKey(Key, bDown ? IE_Pressed : IE_Released);
}

bool Tap(FArena& Arena, const FKey& Key)
{
    return Press(Arena, Key, true) && Press(Arena, Key, false) && Arena.Tick(1);
}

// Each case keeps only the opponents it placed: the chapter's director
// answers a defeat with a fresh hunter, which is removed before every frame.
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
    return Done();
}

// Nyaakoto holds a catalog weapon, drawn, with a rested guard.
bool Arm(FArena& Arena, int32 WeaponId)
{
    ASoraPlayerCharacter* Hero = Arena.Hero();
    Hero->GetEquipment()->Hold(WeaponId);
    Hero->RebuildWeapon();
    return Until(Arena, 600, {}, [Hero]() { return Hero->GetEquipment()->GuardReserve() >= 100.f; });
}

float Seconds(const FArena& Arena)
{
    return Arena.Get()->GetTimeSeconds();
}

// Meets Attacker's next blow with a guard pressed in its last 200 ms: an
// awase. Returns once the parry is announced, the guard still held.
bool Awase(FArena& Arena, ASoraEnemy& Attacker, const TArray<ASoraEnemy*>& Keep, int32& Parries)
{
    const int32 Before = Parries;
    bool bRaised = false;
    for (int32 Index = 0; Index < 900 && Parries == Before; ++Index)
    {
        if (!bRaised && Attacker.IsWindingUp() && Attacker.CurrentAttack() &&
            (1.f - Attacker.WindupProgress()) * Attacker.CurrentAttack()->WindupMs <= 200.f)
        {
            if (!Press(Arena, EKeys::LeftControl, true))
                return false;
            bRaised = true;
        }
        if (!Tick(Arena, 1, Keep))
            return false;
    }
    return Parries > Before;
}

// The angle, in degrees, the hero has travelled round Center since From.
float Round(const FVector& Center, const FVector& From, const FVector& To)
{
    const FVector A = (From - Center).GetSafeNormal2D(), B = (To - Center).GetSafeNormal2D();
    return FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(FVector::DotProduct(A, B), -1.f, 1.f)));
}
} // namespace SoraSwordSchool

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraSheatheKeyTest,
    "SoraArena.Combat.SheatheKey",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraSheatheKeyTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraSwordSchool;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FArena Arena(*this, TEXT("SheatheKey"));
    if (!Arena.Start() || !Arm(Arena, 0))
        return false;
    ASoraPlayerCharacter* Hero = Arena.Hero();
    USoraEquipmentComponent* Kit = Hero->GetEquipment();
    TestFalse(TEXT("The katana starts drawn"), Kit->IsSheathing());
    // 納刀 on V: the blade goes back over 700 ms.
    if (!Tap(Arena, EKeys::V))
        return false;
    TestTrue(TEXT("V puts the blade back"), Kit->IsSheathing());
    TestFalse(TEXT("Sheathing takes its time"), Kit->IsSheathed());
    const float Began = Seconds(Arena);
    if (!Until(Arena, 90, {}, [Kit]() { return Kit->IsSheathed(); }))
        return TestTrue(TEXT("The blade is sheathed"), false);
    TestTrue(TEXT("It is sheathed after 700 ms"), (Seconds(Arena) - Began) * 1000.f >= Rules::SheatheMs - 17.f);
    // A sheathed hand cuts nothing: an attack press draws instead (抜刀).
    if (!Tap(Arena, EKeys::LeftMouseButton))
        return false;
    TestFalse(TEXT("The attack press does not cut"), Kit->IsCommittedStrike());
    TestFalse(TEXT("It draws the blade"), Kit->IsSheathing());
    if (!Tick(Arena, 30, {}) || !Tap(Arena, EKeys::V) || !Tap(Arena, EKeys::RightMouseButton))
        return false;
    TestFalse(TEXT("The melee press draws too, without a cut"), Kit->IsSheathing() || Kit->IsCommittedStrike());
    // The pad: d-pad up sheathes and draws.
    if (!Tap(Arena, EKeys::Gamepad_DPad_Up))
        return false;
    TestTrue(TEXT("D-pad up sheathes"), Kit->IsSheathing());
    if (!Tap(Arena, EKeys::Gamepad_DPad_Up))
        return false;
    TestFalse(TEXT("and draws again"), Kit->IsSheathing());
    // V toggles back again, and a weapon change always comes out drawn.
    if (!Tap(Arena, EKeys::V) || !Tap(Arena, EKeys::V))
        return false;
    TestFalse(TEXT("V draws a sheathed blade"), Kit->IsSheathing());
    if (!Tap(Arena, EKeys::V) || !Tick(Arena, 20, {}) || !Arena.World->TakeUpArm(1) || !Tick(Arena, 20, {}))
        return false;
    TestTrue(TEXT("The carbine comes out drawn"), Hero->WeaponId == 1 && !Kit->IsSheathing());
    if (!Tap(Arena, EKeys::V))
        return false;
    TestFalse(TEXT("Only a blade goes into a scabbard"), Kit->IsSheathing());
    return Arena.Tick(2);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraMarobashiAfterAwaseTest,
    "SoraArena.Combat.MarobashiAfterAwase",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraMarobashiAfterAwaseTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraSwordSchool;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FArena Arena(*this, TEXT("MarobashiAfterAwase"));
    if (!Arena.Start() || !Arm(Arena, 0))
        return false;
    ASoraPlayerCharacter* Hero = Arena.Hero();
    USoraEquipmentComponent* Kit = Hero->GetEquipment();
    USoraGameEvents* Events = USoraGameEvents::Get(Arena.Get());
    if (!TestNotNull(TEXT("The event bus exists"), Events))
        return false;
    int32 Parries = 0;
    TArray<FSoraMarobashiEvent> Steps;
    const FDelegateHandle ParryHandle = Events->OnParried.AddLambda([&Parries](const FSoraDefenseEvent&) { ++Parries; });
    const FDelegateHandle StepHandle = Events->OnMarobashi.AddLambda([&Steps](const FSoraMarobashiEvent& E) { Steps.Add(E); });
    ON_SCOPE_EXIT
    {
        Events->OnParried.Remove(ParryHandle);
        Events->OnMarobashi.Remove(StepHandle);
    };
    Arena.PlaceHero(FVector::ZeroVector, 0.f);
    ASoraEnemy* Retainer = Arena.SpawnKind(TEXT("blade_retainer"), 0, FVector(160.f, 0.f, 0.f), 180.f);
    if (!TestNotNull(TEXT("A blade retainer spawns"), Retainer))
        return false;
    const TArray<ASoraEnemy*> Keep{Retainer};
    TestNull(TEXT("No 転 is open before an awase"), SoraDefense::MarobashiTarget(*Hero));

    // Awase, then Right with Jump inside 400 ms: the hero rolls to its flank.
    if (!TestTrue(TEXT("The retainer's cut is met with awase"), Awase(Arena, *Retainer, Keep, Parries)))
        return false;
    const float ParriedAt = Seconds(Arena);
    TestTrue(TEXT("The awase opens 転"), SoraDefense::MarobashiTarget(*Hero) == Retainer);
    const FVector Center = Retainer->GetActorLocation();
    const FVector From = Hero->GetActorLocation();
    const float Yaw = Retainer->GetActorRotation().Yaw;
    if (!Press(Arena, EKeys::LeftControl, false) || !Press(Arena, EKeys::D, true) || !Press(Arena, EKeys::SpaceBar, true) ||
        !Tick(Arena, 1, Keep) || !Press(Arena, EKeys::SpaceBar, false) || !Press(Arena, EKeys::D, false))
        return false;
    TestTrue(TEXT("The step came inside the window"), (Seconds(Arena) - ParriedAt) * 1000.f <= Rules::MarobashiWindowMs);
    TestEqual(TEXT("One 転 is announced"), Steps.Num(), 1);
    TestTrue(TEXT("after the awase, on the retainer"), Steps.Num() == 1 && Steps[0].bAfterAwase && Steps[0].Opponent == Retainer);
    TestTrue(TEXT("The retainer cannot turn after him"), Retainer->IsTurnLocked());
    if (!Until(Arena, 60, Keep, [Kit]() { return !Kit->IsStepping(); }))
        return TestTrue(TEXT("The step ends"), false);
    const FVector To = Hero->GetActorLocation();
    const float Travelled = Round(Center, From, To);
    AddInfo(FString::Printf(TEXT("The step went %.0f degrees round the retainer, from (%.0f, %.0f) to (%.0f, %.0f)"),
        Travelled, From.X, From.Y, To.X, To.Y));
    TestTrue(TEXT("It rounds the retainer toward the side pressed"), To.Y > From.Y + 100.f);
    TestTrue(TEXT("by the 転 arc, no more than its step"), Travelled >= 55.f && Travelled <= Rules::MarobashiArcDeg + 2.f &&
        FVector::Dist2D(From, To) <= Rules::MarobashiStepCm + 5.f);
    TestTrue(TEXT("at the distance it began from"), FMath::Abs(FVector::Dist2D(To, Center) - FVector::Dist2D(From, Center)) < 15.f);
    TestTrue(TEXT("still facing the retainer"),
        FVector::DotProduct(Hero->GetActorForwardVector().GetSafeNormal2D(), (Center - To).GetSafeNormal2D()) > .95f);
    TestTrue(TEXT("It stands at his flank"), SoraDamage::FacingMilli(*Retainer, To) < Rules::FrontMilli);
    TestTrue(TEXT("and has not turned"), FMath::Abs(FMath::FindDeltaAngleDegrees(Retainer->GetActorRotation().Yaw, Yaw)) < 1.f);
    TestFalse(TEXT("The step is not a jump"), Hero->GetCharacterMovement()->IsFalling());

    // Too late: 450 ms after the next awase, Right with Jump is only a jump.
    if (!Until(Arena, 300, Keep, [Retainer]() { return !Retainer->IsStaggered() && !Retainer->IsTurnLocked(); }))
        return TestTrue(TEXT("The retainer recovers"), false);
    Arena.PlaceHero(Retainer->GetActorLocation() + Retainer->GetActorForwardVector() * 160.f, Retainer->GetActorRotation().Yaw + 180.f);
    if (!Until(Arena, 600, Keep, [Kit]() { return Kit->GuardReserve() >= 100.f; }) ||
        !TestTrue(TEXT("The next cut is met with awase"), Awase(Arena, *Retainer, Keep, Parries)))
        return false;
    const float Again = Seconds(Arena);
    if (!Press(Arena, EKeys::LeftControl, false) ||
        !Until(Arena, 300, Keep, [&]() { return (Seconds(Arena) - Again) * 1000.f > Rules::MarobashiWindowMs + 50.f; }))
        return false;
    TestNull(TEXT("The window has closed"), SoraDefense::MarobashiTarget(*Hero));
    const FVector Before = Hero->GetActorLocation();
    if (!Press(Arena, EKeys::D, true) || !Press(Arena, EKeys::SpaceBar, true) || !Tick(Arena, 1, Keep) ||
        !Press(Arena, EKeys::SpaceBar, false))
        return false;
    TestEqual(TEXT("A late step is no 転"), Steps.Num(), 1);
    TestTrue(TEXT("It is an ordinary jump"), Hero->GetCharacterMovement()->IsFalling());
    const bool bLanded = Until(Arena, 120, Keep, [Hero]() { return !Hero->GetCharacterMovement()->IsFalling(); });
    TestTrue(TEXT("which lands"), bLanded);
    AddInfo(FString::Printf(TEXT("The late jump moved the hero %.0f cm"), FVector::Dist2D(Before, Hero->GetActorLocation())));
    return Press(Arena, EKeys::D, false) && Arena.Tick(2);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraZanshinTest,
    "SoraArena.Combat.Zanshin",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraZanshinTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraSwordSchool;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FArena Arena(*this, TEXT("Zanshin"));
    if (!Arena.Start() || !Arm(Arena, 0))
        return false;
    ASoraPlayerCharacter* Hero = Arena.Hero();
    USoraEquipmentComponent* Kit = Hero->GetEquipment();
    Arena.PlaceHero(FVector::ZeroVector, 0.f);
    const auto Fell = [&](int32 Slot)
    {
        ASoraEnemy* Foe = Arena.SpawnKind(TEXT("enforcer_rifle"), Slot, FVector(1500.f, 600.f * Slot, 0.f), 180.f);
        if (Foe)
            UGameplayStatics::ApplyDamage(Foe, Foe->Health, Hero->GetController(), Hero, UDamageType::StaticClass());
        return Foe && !Foe->IsAlive();
    };
    // 残心: after a defeat the guard is held half a second, at no cost, and
    // gives back fifteen.
    Kit->SpendGuard(50.f);
    const float Spent = Kit->GuardReserve();
    const float Restored = Kit->LastZanshinAt();
    if (!TestTrue(TEXT("The hero fells an enforcer"), Fell(1)) || !Press(Arena, EKeys::LeftControl, true))
        return false;
    const float Raised = Seconds(Arena);
    if (!Until(Arena, 60, {}, [&]() { return Kit->LastZanshinAt() != Restored; }))
        return TestTrue(TEXT("Zanshin restores the guard"), false);
    const float HeldMs = (Seconds(Arena) - Raised) * 1000.f;
    AddInfo(FString::Printf(TEXT("Zanshin after %.0f ms of guard: %.1f -> %.1f"), HeldMs, Spent, Kit->GuardReserve()));
    TestTrue(TEXT("after half a second of guard"), HeldMs >= Rules::ZanshinHoldMs - 1.f && HeldMs <= Rules::ZanshinHoldMs + 34.f);
    TestTrue(TEXT("by fifteen, the hold itself free"), FMath::Abs(Kit->GuardReserve() - (Spent + Rules::ZanshinStamina)) < 1.f);
    // Once only: the guard held on drains as ever.
    const float After = Kit->GuardReserve();
    if (!Tick(Arena, 60, {}))
        return false;
    TestTrue(TEXT("Once only; holding on drains"), Kit->GuardReserve() < After - 20.f);
    if (!Press(Arena, EKeys::LeftControl, false) || !Until(Arena, 600, {}, [Kit]() { return Kit->GuardReserve() >= 100.f; }))
        return false;
    // Too late: a guard raised three seconds after a defeat restores nothing.
    const float Before = Kit->LastZanshinAt();
    if (!TestTrue(TEXT("The hero fells another"), Fell(2)) || !Tick(Arena, 180, {}))
        return false;
    Kit->SpendGuard(50.f);
    if (!Press(Arena, EKeys::LeftControl, true) || !Tick(Arena, 45, {}) || !Press(Arena, EKeys::LeftControl, false))
        return false;
    TestEqual(TEXT("A late guard restores nothing"), Kit->LastZanshinAt(), Before);
    TestTrue(TEXT("and drains as ever"), Kit->GuardReserve() < 50.f);
    return Arena.Tick(2);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraMaaiTest,
    "SoraArena.Combat.Maai",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraMaaiTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraSwordSchool;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FArena Arena(*this, TEXT("Maai"));
    if (!Arena.Start() || !Arm(Arena, 0))
        return false;
    ASoraPlayerCharacter* Hero = Arena.Hero();
    USoraEquipmentComponent* Kit = Hero->GetEquipment();
    Arena.PlaceHero(FVector::ZeroVector, 0.f);
    // A retainer held where it is placed (as a takedown holds a guard), its
    // back to the hero.
    FSoraPatrolRoute Post;
    Post.Points.Add(FVector(180.f, 0.f, 90.f));
    ASoraEnemy* Retainer = Arena.SpawnKind(TEXT("blade_retainer"), 5, FVector(180.f, 0.f, 0.f), 0.f, &Post);
    if (!TestNotNull(TEXT("A retainer stands at its post"), Retainer))
        return false;
    Retainer->Seize(true);
    const TArray<ASoraEnemy*> Keep{Retainer};
    const auto At = [&](float Distance)
    {
        Retainer->SetActorLocation(FVector(Distance, 0.f, Retainer->GetActorLocation().Z), false, nullptr, ETeleportType::TeleportPhysics);
        return Tick(Arena, 1, Keep) && Kit->InMaai();
    };
    const float Reach = SoraHistoricalArms::Profile(SoraHistoricalArms::EForm::Katana).MaximumDistanceCm;
    // 水月: the ring lights in the outer fifteen percent of the katana's reach.
    TestFalse(TEXT("Inside the reach, too close: no ring"), At(Reach * .8f));
    TestTrue(TEXT("At the ring's inner edge"), At(Reach * .86f));
    TestTrue(TEXT("At the reach itself"), At(Reach - 1.f));
    TestFalse(TEXT("Beyond the reach: no ring"), At(Reach + 10.f));
    // Only for the opponent the blade points at, and only with it drawn.
    TestTrue(TEXT("In the ring again"), At(Reach * .9f));
    Arena.PlaceHero(FVector::ZeroVector, 90.f);
    if (!Tick(Arena, 1, Keep))
        return false;
    TestFalse(TEXT("Looking away: no ring"), Kit->InMaai());
    Arena.PlaceHero(FVector::ZeroVector, 0.f);
    if (!Tap(Arena, EKeys::V))
        return false;
    TestFalse(TEXT("Sheathed: no ring"), Kit->InMaai());
    if (!Tap(Arena, EKeys::V))
        return false;
    // The yari reads its own, longer distance.
    Kit->Hold(19);
    Hero->RebuildWeapon();
    const float Spear = SoraHistoricalArms::Profile(SoraHistoricalArms::EForm::Yari).MaximumDistanceCm;
    TestFalse(TEXT("A sword's distance is inside the yari's"), At(Reach * .9f));
    TestTrue(TEXT("The yari's ring lies at its own reach"), At(Spear * .92f));
    return Arena.Tick(2);
}
#endif
