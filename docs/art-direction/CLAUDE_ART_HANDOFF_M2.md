# Handoff: SORA Arena photoreal art, continue on the M2 Mac

From the Claude Code session on the M1 Ultra (2026-10-18), for the Claude
instance continuing on an M2 Mac. Read this first, then
`docs/art-direction/CLAUDE_ART_HANDOFF.md` (the original assignment; still
binding) and `docs/recovery/claude-2026-10-18/INTEGRATION.md`.

## 1. What the user wants

- **Photoreal, AAA+ and beautiful.** Never propose a stylized fallback. Build
  the art yourself, or use free assets whose licences allow commercial use
  (CC0 Poly Haven/ambientCG; CC BY with credit). Record every licence.
- **The look of the user's two reference images.** Ask the user to attach them
  again. Both are warm golden-hour East Asian estate interiors and exteriors:
  - Light and setting: low sun with haze and light shafts, autumn red maples,
    distant pagodas and mountains.
  - Surfaces: polished reflective timber floors, massive dark columns.
  - Dressing: glowing paper lanterns, and black urushi chests with gold maki-e
    and gold fittings. Also red silk tassels, scrolls, brass instruments and
    stone paths.
  - **The SORA 天 mark appears as raised iridescent mother-of-pearl (raden)
    medallions and coins.**
  - The images also contain other emblems (a red flower with a hexagram, a
    lotus) and Nexus marketing text. Do not use these without asking the user
    for sources.
- **Elaborate use of the SORA mark for marketing**, done as real craft, always
  from the exact SVG `Content/SourceArt/UI/sora_logo_NOtext2.svg`
  (SHA-256 `d66413a7…0910`): raden, maki-e gold, gilt metal, dyed hemp, roof
  tiles, coffered-ceiling panels.
- **Very fun** gameplay feel (see §6).
- **First release, no backward compatibility:** delete superseded code and
  assets once their replacement is in and verified.
- **Latest direction (mid-session): use Nanite and the latest UE techniques
  fully, so each wood beam is a real, unique beam in geometry, not a texture
  on a box.** This is why the work moved to an M2 Mac.
- The user said you may update the `../iroha` `optimizations` branch if art or
  runtime work needs it. Nothing so far has needed it.

## 2. Why the M2 matters (verified)

UE 5.8.3 enables Nanite on Mac only on the Metal SM6 shader platform, which
needs 64-bit image atomics. M2 and newer have them; M1 does not. Evidence:

- `Engine/Config/Mac/DataDrivenPlatformInfo.ini`: SM6 has `bSupportsNanite=true`
  and `bSupportsUInt64ImageAtomics=true`; SM5 has both `false`.
- The M1 Ultra game log reports `shaderplatform="METAL_SM5"`.

**The project also forces Nanite off on every Mac.** `Config/Mac/MacEngine.ini`
sets `r.Nanite=0`, `r.Nanite.ProxyRenderMode=0`,
`r.Shadow.Virtual.Enable=0`, `r.RayTracing=False` and MegaLights off.

To use Nanite on the M2:

- Remove `r.Nanite=0`. Keep `ProxyRenderMode=0` so M1 Macs still draw
  fallbacks.
- Consider enabling VSM (Nanite shadows want it) and measure it.
- Several importers assert the old policy text. They fail until updated, for
  example `scripts/unreal/import_nyaagyu_cargo_stack.py` checks that
  `"r.Nanite=0" in mac_config`. Grep `scripts/unreal` for `r.Nanite`.
- Keep a working Nanite-disabled fallback for M1 Macs (the handoff requirement).

**First thing to verify on the M2:**

1. Confirm the log reports `METAL_SM6`.
2. Check `r.Nanite` at runtime.
3. Capture with Nanite visualization (`r.Nanite.Visualize Triangles`) to prove
   Nanite is actually drawing.

Report SM5 and SM6 results separately and honestly.

## 3. Repository state

- `master` is at `788084a`, pushed by Codex (recovery integration).
- The art branch is `claude/photoreal-art`, cut from `788084a`. On the M1 it
  was a separate worktree at `../sora-arena-wt/art`.
