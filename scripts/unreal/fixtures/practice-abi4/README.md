# Native practice parity fixture, ABI 4

This repository fixture was recorded by executing the real Rust kernel on **macOS arm64**. Windows has **not** been run or certified. A passing report applies only to the host named in that report. It does not verify Unreal compilation, rendering, input integration, networking, on-chain proofs or settlement.

The fixture contains 94 cases and 99,043 canonical ticks. It replaces `practice-abi3`, which has been removed along with every ABI 3 loader; there is no ABI 3 fixture or compatibility path. The ABI 3 change log is in the Git history of `scripts/unreal/fixtures/practice-abi3/README.md`.

- **72 exercise cases:** every combination of four maps, six classes and three admitted loadouts, six players, free-for-all, 600 ticks each, all on `exercise.controls`.
- **`estate-death-respawn`:** a Teppō with a Coil matchlock kills slot 0 on Nyaagyu Estate; 900 ticks on `death-respawn.controls`.
- **21 scripted cases,** recorded from record-time scripted players (below):

| Cases | Mode | Players | Ticks | What they add |
| --- | --- | ---: | ---: | --- |
| `ffa8-<map>` ×4 | free-for-all | 8 | 1800 | eight-player FFA on every arena, specials, abilities and entities |
| `melee8-<map>` ×4 | Melee | 8 | 1200 | melee-only admission, guards, parries and ripostes |
| `control12-<map>` ×4 | Control | 12 (6v6) | 1800 | captures, contests and the clock result on every arena |
| `payload12-<map>` ×4 | Payload | 12 (6v6) | 1800 | escorts, contests and the defenders' clock win on every arena |
| `control4-overtime-estate` | Control | 4 | 11,712 | overtime, then a secured win before the clock |
| `payload6-escort-estate` | Payload | 6 | 5400 | all three checkpoints, then the route-end win |
| `staked-ffa8-lantern` | free-for-all, bond 1000 | 8 | 2400 | 2B and NFT-entitled specials, credited and unassisted hazard deaths |
| `staked-control12-citadel` | Control, bond 1000 | 12 | 1800 | team death transfers; replays `control12-citadel.controls` |
| `staked-melee2-foundry` | Melee, bond 1000 | 2 | 7231 | ten paid deaths, exhaustion and the early slot win |

Map names are `estate`, `lantern`, `foundry` and `citadel` (arenas 0–3). Across all cases the fixture replays every one of the 19 exported event kinds (`ARENA_EVENT_*` in `crates/arena-ffi/include/arena.h`): 14,669 shots, 2260 damage, 400 deaths, 254 respawns, 94 terminals, 16 guards and parries, 235 heals, 638 abilities, 52 marks, 13 ripostes, 444 entity spawns, 51 entity damages, 8 barricade repairs, 295 entity removals, 25 hazard hits, 6 captures, 1 overtime, 3 checkpoints and 94 winners. The controls hold 334 loadout requests and use all seven button bits.

## Run on macOS

From the repository root, with native Rust and Python 3 available:

```sh
cargo build --release -p arena-ffi
python3 scripts/unreal/stage_kernel.py --platform Mac
python3 scripts/unreal/verify_parity.py
python3 scripts/unreal/test_parity_guards.py
```

## Run on Windows

From the same source revision on 64-bit Windows, with a native Rust MSVC toolchain and Python 3 available:

```powershell
cargo build --release -p arena-ffi
py -3 scripts/unreal/stage_kernel.py --platform Win64
py -3 scripts/unreal/verify_parity.py
py -3 scripts/unreal/test_parity_guards.py
```

The runner itself uses only Python's standard library and the real target-platform shared library. It does not require Unreal, a network service or a Python package installation. `--library PATH` selects another explicit native library. Verification must use the repository fixture unchanged; do not regenerate expectations on Windows to make a mismatch disappear.

Reports go to `Saved/Diagnostics/parity-<system>-<machine>.json`. Collect a successful Windows report and a successful macOS report against the **same manifest SHA-256** before making a cross-platform parity claim. Each report identifies its native library hash; different platform binaries are expected to have different binary hashes.

## Scripted players

`scripts/unreal/practice_fixture_bots.py` authors the 21 scripted cases. Only `--record-reference` runs it. Each tick its players read the real kernel through the C ABI (players, presentation, objective and entities), choose ordinary canonical inputs, and step the kernel; the bytes they chose are the case's control file. They walk a 500 mm grid around the arena's static walls, aim at the nearest visible enemy, fire, strike, guard, use abilities, repair their barricades, heal allies with the lance, and send a `LOADOUT` request after each death that rotates their class. Scenario plans give some players fixed roles: overtime contestants, passive defenders, a player who stands in a hazard, and a passive duellist.

