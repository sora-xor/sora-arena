#include "SoraWorldBuilder.h"
#include "SoraCatalog.h"
#include "SoraClimbRules.h"
#include "Components/StaticMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "PhysicsEngine/BodySetup.h"
#include "ProceduralMeshComponent.h"

void ASoraWorldBuilder::BuildClimb(const FSoraBeat& Beat)
{
    const auto& C=Beat.Space.Climb;
    const FVector O(C.Origin,0);
    const FLinearColor Stone(.34f,.36f,.33f),Metal(.07f,.11f,.13f);
    const auto Slab=[&](const TCHAR* Name,const FVector& At,const FVector& Size,const FLinearColor& Color)
    { return Box(Name,O+At,Size,Color,true,FRotator::ZeroRotator,TEXT("Stone")); };
    Slab(TEXT("ClimbTerrace"),FVector(600,-1700,-25),FVector(3200,5400,50),Stone);
    // A solid sloping prism: both rendered triangles and swept collision use
    // the same eight vertices. The corner route follows the exposed arris.
    const auto Course=[&](double Low,double High)
    {
        const double A=SoraClimbRules::WallX(Low),B=SoraClimbRules::WallX(High);
        TArray<FVector> V={FVector(A,-4200,Low),FVector(2000,-4200,Low),FVector(2000,0,Low),FVector(A,0,Low),
            FVector(B,-4200,High),FVector(2000,-4200,High),FVector(2000,0,High),FVector(B,0,High)};
        const TArray<int32> I={0,2,1,0,3,2,4,5,6,4,6,7,0,1,5,0,5,4,1,2,6,1,6,5,2,3,7,2,7,6,3,0,4,3,4,7};
        auto* M=NewObject<UProceduralMeshComponent>(this,MakeUniqueObjectName(this,UProceduralMeshComponent::StaticClass(),TEXT("ClimbMasonry")));
        M->SetupAttachment(RootComponent);M->SetRelativeLocation(O);M->SetMobility(EComponentMobility::Movable);
        M->bUseComplexAsSimpleCollision=false;M->bUseAsyncCooking=false;
        M->SetCollisionObjectType(ECC_WorldStatic);M->SetCollisionResponseToAllChannels(ECR_Block);
        const TArray<FVector> N;const TArray<FVector2D> UV;const TArray<FLinearColor> Colors;const TArray<FProcMeshTangent> T;
        M->CreateMeshSection_LinearColor(0,V,I,N,UV,Colors,T,false);M->AddCollisionConvexMesh(V);
        M->GetBodySetup()->CollisionTraceFlag=CTF_UseSimpleAsComplex;
        if(auto* Base=LoadObject<UMaterialInterface>(nullptr,TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial")))
        { auto* Mat=UMaterialInstanceDynamic::Create(Base,M);Mat->SetVectorParameterValue(TEXT("Color"),Stone);M->SetMaterial(0,Mat); }
        M->RegisterComponent();AddInstanceComponent(M);M->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    };
    Course(0,600);Course(600,1600);
    for(const auto* Route:{&C.Corner,&C.Extrusion})
        for(int32 H=1;H<Route->Points.Num();++H)
        {
            const FVector P=Route->Points[H];
            Box(TEXT("ClimbAuthoredHold"),O+P+FVector(48,0,110),FVector(35,45,14),Route->bExposed?Metal:Stone,false);
        }
    for(int32 H:C.Corner.RestHolds)
    {
        const FVector P=C.Corner.Points[H];
        Slab(TEXT("ClimbRestLedge"),P+FVector(0,0,-10),FVector(260,300,20),Stone);
    }
    // The parapet and landing are real support. Its outward bay projects over
    // the wall, so the sentry's sight trace can actually reach upper holds.
    Slab(TEXT("ClimbParapet"),FVector(850,-1750,1580),FVector(700,4900,40),Stone);
    // The narrow cantilever leaves real open stone-drop slots on both
    // sides; a broad solid deck would occlude the sentry's own downward ray.
    Slab(TEXT("ClimbStoneDropBay"),FVector(480,-300,1580),FVector(330,80,40),Stone);
    // Ground-to-top bypasses meet the 16 m shell. The landing's far boundary
    // and high sides keep its only exit through the low turret aperture.
    Slab(TEXT("ClimbLandingNorth"),FVector(1350,850,1950),FVector(1700,100,700),Stone);
    Slab(TEXT("ClimbLandingSouth"),FVector(1350,-4300,1950),FVector(1700,100,700),Stone);
    Slab(TEXT("ClimbLandingBack"),FVector(2150,-1700,1950),FVector(100,5200,700),Stone);
    Slab(TEXT("ClimbTopFloor"),FVector(1600,-1700,1625),FVector(1000,5200,50),Stone);
    // A 50 cm rise over 300 cm: the production slope meets both top floors.
    const double Angle=FMath::Atan2(50.,300.);
    const double Length=FMath::Sqrt(300.*300.+50.*50.);
    Box(TEXT("ClimbCrawlApproach"),O+FVector(950+10*FMath::Sin(Angle),0,1625-10*FMath::Cos(Angle)),
        FVector(Length,500,20),Stone,true,FRotator(FMath::RadiansToDegrees(Angle),0,0),TEXT("Stone"));
    Slab(TEXT("ClimbCrawlLintel"),FVector(1250,0,1805),FVector(300,120,190),Stone);
    Slab(TEXT("ClimbCrawlLeft"),FVector(1250,-2180,1900),FVector(300,4240,600),Stone);
    Slab(TEXT("ClimbCrawlRight"),FVector(1250,455,1900),FVector(300,790,600),Stone);
    // A short rail prevents stepping around the aperture off its approach.
    for(int32 Side:{-1,1}) Slab(TEXT("ClimbApproachRail"),FVector(980,Side*280,1730),FVector(240,40,260),Stone);
    Box(TEXT("ClimbExtrusionStrip"),O+FVector(450,-1000,1100),FVector(22,22,1000),FLinearColor(.05f,.7f,.85f),false);
}
