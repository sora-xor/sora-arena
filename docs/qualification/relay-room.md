# Relay room source candidate

This is a work-in-progress implementation of chapter 6 L3 / beat 4. The
runtime changes and six Unreal fixtures have **not been compiled or run**.
The separate complete-game worktree stays frozen at `c3fcf8e` for the queued
press regression. Claude owns the Unreal and Blender lane during the art
rebuild. This candidate does not qualify gameplay, art or a release.

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
it is not an ordinary-input playthrough.

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
changed. A subsequent CI run must verify this correction.

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
