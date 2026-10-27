# First-launch saves and required dojo rails

Signed SOURCE `c4b47fbb15548b66e9d1f3d2fc5fcd954c59e45b`, tree
`e074452fec81ceb5578c2b018c677579ac59a47c`, checks that a campaign, settings or
controls save slot exists before attempting to load it. A missing slot uses
the existing defaults without a failed-read diagnostic. Existing unreadable
or invalid saves still follow the existing load, validation and recovery path.

A fresh isolated editor build succeeds in 20.77 seconds. All 15 exact selected
native cases pass with zero selected errors/warnings: disk recovery, forged
saves, save round-trip, assisted campaign, isolated profiles, hold/toggle,
state-gated keys, controls remapping, graphics presets, key prompts, save
schemas, settings persistence, sound captions/subtitle layout, telegraph
palettes and keyboard/pad screen navigation. The run ends naturally at
06:29:51 UTC with all source/native/Config/Generated inputs unchanged.
Twenty original evidence files independently verify. Nineteen pre-initialization
`Condition failed` diagnostics remain in the raw editor log, as in earlier
runs; the selected tests have no errors. This is NullRHI evidence, not gameplay
or packaged qualification.

The 5b45 package's four missing required meshes were present as verified source
FBXs but absent from generated content: `SM_DojoRail_Nageshi`,
`SM_DojoRail_Cornice`, `SM_DojoRail_Koshi` and `SM_DojoRail_Nuki`. They were
restored through the full production `import_nyaagyu_dojo_kit.py` importer in
the isolated SOURCE worktree. No fallback existence check was added to hide
missing required assets.

Before import, all 32 source/raw input files are hash-checked, and all 1,189
existing Generated files are backed up with verified bytes and separate
inodes. The importer rebuilds all 16 modules, scan/coffer textures and material
bindings. A separate editor process reopens every saved module. Source hashes,
triangle counts, full conventional fallback geometry/attributes, LODs,
material bindings, dedicated Nanite source identity and built Nanite resources
match the recorded import audit. Readback does not mutate Generated. There are
46 changed generated files, exactly four additions and no removals, all within
the permitted kit/material scope. Frozen integration ROOT and raw cache remain
unchanged. The source/art input manifests and importer code were not changed.

The saved-asset review checks 18 originals and the full backup. Geometry
readback uses the existing shared `dojo_nanite` helper; the independent review
compares its recorded content digests and source identity. The first review
stopped on a literal relative/absolute path comparison. Unreal's path resolves
from `Engine/Binaries/Mac`; the corrected check verifies that resolved file
and its exact source hash. The original observation is retained. Import and
readback retain respectively 82 and 41 CPU-access warnings from the editor
geometry inspection, plus 19 pre-initialization diagnostics each. No Python
errors occurred, and no CPU-access flags were changed to suppress warnings.

| Renderer | Observed result on M2 Ultra |
| --- | --- |
| SM6 | Metal Bindless (SM6); `SoraCapture.ArtReview.Dojo` passes with zero selected errors/warnings. Six original 1920×1080 frames, natural EOF at 06:37:54 UTC. |
| SM5 | Metal Bindful (SM5); the same exact test passes with zero selected errors/warnings. Six separate original frames, natural EOF at 06:41:27 UTC. This is not an M1 test. |
| Nanite | Saved enablement, full fallback preservation and built resource readback pass for all 16 modules. These Lit captures do not independently establish Nanite raster coverage or unique-beam quality. |

Each capture independently verifies 28 original files, six ordered screenshot
acknowledgements, PNG CRCs/dimensions, source identity, unchanged inputs and
natural editor/wrapper EOF. Neither log contains the missing rail diagnostics
or absent default-save diagnostics. Each retains 19 pre-initialization errors
and 23 other editor/startup/shutdown warnings outside the selected test.
The first capture reviewer stopped on the Unreal report's UTF-8 BOM; its
script and traceback remain, and the corrected reader accepts that encoding
without rewriting the report.

All 12 original images were viewed directly. The hall and rails render, but
window/lamp highlights lose detail, the ceiling is densely repetitive, timber
and floor grain repeat, bright floor seams are visible, and cargo/practice
proxies and incomplete dressing remain. This restores existing required assets;
it does not pass photoreal acceptance. No image was enhanced or upscaled.

Evidence remains under SOURCE `Saved/Qualification/2026-10-27/`, with prefixes
`first-launch-runtime-c4b47fbb-attempt1`, `dojo-kit-restore-c4b47fbb-attempt1`,
`dojo-restored-sm6-c4b47fbb-attempt1` and `dojo-restored-sm5-c4b47fbb-attempt1`.
The backup is `Local/Backups/dojo-kit-restore-c4b47fbb-before/Generated`.

| Review | SHA-256 |
| --- | --- |
| Native 15-case review | `a178bce762e0d2503b7d931e68505cff8c45e2b83bed21a4affe918e498355b9` |
| Saved-asset restoration | `4861358b7d27e2bcede8c6b97eeb5e9ce028bdb181de6de56349de9163771980` |
| SM6 capture | `0f5239a84403946921784bc694a998b5d6ef7bea169c7aedbc821f43ba8ba4a4` |
| SM6 visual inspection | `52a7f7ad9877f1e887d7116fb96fc9b168db8f062d7e95097a44a8f16132991b` |
| SM5 capture | `bcd35a9b7069c3585dc1840d0714d7033ec1e1aeba5f873d3a73d2edd68c4530` |
| SM5 visual inspection | `bfcc801bda35a75dcf174d4f96f6094ee1d86ffe5f6a0e2a0cdc9833661c451e` |

At this checkpoint, ROOT remains frozen at 5b45 for Claude's inputs. SOURCE
code and restored assets have not yet been adopted into ROOT or repackaged.
M1, Windows, ordinary play, final art and release qualification remain open.
