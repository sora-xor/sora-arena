#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "SoraInputStates.h"
#include "SoraGameMode.generated.h"
class ASoraPlayerCharacter;
class ASoraWorldBuilder;
class UArenaKernelSubsystem;
class USoraCampaignDirector;
class USoraPracticeDirector;
struct FSoraChapter;

// The session shell: menu and pause, mode selection, the title card, round
// results, notices and the input state. Offline rounds (the eight campaign
// chapters and the training arena) belong to USoraCampaignDirector;
// deterministic kernel practice belongs to USoraPracticeDirector.
UCLASS()
class SORAARENA_API ASoraGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    ASoraGameMode();
    virtual void BeginPlay() override;
    virtual void Tick(float Dt) override;
    // Menu and flow commands reached from the player's input.
    void BeginRound();
    void ToggleMenu();
    void NextMap();
    void NewCampaign();
    void ReturnCampaign();
    void DeterministicPractice();
    void SelectPracticeWeapon(int32 Slot);
    void SelectClass(int32 Id);
    void ToggleSubtitles();
    void Interact(ASoraPlayerCharacter* Player);
    // Rebuilds the current round: practice, or an offline chapter or arena.
    void ResetRound();
    // Opens or closes the menu; the open menu pauses the world.
    void SetMenuOpen(bool bOpen);
    // Read at BeginPlay. Automation assigns a unique slot before play begins so
    // it never reads or overwrites the player's campaign.
    FString SaveSlotName = TEXT("SoraSoloCampaign");
    // The hero's local control preferences, read when its input is bound.
    // Automation assigns its own slot for the same reason.
    FString ControlSlotName = TEXT("SoraControlsV1");
    bool bMenu = true;
    // New Campaign erases the saved chapter, checkpoint and highest chapter, so
    // its first press only raises this prompt; a second press confirms it.
    bool bConfirmNewCampaign = false;
    bool bDefeated = false;
    bool bChapterComplete = false;
    bool bCampaign = true;
    bool bDeterministicPractice = false;
    int32 MapId = 0;
    int32 SelectedClass = 0;
    FString Notice;
    FString NoticeEnglish;
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
    UArenaKernelSubsystem* Kernel() const;
    ASoraPlayerCharacter* Hero() const;
private:
    UPROPERTY() TObjectPtr<ASoraWorldBuilder> WorldBuilder;
    UPROPERTY() TObjectPtr<USoraCampaignDirector> CampaignDirector;
    UPROPERTY() TObjectPtr<USoraPracticeDirector> PracticeDirector;
    bool bRoundPrepared = false;
    void SyncMenuPause();
};
