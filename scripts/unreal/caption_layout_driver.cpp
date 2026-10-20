#include "SoraCaptionLayoutRules.h"
#include <iostream>
int main()
{
    using namespace SoraCaptionLayoutRules;
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
