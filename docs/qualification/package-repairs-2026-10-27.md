# October 27 package failure repairs — native checkpoint

Signed `73753ddec2e2032e5a16d9168ced6ffad3653d2f` builds in UE 5.8.3 and passes
all 39 selected editor automation cases on the M2 Ultra. This includes the four
cases that failed in the `541c61ae` Mac package: `Campaign.MoatHands`,
`Campaign.Spaces`, `Fieldcraft.Stones` and `Integration.GuardedWork`. The full
assisted campaign also passes. This is a NullRHI regression run, not a fresh
package, ordinary-play approval or visual acceptance.

The player's guard and central arm-selection inputs now respect stowed hands.
The moat case uses the permitted katana, verifies cancellation on water entry,
refusal of new guard/fire/weapon-wheel inputs while swimming, and restoration
on the bank. The early bow remains unstrung. Other corrections make the test
fixtures match authored play: actual local floor heights, bench approaches,
staged roofs, drone flight corridors, collectible access, a physically thrown
stone within hearing range, and a mapped held interaction at a real writing
desk. Checks are retained; none is disabled or marked expected-failed.

Optional timber variants are queried through the mounted package store before
loading. Existing per-hall own-log/pool/box coverage remains explicit. Restaged
candles receive unique UObject names instead of replacing an object pending
collection. The candle overwrite warnings do not recur in the selected native
cases. Packaged SM6 validation is still required for the missing timber warnings.

The 39-case run finishes naturally at `2026-10-27T04:45:43Z`, with zero test
errors and four warnings. Three are CharacterMovement warnings from the
dialogue prerequisite fixture's half-second simulation steps; the fourth is an
engine connectivity request timing out at `www.google.com/generate_204` during
equipment recovery. The original warnings remain recorded.

Signed `86caa5d363ae92e4b3b4d334a54ba2939f3e237d` changes only that dialogue
fixture, splitting the interval into five 0.1-second steps and stopping at a
beat transition. It builds and passes all seven affected dialogue and epilogue
cases with zero errors or warnings, finishing naturally at
`2026-10-27T04:48:49Z`. The other 38 cases from the first run are not repeated
after this fixture-only change. No production movement setting changes.

Six affected host suites also pass: fieldcraft rules, stealth rules, 20 tenement
tests, 22 workshop tests, eight landing tests and nine timber-binding tests.
The earlier stowed-hands checkpoint separately passes five moat and seven
infiltration host tests. These source checks do not replace native execution.

Both native runs verify exact requested test names, 20 original evidence files
each, source and tree identities, natural EOF receipts, and unchanged source,
native bridge, configuration and generated assets. The bridge remains
`10ad7daddf73212e81496620aba628ebf214ab72`.

| Evidence | SHA-256 |
| --- | --- |
| Independent host-suite review at 73753dde | `78ed8607c5ef8cbc4bf9cb15c871dc2d9146dd210d289f0f1d0bfbc2a5387104` |
| Native39 original status | `c8aeb1e7e18978e1d126987d41a083cdbe0b2523eef5b5e1fa02c4c47dc2fa62` |
| Native39 independent review | `af42c1662803f14fdd271d01eeb3e6c494fb8161e7b03436a2f6d1567d881a2f` |
| Dialogue7 original status | `36c9affacf90ee410ecb81a36247b052615c932b251f655b285d6632408648cc` |
| Dialogue7 independent review | `e2551b4c296f2a067222d2d039b92328a316629e4512a43c8619354f42dda2ae` |

Evidence is retained in the integration worktree under
`Saved/Qualification/2026-10-27/package-repairs-runtime-73753dde-attempt1` and
`dialogue-step-runtime-86caa5d3-attempt1`. The failed `541c61ae` package and its
267/271 results remain unchanged. A new package, readable player-facing credits,
final art, ordinary gameplay, M1/SM5, Windows and performance qualification remain
open. Claude's craft contact, camera visibility and crouched reach defects are
still being repaired; no art deliverable is accepted by these tests.
