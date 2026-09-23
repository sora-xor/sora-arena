# Iroha native integration

The upstream checkout for this task is `/Users/takemiyamakoto/soramitsudev/iroha-arena`, branch `codex/arena-native-games`. The original Iroha checkout is untouched. This integration is under construction; no FPS proof profile is registered or qualified and funded play must remain unavailable.

The production `connect_norito_bridge` library check and macOS dylib build, including Iroha core, pass after a reviewed prerequisite migration to the existing authority-generation model. Source snapshot hashes, the fifteen-file scope, and the remaining incumbent-only committee scheduling limitation are recorded in `iroha-arena/docs/source/arena_authority_generation_prerequisite.md` and its adjacent JSON record. Both authorization binding/seal regressions pass. Actual native C-ABI checks pass for encryption, tamper rejection, exact game transaction construction, and malformed request rejection; the tested dylib is staged under `Binaries/Mac`. The native model game codec subset passes five tests (three explicit qualification/export tests remain ignored), and the focused JavaScript allocation/race codec subset passes fourteen tests. The complete core unit-test suite and production FPS proof are not qualified by these checks.

## Generic custody contract

The initial-release Iroha model now has an explicit `GamePayoutPolicyV1::VerifiedAllocations`. The opened `stake` is a minimum deposit. `JoinGameSessionV1.expected_stake` is the exact amount the wallet approves, not an allowance. The native join checks the immutable manifest hash and asset, frozen decimal precision, minimum deposit, and existing qualification gate before funding. Every original participant stores a mandatory `deposit`, which is also mandatory in the public admission body and therefore the roster commitment. No compatibility decoder supplies an omitted deposit.

`GameOutcomeV1.allocations` is a mandatory bounded vector of `{slot, amount}`. Under the new policy, positive awards must use unique increasing original roster slots and sum exactly to all original deposits. Zero awards are omitted. `winner_slots` does not route the fungible pool. The other payout policies require the vector to be empty. Cancellation returns each original amount. Native asset movements remain private one-shot capabilities, and restoring custody indexes recomputes the same awards.

This code checks authorization and conservation, not kills. A compiled Arena relation must derive every award from the full transition trace, then commit it in the outcome authenticated by the native execution envelope. Current racing validators reject the allocation policy. Qualifying a racing relation cannot authorize Arena gameplay.

The Arena adapter must convert each exact `Quantity` to the configured integer XOR quantum without floating point, rejected rounding, saturation, or overflow. That quantum and XOR asset identity belong in immutable application parameters. It must require equality between these converted admission deposits and `arena_core::simulation::Participant.bond`, and derive the final exact `Quantity` awards from the reference economy ledger. The initial special-equipment decision must bind admitted NFT reservations or the exact higher deposit; it cannot trust a UI tier flag or an endpoint ownership claim.

## Proof compiler boundary

Iroha uses its own integer arithmetic graph, Goldilocks/Fp4 execution AIR, and transparent DEEP-ALI/FRI STARK backend. There is no guest executable or interchangeable proof VM in this path. Relevant sources are under `crates/iroha_core/src/execution_proofs/`:

- `integer_air.rs`: private `IntegerAirV1`, `Value`, arithmetic graph, witness evaluation and residue equations. Interval annotations alone are not proofs of integer range.
- `checked_integer_air.rs`: checked bounded inputs, constrained Boolean values and constrained selection. It currently compiles only for tests; a production adapter must make reviewed use of these helpers and bind their exact source to its profile.
- `staged_race_air.rs`, `environment_air.rs`, `stark.rs`: examples of staging a relation, binding the execution environment, and proving/verifying the trace.
- `registry.rs`: closed compiled-adapter dispatch. A real FPS adapter must be added here with immutable source/rule identity and qualification initially false.

The missing FPS relation must constrain canonical input bytes, position/velocity and collision, aim and visibility, attacks/cooldowns/ammunition, projectile/explosion states, melee and parry windows, health/shields/deaths/respawn, teams/objectives, assist windows, NFT/bond entitlement, original at-risk balances and all final allocations. Host replay, honest witness construction, or a hash of an unproved kill list is insufficient. Negative witness and semantic proof mutation tests, independent verification, and measured proof costs are release requirements.

### Measured native proof research

