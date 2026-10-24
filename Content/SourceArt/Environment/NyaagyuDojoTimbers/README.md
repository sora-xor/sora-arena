# Nyaagyu dojo timbers: columns cut from their own logs

Replacement for the box `SM_DojoColumn` in the estate halls
(`ASoraWorldBuilder::HallInterior`). These are hinoki columns, 24 cm square and
7 m tall, with that column's pivot: floor level, the room-facing −Y face 4 cm
proud of the bay line, the back face in the wall.

Each column is a seeded 3D log (`scripts/art/sora_timber_lib.py`):

- **Log structure:** pith position, lean and sweep; ring widths with wobble;
  whorls of knots whose rings swirl around them; spiral-grain drying checks
  down the faces.
- **Surface detail in the geometry:**
  - kanna plane strokes;
  - worn round-over arrises at handling height;
  - bokken dents;
  - a slight bow.
- **Ring figure:** carried by the material instead. Each vertex stores its place
  in its log: UV2 is the offset from the pith, UV3 the height and seed. So the
  rings agree across faces, arrises, check walls and end grain.

Mesh density follows the detail:

- 5 mm spacing on the visible faces;
- 2.5 cm on the faces hidden in the wall;
- finer only across checks, knots and arrises.

## Two sets

| Set | Names | Drawn | Mesh | Stored |
| --- | --- | --- | --- | --- |
| Placements | `SM_DojoTimberColumn_<x0>_<y0>_<x1>_<y1>_S<side>_B<bay>` | where Nanite runs (Mac SM6, Windows) | one dense log per column placement; Unreal generates the fallback | not committed: rebuilt from seeds into `Local/ArtCache/NyaagyuDojoTimbers` |
| MAC pool | `SM_DojoTimberColumn_MAC_{Wall,Open}_NN` | without Nanite (Mac SM5/M1), and for any placement without its own log | coarse mesh with the checks in geometry, NormalDX and Masks baked from its own dense log | committed (LFS): `FBX/`, `Maps/` |

The two column kinds:

- **Wall columns** detail the room face and the 6 cm of each side in front of
  the infill.
- **Open columns** stand beside door and engawa bays and detail every face.

`scripts/art/dojo_hall_placements.py` lists every placement. It replays
HallInterior's bay layout over the estate halls in `Content/Data/campaign`. Each
placement's name comes from its hall's rect, wall and bay, and its seed from
that name.

A building that appears in several chapters keeps the same logs. HallInterior
logs `SORA_DOJO_TIMBERS` per hall: columns drawn with their own log, from the
pool, or as boxes.

## Rails (`Rails/`)

`scripts/art/create_nyaagyu_dojo_rails.py` makes the bay rails as members
laid horizontal by a proper rotation (no mirror):

| Rail | Height | Span | Stock |
| --- | --- | --- | --- |
| Nageshi | 2.10–2.30 m | full bay | quarter-sawn, straight-grain face, knot-free |
| Cornice | 6.78–7.00 m | full bay | quarter-sawn, straight-grain face, knot-free |
| Koshi | 0.88–1.00 m | between the column faces | flat-sawn, a few knots; worn along its top arris at hand height |
| Nuki | 4.30–4.42 m | between the column faces | flat-sawn, a few knots |

The two sets:

- **Placements:** `SM_DojoTimberRail_<Kind>_<rect>_S<side>_B<bay>`, cut to
  their bay's exact length and drawn unscaled.
- **MAC pool:** `SM_DojoTimberRail_MAC_<Kind>_NN`, at the nominal 1.8 m bay,
  stretched by HallInterior.
- The kit's `SM_DojoRail_*` boxes stay as the last fallback. The bay modules
  no longer carry rails.

## Floor (`Floor/`)

`scripts/art/create_nyaagyu_dojo_floor.py` rebuilds the kit's 3.6 × 2.6 m
floor tile:

- 18 rows of flat-sawn boards, each from its own log, polished on top;
- cupping across the width, small height and tilt offsets between boards, and
  0.5–1.2 mm gaps.

Boards are unique within a tile, but **the tiles repeat across a hall**. The
generator has not run yet: there is no `Floor/` output, and HallInterior keeps
drawing the kit's four floor tiles.

## Coverage (manifest `coverage`)

| Set | Placements with their own log | Estate placements | MAC pool |
| --- | --- | --- | --- |
| Columns | 65 (53 wall, 12 open) | 260 | 13 (10 wall, 3 open) |
| Rails | 235 (64 nageshi, 64 cornice, 64 nuki, 43 koshi) | 940 | 12 (3 per kind) |

- **Built:** the chapter-1 dojo rect `(8000, −1300, 11600, 1300)`, which
  chapters 2 and 4 reuse. Within that hall every column and rail has its own
  log: 65 and 235 distinct seeds and 65 and 235 distinct geometry digests.
- **Not built yet:** the three other estate halls, `pl_dojo_smithy`,
  `pl_suisha_goya` and `pl_gogura`, with 195 columns and 705 rails. They draw
  the MAC pool until `--halls all` is built and imported. So across the estate,
  not every timber has its own log.
- **Campaign drift:** the halls come from the chapter files as of this build;
  the ledger records their hashes. In the integration branch's later chapter
  data (`c139192`) the chapter-1 hall is unchanged, but the smithy hall moved
  to x 38800–42400, so its unbuilt placements take new names. Nothing built is
  affected. The manifests pin the generator scripts, not the chapter files.

## Sizes

