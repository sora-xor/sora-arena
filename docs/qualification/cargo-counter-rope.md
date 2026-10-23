# Cargo counter and lead presentation checkpoint

The chapter-04 specification explicitly calls for a cargo counter
`30 → 20 → 10 → 0` (§9.8, line 1235) and a 3 m lead between Kurimaru and Bunta
(b14, line 476; §6.4, lines 656–660). This change adds those functional displays
on top of the cargo quantity/transfer checkpoint `d8ae065`.

The existing bilingual objective row shows remaining barley sheaves and the
number of destinations served. It uses `SoraCargoRules::Remaining` with the
existing accepted delivery count; there is no additional inventory or counter
state. Other delivery tasks keep their existing text and behavior.

The final accepted unload immediately advances into b15's cinematic, before the
ordinary objective row can render zero. The existing b14 registry completion
notice therefore also includes the derived remaining count in its heading.
Registry notices already preserve their seven visible seconds through a
cinematic and pause menu. This uses that existing feedback path without delaying
progression, changing the registry tally, or adding another completion gate.
The fixture checks the zero notice before, during and after a normal cinematic
skip. Headless assertions do not establish that a player actually saw the
rendered counter or notice; that still requires a HUD capture.

`USoraLeadRopeComponent` is owned by the led horse and ticks in
`TG_PostUpdateWork`, after ordinary actor movement and head/body animation. It
does not change either horse's gameplay tick group or prerequisites. Twelve
short existing cylinder meshes form a sampled slack curve. The curve uses the
authored 300 cm nominal length when the endpoints are close enough; if existing
following or whistle relocation separates them farther, it displays a taut
connection. It exerts no force and does not constrain horse positions.

The endpoints are named `LeadHalter`, attached to Bunta's animated head beside
the muzzle, and `LeadTie`, beside Kurimaru's rear saddle arch. Their transforms
come from the existing proxy tack and head geometry. These are provisional
attachment choices: the specification does not define a socket, knot or exact
handoff pose. The simple halter, rope material, slack shape and attachments
remain WIP art for Claude and equine review. This is not a claim of historical,
physical, animation or photoreal accuracy.

The rope has no collision, overlap, navigation contribution or simulation
forces. It reads the current attachment transforms and does not mutate fear,
steering, gaits, damage, unloading, stock or failure state. Dismount and spook
retain the existing horse-to-horse relation. Detaching the lead, switching to
road following, losing an endpoint, retrying or leaving the beat removes its
mesh components. On-foot unloading remains valid with the horses left behind.

## Validation scope

The host campaign rule driver checks the bounded curve, exact endpoints,
nominal length under slack, taut separation and invalid inputs. The existing
cargo quantity, carry, fieldcraft, stealth, generated-data and content checks
remain part of the source qualification; registry data validation is also run.

The Unreal fixtures are extended, but execution belongs to the root integration
process. `CargoUnload` checks both language strings through accepted and refused
work, the retained zero completion notice, and lead teardown. The existing
`BuntaLeadFear` and `KurimaruSpookDismount` fixtures inspect the actual rendered
segment endpoints against named animated anchors on every sampled tick. This
covers their 60/120 Hz motion, steering, fear, pause, ordinary dismount/remount,
whistle, both horse/director tick orders and checkpoint retry. A small explicit
lifecycle-API check also detaches and reconnects the lead, then switches to road
following and checks cleanup.

No Unreal build, render or runtime test was run in the author worktree. No HUD
layout or style redesign, new gameplay gate, return-to-granary requirement,
package qualification, M1/Windows result or performance result is included.
Earlier `d8ae065` evidence remains unchanged.
