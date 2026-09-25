#include "SoraWorldBuilder.h"

// Silk Foundry, map 2: the levy loom beside the foundry production station.
void ASoraWorldBuilder::SilkFoundryLoom(FVector P)
{
    // The original silk loom is decorative beside the Silk Foundry
    // production station. Its meter and operator face the approach;
    // the established simple boxes retain gameplay collision.
    ImportedProp(TEXT("SM_SilkFoundry_LevyLoom"),P+FVector(-100,-450,0),FRotator::ZeroRotator);
}
