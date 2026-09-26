#pragma once

#if WITH_DEV_AUTOMATION_TESTS
#include "Combat/SoraDamage.h"
#include "Combat/SoraStealth.h"
#include "SoraAutomationWorld.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraCompanion.h"
#include "SoraFieldcraft.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "SoraSaveGame.h"
#include "Camera/CameraComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/AutomationTest.h"
#include "Templates/UniquePtr.h"

// A campaign beat's world for the fieldcraft tests: seeded at the beat's
// checkpoint, started through the player's keys, its fieldcraft's events
// recorded, and helpers to stand the hero, turn his eye and hold his keys.
namespace SoraFieldcraftAutomation
{
struct FBeatWorld
{
    FAutomationTestBase& Test;
    FString Slot;
    int32 Chapter = 0;
    int32 Beat = 0;
    TUniquePtr<FSoraAutomationWorld> World;
    TArray<FString> Events;
    FDelegateHandle EventsHandle;
    FBeatWorld(FAutomationTestBase& InTest, const TCHAR* Name, int32 InChapter, int32 InBeat)
        : Test(InTest), Slot(FSoraAutomationWorld::UniqueSaveSlot(Name)), Chapter(InChapter), Beat(InBeat)
    {
        FSoraAutomationWorld::IgnoreMissingGeneratedArt(Test);
        FSoraAutomationWorld::IgnoreAbsentSaveSlot(Test, Slot);
    }
    ~FBeatWorld()
    {
        if (World)
        {
            if (USoraFieldcraft* Craft = Fieldcraft()) Craft->OnEvent.Remove(EventsHandle);
            World->DestroyTestWorld(true);
            World->ForwardErrorMessages(&Test);
            World.Reset();
        }
        FSoraAutomationWorld::DeleteSaveSlot(Slot);
    }
    ASoraGameMode* Mode() const { return World->Mode(); }
    USoraCampaignDirector* Campaign() const { return Mode()->Campaign(); }
    USoraFieldcraft* Fieldcraft() const { return World ? USoraFieldcraft::Get(World->GetTestWorld()) : nullptr; }
    USoraStealth* Stealth() const { return USoraStealth::Get(World->GetTestWorld()); }
    ASoraPlayerCharacter* Hero() const { return World->Player(); }
    const FSoraBeat& BeatData() const { return Campaign()->ActiveChapter()->Beats[Beat]; }
    const FSoraFieldcraft& Craft() const { return BeatData().Space.Fieldcraft; }
    bool Start()
    {
        USoraSaveGame* Save = Cast<USoraSaveGame>(UGameplayStatics::CreateSaveGameObject(USoraSaveGame::StaticClass()));
        if (!Save || !USoraCampaignDirector::SeedCheckpoint(*Save, Chapter, Beat) || !UGameplayStatics::SaveGameToSlot(Save, Slot, 0))
            return Test.TestTrue(TEXT("The beat's checkpoint is seeded"), false);
        World = MakeUnique<FSoraAutomationWorld>();
        if (!World->Start(Slot) || !World->Tick(1) || !World->EnableKeyInput() || !World->PressKey(EKeys::Enter) ||
            !World->PressKey(EKeys::Enter) || !World->PressKey(EKeys::Enter))
        {
            World->ForwardErrorMessages(&Test);
            return Test.TestTrue(TEXT("The beat's world starts"), false);
        }
        if (USoraFieldcraft* Craft = Fieldcraft())
            EventsHandle = Craft->OnEvent.AddLambda([this](FName Event) { Events.Add(Event.ToString()); });
        return Test.TestTrue(TEXT("The beat is in play"), Mode()->IsPlaying() && Campaign()->ActiveBeat() == Beat);
    }
    bool Tick(int32 Frames, float DeltaSeconds = 1.f / 60.f)
    {
        if (World->Tick(Frames, DeltaSeconds))
            return true;
        World->ForwardErrorMessages(&Test);
        return Test.TestTrue(TEXT("The world ticks"), false);
    }
    bool Press(const FKey& Key)
    {
        return World->PressKey(Key) || Test.TestTrue(TEXT("A key press reaches the hero"), false);
    }
    // A key held down for Frames world frames, then let go.
    bool Hold(const FKey& Key, int32 Frames)
    {
        return World->InjectKey(Key, IE_Pressed) && Tick(Frames) && World->InjectKey(Key, IE_Released) && Tick(1);
    }
    void Harden() const
    {
        Hero()->MaxHealth = 100000.f;
        Hero()->Health = Hero()->MaxHealth;
    }
    void Stand(const FVector& At) const
    {
        ASoraPlayerCharacter* Player = Hero();
        Player->GetCharacterMovement()->StopMovementImmediately();
        Player->SetActorLocation(FVector(At.X, At.Y, Player->GetActorLocation().Z), false, nullptr, ETeleportType::TeleportPhysics);
    }
    void Stand(const FVector& At, float Yaw) const
    {
        Stand(At);
        Look(FRotator(0.f, Yaw, 0.f));
    }
    void Look(const FRotator& Rotation) const
    {
        if (AController* Controller = Hero()->GetController()) Controller->SetControlRotation(Rotation);
        Hero()->FaceRotation(Rotation, 0.f);
        // In play the camera manager turns the eye to the view, pitch and all
        // (UCameraComponent::bUsePawnControlRotation). This world's controller
        // has no local player, so APlayerCameraManager::UpdateCamera never runs
        // and the eye would keep the body's level gaze: it is set here as that
        // update sets it.
        Hero()->GetCamera()->SetWorldRotation(Rotation);
    }
    // The hero's eye turned on a point.
    void LookAt(const FVector& Point) const
    {
        Look((Point - Hero()->GetCamera()->GetComponentLocation()).Rotation());
    }
    bool Raised(const FString& Event) const { return Events.Contains(Event); }
    // The ways round a point the hero tries until one has nothing in between.
    static constexpr float Sides[] = {180.f, 0.f, 90.f, -90.f, 135.f, -135.f, 45.f, -45.f};
    // The hero's eye turned on Point from Distance away until Event is raised
    // (looks are checked ten times a second); false only if the world stops.
    bool LookUntil(const FString& Event, const FVector& Point, float Distance)
    {
        for (const float Side : Sides)
        {
            Stand(Point + FRotator(0.f, Side, 0.f).Vector() * Distance);
            for (int32 Frame = 0; Frame < 20 && !Raised(Event); ++Frame)
            {
                LookAt(Point);
                if (!Tick(1)) return false;
            }
            if (Raised(Event)) return true;
        }
        Test.AddInfo(FString::Printf(TEXT("%s was never raised; the eye last at %s, the point at %s"), *Event,
            *Hero()->GetCamera()->GetComponentLocation().ToString(), *Point.ToString()));
        return true;
    }
    // The hero stood Distance from Target, facing it, where his eye finds it first.
    bool ClearShot(const AActor& Target, float Distance)
    {
        const FVector Point = Target.GetActorLocation();
        for (const float Side : Sides)
        {
            Stand(Point + FRotator(0.f, Side, 0.f).Vector() * Distance);
            if (!Tick(1)) return false;
            LookAt(Point);
            if (!Tick(1)) return false;
            const UCameraComponent* Camera = Hero()->GetCamera();
            FHitResult Hit;
            const FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraFieldcraftTestShot), false, Hero());
            if (World->GetTestWorld()->LineTraceSingleByChannel(Hit, Camera->GetComponentLocation(),
                Camera->GetComponentLocation() + Camera->GetForwardVector() * (Distance + 200.f), ECC_Visibility, Query) &&
                Hit.GetActor() == &Target)
                return true;
        }
        return Test.TestTrue(TEXT("The hero finds a clear shot"), false);
    }
    // The hero stood Distance from Point, his eye on it, where nothing but
    // the people about him stands between (a volley's ring is marked there).
    bool ClearView(const FVector& Point, float Distance)
    {
        for (const float Side : Sides)
        {
            Stand(Point + FRotator(0.f, Side, 0.f).Vector() * Distance);
            if (!Tick(1)) return false;
            LookAt(Point);
            if (!Tick(1)) return false;
            const UCameraComponent* Camera = Hero()->GetCamera();
            FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraFieldcraftTestView), false, Hero());
            for (TActorIterator<ASoraCompanion> It(World->GetTestWorld()); It; ++It) Query.AddIgnoredActor(*It);
            FHitResult Hit;
            if (World->GetTestWorld()->LineTraceSingleByChannel(Hit, Camera->GetComponentLocation(),
                Camera->GetComponentLocation() + Camera->GetForwardVector() * (Distance + 400.f), ECC_Visibility, Query) &&
                FVector::Dist2D(Hit.ImpactPoint, Point) < 150.f)
                return true;
        }
        return Test.TestTrue(TEXT("The hero finds a clear view"), false);
    }
    int32 Count(const TCHAR* Event) const
    {
        return Events.FilterByPredicate([Event](const FString& Raised) { return Raised == Event; }).Num();
    }
    // A blow from nowhere (a hazard): what an opponent's strike does to a companion.
    static void Hurt(AActor& Victim, float Damage)
    {
        FHitResult Trace; Trace.ImpactPoint = Victim.GetActorLocation(); Trace.Location = Trace.ImpactPoint;
        SoraDamage::Strike(&Victim, Damage, FSoraHit::Hazard(Victim.GetActorLocation()), FVector::UpVector, Trace, nullptr, nullptr);
    }
    bool PromptOn(const TCHAR* Event) const
    {
        const FSoraPrompt* Prompt = Campaign()->CurrentPrompt();
        return Prompt && Prompt->On == Event;
    }
};

inline FVector Floor(const FVector2D& At) { return FVector(At.X, At.Y, 0.f); }
} // namespace SoraFieldcraftAutomation
#endif
