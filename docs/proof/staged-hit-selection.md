# Generic staged hit-selection component

This research component implements the kernel's ordered ray-stop decision in
native Iroha AIR. It is conditional on a complete public ray-relevant snapshot;
it does not authenticate that snapshot as a reachable World state or prove a
legal attack, damage, a death, an award or settlement. It is not registered for
funded game sessions. Real-value operations remain disabled.

## Relation and reference

The upstream implementation is in `iroha-arena`:

- `crates/iroha_core/src/execution_proofs/arena_staged_hit_air.rs` provides the
  staged relation and its witness generator.
- `arena_staged_hit_stark_research.rs` supplies typed inspect/prove/verify APIs
  through the existing native STARK backend. The verifier reconstructs fixed
  columns from the public statement; it does not run host target selection as
  a substitute for checking the proof.

The statement binds the attacker slot, aim, range, team/melee/ally controls,
ordered player states, walls, entities, claimed result and computational source
identity. Supported counts are 1–12 players, 0–64 walls and 0–48 entities. The
current maps require up to 42 walls, so the previous four-wall research scene
cannot represent them. Snapshot validity checks and AIR constraints are both
required; the public input cannot choose a different transition schedule.

The AIR computes fixed-point aim and segment/box intersections, then selects
the strictly closest eligible hit in wall, entity and original player-slot
order. It preserves wall-first ties, dead-player and enemy spawn-protection
exclusions, teammate healing eligibility, barricade blocking, enemy decoys and
melee expansion. Entity identity is distinct from vector index. Fire zones and
wards are skipped by this ray-stop relation. Carry constraints cover all 29
scratch values, including initialization, every microstep, final output and
padding. Candidate omission, duplication or reordering cannot select a new
execution schedule.

The game-side independent reference is
`crates/arena-core/tests/staged_hit_reference.rs`. It uses the actual kernel
`direction`, `scale_q15` and `Aabb::intersect` arithmetic with a separate simple
target fold, rather than the AIR's clipped-plane implementation. Its checked-in
fixture, `tests/data/staged_hit_reference.json`, contains 92 cases: 32 directed
edge cases, 28 map/aim cases and 32 deterministic maximum-size scenes. A separate
test compares the fold with actual `World::step` shot, damage, healing and entity
events in 23 directed scenes. This is component parity, not independent
reference coverage of the entire game simulation.

Fixture SHA-256:
`d0a3443232c3b9440f5cb607861e8459285da7b1184303bbb81c01b61e08d3bf`.
The native fixture copy must match these bytes exactly. The fixture also binds
the kernel math, simulation, tick orchestrator and ability source hashes; source changes require
deliberate regeneration and renewed parity review.

## Checkpoint status at the user's stop request

The final native source compiles in full Core after three missing `Copy` derives
were added: two integration tests passed, one expensive prover test remained
explicitly ignored, and 25 existing warnings were not suppressed. The source
manifest stayed identical throughout that build. The game then extracted the
unchanged tick phases and regenerated the fixture's source hashes; all 92 case
values and the recorded kill-history results remained identical.

The user requested committing the work and stopping before the final-source
proof rerun. The proof measurements below belong to their recorded **earlier
source and fixture identities**. They are historical component evidence, not
proof verification for the final checked-in checkpoint. Final-source proving,
independent review and full-game qualification remain outstanding.

## Measured earlier layout, 2026-10-18

| Quantity | Native executable result |
| --- | ---: |
| AIR columns | 674 |
| AIR fixed columns | 46 |
| Profile constraints | 4,302 |
| Maximum-size scheduled rows | 1,371 |
| Native trace rows including padding | 8,192 |
| Native base / auxiliary / fixed columns | 682 / 118 / 89 |
| Conservative native wire bound including DEEP | 2,643,392 bytes |
| Unchanged native proof cap | 4,194,304 bytes |

Column width does not grow with the supported candidate count; the scheduled
row count does. This layout fits the native component cap, not necessarily the
full game envelope, public input, transaction or final composition limits.
The native parameters remain 136 queries, eightfold extension, maximum
constraint degree four, four composition chunks, and a 1,024-point FRI terminal
with degree bound 143. No security parameter or coverage was reduced to fit.

Six focused AIR tests pass, including the 92 reference cases, mutated carry and
output values, coherent forged suffixes, altered public snapshots, candidate
schedule attacks and padding. These tests used the exact native field and AIR
sources with recorded compiler and dependency identities. The separate moved-
kill integration target also compiled in full `iroha_core`: two tests passed,
one expensive proof-generation test was ignored. That older target remains a
fixed two-tick projected scene and is not evidence for a complete game proof.

The earlier source-sealed native proof for maximum-size `bounded_random_9`
completed and verified. It fixes attacker slot 9 and proves selection of entity
ID 6 at Q20 fraction 10,263. The public API accepts bounded snapshots; this
experiment's fixed fixture does not narrow the compiled relation to that scene.

| Measurement on the M1 Ultra | Observed result |
| --- | ---: |
| Actual native proof bytes | 2,514,656 |
| Proof generation | 409.071 seconds |
| Positive verification | 22.003 seconds |
| Entire binary, including ten negative verifications | 504.81 seconds |
| Entire binary maximum resident set size | 735,494,144 bytes (701.42 MiB) |
| Rejected negative verifications | 10 / 10 |

