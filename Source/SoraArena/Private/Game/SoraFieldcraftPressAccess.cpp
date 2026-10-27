#include "SoraFieldcraft.h"
#include "SoraPressRules.h"
#include "SoraPlayerCharacter.h"
#include "SoraEquipmentComponent.h"
#include "Combat/SoraStealth.h"
#include "Game/SoraFieldcraftLayout.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"

namespace Press=SoraPressRules;

void USoraFieldcraft::StagePressAccess()
{
    const FVector Origin(PressHall->Origin,0);
    const auto Part=[&](const TCHAR* Name,const FVector& At,const FVector& Size,bool Collision=true)
    {
        auto* P=Piece(Name,SoraFieldcraftLayout::Cube,Origin+At,Size/100.f,
            FLinearColor(.11f,.14f,.15f),Collision,SoraFieldcraftLayout::Metal);
        P->ComponentTags.Add(TEXT("PressCatwalk")); return P;
    };
    // The authored 120 cm perimeter at z=400; the wall stands outside it.
    Part(TEXT("PressWalkNorth"),FVector(2100,2340,390),FVector(4200,120,20));
    Part(TEXT("PressWalkSouth"),FVector(2100,60,390),FVector(4200,120,20));
    Part(TEXT("PressWalkWest"),FVector(60,1200,390),FVector(120,2160,20));
    Part(TEXT("PressWalkEast"),FVector(4140,1200,390),FVector(120,2160,20));
    // Inner rails keep walkers on the catwalk. The north rail leaves a
    // 180 cm opening for the ladder's swept capsule and step onto the deck.
    Part(TEXT("PressRailNorthWest"),FVector(165,2280,495),FVector(90,5,10));
    Part(TEXT("PressRailNorthEast"),FVector(2235,2280,495),FVector(3690,5,10));
    Part(TEXT("PressRailSouth"),FVector(2100,120,495),FVector(3960,5,10));
    Part(TEXT("PressRailWest"),FVector(120,1200,495),FVector(5,2160,10));
    Part(TEXT("PressRailEast"),FVector(4080,1200,495),FVector(5,2160,10));
    // Rungs and stiles are visual here. The hero is held by the ladder
    // controller, which sweeps the actual capsule against the world.
    for(int Side:{-1,1})
        Part(TEXT("PressLadderStile"),FVector(300+50*Side,2188,200),FVector(5,5,400),false);
    for(int Z=20;Z<400;Z+=30)
        Part(TEXT("PressLadderRung"),FVector(300,2188,Z),FVector(100,6,5),false);
}

