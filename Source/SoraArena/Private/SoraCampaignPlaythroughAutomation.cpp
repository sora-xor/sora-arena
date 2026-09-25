#include "SoraGameMode.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "SoraAutomationWorld.h"
#include "SoraBoss.h"
#include "SoraCampaignDirector.h"
#include "SoraCampaignRules.h"
#include "SoraCatalog.h"
#include "SoraDojoRules.h"
#include "SoraEnemy.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameEvents.h"
#include "SoraInputStates.h"
#include "SoraPlayerCharacter.h"
#include "SoraSaveGame.h"
#include "SoraWorldBuilder.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/DamageType.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/AutomationTest.h"
#include "Templates/UniquePtr.h"

// Plays all eight chapters' schema-4 beats in real game worlds through the
// entry points the player's input reaches: BeginRound (Enter) opens chapters,
// skips cinematics and continues results; Interact (E) works each beat's
// anchor and opens explore caches; the hero walks (is placed) onto anchors;
// lethal damage reaches OpponentDefeated; and the dojo forms are recorded.
// The disk save is read back at every checkpoint beat. Three checkpoints (one
// a boss phase) are restored in fresh worlds, a defeat is retried, locked
// weapons are refused, chapters one to five open every cache while six to
// eight skip them, and the campaign ends liberated with all 21 weapons.
// Combat balance is not under test here (see SoraArena.Campaign.CombatTrace):
// the hero is healed between actions so a long wave cannot end the run.
namespace SoraCampaignPlaythrough
{
constexpr int32 LastChapter = 7;
constexpr float FrameSeconds = 1.f / 60.f;
// Seconds per frame while no opponent stands: dialogue, holds and journeys.
constexpr float FastSeconds = .5f;
constexpr int32 MaxActionsPerBeat = 1000;
constexpr int32 CompletistChapters = 5;

struct FState
{
    FString Slot = FSoraAutomationWorld::UniqueSaveSlot(TEXT("CampaignPlaythrough"));
    TUniquePtr<FSoraAutomationWorld> World;
    bool bAborted = false;
    int32 WorldsStarted = 0;
    int32 ChaptersCompleted = 0;
    int32 BeatsPlayed = 0;
    int32 CachesOpened = 0;
    int32 CheckpointsRead = 0;
    int32 LinesShown = 0;
    ~FState()
    {
        World.Reset();
        FSoraAutomationWorld::DeleteSaveSlot(Slot);
    }
};
using FStateRef = TSharedRef<FState>;

bool Fail(FAutomationTestBase& Test, FState& State, const FString& Message)
{
    Test.AddError(Message);
    State.bAborted = true;
    return false;
}

ASoraGameMode* Mode(const FState& State) { return State.World ? State.World->Mode() : nullptr; }
ASoraPlayerCharacter* Player(const FState& State) { return State.World ? State.World->Player() : nullptr; }
USoraCampaignDirector* Campaign(const FState& State) { return Mode(State) ? Mode(State)->Campaign() : nullptr; }
const FSoraChapter& ChapterData(const FState& State) { return FSoraCatalog::Get().Chapter(Campaign(State)->ChapterId); }

TArray<ASoraEnemy*> LiveEnemies(const FState& State)
{
    TArray<ASoraEnemy*> Result;
    if (UWorld* World = State.World ? State.World->GetTestWorld() : nullptr)
        for (TActorIterator<ASoraEnemy> It(World); It; ++It)
            if (It->IsEnemy() && It->IsAlive() && !It->IsActorBeingDestroyed())
                Result.Add(*It);
    return Result;
}

bool HasJapanese(const FString& Text)
{
    for (const TCHAR Character : Text)
        if (Character >= 0x3040 && Character <= 0x9FFF)
            return true;
    return false;
}

bool Paused(const FState& State)
{
    const UWorld* World = State.World ? State.World->GetTestWorld() : nullptr;
    return World && World->IsPaused();
}

FString Where(const FState& State)
{
    const USoraCampaignDirector* Director = Campaign(State);
    const FSoraBeat* Beat = Director ? Director->ActiveBeatData() : nullptr;
    return FString::Printf(TEXT("Chapter %d %s"), Director ? Director->ChapterId + 1 : 0, Beat ? *Beat->Id : TEXT("(no beat)"));
}

bool Advance(FAutomationTestBase& Test, FState& State, int32 Frames = 2, float DeltaSeconds = FrameSeconds)
{
    for (int32 Frame = 0; Frame < Frames; ++Frame)
    {
        if (!State.World->Tick(1, DeltaSeconds))
        {
            State.World->ForwardErrorMessages(&Test);
            return Fail(Test, State, TEXT("Campaign world failed to tick"));
        }
        ASoraPlayerCharacter* Hero = Player(State);
        if (!Mode(State) || !Hero)
            return Fail(Test, State, TEXT("Campaign world lost its game mode or player"));
        if (Mode(State)->bDefeated)
            return Fail(Test, State, Where(State) + TEXT(": the hero was defeated unexpectedly"));
        if (Hero->Health < Hero->MaxHealth * .5f)
            Hero->Heal(Hero->MaxHealth);
    }
    return true;
}

void MoveTo(FState& State, const FVector& Location)
{
    ASoraPlayerCharacter* Hero = Player(State);
    Hero->GetCharacterMovement()->StopMovementImmediately();
    Hero->SetActorLocation(FVector(Location.X, Location.Y, Hero->GetActorLocation().Z), false, nullptr, ETeleportType::TeleportPhysics);
}

// Every checkpoint beat writes the slot as it starts; read it back from disk.
bool ExpectCheckpoint(FAutomationTestBase& Test, FState& State)
{
    const USoraCampaignDirector* Director = Campaign(State);
    const USoraSaveGame* Saved = Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(State.Slot, 0));
    const FString Context = Where(State) + TEXT(" checkpoint");
    if (!Test.TestNotNull(*(Context + TEXT(": written to the isolated slot")), Saved))
        return Fail(Test, State, Context + TEXT(": no saved checkpoint"));
    const SoraBeatRules::FProgress& Progress = Director->Progress();
    const int32 Lessons = Director->ChapterId == 0 ? (1 << Director->DojoLessonStage()) - 1 : 0;
    bool bOk = Test.TestEqual(*(Context + TEXT(": schema")), Saved->SaveSchema, USoraSaveGame::Schema);
    bOk &= Test.TestEqual(*(Context + TEXT(": current chapter")), Saved->CurrentChapter, Director->ChapterId);
    bOk &= Test.TestEqual(*(Context + TEXT(": checkpoint chapter")), Saved->CheckpointChapter, Director->ChapterId);
    bOk &= Test.TestEqual(*(Context + TEXT(": beat")), Saved->CheckpointBeat, Director->ActiveBeat());
    bOk &= Test.TestEqual(*(Context + TEXT(": phase")), Saved->CheckpointPhase, Director->ActivePhase());
    bOk &= Test.TestEqual(*(Context + TEXT(": beats done")), Saved->CheckpointBeatsMask, static_cast<int32>(Progress.CompletedMask));
    bOk &= Test.TestEqual(*(Context + TEXT(": sites")), Saved->CheckpointSitesMask, static_cast<int32>(Progress.SitesMask));
    bOk &= Test.TestEqual(*(Context + TEXT(": weapons")), Saved->CheckpointWeapons, static_cast<int32>(Progress.WeaponsMask));
    bOk &= Test.TestEqual(*(Context + TEXT(": mechanics")), Saved->CheckpointMechanics, static_cast<int32>(Progress.MechanicsMask));
    bOk &= Test.TestEqual(*(Context + TEXT(": dojo forms")), Saved->CheckpointDojoLessonMask, Lessons);
    bOk &= Test.TestEqual(*(Context + TEXT(": collectibles")), static_cast<uint64>(Saved->Collectibles), static_cast<uint64>(Director->CollectedMask()));
    bOk &= Test.TestEqual(*(Context + TEXT(": Nyaakoto remains the campaign class")), Saved->SelectedClass, 0);
    ++State.CheckpointsRead;
    return bOk || Fail(Test, State, Context + TEXT(" disagrees with the live beat"));
}

