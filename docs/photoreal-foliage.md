# Nyaagyu Estate scanned foliage pass

The campaign's ten former cylinder-and-pink-sphere trees now use a scanned,
texture-backed broadleaf tree. The source is [Poly Haven Tree Small 02](https://polyhaven.com/a/tree_small_02),
by Rico Cilliers. [Poly Haven's license](https://polyhaven.com/license) grants
CC0 use, modification, commercial distribution and redistribution. The raw 1K
glTF source is retained under `Content/SourceArt/Environment/PolyHaven/TreeSmall02/Upstream`;
ten 2K diffuse, DirectX normal, ARM and leaf-alpha maps are retained under its
`Textures` directory. Every byte, the downloaded API identity, the editable
Blender file, derived FBXs and review image have SHA-256 hashes in
`manifest.json`. No Poly Haven website preview image or logo is included.

`blender -b --python scripts/art/create_nyaagyu_photoreal_tree.py` regenerates
the HI and MAC FBX meshes from the pinned 2.06-million-triangle upstream mesh.
The HI tier retains roughly 354,000 triangles and builds Nanite data; the MAC
tier retains roughly 95,000 triangles as conventional geometry. The generator
bakes the upstream branch texture UV transform, preserves separate bark,
branch and leaf material slots, and writes an editable Blender source. Run
`blender -b --python scripts/art/validate_nyaagyu_photoreal_tree.py` to verify
the source hashes and independently import both FBXs. The Blender preview is a
source-art inspection, not a runtime screenshot.

`scripts/unreal/import_original_assets.py` imports both tiers and all ten
textures into `/Game/Generated/Environment/Foliage`. It builds default-lit,
double-sided PBR materials with DirectX normals, ARM channel unpacking and a
masked leaf alpha. `SoraWorldBuilder` places ten varied instances only in the
Nyaagyu Estate campaign. Their collision is disabled; offline gameplay proxies
and deterministic multiplayer practice remain unchanged. Mac selects the
conventional tier; supported Windows builds select the Nanite tier. Foliage
casts shadows and participates in distance-field/dynamic indirect lighting
where the platform supports those paths.

This is a material improvement over the primitive trees, not photoreal AAA
qualification. In-engine alpha, wind, shadowing, Lumen card coverage, pop-in,
frame time, and botanical suitability to the intended Japanese setting still
require art and performance review. A period-specific Japanese tree could
replace this CC0 broadleaf using the same asset boundary and validation path.
