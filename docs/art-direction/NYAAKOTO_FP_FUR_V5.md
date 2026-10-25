# The first-person paw's fur, v5: the coat's colour and volume, each clump's taper, the sleeve's cloth

**Status (2026-10-25):** source, rebuilt assets and capture v6
(`Saved/YumiFP/v6_fur`), made under root's second bounded fur and kote lane.
It is a candidate: not art acceptance, an admission or a photoreal claim.

**Result, qualified:** two asset versions, one capture each, with the
colour, occlusion, taper, fringes, curl and sleeve all changed together.
- **The sleeve** visibly puffs between its cords, with irregular folds.
- **The fur barely changes.** The close-up's gaps read grey-brown rather
  than pale, and its form contrast rose by about 15 %. The eye view stays a
  flat bright white, and the angular patchwork of cards remains.
- **The high-frequency residual rose** by 10-18 %. That measure cannot tell
  speckle from the variation added on purpose.
- Details below.

## What v5 answers

Root's review of capture v5 (fur v4 assets, `Saved/YumiFP/v5_fur`):
- right_cheek_clear's paw is "flat bright white";
- the close-up shows "angular overlapping strips and pale gaps";
- the wrist reads "brush-like";
- the sleeve is "smooth" (in Blender, "glossy").

Root's direction: coherent fur volume and each clump's taper, over another
numerical win.

**What the coat is.** Its strands lie 0.2 to 1.2 mm off the skin: median tip
0.26 mm, 90th percentile 1.2 mm. It is a thin sheet, so it lights like the
surface under it. Earlier reviews pushed the lift down to stop spikes (v1 to
v3), so v5 keeps the lift. Its volume comes from shading the paw's form, and
from each clump's shape.

## The changes

**The coat's colour** (`nyaakoto_fp_paws.TABBY`):
- **The hero's white.** The hero fur texture
  (`T_Nyaakoto_fur_white_Albedo`) averages (0.692, 0.646, 0.574) linear. The
  fur atlas's coverage-weighted mean hair value is 0.933. So TABBY white is
  (0.742, 0.693, 0.617), and a card's mean colour is the hero's body fur.
  v4's (0.86, 0.85, 0.82) made the cards about 0.80, brighter and cooler.
- **Form occlusion** (`form_occlusion`): Quilez's distance-field ambient
  occlusion over the paw with the grip.
  - The steps along the normal are 3, 6, 12 and 24 mm, with falloff 0.6.
  - It is baked into every card point's vertex colour and the skin's, on a
    floor of 0.45.
  - On the coarse test mesh: closed against the leather (mean below 0.5
    within 2 mm of the grip), open away from it (above 0.9 beyond 15 mm).
    The cards' median is 0.96, and 24 % of card points fall below 0.8.
- **The undercoat:** the skin is the coat's bottom, at 0.72 of the coat's
  colour (TABBY undercoat), so it sits darker than the cards above it rather
  than reading as pale gaps. The skin material's own 0.82 multiplies it
  again, about 0.59 in all.

**Each clump's shape:**
- **Taper** (`FUR` tip_width 0.20, taper_power 1.3): a card narrows to 20 %
  of its root's width (v4: 55 %), so a clump ends in a point rather than a
  strip.
- **Curl** (`FUR` curl_deg): each strand turns in the skin's plane toward its
  tip, by 16° (one standard deviation) in the wrist's ruff and 5° elsewhere,
  so the ruff stops reading as a brush.
  - It is drawn from its own seeded stream.
  - Lift, density, lengths and every other random draw are v4's. One card of
    20,269 is lost to the bow on the coarse mesh, because its curled strand
    meets it.
