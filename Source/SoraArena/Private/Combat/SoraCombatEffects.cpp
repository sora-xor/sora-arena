#include "Combat/SoraCombatEffects.h"
#include "SoraCombatRules.h"
#include "SoraGameMode.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/WorldSettings.h"

USoraCombatEffects* USoraCombatEffects::Get(const UObject* WorldContext)
{
    const UWorld* World = WorldContext ? WorldContext->GetWorld() : nullptr;
    return World ? World->GetSubsystem<USoraCombatEffects>() : nullptr;
}

bool USoraCombatEffects::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
    return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

TStatId USoraCombatEffects::GetStatId() const
{
    RETURN_QUICK_DECLARE_CYCLE_STAT(USoraCombatEffects, STATGROUP_Tickables);
}

double USoraCombatEffects::Now() const
{
    return GetWorld()->GetRealTimeSeconds();
}

void USoraCombatEffects::HitStop(int32 Milliseconds)
{
    UWorld* World = GetWorld();
    AWorldSettings* Settings = World ? World->GetWorldSettings() : nullptr;
    if (Milliseconds <= 0 || !Settings)
        return;
    const auto* Mode = Cast<ASoraGameMode>(World->GetAuthGameMode());
    if (Mode && Mode->bDeterministicPractice)
        return;
    if (!bHitStop)
    {
        bHitStop = true;
        DilationBefore = Settings->TimeDilation;
        Settings->SetTimeDilation(DilationBefore * SoraCombatRules::HitStopDilationPermille / 1000.f);
        HitStopEndsAt = 0.0;
    }
    HitStopEndsAt = FMath::Max(HitStopEndsAt, Now() + Milliseconds / 1000.0);
}

void USoraCombatEffects::EndHitStop()
{
    if (!bHitStop)
        return;
    bHitStop = false;
    if (AWorldSettings* Settings = GetWorld() ? GetWorld()->GetWorldSettings() : nullptr)
        Settings->SetTimeDilation(DilationBefore);
}

void USoraCombatEffects::Root(ACharacter& Target, int32 Milliseconds)
{
    UCharacterMovementComponent* Movement = Target.GetCharacterMovement();
    if (Milliseconds <= 0 || !Movement)
        return;
    const double EndsAt = Now() + Milliseconds / 1000.0;
    for (FRoot& Held : Roots)
    {
        if (Held.Target.Get() == &Target)
        {
            Held.EndsAt = FMath::Max(Held.EndsAt, EndsAt);
            return;
        }
    }
    Movement->StopMovementImmediately();
    Movement->DisableMovement();
    Roots.Add({&Target, EndsAt});
}

bool USoraCombatEffects::IsRooted(const AActor* Target) const
{
    for (const FRoot& Held : Roots)
        if (Held.Target.Get() == Target)
            return true;
    return false;
}

void USoraCombatEffects::Tick(float DeltaTime)
{
    Super::Tick(DeltaTime);
    const double Time = Now();
    if (bHitStop && Time >= HitStopEndsAt)
        EndHitStop();
    for (int32 Index = Roots.Num() - 1; Index >= 0; --Index)
    {
        ACharacter* Target = Roots[Index].Target.Get();
        if (Target && Time < Roots[Index].EndsAt)
            continue;
        // The net lets go; a body something else has since set moving is left alone.
        if (Target && Target->GetCharacterMovement() && Target->GetCharacterMovement()->MovementMode == MOVE_None)
            Target->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
        Roots.RemoveAt(Index);
    }
}

void USoraCombatEffects::Deinitialize()
{
    EndHitStop();
    Roots.Reset();
    Super::Deinitialize();
}
