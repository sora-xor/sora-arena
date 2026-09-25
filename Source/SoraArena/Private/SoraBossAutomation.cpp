#include "SoraGameMode.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Combat/SoraBossCatalog.h"
#include "Combat/SoraBossHazard.h"
#include "Combat/SoraCombatEffects.h"
#include "Combat/SoraDamage.h"
#include "SoraBoss.h"
#include "SoraBossRules.h"
#include "SoraCatalog.h"
#include "SoraEnemyTestArena.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameEvents.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/DamageType.h"
#include "Kismet/GameplayStatics.h"

// The campaign bosses and rival duels (Content/Data/bosses.json) in real game
// worlds, one test per fight. Each proves that every strike comes at least
// its whole telegraph after its windup began (and every hurt it deals is
// announced as such a strike), that its phases change exactly at their
// thresholds with the chapter's pattern table and voice line, that guards,
// parries and mutō-dori meet its attacks as the story bible and chapter
// scripts say, and that it falls to its documented counterplay. The hero's
// guards and parries are real key presses; his landed blows are delivered
// through SoraDamage::Strike from where he stands, as his weapons deliver them.
namespace SoraBossAutomation
{
using SoraEnemyTest::FArena;
namespace CombatRules = SoraCombatRules;

struct FStamped
{
    FSoraBossPhaseEvent Event;
    double Ms = 0.0;
};

// Every boss announcement and every hurt, stamped with world time.
struct FLog
{
    UWorld* World = nullptr;
    TArray<FStamped> Boss;
    TArray<TPair<FSoraDamagedEvent, double>> Damaged;
    TArray<FSoraDefenseEvent> Parried;
    TArray<FSoraDefenseEvent> Guarded;
    TArray<FSoraDiedEvent> Died;
    TArray<TFunction<void()>> Removers;

    ~FLog() { Detach(); }
    double Now() const { return World ? World->GetTimeSeconds() * 1000.0 : 0.0; }
    bool Attach(UWorld* InWorld)
    {
        World = InWorld;
        USoraGameEvents* Events = USoraGameEvents::Get(InWorld);
        if (!Events)
            return false;
        const TWeakObjectPtr<USoraGameEvents> Bus = Events;
        const FDelegateHandle BossHandle = Events->OnBossPhase.AddLambda([this](const FSoraBossPhaseEvent& E) { Boss.Add({E, Now()}); });
        const FDelegateHandle DamagedHandle = Events->OnDamaged.AddLambda([this](const FSoraDamagedEvent& E) { Damaged.Add({E, Now()}); });
        const FDelegateHandle ParriedHandle = Events->OnParried.AddLambda([this](const FSoraDefenseEvent& E) { Parried.Add(E); });
        const FDelegateHandle GuardedHandle = Events->OnGuarded.AddLambda([this](const FSoraDefenseEvent& E) { Guarded.Add(E); });
        const FDelegateHandle DiedHandle = Events->OnDied.AddLambda([this](const FSoraDiedEvent& E) { Died.Add(E); });
        Removers.Add([Bus, BossHandle, DamagedHandle, ParriedHandle, GuardedHandle, DiedHandle]()
        {
            if (!Bus.IsValid())
                return;
            Bus->OnBossPhase.Remove(BossHandle);
            Bus->OnDamaged.Remove(DamagedHandle);
            Bus->OnParried.Remove(ParriedHandle);
            Bus->OnGuarded.Remove(GuardedHandle);
            Bus->OnDied.Remove(DiedHandle);
        });
        return true;
    }
    void Detach()
    {
        for (const TFunction<void()>& Remove : Removers)
            Remove();
        Removers.Reset();
    }
    int32 Count(ESoraBossPhase What, FName Detail = NAME_None) const
    {
        int32 Found = 0;
        for (const FStamped& Entry : Boss)
            Found += Entry.Event.Phase == What && (Detail.IsNone() || Entry.Event.Detail == Detail) ? 1 : 0;
        return Found;
    }
    const FStamped* First(ESoraBossPhase What, FName Detail = NAME_None) const
    {
        for (const FStamped& Entry : Boss)
            if (Entry.Event.Phase == What && (Detail.IsNone() || Entry.Event.Detail == Detail))
                return &Entry;
        return nullptr;
    }
    const FStamped* Last(ESoraBossPhase What, FName Detail = NAME_None) const
    {
        for (int32 Index = Boss.Num() - 1; Index >= 0; --Index)
            if (Boss[Index].Event.Phase == What && (Detail.IsNone() || Boss[Index].Event.Detail == Detail))
                return &Boss[Index];
        return nullptr;
    }
    int32 ParriedBy(const AActor* Attacker) const
    {
        int32 Found = 0;
        for (const FSoraDefenseEvent& E : Parried)
            Found += E.Attacker == Attacker ? 1 : 0;
        return Found;
    }
    int32 GuardedBy(const AActor* Attacker) const
    {
        int32 Found = 0;
        for (const FSoraDefenseEvent& E : Guarded)
            Found += E.Attacker == Attacker && E.Defender != Attacker ? 1 : 0;
        return Found;
    }
};

bool Until(FArena& Arena, int32 MaxFrames, TFunctionRef<bool()> Done)
{
    for (int32 Index = 0; Index < MaxFrames && !Done(); ++Index)
        if (!Arena.Tick(1))
            return false;
    return Done();
}

// World time passes: the frames that cover Milliseconds.
bool Wait(FArena& Arena, FLog& Log, double Milliseconds)
{
    const double Until = Log.Now() + Milliseconds;
    for (int32 Index = 0; Index < 6000 && Log.Now() < Until; ++Index)
        if (!Arena.Tick(1))
            return false;
    return Log.Now() >= Until;
}

bool Press(FArena& Arena, const FKey& Key, bool bDown)
{
    return Arena.World->InjectKey(Key, bDown ? IE_Pressed : IE_Released);
}

// Nyaakoto holds a catalog weapon, drawn, with a rested guard.
bool Arm(FArena& Arena, int32 WeaponId)
{
    ASoraPlayerCharacter* Hero = Arena.Hero();
    Hero->GetEquipment()->Hold(WeaponId);
    Hero->RebuildWeapon();
    return Until(Arena, 600, [&]() { return Hero->GetEquipment()->GuardReserve() >= 100.f; });
}

// The hero at the origin facing +X, the fight at Distance facing him.
ASoraBoss* Spawn(FArena& Arena, const TCHAR* Id, float Distance, const FSoraBossSetup& Setup = FSoraBossSetup())
{
    ASoraPlayerCharacter* Hero = Arena.Hero();
    Arena.PlaceHero(FVector::ZeroVector, 0.f);
    Hero->GetCharacterMovement()->StopMovementImmediately();
    FSoraBossCatalog& Catalog = FSoraBossCatalog::Get();
    const FSoraBossData* Data = Catalog.Load() ? Catalog.Find(Id) : nullptr;
    const float Scale = Data ? Data->ScalePermille / 1000.f : 1.f;
    const float Floor = Hero->GetActorLocation().Z - Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    return ASoraBoss::SpawnBoss(*Arena.Get(), FName(Id), 30, FVector(Distance, 0.f, Floor + 90.f * Scale + 10.f),
        FRotator(0.f, 180.f, 0.f), Setup);
}

// A point around the boss: 0 degrees in front of it, 180 behind.
FVector Around(const ASoraBoss& Boss, float Degrees, float Distance)
{
    return Boss.GetActorLocation() + Boss.GetActorForwardVector().GetSafeNormal2D().RotateAngleAxis(Degrees, FVector::UpVector) * Distance;
}

// A blow from the hero's side, delivered as his weapons deliver one: from
// From, meeting Part (a weak point) or the body. Returns the health it took.
float Hit(ASoraBoss& Boss, ASoraCharacterBase& Hero, float Damage, CombatRules::EHit Kind, const FVector& From, int32 WeaponId = 0,
    UPrimitiveComponent* Part = nullptr)
{
    FSoraHit Blow;
    Blow.Kind = Kind;
    Blow.Origin = From;
    Blow.bHasOrigin = true;
    Blow.WeaponId = WeaponId;
    FHitResult Trace;
    Trace.ImpactPoint = Part ? Part->GetComponentLocation() : Boss.GetActorLocation();
    Trace.Location = Trace.ImpactPoint;
    Trace.Component = Part;
    Trace.bBlockingHit = Part != nullptr;
    const float Before = Boss.Health;
    SoraDamage::Strike(&Boss, Damage, Blow, (Boss.GetActorLocation() - From).GetSafeNormal(), Trace, Hero.GetController(), &Hero);
    return Before - Boss.Health;
}

float Cut(ASoraBoss& Boss, ASoraCharacterBase& Hero, float Damage, float Degrees)
{
    return Hit(Boss, Hero, Damage, CombatRules::EHit::Melee, Around(Boss, Degrees, 150.f));
}

// Story damage straight to health (a checkpoint's restore, a test's setup).
void Scripted(ASoraBoss& Boss, const FArena& Arena, float Damage)
{
    UGameplayStatics::ApplyDamage(&Boss, Damage, nullptr, Arena.Hero(), UDamageType::StaticClass());
}

// Every strike came at least its whole telegraph after its windup began, and
// every hurt the boss dealt the hero was announced as a strike that frame.
void CheckTelegraphs(FAutomationTestBase& Test, const FLog& Log, const ASoraBoss& Boss)
{
    const FSoraBossData& Data = *Boss.Data();
    int32 Strikes = 0, Hurts = 0;
    for (const FStamped& Strike : Log.Boss)
    {
        if (Strike.Event.Boss != &Boss || Strike.Event.Phase != ESoraBossPhase::Strike)
            continue;
        ++Strikes;
        const FStamped* Windup = nullptr;
        for (const FStamped& Earlier : Log.Boss)
            if (Earlier.Event.Boss == &Boss && Earlier.Event.Phase == ESoraBossPhase::Windup && Earlier.Event.Serial == Strike.Event.Serial)
                Windup = &Earlier;
        const FString What = FString::Printf(TEXT("%s %s #%d"), *Data.Id.ToString(), *Strike.Event.Detail.ToString(), Strike.Event.Serial);
        if (!Test.TestNotNull(*(What + TEXT(" was telegraphed")), Windup))
            continue;
        Test.TestTrue(*FString::Printf(TEXT("%s struck %.1f ms after its %d ms telegraph began"), *What, Strike.Ms - Windup->Ms,
            Windup->Event.WindupMs), Strike.Ms - Windup->Ms >= Windup->Event.WindupMs - 1.0);
        const int32 Index = Data.AttackIndex(Strike.Event.Detail);
        if (Test.TestTrue(*(What + TEXT(" is one of its attacks")), Index != INDEX_NONE) && Data.Attacks[Index].Hurts())
            Test.TestTrue(*(What + TEXT(" telegraphs at least the fight's floor")), Windup->Event.WindupMs >= Data.TelegraphMinMs);
    }
    const APawn* Hero = UGameplayStatics::GetPlayerPawn(Log.World, 0);
    for (const TPair<FSoraDamagedEvent, double>& Hurt : Log.Damaged)
    {
        if (Hurt.Key.Causer != &Boss || Hurt.Key.Victim != Hero)
            continue;
        ++Hurts;
        bool bAnnounced = false;
        for (const FStamped& Strike : Log.Boss)
            bAnnounced |= Strike.Event.Boss == &Boss && Strike.Event.Phase == ESoraBossPhase::Strike && FMath::Abs(Strike.Ms - Hurt.Value) < .001;
        Test.TestTrue(*FString::Printf(TEXT("%s's hurt at %.1f ms was an announced strike"), *Data.Id.ToString(), Hurt.Value), bAnnounced);
    }
    Test.TestTrue(*FString::Printf(TEXT("%s struck"), *Data.Id.ToString()), Strikes > 0);
    Test.AddInfo(FString::Printf(TEXT("%s: %d strikes and %d hurts, every one after its whole telegraph"), *Data.Id.ToString(), Strikes, Hurts));
}

// Walks the fight through its phases with story damage: one point above each
// threshold it holds its phase; at the threshold the next begins, naming the
// chapter's pattern table and voice line, behind an invulnerable roar.
bool WalkPhases(FAutomationTestBase& Test, FArena& Arena, FLog& Log, ASoraBoss& Boss)
{
    const FSoraBossData& Data = *Boss.Data();
    const int32 Max = FMath::RoundToInt32(Boss.MaxHealth);
    const FStamped* First = Log.Last(ESoraBossPhase::PhaseChanged, Data.Phases[0].Table);
    if (Test.TestNotNull(TEXT("The fight opens on its first pattern table"), First))
        Test.TestEqual(TEXT("with its voice line"), First->Event.Line, Data.Phases[0].Bark);
    for (int32 Phase = 1; Phase < Data.Phases.Num(); ++Phase)
    {
        const FString What = FString::Printf(TEXT("%s %s"), *Data.Id.ToString(), *Data.Phases[Phase].Table.ToString());
        const int32 Threshold = SoraBossRules::PhaseHealth(Max, Data.Phases[Phase].FromPermille);
        // Health reads in permille, as the campaign reads it: one permille above holds the phase.
        const int32 Above = (Max * (Data.Phases[Phase].FromPermille + 1) + 999) / 1000;
        Scripted(Boss, Arena, Boss.Health - Above);
        if (!Arena.Tick(2))
            return false;
        Test.TestEqual(*(What + TEXT(": one permille above the threshold is still the phase before")), Boss.PhaseIndex(), Phase - 1);
        Scripted(Boss, Arena, Boss.Health - Threshold);
        if (!Arena.Tick(1))
            return false;
        Test.TestEqual(*(What + TEXT(": begins exactly at its threshold")), Boss.PhaseIndex(), Phase);
        Test.TestEqual(*(What + TEXT(": at its threshold's health")), FMath::RoundToInt32(Boss.Health), Threshold);
        const FStamped* Changed = Log.Last(ESoraBossPhase::PhaseChanged, Data.Phases[Phase].Table);
        if (Test.TestNotNull(*(What + TEXT(": announced")), Changed))
            Test.TestEqual(*(What + TEXT(": with the chapter's voice line")), Changed->Event.Line, Data.Phases[Phase].Bark);
        if (Data.TransitionMs > 0)
        {
            Test.TestTrue(*(What + TEXT(": the change is an invulnerable roar")), Boss.IsInvulnerable());
            const float Before = Boss.Health;
            Cut(Boss, *Arena.Hero(), 50.f, 180.f);
            Test.TestEqual(*(What + TEXT(": nothing lands during the roar")), Boss.Health, Before);
        }
        if (!Wait(Arena, Log, Data.TransitionMs + 50.0))
            return false;
    }
    return true;
}

enum class EStance { None, Parry, Guard };

struct FBlow
{
    bool bResolved = false;
    int32 Serial = 0;
    float HeroDamage = 0.f;
    int32 Parried = 0;
    int32 Guarded = 0;
    bool bStaggered = false;
};

// Meets one attack (forced, or the pattern's next when bForce is false) with
// a stance: a guard pressed 120 ms before its HitNumber-th blow lands (a
// parry), a guard pressed as its windup begins and held (a guard), or none.
// Returns once its recovery has begun, with the guard lowered again.
bool Meet(FArena& Arena, FLog& Log, ASoraBoss& Boss, FName Attack, EStance Stance, FBlow& Out, int32 HitNumber = 1, bool bForce = true)
{
    ASoraPlayerCharacter* Hero = Arena.Hero();
    const FSoraBossData& Data = *Boss.Data();
    const int32 Index = Data.AttackIndex(Attack);
    if (Index == INDEX_NONE)
        return false;
    if (!Until(Arena, 900, [&]() { return Boss.BossAttackIndex() == INDEX_NONE && !Boss.IsStaggered() && !Boss.IsInvulnerable(); }))
        return false;
    const int32 Mark = Log.Boss.Num();
    if (bForce && !Boss.ForceAttack(Attack))
        return false;
    FStamped Windup;
    const auto Started = [&]()
    {
        for (int32 Entry = Mark; Entry < Log.Boss.Num(); ++Entry)
            if (Log.Boss[Entry].Event.Boss == &Boss && Log.Boss[Entry].Event.Phase == ESoraBossPhase::Windup &&
                Log.Boss[Entry].Event.Detail == Attack)
            {
                Windup = Log.Boss[Entry];
                return true;
            }
        return false;
    };
    if (!Until(Arena, 1200, Started))
        return false;
    Out.Serial = Windup.Event.Serial;
    const double HitAt = Windup.Ms + Windup.Event.WindupMs + (HitNumber - 1) * Data.Attacks[Index].GapMs;
    const int32 Hurts = Log.Damaged.Num();
    const int32 Parried = Log.ParriedBy(&Boss), Guarded = Log.GuardedBy(&Boss);
    bool bPressed = false;
    if (Stance == EStance::Guard)
    {
        if (!Press(Arena, EKeys::LeftControl, true))
            return false;
        bPressed = true;
    }
    const int32 Serial = Out.Serial;
    const auto Recovered = [&]()
    {
        for (int32 Entry = Mark; Entry < Log.Boss.Num(); ++Entry)
            if (Log.Boss[Entry].Event.Boss == &Boss && Log.Boss[Entry].Event.Serial == Serial &&
                Log.Boss[Entry].Event.Phase == ESoraBossPhase::Recovery)
                return true;
        return Boss.IsDefeated();
    };
    for (int32 Frame = 0; Frame < 900 && !Recovered(); ++Frame)
    {
        if (Stance == EStance::Parry && !bPressed && Log.Now() >= HitAt - 120.0)
        {
            if (!Press(Arena, EKeys::LeftControl, true))
                return false;
            bPressed = true;
        }
        if (!Arena.Tick(1))
            return false;
    }
    Out.bResolved = Recovered();
    // What the boss dealt him, from its announcements (a defeat's reward heals him).
    for (int32 Entry = Hurts; Entry < Log.Damaged.Num(); ++Entry)
        if (Log.Damaged[Entry].Key.Victim == Hero && Log.Damaged[Entry].Key.Causer == &Boss)
            Out.HeroDamage += Log.Damaged[Entry].Key.Amount;
    Out.Parried = Log.ParriedBy(&Boss) - Parried;
    Out.Guarded = Log.GuardedBy(&Boss) - Guarded;
    Out.bStaggered = Boss.IsStaggered();
    return (!bPressed || Press(Arena, EKeys::LeftControl, false)) && Arena.Tick(1);
}

// The guard rests to full between cases, so no case decides the next.
bool Rest(FArena& Arena)
{
    USoraEquipmentComponent* Kit = Arena.Hero()->GetEquipment();
    return Until(Arena, 900, [Kit]() { return Kit->GuardReserve() >= 100.f && !Kit->IsStaggered(); });
}

// Keeps the hero standing where he is, facing the boss.
void Face(FArena& Arena, const ASoraBoss& Boss)
{
    ASoraPlayerCharacter* Hero = Arena.Hero();
    const FVector Delta = Boss.GetActorLocation() - Hero->GetActorLocation();
    Arena.PlaceHero(Hero->GetActorLocation(), Delta.Rotation().Yaw);
    Hero->GetCharacterMovement()->StopMovementImmediately();
}

// Where the boss is, with the hero standing Distance in front of it, facing it.
void Stand(FArena& Arena, const ASoraBoss& Boss, float Distance, float Degrees = 0.f)
{
    const FVector At = Around(Boss, Degrees, Distance);
    Arena.PlaceHero(At, (Boss.GetActorLocation() - At).Rotation().Yaw);
    Arena.Hero()->GetCharacterMovement()->StopMovementImmediately();
}

bool Starts(FAutomationTestBase& Test, FArena& Arena, FLog& Log)
{
    if (!Test.TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()) ||
        !Test.TestTrue(TEXT("Content/Data/bosses.json loads"), FSoraBossCatalog::Get().Load()) || !Arena.Start())
        return false;
    return Test.TestTrue(TEXT("The event log attaches"), Log.Attach(Arena.Get())) && Arm(Arena, 0);
}

