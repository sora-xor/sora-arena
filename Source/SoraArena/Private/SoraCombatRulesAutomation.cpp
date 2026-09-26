#include "SoraGameMode.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Combat/SoraBossCatalog.h"
#include "Combat/SoraCombatEffects.h"
#include "Combat/SoraDamage.h"
#include "Combat/SoraEnemyCatalog.h"
#include "SoraBoss.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraCombatRules.h"
#include "SoraEnemyTestArena.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameEvents.h"
#include "SoraHistoricalArms.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/DamageType.h"
#include "GameFramework/WorldSettings.h"

// Campaign combat in real game worlds, one test per rule: every archetype in
// Content/Data/enemies.json spawns as written; guard and parry meet every
// melee attacker, the collector's cleave included; ranged fire only chips a
// guard; strikes stagger by weight and poise, and a blade's contact holds the
// world (hit-stop); shells arm, burst on their own owner and spare the
// owner's allies; every class melee arm strikes with commitment; debt-bound
// conscripts are subdued, never killed; tower shields stop the front; and
// each ranged archetype's telegraph comes before its damage.
namespace SoraCombatAutomation
{
using SoraEnemyTest::FArena;
namespace Rules = SoraCombatRules;
constexpr float Frame = 1.f / 60.f;

// Every combat announcement in the world, stamped with world time.
struct FLog
{
    template <typename TEvent>
    struct FStamped
    {
        TEvent Event;
        float Time = 0.f;
    };
    TArray<FSoraDefenseEvent> Guarded;
    TArray<FSoraDefenseEvent> Parried;
    TArray<FStamped<FSoraDamagedEvent>> Damaged;
    TArray<FSoraStrikeResolvedEvent> Resolved;
    TArray<FStamped<FSoraMeleeCommittedEvent>> Committed;
    TArray<FStamped<FSoraEnemyCueEvent>> Cues;
    TArray<FStamped<FSoraWeaponFiredEvent>> Fired;
    TArray<FStamped<FSoraDetonatedEvent>> Blasts;
    TArray<FSoraDiedEvent> Died;
    UWorld* World = nullptr;
    TArray<TFunction<void()>> Removers;

