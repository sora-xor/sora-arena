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

**The library is never cooked.** The project always cooks `/Game/Generated`
(`DirectoriesToAlwaysCook` in `Config/DefaultGame.ini`), and the library lives
under it, so the same file also lists `/Game/Generated/Environment/CC0` under
`DirectoriesToNeverCook`. In UE 5.8 the never-cook list wins over every other
reason to cook a package (`FRequestCluster` suppresses it with
`ESuppressCookReason::NeverCook`). None of the library reaches a Mac or
Windows package: not the evaluation surfaces, the look-development HDRIs, the
look-development level, or the not-yet-admitted place instances. Its masters
are also never compiled by the cook, so they cannot fail it. An admitted
instance must leave this folder, or the exclusion must be narrowed, in the
same change that references it from a level. `test_cc0_environment_library.py`
fails if the exclusion is removed.

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
   and prints the package count the editor validator must match. The plan
   also loads `scripts/unreal/cc0_ao_ranks.json` (see
   [Height blend](#height-blend)) and refuses it if any measured source's
   SHA-256 has changed.
3. `scripts/unreal/check_cc0_custom_hlsl.py` compiles the masters' Custom HLSL
   on the host (see [Custom HLSL](#custom-hlsl)).
4. `import_cc0_environment.py` runs in the headless editor after the Nyaagyu
   palette import, because it binds the palette's plaster and stone-path maps.
5. `validate_cc0_environment.py` runs in the editor after the main validator.

The raw files stay read-only in the clone's `Local/ThirdPartyRaw/cc0`.
`cc0_environment_library.storage_root` finds that folder from a git worktree
through the worktree's `commondir`, so every worktree uses the one fetched
copy. If a file is missing, the import stops and names
`scripts/assets/fetch_cc0.py`.

Every imported texture, cubemap and mesh records its source SHA-256 as package
metadata. A source whose hash is unchanged is not imported again.

Material compilation is checked only where it can happen.
`import-mac.sh` runs the importer with `-nullrhi`. There,
`FApp::CanEverRender()` is false and no material resource is cached or
translated, so `MaterialEditingLibrary.recompile_material` has no errors to
return. The importer therefore compiles only in an editor with a renderer. In
that case every master and instance must yield a pixel shader for the
running shader platform (`get_statistics`) and report no compile errors. The
completion line says which case ran: `materials not compiled: null RHI`, or
`N materials compiled for this platform`.

Each master records `SoraGraphSha256`, the digest
`cc0_environment_library.master_graph_digest` takes of everything its graph is
built from: the importer, library and Custom HLSL source, the master's name
and the default maps it binds. The importer rebuilds a master only when that digest
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

The plan now has 345 packages, because `M_Env_Silk` has been added as an
eighth master. That count has not been imported yet (see
[Verification status](#verification-status)).

`scripts/unreal/test_cc0_environment_library.py` runs host-only tests. They
cover the period policy, the naming rules, the master digest, the Custom HLSL
wrapper, the cook exclusion, source sizes, the measured ranks and the ledger's
`used_by`.

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
power of two so that they keep mips and streaming. The importer and the
validator take the size from the source file's own header
(`cc0_environment_library.image_size`, for PNG, JPEG and OpenEXR). They do not
use `Texture2D.blueprint_get_size_x`. In an editor with a renderer, that call
returns the built size, which is already stretched (or its stand-in's size
while the texture compiles). The expected mode would then flip between runs
with and without a renderer. The source bytes are pinned by
`SoraSourceSha256`, so the source-derived expectation cannot drift.

## Masters

All masters are in `/Game/Generated/Environment/CC0/Materials`. All of them
are enabled for Nanite and instanced static meshes.

| Master | Use |
| --- | --- |
| `M_Env_Surface`, `M_Env_Surface_VT` | Opaque PBR with ARM. Switches between world-aligned projection and mesh UVs. Optional detail normal and macro variation. `_VT` samples virtual textures. |
| `M_Env_HeightBlend2`, `M_Env_HeightBlend2_VTBase` | Two-layer height blend of layer B over layer A (`_VTBase`: layer A is virtual). |
| `M_Env_Foliage` | Masked, two-sided `TwoSidedFoliage` with dithered LOD transition and opacity from ARM alpha. Instances may override to Opaque, as the moss clumps do. |
| `M_Env_Cloth` | Two-sided `Cloth` shading. Outputs go through material attributes because Python cannot reach the `CustomData0` cloth pin. |
| `M_Env_Silk` | Two-sided default-lit silk, with anisotropic sheen along the mesh tangent and a shot-silk hue shift (see [Silk](#silk)). |
| `M_Env_LanternPaper` | Two-sided lit paper with blackbody emission and flicker. |

The exact parameter names of each family are `FAMILY_PARAMETERS` in
`cc0_environment_library.py`. The validator compares them with the built
graphs.

### Custom HLSL

The eight Custom expressions (world projection, measured rank, projected
normal, detail normal, height blend, the shared finish, shot silk and lantern
emission) live in
`scripts/unreal/cc0_environment_hlsl.py`, each with its pins in order and the
type UE 5.8 gives each wired pin. A world or object position arrives as a
large-world value, which the translator passes as a demoted `float3` plus its
`FWSVector3`. The importer refuses to wire any other pins, and the editor
validator checks that every master holds exactly the expected nodes with the
module's code and pins.

`check_cc0_custom_hlsl.py` wraps each node as
`FHLSLMaterialTranslator::CustomExpression` does, calls all six from one pixel
shader and compiles it with the pinned engine's `libdxcompiler` for SPIR-V
(the front end of the Metal and Vulkan paths) and DXIL (D3D12), under HLSL
2018 and 2021. A deliberately broken node must fail first, so the check cannot
pass on a compiler that accepts everything. This covers the hand-written HLSL
and its pin types only. The rest of each material is generated by the engine
and compiles only when an editor with a renderer, or a cook, builds the
shader maps. D3D11's FXC and Apple's Metal compiler are not run.

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

Mesh-UV mode is required for sets that hold discrete units
(`MESH_UV_ONLY`). The policy rejects a world-aligned instance of one. The
tatami texture holds two 90 x 180 cm mats per 180 cm tile, with heri on the
long edges only, and its short ends tile seamlessly. World projection turns
every mat into an endless strip along world X, with no mat ends and a single
orientation. `MI_EstateDay_Tatami` therefore uses mesh UVs. A mat mesh lays U
along its 180 cm length and V across its width, so that `UVScale` (1, 0.5)
maps it to one mat. Each mat can then be turned, as the 4.5-mat tea room
(b14) needs.

### Height blend

Layer A's ambient occlusion is the height proxy. With `HeightFromCrevices` at
1, layer B fills the crevices first; with it at 0, layer B covers the peaks.

The blend thresholds the AO's **rank**, not its value. Scanned AO maps sit in
narrow bands that differ from scan to scan:

- `white_plaster_02`: 99% above 0.40;
- `grey_stone_path`: 99% above 0.57;
- `riet_01`: between 0.44 and 0.64;
- `clay_plaster`: around 0.97.

An absolute threshold that shows one scan's crevices shows none or all of
another. The first tuning did exactly that. Measured on the real maps, it put
no Plaster007 on the shikkui, no moss in the roji joints and no moss on the
thatch, and it covered 99.98% of the charcoal-hut daub with
`patterned_clay_plaster`. That record is allowed only as a masked breakup.

`scripts/unreal/measure_cc0_ao.py` (a host tool) measures each ranked layer
A's AO at full resolution, as the linear values Unreal samples. It stores
4096-bin histograms and the AO value at eight fixed ranks in
`scripts/unreal/cc0_ao_ranks.json`. The measure-rank Custom node turns a
sampled AO value back into its rank along that piecewise-linear curve. The
instance binds its scan's knots as `AOKnotsLo` and `AOKnotsHi`. The master's
defaults are the identity curve.

Layer B covers the share `LayerBCoverage` of the surface whatever the scan's
band, less vertex red when `VertexColorBlend` is 1, plus `TopFacingBias`
times the upward normal. `BlendContrast` sets the edge width in rank units.
The test evaluates the exact HLSL on the stored histograms, and every
instance is within 0.03 of its coverage:

| Instance | Layer B | Coverage asked | Measured |
| --- | --- | --- | --- |
| `MI_EstateDay_Shikkui` | Plaster007 cracks and stains in the most occluded plaster | 0.10 | 0.088 |
| `MI_EstateDay_RojiStonePath` | Moss002 in the granite joints | 0.25 | 0.222 |
| `MI_Kakuredani_CharcoalHutDaub` | patterned clay on the raised daub | 0.18 | 0.175 |
| `MI_IssosekiWood_MossForestFloor` | Moss001 on the raised forest floor | 0.40 | 0.417 |
| `MI_Kakuredani_MossyThatch` | Moss004 between the reeds (0.35 on flat tops) | 0.20 | 0.186 |
| `MI_Eval_StackedStoneWall_MossJoints` | Moss003 over the mortar joints | 0.30 | 0.301 |

Overlays of the exact mask on the diffuse maps confirmed the placement:

- the roji moss fills the joints between the stones;
- the daub pattern follows a cellular network in the clay's relief;
- the shikkui stains fall in clusters where the plaster is more occluded.

`riet_01`'s AO darkens toward the top of its 2.5 m tile. The thatch moss
therefore gathers in bands that repeat with the tile. The distance view has
to judge whether that reads as repetition.

A medium-risk breakup layer may cover at most `MAX_BREAKUP_COVERAGE` (0.3)
of the surface, counting `TopFacingBias`. The policy rejects more.

Height blends fade with distance. Coarser mips average the AO toward its
median, so the tails that thresholds select thin out.

Each layer has its own tile size and roughness range: `LayerBTileSizeCm`,
`LayerBRoughnessMin`/`Max`, and `LayerBTint`.

### Weather

`MPC_EnvironmentWeather` holds these scalars:

| Scalar | Default |
| --- | --- |
| `Wetness` | 0 |
| `PuddleAmount` | 0 |
| `LanternIntensity` | 1 |

No game code sets them yet. Nothing under `Source/` references the
collection, so every level renders at the defaults, dry and without
puddles. Only `render_cc0_environment_lookdev.py` changes them, for its wet
captures. `environment_presets.LIGHTING` holds the values each lighting
state should set. For example, the ch03 dusk rain holds `Wetness` 1 and
`PuddleAmount` 0.8. Driving the collection from the world builder or the
weather code is part of adopting the library.

Each instance scales the rain through `WetnessResponse`. Sheltered interiors
such as the dojo floor and tatami use 0; open stone, timber and bark use 1.
`BaseWetness` keeps stream beds damp in dry weather.

A wet surface changes in three ways, following story bible §15.1:

- its albedo darkens by `WetDarkening`;
- its roughness falls toward `WetRoughness`;
- vertical and overhanging faces take about 65% of the wetting that floors take.

On world-aligned masters, `PuddleResponse` lets puddles collect as
`PuddleAmount` rises. Puddles form only on flat faces (normal Z above 0.85).
They fill the lowest share of the ground, and the edge is still graded by
rank. Lowness is 0.7 of the macro-variation rank, the metre-scale hollows,
plus 0.3 of layer A's AO rank, the crevices. The macro rank uses constants
measured from the engine's own `T_Default_MacroVariation` (sRGB). Its source
PNG is read out of the pinned engine package, and the two channels the finish
node averages are convolved. At `PuddleAmount` × `PuddleResponse` 0 there are
no puddles. Puddles flatten the normal and bring roughness down to 0.04.

The first formula thresholded raw AO and macro values. Measured on the
packed-earth road, it flooded every flat pixel from `PuddleAmount` 0.7
upward. With the ranks, the road's flat share in puddles at `PuddleResponse`
1 is:

| `PuddleAmount` | 0 | 0.3 | 0.5 | 0.7 (look-dev wet) | 0.8 (ch03 rain) | 1.0 |
| --- | --- | --- | --- | --- | --- | --- |
| Road share in puddles | 0 | 1% | 6% | 15% | 21% | 35% |

The test holds these bands, and it fails if any instance floods more than
40% of flat ground at `PuddleAmount` 1. A top-down simulation of 8 m and
20 m of road draws the real AO tile and the engine macro texture at 13 m and
47 m. In it, puddles gather in the macro's dark blobs as ragged pools of
roughly 20 to 100 cm, with edges roughened by the AO. That shape has not been
checked in a render.

### Silk

Story bible §15.1 asks silk for anisotropic sheen and a shot-silk hue shift
for the nobori. The ledger admits `crepe_satin` for exactly that. The Cloth
shading model has no anisotropy, so `M_Env_Silk` is default-lit. `Anisotropy`
drives the engine's anisotropic BRDF along the mesh tangent, so a silk mesh
lays its warp along U. The BRDF runs where `r.AnisotropicMaterials` is on:
engine shading quality High and above, which Metal SM6 supports. The
shot-silk Custom node shifts the graded colour toward `ShotColor` at
unchanged luminance. The shift grows where the view runs along the warp and
toward grazing angles, scaled by `ShotAmount`. `MI_Kakuredani_JinmakuSilk`
uses Anisotropy 0.7 and a warm weft at ShotAmount 0.25. Neither has been seen
rendered.

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

A place instance may bind a record only at a place its `game_use` lists for
direct use. An entry that names the record only as the input of an authored
asset does not count, for example Rope001 as the "base for authored straw
rope" of the One-Claw Stone's 注連縄.

**Medium risk.** A medium-risk record may only fill the role its flag names:

| Record | Allowed role |
| --- | --- |
| `patterned_clay_plaster` | Breakup layer B, under `clay_plaster`, covering at most 30% |
| `Plaster007` | Breakup layer B (crack and spall), covering at most 30% |
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
| `MI_EstateDay_Tatami` | pl_estate_day | Surface | `tatami_mat` (low) | mesh UV; one mat per UV square |
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
| `MI_Kakuredani_JinmakuSilk` | pl_kakuredani | Silk | `crepe_satin` (low) | mesh UV; warp along U |
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
  ledger lists `Plaster007` there. The One-Claw Stone Wood's rope is the split
  boulder's 注連縄. That is left-laid rice straw, and Rope001's flag reserves
  Rope001 for hemp lashings. So `SURFACES` gives the wood no rope, and
  `UNFILLED` records the shimenawa as authored art still to make.
- `SCATTER` gives per-place densities, scale ranges and clearances for the
  scanned rocks, roots, stumps and moss. `scatter()` places them on a jittered
  grid seeded by SplitMix64 hashes. It returns integer centimetres, tenths of
  a degree and thousandths of scale, and it keeps clear of exclusion circles
  (spawns, objectives, and paths sampled by `path_exclusions`).
- The moss scans are single sprigs 0.9 to 3.7 cm across (measured from the
  glTF accessors). Scattered one per cell they would be invisible specks, so
  the moss rules are cluster rules, where each placement is a cushion:
  - in the wood, 24 to 48 sprigs within 9 cm, 25 cushions per 100 m²;
  - by the road, 20 to 36 sprigs within 7 cm, 8 per 100 m².

  A test checks that the sprigs' footprints cover at least 40% of a cushion.
  The carpet between cushions is the wood floor's Moss001 layer. Ferns are
  not in this library.
- Apart from each rule's grid cell size (a rounded square root of its
  density), the scatter arithmetic is 64-bit integer. Every division and
  remainder has non-negative operands, so C++ `/` and `%`, which truncate,
  agree with Python's, which floor. `path_exclusions` divides a segment's
  magnitude and restores the sign. A test compares it with truncating
  division on paths toward -x and -y and checks its mirror symmetry. A C++
  port can therefore reproduce the scatter. The tests pin digests of a plain
  rule and a cluster rule, the latter along a path toward -x and -y.

`scripts/unreal/test_environment_presets.py` checks all of this with host-only
tests.

## License ledger

Every third-party file the library imports has a schema-2 record. Each
record's `used_by` lists the /Game packages built from that record or binding
it: its textures, cubemaps and meshes, and every instance that binds it.
`scripts/unreal/record_cc0_ledger_uses.py` writes these lists from the plan.
It replaces only the entries under `/Game/Generated/Environment/CC0` and
keeps the others, such as the palette's own instances. The library test fails
when a ledger and the plan differ. The script covers these ledgers:

- the two first-slice ledgers;
- the Poly Haven palette extension, where `white_plaster_02` also feeds
  `MI_EstateDay_Shikkui`;
- `Content/SourceArt/Environment/ShojiPaperArtReview/manifest.ledger.json`.

That last file is a schema-2 extension of the shoji paper study's schema-1
manifest. It records the four unaltered TextureCan Paper 0017 maps the lantern
instances import. Its license evidence is a snapshot of TextureCan's terms,
retrieved on 2026-09-26 UTC and stored in the clone's
`Local/ThirdPartyRaw/_licenses/texturecan`. The terms state "All the PBR
textures ... offered by TextureCan.com are under the Creative Commons CC0 1.0
Universe License". The study's own manifest stays byte-identical, and its
"no runtime/UE import" status still describes the Blender study.

Two library origins have no schema-2 record to write to:

- `grey_stone_path` is covered only by the terrain lane's schema-1
  `NyaagyuTerrain` manifest, and `MI_EstateDay_RojiStonePath` binds it;
- the ibushi atlas is project-owned.

The library's packages are never cooked, so today `used_by` names editor
packages, not shipped ones.

## Verification status

### 2026-09-27 review fixes

Run on the host, in the worktree:

- `test_cc0_environment_library.py`: 35 tests OK.
- `test_environment_presets.py`: 20 tests OK.
- `pack_cc0_environment.py`: `SORA_CC0_PACK_COMPLETE: 33 ARM maps (0 written, 33 unchanged)`.
- `validate_cc0_environment.py --source-only`: `SORA_CC0_SOURCE_CHECK_COMPLETE: 345 expected Unreal packages`.
- `check_cc0_custom_hlsl.py`: `SORA_CC0_HLSL_COMPILED: 8 Custom expressions` as SPIR-V and DXIL under HLSL 2018 and 2021, with no compiler messages.
- `measure_cc0_ao.py`: 9 sets and the macro variation.
- `record_cc0_ledger_uses.py`: 79 records in 4 ledgers.
- `scripts/assets/validate_asset_ledger.py`: `LEDGER_OK`, 0 errors, schema-2 coverage 249.
- `scripts/unreal/validate_content.py`: passed.

Two mutations confirmed that the new tests catch regressions. Removing the
`DirectoriesToNeverCook` line fails the cook test. Setting `PUDDLE_REACH`
to 1.2 fails the puddle test at 55% puddles for `PuddleAmount` 0.5.

The importer's graph and instance code also ran on the host once, against a
stub `unreal` module. The stub checked every Custom node's pin order, every
expression pin and output name the code wires, and each master's parameter
names against `FAMILY_PARAMETERS`. All 8 masters and 76 instances built, and
10 instances bound measured AO knots. That run found and fixed one bug: the
silk master sampled no macro variation. It proves nothing about the engine:
the stub accepts any material property.

**Not run: every editor step.** Free disk was 22 to 25 GiB, below the 32 GiB
floor for heavy work. So the new graphs (the rank node, the rank-based blend
and puddles, `M_Env_Silk` with `MP_Anisotropy`), the source-size texture
settings and the 345-package validation have not run in the pinned editor.
The next `import-mac.sh` rebuilds all eight masters, because the graph digest
changed. It also imports `M_Env_Silk` and rebinds the instances. Until then,
the imported packages under `Content/Generated/Environment/CC0` are the
2026-09-26 build and fail the validator's digest check. Not verified either:

- rendered appearance (puddle shapes, the silk sheen, the tatami mats on the
  engine cube);
- a cook run showing the library excluded;
- frame cost, including the moss cushions' instance counts.

### 2026-09-26

The following were run on 2026-09-26:

- the host tests: 19 library tests (including the master digest and the
  Custom HLSL wrapper) and 15 preset tests;
- the pack step and the host source check: 344 packages;
- the host Custom HLSL check: `SORA_CC0_HLSL_COMPILED: 6 Custom expressions`
  as SPIR-V and DXIL under HLSL 2018 and 2021, with no compiler messages;
- the editor import: `SORA_CC0_ENVIRONMENT_READY: 344 packages`;
- the editor validator: `SORA_CC0_ENVIRONMENT_VALIDATED: 344 packages`, with
  220 textures, 7 masters, 47 place and 29 evaluation instances, and 34 meshes.

Each editor step ran on its own with the same flags that `import-mac.sh` uses,
in a `-nullrhi` editor. A null-RHI editor caches no material resources
(`UMaterial::CacheResourceShadersForRendering` does nothing unless
`FApp::CanEverRender()`), so those runs neither translated the graphs to HLSL
nor compiled shaders, and the importer's `recompile_material` error check had
nothing to report; their logs show no material compilation. They show that
the graphs were built, saved and bound as the validator reads them, not that
they compile. The editor runs also predate the master graph digest and the
Custom HLSL module, so the digest path (`SoraGraphSha256`, skipping unchanged
masters) and the validator's Custom-node check have run only on the host.

The following remain unverified:

- the full `import-mac.sh` run end to end with the new steps;
- shader compilation of the whole materials on any platform (only their
  Custom HLSL has been compiled, on the host, and not by FXC or Apple's Metal
  compiler);
- the rendered appearance of the dry and wet states and of the world-aligned
  normal frame;
- tiling at distance;
- Lumen response;
- frame cost.

Cook inclusion was listed here as unverified. It was in fact automatic,
because `/Game/Generated` is always cooked. The library is now excluded (see
the top of this document).

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
- That attempt's log also shows a handled editor ensure, `No realtime override
  was found with Level Editor Subsystem Realtime Override`, from the script's
  `editor_set_viewport_realtime(True)`. In 5.8 that call only removes an
  override that a `False` call added, so it never turned realtime on. The
  script now invalidates the level viewport on every tick instead, so each
  tick draws a frame and Lumen and TSR accumulate during the capture delay.
  With the `unreal` module mocked, the script's Python ran on the host through
  scene building (179 asset loads, 187 actors, 15 camera views) to its first
  capture request. That dry run was a one-off and says nothing about
  rendering.

The lane's disk watchdog also stopped an end-to-end `import-mac.sh` run at
31.9 GiB free, during its original-asset step. The next `import-mac.sh` run
imports that step's packages again.
