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

At `63651ce`, 22 of 23 selected fixtures pass, including the assisted full
campaign, all press fixtures, the lamp's delayed notice, and a fresh-world
reload of the actual completed relay save. The inspector reaches the blocked
upper approach, waits, and inspects after removal; only its return fails.
The failed run has natural editor 3/wrapper 1 and unchanged inputs; review:
`bd3194d91101a6aa83750f3d1bec25a2d4f81bf1790736bc3f712a1dd58c1327`.

The return trace at `c8a749e` locates it at feet (118.656,800.207,49.324),
still supported by a stair tread behind the rounded capsule. A point ray
ahead missed that support and rejected the descent. `2a791a4` falls back to
CharacterMovement's bounded capsule floor query. The complete inspection,
player gallery route, press catwalk patrol, general patrol and horse withdrawal
all pass with natural exits zero. Review:
`6ebfd6753280b02ecdfe9793c2d8a199a2f482c03cd212cd601b2f65e57de476`.
An intermediate diagnostic build at `947ce49` failed due to a controller
variable outside its scope; no tests ran. That build is retained separately.

The actual staged patrol fixture at `f7fd0fd` finds two further defects:
the gallery guard stalls when starting its alternate stair circuit, and the
drone catches on the north control approach. The floor guard completes its
50-second circuit. The failed fixture is retained with review:
`4c1f67c3b6e6fdf2573e7b5aab1dae1e5ee5c8739d7de0644e27e3e1f56cf6d6`.

At `c3bb27a`, the gallery patrol follows its supported stair segments using
ordinary capsule movement. The drone follows a 1.2 m orbit around the column
at the unchanged z=5 m; the unused front 60 cm of the maintenance approach
and corresponding side rails are removed to leave flight clearance. The
player's existing grounded work position remains supported and reachable.
The flight follows short authored segments, preserving swept collision and
actual arrival instead of free-flight sidestep steering.

All ten selected fixtures pass: relay patrol cadence and blockage, gallery,
inspection and controls; press cadence, blockage and catwalk; general patrol;
and horse withdrawal. The ground/gallery/drone periods are exactly
50,000/40,000/30,000 active milliseconds, with no missed deadlines. The gallery
stays at feet z=402 cm on the first lap, and reaches 46.838 cm before returning
upstairs on the alternate lap. A physical barrier prevents the drone gaining
any visit or circuit for 35 seconds; removal allows its next visit while
retaining the missed-deadline flag. Menu pause preserves patrol time. Inputs
and all 20 evidence files verify, with natural editor/wrapper exits zero.
The hero is held outside detection range: this is movement qualification,
not ordinary stealth difficulty. The eight host relay-contract tests also pass.
Review SHA-256: `1e40192590b01403645c4c87f4e08c9a158b7b01fd9286ce87ce9566f48a655a`.

The next source correction separates chapter-six drone radio marks from the
ordinary eighteen-metre acoustic callout. While the relay is online, a mark
reaches allies in the current world; after sabotage its direct recipients are
limited to twenty metres, inclusive, independent of hearing or walls. It carries
the last observed location. New fixtures exercise the online path and the
offline path after an actual completion save is loaded. The assisted full
campaign also checks frozen, non-retargeting moat lights at its later exfiltration
checkpoint. Source review found that b14 staged only three hand lamps and
omitted both moat towers. The candidate restores the same two towers in the
escape coordinate frame, expands its north bound to include their mounts,
and adds proxy foundations/housings. Tower identities select the relay freeze
and their original opposing phases; hand lamps remain independent. Frozen
spots keep their horizontal positions while the water surface rises. The
loader rejects missing or altered towers. Four flood host tests, the campaign
schema and 65 malformed-schema probes pass. These new Unreal tests are not
compiled or run yet; the b4ac007 checkpoint's initial two-light expectation was
incorrect and was corrected before execution.

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
through an obstructed station. These routes now have the directed runtime evidence above.

After all nodes and the floor-level east exit are completed, saved chapter
progress limits drone callouts to twenty metres and fixes moat searchlight
headings on later visits. The actual completion save reloads with the offline flag; the resulting
drone communication and moat lighting effects still need runtime checks. The assisted full playthrough now explicitly places
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

Implemented Unreal fixtures: `RelayControls`, `RelayScan`, `RelayGallery`,
`RelayInspection`, `RelayExit` and `RelayLookout`, under `SoraArena.Campaign`. They isolate
control mapping, obstruction, height, scan penalties, delayed reinforcement,
stair movement, auditor arrival, completion and checkpoint reset. Most freeze
guard AI or use an inspector with isolated senses; they do not establish
ordinary encounter difficulty. Their current runtime results are recorded above.

The shell now has a physical west crawl aperture, east doorway and upper
north slatted window at the authored 5.5 metre height. Kohagi is staged on a
solid outside perch facing into that window, with her existing undetectable,
noncombat role. The generated contract rejects changing her role or returning
her to the generic entry position. Her current standing animation is a
placeholder for the authored prone lookout pose. The opening, support, facing and noncombat-role assertions pass; the pose remains unfinished.

Known unfinished work: the room remains primitive blockout geometry, the
turret/annex materials and openings are not authored final art, Kohagi's prone
animation is missing, and there is no rendered, ordinary-play, Mac/Windows package or performance
qualification. Restored-checkpoint communication/lighting effects and the
complete ordinary encounter still need dedicated runtime evidence.
