# ArenaV1 staged execution proof: design gate

This is an implementation design for the requested 12-player, 36,000-tick
match. It is **not** a generated hit proof or a qualified settlement path.
Real-value bonding remains disabled. The [feasibility record](arena-feasibility.md)
contains the native source-sealed measurements.

## Limits established by current source

| Current native fact | Consequence for ArenaV1 |
| --- | --- |
| The execution envelope is capped at 4,194,304 bytes (`iroha_data_model/src/execution_proofs.rs`). | The compiled 12-player/four-wall hit layout's mandatory openings alone are 126,125,312 bytes. A larger transaction limit alone cannot repair the relation. |
| The existing segment/box graph has 3,703 AIR columns; the composed hit graph has 57,836 (`arena_geometry_air.rs`, `arena_hit_air.rs`, source-sealed layout run). | Even a standalone current geometry intersection exceeds the envelope's opening budget. It must be expressed as a narrower staged circuit with the same integer semantics. |
| The native proof driver fixes 136 queries, eightfold extension, eight copy columns, 118 auxiliary columns, one trace group/instance, and at most `2^19` native rows (`proof_managed_note_stark.rs`). | For AIR width `w`, mandatory current/next trace openings alone require `2 × 136 × 8 × (w + 8 + 118) = 2,176(w + 126)` bytes. Thus `w <= 1,801` is merely a *necessary* condition under the 4 MiB cap; Merkle, FRI, DEEP, envelope and public data need more room. A practical target such as 400–512 columns is a hypothesis to measure, not an approved profile. |
| Native `OpenGameSessionV1` rejects `max_ticks / batch_ticks > 4096` (`smartcontracts/isi/game.rs`). | The current Arena protocol's 2-tick batches over 36,000 ticks require 18,000 batches, so session opening fails before proof work. The raw 12-player input bytes alone are `36,000 × 12 × 8 = 3,456,000`, within the separate 4,194,304-byte declared-input bound; the batch-count gate still needs a qualified extension. |
| Native `SettleGameSessionV1` accepts one inline `ExecutionProofEnvelopeV1` and verifies it before payouts (`smartcontracts/isi/game.rs`). | It cannot consume a portfolio of stage proofs, even if every stage fits individually. New retained verified-prefix state and terminal composition rules are required. |
| The current generic `input-transcript` commitment hashes the complete `GameTranscriptV1` (`StartGameSessionV1` and RaceV1). | A chunk verifier cannot extend this hash using only the preceding digest. Arena needs a canonical appendable transcript commitment, or each chunk must carry its complete prior transcript, which grows quadratically. |

For the source-sealed 8,192-row, one-group layout probe, the native
`maximum_encoded_proof_with_deep_bytes_v1` results obey
`1,133,632 + 2,240 × AIR_width` bytes. This is the backend's **conservative
maximum wire bound**, not an observed proof size, and is only established for
that fixed layout geometry. It gives 2,029,632 bytes at 400 AIR columns and
2,280,512 at 512. A width of 1,366 leaves only 832 bytes under the 4 MiB
*native* cap, with no room for its surrounding envelope. Larger domains need
their own native layout measurement; the intercept grows with FRI geometry.

An attack-cooldown-only upper bound is `ceil(36,000 / 5) × 12 = 86,400`
initiated attacks: the Phantom SMG has the lowest catalog cooldown of five
ticks. Ammunition/reload, stamina, death and mode rules reduce realizable
activity, so this is **not** a measured or proven attainable workload. A
wall-then-roster scan at four walls plus 12 original slots would require up to
1,382,400 intersection visits at that loose bound, before movement,
projectiles, blast damage, assists, objectives or economy. In particular,
simply moving the existing wide hit graph to one row per box does not establish
the `2^19`-row, 30-minute or 96-GiB gates.

The current local P2P evidence form uses all 12 signatures, commitments and
revealed salts for each 2-tick batch. At the full 18,000 batches, those fields
plus the 3,456,000 control bytes have a 31,104,000-byte raw subtotal, before
headers or storage framing (`18,000 × (12 × (64 + 32 + 32 + 16))`). That is
available off-chain evidence, not an allowable inline proof payload or proof
of ledger data availability. Retention and dispute retrieval need their own
measured design.

## Proposed proof composition

ArenaV1 needs a *closed, compiled* native relation. Its source-bound profile
identity includes the fixed-point kernel, input decoder, catalog, map collision,
rules, payout policy, all staged AIR, state codec, proof driver and verifier.
The proof statement fixes network, session, original 12-slot roster, rule and
map identities, equipment/NFT entitlements, initial deposits, accepted input
history, dispute selection and terminal awards. A publisher catalog is an
admission authority, not a witness-selectable weapon-stat table.

