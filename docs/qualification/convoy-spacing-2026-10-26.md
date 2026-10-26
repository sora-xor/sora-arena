# Convoy spacing and mounted net cut

The chapter-two pack horses now wait as one tied string when the rider moves
too far from any member. Previously each horse stopped independently at its
own 25 m distance limit. Following horses caught up with the stopped leader
and overlapped, losing their authored 450 cm spacing.

The corrected drone body exposed this existing defect by changing which net
landed first. The mounted cut still selected the first eligible net correctly,
but the overlapping horses made the selected horse differ from the fixture's
expected target. The cut's weapon, side, range and reload rules are unchanged.

## Evidence

At signed `5b1f6c49`, the failed ConvoyNets diagnostic records distinct initial
chainages 42300.078, 42750.078 and 43200.078 cm. Before the cut, all three have
collapsed to 43312.578 cm and the same actual world position. The blade frees
quarry 0, while the first net observed by the fixture belonged to quarry 1.
The three failed assertions and natural editor/wrapper exits 3/1 are retained.
Independent review:
`022d263fdc3d3c0f096cabeac91240df98fbabf0976d38ce306e5264ddc2ade0`.

At signed `7b48ae3ac23ac01f94bfcfe0573f4859ea80386e`, all seven selected
NullRHI fixtures pass without errors or warnings: ConvoySpacing, ConvoyNets,
Mount, DroneCrossing, BuntaLeadFear, KurimaruSpookDismount and Playthrough.
The new spacing test observes the real string before the first ambush mark,
waits for every member to halt, verifies that it stays put, then moves the
rider forward and observes all three resume at 450 cm/s. Maximum measured
spacing error across waiting and resumption is 0.000000 cm. ConvoyNets also
checks the separate 450 cm positions and passes the mounted cut, nine-second
drone reload, freed-horse protection, tether kill, held foot cut and haul loss.

The assisted playthrough completes eight chapters, 126 required beats and
seven optional caches. Its relay fixture samples more valid ground approach
positions around fallen drones while retaining reach, visibility, grounding,
body-drag priority and the real scan window. Long assisted waits are divided
into world ticks no larger than 50 ms, eliminating the earlier character
movement iteration warning. Upper-platform positions are unchanged.

The editor builds successfully and editor/wrapper exit naturally at 0/0.
Twenty archived files independently rehash; source/native inputs, Config and
Generated assets remain unchanged. Evidence is under
`Saved/Qualification/2026-10-26/convoy-spacing-runtime-attempt1` in the isolated
complete-game worktree. Review SHA-256:
`eb109d5530a165d30998743e05d89680605f789ac9709875ec5324568ed92422`.

These tests use assisted placement, and the campaign fixture heals the hero.
They establish the scoped movement/interaction regressions, not ordinary
campaign difficulty, final horse/net art, packaged play or performance.
