# Inventory drone integration — 26 October 2026

The full UE 5.8.3 import passes at signed `47b49669`. Its directed runtime
suite finishes with 25 passes and two failures. Final art remains unaccepted.
The ledger's prior exact-height test failed: the humanoid capsule pushed the
drone from its authored 550 cm flight plane down to about 547.079 cm beneath
the 600 cm ceiling. Those authored dimensions remain unchanged.

Claude supplied signed source commit `fc0858a95ab6e488694962fedd20434680fff78f`.
Root verified all 20 changed files against their Git blobs or LFS identities
(13,540,608 bytes), viewed all six original Blender renders, and independently
ran the five record checks. The source is admitted for integration. Faint
machining rings in the top highlight, the faceted net pod, gameplay-distance
materials, and the `audit_hound` variant still require visual review. The
character shown in the scale lineup remains rejected and is not integrated.

The source kit supplies three authored LODs (10,386 / 4,362 / 1,660 triangles),
2048 maps, Eye and NetMuzzle sockets, and three convex UCX hit hulls. Its
original record was pinned to SHA-256
`346a2b86cdc626b57cb1ee245dce38b3948b35aedc0625d10e87b1d75530aedb`;
the reviewed socket export correction below replaces that pin.
The source and review images receive an OWN provenance record.

Runtime changes use the disc at actor scale one with a 38/38 cm movement
capsule. Visibility rays and projectiles use the disc's convex hit hulls;
they ignore the empty space in the movement sphere. A dedicated projectile
object channel preserves ordinary target and horse collision. Drones have
no humanoid body or handheld weapon. Sight and the net tether use the imported
sockets. Defeated drones lose their glow and fall against terrain; patrol
corpses remain discoverable, and combat-wave corpses retain their expiry.

`scripts/unreal/import_inventory_drone.py` imports the source LODs, maps and
UCX hulls without generated fallback shapes. It reads actual render positions,
triangle counts, socket positions/axes/scales, collision counts, and material
bindings back from Unreal. It rejects changed scale, pivot or orientation.
This small mesh uses conventional authored LODs on both shader paths; no
Nanite claim is made for it.

`SoraArena.Campaign.DroneBody` checks the actual imported body, exact spawn
height, sockets while turning, convex hull span, rays and real swept arrows
through the disc versus empty movement-sphere space, and falling defeat.
AI is held in that collision fixture. The actual flight loops remain the
responsibility of LedgerPatrols and the other encounter tests.

Still required: DroneBody,
LedgerPatrols with the 0.1 cm altitude check, LedgerRoute, RegistryPatrols,
archery and horse-shell regressions, drone crossing/convoy/lift/boss routes,
in-game visual review, cooked/package evidence, SM5/SM6 performance, and final
art acceptance. The C++ editor build and full import pass. Runtime tests are
not accepted until their completed reports and original logs are reviewed.

CPU validation: 104 distinct source gates pass (59 gameplay, 27 tooling,
18 assets). The first run retained four asset failures caused by existing
unmaterialized LFS files in the isolated validation checkout. After restoring
the cached objects with `git lfs checkout`, all 18 asset checks passed with
the same Git source identity. The eight drone admission tests include corrupt
FBX bytes, a changed source record, wrong scale/pivot, an outlying vertex still
inside the AABB, missing LODs, and reversed or scaled sockets. These source
checks do not compile C++ or execute Unreal collisions.

## Actual editor import attempts

All three attempts below retain original logs, natural process exit receipts,
source/native input hashes and Config/Generated snapshots in the complete-game
worktree's `Saved/Qualification/2026-10-26`. No source input or Config changed
during a run. Generated changes stayed inside the InventoryDrone folder.
The editor returned zero even when Python raised; the enclosing harness
correctly rejected each attempt.

| Source | Build | Import result |
| --- | --- | --- |
| `4a7401a3` | Pass | LOD threshold readback failed after the material edit. |
| `a1672075` | Pass | Moving threshold assignment after the material edit fixes the LOD check. Geometry passes; socket enumeration fails because UE 5.8 protects the array property. |
| `0eb8c5e5` | Pass | Public component socket enumeration works. Both source sockets import at about 100× scale and point backward, so socket admission fails. |

The final measured positions are correct: Eye is approximately
(36.22, 0, 0) cm and NetMuzzle (7.677, 0, -15.177) cm. Their forward axes are
(-1, 0, 0) and (-0.7071, 0, +0.7071), respectively. Expected scale remains one,
with forward Eye +X and the net muzzle forward/down. No replacement sockets
were created and the checks were not relaxed. Claude received the measured
failure and the engine lane for a scoped source-export correction.

