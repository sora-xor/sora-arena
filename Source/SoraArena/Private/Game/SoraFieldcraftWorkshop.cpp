#include "SoraFieldcraft.h"
#include "SoraCatalog.h"
#include "SoraCompanion.h"
#include "SoraGameMode.h"
#include "SoraLanternWorkshopRules.h"
#include "SoraPlayerCharacter.h"
#include "SoraWorldBuilder.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"

void USoraFieldcraft::ClearWorkshop()
{
    for(const auto& Person:WorkshopPeople)if(IsValid(Person))Person->Destroy();
    WorkshopPeople.Reset();bWorkshopFight=false;bWorkshopSealCut=false;
}

void USoraFieldcraft::StageWorkshop(const FSoraBeat& Beat)
{
    if(!Beat.Space.bLanternWorkshop)return;
    namespace R=SoraLanternWorkshopRules;
    bWorkshopFight=Beat.Id==TEXT("ch03.b08");
    FActorSpawnParameters Params;
    Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    for(int I=0;I<R::CraftspersonCount;++I)
    {
        const auto P=bWorkshopFight?R::CraftStart(I):R::CraftShelter(I);
        auto* Person=GetWorld()->SpawnActor<ASoraCompanion>(FVector(P.X,P.Y,135.15),FRotator(0,180,0),Params);
        WorkshopPeople.Add(Person);
        if(!Person)continue;
        FSoraCompanionSpec Spec;
        Spec.Id=FString::Printf(TEXT("workshop_craftsperson_%d"),I+1);
        Spec.Role=TEXT("bystander");Spec.bDetectable=false;
        Spec.Rules={100,false,3000,0,0,false,0};
        Person->Init(Spec,I);
        Person->GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Ignore);
    }
}

bool USoraFieldcraft::CanCutWorkshopSeal(const ASoraPlayerCharacter& Player) const
{
    const FVector P=Player.GetActorLocation();
    return NeedsWorkshopSeal()&&SoraLanternWorkshopRules::CanCutSeal(P.X,P.Y,
        P.Z-Player.GetCapsuleComponent()->GetScaledCapsuleHalfHeight(),Player.GetCharacterMovement()->IsMovingOnGround());
}

void USoraFieldcraft::CutWorkshopSeal()
{
    if(!NeedsWorkshopSeal())return;
    bWorkshopSealCut=true;
    if(auto* Mode=Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode());Mode&&Mode->Arena())
        Mode->Arena()->ShowWorkshopDoor(false,true);
    // Release the opening wave only after the completed physical hold.
    Raise(TEXT("workshop_seal_cut"));
}

void USoraFieldcraft::TickWorkshop()
{
    if(!bWorkshopFight||!bWorkshopSealCut)return;
    for(int I=0;I<WorkshopPeople.Num();++I)
        if(auto* Person=WorkshopPeople[I].Get();IsValid(Person))
        {
            const auto P=SoraLanternWorkshopRules::CraftShelter(I);
            Person->SetGoal(FVector(P.X,P.Y,135.15),180.f,220.f);
        }
}
