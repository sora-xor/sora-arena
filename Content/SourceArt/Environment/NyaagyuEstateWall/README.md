# Nyaagyu Estate perimeter-wall module

This editable four-meter module replaces the Estate's plain perimeter-wall
rendering while the existing C++ walls remain gameplay collision. The mesh
origin is the center of a **100 × 400 × 540 cm** section: local X is wall
thickness, Y is the repeat axis, and Z is centered on the collision wall.
Thirteen modules fit a 52 m WallX side and sixteen fit a 64 m WallY side.
End timber posts are half-width so adjacent modules complete each post.

The original Blender source models a battered, individually coursed stone
foundation, a lime-plastered upper wall with sparse low-level losses, dark
timber posts, and overlapping pitched clay roof units. Its six material slots
use three pre-existing SHA-pinned Poly Haven scans (plaster, aged wood,
roof ceramic) and a separately acquired [Rock 01](ScanRock01/manifest.json)
scan. All four scans are CC0, with authors, source URLs, file hashes, and
licenses recorded in [manifest.json](manifest.json). The natural rock scan
supplies mineral texture, while project-authored geometry supplies the stone
joints. No image pixels or geometry were copied from a historical photograph.

The material direction comes from [UNESCO's Himeji-jo description](https://whc.unesco.org/en/list/661),
which documents early seventeenth-century stone walls, wood construction,
and plastered earthen walls; [Himeji Castle's official history](https://www.himejicastle.jp/en/guide/history/)
describes layered plaster and fired roof tiles. [Kyoto's official tourism
office](https://kyoto.travel/en/travel-inspiration/kyoto-craftmanship-small-production-crafts/)
documents kawara as an ongoing ceramic craft. The Nyaagyu Estate's height,
post spacing, coursing, and tile-cap profile are a fictional design for this
game, not a surveyed Edo wall. The existing roof scan's Western overlap
pattern is used only as micro-surface on separately modeled clay units.

Rebuild and validate from the repository root:

```sh
blender -b --factory-startup --python scripts/art/create_nyaagyu_estate_wall.py
blender -b Content/SourceArt/Environment/NyaagyuEstateWall/Nyaagyu_EstateWall.blend --python scripts/art/validate_nyaagyu_estate_wall.py
```

Import with the standalone Unreal 5.8.2 script:

```sh
UnrealEditor-Cmd SoraArena.uproject -ExecutePythonScript=scripts/unreal/import_nyaagyu_estate_wall.py
```

It creates `/Game/Generated/Environment/Props/SM_Nyaagyu_EstateWall_4m`
and six exact material instances. The Windows import builds Nanite; its full
conventional mesh remains for M1 Macs, whose `METAL_SM5` path cannot run Nanite.
The WorldBuilder must place visual instances above its unchanged collision
proxies with collision disabled on the visual components.

Compare the same-camera [plain wall](Nyaagyu_WallProxy_Before_Blender.png) and
[replacement](Nyaagyu_EstateWall_Blender.png). This is a stronger original
environment asset, but the tiled run, seam quality, in-engine materials,
lighting, and Mac performance still need inspection. It is not a finished
AAA photoreal asset or a precise historical reconstruction.
