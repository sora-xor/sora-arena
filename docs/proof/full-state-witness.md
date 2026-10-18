# Complete local execution witness

`arena-core::execution_trace` supplies full tick-boundary data for the staged
Arena relation. It replays the actual kernel from original admission and checks
every retained commitment certificate and opening. It does not use a reported
kill, an imported checkpoint, or a manually selected projection of player state.
This is host replay and witness preparation, **not a STARK, ledger-selected
history, an independent execution implementation, or settlement authorization**.

`World::state_bytes()` and `state_hash()` share one streaming encoder in
`simulation/state.rs`. Exhaustive struct patterns require review when a field
is added. It includes every outcome-affecting World, Player, Account, Projectile,
Entity and DamageRecord field, in original order, plus Config, map digest, tick
and terminal/objective state. The last step's presentation events and removed
entities are excluded because the next step does not consume them. Mismatched
player/account counts assert rather than silently omitting accounts.

The single reference-state format is documented in `combat-rules.md` §12.
No decoder or state-restoration API was added. The 27 stored research state
hashes are unchanged; only the fixture's source fingerprint changes to include
the extracted encoder. This does not update or qualify a native proof.

## Replay and authority

`write_trace(config, original_participants, session, writer)` starts with
`World::new`, reconstructs the commitment chain, verifies every original-slot
Ed25519 signature and salted opening, and executes closed batches with
`World::step`. Each actual tick emits its complete outgoing state. Original
admission is separate from mutable respawn loadouts. Final state bytes, epoch,
closed/certified ticks, transcript root, commitment head and phase must match
retained local evidence.

Pending certificates and partial openings remain explicitly unexecuted. If
combat ends after the first tick of a batch, both signed controls and the whole
batch transcript remain present. Further closed batches after terminal combat
are rejected. Memory does not grow with emitted boundaries: at most two encoded
states are held in addition to the World and signed history.

The caller must independently authenticate network/session/manifest, roster,
config and original participant admission. An opaque manifest hash cannot prove
NFT ownership. Even admission fields that do not affect a particular World,
such as entitlement for standard equipment, are included in the header and
compared. This module cannot determine which admission the ledger selected.

All closed or pending deadline attestations are rejected until a native adapter
authenticates them. A nonzero local hash is insufficient to forfeit an opening.
Original evidence remains intact. Interrupted-match proving therefore remains
an explicit open gate.

`verify_trace` regenerates the stream from separately supplied admission and
signed evidence and compares every byte through EOF. Replacing a state and
recomputing the file seal still fails. Claimed states are never deserialized
into an authoritative World. A failed write may leave a prefix; only a
successful return and final seal represent a complete witness.

## Single local file format

Integers are little-endian, Booleans are 0/1, counts and byte lengths are u32.
Vector order is retained. This format is not native Norito.

1. `SORA-ARENA-EXECUTION-TRACE` plus byte 1; length-framed rules string;
   32-byte source digest; length-framed context domain (network, session,
   manifest and ordered input keys).
2. Participant count; each original participant's team, class, weapon and
   entitlement as four bytes, then u64 bond. Length-framed genesis state,
   including every Config field and map digest.
3. Closed-batch count. Each batch contains its certificate/openings, previous
   and resulting transcript roots, executed-tick count, then each tick's u32
   input tick, eight-byte input per slot, and length-framed outgoing state.
4. Pending-frontier count and each unexecuted certificate/opening set.
5. `TRACE-END\0`; phase byte (live 0, resolving 1, terminal 2); completed
   Boolean; u32 combat/evidence/certified ticks; state hash, transcript root and
   commitment head; SHA-256 of all preceding file bytes.

A certificate/opening set contains u64 epoch, u32 start tick, parent digest,
counted 32-byte commitments, counted `(u32 slot, 64-byte signature)` entries,
and counted optional openings. Each opening has a presence byte, then when
present u32 slot/start tick, counted eight-byte inputs and 32-byte salt.

The source digest frames filenames and normalized UTF-8 source contents of
workspace manifest/lock/compiler pin, core manifest, combat, state encoder,
protocol, rollback and trace code. It is a source-change tripwire, not proof
that native AIR executes that code. Release compiler/dependency artifacts
still need qualification.

## Research journal command

The CLI reads the existing scripted `peer` journal, requiring an explicit
retained receipt and exact public research admission. It does not infer
production identities.

```sh
cargo run --release -p arena-cli -- trace \
  --journal /absolute/path/peer-0.journal \
  --receipt-records RECORD_COUNT --receipt-hash LOWERCASE_SHA256 \
  --players 8 --ticks 7200 --session SESSION_NUMBER \
  --output /absolute/path/match.trace
```

Use `--verify /absolute/path/match.trace` instead of `--output` to compare with
replay. Corrupt/truncated journals or execution faults produce no export.
Existing output files and symlinks are never overwritten. A failed stream
removes only its newly created incomplete output. Success reports ticks, byte
count and exact digests, with no proof, ledger selection or transactions.

Focused checks:

```sh
cargo test --locked -p arena-core --test state_encoding --test execution_trace
cargo test --locked -p arena-cli --test execution_trace
```

Native staged AIR, proof-authenticated complete-state chaining, consensus
deadlines, Arena admission, final composition, four-validator settlement,
Windows parity and the full 6v6 proving resource gate remain required.

## Full-size local capacity measurement, 2026-10-18

The release-mode `trace_capacity` example completed on this M1 Ultra with
Rust/Cargo 1.97.1: 12 participants in 6v6, all six classes and twelve standard
weapons, 36,000 ticks and 18,000 signed batches. It generated and independently
replayed the stream through EOF, using fresh certificate verification on each
pass. The artifact contains all executed boundaries; no idle retry or reduction
in duration/player count was needed.

| Measurement | Observed result |
| --- | ---: |
| Signed-history preparation | 73.378 s |
| Trace writing and replay | 58.250 s |
| Trace comparison and replay | 42.091 s |
| Program total | 174.010 s |
| Encoded artifact | 93,337,494 bytes |
| Entire Cargo build/run elapsed time | 200.66 s |
| Entire Cargo build/run peak resident memory | 106,659,840 bytes |

The timed command includes 26.00 seconds of compilation; its memory measurement
is not a separately isolated replay-process peak. Other development work was
active on the machine. This scene uses zero bonds and outward fire, jump,
reload and abilities at team spawns, with no movement axes. It recorded zero
deaths and maximum batch-boundary counts of one projectile and eight entities.
These are serialization, signature and replay capacity observations, not a
representative combat stress test, 60 Hz networking result, STARK benchmark or
settlement qualification. The 30-minute/96-GiB proving gate remains unmeasured.

Reproduce with a fresh output path (existing files are rejected):

```sh
/usr/bin/time -l cargo run --release --locked -p arena-core \
  --example trace_capacity -- /absolute/path/full-size.trace
```

Local evidence is in `Saved/Qualification/2026-10-18/trace-capacity.log` and
`Saved/Qualification/2026-10-18/full-size.trace`, excluded from Git. Artifact
SHA-256:
`d17211dc6f671be67a81c6d87618b818ec96d6ee743d07f0683ae35ffb0aad77`.
Final state hash:
`9e25eb7a41a87d4b8e0b6b04cf9bd8ff0ebcda7eef0c9056ebf0c7387a3a5d0f`.
Accepted-history root:
`d5f025c7850674915f7097402045c0a0120f851ad1986d15f9223ab2de9a54f8`.
The stored source digest matches the measured source:
`f1ad111f74a3153b87da2f3c9b78eea2a804976015d1b777b8ba1a06b81c22c2`.