| Where | Files | Bytes |
| --- | --- | --- |
| Committed (LFS): column pool `FBX/` + `Maps/` | 13 + 26 | 68,228,604 + 26,072,675 |
| Committed (LFS): rail pool `Rails/FBX/` + `Rails/Maps/` | 12 + 24 | 10,685,888 + 6,189,346 |
| Committed (LFS): `Shared/` textures | 3 | 2,921,021 |
| Committed (LFS): `Renders/` | 9 | 14,144,583 |
| **Committed binaries in all** | **87** | **128,242,117** |
| Cache: column logs `Unique/` | 65 | 4,626,705,932 |
| Cache: column bake sources `PoolDense/` | 13 | 967,798,332 |
| Cache: rail logs `Rails/Placements/` | 235 | 2,679,963,780 |
| Cache: rail bake sources `Rails/PoolDense/` | 12 | 131,525,200 |

Triangles:

- **Nanite source:** 35,898,400 for the 65 column logs (about 552k each) and
  21,211,910 for the 235 rail logs: **57.1 M for one hall**.
- **SM5 pool:** 625,546 for the 13 columns and 92,230 for the 12 rails.

## Rebuild

```bash
blender -b --factory-startup --python scripts/art/create_nyaagyu_dojo_timbers.py -- --halls ch01 --cpu
blender -b --factory-startup --python scripts/art/create_nyaagyu_dojo_rails.py -- --halls ch01 --cpu
blender -b --factory-startup --python scripts/art/create_nyaagyu_dojo_timbers.py -- --halls ch01 --cpu --verify
blender -b --factory-startup --python scripts/art/create_nyaagyu_dojo_rails.py -- --halls ch01 --cpu --verify
blender -b --factory-startup --python scripts/art/render_dojo_timbers_lookdev.py -- --cpu
scripts/toolchain/run-editor-script.sh scripts/unreal/import_nyaagyu_dojo_timbers.py NYAAGYU_DOJO_TIMBERS_READY
```

How the steps fit together:

- **Digests.** The manifest pins the generator, every input script's SHA-256,
  the Blender, numpy and Python versions, and a canonical geometry digest per
  mesh. The digest covers topology, positions, corner normals, every UV layer,
  the masks and the material slot, quantised (`sora-timber-geometry-v1`).
  Two separate Blender runs reproduce the digests exactly.
- **Evidence.** `--verify` rebuilds against the committed manifest. It fails on
  any mismatch and writes `Local/ArtCache/NyaagyuDojoTimbers/evidence.json` with
  that run's FBX hashes.
- **Import.** The importer refuses files the evidence doesn't vouch for.
- **CPU rendering.** Cycles' Metal kernel compile hung on this M2 Ultra
  (macOS 27.0.1, Blender 5.2.2), so `--cpu` renders on the CPU.

## Materials

`M_SoraTimber` (pool, baked maps on UV1) and `M_SoraTimberNanite` (placements,
vertex masks) compute the growth rings from the log frame. The model:

- ring widths wander over a few rings, from the shared `T_TimberRingNoise`;
- earlywood grades into a latewood band;
- the next year starts abruptly;
- each year has its own strength, from `T_TimberRingRandom`;
- fibres and drift come from `T_TimberFibre`;
- the clear coat is fuki-urushi.

The normal is bumped by the ring ridge with screen-space derivatives.
`scripts/art/sora_timber_lookdev.py` is the Blender equivalent: the same
textures and the same math.

## Provenance

Original: procedural geometry and procedural shared textures, with no
third-party inputs. The OWN record is in `manifest.ledger.json`.

## Verification

- **Clean rebuilds** (`--verify`, Blender 5.2.2, CPU): columns at
  2026-10-18T14:25:19Z (`DOJO_TIMBERS_VERIFIED 65`), rails at 14:42:27Z
  (`DOJO_RAILS_VERIFIED 235`).
- **Digests:** every placement and pool member matched its manifest digest,
  with zero mismatches.
- **Cache hashes:** each cached FBX hash matches `evidence.json`.
- **Committed files:** every pool FBX and map matches its manifest SHA-256.
- **Look-dev:** `render_dojo_timbers_lookdev.py` rebuilt `MAC_Wall_00` and
  matched both of its digests before rendering.

## Honest status

What has run:

- **Only Blender source renders exist** (`Renders/`, CPU Cycles). No Unreal
  import, SM6/Nanite or SM5 capture has run.
- **Nothing has been measured:** GPU time, Nanite stats, cooked size or
  memory. 57.1 M Nanite source triangles for one hall is heavy, and the whole
  estate would be about four times that.

What the renders show:

- **Close-range relief doesn't read.** In `Clay_Raking_Close` the faces look
  flat: kanna strokes, raised grain and dents sit below what the raking light
  picks out. So the 5 mm spacing buys little visible detail yet. Raise the
  relief, or coarsen the flat areas.
- **The checks read as clean saw kerfs.** Their lips are parallel, with no
  taper at the ends and no torn fibres. The fallback also shows a stair-step
  along the right-hand check in `Fallback_Raking_Close`.
- **Grain and colour read as procedural:** regular vertical stripes, even
  colour. The soot, grime and hand-polish masks exist but don't show in these
  renders.
- **The golden-hour rig washes out** the backdrop and the wood. It is not the
  reference look; the two reference images are still unavailable.

What isn't built:

- **End caps are flat** (which fixed the bake's fan artifact). Visible beam
  ends still need end grain with the checks carried through.
- **Coverage is one hall** (above). The floor generator hasn't run.
