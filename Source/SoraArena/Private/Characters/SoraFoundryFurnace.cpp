#include "SoraFoundryFurnace.h"
#include "SoraCampaignDirector.h"
#include "SoraFoundryDefenseRules.h"
#include "SoraGameMode.h"
#include "SoraViewmodelComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/World.h"
ASoraFoundryFurnace::ASoraFoundryFurnace()
{
    FurnaceMesh=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("FurnaceShell"));
    FurnaceMesh->SetupAttachment(GetRootComponent());
    FurnaceMesh->SetRelativeScale3D(FVector(1.8,1.8,2.2));
    FurnaceMesh->SetCollisionProfileName(TEXT("BlockAllDynamic"));
    GetCapsuleComponent()->SetCapsuleSize(90,110);
    GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}
void ASoraFoundryFurnace::BeginPlay()
{
    Super::BeginPlay();
    GetMesh()->SetHiddenInGame(true,true);
    for(const auto& Part:BodyParts) if(Part) Part->SetHiddenInGame(true,true);
    GetViewmodel()->SetHiddenInGame(true,true);
    GetCharacterMovement()->DisableMovement();
    GetCharacterMovement()->SetComponentTickEnabled(false);
    FurnaceMesh->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
    Health=MaxHealth=SoraFoundryDefenseRules::FurnaceHp;
}
bool ASoraFoundryFurnace::AdmitDamage(float& Damage,FSoraHit& Hit,AActor* Causer)
{
    auto* M=GetWorld()?Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode()):nullptr;
    auto* C=M?M->Campaign():nullptr;
    if(C&&C->IsFoundryDefense())
    {
        C->DamageDefendedTarget(0,FMath::Max(1,FMath::RoundToInt32(Damage)));
        Health=C->TaskProgress().TargetHp[0];
    }
    Damage=0; return false;
}
