#include "SoraWorldBuilder.h"
#include "SoraTenementRules.h"
#include "SoraCatalog.h"
#include "Components/StaticMeshComponent.h"

void ASoraWorldBuilder::BuildTenements()
{
    namespace R=SoraTenementRules;
    int Index=0;
    for(const auto& S:R::Solids())
    {
        const TCHAR* Role=S.Surface==R::ESurface::Stone?TEXT("Stone"):
            S.Surface==R::ESurface::Soil?TEXT("Soil"):S.Surface==R::ESurface::Paper?TEXT(""):TEXT("Timber");
        const FLinearColor Tint=S.Surface==R::ESurface::Paper?FLinearColor(.52f,.5f,.44f):FLinearColor(.3f,.25f,.19f);
        Box(FString::Printf(TEXT("TenementSolid%d"),Index++),FVector(S.X,S.Y,S.Z),FVector(S.SX,S.SY,S.SZ),
            Tint,true,FRotator(0,S.Yaw,0),Role);
    }
    RecoveryHatch=Box(TEXT("TenementWellCover"),FVector(R::WellX,R::WellY,R::Curb-5),FVector(R::Bore,R::Bore,10),
        FLinearColor(.25f,.18f,.11f),true,FRotator::ZeroRotator,TEXT("Timber"));
    Box(TEXT("TenementKnottedRope"),FVector(R::WellX-38,R::WellY,(330-R::Depth)/2.),
        FVector(5,5,R::Depth+330),FLinearColor(.45f,.36f,.21f),false);
    for(int Z=-R::Depth+25;Z<330;Z+=35)
        Box(FString::Printf(TEXT("TenementRopeKnot%d"),Z),FVector(R::WellX-38,R::WellY,Z),FVector(8,8,7),
            FLinearColor(.45f,.36f,.21f),false);
    // The working well's pulley and a clear crate platform are separate
    // from the narrow retrieval shaft. The authored pickup is at its frame.
    Box(TEXT("TenementHoistRope"),FVector(-2600,3100,165),FVector(4,4,220),FLinearColor(.45f,.36f,.21f),false);
    for(int Y:{1000,1800,2400})
    {
        auto* Cloth=Box(TEXT("TenementSightScreen"),FVector(-2800,Y,160),FVector(Y==1000?180:140,2,160),
            FLinearColor(.19f,.23f,.24f),false);
        // Noren/laundry conceal the alley without becoming invisible walls
        // for the player. Their cloth art and motion still need production.
        Cloth->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
        Cloth->SetCollisionResponseToAllChannels(ECR_Ignore);
        Cloth->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
    }
}
