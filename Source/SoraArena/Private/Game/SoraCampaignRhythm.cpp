#include "SoraCampaignDirector.h"
#include "Game/SoraCampaignReach.h"
#include "SoraCatalog.h"
#include "SoraCaptions.h"
#include "SoraAudio.h"
#include "Audio/SoraAudioData.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "SoraSettings.h"
#include "SoraWorldBuilder.h"
#include "GameFramework/PlayerController.h"

bool USoraCampaignDirector::PlayerRhythmEligible() const
{
    const auto& M=Mode(); const auto* Hero=M.Hero(); const auto* Space=ActiveSpace();
    if(!Space||!Hero||!M.bCampaign||!M.IsPlaying()||bDialogueHeld||!SoraRhythmRules::Supported(TaskState,Task)||
        Hero->GetEquipment()->IsStaggered()||Hero->GetEquipment()->bReloading||!Space->StepStations.IsValidIndex(TaskState.Step)) return false;
    return Near(ASoraWorldBuilder::Floor(Space->Stations[Space->StepStations[TaskState.Step]]),SoraCampaignReach::Interact);
}
bool USoraCampaignDirector::RhythmAssistActive() const
{
    return RhythmInput.Active&&Mode().Settings()&&Mode().Settings()->RhythmAssist()&&PlayerRhythmEligible()&&
        Mode().Hero()->IsActionHeld(TEXT("Interact"));
}
void USoraCampaignDirector::StopPlayerRhythm(bool bWaitForRelease)
{
    // Ordinary strikes release between every press; release only ends a cue
    // when that press was performing assisted work. A hit/leave ends either.
    if(bWaitForRelease||RhythmInput.Active) { RhythmClock={}; RhythmCueShown=-1; RhythmStrikeMs=-1; }
    RhythmInput={};
    if(bWaitForRelease) SoraCrankInputRules::Stop(RhythmInput);
}
void USoraCampaignDirector::PresentRhythmCue()
{
    const bool Bellows=Task.AlternateTreads&&IsWorkingCrank();
    const int32 Cue=Bellows?(TaskState.ElapsedMs-BellowsCueStarted)/1000:SoraRhythmRules::Cue(RhythmClock,TaskState,Task);
    if(Cue<0||Cue==RhythmCueShown) return;
    RhythmCueShown=Cue;
    const bool Hammer=!Bellows&&Task.Steps[TaskState.Step].PhraseStrikes==8;
    if(!Bellows) WorkshopSound(Hammer?TEXT("HammerCue"):TEXT("LoomCall"),TaskState.Step);
    if(auto* Captions=USoraCaptions::Get(this); Captions&&!Bellows)
        Captions->Show(Hammer?NSLOCTEXT("SoraArena.Rhythm","HammerCue","〔小鎚の合図〕"):
            NSLOCTEXT("SoraArena.Rhythm","LoomCue","〔杼の合図〕"),nullptr,.6f);
    if(auto* Controller=Cast<APlayerController>(Mode().Hero()->GetController()))
        Controller->PlayDynamicForceFeedback(.22f,.035f,true,true,true,true,EDynamicForceFeedbackAction::Start);
}
void USoraCampaignDirector::WorkshopSound(FName Action,int32 Step)
{
    const auto* Space=ActiveSpace();
    if(!Space||!Space->StepStations.IsValidIndex(Step)) return;
    const int32 Station=Space->StepStations[Step];
    if(!Space->Stations.IsValidIndex(Station)) return;
    // The cue originates at the work, not at the hero's eye. Missing Okinu
    // VO remains a needed, unvoiced cue in audio.json; never play a stand-in.
    if(auto* Audio=USoraAudioSubsystem::Get(this))
        Audio->Hear(TEXT("Workshop"),SoraAudioData::FFacts().Text(TEXT("Action"),Action.ToString()),nullptr,
            ASoraWorldBuilder::Floor(Space->Stations[Station],Space->HeightCm+100.f));
}
void USoraCampaignDirector::PresentRhythmResponse(int32 Step)
{
    RhythmStrikeMs=TaskState.ElapsedMs;
    if(Task.Steps[Step].PhraseStrikes==8) WorkshopSound(TEXT("HammerHit"),Step);
}
int32 USoraCampaignDirector::RhythmCuePeriodMs() const
{
    if(Task.AlternateTreads&&IsWorkingCrank()) return 1000;
    return SoraRhythmRules::Active(RhythmClock,TaskState,Task)?Task.Steps[TaskState.Step].BeatMs:0;
}
int32 USoraCampaignDirector::RhythmCueRemainingMs() const
{
    if(Task.AlternateTreads&&IsWorkingCrank()) return 1000-(TaskState.ElapsedMs-BellowsCueStarted)%1000;
    const int32 Period=RhythmCuePeriodMs();
    return Period>0?Period-(TaskState.ElapsedMs-RhythmClock.StartedMs)%Period:0;
}
void USoraCampaignDirector::RhythmResult(SoraBeatRules::EStroke Result,int32 Step)
{
    using SoraBeatRules::EStroke;
    const FSoraBeat* Beat=ActiveBeatData();
    if(!Beat||Result==EStroke::Refused||Result==EStroke::Credited) return;
    if(Result==EStroke::Missed)
    {
        Fire(TEXT("step_failed:")+Beat->StepKinds[Step]);
        Notify(TEXT("この一節をもう一度。済んだ仕事は残る。"),TEXT("Repeat this phrase or pick. Completed work is kept."),2.f);
    }
    else
        Fire(FString::Printf(TEXT("step_complete:%s:%d"),*Beat->StepKinds[Step],Result==EStroke::Counted?TaskState.StepDone:Task.Steps[Step].Count));
    if(Result==EStroke::StepDone) Fire(TEXT("step_start:")+Beat->StepKinds[TaskState.Step]);
    if(Result==EStroke::Finished) Fire(TEXT("output_complete"));
    UpdateObjective();
}
void USoraCampaignDirector::WorkPlayerRhythm()
{
    if(!PlayerRhythmEligible()||RhythmInput.NeedsRelease) return;
    const bool Assist=Mode().Settings()&&Mode().Settings()->RhythmAssist();
    if(Assist) SoraCrankInputRules::Begin(RhythmInput,true);
    if(!SoraRhythmRules::Active(RhythmClock,TaskState,Task))
    {
        SoraRhythmRules::Begin(RhythmClock,TaskState,Task); RhythmCueShown=-1; RhythmStrikeMs=-1;
        PresentRhythmCue();
        return; // The first press asks for a cue; no free first hit.
    }
    if(!Assist&&SoraRhythmRules::Strike(RhythmClock,TaskState,Task))
        PresentRhythmResponse(TaskState.Step);
}
void USoraCampaignDirector::TickPlayerRhythm()
{
    if(!PlayerRhythmEligible())
    {
        if(RhythmClock.Step>=0||RhythmInput.Active) StopPlayerRhythm(true);
        return;
    }
    if(RhythmInput.Active&&!RhythmAssistActive()) StopPlayerRhythm(false);
    if(!SoraRhythmRules::Active(RhythmClock,TaskState,Task)) return;
    PresentRhythmCue();
    const int32 Step=TaskState.Step;
    bool AutoStruck=false;
    const auto Result=SoraRhythmRules::Tick(RhythmClock,TaskState,Task,RhythmAssistActive(),&AutoStruck);
    // Sound the admitted due crossing even if this coarse frame also resolves
    // the window. Full phrase credit (including 700-permille) is separate.
    if(AutoStruck) PresentRhythmResponse(Step);
    RhythmResult(Result,Step);
}