// Lethal damage from the hero goes through ASoraCharacterBase::TakeDamage and
// SoraDamage::Resolve to ASoraEnemy::OnDefeated, the only caller of
// OpponentDefeated in play.
bool DefeatOne(FAutomationTestBase& Test, FState& State)
{
    ASoraPlayerCharacter* Hero = Player(State);
    const TArray<ASoraEnemy*> Enemies = LiveEnemies(State);
    if (Enemies.IsEmpty())
        return Fail(Test, State, Where(State) + FString::Printf(TEXT(" has no live opponent at %d/%d defeats"),
            Campaign(State)->Kills, Campaign(State)->KillsNeeded));
    ASoraEnemy* Target = Enemies[0];
    const int32 Before = Campaign(State)->Kills;
    const int32 Beat = Campaign(State)->ActiveBeat();
    UGameplayStatics::ApplyDamage(Target, Target->Health, Hero->GetController(), Hero, UDamageType::StaticClass());
    if (!Test.TestFalse(TEXT("A defeated opponent is no longer alive"), Target->IsAlive()) ||
        (Campaign(State)->ActiveBeat() == Beat && !Test.TestEqual(TEXT("OpponentDefeated records one defeat"), Campaign(State)->Kills, Before + 1)))
        return Fail(Test, State, Where(State) + TEXT(": a defeat was not recorded"));
    return Advance(Test, State);
}

// Opponents a non-combat beat's waves send must all fall before it completes.
bool ClearWaves(FAutomationTestBase& Test, FState& State, int32 Beat)
{
    for (int32 Action = 0; Action < MaxActionsPerBeat; ++Action)
    {
        const USoraCampaignDirector* Director = Campaign(State);
        if (Director->ActiveBeat() != Beat || Director->Kills >= Director->KillsNeeded)
            return true;
        if (!DefeatOne(Test, State))
            return false;
    }
    return Fail(Test, State, Where(State) + TEXT(": waves exceeded the action budget"));
}

bool OpenCaches(FAutomationTestBase& Test, FState& State)
{
    USoraCampaignDirector* Director = Campaign(State);
    if (!Mode(State)->IsPlaying())
        return true;
    for (const int32 Cache : Director->AvailableCaches())
    {
        const FSoraChapter& Chapter = ChapterData(State);
        const uint64 Before = Director->CollectedMask();
        MoveTo(State, Director->CacheLocation(Cache));
        Mode(State)->Interact(Player(State));
        const SoraBeatRules::FBeat& Rule = Chapter.Rules[Cache];
        bool bOk = Test.TestTrue(*FString::Printf(TEXT("%s cache opened"), *Chapter.Beats[Cache].Id),
            (Director->Progress().CompletedMask & SoraBeatRules::BeatBit(Cache)) != 0u);
        bOk &= Test.TestTrue(*FString::Printf(TEXT("%s cache weapons"), *Chapter.Beats[Cache].Id),
            (Director->Progress().WeaponsMask & Rule.WeaponsMask) == Rule.WeaponsMask);
        for (const int32 Item : Chapter.Beats[Cache].Rewards)
            bOk &= Test.TestTrue(*FString::Printf(TEXT("%s holds %s"), *Chapter.Beats[Cache].Id, *Chapter.Collectibles[Item].Id),
                (Director->CollectedMask() & SoraCampaignRules::CollectibleBit(Director->ChapterId, Chapter.Collectibles[Item].MaskBit)) != 0ull);
        bOk &= Test.TestTrue(TEXT("Opening a cache finds something new"), Director->CollectedMask() != Before || Rule.WeaponsMask != 0u);
        if (!bOk)
            return Fail(Test, State, Chapter.Beats[Cache].Id + TEXT(" cache did not open"));
        ++State.CachesOpened;
        if (!Advance(Test, State))
            return false;
    }
    return true;
}

