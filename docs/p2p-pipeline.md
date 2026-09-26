# Pipelined P2P evidence and peer dropout

`arena_core::protocol`, `rollback` and `recovery` let several input batches
be in flight at once, so 60 Hz combat does not wait a round trip per batch.
They also implement the plan's peer-dropout policy at protocol level. This is
local evidence: it is not Iroha's consensus-selected history, an execution
proof or a settlement. The formats are first-release p2p-evidence v2, wire v2
and journal v3. There are no older decoders.

## Two chains

**Input commitment.** SHA-256 over the v2 evidence domain with tag `inputs`,
then the epoch, the batch's first tick (a multiple of `BATCH_TICKS = 2` below
36,000), the slot, the input count 2, the two canonical eight-byte controls
and a 32-byte salt ([combat rules §2.2](combat-rules.md)). It binds no other
peer's commitment or reveal and no transcript root. A peer can therefore commit
a batch as soon as it has sampled its own controls.

**Commitment chain.** A `CommitmentSet` holds every slot's commitment for one
batch, and its `parent` is the digest of the set certified before it. The
first set's parent is the SHA-256 of the evidence context under the tag
`commitment-genesis`, which binds the network, session, manifest and roster. A
certificate is every original roster key's Ed25519 signature over the set
digest. `EvidenceLog::certify` accepts sets strictly in chain order: the start
tick must equal `certified_tick` and the parent must equal `commitment_head`.
At most `MAX_OUTSTANDING_FRONTIERS = 16` certified frontiers (32 ticks, 533 ms)
may await their openings.

**Reveal transcript.** Frontiers close strictly in tick order. Each closure
hashes the previous root, the set digest, a closure byte and each slot's
executed controls. The closure byte is 0 when every slot opened and 1 when a
consensus deadline closed the frontier; in that case the 32-byte attestation
follows. Each slot contributes an opened flag and its two controls; a
forfeited slot contributes the canonical idle control. Checkpoints sign this
root. The root does not depend on how many frontiers were in flight: tests
certify six and eight frontiers ahead, open them out of order, and get the
same root and state hash as one frontier at a time.

## Input delay and schedule

`INPUT_DELAY_TICKS = 4` (67 ms). A control sampled on presentation tick `p`
executes on tick `scheduled_tick(p) = p + 4`. The batch holding ticks `s` and
`s + 1` is complete, and its commitment due, on presentation tick
`commitment_due(s) = s − 3`, three ticks before its first tick executes. No
sampled control reaches the two lead-in batches (ticks 0–3). Peers commit the
canonical idle control for them at admission.

With a one-way delay of `d` ticks, a batch needs about three delays from its
commitment to confirmation: commitments go out, then endorsements, then
openings. Rollback prediction covers that gap. Prediction is bounded by
`MAX_PREDICTION_TICKS = 120`, which covers a full assembly window, a full
certified pipeline and the input delay (a compile-time assertion).

## Assembling certificates

Every peer assembles each certificate itself with
`protocol::FrontierAssembler`:

1. Each peer sends its own `WireMessage::Commitment` (wire kind 3). The signed
   envelope authenticates the sender.
2. Once a window and every earlier window hold all commitments, the set is
   determined. Each peer signs it and sends `WireMessage::SetSignature` (kind
   4), which carries the complete set so the receiver can verify the signature
   before assembling the set itself.
3. When every slot has endorsed exactly the assembled set, `take_certified`
   yields the certificate for `EvidenceLog::certify`.

The assembler accepts commitments up to `MAX_ASSEMBLY_FRONTIERS = 32` batches
(64 ticks) beyond the last certified frontier. Each slot may hold one
commitment and one endorsed set per tick. A conflicting commitment or
endorsement is rejected. A slot that endorsed a different set can never
complete the frontier; that stall is a dropout for the rules below. A relayed
complete `CommitmentCertificate` (kind 0) is still accepted, and
`FrontierAssembler::sync` realigns the assembler after one.

A durable peer journals its own opening with `DurableSession::seal` before its
commitment leaves the process. It journals the endorsed set digest with
`DurableSession::endorse` before its signature leaves. After a restart the
peer can therefore open every certified frontier it committed to. It resends
the same commitments and re-derives the same Ed25519 signature, and the
journal refuses a second opening or a second endorsed set for any tick.
`LocalhostPeer::prepare` refuses a commitment that was not sealed or a set
signature that was not endorsed. Commitments and set signatures are
authenticated and acknowledged but not journaled on receipt: they become
evidence only inside a certificate.

