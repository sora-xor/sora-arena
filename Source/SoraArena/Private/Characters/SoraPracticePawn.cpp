#include "SoraPracticePawn.h"
#include "ArenaKernelSubsystem.h"
#include "SoraPracticeActors.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"

ASoraPracticePawn::ASoraPracticePawn(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer)
{
    AutoPossessAI=EAutoPossessAI::Disabled;
    bUseControllerRotationYaw=false;
    GetCharacterMovement()->bOrientRotationToMovement=false;
}
void ASoraPracticePawn::InitParticipant(int32 InSlot,const FSoraPracticeMap& Map,FLinearColor Color,bool bSora,bool bAlienBody)
{
    Slot=InSlot; bAlien=bAlienBody;
    ApplyClass(InSlot%6);
    BuildCat();
    // The kernel's body size first, so the banner stands on the right shoulders.
    SetKernelDriven(true,&Map);
    BuildBanner(Color,bSora);
}
void ASoraPracticePawn::InitDecoy(const FSoraPracticePlayer& Owner,const FSoraPracticeMap& Map,FLinearColor Color,bool bSora,bool bAlienBody)
{
    Slot=Owner.Slot; bAlien=bAlienBody; bDecoy=true;
    ApplyClass(Owner.ClassId);
    BuildCat();
    // A decoy is a body, not a participant: the kernel never moves it, and
    // its entity actor removes it. It stands idle, as its owner did.
    SetKernelDriven(true,&Map);
    BuildBanner(Color,bSora);
    FSoraPracticePlayer Still=Owner; Still.Alive=true; Still.MarkedTicks=0; Still.ChargeTicks=0; Still.ReloadTicks=0;
    KernelPreviousFeet=Still.Feet;
    ApplyKernelPlayer(Still);
}
void ASoraPracticePawn::BuildBanner(FLinearColor Color,bool bSora)
{
    for(const auto& Part:BannerParts) if(Part) Part->DestroyComponent();
    for(const auto& Part:MarkParts) if(Part) Part->DestroyComponent();
    BannerParts.Reset(); MarkParts.Reset();
    const float HalfHeight=GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight();
    TArray<USceneComponent*> Parts;
    SoraPracticeArt::Sashimono(this,GetCapsuleComponent(),HalfHeight,Color,bSora,false,&Parts);
    for(USceneComponent* Part:Parts) BannerParts.Add(Part);
    // The Teppo mark: a red ring with a pointer over the head, hidden unless marked.
    const float Over=HalfHeight+62.f;
    auto* Ring=SoraPracticeArt::Part(this,GetCapsuleComponent(),TEXT("MarkRing"),SoraPracticeArt::Cylinder,FVector(0,0,Over+22.f),FVector(.34f,.34f,.02f));
    auto* Pointer=SoraPracticeArt::Part(this,GetCapsuleComponent(),TEXT("MarkPointer"),SoraPracticeArt::Cone,FVector(0,0,Over),FVector(.16f,.16f,.24f),FRotator(180,0,0));
    for(UStaticMeshComponent* Part:{Ring,Pointer})
    {
        SoraPracticeArt::Glow(Part,FLinearColor(1.f,.08f,.05f),2.f);
        Part->SetVisibility(false);
        MarkParts.Add(Part);
    }
}
bool ASoraPracticePawn::IsShowingMark() const
{
    return MarkParts.Num()>0&&MarkParts[0]&&MarkParts[0]->IsVisible();
}
void ASoraPracticePawn::OnKernelSnapshot(const FSoraPracticePlayer& State)
{
    SetActorHiddenInGame(!State.Alive);
    for(const auto& Part:MarkParts) if(Part) Part->SetVisibility(State.Alive&&State.MarkedTicks>0);
}
