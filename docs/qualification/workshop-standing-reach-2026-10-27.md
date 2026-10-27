# Workshop standing reach — October 27 source checkpoint

Claude's current b09 reach survey reports crouched paw reaches of 105–192% of
the available arm at the four benches. The existing gameplay gate checked
floor support, distance, action state and wall occlusion, but permitted all six
recipe steps while crouched. Hiding unreachable paws would leave invisible
crafting active.

The source change refuses workshop interaction while either crouched or
requesting crouch. The mapped crouch press immediately cancels an active hold,
before capsule movement or a same-frame release can credit a bend. It frees the
hands, discards the partial unit and retains completed work. Holding Interact
while standing again cannot restart the cancelled action; release and a fresh
press are required. A stand request remains ineligible until the actual stance
rises. Refused crouched interaction explains how to reach the bench in Japanese
with an English subtitle. The recipe, counts, timing, geometry and camera are
unchanged.

`SoraArena.Campaign.LanternWorkshop.CraftStandingReach` exercises mapped C and E
input through all six steps on the authored floors. It checks crouch intent
before movement, actual crouching, pending stand, timed cancellation, no banked
time or action serial, fresh standing attempts and full recipe completion.
The existing interruption, recipe persistence and playthrough tests remain.

CPU checks pass: all 22 compiled workshop rules/geometry/data tests, source
content validation including input conflicts and glyph coverage, and whitespace
validation. Signed `558df255` then builds its isolated SOURCE editor and passes
all 42 selected native cases with zero errors/warnings: every workshop case,
the new standing-reach case, climb/moat and input regressions, the assisted
campaign, and credits navigation/font selection. Natural EOF is
`2026-10-27T05:28:35.111035Z`; the independent review verifies all 20 originals
and unchanged source/native/Config/Generated inputs. Review digest:
`c436d059225e19fa8d3cdf71847486d28a93b4f5e07dcfba56dcfc0fe046f237`.

This proves the directed posture/cancellation behavior, not credible paw reach
from every position currently admitted by the 260 cm interaction radius.
Claude's provisional 4–8 cm working depths (zero depth at the shell bench) are
not accepted as usable positions. Final working regions, facing bands and their
matching collision proxies must support ordinary keyboard/controller walking,
including natural stops, without snapping the player or camera. Their boundary
and interior poses, active contact visibility and the presenter remain open.

The packaged client and ordinary-play acceptance remain pending. ROOT stays
frozen at `c096eb98`; these changes remain in the source worktree. The full
engine lane returned to Claude under Coordination 263 after the subsequent
credits capture and its review. No art candidate or failed-package replacement
is admitted by this checkpoint.
