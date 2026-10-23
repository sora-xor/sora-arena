#pragma once
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraLiftAutomation.h"
#include "SoraFieldcraft.h"

namespace SoraFloodAutomation
{
// Campaign progression retains its usual combat-health assistance, while
// crossing this particular physical route with ordinary keys at 60 Hz.
// FloodTraversal/FloodLateWater separately assert zero drowning damage.
inline bool Exit(FSoraAutomationWorld& W)
{
    auto* Hero=W.Player(); auto* C=W.Mode()->Campaign();
    if(!C||!C->ActiveSpace()||!C->ActiveSpace()->Flood.bEnabled) return false;
    const FVector Origin(C->ActiveSpace()->Flood.Origin,0);
    const auto Tick=[&](int32 Frames)
    {
        for(int32 I=0;I<Frames;++I)
        {
            if(Hero->Health<Hero->MaxHealth*.5f) Hero->Heal(Hero->MaxHealth);
            if(!W.Tick(1)) return false;
        }
        return true;
    };
    const auto Walk=[&](FVector Offset)
    {
        const FVector Point=Origin+Offset;
        for(int32 Frame=0;Frame<6000&&FVector::Dist2D(Hero->GetActorLocation(),Point)>20;++Frame)
        {
            const FRotator Facing=(Point-Hero->GetActorLocation()).GetSafeNormal2D().Rotation();
            Hero->GetController()->SetControlRotation(Facing);Hero->FaceRotation(Facing,0);
            if(!W.InjectKey(EKeys::W,IE_Pressed)||!Tick(1)) return false;
        }
        return W.InjectKey(EKeys::W,IE_Released)&&Tick(4)&&FVector::Dist2D(Hero->GetActorLocation(),Point)<30;
    };
    if(Hero->GetCharacterMovement()->bWantsToCrouch&&!W.PressKey(EKeys::C)) return false;
    if(!Walk(FVector(7440,0,0))||!W.PressKey(EKeys::C)||!Walk(FVector(8250,0,0))||
        !W.PressKey(EKeys::C)||!Tick(240)||!W.PressKey(EKeys::C)||!Walk(FVector(9050,0,0))||
        !W.PressKey(EKeys::C)||!Tick(70)||!Walk(FVector(9500,0,0))||!Walk(FVector(9500,-600,0))||
        !Walk(FVector(9500,-3900,0))) return false;
    const FRotator Facing(0,-90,0);Hero->GetController()->SetControlRotation(Facing);Hero->FaceRotation(Facing,0);
    for(int32 I=0;I<500&&C->ActiveBeat()==13;++I)
        if(!W.InjectKey(EKeys::W,IE_Pressed)||!Tick(1)) return false;
    return W.InjectKey(EKeys::W,IE_Released)&&Tick(1)&&C->ActiveBeat()==14;
}
}
#endif
