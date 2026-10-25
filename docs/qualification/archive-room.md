# Archive room source candidate

Chapter six b09/b10 previously used a generic 36 by 26 metre room with eight
low cover boxes. The authored archive is 26 by 18 metres with a six-metre
ceiling and four keyaki posts at (9,6), (17,6), (9,12), (17,12) metres. Those
posts must obstruct blade reach inside the duel ring. The candidate replaces
the generic collision with that footprint and four full-height posts, keeps
the following zones in place, and moves the duel/pledge anchors into the room.
The wall racks occupy the authored 1.2-metre strips; a proxy family slate is
on the east rack. Runtime validation checks the room and its post contract.

Two archive host tests and the five moat tests pass. Campaign generation and
schema validation pass all 133 beats and reject the existing 65 malformed
fixtures. The climb/flood integration baseline remains unchanged. A prepared
Unreal fixture counts the four real posts and commits a mapped katana strike
through one post, followed by a clear-line damage control beside it. It freezes
opponent AI and is not a duel-balance test. The initial fixture failure and corrected runtime results are recorded below.

This is collision and placement work, not final art. Posts, racks, doors and
ceiling use proxies. The north stair connection to the press catwalk remains
unbuilt; both door faces remain on the closed room walls. Ordinary traversal,
the actual duel, save/reload, rendering and packages still need qualification.

The first engine run at `1248987` exposed a fixture error: it equipped weapon
3 (the needle gun) while labelling it a katana. Both required swing-count
assertions failed, so the post check was not accepted. The correction equips
weapon 0, asserts its identity, and waits through the real equip recovery
before mapped attack input. Its successful runtime rerun is recorded below.

The same run passed the assisted 133-beat campaign and ValAmort boss fixture,
but `Campaign.Spaces` still required the removed generic relay pedestal.
It now requires the actual floor at zero and standing capsule clearance for
that relay site, while preserving the raised-base check for ordinary sites.
All 20 evidence files rehashed; editor/wrapper exited naturally with 3/1;
source, native, config and generated inputs were unchanged. Failed-run review:
`e6858f5a78f3d24e6acf9b922f939c011d6894e37706b5fafc3cd08d523e28a4`.
The next run includes ToranosukeSteel, the boss specific to this archive.

The corrected `e638cd6` builds in 21.62 seconds and passes ArchivePosts,
Campaign.Spaces and Boss.ToranosukeSteel. The katana commits both swings:
the real post prevents damage, while the same target is damaged beside it.
The boss fixture separately verifies its phase behavior and sheathed mutō-dori
finish; it is not an ordinary duel played in the archive. Editor/wrapper exit
naturally at 0/0, all twenty evidence files rehash and guarded inputs remain
unchanged. Review:
`7469d1d4798f839b47cc4f527f6eb4683837f020e0417b79c9b1901bfbe4caa8`.
Source CI at `1248987` passes all 110 checks; the later two fixture-only commits
are not covered by that run. Review:
`990d2e768b4cf027d64edb385e079254d32011e26c4efcaa2eb7600739950204`.

A subsequent source candidate links the physical family slate's cyan light to
the duel's existing second phase and the pledge. The page begins dark, lights
when the actual phase changes, and derives the same state from a loaded phase
checkpoint. It adds no new save fields. A prepared ArchiveFamilyPage fixture
uses directed story damage, checks the real light and blocking dialogue,
reloads the actual mid-duel save, and checks the pledge. It has not compiled
or run. This does not implement the authored rack impact, character animation,
readable slate artwork or the final cinematic camera.

Source review also found that the family-page phase was saved immediately,
allowing a quit during its blocking exchange to restore after the reveal.
The candidate now leaves the earlier checkpoint in place while dialogue holds
combat and saves the second phase once control returns. The prepared fixture
checks disk state before and after that boundary, then reloads the resulting
save. This timing correction still awaits engine execution.

The phase transition also queued the remembered radio lesson before the
family exchange. The archive now queues the blocking reveal first, followed
by the phase-two lesson; other encounters retain their order. The fixture
checks both subtitle identities. The assisted campaign waits for that real
blocking exchange before expecting its phase save. This remains dialogue
staging; the authored twenty-second cinematic and rack impact are not finished.

The pending save requires the final family-page line to have actually
finished, including when a prior nonblocking combat bark precedes the reveal.
The prepared fixture covers both queue states. The campaign regression lets
the real queued lines finish before checking the new save; it does not clear
or skip dialogue.

These candidates now pass engine execution at signed `6eb0df6`. All six
selected fixtures pass: ArchiveFamilyPage, ArchivePosts, Spaces,
ToranosukeSteel, CombatAndPlaque and the assisted 133-beat Playthrough.
Both reveal queue states retain the phase-one disk checkpoint until the
final family line finishes, then save phase two; a fresh world loads the
actual save with the physical slate lit. The family exchange precedes the
remembered lesson. The assisted campaign finishes in 69.32 seconds of test
execution; this does not claim ordinary play duration or difficulty.
Natural editor/wrapper exits are 0/0, all twenty evidence files rehash,
and source, native, config and generated inputs remain unchanged. Review:
`5b64a75daf3a80b63aa88cc75f2d192791dabac77b82b57cb1b4cde4359a320d`.

