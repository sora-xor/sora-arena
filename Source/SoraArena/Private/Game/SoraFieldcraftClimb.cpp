#include "SoraFieldcraft.h"
#include "SoraClimbRules.h"
#include "SoraCompanion.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "SoraEquipmentComponent.h"
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
bool SweepFeet(ASoraPlayerCharacter& P,const FVector& To,FHitResult& Hit)
{
    Hit=FHitResult();
    P.SetActorLocation(To+FVector(0,0,P.GetCapsuleComponent()->GetScaledCapsuleHalfHeight()),true,&Hit);
    P.GetCharacterMovement()->Velocity=FVector::ZeroVector;
    const FVector Reached=Feet(P);
    // Flat support contact may retain the engine's small floor separation.
    // Neither a lateral obstruction nor the underside of a shelf qualifies.
    return !Hit.bBlockingHit||SoraClimbRules::AtSupport(Hit.bStartPenetrating,Hit.Normal.Z,Hit.ImpactNormal.Z,
        FVector::Dist2D(Reached,To),Reached.Z-To.Z);
}
}

const FSoraClimbRoute* USoraFieldcraft::CurrentClimbRoute() const
{ return !ClimbSpace||ClimbRoute==INDEX_NONE?nullptr:ClimbRoute==0?&ClimbSpace->Corner:&ClimbSpace->Extrusion; }

