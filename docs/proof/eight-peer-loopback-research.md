# Eight-peer loopback wire research fixture

`crates/arena-core/tests/eight_peer_two_minute_udp_research.rs` exercises eight
separate local sockets, signed wire receivers, frontier assemblers and rollback
sessions. It uses the same 7,200 fixed-input Control-mode ticks as the
[eight-player kernel fixture](eight-player-local-kernel-research.md): four
players per team, standard Samurai Arc carbines, zero bonds and offline
simulation. The 3,600 two-tick batches reach the full two-minute terminal
clock without reducing players or tick count.

Every peer assembles every certificate itself through the
[pipelined protocol](../p2p-pipeline.md):

- Each peer sends its own signed input commitment to the seven others, four
  batches ahead of certification.
- Each peer signs the commitment set it assembled and sends that signature
  with the set.
- Once a peer holds all eight endorsements of its own set, it certifies it
  against its commitment chain.

Openings trail certification by eight frontiers, so nine certified frontiers
await openings when each new one is certified. The openings arrive in rotating
and reversed slot orders. Each peer's `WireReceiver` finds the frontier among
its own certified frontiers by start tick and checks the signed envelope and
the opening.

Each peer also presents every committed tick speculatively. Every peer's
confirmed state, transcript root and evidence tick are compared with a
separately stepped kernel reference after every closed frontier.

At 120-tick intervals, all eight fixture keys sign a checkpoint, and each peer
retains the same checkpoint against its local confirmed state. At the terminal
tick, all eight peers' predicted and confirmed states match the pinned kernel
replay vectors, and all eight reach the same terminal outcome and pinned
reveal transcript root:

| Digest | SHA-256 hex |
| --- | --- |
| Final kernel state | `5d000cfd7b28526bfa55fe0050c0d47872fa6c9831b189f6ea5c602d0af019ea` |
| Input-plus-state timeline | `409dd59b3d6016dd35c026d0d6608e9f55f56512866f22d1cfae1c5d9b1b9c9e` |
| p2p-evidence v2 reveal transcript root | `7e381209517af7f0ea3486ba6ecfed25d171df11dcecb8ccf506be5c91d1e743` |

The two kernel digests are the first-release-7 values shared with the
eight-player kernel fixture; pipelining the evidence protocol did not change
them. The transcript root is new with the v2 commitment chain.

The research test is opt-in because it verifies over a million signatures and
signed packets. Run it with:

```sh
cargo test --locked --release -p arena-core --test eight_peer_two_minute_udp_research -- --ignored --nocapture
```

On 2026-09-25 the release test binary built by that command passed in 211.28
seconds of test execution. It ran on the Apple M1 Ultra (128 GB), macOS 27.0,
arm64, with Rust 1.97.1. The run delivered 605,220 signed UDP packets over 60
checkpoint rounds, and the deepest certified pipeline was 9 frontiers.
`/usr/bin/time -l` reported a maximum resident set size of 63,324,160 bytes
(60.4 MiB). An earlier run with a placeholder transcript root passed every
other assertion in 201.11 seconds and reported the root now pinned. These are
local research measurements, not network or proving performance guarantees.

This test does not use `LocalhostPeer`, which has one remote slot and one
durable pairwise channel. It sends raw signed `WireFrame` packets over
lossless loopback UDP, and the fixture orchestrates every send. It bypasses:

- the pairwise encrypted transport;
- durable journals and receipt files;
- process separation;
- packet loss, retry and latency (see the in-process
  [latency simulation](../p2p-pipeline.md#measured-pipeline));
- matchmaking and NAT/relay;
- independent key custody.

The multi-process harness in the
[mesh transport](../p2p-localhost.md#n-peer-mesh-transport) covers the first
three, and injected loss. It plays the same script as eight separate
`arena-cli peer` processes, each with its own socket, encrypted channels,
durable journal and receipt log, and every process reaches the same final
state. The harness runs the match as a clean baseline, with one peer
SIGKILLed mid-match and restarted from its journal, and with 5% drop,
duplication and reordering plus 1% corruption on every datagram. Each process
signs only its own slot's messages; the keys still derive from a public
session number.

Checkpoint signatures are made from fixture-held keys, not a production
consensus or native chain authority. There is no XOR deposit, NFT admission,
cryptographic execution proof, verifier or settlement. The planned 4v4
two-minute networked proof-to-settlement research gate therefore remains open.
