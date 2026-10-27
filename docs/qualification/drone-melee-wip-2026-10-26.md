# Drone melee collision — directed runtime checks

This change addresses a recorded collision gap: both melee paths previously
swept `ECC_Pawn`, which hits the drone's 38 cm movement
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

`SoraArena.Campaign.DroneMelee` checks actual imported hull sweeps at
all three melee radii (16/36/45 cm), misses above/below the disc despite a
positive movement-sphere control, intervening cover, a valid contact behind
empty sphere space, blocking by the disc itself and preservation of an earlier
overlapping weak point. Mapped wakizashi misses and a positive hit exercise
the production equipment path. The landing permits only the wakizashi;
`DroneMeleeYari` exercises mapped thrust misses and a positive hit against a
positioned inventory drone at the permitted ch02.b03 checkpoint. Neither test
overrides weapon permissions. Threats are frozen and
the drone is positioned by the fixture; this is not ordinary combat validation.

The editor builds and directed tests now pass at their recorded revisions:
`DroneMelee` at signed `72d94e39`, and `DroneMeleeYari` at signed `497ea0e7`.
At signed `25789bc5`, DroneBody, all three LandingDrone cases,
ClassMeleeCommitted, GuardAndParryEveryMelee, CollateralConstruct, assisted
Playthrough and WardGateBrazier pass. Subsequent source changes are confined
to the melee fixtures. Original compile, weapon-selection and invalid-checkpoint
failures remain archived. See [runtime evidence](landing-melee-runtime-2026-10-26.md).
Final art, ordinary controls and current packaged/platform results remain open.
