#include "SoraAutomationWorld.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "SoraWorldBuilder.h"
#include "Components/InputComponent.h"
#include "Engine/World.h"
#include "GameFramework/InputSettings.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerInput.h"
#include "InputKeyEventArgs.h"
#include "GameFramework/WorldSettings.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/AutomationTest.h"
#include "Misc/Guid.h"

bool FSoraAutomationWorld::Start(const FString& SaveSlot)
{
    if (SaveSlot.IsEmpty())
    {
        ReportFailure(TEXT("Automation worlds require an isolated save slot"));
        return false;
    }
    if (!CreateTestWorld(EWorldType::Game))
        return false;
    UWorld* World = GetTestWorld();
    AWorldSettings* Settings = World ? World->GetWorldSettings() : nullptr;
    if (!Settings)
    {
        ReportFailure(TEXT("Test world has no world settings"));
        return false;
    }
    // Do not depend on the project's global default; this world must run ASoraGameMode.
    Settings->DefaultGameMode = ASoraGameMode::StaticClass();
    CachedFrameCounter = GFrameCounter;
    const FURL URL;
    if (!World->SetGameMode(URL))
    {
        ReportFailure(TEXT("Test world rejected its game mode"));
        return false;
    }
    ASoraGameMode* GameMode = Cast<ASoraGameMode>(World->GetAuthGameMode());
    if (!GameMode)
    {
        ReportFailure(TEXT("ASoraGameMode was not created"));
        return false;
    }
    GameMode->SaveSlotName = SaveSlot;
    GameMode->ControlSlotName = ControlSlot(SaveSlot);
    World->InitializeActorsForPlay(URL);
    World->BeginPlay();
    if (!World->GetGameState())
    {
        ReportFailure(TEXT("Test world has no game state"));
        return false;
    }
    APlayerController* Controller = GameMode->SpawnPlayerController(ROLE_Authority, FString());
    if (!Controller)
    {
        ReportFailure(TEXT("Player controller was not spawned"));
        return false;
    }
    const FVector Start = GameMode->Arena() ? GameMode->Arena()->PlayerStart() : FVector::ZeroVector;
    GameMode->RestartPlayerAtTransform(Controller, FTransform(Start));
    if (!Cast<ASoraPlayerCharacter>(Controller->GetPawn()))
    {
        ReportFailure(TEXT("Player controller does not possess ASoraPlayerCharacter"));
        return false;
    }
    return true;
}

bool FSoraAutomationWorld::Tick(int32 Frames, float DeltaSeconds)
{
    for (int32 Frame = 0; Frame < Frames; ++Frame)
        if (!TickTestWorld(DeltaSeconds))
            return false;
    return true;
}

ASoraGameMode* FSoraAutomationWorld::Mode() const
{
    return GetTestWorld() ? Cast<ASoraGameMode>(GetTestWorld()->GetAuthGameMode()) : nullptr;
}

ASoraPlayerCharacter* FSoraAutomationWorld::Player() const
{
    return GetTestWorld() ? Cast<ASoraPlayerCharacter>(UGameplayStatics::GetPlayerPawn(GetTestWorld(), 0)) : nullptr;
}

UInputComponent* FSoraAutomationWorld::BindPlayerInput() const
{
    ASoraPlayerCharacter* Pawn = Player();
    if (!Pawn)
        return nullptr;
    if (!Pawn->InputComponent)
    {
        UInputComponent* Input = NewObject<UInputComponent>(Pawn, TEXT("AutomationPlayerInput"));
        Pawn->InputComponent = Input;
        Pawn->SetupPlayerInputComponent(Input);
        Input->RegisterComponent();
    }
    return Pawn->InputComponent;
}

