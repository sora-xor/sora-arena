#include "SoraFieldcraft.h"
#include "Game/SoraFieldcraftLayout.h"
#include "Combat/SoraDamage.h"
#include "Combat/SoraStealth.h"
#include "SoraCompanion.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "SoraEquipmentComponent.h"
#include "SoraPlayerCharacter.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"

namespace Moat=SoraMoatRules;

void USoraFieldcraft::StageMoat()
{
    if(!MoatSpace)return;
    const FVector O(MoatSpace->Origin,0);
    MoatLast=Hero()?Hero()->GetActorLocation():O+FVector(1000,-100,120);
    Breath=SoraFieldcraftRules::FullBreath(Staged->Water.Rules);
    for(const auto& R:{FVector4(11000,1600,22000,4000),FVector4(20900,4050,1000,900)})
        Piece(TEXT("MoatWater"),SoraFieldcraftLayout::Cube,O+FVector(R.X,R.Y,0),FVector(R.Z/100,R.W/100,.02f),FLinearColor(.025f,.09f,.11f));
    for(const auto& Cover:Staged->Water.Cover)
        Piece(TEXT("MoatSurfaceLeaves"),SoraFieldcraftLayout::Cylinder,FVector(Cover.Center,8),
            FVector(Cover.Size.X/100,Cover.Size.Y/100,.12f),FLinearColor(.12f,.2f,.08f));
    for(float Y=60;Y<3600;Y+=120)
        Piece(TEXT("MoatFloat"),SoraFieldcraftLayout::Sphere,O+FVector(13200,Y,0),FVector(.25f,.25f,.25f),FLinearColor(.4f,.26f,.12f));
    for(auto& Ally:Allies)if(IsValid(Ally)&&Ally->CompanionId()==TEXT("npc_kohagi"))
    {
        Ally->GetCapsuleComponent()->SetCapsuleSize(Moat::Radius,Moat::HalfHeight);
        Ally->GetCharacterMovement()->SetMovementMode(MOVE_Flying);
    }
}
FVector USoraFieldcraft::MoatHead() const
{ return Hero()?Hero()->GetActorLocation()+FVector(0,0,Moat::HeadOffset):FVector::ZeroVector; }
float USoraFieldcraft::MoatDepth() const
{ return MoatSpace&&bMoatPosture?Moat::Surface-MoatHead().Z:0.f; }
bool USoraFieldcraft::MoatBlocksHitscan() const
{ return MoatSpace&&bSwimming&&MoatDepth()>MoatSpace->HitscanClearDepthCm; }
bool USoraFieldcraft::MoatHeadLit() const
{
    if(!MoatSpace||!bMoatPosture||MoatDepth()>0)return false;
    for(const FLightState& Light:LightStates)if(Light.bOn&&Light.bSeesHero)return true;
    return false;
}
bool USoraFieldcraft::MoatCrouch(ASoraPlayerCharacter&)
{ if(!MoatSpace||!bSwimming)return false;bMoatDiveWish=!bMoatDiveWish;return true; }

