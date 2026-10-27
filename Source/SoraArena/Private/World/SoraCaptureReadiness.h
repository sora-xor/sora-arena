#pragma once
#include <cstdint>

// Host-testable admission of observations, not a GPU/shader implementation.
namespace SoraCaptureReadiness
{
enum class EResult { Wait, Capture, TimedOut };
struct FGate
{
    static constexpr double DeadlineSeconds=30.;
    double Started=0;
    std::uint64_t LastFrame=0,FirstReadyFrame=0;
    unsigned Polls=0,Rejected=0;
    bool HasFrame=false,HasReady=false;
    EResult Observe(double Now,std::uint64_t Frame,bool Ready)
    {
        // Even a newly ready observation at the deadline cannot extend it.
        if (Now-Started>=DeadlineSeconds) return EResult::TimedOut;
        if (HasFrame&&Frame<=LastFrame) return EResult::Wait;
        HasFrame=true; LastFrame=Frame; ++Polls;
        if (!Ready) { ++Rejected; HasReady=false; FirstReadyFrame=0; return EResult::Wait; }
        if (HasReady) return EResult::Capture;
        HasReady=true; FirstReadyFrame=Frame; return EResult::Wait;
    }
};
}
