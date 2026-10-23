#pragma once
#include <cstdint>

// Dev-capture evidence rules. These never alter gameplay or rendering clocks.
namespace SoraCaptureFrameRules
{
struct FDrawState
{
    bool Gameplay=false,Visible=false,Paused=false;
    double World=0,FrozenWorld=0;
};
inline bool Drawn(const FDrawState& S)
{
    return S.Gameplay&&S.Visible&&S.Paused&&S.World==S.FrozenWorld;
}
inline bool Processed(const FDrawState& S,std::uint64_t Request,std::uint64_t Current,bool Nonempty,bool Fresh)
{
    return Drawn(S)&&Request!=0&&Request==Current&&Nonempty&&Fresh;
}
}
