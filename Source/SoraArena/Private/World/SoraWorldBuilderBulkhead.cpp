#include "SoraWorldBuilder.h"
#include "SoraCatalog.h"
#include "SoraPlayerCharacter.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"

void ASoraWorldBuilder::StageBulkhead(const FSoraBeat& Beat)
{
    if(!Beat.Space.bBulkhead) return;
    BulkheadAt=FVector(Beat.Space.Bulkhead,Beat.Space.HeightCm);
    const TCHAR* Cube=TEXT("/Engine/BasicShapes/Cube.Cube");
    // Functional lever beside the current vault-entry blockout. The circular
    // chamber, freight-lift and flooding sump remain environment/art work.
    BulkheadLever=KitShape(TEXT("BulkheadLever"),Cube,BulkheadAt+FVector(0,0,60),FVector(.2,.6,1.2),
        FLinearColor(.12,.14,.16),TEXT("Metal"),true);
    BulkheadLever->ComponentTags.Add(TEXT("BulkheadLever"));
    BulkheadHandle=KitShape(TEXT("BulkheadHandle"),Cube,BulkheadAt+FVector(15,0,90),FVector(.08,.08,.5),
        FLinearColor(.4,.4,.4));
    ShowBulkhead(false,0.f);
}
void ASoraWorldBuilder::ShowBulkhead(bool Ready,float Progress)
{
    if(!BulkheadHandle) return;
    BulkheadHandle->SetRelativeRotation(FRotator(0,0,60.f*FMath::Clamp(Progress,0.f,1.f)));
    Tint(BulkheadHandle,Ready?FLinearColor(.94,.65,.21):FLinearColor(.4,.4,.4));
}
bool ASoraWorldBuilder::CanReachBulkhead(const ASoraPlayerCharacter& Hero) const
{
    if(!BulkheadLever||!Hero.GetCharacterMovement()->IsMovingOnGround()) return false;
    const float Feet=Hero.GetActorLocation().Z-Hero.GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    if(FMath::Abs(Feet-BulkheadAt.Z)>15) return false;
    const FVector Eye=Hero.GetCamera()->GetComponentLocation(),Target=BulkheadPoint(),Delta=Target-Eye;
    if(Delta.Size()>260||FVector::DotProduct(Hero.GetCamera()->GetForwardVector(),Delta.GetSafeNormal())<.866f) return false;
    FHitResult Hit; FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraBulkheadReach),false,&Hero);
    return GetWorld()->LineTraceSingleByChannel(Hit,Eye,Target+Delta.GetSafeNormal()*8,ECC_Visibility,Query)&&
        Hit.GetComponent()==BulkheadLever&&FVector::Dist(Hit.ImpactPoint,Target)<12;
}
