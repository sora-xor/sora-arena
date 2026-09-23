# Unreal offline slice

The project targets **Unreal Engine 5.8.2**, Windows and macOS. An offline prototype is in source. The Mac editor target compiled with installed **5.8.3**, changelist **58210709**, in an isolated diagnostic worktree after adapting the source to its APIs. The original art and CC0 palette imported in that isolated checkout, and an editor validator loaded 59 manifest-declared packages with their expected Unreal types. This is an import/type check; play, rendered art quality, packaging, and the exact 5.8.2 release build remain open. Xcode 26.1.1 is installed for macOS; the Windows toolchain and packaged build remain unverified. An earlier diagnostic attempt using 5.2 stopped at SDK validation before compiling source.

## Rendering configuration and acceptance gate

The source-controlled rendering path is defined in `Config/DefaultEngine.ini`,
`Config/Windows/WindowsEngine.ini`, `Config/Mac/MacEngine.ini`, and
`Config/DefaultScalability.ini`. Unreal loads the platform Engine file after the
project default, and project scalability sections customize the engine's
High (`2`) and Epic (`3`) tiers. This follows Epic's [configuration hierarchy](https://dev.epicgames.com/documentation/unreal-engine/configuration-files-in-unreal-engine),
[scalability reference](https://dev.epicgames.com/documentation/unreal-engine/scalability-reference-for-unreal-engine),
and [device-specific optimization guidance](https://dev.epicgames.com/documentation/unreal-engine/optimizing-and-debugging-projects-for-realtime-rendering-in-unreal-engine).

| Path | Configured behavior | Intended use |
| --- | --- | --- |
| Windows quality | DX12/SM6, Lumen GI/reflections, TSR, Virtual Shadow Maps, hardware-ray-tracing support, and MegaLights at Epic shadow tier (`sg.ShadowQuality=3`) | Supported RTX 4070-class reference hardware at 1440p |
| Windows competitive | The same Windows cook at High scalability (`2`), with `r.MegaLights.Allow=0`, High shadow/GI/effects tiers, and no motion blur or gameplay depth of field | Lower-cost, readable combat presentation; requires profiling and tuning |
| macOS M1 Ultra | Metal SM6, software Lumen with mesh distance fields, TSR, conventional shadowing, Nanite fallback meshes/LODs, and no MegaLights or hardware ray tracing | 1080p M1 Ultra reference path |

The existing common renderer settings enable Lumen, mesh distance fields and
TSR. The Windows configuration targets DX12/SM6 only, with the DX11 fallback
shader format removed, and enables support for hardware ray tracing and
MegaLights. Epic describes MegaLights as production
ready in [UE 5.8's release notes](https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-8-release-notes),
which also introduces `r.MegaLights.Supported` to control shader compilation,
and documents `r.MegaLights.Allow` as a [scalability switch](https://dev.epicgames.com/documentation/unreal-engine/megalights-in-unreal-engine).
The quality tier allows it; the competitive tier disables it. MegaLights is a
Windows quality option for hardware meeting Epic's [DX12/SM6/ray-tracing requirements](https://dev.epicgames.com/documentation/unreal-engine/hardware-and-software-specifications-for-unreal-engine),
not an assumption about every Windows GPU. The competitive tier still cooks
ray-tracing support, so its actual memory and frame-time benefit remains to be
measured.

Epic's [UE 5.8 Mac requirements](https://dev.epicgames.com/documentation/unreal-engine/macos-development-requirements-for-unreal-engine)
list software Lumen and TSR for M1+, while hardware Lumen/MegaLights require
M2+ experimentally and Nanite/Virtual Shadow Maps require M2+ in beta. The Mac
configuration therefore disables hardware ray tracing, MegaLights, Nanite, and
Virtual Shadow Maps. It keeps the common Lumen and distance-field settings;
[Lumen's software tracing path](https://dev.epicgames.com/documentation/unreal-engine/lumen-technical-details-in-unreal-engine)
uses mesh distance fields. `r.Nanite.ProxyRenderMode=0` selects the ordinary
fallback when Nanite is off, as described in Epic's [Nanite technical details](https://dev.epicgames.com/documentation/unreal-engine/nanite-technical-details).
Every production asset must still provide a usable conventional LOD or fallback
mesh and card-fur route. These files cannot create missing geometry or prove
that the current prototype assets are visually acceptable.

High (`2`) and Epic (`3`) are the source-controlled preset tiers. A graphics
menu must apply them through Unreal's
[`UGameUserSettings::SetOverallScalabilityLevel`](https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/Engine/UGameUserSettings)
and save the setting; that player-facing selector is not implemented yet. The
Mac build currently uses an M1-safe platform baseline across Macs, without a
separate M2+ experimental profile. Target-hardware validation must inspect the
effective renderer/scalability CVars, cooked shader formats, fallback meshes,
and visual output, then measure representative combat with `stat unit`,
`stat gpu` and GPU profiling. The acceptance targets are 60 fps at 1440p on the
RTX 4070-class Windows reference machine and 1080p on the available M1 Ultra.
No UE 5.8.2 editor or packaged build has run these presets, and neither frame
rate nor photorealistic quality is verified.

## Implemented source

`SoraGameMode` starts a procedural arena from the engine Entry map. `SoraCharacter` provides first-person movement, sprint/jump, weapon selection, ammunition/reloading, line-of-sight gunfire, swept melee, explosive projectiles, and simple enemy movement/attacks. Four arena layouts use generated architecture, cover, torii, lamps and production devices. The campaign has eight Japanese encounter outlines and 24 distinct production-site tasks with English subtitle text. The opening dojo encounter uses wooden-sword visuals and nonlethal sparring pupils; alien opponents appear only after the invasion. A site can require defeated opponents and an earlier site; the interface shows its name, and the world builder gives eight site types distinct prototype geometry and a visible activated state. Checkpoint loading rejects site progress inconsistent with those requirements. The campaign still shares a restore/defeat/exit mission loop; these are not eight finished authored levels or a 6–8 hour experience.

The version-four offline save records each chapter's defeated-opponent count, three restored production sites, and completed exit state after every objective event. Earlier prototype saves are not interpreted under these rules. Restarting the game, returning from practice, changing class in the menu, or retrying after defeat reconstructs that checkpoint. New campaign and chapter advance clear it; unfinished opponents respawn from the remaining count. Round resets also destroy live campaign explosives before spawning the restored encounter, so a shell from a previous attempt cannot damage fresh opponents or advance their kill count. The save has no wallet, bond, or NFT state. Actual UE save serialization, projectile cleanup, and play recovery still require an editor run.

The runtime catalog contains the six approved classes, eighteen approved weapon IDs, eight chapters and four maps. Its damage tuning applies **only to the campaign and ordinary training prototype**. The separately selectable deterministic practice mode reads combat tuning and all outcomes from the actual Rust kernel. Neither mode produces a qualified execution proof or settles money.

The camera enables UE 5.8 native first-person field of view and scale. The
owner's authored or fallback weapon mesh uses `FirstPersonPrimitiveType::FirstPerson`
with a 70-degree viewmodel FOV and 0.6 scale; this keeps the weapon readable while
reducing clipping into nearby architecture. It changes presentation only. The
current source does not yet include a finished first-person feline paw rig or
the separate world-space representation needed to validate self-shadowing and
reflections. The implementation follows Epic's [first-person rendering guide](https://dev.epicgames.com/documentation/unreal-engine/first-person-rendering)
and [UE 5.8 component API](https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/Engine/UPrimitiveComponent);
actual rendering still needs the pinned editor and target hardware.

Japanese is the primary UI/story language. Catalog schema 2 includes six speaker identities and three timed, original Japanese dialogue cues per chapter, each with an English subtitle. The HUD displays a cue while combat and objectives continue; opening dialogue pauses with the campaign menu and does not replay when an objective checkpoint is resumed. English subtitles are on by default and persist through the save setting. No dialogue cursor is saved. `scripts/unreal/validate_content.py` checks speaker references, bounded nonoverlapping timing, text lengths, and every catalog glyph against the shipped Noto Sans CJK JP font. The font includes its SIL OFL license and copyright notice. Voice acting is not recorded; timing and readability still need an Unreal playtest.

`DefaultGame.ini` sets the game culture to `ja`, replaces inherited packaging cultures with `ja` and `en`, and selects the `EFIGSCJK` ICU data preset, which contains both Japanese and English. The culture loader and packaging property/enum names were checked against installed engine source; packaged behavior in the pinned 5.8.2 engine remains to be verified. This game setting does not change the Unreal Editor's preferred language.

The menu calls the real `UArenaWalletSubsystem`; C starts pairing, L opens an available wallet deep link, and X disconnects. It never marks a bond funded merely because a wallet connects. Details are in `connect.md`.

`UArenaKernelSubsystem` dynamically loads the actual staged Rust library, requires its current presentation exports, requires exactly ABI 3, executes a sixty-tick zero-deposit diagnostic, and reads its actual qualification flag. Missing exports or any other ABI version reject the library before layout-sensitive calls; no fallback or alias is provided.

### Deterministic practice source

The menu's **P / 武芸稽古** action creates a ten-minute, six-participant free-for-all practice session with zero base bond and zero deposits. Five local bots generate ordinary canonical inputs; they have no privileged damage or movement path. A visibility graph around the reference obstacles supplies simple bot navigation. This is offline practice, not networked P2P play.

The shared `FSoraPracticeClock` advances at 60 Hz with at most eight steps per rendered frame. Menu time is discarded; a long rendering hitch slows simulation time instead of skipping input ticks. Each step reads player health, positions, cooldowns and respawns, consumes that tick's events before advancing, and updates stable-ID projectile visuals. Millimeters convert to Unreal centimeters and feet positions gain the queried capsule half-height. Map obstacles and capsule/eye dimensions come from native queries. Perimeter lines mark movement limits without inventing bullet-blocking boundary walls.

In this mode, Unreal CharacterMovement is disabled, transforms come from snapshots, and Unreal damage/healing callbacks cannot change health. Tracers clip cosmetically against displayed geometry; hit markers come only from kernel damage events. The HUD displays actual kernel ammunition, magazine capacity, reload ticks, stamina/cooldown, and weapon-bound charge progress. Every practice pawn's weapon pose follows that same charge snapshot, providing a provisional visible windup cue. The combat HUD shows remaining match time; raw state hashes remain available through diagnostics and replay reports. R queues the canonical reload input (bit 32); bots request the same input when empty. Magazine-zero melee weapons display their melee label. No Unreal timer can refill kernel ammunition or complete a charge. Campaign ammo/reload data is not used for practice counters. Menu keys 1/2/3 select a loadout and restart practice; loadouts remain fixed during the session. Right click still invokes the class melee attack. Death triggers the kernel's automatic respawn with no financial movement. Windup visibility and readability still require an Unreal playtest.

`scripts/unreal/verify_practice.py` runs the real staged library through 72 map/class/loadout scenarios and repeats 86,400 ticks across independent handles. It checks matching transcript hashes, zero deposits, invalid-input atomicity and terminal immutability. A targeted clear-sightline scenario verifies death and respawn events. It also compiles and executes the exact shared clock header at multiple frame rates and under long hitches, pauses and invalid deltas. The report is written to `Saved/Diagnostics/practice_replay_report.json`. These native checks do not replace the still-pending Unreal compilation, input, visual and play tests.

`scripts/unreal/verify_parity.py` supplies the stronger cross-platform regression gate: repository-pinned binary canonical controls, explicit source/runner and ABI-layout identities, and expected state/event/presentation digests generated from the actual macOS kernel. It executes 73 scenarios and 44,100 ticks against immutable expectations, including all map/class/loadout combinations and a death/respawn case. It uses Python's standard library and the target-platform native library, so the same command runs on Windows and macOS without Unreal. See `scripts/unreal/fixtures/practice-abi3/README.md` for exact commands, field encoding and baseline-update rules. Eleven negative tests verify that altered inputs/layouts/identities/digests fail and that an obsolete pass report cannot survive a failed new run. **Only macOS arm64 has passed so far; Windows parity remains unverified.** Compare successful reports from both hosts against the same manifest hash before claiming parity.

## Build and authoring order

1. Install the requested UE 5.8.2 and supported compiler/SDK, then build the `SoraArenaEditor` target using the repository's engine tooling. The `.uproject` engine association remains 5.8; the import script additionally checks the 5.8.2 patch version.
2. Build the Rust library with `cargo build --release -p arena-ffi`. Run `python3 scripts/unreal/stage_kernel.py` on the target platform. Staging checks real ABI/execution/zero deposits before copying the library into `Binaries/Mac` or `Binaries/Win64`.
3. The original source art is already generated. To regenerate, run Blender in background with `scripts/art/create_original_assets.py -- --render`, then `scripts/art/rig_original_cats.py`, and separately `scripts/art/create_edo_environment_props.py`, `scripts/art/create_street_debt_terminal.py`, `scripts/art/create_nyaagyu_sluice.py`, `scripts/art/create_silk_foundry_loom.py` and `scripts/art/create_dojo_bokken.py`. The second command adds twenty-bone prototype rigs and keyed idle/walk clips; the environment generators create the lantern, torii, citadel debt kiosk, Lantern Ward street terminal, Nyaagyu irrigation sluice and Silk Foundry loom. `scripts/art/validate_edo_environment_props.py`, `scripts/art/validate_street_debt_terminal.py`, `scripts/art/validate_nyaagyu_sluice.py` and `scripts/art/validate_silk_foundry_loom.py` independently round-trip their FBX geometry, scale, material slots and UCX meshes in Blender. `scripts/art/validate_dojo_bokken.py` round-trips the bokken FBX after opening its editable blend.
4. Run `scripts/unreal/import_original_assets.py` through the compiled UE 5.8.2 editor Python interface. It imports static meshes, the original hero katana, dojo bokken, six environment props, skeletal meshes and animation clips, creates the runtime surface material under `/Game/Generated`, imports `Content/SourceArt/UI/Nyaagyu_Title_KeyArt.png` when present, and imports the hash-verified user-supplied SORA insignia as `/Game/Generated/UI/T_SoraResistanceLogo.T_SoraResistanceLogo`. The optional menu backdrop is explicitly labeled generated key art, not gameplay; controls and wallet pairing remain actionable overlays.
5. Open the project and Play. Without generated Unreal assets, procedural placeholder geometry still supplies the offline encounter; the imported skeletal cat and idle/walk assets are used when available. Neither asset route has yet been verified inside UE 5.8.2.

The art consists of original editable Blender geometry, source FBX files, and rendered previews. The detailed `SM_Nyaagyu_HeroKatana` prop is imported at `/Game/Generated/Meshes/SM_Nyaagyu_HeroKatana` and displayed when the Samurai selects ordinary weapon ID 0 in campaign or offline practice. If that imported asset is absent, the pawn loads `SM_Weapon_00`, then uses procedural geometry if neither mesh exists. The hero prop changes no weapon stats, entitlement, bond, or NFT access; its attached saya is currently a static visual. Its FBX material translation, position and scale still need visual inspection in UE 5.8.2.

The opening dojo sparring uses an original 1.067 m hand-shaped oak bokken from `Content/SourceArt/Weapons/Original`. Its editable blend, FBX, Blender preview, exact SHA-256 hashes and project-owned license are recorded in that folder's `manifest.json`. `scripts/art/create_dojo_bokken.py` regenerates the source and `scripts/art/validate_dojo_bokken.py` verifies an independent Blender FBX round trip, including dimensions, triangles and material slots. The importer targets `/Game/Generated/Meshes/SM_Nyaagyu_DojoBokken`; `SoraCharacter` uses it during dojo training and falls back to its existing wooden primitive when it is not imported. This only changes visuals: sparring remains nonlethal under the chapter-one combat rules. The Blender preview is not an Unreal screenshot; imported scale, materials and lighting still require UE 5.8.2 inspection.

Standard weapon ID 1 has an original `SM_Nyaagyu_ArcCarbine` source prop under `Content/SourceArt/Weapons/Original`: oxblood urushi lacquer over an iron receiver, aged bronze fittings, an indigo-wrapped grip, and exposed copper coils around a porcelain induction core. The editable Blender source has 84 components and a joined 12,532-triangle, UV-unwrapped FBX. Its local +X points toward the muzzle; bounds are 95.7 cm long, 12.5 cm wide and 39.3 cm high. The receiver/trigger origin is `(0,0,0)`, the grip web is approximately `(-11,0,-5)` cm, and the muzzle center is `(52.6,0,2.6)` cm. The FBX retains 12 material slots without machine-local texture paths; the blend links the existing SHA-256-pinned CC0 Poly Haven timber and rusty-metal PBR maps by project-relative paths. `arc_carbine_manifest.json` records exact hashes and license provenance, `scripts/art/create_arc_carbine.py` regenerates it, and `scripts/art/validate_arc_carbine.py` verifies the independent Blender FBX round trip, material slots, UVs and dimensions. The Unreal editor importer checks its hash and targets `/Game/Generated/Meshes/SM_Nyaagyu_ArcCarbine`; actual in-engine appearance, imported material fidelity and runtime performance remain unverified until UE 5.8.2 is available. The Blender preview is a source-art review, not an Unreal gameplay image. The mesh is visual only; standard weapon ID 1 damage and fire rules stay in the combat code.

Samurai special weapon ID 12 has a separate original `SM_Nyaagyu_MonofilamentNaginata` art-review source under `Content/SourceArt/Weapons/MonofilamentNaginata`: a 2.311 m smoked-oak/indigo-lacquer shaft, silk grips, bronze socket, forged curved blade and small ceramic/copper edge module. The editable Blender file retains 30 parts; the single UV-bearing FBX has 27,938 source triangles. Local +X points to the blade tip and +Z is up, with grip centers, bounds, license and SHA-256 hashes in its `manifest.json`; there is no muzzle on this melee polearm. All geometry and procedural Principled BSDF materials are original project-owned work with no external images or purchased assets. `scripts/art/validate_monofilament_naginata.py` independently checks the blend, FBX round trip, material slots and dimensions. `scripts/unreal/import_original_assets.py` declares import **only** to `/Game/ArtReview/Weapons`, and gameplay code does not load this review mesh. The two Blender images are source-art reviews, not Unreal screenshots or shipping photoreal-quality evidence. UE material translation, first-person grip, collision, lighting and performance await in-engine inspection; no combat statistics, bond rules or NFT entitlements changed.

Three original modular environment hero props are generated by `blender -b --factory-startup --python scripts/art/create_edo_environment_props.py`: a timber/washi lantern post, a lacquered Nyaagyu torii, and an alien debt kiosk with authored `負債 ∞` display geometry. The FBX exports and editable blend live under `Content/SourceArt/Environment/Original`, with bounding dimensions, meter units, source triangles, UCX collision boxes, hashes, material roles, and original-art license in its `manifest.json`. The Blender review renders `Edo_Alien_PropReview_Blender.png` and `Alien_DebtKiosk_Detail_Blender.png` are source-art checks, not game screenshots. Run `blender -b Content/SourceArt/Environment/Original/Edo_Alien_Props.blend --python scripts/art/validate_edo_environment_props.py` for an independent FBX round trip of scale, material slots, and collision meshes. Wood, stone, and rusty-metal source materials link to the separately hash-verified CC0 Poly Haven palette with project-relative paths in the blend. FBX exports keep the material slots but omit texture paths; the campaign world builder substitutes the corresponding Unreal PBR palette instances after import. The asset importer targets `/Game/Generated/Environment/Props`; the campaign displays the props when present and logs an explicit error if an intended visual prop is missing. The torii local X span turns 90 degrees to cross the estate road, the citadel kiosk also turns 90 degrees to face the objective approach, and the lantern point light is placed at its authored 2.52 m core. Deterministic multiplayer practice continues to use the kernel-derived collision geometry; these decorative props do not change combat simulation. Unreal import, material translation, in-game lighting, and performance remain unverified until a UE 5.8.2 build is available.

The occupied Lantern Ward also places the separate original `SM_Alien_StreetDebtTerminal` at a roadside position facing the central road. Its narrower twin-claw silhouette, circular lien scanner, declining debt tally and `徴収` levy mark distinguish it from the citadel kiosk. The 4,248-triangle editable Blender source, FBX, flat blockout/PBR comparison renders, UCX box, SHA-256 hashes and license record live under `Content/SourceArt/Environment/StreetDebtTerminal`. The source art links the already retained, digest-verified CC0 Poly Haven wood, rusty-metal and stone diffuse/normal/ARM maps by project-relative paths; original bronze, enamel and display surfaces add subtle procedural wear. The label uses the bundled SIL OFL Japanese font. The imported timber, metal and stone material slots map to the project's separately pinned CC0 Poly Haven Unreal palette. The comparison render is a Blender material review under identical neutral lighting, not an Unreal screenshot or proof of photorealistic gameplay. A simple collision proxy occupies the same campaign position whether the imported visual is present or the placeholder block is shown. Multiplayer practice never adds this prop. `scripts/art/validate_street_debt_terminal.py` checks the PBR image links, license and hashes alongside the Blender FBX round trip; UE 5.8.2 import, material binding, in-scene lighting and frame rate remain unverified.

The agricultural liberation chapter places an original `SM_Nyaagyu_IrrigationSluice` at each Nyaagyu Estate irrigation site. Its joined FBX shows a hand-cranked cedar lift gate between stone channel cheeks, with a small hostile flow/debt meter attached to the timber. The editable 10,524-triangle Blender source, review image, three UCX boxes and SHA-256 checks are recorded in `Content/SourceArt/Environment/NyaagyuSluice/manifest.json`. It reuses the separately pinned CC0 Poly Haven wood, stone and rusty-metal maps through project-relative Blender links; the Japanese plate uses the bundled SIL OFL font. The importer binds the same Unreal palette roles as the other environment props. The mesh is decorative and does not alter campaign objective collision or deterministic multiplayer collision. `scripts/art/validate_nyaagyu_sluice.py` independently checks the links and FBX round trip. The review image is a Blender render; UE 5.8.2 import, lighting and performance remain unverified.

The Silk Foundry chapter has an original `SM_SilkFoundry_LevyLoom` decorative prop: a timber floor loom with back warp beam, suspended heddles, reed, shuttle, treadles, cloth take-up, indigo silk and a bolted alien levy meter. Its separate editable Blender parts, 18,376-triangle FBX, four UCX boxes, review image, license and hashes live under `Content/SourceArt/Environment/SilkFoundryLoom`. The blend links the retained CC0 Poly Haven timber and metal maps with project-relative paths; the textile, bronze and display shaders are original. `M_Env_Timber` and `M_Env_Metal` material slots let the world builder bind the pinned Unreal PBR palette; authored textile and sci-fi surfaces require material review after import. The source's local front faces -Y and its levy meter projects from -X. The prop does not change canonical multiplayer collision. `scripts/art/validate_silk_foundry_loom.py` checks the linked images, font/license, hashes, geometry and FBX round trip. Its review PNG is a Blender source-art render; UE 5.8.2 import, lighting, textile translation and frame rate remain unverified.

The HUD loads the SORA insignia next to `SORA 抵抗軍 / 猫柳生` on both the campaign menu and in combat. The original SVG is preserved byte-for-byte with SHA-256 `d66413a71b70e25dcb8b2f118dcfe846a6446ed1db3de53ce88fc70c16ac0910`; the transparent runtime PNG has SHA-256 `f6d9573096e7e044e9e4a84d739bf724281c4f394131812e1a6eeac915c8a39d`. `Content/SourceArt/UI/sora_logo_manifest.json` records the rasterization provenance. The user supplied the mark for this game; it has no claimed CC0 or general redistribution license. The editor import and actual in-game appearance still need verification in UE 5.8.2.

The anatomy pass adds narrower facial proportions, orbital lids, short geometric guard-hair cards, folded fabric and laced armor. These remain stylized prototype assets. They are not production photorealistic cats, groom assets, refined skin weights, cinematic animation or qualified shipping content.
`Content/SourceArt/Concepts/Nyaagyu_Photoreal_Character_Target.png` is the
separate photoreal art-direction reference for tabby fur, worn indigo cloth,
lacquered armor, rain and lantern lighting. Its JSON record pins the exact
image-generation prompt and SHA-256. It is 2D concept art, not a mesh, texture
set, in-engine screenshot or proof of final visual fidelity. The generated
background emblems are incidental art, not the supplied SORA mark.

### Nyaagyu Estate production surface palette

Powered by [Poly Haven](https://polyhaven.com). The source environment palette contains actual production assets, with exact download URLs, author credits, CC0 declarations, upstream checksums and SHA-256 hashes in `Content/SourceArt/Environment/PolyHaven/manifest.json`:

- [Wood Planks Dirt](https://polyhaven.com/a/wood_planks_dirt), 4K weathered timber.
- [Stone Floor](https://polyhaven.com/a/stone_floor), 2K worn paving.
- [Brown Mud Leaves 01](https://polyhaven.com/a/brown_mud_leaves_01), 2K organic soil.
- [Rusty Metal 02](https://polyhaven.com/a/rusty_metal_02), 2K machinery metal.
- [Kloofendal Overcast Pure Sky](https://polyhaven.com/a/kloofendal_overcast_puresky), 4K HDR lighting and sky.

[Poly Haven's asset license](https://polyhaven.com/license) permits commercial use and redistribution under CC0. [Its current API terms](https://polyhaven.com/our-api), dated July 18, 2026, also permit commercial use with credit. No website preview renders, avatars or logos are included.

`scripts/art/fetch_polyhaven_palette.py` downloads this fixed production selection and verifies upstream checksums. `scripts/unreal/validate_environment_palette.py` checks every retained hash, size and channel. After the editor module is built, run `scripts/unreal/import_environment_palette.py` in UE 5.8.2. It creates world-aligned surface material instances at their recorded physical sizes, uses DirectX normals without flipping their green channel, and maps packed ARM channels to AO, roughness and metallic. The world builder assigns timber, stone, soil and metal to the generated architecture. The Estate uses the imported HDR cubemap for sky illumination and its visible sky dome when those assets exist. Editor material compilation, visible tiling, color space and actual frame performance remain unverified until UE 5.8.2 is available.

`scripts/art/render_environment_palette.py` renders the retained production textures and HDRI in Blender. Its `Nyaagyu_PBR_Palette_Preview.png` is a source-material inspection image, not an Unreal runtime screenshot.

## Controls

| Key | Action |
| --- | --- |
| Enter / Esc | Continue or retry from the latest campaign checkpoint / menu |
| F1–F6 | Select class in menu; restarts the encounter |
| N / M | New campaign / change training map, in menu |
| B | Return to the saved campaign chapter from practice |
| P | Select deterministic offline practice, in menu |
| WASD / mouse | Move / aim |
| Left click / right click | Fire / melee |
| 1 / 2 / 3 | Primary / melee / special weapon preview |
| R / E | Reload / activate nearby workshop or exit gate |
| Shift / Space | Sprint / jump |
| F10 | Toggle English story subtitles |
| C / L / X | Pair / open wallet / disconnect, in menu |
| Ctrl / Q | Block / class ability, in deterministic practice |

All special weapons are available for offline practice. No bonds or NFT ownership are required for this development preview. Campaign weapon selection preserves that weapon's ammunition, and campaign death retries from the latest saved objective checkpoint. Deterministic practice locks the selected weapon for each session and automatically respawns defeated players. Neither route risks assets.

## Verification and remaining gates

`python3 scripts/unreal/validate_content.py` checks the catalog IDs/assignments, Japanese default, English narrative coverage, source FBX headers, pinned font hash and—when fontTools is available—actual glyph coverage of all Japanese catalog/source text. `stage_kernel.py` validates the loaded binary independently of the Unreal wrapper, including map/weapon queries, presentation snapshots, per-tick events and stable projectile IDs. Blender generation and rig export ran successfully.

Required next checks are actual UE 5.8.2 compilation/UHT, import-script execution, asset orientation/scale/material inspection, controller/mouse input, Japanese layout at multiple resolutions, chapter save/retry, deterministic-practice mode transitions and respawn, all weapon interactions, bot navigation, skeletal deformation and animation switching, and packaging on both platforms. Networked UE gameplay, strict-P2P rollback integration, authored production environments, professional character art, audio and a proof-qualified live money path remain unfinished.
