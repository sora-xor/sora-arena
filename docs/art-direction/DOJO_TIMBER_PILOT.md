# Dojo timber pilot: six members with geometric raised grain and adze

**Status:**

- **Run 1 (v2, `sora-timber-geometry-v2`):** ran once in Blender on CPU and
  was archived read-only. It is **not visually accepted**.
- **v2.1 (`sora-timber-geometry-v2.1`):** fixes what run 1's renders showed.
  It ran once in Blender on CPU at `4481327` (exit 0, 15 renders) and was
  archived read-only (`data/timber_pilot_v21_run1.json`). Root's review:
  the geometry is corrected, and the wood character still fails.
- **v2.2 (`sora-timber-geometry-v2.2`):** the wood character. It ran once
  at `0d9a6ef` (Blender PID 96256, natural exit 0, 15 originals) and was
  archived read-only (`data/timber_pilot_v22_run1.json`: 46 files,
  477,383,434 bytes). Root reviewed all 15 and rejected them, as did I
  (below).
- **v2.3 (`sora-timber-geometry-v2.3`):** source and CPU only, not run.
  - It redoes the naguri.
  - It measures the two CC0 scans the focused patch study is judged against.
  - It adds the study's driver.
- **Untouched:** the frozen v1 slice (`6b0e93e`) and its 8.4 GB baseline cache.
- **Namespaces:** v2.3 writes only `Local/ArtCache/NyaagyuDojoTimbersV23Pilot/`,
  and its patch study only `Local/ArtCache/NyaagyuDojoTimbersV23Patch/`. The
  path guards refuse run 1, the v2.1 and v2.2 runs, the v1 kit and its cache.

## Run 1 (v2), archived

- **The run:** Blender PID 33971 exited naturally with code 0:
  `PILOT_READY 6 members, 2145990 Nanite source triangles, 15 renders`.
  - Members took 79 s; the renders took 20–54 s each.
- **The archive:**
  - `Local/ArtCache/Archive/NyaagyuDojoTimbersV2Pilot/run1/receipt.json`, with
    its tracked copy `data/timber_pilot_v2_run1.json`;
  - 46 files, 387,835,397 bytes, `files_digest c2ad8da5…`;
  - the run directory is read-only.
- **Verification:**
  - only from the frozen `82869a4` inputs;
  - read-only, with its own receipt under `Local/ArtCache/Verification/`;
  - this tree's v2.1 sources can't reproduce run 1's canonical geometry.

**The renders showed these defects. Each has a fix and a regression test here:**

| Defect | Cause, as measured | v2.1 |
| --- | --- | --- |
| Check lips step sideways row by row | v1's ladder paired rows by position. The meander moves a check p95 2.2–3.5 half-widths per 10 mm row, so only 27–32% of row pairs joined their V-bottoms (forks 0/17) | Each check is stitched in its own frame. All V-bottoms now join, forks included |
| Grain beading near knots | Knot swirl and log wobble bent the rings between 10 mm rows: p99 0.056 rings in the close band | Rows and samples refined until linear interpolation holds the rings: p99 ≤ 0.023 |
| Radial streaks at knot edges | Inside knots, UVLogQ swapped to knot-centred rings, so edge triangles blended two frames up to 77 rings apart | UVLogQ stays continuous. The knot's rings move to UVKnot (UV4), selected per pixel |
| A seam the full length of the open column's face 2 | v1's wobble at `0.08·atan2` jumps up to 3.5 rings where atan2 wraps at ±π (the frozen v1 kit has it too) | A periodic wobble with the same scale |
| A second fork naming the wrong parent | v2's `checks_v2` bookkeeping | Fixed; junctions are explicit |

**Not yet fixed in v2.1's geometry: wood character.** Codex's review (02:40)
and my own found:

- blister-like dents;
- a glossy, ribbed koshi top (the fuki-urushi clear coat);
- repeated hammered dimples on the nuki (no tiled naguri facets);
- broad clean stripes with little ring-to-ring variation;
- smooth knot patches;
- weak fine-fibre and finish variation.

These are the next candidate. They will be corrected against physical wood
character, not by dimming the room or adding polygons.

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

## v2.3: the naguri, the scan reference and the focused patch study (source and CPU only; not run)

**Root's review of the v2.2 originals:**

- Broad brown bands with hard, faceted boundaries dominate.
- Fine longitudinal fibres are not resolved.
- GrainClose has a faint diagonal crosshatch, cause unmeasured.
- CheckClose is a mostly uniform dark slot with a smooth bright lip.
- Clay GrainClose is nearly smooth apart from the crack.
- The nuki's rectangular, staggered pattern is prominent in clay.
- Root asked for one column and one rail, iterated against real close-up wood
  at the same physical scale, before another full batch. Ring, fibre and
  check character must show in clay and grazing light as well as in the
  material.

