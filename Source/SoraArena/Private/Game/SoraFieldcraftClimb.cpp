#include "SoraFieldcraft.h"
#include "SoraClimbRules.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "SoraPlayerCharacter.h"
#include "Combat/SoraDamage.h"
#include "Components/CapsuleComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SpotLightComponent.h"
#include "Engine/PointLight.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"

namespace SoraClimbRuntime
{
FVector Feet(const ASoraPlayerCharacter& P)
{ return P.GetActorLocation()-FVector(0,0,P.GetCapsuleComponent()->GetScaledCapsuleHalfHeight()); }
bool SweepFeet(ASoraPlayerCharacter& P,const FVector& To)
{
    FHitResult Hit;
    P.SetActorLocation(To+FVector(0,0,P.GetCapsuleComponent()->GetScaledCapsuleHalfHeight()),true,&Hit);
    P.GetCharacterMovement()->Velocity=FVector::ZeroVector;
    return !Hit.bBlockingHit;
}
}

const FSoraClimbRoute* USoraFieldcraft::CurrentClimbRoute() const
{ return !ClimbSpace||ClimbRoute==INDEX_NONE?nullptr:ClimbRoute==0?&ClimbSpace->Corner:&ClimbSpace->Extrusion; }

bool USoraFieldcraft::AtClimbRoute(const ASoraPlayerCharacter& Player,int32& Route) const
{
    if(!ClimbSpace||bClimbReachedTop||!Player.GetCharacterMovement()->IsMovingOnGround()) return false;
    const FVector Local=SoraClimbRuntime::Feet(Player)-FVector(ClimbSpace->Origin,0);
    for(int32 I=0;I<2;++I)
    {
        const FVector Start=(I==0?ClimbSpace->Corner:ClimbSpace->Extrusion).Points[0];
        if(FMath::Abs(Local.Z-Start.Z)<15&&FVector::Dist2D(Local,Start)<115&&Player.GetActorForwardVector().X>.5f)
        { Route=I;return true; }
    }
    return false;
}
bool USoraFieldcraft::BeginClimbRoute(ASoraPlayerCharacter& Player)
{
    int32 Route=INDEX_NONE;if(!AtClimbRoute(Player,Route)) return false;
    ClimbRoute=Route;Grip=SoraFieldcraftRules::StartClimb();ClimbStepTarget=0;ClimbStepAlpha=0;
    ClimbStepStart=SoraClimbRuntime::Feet(Player)-FVector(ClimbSpace->Origin,0);
    bClimbing=true;bFalling=false;bClimbMounting=false;LedgesReached.Reset();Player.StopSprint();
    Player.GetCharacterMovement()->StopMovementImmediately();Player.GetCharacterMovement()->SetMovementMode(MOVE_Flying);
    Raise(TEXT("climb_start"));return true;
}
bool USoraFieldcraft::IsClimbResting() const
{
    const auto* R=CurrentClimbRoute();
    return R&&bClimbing&&ClimbStepTarget==INDEX_NONE&&R->RestHolds.Contains(Grip.Hold);
}
bool USoraFieldcraft::ClimbObjective(FVector& At) const
{
    if(!ClimbSpace) return false;
    At=FVector(ClimbSpace->Origin,0)+(bClimbReachedTop?FVector(1050,0,1650):ClimbSpace->Corner.Points[0]);return true;
}
void USoraFieldcraft::ClearClimbRoutes()
{
    if(bClimbCrawl)
        if(auto* P=Hero())
        {
            // Only checkpoint/beat teardown forces restoration. Normal play
            // waits for a collision-free standing capsule outside the gap.
            auto* Move=P->GetCharacterMovement();Move->SetCrouchedHalfHeight(ClimbOldCrouchHalf);
            P->UnCrouch();Move->UnCrouch(false);
            if(P->IsCrouched())
            {
                // A dying character may still be under the lintel. Teardown
                // relocates to the clear route entry before restoring size;
                // ordinary gap traversal never uses this reset path.
                P->SetActorLocation(FVector(ClimbSpace->Origin,0)+FVector(-400,70,90),false,nullptr,ETeleportType::TeleportPhysics);
                Move->UnCrouch(false);
            }
            P->GetCapsuleComponent()->SetCapsuleSize(ClimbOldRadius,88);
            P->SetIsCrouched(false);Move->bWantsToCrouch=false;
        }
    ClimbSpace=nullptr;ClimbRoute=ClimbStepTarget=INDEX_NONE;ClimbClockMs=0;ClimbStepAlpha=0;
    bClimbMounting=bClimbReachedTop=bClimbCrawl=bClimbCrawlWish=bClimbCrawled=bClimbCrawlEntered=bClimbWatchRaised=false;
    ClimbSentry.Reset();
    if(IsValid(ClimbSentryLamp)) ClimbSentryLamp->DestroyComponent();ClimbSentryLamp=nullptr;
    for(const auto& Light:ClimbStripLights) if(IsValid(Light)) Light->Destroy();ClimbStripLights.Reset();
}
bool USoraFieldcraft::ClimbCrouch(ASoraPlayerCharacter& Player)
{
    if(!ClimbSpace) return false;
    if(bClimbCrawl) { bClimbCrawlWish=!bClimbCrawlWish;return true; }
    const FVector P=SoraClimbRuntime::Feet(Player)-FVector(ClimbSpace->Origin,0);
    if(!bClimbReachedTop||!Player.GetCharacterMovement()->IsMovingOnGround()||
        P.X<1000||P.X>=ClimbSpace->CrawlEntryX||FMath::Abs(P.Y)>45||FMath::Abs(P.Z-1650)>18) return false;
    ClimbOldRadius=Player.GetCapsuleComponent()->GetUnscaledCapsuleRadius();
    ClimbOldCrouchHalf=Player.GetCharacterMovement()->GetCrouchedHalfHeight();
    Player.StopSprint();Player.GetCapsuleComponent()->SetCapsuleRadius(SoraClimbRules::CrawlRadius);
    Player.GetCharacterMovement()->SetCrouchedHalfHeight(SoraClimbRules::CrawlHalfHeight);
    Player.Crouch();bClimbCrawl=bClimbCrawlWish=true;bClimbCrawlEntered=false;
    // A normally crouched approach is already marked crouched, so the
    // movement tick will not call Crouch again merely because its configured
    // height changed. Apply the same CMC resize path explicitly here.
    Player.GetCharacterMovement()->Crouch(false);return true;
}

