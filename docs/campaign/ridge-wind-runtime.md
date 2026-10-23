# Chapter 7 ridge and hangar wind

This is a functional source checkpoint for [chapter 7](chapter-07.md) §§2.3,
3, and 6.10. It replaces the generic walled ridge room with the authored
180 m route and adds physical wind to the 80 × 45 m hangar mouth. It has not
yet been compiled, run, rendered, packaged, or performance-qualified in Unreal.

## Authored behavior implemented

- The ridge crown is 6 m wide, widens to 14 m at X=60–120 m, falls 2 m along
  its length, and has 20° side plates followed by real open edges. There is
  no hidden supporting floor beyond the plates.
- Ribs stand 1.2 m high every 12 m; 3 m sensor fins stand at X=30, 70, 110,
  and 150 m; a 15 m mast stands at X=90 m. Players can vault ribs with the
  normal Jump action or walk around their ends.
- Cables run at Y=±4 m with anchors every 6 m. The downwind cable has the
  authored gaps at X=45–55, 95–105, and 135–145 m. Held, remappable Interact
  requires actual grounded reach and an unobstructed cable trace. Releasing
  it, pausing, firing, jumping, leaving the beat, or retrying clears the brace.
- Wind is 8 m/s, gusting to 18 m/s on 11/9/14/10/12 second intervals, with
  a 1 second warning and a 2.5 second hold. Gameplay pauses stop the clock.
  The director raises the authored `gust_warning` and `gust_warning:first`
  dialogue events. A bilingual warning remains available without sound or
  color, and the brace hint shows the player's mapped Interact key.
- Exposed displacement is 120 cm/s standing and 60 cm/s crouched. A brace
  or traced lee removes it. The ledge guard limits only external wind;
  ordinary input can still step or jump into the void. A net root also
  holds the body against external wind.
- Actual arrows, grenade shells, and enemy shells receive lateral
  acceleration of 35 cm/s² per m/s of wind. Hitscan does not call this path.
  A projectile's physical lee trace suppresses drift while it is sheltered.
- Deliberate falls return to the last used anchor for 25 HP, at most three
  times per checkpoint. Insufficient health or a fourth fall triggers the
  existing defeat/retry flow. Retry starts a new gust cycle and recovery
  allowance. A held brace never persists across a save/reload.
- Ridge waves retain their eight drones, authored group positions and
  mid/forward volume triggers. The rear hatch must be reached on the ground
  after the waves are cleared. Gust onset interrupts exposed drone aim for
  0.6 seconds. Only ridge wave drones receive the chapter's 1.2 second net
  hold; other drones keep the enemy catalog's duration.
- The hangar mouth occupies X=20–60 m, Y=33–45 m and has no movement wall
  across its opening. External push stops at the lip. The floor, gallery at
  Z=8 m, two stair flights, and walk-around shuttle silhouettes are collision
  geometry, with the gallery enemies placed at the authored height.

## Explicit implementation choices

The chapter leaves these details unspecified. They are provisional and need
Unreal traversal, combat, and visual review before they are accepted:

- Schedule entries are interpreted as gust-onset intervals. Standing and
  crouching displacement use the stated fixed speeds in both steady wind
  and gusts; projectile acceleration follows actual wind speed.
- The 4 m plates are measured horizontally. Thirty 6 m segments form the
  crown and plates, with a sharp width change at the shoulder. Plate/crown
  thickness is 40 cm; ribs are 60 cm deep. Fins are 35 cm thick, centered at
  Y=−1.8 m, and the mast is at Y=−5 m. These are collision proxies, not final
  engraved hull geometry.
- Wind exposure is limited vertically to Z=−8…22 m on the ridge and
  Z=−5…14 m in the hangar mouth. Lee uses a 3 m upwind visibility trace from
  the player's eye, with ribs protecting only a crouched player. Projectile
  shelter traces originate at the projectile itself.
- Cable reach is 135 cm laterally, requires feet within 20 cm of the plate,
  and remembers the nearest valid anchor on that cable side. The entry
  anchor is the fallback before the first brace. A recovery occurs 5.5 m
  below the local crown; the return is offset 1 m along and inboard of its
  anchor to avoid the post. End posts are inset 60 cm for capsule support.
- Drone drift is 120 cm/s during gusts; the chapter names drift but gives no
  speed. Members of a ridge group start 120 cm apart along X to avoid
  overlapping capsules at the authored group point.
- The indigo tenugui is a thin first-person mesh on the existing yumi upper
  limb. Its pose responds to wind and warning, but it is not finished cloth
  animation, and its in-frame visibility still needs rendered review.
- The hangar uses a flat deck and shuttle boxes with provisional 4.6 m
  height, rather than complete shuttle interiors. Shield troops appear
  just outside shuttle 2's proxy instead of inside its solid collider. The
  existing loose collectible placement is still generic. The failing force
  curtain, shuttle ramps/cockpit, sleds, canisters, doors, roof, moon/cloud
  vista, hull materials, wind roar and spindrift remain art/gameplay work.

## Verification boundary

`scripts/unreal/test_ridge_wind.py` compiles and exercises the production
header's gust schedule, grade, plate widths, displacement guard and drift
math. It also rejects malformed normalized data and checks its authored
values. The broader gameplay source gate checks deterministic data generation,
campaign validation, localization and existing rule regressions. These host
checks do not validate UE collision, input dispatch, rendering or C++ APIs.

Four Unreal fixtures are supplied but not yet executed in this worktree:

- `SoraArena.Campaign.RidgeWind`: mapped brace and remapping, crouch and lee,
  root interaction, pause, gust timing and a fresh-world checkpoint reload.
- `SoraArena.Campaign.RidgeTraversal`: actual collision traces, the full
  route with mapped movement/vaults, wave triggers, last-anchor recovery,
  the three-fall cap and the normal retry action.
- `SoraArena.Campaign.WindProjectiles`: real mapped arrow/grenade fire,
  an ordinary enemy shell, unchanged hitscan, and hangar/lee boundaries.
- `SoraArena.Campaign.RidgeDroneWind`: a real wave drone's net delivery,
  scoped hold duration, gust interruption, reacquisition delay and drift.

Force/reach cases explicitly relocate to supported sampling positions.
Traversal cases freeze threats to isolate movement; the drone case freezes
its brain and movement while running its attack state machine. The campaign
playthrough now uses mapped ridge traversal between wave goals, but its
existing direct-damage combat helpers remain. None of these fixtures proves
human combat balance, the four-minute pacing target, art quality, accessibility
playtest completion, or either platform's performance budget.
