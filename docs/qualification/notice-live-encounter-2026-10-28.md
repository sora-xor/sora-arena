# Notice-square live encounter — October 28

Both the north-alley and roof routes now complete ch03.b10 in directed native
automation with keyboard and controller input. All seven authored guards and
their brains start live, at Normal difficulty, with the checkpoint's normal
145 HP. The fixture never places the hero, removes guards, changes health,
disables senses or changes collision. The roof marksman is defeated through
the mapped rear-takedown action during the route.

This establishes two rehearsed routes through the complete encounter. It does
not establish first-time discoverability, a generous timing margin, ordinary
play, arbitrary checkpoint/patrol phases, variable-frame-rate robustness or
full campaign acceptance. Final art remains rejected as recorded in
[the night-readability review](notice-night-readability-2026-10-28.md).

## Qualified source and outcome

Signed source `5bca00274c1a3d5ef54b753794f04e1445b91cf5`, tree
`3e842263ab8b46d3bc1cb43035efb323ba3df9c6`, passes all four selected
`SoraArena.Campaign.NoticeSquare.Encounter` cases. Production gameplay,
lighting, collision, Config and content source are unchanged from the prior
night implementation; these commits add tests and stress-category selection
to the native runner. No new asset, image edit or render was made.

| Route | Inputs | Fixture elapsed at departure | Completed | Final HP | Detection |
| --- | --- | --- | --- | --- | --- |
| North alley | Keyboard and controller | 21.5 s | 49.666 s | 145/145 | After ignition; authored reinforcement wave arrives |
| Roof | Keyboard and controller | 11.5 s | 91.722 s | 145/145 | None throughout the encounter |

Both routes enter real blast cover 7,083 ms into the 20-second fuse and remain
grounded there until actual detonation advances to blackout. The alley run
observes at most 11 enemy actors; the roof run at most seven, including the
marksman's body. These are actor counts, not a claim that every actor remains
alive throughout the route.

The tests use the real seeded checkpoint and menu/input mappings, at 60 Hz.
Camera facing is supplied as the update absent from the automation world's
non-local player controller. Walking must remain supported and continuous;
both ladder flights use actual swept movement and supported endpoints.
Planting and ignition use the complete four-second and one-second holds.
Detection before ignition fails the rehearsal; after ignition the unmodified
hero must survive and escape. This is stricter than the authored mission's
general rule, which permits detection and combat before ignition too.

The successful roof approach uses the existing alley opening below Y760,
then the north street at Y1800, both ladder flights, and an east approach to
the ridge. Its return clears the split-house foundation along X−600, rather
than walking down the patrolled street at X−350 or through the house at
X−880. It continues to the terminal without another clocked wait. No wall,
foundation or other obstacle was removed to admit this path.

The final run has zero selected errors and **one selected warning**: an
editor HTTP connectivity request to `www.google.com/generate_204` timed out
after three seconds during the keyboard roof case. The case completed
successfully. The warning remains in the originals; this is not network or
release qualification. The default runner and explicit Stress selection
both execute and export their selected tests; shell syntax checks pass.

## Timing exploration and retained failures

The first four-case run, `b83bbac8`, failed all cases: the alley approach met
the drone, and the roof fixture tried crossing a real wall. At `7f097c2d`,
the fixture used the actual opening and waited for the drone, but the
marksman interrupted both routes. These failures do not prove impossibility.

An explicit Stress probe at `e57f1124` sampled departure seconds 9–78 in
three-second increments: **2/48 succeeded, 46/48 failed**. The alley successes
were at 21 and 63 seconds; every sampled roof route failed. The subsequent
half-second refinement at `2102811e` ran both input modes: **8/32 succeeded,
24/32 failed**. Alley samples 20.5, 21, 21.5 and 22 seconds succeeded on both
inputs. Samples 20 and 22.5 failed; no continuous interval is established.
The 11.5-second roof sample reached the ridge, completed the takedown and
descended both flights, but failed on its street return. Nearby 11 and 12
second approaches failed earlier, so roof timing robustness remains open.

At `e2146cf2`, both alley cases passed. Both roof cases remained undetected
but stopped at the split-house foundation, feet Y1601.6. Routing around its
east edge produced the four final passes. The original probe cases remain
explicit Stress selections; their historical failures are not relabeled.

Three failed launches also remain preserved: `4e2270db` selected no tests
because the default Unreal category omits Stress; `9217b9a9` selected no tests
because of an extra Automation prefix in the command chain; and
`e2146cf2-attempt1` stopped before launch when unrelated Iroha dotnet processes
matched an overly broad process check. The corrected observation recognizes
the Unreal engine's dotnet path. It did not stop or alter those other jobs.
None of these attempts supplies gameplay evidence.

## Evidence

Originals are in isolated SOURCE under `Saved/Qualification/2026-10-28/`.
Every completed test run authenticates 20 originals, the exact selection,
signed source and editor artifact, natural process EOF, and unchanged source,
native inputs, Config, Generated and frozen ROOT. Each failed launch has a
separate review that explicitly records zero executed cases.

| Independent review | SHA-256 |
| --- | --- |
| `notice-encounter-runtime-b83bbac8-attempt1-review.json` | `9f3ad44519b0b998546a7f478b6c73c4641759c50b07f843b9734d0d803f8179` |
| `notice-encounter-runtime-7f097c2d-attempt1-review.json` | `626f3ce1913e8ebdb09982ae9eddf78fc97e1cb5f3f2f673255f8ba74b837de7` |
| `notice-route-probe-4e2270db-attempt1-failed-launch-review.json` | `d3ae97a822f78115f687fa0301439236e6bee86d9cde1dc996eb0e47a41c30d3` |
| `notice-route-probe-9217b9a9-attempt1-failed-launch-review.json` | `c67b7e673c828e98e6f2e6c57a74b4bc2c3020b5ec4cfdc5397a0e428f42c733` |
| `notice-route-probe-e57f1124-attempt1-review.json` | `106bd906ddc6d0141adcd2867da65b3858b4932a1215869994a6af2ffc92bd0d` |
| `notice-route-margin-2102811e-attempt1-review.json` | `82f9daa8763d095911f451e4e6c8746ff78ac87fa02f039aa416de319288fedc` |
| `notice-encounter-runtime-e2146cf2-attempt1-preflight-review.json` | `beb0d88dc4bc3fb8643033d245c377cf524e7eae29279ab9d360dc7b2f28892f` |
| `notice-encounter-runtime-e2146cf2-attempt2-review.json` | `877975ae4b37a99df12fa7b3000c00affeaf8990c1a9778852648f35e8f6d8f9` |
| `notice-encounter-runtime-5bca0027-attempt1-review.json` | `099a477093331cf7d5cb652d3397ae14a13c7ad07ab2730d59ef2a7b9b8ebac2` |

ROOT remains frozen at `b6ba3c11`; the shared checkout remains `610bb975` and
the preserved package remains `1b6dfadc`. No user-game input or restart was
sent. There is no new package, render, actual-M1, Windows or performance result.