// A step that timed out or could not start: named by its line, so no test fails silently.
bool Stopped(FAutomationTestBase& Test, int32 Line)
{
    Test.AddError(FString::Printf(TEXT("SoraBossAutomation.cpp:%d: a step did not complete"), Line));
    return false;
}

bool Defeated(FAutomationTestBase& Test, const FLog& Log, const ASoraBoss& Boss, FName Detail)
{
    const FStamped* End = Log.Last(ESoraBossPhase::Defeated);
    Test.TestTrue(*FString::Printf(TEXT("%s is defeated"), *Boss.Data()->Id.ToString()), Boss.IsDefeated() && !Boss.IsAlive());
    Test.TestEqual(TEXT("It falls once"), Log.Count(ESoraBossPhase::Defeated), 1);
    Test.TestFalse(TEXT("The arena opens"), Boss.IsArenaLocked());
    bool bDied = false;
    for (const FSoraDiedEvent& Died : Log.Died)
        if (Died.Victim == &Boss)
        {
            bDied = true;
            Test.TestEqual(TEXT("Only a lethal fight kills; the disarmed, captured and broken live"), Died.bSparring, !Boss.Data()->bLethal);
        }
    Test.TestTrue(TEXT("Its fall is announced"), bDied);
    return Test.TestNotNull(TEXT("Its defeat is announced"), End) && Test.TestEqual(TEXT("as documented"), End->Event.Detail, Detail);
}
} // namespace SoraBossAutomation

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraBossCatalogTest,
    "SoraArena.Boss.Catalog",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraBossCatalogTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraBossAutomation;
    FArena Arena(*this, TEXT("BossCatalog"));
    FLog Log;
    if (!Starts(*this, Arena, Log))
        return Stopped(*this, __LINE__);
    FSoraBossCatalog& Catalog = FSoraBossCatalog::Get();
    static const TCHAR* const Bosses[] = {TEXT("boss_dunark"), TEXT("boss_penalta"), TEXT("boss_hakari"), TEXT("boss_tarifa"),
        TEXT("boss_eskro"), TEXT("boss_collatera"), TEXT("boss_val_amort")};
    static const TCHAR* const Duels[] = {TEXT("duel_toranosuke_fukuro"), TEXT("duel_toranosuke_steel")};
    TestEqual(TEXT("The story bible's seven bosses, in its order"), Catalog.Bosses().Num(), 7);
    TestEqual(TEXT("And the two duels with Toranosuke"), Catalog.Duels().Num(), 2);
    for (int32 Index = 0; Index < 7; ++Index)
        TestEqual(TEXT("Boss order"), Catalog.Bosses()[Index].Id, FName(Bosses[Index]));
    // A chapter beat finds its fight: the director's way from a duel's npc to its duel.
    const FSoraBossData* Steel = Catalog.ForBeat(TEXT("ch06.b09"));
    const FSoraBossData* Fukuro = Catalog.ForBeat(TEXT("ch01.b11"));
    TestTrue(TEXT("ch06.b09 stages the steel duel"), Steel && Steel->Id == FName(TEXT("duel_toranosuke_steel")) &&
        Steel->Opponent == FName(TEXT("npc_toranosuke")));
    TestTrue(TEXT("ch01.b11 stages the fukuro-shinai bout"), Fukuro && Fukuro->Id == FName(TEXT("duel_toranosuke_fukuro")));
    TestTrue(TEXT("ch08.b14 stages Val Amort"), Catalog.ForBeat(TEXT("ch08.b14")) == Catalog.Find(TEXT("boss_val_amort")));
    TestNull(TEXT("A beat without a fight stages none"), Catalog.ForBeat(TEXT("ch02.b01")));
    int32 Place = 0;
    for (const TCHAR* Id : {Bosses[0], Bosses[1], Bosses[2], Bosses[3], Bosses[4], Bosses[5], Bosses[6], Duels[0], Duels[1]})
    {
        const FSoraBossData* Data = Catalog.Find(Id);
        if (!TestNotNull(*FString::Printf(TEXT("%s is in bosses.json"), Id), Data))
            continue;
        ASoraBoss* Boss = ASoraBoss::SpawnBoss(*Arena.Get(), FName(Id), Place, FVector(-3000.f + Place * 700.f, 2600.f, 400.f),
            FRotator::ZeroRotator);
        ++Place;
        if (!TestNotNull(*FString::Printf(TEXT("%s spawns by id"), Id), Boss))
            continue;
        const FString What(Id);
        TestEqual(What + TEXT(" health"), Boss->Health, static_cast<float>(Data->Health[1]));
        TestEqual(What + TEXT(" starts in its first phase"), Boss->PhaseIndex(), 0);
        TestTrue(What + TEXT(" scale"), FMath::IsNearlyEqual(Boss->GetActorScale3D().Z, Data->ScalePermille / 1000.f));
        TestTrue(What + TEXT(" has bilingual names and a caption for every attack"), !Data->NameJapanese.IsEmpty() && !Data->NameEnglish.IsEmpty());
        for (const FSoraBossAttack& Attack : Data->Attacks)
            TestTrue(What + TEXT(" captions ") + Attack.Id.ToString(), !Attack.TellJapanese.IsEmpty() && !Attack.TellEnglish.IsEmpty());
        TestEqual(What + TEXT(" is not killed unless its fight kills"), Boss->IsSparring(), !Data->bLethal);
        Boss->Destroy();
    }
    // Difficulty scales every telegraph; a checkpoint restores a phase's start.
    FSoraBossSetup Easy;
    Easy.Difficulty = SoraBossRules::EDifficulty::Easy;
    FSoraBossSetup Hard;
    Hard.Difficulty = SoraBossRules::EDifficulty::Hard;
    ASoraBoss* EasyBoss = ASoraBoss::SpawnBoss(*Arena.Get(), TEXT("boss_dunark"), 40, FVector(-2000.f, 3400.f, 400.f), FRotator::ZeroRotator, Easy);
    ASoraBoss* HardBoss = ASoraBoss::SpawnBoss(*Arena.Get(), TEXT("boss_penalta"), 41, FVector(-1000.f, 3400.f, 400.f), FRotator::ZeroRotator, Hard);
    if (TestNotNull(TEXT("An Easy Dunark"), EasyBoss) && TestNotNull(TEXT("A Hard Penalta"), HardBoss))
    {
        const int32 Heavy = EasyBoss->Data()->AttackIndex(TEXT("heavy_overhead"));
        TestEqual(TEXT("Easy (稽古) adds 30% to a windup"), EasyBoss->WindupFor(Heavy), 1170);
        TestEqual(TEXT("Hard (免許皆伝) takes 15% off"), HardBoss->WindupFor(HardBoss->Data()->AttackIndex(TEXT("hammer_slam"))), 850);
        TestEqual(TEXT("Hard Penalta has the chapter's Hard health"), HardBoss->Health, 2400.f);
        TestEqual(TEXT("Easy mutō-dori window"), EasyBoss->MutoWindowMs(), 234);
        EasyBoss->Destroy();
        HardBoss->Destroy();
    }
    FSoraBossSetup Restored;
    Restored.Phase = 2;
    ASoraBoss* Checkpoint = ASoraBoss::SpawnBoss(*Arena.Get(), TEXT("boss_val_amort"), 42, FVector(0.f, 3400.f, 400.f), FRotator::ZeroRotator, Restored);
    if (TestNotNull(TEXT("A restored collector"), Checkpoint))
    {
        TestEqual(TEXT("A phase checkpoint restores that phase"), Checkpoint->PhaseIndex(), 2);
        TestEqual(TEXT("at its start's health"), Checkpoint->Health, 960.f);
        Checkpoint->Destroy();
    }
    AddExpectedError(TEXT("No boss oni"), EAutomationExpectedErrorFlags::Contains, 1);
    TestNull(TEXT("An unknown boss spawns nothing"), ASoraBoss::SpawnBoss(*Arena.Get(), TEXT("oni"), 43, FVector(0.f, 4000.f, 400.f), FRotator::ZeroRotator));
    return Arena.Tick(2);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraBossDunarkTest,
    "SoraArena.Boss.Dunark",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraBossDunarkTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraBossAutomation;
    FArena Arena(*this, TEXT("BossDunark"));
    FLog Log;
    if (!Starts(*this, Arena, Log))
        return Stopped(*this, __LINE__);
    FSoraBossSetup Setup;
    Setup.bLockArena = true;
    ASoraBoss* Boss = Spawn(Arena, TEXT("boss_dunark"), 200.f, Setup);
    ASoraPlayerCharacter* Hero = Arena.Hero();
    if (!TestNotNull(TEXT("Dunark spawns"), Boss))
        return Stopped(*this, __LINE__);
    TestTrue(TEXT("His courtyard is locked"), Boss->IsArenaLocked());
    // The hero cannot walk out of a locked courtyard.
    const FVector Center = Boss->ArenaCenter();
    const float Radius = Boss->ArenaRadius();
    Arena.PlaceHero(FVector(Center.X, Center.Y - (Radius - 150.f), 0.f), -90.f);
    if (!Press(Arena, EKeys::W, true) || !Arena.Tick(90) || !Press(Arena, EKeys::W, false))
        return Stopped(*this, __LINE__);
    TestTrue(TEXT("Walking out, the hero stops at the lock"), FVector::Dist2D(Hero->GetActorLocation(), Center) < Radius);
    TestTrue(TEXT("having walked up to it"), FVector::Dist2D(Hero->GetActorLocation(), Center) > Radius - 120.f);
    // The metronome: [quick, quick, heavy] on 1300 ms beats, a pause after each measure.
    Arena.PlaceHero(FVector::ZeroVector, 0.f);
    const int32 Mark = Log.Boss.Num();
    TArray<const FStamped*> Windups;
    if (!Until(Arena, 1500, [&]()
        {
            Windups.Reset();
            for (int32 Entry = Mark; Entry < Log.Boss.Num(); ++Entry)
                if (Log.Boss[Entry].Event.Phase == ESoraBossPhase::Windup)
                    Windups.Add(&Log.Boss[Entry]);
            return Windups.Num() >= 6;
        }))
        return Stopped(*this, __LINE__);
    static const TCHAR* const Measure[] = {TEXT("quick_cut"), TEXT("quick_cut"), TEXT("heavy_overhead")};
    for (int32 Index = 0; Index < 6; ++Index)
        TestEqual(TEXT("His notices come in fixed measures"), Windups[Index]->Event.Detail, FName(Measure[Index % 3]));
    const double Notice = Windups[0]->Ms;
    for (int32 Index = 1; Index < 6; ++Index)
    {
        const double Offset = FMath::Fmod(Windups[Index]->Ms - Notice, 1300.0);
        TestTrue(*FString::Printf(TEXT("Cut %d falls on the 1300 ms beat counted from his first (%.1f ms off)"), Index, Offset),
            Offset < 20.0 || Offset > 1280.0);
    }
    TestTrue(TEXT("A measure ends in a pause"), Windups[3]->Ms - Windups[2]->Ms >= 900 + 1100 + 1500 - 1);
    // Awase on the heavy overhead: 1.2 s stagger, and a flank cut does half again.
    if (!Rest(Arena))
        return Stopped(*this, __LINE__);
    FBlow Heavy;
    Face(Arena, *Boss);
    if (!Meet(Arena, Log, *Boss, TEXT("heavy_overhead"), EStance::Parry, Heavy) ||
        !TestTrue(TEXT("The heavy resolves"), Heavy.bResolved))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("The heavy overhead is parried"), Heavy.Parried, 1);
    TestEqual(TEXT("A parried heavy does no damage"), Heavy.HeroDamage, 0.f);
    TestTrue(TEXT("Awase staggers him"), Heavy.bStaggered);
    TestEqual(TEXT("A flank cut in his stagger: x1.25, then x1.5"), Cut(*Boss, *Hero, 60.f, 90.f), 113.f);
    // A held guard takes the heavy's chip and 40 stamina.
    if (!Rest(Arena) || !Until(Arena, 300, [&]() { return !Boss->IsStaggered(); }))
        return Stopped(*this, __LINE__);
    FBlow Held;
    Face(Arena, *Boss);
    if (!Meet(Arena, Log, *Boss, TEXT("heavy_overhead"), EStance::Guard, Held))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("A held guard takes the heavy"), Held.Guarded, 1);
    TestEqual(TEXT("with its 12 chip"), Held.HeroDamage, 12.f);
    // The thrust cannot be parried: a fresh guard takes its chip and breaks.
    if (!Rest(Arena))
        return Stopped(*this, __LINE__);
    FBlow Thrust;
    Face(Arena, *Boss);
    if (!Meet(Arena, Log, *Boss, TEXT("thrust"), EStance::Parry, Thrust))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("The thrust is never parried"), Thrust.Parried, 0);
    TestEqual(TEXT("A guard takes its 20 chip"), Thrust.HeroDamage, 20.f);
    TestTrue(TEXT("and the thrust breaks the guard"), Hero->GetEquipment()->IsStaggered());
    const FStamped* Thrusted = Log.Last(ESoraBossPhase::Windup, TEXT("thrust"));
    TestTrue(TEXT("The thrust barks 「一括。」"), Thrusted && Thrusted->Event.Line == FName(TEXT("ch02.b15.dunark.008")));
    // Between measures he turns frontal arrows aside; from his flank they land.
    if (!Rest(Arena) || !Until(Arena, 400, [&]() { return Boss->BossAttackIndex() == INDEX_NONE; }))
        return Stopped(*this, __LINE__);
    Boss->Hold(3000);
    if (!Arena.Tick(2))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("A frontal arrow is deflected in his pause"),
        Hit(*Boss, *Hero, 52.f, CombatRules::EHit::Ranged, Around(*Boss, 0.f, 800.f), 18), 0.f);
    TestTrue(TEXT("and he says so"), Log.Count(ESoraBossPhase::Event, TEXT("deflected")) >= 1);
    TestTrue(TEXT("An arrow from his flank lands"), Hit(*Boss, *Hero, 52.f, CombatRules::EHit::Ranged, Around(*Boss, 90.f, 800.f), 18) > 0.f);
    // Awase on a quick cut restarts his measure: parry the second quick cut of
    // a measure, and the next cut is a quick cut again, not the heavy.
    Boss->Hold(0);
    if (!Rest(Arena))
        return Stopped(*this, __LINE__);
    Face(Arena, *Boss);
    int32 Scan = Log.Boss.Num();
    FName Previous;
    bool bMet = false;
    for (int32 Frame = 0; Frame < 3000 && !bMet; ++Frame)
    {
        for (; Scan < Log.Boss.Num() && !bMet; ++Scan)
        {
            const FStamped Entry = Log.Boss[Scan];
            if (Entry.Event.Phase != ESoraBossPhase::Windup)
                continue;
            if (Entry.Event.Detail == TEXT("quick_cut") && Previous == TEXT("quick_cut"))
            {
                const double HitAt = Entry.Ms + Entry.Event.WindupMs;
                const int32 Parried = Log.ParriedBy(Boss);
                if (!Until(Arena, 120, [&]() { return Log.Now() >= HitAt - 120.0; }) || !Press(Arena, EKeys::LeftControl, true) ||
                    !Until(Arena, 60, [&]() { return Log.ParriedBy(Boss) > Parried; }) || !Press(Arena, EKeys::LeftControl, false))
                    return Stopped(*this, __LINE__);
                TestTrue(TEXT("Awase on a quick cut is answered"), Log.Last(ESoraBossPhase::Countered, TEXT("quick_cut")) != nullptr);
                TestFalse(TEXT("It deflects the cut without a stagger"), Boss->IsStaggered());
                const int32 After = Log.Boss.Num();
                FName Restart;
                if (!Until(Arena, 900, [&]()
                    {
                        for (int32 Later = After; Later < Log.Boss.Num(); ++Later)
                            if (Log.Boss[Later].Event.Phase == ESoraBossPhase::Windup)
                            {
                                Restart = Log.Boss[Later].Event.Detail;
                                return true;
                            }
                        return false;
                    }))
                    return Stopped(*this, __LINE__);
                TestEqual(TEXT("His measure restarts with a quick cut, not the heavy"), Restart, FName(TEXT("quick_cut")));
                bMet = true;
                break;
            }
            Previous = Entry.Event.Detail;
        }
        if (!bMet && !Arena.Tick(1))
            return Stopped(*this, __LINE__);
    }
    TestTrue(TEXT("A second quick cut was met"), bMet);
    // Phases 60% and 25%: notices two and three.
    if (!Until(Arena, 600, [&]() { return Boss->BossAttackIndex() == INDEX_NONE; }) || !WalkPhases(*this, Arena, Log, *Boss))
        return Stopped(*this, __LINE__);
    // The last notice: his drone turns arrows while it is closed.
    TestEqual(TEXT("The custody drone guards the final notice"), Boss->LiveWards(), 1);
    Boss->Hold(20000);
    ASoraBossHazard* Drone = Boss->Wards().Num() ? Boss->Wards()[0].Get() : nullptr;
    if (!TestNotNull(TEXT("The drone orbits him"), Drone) || !Until(Arena, 600, [&]() { return !Drone->IsOpen(); }))
        return Stopped(*this, __LINE__);
    const float Health = Boss->Health;
    TestEqual(TEXT("The drone takes the arrow"), Hit(*Boss, *Hero, 52.f, CombatRules::EHit::Ranged, Around(*Boss, 90.f, 800.f), 18), 0.f);
    TestEqual(TEXT("A closed drone shrugs it off"), Drone->WardHealth(), 40);
    TestTrue(TEXT("Blocking re-indexes it"), Drone->IsOpen());
    FHitResult Shot;
    Shot.ImpactPoint = Drone->GetActorLocation();
    SoraDamage::Strike(Drone, 52.f, FSoraHit::Ranged(Hero->GetActorLocation(), 18), FVector::ForwardVector, Shot, Hero->GetController(), Hero);
    if (!Arena.Tick(1))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("An arrow in its re-index downs it"), Boss->LiveWards(), 0);
    TestTrue(TEXT("Then arrows reach him"), Hit(*Boss, *Hero, 52.f, CombatRules::EHit::Ranged, Around(*Boss, 90.f, 800.f), 18) > 0.f &&
        Boss->Health < Health);
    // A feint's tilted blade: awase on it whiffs, and the real cut is only guarded.
    Boss->Hold(0);
    if (!Rest(Arena))
        return Stopped(*this, __LINE__);
    Face(Arena, *Boss);
    const int32 Feints = Log.Count(ESoraBossPhase::Windup, TEXT("feint_overhead"));
    FBlow Real;
    if (!Until(Arena, 900, [&]() { return Boss->BossAttackIndex() == INDEX_NONE && !Boss->IsStaggered(); }) ||
        !Boss->ForceAttack(TEXT("feint_overhead")) ||
        !Until(Arena, 300, [&]() { return Log.Count(ESoraBossPhase::Windup, TEXT("feint_overhead")) > Feints; }))
        return Stopped(*this, __LINE__);
    const double FeintEnds = Log.Last(ESoraBossPhase::Windup, TEXT("feint_overhead"))->Ms + 900.0;
    if (!Until(Arena, 300, [&]() { return Log.Now() >= FeintEnds - 120.0; }) || !Press(Arena, EKeys::LeftControl, true))
        return Stopped(*this, __LINE__);
    const float HeroBefore = Hero->Health;
    const int32 ParriedBefore = Log.ParriedBy(Boss), GuardedBefore = Log.GuardedBy(Boss);
    if (!Until(Arena, 300, [&]() { return Log.GuardedBy(Boss) + Log.ParriedBy(Boss) > GuardedBefore + ParriedBefore; }) ||
        !Press(Arena, EKeys::LeftControl, false))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("Awase on a feint whiffs: no parry"), Log.ParriedBy(Boss) - ParriedBefore, 0);
    TestEqual(TEXT("The real quick cut is guarded"), Log.GuardedBy(Boss) - GuardedBefore, 1);
    TestEqual(TEXT("with its chip"), HeroBefore - Hero->Health, 5.f);
    // The counterplay to the end: awase the heavy, cut his flank in the stagger.
    for (int32 Round = 0; Round < 8 && Boss->IsAlive(); ++Round)
    {
        if (!Rest(Arena))
            return Stopped(*this, __LINE__);
        Face(Arena, *Boss);
        FBlow Opening;
        if (!Meet(Arena, Log, *Boss, TEXT("heavy_overhead"), EStance::Parry, Opening) || !TestTrue(TEXT("Awase opens him"), Opening.bStaggered))
            return Stopped(*this, __LINE__);
        Cut(*Boss, *Hero, 60.f, 90.f);
        if (!Wait(Arena, Log, 400.0))
            return Stopped(*this, __LINE__);
        if (Boss->IsAlive())
            Cut(*Boss, *Hero, 60.f, 90.f);
    }
    if (!Defeated(*this, Log, *Boss, TEXT("kill")))
        return Stopped(*this, __LINE__);
    CheckTelegraphs(*this, Log, *Boss);
    return Arena.Tick(2);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraBossPenaltaTest,
    "SoraArena.Boss.Penalta",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraBossPenaltaTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraBossAutomation;
    FArena Arena(*this, TEXT("BossPenalta"));
    FLog Log;
    if (!Starts(*this, Arena, Log))
        return Stopped(*this, __LINE__);
    ASoraBoss* Boss = Spawn(Arena, TEXT("boss_penalta"), 220.f);
    ASoraPlayerCharacter* Hero = Arena.Hero();
    if (!TestNotNull(TEXT("Penalta spawns"), Boss))
        return Stopped(*this, __LINE__);
    const FSoraBossData& Data = *Boss->Data();
    UPrimitiveComponent* Vent = Boss->WeakPointPart(0);
    Boss->Hold(60000);
    if (!Arena.Tick(2))
        return Stopped(*this, __LINE__);
    // Frontal immunity; four blocked blows raise the hint; his back is open.
    for (int32 Blow = 0; Blow < 4; ++Blow)
        TestEqual(TEXT("His tower shield stops a frontal cut"), Cut(*Boss, *Hero, 60.f, 0.f), 0.f);
    TestEqual(TEXT("Four blocked blows raise the hint"), Log.Count(ESoraBossPhase::Event, TEXT("front_blocked")), 1);
    TestEqual(TEXT("An arrow from the front is stopped too"),
        Hit(*Boss, *Hero, 52.f, CombatRules::EHit::Ranged, Around(*Boss, 0.f, 900.f), 18), 0.f);
    TestEqual(TEXT("A cut to his back lands whole"), Cut(*Boss, *Hero, 60.f, 180.f), 60.f);
    TestEqual(TEXT("A closed vent takes a quarter more"),
        Hit(*Boss, *Hero, 60.f, CombatRules::EHit::Melee, Around(*Boss, 180.f, 150.f), 0, Vent), 75.f);
    // The shield bash: awase does not stagger him but opens the 転 step.
    Boss->Hold(0);
    if (!Rest(Arena))
        return Stopped(*this, __LINE__);
    Stand(Arena, *Boss, 200.f);
    FBlow Bash;
    if (!Meet(Arena, Log, *Boss, TEXT("shield_bash"), EStance::Parry, Bash))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("The bash is met with awase"), Bash.Parried, 1);
    TestEqual(TEXT("and does no damage"), Bash.HeroDamage, 0.f);
    TestFalse(TEXT("but does not stagger him"), Bash.bStaggered);
    // The hammer slam: leave the inner ring and take only its edge; then the vents glow.
    if (!Rest(Arena))
        return Stopped(*this, __LINE__);
    Stand(Arena, *Boss, 300.f);
    FBlow Slam;
    if (!Meet(Arena, Log, *Boss, TEXT("hammer_slam"), EStance::Guard, Slam))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("No guard stops the slam; its edge does 20"), Slam.HeroDamage, 20.f);
    TestEqual(TEXT("The slam is not guarded"), Slam.Guarded + Slam.Parried, 0);
    TestTrue(TEXT("After the slam his vents are open"), Boss->IsWeakPointOpen(0) && Boss->IsWeakPointOpen(1));
    TestEqual(TEXT("An open vent takes two and a half times"),
        Hit(*Boss, *Hero, 60.f, CombatRules::EHit::Melee, Around(*Boss, 180.f, 150.f), 0, Vent), 150.f);
    // Three shells break the shield.
    Boss->Hold(60000);
    for (int32 Shell = 0; Shell < 3; ++Shell)
        Hit(*Boss, *Hero, 35.f, CombatRules::EHit::Blast, Around(*Boss, 0.f, 90.f), 7);
    TestFalse(TEXT("Three grenade hits break the shield"), Boss->IsShieldUp());
    TestEqual(TEXT("and it is announced"), Log.Count(ESoraBossPhase::Event, TEXT("shield_broken")), 1);
    TestTrue(TEXT("Now the front yields"), Cut(*Boss, *Hero, 60.f, 0.f) > 0.f);
    // Phase two at 50%: faster, spinning, trapping.
    Boss->Hold(0);
    if (!WalkPhases(*this, Arena, Log, *Boss))
        return Stopped(*this, __LINE__);
    // Late-fee seals root whoever steps in; one arrow breaks one.
    if (!Rest(Arena))
        return Stopped(*this, __LINE__);
    Stand(Arena, *Boss, 700.f);
    const int32 Seals = Log.Count(ESoraBossPhase::Windup, TEXT("seal_trap"));
    if (!Until(Arena, 900, [&]() { return Boss->BossAttackIndex() == INDEX_NONE && !Boss->IsStaggered(); }) || !Boss->ForceAttack(TEXT("seal_trap")) ||
        !Until(Arena, 300, [&]() { return Log.Count(ESoraBossPhase::Windup, TEXT("seal_trap")) > Seals; }))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("Two discs are thrown"), Boss->LiveZones(Data.AttackIndex(TEXT("seal_trap"))), 2);
    USoraCombatEffects* Effects = USoraCombatEffects::Get(Arena.Get());
    if (!Until(Arena, 300, [&]() { return Effects->IsRooted(Hero); }))
        return Stopped(*this, __LINE__);
    TestTrue(TEXT("The disc under him roots him once it arms"), Effects->IsRooted(Hero));
    ASoraBossHazard* Other = nullptr;
    for (TActorIterator<ASoraBossHazard> It(Arena.Get()); It; ++It)
        if (!It->IsWard() && !It->IsSpent())
            Other = *It;
    if (TestNotNull(TEXT("The other disc waits"), Other))
    {
        FHitResult Shot;
        Shot.ImpactPoint = Other->GetActorLocation();
        SoraDamage::Strike(Other, 52.f, FSoraHit::Ranged(Hero->GetActorLocation(), 18), FVector::ForwardVector, Shot, Hero->GetController(), Hero);
        if (!Arena.Tick(1))
            return Stopped(*this, __LINE__);
        TestEqual(TEXT("One arrow breaks a disc"), Boss->LiveZones(Data.AttackIndex(TEXT("seal_trap"))), 0);
    }
    if (!Until(Arena, 200, [&]() { return !Effects->IsRooted(Hero); }))
        return Stopped(*this, __LINE__);
    // The counterplay to the end: out of the ring, then his open vents.
    for (int32 Round = 0; Round < 8 && Boss->IsAlive(); ++Round)
    {
        if (!Rest(Arena))
            return Stopped(*this, __LINE__);
        Stand(Arena, *Boss, 500.f);
        FBlow Spin;
        if (!Meet(Arena, Log, *Boss, Round % 2 ? TEXT("hammer_spin") : TEXT("hammer_slam"), EStance::None, Spin))
            return Stopped(*this, __LINE__);
        TestEqual(TEXT("Outside the ring nothing lands"), Spin.HeroDamage, 0.f);
        for (int32 Blow = 0; Blow < 4 && Boss->IsAlive() && Boss->IsWeakPointOpen(0); ++Blow)
        {
            Hit(*Boss, *Hero, 60.f, CombatRules::EHit::Melee, Around(*Boss, 180.f, 150.f), 0, Vent);
            if (!Wait(Arena, Log, 350.0))
                return Stopped(*this, __LINE__);
        }
    }
    if (!Defeated(*this, Log, *Boss, TEXT("kill")))
        return Stopped(*this, __LINE__);
    CheckTelegraphs(*this, Log, *Boss);
    return Arena.Tick(2);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraBossHakariTest,
    "SoraArena.Boss.Hakari",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraBossHakariTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraBossAutomation;
    FArena Arena(*this, TEXT("BossHakari"));
    FLog Log;
    if (!Starts(*this, Arena, Log))
        return Stopped(*this, __LINE__);
    ASoraBoss* Boss = Spawn(Arena, TEXT("boss_hakari"), 1400.f);
    ASoraPlayerCharacter* Hero = Arena.Hero();
    if (!TestNotNull(TEXT("Hakari spawns"), Boss))
        return Stopped(*this, __LINE__);
    const FSoraBossData& Data = *Boss->Data();
    const int32 Drum = 4;
    Boss->Hold(60000);
    if (!Arena.Tick(2))
        return Stopped(*this, __LINE__);
    // Its body is armour; only its weak points take damage.
    TestEqual(TEXT("A cut on its armoured body does nothing"), Cut(*Boss, *Hero, 60.f, 0.f), 0.f);
    TestEqual(TEXT("An arrow on a closed coil does nothing"),
        Hit(*Boss, *Hero, 52.f, CombatRules::EHit::Ranged, Hero->GetActorLocation(), 18, Boss->WeakPointPart(0)), 0.f);
    // A leg plants: its coil glows for three seconds, and an arrow does double.
    int32 Planted = INDEX_NONE;
    if (!Until(Arena, 600, [&]()
        {
            for (int32 Coil = 0; Coil < 4; ++Coil)
                if (Boss->IsWeakPointOpen(Coil))
                    Planted = Coil;
            return Planted != INDEX_NONE;
        }) || !TestTrue(TEXT("A leg plants"), Planted != INDEX_NONE))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("Only one coil glows"), static_cast<int32>(Boss->IsWeakPointOpen(0)) + Boss->IsWeakPointOpen(1) +
        Boss->IsWeakPointOpen(2) + Boss->IsWeakPointOpen(3), 1);
    TestEqual(TEXT("An arrow on the glowing coil does double"),
        Hit(*Boss, *Hero, 52.f, CombatRules::EHit::Ranged, Hero->GetActorLocation(), 18, Boss->WeakPointPart(Planted)), 104.f);
    // The weighing stomp: stay out of its ring, then shoot all four coils.
    Boss->Hold(0);
    FBlow Stomp;
    if (!Meet(Arena, Log, *Boss, TEXT("plant_stomp"), EStance::None, Stomp))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("Outside the 6 m ring the stomp misses"), Stomp.HeroDamage, 0.f);
    Boss->Hold(60000);
    for (int32 Coil = 0; Coil < 4; ++Coil)
    {
        TestTrue(TEXT("After the stomp every coil glows"), Boss->IsWeakPointOpen(Coil) || Boss->WeakPointHealth(Coil) == 0);
        for (int32 Arrow = 0; Arrow < 6 && Boss->WeakPointHealth(Coil) > 0; ++Arrow)
            Hit(*Boss, *Hero, 52.f, CombatRules::EHit::Ranged, Hero->GetActorLocation(), 18, Boss->WeakPointPart(Coil));
        TestEqual(TEXT("A coil breaks after its 450"), Boss->WeakPointHealth(Coil), 0);
    }
    TestEqual(TEXT("Each broken coil is announced"), Log.Count(ESoraBossPhase::Event, TEXT("weakpoint_destroyed")), 4);
    const FStamped* Broken = Log.Last(ESoraBossPhase::Event, TEXT("weakpoint_destroyed"));
    TestTrue(TEXT("with Margina's line"), Broken && Broken->Event.Line == FName(TEXT("ch04.b16.margina.008")));
    TestEqual(TEXT("Four coils take it exactly to 55%"), FMath::RoundToInt32(Boss->Health), 2200);
    if (!Arena.Tick(2))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("On foot at the mill"), Boss->PhaseIndex(), 1);
    const FStamped* Mill = Log.Last(ESoraBossPhase::PhaseChanged, TEXT("hakari_mill"));
    TestTrue(TEXT("The mill phase has Margina's revaluation line"), Mill && Mill->Event.Line == Data.Phases[1].Bark);
    if (!Wait(Arena, Log, Data.TransitionMs + 50.0))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("A drone pair comes out"), Boss->LiveAdds(), 2);
    // The claw sweep cannot be parried; a guard takes 60% off it.
    Boss->Hold(0);
    if (!Rest(Arena))
        return Stopped(*this, __LINE__);
    Stand(Arena, *Boss, 600.f);
    FBlow Claw;
    if (!Meet(Arena, Log, *Boss, TEXT("claw_sweep"), EStance::Parry, Claw))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("The claw sweep is never parried"), Claw.Parried, 0);
    TestEqual(TEXT("A guard takes it down to 20"), Claw.HeroDamage, 20.f);
    // An assessment left alone seals the mill.
    Stand(Arena, *Boss, 900.f);
    FBlow Seal;
    if (!Meet(Arena, Log, *Boss, TEXT("assessment_kneel"), EStance::None, Seal))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("A completed assessment seals the mill"), Boss->Seals(), 1);
    const FStamped* Sealed = Log.Last(ESoraBossPhase::Event, TEXT("mill_seal"));
    TestTrue(TEXT("with 「一件、差押え完了。」"), Sealed && Sealed->Event.Line == FName(TEXT("ch04.b16.margina.013")));
    // The counterplay to the end: cut the drum in each kneel; 250 interrupts
    // it and staggers it, and the drum stays open through the stagger.
    for (int32 Round = 0; Round < 8 && Boss->IsAlive(); ++Round)
    {
        Stand(Arena, *Boss, 250.f);
        if (!Until(Arena, 900, [&]() { return Boss->BossAttackIndex() == INDEX_NONE && !Boss->IsStaggered(); }) ||
            !Boss->ForceAttack(TEXT("assessment_kneel")) || !Until(Arena, 400, [&]() { return Boss->IsWeakPointOpen(Drum); }))
            return Stopped(*this, __LINE__);
        const int32 Countered = Log.Count(ESoraBossPhase::Countered, TEXT("assessment_kneel"));
        TestEqual(TEXT("A drum cut does two and a half times"),
            Hit(*Boss, *Hero, 100.f, CombatRules::EHit::Melee, Hero->GetActorLocation(), 0, Boss->WeakPointPart(Drum)),
            FMath::Min(250.f, static_cast<float>(Boss->WeakPointHealth(Drum) + 250)));
        if (!Boss->IsAlive())
            break;
        TestEqual(TEXT("250 on the drum interrupts the assessment"), Log.Count(ESoraBossPhase::Countered, TEXT("assessment_kneel")), Countered + 1);
        TestTrue(TEXT("and staggers it"), Boss->IsStaggered());
        for (int32 Blow = 0; Blow < 3 && Boss->IsAlive() && Boss->IsWeakPointOpen(Drum); ++Blow)
        {
            if (!Wait(Arena, Log, 450.0))
                return Stopped(*this, __LINE__);
            Hit(*Boss, *Hero, 100.f, CombatRules::EHit::Melee, Hero->GetActorLocation(), 0, Boss->WeakPointPart(Drum));
        }
    }
    TestEqual(TEXT("Interrupted assessments seal nothing"), Boss->Seals(), 1);
    if (!Defeated(*this, Log, *Boss, TEXT("destroy_weakpoints")))
        return Stopped(*this, __LINE__);
    CheckTelegraphs(*this, Log, *Boss);
    return Arena.Tick(2);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraBossTarifaTest,
    "SoraArena.Boss.Tarifa",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraBossTarifaTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraBossAutomation;
    FArena Arena(*this, TEXT("BossTarifa"));
    FLog Log;
    if (!Starts(*this, Arena, Log))
        return Stopped(*this, __LINE__);
    ASoraBoss* Boss = Spawn(Arena, TEXT("boss_tarifa"), 600.f);
    ASoraPlayerCharacter* Hero = Arena.Hero();
    if (!TestNotNull(TEXT("Tarifa spawns"), Boss))
        return Stopped(*this, __LINE__);
    // The hall: a heat slot behind the hero, a channel off to one side, a wet slot beyond her.
    Boss->AddAnchor(TEXT("heat_slot"), FVector(-600.f, 0.f, Hero->GetActorLocation().Z));
    Boss->AddAnchor(TEXT("channel"), FVector(0.f, 900.f, Hero->GetActorLocation().Z));
    Boss->AddAnchor(TEXT("wet_slot"), FVector(900.f, 0.f, Hero->GetActorLocation().Z));
    Boss->Hold(60000);
    if (!Arena.Tick(2))
        return Stopped(*this, __LINE__);
    TestTrue(TEXT("Her coolant mantle is up"), Boss->IsMantleUp());
    TestEqual(TEXT("The mantle takes 70% off"), Cut(*Boss, *Hero, 100.f, 0.f), 30.f);
    // A lash nobody meets drags the hero toward the heat slot.
    Boss->Hold(0);
    if (!Rest(Arena))
        return Stopped(*this, __LINE__);
    Face(Arena, *Boss);
    FBlow Pulled;
    const float StartX = Hero->GetActorLocation().X;
    if (!Meet(Arena, Log, *Boss, TEXT("tether_lash"), EStance::None, Pulled) || !Wait(Arena, Log, 300.0))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("The lash stings for 12"), Pulled.HeroDamage, 12.f);
    TestTrue(TEXT("and drags him toward the heat"), Hero->GetActorLocation().X < StartX - 100.f);
    // Awase on the lash snaps the cable: a two-second stun and her mantle down.
    Arena.PlaceHero(FVector::ZeroVector, 0.f);
    if (!Rest(Arena))
        return Stopped(*this, __LINE__);
    FBlow Snapped;
    if (!Meet(Arena, Log, *Boss, TEXT("tether_lash"), EStance::Parry, Snapped))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("The lash is met with awase"), Snapped.Parried, 1);
    TestTrue(TEXT("The cable snaps: she staggers"), Snapped.bStaggered);
    TestFalse(TEXT("and her mantle drops"), Boss->IsMantleUp());
    const FStamped* Damaged = Log.Last(ESoraBossPhase::Countered, TEXT("tether_lash"));
    TestTrue(TEXT("「……設備に損傷。」"), Damaged && Damaged->Event.Line == FName(TEXT("ch05.b16.tarifa.007")));
    TestEqual(TEXT("Mantle down and staggered, a cut does 125"), Cut(*Boss, *Hero, 100.f, 0.f), 125.f);
    // The rod sweep: guard the first blow, awase the second.
    if (!Rest(Arena) || !Until(Arena, 300, [&]() { return !Boss->IsStaggered(); }))
        return Stopped(*this, __LINE__);
    Stand(Arena, *Boss, 200.f);
    FBlow Sweep;
    if (!Meet(Arena, Log, *Boss, TEXT("rod_sweep"), EStance::Parry, Sweep, 2))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("The first blow lands whole"), Sweep.HeroDamage, 28.f);
    TestEqual(TEXT("The second is met with awase"), Sweep.Parried, 1);
    TestTrue(TEXT("and staggers her"), Sweep.bStaggered);
    // A channel opens on the side: the glow first, then the heat, every second.
    Boss->Hold(60000);
    Arena.PlaceHero(FVector(0.f, 900.f, 0.f), 0.f);
    const float OnChannel = Hero->Health;
    if (!Until(Arena, 900, [&]() { return Log.Count(ESoraBossPhase::Strike, TEXT("channel_cycle")) >= 2; }))
        return Stopped(*this, __LINE__);
    TestTrue(TEXT("A flowing channel burns whoever stands in it"), OnChannel - Hero->Health >= 70.f);
    Arena.PlaceHero(FVector::ZeroVector, 0.f);
    // Phases at 65% (automata) and 30% (steam).
    Boss->Hold(0);
    if (!WalkPhases(*this, Arena, Log, *Boss))
        return Stopped(*this, __LINE__);
    TestTrue(TEXT("Loom automata came at 65%"), Log.Count(ESoraBossPhase::Event, TEXT("loom_pair")) >= 1);
    // Lured into the steam, her mantle overloads.
    Boss->Hold(60000);
    const int32 Steams = Log.Count(ESoraBossPhase::Windup, TEXT("steam_burst"));
    if (!Until(Arena, 900, [&]() { return Log.Count(ESoraBossPhase::Windup, TEXT("steam_burst")) > Steams; }))
        return Stopped(*this, __LINE__);
    Boss->SetActorLocation(FVector(900.f, 0.f, Boss->GetActorLocation().Z));
    const int32 Downs = Log.Count(ESoraBossPhase::Event, TEXT("mantle_down"));
    if (!Until(Arena, 200, [&]() { return Log.Count(ESoraBossPhase::Event, TEXT("mantle_down")) > Downs; }))
        return Stopped(*this, __LINE__);
    TestFalse(TEXT("Steam on her drops the mantle"), Boss->IsMantleUp());
    // The counterplay to the end: snap the lash, cut while her mantle is down.
    Boss->Hold(0);
    for (int32 Round = 0; Round < 8 && Boss->IsAlive(); ++Round)
    {
        if (!Rest(Arena))
            return Stopped(*this, __LINE__);
        Stand(Arena, *Boss, 700.f);
        FBlow Lash;
        if (!Meet(Arena, Log, *Boss, TEXT("tether_lash"), EStance::Parry, Lash) || !TestTrue(TEXT("The cable snaps"), Lash.Parried == 1))
            return Stopped(*this, __LINE__);
        for (int32 Blow = 0; Blow < 3 && Boss->IsAlive(); ++Blow)
        {
            Cut(*Boss, *Hero, 100.f, 0.f);
            if (!Wait(Arena, Log, 450.0))
                return Stopped(*this, __LINE__);
        }
    }
    TestTrue(TEXT("At 10% every channel opened once"), Log.Count(ESoraBossPhase::Windup, TEXT("full_open")) == 1);
    if (!Defeated(*this, Log, *Boss, TEXT("kill")))
        return Stopped(*this, __LINE__);
    CheckTelegraphs(*this, Log, *Boss);
    return Arena.Tick(2);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraBossEskroTest,
    "SoraArena.Boss.Eskro",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraBossEskroTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraBossAutomation;
    FArena Arena(*this, TEXT("BossEskro"));
    FLog Log;
    if (!Starts(*this, Arena, Log))
        return Stopped(*this, __LINE__);
    ASoraBoss* Boss = Spawn(Arena, TEXT("boss_eskro"), 900.f);
    ASoraPlayerCharacter* Hero = Arena.Hero();
    if (!TestNotNull(TEXT("Eskro spawns"), Boss))
        return Stopped(*this, __LINE__);
    ASoraEnemyController* Brain = FArena::Brain(Boss);
    if (!TestNotNull(TEXT("He has a brain to hear with"), Brain))
        return Stopped(*this, __LINE__);
    // Standing still through a pulse, the hero stays unfound.
    const int32 Pulses = Log.Count(ESoraBossPhase::Strike, TEXT("reconcile_pulse"));
    if (!Until(Arena, 900, [&]() { return Log.Count(ESoraBossPhase::Strike, TEXT("reconcile_pulse")) > Pulses; }) || !Wait(Arena, Log, 800.0))
        return Stopped(*this, __LINE__);
    TestFalse(TEXT("A still hero is not revealed by the pulse"), Boss->KnowsHero());
    TestEqual(TEXT("and nothing pounces"), Log.Count(ESoraBossPhase::Windup, TEXT("pounce")), 0);
    // A thrown stone's clatter draws the pounce onto empty floor.
    const FVector Lure(500.f, 700.f, Hero->GetActorLocation().Z);
    Brain->HearNoise(SoraStealthRules::ENoise::Melee, Lure, Lure, nullptr);
    if (!Until(Arena, 120, [&]() { return Log.Count(ESoraBossPhase::Windup, TEXT("pounce")) > 0; }))
        return Stopped(*this, __LINE__);
    const int32 Misses = Log.Count(ESoraBossPhase::Event, TEXT("missed"));
    if (!Until(Arena, 120, [&]() { return Log.Count(ESoraBossPhase::Event, TEXT("missed")) > Misses; }))
        return Stopped(*this, __LINE__);
    const FStamped* Missed = Log.Last(ESoraBossPhase::Event, TEXT("missed"));
    TestTrue(TEXT("He misses and says 「……誤差。」"), Missed && Missed->Event.Line == FName(TEXT("ch06.b13.eskro.004")));
    TestTrue(TEXT("He landed at the lure"), FVector::Dist2D(Boss->GetActorLocation(), Lure) < 120.f);
    // In his long recovery a strike from behind does half again.
    TestEqual(TEXT("A rear strike during the missed pounce's recovery does x1.5"), Cut(*Boss, *Hero, 100.f, 180.f), 150.f);
    // Moving as the pulse's ring passes reveals the hero, and the pounce finds him.
    if (!Until(Arena, 300, [&]() { return Boss->BossAttackIndex() == INDEX_NONE; }))
        return Stopped(*this, __LINE__);
    const int32 Next = Log.Count(ESoraBossPhase::Windup, TEXT("reconcile_pulse"));
    if (!Until(Arena, 900, [&]() { return Log.Count(ESoraBossPhase::Windup, TEXT("reconcile_pulse")) > Next; }))
        return Stopped(*this, __LINE__);
    const FStamped Chirp = *Log.Last(ESoraBossPhase::Windup, TEXT("reconcile_pulse"));
    const double Passes = Chirp.Ms + Chirp.Event.WindupMs + FVector::Dist2D(Boss->GetActorLocation(), Hero->GetActorLocation()) / 1800.0 * 720.0;
    const int32 Reveals = Log.Count(ESoraBossPhase::Event, TEXT("revealed"));
    const int32 Pounces = Log.Count(ESoraBossPhase::Windup, TEXT("pounce"));
    const float Found = Hero->Health;
    if (!Until(Arena, 200, [&]() { return Log.Now() >= Passes - 40.0; }))
        return Stopped(*this, __LINE__);
    for (int32 Frame = 0; Frame < 12 && Log.Count(ESoraBossPhase::Event, TEXT("revealed")) == Reveals; ++Frame)
    {
        Hero->GetCharacterMovement()->Velocity = FVector(0.f, 300.f, 0.f);
        if (!Arena.Tick(1))
            return Stopped(*this, __LINE__);
    }
    Hero->GetCharacterMovement()->StopMovementImmediately();
    TestTrue(TEXT("A moving hero is found by the pulse"), Log.Count(ESoraBossPhase::Event, TEXT("revealed")) > Reveals);
    if (!Until(Arena, 200, [&]() { return Log.Count(ESoraBossPhase::Windup, TEXT("pounce")) > Pounces; }) ||
        !Until(Arena, 120, [&]() { return Boss->IsRecovering(); }))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("The pounce lands on the revealed hero"), Found - Hero->Health, 45.f);
    // Revealed within reach, the claws come: awase on the third swipe.
    if (!Rest(Arena))
        return Stopped(*this, __LINE__);
    Stand(Arena, *Boss, 200.f);
    Brain->HearNoise(SoraStealthRules::ENoise::Melee, Hero->GetActorLocation(), Hero->GetActorLocation(), Hero);
    FBlow Claws;
    if (!Meet(Arena, Log, *Boss, TEXT("claw_flurry"), EStance::Parry, Claws, 3))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("The first two swipes land"), Claws.HeroDamage, 36.f);
    TestEqual(TEXT("The third is met with awase"), Claws.Parried, 1);
    TestTrue(TEXT("and staggers him"), Claws.bStaggered);
    // The flood at 60% and the frenzy at 25%, with its audit hounds.
    if (!WalkPhases(*this, Arena, Log, *Boss))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("Two audit hounds join the frenzy"), Boss->LiveAdds(), 2);
    // The hounds would call the hero's place to him; they are shot down first.
    for (TActorIterator<ASoraEnemy> It(Arena.Get()); It; ++It)
        if (It->Summoner() == Boss && It->IsAlive())
            UGameplayStatics::ApplyDamage(*It, It->Health, Hero->GetController(), Hero, UDamageType::StaticClass());
    if (!Arena.Tick(2))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("The hounds are down"), Boss->LiveAdds(), 0);
    // The counterplay to the end: lure, let him miss twice, strike his back.
    for (int32 Round = 0; Round < 6 && Boss->IsAlive(); ++Round)
    {
        if (!Until(Arena, 900, [&]() { return Boss->BossAttackIndex() == INDEX_NONE && !Boss->IsStaggered(); }))
            return Stopped(*this, __LINE__);
        const FVector Stone = Boss->GetActorLocation() + FVector(0.f, 700.f, 0.f);
        const int32 Missing = Log.Count(ESoraBossPhase::Event, TEXT("missed"));
        Brain->HearNoise(SoraStealthRules::ENoise::Melee, Stone, Stone, nullptr);
        if (!Until(Arena, 400, [&]() { return Boss->IsRecovering() && Log.Count(ESoraBossPhase::Event, TEXT("missed")) > Missing; }))
            return Stopped(*this, __LINE__);
        for (int32 Blow = 0; Blow < 3 && Boss->IsAlive(); ++Blow)
        {
            Cut(*Boss, *Hero, 100.f, 180.f);
            if (!Wait(Arena, Log, 300.0))
                return Stopped(*this, __LINE__);
        }
    }
    if (!Defeated(*this, Log, *Boss, TEXT("capture")))
        return Stopped(*this, __LINE__);
    CheckTelegraphs(*this, Log, *Boss);
    return Arena.Tick(2);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraBossCollateraTest,
    "SoraArena.Boss.Collatera",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraBossCollateraTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraBossAutomation;
    FArena Arena(*this, TEXT("BossCollatera"));
    FLog Log;
    if (!Starts(*this, Arena, Log))
        return Stopped(*this, __LINE__);
    ASoraBoss* Boss = Spawn(Arena, TEXT("boss_collatera"), 1000.f);
    ASoraPlayerCharacter* Hero = Arena.Hero();
    if (!TestNotNull(TEXT("Collatera spawns"), Boss))
        return Stopped(*this, __LINE__);
    Boss->Hold(60000);
    if (!Arena.Tick(2))
        return Stopped(*this, __LINE__);
    // Her barrier soaks every hit; a charged Plasma Matchlock strips half of it.
    TestEqual(TEXT("Her barrier holds 240"), Boss->BarrierPoints(), 240);
    TestEqual(TEXT("A cut on the barrier does nothing to her"), Cut(*Boss, *Hero, 100.f, 0.f), 0.f);
    TestEqual(TEXT("and melee soaks a quarter more"), Boss->BarrierPoints(), 115);
    TestEqual(TEXT("The Plasma Matchlock's hit is soaked"),
        Hit(*Boss, *Hero, 90.f, CombatRules::EHit::Ranged, Around(*Boss, 0.f, 900.f), 14), 0.f);
    TestEqual(TEXT("but strips 120 and breaks it"), Boss->BarrierPoints(), 0);
    const FStamped* Undercapitalised = Log.Last(ESoraBossPhase::Event, TEXT("barrier_broken"));
    TestTrue(TEXT("「……資本不足。」"), Undercapitalised && Undercapitalised->Event.Line == FName(TEXT("ch07.b13.collatera.005")));
    TestTrue(TEXT("Broken, the next shot lands"), Hit(*Boss, *Hero, 30.f, CombatRules::EHit::Ranged, Around(*Boss, 0.f, 900.f), 1) > 0.f);
    if (!Wait(Arena, Log, 4600.0))
        return Stopped(*this, __LINE__);
    TestTrue(TEXT("Four quiet seconds and it regenerates"), Boss->BarrierPoints() > 0);
    // The twin burst locks on: strafing 1.5 m breaks the lock; standing takes six rounds.
    Boss->Hold(0);
    FBlow Standing;
    Face(Arena, *Boss);
    if (!Meet(Arena, Log, *Boss, TEXT("twin_burst"), EStance::None, Standing))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("Six locked rounds find a still hero"), Standing.HeroDamage, 54.f);
    const int32 Bursts = Log.Count(ESoraBossPhase::Windup, TEXT("twin_burst"));
    if (!Until(Arena, 900, [&]() { return Boss->BossAttackIndex() == INDEX_NONE; }) || !Boss->ForceAttack(TEXT("twin_burst")) ||
        !Until(Arena, 120, [&]() { return Log.Count(ESoraBossPhase::Windup, TEXT("twin_burst")) > Bursts; }))
        return Stopped(*this, __LINE__);
    Arena.PlaceHero(Hero->GetActorLocation() + FVector(0.f, 250.f, 0.f), Hero->GetActorRotation().Yaw);
    const float Strafed = Hero->Health;
    if (!Until(Arena, 120, [&]() { return Boss->IsRecovering(); }))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("A strafe of 2.5 m in the windup breaks the lock"), Strafed - Hero->Health, 0.f);
    // Her reload drops the barrier: anything lands.
    Boss->Hold(60000);
    if (!Wait(Arena, Log, 3000.0))
        return Stopped(*this, __LINE__);
    TestTrue(TEXT("Rested, her barrier is back"), Boss->BarrierPoints() > 0);
    Boss->Hold(0);
    FBlow Reload;
    if (!Until(Arena, 900, [&]() { return Boss->BossAttackIndex() == INDEX_NONE; }) || !Boss->ForceAttack(TEXT("reload")) ||
        !Until(Arena, 120, [&]() { return Boss->IsBarrierOffline(); }))
        return Stopped(*this, __LINE__);
    const FStamped* Reloading = Log.Last(ESoraBossPhase::Windup, TEXT("reload"));
    TestTrue(TEXT("「残高、補充。」"), Reloading && Reloading->Event.Line == FName(TEXT("ch07.b13.collatera.003")));
    TestEqual(TEXT("During the reload an arrow lands whole"),
        Hit(*Boss, *Hero, 52.f, CombatRules::EHit::Ranged, Around(*Boss, 0.f, 900.f), 18), 52.f);
    // Margin calls strike marked cover (P2), then the sabre (P3), her barrier burnt out.
    if (!Until(Arena, 300, [&]() { return Boss->BossAttackIndex() == INDEX_NONE; }) || !WalkPhases(*this, Arena, Log, *Boss))
        return Stopped(*this, __LINE__);
    TestFalse(TEXT("At 30% her barrier cell burns out"), Boss->HasBarrier());
    TestTrue(TEXT("Two drones marked the margin phase"), Log.Count(ESoraBossPhase::Event, TEXT("drone_pair")) >= 1);
    // The sabre: awase the second of the pair; the off-hand shot cannot be parried.
    if (!Rest(Arena))
        return Stopped(*this, __LINE__);
    Stand(Arena, *Boss, 180.f);
    FBlow Pair;
    if (!Meet(Arena, Log, *Boss, TEXT("cut_pair"), EStance::Parry, Pair, 2))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("The first cut lands"), Pair.HeroDamage, 22.f);
    TestEqual(TEXT("The second is met with awase"), Pair.Parried, 1);
    TestTrue(TEXT("and staggers her"), Pair.bStaggered);
    if (!Rest(Arena))
        return Stopped(*this, __LINE__);
    Stand(Arena, *Boss, 400.f);
    FBlow Shot;
    if (!Meet(Arena, Log, *Boss, TEXT("offhand_shot"), EStance::Parry, Shot))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("The off-hand shot is never parried"), Shot.Parried, 0);
    TestEqual(TEXT("A guard halves it"), Shot.HeroDamage, 7.f);
    // The counterplay to the end: awase the lunge or the second cut, cut in the stagger.
    for (int32 Round = 0; Round < 10 && Boss->IsAlive(); ++Round)
    {
        if (!Rest(Arena))
            return Stopped(*this, __LINE__);
        Stand(Arena, *Boss, Round % 2 ? 180.f : 500.f);
        FBlow Opening;
        const bool bLunge = Round % 2 == 0;
        if (!Meet(Arena, Log, *Boss, bLunge ? TEXT("fleche_lunge") : TEXT("cut_pair"), EStance::Parry, Opening, bLunge ? 1 : 2) ||
            !TestTrue(TEXT("Awase opens her"), Opening.bStaggered))
            return Stopped(*this, __LINE__);
        Stand(Arena, *Boss, 150.f);
        Cut(*Boss, *Hero, 100.f, 0.f);
        if (!Wait(Arena, Log, 400.0))
            return Stopped(*this, __LINE__);
        if (Boss->IsAlive())
            Cut(*Boss, *Hero, 100.f, 0.f);
    }
    if (!Defeated(*this, Log, *Boss, TEXT("disarm")))
        return Stopped(*this, __LINE__);
    const FStamped* Dishonoured = Log.Last(ESoraBossPhase::Defeated);
    TestTrue(TEXT("「……不渡り、ですか。」"), Dishonoured && Dishonoured->Event.Line == FName(TEXT("ch07.b13.collatera.013")));
    CheckTelegraphs(*this, Log, *Boss);
    return Arena.Tick(2);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraBossValAmortTest,
    "SoraArena.Boss.ValAmort",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraBossValAmortTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraBossAutomation;
    FArena Arena(*this, TEXT("BossValAmort"));
    FLog Log;
    if (!Starts(*this, Arena, Log))
        return Stopped(*this, __LINE__);
    ASoraBoss* Boss = Spawn(Arena, TEXT("boss_val_amort"), 300.f);
    ASoraPlayerCharacter* Hero = Arena.Hero();
    USoraEquipmentComponent* Kit = Hero->GetEquipment();
    if (!TestNotNull(TEXT("Val Amort spawns"), Boss))
        return Stopped(*this, __LINE__);
    Boss->Hold(60000);
    if (!Arena.Tick(2))
        return Stopped(*this, __LINE__);
    // Three ledger shards take the ranged fire until they break; then he reels.
    TestEqual(TEXT("Three ledger shards orbit him"), Boss->LiveWards(), 3);
    const float Health = Boss->Health;
    for (int32 Arrow = 0; Arrow < 6; ++Arrow)
        Hit(*Boss, *Hero, 52.f, CombatRules::EHit::Ranged, Around(*Boss, 0.f, 800.f), 18);
    TestEqual(TEXT("The shards took all six arrows"), Boss->Health, Health);
    TestEqual(TEXT("and all three broke"), Boss->LiveWards(), 0);
    TestTrue(TEXT("Their breaking stuns him"), Boss->IsStunned());
    TestEqual(TEXT("Stunned, he takes half again"), Cut(*Boss, *Hero, 100.f, 0.f), 150.f);
    // The cleave: awase staggers; the debt beam goes through any guard.
    Boss->Hold(0);
    if (!Rest(Arena) || !Until(Arena, 300, [&]() { return !Boss->IsStaggered(); }))
        return Stopped(*this, __LINE__);
    Stand(Arena, *Boss, 250.f);
    FBlow Cleave;
    if (!Meet(Arena, Log, *Boss, TEXT("amort_cleave"), EStance::Parry, Cleave))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("The cleave is met with awase"), Cleave.Parried, 1);
    TestTrue(TEXT("and he staggers"), Cleave.bStaggered);
    if (!Rest(Arena) || !Until(Arena, 300, [&]() { return !Boss->IsStaggered(); }))
        return Stopped(*this, __LINE__);
    FBlow Beam;
    if (!Meet(Arena, Log, *Boss, TEXT("amort_ledger_beam"), EStance::Guard, Beam))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("No guard stops the ledger beam"), Beam.HeroDamage, 22.f);
    TestEqual(TEXT("It is not guarded"), Beam.Guarded + Beam.Parried, 0);
    // His phases at 70% and 40%.
    if (!WalkPhases(*this, Arena, Log, *Boss))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("The sword-cane phase"), Boss->PhaseIndex(), 2);
    CheckTelegraphs(*this, Log, *Boss);
    // The seizure phase's shield and field, on a collector restored at that phase.
    Boss->Destroy();
    if (!Arena.Tick(2))
        return Stopped(*this, __LINE__);
    FSoraBossSetup Seizure;
    Seizure.Phase = 1;
    ASoraBoss* Second = Spawn(Arena, TEXT("boss_val_amort"), 400.f, Seizure);
    if (!TestNotNull(TEXT("The collector restored at the seizure phase"), Second) || !Arena.Tick(2))
        return Stopped(*this, __LINE__);
    Second->Hold(60000);
    if (!Until(Arena, 120, [&]() { return Second->LiveAdds() == 2; }))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("Collateral constructs rise"), Second->LiveAdds(), 2);
    TestTrue(TEXT("While they stand he cannot be hurt"), Second->IsInvulnerable() && Cut(*Second, *Hero, 100.f, 0.f) == 0.f);
    TArray<ASoraEnemy*> Constructs;
    for (TActorIterator<ASoraEnemy> It(Arena.Get()); It; ++It)
        if (It->Summoner() == Second && It->IsAlive())
            Constructs.Add(*It);
    for (ASoraEnemy* Construct : Constructs)
        UGameplayStatics::ApplyDamage(Construct, Construct->Health, Hero->GetController(), Hero, UDamageType::StaticClass());
    if (!Arena.Tick(2))
        return Stopped(*this, __LINE__);
    TestFalse(TEXT("Cleared, his seizure shield drops"), Second->IsInvulnerable());
    TestTrue(TEXT("and a cut lands"), Cut(*Second, *Hero, 100.f, 0.f) > 0.f);
    if (!Wait(Arena, Log, 10100.0))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("Ten seconds on, the constructs return"), Second->LiveAdds(), 2);
    // The seizure field: marked tiles give way under whoever stands on them.
    Second->Hold(0);
    const float BeforeField = Hero->Health;
    const int32 Fields = Log.Count(ESoraBossPhase::Strike, TEXT("amort_seizure_field"));
    if (!Until(Arena, 1200, [&]() { return Log.Count(ESoraBossPhase::Strike, TEXT("amort_seizure_field")) > Fields; }))
        return Stopped(*this, __LINE__);
    TestTrue(TEXT("A tile gave way under the hero"), BeforeField - Hero->Health >= 25.f);
    CheckTelegraphs(*this, Log, *Second);
    Second->Destroy();
    if (!Arena.Tick(2))
        return Stopped(*this, __LINE__);
    // The sword-cane, restored at phase three: a floor only mutō-dori passes.
    FSoraBossSetup Cane;
    Cane.Phase = 2;
    ASoraBoss* Third = Spawn(Arena, TEXT("boss_val_amort"), 220.f, Cane);
    if (!TestNotNull(TEXT("The collector restored at the cane phase"), Third) || !Arena.Tick(2))
        return Stopped(*this, __LINE__);
    Third->Hold(60000);
    Scripted(*Third, Arena, Third->Health - 40.f);
    TestEqual(TEXT("A blow stops at his 1% floor"), Cut(*Third, *Hero, 100.f, 0.f), 16.f);
    TestEqual(TEXT("and no further"), Cut(*Third, *Hero, 100.f, 0.f), 0.f);
    TestEqual(TEXT("He stands at 24"), Third->Health, 24.f);
    // Blade drawn, a held guard is no answer to the final foreclosure.
    Third->Hold(0);
    if (!Rest(Arena))
        return Stopped(*this, __LINE__);
    Stand(Arena, *Third, 200.f);
    FBlow Held;
    if (!Meet(Arena, Log, *Third, TEXT("amort_final_foreclosure"), EStance::Guard, Held))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("The final foreclosure goes through a held guard"), Held.HeroDamage, 45.f);
    // Sheathed but mistimed: the whole blow lands.
    if (!Rest(Arena))
        return Stopped(*this, __LINE__);
    Kit->Sheathe(true);
    if (!Wait(Arena, Log, CombatRules::SheatheMs + 50.0) || !TestTrue(TEXT("The blade is sheathed"), Kit->IsSheathed()))
        return Stopped(*this, __LINE__);
    FBlow Early;
    if (!Meet(Arena, Log, *Third, TEXT("amort_final_foreclosure"), EStance::Guard, Early))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("A mistimed mutō-dori takes the whole blow"), Early.HeroDamage, 45.f);
    TestTrue(TEXT("and takes nothing from him"), Third->IsAlive());
    // 無刀取り: sheathed, a guard pressed just before the foreclosure lands.
    if (!Rest(Arena))
        return Stopped(*this, __LINE__);
    Kit->Sheathe(true);
    FBlow Muto;
    const int32 Hurts = Log.Damaged.Num();
    if (!Meet(Arena, Log, *Third, TEXT("amort_final_foreclosure"), EStance::Parry, Muto))
        return Stopped(*this, __LINE__);
    if (!TestEqual(TEXT("Mutō-dori takes none of the blow"), Muto.HeroDamage, 0.f))
        for (int32 Index = Hurts; Index < Log.Damaged.Num(); ++Index)
            AddInfo(FString::Printf(TEXT("hurt %.0f by %s at %.1f ms"), Log.Damaged[Index].Key.Amount,
                *GetNameSafe(Log.Damaged[Index].Key.Causer), Log.Damaged[Index].Value));
    const FStamped* Taken = Log.Last(ESoraBossPhase::Defeated);
    TestTrue(TEXT("「……計算に、ありません。」"), Taken && Taken->Event.Line == FName(TEXT("ch08.b14.valamort.009")));
    Kit->Sheathe(false);
    if (!Defeated(*this, Log, *Third, TEXT("muto_dori")))
        return Stopped(*this, __LINE__);
    CheckTelegraphs(*this, Log, *Third);
    return Arena.Tick(2);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraBossToranosukeSteelTest,
    "SoraArena.Boss.ToranosukeSteel",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraBossToranosukeSteelTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraBossAutomation;
    FArena Arena(*this, TEXT("BossToranosukeSteel"));
    FLog Log;
    if (!Starts(*this, Arena, Log))
        return Stopped(*this, __LINE__);
    ASoraBoss* Rival = Spawn(Arena, TEXT("duel_toranosuke_steel"), 200.f);
    ASoraPlayerCharacter* Hero = Arena.Hero();
    USoraEquipmentComponent* Kit = Hero->GetEquipment();
    if (!TestNotNull(TEXT("Toranosuke draws steel"), Rival))
        return Stopped(*this, __LINE__);
    // His kesa combination: awase any cut staggers him.
    FBlow Kesa;
    Face(Arena, *Rival);
    if (!Meet(Arena, Log, *Rival, TEXT("kesa_combo"), EStance::Parry, Kesa, 1, false))
        return Stopped(*this, __LINE__);
    const FStamped* Opening = Log.First(ESoraBossPhase::Windup);
    TestTrue(TEXT("His duel opens with the kesa combination"), Opening && Opening->Event.Detail == FName(TEXT("kesa_combo")));
    TestEqual(TEXT("The first cut is met with awase"), Kesa.Parried, 1);
    TestTrue(TEXT("which staggers him"), Kesa.bStaggered);
    TestEqual(TEXT("and stops the rest of the combination"), Kesa.HeroDamage, 0.f);
    // The two-handed thrust cannot be parried: half through the guard, 40 stamina.
    if (!Rest(Arena))
        return Stopped(*this, __LINE__);
    Stand(Arena, *Rival, 200.f);
    FBlow Tsuki;
    const float Stamina = Kit->GuardReserve();
    if (!Meet(Arena, Log, *Rival, TEXT("morote_tsuki"), EStance::Parry, Tsuki))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("The thrust is never parried"), Tsuki.Parried, 0);
    TestEqual(TEXT("A guard lets half through"), Tsuki.HeroDamage, 15.f);
    TestTrue(TEXT("and costs 40 stamina"), Stamina - Kit->GuardReserve() >= 40.f - .5f);
    // A turtling guard draws the shoulder check.
    if (!Rest(Arena))
        return Stopped(*this, __LINE__);
    Stand(Arena, *Rival, 150.f);
    const int32 Checks = Log.Count(ESoraBossPhase::Windup, TEXT("taiatari"));
    if (!Until(Arena, 300, [&]() { return Rival->BossAttackIndex() == INDEX_NONE && !Rival->IsStaggered(); }))
        return Stopped(*this, __LINE__);
    Rival->Hold(1600);
    if (!Press(Arena, EKeys::LeftControl, true) ||
        !Until(Arena, 400, [&]() { return Log.Count(ESoraBossPhase::Windup, TEXT("taiatari")) > Checks; }) ||
        !Press(Arena, EKeys::LeftControl, false))
        return Stopped(*this, __LINE__);
    TestTrue(TEXT("Holding a guard past 1.5 s draws the shoulder check"), Log.Count(ESoraBossPhase::Windup, TEXT("taiatari")) > Checks);
    // His floor: until disarmed, he cannot be beaten.
    Rival->Hold(60000);
    if (!Until(Arena, 300, [&]() { return Rival->BossAttackIndex() == INDEX_NONE; }))
        return Stopped(*this, __LINE__);
    // Phase two at half: only committed vertical cuts, every one mutō-dori's.
    if (!WalkPhases(*this, Arena, Log, *Rival))
        return Stopped(*this, __LINE__);
    Scripted(*Rival, Arena, Rival->Health - 70.f);
    TestEqual(TEXT("A cut stops at his 10% floor"), Cut(*Rival, *Hero, 60.f, 0.f), 10.f);
    TestEqual(TEXT("He cannot be cut down"), Cut(*Rival, *Hero, 60.f, 0.f), 0.f);
    Rival->Hold(0);
    // 無刀取り on his vertical cut ends the duel.
    if (!Rest(Arena))
        return Stopped(*this, __LINE__);
    Stand(Arena, *Rival, 200.f);
    Kit->Sheathe(true);
    if (!Wait(Arena, Log, CombatRules::SheatheMs + 50.0))
        return Stopped(*this, __LINE__);
    FBlow Muto;
    if (!Meet(Arena, Log, *Rival, TEXT("makko_giri"), EStance::Parry, Muto))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("Mutō-dori takes none of the cut"), Muto.HeroDamage, 0.f);
    const FStamped* Cry = Log.First(ESoraBossPhase::Windup, TEXT("makko_giri"));
    TestTrue(TEXT("His first vertical cut cries 「全部、払ったんだ！」"), Cry && Cry->Event.Line == FName(TEXT("ch06.b09.toranosuke.008")));
    if (Log.Count(ESoraBossPhase::Windup, TEXT("makko_giri")) > 1)
        TestEqual(TEXT("and only the first"), Log.Last(ESoraBossPhase::Windup, TEXT("makko_giri"))->Event.Line, FName());
    Kit->Sheathe(false);
    if (!Defeated(*this, Log, *Rival, TEXT("muto_dori")))
        return Stopped(*this, __LINE__);
    CheckTelegraphs(*this, Log, *Rival);
    return Arena.Tick(2);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraBossToranosukeFukuroTest,
    "SoraArena.Boss.ToranosukeFukuro",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraBossToranosukeFukuroTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraBossAutomation;
    FArena Arena(*this, TEXT("BossToranosukeFukuro"));
    FLog Log;
    if (!Starts(*this, Arena, Log))
        return Stopped(*this, __LINE__);
    ASoraBoss* Rival = Spawn(Arena, TEXT("duel_toranosuke_fukuro"), 200.f);
    ASoraPlayerCharacter* Hero = Arena.Hero();
    if (!TestNotNull(TEXT("Toranosuke takes up his fukuro-shinai"), Rival))
        return Stopped(*this, __LINE__);
    const FSoraBossData& Data = *Rival->Data();
    const FSoraBossHabit& Even = Data.Phases[0].Habits[0];
    // His habits while even: the same fixed rotation the weights give, never a roll.
    SoraBossRules::FWeighted Replica = SoraBossRules::Fresh();
    int32 Weights[SoraBossRules::MaxWeighted] = {};
    for (int32 Index = 0; Index < Even.Weights.Num(); ++Index)
        Weights[Index] = Even.Weights[Index];
    TArray<FName> Expected;
    for (int32 Pick = 0; Pick < 8; ++Pick)
        Expected.Add(Data.Attacks[Even.Attacks[SoraBossRules::PickWeighted(Replica, Weights, Even.Attacks.Num())]].Id);
    const int32 Mark = Log.Boss.Num();
    TArray<FName> Seen;
    // A lure's real kote is part of the lure, not a pick of its own.
    const auto Collect = [&]()
    {
        Seen.Reset();
        FName Last;
        for (int32 Entry = Mark; Entry < Log.Boss.Num(); ++Entry)
        {
            if (Log.Boss[Entry].Event.Phase != ESoraBossPhase::Windup)
                continue;
            const FName Detail = Log.Boss[Entry].Event.Detail;
            if (!(Detail == TEXT("tora_kote") && Last == TEXT("tora_feint")))
                Seen.Add(Detail);
            Last = Detail;
        }
        return Seen.Num() >= 8;
    };
    Face(Arena, *Rival);
    if (!Until(Arena, 3000, Collect))
        return Stopped(*this, __LINE__);
    for (int32 Index = 0; Index < 8; ++Index)
        TestEqual(*FString::Printf(TEXT("Even score, attack %d follows his weighted habits"), Index), Seen[Index], Expected[Index]);
    // Leading by two, the hero sees his haste: the lead-two habits.
    Rival->SetDuelScore(2, 0);
    const int32 Lead = Log.Boss.Num();
    if (!Until(Arena, 3000, [&]()
        {
            for (int32 Entry = Lead; Entry < Log.Boss.Num(); ++Entry)
                if (Log.Boss[Entry].Event.Phase == ESoraBossPhase::Windup &&
                    (Log.Boss[Entry].Event.Detail == TEXT("tora_nidan") || Log.Boss[Entry].Event.Detail == TEXT("tora_seme")))
                    return true;
            return false;
        }))
        return Stopped(*this, __LINE__);
    TestTrue(TEXT("Behind by two he hurries into two-step cuts and pressure"), true);
    // The lure: awase only on the real kote; a guard raised on the fake is only a guard.
    Rival->SetDuelScore(0, 0);
    if (!Rest(Arena))
        return Stopped(*this, __LINE__);
    Stand(Arena, *Rival, 200.f);
    FBlow Fake;
    const int32 Kotes = Log.Count(ESoraBossPhase::Windup, TEXT("tora_kote"));
    if (!Until(Arena, 900, [&]() { return Rival->BossAttackIndex() == INDEX_NONE && !Rival->IsStaggered(); }) ||
        !Rival->ForceAttack(TEXT("tora_feint")) || !Until(Arena, 120, [&]() { return Rival->IsBossTelegraphing(); }))
        return Stopped(*this, __LINE__);
    const double FakeEnds = Log.Last(ESoraBossPhase::Windup, TEXT("tora_feint"))->Ms + 250.0;
    if (!Until(Arena, 120, [&]() { return Log.Now() >= FakeEnds - 60.0; }) || !Press(Arena, EKeys::LeftControl, true))
        return Stopped(*this, __LINE__);
    const int32 Parried = Log.ParriedBy(Rival), Guarded = Log.GuardedBy(Rival);
    if (!Until(Arena, 200, [&]() { return Log.ParriedBy(Rival) + Log.GuardedBy(Rival) > Parried + Guarded; }) ||
        !Press(Arena, EKeys::LeftControl, false))
        return Stopped(*this, __LINE__);
    TestTrue(TEXT("The lure turns into his kote"), Log.Count(ESoraBossPhase::Windup, TEXT("tora_kote")) > Kotes);
    TestEqual(TEXT("A guard raised on the fake is no awase"), Log.ParriedBy(Rival) - Parried, 0);
    if (!Rest(Arena))
        return Stopped(*this, __LINE__);
    FBlow Real;
    if (!Meet(Arena, Log, *Rival, TEXT("tora_kote"), EStance::Parry, Real))
        return Stopped(*this, __LINE__);
    TestEqual(TEXT("Awase on the real kote"), Real.Parried, 1);
    TestTrue(TEXT("staggers him"), Real.bStaggered);
    // A points bout: every clean hit lands, but he never falls.
    Rival->Hold(60000);
    for (int32 Blow = 0; Blow < 20; ++Blow)
        Cut(*Rival, *Hero, 60.f, 0.f);
    TestEqual(TEXT("He never falls below his floor"), Rival->Health, 60.f);
    TestTrue(TEXT("and stays in the bout"), Rival->IsAlive() && !Rival->IsDefeated());
    TestFalse(TEXT("He is sparring, never lethal"), Data.bLethal);
    CheckTelegraphs(*this, Log, *Rival);
    return Arena.Tick(2);
}
#endif
