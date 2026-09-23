#include "SoraSaveGame.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Kismet/GameplayStatics.h"
#include "Misc/AutomationTest.h"
#include "Misc/Guid.h"
#include "Misc/ScopeExit.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraCampaignSaveRoundTripTest,
    "SoraArena.Campaign.SaveRoundTrip",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FSoraCampaignSaveRoundTripTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    USoraSaveGame* Original = NewObject<USoraSaveGame>();
    Original->SaveSchema = 5;
    Original->CurrentChapter = 0;
    Original->HighestChapter = 3;
    Original->SelectedClass = 0;
    Original->CampaignComplete = false;
    Original->EnglishSubtitles = true;
    Original->CheckpointChapter = 0;
    Original->CheckpointKills = 3;
    Original->CheckpointNodesMask = 3;
    Original->CheckpointComplete = false;
    Original->CheckpointDojoLessonMask = 15;

    TArray<uint8> Bytes;
    if (!TestTrue(TEXT("Campaign checkpoint serializes"),
        UGameplayStatics::SaveGameToMemory(Original, Bytes)))
        return false;
    USoraSaveGame* Restored = Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromMemory(Bytes));
    if (!TestNotNull(TEXT("Campaign checkpoint restores as USoraSaveGame"), Restored))
        return false;

    TestEqual(TEXT("Schema"), Restored->SaveSchema, Original->SaveSchema);
    TestEqual(TEXT("Current chapter"), Restored->CurrentChapter, Original->CurrentChapter);
    TestEqual(TEXT("Highest chapter"), Restored->HighestChapter, Original->HighestChapter);
    TestEqual(TEXT("Selected class"), Restored->SelectedClass, Original->SelectedClass);
    TestEqual(TEXT("Completion"), Restored->CampaignComplete, Original->CampaignComplete);
    TestEqual(TEXT("English subtitles"), Restored->EnglishSubtitles, Original->EnglishSubtitles);
    TestEqual(TEXT("Checkpoint chapter"), Restored->CheckpointChapter, Original->CheckpointChapter);
    TestEqual(TEXT("Defeated pupils"), Restored->CheckpointKills, Original->CheckpointKills);
    TestEqual(TEXT("Restored dojo sites"), Restored->CheckpointNodesMask, Original->CheckpointNodesMask);
    TestEqual(TEXT("Checkpoint completion"), Restored->CheckpointComplete, Original->CheckpointComplete);
    TestEqual(TEXT("Nyaagyushinkageryuu lessons"), Restored->CheckpointDojoLessonMask,
        Original->CheckpointDojoLessonMask);
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraCampaignDiskSaveRecoveryTest,
    "SoraArena.Campaign.DiskSaveRecovery",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FSoraCampaignDiskSaveRecoveryTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    // Never use the player's SoraSoloCampaign slot. A fresh name also keeps
    // concurrent editor test runs from overwriting one another.
    const FString SlotName = FString(TEXT("SoraArenaAutomation_CampaignDiskRecovery_"))
        + FGuid::NewGuid().ToString(EGuidFormats::Digits);
    constexpr int32 UserIndex = 0;
    struct FDiskCheckpoint
    {
        const TCHAR* Name;
        int32 Chapter;
        int32 HighestChapter;
        int32 CheckpointChapter;
        int32 Kills;
        int32 NodesMask;
        int32 DojoLessons;
        bool CheckpointComplete;
        bool CampaignComplete;
        bool EnglishSubtitles;
    };
    const FDiskCheckpoint Cases[] = {
        {TEXT("Dojo Japanese subtitles"), 0, 0, 0, 3, 3, 15, false, false, false},
        {TEXT("Production sites English subtitles"), 3, 3, 3, 10, 7, 0, true, false, true},
        {TEXT("Final boss checkpoint"), 7, 7, 7, 17, 7, 0, false, false, true},
        {TEXT("Liberated campaign"), 7, 7, -1, 0, 0, 0, false, true, false},
    };

    bool bCleanupAttempted = false;
    {
        ON_SCOPE_EXIT
        {
            bCleanupAttempted = true;
            if (UGameplayStatics::DoesSaveGameExist(SlotName, UserIndex))
                UGameplayStatics::DeleteGameInSlot(SlotName, UserIndex);
        };
        TestFalse(TEXT("Unique disk test slot starts empty"),
            UGameplayStatics::DoesSaveGameExist(SlotName, UserIndex));

        for (const FDiskCheckpoint& Case : Cases)
        {
            USoraSaveGame* Original = NewObject<USoraSaveGame>();
            if (!TestNotNull(*(FString(Case.Name) + TEXT(": created save")), Original))
                continue;
            Original->SaveSchema = 5;
            Original->CurrentChapter = Case.Chapter;
            Original->HighestChapter = Case.HighestChapter;
            Original->SelectedClass = 0;
            Original->CampaignComplete = Case.CampaignComplete;
            Original->EnglishSubtitles = Case.EnglishSubtitles;
            Original->CheckpointChapter = Case.CheckpointChapter;
            Original->CheckpointKills = Case.Kills;
            Original->CheckpointNodesMask = Case.NodesMask;
            Original->CheckpointComplete = Case.CheckpointComplete;
            Original->CheckpointDojoLessonMask = Case.DojoLessons;

            if (!TestTrue(*(FString(Case.Name) + TEXT(": writes disk slot")),
                UGameplayStatics::SaveGameToSlot(Original, SlotName, UserIndex)))
                continue;
            TestTrue(*(FString(Case.Name) + TEXT(": disk slot exists")),
                UGameplayStatics::DoesSaveGameExist(SlotName, UserIndex));

            // Change the source object after saving so equality cannot come
            // from reading that in-memory instance instead of the slot.
            Original->CheckpointKills = -1;
            Original->EnglishSubtitles = !Case.EnglishSubtitles;
            USoraSaveGame* Restored = Cast<USoraSaveGame>(
                UGameplayStatics::LoadGameFromSlot(SlotName, UserIndex));
            if (!TestNotNull(*(FString(Case.Name) + TEXT(": loads USoraSaveGame")), Restored))
                continue;
            TestTrue(*(FString(Case.Name) + TEXT(": new object from disk")), Restored != Original);
            TestEqual(*(FString(Case.Name) + TEXT(": schema")), Restored->SaveSchema, 5);
            TestEqual(*(FString(Case.Name) + TEXT(": chapter")), Restored->CurrentChapter, Case.Chapter);
            TestEqual(*(FString(Case.Name) + TEXT(": highest chapter")), Restored->HighestChapter, Case.HighestChapter);
            TestEqual(*(FString(Case.Name) + TEXT(": samurai class")), Restored->SelectedClass, 0);
            TestEqual(*(FString(Case.Name) + TEXT(": campaign completion")), Restored->CampaignComplete, Case.CampaignComplete);
            TestEqual(*(FString(Case.Name) + TEXT(": English subtitle flag")), Restored->EnglishSubtitles, Case.EnglishSubtitles);
            TestEqual(*(FString(Case.Name) + TEXT(": checkpoint chapter")), Restored->CheckpointChapter, Case.CheckpointChapter);
            TestEqual(*(FString(Case.Name) + TEXT(": checkpoint kills")), Restored->CheckpointKills, Case.Kills);
            TestEqual(*(FString(Case.Name) + TEXT(": site mask")), Restored->CheckpointNodesMask, Case.NodesMask);
            TestEqual(*(FString(Case.Name) + TEXT(": checkpoint completion")), Restored->CheckpointComplete, Case.CheckpointComplete);
            TestEqual(*(FString(Case.Name) + TEXT(": dojo lessons")), Restored->CheckpointDojoLessonMask, Case.DojoLessons);
        }
    }
    TestTrue(TEXT("Disk test cleanup executed"), bCleanupAttempted);
    TestFalse(TEXT("Disk test slot removed after all assertions"),
        UGameplayStatics::DoesSaveGameExist(SlotName, UserIndex));
    return !HasAnyErrors();
}
#endif
