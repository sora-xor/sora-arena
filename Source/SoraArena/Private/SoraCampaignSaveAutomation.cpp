#include "SoraSaveGame.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "SoraAutomationWorld.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraGameMode.h"
#include "SoraWorldBuilder.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/AutomationTest.h"
#include "Misc/Guid.h"
#include "Misc/ScopeExit.h"
#include "Templates/UniquePtr.h"

namespace SoraCampaignSaveTests
{
void Copy(const USoraSaveGame& From, USoraSaveGame& To)
{
    To.SaveSchema = From.SaveSchema; To.CurrentChapter = From.CurrentChapter; To.HighestChapter = From.HighestChapter;
    To.SelectedClass = From.SelectedClass; To.CampaignComplete = From.CampaignComplete; To.EnglishSubtitles = From.EnglishSubtitles;
    To.ChapterEntryWeapons = From.ChapterEntryWeapons; To.ChapterEntryMechanics = From.ChapterEntryMechanics;
    To.ChapterEntryFlags = From.ChapterEntryFlags;
    To.Collectibles = From.Collectibles; To.CheckpointChapter = From.CheckpointChapter; To.CheckpointBeat = From.CheckpointBeat;
    To.CheckpointPhase = From.CheckpointPhase; To.CheckpointBeatsMask = From.CheckpointBeatsMask;
    To.CheckpointSitesMask = From.CheckpointSitesMask; To.CheckpointWeapons = From.CheckpointWeapons;
    To.CheckpointMechanics = From.CheckpointMechanics; To.CheckpointFlags = From.CheckpointFlags;
    To.CheckpointComplete = From.CheckpointComplete;
    To.CheckpointDojoLessonMask = From.CheckpointDojoLessonMask;
}
bool Same(FAutomationTestBase& Test, const FString& Context, const USoraSaveGame& A, const USoraSaveGame& B)
{
    bool bOk = Test.TestEqual(*(Context + TEXT(": schema")), A.SaveSchema, B.SaveSchema);
    bOk &= Test.TestEqual(*(Context + TEXT(": chapter")), A.CurrentChapter, B.CurrentChapter);
    bOk &= Test.TestEqual(*(Context + TEXT(": highest chapter")), A.HighestChapter, B.HighestChapter);
    bOk &= Test.TestEqual(*(Context + TEXT(": class")), A.SelectedClass, B.SelectedClass);
    bOk &= Test.TestEqual(*(Context + TEXT(": liberation")), A.CampaignComplete, B.CampaignComplete);
    bOk &= Test.TestEqual(*(Context + TEXT(": English subtitles")), A.EnglishSubtitles, B.EnglishSubtitles);
    bOk &= Test.TestEqual(*(Context + TEXT(": entry weapons")), A.ChapterEntryWeapons, B.ChapterEntryWeapons);
    bOk &= Test.TestEqual(*(Context + TEXT(": entry mechanics")), A.ChapterEntryMechanics, B.ChapterEntryMechanics);
    bOk &= Test.TestEqual(*(Context + TEXT(": entry story flags")), A.ChapterEntryFlags, B.ChapterEntryFlags);
    bOk &= Test.TestEqual(*(Context + TEXT(": collectibles")), A.Collectibles, B.Collectibles);
    bOk &= Test.TestEqual(*(Context + TEXT(": checkpoint chapter")), A.CheckpointChapter, B.CheckpointChapter);
    bOk &= Test.TestEqual(*(Context + TEXT(": checkpoint beat")), A.CheckpointBeat, B.CheckpointBeat);
    bOk &= Test.TestEqual(*(Context + TEXT(": checkpoint phase")), A.CheckpointPhase, B.CheckpointPhase);
    bOk &= Test.TestEqual(*(Context + TEXT(": beats done")), A.CheckpointBeatsMask, B.CheckpointBeatsMask);
    bOk &= Test.TestEqual(*(Context + TEXT(": sites")), A.CheckpointSitesMask, B.CheckpointSitesMask);
    bOk &= Test.TestEqual(*(Context + TEXT(": weapons")), A.CheckpointWeapons, B.CheckpointWeapons);
    bOk &= Test.TestEqual(*(Context + TEXT(": mechanics")), A.CheckpointMechanics, B.CheckpointMechanics);
    bOk &= Test.TestEqual(*(Context + TEXT(": story flags")), A.CheckpointFlags, B.CheckpointFlags);
    bOk &= Test.TestEqual(*(Context + TEXT(": completion")), A.CheckpointComplete, B.CheckpointComplete);
    bOk &= Test.TestEqual(*(Context + TEXT(": dojo lessons")), A.CheckpointDojoLessonMask, B.CheckpointDojoLessonMask);
    return bOk;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraCampaignSaveRoundTripTest,
    "SoraArena.Campaign.SaveRoundTrip",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FSoraCampaignSaveRoundTripTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    // Chapter one at the start of its third lesson duel: the stance, guard,
    // parry and recovery forms taught, two sites restored, and collectibles
    // from the first and last chapters.
    USoraSaveGame* Original = NewObject<USoraSaveGame>();
    if (!TestTrue(TEXT("A valid dojo checkpoint is seeded"), USoraCampaignDirector::SeedCheckpoint(*Original, 0, 3)))
        return false;
    Original->HighestChapter = 7;
    Original->Collectibles = static_cast<int64>(1ull << 47 | 1ull << 3);
    Original->EnglishSubtitles = false;
    TestEqual(TEXT("Seeded schema"), Original->SaveSchema, USoraSaveGame::Schema);
    TestEqual(TEXT("Seeded dojo forms"), Original->CheckpointDojoLessonMask, 15);
    TestEqual(TEXT("Seeded sites"), Original->CheckpointSitesMask, 3);

    TArray<uint8> Bytes;
    if (!TestTrue(TEXT("Campaign checkpoint serializes"), UGameplayStatics::SaveGameToMemory(Original, Bytes)))
        return false;
    USoraSaveGame* Restored = Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromMemory(Bytes));
    if (!TestNotNull(TEXT("Campaign checkpoint restores as USoraSaveGame"), Restored))
        return false;
    SoraCampaignSaveTests::Same(*this, TEXT("Round trip"), *Restored, *Original);
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraCampaignDiskSaveRecoveryTest,
    "SoraArena.Campaign.DiskSaveRecovery",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FSoraCampaignDiskSaveRecoveryTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    // Never use the player's SoraSoloCampaign slot. A fresh name also keeps
    // concurrent editor test runs from overwriting one another.
    const FString SlotName = FString(TEXT("SoraArenaAutomation_CampaignDiskRecovery_"))
        + FGuid::NewGuid().ToString(EGuidFormats::Digits);
    constexpr int32 UserIndex = 0;
    struct FDiskCheckpoint
    {
        const TCHAR* Name;
        int32 Chapter;
        int32 Beat;
        int32 Phase;
        bool bEnglishSubtitles;
    };
    // The dojo smithy, an irrigation weir, a boss saved at its third phase,
    // and the final chapter's last production task (carrying ch07's story flag).
    const FDiskCheckpoint Cases[] = {
        {TEXT("Dojo smithy"), 0, 8, 0, false},
        {TEXT("Irrigation weir"), 3, 5, 0, true},
        {TEXT("Dunark's third phase"), 1, 14, 2, true},
        {TEXT("Registry to the notice board"), 7, 15, 0, false},
    };

