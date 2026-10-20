#include "SoraCaptionLayoutRules.h"
#include <iostream>
#include <string>
int main(int Argc,char** Argv)
{
    using namespace SoraCaptionLayoutRules;
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
