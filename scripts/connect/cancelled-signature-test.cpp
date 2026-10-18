#include "ArenaCancelledSignatureGuard.h"

#include <cassert>
#include <cstdio>
#include <limits>

int main()
{
    using EResult = FArenaCancelledSignatureGuard::EResult;
    FArenaCancelledSignatureGuard Guard;
    assert(!Guard.BlocksSigning());
    assert(Guard.ConsumeResult(0) == EResult::NotCancelled);

    // A cancellation blocks every new request, including an identical payload.
    Guard.Cancel(90);
    assert(Guard.BlocksSigning());
    assert(!Guard.MustRetire(89.999));
    assert(Guard.ConsumeResult(89.999) == EResult::Discard);
    assert(!Guard.BlocksSigning());
    assert(!Guard.MustRetire(100));

    // Expiry is not an acknowledgement. The old signature/error can still be
    // in flight; neither a tick nor delivery at/after expiry permits reuse.
    Guard.Cancel(180);
    assert(Guard.MustRetire(180));
    assert(Guard.BlocksSigning());
    assert(Guard.ConsumeResult(180) == EResult::RetireSession);
    assert(Guard.BlocksSigning());
    assert(Guard.ConsumeResult(1000) == EResult::RetireSession);
    assert(Guard.BlocksSigning());

    // Only transport teardown may reset an unresolved expired cancellation.
    Guard.Reset();
    assert(!Guard.BlocksSigning());
    assert(!Guard.MustRetire(1000));
    assert(Guard.ConsumeResult(1000) == EResult::NotCancelled);
    Guard.Cancel(1090);
    assert(Guard.ConsumeResult(1089) == EResult::Discard);

    // No invalid deadline or observed time may silently reopen signing.
    Guard.Cancel(std::numeric_limits<double>::quiet_NaN());
    assert(Guard.MustRetire(0));
    assert(Guard.ConsumeResult(0) == EResult::RetireSession);
    Guard.Reset();
    Guard.Cancel(90);
    assert(Guard.MustRetire(std::numeric_limits<double>::quiet_NaN()));
    assert(Guard.BlocksSigning());
    Guard.Cancel(std::numeric_limits<double>::infinity());
    assert(Guard.MustRetire(0));

    std::puts("Cancelled-signature state-machine regressions passed");
}
