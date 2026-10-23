#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraLiftAutomation.h"
#include "SoraRecoveryAutomation.h"
#include "SoraFrontEnd.h"
#include "SoraHorse.h"
#include "SoraLeadRopeComponent.h"
#include "SoraLeadRopeRules.h"
#include "Components/SceneComponent.h"
#include "SoraSettings.h"
#include "Combat/SoraCombatEffects.h"
#include "SoraGameEvents.h"
#include "Game/SoraCampaignReach.h"
#include "Misc/ScopeExit.h"

namespace SoraLeadFearTest
{
using FWorld=SoraFieldcraftAutomation::FBeatWorld;
bool RopeTracks(FWorld& W)
{
    if(W.Campaign()->ActiveBeat()!=13) return true;
    const auto Pack=W.Campaign()->PackHorses();
    if(!W.Test.TestTrue(TEXT("A cargo lead has its real horse pair"),Pack.Num()==1&&IsValid(Pack[0])&&IsValid(W.Campaign()->Steed()))) return false;
    const auto* Rope=Pack[0]->LeadRope();
    FVector Halter,Tie,ShownHalter,ShownTie;
    TInlineComponentArray<USceneComponent*> PackParts(Pack[0]),LeaderParts(W.Campaign()->Steed());
    USceneComponent* const* HalterPart=PackParts.FindByPredicate([](const USceneComponent* Part)
        { return Part->GetName().StartsWith(TEXT("LeadHalter")); });
    USceneComponent* const* TiePart=LeaderParts.FindByPredicate([](const USceneComponent* Part)
        { return Part->GetName().StartsWith(TEXT("LeadTie")); });
    return W.Test.TestTrue(TEXT("Late visual tick joins animated halter and tack with twelve collision-free segments"),
        Rope&&Rope->VisibleSegments()==SoraLeadRopeRules::Segments&&!Rope->HasCollision()&&
        Rope->PrimaryComponentTick.TickGroup==TG_PostUpdateWork&&Rope->Anchors(Halter,Tie)&&Rope->RenderedEndpoints(ShownHalter,ShownTie)&&
        HalterPart&&TiePart&&(*HalterPart)->GetAttachParent()&&(*HalterPart)->GetAttachParent()->GetName().StartsWith(TEXT("Head"))&&
        (*TiePart)->GetAttachParent()&&(*TiePart)->GetAttachParent()->GetName()==TEXT("Body")&&
        FVector::Dist(Halter,(*HalterPart)->GetComponentLocation())<.01&&FVector::Dist(Tie,(*TiePart)->GetComponentLocation())<.01&&
        FVector::Dist(Halter,ShownHalter)<.01&&FVector::Dist(Tie,ShownTie)<.01);
}
bool Tick(FWorld& W,int32 Frames,float Dt=1.f/60.f)
{
    for(int32 Frame=0;Frame<Frames;++Frame)
    {
        SoraLiftAutomation::HoldThreats(*W.World);
        if(!W.Tick(1,Dt)||!RopeTracks(W)) return false;
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
    // Pick the safest point inside the authored volume against every authored
    // spawn. The spook policy remains active while staging the actual wave.
    FVector2D At=Toll->Center;
    double Best=-1;
    for(const FVector2D Offset:{FVector2D(0,0),FVector2D(0,Toll->Size.Y*.3),FVector2D(0,-Toll->Size.Y*.3)})
    {
        const FVector2D Candidate=Toll->Center+Offset;
        double Nearest=MAX_dbl;
        for(const FVector2D& Spawn:C->ActiveSpace()->Spawns) Nearest=FMath::Min(Nearest,FVector2D::DistSquared(Candidate,Spawn));
        if(Nearest>Best) { Best=Nearest; At=Candidate; }
    }
    Horse->Place(FVector(At,0),Yaw);
    if(!Tick(W,3)) return nullptr;
    if(!W.Test.TestTrue(TEXT("Safe toll setup retains the rider with the authored spook policy active"),C->IsMounted())) return nullptr;
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
    FVector RopeHalter,RopeTie;
    if(!Test.TestTrue(TEXT("The paused lead has rendered endpoints"),Pack->LeadRope()->RenderedEndpoints(RopeHalter,RopeTie))) return false;
    const FVector At=Horse->GetActorLocation(),PackAt=Pack->GetActorLocation();
    // FRotator uses double precision. Narrowing this baseline to float makes
    // an exact comparison fail even when pause preserves the original yaw.
    const auto Yaw=Horse->GetActorRotation().Yaw;
    if(!Tick(W,240)||!W.World->InjectKeyPastFrontEnd(EKeys::D,IE_Released)) return false;
    Test.AddInfo(FString::Printf(TEXT("Bunta pause menu=%d tug=%d/%d fear=%d/%d horse_delta=%.17g pack_delta=%.17g yaw_before=%.17g yaw_after=%.17g"),
        W.Mode()->bMenu,Tug,Horse->LeadTugMs(),Fear,Pack->LeadFearMs(),
        FVector::Dist(At,Horse->GetActorLocation()),FVector::Dist(PackAt,Pack->GetActorLocation()),
        double(Yaw),double(Horse->GetActorRotation().Yaw)));
    Test.TestTrue(TEXT("The real pause menu remains open"),W.Mode()->bMenu);
    Test.TestEqual(TEXT("Pause freezes every remaining tug millisecond"),Horse->LeadTugMs(),Tug);
    Test.TestEqual(TEXT("Pause freezes every remaining fear millisecond"),Pack->LeadFearMs(),Fear);
    Test.TestTrue(TEXT("Pause exactly preserves Kurimaru's position"),Horse->GetActorLocation()==At);
    Test.TestTrue(TEXT("Pause exactly preserves Bunta's position"),Pack->GetActorLocation()==PackAt);
    Test.TestTrue(TEXT("Pause exactly preserves Kurimaru's full-precision yaw"),Horse->GetActorRotation().Yaw==Yaw);
    FVector PausedHalter,PausedTie;
    Test.TestTrue(TEXT("Pause preserves the actual rendered lead endpoints"),Pack->LeadRope()->RenderedEndpoints(PausedHalter,PausedTie)&&
        PausedHalter.Equals(RopeHalter,.01)&&PausedTie.Equals(RopeTie,.01));
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
    const TWeakObjectPtr<const USoraLeadRopeComponent> OldRope=Pack->LeadRope();
    if(!Restart(W)) return false;
    Test.TestTrue(TEXT("Retry destroys the previous lead presentation"),!OldRope.IsValid()||OldRope->VisibleSegments()==0);
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
    // Lifecycle API cleanup only, after the ordinary gameplay assertions.
    // Replacing or removing a lead must not leave independent rope meshes.
    auto* FreshPack=Bunta(W);
    FreshPack->Lead(nullptr,300);
    Test.TestTrue(TEXT("Removing a lead immediately destroys its rendered connection"),
        !FreshPack->IsLed()&&FreshPack->LeadRope()->VisibleSegments()==0&&!FreshPack->LeadRope()->IsComponentTickEnabled());
    FreshPack->Lead(C->Steed(),300,2500);
    if(!Tick(W,1)) return false;
    FreshPack->FollowRoad(nullptr,0,0);
    Test.TestTrue(TEXT("Switching from led to road-following removes the old rope"),
        !FreshPack->IsLed()&&FreshPack->LeadRope()->VisibleSegments()==0&&!FreshPack->LeadRope()->IsComponentTickEnabled());
    return !Test.HasAnyErrors();
}

bool OwnSpookLifecycle(FAutomationTestBase& Test,bool HorseFirst)
{
    FWorld W(Test,HorseFirst?TEXT("KurimaruHorseFirst"):TEXT("KurimaruDirectorFirst"),3,13);
    if(!W.Start()||!Tick(W,30)) return false;
    auto* Drone=StageThreat(W); if(!Drone) return false;
    auto* C=W.Campaign();auto* Horse=C->Steed();auto* Pack=Bunta(W);
    // Both legal tick orders must carry a once-only onset to the director.
    if(HorseFirst) C->AddTickPrerequisiteActor(Horse);
    else Horse->AddTickPrerequisiteComponent(C);
    float Damage=0;
    auto* Bus=USoraGameEvents::Get(W.Hero());
    const auto Handle=Bus->OnDamaged.AddLambda([&](const FSoraDamagedEvent& E) { if(E.Victim==W.Hero()) Damage+=E.Amount; });
    ON_SCOPE_EXIT { Bus->OnDamaged.Remove(Handle); };
    const float Health=W.Hero()->Health;
    MoveThreat(*Drone,Horse->GetActorLocation()+Horse->GetActorForwardVector()*800.f);
    if(!Test.TestTrue(TEXT("The controlled cyan source is inside Kurimaru's radius but outside Bunta's"),
        FVector::Dist2D(Drone->GetActorLocation(),Horse->GetActorLocation())<900&&
        FVector::Dist2D(Drone->GetActorLocation(),Pack->GetActorLocation())>900)) return false;
    for(int32 Frame=0;Frame<4&&C->IsMounted();++Frame) if(!Tick(W,1)) return false;
    Test.TestTrue(TEXT("Kurimaru's own spook dismounts without damage, retry or cargo loss"),
        !C->IsMounted()&&Horse->IsSpooked()&&Pack->LeadFearMs()==0&&Horse->LeadTugMs()==0&&
        W.Hero()->Health==Health&&Damage==0&&C->ActiveBeat()==13&&!W.Mode()->bDefeated&&C->TaskProgress().Done==0);
    // The rider is at the usual right flank. Remount during this same fear
    // must not replay the consumed onset or renew it every frame.
    if(!W.Press(EKeys::E)||!Tick(W,20)) return false;
    Test.TestTrue(TEXT("Remount during the same encounter cannot replay an old spook onset"),
        C->IsMounted()&&Horse->IsSpooked()&&W.Hero()->Health==Health&&Damage==0);
    if(!W.Press(EKeys::E)) return false;
    MoveThreat(*Drone,Horse->GetActorLocation()-Horse->GetActorForwardVector()*3000.f);
    const FVector Away=W.Hero()->GetActorLocation()+Horse->GetActorForwardVector()*650.f;
    if(!SoraRecoveryAutomation::WalkTo(*W.World,Away)||!Tick(W,180)) return false;
    const FVector BeforeRecall=Horse->GetActorLocation();
    const double WhistledAt=W.World->GetTestWorld()->GetTimeSeconds();
    if(!W.World->InjectKey(EKeys::E,IE_Pressed)||!W.World->InjectKey(EKeys::E,IE_Released)||!Tick(W,60)) return false;
    Test.TestTrue(TEXT("A whistle cannot return Kurimaru after only one second"),Horse->GetActorLocation()==BeforeRecall);
    if(!W.Press(EKeys::Escape)) return false;
    const double PausedAt=W.World->GetTestWorld()->GetTimeSeconds();
    if(!Tick(W,240)) return false;
    Test.TestTrue(TEXT("The real pause menu freezes the existing whistle deadline"),W.Mode()->bMenu&&
        W.World->GetTestWorld()->GetTimeSeconds()==PausedAt&&Horse->GetActorLocation()==BeforeRecall);
    if(!W.Press(EKeys::Escape)) return false;
    double ReturnedAfter=-1;
    for(int32 Frame=0;Frame<150;++Frame)
    {
        if(!Tick(W,1)) return false;
        const double Elapsed=W.World->GetTestWorld()->GetTimeSeconds()-WhistledAt;
        const bool Returned=FVector::Dist2D(Horse->GetActorLocation(),W.Hero()->GetActorLocation())<220;
        if(Elapsed<3.) Test.TestFalse(TEXT("Recall never completes before three active world seconds"),Returned);
        if(Returned) { ReturnedAfter=Elapsed; break; }
    }
    Test.TestTrue(TEXT("Recall arrives at three seconds within a frame and preserves the led pack"),
        ReturnedAfter>=3.&&ReturnedAfter<=3.+1./60.+.001&&!C->IsMounted()&&Pack->IsLed()&&Horse->LeadTugMs()==0);
    Test.AddInfo(FString::Printf(TEXT("Kurimaru recall horse_first=%d active_seconds=%.9f damage=%.1f"),HorseFirst,ReturnedAfter,Damage));
    if(!W.Press(EKeys::E)||!Tick(W,3)) return false;
    if(!Test.TestTrue(TEXT("Ordinary right-side remount works after recall"),C->IsMounted())) return false;
    // Queue another actual fear and retry at its boundary. Neither a queued
    // request nor a consumed onset can escape the old checkpoint lifecycle.
    MoveThreat(*Drone,Horse->GetActorLocation()+Horse->GetActorForwardVector()*800.f);
    if(!Tick(W,1)||!Restart(W)||!Tick(W,180)) return false;
    Test.TestTrue(TEXT("A fresh checkpoint clears spook onset, pending recall and cargo progress"),
        C->ActiveBeat()==13&&C->IsMounted()&&!C->Steed()->IsSpooked()&&C->Steed()->LeadTugMs()==0&&
        Bunta(W)&&Bunta(W)->LeadFearMs()==0&&C->TaskProgress().Done==0);
    // Now prove cargo continuation after an actual spook dismount. This
    // assisted setup is outside Kami's reach, then every footstep and unload
    // action is ordinary mapped input. Bunta proximity is not an unload gate.
    Drone=StageThreat(W); if(!Drone) return false;
    Horse=C->Steed();Pack=Bunta(W);
    const auto& Road=C->ActiveChapter()->Space.Zones[C->ActiveSpace()->Zone];
    const FVector2D Kami=C->ActiveSpace()->Dropoffs[0]; const float Along=Road.ChainageOf(Kami);
    Horse->Place(FVector(Road.PointAlong(Along-800),0),Road.HeadingAt(Along));
    Pack->Place(Horse->GetActorLocation()-Horse->GetActorForwardVector()*300.f,Horse->GetActorRotation().Yaw);
    MoveThreat(*Drone,Horse->GetActorLocation()+Horse->GetActorForwardVector()*800.f);
    for(int32 Frame=0;Frame<4&&C->IsMounted();++Frame) if(!Tick(W,1)) return false;
    if(!Test.TestFalse(TEXT("The unloading attempt starts from a real spook dismount"),C->IsMounted())) return false;
    MoveThreat(*Drone,Horse->GetActorLocation()-Horse->GetActorForwardVector()*3000.f);
    if(!SoraRecoveryAutomation::WalkTo(*W.World,FVector(Kami,0))||!W.World->InjectKey(EKeys::E,IE_Pressed)||
        !Tick(W,185)||!W.World->InjectKey(EKeys::E,IE_Released)) return false;
    Test.TestTrue(TEXT("Spook continuation permits the ordinary full foot unload with no spook damage"),
        !C->IsMounted()&&C->TaskProgress().Done==1&&C->TaskProgress().DropoffUses[0]==1&&Damage==0);
    return !Test.HasAnyErrors();
}
bool OwnSpookNetPriority(FAutomationTestBase& Test)
{
    FWorld W(Test,TEXT("KurimaruNetPriority"),3,13);
    if(!W.Start()||!Tick(W,30)) return false;
    auto* Drone=StageThreat(W);if(!Drone) return false;
    auto* C=W.Campaign();auto* Horse=C->Steed();
    C->AddTickPrerequisiteActor(Horse);
    MoveThreat(*Drone,Horse->GetActorLocation()+Horse->GetActorForwardVector()*800.f);
    // First director tick queues fear after the horse tick. The next horse
    // tick starts fear before the director sees both that onset and the net.
    if(!Tick(W,1)||!Test.TestTrue(TEXT("Fear is queued while still mounted"),C->IsMounted())) return false;
    const float Health=W.Hero()->Health;
    USoraCombatEffects::Get(W.Hero())->Root(*W.Hero(),1500);
    if(!Tick(W,1)) return false;
    Test.TestTrue(TEXT("A simultaneous net retains its existing thrown damage and foot continuation"),
        Horse->IsSpooked()&&!C->IsMounted()&&!W.Mode()->bDefeated&&
        FMath::IsNearlyEqual(Health-W.Hero()->Health,SoraCampaignReach::ThrownHp));
    return !Test.HasAnyErrors();
}
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraBuntaLeadFearTest,"SoraArena.Campaign.BuntaLeadFear",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraBuntaLeadFearTest::RunTest(const FString&)
{
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    const bool A=SoraLeadFearTest::Timing(*this,60),B=SoraLeadFearTest::Timing(*this,120),C=SoraLeadFearTest::Lifecycle(*this);
    if(A&&B&&C&&!HasAnyErrors()) UE_LOG(LogTemp,Display,TEXT("SORA_BUNTA_LEAD_OK: Bunta-only radius, 60/120Hz active timers, mapped steering, pause, dismount, whistle, retry, foot unloading; late rope endpoint tracking and cleanup"));
    return A&&B&&C&&!HasAnyErrors();
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraKurimaruSpookDismountTest,"SoraArena.Campaign.KurimaruSpookDismount",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraKurimaruSpookDismountTest::RunTest(const FString&)
{
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    const bool A=SoraLeadFearTest::OwnSpookLifecycle(*this,true),B=SoraLeadFearTest::OwnSpookLifecycle(*this,false),
        C=SoraLeadFearTest::OwnSpookNetPriority(*this);
    if(A&&B&&C&&!HasAnyErrors()) UE_LOG(LogTemp,Display,TEXT("SORA_KURIMARU_SPOOK_OK: both tick orders, one onset, no pure-spook damage, net priority, pause, 3s whistle, retry, foot cargo"));
    return A&&B&&C&&!HasAnyErrors();
}
#endif
