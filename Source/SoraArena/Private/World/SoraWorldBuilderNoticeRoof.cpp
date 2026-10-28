#include "SoraWorldBuilder.h"
#include "SoraNoticeSquareRules.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Engine/PointLight.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "PhysicsEngine/BodySetup.h"
#include "ProceduralMeshComponent.h"

void ASoraWorldBuilder::BuildNoticeRoof()
{
    namespace N=SoraNoticeSquareRules;
    const FLinearColor Plaster(.60f,.56f,.47f),Tile(.12f,.15f,.17f),Wood(.25f,.18f,.10f);
    // The closed building has two convex halves. Rendered triangles and
    // movement/visibility collision share these vertices, including gables.
    for(int Half=0;Half<2;++Half)
    {
        const double Y0=Half?800:400,Y1=Half?1300:800;
        const double Z0=N::RoofHeight(Y0)-N::RoofThickness,Z1=N::RoofHeight(Y1)-N::RoofThickness;
        const TArray<FVector> Hull={{600,Y0,0},{1320,Y0,0},{1320,Y1,0},{600,Y1,0},
            {600,Y0,Z0},{1320,Y0,Z0},{1320,Y1,Z1},{600,Y1,Z1}};
        TArray<FVector> V,Normals;TArray<int32> Indices;TArray<FVector2D> UV;
        const auto Triangle=[&](int A,int B,int C)
        {
            const FVector Normal=FVector::CrossProduct(Hull[B]-Hull[A],Hull[C]-Hull[A]).GetSafeNormal();
            for(int I:{A,C,B})
            {
                Indices.Add(V.Num());V.Add(Hull[I]);Normals.Add(Normal);
                UV.Add(FMath::Abs(Normal.X)>.5?FVector2D(Hull[I].Y,Hull[I].Z)/100.:FVector2D(Hull[I].X,Hull[I].Z)/100.);
            }
        };
        for(const auto Q:{FIntVector(0,2,1),FIntVector(0,3,2),FIntVector(4,5,6),FIntVector(4,6,7),
            FIntVector(0,1,5),FIntVector(0,5,4),FIntVector(1,2,6),FIntVector(1,6,5),
            FIntVector(2,3,7),FIntVector(2,7,6),FIntVector(3,0,4),FIntVector(3,4,7)})Triangle(Q.X,Q.Y,Q.Z);
        auto* M=NewObject<UProceduralMeshComponent>(this,MakeUniqueObjectName(this,UProceduralMeshComponent::StaticClass(),TEXT("NoticeMoneyChangerBody")));
        M->SetupAttachment(RootComponent);M->SetMobility(EComponentMobility::Movable);
        M->SetCollisionEnabled(ECollisionEnabled::NoCollision);M->SetCollisionObjectType(ECC_WorldStatic);
        M->SetCollisionResponseToAllChannels(ECR_Block);M->SetGenerateOverlapEvents(false);
        M->bUseComplexAsSimpleCollision=false;M->bUseAsyncCooking=false;
        M->CreateMeshSection_LinearColor(0,V,Indices,Normals,UV,TArray<FLinearColor>{},TArray<FProcMeshTangent>{},false);
        M->AddCollisionConvexMesh(Hull);M->GetBodySetup()->CollisionTraceFlag=CTF_UseSimpleAsComplex;
        if(auto* Base=LoadObject<UMaterialInterface>(nullptr,TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial")))
        {auto* Mat=UMaterialInstanceDynamic::Create(Base,M);Mat->SetVectorParameterValue(TEXT("Color"),Plaster);M->SetMaterial(0,Mat);}
        M->RegisterComponent();AddInstanceComponent(M);M->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
        NoticeBuildingMeshes.Add(M);
    }
    // Top faces meet at the actual 7.5 m east-west ridge. The normal offset
    // puts all roof thickness below the specified walking surface.
    for(int Half=0;Half<2;++Half)
    {
        const double Y0=Half?800:340,Y1=Half?1360:800,Slope=Half?-N::RoofSlope:N::RoofSlope;
        const FRotator Rotation=FRotationMatrix::MakeFromXY(FVector::ForwardVector,FVector(0,1,Slope)).Rotator();
        const FVector Normal=Rotation.RotateVector(FVector::UpVector);
        const FVector At=FVector(960,(Y0+Y1)*.5,N::RoofHeight((Y0+Y1)*.5))-Normal*N::RoofThickness*.5;
        Box(Half?TEXT("NoticeMoneyChangerRoofNorth"):TEXT("NoticeMoneyChangerRoofSouth"),At,
            FVector(780,(Y1-Y0)*FMath::Sqrt(1+Slope*Slope),N::RoofThickness),Tile,true,Rotation);
    }
    Box(TEXT("NoticePentRoof"),FVector(N::Pent.X,N::Pent.Y,N::Pent.Z),FVector(N::Pent.SX,N::Pent.SY,N::Pent.SZ),Wood,true,FRotator::ZeroRotator,TEXT("Timber"));
    for(int X:{470,580})for(int Y:{920,1480})
        Box(TEXT("NoticePentPost"),FVector(X,Y,150),FVector(20,20,300),Wood,true,FRotator::ZeroRotator,TEXT("Timber"));
    // Two storeys and an occupied facade remain visible around the route.
    // These surface details do not add collision outside the closed body.
    for(int Z:{250,470})for(int X:{760,1110})
        Box(TEXT("NoticeMoneyChangerShutter"),FVector(X,398,Z),FVector(150,4,95),Wood,false,FRotator::ZeroRotator,TEXT("Timber"));
    for(int Z:{40,310})
        Box(TEXT("NoticeMoneyChangerBeam"),FVector(960,395,Z),FVector(720,10,14),Wood,false,FRotator::ZeroRotator,TEXT("Timber"));
    // Low warm spill behind the occupied house's shutters identifies the
    // ladder ends. These are real world lights, also read by guard perception.
    // Their frames stay clear of the validated capsule and drone corridors.
    for(int I=0;I<2;++I)
    {
        const FVector Window=I?FVector(597,1120,450):FVector(680,1303,230);
        const FVector Out=I?FVector(-1,0,0):FVector(0,1,0);
        const FVector Across=I?FVector(0,1,0):FVector(1,0,0);
        Box(TEXT("NoticeWarmWindowFrame"),Window,Across*110+Out.GetAbs()*8+FVector(0,0,100),Wood,false,FRotator::ZeroRotator,TEXT("Timber"));
        auto* Pane=Box(TEXT("NoticeWarmWindowPaper"),Window+Out*5,Across*94+Out.GetAbs()*2+FVector(0,0,84),FLinearColor(1,.58,.23),false);
        if(auto* Base=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Generated/Materials/M_ArenaGlow.M_ArenaGlow"),nullptr,LOAD_NoWarn))
        {
            auto* Mat=UMaterialInstanceDynamic::Create(Base,Pane);Mat->SetVectorParameterValue(TEXT("Color"),FLinearColor(1,.58,.23)*.18f);Pane->SetMaterial(0,Mat);
        }
        for(int Bar:{-30,0,30})
            Box(TEXT("NoticeWarmWindowLattice"),Window+Out*8+Across*Bar,Across*4+Out.GetAbs()*4+FVector(0,0,84),Wood,false,FRotator::ZeroRotator,TEXT("Timber"));
        if(auto* Light=GetWorld()->SpawnActor<APointLight>(Window+Out*30,FRotator::ZeroRotator))
        {
            Light->Tags.Add(TEXT("NoticeRouteWindow"));Light->SetMobility(EComponentMobility::Movable);
            auto* Glow=Light->PointLightComponent.Get();Glow->SetIntensityUnits(ELightUnits::Lumens);Glow->SetIntensity(180.f);
            Glow->SetAttenuationRadius(450.f);Glow->SetSourceRadius(24.f);
            Glow->SetUseTemperature(true);Glow->SetTemperature(1900.f);Glow->SetCastShadows(true);DecorActors.Add(Light);
        }
    }
}
