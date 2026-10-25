#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SoraBridgeProp.generated.h"
class ASoraBoss;
class UBoxComponent;
class USceneComponent;

// A swept gameplay body. Each prop is a separate actor so its sweep collides
// with the deck, other props and pawns (component sweeps ignore their owner).
UCLASS()
class SORAARENA_API ASoraBridgeProp : public AActor
{
    GENERATED_BODY()
public:
    ASoraBridgeProp();
    void Build(bool Pod);
    void Warn(ASoraBoss& Boss,int32 Attack,int32 Serial,bool Announce);
    void Advance(float DeltaSeconds,float Degrees);
    void Cancel();
    bool IsBlocked() const { return bBlocked; }
    double WarningElapsedMs() const { return ElapsedMs; }
    UBoxComponent* CollisionBody() const { return Body; }
private:
    UPROPERTY() TObjectPtr<UBoxComponent> Body;
    UPROPERTY() TObjectPtr<USceneComponent> Visual;
    TWeakObjectPtr<ASoraBoss> Keeper;
    int32 AttackIndex=INDEX_NONE,AttackSerial=0;
    double ElapsedMs=-1,Speed=0;
    int32 WarningMs=700;
    bool bBlocked=false,bHitHero=false,bAnnounced=false;
};