bool USoraFieldcraft::RestoreMoatPosture(bool Reset)
{
    auto* P=Hero();if(!P||!bMoatPosture)return true;
    auto* M=P->GetCharacterMovement();auto* C=P->GetCapsuleComponent();
    const auto* Default=P->GetClass()->GetDefaultObject<ASoraPlayerCharacter>();
    const float Half=Default->GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight();
    const float Scale=C->GetShapeScale();
    FCollisionQueryParams Q(SCENE_QUERY_STAT(MoatStand),false,P);
    // CMC's airborne expansion is centered at the current position. Check
    // the original radius as well; a smaller swim radius cannot admit land.
    const FVector StandAt=P->GetActorLocation()+FVector(0,0,M->IsMovingOnGround()?(Half-C->GetUnscaledCapsuleHalfHeight())*Scale:0);
    bool Blocked=GetWorld()->OverlapBlockingTestByChannel(StandAt,FQuat::Identity,ECC_Pawn,
        FCollisionShape::MakeCapsule(MoatOldRadius*Scale,Half*Scale),Q);
    if(Blocked&&!Reset)return false;
    if(Blocked)
    {
        // Checkpoint/beat teardown only: never an ordinary traversal move.
        P->SetActorLocation(FVector(MoatSpace->Origin,0)+FVector(1000,-700,200),false,nullptr,ETeleportType::TeleportPhysics);
    }
    M->SetCrouchedHalfHeight(MoatOldCrouchHalf);P->UnCrouch();M->UnCrouch(false);
    if(P->IsCrouched())return false;
    C->SetCapsuleRadius(MoatOldRadius);M->GravityScale=MoatOldGravity;M->AirControl=MoatOldAirControl;
    M->FallingLateralFriction=MoatOldFriction;M->SetMovementMode(MOVE_Falling);bMoatPosture=false;bMoatDiveWish=false;
    return true;
}
void USoraFieldcraft::ClearMoat()
{
    RestoreMoatPosture(true);
    MoatSpace=nullptr;bMoatPosture=bMoatDiveWish=bMoatGateCrossed=bMoatAlarm=false;
    MoatClockMs=MoatGuidePoint=0;MoatGuards.Reset();MoatPace=Moat::SurfaceSpeed;
}
void USoraFieldcraft::TickMoatWater(int32 DtMs)
{
    auto* P=Hero();if(!MoatSpace||!P||DtMs<=0)return;
    const float Dt=DtMs/1000.f;MoatClockMs=FMath::Min(MoatClockMs+DtMs,3600000);
    auto* M=P->GetCharacterMovement();auto* C=P->GetCapsuleComponent();
    FVector At=P->GetActorLocation(),Local=At-FVector(MoatSpace->Origin,0);
    FCollisionQueryParams Q(SCENE_QUERY_STAT(MoatBed),false,P);
    for(auto& Ally:Allies)if(IsValid(Ally))Q.AddIgnoredActor(Ally);
    FHitResult Floor;
    const bool Bed=GetWorld()->LineTraceSingleByChannel(Floor,At,At-FVector(0,0,1000),ECC_WorldStatic,Q);
    const bool Wet=Moat::Water(Local.X,Local.Y)&&Bed&&Floor.ImpactPoint.Z<-90&&At.Z-C->GetScaledCapsuleHalfHeight()<=12;
    const bool WasSwimming=bSwimming;
    bSwimming=Wet;
    if(Wet&&!bMoatPosture)
    {
        MoatOldRadius=C->GetUnscaledCapsuleRadius();MoatOldCrouchHalf=M->GetCrouchedHalfHeight();
        MoatOldGravity=M->GravityScale;MoatOldAirControl=M->AirControl;MoatOldFriction=M->FallingLateralFriction;
        bMoatDiveWish=false;bMoatPosture=true;
        if(auto* Kit=P->GetEquipment())Kit->Halt();P->StopSprint();
        C->SetCapsuleRadius(Moat::Radius);M->SetCrouchedHalfHeight(Moat::HalfHeight);P->Crouch();M->Crouch(false);
        MoatLast=P->GetActorLocation();
    }
    if(Wet)
    {
        M->GravityScale=0;M->AirControl=1;M->FallingLateralFriction=8;M->SetMovementMode(MOVE_Falling);
        M->bWantsToCrouch=true;M->Velocity.Z=0;
        At=P->GetActorLocation();
        const float Target=FMath::Max(float(bMoatDiveWish?Moat::DiveCenter:Moat::SurfaceCenter),Floor.ImpactPoint.Z+C->GetScaledCapsuleHalfHeight()+2);
        const float Vertical=FMath::Clamp((Target-At.Z)/Dt,-70.f,70.f);
        const float Speed=Moat::Submerged(At.Z)||bMoatDiveWish?Moat::DiveSpeed:Moat::SurfaceSpeed;
        MoatPace=FMath::Sqrt(FMath::Max(0.f,Speed*Speed-Vertical*Vertical));
        const FVector XY(M->Velocity.X,M->Velocity.Y,0);M->Velocity=XY.GetClampedToMaxSize(MoatPace);
        FHitResult Hit;P->SetActorLocation(At+FVector(0,0,Vertical*Dt),true,&Hit);
    }
    else if(bMoatPosture)
    {
        // On the bank, ordinary falling/walking raises the compact capsule
        // until there is physical room to restore the standing body.
        M->GravityScale=MoatOldGravity;M->AirControl=MoatOldAirControl;M->FallingLateralFriction=MoatOldFriction;
        RestoreMoatPosture(false);
    }
    At=P->GetActorLocation();Local=At-FVector(MoatSpace->Origin,0);
    bDiving=Wet&&Moat::Submerged(At.Z);
    const int32 Damage=SoraFieldcraftRules::Breathe(Breath,Staged->Water.Rules,bDiving,DtMs);
    const FVector Before=MoatLast-FVector(MoatSpace->Origin,0);
    if(bSwimming&&Moat::GateCrossed(Before.X,Before.Y,Before.Z,Local.X,Local.Y,Local.Z,FVector::Dist(At,MoatLast),Dt))bMoatGateCrossed=true;
    MoatLast=At;
    for(int32 I=0;I<Staged->Water.Lines.Num();++I)
    {
        const bool In=Wet&&Staged->Water.Lines[I].Contains(At);
        if(In&&MoatDepth()<=MoatSpace->FloatClearDepthCm&&!LinesTouched.Contains(I))
        {
            LinesTouched.Add(I);
            if(const auto* S=USoraStealth::Get(this))S->MakeNoise(SoraStealthRules::ENoise::Lure,At,At,P);
            Raise(TEXT("ai_event:float_line"));if(!MoatSpace)return;
        }
        else if(!In)LinesTouched.Remove(I);
    }
    if(WasSwimming!=bSwimming){Raise(bSwimming?TEXT("water_enter"):TEXT("water_leave"));if(!MoatSpace)return;}
    if(Damage>0){FHitResult H;H.ImpactPoint=H.Location=At;SoraDamage::Strike(P,Damage,FSoraHit::Hazard(At),FVector::UpVector,H,nullptr,nullptr);}
}
int32 USoraFieldcraft::MoatFootstepPermille(const FVector& Feet) const
{
    if(!MoatSpace||!bSwimming||!Hero()||FVector::Dist2D(Feet,Hero()->GetActorLocation())>100)return -1;
    return MoatDepth()>0?0:Staged->Water.SurfaceStepPermille;
}
bool USoraFieldcraft::MoatObjective(FVector& At) const
{
    if(!MoatSpace)return false;
    At=FVector(MoatSpace->Origin,0)+(bMoatGateCrossed?FVector(20800,4000,-6):FVector(20800,3400,-150));return true;
}

