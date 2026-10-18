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

Completing a goods task emits a bilingual registry notice. The three first-tally
entries report their inspection when ch05.b12 ends. Registry notices wait through
the following cinematic so the title-card renderer cannot consume them unseen.
The successful campaign result shows the current chapter's ordered registry
page using the existing HUD typography, palette and logo. Inspected entries
show three labelled seal marks and a split tally with the crest across its
halves. Returned goods show the authored note 「返還のみ記帳・札は切らず」 /
“Recorded as returned. No tally cut.” with no split tally.

Continuing a saved chapter completion reopens that page; Enter on the page
advances normally. Incomplete saves resume their checkpoint, and defeat and
practice retain their existing result presentations. The English subtitle
toggle and remapped Continue/Menu prompts remain available.

Host checks: `python3 scripts/unreal/test_registry_data.py`, the campaign data
generator's `--check`, and `validate_campaign.py`. Directed engine checks are
`SoraArena.Campaign.Registry.Data`, `InvalidData`, `ProductionAndRetry`,
`FirstInspection` and `ResultRecovery`. They cover real carry interactions,
completion notices, checkpoint rollback/reload, both authored ways to finish the
inspection cinematic, saved completion pages, subtitle toggling, progression,
chapter replay and New Campaign. The result-recovery fixture constructs a valid
completed checkpoint through the pure progression rules; it is not a substitute
for the full campaign playthrough. Adding tests is not execution evidence.

The functional seal and tally marks are not bespoke final art. The diegetic ch05
branding press and ch06/ch08 posted-page world interactions remain separate work.
