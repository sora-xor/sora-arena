# Inventory drone integration — 26 October 2026

This is a source integration checkpoint, not runtime or final art acceptance.
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
record is pinned by the importer to SHA-256
`346a2b86cdc626b57cb1ee245dce38b3948b35aedc0625d10e87b1d75530aedb`.
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

Still required: a successful editor build and import, DroneBody,
LedgerPatrols with the 0.1 cm altitude check, LedgerRoute, RegistryPatrols,
archery and horse-shell regressions, drone crossing/convoy/lift/boss routes,
in-game visual review, cooked/package evidence, SM5/SM6 performance, and final
art acceptance. No Unreal process has validated this checkpoint yet.

CPU validation: 104 distinct source gates pass (59 gameplay, 27 tooling,
18 assets). The first run retained four asset failures caused by existing
unmaterialized LFS files in the isolated validation checkout. After restoring
the cached objects with `git lfs checkout`, all 18 asset checks passed with
the same Git source identity. The eight drone admission tests include corrupt
FBX bytes, a changed source record, wrong scale/pivot, an outlying vertex still
inside the AABB, missing LODs, and reversed or scaled sockets. These source
checks do not compile C++ or execute Unreal collisions.
