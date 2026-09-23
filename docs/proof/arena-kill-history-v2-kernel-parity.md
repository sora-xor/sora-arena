# Arena kill-history V2 kernel parity fixture

[`arena_kill_history_v2_parity.rs`](../../crates/arena-core/tests/arena_kill_history_v2_parity.rs) independently replays the exact unregistered Iroha research scene in `arena-core`: three FFA samurai on map 0, two Arc carbines, 1,000 atomic-unit bonds, 26 ticks, and shots at ticks 0, 12, and 24. The final tick is an admitted idle control, not unexecuted padding.

The committed [JSON projection](../../crates/arena-core/tests/data/arena_kill_history_v2_kernel.json) contains all 27 tick-boundary fields used by Iroha's `KillResearchStateV1`, all 13 two-tick control batches in canonical wire hex, ordered events, final allocations, and full kernel state hashes. `kernel_revision` is the SHA-256 fingerprint of length-framed `lib.rs`, `simulation.rs`, `catalog.rs`, `math.rs`, `economy.rs`, and `protocol.rs`; it is a source-change tripwire, not an executable attestation or production proof identity.

Run the focused regression with `cargo test --locked -p arena-core --test arena_kill_history_v2_parity`. The test compares the live replay to every committed JSON value and explicitly checks the death, 20/80 awards, final idle-tick respawn countdown, and terminal state. A kernel change requires reviewing the resulting diff against Iroha's proof relation before regenerating the fixture with `ARENA_REGENERATE_KILL_V2_FIXTURE=1 cargo test --locked -p arena-core --test arena_kill_history_v2_parity`.

This fixture authenticates no wallet, admission, signed P2P certificate, ledger-selected history, or settlement. It does not qualify value-bearing play.
