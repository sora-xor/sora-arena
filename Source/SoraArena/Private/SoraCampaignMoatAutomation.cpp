#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraMoatAutomation.h"
#include "SoraCatalogMoat.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameEvents.h"
#include "Dom/JsonObject.h"
#include "GameFramework/DamageType.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
namespace SoraMoatTest
{
using FWorld=SoraFieldcraftAutomation::FBeatWorld;
bool Start(FWorld& W,bool Harden=true)
{
    if(!FSoraCatalog::Get().Load()||!W.Start())return false;
    if(Harden)W.Harden();
    for(int32 F=0;F<600&&!W.Hero()->CanPlay();++F)if(!W.Tick(1))return false;
    return W.Tick(120)&&W.Hero()->CanPlay()&&W.Fieldcraft()->IsMoatSwimming();
}
void Sample(FWorld& W,const TCHAR* Stage)
{
    const auto* C=W.Fieldcraft();const FVector P=W.Hero()->GetActorLocation()-FVector(W.BeatData().Space.Moat.Origin,0);
    W.Test.AddInfo(FString::Printf(TEXT("SORA_MOAT: %s xyz=%s head_depth=%.3f swim=%d dive=%d gate=%d breath=%.5f radius=%.1f half=%.1f mode=%d hp=%.1f"),
        Stage,*P.ToString(),C->MoatDepth(),C->IsSwimming(),C->IsDiving(),C->MoatExitReady(),C->Readout(*W.Hero()).Breath,
        W.Hero()->GetCapsuleComponent()->GetScaledCapsuleRadius(),W.Hero()->GetCapsuleComponent()->GetScaledCapsuleHalfHeight(),
        int32(W.Hero()->GetCharacterMovement()->MovementMode),W.Hero()->Health));
}
void GuardSample(FWorld& W,const TCHAR* Stage)
{
    const FVector O(W.BeatData().Space.Moat.Origin,0);
    for(TActorIterator<ASoraEnemyController> I(W.World->GetTestWorld());I;++I)
        if(const auto* E=Cast<ASoraEnemy>(I->GetPawn());E&&W.Fieldcraft()->IsMoatGuard(*E))
            W.Test.AddInfo(FString::Printf(TEXT("SORA_MOAT_GUARD: %s time=%.3f actor=%s kind=%s xyz=%s known=%s state=%d sees=%d hunting=%d awareness=%d alive=%d radius=%.2f half=%.2f mode=%d velocity=%s"),
                Stage,W.World->GetTestWorld()->GetTimeSeconds(),*E->GetName(),*E->ArchetypeId().ToString(),
                *(E->GetActorLocation()-O).ToString(),*(I->LastKnownLocation()-O).ToString(),int32(I->State()),I->SeesHero(),I->IsHunting(),I->AwarenessPermille(),E->IsAlive(),
                E->GetCapsuleComponent()->GetScaledCapsuleRadius(),E->GetCapsuleComponent()->GetScaledCapsuleHalfHeight(),
                int32(E->GetCharacterMovement()->MovementMode),*E->GetVelocity().ToString()));
}
struct FSearchAudit
{
    struct FGuard { bool Detected=false,Completed=false;FName Previous;double SearchAt=0,SearchSeconds=0;int32 SearchFrames=0; };
    FWorld& W;TWeakObjectPtr<USoraGameEvents> Bus;FDelegateHandle Handle;TMap<FString,FGuard> Guards;
    explicit FSearchAudit(FWorld& World):W(World),Bus(USoraGameEvents::Get(World.Hero()))
    {
        if(Bus.IsValid())Handle=Bus->OnEnemyCue.AddLambda([this](const FSoraEnemyCueEvent& Event)
        {
            const auto* E=Cast<ASoraEnemy>(Event.Enemy);
            if(Event.Cue!=ESoraEnemyCue::AlertState||!E||!W.Fieldcraft()->IsMoatGuard(*E))return;
            FGuard& G=Guards.FindOrAdd(E->GetName());const double Now=W.World->GetTestWorld()->GetTimeSeconds();
            G.Detected|=Event.Detail==TEXT("alert")||Event.Detail==TEXT("combat");
            if(Event.Detail==TEXT("search"))G.SearchAt=Now;
            if(Event.Detail==TEXT("unaware")&&G.Previous==TEXT("search"))
            { G.Completed=true;G.SearchSeconds=Now-G.SearchAt;G.SearchFrames=FMath::RoundToInt32(G.SearchSeconds*60.); }
            W.Test.AddInfo(FString::Printf(TEXT("SORA_MOAT_SEARCH: actor=%s time=%.6f state=%s search_seconds=%.6f search_frames=%d"),
                *E->GetName(),Now,*Event.Detail.ToString(),G.Completed?Now-G.SearchAt:0.,G.SearchFrames));
            G.Previous=Event.Detail;
        });
    }
    ~FSearchAudit() { if(Bus.IsValid())Bus->OnEnemyCue.Remove(Handle); }
};
bool Walk(FWorld& W,const FVector& Local,bool Finish=false)
{
    const bool OK=SoraMoatAutomation::Swim(*W.World,FVector(W.BeatData().Space.Moat.Origin,0)+Local,Finish);
    if(!OK)Sample(W,TEXT("failed swim endpoint"));
    return W.Test.TestTrue(TEXT("Mapped swimming reaches the real route point"),OK);
}
bool Floor(FWorld& W,FVector Local,float Expected)
{
    const FVector O(W.BeatData().Space.Moat.Origin,0);FHitResult H;
    FCollisionQueryParams Q(SCENE_QUERY_STAT(MoatSupport),false,W.Hero());
    for(auto& A:W.Fieldcraft()->AlliesInPlay())if(IsValid(A))Q.AddIgnoredActor(A);
    const bool Hit=W.World->GetTestWorld()->LineTraceSingleByChannel(H,O+Local,O+Local-FVector(0,0,500),ECC_WorldStatic,Q);
    return W.Test.TestTrue(TEXT("Authored water has its actual deep supporting bed"),Hit&&!H.bStartPenetrating&&FMath::Abs(H.ImpactPoint.Z-Expected)<1);
}
bool Reload(FWorld& W)
{
    W.Fieldcraft()->OnEvent.Remove(W.EventsHandle);W.World->DestroyTestWorld(true);W.World->ForwardErrorMessages(&W.Test);W.World.Reset();
    W.World=MakeUnique<FSoraAutomationWorld>();
    if(!W.World->Start(W.Slot)||!W.Tick(1)||!W.World->EnableKeyInput())return false;
    for(int32 I=0;I<3;++I)if(!W.Press(EKeys::Enter))return false;
    return W.Tick(120)&&W.Campaign()->ActiveBeat()==1;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraMoatTraversal,"SoraArena.Campaign.MoatTraversal",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraMoatTraversal::RunTest(const FString&)
{
    SoraMoatTest::FWorld W(*this,TEXT("MoatTraversal"),5,1);if(!SoraMoatTest::Start(W))return false;
    auto* C=W.Fieldcraft();const FVector O(W.BeatData().Space.Moat.Origin,0);
    int32 Guards=0;for(TActorIterator<ASoraEnemy> I(W.World->GetTestWorld());I;++I)if(C->IsMoatGuard(**I)&&I->IsAlive())++Guards;
    TestEqual(TEXT("Both parapet sentries and the drone remain live"),Guards,3);
    SoraMoatTest::Floor(W,FVector(4000,1800,-20),-240);SoraMoatTest::Floor(W,FVector(20800,3400,-20),-300);
    SoraMoatTest::Floor(W,FVector(1000,-399,100),99.15f);SoraMoatTest::Floor(W,FVector(1000,-1,-200),-239.15f);
    const float Health=W.Hero()->Health;
    if(!TestTrue(TEXT("The entire moat route uses real swimming and breathing input"),SoraMoatAutomation::ToGate(*W.World)))return false;
    SoraMoatTest::Sample(W,TEXT("gate approach"));
    TestTrue(TEXT("Float clearance and recovery do not require drowning"),W.Hero()->Health==Health);
    TestFalse(TEXT("Crossing the float below 80cm is silent"),W.Raised(TEXT("ai_event:float_line")));
    TestFalse(TEXT("Approaching the gate does not grant passage"),C->MoatExitReady());
    W.Look(FRotator(0,90,0));if(!W.Hold(EKeys::W,180))return false;
    TestTrue(TEXT("The real lintel blocks a surfaced capsule"),W.Hero()->GetActorLocation().Y-O.Y<3560&&!C->MoatExitReady());
    if(!SoraMoatTest::Walk(W,FVector(20800,3400,0))||!SoraMoatAutomation::Recover(*W.World)||!SoraMoatAutomation::Posture(*W.World,true))return false;
    TestTrue(TEXT("The actual swimming body and fixed head fit the submerged opening"),C->MoatDepth()>130&&W.Hero()->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()==28);
    if(!SoraMoatTest::Walk(W,FVector(20800,3800,-150),true))return false;
    TestTrue(TEXT("Actual gate crossing reaches the next checkpoint and restores the ordinary capsule"),W.Campaign()->ActiveBeat()==2&&
        (W.Campaign()->Progress().CompletedMask&SoraBeatRules::BeatBit(1))!=0u&&W.Hero()->GetCapsuleComponent()->GetUnscaledCapsuleRadius()==34&&W.Hero()->GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight()==88);
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraMoatDepth,"SoraArena.Campaign.MoatDepth",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraMoatDepth::RunTest(const FString&)
{
    SoraMoatTest::FWorld W(*this,TEXT("MoatDepth"),5,1);if(!SoraMoatTest::Start(W))return false;
    auto* C=W.Fieldcraft();if(!SoraMoatTest::Walk(W,FVector(3000,200,0)))return false;
    TestTrue(TEXT("Surface swim is180cm/s, arms stowed and physical head above water"),FMath::IsNearlyEqual(C->HeroPace(),180.f)&&C->MoatDepth()<0&&C->ArmsStowed());
    if(!W.Press(SoraMoatAutomation::Key(*W.Hero(),TEXT("Crouch"),true)))return false;
    // Merely requesting a dive cannot grant the 1m hitscan exclusion.
    TestFalse(TEXT("A fresh dive wish cannot grant deep-water protection"),C->MoatBlocksHitscan());
    for(int32 F=0;F<240&&C->MoatDepth()<90;++F)if(!W.Tick(1))return false;
    TestTrue(TEXT("Head depth between80cm and1m clears a float but not hitscan"),C->MoatDepth()>80&&C->MoatDepth()<=100&&!C->MoatBlocksHitscan());
    for(int32 F=0;F<120&&C->MoatDepth()<131;++F)if(!W.Tick(1))return false;
    TestTrue(TEXT("Actual deeper immersion excludes hitscan and limits dive speed"),C->MoatBlocksHitscan()&&C->IsDiving()&&C->HeroPace()<=140);
    const float Depth=C->MoatDepth();W.Hero()->GetCamera()->AddLocalOffset(FVector(0,0,500));
    TestEqual(TEXT("Cosmetic camera motion cannot change authoritative head depth"),C->MoatDepth(),Depth);
    const float Hp=W.Hero()->Health;FHitResult H;H.Location=H.ImpactPoint=W.Hero()->GetActorLocation();
    ASoraEnemy* Shooter=nullptr;for(TActorIterator<ASoraEnemy> I(W.World->GetTestWorld());I;++I)if(I->IsAlive()){Shooter=*I;break;}
    if(!TestNotNull(TEXT("A real hostile damage source exists"),Shooter))return false;
    FSoraHit Round=FSoraHit::Ranged(Shooter->GetActorLocation(),INDEX_NONE);Round.bHitscan=true;
    SoraDamage::Strike(W.Hero(),10,Round,FVector::ForwardVector,H,Shooter->GetController(),Shooter);
    TestEqual(TEXT("The production defense rejects a traced round below1m"),W.Hero()->Health,Hp);
    SoraDamage::Strike(W.Hero(),10,FSoraHit::Hazard(H.Location),FVector::UpVector,H,nullptr,nullptr);
    TestTrue(TEXT("Deep-water protection cannot exclude hazards"),W.Hero()->Health<Hp);
    const float Before=W.Hero()->Health;if(!W.Tick(600))return false;
    TestTrue(TEXT("Eight-second air exhaustion applies real drowning damage"),W.Hero()->Health<Before);
    if(!SoraMoatAutomation::Posture(*W.World,false,true))return false;
    const float Partial=C->Readout(*W.Hero()).Breath;
    if(!W.Tick(60))return false;
    TestTrue(TEXT("One second of actual air is only partial recovery"),Partial<1&&C->Readout(*W.Hero()).Breath<1);
    if(!SoraMoatAutomation::Recover(*W.World))return false;
    TestTrue(TEXT("Actual surfacing restores breath and removes hitscan exclusion"),C->Readout(*W.Hero()).Breath==1&&!C->MoatBlocksHitscan());
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraMoatFloat,"SoraArena.Campaign.MoatFloat",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraMoatFloat::RunTest(const FString&)
{
    SoraMoatTest::FWorld W(*this,TEXT("MoatFloat"),5,1);if(!SoraMoatTest::Start(W)||!SoraMoatTest::Walk(W,FVector(3000,200,0))||!SoraMoatTest::Walk(W,FVector(12950,200,0)))return false;
    if(!SoraMoatTest::Walk(W,FVector(13200,200,0)))return false;
    TestTrue(TEXT("Actual surface contact rings the authored float line"),W.Raised(TEXT("ai_event:float_line")));
    const auto* C=W.Fieldcraft();const FVector At=W.Hero()->GetActorLocation();
    TestTrue(TEXT("Surface swimming uses500cm strokes instead of ordinary crouch silence"),C->MoatFootstepPermille(At)==1111);
    if(!SoraMoatAutomation::Posture(*W.World,true))return false;
    TestEqual(TEXT("Actual submerged strokes are silent"),C->MoatFootstepPermille(W.Hero()->GetActorLocation()),0);
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraMoatRetry,"SoraArena.Campaign.MoatPauseRetryReload",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraMoatRetry::RunTest(const FString&)
{
    SoraMoatTest::FWorld W(*this,TEXT("MoatRetry"),5,1);if(!SoraMoatTest::Start(W)||!SoraMoatTest::Walk(W,FVector(3000,200,0))||!SoraMoatAutomation::Posture(*W.World,true))return false;
    auto* C=W.Fieldcraft();if(!W.Press(EKeys::Escape))return false;
    const float Air=C->Readout(*W.Hero()).Breath;const FVector At=W.Hero()->GetActorLocation();
    if(!W.Tick(180))return false;
    TestTrue(TEXT("Pause freezes actual water movement and remaining air"),W.Hero()->GetActorLocation().Equals(At)&&C->Readout(*W.Hero()).Breath==Air);
    if(!W.Press(EKeys::Escape))return false;
    W.Hero()->Health=5;
    if(!W.Tick(720))return false;
    TestTrue(TEXT("Drowning reaches the real death state"),W.Mode()->bDefeated);
    if(!W.Press(EKeys::Enter)||!W.Tick(120))return false;
    TestTrue(TEXT("Retry restores surface posture, full breath and unearned gate state"),W.Campaign()->ActiveBeat()==1&&C->IsSwimming()&&!C->IsDiving()&&C->Readout(*W.Hero()).Breath==1&&!C->MoatExitReady());
    if(!SoraMoatTest::Reload(W))return false;C=W.Fieldcraft();
    TestTrue(TEXT("A fresh world cannot keep a dive or gate crossing"),C->IsSwimming()&&!C->IsDiving()&&!C->MoatExitReady()&&C->Readout(*W.Hero()).Breath==1);
    if(!SoraMoatTest::Walk(W,FVector(1000,-700,100))||!W.Tick(60))return false;
    TestTrue(TEXT("Ordinary bank ascent restores the original grounded capsule"),!C->IsSwimming()&&!C->IsMoatSwimming()&&W.Hero()->GetCharacterMovement()->IsMovingOnGround()&&W.Hero()->GetCapsuleComponent()->GetUnscaledCapsuleRadius()==34&&W.Hero()->GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight()==88);
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraMoatSenses,"SoraArena.Campaign.MoatSenses",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraMoatSenses::RunTest(const FString&)
{
    SoraMoatTest::FWorld W(*this,TEXT("MoatSenses"),5,1);if(!SoraMoatTest::Start(W))return false;
    SoraMoatTest::FSearchAudit Search(W);
    auto* C=W.Fieldcraft();const FVector O(W.BeatData().Space.Moat.Origin,0);
    const FVector Initial=C->SpotOf(0);
    // Seven degrees inside the left sweep endpoint, rather than the centre
    // crossing: the real spot remains on this open water through the reversal
    // for about2.09s (400cm radius,3000cm reach,14degrees/s). The centre and
    // exact endpoint expose a stationary head for only about1.09s per pass.
    const FVector Exposed(4592,2151,0);
    if(!SoraMoatTest::Walk(W,FVector(3000,200,0))||!SoraMoatTest::Walk(W,Exposed))return false;
    TestTrue(TEXT("The two authored lamps physically sweep the water"),C->LightCount()==2&&C->IsLightOn(0)&&C->IsLightOn(1)&&FVector::Dist2D(Initial,C->SpotOf(0))>100);
    // No frozen guards, moved lamps, injected detection or repositioning.
    int32 LitFrames=0,LongestLitFrames=0;
    for(int32 F=0;F<1800&&!W.Raised(TEXT("ai_event:searchlight_alert"));++F)
    {
        if(!W.Tick(1))return false;
        LitFrames=C->MoatHeadLit()?LitFrames+1:0;LongestLitFrames=FMath::Max(LongestLitFrames,LitFrames);
    }
    SoraMoatTest::Sample(W,TEXT("live searchlight detection"));
    AddInfo(FString::Printf(TEXT("SORA_MOAT: real lamp exposure longest_frames=%d suspicious=%d alert=%d"),
        LongestLitFrames,W.Raised(TEXT("ai_event:searchlight_suspicious")),W.Raised(TEXT("ai_event:searchlight_alert"))));
    TestTrue(TEXT("Real head exposure reaches both authored light thresholds"),W.Raised(TEXT("ai_event:searchlight_suspicious"))&&W.Raised(TEXT("ai_event:searchlight_alert"))&&W.Stealth()->IsDetected());
    TestTrue(TEXT("Actual traced searchlight exposure supplies the guard light-range input"),C->MoatHeadLit());
    SoraMoatTest::GuardSample(W,TEXT("alarm"));
    ASoraEnemy* Flight=nullptr;
    for(TActorIterator<ASoraEnemy> I(W.World->GetTestWorld());I;++I)
        if(C->IsMoatGuard(**I)&&I->ArchetypeId()==TEXT("drone")&&I->IsAlive())Flight=*I;
    double MaxFlightStep=0;
    for(int32 F=0;F<90;++F)
    {
        const FVector Before=Flight?Flight->GetActorLocation():FVector::ZeroVector;
        if(!W.Tick(1))return false;
        if(Flight)MaxFlightStep=FMath::Max(MaxFlightStep,FVector::Dist(Before,Flight->GetActorLocation()));
    }
    SoraMoatTest::GuardSample(W,TEXT("alarm plus90 frames"));
    int32 Rifle=0;ASoraEnemy* Drone=nullptr;
    for(TActorIterator<ASoraEnemy> I(W.World->GetTestWorld());I;++I)if(C->IsMoatGuard(**I)&&I->IsAlive())
    { if(I->ArchetypeId()==TEXT("drone"))Drone=*I;else ++Rifle; }
    TestEqual(TEXT("Detection adds two real parapet riflemen"),Rifle,4);
    if(!TestNotNull(TEXT("The living figure-eight drone remains"),Drone))return false;
    TestTrue(TEXT("Alarm physically descends the drone to3m"),FMath::Abs(Drone->GetActorLocation().Z-300)<5);
    TestTrue(TEXT("Alarm descent shares the original300cm/s swept flight budget"),MaxFlightStep<=300.f/60.f+UE_KINDA_SMALL_NUMBER);
    const FVector Seen=W.Hero()->GetActorLocation();
    TestTrue(TEXT("Both lamps lock the actual detection position"),FVector::Dist2D(C->SpotOf(0),Seen)<30&&FVector::Dist2D(C->SpotOf(1),Seen)<30);
    // Leave the locked400cm spot underwater, then surface in real open air
    // before the8s breath budget expires and swim beneath the nearby lotus.
    if(!SoraMoatAutomation::Posture(*W.World,true)||!SoraMoatTest::Walk(W,FVector(Exposed.X,1700,-150))||
        !SoraMoatAutomation::Posture(*W.World,false)||!SoraMoatTest::Walk(W,FVector(Exposed.X,1300,0)))return false;
    TestTrue(TEXT("Surfacing beneath real lotus cover hides the head and restores air"),!C->IsDiving()&&C->HeroExposure(1000)==0);
    TestFalse(TEXT("Cover cannot retain the searchlight range bonus"),C->MoatHeadLit());
    SoraMoatTest::GuardSample(W,TEXT("lotus arrival"));
    // Search itself is20s; a remote parapet guard first walks to its
    // reachable investigation point. Keep that physical travel in the test.
    for(int32 I=0;I<6;++I)
    {
        if(!W.Tick(600))return false;
        SoraMoatTest::GuardSample(W,*FString::Printf(TEXT("lotus plus%d frames"),(I+1)*600));
    }
    bool AnySeeing=false,AnyCombat=false,AllUnaware=true;
    for(TActorIterator<ASoraEnemyController> I(W.World->GetTestWorld());I;++I)
        if(const auto* E=Cast<ASoraEnemy>(I->GetPawn());E&&C->IsMoatGuard(*E))
        { AnySeeing|=I->SeesHero();AnyCombat|=I->State()==SoraStealthRules::EState::Combat||I->State()==SoraStealthRules::EState::Alert;
          AllUnaware&=I->State()==SoraStealthRules::EState::Unaware; }
    TestTrue(TEXT("Actual cover and20s search end the live pursuit"),!AnySeeing&&!AnyCombat&&C->Readout(*W.Hero()).Breath==1);
    TestTrue(TEXT("Investigation arrivals also let unconfirmed suspicion decay"),AllUnaware);
    // Measure real state cues against authored active time. A state change
    // may land on the next frame; millisecond carry may differ by <1ms at
    // entry. Neither allows the former cumulative per-frame rounding drift.
    const int32 SearchMs=W.Stealth()->Vigilance().SearchDurationMs;
    const double SearchSeconds=SearchMs/1000.;
    int32 CompletedSearches=0;
    for(const auto& Pair:Search.Guards)if(Pair.Value.Detected)
    {
        const auto& G=Pair.Value;
        TestTrue(*FString::Printf(TEXT("Detected guard %s physically arrives and finishes its timed search"),*Pair.Key),G.Completed);
        if(G.Completed)
        {
            ++CompletedSearches;
            TestTrue(*FString::Printf(TEXT("Guard %s searches for the active vigilance timer"),*Pair.Key),
                G.SearchSeconds>=SearchSeconds-.001&&G.SearchSeconds<=SearchSeconds+1./60.+.001);
        }
    }
    TestTrue(TEXT("The alarm produces observed completed guard searches"),CompletedSearches>0);
    AddInfo(FString::Printf(TEXT("SORA_MOAT_SEARCH: timer_ms=%d authored_seconds=%.6f completed=%d max_flight_step_cm=%.6f"),
        SearchMs,SearchSeconds,CompletedSearches,MaxFlightStep));
    // An actual wall blocks a ray from the water to the lower terrace.
    FHitResult Hit;FCollisionQueryParams Q(SCENE_QUERY_STAT(MoatWallSight),false,W.Hero());
    TestTrue(TEXT("Stone occludes a water-level line of sight"),W.World->GetTestWorld()->LineTraceSingleByChannel(Hit,O+FVector(10000,3400,20),O+FVector(10000,4000,20),ECC_Visibility,Q));
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraMoatGuide,"SoraArena.Campaign.MoatGuide",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraMoatGuide::RunTest(const FString&)
{
    SoraMoatTest::FWorld W(*this,TEXT("MoatGuide"),5,1);if(!SoraMoatTest::Start(W))return false;
    auto* C=W.Fieldcraft();ASoraCompanion* Guide=nullptr;
    for(auto& A:C->AlliesInPlay())if(IsValid(A)&&A->CompanionId()==TEXT("npc_kohagi"))Guide=A;
    if(!TestNotNull(TEXT("Kohagi exists as a real companion"),Guide))return false;
    const FVector O(W.BeatData().Space.Moat.Origin,0);FVector Last=Guide->GetActorLocation();
    bool DivedAtFloat=false;float MaxStep=0;
    for(int32 F=0;F<12000&&FVector::Dist(Guide->GetActorLocation(),O+FVector(20800,3350,-6))>3;++F)
    {
        if(!W.Tick(1))return false;
        const FVector Now=Guide->GetActorLocation();MaxStep=FMath::Max(MaxStep,FVector::Dist(Last,Now));Last=Now;
        const FVector Local=Now-O;if(Local.X>13000&&Local.X<13400&&Local.Z<-140)DivedAtFloat=true;
    }
    TestTrue(TEXT("Kohagi leads by bounded swept swimming and dives under the float"),DivedAtFloat&&MaxStep<=140.f/60.f+.2f);
    TestTrue(TEXT("Kohagi waits physically outside the old gate"),FVector::Dist(Guide->GetActorLocation(),O+FVector(20800,3350,-6))<3);
    TestFalse(TEXT("The companion's route cannot grant player gate credit"),C->MoatExitReady());
    const FVector Wait=Guide->GetActorLocation();if(!W.Tick(180))return false;
    TestTrue(TEXT("The gate wait is stable without relocating the player"),Guide->GetActorLocation().Equals(Wait,.1f));
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraMoatLoader,"SoraArena.Campaign.MoatLoader",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraMoatLoader::RunTest(const FString&)
{
    if(!FSoraCatalog::Get().Load())return false;
    FString Text;if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("Data/campaign/chapter_06.json"))))return false;
    TSharedPtr<FJsonObject> Root;const auto Reader=TJsonReaderFactory<>::Create(Text);
    if(!FJsonSerializer::Deserialize(Reader,Root))return false;
    auto Row=Root->GetObjectField(TEXT("space"))->GetArrayField(TEXT("beats"))[1]->AsObject();
    const auto& Chapter=FSoraCatalog::Get().Chapter(5);FSoraBeat B=Chapter.Beats[1];
    TestTrue(TEXT("The production typed reader accepts the exact physical moat"),SoraCatalogMoat::Read(*Row,B,Chapter.Space));
    auto Data=Row->GetObjectField(TEXT("moat"));Data->SetNumberField(TEXT("float_clear_depth_cm"),0);
    TestFalse(TEXT("A dropped float-depth contract is rejected"),SoraCatalogMoat::Read(*Row,B,Chapter.Space));
    Data->SetNumberField(TEXT("float_clear_depth_cm"),80);Data->SetNumberField(TEXT("gate_top_cm"),0);
    TestFalse(TEXT("The gate cannot be silently enlarged to the surface"),SoraCatalogMoat::Read(*Row,B,Chapter.Space));
    Data->SetNumberField(TEXT("gate_top_cm"),-120);Data->SetBoolField(TEXT("hitscan_clear_depth_cm"),true);
    TestFalse(TEXT("A boolean cannot impersonate a depth"),SoraCatalogMoat::Read(*Row,B,Chapter.Space));
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraMoatHands,"SoraArena.Campaign.MoatHands",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraMoatHands::RunTest(const FString&)
{
    SoraMoatTest::FWorld W(*this,TEXT("MoatHands"),5,1);if(!SoraMoatTest::Start(W))return false;
    // Only this equipment fixture holds combat to isolate actual held-draw
    // cancellation. MoatTraversal and MoatSenses retain every living guard.
    SoraLiftAutomation::HoldThreats(*W.World);
    if(!SoraMoatTest::Walk(W,FVector(1000,-700,100))||!W.Tick(60))return false;
    auto* C=W.Fieldcraft();auto* Kit=W.Hero()->GetEquipment();
    TestFalse(TEXT("The real bank frees the arms"),C->ArmsStowed());
    if(!W.Press(SoraMoatAutomation::Key(*W.Hero(),TEXT("WeaponThree")))||!W.Tick(30))return false;
    if(!TestEqual(TEXT("Mapped selection equips the unlocked bow on land"),W.Hero()->WeaponId,18))return false;
    const FKey Fire=SoraMoatAutomation::Key(*W.Hero(),TEXT("Fire"));const int32 Ammo=Kit->Ammo;
    if(!W.World->InjectKey(Fire,IE_Pressed)||!W.Tick(50)||!TestTrue(TEXT("The land draw is really held"),Kit->IsBowDrawing()))return false;
    if(!SoraMoatTest::Walk(W,FVector(1000,200,0))||!W.World->InjectKey(Fire,IE_Released)||!W.Tick(2))return false;
    TestTrue(TEXT("Water admission cancels the held draw through production equipment semantics"),C->ArmsStowed()&&!Kit->IsBowDrawing()&&!Kit->IsTriggerHeld()&&Kit->Ammo==Ammo);
    if(!W.Hold(Fire,90)||!W.Press(SoraMoatAutomation::Key(*W.Hero(),TEXT("WeaponOne"))))return false;
    TestTrue(TEXT("New fire and weapon selection remain refused while swimming"),!Kit->IsBowDrawing()&&Kit->Ammo==Ammo&&W.Hero()->WeaponId==18);
    if(!SoraMoatTest::Walk(W,FVector(1000,-700,100))||!W.Tick(60)||!W.Hold(Fire,50))return false;
    TestEqual(TEXT("The same mapped bow fires normally after ordinary bank exit"),Kit->Ammo,Ammo-1);
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraMoatGateRetry,"SoraArena.Campaign.MoatGateRetry",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraMoatGateRetry::RunTest(const FString&)
{
    SoraMoatTest::FWorld W(*this,TEXT("MoatGateRetry"),5,1);if(!SoraMoatTest::Start(W)||!SoraMoatAutomation::ToGate(*W.World)||!SoraMoatAutomation::Recover(*W.World)||!SoraMoatAutomation::Posture(*W.World,true))return false;
    if(!SoraMoatTest::Walk(W,FVector(20800,3590,-150)))return false;
    auto* C=W.Fieldcraft();const float Air=C->Readout(*W.Hero()).Breath;
    if(!W.Press(SoraMoatAutomation::Key(*W.Hero(),TEXT("Jump")))||!W.Tick(90))return false;
    SoraMoatTest::Sample(W,TEXT("ascend refused under gate lintel"));
    TestTrue(TEXT("A surface wish under actual stone cannot create air or expand into it"),C->IsDiving()&&C->MoatDepth()>125&&C->Readout(*W.Hero()).Breath<Air&&
        W.Hero()->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()==28&&!C->MoatExitReady());
    W.Hero()->Health=5;if(!W.Tick(600))return false;
    TestTrue(TEXT("Drowning under the real gate reaches defeat"),W.Mode()->bDefeated);
    if(!W.Press(EKeys::Enter)||!W.Tick(120))return false;
    TestTrue(TEXT("Gate death retry restores a surface swimmer at the real entry"),W.Campaign()->ActiveBeat()==1&&!W.Mode()->bDefeated&&!C->IsDiving()&&!C->MoatExitReady()&&C->Readout(*W.Hero()).Breath==1&&
        FVector::Dist2D(W.Hero()->GetActorLocation(),FVector(W.BeatData().Space.Entry,0))<30);
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraMoatPatrols,"SoraArena.Campaign.MoatPatrols",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraMoatPatrols::RunTest(const FString&)
{
    SoraMoatTest::FWorld W(*this,TEXT("MoatPatrols"),5,1);if(!SoraMoatTest::Start(W))return false;
    auto* C=W.Fieldcraft();const FVector O(W.BeatData().Space.Moat.Origin,0);
    TArray<TWeakObjectPtr<ASoraEnemy>> Guards;
    for(TActorIterator<ASoraEnemy> I(W.World->GetTestWorld());I;++I)
        if(C->IsMoatGuard(**I)&&I->ArchetypeId()==TEXT("enforcer_rifle"))Guards.Add(*I);
    if(!TestEqual(TEXT("Two real rifle patrols are staged"),Guards.Num(),2))return false;
    float MaxA=0,MaxB=0;
    for(int32 F=0;F<2700;++F)
    {
        if(!W.Tick(1))return false;
        for(auto& G:Guards)if(G.IsValid())
        {
            const FVector P=G->GetActorLocation()-O;
            if(P.X<10500)MaxA=FMath::Max(MaxA,float(P.X));else MaxB=FMath::Max(MaxB,float(P.X));
        }
    }
    TestTrue(TEXT("Parapet A physically passes its searchlight support"),MaxA>6500);
    TestTrue(TEXT("Parapet B physically passes its searchlight support"),MaxB>15500);
    TestTrue(TEXT("Starting reed cover keeps the live patrol experiment undetected"),!W.Stealth()->IsDetected()&&C->HeroExposure(1000)==0);
    return !HasAnyErrors();
}
#endif