bool FSoraAutomationWorld::EnableKeyInput() const
{
    ASoraPlayerCharacter* Pawn = Player();
    APlayerController* Controller = Pawn ? Cast<APlayerController>(Pawn->GetController()) : nullptr;
    if (!Controller)
        return false;
    if (!Controller->PlayerInput)
        Controller->PlayerInput = NewObject<UPlayerInput>(Controller, UInputSettings::GetDefaultPlayerInputClass());
    Controller->SetAsLocalPlayerController();
    return Controller->PlayerInput && BindPlayerInput();
}

bool FSoraAutomationWorld::PressKey(const FKey& Key)
{
    constexpr float FrameSeconds = 1.f / 60.f;
    for (const EInputEvent Event : {IE_Pressed, IE_Released})
        if (!InjectKey(Key, Event) || !Tick(1, FrameSeconds))
            return false;
    return true;
}

bool FSoraAutomationWorld::InjectKey(const FKey& Key, EInputEvent Event) const
{
    ASoraPlayerCharacter* Pawn = Player();
    APlayerController* Controller = Pawn ? Cast<APlayerController>(Pawn->GetController()) : nullptr;
    UWorld* World = GetTestWorld();
    if (!Controller || !Controller->PlayerInput || !World || !Pawn->InputComponent)
        return false;
    constexpr float FrameSeconds = 1.f / 60.f;
    // The stack APlayerController::BuildInputStack gives a possessed pawn: its
    // own input component, evaluated with the world's pause state.
    const TArray<UInputComponent*> Stack = {Pawn->InputComponent};
    Controller->InputKey(FInputKeyEventArgs::CreateSimulated(Key, Event, Event == IE_Pressed ? 1.f : 0.f));
    Controller->PlayerInput->ProcessInputStack(Stack, FrameSeconds, World->IsPaused());
    return true;
}

void FSoraAutomationWorld::IgnoreMissingGeneratedArt(FAutomationTestBase& Test)
{
    for (const TCHAR* Message : {
        TEXT("SORA authored environment prop "),
        TEXT("SORA estate terrain needs the pinned CC0 soil"),
        TEXT("SORA authored estate terrain tile missing: "),
        TEXT("SORA pinned CC0 Nyaagyu tree is missing: "),
        TEXT("SORA pinned CC0 Nyaagyu pine is missing: "),
        TEXT("Nyaakoto PBR material is missing: ")})
        Test.AddExpectedErrorPlain(Message, EAutomationExpectedErrorFlags::Contains, -1);
    // The engine's localized "object not found" warning quotes the class and
    // /Game/Generated path; only that form is ignored.
    Test.AddExpectedMessage(TEXT("'[A-Za-z]+ /Game/Generated/[^']+'"), ELogVerbosity::Warning,
        EAutomationExpectedMessageFlags::Contains, -1);
}

void FSoraAutomationWorld::IgnoreAbsentSaveSlot(FAutomationTestBase& Test, const FString& SaveSlot)
{
    for (const FString& Slot : {SaveSlot, ControlSlot(SaveSlot)})
        Test.AddExpectedMessagePlain(Slot + TEXT(".sav"), ELogVerbosity::Warning,
            EAutomationExpectedMessageFlags::Contains, -1);
}

FString FSoraAutomationWorld::UniqueSaveSlot(const TCHAR* Purpose)
{
    return FString::Printf(TEXT("SoraArenaAutomation_%s_%s"), Purpose, *FGuid::NewGuid().ToString(EGuidFormats::Digits));
}

FString FSoraAutomationWorld::ControlSlot(const FString& SaveSlot)
{
    return SaveSlot + TEXT("_Controls");
}

void FSoraAutomationWorld::DeleteSaveSlot(const FString& SaveSlot)
{
    if (SaveSlot.IsEmpty())
        return;
    for (const FString& Slot : {SaveSlot, ControlSlot(SaveSlot)})
        if (UGameplayStatics::DoesSaveGameExist(Slot, 0))
            UGameplayStatics::DeleteGameInSlot(Slot, 0);
}
#endif
