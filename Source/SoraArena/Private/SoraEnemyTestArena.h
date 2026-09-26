#pragma once
#include "CoreMinimal.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "SoraAutomationWorld.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "SoraSaveGame.h"
#include "SoraWorldBuilder.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/AutomationTest.h"
#include "Templates/UniquePtr.h"

// A real game world for the opponents' automation (SoraArena.AI.*, SoraArena.Combat.*).
namespace SoraEnemyTest
{
// The first invasion chapter on the estate, cleared of its hunting wave so each
// test places exactly the opponents it examines on the open central road.
struct FArena
{
    FAutomationTestBase& Test;
    FString Slot;
    TUniquePtr<FSoraAutomationWorld> World;

    FArena(FAutomationTestBase& InTest, const TCHAR* Name)
        : Test(InTest), Slot(FSoraAutomationWorld::UniqueSaveSlot(Name))
    {
        FSoraAutomationWorld::IgnoreMissingGeneratedArt(Test);
        FSoraAutomationWorld::IgnoreAbsentSaveSlot(Test, Slot);
    }
    ~FArena()
    {
        if (World)
        {
            World->DestroyTestWorld(true);
            World->ForwardErrorMessages(&Test);
            World.Reset();
        }
        FSoraAutomationWorld::DeleteSaveSlot(Slot);
    }
    UWorld* Get() const { return World ? World->GetTestWorld() : nullptr; }
    ASoraGameMode* Mode() const { return World ? World->Mode() : nullptr; }
    ASoraPlayerCharacter* Hero() const { return World ? World->Player() : nullptr; }

    bool Start()
    {
        USoraSaveGame* Save = Cast<USoraSaveGame>(UGameplayStatics::CreateSaveGameObject(USoraSaveGame::StaticClass()));
        if (!Test.TestNotNull(TEXT("Seed save is created"), Save))
            return false;
        Save->SaveSchema = 5;
        Save->CurrentChapter = 1;
        Save->HighestChapter = 1;
        Save->CheckpointChapter = -1;
        if (!Test.TestTrue(TEXT("Seed save is written"), UGameplayStatics::SaveGameToSlot(Save, Slot, 0)))
            return false;
        World = MakeUnique<FSoraAutomationWorld>();
        // Enter three times: the title screen opens the main menu, Continue
        // opens the saved chapter on its title card, and the card is skipped.
        if (!World->Start(Slot) || !World->Tick(1) || !World->EnableKeyInput() ||
            !World->PressKey(EKeys::Enter) || !World->PressKey(EKeys::Enter) || !World->PressKey(EKeys::Enter))
        {
            World->ForwardErrorMessages(&Test);
            return Test.TestTrue(TEXT("The chapter world starts with key input"), false);
        }
        if (!Test.TestTrue(TEXT("The chapter is in play"), Mode() && Mode()->IsPlaying() && Hero()))
            return false;
        // The director never replaces an opponent that is removed rather than defeated.
        for (TActorIterator<ASoraEnemy> It(Get()); It; ++It)
            It->Destroy();
        // The hero rests (no footsteps) and outlasts any strike during a test.
        Hero()->MaxHealth = 100000.f;
        Hero()->Health = Hero()->MaxHealth;
        return true;
    }
    bool Tick(int32 Frames)
    {
        if (World->Tick(Frames))
            return true;
        World->ForwardErrorMessages(&Test);
        return Test.TestTrue(TEXT("The world ticks"), false);
    }
    void PlaceHero(const FVector& At, float Yaw) const
    {
        ASoraPlayerCharacter* Player = Hero();
        Player->SetActorLocation(FVector(At.X, At.Y, Player->GetActorLocation().Z), false, nullptr, ETeleportType::TeleportPhysics);
        const FRotator Rotation(0.f, Yaw, 0.f);
        if (AController* Controller = Player->GetController())
            Controller->SetControlRotation(Rotation);
        Player->FaceRotation(Rotation, 0.f);
    }
    ASoraEnemy* Spawn(int32 EnemySlot, const FVector& At, float Yaw, const FSoraPatrolRoute* Patrol = nullptr) const
    {
        return ASoraEnemy::SpawnInvader(*Get(), EnemySlot, FVector(At.X, At.Y, 120.f), FRotator(0.f, Yaw, 0.f), Patrol);
    }
    // An opponent of an archetype from Content/Data/enemies.json.
    ASoraEnemy* SpawnKind(const TCHAR* Archetype, int32 EnemySlot, const FVector& At, float Yaw,
        const FSoraPatrolRoute* Patrol = nullptr, const FSoraEnemyTuning* Tuning = nullptr) const
    {
        return ASoraEnemy::SpawnArchetype(*Get(), FName(Archetype), EnemySlot, FVector(At.X, At.Y, 120.f), FRotator(0.f, Yaw, 0.f),
            Patrol, Tuning);
    }
    // A sentry guarding the spot it stands on.
    ASoraEnemy* Sentry(int32 EnemySlot, const FVector& At, float Yaw) const
    {
        FSoraPatrolRoute Post;
        Post.Points.Add(FVector(At.X, At.Y, 90.f));
        return Spawn(EnemySlot, At, Yaw, &Post);
    }
    // A wall raised during play; it blocks bodies, sight and the navigation mesh.
    AActor* Wall(const FVector& Center, const FVector& Size) const
    {
        AActor* Built = Get()->SpawnActor<AActor>();
        UStaticMeshComponent* Mesh = ASoraWorldBuilder::Shape(Built, nullptr, TEXT("AutomationWall"),
            TEXT("/Engine/BasicShapes/Cube.Cube"), Center, Size / 100.f, FLinearColor(.3f, .3f, .3f), true);
        Built->SetRootComponent(Mesh);
        return Built;
    }
    static ASoraEnemyController* Brain(const ASoraEnemy* Enemy)
    {
        return Enemy ? Cast<ASoraEnemyController>(Enemy->GetController()) : nullptr;
    }
};
} // namespace SoraEnemyTest
#endif
