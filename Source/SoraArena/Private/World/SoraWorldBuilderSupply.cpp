#include "SoraWorldBuilder.h"
#include "SoraCatalog.h"
#include "SoraPlayerCharacter.h"
#include "SoraTenementDefenseRules.h"
#include "Game/SoraCampaignReach.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"

void ASoraWorldBuilder::StageSupply(const FSoraBeat& Beat)
{
    const bool Kitchen=Beat.SupplyPoint==TEXT("vol_b14_supply")&&Beat.Space.bTenementDefense;
    const bool Spire=Beat.SupplyPoint==TEXT("sp_spire_base")&&Beat.Space.Spire.Enabled()&&!Beat.Space.Spire.Ramp.IsEmpty();
    if(!Kitchen&&!Spire)return;
    SupplyId=Beat.SupplyPoint;
    const auto P=SoraTenementDefenseRules::SupplyAt,Size=SoraTenementDefenseRules::SupplySize;
    SupplyAt=Kitchen?FVector(P.X,P.Y,P.Z):Beat.Space.Spire.Ramp[0]+FVector(300,100,0);
    const FVector CrateSize=Kitchen?FVector(Size.X,Size.Y,Size.Z):FVector(120,80,70);
    const TCHAR* Cube=TEXT("/Engine/BasicShapes/Cube.Cube");
    const FLinearColor Wood(.30f,.19f,.09f),Teal(.05f,.42f,.35f),Paper(.8f,.73f,.55f);
    SupplyCrate=KitShape(TEXT("LeagueSupply"),Cube,SupplyAt+FVector(0,0,CrateSize.Z*.5),CrateSize/100.,Wood,TEXT("Timber"),true);
    KitShape(TEXT("SupplyCloth"),Cube,SupplyAt+FVector(0,0,CrateSize.Z+1),
        FVector(CrateSize.X+2,CrateSize.Y+2,2)/100.,Teal);
    // Explicit functional proxies: an arrow bundle and wrapped cartridges.
    // Final crate craft and League mark belong to the art lane.
    for(int32 N=0;N<6;++N)
        KitShape(TEXT("SupplyArrow"),Cube,SupplyAt+FVector(-28+N*6,0,75),FVector(.018,Kitchen?.6:.7,.018),Paper);
    KitShape(TEXT("SupplyCartridges"),Cube,SupplyAt+FVector(Kitchen?23:35,10,78),FVector(.25,.3,.12),Paper);
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
    if(Id==TEXT("vol_b14_supply"))
    {
        const auto At=Hero.GetActorLocation();
        if(!SoraTenementDefenseRules::SupplyReach(true,At.X,At.Y,Feet))return false;
    }
    else if(FMath::Abs(Feet-Floor.Z)>20||FVector::Dist2D(Hero.GetActorLocation(),Floor)>SoraCampaignReach::Interact)return false;
    FHitResult Hit;
    const FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraSupplyReach),false,&Hero);
    return GetWorld()->LineTraceSingleByChannel(Hit,Hero.GetCamera()->GetComponentLocation(),Floor+FVector(0,0,55),
        ECC_Visibility,Query)&&Hit.GetComponent()==SupplyCrate;
}
