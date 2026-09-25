#include "SoraWorldBuilder.h"
#include "Components/StaticMeshComponent.h"

// Lantern Ward, map 1: the occupied street's alien debt terminal.
void ASoraWorldBuilder::LanternWardTerminal()
{
    // The occupied street faces the road at local -Y. Use the same simple
    // campaign collision whether the authored mesh imported or not.
    const FVector StreetTerminal(-730,460,0);
    const bool HasStreetTerminal=ImportedProp(TEXT("SM_Alien_StreetDebtTerminal"),StreetTerminal,FRotator::ZeroRotator);
    auto* Proxy=Box(TEXT("StreetDebtTerminalCollision"),StreetTerminal+FVector(0,0,121),
        FVector(140,74,242),FLinearColor(.10f,.15f,.20f),true);
    if(HasStreetTerminal) Proxy->SetVisibility(false);
}
