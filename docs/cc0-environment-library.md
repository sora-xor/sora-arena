# CC0 environment material library

The first-slice CC0 surfaces, scans and HDRIs from
[`polyhaven-first-slice.json`](../scripts/assets/manifests/polyhaven-first-slice.json) and
[`ambientcg-first-slice.json`](../scripts/assets/manifests/ambientcg-first-slice.json)
are imported into `/Game/Generated/Environment/CC0`. This library includes:

- a small set of master materials;
- one weather Material Parameter Collection;
- material instances named for the places in the [story bible](campaign/story-bible.md).

Nothing in the library is admitted as photoreal game art yet. Every instance
and mesh carries the ledger's `photoreal_gate` text as metadata. Gameplay
code and the world builder do not reference the library yet. Admission still
needs the packaged A/B comparison and frame-cost measurement in
[photoreal acceptance](art-direction/photoreal-acceptance.md).

## Building it

`scripts/toolchain/import-mac.sh` builds the library as part of the normal import:

1. `scripts/unreal/pack_cc0_environment.py` runs on the host. It builds the
   library plan, which checks three things:
   - each ledger's identity and every CC0 record's license fields;
   - the SHA-256 of every raw file;
   - the period policy described below.

   It then packs the separate ambientCG AO/roughness/metalness/opacity maps into
   ARM PNGs under the gitignored `Saved/CC0Environment/Packed`. The packing covers:
   - every ambientCG material;
   - the two Poly Haven rock sets, which have roughness only;
   - the paper study, which has roughness only.

   `packed.json` records input and output hashes. An unchanged output is kept.
2. `scripts/unreal/validate_cc0_environment.py --source-only` repeats the checks
   and prints the package count the editor validator must match.
3. `import_cc0_environment.py` runs in the headless editor after the Nyaagyu
   palette import, because it binds the palette's plaster and stone-path maps.
4. `validate_cc0_environment.py` runs in the editor after the main validator.

The raw files stay read-only in the clone's `Local/ThirdPartyRaw/cc0`.
`cc0_environment_library.storage_root` finds that folder from a git worktree
through the worktree's `commondir`, so every worktree uses the one fetched
copy. If a file is missing, the import stops and names
`scripts/assets/fetch_cc0.py`.

Every imported texture, cubemap and mesh records its source SHA-256 as package
metadata. A source whose hash is unchanged is not imported again.

Each master records `SoraGraphSha256`, the digest
`cc0_environment_library.master_graph_digest` takes of everything its graph is
built from: the importer and library source, the master's name and the
default maps it binds. The importer rebuilds a master only when that digest
changes, and leaves `MPC_EnvironmentWeather` alone when its parameters already
match. Rebuilding a master gives it a new state id, which recompiles every
shader of it and of its instances, and every rebuild adds to the shader cache
on disk. The validator fails a master whose recorded digest is stale.

The first run on 2026-09-26 imported the following. It used about 2.3 GB under
`Content/Generated/Environment/CC0`.

| Imported | Count |
| --- | --- |
| Texture packages | 220 |
| HDRI cubemaps | 6 |
| Static meshes | 34 |
| Master materials | 7 |
| Material instances | 76 |

`scripts/unreal/test_cc0_environment_library.py` runs host-only tests of the
period policy, naming rules and master digest.

## Texture import rules

