#include "SoraCampaignDirector.h"
#include "SoraFoundryFurnace.h"
#include "SoraCompanion.h"
#include "Combat/SoraDamage.h"
#include "SoraRidgeRules.h"
#include "SoraWoodRules.h"
#include "Game/SoraCampaignReach.h"
#include "Combat/SoraBossCatalog.h"
#include "Combat/SoraStealth.h"
#include "SoraBoss.h"
#include "SoraCampaignRules.h"
#include "SoraCatalog.h"
#include "SoraCombatRules.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "Components/CapsuleComponent.h"
#include "SoraEquipmentComponent.h"
#include "SoraFieldcraft.h"
#include "SoraPressRules.h"
#include "SoraArchiveRules.h"
#include "SoraLedgerRules.h"
#include "SoraGameEvents.h"
#include "SoraGameMode.h"
#include "SoraGalleryRules.h"
#include "SoraHorse.h"
#include "SoraInputStates.h"
#include "SoraPlayerCharacter.h"
#include "SoraProjectile.h"
#include "SoraSaveGame.h"
#include "SoraSettings.h"
#include "SoraText.h"
#include "SoraWorldBuilder.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"
#include "HAL/FileManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

namespace
{
constexpr int32 LastChapter = SoraCampaignRules::ChapterCount - 1;
constexpr float PromptSeconds = 8.f;
// The dojo form each lesson gate names, in SoraDojoRules order.
const TCHAR* const LessonGates[] = {TEXT("stance_hold"), TEXT("front_guard_survive"), TEXT("awase"), TEXT("recovery_complete")};
// 転 answers an awase within this window (bible §3.2), and an awase pressed
// this long after the cut landed is only late.
constexpr int32 MarobashiWindowMs = SoraCombatRules::MarobashiWindowMs;
constexpr double LateAwaseSeconds = .5;

// The dojo forms a chapter's completed lesson duels taught; a checkpoint
// taken at a beat's start holds exactly these.
unsigned LessonsTaught(const FSoraChapter& Chapter, unsigned CompletedMask)
{
    unsigned Mask = 0u;
    for (int32 Index = 0; Index < Chapter.Beats.Num(); ++Index)
        if ((CompletedMask & SoraBeatRules::BeatBit(Index)) != 0u && Chapter.Beats[Index].Has(SoraBeatRules::EGoal::Lessons))
            Mask |= Chapter.Beats[Index].Task.LessonMask;
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
// A trigger's "progress_at:0.25" or "idle_s:20" threshold, in permille or ms.
int32 Threshold(const FString& On, int32 PrefixLength, double Scale)
{
    return FMath::RoundToInt32(FCString::Atod(*On.RightChop(PrefixLength)) * Scale);
}
// A chapter-one sparring pupil (bokuto bouts and the matoba's targets), or
// the training arena's invader of this slot.
ASoraEnemy* SpawnPrototype(UWorld& World, const FVector& Location, bool bPupil, int32 Slot,
    const SoraDojoRules::FPupilTiming& PupilTiming = {})
{
    FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;
    ASoraEnemy* Enemy=World.SpawnActor<ASoraEnemy>(Location,FRotator(0,180,0),Params);
    if(!Enemy) return nullptr;
    if(bPupil) Enemy->InitDojoPupil(Slot,PupilTiming);
    else Enemy->InitInvader(Slot);
    return Enemy;
}
// The settings' campaign difficulty in the boss rules' order (Easy, Normal, Hard).
SoraBossRules::EDifficulty BossDifficulty(const UObject* WorldContext)
{
    return static_cast<SoraBossRules::EDifficulty>(static_cast<uint8>(SoraAccessibility::CampaignDifficulty(WorldContext)));
}
}

USoraCampaignDirector::USoraCampaignDirector()
{
    // The beat clock runs in the director's own tick; the paused menu stops it.
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.bStartWithTickEnabled=true;
}
void USoraCampaignDirector::BeginPlay()
{
    Super::BeginPlay();
    if(USoraGameEvents* Events=USoraGameEvents::Get(this))
    {
        Events->OnDamaged.AddUObject(this,&USoraCampaignDirector::HeroDamaged);
        Events->OnParried.AddUObject(this,&USoraCampaignDirector::HeroParried);
        Events->OnMarobashi.AddUObject(this,&USoraCampaignDirector::HeroRolled);
        Events->OnEnemyCue.AddUObject(this,&USoraCampaignDirector::EnemyCue);
        Events->OnBossPhase.AddUObject(this,&USoraCampaignDirector::CollectorCue);
    }
    if(USoraFieldcraft* Fieldcraft=USoraFieldcraft::Get(this))
        Fieldcraft->OnEvent.AddUObject(this,&USoraCampaignDirector::FieldcraftEvent);
    if(USoraStealth* Stealth=USoraStealth::Get(this))
    {
        Stealth->OnDetected.AddUObject(this,&USoraCampaignDirector::StealthDetected);
        Stealth->OnAlarm.AddUObject(this,&USoraCampaignDirector::StealthAlarm);
        Stealth->OnBodyFound.AddUObject(this,&USoraCampaignDirector::StealthBodyFound);
    }
}
void USoraCampaignDirector::HeroDamaged(const FSoraDamagedEvent& Event)
{
    const ASoraGameMode& M=Mode();
    if(!ActiveBeatData()||Event.Victim!=M.Hero()) return;
    CancelFoundryWork();
    CancelHorseTreatment();
    CancelCopying();
    if(bPryingCarryGate) bCarryGateHit=true;
    if(IsHelmHold()) CancelHelm();
    StopPlayerCrank();
    if(SpineCut.Active) SoraSummitRules::Interrupt(SpineCut);
    if(BulkheadHold.Active) CancelBulkheadHold();
    CancelConstructCut();
    // A pupil's cut landed while the awase was still to be met: a guard
    // raised just after it is late.
    const ASoraEnemy* Pupil=Cast<ASoraEnemy>(Event.Causer);
    if(ChapterId==0&&DojoLessonStage()==2&&Pupil&&Pupil->IsDojoPupil()&&GetWorld()) LateHitAt=GetWorld()->GetTimeSeconds();
    if(!SoraBeatRules::DropCarried(TaskState,Task)) return;
    CarryChanged();
    Fire(TEXT("item_dropped"));
    Notify(TEXT("荷を落とした。拾いに戻ろう。"),TEXT("You dropped your load. Go back for it."),4.f);
    UpdateObjective();
}
void USoraCampaignDirector::OpenStealthZone()
{
    USoraStealth* Stealth=USoraStealth::Get(this);
    if(!Stealth) return;
    if(Stealth->IsZoneActive()) Stealth->EndZone();
    const FSoraBeat* Beat=ActiveBeatData();
    if(!Beat||(!Beat->Is(SoraBeatRules::EType::StealthZone)&&!Task.PauseWhenSeen)) return;
    // The zone's authored detection, takedowns and bodies (bible §12.2), on
    // the settings' difficulty.
    const FSoraStealthRulesData& Rules=Beat->Stealth;
    FSoraStealthZone Zone;
    Zone.Vigilance=SoraStealthRules::Detection(Rules.RatePermille,Rules.SuspiciousAtPermille,Rules.SearchMs,Rules.WaryPermille);
    Zone.Difficulty=static_cast<SoraStealthRules::EDifficulty>(static_cast<uint8>(SoraAccessibility::CampaignDifficulty(this)));
    Zone.OnDetected=Task.OnDetected==SoraBeatRules::EDetected::Restart?SoraStealthRules::EOnDetected::Restart
        :Task.OnDetected==SoraBeatRules::EDetected::Reinforce?SoraStealthRules::EOnDetected::Reinforce:SoraStealthRules::EOnDetected::Combat;
    // Rear takedowns once the story teaches them (bible §12.1 takedown), from
    // the beat that teaches them on, where the zone allows them.
    Zone.bRearTakedowns=Rules.bRearTakedowns&&IsMechanicInPlay(TEXT("takedown"));
    Zone.bLethalDefault=Rules.bLethalDefault;
    Zone.bBodiesDiscoverable=Rules.bBodies;
    Zone.bDragBodies=Rules.bDrag;
    // An earlier zone that saw the hero sends its word ahead (ch03.b02 to b03).
    Zone.bCarriedOver=DetectionCarried.Contains(Beat->Id);
    Stealth->BeginZone(Zone);
}
void USoraCampaignDirector::CloseStealthZone()
{
    if(USoraStealth* Stealth=USoraStealth::Get(this); Stealth&&Stealth->IsZoneActive()) Stealth->EndZone();
}
void USoraCampaignDirector::FieldcraftEvent(FName Event)
{
    if(!Mode().bCampaign||!ActiveBeatData()) return;
    RaiseBeatEvent(Event);
    // A cook-fire guttering or relit moves the objective to it and back.
    if(Event.ToString().StartsWith(TEXT("fire_"))) UpdateObjective();
}
void USoraCampaignDirector::EnemyCue(const FSoraEnemyCueEvent& Event)
{
    if(!Mode().bCampaign||!ActiveBeatData()||Mode().bDeterministicPractice) return;
    const FString Detail=Event.Detail.ToString();
    switch(Event.Cue)
    {
    case ESoraEnemyCue::AlertState:
    {
        // The guards' barks for their state; detection itself (and what it
        // fails) comes from the stealth zone, never from a bark.
        const TWeakObjectPtr<const AActor> Key(Event.Enemy.Get());
        const FName* Before=GuardStates.Find(Key);
        if(Before&&*Before==TEXT("search")&&Event.Detail==TEXT("unaware")) Fire(TEXT("alert_state:search_to_unaware"));
        GuardStates.Add(Key,Event.Detail);
        if(Event.Detail==TEXT("retreat")) { Fire(TEXT("ai_event:retreat")); Fire(TEXT("enemy_retreat")); Fire(TEXT("event:enemy_retreat")); }
        else Fire(TEXT("alert_state:")+Detail);
        return;
    }
    case ESoraEnemyCue::Alarm: Fire(TEXT("ai_event:alarm_run")); return;
    case ESoraEnemyCue::KnockedOut:
        Fire(TEXT("ai_event:takedown"));
        if(!BeatEvents.Contains(TEXT("ai_event:first_takedown"))) Fire(TEXT("ai_event:first_takedown"));
        return;
    case ESoraEnemyCue::Subdued: Fire(TEXT("conscript_downed")); return;
    case ESoraEnemyCue::Freed: Fire(TEXT("conscript_freed")); return;
    case ESoraEnemyCue::ShieldTurned: Fire(TEXT("ai:shield_turned")); return;
    case ESoraEnemyCue::AttackWindup:
        // An opponent's attack telegraph, as the scripts key it: the marksman's
        // glint (pattern:marksman_lock), the grenadier's shell, a walker's sweep.
        if(Event.Detail.IsNone()) return;
        Fire(TEXT("pattern:")+Detail);
        Fire(TEXT("ai:")+Detail);
        return;
    case ESoraEnemyCue::BarrierBroken: Fire(TEXT("shield_broken")); return;
    default: return;
    }
}
void USoraCampaignDirector::StealthDetected(const FSoraStealthDetection& Detection)
{
    if(!ActiveBeatData()) return;
    // A patrol that finds the hero finds the party beside him: they drop.
    if(USoraFieldcraft* Fieldcraft=USoraFieldcraft::Get(this))
    {
        Fieldcraft->PartyDetected();
        if(Detection.KnownLocation.IsSet())
        {
            Fieldcraft->LockSearchlights(Detection.KnownLocation.GetValue());
            Fieldcraft->MoatDetected(Detection.KnownLocation.GetValue());
        }
    }
    // A later zone the script names starts suspicious and wary.
    if(const FSoraBeat* Beat=ActiveBeatData(); Beat->bStealth&&!Beat->Stealth.CarryoverTo.IsEmpty())
        DetectionCarried.Add(Beat->Stealth.CarryoverTo);
    // On Easy the zone answers a detection with a fight (SoraStealthRules::
    // Response): the beat is neither failed nor reinforced. Guarded work
    // pauses only while a guard sees the hero or is alarmed (IsWorkPaused).
    if(Detection.Response==SoraStealthRules::EOnDetected::Combat&&Task.OnDetected!=SoraBeatRules::EDetected::Combat)
    {
        Fire(TEXT("ai_event:detected"));
        return;
    }
    if(IsRelayRoom()) Relay.Detect(RelayCatchAgeMs);
    RaiseBeatEvent(TEXT("alert_state:alert"));
}
void USoraCampaignDirector::StealthAlarm(ASoraEnemy* By)
{
    if(ActiveBeatData()) RaiseBeatEvent(TEXT("ai_event:alarm_raised"));
}
void USoraCampaignDirector::StealthBodyFound(ASoraEnemy* Body,ASoraEnemy* Finder)
{
    if(ActiveBeatData()) RaiseBeatEvent(TEXT("ai_event:body_found"));
}
void USoraCampaignDirector::HeroParried(const FSoraDefenseEvent& Event)
{
    // The awase a 転 lesson's flank must follow: a sparring cut met within the parry window.
    if(!ActiveBeatData()||!Event.bDojo||Event.Defender!=Mode().Hero()||Event.HeldMs<0||Event.HeldMs>SoraDojoRules::ParryWindowMs||
        !Task.FlankBouts||TaskState.Flanked||(TaskState.Forms&Task.LessonMask)!=Task.LessonMask)
        return;
    AwaseAtMs=TaskState.ElapsedMs;
}
void USoraCampaignDirector::HeroRolled(const FSoraMarobashiEvent& Event)
{
    // 転 straight after an awase lets the lesson's next bout score.
    if(!ActiveBeatData()||Event.Hero!=Mode().Hero()||!Event.bAfterAwase||!SoraBeatRules::RecordFlank(TaskState,Task)) return;
    AwaseAtMs=INDEX_NONE;
    Fire(TEXT("marobashi_flank"));
    UpdateObjective();
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
    // Only a schema-6 save whose chapter, entry unlocks, story flags and
    // collectibles a route through the earlier chapters reaches is read;
    // anything else is a fresh campaign (the unreadable file is replaced at
    // the next save).
    const bool bReadable=Save&&Catalog.IsReady()&&Save->SaveSchema==USoraSaveGame::Schema&&
        Save->CurrentChapter>=0&&Save->CurrentChapter<=Save->HighestChapter&&Save->HighestChapter<=LastChapter&&
        SoraBeatRules::EntryValid(static_cast<unsigned>(Save->ChapterEntryWeapons),
            Catalog.RouteMinimumWeapons(Save->CurrentChapter),Catalog.EarlierWeapons(Save->CurrentChapter))&&
        static_cast<unsigned>(Save->ChapterEntryMechanics)==Catalog.EarlierMechanics(Save->CurrentChapter)&&
        SoraBeatRules::EntryValid(static_cast<unsigned>(Save->ChapterEntryFlags),0u,Catalog.EarlierFlags(Save->CurrentChapter))&&
        SoraCampaignRules::CollectiblesValid(static_cast<unsigned long long>(Save->Collectibles),Save->HighestChapter)&&
        SoraWoodRules::LedgerValid(Save->WoodPoiMask,static_cast<uint64>(Save->Collectibles))&&
        SoraGalleryRules::Valid(Save->GalleryPoiMask,Save->HighestChapter)&&
        SoraGalleryRules::ClaimValid(Save->GalleryArrowsClaimed,Save->HighestChapter,static_cast<uint64>(Save->Collectibles))&&
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
    EntryFlags=static_cast<unsigned>(Save->ChapterEntryFlags);
    bCampaignComplete=Save->CampaignComplete;
    if(Catalog.IsReady()) M.MapId=Catalog.Chapter(ChapterId).Map;
    return true;
}
void USoraCampaignDirector::ResetRound()
{
    Relay={};RelayClock.Reset();RelayCatchAgeMs=0;
    ResetWind();
    BulkheadHold={}; BulkheadClock.Reset();
    ASoraGameMode& M=Mode();
    ASoraWorldBuilder* WorldBuilder=M.Arena();
    const bool bCampaign=M.bCampaign;
    EndRecoveryClimb();
    ResetCarryWork();
    StopPlayerCrank(false);
    RhythmClock={}; RhythmInput={}; RhythmCueShown=-1; RhythmStrikeMs=-1;
    // A shell fired before death or chapter advance must never damage the
    // restored encounter or score a defeat against its fresh opponents.
    ClearOfflineProjectiles();
    ClearOpponents();
    if(USoraFieldcraft* Fieldcraft=USoraFieldcraft::Get(this)) Fieldcraft->Clear();
    // The hero comes down from the saddle before the world he stands in is rebuilt.
    ClearHorses();
    bLiftGallery=false; bWoodTransit=false;
    EndCinematicCamera(0.f);
    Notices.Reset();
    Kills=0; KillsNeeded=0; bLinesStarted=false; bChapterOpening=false; CinematicSeconds=0.f; DojoLessonMask=0u;
    DetectionCarried.Reset();
    ClearDialogue(); Heard.Reset(); FinishedLines.Reset(); FiredTriggers.Reset(); TriggerTimes.Reset();
    PromptIndex=INDEX_NONE; PromptRemaining=0.f;
    BeatIndex=INDEX_NONE; BeatPhase=0; ArenaSitesMask=0; bArenaComplete=false;
    Task=SoraBeatRules::FTask(); TaskState=SoraBeatRules::FTaskState();
    BeatState={0u,0u,EntryWeapons,EntryMechanics,EntryFlags,false};
    M.RoundTime=0; M.bDefeated=false; M.bChapterComplete=false; M.TitleCardTime=0.f;
    M.Notice.Empty(); M.NoticeEnglish.Empty(); M.NoticeTime=0.f;
    WorldBuilder->Build(M.MapId,bCampaign?ActiveChapter():nullptr);
    ApplyLoadout();
    if(!bCampaign)
    {
        KillsNeeded=SoraCampaignRules::ArenaDefeats;
        for(int32 I=0;I<4;++I) SpawnArenaInvader();
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
    ShowPickups();
    if(M.bChapterComplete) { UpdateObjective(); return; }
    const int32 Beat=bResumed?BeatIndex:SoraBeatRules::NextBeat(BeatState,Chapter.Rules.GetData(),Chapter.Rules.Num());
    const int32 Phase=bResumed?BeatPhase:0;
    // A fresh chapter opens on its first cinematic, which carries the title card.
    bChapterOpening=!bResumed; BeatIndex=INDEX_NONE;
    if(bResumed&&ResumeWoodJunction()) return;
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
        static_cast<unsigned>(Save->CheckpointMechanics),static_cast<unsigned>(Save->CheckpointFlags),Save->CheckpointComplete};
    const unsigned Lessons=static_cast<unsigned>(Save->CheckpointDojoLessonMask);
    const int32 Beat=Save->CheckpointBeat,Phase=Save->CheckpointPhase;
    const auto* Gates=Chapter.Rules.GetData(); const int32 Count=Chapter.Rules.Num();
    // The start of a required beat (or a later boss or duel phase its task
    // saves at), or a finished chapter at its result screen; either way exactly
    // what its completed beats earn from the chapter's entry unlocks and flags.
    bool bValid=Beat==INDEX_NONE
        ?Saved.Complete&&Phase==0&&SoraBeatRules::ProgressValid(Saved,Gates,Count,EntryWeapons,EntryMechanics,EntryFlags)
        :!Saved.Complete&&Chapter.Rules.IsValidIndex(Beat)&&(!Chapter.Rules[Beat].Optional||Beat==Chapter.Wood.Beat)&&
            SoraBeatRules::CheckpointValid(Saved,Gates,Count,EntryWeapons,EntryMechanics,EntryFlags,Beat,Phase)&&
            SoraBeatRules::TaskCheckpointValid(Chapter.Tasks[Beat],Phase);
    // Chapter one's forms are exactly those its completed lesson duels taught.
    bValid&=ChapterId==0
        ?SoraDojoRules::CheckpointValid({Lessons},0,Saved.SitesMask)&&Lessons==LessonsTaught(Chapter,Saved.CompletedMask)
        :Lessons==0u;
    bValid&=SoraWoodRules::JunctionValid(Save->WoodJunction,ChapterId,Beat,Saved.CompletedMask);
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
    const FRotator Facing(0,M.Arena()->PlayerStartYaw(),0);
    Player->SetActorRotation(Facing); if(Player->GetController()) Player->GetController()->SetControlRotation(Facing);
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
    if(Save) Save->WoodJunction=false;
    // Consecutive lesson duels keep their pupil on the floor; any other
    // change of beat clears the field.
    const auto Lesson=[](const FSoraBeat& Row) { return Row.Is(SoraBeatRules::EType::Duel)&&Row.bSparring&&Row.Has(SoraBeatRules::EGoal::Lessons); };
    const bool bKeepPupil=Chapter.Beats.IsValidIndex(BeatIndex)&&Lesson(Chapter.Beats[BeatIndex])&&Lesson(Beat)&&
        Chapter.Beats[BeatIndex].Task.Maai.Count==0&&Beat.Task.Maai.Count==0;
    if(Index!=0||bResumed) bChapterOpening=false;
    EndRecoveryClimb();
    ResetArchiveReveal();
    ResetWind();
    BeatIndex=Index; BeatPhase=Phase;
    Task=Beat.Task;
    static_assert(static_cast<int32>(SoraAccessibility::EDifficulty::Count)==3);
    SoraBeatRules::ApplyCarryDifficulty(Task,static_cast<int32>(SoraAccessibility::CampaignDifficulty(this)));
    SoraBeatRules::ApplyRhythmDifficulty(Task,static_cast<int32>(SoraAccessibility::CampaignDifficulty(this)));
    TaskState=SoraBeatRules::StartTask(Task,Phase);
    ResetFoundry();
    ResetHorseTreatment();
    ResetHelm();
    CancelCopying();
    SpineCut={}; SpineReadyMs=0; bSpinePromptShown=false; bSpineMutoRaised=false;
    BulkheadHold={}; BulkheadClock.Reset();
    PendingSummitPhaseSave=INDEX_NONE; PendingArchivePhaseSave=INDEX_NONE;
    ResetCarryWork();
    StopPlayerCrank(false);
    RhythmClock={}; RhythmInput={}; RhythmCueShown=-1; RhythmStrikeMs=-1;
    SoraBeatRules::RecordForms(TaskState,Task,DojoLessonMask);
    Kills=0; KillsNeeded=Task.Goal==SoraBeatRules::EGoal::Points||Task.Goal==SoraBeatRules::EGoal::Lessons?Task.Count:SoraBeatRules::TotalLethal(Task);
    ClockCarryMs=0.f; IdleMs=0; bLinesStarted=false; bCrankSlack=false; ActiveCrankHelpers=0; bCrankHelperRetreating=false; bLiftGallery=false; bDetected=false; CinematicSeconds=0.f;
    VolumesEntered.Reset(); TackSteps=0; TackRefused=0; Frightening.Reset(); BeatEvents.Reset(); WhistleAt=-1.0;
    HeldWork=EHeldWork::None; HeldPoint=INDEX_NONE; HeldMs=0; bHeldWatched=false;
    Relay={};RelayClock.Reset();RelayCatchAgeMs=0;
    CargoClock.Reset();
    Scheduled.Reset(); bWorkWasSeen=false; GuardStates.Reset(); EventRaises.Reset();
    AwaseAtMs=INDEX_NONE; LateHitAt=-1.0; BoutOffset=0;
    // The dojo numbers its bouts across the chapter's lesson duels.
    for(int32 Earlier=0;Earlier<Chapter.Beats.Num();++Earlier)
        if((BeatState.CompletedMask&SoraBeatRules::BeatBit(Earlier))!=0u&&Chapter.Beats[Earlier].Has(SoraBeatRules::EGoal::Lessons))
            BoutOffset+=Chapter.Tasks[Earlier].Count;
    if(bKeepPupil)
    {
        Enemies.RemoveAll([](const TObjectPtr<ASoraEnemy>& Enemy) { return !IsValid(Enemy)||!Enemy->IsAlive(); });
        Pending.Reset();
    }
    else ClearOpponents();
    // Saves at the beat's start; a restored checkpoint is already on disk.
    if(!bResumed&&Phase==0&&Chapter.Rules[Index].Checkpoint) SaveCheckpoint();
    // Until Sequencer cinematics land, the letterboxed card holds play, the
    // round timer and dialogue while the subtitles run on its clock and a
    // camera dollies over the place.
    if(Task.Goal==SoraBeatRules::EGoal::Elapsed) M.TitleCardTime=Task.DurationMs/1000.f;
    // The beat's place: a travel cut to its entry, its kit, horse and camera.
    EnterBeatSpace(bResumed);
    // A stealth beat opens its zone before its guards take their posts; a
    // restored checkpoint opens it afresh. Its fieldcraft follows, so its
    // floors and the candle join the zone.
    OpenStealthZone();
    if(USoraFieldcraft* Fieldcraft=USoraFieldcraft::Get(this)) Fieldcraft->Stage(Beat);
    if(Task.Goal==SoraBeatRules::EGoal::Lines&&Beat.LinesEvent==TEXT("beat_start")) StartLines();
    SpawnCast(bKeepPupil);
    ResetMaai();
    ResetEquipmentRecovery();
    if(UsesDojoQuiver()&&(bResumed||Beat.Id==TEXT("ch01.b07")||Beat.Id==TEXT("ch01.b09"))) RestoreDojoQuiver();
    BeginArchery();
    if(UsesDojoQuiver()&&Beat.bSparring&&Beat.Is(SoraBeatRules::EType::Duel)&&M.Hero()&&M.Hero()->WeaponId!=0)
    {
        M.Hero()->GetEquipment()->DropStance();
        M.Hero()->GetEquipment()->EquipClassSlot(0);
    }
    ShowEpilogue();
    Fire(TEXT("beat_start"));
    // Until Sequencer lands, a boss's intro plays its lines as the fight opens.
    if(Beat.Is(SoraBeatRules::EType::Boss)&&Phase==0) Fire(TEXT("intro_cinematic"));
    if(Task.Goal==SoraBeatRules::EGoal::Steps) Fire(TEXT("step_start:")+Beat.StepKinds[0]);
    if(Task.PhaseCount>1)
        Fire(FString::Printf(TEXT("%s_phase:%d"),Beat.Is(SoraBeatRules::EType::Duel)?TEXT("duel"):TEXT("boss"),Phase+1));
    // A lesson whose forms are already learned opens on its first bout.
    if(Task.Goal==SoraBeatRules::EGoal::Lessons&&(TaskState.Forms&Task.LessonMask)==Task.LessonMask) OpenBout();
    QueueWaves(SoraBeatRules::ReleaseWaves(TaskState,Task));
    UpdateObjective();
    BroadcastBeat(true,bResumed);
    Telemetry(bResumed?TEXT("resume"):TEXT("start"));
}
void USoraCampaignDirector::RetryBeatInPlace()
{
    ASoraGameMode& M=Mode();
    // A lost sparring match starts over where it stands: fresh points, the
    // losses and the forms learned kept, the rival back on the floor.
    StopPlayerCrank(false);
    RhythmClock={}; RhythmInput={}; RhythmCueShown=-1; RhythmStrikeMs=-1;
    TaskState=SoraBeatRules::RetryTask(TaskState,Task);
    Kills=0; ClearOpponents();
    if(ASoraPlayerCharacter* Player=M.Hero()) Player->Heal(Player->MaxHealth);
    SpawnCast(false);
    QueueWaves(SoraBeatRules::ReleaseWaves(TaskState,Task));
    Fire(TEXT("match_lost"));
    Notify(TEXT("一本取られた。構え直して、もう一度。"),TEXT("The bout is lost. Take your stance and go again."),6.f);
    UpdateObjective();
    Telemetry(TEXT("retry"));
}
void USoraCampaignDirector::CompleteActiveBeat()
{
    ASoraGameMode& M=Mode();
    const FSoraChapter& Chapter=*ActiveChapter();
    if(!Chapter.Beats.IsValidIndex(BeatIndex)) return;
    if(!HorseWithdrawalReady()) return;
    const int32 Index=BeatIndex;
    SoraBeatRules::FProgress Next=BeatState;
    if(!SoraBeatRules::CompleteBeat(Next,Chapter.Rules.GetData(),Chapter.Rules.Num(),Index)) return;
    const unsigned NewWeapons=Next.WeaponsMask&~BeatState.WeaponsMask;
    BeatState=Next;
    if(UsesDojoQuiver()&&(Index==6||Index==8)) RestoreDojoQuiver();
    if(Task.Goal==SoraBeatRules::EGoal::Elapsed) M.TitleCardTime=0.f;
    const int32 Site=Chapter.Rules[Index].Site;
    FString Japanese,English;
    if(Site>=0)
    {
        M.Arena()->ActivateSite(Site);
        if(ASoraPlayerCharacter* Player=M.Hero()) Player->Heal(22.f);
        Japanese=Chapter.Sites[Site].Restored; English=Chapter.Sites[Site].RestoredEnglish;
        Tell(FSoraStoryNotice::EKind::Site,TEXT("生産を取り戻した：")+Chapter.Sites[Site].Name,
            TEXT("Production restored: ")+Chapter.Sites[Site].NameEnglish,Japanese,English);
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
        Tell(FSoraStoryNotice::EKind::Weapon,FString::Printf(TEXT("新たな武器：%s"),*WeaponNames(NewWeapons,false)),
            FString::Printf(TEXT("New weapon: %s"),*WeaponNames(NewWeapons,true)));
    }
    for(int32 Bit=0;Bit<FSoraCatalog::Get().MechanicLabels.Num();++Bit)
        if((Chapter.Rules[Index].MechanicsMask&(1u<<Bit))!=0u)
            Tell(FSoraStoryNotice::EKind::Mechanic,TEXT("新たな技：")+FSoraCatalog::Get().MechanicLabels[Bit].Japanese,
                TEXT("New skill: ")+FSoraCatalog::Get().MechanicLabels[Bit].English);
    if(!Japanese.IsEmpty()) Notify(Japanese,English,8.f);
    TellRegistry(Index);
    Collect(Index);
    Fire(TEXT("beat_complete"));
    BroadcastBeat(false,false);
    Telemetry(TEXT("complete"));
    if(BeginWoodTransit()||BeginLiftGallery()) return;
    const int32 NextBeat=SoraBeatRules::NextBeat(BeatState,Chapter.Rules.GetData(),Chapter.Rules.Num());
    LeaveBeatSpace();
    if(NextBeat==INDEX_NONE) FinishChapter();
    else BeginBeat(NextBeat,0,false);
}
void USoraCampaignDirector::FinishChapter()
{
    ASoraGameMode& M=Mode();
    const FSoraChapter& Chapter=*ActiveChapter();
    if(!SoraBeatRules::FinishChapter(BeatState,Chapter.Rules.GetData(),Chapter.Rules.Num())) return;
    ClearOpponents();
    ClearHorses();
    if(USoraFieldcraft* Fieldcraft=USoraFieldcraft::Get(this)) Fieldcraft->Clear();
    M.bChapterComplete=true;
    Save->HighestChapter=FMath::Max(Save->HighestChapter,FMath::Min(LastChapter,ChapterId+1));
    const bool bLiberated=SoraCampaignRules::CampaignLiberated(ChapterId,LastChapter,true);
    if(bLiberated) bCampaignComplete=true;
    Fire(TEXT("chapter_complete"));
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
    if(!ClaimCacheArrows(Index)||!ClaimGalleryArrows(Index)) return;
    const unsigned NewWeapons=Next.WeaponsMask&~BeatState.WeaponsMask;
    BeatState=Next;
    Collect(Index);
    Fire(TEXT("beat_complete"),Index);
    if(NewWeapons)
        Tell(FSoraStoryNotice::EKind::Weapon,FString::Printf(TEXT("新たな武器：%s"),*WeaponNames(NewWeapons,false)),
            FString::Printf(TEXT("New weapon: %s"),*WeaponNames(NewWeapons,true)));
    if(auto* Events=USoraGameEvents::Get(this))
    {
        FSoraBeatEvent Event;
        Event.ChapterId=ChapterId; Event.BeatIndex=Index; Event.BeatId=Chapter.Beats[Index].Id; Event.bOptional=true;
        Events->OnBeatCompleted.Broadcast(Event);
    }
    UpdateObjective();
    Telemetry(TEXT("complete"),Index);
    // The find, and the cache's weapons and story flag, are saved at once
    // when the active beat can be restored from where play stands, so a
    // completist's detour never runs past the checkpoint spacing
    // (validate_campaign.py rule 8); otherwise the find is kept and the
    // beat's completion reaches the next checkpoint.
    if(Chapter.Rules[Index].Checkpoint&&CanCheckpointHere()) SaveCheckpoint();
    else SaveProgress();
}
void USoraCampaignDirector::Collect(int32 Beat)
{
    const FSoraChapter& Chapter=*ActiveChapter();
    // Wood finds belong to their physical POIs, never its exit completion.
    if(Beat==Chapter.Wood.Beat) return;
    // An explore beat's cache holds its collectibles; each goes to the codex.
    for(const FSoraCollectible& Item:Chapter.Collectibles)
    {
        const unsigned long long Bit=SoraCampaignRules::CollectibleBit(ChapterId,Item.MaskBit);
        if(!Item.Beats.Contains(Beat)||(static_cast<unsigned long long>(Save->Collectibles)&Bit)!=0ull) continue;
        Save->Collectibles=static_cast<int64>(static_cast<unsigned long long>(Save->Collectibles)|Bit);
        for(const FSoraCollectibleCategory& Category:FSoraCatalog::Get().CollectibleCategories)
            if(Category.Id==Item.Category)
                Tell(FSoraStoryNotice::EKind::Collectible,TEXT("見つけた：")+Category.Japanese,TEXT("Found: ")+Category.English,
                    Item.Codex,Item.CodexEnglish);
        Fire(TEXT("collectible:")+Item.Id,Beat); Fire(TEXT("collectible_found:")+Item.Id,Beat);
        // Preserve the original event contracts and also raise the exact
        // authored alias used by the seized-gallery memory lines.
        Fire(TEXT("event:collectible_")+Item.Id.Replace(TEXT("."),TEXT("_")),Beat);
    }
}
void USoraCampaignDirector::TickComponent(float DeltaTime,ELevelTick TickType,FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime,TickType,ThisTickFunction);
    ASoraGameMode& M=Mode();
    if(!M.bMenu)
    {
        for(FSoraStoryNotice& Notice:Notices)
            // A newly recorded entry waits through the following cinematic,
            // when the title-card path does not draw story notices.
            if(Notice.Kind!=FSoraStoryNotice::EKind::Registry||M.InputState()!=SoraInput::Card) Notice.Remaining-=DeltaTime;
        Notices.RemoveAll([](const FSoraStoryNotice& Notice) { return Notice.Remaining<=0.f; });
    }
    const FSoraBeat* Beat=ActiveBeatData();
    TickPlayerCrank(0);
    if(!PlayerRhythmEligible()&&(RhythmClock.Step>=0||RhythmInput.Active)) StopPlayerRhythm(true);
    if(!Beat||!Save||M.bDeterministicPractice||M.bMenu||M.bDefeated||M.bChapterComplete) return;
    if(Task.Goal==SoraBeatRules::EGoal::Elapsed)
    {
        UpdateCinematicCamera();
        // A cinematic runs on the card's clock; when the card closes on its own the cinematic is over.
        CinematicSeconds=M.InputState()==SoraInput::Card?FMath::Max(0.f,Task.DurationMs/1000.f-M.TitleCardTime):Task.DurationMs/1000.f;
        SoraBeatRules::FTick Step;
        Step.DeltaMs=FMath::Min(Task.DurationMs,FMath::FloorToInt32(CinematicSeconds*1000.f))-TaskState.ElapsedMs;
        SoraBeatRules::Tick(TaskState,Task,Step);
        if(M.InputState()!=SoraInput::Card&&SoraBeatRules::TaskComplete(TaskState,Task)) CompleteActiveBeat();
        return;
    }
    if(M.InputState()==SoraInput::Card) return;
    PromptRemaining=FMath::Max(0.f,PromptRemaining-DeltaTime);
    TickScheduled();
    if(ActiveBeatData()!=Beat) return;
    const bool bWasBlocking=bDialogueHeld;
    if(TickArchiveReveal(DeltaTime)) return;
    TickDialogue(DeltaTime);
    if(ActiveBeatData()!=Beat||bWasBlocking||bDialogueHeld) return;
    if(TickHorseWithdrawal(DeltaTime)||TickWoodTransit()||TickLiftGallery(DeltaTime)) return;
    TickSealCut();
    TickBeat(DeltaTime);
}
void USoraCampaignDirector::TickBeat(float DeltaSeconds)
{
    const ASoraGameMode& M=Mode();
    const FSoraBeat& Beat=*ActiveBeatData();
    // The beat clock counts whole milliseconds; the fraction carries over.
    ClockCarryMs+=DeltaSeconds*1000.f;
    const int32 DeltaMs=FMath::FloorToInt32(ClockCarryMs);
    ClockCarryMs-=DeltaMs;
    CheckPhase();
    if(ActiveBeatData()!=&Beat) return;
    SaveArrivedSummitPhase();
    // The archive's family-page checkpoint belongs after its blocking reveal.
    // Quitting or dying during the exchange must still restore phase one.
    if(PendingArchivePhaseSave!=INDEX_NONE&&!IsDialogueBlocking()&&
        FinishedLines.Contains(ActiveChapter()->LineIndex(TEXT("ch06.b09.toranosuke.006"))))
    {
        const bool Ready=Beat.Id==TEXT("ch06.b09")&&BeatPhase==PendingArchivePhaseSave;
        PendingArchivePhaseSave=INDEX_NONE;
        if(Ready) SaveCheckpoint();
    }
    TickSupplyHint();
    const int32 Before=SoraBeatRules::ProgressPermille(TaskState,Task);
    SoraBeatRules::FTick Step;
    // Work under guard pauses while any guard sees the hero or is alarmed,
    // and goes on once none does.
    const USoraStealth* Stealth=USoraStealth::Get(this);
    Step.DeltaMs=DeltaMs; Step.AtTask=HeroAtTask(); Step.Contested=Contested();
    Step.Seen=Stealth&&Stealth->IsZoneActive()&&Stealth->IsWorkPaused();
    // A cupped candle copies at its reduced pace.
    if(const USoraFieldcraft* Fieldcraft=USoraFieldcraft::Get(this)) Step.RatePermille=Fieldcraft->WorkRatePermille();
    // Work under guard stops the moment a guard sees the hero (ch06.b08's copy_paused).
    if(Task.PauseWhenSeen&&Step.Seen&&!bWorkWasSeen) Fire(TEXT("ai_event:copy_paused"));
    bWorkWasSeen=Task.PauseWhenSeen&&Step.Seen;
    // A guard the hero could take from behind, the first time (ch06.b04's first_rear_reach).
    if(Stealth&&Stealth->IsZoneActive()&&M.Hero()&&!BeatEvents.Contains(TEXT("ai_event:first_rear_reach"))&&
        Stealth->TakedownTarget(*M.Hero()))
        Fire(TEXT("ai_event:first_rear_reach"));
    Step.CrankHelpers=CrankHelpers();
    Step.CrankDecayMultiplier=LiftDecayMultiplier();
    if(!TickHelm(Step)&&!TickCopyDesk(Step)) SoraBeatRules::Tick(TaskState,Task,Step);
    if(M.bDefeated) return;
    TickPods(DeltaSeconds);
    if(ActiveBeatData()!=&Beat||M.bDefeated) return;
    TickHorseTreatment(DeltaMs);
    TickFoundry(DeltaMs);
    if(ActiveBeatData()!=&Beat||M.bDefeated) return;
    TickArchery(DeltaMs);
    TickMaai(DeltaMs);
    TickWind(DeltaMs);
    if(ActiveBeatData()!=&Beat||M.bDefeated) return;
    // Trigger volumes the hero walks or rides into raise their events: a
    // dialogue waiting on one starts, and the waves it names come.
    TickVolumes();
    if(ActiveBeatData()!=&Beat||M.bDefeated) return;
    if(Task.Goal==SoraBeatRules::EGoal::Lines&&bLinesStarted&&Queue.IsEmpty()&&DialogueLinesDone()) SoraBeatRules::FinishLines(TaskState,Task);
    // Arrivals: a dialogue's closing anchor (or its volume) after its lines, and the exit.
    const FSoraBeatSpace& Space=Beat.Space;
    const FVector Hero=M.Hero()?M.Hero()->GetActorLocation():FVector::ZeroVector;
    const FSoraVolume* Closing=Space.Volumes.FindByPredicate([&](const FSoraVolume& Volume) { return Volume.Event==Beat.ClosingEvent; });
    const bool bAtClosing=IsToriiEpilogue()?HasRehungPlaques():Closing?Closing->Contains(Hero):
        Near(ASoraWorldBuilder::Floor(Space.Closing,Space.HeightCm),SoraCampaignReach::Arrive);
    // A closing volume raised its own event as the hero entered it; an
    // "event:" closing is raised here.
    if(Task.AnchorAfterLines&&TaskState.LinesDone&&!TaskState.Reached&&bAtClosing&&SoraBeatRules::Reach(TaskState,Task)&&!Closing&&!BeatEvents.Contains(Beat.ClosingEvent))
        Fire(Beat.ClosingEvent);
    if(Task.Goal==SoraBeatRules::EGoal::Exit&&M.Hero())
    {
        // The way to the exit, so ambushes along a route come as the hero passes them.
        SoraBeatRules::Travel(TaskState,Task,RoadPermille());
        if(Space.Exit.Contains(Hero)&&(!IsWoodExplore()||AtWoodExit())&&
            (!Space.Moat.bEnabled||(USoraFieldcraft::Get(this)&&USoraFieldcraft::Get(this)->MoatExitReady()))&&
            (!Space.Climb.bEnabled||(USoraFieldcraft::Get(this)&&USoraFieldcraft::Get(this)->ClimbExitReady()))&&
            (!Space.Flood.bEnabled||(USoraFieldcraft::Get(this)&&USoraFieldcraft::Get(this)->FloodExitReady()))&&
            SoraBeatRules::Reach(TaskState,Task)) Fire(TEXT("exit_reached"));
    }
    // Work held at a point: a load hoisted, an objective worked.
    TickEquipmentRecovery(DeltaMs);
    TickCarryWork(DeltaMs);
    TickHeldWork(DeltaMs,DeltaSeconds);
    TickRelay(DeltaSeconds);
    TickPlayerCrank(DeltaMs);
    TickPlayerRhythm();
    if(ActiveBeatData()!=&Beat) return;
    TickSpineCut(DeltaMs);
    if(ActiveBeatData()!=&Beat||M.bDefeated) return;
    TickBulkhead(DeltaSeconds);
    if(ActiveBeatData()!=&Beat||M.bDefeated) return;
    // Horses, a siege on defended targets, the escorted party and the task's kit.
    TickSpace(DeltaMs);
    if(ActiveBeatData()!=&Beat||M.bDefeated) return;
    // A crank left alone goes slack.
    const bool bSlack=SoraBeatRules::CrankSlipping(TaskState,Task);
    if(bSlack&&!bCrankSlack) { Fire(TEXT("crank_released")); Fire(TEXT("event:player_left_capstan")); }
    bCrankSlack=bSlack;
    // The dojo: an awase that 転 did not follow, and one met too late.
    if(AwaseAtMs!=INDEX_NONE&&TaskState.ElapsedMs-AwaseAtMs>MarobashiWindowMs)
    {
        AwaseAtMs=INDEX_NONE;
        Fire(TEXT("marobashi_miss"));
    }
    if(LateHitAt>=0.0&&GetWorld())
    {
        const USoraEquipmentComponent* Kit=M.Hero()?M.Hero()->GetEquipment():nullptr;
        if(Kit&&Kit->IsGuardHeld()&&Kit->GuardPressedAt()>=LateHitAt)
        {
            LateHitAt=-1.0;
            Fire(TEXT("awase_fail:late"));
        }
        else if(GetWorld()->GetTimeSeconds()-LateHitAt>LateAwaseSeconds) LateHitAt=-1.0;
    }
    // Hints for a hero who has stood idle (idle_s:N).
    const int32 IdleBefore=IdleMs;
    IdleMs=FMath::Min(IdleMs+DeltaMs,SoraBeatRules::MaxClockMs);
    for(const FSoraDialogueTrigger& Trigger:ActiveChapter()->Triggers)
        if(Trigger.Beat==BeatIndex&&Trigger.On.StartsWith(TEXT("idle_s:")))
        {
            const int32 At=Threshold(Trigger.On,7,1000.0);
            if(IdleBefore<At&&IdleMs>=At) Fire(Trigger.On);
        }
    Progressed(Before);
}
bool USoraCampaignDirector::TakeLoad(int32 Pickup)
{
    const FSoraBeat* Beat=ActiveBeatData();
    if(!Beat||!SoraBeatRules::Pickup(TaskState,Task,Pickup)) return false;
    CarryChanged();
    if(!BeatEvents.Contains(TEXT("event:first_pickup"))) Fire(TEXT("event:first_pickup"));
    Fire(TEXT("item_picked:")+Beat->Pickups[Pickup]);
    Fire(TEXT("item_picked:")+Beat->CarryItem);
    return true;
}
bool USoraCampaignDirector::WorkObjectiveAt(int32 Objective)
{
    const FSoraBeat* Beat=ActiveBeatData();
    if(IsRelayRoom()&&(Objective==3?!CanReachRelay(3):!Relay.IsDisabled(Objective))) return false;
    if(!Beat||!SoraBeatRules::WorkObjective(TaskState,Task,Objective)) return false;
    if(auto* Craft=USoraFieldcraft::Get(this)) Craft->JamPress(Objective);
    Fire(TEXT("interact:")+Beat->Objectives[Objective]);
    Fire(TEXT("event:objective_done_")+Beat->Objectives[Objective]);
    return true;
}
void USoraCampaignDirector::CancelCargoUnload()
{
    if(!IsUnloadingCargo()) return;
    HeldWork=EHeldWork::None; HeldPoint=INDEX_NONE; HeldMs=0; bHeldWatched=false;
    CargoClock.Reset();
}
bool USoraCampaignDirector::DeliverLoad(int32 Dropoff,int32 HeldDurationMs)
{
    const FSoraBeat* Beat=ActiveBeatData();
    if(!Beat||!SoraBeatRules::Deliver(TaskState,Task,Dropoff,HeldDurationMs)) return false;
    if(Task.Task==SoraBeatRules::ETask::Carry) CarryChanged();
    if(Beat->Cargo.Total>0) ShowKit(); // Commit both visible sides before emitting delivery/teardown events.
    // Only a completed delivery emits credit or releases its waiting ambush.
    Fire(TEXT("item_delivered:")+Beat->Dropoffs[Dropoff]);
    if(!Beat->CarryItem.IsEmpty()) Fire(TEXT("item_delivered:")+Beat->CarryItem);
    Fire(FString::Printf(TEXT("item_delivered:load_%02d"),TaskState.Done));
    ReleaseEventWaves(TEXT("item_delivered:")+Beat->Dropoffs[Dropoff]);
    return true;
}
void USoraCampaignDirector::TickHeldWork(int32 DeltaMs,float DeltaSeconds)
{
    if(IsRelayRoom()) return; // The scan and the hold share the relay's clock.
    const FSoraBeat* Beat=ActiveBeatData();
    const FSoraBeatSpace* Space=ActiveSpace();
    ASoraPlayerCharacter* Hero=Mode().Hero();
    if(HeldWork==EHeldWork::None||!Beat||!Space||!Hero) return;
    const bool bHoist=HeldWork==EHeldWork::Hoist;
    const bool bCargo=IsUnloadingCargo();
    const TArray<FVector2D>& Points=bHoist?Space->Pickups:bCargo?Space->Dropoffs:Space->Objectives;
    const int32 Need=bHoist?Task.PickupHoldMs:bCargo?Task.UnloadHoldMs:
        Beat->ObjectiveHoldMs.IsValidIndex(HeldPoint)?Beat->ObjectiveHoldMs[HeldPoint]:0;
    const float Reach=bCargo&&IsMounted()?SoraCampaignReach::Saddle:SoraCampaignReach::Interact;
    // The work holds while Interact stays down at its point. A hoist under
    // guard waits (without letting the load fall) while a guard watches.
    if(!Hero->IsActionHeld(TEXT("Interact"))||!Points.IsValidIndex(HeldPoint)||
        !Near(ASoraWorldBuilder::Floor(Points[HeldPoint]),Reach+60.f)||
        (bCargo&&!SoraBeatRules::DropoffHasRoom(TaskState,Task,HeldPoint))||
        (HeldWork==EHeldWork::Objective&&Space->PressHall.bEnabled&&
            (!USoraFieldcraft::Get(this)||!USoraFieldcraft::Get(this)->CanWorkPress(HeldPoint))))
    {
        HeldWork=EHeldWork::None; HeldPoint=INDEX_NONE; HeldMs=0; bHeldWatched=false;
        CargoClock.Reset();
        return;
    }
    const USoraStealth* Stealth=USoraStealth::Get(this);
    const bool bWatched=bHoist&&Task.PauseWhenSeen&&Stealth&&Stealth->IsZoneActive()&&Stealth->IsWorkPaused();
    if(bWatched&&!bHeldWatched) Fire(TEXT("ai_event:hoist_paused"));
    bHeldWatched=bWatched;
    if(bWatched) return;
    // Cargo owns a clock from the press: TickBeat's earlier fraction must
    // never count toward a new unload. Other held work keeps its timing.
    if(bCargo) HeldMs+=FMath::Clamp(CargoClock.Advance(DeltaSeconds),0,FMath::Max(0,Need-HeldMs));
    else HeldMs+=DeltaMs;
    if(HeldMs<Need) return;
    const int32 Before=SoraBeatRules::ProgressPermille(TaskState,Task);
    const int32 DoneBefore=TaskState.Done;
    const int32 Point=HeldPoint;
    const int32 Duration=HeldMs;
    HeldWork=EHeldWork::None; HeldPoint=INDEX_NONE; HeldMs=0; bHeldWatched=false;
    CargoClock.Reset();
    if(bHoist?TakeLoad(Point):bCargo?DeliverLoad(Point,Duration):WorkObjectiveAt(Point))
    {
        if(bCargo&&DoneBefore==0&&TaskState.Done>0) Fire(TEXT("interact_start"));
        UpdateObjective();
        Progressed(Before);
    }
}
float USoraCampaignDirector::HeldWorkProgress() const
{
    if(IsCopying()) return static_cast<float>(TaskState.HoldProgress[CopyDesk])/Task.HoldPointMs;
    if(HorseTreatmentOccupiesHands()) return float(Treatment.HeldMs)/SoraHorseTreatmentRules::HoldMs;
    if(FoundryOccupiesHands()) return float(Foundry.HeldMs)/SoraFoundryDefenseRules::Need(Foundry.Work);
    if(IsHelmHold()&&Helm.Working) return static_cast<float>(Helm.HeldMs)/ActiveSpace()->Helm.Contract.WorkMs;
    if(SpineCut.Active&&ActiveBeatData()&&ActiveBeatData()->CaptureHoldMs>0)
        return static_cast<float>(SpineCut.HeldMs)/ActiveBeatData()->CaptureHoldMs;
    if(BulkheadHold.Active&&ActiveBeatData()&&ActiveBeatData()->CaptureHoldMs>0)
        return static_cast<float>(BulkheadHold.HeldMs)/ActiveBeatData()->CaptureHoldMs;
    if(bPryingCarryGate&&Task.CarryGateMs>0) return static_cast<float>(TaskState.CarryGateHeldMs)/Task.CarryGateMs;
    if(bStringingBow&&Task.RecoveryStringMs>0) return static_cast<float>(TaskState.RecoveryHeldMs)/Task.RecoveryStringMs;
    const FSoraBeat* Beat=ActiveBeatData();
    const int32 Need=HeldWork==EHeldWork::Hoist?Task.PickupHoldMs
        :IsUnloadingCargo()?Task.UnloadHoldMs
        :Beat&&Beat->ObjectiveHoldMs.IsValidIndex(HeldPoint)?Beat->ObjectiveHoldMs[HeldPoint]:0;
    return HeldWork!=EHeldWork::None&&Need>0?FMath::Clamp(static_cast<float>(HeldMs)/Need,0.f,1.f):-1.f;
}
void USoraCampaignDirector::Progressed(int32 PermilleBefore)
{
    const FSoraBeat* Beat=ActiveBeatData();
    if(!Beat) return;
    const int32 After=SoraBeatRules::ProgressPermille(TaskState,Task);
    if(After!=PermilleBefore)
    {
        IdleMs=0;
        for(const FSoraDialogueTrigger& Trigger:ActiveChapter()->Triggers)
            if(Trigger.Beat==BeatIndex&&Trigger.On.StartsWith(TEXT("progress_at:")))
            {
                const int32 At=Threshold(Trigger.On,12,1000.0);
                if(PermilleBefore<At&&After>=At) Fire(Trigger.On);
            }
        UpdateObjective();
    }
    QueueWaves(SoraBeatRules::ReleaseWaves(TaskState,Task));
    SpawnPending();
    if(SoraBeatRules::TaskComplete(TaskState,Task)&&LiftReadyToComplete()&&SpireReadyToComplete()&&RidgeReadyToComplete()&&FoundryReadyToComplete()) CompleteActiveBeat();
}
void USoraCampaignDirector::QueueWaves(unsigned Waves)
{
    const FSoraBeat* Beat=ActiveBeatData();
    if(!Beat||Waves==0u||bHorseWithdrawal) return;
    const uint64 Generation=PodGeneration;
    for(int32 Wave=0;Wave<Beat->Waves.Num();++Wave)
    {
        if((Waves&(1u<<Wave))==0u) continue;
        const bool Pod=Beat->Space.PodArrivals.IsValidIndex(Wave);
        if(Pod&&(PodQueued&(1u<<Wave))) continue;
        if(Pod) PodQueued|=1u<<Wave;
        int32 PodMember=0;
        // Debt-bound conscripts fight beside the wave but never count toward
        // it: a lethal blow only knocks one down, and cutting its seal frees it.
        if(!IsArcheryLesson())
        {
            for(const FSoraWaveGroup& Group:Beat->Waves[Wave].Groups)
            {
                if(Group.bLethal)
                {
                    for(int32 Member=0;Member<Group.Count;++Member)
                        Pending.Add({Wave,Group.Type,Group.bInvulnerable,Pod?PodMember++:INDEX_NONE,Group.Spawn,Member});
                }
                else if(!Beat->bSparring&&GetWorld())
                {
                    for(int32 Member=0;Member<Group.Count;++Member)
                        if(ASoraEnemy* Conscript=ASoraEnemy::SpawnArchetype(*GetWorld(),Group.Type,Spawned,SpawnLocation(Spawned),FRotator(0,180,0)))
                            AddOpponent(Conscript,INDEX_NONE);
                }
            }
        }
        if(Pod) ActivatePod(Wave);
        if(PodGeneration!=Generation||ActiveBeatData()!=Beat||Mode().bDefeated) return;
        Fire(FString::Printf(TEXT("wave_start:%d"),Wave+1));
        Fire(FString::Printf(TEXT("event:wave_start_%d"),Wave+1));
        Fire(TEXT("wave_spawned"));
        Fire(FString::Printf(TEXT("wave_spawned:%d"),Wave+1));
        if(!Beat->Waves[Wave].Id.IsEmpty()) Fire(TEXT("wave_spawned:")+Beat->Waves[Wave].Id);
        if(PodGeneration!=Generation||ActiveBeatData()!=Beat||Mode().bDefeated) return;
    }
    SpawnPending();
    UpdateObjective();
}
void USoraCampaignDirector::CheckPhase()
{
    if(Task.Goal!=SoraBeatRules::EGoal::OpponentDown) return;
    const ASoraEnemy* Opponent=CampaignBoss();
    for(int32 Index=0;!Opponent&&Index<Enemies.Num();++Index)
        if(IsValid(Enemies[Index])&&Enemies[Index]->IsAlive()) Opponent=Enemies[Index];
    if(!Opponent||Opponent->MaxHealth<=0.f) return;
    const int32 Before=SoraBeatRules::ProgressPermille(TaskState,Task);
    const int32 PhaseBefore=TaskState.Phase;
    if(!SoraBeatRules::OpponentHealth(TaskState,Task,FMath::RoundToInt32(1000.f*Opponent->Health/Opponent->MaxHealth)))
        return;
    EnterPhases(PhaseBefore,true);
    Progressed(Before);
}
void USoraCampaignDirector::EnterPhases(int32 Before,bool bSave)
{
    if(TaskState.Phase==Before) return;
    const FSoraBeat& Beat=*ActiveBeatData();
    const bool bDuel=Beat.Is(SoraBeatRules::EType::Duel);
    // One blow can carry the opponent past more than one threshold: every
    // phase it passes plays its lines and its scripted event, in order.
    for(int32 Phase=Before+1;Phase<=TaskState.Phase;++Phase)
    {
        BeatPhase=Phase;
        if(Mode().Arena()) Mode().Arena()->ShowArchivePage(Beat,BeatPhase);
        // The family-page reveal precedes the remembered phase-two lesson;
        // otherwise its radio lines sit ahead of the blocking exchange.
        const bool Archive=Beat.Id==TEXT("ch06.b09");
        if(Archive&&Phase==1&&bSave)
        {
            bArchiveRevealPending=true;
            if(Mode().Arena()) Mode().Arena()->StageArchiveReveal(0.f);
        }
        if(Archive&&Beat.PhaseEvents.IsValidIndex(Phase-1)) Fire(TEXT("duel_event:")+Beat.PhaseEvents[Phase-1]);
        Fire(FString::Printf(TEXT("%s_phase:%d"),bDuel?TEXT("duel"):TEXT("boss"),Phase+1));
        if(bDuel&&!Archive&&Beat.PhaseEvents.IsValidIndex(Phase-1)) Fire(TEXT("duel_event:")+Beat.PhaseEvents[Phase-1]);
        Telemetry(TEXT("phase"));
    }
    // A long boss or duel also saves at each later phase; the opponent then
    // returns at that phase's health.
    if(bSave&&BeatPhase<=ActiveChapter()->Rules[BeatIndex].PhaseCheckpoints)
    {
        if(Beat.Space.Summit.Enabled()) PendingSummitPhaseSave=BeatPhase;
        else if(Beat.Id==TEXT("ch06.b09")) PendingArchivePhaseSave=BeatPhase;
        else SaveCheckpoint();
    }
    BroadcastBeat(true,false);
}
void USoraCampaignDirector::SkipCinematic()
{
    ASoraGameMode& M=Mode();
    const FSoraBeat* Beat=ActiveBeatData();
    if(!Beat||Task.Goal!=SoraBeatRules::EGoal::Elapsed) { M.TitleCardTime=0.f; return; }
    if(!SoraBeatRules::Skip(TaskState,Task)) return;
    Telemetry(TEXT("skip"));
    CompleteActiveBeat();
}
ASoraEnemy* USoraCampaignDirector::SpawnWaveOpponent(FName Type,bool bSparring,int32 Slot,bool bInvulnerable,const FVector* Position)
{
    // Sparring beats (bokuto bouts, the matoba's targets) keep the chapter-one
    // pupil; every other opponent is its enemies.json archetype, hunting the hero.
    UWorld* World=GetWorld();
    if(!World) return nullptr;
    if(bSparring) return SpawnPrototype(*World,SpawnLocation(Slot),true,Slot);
    FSoraEnemyTuning Tuning;
    Tuning.bInvulnerable=bInvulnerable;
    if(const auto* Space=ActiveSpace();Space&&Space->Wind.Ridge()) Tuning.NetRootMs=SoraRidgeRules::NetRootMs;
    return ASoraEnemy::SpawnArchetype(*World,Type,Slot,Position?*Position:SpawnLocation(Slot),FRotator(0,180,0),nullptr,&Tuning);
}
ASoraEnemy* USoraCampaignDirector::SpawnStealthGuard(const FSoraGuard& Guard,int32 GuardIndex,int32 Slot)
{
    // The archetype walks its patrol route from its first point, unaware
    // until USoraStealth's perception reports it (alert_state events).
    const FSoraBeatSpace* Space=ActiveSpace();
    if(!GetWorld()||!Space) return nullptr;
    FSoraPatrolRoute Route;
    const TArray<FVector2D>* Points=Space->Patrols.IsEmpty()?nullptr:&Space->Patrols[Slot%Space->Patrols.Num()];
    if(Points)
        for(const FVector2D& Point:*Points) Route.Points.Add(ASoraWorldBuilder::Floor(Point,90.f));
    FVector Post=Points&&!Points->IsEmpty()?ASoraWorldBuilder::Floor((*Points)[0],120.f):SpawnLocation(Slot);
    if(Space->Moat.bEnabled)
    {
        const float Z=GuardIndex==2?600.f:1840.f;
        for(auto& Point:Route.Points)Point.Z=Z;
        if(!Route.Points.IsEmpty())Post=Route.Points[0];
    }
    if(Space->Climb.bEnabled&&GuardIndex==Space->Climb.GuardIndex)
    { Post=FVector(Space->Climb.Origin,0)+FVector(360,-300,1690);Route.Points={Post}; }
    if(Space->RelayRoom.bEnabled)
    {
        const FVector Origin(Space->RelayRoom.Origin,0);
        Route.Points.Reset();Route.PauseMs=0;Route.bThreeDimensional=true;
        if(GuardIndex==0)
        {
            for(const FVector2D P:{FVector2D(650,200),FVector2D(1350,200),FVector2D(1350,800),FVector2D(650,800)})
                Route.Points.Add(Origin+FVector(P,90));
            Route.PeriodMs=50000;
        }
        else if(GuardIndex==1)
        {
            Route.bSupportedSegments=true;Route.bSupportedSteps=true;
            for(const FVector2D P:{FVector2D(510,840),FVector2D(510,160),FVector2D(1490,160),FVector2D(1490,840)})
                Route.Points.Add(Origin+FVector(P,490));
            Route.PeriodMs=40000;
            Route.AlternatePoints.Add(Route.Points[0]);
            // Short, similarly sized legs leave enough time to walk the
            // steep stair on every other 40 s circuit at the actual speed.
            for(int Side=0;Side<4;++Side)
            {
                const int Parts=Side%2==0?3:4;
                for(int I=1;I<=Parts;++I)
                    Route.AlternatePoints.Add(FMath::Lerp(Route.Points[Side],Route.Points[(Side+1)%4],float(I)/Parts));
            }
            for(int I=4;I>=0;--I) Route.AlternatePoints.Add(Origin+FVector(110+80*I,850,90+80*I));
            for(int I=1;I<=4;++I) Route.AlternatePoints.Add(Origin+FVector(110+80*I,850,90+80*I));
        }
        else if(GuardIndex==2)
        { Route.Points.Add(Origin+FVector(300,500,90));Route.PauseFacing=FVector(1,0,0); }
        else
        {
            // A 1.2 m orbit leaves the 0.8 m column and the north control's
            // approach clear at the authored five-metre flight height.
            Route.bDirectFlightSegments=true;
            for(int I=0;I<8;++I)
                Route.Points.Add(Origin+FVector(1000+120*FMath::Cos(I*PI/4),500+120*FMath::Sin(I*PI/4),500));
            Route.PeriodMs=30000;
        }
        Post=Route.Points[0];
    }
    if(Space->PressHall.bEnabled&&SoraPressRules::PatrolCount(GuardIndex)>0)
    {
        Route.Points.Reset();
        for(int I=0;I<SoraPressRules::PatrolCount(GuardIndex);++I)
        {
            const auto Point=SoraPressRules::PatrolPoint(GuardIndex,I);
            Route.Points.Add(FVector(Space->PressHall.Origin+FVector2D(Point.X,Point.Y),SoraPressRules::PatrolFloor(GuardIndex)+90.f));
        }
        Route.PeriodMs=SoraPressRules::PatrolPeriod(GuardIndex);
        Route.PauseMs=SoraPressRules::PatrolDwell(GuardIndex);
        Route.bThreeDimensional=true;
        Route.bSupportedSegments=GuardIndex==SoraPressRules::CatwalkGuard;
        if(GuardIndex<2) Route.PauseFacing=FVector(0,1,0);
        Post=Route.Points[0]+FVector(0,0,30);
    }
    if(Space->LedgerHall.bEnabled&&ActiveBeatData()->Id==TEXT("ch06.b06")&&GuardIndex<SoraLedgerRules::GuardCount)
    {
        Route.Points.Reset();
        for(const auto& P:Space->Patrols[GuardIndex])
            Route.Points.Add(FVector(P,SoraLedgerRules::HeightCm[GuardIndex]>0?SoraLedgerRules::HeightCm[GuardIndex]:90));
        Route.PeriodMs=SoraLedgerRules::PeriodMs[GuardIndex];Route.PauseMs=0;
        Route.bSupportedSegments=SoraLedgerRules::HeightCm[GuardIndex]==0;
        Route.bThreeDimensional=true;Route.bDirectFlightSegments=!Route.bSupportedSegments;
        Post=Route.Points[0];
    }
    if(Space->RegistryHall.bEnabled&&Space->Patrols.IsValidIndex(GuardIndex))
    {
        Route.Points.Reset();
        for(const auto& P:Space->Patrols[GuardIndex])
            Route.Points.Add(FVector(P,GuardIndex==4?400.f:Space->FloorAt(P)+90.f));
        if(GuardIndex<3)
        {
            Route.PointPauseMs.Init(0,Route.Points.Num());
            Route.PointPauseMs[0]=SoraRegistryRules::AuditorDwellMs(GuardIndex);
            Route.PauseFacing=FVector(0,1,0);
        }
        if(GuardIndex>=3)
        {
            Route.PeriodMs=GuardIndex==3?60000:30000;Route.PauseMs=0;
            Route.bThreeDimensional=true;Route.bSupportedSegments=GuardIndex==3;
            Route.bDirectFlightSegments=GuardIndex==4;
        }
        Post=Route.Points[0];
    }
    if(Route.Points.IsEmpty()) Route.Points.Add(FVector(Post.X,Post.Y,90.f));
    // A route of two points is walked back and forth; a longer one loops. A
    // guard the chapter posts keeps the first point of its round as its post.
    if(Guard.bPost&&Route.Points.Num()>1) Route.Points.SetNum(1);
    Route.bPingPong=Route.Points.Num()==2;
    // A guard the script posts on a roof (ch03.b10's marksman) stands up there.
    if(const USoraFieldcraft* Fieldcraft=USoraFieldcraft::Get(this); Fieldcraft&&Fieldcraft->Active())
        for(const FSoraLadder& Ladder:Fieldcraft->Active()->Ladders)
            if(Ladder.Guards.Contains(GuardIndex))
            {
                Post=FVector(Ladder.Roof.Center,Ladder.HeightCm+120.f);
                Route.Points.Reset();
                Route.Points.Add(FVector(Ladder.Roof.Center,Ladder.HeightCm+90.f));
                Route.bPingPong=false;
            }
    // The senses the chapter authors for this guard.
    FSoraEnemyTuning Senses;
    Senses.SightCm=Guard.SightCm; Senses.DarkSightCm=Guard.DarkSightCm; Senses.ViewDegrees=Guard.ViewDegrees;
    Senses.HearingCm=Guard.HearingCm; Senses.SuspicionPermille=Guard.SuspicionPermille;
    Senses.ScanDegrees=Guard.ScanDegrees; Senses.ScanMs=Guard.ScanMs; Senses.TurnMs=Guard.TurnMs;
    auto* GuardActor=ASoraEnemy::SpawnArchetype(*GetWorld(),Guard.Type,Slot,Post,FRotator(0,180,0),&Route,&Senses);
    if(GuardActor&&Space->RelayRoom.bEnabled)
    {
        if(GuardIndex!=3)
        {
            const float Offset=GuardActor->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2.f-90.f;
            for(auto& P:Route.Points) P.Z+=Offset;
            for(auto& P:Route.AlternatePoints) P.Z+=Offset;
        }
        GuardActor->SetActorLocation(Route.Points[0]);
        if(GuardIndex==2) GuardActor->SetActorRotation(FRotator::ZeroRotator);
        if(auto* Brain=Cast<ASoraEnemyController>(GuardActor->GetController())) Brain->BeginPatrol(Route);
    }
    if(GuardActor&&Space->PressHall.bEnabled&&SoraPressRules::PatrolCount(GuardIndex)>0)
    {
        // Resolve the spawned body's actual scaled capsule (the drone is
        // smaller), so scheduled flight follows the recorded floor height.
        for(auto& Point:Route.Points)
            Point.Z=SoraPressRules::PatrolFloor(GuardIndex)+GuardActor->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2.f;
        GuardActor->SetActorLocation(Route.Points[0]);
        if(auto* Brain=Cast<ASoraEnemyController>(GuardActor->GetController())) Brain->BeginPatrol(Route);
    }
    if(GuardActor&&Space->LedgerHall.bEnabled&&ActiveBeatData()->Id==TEXT("ch06.b06")&&
        GuardIndex>=0&&GuardIndex<SoraLedgerRules::GuardCount&&!Route.Points.IsEmpty())
    {
        if(SoraLedgerRules::HeightCm[GuardIndex]==0)
            for(auto& P:Route.Points) P.Z=GuardActor->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2.f;
        GuardActor->SetActorLocation(Route.Points[0]);
        GuardActor->SetActorRotation(FRotator(0,SoraLedgerRules::Yaw[GuardIndex],0));
        if(auto* Brain=Cast<ASoraEnemyController>(GuardActor->GetController())) Brain->BeginPatrol(Route);
        if(auto* Craft=USoraFieldcraft::Get(this)) Craft->AssignLedgerAuditor(*GuardActor,GuardIndex);
    }
    if(GuardActor&&Space->RegistryHall.bEnabled&&!Route.Points.IsEmpty())
    {
        if(GuardIndex!=4)
            for(auto& P:Route.Points) P.Z=Space->FloorAt(FVector2D(P))+GuardActor->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2.f;
        GuardActor->SetActorLocation(Route.Points[0]);
        if(auto* Brain=Cast<ASoraEnemyController>(GuardActor->GetController())) Brain->BeginPatrol(Route);
        if(auto* Craft=USoraFieldcraft::Get(this)) Craft->AssignRegistryAuditor(*GuardActor,GuardIndex);
    }
    if(GuardActor&&Space->Moat.bEnabled)
        if(auto* Craft=USoraFieldcraft::Get(this))Craft->AssignMoatGuard(*GuardActor,GuardIndex);
    if(GuardActor&&Space->Climb.bEnabled&&GuardIndex==Space->Climb.GuardIndex)
        if(auto* Craft=USoraFieldcraft::Get(this)) Craft->AssignClimbSentry(*GuardActor);
    return GuardActor;
}
ASoraEnemy* USoraCampaignDirector::SpawnDuelOpponent(FName Opponent,bool bSparring,int32 Slot)
{
    // A rival duel staged in bosses.json (Toranosuke's fukuro-shinai and steel
    // duels) is that fight; the dojo's other lesson bouts are sparring pupils.
    UWorld* World=GetWorld();
    const FSoraBeat* Beat=ActiveBeatData();
    if(!World) return nullptr;
    FSoraBossCatalog& Bosses=FSoraBossCatalog::Get();
    const FSoraBossData* Duel=Beat&&(Bosses.IsReady()||Bosses.Load())?Bosses.ForBeat(Beat->Id):nullptr;
    if(Duel&&Duel->bDuel&&Duel->Opponent==Opponent)
    {
        FSoraBossSetup Setup;
        Setup.Difficulty=BossDifficulty(this); Setup.Phase=TaskState.Phase;
        return ASoraBoss::SpawnBoss(*World,Duel->Id,Slot,SpawnLocation(Slot),FRotator(0,180,0),Setup);
    }
    return SpawnPrototype(*World,SpawnLocation(Slot),bSparring,Slot,Beat?Beat->PupilTiming:SoraDojoRules::FPupilTiming{});
}
ASoraBoss* USoraCampaignDirector::SpawnBoss(FName Boss,int32 Slot)
{
    // The bosses.json boss with its pattern tables, defenses and adds, on the
    // settings' difficulty; a restored phase checkpoint starts it at that phase.
    if(!GetWorld()) return nullptr;
    FSoraBossSetup Setup;
    Setup.Difficulty=BossDifficulty(this); Setup.Phase=TaskState.Phase;
    if(const auto* Space=ActiveSpace();Space&&Space->Summit.Enabled())
    {
        Setup.bHasArenaCenter=true; Setup.ArenaCenter=FVector(Space->Summit.Center,Space->HeightCm+90);
        Setup.ArenaRadiusCm=1800;
        Setup.bSummit=true; Setup.SummitDaisFloor=FVector(Space->Summit.Center,Space->HeightCm)+FVector(0,320,120);
    }
    return ASoraBoss::SpawnBoss(*GetWorld(),Boss,Slot,SpawnLocation(Slot),FRotator(0,180,0),Setup);
}
void USoraCampaignDirector::SpawnCast(bool bKeepPupil)
{
    const FSoraBeat* Beat=ActiveBeatData();
    if(!Beat) return;
    // A boss or duel restored at a later phase returns at that phase's health.
    const float Health=SoraBeatRules::PhaseStartPermille(Task,TaskState.Phase)/1000.f;
    if(Beat->Is(SoraBeatRules::EType::Boss))
    {
        if(ASoraBoss* Boss=SpawnBoss(Beat->Opponent,Spawned))
        {
            BossActor=Boss;
            AddOpponent(Boss,INDEX_NONE);
        }
    }
    else if(Beat->Is(SoraBeatRules::EType::Duel)&&(!bKeepPupil||Enemies.IsEmpty()))
    {
        if(ASoraEnemy* Duellist=SpawnDuelOpponent(Beat->Opponent,Beat->bSparring,Spawned))
        {
            if(!Duellist->IsA<ASoraBoss>()) Duellist->Health=Duellist->MaxHealth*Health;
            AddOpponent(Duellist,INDEX_NONE);
        }
    }
    // A stealth zone's guards, and those watching guarded work, take their posts.
    else
        for(int32 Index=0;Index<Beat->Guards.Num();++Index)
            if(ASoraEnemy* Enemy=SpawnStealthGuard(Beat->Guards[Index],Index,Spawned)) AddOpponent(Enemy,INDEX_NONE);
}
void USoraCampaignDirector::SpawnPending()
{
    const FSoraBeat* Beat=ActiveBeatData();
    if(!Beat||bHorseWithdrawal) return;
    if(IsRelayRoom()&&!Relay.ReinforcementsReady()) return;
    for(int32 Alive=LiveWaveOpponents();!Pending.IsEmpty()&&Alive<Task.MaxAlive;)
    {
        const FPendingSpawn Next=Pending[0];
        const bool Pod=Beat->Space.PodArrivals.IsValidIndex(Next.Wave);
        if(Pod&&!PodState[Next.Wave].Impacted) break;
        FVector PodPosition=FVector::ZeroVector;
        const bool Ledger=Beat->Space.LedgerHall.bEnabled&&!Next.Spawn.IsNone();
        if(Ledger)
        {
            const bool North=Next.Spawn==TEXT("sp_aisle_north_door");
            check((North||Next.Spawn==TEXT("sp_aisle_south_door"))&&Next.SpawnMember>=0&&Next.SpawnMember<2);
            const auto At=SoraLedgerRules::Reinforcement[North?Next.SpawnMember:Next.SpawnMember+2];
            PodPosition=FVector(Beat->Space.LedgerHall.Origin,120)+FVector(At.X,At.Y,0);
        }
        if(IsRelayRoom()) PodPosition=FVector(Beat->Space.RelayRoom.Origin,0)+FVector(1850,400+200*(Alive%2),120);
        if(Pod)
        {
            check(Next.PodMember>=0&&Next.PodMember<SoraPodRules::Members);
            const auto& Offset=SoraPodRules::Offsets[Next.PodMember];
            PodPosition=Beat->Space.PodArrivals[Next.Wave].Floor+FVector(Offset[0],Offset[1],120);
        }
        Pending.RemoveAt(0);
        ASoraEnemy* Enemy=Beat->Space.Lift.bEnabled?SpawnLiftOpponent(Next.Type,Next.Wave,Spawned):
            SpawnWaveOpponent(Next.Type,Beat->bSparring,Spawned,Next.bInvulnerable,(Pod||IsRelayRoom()||Ledger)?&PodPosition:nullptr);
        if(Enemy)
        {
            if(Ledger) { Enemy->Tags.Add(TEXT("LedgerReinforcement"));Enemy->Tags.Add(Next.Spawn); }
            AddOpponent(Enemy,Next.Wave); ++Alive;
        }
        else
        {
            // A wave never waits on an opponent the world could not build.
            UE_LOG(LogTemp,Error,TEXT("SORA campaign: %s could not spawn %s; it counts as down"),*Beat->Id,*Next.Type.ToString());
            SoraBeatRules::RecordDefeat(TaskState,Task,Next.Wave);
        }
    }
}
void USoraCampaignDirector::AddOpponent(ASoraEnemy* Enemy,int32 Wave)
{
    if(ActiveSpace()&&ActiveSpace()->Spire.Enabled()&&Enemy&&Enemy->IsFlying())
        if(auto* Brain=Cast<ASoraEnemyController>(Enemy->GetController())) Brain->AssignSpireFlight();
    Enemies.Add(Enemy); EnemyWaves.Add(TWeakObjectPtr<const ASoraEnemy>(Enemy),Wave); ++Spawned;
    if(Enemy) BindHorseGrenadier(*Enemy,Wave);
    // A wave's drones may be the beat's seizure drones or its scouts.
    if(USoraFieldcraft* Fieldcraft=USoraFieldcraft::Get(this); Fieldcraft&&Enemy&&Wave!=INDEX_NONE) Fieldcraft->OpponentJoined(*Enemy,Wave);
}
void USoraCampaignDirector::SpawnArenaInvader()
{
    ASoraWorldBuilder* WorldBuilder=Mode().Arena();
    if(!WorldBuilder||!GetWorld()) return;
    if(ASoraEnemy* Enemy=SpawnPrototype(*GetWorld(),WorldBuilder->SpawnPoint(Spawned),false,Spawned)) AddOpponent(Enemy,INDEX_NONE);
}
int32 USoraCampaignDirector::LiveWaveOpponents() const
{
    int32 Count=0;
    for(const auto& Enemy:Enemies)
        if(IsValid(Enemy)&&Enemy->IsAlive())
            if(const int32* Wave=EnemyWaves.Find(TWeakObjectPtr<const ASoraEnemy>(Enemy.Get()))) Count+=*Wave!=INDEX_NONE;
    return Count;
}
void USoraCampaignDirector::ClearOpponents()
{
    ResetPods();
    ClearArchery();
    // A falling opponent removes itself after its lifespan. Everyone else
    // leaves now: the living, a captive the hero has bound, a knocked-down
    // conscript (whose collar would drag it up with nobody tracking it) and a
    // guard's body, knocked out or killed.
    for(const auto& Enemy:Enemies)
        if(IsValid(Enemy)&&!Enemy->IsActorBeingDestroyed()&&(Enemy->IsAlive()||Enemy->GetLifeSpan()<=0.f)) Enemy->Destroy();
    if(IsValid(Captive)) Captive->Destroy();
    Enemies.Reset(); EnemyWaves.Reset(); Frightening.Reset(); Pending.Reset(); BossActor=nullptr; Spawned=0;
    Captive=nullptr;
}
bool USoraCampaignDirector::SparesOpponent(const ASoraEnemy& Opponent) const
{
    return ActiveBeatData()&&Task.Goal==SoraBeatRules::EGoal::OpponentDown&&Task.Defeat!=SoraBeatRules::EDefeat::Kill&&
        Enemies.ContainsByPredicate([&](const TObjectPtr<ASoraEnemy>& Enemy) { return Enemy.Get()==&Opponent; });
}
bool USoraCampaignDirector::IsCaptive(const ASoraEnemy& Opponent) const
{
    return AwaitingCapture()&&Captive.Get()==&Opponent;
}
bool USoraCampaignDirector::AwaitingCapture() const
{
    return ActiveBeatData()&&SoraBeatRules::AwaitsCapture(TaskState,Task);
}
void USoraCampaignDirector::ClearEncounter()
{
    ResetFoundry();
    ResetHorseTreatment();
    BulkheadHold={}; BulkheadClock.Reset();
    CancelHelm();
    Helm={};
    CancelCopying();
    ResetWind();
    CloseStealthZone();
    if(USoraFieldcraft* Fieldcraft=USoraFieldcraft::Get(this)) Fieldcraft->Clear();
    ClearOpponents();
    ClearOfflineProjectiles();
    ClearHorses();
    bLiftGallery=false; bWoodTransit=false;
    EndCinematicCamera(0.f);
    Kills=0;
    ClearDialogue(); PromptRemaining=0.f; Notices.Reset();
    if(ASoraWorldBuilder* WorldBuilder=Mode().Arena())
    {
        WorldBuilder->ShowObjective(nullptr); WorldBuilder->ShowCaches({}); WorldBuilder->ClearKit();
        WorldBuilder->ShowCarried(Mode().Hero(),NAME_None);
    }
}
const ASoraBoss* USoraCampaignDirector::CampaignBoss() const
{
    return IsValid(BossActor)&&BossActor->IsAlive() ? BossActor.Get() : nullptr;
}
void USoraCampaignDirector::FireDialogueTrigger(FName Event)
{
    if(Mode().bCampaign&&ActiveBeatData()) Fire(Event.ToString());
}
bool USoraCampaignDirector::TriggerAllowed(int32 Index) const
{
    const FSoraDialogueTrigger& Trigger=ActiveChapter()->Triggers[Index];
    if(!Trigger.bRepeatable&&FiredTriggers.Contains(Index)) return false;
    // A conditional line waits for its find or its story flag.
    if((CollectedMask()&Trigger.RequiresCollectible)!=Trigger.RequiresCollectible||
        (BeatState.FlagsMask&Trigger.RequiresFlags)!=Trigger.RequiresFlags)
        return false;
    const double* Last=TriggerTimes.Find(Index);
    return !Last||!GetWorld()||GetWorld()->GetTimeSeconds()-*Last>=Trigger.CooldownSeconds;
}
void USoraCampaignDirector::Fire(const FString& Event,int32 Beat,bool bReplayLines)
{
    const FSoraChapter* Chapter=ActiveChapter();
    if(Beat==INDEX_NONE) Beat=BeatIndex;
    if(!Chapter||Event.IsEmpty()) return;
    // The first time the active beat raises an event, its ":first" rows play too.
    bool bRaised=false;
    if(Beat==BeatIndex) BeatEvents.Add(Event,&bRaised);
    const bool bFirst=Beat==BeatIndex&&!bRaised;
    const FString First=Event+TEXT(":first");
    // The Nth time the beat raises an event, its "<event>@N" rows play too
    // (ch02.b08's first net, ai:convoy_netted@1).
    const int32 Raises=Beat==BeatIndex?++EventRaises.FindOrAdd(Event):0;
    const FString Nth=Raises>0?FString::Printf(TEXT("%s@%d"),*Event,Raises):FString();
    for(int32 Index=0;Index<Chapter->Triggers.Num();++Index)
    {
        const FSoraDialogueTrigger& Trigger=Chapter->Triggers[Index];
        // The beat's own rows and the chapter's bark pools.
        if((Trigger.Beat!=Beat&&Trigger.Beat!=INDEX_NONE)||
            (Trigger.On!=Event&&!(bFirst&&Trigger.On==First)&&!(Raises>0&&Trigger.On==Nth))||!TriggerAllowed(Index))
            continue;
        FiredTriggers.Add(Index);
        if(GetWorld()) TriggerTimes.Add(Index,GetWorld()->GetTimeSeconds());
        Enqueue(Trigger.Lines,bReplayLines,Trigger.Mode);
    }
    ShowPrompt(Event,Beat);
    // A prompt keyed "<event>:first" shows on the event's first raise in the
    // beat, one keyed "<event>@N" on its Nth.
    if(bFirst) ShowPrompt(First,Beat);
    if(Raises>0) ShowPrompt(Nth,Beat);
    if(Beat!=BeatIndex) return;
    // A row keyed "<event>+Ns" plays N seconds after the event, once.
    if(GetWorld())
    {
        const FString Delayed=Event+TEXT("+");
        TSet<FString> Due;
        for(const FSoraDialogueTrigger& Trigger:Chapter->Triggers)
            if(Trigger.Beat==Beat&&Trigger.On.StartsWith(Delayed)&&Trigger.On.EndsWith(TEXT("s"))) Due.Add(Trigger.On);
        for(const FSoraPrompt& Prompt:Chapter->Prompts)
            if(Prompt.Beats.Contains(Beat)&&Prompt.On.StartsWith(Delayed)&&Prompt.On.EndsWith(TEXT("s"))) Due.Add(Prompt.On);
        for(const FString& Row:Due)
            if(!BeatEvents.Contains(Row)&&!Scheduled.ContainsByPredicate([&](const TPair<double,FString>& Entry) { return Entry.Value==Row; }))
                Scheduled.Emplace(GetWorld()->GetTimeSeconds()+FCString::Atod(*Row.Mid(Delayed.Len(),Row.Len()-Delayed.Len()-1)),Row);
    }
    // Allies that join with a wave step in as it comes.
    if(USoraFieldcraft* Fieldcraft=USoraFieldcraft::Get(this)) Fieldcraft->NoteBeatEvent(Event);
}
void USoraCampaignDirector::TickScheduled()
{
    if(Scheduled.IsEmpty()||!GetWorld()) return;
    const double Now=GetWorld()->GetTimeSeconds();
    TArray<FString> Due;
    for(int32 Index=Scheduled.Num()-1;Index>=0;--Index)
        if(Now>=Scheduled[Index].Key) { Due.Insert(Scheduled[Index].Value,0); Scheduled.RemoveAt(Index); }
    for(const FString& Event:Due) Fire(Event);
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
void USoraCampaignDirector::RaiseBeatEvent(FName Event)
{
    const FSoraBeat* Beat=ActiveBeatData();
    const FString Name=Event.ToString();
    if(!Beat||Mode().bChapterComplete||Mode().bDefeated||Name.IsEmpty()) return;
    const int32 Before=SoraBeatRules::ProgressPermille(TaskState,Task);
    Fire(Name);
    ReleaseEventWaves(Name);
    SoraBeatRules::EFail Failure=SoraBeatRules::EFail::PlayerDied;
    if(FailureOf(Name,Failure)&&!(Failure==SoraBeatRules::EFail::Detected&&bDetected))
    {
        bDetected|=Failure==SoraBeatRules::EFail::Detected;
        const unsigned ReleasedBefore=TaskState.Released;
        const SoraBeatRules::ERetry Outcome=SoraBeatRules::Fail(TaskState,Task,Failure);
        // Detection may call the zone's reinforcements.
        QueueWaves(TaskState.Released&~ReleasedBefore);
        HandleFailure(Outcome,Name);
        if(Outcome!=SoraBeatRules::ERetry::None&&Outcome!=SoraBeatRules::ERetry::Continue) return;
    }
    Progressed(Before);
}
void USoraCampaignDirector::ReleaseEventWaves(const FString& Event)
{
    const FSoraBeat* Beat=ActiveBeatData();
    if(!Beat) return;
    unsigned Fresh=0u;
    for(int32 Wave=0;Wave<Beat->Waves.Num();++Wave)
        if(Beat->Waves[Wave].Event==Event&&SoraBeatRules::ReleaseWave(TaskState,Task,Wave)) Fresh|=1u<<Wave;
    QueueWaves(Fresh);
}
bool USoraCampaignDirector::FailureOf(const FString& Event,SoraBeatRules::EFail& Failure) const
{
    using SoraBeatRules::EFail;
    const FSoraBeat* Beat=ActiveBeatData();
    if(!Beat) return false;
    // The beat's own `fail` rows first, then the failures every beat understands.
    if(const EFail* Row=Beat->FailEvents.Find(Event)) { Failure=*Row; return true; }
    if(Event.StartsWith(TEXT("npc_died:"))) Failure=EFail::EscortDown;
    else if(Event.StartsWith(TEXT("convoy_member_"))) Failure=EFail::ConvoyLost;
    else if(Event.StartsWith(TEXT("target_destroyed"))) Failure=EFail::TargetDestroyed;
    else if(Event==TEXT("horse_down")) Failure=EFail::HorseDown;
    else if(Event==TEXT("alert_state:alert")||Event==TEXT("alert_state:combat")) Failure=EFail::Detected;
    else return false;
    return true;
}
void USoraCampaignDirector::HandleFailure(SoraBeatRules::ERetry Outcome,const FString& Event)
{
    using SoraBeatRules::ERetry;
    ASoraGameMode& M=Mode();
    const FSoraBeat* Beat=ActiveBeatData();
    if(!Beat) return;
    switch(Outcome)
    {
    case ERetry::None:
        return;
    case ERetry::Continue:
        // A sparring bout lost is the rival's point; the match goes on.
        if(Event==TEXT("player_died"))
        {
            if(ASoraPlayerCharacter* Player=M.Hero()) Player->Heal(Player->MaxHealth);
            Fire(TEXT("point:rival"));
            Notify(FString::Printf(TEXT("一本取られた。%d 対 %d"),TaskState.Done,TaskState.RivalPoints),
                FString::Printf(TEXT("A point to your rival: %d to %d."),TaskState.Done,TaskState.RivalPoints),5.f);
        }
        Telemetry(TEXT("setback"));
        return;
    case ERetry::RetryBeat:
        RetryBeatInPlace();
        return;
    case ERetry::Advance:
        // The story moves on along the lost match's branch.
        Fire(TEXT("loss_continue"));
        Telemetry(TEXT("conceded"));
        CompleteActiveBeat();
        return;
    case ERetry::Checkpoint:
        break;
    }
    ResetPods();
    CancelFoundryWork();
    CancelHorseTreatment();
    CancelCopying();
    CancelBulkheadHold();
    M.bDefeated=true;
    ClearDialogue();
    const bool bFell=Event==TEXT("player_died");
    M.Notice=ChapterId==0?TEXT("立合いはここまで。Enter で稽古をやり直そう。")
        :bFell?TEXT("仲間は、あなたを待っている。Enter で最後の復旧記録から再開する。")
        :TEXT("守るべきものを失った。Enter で最後の復旧記録から再開する。");
    M.NoticeEnglish=ChapterId==0?TEXT("The sparring bout has ended. Press Enter to resume training.")
        :bFell?TEXT("The resistance remembers. Press Enter to retry from the latest checkpoint.")
        :TEXT("What you were protecting was lost. Press Enter to retry from the latest checkpoint.");
    if(auto* Events=USoraGameEvents::Get(this))
    {
        FSoraBeatEvent Failed;
        Failed.ChapterId=ChapterId; Failed.BeatIndex=BeatIndex; Failed.BeatId=Beat->Id; Failed.Phase=BeatPhase;
        Events->OnBeatFailed.Broadcast(Failed);
    }
    Telemetry(TEXT("failed"));
}
bool USoraCampaignDirector::DamageDefendedTarget(int32 Target,int32 Hp)
{
    const FSoraBeat* Beat=ActiveBeatData();
    if(!Beat||!Beat->Targets.IsValidIndex(Target)||Mode().bDefeated) return false;
    if(IsFoundryDefense()&&Target==1)
    {
        if(auto* Kozo=FoundryKozo())
        {
            SoraDamage::Strike(Kozo,Hp,FSoraHit::Hazard(Kozo->GetActorLocation()),FVector::ZeroVector,FHitResult(),nullptr,nullptr);
            TaskState.TargetHp[1]=FMath::RoundToInt32(Kozo->Health);
        }
        return false; // Downing starts the authored rescue deadline, not target destruction.
    }
    const int32 Full=Task.TargetHp[Target],Before=TaskState.TargetHp[Target];
    const bool bDestroyed=SoraBeatRules::DamageTarget(TaskState,Task,Target,Hp);
    const int32 After=TaskState.TargetHp[Target];
    // The person standing at a worn target is netted, and taken when it is lost.
    if(USoraFieldcraft* Fieldcraft=USoraFieldcraft::Get(this)) Fieldcraft->TargetChanged(Target,Full>0?After*1000/Full:0);
    // "target_hp_below:<actor or any>:<fraction>" lines as a target weakens.
    for(const FSoraDialogueTrigger& Trigger:ActiveChapter()->Triggers)
    {
        FString Actor,Fraction;
        if(Trigger.Beat!=BeatIndex||!Trigger.On.StartsWith(TEXT("target_hp_below:"))||
            !Trigger.On.RightChop(16).Split(TEXT(":"),&Actor,&Fraction)||(Actor!=TEXT("any")&&Actor!=Beat->Targets[Target]))
            continue;
        const int32 At=FMath::RoundToInt32(FCString::Atod(*Fraction)*1000.0);
        if(Before*1000>At*Full&&After*1000<=At*Full) Fire(Trigger.On);
    }
    if(IsFoundryDefense()) if(auto* Furnace=FoundryFurnace()) Furnace->Health=After;
    if(bDestroyed) RaiseBeatEvent(FName(TEXT("target_destroyed:")+Beat->Targets[Target]));
    return bDestroyed;
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
        if(!Beat->Is(SoraBeatRules::EType::Cinematic)) return nullptr;
        // Subtitles run on the cinematic's own clock.
        const int32 Ms=FMath::FloorToInt32(CinematicElapsed()*1000.f);
        for(const FSoraDialogueTrigger& Trigger:Chapter.Triggers)
            if(Trigger.Beat==BeatIndex&&Trigger.On==TEXT("subtitle")&&Ms>=Trigger.AtMs&&
                Ms<Trigger.AtMs+FMath::CeilToInt32(Chapter.Dialogue[Trigger.Lines[0]].DurationSeconds*1000.f))
                return &Chapter.Dialogue[Trigger.Lines[0]];
        return nullptr;
    }
    if(bArchiveReveal&&ArchiveRevealSeconds<SoraArchiveRules::SpeechStartSeconds) return nullptr;
    return !Queue.IsEmpty()?&Chapter.Dialogue[Queue[0].Line]:nullptr;
}
TArray<FSoraSubtitle> USoraCampaignDirector::QueuedSubtitles() const
{
    TArray<FSoraSubtitle> Result;
    const FSoraChapter* Chapter=ActiveChapter();
    if(!Chapter||!Mode().bCampaign) return Result;
    for(const FQueuedLine& Line:Queue)
    {
        const FSoraDialogueCue& Cue=Chapter->Dialogue[Line.Line];
        FSoraSubtitle& Row=Result.AddDefaulted_GetRef();
        Row.LineId=Cue.Id; Row.Japanese=Cue.Japanese; Row.English=Cue.English; Row.Seconds=Cue.DurationSeconds;
        if(const FSoraDialogueSpeaker* Speaker=FSoraCatalog::Get().DialogueSpeaker(Cue.SpeakerId))
        {
            Row.Speaker=Speaker->Japanese; Row.SpeakerEnglish=Speaker->English;
        }
    }
    return Result;
}
float USoraCampaignDirector::CinematicElapsed() const
{
    const FSoraBeat* Beat=ActiveBeatData();
    return Beat&&Beat->Is(SoraBeatRules::EType::Cinematic)?FMath::Max(0.f,Task.DurationMs/1000.f-Mode().TitleCardTime):0.f;
}
bool USoraCampaignDirector::ObjectiveAnchor(FVector& Location) const
{
    bool bInteract=false;
    return ObjectivePoint(Location,bInteract);
}
bool USoraCampaignDirector::AnchorTakesInteract() const
{
    FVector Location; bool bInteract=false;
    return ObjectivePoint(Location,bInteract)&&bInteract;
}
bool USoraCampaignDirector::HeroAtTask() const
{
    const FSoraBeatSpace* Space=ActiveSpace();
    if(!Space) return false;
    if(IsHelmHold()) return Mode().Hero()&&Mode().Hero()->GetCharacterMovement()->IsMovingOnGround()&&InHelmFloor(Mode().Hero()->GetActorLocation());
    if(Task.HoldPointCount>0) return IsCopying()&&AtCopyDesk(CopyDesk);
    if(Task.Goal==SoraBeatRules::EGoal::Hold) return Near(ASoraWorldBuilder::Floor(Space->Anchor),SoraCampaignReach::Hold);
    // The escorted party walks while the hero keeps up and all of it is free,
    // standing and in the open (SoraFieldcraftRules::PartyWalks).
    if(Task.Goal==SoraBeatRules::EGoal::Escort)
    {
        // A netted ox halts the cart until the net is cut.
        const USoraFieldcraft* Fieldcraft=USoraFieldcraft::Get(this);
        return Near(PartyLocation(),static_cast<float>(Task.WaitCm))&&(!Fieldcraft||(Fieldcraft->PartyReady()&&!Fieldcraft->QuarryHalted()));
    }
    return false;
}
bool USoraCampaignDirector::Contested() const
{
    if(Task.HoldPointCount>0) return CopyDeskContested();
    const FSoraBeatSpace* Space=ActiveSpace();
    if(Task.Goal!=SoraBeatRules::EGoal::Hold||!Space) return false;
    const FVector Anchor=ASoraWorldBuilder::Floor(Space->Anchor);
    for(const auto& Enemy:Enemies)
        if(IsValid(Enemy)&&Enemy->IsEnemy()&&Enemy->IsAlive()&&(IsHelmHold()?InHelmFloor(Enemy->GetActorLocation()):FVector::Dist2D(Enemy->GetActorLocation(),Anchor)<SoraCampaignReach::Contest)) return true;
    return false;
}
TArray<int32> USoraCampaignDirector::AvailableCaches() const
{
    TArray<int32> Result;
    const FSoraChapter* Chapter=ActiveChapter();
    if(!Chapter||!Mode().bCampaign||Mode().bChapterComplete) return Result;
    for(int32 Index=0;Index<Chapter->Beats.Num();++Index)
        if(Chapter->Beats[Index].Has(SoraBeatRules::EGoal::Cache)&&
            (Chapter->Beats[Index].Space.HeightCm==0||bLiftGallery)&&
            SoraBeatRules::CanStartBeat(BeatState,Chapter->Rules.GetData(),Chapter->Rules.Num(),Index))
            Result.Add(Index);
    return Result;
}
FVector USoraCampaignDirector::CacheLocation(int32 Beat) const
{
    const FSoraChapter* Chapter=ActiveChapter();
    return Chapter&&Chapter->Beats.IsValidIndex(Beat)?ASoraWorldBuilder::Floor(Chapter->Beats[Beat].Space.Cache,Chapter->Beats[Beat].Space.HeightCm):FVector::ZeroVector;
}
void USoraCampaignDirector::UpdateObjective()
{
    ASoraWorldBuilder* WorldBuilder=Mode().Arena();
    if(!WorldBuilder) return;
    FVector Anchor;
    WorldBuilder->ShowObjective(ObjectiveAnchor(Anchor)&&Mode().bCampaign?&Anchor:nullptr);
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
        EntryWeapons=BeatState.WeaponsMask; EntryMechanics=BeatState.MechanicsMask; EntryFlags=BeatState.FlagsMask;
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
    EntryWeapons=0u; EntryMechanics=0u; EntryFlags=0u; DojoLessonMask=0u;
    if(Save) { Save->HighestChapter=0; Save->Collectibles=0; Save->GalleryPoiMask=0; Save->WoodPoiMask=0; Save->GalleryArrowsClaimed=false; }
    ClearCheckpoint();
    SaveProgress();
}
void USoraCampaignDirector::ResumeSavedChapter()
{
    ChapterId=Save->CurrentChapter;
    EntryWeapons=static_cast<unsigned>(Save->ChapterEntryWeapons);
    EntryMechanics=static_cast<unsigned>(Save->ChapterEntryMechanics);
    EntryFlags=static_cast<unsigned>(Save->ChapterEntryFlags);
    bCampaignComplete=Save->CampaignComplete; Mode().MapId=FSoraCatalog::Get().Chapter(ChapterId).Map;
}
int32 USoraCampaignDirector::HighestChapter() const { return Save?FMath::Clamp(Save->HighestChapter,0,LastChapter):0; }
bool USoraCampaignDirector::SelectChapter(int32 Chapter)
{
    const FSoraCatalog& Catalog=FSoraCatalog::Get();
    if(!Save||!Catalog.IsReady()||Chapter<0||Chapter>HighestChapter()) return false;
    // Replaying reopens the story from that chapter with every unlock and
    // story flag the earlier chapters offer (bible §11), so a liberated
    // campaign fights its final chapter again rather than restoring the
    // liberated city.
    ChapterId=Chapter; bCampaignComplete=false; DojoLessonMask=0u;
    EntryWeapons=Catalog.EarlierWeapons(Chapter); EntryMechanics=Catalog.EarlierMechanics(Chapter); EntryFlags=Catalog.EarlierFlags(Chapter);
    Mode().MapId=Catalog.Chapter(ChapterId).Map;
    ClearCheckpoint();
    SaveProgress();
    return true;
}
bool USoraCampaignDirector::HasProgress() const
{
    // The dojo's opening checkpoint, with no beat done, is where New Campaign begins.
    return Save&&(Save->CurrentChapter>0||Save->HighestChapter>0||Save->CampaignComplete||Save->Collectibles!=0||Save->WoodPoiMask!=0||
        (Save->CheckpointChapter>=0&&Save->CheckpointBeatsMask!=0));
}
bool USoraCampaignDirector::SeedCheckpoint(USoraSaveGame& Target,int32 Chapter,int32 Beat,int32 Phase)
{
    const FSoraCatalog& Catalog=FSoraCatalog::Get();
    if(!Catalog.IsReady()||Chapter<0||Chapter>LastChapter) return false;
    const FSoraChapter& Data=Catalog.Chapter(Chapter);
    const unsigned Weapons=Catalog.EarlierWeapons(Chapter),Mechanics=Catalog.EarlierMechanics(Chapter),Flags=Catalog.EarlierFlags(Chapter);
    SoraBeatRules::FProgress State{0u,0u,Weapons,Mechanics,Flags,false};
    for(int32 Index=0;Index<Beat&&Index<Data.Rules.Num();++Index)
        if(!Data.Rules[Index].Optional&&!SoraBeatRules::CompleteBeat(State,Data.Rules.GetData(),Data.Rules.Num(),Index)) return false;
    if(!Data.Rules.IsValidIndex(Beat)||(Data.Rules[Beat].Optional&&Beat!=Data.Wood.Beat)||
        !SoraBeatRules::CheckpointValid(State,Data.Rules.GetData(),Data.Rules.Num(),Weapons,Mechanics,Flags,Beat,Phase)||
        !SoraBeatRules::TaskCheckpointValid(Data.Tasks[Beat],Phase))
        return false;
    Target.SaveSchema=USoraSaveGame::Schema;
    Target.CurrentChapter=Chapter; Target.HighestChapter=FMath::Max(Target.HighestChapter,Chapter);
    Target.CampaignComplete=false; Target.WoodJunction=false;
    Target.ChapterEntryWeapons=static_cast<int32>(Weapons); Target.ChapterEntryMechanics=static_cast<int32>(Mechanics);
    Target.ChapterEntryFlags=static_cast<int32>(Flags);
    Target.CheckpointChapter=Chapter; Target.CheckpointBeat=Beat; Target.CheckpointPhase=Phase;
    Target.CheckpointBeatsMask=static_cast<int32>(State.CompletedMask); Target.CheckpointSitesMask=static_cast<int32>(State.SitesMask);
    Target.CheckpointWeapons=static_cast<int32>(State.WeaponsMask); Target.CheckpointMechanics=static_cast<int32>(State.MechanicsMask);
    Target.CheckpointFlags=static_cast<int32>(State.FlagsMask);
    Target.CheckpointComplete=false;
    Target.CheckpointDojoLessonMask=Chapter==0?static_cast<int32>(LessonsTaught(Data,State.CompletedMask)):0;
    return true;
}
bool USoraCampaignDirector::IsWeaponUnlocked(int32 WeaponId) const
{
    // The training arena lends every arm; the campaign holds what it has
    // earned and what the beat in play hands over.
    const FSoraChapter* Chapter=ActiveChapter();
    const unsigned Held=Chapter&&ActiveBeatData()
        ?SoraBeatRules::InPlayWeapons(BeatState,Chapter->Rules.GetData(),Chapter->Rules.Num(),BeatIndex):BeatState.WeaponsMask;
    return WeaponId>=0&&WeaponId<SoraBeatRules::WeaponCount&&(!Mode().bCampaign||(Held&(1u<<WeaponId))!=0u);
}
bool USoraCampaignDirector::IsMechanicInPlay(FName Mechanic) const
{
    const FSoraChapter* Chapter=ActiveChapter();
    const int32 Bit=Chapter?FSoraCatalog::Get().Mechanics.Find(Mechanic.ToString()):INDEX_NONE;
    if(Bit==INDEX_NONE) return false;
    const unsigned Learned=ActiveBeatData()
        ?SoraBeatRules::InPlayMechanics(BeatState,Chapter->Rules.GetData(),Chapter->Rules.Num(),BeatIndex):BeatState.MechanicsMask;
    return (Learned&(1u<<Bit))!=0u;
}
bool USoraCampaignDirector::BeginSealCut(ASoraPlayerCharacter& Player)
{
    // The seal can be cut once the story teaches it (bible §12.1 seal_cut),
    // from the beat that teaches it on.
    if(!IsMechanicInPlay(TEXT("seal_cut"))||!GetWorld()) return false;
    ASoraEnemy* Nearest=nullptr;
    float Best=SoraCampaignReach::Interact;
    for(const auto& Enemy:Enemies)
        if(IsValid(Enemy)&&Enemy->CanCutSeal())
        {
            const float Distance=FVector::Dist2D(Enemy->GetActorLocation(),Player.GetActorLocation());
            if(Distance<Best) { Best=Distance; Nearest=Enemy; }
        }
    // Boss adds are deliberately outside the beat's enemy list. Only the
    // authored collateral core joins this held interaction; no new kill credit.
    for(TActorIterator<ASoraEnemy> It(GetWorld());It;++It)
        if(It->IsCollateralConstruct()&&It->Summoner()==CampaignBoss()&&It->CanReachConstructCore(Player))
        {
            const float Distance=FVector::Dist2D(It->GetActorLocation(),Player.GetActorLocation());
            if(Distance<Best) { Best=Distance; Nearest=*It; }
        }
    if(!Nearest) return false;
    SealTarget=Nearest; SealStartedAt=GetWorld()->GetTimeSeconds();
    if(Nearest->IsCollateralConstruct())
        Notify(TEXT("核の封印を断つ……そのまま押さえていよう。"),TEXT("Cutting the exposed core seal... hold for one second."),2.f);
    else Notify(TEXT("借財の封印を断つ……そのまま押さえていよう。"),TEXT("Cutting the debt seal... keep holding."),Nearest->SealCutHoldMs()/1000.f+1.f);
    return true;
}
void USoraCampaignDirector::CancelConstructCut()
{
    if(const auto* Target=SealTarget.Get();Target&&Target->IsCollateralConstruct()) SealTarget.Reset();
}
float USoraCampaignDirector::SealCutProgress() const
{
    const ASoraEnemy* Target=SealTarget.Get();
    if(!Target||!GetWorld()) return 0.f;
    return FMath::Clamp((GetWorld()->GetTimeSeconds()-SealStartedAt)*1000.f/FMath::Max(1,Target->SealCutHoldMs()),0.f,1.f);
}
void USoraCampaignDirector::TickSealCut()
{
    ASoraEnemy* Target=SealTarget.Get();
    if(!Target) { SealTarget.Reset(); return; }
    ASoraPlayerCharacter* Hero=Mode().Hero();
    const APlayerController* Controller=Hero?Cast<APlayerController>(Hero->GetController()):nullptr;
    // The cut holds only while Interact is held beside the conscript.
    bool bHeld=false;
    if(Controller)
        for(const FKey& Key:Hero->GetActionKeys(TEXT("Interact"))) bHeld|=Controller->IsInputKeyDown(Key);
    if(!bHeld||!Hero||!Target->CanCutSeal()||(Target->IsCollateralConstruct()&&!Target->CanReachConstructCore(*Hero))||FVector::Dist2D(Target->GetActorLocation(),Hero->GetActorLocation())>SoraCampaignReach::Interact+50.f)
    {
        SealTarget.Reset();
        return;
    }
    if(SealCutProgress()<1.f) return;
    SealTarget.Reset();
    if(!Target->CutSeal(Hero)) return;
    Fire(TEXT("seal_cut"));
    if(Target->IsCollateralConstruct())
        Notify(TEXT("担保の封印を断った。荷は解き放たれた。"),TEXT("The collateral seal is cut. The goods are released."),5.f);
    else Notify(TEXT("封印を断った。この者はもう借財に縛られない。"),TEXT("The seal is cut. No debt binds them now."),5.f);
}
bool USoraCampaignDirector::IsStoryFlagSet(FName Flag) const
{
    const int32 Bit=FSoraCatalog::Get().IsReady()?FSoraCatalog::Get().StoryFlags.Find(Flag.ToString()):INDEX_NONE;
    return Bit!=INDEX_NONE&&(BeatState.FlagsMask&(1u<<Bit))!=0u;
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
    if(InteractHorseTreatment(Player)||InteractFoundry(Player)) return;
    using SoraBeatRules::EStroke;
    ASoraGameMode& M=Mode();
    if(!M.bCampaign) { ArenaInteract(Player); return; }
    const FSoraBeat* Beat=ActiveBeatData();
    if(!Beat||M.bChapterComplete) return;
    if(InteractHelm(Player)) return;
    if(InteractCopyDesk(Player)) return;
    if(InteractWind(Player)) return;
    if(InteractEpilogue(Player)) return;
    if(InteractRecovery(Player)) return;
    if(InteractCarryGate(Player)) return;
    if(InteractSpine()) return;
    if(InteractBulkhead()) return;
    // A knocked-down conscript within reach: Interact held cuts its seal.
    if(BeginSealCut(Player)) return;
    if(InteractSupply(Player)) return;
    if(InteractWood(Player)||InteractGalleryPoi(Player)) return;
    const FSoraBeatSpace& Space=Beat->Space;
    IdleMs=0;
    const int32 Before=SoraBeatRules::ProgressPermille(TaskState,Task);
    const int32 DoneBefore=TaskState.Done;
    const float Reach=IsMounted()?SoraCampaignReach::Saddle:SoraCampaignReach::Interact;
    // The nearest of Points within reach that Usable allows, or INDEX_NONE.
    const auto NearestOf=[&](const TArray<FVector2D>& Points,TFunctionRef<bool(int32)> Usable)
    {
        int32 Best=INDEX_NONE; float BestDistance=Reach;
        for(int32 Index=0;Index<Points.Num();++Index)
        {
            const float Distance=FVector::Dist2D(Player.GetActorLocation(),ASoraWorldBuilder::Floor(Points[Index]));
            if(Distance<BestDistance&&Usable(Index)) { Best=Index; BestDistance=Distance; }
        }
        return Best;
    };
    const bool bAtAnchor=AtWorkAnchor(Reach);
    if(Task.Goal==SoraBeatRules::EGoal::Lines&&bAtAnchor&&!bLinesStarted&&Beat->LinesEvent.StartsWith(TEXT("interact:")))
    {
        StartLines(); Fire(Beat->LinesEvent);
        return;
    }
    bool bWorked=false;
    switch(Task.Goal)
    {
    case SoraBeatRules::EGoal::Objectives:
    {
        if(IsRelayRoom()) { bWorked=InteractRelay();break; }
        const int32 Objective=NearestOf(Space.Objectives,[&](int32 Index) { return (TaskState.PointsMask&(1u<<Index))==0u; });
        if(Space.PressHall.bEnabled&&Objective>=0&&
            (!USoraFieldcraft::Get(this)||!USoraFieldcraft::Get(this)->CanWorkPress(Objective))) return;
        // An objective with a hold (a charge planted, a relay node pulled) is
        // worked with Interact held; the hold fills in TickHeldWork.
        if(Beat->ObjectiveHoldMs.IsValidIndex(Objective)&&Beat->ObjectiveHoldMs[Objective]>0)
        {
            HeldWork=EHeldWork::Objective; HeldPoint=Objective; HeldMs=0;
            Fire(TEXT("interact_start:")+Beat->Objectives[Objective]);
            return;
        }
        bWorked=WorkObjectiveAt(Objective);
        break;
    }
    case SoraBeatRules::EGoal::Turns:
    {
        if(!bAtAnchor) break;
        bWorked=TurnPlayerCrank(true);
        if(!bWorked) return; // The wheel consumes refused attempts too.
        break;
    }
    case SoraBeatRules::EGoal::Deliveries:
        if(Task.Task==SoraBeatRules::ETask::Carry&&!TaskState.Carrying)
        {
            if((bWorked=TakeLooseLoad(Player))) break;
            // A store is revisited for every load; distinct goods are taken once each.
            const int32 Pickup=NearestOf(Space.Pickups,[&](int32 Index)
                { return Task.Pickups<Task.Count||(TaskState.PointsMask&(1u<<Index))==0u; });
            // A load hoisted at its pickup (ch03.b05's 釣瓶) is held for; the hold fills in TickHeldWork.
            if(Pickup!=INDEX_NONE&&Task.PickupHoldMs>0)
            {
                HeldWork=EHeldWork::Hoist; HeldPoint=Pickup; HeldMs=0;
                Fire(TEXT("hoist_start"));
                return;
            }
            bWorked=TakeLoad(Pickup);
        }
        else
        {
            const int32 Dropoff=NearestOf(Space.Dropoffs,[&](int32 Index)
                { return SoraBeatRules::DropoffHasRoom(TaskState,Task,Index); });
            if(Dropoff!=INDEX_NONE&&Task.UnloadHoldMs>0)
            {
                // A fresh press starts the whole unload. Release, including
                // release/repress between ticks, discards its partial time.
                HeldWork=EHeldWork::CargoUnload; HeldPoint=Dropoff; HeldMs=0;
                CargoClock.Reset();
                return;
            }
            bWorked=DeliverLoad(Dropoff);
            if(!bWorked&&Task.Task==SoraBeatRules::ETask::Carry) bWorked=SetDownLoad(Player);
        }
        break;
    case SoraBeatRules::EGoal::Steps:
    {
        // Each step is worked at its own station.
        const int32 Step=TaskState.Step;
        if(!Space.StepStations.IsValidIndex(Step)||
            !Near(ASoraWorldBuilder::Floor(Space.Stations[Space.StepStations[Step]]),Reach))
            break;
        if(SoraRhythmRules::Supported(TaskState,Task)) { WorkPlayerRhythm(); return; }
        const EStroke Struck=SoraBeatRules::Stroke(TaskState,Task);
        bWorked=Struck!=EStroke::Refused;
        if(Struck==EStroke::Missed)
        {
            Fire(TEXT("step_failed:")+Beat->StepKinds[Step]);
            Notify(TEXT("調子が外れた。拍に合わせて、もう一度。"),TEXT("Off the beat. Find the rhythm and strike again."),3.f);
        }
        else if(bWorked)
            Fire(FString::Printf(TEXT("step_complete:%s:%d"),*Beat->StepKinds[Step],Struck==EStroke::Counted?TaskState.StepDone:Task.Steps[Step].Count));
        if(Struck==EStroke::StepDone) Fire(TEXT("step_start:")+Beat->StepKinds[TaskState.Step]);
        if(Struck==EStroke::Finished) Fire(TEXT("output_complete"));
        break;
    }
    case SoraBeatRules::EGoal::Survive:
    {
        // A repair at the defended position or a target: the worst-hit target
        // standing regains a quarter of its health.
        if(!bAtAnchor&&NearestOf(Space.Targets,[](int32) { return true; })==INDEX_NONE) break;
        int32 Worst=INDEX_NONE;
        for(int32 Target=0;Target<Task.TargetCount;++Target)
            if(TaskState.TargetHp[Target]>0&&TaskState.TargetHp[Target]<Task.TargetHp[Target]&&
                (Worst==INDEX_NONE||TaskState.TargetHp[Target]*Task.TargetHp[Worst]<TaskState.TargetHp[Worst]*Task.TargetHp[Target]))
                Worst=Target;
        bWorked=Worst!=INDEX_NONE&&SoraBeatRules::RepairTarget(TaskState,Task,Worst,FMath::Max(1,Task.TargetHp[Worst]/4));
        // Mended past half, a netted person's net is cut.
        if(bWorked)
            if(USoraFieldcraft* Fieldcraft=USoraFieldcraft::Get(this))
                Fieldcraft->TargetChanged(Worst,TaskState.TargetHp[Worst]*1000/FMath::Max(1,Task.TargetHp[Worst]));
        break;
    }
    case SoraBeatRules::EGoal::OpponentDown:
        // Both authored captures consume Interact above. The yielded body
        // has no instant interaction that can bypass either held ending.
        break;
    default:
        break;
    }
    if(bWorked)
    {
        if(DoneBefore==0&&TaskState.Done>0) Fire(TEXT("interact_start"));
        UpdateObjective();
        Progressed(Before);
        return;
    }
    // A loose collectible or an explore cache within reach, else the horse
    // (tack-up, mount, dismount).
    if(PickUp()) return;
    for(const int32 Cache:AvailableCaches())
        if((Space.HeightCm>0||ActiveChapter()->Beats[Cache].Space.HeightCm>0)?
            NearFloor(CacheLocation(Cache),SoraCampaignReach::Interact):Near(CacheLocation(Cache),SoraCampaignReach::Interact))
        {
            // The cache's own task: opened, it completes its explore beat.
            SoraBeatRules::FTaskState Opened=SoraBeatRules::StartTask(ActiveChapter()->Tasks[Cache],0);
            if(SoraBeatRules::OpenCache(Opened,ActiveChapter()->Tasks[Cache])&&
                SoraBeatRules::TaskComplete(Opened,ActiveChapter()->Tasks[Cache]))
                CompleteOptional(Cache);
            return;
        }
    InteractSpace(Player);
}
void USoraCampaignDirector::OpponentDefeated(ASoraEnemy* Opponent)
{
    using SoraBeatRules::EPoint;
    ASoraGameMode& M=Mode();
    if(M.bDeterministicPractice) return;
    if(!M.bCampaign)
    {
        SoraCampaignRules::FArena Arena{Kills,static_cast<unsigned>(ArenaSitesMask),bArenaComplete};
        if(!SoraCampaignRules::RecordArenaDefeat(Arena)) return;
        Kills=Arena.Kills;
        if(ASoraPlayerCharacter* Player=M.Hero()) Player->Heal(8.f);
        if(Spawned<SoraCampaignRules::ArenaDefeats) SpawnArenaInvader();
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
    const int32 Before=SoraBeatRules::ProgressPermille(TaskState,Task);
    const int32* Wave=EnemyWaves.Find(TWeakObjectPtr<const ASoraEnemy>(Opponent));
    if(Wave&&*Wave!=INDEX_NONE) SoraBeatRules::RecordDefeat(TaskState,Task,*Wave);
    else if(Task.Goal==SoraBeatRules::EGoal::Points||Task.Goal==SoraBeatRules::EGoal::Lessons)
    {
        // A bout to the hero: the rival yields and, until the match is won, comes back.
        const EPoint Point=SoraBeatRules::ScorePoint(TaskState,Task,true);
        const bool bLesson=Task.Goal==SoraBeatRules::EGoal::Lessons;
        if(Point==EPoint::Scored||Point==EPoint::Won)
        {
            // A dojo knockdown without the required flank is not a scored
            // point and cannot grant the passive taught by the recovery form.
            if(CanScoreDojoBout()&&M.Hero()) M.Hero()->GetEquipment()->NoteDefeat();
            // Lesson bouts are numbered across the dojo (ch01.b04 scores bouts 3 and 4).
            Fire(FString::Printf(TEXT("bout_scored:%d"),(bLesson?BoutOffset:0)+TaskState.Done));
            Fire(TEXT("point:player"));
        }
        // A 転 lesson's bout won without the flank does not score; the
        // master's hint plays and a fresh pupil steps in.
        if(Point==EPoint::Refused&&bLesson&&Task.FlankBouts) Fire(TEXT("marobashi_miss"));
        if(Point==EPoint::Won) Fire(TEXT("duel_won"));
        else if(Point==EPoint::Scored||(Point==EPoint::Refused&&bLesson))
        {
            if(ASoraEnemy* Next=SpawnDuelOpponent(Beat->Opponent,Beat->bSparring,Spawned)) AddOpponent(Next,INDEX_NONE);
            if(Point==EPoint::Scored&&bLesson) OpenBout();
        }
    }
    else if(Task.Goal==SoraBeatRules::EGoal::OpponentDown)
    {
        const bool bBoss=Beat->Is(SoraBeatRules::EType::Boss);
        const int32 PhaseBefore=TaskState.Phase;
        SoraBeatRules::OpponentHealth(TaskState,Task,0);
        // The phases a killing blow passes through still play, but save nothing.
        EnterPhases(PhaseBefore,false);
        Fire(bBoss?TEXT("boss_defeated"):TEXT("duel_won"));
        if(SoraBeatRules::AwaitsCapture(TaskState,Task))
        {
            // A yielded boss persists while the hero completes its held ending.
            Captive=Opponent;
            if(IsSpineCapture()) BeginSpineCapture();
            else if(IsBulkheadCapture()) BeginBulkheadCapture();
            UpdateObjective();
        }
        else if(bBoss) Fire(TEXT("outro_cinematic"));
    }
    // A fallen opponent's wave and fear entries leave with it.
    EnemyWaves.Remove(TWeakObjectPtr<const ASoraEnemy>(Opponent));
    Frightening.Remove(TWeakObjectPtr<const ASoraEnemy>(Opponent));
    Progressed(Before);
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
    if(!M.bCampaign||ChapterId!=0||!M.IsPlaying()||!Beat||Task.Goal!=SoraBeatRules::EGoal::Lessons||
        (Task.LessonMask&(1u<<static_cast<int32>(Action)))==0u) return false;
    SoraDojoRules::FProgress Lessons{DojoLessonMask};
    const int32 Form=static_cast<int32>(Action);
    if(!SoraDojoRules::Record(Lessons,Action,DurationMs,bFacingAttacker,RecoveryMs))
    {
        // A cut met with a guard raised long before it is an awase too early.
        if(Action==SoraDojoRules::EAction::Parry&&bFacingAttacker&&DurationMs>SoraDojoRules::ParryWindowMs&&
            DojoLessonStage()==Form)
            Fire(TEXT("awase_fail:early"));
        return false;
    }
    // A form the lesson wants repeated (awase ×2) is learned on its last
    // clean repetition; each awase met is named.
    const bool bLearned=SoraBeatRules::RepeatForm(TaskState,Task,Form);
    LateHitAt=-1.0;
    if(Action==SoraDojoRules::EAction::Parry) Fire(FString::Printf(TEXT("awase_success:%d"),TaskState.FormReps[Form]));
    if(!bLearned)
    {
        Notify(FString::Printf(TEXT("よし。あと %d 回。"),Task.FormReps[Form]-TaskState.FormReps[Form]),
            FString::Printf(TEXT("Good. %d more."),Task.FormReps[Form]-TaskState.FormReps[Form]),4.f);
        UpdateObjective();
        return true;
    }
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
    if(Task.Maai.Count==0) Notify(Japanese[Completed],English[Completed],8.f);
    const int32 Before=SoraBeatRules::ProgressPermille(TaskState,Task);
    SoraBeatRules::RecordForms(TaskState,Task,DojoLessonMask);
    Fire(FString(TEXT("gate_complete:"))+LessonGates[Completed]);
    if(MaaiReady())
    {
        Fire(TEXT("gate_start:maai_step"));
        Notify(DojoLessonText(false),DojoLessonText(true),8.f);
    }
    // The lesson's next gate, or its first bout once every form is learned.
    for(int32 Next=Completed+1;Next<4;++Next)
        if((Task.LessonMask&(1u<<Next))!=0u)
        {
            Fire(FString(TEXT("gate_start:"))+LessonGates[Next]);
            break;
        }
    if((TaskState.Forms&Task.LessonMask)==Task.LessonMask) OpenBout();
    Progressed(Before);
    return true;
}
void USoraCampaignDirector::OpenBout()
{
    if(Task.Goal==SoraBeatRules::EGoal::Lessons&&TaskState.Done<Task.Count)
        Fire(FString::Printf(TEXT("bout_start:%d"),BoutOffset+TaskState.Done+1));
}
void USoraCampaignDirector::PlayerKilled()
{
    ASoraGameMode& M=Mode();
    if(M.bDeterministicPractice) return;
    if(M.bCampaign&&ActiveBeatData()&&!M.bChapterComplete)
    {
        // The beat decides: a sparring point to the rival, a lesson or match
        // retried in place, the story moving on, or the latest checkpoint.
        Fire(TEXT("player_died"));
        HandleFailure(SoraBeatRules::Fail(TaskState,Task,SoraBeatRules::EFail::PlayerDied),TEXT("player_died"));
        return;
    }
    M.bDefeated=true;
    ClearDialogue();
    M.Notice=TEXT("仲間は、あなたを待っている。Enter で最後の復旧記録から再開する。");
    M.NoticeEnglish=TEXT("The resistance remembers. Press Enter to retry from the latest checkpoint.");
}
void USoraCampaignDirector::Notify(const FString& Japanese,const FString& English,float Seconds)
{
    ASoraGameMode& M=Mode();
    M.Notice=Japanese; M.NoticeEnglish=English; M.NoticeTime=Seconds;
}
void USoraCampaignDirector::Notify(const SoraText::FLine& Line,float Seconds)
{
    Notify(Line.Japanese,Line.English,Seconds);
}
void USoraCampaignDirector::BroadcastBeat(bool bStarted,bool bResumed)
{
    const FSoraBeat* Beat=ActiveBeatData();
    USoraGameEvents* Events=USoraGameEvents::Get(this);
    if(!Beat||!Events) return;
    FSoraBeatEvent Event;
    Event.bOptional=ActiveChapter()->Rules[BeatIndex].Optional;
    Event.ChapterId=ChapterId; Event.BeatIndex=BeatIndex; Event.BeatId=Beat->Id; Event.bResumed=bResumed; Event.Phase=BeatPhase;
    (bStarted?Events->OnBeatStarted:Events->OnBeatCompleted).Broadcast(Event);
}
void USoraCampaignDirector::Telemetry(const TCHAR* Event,int32 Beat) const
{
    // Per-beat timestamps and task progress for pacing playtests (bible §10),
    // one JSON object per line. A cache opened beside the active beat writes
    // its own optional beat's row, complete at once.
    const ASoraGameMode& M=Mode();
    const FSoraChapter* Chapter=ActiveChapter();
    if(!Chapter) return;
    const bool bActive=Beat==INDEX_NONE||Beat==BeatIndex;
    if(bActive) Beat=BeatIndex;
    const FString BeatId=Chapter->Beats.IsValidIndex(Beat)?Chapter->Beats[Beat].Id:FString();
    const FString Line=FString::Printf(TEXT("{\"utc\":\"%s\",\"slot\":\"%s\",\"chapter\":\"%s\",\"beat\":\"%s\",\"event\":\"%s\",\"phase\":%d,")
        TEXT("\"beat_ms\":%d,\"progress_permille\":%d,\"done\":%d,\"losses\":%d,\"round_s\":%.2f,\"world_s\":%.2f}\n"),
        *FDateTime::UtcNow().ToIso8601(),*M.SaveSlotName,*Chapter->Id,*BeatId,Event,bActive?BeatPhase:0,
        bActive?TaskState.ElapsedMs:0,bActive?SoraBeatRules::ProgressPermille(TaskState,Task):SoraBeatRules::Permille,
        bActive?TaskState.Done:1,bActive?TaskState.Losses:0,M.RoundTime,GetWorld()?GetWorld()->GetTimeSeconds():0.0);
    FFileHelper::SaveStringToFile(Line,*(FPaths::ProjectSavedDir()/TEXT("Telemetry/campaign_beats.jsonl")),
        FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM,&IFileManager::Get(),FILEWRITE_Append);
}
void USoraCampaignDirector::SaveCheckpoint(int32 AtBeat)
{
    ASoraGameMode& M=Mode();
    if(!M.bCampaign||!Save) return;
    Save->CheckpointChapter=ChapterId;
    Save->CheckpointBeat=BeatState.Complete?INDEX_NONE:AtBeat==INDEX_NONE?BeatIndex:AtBeat;
    Save->CheckpointPhase=BeatState.Complete||AtBeat!=INDEX_NONE?0:BeatPhase;
    Save->CheckpointBeatsMask=static_cast<int32>(BeatState.CompletedMask);
    Save->CheckpointSitesMask=static_cast<int32>(BeatState.SitesMask);
    Save->CheckpointWeapons=static_cast<int32>(BeatState.WeaponsMask);
    Save->CheckpointMechanics=static_cast<int32>(BeatState.MechanicsMask);
    Save->CheckpointFlags=static_cast<int32>(BeatState.FlagsMask);
    Save->CheckpointComplete=BeatState.Complete;
    // The forms the completed lesson duels taught: a checkpoint restores the
    // active beat from its start, before any form it teaches.
    Save->CheckpointDojoLessonMask=ChapterId==0?static_cast<int32>(LessonsTaught(*ActiveChapter(),BeatState.CompletedMask)):0;
    SaveProgress();
}
bool USoraCampaignDirector::CanCheckpointHere() const
{
    const FSoraChapter* Chapter=ActiveChapter();
    return Chapter&&Mode().bCampaign&&!BeatState.Complete&&PendingArchivePhaseSave==INDEX_NONE&&Chapter->Rules.IsValidIndex(BeatIndex)&&
        SoraBeatRules::CheckpointValid(BeatState,Chapter->Rules.GetData(),Chapter->Rules.Num(),EntryWeapons,EntryMechanics,
            EntryFlags,BeatIndex,BeatPhase)&&
        SoraBeatRules::TaskCheckpointValid(Chapter->Tasks[BeatIndex],BeatPhase);
}
void USoraCampaignDirector::ClearCheckpoint()
{
    if(!Save) return;
    Save->WoodJunction=false;
    Save->CheckpointChapter=-1; Save->CheckpointBeat=-1; Save->CheckpointPhase=0;
    Save->CheckpointBeatsMask=0; Save->CheckpointSitesMask=0; Save->CheckpointWeapons=0; Save->CheckpointMechanics=0;
    Save->CheckpointFlags=0; Save->CheckpointComplete=false; Save->CheckpointDojoLessonMask=0;
}
void USoraCampaignDirector::SaveProgress()
{
    if(!Save) return;
    ASoraGameMode& M=Mode();
    Save->SaveSchema=USoraSaveGame::Schema;
    Save->CurrentChapter=ChapterId; Save->SelectedClass=M.SelectedClass; Save->CampaignComplete=bCampaignComplete;
    Save->EnglishSubtitles=M.bEnglishSubtitles;
    Save->ChapterEntryWeapons=static_cast<int32>(EntryWeapons); Save->ChapterEntryMechanics=static_cast<int32>(EntryMechanics);
    Save->ChapterEntryFlags=static_cast<int32>(EntryFlags);
    if(!UGameplayStatics::SaveGameToSlot(Save,M.SaveSlotName,0))
        Notify(TEXT("進行を保存できませんでした。今回の起動中は続けられます。"),TEXT("Unable to write campaign save. Progress remains available this session."),6.f);
}
void USoraCampaignDirector::ClearOfflineProjectiles()
{
    WoodShots.Reset();
    ClearArchery();
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
    if(bWoodTransit) return TEXT("林を散策するか、南の道から鍛冶場へ進む");
    if(IsToriiEpilogue()) return EpilogueObjectiveText(false);
    if(IsArcheryLesson()) return ArcheryText(false);
    if(IsHorseTreatment()) return HorseTreatmentText(false);
    if(IsFoundryDefense()) return FoundryText(false);
    if(IsHelmHold()) return HelmText(false);
    if(Task.HoldPointCount>0) return CopyDeskText(false);
    if(IsBulkheadCapture()&&AwaitingCapture()) return BulkheadText().Japanese;
    if(NeedsCarryGate()) return TEXT("蔵の封印で操作を長押しし、槍の石突でこじ開ける");
    if(NeedsEquipmentRecovery()) return AtRecoveryBottom()?TEXT("包みの前で操作を 3 秒長押しし、弓に弦を張る"):
        TEXT("空井戸の縄で操作を長押しし、底の刀の包みを取り戻す");
    if(IsClimbingRecoveryWell()||(Task.RecoveryWeapons!=0u&&AtRecoveryBottom())) return TEXT("縄で操作を長押しし、井戸から上がる");
    if(ChapterId==0&&Task.Goal==SoraBeatRules::EGoal::Lessons&&(DojoLessonMask&Task.LessonMask)!=Task.LessonMask)
        return FString::Printf(TEXT("%s  |  猫柳生新陰流  型 %d / 4"),*Beat->Title,DojoLessonStage()+1);
    const SoraBeatRules::FTaskState& S=TaskState;
    const int32 Percent=SoraBeatRules::ProgressPermille(S,Task)/10;
    FString Progress;
    switch(Task.Goal)
    {
    case SoraBeatRules::EGoal::WavesCleared: Progress=FString::Printf(TEXT("侵略者 %d / %d"),SoraBeatRules::Defeated(S,Task),SoraBeatRules::TotalLethal(Task)); break;
    case SoraBeatRules::EGoal::Objectives: Progress=FString::Printf(TEXT("目標 %d / %d"),S.Done,Task.Count); break;
    case SoraBeatRules::EGoal::Survive: Progress=FString::Printf(TEXT("持ちこたえる 残り %d 秒"),FMath::DivideAndRoundUp(Task.DurationMs-S.Progress,1000)); break;
    case SoraBeatRules::EGoal::Points: Progress=FString::Printf(TEXT("一本 %d 対 %d"),S.Done,S.RivalPoints); break;
    case SoraBeatRules::EGoal::Lessons: if(Task.Count>0) Progress=FString::Printf(TEXT("立合い %d / %d"),S.Done,Task.Count); break;
    case SoraBeatRules::EGoal::Exit: Progress=Beat->Is(SoraBeatRules::EType::HorsebackRide)?TEXT("目的地へ"):TEXT("出口へ"); break;
    case SoraBeatRules::EGoal::Hold: Progress=FString::Printf(TEXT("持ちこたえる %d / %d 秒"),S.Progress/1000,FMath::DivideAndRoundUp(Task.DurationMs,1000)); break;
    case SoraBeatRules::EGoal::Turns: Progress=FString::Printf(TEXT("回す %d / %d"),S.Done,Task.Count); break;
    case SoraBeatRules::EGoal::Escort: Progress=FString::Printf(TEXT("護衛 %d%%"),Percent); break;
    case SoraBeatRules::EGoal::Deliveries:
        Progress=Beat->Cargo.Total>0
            ?FString::Printf(TEXT("麦 残り %d束（配達 %d / %d）"),SoraCargoRules::Remaining(Beat->Cargo,Task.Count,S.Done),S.Done,Task.Count)
            :FString::Printf(TEXT("運ぶ %d / %d%s"),S.Done,Task.Count,S.Carrying?TEXT("（運搬中）"):TEXT(""));
        break;
    case SoraBeatRules::EGoal::Steps: Progress=FString::Printf(TEXT("工程 %d / %d"),FMath::Min(S.Step+1,Task.StepCount),Task.StepCount); break;
    case SoraBeatRules::EGoal::OpponentDown: if(SoraBeatRules::AwaitsCapture(S,Task)) Progress=TEXT("捕らえる"); break;
    default: break;
    }
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
    if(bWoodTransit) return TEXT("Explore the wood, or take the south terrace to the smithy");
    if(IsToriiEpilogue()) return EpilogueObjectiveText(true);
    if(IsArcheryLesson()) return ArcheryText(true);
    if(IsHorseTreatment()) return HorseTreatmentText(true);
    if(IsFoundryDefense()) return FoundryText(true);
    if(IsHelmHold()) return HelmText(true);
    if(Task.HoldPointCount>0) return CopyDeskText(true);
    if(IsBulkheadCapture()&&AwaitingCapture()) return BulkheadText().English;
    if(NeedsCarryGate()) return TEXT("Hold Interact at the granary seal to pry it off with the spear butt");
    if(NeedsEquipmentRecovery()) return AtRecoveryBottom()?TEXT("Hold Interact at the bundle for 3 seconds to string the bow"):
        TEXT("Hold Interact at the dry-well rope to recover the sword bundle below");
    if(IsClimbingRecoveryWell()||(Task.RecoveryWeapons!=0u&&AtRecoveryBottom())) return TEXT("Hold Interact on the rope to climb out");
    if(ChapterId==0&&Task.Goal==SoraBeatRules::EGoal::Lessons&&(DojoLessonMask&Task.LessonMask)!=Task.LessonMask)
        return FString::Printf(TEXT("%s / Nyaagyushinkageryuu form %d of 4"),*Beat->TitleEnglish,DojoLessonStage()+1);
    const SoraBeatRules::FTaskState& S=TaskState;
    const int32 Percent=SoraBeatRules::ProgressPermille(S,Task)/10;
    FString Progress;
    switch(Task.Goal)
    {
    case SoraBeatRules::EGoal::WavesCleared: Progress=FString::Printf(TEXT("Invaders %d of %d"),SoraBeatRules::Defeated(S,Task),SoraBeatRules::TotalLethal(Task)); break;
    case SoraBeatRules::EGoal::Objectives: Progress=FString::Printf(TEXT("Objectives %d of %d"),S.Done,Task.Count); break;
    case SoraBeatRules::EGoal::Survive: Progress=FString::Printf(TEXT("Hold out %d s"),FMath::DivideAndRoundUp(Task.DurationMs-S.Progress,1000)); break;
    case SoraBeatRules::EGoal::Points: Progress=FString::Printf(TEXT("Points %d to %d"),S.Done,S.RivalPoints); break;
    case SoraBeatRules::EGoal::Lessons: if(Task.Count>0) Progress=FString::Printf(TEXT("Bouts %d of %d"),S.Done,Task.Count); break;
    case SoraBeatRules::EGoal::Exit: Progress=Beat->Is(SoraBeatRules::EType::HorsebackRide)?TEXT("Ride to the destination"):TEXT("Reach the exit"); break;
    case SoraBeatRules::EGoal::Hold: Progress=FString::Printf(TEXT("Hold %d of %d s"),S.Progress/1000,FMath::DivideAndRoundUp(Task.DurationMs,1000)); break;
    case SoraBeatRules::EGoal::Turns: Progress=FString::Printf(TEXT("Turns %d of %d"),S.Done,Task.Count); break;
    case SoraBeatRules::EGoal::Escort: Progress=FString::Printf(TEXT("Escort %d%%"),Percent); break;
    case SoraBeatRules::EGoal::Deliveries:
        Progress=Beat->Cargo.Total>0
            ?FString::Printf(TEXT("Barley: %d sheaves left / Delivered %d of %d"),SoraCargoRules::Remaining(Beat->Cargo,Task.Count,S.Done),S.Done,Task.Count)
            :FString::Printf(TEXT("Delivered %d of %d%s"),S.Done,Task.Count,S.Carrying?TEXT(" (carrying)"):TEXT(""));
        break;
    case SoraBeatRules::EGoal::Steps: Progress=FString::Printf(TEXT("Step %d of %d"),FMath::Min(S.Step+1,Task.StepCount),Task.StepCount); break;
    case SoraBeatRules::EGoal::OpponentDown: if(SoraBeatRules::AwaitsCapture(S,Task)) Progress=TEXT("Capture"); break;
    default: break;
    }
    return Progress.IsEmpty()?Beat->TitleEnglish:Beat->TitleEnglish+TEXT(" / ")+Progress;
}
FString USoraCampaignDirector::DojoLessonText(bool bEnglish) const
{
    if(!Mode().bCampaign||ChapterId!=0||DojoLessonStage()>=4) return FString();
    if(MaaiReady())
    {
        const SoraText::FLine Line=SoraText::Format(NSLOCTEXT("SoraArena.Campaign","MaaiLesson",
            "間合い：師に向き、水月の輪を 0.5 秒保つ。{Done} / {Count} 歩"),
            {{TEXT("Done"),TaskState.Maai.Done},{TEXT("Count"),Task.Maai.Count}});
        return bEnglish?Line.English:Line.Japanese;
    }
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
