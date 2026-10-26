# Ward gate: source implementation, 26 October 2026

This checkpoint implements the chapter-three ward gate's functional layout and
interaction. It is **not Unreal-qualified**: its engine code and seven new runtime
fixtures have not been compiled or run. The previous packaged game is unchanged.
Final art, ordinary stealth play, platform performance and release acceptance are
still open. Claude retains the exclusive engine/Blender lane for the r3 character
rebuild while this work uses host checks only.

## Behavior

The generated `ch03.b03` layout now binds the authored 18 × 14 m plaza, 2.4 m fence,
shut gate, hut, shop roof, firewall, ladder, straw, below-ground culvert and wicket.
The construction tables used by the world builder are also compiled for host
geometry checks. These are functional solids, not finished environment art.

The scanner checks swept player-capsule bounds so touching it raises the existing
stealth alarm even when no guard sees the player. The shut gate stops the capsule
centre before it reaches the sheet, so centre-only detection would miss contact.
The low wicket lies outside the scanner. Menu pause suspends evaluation; leaving
and returning can alert searching guards again without duplicating the zone's
first detection notification.

Only freeing the assigned kido-ban swings the wicket clear, keeps the open leaf's
collision, and raises `npc_freed:kidoban`. Freeing another conscript does not open
it. The existing forced nonlethal knockdown, eight-second recovery and 1.5-second
seal-cut interaction remain in use. Clearing the beat discards the assignment,
open state and previous scanner contact.

## Physical resolutions of authored conflicts

- The landing exit and gate approach share X −8000..−7600, Y −1000..−660 cm. The
  landing alone owns this ground. Its north/east boundary walls stop at the open
  connection; the ward's south wall begins east of it. Only this exact chapter,
  zone pair, bounds and contract may pass the general zone-separation check.
- The hut obstructs the proposed straight ditch patrol and western culvert
  approach. The patrol detours south of it; the culvert descent bends around its
  southeast corner on three 30 cm steps. The prose's three-metre culvert governs
  the provisional two-metre source volume. The tunnel remains 100 cm wide and
  90 cm high, with its floor at −90 cm.
- The perimeter patrol avoids the hut and brazier guard. Its south return is
  moved 100 cm north so its body cannot overlap the ditch patrol. Both retain
  their authored 40/50-second circuits. Actual arrival, not elapsed time, advances
  the existing patrol scheduler.
- The brazier guard stands beside the brazier body and the arch guard stands
  clear of its frame. C1 retains the twelve-second turning duty and all three
  conscripts retain 0.7× suspicion. The eave lamp remains snuffable; the brazier
  and scanner are permanent.

## Validation and remaining work

Targeted host checks pass: eight ward tests, eight landing tests, fifteen source
runner tests and the campaign validator, including its 65 rejected bad variants.
The ward native driver checks scanner direction/contact/alternate-route heights,
patrol deadlines, and blocked-arrival behavior. Python tests use its compiled
solids to check guard-body clearance, separated routes, entrance support, culvert
steps and headroom, the wicket opening, and contract mutations.

The new Unreal fixtures are `SoraArena.Campaign.WardGate.Solids`, `.Scanner`,
`.Wicket`, `.Patrols`, and `.Routes.Culvert`, `.Roof`, `.Wicket`. They exercise
real collision, mapped traversal and interaction, live patrol timing, menu pause
and checkpoint reset. Directed route fixtures hold enemy AI; the wicket fixture
supplies a nonlethal hit through the damage interface. They do not establish
ordinary stealth difficulty or visual quality.

The first runtime concern is the 90 cm tunnel: the crouched capsule is 88 cm tall,
and Unreal's floor-hover allowance may consume its remaining clearance. Do not
claim this route works until the mapped-input fixture traverses it. The landing
suite, brazier test and campaign playthrough must also rerun after the changed
connection and gate geometry. No runtime result is implied by the host passes.
