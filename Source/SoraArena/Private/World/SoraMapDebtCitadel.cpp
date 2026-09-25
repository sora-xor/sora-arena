#include "SoraWorldBuilder.h"

// Debt Citadel, map 3: the alien debt kiosk beside the second production site.
void ASoraWorldBuilder::DebtCitadelKiosk()
{
    ImportedProp(TEXT("SM_Alien_DebtKiosk"),NodePositions[1]+FVector(315,0,0),FRotator(0,90,0));
}