bool RecordLessons(FAutomationTestBase& Test, FState& State, const FSoraBeat& Beat, bool bFirst)
{
    USoraCampaignDirector* Director = Campaign(State);
    using SoraDojoRules::EAction;
    bool bOk = true;
    if (bFirst)
    {
        // Pupils cannot be scored and forms cannot be skipped before they are taught.
        const TArray<ASoraEnemy*> Pupils = LiveEnemies(State);
        if (Pupils.IsEmpty())
            return Fail(Test, State, TEXT("The dojo has no sparring pupil"));
        UGameplayStatics::ApplyDamage(Pupils[0], Pupils[0]->Health, Player(State)->GetController(), Player(State), UDamageType::StaticClass());
        bOk &= Test.TestTrue(TEXT("An untrained strike leaves the pupil standing"), Pupils[0]->IsAlive() && Director->Kills == 0);
        bOk &= Test.TestFalse(TEXT("The guard form waits for its own duel"), Director->RecordDojoLesson(EAction::Guard, SoraDojoRules::GuardHoldMs));
        bOk &= Test.TestFalse(TEXT("A short stance is rejected"), Director->RecordDojoLesson(EAction::Stance, SoraDojoRules::StanceHoldMs - 1));
    }
    for (int32 Stage = 0; Stage < 4; ++Stage)
    {
        if ((Beat.LessonMask & (1u << Stage)) == 0u)
            continue;
        switch (static_cast<EAction>(Stage))
        {
        case EAction::Stance:
            bOk &= Test.TestTrue(TEXT("Stance"), Director->RecordDojoLesson(EAction::Stance, SoraDojoRules::StanceHoldMs));
            break;
        case EAction::Guard:
            bOk &= Test.TestFalse(TEXT("Guard must face the attacker"), Director->RecordDojoLesson(EAction::Guard, SoraDojoRules::GuardHoldMs, false));
            bOk &= Test.TestTrue(TEXT("Guard"), Director->RecordDojoLesson(EAction::Guard, SoraDojoRules::GuardHoldMs));
            break;
        case EAction::Parry:
            bOk &= Test.TestFalse(TEXT("A late parry is rejected"), Director->RecordDojoLesson(EAction::Parry, SoraDojoRules::ParryWindowMs + 1));
            bOk &= Test.TestTrue(TEXT("Parry"), Director->RecordDojoLesson(EAction::Parry, SoraDojoRules::ParryWindowMs));
            break;
        case EAction::Recovery:
            bOk &= Test.TestFalse(TEXT("Recovery needs a committed swing"), Director->RecordDojoLesson(EAction::Recovery, 500, true, 0));
            bOk &= Test.TestTrue(TEXT("Recovery"), Director->RecordDojoLesson(EAction::Recovery, 500, true, 450));
            break;
        }
    }
    return bOk || Fail(Test, State, Beat.Id + TEXT(": Nyaagyushinkageryuu forms did not follow the dojo rules"));
}