void USoraFieldcraft::TickClimbRoutes(float DeltaTime,int32 DtMs)
{
    auto* P=Hero();if(!P||!ClimbSpace) return;
    ClimbClockMs+=DtMs;
    const bool Watch=ClimbSentryWatching();
    if(Watch&&!bClimbWatchRaised) Raise(TEXT("ai_event:sentry_lookdown"));
    bClimbWatchRaised=Watch;
    if(!ClimbSpace) return; // dialogue callbacks may leave this stage
    auto* Move=P->GetCharacterMovement();const FVector O(ClimbSpace->Origin,0);
    if(bClimbCrawl)
    {
        const FVector At=SoraClimbRuntime::Feet(*P)-O;
        const bool InGap=At.X>ClimbSpace->CrawlEntryX-40&&At.X<ClimbSpace->CrawlExitX+40;
        if(P->IsCrouched()&&At.X>ClimbSpace->CrawlEntryX+30&&At.X<ClimbSpace->CrawlExitX&&FMath::Abs(At.Y)<32)
            bClimbCrawlEntered=true;
        if(!bClimbCrawled&&bClimbCrawlEntered&&At.X>ClimbSpace->CrawlExitX+35&&P->IsCrouched()&&FMath::Abs(At.Y)<32)
        { bClimbCrawled=true;Raise(Staged->Climb.TopEvent);if(!ClimbSpace) return; }
        // A released/toggled wish inside never expands collision into stone.
        if(InGap) Move->bWantsToCrouch=true;
        if(!InGap&&(!bClimbCrawlWish||bClimbCrawled||At.X<1000||FMath::Abs(At.Y)>100||FMath::Abs(At.Z-1650)>80))
        {
            FCollisionQueryParams Q(SCENE_QUERY_STAT(ClimbCrawlHeadroom),false,P);
            const FVector Standing=O+At+FVector(0,0,88);
            if(!GetWorld()->OverlapBlockingTestByChannel(Standing,FQuat::Identity,ECC_Pawn,FCollisionShape::MakeCapsule(ClimbOldRadius,88),Q))
            { Move->SetCrouchedHalfHeight(ClimbOldCrouchHalf);P->UnCrouch();Move->UnCrouch(false);bClimbCrawl=P->IsCrouched(); }
        }
    }
    const auto* R=CurrentClimbRoute();if(!R) return;
    const auto Rules=SoraClimbRules::GripRules(ClimbRoute==1);
    if(bFalling&&!bClimbing&&Move->IsMovingOnGround())
    {
        bFalling=false;
        const int32 Damage=SoraFieldcraftRules::FallDamage(Rules,FMath::RoundToInt32(FallFromZ-P->GetActorLocation().Z));
        if(Damage!=0)
        { FHitResult Hit;Hit.ImpactPoint=P->GetActorLocation();Hit.Location=Hit.ImpactPoint;
          SoraDamage::Strike(P,Damage<0?P->Health+1000.f:float(Damage),FSoraHit::Hazard(Hit.Location),FVector::UpVector,Hit,nullptr,nullptr); }
    }
    if(!bClimbing||!P->IsAlive()) return;
    const float Up=FMath::Clamp(P->GetInputAxisValue(TEXT("MoveForward")),-1.f,1.f);
    if(ClimbStepTarget==INDEX_NONE)
    {
        if(FMath::Abs(Up)<.2f) { SoraFieldcraftRules::Rest(Grip,Rules,DtMs);return; }
        bClimbMounting=Grip.Hold==R->Points.Num()-1&&Up>0;
        const int32 Next=bClimbMounting?Grip.Hold:FMath::Clamp(Grip.Hold+(Up>0?1:-1),0,R->Points.Num()-1);
        if(Next==Grip.Hold&&!bClimbMounting) return;
        ClimbStepStart=SoraClimbRuntime::Feet(*P)-O;ClimbStepTarget=Next;ClimbStepAlpha=0;
    }
    // Releasing forward pauses at the actual point; no hold or paused time is
    // credited. Both directions use the same mapped axis and swept capsule.
    if(FMath::Abs(Up)<.2f&&ClimbStepTarget!=0) return;
    const bool Forward=bClimbMounting||ClimbStepTarget>=Grip.Hold;
    const float Direction=ClimbStepTarget==0&&Grip.Hold==0?1.f:(Up>0)==Forward?1.f:-1.f;
    const float NextAlpha=FMath::Clamp(ClimbStepAlpha+Direction*DeltaTime*1000.f/R->StepMs,0.f,1.f);
    FVector Target=R->Points[ClimbStepTarget];
    if(bClimbMounting) Target=FVector(650,R->Points.Last().Y,1600);
    FVector Wanted=FMath::Lerp(ClimbStepStart,Target,NextAlpha);
    // Approach a real rest shelf around its outer lip, then move inward with
    // feet above its support; never phase a capsule through the shelf.
    if(!bClimbMounting&&R->RestHolds.Contains(ClimbStepTarget)&&ClimbStepTarget>Grip.Hold)
    {
        const FVector Outside(Target.X-210,Target.Y,Target.Z);
        Wanted=NextAlpha<.8f?FMath::Lerp(ClimbStepStart,Outside,NextAlpha/.8f):FMath::Lerp(Outside,Target,(NextAlpha-.8f)/.2f);
    }
    else if(!bClimbMounting&&R->RestHolds.Contains(Grip.Hold)&&ClimbStepTarget<Grip.Hold)
    {
        const FVector Outside(ClimbStepStart.X-210,ClimbStepStart.Y,ClimbStepStart.Z);
        Wanted=NextAlpha<.2f?FMath::Lerp(ClimbStepStart,Outside,NextAlpha/.2f):FMath::Lerp(Outside,Target,(NextAlpha-.2f)/.8f);
    }
    if(!SoraClimbRuntime::SweepFeet(*P,O+Wanted)) return;
    ClimbStepAlpha=NextAlpha;
    if(NextAlpha==0&&Direction<0) { ClimbStepTarget=INDEX_NONE;bClimbMounting=false;return; }
    if(NextAlpha<1) return;
    if(bClimbMounting)
    { bClimbMounting=false;bClimbing=false;bClimbReachedTop=true;ClimbStepTarget=INDEX_NONE;Move->SetMovementMode(MOVE_Walking);Raise(TEXT("climb_top"));return; }
    if(ClimbStepTarget!=Grip.Hold)
    {
        const auto Reached=SoraFieldcraftRules::Reach(Grip,Rules,ClimbStepTarget>Grip.Hold?1:-1);
        if(Reached==SoraFieldcraftRules::EReach::Fell) { LetGo(*P,true);return; }
        if(Reached==SoraFieldcraftRules::EReach::Top)
        { bClimbMounting=true;ClimbStepStart=Target;ClimbStepAlpha=0;return; }
        if(Reached==SoraFieldcraftRules::EReach::Ground)
        { bClimbing=false;Move->SetMovementMode(MOVE_Walking); }
        const int32 Ledge=R->RestHolds.Find(Grip.Hold);
        if(Ledge!=INDEX_NONE&&!LedgesReached.Contains(Ledge))
        { LedgesReached.Add(Ledge);Raise(FString::Printf(TEXT("volume_enter:vol_rest_ledge_%d"),Ledge+1)); }
    }
    ClimbStepTarget=INDEX_NONE;
}

