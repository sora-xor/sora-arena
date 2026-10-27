# Elevated ladder flights — October 27 validation

Signed source `4c4fb7fac80689d84f7048845fa7ff313d672525` (tree
`dac76dbce6b21aabb3140ba9347dd289f9627ce8`) adds an optional absolute
`base_height_cm` for ladder flights. Existing ladders default to street level.
`height_cm` remains the absolute roof height, so a flight from 340 cm to
560 cm climbs 220 cm. Its rails and rungs begin at the raised base. Overlapping
roof regions select the highest roof below the player for landing/noise state.

Mount admission checks the real feet elevation and facing. Both directions
retain the same swept movement, speed budget, interruption behavior and
support check; a removed landing cannot award arrival or drop the held player
through to the street. Serialized bases must be nonnegative integers below
the destination roof. Existing eight chapter outputs regenerate unchanged.

All seven selected editor tests pass with zero selected errors or warnings:
the new elevated-flight fixture, existing ladder collision and roof behavior,
three notice-square street/patrol checks, and campaign-space checks. The new
fixture rejects mounting from the street beneath the raised flight, climbs
from a supported 3.4 m landing to the 5.6 m roof and back with mapped Jump,
checks pause, removes/restores the lower support, and checks arrival counts.
Only its initial fixture placements are teleported; traversal is swept.
This is directed automation, not ordinary route-play acceptance.

The fresh Editor build and NullRHI run finish naturally from 08:08:46 to
08:10:29 UTC on the M2 Ultra with UE 5.8.3 and project-scoped Xcode 26.1.1.
Independent review verifies 20 original evidence files, exact selected names,
source/native/Config/Generated immutability and the frozen integration Git
state at `b6ba3c11`. The raw log retains 19 pre-initialization `Condition
failed` diagnostics outside the selected tests. No rendering or packaging was
performed. The native bridge remains `10ad7dad`.

Host validation passes the eight chapter regeneration check, campaign schema
validation with 71 rejected bad variants, and 11 ladder normalization cases
covering omitted/default bases, valid elevations and invalid types/ranges.

Evidence is in `Saved/Qualification/2026-10-27/` in the source-validation
worktree:

| Record | SHA-256 |
| --- | --- |
| Original run status | `db448704aac1b10c596dada58dcb3d03561db5424031a8b2514a36df27a22dd9` |
| Independent review | `d0ce11950565e7c14ff11738bb4eed256ea78d9540e271302257a36ed4d49ca4` |
| Runner | `384df900ca22af8abfdf66ca3ace095c31010b68d9a37009796620e8bc364661` |

The notice-square multi-stage roof, coherent building/eave layout, drone
circuit and rear marksman approach are still being designed. No authored
route amendment is accepted by this isolated fixture. This source has not
been adopted into the frozen integration worktree or its preserved 1b6
package. Final art, ordinary play and broader release qualification remain open.
