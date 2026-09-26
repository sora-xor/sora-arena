#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "SoraCaptions.generated.h"
struct FSoraBossPhaseEvent;
struct FSoraDefenseEvent;
struct FSoraDetonatedEvent;
struct FSoraMeleeCommittedEvent;
struct FSoraWeaponFiredEvent;

// Sound captions: the sounds that matter in play, in words, with where they
// came from. It listens to USoraGameEvents for other combatants' shots and
// swings, blades meeting, explosions and a collector's phases; the audio
// lane can add its own through Show. The HUD draws the live captions while
// the Sound captions setting is on. Captions are presentation only.
struct FSoraCaption
{
    FString Japanese, English;
    // Where the sound came from; a caption without one shows no direction.
    FVector Source = FVector::ZeroVector;
    bool bHasSource = false;
    // World time, so captions wait while a menu pauses the world.
    float Expires = 0.f;
    // The same sound again while its caption shows.
    int32 Count = 1;
};

UCLASS()
class SORAARENA_API USoraCaptions : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    static constexpr int32 MaxLive = 4;
    static USoraCaptions* Get(const UObject* WorldContext);
    // A caption for Seconds: an NSLOCTEXT with its English subtitle in the
    // Game localization. The same caption while it shows is refreshed and
    // counted; beyond MaxLive the oldest goes.
    void Show(const FText& Caption, const FVector* Source = nullptr, float Seconds = 3.f);
    // The captions still showing, oldest first.
    TArray<FSoraCaption> Live() const;
    virtual void OnWorldBeginPlay(UWorld& InWorld) override;
protected:
    virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
private:
    TArray<FSoraCaption> Captions;
    float Now() const;
    // True for the player's own sounds, which need no caption.
    bool IsHero(const AActor* Actor) const;
    void WeaponFired(const FSoraWeaponFiredEvent& Event);
    void MeleeCommitted(const FSoraMeleeCommittedEvent& Event);
    void Guarded(const FSoraDefenseEvent& Event);
    void Parried(const FSoraDefenseEvent& Event);
    void Detonated(const FSoraDetonatedEvent& Event);
    void BossPhase(const FSoraBossPhaseEvent& Event);
};
