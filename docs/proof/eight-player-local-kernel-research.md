# Eight-player local kernel research fixture

The game repository now has a bounded, **offline** 4-per-team reference-kernel
fixture in `crates/arena-core/tests/eight_player_two_minute_research.rs`. It runs
7,200 fixed 60 Hz ticks (two minutes of simulated time) in Control mode on
Nyaagyu Estate. All eight participants use the standard Samurai Arc carbine.
The control script routes around the map walls, holds fire, and repeats on a
900-tick cycle. It produced actual attack, damage, death, and respawn events.
This fixture uses `World::new`, `World::step`, and the kernel's state hash.

The first pass records every eight-byte input and every tick's state hash. A
second pass regenerates controls, and a third decodes the recorded input bytes.
The test compares all 7,200 per-tick hashes, the final state hash, the complete
input-plus-state timeline digest, and event counts across all three passes. The
two digests are pinned as regression vectors under `sora-arena-first-release-7`:

| Digest | SHA-256 hex |
| --- | --- |
| Final kernel state | `5d000cfd7b28526bfa55fe0050c0d47872fa6c9831b189f6ea5c602d0af019ea` |
| Input-plus-state timeline | `409dd59b3d6016dd35c026d0d6608e9f55f56512866f22d1cfae1c5d9b1b9c9e` |

Run with `cargo test --locked -p arena-core --test eight_player_two_minute_research -- --nocapture`.
On 2026-09-26, the focused test passed on Apple M1 Ultra (128 GB), macOS 27.0,
arm64, Rust 1.97.1, in an unoptimized debug build, with a load average of about
18 from other work. The first run took 1,353 ms, the regenerated repeat
1,369 ms, and encoded-input replay 1,363 ms. The direct test process took
4.69 s wall time for all three runs. `/usr/bin/time -l` on that process
reported a maximum resident set size of 5,390,336 bytes (about 5.14 MiB),
including the test harness and recorded inputs/hashes. The fixture timings
include input generation or decoding, state hashing, and test checks; they do
not isolate combat-step cost. The fixture recorded 1,838 shot events, 384
damage events, 64 deaths, and 64 respawns. The recorded input tape is 460,800
bytes. These numbers are local observations,
not performance guarantees for other machines or builds.

This is **not** the planned 4v4 two-minute networked research match. There are
no peers, commitment/reveal exchange, rollback, signatures, execution proof,
prover, verifier, chain transactions, NFT admission, or settlement. The fixture
uses `offline=true` and zero bonds; its conservation assertion cannot qualify
value-bearing play. Full proof coverage and measured proof resources remain
separate release gates.