bool USoraFieldcraft::MoveMoatCompanion(ASoraCompanion& Companion,float Dt)
{
    if(!MoatSpace||Companion.CompanionId()!=TEXT("npc_kohagi"))return false;
    // A lead across the reed-side route, beneath the float line, then to the
    // old gate. Only capsule sweeps advance a waypoint; the hero's position
    // cannot relocate the guide or grant the player's gate crossing.
    const FVector Points[]={{2000,200,-6},{8000,200,-6},{12950,200,-6},{12950,200,-150},
        {13450,200,-150},{13450,200,-6},{20000,200,-6},{20800,2800,-6},{20800,3350,-6}};
    const FVector O(MoatSpace->Origin,0),At=Companion.GetActorLocation();
    auto* M=Companion.GetCharacterMovement();M->StopMovementImmediately();M->SetMovementMode(MOVE_Flying);
    if(MoatGuidePoint>=UE_ARRAY_COUNT(Points))return true;
    const FVector Goal=O+Points[MoatGuidePoint],Delta=Goal-At;
    FHitResult Hit;Companion.SetActorLocation(At+Delta.GetClampedToMaxSize(140.f*Dt),true,&Hit);
    if(FVector::Dist(Companion.GetActorLocation(),Goal)<2)++MoatGuidePoint;
    if(!Delta.IsNearlyZero())Companion.SetActorRotation(FRotator(0,Delta.Rotation().Yaw,0));
    return true;
}
void USoraFieldcraft::AssignMoatGuard(ASoraEnemy& Enemy,int32 Index)
{
    if(!MoatSpace)return;MoatGuards.Add(&Enemy,Index);
    if(Index>=3)
        if(auto* Brain=Cast<ASoraEnemyController>(Enemy.GetController()))
        {
            // Reinforcements are finite-search parapet guards. A generic
            // wave hunter receives omniscient relay updates and could never
            // be evaded by the authored dive/cover/20s search route.
            FSoraPatrolRoute Route;Route.Points.Add(Enemy.GetActorLocation());Brain->BeginPatrol(Route);
            if(bMoatAlarm)Brain->Rouse(MoatAlarmAt);
        }
}
bool USoraFieldcraft::IsMoatGuard(const ASoraEnemy& Enemy) const
{ return MoatSpace&&MoatGuards.Contains(TWeakObjectPtr<ASoraEnemy>(const_cast<ASoraEnemy*>(&Enemy))); }
void USoraFieldcraft::MoatDetected(const FVector& Evidence)
{ if(MoatSpace){bMoatAlarm=true;MoatAlarmAt=Evidence;} }
FVector USoraFieldcraft::MoatGuardAim(const ASoraEnemy& Enemy) const
{
    if(!MoatSpace)return Enemy.GetActorLocation()+Enemy.GetActorForwardVector()*1000;
    const auto* Brain=Cast<ASoraEnemyController>(Enemy.GetController());
    if(Brain&&(Brain->State()==SoraStealthRules::EState::Combat||Brain->State()==SoraStealthRules::EState::Alert))return Brain->LastKnownLocation();
    const FVector At=Enemy.GetActorLocation();
    return Enemy.ArchetypeId()==TEXT("drone")?At-FVector(0,0,1000):FVector(At.X,MoatSpace->Origin.Y+2800,0);
}
bool USoraFieldcraft::DriveMoatGuard(ASoraEnemy& Enemy,float Dt,bool& Reached)
{
    const int32* Index=MoatGuards.Find(&Enemy);if(!MoatSpace||!Index)return false;
    const FVector O(MoatSpace->Origin,0);auto* M=Enemy.GetCharacterMovement();
    const auto* Brain=Cast<ASoraEnemyController>(Enemy.GetController());
    const bool Combat=Brain&&(Brain->State()==SoraStealthRules::EState::Combat||Brain->State()==SoraStealthRules::EState::Alert);
    const bool Investigating=Brain&&Brain->State()==SoraStealthRules::EState::Alert;
    Reached=false;FVector Goal=Enemy.GetActorLocation();
    if(*Index==2)
    {
        // Authored figure-eight extents and altitude; constant-speed legs are
        // provisional timing. The alarm physically descends to three metres.
        const FVector2D Points[]={{4000,1800},{7500,2800},{11000,1800},{14500,800},{18000,1800},{14500,2800},{11000,1800},{7500,800},{4000,1800}};
        constexpr float Leg=3640.055f;
        const float Along=FMath::Fmod(MoatClockMs*.30f,8*Leg)/Leg;
        const int32 I=FMath::Min(7,FMath::FloorToInt(Along));
        Goal=O+FVector(FMath::Lerp(Points[I],Points[I+1],Along-I),bMoatAlarm?300.f:600.f);
        if(Investigating) { Goal.X=Brain->LastKnownLocation().X;Goal.Y=Brain->LastKnownLocation().Y; }
        M->SetMovementMode(MOVE_Flying);
    }
    else
    {
        const float Start=*Index==0?3000.f:*Index==1?11000.f:*Index==3?19000.f:20500.f;
        const float End=*Index==0?10000.f:*Index==1?19000.f:Start+500.f;
        const float Length=End-Start,Along=FMath::Fmod(MoatClockMs*.16f,Length*2);
        const float X=Investigating?FMath::Clamp(float(Brain->LastKnownLocation().X-O.X),Start,End):Start+(Along<=Length?Along:Length*2-Along);
        Goal=O+FVector(X,Moat::ParapetY,Moat::ParapetWalk+Enemy.GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2);
    }
    if(!Combat||Investigating||*Index==2)
    {
        M->StopMovementImmediately();const FVector Delta=Goal-Enemy.GetActorLocation();
        FHitResult Hit;Enemy.SetActorLocation(Enemy.GetActorLocation()+Delta.GetClampedToMaxSize(300.f*Dt),true,&Hit);
    }
    else M->StopMovementImmediately();
    // Feed ordinary perception its actual investigation arrival. Without
    // this geometry-backed receipt an Alert guard could never begin Search.
    if(Investigating)Reached=FVector::Dist(Enemy.GetActorLocation(),Goal)<12;
    const FVector Aim=MoatGuardAim(Enemy);Enemy.SetActorRotation(FRotator(0,(Aim-Enemy.GetActorLocation()).Rotation().Yaw,0));
    if(Combat&&Brain&&Brain->SeesHero()&&Hero())Enemy.TryAttack(*Hero(),FVector::Dist(Enemy.GetActorLocation(),Hero()->GetActorLocation()));
    return true;
}