A research-only adapter has generated and independently verified a real native
STARK for one fixed public damage/parry transition. The proof is 2,282,816 bytes
(SHA-256 `f7cd23ba5598f774c7699a543f9910622eb2de78c84dd91b62766f0011edc82c`).
On this M1 Ultra, generation took 522,431 ms including the backend's mandatory
self-verification; a separate verification took 19,193 ms. Peak measured process
RSS was 584,663,040 bytes. Seven altered-public-input or malformed-proof cases
were rejected. The native security parameters were unchanged.

This relation repeats the same transition over 8,192 rows; those rows are not
8,192 game ticks. It does not prove hit legitimacy, movement, a kill, or a match,
and provides no full-size proving performance evidence. The adapter is not
registered or qualified. Exact source provenance, measurement output and proof
are under `iroha-arena/target/arena-damage-stark-research/`; its reproducible
harness and scope are documented in
`iroha-arena/crates/iroha_core/src/execution_proofs/ARENA_DAMAGE_AIR.md`.

## Native wallet bridge

The isolated upstream bridge adds `connect_norito_native_transaction_scaffold_build_v1` in `crates/connect_norito_bridge/include/connect_norito_bridge.h`. It accepts a UTF-8 JSON object with exactly:

```json
{
  "network_id": "<canonical native NetworkId>",
  "authority": "<canonical wallet AccountId>",
  "creation_time_ms": 0,
  "time_to_live_ms": 60000,
  "fee_payment": "<complete native FeePaymentIntent object>",
  "instruction": { "name": "JoinGameSessionV1", "value": "<complete typed terms>" }
}
```

The placeholder strings above are schema explanations, not a valid request. The general native bridge builder supports seven names: `OpenGameSessionV1`, `JoinGameSessionV1`, `ClaimGamePayoutV1`, `StakeGameItemV1`, `OfferNftV1`, `BuyNftV1`, and `CancelNftOfferV1`. The Arena wallet intentionally allows only the other six; `StakeGameItemV1` wagers an NFT and is unsuitable for returnable weapon equipment, which `JoinGameSessionV1.resources` reserves. No batch, arbitrary instruction or fallback is accepted. Typed terms and fee intent must match complete canonical native JSON. The builder returns an unauthorized canonical transaction scaffold and a complete inspection. Existing `connect_norito_detached_transaction_scaffold_inspect_v1` returns the exact action, authority, network, time bounds, fees, payload bytes and signing hash. Existing `connect_norito_detached_transaction_scaffold_finalize_ed25519_v1` verifies the wallet signature and authority before producing a submit-ready signed transaction. All successful output buffers use `connect_norito_free`; C lengths are `unsigned long`, which differs between Windows and macOS.

The UE integration must bind the approved Connect session, requested account, exact network, action terms, fee ceiling and signing hash. It must verify the authenticated encrypted wallet reply, request/sequence context and returned signature. Building a scaffold or receiving a relay message is not transaction finality. Do not unlock weapons or acknowledge a purchase until authenticated chain state shows the exact accepted action.

## NFTs and native catalog admission

Native `OfferNftV1`/`BuyNftV1`/`CancelNftOfferV1` provide exact immutable sale terms and atomic payment/delivery. Native game returnable resources already reserve an owned NFT with its metadata hash and role and return it to the original owner at a terminal outcome; they are distinct from `StakeGameItemV1`, whose NFT is explicitly at risk. Equipment should use returnable resources. Do not use an at-risk item instruction for a cosmetic or weapon entitlement.

The isolated Iroha worktree now implements `RegisterGameEquipmentPublisherV1` (signed-genesis-only trusted publisher scope), `PublishGameEquipmentCatalogV1`, retained state and singular queries. Publication authenticates the exact trusted publisher, collection ownership, NFT identity and full metadata hash. Core equipment admission resolves a mandatory catalog selected by the compiled manifest and checks network, application, profile, role, return policy and live metadata before shared custody. Publisher trust and catalogs are immutable; neither metadata nor a later collection owner can grant game permissions. The production bridge check and six native catalog policy/codec tests pass; focused native runtime and rebuilt SDK tests are tracked in the upstream validation log.

No publisher account or catalog is installed by this change. The FPS adapter still must derive these requirements and constrain the resulting weapon/class entitlement in its complete execution proof. Existing stock adapters request no equipment, and value-bearing Arena qualification remains false. Catalog approval establishes exact identity and metadata, not historical mint provenance. See the upstream `docs/source/native_game_equipment_v1.md` for the native trust and custody contract. A marketplace capability flag is not itself a consensus qualification check.
