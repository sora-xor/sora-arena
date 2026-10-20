#include "SoraCampaignDirector.h"
#include "SoraBoss.h"
#include "SoraCatalog.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "SoraWorldBuilder.h"

bool USoraCampaignDirector::IsSpineCapture() const
{
    const auto* Beat=ActiveBeatData();
    return Beat&&Beat->Space.Summit.Enabled()&&Beat->CaptureEvent==TEXT("interact:engine_spine")&&Beat->CaptureHoldMs>0;
}
void USoraCampaignDirector::CancelSpineCut()
{
    const auto* Hero=Mode().Hero();
    // A boundary while Interact is down needs a release before a new press.
    // An actual release can arrive while paused, with no TickSpineCut call.
    SpineCut={0,false,Hero&&Hero->IsActionHeld(TEXT("Interact"))};
}
void USoraCampaignDirector::BeginSpineCapture()
{
    SpineCut={}; SpineReadyMs=TaskState.ElapsedMs+1500; bSpinePromptShown=false; bSpineMutoRaised=false;
    if(auto* Hero=Mode().Hero())
    {
        auto* Kit=Hero->GetEquipment();
        Kit->DropStance(); Kit->EquipCampaignWeapon(0); Kit->Sheathe(true);
    }
    // The first-person disarm clip remains an art task. Its authored 1.5 s
    // interval does not skip traversal or consume a held Interact press.
}
bool USoraCampaignDirector::SpineCutEligible() const
{
    const auto* Hero=Mode().Hero(); const auto* Arena=Mode().Arena();
    const auto* Boss=Cast<ASoraBoss>(Captive);
    return IsSpineCapture()&&AwaitingCapture()&&Hero&&Arena&&Boss&&Boss->IsDefeated()&&
        Mode().IsPlaying()&&!Mode().bDefeated&&!bDialogueHeld&&TaskState.ElapsedMs>=SpineReadyMs&&
        Hero->WeaponId==0&&!Hero->GetEquipment()->IsStaggered()&&!Hero->GetEquipment()->bReloading&&
        !Hero->GetEquipment()->IsCommittedStrike()&&(!SpineCut.Active||Hero->GetEquipment()->IsSheathing())&&
        Arena->CanReachSummitSpine(*Hero);
}
bool USoraCampaignDirector::InteractSpine()
{
    if(!IsSpineCapture()||!AwaitingCapture()) return false;
    const auto* Hero=Mode().Hero();
    if(Hero&&SoraSummitRules::Begin(SpineCut,SpineCutEligible(),Hero->IsActionHeld(TEXT("Interact"))))
    {
        Hero->GetEquipment()->Sheathe(true);
        Notify(TEXT("継ぎ目を見据え、長押しで背骨を断て。"),TEXT("Face the seam and hold Interact to cut the spine."),2.f);
    }
    return true; // Never fall through to the generic E-at-captive shortcut.
}
void USoraCampaignDirector::TickSpineCut(int32 DeltaMs)
{
    if(!IsSpineCapture()||!AwaitingCapture()) return;
    auto* Hero=Mode().Hero(); auto* Arena=Mode().Arena();
    if(!Hero||!Arena) return;
    if(!bSpineMutoRaised)
    {
        if(const auto* Boss=Cast<ASoraBoss>(Captive);Boss&&Boss->DefeatDetail()==TEXT("muto_dori"))
            Fire(TEXT("event:muto_dori_success"));
        bSpineMutoRaised=true;
    }
    const bool Ready=TaskState.ElapsedMs>=SpineReadyMs;
    if(Ready&&!bSpinePromptShown)
    {
        bSpinePromptShown=true; Fire(TEXT("event:spine_prompt"));
        Notify(TEXT("機関の背骨を断て。台座の継ぎ目で E を長押し。"),TEXT("Cut the engine's spine. Face its seam on the dais and hold Interact."),6.f);
    }
    const auto* Beat=ActiveBeatData();
    const bool Cut=SoraSummitRules::TickCut(SpineCut,DeltaMs,SpineCutEligible(),Hero->IsActionHeld(TEXT("Interact")),Beat->CaptureHoldMs);
    Arena->ShowSummitSpine(Ready,Cut?1.f:static_cast<float>(SpineCut.HeldMs)/Beat->CaptureHoldMs);
    if(!Cut) return;
    const int32 Before=SoraBeatRules::ProgressPermille(TaskState,Task);
    if(!SoraBeatRules::Capture(TaskState,Task)) return;
    Hero->GetEquipment()->Sheathe(false);
    Fire(Beat->CaptureEvent); Fire(TEXT("outro_cinematic"));
    UpdateObjective(); Progressed(Before);
}
