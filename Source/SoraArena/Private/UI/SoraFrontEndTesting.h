#pragma once

#if WITH_DEV_AUTOMATION_TESTS
#include "CoreMinimal.h"
#include "SoraAutomationWorld.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraFrontEnd.h"
#include "SoraGameMode.h"
#include "SoraSaveGame.h"
#include "Engine/World.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/AutomationTest.h"
#include "Templates/UniquePtr.h"

// Shared by the front end and settings automation: one device's menu keys,
// and a standalone game world with isolated save, control and settings slots
// that it deletes afterwards. Keys reach USoraFrontEnd as SSoraFrontEnd
// forwards them (FSoraAutomationWorld::InjectKey).
namespace SoraFrontEndTests
{
using SoraUI::EAction;
using SoraUI::EScreen;
constexpr int32 FramesPerSecond = 60;

struct FKeys
{
    FKey Up, Down, Left, Right, Accept, Back, Pause;
    SoraUI::EDevice Device;
    const TCHAR* AcceptLabel;
    const TCHAR* Name;
};
const FKeys Pad{EKeys::Gamepad_DPad_Up, EKeys::Gamepad_DPad_Down, EKeys::Gamepad_DPad_Left, EKeys::Gamepad_DPad_Right,
    EKeys::Gamepad_FaceButton_Bottom, EKeys::Gamepad_FaceButton_Right, EKeys::Gamepad_Special_Right, SoraUI::EDevice::Gamepad, TEXT("A"), TEXT("Pad")};
const FKeys Keyboard{EKeys::Up, EKeys::Down, EKeys::Left, EKeys::Right, EKeys::Enter, EKeys::Escape, EKeys::Escape,
    SoraUI::EDevice::KeyboardMouse, TEXT("Enter"), TEXT("Keyboard")};

struct FScope
{
    FAutomationTestBase& Test;
    FString Slot;
    TUniquePtr<FSoraAutomationWorld> World;
    // Runs after every key Key() presses, to inspect each screen reached.
    TFunction<void()> AfterKey;

