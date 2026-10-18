#include "SoraWorldBuilder.h"
#include "SoraCatalog.h"
#include "Components/StaticMeshComponent.h"

// Functional collision proxies. The dimension-derived spiral is visible to the
// same navigation scan as every other arena piece; no pawn is lifted by code.
void ASoraWorldBuilder::BuildSpire(const FSoraBeat& Beat)
{
    const auto& S=Beat.Space.Spire;
    const FVector C(S.Center,0);
    const FLinearColor Metal(.10f,.14f,.17f),Rail(.22f,.32f,.36f),Glass(.12f,.35f,.40f);
    Box(TEXT("SpireBase"),C+FVector(0,0,-30),FVector(3600,3600,60),Metal,true);
    const auto Segment=[&](const FString& Name,const FVector& A,const FVector& B,float Width,bool Railed,float StartPad=0,float EndPad=0)
    {
        const FVector D=B-A,Side=FVector::CrossProduct(FVector::UpVector,D).GetSafeNormal();
        const FRotator Rotation=D.Rotation();
        Box(Name,(A+B)*.5f-FVector(0,0,15),FVector(D.Size()+30,Width,30),Metal,true,Rotation);
        if(Railed)
        {
            const FVector Along=D.GetSafeNormal();
            const FVector RailA=A+Along*SoraSpireRules::GantryRailInset(D.X,D.Y,StartPad);
            const FVector RailB=B-Along*SoraSpireRules::GantryRailInset(D.X,D.Y,EndPad);
            for(int32 Sign:{-1,1})
                Box(Name+FString::FromInt(Sign)+TEXT("Rail"),(RailA+RailB)*.5f+Side*(Sign*(Width*.5f-10))+FVector(0,0,75),
                    FVector((RailB-RailA).Size()+SoraSpireRules::RailOverlapCm,20,150),Rail,true,Rotation);
        }
    };
    for(int32 N=1;N<S.Ramp.Num();++N)
    {
        const FVector A=S.Ramp[N-1],B=S.Ramp[N],D=(B-A).GetSafeNormal();
        Segment(FString::Printf(TEXT("SpireRamp%d"),N),A,B,SoraSpireRules::WidthCm,false);
        // Leave the inside of the named landings open to their gantries.
        const FVector RailA=A+D*(SoraSpireRules::IsLanding(N-1)?230:0),RailB=B-D*(SoraSpireRules::IsLanding(N)?230:0);
        const FVector Side=FVector::CrossProduct(FVector::UpVector,D).GetSafeNormal();
        for(int32 Sign:{-1,1})
        {
            const FVector Start=Sign>0?RailA:A,End=Sign>0?RailB:B;
            Box(FString::Printf(TEXT("SpireRail%d_%d"),N,Sign),(Start+End)*.5f+Side*(Sign*190)+FVector(0,0,75),
                FVector((End-Start).Size()+35,20,150),Rail,true,D.Rotation());
        }
    }
    for(int32 L=0;L<4;++L)
    {
        const int32 N=SoraSpireRules::Landing(L);
        Box(FString::Printf(TEXT("SpireLanding%d"),N),S.Ramp[N]-FVector(0,0,20),FVector(2*SoraSpireRules::LandingHalfCm,2*SoraSpireRules::LandingHalfCm,40),Metal,true);
    }
    // L2 crosses the 14 m void. Its far marksman platform is an intentional
    // dead end reached along the bridge, never a spawn floating over ground.
    const FVector L2=S.Ramp[SoraSpireRules::Landing(1)];
    const FVector Far(2*C.X-L2.X,2*C.Y-L2.Y,L2.Z);
    Segment(TEXT("SpireL2Gantry"),L2,Far,SoraSpireRules::GantryWidthCm,true,SoraSpireRules::LandingHalfCm,SoraSpireRules::MarksmanHalfCm);
    Box(TEXT("SpireMarksmanPost"),Far-FVector(0,0,20),FVector(2*SoraSpireRules::MarksmanHalfCm,2*SoraSpireRules::MarksmanHalfCm,40),Glass,true);
    // L4's middle is the parked lift. The short crossing is staged only for
    // b10 and removed before the moving deck takes its place in b11.
    Segment(TEXT("SpireL4West"),S.Ramp.Last(),C+FVector(-300,0,2700),SoraSpireRules::GantryWidthCm,true,SoraSpireRules::LandingHalfCm);
    Segment(TEXT("SpireL4East"),C+FVector(300,0,2700),C+FVector(-SoraSpireRules::Point(SoraSpireRules::NodeCount-1).X,0,2700),200,true);
    for(int32 N=0;N<6;++N)
    {
        const auto A=SoraSpireRules::Vertex(N,1500),B=SoraSpireRules::Vertex(N+1,1500);
        const FVector FlatA=C+FVector(A.X,A.Y,0),FlatB=C+FVector(B.X,B.Y,0);
        Box(FString::Printf(TEXT("SpireOuterWall%d"),N),(FlatA+FlatB)*.5f+FVector(0,0,1600),
            FVector(FVector::Dist2D(FlatA,FlatB)+40,30,3200),Metal,true,(FlatB-FlatA).Rotation());
    }
}
