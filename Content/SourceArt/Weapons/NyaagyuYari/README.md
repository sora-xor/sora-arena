# Nyaagyu su-yari — source-only art study

This is an original, editable **Blender weapon study**, not a playable Unreal
asset or a certified historic replica. It is grounded in one accession:
[British Museum OA+.7199](https://www.britishmuseum.org/collection/object/A_OA-7199),
cataloged as a middle-Edo suyari (18th–19th century). The museum record gives
**1.93 m overall length, an 18 cm blade, and a 48 cm tang** and lists steel.
The model matches those three length envelopes. The 48 cm tang is a separate
inspectable solid inside the modeled shaft.

The remaining design is an informed **game-art interpretation**. In particular,
the eight-facet diamond blade section, 25.6 mm maximum blade width, ash-colored
wood core, dark urushi concept, patinated steel collar and shoe, and russet
binding are project-authored choices; the OA+.7199 record does not establish
their exact forms or materials. A Japanese arms specialist must review the
mounting, blade section, finish, and period context before the asset is
described as historically accurate.

The study contains 10 named, closed, UV-unwrapped mesh parts (8,544 evaluated
triangles), 15 original 2K PBR maps across steel, iron, wood, lacquer, and cord,
an FBX, the packed `.blend`, and two fixed-camera inspection renders. The
albedo/ORM/DirectX-normal maps are generated entirely by the local Python
source. Blender flips the DirectX green channel for its own normal-map node.
No museum image, paid asset, or third-party bitmap is included.

![Full object study](Nyaagyu_Suyari_Full.png)

![Blade and shaft join](Nyaagyu_Suyari_BladeJoin.png)

From the repository root, rebuild and validate with:

```sh
python3 Content/SourceArt/Weapons/NyaagyuYari/build_textures.py
blender -b --factory-startup --python Content/SourceArt/Weapons/NyaagyuYari/build_nyaagyu_yari.py
blender -b --factory-startup --python Content/SourceArt/Weapons/NyaagyuYari/validate_nyaagyu_yari.py
```

The independent validation checks source mesh watertightness and positive
volumes, UV completeness, the three accession-based length envelopes, texture
and FBX hashes, and Blender FBX round-trip world-space vertex parity. Current
maximum round-trip error is 1 µm.

**Visual verdict:** the slender silhouette, faceted blade, and exposed join are
readable. The studio render still has conspicuously even shaft reflections,
regular binding, and procedural-looking iron mottle. It does **not** meet the
project's AAA photoreal gate. A production successor needs licensed
photographic/material capture, physical wear reference, historical review,
first-person paw-grip and animation fitting, LODs, and an Unreal lighting and
performance review before promotion to runtime content.
