# Dojo timber v2 pilot: six members with geometric raised grain and adze

**Status:** source and CPU checks only. Nothing has run in Blender or Unreal,
and nothing is rendered or imported yet. The frozen v1 slice (`6b0e93e`) and
its 8.4 GB baseline cache are untouched. The pilot has its own geometry
version (`sora-timber-geometry-v2`) and its own namespace
(`Local/ArtCache/NyaagyuDojoTimbersV2Pilot/`), and writes nowhere else.

This follows root's read of `ea2c769`: the visible adze marks and raised
grain must be **real Nanite geometry**. The shader may only supplement them.

## Two v1 material faults this work found

Both are in the material math, not the geometry, so no v1 digest changes.

1. **Unreal flips V on every UV channel at FBX import**
   (`FbxMesh.cpp:944`, `FbxStaticMeshImport.cpp:758`, inside the loop over
   all UV layers). The timber masters read UV2 as the offset from the pith,
   so in Unreal r becomes √(x² + (1 − y)²), about a metre off; the seed
   (UV3.V) becomes 1 − seed. The fix, already sent to root, is in the
   material: `q = (U, 1 − V)`, `seed = 1 − UV3.V`, and `RingNoise` and
   `RingRandom` sampled at `1 − v`.
2. **The ring-width wander was chaotic.**
   - v1 sampled the 1024-texel `RingNoise` row at `nu = r / 6w`: the whole row
     over just 6 rings, about 170 texels per ring.
   - Its ±1.5-ring term outruns the rings themselves by up to 8.8×.
   - So across one 24 cm face the phase reverses 440 times. That paints fine
     chaotic stripes instead of rings that wander every few years, and likely
     explains much of the "uniform parallel lines" grain.
   - v2 uses `nu = r / 300w`, about 3.4 texels per ring, so the noise's shortest
     wave spans about 5 rings, with an amplitude of 2.6 rings. The phase is then
     monotonic (one turn, at the face centre), and ring widths vary 0.90–1.14×
     across that face.
   - `sora_timber_lookdev_v2.py` and `sora_timber_v2.ring_phase` both use it.
     Unreal's masters need the same two constants for v2 assets, and v1 would
     benefit too.

## What v2 builds

`scripts/art/sora_timber_v2.py` is numpy only, and it imports v1 without
changing it.

**Raised grain** is the latewood standing proud of the earlywood, as real
displacement:

- **Same phase as the shader:** each vertex's ring phase is the materials'
  formula, using the shared textures (byte-identical to the committed PNGs),
  the member's own ring width, and the log frame it stores in UVLogQ/UVLogZ.
  Each ridge therefore sits on its shaded latewood band; rebuilding the phase
  from the stored UVs gives an error of 0.0.
- **Profile:** samples sit at four phases of every ring (0, 0.51, 0.70, 0.83),
  so triangles run along the grain and the piecewise-linear ridge stays within
  5 µm of the masters' smooth one.
- **Scale:**

  | Surface | Earlywood recess |
  | --- | --- |
  | Indoor planed faces | 25–45 µm |
  | The hand-worn koshi top | 0.10–0.18 mm |
  | Knots and dents | faded out |

**Where the grain is geometry** follows one physical rule: wherever a player
can come within about a metre, a 1.4–2.4 mm ring is several pixels.

- columns: the 0.6–2.0 m band;
- nageshi and koshi: their whole length;
- cornice (6.8 m): never that close, so the shader carries it.

**Adze (chōna):**

- staggered scoops 3.4–4.2 cm across and 5–6.4 cm along, 0.9–2.3 mm deep, plus
  v1's undulation;
- a C1 rim (v1's profile, never used before, was infinitely steep at the rim
  and folded once sampled);
- shallowing to zero where the arris round-over starts;
- on the nuki's room face and underside.

**Split checks:**

- a meander of 0.5–2 mm over 8–20 cm, an opening varying ±45%, and fibre
  bridges;
- hairline runs of 2–6 cm past each end, and 30% forked ends;
- an asymmetric V with depth 8–25× the opening, torn lips and splinters;
- 17 samples across each check in every row (nothing else enters its zone),
  and a 0.16 mm half-width floor.

**Bokken dents** run across the grain (6–22 mm × 1.5–7 mm, 0.15–0.9 mm deep)
with a crushed rim. They're sampled at 1.5 mm.

**Sampling:**

- base rows every 4 cm, with a 2 cm grid on every face in every row, so a stitch
  never fans a short edge across a face;
- feature rows on shared lattices: 10 mm for grain and checks, 2 mm at check
  ends, bridges and splinters, 1.5 mm for dents and knots;
- each feature's fine samples widened to the enclosing base rows;
- 6 arris samples.

**Form:** v1's bow, plus a 1–3 mm drying twist on the columns.

**The SM5/M1 fallback** stays separate (`fallback()`): the same log and checks
at 2 cm, with grain, adze scallops, knots and dents left to the bake from the
dense mesh.

## The six members (`scripts/art/dojo_timber_pilot.py`)

Each member is the first chapter-1 placement of its kind: the same seed, log
and finish as v1, named `<v1 name>_V2`.

