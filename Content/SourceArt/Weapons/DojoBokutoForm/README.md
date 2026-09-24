# Nyaagyu bokuto form study

This is an editable **source-only** response to the playable chapter-one bokken's
straight, baton-like silhouette. The four-piece mesh has an oval hand-planed
grip, shallow blade curvature, carved mune/shinogi/ha facets, a blunt tip, and
a dark leather tsuba held by a fitted retainer. Its single primary UV channel
samples the CC0 [Poly Haven White Oak Veneer](https://polyhaven.com/a/white_oak_veneer)
photographed albedo, DirectX normal and ARM maps at 2K, plus a pinned CC0
brown-leather scan. The scanned veneer supplies *surface detail* on an original
solid-wood mesh; no veneer construction is asserted for historical bokuto.
The [texture manifest](texture_manifest.json) pins every source URL and hash.

The [All Japan Kendo Federation's 2023 jodo regulations](https://www.kendo.or.jp/wp/wp-content/uploads/2023/07/jodo-shiai_regulations.pdf)
specify a modern wooden tachi at 101.5 cm overall, 24.2 cm tsuka and 1.5 cm
sori, with white oak and leather tsuba. This study uses those **modern practice
proportions as a benchmark**. It does not claim that all Edo-period or
Nyaagyushinkageryuu training swords had this exact form. A Japanese weapons
historian and practical sword instructor should review the final school-specific
prop and first-person handling before production admission.

The [full source render](Nyaagyu_BokutoForm_Blender.png) and
[facet detail](Nyaagyu_BokutoForm_Detail_Blender.png) show a more legible
curve/profile and photographed grain than the inherited mesh. The wood remains
too clean and the
first-person silhouette, grip fit, and collision are unverified in Unreal.
The original playable bokken remains unchanged. This model is not an AAA
photoreal quality claim.

The strict [UE 5.8.2 ArtReview importer](../../../../scripts/unreal/import_dojo_bokuto_form_art_review.py)
verifies source hashes, scan rights, image dimensions, UV0, material slots, and
the full conventional Nanite fallback. It creates review-only assets under
`/Game/Generated/ArtReview/DojoBokutoForm` and does not replace the playable
mesh.

Regenerate and independently validate with Blender 5.2.2 LTS:

```sh
blender -b --factory-startup --python scripts/art/create_dojo_bokuto_form_study.py
blender -b --factory-startup --python scripts/art/validate_dojo_bokuto_form_study.py
blender -b --factory-startup --python scripts/art/audit_fbx_primary_uv.py -- \
  Content/SourceArt/Weapons/DojoBokutoForm/SM_Nyaagyu_BokutoForm.fbx
```

The validator checks source/FBX/renders and their hashes, 5,332 triangles,
three material zones across four parts, outward normals, UV0 coverage,
dimensions, blunt tip, sori, packed
texture sources, and Blender FBX round-trip. The [manifest](manifest.json)
records exact sources and scope. Shipping still requires packaged UE 5.8.2
material, first-person hand/paw, animation, hit-volume, historical, and
performance review.
