#include "SoraGameMode.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Combat/SoraStealth.h"
#include "SoraAutomationWorld.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "SoraEnemyTestArena.h"
#include "SoraGameEvents.h"
#include "SoraInputStates.h"
#include "SoraSaveGame.h"
#include "SoraSettings.h"
#include "SoraStealthRules.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/AutomationTest.h"
#include "Templates/UniquePtr.h"

// Where the lanes meet, in real game worlds: a campaign stealth beat opens the
// AI lane's stealth zone on the settings' difficulty with its guards on their
// patrol routes, and the zone's detection reaches the beat (a reinforce zone
// calls its wave; on Easy the zone answers with a fight and calls none); and
// the settings' campaign difficulty scales an archetype's windup as it scales
// the bosses'.
namespace SoraIntegrationAutomation
{
// ch05.b02: a reinforce zone of rifle enforcers, a drone and two conscripts.
constexpr int32 ZoneChapter = 4, ZoneBeat = 1;

struct FZoneWorld
{
    FAutomationTestBase& Test;
    FString Slot;
    TUniquePtr<FSoraAutomationWorld> World;
    FZoneWorld(FAutomationTestBase& InTest, const TCHAR* Name) : Test(InTest), Slot(FSoraAutomationWorld::UniqueSaveSlot(Name))
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
    // The stealth beat's checkpoint, continued from the main menu; a third
    // Enter skips a title card if one shows.
    bool Start()
    {
        USoraSaveGame* Save = Cast<USoraSaveGame>(UGameplayStatics::CreateSaveGameObject(USoraSaveGame::StaticClass()));
        if (!Save || !USoraCampaignDirector::SeedCheckpoint(*Save, ZoneChapter, ZoneBeat) || !UGameplayStatics::SaveGameToSlot(Save, Slot, 0))
            return Test.TestTrue(TEXT("The stealth beat's checkpoint is seeded"), false);
        World = MakeUnique<FSoraAutomationWorld>();
        if (!World->Start(Slot) || !World->Tick(1) || !World->EnableKeyInput() || !World->PressKey(EKeys::Enter) ||
            !World->PressKey(EKeys::Enter) || !World->PressKey(EKeys::Enter))
        {
            World->ForwardErrorMessages(&Test);
            return Test.TestTrue(TEXT("The stealth beat's world starts"), false);
        }
        return Test.TestTrue(TEXT("The stealth beat is in play"), Mode()->IsPlaying() && Campaign()->ActiveBeat() == ZoneBeat);
    }
    // The beat restarted from its checkpoint through the pause menu.
    bool Restart()
    {
        Mode()->OpenPauseMenu();
        if (!Mode()->RestartRound() || !World->Tick(2))
            return Test.TestTrue(TEXT("The stealth beat restarts"), false);
        if (Mode()->InputState() == SoraInput::Card && (!World->PressKey(EKeys::Enter) || !World->Tick(1)))
            return Test.TestTrue(TEXT("The restarted beat's card is skipped"), false);
        return Test.TestTrue(TEXT("The restarted beat is in play"), Mode()->IsPlaying() && Campaign()->ActiveBeat() == ZoneBeat);
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
#endif
