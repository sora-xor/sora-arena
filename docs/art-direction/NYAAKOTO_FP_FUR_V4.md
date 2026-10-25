# The first-person paw's fur, v4: opaque clumps, fringed tips, skin-lit cards

**Status (2026-10-25):** source, rebuilt assets and capture v5, made during
root's bounded fur and paw lane. It is a fur diagnostic and candidate: not
art acceptance, an admission or a photoreal claim.

**Result, qualified (root's review of v5):** this compares two asset
versions, one capture each, with the atlas, the card normals and the winding
all changed together. The fur's measured high-frequency residual fell by
40 % to 47 %. How that splits among the three changes is not established.
What remains is a flatter, whiter coat with angular card gaps (below).

**The comparator, reviewed:** root's probe of `fur_capture_noise --assets`
(148c5c1) found four malformed copies of v5 that it accepted. The v4 and v5
figures here stand on root's separate checks of the originals. The fix
follows the v6 capture.

## The defect

Capture v4 (`Saved/YumiFP/v4_runup_auto`, `v4_runup_4`) and root's review of
it: the white fur stays "coarse, blade-like, noisy".
- The same speckle appeared under both run-ups. On each hold's common fur
  region the residual changed by -2.4 % to +1.3 %.
- In a 2x crop of the paw hold, both runs show flat, angular bright flakes
  with dark specks between them.

## What the atlas did to it (`scripts/art/fur_atlas_coverage.py`)

**The engine's rule.** A masked material with DitherOpacityMask draws a
fragment when mask - clip + 0.83 x noise - 0.5 > 0, with blue noise that
changes every frame (`BlueNoiseCommon.ush:19-26`, through
`MaterialTemplate.ush` `GetDitheredCoverage`; `GetMaterialMask` = mask -
clip, `:3911`).
- So a texel of alpha a is drawn with probability a / 0.83 at clip 0.33.
- Any alpha between 0 and 0.83 is a per-frame coin flip, which is speckle
  unless a temporal history averages it.

**The footprints.** A card's tile (256 x 512 texels) spans its width and
length, about 0.79 x 2.5 to 4.7 mm at the viewmodel's 0.75 scale (a digit's
card and the metacarpus's):
- the eye view is 0.44 mm a pixel (Grip_L 60.8 cm away, 70°): about 144
  texels across by 48 to 92 along;
- the paw close-up is 0.078 mm a pixel (26.2 cm, 32°): about 25 across by
  8 to 16 along.

**v3's 260 to 360 hairs a tile** are about 5 µm each on the card, so every
footprint averages them to alpha 0.1 to 0.7. Over the area the cards cover:

| atlas | eye view: dithered / speckle variance | paw close-up: dithered / speckle variance |
| --- | --- | --- |
| v3 (archived, `Saved/NyaakotoFPPaws/Archive/v3_furcards`) | 98 to 99 % / 0.166 to 0.170 | 89 to 90 % / 0.132 to 0.133 |
| **v4** | **47 to 49 % / 0.069 to 0.071** | **37 % / 0.060** |

The speckle variance is the mean of P(1 - P): the speckle's energy. v4 has
42 % of v3's in the eye view and 45 % in the close-up. The measure models
the atlas only: not the geometry, the lighting or TSR.

## What v4 changes

**The atlas** (`create_nyaakoto_fp_fur_textures.py`, manifest schema 4,
with its dither measure):
- **Strand groups at the scale the close-up resolves:** 7 to 11 a tile.
  Their roots are 1.5 to 2.1 times the even share of the width, so the lower
  tile is fully covered.
- **Opaque bodies:** each body closes at 62 % to 82 % of its strand.
- **The fringe:** the body's 4 to 8 hairs run on alone to the strand's tip,
  at 70 % to 100 % of the tile. They fade in inside the body, so they leave
  no seam.
- **The hair in colour and normal, not alpha:** streaks ±6 %, darker at
  their seams, each hair's cylinder on its strand's.
- **Odd rows run root at the top.** Tips then abut tips and roots abut
  roots. Without it, a mip read past a row-0 tile's tip would pull in row
  1's opaque roots.

**The cards** (`nyaakoto_fp_paws.fur_cards`). The layout, density, lengths
and seeds are v3's.
- **Shading normals bent 0.75 of the way to the skin's normal at the root.**
  v3 exported each card's own face normal, so overlapping cards at slightly
  different angles lit as separate flat facets.
  - The bent normals are within 13° of the skin's.
  - They sit 8.6° off their own faces on average, against about 1° for a
    face normal.
- **Fronts outward:** v3's winding faced the skin, so a two-sided material
  shaded the visible side with its normal flipped.
- **UVs follow the flipped rows:** every card's tip is at v 0.5.

**The build and the import** (`create_nyaakoto_fp_paws.py`,
`import_nyaakoto_fp_paws.py`):
- **The Blender build** sets the cards' normals as custom normals, and gives
  every other part its own custom normals before the join, so the cards'
  survive it.
- **Its checks** require the fronts outward and the bent normals within 20°
  of the skin.
- **An FBX round trip** re-imports the export and requires its card corners'
  mean angle from their faces within 0.5° of the built arrays'.
- **The Unreal import** reads the fur section back from the mesh's render
  data, every 8th triangle. It requires the same mean within 1° of the FBX's,
  so a recomputed normal fails the import.

**Unchanged:** the fur material (two-sided foliage, DitherOpacityMask, clip
0.33, the root occlusion from the masks), the skin, the pads, the kote, the
holds, the cameras and the exposure.

## Tests

- `test_nyaakoto_fp_fur_textures` (6):
  - the measure against a direct sampling of the engine's rule;
  - the box mean against a direct sum, with and without wrap;
  - the committed atlas's hashes and measure;
  - at most half v3's speckle variance at both footprints, and more than
    half the cards solid;
  - the odd rows' roots at the top;
  - a tile's lower half covered.
- `test_nyaakoto_fp_paws.Fur`, 3 added:
  - every live card triangle's front faces out from the skin;
  - the shading normals are unit and within 20° of it;
  - the odd rows' UVs are reversed.

## The run (2026-10-25, root's bounded lane)

Each step's command, PIDs, logs and exits are in `Saved/W18Rebuild/s20-s25*`
and the mailbox note of 20:58 UTC.

1. **The atlas:** generated deterministically, byte-identical to the
   reviewed draft. Its ledger is rewritten, and v3 is archived.
2. **Blender, attempt 0:** stopped at its own FBX check.
   - That check re-imported the FBX through Blender's importer, which read
     the cards' corners at 0.45° off their faces.
   - The file itself holds 8.46°, against v3's 1.86°. The check measured the
     importer, not the export.
   - It now parses the FBX's bytes with Blender's own
     `io_scene_fbx.parse_fbx` (0b2fac1).
   - Attempt 0's FBX and logs are kept.
3. **Blender, attempt 1:** passed, exit 0.
   - Counts as v3's: 404,012 triangles, 20,292 cards.
   - Fronts all outward (worst cos 0.639), normals within 11.9° of the skin.
   - Corners 8.352° off their faces as built, 8.456° in the FBX.
   - Signed 6f81938, with its ledger. v3's production files are archived.
4. **The Unreal import** (`--rhi`): passed, editor 0, wrapper 0. The fur
   section's corners read back 8.32° off their faces, so the import kept
   the custom normals. Bounds error 5e-6 cm, all materials compiled.
5. **The fresh-editor material check:**
   - Attempt 0 could not write over step 9's read-only record (wrapper 1).
   - It now takes an exclusive `out=` (d6021af).
   - Attempt 1 passed with no problems.
6. **Capture v5** (`Saved/YumiFP/v5_fur`): right_cheek_clear and paw, 1920 x
   1080, runup=auto, IDs.
   - Editor 0, wrapper 0; it exited by itself 8 s after its marker.
   - Cameras, exposure, sun, set and material bindings are v4's. The solved
     right_cheek_clear differs from v4's by at most 3.4e-12 cm.

## Capture v5 against v4 (runup=auto)

**The reticle:** right_cheek_clear's ID pass still shows no bow, arrow or paw
pixel in the 0.12 disc.

**The fur's speckle** (`fur_capture_noise --assets`, new for this
comparison; `Saved/W18Rebuild/s25_fur_assets_v4auto_v5.json`):
- The common region is the intersection of the two runs' fur selections.
- It checks first that each common hold's camera, hold, posed sockets and
  pose match within 1e-9 cm, beside the setup.