// Plays the active beat to its completion through the entry points its goal
// uses, then checks the beat's site, unlocks and the next beat's checkpoint.
bool PlayBeat(FAutomationTestBase& Test, FState& State)
{
    ASoraGameMode* GameMode = Mode(State);
    USoraCampaignDirector* Director = Campaign(State);
    const FSoraChapter& Chapter = ChapterData(State);
    const int32 Index = Director->ActiveBeat();
    if (!Chapter.Beats.IsValidIndex(Index))
        return Fail(Test, State, Where(State) + TEXT(": no active beat"));
    const FSoraBeat& Beat = Chapter.Beats[Index];
    const SoraBeatRules::FBeat& Rule = Chapter.Rules[Index];
    FVector Anchor;
    bool bOk = true;
    switch (Beat.Goal)
    {
    case ESoraBeatGoal::Cinematic:
        bOk &= Test.TestTrue(*(Beat.Id + TEXT(" plays on the card")), GameMode->InputState() == SoraInput::Card &&
            GameMode->TitleCardChapter() == &Chapter && GameMode->TitleCardTime > 0.f && LiveEnemies(State).IsEmpty());
        bOk &= Test.TestTrue(*(Beat.Id + TEXT(" is skippable")), Beat.bSkippable);
        GameMode->BeginRound();
        break;
    case ESoraBeatGoal::Lines:
        if (Beat.bLinesAtAnchor)
        {
            bOk &= Test.TestFalse(*(Beat.Id + TEXT(" waits for its trigger")), Director->LinesStarted());
            if (!Director->ObjectiveAnchor(Anchor))
                return Fail(Test, State, Beat.Id + TEXT(" has no trigger anchor"));
            MoveTo(State, Anchor);
            if (!Advance(Test, State))
                return false;
            if (Beat.bLinesOnInteract)
                GameMode->Interact(Player(State));
        }
        bOk &= Test.TestTrue(*(Beat.Id + TEXT(" lines begin")), Director->LinesStarted());
        for (int32 Action = 0; Action < MaxActionsPerBeat && Director->ActiveBeat() == Index && !GameMode->bChapterComplete; ++Action)
        {
            if (const FSoraDialogueCue* Line = Director->CurrentDialogueCue())
            {
                bOk &= Test.TestTrue(*(Line->Id + TEXT(" is bilingual")), HasJapanese(Line->Japanese) && !Line->English.IsEmpty() &&
                    FSoraCatalog::Get().DialogueSpeaker(Line->SpeakerId) != nullptr);
                ++State.LinesShown;
            }
            if (Director->LinesQueued() == 0 && Beat.bReachAfterLines && Director->ObjectiveAnchor(Anchor))
                MoveTo(State, Anchor);
            if (!Advance(Test, State, 1, FastSeconds))
                return false;
        }
        break;
    case ESoraBeatGoal::Defeat:
        for (int32 Action = 0; Action < MaxActionsPerBeat && Director->ActiveBeat() == Index && !GameMode->bChapterComplete; ++Action)
            if (!DefeatOne(Test, State))
                return false;
        break;
    case ESoraBeatGoal::Lessons:
        if (!RecordLessons(Test, State, Beat, Index == 1 && Director->ChapterId == 0))
            return false;
        for (int32 Action = 0; Action < MaxActionsPerBeat && Director->ActiveBeat() == Index; ++Action)
            if (!DefeatOne(Test, State))
                return false;
        break;
    case ESoraBeatGoal::Interact:
        if (!Director->ObjectiveAnchor(Anchor))
            return Fail(Test, State, Beat.Id + TEXT(" has no anchor"));
        GameMode->Interact(Player(State));
        bOk &= Test.TestEqual(*(Beat.Id + TEXT(" cannot be worked from afar")), Director->Interactions(), 0);
        MoveTo(State, Anchor);
        if (!Advance(Test, State))
            return false;
        for (int32 Turn = 0; Turn < Beat.GoalCount && Director->ActiveBeat() == Index; ++Turn)
            GameMode->Interact(Player(State));
        if (!ClearWaves(Test, State, Index) || !Advance(Test, State))
            return false;
        break;
    case ESoraBeatGoal::Hold:
        if (!ClearWaves(Test, State, Index) || !Director->ObjectiveAnchor(Anchor))
            return Fail(Test, State, Beat.Id + TEXT(" cannot be held"));
        bOk &= Test.TestEqual(*(Beat.Id + TEXT(" holds nothing from afar")), Director->HeldSeconds(), 0.f);
        MoveTo(State, Anchor);
        for (int32 Action = 0; Action < MaxActionsPerBeat && Director->ActiveBeat() == Index; ++Action)
            if (!Advance(Test, State, 1, FastSeconds))
                return false;
        break;
    case ESoraBeatGoal::Reach:
        if (!ClearWaves(Test, State, Index) || !Director->ObjectiveAnchor(Anchor))
            return Fail(Test, State, Beat.Id + TEXT(" has no destination"));
        MoveTo(State, Anchor);
        if (!Advance(Test, State))
            return false;
        break;
    case ESoraBeatGoal::Explore:
        return Fail(Test, State, Beat.Id + TEXT(": an optional beat became the active beat"));
    }
    const SoraBeatRules::FProgress& Progress = Director->Progress();
    bOk &= Test.TestTrue(*(Beat.Id + TEXT(" completes")), (Director->ActiveBeat() != Index || GameMode->bChapterComplete) &&
        (Progress.CompletedMask & SoraBeatRules::BeatBit(Index)) != 0u);
    bOk &= Test.TestTrue(*(Beat.Id + TEXT(" unlocks its weapons and mechanics")),
        (Progress.WeaponsMask & (Rule.WeaponsMask | Rule.GrantsMask)) == (Rule.WeaponsMask | Rule.GrantsMask) &&
        (Progress.MechanicsMask & Rule.MechanicsMask) == Rule.MechanicsMask);
    if (Rule.Site >= 0)
        bOk &= Test.TestTrue(*(Beat.Id + TEXT(" restores its site")), (GameMode->Arena()->ActivatedMask() & (1 << Rule.Site)) != 0);
    if (!bOk)
        return Fail(Test, State, Beat.Id + TEXT(" did not play through"));
    ++State.BeatsPlayed;
    Player(State)->Heal(Player(State)->MaxHealth);
    return Advance(Test, State, 1);
}

// Plays beats until StopBeat is active (INDEX_NONE: until the chapter ends).
bool PlayUntil(FAutomationTestBase& Test, FState& State, int32 StopBeat = INDEX_NONE)
{
    for (int32 Beat = 0; Beat <= SoraBeatRules::MaxBeats; ++Beat)
    {
        const USoraCampaignDirector* Director = Campaign(State);
        if (Mode(State)->bChapterComplete || Director->ActiveBeat() == StopBeat)
            return true;
        // A checkpoint beat saved as it started, before any cache is opened.
        const FSoraChapter& Chapter = ChapterData(State);
        if (Chapter.Rules.IsValidIndex(Director->ActiveBeat()) && Chapter.Rules[Director->ActiveBeat()].Checkpoint &&
            Director->ActivePhase() == 0 && !ExpectCheckpoint(Test, State))
            return false;
        if (Director->ChapterId < CompletistChapters && !OpenCaches(Test, State))
            return false;
        if (!PlayBeat(Test, State))
            return false;
    }
    return Fail(Test, State, Where(State) + TEXT(": the chapter did not end"));
}

// A fresh chapter opens on its first cinematic with the title card: the
// chapter's Japanese and English title, narrative and objective. The card
// holds the round timer, combat and dialogue until Enter skips it.
bool ExpectOpening(FAutomationTestBase& Test, FState& State, int32 Chapter)
{
    const ASoraGameMode* GameMode = Mode(State);
    const USoraCampaignDirector* Director = Campaign(State);
    const FSoraChapter& Data = FSoraCatalog::Get().Chapter(Chapter);
    const FSoraChapter* Card = GameMode->TitleCardChapter();
    const FString Context = FString::Printf(TEXT("Chapter %d opening"), Chapter + 1);
    bool bOk = Test.TestEqual(*(Context + TEXT(": chapter")), Director->ChapterId, Chapter);
    bOk &= Test.TestEqual(*(Context + TEXT(": cataloged map")), GameMode->MapId, Data.Map);
    bOk &= Test.TestTrue(*(Context + TEXT(": the title card shows before play")), Card == &Data &&
        GameMode->InputState() == SoraInput::Card && Director->ActiveBeat() == 0 && Director->IsChapterOpening() &&
        Director->CinematicElapsed() < ASoraGameMode::TitleCardSeconds);
    bOk &= Test.TestTrue(*(Context + TEXT(": Japanese title, narrative and objective")),
        Card && HasJapanese(Card->Title) && HasJapanese(Card->Narrative) && HasJapanese(Card->Objective));
    bOk &= Test.TestTrue(*(Context + TEXT(": English title, narrative and objective")),
        Card && !Card->TitleEnglish.IsEmpty() && !Card->NarrativeEnglish.IsEmpty() && !Card->ObjectiveEnglish.IsEmpty() &&
        !HasJapanese(Card->TitleEnglish) && !HasJapanese(Card->ObjectiveEnglish));
    bOk &= Test.TestTrue(*(Context + TEXT(": English subtitles are on by default")), GameMode->bEnglishSubtitles);
    bOk &= Test.TestEqual(*(Context + TEXT(": round timer waits")), GameMode->RoundTime, 0.f);
    bOk &= Test.TestEqual(*(Context + TEXT(": no beat done")), static_cast<int32>(Director->Progress().CompletedMask), 0);
    bOk &= Test.TestEqual(*(Context + TEXT(": no site")), GameMode->Arena()->ActivatedMask(), 0);
    bOk &= Test.TestTrue(*(Context + TEXT(": no opponent")), LiveEnemies(State).IsEmpty());
    return bOk || Fail(Test, State, Context + TEXT(" did not open on its title card"));
}