FString USoraFieldcraft::ClimbDiagnostic() const
{
    const FVector O=ClimbSpace?FVector(ClimbSpace->Origin,0):FVector::ZeroVector;
    const auto HitText=[](const FHitResult& Hit)
    {
        return FString::Printf(TEXT("blocking=%d penetrating=%d actor=%s component=%s normal=%s impact_normal=%s time=%.6f depth=%.4f location=%s impact=%s"),
            Hit.bBlockingHit,Hit.bStartPenetrating,*GetNameSafe(Hit.GetActor()),*GetNameSafe(Hit.GetComponent()),
            *Hit.Normal.ToString(),*Hit.ImpactNormal.ToString(),Hit.Time,Hit.PenetrationDepth,*Hit.Location.ToString(),*Hit.ImpactPoint.ToString());
    };
    FString Out=FString::Printf(TEXT("origin=%s clock=%d route=%d hold=%d step=%d alpha=%.6f climbing=%d falling=%d mounting=%d top=%d crawl=%d crawl_wish=%d entered=%d exited=%d grip_milli=%d step_start=%s last_from=%s last_wanted=%s last_accepted=%d last_hit={%s}"),
        *O.ToString(),ClimbClockMs,ClimbRoute,Grip.Hold,ClimbStepTarget,ClimbStepAlpha,bClimbing,bFalling,bClimbMounting,bClimbReachedTop,
        bClimbCrawl,bClimbCrawlWish,bClimbCrawlEntered,bClimbCrawled,Grip.GripMilli,*ClimbStepStart.ToString(),
        *(ClimbSweepFrom-O).ToString(),*(ClimbSweepWanted-O).ToString(),bClimbSweepAccepted,*HitText(ClimbSweepHit));
    Out+=FString::Printf(TEXT(" fall_initialized=%d fall_airborne=%d fall_last_feet_z=%.4f fall_peak_z=%.4f"),
        ClimbFall.Initialized,ClimbFall.Airborne,ClimbFall.LastFeetZ,ClimbFall.PeakZ);
    if(const auto* P=Hero())
    {
        const auto* Move=P->GetCharacterMovement();
        Out+=FString::Printf(TEXT(" hero_feet=%s hero_center=%s velocity=%s mode=%d custom=%d forward_axis=%.4f right_axis=%.4f can_play=%d alive=%d crouched=%d wants_crouch=%d half=%.3f radius=%.3f floor={%s}"),
            *(SoraClimbRuntime::Feet(*P)-O).ToString(),*P->GetActorLocation().ToString(),*Move->Velocity.ToString(),int32(Move->MovementMode),int32(Move->CustomMovementMode),
            P->GetInputAxisValue(TEXT("MoveForward")),P->GetInputAxisValue(TEXT("MoveRight")),P->CanPlay(),P->IsAlive(),P->IsCrouched(),Move->bWantsToCrouch,
            P->GetCapsuleComponent()->GetScaledCapsuleHalfHeight(),P->GetCapsuleComponent()->GetScaledCapsuleRadius(),*HitText(Move->CurrentFloor.HitResult));
    }
    if(ClimbGuide.IsValid())
    {
        const auto* G=ClimbGuide.Get();const auto* Move=G->GetCharacterMovement();const float Half=G->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
        const FVector Goal=ClimbGuidePath.IsValidIndex(ClimbGuidePoint)?ClimbGuidePath[ClimbGuidePoint]:FVector::ZeroVector;
        Out+=FString::Printf(TEXT(" guide_feet=%s guide_target=%s guide_point=%d/%d guide_wait=%d guide_mode=%d guide_velocity=%s guide_half=%.3f guide_radius=%.3f guide_vertical={%s} guide_horizontal={%s}"),
            *(G->GetActorLocation()-O-FVector(0,0,Half)).ToString(),*Goal.ToString(),ClimbGuidePoint,ClimbGuidePath.Num(),bClimbGuideWaiting,
            int32(Move->MovementMode),*Move->Velocity.ToString(),Half,G->GetCapsuleComponent()->GetScaledCapsuleRadius(),*HitText(ClimbGuideVerticalHit),*HitText(ClimbGuideHorizontalHit));
    }
    if(ClimbSentry.IsValid())
        Out+=FString::Printf(TEXT(" sentry_center=%s sentry_goal=%s sentry_mode=%d watching=%d aim=%s sentry_hit={%s}"),
            *(ClimbSentry->GetActorLocation()-O).ToString(),*(ClimbSentryMoveGoal-O).ToString(),int32(ClimbSentry->GetCharacterMovement()->MovementMode),
            ClimbSentryWatching(),*(ClimbSentryAim()-O).ToString(),*HitText(ClimbSentryMoveHit));
    return Out;
}

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
    if(auto* Kit=Player.GetEquipment()) Kit->Halt();
    ClimbRoute=Route;Grip=SoraFieldcraftRules::StartClimb();ClimbStepTarget=0;ClimbStepAlpha=0;
    ClimbFall=SoraClimbRules::FallAt(SoraClimbRuntime::Feet(Player).Z);
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
    if(ClimbGuide.IsValid())
    { ClimbGuide->GetCharacterMovement()->StopMovementImmediately();ClimbGuide->GetCharacterMovement()->SetMovementMode(MOVE_Walking); }
    ClimbGuide.Reset();ClimbGuidePath.Reset();ClimbGuidePoint=0;bClimbGuideWaiting=false;
    ClimbFall={};
    ClimbSweepHit=ClimbGuideVerticalHit=ClimbGuideHorizontalHit=ClimbSentryMoveHit=FHitResult();
    ClimbSweepFrom=ClimbSweepWanted=ClimbSentryMoveGoal=FVector::ZeroVector;bClimbSweepAccepted=false;
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

