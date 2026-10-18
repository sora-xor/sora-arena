#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SoraCampaignLift.generated.h"
class UBoxComponent;
class UStaticMeshComponent;
class ACharacter;
class ASoraEnemy;

// A physical moving floor with stationary landings. Riders are carried by
// CharacterMovement's movement base; this actor never relocates a rider.
UCLASS()
class SORAARENA_API ASoraCampaignLift : public AActor
{
    GENERATED_BODY()
public:
    ASoraCampaignLift();
    void Build(FVector2D Center,int32 Turns,int32 MinTurnMs);
    void SetWork(int32 Milliturns);
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    float Height() const;
    bool Arrived() const;
    bool Aboard(const ACharacter& Rider) const;
    FVector BoardingPoint() const;
    FVector GalleryExit() const;
    FVector GalleryCache() const;
    UBoxComponent* FloorBase() const;
    FVector WaveSpawn(int32 Wave,int32 Member) const;
    FVector CutterGoal(int32 Member) const;
    FVector HawserPoint(float HeightCm) const;
    void Assign(ASoraEnemy& Enemy,int32 Wave);
    bool CutterTouching() const;
private:
    UPROPERTY() TObjectPtr<USceneComponent> Scene;
    UPROPERTY() TObjectPtr<UBoxComponent> Deck;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> WestGate;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> EastGate;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Wheel;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Hawser;
    TArray<TWeakObjectPtr<UStaticMeshComponent>> Cutters;
    int32 Goal=48000;
    double TargetCm=2700.0,SpeedCmS=0.0;
    void Gates();
    UStaticMeshComponent* Box(const TCHAR* Name,USceneComponent* Parent,FVector At,FVector Size,bool Collision);
    void Landing(const TCHAR* Name,FVector Center,FVector2D Size,bool WestOpening,bool Through=false);
};
