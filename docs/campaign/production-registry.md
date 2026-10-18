# Offline production registry

The registry records the authored goods, quantities and period counter words.
It has no wallet, balance, price, conversion, multiplayer entitlement or network
operation. Collected `registry_page` lore remains a separate codex category.

`FSoraBeat::Registry` keeps the sixteen existing authored entries. The importer,
host validator and runtime catalog require the five typed fields, nonempty
labels and a positive 32-bit integer count. Only production tasks and cargo
rides can carry an entry. An explicitly supplied `registry_mode` must be
`record_only`, with an entry; unknown values fail loading.

`SoraRegistry::Completed` reads the current chapter's completed-beat mask. It
does not accumulate quantities or write another save field. Existing schema-6
checkpoint validation, death/retry, chapter replay and new-campaign rules remain
the source of progress. The saved completed checkpoint reconstructs the same
chapter page. Earlier chapters are not a new persistent archive.

Before ch05.b12, entries are recorded without split tallies. Completing that
inspection, including its authored cinematic skip, inspects the three ch05
entries; later ordinary entries are inspected. Ch07.b07's 430 horse-loads are
returned goods: they never gain a split tally. Ch05.b17's delivery and ch08.b16's
posting do not add entries, because their goods were already recorded.

Host checks: `python3 scripts/unreal/test_registry_data.py`, the campaign data
generator's `--check`, and `validate_campaign.py`. Directed engine checks are
`SoraArena.Campaign.Registry.Data` and `InvalidData`; adding them is not evidence
that Unreal has run them.

This data/readout slice does not complete the display, bespoke brush/tally art,
the diegetic ch05 branding press or ch06/ch08 posted-page world interactions.
