# Chapter six: physical moat and submerged gate

This is source implementation for `ch06.b02`, bound to chapter-06.md §1.3 L1
and the authored b02 traversal, guards, sensors, detection, ally and exit.
It has not yet been compiled or executed in Unreal. No visual, packaged,
platform or performance acceptance is implied by the host checks.

## Physical contract

`campaign_moat.py` appends a separate campaign zone **after** all existing
placement, including b03 climb and b14 flood. Their generated records and zones
remain byte-equivalent as JSON values to integration baseline
`ba35d36b7a128c52f1e70616df9e5e13b20c9c87`; the host test pins their canonical
SHA-256 hashes. Arena collision and the existing flood/climb runtime are unchanged.
The new typed `moat` contract rejects missing, displaced or altered dimensions.

The water frame is 220 × 36 metres at z=0. The bed is z=-240cm, with a real
z=-300cm gate pocket and inner basin. Split bed slabs avoid a shallower floor
covering the pocket. The gate spans x=20600..21000, y=3560..3640; its only opening
is z=-180..-120cm. Stone on both sides, above and below physically refuses a
surface swimmer. The inner basin is bounded; entering its exit rectangle alone
cannot earn passage. A continuous, speed-bounded capsule crossing through the
opening must first have been observed. Checkpoint/fresh-world staging clears it.

The bank slope's **top** joins y=-400,z=100 to y=0,z=-240. The slab is offset
below its normal, and the pure-rule host test verifies both transformed endpoints.
Pilings and all three boat hulls collide. Reeds/lotus provide their authored
surface cover; the pilings/boats provide actual ray occlusion. The two lamp
mounts remain at (60/150m,48m,17.5m). The walk deck is z=17.5m; its patrol aisle
is provisionally 60cm behind the optical mounts so the lamps can shine down
from the front edge without intersecting their own deck. Physical support
columns remain below/behind this aisle. An engine fixture requires both sentries
to actually pass their respective lamp positions.

## Input, posture and air

Mapped Crouch toggles dive; mapped Jump requests surface. Forward/strafe remain
ordinary character movement with swept collision. This route alone uses a
28cm radius/half-height swimming capsule. Admission uses the real CMC crouch
resize even when already crouched, and halts a previously held weapon action.
The ordinary capsule/radius, crouch setting, gravity, air control and friction
are restored with headroom checks after actual bank exit. A teardown under the
lintel may use the existing checkpoint reset convention of relocating to a clear
entry before restoring size; ordinary traversal never uses that reset path.

The physical head is the capsule centre plus18cm. Camera interpolation and sway
cannot manufacture air, float clearance, cover or hitscan immunity. Surface
centre is -6cm; dive centre is -150cm, leaving2cm clearance at both gate edges.
The posture, head offset, bank slope, guard/drone pace and guide waypoints are
explicit provisional gameplay geometry, rather than authored anatomical values.

Surface speed is capped at180cm/s and immersed/dive movement at140cm/s. The
provisional70cm/s vertical stroke subtracts from the horizontal speed budget;
vertical motion remains a sweep and a blocked ascent cannot grant air. Actual
head immersion spends8s of breath, actual air recovers it over3s, and exhaustion
applies10HP/s through normal hazard damage. Arms and weapon selection are stowed
while swimming. A surface stroke uses the existing noise system's500cm nominal
radius; listener hearing sensitivity still scales its perceived reach.

The float line compares actual head depth with the typed80cm threshold;
merely requesting a dive is insufficient. The separate100cm threshold rejects
**traced hitscan rounds** in the production defense path. The hit carries an
explicit hitscan tag set by the real enemy ray attack; arrows, blasts, hazards
and drowning are not reclassified as hitscan.

## Living encounter

Both rifle sentries patrol their authored x ranges on supported collision.
The drone follows the figure-eight extents at6m, with a physical descent to3m
on detection. Their sight uses an actual 3D cone and ordinary visibility traces.
The existing light controller retains the70°/10s sweep,400cm radius,
0.5s/1.5s suspicion/alert thresholds and6s lock on actual last-seen evidence.

Detection releases the existing two-rifle wave onto the parapet. Those actors
become finite-search guards, not omniscient generic wave hunters. Alert movement
investigates the nearest point reachable on the guard's own route (or the drone's
altitude); actual swept arrival feeds the normal perception state machine. Its
20s search timer then runs normally, with difficulty scaling retained. Returning
to cover prevents visual reacquisition; arriving at the investigation point may
add travel time before that search window. No new global AI policy is applied.

Kohagi is the actual nondetectable companion. She swims a bounded swept route,
dives under the float, and waits outside the gate. Her passage cannot grant
player exit credit. The exact guide pace/path is provisional. The League mark
moves to the outer gate approach at x208m,y35m; its existing collectible pickup
mechanism remains in use.

## Qualification boundaries

Host checks cover typed/generated mutations, exact prior-space preservation,
actual pure C++ threshold/gate/air rules, and the transformed bank joins. The
first host attempt exposed a missing test-only `<initializer_list>` include;
the second exposed an incorrect test expectation at the exact gate tangency
(-148cm is a fit, -147.99cm is not). Both failed logs remain under
`Saved/SourceChecks/moat-depth`; subsequent focused checks pass.

Ten new Unreal fixtures are authored and **not executed in this worktree**:
`Campaign.MoatTraversal`, `MoatDepth`, `MoatFloat`, `MoatPauseRetryReload`,
`MoatSenses`, `MoatGuide`, `MoatLoader`, `MoatHands`, `MoatGateRetry`, and
`MoatPatrols`. They require mapped swim/dive/ascent input, actual bed/gate
collision, live sentries/drone/lamps, real air and damage, physical guide movement,
under-lintel refusal/death/retry, fresh-world state and safe bank restoration.
Only the equipment-isolation fixture freezes opponents; traversal and senses
keep them live. Health hardening isolates route execution from combat balance,
so the source fixtures do not establish final difficulty tuning.

The aggregate playthrough now uses the same real moat traversal helper.
`Fieldcraft.Water` uses physical mapped swimming; the older searchlight-isolation
fixture still controls its target position but waits for actual ascent. It is
not evidence of ordinary traversal. `Campaign.Spaces` retains every bed/support
probe and adds the correct physical swimmer clearance and actual airborne drone
clearance; grounded sentry posts retain standing capsule checks.

Required next gate: root-owned actual UE compile and these fixtures, plus
`Fieldcraft.Water`, `Fieldcraft.Searchlights`, `Campaign.Spaces` and the aggregate
playthrough. The source changes alone do not establish that capsule admission,
collision queries, sentry acquisition, pursuit expiry or gate transitions work
in the engine. Art remains procedural/blockout, not photoreal acceptance.
