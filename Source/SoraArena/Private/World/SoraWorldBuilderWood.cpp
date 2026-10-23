#include "SoraWorldBuilder.h"
#include "SoraCatalog.h"
#include "SoraPlayerCharacter.h"
#include "SoraWoodRules.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"

void ASoraWorldBuilder::BuildChapterWood(const FSoraChapter& Chapter)
{
    WoodFloors.Reset(); WoodTargets.Reset(); WoodClapper=nullptr;
    if(!Chapter.Wood.Enabled()) return;
    const auto& W=Chapter.Wood;
    // Flat collision and primitive craft are explicitly provisional. These
    // continuous floors replace the old inaccessible optional cache island.
    const auto Path=[&](const TArray<FVector2D>& Points,const TCHAR* Name,bool Road)
    {
        for(int32 I=1;I<Points.Num();++I)
        {
            const FVector2D D=Points[I]-Points[I-1],C=(Points[I]+Points[I-1])*.5;
            Box(FString::Printf(TEXT("%s%d"),Name,I),FVector(C,Road?.5:-25),
                FVector(D.Size()+400,400,Road?1:50),FLinearColor(.29,.24,.17),!Road,
                FRotator(0,FMath::RadiansToDegrees(FMath::Atan2(D.Y,D.X)),0),TEXT("Soil"));
        }
    };
    Path(W.Approach,TEXT("WoodApproach"),false); Path(W.Terrace,TEXT("WoodTerrace"),false);
    Path(W.Bridge,TEXT("WoodSmithyBridge"),false); Path(W.Trail,TEXT("WoodTrail"),true);
    for(int32 I=0;I<W.Pois.Num();++I)
    {
        const FVector At=Floor(W.Pois[I]); WoodFloors.Add(At);
        // A small readable interaction proxy leaves a reachable standing
        // place. Final stone hollow, shrine, scenery and plaque art are open.
        const FLinearColor Color=I==SoraWoodRules::Shrine?FLinearColor(.4,.16,.1):FLinearColor(.48,.45,.37);
        auto* Target=Box(FString::Printf(TEXT("WoodPoi%d"),I),At+(I==SoraWoodRules::Vista?FVector(100,0,50):FVector(0,0,80)),
            I==SoraWoodRules::Vista?FVector(45,45,100):FVector(55,45,160),Color,true);
        WoodTargets.Add(Target);
    }
    // South-facing provisional clapper, with no floor across the ravine.
    // The authored origin and target centers are exactly 45 m apart.
    const FRotator Facing(0,(Floor(W.Pois[SoraWoodRules::Vista],150)-W.Naruko).Rotation().Yaw-90,0);
    WoodClapper=Box(TEXT("NarukoClapper"),W.Naruko,FVector(W.FaceCm.X,8,W.FaceCm.Y),FLinearColor(.66,.42,.15),true,Facing);
    Box(TEXT("NarukoCrossbar"),W.Naruko+FVector(0,0,W.FaceCm.Y*.5+20),FVector(100,12,12),FLinearColor(.24,.16,.08),true,Facing);
    for(int32 Side:{-1,1})
        Box(TEXT("NarukoPost")+FString::FromInt(Side),W.Naruko+Facing.RotateVector(FVector(Side*45,0,-30)),FVector(10,10,150),FLinearColor(.24,.16,.08),true,Facing);
}
bool ASoraWorldBuilder::CanReachWoodPoi(int32 Index,const ASoraPlayerCharacter& Hero) const
{
    if(!WoodFloors.IsValidIndex(Index)||!WoodTargets.IsValidIndex(Index)||!IsValid(WoodTargets[Index])||
        !Hero.GetCharacterMovement()->IsMovingOnGround()) return false;
    const auto At=WoodFloors[Index];
    const double Feet=Hero.GetActorLocation().Z-Hero.GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    if(FMath::Abs(Feet-At.Z)>SoraWoodRules::FloorToleranceCm||FVector::Dist2D(Hero.GetActorLocation(),At)>SoraWoodRules::ReachCm) return false;
    FHitResult Hit;
    const FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraWoodReach),false,&Hero);
    return GetWorld()->LineTraceSingleByChannel(Hit,Hero.GetCamera()->GetComponentLocation(),
        WoodTargets[Index]->GetComponentLocation(),ECC_Visibility,Query)&&Hit.GetComponent()==WoodTargets[Index];
}
bool ASoraWorldBuilder::IsWoodClapperHit(const FHitResult& Hit) const
{
    if(!IsValid(WoodClapper)||Hit.GetComponent()!=WoodClapper) return false;
    const FVector P=WoodClapper->GetComponentTransform().InverseTransformPosition(Hit.ImpactPoint);
    return FMath::Abs(P.X)<=50.01&&FMath::Abs(P.Z)<=50.01&&FMath::Abs(P.Y)<=50.01;
}
