# Dojo timber relief, checks and triangle budget: proposal

**Status:** proposal for root review. Nothing is rebuilt: the frozen slice
`6b0e93e` (87 LFS binaries, 8.4 GB cache) and its manifests, ledger and
binding stay as they are until its import. The two references are
unavailable, so the look below is **original art direction**, not a reference
match. Every number comes from `scripts/art/timber_density_study.py`
(numpy only, no Blender), saved in `data/timber_density_study.json`.

## What root and I saw in the originals

- **Broad faces are extremely flat.**
- **The grain reads as uniform parallel lines or big simple curves.**
- **The checks look cut, not split.** On the SM5 fallback their edges step.
- **The golden-hour rig washes the relief out.**

Root's requirement stands: real unique geometry, with the finish judged in
the actual game.

## Measurements of today's logs

The study rebuilds the logs from copies of the generators' recipes. The
copies reproduce the committed triangle counts exactly: 470,624 and 836,068
for a wall and an open column; 106,320, 114,012, 68,280 and 63,976 for the
four rail kinds.

**Relief.** Triangle tilt from the room face, and the shading change it
makes under raking light, roughly tilt × cot(grazing angle):

| Room-face triangles | Share | Tilt p50 / p95 | Shading change at p95, 10° graze |
| --- | --- | --- | --- |
| Plain planed surface | 94–95% | 0.035–0.046° / 0.12–0.14° | **1.2–1.4%: invisible** |
| Dents | 0.8–1.7% | 0.5–0.6° / 3.8–4.8° | 38–48% |
| Knots | ≤ 0.03% | up to 18° | — |
| Checks | 4.4% | walls at about 89° | they render as dark lines |

**Why the faces are flat:**

- **Kanna strokes** are 12 µm pass offsets plus a 16 µm hollow across each
  6 cm lane. That is right for a fine plane, but geometry sampled every 5 mm
  can't show it. The 0.836M-triangle log buys almost nothing on its broad
  faces.
- **Dents:** 57% are narrower than 5 mm across, and 18% narrower than
  2.5 mm, so the 5 mm grid aliases or drops them. All of them are also long
  *along* the grain, while a bokken strike crushes a short line *across* it.
- **Checks** taper smoothly (sin^0.55), keep one V profile, and wiggle
  gently (0.9 mm over 0.37 m) between parallel lips eased by 40 µm. That reads
  as a kerf.

**The fallback's stair-step.** The ladder stitch joins rows by perimeter
order. As a check drifts across the fixed base grid, base samples move in and
out of its zone, and the stitch skews triangles across the check.

| Samples across a check, row to row | Count | Rows where it changes |
| --- | --- | --- |
| Today's dense logs | 13–21 | 15–52% |
| Today's SM5 fallback | 12–20 | 5–20% |
| Fallback with the zone kept clear (below) | always 17 | **0%**, at the same sample count (±3%) |

## Proposal

### Geometry (Nanite logs; checks also on the SM5 fallback)

1. **Checks that split, not cut.**
   - The path keeps the spiral-grain drift and gains a meander: 0.5–2 mm,
     correlated over 4–12 cm. It bends round or stops at a knot within 3 cm.
   - The opening varies by ±45% over 2–8 cm. Checks over 0.6 m get 1–3
     bridges where the fibres still hold.
   - The ends run on as a 0.05–0.1 mm hairline for 2–6 cm, and 30% of them
     fork.
   - In section, the V is asymmetric (one wall 1.3–1.8× steeper), with depth
     at 8–25× the local opening.
   - The lips are torn: ±20–80 µm along them, with 0–3 splinters per 30 cm,
     each 0.3–0.8 mm wide, 5–20 mm long and 0.05–0.15 mm proud.
   - Sampling: 17 samples across, a half-width floor of 0.16 mm and the base
     grid kept out of the zone, which the study shows gives zero topology
     changes. Rows run every 8 mm along the body and every 2 mm at the ends,
     bridges and splinters.
2. **Bokken dents across the grain.** Each is 6–22 mm across, 1.5–7 mm
   along and 0.15–0.9 mm deep, with a 10–30 µm crushed rim. They concentrate
   at 0.9–1.7 m on the room-facing faces, plus handling dings at 0.3–2.0 m.
   They're sampled locally at 1.5 mm, so all of them resolve.
