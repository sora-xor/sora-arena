# Press stamp masking and silent-machine inspection

The first Unreal run on signed `c3fcf8ef42bd7f34cfff61cd8f5235be971684f6`
built successfully in 25.72 seconds on the pinned Mac toolchain. It ran all
13 selected NullRHI tests and exited naturally with editor status 3 and
wrapper status 1: eight passed and five failed. The failed report is retained
at `Saved/Qualification/2026-10-25/press-c3fcf8e-runtime-attempt1`.
Its 20 evidence files, source/native inputs, generated content and configuration
were independently checked; review SHA-256:
`0cc4a03c645beffca69cb2bdb2f9160b3cd90fc45ce355495ccba7536e70b624`.

Passing fixtures were PressHall, PressInspection, PressNoiseEmission,
PressDieLamps, PressPatrolCadence, PressPatrolBlocked, CopyDesks and Candle.
The first six establish only their directed conditions with isolated senses
or frozen guards, not ordinary stealth difficulty or visual quality.

Failures remain explicit:

- PressCheckpointReload and PressExit tried to rebind Interact while playing;
  the controls API correctly refused. Their setups now open the controls menu.
- PressCatwalk exceeded its 150 cm/s movement bound at the landing. The next
  candidate ends at the character movement component's normal floor clearance
  instead of six centimetres above the deck, avoiding an extra floor snap.
- PressCatwalkPatrol did not reach all corners. The fixture now uses the same
  capsule-adjusted, three-dimensional route setup as the authored enforcer
  and records its final position and reached corners. No navigation fix or
  successful circuit is claimed yet.
- Assisted Playthrough stopped at the held objective in chapter 6 beat 11.
  The next candidate records held-input and physical-state diagnostics; the
  cause and full campaign result remain open.

The focused follow-up on signed `f9b12114878b371567c7608d90c3bae2d09c7aed`
passed PressCatwalk, PressCheckpointReload and PressExit. The largest measured
ascent step was 2.5 cm at 60 Hz. Playthrough and PressCatwalkPatrol still
failed; the guard stopped at local feet (4131.549,2222.871,402.150) after
reaching only the first corner. The held objective cancelled at the first
master while the hero remained grounded and Interact stayed held. The run
exited naturally with editor 3/wrapper 1; all source and generated inputs
remained unchanged. Review SHA-256:
`e74ceb09c09e1e2b4dc00ab160d4ee165729d4a8b253ba99e828fd944a6f64a4`.
The diagnostic follow-up at signed `5a183a4` reproduced both failures.
The guard had an unobstructed southward capsule sweep, but navigation returned
only a partial path ending at local (4140,2188,410). The candidate now follows
the authored flat catwalk segments with ordinary movement, capsule sweeps and
floor-support checks. It uses a 20 cm arrival radius at narrow corners and
never advances a blocked segment. A physical barrier fixture checks that it
waits and resumes before completing the circuit. This does not change the
120 cm walkway or the project's global navigation resolution.

The campaign fixture now faces the handle, finds an unobstructed work position
without body-drag priority, and presses the actual mapped interaction instead
of starting the press through GameMode directly. Press holds use 60 Hz ticks
so their physical state is observed at the same cadence as the focused tests.
These changes are not yet compiled or run; no successful fix is claimed yet.
The diagnostic run's review SHA-256 is
`14a3227e1e31e83824fbd1ddb4f7c2dcfe8de4636ebfe54a6e861442616435ac`.

The implementation description below records intended behavior; where it
says execution is pending, these dated results take precedence. Prior Linux
CI at `2b911ea` passed all 108 source checks; source CI does not establish
Unreal behavior.

The previous encounter credited three four-second held objectives, but had
no running presses, stamp masking or silent-machine inspection. The candidate
places the eight machine footprints from chapter 6 L7 on a 42 by 24 metre
floor. A2, B2 and C1 retain their separate four-second holds. Grounding, reach
and a clear view to the handle are required at admission and during work.
Releasing, leaving or becoming obstructed resets an unfinished jam; clearing
an obstruction while holding the key does not restart it.

The stamp clock advances before actor perception and sound emission. It
freezes when play is paused and resets with the beat. A running press masks
player noise to 0.2 within 800 cm of its impact, for the first 500 ms of every
1600 ms period. Overlapping presses do not compound the mask. Impulse noise
stores its loudness when emitted, including ranged attacks, melee, landing,
takedowns and player-instigated thrown objects or explosions. Alarms and
unrelated environmental sounds retain their behavior. Footsteps integrate
the masked and exposed perception values across the interval; averaging an
audible radius would incorrectly make a distant listener hear the quiet part.

Jamming stops that machine's masking immediately. An available living,
calm auditor receives a real navigation errand to the jammed master. An
unreachable path cannot count as arrival. The twenty-second deadline and
actual arrival are recorded separately, so a blocked or delayed inspection
cannot silently become a passing timed event. An unavailable auditor remains
pending; suspicion, search and detection take precedence over inspection. The first jam
and dispatch raise their authored dialogue events.