Verification replays the stored bytes open-loop and never runs the scripted players, so their floating-point aim and navigation cannot affect parity. They are fixture authors, not the shipped practice bots, and make no balance claim. A case whose bytes equal an earlier file's reuses that file; the staked Control case does, because bonds do not change the players' choices.

## Identity and comparison rules

`manifest.json` (schema 2) records:

- Exact canonical control file lengths and SHA-256 hashes, and each case's configuration, roster (including bonds and NFT entitlement) and declared tick count.
- The eight-byte input encoding from `arena_core::simulation::Input::encode`: little-endian `<HbbHh>` (buttons `u16`, forward/right `i8`, yaw `u16`, pitch `i16`). Frames are tick-major; permanent slots ascend within each frame. Slot and tick are implicit. `scripts/unreal/fixtures/.gitattributes` prevents text conversion of these binary files. A `LOADOUT` frame carries the class and loadout index in the forward and right bytes.
- Every C ABI structure's expected size, alignment, scalar field type and byte offset.
- SHA-256 identities for the simulation, math, combat catalog, economy, maps, C ABI/header and dependency manifests, plus the exact Python binding, runner and scripted-player sources. Source text normalizes CRLF to LF, allowing ordinary Windows checkouts. Unrelated transport/proof implementation files are outside this fixture's explicit semantic-source scope.
- Actual native map data (bounds, walls, the Control circle, payload route points and checkpoints, and hazards; domain `geometry-v2`), weapon data (`weapons-v1`) and per-case initial/final state hashes.
- Per case: the event count of every kind, the winner (kind and value), and the final deposited, remaining and earned totals.
- Cumulative state, event and presentation digests at every 60-tick checkpoint and at the terminal tick. State streams (`states-v1`) include every completed tick and its native hash. Event streams (`events-v2`) include every tick, its count and every field of every event. Presentation streams (`presentation-v2`) include snapshot fields, every player and presentation field, every stable-ID projectile, every live entity and the objective snapshot. Each scalar is encoded little-endian by name and order, with C padding excluded.

Before any case runs, the runner checks every case's declaration: ABI 4, zero-stake practice or exact staked bonds, and a control length that matches the declared ticks and slots. While a case runs it checks conservation on every tick (deposits never change and always equal remaining plus earnings), each player's admitted bond, rejected-input atomicity (an out-of-range move, an unknown button bit and an out-of-range loadout class), that the match becomes terminal exactly on the declared tick, and terminal immutability.

Any mismatch exits nonzero without writing a success report or changing the fixture. Starting verification invalidates the previous report; failure writes `status: fail`, so an obsolete pass cannot be mistaken for the current run. `test_parity_guards.py` has seventeen tests. They check rejection of altered controls, noncanonical input, ABI layout, source/runner identities, state and event digests, the per-case summary, declared ticks, funded practice, inexact staked bonds and a missing case. They also check ABI 3 library rejection, invalidation of an old success report, optimized Python, and that the fixture's source identity covers every simulation source.

## Deliberate baseline changes

When the first-release rules or relevant code intentionally change, review the reason and then explicitly run:

```sh
python3 scripts/unreal/verify_parity.py --record-reference
```

This replaces the reference controls/expectations by executing the loaded native kernel, including a fresh scripted recording of the 21 scripted cases. It is a maintenance operation, never the solution to an unexplained platform mismatch. Recording also requires that the cases still replay every exported event kind, the overtime case ends in a secured team 0 win, the escort passes all three checkpoints and wins, the staked duel ends by exhaustion with 1000 earned, and both other staked cases pay at least one death. Review the resulting source identities, control hashes, geometry/weapon identities and expected digest changes together. Recording a new macOS reference does not establish Windows parity.

## Change log

### 2026-09-26 merge with the pipelined P2P evidence lane (re-recorded identities only)

Merging the practice lane with the P2P lane changed two pinned files that carry no simulation rule: `Cargo.lock`, where `arena-cli` gained its `ed25519-dalek` and `sha2` dependency edges for the N-peer mesh, and `crates/arena-core/src/lib.rs`, which declares the new `mesh_transport` module. The library was rebuilt from the merged tree (`cargo build --release -p arena-ffi`) and staged with `stage_kernel.py`; before recording, `verify_parity.py` refused it only for the changed source identity.

The new manifest was compared field by field with the previous one. Only `recorded_utc`, the reference library hash (`8f44cde8…` to `1bd6e8fa…`, since the library links the merged `arena-core`) and the two source identities changed. The ABI layout, the map and weapon data identities, all 22 control files and every expected value of all 94 cases are identical. Windows parity remains unverified.

### 2026-09-26 four practice bot tiers (re-recorded identities only)

