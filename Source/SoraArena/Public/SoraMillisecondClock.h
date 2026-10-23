#pragma once
#include <cmath>
#include <cstdint>
#include <limits>

// Converts active frame time to whole milliseconds without rounding every
// frame. Owners stop advancing while paused and reset at a new lifecycle.
struct FSoraMillisecondClock
{
    void Reset() { RemainderMs = 0.; }
    int32_t Advance(double DeltaSeconds)
    {
        if (!std::isfinite(DeltaSeconds) || DeltaSeconds <= 0.) return 0;
        const double Total = RemainderMs + DeltaSeconds * 1000.;
        constexpr int32_t Max = std::numeric_limits<int32_t>::max();
        if (Total >= Max) { Reset(); return Max; }
        const int32_t Whole = static_cast<int32_t>(std::floor(Total));
        RemainderMs = Total - Whole;
        return Whole;
    }
private:
    double RemainderMs = 0.;
};
