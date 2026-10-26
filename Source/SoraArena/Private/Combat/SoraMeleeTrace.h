#pragma once
#include "CoreMinimal.h"

class AActor;
class UWorld;
struct FHitResult;

namespace SoraMeleeTrace
{
// Preserve Pawn-channel contacts, including overlapping weak points, while
// substituting a drone's authored hulls for its movement-only sphere.
void Sweep(UWorld& World,TArray<FHitResult>& Hits,const FVector& Start,
    const FVector& End,float Radius,AActor* Attacker);
}
