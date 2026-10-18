# Claude work recovery and master integration

Recovery date: 2026-10-18. The request was to find the latest interrupted work
and incorporate it into `master`, preserving source and unfinished assets.

## Recovered history

At the start, local and remote `master` both pointed to `a139b26` (the initial
commit). The main development checkout was `codex/nyaagyu-rebellion` at
`bf964f09517e88b75316eaaef9a07dcdc4a817c9`, with additional uncommitted art.
The recovery branch is `codex/claude-recovery-2026-10-18`.

| Source | Recovered tip | Integration |
| --- | --- | --- |
| Main development history | `bf964f09517e88b75316eaaef9a07dcdc4a817c9` | Recovery branch base; includes the earlier AI, campaign and practice work |
| Uncommitted main-checkout art | [Exact inventory](art-inventory.json) | Snapshot commit `f4e8a16`; 343 inventoried source files plus recovery records |
| `lane/gameplay` | `2cfa9691302931e7f2ac0d447a3098453ebc53b5` | Merge `ab95c12`; fieldcraft, arms controls, companions and expanded campaign sets |
| `lane/audio` | `b4c2fe127fde36e4ac406767f44ecf50ebb60f41` | Merge `fd33d10`; CC0 derivatives, runtime cues, buses, captions and tests |
| `lane/env` | `ca9e2c4bf319ae4b0e2125ea1a35f4936e7ac2bb` | Merge `3fd48d6`; CC0 environment materials, presets, imports and validation |
| `lane/vfx` | `ba0aa2b07562f369fcd474628397af3b6e5934a8` | Merge `bdd2788`; textures, Niagara authoring, previews and import gates |

The lane histories contain 17 commits beyond their shared fork point. Original
branch histories are retained by merge commits. All four lane worktrees were
clean before recovery; their ignored generated packages and caches remain in
place. No worktrees, source branches or ignored working files were deleted.

Local Claude session records corroborated the interrupted work streams; their
private conversation contents are not copied into the repository. Git object
and reflog inspection found older stash/amend objects, but no newer lost commit.
The detached `ue583-diagnostic` worktree holds older September 23–24 source and
rejected study inputs. It is preserved separately; its superseded sources were
not copied over newer development files.

## Integration decisions

- Keep main's packaged-build fixes, including case-insensitive input-state
  lookup and the saya mesh's navigation exclusion, alongside the new controls.
- Regenerate Japanese and English localization resources from the combined
  text sources and translation catalog, retaining both gameplay and audio keys.
- Combine original art, palette, CC0 environment, Niagara and audio import
  paths. Preserve every source check and completion gate, including the VFX
  rendering requirement and protection against partial imports.
- Keep the unapproved CC0 environment library out of cooked releases. Recovery
  does not authorize unreviewed art for runtime use.
- Preserve unfinished art exactly, including stale records and the interrupted
  W14 preview. [The art audit](README.md) distinguishes recovery from validation.
- Update central CatBaseV6 CC BY derivative statements for the recovered work
  and retain them across source reacquisition. This resolves the attribution
  follow-up noted in the snapshot audit without changing its inventoried bytes.
- Move duplicated audio math helpers to a shared private header. The combined
  Unreal unity build exposed two same-translation-unit redefinitions; the fix
  retains unity compilation and the original audio behavior.
- Keep charging riders clear of the hero's actual position, and keep convoy
  netters on their assignment while reloading instead of resuming an unrelated
  attack that dismounts the hero. Correct test scenarios that skipped living
  guards, starved a later wave behind the opponent cap, walked a cart away from
  its attackers, entered a chapter exit during a landing test or waited beyond
  a searchlight's lock deadline. Preserve their original behavior assertions.
- Resolve automation output paths before launching Unreal so relative report
  directories are written where the wrapper expects them.
- Record the roof at climb completion so an immediate drop retains its correct
  landing-noise source. Separate current searchlight visibility from fading
  suspicion, and lock lights to detection evidence. Repeated generic alert barks
  must not reveal the hidden player's current position.

The requested [Claude art handoff](../../art-direction/CLAUDE_ART_HANDOFF.md)
is included with the recovered state, modeling/material requirements, historical
research obligations and in-engine visual evidence requirements.

## Validation

| Check | Result |
| --- | --- |
| Rust `cargo test --workspace --locked` | 255 passed, 0 failed; five long research-network tests remain explicitly ignored by the default suite |
| Integrated content/gameplay/localization | Ten commands passed; 133 campaign beats, 1,032 bilingual lines, 438 native localization keys |
| Audio source checks | Six commands passed; 235 WAVs passed QA; quick mode did not rehash the entire private raw-download cache |
| Environment library/preset tests | 55 passed |
| Environment Custom HLSL | Eight expressions compiled for SPIR-V and DXIL under HLSL 2018 and 2021; negative controls rejected |
| Importer/VFX/preview host tests | 17 passed, including the combined pipeline, required counts and partial-import rejection |
| Asset-ledger unit tests | 26 passed |
| Cat attribution reacquisition regression tests | Six passed |
| Third-party notices freshness | Passed |
| Git LFS current-tree integrity | Passed; all 1,762 historical LFS objects needed by the recovered history were present locally |
| UE 5.8.3 Mac Development Editor build | Passed after the audio unity fix |
| Actual Unreal audio import and validation | Passed; 235 SoundWaves plus bus/mix assets, 267 packages loaded with expected types and routing; project Config unchanged |
| Targeted Unreal automation | The initial 53-test run exposed seven failures; fixes were exercised in subsequent runs. The broader recheck passed 51/53, then both remaining Ladders/Searchlights cases passed focused verification. Final changed-subsystem regression at `0e58c02`: **35/35 passed** (27 Fieldcraft, full Campaign.Playthrough, six Stealth and Integration.StealthZone), zero assertion errors. The 431 final-run warnings are temporary-world `UWorld::DestroyActor` teardown warnings. |
| Full source asset ledger | **Failed:** 216 stale weapon output records and 12 unrecorded renders belonging to intentionally withheld blockout weapons |

The 228 ledger errors are confined to the recovered `Weapons/Runtime` WIP
directory. Source inspection found no current runtime or importer references to
that directory or CatBaseV6; the existing imported weapon path uses the older
top-level source meshes. This is not a cooked-package audit and does not waive
the failing ledger gate. The original recovered manifests remain untouched.
The two campaign pacing overruns and Japanese literals outside the enforced
localization sources also remain visible in the host-check output.

Detailed local logs are under `Saved/Recovery/2026-10-18/` and remain outside
source control.
This integration does not constitute full game, rendering, Windows, economic,
historical-accuracy or production-deployment qualification.

## Parallel art production

The running Claude session, **Sora photorealism and logo marketing**, acknowledged
the handoff and created `claude/photoreal-art` in the separate
`sora-arena-wt/art` worktree. Its first milestone is the SORA-branded first-person
hero kit: Nyaakoto's skinned paws/forearms and sleeves, katana/saya fittings, then
unedited gameplay captures at normal FOV. Claude owns source art, its import and
provenance work, and visual review. Presentation-code changes are coordinated
file by file before integration.

Codex owns this recovery, gameplay fixes, validation and final master push.
Local coordination uses separate author-owned files under
`Local/Coordination/`; these operational messages are not distributable source.
After the 35-test regression finished, Codex released the Unreal build/render
slot to Claude. Future art changes remain on Claude's branch until reviewed and
integrated; they are not represented as part of the recovered snapshot or as
completed photoreal assets.
