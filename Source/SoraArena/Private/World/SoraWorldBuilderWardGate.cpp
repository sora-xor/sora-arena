#include "SoraWorldBuilder.h"
#include "SoraCatalog.h"
#include "SoraWardGateRules.h"

void ASoraWorldBuilder::BuildWardGate(const FSoraZone& Zone)
{
    namespace R=SoraWardGateRules;
    const FLinearColor Earth(.24f,.20f,.14f),Wood(.25f,.17f,.10f),Stone(.28f,.29f,.27f),Plaster(.58f,.56f,.49f);
    // These are the same solids swept by the host geometry checks. The
    // shared landing owns the entrance floor; the west descent bends around
    // the hut instead of placing steps through its wall.
    for(const auto& S:R::Ground)
        Box(UTF8_TO_TCHAR(S.Name),FVector((S.X0+S.X1)*.5f,(S.Y0+S.Y1)*.5f,S.Top-30),
            FVector(S.X1-S.X0,S.Y1-S.Y0,60),Earth,true,FRotator::ZeroRotator,TEXT("Soil"));
    for(const auto& S:R::Solids)
    {
        const FLinearColor Color=S.Surface==R::ESurface::Wood?Wood:S.Surface==R::ESurface::Stone?Stone:Plaster;
        const TCHAR* Role=S.Surface==R::ESurface::Wood?TEXT("Timber"):S.Surface==R::ESurface::Stone?TEXT("Stone"):TEXT("Plaster");
        Box(UTF8_TO_TCHAR(S.Name),FVector(S.X,S.Y,S.Z),FVector(S.Width,S.Depth,S.Height),Color,true,FRotator::ZeroRotator,Role);
    }
    for(const auto& W:Zone.Walls)
        Box(TEXT("WardBoundary"),FVector(W.Center,W.Height*.5f),FVector(W.Size,W.Height),Stone,true);
    // Fieldcraft owns the opening wicket, sensor, shop's walkable roof,
    // ladder and straw. These boxes are functional layout, not final art.
}
