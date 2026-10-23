#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraLiftAutomation.h"
#include "SoraRecoveryAutomation.h"
#include "SoraFrontEnd.h"
#include "SoraHorse.h"
#include "SoraSettings.h"

namespace SoraLeadFearTest
{
using FWorld=SoraFieldcraftAutomation::FBeatWorld;
bool Tick(FWorld& W,int32 Frames,float Dt=1.f/60.f)
{
    for(int32 Frame=0;Frame<Frames;++Frame)
    {
        SoraLiftAutomation::HoldThreats(*W.World);
        if(!W.Tick(1,Dt)) return false;
    }
    return true;
}
bool MenuAction(FWorld& W,SoraUI::EAction Action)
{
    auto* Menu=W.Mode()->FrontEnd();
    for(int32 Press=0;Press<12;++Press)
    {
        const auto& Rows=Menu->Rows();
        if(Rows.IsValidIndex(Menu->Focus())&&Rows[Menu->Focus()].Action==Action) return W.Press(EKeys::Enter);
        if(!W.Press(EKeys::Down)) return false;
    }
    return false;
}
bool Restart(FWorld& W)
{
    return W.Press(EKeys::Escape)&&MenuAction(W,SoraUI::EAction::Restart)&&
        MenuAction(W,SoraUI::EAction::ConfirmYes)&&Tick(W,30);
}
ASoraHorse* Bunta(FWorld& W) { return W.Campaign()->PackHorses().Num()==1?W.Campaign()->PackHorses()[0]:nullptr; }
void MoveThreat(ASoraEnemy& Enemy,const FVector& Point)
{
    Enemy.SetActorLocation(FVector(Point.X,Point.Y,Enemy.GetActorLocation().Z),false,nullptr,ETeleportType::TeleportPhysics);
}
void ThreatBehind(FWorld& W,ASoraEnemy& Enemy,float Distance)
{
    MoveThreat(Enemy,Bunta(W)->GetActorLocation()-W.Campaign()->Steed()->GetActorForwardVector()*Distance);
}
ASoraEnemy* StageThreat(FWorld& W)
{
    auto* C=W.Campaign(); auto* Horse=C->Steed(); auto* Pack=Bunta(W);
    if(!Horse||!Pack||!C->IsMounted()) return nullptr;
    const FVector Start=Horse->GetActorLocation(); const float Yaw=Horse->GetActorRotation().Yaw;
    const auto* Toll=C->ActiveSpace()->Volumes.FindByPredicate([](const FSoraVolume& V)
        { return V.Event==TEXT("volume_enter:vol_toll_post"); });
    if(!Toll) return nullptr;
    // Assisted setup: enter the real authored volume to release its registered
    // wave, freeze those opponents, then restore the horses to the start.
    // Only the hazard is repositioned during the control/timing checks. HP,
    // collision, damage, task progress and movement rules are unchanged.
    Horse->Place(FVector(Toll->Center,0),Yaw);
    if(!Tick(W,3)) return nullptr;
    ASoraEnemy* Drone=nullptr;
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
    {
        if(It->ArchetypeId()==TEXT("drone")) Drone=*It;
        MoveThreat(**It,Start+FVector(6000,6000,0));
    }
    Horse->Place(Start,Yaw);
    Pack->Place(Start-Horse->GetActorForwardVector()*300.f,Yaw);
    if(!Tick(W,180)||!W.Test.TestNotNull(TEXT("The actual toll wave supplies a cyan drone"),Drone)) return nullptr;
    W.Test.TestTrue(TEXT("The authored laden mare retains her identity and lead"),
        Pack->PackId==TEXT("pack_horse_cargo")&&Pack->IsLed()&&Pack->LeadFearMs()==0&&Horse->LeadTugMs()==0);
    return Drone;
}
bool FreshFear(FWorld& W,ASoraEnemy& Drone,float Dt)
{
    ThreatBehind(W,Drone,1600);
    if(!Tick(W,1,Dt)) return false;
    ThreatBehind(W,Drone,800);
    if(!Tick(W,1,Dt)) return false;
    auto* Horse=W.Campaign()->Steed(); auto* Pack=Bunta(W);
    return W.Test.TestTrue(TEXT("A Bunta-only cyan threat starts fresh authored clocks"),
        FVector::Dist2D(Drone.GetActorLocation(),Pack->GetActorLocation())<900&&
        FVector::Dist2D(Drone.GetActorLocation(),Horse->GetActorLocation())>900&&
        Pack->LeadFearMs()==2500&&Horse->LeadTugMs()==1000&&!Horse->IsSpooked());
}
bool Timing(FAutomationTestBase& Test,int32 Hz)
{
    FWorld W(Test,*FString::Printf(TEXT("BuntaLead%dHz"),Hz),3,13);
    if(!W.Start()||!Tick(W,30)) return false;
    auto* Drone=StageThreat(W); if(!Drone) return false;
    auto* Horse=W.Campaign()->Steed(); auto* Pack=Bunta(W);
    W.Mode()->Settings()->SetAutoSteer(true);
    const float Dt=1.f/Hz;
    // One centimetre outside avoids floating point rotation at the exact
    // authored boundary. Moving the source nearer affects only Bunta.
    ThreatBehind(W,*Drone,901);
    if(!Tick(W,2,Dt)) return false;
    Test.TestEqual(TEXT("A source beyond the fear radius cannot trigger it"),Pack->LeadFearMs(),0);
    if(!FreshFear(W,*Drone,Dt)||!W.World->InjectKey(EKeys::D,IE_Pressed)) return false;
    const float Yaw=Horse->GetActorRotation().Yaw;
    double Elapsed=0,SteeringRecovered=-1,FearRecovered=-1;
    for(int32 Frame=0;Frame<Hz*3;++Frame)
    {
        if(!Tick(W,1,Dt)) return false;
        Elapsed+=double(Dt);
        const bool Turned=FMath::Abs(FMath::FindDeltaAngleDegrees(Yaw,Horse->GetActorRotation().Yaw))>.05f;
        if(Elapsed<1.) Test.TestTrue(TEXT("Mapped steering cannot act during the full first active second"),!Turned&&Horse->LeadTugMs()>0);
        if(Turned&&SteeringRecovered<0)
        {
            SteeringRecovered=Elapsed;
            if(!W.World->InjectKey(EKeys::D,IE_Released)) return false;
        }
        if(Elapsed<2.5) Test.TestTrue(TEXT("Bunta cannot recover before her full active fear duration"),Pack->LeadFearMs()>0);
        if(Pack->LeadFearMs()==0&&FearRecovered<0) FearRecovered=Elapsed;
    }
    Test.TestTrue(TEXT("Steering resumes within one sampled frame plus clock quantization"),
        SteeringRecovered>=1.&&SteeringRecovered<=1.+double(Dt)+.001);
    Test.TestTrue(TEXT("Fear ends within one sampled frame plus clock quantization"),
        FearRecovered>=2.5&&FearRecovered<=2.5+double(Dt)+.001);
    Test.TestTrue(TEXT("Remaining beside the same threat cannot keep restarting either timer"),
        Horse->LeadTugMs()==0&&Pack->LeadFearMs()==0);
    Test.AddInfo(FString::Printf(TEXT("Bunta active clock hz=%d steering_recovered=%.9f fear_recovered=%.9f tolerance_frame=%.9f"),
        Hz,SteeringRecovered,FearRecovered,double(Dt)));
    // A separate assisted initial heading gives auto-steer real work to do.
    // Normal forward input then traverses with unchanged swept collision.
    const auto& Road=W.Campaign()->ActiveChapter()->Space.Zones[W.Campaign()->ActiveSpace()->Zone];
    const float OffHeading=Road.HeadingAt(Horse->RoadChainage())+20.f;
    Horse->Place(Horse->GetActorLocation(),OffHeading);
    Pack->Place(Horse->GetActorLocation()-Horse->GetActorForwardVector()*300.f,OffHeading);
    if(!FreshFear(W,*Drone,Dt)||!W.World->InjectKey(EKeys::W,IE_Pressed)||!Tick(W,Hz-1,Dt)) return false;
    Test.TestTrue(TEXT("The lead tug also blocks automatic steering during forward input"),
        Horse->LeadTugMs()>0&&FMath::Abs(FMath::FindDeltaAngleDegrees(OffHeading,Horse->GetActorRotation().Yaw))<.05f);
    if(!Tick(W,4,Dt)||!W.World->InjectKey(EKeys::W,IE_Released)) return false;
    Test.TestTrue(TEXT("Automatic road steering recovers after the full tug"),
        Horse->LeadTugMs()==0&&FMath::Abs(FMath::FindDeltaAngleDegrees(OffHeading,Horse->GetActorRotation().Yaw))>.1f);
    return !Test.HasAnyErrors();
}
bool Lifecycle(FAutomationTestBase& Test)
{
    FWorld W(Test,TEXT("BuntaLifecycle"),3,13);
    if(!W.Start()||!Tick(W,30)) return false;
    auto* Drone=StageThreat(W); if(!Drone) return false;
    auto* C=W.Campaign();auto* Horse=C->Steed();auto* Pack=Bunta(W);
    if(!FreshFear(W,*Drone,1.f/60.f)||!W.World->InjectKey(EKeys::D,IE_Pressed)||!Tick(W,12)||!W.Press(EKeys::Escape)) return false;
    const int32 Tug=Horse->LeadTugMs(),Fear=Pack->LeadFearMs();
    const FVector At=Horse->GetActorLocation(),PackAt=Pack->GetActorLocation();
    const float Yaw=Horse->GetActorRotation().Yaw;
    if(!Tick(W,240)||!W.World->InjectKeyPastFrontEnd(EKeys::D,IE_Released)) return false;
    Test.TestTrue(TEXT("The real pause menu freezes both clocks and both horses"),W.Mode()->bMenu&&
        Horse->LeadTugMs()==Tug&&Pack->LeadFearMs()==Fear&&Horse->GetActorLocation()==At&&
        Pack->GetActorLocation()==PackAt&&Horse->GetActorRotation().Yaw==Yaw);
    if(!W.Press(EKeys::Escape)||!W.Press(EKeys::E)) return false;
    Test.TestTrue(TEXT("Ordinary dismount clears the steering tug without dropping cargo"),
        !C->IsMounted()&&Horse->LeadTugMs()==0&&Pack->IsLed()&&C->TaskProgress().Done==0);
    ThreatBehind(W,*Drone,1600);
    if(!Tick(W,180)) return false;
    // Walk away normally, then whistle with Interact. Recall retains Bunta's
    // leader relationship, and never stores an interruption for remounting.
    const FVector Away=W.Hero()->GetActorLocation()+Horse->GetActorForwardVector()*650.f;
    if(!SoraRecoveryAutomation::WalkTo(*W.World,Away)||!W.Press(EKeys::E)||!Tick(W,190)) return false;
    Test.TestTrue(TEXT("The ordinary whistle recalls Kurimaru on foot with no banked tug"),
        !C->IsMounted()&&FVector::Dist2D(Horse->GetActorLocation(),W.Hero()->GetActorLocation())<220&&
        Horse->LeadTugMs()==0&&Pack->IsLed());
    if(!Tick(W,400)) return false;
    ThreatBehind(W,*Drone,800);
    if(!Tick(W,1)) return false;
    Test.TestTrue(TEXT("A fresh Bunta fear while on foot cannot bank a saddle interruption"),Pack->LeadFearMs()==2500&&Horse->LeadTugMs()==0);
    if(!W.Press(EKeys::E)) return false;
    Test.TestTrue(TEXT("Ordinary remount restores steering without a stale tug"),C->IsMounted()&&Horse->LeadTugMs()==0);
    if(!Restart(W)) return false;
    Test.TestTrue(TEXT("Checkpoint retry recreates a calm led mare and clear reins"),C->ActiveBeat()==13&&
        C->IsMounted()&&Bunta(W)&&Bunta(W)->LeadFearMs()==0&&C->Steed()->LeadTugMs()==0&&C->TaskProgress().Done==0);
    // Independent post-retry setup near Kami. Dismount outside the delivery
    // radius and walk in. Bunta need not be near the unloading hero: the
    // authored contract permits foot continuation and has no pack gate.
    const auto& Road=C->ActiveChapter()->Space.Zones[C->ActiveSpace()->Zone];
    const FVector2D Kami=C->ActiveSpace()->Dropoffs[0];
    const float Along=Road.ChainageOf(Kami);
    C->Steed()->Place(FVector(Road.PointAlong(Along-800),0),Road.HeadingAt(Along));
    if(!Tick(W,2)||!W.Press(EKeys::E)||!Test.TestFalse(TEXT("Interact away from Kami dismounts"),C->IsMounted())||
        !SoraRecoveryAutomation::WalkTo(*W.World,FVector(Kami,0))||!W.World->InjectKey(EKeys::E,IE_Pressed)||!Tick(W,185)||
        !W.World->InjectKey(EKeys::E,IE_Released)) return false;
    Test.TestTrue(TEXT("A complete ordinary hold still unloads once while on foot"),
        !C->IsMounted()&&C->TaskProgress().Done==1&&C->TaskProgress().DropoffUses[0]==1);
    return !Test.HasAnyErrors();
}
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraBuntaLeadFearTest,"SoraArena.Campaign.BuntaLeadFear",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraBuntaLeadFearTest::RunTest(const FString&)
{
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    const bool A=SoraLeadFearTest::Timing(*this,60),B=SoraLeadFearTest::Timing(*this,120),C=SoraLeadFearTest::Lifecycle(*this);
    if(A&&B&&C&&!HasAnyErrors()) UE_LOG(LogTemp,Display,TEXT("SORA_BUNTA_LEAD_OK: Bunta-only radius, 60/120Hz active timers, mapped steering, pause, dismount, whistle, retry, foot unloading"));
    return A&&B&&C&&!HasAnyErrors();
}
#endif
