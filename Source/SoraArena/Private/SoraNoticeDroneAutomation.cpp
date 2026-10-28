#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraNoticeSquareRules.h"
#include "SoraDroneRules.h"
#include "SoraEnemyController.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"

namespace SoraNoticeDroneTest
{
using SoraFieldcraftAutomation::FBeatWorld;
namespace N=SoraNoticeSquareRules;
ASoraEnemy* Observe(FBeatWorld& W)
{
    W.Harden();W.Stand(FVector(-2575,1050,0));
    W.Hero()->GetCharacterMovement()->StopMovementImmediately();
    W.Hero()->GetCharacterMovement()->SetComponentTickEnabled(false);
    for(int I=0;I<3000&&!W.Mode()->IsPlaying();++I)if(!W.Tick(1,.02f))return nullptr;
    if(!W.Test.TestTrue(TEXT("The notice dialogue releases control"),W.Mode()->IsPlaying()))return nullptr;
    ASoraEnemy* Drone=nullptr;int Count=0,OtherGuards=0;
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
        if(It->Tags.Contains(TEXT("NoticeSquareDrone"))){Drone=*It;++Count;}
        else ++OtherGuards;
    if(!W.Test.TestEqual(TEXT("One notice drone owns the circuit"),Count,1)||
       !W.Test.TestEqual(TEXT("All six other encounter guards remain live"),OtherGuards,6))return nullptr;
    return Drone;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraNoticeDroneCircuitTest,"SoraArena.Campaign.NoticeSquare.DroneCircuit",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraNoticeDroneCircuitTest::RunTest(const FString&)
{
    using namespace SoraNoticeDroneTest;
    FBeatWorld W(*this,TEXT("NoticeDroneCircuit"),2,9);
    if(!FSoraCatalog::Get().Load()||!W.Start())return false;
    auto* Drone=Observe(W);if(!Drone)return false;
    auto* Brain=Cast<ASoraEnemyController>(Drone->GetController());
    if(!TestNotNull(TEXT("The notice drone uses the production controller"),Brain))return false;
    TestEqual(TEXT("The full imported drone retains its movement radius"),Drone->GetCapsuleComponent()->GetScaledCapsuleRadius(),SoraDroneRules::MovementRadiusCm);
    FCollisionObjectQueryParams Objects;Objects.AddObjectTypesToQuery(ECC_WorldStatic);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    for(int I=0;I<N::DroneCount;++I)
    {
        const auto A=N::DroneCircuit[I],B=N::DroneCircuit[(I+1)%N::DroneCount];FHitResult Hit;
        // The extra 10 cm also covers tight arrival tolerance and turning.
        const bool Blocked=W.World->GetTestWorld()->SweepSingleByObjectType(Hit,
            FVector(A.X,A.Y,N::DroneHeight),FVector(B.X,B.Y,N::DroneHeight),FQuat::Identity,Objects,
            FCollisionShape::MakeSphere(SoraDroneRules::MovementRadiusCm+10.f));
        if(!TestFalse(FString::Printf(TEXT("Flight leg %d clears built geometry: %s/%s"),I,
            *GetNameSafe(Hit.GetActor()),*GetNameSafe(Hit.GetComponent())),Blocked))return false;
    }
    FVector Previous=Drone->GetActorLocation();float MinRadius=10000.f,MaxRadius=0.f,MaxStep=0.f;
    for(int Frame=0;Frame<2200;++Frame)
    {
        if(!W.Tick(1,.02f))return false;
        const FVector Here=Drone->GetActorLocation();const float Radius=Here.Size2D();
        MinRadius=FMath::Min(MinRadius,Radius);MaxRadius=FMath::Max(MaxRadius,Radius);
        MaxStep=FMath::Max(MaxStep,FVector::Dist(Here,Previous));Previous=Here;
        if(!TestTrue(TEXT("The live drone stays calm on the 6 m circuit with continuous swept movement"),
            Drone->IsAlive()&&Brain->State()==SoraStealthRules::EState::Unaware&&
            FMath::IsNearlyEqual(Here.Z,float(N::DroneHeight),1.f)&&Radius>=530.f&&Radius<=548.f&&MaxStep<10.f))return false;
    }
    const auto& T=Brain->PatrolTiming();
    TestTrue(TEXT("All 32 real arrivals complete the 36 second circuit without missed deadlines"),
        T.Cycles>=1&&!T.Overdue&&FMath::Abs(T.LastCycleMs-N::DronePeriodMs)<=50&&T.Visited==0xffffffffu);
    AddInfo(FString::Printf(TEXT("Notice drone: cycles=%d last_ms=%lld visited=%u overdue=%d radius_cm=[%.3f,%.3f] max_step_cm=%.3f"),
        T.Cycles,T.LastCycleMs,T.Visited,T.Overdue,MinRadius,MaxRadius,MaxStep));
    if(!W.Press(EKeys::Escape))return false;
    const FVector Paused=Drone->GetActorLocation();const auto Clock=T.ElapsedMs;
    if(!W.Tick(180))return false;
    TestTrue(TEXT("Menu pause holds the real drone and its circuit clock"),Drone->GetActorLocation().Equals(Paused,.1f)&&T.ElapsedMs==Clock);
    if(!W.Press(EKeys::Escape)||!W.Tick(20))return false;
    TestTrue(TEXT("Closing the menu resumes the same circuit"),T.ElapsedMs>Clock&&!Drone->GetActorLocation().Equals(Paused,.1f));
    const TWeakObjectPtr<ASoraEnemy> Old=Drone;
    FBeatWorld::Hurt(*W.Hero(),W.Hero()->Health+1000.f);
    if(!W.Tick(2)||!W.Press(EKeys::Enter))return false;
    Drone=Observe(W);if(!Drone)return false;Brain=Cast<ASoraEnemyController>(Drone->GetController());
    TestTrue(TEXT("Retry removes the old flight and restores its initial phase"),!Old.IsValid()&&Brain&&
        Brain->PatrolTiming().Cycles==0&&Brain->PatrolTiming().Legs==0&&!Brain->PatrolTiming().Overdue&&
        FVector::Dist(Drone->GetActorLocation(),FVector(540,0,600))<20.f);
    TestEqual(TEXT("The flight cannot credit terminal work"),W.Campaign()->TaskProgress().Done,0);
    AddInfo(TEXT("Hidden stationary observer; all seven guards live. Existing collision only: unfinished roof architecture and ordinary stealth play remain unqualified."));
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraNoticeDroneBlockedCircuitTest,"SoraArena.Campaign.NoticeSquare.DroneBlockedCircuit",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraNoticeDroneBlockedCircuitTest::RunTest(const FString&)
{
    using namespace SoraNoticeDroneTest;
    FBeatWorld W(*this,TEXT("NoticeDroneBlockedCircuit"),2,9);
    if(!FSoraCatalog::Get().Load()||!W.Start())return false;
    auto* Drone=Observe(W);if(!Drone)return false;
    auto* Brain=Cast<ASoraEnemyController>(Drone->GetController());
    if(!TestNotNull(TEXT("The blocked drone has its production controller"),Brain))return false;
    auto* Barrier=W.World->GetTestWorld()->SpawnActor<AActor>();
    if(!TestNotNull(TEXT("A real obstruction spawns ahead of the first arrival"),Barrier))return false;
    auto* Box=NewObject<UBoxComponent>(Barrier);Barrier->SetRootComponent(Box);Barrier->AddInstanceComponent(Box);
    Box->SetBoxExtent(FVector(80,5,80));Box->SetCollisionProfileName(TEXT("BlockAll"));Box->RegisterComponent();
    Barrier->SetActorLocation(FVector(535,55,600));
    // Hold longer than a complete scheduled lap: time alone must not credit
    // any waypoint, even when the entire 36 second period has elapsed.
    if(!W.Tick(2000,.02f))return false;
    const auto& T=Brain->PatrolTiming();
    TestTrue(TEXT("The swept body stops without inventing the obstructed arrival"),
        Drone->GetActorLocation().Y<14.f&&T.Legs==0&&T.Cycles==0&&T.Visited==0&&T.Overdue&&T.ElapsedMs>N::DronePeriodMs);
    const long long BlockedUntil=T.ElapsedMs;
    Barrier->Destroy();
    for(int I=0;I<2400&&T.Cycles==0;++I)if(!W.Tick(1,.02f))return false;
    TestTrue(TEXT("Removing the obstruction allows a real late circuit, retaining the missed deadline"),
        T.Cycles>=1&&T.LastCycleMs>BlockedUntil&&T.Visited==0xffffffffu&&T.Overdue);
    AddInfo(FString::Printf(TEXT("Obstructed notice drone: cycles=%d last_ms=%lld visited=%u overdue=%d"),T.Cycles,T.LastCycleMs,T.Visited,T.Overdue));
    return !HasAnyErrors();
}
#endif
