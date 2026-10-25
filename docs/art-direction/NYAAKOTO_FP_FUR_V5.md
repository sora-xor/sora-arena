# The first-person paw's fur, v5: the coat's colour and volume, each clump's taper, the sleeve's cloth

**Status (2026-10-25):** source and CPU measurements, made under root's
second bounded fur and kote lane. Capture v6 (`Saved/YumiFP/v6_fur`) will
show how it renders. It is a candidate: not art acceptance, an admission or
a photoreal claim.

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

## The run and the capture

To follow, one job at a time: the Blender build, the ledgers, the Unreal
import with its normal readback, the fresh-editor material check, then
capture v6. Capture v6 is matched to v5: right_cheek_clear and paw, 1920 x
1080, runup=auto, IDs.

**The comparison with v5** waits for the comparator's fix (root's review of
`--assets`).

**What it can show:** the colour, occlusion, taper, fringes, curl and sleeve
all change together. So like v5, it can compare the two versions, and it
cannot split the change among them.
