#include "SoraCaptionLayoutRules.h"
#include "SoraAimHUDLayout.h"
#include "SoraCaptureFrameRules.h"
#include <cassert>
#include <iostream>
#include <string>
int main(int Argc,char** Argv)
{
    using namespace SoraCaptionLayoutRules;
    if(Argc>1&&std::string(Argv[1])=="capture-frame")
    {
        SoraCaptureFrameRules::FDrawState S; std::uint64_t Request,Current; bool Nonempty,Fresh;
        std::cin>>S.Gameplay>>S.Visible>>S.Paused>>S.World>>S.FrozenWorld>>Request>>Current>>Nonempty>>Fresh;
        std::cout<<SoraCaptureFrameRules::Drawn(S)<<' '<<SoraCaptureFrameRules::Processed(S,Request,Current,Nonempty,Fresh)<<'\n';
        return 0;
    }
    if(Argc>1&&std::string(Argv[1])=="ordinary-caption-regions")
    {
        FOrdinaryCaptionRegionsInput I; FRect Obstacles[32]; int N;
        std::cin>>I.W>>I.H>>I.S>>I.X>>I.Width>>I.NextY>>I.Limit>>I.NoticeReserve
            >>I.HasHero>>I.WeaponLeft>>I.BottomTop>>N;
        if(N<0||N>32) return 2;
        for(int J=0;J<N;++J) std::cin>>Obstacles[J].X>>Obstacles[J].Y>>Obstacles[J].W>>Obstacles[J].H;
        const auto R=OrdinaryCaptionRegions(I,Obstacles,N);
        for(int J=0;J<R.Count;++J) std::cout<<R.Bounds[J].X<<' '<<R.Bounds[J].Y<<' '<<R.Bounds[J].W<<' '<<R.Bounds[J].H<<'\n';
        return 0;
    }
    if(Argc>1&&std::string(Argv[1])=="aim-regions")
    {
        float W,H,S,O,B; std::cin>>W>>H>>S>>O>>B;
        FRect Regions[MaxRegions]{};
        const int N=SoraAimHUDLayout::LowerRegions(W,H,S,O,B,Regions);
        for(int I=0;I<N;++I) std::cout<<Regions[I].X<<' '<<Regions[I].Y<<' '<<Regions[I].W<<' '<<Regions[I].H<<'\n';
        return 0;
    }
    if(Argc>1&&std::string(Argv[1])=="aim-free")
    {
        FRect View,Obstacles[32]; int N; float Gap;
        std::cin>>View.X>>View.Y>>View.W>>View.H>>N>>Gap;
        if(N<0||N>32) return 2;
        for(int I=0;I<N;++I) std::cin>>Obstacles[I].X>>Obstacles[I].Y>>Obstacles[I].W>>Obstacles[I].H;
        const auto Regions=SoraAimHUDLayout::FreeRegions(View,Obstacles,N,Gap);
        for(int I=0;I<Regions.Count;++I) { const auto& B=Regions.Bounds[I]; std::cout<<B.X<<' '<<B.Y<<' '<<B.W<<' '<<B.H<<'\n'; }
        return 0;
    }
    if(Argc>1&&std::string(Argv[1])=="aim-progress")
    {
        using namespace SoraArcheryRules;
        FState S;
        for(int I=1;I<=6;++I) { assert(Issue(S,I,true)); Resolve(S,I,I<=3?0:-1); }
        auto P=SoraAimHUDLayout::ArcheryProgress(S);
        assert(P.Near&&P.Resolved==6&&P.Hits==3&&P.Goal==4&&P.FetchSeconds==8);
        TickFetch(S,1); assert(SoraAimHUDLayout::ArcheryProgress(S).FetchSeconds==8);
        TickFetch(S,7999); P=SoraAimHUDLayout::ArcheryProgress(S); assert(P.Resolved==0&&P.Hits==0);
        for(int I=7;I<=12;++I) { assert(Issue(S,I,true)); Resolve(S,I,I<=10?0:-1); }
        P=SoraAimHUDLayout::ArcheryProgress(S); assert(!P.Near&&P.Hits==0&&P.Goal==3);
        assert(Issue(S,13,true)); Resolve(S,13,2);
        assert(Issue(S,14,true)); Resolve(S,14,2);
        P=SoraAimHUDLayout::ArcheryProgress(S); assert(P.Hits==1);
        assert(FetchExhausted(S,0)); TickFetch(S,8000);
        assert(SoraAimHUDLayout::ArcheryProgress(S).Hits==1);
        assert(Issue(S,15,true)); Resolve(S,15,1); assert(Issue(S,16,true)); Resolve(S,16,3);
        P=SoraAimHUDLayout::ArcheryProgress(S); assert(P.Hits==3&&S.Stage==EStage::Done);
        std::cout<<"progress passed\n"; return 0;
    }
    if(Argc>1&&(std::string(Argv[1])=="marker"||std::string(Argv[1])=="backed-marker"))
    {
        FRect Label,View,Obstacles[32]; int Count=0; float Gap=0;
        std::cin>>Label.X>>Label.Y>>Label.W>>Label.H>>View.X>>View.Y>>View.W>>View.H>>Count>>Gap;
        if(Count<0||Count>32) return 2;
        for(int I=0;I<Count;++I) std::cin>>Obstacles[I].X>>Obstacles[I].Y>>Obstacles[I].W>>Obstacles[I].H;
        if(std::string(Argv[1])=="backed-marker")
        {
            float Scale=1.f; std::cin>>Scale;
            const auto P=PlaceBackedLabel(Label,View,Obstacles,Count,Gap,Scale);
            std::cout<<P.Fits<<' '<<P.Bounds.X<<' '<<P.Bounds.Y<<' '<<P.Bounds.W<<' '<<P.Bounds.H
                <<' '<<P.TextX<<' '<<P.TextY<<'\n';
            return 0;
        }
        const auto P=PlaceLabel(Label,View,Obstacles,Count,Gap);
        std::cout<<P.Fits<<' '<<P.Bounds.X<<' '<<P.Bounds.Y<<' '<<P.Bounds.W<<' '<<P.Bounds.H<<'\n';
        return 0;
    }
    int N=0,R=0; float Gap=0;
    if(!(std::cin>>N>>R>>Gap)||N<0||N>MaxCaptions||R<0||R>MaxRegions) return 2;
    FRect Regions[MaxRegions]; float Heights[MaxCaptions][MaxRegions]={};
    for(int I=0;I<R;++I) std::cin>>Regions[I].X>>Regions[I].Y>>Regions[I].W>>Regions[I].H;
    for(int C=0;C<N;++C) for(int I=0;I<R;++I) std::cin>>Heights[C][I];
    const auto Plan=Arrange(N,Regions,R,Heights,Gap);
    std::cout<<Plan.Fits<<'\n';
    if(Plan.Fits) for(int C=0;C<N;++C)
    {
        const auto& B=Plan.Bounds[C];
        std::cout<<Plan.Region[C]<<' '<<B.X<<' '<<B.Y<<' '<<B.W<<' '<<B.H<<'\n';
    }
}