bool USoraFieldcraft::MoveClimbCompanion(ASoraCompanion& Companion,float Dt)
{
    if(!ClimbSpace||Companion.CompanionId()!=TEXT("npc_kohagi")) return false;
    const FVector O(ClimbSpace->Origin,0);
    if(!ClimbGuide.IsValid())
    {
        ClimbGuide=&Companion;
        // She starts at the real foot and demonstrates the same corner
        // holds, including the collision-safe approach outside each shelf.
        for(int32 H=1;H<ClimbSpace->Corner.Points.Num();++H)
        {
            const FVector Point=ClimbSpace->Corner.Points[H];
            if(ClimbSpace->Corner.RestHolds.Contains(H+1))
                ClimbGuidePath.Add(FVector(Point.X,Point.Y,ClimbSpace->Corner.Points[H-1].Z));
            if(ClimbSpace->Corner.RestHolds.Contains(H))
            {
                ClimbGuidePath.Add(Point+FVector(-210,0,SoraClimbRules::SupportLiftCm));
                ClimbGuidePath.Add(Point+FVector(0,0,SoraClimbRules::SupportLiftCm));
            }
            ClimbGuidePath.Add(Point);
        }
        ClimbGuidePath.Add(ClimbSpace->Corner.Points.Last()+FVector(0,0,SoraClimbRules::SupportLiftCm));
        ClimbGuidePath.Add(FVector(650,70,1600+SoraClimbRules::SupportLiftCm));
        // Provisional route around the turret's outside wall, then over its
        // roof edge. Every segment is swept against the actual shell.
        for(const auto& Point:SoraClimbRules::GuideRoofPath)
            ClimbGuidePath.Add(FVector(Point.X,Point.Y,Point.Z));
    }
    auto* Move=Companion.GetCharacterMovement();Move->StopMovementImmediately();
    if(bClimbGuideWaiting) { Move->SetMovementMode(MOVE_Walking);return true; }
    Move->SetMovementMode(MOVE_Flying);
    const float Half=Companion.GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    const FVector Target=O+ClimbGuidePath[ClimbGuidePoint]+FVector(0,0,Half);
    const bool Final=ClimbGuidePoint==ClimbGuidePath.Num()-1;
    // The final bounded downward sweep crosses the nominal support plane
    // so an endpoint merely tangent to the roof cannot masquerade as a hit.
    const FVector SweepTarget=Target-(Final?FVector(0,0,SoraClimbRules::SupportLiftCm):FVector::ZeroVector);
    const FVector Delta=SweepTarget-Companion.GetActorLocation();
    const FVector Step=Delta.GetClampedToMaxSize(SoraClimbRules::GuideSpeed*Dt);
    // Resolve vertical support first so a floor contact cannot consume the
    // sideways part of the same bounded step across a shelf or parapet.
    ClimbGuideVerticalHit=ClimbGuideHorizontalHit=FHitResult();
    Companion.SetActorLocation(Companion.GetActorLocation()+FVector(0,0,Step.Z),true,&ClimbGuideVerticalHit);
    Companion.SetActorLocation(Companion.GetActorLocation()+FVector(Step.X,Step.Y,0),true,&ClimbGuideHorizontalHit);
    if(!Delta.IsNearlyZero()) Companion.SetActorRotation(FRotator(0,Delta.Rotation().Yaw,0));
    // A collision may stop at the normal floor-contact separation. Only
    // actual proximity advances a waypoint; a remote blocker never does.
    const FVector Reached=Companion.GetActorLocation();
    // The final waypoint lowers onto the roof. Waiting requires a real top
    // contact; proximity to the raised crossing point alone is insufficient.
    const bool Supported=ClimbGuideVerticalHit.bBlockingHit&&SoraClimbRules::AtSupport(
        ClimbGuideVerticalHit.bStartPenetrating,ClimbGuideVerticalHit.Normal.Z,ClimbGuideVerticalHit.ImpactNormal.Z,
        FVector::Dist2D(Reached,Target),Reached.Z-Target.Z);
    if(FVector::Dist(Reached,Target)<=3.f&&(!Final||Supported))
        if(++ClimbGuidePoint==ClimbGuidePath.Num())
        { bClimbGuideWaiting=true;Move->SetMovementMode(MOVE_Walking);Companion.SetActorRotation(FRotator(0,180,0)); }
    return true;
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
    if(auto* Kit=Player.GetEquipment()) Kit->Halt();
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
    const auto Rules=SoraClimbRules::GripRules(ClimbRoute==1);
    const int32 Drop=SoraClimbRules::SampleFall(ClimbFall,SoraClimbRuntime::Feet(*P).Z,bClimbing,
        Move->IsMovingOnGround(),Move->IsFalling());
    bFalling=ClimbFall.Airborne;
    const int32 Damage=SoraFieldcraftRules::FallDamage(Rules,Drop);
    if(Damage!=0)
    {
        FHitResult Hit;Hit.ImpactPoint=P->GetActorLocation();Hit.Location=Hit.ImpactPoint;
        SoraDamage::Strike(P,Damage<0?P->Health+1000.f:float(Damage),FSoraHit::Hazard(Hit.Location),FVector::UpVector,Hit,nullptr,nullptr);
    }
    const auto* R=CurrentClimbRoute();if(!R) return;
    if(!bClimbing||!P->IsAlive()) return;
    const float Up=FMath::Clamp(P->GetInputAxisValue(TEXT("MoveForward")),-1.f,1.f);
    if(ClimbStepTarget==INDEX_NONE)
    {
        if(FMath::Abs(Up)<.2f) { SoraFieldcraftRules::Rest(Grip,Rules,DtMs);return; }
        bClimbMounting=Grip.Hold==R->Points.Num()-1&&Up>0;
        const int32 Next=bClimbMounting?Grip.Hold:FMath::Clamp(Grip.Hold+(Up>0?1:-1),0,R->Points.Num()-1);
        if(Next==Grip.Hold&&!bClimbMounting) return;
        // A shot may begin on a stationary rest. Taking the next hold needs
        // both hands and must cancel that held action before release can fire.
        if(auto* Kit=P->GetEquipment()) Kit->Halt();
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
    SoraClimbRules::EHoldPath Path=bClimbMounting?SoraClimbRules::EHoldPath::Mount:SoraClimbRules::EHoldPath::Direct;
    // Approach a real rest shelf around its outer lip, then move inward with
    // feet above its support; never phase a capsule through the shelf.
    if(!bClimbMounting&&R->RestHolds.Contains(ClimbStepTarget)&&ClimbStepTarget>Grip.Hold)
        Path=SoraClimbRules::EHoldPath::OntoRest;
    else if(!bClimbMounting&&R->RestHolds.Contains(Grip.Hold)&&ClimbStepTarget<Grip.Hold)
        Path=SoraClimbRules::EHoldPath::OffRest;
    else if(!bClimbMounting&&R->RestHolds.Contains(ClimbStepTarget+1)&&ClimbStepTarget>Grip.Hold)
        Path=SoraClimbRules::EHoldPath::BeforeRest;
    else if(!bClimbMounting&&R->RestHolds.Contains(Grip.Hold+1)&&ClimbStepTarget<Grip.Hold)
        Path=SoraClimbRules::EHoldPath::FromBeforeRest;
    // The capsule's upper hemisphere also needs clearance on the hold before
    // a shelf: get outside while low, then rise; reverse by lowering first.
    const auto Point=SoraClimbRules::HoldPath({ClimbStepStart.X,ClimbStepStart.Y,ClimbStepStart.Z},
        {Target.X,Target.Y,Target.Z},NextAlpha,Path);
    const FVector Wanted(Point.X,Point.Y,Point.Z);
    ClimbSweepFrom=SoraClimbRuntime::Feet(*P);ClimbSweepWanted=O+Wanted;
    bClimbSweepAccepted=SoraClimbRuntime::SweepFeet(*P,O+Wanted,ClimbSweepHit);
    if(!bClimbSweepAccepted) return;
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
    ClimbSentryMoveGoal=O+Goal;ClimbSentryMoveHit=FHitResult();
    Enemy.SetActorLocation(Enemy.GetActorLocation()+Facing.GetClampedToMaxSize(700.f*Dt),true,&ClimbSentryMoveHit);
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
