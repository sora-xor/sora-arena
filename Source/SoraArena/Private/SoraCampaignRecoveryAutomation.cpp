#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraRecoveryAutomation.h"
#include "SoraCatalog.h"
#include "SoraEquipmentComponent.h"
#include "SoraEnemy.h"
#include "SoraFieldcraft.h"
#include "EngineUtils.h"
#include "SoraSaveGame.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/DamageType.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/AutomationTest.h"
#include "Misc/ScopeExit.h"
#include "Templates/UniquePtr.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraCampaignRecoveryTest,"SoraArena.Campaign.EquipmentRecovery",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraCampaignRecoveryTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    const FString Slot=FSoraAutomationWorld::UniqueSaveSlot(TEXT("EquipmentRecovery"));
    FSoraAutomationWorld::IgnoreMissingGeneratedArt(*this);
    FSoraAutomationWorld::IgnoreAbsentSaveSlot(*this,Slot);
    TUniquePtr<FSoraAutomationWorld> World;
    const auto Destroy=[&]() { if(World) { World->DestroyTestWorld(true); World->ForwardErrorMessages(this); World.Reset(); } };
    ON_SCOPE_EXIT { Destroy(); FSoraAutomationWorld::DeleteSaveSlot(Slot); };
    const auto Seed=[&](int32 Beat) {
        auto* Save=NewObject<USoraSaveGame>();
        return USoraCampaignDirector::SeedCheckpoint(*Save,2,Beat)&&UGameplayStatics::SaveGameToSlot(Save,Slot,0);
    };
    const auto Start=[&]() {
        World=MakeUnique<FSoraAutomationWorld>();
        return World->Start(Slot)&&World->Tick(1)&&World->EnableKeyInput()&&
            World->PressKey(EKeys::Enter)&&World->PressKey(EKeys::Enter)&&!World->Mode()->bMenu&&
            !World->Mode()->bDefeated&&!World->Mode()->bChapterComplete&&World->Mode()->TitleCardTime<=0.f;
    };
    if(!TestTrue(TEXT("Recovery checkpoint starts"),Seed(4)&&Start())) return false;
    auto* Campaign=World->Mode()->Campaign();
    auto* Hero=World->Player();
    const auto* Scroll=FSoraCatalog::Get().Chapter(2).Collectibles.FindByPredicate(
        [](const FSoraCollectible& Item){return Item.Id==TEXT("ch03.c03");});
    if(!TestNotNull(TEXT("The authored well scroll exists"),Scroll))return false;
    const uint64 ScrollBit=SoraCampaignRules::CollectibleBit(2,Scroll->MaskBit);
    // Hold opponents in place to isolate this traversal test. The full
    // playthrough deals with these same guards before its retrieval.
    const auto HoldGuards=[&]() {
        for(TActorIterator<ASoraEnemy> It(World->GetTestWorld());It;++It)
        {
            It->SetActorTickEnabled(false);
            It->GetCharacterMovement()->SetComponentTickEnabled(false);
            if(auto* Brain=It->GetController()) Brain->SetActorTickEnabled(false);
        }
    };
    HoldGuards();
    const auto HasLine=[&](const TCHAR* Id) { return Campaign->QueuedSubtitles().ContainsByPredicate(
        [Id](const FSoraSubtitle& S) { return S.LineId==Id; }); };
    TestEqual(TEXT("Wakizashi is in hand on recovery-beat resume"),Hero->WeaponId,4);
    TestFalse(TEXT("An unlocked katana cannot be selected early"),Hero->GetEquipment()->EquipCampaignWeapon(0));
    TestFalse(TEXT("An unlocked bow cannot be selected early"),Hero->GetEquipment()->EquipCampaignWeapon(18));
    TestFalse(TEXT("Bow attacks are denied before pickup"),Campaign->ArmsReady(18,0,false));
    TestTrue(TEXT("Wakizashi remains usable"),Campaign->ArmsReady(4,0,false));
    if(!World->PressKey(EKeys::E)) return false;
    TestTrue(TEXT("Distant Interact cannot recover equipment"),Campaign->NeedsEquipmentRecovery());
    if(!TestTrue(TEXT("The court beside the well is reached through movement input"),
        SoraRecoveryAutomation::WalkTo(*World,FVector(-3220,3350,90)))||!World->PressKey(EKeys::E))return false;
    TestEqual(TEXT("Nearby court interaction cannot take the scroll seven metres below"),Campaign->CollectedMask()&ScrollBit,uint64(0));
    if(!TestTrue(TEXT("The rope is reached through movement input"),SoraRecoveryAutomation::WalkTo(*World,Campaign->RecoveryApproach()))) return false;
    const FVector Surface=Hero->GetActorLocation();
    TestEqual(TEXT("The lining scroll cannot be collected from the surface"),Campaign->CollectedMask()&ScrollBit,uint64(0));
    if(!World->InjectKey(EKeys::E,IE_Pressed)||!World->Tick(180)||!World->InjectKey(EKeys::E,IE_Released)||!World->Tick(1)) return false;
    const FVector Paused=Hero->GetActorLocation();
    TestTrue(TEXT("The rope moves the capsule down the shaft"),Paused.Z<Surface.Z-50.f);
    if(!World->Tick(60)) return false;
    TestTrue(TEXT("Releasing holds position safely on the rope"),Hero->GetActorLocation().Equals(Paused,.1f));
    TestFalse(TEXT("Climbing prevents weapon attacks"),Campaign->ArmsReady(4,0,false));
    if(!TestTrue(TEXT("Holding again resumes the swept descent"),SoraRecoveryAutomation::Rope(*World))) return false;
    TestTrue(TEXT("Bottom is seven metres below its surface"),FMath::IsNearlyEqual(Surface.Z-Hero->GetActorLocation().Z,700.f,10.f));
    TestTrue(TEXT("At bottom the capsule rests on collision"),Hero->GetCharacterMovement()->IsMovingOnGround());
    TestTrue(TEXT("Descent alone grants no equipment"),Campaign->NeedsEquipmentRecovery());
    if(!World->InjectKey(EKeys::E,IE_Pressed)||!World->Tick(90)||!World->InjectKey(EKeys::E,IE_Released)||!World->Tick(2)) return false;
    TestTrue(TEXT("Half-strung bow is not recovered"),Campaign->NeedsEquipmentRecovery());
    TestEqual(TEXT("Interrupted stringing resets its hold"),Campaign->TaskProgress().RecoveryHeldMs,0);
    if(!World->InjectKey(EKeys::E,IE_Pressed)||!World->Tick(170)) return false;
    TestTrue(TEXT("Less than three seconds cannot restore weapons"),Campaign->NeedsEquipmentRecovery());
    TestFalse(TEXT("Pickup line cannot play before recovery"),HasLine(TEXT("ch03.b05.nyaakoto.002")));
    if(!World->Tick(15)||!World->InjectKey(EKeys::E,IE_Released)||!World->Tick(1)) return false;
    TestFalse(TEXT("Three seconds completes recovery"),Campaign->NeedsEquipmentRecovery());
    TestEqual(TEXT("Recovered katana is in hand"),Hero->WeaponId,0);
    TestEqual(TEXT("Quiver has exactly twelve arrows"),Hero->GetEquipment()->AmmoByWeapon[18],12);
    TestTrue(TEXT("Pickup raises the quiet Nyaakoto line"),HasLine(TEXT("ch03.b05.nyaakoto.002")));
    TestFalse(TEXT("Kohagi does not speak her delayed line immediately"),HasLine(TEXT("ch03.b05.kohagi.003")));
    if(!World->Tick(242)) return false;
    TestTrue(TEXT("Four seconds after pickup raises Kohagi's instruction"),HasLine(TEXT("ch03.b05.kohagi.003")));
    TestTrue(TEXT("Restored bow can be selected"),Hero->GetEquipment()->EquipCampaignWeapon(18));
    if(!TestTrue(TEXT("Real held input climbs back to the courtyard"),SoraRecoveryAutomation::Rope(*World))) return false;
    TestTrue(TEXT("The player exits onto solid ground"),Hero->GetActorLocation().Z>0&&Hero->GetCharacterMovement()->IsMovingOnGround());
    TestEqual(TEXT("The bottom interaction collects the lining scroll"),Campaign->CollectedMask()&ScrollBit,ScrollBit);
    auto* Save=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(Slot,0));
    if(!TestNotNull(TEXT("Beat-start checkpoint still exists"),Save)) return false;
    TestEqual(TEXT("Retrieval alone does not invent a mid-beat checkpoint"),Save->CheckpointBeat,4);
    Destroy();
    if(!TestTrue(TEXT("Recovery beat reloads in a fresh world"),Start())) return false;
    Campaign=World->Mode()->Campaign(); Hero=World->Player();
    TestTrue(TEXT("Reload requires recovery again"),Campaign->NeedsEquipmentRecovery());
    TestEqual(TEXT("The lining find persists across a fresh-world load"),Campaign->CollectedMask()&ScrollBit,ScrollBit);
    TestEqual(TEXT("Reload restores wakizashi restriction"),Hero->WeaponId,4);
    HoldGuards();
    if(!SoraRecoveryAutomation::WalkTo(*World,Campaign->RecoveryApproach())||
        !World->InjectKey(EKeys::E,IE_Pressed)||!World->Tick(180)||!World->InjectKey(EKeys::E,IE_Released)) return false;
    TestTrue(TEXT("Retry test starts while suspended on the rope"),Campaign->IsClimbingRecoveryWell());
    UGameplayStatics::ApplyDamage(Hero,Hero->Health+1000.f,nullptr,nullptr,UDamageType::StaticClass());
    if(!World->Tick(2)||!TestTrue(TEXT("Death on the rope reaches the defeat screen"),World->Mode()->bDefeated)||
        !World->PressKey(EKeys::Enter)||!World->Tick(30)) return false;
    TestFalse(TEXT("Death retry clears the rope state"),Campaign->IsClimbingRecoveryWell());
    TestTrue(TEXT("Death retry restores walking above ground"),Hero->GetCharacterMovement()->IsMovingOnGround()&&Hero->GetActorLocation().Z>0.f);
    TestTrue(TEXT("Death retry has not recovered any equipment"),Campaign->NeedsEquipmentRecovery());
    Destroy();
    // ch03.b06 is a dialogue transition without a checkpoint. The next
    // authored checkpoint is ch03.b07, after that conversation.
    if(!TestTrue(TEXT("Next authored checkpoint loads"),Seed(6)&&Start())) return false;
    Campaign=World->Mode()->Campaign(); Hero=World->Player();
    TestFalse(TEXT("Later checkpoint does not replay retrieval"),Campaign->NeedsEquipmentRecovery());
    TestTrue(TEXT("Later checkpoint restores katana and bow availability"),Campaign->CanHold(0,false)&&Campaign->CanHold(18,false));
    TestEqual(TEXT("Later checkpoint restores twelve-arrow quiver"),Hero->GetEquipment()->AmmoByWeapon[18],12);
    auto* Fieldcraft=USoraFieldcraft::Get(Hero);
    if(!TestNotNull(TEXT("Escort checkpoint stages fieldcraft"),Fieldcraft)) return false;
    TestFalse(TEXT("Teardown fixture has live escorted companions"),Fieldcraft->PartyMembers().IsEmpty());
    if(!TestTrue(TEXT("World ends gameplay before its context is removed"),World->EndPlayInTestWorld())) return false;
    TestFalse(TEXT("End-play releases staged fieldcraft before subsystem deinitialization"),Fieldcraft->IsStaged());
    TestTrue(TEXT("End-play releases owned companions before context removal"),Fieldcraft->PartyMembers().IsEmpty());
    return !HasAnyErrors();
}
#endif
