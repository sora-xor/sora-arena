# West landing source checkpoint — not runtime qualified

This prepares chapter 3's west landing and two timed patrols for an Unreal
build. It is separate from the already exercised landing-drone attack. The
new C++ has not been compiled or run in Unreal. Claude owns the engine and
Blender lane while producing the character revision.

The generated data now uses the authored 44 × 16 m yard, entry at the west
steps, three lamp positions, six puddles, five cargo stacks and north-east
exit. Both b01 and b02 share that place. Every other zone retains its existing
placement. The scene now includes the 100 m approach, ten-metre-wide canal
and timber bridge at X −160 m. Its lowest stringer is 240 cm above the water;
the opening camera follows a continuous path beneath it. The actual boat,
character performance and final cinematic direction remain outstanding.

Banks are 160 cm above the water. A physical bed replaces the provisional
lower quay; six west steps descend to it and an east gangplank returns to
the landing. The bed is 40 cm below water, an implementation choice sent to
Claude for design review, not a depth specified by the chapter. It supports
wading and the moored hulls' 35 cm draft. Wet footsteps double in either
stance; dry boat decks and bank heights are excluded. The outer south wall
now sits beyond the opposite bank. Water shading and finished bank/boat art
still need visual review.

D1's 40 s route is a sampled figure-eight at 500 cm. The chapter's proposed
four knots would form a diamond; the prose's figure-eight governs, retaining
the proposed centre and bounds. D2 retains the authored canal endpoints,
400 cm altitude and 30 s out-and-back period. Both use swept character
movement and arrival-gated deadlines. D2 also carries a shadow-casting
downward spotlight; the stealth light query checks that actual cone and
opaque cover and extinguishes it when the drone is downed.

Eight CPU tests pass, including compiled C++/generated-data parity, a genuine
crossing with oppositely oriented lobes, reachable leg speeds, blocked
scheduler deadlines, mutation rejection, binding isolation and camera/bridge
clearance. These are source checks, not proof of Unreal movement or ordinary
play. The earlier signed `22eacc89` passed all 88 selected gameplay/tooling
source gates with a clean, unchanged tree; that result predates this canal
revision.

Seven new Unreal cases are prepared under
`SoraArena.Campaign.LandingSpace`: `Solids`, `Patrols`, `Searchlight` and
`BlockedPatrol`, plus `Routes.Eaves`, `Routes.WaterEdge` and `Routes.Shed`.
None has run. The patrol observer is deliberately held
inside a warehouse solid to isolate flight from detection. Passing those
fixtures will still not establish an ordinary-control stealth route. The
three route cases use mapped crouch, movement and lamp interaction from the
authored spawn without position warps, but freeze combat to isolate traversal.

Open before integration or acceptance:

- Compile and run the seven new cases and existing landing-drone attack
  regressions. Check generated collision, imports, navigation and lighting.
- Physically play all three routes, snuff each lamp with its one-second
  interaction, and verify puddles, detection carryover and the real exit.
- Review the shallow bed, boats, banks and east gangplank in actual play.
  Confirm the selected depth and all collision transitions. Do not treat this
  functional geometry as accepted chapter art.
- Inspect D2's spotlight in rendered play and check visual/gameplay agreement
  at the steps and behind the boats; source constants are not visual proof.
- Complete the boat/character cinematic performance and final
  warehouse/shed/canal craft with Claude.

The previous integration commit `e8e392c9` independently passed all 118
source gates in CI run `40277452775`. Its tested merge
`17730829433ea7ff6982f3038b63ffa154bc718a` has the identical tree
`34d4b5fc65a5f0bd39fb65ecaf5f408112856e1b`; artifacts and raw logs were
authenticated. That result predates this landing work and does not qualify it.
