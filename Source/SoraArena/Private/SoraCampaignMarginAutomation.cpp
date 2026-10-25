#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraLiftAutomation.h"
#include "SoraBoss.h"
#include "SoraMarginRules.h"
#include "Combat/SoraBossCatalog.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/DamageType.h"
#include "World/SoraNavigation.h"

namespace SoraMarginTest
{
using SoraFieldcraftAutomation::FBeatWorld;
ASoraBoss* Boss(FBeatWorld& W) { return const_cast<ASoraBoss*>(W.Campaign()->CampaignBoss()); }
void Freeze(FBeatWorld& W)
{
    if(auto* Body=Boss(W))
    {
        Body->SetActorTickEnabled(false);
        if(auto* Brain=Body->GetController()) Brain->SetActorTickEnabled(false);
        Body->GetCharacterMovement()->StopMovementImmediately();
    }
}
bool Start(FBeatWorld& W)
{
    if(!FSoraCatalog::Get().Load()||!W.Start(0,INDEX_NONE,1)) return false;
    W.Harden(); Freeze(W); return W.Tick(90)&&W.Mode()->Arena()->BridgeConsoles().Num()==15;
}
// Use actual game time and bounded steps; a large single UWorld tick is
// clamped by WorldSettings and cannot prove a warning boundary.
bool Until(FBeatWorld& W,double Time)
{
    for(int32 Frame=0;Frame<2000&&W.World->GetTestWorld()->GetTimeSeconds()<Time;++Frame)
    {
        const double Remaining=Time-W.World->GetTestWorld()->GetTimeSeconds();
        if(!W.Tick(1,FMath::Clamp(float(Remaining),.001f,.02f))) return false;
    }
    return W.World->GetTestWorld()->GetTimeSeconds()>=Time;
}
bool Seconds(FBeatWorld& W,double Time) { return Until(W,W.World->GetTestWorld()->GetTimeSeconds()+Time); }
FHitResult TraceCover(FBeatWorld& W,const TCHAR* Stage)
{
    auto* Arena=W.Mode()->Arena(); auto* Hero=W.Hero(); auto* Body=Boss(W);
    auto* Cover=Arena->BridgeConsoles()[2].Get();
    const FTransform Deck=Arena->BridgeDeckRoot()->GetComponentTransform();
    const FHitResult Hit=Body->RangedAimTrace(*Hero);
    const int32 HitId=Arena->BridgeConsoles().IndexOfByPredicate(
        [&](const auto& Console) { return Console.Get()==Hit.GetComponent(); });
    const FVector Feet=Hero->GetActorLocation()-FVector(0,0,Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
    W.Test.AddInfo(FString::Printf(TEXT("MarginLinger %s: input=%d playing=%d crouched=%d wants_crouch=%d grounded=%d base=%s hero_world=(%s) hero_local=(%s) feet_local=(%s) half_height=%.3f boss_world=(%s) boss_local=(%s)"),
        Stage,int32(W.Mode()->InputState()),W.Mode()->IsPlaying(),Hero->IsCrouched(),Hero->GetCharacterMovement()->bWantsToCrouch,
        Hero->GetCharacterMovement()->IsMovingOnGround(),*GetNameSafe(Hero->GetMovementBase()),*Hero->GetActorLocation().ToString(),
        *Deck.InverseTransformPosition(Hero->GetActorLocation()).ToString(),*Deck.InverseTransformPosition(Feet).ToString(),
        Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight(),*Body->GetActorLocation().ToString(),
        *Deck.InverseTransformPosition(Body->GetActorLocation()).ToString()));
    W.Test.AddInfo(FString::Printf(TEXT("MarginLinger %s trace: start=(%s) end=(%s) start_local=(%s) end_local=(%s) blocking=%d penetrating=%d actor=%s component=%s console_id=%d impact_local=(%s) cover=%s cover_local=(%s) cover_bounds_origin=(%s) cover_bounds_extent=(%s) cover_transform=(%s) deck_transform=(%s)"),
        Stage,*Hit.TraceStart.ToString(),*Hit.TraceEnd.ToString(),*Deck.InverseTransformPosition(Hit.TraceStart).ToString(),
        *Deck.InverseTransformPosition(Hit.TraceEnd).ToString(),Hit.bBlockingHit,Hit.bStartPenetrating,*GetNameSafe(Hit.GetActor()),
        *GetNameSafe(Hit.GetComponent()),HitId,*Deck.InverseTransformPosition(Hit.ImpactPoint).ToString(),*Cover->GetName(),
        *Cover->GetRelativeLocation().ToString(),*Cover->Bounds.Origin.ToString(),*Cover->Bounds.BoxExtent.ToString(),
        *Cover->GetComponentTransform().ToString(),*Deck.ToString()));
    return Hit;
}
bool Reload(FBeatWorld& W)
{
    W.Fieldcraft()->OnEvent.Remove(W.EventsHandle);
    W.World->DestroyTestWorld(true); W.World->ForwardErrorMessages(&W.Test); W.World.Reset();
    W.World=MakeUnique<FSoraAutomationWorld>();
    if(!W.World->Start(W.Slot)||!W.Tick(1)||!W.World->EnableKeyInput()) return false;
    for(int N=0;N<3&&!W.Mode()->IsPlaying();++N) if(!W.Press(EKeys::Enter)) return false;
    W.EventsHandle=W.Fieldcraft()->OnEvent.AddLambda([&W](FName Event) { W.Events.Add(Event.ToString()); });
    W.Harden(); Freeze(W); return W.Tick(90)&&W.Mode()->IsPlaying();
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraMarginCoverTest,"SoraArena.Campaign.MarginCover",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraMarginCoverTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    SoraMarginTest::FBeatWorld W(*this,TEXT("MarginCover"),6,12);
    if(!SoraMarginTest::Start(W)) return false;
    auto* Arena=W.Mode()->Arena(); auto* Boss=SoraMarginTest::Boss(W);
    const int32 Attack=Boss->Data()->AttackIndex(TEXT("margin_call")),Warning=Boss->WindupFor(Attack);
    const float Health=W.Hero()->Health;
    int32 Serial=9000;
    for(int32 Wave=0;Wave<6;++Wave)
    {
        if(!TestTrue(TEXT("Production margin accepts a unique wave"),Arena->BeginBridgeMargin(*Boss,Attack,++Serial))) return false;
        const auto Targets=Arena->MarginTargetIds();
        TSet<int32> Unique; TArray<int32> Hits;
        for(int Id:Targets) { Unique.Add(Id); Hits.Add(Arena->MarginConsoleHits(Id)); }
        TestTrue(TEXT("Each windup selects three distinct real consoles"),Targets.Num()==3&&Unique.Num()==3&&!Unique.Contains(INDEX_NONE));
        const double Started=W.World->GetTestWorld()->GetTimeSeconds();
        if(!SoraMarginTest::Until(W,Started+(Warning-2)/1000.0)) return false;
        for(int N=0;N<Targets.Num();++N) TestEqual(TEXT("Cover takes no hit during its warning"),Arena->MarginConsoleHits(Targets[N]),Hits[N]);
        if(!W.Tick(1,.019f)) return false;
        TestTrue(TEXT("The actual sample crossed beyond the narrow deadline"),W.World->GetTestWorld()->GetTimeSeconds()>Started+(Warning+1)/1000.0);
        TestEqual(TEXT("Dodging the marked consoles avoids damage"),W.Hero()->Health,Health);
        const int ExpectedLost=Wave<2?(Wave==0?0:3):Wave==2?3:6;
        TestEqual(TEXT("Two strikes destroy a batch, then the sixth loss reinforces survivors"),Arena->MarginDestroyedCount(),ExpectedLost);
        int32 Live=0;
        for(int Id=0;Id<Arena->BridgeConsoles().Num();++Id)
        {
            auto* Console=Arena->BridgeConsoles()[Id].Get();
            if(Console->IsCollisionEnabled()) ++Live;
            else
            {
                TestFalse(TEXT("Destroyed cover leaves navigation"),Console->CanEverAffectNavigation());
                TestFalse(TEXT("Destroyed cover is not still shown intact"),Console->IsVisible());
                const FVector Side=Arena->BridgeDeckRoot()->GetForwardVector()*180;
                FHitResult Ray; FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraMarginGone),false,W.Hero());
                W.World->GetTestWorld()->LineTraceSingleByChannel(Ray,Console->GetComponentLocation()+Side,Console->GetComponentLocation()-Side,ECC_Visibility,Query);
                TestTrue(TEXT("The destroyed physical body no longer blocks a ray"),Ray.GetComponent()!=Console);
            }
        }
        TestEqual(TEXT("Visible gameplay cover never falls below nine survivors"),Live,15-ExpectedLost);
        if(!SoraMarginTest::Seconds(W,.25)) return false;
        TestFalse(TEXT("The released wave cleans up"),Arena->MarginIsPending());
        TestFalse(TEXT("A replayed serial cannot re-release cover or damage"),Arena->BeginBridgeMargin(*Boss,Attack,Serial));
    }
    TestEqual(TEXT("A forced seventh loss remains impossible after extra complete strikes"),Arena->MarginDestroyedCount(),6);
    if(!Arena->BeginBridgeMargin(*Boss,Attack,++Serial)||!W.Press(EKeys::Escape)) return false;
    if(!W.Tick(180)) return false;
    TestTrue(TEXT("Pause preserves the pending warning without release"),Arena->MarginIsPending()&&Arena->MarginDestroyedCount()==6);
    W.Mode()->ResumePlay();
    if(!SoraMarginTest::Seconds(W,Warning/1000.0+.25)||!SoraMarginTest::Reload(W)) return false;
    Arena=W.Mode()->Arena(); Boss=SoraMarginTest::Boss(W);
    TestTrue(TEXT("Reload reconstructs canonical phase-two cover, with no stale wave"),Boss&&Boss->PhaseIndex()==1&&Arena->MarginDestroyedCount()==0&&!Arena->MarginIsPending());
    for(UStaticMeshComponent* Console:Arena->BridgeConsoles()) TestTrue(TEXT("Reload restores fifteen physical consoles"),Console->IsCollisionEnabled());
    UGameplayStatics::ApplyDamage(W.Hero(),W.Hero()->Health+1,nullptr,nullptr,UDamageType::StaticClass());
    if(!W.Tick(2)||!TestTrue(TEXT("Normal defeat offers retry"),W.Mode()->bDefeated)||!W.Press(EKeys::Enter)) return false;
    SoraMarginTest::Freeze(W); if(!W.Tick(90)) return false;
    Arena=W.Mode()->Arena(); Boss=SoraMarginTest::Boss(W);
    TestTrue(TEXT("Retry clears cover loss and pending attack state"),Arena->MarginDestroyedCount()==0&&!Arena->MarginIsPending());
    // Leave the actual concurrent scheduler live while holding ordinary
    // attack intent. This tests the authored clock, not a fixture timer.
    Boss->Hold(60000); Boss->SetActorTickEnabled(true);
    double First=-1,Second=-1; bool Pending=Arena->MarginIsPending();
    for(int32 Frame=0;Frame<1200&&Second<0;++Frame)
    {
        if(!W.Tick(1)) return false;
        const bool Now=Arena->MarginIsPending();
        if(Now&&!Pending)
        { if(First<0) First=W.World->GetTestWorld()->GetTimeSeconds(); else Second=W.World->GetTestWorld()->GetTimeSeconds(); }
        Pending=Now;
    }
    TestTrue(TEXT("Production concurrent scheduler starts margin calls seven seconds apart"),First>=0&&Second>First&&FMath::Abs(Second-First-7)<.05);
    if(!SoraMarginTest::Seconds(W,Warning/1000.0+.25)) return false;
    SoraMarginTest::Freeze(W);
    const int32 LostBeforePhase=Arena->MarginDestroyedCount();
    if(!Arena->BeginBridgeMargin(*Boss,Attack,10001)) return false;
    Boss->Health=Boss->MaxHealth*.3f; Boss->SetActorTickEnabled(true);
    if(!W.Tick(3)) return false;
    TestTrue(TEXT("Phase three cancels a pending call and preserves existing cover losses"),Boss->PhaseIndex()==2&&!Arena->MarginIsPending()&&Arena->MarginDestroyedCount()==LostBeforePhase);
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraMarginLingerTest,"SoraArena.Campaign.MarginLinger",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraMarginLingerTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    SoraMarginTest::FBeatWorld W(*this,TEXT("MarginLinger"),6,12);
    if(!SoraMarginTest::Start(W)) return false;
    auto* Arena=W.Mode()->Arena(); auto* Boss=SoraMarginTest::Boss(W);
    const auto Local=[&](FVector Point) { return Arena->BridgeDeckRoot()->GetComponentTransform().TransformPosition(Point); };
    // Approach the middle of console 2 through clear floor, using mapped W.
    // Walk allows a 30 cm stopping band. The old (-1154,-394) destination
    // put the nominal deck-plane ray only about 12 cm inside its corner;
    // the measured three-dimensional pistol trace remains the assertion.
    for(FVector Point:{FVector(-1300,0,0),FVector(-1300,-300,0),FVector(-1120,-300,0)})
        if(!TestTrue(TEXT("Mapped movement reaches real cover"),SoraLiftAutomation::Walk(*W.World,Local(Point)))) return false;
    SoraMarginTest::TraceCover(W,TEXT("standing"));
    TestEqual(TEXT("Standing outside the pistol's blocked line earns no cover time"),Arena->MarginLingerMs(),0);
    if(!W.Press(EKeys::C)||!W.Tick(5)) return false;
    auto* Cover=Arena->BridgeConsoles()[2].Get();
    const FHitResult CrouchedTrace=SoraMarginTest::TraceCover(W,TEXT("after mapped C"));
    const bool Crouched=TestTrue(TEXT("Mapped C reaches the actual crouched stance"),W.Hero()->IsCrouched());
    const bool Blocked=TestTrue(TEXT("Real console 2 physically blocks Collatera's actual pistol trace"),
        CrouchedTrace.bBlockingHit&&CrouchedTrace.GetComponent()==Cover);
    if(!Crouched||!Blocked) return false;
    if(!SoraMarginTest::Seconds(W,2)||!W.Press(EKeys::Escape)) return false;
    const int32 Paused=Arena->MarginLingerMs();
    if(!W.Tick(120)) return false;
    TestEqual(TEXT("Pause does not advance continuous cover time"),Arena->MarginLingerMs(),Paused);
    W.Mode()->ResumePlay();
    for(int Frame=0;Frame<500&&Arena->MarginPinnedConsole()==INDEX_NONE;++Frame) if(!W.Tick(1)) return false;
    TestEqual(TEXT("Six seconds of actual blocking cover pins that console"),Arena->MarginPinnedConsole(),2);
    TestTrue(TEXT("The existing authored cover bark enters the dialogue queue"),W.Campaign()->QueuedSubtitles().ContainsByPredicate(
        [](const FSoraSubtitle& Line) { return Line.LineId==TEXT("ch07.b13.collatera.009"); }));
    const int32 Attack=Boss->Data()->AttackIndex(TEXT("margin_call"));
    const float InsideHealth=W.Hero()->Health;
    if(!Arena->BeginBridgeMargin(*Boss,Attack,9100)||!SoraMarginTest::Seconds(W,Boss->WindupFor(Attack)/1000.0+.25)) return false;
    TestEqual(TEXT("Staying under one real marked strike deals sixty damage"),InsideHealth-W.Hero()->Health,60.f);
    TestTrue(TEXT("The first strike damages but does not destroy the console"),Arena->MarginConsoleHits(2)==1&&Cover->IsCollisionEnabled());
    for(int Frame=0;Frame<500&&Arena->MarginPinnedConsole()==INDEX_NONE;++Frame) if(!W.Tick(1)) return false;
    TestEqual(TEXT("Remaining behind the same blocker can pin the following call"),Arena->MarginPinnedConsole(),2);
    if(!W.Press(EKeys::C)||!W.Tick(5)) return false;
    for(FVector Point:{FVector(-1300,0,0),FVector(1800,0,0),FVector(1800,1500,0)})
        if(!SoraLiftAutomation::Walk(*W.World,Local(Point))) return false;
    TestEqual(TEXT("Leaving the blocker resets continuous occupancy"),Arena->MarginLingerMs(),0);
    TestEqual(TEXT("Leaving does not erase the announced next target"),Arena->MarginPinnedConsole(),2);
    if(!Arena->BeginBridgeMargin(*Boss,Attack,9101)) return false;
    TestTrue(TEXT("The next call prioritizes the pinned console even after the hero leaves"),Arena->MarginTargetIds().Num()==3&&Arena->MarginTargetIds()[0]==2);
    TestEqual(TEXT("Starting the next call consumes the pin"),Arena->MarginPinnedConsole(),INDEX_NONE);
    const float Health=W.Hero()->Health;
    if(!SoraMarginTest::Seconds(W,Boss->WindupFor(Attack)/1000.0+.25)) return false;
    TestTrue(TEXT("The departed console takes its second hit and loses real collision"),Arena->MarginConsoleHits(2)==2&&!Cover->IsCollisionEnabled());
    TestEqual(TEXT("The escaped hero is not chased by the snapshotted warning"),W.Hero()->Health,Health);
    return !HasAnyErrors();
}
#endif
