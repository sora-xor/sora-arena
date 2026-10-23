# Authored cargo quantity and transfer checkpoint

This change implements the remaining quantity and visible-transfer contract in
`docs/campaign/chapter-04.md` b14 and §6.4: Bunta starts with 30 barley sheaves,
and a completed three-second unload transfers ten to each of the three hamlet
drying stands. The existing unique delivery credits remain the sole mutable
inventory. Remaining cargo is derived as `total - per_dropoff * Done`; each
stand's display follows its existing `DropoffUses` entry.

The authoring normalizer rejects missing, non-integer, non-positive, oversized,
duplicate-destination or inconsistent quantity records. The generated mount
manifest retains the quantity, unit size and item. The C++ catalog independently
checks numeric type/range, quantity conservation, authored destination order,
the led carrier, and exactly one drying stand per destination. Other mounts
require a null cargo manifest. Allocation is bounded by the existing maximum
of eight destinations, rather than by a potentially large sheaf count.

The pack's paired bundle groups and the drying stands use existing basic scene
meshes. They make transfer state visible, but remain functional WIP art; this
checkpoint does not establish photoreal barley, horse, prop or scene acceptance.
The connecting lead rope remains separate unfinished work. The new meshes have
no collision, and this change adds no pack-proximity condition, cargo loss,
horse-health failure, required remount or post-delivery return gate. Ordinary
on-foot continuation and the existing gaits, fear, collision, damage and hold
rules are unchanged.

The display updates immediately after an accepted delivery, before delivery
events and beat teardown. Starting or retrying the beat reconstructs the full
pack load and empty stands. Leaving the beat destroys the temporary displays.

## Author checks

The following commands passed in the isolated author worktree. These are source,
data and host C++ rule checks, not Unreal runtime results:

- `python scripts/unreal/build_campaign_data.py --check`
- `python scripts/unreal/test_cargo_unload_data.py` — 14 tests, including malformed
  quantities, overflow bounds, mismatched normalized manifests and carrier/kit
  metadata, plus the existing hold and spook-policy validation.
- `python scripts/unreal/test_campaign_progression.py` — includes all six delivery
  orders, quantity conservation after each accepted share, refused partial and
  duplicate deliveries, on-foot continuation and checkpoint reset.
- `python scripts/unreal/test_carry_work_data.py`
- `python scripts/unreal/test_carry_difficulty_data.py`
- `python scripts/unreal/test_fieldcraft_rules.py`
- `python scripts/unreal/test_stealth_rules.py`
- `python scripts/unreal/validate_content.py`

`SoraArena.Campaign.CargoUnload` is extended to inspect the actual pack and stand
component visibility at each state. It checks partial/released/paused/cancelled
work, all three accepted deliveries, holding after a delivery, on-foot unloading
with the horses left behind, and retry after an accepted transfer. Its observer
checks the empty pack and all three loaded stands at `OnBeatCompleted`, before
the next beat removes them. The fixture retains its existing assisted checkpoint
and initial hamlet placement plus frozen threats; it does not establish ordinary
campaign pacing or balance.

The runtime fixture includes the integration fixes from signed commits
`d6d51b025764cfa5ac71f97fae52317b2b2c00d3` and
`3a3a3d3927015566011f2cbfd789586e98c6eb82`, cherry-picked here as
`9a0e009` and `2415206`. Those preserve the real route spook and use the mapped
Interact key to remount during the traversal fixture. The parent integration
process owns Unreal compilation and runtime qualification of this new extension.
No Unreal build, render or runtime test was run in this author worktree.
