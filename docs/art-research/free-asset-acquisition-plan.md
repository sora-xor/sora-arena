# Free asset acquisition plan

**Date:** 2026-09-25. **Status:** plan only. This plan downloaded nothing into the repository.

This plan merges four sourcing reports written on the same day:
- environment, terrain, foliage and materials;
- characters, animals and animation;
- historical arms, armor, clothing, tack and sci-fi kits;
- audio.

It checks their claims against the repository, the [story bible](../campaign/story-bible.md), chapters [1](../campaign/chapter-01.md) and [2](../campaign/chapter-02.md), and this Mac. Section 8 lists every claim that is still unverified.

**Binding rules this plan works within:**
- **Photoreal is non-negotiable** (user directives 11, 13, 14 and 17). Free assets are allowed only where their licenses allow it. Otherwise the project makes the art.
- **Don't delete anything, and run one heavy job at a time** (directive 18).
- **No paid software, assets or services.** Record every license, and keep restricted-redistribution assets out of publicly distributable repositories (approved plan §2).
- **Free assets are inputs to the [photoreal acceptance](../art-direction/photoreal-acceptance.md) gate, never a pass.** Every asset still needs a packaged A/B comparison, a recorded license and a measured frame cost before it enters the game.

## Summary

- **Only CC0 and public-domain material is free to commit.** It can go into the Apache-2.0 repository with no conditions. CC BY material can be committed once its credit is recorded. Everything else goes in gitignored folders or is not used.
- **Poly Haven and ambientCG (both CC0) cover most Japanese surfaces the Estate and chapters 1–2 need.** Agents can fetch them without a login, and the project already has a fetch and pinning flow for them.
- **The biggest photoreal gaps have no free source.** These are:
  - whole sugi and hinoki trees;
  - a hero-quality cat face;
  - native Japanese horses;
  - Edo tōsei-gusoku armor;
  - historical kenjutsu, kyūdō, yari and naginata motion;
  - photoreal alien hardware.

  All of them have to be made in-house. Free sources supply references, surfaces and anatomy for that work.
- **Epic and Fab content has a clause that may block agent handling.** Every Epic sample the reports could check is flagged "Allows usage with AI: No". Until the user decides how to read that clause (decision D1), Fab and Epic content stays outside the agent workflow.
- **Several items need the user to log in once:** Sketchfab (with an Epic account), Freesound (OAuth), Fab, and JAXA registration. Section 4.2 gives the exact steps. Sketchfab is time-sensitive, because free licensing there may be removed.
- **Disk:** 81 GiB is free now, and nothing may be deleted. The core first-slice set needs about 12–14 GiB. The first-slice acquisition cap is 20 GiB, which keeps at least 30 GiB free for builds and cooks.

## 1. What was checked for this plan

- **Disk and repository:**
  - `df` shows 81 GiB free on `/System/Volumes/Data` (99% used).
  - `.git/lfs` is 4.7 GB and `Content/SourceArt` is 2.5 GB.
  - `.gitattributes` sends these file types to LFS: `uasset umap blend fbx glb wav exr png tga jpg jpeg hdr tif otf`, plus two specific Poly Haven `Upstream/*.bin` paths. It does not cover `ogg`, `flac`, general `bin`, `usd*` or `abc`.
- **Gitignored paths** (confirmed with `git check-ignore`):
  - Ignored: `/Local/` (.gitignore line 82), `/Content/ThirdPartyRestricted/` (line 84), `Content/Generated/` and `Content/ArtReview/`.
  - **Not ignored:** `Content/Fab/`.
- **The existing CC0 flow:**
  - [`scripts/art/fetch_polyhaven_palette.py`](../../scripts/art/fetch_polyhaven_palette.py) sends a unique User-Agent, allows only Poly Haven's download hosts, checks the upstream MD5, and writes SHA-256 hashes to a schema-1 [manifest](../../Content/SourceArt/Environment/PolyHaven/manifest.json) with a `NOTICE.txt`.
  - The manifests reference 17 distinct Poly Haven assets; with the docs included, 20. The environment report said 18.
- **Real file sizes in the repo.** These are larger than the report estimates, because the flow stores PNG normal and ARM maps:
  - Poly Haven 2K texture sets: 11–47 MB.
  - A 4K set: 74 MB.
  - A 4K puresky HDRI: 17 MB.
- **Poly Haven IDs:** every ID named in this plan exists in the asset index fetched 2026-09-25.
- **Objaverse mirror.** I checked the Sketchfab UIDs against the Objaverse 1.0 object-path index:
  - **Present:** the Edinburgh cat CT, both RISD cat skulls, the MRI PAS skull, the westerly skeleton, the Edinburgh horse CT, the Luján skeleton, the Stabel horse, the giravolt do-maru, the kokutochi yoroi, and the Neo_minigan and elaughli cats.
  - **Absent, so they need a Sketchfab login:** the Paul Sabatier cat forelimb and horse hind limb, the adrianocanotto ō-yoroi, snacksthecat's cat face, and the Osaka castle ishigaki.
  - The creatureanimator horse walk (CC BY-ND) is in Objaverse, but mirror availability does not change its no-derivatives license.
- **This Mac:**
  - Apple **M1 Ultra**, 128 GiB.
  - Blender 5.2.2 LTS.
  - **GarageBand 10.4.14 is installed**, with about 0.9 GB of loops. The audio report said it was not installed.
  - `sox` and `ffmpeg` are not installed.
- **Setting.** The story bible sets the game in 1623 (元和九年), with early-17th-century material culture. Several period flags below follow from that date.

## 2. License ledger policy

### 2.1 Tiers

