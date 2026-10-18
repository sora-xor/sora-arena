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

Checkpoint flags save at a beat's start. A reload during ch05.b14 therefore
returns to the saved ch05.b12 start, with its three goods recorded but the
inspection not yet completed. After the following mandatory checkpoint at
ch05.b15 starts, its saved completed-beat mask retains the inspection. Registry
seals follow that ordinary rollback contract; they do not persist separately.

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

Rendered UI fixtures are a separate review gate. `SoraCapture.RegistryFixture`
contains `Chapter4`, `Chapter5` and `Chapter7`; each loads a throwaway, validated
completed save through Continue and captures Japanese alone and Japanese with
English enabled. It verifies four recorded entries, three inspected entries and
one return-only entry respectively, including exact quantities and tally state.
These constructed saves are **UI fixtures, not campaign completion evidence**.
The lifecycle tests and capture fixtures share the same completed-save builder.

Run the rendering wrapper once at each review size after integrating the source:

```sh
scripts/toolchain/capture-editor-game.sh SoraCapture.RegistryFixture 1920 1080 sm6
scripts/toolchain/capture-editor-game.sh SoraCapture.RegistryFixture 1280 720 sm6
```

Each successful run writes six PNGs under
`Saved/Screenshots/SoraCapture/<width>x<height>/`, with names such as
`RegistryFixture_Chapter4_JA.png` and `RegistryFixture_Chapter4_JA_EN.png`.
`index.tsv` labels their language, row count and fixture provenance. The log emits
`SORA_REGISTRY_FIXTURE_FRAME <absolute PNG path>` only after a fresh screenshot
write succeeds; the qualification wrapper archives those acknowledged frames.
A failed save/load, wrong entry state, text overflow or missing fresh PNG fails
the fixture. Existing player save slots and HUD visibility are restored.

The completed campaign result renders its top bar and registry page without
objective, vitals, weapon or arms-wheel overlays. The chapter title and existing
completion headline remain inside the page. Row names, quantities, status notes
and footer prompts use measured wrapping with no line-count truncation. Chapter
and row heights grow to retain every character. Small text has a minimum scale
independent of viewport scaling; seal cells size from the actual Japanese and
English role labels. Bilingual status shares one wrapped line, while English
footer prompts occupy their own wrapped lines. Captures check the same measured
layout used to draw, including viewport margins, line height, role-label bounds,
minimum text scale and retained text. The resulting images still need visual
inspection for readable typography, seal placement and overall composition at
both sizes.

Goods and their English translation share a baseline when both measured strings
fit the row; otherwise the translation wraps beneath. Status remains complete
on the following line(s). This recovers vertical space at 720p without shrinking
the readable text floors. The page centers within the usable region below the
top bar, with the existing top and bottom bounds still enforced. Fit diagnostics
include actual page height and available bounds so a failed capture identifies
the overflow rather than permitting a clipped screenshot.

Before each registry screenshot the fixture waits for asynchronous asset
compilation to remain idle for two seconds, allowing engine preparation
messages to disappear naturally. A 120-second timeout fails the fixture instead
of capturing a partially prepared frame. Diagnostic messages remain enabled.
SM5, SM6, packaged output and full campaign completion remain distinct evidence
gates.
