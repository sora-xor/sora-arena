#pragma once
#include "CoreMinimal.h"

// Where the fieldcraft sources (SoraFieldcraft*.cpp) lay out what they stage.
// UnrealBuildTool compiles those sources in one unity file with each other and
// with the rest of Game/ (SoraPracticeActors.cpp has its own Cube), so each
// source names these through its `Layout` alias. None of them pulls this
// namespace in with a file-scope using-directive, and each member name is
// used by one source only, apart from the shared ones here.
namespace SoraFieldcraftLayout
{
inline const TCHAR* const Cube = TEXT("/Engine/BasicShapes/Cube.Cube");
inline const TCHAR* const Cylinder = TEXT("/Engine/BasicShapes/Cylinder.Cylinder");
inline const TCHAR* const Sphere = TEXT("/Engine/BasicShapes/Sphere.Sphere");
// The water stands at a swimmer's chest: a crouch (a dive) puts his eye under it.
inline constexpr float WaterLevel = 110.f;
// The environment palette's CC0 PBR surfaces (import_environment_palette.py,
// /Game/Generated/Environment/MI_Nyaagyu_<role>) the sets are dressed in.
inline const TCHAR* const Timber = TEXT("Timber");
inline const TCHAR* const Stone = TEXT("Stone");
inline const TCHAR* const Metal = TEXT("Metal");
inline const TCHAR* const Plaster = TEXT("Plaster");
}
