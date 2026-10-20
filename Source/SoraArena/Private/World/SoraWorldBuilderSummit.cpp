#include "SoraWorldBuilder.h"
#include "SoraSettings.h"
#include "Camera/CameraComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "SoraCatalog.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/DamageType.h"
#include "Kismet/GameplayStatics.h"

void ASoraWorldBuilder::BuildSummit(const FSoraBeat& Beat)
{
    const auto& S=Beat.Space.Summit;
    SummitCenter=FVector(S.Center,16000);
    const FLinearColor Metal(.12f,.16f,.20f),Cyan(.08f,.65f,.75f),Gold(.75f,.52f,.2f);
    const auto Cylinder=[&](const TCHAR* Name,FVector At,float Radius,float Height,bool Collision)
    {
        auto* Part=Shape(this,RootComponent,Name,TEXT("/Engine/BasicShapes/Cylinder.Cylinder"),At,
            FVector(Radius/50,Radius/50,Height/100),Metal,Collision);
        Pieces.Add(Part); return Part;
    };
    BuildSummitTiles();
    Cylinder(TEXT("SummitDais"),SummitCenter+FVector(0,0,60),400,120,true);
    for(int32 Step=0;Step<3;++Step)
        Cylinder(TEXT("SummitDaisStep"),SummitCenter+FVector(0,0,(Step+1)*15),640-Step*80,(Step+1)*30,true);
    SummitSpine=Cylinder(TEXT("SummitSpine"),SummitCenter+FVector(0,0,1220),200,2200,true);
    for(int32 Drum=0;Drum<11;++Drum)
        Cylinder(TEXT("SummitLedgerDrum"),SummitCenter+FVector(0,0,220+200*Drum),220,14,false);
    SummitSeam=Box(TEXT("SummitSpineSeam"),SummitCenter+FVector(0,-201,220),FVector(10,3,180),Gold,false);
    Box(TEXT("SummitDeskPlinth"),SummitCenter+FVector(0,1200,50),FVector(260,140,100),Metal,true);
    Box(TEXT("SummitWritingDesk"),SummitCenter+FVector(0,1200,118),FVector(240,100,36),FLinearColor(.2f,.05f,.03f),true);
    for(int32 N=0;N<48;++N)
    {
        const FVector A=SummitCenter+FRotator(0,N*7.5f,0).Vector()*3000+FVector(0,0,1400);
        const FVector B=SummitCenter+FRotator(0,(N+1)*7.5f,0).Vector()*3000+FVector(0,0,1400);
        Box(TEXT("SummitEngineRing"),(A+B)*.5f,FVector((B-A).Size()+5,40,80),Cyan,false,(B-A).Rotation());
    }
    for(int32 N=1;N<S.Stairs.Num();++N)
    {
        const FVector A=S.Stairs[N-1],B=S.Stairs[N],D=B-A;
        const FVector Side=FVector::CrossProduct(FVector::UpVector,D).GetSafeNormal();
        const FVector Start=A+D.GetSafeNormal2D()*(N>1?200:0),End=B-D.GetSafeNormal2D()*(N<S.Stairs.Num()-1?200:0);
        const FVector Flight=End-Start;
        const int32 Count=FMath::Max(1,FMath::CeilToInt(D.Z/18.f));
        const float Run=Flight.Size2D()/Count;
        for(int32 Step=0;Step<Count;++Step)
        {
            const FVector P=FMath::Lerp(Start,End,(Step+.5f)/Count);
            const float Top=FMath::Lerp(A.Z,B.Z,(Step+1.f)/Count);
            Box(TEXT("SummitNorthStair"),FVector(P.X,P.Y,Top-20),FVector(Run+2,300,40),Metal,true,FRotator(0,D.Rotation().Yaw,0));
        }
        const FVector RailA=Start,RailB=End;
        for(int32 Sign:{-1,1})
            Box(TEXT("SummitStairRail"),(RailA+RailB)*.5f+Side*(Sign*142)+FVector(0,0,75),
                FVector((RailB-RailA).Size()+15,16,150),Metal,true,Flight.Rotation());
        // Broad flat landings have openings along the incoming and outgoing
        // flights. A rail across either opening would block the turn.
        if(N<S.Stairs.Num()-1)
        {
            Box(TEXT("SummitStairLanding"),B-FVector(0,0,20),FVector(400,400,40),Metal,true);
            const FVector In=D.GetSafeNormal2D(),Out=(S.Stairs[N+1]-B).GetSafeNormal2D();
            for(const FVector Normal:{FVector(1,0,0),FVector(-1,0,0),FVector(0,1,0),FVector(0,-1,0)})
                if(FVector::DotProduct(Normal,-In)<.5f&&FVector::DotProduct(Normal,Out)<.5f)
                    Box(TEXT("SummitStairLandingRail"),B+Normal*192+FVector(0,0,75),
                        Normal.X!=0?FVector(16,400,150):FVector(400,16,150),Metal,true);
        }
    }
}

void ASoraWorldBuilder::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    TickSpireAlarm();
    TickSeizure();
}

bool ASoraWorldBuilder::CanReachSummitSpine(const ASoraPlayerCharacter& Hero) const
{
    if(!bSummitActive||!SummitSpine||!Hero.GetCharacterMovement()->IsMovingOnGround()) return false;
    const float Feet=Hero.GetActorLocation().Z-Hero.GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    if(FMath::Abs(Feet-(SummitCenter.Z+120))>15) return false;
    const FVector Eye=Hero.GetCamera()->GetComponentLocation(),Target=SummitSpinePoint(),Delta=Target-Eye;
    if(Delta.Size()>260||FVector::DotProduct(Hero.GetCamera()->GetForwardVector(),Delta.GetSafeNormal())<.866f) return false;
    FHitResult Hit; FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraSpineReach),false,&Hero);
    // Trace just into the spine: the far side, a wall or a body cannot satisfy
    // a clear view of the actual seam on its south face.
    return GetWorld()->LineTraceSingleByChannel(Hit,Eye,Target+Delta.GetSafeNormal()*8,ECC_Visibility,Query)&&
        Hit.GetComponent()==SummitSpine&&FVector::Dist(Hit.ImpactPoint,Target)<12;
}
void ASoraWorldBuilder::ShowSummitSpine(bool Ready,float CutProgress)
{
    if(!SummitSeam) return;
    const float Progress=FMath::Clamp(CutProgress,0.f,1.f);
    const FLinearColor Color=Progress>=1?FLinearColor(.01f,.01f,.015f):Ready
        ?SoraAccessibility::TelegraphColor(this,SoraAccessibility::ETelegraph::Cleave):FLinearColor(.15f,.2f,.22f);
    if(auto* Material=Cast<UMaterialInstanceDynamic>(SummitSeam->GetMaterial(0)))
    {
        Material->SetVectorParameterValue(TEXT("BaseColor"),Color);
        Material->SetVectorParameterValue(TEXT("Color"),Color);
    }
    // A widening fracture is a functional seam proxy. The 22 m spine's
    // authored split and the hero's nukitsuke clip remain art work.
    SummitSeam->SetRelativeScale3D(FVector(.1f+.7f*Progress,.03f,1.8f));
}
