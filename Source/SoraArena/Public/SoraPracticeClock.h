#pragma once
#include <cmath>

// A render hitch slows wall-time progress; it never skips reference input ticks.
// Independent of Unreal so its scheduling contract can be checked without an SDK.
struct FSoraPracticeClock
{
    static constexpr double StepSeconds = 1.0 / 60.0;
    static constexpr int MaxCatchUp = 8;
    double Accumulator = 0;
    bool Slowed = false;
    void Reset() { Accumulator=0; Slowed=false; }
    int Advance(double DeltaSeconds)
    {
        Slowed=false;
        if(!std::isfinite(DeltaSeconds)||DeltaSeconds<0) return 0;
        Accumulator+=DeltaSeconds;
        if(Accumulator>StepSeconds*MaxCatchUp)
        { Accumulator=StepSeconds*MaxCatchUp; Slowed=true; }
        int Steps=0;
        while(Accumulator+1.e-9>=StepSeconds&&Steps<MaxCatchUp)
        { Accumulator-=StepSeconds; ++Steps; }
        if(Accumulator<0) Accumulator=0;
        return Steps;
    }
};
