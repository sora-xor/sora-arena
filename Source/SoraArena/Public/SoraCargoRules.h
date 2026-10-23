#pragma once
#include "SoraBeatRules.h"

// A ride's cargo is one share per unique destination. Quantities are derived
// from accepted delivery credits; they are never a second mutable inventory.
namespace SoraCargoRules
{
struct FCargo { int Total = 0; int PerDropoff = 0; };
constexpr bool Valid(FCargo Cargo, int Destinations)
{
    return Destinations > 0 && Destinations <= SoraBeatRules::MaxPoints &&
        Cargo.Total > 0 && Cargo.PerDropoff > 0 &&
        static_cast<long long>(Cargo.PerDropoff) * Destinations == Cargo.Total;
}
constexpr int Remaining(FCargo Cargo, int Destinations, int Done)
{
    return Valid(Cargo, Destinations) && Done >= 0 && Done <= Destinations
        ? Cargo.Total - Cargo.PerDropoff * Done : 0;
}
}
