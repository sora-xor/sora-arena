# Nyaagyu horse tack: measured art references

The user asked for historically credible **abumi**, **tazuna**, and the rest of
the mounted kit. The current horse and tack are an original fictional design,
not a museum replica. These primary collection records give the next modeling
pass object dimensions, construction, and material evidence. No collection
image has been copied into the game.

| Object | Primary record and observed construction | Modeling constraint |
|---|---|---|
| Kura, dated 1658 | [The Met, 2000.405](https://www.metmuseum.org/art/collection/search/26572): 36.8 cm long, 27.3 cm high, 38.1 cm wide. The record describes a typical four-piece wooden tree, mortise-and-tenon joints, hemp or leather lacing, and lacquered surfaces. | Sculpt the front and rear trees as constructed wooden forms with joints and lacing. Keep lacquer, leather, wood, and textile as distinct PBR responses. |
| Complete 19th-century saddle kit | [The Met, 36.25.571a–l](https://www.metmuseum.org/art/collection/search/23992): 40.0 cm saddle length; each abumi about 29.2 cm long and 12.1 cm wide; stirrup straps 91.4 cm; saddle flaps 50.8 × 68.6 cm. Listed materials include wood, leather, lacquer, doeskin, silk, iron, and gold. | Use as scale evidence for the full assembly, with its later date labeled. Do not silently merge its ornaments into the 1658 design. |
| Late-16th/early-17th-century abumi | [The Met, 2008.120.1–2](https://www.metmuseum.org/art/collection/search/35376): each roughly 29.8 cm long, 26.5 cm high, 12.5 cm wide; iron, lacquer, mother-of-pearl. The family mon appears prominently at the front. | Keep the protective broad-toe shape and a visible open heel; mount the supplied SORA mon at the same kind of front location as a fictional clan mark. |
| 18th-century hato-mune abumi | [The Met, 2016.205a–b](https://www.metmuseum.org/art/collection/search/712927): left 27.2 × 12.8 × 24.6 cm; right 27.6 × 12.8 × 24.8 cm. Iron, wood, silver, lacquer, paper. | The current modeled pair is based on this form. Recheck the bowl, toe rise, suspension loop, tread, and edge thickness against multiple object views before signoff. |
| Late-18th-century ceremonial trappings | [The Met, 14.100.544](https://www.metmuseum.org/art/collection/search/22586): lacquered saddle, silver-inlaid abumi, and ceremonial braids on the horse's chest and flanks. | Use for an elite ceremonial variant only; the campaign workhorse should not inherit all luxury ornament by default. |

The current generator's approximate `Kura_wooden_tree` bounding length and
width are 48 × 46 cm, larger than the museum saddle measurements above. This
may accommodate the anthropomorphic rider, but it is **not historically
validated**. An artist should put Nyaakoto in a mounted pose with both feet in
the broad abumi, then reconcile saddle dimensions, horse anatomy, leg reach,
strap hang, and paw grip against the measured objects. The procedural tazuna
curves are also not yet tested under rein tension or rider hand placement.

The current [horse source](../Content/SourceArt/Horses/Nyaagyu/manifest.json)
and [walk study](../Content/SourceArt/Horses/Nyaagyu/RigStudy/README.md) remain
stylized. A period specialist and equine animator should review the final
functional rig and equipment before any "historically accurate" claim.
