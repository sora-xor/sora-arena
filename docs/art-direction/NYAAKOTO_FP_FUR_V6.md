# The first-person paw's fur, v6: shells instead of cards

**Status (2026-10-25):** source, under root's third bounded fur lane. The
build, import and capture v7 follow below once run. It is a candidate: not
art acceptance, an admission or a photoreal claim.

## Why a different construction

Root's reviews of captures v5 and v6: the paw reads as "bright angular white
flakes over dark gaps, with weak coherent volume". Colour, occlusion, taper
and fringe changes (fur v5) did not move it.

Both failures come from one construction, masked cards on a thin sheet:
- **Thin alpha** (v3's 5 µm hairs) averages to mid alpha at every footprint
  a view uses. The engine's dithered mask turns that into per-frame speckle
  (`fur_atlas_coverage.py`).
- **Opaque cores** (v4, v5) end the speckle, but each card is then a flat
  flake. Overlapping flakes tile into a patchwork with skin showing between
  them.

**Shell fur** is a different construction:
- the coat is a stack of translucent offset layers of the skin;
- each layer draws only the cross-sections of the strands that reach its
  height.

So:
- there are no card outlines;
- a translucent material has no dither;
- every gap is the coat's deeper layers, never skin;
- the volume is built in, since each layer is shaded darker toward the skin.

## The construction

**The layers** (`nyaakoto_fp_paws.fur_shells`, `SHELLS`; `FUR_MODE = "shells"`):
- ten shells on the paw's own coarser skin (surface nets at 1.6 mm), only
  over furred skin, by the cards' rules (no pads, no contact with the
  leather, nothing under the sleeve);
- shell i sits at H x ((i + 0.5) / 10)^1.15, at least 0.15 mm up. H is the
  coat's height by region: digits 1.2 mm, metacarpus 1.8 mm, the wrist's
  ruff 3.0 mm, the dewclaw 1.0 mm. It is clamped 0.4 mm clear of the bow.
- **The comb:** each shell slides along the coat's flow by h x tan(50°), so
  the strands lean as the coat lies. The flow is the cards' own field
  (`coat_flow`, factored out unchanged).
- **The colour:** the hero's white (fur v5), the form's occlusion, and a
  self-shadow from 0.55 at the skin to 1 at the top. Alpha is the shell's
  height share.
- **The UVs:** a box projection of the shells' skin, one texture tile per
  4 mm, shared by every shell, so each strand is one leaning column.

**The strand texture** (`create_nyaakoto_fp_shell_texture.py`;
`FurShells/T_NyaakotoFP_FurShells_Strands.png`):
- 512 x 512, tileable, 494 blue-noise strand centres about 0.18 mm apart;
- each strand has its own length (45 % to 100 % of the coat's height), and
  tapers as 0.58 x (1 - h / length)^0.6 spacings;
- its four channels hold the strands' coverage at 15 %, 40 %, 65 % and 90 %
  of the coat's height: 0.742, 0.383, 0.107 and 0.007.
- It stores coverage, not distance, so mips average it correctly. From far
  away a shell draws its strands' mean coverage, not a thresholded edge.

**The material:**
- `M_NyaakotoFP_FurShells` in Unreal: translucent, lit per pixel (Surface
  ForwardShading), not two-sided, roughness 0.65, specular 0.35. Its colour
  is the vertex colour. Its opacity is 0.95 times the texture's coverage at
  the shell's height, blended between the four channels by tents a quarter
  wide.
- Blender (the Cycles reviews) uses the same alpha.
- The strand texture is imported uncompressed and linear
  (`TC_VectorDisplacementmap`).

**What changes around it:**
- **The slot:** `M_NyaakotoFP_FurShells` replaces `M_NyaakotoFP_FurCards` in
  the paw's slot list (`fp_material_bindings.json`, the importer).
- **The card atlas** is still imported, because the capture's ID pass masks
  with it.
- **The checks:**
  - the build checks the shells' clearance of the bow and of the skin;
  - its FBX normal measure, and the import's readback of it, use the shell
    slot.
- **Unchanged:** the skin, pads, kote (fur v5's), holds, cameras and
  exposure.

**Not built: fins.** Shells seen edge-on show their layers. The usual cure is
fins, cards standing along the silhouette and faded by view angle. They wait
for the capture to show whether the layers read.

## On the CPU

**The shells** (`test_nyaakoto_fp_paws.Shells`, the real config):
- 288k triangles on a 2 mm test skin;
- every vertex at least 0.4 mm clear of the bow;
- 99.99 % above the fine skin. A few points of the lowest shell dip under it
  where the coarse skin cuts a curve, hidden under the opaque skin.
- each shell higher than the one below;
- the comb's lean is tan(50°) where nothing slid it;
- the faces point out, and deeper shells are darker by the designed ratio.

**The strand texture** (`test_nyaakoto_fp_shell_texture`): it is its
manifest's, it tiles, its coverage falls with height, and its strand count
is (4 / 0.18)^2 within 15 %.

Tests: 128 run: 128 passed, 0 expected failures, 0 skipped. The suites:
- the shell texture 4; paws 28; bindings 10; the fur atlas 8; raster 9;
- fur noise 26; analysis 28; capture run-up 7; exit hand-off 8.
