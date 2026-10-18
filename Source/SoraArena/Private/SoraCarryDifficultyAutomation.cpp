#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraRecoveryAutomation.h"
#include "SoraCarryAutomation.h"
#include "SoraCatalog.h"
#include "SoraEnemy.h"
#include "SoraSaveGame.h"
#include "SoraSettings.h"
#include "EngineUtils.h"
#include "GameFramework/DamageType.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/AutomationTest.h"
#include "Misc/ScopeExit.h"
#include "Templates/UniquePtr.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraCarryDifficultyTest,"SoraArena.Campaign.CarryDifficulty",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraCarryDifficultyTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    const auto& Policy=FSoraCatalog::Get().Chapter(1).Beats[4].Task;
    TestFalse(TEXT("Catalog preserves Easy retention"),Policy.DropOnHitByDifficulty[0]);
    TestFalse(TEXT("Catalog preserves Normal retention"),Policy.DropOnHitByDifficulty[1]);
    TestTrue(TEXT("Catalog preserves Hard drops"),Policy.DropOnHitByDifficulty[2]);
    const FString Slot=FSoraAutomationWorld::UniqueSaveSlot(TEXT("CarryDifficulty"));
    FSoraAutomationWorld::IgnoreMissingGeneratedArt(*this);
    FSoraAutomationWorld::IgnoreAbsentSaveSlot(*this,Slot);
    TUniquePtr<FSoraAutomationWorld> World;
    const auto Destroy=[&]() { if(World) { World->DestroyTestWorld(true); World->ForwardErrorMessages(this); World.Reset(); } };
    ON_SCOPE_EXIT { Destroy(); FSoraAutomationWorld::DeleteSaveSlot(Slot); };
    const auto HoldOpponents=[&]() {
        // Damage is deliberately injected below, independently of AI attack
        // timing. The pickup still uses navigation, W and ordinary Interact.
        for(TActorIterator<ASoraEnemy> It(World->GetTestWorld());It;++It)
        {
            It->SetActorTickEnabled(false);
            It->GetCharacterMovement()->SetComponentTickEnabled(false);
            if(auto* Brain=It->GetController()) Brain->SetActorTickEnabled(false);
        }
    };
    const auto Start=[&](int32 Difficulty=-1) {
        World=MakeUnique<FSoraAutomationWorld>();
        if(!World->Start(Slot)) return false;
        // ResetRound prepares the saved beat on the first world tick, even
        // behind the title. Select the fixture's tier before that beat starts.
        if(Difficulty>=0) World->Mode()->Settings()->SetCampaignDifficulty(static_cast<SoraAccessibility::EDifficulty>(Difficulty));
        if(!World->Tick(1)||!World->EnableKeyInput()||!World->PressKey(EKeys::Enter)||!World->PressKey(EKeys::Enter)||!World->Mode()->IsPlaying()||
            World->Mode()->Campaign()->ActiveChapter()!=&FSoraCatalog::Get().Chapter(1)||World->Mode()->Campaign()->ActiveBeat()!=4) return false;
        const bool ExpectedDrop=World->Mode()->Settings()->CampaignDifficulty()==SoraAccessibility::EDifficulty::Hard;
        if(!TestEqual(TEXT("Beat start selects the saved settings tier"),World->Mode()->Campaign()->ActiveTask().DropOnHit,ExpectedDrop)) return false;
        HoldOpponents();
        return true;
    };
    const auto Pickup=[&]() {
        auto* Campaign=World->Mode()->Campaign();
        if(!SoraCarryAutomation::PrySeal(*World)) return false;
        const auto* Space=Campaign->ActiveSpace();
        if(!Space||Space->Pickups.Num()!=1) return false;
        const FVector At(Space->Pickups[0],World->Player()->GetActorLocation().Z);
        const bool Reached=FVector::Dist2D(World->Player()->GetActorLocation(),At)<=30.f||SoraRecoveryAutomation::WalkTo(*World,At);
        return Reached&&World->PressKey(EKeys::E)&&
            Campaign->TaskProgress().Carrying;
    };
    const auto Hit=[&](bool Drops) {
        auto* Hero=World->Player();
        const float Before=Hero->Health;
        UGameplayStatics::ApplyDamage(Hero,25.f,nullptr,nullptr,UDamageType::StaticClass());
        if(!World->Tick(1)) return false;
        const auto& State=World->Mode()->Campaign()->TaskProgress();
        const bool Damaged=TestTrue(TEXT("The load policy is exercised by actual damage"),Hero->Health<Before);
        const bool Correct=TestEqual(TEXT("Only Hard loses the seed-rice load on hit"),State.Carrying,!Drops);
        TestEqual(TEXT("A hit never delivers a load"),State.Done,0);
        return Damaged&&Correct;
    };
    const auto Retry=[&]() {
        auto* Hero=World->Player();
        UGameplayStatics::ApplyDamage(Hero,Hero->Health+1000.f,nullptr,nullptr,UDamageType::StaticClass());
        if(!World->Tick(2)||!World->Mode()->bDefeated||!World->PressKey(EKeys::Enter)||!World->Tick(30)) return false;
        HoldOpponents();
        return World->Mode()->IsPlaying()&&!World->Mode()->Campaign()->TaskProgress().Carrying;
    };
    for(int32 Difficulty=0;Difficulty<3;++Difficulty)
    {
        AddInfo(FString::Printf(TEXT("Seed-rice carry policy: difficulty %d (Easy=0, Normal=1, Hard=2)"),Difficulty));
        auto* Save=NewObject<USoraSaveGame>();
        if(!USoraCampaignDirector::SeedCheckpoint(*Save,1,4)||!UGameplayStatics::SaveGameToSlot(Save,Slot,0)||
            !TestTrue(TEXT("Authored seed-rice checkpoint starts at the selected difficulty"),Start(Difficulty))) return false;
        const bool Drops=Difficulty==2;
        if(!TestTrue(TEXT("Movement and Interact pick up one load"),Pickup())||!Hit(Drops)) return false;
        if(Drops&&!TestTrue(TEXT("Hard's dropped load can be picked up again"),Pickup())) return false;
        if(!TestTrue(TEXT("Death retry resets the carried load"),Retry())||
            !TestTrue(TEXT("The retried load can be picked up"),Pickup())||!Hit(Drops)) return false;
        Destroy();
        if(!TestTrue(TEXT("A fresh world reloads the carry checkpoint"),Start())) return false;
        TestEqual(TEXT("Difficulty persists in the isolated settings slot"),static_cast<int32>(World->Mode()->Settings()->CampaignDifficulty()),Difficulty);
        if(!TestTrue(TEXT("Reload starts without partial cargo"),!World->Mode()->Campaign()->TaskProgress().Carrying)||
            !TestTrue(TEXT("The reloaded load can be picked up"),Pickup())||!Hit(Drops)) return false;
        if(Difficulty==2)
        {
            // Difficulty is selected afresh at a beat's start, including a
            // retry. Changing the setting must not mutate the catalog policy.
            World->Mode()->Settings()->SetCampaignDifficulty(SoraAccessibility::EDifficulty::Easy);
            if(!TestTrue(TEXT("Retry reads a newly selected difficulty"),Retry())||
                !TestTrue(TEXT("The load remains available after changing difficulty"),Pickup())||!Hit(false)) return false;
            TestTrue(TEXT("Changing settings preserves the authored Hard policy"),Policy.DropOnHitByDifficulty[2]);
        }
        Destroy();
    }
    return !HasAnyErrors();
}
#endif
