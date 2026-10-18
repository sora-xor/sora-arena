#include "SoraWorldBuilder.h"
#include "SoraCatalog.h"
#include "Components/StaticMeshComponent.h"

// Functional collision proxies. The four-turn hex spiral is visible to the
// same navigation scan as every other arena piece; no pawn is lifted by code.
void ASoraWorldBuilder::BuildSpire(const FSoraBeat& Beat)
{
    const auto& S=Beat.Space.Spire;
    const FVector C(S.Center,0);
    const FLinearColor Metal(.10f,.14f,.17f),Rail(.22f,.32f,.36f),Glass(.12f,.35f,.40f);
    Box(TEXT("SpireBase"),C+FVector(0,0,-30),FVector(3600,3600,60),Metal,true);
    const auto Segment=[&](const FString& Name,const FVector& A,const FVector& B,float Width,bool Railed)
    {
        const FVector D=B-A,Side=FVector::CrossProduct(FVector::UpVector,D).GetSafeNormal();
        const FRotator Rotation=D.Rotation();
        Box(Name,(A+B)*.5f-FVector(0,0,15),FVector(D.Size()+30,Width,30),Metal,true,Rotation);
        if(Railed)
            for(int32 Sign:{-1,1})
                Box(Name+FString::FromInt(Sign)+TEXT("Rail"),(A+B)*.5f+Side*(Sign*(Width*.5f-10))+FVector(0,0,75),
                    FVector(D.Size()+35,20,150),Rail,true,Rotation);
    };
    for(int32 N=1;N<S.Ramp.Num();++N)
    {
        const FVector A=S.Ramp[N-1],B=S.Ramp[N],D=(B-A).GetSafeNormal();
        Segment(FString::Printf(TEXT("SpireRamp%d"),N),A,B,400,false);
        // Leave the inside of the named landings open to their gantries.
        const FVector RailA=A+D*((N-1)%8==0?230:0),RailB=B-D*(N%8==0?230:0);
        const FVector Side=FVector::CrossProduct(FVector::UpVector,D).GetSafeNormal();
        for(int32 Sign:{-1,1})
        {
            const FVector Start=Sign>0?RailA:A,End=Sign>0?RailB:B;
            Box(FString::Printf(TEXT("SpireRail%d_%d"),N,Sign),(Start+End)*.5f+Side*(Sign*190)+FVector(0,0,75),
                FVector((End-Start).Size()+35,20,150),Rail,true,D.Rotation());
        }
    }
    for(int32 N:{0,8,16,24})
        Box(FString::Printf(TEXT("SpireLanding%d"),N),S.Ramp[N]-FVector(0,0,20),FVector(600,600,40),Metal,true);
    // L2 crosses the 14 m void. Its far marksman platform is an intentional
    // dead end reached along the bridge, never a spawn floating over ground.
    const FVector Far=C+FVector(-693,1200,900);
    Segment(TEXT("SpireL2Gantry"),S.Ramp[8],Far,200,true);
    Box(TEXT("SpireMarksmanPost"),Far-FVector(0,0,20),FVector(400,400,40),Glass,true);
    // L4's middle is the parked lift. The short crossing is staged only for
    // b10 and removed before the moving deck takes its place in b11.
    Segment(TEXT("SpireL4West"),C+FVector(-1386,0,2700),C+FVector(-300,0,2700),200,true);
    Segment(TEXT("SpireL4East"),C+FVector(300,0,2700),C+FVector(1386,0,2700),200,true);
    for(int32 N=0;N<6;++N)
    {
        const FVector A=C+(S.Ramp[N]-C)*1.25f,B=C+(S.Ramp[N+1]-C)*1.25f;
        const FVector FlatA(A.X,A.Y,0),FlatB(B.X,B.Y,0);
        Box(FString::Printf(TEXT("SpireOuterWall%d"),N),(FlatA+FlatB)*.5f+FVector(0,0,1600),
            FVector(FVector::Dist2D(A,B)+40,30,3200),Metal,true,(FlatB-FlatA).Rotation());
    }
}
