# Nyaagyu horse: isolated anatomy, coat and tack study

This is a **source-only art study**. It is an original, editable Blender scene,
one UV0 static FBX, nine 2K PBR maps (albedo, DirectX normal, ORM), three
review renders, and a validator. It does not replace the existing game mesh or
claim photorealism, historical reconstruction, or rideable gameplay.

Build and verify from the repository root:

```sh
python3 scripts/art/create_nyaagyu_horse_anatomy_textures.py
blender -b --factory-startup --python scripts/art/create_nyaagyu_horse_anatomy_study.py
python3 scripts/art/validate_nyaagyu_horse_anatomy_study.py
```

The new anatomical core joins the barrel, scapular muscles, croup, haunch,
forearm, hindquarter, head and proximal limbs into a continuous surface. Its
fore and hind legs have explicit elbow/stifle, carpal/hock, cannon, fetlock,
pastern and hoof-ring stations. The head adds a narrowed nasal bridge,
masseter, inset eyes, lid fold, nostril and folded pinnae. Short coat color
varies by vertex color so bay points darken gradually down the limbs instead
of ending at a horizontal stripe. A denser fine-fibre mane and tail are
separate static geometry; neither is a production groom.

Compared with the [previous PBR review](../PBR/Nyaagyu_HorseAndTack_PBR_Review.png),
the [three-quarter](Nyaagyu_Horse_Anatomy_ThreeQuarter.png) and
[profile](Nyaagyu_Horse_Anatomy_Profile.png) views show more deliberate
shoulder and haunch transitions, a longer nasal profile and narrower lower
limbs. The previous single rectangular kura tree and solid upright panels
are replaced by curved longitudinal members, two arched crosspieces, a
tensioned seat and small visible joint lacing; the [saddle close-up](Nyaagyu_Horse_Tack_Detail.png)
shows this construction. The retained abumi, tazuna, bit, cloth and exact
SORA SVG relief remain in their source locations. The stirrup's broad toe
enclosure is based on the dimensions in the existing tack reference, but
its load path and rider clearance still need validation.

The material graph in the Blender source uses the nine maps and packs them
into the `.blend`. The FBX intentionally contains geometry, UV0, vertex color
and material names. For Unreal, wire each manifest texture set to its named
material slot: albedo to Base Color, green from ORM to Roughness, blue from
ORM to Metallic, red from ORM to Ambient Occlusion, and NormalDX to Normal.
The coat slot also multiplies `CoatVariation` vertex color into Base Color.
Use a conventional Mac-compatible LOD/card-fur path. These authored maps
derive from the project-owned horse coat swatch or procedural horn/lacquer
variation; **they are not measured scans**.

Art/reference provenance:

| Evidence | How it was used | Rights |
|---|---|---|
| [Met 1658 kura, 2000.405](https://www.metmuseum.org/art/collection/search/26572) | Four-piece wooden construction, lacing, lacquer, and 36.8 × 38.1 × 27.3 cm object dimensions informed the revised seat/crosspieces. This is proportion evidence, not a mesh trace. | Public-domain object image per the Met; no image copied into this asset. |
| [Met late-16th/early-17th c. abumi, 2008.120.1–2](https://www.metmuseum.org/art/collection/search/35376) | Width/height/length and placement of a mon at the front informed the inherited stirrup. The SORA SVG is a fictional substitution. | Public-domain object image per the Met; no image copied. |
| [Met hato-mune abumi, 2016.205a–b](https://www.metmuseum.org/art/collection/search/712927) | The inherited toe form and iron/wood/lacquer material split use these dimensions. | No image copied. |
| [UC Davis equine limb diagram](https://ceh.vetmed.ucdavis.edu/sites/g/files/dgvnsk4536/files/local_resources/pdfs/pubs-HR29-3-Chart-sec.pdf) and [horse-parts chart](https://ceh.vetmed.ucdavis.edu/sites/g/files/dgvnsk4536/files/inline-files/Parts%20of%20the%20horse.pdf) | Named bone/joint and exterior landmarks informed the sculpt station names. | Visual reference only; no image copied. |
| Project-owned [baseline PBR source](../PBR/variant_manifest.json) | Existing first-party tack, exact user SORA SVG, and project-owned horse coat source. | Source hashes pinned in `manifest.json`; no third-party mesh used. |

The images remain an honest art gate: the round eye surround, geometry-based
hooves, sparse mane, uncomplicated cloth, overexposed arch highlights and
unscanned coat are visibly stylized. Before replacing the game horse, a horse
anatomy artist should sculpt against side/front reference plates, retopologize
for deformation, acquire or capture calibrated hide/hoof/leather/lacquer
materials, build a strand/card groom, test saddle fit with mounted Nyaakoto,
simulate reins/girth and collision, and obtain equine and Japanese-tack
specialist review. UV seams, Nanite/conventional LODs, skeletal transfer and
in-engine lighting/performance remain unqualified.
