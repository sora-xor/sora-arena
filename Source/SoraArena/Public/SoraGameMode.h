#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "SoraPracticeClock.h"
#include "SoraDojoRules.h"
#include "SoraGameMode.generated.h"
class ASoraCharacter;
class ASoraWorldBuilder;
class USoraSaveGame;
class UArenaKernelSubsystem;
class UStaticMeshComponent;
struct FSoraDialogueCue;
UCLASS()
class SORAARENA_API ASoraGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    ASoraGameMode();
    virtual void BeginPlay() override;
    virtual void Tick(float Dt) override;
    void BeginRound();
    void ToggleMenu();
    void NextMap();
    void NewCampaign();
    void ReturnCampaign();
    void DeterministicPractice();
    void SelectPracticeWeapon(int32 Slot);
    bool bDeterministicPractice = false;
    int32 PracticeWeaponSlot = 1;
    bool bPracticeSlowed = false;
    UArenaKernelSubsystem* Kernel() const;
    void SelectClass(int32 Id);
    void Interact(ASoraCharacter* Player);
    void OpponentDefeated(ASoraCharacter* Opponent);
    bool RecordDojoLesson(SoraDojoRules::EAction Action, int32 DurationMs,
        bool bFacingAttacker = true, int32 RecoveryMs = 0);
    bool CanScoreDojoBout() const;
    int32 DojoLessonStage() const;
    void PlayerKilled();
    void SaveProgress();
    bool bMenu = true;
    bool bDefeated = false;
    bool bChapterComplete = false;
    bool bCampaignComplete = false;
    bool bCampaign = true;
    int32 ChapterId = 0;
    int32 MapId = 0;
    int32 SelectedClass = 0;
    int32 Kills = 0;
    int32 KillsNeeded = 6;
    FString Notice;
    FString NoticeEnglish;
    bool bEnglishSubtitles = true;
    void ToggleSubtitles();
    float NoticeTime = 0;
    float RoundTime = 0;
    FString ObjectiveText() const;
    FString DojoLessonText(bool bEnglish) const;
    const FSoraDialogueCue* CurrentDialogueCue() const;
    ASoraWorldBuilder* Arena() const { return WorldBuilder; }
    const ASoraCharacter* CampaignBoss() const;
private:
    UPROPERTY() TObjectPtr<ASoraWorldBuilder> WorldBuilder;
    UPROPERTY() TObjectPtr<USoraSaveGame> Save;
    UPROPERTY() TArray<TObjectPtr<ASoraCharacter>> Enemies;
    UPROPERTY() TObjectPtr<ASoraCharacter> BossActor;
    int32 Spawned = 0;
    unsigned DojoLessonMask = 0u;
    FSoraPracticeClock PracticeClock;
    bool bPlayChapterDialogue = false;
    UPROPERTY() TArray<TObjectPtr<ASoraCharacter>> PracticePawns;
    UPROPERTY() TMap<uint32, TObjectPtr<AActor>> PracticeProjectileActors;
    bool ResetPractice();
    void ClearPractice();
    void ClearOfflineProjectiles();
    void UpdatePracticePresentation();
    void PresentPracticeEvents();
    void ResetRound();
    void SpawnEnemy();
    void SaveCheckpoint();
    void ClearCheckpoint();
};
