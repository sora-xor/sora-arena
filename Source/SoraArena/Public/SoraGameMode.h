#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "SoraInputStates.h"
#include "SoraGameMode.generated.h"
class ASoraPlayerCharacter;
class ASoraWorldBuilder;
class UArenaKernelSubsystem;
class USoraCampaignDirector;
class USoraFrontEnd;
class USoraPracticeDirector;
class USoraSettings;
struct FSoraChapter;
struct FSoraPracticeLobbySelection;

// The session shell: the front end's menu flow and pause, the title card,
// round results, notices and the input state. The screens themselves belong
// to USoraFrontEnd and the player's settings to USoraSettings; offline rounds
// (the eight campaign chapters and the training arena) to
// USoraCampaignDirector; deterministic kernel practice to
// USoraPracticeDirector.
UCLASS()
class SORAARENA_API ASoraGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    ASoraGameMode();
    virtual void BeginPlay() override;
    virtual void Tick(float Dt) override;
    // Enter: closes the menu into play, skips the chapter title card, and
    // continues from a defeat or a completed chapter.
    void BeginRound();
    // Esc or Start in play opens the pause menu.
    void OpenPauseMenu();
    // Kernel practice with the current class, map and loadout slot.
    void DeterministicPractice();
    // F10: English subtitles on or off, saved with the settings.
    void ToggleSubtitles();
    void Interact(ASoraPlayerCharacter* Player);
    // The front end's commands. Its confirmation dialogs come first; these act.
    // Continue returns to the saved chapter from the title or from practice.
    bool CanContinueCampaign() const;
    bool ContinueCampaign();
    // Whether the save holds anything New Campaign would erase.
    bool CampaignHasProgress() const;
    // Erases the saved chapter, checkpoint and chapter reach, then plays the dojo.
    void StartNewCampaign();
    // Chapter select: a fresh start of any chapter up to the highest reached.
    int32 HighestChapterReached() const;
    bool StartChapter(int32 Chapter);
    // Zero-stake practice with the lobby's choice; false leaves the menu open
    // with the reason in Notice.
    bool StartPracticeFromLobby(const FSoraPracticeLobbySelection& Selection);
    void ResumePlay();
    // The campaign round from its last checkpoint, or practice from its start.
    bool RestartRound();
    // Leaves play for the main menu; the campaign waits at its last checkpoint.
    void ReturnToTitle();
    void QuitGame();
    // Rebuilds the current round: practice, or an offline chapter or arena.
    void ResetRound();
    // Opens or closes the menu; the open menu pauses the world. Opened from
    // play by a director, it shows the main menu with the notice as a banner.
    void SetMenuOpen(bool bOpen);
    // Read at BeginPlay. Automation assigns a unique slot before play begins so
    // it never reads or overwrites the player's campaign.
    FString SaveSlotName = TEXT("SoraSoloCampaign");
    // The hero's local control preferences, read when its input is bound.
    // Automation assigns its own slot for the same reason.
    FString ControlSlotName = TEXT("SoraControlsV1");
    // Volumes, subtitles and accessibility, read at BeginPlay.
    FString SettingsSlotName = TEXT("SoraSettings");
    // Automation clears this before BeginPlay so the settings never apply
    // graphics or volume to the engine or write GameUserSettings.ini.
    bool bAttachSettingsToEngine = true;
    // A front-end screen is open: the title, a menu or a dialog.
    bool bMenu = true;
    bool bDefeated = false;
    bool bChapterComplete = false;
    bool bCampaign = true;
    bool bDeterministicPractice = false;
    int32 MapId = 0;
    int32 SelectedClass = 0;
    FString Notice;
    FString NoticeEnglish;
    // The live English subtitle switch; USoraSettings sets and saves it.
    bool bEnglishSubtitles = true;
    float NoticeTime = 0;
    float RoundTime = 0;
    // A fresh chapter opens on its title card before dialogue and the round
    // timer start. Enter skips it; otherwise it closes after TitleCardSeconds.
    static constexpr float TitleCardSeconds = 9.f;
    float TitleCardTime = 0;
    const FSoraChapter* TitleCardChapter() const;
    // Decides which input actions may act (see SoraInputStates.h).
    SoraInput::EState InputState() const;
    bool IsPlaying() const { return InputState() == SoraInput::Play; }
    FString ObjectiveText() const;
    FString ObjectiveTextEnglish() const;
    ASoraWorldBuilder* Arena() const { return WorldBuilder; }
    USoraCampaignDirector* Campaign() const { return CampaignDirector; }
    USoraPracticeDirector* Practice() const { return PracticeDirector; }
    USoraFrontEnd* FrontEnd() const { return FrontEndState; }
    USoraSettings* Settings() const { return SettingsState; }
    UArenaKernelSubsystem* Kernel() const;
    ASoraPlayerCharacter* Hero() const;
private:
    UPROPERTY() TObjectPtr<ASoraWorldBuilder> WorldBuilder;
    UPROPERTY() TObjectPtr<USoraCampaignDirector> CampaignDirector;
    UPROPERTY() TObjectPtr<USoraPracticeDirector> PracticeDirector;
    UPROPERTY() TObjectPtr<USoraFrontEnd> FrontEndState;
    UPROPERTY() TObjectPtr<USoraSettings> SettingsState;
    bool bRoundPrepared = false;
    void SyncMenuPause();
};