bool StartWorld(FAutomationTestBase& Test, FState& State)
{
    State.World = MakeUnique<FSoraAutomationWorld>();
    ++State.WorldsStarted;
    // BeginPlay reads the save; the next tick runs ResetRound, which rebuilds
    // the chapter and restores the checkpoint.
    if (!State.World->Start(State.Slot) || !State.World->Tick(1))
    {
        State.World->ForwardErrorMessages(&Test);
        return Fail(Test, State, FString::Printf(TEXT("Campaign world %d did not start"), State.WorldsStarted));
    }
    const ASoraGameMode* GameMode = Mode(State);
    if (!GameMode || !GameMode->Arena() || !Player(State) || !FSoraCatalog::Get().IsReady())
        return Fail(Test, State, TEXT("Campaign world lacks its arena, player or catalog"));
    return (Test.TestTrue(TEXT("A loaded campaign opens in the menu"), GameMode->bMenu) &&
        Test.TestTrue(TEXT("The open menu pauses the world"), Paused(State))) ||
        Fail(Test, State, TEXT("Campaign world skipped its paused menu"));
}

bool StopWorld(FAutomationTestBase& Test, FState& State)
{
    const bool bDestroyed = State.World->DestroyTestWorld(true);
    State.World->ForwardErrorMessages(&Test);
    State.World.Reset();
    return Test.TestTrue(TEXT("Campaign world tears down"), bDestroyed) || Fail(Test, State, TEXT("World teardown failed"));
}

// Tears the world down and restores the saved checkpoint in a fresh one.
bool Reload(FAutomationTestBase& Test, FState& State)
{
    const USoraCampaignDirector* Director = Campaign(State);
    const FString Context = TEXT("Reloaded ") + Where(State);
    const int32 Chapter = Director->ChapterId, Beat = Director->ActiveBeat(), Phase = Director->ActivePhase();
    const SoraBeatRules::FProgress Progress = Director->Progress();
    const int32 Sites = Mode(State)->Arena()->ActivatedMask();
    const int32 LessonStage = Director->DojoLessonStage();
    const bool bComplete = Mode(State)->bChapterComplete, bLiberated = Director->bCampaignComplete;
    const uint64 Collected = Director->CollectedMask();
    if (!StopWorld(Test, State) || !StartWorld(Test, State))
        return false;
    Director = Campaign(State);
    bool bOk = Test.TestEqual(*(Context + TEXT(": chapter")), Director->ChapterId, Chapter);
    bOk &= Test.TestEqual(*(Context + TEXT(": completion")), Mode(State)->bChapterComplete, bComplete);
    bOk &= Test.TestEqual(*(Context + TEXT(": liberation")), Director->bCampaignComplete, bLiberated);
    bOk &= Test.TestEqual(*(Context + TEXT(": collectibles")), Director->CollectedMask(), Collected);
    if (!bComplete)
    {
        bOk &= Test.TestEqual(*(Context + TEXT(": beat")), Director->ActiveBeat(), Beat);
        bOk &= Test.TestEqual(*(Context + TEXT(": phase")), Director->ActivePhase(), Phase);
        bOk &= Test.TestEqual(*(Context + TEXT(": beats done")), Director->Progress().CompletedMask, Progress.CompletedMask);
        bOk &= Test.TestEqual(*(Context + TEXT(": weapons")), Director->Progress().WeaponsMask, Progress.WeaponsMask);
        bOk &= Test.TestEqual(*(Context + TEXT(": mechanics")), Director->Progress().MechanicsMask, Progress.MechanicsMask);
        bOk &= Test.TestEqual(*(Context + TEXT(": sites")), Mode(State)->Arena()->ActivatedMask(), Sites);
        bOk &= Test.TestEqual(*(Context + TEXT(": dojo forms")), Director->DojoLessonStage(), LessonStage);
    }
    return bOk || Fail(Test, State, Context + TEXT(" did not match its checkpoint"));
}

// Enter from the menu returns to a restored checkpoint without the title card.
bool Resume(FAutomationTestBase& Test, FState& State)
{
    ASoraGameMode* GameMode = Mode(State);
    GameMode->BeginRound();
    const FSoraBeat* Beat = Campaign(State)->ActiveBeatData();
    bool bOk = Test.TestFalse(TEXT("Enter closes the menu"), GameMode->bMenu);
    bOk &= Test.TestFalse(TEXT("Closing the menu unpauses the world"), Paused(State));
    bOk &= Test.TestFalse(TEXT("A resumed checkpoint skips the title card"), Campaign(State)->IsChapterOpening());
    bOk &= Test.TestTrue(TEXT("A resumed checkpoint is in play or its cinematic"),
        GameMode->IsPlaying() || (Beat && Beat->Goal == ESoraBeatGoal::Cinematic));
    return (bOk || Fail(Test, State, TEXT("Resuming a checkpoint did not return to play"))) && Advance(Test, State);
}

