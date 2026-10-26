#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraLiftAutomation.h"
#include "SoraDroneRules.h"
#include "SoraProjectile.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "PhysicsEngine/BodySetup.h"
#include "Kismet/GameplayStatics.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraDroneBodyTest,"SoraArena.Campaign.DroneBody",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraDroneBodyTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using SoraFieldcraftAutomation::FBeatWorld;
    if(!FSoraCatalog::Get().Load()) return false;
    FBeatWorld W(*this,TEXT("DroneBody"),5,5);
    if(!W.Start()) return false;
    W.Harden();
    // Geometry and real projectile collision are isolated from AI here.
    // LedgerPatrols separately leaves both actual flight loops running.
    SoraLiftAutomation::HoldThreats(*W.World);
    ASoraEnemy* Drone=nullptr;
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
        if(It->EnemySlot()==6) Drone=*It;
    if(!TestNotNull(TEXT("The ledger spawns its actual inventory drone"),Drone)) return false;
    TInlineComponentArray<UStaticMeshComponent*> Parts(Drone);
    if(!TestEqual(TEXT("The drone has one disc body and no handheld gun or humanoid parts"),Parts.Num(),1)) return false;
    auto* Body=Parts[0];
    if(!TestTrue(TEXT("The imported body has both integrated emitter sockets"),
        Body->ComponentHasTag(TEXT("InventoryDroneBody"))&&Body->DoesSocketExist(TEXT("Eye"))&&Body->DoesSocketExist(TEXT("NetMuzzle")))) return false;
    const auto* Setup=Body->GetStaticMesh()->GetBodySetup();
    if(!TestTrue(TEXT("Precision collision contains exactly the three imported convex hulls"),
        Setup&&Setup->AggGeom.ConvexElems.Num()==3&&Setup->AggGeom.GetElementCount()==3)) return false;
    for(const auto& Hull:Setup->AggGeom.ConvexElems)
    {
        TestTrue(TEXT("Each imported hit hull has actual geometry"),Hull.VertexData.Num()>=4);
        for(const FVector& Vertex:Hull.VertexData)
        {
            const FVector Local=Hull.GetTransform().TransformPosition(Vertex);
            if(!TestTrue(TEXT("Hit hull stays in the physical disc/dome/pod span"),
                !Local.ContainsNaN()&&Local.Size()<38.&&Local.Z>=-18.&&Local.Z<=10.)) return false;
        }
    }
    TestNull(TEXT("The drone has no humanoid skeletal visual"),Drone->GetMesh()->GetSkeletalMeshAsset());
    TestTrue(TEXT("The disc is used at authored scale one"),Drone->GetActorScale3D().Equals(FVector::OneVector,.0001f));
    TestEqual(TEXT("The movement sphere uses its measured radius"),Drone->GetCapsuleComponent()->GetScaledCapsuleRadius(),SoraDroneRules::MovementRadiusCm);
    TestEqual(TEXT("The movement sphere has equal radius and half-height"),Drone->GetCapsuleComponent()->GetScaledCapsuleHalfHeight(),SoraDroneRules::MovementRadiusCm);
    const FVector At=Drone->GetActorLocation();
    TestTrue(TEXT("The complete body remains on the authored flight plane"),FMath::IsNearlyEqual(At.Z,550.,.1));
    for(float Yaw:{0.f,90.f})
    {
        Drone->SetActorRotation(FRotator(0,Yaw,0));
        TestTrue(TEXT("Sight follows the cyan eye while the drone turns"),Drone->SenseOrigin().Equals(Body->GetSocketLocation(TEXT("Eye")),.01));
        TestTrue(TEXT("The tether follows the integrated outlet while the drone turns"),Drone->NetMuzzle().Equals(Body->GetSocketLocation(TEXT("NetMuzzle")),.01));
    }
    Drone->SetActorRotation(FRotator::ZeroRotator);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(DronePrecisionHits),false,W.Hero());
    for(float Z:{-30.f,30.f})
    {
        const FVector Probe=At+FVector(0,0,Z);
        TestTrue(TEXT("The miss probe is inside the movement sphere"),W.World->GetTestWorld()->OverlapBlockingTestByChannel(
            Probe,FQuat::Identity,ECC_Pawn,FCollisionShape::MakeSphere(1),Query));
        TestFalse(TEXT("A precision ray through empty space above or below the disc misses"),W.World->GetTestWorld()->LineTraceTestByChannel(
            Probe-FVector(100,0,0),Probe+FVector(100,0,0),ECC_Visibility,Query));
    }
    FHitResult Hit;
    TestTrue(TEXT("A centre ray hits the visible convex body"),W.World->GetTestWorld()->LineTraceSingleByChannel(
        Hit,At-FVector(100,0,0),At+FVector(100,0,0),ECC_Visibility,Query)&&Hit.GetComponent()==Body);
    const auto Arrow=[&](float Z)
    {
        const FTransform Spawn(FRotator::ZeroRotator,At+FVector(-120,0,Z));
        auto* Shot=W.World->GetTestWorld()->SpawnActorDeferred<ASoraProjectile>(ASoraProjectile::StaticClass(),
            Spawn,W.Hero(),W.Hero(),ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
        if(!Shot) return TWeakObjectPtr<ASoraProjectile>();
        Shot->bArrow=true;Shot->WeaponId=18;Shot->Damage=5;Shot->Velocity=FVector(4000,0,0);
        UGameplayStatics::FinishSpawningActor(Shot,Spawn);
        return TWeakObjectPtr<ASoraProjectile>(Shot);
    };
    const float Health=Drone->Health;
    for(float Z:{-30.f,30.f})
    {
        auto Shot=Arrow(Z);
        if(!TestTrue(TEXT("A real test arrow launches"),Shot.IsValid())||!W.Tick(6)) return false;
        TestTrue(TEXT("An arrow crosses the empty movement sphere without impact"),Shot.IsValid()&&Shot->GetActorLocation().X>At.X+100);
        TestEqual(TEXT("A miss outside the visible disc causes no damage"),Drone->Health,Health);
        if(Shot.IsValid()) Shot->Destroy();
    }
    auto Shot=Arrow(0);
    if(!TestTrue(TEXT("The positive-control arrow launches"),Shot.IsValid())||!W.Tick(6)) return false;
    TestFalse(TEXT("The disc stops an arrow that physically hits it"),Shot.IsValid());
    TestEqual(TEXT("A physical arrow hit applies its actual damage"),Drone->Health,Health-5.f);
    // Release only this pawn's movement for a real gravity/collision defeat.
    // Other guards remain held so they cannot interrupt the isolated fixture.
    Drone->SetActorTickEnabled(true);
    Drone->GetCharacterMovement()->SetComponentTickEnabled(true);
    FHitResult Defeat; Defeat.ImpactPoint=At;
    TestTrue(TEXT("A lethal physical hit defeats the drone"),SoraDamage::Strike(Drone,Drone->Health,
        FSoraHit::Ranged(At-FVector(120,0,0),18),FVector::ForwardVector,Defeat,W.Hero()->GetController(),W.Hero())>0&&!Drone->IsAlive());
    TestTrue(TEXT("Loss of hover starts an actual fall"),Drone->GetCharacterMovement()->IsFalling());
    if(!W.Tick(30)) return false;
    TestTrue(TEXT("The defeated drone falls below its former patrol plane"),Drone->GetActorLocation().Z<At.Z-80);
    if(!W.Tick(120)) return false;
    TestTrue(TEXT("A fallen guard remains available for discovery"),IsValid(Drone)&&Drone->IsBody());
    TestTrue(TEXT("The fallen drone settles on actual world geometry"),Drone->GetCharacterMovement()->IsMovingOnGround());
    const FVector Rest=Drone->GetActorLocation();
    if(!W.Tick(30)) return false;
    TestTrue(TEXT("The defeated drone does not return to flight"),Drone->GetActorLocation().Equals(Rest,.1));
    AddInfo(TEXT("Actual imported body, sockets, ray/swept-arrow hits and falling defeat with other guards held. Patrol routes and final art require separate checks."));
    return true;
}
#endif
