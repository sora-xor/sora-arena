#include "SoraProjectile.h"
#include "SoraWorldBuilder.h"
#include "SoraSettings.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"

void ASoraProjectile::ShowArcWarning(const FVector& Landing,float FlightSeconds)
{
    if(bArrow||FlightSeconds<=0||ArcWarning.IsValid())return;
    auto* Warning=GetWorld()->SpawnActor<AActor>();if(!Warning)return;
    Warning->SetOwner(this);Warning->Tags.Add(TEXT("WorkshopShellArc"));ArcWarning=Warning;
    auto* Root=NewObject<USceneComponent>(Warning);Warning->SetRootComponent(Root);Root->RegisterComponent();
    const auto Color=SoraAccessibility::TelegraphColor(this,SoraAccessibility::ETelegraph::Cleave);
    const auto Segment=[&](FVector A,FVector B,const FString& Name)
    {
        auto* Mesh=ASoraWorldBuilder::Shape(Warning,Root,Name,TEXT("/Engine/BasicShapes/Cube.Cube"),
            (A+B)*.5,FVector((B-A).Size()/100.f,.025f,.025f),Color,false);
        Mesh->SetRelativeRotation((B-A).Rotation());Mesh->SetCastShadow(false);
    };
    const FVector Origin=GetActorLocation();
    const auto At=[&](float T){return Origin+Velocity*T-FVector(0,0,.5f*Gravity*T*T);};
    for(int I=0;I<24;++I)Segment(At(FlightSeconds*I/24.f),At(FlightSeconds*(I+1)/24.f),FString::Printf(TEXT("Arc%d"),I));
    for(int I=0;I<32;++I)
    {
        const auto Point=[&](int N){const float A=2*PI*N/32.f;return Landing+FVector(FMath::Cos(A)*Radius,FMath::Sin(A)*Radius,3);};
        Segment(Point(I),Point(I+1),FString::Printf(TEXT("Landing%d"),I));
    }
    // The projectile owns this warning. Early collision, teardown and retry
    // remove it immediately through EndPlay; pause freezes both together.
}
