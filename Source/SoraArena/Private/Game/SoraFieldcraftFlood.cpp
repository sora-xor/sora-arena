#include "SoraFieldcraft.h"
#include "Game/SoraFieldcraftLayout.h"
#include "Combat/SoraDamage.h"
#include "Combat/SoraStealth.h"
#include "SoraCompanion.h"
#include "SoraPlayerCharacter.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/PointLight.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"

namespace Flood=SoraFloodRules;
namespace Layout=SoraFieldcraftLayout;

bool USoraFieldcraft::InFloodWater(const FVector& At) const
{
    if(!FloodSpace) return false;
    const FVector P=At-FVector(FloodSpace->Origin,0);
    return (P.X>=-100&&P.X<=9000&&FMath::Abs(P.Y)<=120)||
        (P.X>=9000&&P.X<=10000&&P.Y>=-400&&P.Y<=400)||
        (P.X>=-11100&&P.X<=10900&&P.Y<=-400&&P.Y>=-4350);
}
float USoraFieldcraft::FloodSurfaceAt(const FVector& At) const
{
    // The connected basin and moat share the same rising surface. They are
    // deep from entry; the first 73 m of culvert initially permits wading.
    return InFloodWater(At)?static_cast<float>(Flood::Surface(FloodClockMs)):-10000.f;
}
void USoraFieldcraft::StageFlood(const FSoraBeat& Beat)
{
    if(!FloodSpace) return;
    FloodClockMs=0; FloodRoute={}; bFloodCarrying=false;
    Breath=SoraFieldcraftRules::FullBreath(Staged->Water.Rules);
    const FVector O(FloodSpace->Origin,0);
    FloodLast=Hero()?Hero()->GetActorLocation():FVector(Beat.Space.Entry,120);
    const auto Water=[&](const TCHAR* Name,float X,float Y,float W,float H)
    {
        auto* Surface=Piece(Name,Layout::Cube,O+FVector(X,Y,Flood::FromCm),FVector(W/100,H/100,.02f),FLinearColor(.025f,.09f,.11f));
        Surface->SetMobility(EComponentMobility::Movable); FloodSurfaces.Add(Surface);
        if(auto* Stealth=USoraStealth::Get(this);Stealth&&Stealth->IsZoneActive())
            Stealth->AddSurface(FBox(O+FVector(X-W/2,Y-H/2,-250),O+FVector(X+W/2,Y+H/2,250)),{2000,0});
    };
    Water(TEXT("FloodCulvertWater"),4450,0,9100,240);
    Water(TEXT("FloodBasinWater"),9500,0,1000,800);
    Water(TEXT("FloodMoatWater"),-100,-2400,22000,4000);
    FloodBoat=Piece(TEXT("FloodLampBoat"),Layout::Cube,O+FVector(4075,-2100,100),FVector(4.5f,2.4f,.3f),FLinearColor(.18f,.12f,.07f),true,Layout::Timber);
    FloodBoat->SetMobility(EComponentMobility::Movable);
    FloodBoat->SetCanEverAffectNavigation(false);
    auto* BoatLamp=GetWorld()->SpawnActor<APointLight>(O+FVector(4075,-2100,230),FRotator::ZeroRotator);
    if(BoatLamp)
    {
        BoatLamp->SetMobility(EComponentMobility::Movable);
        BoatLamp->AttachToComponent(FloodBoat,FAttachmentTransformRules::KeepWorldTransform);
        BoatLamp->PointLightComponent->SetIntensity(5000);
        BoatLamp->PointLightComponent->SetAttenuationRadius(1500);
        BoatLamp->PointLightComponent->SetLightColor(FLinearColor(1,.65f,.3f));
        BoatLamp->PointLightComponent->SetCastShadows(true); FloodLights.Add(BoatLamp);
    }
    for(const auto& Cover:Staged->Water.Cover)
        Piece(TEXT("FloodReeds"),Layout::Cylinder,FVector(Cover.Center,170),FVector(Cover.Size.X/100,Cover.Size.Y/100,1.2f),FLinearColor(.12f,.2f,.08f));
    // A visible light above the shaft makes the necessary breathing place
    // readable from either submerged leg. It never changes the breath state.
    FActorSpawnParameters Params; Params.Owner=Props;
    auto* Light=GetWorld()->SpawnActor<APointLight>(O+FVector(8250,0,205),FRotator::ZeroRotator,Params);
    if(Light)
    {
        Light->SetMobility(EComponentMobility::Movable);
        Light->PointLightComponent->SetIntensity(2400);
        Light->PointLightComponent->SetAttenuationRadius(950);
        Light->PointLightComponent->SetLightColor(FLinearColor(.65f,.8f,1));
        Light->PointLightComponent->SetCastShadows(true); FloodLights.Add(Light);
    }
}
void USoraFieldcraft::ClearFlood()
{
    if(bFloodFloating)
        if(auto* Player=Hero())
        {
            auto* Move=Player->GetCharacterMovement();
            Move->GravityScale=FloodOldGravity; Move->AirControl=FloodOldAirControl;
            Move->FallingLateralFriction=FloodOldFriction; Move->SetMovementMode(MOVE_Falling);
        }
    for(auto& Light:FloodLights) if(IsValid(Light)) Light->Destroy();
    FloodLights.Reset(); FloodSurfaces.Reset(); FloodBoat=nullptr;
    FloodSpace=nullptr; FloodClockMs=0; FloodRoute={}; bFloodFloating=false; bFloodCarrying=false;
}
void USoraFieldcraft::TickFloodWater(int32 DtMs)
{
    auto* Player=Hero(); if(!FloodSpace||!Player||DtMs<=0) return;
    FloodClockMs=FMath::Min(FloodClockMs+FMath::Min(DtMs,Flood::RiseMs),3600000);
    const float WaterZ=Flood::Surface(FloodClockMs),Dt=DtMs/1000.f;
    for(auto& Surface:FloodSurfaces) if(IsValid(Surface))
    { FVector At=Surface->GetComponentLocation(); At.Z=WaterZ; Surface->SetWorldLocation(At); }
    if(IsValid(FloodBoat))
    {
        // 14,000 cm out and back in the authored 60-second patrol. The
        // moving collision base carries guards that remain aboard.
        const int32 T=(FloodClockMs+18375)%60000;
        const float X=-4500.f+14000.f*(T<=30000?T:60000-T)/30000.f;
        const FVector At(FloodSpace->Origin+FVector2D(X,-2100),WaterZ+60.f);
        FloodBoat->SetWorldLocation(At,false,nullptr,ETeleportType::None);
    }
    auto* Move=Player->GetCharacterMovement();
    FVector At=Player->GetActorLocation();
    const FVector Local=At-FVector(FloodSpace->Origin,0);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraFloodFloor),false,Player);
    for(auto& Ally:Allies) if(IsValid(Ally)) Query.AddIgnoredActor(Ally);
    FHitResult Floor;
    const bool bFloor=GetWorld()->LineTraceSingleByChannel(Floor,At,At-FVector(0,0,1000),ECC_WorldStatic,Query);
    const bool bWet=InFloodWater(At)&&bFloor&&Floor.ImpactPoint.Z<WaterZ;
    const bool WasSwimming=bSwimming;
    bSwimming=bWet&&(WaterZ-Floor.ImpactPoint.Z>=Flood::SwimDepth||
        (Move->bWantsToCrouch&&WaterZ-Floor.ImpactPoint.Z>=90));
    if(bSwimming&&!bFloodFloating)
    {
        FloodOldGravity=Move->GravityScale; FloodOldAirControl=Move->AirControl; FloodOldFriction=Move->FallingLateralFriction;
        bFloodFloating=true;
    }
    if(bSwimming)
    {
        // Retain the character's swept horizontal movement and crouch shape.
        // Falling with neutral buoyancy permits UE's ordinary crouch/uncrouch
        // clearance checks; switching to Flying would disable crouching.
        Move->GravityScale=0; Move->AirControl=1; Move->FallingLateralFriction=8;
        Move->SetMovementMode(MOVE_Falling); Move->Velocity.Z=0;
        const float Half=Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
        const bool WantDive=Move->bWantsToCrouch;
        float Target=WaterZ-(Player->IsCrouched()?40.f:64.f)+12.f;
        if(WantDive)
        {
            Target=WaterZ-100.f-40.f;
            if(Local.X>=7300&&Local.X<=9034&&FMath::Abs(Local.Y)<120)
                Target=FMath::Min(Target,Flood::DeepRoof-Half-8.f);
        }
        Target=FMath::Max(Target,Floor.ImpactPoint.Z+Half+3.f);
        FHitResult Hit;
        Player->SetActorLocation(At+FVector(0,0,FMath::Clamp(Target-At.Z,-180.f*Dt,180.f*Dt)),true,&Hit);
    }
    else if(bFloodFloating)
    {
        Move->GravityScale=FloodOldGravity; Move->AirControl=FloodOldAirControl;
        Move->FallingLateralFriction=FloodOldFriction; Move->SetMovementMode(MOVE_Falling); bFloodFloating=false;
    }
    At=Player->GetActorLocation();
    // Actual camera immersion, not stance, XY presence or an uncrouch wish,
    // controls breathing. Releasing crouch under stone cannot create air.
    bDiving=bWet&&Flood::Immersed(FMath::RoundToInt(Player->GetCamera()->GetComponentLocation().Z),FMath::RoundToInt(WaterZ));
    const int32 Damage=SoraFieldcraftRules::Breathe(Breath,Staged->Water.Rules,bDiving,DtMs);
    const FVector Before=FloodLast-FVector(FloodSpace->Origin,0),Now=At-FVector(FloodSpace->Origin,0);
    Flood::Travel(FloodRoute,Before.X,Now.X,Now.Y,bDiving,FVector::Dist(FloodLast,At),DtMs);
    if(FloodRoute.Stage==4&&Before.Y>=-400&&Now.Y<-400&&Now.X>=9300&&Now.X<=9700&&
        FVector::Dist(FloodLast,At)<=Flood::SurfaceSpeed*Dt+25.f) FloodRoute.Gate=true;
    FloodLast=At;
    TickFloodCompanions(DtMs);
    if(WasSwimming!=bSwimming) Raise(bSwimming?TEXT("water_enter"):TEXT("water_leave"));
    if(!Staged) return;
    if(Damage>0)
    {
        FHitResult Hit; Hit.ImpactPoint=At; Hit.Location=At;
        SoraDamage::Strike(Player,Damage,FSoraHit::Hazard(At),FVector::UpVector,Hit,nullptr,nullptr);
    }
}
bool USoraFieldcraft::FloodObjective(FVector& At) const
{
    if(!FloodSpace||!Hero()) return false;
    const FVector Local=Hero()->GetActorLocation()-FVector(FloodSpace->Origin,0);
    FVector Goal(7250,0,100);
    if(Local.X>=7200&&FloodRoute.Stage<2) Goal=FVector(8250,0,Flood::Surface(FloodClockMs)+20);
    else if(FloodRoute.Stage==2) Goal=FVector(9150,0,50);
    else if(FloodRoute.Stage>=3) Goal=FloodRoute.Gate?FVector(9500,-4300,200):FVector(9500,-600,100);
    At=FVector(FloodSpace->Origin,0)+Goal; return true;
}
void USoraFieldcraft::TickFloodCompanions(int32)
{
    if(bFloodCarrying||!Hero()||!FloodSpace||Hero()->GetActorLocation().X-FloodSpace->Origin.X<7250) return;
    ASoraCompanion* Carrier=nullptr; ASoraCompanion* Iota=nullptr;
    for(auto& Ally:Allies) if(IsValid(Ally))
    {
        if(Ally->CompanionId()==TEXT("npc_toranosuke")) Carrier=Ally;
        if(Ally->CompanionId()==TEXT("npc_iota")) Iota=Ally;
    }
    if(!Carrier||!Iota||FVector::Dist(Carrier->GetActorLocation(),Iota->GetActorLocation())>350) return;
    Iota->GetCharacterMovement()->DisableMovement(); Iota->SetActorEnableCollision(false);
    Iota->AttachToActor(Carrier,FAttachmentTransformRules::KeepWorldTransform);
    Iota->SetActorRelativeLocation(FVector(-32,0,30)); Iota->SetActorRelativeRotation(FRotator(0,0,70));
    bFloodCarrying=true;
}
bool USoraFieldcraft::FloodCarriesIota() const
{
    if(!FloodSpace||!bFloodCarrying) return false;
    for(const auto& Ally:Allies) if(IsValid(Ally)&&Ally->CompanionId()==TEXT("npc_iota"))
        return Ally->GetAttachParentActor()!=nullptr;
    return false;
}
bool USoraFieldcraft::MoveFloodCompanion(ASoraCompanion& Companion,float Dt)
{
    if(!FloodSpace||!Hero()||Companion.Role()!=ASoraCompanion::ERole::Guide) return false;
    if(Companion.GetAttachParentActor()) return true;
    const FVector O(FloodSpace->Origin,0),P=Companion.GetActorLocation()-O,H=Hero()->GetActorLocation()-O;
    auto* Move=Companion.GetCharacterMovement();
    const auto BankSupport=[&](const FVector& Local,FHitResult& Hit)
    {
        if(Local.Y>Flood::BankWaterY) return false;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraFloodBank),false,&Companion);
        Query.AddIgnoredActor(Hero());
        for(const auto& Ally:Allies) if(IsValid(Ally)) Query.AddIgnoredActor(Ally);
        return GetWorld()->LineTraceSingleByChannel(Hit,O+FVector(Local.X,Local.Y,1000),
            O+FVector(Local.X,Local.Y,-1000),ECC_WorldStatic,Query)&&Hit.ImpactNormal.Z>=Move->GetWalkableFloorZ();
    };
    FHitResult Underfoot;
    const float Feet=P.Z-Companion.GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    if(P.Y<Flood::BankEdgeY-Companion.GetCapsuleComponent()->GetScaledCapsuleRadius()&&
        BankSupport(P,Underfoot)&&FMath::Abs(Underfoot.ImpactPoint.Z-Flood::BankTop)<1.f&&
        FMath::Abs(Feet-Flood::BankTop)<8.f)
    {
        // Back on the bank, ordinary guide walking owns gravity and support.
        Move->GravityScale=1; Move->SetMovementMode(MOVE_Walking);
        return false;
    }
    Move->GetNavAgentPropertiesRef().bCanCrouch=true; Move->SetCrouchedHalfHeight(44);
    const bool Deep=P.X>=7250&&P.X<=9034;
    if(Deep) Companion.Crouch(); else Companion.UnCrouch();
    Move->GravityScale=0; Move->SetMovementMode(MOVE_Falling); Move->Velocity=FVector::ZeroVector;
    FVector Goal(FMath::Clamp(H.X-180.f,100.f,9500.f),0,0);
    if(H.Y<-300&&P.X>=9400) Goal=FVector(9500,FMath::Min(-100.f,H.Y+180.f),0);
    else if(H.Y<-300) Goal=FVector(9500,0,0);
    const float Half=Companion.GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    const float Water=Flood::Surface(FloodClockMs);
    Goal.Z=Deep?FMath::Max(-200+Half+3,FMath::Min(Water-140.f,20-Half-8)):
        P.X<7300?FMath::Max(Half+3,Water-52.f):Water-52.f;
    FHitResult Support;
    if(BankSupport(Goal,Support)) Goal.Z=FMath::Max(Goal.Z,Support.ImpactPoint.Z+Half+3.f);
    FVector Delta=Goal-P;
    if(Delta.Size2D()<90) Delta.X=Delta.Y=0;
    const FVector Step=Delta.GetClampedToMaxSize(240.f*Dt);
    Companion.SetActorLocation(Companion.GetActorLocation()+Step,true);
    if(Step.SizeSquared2D()>1) Companion.SetActorRotation(FRotator(0,Step.Rotation().Yaw,0));
    return true;
}

int32 USoraFieldcraft::FloodFootstepPermille(const FVector& Feet) const
{
    if(!InFloodWater(Feet)||Feet.Z>=FloodSurfaceAt(Feet)) return -1;
    const auto* Player=Hero();
    return bDiving&&Player&&FVector::Dist2D(Feet,Player->GetActorLocation())<100.f?0:2000;
}
