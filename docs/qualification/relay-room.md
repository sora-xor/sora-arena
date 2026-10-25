# Relay room source candidate

This is a work-in-progress implementation of chapter 6 L3 / beat 4.
The integrated source at `1479a6e` first failed to compile because its
FJsonObject forward declaration used struct instead of Unreal's class.
That one-line error is fixed by signed `ae5bee6`; the failed build and
natural wrapper exit are retained. Review SHA-256:
`527b97fa2e60fd0d6ebd78de47ea2bbe6a9a8c2a9434517354402177c4600aed`.

The exact `ae5bee6` editor build succeeded in 16.20 seconds. Seventeen of
20 NullRHI fixtures passed: all eleven press tests, CopyDesks, Candle, and
RelayControls, RelayScan, RelayExit and RelayLookout. The failures were
Playthrough, RelayGallery and RelayInspection. Source, native, generated
content and configuration stayed unchanged; editor 3/wrapper 1 reached
natural EOF. All 20 evidence files were rehashed; review SHA-256:
`bbd590796506fb3d99fd924d5eb1fa7d262b7f36df1717e287abc4b50c182ddd`.

The `2ddd15d` follow-up passes the gallery route, including ordinary ascent,
upper-node work and descent. Its earlier failure checked floor height before
the descending capsule finished landing; it now waits for natural grounding.
The inspector still stalls at local feet (395.627,861.723,327.855), near the
top of the stair. A navigation query to the upper control returns a path
back down to floor level, not a usable gallery connection. The ordinary
player traversal establishes that the physical stair is usable.
The assisted campaign's relay exit advances to the next beat, where its
test incorrectly demands a new hold from the reset objective count.
These two failures are retained, with natural editor 3/wrapper 1; review:
`c3792459cc9f2da348ac55755c69ea1f27b8c3e966065895176cb5e8a5d4bf45`.

The next candidate follows only the inspector's authored stair/gallery legs
with normal character movement and a support check at each next step. The
walking capsule still handles collision and step-up; actual arrival is
required, and a blocking wall cannot count as inspection. Ground approaches
keep navigation. The fixture also checks the return down to the floor post.
The campaign test now decides whether to expect a hold from the objective
before pressing, so completing the exit is accepted. These latest changes
are not yet compiled or run. Claude owns the engine lane for two controlled
art captures while root prepares the source fix.

The previous room credited three generic held points. This candidate binds
the portable relay reducer to mapped Interact input, grounded floor height,
ordinary interaction reach and a visibility trace to each real control.
One director clock advances the scan and node holds. Each node has an
eight-second exposure and four-second gap per twelve-second revolution.
A three-second pull finishing exactly at the gap boundary succeeds; an
incomplete pull is caught. Releasing, leaving or becoming obstructed cancels
work, and keeping the key held cannot restart it.

A catch adds 0.6 suspicion to the nearest living guard and freezes the fan's
actual heading for two seconds. Detection locks the nodes for thirty seconds
and releases two enforcers at the east entrance after eight seconds. The
sensor event's position inside a coarse frame is retained when starting
those deadlines. Easy retains the campaign's existing combat-only detection
response. Beat restart clears all relay state.

The source places the authored 20 by 10 metre room, column, gallery at four
metres, ordinary colliding stair treads, a north-node maintenance approach,
railings, eight posts, four chests and three bell stacks. Noisy clapper floor
patches have visible loose clappers. The two work lamps retain their authored
positions and five-second guard notice. A living calm auditor is assigned
physical waypoints to disabled controls; the upper route climbs the stair
and returns along it. Only actual arrival counts as inspection. A blocked
path remains pending and stronger perception interrupts the errand.

The ground enforcer is scheduled on a fifty-second circuit; the gallery
enforcer alternates a gallery circuit with a stair excursion, each forty
seconds; the drone is scheduled at five metres on a thirty-second orbit.
The existing patrol scheduler retains missed deadlines and cannot advance
through an obstructed station. Actual navigation and cadence remain untested.

After all nodes and the floor-level east exit are completed, saved chapter
progress limits drone callouts to twenty metres and fixes moat searchlight
headings on later visits. This checkpoint-derived behavior has not yet been
exercised in Unreal. The assisted full playthrough now explicitly places
the hero on the upper control's floor and waits for a real safe scan window;
it is not an ordinary-input playthrough. At integration, the fixture also
clears attacking guards through its existing assisted combat path and waits
for net effects to expire before the held work, as the press follow-up does.
Relay holds use actual mapped Interact and 60 Hz ticks. The timed scan, reach
and grounding requirements remain active.

Host validation performed during implementation:

- Generated campaign data is current; all 133 beats and 65 rejection fixtures pass.
- Eight relay-contract tests and ten existing press-contract tests pass.
- Fieldcraft, press and relay C++ host drivers pass with undefined-behavior
  traps. Relay coverage includes all 36,000 node/start phases, completion
  versus catch boundaries, input cancellation, frozen scan, frame partitions
  and delayed detection delivered after a coarse tick.
- The source-check runner's fifteen tests pass. CI now includes the new relay
  data contract, increasing its inventory from 108 to 109 checks.

Source CI run `40224399111` for `6bf19b4` passed 108 of 109 checks. Its one
failure was `dojo-timber-binding-current`: the chapter-six data edit left
that binding's chapter hash stale. The binding has now been regenerated;
only that hash changed, and `--check` passes. No timber geometry or coverage
changed. The subsequent exact-source run `40225482561` for `e0ef5e9` passed all
109 checks. Its archived review is
`9a8636083ac6d333047a4617df228c25d5e973e0ef2ad67a04244e8bf7ab502d`.

Prepared Unreal fixtures: `RelayControls`, `RelayScan`, `RelayGallery`,
`RelayInspection`, `RelayExit` and `RelayLookout`, under `SoraArena.Campaign`. They isolate
control mapping, obstruction, height, scan penalties, delayed reinforcement,
stair movement, auditor arrival, completion and checkpoint reset. Most freeze
guard AI or use an inspector with isolated senses; they do not establish
ordinary encounter difficulty. Their assertions are prospective until run.

The shell now has a physical west crawl aperture, east doorway and upper
north slatted window at the authored 5.5 metre height. Kohagi is staged on a
solid outside perch facing into that window, with her existing undetectable,
noncombat role. The generated contract rejects changing her role or returning
her to the generic entry position. Her current standing animation is a
placeholder for the authored prone lookout pose. These changes are unrun.

Known unfinished work: the room remains primitive blockout geometry, the
turret/annex materials and openings are not authored final art, Kohagi's prone
animation is missing, and there is no rendered, ordinary-play, Mac/Windows package or performance
qualification. Lamp notices, alternating patrol cadence, restored-checkpoint
effects and the complete encounter still need dedicated runtime evidence.
