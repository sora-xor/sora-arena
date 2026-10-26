#include "SoraEnemy.h"
#include "SoraGameMode.h"
#include "SoraSettings.h"
#include "SoraWorldBuilder.h"
#include "Combat/SoraDamage.h"
#include "Combat/SoraEnemyCatalog.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"

namespace Landing=SoraLandingDroneRules;

bool ASoraEnemy::IsLandingDroneLow() const
{
    return bLandingDrone&&bLandingFloorKnown&&IsAlive()&&
        GetActorLocation().Z<=LandingLow.Z+.1;
}
void ASoraEnemy::ClearLandingWarning()
{
    const auto Warning=LandingWarning; LandingWarning.Reset();
    if(Warning.IsValid()) Warning->Destroy();
}
bool ASoraEnemy::BeginLandingDrone(int32 WindupMs)
{
    LandingHome=GetActorLocation();
    FHitResult Floor;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(LandingDroneFloor),false,this);
    FCollisionObjectQueryParams Objects;
    Objects.AddObjectTypesToQuery(ECC_WorldStatic); Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    if(!GetWorld()->LineTraceSingleByObjectType(Floor,LandingHome,LandingHome-FVector(0,0,10000),Objects,Query))
        return false;
    LandingLow=FVector(LandingHome.X,LandingHome.Y,Floor.ImpactPoint.Z+Landing::LowHeightCm);
    if(LandingLow.Z>LandingHome.Z) return false;
    bLandingFloorKnown=true;

    FActorSpawnParameters Params; Params.Owner=this;
    auto* Warning=GetWorld()->SpawnActor<AActor>(Params);
    if(!Warning) return false;
    auto* Root=NewObject<USceneComponent>(Warning,TEXT("LandingDroneWarningRoot"));
    Warning->SetRootComponent(Root); Root->RegisterComponent(); Warning->AddInstanceComponent(Root);
    Warning->SetActorLocation(LockedPoint); Warning->Tags.Add(TEXT("SoraLandingDroneWarning"));
    const auto Color=SoraAccessibility::TelegraphColor(this,SoraAccessibility::ETelegraph::Lock);
    const float Radius=AttackSet()[AttackIndex].RadiusCm;
    constexpr int Segments=48;
    for(int I=0;I<Segments;++I)
    {
        const float Angle=2.f*PI*I/Segments;
        auto* Mark=ASoraWorldBuilder::Shape(Warning,Root,TEXT("LandingDroneLock"),TEXT("/Engine/BasicShapes/Cube.Cube"),
            FVector(FMath::Cos(Angle)*Radius,FMath::Sin(Angle)*Radius,3),
            FVector(.04f,2.f*PI*Radius/Segments/100.f,.02f),Color);
        if(!Mark||!Mark->GetStaticMesh()) { Warning->Destroy(); return false; }
        Mark->SetRelativeRotation(FRotator(0,FMath::RadiansToDegrees(Angle),0));
        Mark->SetCollisionEnabled(ECollisionEnabled::NoCollision); Mark->SetCastShadow(false);
    }
    // Owned marker, no world-time lifespan: pause/dialogue preserves it.
    ClearLandingWarning(); LandingWarning=Warning;
    Landing::Begin(LandingDroneClock,WindupMs); LandingDroneMilliseconds.Reset();
    LandingDroneLastWorldSeconds=GetWorld()->GetTimeSeconds();
    ConsumeMovementInputVector(); GetCharacterMovement()->StopMovementImmediately();
    return true;
}
void ASoraEnemy::TickLandingDrone()
{
    const double Time=GetWorld()->GetTimeSeconds();
    const double Elapsed=FMath::Max(0.,Time-LandingDroneLastWorldSeconds);
    LandingDroneLastWorldSeconds=Time;
    const auto* Mode=Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode());
    if(!Mode||!Mode->IsPlaying()||Mode->InputState()==SoraInput::Dialogue||!OwnsLandingDroneMotion()) return;
    auto* Target=AttackTarget.Get();
    if(!Target||!Target->IsAlive()||!AttackSet().IsValidIndex(AttackIndex)) { CancelAttack(); return; }
    if((LandingDroneClock.Stage==Landing::EStage::Mark||LandingDroneClock.Stage==Landing::EStage::Descending)&&
        (!LandingWarning.IsValid()||LandingWarning->IsActorBeingDestroyed())) { CancelAttack(); return; }
    ConsumeMovementInputVector(); GetCharacterMovement()->StopMovementImmediately();
    int32 Remaining=LandingDroneMilliseconds.Advance(Elapsed);
    while(Remaining>0&&OwnsLandingDroneMotion())
    {
        Remaining=Landing::AdvanceTimer(LandingDroneClock,Remaining);
        const auto Stage=LandingDroneClock.Stage;
        if(Stage==Landing::EStage::Mark||Stage==Landing::EStage::Low) return;
        const bool Descending=Stage==Landing::EStage::Descending;
        if(!Descending&&Stage!=Landing::EStage::Ascending) return;
        Phase=Descending?EPhase::Firing:EPhase::Recovery;
        const FVector Destination=Descending?LandingLow:LandingHome;
        const FVector From=GetActorLocation();
        const double Distance=FVector::Distance(From,Destination);
        const double Travel=FMath::Min(Distance,double(Remaining)*Landing::SpeedCmPerSecond/1000.);
        FHitResult Hit;
        SetActorLocation(From+(Destination-From).GetSafeNormal()*Travel,true,&Hit);
        const bool Arrived=GetActorLocation().Equals(Destination,.01);
        // A ceiling, prop or moving body can obstruct either leg. Abort in
        // place; never teleport through it or spend a net on a timer alone.
        if(Hit.bBlockingHit&&!Arrived) { CancelAttack(); return; }
        if(!Arrived) return;
        Remaining=FMath::Max(0,Remaining-FMath::CeilToInt(Distance*1000./Landing::SpeedCmPerSecond));
        if(Descending)
        {
            if(!Landing::ArriveLow(LandingDroneClock,true)) return;
            ClearLandingWarning();
            const FSoraEnemyAttack Attack=AttackSet()[AttackIndex];
            Recover(Attack);
            // A hero who moves behind solid cover after the lock is safe.
            FHitResult Cover;
            FCollisionQueryParams Query(SCENE_QUERY_STAT(LandingDroneNet),false,this);
            GetWorld()->LineTraceSingleByChannel(Cover,NetMuzzle(),Target->GetActorLocation(),ECC_Visibility,Query);
            if(!Cover.bBlockingHit||Cover.GetActor()==Target) CastNet(Attack,*Target);
        }
        else if(Landing::ArriveHome(LandingDroneClock,true)) CancelAttack();
    }
}