    bool bCleanupAttempted = false;
    {
        ON_SCOPE_EXIT
        {
            bCleanupAttempted = true;
            if (UGameplayStatics::DoesSaveGameExist(SlotName, UserIndex))
                UGameplayStatics::DeleteGameInSlot(SlotName, UserIndex);
        };
        TestFalse(TEXT("Unique disk test slot starts empty"), UGameplayStatics::DoesSaveGameExist(SlotName, UserIndex));
        for (const FDiskCheckpoint& Case : Cases)
        {
            const FString Name(Case.Name);
            USoraSaveGame* Original = NewObject<USoraSaveGame>();
            if (!TestTrue(*(Name + TEXT(": seeds a valid checkpoint")),
                USoraCampaignDirector::SeedCheckpoint(*Original, Case.Chapter, Case.Beat, Case.Phase)))
                continue;
            Original->EnglishSubtitles = Case.bEnglishSubtitles;
            Original->Collectibles = static_cast<int64>(1ull << (Case.Chapter * 6));
            if (!TestTrue(*(Name + TEXT(": writes disk slot")), UGameplayStatics::SaveGameToSlot(Original, SlotName, UserIndex)))
                continue;
            USoraSaveGame* Expected = NewObject<USoraSaveGame>();
            SoraCampaignSaveTests::Copy(*Original, *Expected);
            // Change the source after saving so equality cannot come from the
            // in-memory instance instead of the slot.
            Original->CheckpointBeatsMask = -1;
            Original->EnglishSubtitles = !Case.bEnglishSubtitles;
            USoraSaveGame* Restored = Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(SlotName, UserIndex));
            if (!TestNotNull(*(Name + TEXT(": loads USoraSaveGame")), Restored))
                continue;
            TestTrue(*(Name + TEXT(": new object from disk")), Restored != Original);
            SoraCampaignSaveTests::Same(*this, Name, *Restored, *Expected);
            if (Case.Chapter == 7)
                TestTrue(*(Name + TEXT(": the name board's story flag is carried")), Restored->CheckpointFlags != 0);
        }
    }
    TestTrue(TEXT("Disk test cleanup executed"), bCleanupAttempted);
    TestFalse(TEXT("Disk test slot removed after all assertions"), UGameplayStatics::DoesSaveGameExist(SlotName, UserIndex));
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraCampaignForgedSaveTest,
    "SoraArena.Campaign.ForgedSaves",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

