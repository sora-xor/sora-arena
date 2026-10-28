# Notice-square drone circuit — October 28

The old runtime flew between two points; the original authored 12 m circle
crossed the money-changer footprint below its ridge. Chapter 3 now explicitly
specifies a 5.4 m radius around the crossing, retaining the 6 m altitude and
36 s period. This follows Claude's proposed radius; the roof remains separate
unfinished work. Thirty-two rounded centimetre waypoints approximate the
circle with less than 3 cm chord error.

The production controller uses ordinary swept movement and requires every
physical arrival. A 2 cm arrival tolerance prevents short legs from stopping
20 cm short of their corners. Existing long flight corridors retain 20 cm.
Flight pacing reserves the input and subsequent arrival-observation frames
before the deadline; scheduled release and late-state rules are unchanged.
The native loader and source validator bind the circuit, height and period.

Signed implementation `0b4d133d339a6ee881d2a2c1d2ebde54ef6d7a8a` builds and
passes all 18 selected native cases with zero selected errors or warnings.
They cover both new drone cases, existing ground patrols and street routes,
charge/escape/retry, loader rejection, imported drone collision, landing
flights, ladders, campaign spaces and the assisted campaign playthrough.

The new flight fixture keeps all seven encounter guards live with a hidden,
stationary observer. Every segment clears the built static/dynamic geometry
using the full 38 cm movement sphere plus 10 cm margin. The measured live
radius is 537.327–540.281 cm; the largest movement step is 2.264 cm at the
fixture's 20 ms tick. All 32 real arrivals complete in 36.006 s without a late
flag. Menu pause freezes movement/time, resuming continues the same circuit,
and retry replaces the actor at its initial phase. This does not measure
ordinary stealth difficulty, performance or future roof geometry.

The first run at `b6dc3bc3` remains failed, 17/18. The clear route reached
every waypoint but incorrectly set the late flag because short-flight pacing
did not budget input/arrival-observation frames. Its original files and
independent review are preserved. The runtime repair does not relax the
deadline or permit a blocked waypoint to advance.

Test-only follow-up `06235881d30ff796e48085a8cea7a085d75ddbc9` holds an actual
obstruction for 40 s, longer than the entire circuit. The drone records zero
waypoints and zero laps while blocked. After removal it completes all 32
arrivals at 68.826 s and retains the late flag. This focused case passes with
zero selected errors or warnings; the other 17 retain their `0b4d133d` result.

All 66 gameplay source gates pass at `b6dc3bc3`, with unchanged inputs.
The compiled contract checks analytic circle/chord error, required speed,
data/header agreement, and malformed radius, height, period, point and count.
Fresh generation changes only Chapter 3; the campaign validator rejects its
71 existing bad variants. The subsequent runtime repair changes only flight
pacing, and the follow-up changes only the obstruction fixture.

All native builds/runs finish naturally on the M2 Ultra, UE 5.8.3 and
project-scoped Xcode 26.1.1. Independent reviews authenticate each run's 20
original files, exact selection and unchanged source/native/Config/Generated
inputs and frozen ROOT. Raw pre-initialization engine diagnostics remain
recorded. Evidence is under `Saved/Qualification/2026-10-28/` in SOURCE:

| Independent review | SHA-256 |
| --- | --- |
| First 17/18 run | `29701ee10bc5fd838aeebf2e4af9c2be42437cadf153e6e0c1692501f4e1dedd` |
| Repaired 18/18 run | `d53cd6326670946d2ea729315539269f4f12d52ae0c02a18909275b9df0c962e` |
| Full-period obstruction | `913a3b7d4d92d11e0d1e2470879205161a206df88d6cd0c01f52d986c092acf7` |
| 66 source gates and log digests | `ab68e690a1029a5689e130cc7fb50f50e2ece62cc2474bbc98b71f8e255ac5b8` |

No new flight render or package was produced. The actual pitched roof,
supported two-flight climb, rear takedown approach, final art, ordinary play,
actual-M1/Windows and performance remain unqualified. ROOT remains frozen at
`b6ba3c11`; its preserved package remains `1b6dfadc`.