1. **Canonical input prefix.** Commit/reveal evidence must select exactly one
   slot-ordered input at each tick. A chain-owned appendable commitment binds
   every certified 2-tick batch and consensus-selected forced/DNF event. It
   carries its precise start/end ticks, epoch and prior root. The verifier
   compares each stage's public input slice with this retained prefix; a local
   peer log or signature without consensus selection cannot authorize a slash.
2. **Narrow microcycles.** A verifier-fixed schedule executes tick prelude;
   all original-slot movement/collision; abilities and attack initiation in
   slot order; wall-then-original-roster hit selection for each legal melee or
   hitscan; projectile motion, ordered collision and blast effects; gathered
   damage, guarding/parry, death and assist attribution; payouts; objectives;
   and terminal conditions. Inactive branches, vector lengths, sparse event
   counts, padding and transitions to the next stage must be constrained.
   The relation must also bind charge progress to its specific weapon so a
   Kanabo windup cannot precharge another weapon, resolve team-mode Healing
   lance recovery before same-tick damage without reviving the dead, and apply
   Plasma matchlock guard penetration only to its charged direct hit. These
   transitions affect deaths and therefore XOR transfers; they cannot remain
   presentation-only rules.
   The current `arena_hit_air.rs` can supply parity cases, not a drop-in wire
   layout. A narrower axis-staged geometry relation must retain truncation,
   `Q20` boundaries, wall-first and strict-closer tie rules.
3. **Full boundary state.** Each proof segment has exact incoming and outgoing
   canonical state, including every player timer, ammo/charge, ordered
   projectile and damage-history entry, objectives, initial reserves and earned
   balances. The AIR constrains its first and last rows to those public values;
   the native verifier compares outgoing bytes to the next segment's incoming
   bytes. If only a state digest is exposed, its canonical encoding and hash
   must also be proven in AIR. A host-calculated digest of witness-selected
   fields is insufficient. The first state is derived from immutable admission;
   the last is terminal under the proved rules or a consensus-selected
   interruption with all pending evidence resolved.
4. **Verified prefix ledger.** A proposed `VerifyArenaSegmentV1` checks the
   STARK and the selected input span, requires exact next segment number/tick
   and state, verifies the preceding proof receipt, and retains an immutable
   session-scoped prefix cursor. It never releases funds. `SettleArenaSessionV1`
   accepts a terminal cursor only when every tick through the selected terminal
   boundary is covered, no pending commitment is erased, and the final proved
   reserve/earnings vector matches exact per-slot XOR allocations. A compact
   terminal receipt could attest to the entire **native-verified** proof chain,
   but this is not yet the requested final composition proof. A release design
   must establish whether a consensus-certified verified-chain receipt meets
   that requirement, or implement recursive verification/folding of the
   segment STARKs. This equivalence and its resource costs require independent
   review. Existing Iroha recursive components do not establish composition
   for Arena STARKs.

Each stage must enforce conservation, including fixed 10% losses from initial
bond, exact assist/team splits and deterministic remainder slots. Earnings never
reenter the slashable reserve. Death exhaustions, simultaneous kills,
unassisted deaths and verified disconnects remain part of the relation.
Unavailable inputs after a consensus deadline stop simulation at the exact
selected terminal boundary; no absent final peer signature may erase earlier
proved transitions. Equipment remains reserved until this terminal settlement.

## Release gates and first buildable experiment

The first implementable proof experiment is a **single legal attack and its
selected hit/damage transition**, not merely an isolated geometry witness:
compile an axis-staged segment/AABB relation below the 4 MiB native bound,
bind its inputs to one exact canonical two-player state and accepted control
batch, and verify its output against a second independently implemented
reference. Measure actual proof length, peak RSS, generation and verification
time on the available M1 Ultra. Forge the selected target, wall order, attack
legality, input, state boundary and payout to ensure rejection. Then compose
two consecutive segments with altered/missing/duplicated/reordered middle
boundaries and verify rejection. Register no funded profile from this experiment.

Before a release, the native 4,096-batch gate, proof portfolio admission,
appendable input commitment, vector-state bounds and data availability must be
implemented and independently reviewed. Qualification must benchmark a
two-player proof chain, the agreed 4v4 two-minute research match, then a real
6v6 36,000-tick profile including projectile-heavy stress. The sum of proving
work must remain at most 30 minutes and simultaneous peak memory at most 96
GiB on the M1 Ultra; proof bytes, validator verification, transactions, blocks,
retention and availability must fit enforced deployment limits. These are open
gates, not inferred successes. No reduction in player count, duration, combat
coverage or financial guarantees is an acceptable silent fallback.
