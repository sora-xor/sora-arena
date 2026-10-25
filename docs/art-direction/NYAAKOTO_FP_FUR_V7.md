# The first-person paw's fur, v7: the white mitt, a smooth coat height, and clumped strands

**Status (2026-10-25):** source, rebuilt assets, a GPU cost check and capture
v8 (`Saved/YumiFP/v8_fur`), under root's bounded lane for the v8 capture.
The lane was returned at 23:15 UTC. This is a candidate: not art
acceptance, an admission, a performance acceptance or a photoreal claim.

**Result, qualified** (two asset versions, one capture each):
- **The contours are gone** in both views, as are the tabby's stripes.
- **The coat is brighter:** mean luminance 0.719 → 0.759 in the eye view and
  0.662 → 0.709 in the close-up.
- **The close-up** now shows a clumped coat lying along the flow, where v7's
  was felt. Its clumps can read as feathery or scaled.
- **The eye view** is cleaner but still reads mostly smooth at its scale.
- **No speckle came back:** the high-frequency residual fell further.
- Details below.

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

**Clumped strands** (`create_nyaakoto_fp_shell_texture.py` v3; v2 was its
first draft, below):
- **The structure:** v1's 1,975 strands per tile are now gathered into 44
  clumps, 1.2 mm apart on average, on an 8 mm tile. The clumps are laid out
  loosely (dart throwing at 0.5 of their spacing), so they differ in size.
  Each strand belongs to its nearest clump centre, and is drawn toward it
  with height, by a convergence of 0.45-0.8 per clump. So clumps taper to
  tips, and partings open between them.
- **The lengths:**
  - clumps run 0.75-1.25 of the coat's height, longer on a tileable tuft
    field a few millimetres across;
  - strands run 0.8-1.0 of their clump's length;
  - the tallest pass the top shell, so every shell draws some tips. A draft
    at 0.55-1.0 left the top shell empty: ten layers of overdraw for nine
    layers of coat.
- **The coverage** at the four heights is 0.733 / 0.466 / 0.215 / 0.025
  (v1: 0.742 / 0.383 / 0.107 / 0.007).
- **A tint map:** each strand's brightness (linear, 512 x 512, mean 0.909),
  darker in the tuft field's troughs (0.12), per clump (0.03) and per strand
  (0.03). The shell material multiplies the vertex colour by it, in both
  builds.
- **On the composite model:** luminance varies by 0.053 in the eye view and
  0.082 in the close-up, against v1's 0.015 and 0.044.
- **v2, the first draft, and why it changed:**
  - It was signed in 1f18f3ab and built once in Blender: 22:49:13-22:51:30
    UTC, exit 0 (`s41_paw_v7.attempt0_regular_grain.*`;
    `Saved/NyaakotoFPPaws/Archive/v7_attempt0_production`).
  - Its Cycles reviews showed the stripes gone at every distance.
  - But its clumps read as a regular knit or terry grain: even sizes in rows,
    each one outlined. v2's clumps were laid out tighter (0.8 of their
    spacing) and converged more (0.7-0.9), with more tint per clump (0.05).
  - On the composite model it varied by 0.050 / 0.094.
- **Attempts kept:** two drafts of v2 were superseded before any use, the
  empty top shell and tint seams where no strand reached
  (`s40_shell_texture_v2.attempt*`). v6's texture is archived at
  `Saved/NyaakotoFPPaws/Archive/v6_furshells`.

**The white** (`shell_white_gain`):
- v6's ten layers composited to 0.76 of TABBY white, the grey glove;
- the shells' colour is now scaled so their far-field composite over the
  skin is the hero's white: 0.933 of TABBY white, as the cards' was in v5;
- with v3's maps the gain is 1.237, and the brightest shell colour stays
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
source (d65d96e2; `Saved/W18Rebuild/s45_overdraw_v7_poses_d65d96e2.json`):

| hold | fragments | pixels with shells | mean layers | most layers |
| --- | --- | --- | --- | --- |
| right_cheek_clear | 89,514 | 9,371 | 9.55 | 23 |
| paw | 2,908,447 | 303,865 | 9.57 | 23 |

The most layers, 23, is where one digit's shells overlie another's.

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

## The run (2026-10-25)

Each command, PID, log and exit is in `Saved/W18Rebuild/s41-s51*` and the
mailbox note of 23:15 UTC.

| step | when (UTC) | exits | record |
| --- | --- | --- | --- |
| Blender, attempt 0 (the v2 textures) | 22:49:13-22:51:30 | 0 | `s41_paw_v7.attempt0_regular_grain.*`; `Archive/v7_attempt0_production` |
| Blender (v3) | 23:04:18-23:06:31 | 0 | `s43_paw_v7.*`; signed b9ef0365 |
| the Unreal import | 23:07:37-23:08:21 | editor 0, wrapper 0 | `readback_v7.json` |
| the fresh-editor material check | 23:08:42-23:09:04 | 0 / 0, no problems | `material_check_v7.json` |
| the cost check | 23:09:27-23:11:00 | 0 / 0; it exited by itself 6 s after its marker | `Cost/cost_v7.json`, six CSVs |
| capture v8 | 23:12:21-23:12:52 | 0 / 0; it exited by itself 3 s after its marker | `s50_v8_fur_outputs.sha256` |

**Preserved first:**
- v6's paw production is at `Archive/v6_paw_production`;
- the imported namespace capture v7 drew is at `Archive/v6_ue_namespace`.
  Its 21 files are the ones v7's manifest binds.

