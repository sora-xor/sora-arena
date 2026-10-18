#include "SoraCampaignDirector.h"
#include "SoraBoss.h"

void USoraCampaignDirector::SaveArrivedSummitPhase()
{
    if(PendingSummitPhaseSave==INDEX_NONE) return;
    const auto* Boss=CampaignBoss();
    if(!Boss||Boss->IsDefeated()) { PendingSummitPhaseSave=INDEX_NONE; return; }
    // Actor and director tick order can differ. Wait for the boss's actual
    // phase, its minimum transition, and P2's physical arrival before saving.
    if(Boss->PhaseIndex()!=PendingSummitPhaseSave||Boss->IsPhaseTransitioning()||
        (PendingSummitPhaseSave==1&&!Boss->IsOnSummitDais())) return;
    PendingSummitPhaseSave=INDEX_NONE;
    SaveCheckpoint();
}
