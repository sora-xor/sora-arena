#pragma once
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraRecoveryAutomation.h"
#include "SoraCatalog.h"

namespace SoraCarryAutomation
{
inline bool PrySeal(FSoraAutomationWorld& World)
{
    auto* Campaign=World.Mode()->Campaign();
    if(!Campaign->NeedsCarryGate()) return true;
    const auto* Space=Campaign->ActiveSpace();
    if(!Space) return false;
    const FVector At(Space->CarryGate,World.Player()->GetActorLocation().Z);
    if(FVector::Dist2D(World.Player()->GetActorLocation(),At)>30.f&&!SoraRecoveryAutomation::WalkTo(World,At)) return false;
    if(!World.InjectKey(EKeys::E,IE_Pressed)) return false;
    for(int32 Frame=0;Frame<420&&Campaign->NeedsCarryGate();++Frame)
        if(!World.Tick(1)) return false;
    return World.InjectKey(EKeys::E,IE_Released)&&World.Tick(2)&&!Campaign->NeedsCarryGate();
}
}
#endif
