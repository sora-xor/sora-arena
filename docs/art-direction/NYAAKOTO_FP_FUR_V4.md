# The first-person paw's fur, v4: opaque clumps, fringed tips, skin-lit cards

**Status (2026-10-25):** source and rebuilt assets, made during root's
bounded fur and paw lane. Its capture is below once it has run. A fur
diagnostic and candidate: not art acceptance, an admission or a photoreal
claim.

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

## The capture

**Planned:** right_cheek_clear and paw, 1920 x 1080, runup=auto, IDs for the
eye view, into a fresh directory. The camera and exposure are v4's, and v4's
originals stay as they are.
