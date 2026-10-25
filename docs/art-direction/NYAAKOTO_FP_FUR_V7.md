# The first-person paw's fur, v7: the white mitt, a smooth coat height, and clumped strands

**Status (2026-10-25):** source and CPU checks, under root's bounded lane
for the v8 capture (its handbacks of 22:05 and 22:44 UTC). The build,
import, material check, cost check and capture v8 follow below once run.
This is a candidate: not art acceptance, an admission, a performance
acceptance or a photoreal claim.

## What capture v7 showed

**Root's review of v7** (`248f412b…`):
- the flakes and gaps are gone, and the macro pile and silhouette improved;
- but the eye view "still reads as a white glove with broad grey wrist
  contours";
- the coat is felt-like;
- the 1,781-instruction shell material over ten translucent layers "needs
  measured performance before acceptance".

## The contours: mostly colour, partly height (measured)

`Saved/W18Rebuild/s39_v7_bands` holds the scripts, sheets and logs. The v6
doc's guess, that the lines lay where the shells end, was wrong.

**The method:**
- the committed shell build was projected into both v7 views on the CPU,
  z-buffered over the skin, the kote and the bow;
- in the eye view the projection registers at zero shift (silhouette IoU
  0.975). The raster's own check against v7's ID pass gives the paw 0.951.

**The tabby's stripes:**
- **The shapes match.** The capture's lines are the tabby's dark stripes
  where they fade into the white mitt, including one isolated dark spot by
  the knuckle.
- **The cause is the mitt's fade.** The old mitt (`TABBY`) starts 10 mm
  behind the knuckles and fades over 12 mm, with a 7 mm wobble. So 43 % of
  the shells' furred vertices sat in the fade, and 17 % carried a visible
  stripe.
- **They were in v6 too.** Band-passed luminance correlates between v6
  (cards) and v7 (shells), over the same colours, poses and cameras:

  | band (Gaussian sigmas) | eye view | close-up |
  | --- | --- | --- |
  | 3-15 px | +0.618 | not measured |
  | 8-40 px | +0.774 | +0.419 |

  v6's card speckle had hidden the stripes. The shells exposed them.

**The coat's height, a smaller share:**
- The height stepped hard between regions: ruff 3.0, dorsal 1.8, digits 1.2,
  dewclaw 1.0 mm.
- In the eye view's 3-15 px band:

  | field | R², v7 | R², v6 |
  | --- | --- | --- |
  | the height field alone | 0.211 | 0.088 |
  | the stripe field alone | 0.154 | 0.189 |

  The height field explains more of v7's band-passed luminance than of v6's.
  So the shells add this feature.

**Not found:** lines where the shells end at the furred region's border.

**The reference:** the hero's bow hand is white-grey; the tabby markings
are on the head, body and tail (`Nyaakoto_Photoreal_Target.png`).

## The felt: strands too fine for either footprint

v1's strand texture spaced strands 0.18 mm apart on a 4 mm tile. After the
paw's 0.75 scale, the eye view's pixel spans 0.44 mm of the world and the
close-up's 0.08 mm. The mips therefore average each layer to its mean
coverage, and ten uniform layers composite to a uniform pile.

`composite_measure` (in `create_nyaakoto_fp_shell_texture.py`) is a CPU
model of the shader's composite:
- the ten shells' heights, tents and 0.95;
- each layer read at the view's footprint, as its mip;
- each layer displaced along the flow by its height x tan(50°);
- the layers composited bottom to top.

On it, v1's texture under v6's shells varies in luminance by a coefficient of
0.015 in the eye view and 0.044 in the close-up.

## The changes

**The white mitt** (`nyaakoto_fp_paws.MITT`):
- the white runs 12 mm under the kote's cuff, and fades over 6 mm there;
- so every furred point that can show is white, which a test checks;
- the skin under the shells takes the same mitt;
- the fur cards keep v5's mitt, so `FUR_MODE = "cards"` still builds v5.

**The coat's height** (`SHELLS["height_smooth"]`):
- the regions' heights are diffused over the shells' skin, sigma about
  4.4 mm (30 steps at lam 0.5 on its 1.6 mm edges), then clamped clear of
  the bow as before;
