# Nyaakoto first-person paw and kote grip study

This is an **editable source-only visual study**, not the first-person asset in
the playable Unreal build. The fixed-camera PNGs are Blender renders, not game
screenshots or an AAA quality claim. The study holds the project's existing
katana and yumi meshes as **review-only props** so contact can be assessed at
their real source dimensions. The export FBXs contain the paw/sleeve studies,
not the reviewed weapons.

Nyaakoto's pictured white feline paws informed the color and proportions.
Each paw has a continuous remeshed palm/forefoot, four short curved digits, an
opposing dewclaw, separate warm skin contact pads, small partly retracted claws,
and a tufted transition into an indigo kote sleeve. The sleeve has three curved
lacquered lamellae, raised iron hems, and silk ties. A construction collection
retains editable anatomical masses; the renderable body is 29,470 faces per
paw and has UV0. The two-handed katana contact is fitted to the existing tsuka
near the tsuba and kashira; the bow paw contacts the new 2.20 m yumi's
asymmetric grip. All measurements use metres.

The fur, indigo weave, and lacquer reuse the project's own PBR source maps in
`../Hero/PBR`; that folder records their image-generation/procedural rights and
hashes. The 1K paw-pad albedo, DirectX normal, and ORM maps in `Textures/` are
new **project-authored procedural textures** with a fixed seed and SHA-256
records. The source props are the project-authored katana and yumi .blend files;
no paid or third-party mesh is incorporated. All external-image links in the
saved .blend resolve to paths within this repository.

The resulting pose is still too clean and geometrically simple for the user's
AAA photoreal target. The forearm fabric is a tube without anatomically driven
wrinkles, the iron plates need hand-authored wear and authentic construction
review, and the paw silhouette still needs a sculptor's anatomical pass. The
fur uses object-space box projection in Blender to avoid UV seams, but its UV0
requires a production bake for Unreal. The bow hand needs an articulated draw
state, proper string/arrow interaction, and a second draw paw with reviewed
historical technique. The katana needs animation and camera/swing visibility
checks, not just a static contact pose. Kote details are **Edo-inspired visual
study**, not a museum-certified reconstruction. Keep these assets out of the
runtime until those deficits are corrected and a packaged UE5.8.2 first-person
A/B review proves a visible improvement without clipping or performance loss.

Rebuild and validate from the repository root:

```sh
python3 scripts/art/create_nyaakoto_paw_pad_textures.py
blender -b --factory-startup --python scripts/art/create_nyaakoto_first_person_paws.py
blender -b Content/SourceArt/Characters/NyaakotoFirstPersonPaws/Nyaakoto_FirstPersonPaws_GripStudy.blend \
  --python scripts/art/validate_nyaakoto_first_person_paws.py
```
