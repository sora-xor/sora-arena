# Recovered source art — 2026-10-18

This recovery preserves the main checkout's unfinished art and scripts when the
user requested that the latest work be incorporated into `master`.
[art-inventory.json](art-inventory.json) records the exact paths, SHA-256 hashes,
sizes, working-tree status and checks for **343 files (665.16 MiB)**. These are
recovered source bytes, not newly approved game assets. The inventory records the
source branch and HEAD; authorship is not inferred from filenames or timestamps.

## Recovered work and its limits

| Work | Preserved state | Remaining work |
| --- | --- | --- |
| `Content/SourceArt/Characters/CatBaseV6/` and `scripts/art/create_cat_base_v11.py`, `create_cat_base_v12.py` | Round-9 head and first-person paw Blender studies, eight textures, 11 fixed review frames, updated README; round-10 generator source | Round 9 has 11 of 21 fixed frames and no final paw frames. Its existing `manifest.json` still describes round 8 and has seven mismatched file hashes. No round-10 source output or render was found. No runtime import or photoreal approval. |
| `Content/SourceArt/Weapons/Runtime/` and `scripts/art/create_runtime_weapon_*.py` | All 21 weapon folders with Blender, FBX LODs, textures, records and 63 render paths; 11 generators/support scripts | Current specs deliberately hold IDs 3, 11, 13 and 16 back as blockouts. The README, top-level manifest and metric report predate later outputs. W14's last rebuild was interrupted (details below). No Unreal import or photoreal/historical approval. |
| `Content/SourceArt/Horses/NyaagyuAbumiTazunaStudy/` and its two generators | Five original 2K texture sets (15 PNGs) and texture manifest; mesh generator source | No generated study Blender file, FBX, renders or mesh manifest were found. All 15 recorded texture hashes match. |
| `Content/SourceArt/Weapons/NyaagyuYumi/HistoricalStudy/` and its two generators | Five original 1K texture sets (15 PNGs) and texture manifest; mesh generator source | No generated study Blender file, FBX, renders or mesh manifest were found. |
| `docs/art-direction/NYAAKOTO_PHOTOREAL_TARGET.md` | Latest note linking the wet-dojo concept reference | The reference remains 2D look-development material, not measured anatomy or a shipped asset. |

## Interrupted W14 output and stale records

`Content/SourceArt/Weapons/Runtime/Renders/SM_Weapon_14_Neutral_1m.png` is an
incomplete 65,536-byte PNG. Its IDAT chunk at byte 58,136 requires the file to
extend to byte 66,340; the file ends early and has no complete IEND. It is
preserved as recovered interruption evidence and must not be used as a valid
review image.

The W14 source, FBX LODs and textures were last written after its `build_record`.
Seven of its eight recorded hashes disagree with those files. The inventory lists
each mismatch. The other 20 weapon build records match all of their recorded
hashes. Matching hashes establish byte consistency only.

The Runtime top-level manifest has **216 mismatches in 218 recorded outputs**.
It lists 17 weapons and incorrectly calls the four later blockout outputs
unbuilt. The current manifest generator knows to hold those four back. Its
existing metric report has a 17/21 summary and does not validate the latest
rebuilt files. The 26 third-party input hashes in `sources_manifest.json` all
match. Do not present the old metric report as a current pass or refresh hashes
as a substitute for mesh validation.

The CatBaseV6 README also records a pending CC BY statement-of-changes update for
round 9. The existing source credits must be retained; the recovered README's
round-9 description is not a completed update to the central attribution ledger.

## Checks and exclusions

The recovery audit parsed all 17 recovered Python scripts and the recovered JSON,
checked recorded SHA-256 values and file existence, and checked the chunks, CRCs
and terminal IEND of all 196 recovered PNGs. The truncated W14 image is the only
PNG failure. No models were rebuilt, rerendered or imported during this audit.
No historical, photoreal, performance or release qualification was performed.

Ignored `Local/` caches, raw scans, private snapshots, logs, Blender backups and
generated Unreal packages are outside this inventory and remain outside source
control. No paid or restricted raw source assets were found among these recovered
paths. The cat sources retain their documented CC BY derivation; weapon bakes
retain their recorded CC0 input provenance.
