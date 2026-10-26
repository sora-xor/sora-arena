#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "SoraWorldBuilder.h"
#include "SoraLandingSpaceRules.h"
#include "SoraDroneRules.h"
#include "Components/SpotLightComponent.h"
#include "Components/StaticMeshComponent.h"

namespace SoraLandingSpaceTest
{
using SoraFieldcraftAutomation::FBeatWorld;
bool Start(FBeatWorld& W)
{
    if(!FSoraCatalog::Get().Load()||!W.Start())return false;
    W.Harden();
    // Isolate patrol observation from detection without replacing a guard's
    // senses or circuit. The observer is held inside a solid warehouse.
    W.Stand(FVector(-11440,-930,0));
    W.Hero()->GetCharacterMovement()->StopMovementImmediately();
    W.Hero()->GetCharacterMovement()->SetComponentTickEnabled(false);
    for(int I=0;I<3000&&!W.Mode()->IsPlaying();++I)if(!W.Tick(1,.02f))return false;
    return W.Test.TestTrue(TEXT("Landing dialogue releases the actual encounter"),W.Mode()->IsPlaying());
}
TArray<ASoraEnemy*> Drones(FBeatWorld& W)
{
    TArray<ASoraEnemy*> Result;
    for(TActorIterator<ASoraEnemy> I(W.World->GetTestWorld());I;++I)
        if(I->HasLandingDroneAssignment())Result.Add(*I);
    Result.Sort([](const ASoraEnemy& A,const ASoraEnemy& B){return A.GetActorLocation().Z>B.GetActorLocation().Z;});
    return Result;
}
AActor* Block(FBeatWorld& W,const FVector& At,const FVector& Size)
{
    auto* Actor=W.World->GetTestWorld()->SpawnActor<AActor>();
    if(!Actor)return nullptr;
    auto* Mesh=ASoraWorldBuilder::Shape(Actor,nullptr,TEXT("LandingTestBlock"),TEXT("/Engine/BasicShapes/Cube.Cube"),
        FVector::ZeroVector,Size/100.f,FLinearColor(.2f,.2f,.2f));
    Actor->SetRootComponent(Mesh);Actor->SetActorLocation(At);
    Mesh->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);Mesh->SetCollisionObjectType(ECC_WorldStatic);
    Mesh->SetCollisionResponseToAllChannels(ECR_Block);
    return Actor;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraLandingSolidsTest,"SoraArena.Campaign.LandingSpace.Solids",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraLandingSolidsTest::RunTest(const FString&)
{
    using namespace SoraLandingSpaceTest;namespace R=SoraLandingSpaceRules;
    FBeatWorld W(*this,TEXT("LandingSolids"),2,1);if(!Start(W))return false;
    const auto Floor=[&](FVector2D At,float Expected)
    {
        FHitResult Hit;FCollisionObjectQueryParams Objects(ECC_WorldStatic);
        FCollisionQueryParams Query(SCENE_QUERY_STAT(LandingFloor),false,W.Hero());
        const bool Found=W.World->GetTestWorld()->LineTraceSingleByObjectType(Hit,FVector(At,200),FVector(At,-250),Objects,Query);
        return TestTrue(FString::Printf(TEXT("Actual support at %s has top %.1f cm"),*At.ToString(),Expected),
            Found&&!Hit.bStartPenetrating&&FMath::Abs(Hit.ImpactPoint.Z-Expected)<1.f);
    };
    Floor(FVector2D(R::Entry.X,R::Entry.Y),0);
    Floor(FVector2D(-7820,-850),0);
    for(int I=0;I<6;++I)Floor(FVector2D(-11300,-2825-I*50),-(I+1)*(160.f/6.f));
    for(const auto& P:R::Cargo)Floor(FVector2D(P.X,P.Y),140);
    for(int X:{-11440,-10520,-9600})Floor(FVector2D(X,-1270),1);
    FCollisionObjectQueryParams Objects(ECC_WorldStatic);
    for(int G=0;G<2;++G)for(int I=0;I<R::Count(G);++I)
    {
        const auto A=R::Point(G,I),B=R::Point(G,(I+1)%R::Count(G));FHitResult Hit;
        const bool Blocked=W.World->GetTestWorld()->SweepSingleByObjectType(Hit,FVector(A.X,A.Y,R::Height(G)),
            FVector(B.X,B.Y,R::Height(G)),FQuat::Identity,Objects,FCollisionShape::MakeSphere(SoraDroneRules::MovementRadiusCm));
        TestFalse(FString::Printf(TEXT("Physical drone corridor %d leg %d is clear"),G,I),Blocked);
    }
    AddInfo(TEXT("Directed collision probes only. Ordinary-control traversal and visual acceptance remain separate."));
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraLandingPatrolTest,"SoraArena.Campaign.LandingSpace.Patrols",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraLandingPatrolTest::RunTest(const FString&)
{
    using namespace SoraLandingSpaceTest;namespace R=SoraLandingSpaceRules;
    FBeatWorld W(*this,TEXT("LandingPatrols"),2,1);if(!Start(W))return false;
    const auto Guards=Drones(W);if(!TestEqual(TEXT("Both authored drones are present"),Guards.Num(),2))return false;
    for(int Frame=0;Frame<4200;++Frame)
    {
        if(!W.Tick(1))return false;
        for(int G=0;G<2;++G)
        {
            const auto* Brain=Cast<ASoraEnemyController>(Guards[G]->GetController());
            if(!TestTrue(TEXT("Real guard stays calm on its assigned flight layer"),Brain&&
                Brain->State()==SoraStealthRules::EState::Unaware&&FMath::IsNearlyEqual(Guards[G]->GetActorLocation().Z,float(R::Height(G)),5.f)))return false;
        }
    }
    for(int G=0;G<2;++G)
    {
        const auto* Brain=Cast<ASoraEnemyController>(Guards[G]->GetController());const auto& T=Brain->PatrolTiming();
        TestTrue(TEXT("All real waypoint arrivals complete the authored loop on time"),T.Cycles>=1&&!T.Overdue&&
            FMath::Abs(T.LastCycleMs-R::Period(G))<=50&&T.Visited==((1u<<R::Count(G))-1));
        AddInfo(FString::Printf(TEXT("Landing D%d cycles=%d last_ms=%lld visited=%u overdue=%d"),G+1,T.Cycles,T.LastCycleMs,T.Visited,T.Overdue));
    }
    if(!W.Press(EKeys::Escape))return false;
    FVector Positions[2];long long Clocks[2];
    for(int G=0;G<2;++G){Positions[G]=Guards[G]->GetActorLocation();Clocks[G]=Cast<ASoraEnemyController>(Guards[G]->GetController())->PatrolTiming().ElapsedMs;}
    if(!W.Tick(180))return false;
    for(int G=0;G<2;++G)
    {
        TestTrue(TEXT("Menu holds the physical patrol"),Guards[G]->GetActorLocation().Equals(Positions[G],1.f));
        TestEqual(TEXT("Menu holds its deadline clock"),Cast<ASoraEnemyController>(Guards[G]->GetController())->PatrolTiming().ElapsedMs,Clocks[G]);
    }
    AddInfo(TEXT("The observer is held within a warehouse solid. This tests live patrols and menu pause, not a player stealth route."));
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraLandingSearchlightTest,"SoraArena.Campaign.LandingSpace.Searchlight",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraLandingSearchlightTest::RunTest(const FString&)
{
    using namespace SoraLandingSpaceTest;
    FBeatWorld W(*this,TEXT("LandingSearchlight"),2,1);if(!Start(W))return false;
    const auto Guards=Drones(W);if(!TestEqual(TEXT("Both actual landing drones spawn"),Guards.Num(),2))return false;
    TestNull(TEXT("D1 has no canal searchlight"),Guards[0]->FindComponentByClass<USpotLightComponent>());
    auto* Drone=Guards[1];auto* Lamp=Drone->FindComponentByClass<USpotLightComponent>();
    if(!TestNotNull(TEXT("D2 carries its physical searchlight"),Lamp))return false;
    Drone->GetController()->SetActorTickEnabled(false);Drone->GetCharacterMovement()->SetComponentTickEnabled(false);
    Drone->SetActorLocation(FVector(-11000,-2700,500),false,nullptr,ETeleportType::TeleportPhysics);
    Drone->SetActorRotation(FRotator::ZeroRotator);
    const FVector Origin=Lamp->GetComponentLocation(),Aim=Lamp->GetForwardVector(),Sample=Origin+Aim*500;
    TestTrue(TEXT("The real downward cone illuminates its footprint"),Drone->LandingSearchlightAt(Sample)>0);
    TestEqual(TEXT("The same distance behind the lamp stays outside its cone"),Drone->LandingSearchlightAt(Origin-Aim*500),0);
    auto* Cover=Block(W,Origin+Aim*250,FVector(100));if(!TestNotNull(TEXT("Actual opaque cover spawns"),Cover))return false;
    TestEqual(TEXT("Physical cover shadows the cone"),Drone->LandingSearchlightAt(Sample),0);
    Cover->Destroy();
    TestTrue(TEXT("Removing cover restores the cone"),Drone->LandingSearchlightAt(Sample)>0);
    FBeatWorld::Hurt(*Drone,Drone->Health+1000.f);
    TestEqual(TEXT("A downed drone cannot illuminate stealth samples"),Drone->LandingSearchlightAt(Sample),0);
    TestFalse(TEXT("A downed drone extinguishes its rendered lamp"),Lamp->IsVisible());
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraLandingBlockedPatrolTest,"SoraArena.Campaign.LandingSpace.BlockedPatrol",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraLandingBlockedPatrolTest::RunTest(const FString&)
{
    using namespace SoraLandingSpaceTest;
    FBeatWorld W(*this,TEXT("LandingBlockedPatrol"),2,1);if(!Start(W))return false;
    const auto Guards=Drones(W);if(!TestEqual(TEXT("Both landing drones spawn"),Guards.Num(),2))return false;
    auto* Drone=Guards[1];auto* Brain=Cast<ASoraEnemyController>(Drone->GetController());
    if(!TestNotNull(TEXT("Canal drone has its actual controller"),Brain))return false;
    auto* Obstacle=Block(W,FVector(-9800,-2700,400),FVector(100,350,250));
    if(!TestNotNull(TEXT("Physical flight obstruction spawns"),Obstacle)||!W.Tick(1260))return false;
    const auto& Blocked=Brain->PatrolTiming();
    TestTrue(TEXT("The body stops before the obstruction without inventing a waypoint arrival"),
        Drone->GetActorLocation().X<-9850&&Blocked.Legs==0&&Blocked.Cycles==0&&Blocked.Overdue);
    Obstacle->Destroy();
    for(int I=0;I<2400&&Brain->PatrolTiming().Cycles==0;++I)if(!W.Tick(1))return false;
    const auto& Resumed=Brain->PatrolTiming();
    TestTrue(TEXT("Removing the obstruction permits a real late return, preserving the missed deadline"),
        Resumed.Cycles>=1&&Resumed.LastCycleMs>30000&&Resumed.Visited==3&&Resumed.Overdue);
    return !HasAnyErrors();
}
#endif