3. **Knots:** as now, plus the check interaction above, and more small pin
   knots on the sugi members.
4. **Arrises:** wear as now, at 6 samples per corner instead of 10. Each
   chord then spans 15° of the round-over, a sag of 0.02 mm on a 2.5 mm
   radius.
5. **Low-frequency form:** keep the bow, and add a 1–3 mm drying twist over
   7 m for the silhouettes.

### Material (both paths, no triangles)

Each placement already has its own material instance; a per-instance
parameter carries its ring width today.

1. **Kanna lanes and chatter.**
   - New per-instance parameters: lane width, offset and seed (the same
     values the generator uses).
   - The material then draws 15–35 µm lane-edge ridges, 1–2 mm wide, and
     5–15 µm chatter at 3–6 mm pitch where each pass starts.
   - These read in the semi-gloss fuki-urushi specular, the way planed
     timber really does. They are too fine for geometry.
2. **Raised latewood:** the existing ring-ridge bump, stronger where worn
   or weathered (the koshi top, the floor, engawa-facing columns), driven by
   the wear mask.
3. **Polish and grime:**
   - the G mask lowers roughness and darkens a band at handling height, and
     shows rub-through on the arrises;
   - the B mask shows soot streaks on the upper columns;
   - the R mask darkens check lips, where urushi collects.

   All three masks already exist; they need a visible response.
4. **Optional, root to evaluate:** Nanite Tessellation displacement for
   sub-millimetre raised grain. UE 5.8 Mac SM6 support and its cost are
   unknown, so it is not part of the plan.

### Sampling and budget

The proposed sampling, as the study models it:

- base rows every 4 cm and a 2 cm base grid on plain faces;
- fine rows and columns only around checks, knots and dents;
- feature rows are local (only their own face gets dense samples), while
  corners keep every sample in every row, so arris highlights never facet;
- every check zone kept clear.

Chapter-1 hall, Nanite source triangles:

| Sampling | Columns (65) | Rails (235) | Hall | vs today |
| --- | --- | --- | --- | --- |
| Committed (5 mm everywhere) | 35,898,400 | 21,211,910 | **57,110,310** | — |
| F: checks 8 mm / 2 mm ends, dents and knots 1.5 mm | 16,370,420 | 5,976,818 | 22,347,238 | 2.6× fewer |
| **G: F with 6 arris samples (recommended)** | 13,777,396 | 4,851,442 | **18,628,838** | 3.1× fewer |
| C: checks 15 mm / 3 mm ends | 12,670,846 | 5,235,284 | 17,906,130 | 3.2× fewer |

Per member under G:

- a wall column falls from 470,624 to 169,498 triangles, an open column from
  836,068 to 204,358;
- rails fall from 64–114k to 24–32k.

These counts already include the new check, dent and knot refinement. The
cache should shrink about in proportion, from 8.4 GB to about 2.7 GB
(estimated). Nanite's cooked bytes per triangle, streaming memory and GPU
time are unmeasured on Mac; the pilot below measures them.

## Order of work (each step waits for a coordinated slot)

1. **Source.** Implement the above in `sora_timber_lib.py` behind a new
   digest version, `sora-timber-geometry-v2`. The current lib and manifests
   stay byte-identical until the pilot is accepted. Tests extend
   `test_timber_density_study.py`.
2. **Pilot (Blender CPU, about 20 min).**
   - Rebuild 2 columns and 4 rails, plus their pool members.
   - Look-dev renders: today's rigs, plus close-ups of a check, a dent and an
     arris highlight, and a fallback close-up for the stair-step.
   - Root imports the pilot and measures Nanite bytes per triangle, import
     time and actual draw.
3. **Chapter 1 (about 1 h CPU).** Rebuild and verify, then a new binary
   commit with its OWN ledger replacing the frozen pool files, then a rebind.
   Root imports and captures SM6 and SM5.
4. **The other three halls,** at the measured budget.

Not done, and not claimed: any rebuild, render, import, Nanite or GPU
measurement, or photoreal acceptance.
