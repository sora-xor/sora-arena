# West landing source checkpoint — not runtime qualified

This prepares chapter 3's west landing and two timed patrols for an Unreal
build. It is separate from the already exercised landing-drone attack. The
new C++ has not been compiled or run in Unreal. Claude owns the engine and
Blender lane while producing the character revision.

The generated data now uses the authored 44 × 16 m yard, entry at the west
steps, three lamp positions, six puddles, five cargo stacks and north-east
exit. Both b01's last camera shot and b02 share that place. Every other zone
retains its existing placement. The b01 100 m boat approach and bridge are
still outstanding.

D1's 40 s route is a sampled figure-eight at 500 cm. The chapter's proposed
four knots would form a diamond; the prose's figure-eight governs, retaining
the proposed centre and bounds. D2 retains the authored canal endpoints,
400 cm altitude and 30 s out-and-back period. Both use swept character
movement and arrival-gated deadlines. D2 also carries a shadow-casting
downward spotlight; the stealth light query checks that actual cone and
opaque cover and extinguishes it when the drone is downed.

Six CPU tests pass, including compiled C++/generated-data parity, a genuine
crossing with oppositely oriented lobes, reachable leg speeds, blocked
scheduler deadlines, mutation rejection and binding isolation. Generated
campaign data passes `build_campaign_data.py --check`. These are source
checks, not proof of Unreal movement or ordinary play.

Four new Unreal fixtures are prepared under
`SoraArena.Campaign.LandingSpace`: `Solids`, `Patrols`, `Searchlight` and
`BlockedPatrol`. None has run. The patrol observer is deliberately held
inside a warehouse solid to isolate flight from detection. Passing those
fixtures will still not establish an ordinary-control stealth route.

Open before integration or acceptance:

- Compile and run the four new fixtures and existing landing-drone attack
  regressions. Check generated collision, imports, navigation and lighting.
- Physically play all three routes, snuff each lamp with its one-second
  interaction, and verify puddles, detection carryover and the real exit.
- Review the lower quay, boats and east gangplank. These are provisional
  functional geometry. The current visible canal is 6 m rather than the
  authored 10 m, and the enclosing south wall needs replacement by a coherent
  canal/bank boundary. Do not treat this geometry as accepted chapter art.
- Inspect D2's spotlight in rendered play and check visual/gameplay agreement
  at the steps and behind the boats; source constants are not visual proof.
- Complete the boat approach and final warehouse/shed/canal craft with Claude.

The previous integration commit `e8e392c9` independently passed all 118
source gates in CI run `40277452775`. Its tested merge
`17730829433ea7ff6982f3038b63ffa154bc718a` has the identical tree
`34d4b5fc65a5f0bd39fb65ecaf5f408112856e1b`; artifacts and raw logs were
authenticated. That result predates this landing work and does not qualify it.