- **Check that the user pushed this branch (with LFS) before you start.** If it
  is missing, ask. All of the session's work was uncommitted when it stopped.
- `Content/Generated` and `Content/ArtReview` are gitignored. Rebuild them on
  the M2 with the importers (§5).
- `Local/ThirdPartyRaw` (the CC0 raw cache) is gitignored too. Rebuild it with
  `scripts/assets/fetch_cc0.py`; downloading needs the user's approval.

**New files on the branch:**

| Path | What it is | State |
| --- | --- | --- |
| `scripts/art/sora_mark.py` | Exact SVG path parser and scanline rasterizer for the SORA mark, numpy-only, runs in Blender | Verified against the pinned CairoSVG raster: coverage within 0.02 %, edges differ only in anti-aliasing |
| `scripts/art/craft_textures.py` | Raden film/body, roiro urushi, maki-e powder, nashiji, maple-leaf polygons, polyline strokes (numpy) | Works; the maple shape is acceptable but generic |
| `scripts/art/sora_prop_lib.py` | `PropBuild`: generic prop pipeline over `create_runtime_weapon_lib.Build` | Bakes BaseColor, NormalDX, ORM and Mask (R raden, G gold, B film). Exports LOD0 only; Unreal builds the LODs. Studio, golden and lantern review renders |
| `scripts/art/create_sora_raden_bunko.py` | Edo maki-e document box on a neko-ashi (cat-paw) stand | Tatsuta-gawa water, maple leaves with kakiwari veins, three gold SORA mons, a **domed raden SORA medallion** in a gilt rim, gilt corner caps, silk cords and tassels. 71.7k triangles, 4K atlas. Output in `Content/SourceArt/Environment/SoraCraft/SoraRadenBunko/` |
| `scripts/unreal/import_sora_craft.py` | Imports SoraCraft props | Builds the **M_SoraCraft** master, which computes raden as per-pixel thin-film interference (260–720 nm aragonite, view dependent). LODs come from Unreal's reducer at 1.0, 0.45 and 0.18, with screen sizes 1.0, 0.30 and 0.10 |
| `scripts/unreal/render_sora_lookdev.py` | Editor look-dev captures | Fixed cameras; golden, overcast and lantern rigs; the game's histogram auto-exposure. Runs in the full editor through `--editor`, piloting cine cameras, with `HighResShot` from the console |
| `scripts/toolchain/run-editor-script.sh` | Headless editor Python runner with the Config guard | `--rhi` uses UnrealEditor-Cmd with Metal. `--editor` runs the full offscreen editor for tick-driven scripts, which need `set_keep_python_script_alive(True)` and their own quit. Exit status 1 with the marker present is accepted |
| `scripts/toolchain/capture-editor-game.sh` | Runs rendered game automation in the editor binary's `-game` mode on uncooked content | `-NoTextureStreaming`. `SORA_EXEC_PREFIX="cvar value,"` runs console commands first; ExecCmds separates commands with commas |
| `Source/SoraArena/Private/SoraArtReviewCapture.cpp` | `SoraCapture.ArtReview.Dojo` | Six HUD-free fixed shots of the chapter-1 dojo, from a seeded throwaway save. Finishes asset and shader compilation and forces mips resident first. Frames go to `Saved/Screenshots/SoraArtReview/1920x1080/` |
| `scripts/art/sora_arch_lib.py` | Modular-architecture helpers | Metre-scale UV0, role materials `M_Arch_<Role>`, FBX export, manifest |
| `scripts/art/create_nyaagyu_dojo_kit.py` | Tsumagizaka dojo hall kit | Wall bays (Panel, Renji, RenjiHigh, Shoji, DoorOpen), column, four hinoki floor tiles (per-board UV windows), coffered ceiling tile with gold-leaf SORA mon and maple panels, east-wall kamiza alcove. Output in `Content/SourceArt/Environment/NyaagyuDojoKit/`. **These are box primitives. Replace them with unique Nanite geometry (§4).** |
| `scripts/unreal/import_nyaagyu_dojo_kit.py` | Imports the kit | Uses Poly Haven CC0 scans from the local raw cache, checked against `scripts/assets/manifests/polyhaven-first-slice.json`. Builds `M_SoraArch` (UV-tiling scan master with TileMeters, tint, macro break-up and a position-hash UV offset), `M_SoraArchFoliage` (two-sided foliage for shoji) and `M_SoraArchFlat` |
| `Source/SoraArena/Private/World/SoraWorldBuilderDojoHall.cpp` | `ASoraWorldBuilder::HallInterior()` | Lays the kit along any estate hall zone's rect (chapter 1 dojo: x 8000–11600, y −1300–1300, 7 m walls). Adds a roof deck that stops ceiling light leaks. `sora.HallInstanced 0` places one component per module |
| Edited: `Source/SoraArena/Private/World/SoraWorldBuilderLayoutZones.cpp` (+10 lines), `Source/SoraArena/Public/SoraWorldBuilder.h` (+3 lines) | `BuildZone` calls `HallInterior` for estate halls | Hides the primitive floor and wall visuals only when every module loads. Collision and navigation are unchanged |
| `docs/art-research/katana-koshirae-construction.md` | Sourced Edo katana and koshirae construction | Met, V&A, TNM and NBTHK objects with dimensions. Modeling spec: blade 720 mm, sori 19, tsuba 78 × 75 × 5.5. Kamon-on-fittings precedents include raden crests on V&A 603&A and scattered aoi crests on TNM F-19985 |

