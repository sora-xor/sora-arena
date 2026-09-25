#include "SoraCampaignDirector.h"
#include "SoraBoss.h"
#include "SoraCampaignRules.h"
#include "SoraCatalog.h"
#include "SoraEnemy.h"
#include "SoraGameEvents.h"
#include "SoraGameMode.h"
#include "SoraInputStates.h"
#include "SoraPlayerCharacter.h"
#include "SoraProjectile.h"
#include "SoraSaveGame.h"
#include "SoraWorldBuilder.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"
#include "HAL/FileManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

namespace
{
constexpr int32 LastChapter = SoraCampaignRules::ChapterCount - 1;
// Anchor radii (2D, cm): working an objective, arriving, and holding ground.
constexpr float InteractRadius = 260.f;
constexpr float ReachRadius = 320.f;
constexpr float HoldRadius = 420.f;
constexpr float PromptSeconds = 8.f;

// The dojo forms a chapter's completed lesson duels taught; a checkpoint
// taken at a beat's start holds exactly these.
unsigned LessonsTaught(const FSoraChapter& Chapter, unsigned CompletedMask)
{
    unsigned Mask = 0u;
    for (int32 Index = 0; Index < Chapter.Beats.Num(); ++Index)
        if ((CompletedMask & SoraBeatRules::BeatBit(Index)) != 0u && Chapter.Beats[Index].Goal == ESoraBeatGoal::Lessons)
            Mask |= Chapter.Beats[Index].LessonMask;
    return Mask;
}
FString WeaponNames(unsigned Mask, bool bEnglish)
{
    FString Names;
    for (int32 Id = 0; Id < SoraBeatRules::WeaponCount; ++Id)
        if ((Mask & (1u << Id)) != 0u)
        {
            const FSoraWeapon& Weapon = FSoraCatalog::Get().Weapon(Id);
            Names += (Names.IsEmpty() ? TEXT("") : bEnglish ? TEXT(", ") : TEXT("、")) + (bEnglish ? Weapon.NameEnglish : Weapon.Name);
        }
    return Names;
}
}

