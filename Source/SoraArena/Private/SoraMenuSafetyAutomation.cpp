#include "SoraGameMode.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "SoraAutomationWorld.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraCompanion.h"
#include "SoraControlSaveGame.h"
#include "SoraEnemy.h"
#include "SoraEquipmentComponent.h"
#include "SoraFrontEnd.h"
#include "SoraPlayerCharacter.h"
#include "SoraInputStates.h"
#include "SoraSaveGame.h"
#include "SoraWorldBuilder.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/DamageType.h"
#include "GameFramework/InputSettings.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/AutomationTest.h"
#include "Templates/UniquePtr.h"

// Menu safety, input-state gating, the chapter title card and enemy fire, each
// in a real standalone game world. In play, keys go through UPlayerInput and
// the project's DefaultInput.ini, so these tests cover the key-to-action layer
// that direct handler calls skip. While a front-end screen is open, presses go
// to USoraFrontEnd::HandleKey, the path SSoraFrontEnd forwards them on.
namespace SoraMenuSafety
{
constexpr int32 FramesPerSecond = 60;

struct FScope
{
    FAutomationTestBase& Test;
    FString Slot;
    TUniquePtr<FSoraAutomationWorld> World;

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
    // BeginPlay reads the save; the next tick builds the round and opens the menu.
    bool Start()
    {
        World = MakeUnique<FSoraAutomationWorld>();
        if (!World->Start(Slot) || !World->Tick(1) || !World->EnableKeyInput())
        {
            World->ForwardErrorMessages(&Test);
            Test.AddError(TEXT("Test world did not start with key input"));
            return false;
        }
        return Test.TestNotNull(TEXT("World has ASoraGameMode"), Mode()) && Test.TestNotNull(TEXT("World has the hero"), Player()) &&
            Test.TestNotNull(TEXT("World has its arena"), Mode()->Arena());
    }
    ASoraGameMode* Mode() const { return World ? World->Mode() : nullptr; }
    USoraFrontEnd* FrontEnd() const { return Mode() ? Mode()->FrontEnd() : nullptr; }
    bool On(SoraUI::EScreen Screen) const { return FrontEnd() && FrontEnd()->IsOpen() && FrontEnd()->Screen() == Screen; }
    ASoraPlayerCharacter* Player() const { return World ? World->Player() : nullptr; }
    UWorld* Get() const { return World ? World->GetTestWorld() : nullptr; }
    bool Paused() const { return Get() && Get()->IsPaused(); }
    bool Key(const FKey& Key)
    {
        if (World->PressKey(Key))
            return true;
        Test.AddError(FString::Printf(TEXT("Key %s could not be pressed"), *Key.ToString()));
        return false;
    }
    bool Frames(int32 Count, float DeltaSeconds = 1.f / FramesPerSecond)
    {
        if (World->Tick(Count, DeltaSeconds))
            return true;
        Test.AddError(TEXT("Test world failed to tick"));
        return false;
    }
    // Holds keys straight into play input past an open front end, as if focus
    // had fallen back to the game viewport, checks what they did while still
    // held, then releases them.
    bool HeldPastFrontEnd(std::initializer_list<FKey> Keys, TFunctionRef<bool()> ActedOnNothing)
    {
        for (const FKey& Key : Keys)
            if (!World->InjectKeyPastFrontEnd(Key, IE_Pressed))
                Test.AddError(FString::Printf(TEXT("Key %s could not reach play input"), *Key.ToString()));
        Frames(1);
        const bool bNothing = ActedOnNothing();
        for (const FKey& Key : Keys)
            World->InjectKeyPastFrontEnd(Key, IE_Released);
        Frames(1);
        return bNothing;
    }
    TArray<FVector> OpponentLocations() const
    {
        TArray<FVector> Result;
        for (TActorIterator<ASoraEnemy> It(Get()); It; ++It)
            if (It->IsEnemy())
                Result.Add(It->GetActorLocation());
        return Result;
    }
};

// Seeds the isolated slot with a campaign in progress before the world loads
// it: a chapter entered with every earlier unlock, fresh or at the start of
// CheckpointBeat.
bool WriteSave(FAutomationTestBase& Test, const FString& Slot, int32 Chapter, int32 Highest, int32 CheckpointBeat = INDEX_NONE)
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
        Save->SaveSchema = USoraSaveGame::Schema;
        Save->CurrentChapter = Chapter;
        Save->ChapterEntryWeapons = static_cast<int32>(FSoraCatalog::Get().EarlierWeapons(Chapter));
        Save->ChapterEntryMechanics = static_cast<int32>(FSoraCatalog::Get().EarlierMechanics(Chapter));
    }
    Save->HighestChapter = Highest;
    return Test.TestTrue(TEXT("Seed campaign saved to the isolated slot"), UGameplayStatics::SaveGameToSlot(Save, Slot, 0));
}

