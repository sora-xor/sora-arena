#pragma once
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraLiftAutomation.h"
#include "SoraRidgeRules.h"
#include "Misc/AutomationTest.h"
namespace SoraRidgeAutomation
{
// Traverse the actual crown using W and the ordinary low-cover vault. No
// time dilation, teleport, movement mode mutation or synthetic wave event.
inline bool Walk(FSoraAutomationWorld& W,const FSoraBeatSpace& Space,double LocalX,FAutomationTestBase& Test,bool Quiet=false,bool FinishBeat=false)
{
    const FVector O(Space.Wind.Origin,0);
    const FVector Target=O+FVector(LocalX,0,SoraRidgeRules::Height(LocalX));
    const auto* Director=W.Mode()->Campaign();
    const int32 Chapter=Director->ChapterId, Beat=Director->ActiveBeat();
    const auto StillHere=[&]() { return Director->ChapterId==Chapter&&Director->ActiveBeat()==Beat; };
    if(FinishBeat&&(!Space.Exit.Contains(Target)||!SoraBeatRules::TaskComplete(Director->TaskProgress(),Director->ActiveTask())||
        (Director->Progress().CompletedMask&SoraBeatRules::BeatBit(Beat))!=0u))
    { Test.AddError(TEXT("Ridge exit walk requires cleared waves, an unfinished beat and its authored exit target"));return false; }
    const auto AdvanceTo=[&](const FVector& Point,bool Exit=false)
    {
        for(int F=0;F<3600&&StillHere()&&(Exit||FVector::Dist2D(W.Player()->GetActorLocation(),Point)>20);++F)
        {
            if(Quiet) SoraLiftAutomation::HoldThreats(W);
            const FRotator Facing=(Point-W.Player()->GetActorLocation()).GetSafeNormal2D().Rotation();
            W.Player()->GetController()->SetControlRotation(Facing);W.Player()->FaceRotation(Facing,0);
            if(!W.InjectKey(EKeys::W,IE_Pressed)||!W.Tick(1)) return false;
        }
        if(!W.InjectKey(EKeys::W,IE_Released)||!W.Tick(2)) return false;
        // The grounded exit completes the beat before its center is reached;
        // BeginBeat then travels the hero to the next place in the same tick.
        // Only this explicit final leg may accept that production transition.
        if(Exit) return Director->ChapterId==Chapter&&Director->ActiveBeat()!=Beat&&!W.Mode()->bDefeated&&
            (Director->Progress().CompletedMask&SoraBeatRules::BeatBit(Beat))!=0u;
        return StillHere()&&FVector::Dist2D(W.Player()->GetActorLocation(),Point)<35;
    };
    const double Start=W.Player()->GetActorLocation().X-O.X;
    for(int Rib=1200;Rib<18000&&Rib<LocalX;Rib+=1200)
    {
        if(Rib<Start-50) continue;
        const FVector Before=O+FVector(Rib-100,0,SoraRidgeRules::Height(Rib-100));
        if(!AdvanceTo(Before))
        { Test.AddError(FString::Printf(TEXT("Ridge walk blocked before rib %d: hero=%s target=%s"),Rib,*W.Player()->GetActorLocation().ToString(),*Before.ToString())); return false; }
        const FRotator Facing(0,0,0);
        W.Player()->GetController()->SetControlRotation(Facing); W.Player()->FaceRotation(Facing,0);
        if(!W.PressKey(EKeys::SpaceBar)) return false;
        bool Vaulted=W.Player()->IsVaulting();
        for(int Frame=0;Frame<180&&W.Player()->GetActorLocation().X<O.X+Rib+60;++Frame)
        {
            if(Quiet) SoraLiftAutomation::HoldThreats(W);
            if(!W.InjectKey(EKeys::W,IE_Pressed)||!W.Tick(1)) return false;
            Vaulted|=W.Player()->IsVaulting();
        }
        if(!W.InjectKey(EKeys::W,IE_Released)||!W.Tick(3)) return false;
        if(!Vaulted||W.Player()->GetActorLocation().X<O.X+Rib+60)
        { Test.AddError(FString::Printf(TEXT("Ridge mapped vault failed at rib %d: hero=%s mode=%d"),Rib,*W.Player()->GetActorLocation().ToString(),int32(W.Player()->GetCharacterMovement()->MovementMode)));return false; }
    }
    const bool Arrived=AdvanceTo(Target,FinishBeat);
    if(!Arrived) Test.AddError(FString::Printf(TEXT("Ridge final walk failed: exit=%d chapter=%d->%d beat=%d->%d completed=%u defeated=%d health=%.3f hero=%s target=%s mode=%d"),
        FinishBeat,Chapter,Director->ChapterId,Beat,Director->ActiveBeat(),Director->Progress().CompletedMask,W.Mode()->bDefeated,W.Player()->Health,
        *W.Player()->GetActorLocation().ToString(),*Target.ToString(),int32(W.Player()->GetCharacterMovement()->MovementMode)));
    else if(FinishBeat) Test.AddInfo(FString::Printf(TEXT("Ridge real exit completed: chapter=%d beat=%d->%d completed=%u hero=%s"),
        Chapter,Beat,Director->ActiveBeat(),Director->Progress().CompletedMask,*W.Player()->GetActorLocation().ToString()));
    return Arrived;
}
}
#endif