    ~FLog() { Detach(); }
    float Now() const { return World ? World->GetTimeSeconds() : 0.f; }
    template <typename TDelegate, typename TEvent>
    void Listen(TDelegate& Delegate, TWeakObjectPtr<USoraGameEvents> Bus, TArray<TEvent>& Into)
    {
        const FDelegateHandle Handle = Delegate.AddLambda([&Into](const TEvent& Event) { Into.Add(Event); });
        Removers.Add([&Delegate, Bus, Handle]() { if (Bus.IsValid()) Delegate.Remove(Handle); });
    }
    template <typename TDelegate, typename TEvent>
    void Stamp(TDelegate& Delegate, TWeakObjectPtr<USoraGameEvents> Bus, TArray<FStamped<TEvent>>& Into)
    {
        const FDelegateHandle Handle = Delegate.AddLambda([this, &Into](const TEvent& Event) { Into.Add({Event, Now()}); });
        Removers.Add([&Delegate, Bus, Handle]() { if (Bus.IsValid()) Delegate.Remove(Handle); });
    }
    bool Attach(UWorld* InWorld)
    {
        World = InWorld;
        USoraGameEvents* Events = USoraGameEvents::Get(InWorld);
        if (!Events)
            return false;
        const TWeakObjectPtr<USoraGameEvents> Bus = Events;
        Listen(Events->OnGuarded, Bus, Guarded);
        Listen(Events->OnParried, Bus, Parried);
        Stamp(Events->OnDamaged, Bus, Damaged);
        Listen(Events->OnStrikeResolved, Bus, Resolved);
        Stamp(Events->OnMeleeCommitted, Bus, Committed);
        Stamp(Events->OnEnemyCue, Bus, Cues);
        Stamp(Events->OnWeaponFired, Bus, Fired);
        Stamp(Events->OnDetonated, Bus, Blasts);
        Listen(Events->OnDied, Bus, Died);
        return true;
    }
    void Detach()
    {
        for (const TFunction<void()>& Remove : Removers)
            Remove();
        Removers.Reset();
    }
    template <typename TEvent, typename TPredicate>
    static int32 CountIf(const TArray<TEvent>& Events, TPredicate Predicate)
    {
        int32 Count = 0;
        for (const TEvent& Event : Events)
            Count += Predicate(Event) ? 1 : 0;
        return Count;
    }
    int32 GuardedBy(const AActor* Attacker) const { return CountIf(Guarded, [Attacker](const FSoraDefenseEvent& E) { return E.Attacker == Attacker; }); }
    int32 ParriedBy(const AActor* Attacker) const { return CountIf(Parried, [Attacker](const FSoraDefenseEvent& E) { return E.Attacker == Attacker; }); }
    int32 ResolvedBy(const AActor* Attacker) const { return CountIf(Resolved, [Attacker](const FSoraStrikeResolvedEvent& E) { return E.Attacker == Attacker; }); }
    int32 CueCount(const AActor* Enemy, ESoraEnemyCue Cue) const
    {
        return CountIf(Cues, [Enemy, Cue](const FStamped<FSoraEnemyCueEvent>& E) { return E.Event.Enemy == Enemy && E.Event.Cue == Cue; });
    }
    int32 BlastsBy(const AActor* Instigator) const
    {
        return CountIf(Blasts, [Instigator](const FStamped<FSoraDetonatedEvent>& E) { return E.Event.Instigator == Instigator; });
    }
};

// Destroys every opponent, so the next case starts alone with the hero.
void Clear(FArena& Arena)
{
    for (TActorIterator<ASoraEnemy> It(Arena.Get()); It; ++It)
        It->Destroy();
}

bool Press(FArena& Arena, const FKey& Key, bool bDown)
{
    return Arena.World->InjectKey(Key, bDown ? IE_Pressed : IE_Released);
}

// Press and release in one frame, as a tap does.
bool Tap(FArena& Arena, const FKey& Key)
{
    return Press(Arena, Key, true) && Press(Arena, Key, false) && Arena.Tick(1);
}

// Ticks until Done holds or MaxFrames pass; false when the world fails.
bool Until(FArena& Arena, int32 MaxFrames, TFunctionRef<bool()> Done)
{
    for (int32 Index = 0; Index < MaxFrames && !Done(); ++Index)
        if (!Arena.Tick(1))
            return false;
    return true;
}

float Dilation(const FArena& Arena)
{
    return Arena.Get()->GetWorldSettings()->GetEffectiveTimeDilation();
}

// Taps Fire until Nyaakoto's melee arm commits to a strike, which waits out
// any recovery; false when it never does.
bool Swing(FArena& Arena)
{
    USoraEquipmentComponent* Kit = Arena.Hero()->GetEquipment();
    for (int32 Index = 0; Index < 120; ++Index)
    {
        if (!Tap(Arena, EKeys::LeftMouseButton))
            return false;
        if (Kit->IsCommittedStrike())
            return true;
    }
    return false;
}

// Nyaakoto holds a catalog weapon with a full magazine and nothing in recovery.
bool Arm(FArena& Arena, int32 WeaponId)
{
    ASoraPlayerCharacter* Hero = Arena.Hero();
    Hero->GetEquipment()->Hold(WeaponId);
    Hero->RebuildWeapon();
    return Arena.Tick(90);
}

enum class EStance { Parry, Guard, Behind };

struct FBlow
{
    bool bResolved = false;
    bool bRaised = false;
    FSoraEnemyAttack Attack;
    float HeroDamage = 0.f;
    float Stamina = 0.f;
    int32 Guarded = 0;
    int32 Parried = 0;
    float GuardedDamage = -1.f;
    bool bStaggered = false;
    bool bHitStop = false;
};

// Waits for Attacker's next committed blow and meets it: with a guard raised
// no more than 200 ms before the blow lands (a parry), with a guard raised on
// the first frame of its windup and held, or with a held guard and the hero's
// back turned. The guard comes down after the blow.
bool MeetBlow(FArena& Arena, FLog& Log, ASoraEnemy& Attacker, EStance Stance, FBlow& Out)
{
    ASoraPlayerCharacter* Hero = Arena.Hero();
    USoraEquipmentComponent* Kit = Hero->GetEquipment();
    const int32 Resolved = Log.ResolvedBy(&Attacker), Guarded = Log.GuardedBy(&Attacker), Parried = Log.ParriedBy(&Attacker);
    float Health = Hero->Health;
    float Stamina = Kit->GuardReserve();
    for (int32 Index = 0; Index < 900 && !Out.bResolved; ++Index)
    {
        if (!Out.bRaised && Attacker.IsWindingUp() && Attacker.CurrentAttack())
        {
            Out.Attack = *Attacker.CurrentAttack();
            const float RemainingMs = (1.f - Attacker.WindupProgress()) * Out.Attack.WindupMs;
            if (Stance != EStance::Parry || RemainingMs <= 200.f)
            {
                if (!Press(Arena, EKeys::LeftControl, true))
                    return false;
                Out.bRaised = true;
                Health = Hero->Health;
                Stamina = Kit->GuardReserve();
            }
        }
        if (!Arena.Tick(1))
            return false;
        Out.bResolved = Log.ResolvedBy(&Attacker) > Resolved;
    }
    Out.bHitStop = Dilation(Arena) < .5f;
    Out.bStaggered = Attacker.IsStaggered();
    Out.HeroDamage = Health - Hero->Health;
    Out.Stamina = Stamina - Kit->GuardReserve();
    Out.Guarded = Log.GuardedBy(&Attacker) - Guarded;
    Out.Parried = Log.ParriedBy(&Attacker) - Parried;
    if (Out.Guarded > 0)
        Out.GuardedDamage = Log.Guarded.Last().Damage;
    return Press(Arena, EKeys::LeftControl, false) && Arena.Tick(1);
}

const TCHAR* StanceName(EStance Stance)
{
    return Stance == EStance::Parry ? TEXT("fresh guard") : Stance == EStance::Guard ? TEXT("held guard") : TEXT("guard from behind");
}
} // namespace SoraCombatAutomation

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraArchetypeCatalogTest,
    "SoraArena.Combat.ArchetypeCatalog",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraArchetypeCatalogTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraCombatAutomation;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FSoraEnemyCatalog& Enemies = FSoraEnemyCatalog::Get();
    if (!TestTrue(TEXT("Content/Data/enemies.json loads"), Enemies.Load()))
        return false;
    static const TCHAR* const Roster[] = {TEXT("enforcer_rifle"), TEXT("blade_retainer"), TEXT("shield_enforcer"), TEXT("grenadier"),
        TEXT("marksman"), TEXT("drone"), TEXT("bound_conscript"), TEXT("auditor"), TEXT("loom_automaton"), TEXT("seizure_walker")};
    TestEqual(TEXT("The story bible's ten archetypes, in its order"), Enemies.Archetypes().Num(), 10);
    FArena Arena(*this, TEXT("ArchetypeCatalog"));
    if (!Arena.Start())
        return false;
    for (int32 Index = 0; Index < static_cast<int32>(UE_ARRAY_COUNT(Roster)); ++Index)
    {
        const FSoraEnemyArchetype* Kind = Enemies.Find(Roster[Index]);
        if (!TestNotNull(*FString::Printf(TEXT("%s is in enemies.json"), Roster[Index]), Kind) ||
            !TestEqual(TEXT("Roster order"), Enemies.Archetypes()[Index].Id, FName(Roster[Index])))
            continue;
        const FVector At(-1800.f + Index * 400.f, 1500.f, 0.f);
        FSoraPatrolRoute Post;
        Post.Points.Add(FVector(At.X, At.Y, 90.f));
        ASoraEnemy* Enemy = Arena.SpawnKind(Roster[Index], Index, At, 90.f, &Post);
        if (!TestNotNull(*FString::Printf(TEXT("%s spawns by archetype"), Roster[Index]), Enemy))
            continue;
        const FString What(Roster[Index]);
        TestEqual(What + TEXT(" archetype"), Enemy->ArchetypeId(), Kind->Id);
        TestEqual(What + TEXT(" health"), Enemy->Health, static_cast<float>(Kind->Health));
        TestEqual(What + TEXT(" speed"), Enemy->GetCharacterMovement()->MaxWalkSpeed, static_cast<float>(Kind->SpeedCmPerSecond));
        TestEqual(What + TEXT(" sight"), Enemy->Perception().SightRangeCm, Kind->Perception.SightRangeCm);
        TestEqual(What + TEXT(" hearing"), Enemy->Perception().HearingCm, Kind->Perception.HearingCm);
        TestEqual(What + TEXT(" is nonlethal only when debt-bound"), Enemy->IsNonlethal(), !Kind->bLethal);
        TestEqual(What + TEXT(" flies only as a drone"), Enemy->IsFlying(), Kind->Behavior == ESoraEnemyBehavior::Drone);
        TestEqual(What + TEXT(" flies in the air"), Enemy->GetCharacterMovement()->MovementMode == MOVE_Flying,
            Kind->Behavior == ESoraEnemyBehavior::Drone);
        TestTrue(What + TEXT(" scale"), FMath::IsNearlyEqual(Enemy->GetActorScale3D().Z, Kind->ScalePermille / 1000.f));
        TestTrue(What + TEXT(" has bilingual names"), !Kind->NameJapanese.IsEmpty() && !Kind->NameEnglish.IsEmpty() &&
            !Kind->WeaponJapanese.IsEmpty() && !Kind->WeaponEnglish.IsEmpty());
        for (const FSoraEnemyAttack& Attack : Kind->Attacks)
            TestTrue(What + TEXT(" telegraphs every attack for at least 300 ms"), Attack.WindupMs >= 300 &&
                !Attack.NameJapanese.IsEmpty() && !Attack.NameEnglish.IsEmpty() && !Attack.Cue.IsNone());
    }
    TestTrue(TEXT("Only the debt-bound are nonlethal"), Enemies.Find(TEXT("bound_conscript"))->bDebtBound &&
        !Enemies.Find(TEXT("bound_conscript"))->bLethal && Enemies.Find(TEXT("enforcer_rifle"))->bLethal);

    // Variants and a beat's tuning.
    FSoraEnemyTuning Shielded;
    Shielded.Variant = TEXT("shielded");
    const ASoraEnemy* Barrier = Arena.SpawnKind(TEXT("enforcer_rifle"), 20, FVector(0.f, 2200.f, 0.f), 90.f, nullptr, &Shielded);
    if (TestNotNull(TEXT("A shielded enforcer spawns"), Barrier))
        TestEqual(TEXT("Its barrier holds 60 points"), Barrier->BarrierHealth(), 60);
    FSoraEnemyTuning Hound;
    Hound.Variant = TEXT("audit_hound");
    const ASoraEnemy* Audit = Arena.SpawnKind(TEXT("drone"), 21, FVector(400.f, 2200.f, 0.f), 90.f, nullptr, &Hound);
    if (TestNotNull(TEXT("An audit hound spawns"), Audit))
        TestTrue(TEXT("The audit hound has its own health and short sight"),
            Audit->Health == 60.f && Audit->Perception().SightRangeCm == 900 && Audit->Perception().DarkSightRangeCm == 900);
    FSoraEnemyTuning Beat;
    Beat.Health = 250; Beat.SightCm = 1500; Beat.DarkSightCm = 700; Beat.ViewDegrees = 90; Beat.HearingCm = 0; Beat.bInvulnerable = true;
    ASoraEnemy* Tuned = Arena.SpawnKind(TEXT("enforcer_rifle"), 22, FVector(800.f, 2200.f, 0.f), 90.f, nullptr, &Beat);
    if (TestNotNull(TEXT("A tuned enforcer spawns"), Tuned))
    {
        TestTrue(TEXT("A beat's tuning overrides health and perception"),
            Tuned->Health == 250.f && Tuned->Perception().SightRangeCm == 1500 && Tuned->Perception().DarkSightRangeCm == 700 &&
            Tuned->Perception().ViewConeMilli == 707 && Tuned->Perception().HearingCm == 0);
        UGameplayStatics::ApplyDamage(Tuned, 100.f, nullptr, Arena.Hero(), UDamageType::StaticClass());
        TestEqual(TEXT("A scripted invulnerable opponent takes no damage"), Tuned->Health, 250.f);
    }
    // An unknown archetype or variant spawns nothing.
    AddExpectedError(TEXT("No opponent archetype"), EAutomationExpectedErrorFlags::Contains, 2);
    TestNull(TEXT("An unknown archetype spawns nothing"), Arena.SpawnKind(TEXT("oni"), 23, FVector(0.f, 2600.f, 0.f), 0.f));
    FSoraEnemyTuning Wrong;
    Wrong.Variant = TEXT("shielded");
    TestNull(TEXT("A variant of another archetype spawns nothing"), Arena.SpawnKind(TEXT("drone"), 24, FVector(0.f, 2600.f, 0.f), 0.f, nullptr, &Wrong));
    // The schema-3 director's combat wave.
    TestEqual(TEXT("Wave slot 0 is a blade retainer"), ASoraEnemy::WaveArchetype(0), FName(TEXT("blade_retainer")));
    TestEqual(TEXT("Wave slot 1 is a rifle enforcer"), ASoraEnemy::WaveArchetype(1), FName(TEXT("enforcer_rifle")));
    TestEqual(TEXT("Wave slot 12 is a blade retainer"), ASoraEnemy::WaveArchetype(12), FName(TEXT("blade_retainer")));
    return Arena.Tick(2);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraGuardAndParryEveryMeleeTest,
    "SoraArena.Combat.GuardAndParryEveryMelee",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraGuardAndParryEveryMeleeTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraCombatAutomation;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FArena Arena(*this, TEXT("GuardAndParry"));
    if (!Arena.Start())
        return false;
    FLog Log;
    if (!TestTrue(TEXT("The event log attaches"), Log.Attach(Arena.Get())) || !Arm(Arena, 0))
        return false;
    struct FAttacker
    {
        const TCHAR* Archetype;
        float Distance;
    };
    const FAttacker Attackers[] = {{TEXT("blade_retainer"), 160.f}, {TEXT("shield_enforcer"), 190.f},
        {TEXT("bound_conscript"), 180.f}, {TEXT("loom_automaton"), 235.f}};
    int32 Slot = 0;
    for (const FAttacker& Spec : Attackers)
    {
        for (const EStance Stance : {EStance::Parry, EStance::Guard, EStance::Behind})
        {
            // Each case starts with a rested guard: stamina spent in one case
            // must not decide the next.
            Clear(Arena);
            if (!Until(Arena, 600, [&]() { return Arena.Hero()->GetEquipment()->GuardReserve() >= 100.f; }))
                return false;
            Arena.PlaceHero(FVector::ZeroVector, Stance == EStance::Behind ? 180.f : 0.f);
            Arena.Hero()->GetCharacterMovement()->StopMovementImmediately();
            ASoraEnemy* Attacker = Arena.SpawnKind(Spec.Archetype, Slot++, FVector(Spec.Distance, 0.f, 0.f), 180.f);
            const FString What = FString::Printf(TEXT("%s against a %s"), Spec.Archetype, StanceName(Stance));
            FBlow Blow;
            if (!TestNotNull(*What, Attacker) || !MeetBlow(Arena, Log, *Attacker, Stance, Blow) ||
                !TestTrue(What + TEXT(": the blow resolves"), Blow.bResolved && Blow.bRaised))
                continue;
            const FSoraEnemyAttack& A = Blow.Attack;
            AddInfo(FString::Printf(TEXT("%s: %s, %.0f damage, parried %d, guarded %d"), *What, *A.Id.ToString(),
                Blow.HeroDamage, Blow.Parried, Blow.Guarded));
            if (Stance == EStance::Behind)
            {
                TestEqual(What + TEXT(": nothing is defended from behind"), Blow.Guarded + Blow.Parried, 0);
                TestEqual(What + TEXT(": the whole blow lands"), Blow.HeroDamage, static_cast<float>(A.Damage));
            }
            else if (Stance == EStance::Parry && A.bParryable)
            {
                TestEqual(What + TEXT(": parried"), Blow.Parried, 1);
                TestEqual(What + TEXT(": a parry stops the whole blow"), Blow.HeroDamage, 0.f);
                TestTrue(What + TEXT(": the parried attacker staggers"), Blow.bStaggered);
                TestTrue(What + TEXT(": the parry holds the world still"), Blow.bHitStop);
            }
            else
            {
                TestEqual(What + TEXT(": guarded"), Blow.Guarded, 1);
                TestEqual(What + TEXT(": no parry"), Blow.Parried, 0);
                TestEqual(What + TEXT(": the guard lets the chip through"), Blow.HeroDamage, static_cast<float>(A.GuardChip));
                TestEqual(What + TEXT(": the event names the chip"), Blow.GuardedDamage, static_cast<float>(A.GuardChip));
                TestTrue(What + TEXT(": the guard spends stamina"), Blow.Stamina >= A.GuardStamina - .5f);
                TestTrue(What + TEXT(": a guarded blow holds the world still"), Blow.bHitStop);
            }
        }
    }

    // The collector (High Collector Val Amort, bosses.json): its debt beam
    // goes through any guard; its cleave is a blade like any other.
    Clear(Arena);
    Arena.PlaceHero(FVector::ZeroVector, 0.f);
    ASoraBoss* Boss = ASoraBoss::SpawnBoss(*Arena.Get(), TEXT("boss_val_amort"), 17, FVector(250.f, 0.f, 120.f), FRotator(0.f, 180.f, 0.f));
    if (!TestNotNull(TEXT("The collector spawns"), Boss))
        return false;
    ASoraPlayerCharacter* Hero = Arena.Hero();
    const auto Telegraphing = [Boss](bool bBeam)
    {
        const FSoraBossAttack* Attack = Boss->BossAttack();
        return Boss->IsBossTelegraphing() && Attack && (Attack->Kind == ESoraBossAttackKind::Beam) == bBeam;
    };
    if (!Until(Arena, 600, [&]() { return Telegraphing(true); }) || !TestTrue(TEXT("The collector opens with its beam"), Telegraphing(true)))
        return false;
    const int32 BeamsBefore = Log.CountIf(Log.Fired, [Boss](const FLog::FStamped<FSoraWeaponFiredEvent>& E) { return E.Event.Shooter == Boss; });
    float Health = Hero->Health;
    if (!Press(Arena, EKeys::LeftControl, true) || !Until(Arena, 300, [&]() { return !Telegraphing(true); }) || !Arena.Tick(1))
        return false;
    TestEqual(TEXT("The debt beam fires"), Log.CountIf(Log.Fired, [Boss](const FLog::FStamped<FSoraWeaponFiredEvent>& E)
        { return E.Event.Shooter == Boss && E.Event.Kind == ESoraShotKind::Beam; }) - BeamsBefore, 1);
    TestEqual(TEXT("No guard stops the debt beam"), Health - Hero->Health, 22.f);
    TestEqual(TEXT("The beam is not guarded"), Log.GuardedBy(Boss) + Log.ParriedBy(Boss), 0);
    if (!Press(Arena, EKeys::LeftControl, false) || !Until(Arena, 600, [&]() { return Telegraphing(false); }) ||
        !TestTrue(TEXT("The collector winds up its cleave"), Telegraphing(false)))
        return false;
    // A fresh guard meets the cleave: parried, and the collector staggers.
    if (!Until(Arena, 300, [&]() { return Boss->BossWarningSeconds() <= .2f; }) || !Press(Arena, EKeys::LeftControl, true))
        return false;
    Health = Hero->Health;
    const int32 Resolved = Log.ResolvedBy(Boss);
    if (!Until(Arena, 120, [&]() { return Log.ResolvedBy(Boss) > Resolved; }))
        return false;
    TestEqual(TEXT("The collector's cleave is parried"), Log.ParriedBy(Boss), 1);
    TestEqual(TEXT("A parried cleave does no damage"), Health - Hero->Health, 0.f);
    TestTrue(TEXT("The parried collector staggers"), Boss->IsStaggered());
    TestTrue(TEXT("The parry holds the world still"), Dilation(Arena) < .5f);
    if (!Press(Arena, EKeys::LeftControl, false))
        return false;
    // While staggered it starts no attack, and a cut on it deals a quarter more.
    const float BossHealth = Boss->Health;
    FHitResult Cut;
    Cut.ImpactPoint = Boss->GetActorLocation();
    SoraDamage::Strike(Boss, 40.f, FSoraHit::Melee(Hero->GetActorLocation(), 0), FVector(1.f, 0.f, 0.f), Cut, Hero->GetController(), Hero);
    TestEqual(TEXT("A staggered collector takes a quarter more"), BossHealth - Boss->Health, 50.f);
    bool bAttackedInStagger = false;
    if (!Until(Arena, 240, [&]() { bAttackedInStagger |= Boss->IsBossTelegraphing() && Boss->IsStaggered(); return !Boss->IsStaggered(); }))
        return false;
    TestFalse(TEXT("A staggered collector starts no attack"), bAttackedInStagger);
    // The next cleave, met with a held guard: guarded, with its chip.
    if (!Until(Arena, 900, [&]() { return Telegraphing(false); }) || !TestTrue(TEXT("The collector cleaves again"), Telegraphing(false)) ||
        !Press(Arena, EKeys::LeftControl, true))
        return false;
    Health = Hero->Health;
    const int32 Cleaves = Log.ResolvedBy(Boss);
    if (!Until(Arena, 150, [&]() { return Log.ResolvedBy(Boss) > Cleaves; }))
        return false;
    TestEqual(TEXT("A held guard takes the collector's cleave"), Log.GuardedBy(Boss), 1);
    TestEqual(TEXT("The guarded cleave's chip"), Health - Hero->Health, 8.f);
    return Press(Arena, EKeys::LeftControl, false) && Arena.Tick(2);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraRangedChipTest,
    "SoraArena.Combat.RangedChip",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraRangedChipTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraCombatAutomation;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FArena Arena(*this, TEXT("RangedChip"));
    if (!Arena.Start())
        return false;
    FLog Log;
    if (!TestTrue(TEXT("The event log attaches"), Log.Attach(Arena.Get())) || !Arm(Arena, 0))
        return false;
    ASoraPlayerCharacter* Hero = Arena.Hero();
    Arena.PlaceHero(FVector::ZeroVector, 0.f);
    ASoraEnemy* Rifle = Arena.SpawnKind(TEXT("enforcer_rifle"), 2, FVector(800.f, 0.f, 0.f), 180.f);
    if (!TestNotNull(TEXT("A rifle enforcer spawns"), Rifle))
        return false;
    // Held where it stands, so every burst has a clear line.
    Rifle->GetCharacterMovement()->DisableMovement();
    const int32 Damage = Rifle->AttackDamage(0);
    // One burst, met as Stance says; returns the rounds that hurt the hero.
    const auto Burst = [&](EStance Stance, bool bGuard, TArray<float>& Hits, float& WindupLead) -> bool
    {
        Arena.PlaceHero(FVector::ZeroVector, Stance == EStance::Behind ? 180.f : 0.f);
        const int32 Cues = Log.CueCount(Rifle, ESoraEnemyCue::AttackWindup);
        const int32 Damaged = Log.Damaged.Num();
        bool bRaised = false, bFired = false;
        float WindupAt = 0.f;
        for (int32 Index = 0; Index < 900; ++Index)
        {
            if (!WindupAt && Log.CueCount(Rifle, ESoraEnemyCue::AttackWindup) > Cues)
                WindupAt = Log.Cues.Last().Time;
            if (bGuard && !bRaised && Rifle->IsWindingUp() && (Stance != EStance::Parry || Rifle->WindupProgress() >= .75f))
            {
                if (!Press(Arena, EKeys::LeftControl, true))
                    return false;
                bRaised = true;
            }
            bFired |= Rifle->IsCommitted() && !Rifle->IsWindingUp();
            if (bFired && !Rifle->IsCommitted())
                break;
            if (!Arena.Tick(1))
                return false;
        }
        Hits.Reset();
        float FirstHit = 0.f;
        for (int32 Index = Damaged; Index < Log.Damaged.Num(); ++Index)
            if (Log.Damaged[Index].Event.Victim == Hero && Log.Damaged[Index].Event.Causer == Rifle)
            {
                Hits.Add(Log.Damaged[Index].Event.Amount);
                FirstHit = FirstHit ? FirstHit : Log.Damaged[Index].Time;
            }
        WindupLead = FirstHit && WindupAt ? FirstHit - WindupAt : 0.f;
        return (!bRaised || Press(Arena, EKeys::LeftControl, false)) && bFired && Arena.Tick(1);
    };
    TArray<float> Hits;
    float Lead = 0.f;
    // A guard raised just before the first round: bullets are never parried.
    const float Stamina = Hero->GetEquipment()->GuardReserve();
    if (!TestTrue(TEXT("A burst meets a fresh frontal guard"), Burst(EStance::Parry, true, Hits, Lead)))
        return false;
    TestTrue(TEXT("Some rounds hit"), Hits.Num() >= 1);
    for (const float Hit : Hits)
        TestEqual(TEXT("A frontal guard halves each round, rounded up"), Hit, static_cast<float>(Rules::Share(Damage, Rules::RangedChipPermille)));
    TestEqual(TEXT("Bullets are never parried"), Log.ParriedBy(Rifle), 0);
    TestEqual(TEXT("Each guarded round is announced"), Log.GuardedBy(Rifle), Hits.Num());
    TestTrue(TEXT("Guarded rounds spend guard stamina"), Stamina - Hero->GetEquipment()->GuardReserve() >= Rules::RangedGuardStamina * Hits.Num() - 1.f);
    TestTrue(TEXT("The raised stock precedes the first round by its windup"), Lead >= .6f - Frame);
    // The hero's back to the rifle: the guard does nothing.
    if (!TestTrue(TEXT("A burst meets a guard from behind"), Burst(EStance::Behind, true, Hits, Lead)))
        return false;
    TestTrue(TEXT("Rounds hit from behind"), Hits.Num() >= 1);
    for (const float Hit : Hits)
        TestEqual(TEXT("A guard from behind takes nothing off"), Hit, static_cast<float>(Damage));
    // No guard at all.
    if (!TestTrue(TEXT("A burst meets no guard"), Burst(EStance::Guard, false, Hits, Lead)))
        return false;
    for (const float Hit : Hits)
        TestEqual(TEXT("An unguarded round deals its damage"), Hit, static_cast<float>(Damage));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraStaggerAndHitStopTest,
    "SoraArena.Combat.StaggerAndHitStop",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraStaggerAndHitStopTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraCombatAutomation;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FArena Arena(*this, TEXT("StaggerAndHitStop"));
    if (!Arena.Start())
        return false;
    FLog Log;
    if (!TestTrue(TEXT("The event log attaches"), Log.Attach(Arena.Get())) || !Arm(Arena, 0))
        return false;
    Arena.PlaceHero(FVector::ZeroVector, 0.f);
    // A cut that lands during a retainer's windup staggers it: the windup drops
    // and the world holds still for the contact.
    ASoraEnemy* Retainer = Arena.SpawnKind(TEXT("blade_retainer"), 0, FVector(150.f, 0.f, 0.f), 180.f);
    if (!TestNotNull(TEXT("A blade retainer spawns"), Retainer) ||
        !Until(Arena, 600, [Retainer]() { return Retainer->IsWindingUp(); }) || !TestTrue(TEXT("The retainer winds up"), Retainer->IsWindingUp()))
        return false;
    const int32 Resolved = Log.ResolvedBy(Retainer);
    const float Health = Retainer->Health;
    if (!TestTrue(TEXT("The katana commits"), Swing(Arena)) || !Until(Arena, 60, [&]() { return Retainer->Health < Health; }))
        return false;
    TestEqual(TEXT("The katana lands before the retainer's cut"), Health - Retainer->Health, 52.f);
    TestTrue(TEXT("The cut staggers the retainer"), Retainer->IsStaggered());
    TestFalse(TEXT("Its windup drops"), Retainer->IsWindingUp());
    TestTrue(TEXT("The contact holds the world still"), FMath::IsNearlyEqual(Dilation(Arena), Rules::HitStopDilationPermille / 1000.f));
    int32 HeldFrames = 0;
    if (!Until(Arena, 30, [&]() { ++HeldFrames; return Dilation(Arena) >= 1.f; }))
        return false;
    TestTrue(TEXT("The hit-stop ends within its real milliseconds"), Dilation(Arena) == 1.f && HeldFrames <= 7);
    if (!Until(Arena, 120, [Retainer]() { return Retainer->IsWindingUp(); }))
        return false;
    TestEqual(TEXT("The interrupted cut never lands"), Log.ResolvedBy(Retainer), Resolved);
    // The next cut within the immunity window wounds but does not stagger again.
    const float Second = Retainer->Health;
    if (!TestTrue(TEXT("The katana recovers and commits again"), Swing(Arena)) ||
        !Until(Arena, 60, [&]() { return Retainer->Health < Second; }))
        return false;
    TestTrue(TEXT("A second cut lands"), Retainer->Health < Second);
    TestFalse(TEXT("No chain of cuts holds an opponent still"), Retainer->IsStaggered());

    // A parry's stagger is a punishing window: hits in it deal a quarter more.
    Clear(Arena);
    if (!Arena.Tick(90))
        return false;
    Arena.PlaceHero(FVector::ZeroVector, 0.f);
    ASoraEnemy* Parried = Arena.SpawnKind(TEXT("blade_retainer"), 6, FVector(150.f, 0.f, 0.f), 180.f);
    FBlow Blow;
    if (!TestNotNull(TEXT("A second retainer spawns"), Parried) || !MeetBlow(Arena, Log, *Parried, EStance::Parry, Blow) ||
        !TestEqual(TEXT("Its cut is parried"), Blow.Parried, 1))
        return false;
    const float Before = Parried->Health;
    if (!TestTrue(TEXT("The punish commits"), Swing(Arena)) || !Until(Arena, 60, [&]() { return Parried->Health < Before; }))
        return false;
    TestTrue(TEXT("The punish lands inside the parry's stagger"), Parried->IsStaggered());
    TestEqual(TEXT("A staggered opponent takes a quarter more"), Before - Parried->Health, 65.f);

    // Poise: a katana does not stagger a loom automaton; a kanabō does.
    for (const int32 WeaponId : {0, 6})
    {
        Clear(Arena);
        if (!Arm(Arena, WeaponId))
            return false;
        Arena.PlaceHero(FVector::ZeroVector, 0.f);
        ASoraEnemy* Automaton = Arena.SpawnKind(TEXT("loom_automaton"), 10 + WeaponId, FVector(150.f, 0.f, 0.f), 180.f);
        if (!TestNotNull(TEXT("A loom automaton spawns"), Automaton))
            return false;
        Automaton->SetActorTickEnabled(false);
        const float Full = Automaton->Health;
        if (!Arena.Tick(2) || !TestTrue(TEXT("The strike commits"), Swing(Arena)) ||
            !Until(Arena, 60, [&]() { return Automaton->Health < Full; }))
            return false;
        const float Dealt = Full - Automaton->Health;
        TestEqual(*FString::Printf(TEXT("Weapon %d deals its catalog damage to the automaton's front"), WeaponId), Dealt,
            FSoraCatalog::Get().Weapon(WeaponId).Damage);
        TestEqual(*FString::Printf(TEXT("Weapon %d staggers the automaton only past its poise"), WeaponId), Automaton->IsStaggered(),
            WeaponId == 6);
    }
    return Arena.Tick(2);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraExplosivesTest,
    "SoraArena.Combat.ExplosiveSelfDamageAndArming",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraExplosivesTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraCombatAutomation;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FArena Arena(*this, TEXT("Explosives"));
    if (!Arena.Start())
        return false;
    FLog Log;
    if (!TestTrue(TEXT("The event log attaches"), Log.Attach(Arena.Get())))
        return false;
    ASoraPlayerCharacter* Hero = Arena.Hero();
    // Fires Weapon at a wall whose face stands Face centimetres ahead; true
    // when the shell burst, with the damage the hero took from it.
    const auto Shoot = [&](int32 WeaponId, float Face, bool& bBurst, float& SelfDamage) -> bool
    {
        Clear(Arena);
        if (!Arm(Arena, WeaponId))
            return false;
        Arena.PlaceHero(FVector::ZeroVector, 0.f);
        AActor* Wall = Arena.Wall(FVector(Face + 30.f, 0.f, 200.f), FVector(60.f, 800.f, 400.f));
        const int32 Blasts = Log.BlastsBy(Hero);
        const float Health = Hero->Health;
        const bool bOk = Arena.Tick(2) && Tap(Arena, EKeys::LeftMouseButton) && Arena.Tick(90);
        bBurst = Log.BlastsBy(Hero) > Blasts;
        SelfDamage = Health - Hero->Health;
        Wall->Destroy();
        return bOk && Arena.Tick(2);
    };
    bool bBurst = false;
    float SelfDamage = 0.f;
    const float Grenade = FSoraCatalog::Get().Weapon(7).Damage;
    // The grenade launcher arms at 200 cm (kernel weapon 7): a shell stopped
    // short is a dud; an armed one bursts on its own owner at full damage.
    if (!Shoot(7, 330.f, bBurst, SelfDamage))
        return false;
    TestTrue(TEXT("An armed shell bursts"), bBurst);
    TestEqual(TEXT("Its blast reaches its own owner at full damage"), SelfDamage, Grenade);
    if (!Shoot(7, 200.f, bBurst, SelfDamage))
        return false;
    TestFalse(TEXT("A shell stopped short of its arming distance is a dud"), bBurst);
    TestEqual(TEXT("A dud hurts nobody"), SelfDamage, 0.f);
    // The micro-mortar arms at 450 cm (kernel weapon 15).
    if (!Shoot(15, 400.f, bBurst, SelfDamage))
        return false;
    TestFalse(TEXT("A mortar shell inside 450 cm is a dud"), bBurst);
    if (!Shoot(15, 700.f, bBurst, SelfDamage))
        return false;
    TestTrue(TEXT("A mortar shell past 450 cm bursts"), bBurst);
    TestEqual(TEXT("A burst beyond its radius spares its owner"), SelfDamage, 0.f);

    // A grenadier's shell: its landing ring shows for the whole flight, and
    // its blast spares the grenadier's allies.
    Clear(Arena);
    if (!Arm(Arena, 0))
        return false;
    Arena.PlaceHero(FVector::ZeroVector, 0.f);
    ASoraEnemy* Ally = Arena.SpawnKind(TEXT("enforcer_rifle"), 5, FVector(0.f, 120.f, 0.f), 0.f);
    ASoraEnemy* Grenadier = Arena.SpawnKind(TEXT("grenadier"), 6, FVector(1300.f, 0.f, 0.f), 180.f);
    if (!TestNotNull(TEXT("An ally spawns"), Ally) || !TestNotNull(TEXT("A grenadier spawns"), Grenadier))
        return false;
    Ally->SetActorTickEnabled(false);
    Grenadier->GetCharacterMovement()->DisableMovement();
    const float AllyHealth = Ally->Health;
    float Health = Hero->Health;
    if (!Until(Arena, 900, [&]() { return Log.BlastsBy(Grenadier) > 0; }) || !TestEqual(TEXT("The grenadier's shell bursts"), Log.BlastsBy(Grenadier), 1))
        return false;
    const auto* Launch = Log.Fired.FindByPredicate([Grenadier](const FLog::FStamped<FSoraWeaponFiredEvent>& E)
        { return E.Event.Shooter == Grenadier && E.Event.Kind == ESoraShotKind::Shell; });
    const auto* Windup = Log.Cues.FindByPredicate([Grenadier](const FLog::FStamped<FSoraEnemyCueEvent>& E)
        { return E.Event.Enemy == Grenadier && E.Event.Cue == ESoraEnemyCue::AttackWindup; });
    const auto* Burst = Log.Blasts.FindByPredicate([Grenadier](const FLog::FStamped<FSoraDetonatedEvent>& E) { return E.Event.Instigator == Grenadier; });
    if (!TestTrue(TEXT("The launch, its windup and its burst are announced"), Launch && Windup && Burst))
        return false;
    AddInfo(FString::Printf(TEXT("Grenadier windup %.3f, launch %.3f, burst %.3f"), Windup->Time, Launch->Time, Burst->Time));
    TestTrue(TEXT("The landing ring shows for about its 1.4 s flight before the burst"), Burst->Time - Launch->Time >= 1.2f);
    TestTrue(TEXT("The windup comes before the launch"), Launch->Time - Windup->Time >= .5f - Frame);
    TestEqual(TEXT("The shell hurts the hero"), Health - Hero->Health, 35.f);
    TestEqual(TEXT("It spares the grenadier's ally"), Ally->Health, AllyHealth);
    return Arena.Tick(2);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraClassMeleeCommittedTest,
    "SoraArena.Combat.ClassMeleeCommitted",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraClassMeleeCommittedTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraCombatAutomation;
    using namespace SoraHistoricalArms;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FArena Arena(*this, TEXT("ClassMelee"));
    if (!Arena.Start())
        return false;
    FLog Log;
    if (!TestTrue(TEXT("The event log attaches"), Log.Attach(Arena.Get())))
        return false;
    ASoraPlayerCharacter* Hero = Arena.Hero();
    USoraEquipmentComponent* Kit = Hero->GetEquipment();
    int32 Slot = 30;
    for (const int32 WeaponId : {2, 4, 6, 8, 10, 12})
    {
        const FString What = FString::Printf(TEXT("Weapon %d (%s)"), WeaponId, *FSoraCatalog::Get().Weapon(WeaponId).NameEnglish);
        const FProfile Handling = Profile(FormFor(WeaponId));
        const float Distance = FMath::Clamp((Handling.MinimumDistanceCm + Handling.MaximumDistanceCm) * .5f, 120.f,
            Handling.MaximumDistanceCm - 15.f);
        Clear(Arena);
        if (!Arm(Arena, WeaponId))
            return false;
        Arena.PlaceHero(FVector::ZeroVector, 0.f);
        ASoraEnemy* Target = Arena.SpawnKind(TEXT("blade_retainer"), Slot++, FVector(Distance, 0.f, 0.f), 180.f);
        if (!TestNotNull(*What, Target))
            continue;
        // Held still, so only the strike changes it.
        Target->SetActorTickEnabled(false);
        if (!Arena.Tick(2))
            return false;
        const float Health = Target->Health;
        const int32 Committed = Log.Committed.Num();
        if (!Tap(Arena, EKeys::LeftMouseButton))
            return false;
        TestTrue(What + TEXT(" commits to its strike"), Kit->IsCommittedStrike());
        const auto* Commit = Log.Committed.Num() > Committed ? &Log.Committed.Last() : nullptr;
        if (!TestNotNull(What + TEXT(" announces its commitment"), Commit))
            continue;
        TestEqual(What + TEXT(" commits with the held weapon"), Commit->Event.WeaponId, WeaponId);
        TestTrue(What + TEXT(" announces its windup"), FMath::IsNearlyEqual(Commit->Event.WindupSeconds, Handling.WindupSeconds, .001f));
        TestEqual(What + TEXT(" does no damage when it commits"), Target->Health, Health);
        float LandedAt = 0.f;
        if (!Until(Arena, 90, [&]() { LandedAt = Log.Now(); return Target->Health < Health; }))
            return false;
        TestTrue(What + TEXT(" lands no sooner than its windup"), LandedAt - Commit->Time >= Handling.WindupSeconds - Frame);
        TestEqual(What + TEXT(" deals its catalog damage"), Health - Target->Health, FSoraCatalog::Get().Weapon(WeaponId).Damage);
        // During recovery another press starts nothing.
        if (!Tap(Arena, EKeys::LeftMouseButton))
            return false;
        TestFalse(What + TEXT(" cannot strike again in its recovery"), Kit->IsCommittedStrike());
    }
    return Arena.Tick(2);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraConscriptSubdueTest,
    "SoraArena.Combat.ConscriptSubdue",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraConscriptSubdueTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraCombatAutomation;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FArena Arena(*this, TEXT("ConscriptSubdue"));
    if (!Arena.Start())
        return false;
    FLog Log;
    if (!TestTrue(TEXT("The event log attaches"), Log.Attach(Arena.Get())) || !Arm(Arena, 0))
        return false;
    ASoraPlayerCharacter* Hero = Arena.Hero();
    const int32 Kills = Arena.Mode()->Campaign()->Kills;
    Arena.PlaceHero(FVector::ZeroVector, 0.f);
    // A conscript at its post with its back to the hero.
    FSoraPatrolRoute Post;
    Post.Points.Add(FVector(150.f, 0.f, 90.f));
    ASoraEnemy* Conscript = Arena.SpawnKind(TEXT("bound_conscript"), 0, FVector(150.f, 0.f, 0.f), 0.f, &Post);
    if (!TestNotNull(TEXT("A debt-bound conscript spawns"), Conscript) || !Arena.Tick(2))
        return false;
    // 峰打ち: cuts that would kill knock it down instead.
    for (int32 Cut = 0; Cut < 2 && Conscript->IsAlive(); ++Cut)
    {
        const float Health = Conscript->Health;
        if (!TestTrue(TEXT("The katana commits"), Swing(Arena)) || !Until(Arena, 60, [&]() { return Conscript->Health < Health; }))
            return false;
    }
    TestTrue(TEXT("The conscript is knocked down"), Conscript->IsSubdued() && !Conscript->IsAlive());
    TestEqual(TEXT("Its knockdown is announced"), Log.CueCount(Conscript, ESoraEnemyCue::Subdued), 1);
    TestEqual(TEXT("Nobody died"), Log.CountIf(Log.Died, [Conscript](const FSoraDiedEvent& E) { return E.Victim == Conscript; }), 0);
    if (!Arena.Tick(120))
        return false;
    TestTrue(TEXT("It stays where it fell"), IsValid(Conscript) && !Conscript->IsActorBeingDestroyed() && Conscript->IsSubdued());
    TestEqual(TEXT("A knocked-down conscript never counts as a kill"), Arena.Mode()->Campaign()->Kills, Kills);
    // The collar is cut: freed for good.
    TestTrue(TEXT("Its collar can be cut while it is down"), Conscript->CanCutSeal());
    TestTrue(TEXT("Cutting the collar frees it"), Conscript->CutSeal(Hero));
    TestTrue(TEXT("A freed conscript stands, at full health, no longer an opponent"),
        Conscript->IsFreed() && Conscript->IsAlive() && !Conscript->IsEnemy() && Conscript->Health == Conscript->MaxHealth);
    TestEqual(TEXT("Its freedom is announced"), Log.CueCount(Conscript, ESoraEnemyCue::Freed), 1);
    TestFalse(TEXT("A collar is cut only once"), Conscript->CutSeal(Hero));
    const float Freed = Conscript->Health;
    if (!TestTrue(TEXT("The katana commits on the freed conscript"), Swing(Arena)) || !Arena.Tick(30))
        return false;
    TestEqual(TEXT("A freed conscript cannot be hurt"), Conscript->Health, Freed);

    // Left down past its window, the collar drags a conscript back up, hurt and alert.
    ASoraEnemy* Risen = Arena.SpawnKind(TEXT("bound_conscript"), 1, FVector(150.f, 400.f, 0.f), 0.f, &Post);
    if (!TestNotNull(TEXT("A second conscript spawns"), Risen) || !Arena.Tick(2))
        return false;
    UGameplayStatics::ApplyDamage(Risen, 1000.f, Hero->GetController(), Hero, UDamageType::StaticClass());
    TestTrue(TEXT("Even scripted lethal damage only knocks it down"), Risen->IsSubdued());
    const FSoraEnemyArchetype& Kind = *Risen->Archetype();
    if (!Arena.Tick(FMath::CeilToInt32(Kind.SubdueWindowMs / 1000.f / Frame) - 30))
        return false;
    TestTrue(TEXT("It stays down inside its window"), Risen->IsSubdued());
    if (!Until(Arena, 90, [Risen]() { return !Risen->IsSubdued(); }))
        return false;
    TestTrue(TEXT("It rises when its window closes"), Risen->IsAlive() && !Risen->IsSubdued());
    TestEqual(TEXT("It rises with half its health"), Risen->Health, Kind.Health * Kind.RiseHealthPermille / 1000.f);
    TestEqual(TEXT("Its rising is announced"), Log.CueCount(Risen, ESoraEnemyCue::Risen), 1);
    TestFalse(TEXT("A risen conscript's collar cannot be cut"), Risen->CanCutSeal());
    const ASoraEnemyController* Brain = FArena::Brain(Risen);
    TestTrue(TEXT("It rises knowing where the hero is"), Brain && Brain->State() != SoraStealthRules::EState::Unaware);

    // A blast knocks down, never kills.
    Clear(Arena);
    if (!Arm(Arena, 7))
        return false;
    Arena.PlaceHero(FVector::ZeroVector, 0.f);
    FSoraPatrolRoute Far;
    Far.Points.Add(FVector(600.f, 0.f, 90.f));
    ASoraEnemy* Blasted = Arena.SpawnKind(TEXT("bound_conscript"), 2, FVector(600.f, 0.f, 0.f), 0.f, &Far);
    if (!TestNotNull(TEXT("A third conscript spawns"), Blasted) || !Arena.Tick(2) || !Tap(Arena, EKeys::LeftMouseButton) ||
        !Until(Arena, 90, [Blasted]() { return Blasted->IsSubdued(); }))
        return false;
    TestTrue(TEXT("A shell knocks a conscript down"), Blasted->IsSubdued());
    TestEqual(TEXT("Still no kill is counted"), Arena.Mode()->Campaign()->Kills, Kills);
    return Arena.Tick(2);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraShieldFrontTest,
    "SoraArena.Combat.ShieldFront",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraShieldFrontTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraCombatAutomation;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FArena Arena(*this, TEXT("ShieldFront"));
    if (!Arena.Start())
        return false;
    FLog Log;
    if (!TestTrue(TEXT("The event log attaches"), Log.Attach(Arena.Get())) || !Arm(Arena, 0))
        return false;
    // A shield enforcer held still, facing the hero.
    const auto Spawn = [&](float Distance, int32 Slot) -> ASoraEnemy*
    {
        Clear(Arena);
        ASoraEnemy* Shield = Arena.SpawnKind(TEXT("shield_enforcer"), Slot, FVector(Distance, 0.f, 0.f), 180.f);
        if (Shield)
            Shield->SetActorTickEnabled(false);
        return Shield;
    };
    const auto Strike = [&](ASoraEnemy& Target) -> float
    {
        const float Health = Target.Health;
        const bool bOk = Swing(Arena) && Arena.Tick(30);
        return bOk ? Health - Target.Health : -1.f;
    };
    Arena.PlaceHero(FVector::ZeroVector, 0.f);
    ASoraEnemy* Shield = Spawn(180.f, 40);
    if (!TestNotNull(TEXT("A shield enforcer spawns"), Shield) || !Arena.Tick(2))
        return false;
    TestEqual(TEXT("A katana cut on the squared shield does nothing"), Strike(*Shield), 0.f);
    TestEqual(TEXT("The shield's block is announced"),
        Log.CountIf(Log.Guarded, [Shield](const FSoraDefenseEvent& E) { return E.Defender == Shield; }), 1);
    // From behind the shield covers nothing.
    Arena.PlaceHero(FVector(360.f, 0.f, 0.f), 180.f);
    TestEqual(TEXT("A cut from behind lands in full"), Strike(*Shield), 52.f);

    // A yari thrust on the rim turns the shield aside; the next thrust lands.
    if (!Arm(Arena, 19))
        return false;
    Arena.PlaceHero(FVector::ZeroVector, 0.f);
    Shield = Spawn(240.f, 41);
    if (!TestNotNull(TEXT("A second shield enforcer spawns"), Shield) || !Arena.Tick(2))
        return false;
    TestEqual(TEXT("A rim thrust does no damage"), Strike(*Shield), 0.f);
    TestTrue(TEXT("The rim thrust turns the shield aside"), Shield->IsShieldOpen());
    TestEqual(TEXT("The turned shield is announced"), Log.CueCount(Shield, ESoraEnemyCue::ShieldTurned), 1);
    // The yari recovers and thrusts again while the shield is still turned.
    const float Opened = Shield->Health;
    if (!TestTrue(TEXT("The yari thrusts again"), Swing(Arena)) || !Until(Arena, 60, [&]() { return Shield->Health < Opened; }))
        return false;
    TestEqual(TEXT("The next thrust lands inside the opening"), Opened - Shield->Health, FSoraCatalog::Get().Weapon(19).Damage);
    if (!Arena.Tick(90))
        return false;
    TestFalse(TEXT("The shield squares again"), Shield->IsShieldOpen());

    // A shell bursting on the shield's face is stopped too.
    if (!Arm(Arena, 7))
        return false;
    Arena.PlaceHero(FVector::ZeroVector, 0.f);
    Shield = Spawn(600.f, 42);
    if (!TestNotNull(TEXT("A third shield enforcer spawns"), Shield) || !Arena.Tick(2) || !Tap(Arena, EKeys::LeftMouseButton) ||
        !Until(Arena, 90, [&]() { return Log.BlastsBy(Arena.Hero()) > 0; }))
        return false;
    TestEqual(TEXT("A frontal blast is stopped by the shield"), Shield->Health, static_cast<float>(Shield->Archetype()->Health));
    return Arena.Tick(2);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraRangedTelegraphsTest,
    "SoraArena.Combat.RangedTelegraphs",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraRangedTelegraphsTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraCombatAutomation;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FArena Arena(*this, TEXT("RangedTelegraphs"));
    if (!Arena.Start())
        return false;
    FLog Log;
    if (!TestTrue(TEXT("The event log attaches"), Log.Attach(Arena.Get())) || !Arm(Arena, 0))
        return false;
    ASoraPlayerCharacter* Hero = Arena.Hero();
    // Waits for Enemy's next windup; the time it began.
    const auto NextWindup = [&](ASoraEnemy& Enemy, float& At) -> bool
    {
        const int32 Cues = Log.CueCount(&Enemy, ESoraEnemyCue::AttackWindup);
        if (!Until(Arena, 900, [&]() { return Log.CueCount(&Enemy, ESoraEnemyCue::AttackWindup) > Cues; }))
            return false;
        At = Log.Cues.Last().Time;
        return Log.CueCount(&Enemy, ESoraEnemyCue::AttackWindup) > Cues;
    };
    // Damage Causer has dealt the hero since event index From, and when it first landed.
    const auto Dealt = [&](const AActor* Causer, int32 From, float& FirstAt) -> float
    {
        float Total = 0.f;
        FirstAt = 0.f;
        for (int32 Index = From; Index < Log.Damaged.Num(); ++Index)
            if (Log.Damaged[Index].Event.Victim == Hero && Log.Damaged[Index].Event.Causer == Causer)
            {
                Total += Log.Damaged[Index].Event.Amount;
                FirstAt = FirstAt ? FirstAt : Log.Damaged[Index].Time;
            }
        return Total;
    };
    float WindupAt = 0.f, HitAt = 0.f;

    // The marksman's cyan glint: 900 ms of warning, then 40 damage; a wall
    // raised during the glint holds the shot.
    Arena.PlaceHero(FVector::ZeroVector, 0.f);
    ASoraEnemy* Marksman = Arena.SpawnKind(TEXT("marksman"), 50, FVector(2500.f, 0.f, 0.f), 180.f);
    if (!TestNotNull(TEXT("A marksman spawns"), Marksman))
        return false;
    Marksman->GetCharacterMovement()->DisableMovement();
    int32 From = Log.Damaged.Num();
    if (!TestTrue(TEXT("The marksman locks on"), NextWindup(*Marksman, WindupAt)) ||
        !Until(Arena, 120, [&]() { return !Marksman->IsCommitted(); }) || !Arena.Tick(1))
        return false;
    TestEqual(TEXT("The assessed shot deals 40"), Dealt(Marksman, From, HitAt), 40.f);
    TestTrue(TEXT("The glint precedes the shot by its 900 ms"), HitAt - WindupAt >= .9f - Frame);
    const int32 Shots = Marksman->RangedShotsFired();
    if (!TestTrue(TEXT("The marksman locks on again"), NextWindup(*Marksman, WindupAt)))
        return false;
    From = Log.Damaged.Num();
    AActor* Screen = Arena.Wall(FVector(1250.f, 0.f, 200.f), FVector(60.f, 800.f, 400.f));
    if (!Until(Arena, 120, [&]() { return !Marksman->IsCommitted(); }) || !Arena.Tick(1))
        return false;
    TestEqual(TEXT("Broken line of sight holds the shot"), Dealt(Marksman, From, HitAt), 0.f);
    TestEqual(TEXT("No round leaves the barrel"), Marksman->RangedShotsFired(), Shots);
    Screen->Destroy();

    // The drone's seizure net: a cyan lock ring for 800 ms, then a 1.5 s hold
    // on a hero who stayed in the ring; one who stepped out walks on.
    Clear(Arena);
    Arena.PlaceHero(FVector::ZeroVector, 0.f);
    ASoraEnemy* Drone = Arena.SpawnKind(TEXT("drone"), 51, FVector(800.f, 0.f, 0.f), 180.f);
    if (!TestNotNull(TEXT("A drone spawns"), Drone))
        return false;
    USoraCombatEffects* Effects = USoraCombatEffects::Get(Arena.Get());
    if (!TestTrue(TEXT("The drone locks its net ring"), NextWindup(*Drone, WindupAt)))
        return false;
    TestFalse(TEXT("Nobody is held during the lock"), Effects->IsRooted(Hero));
    if (!Until(Arena, 90, [&]() { return Effects->IsRooted(Hero); }))
        return false;
    TestTrue(TEXT("A hero who stayed in the ring is netted"), Effects->IsRooted(Hero) && Hero->GetCharacterMovement()->MovementMode == MOVE_None);
    TestTrue(TEXT("The net drops no sooner than its 800 ms lock"), Log.Now() - WindupAt >= .8f - Frame);
    if (!Until(Arena, 150, [&]() { return !Effects->IsRooted(Hero); }))
        return false;
    TestTrue(TEXT("The net lets go after its hold"), !Effects->IsRooted(Hero) && Hero->GetCharacterMovement()->MovementMode == MOVE_Walking);
    if (!TestTrue(TEXT("The drone locks again"), NextWindup(*Drone, WindupAt)))
        return false;
    Arena.PlaceHero(FVector(0.f, 400.f, 0.f), 0.f);
    if (!Until(Arena, 90, [&]() { return !Drone->IsCommitted(); }) || !Arena.Tick(1))
        return false;
    TestFalse(TEXT("A hero who left the ring is not netted"), Effects->IsRooted(Hero));

    // The walker's sweep beam: a cyan ground line for 1100 ms, then a beam no
    // guard stops; a step off the line escapes it.
    Clear(Arena);
    Arena.PlaceHero(FVector::ZeroVector, 0.f);
    ASoraEnemy* Walker = Arena.SpawnKind(TEXT("seizure_walker"), 52, FVector(2000.f, 0.f, 0.f), 180.f);
    if (!TestNotNull(TEXT("A seizure walker spawns"), Walker) || !TestTrue(TEXT("The walker locks its line"), NextWindup(*Walker, WindupAt)))
        return false;
    From = Log.Damaged.Num();
    if (!Press(Arena, EKeys::LeftControl, true) || !Until(Arena, 120, [&]() { return !Walker->IsCommitted(); }) || !Arena.Tick(1) ||
        !Press(Arena, EKeys::LeftControl, false))
        return false;
    TestEqual(TEXT("No guard stops the sweep beam"), Dealt(Walker, From, HitAt), 30.f);
    TestTrue(TEXT("The ground line precedes the beam by its 1100 ms"), HitAt - WindupAt >= 1.1f - Frame);
    if (!TestTrue(TEXT("The walker locks again"), NextWindup(*Walker, WindupAt)))
        return false;
    From = Log.Damaged.Num();
    Arena.PlaceHero(FVector(0.f, 300.f, 0.f), 0.f);
    if (!Until(Arena, 120, [&]() { return !Walker->IsCommitted(); }) || !Arena.Tick(1))
        return false;
    TestEqual(TEXT("A step off the locked line escapes the beam"), Dealt(Walker, From, HitAt), 0.f);

    // The auditor: weak, it skips suspicion, raises an alarm that carries
    // past a trooper's shout, and runs.
    Clear(Arena);
    Arena.PlaceHero(FVector::ZeroVector, 0.f);
    FSoraPatrolRoute Desk;
    Desk.Points.Add(FVector(400.f, 0.f, 90.f));
    ASoraEnemy* Auditor = Arena.SpawnKind(TEXT("auditor"), 53, FVector(400.f, 0.f, 0.f), 180.f, &Desk);
    FSoraPatrolRoute Gate;
    Gate.Points.Add(FVector(400.f, 2400.f, 90.f));
    ASoraEnemy* Trooper = Arena.SpawnKind(TEXT("enforcer_rifle"), 54, FVector(400.f, 2400.f, 0.f), 90.f, &Gate);
    if (!TestNotNull(TEXT("An auditor spawns"), Auditor) || !TestNotNull(TEXT("A distant trooper spawns"), Trooper))
        return false;
    TestTrue(TEXT("The trooper stands beyond a shout but inside the alarm"),
        FVector::Dist(Auditor->GetActorLocation(), Trooper->GetActorLocation()) > SoraStealthRules::NoiseRadiusCm(SoraStealthRules::ENoise::Callout) &&
        FVector::Dist(Auditor->GetActorLocation(), Trooper->GetActorLocation()) < Auditor->Archetype()->AlarmRadiusCm);
    if (!Until(Arena, 300, [&]() { return Log.CueCount(Auditor, ESoraEnemyCue::Alarm) > 0; }))
        return false;
    TestTrue(TEXT("The auditor raises the alarm"), Log.CueCount(Auditor, ESoraEnemyCue::Alarm) > 0);
    TestEqual(TEXT("It never stops at suspicion"), Log.CountIf(Log.Cues, [Auditor](const FLog::FStamped<FSoraEnemyCueEvent>& E)
        { return E.Event.Enemy == Auditor && E.Event.Detail == FName(TEXT("suspicious")); }), 0);
    const float Start = FVector::Dist2D(Auditor->GetActorLocation(), Hero->GetActorLocation());
    if (!Arena.Tick(60))
        return false;
    const ASoraEnemyController* Distant = FArena::Brain(Trooper);
    TestTrue(TEXT("The alarm reaches the distant trooper"), Distant && Distant->State() != SoraStealthRules::EState::Unaware &&
        FVector::Dist2D(Distant->LastKnownLocation(), Hero->GetActorLocation()) < 300.f);
    TestTrue(TEXT("The auditor runs from the hero"), FVector::Dist2D(Auditor->GetActorLocation(), Hero->GetActorLocation()) > Start + 100.f);
    return Arena.Tick(2);
}
#endif
