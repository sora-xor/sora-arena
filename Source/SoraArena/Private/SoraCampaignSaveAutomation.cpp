#include "SoraSaveGame.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Kismet/GameplayStatics.h"
#include "Misc/AutomationTest.h"

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
#endif
