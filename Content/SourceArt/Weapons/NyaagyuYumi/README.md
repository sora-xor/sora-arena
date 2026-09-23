# Nyaakoto yumi and ya study

This is an **editable source-only candidate** for Nyaakoto's first-person bow.
The playable build still uses its temporary bow presentation. Do not bind this
FBX to gameplay yet: the studio renders still look too clean and procedural for
the requested AAA photoreal standard, and the bowstring, arrow nock, grip and
cat paw need a working draw rig and in-game fitting. The three-quarter and
close-grip renders are source inspections, not Unreal screenshots.

The original project-authored mesh has a 2.20 m asymmetric stave with a grip
0.75 m above the lower nock, an eight-sided swept bamboo/urushi laminate,
separate horn nocks and hemp string, leather sleeve with modeled binding, and
a nocked 98 cm ya with modeled feather barbs and iron point. The grip marker is
made from the user's exact `Content/SourceArt/UI/sora_logo_NOtext2.svg` paths.
It is a visually informed design study, **not** a certified Edo bow replica.
Living [kyūdō guidance](https://www.kyudo.com/kyudo-l.html) establishes the
asymmetric upper/lower limbs; [bow care guidance](https://kyudo.com/asahiam-buybow.html)
describes the roughly 15 cm bow-to-string brace dimension. Period-specific
lamination, string knotting, arrowhead and grip construction still require
expert review before calling it historically accurate.

The stave uses Poly Haven's [Bamboo Veneer](https://polyhaven.com/a/bamboo_veneer)
photo-derived 2K albedo/DirectX normal/ARM set. The grip uses its
[Brown Leather](https://polyhaven.com/a/brown_leather) photo-derived 2K set.
Both are [CC0](https://polyhaven.com/license); exact source URLs, MD5 and SHA-256
digests are pinned in `manifest.json`. Other surfaces are project-authored
Blender materials. No paid or restricted asset is included.

Rebuild and validate from the repository root:

```sh
blender -b --factory-startup --python scripts/art/create_nyaagyu_yumi_study.py
blender -b --factory-startup --python scripts/art/validate_nyaagyu_yumi_study.py
```

The FBX round trip currently yields 60 editable mesh parts with preserved
stave/grip UVs and exact crest path hashes. A production successor needs
period-art review, a driven bow/string/arrow rig, correct paw contact, PBR
import and a packaged first-person review at multiple lighting and draw states.