// The chapter's result screen; Enter saves the next chapter (entered with
// everything this route earned) and opens it, or liberates the campaign.
bool NextChapter(FAutomationTestBase& Test, FState& State)
{
    ASoraGameMode* GameMode = Mode(State);
    USoraCampaignDirector* Director = Campaign(State);
    const int32 Chapter = Director->ChapterId;
    const SoraBeatRules::FProgress Earned = Director->Progress();
    const USoraSaveGame* Saved = Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(State.Slot, 0));
    bool bOk = Test.TestTrue(*FString::Printf(TEXT("Chapter %d completes"), Chapter + 1),
        GameMode->bChapterComplete && GameMode->InputState() == SoraInput::Result && Earned.Complete);
    bOk &= Test.TestTrue(TEXT("The finished chapter waits at its result in the save"),
        Saved && Saved->CheckpointChapter == Chapter && Saved->CheckpointBeat == INDEX_NONE && Saved->CheckpointComplete);
    bOk &= Test.TestEqual(TEXT("The next chapter is reached"), Saved ? Saved->HighestChapter : -1, FMath::Min(LastChapter, Chapter + 1));
    if (!bOk)
        return Fail(Test, State, FString::Printf(TEXT("Chapter %d did not finish"), Chapter + 1));
    GameMode->BeginRound();
    ++State.ChaptersCompleted;
    Saved = Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(State.Slot, 0));
    if (!Test.TestNotNull(TEXT("The advance is saved"), Saved))
        return Fail(Test, State, TEXT("Chapter advance was not saved"));
    if (Chapter == LastChapter)
    {
        Test.TestEqual(TEXT("Liberation clears the chapter checkpoint"), Saved->CheckpointChapter, -1);
        bOk = Test.TestTrue(TEXT("The final Enter liberates the campaign"), Director->bCampaignComplete);
        bOk &= Test.TestTrue(TEXT("Liberation returns to the menu"), GameMode->bMenu);
        bOk &= Test.TestTrue(TEXT("The liberation menu pauses the world"), Paused(State));
        bOk &= Test.TestTrue(TEXT("Liberation is saved"), Saved->CampaignComplete);
        bOk &= Test.TestEqual(TEXT("The liberated campaign stays on the final chapter"), Saved->CurrentChapter, LastChapter);
        return bOk || Fail(Test, State, TEXT("Campaign liberation was not recorded"));
    }
    // The next chapter's opening cinematic takes the first checkpoint at once.
    bOk = Test.TestEqual(TEXT("Enter advances to the next chapter"), Director->ChapterId, Chapter + 1);
    bOk &= Test.TestTrue(TEXT("The next chapter's first checkpoint is its opening"),
        Saved->CheckpointChapter == Chapter + 1 && Saved->CheckpointBeat == 0 && Saved->CheckpointBeatsMask == 0);
    bOk &= Test.TestFalse(TEXT("The next chapter starts out of the menu"), GameMode->bMenu);
    bOk &= Test.TestEqual(TEXT("The next chapter is saved"), Saved->CurrentChapter, Chapter + 1);
    bOk &= Test.TestEqual(TEXT("It is entered with this route's weapons"), Saved->ChapterEntryWeapons, static_cast<int32>(Earned.WeaponsMask));
    bOk &= Test.TestEqual(TEXT("It is entered with this route's mechanics"), Saved->ChapterEntryMechanics, static_cast<int32>(Earned.MechanicsMask));
    bOk &= Test.TestFalse(TEXT("The campaign is not liberated early"), Saved->CampaignComplete);
    return (bOk || Fail(Test, State, FString::Printf(TEXT("Chapter %d did not advance"), Chapter + 1))) && ExpectOpening(Test, State, Chapter + 1);
}

bool FinishChapter(FAutomationTestBase& Test, FState& State)
{
    return PlayUntil(Test, State) && NextChapter(Test, State);
}

// Nyaakoto holds only what the campaign has unlocked: his class slots
// (katana, arc carbine, monofilament naginata) and the yumi, yari and naginata.
bool ExpectWeapon(FAutomationTestBase& Test, FState& State, int32 WeaponId, bool bUnlocked)
{
    ASoraPlayerCharacter* Hero = Player(State);
    USoraEquipmentComponent* Kit = Hero->GetEquipment();
    const int32 Held = Hero->WeaponId;
    if (WeaponId < 18 && !FSoraCatalog::Get().Class(0).Weapons.Contains(WeaponId))
        return Fail(Test, State, FString::Printf(TEXT("Weapon %d has no campaign slot"), WeaponId));
    const bool bEquipped = WeaponId >= 18 ? Kit->EquipCampaignWeapon(WeaponId) : Kit->EquipClassSlot(FSoraCatalog::Get().Class(0).Weapons.Find(WeaponId));
    const FString What = FString::Printf(TEXT("%s: weapon %d %s"), *Where(State), WeaponId, bUnlocked ? TEXT("equips") : TEXT("stays locked"));
    bool bOk = Test.TestEqual(*What, bEquipped, bUnlocked) && Test.TestEqual(*(What + TEXT(" (held)")), Hero->WeaponId, bUnlocked ? WeaponId : Held);
    if (!bUnlocked)
        bOk &= Test.TestTrue(*(What + TEXT(" with a notice")), Mode(State)->NoticeTime > 0.f && !Mode(State)->NoticeEnglish.IsEmpty());
    // Back to the katana, after the equip delay.
    if (!Advance(Test, State, 20) || (bEquipped && !Kit->EquipClassSlot(0)))
        return Fail(Test, State, What + TEXT(": could not return to the katana"));
    return (bOk || Fail(Test, State, What)) && Advance(Test, State, 20);
}