- where the clamp leaves two neighbouring vertices alone, the height now
  changes by at most 0.34 mm between them, where the ruff meets the dewclaw.
  Unsmoothed, it steps by 1.2-2.0 mm.
- The regions' plateaus keep their heights.

**Clumped strands** (`create_nyaakoto_fp_shell_texture.py` v2):
- **The structure:** v1's 1,975 strands per tile are now gathered into 44
  clumps, 1.2 mm apart, on an 8 mm tile. Each strand belongs to its nearest
  clump centre, and is drawn toward it with height, by a convergence of
  0.7-0.9 per clump. So clumps taper to tips, and partings open between them.
- **The lengths:**
  - clumps run 0.75-1.25 of the coat's height, longer on a tileable tuft
    field a few millimetres across;
  - strands run 0.8-1.0 of their clump's length;
  - the tallest pass the top shell, so every shell draws some tips. A draft
    at 0.55-1.0 left the top shell empty: ten layers of overdraw for nine
    layers of coat.
- **The coverage** at the four heights is 0.718 / 0.433 / 0.195 / 0.025
  (v1: 0.742 / 0.383 / 0.107 / 0.007).
- **A tint map:** each strand's brightness (linear, 512 x 512, mean 0.915),
  darker in the tuft field's troughs, per clump and per strand. The shell
  material multiplies the vertex colour by it, in both builds.
- **On the composite model:** luminance varies by 0.050 in the eye view and
  0.094 in the close-up, against v1's 0.015 and 0.044.
- **Attempts kept:** two drafts were superseded before any use, the empty top
  shell and tint seams where no strand reached
  (`s40_shell_texture_v2.attempt*`). v6's texture is archived at
  `Saved/NyaakotoFPPaws/Archive/v6_furshells`.

**The white** (`shell_white_gain`):
- v6's ten layers composited to 0.76 of TABBY white, the grey glove;
- the shells' colour is now scaled so their far-field composite over the
  skin is the hero's white: 0.933 of TABBY white, as the cards' was in v5;
- with v2's maps the gain is 1.240, and the brightest shell colour stays
  under 1;
- the deep shade is a little weaker (0.55 → 0.62), now that partings show
  the deeper layers.

**Unchanged:**
- the shells' count, spacing, comb and clearance;
- the skin, pads, kote, slots, holds, cameras and exposure.

## The cost check

**`scripts/unreal/measure_fp_fur_cost.py`** runs in the engine, in the
capture's own scene (it imports `render_yumi_fp_review.py`, whose `main()`
now runs only as `__main__`, as `-ExecutePythonScript` runs it):
- **The material statistics:** for every paw material, and for transient
  copies of the shell material under the other translucency lighting modes.
- **The GPU time:** per hold, in three states:
  - the shells as built;
  - the shells drawn by a clear unlit material, so they rasterise and blend
    but are not shaded;
  - the paw hidden.

  Each state is timed by the CSV profiler with `r.GPUCsvStatsEnabled`, at
  the editor viewport's own size, which is recorded.

**The importer** now reads back every material statistic the engine
reports.

**`scripts/art/fp_fur_overdraw.py`** counts on the CPU the shells'
front-facing fragments that pass the opaque depth. At v7's poses, with this
source:

| hold | fragments | pixels with shells | mean layers | most layers |
| --- | --- | --- | --- | --- |
| right_cheek_clear | 89,609 | 9,366 | 9.57 | 23 |
| paw | 2,911,762 | 303,986 | 9.58 | 23 |

## On the CPU

The tests:
- `test_nyaakoto_fp_shell_texture` (7), for the maps:
  - they are their manifest's, and tile;
  - coverage falls with height, and every shell has some;
  - the strand and clump counts;
  - strands gather near clump centres;
  - the tint's spread;
  - the far field and the measure, recomputed.
- `test_nyaakoto_fp_paws` (32), with three new tests:
  - every shell is the white mitt;
  - the height changes smoothly, but steps without the smoothing;
  - the far field is the hero's white.
- `test_fp_fur_overdraw` (4) and `test_measure_fp_fur_cost` (3), both new.
