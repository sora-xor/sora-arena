#include "SoraGameMode.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Combat/SoraStealth.h"
#include "HUD/SoraHUDPanels.h"
#include "SoraAutomationWorld.h"
#include "SoraCampaignDirector.h"
#include "SoraCampaignRules.h"
#include "SoraCatalog.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "SoraEnemyTestArena.h"
#include "SoraGameEvents.h"
#include "SoraInputStates.h"
#include "SoraPlayerCharacter.h"
#include "SoraSaveGame.h"
#include "SoraSettings.h"
#include "SoraStealthRules.h"
#include "SoraWorldBuilder.h"
#include "Components/StaticMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Algo/AllOf.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/DamageType.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Misc/AutomationTest.h"
#include "Templates/UniquePtr.h"

// Where the lanes meet, in real game worlds: a campaign stealth beat opens the
// AI lane's stealth zone on the settings' difficulty with its guards on their
// patrol routes, and the zone's detection reaches the beat (a reinforce zone
// calls its wave; on Easy the zone answers with a fight and calls none); work
// under guard posts its guards and pauses only while one sees the hero; a beat
// lets the hero use what it teaches; opponents knocked down, knocked out or
// killed leave with their encounter; HUD prompts name the player's own keys
// and results head both languages; the telegraph palette reaches every
// opponent's telegraph and strike; and the settings' campaign difficulty
// scales an archetype's windup as it scales the bosses'.
namespace SoraIntegrationAutomation
{
// ch05.b02: a reinforce zone of rifle enforcers, a drone and two conscripts.
constexpr int32 ZoneChapter = 4, ZoneBeat = 1;

struct FZoneWorld
{
    FAutomationTestBase& Test;
    FString Slot;
    int32 Chapter = ZoneChapter;
    int32 Beat = ZoneBeat;
    TUniquePtr<FSoraAutomationWorld> World;
    FZoneWorld(FAutomationTestBase& InTest, const TCHAR* Name, int32 InChapter = ZoneChapter, int32 InBeat = ZoneBeat)
        : Test(InTest), Slot(FSoraAutomationWorld::UniqueSaveSlot(Name)), Chapter(InChapter), Beat(InBeat)
    {
        FSoraAutomationWorld::IgnoreMissingGeneratedArt(Test);
        FSoraAutomationWorld::IgnoreAbsentSaveSlot(Test, Slot);
    }
    ~FZoneWorld()
    {
        if (World)
        {
            World->DestroyTestWorld(true);
            World->ForwardErrorMessages(&Test);
            World.Reset();
        }
        FSoraAutomationWorld::DeleteSaveSlot(Slot);
    }
    ASoraGameMode* Mode() const { return World->Mode(); }
    USoraCampaignDirector* Campaign() const { return Mode()->Campaign(); }
    USoraStealth* Stealth() const { return USoraStealth::Get(World->GetTestWorld()); }
    ASoraPlayerCharacter* Hero() const { return World->Player(); }
    const FSoraBeat& BeatData() const { return Campaign()->ActiveChapter()->Beats[Beat]; }
    // The beat's checkpoint, continued from the main menu; a third Enter
    // skips a title card if one shows.
    bool Start()
    {
        USoraSaveGame* Save = Cast<USoraSaveGame>(UGameplayStatics::CreateSaveGameObject(USoraSaveGame::StaticClass()));
        if (!Save || !USoraCampaignDirector::SeedCheckpoint(*Save, Chapter, Beat) || !UGameplayStatics::SaveGameToSlot(Save, Slot, 0))
            return Test.TestTrue(TEXT("The beat's checkpoint is seeded"), false);
        World = MakeUnique<FSoraAutomationWorld>();
        if (!World->Start(Slot) || !World->Tick(1) || !World->EnableKeyInput() || !World->PressKey(EKeys::Enter) ||
            !World->PressKey(EKeys::Enter) || !World->PressKey(EKeys::Enter))
        {
            World->ForwardErrorMessages(&Test);
            return Test.TestTrue(TEXT("The beat's world starts"), false);
        }
        return Test.TestTrue(TEXT("The beat is in play"), Mode()->IsPlaying() && Campaign()->ActiveBeat() == Beat);
    }
    bool Tick(int32 Frames, float DeltaSeconds = 1.f / 60.f)
    {
        if (World->Tick(Frames, DeltaSeconds))
            return true;
        World->ForwardErrorMessages(&Test);
        return Test.TestTrue(TEXT("The world ticks"), false);
    }
    // The hero outlasts every shot a test takes while it examines something else.
    void Harden() const
    {
        Hero()->MaxHealth = 100000.f;
        Hero()->Health = Hero()->MaxHealth;
    }
    void Stand(const FVector& At) const
    {
        Hero()->SetActorLocation(FVector(At.X, At.Y, Hero()->GetActorLocation().Z), false, nullptr, ETeleportType::TeleportPhysics);
    }
    // A blow that ends the opponent's fight: a conscript is knocked down, anyone else falls.
    void Defeat(ASoraEnemy& Enemy) const
    {
        UGameplayStatics::ApplyDamage(&Enemy, Enemy.Health, Hero()->GetController(), Hero(), UDamageType::StaticClass());
    }
    // Opponents in the world, standing or down, that are not leaving it.
    TArray<ASoraEnemy*> Opponents(TFunctionRef<bool(const ASoraEnemy&)> Wanted) const
    {
        TArray<ASoraEnemy*> Found;
        for (TActorIterator<ASoraEnemy> It(World->GetTestWorld()); It; ++It)
            if (!It->IsActorBeingDestroyed() && Wanted(**It))
                Found.Add(*It);
        return Found;
    }
    static bool IsGuard(const ASoraEnemy& Enemy)
    {
        const ASoraEnemyController* Brain = Cast<ASoraEnemyController>(Enemy.GetController());
        return Brain && Brain->IsGuard();
    }
    // The beat restarted from its checkpoint through the pause menu.
    bool Restart()
    {
        Mode()->OpenPauseMenu();
        if (!Mode()->RestartRound() || !World->Tick(2))
            return Test.TestTrue(TEXT("The stealth beat restarts"), false);
        if (Mode()->InputState() == SoraInput::Card && (!World->PressKey(EKeys::Enter) || !World->Tick(1)))
            return Test.TestTrue(TEXT("The restarted beat's card is skipped"), false);
        return Test.TestTrue(TEXT("The restarted beat is in play"), Mode()->IsPlaying() && Campaign()->ActiveBeat() == Beat);
    }
    int32 Count(bool bGuards) const
    {
        int32 Found = 0;
        for (TActorIterator<ASoraEnemy> It(World->GetTestWorld()); It; ++It)
        {
            const ASoraEnemyController* Brain = Cast<ASoraEnemyController>(It->GetController());
            Found += It->IsEnemy() && It->IsAlive() && !It->IsActorBeingDestroyed() && Brain && Brain->IsGuard() == bGuards ? 1 : 0;
        }
        return Found;
    }
};

// Every tracer and telegraph line in the world has the colour it was drawn
// in (ASoraWorldBuilder::Tint on SoraDamage::Beam's "Tracer" mesh).
void CollectTracerColors(UWorld& World, TArray<FLinearColor>& Seen)
{
    for (TActorIterator<AActor> It(&World); It; ++It)
    {
        const UStaticMeshComponent* Mesh = Cast<UStaticMeshComponent>(It->GetRootComponent());
        const UMaterialInstanceDynamic* Material = Mesh && Mesh->GetName().StartsWith(TEXT("Tracer"))
            ? Cast<UMaterialInstanceDynamic>(Mesh->GetMaterial(0)) : nullptr;
        if (!Material)
            continue;
        for (const FVectorParameterValue& Value : Material->VectorParameterValues)
            if (Value.ParameterInfo.Name == TEXT("Color") &&
                !Seen.ContainsByPredicate([&](const FLinearColor& Known) { return Known.Equals(Value.ParameterValue, .002f); }))
                Seen.Add(Value.ParameterValue);
    }
}
bool Drawn(const TArray<FLinearColor>& Seen, const FLinearColor& Color)
{
    return Seen.ContainsByPredicate([&](const FLinearColor& Known) { return Known.Equals(Color, .002f); });
}
} // namespace SoraIntegrationAutomation

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraIntegrationStealthZoneTest,
    "SoraArena.Integration.StealthZone",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraIntegrationStealthZoneTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraIntegrationAutomation;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FZoneWorld Zone(*this, TEXT("IntegrationStealthZone"));
    if (!Zone.Start())
        return false;
    USoraStealth* Stealth = Zone.Stealth();
    const FSoraBeat& Beat = Zone.Campaign()->ActiveChapter()->Beats[ZoneBeat];
    if (!TestNotNull(TEXT("The world has its stealth subsystem"), Stealth) ||
        !TestTrue(TEXT("The stealth beat opens its zone"), Stealth->IsZoneActive()))
        return false;
    TestTrue(TEXT("The zone takes the beat's reinforce answer on Normal"),
        Stealth->Zone().OnDetected == SoraStealthRules::EOnDetected::Reinforce && Stealth->Zone().Difficulty == SoraStealthRules::EDifficulty::Normal);
    TestEqual(TEXT("Every guard of the beat stands on its patrol, unaware"), Zone.Count(true), Beat.Guards.Num());
    TestEqual(TEXT("No hunter comes before a detection"), Zone.Count(false), 0);
    // The zone's detection reaches the beat, which calls its reinforcements.
    FSoraStealthDetection Detected;
    Detected.Response = SoraStealthRules::Response(Stealth->Zone().OnDetected, Stealth->Zone().Difficulty);
    Stealth->OnDetected.Broadcast(Detected);
    if (!Zone.World->Tick(2))
        return false;
    TestTrue(TEXT("A detection in a reinforce zone calls the beat's wave"), Zone.Count(false) > 0);

    // On Easy the zone answers a detection with a fight and calls nobody.
    Zone.Mode()->Settings()->SetCampaignDifficulty(SoraAccessibility::EDifficulty::Easy);
    if (!Zone.Restart())
        return false;
    TestTrue(TEXT("The restarted zone opens on Easy"), Stealth->IsZoneActive() && Stealth->Zone().Difficulty == SoraStealthRules::EDifficulty::Easy);
    TestEqual(TEXT("The restart puts back only the guards"), Zone.Count(false), 0);
    Detected.Response = SoraStealthRules::Response(Stealth->Zone().OnDetected, Stealth->Zone().Difficulty);
    TestTrue(TEXT("Easy turns a detection into a fight"), Detected.Response == SoraStealthRules::EOnDetected::Combat);
    Stealth->OnDetected.Broadcast(Detected);
    if (!Zone.World->Tick(2))
        return false;
    TestEqual(TEXT("On Easy no reinforcements come"), Zone.Count(false), 0);
    TestTrue(TEXT("and the beat goes on"), Zone.Mode()->IsPlaying() && Zone.Campaign()->ActiveBeat() == ZoneBeat);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraIntegrationDifficultyWindupTest,
    "SoraArena.Integration.DifficultyWindups",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraIntegrationDifficultyWindupTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using SoraAccessibility::EDifficulty;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    // A blade retainer's cut winds up for 420 ms on Normal (enemies.json);
    // Easy adds 30% and Hard takes 15% (bosses.json's difficulty permilles).
    const TPair<EDifficulty, float> Tiers[] = {{EDifficulty::Normal, .42f}, {EDifficulty::Easy, .546f}, {EDifficulty::Hard, .357f}};
    for (const TPair<EDifficulty, float>& Tier : Tiers)
    {
        SoraEnemyTest::FArena Arena(*this, TEXT("DifficultyWindups"));
        if (!Arena.Start())
            return false;
        Arena.Mode()->Settings()->SetCampaignDifficulty(Tier.Key);
        Arena.PlaceHero(FVector::ZeroVector, 0.f);
        ASoraEnemy* Retainer = Arena.SpawnKind(TEXT("blade_retainer"), 0, FVector(150.f, 0.f, 0.f), 180.f);
        if (!TestNotNull(TEXT("A blade retainer spawns"), Retainer))
            return false;
        float Windup = -1.f;
        const FDelegateHandle Handle = USoraGameEvents::Get(Arena.Get())->OnMeleeCommitted.AddLambda([&](const FSoraMeleeCommittedEvent& Event)
        {
            if (Event.Attacker == Retainer && Windup < 0.f)
                Windup = Event.WindupSeconds;
        });
        for (int32 Frame = 0; Frame < 600 && Windup < 0.f; ++Frame)
            if (!Arena.Tick(1))
                break;
        USoraGameEvents::Get(Arena.Get())->OnMeleeCommitted.Remove(Handle);
        TestTrue(*FString::Printf(TEXT("Difficulty %d: the retainer's cut winds up for %.3f s"), static_cast<int32>(Tier.Key), Tier.Value),
            FMath::IsNearlyEqual(Windup, Tier.Value, .0005f));
    }
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraIntegrationTaughtInBeatTest,
    "SoraArena.Integration.TaughtInBeat",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraIntegrationTaughtInBeatTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraIntegrationAutomation;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    // ch03.b03, the ward gate, teaches the rear takedown and the seal cut: both
    // work in it, before the beat completes and keeps them.
    FZoneWorld Gate(*this, TEXT("IntegrationTaughtInBeat"), 2, 2);
    if (!Gate.Start() || !TestEqual(TEXT("The ward gate is in play"), Gate.BeatData().Id, FString(TEXT("ch03.b03"))))
        return false;
    USoraCampaignDirector* Campaign = Gate.Campaign();
    USoraStealth* Stealth = Gate.Stealth();
    const int32 SealBit = FSoraCatalog::Get().Mechanics.Find(TEXT("seal_cut"));
    TestTrue(TEXT("The seal cut is kept only once the beat completes"),
        SealBit != INDEX_NONE && (Campaign->Progress().MechanicsMask & (1u << SealBit)) == 0u);
    TestTrue(TEXT("The beat that teaches them has the takedown and the seal cut in play"),
        Campaign->IsMechanicInPlay(TEXT("takedown")) && Campaign->IsMechanicInPlay(TEXT("seal_cut")));
    if (!TestTrue(TEXT("Its stealth zone allows rear takedowns"), Stealth && Stealth->IsZoneActive() && Stealth->Zone().bRearTakedowns))
        return false;
    Gate.Harden();
    // Behind an unaware rifle guard, facing its back, Melee takes it down.
    const TArray<ASoraEnemy*> Rifles = Gate.Opponents([](const ASoraEnemy& Enemy)
    {
        const ASoraEnemyController* Brain = Cast<ASoraEnemyController>(Enemy.GetController());
        return FZoneWorld::IsGuard(Enemy) && Enemy.IsAlive() && !Enemy.IsNonlethal() && Enemy.CanBeTakenDown() &&
            SoraStealthRules::IsCalm(Brain->State());
    });
    if (!TestTrue(TEXT("A rifle guard stands its post"), Rifles.Num() > 0))
        return false;
    ASoraEnemy* Rifle = Rifles[0];
    const FVector Back = Rifle->GetActorLocation() - Rifle->GetActorForwardVector().GetSafeNormal2D() * 90.f;
    Gate.Stand(Back);
    const FRotator Facing(0.f, (Rifle->GetActorLocation() - Back).Rotation().Yaw, 0.f);
    Gate.Hero()->GetController()->SetControlRotation(Facing);
    Gate.Hero()->FaceRotation(Facing, 0.f);
    TestTrue(TEXT("From behind, the unaware guard can be taken down"), Stealth->TakedownTarget(*Gate.Hero()) == Rifle);
    // A collared guard knocked down; Interact held beside it cuts its seal.
    const TArray<ASoraEnemy*> Collared = Gate.Opponents([](const ASoraEnemy& Enemy)
        { return FZoneWorld::IsGuard(Enemy) && Enemy.IsAlive() && Enemy.IsNonlethal(); });
    if (!TestTrue(TEXT("A collared guard stands its post"), Collared.Num() > 0))
        return false;
    ASoraEnemy* Conscript = Collared[0];
    Gate.Defeat(*Conscript);
    if (!TestTrue(TEXT("A lethal blow only knocks the collared guard down"), Conscript->IsSubdued()))
        return false;
    Gate.Stand(Conscript->GetActorLocation() + FVector(80.f, 0.f, 0.f));
    Gate.World->InjectKey(EKeys::E, IE_Pressed);
    const bool bHeld = Gate.Tick(5, .4f);
    Gate.World->InjectKey(EKeys::E, IE_Released);
    if (!bHeld || !Gate.Tick(1))
        return false;
    TestTrue(TEXT("Interact held beside it cuts the collar in the beat that teaches the cut"), Conscript->IsFreed());
    TestEqual(TEXT("and the beat is still the ward gate"), Campaign->ActiveBeat(), 2);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraIntegrationOpponentsLeaveTest,
    "SoraArena.Integration.OpponentsLeave",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraIntegrationOpponentsLeaveTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraIntegrationAutomation;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    {
        // The ward gate restarted from its checkpoint: a collared guard knocked
        // down, a guard knocked out and one killed stay down through the beat,
        // and leave with the round; only the zone's fresh guards stand after it.
        FZoneWorld Gate(*this, TEXT("IntegrationOpponentsLeaveGate"), 2, 2);
        if (!Gate.Start())
            return false;
        Gate.Harden();
        const TArray<ASoraEnemy*> Collared = Gate.Opponents([](const ASoraEnemy& Enemy) { return Enemy.IsAlive() && Enemy.IsNonlethal(); });
        const TArray<ASoraEnemy*> Rifles = Gate.Opponents([](const ASoraEnemy& Enemy) { return Enemy.IsAlive() && !Enemy.IsNonlethal(); });
        if (!TestTrue(TEXT("The gate has a collared guard and two others"), Collared.Num() > 0 && Rifles.Num() > 1))
            return false;
        Gate.Defeat(*Collared[0]);
        Rifles[0]->KnockOut(Gate.Hero());
        Gate.Defeat(*Rifles[1]);
        const TArray<TWeakObjectPtr<ASoraEnemy>> Down = {Collared[0], Rifles[0], Rifles[1]};
        if (!Gate.Tick(2))
            return false;
        TestTrue(TEXT("Knocked down, knocked out or killed, each stays down in the beat for the guards to find"),
            Algo::AllOf(Down, [](const TWeakObjectPtr<ASoraEnemy>& Enemy) { return Enemy.IsValid() && Enemy->IsBody(); }));
        if (!Gate.Restart())
            return false;
        TestTrue(TEXT("Every one of them leaves with the round"),
            Algo::AllOf(Down, [](const TWeakObjectPtr<ASoraEnemy>& Enemy) { return !Enemy.IsValid() || Enemy->IsActorBeingDestroyed(); }));
        TestEqual(TEXT("Only the zone's fresh guards are in the world"), Gate.Opponents([](const ASoraEnemy&) { return true; }).Num(),
            Gate.BeatData().Guards.Num());
    }
    // The foundry yard (ch05.b05): a conscript released with the second wave
    // is knocked down, and the yard is cleared around it. It leaves with its
    // beat, and nothing rises in the next.
    FZoneWorld Yard(*this, TEXT("IntegrationOpponentsLeaveYard"), 4, 4);
    if (!Yard.Start() || !TestEqual(TEXT("The foundry yard is in play"), Yard.BeatData().Id, FString(TEXT("ch05.b05"))))
        return false;
    Yard.Harden();
    int32 Risen = 0;
    USoraGameEvents* Events = USoraGameEvents::Get(Yard.World->GetTestWorld());
    const FDelegateHandle Handle = Events->OnEnemyCue.AddLambda([&Risen](const FSoraEnemyCueEvent& Event) { Risen += Event.Cue == ESoraEnemyCue::Risen; });
    TWeakObjectPtr<ASoraEnemy> Downed;
    bool bKnockedDown = false;
    for (int32 Round = 0; Round < 120 && Yard.Campaign()->ActiveBeat() == 4; ++Round)
    {
        const TArray<ASoraEnemy*> Collared = Yard.Opponents([](const ASoraEnemy& Enemy) { return Enemy.IsAlive() && Enemy.IsNonlethal(); });
        const TArray<ASoraEnemy*> Lethal = Yard.Opponents([](const ASoraEnemy& Enemy) { return Enemy.IsEnemy() && Enemy.IsAlive() && !Enemy.IsNonlethal(); });
        if (!bKnockedDown && Collared.Num() > 0)
        {
            Downed = Collared[0];
            Yard.Defeat(*Collared[0]);
            bKnockedDown = TestTrue(TEXT("A lethal blow only knocks the conscript down"), Downed->IsSubdued());
        }
        else if (Lethal.Num() > 0)
            Yard.Defeat(*Lethal[0]);
        if (!Yard.Tick(1))
            break;
    }
    const bool bCleared = TestTrue(TEXT("The yard is cleared and the next beat begins"), Yard.Campaign()->ActiveBeat() != 4) &&
        TestTrue(TEXT("A conscript was knocked down in the yard"), bKnockedDown);
    TestTrue(TEXT("The knocked-down conscript leaves with its beat"), !Downed.IsValid() || Downed->IsActorBeingDestroyed());
    // Past the collar's 8 s window nobody left behind rises.
    if (bCleared)
        Yard.Tick(600);
    Events->OnEnemyCue.Remove(Handle);
    TestEqual(TEXT("Nobody rises after the yard's beat"), Risen, 0);
    TestEqual(TEXT("No knocked-down conscript is left in the world"),
        Yard.Opponents([](const ASoraEnemy& Enemy) { return Enemy.IsSubdued(); }).Num(), 0);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraIntegrationGuardedWorkTest,
    "SoraArena.Integration.GuardedWork",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraIntegrationGuardedWorkTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraIntegrationAutomation;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    // Work under guard (ch03.b05's deliveries, ch05.b03's escort) posts its
    // authored patrols as the zone's guards; nobody hunts the hero.
    for (const TPair<int32, int32>& At : {TPair<int32, int32>(2, 4), TPair<int32, int32>(4, 2)})
    {
        FZoneWorld Work(*this, TEXT("IntegrationGuardedWorkPosts"), At.Key, At.Value);
        if (!Work.Start())
            return false;
        const FSoraBeat& Beat = Work.BeatData();
        TestTrue(*(Beat.Id + TEXT(": the work opens a stealth zone")), Work.Stealth()->IsZoneActive());
        TestTrue(*(Beat.Id + TEXT(": its guards stand on their patrols")), Beat.Guards.Num() > 0 && Work.Count(true) == Beat.Guards.Num());
        TestEqual(*(Beat.Id + TEXT(": nobody hunts the hero")), Work.Count(false), 0);
    }
    // ch06.b08: the totals copied at three desks (a hold) under three
    // auditors, a rifle and a drone.
    FZoneWorld Desks(*this, TEXT("IntegrationGuardedWorkDesks"), 5, 7);
    if (!Desks.Start() || !TestEqual(TEXT("The desks are in play"), Desks.BeatData().Id, FString(TEXT("ch06.b08"))))
        return false;
    USoraStealth* Stealth = Desks.Stealth();
    USoraCampaignDirector* Campaign = Desks.Campaign();
    TestTrue(TEXT("The desks open a stealth zone"), Stealth->IsZoneActive());
    TestEqual(TEXT("All five stand guard on their patrols"), Desks.Count(true), 5);
    TestEqual(TEXT("Nobody hunts the hero"), Desks.Count(false), 0);
    Desks.Harden();
    const FSoraBeatSpace& Space=Desks.BeatData().Space;
    if (!TestEqual(TEXT("The hold has three distinct desks"), Space.Objectives.Num(), 3))
        return false;
    const FVector Desk(Space.Objectives[2],Space.FloorAt(Space.Objectives[2]));
    // Isolate the detection-to-work contract at a real desk. Stop patrol and
    // movement while the fixture supplies one explicit alarm. Move the desk's
    // own auditor to the far corner of its authored route so physical contest
    // cannot substitute for detection; CopyDesks covers that separate cause.
    const TArray<ASoraEnemy*> Guards = Desks.Opponents([](const ASoraEnemy& Enemy) { return FZoneWorld::IsGuard(Enemy) && Enemy.IsAlive(); });
    if(!TestEqual(TEXT("All five live guards are available to the fixture"),Guards.Num(),5)) return false;
    for (ASoraEnemy* Guard : Guards)
    {
        Guard->SetActorTickEnabled(false);
        Guard->GetCharacterMovement()->StopMovementImmediately();
        Guard->GetCharacterMovement()->SetComponentTickEnabled(false);
        if(FVector::Dist2D(Guard->GetActorLocation(),Desk)<300.f)
        {
            const FVector2D Post=Space.Patrols[2][2];
            Guard->SetActorLocation(FVector(Post,Space.FloorAt(Post)+Guard->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2),
                false,nullptr,ETeleportType::TeleportPhysics);
        }
        auto* Brain=Cast<ASoraEnemyController>(Guard->GetController());
        Brain->BeginPatrol(FSoraPatrolRoute{});
        Brain->SetActorTickEnabled(false);
    }
    Desks.Hero()->SetActorLocation(Desk+FVector(0,0,Desks.Hero()->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2),
        false,nullptr,ETeleportType::TeleportPhysics);
    if(!Desks.Tick(2)||!Desks.World->InjectKey(EKeys::E,IE_Pressed)||!Desks.Tick(30)) return false;
    if(!TestTrue(TEXT("A held mapped interaction copies the third desk before the alarm"),
        Campaign->IsCopying()&&Campaign->TaskProgress().HoldProgress[2]>0&&!Campaign->IsHeldWorkWatched())) return false;
    // A guard that has placed the hero pauses the copying.
    Cast<ASoraEnemyController>(Guards[0]->GetController())->Rouse(Desks.Hero()->GetActorLocation());
    if (!Desks.Tick(2))
        return false;
    TestTrue(TEXT("The guard's detection reaches the zone"), Stealth->IsDetected());
    TestTrue(TEXT("Work under guard pauses while a guard is alarmed"), Stealth->IsWorkPaused());
    TestTrue(TEXT("The held desk operation remains admitted but watched"),Campaign->IsCopying()&&Campaign->IsHeldWorkWatched());
    const int32 Paused = Campaign->TaskProgress().Progress;
    if (!Desks.Tick(30))
        return false;
    TestEqual(TEXT("No copying is done while seen"), Campaign->TaskProgress().Progress, Paused);
    // Once no guard sees him the same held interaction resumes. The alarm
    // must not clear partial work or require an unrelated new interaction.
    for (ASoraEnemy* Guard : Guards)
        if (IsValid(Guard) && Guard->IsAlive())
            Desks.Defeat(*Guard);
    if (!Desks.Tick(2))
        return false;
    TestFalse(TEXT("With no guard standing the work is not paused"), Stealth->IsWorkPaused());
    const int32 Resumed = Campaign->TaskProgress().Progress;
    if (!Desks.Tick(60))
        return false;
    TestTrue(TEXT("The copying goes on once no guard sees the hero"), Campaign->TaskProgress().Progress > Resumed);
    Desks.World->InjectKey(EKeys::E,IE_Released);
    const int32 Released=Campaign->TaskProgress().Progress;
    if(!Desks.Tick(30)) return false;
    TestTrue(TEXT("Releasing the mapped key stops copying at its retained progress"),
        !Campaign->IsCopying()&&Campaign->TaskProgress().Progress==Released);
    AddInfo(TEXT("Directed detection-to-copying integration: guards are frozen and the desk's auditor is placed at its authored far patrol corner; ordinary stealth difficulty is not qualified here."));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraIntegrationCampaignPromptsTest,
    "SoraArena.Integration.CampaignPrompts",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraIntegrationCampaignPromptsTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraIntegrationAutomation;
    const FSoraCatalog& Catalog = FSoraCatalog::Get();
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    // ch02.b03 hands over the yari as it begins.
    FZoneWorld Armory(*this, TEXT("IntegrationCampaignPrompts"), 1, 2);
    if (!Armory.Start() || !TestEqual(TEXT("The armory is in play"), Armory.BeatData().Id, FString(TEXT("ch02.b03"))))
        return false;
    UWorld* World = Armory.World->GetTestWorld();
    // Every prompt of every chapter names real keys, never a raw token.
    for (int32 Chapter = 0; Chapter < SoraCampaignRules::ChapterCount; ++Chapter)
        for (const FSoraPrompt& Prompt : Catalog.Chapter(Chapter).Prompts)
        {
            const SoraText::FLine Line = SoraHUDPanels::KeyPrompt(World, Prompt.Japanese, Prompt.English);
            for (const FString& Text : {Line.Japanese, Line.English})
                TestTrue(*FString::Printf(TEXT("Chapter %d prompt resolves its keys: %s"), Chapter + 1, *Text),
                    !Text.Contains(TEXT("{")) && !Text.Contains(TEXT("}")) && !Text.Contains(TEXT("—")));
        }
    // The armory's opening prompt names the yari's keys, and the first of them takes it up.
    const FSoraPrompt* Prompt = Armory.Campaign()->CurrentPrompt();
    if (!TestNotNull(TEXT("The armory opens on its prompt"), Prompt))
        return false;
    const SoraText::FLine Shown = SoraHUDPanels::KeyPrompt(World, Prompt->Japanese, Prompt->English);
    TestEqual(TEXT("The prompt names the yari's keys"), Shown.English, FString(TEXT("Yari acquired. Press [2] (polearms) or [X] to switch.")));
    TestTrue(TEXT("in Japanese too"), Shown.Japanese.Contains(TEXT("［2］（長柄）／［X］")));
    TestTrue(TEXT("The yari is kept only once the beat completes"), (Armory.Campaign()->Progress().WeaponsMask & (1u << 19)) == 0u);
    if (!Armory.World->PressKey(EKeys::Two) || !Armory.Tick(1))
        return false;
    TestEqual(TEXT("2, the polearms key, takes up the yari in the beat that hands it over"), Armory.Hero()->WeaponId, 19);

    // The result screen heads every ending in both languages.
    ASoraGameMode* Mode = Armory.Mode();
    USoraCampaignDirector* Campaign = Armory.Campaign();
    const int32 Chapter = Campaign->ChapterId;
    const bool bComplete = Campaign->bCampaignComplete;
    const auto Heads = [&](const TCHAR* What, const TCHAR* Japanese, const TCHAR* English)
    {
        const SoraText::FLine Headline = SoraHUDPanels::ResultHeadline(*Mode);
        TestEqual(*FString::Printf(TEXT("%s is headed in Japanese"), What), Headline.Japanese, FString(Japanese));
        TestEqual(*FString::Printf(TEXT("%s is headed in English"), What), Headline.English, FString(English));
    };
    Campaign->ChapterId = 0;
    Heads(TEXT("The dojo's end"), TEXT("道場の修行を終えた"), TEXT("Dojo training complete"));
    Campaign->ChapterId = 3;
    Heads(TEXT("A later chapter's end"), TEXT("街区を解放した"), TEXT("District liberated"));
    Campaign->bCampaignComplete = true;
    Heads(TEXT("The liberation"), TEXT("猫柳生、解放"), TEXT("Nyaagyu liberated"));
    Campaign->bCampaignComplete = bComplete;
    Mode->bDefeated = true;
    Heads(TEXT("A fall"), TEXT("ふたたび立ち上がれ"), TEXT("Rise again"));
    Mode->bDefeated = false;
    Mode->bCampaign = false;
    Heads(TEXT("The training arena"), TEXT("稽古場を制した"), TEXT("Training arena cleared"));
    Mode->bDeterministicPractice = true;
    Heads(TEXT("Practice"), TEXT("稽古終了"), TEXT("Practice over"));
    Mode->bDeterministicPractice = false;
    Mode->bCampaign = true;
    Campaign->ChapterId = Chapter;
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraIntegrationTelegraphDrawsTest,
    "SoraArena.Integration.TelegraphDraws",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraIntegrationTelegraphDrawsTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraIntegrationAutomation;
    using SoraAccessibility::ETelegraph;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    // On the high-contrast palette: the dojo pupil's windup, a loom
    // automaton's sweep, a drone's net and a walker's beam, each telegraphed
    // and struck in the palette's colours and never in the old fixed ones.
    SoraEnemyTest::FArena Arena(*this, TEXT("IntegrationTelegraphDraws"));
    if (!Arena.Start())
        return false;
    Arena.Mode()->Settings()->SetTelegraphPalette(SoraAccessibility::EPalette::HighContrast);
    Arena.PlaceHero(FVector::ZeroVector, 0.f);
    FActorSpawnParameters Params;
    Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;
    ASoraEnemy* Pupil = Arena.Get()->SpawnActor<ASoraEnemy>(FVector(150.f, 0.f, 120.f), FRotator(0.f, 180.f, 0.f), Params);
    if (!TestNotNull(TEXT("A dojo pupil spars"), Pupil))
        return false;
    Pupil->InitDojoPupil(0);
    const bool bSpawned = Arena.SpawnKind(TEXT("loom_automaton"), 1, FVector(-160.f, 0.f, 0.f), 0.f) &&
        Arena.SpawnKind(TEXT("drone"), 2, FVector(700.f, 400.f, 0.f), 200.f) &&
        Arena.SpawnKind(TEXT("seizure_walker"), 3, FVector(900.f, -300.f, 0.f), 160.f);
    if (!TestTrue(TEXT("The automaton, the drone and the walker spawn"), bSpawned))
        return false;
    int32 PupilWindups = 0;
    USoraGameEvents* Events = USoraGameEvents::Get(Arena.Get());
    const FDelegateHandle Handle = Events->OnMeleeCommitted.AddLambda([&](const FSoraMeleeCommittedEvent& Event) { PupilWindups += Event.Attacker == Pupil; });
    TArray<FLinearColor> Seen;
    for (int32 Frame = 0; Frame < 900; ++Frame)
    {
        if (!Arena.Tick(1))
            break;
        CollectTracerColors(*Arena.Get(), Seen);
    }
    Events->OnMeleeCommitted.Remove(Handle);
    UWorld* World = Arena.Get();
    TestTrue(TEXT("The pupil wound up its cut"), PupilWindups > 0);
    TestTrue(TEXT("The pupil's windup and the sweep are telegraphed in the palette's cleave colour"),
        Drawn(Seen, SoraAccessibility::TelegraphColor(World, ETelegraph::Cleave)));
    TestTrue(TEXT("The sweep strikes in the palette's lighter cleave shade"), Drawn(Seen, SoraAccessibility::StrikeColor(World, ETelegraph::Cleave)));
    TestTrue(TEXT("The net and the beam strike in the palette's lighter lock shade"), Drawn(Seen, SoraAccessibility::StrikeColor(World, ETelegraph::Lock)));
    TestFalse(TEXT("No telegraph or strike keeps the old fixed amber or cyan"),
        Drawn(Seen, FLinearColor(1.f, .68f, .16f)) || Drawn(Seen, FLinearColor(1.f, .80f, .24f)) || Drawn(Seen, FLinearColor(.12f, 1.f, 1.f)));
    return true;
}
#endif