| hold | fur pixels, v4 / v5 | own residual, v4 / v5 | common-region residual, v4 / v5 | fur / bow |
| --- | --- | --- | --- | --- |
| right_cheek_clear (eye view) | 7,266 / 7,630 | 0.0216 / 0.0133 | 0.0216 / 0.0130 (**-39.7 %**) | 4.1x / 2.5x |
| paw (close-up) | 271,445 / 279,556 | 0.0166 / 0.0092 | 0.0166 / 0.0088 (**-46.8 %**) | - |

For scale, the run-up comparison of v4's two runs moved the same measure by
-2.4 % to +1.3 %.

**The coat's form** (`Saved/W18Rebuild/s25_fur_form_v4auto_v5.json`): it is
brighter and a little flatter.

| hold | mean luminance, v4 / v5 | form contrast (15 px), v4 / v5 |
| --- | --- | --- |
| right_cheek_clear | 0.746 / 0.815 | 0.074 / 0.069 |
| paw | 0.788 / 0.825 | 0.053 / 0.047 |

**What the originals show:**
- The close-up has lost v4's dark pepper of dither specks, and the strands
  read as directional streaks.
- The patchwork of flat, angular card shapes with darker gaps between them
  remains, its edges now crisper.
- At the eye view the paw is a smoother but flat white.
- Root's reading of the Blender originals applies here too: broad opaque
  strips, comb-like edges, a flat white paw and a glossy sleeve.

## What is left, for a later lane

- **Form and volume:**
  - coat-depth occlusion per card (a lower card darker), not only per
    texel from root to tip;
  - a white nearer real white fur's albedo, so form shading shows.
- **The angular gaps:** the skin under the cards shows as grey wedges. Bring
  the skin's colour to the coat's mean, or close the gaps.
- **Comb-like fringes:** less regular hair spacing and lengths in each
  strand's fringe.
- **The sleeve's gloss:** the kote silk's broad highlights, a separate
  material defect.