bool DefeatAndRetry(FAutomationTestBase& Test, FState& State)
{
    ASoraGameMode* GameMode = Mode(State);
    USoraCampaignDirector* Director = Campaign(State);
    ASoraPlayerCharacter* Hero = Player(State);
    const TArray<ASoraEnemy*> Enemies = LiveEnemies(State);
    if (Enemies.IsEmpty())
        return Fail(Test, State, TEXT("No opponent is there to defeat the hero"));
    if (!DefeatOne(Test, State))
        return false;
    const int32 Beat = Director->ActiveBeat();
    const SoraBeatRules::FProgress Progress = Director->Progress();
    const int32 Sites = GameMode->Arena()->ActivatedMask();
    UGameplayStatics::ApplyDamage(Hero, Hero->Health, nullptr, LiveEnemies(State)[0], UDamageType::StaticClass());
    if (!Test.TestTrue(TEXT("Lethal damage defeats the hero"), GameMode->bDefeated && GameMode->InputState() == SoraInput::Result))
        return Fail(Test, State, TEXT("Hero defeat was not recorded"));
    GameMode->BeginRound();
    bool bOk = Test.TestFalse(TEXT("Enter retries after defeat"), GameMode->bDefeated);
    bOk &= Test.TestFalse(TEXT("A retry skips the title card"), Director->IsChapterOpening());
    bOk &= Test.TestEqual(TEXT("A retry returns to the beat's checkpoint"), Director->ActiveBeat(), Beat);
    bOk &= Test.TestEqual(TEXT("A retry keeps the beats done"), Director->Progress().CompletedMask, Progress.CompletedMask);
    bOk &= Test.TestEqual(TEXT("A retry keeps restored sites"), GameMode->Arena()->ActivatedMask(), Sites);
    bOk &= Test.TestEqual(TEXT("A retry starts the wave over"), Director->Kills, 0);
    bOk &= Test.TestTrue(TEXT("A retry restores the hero"), Hero->IsAlive() && Hero->Health == Hero->MaxHealth);
    bOk &= Test.TestFalse(TEXT("A retry respawns the opponents"), LiveEnemies(State).IsEmpty());
    return (bOk || Fail(Test, State, TEXT("Retry did not restore the checkpoint"))) && Advance(Test, State);
}

// A long boss saves at each later phase and returns at that phase's health.
bool BossPhase(FAutomationTestBase& Test, FState& State)
{
    USoraCampaignDirector* Director = Campaign(State);
    const FSoraBeat& Beat = *Director->ActiveBeatData();
    const ASoraBoss* Boss = Director->CampaignBoss();
    if (!Test.TestNotNull(*(Beat.Id + TEXT(": the boss takes the field")), Boss) || Beat.PhaseHealthPercent.Num() < 2)
        return Fail(Test, State, Beat.Id + TEXT(" has no phased boss"));
    ASoraBoss* Target = const_cast<ASoraBoss*>(Boss);
    const float Damage = Target->MaxHealth * (100 - Beat.PhaseHealthPercent[1] + 5) / 100.f;
    UGameplayStatics::ApplyDamage(Target, Damage, Player(State)->GetController(), Player(State), UDamageType::StaticClass());
    if (!Advance(Test, State))
        return false;
    const USoraSaveGame* Saved = Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(State.Slot, 0));
    bool bOk = Test.TestEqual(*(Beat.Id + TEXT(": the second phase begins")), Director->ActivePhase(), 1);
    bOk &= Test.TestTrue(*(Beat.Id + TEXT(": the phase is saved")), Saved && Saved->CheckpointBeat == Director->ActiveBeat() && Saved->CheckpointPhase == 1);
    if (!bOk || !Reload(Test, State) || !Resume(Test, State))
        return Fail(Test, State, Beat.Id + TEXT(": phase checkpoint failed"));
    Boss = Campaign(State)->CampaignBoss();
    return (Test.TestNotNull(TEXT("The restored phase respawns the boss"), Boss) &&
        Test.TestEqual(TEXT("The boss returns at its phase's health"), Boss->Health, Boss->MaxHealth * Beat.PhaseHealthPercent[1] / 100.f)) ||
        Fail(Test, State, TEXT("The boss phase was not restored"));
}