bool HasJapanese(const FString& Text)
{
    for (const TCHAR Character : Text)
        if (Character >= 0x3040 && Character <= 0x9FFF)
            return true;
    return false;
}

// Bit order of SoraInput::EState; bit 1 is unused.
FString StateNames(uint8 States)
{
    static const TCHAR* Names[] = {TEXT("Menu"), TEXT("Unused"), TEXT("Card"), TEXT("Play"), TEXT("Result")};
    TArray<FString> Live;
    for (int32 Bit = 0; Bit < UE_ARRAY_COUNT(Names); ++Bit)
        if (States & (1 << Bit))
            Live.Add(Names[Bit]);
    return FString::Join(Live, TEXT("|"));
}

struct FFireRun
{
    TArray<int32> HitFrames;
    int32 Shots = 0;
};

// One ranged invader faces the hero on the road west of the estate gate for
// fifteen seconds; every other opponent is held still.
bool RunFire(FAutomationTestBase& Test, FFireRun& Run)
{
    constexpr int32 ChapterId = 1, ShooterSlot = 1, Frames = 15 * FramesPerSecond;
    FScope Scope(Test, TEXT("EnemyFire"));
    if (!WriteSave(Test, Scope.Slot, ChapterId, ChapterId) || !Scope.Start())
        return false;
    ASoraGameMode* Mode = Scope.Mode();
    ASoraPlayerCharacter* Hero = Scope.Player();
    UWorld* World = Scope.Get();
    Mode->BeginRound();
    Mode->BeginRound();
    if (!Test.TestTrue(TEXT("Enter twice passes the menu and the title card into play"), Mode->IsPlaying()))
        return false;
    ASoraEnemy* Shooter = nullptr;
    for (TActorIterator<ASoraEnemy> It(World); It; ++It)
    {
        if (!It->IsEnemy())
            continue;
        if (It->EnemySlot() == ShooterSlot)
            Shooter = *It;
        else
            It->SetActorTickEnabled(false);
    }
    // The dojo's pupils who stand with the hero here leave the road clear.
    for (TActorIterator<ASoraCompanion> It(World); It; ++It)
        It->Destroy();
    if (!Test.TestNotNull(TEXT("The ranged invader spawned"), Shooter) ||
        !Test.TestFalse(TEXT("It fires rather than duels"), Shooter->IsBladeRetainer()))
        return false;
    const FVector Stand = Mode->Arena()->PlayerStart() + FVector(1100.f, 0.f, 0.f);
    FHitResult Ground;
    FCollisionQueryParams GroundQuery(SCENE_QUERY_STAT(EnemyFireGround), false, Shooter);
    GroundQuery.AddIgnoredActor(Hero);
    if (!Test.TestTrue(TEXT("The road has ground to stand on"), World->LineTraceSingleByChannel(Ground,
        Stand + FVector(0, 0, 2000), Stand - FVector(0, 0, 2000), ECC_Visibility, GroundQuery)))
        return false;
    Shooter->SetActorLocation(Ground.ImpactPoint + FVector(0, 0, 100), false, nullptr, ETeleportType::TeleportPhysics);
    FHitResult Sight;
    World->LineTraceSingleByChannel(Sight, Shooter->GetActorLocation() + FVector(0, 0, 50), Hero->GetActorLocation() + FVector(0, 0, 35),
        ECC_Visibility, FCollisionQueryParams(SCENE_QUERY_STAT(EnemyFireSight), false, Shooter));
    if (!Test.TestTrue(TEXT("The invader can see the hero"), Sight.GetActor() == Hero))
        return false;
    float Health = Hero->Health;
    for (int32 Frame = 0; Frame < Frames; ++Frame)
    {
        if (!Scope.Frames(1) || !Test.TestFalse(TEXT("The hero survives the volley"), Mode->bDefeated))
            return false;
        if (Hero->Health < Health)
        {
            Test.TestEqual(TEXT("Each hit deals the invader's fixed damage"), Health - Hero->Health, static_cast<float>(Shooter->AttackDamage(0)));
            Run.HitFrames.Add(Frame);
            Health = Hero->Health;
        }
    }
    Run.Shots = Shooter->RangedShotsFired();
    int32 Misses = 0;
    for (int32 Shot = 0; Shot < Run.Shots; ++Shot)
        Misses += ASoraEnemy::RangedShotMisses(ShooterSlot, Shot);
    Test.TestTrue(TEXT("Enough shots to exercise the miss pattern"), Run.Shots >= 6);
    return Test.TestEqual(TEXT("Hits follow the fixed miss pattern"), Run.HitFrames.Num(), Run.Shots - Misses);
}
} // namespace SoraMenuSafety

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraNewCampaignConfirmationTest,
    "SoraArena.Menu.NewCampaignConfirmation",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraNewCampaignConfirmationTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraMenuSafety;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FScope Scope(*this, TEXT("NewCampaignConfirmation"));
    // Chapter four at its first weir (ch04.b06), and chapter five reached.
    constexpr int32 Chapter = 3, Highest = 4, Beat = 5;
    if (!WriteSave(*this, Scope.Slot, Chapter, Highest, Beat) || !Scope.Start())
        return false;
    ASoraGameMode* Mode = Scope.Mode();
    if (!TestEqual(TEXT("The saved chapter loads"), Mode->Campaign()->ChapterId, Chapter) ||
        !TestEqual(TEXT("The saved checkpoint loads"), Mode->Campaign()->ActiveBeat(), Beat) || !TestTrue(TEXT("The game opens in the menu"), Mode->bMenu))
        return false;
    const auto Kept = [&](const TCHAR* What)
    {
        const USoraSaveGame* Saved = Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(Scope.Slot, 0));
        return TestTrue(What, Saved && Saved->CurrentChapter == Chapter && Saved->HighestChapter == Highest &&
            Saved->CheckpointChapter == Chapter && Saved->CheckpointBeat == Beat &&
            Mode->Campaign()->ChapterId == Chapter && Mode->Campaign()->ActiveBeat() == Beat);
    };
    USoraFrontEnd* FrontEnd = Scope.FrontEnd();
    if (!TestTrue(TEXT("The game opens on the title screen"), Scope.On(SoraUI::EScreen::Title) && Scope.Paused()))
        return false;
    Scope.Key(EKeys::Enter);
    if (!TestTrue(TEXT("Any key leaves the title for the main menu"), Scope.On(SoraUI::EScreen::Main)) ||
        !TestTrue(TEXT("A saved campaign offers Continue first, then New campaign"), FrontEnd->Rows().Num() > 1 &&
            FrontEnd->Rows()[0].Action == SoraUI::EAction::Continue && FrontEnd->Rows()[1].Action == SoraUI::EAction::NewCampaign))
        return false;

    // Retired hotkeys: the left stick click, N and P mean nothing to the menu.
    for (const FKey& Retired : {EKeys::Gamepad_LeftThumbstick, EKeys::N, EKeys::P})
        Scope.Key(Retired);
    TestTrue(TEXT("Retired menu hotkeys neither prompt nor start practice"), Scope.On(SoraUI::EScreen::Main) && !Mode->bDeterministicPractice);
    // Nor do they reach anything through play input, should focus fall back
    // to the game viewport with the menu open.
    TestTrue(TEXT("Retired hotkeys that reach play input in the menu do nothing either"), Scope.HeldPastFrontEnd(
        {EKeys::Gamepad_LeftThumbstick, EKeys::N, EKeys::P},
        [&]() { return Scope.On(SoraUI::EScreen::Main) && Mode->bMenu && !Mode->bDeterministicPractice; }));
    Kept(TEXT("Retired hotkeys keep the saved campaign"));

    Scope.Key(EKeys::Down);
    Scope.Key(EKeys::Enter);
    TestTrue(TEXT("New campaign only asks for confirmation, starting on Cancel"),
        Scope.On(SoraUI::EScreen::Confirm) && FrontEnd->Rows()[FrontEnd->Focus()].Action == SoraUI::EAction::ConfirmNo);
    Kept(TEXT("Asking erases nothing"));
    Scope.Key(EKeys::Enter);
    TestTrue(TEXT("Enter on Cancel withdraws the prompt"), Scope.On(SoraUI::EScreen::Main) && Mode->bMenu && Scope.Paused());
    Kept(TEXT("Cancel erases nothing"));

    Scope.Key(EKeys::Gamepad_FaceButton_Bottom);
    Scope.Key(EKeys::Escape);
    TestTrue(TEXT("Esc withdraws the prompt and keeps the menu open"), Scope.On(SoraUI::EScreen::Main) && Scope.Paused());
    Scope.Key(EKeys::Gamepad_FaceButton_Bottom);
    Scope.Key(EKeys::Gamepad_FaceButton_Right);
    TestTrue(TEXT("Pad B withdraws the prompt"), Scope.On(SoraUI::EScreen::Main));
    Kept(TEXT("Withdrawing erases nothing"));

    Scope.Key(EKeys::Gamepad_FaceButton_Bottom);
    Scope.Key(EKeys::Gamepad_DPad_Up);
    Scope.Key(EKeys::Gamepad_FaceButton_Bottom);
    const USoraSaveGame* Saved = Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(Scope.Slot, 0));
    // The dojo's opening cinematic is a checkpoint beat, so the new save
    // holds that opening and nothing else.
    TestTrue(TEXT("Confirming erases the saved campaign"), Saved && Saved->CurrentChapter == 0 &&
        Saved->HighestChapter == 0 && Saved->CheckpointChapter == 0 && Saved->CheckpointBeat == 0 &&
        Saved->CheckpointBeatsMask == 0 && !Saved->CampaignComplete);
    TestFalse(TEXT("A new campaign has no progress to erase"), Mode->Campaign()->HasProgress());
    TestTrue(TEXT("Confirming erases every unlock and find"), Saved && Saved->ChapterEntryWeapons == 0 &&
        Saved->ChapterEntryMechanics == 0 && Saved->Collectibles == 0);
    TestTrue(TEXT("The new campaign opens on the dojo's title card"),
        !Mode->bMenu && !Scope.Paused() && Mode->InputState() == SoraInput::Card && Mode->Campaign()->ChapterId == 0 &&
        Mode->Campaign()->ActiveBeat() == 0 && Mode->Campaign()->Progress().CompletedMask == 0u);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraMenuPausesWorldTest,
    "SoraArena.Menu.PausesWorld",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraMenuPausesWorldTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraMenuSafety;
    FScope Scope(*this, TEXT("MenuPause"));
    if (!Scope.Start())
        return false;
    ASoraGameMode* Mode = Scope.Mode();
    UWorld* World = Scope.Get();
    if (!TestTrue(TEXT("The title screen pauses the world"), Scope.On(SoraUI::EScreen::Title) && Mode->bMenu && Scope.Paused()))
        return false;
    double Time = World->GetTimeSeconds();
    TArray<FVector> Opponents = Scope.OpponentLocations();
    Scope.Frames(FramesPerSecond);
    TestEqual(TEXT("World time holds under the title screen"), World->GetTimeSeconds(), Time);
    TestTrue(TEXT("Opponents hold still under the title screen"), Scope.OpponentLocations() == Opponents);

    Scope.Key(EKeys::Enter);
    TestTrue(TEXT("The main menu keeps the world paused"), Scope.On(SoraUI::EScreen::Main) && Scope.Paused());
    // A fresh save begins the prepared dojo round from the first row.
    Scope.Key(EKeys::Enter);
    TestTrue(TEXT("Enter closes the menu and unpauses the world"), !Mode->bMenu && !Scope.Paused() && !Scope.FrontEnd()->IsOpen());
    Scope.Key(EKeys::Enter);
    TestTrue(TEXT("Enter skips the chapter card into play"), Mode->IsPlaying());
    Time = World->GetTimeSeconds();
    Scope.Frames(FramesPerSecond);
    TestTrue(TEXT("World time runs in play"), World->GetTimeSeconds() > Time + .9);
    TestTrue(TEXT("The round timer runs in play"), Mode->RoundTime > .9f);

    Scope.Key(EKeys::Escape);
    if (!TestTrue(TEXT("Esc opens the pause menu and pauses the world mid-round"),
        Scope.On(SoraUI::EScreen::Pause) && Mode->bMenu && Scope.Paused()))
        return false;
    Time = World->GetTimeSeconds();
    float Round = Mode->RoundTime;
    Opponents = Scope.OpponentLocations();
    Scope.Frames(2 * FramesPerSecond);
    TestEqual(TEXT("World time holds under the pause menu"), World->GetTimeSeconds(), Time);
    TestEqual(TEXT("The round timer holds under the pause menu"), Mode->RoundTime, Round);
    TestTrue(TEXT("Opponents hold still under the pause menu"), Scope.OpponentLocations() == Opponents);

    // Settings opened from the pause menu keep the world paused and return to it.
    Scope.Key(EKeys::Gamepad_DPad_Down);
    Scope.Key(EKeys::Gamepad_DPad_Down);
    Scope.Key(EKeys::Gamepad_FaceButton_Bottom);
    TestTrue(TEXT("Settings open over the paused round"), Scope.On(SoraUI::EScreen::Settings) && Scope.Paused());
    Scope.Key(EKeys::Gamepad_FaceButton_Right);
    TestTrue(TEXT("B returns from settings to the pause menu"), Scope.On(SoraUI::EScreen::Pause) && Scope.Paused());

    // The pad's Start resumes, as does B on the pause menu.
    Scope.Key(EKeys::Gamepad_Special_Right);
    TestTrue(TEXT("Start closes the pause menu and unpauses the world"), !Mode->bMenu && !Scope.Paused());
    Scope.Frames(FramesPerSecond / 2);
    TestTrue(TEXT("The round resumes after the menu closes"), Mode->RoundTime > Round);
    Scope.Key(EKeys::Gamepad_Special_Right);
    TestTrue(TEXT("Start in play opens the pause menu"), Scope.On(SoraUI::EScreen::Pause) && Scope.Paused());
    Round = Mode->RoundTime;
    Scope.Key(EKeys::Gamepad_FaceButton_Right);
    TestTrue(TEXT("B on the pause menu resumes"), !Mode->bMenu && !Scope.Paused());
    Scope.Frames(FramesPerSecond / 2);
    return TestTrue(TEXT("The round runs again"), Mode->RoundTime > Round);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraStateGatedKeysTest,
    "SoraArena.Input.StateGatedKeys",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraStateGatedKeysTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraMenuSafety;
    // The mappings the engine actually loaded: every action has states, none
    // acts under the front end, and no key triggers two actions that can act
    // in one state.
    const UInputSettings* Settings = GetDefault<UInputSettings>();
    TMap<FKey, TArray<FString>> ActionsByKey;
    for (const FInputActionKeyMapping& Mapping : Settings->GetActionMappings())
    {
        const FString Action = Mapping.ActionName.ToString();
        TestTrue(*FString::Printf(TEXT("%s has input states"), *Action), SoraInput::StatesFor(*Action) != 0);
        TestEqual(*FString::Printf(TEXT("%s does not act in menus, where the front end holds input"), *Action),
            SoraInput::StatesFor(*Action) & SoraInput::Menu, 0);
        ActionsByKey.FindOrAdd(Mapping.Key).AddUnique(Action);
    }
    for (const FInputAxisKeyMapping& Mapping : Settings->GetAxisMappings())
    {
        const FString Axis = Mapping.AxisName.ToString();
        TestTrue(*FString::Printf(TEXT("%s has input states"), *Axis), SoraInput::StatesFor(*Axis) != 0);
        ActionsByKey.FindOrAdd(Mapping.Key).AddUnique(Axis);
    }
    int32 SharedKeys = 0;
    for (const TPair<FKey, TArray<FString>>& Entry : ActionsByKey)
    {
        SharedKeys += Entry.Value.Num() > 1;
        for (int32 A = 0; A < Entry.Value.Num(); ++A)
            for (int32 B = A + 1; B < Entry.Value.Num(); ++B)
            {
                const uint8 Both = SoraInput::StatesFor(*Entry.Value[A]) & SoraInput::StatesFor(*Entry.Value[B]);
                TestEqual(*FString::Printf(TEXT("%s triggers %s and %s together in %s"), *Entry.Key.ToString(),
                    *Entry.Value[A], *Entry.Value[B], *StateNames(Both)), static_cast<int32>(Both), 0);
            }
    }
    // Pad A is Enter on the card and results and Jump in play.
    TestTrue(TEXT("The overlap check covers the shared pad button"), SharedKeys >= 1);

    FScope Scope(*this, TEXT("StateGatedKeys"));
    if (!Scope.Start())
        return false;
    ASoraGameMode* Mode = Scope.Mode();
    ASoraPlayerCharacter* Hero = Scope.Player();
    Scope.Key(EKeys::Gamepad_RightThumbstick);
    TestTrue(TEXT("Any button, even a stick click, only leaves the title"), Scope.On(SoraUI::EScreen::Main) && !Mode->bDeterministicPractice);

    // Should focus fall back to the game viewport with the menu open, keys
    // reach play input; the input states and the paused world keep every
    // play action, Enter's skip included, from acting on them.
    TestTrue(TEXT("A, Space, the mouse, X, E and Enter that reach play input in the menu act on nothing"), Scope.HeldPastFrontEnd(
        {EKeys::Gamepad_FaceButton_Bottom, EKeys::SpaceBar, EKeys::LeftMouseButton, EKeys::Gamepad_FaceButton_Left, EKeys::E, EKeys::Enter},
        [&]() { return Scope.On(SoraUI::EScreen::Main) && Mode->bMenu && !Hero->bPressedJump && Hero->JumpCurrentCount == 0 &&
            !Hero->GetEquipment()->IsTriggerHeld() && !Mode->bDeterministicPractice; }));

    // Pad A accepts in the menu, skips the card, and jumps only in play.
    Scope.Key(EKeys::Gamepad_FaceButton_Bottom);
    TestTrue(TEXT("A in the menu starts the chapter on its title card"), !Mode->bMenu && Mode->InputState() == SoraInput::Card);
    TestEqual(TEXT("A in the menu does not also jump"), Hero->JumpCurrentCount, 0);
    // Let the hero settle on the ground while the card counts down.
    Scope.Frames(FramesPerSecond);
    TestFalse(TEXT("The hero stands on the ground"), Hero->GetCharacterMovement()->IsFalling());
    Scope.Key(EKeys::Gamepad_FaceButton_Bottom);
    TestTrue(TEXT("A on the title card skips it into play"), Mode->IsPlaying());
    TestEqual(TEXT("A on the title card does not also jump"), Hero->JumpCurrentCount, 0);
    Scope.Key(EKeys::Gamepad_FaceButton_Bottom);
    TestTrue(TEXT("A in play jumps"), Hero->JumpCurrentCount > 0 || Hero->GetCharacterMovement()->IsFalling());
    TestTrue(TEXT("A in play leaves the round running"), Mode->IsPlaying());

    // The old menu buttons act only in play now: Y, X, LB and the d-pad's up.
    const int32 Class = Mode->SelectedClass;
    for (const FKey& Button : {EKeys::Gamepad_FaceButton_Top, EKeys::Gamepad_FaceButton_Left, EKeys::Gamepad_LeftShoulder, EKeys::Gamepad_DPad_Up})
        Scope.Key(Button);
    TestTrue(TEXT("Y, X, LB and d-pad up open no menu and start no practice"),
        !Mode->bMenu && !Mode->bDeterministicPractice && Mode->bCampaign && Mode->SelectedClass == Class);
    TestTrue(TEXT("The round is still in play"), Mode->IsPlaying());

    // The pause menu holds the same line.
    Scope.Frames(FramesPerSecond);
    Scope.Key(EKeys::Escape);
    if (!TestTrue(TEXT("Esc in play opens the pause menu"), Scope.On(SoraUI::EScreen::Pause) && Scope.Paused()))
        return false;
    return TestTrue(TEXT("A, Space, the mouse and Enter that reach play input under the pause menu act on nothing"), Scope.HeldPastFrontEnd(
        {EKeys::Gamepad_FaceButton_Bottom, EKeys::SpaceBar, EKeys::LeftMouseButton, EKeys::Enter},
        [&]() { return Scope.On(SoraUI::EScreen::Pause) && Mode->bMenu && !Hero->bPressedJump && !Hero->GetEquipment()->IsTriggerHeld(); }));
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraIsolatedControlProfileTest,
    "SoraArena.Input.IsolatedControlProfile",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraIsolatedControlProfileTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraMenuSafety;
    // The key tests must not depend on this machine's local control profile.
    // A profile seeded in the world's own control slot moves Jump from Space
    // to J and inverts look; binding input must apply exactly that.
    FScope Scope(*this, TEXT("ControlProfile"));
    const FString ControlSlot = FSoraAutomationWorld::ControlSlot(Scope.Slot);
    USoraControlSaveGame* Profile = USoraControlSaveGame::New();
    if (!TestNotNull(TEXT("Control profile object"), Profile))
        return false;
    FSoraControlBinding Binding;
    Binding.ActionName = TEXT("Jump");
    Binding.Key = EKeys::J;
    Profile->Bindings.Add(Binding);
    Profile->InvertedLook = true;
    if (!TestTrue(TEXT("Seed profile saved to the isolated control slot"), UGameplayStatics::SaveGameToSlot(Profile, ControlSlot, 0)) ||
        !Scope.Start())
        return false;
    ASoraPlayerCharacter* Hero = Scope.Player();
    TestEqual(TEXT("The world reads its own control slot"), Scope.Mode()->ControlSlotName, ControlSlot);
    const TArray<FKey> Keys = Hero->GetActionKeys(TEXT("Jump"));
    TestTrue(TEXT("The seeded keyboard key replaces Space"), Keys.Contains(EKeys::J) && !Keys.Contains(EKeys::SpaceBar));
    TestTrue(TEXT("The pad key stays"), Keys.Contains(EKeys::Gamepad_FaceButton_Bottom));
    TestTrue(TEXT("The seeded look preference applies"), Hero->GetInvertedLook());
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraChapterTitleCardTest,
    "SoraArena.Campaign.ChapterTitleCard",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraChapterTitleCardTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraMenuSafety;
    const FSoraCatalog& Catalog = FSoraCatalog::Get();
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    // Every English field in catalog.json reaches the runtime structs.
    for (int32 Id = 0; Id < Catalog.Chapters.Num(); ++Id)
    {
        const FSoraChapter& Chapter = Catalog.Chapter(Id);
        TestTrue(*FString::Printf(TEXT("Chapter %d has Japanese title, narrative and objective"), Id),
            HasJapanese(Chapter.Title) && HasJapanese(Chapter.Narrative) && HasJapanese(Chapter.Objective));
        TestTrue(*FString::Printf(TEXT("Chapter %d has English title, narrative and objective"), Id),
            !Chapter.TitleEnglish.IsEmpty() && !Chapter.NarrativeEnglish.IsEmpty() && !Chapter.ObjectiveEnglish.IsEmpty() &&
            !HasJapanese(Chapter.TitleEnglish) && !HasJapanese(Chapter.ObjectiveEnglish));
    }
    for (const FSoraMap& Map : Catalog.Maps)
        TestTrue(*FString::Printf(TEXT("Map %s has an English name"), *Map.Name), !Map.NameEnglish.IsEmpty() && !HasJapanese(Map.NameEnglish));
    for (const FSoraClass& Class : Catalog.Classes)
        TestTrue(*FString::Printf(TEXT("Class %s has an English name and role"), *Class.Name),
            !Class.NameEnglish.IsEmpty() && !Class.RoleEnglish.IsEmpty() && !HasJapanese(Class.NameEnglish));
    for (int32 Id = 0; Id < 21; ++Id)
        TestFalse(*FString::Printf(TEXT("Weapon %d has an English name"), Id), Catalog.Weapon(Id).NameEnglish.IsEmpty());

    // The first invasion chapter, started fresh from the menu. Its opening
    // cinematic plays on the card: the title card first, then the letterboxed
    // frame with the cinematic's subtitles on their own clock.
    constexpr int32 ChapterId = 1;
    const FSoraChapter& Chapter = Catalog.Chapter(ChapterId);
    const FSoraBeat& Opening = Chapter.Beats[0];
    const FSoraDialogueTrigger* FirstSubtitle = Chapter.Triggers.FindByPredicate([](const FSoraDialogueTrigger& Trigger)
    {
        return Trigger.Beat == 0 && Trigger.On == TEXT("subtitle");
    });
    if (!TestTrue(TEXT("The chapter opens on a cinematic with subtitles"), Opening.Is(SoraBeatRules::EType::Cinematic) && FirstSubtitle != nullptr))
        return false;
    FScope Scope(*this, TEXT("ChapterTitleCard"));
    if (!WriteSave(*this, Scope.Slot, ChapterId, ChapterId) || !Scope.Start())
        return false;
    ASoraGameMode* Mode = Scope.Mode();
    ASoraPlayerCharacter* Hero = Scope.Player();
    TestNull(TEXT("The card waits behind the title screen"), Mode->TitleCardChapter());
    Scope.Key(EKeys::Enter);
    TestTrue(TEXT("The card waits behind the main menu"), Scope.On(SoraUI::EScreen::Main) && !Mode->TitleCardChapter());
    Scope.Key(EKeys::Enter);
    if (!TestTrue(TEXT("Continue opens the chapter on its title card"), Mode->TitleCardChapter() == &Chapter &&
        Mode->Campaign()->ActiveBeat() == 0 && Mode->Campaign()->IsChapterOpening()))
        return false;
    TestEqual(TEXT("No notice competes with the card"), Mode->NoticeTime, 0.f);

    // The card holds combat, the round timer and the dialogue queue.
    const float Health = Hero->Health;
    UGameplayStatics::ApplyDamage(Hero, 50.f, nullptr, nullptr, UDamageType::StaticClass());
    TestEqual(TEXT("The hero cannot be hurt under the card"), Hero->Health, Health);
    TestTrue(TEXT("No opponent takes the field during the opening cinematic"), Scope.OpponentLocations().IsEmpty());
    Scope.Frames(2 * FramesPerSecond);
    TestEqual(TEXT("The round timer waits for the card"), Mode->RoundTime, 0.f);
    TestNull(TEXT("No subtitle before its cue"), Mode->Campaign()->CurrentDialogueCue());
    TestTrue(TEXT("The card counts down the cinematic"), Mode->TitleCardTime > 0.f && Mode->TitleCardTime < Opening.Task.DurationMs / 1000.f - 1.9f);
    TestTrue(TEXT("The title card shows first"), Mode->Campaign()->CinematicElapsed() < ASoraGameMode::TitleCardSeconds);
    Scope.Frames(FMath::CeilToInt32((FirstSubtitle->AtMs / 1000.f - 2.f + .1f) * FramesPerSecond));
    TestTrue(TEXT("The first subtitle appears on its cue"),
        Mode->Campaign()->CurrentDialogueCue() == &Chapter.Dialogue[FirstSubtitle->Lines[0]]);

    // Left alone, the cinematic closes by itself and the next beat's lines follow it.
    int32 Frames = 0;
    while (Mode->TitleCardChapter() && Frames++ < FMath::CeilToInt32(Opening.Task.DurationMs / 1000.f) * 4)
        Scope.Frames(1, .25f);
    if (!TestTrue(TEXT("The card closes on its own"), Mode->TitleCardChapter() == nullptr && Mode->IsPlaying()))
        return false;
    Scope.Frames(1);
    TestTrue(TEXT("The round timer starts when the card closes"), Mode->RoundTime < .3f);
    TestEqual(TEXT("The chapter's first combat beat begins"), Mode->Campaign()->ActiveBeat(), 1);
    const FSoraDialogueTrigger* Next = Chapter.Triggers.FindByPredicate([](const FSoraDialogueTrigger& Trigger)
    {
        return Trigger.Beat == 1 && Trigger.On == TEXT("beat_start");
    });
    TestTrue(TEXT("Its opening line follows the card"),
        Next && Mode->Campaign()->CurrentDialogueCue() == &Chapter.Dialogue[Next->Lines[0]]);
    TestFalse(TEXT("Its opponents take the field"), Scope.OpponentLocations().IsEmpty());
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraDeterministicEnemyFireTest,
    "SoraArena.Campaign.DeterministicEnemyFire",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraDeterministicEnemyFireTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraMenuSafety;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    // The pattern: one shot in three misses, never two in a row, and slots differ.
    for (int32 Slot = 1; Slot <= 3; ++Slot)
    {
        int32 Misses = 0;
        for (int32 Shot = 0; Shot < 30; ++Shot)
        {
            Misses += ASoraEnemy::RangedShotMisses(Slot, Shot);
            TestFalse(TEXT("Never two misses in a row"), Shot > 0 &&
                ASoraEnemy::RangedShotMisses(Slot, Shot) && ASoraEnemy::RangedShotMisses(Slot, Shot - 1));
        }
        TestEqual(*FString::Printf(TEXT("Slot %d misses one shot in three"), Slot), Misses, 10);
    }
    // Slots 1, 2 and 3 first miss on shots 2, 1 and 0, so a wave never misses in unison.
    for (int32 Slot = 1; Slot <= 3; ++Slot)
        TestTrue(*FString::Printf(TEXT("Slot %d first misses on shot %d"), Slot, 3 - Slot),
            ASoraEnemy::RangedShotMisses(Slot, 3 - Slot) && !ASoraEnemy::RangedShotMisses(Slot, (4 - Slot) % 3) &&
            !ASoraEnemy::RangedShotMisses(Slot, (5 - Slot) % 3));
    FFireRun First, Second;
    if (!RunFire(*this, First) || !RunFire(*this, Second))
        return false;
    TestEqual(TEXT("Both runs fire the same shots"), Second.Shots, First.Shots);
    TestTrue(TEXT("Both runs hit on the same frames"), Second.HitFrames == First.HitFrames);
    FString Frames;
    for (const int32 Frame : First.HitFrames)
        Frames += FString::Printf(TEXT("%s%d"), Frames.IsEmpty() ? TEXT("") : TEXT(","), Frame);
    UE_LOG(LogTemp, Display, TEXT("SORA_ENEMY_FIRE_OK: shots=%d hits=%d frames=%s"), First.Shots, First.HitFrames.Num(), *Frames);
    return true;
}
#endif
