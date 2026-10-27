#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraLiftAutomation.h"
#include "SoraNoticeSquareRules.h"
#include "Components/CapsuleComponent.h"
#include "Components/BoxComponent.h"
#include "SoraEnemyController.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraNoticeStreetRoutesTest,"SoraArena.Campaign.NoticeSquare.StreetRoutes",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraNoticeStreetRoutesTest::RunTest(const FString&)
{
    namespace N=SoraNoticeSquareRules;
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("NoticeStreetRoutes"),2,9);
    if(!FSoraCatalog::Get().Load()||!W.Start())return false;
    for(int I=0;I<3000&&!W.Mode()->IsPlaying();++I)if(!W.Tick(1))return false;
    if(!TestTrue(TEXT("The notice-square checkpoint releases normal controls"),W.Mode()->IsPlaying()))return false;
    // Isolate street traversal from guard interference. Only the
    // starting point of each route is placed; every segment uses mapped W
    // input, real character collision and gravity.
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)It->Destroy();
    const auto Walk=[&](FVector To)
    {
        const bool Reached=SoraLiftAutomation::Walk(*W.World,To);
        const auto* H=W.Hero();
        return TestTrue(TEXT("The real street segment reaches its destination on the street floor"),
            Reached&&H->GetCharacterMovement()->IsMovingOnGround()&&
            FMath::Abs(H->GetActorLocation().Z-H->GetCapsuleComponent()->GetScaledCapsuleHalfHeight())<=8.f);
    };
    W.Stand(FVector(0,N::SouthStub,0));if(!W.Tick(8))return false;
    for(int Y:{-700,700,N::NorthStub})if(!Walk(FVector(0,Y,0)))return false;
    W.Stand(FVector(N::WestTurnaround,0,0));if(!W.Tick(8))return false;
    for(int X:{0,N::EastTurnaround})if(!Walk(FVector(X,0,0)))return false;
    const TPair<FVector,FVector> Edges[]={
        {FVector(0,3800,90),FVector(0,4100,90)},
        {FVector(0,3250,90),FVector(-500,3250,90)},
        {FVector(0,3250,90),FVector(500,3250,90)},
        {FVector(4000,0,90),FVector(4300,0,90)},
        {FVector(3650,0,90),FVector(3650,-500,90)},
        {FVector(3650,0,90),FVector(3650,500,90)}};
    for(const auto& Edge:Edges)
    {
        FHitResult Hit;FCollisionQueryParams Query(SCENE_QUERY_STAT(NoticeStreetBoundary),false,W.Hero());
        const bool Blocked=W.World->GetTestWorld()->LineTraceSingleByChannel(Hit,Edge.Key,Edge.Value,ECC_Visibility,Query);
        if(!TestTrue(TEXT("Each new street edge has its real blocking boundary"),Blocked&&Hit.GetComponent()&&
            Hit.GetComponent()->GetName().StartsWith(TEXT("NoticeSquareBoundary"))))return false;
    }
    TestEqual(TEXT("Walking either street does not credit the terminal objectives"),W.Campaign()->TaskProgress().Done,0);
    AddInfo(TEXT("Seeded b10 with guards removed; real street traversal only. Authored patrol timing, rooftop routes and visual acceptance remain separate."));
    return !HasAnyErrors();
}
namespace SoraNoticeTest
{
using SoraFieldcraftAutomation::FBeatWorld;
namespace N=SoraNoticeSquareRules;
FName Tag(int G){return FName(*FString::Printf(TEXT("NoticeGroundGuard%d"),G));}
bool WaitForControl(FBeatWorld& W)
{
    for(int I=0;I<3000&&!W.Mode()->IsPlaying();++I)if(!W.Tick(1,.02f))return false;
    return W.Test.TestTrue(TEXT("Notice-square dialogue releases control"),W.Mode()->IsPlaying());
}
void Observe(FBeatWorld& W,int Only=-1)
{
    W.Harden();W.Stand(FVector(-2575,1050,0));
    W.Hero()->GetCharacterMovement()->StopMovementImmediately();
    W.Hero()->GetCharacterMovement()->SetComponentTickEnabled(false);
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
    {
        bool Keep=false;for(int G=2;G<7;++G)Keep|=(Only<0||G==Only)&&It->Tags.Contains(Tag(G));
        if(!Keep)It->Destroy();
    }
}
ASoraEnemy* Guard(FBeatWorld& W,int G)
{
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
        if(It->Tags.Contains(Tag(G)))return *It;
    W.Test.AddError(FString::Printf(TEXT("Missing notice-square ground guard %d"),G));return nullptr;
}
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraNoticeGroundPatrolsTest,"SoraArena.Campaign.NoticeSquare.GroundPatrols",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraNoticeGroundPatrolsTest::RunTest(const FString&)
{
    using namespace SoraNoticeTest;
    FBeatWorld W(*this,TEXT("NoticeGroundPatrols"),2,9);
    if(!FSoraCatalog::Get().Load()||!W.Start())return false;
    Observe(W);if(!WaitForControl(W))return false;
    ASoraEnemy* Guards[5]={};ASoraEnemyController* Brains[5]={};FVector Previous[5];
    TWeakObjectPtr<ASoraEnemy> Original[5];
    for(int I=0;I<5;++I)
    {
        Guards[I]=Guard(W,I+2);if(!Guards[I])return false;
        Brains[I]=Cast<ASoraEnemyController>(Guards[I]->GetController());
        if(!TestNotNull(TEXT("Each ground guard has its production patrol brain"),Brains[I]))return false;
        Previous[I]=Guards[I]->GetActorLocation();Original[I]=Guards[I];
    }
    for(int Frame=0;Frame<3600;++Frame)
    {
        if(!W.Tick(1,.02f))return false;
        for(int I=0;I<5;++I)
        {
            const FVector Here=Guards[I]->GetActorLocation();
            const float Feet=Here.Z-Guards[I]->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
            if(!TestTrue(TEXT("Every observed patrol stays unaware, grounded and physically continuous"),
                Brains[I]->State()==SoraStealthRules::EState::Unaware&&
                Guards[I]->GetCharacterMovement()->IsMovingOnGround()&&FMath::Abs(Feet)<8.f&&
                FVector::Dist(Here,Previous[I])<20.f))return false;
            Previous[I]=Here;
        }
    }
    for(int I=0;I<5;++I)
    {
        const auto& T=Brains[I]->PatrolTiming();const int G=I+2;
        TestTrue(TEXT("Every actual waypoint is visited and the circuit finishes on its authored period"),
            T.Cycles>=1&&!T.Overdue&&FMath::Abs(T.LastCycleMs-N::PatrolPeriod(G))<=50&&
            T.Visited==((1u<<N::PatrolCount(G))-1));
        AddInfo(FString::Printf(TEXT("Notice ground guard %d: cycles=%d last_ms=%lld visited=%u overdue=%d at=%s"),
            G,T.Cycles,T.LastCycleMs,T.Visited,T.Overdue,*Guards[I]->GetActorLocation().ToString()));
    }
    if(!W.Press(EKeys::Escape))return false;
    long long Clocks[5];for(int I=0;I<5;++I)
    {Previous[I]=Guards[I]->GetActorLocation();Clocks[I]=Brains[I]->PatrolTiming().ElapsedMs;}
    if(!W.Tick(180))return false;
    for(int I=0;I<5;++I)
    {
        TestTrue(TEXT("The menu freezes physical patrol movement"),Guards[I]->GetActorLocation().Equals(Previous[I],1.f));
        TestEqual(TEXT("The menu freezes each circuit clock"),Brains[I]->PatrolTiming().ElapsedMs,Clocks[I]);
    }
    if(!W.Press(EKeys::Escape)||!W.Tick(20))return false;
    for(int I=0;I<5;++I)TestTrue(TEXT("Closing the menu resumes each schedule"),Brains[I]->PatrolTiming().ElapsedMs>Clocks[I]);
    FBeatWorld::Hurt(*W.Hero(),W.Hero()->Health+1000.f);
    if(!W.Tick(2)||!TestTrue(TEXT("Death offers checkpoint retry"),W.Mode()->bDefeated)||!W.Press(EKeys::Enter))return false;
    Observe(W);if(!WaitForControl(W))return false;
    for(int I=0;I<5;++I)
    {
        TestFalse(TEXT("Retry removes the old patrol actors"),Original[I].IsValid());
        auto* E=Guard(W,I+2);if(!E)return false;
        auto* Brain=Cast<ASoraEnemyController>(E->GetController());const auto P=N::PatrolPoint(I+2,0);
        TestTrue(TEXT("Retry restores each route's initial phase and clears missed deadlines"),Brain&&
            Brain->PatrolTiming().Cycles==0&&Brain->PatrolTiming().Legs==0&&!Brain->PatrolTiming().Overdue&&
            FVector::Dist2D(E->GetActorLocation(),FVector(P.X,P.Y,0))<100.f);
    }
    TestEqual(TEXT("Patrol observation does not credit terminal work"),W.Campaign()->TaskProgress().Done,0);
    AddInfo(TEXT("Hidden stationary observer; the two provisional airborne/roof guards are removed. All five ground guards remain live together. This checks movement, schedules, pause and retry, not ordinary stealth difficulty."));
    return !HasAnyErrors();
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraNoticeBlockedPatrolTest,"SoraArena.Campaign.NoticeSquare.BlockedPatrol",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraNoticeBlockedPatrolTest::RunTest(const FString&)
{
    using namespace SoraNoticeTest;
    FBeatWorld W(*this,TEXT("NoticeBlockedPatrol"),2,9);
    if(!FSoraCatalog::Get().Load()||!W.Start())return false;
    Observe(W,2);
    auto* Barrier=W.World->GetTestWorld()->SpawnActor<AActor>();
    if(!TestNotNull(TEXT("The route obstruction spawns"),Barrier))return false;
    auto* Box=NewObject<UBoxComponent>(Barrier);Barrier->SetRootComponent(Box);Barrier->AddInstanceComponent(Box);
    Box->SetBoxExtent(FVector(10,150,150));Box->SetCollisionProfileName(TEXT("BlockAll"));Box->RegisterComponent();
    Barrier->SetActorLocation(FVector(-760,-700,150));
    if(!WaitForControl(W))return false;
    auto* E=Guard(W,2);if(!E)return false;auto* Brain=Cast<ASoraEnemyController>(E->GetController());
    if(!TestNotNull(TEXT("The obstructed guard has its production brain"),Brain)||!W.Tick(350,.02f))return false;
    const auto& T=Brain->PatrolTiming();
    TestTrue(TEXT("Time cannot skip an obstructed first waypoint"),T.Cycles==0&&T.Legs==0&&T.Visited==0&&T.Overdue&&E->GetActorLocation().X<-790.f);
    Barrier->Destroy();
    for(int Frame=0;Frame<600&&Brain->PatrolTiming().Legs==0;++Frame)if(!W.Tick(1,.02f))return false;
    const auto P=N::PatrolPoint(2,1);
    TestTrue(TEXT("Removing the barrier allows the next real arrival without erasing lateness"),
        T.Legs==1&&T.Visited==2&&T.Overdue&&T.Cycles==0&&FVector::Dist2D(E->GetActorLocation(),FVector(P.X,P.Y,0))<=25.f);
    AddInfo(TEXT("Seeded obstruction fixture with other guards removed and a hidden observer. No route replacement or clock-driven actor positioning."));
    return !HasAnyErrors();
}
#endif