**Verified results** (Unreal captures were on the M1, SM5):

- The bunko renders in an editor look-dev view, `Saved/SoraLookDev/Bunko1/`
  (regenerate it). It shows black lacquer, gold maki-e, gilt caps and raden
  leaves with iridescence.
- The dojo hall renders in game:
  - With `sora.HallInstanced 0`, textures are correct: hinoki floor boards,
    cedar boards and shoji with kumiko.
  - **With instanced static mesh components (the default), every kit texture
    renders blocky, like the lowest mip.** The position-hash change did not fix
    it. Possible causes: ISM vertex-factory UV handling on SM5, or something in
    `M_SoraArch` under ISM. Re-test on SM6. If it persists, use one component
    per module or Nanite instances, and find the root cause before shipping.

## 4. Next work, in priority order

1. **Set up and verify on the M2 (§5).** Rebuild Content/Generated, confirm
   SM6 and Nanite, re-run `SoraCapture.ArtReview.Dojo`, and record a baseline.
2. **Unique Nanite wood: the user's explicit request.** Replace the box
   columns, beams, boards and rails with one-off high-resolution timbers
   (about 0.5–1.5 M triangles for a 7 m column). Requirements:
   - **3D growth-ring field.** Each piece is cut from its own log: random pith
     offset and axis, taper and ring wobble. Grain therefore stays consistent
     across faces and end grain shows rings.
   - **Geometric detail:**
     - chōna-hatsuri adze scallops on hewn members, planed faces elsewhere;
     - weathered raised grain (uzukuri: latewood proud by 0.2–0.5 mm);
     - drying checks, V-shaped, tapering, oriented by the pith;
     - knots, worn chamfers (men-tori), dents and nail holes;
     - real joinery at beam ends and column tops.
   - **Look:** soot patina (susu) and dust in recesses; lighter wear on edges.
   - **Materials and LODs:**
     - For Nanite, use a micro-normal material (grain only) as the **Nanite
       Override Material**, because the geometry carries the macro detail.
     - For the fallback (M1 Macs), bake the macro detail from the high
       resolution into normal and AO maps.
     - Set Nanite fallback triangle percent or relative error so the fallback
       stays light.
   - **Variants:** about 8–12 columns and 8–12 beams, distributed with
     rotation and flip so no two neighbours match.
   - **Measure** GPU time, Nanite stats and memory.
   - Apply the same approach to floorboards (per-board geometry with wear
     paths) and to stone.
