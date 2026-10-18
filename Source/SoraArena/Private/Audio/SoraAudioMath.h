#pragma once

#include "Math/UnrealMathUtility.h"

// Shared by the subsystem's playback, music and polling sources, which may
// be compiled together in an Unreal unity translation unit.
namespace SoraAudioMath
{
// Sound in air, centimetres per second: delay and Doppler use the same speed.
inline constexpr float SpeedOfSoundCmS = 34300.f;

inline float DbToGain(float Db) { return FMath::Pow(10.f, Db / 20.f); }
}
