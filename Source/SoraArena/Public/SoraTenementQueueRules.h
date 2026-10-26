#pragma once
#include "SoraTenementRules.h"

// Six residents stand in a file from the serving court down the alley.
// An attack sends them to six distinct homes through the open paper fronts.
namespace SoraTenementQueueRules
{
constexpr int Count=6;
constexpr double Pace=260,Arrival=8;
struct FPoint { double X,Y; };
constexpr FPoint Queue(int Resident) { return {-2800.,3030.-Resident*110.}; }
constexpr FPoint DoorApproach(int Resident)
{ return {-2800.,SoraTenementRules::DoorY(5-Resident/2)}; }
constexpr FPoint Home(int Resident)
{ return {Resident%2==0?-3070.:-2530.,DoorApproach(Resident).Y}; }
}
