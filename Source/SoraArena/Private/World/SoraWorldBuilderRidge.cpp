#include "SoraWorldBuilder.h"
#include "SoraCatalog.h"
#include "SoraRidgeRules.h"
#include "SoraPlayerCharacter.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Camera/CameraComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/World.h"

void ASoraWorldBuilder::BuildWindSpace(const FSoraBeat& Beat)
{
    const auto& S=Beat.Space.Wind;
    const FVector O(S.Origin,0);
    const FLinearColor Metal(.16f,.18f,.21f),Cable(.32f,.29f,.24f);
    if(!S.Ridge())
    {
        // Functional hangar shell: the authored mouth is genuinely open.
        Box(TEXT("HangarDeck"),O+FVector(4000,2250,-40),FVector(8000,4500,80),Metal,true);
        Box(TEXT("HangarStarboard"),O+FVector(4000,-30,1000),FVector(8060,60,2000),Metal,true);
        for(int Sign:{-1,1})
            Box(TEXT("HangarEnd"),O+FVector(Sign<0?-30:8030,2250,1000),FVector(60,4500,2000),Metal,true);
        for(float X:{1000.f,7000.f}) Box(TEXT("HangarPortWall"),O+FVector(X,4530,1000),FVector(2000,60,2000),Metal,true);
        Box(TEXT("HangarMouthLintel"),O+FVector(4000,4530,1700),FVector(4000,60,600),Metal,true);
        // Three walk-around shuttle proxies, with a continuous gallery and
        // real stair flights. Art/canister behavior is not claimed here.
        for(float X:{1500.f,4000.f,6500.f})
            Box(TEXT("HangarShuttleProxy"),O+FVector(X,2500,230),FVector(1800,1400,460),Metal,true);
        Box(TEXT("HangarGallery"),O+FVector(4000,200,775),FVector(7000,400,50),Metal,true);
        for(float X:{1000.f,7000.f}) for(int Step=0;Step<40;++Step)
            Box(TEXT("HangarGalleryStair"),O+FVector(X,1200-Step*20,(Step+1)*10),FVector(300,22,(Step+1)*20),Metal,true);
        return;
    }
    RidgeOrigin=S.Origin;
    // Thirty six-metre sections retain the authored longitudinal fall and
    // 20 degree side plates. No hidden floor or perimeter wall spans a lip.
    const float Pitch=-FMath::RadiansToDegrees(FMath::Atan(200.f/18000.f));
    for(int N=0;N<30;++N)
    {
        const double X=N*600+300,Half=SoraRidgeRules::CrownHalf(X),Z=SoraRidgeRules::Height(X);
        Box(TEXT("RidgeCrown"),O+FVector(X,0,Z-20),FVector(600.04,Half*2,40),Metal,true,FRotator(Pitch,0,0));
        for(int Side:{-1,1})
            Box(TEXT("RidgePlate"),O+FVector(X,Side*(Half+200),SoraRidgeRules::Height(X,Half+200)-20),
                FVector(600.04,400/FMath::Cos(FMath::DegreesToRadians(20.f)),40),Metal,true,FRotator(Pitch,0,Side*20.f));
    }
    // Ribs cross the crown; their ends can be walked around on the plates,
    // or the ordinary mapped Jump vaults the 1.2 m low cover.
    for(int X=1200;X<18000;X+=1200)
    {
        const float Half=SoraRidgeRules::CrownHalf(X),Z=SoraRidgeRules::Height(X);
        auto* Rib=Box(TEXT("RidgeRib"),O+FVector(X,0,Z+60),FVector(60,Half*2,120),Metal,true);
        Rib->ComponentTags.Add(TEXT("WindRib"));
    }
    for(int X:{3000,7000,11000,15000})
    {
        auto* Fin=Box(TEXT("RidgeSensorFin"),O+FVector(X,-180,SoraRidgeRules::Height(X)+150),FVector(400,35,300),Metal,true);
        Fin->ComponentTags.Add(TEXT("WindFin"));
    }
    Box(TEXT("RidgeMast"),O+FVector(9000,-500,SoraRidgeRules::Height(9000)+750),FVector(45,45,1500),Metal,true);
    RidgeAnchors.Reset(); RidgeAnchors.SetNum(62);
    for(int N=0;N<62;++N)
    {
        if(!SoraRidgeRules::Cable(N)) continue;
        const float X=(N/2)*600,Side=N%2?1:-1;
        // End anchors are inset 60 cm so their recovery capsule has support.
        const float SafeX=FMath::Clamp(X,60.f,17940.f);
        const FVector At=O+FVector(SafeX,Side*400,SoraRidgeRules::Height(SafeX,400));
        RidgeAnchors[N]=Box(TEXT("RidgeBraceAnchor"),At+FVector(0,0,45),FVector(12,12,90),Cable,true);
        RidgeAnchors[N]->SetCanEverAffectNavigation(false);
    }
    // Cable is visible and queryable, but never an invisible movement rail.
    for(int Side:{-1,1}) for(int X=0;X<18000;X+=100)
    {
        if(SoraRidgeRules::Gap(X+50,Side)) continue;
        const float Z=SoraRidgeRules::Height(X+50,400)+90;
        auto* Line=Box(TEXT("RidgeBraceCable"),O+FVector(X+50,Side*400,Z),FVector(101,5,5),Cable,false,FRotator(Pitch,0,0));
        Line->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
        Line->SetCollisionResponseToAllChannels(ECR_Ignore); Line->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
        Line->ComponentTags.Add(TEXT("WindCable"));
    }
}
FVector ASoraWorldBuilder::RidgeAnchorFloor(int Index) const
{
    const float X=FMath::Clamp((Index/2)*600.f+100,100.f,17900.f),Side=Index%2?1.f:-1.f;
    // Land 100 cm inboard of the post, not on top of its collider.
    return FVector(RidgeOrigin,0)+FVector(X,Side*300,SoraRidgeRules::Height(X,300));
}
int32 ASoraWorldBuilder::ReachRidgeCable(const ASoraPlayerCharacter& Hero) const
{
    if(!Hero.GetCharacterMovement()->IsMovingOnGround()||Hero.IsVaulting()) return INDEX_NONE;
    const FVector At=Hero.GetActorLocation()-FVector(RidgeOrigin,0);
    if(At.X<0||At.X>18000) return INDEX_NONE;
    const int Side=At.Y>=0?1:-1;
    if(FMath::Abs(At.Y-Side*400)>135||SoraRidgeRules::Gap(At.X,Side)) return INDEX_NONE;
    const float Feet=At.Z-Hero.GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    if(FMath::Abs(Feet-SoraRidgeRules::Height(At.X,At.Y))>20) return INDEX_NONE;
    const FVector Target=FVector(RidgeOrigin,0)+FVector(At.X,Side*400,SoraRidgeRules::Height(At.X,400)+90);
    FHitResult Hit; FCollisionQueryParams Q(SCENE_QUERY_STAT(RidgeCableReach),false,&Hero);
    if(!GetWorld()->LineTraceSingleByChannel(Hit,Hero.GetCamera()->GetComponentLocation(),Target,ECC_Visibility,Q)||
        !Hit.GetComponent()||(!Hit.GetComponent()->ComponentHasTag(TEXT("WindCable"))&&!Hit.GetComponent()->GetName().StartsWith(TEXT("RidgeBraceAnchor")))) return INDEX_NONE;
    int Best=INDEX_NONE; double Distance=1.e9;
    for(int N=0;N<RidgeAnchors.Num();++N) if(RidgeAnchors[N]&&(N%2?1:-1)==Side)
    {
        const double D=FVector::DistSquared2D(Hero.GetActorLocation(),RidgeAnchorFloor(N));
        if(D<Distance) { Best=N; Distance=D; }
    }
    return Best;
}
bool ASoraWorldBuilder::WindLee(const ASoraPlayerCharacter& Hero) const
{
    // Trace where the hero reads the wind. On the sloping plate the crouched
    // capsule centre can sit below the adjacent crown/rib's base even though
    // the head is sheltered. Sampling the centre would miss that real lee.
    const FVector At=Hero.GetCamera()->GetComponentLocation();
    FHitResult Hit; FCollisionQueryParams Q(SCENE_QUERY_STAT(RidgeLee),false,&Hero);
    if(!GetWorld()->LineTraceSingleByChannel(Hit,At,At-FVector(0,300,0),ECC_Visibility,Q)||!Hit.GetComponent()) return false;
    return Hit.GetComponent()->ComponentHasTag(TEXT("WindFin"))||
        (Hero.IsCrouched()&&Hit.GetComponent()->ComponentHasTag(TEXT("WindRib")));
}

bool ASoraWorldBuilder::WindShelteredPoint(const FVector& Point) const
{
    FHitResult Hit; FCollisionQueryParams Q(SCENE_QUERY_STAT(RidgeProjectileLee));
    if(!GetWorld()->LineTraceSingleByChannel(Hit,Point,Point-FVector(0,300,0),ECC_Visibility,Q)||!Hit.GetComponent()) return false;
    return Hit.GetComponent()->ComponentHasTag(TEXT("WindFin"))||Hit.GetComponent()->ComponentHasTag(TEXT("WindRib"));
}
