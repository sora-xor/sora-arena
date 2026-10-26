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

The complete selected host groups also pass at signed source commit
`3f115e5155bd152bc92411d094b6c6e8a2e79776` (tree
`14f2b9920f2447173877a4cc0f1fe43e472a4573`): **112/112**, comprising 63
gameplay, 27 tooling and 22 asset checks. The checkout stayed clean and unchanged.
Rust and audio groups were not rerun. The report is under
`Saved/Qualification/2026-10-26/ward-gate-3f115e51-source/` in the source-validation
worktree. `report.json` SHA-256 is
`7c87b8ef03729d7d7b1bfab234e9e1a817bdf1ebc649c3c596dab02dead719f8`;
the separate inventory/112-log hash audit `independent-review.json` is
`c0960a6d7aa388c891fa9a2e60cc88f0bf33fb962ce8957a147999e10874cf91`.
These results do not compile the Unreal code or establish release qualification.

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
