# Rendered horse-defense withdrawal

`SoraCapture.HorseWithdrawal.Live` is a prepared scene review for the
chapter-two defense ending. At exact `c63af6f`, its editor build passes in
21.60 seconds and the Metal SM6 1280×720 test passes in 158.90 seconds,
with zero selected errors/warnings and natural editor/wrapper exit zero.
All three original images were reviewed. The earlier thirteen-test NullRHI
result at `0adc081` remains separate evidence.

The fixture loads an isolated `ch02.b06` checkpoint and uses a fixed overview
camera. It freezes enemy combat through the real 150-second defense timer,
retains six actual pod arrivals, then releases their ordinary movement when
the campaign assigns withdrawal. It never writes task progress, enemy
positions, arrival state or defeat credit. This is not an ordinary defense
playtest and cannot establish combat pacing or difficulty.

The three overview originals show the retreat bark, physical walking and Kohagi's
gate-clear call. Requests bind to the actual bilingual HUD draw and completed
screenshot frame. The world remains live. The fixture waits through the full
call and verifies real grounded arrivals, one completion, no survivor shots
and unchanged defeat credit. The profile, settings, controls and temporary
save cleanup are checked. Image files and observations are archived unchanged,
including originals from a failed semantic check.

The subsequent source candidate adds an `arrival-detail` original immediately
after the gate-clear overview, while the same call and ordinary clock continue.
Only this fourth frame hides the HUD. Its fixed camera at `(-2220, 0, 1200)` cm
looks at `(-2300, 0, 90)` with a 45-degree horizontal field of view. It waits
two frames for the view change and requires the actual player-camera cache
to match the prepared position, rotation and field of view. All six identities,
grounded arrivals, matching screenshot frames and cleanup remain required.
The current-only `sora-arena.withdrawal-capture.v2` contract requires all four
originals and their explicit HUD states. Historical v1 evidence remains intact.
This new camera and the tracker correction have not yet run in Unreal; the
extra detail cannot establish ordinary HUD visibility or finished art.

Run the existing guarded capture launcher with the exact filter at 1280×720
and Metal SM6 first. Review all four current original PNGs before considering a
second viewport. Projection and HUD layout checks alone do not prove visible
enemies, readable subtitles, proper materials or finished animation.

Four affected host groups pass on the source candidate: withdrawal evidence,
cargo evidence, capture reports and frame contracts. They reject shortened
clocks, false arrivals, swapped actors, missing/replayed images and failed
cleanup. The new four-frame candidate passes 75 tests in these groups,
including rejection of a hidden overview HUD or a substituted detail camera.
Exact tracker revision `ede1c06` passes all 107 CI source gates in five jobs;
the tested tree, artifact digests and raw logs were independently verified.
Its 279 Rust passes and five explicit ignores do not qualify the subsequent
four-frame source or any engine runtime.

The actual defense lasted 150.000 world seconds and 150.176 wall seconds.
The three screenshot requests matched their processed frames exactly. Six
living survivors reached the approach without firing or receiving defeat
credit. Kohagi's complete call preceded completion, and profile/mapping/save
cleanup passed. All 32 archived files and four original/archive pairs were
rehashed; source, native inputs, Config and Generated remained unchanged.

Retreat movement and bilingual dialogue are readable in these images. At the
gate, bodies overlap each other and the torii posts, so the six arrivals are
not individually distinguishable from this camera. The tracker also retained
“Hold out: 0 s left” after the defense ended. A subsequent source correction
shows “Pack horses defended” during withdrawal; that correction has not yet
run in Unreal. Better arrival framing, ordinary play and final art remain open.

This functional capture allowed recorded background CPU compilation, with an
exclusive Unreal/Blender slot, at least 24 GiB free physical memory at launch
and the unchanged 30 GiB disk reserve. It is not performance qualification.
The original preparation requiring all compilers to be idle is preserved.
Evidence: `Saved/Qualification/2026-10-25/withdrawal-sm6-c63af6f/1280x720-20261025T074606Z-305577ad/`;
the independent `root-review.json` SHA-256 is
`0a9ea8a51855ad969dcc0be10f7880c10a0c971cfdfaec9573343ad800e4254a`.
