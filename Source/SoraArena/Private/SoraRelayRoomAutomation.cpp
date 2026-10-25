#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"

namespace SoraRelayAutomation
{
using SoraFieldcraftAutomation::FBeatWorld;
FVector Feet(const ASoraCharacterBase& Body)
{ return Body.GetActorLocation()-FVector(0,0,Body.GetCapsuleComponent()->GetScaledCapsuleHalfHeight()); }
void Place(FBeatWorld& W,const FVector& At)
{
    W.Hero()->GetCharacterMovement()->StopMovementImmediately();
    W.Hero()->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    W.Hero()->SetActorLocation(At+FVector(0,0,W.Hero()->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2),false,nullptr,ETeleportType::TeleportPhysics);
}
bool Dialogue(FBeatWorld& W)
{
    for(int I=0;I<1800&&W.Campaign()->IsDialogueBlocking();++I) if(!W.Tick(1)) return false;
    return W.Test.TestFalse(TEXT("Authored relay dialogue releases control"),W.Campaign()->IsDialogueBlocking());
}
void FreezeGuards(FBeatWorld& W)
{
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
    {
        It->SetActorTickEnabled(false);It->SetActorEnableCollision(false);
        It->GetCharacterMovement()->StopMovementImmediately();It->GetCharacterMovement()->SetComponentTickEnabled(false);
        It->SetActorLocation(FVector(W.BeatData().Space.Entry+FVector2D(0,8000),90));
        if(auto* Brain=Cast<ASoraEnemyController>(It->GetController()))
        { Brain->BeginPatrol(FSoraPatrolRoute{});Brain->SetActorTickEnabled(false); }
    }
}
bool Ready(FBeatWorld& W,int Node,int Minimum=3300,int Maximum=4000)
{
    if(!Dialogue(W)) return false;
    for(int I=0;I<3000;++I)
    {
        const auto& S=W.Campaign()->RelayState();const int Safe=S.SafeRemainingMs(Node);
        if(S.NodesLockedMs==0&&Safe>=Minimum&&Safe<=Maximum) return true;
        if(!W.Tick(1)) return false;
    }
    return W.Test.TestTrue(TEXT("The scan reaches the required real-time gap"),false);
}
AActor* Block(FBeatWorld& W,const FVector& At,const FVector& Half)
{
    auto* Actor=W.World->GetTestWorld()->SpawnActor<AActor>();if(!Actor) return nullptr;
    auto* Box=NewObject<UBoxComponent>(Actor);Actor->SetRootComponent(Box);Actor->AddInstanceComponent(Box);
    Box->SetBoxExtent(Half);Box->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    Box->SetCollisionResponseToAllChannels(ECR_Block);Box->RegisterComponent();Actor->SetActorLocation(At);return Actor;
}
bool Pull(FBeatWorld& W,int Node)
{
    Place(W,W.Campaign()->RelayWorkLocation(Node));
    if(!W.Tick(3)||!Ready(W,Node)||!W.Hold(EKeys::G,185)) return false;
    return W.Test.TestTrue(TEXT("The mapped hold pulls its node"),W.Campaign()->RelayState().IsDisabled(Node));
}
int Hunters(FBeatWorld& W)
{
    int Count=0;
    for(TActorIterator<ASoraEnemyController> It(W.World->GetTestWorld());It;++It)
        if(auto* Enemy=Cast<ASoraEnemy>(It->GetPawn());Enemy&&Enemy->IsAlive()&&!It->IsGuard()) ++Count;
    return Count;
}
bool Walk(FBeatWorld& W,float Yaw,TFunctionRef<bool()> Arrived,int Limit=600)
{
    W.Look(FRotator(0,Yaw,0));if(!W.World->InjectKey(EKeys::W,IE_Pressed)) return false;
    bool Good=true;for(int I=0;I<Limit&&!Arrived()&&Good;++I) Good=W.Tick(1);
    W.World->InjectKey(EKeys::W,IE_Released);
    return Good&&W.Test.TestTrue(TEXT("Ordinary mapped movement reaches the relay waypoint"),Arrived())&&W.Tick(3);
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraRelayControlsTest,"SoraArena.Campaign.RelayControls",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraRelayControlsTest::RunTest(const FString& Parameters)
{
    (void)Parameters;using namespace SoraRelayAutomation;
    if(!FSoraCatalog::Get().Load()) return false;
    FBeatWorld W(*this,TEXT("RelayControls"),5,3);if(!W.Start()) return false;
    W.Harden();FreezeGuards(W);auto* C=W.Campaign();
    if(!Dialogue(W)||!W.Press(EKeys::Escape)) return false;
    const int Phase=C->RelayState().PhaseMs;
    if(!W.Tick(120)) return false;
    TestEqual(TEXT("Pause freezes the scan"),C->RelayState().PhaseMs,Phase);
    if(!W.Hero()->RemapCombatAction(TEXT("Interact"),EKeys::G)||!W.Press(EKeys::Escape)) return false;
    Place(W,C->RelayWorkLocation(1));
    if(!W.Tick(3)||!Ready(W,1)||!W.Hold(EKeys::E,185)) return false;
    TestEqual(TEXT("The former input binding cannot pull a node"),C->RelayState().Disabled,0u);
    if(!Ready(W,1)||!W.Hold(EKeys::G,90)) return false;
    TestTrue(TEXT("Releasing a partial hold discards it"),C->RelayState().HeldNode==-1&&C->RelayState().Disabled==0);
    if(!Ready(W,1)||!W.World->InjectKey(EKeys::G,IE_Pressed)||!W.Tick(60)) return false;
    auto* Wall=Block(W,C->RelayNodeLocation(1)+FVector(50,0,30),FVector(5,90,120));
    if(!TestNotNull(TEXT("The control obstruction spawns"),Wall)||!W.Tick(10)) return false;
    TestEqual(TEXT("An obstruction cancels ongoing work"),C->RelayState().HeldNode,-1);
    Wall->Destroy();
    if(!W.Tick(200)||!W.World->InjectKey(EKeys::G,IE_Released)) return false;
    TestEqual(TEXT("Clearing the obstruction cannot resume without a fresh press"),C->RelayState().Disabled,0u);
    Place(W,FVector(C->RelayWorkLocation(2).X,C->RelayWorkLocation(2).Y,0));
    if(!W.Tick(3)||!W.Hold(EKeys::G,185)) return false;
    TestFalse(TEXT("The upper node cannot be worked from the floor"),C->RelayState().IsDisabled(2));
    if(!Pull(W,1)) return false;
    FBeatWorld::Hurt(*W.Hero(),W.Hero()->Health+1000.f);
    if(!W.Tick(2)||!TestTrue(TEXT("Death ends the relay attempt"),W.Mode()->bDefeated)||!W.Press(EKeys::Enter)) return false;
    TestTrue(TEXT("Checkpoint retry resets nodes, locks and inspection"),C->ActiveBeat()==3&&C->RelayState().Disabled==0&&
        !C->RelayState().Detected&&C->RelayState().NodesLockedMs==0&&!W.Fieldcraft()->RelayInspectionArrived(1));
    AddInfo(TEXT("Directed control fixture with guard AI frozen and explicit placement. Ordinary stealth, art and performance remain separate."));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraRelayScanTest,"SoraArena.Campaign.RelayScan",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraRelayScanTest::RunTest(const FString& Parameters)
{
    (void)Parameters;using namespace SoraRelayAutomation;
    if(!FSoraCatalog::Get().Load()) return false;
    FBeatWorld W(*this,TEXT("RelayScan"),5,3);if(!W.Start()) return false;
    W.Harden();FreezeGuards(W);auto* C=W.Campaign();
    if(!Dialogue(W)||!W.Hero()->RemapCombatAction(TEXT("Interact"),EKeys::G)) return false;
    Place(W,C->RelayWorkLocation(1));if(!W.Tick(3)) return false;
    FSoraPatrolRoute Route;Route.Points={C->RelayWorkLocation(1)+FVector(300,0,90)};
    FSoraEnemyTuning Tune;Tune.SightCm=1;Tune.DarkSightCm=0;Tune.HearingCm=0;
    auto* Guard=ASoraEnemy::SpawnArchetype(*W.World->GetTestWorld(),TEXT("enforcer_rifle"),0,Route.Points[0],FRotator::ZeroRotator,&Route,&Tune);
    auto* Brain=Guard?Cast<ASoraEnemyController>(Guard->GetController()):nullptr;
    if(!TestNotNull(TEXT("The sensor witness spawns"),Brain)) return false;
    Brain->SetActorTickEnabled(false);Guard->SetActorTickEnabled(false);Guard->GetCharacterMovement()->SetComponentTickEnabled(false);
    if(!Ready(W,1,1000,1500)||!W.World->InjectKey(EKeys::G,IE_Pressed)) return false;
    for(int I=0;I<120&&C->RelayState().HeldNode>=0;++I) if(!W.Tick(1)) return false;
    W.World->InjectKey(EKeys::G,IE_Released);
    TestEqual(TEXT("The scan adds exactly 0.6 suspicion to the witness"),Brain->AwarenessPermille(),600);
    TestTrue(TEXT("An incomplete pull is caught and the fan freezes"),!C->RelayState().IsDisabled(1)&&C->RelayState().FanLockedMs>1900);
    const int Phase=C->RelayState().PhaseMs;
    for(int I=0;I<180&&C->RelayState().FanLockedMs>0;++I)
    {
        if(!W.Tick(1)) return false;
        if(C->RelayState().FanLockedMs>0) TestEqual(TEXT("The frozen scan keeps its heading"),C->RelayState().PhaseMs,Phase);
    }
    if(!Dialogue(W)) return false;
    Brain->SensorEvidence(W.Hero()->GetActorLocation(),400);
    TestTrue(TEXT("Full evidence triggers detection and the 30 s lock"),C->RelayState().Detected&&C->RelayState().NodesLockedMs==30000);
    TestEqual(TEXT("Detection does not spawn reinforcements immediately"),Hunters(W),0);
    if(!Dialogue(W)) return false;
    for(int I=0;I<600&&!C->RelayState().ReinforcementsReady();++I)
    {
        TestEqual(TEXT("No reinforcements before the eight-second deadline"),Hunters(W),0);
        if(!W.Tick(1)) return false;
    }
    if(!W.Tick(2)) return false;
    TestEqual(TEXT("Exactly two hunters enter after eight seconds"),Hunters(W),2);
    TestTrue(TEXT("Nodes remain locked after reinforcements enter"),C->RelayState().NodesLockedMs>21000&&C->RelayState().NodesLockedMs<23000);
    FreezeGuards(W);
    for(int I=0;I<1500&&C->RelayState().NodesLockedMs>0;++I) if(!W.Tick(1)) return false;
    TestEqual(TEXT("The lock expires at thirty active seconds"),C->RelayState().NodesLockedMs,0);
    AddInfo(TEXT("Sensor evidence and delayed-spawn fixture. The witness AI is frozen to isolate the exact impulse; timing core has separate exhaustive host tests."));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraRelayGalleryTest,"SoraArena.Campaign.RelayGallery",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraRelayGalleryTest::RunTest(const FString& Parameters)
{
    (void)Parameters;using namespace SoraRelayAutomation;
    if(!FSoraCatalog::Get().Load()) return false;
    FBeatWorld W(*this,TEXT("RelayGallery"),5,3);if(!W.Start()) return false;
    W.Harden();FreezeGuards(W);auto* C=W.Campaign();const FVector O(W.BeatData().Space.RelayRoom.Origin,0);
    if(!Dialogue(W)||!W.Hero()->RemapCombatAction(TEXT("Interact"),EKeys::G)) return false;
    Place(W,O+FVector(75,850,0));if(!W.Tick(3)) return false;
    if(!Walk(W,0,[&]{return Feet(*W.Hero()).Z>=399&&W.Hero()->GetActorLocation().X>=O.X+520;})) return false;
    if(!Walk(W,0,[&]{return W.Hero()->GetActorLocation().X>=O.X+1000;})) return false;
    if(!Walk(W,-90,[&]{return W.Hero()->GetActorLocation().Y<=O.Y+695;})) return false;
    TestTrue(TEXT("The real stair and north approach reach the upper control"),C->CanReachRelay(2)&&FMath::Abs(Feet(*W.Hero()).Z-400)<5);
    if(!Ready(W,2)||!W.Hold(EKeys::G,185)) return false;
    TestTrue(TEXT("A three-second hold from the traversed gallery disables the upper node"),C->RelayState().IsDisabled(2));
    if(!Walk(W,90,[&]{return W.Hero()->GetActorLocation().Y>=O.Y+850;})) return false;
    if(!Walk(W,180,[&]{return W.Hero()->GetActorLocation().X<=O.X+75;})) return false;
    TestTrue(TEXT("Ordinary movement descends the stair to the floor"),Feet(*W.Hero()).Z<25);
    AddInfo(TEXT("Only the starting foot position is placed. Stair ascent, gallery approach and descent use ordinary W movement with frozen guards; visual quality and ordinary encounter difficulty remain open."));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraRelayInspectionTest,"SoraArena.Campaign.RelayInspection",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraRelayInspectionTest::RunTest(const FString& Parameters)
{
    (void)Parameters;using namespace SoraRelayAutomation;
    if(!FSoraCatalog::Get().Load()) return false;
    FBeatWorld W(*this,TEXT("RelayInspection"),5,3);if(!W.Start()) return false;
    W.Harden();FreezeGuards(W);auto* C=W.Campaign();auto* Craft=W.Fieldcraft();
    // Frozen original guards are taken out of the inspection candidate pool.
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It) if(It->ArchetypeId()==TEXT("auditor")) It->Destroy();
    if(!Dialogue(W)||!W.Hero()->RemapCombatAction(TEXT("Interact"),EKeys::G)||!Pull(W,2)) return false;
    const FVector O(W.BeatData().Space.RelayRoom.Origin,0);FSoraPatrolRoute Route;
    Route.Points={O+FVector(300,500,90)};Route.bThreeDimensional=true;
    FSoraEnemyTuning Tune;Tune.SightCm=1;Tune.DarkSightCm=0;Tune.HearingCm=0;
    auto* Auditor=ASoraEnemy::SpawnArchetype(*W.World->GetTestWorld(),TEXT("auditor"),0,Route.Points[0],FRotator::ZeroRotator,&Route,&Tune);
    if(!TestNotNull(TEXT("The inspector spawns"),Auditor)) return false;
    Place(W,O+FVector(1800,100,0));
    auto* Wall=Block(W,O+FVector(1000,690,500),FVector(50,50,100));
    if(!Wall||!W.Tick(1800)) return false;
    TestFalse(TEXT("A blocked node cannot be marked inspected by elapsed time"),Craft->RelayInspectionArrived(2));
    TestTrue(TEXT("The actual auditor is assigned to the upper node"),Craft->RelayInspector()==Auditor);
    Wall->Destroy();
    for(int I=0;I<2400&&!Craft->RelayInspectionArrived(2);++I) if(!W.Tick(1)) return false;
    TestTrue(TEXT("The auditor physically reaches the upper node after the route opens"),
        Craft->RelayInspectionArrived(2)&&FVector::Dist(Feet(*Auditor),C->RelayWorkLocation(2))<50);
    AddInfo(TEXT("Directed real-navigation fixture with a deaf, nearly blind auditor. Path obstruction, floor height and arrival are checked; ordinary detection remains separate."));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraRelayExitTest,"SoraArena.Campaign.RelayExit",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraRelayExitTest::RunTest(const FString& Parameters)
{
    (void)Parameters;using namespace SoraRelayAutomation;
    if(!FSoraCatalog::Get().Load()) return false;
    FBeatWorld W(*this,TEXT("RelayExit"),5,3);if(!W.Start()) return false;
    W.Harden();FreezeGuards(W);auto* C=W.Campaign();
    if(!Dialogue(W)||!W.Hero()->RemapCombatAction(TEXT("Interact"),EKeys::G)) return false;
    const FVector Exit=C->RelayWorkLocation(3);
    Place(W,Exit);if(!W.Tick(3)||!W.Press(EKeys::G)) return false;
    TestTrue(TEXT("The east door cannot complete before the three nodes"),C->ActiveBeat()==3&&!C->RelayOffline());
    for(int Node=0;Node<3;++Node) if(!Pull(W,Node)) return false;
    if(!Dialogue(W)) return false;
    // Height-qualified work cannot be banked from a point above the exit.
    Place(W,Exit+FVector(0,0,400));
    if(!W.World->InjectKey(EKeys::G,IE_Pressed)||!W.World->InjectKey(EKeys::G,IE_Released)) return false;
    TestEqual(TEXT("The exit must be reached on its own floor"),C->ActiveBeat(),3);
    Place(W,Exit);if(!W.Tick(3)||!W.Press(EKeys::G)||!W.Tick(2)) return false;
    TestTrue(TEXT("Three nodes and the floor exit restore the relay site"),C->ActiveBeat()>3&&C->RelayOffline()&&(C->Progress().SitesMask&1u)!=0);
    const auto* Saved=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
    TestTrue(TEXT("The completed relay survives in the next checkpoint"),Saved&&(Saved->CheckpointBeatsMask&(1u<<3))!=0);
    AddInfo(TEXT("Directed completion and save fixture with explicit node placement and frozen guards. Stair movement is exercised separately."));
    return true;
}
#endif
