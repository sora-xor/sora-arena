# Tenement finds: source checkpoint, 26 October 2026

This continues `codex/tenement-defense` at `f1efa2fa`. It is source work in the
source-validation worktree, not a compiled Unreal result or release acceptance.
Claude retains the exclusive engine/Blender lane. The integration branch, shared
checkout and packaged game have not been advanced.

## Behavior

Chapter three's optional b04 exploration no longer offers a combined cache that
grants c01 and c02 together. The chalk sky crest is on the west alley wall at
(-2887, 1830, 65) cm; the widow's seizure notice is on an east door at
(-2713, 2415, 135). These positions refine the existing chalk and balance-door
POI volumes. The former cache descriptor remains in the compiled task schema for
compatibility, but is excluded from available caches and their markers.

Each interaction requires grounded feet within eight centimetres of the alley
floor, horizontal reach of 140 cm, a view within 60 degrees of the object and a
visibility trace reaching its own target. The actor cannot collect from above,
through another object or while looking away. Ordinary mapped Interact records
only that find, its codex and events, and saves immediately. Repeating an
inspection awards nothing else. Both finds are required to complete the optional
beat, in either order; the carry objective and hidden-weapon recovery remain
active. Optional completion cannot bulk-grant these collectibles.

The b04 ambient volumes now run alongside b05/b06, at ground level. Previously
they belonged only to b04's inactive space and could not fire during the required
carry objective. They retain their existing nonrepeatable dialogue contracts.
Proximity prompts display the current Interact binding. No map markers are added.

The chalk object uses the existing pinned SVG's mon mesh, flattened and painted
chalk white at child height. The notice is a paper proxy. Children, residents,
hand lettering, balance numerals, weathering and final art remain unfinished.
This does not implement the 150-second hint lamp or the kitchen resident queue.

## Evidence and pending checks

Fourteen targeted host tests pass. A compiled native driver checks grounded,
distance, height, invalid-index and nonfinite-input cases and emits the actual
find coordinates. Geometry tests verify clear alley approaches and separate
interaction ranges. Data tests reject swapped collectible bindings, moved or
raised objects, combined rewards, duplicate POIs and finds attached to other
beats. The campaign validator passes 133 beats, 1,032 bilingual lines and 65
rejected invalid variants. Regeneration is current; only chapter three and its
dojo campaign-binding hash changed. Broad source checks are still to be recorded.

The revised `SoraArena.Campaign.RecoveryCache` fixture is **uncompiled and unrun**.
It uses controlled placement and held threats to check both discovery orders,
separate saves, repeated input, looking away, an intervening box, a raised actor,
menu refusal, remapped Interact, fresh-world partial-save restoration and the
still-locked hoist/katana. The assisted campaign harness visits both objects
separately and retains its existing completion, collectible and checkpoint
assertions. Neither fixture proves ordinary campaign traversal.

After lane handback, compile and run RecoveryCache, EquipmentRecovery, the
tenement/defense and ward suites, campaign save/control regressions and the
assisted playthrough. Inspect actual dialogue delivery, interaction readability
and both physical finds during normal play. Preserve the earlier source and
runtime qualifications at their recorded revisions.