**The naguri** (`adze`, `_naguri_layout`):

- The chōna strokes are hand-laid. Each lane has its own width, overlapping
  its neighbour by a tenth. Each stroke has its own length, advance, depth,
  swing, width and sideways shift.
- Each facet is a leaf-shaped scoop: narrow at entry and exit, deepest just
  after the strike, flat-bottomed across. The deeper cut wins where scoops
  overlap.
- **Measured** on the nuki's adzed faces: the strongest off-centre
  autocorrelation of the field, high-passed at 12 mm, fell from 0.69 and 0.66
  (v2.2's brick lattice: half a stroke along, one lane across) to 0.36 and
  0.30, at one stroke's length within its own lane.
- `test_naguri_has_no_brick_lattice` requires it below 0.45.

**The scan reference** (`scripts/art/timber_scan_reference.py` →
`data/timber_scan_reference.json`):

- Inputs: Poly Haven's `hinoki_planks` and `japanese_cedar_planks` diffuse
  maps, at their ledgered sizes of 1,890 and 1,130 mm, so 0.461 and
  0.276 mm/px.
- Measured on linear luminance, in 36 × 8 mm windows whose ring lines run
  within 12° of the grain, with plank seams kept out.

| | Hinoki (planed, flat-sawn) | Sugi |
| --- | --- | --- |
| Windows measured | 2,699 | 45 (mostly arched figure) |
| Apparent ring spacing p10 / p50 / p90 | 1.46 / 3.14 / 11.5 mm | 5.8 / 8.3 / 14.0 mm |
| Latewood share (below the p5–p95 midpoint), p50 | 0.37 | 0.32 |
| Ring contrast p95/p5, p50 | 1.33 | 1.38 |
| Earlywood / latewood mean luminance | 1.19 | 1.21 |
| Fibre band (0.92–1.5 mm) RMS over ring band (1.5–15 mm), p50 | 0.31 | 0.15 |
| Fibre band RMS over mean luminance, p50 | 2.0% | 1.3% |
| Earlywood, latewood (sRGB) | #a07e59, #97734f | #bd6f12, #b16209 |

How to read the table:

- **Spacing is on the face.** A flat-sawn face cuts rings obliquely, so
  apparent spacing runs wider than ring width. Hinoki's narrowest decile,
  1.46 mm, sits at the low end of the pilot's 1.4–2.4 mm rings.
- **The seam count is a count of dips.** Strong straight latewood lines and
  knot rows add false seams in hinoki, so its plank width is the p75–p90 seam
  spacing, 143–145 mm. Sugi's is 80 mm.
- **The fibre band is a lower bound,** because the JPEG softens it. The
  normal and roughness EXRs are DWA-compressed, which no host reader here
  decodes, so the study reads them in Blender.

**What this says about v2.2's materials, before any render:**

- **The rings are stronger than either scan's.** The masters' and the
  look-dev's EarlyColor and LateColor give a luminance ratio of 1.71. With
  the latewood weight at its mean, 0.8, it is about 1.5. Both fresh scans are
  at 1.19–1.21. That fits root's "broad brown bands".
- **The latewood band is narrower and harder.** v2.2 rises from earlywood to
  latewood over a tenth of a ring and gives the band 24% of it. The scans'
  latewood share is 0.32–0.37.
- **Fresh wood is an upper bound on contrast.** Age, soot and wiped urushi
  (which soaks the porous earlywood more) all lower ring contrast. So matching
  the fresh scans' contrast is a ceiling, not a target to tune toward.

**The focused patch study** (`scripts/art/render_timber_patch_study.py`; it
needs a Blender slot):

- **Members:** the wall column and the nuki, built and checked as the pilot
  builds them. Nothing is exported.
- **Patches:** orthographic, fronto-parallel views at the sugi scan's
  0.276 mm/px. The column's GrainClose region is 140 × 200 mm; the nuki's
  adzed face is 100 × 240 mm.
- **Views:**
  - clay under a sun 10° off the face, travelling across and along the grain;
  - the material under the same grazing sun, and under a soft sky with a key;
  - base colour as emission, at both scans' pitches, for measurement;
  - the shading normal (geometry and bump) in camera space.
- **Two materials:**
  - v2.3 as built;
  - `scan_contrast`, whose late colour moves toward the early colour by
    α = (1 − 1/r_t)/(1 − 1/r₀). Here r₀ is the measured v2.3 base-colour
    ratio and r_t the scans' mean, 1.20. The run measures what that achieves.
- **Measurements:**
  - the scan reference's statistics, on the rendered base colour;
  - across-grain slope band RMS, from the shading normals and from the scans'
    normal maps. Poly Haven's normal strength is a processing choice, so slope
    compares as an order of magnitude only.
- **Output:** one contact sheet per patch, every panel at the same physical
  size: the scans, both base colours, both materials under each light, and
  clay under each light. Plus `study.json`.

**Not done:** no Blender run, render, import or Unreal draw of v2.3. No
photoreal claim.

## v2.2: wood character (ran at `0d9a6ef`; rejected)

Root reviewed the 15 v2.1 originals. The crack is continuous, but five
surfaces still fail physical wood character. v2.2 corrects each with
sculpted and material form, using controlled, reference-based variation and
no more polygons: dense triangles drop from 2,442,978 to 2,439,030, and the
fallback stays at 146,412. Each fix is measured on the real members and
tested (`WoodCharacter`).

| Root's finding | v2.2 | Measured |
| --- | --- | --- |
| The nuki: "a repeated grid of rounded hammered dimples, not directional cut facets" | **Naguri** (`NAGURI`). Each chōna stroke is one facet: the blade's arc across the grain, and along it a chip deepest just after a steep entry, easing out in a long tail. Lanes overlap 24% across and strokes 35% along; the deepest cut wins, so there is no land and the facets meet at crisp ridges. Rows are staggered half a stroke, each swing turns up to 8°, and the facets are 1.2–2.6 mm deep in 3–4 cm lanes of 5–7 cm strokes | Correlation length 18 mm along the grain against 8 mm across; land under 2% inside the arris fade |
| The column dent: "still reads as a soft blister" | **A crushed groove** across the grain: a flat floor to 55% of the radius, a steep wall, up to a 25% tilt, and **no raised rim** (v2.1 had a Gaussian dish with one). The floor feeds the cavity mask: uncoated, rougher, darker | Floors flat (over 75% of their depth) within half the radius; no vertex raised |
| The nageshi: "fine uniform corrugation" | **Year-to-year rings.** Ring widths take three sines at 1.7, 2.9 and 4.3 rings, phased by the log's seed (`YEAR_WAVES`), with a peak slope of 0.65, so the phase stays monotonic. Each ring's relief follows that year's latewood strength (RingRandom, 0.55–1.45×, `YEAR_RELIEF`), so a darker ridge stands prouder; the fall after a ridge takes the next ring's depth, so there is no step | Nageshi ring widths CV 0.17, 1.15–2.43 mm (v2.1: 0.04, 1.63–1.96 mm); relief per ring CV 0.28 (v2.1: constant); no phase reversal |
| The koshi top: "repetitive parallel glossy ridges" | The **hand wear varies** along the rail. The finish is a **satin wiped urushi** (`FINISH_V22`: coat 0.55 at roughness 0.38, base 0.62), not v1's mirror coat (1.0 at 0.17) | Worn-top relief p95 varies along the rail (CV over 0.05) |
| The column GrainClose: "broad smooth color bands with little believable fiber break-up" | **Fibre break-up** in the material: fibre tone 0.22 (from 0.12) and streaks 0.16, fibre streaks through the latewood (×(0.85 + 0.30 Fibre.R)), and cavities rougher and uncoated | Look-dev and contract only. Its proof is a render |

The UV contract now carries the year-wave ring formula, the per-year relief
rule and the finish (`UV_CONTRACT["ring"]["year_waves"]`, `["year"]`,
`["finish"]`). Unreal needs a dedicated **PilotV22** master to match. The
namespace is `Local/ArtCache/NyaagyuDojoTimbersV22Pilot/`; the path guard
refuses run 1 and the v2.1 run.

**The run:** v2.2 ran once at `0d9a6ef` (Blender PID 96256, natural exit 0,
15 originals; `data/timber_pilot_v22_run1.json`). Its renders did not read as
wood: root's findings and the response are under v2.3 above. No Unreal import
or draw of v2.2. No photoreal claim.

## v2.1: what changes and how it is checked

`check_mesh` gains two gates, on every dense and fallback mesh.

**Unbroken grooves.**

- In every check, consecutive rows join their V-bottoms with an edge.
- Forks part only at **explicit Y-junctions** (`junctions()`). Each fork is
  recorded with its parent and the z where it leaves the parent's end.
- A junction's window is only the rows where both branches have their own
  samples and their V's overlap.
- A row pair touching the window may join the other branch's V-bottom
  instead, but must stay continuous, within 6 mm and 4 row pairs.
- Proximity alone exempts nothing.
- The six members need none of it: all V-bottoms join, at all six junctions.
- The tests show that v1's ladder fails the gate (300+ steps), and that a
  staircase can't hide inside a junction window.

**Rings where the log's are.** At every shown triangle's centroid, the
interpolated |UVLogQ| is compared with the frame `build()` stores there, in
rings.

| Zone | p99 limit | Max limit |
| --- | --- | --- |
| Close band (the grain zone) | 0.03 | 0.10 |
| Elsewhere | 0.2 | 0.4 |

Rows and samples come from the same criterion, `RING_TOL_*`. The tests show
that without the refinement the wall column fails the close limits (p99 0.055,
max 0.108).

**Both gates are sampled scope, not universal surface certification:**

- the joins gate tests each check's V-bottoms between the rows of its body
  (z0..z1);
- the ring gate tests one point per triangle (its centroid).

The material review (Unreal readback and originals) still has to show the
surface.

**The junction exception (review of `3a4aba6`).** A pair whose own V-bottoms
don't join may cross to the other branch only if **both** endpoints stay in
the groove:

- forward: the earlier V-bottom joins the other branch's in the later row;
- backward: the other branch's in the earlier row joins the later V-bottom.

Codex's counterexample was a five-row graph with only the forward edge, and
`3a4aba6` called it continuous. It now fails. The tests reproduce it
(`JunctionGate`), its mirror, a two-sided crossing that passes, and a break
4 mm from its fork, which stays a step.

**Triangles:**

| Member | v2 (run 1) dense | v2.1 dense | v2 fallback | v2.1 fallback |
| --- | --- | --- | --- | --- |
| Wall column | 454,612 | 547,268 | 44,918 | 45,696 |
| Open column | 1,088,942 | 1,271,458 | 54,970 | 67,048 |
| Nageshi | 338,460 | 338,226 | 9,746 | 9,746 |
| Cornice | 40,178 | 41,090 | 10,012 | 10,012 |
| Koshi | 125,590 | 146,728 | 6,836 | 6,836 |
| Nuki | 98,208 | 98,208 | 6,428 | 7,074 |
| **Total** | **2,145,990** | **2,442,978** | **132,910** | **146,412** |

## The v2.1 importer and material mapping (`sora_timber_v2.UV_CONTRACT`)

The manifest carries this contract.

**Unreal content path:** `/Game/Generated/Qualification/DojoTimberPilotV21`,
separate from the baseline and from run 1.

**Decode:** Interchange imports every channel as (U, 1 − V). Decode with
`flip_v` before reading the channels as data, and sample shared images
through `sample_blender`, as `import_nyaagyu_dojo_timbers.py` (`cd10643`) does.

| FBX channel | Blender layer | Payload | Unreal |
| --- | --- | --- | --- |
| 0 | UV0 | metric (s, z), m | `flip_v(TexCoord[0])` |
| 1 | UV1 | bake atlas | as imported |
| 2 | UVLogQ | signed log offset q · r_warp / r, with v2.1's periodic wobble and the knots' swirl; continuous across knot edges | `flip_v(TexCoord[2])` |
| 3 | UVLogZ | (z, seed01) | `seed = 1 − TexCoord[3].g` |
| 4 | **UVKnot** | (r_k: knot ring radius in ring units, 0.55 mm rings; d: signed distance from the knot edge in knot radii, clamped to [−1, 1]). Fallbacks carry (0, 1) | `r_k = TexCoord[4].r`, `d = 1 − TexCoord[4].g` |

**The ring formula:**

- `r = (d < 0 ? r_k : length(UVLogQ)) + (Fibre.G(UV0 / 0.25) − 0.5) · 0.00025`;
- `phase = r / w + (RingNoise.R(nu, nv) − 0.5) · 2.6`, where
  `nu = r / (300 w) + seed · 37` and `nv = frac(seed · 7.31)`;
- the d select is per pixel, anti-aliased:
  `inside = saturate(0.5 − d / max(fwidth(d), 1e-6))`.

`material_phase()` is its numpy reference. On the stored channels it gives
exactly the phase the raised grain is cut from, and inside knots the knot's
own rings. The Blender look-dev implements it.

**Samplers:**

| Texture | Sampler | Note |
| --- | --- | --- |
| Fibre | Masks | linear RGB |
| RingNoise | LinearGrayscale | 16-bit, bilinear |
| RingRandom | LinearGrayscale | nearest |
| Fallback NormalDX | Normal | |
| Fallback Masks | Masks | knot weight from the sample's alpha output, not from RGB |

The baseline master's ring model does not apply to v2.1 assets.

**What the Unreal side still needs (not implemented yet):**

- **A dedicated PilotV21 timber master,** and fallback master, in that content
  path. It decodes UV4 and applies this ring formula. Never the baseline
  `timber_master`.
- **A readback after import,** before any material review:
  - each mesh's UV channel count (5);
  - the decoded UV0, UVLogQ, seed and UVKnot at known source vertices, to
    1e-6 against the FBX;
  - the material's resolved parent and sampler types.

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

- every check holds 17 samples across, with constant topology, and (v2.1)
  joins its V-bottoms in every row pair, forks included;
- dents reach 81–100% of their depth;
- the grain recess at p95 is 48–54 µm on the columns, 41 µm on the nageshi and
  0.12 mm on the koshi top. These are the face's range times v2.2's per-year
  0.55–1.45; v2.1 was 42–43 µm, 32 µm and 0.12 mm. The phase from the stored
  UVs is exact;
- adze depth is 2.2 mm at p50.

Steep relief, such as a dent wall or an adze crease, is counted but allowed.

`scripts/art/test_sora_timber_v2.py` has 20 tests, passing on numpy 2.3 and
1.23. Besides the above, they cover every defect reproduced on the way:

- a hole, a flipped triangle, a fold and a crossing;
- misaligned grain UVs;
- an adze that ignores the arris;
- v1's wander reversing more than 100 times on the face;
- the frozen kit's inputs unchanged;
- the namespace guard, which refuses run 1 too.

The v2.1 tests:

- **The staircase:** v1's ladder fails the gate, and a staircase can't hide in
  a junction window.
- **Junctions:** explicit, bounded and continuous, one per fork, at the
  parent's end, nothing by proximity.
- **Ring beading:** caught without the refinement.
- **The wobble seam:** a jump of more than 1 ring in v1's form, none in
  v2.1's.
- **UVKnot:** d < 0 exactly inside knots, and UVLogQ has no swap.
- **The material reference:** it reproduces the ridges' phase, and the knot
  rings.
- **The UV contract:** every channel, in export order.

**Visibility** on the room face (the koshi's top): the p95 tilt, and the
shading change that tilt makes under raking light at 30°.

| Surface | Shading change |
| --- | --- |
| Plain planed | 0.0–1.3% |
| Raised grain, columns | 8.1–8.5% |
| Raised grain, nageshi | 14.7% |
| Koshi worn top | 54.7% |
| Adze | 74.4% |
| Dents | 19–72% |
| Knots | 14–37% |

v1's planed faces were 1.2–1.4% even at a 10° graze.

## The bounded pilot run (needs your Blender slot)

```bash
/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python-exit-code 1 --python scripts/art/create_nyaagyu_dojo_timbers_pilot.py -- --cpu --samples 96 --bake-res 2048
```

v2.1 writes only `Local/ArtCache/NyaagyuDojoTimbersV21Pilot/`. It refuses a
namespace that already holds a run. The path guard refuses the frozen kit,
its cache and run 1.

The run-1 sizes:

- 332.8 MB of dense FBX, 155 bytes per triangle. v2.1 would be about 380 MB.
- about 11 minutes.

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
Afterwards, `-- --cpu --verify [--archive-receipt …] [--accept-generator SHA]`
only reads the run.

- **What it does:** it rebuilds the members and compares the digests, checks,
  FBX SHA, Shared textures and inputs with the run's own evidence.
- **Its verdict** is `GEOMETRY_INPUTS_VERIFIED`: geometry and inputs only. It
  is not a re-export, re-bake or re-render; FBX bytes, baked maps and renders
  are checked as the original files.
- **A changed generator** fails as `INPUTS_CHANGED`, unless its exact current
  SHA is pinned. For run 1 that is the verify-only driver of `82869a4`
  against the `0c8809f` generator that made it. The receipt keeps the
  original hash, the pin and the acceptance.
- **Its only output** is a new receipt under `Local/ArtCache/Verification/`.

**After the run (your lane):**

- import into an isolated `/Game/Generated/Qualification/DojoTimberPilotV2`,
  with Nanite resource counts and cooked bytes per triangle;
- the V-flip and v2-wander material corrections;
- SM6 close originals (clay and material) and the SM5 fallback, against the
  Blender originals.

## Not done, not claimed

- v2.1: no Blender run, bake, render, Unreal import, Nanite or GPU measurement.
- Run 1 is rendered only in Blender and is not accepted.
- No photoreal acceptance.
- No coverage beyond these six members.
- The Unreal material corrections are root's, in `timber_master`.
- Root's capture inventory needs the pilot namespace added.
