# Kitchen residents: source checkpoint

The ch03.b14 kitchen previously had no serving queue. Six bystanders now stand
in a file from the court down the alley. They are excluded from enemy perception,
immune to incidental damage, and ignored by bullet/interaction visibility traces.
Their world collision remains enabled.

The same live enemy capsule-volume test that suspends kitchen work starts their
scatter. Each resident first aligns with a doorway in the alley, then walks into
a different home using the existing bystander's CharacterMovement. They remain
visible indoors for the rest of the defense; they do not disappear or teleport.
Beat cleanup destroys them, and checkpoint staging creates a fresh queue.

All twelve homes now have 100 cm door openings, 210 cm above their 15 cm raised
floors. The openings are offset to keep the children's chalk and the debt notice
on paper panels. Home footprints, the alley, court, wells and manager room retain
their dimensions. These are functional solids and existing civilian proxies;
door craft, individual resident art and final kitchen dressing remain open.

The compiled host geometry tests cover six distinct routes, capsule clearance
through each doorway, raised home floors, separate queue positions, and preserved
backing for both finds. Filled or too-narrow doorway fixtures block the capsule.
All eighteen tenement tests pass locally. The first new run exposed an omission
in the test's floor lookup: it counted earth but not the raised stone slabs.
The lookup now includes low stone floors; production geometry was unchanged by
that correction.

All 64 gameplay source gates subsequently pass at signed
`09b192d08c47e563adcbc121c938efac4742a7ed`, tree
`2e033a5aa7c846a0f45cd61e808e7cbeeebea681`. The checkout remains clean and
unchanged throughout. Exact gate/command inventory and all 64 original logs
are separately audited. The source-validation worktree retains
`Saved/Qualification/2026-10-26/kitchen-queue-source-09b192d0/`:

| Evidence | SHA-256 |
| --- | --- |
| `report.json` | `ff100379cf26814033ae9efbc2469c49dde5f80bac8b3ca4a5aee9d3da3f6ea2` |
| `independent-review.json` | `7ab7b5446388eda659bcaa02932e1f92bb9c7a2a9faa003b392a03ca891b773c` |

`SoraArena.Campaign.Tenements.KitchenQueue` is added but **not yet run**. It uses
the real first wave, directed enemy placement, damage and traces to check
non-targetability, scatter only after volume entry, bounded movement, standing
inside each room, menu pause, actual defeat/retry and cleanup. Its hero is hardened
and enemies are held to isolate this behavior. It does not establish ordinary
combat or final civilian art.

Unreal compilation and runtime validation remain pending while Claude owns the
engine/Blender lane. Earlier 32/32 runtime and 123/123 CI evidence at `bae6e9d4`
and `6795e0c6` respectively predates this change. No new package, performance,
render or release acceptance is claimed.
