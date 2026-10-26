#include "SoraWorkshopProp.h"
#include "Combat/SoraDamage.h"
#include "SoraCharacterBase.h"
#include "SoraEnemy.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "SoraWorldBuilder.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"

namespace R=SoraWorkshopHazardRules;
ASoraWorkshopProp::ASoraWorkshopProp()
{
    Collision=CreateDefaultSubobject<UBoxComponent>(TEXT("WorkshopPropCollision"));RootComponent=Collision;
    Collision->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    Collision->SetCollisionObjectType(ECC_WorldDynamic);Collision->SetCollisionResponseToAllChannels(ECR_Block);
    Collision->SetGenerateOverlapEvents(false);Collision->SetCanEverAffectNavigation(true);
    Light=CreateDefaultSubobject<UPointLightComponent>(TEXT("OilFireLight"));Light->SetupAttachment(Collision);
    Light->SetIntensity(3500);Light->SetAttenuationRadius(350);Light->SetLightColor(FLinearColor(1,.35f,.025f));
    Light->SetCastShadows(false);Light->SetVisibility(false);
}
void ASoraWorkshopProp::Build(int Index)
{
    CoverIndex=Index;
    const auto Add=[&](const TCHAR* Name,const TCHAR* Mesh,FVector At,FVector Scale,FLinearColor Color)
    {
        auto* P=ASoraWorldBuilder::Shape(this,Collision,Name,Mesh,At,Scale,Color);
        Pieces.Add(P);return P;
    };
    const TCHAR* Cube=TEXT("/Engine/BasicShapes/Cube.Cube");
    if(IsOil())
    {
        Tags.Add(TEXT("SoraWorkshopOil"));
        Collision->SetBoxExtent(FVector(R::OilRadiusCm,R::OilRadiusCm,R::OilHalfHeightCm));
        Add(TEXT("ProvisionalOilJars"),TEXT("/Engine/BasicShapes/Cylinder.Cylinder"),FVector::ZeroVector,
            FVector(R::OilRadiusCm/50.f,R::OilRadiusCm/50.f,R::OilHalfHeightCm/50.f),FLinearColor(.25f,.12f,.055f));
        Flame=ASoraWorldBuilder::Shape(this,Collision,TEXT("ProvisionalOilFire"),
            TEXT("/Engine/BasicShapes/Cylinder.Cylinder"),FVector(0,0,5-R::OilHalfHeightCm),
            FVector(R::FireRadiusCm/50.f,R::FireRadiusCm/50.f,.1f),FLinearColor(1,.24f,.015f));
        Flame->SetVisibility(false);
    }
    else
    {
        Tags.Add(TEXT("SoraWorkshopSoftCover"));const auto& C=R::Covers[Index];Health=C.Health;
        Collision->SetBoxExtent(FVector(C.SX*.5f,C.SY*.5f,C.Height*.5f));
        // A legged frame with a narrow bamboo/board face. The simple bounding
        // collider deliberately supplies continuous low cover until broken.
        for(int Sign:{-1,1})Add(TEXT("ProvisionalRackPost"),Cube,FVector(Sign*(C.SX*.5f-6),0,0),
            FVector(.1f,C.SY/100.f,C.Height/100.f),FLinearColor(.32f,.2f,.08f));
        Add(TEXT("ProvisionalRackFace"),Cube,FVector(0,0,C.Height*.2f),
            FVector(C.SX/100.f,.08f,C.Height*.006f),FLinearColor(.42f,.31f,.14f));
    }
}
bool ASoraWorkshopProp::Playing() const
{
    const auto* Mode=GetWorld()?Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode()):nullptr;
    return !IsActorBeingDestroyed()&&Mode&&Mode->IsPlaying()&&!GetWorld()->IsPaused();
}
bool ASoraWorkshopProp::ClearLine(const FVector& From,const FVector& To) const
{
    FCollisionObjectQueryParams Solid;Solid.AddObjectTypesToQuery(ECC_WorldStatic);Solid.AddObjectTypesToQuery(ECC_WorldDynamic);
    FCollisionQueryParams Q(SCENE_QUERY_STAT(WorkshopOilCover),false,this);
    // Live bodies and corpses cannot become blast/fire-cover walls.
    for(TActorIterator<ASoraCharacterBase> It(GetWorld());It;++It)Q.AddIgnoredActor(*It);
    return !GetWorld()->LineTraceTestByObjectType(From,To,Solid,Q);
}
bool ASoraWorkshopProp::BlastReaches(const FVector& At,float Radius,float Damage) const
{
    return !IsSpent()&&R::BlastReaches(FVector::Distance(At,GetActorLocation()),Radius,Damage,true)&&
        ClearLine(At,GetActorLocation());
}
void ASoraWorkshopProp::Break()
{
    Collision->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    for(auto& P:Pieces)if(IsValid(P))P->SetVisibility(false);
}
float ASoraWorkshopProp::TakeDamage(float Amount,const FDamageEvent& Event,AController*,AActor*)
{
    if(IsOil()||!Event.IsOfType(FSoraDamageEvent::ClassID))return 0;
    const int Applied=R::BreakCover(Health,static_cast<const FSoraDamageEvent&>(Event).Hit.Kind,Amount,Playing());
    if(Applied&&Health==0)Break();
    return Applied;
}
void ASoraWorkshopProp::Detonate(float Damage)
{
    if(!Playing()||IsSpent())return;
    if(IsOil())
    {
        if(Fire.Ignite()){Break();Flame->SetVisibility(true);Light->SetVisibility(true);}
    }
    else
    {
        const int Applied=R::BreakCover(Health,SoraCombatRules::EHit::Blast,Damage,true);
        if(Applied&&Health==0)Break();
    }
}
void ASoraWorkshopProp::StepFire(int DtMs)
{
    if(!Playing()||Fire.LeftMs<=0)return;
    const int Active=Fire.Advance(DtMs);if(Active<=0)return;
    struct FPending{TWeakObjectPtr<ASoraCharacterBase> Body;int Damage;};TArray<FPending> Pending;
    for(TActorIterator<ASoraCharacterBase> It(GetWorld());It;++It)
    {
        auto* Body=*It;
        if(!Body->IsAlive()||Body->IsActorBeingDestroyed()||(!Cast<ASoraPlayerCharacter>(Body)&&!Cast<ASoraEnemy>(Body)))continue;
        const FVector At=Body->GetActorLocation();
        const double Feet=At.Z-Body->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
        // Contact is measured at the feet, with a ground-level obstruction
        // trace. Interior floors, the roof, jumps and walls block exposure.
        if(!R::FloorContact(At.X,At.Y,Feet)||!ClearLine(FVector(R::OilX,R::OilY,15),FVector(At.X,At.Y,15)))continue;
        int& Carry=Exposure.FindOrAdd(Body);const int Damage=R::Burn(Carry,Active);
        if(Damage)Pending.Add({Body,Damage});
    }
    for(auto It=Exposure.CreateIterator();It;++It)if(!It.Key().IsValid()||!It.Key()->IsAlive())It.RemoveCurrent();
    if(Fire.LeftMs==0){Flame->SetVisibility(false);Light->SetVisibility(false);Exposure.Reset();}
    for(const auto& P:Pending)
    {
        // A death callback can destroy all workshop props or end play. Never
        // apply the remaining old-stage hits after that synchronous change.
        if(!Playing())break;
        auto* Body=P.Body.Get();if(!IsValid(Body)||!Body->IsAlive()||Body->IsActorBeingDestroyed())continue;
        FHitResult Trace;Trace.ImpactPoint=Body->GetActorLocation();
        auto Hit=FSoraHit::Hazard(FVector(R::OilX,R::OilY,0));
        Hit.EnvironmentalRate=SoraCombatRules::EEnvironmentalRate::WorkshopOil;
        // Spilled oil is environmental: it hurts either side without taking
        // the ignition shell's faction. Normal death/subdue credit still runs.
        SoraDamage::Strike(Body,P.Damage,Hit,FVector::UpVector,Trace,nullptr,this);
    }
}
