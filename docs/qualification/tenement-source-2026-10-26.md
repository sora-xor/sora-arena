# Back tenements: source checkpoint, 26 October 2026

This is provisional functional geometry and interaction source for chapter three.
It has **not been compiled or run in Unreal**. The engine/Blender lane remains with
Claude for the r3 character export and readback. The published integration branch
and previous package are unchanged; this branch also contains the uncompiled ward
gate and stream checkpoints. This is not final art or release qualification.

## Implemented source

The five tenement beats now use their authored district coordinates: twelve homes
of 2.7 m frontage and 3.6 m depth, a 1.8 m alley, court, front-shop storeroom, manager
room, two wells, west fence gap and the north passage. Closed shoji inner faces
preserve the alley's full width. The existing arena boundary has specific openings,
and one north-side building is split around the 1.2 m passage, including its
foundations. Existing arena ground is retained without a second coplanar floor.

The dry well has a 90 cm clear bore, actual floor 7 m below the court and a 75 cm
curb. Its held-input path aligns outside the well, rises over the curb, enters and
descends using swept movement of the unchanged player capsule. The return reverses
that path. The bottom still requires three seconds of bow stringing and restores
the existing equipment and twelve-arrow grant. Weapon-bundle proxies stand against
the lining instead of lying horizontally through the shaft.

Loose finds now use their authored height and the existing floor-aware interaction
reach. The well scroll is at -650 cm; a court interaction cannot collect it from
above. The bottom interaction can collect it as ascent starts. Its provisional
visual sits in the lining. The manager's find sits on the desk at +125 cm. The
manager room floor is +45 cm, reached by two 22.5 cm rises; the first tread is 70 cm
deep to clear the capsule's rounded foot.

The hoist and storeroom use their authored points. Two street guards retain a
45-second circuit; their parallel paths are 100 cm apart so bodies do not overlap.
The gutter occupies the central 80 cm of the alley and uses the authored 1.5x noise
multiplier. Cloth proxies block visibility queries while allowing pawn movement.
Cookfire points and the b14 hold anchor lie in the court's west lean-to.

## Source checks

Nine targeted host tests pass. They compile the exact builder solid table with
Clang, warnings as errors and undefined-behavior checks, then test capsule clearance
and floor support along the new routes. Coverage includes home dimensions, both
alley edges, north passage, hoist/carry/storeroom route, shaft depth, curb traversal,
manager landings, patrol separation and west fence access. Negative controls reject
an oversized body in the bore, direct ground-level entry through the curb, and
changed recovery/patrol/pickup-height contracts. These checks cover the new solids;
the complete built arena and CharacterMovement require the Unreal fixtures.

Campaign regeneration is unchanged on a second run. The validator passes 133 beats
and 1,032 bilingual lines, and rejects its 65 invalid variants. The dojo campaign
binding is refreshed only for the changed chapter-data hash.

The first broad run at signed `301d66f1` finished with 118 passed and one failed
(`lift-data`), with clean unchanged source. Its report and logs remain in
`Saved/Qualification/2026-10-26/tenement-301d66f1-source/`. The lift helper reset
every record's floor to zero before applying its own two floors, so rerunning it
flattened the new manager room. It now initializes only missing heights and
preserves other layouts' authored floors. The existing deterministic/scoping test
no longer repairs archive and summit heights after that call; it requires them,
and the manager room, to remain intact. This is a production helper fix, not a
waiver of the failing check.

The corrected signed source `e294100a6b66898a846d9df8a05c44b47950a64f` (tree
`3c3cac45059c8da8e99a4c2a732dc14f2a60f57f`) passed **119/119** selected host
checks: 64 gameplay, 27 tooling, 22 assets and 6 audio. Rust was not rerun. The
checkout remained clean and unchanged. The report is
`Saved/Qualification/2026-10-26/tenement-e294100a-source/report.json` in the
source-validation worktree, SHA-256
`48de1140b5d6bc33cb55fe6d628468e272d940172f84aada7a04337d2d990051`.
The separate inventory, 119-log hash, signed-source and preserved-failure audit is
`independent-review.json`, SHA-256
`7da7450c96049020908a9b718ed3bdd828106563e297ae5378e4934f1745bd7d`.
These passes do not compile Unreal code or establish any runtime or art acceptance.

## Pending runtime validation and known omissions

New fixtures `SoraArena.Campaign.Tenements.Solids` and `.Routes` check actual shaft,
curb and room collisions, cloth sight blocking, held recovery and hoisting, mapped
crate carry, manager stair movement and the narrow north passage. The existing
`SoraArena.Campaign.EquipmentRecovery` fixture also checks the nearby court cannot
take the lining scroll, bottom collection, and persistence across a new world.
They are source only and have not been compiled or executed. Directed fixtures hold
guard AI; they do not establish ordinary stealth difficulty. Existing recovery,
carry, fieldcraft, campaign-space and assisted-playthrough regressions must rerun.

The remaining authored tenement work includes its people and door-balance displays,
separate c01/c02 interactions (the old combined explore cache remains), the 150 s
hint lamp, final craft/cloth/prop art, b14 drone altitude and west-gap wave routing,
and b10's continuation from the notice-board approach. The ward-to-tenement street
still uses a beat transition: the intervening floor and ward east opening have not
been connected. This checkpoint does not claim continuous district traversal,
finished chapter-three design, ordinary campaign completion or performance.