| Tier | Licenses | Where files live | Committed? | Obligations |
|---|---|---|---|---|
| **PUB-CC0** | CC0 1.0, the Public Domain Mark, US public domain (for example Muybridge's 1887 plates), and museum open-access records marked CC0 | `Content/SourceArt/<area>/<source>/` (LFS) | Yes | Keep a ledger record. Keep "Powered by Poly Haven", because our scripts use its API. |
| **PUB-PD with conditions** | NASA media | `Content/SourceArt/...` | Yes | No NASA insignia, logotype or seal, and nothing that implies endorsement |
| **PUB-BY** | CC BY 3.0/4.0, OGA-BY 3.0/4.0, and ColBase's Government Standard Terms of Use 2.0 (compatible with CC BY 4.0) | Derived art in `Content/SourceArt`. Raw scans in `Local/ThirdPartyRaw/`, following the existing [cat-scan policy](nyaakoto-real-cat-scan-acquisition.md) | Derived art only | Creator, source URL, license URL and a statement of changes, in NOTICE and in the in-game credits |
| **OWN** | Project work: generator scripts, our own recordings, and our own mocap under a signed performer release | `Content/SourceArt/...` | Yes | Record the generator script, or the session and release ID |
| **RST** | Commercial use allowed but no standalone redistribution, or UE-only: Fab Standard License, Epic Content License, UE-EULA template content, Sonniss, Mixamo, Pixabay, Mixkit, 効果音ラボ, OpenTracks, 魔王魂 (treated as RST because its site rules conflict with its CC label), and the raw CMU library | Raw files in `Local/ThirdPartyRaw/<source>/`. Imported UE packages in `Content/ThirdPartyRestricted/<source>/` | **Never** | Ships only inside cooked, packed builds. Needs a PUB or OWN fallback so a public clone still builds |
| **REF** | Viewed, never shipped: museum photos (lighting is baked in), measurement text from records that are not open access, CC BY-ND and CC BY-SA items, raw Unsplash and Pexels photos, a local look at Sensei Terrain | `Local/Reference/<topic>/` | Never. Only the ledger record and the numbers we extract | The measurements, drawings and derived textures we produce are OWN |
| **EXCL** | Non-commercial, no-derivatives (for use in the game), research-only, paid, or unclear rights | Nowhere | — | Section 9 lists them |

### 2.2 Per-asset record

Every acquired file gets a record in the `manifest.json` next to it. The existing Poly Haven schema-1 fields stay: `asset_id`, `name`, `role`, `resolution`, `asset_url`, `metadata_url`, `license`, `license_url`, `legal_code_url`, `authors`, and `files[]` with `url`/`file`/`bytes`/`upstream_md5`/`sha256`.

Schema 2 adds the fields below. Migrate the existing manifests in one pass rather than keeping two formats, in line with the README's no-legacy rule.

```json
{
  "tier": "PUB-CC0 | PUB-PD | PUB-BY | OWN | RST | REF",
  "origin_url": "creator's page (Sketchfab listing, museum record, Fab listing)",
  "mirror_url": "Objaverse or other mirror actually downloaded from, or null",
  "commercial_use": true,
  "redistribution": "unrestricted | attribution | no-standalone | none",
  "derivatives": true,
  "platform_restriction": null,
  "ai_terms": "none | no-training | no-genai-input | written-permission | unknown",
  "agent_handling": "allowed | forbidden",
  "attribution_text": "required for PUB-BY and ColBase",
  "changes": "what we changed (required for CC BY)",
  "license_snapshot": {"path": "Local/ThirdPartyRaw/_licenses/<source>-<date>.pdf", "sha256": "..."},
  "access": "direct | api | login:sketchfab | login:freesound | login:epic | registration:jaxa",
  "acquired_at_utc": "...",
  "acquired_by": "agent | user",
  "storage": "repo-lfs | local-private | ue-restricted",
  "used_by": ["/Game/... runtime paths"],
  "fallback": "asset_id of the PUB/OWN substitute (required when tier is RST)"
}
```

**License snapshots:**
- Snapshots of terms pages stay private, because the page text is itself copyrighted.
- The committed record holds the snapshot's URL, date and SHA-256.
- When an agent reads terms through Wayback or a search index, the record says so (see section 8).

### 2.3 Attribution outputs

- **Generated files.** A generated `ThirdPartyNotices/ASSETS.md` and the in-game credits screen (lane L4) both read the ledger, so they cannot drift apart.
- **CC BY credit format:** "Title" by Author, source link, license link, and the changes made.
- **ColBase credit:** `出典：ColBase（https://colbase.nich.go.jp/）`. Add `…を加工して作成` when the image has been edited.
- **JAXA DEM credit:** `©JAXA`.
- **CMU mocap:** add the CMU acknowledgment (NSF EIA-0196217) to the credits. CMU requests it for publications; we include it voluntarily.
- **Other motion-data credits:** 100STYLE (Mason, Starke, Komura) and EMM (Ponton, Andújar, Pelechano, Andrews).

### 2.4 Restricted content: reproducible without being committed

- **Committed manifests.** `scripts/assets/restricted/<source>.json` (new) lists, for each restricted item:
  - the listing URL;
  - the license and its flags;
  - the entitlement owner;
  - the expected download SHA-256s and the imported package paths.

  The files themselves are never committed.
- **Checker script.** `scripts/assets/check_restricted.py` (new) verifies that the files are present and their hashes match. For anything missing, it prints the exact manual steps from section 4.2. It never downloads anything that sits behind a login.
- **Sonniss** needs no login, so a fetch script can reproduce it for each teammate. Its license forbids passing files to "any other person", so each person downloads their own copy.
- **Fab-plugin trap.** Before any Fab import, point the plugin's import location at `/Game/ThirdPartyRestricted/Fab/`. `Content/Fab/` is **not** gitignored today, so either add it to `.gitignore` or have the validator fail on it. The plugin's default path has not been verified.

### 2.5 Validator rules

`scripts/assets/validate_asset_ledger.py` is new. Lane L5's `validate_audio.py` applies the same rules to audio. The validator fails when any of these holds:

1. A tracked binary under `Content/SourceArt` has neither a PUB ledger record nor an OWN generator record.
2. A tracked path lies under `Local/`, `Content/ThirdPartyRestricted/` or `Content/Fab/`, or has an RST, REF or EXCL record.
3. A license is outside the allowlist. The allowlist is: CC0-1.0, PDM, US-PD, NASA-media, CC-BY-3.0, CC-BY-4.0, OGA-BY-3.0, OGA-BY-4.0 and JP-GSToU-2.0. Anything NC, ND, SA or GPL is rejected for asset content.
4. A PUB-BY record lacks `attribution_text` or `changes`.
5. A file's SHA-256 does not match its record.
6. A runtime asset depends on RST content and declares no `fallback`. A "public clone" check hides `Content/ThirdPartyRestricted` and runs the packaged smoke test.
7. An agent-run import script touches a record marked `agent_handling: forbidden`.

**LFS patterns.** Add `*.ogg`, `*.flac`, `*.bin`, `*.usd`, `*.usdc`, `*.usdz` and `*.abc`. Never commit archives (`*.zip`, `*.7z`) or videos.

### 2.6 AI-use terms

**Epic and Fab:**
- Epic Content License §17 and Fab's per-listing flag "Allows usage with AI: No" forbid using that content "as inputs to Generative AI Programs". The terms were read from a Wayback snapshot.
- Agents importing those files, or reviewing screenshots that contain them, could fall under that clause.
- Six Epic samples were checked and all six carry the flag: Electric Dreams, Valley of the Ancient, Project Titan, Lyra, Cropout and City Sample Vehicles.
- **Not checked:** Megaplants, the Game Animation Sample Project (GASP), Paragon, and the UE template content.

**Other sources:**
- **Ban AI training:** Sonniss, 効果音ラボ and OpenTracks. MetaHuman bans using it to train AI.
- **Bans feeding its music into AI composition:** 魔王魂.
- **Needs written permission for any AI use:** MoCap Online.
- **Terms not checked:** Adobe (Mixamo), Rokoko and ActorCore.

**Default until the user decides D1 (section 7):**
- Every Epic or Fab item is `agent_handling: forbidden` unless its listing shows AI usage allowed.
- Sources that ban training stay agent-handled, but no ML step, such as stem separation, denoising models or training, may ever process them.

## 3. Recommended sources by need

Within each table, rows are ranked by photoreal value among sources that are safe to use. Restricted sources appear only where they beat every public option, and only with a fallback.

**Access codes:**
- **A:** an agent can fetch it with no login.
- **U:** the user must log in or register once.
- **H:** a human must do it.

### 3.1 Architecture and building surfaces

This covers the dojo interior and yard, stable, smithy, armory yard, nagaya gate, tea hut, lane kit and stone bridge.

| # | Source | Tier | Access | What to take, and limits |
|---|---|---|---|---|
| 1 | [Poly Haven](https://polyhaven.com/license) textures | PUB-CC0 | A | See the list below the table. |
| 2 | [ambientCG](https://docs.ambientcg.com/license/) | PUB-CC0 | A | See the list below the table. |
| 3 | Project generators (`scripts/art/create_nyaagyu_*.py`) | OWN | A | Every building and set piece. Free sources provide surfaces, not buildings. |
| 4 | Sketchfab CC BY scans | PUB-BY | U | See the list below the table. |
| 5 | Sketchfab CC0 museum scans | PUB-CC0 | U | See the list below the table. |
| ref | ColBase, National Diet Library, Met photos | REF | A | Construction and proportion only. Not textures: the lighting is baked in. |

**1. Poly Haven textures:**
- **Timber:**
  - `hinoki_planks` for the dojo floor. The scan is knotty; check it against a clear-grain floor.
  - `japanese_cedar_planks` for 羽目板 panelling and sheds.
  - `roof_planks` for plank-roofed sheds.
- **Walls:**
  - `clay_plaster` and `patterned_clay_plaster` for 土壁; the existing `white_plaster_02` for 漆喰.
  - `wood_inlaid_stone_wall`.
  - `stacked_stone_wall` and `mossy_stone_wall` for retaining walls and plinths.
  - `japanese_stone_wall` and `granite_wall` for the stone bridge. Poly Haven describes both with "deep mortar joints", but ishigaki and dry-stone walls are laid without mortar, so check them before use.
- **Roofs:** `thatch_roof_angled`, `reed_roof_03`/`04` and `riet_01` for the thatched stable and farmhouses.
- **Other:**
  - `bamboo_wall_02`/`03` for fences.
  - `tatami_mat` for the tea hut and main house.
  - `lacquered_cherry_wood` as the urushi base.

**2. ambientCG:**
- `Plaster001–007`.
- `Bamboo001/002`.
- `Rope001–003` for shimenawa and lashings.
- `RoofingTiles011–015`: compare them with the existing ibushi kawara maps first.
- `Paper` for washi (`Paper001` is already used in the shōji study).
- Wicker and `ThatchedRoof` for straw targets, 叺 straw sacks and umagutsu.

**4. Sketchfab CC BY scans:**
- the tōrō lantern by Yu;
- the oni-gawara by jishtk;
- the Kokugakuin University Museum round eaves-end tile, as a reference for the SORA eave cap;
- the Kinosaki torii;
- the komainu scans.

**5. Sketchfab CC0 museum scans.** These are mostly for later chapters (the ch3 ward and the ch8 festival), and all need decimation or retopology before Nanite import:
- the Cleveland Museum of Art mikoshi (1968.214), jūbako (1989.5), and Nio and Zuishin figures;
- the Minneapolis Institute of Art Musashi Plains byōbu.

### 3.2 Terrain, rock, ground and water

| # | Source | Tier | Access | What to take, and limits |
|---|---|---|---|---|
| 1 | Poly Haven ground textures | PUB-CC0 | A | `forest_ground_04/05/06`, `muddy_tracks`, `river_small_rocks`. The existing `brown_mud_leaves_01`, `gravel_ground_01` and `grey_stone_path` stay. Edo streets are packed earth (story bible §15.1). |
| 2 | Poly Haven models | PUB-CC0 | A | `rock_moss_set_01/02`, `boulder_01`, `root_cluster_01`, `moss_01`, `tree_stump_01`, at 2K. The existing `ScanRock01` and `MossyRock` are the base for the stone bridge, as the chapter 2 plan already says. |
| 3 | ambientCG | PUB-CC0 | A | `Moss001–004`, plus a few ground and gravel sets where Poly Haven has gaps |
| 4 | Our own Mesh Terrain master material | OWN | A | Slope layers, cell bombing, distance blending and triplanar mapping on CC0 textures. These are standard techniques, so nothing needs licensing. It replaces Sensei Terrain (see [mesh-terrain-nyaagyu.md](../mesh-terrain-nyaagyu.md)). |
| 5 | [JAXA AW3D30](https://www.eorc.jaxa.jp/ALOS/en/dataset/aw3d30/) 30 m DEM | PUB-BY-like (`©JAXA`) | U | Macro landform for `pl_kaido`, the valley vistas and later `pl_shimomura`. Skip the GSI 5 m DEM: it may need an application under the Survey Act. |
| 6 | Sketchfab CC BY ishigaki scans (Osaka castle, 189k faces; Obama castle, 695k faces) | PUB-BY | U | Arena 3 ramparts (ch6). Acquire early anyway, because Sketchfab licensing may change. |
| ref | Sensei Terrain | REF, human only | U | Local evaluation only. Its site terms give a personal, non-transferable license with no product license, so it is never committed or shipped. A forum thread (Sept 2026) reports flat results and tiling problems. |
| engine | `MeshPartition`, `MeshTerrainMode`, `PCGMeshPartitionInterop`, `MeshPartitionWater`, `PCGBiome*` | UE EULA | installed | Referenced from the engine, never copied. All are Experimental, and support on the Mac tier is unverified. |

### 3.3 Trees and foliage (the largest photoreal gap)

**Needed:**
- sugi and hinoki (three growth stages);
- akamatsu and kuromatsu pines;
- keyaki (zelkova), yamazakura and momiji;
- madake or hachiku bamboo;
- kuma-zasa, tea hedges, moss, ferns and wisteria;
- willows for the ch2 bridge.

**Period constraints (from the environment report, not independently verified):**
- Mōsō bamboo arrived in 1736, and Somei-Yoshino is a late-Edo cultivar. Both are wrong for 1623.
- Fab's "Giant Bamboo" is a tropical *Dendrocalamus*.

| # | Source | Tier | Access | What to take, and limits |
|---|---|---|---|---|
| 1 | Build in-house with UE 5.8 ProceduralVegetationEditor (Experimental, installed) or Blender geometry nodes | OWN | A | See the ingredient list below the table. |
| 2 | Poly Haven `pine_tree_01` (17.4 M triangles, about 1 GB glTF) and `fir_tree_01` (7.9 M triangles) | PUB-CC0 | A | Poly Haven gives no species ("a tall, slender pine"). Use them as a shading and structure benchmark, or decimated as distant conifers. Only one heavy download at a time, and only if route 1 stalls. |
| 3 | Existing `TreeSmall02`, `PineSaplingSmall`, `Fern02` | PUB-CC0 | in repo | Already pinned. The fern contact still fails its gate. |
| 4 | Fab Megaplants (free listings): **Japanese Cypress** (listing 0843f3cf…), Japanese Medlar | RST | U | Only after D1 and the AI-flag check. They need PVE and Nanite Foliage (both Experimental; UE 5.8+). The M1 Ultra has no Nanite, so a conventional-LOD Mac version would still have to be built. Sizes are unknown. Baltic Pine and Norway Spruce would be distant filler at most. Don't use Yoshino Cherry or Giant Bamboo. |
| 5 | Engine PVE sample species (European Beech, Quaking Aspen, Common Hazel, Norway Maple) | UE EULA | installed | Generic filler only. They are the wrong species. |

**Ingredients for route 1:**
- **CC0 bark:**
  - `japanese_cedar_bark` for sugi;
  - `pine_bark`;
  - `japanese_zelkova_bark`;
  - `sakura_bark`;
  - `trident_maple_bark`;
  - `japanese_camphor_bark`.
- **Leaf and needle cards** from the CC0 ffish.asia/floraZia specimen scans on Sketchfab. These cover:
  - Japanese black and red pine buds and cones;
  - madake and kuma-zasa;
  - iroha-momiji, yamazakura and ume;
  - camellia and wisteria.

  The scans are specimen-scale, not whole trees.
- **Gap:** no CC0 source of sugi or hinoki foliage was found. Author those needle cards procedurally.

### 3.4 Sky and lighting

| # | Source | Tier | Access | What to take |
|---|---|---|---|---|
| 1 | Poly Haven puresky HDRIs at 4K (about 17 MB each) | PUB-CC0 | A | Lighting only: `kloofendal_misty_morning_puresky` (ch1 dawn), `qwantani_dusk_2_puresky`, and `qwantani_night_puresky` (the chapter 2 plan asks for a CC0 night HDRI). `kloofendal_overcast_puresky` is already pinned. The visible sky comes from SkyAtmosphere and volumetric clouds. |
| 2 | Poly Haven `ninomaru_teien` (a Japanese garden at sunrise), 4K | PUB-CC0 | A | Look-development and reflection reference only |
| 3 | Poly Haven `bamboo_tunnel` and `spooky_bamboo_morning` | PUB-CC0 | A | Light-quality reference for bamboo groves. The location is not stated. |

Full-scene HDRIs mostly show European or South African horizons, so don't use them as visible backgrounds.

### 3.5 Nyaakoto hero: anatomy, coat, fur, rig and face

Six scripted head attempts have failed (decision B5 in the completion map). These sources improve the inputs. They do not decide the outcome, which still depends on B5.

| # | Source | Tier | Access | Use |
|---|---|---|---|---|
| 1 | Edinburgh R(D)SVS **cat CT** (skull, 1.09 M triangles, 30.4 MB) | PUB-BY, raw private | A (Objaverse) | The real skull under the face, to fix the "toy dome" failures. Credit: "CT courtesy Dr Tobias Schwarz; prepared by Brian Mather, R(D)SVS, Univ. of Edinburgh". |
| 2 | RISD Nature Lab textured cat skulls (two scans, 0.6–1.0 M triangles) and the MRI PAS skull | PUB-BY, raw private | A (Objaverse) | Cross-check skull proportions |
| 3 | snacksthecat "Cat's Face" (279k triangles, 455 photos) | PUB-BY, raw private | **U** (Sketchfab) | The strongest real open-eye face form ([source gate](nyaakoto-open-eye-cat-source-gate.md)) |
| 4 | Paul Sabatier cat forelimb skeleton (53k triangles) | PUB-BY, raw private | **U** | Paw-grip rigging |
| 5 | Neo_minigan and elaughli scans | PUB-BY, raw private | A | Already vetted: head, cheek, ear and coat reference |
| 6 | westerly feline skeleton | PUB-BY | A | Artist-modelled, not a scan, and its accuracy is unverified. Check it against rows 1–4. |
| 7 | Muybridge plate 717, "Cat trotting, changing to a gallop" | PUB-CC0 (US PD) | A | Gait key poses for the tail and body |
| 8 | Unsplash and Pexels photos of grey tabbies with white muzzles and blue eyes | REF raw → OWN textures | A | Fur, eye and nose macro reference. Don't compile the photos into a library. |
| 9 | Wikimedia Commons, per file | PD/CC0/BY: PUB; BY-SA: REF only | A | Coat and marking reference |

**Fur pipeline (verified only up to the UE import):**
- **Route:** Blender 5.2.2 hair curves, using the bundled CC0 procedural hair node assets, then USD export, which keeps `primvars:groom_root_uv`, `groom_color` and widths. Next, `AddAppliedSchema("GroomAPI")` through Blender's `pxr`, then import through UE 5.8.3's USD groom path.
- **Don't use Alembic export:** it drops the root UVs and colors, which would put the tabby markings in the wrong place.
- **Don't use GroomExporter:** it states no license.
- **Tiers:**
  - Strands for Windows and for M2-or-later Macs on SM6. **The M1 Ultra cannot render strands**, according to Epic's docs and the local `DataDrivenPlatformInfo.ini`.
  - Cards from the Hair Card Generator (Experimental; it needs PythonMLPackages plus moderngl, PyOpenGL and scikit-learn) for gameplay, first-person view and the Mac.
  - Meshes as the last fallback.

**Rig and face:**
- **Rigging add-ons:**
  - Rigify, which ships with Blender: the human metarig plus the tail, `paw`, `front_paw` and `rear_paw` rig types. Its Cat and Horse metarigs are confirmed in the local install.
  - CloudRig 2.2.30 (GPL-3).
  - Pose Shape Keys (GPL-3).
  - Robust Weight Transfer (GPL-3).
- **Retopology:** QRemeshify (GPL-3), Instant Meshes (BSD-3), RetopoFlow (GPL-3 code).
- **Face:**
  - Author the 52 ARKit blendshapes with the ARKit Blendshape Helper (GPL-3) and drive them with Live Link Face, which needs a supported iPhone.
  - MetaHuman Creator only makes humanoids, so it cannot make cats.
  - MetaHuman Animator's audio-driven face path is R&D for Japanese lip-sync.

### 3.6 Clothing, armor and textiles

**Needed:**
- Nyaakoto's ch1 practice outfit (小袖, 袴, 襷);
- his ch2 armor (紺糸威 dark-blue lacing with 朱漆 vermilion plates);
- villagers and the pupils;
- League ashigaru for later chapters.

| # | Source | Tier | Access | Use |
|---|---|---|---|---|
| 1 | Poly Haven fabric and leather | PUB-CC0 | A | `rough_linen`, `hessian_230`/`380` for asa hemp, `crepe_satin` as the silk-sheen base, and `brown_leather`, already pinned |
| 2 | ambientCG Fabric (103), Leather (50), Rope, Chainmail001–004 | PUB-CC0 | A | The chainmail is a European weave. Re-author it as Japanese kusari. |
| 3 | Cooper Hewitt **katagami stencils** (141, CC0, via Smithsonian Open Access) | PUB-CC0 | A | Edo dye-pattern masks for kimono albedo, and a layout reference for the SORA mon |
| 4 | Met and Art Institute of Chicago kosode images (CC0) | REF/PUB-CC0 | A | Motif reference, not albedo |
| 5 | giravolt do-maru (1.06 M faces, 57.5 MB) and kokutochi-sankokan yoroi (211k faces, 7.1 MB) | PUB-BY, raw private | A (Objaverse) | Odoshi lacing and kozane rhythm only. These are earlier styles, not Edo tōsei-gusoku. |
| 6 | adrianocanotto ō-yoroi scan | PUB-BY | U | Same use as row 5 |
| ref | Met gusoku 894751, 22521, 24975; kabuto 22513, 24014; menpō 24160; sode 22472; jinbaori 32638. ColBase gusoku F-20102, F-16000, F-20155, F-20117-1; nobakama I-1356, I-4460; kamishimo I-4127 | REF | A | Measurement and construction boards (section 3.8 has the numbers) |

### 3.7 Horses and tack

The story bible specifies unshod native horses (在来馬, Kiso type, about 130 cm). The named horses are Kurimaru (a chestnut mare) and Arashi (a black-bay stallion), plus bay and black-bay pack horses.

| # | Source | Tier | Access | Use |
|---|---|---|---|---|
| 1 | Edinburgh horse CT (703k triangles, 19.1 MB) | PUB-BY, raw private | A (Objaverse) | Skull |
| 2 | Paul Sabatier horse hind-limb skeleton (49k triangles) | PUB-BY, raw private | **U** | Hock, fetlock and hoof. This targets the failed hock and fetlock gate. |
| 3 | Luján horse skeleton (3.5 MB) and Stabel "Horse running" muscle sculpt (2.28 M triangles, 93.9 MB) | PUB-BY, raw private | A (Objaverse) | Skeleton and surface musculature. The Stabel sculpt is a Thoroughbred-type body, so re-proportion it. |
| 4 | Muybridge horse plates (Library of Congress; "no known restrictions") | PUB-CC0 (US PD) | A | Walk, trot and gallop key poses |
| 5 | [Zenodo 4969712](https://zenodo.org/records/4969712) ridden Thoroughbred gallop, two synchronized views, CC0 (2.15 GB) | PUB-CC0 | A | Gallop timing. It is a Thoroughbred. P1: download it only once the rig exists. |
| 6 | Tack: Met CC0 kura 26572 (1658); **abumi 35376 (late 16th–early 17th century, closest to 1623)**; hato-mune abumi 712927 (18th century); aori 34797. ColBase kura and abumi H-3773, H-3767, H-1459 and the tazuna treatises QB-445/446. National Diet Library 集古十種 tack plates | REF (photos) → OWN models | A | Scale, construction and material evidence. For a 1623 setting, prefer 35376. Treat later objects as scale evidence, as the [tack reference](../historical-horse-tack-art-reference.md) already warns. |
| 7 | Met 23992 and 22586 | REF (text only) | A | Not open access. Use only their published measurements. |

**Rig and gaits:**
- Use the Rigify Horse metarig and hand-key 常歩, 速歩, 駈歩 and 襲歩.
- The lateral amble needs an equine animator.
- Manes and tails use the fur pipeline in section 3.5.
- **Gap:** no license-clean photo set of native Japanese horses (Kiso, Misaki) was found. Look for Wikimedia Commons files one by one, as REF.

### 3.8 Historical weapons

Weapons are built in-house (OWN) against these measurements. Many free "katana" and "kabuto" models are fantasy or replicas, including the hand-made Sketchfab models by patspet, sneeky and pinkycolada. They are not scans, and must not be treated as ground truth.

| Item | Reference (record checked 2026-09-25) |
|---|---|
| Katana | Standard Edo length about 71 cm (2 shaku 3 sun 5 bu; whether a decree set it is debated). Met 27789: blade 64.1 cm, overall 86.7 cm. Met 24378: blade 71.8 cm, curvature 0.9 cm. Tokyo National Museum F-20045 koshirae: overall 99.8 cm (see flag F12). |
| Wakizashi and tachi | Met 21880: blade 44.8 cm. Met 22123 tachi: blade 89.7 cm, overall 101.2 cm |
| Yumi | All Japan Kyudo Federation standard length 221 cm, grip about one-third from the bottom. Cleveland 1921.403 (CC0): 220.9 cm. ColBase F-20181: 195.3 cm. No Japanese yumi in Met Open Access. |
| Yari | Met 27609 jūmonji: blade 52.1 cm, surviving shaft 198 cm. Met 30843 su-yari blade: 20.6 cm. Ashigaru pikes about 3.6–4.5 m. |
| Naginata | ColBase F-20202 (1338): blade 46.7 cm, curvature 2.1 cm. The Met naginata records are not open access. |
| Tanegashima | Met 22492: overall 103.8 cm, barrel 73 cm, 16 mm bore, 3.01 kg. Met 22734 pistol: 50.8 cm |
| Armor and tack | Section 3.6 and section 3.7, plus Met 23941 saddle set (ca. 1700; confirm open-access status before using its images) |
| **Kanabō/tetsubō** | **Gap.** Tokyo National Museum F-15962, F-15963 and F-16879 have no image or size data. It needs a museum visit or a secondary source, labelled as such. |

**Materials and placeholders:**
- **Materials:**
  - ambientCG Bamboo, Rope and Leather for the yumi, ya, ebira, yugake and tsuka ito;
  - Poly Haven `lacquered_cherry_wood` for urushi;
  - CC0 metal sets.
- **Placeholder only:** Poly Haven `antique_katana_01`, whose fittings are generic.
- **Reference:** `katana_stand_01` for the 刀掛け; check its period.
- **Not searched:** CC0 feather textures for fletching.

### 3.9 Alien enemies, sci-fi weapons and machinery

The invaders are hairless, sphynx-like cats (story bible §1.4), so they need **no grooms**. Their material family is micro-engraved graphite, thin-film black glass, brushed titanium and cyan ledger emissives.

| # | Source | Tier | Access | Use |
|---|---|---|---|---|
| 1 | Original hard-surface modelling (the Arc Carbine pipeline) | OWN | A | Every enforcer, drone, pod, barrier, carbine, shield, grenade drum and marksman rifle. There is **no photoreal CC0 sci-fi kit** anywhere. |
| 2 | Poly Haven metals | PUB-CC0 | A | `blue_metal_plate`, `rusty_painted_metal`, `rusty_metal_grid`, `metal_plate_02`, `painted_metal_shutter`, and `rusty_metal_02` (already pinned) |
| 3 | ambientCG metals | PUB-CC0 | A | `MetalPlates001–017` (015–017 are tagged SciFi), `SheetMetal001–004`, DiamondPlate, PaintedMetal, CorrugatedSteel, `Scratches`, `Grate001/002` |
| 4 | Smithsonian Apollo 11 Command Module (721k faces, 39.2 MB via Objaverse) and Space Shuttle Discovery | PUB-CC0 | A | Greeble and panel-logic reference |
| 5 | [NASA 3D Resources](https://github.com/nasa/NASA-3D-Resources) | PUB-PD (conditions) | A | Spacecraft reference. No insignia, and no implied endorsement. |
| 6 | Poly Haven `overhead_crane` and `old_military_compressor` | PUB-CC0 | A | Kitbash reference |
| 7 | Kenney Space and Space Station kits; Quaternius Modular Sci-Fi MegaKit and Sci-Fi Modular Guns | PUB-CC0 | A | **Graybox and blockout only.** They are stylized, and would fail the photoreal gate. |
| 8 | Unsplash and Pexels sphynx-cat skin photos | REF → OWN | A | Wrinkle and skin micro-detail reference |
| — | Paragon sci-fi characters and weapons (Fab) | RST | U | Not recommended: the AI flag is unknown, the style is stylized-AAA, and the PARAGON trademark may not be used |

### 3.10 Animation and motion capture

| Need | Recommended source, in order | Tier and access |
|---|---|---|
| **Historical kenjutsu, kyūdō shaho, yari and naginata** | (1) Self-capture with a qualified practitioner who signs a performer release, using [FreeMoCap](https://github.com/freemocap/freemocap) (the tool is AGPL-3.0; the data is ours), and following story bible §3.1's respect rules. (2) Hand-keying. MetaHuman Animator mono-video body capture is Windows-only. **No open, commercially usable dataset exists.** | OWN, H |
| Blocking moves | CMU Graphics Lab: swordplay 02_07–09, bow mime 79_86, falls, locomotion. Take selected trials only. | Raw RST (Local); retargeted clips PUB with acknowledgment; A |
| Locomotion and idles | (1) [EMM data](https://zenodo.org/records/17220516): CC BY 4.0, 50+ min of Xsens locomotion, 53 MB zip. (2) [100STYLE](https://zenodo.org/records/8127870): CC BY 4.0, 1.5 GB BVH. Not the bundled Geno mesh, which is non-commercial. (3) Quaternius Universal Animation Library (CC0) as the public-clone fallback. | PUB-BY/CC0; A |
| Motion-matching base | GASP 5.8 (500+ locomotion clips; UE-only). It would be the best fit if agents are allowed to handle it. | RST; U; **only after D1** |
| First-person gun and combo blocking | UE template `Variant_Shooter` first-person animations and `Variant_Combat` montages, already installed | RST; the AI terms of the UE EULA template content are unknown (D1) |
| Alien fighters (no historical requirement) | CMU, EMM and 100STYLE first. Mixamo is P2 (RST; Adobe's AI terms not checked). | PUB-BY / RST |
| Horses | Hand-keyed from Muybridge and the Zenodo CC0 video (section 3.7) | OWN |
| Retargeting tools | UE 5.8 IK Retargeter (foot plane and toe, pelvis controls, Retarget Override Sets); Expy Kit (GPL-3); Retarget (GPL-3); Rokoko Studio Live for Blender (LGPL-3); Send to Unreal (MIT; access to the EpicGames repository not checked, and the poly-hammer fork is public) | Tools; A |

### 3.11 Sound effects and ambience (chapter 1–2 cue list)

**Original audio and CC0 come first.** Each file needs a license check at import, its source ID and a SHA-256. Store sources as 48 kHz/24-bit WAV or FLAC where the source allows. Freesound counts below are "all licenses / CC0 / CC BY" on 2026-09-25.

| Need | Sources, in order |
|---|---|
| Bokutō clacks, fukuro-shinai slaps, sword clash and unsheathe | (1) Our own foley recording of white oak and split bamboo (OWN, H). (2) Freesound CC0: sword clash 318/128/170, unsheathe 107/34/55, katana 81/25/45, parry 19/9/4. (3) Sonniss *Melee*, *Hero* and *Weapon Swings* (RST, P1). |
| Tsurune bow release, arrow flight and hits | Freesound bow release 899/**13**/885, so CC BY (with credit) is the practical tier. Arrow whoosh 84/61/14; arrow impact 73/49/15. Sonniss *Nocked* (RST). |
| Suri-ashi on hinoki and earth, footsteps | Freesound CC0: wood 894, gravel 700, stone 209, mud 92. Kenney RPG Audio (CC0 OGG, placeholder only). |
| Horses (unshod, on dirt and wood) | Freesound CC0: gallop 135, snort 34, whinny 40, bridle only 5. OpenGameArt "Horse Trotting". Iron abumi and bit clanks from metal foley plus modal synthesis. Avoid steel-shod hooves on cobbles. Sonniss *Animal Footsteps Foley – Hooves* (RST). |
| Nature | Freesound CC0: river 2,880, wind 10,489, rain 6,169, cicada 666 (summer chapters only). RutgerMuller "Field Recordings – Japan" (126 sounds; confirm each sound is CC0). **Uguisu and pheasant were not searched.** |
| Smithy | Freesound CC0: forge 449, anvil 121 |
| 半鐘 bell | Freesound temple bell 233/88/113; VCSL (CC0) tubular bells and gongs |
| Fire (ch2 estate) | **Not counted by the audio report.** Search Freesound CC0 first, then Sonniss. |
| Matchlock | OpenGameArt *The Free Firearm Sound Library* (CC0, 194 MB) plus Freesound CC0 musket (17) and flintlock (7), plus synthesized slow-match fizz and pan flash |
| Alien palette (sky seam, pods, drones, seizure field) | Runtime MetaSounds plus Python-rendered one-shots (OWN). Layers from Freesound CC0: laser gun 416, plasma 144, machine hum 762. Surge XT renders (GPL-3 tool; the output is ours). |
| UI | Python synthesis (OWN); Kenney Interface and UI Audio (CC0) as placeholders; hyoshigi and bells from VCSL woodblock and hand bells |
| Crowd 掛け声 and kiai efforts | Voice, blocked on B6. Generic crowd beds from Freesound CC0 (4,865). |

### 3.12 Music

- **All original compositions (OWN):**
  - Freesound CC0 instrument samples: shakuhachi 129 (many are PhonosUPF uploads, so check each), koto 90, taiko 71, shamisen 19, biwa 1.
  - VCSL (CC0) gongs, woodblock, bass drums as a taiko stand-in, and Dan Tranh as a koto stand-in.
  - Build Harmonix Fusion Sampler patches with the `FusionPatchJsonImporter` and drive them from MIDI.
- **Alien layer:** MetaSounds or Surge XT.
- **GarageBand** is installed (10.4.14). Apple Loops may be used inside our own compositions, never on their own. Its Asian instrument patches were not checked.
- **Pianobook** Shakuhachi and "Hunter's Percussion – World" need a login and are for rendered music only (P2).
- **Best route to AAA quality:** volunteer performers who release their recordings under CC0 or assign the rights (H).
- **Kevin MacLeod** (CC BY) as temporary music only.
- **Avoid OpenTracks and 魔王魂.** Both are RST, and their tracks risk Content ID claims.

### 3.13 Voice

Voice is blocked on B6. Nothing is sourced here. Don't use macOS `say` voices in anything shipped: Apple's terms were not checked.

### 3.14 Free tools an agent may install

All of these are free, and the work they produce is ours:
- **Audio:** Homebrew `sox` and `ffmpeg`; Surge XT (a 152 MB plugins-only build); optionally Audacity.
- **Capture:** FreeMoCap and MediaPipe.
- **Hair cards:** PythonMLPackages and its pip dependencies for the Hair Card Generator.
- **Blender extensions:** CloudRig, Pose Shape Keys, Retarget, ARKit Blendshape Helper, Unreal Groom Importer, Hair Bone Generator, PolyQuilt fork and Bsurfaces.
- **From GitHub:** Expy Kit, QRemeshify, Instant Meshes and Robust Weight Transfer.

**Excluded because they are paid:** Auto-Rig Pro, Hair Tool, Faceit and Quad Remesher.

## 4. Who fetches what

### 4.1 Agents, unattended (direct download or API, no login)

| Source | How | Notes |
|---|---|---|
| Poly Haven | `api.polyhaven.com` plus `dl.polyhaven.org` | Reuse the `fetch_polyhaven_palette.py` pattern: unique User-Agent, host allowlist, MD5 then SHA-256. Take 2K by default and 4K for hero surfaces. |
| ambientCG | API v2/v3 or direct zip per material | Run by one person and "not as reliable" as an enterprise service. Pin hashes. Take the 2K-JPG zip; each is its own small archive. |
| Objaverse 1.0 mirror (Hugging Face) | Direct GLB | Read the license from the public Sketchfab model API (`api.sketchfab.com/v3/models/<uid>` needs no login) and record both the origin URL and the mirror URL |
| The Met, Cleveland Museum of Art, Art Institute of Chicago, Rijksmuseum | Open-access APIs, no key | Use only records with `isPublicDomain: true` or CC0 |
| ColBase | Japan Search API (`f-db=cobas`) and web images | Web resolution only; credit line required; REF |
| National Diet Library | IIIF | Only items marked 保護期間満了 (copyright expired) |
| Smithsonian (3D Voyager, item pages) | Direct | The API needs an api.data.gov key (step U5). The demo key hit HTTP 429 after about 16 calls. |
| Wikimedia Commons and the Library of Congress | API or direct, with a User-Agent | Check each file's license |
| Zenodo (EMM, 100STYLE, racehorse video) and CMU | Direct | Selective downloads (section 5) |
| Kenney, OpenGameArt, Quaternius (itch.io, $0, no account) | Direct | CC0 files only |
| VCSL | `git clone --filter=blob:none --sparse`, then `git sparse-checkout set` the needed folders | Avoids the 3.8 GB full repository |
| Sonniss GDC bundles | Direct, no account | RST. **Only after the user acknowledges the license (step U6).** Extract selectively. |
| NASA 3D Resources and Blender extensions | Direct or GitHub | — |

### 4.2 User steps (one time each, done by the user)

**Handoff contract.** The user puts files in `Local/ThirdPartyRaw/inbox/<source>/`, together with a PDF of the listing or terms page. An agent then:
- hashes the files;
- reads the license from a public source where one exists;
- writes the ledger record;
- moves the files to their tier location.

Agents never accept terms or click-through licenses for the user.

**U1. Sketchfab** (sign in with an Epic account). Do this early: Sketchfab has announced that free licensing will be removed after the Fab migration.
1. Sign in at https://sketchfab.com.
2. Open each listing in backlog item 8.
3. Check that the license badge matches the one in this plan (CC0 or CC Attribution). If it shows NonCommercial, NoDerivs or ShareAlike, or has no Download button, skip it and write down which one.
4. Click **Download 3D Model** and choose the original archive. If the original is over 500 MB, choose glTF instead.
5. Save it to `Local/ThirdPartyRaw/inbox/sketchfab/<32-hex model UID from the URL>/`.
6. Save the listing page as a PDF (Print → Save as PDF) in the same folder.
7. Tell the agent "Sketchfab batch ready".

**U2. Freesound** (needed for original files; without it the API only returns lossy previews).
1. Log in or create an account at https://freesound.org, and accept its terms yourself.
2. Apply for API credentials at https://freesound.org/apiv2/apply/. Leave the callback URL at its default.
3. Save the client ID and secret in `~/.config/sora-arena/freesound.json` with `chmod 600`. This keeps them outside the repository.
4. Run the agent's authorization helper. It prints an authorize URL. Open it, log in, click **Authorize**, and paste the code back. The helper stores and refreshes the token (token lifetimes were not checked).
5. **Alternative:** download the packs from the website while logged in and put the zips in the inbox.

**U3. Epic Games Launcher and Fab** (only after D1).
1. In a browser signed in to fab.com, open each listing: GASP (5.8 update), Megaplants Japanese Cypress and Japanese Medlar.
2. For each, record the license type, **"UE-Only"** and **"Allows usage with AI"**. Save the page as a PDF to `Local/ThirdPartyRaw/_licenses/fab/`.
3. If AI use says **No**, stop. Don't claim it for the agent workflow.
4. Open Fab **My Library** and export or screenshot the list of anything claimed in 2024 or earlier, such as Megascans "Feudal Japan" items. Earlier claims remain usable.
5. Claim the $0 items you approve.
6. Before importing, set the Fab plugin's (Window > Fab) import folder to `/Game/ThirdPartyRestricted/Fab/`, or use Launcher **Add to Project** and move the content there.
7. Run `git status --porcelain Content`. Nothing new should appear outside the ignored folder.
8. Tell the agent. It records hashes in `scripts/assets/restricted/fab.json`.

**U4. JAXA AW3D30.**
1. Register on the EORC site.
2. Download the tile that covers the Yagyū area (Nara). Check the tile ID on the site.
3. Put it in `Local/ThirdPartyRaw/inbox/jaxa/`.
4. Credit: `©JAXA`.

**U5. Smithsonian API key (optional).** Get a free api.data.gov key and put it in `~/.config/sora-arena/si.json`. Direct item pages work without a key.

**U6. Restricted-license acknowledgement.** Before agents fetch any restricted source that needs no login (Sonniss, and later 効果音ラボ, Pixabay or Mixkit), read its license page and confirm in the session. The ledger records who accepted it and when.

**U7. Sensei Terrain (optional).** Even the $0 Gumroad checkout (code `UNREAL5`) goes through a purchase step, so the user approves it. The download (80.9 MB) is for human-only local evaluation. Ask Unreal Sensei for written commercial permission only if you want to ship it.

### 4.3 Human-only work

- **Motion capture:** kata capture needs a practitioner and a signed release, and the raw videos stay private.
- **Voice:** voice and kiai (B6).
- **Review:** listening and mix review; historian and practitioner review.
- **Restricted content:** any handling of content marked NoAI, if the user allows it at all.
- **Anything that needs acceptance:** license click-throughs and purchase-flow checkouts.

## 5. Disk budget

**Numbers to work from:**
- **Free space:** 81 GiB now. The completion map recorded 43 GiB earlier the same day, so re-measure before every heavy job rather than trusting either number.
- **Floor:** keep at least 30 GiB free (the plan's rule; `import-mac.sh` refuses to run below it).
- **Headroom:** 81 − 30 = 51 GiB, shared with builds, cooks, DerivedDataCache and packaged outputs, none of which can be deleted either.

**Rules:**
- **The first-slice acquisition cap is 20 GiB of real footprint.** Fab's conditional items proceed only if at least 45 GiB is free when their turn comes.
- **Count what is really stored.** A committed file costs about twice its size locally (working tree plus `.git/lfs`), plus its UE import in `Content/Generated` and the DerivedDataCache. That import cost is an unmeasured estimate of 0.5–1× the source. Files kept in `Local/` count once, plus their import.
- **Never download an archive that will only be partly used**, because it can never be deleted. Instead:
  - use per-file URLs;
  - or extract single members through HTTP Range requests (a seekable HTTP reader passed to Python's `zipfile`; whether each host supports Range is unverified);
  - or pick individual files in a torrent client.

  If a whole archive is unavoidable, count it in full and keep it.
- **Resolution:**
  - 2K is the default.
  - Use 4K only for hero surfaces seen from under 3 m. The story bible's 1024 px/m hero texel density means a 2K tile covers 2 m and a 4K tile covers 4 m.
  - No 8K or 16K.
  - No displacement maps unless Nanite displacement or Mesh Terrain actually uses them.
- **Batching:**
  - One heavy job at a time.
  - Download straight to the final location.
  - For each batch, log `du -sk` of `Local/`, `Content/SourceArt`, `.git/lfs`, `DerivedDataCache` and `Content/Generated`, before and after, in the ledger's batch log.

| Batch | Download | Stored in | Estimated footprint |
|---|---|---|---|
| Poly Haven surfaces, 26 sets (20 at 2K, 6 at 4K; backlog items 3–4) | ~1.3–1.5 GB (measured 2K sets are 11–47 MB, a 4K set 74 MB) | repo (LFS) | ~4 GB |
| Poly Haven HDRIs, 4 at 4K | ~0.07 GB | repo | ~0.2 GB |
| Poly Haven models, 9 rocks and props at 2K | ~0.3–0.6 GB (not measured) | repo | ~1.5 GB |
| ambientCG, about 20 materials at 2K | ~0.5–0.7 GB | repo | ~1.7 GB |
| Scans (Objaverse and Sketchfab: anatomy, armor, plant specimens, ishigaki) | ~1 GB | `Local/ThirdPartyRaw` | ~1 GB |
| Museum and photo reference boards | ~0.7–1.2 GB | `Local/Reference` | ~1.2 GB |
| Audio: Kenney, OpenGameArt, VCSL subset, Freesound picks | ~0.8 GB | sources used in the repo (≤0.5 GB); the rest in `Local` | ~1.5 GB |
| Mocap: CMU trials, EMM (selective), Quaternius | ~0.1 GB, plus ≤0.5 GB extracted | `Local` | ~0.6 GB |
| **Core subtotal** | | | **~12–14 GB** |
| Sonniss 2026 plus selected earlier libraries (P1) | ≤2 GB, selective only | `Local` + `Content/ThirdPartyRestricted` | ~3 GB |
| 100STYLE BVH (P1, only if needed) | 1.5 GB | `Local` | ~1.5 GB |
| Racehorse video (P1) | 2.15 GB, or one view if the files are separate | `Local` | ~2.2 GB |
| **With P1** | | | **~18–20 GB** (the cap) |
| Fab conditional: Megaplants hinoki, GASP | sizes unknown ("several GB" reported) | `Content/ThirdPartyRestricted` + DDC | up to 10 GB; separate gate at ≥45 GiB free |

**Never download:**
- Epic samples: Electric Dreams (about 13 GB), Valley of the Ancient (100 GB+ reported), Titan and City Sample.
- The full Sonniss 2023 (40 GB+) and 2024 (27.5 GB+) bundles.
- The full VCSL repository.
- The processed 100STYLE set (14.8 GB).
- The CMU c3d set (over 4 GB).
- PFERD (348 GB, and excluded anyway).
- 8K-PNG ambientCG sets (about 0.9 GB each).

## 6. Acquisition backlog for the first playable photoreal slice

The slice is the Nyaagyu Estate plus the chapter 1–2 spaces, the Nyaakoto hero, alien enemies, horses, weapons, and core sound, ambience and music. Do the items in order. Items marked **U** wait for the matching step in section 4.2; agents carry on with the next A item meanwhile.

| # | Item | Source → tier | Who | Download | For | Done when |
|---|---|---|---|---|---|---|
| 1 | Ledger schema 2, migration of the existing manifests, `validate_asset_ledger.py`, `check_restricted.py`, and the `Content/Fab/` guard | — | A | 0 | Everything | The validator passes on the repo and fails on a planted restricted file in a tracked path |
| 2 | Decisions D1–D6 (section 7) | — | User | 0 | Fab, Epic and restricted items | Answers recorded in the ledger README |
| 3 | Poly Haven architecture set: `hinoki_planks`, `japanese_cedar_planks`, `clay_plaster`, `stacked_stone_wall` at 4K; `patterned_clay_plaster`, `roof_planks`, `thatch_roof_angled`, `reed_roof_03`, `bamboo_wall_02/03`, `tatami_mat`, `lacquered_cherry_wood`, `wood_inlaid_stone_wall`, `mossy_stone_wall`, `japanese_stone_wall`, `granite_wall` at 2K | PUB-CC0 | A | ~1 GB | Dojo interior, stable, smithy, armory, gatehouse, tea hut, stone bridge | Hashes pinned; mortar-joint check done for the stone sets |
| 4 | Poly Haven ground and bark: `forest_ground_05` and `japanese_cedar_bark` at 4K; `forest_ground_04/06`, `muddy_tracks`, `river_small_rocks`, `pine_bark`, `japanese_zelkova_bark`, `sakura_bark`, `trident_maple_bark` at 2K | PUB-CC0 | A | ~0.5 GB | Lane, wood, highway, stream, tree building | Pinned |
| 5 | HDRIs at 4K: `kloofendal_misty_morning_puresky`, `qwantani_dusk_2_puresky`, `qwantani_night_puresky`, `ninomaru_teien` | PUB-CC0 | A | ~0.07 GB | Ch1 dawn, dusk, ch2 night | Pinned |
| 6 | Poly Haven models at 2K: `rock_moss_set_01/02`, `boulder_01`, `root_cluster_01`, `moss_01`, `tree_stump_01`, `wooden_bucket_01/02` (the well bucket), `katana_stand_01` | PUB-CC0 | A | ~0.3–0.6 GB | Wood, yard, dojo | Pinned; the sizes now measured |
| 7 | ambientCG 2K: `Rope001–003`, `Bamboo001/002`, `Moss001–004`, 2 Plaster, `RoofingTiles011–015` (evaluate), 4 Leather, 6 Fabric, straw (Wicker/ThatchedRoof), `Chainmail001–004` | PUB-CC0 | A | ~0.6 GB | Shimenawa, tack, costume, straw props, kusari base | Pinned |
| 8 | **Sketchfab batch** (U1). **Ch1–2 set:** snacksthecat cat face; Paul Sabatier cat forelimb and horse hind limb; ffish.asia/floraZia CC0 specimens (pine buds and cones, madake, kuma-zasa, iroha-momiji, yamazakura, ume, camellia, wisteria); the tōrō lantern; the Kokugakuin eaves-end tile. **Early because of license risk:** Osaka and Obama ishigaki, oni-gawara, adrianocanotto ō-yoroi. **Optional:** Cleveland CC0 mikoshi, jūbako and Nio, and the Mia byōbu | PUB-BY/CC0, raw in Local | **U** | ~1 GB | Hero face, paws, horse legs, foliage cards, roof and ishigaki | Each has a license PDF, hash and ledger record |
| 9 | Freesound OAuth set-up (U2) | — | **U** | 0 | Item 17 and the music samples (section 3.12) | Token stored outside the repo |
| 10 | Objaverse anatomy and armor kit: cat CT, both RISD skulls, MRI PAS skull, westerly skeleton; horse CT, Luján skeleton, Stabel horse; do-maru, yoroi; Apollo 11 CM | PUB-BY/CC0, raw in Local | A | ~0.4 GB | Hero, horses, armor lacing, alien greebles | Licenses re-read from the Sketchfab public API; origin and mirror recorded |
| 11 | Photo reference boards (Unsplash, Pexels, Wikimedia; per-file licenses): grey tabby with white muzzle and blue eyes; sphynx skin; bay, chestnut and black-bay native horses | REF | A | ~0.2 GB | Coat, skin and horse lookdev | Boards in `Local/Reference` with per-file records |
| 12 | Fur pipeline pilot: groom a test patch in Blender, export USD, apply GroomAPI, import into UE 5.8.3, then build cards with the Hair Card Generator | OWN | A | 0 (installs only) | Nyaakoto, horse manes | Root UV, color and width survive the import; cards render on the M1 Mac. **Strand verification waits for Windows or an M2+ Mac.** |
| 13 | Blender rigging and retopology add-ons (section 3.14) | tools | A | small | Hero and horse rigs | Installed, versions recorded |
| 14 | Museum measurement boards: Met (open-access only), Cleveland (bow 1921.403, gusoku 1921.404), ColBase (section 3.8 list), NDL 集古十種, Smithsonian NMNH and NMAH item pages, AIC kosode, 141 Cooper Hewitt katagami | REF; katagami PUB-CC0 | A | ~0.7 GB | Weapons, armor, tack and textiles | A committed measurement table (text) plus URL and hash manifests; derived katagami masks may be committed |
| 15 | Audio tools: `brew install sox ffmpeg`, Surge XT | tools | A | ~0.3 GB (estimated) | Items 16–20 | Installed |
| 16 | Direct CC0 audio: 8 Kenney packs; OpenGameArt Free Firearm Sound Library; OpenGameArt swords, footsteps, horse trotting, rain and sci-fi packs; VCSL sparse checkout (Gong, Woodblock, Slit Drum, Bass Drum 1–3, Frame Drum, Tubular Bells, Hand Bells, Hand Chimes, Dan Tranh) | PUB-CC0 | A | ~0.6 GB | UI, matchlock, placeholders, instruments | Per-file records with `License.txt` hashes |
| 17 | Freesound picks for the chapter 1–2 cue list (section 3.11). Original files only; CC0 first, CC BY where CC0 is thin (tsurune) | PUB-CC0/BY | A after U2 | ~0.4 GB | Sword, bow, steps, horse, nature, smithy, bell, alien layers | Every cue in `audio.json` has a source record |
| 18 | CMU selected trials, EMM (selective extraction), Quaternius UAL | RST raw / PUB-BY / CC0 | A | ~0.1 GB | Blocking and locomotion | Retarget test on the cat skeleton |
| 19 | Kata capture sessions: seigan, awase, marobashi, men/kote/kesa; kyūdō hassetsu; su-yari thrusts | OWN | **H** | — | Chapter 1 duels and range | Release signed; practitioner review logged |
| 20 | Sonniss GDC 2026 plus named earlier libraries (*Nocked*, *Hero*, *Melee*, *Medieval*, *Weapon Swings*, *Asian Countrysides*, *Animal Footsteps Foley – Hooves*, *Crickets and Cicadas*, *Sci-Fi Weapons Pack 1*, *Exoplanets – Drones*), selective only | RST | A after U6 | ≤2 GB | Professional layers | Restricted manifest; nothing tracked |
| 21 | Muybridge horse and cat plates | PUB-CC0 | A | small | Gait keys | Pinned |
| 22 | NASA 3D selected parts; Kenney and Quaternius sci-fi blockout kits | PUB | A | ~0.2 GB | Alien graybox and greebles | Marked "blockout only" in the ledger |
| 23 | JAXA AW3D30 tile (U4) | PUB-BY-like | **U** | small | `pl_kaido` and vista macro terrain | Credit recorded |
| 24 | Zenodo racehorse video (P1) | PUB-CC0 | A | 2.15 GB | Gallop keys | Only after the horse rig exists |
| 25 | 100STYLE BVH (P1) | PUB-BY | A | 1.5 GB | Style gaps | Only if EMM and CMU leave gaps |
| 26 | Fab: Megaplants Japanese Cypress, then GASP 5.8 | RST | **U**, then A if allowed | unknown | Hinoki grove, motion matching | AI flag allows it; Mac fallback planned; ≥45 GiB free |
| 27 | UE template FP and combat animations (installed) | RST | A if D1 allows | 0 | FP paw blocking | Retargeted into `Content/ThirdPartyRestricted` |
| 28 | Sensei Terrain (U7) | REF, human only | **H** | 81 MB | Comparison with our own material | Never enters the repo or reaches an agent |

**P2, after the slice:**
- **Motion and characters:** Paragon, Mixamo, Rokoko, ActorCore, the Blender Studio cat rig (workflow study), and the MorphoSource *Felis silvestris* CT (after reading its terms).
- **Music and sound:** Pianobook libraries, 効果音ラボ, Pixabay and Mixkit for leftover gaps, Wikimedia CC0 instrument clips, and Kevin MacLeod as temporary music.
- **Later chapters:** the Cleveland and Minneapolis scans.

## 7. Decisions for the user

- **D1. Reading the Epic and Fab AI clause.** Should content marked "Allows usage with AI: No", or content whose terms are unclear (UE template assets), be used at all?
  - **Recommendation:** keep it out of the agent workflow.
  - If you want Megaplants Japanese Cypress or GASP, a human handles those files and renders, and agents never see them. In practice that also means agents cannot run visual reviews of scenes that contain them.
- **D2. One-time logins:** Sketchfab (U1), Freesound (U2), Fab (U3) and JAXA (U4). Sketchfab is the most urgent.
- **D3. Restricted licenses** (Sonniss first): accept them yourself (U6). Remember that each teammate must download their own copy.
- **D4. $0 checkouts that go through a purchase step** (Sensei Terrain on Gumroad, Fab claims): approve each one.
- **D5. Performers and releases** for kata capture, plus the voice route (B6).
- **D6. Raw CC BY scans:** keep them private, as the existing cat-scan docs do, and commit only derived art.
  - **Recommendation:** keep that policy.

## 8. Unverified claims and conflicts between the reports

| # | Claim | Status |
|---|---|---|
| F1 | Terms of Fab, Epic, Adobe (Mixamo), ColBase, ZapSplat, Mixkit and Musopen | Read through Wayback or search-engine snippets; the sites returned 403 to scripts. Re-read each in a browser and record the date when acquiring. |
| F2 | AI flags of Megaplants, GASP, Paragon, Cassini, Stack O Bot and UE template content | **Unknown** |
| F3 | The Fab plugin's default import folder | Not checked. `Content/Fab/` is not gitignored today. |
| F4 | The USD groom import into UE 5.8.3 | Verified from engine source and in Blender only; not in the editor |
| F5 | Hair Card Generator pip dependencies (moderngl, OpenGL) on macOS | Not tested. Windows is the fallback. |
| F6 | Strands and Nanite on the M1 Ultra | Epic's docs require M2 or later for SM6 strands and for Nanite. So this Mac can verify card and mesh fur only (and the conventional-LOD Megaplants path). |
| F7 | Asset sizes | The reports' Poly Haven set sizes (2K "9–14 MB", 4K "30–47 MB") are lower than the measured repo files (2K 11–47 MB, 4K 74 MB). Megaplants, GASP, Titan and City Sample sizes are unconfirmed. Poly Haven model sizes were not measured. |
| F8 | "GarageBand not installed" (audio report) | **Wrong:** 10.4.14 is installed. |
| F9 | Free disk: 43 GiB (completion map) against 81 GiB (reports and `df` now) | Re-measure before each heavy job |
| F10 | "18 Poly Haven assets in the repo" | The manifests show 17 distinct IDs; 20 with the docs included. |
| F11 | Freesound "packs" found through CC0-filtered searches | Confirm the license of each sound. Download originals only. |
| F12 | Tokyo National Museum F-20045 koshirae "overall 99.8 cm" | The same figure appears for Met 638804 in [historical-arms.md](../historical-arms.md). One may be a transcription mix-up; re-check both records. |
| F13 | Met 23941 saddle set | Its open-access status was not stated |
| F14 | Mōsō bamboo introduced in 1736; Somei-Yoshino late Edo | From the environment report; not independently sourced here |
| F15 | Unshod Edo horses wearing umagutsu, with iron shoes arriving in the Meiji era | The story bible §4.5 designs for it; no historical source is cited |
| F16 | Mortar joints in `japanese_stone_wall` and `granite_wall` | Taken from Poly Haven's own descriptions; check them visually |
| F17 | Sketchfab moving to Epic accounts (Dec 2025), KitBash buying Sketchfab (Aug 2026), free licensing to be removed | Reported, not re-verified |
| F18 | HTTP Range support at the Sonniss, OpenGameArt and Zenodo hosts; the Sonniss torrent layout; per-file layout of 100STYLE and the racehorse video | Not checked |
| F19 | Whether Pixabay audio downloads need an account | Not checked |
| F20 | Access to the `EpicGames/BlenderTools` repository | Not checked; the poly-hammer fork is public |
| F21 | Adobe, Rokoko and ActorCore terms on AI use | Not checked |
| F22 | craigsmith's Freesound "vintage" libraries | The CC0 claim is doubtful; excluded |
| F23 | Report 2 ranks GASP as the P0 locomotion source; Report 1 finds every Epic sample it checked is NoAI | Resolved here by making GASP conditional on D1, with EMM, 100STYLE and CMU as the default |
| F24 | The completion map suggests parking horse studies; user directive 7 says horses are in scope | Horses stay in the backlog (directive 7 is binding); horse acquisition is kept to references and hand-keying |

## 9. Excluded sources

| Source | Reason |
|---|---|
| PFERD horse mocap, VAREN, hSMAL | Non-commercial research licenses |
| Bandai Namco Research Motion Dataset (CC BY-NC), LAFAN1 (CC BY-NC-ND), 100STYLE's Geno mesh (NC) | Non-commercial |
| creatureanimator horse walk, trot and run cycles | CC BY-ND. Viewing for timing only (REF), even though Objaverse mirrors the walk |
| MorphoSource *Felis catus* CT records | `CommercialUseNotPermitted` |
| Sketchfab "Japanese armor, Edo period" scan | CC BY-NC |
| BBC Sound Effects (RemArc licence), Freesound CC BY-NC and Sampling+, all CC BY-SA assets | Non-commercial or ShareAlike (a policy choice for simplicity) |
| ZapSplat, Musopen | Low value for the restrictions attached; Musopen is Western classical only |
| MoCap Online | Needs written permission for any AI use; revenue caps |
| Epic sample projects | NoAI flags, no Japanese biomes, 13–100+ GB downloads |
| Twinmotion Education content | Educational-use license |
| Tokyo National Museum high-resolution images, Truebones Zoo, Fab horse packs, Blender Studio production files, Auto-Rig Pro, Hair Tool, Faceit, Quad Remesher | Paid |
| WildMesh horse | Personal use only |
| Blendkit cat rig | Its royalty-free terms forbid public source repositories; not needed |
| Stylized CC0 cats (BlendSwap, OpenGameArt) | Fail the photoreal gate |
| GSI 5 m DEM | May need an application under the Survey Act |
| macOS `say` voices | Apple's terms not checked |