bool USoraFieldcraft::AtPressLadder(const ASoraPlayerCharacter& Player,bool& bUp) const
{
    if(!PressHall||!Player.GetCharacterMovement()->IsMovingOnGround()||Player.IsCrouched()) return false;
    const FVector Feet=Player.GetActorLocation()-FVector(0,0,Player.GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
    const FVector Local=Feet-FVector(PressHall->Origin,0);
    const float ForwardY=Player.GetActorForwardVector().Y;
    bUp=FMath::Abs(Local.Z)<15.f;
    const auto P=bUp?Press::LadderFoot:Press::LadderTop;
    return FMath::Abs(Local.Z-(bUp?0.f:float(Press::CatwalkHeightCm)))<15.f&&
        FVector2D::Distance(FVector2D(Local),FVector2D(P.X,P.Y))<=80.f&&
        (bUp?ForwardY>.5f:ForwardY<-.5f);
}

bool USoraFieldcraft::PressLadderJump(ASoraPlayerCharacter& Player)
{
    if(!PressHall) return false;
    auto* Move=Player.GetCharacterMovement();
    if(PressLadderStep!=INDEX_NONE)
    {
        // Jump again releases the ladder at the actual position, even when
        // an obstruction has stopped progress. It never snaps past a wall.
        PressLadderStep=INDEX_NONE; PressLadderFeet.Reset();
        bPressFalling=true;
        PressFallPeak=Player.GetActorLocation().Z-Player.GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
        Move->SetMovementMode(MOVE_Falling);
        Raise(TEXT("ladder_release:press_nw")); return true;
    }
    bool bUp=false;
    if(!AtPressLadder(Player,bUp)) return false;
    const FVector Origin(PressHall->Origin,0);
    const FVector Foot=Origin+FVector(Press::LadderFoot.X,Press::LadderFoot.Y,2);
    // End at the walking capsule's normal floor clearance. Starting walking
    // six centimetres above the deck caused its floor adjustment to snap
    // downward outside the ladder's per-frame movement budget.
    const float Clearance=(UCharacterMovementComponent::MIN_FLOOR_DIST+UCharacterMovementComponent::MAX_FLOOR_DIST)*.5f;
    const FVector Above=Origin+FVector(Press::LadderFoot.X,Press::LadderFoot.Y,Press::CatwalkHeightCm+Clearance);
    const FVector Top=Origin+FVector(Press::LadderTop.X,Press::LadderTop.Y,Press::CatwalkHeightCm+Clearance);
    PressLadderFeet=bUp?TArray<FVector>{Foot,Above,Top}:TArray<FVector>{Top,Above,Foot};
    PressLadderStep=0; bPressLadderUp=bUp; bPressFalling=false;
    Player.StopSprint(); Player.ConsumeMovementInputVector();
    if(auto* Kit=Player.GetEquipment()) Kit->Halt();
    Move->StopMovementImmediately(); Move->SetMovementMode(MOVE_Flying);
    Raise(bUp?TEXT("ladder_up:press_nw"):TEXT("ladder_down:press_nw"));
    return true;
}

void USoraFieldcraft::TickPressAccess(float DeltaTime)
{
    auto* Player=Hero();
    if(!PressHall||!Player||DeltaTime<=0.f||!Player->IsAlive()) return;
    auto* Move=Player->GetCharacterMovement();
    const float Half=Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    if(PressLadderStep!=INDEX_NONE)
    {
        Move->StopMovementImmediately(); Player->ConsumeMovementInputVector();
        float Remaining=SoraFieldcraftRules::LadderCmS*DeltaTime;
        while(PressLadderFeet.IsValidIndex(PressLadderStep)&&Remaining>0.f)
        {
            const FVector Goal=PressLadderFeet[PressLadderStep]+FVector(0,0,Half);
            const FVector Delta=Goal-Player->GetActorLocation();
            const float Distance=Delta.Size();
            if(Distance<=.1f) { ++PressLadderStep; continue; }
            const float Step=FMath::Min(Distance,Remaining);
            FHitResult Hit;
            Player->SetActorLocation(Player->GetActorLocation()+Delta*(Step/Distance),true,&Hit);
            Remaining-=Step;
            if(FVector::Dist(Player->GetActorLocation(),Goal)<=.1f) ++PressLadderStep;
            else if(Hit.bBlockingHit) return; // Keep this waypoint until clear or released.
        }
        if(PressLadderFeet.IsValidIndex(PressLadderStep)) return;
        const bool bUp=bPressLadderUp;
        PressLadderStep=INDEX_NONE; PressLadderFeet.Reset();
        PressFallPeak=Player->GetActorLocation().Z-Half;
        Move->SetMovementMode(MOVE_Walking);
        Raise(bUp?TEXT("roof_reached:press_nw"):TEXT("ladder_foot:press_nw"));
        return;
    }
    const float FeetZ=Player->GetActorLocation().Z-Half;
    if(Move->IsFalling())
    {
        bPressFalling=true; PressFallPeak=FMath::Max(PressFallPeak,FeetZ);
    }
    else if(Move->IsMovingOnGround())
    {
        if(bPressFalling&&SoraFieldcraftRules::LandingHeard(FMath::RoundToInt(PressFallPeak-FeetZ),false))
        {
            const FVector Feet=Player->GetActorLocation()-FVector(0,0,Half);
            if(auto* Stealth=USoraStealth::Get(this))
                Stealth->MakeNoise(SoraStealthRules::ENoise::Landing,Feet,Feet,Player);
        }
        bPressFalling=false; PressFallPeak=FeetZ;
    }
}
