#pragma once

#include <cmath>

// Connect signature results carry no request identifier. Until the cancelled
// result is consumed, elapsed time cannot make this session safe to reuse.
// This state machine is independent of Unreal so delayed-result races can be
// exercised by the host tests as well as the subsystem automation test.
struct FArenaCancelledSignatureGuard
{
    enum class EResult { NotCancelled, Discard, RetireSession };

    void Cancel(double RequestDeadline)
    {
        bPending = true;
        Deadline = RequestDeadline;
    }

    bool BlocksSigning() const { return bPending; }

    bool MustRetire(double Now) const
    {
        // Fail closed for an invalid deadline/clock as well as at expiry.
        return bPending && (!std::isfinite(Now) || !std::isfinite(Deadline) || Now >= Deadline);
    }

    EResult ConsumeResult(double Now)
    {
        if (!bPending) return EResult::NotCancelled;
        if (MustRetire(Now)) return EResult::RetireSession;
        Reset();
        return EResult::Discard;
    }

    void Reset()
    {
        bPending = false;
        Deadline = 0;
    }

private:
    bool bPending = false;
    double Deadline = 0;
};