USoraCampaignDirector::USoraCampaignDirector()
{
    // The beat clock runs in the director's own tick; the paused menu stops it.
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.bStartWithTickEnabled=true;
}
ASoraGameMode& USoraCampaignDirector::Mode() const { return *CastChecked<ASoraGameMode>(GetOwner()); }
const FSoraChapter* USoraCampaignDirector::ActiveChapter() const
{
    return FSoraCatalog::Get().IsReady()?&FSoraCatalog::Get().Chapter(ChapterId):nullptr;
}
const FSoraBeat* USoraCampaignDirector::ActiveBeatData() const
{
    const FSoraChapter* Chapter=ActiveChapter();
    return Chapter&&Mode().bCampaign&&Chapter->Beats.IsValidIndex(BeatIndex)?&Chapter->Beats[BeatIndex]:nullptr;
}
bool USoraCampaignDirector::LoadSave()
{
    ASoraGameMode& M=Mode();
    const FSoraCatalog& Catalog=FSoraCatalog::Get();
    Save=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(M.SaveSlotName,0));
    // Only a schema-6 save whose chapter, entry unlocks and collectibles a
    // route through the earlier chapters reaches is read; anything else is a
    // fresh campaign (the unreadable file is replaced at the next save).
    const bool bReadable=Save&&Catalog.IsReady()&&Save->SaveSchema==USoraSaveGame::Schema&&
        Save->CurrentChapter>=0&&Save->CurrentChapter<=Save->HighestChapter&&Save->HighestChapter<=LastChapter&&
        SoraBeatRules::EntryValid(static_cast<unsigned>(Save->ChapterEntryWeapons),
            Catalog.RouteMinimumWeapons(Save->CurrentChapter),Catalog.EarlierWeapons(Save->CurrentChapter))&&
        static_cast<unsigned>(Save->ChapterEntryMechanics)==Catalog.EarlierMechanics(Save->CurrentChapter)&&
        SoraCampaignRules::CollectiblesValid(static_cast<unsigned long long>(Save->Collectibles),Save->HighestChapter)&&
        (!Save->CampaignComplete||Save->CurrentChapter==LastChapter);
    if(!bReadable)
    {
        Save=Cast<USoraSaveGame>(UGameplayStatics::CreateSaveGameObject(USoraSaveGame::StaticClass()));
        if(!Save) return false;
        Save->SaveSchema=USoraSaveGame::Schema;
    }
    ChapterId=Save->CurrentChapter; M.SelectedClass=FMath::Clamp(Save->SelectedClass,0,5);
    M.bEnglishSubtitles=Save->EnglishSubtitles;
    EntryWeapons=static_cast<unsigned>(Save->ChapterEntryWeapons);
    EntryMechanics=static_cast<unsigned>(Save->ChapterEntryMechanics);
    bCampaignComplete=Save->CampaignComplete;
    if(Catalog.IsReady()) M.MapId=Catalog.Chapter(ChapterId).Map;
    return true;
}
void USoraCampaignDirector::ResetRound()
{
    ASoraGameMode& M=Mode();
    ASoraWorldBuilder* WorldBuilder=M.Arena();
    const bool bCampaign=M.bCampaign;
    // A shell fired before death or chapter advance must never damage the
    // restored encounter or score a defeat against its fresh opponents.
    ClearOfflineProjectiles();
    ClearOpponents();
    Kills=0; KillsNeeded=0; Spawned=0; InteractCount=0; HoldSeconds=0.f; bReached=false; bLinesStarted=false;
    bChapterOpening=false; CinematicSeconds=0.f; DojoLessonMask=0u;
    Queue.Reset(); LineRemaining=0.f; Heard.Reset(); FiredTriggers.Reset(); PromptIndex=INDEX_NONE; PromptRemaining=0.f;
    BeatIndex=INDEX_NONE; BeatPhase=0; ArenaSitesMask=0; bArenaComplete=false;
    BeatState={0u,0u,EntryWeapons,EntryMechanics,false};
    M.RoundTime=0; M.bDefeated=false; M.bChapterComplete=false; M.TitleCardTime=0.f;
    M.Notice.Empty(); M.NoticeEnglish.Empty(); M.NoticeTime=0.f;
    WorldBuilder->Build(M.MapId,bCampaign?ActiveChapter():nullptr);
    ApplyLoadout();
    if(!bCampaign)
    {
        KillsNeeded=SoraCampaignRules::ArenaDefeats;
        for(int32 I=0;I<4;++I) SpawnOne();
        M.Notice=TEXT("稽古場です。特殊武器を自由に試せます。XOR や NFT は預けません。");
        M.NoticeEnglish=TEXT("Training arena. All special weapons are available for practice; no assets are bonded.");
        M.NoticeTime=12.f;
        return;
    }
    const FSoraChapter& Chapter=*ActiveChapter();
    // Completion is durable after the final chapter's checkpoint is cleared:
    // a liberated campaign reopens on the freed city, not the last battle.
    const bool bLiberated=bCampaignComplete&&ChapterId==LastChapter;
    bool bResumed=false;
    if(bLiberated)
    {
        for(int32 Index=0;Index<Chapter.Rules.Num();++Index)
            if(!Chapter.Rules[Index].Optional) SoraBeatRules::CompleteBeat(BeatState,Chapter.Rules.GetData(),Chapter.Rules.Num(),Index);
        SoraBeatRules::FinishChapter(BeatState,Chapter.Rules.GetData(),Chapter.Rules.Num());
        WorldBuilder->RestoreActivatedMask(SoraBeatRules::AllSitesMask);
        M.bChapterComplete=true;
        Notify(TEXT("猫柳生は自由だ。生み出す力は、民の手にある。"),TEXT("Nyaagyu is free. Production belongs to its people."),12.f);
    }
    else
    {
        bResumed=LoadCheckpoint();
        if(M.bChapterComplete)
            Notify(TEXT("この章は終えた。Enter で物語を進めよう。"),TEXT("This chapter is complete. Press Enter to continue the story."),12.f);
    }
    if(auto* Events=USoraGameEvents::Get(this))
    {
        FSoraChapterEvent Started;
        Started.ChapterId=ChapterId; Started.bResumed=bResumed||bLiberated; Started.bLiberated=bLiberated;
        Events->OnChapterStarted.Broadcast(Started);
    }
    if(M.bChapterComplete) { UpdateObjective(); return; }
    const int32 Beat=bResumed?BeatIndex:SoraBeatRules::NextBeat(BeatState,Chapter.Rules.GetData(),Chapter.Rules.Num());
    const int32 Phase=bResumed?BeatPhase:0;
    // A fresh chapter opens on its first cinematic, which carries the title card.
    bChapterOpening=!bResumed; BeatIndex=INDEX_NONE;
    BeginBeat(Beat,Phase,bResumed);
    if(bResumed&&M.NoticeTime<=0.f)
        Notify(TEXT("復旧記録から再開した。"),TEXT("Checkpoint restored."),6.f);
}
bool USoraCampaignDirector::LoadCheckpoint()
{
    ASoraGameMode& M=Mode();
    if(!Save||Save->CheckpointChapter!=ChapterId) return false;
    const FSoraChapter& Chapter=*ActiveChapter();
    const SoraBeatRules::FProgress Saved{static_cast<unsigned>(Save->CheckpointBeatsMask),
        static_cast<unsigned>(Save->CheckpointSitesMask),static_cast<unsigned>(Save->CheckpointWeapons),
        static_cast<unsigned>(Save->CheckpointMechanics),Save->CheckpointComplete};
    const unsigned Lessons=static_cast<unsigned>(Save->CheckpointDojoLessonMask);
    const int32 Beat=Save->CheckpointBeat,Phase=Save->CheckpointPhase;
    const auto* Gates=Chapter.Rules.GetData(); const int32 Count=Chapter.Rules.Num();
    // The start of a required beat (or a later boss or duel phase), or a
    // finished chapter at its result screen; either way exactly what its
    // completed beats earn from the chapter's entry unlocks.
    bool bValid=Beat==INDEX_NONE
        ?Saved.Complete&&Phase==0&&SoraBeatRules::ProgressValid(Saved,Gates,Count,EntryWeapons,EntryMechanics)
        :!Saved.Complete&&Chapter.Rules.IsValidIndex(Beat)&&!Chapter.Rules[Beat].Optional&&
            SoraBeatRules::CheckpointValid(Saved,Gates,Count,EntryWeapons,EntryMechanics,Beat,Phase);
    // Chapter one's forms are exactly those its completed lesson duels taught.
    bValid&=ChapterId==0
        ?SoraDojoRules::CheckpointValid({Lessons},0,Saved.SitesMask)&&Lessons==LessonsTaught(Chapter,Saved.CompletedMask)
        :Lessons==0u;
    if(!bValid) { ClearCheckpoint(); return false; }
    BeatState=Saved; DojoLessonMask=Lessons;
    BeatIndex=Beat; BeatPhase=Phase;
    M.Arena()->RestoreActivatedMask(static_cast<int32>(Saved.SitesMask));
    M.bChapterComplete=Saved.Complete;
    return true;
}
void USoraCampaignDirector::ApplyLoadout()
{
    ASoraGameMode& M=Mode();
    ASoraPlayerCharacter* Player=M.Hero();
    if(!Player||!M.Arena()) return;
    Player->GetCharacterMovement()->StopMovementImmediately();
    Player->SetActorLocation(M.Arena()->PlayerStart(),false,nullptr,ETeleportType::TeleportPhysics);
    Player->SetActorRotation(FRotator::ZeroRotator); if(Player->GetController()) Player->GetController()->SetControlRotation(FRotator::ZeroRotator);
    // The campaign follows Nyaakoto. The six-class selection is for Arena
    // practice and cannot rewrite the offline protagonist's loadout.
    Player->ApplyClass(M.bCampaign?0:M.SelectedClass);
    Player->SetDojoTraining(M.bCampaign&&ChapterId==0);
    Player->SetCampaignHeroLoadout(M.bCampaign&&ChapterId>0);
}
void USoraCampaignDirector::BeginBeat(int32 Index,int32 Phase,bool bResumed)
{
    ASoraGameMode& M=Mode();
    const FSoraChapter& Chapter=*ActiveChapter();
    const FSoraBeat& Beat=Chapter.Beats[Index];
    const ESoraOpponent Previous=Chapter.Beats.IsValidIndex(BeatIndex)?Chapter.Beats[BeatIndex].Opponent:ESoraOpponent::None;
    if(Index!=0||bResumed) bChapterOpening=false;
    BeatIndex=Index; BeatPhase=Phase;
    Kills=0; Spawned=0; InteractCount=0; HoldSeconds=0.f; bReached=false; bLinesStarted=false; CinematicSeconds=0.f;
    KillsNeeded=Beat.Goal==ESoraBeatGoal::Defeat||Beat.Goal==ESoraBeatGoal::Lessons?Beat.GoalCount:Beat.Opponents;
    // Consecutive lesson duels keep their pupil on the floor; any other
    // change of beat clears the field.
    if(Previous==ESoraOpponent::Pupil&&Beat.Opponent==ESoraOpponent::Pupil&&Beat.Goal==ESoraBeatGoal::Lessons)
    {
        Enemies.RemoveAll([](const TObjectPtr<ASoraEnemy>& Enemy) { return !IsValid(Enemy)||!Enemy->IsAlive(); });
        Spawned=FMath::Min(Enemies.Num(),Beat.Opponents);
    }
    else ClearOpponents();
    // Saves at the beat's start; a restored checkpoint is already on disk.
    if(!bResumed&&Phase==0&&Chapter.Rules[Index].Checkpoint) SaveCheckpoint();
    switch(Beat.Goal)
    {
    case ESoraBeatGoal::Cinematic:
        // Until Sequencer cinematics land, the letterboxed card holds play,
        // the round timer and dialogue while the subtitles run on its clock.
        M.TitleCardTime=Beat.GoalSeconds;
        break;
    case ESoraBeatGoal::Lines:
        if(!Beat.bLinesAtAnchor) { Enqueue(Beat.Lines,true); bLinesStarted=true; }
        break;
    default:
        break;
    }
    SpawnOpponents();
    Fire(TEXT("beat_start"));
    if(!Beat.PhaseHealthPercent.IsEmpty()) Fire(FString::Printf(TEXT("boss_phase:%d"),Phase+1));
    UpdateObjective();
    BroadcastBeat(true,bResumed);
    Telemetry(bResumed?TEXT("resume"):TEXT("start"));
}
void USoraCampaignDirector::CompleteActiveBeat()
{
    ASoraGameMode& M=Mode();
    const FSoraChapter& Chapter=*ActiveChapter();
    if(!Chapter.Beats.IsValidIndex(BeatIndex)) return;
    const int32 Index=BeatIndex;
    const FSoraBeat& Beat=Chapter.Beats[Index];
    SoraBeatRules::FProgress Next=BeatState;
    if(!SoraBeatRules::CompleteBeat(Next,Chapter.Rules.GetData(),Chapter.Rules.Num(),Index)) return;
    const unsigned NewWeapons=Next.WeaponsMask&~BeatState.WeaponsMask;
    BeatState=Next;
    if(Beat.Goal==ESoraBeatGoal::Cinematic) M.TitleCardTime=0.f;
    const int32 Site=Chapter.Rules[Index].Site;
    FString Japanese,English;
    if(Site>=0)
    {
        M.Arena()->ActivateSite(Site);
        if(ASoraPlayerCharacter* Player=M.Hero()) Player->Heal(22.f);
        Japanese=Chapter.Sites[Site].Restored; English=Chapter.Sites[Site].RestoredEnglish;
        if(auto* Events=USoraGameEvents::Get(this))
        {
            FSoraSiteRestoredEvent Restored;
            Restored.ChapterId=ChapterId; Restored.SiteIndex=Site; Restored.bCampaign=true; Restored.Kind=Chapter.Sites[Site].Kind;
            Events->OnSiteRestored.Broadcast(Restored);
        }
        Fire(FString::Printf(TEXT("site_restored:%d"),Site));
    }
    if(NewWeapons)
    {
        Japanese+=(Japanese.IsEmpty()?TEXT(""):TEXT(" "))+FString::Printf(TEXT("新たな武器：%s"),*WeaponNames(NewWeapons,false));
        English+=(English.IsEmpty()?TEXT(""):TEXT(" "))+FString::Printf(TEXT("New weapon: %s."),*WeaponNames(NewWeapons,true));
    }
    if(!Japanese.IsEmpty()) Notify(Japanese,English,8.f);
    Collect(Index);
    Fire(TEXT("beat_complete"));
    BroadcastBeat(false,false);
    Telemetry(TEXT("complete"));
    const int32 NextBeat=SoraBeatRules::NextBeat(BeatState,Chapter.Rules.GetData(),Chapter.Rules.Num());
    if(NextBeat==INDEX_NONE) FinishChapter();
    else BeginBeat(NextBeat,0,false);
}
void USoraCampaignDirector::FinishChapter()
{
    ASoraGameMode& M=Mode();
    const FSoraChapter& Chapter=*ActiveChapter();
    if(!SoraBeatRules::FinishChapter(BeatState,Chapter.Rules.GetData(),Chapter.Rules.Num())) return;
    ClearOpponents();
    M.bChapterComplete=true;
    Save->HighestChapter=FMath::Max(Save->HighestChapter,FMath::Min(LastChapter,ChapterId+1));
    const bool bLiberated=SoraCampaignRules::CampaignLiberated(ChapterId,LastChapter,true);
    if(bLiberated) bCampaignComplete=true;
    Notify(bLiberated?TEXT("猫柳生は自由だ。生み出す力は、民の手にある。")
            :ChapterId==0?TEXT("道場の修行を終えた。Enter で物語を進めよう。"):TEXT("街区を解放した。Enter で次の戦いへ。"),
        bLiberated?TEXT("Nyaagyu is free. Production belongs to its people.")
            :ChapterId==0?TEXT("Dojo training complete. Press Enter to continue the story."):TEXT("District liberated. Press Enter to continue."),
        12.f);
    SaveCheckpoint();
    UpdateObjective();
    Telemetry(TEXT("chapter_complete"));
    if(auto* Events=USoraGameEvents::Get(this))
    {
        FSoraChapterEvent Completed;
        Completed.ChapterId=ChapterId; Completed.bLiberated=bLiberated;
        Events->OnChapterCompleted.Broadcast(Completed);
    }
}
void USoraCampaignDirector::CompleteOptional(int32 Index)
{
    const FSoraChapter& Chapter=*ActiveChapter();
    SoraBeatRules::FProgress Next=BeatState;
    if(!Chapter.Rules[Index].Optional||!SoraBeatRules::CompleteBeat(Next,Chapter.Rules.GetData(),Chapter.Rules.Num(),Index)) return;
    const unsigned NewWeapons=Next.WeaponsMask&~BeatState.WeaponsMask;
    BeatState=Next;
    Collect(Index);
    Fire(TEXT("beat_complete"),Index);
    if(NewWeapons)
        Notify(FString::Printf(TEXT("新たな武器：%s"),*WeaponNames(NewWeapons,false)),
            FString::Printf(TEXT("New weapon: %s."),*WeaponNames(NewWeapons,true)),8.f);
    if(auto* Events=USoraGameEvents::Get(this))
    {
        FSoraBeatEvent Event;
        Event.ChapterId=ChapterId; Event.BeatIndex=Index; Event.BeatId=Chapter.Beats[Index].Id; Event.bOptional=true;
        Events->OnBeatCompleted.Broadcast(Event);
    }
    UpdateObjective();
    // The find is kept at once; the beat's completion reaches the next checkpoint.
    SaveProgress();
}
void USoraCampaignDirector::Collect(int32 Beat)
{
    const FSoraChapter& Chapter=*ActiveChapter();
    unsigned long long Found=0ull;
    FString Japanese,English;
    for(const FSoraCollectible& Item:Chapter.Collectibles)
    {
        const unsigned long long Bit=SoraCampaignRules::CollectibleBit(ChapterId,Item.MaskBit);
        if(!Item.Beats.Contains(Beat)||(static_cast<unsigned long long>(Save->Collectibles)&Bit)!=0ull) continue;
        Found|=Bit;
        for(const FSoraCollectibleCategory& Category:FSoraCatalog::Get().CollectibleCategories)
            if(Category.Id==Item.Category&&!Japanese.Contains(Category.Japanese))
            {
                Japanese+=(Japanese.IsEmpty()?TEXT(""):TEXT("、"))+Category.Japanese;
                English+=(English.IsEmpty()?TEXT(""):TEXT(", "))+Category.English;
            }
    }
    if(!Found) return;
    Save->Collectibles=static_cast<int64>(static_cast<unsigned long long>(Save->Collectibles)|Found);
    if(Mode().NoticeTime<=0.f) Notify(FString::Printf(TEXT("見つけた：%s"),*Japanese),FString::Printf(TEXT("Found: %s."),*English),6.f);
}
void USoraCampaignDirector::TickComponent(float DeltaTime,ELevelTick TickType,FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime,TickType,ThisTickFunction);
    ASoraGameMode& M=Mode();
    const FSoraBeat* Beat=ActiveBeatData();
    if(!Beat||!Save||M.bDeterministicPractice||M.bMenu||M.bDefeated||M.bChapterComplete) return;
    if(M.InputState()==SoraInput::Card)
    {
        CinematicSeconds=Beat->Goal==ESoraBeatGoal::Cinematic?FMath::Max(0.f,Beat->GoalSeconds-M.TitleCardTime):0.f;
        return;
    }
    // The card closed on its own: the cinematic is over.
    if(Beat->Goal==ESoraBeatGoal::Cinematic) { CompleteActiveBeat(); return; }
    PromptRemaining=FMath::Max(0.f,PromptRemaining-DeltaTime);
    TickDialogue(DeltaTime);
    TickBeat(DeltaTime);
}
void USoraCampaignDirector::TickDialogue(float DeltaSeconds)
{
    if(Queue.IsEmpty()) return;
    LineRemaining-=DeltaSeconds;
    while(!Queue.IsEmpty()&&LineRemaining<=0.f)
    {
        Queue.RemoveAt(0);
        if(!Queue.IsEmpty()) LineRemaining+=ActiveChapter()->Dialogue[Queue[0]].DurationSeconds;
    }
    if(Queue.IsEmpty()) LineRemaining=0.f;
}
void USoraCampaignDirector::TickBeat(float DeltaSeconds)
{
    const FSoraBeat& Beat=*ActiveBeatData();
    CheckPhase();
    FVector Anchor;
    const bool bAtAnchor=ObjectiveAnchor(Anchor)&&Near(Anchor,Beat.Goal==ESoraBeatGoal::Hold?HoldRadius:ReachRadius);
    switch(Beat.Goal)
    {
    case ESoraBeatGoal::Lines:
        if(!bLinesStarted)
        {
            // A volume trigger starts the lines on arrival; an interact trigger waits for E.
            if(bAtAnchor&&!Beat.bLinesOnInteract)
            {
                Enqueue(Beat.Lines,true); bLinesStarted=true;
                Fire(Beat.AnchorEvent); UpdateObjective();
            }
        }
        else if(Queue.IsEmpty())
        {
            if(!Beat.bReachAfterLines) { CompleteActiveBeat(); return; }
            if(!bReached) { bReached=true; UpdateObjective(); }
            if(bAtAnchor) { CompleteActiveBeat(); return; }
        }
        break;
    case ESoraBeatGoal::Hold:
        if(bAtAnchor&&HoldSeconds<Beat.GoalSeconds)
        {
            const float Before=HoldSeconds/Beat.GoalSeconds;
            HoldSeconds=FMath::Min(Beat.GoalSeconds,HoldSeconds+DeltaSeconds);
            for(const FSoraDialogueTrigger& Trigger:ActiveChapter()->Triggers)
                if(Trigger.Beat==BeatIndex&&Trigger.On.StartsWith(TEXT("progress_at:")))
                {
                    const float At=FCString::Atof(*Trigger.On.RightChop(12));
                    if(Before<At&&HoldSeconds/Beat.GoalSeconds>=At) Fire(Trigger.On);
                }
        }
        if(HoldSeconds>=Beat.GoalSeconds&&WavesCleared()) { CompleteActiveBeat(); return; }
        break;
    case ESoraBeatGoal::Reach:
        if(bAtAnchor&&!bReached) { bReached=true; Fire(Beat.AnchorEvent); }
        if(bReached&&WavesCleared()) { CompleteActiveBeat(); return; }
        break;
    case ESoraBeatGoal::Interact:
        if(InteractCount>=Beat.GoalCount&&WavesCleared()) { CompleteActiveBeat(); return; }
        break;
    default:
        break;
    }
}
void USoraCampaignDirector::CheckPhase()
{
    const FSoraBeat& Beat=*ActiveBeatData();
    if(Beat.PhaseHealthPercent.Num()<2) return;
    const ASoraEnemy* Opponent=nullptr;
    for(const auto& Enemy:Enemies) if(IsValid(Enemy)&&Enemy->IsAlive()) { Opponent=Enemy; break; }
    if(!Opponent||Opponent->MaxHealth<=0.f) return;
    const float Percent=100.f*Opponent->Health/Opponent->MaxHealth;
    int32 Phase=BeatPhase;
    while(Beat.PhaseHealthPercent.IsValidIndex(Phase+1)&&Percent<=Beat.PhaseHealthPercent[Phase+1]) ++Phase;
    if(Phase==BeatPhase) return;
    BeatPhase=Phase;
    Fire(FString::Printf(TEXT("boss_phase:%d"),Phase+1));
    // A long boss or duel also saves at each later phase; the opponent then
    // returns at that phase's health.
    if(Phase<=ActiveChapter()->Rules[BeatIndex].PhaseCheckpoints) SaveCheckpoint();
    BroadcastBeat(true,false);
    Telemetry(TEXT("phase"));
}
void USoraCampaignDirector::SkipCinematic()
{
    ASoraGameMode& M=Mode();
    const FSoraBeat* Beat=ActiveBeatData();
    if(!Beat||Beat->Goal!=ESoraBeatGoal::Cinematic) { M.TitleCardTime=0.f; return; }
    if(!Beat->bSkippable) return;
    Telemetry(TEXT("skip"));
    CompleteActiveBeat();
}
void USoraCampaignDirector::SpawnOpponents()
{
    const FSoraBeat* Beat=ActiveBeatData();
    if(!Beat) return;
    int32 Alive=0;
    for(const auto& Enemy:Enemies) Alive+=IsValid(Enemy)&&Enemy->IsAlive();
    while(Spawned<Beat->Opponents&&Alive<Beat->MaxAlive) { SpawnOne(); ++Alive; }
}
void USoraCampaignDirector::SpawnOne()
{
    ASoraGameMode& M=Mode();
    ASoraWorldBuilder* WorldBuilder=M.Arena();
    const FSoraBeat* Beat=ActiveBeatData();
    const ESoraOpponent Kind=M.bCampaign?(Beat?Beat->Opponent:ESoraOpponent::None):ESoraOpponent::Invader;
    if(!WorldBuilder||Kind==ESoraOpponent::None) return;
    FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;
    ASoraEnemy* Enemy=nullptr;
    if(Kind==ESoraOpponent::Boss)
    {
        auto* Boss=GetWorld()->SpawnActor<ASoraBoss>(WorldBuilder->SpawnPoint(Spawned),FRotator(0,180,0),Params);
        if(!Boss) return;
        Boss->InitCollector(Spawned);
        BossActor=Boss;
        Enemy=Boss;
    }
    else
    {
        Enemy=GetWorld()->SpawnActor<ASoraEnemy>(WorldBuilder->SpawnPoint(Spawned),FRotator(0,180,0),Params);
        if(!Enemy) return;
        if(Kind==ESoraOpponent::Pupil) Enemy->InitDojoPupil(Spawned);
        else Enemy->InitInvader(Spawned);
    }
    // A boss or duel restored at a later phase returns at that phase's health.
    if(Beat&&Beat->PhaseHealthPercent.IsValidIndex(BeatPhase))
        Enemy->Health=Enemy->MaxHealth*Beat->PhaseHealthPercent[BeatPhase]/100.f;
    Enemies.Add(Enemy); ++Spawned;
}
void USoraCampaignDirector::ClearOpponents()
{
    // A falling opponent removes itself after its lifespan; the living leave now.
    for(const auto& Enemy:Enemies) if(IsValid(Enemy)&&Enemy->IsAlive()) Enemy->Destroy();
    Enemies.Reset(); BossActor=nullptr; Spawned=0;
}
bool USoraCampaignDirector::WavesCleared() const
{
    const FSoraBeat* Beat=ActiveBeatData();
    return !Beat||Kills>=Beat->Opponents;
}
void USoraCampaignDirector::ClearEncounter()
{
    ClearOpponents();
    ClearOfflineProjectiles();
    Kills=0;
    Queue.Reset(); LineRemaining=0.f; PromptRemaining=0.f;
    if(ASoraWorldBuilder* WorldBuilder=Mode().Arena()) { WorldBuilder->ShowObjective(nullptr); WorldBuilder->ShowCaches({}); }
}
const ASoraBoss* USoraCampaignDirector::CampaignBoss() const
{
    return IsValid(BossActor)&&BossActor->IsAlive() ? BossActor.Get() : nullptr;
}
void USoraCampaignDirector::Enqueue(const TArray<int32>& Lines,bool bForce)
{
    const FSoraChapter& Chapter=*ActiveChapter();
    for(const int32 Line:Lines)
    {
        // Lines never repeat in a round unless the script marks them repeatable.
        if(!bForce&&Heard.Contains(Line)&&!Chapter.Dialogue[Line].bRepeatable) continue;
        Heard.Add(Line);
        if(Queue.IsEmpty()) LineRemaining=Chapter.Dialogue[Line].DurationSeconds;
        Queue.Add(Line);
    }
}
void USoraCampaignDirector::Fire(const FString& Event,int32 Beat)
{
    const FSoraChapter* Chapter=ActiveChapter();
    if(Beat==INDEX_NONE) Beat=BeatIndex;
    if(!Chapter||Event.IsEmpty()) return;
    for(int32 Index=0;Index<Chapter->Triggers.Num();++Index)
    {
        const FSoraDialogueTrigger& Trigger=Chapter->Triggers[Index];
        if(Trigger.Beat!=Beat||Trigger.On!=Event||(!Trigger.bRepeatable&&FiredTriggers.Contains(Index))) continue;
        FiredTriggers.Add(Index);
        Enqueue(Trigger.Lines,false);
    }
    ShowPrompt(Event,Beat);
}
void USoraCampaignDirector::ShowPrompt(const FString& Event,int32 Beat)
{
    const FSoraChapter* Chapter=ActiveChapter();
    if(!Chapter) return;
    for(int32 Index=0;Index<Chapter->Prompts.Num();++Index)
    {
        const FSoraPrompt& Prompt=Chapter->Prompts[Index];
        if(Prompt.Beats.Contains(Beat)&&(Prompt.On==Event||(Prompt.On.IsEmpty()&&Event==TEXT("beat_start"))))
        {
            PromptIndex=Index; PromptRemaining=PromptSeconds;
            return;
        }
    }
}
const FSoraPrompt* USoraCampaignDirector::CurrentPrompt() const
{
    const FSoraChapter* Chapter=ActiveChapter();
    return Chapter&&Mode().bCampaign&&PromptRemaining>0.f&&Chapter->Prompts.IsValidIndex(PromptIndex)?&Chapter->Prompts[PromptIndex]:nullptr;
}
const FSoraDialogueCue* USoraCampaignDirector::CurrentDialogueCue() const
{
    const ASoraGameMode& M=Mode();
    const FSoraBeat* Beat=ActiveBeatData();
    if(!Beat||M.bMenu||M.bDefeated||M.bChapterComplete) return nullptr;
    const FSoraChapter& Chapter=*ActiveChapter();
    if(M.InputState()==SoraInput::Card)
    {
        if(Beat->Goal!=ESoraBeatGoal::Cinematic) return nullptr;
        // Subtitles run on the cinematic's own clock.
        const int32 Ms=FMath::FloorToInt32(CinematicElapsed()*1000.f);
        for(const FSoraDialogueTrigger& Trigger:Chapter.Triggers)
            if(Trigger.Beat==BeatIndex&&Trigger.On==TEXT("subtitle")&&Ms>=Trigger.AtMs&&
                Ms<Trigger.AtMs+FMath::CeilToInt32(Chapter.Dialogue[Trigger.Lines[0]].DurationSeconds*1000.f))
                return &Chapter.Dialogue[Trigger.Lines[0]];
        return nullptr;
    }
    return M.IsPlaying()&&!Queue.IsEmpty()?&Chapter.Dialogue[Queue[0]]:nullptr;
}
float USoraCampaignDirector::CinematicElapsed() const
{
    const FSoraBeat* Beat=ActiveBeatData();
    return Beat&&Beat->Goal==ESoraBeatGoal::Cinematic?FMath::Max(0.f,Beat->GoalSeconds-Mode().TitleCardTime):0.f;
}
bool USoraCampaignDirector::ObjectiveAnchor(FVector& Location) const
{
    const ASoraGameMode& M=Mode();
    const FSoraBeat* Beat=ActiveBeatData();
    if(!Beat||!M.Arena()||M.bChapterComplete) return false;
    const bool bHasAnchor=Beat->Goal==ESoraBeatGoal::Interact||Beat->Goal==ESoraBeatGoal::Hold||
        (Beat->Goal==ESoraBeatGoal::Reach&&!bReached)||
        (Beat->Goal==ESoraBeatGoal::Lines&&((Beat->bLinesAtAnchor&&!bLinesStarted)||(Beat->bReachAfterLines&&bReached)));
    if(!bHasAnchor) return false;
    Location=M.Arena()->BeatAnchor(BeatIndex,ActiveChapter()->Rules[BeatIndex].Site);
    return true;
}
TArray<int32> USoraCampaignDirector::AvailableCaches() const
{
    TArray<int32> Result;
    const FSoraChapter* Chapter=ActiveChapter();
    if(!Chapter||!Mode().bCampaign||Mode().bChapterComplete) return Result;
    for(int32 Index=0;Index<Chapter->Beats.Num();++Index)
        if(Chapter->Beats[Index].Goal==ESoraBeatGoal::Explore&&
            SoraBeatRules::CanStartBeat(BeatState,Chapter->Rules.GetData(),Chapter->Rules.Num(),Index))
            Result.Add(Index);
    return Result;
}
FVector USoraCampaignDirector::CacheLocation(int32 Beat) const
{
    return Mode().Arena()?Mode().Arena()->CacheAnchor(Beat):FVector::ZeroVector;
}
void USoraCampaignDirector::UpdateObjective()
{
    ASoraWorldBuilder* WorldBuilder=Mode().Arena();
    if(!WorldBuilder) return;
    FVector Anchor;
    WorldBuilder->ShowObjective(ObjectiveAnchor(Anchor)?&Anchor:nullptr);
    TArray<FVector> Caches;
    for(const int32 Beat:AvailableCaches()) Caches.Add(CacheLocation(Beat));
    WorldBuilder->ShowCaches(Caches);
}
bool USoraCampaignDirector::Near(const FVector& Location,float Radius) const
{
    const ASoraPlayerCharacter* Player=Mode().Hero();
    return Player&&FVector::Dist2D(Player->GetActorLocation(),Location)<Radius;
}
bool USoraCampaignDirector::AdvanceChapter()
{
    ASoraGameMode& M=Mode();
    const int32 NextChapter=SoraCampaignRules::AdvanceChapter(ChapterId,LastChapter,M.bChapterComplete);
    if(M.bCampaign&&NextChapter!=ChapterId)
    {
        // The next chapter begins with everything this route has earned.
        EntryWeapons=BeatState.WeaponsMask; EntryMechanics=BeatState.MechanicsMask;
        ChapterId=NextChapter; M.MapId=FSoraCatalog::Get().Chapter(ChapterId).Map;
        ClearCheckpoint(); SaveProgress();
    }
    else if(M.bCampaign)
    {
        bCampaignComplete=SoraCampaignRules::CampaignLiberated(ChapterId,LastChapter,M.bChapterComplete);
        ClearCheckpoint(); SaveProgress(); M.SetMenuOpen(true);
        return false;
    }
    return true;
}
void USoraCampaignDirector::StartOver()
{
    bCampaignComplete=false; ChapterId=0;
    EntryWeapons=0u; EntryMechanics=0u; DojoLessonMask=0u;
    if(Save) { Save->HighestChapter=0; Save->Collectibles=0; }
    ClearCheckpoint();
    SaveProgress();
}
void USoraCampaignDirector::ResumeSavedChapter()
{
    ChapterId=Save->CurrentChapter;
    EntryWeapons=static_cast<unsigned>(Save->ChapterEntryWeapons);
    EntryMechanics=static_cast<unsigned>(Save->ChapterEntryMechanics);
    bCampaignComplete=Save->CampaignComplete; Mode().MapId=FSoraCatalog::Get().Chapter(ChapterId).Map;
}
int32 USoraCampaignDirector::HighestChapter() const { return Save?FMath::Clamp(Save->HighestChapter,0,LastChapter):0; }
bool USoraCampaignDirector::SelectChapter(int32 Chapter)
{
    const FSoraCatalog& Catalog=FSoraCatalog::Get();
    if(!Save||!Catalog.IsReady()||Chapter<0||Chapter>HighestChapter()) return false;
    // Replaying reopens the story from that chapter with every unlock the
    // earlier chapters offer (bible §11), so a liberated campaign fights its
    // final chapter again rather than restoring the liberated city.
    ChapterId=Chapter; bCampaignComplete=false; DojoLessonMask=0u;
    EntryWeapons=Catalog.EarlierWeapons(Chapter); EntryMechanics=Catalog.EarlierMechanics(Chapter);
    Mode().MapId=Catalog.Chapter(ChapterId).Map;
    ClearCheckpoint();
    SaveProgress();
    return true;
}
bool USoraCampaignDirector::HasProgress() const
{
    // The dojo's opening checkpoint, with no beat done, is where New Campaign begins.
    return Save&&(Save->CurrentChapter>0||Save->HighestChapter>0||Save->CampaignComplete||Save->Collectibles!=0||
        (Save->CheckpointChapter>=0&&Save->CheckpointBeatsMask!=0));
}
bool USoraCampaignDirector::SeedCheckpoint(USoraSaveGame& Target,int32 Chapter,int32 Beat,int32 Phase)
{
    const FSoraCatalog& Catalog=FSoraCatalog::Get();
    if(!Catalog.IsReady()||Chapter<0||Chapter>LastChapter) return false;
    const FSoraChapter& Data=Catalog.Chapter(Chapter);
    const unsigned Weapons=Catalog.EarlierWeapons(Chapter),Mechanics=Catalog.EarlierMechanics(Chapter);
    SoraBeatRules::FProgress State{0u,0u,Weapons,Mechanics,false};
    for(int32 Index=0;Index<Beat&&Index<Data.Rules.Num();++Index)
        if(!Data.Rules[Index].Optional&&!SoraBeatRules::CompleteBeat(State,Data.Rules.GetData(),Data.Rules.Num(),Index)) return false;
    if(!Data.Rules.IsValidIndex(Beat)||Data.Rules[Beat].Optional||
        !SoraBeatRules::CheckpointValid(State,Data.Rules.GetData(),Data.Rules.Num(),Weapons,Mechanics,Beat,Phase))
        return false;
    Target.SaveSchema=USoraSaveGame::Schema;
    Target.CurrentChapter=Chapter; Target.HighestChapter=FMath::Max(Target.HighestChapter,Chapter);
    Target.CampaignComplete=false;
    Target.ChapterEntryWeapons=static_cast<int32>(Weapons); Target.ChapterEntryMechanics=static_cast<int32>(Mechanics);
    Target.CheckpointChapter=Chapter; Target.CheckpointBeat=Beat; Target.CheckpointPhase=Phase;
    Target.CheckpointBeatsMask=static_cast<int32>(State.CompletedMask); Target.CheckpointSitesMask=static_cast<int32>(State.SitesMask);
    Target.CheckpointWeapons=static_cast<int32>(State.WeaponsMask); Target.CheckpointMechanics=static_cast<int32>(State.MechanicsMask);
    Target.CheckpointComplete=false;
    Target.CheckpointDojoLessonMask=Chapter==0?static_cast<int32>(LessonsTaught(Data,State.CompletedMask)):0;
    return true;
}
bool USoraCampaignDirector::IsWeaponUnlocked(int32 WeaponId) const
{
    // The training arena lends every arm; the campaign holds what it has earned.
    return WeaponId>=0&&WeaponId<SoraBeatRules::WeaponCount&&
        (!Mode().bCampaign||(BeatState.WeaponsMask&(1u<<WeaponId))!=0u);
}
unsigned long long USoraCampaignDirector::CollectedMask() const
{
    return Save?static_cast<unsigned long long>(Save->Collectibles):0ull;
}
void USoraCampaignDirector::SuspendDojo(bool bIncludeHero)
{
    if(ChapterId!=0) return;
    if(bIncludeHero)
    {
        if(ASoraPlayerCharacter* Player=Mode().Hero()) Player->SuspendDojoAction();
    }
    for(const auto& Enemy:Enemies) if(IsValid(Enemy)) Enemy->SuspendDojoAction();
}
void USoraCampaignDirector::Interact(ASoraPlayerCharacter& Player)
{
    ASoraGameMode& M=Mode();
    if(!M.bCampaign) { ArenaInteract(Player); return; }
    const FSoraBeat* Beat=ActiveBeatData();
    if(!Beat||M.bChapterComplete) return;
    FVector Anchor;
    if(ObjectiveAnchor(Anchor)&&Near(Anchor,InteractRadius))
    {
        if(Beat->Goal==ESoraBeatGoal::Interact&&InteractCount<Beat->GoalCount)
        {
            const float Before=static_cast<float>(InteractCount)/Beat->GoalCount;
            ++InteractCount;
            const float After=static_cast<float>(InteractCount)/Beat->GoalCount;
            if(InteractCount==1) Fire(TEXT("interact_start"));
            for(const FSoraDialogueTrigger& Trigger:ActiveChapter()->Triggers)
                if(Trigger.Beat==BeatIndex&&Trigger.On.StartsWith(TEXT("progress_at:")))
                {
                    const float At=FCString::Atof(*Trigger.On.RightChop(12));
                    if(Before<At&&After>=At) Fire(Trigger.On);
                }
            if(InteractCount>=Beat->GoalCount&&!WavesCleared())
                Notify(TEXT("作業は済んだ。残る侵略者を退けよう。"),TEXT("The work is done. Drive off the remaining invaders."),5.f);
            else if(InteractCount>=Beat->GoalCount) CompleteActiveBeat();
            return;
        }
        if(Beat->Goal==ESoraBeatGoal::Lines&&Beat->bLinesOnInteract&&!bLinesStarted)
        {
            Enqueue(Beat->Lines,true); bLinesStarted=true;
            Fire(Beat->AnchorEvent); UpdateObjective();
            return;
        }
    }
    for(const int32 Cache:AvailableCaches())
        if(Near(CacheLocation(Cache),InteractRadius)) { CompleteOptional(Cache); return; }
}
void USoraCampaignDirector::OpponentDefeated(ASoraEnemy* Opponent)
{
    ASoraGameMode& M=Mode();
    if(M.bDeterministicPractice) return;
    if(!M.bCampaign)
    {
        SoraCampaignRules::FArena Arena{Kills,static_cast<unsigned>(ArenaSitesMask),bArenaComplete};
        if(!SoraCampaignRules::RecordArenaDefeat(Arena)) return;
        Kills=Arena.Kills;
        if(ASoraPlayerCharacter* Player=M.Hero()) Player->Heal(8.f);
        if(Spawned<SoraCampaignRules::ArenaDefeats) SpawnOne();
        if(Kills>=SoraCampaignRules::ArenaDefeats)
            Notify(TEXT("侵略者を退けた。残る工房を取り戻し、東の鳥居へ向かおう。"),
                TEXT("Invaders cleared. Restore the remaining workshops, then reach the eastern torii gate."),7.f);
        return;
    }
    const FSoraBeat* Beat=ActiveBeatData();
    if(!Beat||!Opponent||!Enemies.Contains(Opponent)) return;
    if(ChapterId==0&&Opponent->IsDojoPupil()&&!CanScoreDojoBout()) return;
    if(Opponent==BossActor) BossActor=nullptr;
    ++Kills;
    if(ASoraPlayerCharacter* Player=M.Hero()) Player->Heal(8.f);
    SpawnOpponents();
    if(Beat->Goal==ESoraBeatGoal::Defeat&&Kills>=Beat->GoalCount) { CompleteActiveBeat(); return; }
    if(Beat->Goal==ESoraBeatGoal::Lessons&&Kills>=Beat->GoalCount&&(DojoLessonMask&Beat->LessonMask)==Beat->LessonMask)
        CompleteActiveBeat();
}
bool USoraCampaignDirector::CanScoreDojoBout() const
{
    return Mode().bCampaign&&ChapterId==0&&SoraDojoRules::CanScoreBout({DojoLessonMask});
}
int32 USoraCampaignDirector::DojoLessonStage() const
{
    return Mode().bCampaign&&ChapterId==0?SoraDojoRules::NextLesson({DojoLessonMask}):4;
}
bool USoraCampaignDirector::RecordDojoLesson(SoraDojoRules::EAction Action,int32 DurationMs,bool bFacingAttacker,int32 RecoveryMs)
{
    ASoraGameMode& M=Mode();
    const FSoraBeat* Beat=ActiveBeatData();
    // Forms are taught only in the lesson duel whose gates name them.
    if(!M.bCampaign||ChapterId!=0||!M.IsPlaying()||!Beat||Beat->Goal!=ESoraBeatGoal::Lessons||
        (Beat->LessonMask&(1u<<static_cast<int32>(Action)))==0u) return false;
    SoraDojoRules::FProgress Lessons{DojoLessonMask};
    if(!SoraDojoRules::Record(Lessons,Action,DurationMs,bFacingAttacker,RecoveryMs)) return false;
    DojoLessonMask=Lessons.CompletedMask;
    static const TCHAR* Japanese[]={
        TEXT("壱の型・構え。守りを保った。次は門弟の一撃を受けよう。"),
        TEXT("弐の型・受け。刃を正面で受けた。次は予兆に合わせて防御を押そう。"),
        TEXT("参の型・捌き。打ち込みを見切った。次は木刀を振り、刃が戻るまで待とう。"),
        TEXT("肆の型・残心。打った後も構えを崩さない。これより門弟との立合いだ。")};
    static const TCHAR* English[]={
        TEXT("Form one: stance held. Now face and guard a pupil's strike."),
        TEXT("Form two: guarded. Release defense, then press it during the golden warning to parry."),
        TEXT("Form three: parried. Swing your wooden sword, then let it fully recover."),
        TEXT("Form four: recovery mastered. You may now score the sparring bouts.")};
    const int32 Completed=DojoLessonStage()-1;
    Notify(Japanese[Completed],English[Completed],8.f);
    if((DojoLessonMask&Beat->LessonMask)==Beat->LessonMask&&Kills>=Beat->GoalCount) CompleteActiveBeat();
    return true;
}
void USoraCampaignDirector::PlayerKilled()
{
    ASoraGameMode& M=Mode();
    if(M.bDeterministicPractice) return;
    M.bDefeated=true;
    M.Notice=M.bCampaign&&ChapterId==0?TEXT("立合いはここまで。Enter で稽古をやり直そう。")
        :TEXT("仲間は、あなたを待っている。Enter で最後の復旧記録から再開する。");
    M.NoticeEnglish=M.bCampaign&&ChapterId==0?TEXT("The sparring bout has ended. Press Enter to resume training.")
        :TEXT("The resistance remembers. Press Enter to retry from the latest checkpoint.");
    if(ActiveBeatData())
    {
        Fire(TEXT("player_died"));
        if(auto* Events=USoraGameEvents::Get(this))
        {
            FSoraBeatEvent Failed;
            Failed.ChapterId=ChapterId; Failed.BeatIndex=BeatIndex; Failed.BeatId=ActiveBeatData()->Id; Failed.Phase=BeatPhase;
            Events->OnBeatFailed.Broadcast(Failed);
        }
        Telemetry(TEXT("failed"));
    }
}
void USoraCampaignDirector::Notify(const FString& Japanese,const FString& English,float Seconds)
{
    ASoraGameMode& M=Mode();
    M.Notice=Japanese; M.NoticeEnglish=English; M.NoticeTime=Seconds;
}
void USoraCampaignDirector::BroadcastBeat(bool bStarted,bool bResumed)
{
    const FSoraBeat* Beat=ActiveBeatData();
    USoraGameEvents* Events=USoraGameEvents::Get(this);
    if(!Beat||!Events) return;
    FSoraBeatEvent Event;
    Event.ChapterId=ChapterId; Event.BeatIndex=BeatIndex; Event.BeatId=Beat->Id; Event.bResumed=bResumed; Event.Phase=BeatPhase;
    (bStarted?Events->OnBeatStarted:Events->OnBeatCompleted).Broadcast(Event);
}
void USoraCampaignDirector::Telemetry(const TCHAR* Event) const
{
    // Per-beat timestamps for pacing playtests (bible §10), one JSON object per line.
    const ASoraGameMode& M=Mode();
    const FSoraChapter* Chapter=ActiveChapter();
    if(!Chapter) return;
    const FString BeatId=Chapter->Beats.IsValidIndex(BeatIndex)?Chapter->Beats[BeatIndex].Id:FString();
    const FString Line=FString::Printf(TEXT("{\"utc\":\"%s\",\"slot\":\"%s\",\"chapter\":\"%s\",\"beat\":\"%s\",\"event\":\"%s\",\"phase\":%d,\"round_s\":%.2f,\"world_s\":%.2f}\n"),
        *FDateTime::UtcNow().ToIso8601(),*M.SaveSlotName,*Chapter->Id,*BeatId,Event,BeatPhase,M.RoundTime,GetWorld()?GetWorld()->GetTimeSeconds():0.0);
    FFileHelper::SaveStringToFile(Line,*(FPaths::ProjectSavedDir()/TEXT("Telemetry/campaign_beats.jsonl")),
        FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM,&IFileManager::Get(),FILEWRITE_Append);
}
void USoraCampaignDirector::SaveCheckpoint()
{
    ASoraGameMode& M=Mode();
    if(!M.bCampaign||!Save) return;
    Save->CheckpointChapter=ChapterId;
    Save->CheckpointBeat=BeatState.Complete?INDEX_NONE:BeatIndex;
    Save->CheckpointPhase=BeatState.Complete?0:BeatPhase;
    Save->CheckpointBeatsMask=static_cast<int32>(BeatState.CompletedMask);
    Save->CheckpointSitesMask=static_cast<int32>(BeatState.SitesMask);
    Save->CheckpointWeapons=static_cast<int32>(BeatState.WeaponsMask);
    Save->CheckpointMechanics=static_cast<int32>(BeatState.MechanicsMask);
    Save->CheckpointComplete=BeatState.Complete;
    Save->CheckpointDojoLessonMask=ChapterId==0?static_cast<int32>(DojoLessonMask):0;
    SaveProgress();
}
void USoraCampaignDirector::ClearCheckpoint()
{
    if(!Save) return;
    Save->CheckpointChapter=-1; Save->CheckpointBeat=-1; Save->CheckpointPhase=0;
    Save->CheckpointBeatsMask=0; Save->CheckpointSitesMask=0; Save->CheckpointWeapons=0; Save->CheckpointMechanics=0;
    Save->CheckpointComplete=false; Save->CheckpointDojoLessonMask=0;
}
void USoraCampaignDirector::SaveProgress()
{
    if(!Save) return;
    ASoraGameMode& M=Mode();
    Save->SaveSchema=USoraSaveGame::Schema;
    Save->CurrentChapter=ChapterId; Save->SelectedClass=M.SelectedClass; Save->CampaignComplete=bCampaignComplete;
    Save->EnglishSubtitles=M.bEnglishSubtitles;
    Save->ChapterEntryWeapons=static_cast<int32>(EntryWeapons); Save->ChapterEntryMechanics=static_cast<int32>(EntryMechanics);
    if(!UGameplayStatics::SaveGameToSlot(Save,M.SaveSlotName,0))
        Notify(TEXT("進行を保存できませんでした。今回の起動中は続けられます。"),TEXT("Unable to write campaign save. Progress remains available this session."),6.f);
}
void USoraCampaignDirector::ClearOfflineProjectiles()
{
    TArray<AActor*> Projectiles;
    UGameplayStatics::GetAllActorsOfClass(this,ASoraProjectile::StaticClass(),Projectiles);
    for(auto* Projectile:Projectiles) if(IsValid(Projectile)) Projectile->Destroy();
}
void USoraCampaignDirector::ArenaInteract(ASoraPlayerCharacter& Player)
{
    ASoraGameMode& M=Mode();
    ASoraWorldBuilder* WorldBuilder=M.Arena();
    SoraCampaignRules::FArena Arena{Kills,static_cast<unsigned>(ArenaSitesMask),bArenaComplete};
    const int32 SiteId=WorldBuilder->NearestInactiveNode(Player.GetActorLocation());
    if(SiteId!=INDEX_NONE)
    {
        if(!SoraCampaignRules::RestoreArenaSite(Arena,SiteId)||!WorldBuilder->ActivateNearest(Player.GetActorLocation())) return;
        ArenaSitesMask=static_cast<int32>(Arena.SitesMask);
        Player.Heal(22.f);
        Notify(TEXT("生産を再開した。この工房は、再び民のものだ。"),TEXT("Production restored. The community now controls this workshop."),7.f);
        if(auto* Events=USoraGameEvents::Get(this))
        {
            FSoraSiteRestoredEvent Restored;
            Restored.ChapterId=ChapterId; Restored.SiteIndex=SiteId; Restored.bCampaign=false; Restored.Kind=TEXT("workshop");
            Events->OnSiteRestored.Broadcast(Restored);
        }
        return;
    }
    if(FVector::Dist2D(Player.GetActorLocation(),WorldBuilder->ExitPoint())>=270.f) return;
    if(SoraCampaignRules::FinishArena(Arena))
    {
        bArenaComplete=true; M.bChapterComplete=true;
        Notify(TEXT("稽古場を制した。Enter でもう一度。"),TEXT("Training arena cleared. Press Enter to go again."),12.f);
    }
    else Notify(TEXT("残る工房の仕事を終え、侵略者を退けよう。"),TEXT("Finish the remaining workshops and defeat the invaders first."),5.f);
}
FString USoraCampaignDirector::ObjectiveText() const
{
    const ASoraGameMode& M=Mode();
    if(!M.bCampaign)
        return FString::Printf(TEXT("生産の復旧 %d / 3    |    侵略者 %d / %d    |    出口：東の鳥居"),
            M.Arena()?M.Arena()->ActiveNodes():0,Kills,KillsNeeded);
    const FSoraBeat* Beat=ActiveBeatData();
    if(M.bChapterComplete||!Beat) return TEXT("章を終えた");
    if(ChapterId==0&&Beat->Goal==ESoraBeatGoal::Lessons&&(DojoLessonMask&Beat->LessonMask)!=Beat->LessonMask)
        return FString::Printf(TEXT("%s  |  猫柳生新陰流  型 %d / 4"),*Beat->Title,DojoLessonStage()+1);
    FString Progress;
    switch(Beat->Goal)
    {
    case ESoraBeatGoal::Defeat:
    case ESoraBeatGoal::Lessons:
        if(Beat->Opponent!=ESoraOpponent::Boss)
            Progress=FString::Printf(TEXT("%s %d / %d"),Beat->Opponent==ESoraOpponent::Pupil?TEXT("立合い"):TEXT("侵略者"),Kills,KillsNeeded);
        break;
    case ESoraBeatGoal::Interact: Progress=FString::Printf(TEXT("作業 %d / %d"),InteractCount,Beat->GoalCount); break;
    case ESoraBeatGoal::Hold: Progress=FString::Printf(TEXT("持ちこたえる %d / %d 秒"),FMath::FloorToInt32(HoldSeconds),FMath::CeilToInt32(Beat->GoalSeconds)); break;
    case ESoraBeatGoal::Reach: Progress=TEXT("目的地へ"); break;
    default: break;
    }
    if(Beat->Opponents>0&&Beat->Goal!=ESoraBeatGoal::Defeat&&Beat->Goal!=ESoraBeatGoal::Lessons)
        Progress+=FString::Printf(TEXT("%s侵略者 %d / %d"),Progress.IsEmpty()?TEXT(""):TEXT("  |  "),Kills,KillsNeeded);
    return Progress.IsEmpty()?Beat->Title:Beat->Title+TEXT("  |  ")+Progress;
}
FString USoraCampaignDirector::ObjectiveTextEnglish() const
{
    const ASoraGameMode& M=Mode();
    if(!M.bCampaign)
        return FString::Printf(TEXT("Production sites %d of 3 / Invaders %d of %d / Exit: eastern torii gate"),
            M.Arena()?M.Arena()->ActiveNodes():0,Kills,KillsNeeded);
    const FSoraBeat* Beat=ActiveBeatData();
    if(M.bChapterComplete||!Beat) return TEXT("Chapter complete");
    if(ChapterId==0&&Beat->Goal==ESoraBeatGoal::Lessons&&(DojoLessonMask&Beat->LessonMask)!=Beat->LessonMask)
        return FString::Printf(TEXT("%s / Nyaagyushinkageryuu form %d of 4"),*Beat->TitleEnglish,DojoLessonStage()+1);
    FString Progress;
    switch(Beat->Goal)
    {
    case ESoraBeatGoal::Defeat:
    case ESoraBeatGoal::Lessons:
        if(Beat->Opponent!=ESoraOpponent::Boss)
            Progress=FString::Printf(TEXT("%s %d of %d"),Beat->Opponent==ESoraOpponent::Pupil?TEXT("Bouts"):TEXT("Invaders"),Kills,KillsNeeded);
        break;
    case ESoraBeatGoal::Interact: Progress=FString::Printf(TEXT("Work %d of %d"),InteractCount,Beat->GoalCount); break;
    case ESoraBeatGoal::Hold: Progress=FString::Printf(TEXT("Hold %d of %d s"),FMath::FloorToInt32(HoldSeconds),FMath::CeilToInt32(Beat->GoalSeconds)); break;
    case ESoraBeatGoal::Reach: Progress=TEXT("Reach the marker"); break;
    default: break;
    }
    if(Beat->Opponents>0&&Beat->Goal!=ESoraBeatGoal::Defeat&&Beat->Goal!=ESoraBeatGoal::Lessons)
        Progress+=FString::Printf(TEXT("%sInvaders %d of %d"),Progress.IsEmpty()?TEXT(""):TEXT(" / "),Kills,KillsNeeded);
    return Progress.IsEmpty()?Beat->TitleEnglish:Beat->TitleEnglish+TEXT(" / ")+Progress;
}
FString USoraCampaignDirector::DojoLessonText(bool bEnglish) const
{
    if(!Mode().bCampaign||ChapterId!=0||DojoLessonStage()>=4) return FString();
    static const TCHAR* Japanese[]={
        TEXT("壱・構え：防御を 0.6 秒保つ"),
        TEXT("弐・受け：相手に向き、防御を保って一撃を受ける"),
        TEXT("参・捌き：金色の予兆に合わせて防御を押す"),
        TEXT("肆・残心：木刀を振り、攻撃を止めて刃の戻りを待つ")};
    static const TCHAR* English[]={
        TEXT("STANCE: hold Guard for 0.6 seconds."),
        TEXT("GUARD: face a pupil and hold Guard through its strike."),
        TEXT("PARRY: release, then press Guard during the golden warning."),
        TEXT("RECOVERY: swing once, release attack, and wait for the blade to return.")};
    return bEnglish?English[DojoLessonStage()]:Japanese[DojoLessonStage()];
}