void USoraFieldcraft::AssignClimbSentry(ASoraEnemy& Enemy)
{
    if(!ClimbSpace) return;
    ClimbSentry=&Enemy;Enemy.EnableClimbSentry();
    ClimbSentryLamp=NewObject<USpotLightComponent>(&Enemy,TEXT("YaguraLookdownLamp"));
    ClimbSentryLamp->SetupAttachment(Enemy.GetRootComponent());ClimbSentryLamp->SetRelativeLocation(FVector(0,0,50));
    ClimbSentryLamp->SetMobility(EComponentMobility::Movable);ClimbSentryLamp->SetIntensity(2500);
    ClimbSentryLamp->SetAttenuationRadius(1800);ClimbSentryLamp->SetInnerConeAngle(22);ClimbSentryLamp->SetOuterConeAngle(30);
    ClimbSentryLamp->RegisterComponent();Enemy.AddInstanceComponent(ClimbSentryLamp);
    for(int32 Z:{600,1000,1400})
        if(auto* Light=GetWorld()->SpawnActor<APointLight>(FVector(ClimbSpace->Origin,0)+FVector(SoraClimbRules::WallX(Z)-100,-1000,Z),FRotator::ZeroRotator))
        { Light->SetMobility(EComponentMobility::Movable);Light->PointLightComponent->SetAttenuationRadius(450);
          Light->PointLightComponent->SetIntensity(1800);Light->PointLightComponent->SetLightColor(FLinearColor(.2f,.9f,1));ClimbStripLights.Add(Light); }
}
bool USoraFieldcraft::IsClimbSentry(const ASoraEnemy& Enemy) const { return ClimbSpace&&ClimbSentry.Get()==&Enemy; }
bool USoraFieldcraft::ClimbSentryWatching() const
{
    return ClimbSpace&&ClimbSentry.IsValid()&&ClimbSentry->IsAlive()&&SoraClimbRules::Watching(ClimbClockMs)&&
        FVector::Dist2D(ClimbSentry->GetActorLocation(),FVector(ClimbSpace->Origin,0)+FVector(360,-300,1690))<55;
}
FVector USoraFieldcraft::ClimbSentryAim() const
{
    if(!ClimbSpace) return FVector::ForwardVector;
    const FVector Targets[]={ClimbSpace->Corner.Points[9],ClimbSpace->Corner.Points.Last(),
        ClimbSpace->Extrusion.Points.Last(),ClimbSpace->Extrusion.Points[4]};
    const float Along=FMath::Clamp(float(ClimbClockMs%20000)/4000.f*3,0.f,3.f);
    const int32 I=FMath::Min(2,FMath::FloorToInt(Along));
    return FVector(ClimbSpace->Origin,0)+FMath::Lerp(Targets[I],Targets[I+1],Along-I)+FVector(0,0,88);
}
bool USoraFieldcraft::DriveClimbSentry(ASoraEnemy& Enemy,float Dt)
{
    if(!IsClimbSentry(Enemy)) return false;
    const FVector O(ClimbSpace->Origin,0),Bay(360,-300,1690);
    const auto* Brain=Cast<ASoraEnemyController>(Enemy.GetController());
    const bool Combat=Brain&&(Brain->State()==SoraStealthRules::EState::Combat||Brain->State()==SoraStealthRules::EState::Alert);
    const bool Watch=SoraClimbRules::Watching(ClimbClockMs);
    FVector Goal=Bay;
    if(Combat&&Enemy.GetActorLocation().X-O.X>500&&FMath::Abs(Enemy.GetActorLocation().Y-O.Y+300)>3)
        Goal=FVector(650,-300,1690);
    if(!Watch&&!Combat)
    {
        const auto Point=SoraClimbRules::PatrolAt(ClimbClockMs);
        Goal=FVector(Point.X,Point.Y,1690);
    }
    auto* Move=Enemy.GetCharacterMovement();Move->StopMovementImmediately();
    FVector Facing=(O+Goal-Enemy.GetActorLocation());
    FHitResult Hit;Enemy.SetActorLocation(Enemy.GetActorLocation()+Facing.GetClampedToMaxSize(700.f*Dt),true,&Hit);
    if(ClimbSentryWatching()) Facing=ClimbSentryAim()-Enemy.GetActorLocation();
    if(Combat&&Hero()) Facing=Hero()->GetActorLocation()-Enemy.GetActorLocation();
    if(!Facing.IsNearlyZero()) Enemy.SetActorRotation(FRotator(0,Facing.Rotation().Yaw,0));
    if(ClimbSentryLamp)
    {
        const FVector Aim=Combat&&Hero()?Hero()->GetActorLocation():ClimbSentryWatching()?ClimbSentryAim():Enemy.GetActorLocation()+Enemy.GetActorForwardVector()*1000;
        ClimbSentryLamp->SetWorldRotation((Aim-ClimbSentryLamp->GetComponentLocation()).Rotation());
    }
    if(Combat&&Brain&&Brain->SeesHero()&&Hero()) Enemy.TryAttack(*Hero(),FVector::Dist(Enemy.GetActorLocation(),Hero()->GetActorLocation()));
    return true;
}
