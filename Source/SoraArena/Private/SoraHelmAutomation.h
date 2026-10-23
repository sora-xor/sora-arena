#pragma once
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraRecoveryAutomation.h"
namespace SoraHelmAutomation
{
// Actual walking and the pawn's current mapped Interact, never state credit.
inline bool Correct(FSoraAutomationWorld& World,const FKey& Key=EKeys::E)
{
    auto* C=World.Mode()->Campaign();
    if(!C->HelmNeedsTrim()) return true;
    if(!SoraRecoveryAutomation::WalkTo(World,C->HelmWheelPoint()+FVector(-190,0,0))||!C->AtHelmWheel()) return false;
    if(!World.InjectKey(Key,IE_Pressed)||!World.Tick(125)||!World.InjectKey(Key,IE_Released)||!World.Tick(2)) return false;
    return !C->HelmNeedsTrim();
}
}
#endif