Checkpoints are gathered the same way. `WireMessage::CheckpointSignature`
(kind 5) carries one slot's Ed25519 signature over the checkpoint of a
boundary it confirmed; the receiver checks it against that slot's roster key.
A peer retains the checkpoint only when every roster key has signed exactly
the checkpoint of its own boundary at that tick. A signature over any other
root or state at that tick is a divergence, not a vote. Signing a checkpoint
is deterministic and commits to nothing a restarted peer could contradict, so
it is not journaled before it is sent. `RollbackSession::boundary` exposes the
recent boundaries (the checkpoint window) so a peer that closed several
frontiers at once still signs each checkpoint tick it passed. The
[mesh transport](p2p-localhost.md#n-peer-mesh-transport) gathers one every
120 ticks and one at the end of combat.

## Measured pipeline

`crates/arena-core/tests/pipelined_protocol.rs` simulates three peers in
process with a fixed one-way delay, counted in 60 Hz ticks. Each peer
presents one tick per wall tick, commits each batch as its last control is
sampled, opens its own commitment as soon as the frontier is certified, and
predicts remote controls by repeating each slot's last confirmed control.
After 240 presentation ticks the in-flight batches drain. Every peer's
transcript root and state then match an independently stepped kernel. They
also match a session that certified and opened one frontier at a time over
the same openings.

| One-way delay | Round trip | Presented / stalls | Deepest prediction | Deepest certified pipeline |
| --- | --- | --- | --- | --- |
| 3 ticks (50 ms) | 100 ms | 240 / 0 | 9 ticks | 3 frontiers |
| 9 ticks (150 ms) | 300 ms | 240 / 0 | 27 ticks | 6 frontiers |
| 24 ticks (400 ms) | 800 ms | 240 / 0 | 72 ticks | 14 frontiers |
| 32 ticks (533 ms) | 1,067 ms | 234 / 6 | not asserted | 16 frontiers (full) |

At 32 ticks the full certified pipeline applies backpressure: presentation
stalls, and every peer still agrees with the reference. An exploratory run
during development, with 300 presentation ticks, also presented every tick at
15 and 30 ticks one way (deepest prediction 45 and 90 ticks; pipeline 9 and
16 frontiers).

For comparison, the same simulation emulates one frontier in flight by
committing a batch only after every earlier frontier has closed. At a 9-tick
one-way delay it presented 17 of 240 ticks and stalled on 223.

This is a deterministic in-process model. It has no packet loss, jitter,
bandwidth limit, CPU or fsync cost, real sockets or NAT, and it does not
measure signature or kernel time. The eight-peer loopback fixture
([research note](proof/eight-peer-loopback-research.md)) runs the same
assembly over real signed UDP packets without latency.

## Peer dropout

**Stop combat.** `interrupt` moves the evidence to `Resolving`; a local
timeout may call it. The N-peer mesh does so after its stall limit, then
shares its pending certificates and last certified checkpoint with the other
survivors ([mesh dropout](p2p-localhost.md#dropout)). A resolving session runs
no prediction, and its journal refuses to seal or endorse anything new. It
still accepts:

- certificates, because each needed every original key and so was complete
  before the dropout;
- openings, which frontiers still close in tick order.

**Preserve.** The last certified checkpoint, every pending frontier and every
opening received stay in the session and the journal. Nothing local discards
them.

**Resolve.** A frontier closes in one of two ways:

- **Complete openings.** An opening authenticates itself against its
  certified commitment, so any peer may relay one it received; a forged relay
  is rejected.
- **A consensus deadline.** A `DeadlineResolution` is native consensus's
  retained view of one frontier's openings in slot order. `None` marks a slot
  that published nothing before the deadline; that slot is forfeited and
  executes the canonical idle control for the batch. A non-zero `attestation`
  identifies the consensus decision, and the transcript binds it.

A resolution must forfeit at least one slot. Complete openings close as
ordinary reveals, so every peer that holds them derives the same transcript.
Once consensus closes a frontier, a late opening is refused. A resolution
stops combat if it had not stopped already. arena-core cannot verify the
attestation: the chain adapter must. A peer clock never produces one, and a
local timeout can only interrupt.

**Terminal.** `finish` requires that no certified frontier is still pending.
The only exception is a match the kernel's clock or objective already ended:
certified frontiers after that point are void, and they stay retained without
executing. `RollbackSession::terminal_outcome` then reports the epoch, the
last executed tick, the evidence tick, the transcript root, the state hash,
whether the kernel completed the match, and how many frontiers a deadline
closed. It is derived from retained evidence alone and needs no final
signature. A peer that refuses to sign a checkpoint cannot erase a death its
certified inputs produced. A victim that withholds the opening of the batch in
which it dies is forfeited to idle, and the death and its award still execute.

**No timeout settles funds.** Nothing in arena-core submits a transaction or
releases a reserve, an award or an NFT. The terminal outcome is dispute
material. Native settlement must verify the proof before it pays accrued
verified awards and returns unused reserves. That verification is not
implemented here.

**Agreement.** Peers reach the same terminal outcome only if they hold the
same certificates, openings and deadlines. Before a peer finishes, the chain
adapter must deliver every certificate and opening published to consensus.
Suppose a peer held an opening but did not publish it before the deadline.
Consensus's forfeit still stands, and that peer's local transcript is not
canonical.

The dropout tests in `pipelined_protocol.rs` use durable journals:

- A peer that drops before committing, or after committing but before
  endorsing, leaves both survivors at the last certified frontier with
  identical outcomes.
- A peer that drops after certification but before opening two pipelined
  frontiers is forfeited by two consensus deadlines. Both survivors reach the
  same outcome and preserve the pre-dropout checkpoint. A restored journal
  reproduces it.
- An opening sent to one peer before the dropout completes the frontier for
  both through a relay, with no deadline.
- A victim that withholds its opening and every later checkpoint signature
  still dies, pays 100 of its 1,000 bond and credits the killer, exactly as
  in the honest replay.
- A restart in the middle of the pipeline, with three pending frontiers,
  partial openings and an uncertified endorsement, reaches the same outcome as
  an uninterrupted run.

## Still open

- The native consensus adapter: publishing openings and certificates,
  deciding deadlines, attestations, and Iroha's terminal-on-disconnect
  instruction.
- Proofs over the v2 transcript.
- NAT traversal, relays and peer discovery. The
  [N-peer mesh](p2p-localhost.md#n-peer-mesh-transport) runs on loopback, or on
  a private research LAN when chosen explicitly, and is measured on one
  machine only.
- Measurements under jitter and bandwidth limits, and qualification of the
  constants on real networks. Loss, duplication and reordering are measured
  only as injected loopback damage.

Real-value admission stays disabled until the proof and validator gates pass.
