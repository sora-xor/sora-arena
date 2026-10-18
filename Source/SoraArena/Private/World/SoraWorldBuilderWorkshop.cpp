#include "SoraWorldBuilder.h"
#include "SoraCatalog.h"
#include "SoraWorkshopRules.h"
#include "Components/StaticMeshComponent.h"

namespace
{
const TCHAR* const Cube=TEXT("/Engine/BasicShapes/Cube.Cube");
const FLinearColor Wood(.36f,.23f,.12f),Iron(.19f,.21f,.22f),Silk(.84f,.78f,.61f),Gold(.94f,.65f,.21f);
}
void ASoraWorldBuilder::StageWorkshop(const FSoraBeat& Beat)
{
    // Ch05 has one rhythmic station per beat. These collision-free tools
    // expose the actual timing; they do not impersonate the missing NPC or
    // first-person skeletal animation assets (chapter-05 §5.4).
    for(int32 Step=0;Step<Beat.Task.StepCount;++Step)
    {
        if(Beat.Task.Steps[Step].PhraseStrikes<=0||!Beat.Space.StepStations.IsValidIndex(Step)) continue;
        const int32 Station=Beat.Space.StepStations[Step];
        if(!Beat.Space.Stations.IsValidIndex(Station)) continue;
        WorkshopStep=Step;
        WorkshopAnchor=Floor(Beat.Space.Stations[Station],Beat.Space.HeightCm);
        bWorkshopHammer=Beat.Task.Steps[Step].PhraseStrikes==8;
        break;
    }
    if(WorkshopStep<0) return;
    const FVector P=WorkshopAnchor;
    auto Moving=[&](const TCHAR* Name,FVector Scale,FLinearColor Color,const TCHAR* Role)
    {
        auto* Part=KitShape(Name,Cube,P,Scale,Color,Role);
        Part->ComponentTags.Add(bWorkshopHammer?TEXT("WorkshopHammer"):TEXT("WorkshopLoom"));
        WorkshopParts.Add(Part); return Part;
    };
    if(bWorkshopHammer)
    {
        KitShape(TEXT("AnvilFoot"),Cube,P+FVector(0,0,92),FVector(.42f,.36f,.16f),Iron,TEXT("Metal"));
        KitShape(TEXT("AnvilFace"),Cube,P+FVector(0,0,106),FVector(.9f,.30f,.12f),Iron,TEXT("Metal"));
        Moving(TEXT("CueHammerHead"),FVector(.18f,.13f,.12f),Iron,TEXT("Metal"));
        Moving(TEXT("CueHammerHandle"),FVector(.42f,.035f,.035f),Wood,TEXT("Timber"));
        Moving(TEXT("SledgeHead"),FVector(.24f,.18f,.14f),Iron,TEXT("Metal"));
        Moving(TEXT("SledgeHandle"),FVector(.65f,.045f,.045f),Wood,TEXT("Timber"));
        Moving(TEXT("HammerGlint"),FVector(.055f,.14f,.018f),Gold,TEXT(""));
        for(int32 Segment=0;Segment<32;++Segment)
        {
            auto* Mark=KitShape(TEXT("AnvilTimingRing"),Cube,P+FVector(0,0,114),FVector(.08f,.018f,.012f),Gold);
            Mark->ComponentTags.Add(TEXT("WorkshopTimingRing")); WorkshopRing.Add(Mark);
        }
    }
    else
    {
        // Drawloom frame, separate shuttle and beater, and a figure cord on
        // the player's side. The marker moves down on an accepted pull.
        for(int32 Side:{-1,1})
            KitShape(TEXT("DrawloomPost"),Cube,P+FVector(28,Side*49,130),FVector(.08f,.08f,1.f),Wood,TEXT("Timber"));
        KitShape(TEXT("DrawloomBeam"),Cube,P+FVector(28,0,180),FVector(.08f,1.06f,.08f),Wood,TEXT("Timber"));
        for(int32 Thread=0;Thread<9;++Thread)
            KitShape(TEXT("WarpThread"),Cube,P+FVector(0,-40+Thread*10,100),FVector(.9f,.008f,.008f),Silk);
        Moving(TEXT("Shuttle"),FVector(.13f,.30f,.055f),Wood,TEXT("Timber"));
        Moving(TEXT("FigureCord"),FVector(.012f,.012f,.76f),Silk,TEXT(""));
        Moving(TEXT("CordMarker"),FVector(.075f,.15f,.10f),Gold,TEXT(""));
        Moving(TEXT("Beater"),FVector(.06f,.88f,.16f),Wood,TEXT("Timber"));
    }
    ShowWorkshop(FSoraKitView{});
}
void ASoraWorldBuilder::ShowWorkshop(const FSoraKitView& View)
{
    if(WorkshopStep<0) return;
    const bool Active=View.RhythmStep==WorkshopStep;
    const auto Pose=SoraWorkshopRules::Pose(Active,View.RhythmElapsedMs,View.RhythmPeriodMs,View.RhythmHitAgeMs);
    const FVector P=WorkshopAnchor;
    if(bWorkshopHammer&&WorkshopParts.Num()==5)
    {
        WorkshopParts[0]->SetRelativeLocation(P+FVector(24,0,150-32*Pose.CueTap));
        WorkshopParts[1]->SetRelativeLocation(P+FVector(45,0,146-22*Pose.CueTap));
        WorkshopParts[1]->SetRelativeRotation(FRotator(-12+22*Pose.CueTap,0,0));
        WorkshopParts[2]->SetRelativeLocation(P+FVector(-24,0,166-47*Pose.Response));
        WorkshopParts[3]->SetRelativeLocation(P+FVector(-46,0,146-30*Pose.Response));
        WorkshopParts[3]->SetRelativeRotation(FRotator(35-40*Pose.Response,0,0));
        WorkshopParts[4]->SetRelativeLocation(P+FVector(24,0,157-32*Pose.CueTap));
        WorkshopParts[4]->SetVisibility(Active&&Pose.Glint);
        const float Radius=4.f+34.f*Pose.Ring;
        for(int32 N=0;N<WorkshopRing.Num();++N)
        {
            const float Angle=2.f*PI*N/WorkshopRing.Num();
            UStaticMeshComponent* Mark=WorkshopRing[N]; Mark->SetVisibility(Active);
            Mark->SetRelativeLocation(P+FVector(FMath::Cos(Angle)*Radius,FMath::Sin(Angle)*Radius,114));
            Mark->SetRelativeRotation(FRotator(0,FMath::RadiansToDegrees(Angle)+90,0));
            Mark->SetRelativeScale3D(FVector(2.f*PI*Radius/WorkshopRing.Num()/100.f,.018f,.012f));
        }
    }
    else if(!bWorkshopHammer&&WorkshopParts.Num()==4)
    {
        WorkshopParts[0]->SetRelativeLocation(P+FVector(0,40*Pose.Shuttle,105));
        // The upper cord stays anchored as its lower end is pulled down.
        WorkshopParts[1]->SetRelativeLocation(P+FVector(-35,0,142-11*Pose.Response));
        WorkshopParts[1]->SetRelativeScale3D(FVector(.012f,.012f,.76f+.22f*Pose.Response));
        WorkshopParts[2]->SetRelativeLocation(P+FVector(-35,0,104-22*Pose.Response));
        WorkshopParts[3]->SetRelativeLocation(P+FVector(25-12*Pose.Response,0,104));
    }
}