The first `f3de9c2` attempt failed before editor launch: Unity grouping
exposed a missing direct `SoraCatalog.h` include in the older copying test
helper. No runtime tests ran. Its fourteen preserved files and unchanged
inputs verify, review
`2667b337bfebe5d3f1ffe3215fd980bdfe36a9932865ea11983bbd341470e546`.
The sole correction in `6eb0df6` adds that include. Source CI at `f3de9c2`
independently passes all 110 checks in run `40235477188`, review
`42268d2688b863f5c15922eff30758d655e8ca778a8b7e64990324b3bf609755`.
The authored cinematic, rack impact, slate artwork and north stair remain
unfinished.

The next source candidate raises the archive floor to six metres, places
ten 20 cm steps outside its north door, and connects their four-metre landing
to the press hall's NW catwalk across the current layout's gap. The wall
openings, steps, landings and guard rails have real collision. The door stays
locked during the duel; the pledge now requires its dialogue and arrival at
the press landing. Ordinary arrival keeps the actual capsule position;
checkpoint entry still restores the supported catwalk start.

The long connector and six-metre placement are provisional architecture
chosen to connect the existing separated zones without moving later areas.
The south entry still uses the existing travel cut. Three archive host
checks and the 133-beat/65-malformed-fixture validator pass. The prepared
ArchiveExit fixture uses forward input through the door and ten treads,
checks pause and a blocking obstacle, and verifies the press checkpoint and
continuous position at arrival. None of this new geometry or movement has
compiled or run in Unreal yet.


## Guarded exit runtime result, October 26

The source candidate above is now exercised. `dc32d81` passes ArchiveExit:
ordinary mapped movement traverses the unlocked north door, all ten descending
treads and the connector. Pause holds the stair position; a real obstacle stops
passage; removing it restores passage. Ordinary jump input against both
180 cm bridge screens cannot escape into the unbuilt gap. Pledge completion
waits for physical arrival, saves beat 11 on disk and retains a grounded capsule
on the four-metre catwalk without a teleport (largest frame step 13.289 cm).
The fixture freezes press guards only after arrival to isolate traversal.

That batch passes thirteen of fifteen checks. Its two failures are preserved:
Spaces still probes the archive zone entry at zero, and the assisted campaign
places its dialogue closing anchor at zero. `fa9f5a6` corrects those fixture
heights, then passes ArchiveExit, Spaces and the complete assisted 133-beat
campaign together. No production code changed between these two batches.
Natural editor/wrapper exits are 0/0; all twenty evidence files and unchanged
source/native/Config/Generated inputs verify. Passing review:
`73e8cf05f9fe49f0d447d017f613f456467e02bf2ad0d441cbe4d2d8509619ab`.
Initial failed-run review:
`4102c4fc3205a2e77af7aef02e497666a043a75e9c461951062e8509dedfc5e8`.

Source CI at `17fe866` fails the stale timber campaign hash and an older lift
fixture's zero-height assumption. Both are corrected in `dc32d81`; the four lift
and three archive host tests, plus the binding check, pass locally. The failed
CI artifacts remain authenticated under run `40237210108` (108 passes).

This accepts the directed physical route, not the provisional long connector's
visual design, the closed south entry's travel cut, the authored twenty-second
rack-impact cinematic, ordinary duel balance, packaged play or final art.

## Family-page cinematic source candidate

The next source candidate stages the authored twenty-second reveal when the
actual duel crosses 50 percent health. A preceding combat bark finishes first.
The scene cuts to clear marks in the east aisle, moves Toranosuke into the east
rack, shakes that physical rack and lights the family slate at 1.4 seconds.
A wide impact shot, slow slate view and final reaction lead back to the duel
ring and the player's camera. These are procedural character transforms;
final strike/recoil animation, readable slate artwork, sound and rendered
camera composition remain unfinished.

The actual four subtitle durations total 15.4 seconds, leaving a 4.6-second
visual prologue in the twenty-second sequence. A host contract now checks
that sum against the generated dialogue. The scene uses active time, so pause
freezes movement, camera and speech; held actions remain blocked. The phase
checkpoint stays at phase one until all speech and the scene finish. Reset
cancels the scene and camera ownership, while a saved phase-two reload does
not replay it.

ArchiveFamilyPage now checks both preceding-bark cases, actual camera ownership,
physical rack response, pause, held movement/fire, the twenty-second duration,
late pre-completion save state and completed reload. ArchiveRevealReset adds
mid-scene checkpoint reset coverage. The assisted campaign permits a silent
visual prologue only while that named scene is active. These fixtures have
not yet compiled or run; Claude still owns the engine/Blender lane.
