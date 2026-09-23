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
two digests are pinned as regression vectors:

| Digest | SHA-256 hex |
| --- | --- |
| Final kernel state | `ae4f7add6174106217c1ba20f1dc18da4b1c28456a7630931739f5ba78ea60be` |
| Input-plus-state timeline | `effafb52709a3fc946c82eeb3ad80b3b2616193c0505c22289273e16f754fe56` |

Run with `cargo test --locked -p arena-core --test eight_player_two_minute_research -- --nocapture`.
On 2026-09-23, the focused test passed on Apple M1 Ultra (128 GB), macOS 27.0,
arm64, Rust 1.97.1, in an unoptimized debug build. The first run took 549 ms,
the regenerated repeat 546 ms, and encoded-input replay 550 ms. The direct
test process took 1.65 s wall time for all three runs. `/usr/bin/time -l` on
that process reported a maximum resident set size of 5,193,728 bytes (about
4.95 MiB), including the test harness and recorded inputs/hashes. The fixture
timings include input generation or decoding, state hashing, and test checks;
they do not isolate combat-step cost. The fixture
recorded 1,856 shot events, 384 damage events, 64 deaths, and 64 respawns. The
recorded input tape is 460,800 bytes. These numbers are local observations,
not performance guarantees for other machines or builds.

This is **not** the planned 4v4 two-minute networked research match. There are
no peers, commitment/reveal exchange, rollback, signatures, execution proof,
prover, verifier, chain transactions, NFT admission, or settlement. The fixture
uses `offline=true` and zero bonds; its conservation assertion cannot qualify
value-bearing play. Full proof coverage and measured proof resources remain
separate release gates.
