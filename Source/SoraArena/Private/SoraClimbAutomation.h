#pragma once
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraLiftAutomation.h"
#include "SoraFieldcraft.h"
#include "Components/CapsuleComponent.h"
#include "Misc/AutomationTest.h"
namespace SoraClimbAutomation
{
inline bool Note(FSoraAutomationWorld& W,const TCHAR* Phase,bool Result,const FVector& Desired=FVector::ZeroVector,int32 Hold=INDEX_NONE,int32 Frames=-1)
{
    const auto* C=USoraFieldcraft::Get(W.GetTestWorld());const auto* M=W.Mode();const auto* D=M?M->Campaign():nullptr;
    UE_LOG(LogTemp,Display,TEXT("CLIMB_DIAGNOSTIC phase=%s result=%d requested_hold=%d frames=%d desired_world=%s chapter=%d beat=%d input=%d menu=%d defeated=%d state={%s}"),
        Phase,Result,Hold,Frames,*Desired.ToString(),D?D->ChapterId:INDEX_NONE,D?D->ActiveBeat():INDEX_NONE,
        M?int32(M->InputState()):-1,M&&M->bMenu,M&&M->bDefeated,C?*C->ClimbDiagnostic():TEXT("no_fieldcraft"));
    return Result;
}
inline FKey Key(ASoraPlayerCharacter& Hero,const TCHAR* Action,bool Pad=false)
{
    for(const FKey& K:Hero.GetActionKeys(Action)) if(K.IsGamepadKey()==Pad) return K;
    return FKey();
}
inline bool Begin(FSoraAutomationWorld& W,int32 Route=0,bool Pad=false)
{
    auto* D=W.Mode()->Campaign();const auto& C=D->ActiveBeatData()->Space.Climb;
    if(!C.bEnabled) return Note(W,TEXT("Begin.contract"),false);
    const FVector O(C.Origin,0),Foot=(Route==0?C.Corner:C.Extrusion).Points[0];
    // Walk around the wall's foot to choose a route; no stand/teleport helper.
    if(!SoraLiftAutomation::Walk(W,O+FVector(-300,Foot.Y,0))) return Note(W,TEXT("Begin.walk_side"),false,O+FVector(-300,Foot.Y,0),Route);
    if(!SoraLiftAutomation::Walk(W,O+Foot-FVector(40,0,0))) return Note(W,TEXT("Begin.walk_foot"),false,O+Foot-FVector(40,0,0),Route);
    W.Player()->GetController()->SetControlRotation(FRotator::ZeroRotator);W.Player()->FaceRotation(FRotator::ZeroRotator,0);
    return Note(W,TEXT("Begin.jump"),W.PressKey(Key(*W.Player(),TEXT("Jump"),Pad))&&USoraFieldcraft::Get(W.GetTestWorld())->IsClimbing(),O+Foot,Route);
}
inline bool ToHold(FSoraAutomationWorld& W,int32 Hold)
{
    auto* C=USoraFieldcraft::Get(W.GetTestWorld());int32 F=0;
    for(;F<3600&&C->IsClimbing()&&C->ClimbHoldIndex()<Hold;++F)
        if(!W.InjectKey(EKeys::W,IE_Pressed)||!W.Tick(1)) return Note(W,TEXT("ToHold.input_tick"),false,FVector::ZeroVector,Hold,F);
    if(!C->IsClimbing()||C->ClimbHoldIndex()!=Hold) Note(W,TEXT("ToHold.before_release"),false,FVector::ZeroVector,Hold,F);
    return Note(W,TEXT("ToHold.end"),W.InjectKey(EKeys::W,IE_Released)&&W.Tick(1)&&C->IsClimbing()&&C->ClimbHoldIndex()==Hold,FVector::ZeroVector,Hold,F);
}
inline bool DownToHold(FSoraAutomationWorld& W,int32 Hold)
{
    auto* C=USoraFieldcraft::Get(W.GetTestWorld());int32 F=0;
    for(;F<3600&&C->IsClimbing()&&C->ClimbHoldIndex()>Hold;++F)
        if(!W.InjectKey(EKeys::S,IE_Pressed)||!W.Tick(1)) return Note(W,TEXT("DownToHold.input_tick"),false,FVector::ZeroVector,Hold,F);
    if(!C->IsClimbing()||C->ClimbHoldIndex()!=Hold) Note(W,TEXT("DownToHold.before_release"),false,FVector::ZeroVector,Hold,F);
    return Note(W,TEXT("DownToHold.end"),W.InjectKey(EKeys::S,IE_Released)&&W.Tick(1)&&C->IsClimbing()&&C->ClimbHoldIndex()==Hold,FVector::ZeroVector,Hold,F);
}
inline bool Top(FSoraAutomationWorld& W)
{
    auto* C=USoraFieldcraft::Get(W.GetTestWorld());int32 F=0;
    for(;F<3600&&C->IsClimbing();++F)
        if(!W.InjectKey(EKeys::W,IE_Pressed)||!W.Tick(1)) return Note(W,TEXT("Top.input_tick"),false,FVector::ZeroVector,INDEX_NONE,F);
    if(C->IsClimbing()) Note(W,TEXT("Top.before_release"),false,FVector::ZeroVector,INDEX_NONE,F);
    return Note(W,TEXT("Top.end"),W.InjectKey(EKeys::W,IE_Released)&&W.Tick(4)&&!C->IsClimbing()&&
        W.Player()->GetCharacterMovement()->IsMovingOnGround()&&FMath::Abs(W.Player()->GetActorLocation().Z-1690)<10,FVector::ZeroVector,INDEX_NONE,F);
}
inline bool Approach(FSoraAutomationWorld& W)
{
    const FVector O(W.Mode()->Campaign()->ActiveBeatData()->Space.Climb.Origin,0);
    if(!SoraLiftAutomation::Walk(W,O+FVector(700,0,1600))) return Note(W,TEXT("Approach.landing"),false,O+FVector(700,0,1600));
    return Note(W,TEXT("Approach.aperture"),SoraLiftAutomation::Walk(W,O+FVector(1040,0,1640)),O+FVector(1040,0,1640));
}
inline bool Exit(FSoraAutomationWorld& W,bool Pad=false)
{
    auto* D=W.Mode()->Campaign();const int32 Chapter=D->ChapterId,Beat=D->ActiveBeat();
    if(!W.PressKey(Key(*W.Player(),TEXT("Crouch"),Pad))||!W.Tick(3)) return Note(W,TEXT("Exit.crouch_input"),false);
    auto* C=USoraFieldcraft::Get(W.GetTestWorld());
    if(!C->IsClimbCrawling()||!W.Player()->IsCrouched()||W.Player()->GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight()!=28) return Note(W,TEXT("Exit.crouch_admission"),false);
    W.Player()->GetController()->SetControlRotation(FRotator::ZeroRotator);W.Player()->FaceRotation(FRotator::ZeroRotator,0);
    int32 F=0;
    for(;F<1000&&D->ActiveBeat()==Beat&&!W.Mode()->bDefeated;++F)
        if(!W.InjectKey(EKeys::W,IE_Pressed)||!W.Tick(1)) return Note(W,TEXT("Exit.input_tick"),false,FVector::ZeroVector,INDEX_NONE,F);
    if(D->ActiveBeat()==Beat) Note(W,TEXT("Exit.before_release"),false,FVector::ZeroVector,INDEX_NONE,F);
    if(!W.InjectKey(EKeys::W,IE_Released)||!W.Tick(3)) return Note(W,TEXT("Exit.release_tick"),false);
    return Note(W,TEXT("Exit.end"),D->ChapterId==Chapter&&D->ActiveBeat()==Beat+1&&!W.Mode()->bDefeated&&
        (D->Progress().CompletedMask&SoraBeatRules::BeatBit(Beat))!=0u&&
        W.Player()->GetCapsuleComponent()->GetUnscaledCapsuleRadius()==34&&W.Player()->GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight()==88,FVector::ZeroVector,INDEX_NONE,F);
}
inline bool Traverse(FSoraAutomationWorld& W,int32 Route=0,bool Pad=false)
{ return Begin(W,Route,Pad)&&Top(W)&&Approach(W)&&Exit(W,Pad); }
struct FObservedFall
{
    double SupportFeet=0,PeakFeet=0,LandingFeet=0;
    bool Airborne=false,PauseChecked=false,PauseStable=false;
};
inline bool WalkOff(FSoraAutomationWorld& W,FObservedFall& Observed,bool Pause=false)
{
    auto* Hero=W.Player();auto* Move=Hero->GetCharacterMovement();auto* C=USoraFieldcraft::Get(W.GetTestWorld());
    const auto Feet=[&]() { return Hero->GetActorLocation().Z-Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight(); };
    if(!Move->IsMovingOnGround()) return Note(W,TEXT("Fall.support_admission"),false);
    Observed.SupportFeet=Observed.PeakFeet=Feet();
    Hero->GetController()->SetControlRotation(FRotator::ZeroRotator);Hero->FaceRotation(FRotator::ZeroRotator,0);
    if(!W.InjectKey(EKeys::S,IE_Pressed)) return false;
    int32 AirFrames=0,F=0;
    for(;F<360&&!W.Mode()->bDefeated;++F)
    {
        if(!W.Tick(1)) return false;
        Observed.PeakFeet=FMath::Max(Observed.PeakFeet,Feet());
        if(Move->IsFalling()) { Observed.Airborne=true;++AirFrames; }
        if(Pause&&AirFrames==10&&!Observed.PauseChecked)
        {
            if(!W.InjectKey(EKeys::S,IE_Released)||!W.PressKey(EKeys::Escape)||!W.Mode()->bMenu) return false;
            const FVector At=Hero->GetActorLocation();const double Peak=C->ClimbFallPeak();const float Hp=Hero->Health;
            if(!W.Tick(120)) return false;
            Observed.PauseChecked=true;Observed.PauseStable=C->IsClimbFalling()&&C->ClimbFallPeak()==Peak&&
                Hero->GetActorLocation().Equals(At,.01f)&&Hero->Health==Hp;
            if(!W.PressKey(EKeys::Escape)||W.Mode()->bMenu) return false;
            if(!W.InjectKey(EKeys::S,IE_Pressed)) return false;
        }
        if(Observed.Airborne&&Move->IsMovingOnGround()) break;
    }
    if(!W.InjectKey(EKeys::S,IE_Released)||!W.Tick(2)) return false;
    Observed.LandingFeet=Feet();
    UE_LOG(LogTemp,Display,TEXT("CLIMB_DIAGNOSTIC fall support_feet=%.4f peak_feet=%.4f landing_feet=%.4f actual_drop=%.4f airborne=%d pause_checked=%d pause_stable=%d health=%.3f"),
        Observed.SupportFeet,Observed.PeakFeet,Observed.LandingFeet,Observed.PeakFeet-Observed.LandingFeet,
        Observed.Airborne,Observed.PauseChecked,Observed.PauseStable,Hero->Health);
    return Note(W,TEXT("Fall.walk_off_end"),Observed.Airborne&&(Move->IsMovingOnGround()||W.Mode()->bDefeated),FVector::ZeroVector,INDEX_NONE,F);
}
}
#endif
