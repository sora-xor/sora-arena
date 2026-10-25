#pragma once

// The archive floor is two metres above the press catwalk. Its ten ordinary
// 20 cm risers descend through the north door; no scripted pawn movement.
namespace SoraArchiveRules
{
constexpr int FloorCm=600, CatwalkCm=400, DoorX=1300, DoorHalfWidth=120;
constexpr int StairStart=80, TreadCm=35, Risers=10, RiserCm=20;
constexpr int WalkNorth=600, WalkHalfWidth=100;
// The provisional connector crosses an unbuilt gap. Solid screens must be
// above both ordinary jump height and the 165 cm vault limit.
constexpr int GuardHeightCm=180;
}
