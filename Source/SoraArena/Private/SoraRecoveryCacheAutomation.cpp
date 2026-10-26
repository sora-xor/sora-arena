#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraCampaignRules.h"
#include "SoraWorldBuilder.h"
#include "SoraTenementFindRules.h"
#include "SoraLiftAutomation.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraRecoveryCacheTest,"SoraArena.Campaign.RecoveryCache",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraRecoveryCacheTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    for(int First:{0,1})
    {
        SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("RecoveryCache"),2,4);
        if(!W.Start()) return false;
        const auto Settle=[&]()
        {
            W.Harden();
            for(int Frame=0;Frame<1800;++Frame)
            {
                SoraLiftAutomation::HoldThreats(*W.World);
                if(W.Hero()->CanPlay())return W.Tick(30);
                if(!W.Tick(1))return false;
            }
            return TestTrue(TEXT("Carry intro releases player input"),false);
        };
        if(!Settle())return false;
        auto* Campaign=W.Campaign();
        const auto& Chapter=FSoraCatalog::Get().Chapter(2);
        const int32 Cache=Chapter.BeatIndex(TEXT("ch03.b04"));
        TestTrue(TEXT("Equipment recovery is pending beside optional exploration"),Campaign->NeedsEquipmentRecovery());
        TestFalse(TEXT("No combined b04 cache is offered or marked"),Campaign->AvailableCaches().Contains(Cache));
        const auto Aim=[&](int I)
        {
            const auto P=SoraTenementFindRules::Points[I];
            W.Hero()->GetCharacterMovement()->StopMovementImmediately();
            W.Hero()->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
            W.Hero()->SetActorLocation(FVector(-2800,P.Y+45,W.Hero()->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2.15),
                false,nullptr,ETeleportType::TeleportPhysics);
            W.LookAt(FVector(P.X,P.Y,P.Z));
        };
        Aim(First);if(!W.Tick(4))return false;
        bool HeardPoi=false;
        for(int Frame=0;Frame<1200&&!HeardPoi;++Frame)
        {
            const auto* Cue=Campaign->CurrentDialogueCue();
            HeardPoi=Cue&&(First==0?Cue->Id.StartsWith(TEXT("ch03.b04.child.")):Cue->Id==TEXT("ch03.b04.nyaakoto.007"));
            SoraLiftAutomation::HoldThreats(*W.World);
            if(!HeardPoi&&!W.Tick(1))return false;
        }
        TestTrue(TEXT("The optional POI dialogue plays beside the active carry task"),HeardPoi);
        W.Look(FRotator(0,First==0?0:180,0));
        if(!W.Press(EKeys::E))return false;
        TestEqual(TEXT("Looking away cannot inspect a nearby find"),Campaign->CollectedMask(),uint64(0));
        Aim(First);
        const auto P=SoraTenementFindRules::Points[First];
        auto* Obstacle=W.World->GetTestWorld()->SpawnActor<AActor>();
        if(!TestNotNull(TEXT("The sightline obstacle spawns"),Obstacle))return false;
        auto* Block=NewObject<UBoxComponent>(Obstacle);Obstacle->SetRootComponent(Block);
        Block->InitBoxExtent(FVector(10,70,100));Block->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
        Block->SetCollisionResponseToAllChannels(ECR_Ignore);Block->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
        Block->RegisterComponent();Block->SetWorldLocation((W.Hero()->GetCamera()->GetComponentLocation()+FVector(P.X,P.Y,P.Z))*.5);
        if(!W.Press(EKeys::E))return false;
        TestEqual(TEXT("An intervening wall prevents the find"),Campaign->CollectedMask(),uint64(0));
        Obstacle->Destroy();
        W.Hero()->SetActorLocation(W.Hero()->GetActorLocation()+FVector(0,0,300),false,nullptr,ETeleportType::TeleportPhysics);
        W.LookAt(FVector(P.X,P.Y,P.Z));
        if(!W.Press(EKeys::E))return false;
        TestEqual(TEXT("The floor above cannot claim the find"),Campaign->CollectedMask(),uint64(0));
        Aim(First);if(!W.Tick(4))return false;
        FKey Use=EKeys::E;
        if(First==0)
        {
            if(!W.Press(EKeys::Escape)||!W.Hero()->RemapCombatAction(TEXT("Interact"),EKeys::G)||!W.Press(EKeys::G))return false;
            TestEqual(TEXT("Menu input cannot inspect"),Campaign->CollectedMask(),uint64(0));
            W.Mode()->ResumePlay();Use=EKeys::G;
            if(!W.Tick(3)||!W.Press(EKeys::E))return false;
            TestEqual(TEXT("The old binding cannot inspect"),Campaign->CollectedMask(),uint64(0));
        }
        if(!W.Press(Use))return false;
        const uint64 FirstBit=SoraCampaignRules::CollectibleBit(2,First);
        TestEqual(TEXT("The first physical find awards only itself"),Campaign->CollectedMask(),FirstBit);
        TestEqual(TEXT("One find does not complete the optional beat"),Campaign->Progress().CompletedMask&SoraBeatRules::BeatBit(Cache),0u);
        auto* Saved=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
        if(!TestNotNull(TEXT("First find is immediately saved"),Saved))return false;
        TestEqual(TEXT("Disk preserves the partial discovery"),uint64(Saved->Collectibles),FirstBit);
        if(!W.Press(Use))return false;
        TestEqual(TEXT("Repeated input does not claim its neighbour"),Campaign->CollectedMask(),FirstBit);
        if(First==0)
        {
            W.Fieldcraft()->OnEvent.Remove(W.EventsHandle);
            if(!W.World->DestroyTestWorld(true))return false;
            W.World->ForwardErrorMessages(this);W.World.Reset();W.EventsHandle.Reset();
            W.World=MakeUnique<FSoraAutomationWorld>();
            if(!W.World->Start(W.Slot)||!W.Tick(1)||!W.World->EnableKeyInput()||
               !W.Press(EKeys::Enter)||!W.Press(EKeys::Enter)||!W.Press(EKeys::Enter)||!Settle())return false;
            Campaign=W.Campaign();
            TestEqual(TEXT("A new world preserves only the first find"),Campaign->CollectedMask(),FirstBit);
            TestTrue(TEXT("Reload still requires the weapon bundle"),Campaign->NeedsEquipmentRecovery());
        }
        Aim(1-First);if(!W.Tick(4)||!W.Press(Use))return false;
        const uint64 Both=SoraCampaignRules::CollectibleBit(2,0)|SoraCampaignRules::CollectibleBit(2,1);
        TestEqual(TEXT("Both orders independently discover both finds"),Campaign->CollectedMask(),Both);
        TestTrue(TEXT("Only the second discovery completes exploration"),
            (Campaign->Progress().CompletedMask&SoraBeatRules::BeatBit(Cache))!=0u);
        TestEqual(TEXT("The carry objective remains active"),Campaign->ActiveBeat(),4);
        TestTrue(TEXT("Reading both finds does not recover the hidden weapons"),Campaign->NeedsEquipmentRecovery());
        TestFalse(TEXT("The katana remains unavailable"),Campaign->CanHold(0,false));
        const auto* Space=Campaign->ActiveSpace();
        if(!TestTrue(TEXT("The guarded hoist has its pickup"),Space&&!Space->Pickups.IsEmpty())) return false;
        W.Stand(ASoraWorldBuilder::Floor(Space->Pickups[0]));
        if(!W.World->InjectKey(Use,IE_Pressed)||!W.Tick(240)||
            !W.World->InjectKey(Use,IE_Released)) return false;
        TestFalse(TEXT("Holding the hoist before retrieval takes no load"),Campaign->TaskProgress().Carrying);
        TestEqual(TEXT("No recovery requirement or delivery is bypassed"),Campaign->TaskProgress().Done,0);
        TestTrue(TEXT("Equipment recovery is still mandatory"),Campaign->NeedsEquipmentRecovery());
    }
    AddInfo(TEXT("Fixture uses controlled placement and held threats; mapped interaction and save isolation are covered, not ordinary traversal or final art."));
    return true;
}
#endif
