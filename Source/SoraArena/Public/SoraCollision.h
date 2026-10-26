#pragma once
#include "Engine/EngineTypes.h"

namespace SoraCollision
{
// Named SoraProjectile in DefaultEngine.ini. A projectile must be able to
// ignore a drone's movement sphere while hitting its separate visible hull.
constexpr ECollisionChannel Projectile=ECC_GameTraceChannel1;
}