| Map | Settings |
| --- | --- |
| Base colour | sRGB, `TEXTUREGROUP_World`. BC7 for the 4K hero sets, default BC1 otherwise. |
| Normal | Linear, `TC_Normalmap`, DirectX. Only `moss_01` ships an OpenGL glTF normal, and it is flipped on import. Every other scan uses its `nor_dx` map. |
| ARM | Linear `TC_Masks`: R = ambient occlusion, G = roughness, B = metalness. Poly Haven `arm` maps and the ibushi `ORM` atlas are used as is. Opacity, where the source has one, is packed into alpha. |
| Paper thickness | Linear `TC_Grayscale` (the paper study's 16-bit height). |
| HDRI | `TextureCube`. Every HDRI is lighting-only by its ledger flag. The three look-development HDRIs are prefixed `HDRI_LookDev_`. |

Streaming virtual textures are enabled only for the six 4K hero sets that are
seen from under 2 m and cover large areas:

- `hinoki_planks`
- `japanese_cedar_planks`
- `clay_plaster`
- `forest_ground_05`
- `japanese_cedar_bark`
- `stacked_stone_wall` (evaluation only)

Only visible tiles of these maps stay resident. The 2K sets keep ordinary mip
streaming, which is cheaper for small tiling maps. A master's samplers must
match the virtual-texture state of what it binds, which is why there are `_VT`
masters.

`hessian_230` (2048 x 2036) and `crepe_satin` (2048 x 2085) are stretched to a
power of two so that they keep mips and streaming.

## Masters

All masters are in `/Game/Generated/Environment/CC0/Materials`. All of them
are enabled for Nanite and instanced static meshes.

| Master | Use |
| --- | --- |
| `M_Env_Surface`, `M_Env_Surface_VT` | Opaque PBR with ARM. Switches between world-aligned projection and mesh UVs. Optional detail normal and macro variation. `_VT` samples virtual textures. |
| `M_Env_HeightBlend2`, `M_Env_HeightBlend2_VTBase` | Two-layer height blend of layer B over layer A (`_VTBase`: layer A is virtual). |
| `M_Env_Foliage` | Masked, two-sided `TwoSidedFoliage` with dithered LOD transition and opacity from ARM alpha. Instances may override to Opaque, as the moss clumps do. |
| `M_Env_Cloth` | Two-sided `Cloth` shading. Outputs go through material attributes because Python cannot reach the `CustomData0` cloth pin. |
| `M_Env_LanternPaper` | Two-sided lit paper with blackbody emission and flicker. |

The exact parameter names of each family are `FAMILY_PARAMETERS` in
`cc0_environment_library.py`. The validator compares them with the built
graphs.

### UV

In `WorldAlignedUV` mode, the world position in centimetres is projected on
the dominant axis of the vertex normal, and divided by `TileSizeCm` (U, V).
This costs one fetch per map. Wall textures stay upright.

`TileSizeCm` comes from the ledger's measured `tile_size_cm` and
`source_dimensions_mm`. For example, the cedar bark is 1 m by 2 m. The
ambientCG sets carry no measured size. They default to 200 cm, and the
instances override that.

The DirectX tangent-space normal is rebuilt in the same frame. It is
re-orthogonalised against the geometric normal so that slopes keep their
shading, and the material outputs a world-space normal. Mesh-UV mode
multiplies `TexCoord0` by `UVScale` and transforms the normal from tangent
space.

### Grading

The grading parameters are:

- `BaseColorTint`
- `Desaturation`
- `RoughnessMin` and `RoughnessMax`, which remap ARM green
- `AOStrength`
- `NormalStrength`
- `MetallicScale`

Instances use them to re-grade scans whose ledger flag asks for it. For
example, modern tanned leather is darkened toward smoked leather, the jute
hessian is tinted toward hemp, and the gold crepe satin is desaturated and
retinted to undyed silk.

### Macro variation and detail normal

Macro variation samples the engine's `T_Default_MacroVariation` at two
world-space scales, `MacroScaleACm` and `MacroScaleBCm` (13 m and 47 m).
`MacroStrength` and `MacroRoughness` then vary brightness and roughness over
large distances. This breaks up tile repetition on ground and walls.

`UseDetailNormal` blends the layer's own normal at a non-integer
`DetailTiling`, using a UDN blend. The dojo floor and the earthen wall use it.

### Height blend

The coverage of layer B is `LayerBCoverage`, multiplied by vertex red when
`VertexColorBlend` is 1, plus `TopFacingBias` times the upward normal. Layer
A's ambient occlusion acts as its height. With `HeightFromCrevices` at 1,
layer B fills the crevices first; with it at 0, layer B covers the peaks.
`BlendContrast` sharpens the edge.

Each layer has its own tile size and roughness range: `LayerBTileSizeCm`,
`LayerBRoughnessMin`/`Max`, and `LayerBTint`.

### Weather

`MPC_EnvironmentWeather` holds these scalars:

| Scalar | Default |
| --- | --- |
| `Wetness` | 0 |
| `PuddleAmount` | 0 |
| `LanternIntensity` | 1 |

Gameplay sets them with `UKismetMaterialLibrary::SetScalarParameterValue`.
For example, the ch03 dusk rain sets `Wetness` to 1.

Each instance scales the rain through `WetnessResponse`. Sheltered interiors
such as the dojo floor and tatami use 0; open stone, timber and bark use 1.
`BaseWetness` keeps stream beds damp in dry weather.

A wet surface changes in three ways, following story bible §15.1:

- its albedo darkens by `WetDarkening`;
- its roughness falls toward `WetRoughness`;
- vertical and overhanging faces take about 65% of the wetting that floors take.

On world-aligned masters, `PuddleResponse` lets puddles collect as
`PuddleAmount` rises. Puddles form on flat faces (normal Z above 0.85), and in
low areas, which are occluded or macro-dark. They flatten the normal and bring
roughness down to 0.04.

### Lantern paper

`ColorTemperatureK` drives the engine blackbody, normalised to unit
luminance. The emission is:

- multiplied by `EmissiveIntensity` and the collection's `LanternIntensity`;
- multiplied by paper transmission, which falls from `TransmissionMax` to
  `TransmissionMin` as the paper thickness rises;
- given a per-object sine flicker (`FlickerAmount`, `FlickerSpeed`).

Emission feeds Lumen. The story bible's fallback of no more than eight
shadowed lights on Mac is a level-design rule and is not enforced here.

## Period-accuracy policy

The ledgers' `period_risk` and `period_flags` decide what may reach a place.
`cc0_environment_library.check_instance` enforces the rules below at every
plan build, and the unit test checks the rejections.

**High risk.** These records are imported under `CC0/Evaluation` and bound
only to `MI_Eval_*` instances, never to a place instance:

- walls whose flags record mortar joints (`stacked_stone_wall`,
  `japanese_stone_wall`, `granite_wall`, `wood_inlaid_stone_wall`);
- `muddy_tracks` (tyre tracks);
- the six Western `RoofingTiles` sets;
- `Rope002` (wire rope);
- the six ambientCG bamboo sets (possible mōsō);
- the metal-hooped buckets.

**Medium risk.** A medium-risk record may only fill the role its flag names:

| Record | Allowed role |
| --- | --- |
| `patterned_clay_plaster` | Breakup layer B, under `clay_plaster` |
| `Plaster007` | Breakup layer B (crack and spall) |
| `roof_planks` | Plank roofs, never the stable, with roughness re-graded to at least 0.5 |
| `trident_maple_bark` | Generic momiji bark only |
| `bamboo_wall_02`, `bamboo_wall_03` | Place instances marked review-pending, until the species and weave are checked |

The other medium-risk records have no role and are evaluation only:

- `lacquered_cherry_wood` (it needs an authored urushi layer);
- `mossy_stone_wall` (mortar);
- `Plaster001`;
- `Fabric019` (wool);
- `Wicker005`;
- the `katana_stand_01` mesh, until its crest is replaced by the SORA mon.

**Low and none.** These records may be used at the places their ledger
`game_use` names. A place instance may only bind a record planned for that
place.

Records meant only for characters or weapons are not imported here: the
chainmail sets, `Fabric001`/`002`/`012`, `rough_linen`, `Leather001` and
`Leather006`. `reed_roof_03` and `reed_roof_04` are evaluation only because
their top band is a ridge; tiled across a roof field, that band would repeat.

Each instance's metadata records its sources, highest risk, role and flag
caveats: `SoraSources`, `SoraPeriodRisk`, `SoraPeriodNotes` and
`SoraPhotorealGate`.

Three consequences of the policy:

- **No place-named stone wall exists.** Every first-slice wall scan is flagged
  for mortar. `MI_Eval_StackedStoneWall_MossJoints` tries the remedy the flag
  names, masking the joints with moss. It stays in evaluation until the joints
  are checked on screen.
- **Kawara uses the project's own ibushi atlas.** The ledger keeps
  `NyaagyuKawaraBay`'s original ibushi maps primary over every `RoofingTiles`
  set. The atlas is meant for per-tile UV kawara meshes and is still source-only.
- **Lantern paper uses TextureCan Paper 0017 (CC0).** The shōji study already
  retains this paper. Its fibres failed the shōji gate, so the lanterns need
  their own A/B.

## Place instances

The following instances are in `/Game/Generated/Environment/CC0/Instances`.
In the table, "world" means `WorldAlignedUV`, "palette" means an existing
Nyaagyu palette map, and "project" means an original or retained project
source. A risk in parentheses is the ledger's period risk.

| Instance | Place | Master | Sources | Mapping and role |
| --- | --- | --- | --- | --- |
| `MI_TsumagizakaDojo_HinokiFloor` | pl_tsumagizaka_dojo | Surface_VT | `hinoki_planks` (low) | world |
| `MI_EstateDay_EngawaHinoki` | pl_estate_day | Surface_VT | `hinoki_planks` (low) | world |
| `MI_TsumagizakaDojo_SugiHameita` | pl_tsumagizaka_dojo | Surface_VT | `japanese_cedar_planks` (low) | world |
| `MI_Umaya_SugiBoardWall` | pl_umaya | Surface_VT | `japanese_cedar_planks` (low) | world |
| `MI_DojoSmithy_ItabukiRoof` | pl_dojo_smithy | Surface | `roof_planks` (medium) | world; plank roof, re-graded |
| `MI_EstateDay_Tsuchikabe` | pl_estate_day | Surface_VT | `clay_plaster` | world |
| `MI_Kakuredani_CharcoalHutDaub` | pl_kakuredani | HeightBlend2_VTBase | `clay_plaster` + `patterned_clay_plaster` (medium) | world; layer B |
| `MI_EstateDay_Shikkui` | pl_estate_day | HeightBlend2 | `white_plaster_02` (palette) + `Plaster007` (medium) | world; layer B |
| `MI_EstateDay_Tatami` | pl_estate_day | Surface | `tatami_mat` (low) | world |
| `MI_EstateDay_IbushiKawara` | pl_estate_day | Surface | `nyaagyu_ibushi` (project) | mesh UV |
| `MI_EstateDay_RojiStonePath` | pl_estate_day | HeightBlend2 | `grey_stone_path` (palette) + `Moss002` | world |
| `MI_Kaido_PackedEarthRoad` | pl_kaido | Surface_VT | `forest_ground_05` | world |
| `MI_Kaido_GravelPitch` | pl_kaido | Surface | `forest_ground_04` | world |
| `MI_Kakuredani_ValleyFloor` | pl_kakuredani | Surface | `forest_ground_06` (low) | world |
| `MI_IssosekiWood_MossForestFloor` | pl_issoseki_wood | HeightBlend2 | `forest_ground_06` (low) + `Moss001` | world |
| `MI_Ishibashi_StreamBed` | pl_ishibashi | Surface | `river_small_rocks` | world |
| `MI_Kaido_MossBank` | pl_kaido | Surface | `Moss003` | world |
| `MI_Kakuredani_KayabukiThatchField` | pl_kakuredani | Surface | `thatch_roof_angled` (low) | world |
| `MI_Kakuredani_MossyThatch` | pl_kakuredani | HeightBlend2 | `riet_01` (low) + `Moss004` | world |
| `MI_Umaya_WaraStraw` | pl_umaya | Surface | `ThatchedRoof001A` (low) | world |
| `MI_Matoba_MakiwaraStraw` | pl_matoba | Surface | `ThatchedRoof002A` (low) | mesh UV |
| `MI_LaneKit_AjiroTakegaki` | lane_kit | Surface | `bamboo_wall_02` (medium) | world; review pending |
| `MI_Bugugura_TakegakiPanel` | pl_bugugura | Surface | `bamboo_wall_03` (medium) | world; review pending |
| `MI_IssosekiWood_SugiBark` | pl_issoseki_wood | Surface_VT | `japanese_cedar_bark` | mesh UV |
| `MI_EstateDay_MatsuBark` | pl_estate_day | Surface | `pine_bark` (low) | mesh UV |
| `MI_TsumagizakaDojo_KeyakiBark` | pl_tsumagizaka_dojo | Surface | `japanese_zelkova_bark` | mesh UV |
| `MI_IssosekiWood_YamazakuraBark` | pl_issoseki_wood | Surface | `sakura_bark` (low) | mesh UV |
| `MI_IssosekiWood_MomijiBark` | pl_issoseki_wood | Surface | `trident_maple_bark` (medium) | mesh UV; generic maple bark |
| `MI_Kaido_KusunokiBark` | pl_kaido | Surface | `japanese_camphor_bark` | mesh UV |
| `MI_Matoba_HempLashing` | pl_matoba | Surface | `Rope001` (low) | mesh UV |
| `MI_Umaya_HempRope` | pl_umaya | Surface | `Rope003` (low) | mesh UV |
| `MI_Umaya_TackLeather` | pl_umaya | Surface | `Leather014` (low) | mesh UV |
| `MI_Bugugura_ArmorChestLeather` | pl_bugugura | Surface | `Leather007` (low) | mesh UV |
| `MI_DojoSmithy_TakeKago` | pl_dojo_smithy | Surface | `Wicker013` (low) | mesh UV |
| `MI_Kakuredani_AsaSacking` | pl_kakuredani | Cloth | `hessian_230` (low) | mesh UV |
| `MI_Umaya_AsaHorseBlanket` | pl_umaya | Cloth | `hessian_380` (low) | mesh UV |
| `MI_Kakuredani_JinmakuSilk` | pl_kakuredani | Cloth | `crepe_satin` (low) | mesh UV |
| `MI_Kakuredani_PackWrapCloth` | pl_kakuredani | Cloth | `Fabric011` (low) | mesh UV |
| `MI_Umaya_ShitaguraPad` | pl_umaya | Cloth | `Fabric013` (low) | mesh UV |
| `MI_IssosekiWood_MossRockSet01` | pl_issoseki_wood | Surface | `rock_moss_set_01` | mesh UV |
| `MI_Ishibashi_MossRockSet02` | pl_ishibashi | Surface | `rock_moss_set_02` | mesh UV |
| `MI_IssosekiWood_Boulder01` | pl_issoseki_wood | Surface | `boulder_01` (low) | mesh UV |
| `MI_IssosekiWood_RootCluster01` | pl_issoseki_wood | Surface | `root_cluster_01` | mesh UV |
| `MI_IssosekiWood_TreeStump01` | pl_issoseki_wood | Surface | `tree_stump_01` (low) | mesh UV |
| `MI_IssosekiWood_MossClump01` | pl_issoseki_wood | Foliage | `moss_01` | mesh UV; opaque override |
| `MI_LanternWardRain_ChochinPaper` | pl_lantern_ward_rain | LanternPaper | `texturecan_paper_0017` (project) | mesh UV; 1900 K |
| `MI_EstateNight_AndonPaper` | pl_estate_night | LanternPaper | `texturecan_paper_0017` (project) | mesh UV; 2000 K |

The 29 evaluation instances are in `/Game/Generated/Environment/CC0/Evaluation`:

- one `MI_Eval_<Set>` for every imported set that no place instance binds;
- `MI_Eval_StackedStoneWall_MossJoints`.

## Scanned meshes

Each glTF node becomes its own static mesh, named `SM_<Asset>[_<Node>]`, for
example `SM_RockMossSet01_Rock01`. The importer writes a one-node glTF with an
embedded buffer to `Saved/CC0Environment/Gltf`, then imports it through
Interchange with these settings:

- static mesh only;
- Nanite on;
- the scanned normals kept;
- MikkTSpace tangents computed, as the maps were baked;
- no glTF materials or textures.

Each mesh's position offset within its set is dropped, so every rock keeps its
own pivot. The node scale is kept: `rock07` in set 02 is scaled by 0.679. The
validator checks each mesh's bounding box against the glTF's own accessor
extents times its scale, to 0.5%.

Every slot binds the instance built from that scan's own maps. The Mac preset
turns Nanite off (`Config/Mac/MacEngine.ini`), so the Mac renders Nanite's
fallback mesh. No conventional LOD chain has been authored.

## Presets for applying the library

`scripts/unreal/environment_presets.py` holds the data the next step needs to
apply the library. The game does not read it yet.

- `LIGHTING` has one preset per lighting state in the story bible's §16 table
  (overcast estate day, misty wood dawn, golden dusks, the fire-lit ch02 night,
  Lantern Ward dusk rain, the hazy village day, the furnace night, the new-moon
  citadel, the typhoon, the clear ch08 dawn and the festival night), and
  `ARENAS` maps each arena to one of them. Each preset gives the key light
  (kind, colour temperature, angle, intensity), a lighting-only HDRI where the
  ledger plans one for that chapter, exposure bias, fog, the
  `MPC_EnvironmentWeather` values, the lantern colour and the bible's Mac
  fallback. Only `estate_day` is `shipped`: it repeats the values
  `SoraWorldBuilderLighting.cpp` uses today, and a test holds the two
  together. Every other intensity is an unverified starting value to tune
  against captures.
- `SURFACES` names, for each story-bible place, the place instance for each
  surface role (floor, board wall, earthen wall, plaster, roof, ground, path,
  bark, straw, rope, leather, cloth, fence, lantern paper). The test runs the
  library's own `check_instance` with the instance moved to that place, so an
  instance is only reused where every ledger record it binds is planned. For
  example, `MI_EstateDay_Shikkui` cannot be used at the night estate until the
  ledger lists `Plaster007` there.
- `SCATTER` gives per-place densities, scale ranges and clearances for the
  scanned rocks, roots, stumps and moss. `scatter()` places them on a jittered
  grid seeded by SplitMix64 hashes. It returns integer centimetres, tenths of
  a degree and thousandths of scale, and it keeps clear of exclusion circles
  (spawns, objectives, and paths sampled by `path_exclusions`). Apart from
  each rule's grid cell size (a rounded square root of its density), its
  arithmetic is 64-bit integer, so a C++ port can reproduce it. The test pins
  an output digest.

`scripts/unreal/test_environment_presets.py` checks all of this with host-only
tests.

## Verification status

The following were run on 2026-09-26:

- the host tests: 16 library tests (including the master digest) and 15
  preset tests;
- the pack step and the host source check: 344 packages;
- the editor import: `SORA_CC0_ENVIRONMENT_READY: 344 packages`;
- the editor validator: `SORA_CC0_ENVIRONMENT_VALIDATED: 344 packages`, with
  220 textures, 7 masters, 47 place and 29 evaluation instances, and 34 meshes.

Each editor step ran on its own with the same flags that `import-mac.sh` uses,
in a `-nullrhi` editor. That editor translated the materials without errors
but compiled no shaders. The editor runs predate the master graph digest, so
the digest path (`SoraGraphSha256`, skipping unchanged masters) has run only
in the host test, not yet in the editor.

The following remain unverified:

- the full `import-mac.sh` run end to end with the new steps;
- actual Metal and D3D shader compilation of the Custom HLSL nodes;
- the rendered appearance of the dry and wet states and of the world-aligned
  normal frame;
- tiling at distance;
- Lumen response;
- cook inclusion;
- frame cost.

`scripts/unreal/render_cc0_environment_lookdev.py` renders fixed-camera dry
and wet captures of every instance and the distance views, and in doing so
compiles the shaders. It has not produced a capture, for lack of disk:

- The first attempt, at 32.4 GiB free, built the look-development level. The
  lane's own disk watchdog then stopped it when free space fell to 31.9 GiB:
  SIGTERM (logged as `Mac GracefulTerminationHandler`), then `kill -9` (exit
  137) because the busy editor kept running. That was while it built the
  imported textures' platform data, before any shader or screenshot.
- Before the second attempt, a review of the script found that it passed
  rotations to `unreal.Rotator` positionally, and the order is (roll, pitch,
  yaw). The cameras would have been rolled, not pitched down, so they would
  have missed the samples. The labels would have been upside down, and the
  sun would have pointed up. The script now names pitch and yaw. It also waits
  for each PNG from the image write queue and fails unless every capture is
  written afresh.
- The second attempt ran from 20:05 to 20:51 JST under a guard that suspends
  the editor (SIGSTOP) below 32 GiB free and resumes it at 32.5 GiB. Other
  jobs held free space at 29.0-33.2 GiB. The editor was suspended for 1,717
  of 2,723 seconds, loaded the level and began building textures. It was
  stopped after 15 minutes suspended in a row, before any shader compilation
  or screenshot.

The lane's disk watchdog also stopped an end-to-end `import-mac.sh` run at
31.9 GiB free, during its original-asset step. The next `import-mac.sh` run
imports that step's packages again.
