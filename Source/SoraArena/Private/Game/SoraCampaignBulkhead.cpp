#include "SoraCampaignDirector.h"
#include "SoraBoss.h"
#include "SoraCatalog.h"
#include "SoraEquipmentComponent.h"
#include "SoraFrontEnd.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "SoraText.h"
#include "SoraWorldBuilder.h"

bool USoraCampaignDirector::IsBulkheadCapture() const
{
    const auto* Beat=ActiveBeatData();
    return Beat&&Beat->Space.bBulkhead&&Beat->CaptureEvent==TEXT("interact:bulkhead_lever")&&Beat->CaptureHoldMs==2000;
}
void USoraCampaignDirector::CancelBulkheadHold()
{
    const auto* Hero=Mode().Hero();
    // As with the summit cut, a cancelled held press must be released. This
    // also runs on input boundaries where the gameplay clock cannot tick.
    BulkheadHold={0,false,Hero&&Hero->IsActionHeld(TEXT("Interact"))};
    BulkheadClock.Reset();
    if(IsBulkheadCapture()&&Mode().Arena()) Mode().Arena()->ShowBulkhead(AwaitingCapture(),0.f);
}
void USoraCampaignDirector::BeginBulkheadCapture()
{
    CancelBulkheadHold();
    Notify(BulkheadText(),8.f);
}
SoraText::FLine USoraCampaignDirector::BulkheadText() const
{
    const auto Key=SoraUI::ActionKey(this,TEXT("Interact"));
    return SoraText::Format(NSLOCTEXT("SoraArena.Campaign","BulkheadHold",
        "入口の隔壁レバーで {Key} を 2 秒長押しし、エスクロを封じ込めよう。"),{{TEXT("Key"),Key}});
}
bool USoraCampaignDirector::BulkheadEligible() const
{
    const auto* Hero=Mode().Hero(); const auto* Arena=Mode().Arena();
    const auto* Boss=Cast<ASoraBoss>(Captive);
    const auto* Kit=Hero?Hero->GetEquipment():nullptr;
    return IsBulkheadCapture()&&AwaitingCapture()&&Hero&&Arena&&Boss&&Boss->IsDefeated()&&
        Mode().IsPlaying()&&!Mode().bDefeated&&!bDialogueHeld&&Hero->CanPlay()&&
        !Kit->IsStaggered()&&!Kit->bReloading&&!Kit->IsCommittedStrike()&&!Kit->IsBowDrawing()&&!Kit->IsStepping()&&
        Arena->CanReachBulkhead(*Hero);
}
bool USoraCampaignDirector::InteractBulkhead()
{
    if(!IsBulkheadCapture()) return false;
    const auto* Hero=Mode().Hero();
    if(Hero&&SoraSummitRules::Begin(BulkheadHold,BulkheadEligible(),Hero->IsActionHeld(TEXT("Interact"))))
        BulkheadClock.Reset();
    return true; // The captive's body and an unheld synthetic press never bind him.
}
void USoraCampaignDirector::TickBulkhead(float DeltaSeconds)
{
    if(!IsBulkheadCapture()||!AwaitingCapture()) return;
    auto* Hero=Mode().Hero(); auto* Arena=Mode().Arena();
    if(!Hero||!Arena) { CancelBulkheadHold(); return; }
    const auto* Beat=ActiveBeatData();
    // Only this press owns the fractional clock; prior idle/cancelled time
    // cannot shorten its two seconds. Bound a hitch to the remaining hold.
    const int32 DeltaMs=BulkheadHold.Active?FMath::Min(BulkheadClock.Advance(DeltaSeconds),Beat->CaptureHoldMs-BulkheadHold.HeldMs):0;
    const bool Sealed=SoraSummitRules::TickCut(BulkheadHold,DeltaMs,BulkheadEligible(),Hero->IsActionHeld(TEXT("Interact")),Beat->CaptureHoldMs);
    if(!BulkheadHold.Active) BulkheadClock.Reset();
    Arena->ShowBulkhead(true,Sealed?1.f:static_cast<float>(BulkheadHold.HeldMs)/Beat->CaptureHoldMs);
    if(!Sealed) return;
    const int32 Before=SoraBeatRules::ProgressPermille(TaskState,Task);
    if(!SoraBeatRules::Capture(TaskState,Task)) return;
    Fire(Beat->CaptureEvent); Fire(TEXT("outro_cinematic"));
    UpdateObjective(); Progressed(Before);
}