// Each save is written to an isolated slot and loaded by a real game world.
// The director restores the valid checkpoints exactly and refuses every
// forgery: a stale schema, or a chapter, unlock, story flag or collectible no
// route reaches, starts a fresh campaign; an unearned checkpoint replays the
// saved chapter from its opening.
bool FSoraCampaignForgedSaveTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FSoraAutomationWorld::IgnoreMissingGeneratedArt(*this);
    enum class EOutcome { Restored, ChapterStart, FreshCampaign };
    struct FCase
    {
        const TCHAR* Name;
        int32 Chapter;
        int32 Beat;
        int32 Phase;
        TFunction<void(USoraSaveGame&)> Forge;
        EOutcome Outcome;
    };
    const int32 MutoDori = FSoraCatalog::Get().Mechanics.Find(TEXT("muto_dori"));
    const TArray<FCase> Cases = {
        {TEXT("Valid ledger-vault checkpoint"), 5, 7, 0, [](USoraSaveGame&) {}, EOutcome::Restored},
        {TEXT("Valid boss phase"), 1, 14, 1, [](USoraSaveGame&) {}, EOutcome::Restored},
        {TEXT("Valid final-chapter checkpoint with a story flag"), 7, 3, 0, [](USoraSaveGame&) {}, EOutcome::Restored},
        {TEXT("Schema-5 save"), 5, 7, 0, [](USoraSaveGame& Save) { Save.SaveSchema = 5; }, EOutcome::FreshCampaign},
        {TEXT("Entry weapon from a later chapter"), 2, 4, 0,
            [](USoraSaveGame& Save) { Save.ChapterEntryWeapons |= 1 << 17; }, EOutcome::FreshCampaign},
        {TEXT("Entry mechanic from a later chapter"), 2, 4, 0,
            [MutoDori](USoraSaveGame& Save) { Save.ChapterEntryMechanics |= 1 << MutoDori; }, EOutcome::FreshCampaign},
        {TEXT("Story flag no earlier chapter sets"), 2, 4, 0,
            [](USoraSaveGame& Save) { Save.ChapterEntryFlags |= 1; }, EOutcome::FreshCampaign},
        {TEXT("Collectible from an unreached chapter"), 2, 4, 0,
            [](USoraSaveGame& Save) { Save.Collectibles = static_cast<int64>(1ull << 40); }, EOutcome::FreshCampaign},
        {TEXT("Chapter beyond the reach"), 4, 3, 0, [](USoraSaveGame& Save) { Save.HighestChapter = 3; }, EOutcome::FreshCampaign},
        {TEXT("Unearned weapon at the checkpoint"), 5, 7, 0,
            [](USoraSaveGame& Save) { Save.CheckpointWeapons |= 1 << 12; }, EOutcome::ChapterStart},
        {TEXT("Unearned story flag at the checkpoint"), 6, 3, 0,
            [](USoraSaveGame& Save) { Save.CheckpointFlags |= 1; }, EOutcome::ChapterStart},
        {TEXT("Unearned site at the checkpoint"), 5, 7, 0,
            [](USoraSaveGame& Save) { Save.CheckpointSitesMask |= 4; }, EOutcome::ChapterStart},
        {TEXT("Beat saved without its requirements"), 5, 7, 0,
            [](USoraSaveGame& Save) { Save.CheckpointBeatsMask &= ~1; }, EOutcome::ChapterStart},
        // ch02.b04 is a dialogue beat that takes no checkpoint of its own.
        {TEXT("Checkpoint at a beat that saves none"), 1, 4, 0,
            [](USoraSaveGame& Save) { Save.CheckpointBeat = 3; Save.CheckpointBeatsMask &= ~(1 << 3); }, EOutcome::ChapterStart},
        {TEXT("Phase beyond the boss's saves"), 1, 14, 0,
            [](USoraSaveGame& Save) { Save.CheckpointPhase = 3; }, EOutcome::ChapterStart},
        {TEXT("Premature chapter completion"), 5, 7, 0,
            [](USoraSaveGame& Save) { Save.CheckpointBeat = -1; Save.CheckpointComplete = true; }, EOutcome::ChapterStart},
        {TEXT("Dojo form never taught"), 0, 2, 0,
            [](USoraSaveGame& Save) { Save.CheckpointDojoLessonMask = 3; }, EOutcome::ChapterStart},
    };
    for (const FCase& Case : Cases)
    {
        const FString Name(Case.Name);
        const FString Slot = FSoraAutomationWorld::UniqueSaveSlot(TEXT("ForgedSave"));
        FSoraAutomationWorld::IgnoreAbsentSaveSlot(*this, Slot);
        ON_SCOPE_EXIT { FSoraAutomationWorld::DeleteSaveSlot(Slot); };
        USoraSaveGame* Seed = Cast<USoraSaveGame>(UGameplayStatics::CreateSaveGameObject(USoraSaveGame::StaticClass()));
        if (!TestNotNull(*(Name + TEXT(": save object")), Seed) ||
            !TestTrue(*(Name + TEXT(": seeds")), USoraCampaignDirector::SeedCheckpoint(*Seed, Case.Chapter, Case.Beat, Case.Phase)))
            continue;
        Case.Forge(*Seed);
        if (!TestTrue(*(Name + TEXT(": written")), UGameplayStatics::SaveGameToSlot(Seed, Slot, 0)))
            continue;
        TUniquePtr<FSoraAutomationWorld> World = MakeUnique<FSoraAutomationWorld>();
        if (!World->Start(Slot) || !World->Tick(1))
        {
            World->ForwardErrorMessages(this);
            AddError(Name + TEXT(": world did not start"));
            continue;
        }
        const ASoraGameMode* Mode = World->Mode();
        const USoraCampaignDirector* Campaign = Mode ? Mode->Campaign() : nullptr;
        if (!TestNotNull(*(Name + TEXT(": campaign director")), Campaign) || !TestNotNull(*(Name + TEXT(": arena")), Mode->Arena()))
            continue;
        switch (Case.Outcome)
        {
        case EOutcome::Restored:
            TestEqual(*(Name + TEXT(": chapter")), Campaign->ChapterId, Case.Chapter);
            TestEqual(*(Name + TEXT(": beat")), Campaign->ActiveBeat(), Case.Beat);
            TestEqual(*(Name + TEXT(": phase")), Campaign->ActivePhase(), Case.Phase);
            TestEqual(*(Name + TEXT(": beats done")), static_cast<int32>(Campaign->Progress().CompletedMask), Seed->CheckpointBeatsMask);
            TestEqual(*(Name + TEXT(": weapons")), static_cast<int32>(Campaign->Progress().WeaponsMask), Seed->CheckpointWeapons);
            TestEqual(*(Name + TEXT(": story flags")), static_cast<int32>(Campaign->Progress().FlagsMask), Seed->CheckpointFlags);
            TestEqual(*(Name + TEXT(": sites")), Mode->Arena()->ActivatedMask(), Seed->CheckpointSitesMask);
            break;
        case EOutcome::ChapterStart:
            TestEqual(*(Name + TEXT(": chapter kept")), Campaign->ChapterId, Case.Chapter);
            TestEqual(*(Name + TEXT(": replays from the opening")), Campaign->ActiveBeat(), 0);
            TestEqual(*(Name + TEXT(": no beats done")), static_cast<int32>(Campaign->Progress().CompletedMask), 0);
            TestEqual(*(Name + TEXT(": only the entry weapons")), static_cast<int32>(Campaign->Progress().WeaponsMask), Seed->ChapterEntryWeapons);
            TestEqual(*(Name + TEXT(": only the entry story flags")), static_cast<int32>(Campaign->Progress().FlagsMask), Seed->ChapterEntryFlags);
            TestEqual(*(Name + TEXT(": no sites")), Mode->Arena()->ActivatedMask(), 0);
            break;
        case EOutcome::FreshCampaign:
            TestEqual(*(Name + TEXT(": back to the dojo")), Campaign->ChapterId, 0);
            TestEqual(*(Name + TEXT(": no reach")), Campaign->HighestChapter(), 0);
            TestEqual(*(Name + TEXT(": no weapons")), static_cast<int32>(Campaign->Progress().WeaponsMask), 0);
            TestEqual(*(Name + TEXT(": no collectibles")), static_cast<int64>(Campaign->CollectedMask()), static_cast<int64>(0));
            break;
        }
        World->DestroyTestWorld(true);
        World->ForwardErrorMessages(this);
    }
    return !HasAnyErrors();
}
#endif