| Member | Relief | v1 triangles | v2 dense | v2 fallback |
| --- | --- | --- | --- | --- |
| Wall column `…S0_B01` | grain on the room face and front strips, 0.6–2.0 m | 470,624 | 454,612 | 44,918 |
| Open column `…S0_B00` | grain on all four faces, 0.6–2.0 m | 836,068 | 1,088,942 | 54,970 |
| Nageshi | grain on the room face, whole length | 106,320 | 338,460 | 9,746 |
| Cornice | shader only (beyond 1 m) | 114,012 | 40,178 | 10,012 |
| Koshi | worn-top grain 0.10–0.18 mm; room face 30–60 µm | 68,280 | 125,590 | 6,836 |
| Nuki | adzed room face and underside | 63,976 | 98,208 | 6,428 |
| **Total** | | **1,659,280** | **2,145,990** | **132,910** |

## Checks (`check_mesh`; every result in `data/timber_pilot_checks.json`)

All twelve meshes (six dense, six fallback) pass:

- **Closed:** every edge is shared by exactly two triangles.
- **Consistently wound:** no directed edge repeats, and the signed volume is
  positive.
- **No degenerate triangles.**
- **No folds:** no triangle faces away from its section normal; inside checks
  the tolerance is −0.05.
- **No row crossings:** no sample passes its neighbour along a row once
  displaced.
- **No needles:** the largest interior angle outside checks is under 179°.
  The worst is 178.5°, and the few above 175° have normals within 0.97–1.00 of
  the face's.

Each feature carries its specified relief:

- every check holds 17 samples across, with constant topology (except where a
  forked hairline joins its parent);
- dents reach 81–100% of their depth;
- the grain recess at p95 is 42–43 µm on the columns, 32 µm on the nageshi and
  0.12 mm on the koshi top, and the phase from the stored UVs is exact;
- adze depth is 2.2 mm at p50.

Steep relief, such as a dent wall or an adze crease, is counted but allowed.

`scripts/art/test_sora_timber_v2.py` has 13 tests, passing on numpy 2.3 and
1.23. Besides the above, they cover every defect reproduced on the way:

- a hole, a flipped triangle, a fold and a crossing;
- misaligned grain UVs;
- an adze that ignores the arris;
- v1's wander reversing more than 100 times on the face;
- the frozen kit's inputs unchanged;
- the namespace guard.

**Visibility** on the room face (the koshi's top): the p95 tilt, and the
shading change that tilt makes under raking light at 30°.

| Surface | Shading change |
| --- | --- |
| Plain planed | 0.3–1.3% |
| Raised grain, columns | 8.2–8.5% |
| Raised grain, nageshi | 14.7% |
| Koshi worn top | 54.5% |
| Adze | 74.4% |
| Dents | 19–72% |
| Knots | 15–37% |

v1's planed faces were 1.2–1.4% even at a 10° graze.

## The bounded pilot run (needs your Blender slot)

```bash
/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python-exit-code 1 --python scripts/art/create_nyaagyu_dojo_timbers_pilot.py -- --cpu --samples 96 --bake-res 2048
```

It writes only `Local/ArtCache/NyaagyuDojoTimbersV2Pilot/`. The path guard
refuses the frozen kit and its cache.

| Output | Files | Estimate |
| --- | --- | --- |
| `Dense/*.fbx` (Nanite source) | 6 | about 280 MB (2.15M triangles at v1's 129 bytes per triangle) |
| `Fallback/*.fbx` | 6 | about 17 MB |
| `Maps/T_*_{NormalDX,Masks}.png` (2K bakes) | 12 | about 20 MB |
| `Renders/*.png` (1600×1000) | 15 | about 23 MB |
| `Shared/`, `manifest.json`, `evidence.json`, `checks.json`, `renders.json` | | small |

The 15 renders are clay and v2-material pairs:

- the wall column's grain close-up, check close-up (plus the SM5 fallback),
  dent close-up and arris mid shot;
- the koshi's worn top, the nuki's adze and the nageshi's grain.

**Time, about 20–25 min of CPU,** from v1's logs:

- **Members, about 6–9 min:** a dense column build and export averaged 17 s,
  a pool member with its 2K bake 38 s; pilot members are similar or smaller,
  except the open column.
- **Renders, about 10–15 min:** about 40–60 s each.

The run stops before exporting anything if a mesh fails its checks.
Afterwards, `-- --cpu --verify` rebuilds and compares digests, writing only
`evidence.json`.

**After the run (your lane):**

- import into an isolated `/Game/Generated/Qualification/DojoTimberPilotV2`,
  with Nanite resource counts and cooked bytes per triangle;
- the V-flip and v2-wander material corrections;
- SM6 close originals (clay and material) and the SM5 fallback, against the
  Blender originals.

## Not done, not claimed

- No Blender run, bake, render, Unreal import, Nanite or GPU measurement.
- No photoreal acceptance.
- No coverage beyond these six members.
- The Unreal material corrections are root's, in `timber_master`.
- Root's capture inventory needs the pilot namespace added.