The source also places a hanging 5,500 K die lamp above each master. Its lens
requires a swept arrow impact; bullets, melee and blast do not extinguish it.
Five seconds of encounter time after it goes dark, the nearest living guard
becomes suspicious of the lamp's location. An auditor does not raise an alarm
from this alone, and an existing search or alert is not downgraded. Pause
freezes the delay; retry clears it and restores the lamps. This behavior has
an additional prepared `PressDieLamps` collision/delay fixture and remains
uncompiled and unrun in Unreal.

The catwalk candidate now places a colliding 1.2 metre perimeter at four
metres, with a north-west ladder opening and an elevated rifle-enforcer
route. Checkpoint entry starts on the catwalk. Mapped Jump takes the ladder
when grounded, close to an endpoint and facing it; pressing Jump again
releases it. Every alignment, vertical and landing step sweeps the actual
capsule, with a shared 150 cm/s movement budget across corners. An obstruction
holds the current waypoint rather than allowing time to advance through it.
Pause freezes traversal, and leaving the beat clears its held movement mode.
Drops use ordinary gravity and emit landing noise through the press mask.
The source fixtures cover these assertions, including retry during a climb
and a living enforcer following all four sides with senses isolated. None of
these traversal or navigation results has yet been observed in Unreal.

The two auditors now have offset eight-station inspection circuits, scheduled
for 45 seconds. The drone has a four-corner circuit over the rows, scheduled
for 30 seconds at a fixed 450 cm floor-relative height. The two floor rifle
guards use separate aisles between A–B and B–C; the third retains its catwalk
route. Scheduled travel uses the remaining real navigation path to choose a
pace within the archetype's speed limit. It requires actual arrival, faces
the machine during the reserved inspection pause, and records missed
deadlines instead of skipping blocked stations. Menus, investigation,
combat and explicit errands do not count as uninterrupted patrol time.
The late flag remains visible after a delayed arrival. The generic untimed
patrol remains the default outside these scheduled routes.

`PressPatrolCadence` and `PressPatrolBlocked` are prepared to exercise actual
movement of both auditors and the drone, the 45/30-second periods, every
station, pause/inspection priority and a fifty-second physical obstruction.
Their senses are isolated; ordinary encounter behavior still needs its own
execution evidence. Neither fixture has run yet. The portable schedule tests
cover early and late arrivals, a full-period obstruction, and 30/60/144 Hz
partitions and pass in the exact `2b911ea` Linux CI run. The Unreal
controller and its actual movement remain uncompiled and unrun.

Floor chatter and the lift exit now carry an explicit floor-height bound.
The exit cannot be pre-credited while a master is still running, or activated
from the catwalk above it after the jams. A prepared `PressExit` fixture uses
real held input for all three masters, rejects an early lift visit and an
elevated attempt, and requires returning to the floor to finish. Its positions
are assisted; it has not run in Unreal.

The source includes integer rule tests for exact window boundaries, long
intervals, 30/60/144 Hz partitions and independent master state. Ten Python
contract tests pass, including malformed numbers, reordered or missing
machines, altered authored rules and footprint clearance at work/patrol
points. Campaign generation and the existing schema validator pass all 133
beats and reject its 65 malformed fixtures. The timber binding changes only
the chapter-six digest. The C++ rule driver passed on Linux in CI run
40211292915 at `f9a4545`; that run also exposed the press enlargement moving
later zones and failing the existing climb/flood baseline. The correction
extends the hall six metres into its existing thirty-metre gap, preserving
all other zone coordinates. Four host-only moat checks (including the
unchanged baseline) and the six press contract checks pass on the corrected
data. Ten engine fixtures (`PressHall`, `PressInspection`, `PressNoiseEmission`,
`PressDieLamps`, `PressCheckpointReload`, `PressCatwalk`, `PressCatwalkPatrol`,
`PressExit`, `PressPatrolCadence`, `PressPatrolBlocked`)
are prepared and remain unrun.
The reload fixture saves after an actual held jam and a swept arrow impact,
destroys the test world, and resumes the same save in a new world. It requires
all machines and lamps restored, no old inspection or suspicion delivered,
and exactly one encounter clock advancing. These are pending assertions, not
observed runtime results.

This is still a functional blockout. Actual catwalk/ladder and elevated
enforcer execution, actual 45/30-second patrol timing, die-lamp suspicion after
five seconds in actual play, synchronized stamp audio/music, final machines and dressing,
ordinary stealth difficulty, fresh-world save reload execution, full campaign regression
and current packages remain open. The archive-to-catwalk stair connection is
also unfinished; entry currently uses the campaign's beat placement. Neither
these host checks nor the prepared engine fixtures establish
complete campaign or release acceptance.
