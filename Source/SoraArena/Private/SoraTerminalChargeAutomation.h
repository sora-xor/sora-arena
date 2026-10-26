#pragma once
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraRecoveryAutomation.h"
#include "SoraLiftAutomation.h"
namespace SoraTerminalChargeAutomation
{
inline bool HoldTo(FSoraAutomationWorld& W,SoraTerminalChargeRules::EStage Stage)
{
    auto* C=W.Mode()->Campaign();
    if(!W.InjectKey(EKeys::E,IE_Pressed))return false;
    bool Ok=true;
    for(int I=0;I<360&&Ok&&C->TerminalState().Stage!=Stage;++I)Ok=W.Tick(1);
    const bool Released=W.InjectKey(EKeys::E,IE_Released);
    return Ok&&Released&&C->TerminalState().Stage==Stage&&W.Tick(1);
}
// Caller clears enemies for directed traversal/progression. All approach,
// work and escape movement here uses the real capsule and mapped controls.
inline bool Escape(FSoraAutomationWorld& W)
{
    namespace R=SoraTerminalChargeRules;auto* C=W.Mode()->Campaign();
    // The AI query returns a partial path behind the board for this narrow
    // player corridor. Walk its checked straight segments with ordinary W
    // input instead of appending a line through the board to that path.
    if(!C->IsTerminalCharge()||!SoraLiftAutomation::Walk(W,FVector(-1000,540,0))||
       !SoraLiftAutomation::Walk(W,FVector(R::PanelX,548,0))||
       !HoldTo(W,R::EStage::Planted)||!HoldTo(W,R::EStage::Burning)||C->TaskProgress().Done!=2)return false;
    // Clicking on safety cannot credit it. The detonation is the completion boundary.
    for(const FVector P:{FVector(-1000,548,0),FVector(-1000,3000,0),FVector(-1600,3000,0)})
        if(!SoraLiftAutomation::Walk(W,P))return false;
    if(!C->TerminalSafe()||!C->IsTerminalCharge()||C->TaskProgress().Done!=2)return false;
    if(!W.InjectKey(EKeys::E,IE_Pressed)||!W.InjectKey(EKeys::E,IE_Released)||C->TaskProgress().Done!=2)return false;
    for(int I=0;I<1300&&C->IsTerminalCharge()&&!W.Mode()->bDefeated;++I)if(!W.Tick(1))return false;
    return C->ActiveBeatData()&&C->ActiveBeatData()->Id==TEXT("ch03.b11")&&!W.Mode()->bDefeated;
}
}
#endif
