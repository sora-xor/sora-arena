#pragma once

// Reach radii (2D, cm) the campaign director and its world play share:
// working a point, opening a cache or picking up a find; arriving at an
// anchor; holding ground; an opponent close enough to contest a hold; tacking
// up or delivering from the saddle; and how far a convoy lets its rider fall
// behind before it waits.
namespace SoraCampaignReach
{
constexpr float Interact = 260.f;
constexpr float Arrive = 320.f;
constexpr float Hold = 420.f;
constexpr float Contest = 900.f;
constexpr float Saddle = 420.f;
constexpr float ConvoyWait = 2500.f;
// How far an escorted party's members walk behind one another.
constexpr float PartySpacing = 150.f;
// Opponents on a road enter this far ahead of the hero.
constexpr float RoadSpawnNear = 2500.f;
constexpr float RoadSpawnFar = 6500.f;
}
