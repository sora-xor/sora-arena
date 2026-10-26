#include "SoraWorldBuilder.h"
#include "SoraLanternWorkshopRules.h"

void ASoraWorldBuilder::BuildLanternWorkshop()
{
    namespace R=SoraLanternWorkshopRules;
    int Index=0;
    for(const auto& S:R::Solids())
    {
        const TCHAR* Role=S.Surface==R::ESurface::Stone?TEXT("Stone"):
            S.Surface==R::ESurface::Soil?TEXT("Soil"):TEXT("Timber");
        Box(FString::Printf(TEXT("LanternWorkshopSolid%d"),Index++),FVector(S.X,S.Y,S.Z),
            FVector(S.SX,S.SY,S.SZ),FLinearColor(.31f,.25f,.18f),true,FRotator::ZeroRotator,Role);
    }
}
