# Offline campaign progression acceptance

## Campaign data (catalog schema 4)

The chapter scripts in `docs/campaign/chapter-0N.md` are the authored source. Each carries one YAML block written to the story bible's beat taxonomy (§12.1, §12.2) and chapter-YAML conventions (§12.5). `python3 scripts/unreal/build_campaign_data.py` turns block N into `Content/Data/campaign/chapter_0N.json`; `--check` fails when a committed file differs from a fresh build. The importer needs PyYAML (`pip3 install --user -r scripts/requirements.txt`). It rejects duplicate YAML keys, non-JSON values, keys outside the §12 contract without an `x_` prefix, unknown beat, task, ride, defeat, scoring and dialogue-mode values, and registers with no §18 family. Each chapter file holds:

- `beats`: the §12.1 common fields, always present with fixed types and their defaults filled in (`requires` defaults to the previous beat, `fail` to `player_died` → `checkpoint`); the §12.2 parameters under `params`, with completion normalized to `{kind, …}`; every `x_` proposal, without its prefix, under `ext`. `unlocks.grants` names a skipped optional weapon a later beat grants (weapon 13 at ch07.b01), which is not a second unlock.
- `lines`: all 1,032 voiced lines once, with speaker id, `duration_s`, the register's §18 family and the alias's delivery note.
- `triggers`: the one table that schedules lines, as `{beat, on, mode, lines}` rows. It covers beat dialogue entries, dialogue beats, boss and duel barks, cinematic subtitles (with `at_ms` on the cinematic's own clock) and the ch05/ch06 bark pools. No line has an absolute start time. Where a script lists a cinematic's subtitles without times (ch05–ch07), the importer spreads them over the cinematic in script order without overlap and marks each row `ext.at_ms_spread`; a script that times some subtitles must time all of them.
- `sites` (restored in beat order, each requiring the one before; ch08 restores site 1 first), `checkpoints` (in target centiseconds, with per-phase saves), `unlocks`, `collectibles`, `ui_prompts`, `places` (from the bible's §14 table, with their arena) and `layout` (ch01–ch03's volumes, points, splines and patrols in integer centimetres, in the frame each chapter authored; ch04–ch08 have authored none yet).

`Content/Data/campaign/campaign.json` is hand-authored. It lists the chapter files, the chapter title-card narrative and objective, the three production-site labels (all moved verbatim from schema 3, except that ch08's objective is the one its script gives), the mechanic flags in save-bit order and the collectible categories. `Content/Data/catalog.json` keeps the shared core (classes, weapons, maps, hero) and the 40 dialogue speakers; it no longer has chapters, kill quotas or timed cues. `SoraArena.Build.cs` stages `Content/Data/...`, which UnrealBuildTool's file filter resolves recursively, so the campaign files are packaged without a Build.cs change.

`python3 scripts/unreal/validate_content.py` requires the committed chapter files to equal a fresh build and runs `scripts/unreal/validate_campaign.py`, which checks the bible's §12.3 rules: pacing against §10 (the beats sum to exactly 25,200 s), sites 0–2 once per chapter in `requires` order, weapons 0–20 once each at their §11 beats in §11 order, bosses from §8 (and `bosses.json` once it exists), mutō-dori attacks only where the fight's defeat or finisher allows them, mounted weapons within {0, 18, 19}, registry entries only on production tasks and cargo rides, every line bilingual with a catalog speaker, at most 17 EN characters per second and within two subtitle lines (42 EN or 16 JA characters each), nonlethal enemies never counted toward a defeat count, and at most 360 target seconds between checkpoints. It also checks line references in both directions, blocking dialogue of at most 20 s, collectibles and prompts, and that the 25 cues of schema 3 (frozen in `scripts/unreal/fixtures/campaign_legacy_lines.json`) survive verbatim with their §20 speakers. Its self-test first passes the real data, then must reject 18 mutated variants that each break one check, so a broken check cannot pass. The glyph check covers every campaign string against the bundled Noto Sans CJK JP font.

## Beat rules

Run `python3 scripts/unreal/test_campaign_progression.py` from the repository root. It reads the eight chapter files, generates a temporary C++ fixture of each chapter's beats (requirements, site, weapon and mechanic unlocks, grants, checkpoints and per-phase saves) and compiles `campaign_progression_driver.cpp` against `SoraBeatRules.h`.

The script also requires `SoraCampaignDirector.cpp` to call the tested gates (`SoraBeatRules` beat completion, checkpoint, progress and entry checks; `SoraCampaignRules` chapter advance, collectibles and training arena; `SoraDojoRules` forms) and `SoraCatalog.cpp` to refuse chapters that `SoraBeatRules::ChapterValid` rejects. The driver first checks `SoraCampaignRules.h`: chapter advance and liberation, the 48 collectibles as one mask that no unreached chapter can hold, and the training arena's twelve defeats and three workshops.

The driver checks each chapter against the beat rules and plays it twice: once skipping every optional beat and once playing them all. Before each beat it checks that the next required beat is the one expected, that no later beat whose requirements are unmet can start or complete, and that checkpoints are valid exactly at the authored beat starts and boss or duel phases. It also checks that forged saves are rejected: an unearned site, weapon or mechanic, a beat saved without its requirements, or a premature completion. It then completes the beat, rejects a second completion and revalidates the state. Each chapter ends with the exit gate and a rejected second completion. Between chapters it checks that both routes' carried unlocks are valid entry masks and that chapter select's cumulative mask is the completist's. Both routes must end with all 21 weapons and all 19 mechanics.

Chapter one additionally uses `SoraDojoRules.h`: stance must be held for 600 ms, a front-facing guard must survive a pupil strike after 350 ms, a fresh front-facing parry must land within 260 ms of pressing defense, and a wooden-sword swing must complete its recovery before a pupil can be scored. The driver rejects out-of-order, short, late, backwards, and forged lesson progress.

This host test covers the rules and the content. The Unreal runtime and its in-editor acceptance follow.

## Unreal runtime (schema 4, save schema 6)

`FSoraCatalog::Load` reads `catalog.json` (schema 4, no chapters), `campaign/campaign.json` and the eight chapter files, and fails closed: any missing or mistyped field, an unknown speaker, line, beat, mechanic or collectible category, a subtitle outside a cinematic, checkpoint rows that disagree with a beat's own flag, a chapter that does not open on a cinematic, or beats that `SoraBeatRules::ChapterValid` rejects leave the catalog unloaded with the reason in `FSoraCatalog::Error`. It also requires every route through the eight chapters to end with all 21 weapons and all 19 mechanics.

`USoraCampaignDirector` plays each chapter's beats in the order `SoraBeatRules` allows. Until the specialised systems land, every beat type reduces to one goal (`ESoraBeatGoal`):

| Beat | Goal in the offline runtime |
|---|---|
| `cinematic` | The letterboxed card for `duration_s`, holding play, the round timer and dialogue queue, with subtitles on the cinematic's clock; Enter skips. A fresh chapter's opening cinematic shows the chapter title card first. |
| `dialogue` | The beat's lines in order, walk-and-talk. A `volume_enter` trigger starts them on reaching the anchor, an `interact` trigger on E there; a `complete` volume or event then waits at the anchor. |
| `combat_wave` | Defeat every lethal enemy over the waves (`nonlethal_types` never count), at most `max_alive` at once. `objectives` completion is worked at the anchor instead. Training targets (`mato`) are sparring pupils. |
| `duel` | Lesson gates teach the dojo forms their gates name, then score `marobashi_flank` bouts; `points` duels respawn one opponent until `first_to`; `hp` duels end on one defeat. Bokuto and fukuro-shinai bouts use a sparring pupil, live blades a retainer. |
| `boss` | Defeat the boss; each later phase starts at its `hp_pct_start`, raises `boss_phase:N` and saves a phase checkpoint where the chapter file has one. A restored phase returns the boss at that health. |
| `production_task` | `crank` turns, `carry` deliveries and `manufacture` steps are E presses at the anchor; `hold` and timed `defend` are seconds spent there; `escort` reaches the anchor. Any waves must also fall. |
| `stealth_zone` | Reach the exit, or work each objective, at the anchor. |
| `horseback_ride` | Reach the destination (or deliver to each cargo drop-off) and defeat any waves, on foot. |
| `explore_optional` | An unmarked cache (a chest and a lantern glow, no HUD marker) off the road; E there completes the beat, collects its rewards and unlocks its weapon. |

Each beat's anchor comes from `SoraWorldBuilderLayout.cpp`: a beat that restores a site stands at that site, other beats at one of ten points on the arena's central road, and caches in the gaps between building rows. A gold beacon marks the active anchor. Completing a beat restores its site, grants its weapons and mechanics (with a bilingual notice), collects the collectibles tied to it, plays its `beat_complete` lines and starts the next beat. Triggers raised by the runtime are `beat_start`, `beat_complete`, `subtitle`, `boss_phase:N`, `site_restored:N`, `player_died`, `progress_at:X`, `interact_start` and the anchor's `volume_enter:`/`interact:` event; HUD prompts show on the same events. `USoraGameEvents` announces `OnBeatStarted`, `OnBeatCompleted` and `OnBeatFailed`, and each beat event appends one JSON line to `Saved/Telemetry/campaign_beats.jsonl`.

`USoraSaveGame` schema 6 holds the chapter, the reach, the unlocks held when the chapter began, the 48-bit collectibles mask and the checkpoint: the beat (or boss phase) it starts, the beats done and the sites, weapons, mechanics and dojo forms they earned, or a finished chapter at its result. A checkpoint beat saves as it starts. `LoadSave` starts a fresh campaign for any other schema, a chapter beyond the reach, entry unlocks outside `EntryValid`, mechanics other than the earlier chapters' or collectibles from an unreached chapter; `ResetRound` replays the chapter from its opening when the checkpoint fails `CheckpointValid` or `ProgressValid`, or its dojo forms differ from those its lesson duels taught. Chapter advance carries the route's unlocks forward; chapter select grants every unlock the earlier chapters offer (bible §11); New Campaign clears unlocks and collectibles. Nyaakoto's equipment refuses a weapon the campaign has not unlocked, with a notice; the training arena lends every arm.

## In-editor acceptance

`scripts/toolchain/run-automation-mac.sh SoraArena` runs these campaign tests in real game worlds with isolated save slots:

- `SoraArena.Campaign.Playthrough` plays all eight chapters (the 125 required beats) through Enter, E, the hero's position and lethal damage, reads the disk save back at every checkpoint beat, restores three checkpoints in fresh worlds (the dojo smithy, Dunark's second phase at its saved health, and a hold beat), retries a defeat, checks that the yari and arc carbine stay locked until their beats, opens every cache in chapters one to five and skips those of six to eight (so the phantom SMG arrives by the ch07.b01 grant), ends with all 21 weapons and 19 mechanics, and reloads the liberated city. The hero is healed between actions; combat balance is tested by the combat trace, not here.
- `SoraArena.Campaign.ForgedSaves` writes two valid checkpoints and twelve forgeries (a schema-5 save, later-chapter unlocks, an unreached collectible, a chapter beyond the reach, an unearned weapon or site, a beat without its requirements, a beat that takes no checkpoint, a phase beyond the boss's saves, a premature completion, an untaught dojo form) and checks what a real world restores from each.
- `SoraArena.Campaign.SaveRoundTrip` and `SoraArena.Campaign.DiskSaveRecovery` round-trip schema-6 checkpoints through memory and disk.
- `SoraArena.Campaign.ChapterTitleCard`, `CombatTrace`, `DeterministicEnemyFire`, `SoraArena.Events.ScriptedFight` and the menu tests seed schema-6 checkpoints with `USoraCampaignDirector::SeedCheckpoint`.

Each of four director mutations (unlocked weapons, no checkpoint at beat start, accepting a forged checkpoint, no site restore) makes the playthrough or forged-save test fail.

## What the offline runtime does not do yet

These wait for other lanes or later steps and are not claimed:

- Stealth guards, detection, takedowns, light and noise (L2); stealth beats spawn no guards.
- Enemy and boss types from `enemies.json` and `bosses.json` (AI lane): every opponent is the prototype invader, blade retainer, sparring pupil or collector, and boss pattern tables, weak points and adds are not used.
- Horses and mounted combat: rides are crossed on foot.
- Sequencer cinematics (C9): cinematics are the letterboxed card with subtitles.
- Escort NPCs, defended targets' health, carry pickups as separate places, crank rate bands, the `maai_step` gate, blocking dialogue's input lock, and allies.
- Authored layouts: ch01–ch03's layout data (in their own frames) is not yet placed in the arenas, and ch04–ch08 have none, so every chapter uses the anchors above in its cataloged arena.
- Loadout slots for weapons other than Nyaakoto's class slots and the yumi, yari and naginata (L4), and key glyphs in HUD prompts, which show the scripts' placeholders. `ASoraPlayerCharacter::EquipCampaignWeapon` still refuses the yumi, yari and naginata throughout chapter one, so the matoba's targets fall to the bokken until that check defers to the unlock mask.
- The 6–8 hour pacing, combat readability and visual quality, which need playtests and captures.