- **The atlas** (`create_nyaakoto_fp_fur_textures.py`, v5):
  - fringe hairs irregular in length (62 % to 100 % of the strand's longest),
    place (jittered 40 % of their spacing) and width (0.75 to 1.5 times);
  - each tile's lateral edges fade over 4 % of its width.
  - Its dither measure is about v4's: dithered 45-47 % in the eye view and
    39 % in the close-up, speckle variance 0.062-0.065 and 0.061 (v4:
    0.069-0.071 and 0.060).

**The sleeve** (`nyaakoto_fp_kote.py`, and the silk in both builds):
- **A second fold family:** 5 lobes, 0.8 mm, its own twist, ripple and slow
  swell, over the regular 9-lobed one.
- **Puff:** the cloth swells up to 1.2 mm between its cord bindings. It is
  tight at each cord, eases up past the last one toward the elbow, and stays
  flat under the splints, which hold it.
- **Material:** roughness 1.15 → 1.35 times the map. The weave's normal is
  1.2 in Blender (from 0.8); in Unreal its tangent-space x and y are scaled
  by 1.5 and renormalised.

**Unchanged:** lift, density, card lengths and widths, the shading normals'
bend, the fronts, the material graphs other than the silk, holds, cameras
and exposure.

## Tests, and two baselines that changed

`test_nyaakoto_fp_paws` (23) and `test_nyaakoto_fp_fur_textures` (8). New:
- cards narrow to their tips;
- form occlusion darkens where the paw closes;
- the skin sits below the coat;
- the cloth puffs between cords and not under the splints;
- the coat's white is the hero's;
- each card's lateral edges fade.

**Two failed on their first run** (kept:
`Saved/W18Rebuild/s26_test_failures_before_baseline_change.txt`):
- **v4's tile-coverage test** (0.908 against > 0.97). v5's edge fade lowers
  it on purpose. Inside the faded edges the tile is 0.984 covered, so the
  test now measures there.
- **The new taper test's maximum** (0.25 against 0.205). 4 of 20,268 cards
  have narrower roots, whose edges slid back off the bow (0.24 to 0.85 mm
  from the grip). It now requires the median at tip_width, fewer than 0.1 %
  wider, and each wider card within 1 mm of the grip.

## The run (2026-10-25, root's lane, returned at 21:26 UTC)

Each command, PID, log and exit is in `Saved/W18Rebuild/s26-s30*` and the
mailbox note of 21:26 UTC.

1. **Atlas v5:** byte-identical to the reviewed draft. v4 is archived, and
   the ledger rewritten.
2. **Blender:** exit 0.
   - Counts as v4's: 404,012 triangles, 20,292 cards.
   - Occlusion median 0.966, with 23.6 % of card points below 0.8.
   - FBX card normals 8.449°, against 8.351° built.
   - The kote clears the grip by 51.26 mm.
   - Signed bc2d1d4; v4's production files are archived.
3. **The Unreal import:** editor 0, wrapper 0. The fur corners read back
   8.49° off their faces. It wrote `readback_v5.json` exclusively; the
   importer's `out=` is new (c928d90).
4. **The fresh-editor material check:** no problems
   (`material_check_v5.json`).
5. **Capture v6:** matched to v5 (right_cheek_clear and paw, 1920 x 1080,
   runup=auto, IDs). Editor 0, wrapper 0; it exited by itself 3 s after its
   marker. Cameras, exposure and gates are v5's.

## Capture v6 against v5

The comparison uses `fur_capture_noise --assets`, fixed in a036f59 to root's
review, whose probes it now refuses. It passed its setup checks.

**The reticle:** right_cheek_clear's ID pass still shows no bow, arrow or
paw pixel in the 0.12 disc.

**The fur's high-frequency residual** (`Saved/W18Rebuild/s32_fur_assets_v5_v6.json`):

| hold | fur pixels, v5 / v6 | own residual, v5 / v6 | common-region residual, v5 / v6 | fur / bow |
| --- | --- | --- | --- | --- |
| right_cheek_clear | 7,630 / 7,541 | 0.0133 / 0.0157 | 0.0132 / 0.0156 (+18 %) | 2.5x / 2.9x |
| paw | 279,556 / 274,438 | 0.0092 / 0.0098 | 0.0089 / 0.0098 (+10 %) | - |

The residual rose. The occlusion, the colour's variation, the soft card
edges and the irregular fringes all add high-frequency content on purpose,
and this measure cannot separate that from speckle. It is not a speckle win.

**The coat's form** (`s32_fur_form_v5_v6.json`, `s32_fur_form_v5_v6_eyeview.json`;
over the union of both runs' fur selections):

| hold | mean luminance, v5 / v6 | form contrast (15 px), v5 / v6 | p10 luminance, v5 / v6 |
| --- | --- | --- | --- |
| right_cheek_clear | 0.814 / 0.799 | 0.070 / 0.072 | 0.754 / 0.728 |
| paw | 0.823 / 0.807 | 0.052 / 0.059 | 0.753 / 0.711 |

The hero's white is 14 % less albedo than v4's. The display moves only
about 2 %, because a white in this sun at EV100 12.97 sits near the tone
curve's shoulder.

**What the originals show:**
- **The sleeve:** it puffs between its cord bindings, and its folds are
  irregular. It reads more as gathered cloth than v5's even ridges. This is
  the clearest gain.
- **The close-up:** the same patchwork of flat, angular card shapes. The
  gaps between them are grey-brown rather than pale. The cards' taper does
  not show, because what reads as angular are the gaps between overlapping
  cards, not their tips.
- **The eye view:** a flat bright white, about as v5.

## What it suggests, for a later lane

These are candidates, not started.
- **The fur material's transmission:** two-sided foliage passes light
  through each card (its subsurface colour 0.9, 0.82, 0.74 of the base),
  which flattens the form in sun. Try less of it, or the Hair shading model
  for anisotropic sheen.
- **An undercoat that is fur:** the gaps show the skin, lit as a flat
  surface. A shell layer of the coat's texture under the cards would put fur
  in every gap.
- **Smaller, denser cards:** the patchwork's scale is the cards'. At the
  close-up they are 8 to 13 px wide; smaller ones would put it below what
  reads.
- **Exposure:** the coat sits near the tone curve's shoulder. That is set
  by the scene's sun and exposure, which this pass kept as v5's.