Proof SHA-256:
`22c0daae0817b50a4917fdef86f922ec1da4d7b191be71a90a5a8b66f2e3da18`.
Negative checks alter the result kind, identity, fraction, yaw, actor position,
wall and entity team; they also truncate, append to and corrupt the proof.
Source, toolchain and exact dependency seals match before compilation, after
compilation and after verification. All 22 recorded artifact hashes match,
including before/after seals for the fixture, runner, generated sources and
binary. The sealed compiler is Rust 1.93.1, invoked by its exact sysroot path.

An initial run genuinely verified but recorded the game checkout's Rust 1.97.1
while compiling from Iroha's Rust 1.93.1 checkout. Its compiler provenance is
invalid. It remains separately retained under `staged-hit-stark-native`, with a
provenance-error note. The table above uses the fresh corrected run, which
repeated proving and all verification checks with the repository-owned runner.

The executable included the native AIR, adapter and STARK backend plus
the unchanged extracted native field implementation. It used seven explicitly
recorded rlibs. It is a source-sealed component harness, not an Iroha validator
or a live session. `RAYON_NUM_THREADS=4` bounded worker count. Darwin
`/usr/bin/time -l` measured the entire executable, including its negative
checks; the RSS above is not an isolated proving-phase peak. Claude's art work
was active on the machine, so this is an observed shared-machine run rather
than an uncontended release benchmark. It does not establish the full-match
30-minute resource gate.

Corrected evidence is under
`Saved/Qualification/2026-10-18/staged-hit-stark-qualified-harness/`: `run.log`,
`run-status.json`, the three seals, dependency/source manifests and `result/`
containing the proof, public statement, layout and measurements. These ignored
machine-local artifacts are not checked into the game repository. The directory
name refers to the harness; the relation remains explicitly unqualified.
A compact checked-in [observation manifest](evidence/staged-hit-2026-10-18.json)
retains the source, compiler, dependency, fixture, runner and artifact hashes
alongside the measured results, without requiring these local absolute paths.

## Reproduce the component experiment

Run the repository-owned `scripts/qualification/staged_hit_proof.py` from the
game root. It requires an existing native checkout and built dependencies, an
explicit manifest of exact rlib paths and hashes, a reference fixture/case and
a new output directory outside the frozen Iroha checkout. It never guesses
dependency versions. The recorded manifest below is usable on this machine;
another machine needs its own explicitly pinned manifest matching its build.

```sh
python3 scripts/qualification/staged_hit_proof.py \
  --iroha-root ../iroha-arena \
  --target-dir ../iroha-arena/target \
  --dependency-manifest Saved/Qualification/2026-10-18/staged-hit-stark-native/dependencies.json \
  --fixture crates/arena-core/tests/data/staged_hit_reference.json \
  --case bounded_random_9 \
  --output-dir Saved/Qualification/staged-hit-reproduction \
  --threads 4 --prove
```

Omitting `--prove` performs only layout inspection and records
`proof_verified=false`. The runner uses the compiler from the native seal's
exact sysroot and captures toolchain state from the Iroha working directory.
It seals the driver, fixture, manifest, guard, generated sources and binary as
well as native source/dependencies. Failures or drift invalidate the run. The
JSON fixture is bounded and strictly typed before it can generate Rust source.
Darwin/Linux resource reports retain their platform-specific units; unsupported
hosts explicitly report that RSS was not collected.

Fourteen guard tests pass, including invalid types/code injection, counts and
bounds, duplicate identities, stale dependency hashes, source/generated-input
drift, occupied output paths, compiler failure, and foreign-working-directory
compiler selection. The corrected runner's separate layout self-check passes
with matching seals; layout success is not a substitute for a proof run.

```sh
python3 scripts/qualification/test_staged_hit_proof.py --iroha-root ../iroha-arena -v
cargo test --locked -p arena-core --test staged_hit_reference
cargo clippy --locked -p arena-core --test staged_hit_reference -- -D warnings
```

## Remaining composition work

This component still needs authenticated full-state boundaries, ledger-selected
controls, attack legality, movement and collision, damage and guarding,
projectiles and explosions, abilities, objectives, death and assist attribution,
exact conserved awards, and terminal-on-disconnect semantics. A public snapshot
is a premise, not proof that those fields arose from accepted play. The
computational source digest is a research tripwire, not a qualified release
profile identity or an independent security audit.

The [staged execution design](staged-arena-v1.md) records the open session,
retention and proof-composition gates. A maximum-size snapshot proof is not a
12-player, 36,000-tick match proof; the agreed 30-minute/96-GiB full-match target,
Windows/macOS agreement, independent proof review and actual four-validator
settlement runs remain unqualified.

The observed standalone cost also makes a separate proof for every shot
unsuitable for the full-match target. Execution stages must amortize that work;
the resource gate must then be measured on actual full-match coverage. A source
review identified repeated per-program residue allocation and repeated
vanishing-polynomial inversions as optimization candidates. Neither has been
profiled or changed in this experiment, and neither establishes full-match
feasibility. Security parameters, player count, duration and financial coverage
remain requirements.
