#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraSummitAutomation.h"
#include "SoraBoss.h"
#include "Components/BoxComponent.h"
#include "GameFramework/DamageType.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraCampaignSpineTest,"SoraArena.Campaign.SpineDrawCut",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraCampaignSpineTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("SpineDrawCut"),7,13);
    if(!W.Start(0,INDEX_NONE,2)) return false;
    W.Harden();
    auto* Boss=const_cast<ASoraBoss*>(W.Campaign()->CampaignBoss());
    auto* Arena=W.Mode()->Arena();
    if(!TestNotNull(TEXT("The cane phase boss exists"),Boss)) return false;
    SoraLiftAutomation::HoldThreats(*W.World);
    // Setup only: ordinary mutō-dori is covered by Boss.ValAmort and the
    // combat trace. This fixture isolates post-defeat controls and traversal.
    UGameplayStatics::ApplyDamage(Boss,Boss->Health,W.Hero()->GetController(),W.Hero(),UDamageType::StaticClass());
    if(!W.Tick(2)) return false;
    TestTrue(TEXT("The take-alive outcome waits for the spine"),W.Campaign()->AwaitingCapture()&&W.Campaign()->IsCaptive(*Boss)&&Boss->GetLifeSpan()==0);
    FVector Objective;
    TestTrue(TEXT("The objective is the actual seam, not the captive's body"),W.Campaign()->ObjectiveAnchor(Objective)&&Objective.Equals(Arena->SummitSpinePoint(),1));
    const auto Place=[&](FVector At)
    {
        W.Hero()->SetBase(static_cast<FMovementBaseInterfaceData*>(nullptr));
        W.Hero()->GetCharacterMovement()->StopMovementImmediately();
        W.Hero()->SetActorLocation(At,false,nullptr,ETeleportType::TeleportPhysics);
        SoraSummitAutomation::FaceSpine(*W.World);
    };
    const FVector Approach=Arena->SummitSpineApproach();
    Place(Approach-FVector(0,0,1800)+FVector(0,0,90));
    W.Hero()->GetCharacterMovement()->DisableMovement();
    if(!W.Hold(EKeys::E,110)) return false;
    TestTrue(TEXT("Matching XY from the gallery floor cannot cut the spine"),W.Campaign()->AwaitingCapture());
    W.Hero()->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    Place(Approach+FVector(0,640,90));
    if(!W.Tick(2)) return false;
    TestFalse(TEXT("The far side of the solid spine blocks the seam"),Arena->CanReachSummitSpine(*W.Hero()));
    Place(Approach+FVector(0,-700,-30)); // Disc floor, south of the dais.
    if(!W.Tick(4)||!SoraSummitAutomation::ApproachSpine(*W.World)) return false;
    TestTrue(TEXT("Normal movement climbs to a reachable seam"),Arena->CanReachSummitSpine(*W.Hero()));
    if(!W.World->InjectKey(EKeys::E,IE_Pressed)||!W.Tick(45)) return false;
    TestTrue(TEXT("A partial hold shows progress without capture"),W.Campaign()->AwaitingCapture()&&W.Campaign()->HeldWorkProgress()>0);
    if(!W.World->InjectKey(EKeys::E,IE_Released)||!W.Tick(1)) return false;
    TestTrue(TEXT("Release discards partial work"),W.Campaign()->HeldWorkProgress()<0&&W.Campaign()->AwaitingCapture());
    if(!W.World->InjectKey(EKeys::E,IE_Pressed)||!W.Tick(20)) return false;
    W.Look(FRotator(0,-90,0));
    if(!W.Tick(100)) return false;
    SoraSummitAutomation::FaceSpine(*W.World);
    if(!W.Tick(100)) return false;
    TestTrue(TEXT("Looking away cancels; returning while held cannot restart"),W.Campaign()->AwaitingCapture()&&W.Campaign()->HeldWorkProgress()<0);
    if(!W.World->InjectKey(EKeys::E,IE_Released)||!W.Tick(1)||!W.World->InjectKey(EKeys::E,IE_Pressed)||!W.Tick(20)) return false;
    SoraFieldcraftAutomation::FBeatWorld::Hurt(*W.Hero(),10);
    if(!W.Tick(100)) return false;
    TestTrue(TEXT("Damage cancels the held cut"),W.Campaign()->AwaitingCapture()&&W.Campaign()->HeldWorkProgress()<0);
    if(!W.World->InjectKey(EKeys::E,IE_Released)||!W.Tick(90)) return false;
    auto* Wall=W.World->GetTestWorld()->SpawnActor<AActor>();
    auto* Box=NewObject<UBoxComponent>(Wall); Wall->SetRootComponent(Box); Box->SetBoxExtent(FVector(100,10,100));
    Box->SetCollisionProfileName(TEXT("BlockAll")); Box->RegisterComponent(); Wall->AddInstanceComponent(Box);
    Wall->SetActorLocation(Arena->SummitSpinePoint()+FVector(0,-59,30));
    TestFalse(TEXT("A real blocker prevents seam contact"),Arena->CanReachSummitSpine(*W.Hero()));
    if(!W.Hold(EKeys::E,100)) return false;
    TestTrue(TEXT("Held input through a wall does not cut"),W.Campaign()->AwaitingCapture());
    Wall->Destroy();
    if(!W.Tick(2)) return false;
    SoraSummitAutomation::FaceSpine(*W.World);
    if(!W.World->InjectKey(EKeys::E,IE_Pressed)||!W.Tick(84)) return false;
    TestTrue(TEXT("The full authored 1.5 seconds are required"),W.Campaign()->AwaitingCapture());
    auto* Before=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
    TestTrue(TEXT("Partial cut never saves a partial capture"),Before&&Before->CheckpointBeat==13&&Before->CheckpointPhase==2);
    if(!W.Tick(10)||!W.World->InjectKey(EKeys::E,IE_Released)) return false;
    TestEqual(TEXT("The held draw-cut starts the seals-dark cinematic"),W.Campaign()->ActiveBeat(),14);
    auto* After=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
    TestTrue(TEXT("Only the complete cut advances the checkpoint"),After&&After->CheckpointBeat==14&&After->CheckpointPhase==0);
    return !HasAnyErrors();
}
#endif
