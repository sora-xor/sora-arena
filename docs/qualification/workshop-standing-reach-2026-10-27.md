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
validation. These do not compile or execute the Unreal stance integration.
The new native case, affected input/fieldcraft regressions, full campaign,
packaged client and visible paw behavior remain pending. ROOT stays frozen at
`c096eb98` while Claude owns the full engine lane; these changes are isolated in
the source worktree. No art candidate is admitted, and the reported paste,
oil and rim contact visibility defects remain open.
