#include "SoraCampaignDirector.h"
#include "SoraBoss.h"
#include "SoraCatalog.h"
#include "SoraGameEvents.h"
#include "SoraGameMode.h"

void USoraCampaignDirector::CollectorCue(const FSoraBossPhaseEvent& Event)
{
    const FSoraBeat* Beat=ActiveBeatData();
    if(!Mode().bCampaign||Mode().bDeterministicPractice||!Beat||Beat->Id!=TEXT("ch08.b14")||
        Event.Boss!=CampaignBoss()||Event.BossId!=TEXT("boss_val_amort")||Event.PhaseIndex!=2||
        Event.Phase!=ESoraBossPhase::Windup||Event.Detail!=TEXT("amort_final_foreclosure")) return;
    const FString First=TEXT("event:first_foreclosure");
    if(!BeatEvents.Contains(First))
    {
        // This is an authored memory of b09, not another ordinary reading of
        // its line. Replaying it must survive the chapter's Heard deduplication.
        Fire(First,INDEX_NONE,true);
    }
    else if(const ASoraBoss* Boss=CampaignBoss(); Boss&&Boss->HealthPermille()<=10)
    {
        // At the 1% floor the capture reminder returns with each foreclosure;
        // the mentor memory remains once-only for this encounter.
        ShowPrompt(First,BeatIndex);
    }
}
