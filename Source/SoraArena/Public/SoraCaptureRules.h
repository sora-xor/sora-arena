#pragma once

// The two authored take-alive endings. No instant or unknown capture may
// silently enter the generic interaction path when normalized data changes.
namespace SoraCaptureRules
{
template<typename Char> constexpr bool Equal(const Char* Value,const char* Expected)
{
    if(!Value) return false;
    while(*Expected&&*Value==*Expected) { ++Value; ++Expected; }
    return *Value==0&&*Expected==0;
}
template<typename Char> constexpr bool Valid(const Char* Beat,const Char* Opponent,
    const Char* Event,int HoldMs,bool Boss,bool Capture)
{
    if(Equal(Beat,"ch06.b13"))
        return Boss&&Capture&&Equal(Opponent,"boss_eskro")&&Equal(Event,"interact:bulkhead_lever")&&HoldMs==2000;
    if(Equal(Beat,"ch08.b14"))
        return Boss&&Capture&&Equal(Opponent,"boss_val_amort")&&Equal(Event,"interact:engine_spine")&&HoldMs==1500;
    return !Capture&&Equal(Event,"")&&HoldMs==0;
}
}
