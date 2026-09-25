#pragma once
#include "CoreMinimal.h"
#include "AIController.h"
#include "SoraEnemyController.generated.h"
class ASoraBoss;
class ASoraCharacterBase;
class ASoraEnemy;

// The campaign opponents' brain. Each frame it faces its pawn toward Nyaakoto,
// steers around the obstacle ahead, keeps its kind's distance and runs the
// pawn's attack. The pawn's tick calls Think at the point in the frame where
// the first prototype ran this logic, before the hero's tick, so frame order
// and behaviour are unchanged. Navigation-mesh pathing is not used yet.
UCLASS()
class SORAARENA_API ASoraEnemyController : public AAIController
{
    GENERATED_BODY()
public:
    // One frame of decisions for a pawn that is alive in live play.
    void Think(float DeltaSeconds);
private:
    void DriveOpponent(ASoraEnemy& Enemy, ASoraCharacterBase& Target, float DeltaSeconds);
    void DriveCollector(ASoraBoss& Boss, ASoraCharacterBase& Target, float DeltaSeconds);
};
