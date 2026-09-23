# Eight-peer loopback wire research fixture

`crates/arena-core/tests/eight_peer_two_minute_udp_research.rs` exercises eight
separate local sockets, signed wire receivers, and rollback sessions. It uses
the same 7,200 fixed-input Control-mode ticks as the
[eight-player kernel fixture](eight-player-local-kernel-research.md): four
players per team, standard Samurai Arc carbines, zero bonds, and offline
simulation. The 3,600 two-tick batches reach the full two-minute terminal
clock without reducing players or tick count.

For every batch, all eight fixture keys sign one complete commitment set. A
signed certificate reaches seven other loopback sockets before any reveal.
Reveals arrive in rotating and reversed slot orders; each peer's `WireReceiver`
checks the signed envelope and the opening against its locally certified
frontier. The fixture restores permanent-slot order before each peer applies
the complete batch. One speculative tick exercises `RollbackSession`'s
prediction reconciliation. Every peer's confirmed state and history root are
compared with a separately stepped kernel reference after every batch.

At 120-tick intervals, all eight fixture keys sign a checkpoint, and each peer
retains the same checkpoint against its local confirmed state. There are 60
checkpoint rounds and 227,220 delivered UDP packets. At the terminal tick,
all eight peers agree with the pinned kernel replay vectors:

| Digest | SHA-256 hex |
| --- | --- |
| Final kernel state | `ae4f7add6174106217c1ba20f1dc18da4b1c28456a7630931739f5ba78ea60be` |
| Input-plus-state timeline | `effafb52709a3fc946c82eeb3ad80b3b2616193c0505c22289273e16f754fe56` |

The research test is opt-in because it verifies hundreds of thousands of
signed packets. Run it with:

```sh
cargo test --locked --release -p arena-core --test eight_peer_two_minute_udp_research -- --ignored --nocapture
```

On 2026-09-23, that command passed in 90.92 seconds of test execution on the
Apple M1 Ultra (128 GB), macOS 27.0, arm64, Rust 1.97.1. An external watchdog
sampled the test's resident memory every two seconds and would terminate above
512 MiB or at roughly 180 seconds total. It did not trigger. Exact peak RSS
was not captured, so this only establishes that sampled RSS stayed below the
threshold. These are local research measurements, not network or proving
performance guarantees.

The existing `LocalhostPeer` module has one remote slot and one durable
pairwise channel; it does not implement an eight-peer mesh. This test uses
raw signed `WireFrame` packets over lossless, fixture-orchestrated loopback
UDP. It bypasses the pairwise encrypted transport, durable journals and
receipt files, process separation, packet loss/retry, matchmaking, NAT/relay,
and independent key custody. Checkpoint signatures are made from fixture-held
keys, not a production consensus or native chain authority. There is no XOR
deposit, NFT admission, cryptographic execution proof, verifier, or settlement.
Consequently the planned 4v4 two-minute networked proof-to-settlement research
gate remains open.
