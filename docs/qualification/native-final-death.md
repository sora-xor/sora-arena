# Bounded native final-tick-death proof

Signed native source `cd9263628d5fea902675189cf3700ef14d29f080` completes
`execution_proofs::arena_prepare_air::carbine::native::tests::actual_native_final_tick_death_proof_and_adversarial_cohort`
on the M2 Ultra, using the previously reviewed retained privacy-crate binary.
The production game bridge remains `10ad7daddf73212e81496620aba628ebf214ab72`.

## Observed result

The `death-map0-mutual-1-2` case produces a 3,666,144-byte native proof,
SHA-256 `136790ec0f892cb53a972e52ec0e4823c4897e1bb8acc9f8149351cf6ec4820a`.
Separate native verification returns success. The maximum wire-size bound is
3,803,712 bytes, below 4 MiB, with 3,039 active rows padded to 8,192 trace rows,
1,200 base columns and 45 programs.

All 103 negative cases complete:

- 90 public/request/statement/boundary/death-output mutations fail native verification.
- Corrupt and truncated proofs fail native verification.
- Eleven private-trace, reordered/padding, false-boundary and false-death
  cases run the actual prover and return `Constraint`, including both player
  accounts and the terminal result. They are not substituted verifier tests.

The complete cohort takes 9,621.28 wall seconds. The positive prover reports
1,298.258191 seconds and its separate verification 19.579289 seconds. Peak
reported test RSS is 2,050,899,968 bytes. Recorded unrelated compiler load means
these are execution observations, not performance qualification.

## Evidence

The listing and proof phases both reach natural output-stream EOF with
process/collector exit zero. No resource guard breaches occur; the unchanged
10,800-second observation bound and disk reserve hold. The signed source,
36 embedded source inputs, retained binary, sealed prerequisites and every
one of the 116 archived files independently verify.

Evidence remains under the isolated dojo-timber-capture worktree's
`Saved/Qualification/2026-10-25/native-final-death-proof-cd9263628d/`.
The independent review digest is
`0ecaeb6a1aeeafcbc08e977bef10e072003d2b0ef548bc75b76914db217281d5`.
Binary SHA-256 is
`b75f671cff284d16ff098f38d838fd1f42b2178d6d3de5d4081acafb273c2624`;
sealed plan SHA-256 is
`34d0da35174242e121944b5c1006a0a084b39b7179e718400f4ffb6caabcdd7f`.
Earlier CPU preparation/observer failures remain preserved separately.

## Remaining scope

This is the unregistered caller-bound two-player/two-tick relation. It does
not establish full World/Core execution, a registered production profile,
full-match proofs, four-validator admission/dispute/settlement, Connect
finality, reference-M1 performance or complete-game acceptance. No production
bridge, registry, live funding or trading was enabled by this run.