    FScope(FAutomationTestBase& InTest, const TCHAR* Purpose)
        : Test(InTest), Slot(FSoraAutomationWorld::UniqueSaveSlot(Purpose))
    {
        FSoraAutomationWorld::IgnoreMissingGeneratedArt(Test);
        FSoraAutomationWorld::IgnoreAbsentSaveSlot(Test, Slot);
    }
    ~FScope()
    {
        if (World)
        {
            World->DestroyTestWorld(true);
            World->ForwardErrorMessages(&Test);
            World.Reset();
        }
        FSoraAutomationWorld::DeleteSaveSlot(Slot);
    }
    // A schema-6 save at Chapter with the reach Highest: a checkpoint at
    // CheckpointBeat (USoraCampaignDirector::SeedCheckpoint), or none, with the
    // entry unlocks the earlier chapters offer.
    bool Seed(int32 Chapter, int32 Highest, int32 CheckpointBeat = INDEX_NONE, bool bComplete = false)
    {
        USoraSaveGame* Save = Cast<USoraSaveGame>(UGameplayStatics::CreateSaveGameObject(USoraSaveGame::StaticClass()));
        if (!Save)
            return false;
        if (CheckpointBeat != INDEX_NONE)
        {
            if (!Test.TestTrue(TEXT("Seed checkpoint is valid"), USoraCampaignDirector::SeedCheckpoint(*Save, Chapter, CheckpointBeat)))
                return false;
        }
        else
        {
            const FSoraCatalog& Catalog = FSoraCatalog::Get();
            Save->SaveSchema = USoraSaveGame::Schema;
            Save->CurrentChapter = Chapter;
            Save->ChapterEntryWeapons = static_cast<int32>(Catalog.EarlierWeapons(Chapter));
            Save->ChapterEntryMechanics = static_cast<int32>(Catalog.EarlierMechanics(Chapter));
            Save->ChapterEntryFlags = static_cast<int32>(Catalog.EarlierFlags(Chapter));
        }
        Save->HighestChapter = Highest;
        Save->CampaignComplete = bComplete;
        return Test.TestTrue(TEXT("Seed campaign saved to the isolated slot"), UGameplayStatics::SaveGameToSlot(Save, Slot, 0));
    }
    bool Start()
    {
        World = MakeUnique<FSoraAutomationWorld>();
        if (!World->Start(Slot) || !World->Tick(1) || !World->EnableKeyInput())
        {
            World->ForwardErrorMessages(&Test);
            Test.AddError(TEXT("Test world did not start with key input"));
            return false;
        }
        return Test.TestNotNull(TEXT("World has ASoraGameMode"), Mode()) && Test.TestNotNull(TEXT("World has its front end"), FrontEnd()) &&
            Test.TestNotNull(TEXT("World has its arena"), Mode()->Arena());
    }
    ASoraGameMode* Mode() const { return World ? World->Mode() : nullptr; }
    USoraFrontEnd* FrontEnd() const { return Mode() ? Mode()->FrontEnd() : nullptr; }
    bool Paused() const { return World && World->GetTestWorld() && World->GetTestWorld()->IsPaused(); }
    bool On(EScreen Screen) const { return FrontEnd()->IsOpen() && FrontEnd()->Screen() == Screen; }
    const SoraUI::FRow* Focused() const
    {
        const TArray<SoraUI::FRow>& Rows = FrontEnd()->Rows();
        return Rows.IsValidIndex(FrontEnd()->Focus()) ? &Rows[FrontEnd()->Focus()] : nullptr;
    }
    void Key(const FKey& Key)
    {
        if (!World->PressKey(Key))
            Test.AddError(FString::Printf(TEXT("Key %s could not be pressed"), *Key.ToString()));
        if (AfterKey)
            AfterKey();
    }
    // Moves down the list to the row with this action and presses Accept.
    bool Choose(const FKeys& Keys, EAction Action, int32 Param = INDEX_NONE)
    {
        for (int32 Step = 0; Step <= FrontEnd()->Rows().Num(); ++Step)
        {
            const SoraUI::FRow* Row = Focused();
            if (Row && Row->Action == Action && (Param == INDEX_NONE || Row->Param == Param))
            {
                Key(Keys.Accept);
                return true;
            }
            Key(Keys.Down);
        }
        Test.AddError(FString::Printf(TEXT("%s: no enabled row for action %d"), Keys.Name, static_cast<int32>(Action)));
        return false;
    }
    // Ends the world and starts a new one on the same slots, as a restart of the game would.
    bool Restart()
    {
        if (World)
        {
            World->DestroyTestWorld(true);
            World->ForwardErrorMessages(&Test);
            World.Reset();
        }
        return Start();
    }
    // Moves to the row with this action and Param without accepting it.
    bool FocusOn(const FKeys& Keys, EAction Action, int32 Param)
    {
        for (int32 Step = 0; Step <= FrontEnd()->Rows().Num(); ++Step)
        {
            if (Focused() && Focused()->Action == Action && Focused()->Param == Param)
                return true;
            Key(Keys.Down);
        }
        Test.AddError(FString::Printf(TEXT("%s: no enabled row for action %d, %d"), Keys.Name, static_cast<int32>(Action), Param));
        return false;
    }
    // From the title: the main menu, Settings, then one settings screen.
    bool OpenSettings(const FKeys& Keys, EAction Screen)
    {
        if (On(EScreen::Title))
            Key(Keys.Accept);
        return Choose(Keys, EAction::Settings) && Choose(Keys, Screen);
    }
    // Moves to the row with this action without accepting it.
    bool FocusOn(const FKeys& Keys, EAction Action)
    {
        for (int32 Step = 0; Step <= FrontEnd()->Rows().Num(); ++Step)
        {
            if (Focused() && Focused()->Action == Action)
                return true;
            Key(Keys.Down);
        }
        Test.AddError(FString::Printf(TEXT("%s: no enabled row for action %d"), Keys.Name, static_cast<int32>(Action)));
        return false;
    }
};

} // namespace SoraFrontEndTests
#endif
