#include "SoraFieldcraft.h"
#include "SoraCatalog.h"
#include "SoraCompanion.h"
#include "SoraGameMode.h"
#include "SoraGameEvents.h"
#include "SoraLanternWorkshopRules.h"
#include "SoraPlayerCharacter.h"
#include "SoraWorldBuilder.h"
#include "SoraWorkshopProp.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"

void USoraFieldcraft::ClearWorkshop()
{
    ++WorkshopGeneration;
    if(auto* Bus=USoraGameEvents::Get(this))Bus->OnDetonated.Remove(WorkshopBurst);
    WorkshopBurst.Reset();
    for(const auto& Prop:WorkshopProps)if(IsValid(Prop))Prop->Destroy();
    WorkshopProps.Reset();
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
    // These hazardous/destructible proxies belong to the defense encounter;
    // the following manufacturing beat starts with a cleared work yard.
    if(!bWorkshopFight)return;
    namespace H=SoraWorkshopHazardRules;
    Params.Owner=Props;
    for(int I=-1;I<int(UE_ARRAY_COUNT(H::Covers));++I)
    {
        const FVector At=I<0?FVector(H::OilX,H::OilY,H::OilHalfHeightCm):
            FVector(H::Covers[I].X,H::Covers[I].Y,H::Covers[I].Height*.5f);
        if(auto* Prop=GetWorld()->SpawnActor<ASoraWorkshopProp>(At,FRotator::ZeroRotator,Params))
        {Prop->Build(I);WorkshopProps.Add(Prop);}
    }
    if(auto* Bus=USoraGameEvents::Get(this))WorkshopBurst=Bus->OnDetonated.AddUObject(this,&USoraFieldcraft::WorkshopDetonated);
}

void USoraFieldcraft::WorkshopDetonated(const FSoraDetonatedEvent& Event)
{
    const auto* Mode=Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode());
    if(!bWorkshopFight||!Mode||!Mode->IsPlaying()||GetWorld()->IsPaused())return;
    // Sample every line before breaking any cover. One blast cannot acquire
    // different oil reach merely by changing delegate/prop iteration order.
    TArray<TWeakObjectPtr<ASoraWorkshopProp>> Reached;
    for(const auto& Prop:WorkshopProps)
        if(IsValid(Prop)&&!Prop->IsActorBeingDestroyed()&&Prop->BlastReaches(Event.Location,Event.Radius,Event.Damage))Reached.Add(Prop);
    for(const auto& Weak:Reached)if(auto* Prop=Weak.Get())Prop->Detonate(Event.Damage);
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

void USoraFieldcraft::TickWorkshop(int32 DtMs)
{
    const uint32 Generation=WorkshopGeneration;
    const auto CurrentProps=WorkshopProps;
    for(const auto& Prop:CurrentProps)
    {
        if(Generation!=WorkshopGeneration)return;
        if(IsValid(Prop)&&!Prop->IsActorBeingDestroyed())Prop->StepFire(DtMs);
    }
    if(!bWorkshopFight||!bWorkshopSealCut)return;
    for(int I=0;I<WorkshopPeople.Num();++I)
        if(auto* Person=WorkshopPeople[I].Get();IsValid(Person))
        {
            const auto P=SoraLanternWorkshopRules::CraftShelter(I);
            Person->SetGoal(FVector(P.X,P.Y,135.15),180.f,220.f);
        }
}
