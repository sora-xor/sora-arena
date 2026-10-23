# Chapter six corner climb

This slice implements the player traversal and parapet sentry in chapter-06
§L2 and b03. The typed `space.beats[].climb_routes` record exists only on b03.
It defines a 16 m wall, fourteen corner holds, eight exposed extrusion holds,
rests at 5.5 and 11 m, a twenty-second/four-second sentry cycle, and a 60 cm
crawl gap at floor height 16.5 m. The original generic climb metadata remains
readable, but this beat uses the dedicated physical layout and route runtime.

Mapped Jump at the actual grounded foot starts either route. Forward and
backward move a swept capsule between holds; releasing pauses at the current
physical position. Both directions go around each solid shelf's outside lip.
The final mount can be reversed and resumed. Grip still starts at 100, costs
6 per reached hold and recovers 25 per second at a stationary rest. Resting
frees the hands for ordinary shooting. Taking a new hold, starting the route
or entering the crawl cancels held equipment actions without releasing a shot.
Letting go uses gravity and actual landing height: a drop over 4 m costs
30 HP and over 8 m is lethal. Landing on a lower shelf counts only that drop.

The sentry physically travels the connected parapet and projecting bay.
The twenty-second clock pauses with play; each four-second watch begins only
at the bay. A visible 60-degree cone sweeps continuously across the upper
corner and extrusion. Perception uses three-dimensional direction/distance
and the existing three collision visibility traces, light and suspicion
rules. The sentry's scoped rifle uses 12 damage, 200 ms nominal windup and
1,000 ms recovery; ordinary difficulty windup scaling still applies. The
extrusion's alien cyan strip has real lights. No synthetic detection event
credits the route or ignores facing and occlusion.

Reaching the parapet alone does not complete b03. The player walks up the
approach and uses the currently mapped Crouch at the aperture. A local stance
uses a 28 cm radius and half-height (56 cm total), including when the player
arrives already normally crouched. Ordinary movement at 90 cm/s physically
crosses the 60 cm opening. Toggling crouch off inside cannot grow the capsule
into the lintel; standing resumes only with clear headroom outside. The normal
34/88 cm capsule and 44 cm crouch configuration return on completion, retry,
fresh checkpoint load or beat teardown. Teardown inside the stone may move
the hero to the safe route entry before restoring the capsule; normal gap
traversal never uses that reset relocation. The top event and exit gate require
actual entry and emergence from the gap.

The script does not specify these implementation choices; they are provisional:

- Exact hold coordinates, collision dimensions beyond authored heights, the
  straight 60/80-degree two-course shell, bay projection and aperture approach.
  Route points are feet positions. The two holds immediately below rest shelves
  sit 210 cm outside the following rest centre, clearing the 130 cm shelf lip.
  Approaching either of those holds moves outward before rising so the
  capsule's upper hemisphere also clears the shelf underside; descending
  lowers first before moving inward. The source gate samples the production
  interpolation in both directions against both physical shelf envelopes.
  Shelf and parapet crossings lift the feet 6 cm above the support, cross,
  then settle at the unchanged authored endpoint height. Descending a shelf
  lifts first and crosses outward before lowering. Input reversal follows
  the same continuous path. This clearance avoids the observed time-zero
  side-face hits when a rounded capsule crossed exactly at the top plane.
- Player sweep completion admits ordinary support separation only for a
  non-penetrating flat upward contact (capsule and face impact normal Z both
  at least 0.99), no more than 0.25 cm lateral error and 0–3 cm feet above the requested point. Side,
  underside, penetrating or more distant hits still stop the step.
- Each hold move and final mount lasts 1.8 seconds. The same cadence makes the
  eight-hold route faster. These numbers do not accept the three-minute beat
  target or ordinary encounter pacing.
- The full 30 m parapet plus approach/bay circuit uses about 3.79 m/s during
  the initial twenty seconds and 4.7375 m/s during subsequent sixteen-second
  patrol windows, with a 7 m/s catch-up cap after interruptions. This resolves
  the full out-and-back circuit within the authored watch cadence. It is not
  the old general-purpose walking speed or final locomotion animation.
- The local crawl stance, speed, camera position and collision shell are
  implementation choices for the authored 60 cm opening, scoped to this beat.

The host gate validates typed data, authored dimensions/timing, malformed and
shortcut variants, unchanged generated chapters/flood data, actual C++ grip,
fall and rest rules, watch boundaries and the connected patrol trajectory.
It is registered as gameplay `climb-routes`.

Seven engine fixtures are supplied: `SoraArena.Campaign.ClimbLoader`,
`ClimbCorner`, `ClimbExtrusion`, `ClimbSentry`, `ClimbPauseRetryReload`,
`ClimbHands`, and `ClimbFalls` (all with the same campaign prefix). They cover
both actual routes, support traces, backward shelf departure, mount reversal,
keyboard remapping, gamepad crouch, blocked standing entry, already-crouched
entry, held equipment cancellation and legitimate resting fire, real sentry
travel/visibility/damage, pause, death/retry and a fresh world. Traversal and
sentry fixtures keep the sentry alive and use extra hero health to separate
movement from encounter balance. Hands and fall fixtures freeze threats to
isolate those mechanisms. The existing `SoraArena.Fieldcraft.Climb` keeps the
30 HP lower-drop regression. Aggregate playthrough now uses the same real
climb and crawl helper; space checks use the dedicated support elevations.

This is a source checkpoint. No Unreal compilation or runtime pass, art
approval, render, package, platform or performance result is claimed here.
Root owns those execution gates. In particular, contact at exact support
heights and runtime sentry visibility require the supplied engine replay.
Final masonry, unique stones, character climb/crawl animation, bow-stringing
animation and ordinary-control pacing remain unaccepted.

The separate guide follow-up replaces generic following for b03 Kohagi only.
She starts at the actual corner foot, climbs its fourteen physical points
(including both shelf approaches), mounts the parapet, climbs the outside
turret face and waits on a colliding roof at 24 m. Every move sweeps her
ordinary capsule; blockers stop progress. The final roof state uses ordinary
walking support and never grants the player's crawl completion. Her authored
nondetectability remains unchanged. The 140 cm/s demonstration pace, outside
roof approach and exact roof slab bounds are provisional implementation
geometry. A waypoint accepts at most 3 cm of actual proximity to accommodate
normal floor-contact separation, without ignoring or disabling collision.
Her shelf, parapet and roof crossings use the same 6 cm foot clearance;
even the existing 3 cm waypoint radius leaves positive crossing clearance.
The final roof waypoint settles vertically to 24 m and requires an actual
upward-facing support hit before waiting begins. Its speed-limited downward
sweep aims 6 cm beyond the support plane; the collision must stop it within
the unchanged 0–3 cm above-plane bound. A missing roof cannot grant waiting.
Pause freezes the active movement; retry/fresh load restarts it, and leaving
the beat clears the owned route and actor. `SoraArena.Campaign.ClimbGuide`
observes all fourteen holds, bounded movement, active pause, real roof
support/waiting, nondetectability, death retry, fresh load and player-triggered
beat teardown. This follow-up still requires Unreal execution.
