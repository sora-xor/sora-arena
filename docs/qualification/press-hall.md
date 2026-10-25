# Press stamp masking and silent-machine inspection

This is an unqualified source candidate for chapter 6, beat 11. It has not
been compiled or exercised in Unreal. The existing copying-desk regression
remains pinned to `56bdcfe` in a different worktree while the native proof
cohort runs. No local compiler, Unreal or Blender process was launched for
this change during that cohort.

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

The source includes integer rule tests for exact window boundaries, long
intervals, 30/60/144 Hz partitions and independent master state. Eight Python
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
data. Seven engine fixtures (`PressHall`, `PressInspection`, `PressNoiseEmission`,
`PressDieLamps`, `PressCheckpointReload`, `PressCatwalk`, `PressCatwalkPatrol`)
are prepared and remain unrun.
The reload fixture saves after an actual held jam and a swept arrow impact,
destroys the test world, and resumes the same save in a new world. It requires
all machines and lamps restored, no old inspection or suspicion delivered,
and exactly one encounter clock advancing. These are pending assertions, not
observed runtime results.

This is still a functional blockout. Actual catwalk/ladder and elevated
enforcer execution, authored 45/30-second patrol loops, die-lamp suspicion after
five seconds in actual play, synchronized stamp audio/music, final machines and dressing,
ordinary stealth difficulty, fresh-world save reload execution, full campaign regression
and current packages remain open. The archive-to-catwalk stair connection is
also unfinished; entry currently uses the campaign's beat placement. Neither
these host checks nor the prepared engine fixtures establish
complete campaign or release acceptance.
