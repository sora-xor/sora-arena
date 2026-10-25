#include "SoraPressRules.h"
#include <cassert>
#include <cstdint>
#include <iostream>
#include <initializer_list>
#include <limits>

namespace P=SoraPressRules;
int main()
{
    unsigned Jammed=0;
    for(int I=0;I<8;++I) assert(P::Running(Jammed,I));
    assert(!P::Running(Jammed,-1)&&!P::Running(Jammed,8));
    assert(!P::Jam(Jammed,-1)&&!P::Jam(Jammed,3)&&Jammed==0);
    assert(P::Jam(Jammed,1)&&!P::Jam(Jammed,1));
    for(int I=0;I<8;++I) assert(P::Running(Jammed,I)==(I!=4));
    assert(P::Jam(Jammed,0)&&P::Jam(Jammed,2));
    assert(Jammed==((1u<<1)|(1u<<4)|(1u<<6)));
    for(int I:{0,2,3,5,7}) assert(P::Running(Jammed,I));
    assert(P::Masking(0)&&P::Masking(499)&&!P::Masking(500));
    assert(!P::Masking(1599)&&P::Masking(1600)&&!P::Masking(-1));
    assert(P::MaskedBetween(0,1600)==500&&P::MaskedBetween(499,501)==1);
    assert(P::MaskedBetween(1599,1601)==1&&P::MaskedBetween(1600,1600)==0);
    assert(P::MaskedBetween(-400,400)==400&&P::MaskedBetween(500,400)==0);
    // Independent per-ms oracle, including long frames that cross several
    // stamps. This catches off-by-one windows and skipped cycles.
    for(int Start=0;Start<3200;Start+=13) for(int Span:{1,7,16,33,500,1600,4703})
    {
        int Expected=0;
        for(int T=Start;T<Start+Span;++T) Expected+=(T%1600)<500;
        assert(P::MaskedBetween(Start,Start+Span)==Expected);
    }
    // Every partition covers exactly the same masked duration: no sample-
    // at-frame-end shortcut, including 30/60/144 Hz and one huge tick.
    for(int Frames:{1,30,60,144,1000})
    {
        long long Total=0,Previous=0;
        for(int F=1;F<=Frames;++F)
        {
            const long long End=4800LL*F/Frames;
            Total+=P::MaskedBetween(Previous,End); Previous=End;
        }
        assert(Total==1500);
    }
    constexpr long long Long=static_cast<long long>(std::numeric_limits<int>::max())+1600;
    assert(P::MaskedBetween(Long,Long+1600)==500);
    assert(P::Scale(1500,200)==300&&P::Scale(1000,200)==200&&P::Scale(0,200)==0);
    assert(P::Scale(std::numeric_limits<int>::max(),1000)==std::numeric_limits<int>::max());
    std::cout<<"Press rules: exact stamp boundaries, long intervals, 30/60/144 Hz partitions and independent master jams passed\n";
}
