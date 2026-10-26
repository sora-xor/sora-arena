# Kitchen supply: source checkpoint, 26 October 2026

Inspection after `fb08f688` found that b14's named supply data and generic refill
code were present, but `StageSupply` created only the chapter-eight spire crate.
The kitchen had no runtime supply object. The earlier defense source note is
corrected; its passing host checks did not establish this missing behavior.

The builder now stages the kitchen's crate at (-2340, 3540, 0) cm, wholly inside
the authored 200 cm doorway volume and clear of both manager-house step runs.
The functional crate is 80 x 70 x 70 cm. The existing arrow/cartridge proxies,
refill rules, weapon entitlement checks, cooldown refusal and teardown are reused.
Other supply identities are unchanged.

Kitchen supply requires a grounded player within the authored rectangle and an
unobstructed trace to its own crate. The door volume includes earth, 22.5 cm steps
and the 45 cm room, so these approaches are admitted explicitly; the spire's
existing floor tolerance is unchanged. Proximity alone does not refill anything.
The crate's craft, League mark and final dressing remain unfinished.

The host test checks the shared crate dimensions against the tenement solids,
floor and supply bounds, along with the approach and reach constraints. Its first
straight diagonal approach struck the working-well post; the corrected route
goes north of the well. The collision check was retained unchanged.
All 15 targeted host tests pass with that route; `git diff --check` also passes.

`SoraArena.Campaign.Tenements.KitchenSupply` is prepared for Unreal: it equips the
restored yumi, actually spends an arrow with mapped Fire, walks from the kitchen
spawn around the well to the manager's east step, checks refusal outside the
200 cm volume and in the menu, then refills with Interact. It checks the weapon,
health, beat and unlocks remain unchanged and the quiver cannot overfill. It uses
a hardened hero and fixture damage; it does not establish combat difficulty.

Unreal compilation, this route, the other pending ward/tenement suites, rendered
inspection and ordinary play remain required. No release qualification is claimed.
Claude explicitly returned the engine/Blender lane at 17:20 UTC for this validation.
