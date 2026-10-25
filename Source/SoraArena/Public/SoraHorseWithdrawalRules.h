#pragma once
// The authored gate approach lies inside the current estate collision wall.
// This is an outro after the 150-second task, never a kill requirement or timeout.
namespace SoraHorseWithdrawalRules
{
constexpr int GoalX=-2300,GoalY=0,GoalZ=0;
constexpr int ArrivalCm=220,FloorToleranceCm=30,PacePermille=750;
constexpr int Slots=6,SlotAcceptanceCm=30;
constexpr int Offsets[Slots][2]={{-130,-100},{-130,100},{0,-100},{0,100},{130,-100},{130,100}};
}
