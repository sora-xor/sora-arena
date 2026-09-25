#pragma once
#include "CoreMinimal.h"

class AActor;
class AController;
class ASoraCharacterBase;
class UWorld;
struct FHitResult;

// The single damage path for campaign and training combat. Attackers call
// Deal; every character's TakeDamage calls Resolve, which applies the shared
// rules, asks the victim for its own defenses and defeat handling, and
// announces Damaged and Died through USoraGameEvents. Kernel practice never
// reaches it: kernel-driven characters take no Unreal damage.
namespace SoraDamage
{
// Point damage from Causer, credited to Instigator. Returns the damage applied.
float Deal(AActor* Target, float Damage, const FVector& Direction, const FHitResult& Hit,
    AController* Instigator, AActor* Causer);
float Resolve(ASoraCharacterBase& Victim, float Damage, AActor* Causer);
// A short-lived tracer or telegraph line. Presentation only; it never collides.
void Beam(UWorld* World, FVector From, FVector To, FLinearColor Color, float Radius = 1.5f, float Life = .08f);
}
