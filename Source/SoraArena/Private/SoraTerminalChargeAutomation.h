#pragma once
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraRecoveryAutomation.h"
#include "SoraLiftAutomation.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameEvents.h"
#include "Combat/SoraStealth.h"
#include "Components/CapsuleComponent.h"
#include "Misc/ScopeExit.h"
namespace SoraTerminalChargeAutomation
{
inline bool HoldTo(FSoraAutomationWorld& W,SoraTerminalChargeRules::EStage Stage)
{
    auto* C=W.Mode()->Campaign();
    if(!W.InjectKey(EKeys::E,IE_Pressed))return false;
    auto* Events=USoraGameEvents::Get(W.GetTestWorld());
    FString DamageSource=TEXT("none");
    const auto Damaged=Events->OnDamaged.AddLambda([&](const FSoraDamagedEvent& E)
    {
        if(E.Victim==W.Player())DamageSource=FString::Printf(TEXT("%s (%s), %.2f HP"),
            *GetNameSafe(E.Causer),E.Causer?*E.Causer->GetActorLocation().ToString():TEXT("no actor"),E.Amount);
    });
    ON_SCOPE_EXIT { Events->OnDamaged.Remove(Damaged); };
    if(!C->TerminalOccupiesHands()&&C->TerminalState().Stage!=Stage)
    {
        const auto* H=W.Player();const auto* K=H->GetEquipment();const auto* S=USoraStealth::Get(H);
        FHitResult Hit;FCollisionQueryParams Q(SCENE_QUERY_STAT(TerminalHoldDiagnostic),false,H);
        W.GetTestWorld()->LineTraceSingleByChannel(Hit,H->GetActorLocation(),FVector(-730,560,110),ECC_Visibility,Q);
        UE_LOG(LogTemp,Error,TEXT("Terminal hold refused: playable=%d ground=%d feet=%.3f wait_release=%d stagger=%d strike=%d step=%d reload=%d dragging=%d drag_target=%s seal=%s ray=%s/%s"),
            H->CanPlay(),H->GetCharacterMovement()->IsMovingOnGround(),H->GetActorLocation().Z-H->GetCapsuleComponent()->GetScaledCapsuleHalfHeight(),
            C->TerminalState().WaitRelease,K->IsStaggered(),K->IsCommittedStrike(),K->IsStepping(),K->bReloading,S&&S->IsDragging(),
            *GetNameSafe(S?S->DragTarget(*H):nullptr),*GetNameSafe(C->SealBeingCut()),*GetNameSafe(Hit.GetActor()),*GetNameSafe(Hit.GetComponent()));
    }
    bool Ok=true;
    for(int I=0;I<360&&Ok&&C->TerminalState().Stage!=Stage;++I)
    {
        const bool WasWorking=C->TerminalOccupiesHands();const float Health=W.Player()->Health;
        Ok=W.Tick(1);
        if(WasWorking&&!C->TerminalOccupiesHands()&&C->TerminalState().Stage!=Stage)
        {
            const auto* H=W.Player();const auto* K=H->GetEquipment();
            FHitResult Hit;FCollisionQueryParams Q(SCENE_QUERY_STAT(TerminalCancelDiagnostic),false,H);
            W.GetTestWorld()->LineTraceSingleByChannel(Hit,H->GetActorLocation(),FVector(-730,560,110),ECC_Visibility,Q);
            UE_LOG(LogTemp,Error,TEXT("Terminal work cancelled at frame=%d: hero=%s playable=%d ground=%d feet=%.3f key=%d wait_release=%d health=%.2f->%.2f stagger=%d strike=%d step=%d reload=%d dialogue=%d ray=%s/%s damage=%s"),
                I,*H->GetActorLocation().ToString(),H->CanPlay(),H->GetCharacterMovement()->IsMovingOnGround(),H->GetActorLocation().Z-H->GetCapsuleComponent()->GetScaledCapsuleHalfHeight(),
                H->IsActionHeld(TEXT("Interact")),C->TerminalState().WaitRelease,Health,H->Health,K->IsStaggered(),K->IsCommittedStrike(),K->IsStepping(),K->bReloading,C->IsDialogueBlocking(),
                *GetNameSafe(Hit.GetActor()),*GetNameSafe(Hit.GetComponent()),*DamageSource);
            break;
        }
    }
    const bool Released=W.InjectKey(EKeys::E,IE_Released);
    return Ok&&Released&&C->TerminalState().Stage==Stage&&W.Tick(1);
}
// Caller clears enemies for directed traversal/progression. All approach,
// work and escape movement here uses the real capsule and mapped controls.
inline bool Escape(FSoraAutomationWorld& W)
{
    namespace R=SoraTerminalChargeRules;auto* C=W.Mode()->Campaign();
    const auto Check=[&](bool Ok,const TCHAR* Step)
    {
        if(!Ok)UE_LOG(LogTemp,Error,TEXT("Terminal traversal failed at %s: hero=%s stage=%d held=%d fuse=%d done=%d input=%d"),
            Step,*W.Player()->GetActorLocation().ToString(),int(C->TerminalState().Stage),C->TerminalState().HeldMs,
            C->TerminalState().FuseAgeMs,C->TaskProgress().Done,int(W.Mode()->InputState()));
        return Ok;
    };
    if(!C->IsTerminalCharge())return false;
    // The assisted campaign may finish freeing conscripts elsewhere in the
    // street. Reach the alley entrance before taking its checked segments.
    const FVector Entry(-1000,2800,0);
    if(FVector::Dist2D(W.Player()->GetActorLocation(),Entry)>40.f&&
       !Check(SoraRecoveryAutomation::WalkTo(W,Entry),TEXT("alley entrance")))return false;
    // The AI query returns a partial path behind the board for this narrow
    // player corridor. Walk its checked straight segments with ordinary W
    // input instead of appending a line through the board to that path.
    if(!Check(SoraLiftAutomation::Walk(W,FVector(-1000,540,0)),TEXT("service corridor"))||
       !Check(SoraLiftAutomation::Walk(W,FVector(R::PanelX,548,0)),TEXT("panel"))||
       !Check(HoldTo(W,R::EStage::Planted),TEXT("plant"))||!Check(HoldTo(W,R::EStage::Burning),TEXT("ignite"))||C->TaskProgress().Done!=2)return false;
    // Clicking on safety cannot credit it. The detonation is the completion boundary.
    for(const FVector P:{FVector(-1000,548,0),FVector(-1000,3000,0),FVector(-1600,3000,0)})
        if(!Check(SoraLiftAutomation::Walk(W,P),TEXT("escape")))return false;
    if(!Check(C->TerminalSafe()&&C->IsTerminalCharge()&&C->TaskProgress().Done==2,TEXT("safe cover")))return false;
    if(!W.InjectKey(EKeys::E,IE_Pressed)||!W.InjectKey(EKeys::E,IE_Released)||C->TaskProgress().Done!=2)return false;
    for(int I=0;I<1300&&C->IsTerminalCharge()&&!W.Mode()->bDefeated;++I)if(!W.Tick(1))return false;
    return C->ActiveBeatData()&&C->ActiveBeatData()->Id==TEXT("ch03.b11")&&!W.Mode()->bDefeated;
}
}
#endif
