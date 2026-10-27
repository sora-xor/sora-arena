# Workshop action view

`SoraWorkshopCraftRules::FView::LastAction` is a read-only record for the
presentation of the most recently credited workshop unit. It supplements
`Committed`, `HeldStep` / `HeldMs` and the failed-strip state.

| Field | Meaning |
| --- | --- |
| `Serial` | Starts at zero; advances once per successful unit, including timed work. Zero means no action since reset. |
| `Step` | Credited zero-based recipe step, 0–5; −1 before any action. It remains the completed step when the current task advances. |
| `Unit` | One-based completed unit within that step; zero before any action. |
| `AgeMs` | Whole active gameplay milliseconds since credit; −1 before any action. Saturates at `ActionPresentationMs`, currently 1200 ms. |

Only gameplay credit publishes an action. Failure, refused input, reading the
view and completing an animation cannot advance production. Repeated valid
presses replace the latest record; this is not a queue and a presenter must
not fabricate intermediate clips or impose a new input cooldown.

Animation may use a shorter authored clip, but ends by 1200 ms. Menu, blocking
dialogue, cinematics and defeat do not advance its age. Reset, reload and a new
encounter clear the record; the presenter must clear its own serial cursor too.
The one normal b09 → b10 transition retains final inspection briefly. The
recipe, forty-lantern registry entry and unlock still complete immediately.
Later beat changes clear the action.

This state does not establish a viable hand pose. The presenter must separately
check player posture, location, current activity, world contact and prop
lifetime, and relinquish an invalid pose. It may not stretch arms, reposition
the camera/player, replay output, or delay accounting to finish a clip. The
normal b09 → b10 transition now preserves the player's place and four
chapter-owned station components; checkpoint entry retains its saved start.
New craft props must share that chapter lifetime rather than belong to the
temporary `KitPieces` / `KitActors`, which are still cleared on a beat change.
Surviving state alone is not proof that final inspection is visible. ROOT owns
that integration; Claude owns authored paws, contact poses and clips.

No workshop craft paw assets or presenter are integrated by this interface.
The [station-lifetime and continuous-exit follow-up](../qualification/workshop-lifetime-2026-10-27.md)
passes all 70 selected native cases at signed `94eb18bb`, including the mapped
exit and death/retry checks. This does not qualify visible contact or final art.
