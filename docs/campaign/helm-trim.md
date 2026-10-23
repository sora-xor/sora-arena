# Chapter seven helm trim implementation

The authored contract is chapter-07 §2.3 and b14: 60 seconds of uncontested
holding, trim alarms at 25/50/75 percent, a two-second wheel correction,
eight-second grace, 0.02 of the whole hold lost per second when ignored, and
an overall deadline of 200/150/130 seconds on Easy/Normal/Hard.

The generated `space.helm` contains typed integer timings, thresholds and
positions. Its six-by-sixteen-metre floor and the wheel/beacon offsets match
the authored lowest bridge tier. This patch places that floor inside the
existing bridge hall; it does not claim the final tiered amphitheatre,
five-degree ship list, unconscious Collatera staging, exterior evacuation
vista, final wheel art or ordinary-control encounter balance.

`SoraHelmRules` and `SoraCampaignHelm` replace the generic hold progression for
this beat. The player must walk to the colliding wheel, stand on its floor,
have an unobstructed reach trace, and hold the current mapped Interact key.
Releasing, leaving reach, jumping or taking a hit resets partial correction.
The heading needle moves back to centre during the hold. Existing authored
`trim_event` dialogue fires at each alarm; bilingual notices identify the
current input binding, and the objective tracks remaining time and grace.

The visible hold boundary and its progress fill now use that same rectangular
volume; the generic circular hold ring and posts are omitted for this beat.
Its fill grows across the rectangle, with its edges kept inside the hold.

Helm correction reserves both hands through the campaign's ordinary weapon
permission path. With a melee arm selected, the player first uses the mapped
Sheathe action and waits for its existing 700 ms stow to finish. Interact gives
the current binding when the blade is still out. A ranged weapon is put aside
on taking the wheel: an existing held trigger or bow draw stops without a shot
or an ammunition change. An active strike, reload, step or stagger must finish
before work can begin. During correction, firing, melee, guarding, reloading,
drawing and changing weapons are refused. Release, damage, leaving reach,
completion and failure restore the selected weapon's visibility and permission;
a sheathed blade remains sheathed. The final authored helm grip animation is
still outstanding; hiding the stowed weapon does not claim that animation.

The following choices resolve details the script does not specify:

- Ordinary holding continues during the grace period. Once grace expires,
  decay replaces progress gain until the wheel is corrected; fighting in the
  hold does not stop this overdue decay.
- Each threshold fires once per attempt. Losing progress and regaining it
  does not rearm an old threshold. All three corrections are necessary for
  completion; a late correction remains possible.
- A correction must finish within the grace period to avoid any decay.
  Reaching the wheel alone does not suspend the clock. Deadline expiry wins
  if it coincides with completion.
- The timer and partial correction stop with the paused game. Beat state is
  temporary: deadline failure, death retry and fresh checkpoint load restart
  the hold, all trim thresholds and the difficulty deadline. Partial work
  does not create an additional save or alter the save schema.

The dedicated CPU gate covers exact frame-partition invariance, grace,
decay, interruption, contest, all three corrections and difficulty deadlines;
it also validates authored data and clear wheel/beacon placement. It is part
of the gameplay source group. Three engine fixtures are supplied as
`SoraArena.Campaign.HelmTrim`, `SoraArena.Campaign.HelmDeadline` and
`SoraArena.Campaign.HelmHandsAndFloor`, with
ordinary walking/held keyboard and gamepad input, obstruction and airborne
refusals, remapping, pause, checkpoint bytes, fresh-world reload and retry.
The hands/floor fixture checks the production component bounds, both sides of
the previous circle/rectangle mismatch, actual mapped sheathing, weapon-action
refusals with a blade/bow/partially spent firearm, damage and release restoration,
and an ordinary reload that must finish before wheel admission.
Their opponents are deliberately isolated to test the mechanism. Aggregate
campaign traversal now works the actual wheel rather than crediting the hold
without corrections.

At this source checkpoint no Unreal compilation, engine fixture run, render,
package, platform performance or human pacing result is claimed. Root owns
those execution gates. The original implementation's first CPU/source run
preserved 50 passes and two font-dependent failures caused by an
unmaterialized tracked LFS font; after materializing it, all 52 source gates
passed. The hands/floor correction's first source run preserved 51 passes
and one localization refusal; its hands notice now reuses the existing
localized wheel notice. Source reports and their hashes accompany the
handoff; none establishes an Unreal compilation or runtime result.
