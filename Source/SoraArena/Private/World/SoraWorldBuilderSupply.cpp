#include "SoraWorldBuilder.h"
#include "SoraCatalog.h"
#include "SoraPlayerCharacter.h"
#include "Game/SoraCampaignReach.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"

void ASoraWorldBuilder::StageSupply(const FSoraBeat& Beat)
{
    // This slice stages the authored L1 engineers' cache only. Other supply
    // identities remain data for their own place-specific implementations.
    if(Beat.SupplyPoint!=TEXT("sp_spire_base")||!Beat.Space.Spire.Enabled()||
        Beat.Space.Spire.Ramp.IsEmpty()) return;
    SupplyId=Beat.SupplyPoint;
    SupplyAt=Beat.Space.Spire.Ramp[0]+FVector(300,100,0);
    const TCHAR* Cube=TEXT("/Engine/BasicShapes/Cube.Cube");
    const FLinearColor Wood(.30f,.19f,.09f),Teal(.05f,.42f,.35f),Paper(.8f,.73f,.55f);
    SupplyCrate=KitShape(TEXT("LeagueSupply"),Cube,SupplyAt+FVector(0,0,35),FVector(1.2,.8,.7),Wood,TEXT("Timber"),true);
    KitShape(TEXT("SupplyCloth"),Cube,SupplyAt+FVector(0,0,71),FVector(1.22,.82,.02),Teal);
    // Explicit functional proxies: an arrow bundle and wrapped cartridges.
    // Final crate craft and League mark belong to the art lane.
    for(int32 N=0;N<6;++N)
        KitShape(TEXT("SupplyArrow"),Cube,SupplyAt+FVector(-28+N*6,0,75),FVector(.018,.7,.018),Paper);
    KitShape(TEXT("SupplyCartridges"),Cube,SupplyAt+FVector(35,10,78),FVector(.25,.3,.12),Paper);
}
bool ASoraWorldBuilder::SupplyFloor(const FString& Id,FVector& Out) const
{
    if(Id.IsEmpty()||Id!=SupplyId||!SupplyCrate) return false;
    Out=SupplyAt;
    return true;
}
bool ASoraWorldBuilder::CanReachSupply(const FString& Id,const ASoraPlayerCharacter& Hero) const
{
    FVector Floor;
    if(!SupplyFloor(Id,Floor)||!Hero.GetCharacterMovement()->IsMovingOnGround()) return false;
    const float Feet=Hero.GetActorLocation().Z-Hero.GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    if(FMath::Abs(Feet-Floor.Z)>20||FVector::Dist2D(Hero.GetActorLocation(),Floor)>SoraCampaignReach::Interact) return false;
    FHitResult Hit;
    const FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraSupplyReach),false,&Hero);
    return GetWorld()->LineTraceSingleByChannel(Hit,Hero.GetCamera()->GetComponentLocation(),Floor+FVector(0,0,55),
        ECC_Visibility,Query)&&Hit.GetComponent()==SupplyCrate;
}
