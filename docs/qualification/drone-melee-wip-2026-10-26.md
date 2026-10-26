# Drone melee collision source checkpoint — not compiled or run

The landing candidate at signed `53967094` compiles but still awaits its
runtime tests. This separate source candidate addresses a recorded collision
gap: both melee paths sweep `ECC_Pawn`, which hits the drone's 38 cm movement
sphere. Arrows and sight already use the imported disc, dome and pod hulls.
A swing wholly outside those hulls could therefore damage the drone, or the
movement sphere could hide a valid contact farther along the swing.

`SoraMeleeTrace::Sweep` excludes each drone's movement capsule before the
ordinary world query and separately sweeps the same weapon volume against
the imported simple hulls. It combines the results through the earliest
blocking contact, preserving Pawn-channel overlaps used by construct and
boss weak points. Existing melee radii, reach, facing, commitment, visibility
checks and damage remain unchanged. The movement sphere still handles flight
and physical navigation. No collision channels or project configuration change.

The installed UE 5.8.3 implementation of `FBodyInstance::Sweep` delegates to
`FPhysInterface_Chaos::Sweep_Geom`, whose hit conversion uses an overlap-all
filter. The helper explicitly classifies a successful drone hull contact as
blocking before merging it with world cover. This avoids treating the solid
disc as a nonblocking overlap merely because the component query has no
trace-channel policy.

Prepared `SoraArena.Campaign.DroneMelee` checks actual imported hull sweeps at
all three melee radii (16/36/45 cm), misses above/below the disc despite a
positive movement-sphere control, intervening cover, a valid contact behind
empty sphere space, blocking by the disc itself and preservation of an earlier
overlapping weak point. Mapped wakizashi and yari misses plus a positive
wakizashi hit exercise the production equipment path. Threats are frozen and
the drone is positioned by the fixture; this is not ordinary combat validation.

No new Unreal build or test has run for this source. Required runtime checks
include DroneMelee, DroneBody, LandingDrone, ClassMeleeCommitted,
GuardAndParryEveryMelee, CollateralConstruct and the assisted campaign.
Final art, ordinary controls and current packaged/platform results remain open.
