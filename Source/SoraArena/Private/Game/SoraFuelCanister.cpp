#include "SoraFuelCanister.h"
#include "Combat/SoraDamage.h"
#include "SoraFieldcraft.h"
#include "SoraGameEvents.h"
#include "SoraGameMode.h"
#include "SoraWorldBuilder.h"
#include "Components/CapsuleComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/Controller.h"
#include "GameFramework/Pawn.h"

namespace Fuel=SoraFuelCanisterRules;
ASoraFuelCanister::ASoraFuelCanister()
{
    PrimaryActorTick.bCanEverTick=true; PrimaryActorTick.bStartWithTickEnabled=false;
    Collision=CreateDefaultSubobject<UCapsuleComponent>(TEXT("CanisterCollision")); RootComponent=Collision;
    Collision->InitCapsuleSize(Fuel::BodyRadiusCm,Fuel::BodyHalfHeightCm);
    // Stage places the actor center one half-height above its authored floor.
    Collision->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    Collision->SetCollisionObjectType(ECC_WorldDynamic); Collision->SetCollisionResponseToAllChannels(ECR_Block);
    Collision->SetGenerateOverlapEvents(false); Collision->SetCanEverAffectNavigation(true);
    Light=CreateDefaultSubobject<UPointLightComponent>(TEXT("FuelGlow")); Light->SetupAttachment(Collision);
    Light->SetIntensity(650); Light->SetAttenuationRadius(300); Light->SetLightColor(FLinearColor(.15f,.95f,.75f));
    Light->SetCastShadows(false);
}
void ASoraFuelCanister::Build(FName InId)
{
    Id=InId; Tags.Add(TEXT("SoraFuelCanister"));
    // Keep the root collider centered above the floor. Its actor position is
    // the body center; the typed floor coordinate is used by StageCanisters.
    Body=ASoraWorldBuilder::Shape(this,Collision,TEXT("ProvisionalFuelBody"),TEXT("/Engine/BasicShapes/Cylinder.Cylinder"),
        FVector::ZeroVector,FVector(.6f,.6f,1.4f),FLinearColor(.16f,.23f,.24f));
    Band=ASoraWorldBuilder::Shape(this,Collision,TEXT("ProvisionalFuelBand"),TEXT("/Engine/BasicShapes/Cylinder.Cylinder"),
        FVector(0,0,20),FVector(.63f,.63f,.12f),FLinearColor(.15f,1.f,.75f));
    Flash=ASoraWorldBuilder::Shape(this,Collision,TEXT("ProvisionalFuelBurst"),TEXT("/Engine/BasicShapes/Sphere.Sphere"),
        FVector::ZeroVector,FVector(Fuel::BlastRadiusCm/50.f),FLinearColor(1.f,.35f,.035f));
    Flash->SetVisibility(false);
}
float ASoraFuelCanister::TakeDamage(float Amount,const FDamageEvent& Event,AController* EventInstigator,AActor* Causer)
{
    if(IsActorBeingDestroyed()||!Event.IsOfType(FSoraDamageEvent::ClassID)) return 0;
    const auto* Mode=Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode());
    const auto& Shot=static_cast<const FSoraDamageEvent&>(Event).Hit;
    if(!State.Shot(Shot.Kind,Amount,Mode&&Mode->IsPlaying()&&!GetWorld()->IsPaused())) return 0;
    APawn* Shooter=EventInstigator?EventInstigator->GetPawn():Cast<APawn>(Causer);
    if(!Shooter&&Causer) Shooter=Causer->GetInstigator();
    SetInstigator(Shooter);
    Collision->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Body->SetVisibility(false); Band->SetVisibility(false); Flash->SetVisibility(true);
    Light->SetLightColor(FLinearColor(1.f,.35f,.035f)); Light->SetIntensity(9000); Light->SetAttenuationRadius(Fuel::BlastRadiusCm);
    FlashLeft=.12f; SetActorTickEnabled(true);
    const FVector At=GetActorLocation();
    if(auto* Bus=USoraGameEvents::Get(this))
    {
        FSoraDetonatedEvent Burst; Burst.Instigator=Shooter; Burst.Location=At; Burst.Radius=Fuel::BlastRadiusCm; Burst.Damage=Fuel::Damage;
        Bus->OnDetonated.Broadcast(Burst);
    }
    // The canister is the causer and the firing pawn its instigator: ordinary
    // self-blast/ally exclusions, shields, invulnerability and credit remain.
    // Do not access owned state after callbacks can restage/destroy this actor.
    SoraDamage::Blast(*GetWorld(),Fuel::Damage,Fuel::BlastRadiusCm,FSoraHit::Blast(At,INDEX_NONE),EventInstigator,this);
    return Amount;
}
void ASoraFuelCanister::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds); FlashLeft=FMath::Max(0.f,FlashLeft-DeltaSeconds);
    if(FlashLeft<=0) { Flash->SetVisibility(false); Light->SetVisibility(false); SetActorTickEnabled(false); }
}

void USoraFieldcraft::StageCanisters(const FSoraBeat& Beat)
{
    for(const auto& Item:Beat.Space.FuelCanisters)
    {
        FActorSpawnParameters Params; Params.Owner=Props; Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Canister=GetWorld()->SpawnActor<ASoraFuelCanister>(Item.Floor+FVector(0,0,Fuel::BodyHalfHeightCm),FRotator::ZeroRotator,Params);
        if(Canister) { Canister->Build(Item.Id); FuelCanisters.Add(Canister); }
    }
}
