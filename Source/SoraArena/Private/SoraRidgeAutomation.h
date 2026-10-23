#pragma once
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraLiftAutomation.h"
#include "SoraRidgeRules.h"
#include "Misc/AutomationTest.h"
namespace SoraRidgeAutomation
{
// Traverse the actual crown using W and the ordinary low-cover vault. No
// time dilation, teleport, movement mode mutation or synthetic wave event.
inline bool Walk(FSoraAutomationWorld& W,const FSoraBeatSpace& Space,double LocalX,FAutomationTestBase& Test,bool Quiet=false)
{
    const FVector O(Space.Wind.Origin,0);
    const auto AdvanceTo=[&](const FVector& Point)
    {
        for(int F=0;F<3600&&FVector::Dist2D(W.Player()->GetActorLocation(),Point)>20;++F)
        {
            if(Quiet) SoraLiftAutomation::HoldThreats(W);
            const FRotator Facing=(Point-W.Player()->GetActorLocation()).GetSafeNormal2D().Rotation();
            W.Player()->GetController()->SetControlRotation(Facing);W.Player()->FaceRotation(Facing,0);
            if(!W.InjectKey(EKeys::W,IE_Pressed)||!W.Tick(1)) return false;
        }
        return W.InjectKey(EKeys::W,IE_Released)&&W.Tick(2)&&FVector::Dist2D(W.Player()->GetActorLocation(),Point)<35;
    };
    const double Start=W.Player()->GetActorLocation().X-O.X;
    for(int Rib=1200;Rib<18000&&Rib<LocalX;++Rib)
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
    return AdvanceTo(O+FVector(LocalX,0,SoraRidgeRules::Height(LocalX)));
}
}
#endif
