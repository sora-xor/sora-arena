#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"

void USoraCampaignDirector::StartLines()
{
    const FSoraBeat* Beat=ActiveBeatData();
    if(!Beat||bLinesStarted) return;
    bLinesStarted=true;
    // Event rows own the order and modes, including lines enqueued by
    // lines_done. Eagerly adding the beat's whole list skips later triggers.
    const bool bAuthored=ActiveChapter()->Triggers.ContainsByPredicate([&](const FSoraDialogueTrigger& Trigger)
        { return Trigger.Beat==BeatIndex&&Trigger.On==Beat->LinesEvent; });
    if(!bAuthored) Enqueue(Beat->Lines,true,TEXT("ambient"));
    UpdateObjective();
}

void USoraCampaignDirector::Enqueue(const TArray<int32>& Lines,bool bForce,const FString& TriggerMode)
{
    const FSoraChapter& Chapter=*ActiveChapter();
    for(const int32 Line:Lines)
    {
        const FSoraDialogueCue& Cue=Chapter.Dialogue[Line];
        if(!bForce&&Heard.Contains(Line)&&!Cue.bRepeatable) continue;
        Heard.Add(Line);
        const bool bBlocking=(Cue.Mode.IsEmpty()?TriggerMode:Cue.Mode)==TEXT("blocking");
        if(Queue.IsEmpty()) LineRemaining=Cue.DurationSeconds;
        Queue.Add({Line,Cue.Beat,bBlocking});
    }
    RefreshDialogueHold();
}

void USoraCampaignDirector::RefreshDialogueHold()
{
    const bool bBlockingHead=!Queue.IsEmpty()&&Queue[0].bBlocking;
    if(!bBlockingHead) { BlockingSeconds=0.f; bBlockingLimitReached=false; }
    const ASoraGameMode& M=Mode();
    const bool bWanted=bBlockingHead&&!bBlockingLimitReached&&M.bCampaign&&!M.bDefeated&&!M.bChapterComplete;
    if(bDialogueHeld==bWanted) return;
    bDialogueHeld=bWanted;
    if(bWanted)
    {
        CancelFoundryWork();
        CancelHorseTreatment();
        CancelCopying();
        HeldWork=EHeldWork::None; HeldPoint=INDEX_NONE; HeldMs=0; bHeldWatched=false;
        SealTarget.Reset();
    }
    if(ASoraPlayerCharacter* Hero=M.Hero()) Hero->ResetDialogueInput();
}

void USoraCampaignDirector::ClearDialogue()
{
    Queue.Reset(); LineRemaining=0.f;
    RefreshDialogueHold();
}

void USoraCampaignDirector::TickDialogue(float DeltaSeconds)
{
    float Remaining=FMath::Max(0.f,DeltaSeconds);
    const FSoraChapter* Chapter=ActiveChapter();
    while(Chapter&&!Queue.IsEmpty()&&Remaining>0.f)
    {
        const float Step=FMath::Min(Remaining,LineRemaining);
        if(bDialogueHeld)
        {
            BlockingSeconds+=Step;
            if(BlockingSeconds>=20.f) bBlockingLimitReached=true;
        }
        LineRemaining-=Step;
        Remaining-=Step;
        if(LineRemaining>0.f) { RefreshDialogueHold(); break; }

        const FQueuedLine Finished=Queue[0];
        Queue.RemoveAt(0);
        FinishedLines.Add(Finished.Line);
        if(Finished.Beat==BeatIndex) EpilogueLineFinished(Chapter->Dialogue[Finished.Line].Id);
        // Establish the new head before firing callbacks: an empty queue can
        // be filled reentrantly, and its first line gets exactly its own time.
        LineRemaining=Queue.IsEmpty()?0.f:Chapter->Dialogue[Queue[0].Line].DurationSeconds;
        Fire(TEXT("lines_done:")+Chapter->Dialogue[Finished.Line].Id,Finished.Beat);
        if(ActiveChapter()!=Chapter) return;
        const FSoraBeat* Beat=ActiveBeatData();
        if(Beat&&Finished.Beat==BeatIndex&&!Beat->BlockingLines.IsEmpty()&&Finished.Line==Beat->BlockingLines.Last())
            Fire(TEXT("blocking_end"));
        RefreshDialogueHold();
    }
}

bool USoraCampaignDirector::DialogueLinesDone() const
{
    const FSoraBeat* Beat=ActiveBeatData();
    const FSoraChapter* Chapter=ActiveChapter();
    if(!Beat||!Chapter) return false;
    for(const int32 Line:Beat->Lines)
    {
        if(FinishedLines.Contains(Line)) continue;
        // A branch response or collectible-gated exchange is optional only
        // when no eligible non-branch trigger can produce it. Once queued,
        // it must finish even if a condition changes meanwhile.
        if(Heard.Contains(Line)) return false;
        bool bHasTrigger=false,bRequired=false;
        for(const FSoraDialogueTrigger& Trigger:Chapter->Triggers)
        {
            if(Trigger.Beat!=BeatIndex||!Trigger.Lines.Contains(Line)) continue;
            bHasTrigger=true;
            if(!Trigger.On.StartsWith(TEXT("branch:"))&&
                (CollectedMask()&Trigger.RequiresCollectible)==Trigger.RequiresCollectible&&
                (BeatState.FlagsMask&Trigger.RequiresFlags)==Trigger.RequiresFlags) bRequired=true;
        }
        if(!bHasTrigger||bRequired) return false;
    }
    return true;
}
