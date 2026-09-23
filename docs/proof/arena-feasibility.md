# Arena execution-proof feasibility gate

This is a measured research record for the requested 6v6, ten-minute,
cryptographically verified FPS match. It is **not** a qualified full-match proof.
The game's value-bearing Arena profile remains disabled. The agreed acceptance
target is at most 30 minutes and 96 GiB peak memory on the available M1 Ultra,
with the full 12-player match and every outcome-affecting rule proved.

## Actual native findings

A research adapter has generated and independently verified one native STARK
for a **single, fixed, public damage/parry transition** repeated over 8,192
rows. Its proof is 2,282,816 bytes. Generation took 522,431 ms (including
mandatory native self-verification), separate verification took 19,193 ms,
and process peak RSS was 584,663,040 bytes. Seven changed public statements
or malformed proofs were rejected. These rows are repetitions of one relation,
not game ticks. The experiment proves neither hit legitimacy nor a kill, a
complete match, or any XOR allocation. Its first-run library/source seal was
not sufficient to claim an exact reproducible build; the later hardened
build-only harness has source and dependency seals but produced no proof.

The actual compiled first-release arithmetic graph, with current four-map wall
counts, has these dimensions. The 12-player shape was compiled independently
for every attacker slot; all attacker shapes match. Values are counts from
`iroha-arena/target/research/arena-air-shape-152_1q8z/counts.csv`, whose
provenance file records source SHA-256 values, the compiler command, native
field implementation, and stable before/after source seals.

| Relation | Players | Walls | Trace columns | Constraints |
| --- | ---: | ---: | ---: | ---: |
| Aim | — | — | 1,849 | 2,039 |
| Segment/box geometry | — | — | 3,703 | 4,093 |
| Damage/parry | — | — | 575 | 663 |
| Nearest eligible hit, Nyaagyu Estate | 2 | 3 | 19,613 | 21,686 |
| Nearest eligible hit, other current maps | 2 | 4 | 23,103 | 25,545 |
| Nearest eligible hit, other current maps | 8 | 4 | 43,944 | 48,612 |
| Nearest eligible hit, other current maps | 12 | 4 | 57,836 | 63,988 |

The native profile uses eightfold low-degree extension. A single dense base
field evaluation matrix consumes at least `columns × rows × 8 × 8` bytes
before auxiliary columns, masks, Merkle trees, quotient, FRI, transcript,
witness construction, interpreter, or operating-system overhead. This is an
arithmetic lower bound for a straightforward monolithic layout, not a measured
peak process usage or a production memory forecast.

| Layout candidate, four-wall map | Rows | Single base matrix | Gate |
| --- | ---: | ---: | --- |
| 2 players, one 60 Hz track | 65,536 | 90.25 GiB | Leaves under 6 GiB for every other allocation; unqualified |
| 8 players, one 60 Hz track | 65,536 | 171.66 GiB | Exceeds 96 GiB before other allocations |
| 12 players, one 60 Hz track | 65,536 | 225.92 GiB | Exceeds 96 GiB before other allocations |
| 12 players, one 8,192-row stage | 8,192 | 28.24 GiB | Memory candidate only; actual peak unknown |
| 12 players, 524,288 serialized attacker rows | 524,288 | 1,807.38 GiB | Exceeds 96 GiB before other allocations |

The complete match has at most 36,000 ticks and 12 original participant slots.
Serializing every attacker slot produces up to 432,000 transitions, requiring a
524,288-row power-of-two monolithic domain. A simple tick-parallel layout fits
65,536 rows, but a hit graph that proves all potential attacks needs additional
per-attacker width or compositional proofs. None of the figures above includes
movement, projectiles, explosions, ability effects, objectives, input
admission, dropouts, bonds, assists, refunds, or allocation conservation.

The source-sealed native hit layout also fails the current **4,194,304-byte
proof-size cap** before proving any transitions. Its mandatory canonical trace
openings alone are 20,169,344 bytes for 2 players/0 walls, 42,952,064 bytes
for 2 players/3 walls, and 126,125,312 bytes for 12 players/4 walls. Native
maximum encoded proof estimates for the latter two shapes are 45,066,752 and
130,686,272 bytes. These figures come from
`iroha-arena/scripts/check_arena_hit_stark_feasibility.py` and the run recorded
under `iroha-arena/target/arena-hit-stark-feasibility/runs/layout-fmdzahmd/`.
The harness generated no hit proof: this is a hard limit for the **current
monolithic hit layout**, not a measured lower bound for every possible staged
or recursive design. Raising the cap alone would not resolve the memory and
full-coverage requirements above. The gate has failed for the present layout;
the value-bearing Arena profile stays disabled.

Two narrower native research proofs now fit individually, but their scopes are
far short of a match. A two-player, two-tick cardinal-movement relation produced
a 1,192,288-byte STARK in 121.994 seconds with 252,723,200 bytes peak process
RSS; fresh verification took 12.260 seconds. A three-player, two-tick
fixed-scene Arc-carbine hit produced a 2,471,808-byte STARK in 134.148 seconds
with 664,354,816 bytes peak process RSS; fresh verification took 17.426
seconds. The latter proves 30 slab fractions and damage arithmetic while host
validation fixes the scene, target and projected state. Neither relation is
registered, funded, ledger-selected, or a general kill/payout proof. See the
exact native artifacts and tampering checks in
`../iroha-arena/docs/source/arena_movement_research_v1.md` and
`../iroha-arena/docs/source/arena_ranged_research_v1.md`.

For scale only, naively proving all 18,000 two-tick slices at the measured
fixed-scene hit cost would take 2,414,664 seconds (about 28 days) of serial
proving and produce 44,492,544,000 bytes of separate proofs. This is **not** a
forecast or lower bound for a newly designed staged/recursive prover: the
fixed scene cannot express most real ticks, and proof amortization could change
both costs. It does show that repeating the current research adapter cannot
meet the agreed 30-minute target or the single-proof ledger envelope.

## Next required implementation and measurement

A staged relation must preserve the **one canonical tick order**: committed
controls; movement and collision; per-slot ability/attack mutations; complete
wall and roster hit selection; ordered damage; deaths/assists; economy and
objectives; and terminal settlement. Each stage needs a proof-authenticated
incoming and outgoing full state commitment, fixed roster/map/rule/equipment
binding, exact coverage indices, and a final composition proof. No host-supplied
kill log or unchecked checkpoint can bridge stages. Malicious omissions,
reordering, duplicate stages, and divergent public commitments must reject.

Research should implement a bounded native hit-plus-damage stage, measure
actual process peak, proof length, generation and verification time, then test
chaining and exact coverage on a two-player match. Next repeat at 4v4 for two
minutes and 6v6 for the full ten minutes. Optimize representation or proving
architecture only while retaining all requested rules and the native security
parameters. The 30-minute/96-GiB gate is not passed by the one-transition
experiment or the lower-bound table. If a complete staged profile cannot meet
it, report the failed gate before proposing any scope change.
