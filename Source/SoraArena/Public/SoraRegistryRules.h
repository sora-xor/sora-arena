#pragma once

// Chapter six L5, centimetres from the garden's southwest corner.
namespace SoraRegistryRules
{
constexpr int PerimeterWidthCm=180;
constexpr int DeskX[3]={1600,600,-200};
constexpr int DeskY=2900;
constexpr int DeskFloor[3]={0,15,30};
inline float Floor(float X,float Y)
{
    // The south perimeter corridor stays level across all three tiers.
    if(Y<2200+PerimeterWidthCm||Y>3400||X<-600||X>2200) return 0.f;
    return X<200?30.f:X<1000?15.f:0.f;
}
}