void Step(FAutomationTestBase* Test, const FStateRef& State, TFunction<bool(FAutomationTestBase&, FState&)> Body)
{
    ADD_LATENT_AUTOMATION_COMMAND(FFunctionLatentCommand([Test, State, Body = MoveTemp(Body)]()
    {
        if (!State->bAborted)
            Body(*Test, *State);
        return true;
    }));
}
} // namespace SoraCampaignPlaythrough

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraCampaignPlaythroughTest,
    "SoraArena.Campaign.Playthrough",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraCampaignPlaythroughTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraCampaignPlaythrough;
    const FSoraCatalog& Catalog = FSoraCatalog::Get();
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()) ||
        !TestEqual(TEXT("Eight campaign chapters"), Catalog.Chapters.Num(), LastChapter + 1))
        return false;
    for (int32 Chapter = 0; Chapter <= LastChapter; ++Chapter)
        if (!TestEqual(*FString::Printf(TEXT("Chapter %d has three production sites"), Chapter + 1), Catalog.Chapter(Chapter).Sites.Num(), 3))
            return false;
    FSoraAutomationWorld::IgnoreMissingGeneratedArt(*this);
    const FStateRef State = MakeShared<FState>();
    FSoraAutomationWorld::IgnoreAbsentSaveSlot(*this, State->Slot);

    // The dojo from a new save, through the lesson duels to its smithy.
    Step(this, State, [](FAutomationTestBase& Test, FState& S)
    {
        if (!Test.TestFalse(TEXT("The isolated save slot starts empty"), UGameplayStatics::DoesSaveGameExist(S.Slot, 0)))
            return Fail(Test, S, TEXT("Automation save slot already exists"));
        if (!StartWorld(Test, S))
            return false;
        Mode(S)->BeginRound();
        if (!Test.TestFalse(TEXT("Closing the menu unpauses the world"), Paused(S)) || !ExpectOpening(Test, S, 0))
            return false;
        return PlayUntil(Test, S, 8);
    });
    // Mid-dojo: the forms, two sites and the yumi survive world teardown.
    Step(this, State, [](FAutomationTestBase& Test, FState& S)
    {
        return Reload(Test, S) && Test.TestTrue(TEXT("Restored pupils can be scored"), Campaign(S)->CanScoreDojoBout()) &&
            Resume(Test, S) && FinishChapter(Test, S);
    });
    // The invasion: the yari stays locked until the armory, then Dunark's phases.
    Step(this, State, [](FAutomationTestBase& Test, FState& S)
    {
        if (!PlayUntil(Test, S, 1) || !ExpectWeapon(Test, S, 19, false) || !ExpectWeapon(Test, S, 1, false) ||
            !ExpectWeapon(Test, S, 18, true) || !PlayUntil(Test, S, 3) || !ExpectWeapon(Test, S, 19, true))
            return false;
        return PlayUntil(Test, S, 14) && BossPhase(Test, S);
    });
    Step(this, State, [](FAutomationTestBase& Test, FState& S) { return FinishChapter(Test, S); });
    // Occupied streets: a defeat is retried from the workshop fight's checkpoint.
    Step(this, State, [](FAutomationTestBase& Test, FState& S)
    {
        return PlayUntil(Test, S, 7) && DefeatAndRetry(Test, S) && FinishChapter(Test, S);
    });
    // The fields: a hold beat's checkpoint survives world teardown.
    Step(this, State, [](FAutomationTestBase& Test, FState& S)
    {
        return PlayUntil(Test, S, 6) && Reload(Test, S) && Resume(Test, S) && FinishChapter(Test, S);
    });
    Step(this, State, [](FAutomationTestBase& Test, FState& S) { return FinishChapter(Test, S); });
    // The vault: the foundry's arc carbine is carried in; the optional armory is
    // skipped, so the phantom SMG waits for the flagship chapter's auto-grant.
    Step(this, State, [](FAutomationTestBase& Test, FState& S)
    {
        return PlayUntil(Test, S, 1) && ExpectWeapon(Test, S, 1, true) && FinishChapter(Test, S);
    });
    Step(this, State, [](FAutomationTestBase& Test, FState& S)
    {
        const bool bBefore = (Campaign(S)->Progress().WeaponsMask & (1u << 13)) != 0u;
        if (!Test.TestFalse(TEXT("The skipped armory leaves the phantom SMG locked"), bBefore) || !PlayUntil(Test, S, 1))
            return Fail(Test, S, TEXT("Optional weapon mask is wrong"));
        return Test.TestTrue(TEXT("The war council grants the phantom SMG"), (Campaign(S)->Progress().WeaponsMask & (1u << 13)) != 0u) &&
            FinishChapter(Test, S);
    });
    Step(this, State, [](FAutomationTestBase& Test, FState& S)
    {
        if (!PlayUntil(Test, S) || !Test.TestEqual(TEXT("Every weapon is unlocked"), Campaign(S)->Progress().WeaponsMask, SoraBeatRules::AllWeaponsMask) ||
            !Test.TestEqual(TEXT("Every mechanic is unlocked"), Campaign(S)->Progress().MechanicsMask, SoraBeatRules::AllMechanicsMask))
            return Fail(Test, S, TEXT("The final chapter did not end with every unlock"));
        return NextChapter(Test, S);
    });
    // Liberation is durable: a fresh world shows the freed city, not a new battle.
    Step(this, State, [](FAutomationTestBase& Test, FState& S)
    {
        if (!Reload(Test, S))
            return false;
        const ASoraGameMode* GameMode = Mode(S);
        bool bOk = Test.TestTrue(TEXT("The reloaded campaign is liberated"), Campaign(S)->bCampaignComplete && GameMode->bChapterComplete);
        bOk &= Test.TestEqual(TEXT("The liberated city shows every site"), GameMode->Arena()->ActivatedMask(), 7);
        bOk &= Test.TestTrue(TEXT("No opponent returns to the liberated city"), LiveEnemies(S).IsEmpty());
        // Chapters one to five opened every cache; six to eight left theirs.
        const FSoraCatalog& Data = FSoraCatalog::Get();
        for (int32 Chapter = 0; Chapter <= LastChapter; ++Chapter)
            for (const FSoraBeat& Beat : Data.Chapter(Chapter).Beats)
                for (const int32 Item : Beat.Rewards)
                {
                    const FSoraCollectible& Found = Data.Chapter(Chapter).Collectibles[Item];
                    bOk &= Test.TestEqual(*FString::Printf(TEXT("%s found on this route"), *Found.Id),
                        (Campaign(S)->CollectedMask() & SoraCampaignRules::CollectibleBit(Chapter, Found.MaskBit)) != 0ull,
                        Chapter < CompletistChapters);
                }
        return bOk || Fail(Test, S, TEXT("Liberation did not survive reload"));
    });
    Step(this, State, [](FAutomationTestBase& Test, FState& S)
    {
        if (!StopWorld(Test, S))
            return false;
        Test.TestEqual(TEXT("All eight chapters completed"), S.ChaptersCompleted, LastChapter + 1);
        FSoraAutomationWorld::DeleteSaveSlot(S.Slot);
        Test.TestFalse(TEXT("The isolated save slot is removed"), UGameplayStatics::DoesSaveGameExist(S.Slot, 0));
        UE_LOG(LogTemp, Display, TEXT("SORA_CAMPAIGN_PLAYTHROUGH_OK: chapters=%d beats=%d caches=%d checkpoints=%d lines=%d worlds=%d"),
            S.ChaptersCompleted, S.BeatsPlayed, S.CachesOpened, S.CheckpointsRead, S.LinesShown, S.WorldsStarted);
        return true;
    });
    return true;
}
#endif