**The build:**
- 529,806 triangles, the same topology as v6;
- the white gain 1.2367;
- the shells at least 0.40 mm clear of the bow and 99.987 % above the skin;
- the FBX normals as built.

**The import's readback:**
- The shell section's normals are 4.76° off their faces (FBX 4.78°).
- The shell material is 1,786 pixel and 357 vertex instructions, with 2
  pixel texture samples (v6: 1,781 pixel instructions; the tint multiply
  adds 5). The opaque fur skin's is 212. That is an instruction ratio, not a
  runtime cost.

**The freezes** around capture v8 agree: head b9ef0365, no tracked change,
and the imported namespaces unchanged. The editor saved its own settings
under `Saved/Config` during the session.

## The cost check, as measured

The cost check ran in the editor, in the capture's own scene. Its viewport
was 969 x 545, so these are not 1920 x 1080 times. Each state is 120 valid
samples: the JSON's frames 121 counted a repeated header row, which the
fixed parser no longer counts.

The translucency pass (`GPU/Translucency`), median (p25-p75), ms:

| hold | the shells | the same shells, unlit, opacity 0 | the paw hidden |
| --- | --- | --- | --- |
| right_cheek_clear | 2.108 (2.001-2.188) | 0.085 (0-0.147) | 0 |
| paw | 2.527 (2.377-2.572) | 0.049 (0-0.115) | 0 |

The whole frame (`GPUTime`), median (p25-p75), ms:

| hold | the shells | the clear shells | the paw hidden |
| --- | --- | --- | --- |
| right_cheek_clear | 11.96 (10.24-13.58) | 11.61 (10.04-12.84) | 10.56 (9.36-11.89) |
| paw | 11.71 (10.56-12.88) | 11.37 (9.82-12.38) | 10.95 (9.19-12.73) |

The lit and clear shells differ by only 0.35 and 0.34 ms in the whole frame,
with wide, overlapping spreads. So the pass medians are not whole-frame
savings. The editor's frames were bound by its game thread, about 12.3 ms of
a 13.9 ms frame.

**The shell material's instructions per translucency lighting mode**
(compiled copies, not timed):

| lighting mode | pixel instructions |
| --- | --- |
| Surface ForwardShading (as built) | 1,786 |
| Surface TranslucencyVolume | 1,229 |
| Volumetric directional | 410 |
| Volumetric non-directional | 384 |
| Volumetric non-directional per vertex | 337 |
| the clear control | 150 |

**What this does not show** (root's review of the run):
- The clear control changes the opacity, the lighting and the shader
  together. So it does not isolate equal-work overdraw.
- Two holds cannot establish a fixed plus per-fragment model.

The close-up has about 32 times the eye view's shell fragments, yet its pass
took only 0.42 ms more. A large per-frame cost of the lit translucent
material would explain that, but it is a hypothesis, not a finding. Nor does
the run show that fewer layers would save little.

**The next measurements**, for a later lane:
- time the shells under the cheaper lighting modes;
- an equal-work control: the same shader and opacity with fewer layers;
- times at 1920 x 1080.

## Capture v8 against v7

The comparison is `fur_capture_noise --assets`, an asset comparison.
- **The setup is matched:** holds, cameras, sockets, poses, resolution,
  exposure, sun, set and run-up are equal.
- **The assets differ, as bound:** v8 binds 33 files (the tint map is new)
  and v7 32. 22 differ, all in the paw's namespace. The rig's are identical.
- **No paw slot changed.**

**The reticle:** right_cheek_clear's ID pass shows no bow, arrow or paw
pixel in the 0.12 disc.

**The fur's high-frequency residual** (`s51_fur_assets_v7_v8.json`):

| hold | common pixels | residual, v7 / v8 | fur / bow, v7 / v8 |
| --- | --- | --- | --- |
| right_cheek_clear | 7,739 | 0.00316 / 0.00245 (-22.51 %) | 0.61x / 0.52x |
| paw | 278,882 | 0.00179 / 0.00163 (-9.06 %) | - |

**The coat's form** (`s51_fur_form_v7_v8.json`; over both runs' fur
selections, as v6/v7's):

| hold | mean luminance, v7 / v8 | form contrast (15 px), v7 / v8 | p10, v7 / v8 |
| --- | --- | --- | --- |
| right_cheek_clear | 0.719 / 0.759 | 0.087 / 0.084 | 0.607 / 0.668 |
| paw | 0.662 / 0.709 | 0.081 / 0.074 | 0.544 / 0.600 |

**What the originals show:**
- **The eye view:**
  - v7's grey contour lines are gone, and the paw is a clean white with soft
    form shading;
  - the clumps are about 2 px here, so at this scale it still reads mostly
    smooth, glove-like in form.
- **The close-up:**
  - the stripe bands are gone;
  - the coat shows overlapping tufts with soft partings along the flow,
    fine streaks, and a fuzzier silhouette at the knuckle;
  - it no longer reads as felt, but its clumps can read as feathery or
    scaled.
- **Unchanged:** the pink pad at the grip's edge, and the kote's cloth and
  cord.

**The CPU fragment count** at v8's poses (`s51_overdraw_v8.json`) equals the
count at v7's: 89,514 (eye) and 2,908,447 (close-up).

## What is left, for a later lane

These are candidates, not started.
- **Root's review of the v7 build's Cycles originals:** dense grooves at
  macro and archer scale, and smooth highlights on the cloth and the cords.
- **The eye view's smoothness:** larger tufts, or guard hairs or fins along
  the silhouette, would give it structure at 0.44 mm per pixel.
- **The close-up's feathery read:** softer partings, more variation in
  length, and less regular clump outlines.
- **The cost:** the next measurements above.
