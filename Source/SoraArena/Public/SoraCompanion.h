#pragma once
#include "CoreMinimal.h"
#include "SoraCharacterBase.h"
#include "SoraFieldcraftRules.h"
#include "SoraCompanion.generated.h"
class ASoraEnemy;
struct FSoraCompanionSpec;

// Someone who walks or fights beside Nyaakoto in the campaign: a member of
// an escorted party, or an ally (a fighter, a shooter, a guide or a
// volley rank's gunner, a guide or a bystander) from the beat's fieldcraft
// (FSoraCompanionSpec). Its health,
// knockdown, revival, bleeding out, collar or cell, and hiding follow
// SoraFieldcraftRules; USoraFieldcraft stages it, counts the hero's held hand
// on it and reports what happens to it to the beat. Opponents may take it
// for their quarry (ASoraEnemyController) unless it cannot be seen; the
// hero's own blows never reach it (SoraDamage). A fighter closes on the
// nearest opponent near its post and strikes with a committed windup, a
// shooter holds its post and fires on a fixed miss pattern, a volley rank's
// gunner fires only on the hero's order (USoraFieldcraft), a guide keeps
// near the hero and a bystander keeps its post. An escorted member walks
// where the fieldcraft places it on the road. Nothing is random.
UCLASS()
class SORAARENA_API ASoraCompanion : public ASoraCharacterBase
{
    GENERATED_BODY()
public:
    enum class ERole : uint8 { Escort, Fighter, Shooter, Rank, Guide, Bystander };
    ASoraCompanion(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get());
    // Takes up its spec: its role, arm, health rules and post. Slot offsets
    // its fixed patterns so a group never acts in unison.
    void Init(const FSoraCompanionSpec& Spec, int32 Slot);
    virtual bool AdmitDamage(float& Damage, FSoraHit& Hit, AActor* Causer) override;
    virtual bool IsEnemy() const override { return false; }
    const FString& CompanionId() const { return Id; }
    ERole Role() const { return Kind; }
    const SoraFieldcraftRules::FCompanionRules& Rules() const { return RulesData; }
    const SoraFieldcraftRules::FCompanion& State() const { return StateData; }
    SoraFieldcraftRules::EState Condition() const { return StateData.State; }
    bool IsDown() const { return StateData.State == SoraFieldcraftRules::EState::Down; }
    bool IsDead() const { return StateData.State == SoraFieldcraftRules::EState::Dead; }
    bool IsBound() const { return StateData.State == SoraFieldcraftRules::EState::Bound; }
    bool IsHiddenAway() const { return StateData.State == SoraFieldcraftRules::EState::Hidden; }
    // In the fight (an ally that joins with a later wave waits unseen until then).
    bool IsJoined() const { return bJoined; }
    void Join();
    // Whether an opponent at Distance can see it or take it for its quarry:
    // standing, joined and detectable, and hidden only at arm's length.
    bool IsExposed(int32 DistanceCm) const;
    // The fieldcraft's step: Held is the hero's hand on it (reviving or
    // freeing); the change this step brought.
    SoraFieldcraftRules::EChange Step(int32 DtMs, bool bHeld);
    // A healing lance round on it: true when it starts raising it.
    bool Lance();
    // A defended person follows its target (USoraFieldcraft::TargetChanged):
    // netted, freed or taken.
    void Present(SoraFieldcraftRules::EState State);
    // The hero's signal: hide, or go on.
    bool Signal(bool bHide);
    // Where the fieldcraft wants an escorted member (or a hidden one's spot),
    // reached at its walking pace; the way it faces there.
    void SetGoal(const FVector& Goal, float Yaw, float PaceCmS);
    // The post an ally keeps and returns to.
    FVector Post() const { return PostAt; }
    // Blows landed and rounds fired (automation reads them).
    int32 Strikes() const { return StrikeCount; }
    int32 Rounds() const { return RoundCount; }
    // Nearest standing opponent it could fight now, or null.
    ASoraEnemy* Quarry() const;
    // A volley rank's gunner: its rank, or INDEX_NONE.
    int32 VolleyRank() const { return RankIndex; }
    // Whether it can fire in its rank's volley now.
    bool CanVolley() const { return Kind == ERole::Rank && bJoined && StateData.State == SoraFieldcraftRules::EState::Up; }
    // Its rank at the front (a step before its post, match lit) or filed back to load.
    void StepUp(bool bFront);
    // Its round in a volley on At (the damage is the volley's, not its own).
    void Volley(const FVector& At);
protected:
    virtual void TickPlay(float DeltaSeconds) override;
    virtual void HaltActions() override;
private:
    void Present();
    void Fight(float DeltaSeconds);
    void Shoot(float DeltaSeconds);
    void Guide(float DeltaSeconds);
    void HoldRank(float DeltaSeconds);
    void WalkToGoal(float DeltaSeconds);
    void MoveToward(const FVector& Where, float Pace, float Acceptance);
    bool UsesSpireRoute() const;
    void MoveOnSpire(const FVector& Goal,float Pace,float Acceptance);
    bool SpireContact(const ASoraEnemy& Enemy,float Reach) const;
    TArray<FVector> SpirePath;
    FVector SpirePathGoal=FVector::ZeroVector;
    int32 SpirePathIndex=0;
    float SpireRepathAt=0.f;
    float Now() const;
    FString Id;
    ERole Kind = ERole::Bystander;
    SoraFieldcraftRules::FCompanionRules RulesData{100, false, 3000, 0, 0, false, 0};
    SoraFieldcraftRules::FCompanion StateData{SoraFieldcraftRules::EState::Up, 100, 0, 0, -1};
    bool bDetectable = true;
    bool bJoined = true;
    int32 CompanionSlot = 0;
    int32 RankIndex = INDEX_NONE;
    bool bFrontRank = false;
    FVector PostAt = FVector::ZeroVector;
    float PostYaw = 0.f;
    FVector GoalAt = FVector::ZeroVector;
    float GoalYaw = 0.f;
    float GoalPace = 0.f;
    bool bHasGoal = false;
    // A fighter's committed blow: its target, and when it lands.
    TWeakObjectPtr<ASoraEnemy> Target;
    bool bWindup = false;
    float StrikeAt = 0.f;
    float ReadyAt = 0.f;
    int32 StrikeCount = 0;
    int32 RoundCount = 0;
    SoraFieldcraftRules::EState Shown = SoraFieldcraftRules::EState::Up;
};
