#include "SoraArcheryTarget.h"
#include "SoraArcheryRules.h"
#include "SoraWorldBuilder.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"

ASoraArcheryTarget::ASoraArcheryTarget()
{
    PrimaryActorTick.bCanEverTick=false;
    Face=CreateDefaultSubobject<UBoxComponent>(TEXT("MatoFace"));
    RootComponent=Face;
    Face->SetCanEverAffectNavigation(false);
    Face->SetCollisionObjectType(ECC_WorldDynamic);
    Face->SetCollisionResponseToAllChannels(ECR_Ignore);
    Face->SetCollisionResponseToChannel(ECC_WorldDynamic,ECR_Block);
    Face->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
    Face->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
}
void ASoraArcheryTarget::Configure(int32 InIndex,const FVector& Center,float InRadius,float Diameter)
{
    Index=InIndex; Rest=Center; Radius=InRadius;
    Face->SetBoxExtent(FVector(2,Radius,Radius));
    SetActorLocation(Rest);
    // The collision circle is validated at impact, including the Easy/Normal
    // assist outside the physical 36 cm near face. Final woven art is pending.
    auto* Disc=ASoraWorldBuilder::Shape(this,RootComponent,TEXT("MatoPaper"),
        TEXT("/Engine/BasicShapes/Cylinder.Cylinder"),FVector::ZeroVector,
        FVector(Diameter/100.f,Diameter/100.f,.025f),FLinearColor(.83f,.76f,.57f));
    // Cylinder's axis is Z; a yaw-independent pitch puts its face toward -X.
    Disc->SetRelativeRotation(FRotator(90,0,0));
    for(int32 Ring=0;Ring<2;++Ring)
    {
        auto* Mark=ASoraWorldBuilder::Shape(this,RootComponent,FString::Printf(TEXT("MatoRing%d"),Ring),
            TEXT("/Engine/BasicShapes/Cylinder.Cylinder"),FVector(-2.f-Ring,0,0),
            FVector(Diameter/100.f*(Ring?.20f:.58f),Diameter/100.f*(Ring?.20f:.58f),.006f),
            Ring?FLinearColor(.9f,.84f,.66f):FLinearColor(.11f,.09f,.07f));
        Mark->SetRelativeRotation(FRotator(90,0,0));
    }
}
FVector ASoraArcheryTarget::CenterAt(int32 Milliseconds) const
{
    if(Index==0) return Rest;
    const float Phase=2.f*PI*float(Milliseconds%SoraArcheryRules::PeriodMs)/SoraArcheryRules::PeriodMs+
        (Index-1)*2.f*PI/3.f;
    return Rest+FVector(0,SoraArcheryRules::SwingCm*FMath::Sin(Phase),0);
}
void ASoraArcheryTarget::MoveForClock(int32 Milliseconds) { SetActorLocation(CenterAt(Milliseconds)); }
bool ASoraArcheryTarget::ContainsImpact(const FHitResult& Hit) const
{
    const FVector Local=Hit.ImpactPoint-GetActorLocation();
    return Hit.GetActor()==this&&Local.Y*Local.Y+Local.Z*Local.Z<=Radius*Radius;
}
void ASoraArcheryTarget::SetAvailable(bool bAvailable)
{
    SetActorHiddenInGame(!bAvailable);
    Face->SetCollisionEnabled(bAvailable?ECollisionEnabled::QueryOnly:ECollisionEnabled::NoCollision);
}