Independent review SHA-256 values, in table order:
`bcf8e33eeaeb6de82befc2bc3578e4ca17907f57ce8537e1e139e40dad0f80ec`,
`522bcdd883ce8214ef596935408d3f8ec808c81560ad9e81de1bb39960f7db5d`,
`d852e4263f89930e87fb2c504c7641f7350079950b943cbe4446f7d2c7932ce5`.

## Reviewed socket correction and successful full import

Claude's signed `45a2af0ab3d10d9c2840731f177a227ab1a12dc9` re-exports only
LOD0 in UE's FBX import axes, with the unit conversion baked into geometry
and socket translations. Root independently checked all ten changed Git/LFS
files, the body and three UCX geometry arrays, unchanged blend/maps/other LODs,
and the narrowly changed record. Fourteen CPU checks passed without skips.
Source review SHA-256:
`d00113ea1b95fb2f12f9da6e5987fc8ba8ed5ce8d475527ea54bfe3248174c7c`.
The new record pin is
`eec9c2f4c38160feea3317cf05edd63b7f90af11197d53bcccfdd3cd63c74251`.

The old importer also disabled UCX through UE 5.8 Interchange's conversion of
`auto_generate_collision=False`. Installed engine source and Claude's real
control/corrected import probe establish that this flag gates custom hulls.
Enabling it imports UCX; custom hulls suppress the generated fallback. The
unchanged admission check still requires three convex and zero other shapes.

Root's `drone-47b4966-import-attempt2` builds and imports all three LODs, four
maps and the material. Real Unreal readback verifies 10,386 / 4,362 / 1,660
triangles, screen sizes 1 / 0.35 / 0.12, maximum radius 36.2273 cm, unit socket
scales, Eye +X and NetMuzzle forward/down, three convex hulls and zero other
simple collision. Build and editor exit naturally with zero. Inputs and Config
are unchanged; only six InventoryDrone generated packages change. Review:
`83a60046c3f13d89659b7fdd47f891db40854a2610cd2adb89d7df60c9926971`.
Attempt1 is retained as an unlaunched preflight failure: an abbreviated commit
ID did not satisfy the harness's exact full-SHA comparison.

Claude's updated CPU inventory predicts malformed socket exports in 83 sockets
across 26 weapon FBXs (correcting the initial count of 25). That is not yet actual weapon-import proof.
The viewmodel's unit-scale admission gate and full socket transforms make it
material; scoped real-import verification and correction remain open.

## Directed runtime at 47b49669

The 27-filter run completes naturally: editor exit 3, wrapper exit 1. Twenty
files are independently rehashed, all source/native inputs remain unchanged,
and Config/Generated are unchanged. Review SHA-256:
`58e08bc7cbdc71695417063c817543aefe60509ad826a3ddef1f4e0412c63bb3`.

DroneBody, the exact-altitude LedgerPatrols, LedgerRoute, LedgerLockdown,
PalaceFusuma, Spaces, RegistryPatrols, three archery/cache fixtures, three
horse-shell fixtures, LiftEncounters, RidgeDroneWind, FoundryBellowsNets,
CrankNets, RelayDroneMarkOnline, PressNetInterruption, CartNet, DroneCrossing,
PlantersNets and the three boss fixtures pass.

Two failures are retained, not reclassified:

- Playthrough cannot select a relay work spot free of body-drag priority.
  Its diagnostic has node 1, reachable control, grounded hero at
  (16600,-60,90), and `SoraEnemy_3` as the drag target. Two later unlock
  assertions fail after that early stop. One walking-simulation iteration
  warning is retained alongside the failed result.
- ConvoyNets nets the horse but its mounted katana cut does not free it;
  the dependent reload and eight-second protection assertions also fail.

These results qualify the scoped collision, flight, door and alarm fixtures,
not ordinary campaign controls, gameplay difficulty, final art or packaging.

## Follow-up runtime at 7b48ae3a

Both failures now pass in the seven-test convoy cohort, with no warnings.
The relay fixture retains body-drag priority and finds a valid grounded work
position around the fallen disc. Its long waits use bounded world ticks.
The convoy bug was independent distance stops: all three pack horses collapsed
onto one point, making the correctly committed cut free a different net.
The tied string now stops together and keeps its 450 cm spacing. Mounted net,
reload/protection, horse-fear, mounted combat, drone crossing and the full
assisted campaign pass. See [the convoy evidence](convoy-spacing-2026-10-26.md).
No final visual or ordinary-play acceptance is implied.
