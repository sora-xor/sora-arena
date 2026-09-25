#include "SoraGameMode.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "SoraAutomationWorld.h"
#include "SoraCampaignRules.h"
#include "SoraBoss.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraEnemy.h"
#include "SoraPlayerCharacter.h"
#include "SoraDojoRules.h"
#include "SoraSaveGame.h"
#include "SoraWorldBuilder.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/DamageType.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/AutomationTest.h"
#include "Templates/UniquePtr.h"

// Plays the offline campaign in real game worlds through the same GameMode
// entry points the character input uses: BeginRound (Enter), Interact (E) and
// lethal damage that reaches OpponentDefeated. The disk save is checked after
// every objective event, and three checkpoints are restored in fresh worlds.
// Every fresh chapter must open on its bilingual title card, and the open menu
// must pause the world.
namespace SoraCampaignPlaythrough
{
constexpr int32 LastChapter = 7;
constexpr int32 FramesPerAction = 2;
constexpr int32 MaxActionsPerChapter = 64;

struct FState
{
    FString Slot = FSoraAutomationWorld::UniqueSaveSlot(TEXT("CampaignPlaythrough"));
    TUniquePtr<FSoraAutomationWorld> World;
    bool bAborted = false;
    int32 WorldsStarted = 0;
    int32 ChaptersCompleted = 0;
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

TArray<ASoraEnemy*> LiveEnemies(const FState& State)
{
    TArray<ASoraEnemy*> Result;
    if (UWorld* World = State.World ? State.World->GetTestWorld() : nullptr)
        for (TActorIterator<ASoraEnemy> It(World); It; ++It)
            if (It->IsEnemy() && It->IsAlive() && !It->IsActorBeingDestroyed())
                Result.Add(*It);
    return Result;
}

int32 ActivatedMask(const ASoraGameMode& GameMode)
{
    return GameMode.Arena() ? GameMode.Arena()->ActivatedMask() : -1;
}

SoraCampaignRules::FSite SiteRule(int32 Chapter, int32 Site)
{
    const FSoraProductionSite& Data = FSoraCatalog::Get().Chapter(Chapter).Sites[Site];
    return {Data.RequiredKills, static_cast<unsigned>(Data.RequiredSitesMask)};
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

bool Advance(FAutomationTestBase& Test, FState& State, int32 Frames = FramesPerAction)
{
    if (!State.World->Tick(Frames))
    {
        State.World->ForwardErrorMessages(&Test);
        return Fail(Test, State, TEXT("Campaign world failed to tick"));
    }
    const ASoraGameMode* GameMode = Mode(State);
    if (!GameMode || !Player(State))
        return Fail(Test, State, TEXT("Campaign world lost its game mode or player"));
    // Enemies spawn beyond firing range of the player start and live only a
    // few frames, so a defeat here is a regression rather than bad luck.
    if (GameMode->bDefeated)
        return Fail(Test, State, FString::Printf(TEXT("Player was defeated unexpectedly in chapter %d"), GameMode->Campaign()->ChapterId));
    return true;
}

// Every objective event writes the checkpoint slot. Read it back from disk.
bool ExpectSaved(FAutomationTestBase& Test, FState& State, const FString& Context)
{
    const ASoraGameMode* GameMode = Mode(State);
    const USoraSaveGame* Saved = Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(State.Slot, 0));
    if (!Test.TestNotNull(*(Context + TEXT(": checkpoint written to the isolated slot")), Saved) || !GameMode)
        return Fail(Test, State, Context + TEXT(": no saved checkpoint"));
    const int32 LessonMask = GameMode->Campaign()->ChapterId == 0 ? (1 << GameMode->Campaign()->DojoLessonStage()) - 1 : 0;
    bool bOk = Test.TestEqual(*(Context + TEXT(": save schema")), Saved->SaveSchema, 5);
    bOk &= Test.TestEqual(*(Context + TEXT(": current chapter")), Saved->CurrentChapter, GameMode->Campaign()->ChapterId);
    bOk &= Test.TestEqual(*(Context + TEXT(": checkpoint chapter")), Saved->CheckpointChapter, GameMode->Campaign()->ChapterId);
    bOk &= Test.TestEqual(*(Context + TEXT(": checkpoint defeats")), Saved->CheckpointKills, GameMode->Campaign()->Kills);
    bOk &= Test.TestEqual(*(Context + TEXT(": checkpoint sites")), Saved->CheckpointNodesMask, ActivatedMask(*GameMode));
    bOk &= Test.TestEqual(*(Context + TEXT(": checkpoint completion")), Saved->CheckpointComplete, GameMode->bChapterComplete);
    bOk &= Test.TestEqual(*(Context + TEXT(": dojo lessons")), Saved->CheckpointDojoLessonMask, LessonMask);
    bOk &= Test.TestEqual(*(Context + TEXT(": Nyaakoto remains the campaign class")), Saved->SelectedClass, 0);
    return bOk || Fail(Test, State, Context + TEXT(": saved checkpoint disagrees with the live encounter"));
}

// Lethal damage from the player goes through ASoraCharacterBase::TakeDamage and
// SoraDamage::Resolve to ASoraEnemy::OnDefeated, the only caller of
// OpponentDefeated in play.
bool DefeatOne(FAutomationTestBase& Test, FState& State)
{
    ASoraGameMode* GameMode = Mode(State);
    ASoraPlayerCharacter* Hero = Player(State);
    const TArray<ASoraEnemy*> Enemies = LiveEnemies(State);
    if (Enemies.IsEmpty())
        return Fail(Test, State, FString::Printf(TEXT("Chapter %d has no live opponent at %d/%d defeats"),
            GameMode->Campaign()->ChapterId, GameMode->Campaign()->Kills, GameMode->Campaign()->KillsNeeded));
    ASoraEnemy* Target = Enemies[0];
    const int32 Before = GameMode->Campaign()->Kills;
    UGameplayStatics::ApplyDamage(Target, Target->Health, Hero->GetController(), Hero, UDamageType::StaticClass());
    if (!Test.TestFalse(TEXT("Defeated opponent is no longer alive"), Target->IsAlive()) ||
        !Test.TestEqual(TEXT("OpponentDefeated records exactly one defeat"), GameMode->Campaign()->Kills, Before + 1))
        return Fail(Test, State, FString::Printf(TEXT("Chapter %d defeat %d was not recorded"), GameMode->Campaign()->ChapterId, Before + 1));
    return ExpectSaved(Test, State, FString::Printf(TEXT("Chapter %d defeat %d"), GameMode->Campaign()->ChapterId, GameMode->Campaign()->Kills)) &&
        Advance(Test, State);
}

// Interact is range-gated. Step onto the site, press E, and return to the start
// in the same frame so opponents never see the hero at the site.
void InteractAt(FState& State, const FVector& Location)
{
    ASoraPlayerCharacter* Hero = Player(State);
    const FVector Home = Hero->GetActorLocation();
    Hero->SetActorLocation(FVector(Location.X, Location.Y, Home.Z), false, nullptr, ETeleportType::TeleportPhysics);
    Mode(State)->Interact(Hero);
    Hero->SetActorLocation(Home, false, nullptr, ETeleportType::TeleportPhysics);
}

bool RestoreSite(FAutomationTestBase& Test, FState& State, int32 Site)
{
    ASoraGameMode* GameMode = Mode(State);
    const int32 Before = ActivatedMask(*GameMode);
    InteractAt(State, GameMode->Arena()->NodePositions[Site]);
    if (!Test.TestEqual(*FString::Printf(TEXT("Chapter %d site %d restored"), GameMode->Campaign()->ChapterId, Site),
        ActivatedMask(*GameMode), Before | (1 << Site)))
        return Fail(Test, State, FString::Printf(TEXT("Chapter %d site %d was not restored"), GameMode->Campaign()->ChapterId, Site));
    return ExpectSaved(Test, State, FString::Printf(TEXT("Chapter %d site %d"), GameMode->Campaign()->ChapterId, Site)) &&
        Advance(Test, State);
}

bool ExpectSiteRejected(FAutomationTestBase& Test, FState& State, int32 Site)
{
    ASoraGameMode* GameMode = Mode(State);
    const int32 Before = ActivatedMask(*GameMode);
    InteractAt(State, GameMode->Arena()->NodePositions[Site]);
    return Test.TestEqual(*FString::Printf(TEXT("Chapter %d site %d stays locked before its requirements"),
        GameMode->Campaign()->ChapterId, Site), ActivatedMask(*GameMode), Before) || Fail(Test, State, TEXT("Locked site restored"));
}

bool ExpectExitLocked(FAutomationTestBase& Test, FState& State)
{
    ASoraGameMode* GameMode = Mode(State);
    InteractAt(State, GameMode->Arena()->ExitPoint());
    return Test.TestFalse(*FString::Printf(TEXT("Chapter %d exit stays sealed before its objectives"), GameMode->Campaign()->ChapterId),
        GameMode->bChapterComplete) || Fail(Test, State, TEXT("Exit opened early"));
}

// Restore sites as soon as the catalog allows, otherwise defeat the next
// opponent, until the encounter reaches exactly the requested checkpoint.
bool AdvanceTo(FAutomationTestBase& Test, FState& State, int32 StopKills, int32 StopMask)
{
    for (int32 Action = 0; Action < MaxActionsPerChapter; ++Action)
    {
        ASoraGameMode* GameMode = Mode(State);
        const int32 Mask = ActivatedMask(*GameMode);
        if (GameMode->Campaign()->Kills == StopKills && Mask == StopMask)
            return true;
        int32 Site = INDEX_NONE;
        for (int32 Index = 0; Index < 3 && Site == INDEX_NONE; ++Index)
            if ((StopMask & (1 << Index)) && !(Mask & (1 << Index)) &&
                SoraCampaignRules::CanRestoreSite(GameMode->Campaign()->Kills, static_cast<unsigned>(Mask), SiteRule(GameMode->Campaign()->ChapterId, Index)))
                Site = Index;
        const bool bOk = Site != INDEX_NONE ? RestoreSite(Test, State, Site)
            : GameMode->Campaign()->Kills < StopKills ? DefeatOne(Test, State)
            : Fail(Test, State, FString::Printf(TEXT("Chapter %d cannot reach %d defeats with site mask %d"),
                GameMode->Campaign()->ChapterId, StopKills, StopMask));
        if (!bOk)
            return false;
    }
    return Fail(Test, State, TEXT("Chapter exceeded its action budget"));
}

bool CompleteDojoLessons(FAutomationTestBase& Test, FState& State)
{
    ASoraGameMode* GameMode = Mode(State);
    const TArray<ASoraEnemy*> Pupils = LiveEnemies(State);
    if (Pupils.IsEmpty())
        return Fail(Test, State, TEXT("Dojo has no sparring pupils"));
    // A pupil cannot be scored until all four forms are complete.
    UGameplayStatics::ApplyDamage(Pupils[0], Pupils[0]->Health, Player(State)->GetController(), Player(State), UDamageType::StaticClass());
    bool bOk = Test.TestEqual(TEXT("Untrained strike does not score a bout"), GameMode->Campaign()->Kills, 0);
    bOk &= Test.TestTrue(TEXT("Untrained strike leaves the pupil standing"), Pupils[0]->IsAlive());
    using SoraDojoRules::EAction;
    bOk &= Test.TestFalse(TEXT("Forms are taught in order"), GameMode->Campaign()->RecordDojoLesson(EAction::Guard, SoraDojoRules::GuardHoldMs));
    bOk &= Test.TestFalse(TEXT("Short stance is rejected"), GameMode->Campaign()->RecordDojoLesson(EAction::Stance, SoraDojoRules::StanceHoldMs - 1));
    bOk &= Test.TestTrue(TEXT("Stance"), GameMode->Campaign()->RecordDojoLesson(EAction::Stance, SoraDojoRules::StanceHoldMs));
    bOk &= Test.TestFalse(TEXT("Guard must face the attacker"), GameMode->Campaign()->RecordDojoLesson(EAction::Guard, SoraDojoRules::GuardHoldMs, false));
    bOk &= Test.TestTrue(TEXT("Guard"), GameMode->Campaign()->RecordDojoLesson(EAction::Guard, SoraDojoRules::GuardHoldMs));
    bOk &= Test.TestFalse(TEXT("Late parry is rejected"), GameMode->Campaign()->RecordDojoLesson(EAction::Parry, SoraDojoRules::ParryWindowMs + 1));
    bOk &= Test.TestTrue(TEXT("Parry"), GameMode->Campaign()->RecordDojoLesson(EAction::Parry, SoraDojoRules::ParryWindowMs));
    bOk &= Test.TestFalse(TEXT("Recovery needs a committed swing"), GameMode->Campaign()->RecordDojoLesson(EAction::Recovery, 500, true, 0));
    bOk &= Test.TestTrue(TEXT("Recovery"), GameMode->Campaign()->RecordDojoLesson(EAction::Recovery, 500, true, 450));
    bOk &= Test.TestTrue(TEXT("Bouts may be scored after four forms"), GameMode->Campaign()->CanScoreDojoBout());
    if (!bOk)
        return Fail(Test, State, TEXT("Nyaagyushinkageryuu lessons did not follow the dojo rules"));
    return ExpectSaved(Test, State, TEXT("Dojo lessons")) && Advance(Test, State);
}

// A fresh chapter opens on its title card: the chapter's Japanese and English
// title, narrative and objective. It holds the round timer and dialogue and
// blocks combat until Enter skips it.
bool DismissTitleCard(FAutomationTestBase& Test, FState& State)
{
    if (!Advance(Test, State, 30))
        return false;
    ASoraGameMode* GameMode = Mode(State);
    const FSoraChapter& Data = FSoraCatalog::Get().Chapter(GameMode->Campaign()->ChapterId);
    const FSoraChapter* Card = GameMode->TitleCardChapter();
    const FString Context = FString::Printf(TEXT("Chapter %d title card"), GameMode->Campaign()->ChapterId);
    bool bOk = Test.TestTrue(*(Context + TEXT(": shown before play")),
        Card == &Data && GameMode->InputState() == SoraInput::Card && !GameMode->IsPlaying());
    bOk &= Test.TestTrue(*(Context + TEXT(": Japanese title, narrative and objective")),
        Card && HasJapanese(Card->Title) && HasJapanese(Card->Narrative) && HasJapanese(Card->Objective));
    bOk &= Test.TestTrue(*(Context + TEXT(": English title, narrative and objective")),
        Card && !Card->TitleEnglish.IsEmpty() && !Card->NarrativeEnglish.IsEmpty() && !Card->ObjectiveEnglish.IsEmpty() &&
        !HasJapanese(Card->TitleEnglish) && !HasJapanese(Card->ObjectiveEnglish));
    bOk &= Test.TestTrue(*(Context + TEXT(": English subtitles are on by default")), GameMode->bEnglishSubtitles);
    bOk &= Test.TestTrue(*(Context + TEXT(": counts down")),
        GameMode->TitleCardTime > 0.f && GameMode->TitleCardTime < ASoraGameMode::TitleCardSeconds);
    bOk &= Test.TestEqual(*(Context + TEXT(": round timer waits")), GameMode->RoundTime, 0.f);
    bOk &= Test.TestNull(*(Context + TEXT(": dialogue waits")), GameMode->Campaign()->CurrentDialogueCue());
    GameMode->BeginRound();
    bOk &= Test.TestTrue(*(Context + TEXT(": Enter skips it into play")),
        GameMode->TitleCardChapter() == nullptr && GameMode->IsPlaying());
    return bOk || Fail(Test, State, Context + TEXT(" was not shown or dismissed"));
}

// A restored checkpoint resumes straight into play without the title card.
bool Resume(FAutomationTestBase& Test, FState& State)
{
    ASoraGameMode* GameMode = Mode(State);
    GameMode->BeginRound();
    bool bOk = Test.TestFalse(TEXT("Enter closes the menu"), GameMode->bMenu);
    bOk &= Test.TestFalse(TEXT("Closing the menu unpauses the world"), Paused(State));
    bOk &= Test.TestNull(TEXT("A resumed checkpoint skips the title card"), GameMode->TitleCardChapter());
    bOk &= Test.TestTrue(TEXT("A resumed checkpoint is in play"), GameMode->IsPlaying());
    return bOk || Fail(Test, State, TEXT("Resuming a checkpoint did not return to play"));
}

bool CheckChapterStart(FAutomationTestBase& Test, FState& State, int32 Chapter)
{
    const ASoraGameMode* GameMode = Mode(State);
    const FSoraChapter& Data = FSoraCatalog::Get().Chapter(Chapter);
    bool bOk = Test.TestEqual(TEXT("Chapter"), GameMode->Campaign()->ChapterId, Chapter);
    bOk &= Test.TestTrue(TEXT("Campaign mode"), GameMode->bCampaign && !GameMode->bDeterministicPractice);
    bOk &= Test.TestEqual(TEXT("Chapter uses its cataloged map"), GameMode->MapId, Data.Map);
    bOk &= Test.TestEqual(TEXT("Chapter defeat goal"), GameMode->Campaign()->KillsNeeded, Data.Kills);
    bOk &= Test.TestEqual(TEXT("New chapter starts with no defeats"), GameMode->Campaign()->Kills, 0);
    bOk &= Test.TestEqual(TEXT("New chapter starts with no sites"), ActivatedMask(*GameMode), 0);
    bOk &= Test.TestFalse(TEXT("New chapter is incomplete"), GameMode->bChapterComplete);
    bOk &= Test.TestEqual(TEXT("New chapter spawns its first wave"), LiveEnemies(State).Num(), FMath::Min(4, Data.Kills));
    return bOk || Fail(Test, State, FString::Printf(TEXT("Chapter %d did not start cleanly"), Chapter));
}

bool ReachExit(FAutomationTestBase& Test, FState& State)
{
    ASoraGameMode* GameMode = Mode(State);
    InteractAt(State, GameMode->Arena()->ExitPoint());
    if (!Test.TestTrue(*FString::Printf(TEXT("Chapter %d completes at the torii"), GameMode->Campaign()->ChapterId), GameMode->bChapterComplete))
        return Fail(Test, State, TEXT("Exit did not complete the chapter"));
    const USoraSaveGame* Saved = Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(State.Slot, 0));
    if (Saved)
        Test.TestEqual(TEXT("Highest unlocked chapter"), Saved->HighestChapter, FMath::Min(LastChapter, GameMode->Campaign()->ChapterId + 1));
    return ExpectSaved(Test, State, FString::Printf(TEXT("Chapter %d exit"), GameMode->Campaign()->ChapterId)) && Advance(Test, State);
}

// Finish the current chapter and press Enter, as the completion notice asks.
bool FinishChapter(FAutomationTestBase& Test, FState& State)
{
    ASoraGameMode* GameMode = Mode(State);
    const int32 Chapter = GameMode->Campaign()->ChapterId;
    if (!AdvanceTo(Test, State, GameMode->Campaign()->KillsNeeded, 7) || !ReachExit(Test, State))
        return false;
    GameMode->BeginRound();
    ++State.ChaptersCompleted;
    const USoraSaveGame* Saved = Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(State.Slot, 0));
    if (!Test.TestNotNull(TEXT("Chapter advance is saved"), Saved))
        return Fail(Test, State, TEXT("Chapter advance was not saved"));
    Test.TestEqual(TEXT("Advancing clears the chapter checkpoint"), Saved->CheckpointChapter, -1);
    if (Chapter == LastChapter)
    {
        bool bOk = Test.TestTrue(TEXT("Final Enter liberates the campaign"), GameMode->Campaign()->bCampaignComplete);
        bOk &= Test.TestTrue(TEXT("Liberation returns to the menu"), GameMode->bMenu);
        bOk &= Test.TestTrue(TEXT("The liberation menu pauses the world"), Paused(State));
        bOk &= Test.TestTrue(TEXT("Liberation is saved"), Saved->CampaignComplete);
        bOk &= Test.TestEqual(TEXT("Liberated campaign stays on the final chapter"), Saved->CurrentChapter, LastChapter);
        return bOk || Fail(Test, State, TEXT("Campaign liberation was not recorded"));
    }
    bool bOk = Test.TestEqual(TEXT("Enter advances to the next chapter"), GameMode->Campaign()->ChapterId, Chapter + 1);
    bOk &= Test.TestFalse(TEXT("Next chapter starts in play"), GameMode->bMenu);
    bOk &= Test.TestEqual(TEXT("Next chapter is saved"), Saved->CurrentChapter, Chapter + 1);
    bOk &= Test.TestFalse(TEXT("Campaign is not liberated early"), Saved->CampaignComplete);
    if (!bOk)
        return Fail(Test, State, FString::Printf(TEXT("Chapter %d did not advance"), Chapter));
    return CheckChapterStart(Test, State, Chapter + 1) && DismissTitleCard(Test, State) && Advance(Test, State);
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

// Tear the world down and restore the saved checkpoint in a fresh one.
bool Reload(FAutomationTestBase& Test, FState& State)
{
    const ASoraGameMode* GameMode = Mode(State);
    const int32 Chapter = GameMode->Campaign()->ChapterId;
    const int32 Kills = GameMode->Campaign()->Kills;
    const int32 Mask = ActivatedMask(*GameMode);
    const int32 LessonStage = GameMode->Campaign()->DojoLessonStage();
    const bool bComplete = GameMode->bChapterComplete;
    const bool bLiberated = GameMode->Campaign()->bCampaignComplete;
    if (!StopWorld(Test, State) || !StartWorld(Test, State))
        return false;
    GameMode = Mode(State);
    const FString Context = FString::Printf(TEXT("Reloaded chapter %d"), Chapter);
    bool bOk = Test.TestEqual(*(Context + TEXT(": chapter")), GameMode->Campaign()->ChapterId, Chapter);
    bOk &= Test.TestEqual(*(Context + TEXT(": defeats")), GameMode->Campaign()->Kills, Kills);
    bOk &= Test.TestEqual(*(Context + TEXT(": sites")), ActivatedMask(*GameMode), Mask);
    bOk &= Test.TestEqual(*(Context + TEXT(": dojo lessons")), GameMode->Campaign()->DojoLessonStage(), LessonStage);
    bOk &= Test.TestEqual(*(Context + TEXT(": completion")), GameMode->bChapterComplete, bComplete);
    bOk &= Test.TestEqual(*(Context + TEXT(": liberation")), GameMode->Campaign()->bCampaignComplete, bLiberated);
    const int32 ExpectedEnemies = bComplete ? 0 : FMath::Min(4, GameMode->Campaign()->KillsNeeded - Kills);
    bOk &= Test.TestEqual(*(Context + TEXT(": remaining opponents respawn")), LiveEnemies(State).Num(), ExpectedEnemies);
    return bOk || Fail(Test, State, Context + TEXT(" did not match its checkpoint"));
}

bool DefeatAndRetry(FAutomationTestBase& Test, FState& State)
{
    ASoraGameMode* GameMode = Mode(State);
    ASoraPlayerCharacter* Hero = Player(State);
    const TArray<ASoraEnemy*> Enemies = LiveEnemies(State);
    if (Enemies.IsEmpty())
        return Fail(Test, State, TEXT("No opponent available to defeat the hero"));
    const int32 Kills = GameMode->Campaign()->Kills;
    const int32 Mask = ActivatedMask(*GameMode);
    UGameplayStatics::ApplyDamage(Hero, Hero->Health, nullptr, Enemies[0], UDamageType::StaticClass());
    if (!Test.TestTrue(TEXT("Lethal damage defeats the hero"), GameMode->bDefeated))
        return Fail(Test, State, TEXT("Hero defeat was not recorded"));
    GameMode->BeginRound();
    bool bOk = Test.TestFalse(TEXT("Enter retries after defeat"), GameMode->bDefeated);
    bOk &= Test.TestNull(TEXT("A retry from a checkpoint skips the title card"), GameMode->TitleCardChapter());
    bOk &= Test.TestEqual(TEXT("Retry keeps checkpoint defeats"), GameMode->Campaign()->Kills, Kills);
    bOk &= Test.TestEqual(TEXT("Retry keeps restored sites"), ActivatedMask(*GameMode), Mask);
    bOk &= Test.TestTrue(TEXT("Retry restores the hero"), Hero->IsAlive() && Hero->Health == Hero->MaxHealth);
    bOk &= Test.TestEqual(TEXT("Retry respawns remaining opponents"), LiveEnemies(State).Num(),
        FMath::Min(4, GameMode->Campaign()->KillsNeeded - Kills));
    return (bOk || Fail(Test, State, TEXT("Retry did not restore the checkpoint"))) && Advance(Test, State);
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
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()) ||
        !TestEqual(TEXT("Eight campaign chapters"), FSoraCatalog::Get().Chapters.Num(), LastChapter + 1))
        return false;
    for (int32 Chapter = 0; Chapter <= LastChapter; ++Chapter)
        if (!TestEqual(*FString::Printf(TEXT("Chapter %d has three production sites"), Chapter),
            FSoraCatalog::Get().Chapter(Chapter).Sites.Num(), 3))
            return false;
    FSoraAutomationWorld::IgnoreMissingGeneratedArt(*this);
    const FStateRef State = MakeShared<FState>();
    FSoraAutomationWorld::IgnoreAbsentSaveSlot(*this, State->Slot);

    Step(this, State, [](FAutomationTestBase& Test, FState& S)
    {
        if (!Test.TestFalse(TEXT("Isolated save slot starts empty"), UGameplayStatics::DoesSaveGameExist(S.Slot, 0)))
            return Fail(Test, S, TEXT("Automation save slot already exists"));
        if (!StartWorld(Test, S) || !CheckChapterStart(Test, S, 0))
            return false;
        Mode(S)->BeginRound();
        return Test.TestFalse(TEXT("Enter starts the dojo"), Mode(S)->bMenu) &&
            Test.TestFalse(TEXT("Closing the menu unpauses the world"), Paused(S)) && DismissTitleCard(Test, S) &&
            ExpectExitLocked(Test, S) && CompleteDojoLessons(Test, S) && AdvanceTo(Test, S, 2, 3);
    });
    // Mid-dojo: lessons, two bouts and two sites survive world teardown.
    Step(this, State, [](FAutomationTestBase& Test, FState& S)
    {
        if (!Reload(Test, S) || !Test.TestTrue(TEXT("Restored pupils can be scored"), Mode(S)->Campaign()->CanScoreDojoBout()))
            return false;
        return Resume(Test, S) && FinishChapter(Test, S);
    });
    Step(this, State, [](FAutomationTestBase& Test, FState& S)
    {
        return ExpectExitLocked(Test, S) && ExpectSiteRejected(Test, S, 1) && ExpectSiteRejected(Test, S, 0) &&
            AdvanceTo(Test, S, 3, 1) && DefeatAndRetry(Test, S) && FinishChapter(Test, S);
    });
    Step(this, State, [](FAutomationTestBase& Test, FState& S)
    {
        return ExpectExitLocked(Test, S) && FinishChapter(Test, S) && AdvanceTo(Test, S, 5, 1);
    });
    // Mid-field: an ordinary chapter checkpoint survives world teardown.
    Step(this, State, [](FAutomationTestBase& Test, FState& S)
    {
        if (!Reload(Test, S))
            return false;
        return Resume(Test, S) && FinishChapter(Test, S);
    });
    for (int32 Chapter = 4; Chapter < LastChapter; ++Chapter)
        Step(this, State, [](FAutomationTestBase& Test, FState& S)
        {
            return ExpectExitLocked(Test, S) && FinishChapter(Test, S);
        });
    Step(this, State, [](FAutomationTestBase& Test, FState& S)
    {
        if (!ExpectExitLocked(Test, S) || !AdvanceTo(Test, S, 17, 3))
            return false;
        const ASoraBoss* Boss = Mode(S)->Campaign()->CampaignBoss();
        return (Test.TestNotNull(TEXT("Collector arrives after seventeen guards"), Boss) &&
            Test.TestEqual(TEXT("Only the collector remains"), LiveEnemies(S).Num(), 1)) ||
            Fail(Test, S, TEXT("Final boss did not arrive"));
    });
    // Pre-boss: the collector returns at full health in a fresh world.
    Step(this, State, [](FAutomationTestBase& Test, FState& S)
    {
        if (!Reload(Test, S))
            return false;
        const ASoraBoss* Boss = Mode(S)->Campaign()->CampaignBoss();
        if (!Test.TestNotNull(TEXT("Restored checkpoint respawns the collector"), Boss) ||
            !Test.TestEqual(TEXT("Collector returns at full health"), Boss->Health, Boss->MaxHealth))
            return Fail(Test, S, TEXT("Final boss checkpoint was not restored"));
        if (!Resume(Test, S) || !DefeatOne(Test, S) || !Test.TestNull(TEXT("Collector defeated"), Mode(S)->Campaign()->CampaignBoss()))
            return Fail(Test, S, TEXT("Collector was not defeated"));
        return FinishChapter(Test, S);
    });
    // Liberation is durable: a fresh world shows the freed city, not a new battle.
    Step(this, State, [](FAutomationTestBase& Test, FState& S)
    {
        if (!Reload(Test, S))
            return false;
        const ASoraGameMode* GameMode = Mode(S);
        bool bOk = Test.TestTrue(TEXT("Reloaded campaign is liberated"), GameMode->Campaign()->bCampaignComplete);
        bOk &= Test.TestEqual(TEXT("Liberated city shows every defeat"), GameMode->Campaign()->Kills, GameMode->Campaign()->KillsNeeded);
        bOk &= Test.TestEqual(TEXT("Liberated city shows every site"), ActivatedMask(*GameMode), 7);
        bOk &= Test.TestTrue(TEXT("Liberated city keeps its exit open"), GameMode->bChapterComplete);
        return bOk || Fail(Test, S, TEXT("Liberation did not survive reload"));
    });
    Step(this, State, [](FAutomationTestBase& Test, FState& S)
    {
        if (!StopWorld(Test, S))
            return false;
        Test.TestEqual(TEXT("All eight chapters completed"), S.ChaptersCompleted, LastChapter + 1);
        FSoraAutomationWorld::DeleteSaveSlot(S.Slot);
        Test.TestFalse(TEXT("Isolated save slot removed"), UGameplayStatics::DoesSaveGameExist(S.Slot, 0));
        UE_LOG(LogTemp, Display, TEXT("SORA_CAMPAIGN_PLAYTHROUGH_OK: chapters=%d worlds=%d"), S.ChaptersCompleted, S.WorldsStarted);
        return true;
    });
    return true;
}
#endif
