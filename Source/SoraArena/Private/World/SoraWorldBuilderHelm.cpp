#include "SoraWorldBuilder.h"
#include "SoraCatalog.h"
#include "SoraPlayerCharacter.h"
#include "Game/SoraCampaignReach.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"

void ASoraWorldBuilder::StageHelm(const FSoraBeat& Beat)
{
    if(!Beat.Space.Helm.bEnabled) return;
    const auto& H=Beat.Space.Helm;
    HelmAt=FVector(H.Wheel,Beat.Space.HeightCm);
    const TCHAR* Cube=TEXT("/Engine/BasicShapes/Cube.Cube");
    const TCHAR* Cylinder=TEXT("/Engine/BasicShapes/Cylinder.Cylinder");
    const FLinearColor Metal(.12,.14,.16),Gold(.9,.65,.18),Teal(.05,.55,.45);
    // Functional helm proxies, not final alien-bridge art. A vertical wheel
    // and a heading needle make the correction visible without a HUD alone.
    KitShape(TEXT("HelmPedestal"),Cube,HelmAt+FVector(20,0,50),FVector(.4,.6,1),Metal,TEXT("Metal"),true);
    HelmWheel=KitShape(TEXT("HelmWheel"),Cylinder,HelmAt+FVector(0,0,110),FVector(1.3,1.3,.12),Metal,TEXT("Metal"),true);
    HelmWheel->SetRelativeRotation(FRotator(90,0,0));
    HelmWheel->ComponentTags.Add(TEXT("HelmTrimWheel"));
    HelmNeedle=KitShape(TEXT("HelmHeadingNeedle"),Cube,HelmAt+FVector(-8,0,110),FVector(.035,.05,1),Gold);
    KitShape(TEXT("HelmCenterMark"),Cube,HelmAt+FVector(-9,0,180),FVector(.03,.06,.15),Teal);
    KitShape(TEXT("HelmBeacon"),Cube,FVector(H.Beacon,Beat.Space.HeightCm+100),FVector(.8,1,2),Teal,TEXT("Metal"),true);
    const FVector C(H.Hold.Center,Beat.Space.HeightCm+1);
    for(int32 Side:{-1,1})
    {
        KitShape(TEXT("HelmFloorEdge"),Cube,C+FVector(Side*H.Hold.Size.X*.5,0,0),FVector(.025,H.Hold.Size.Y/100,.02),Gold);
        KitShape(TEXT("HelmFloorEdge"),Cube,C+FVector(0,Side*H.Hold.Size.Y*.5,0),FVector(H.Hold.Size.X/100,.025,.02),Gold);
    }
}
void ASoraWorldBuilder::ShowHelm(bool NeedsTrim,float HeldFraction)
{
    if(HelmNeedle)
    {
        HelmNeedle->SetRelativeRotation(FRotator(0,0,NeedsTrim?30.f*(1.f-FMath::Clamp(HeldFraction,0.f,1.f)):0.f));
        Tint(HelmNeedle,NeedsTrim?FLinearColor(.95,.55,.1):FLinearColor(.05,.7,.5));
    }
}
bool ASoraWorldBuilder::CanReachHelm(const ASoraPlayerCharacter& Hero) const
{
    if(!HelmWheel||!Hero.GetCharacterMovement()->IsMovingOnGround()) return false;
    const float Feet=Hero.GetActorLocation().Z-Hero.GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    if(FMath::Abs(Feet-HelmAt.Z)>20||FVector::Dist2D(Hero.GetActorLocation(),HelmAt)>SoraCampaignReach::Interact) return false;
    FHitResult Hit;
    const FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraHelmReach),false,&Hero);
    return GetWorld()->LineTraceSingleByChannel(Hit,Hero.GetCamera()->GetComponentLocation(),HelmAt+FVector(0,0,110),
        ECC_Visibility,Query)&&Hit.GetComponent()==HelmWheel;
}