3. **Lighting rig** in `Source/SoraArena/Private/World/SoraWorldBuilderLighting.cpp`:
   - **Today's rig:** a 25-lux sun, an overcast cubemap and histogram exposure.
     Volumetric fog is Windows-only.
   - **Target:** chapter 1's per-beat time of day (`docs/campaign/chapter-01.md`
     §2). For b01, dawn at azimuth 72° and elevation about 2°, raking through
     the east renji-mado; later beats run to golden hour. Keep one retained
     rig updated from `StageKit` rather than spawning lights per beat.
   - **Codex's constraints:**
     - `Combat/SoraStealth.cpp` `LightAt` uses the maximum directional
       intensity and point-light radius; ambient reaches 1000 permille at
       25 lux. Do not change absolute intensities without a stealth review.
     - Run CrouchAndCover, Detection and LampsAndFloors afterwards.
     - `test_environment_presets.py` asserts the literal 25 lux, 0.65 sky,
       −0.45 EV and 0.0045 fog values. Update source, presets and tests
       together.
   - Enable volumetric fog on capable Macs and measure its cost.
4. **Dojo dressing with the SORA mark:**
   - Kamiza alcove (east wall, which faces the player at the b02 start): a
     hemp maku with the SORA mon dyed indigo, backlit through shoji at dawn so
     the mon reads in silhouette. Kamidana, katana-kake, and the raden bunko
     placed on the kamiza (collectible `ch01.c03`, "lacquered box on the
     kamiza").
   - Chōchin lanterns with the mark, to replace the corner lantern posts.
   - Replace the cargo stacks inside halls (wrong for a dojo) with nagamochi
     chests and stands that fill the cover envelope exactly: 2.3 × 1.8 × 1.4 m
     at (9080/9656/10232, ±780). The collision boxes stay.
   - West wall: the name board (名札掛け), headed by the mon.
   - Lesson-ring visuals for production sites 0/1 at (11096, ±520). They are
     red primitive cylinders today.
   - A garden visible through the open south bays: engawa, maples, pagoda and
     mountain vista. Enclose it so the route corridor at y ≈ −12000 is hidden.
5. **First-person paws:**
   - Today the viewmodel (`SoraViewmodelComponent.cpp`) has no arms. Its only
     animation is procedural pitch snaps. Chapter 1 always uses
     `SM_Nyaagyu_DojoBokken`.
   - Build skeletal grey-tabby and white paws in indigo kote, with the SORA
     mark on the tekkō. Give them an IK grip on the weapon, plus real swing,
     guard, parry, draw and sheathe motion. Gameplay timing, reach and rules
     must not change. For cards versus strands on SM6, measure first.
6. **Katana and saya** per the research doc. SORA mark on the menuki, habaki
   engraving and saya maki-e or raden.
7. **Bunko polish:**
   - leaf composition, which is too uniform (Codex flagged it);
   - takamaki-e relief;
   - a braided cord texture, since the cord is smooth bright red now;
   - nashiji gold-flake interior.
8. **Provenance before any commit to master:**
   - Add OWN-tier ledger manifests for SoraCraft and NyaagyuDojoKit outputs,
     then run `python3 scripts/assets/validate_asset_ledger.py`.
   - Update the CC0 records' `used_by`.
   - Regenerate `ThirdPartyNotices/ASSETS.md` with
     `generate_asset_notices.py`.
9. **Delete superseded code** once replacements are in and verified:
   - the box dojo kit after the Nanite timbers land;
   - the cargo-in-hall path;
   - cat-base v6–v10 generators once a new Nyaakoto exists;
   - the static `SM_NyaagyuSamurai` prototype path;
   - the decimated-LOD path in `create_runtime_weapon_lib`.

   List each deletion for Codex first.
10. **"Very fun"** (coordinate any gameplay code with Codex):
    - hit-stop and camera kick on clean cuts;
    - a slow-motion beat on a perfect parry;
    - a vermilion SORA seal (朱印) stamp effect on objective completion;
    - tameshigiri tatami-omote targets that actually slice;
    - kamon banners and lanterns that react to blade swipes;
    - hidden SORA omamori collectibles.

## 5. Setup on the M2

Steps in order:

1. Run `git fetch && git switch claude/photoreal-art` (or make your own
   worktree), then `git lfs pull`.
2. Install the pinned tools: UE **5.8.3 CL 58210709** at
   `/Users/Shared/Epic Games/UE_5.8`, Blender **5.2.2**, Xcode **26.1.1**
   (project-scoped through `scripts/toolchain/doctor.py`) and Rust 1.97.1.
3. Run `scripts/toolchain/doctor.py --json`.
4. Ask the user before downloading the CC0 cache:
   `python3 scripts/assets/fetch_cc0.py --dry-run`, then the fetch.
5. Run `scripts/toolchain/build-mac.sh Development`.
6. Run `scripts/toolchain/import-mac.sh` (base art, palette, VFX and audio).
7. Run the art importers:
   - `scripts/toolchain/run-editor-script.sh scripts/unreal/import_sora_craft.py SORA_CRAFT_IMPORT_COMPLETE`
   - `scripts/toolchain/run-editor-script.sh scripts/unreal/import_nyaagyu_dojo_kit.py NYAAGYU_DOJO_KIT_READY`
8. Capture:
   - `scripts/toolchain/capture-editor-game.sh SoraCapture.ArtReview.Dojo` (in-game frames)
   - `scripts/toolchain/run-editor-script.sh --editor scripts/unreal/render_sora_lookdev.py SORA_LOOKDEV -- props=SM_SoraRadenBunko out=Bunko rigs=golden,overcast,lantern` (editor look-dev)

**Gotchas:**

- The editor binary's `-game` mode needs `DEVELOPER_DIR` set to the pinned
  Xcode. The capture script handles it; otherwise it fails with "Xcode not
  found".
- Texture parameters on a Normal or Masks sampler need a default texture of
  the same type, or the material fails to compile on Metal.
- Revolved discs in the Blender lib need smart-projected UVs. Loft travel UVs
  leave a long strip that the bake cannot resolve.
- Blender's collapse decimation breaks UV seams. Let Unreal reduce LODs.
- Never run Unreal or Blender in a checkout someone else is using.

For packaged builds, stage `libarena_ffi.dylib` (`cargo build --release -p
arena-ffi`, then `scripts/unreal/stage_kernel.py`) and
`libconnect_norito_bridge.dylib` (`scripts/connect/build-bridge.sh`).

## 6. Coordination with Codex

On the M1, Codex (gpt-6-astra, ultra reasoning) shared the work through
`Local/Coordination/{codex-to-claude,claude-to-codex}.md` in the main checkout.
Each agent owns its own file and a `STATUS:` line marks who holds the
engine/GPU slot.

**Agreed ownership:**

- **Codex:** recovery integration, tests, master pushes, proofs and
  economics, the wallet and Connect, Iroha, and the gameplay files
  `SoraFieldcraft*`, `SoraStealth*`, `SoraCampaignDirector.cpp` and
  `ArenaWalletSubsystem.*`.
- **Claude:** art (`Content/SourceArt`, `scripts/art`, art importers in
  `scripts/unreal`, art docs, provenance) and presentation-only C++. List
  presentation files for Codex before editing them.

Codex's standing asks:

- Do not auto-merge unqualified art into master.
- Label every capture type: Blender source, editor look-dev, editor-binary
  game and packaged game.
- Keep visual captures separate from performance evidence.
- Run Campaign.Spaces and Playthrough after placement changes.

If Codex runs on the M2 too, set up the same files.

## 7. Honest status

Nothing yet meets the photoreal gate.

- The dojo interior is a first pass of box modules under the old overcast
  rig. It looks like an empty hall:
  - no dressing, maku or lanterns;
  - cargo crates still stand inside;
  - textures are blocky on the instanced path.
- The bunko is a credible lacquer prop in look-dev but needs polish.
- Characters, first-person paws, weapons, horses and exteriors are untouched
  in this session.
- No Windows, Nanite, packaged-build or performance evidence exists.
