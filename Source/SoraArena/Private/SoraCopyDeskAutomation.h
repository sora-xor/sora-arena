#pragma once
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraRecoveryAutomation.h"

namespace SoraCopyDeskAutomation
{
inline bool Copy(FSoraAutomationWorld& World,int32 Point)
{
    auto* Campaign=World.Mode()->Campaign();
    const auto* Space=Campaign->ActiveSpace();
    if(!Space||!Space->Objectives.IsValidIndex(Point)||Campaign->ActiveTask().HoldPointCount<=Point) return false;
    const int32 Beat=Campaign->ActiveBeat();
    const FVector Target(Space->Objectives[Point],Space->HeightCm);
    const FVector From=World.Player()->GetActorLocation();
    // Walk along the clear front aisle, then step up to the chosen desk.
    const double AisleX=FMath::Min(From.X,Target.X-350.);
    if(!SoraRecoveryAutomation::WalkTo(World,FVector(AisleX,From.Y,Target.Z))||
        !SoraRecoveryAutomation::WalkTo(World,FVector(AisleX,Target.Y,Target.Z))||
        !SoraRecoveryAutomation::WalkTo(World,Target)) return false;
    FKey Use;
    for(const FKey& Key:World.Player()->GetActionKeys(TEXT("Interact"))) if(!Key.IsGamepadKey()) { Use=Key;break; }
    if(!Use.IsValid()||!World.InjectKey(Use,IE_Pressed)) return false;
    bool Ok=true;
    for(int Frame=0;Frame<3900&&Campaign->ActiveBeat()==Beat&&
        Campaign->TaskProgress().HoldProgress[Point]<Campaign->ActiveTask().HoldPointMs;++Frame)
        if(!World.Tick(1)) { Ok=false;break; }
    const bool Finished=Campaign->ActiveBeat()!=Beat||
        Campaign->TaskProgress().HoldProgress[Point]==Campaign->ActiveTask().HoldPointMs;
    return World.InjectKey(Use,IE_Released)&&World.Tick(1)&&Ok&&Finished;
}
}
#endif
