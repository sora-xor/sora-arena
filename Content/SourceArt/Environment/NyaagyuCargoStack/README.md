# Nyaagyu Estate cargo stack

This is an original visual replacement for the plain 230 × 180 × 140 cm Estate
cover cube. The mesh occupies 223.5 × 173.0 × 138.6 cm and retains the
existing cube as gameplay collision. The detailed boards, bundles, nails,
ropes, and emblem have **no gameplay collision**.

The editable [Blender source](Nyaagyu_CargoStack.blend) contains two individually
planked timber crates on a pallet, edge scuffs, iron fasteners, four crate
lashings, two rice-bale-inspired straw bundles, an indigo cloth bundle, and
six bundle ties. The small crate stamp uses the two exact paths of the
user-supplied SORA SVG, with its source hash pinned in [manifest.json](manifest.json).
The static [FBX](SM_Nyaagyu_CargoStack.fbx) has eight exact material slots.

The nine 2K albedo, DirectX normal, and ORM maps for wood, straw, and indigo
cloth are original deterministic procedural pixels. The same straw maps,
color-tinted, serve the hemp lashings. Generator hash, seed, map hashes, and
material bindings are in [PBR/manifest.json](PBR/manifest.json). The normal
and roughness maps are authored estimates, not measured scans. Iron and the
SORA mark use constant physically based materials.

Edo period context is limited. [The Met's *Farmers' Lives in the Twelve Months*](https://www.metmuseum.org/art/collection/search/44674)
shows rice baling and warehouse storage. [The British Museum's Osaka guide](https://www.britishmuseum.org/blog/historical-city-travel-guide-osaka-early-19th-century)
describes harvest grain being inspected in straw bags. The crate joinery,
relative arrangement, and cloth bundle are fictional workshop cargo, not a
reconstruction of one recorded Edo object.

Rebuild and validate from the project root:

```sh
python3 scripts/art/create_nyaagyu_cargo_pbr.py
blender -b --factory-startup --python scripts/art/create_nyaagyu_cargo_stack.py
python3 scripts/art/validate_nyaagyu_cargo_pbr.py
blender -b Content/SourceArt/Environment/NyaagyuCargoStack/Nyaagyu_CargoStack.blend --python scripts/art/validate_nyaagyu_cargo_stack.py
```

The standalone pinned UE 5.8.2 importer is
`scripts/unreal/import_nyaagyu_cargo_stack.py`:

```sh
UnrealEditor-Cmd SoraArena.uproject -ExecutePythonScript=scripts/unreal/import_nyaagyu_cargo_stack.py
```

It creates `/Game/Generated/Environment/Props/SM_Nyaagyu_CargoStack` and its
exact material instances. The import builds Nanite data for supported Windows
hardware and keeps a full conventional static-mesh fallback for M1 Macs,
whose `METAL_SM5` path cannot run Nanite. The WorldBuilder must place
the visual above its unchanged collision proxy separately.

Compare the same-camera [plain cube](Nyaagyu_CoverProxy_Before_Blender.png) and
[cargo stack](Nyaagyu_CargoStack_Blender.png). This is a stronger set-dressing
source asset, but the bundles still need higher-fidelity fiber modeling,
weathering variation, and in-engine lighting/performance review before an
AAA or historically exact claim.