The practice bots gained a fourth, strongest tier so that each of the practice lobby's four choices maps to a real tier. The ABI constants were renamed to the lobby's names, with no aliases: `ARENA_BOT_NOVICE` (0), `ARENA_BOT_STANDARD` (1), `ARENA_BOT_VETERAN` (2) and the new `ARENA_BOT_MASTER` (3). Codes 0-2 keep the parameters of the former Easy, Normal and Hard tiers, so every existing bot match replays unchanged; `arena_bot_input` now refuses code 4 and above. The re-record was required because three pinned files changed: `crates/arena-ffi/include/arena.h`, `crates/arena-ffi/src/lib.rs` and the runner binding `scripts/unreal/kernel_abi.py`.

The new manifest was compared field by field with the previous one. Only `recorded_utc`, the reference library hash (`993d0ba6…` to `8f44cde8…`) and those three source and runner identities changed. The ABI layout, the map and weapon data identities, all 22 control files and every expected value of all 94 cases are identical. The library passed all 94 cases / 99,043 ticks and the seventeen negative guards on macOS arm64. Windows parity remains unverified.

### 2026-09-26 practice bots export (re-recorded identities only)

ABI 4 gained one export, `arena_bot_input`, with the `ARENA_BOT_EASY`, `ARENA_BOT_NORMAL` and `ARENA_BOT_HARD` constants. It serves the zero-stake practice bots of the new `crates/arena-bots` crate, which `arena-ffi` now depends on; each handle keeps the bots' memories outside the state hash. No structure layout, kernel source or simulation outcome changed. The re-record was required because pinned files changed: `Cargo.toml` and `Cargo.lock` (the new workspace member and its dependency edges), `crates/arena-ffi/Cargo.toml`, `crates/arena-ffi/src/lib.rs`, `crates/arena-ffi/include/arena.h`, and the runner file `scripts/unreal/kernel_abi.py` (the new binding). The bot crate is deliberately not pinned: the fixture replays stored control bytes, and bots never author them.

The new manifest was compared field by field with the previous one. The ABI layout, the native map and weapon data identity, all 22 control files, and all 94 cases (configurations, rosters, declared ticks, and every expected value: initial and final state hashes, state, event and presentation streams, event counts, winners, economy summaries and all 1652 checkpoints) are identical. Only `recorded_utc`, the reference library hash (`87f5a5fb…` to `993d0ba6…`) and the source and runner identities changed. The library passed all 94 cases / 99,043 ticks and the seventeen negative guards on macOS arm64. Windows parity remains unverified.

### 2026-09-26 native ABI 4

The C ABI moved from 3 to 4 (`crates/arena-ffi/include/arena.h`). Every kernel event is now exported, one for one: kinds 1–5 keep their meaning and kinds 6–19 number guard/parry, heal, ability, mark, riposte, entity spawn/damage/repair/removal, hazard damage, capture, overtime, checkpoint and winner. `ArenaEvent` grows to 48 bytes with an entity id, entity kind and detail. `arena_step` accepts the `LOADOUT` bit. New queries return entities (`arena_entity_count`, `arena_entity`), the objective snapshot (`arena_objective`), payload route points (`arena_map_route_point`) and hazards (`arena_map_hazard`). `ArenaMapInfo` adds the Control circle, route and checkpoints, and `ArenaPlayerPresentation` adds guard ticks, the class cooldown, stance and mark timers, the pending loadout and the admitted special. The kernel gained `World::removed_entities`, `EntityKind::max_health` and a public `World::count_near`, all presentation-only and outside the state hash, and `ABI_VERSION` became 4. The rules identity and every simulation outcome are unchanged.

The fixture directory and identity moved from `practice-abi3` to `practice-abi4`. The runner adds the 21 scripted cases, staked-case checks, the declared tick count and early terminals, the per-case summary, and entity and objective presentation. Before `practice-abi3` was removed, its manifest was compared with this one. For the 73 cases the two share:

- the control bytes and hashes, session configurations (apart from the ABI number), rosters, weapon-spec identity (`cb0ad920…`) and kind 1–5 event counts are identical;
- all 73 initial and final state hashes, state streams, and the state hashes and state streams at all 735 checkpoints are identical, so the kernel's behaviour in these scenarios did not change;
- every event stream changed, because events that ABI 3 skipped are now exported (402 abilities, 306 entity spawns, 180 entity removals and 73 winners in these cases), and every presentation stream changed with the wider structures and the entity and objective queries. The map identity changed with the ABI 4 map data.

The kill-history V2 projection changed only in `abi_version` (3 to 4) and `kernel_revision`. The new library (`87f5a5fb…`) passed all 94 cases / 99,043 ticks and all seventeen negative guards on macOS arm64. Windows parity remains unverified.
