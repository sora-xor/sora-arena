# Offline campaign progression acceptance

The latest prepared cargo checkpoint is `eeaf2ed`: five selected SM6 720p
captures pass, including all three unchanged-duration holds, the complete
cinematic and the final zero notice with an unobscured idle boss readout.
All twelve originals were inspected. Separate `812d70c` campaign captures pass
seven tests but remain visually rejected for Tarifa's reticle/hint collision
and three stealth/tracker collisions. The
[current checkpoint](../complete-release-plan.md#october-24-cargo-timing-and-campaign-hud-checkpoint)
preserves failures, exact scope and remaining work. Ordinary campaign play,
combat presentation, final art, 1080p and a current package remain open.

The preceding rendered cargo checkpoint is `235e810`. Five selected SM6 720p
capture tests pass and all twelve originals were inspected, but final visual
acceptance fails because the tracker obscures the boss readout. The counter,
horse framing, stand visibility and final zero notice improved; the measured
boss layout correction is pending. See the
[rendered checkpoint](../complete-release-plan.md#october-24-rendered-cargo-and-final-death-source-checkpoint).
These prepared captures do not qualify ordinary campaign play or a new package.

The latest counter/rope checkpoint is `67cc9a0`: CargoUnload, BuntaLeadFear,
KurimaruSpookDismount, Mount and Playthrough pass with zero selected
errors/warnings, plus all 43 gameplay source gates. The bilingual counter and
visual lead have independent source/build/log authentication in the
[counter and rope checkpoint](../complete-release-plan.md#october-24-cargo-counter-and-lead-rope-checkpoint).
Actual rendered readability, final art, ordinary pacing and a current package
remain unqualified.

The preceding directed cargo checkpoint is `ec91382`: seven cargo, horse, carry
and Playthrough tests pass with zero selected errors/warnings, along with all
43 gameplay source gates. Actual pack/stand components show accepted transfers
30 → 20 → 10 → 0, including a foot unload, checkpoint reconstruction, and final
state before teardown. Source/build/EOF/log authentication is recorded in the
[cargo transfer checkpoint](../complete-release-plan.md#october-24-cargo-transfer-checkpoint).
The fixtures still use assisted placement and frozen threats. Rendered
readability, ordinary pacing and final art remain unqualified; the later
checkpoint separately verifies the numeric HUD and connecting lead components.

The preceding directed horse checkpoint is `3a3a3d3`: CargoUnload, BuntaLeadFear
and KurimaruSpookDismount pass together with zero selected errors/warnings.
The cargo fixture remounts normally after the authored Shimo-route spook;
three unique deliveries still require their full holds. At `2ab5d01`, Mount,
Playthrough, Searchlights, HorseDown and ConvoyNets also pass, and all 43
gameplay source gates pass. Both actor orders preserve Kurimaru's once-only
spook dismount, net priority and three-second pause-aware recall. Earlier
failed assertions and the diagnosed cargo traversal failure are preserved in
the [horse checkpoint](../complete-release-plan.md#october-23-horse-behavior-and-bounded-proof-checkpoint).
That earlier checkpoint did not implement visible cargo transfer or the connecting lead.

The earlier `d21013d` checkpoint passes CargoUnload, Mount,
CarrySealAndSetDown, CarryDifficulty and the full campaign Playthrough pass.
Mount retains one HTTP connectivity timeout warning; all five have zero errors.
All 43 gameplay source gates pass at that clean source. Cargo now requires its
authored uninterrupted three-second hold before delivery credit and ambush
release. At `4db3ce3`, guard searches last 20 active seconds; at `fea8842`,
gallery hints follow 60 active seconds at both 60 and 120 Hz through pause and
retry. Earlier failures and exact source/build receipts are retained in the
[release plan](../complete-release-plan.md#october-23-cargo-unloading-and-timer-qualification).
These assisted NullRHI fixtures do not establish ordinary play pacing, final
art, a new package or platform/performance acceptance.

## Campaign data (catalog schema 4)

The chapter scripts in `docs/campaign/chapter-0N.md` are the authored source. Each carries one YAML block written to the story bible's beat taxonomy (§12.1, §12.2) and chapter-YAML conventions (§12.5). `python3 scripts/unreal/build_campaign_data.py` turns block N into `Content/Data/campaign/chapter_0N.json`; `--check` fails when a committed file differs from a fresh build. The importer needs PyYAML (`pip3 install --user -r scripts/requirements.txt`). It rejects duplicate YAML keys, non-JSON values, keys outside the §12 contract without an `x_` prefix, unknown beat, task, ride, defeat, scoring and dialogue-mode values, registers with no §18 family, times finer than a millisecond, fractions finer than a permille, `fail` rows the runtime cannot act on, and dialogue conditions that are neither `collectible:<id>` nor `story:<flag>`. Its self-test must reject 17 bad inputs, among them a horse mounted from the left, a matchlock in the saddle, a capture that names no interaction to bind its boss and 転 flanks that do not match their lesson's bouts. Each chapter file holds:

- `beats`: the §12.1 common fields, always present with fixed types and their defaults filled in (`requires` defaults to the previous beat, `fail` to `player_died` → `checkpoint`); the §12.2 parameters under `params`, with completion normalized to `{kind, …}`; the beat's `task`; and every `x_` proposal, without its prefix, under `ext`, except a ride's `x_waves` (ch02.b08's drone groups), which are the ride's waves as ch08.b02's unprefixed ones are. `unlocks.grants` names a skipped optional weapon a later beat grants (weapon 13 at ch07.b01), which is not a second unlock. `unlocks.story_flags` names a story flag the beat sets (ch07.b05's `x_story_flag`, `nafudakake_marked`).
- `task`: the beat's §12.2 parameters in the integer units `SoraBeatRules.h` runs, with the same keys on every beat: the goal (`elapsed`, `lines`, `waves_cleared`, `objectives`, `survive`, `points`, `lessons`, `opponent_down`, `exit`, `hold`, `turns`, `escort`, `deliveries`, `steps`, `cache`), its count and duration in milliseconds, the waves (trigger, value in ms or permille, the event that releases a volume or alarm wave, and spawn groups with their lethal and nonlethal counts), boss and duel phases in health permille, lesson forms, the loss policy, the hold's contest and decay, the crank's rate band as turn intervals, the escort's pace, reach and route, pickups, drop-offs, manufacturing steps with their rhythm and tolerance, defended targets, `on_detected` and its reinforcement wave, `on_horse_down`, and the `fail` rows as failures. It also holds how a boss or a duel fought to its end ends (`defeat`: `kill` for a kill or broken weak points, `spare` for a disarm or a duel that is not lethal or ends in mutō-dori, `capture` with the `capture_event` that binds the boss: ch06.b13's `interact:bulkhead_lever`, ch08.b14's `interact:engine_spine`), each lesson form's clean repetitions (`form_reps`: ch01.b03's awase ×2), whether each bout needs a 転 flank (`flank_bouts`, ch01.b04), the lesson's scored bouts (`x_scored_bouts`), and what a carry moves (`carry_item`). The loader reads this block; the host driver plays it.
- `lines`: all 1,032 voiced lines once, with speaker id, `duration_s`, the register's §18 family and the alias's delivery note.
- `triggers`: the one table that schedules lines, as `{beat, on, mode, lines, requires_flag}` rows. It covers beat dialogue entries, dialogue beats, boss and duel barks, cinematic subtitles (with `at_ms` on the cinematic's own clock) and the ch05/ch06 bark pools. No line has an absolute start time. Where a script lists a cinematic's subtitles without times (ch05–ch07), the importer spreads them over the cinematic in script order without overlap and marks each row `ext.at_ms_spread`. `requires_flag` holds a conditional line back until its collectible is found or its story flag is set (ch08.b17's returned Washio sword waits for `collectible:ch08.c03`). Events are spelled as the runtime raises them: ch02.b15's boss cues `intro@6.0` … `outro@3.0` become `intro_cinematic` and `outro_cinematic` rows (like ch05.b16's, keeping `ext.at_s` for Sequencer), and ch03's proposals the director now raises lose their prefix (`x_wave_start:N`, `x_boss_defeated`, `x_objective:<id>` → `interact:<id>`, keeping `ext.proposed`).
- `sites`, `checkpoints` (in target centiseconds, with per-phase saves), `unlocks`, `collectibles`, `ui_prompts`, `places` (from the bible's §14 table, each marked `hub` when its row is a bold "**Arena N**") and `layout` (ch01–ch03's volumes, points, splines and patrols in integer centimetres, in each chapter's authored frame; ch04–ch08 have none). The authored layout is kept for the level artists; the runtime plays `space`.
- `space`: the playable layout `scripts/unreal/campaign_space.py` derives by rule from the places, beats and tasks, in integer centimetres in the Unreal world frame (origin at the arena centre, every floor at z 0). See **Chapter spaces** below.
- Carry tasks also carry `carry_speed_permille` (the script's `move_speed_mult`), `carry_weapons` (`katana_one_hand` → the katana, else nothing), and all three `drop_on_hit` values (`easy`, `normal`, `hard`). A uniform authored boolean expands to the same value at each difficulty. The director selects the current setting at beat start, including checkpoint retry and reload; ch02.b05's seed rice drops on a hit only on Hard. An escort's `path_cm` is the length of its road.

`Content/Data/campaign/campaign.json` is hand-authored: the chapter files, the chapter title-card narrative and objective, the three production-site labels, the mechanic flags (with their Japanese and English names) and the story flags in save-bit order, the collectible categories, and bilingual labels for the manufacturing steps and the defended targets the HUD names. `Content/Data/catalog.json` keeps the shared core (classes, weapons, maps, hero) and the 40 dialogue speakers. `SoraArena.Build.cs` stages `Content/Data/...`, which UnrealBuildTool's file filter resolves recursively.

`python3 scripts/unreal/validate_content.py` requires the committed chapter files to equal a fresh build and runs `scripts/unreal/validate_campaign.py`, which checks the bible's §12.3 rules: pacing against §10 (the beats sum to exactly 25,200 s), sites 0–2 once per chapter in `requires` order, weapons 0–20 once each at their §11 beats in §11 order, bosses from §8 each staged by its `bosses.json` fight at its beat, the rival duels `bosses.json` stages fought against their beat's opponent, wave and guard enemy types that are `enemies.json` archetypes (whose roster must be the bible's §7), mutō-dori attacks only where the fight's defeat or finisher allows them, mounted weapons within {0, 18, 19}, registry entries only on production tasks and cargo rides, every line bilingual with a catalog speaker within the subtitle limits, nonlethal enemies never counted toward a defeat count, and at most 360 target seconds between the checkpoints the runtime writes. Rule 8 models the director (`checkpoint_saves`): required beats in order, each checkpoint beat saving as it begins and a boss or duel at each later phase it saves at, on a route that skips the explore beats and on one that opens each cache at the first beat in play once it is available, where opening a checkpointed cache saves again when the active beat can be restored from its start. It also checks that every trigger naming an event the director raises can fire in its beat (`director_event_error`: a crank's `rate_band:in|above|below`, phases within the fight's count, duel events, bouts numbered across the chapter's lesson duels, waves, lesson gates and awase counts, manufacturing steps, pickups, drop-offs, the carried item and `load_NN`, sites, points and collectibles, `intro_cinematic`/`outro_cinematic` only in a boss fight, and no `intro@`/`outro@` or `x_` spelling of them; the sword-bundle pickup also requires the authored recovery pre-step). It also checks line references both ways, blocking dialogue of at most 20 s, collectibles and prompts, the 25 schema-3 cues verbatim, every story flag set by exactly one beat, every conditional line's collectible or flag provided by an earlier find or beat, and that each task has a goal and counts the same lethal opponents as its waves. It checks every chapter's space: zones and road corridors never overlap each other or the arena; every beat's entry, anchor, objectives, pickups, drop-offs, targets, stations, spawns, patrol posts, cache, horse and every loose collectible stand on their zone's floor clear of its walls and cover (in the hub, of the arena's buildings, cover, lantern poles and torii posts, mirrored per map by `campaign_space.arena_blockers`); every volume a beat's events name is placed in its zone; rides and escorts run on roads as long as their scripts say, and an escort walks its whole road; every manufacturing step has its station; horses have rising gait speeds, the katana, yumi and yari only, and a yumi arc to the left; and every mechanic, step and target has a bilingual label. It checks each beat's fieldcraft too: lamps, rubble, hide spots, cell doors and allies on the floor, a climbing face that bars the way wall to wall, allies that join a wave the beat has, a party only on an escort, and volley ranks that are full rows with the volley's arm. Its self-test passes the real data, then must reject 46 mutated variants, among them a lamp in a wall, a face that can be walked around, a volley rank short of a gunner, a boss staged at the wrong beat, a wave of an unknown archetype, a checkpoint beat that no longer saves, a cache whose opening no longer saves (a completist's 510 s gap in chapter one), a boss cue left as `intro@6.0`, an unraised rate band and a bout numbered within its own beat. The glyph check covers every campaign string against the bundled Noto Sans CJK JP font.

## Chapter spaces

`campaign_space.py` lays out each chapter in one world frame:

- **The hub**: the chapter's own arena (Nyaagyu Estate, Lantern Ward, Silk Foundry or Debt Citadel), built by `SoraWorldBuilder.cpp` exactly as the training arena is, when one of the chapter's places is the arena itself. Hub beats use the arena's clear road, its three production sites, its caches, six invader spawns clear of every arena's buildings, nooks for collectibles and two patrol loops. Chapter 4 has no hub.
- **Zones**: a walled floor for every other place, by form (bible §14): halls 36 × 26 m with 7 m walls, yards 44 × 32 m, fields 72 × 52 m; a zone hosting a boss is at least 56 × 42 m. Each has an entry, cover by its long walls where a fight happens, lantern posts in its corners, production sites along its far wall, work spots in its middle, spawns at its edges, two patrol loops, a cache corner and collectible nooks. Estate yards wear the authored four-metre wall module; storehouses, halls, pines, trees and street or alien buildings stand outside the walls as backdrop, so no visual-only prop covers a work spot.
- **Roads**: every ride and escort gets a straight walled corridor 24 m wide with a packed-earth road swaying ±4.5 m inside it, as long as the script says (`route_length_m`, `path_length_m`, or ch01's `spl_ch01_umaba_lane` at 300 m) or as its pace and target time imply. The road's trigger volumes stand at their authored chainage (the ch01 pheasant at 150 m) or spread along it, spawns line its walls, and the exit fills its end.
- Every beat's record gives its zone, its entry (where a travel cut puts the hero), its anchor and points, its volumes (every `volume_enter:` its waves, lines, closing or exit, triggers, scripted spooks and forced-gait stretches name), its exit, spawns, patrols, cache and cinematic camera (a dolly from one mark to another looking at the place), the task's kit (`sluice`, `bellows` or `lift` for a crank by its actor, `hold`, `stations`, `carry` with the item's kind, `defend` with each target's kind, `escort` with its party), and for rides and mounted fights the horse: coat, whether the ride starts in the saddle, the tack to put on first (ch01.b06), gaits and their speeds (chapter-04 §6.5, overridden by a script's own), wind per gait, the gallop lockout, fear radius and recovery, scripted spooks, gait caps along the road and forced-gait volumes, weapons and their arcs, whether the rider may dismount, the phase a mounted fight is dismounted at, and its pack horses (a convoy on the road ahead, or a laden mare on a lead rope).
- Loose collectibles (those no explore cache holds) get a pickup in their place's zone, or beside the road near its start when the hero only passes through the place.

`FSoraCatalog::LoadSpace` (`SoraCatalogSpace.cpp`) reads the block fail-closed: every field typed, point counts equal to the beat's task, an escort's path equal to its road, a cinematic's camera, a dialogue's closing anchor, an explore beat's cache, every weapon arc, and every horse `SoraMountRules::HorseValid` accepts. A collectible must lie in exactly one cache or at one pickup.

## Beat rules

`SoraBeatRules.h` holds the chapter gates (requirements, sites, weapon, mechanic and story-flag unlocks, checkpoints, entry masks) and the beat engine: an `FTask` per beat and the pure functions that play it, in integer milliseconds, centimetres and permille.

| Type | Completion | Advance | Failure and retry |
|---|---|---|---|
| `cinematic` | `duration_s` on its clock, or skipped | `Tick`, `Skip` | a fall returns to the checkpoint |
| `dialogue` | its lines played, then its closing anchor reached when it has one | `FinishLines`, `Reach` | as above |
| `combat_wave` | every wave but a reinforcement released and every lethal opponent down; or its objectives worked; or `survive_s` survived | `ReleaseWaves` (start, prev_cleared, alive_below, after_s, progress_at, then volume and event waves by `ReleaseWave`), `RecordDefeat`, `WorkObjective` | its `fail` rows |
| `duel` | lesson forms (each repeated as often as its gate asks: awase ×2) then bouts, each straight after a 転 flank where the lesson teaches it; first to N points; or the opponent's health to zero, where a duel that is not to the death spares him | `RepeatForm`, `RecordForms`, `RecordFlank`, `ScorePoint`, `OpponentHealth` (phases at their health) | a sparring bout lost is the rival's point; a lost match retries in place (`RetryTask` keeps losses and forms) or, under `continue_after:N`, moves the story on after N losses; a lost lesson bout retries in place |
| `boss` | the boss's health to zero: killed (or broken), spared (disarmed), or yielding and then bound by the hero (a capture) | `OpponentHealth` through each phase, `Capture` | phase checkpoints restore at the phase's health |
| `stealth_zone` | the exit reached, or its objectives worked; its alarms never have to fall | `Travel`, `Reach`, `WorkObjective` | detection follows `on_detected`: combat, a checkpoint restart, or the named reinforcement wave |
| `production_task` hold | the hold's time spent in its volume | `Tick` (contest pauses or decays; work under guard pauses while seen) | its `fail` rows |
| · crank | N turns | `Turn`: faster than the band slips and restarts the rhythm; a slack crank decays for the time past its slowest turn | as above |
| · escort | the party covers its route | `Tick` while the hero stays within reach | a fallen escort (`fail_on_npc_death`) |
| · carry | N deliveries | `Pickup`, `Deliver` (named capacities, or a derived equal ceiling share), `DropCarried` on a hit where the carry drops | as above |
| · manufacture | every step in order | `Stroke`: an off-beat stroke restarts its rhythm step | as above |
| · defend | `duration_s` survived, or the waves cleared | `DamageTarget`, `RepairTarget` | a destroyed target (`fail_on_target_destroyed`) |
| `horseback_ride` | the destination, or every cargo drop-off | `Travel` (ambushes come as the rider passes their mark), `Reach`, `Deliver` after the cargo's authored `unload_hold_ms` | `on_horse_down`: checkpoint or on foot |
| `explore_optional` | its cache opened | `OpenCache` | — |
| `collectible` | picked up | `Find` | — |

Waves are what a beat throws at the hero. Only a fight to clear them (`waves_cleared`) waits for its opponents to fall; any other goal completes its beat at once, and whoever still stands withdraws (they are cleared as the next beat begins): a timed defence on its clock (chapter-02 b06: "the remaining enemies withdraw"), a hold, a crank or an escort when done, a ride at its destination (chapter-08 b02: "completes on entering `vol_outer_koguchi`"), objectives worked, and the ledger copied unseen in chapter six, which has no kill requirement. A completed task no longer moves, so a full crank never slips. A hold's and a crank's decay is worn off in millionths of a unit and the fraction carried to the next step (`Decay`), so the same slack costs the same progress at any frame rate, as a siege's damage does. `TaskCheckpointValid` allows a phase checkpoint only in a boss, or a duel fought to its end, below its phase count. `TasksValid` refuses a chapter that does not open on a cinematic, an optional beat that is not an explore beat, or a required explore beat.

Run `python3 scripts/unreal/test_campaign_progression.py` from the repository root. It generates a temporary C++ fixture of every beat's gates and task and the §11 unlock order, and compiles `campaign_progression_driver.cpp` (C++17, `-Wall -Wextra -Werror -pedantic`) against `SoraBeatRules.h`, `SoraCampaignRules.h` and `SoraDojoRules.h`. The script also requires `SoraCampaignDirector.cpp` to call the tested rules and `SoraCatalog.cpp` to refuse chapters by `ChapterValid` and `TasksValid`. The driver:

- runs every beat type's completion, advance, failure, retry and checkpoint rules on hand-made tasks, and the parameters `TaskValid` must refuse; among them a timed defence, combat objectives and a ride that end with opponents standing, a crank turned full while its wave stands (it completes and never slips), spared and captured opponents, awase ×2 and 転 bouts;
- wears a hold's and a crank's decay at 1, 2, 3, 4, 7, 8, 16, 17, 33, 50, 250 and 1,000 ms frames and requires the same loss every time (48-turn crank at 1% a second: 4,800 thousandths over ten seconds of slack);
- plays every one of the 133 authored tasks to completion as a hero who does everything right (so no authored wave or goal can deadlock), and again as a hero who fights nobody, which every goal but a fight's must still complete; and restores each phase checkpoint and plays it out;
- puts every authored task through a fall, its `fail` rows, lost matches, detection and a lost horse;
- plays every chapter twice, skipping or playing the optional beats, checking gates, checkpoints and forged saves (an unearned site, weapon, mechanic or story flag, a beat saved without its requirements, a premature completion), and the carried entry masks between chapters;
- requires the completist to hold every weapon at its §11 beat in §11 order and the skipper to differ only by the optional pickup the ch07.b01 grant restores; both end with all 21 weapons and 19 mechanics, the completist with the story flag;
- keeps the chapter-advance, collectibles, training-arena and chapter-one dojo lesson tests.

`SoraBeatRules::SiegeDamage` wears a defended target down by `SiegeHpPerSecond` (5) for every opponent within `SiegeRadiusCm` (7 m), carried in whole opponent-milliseconds so no frame loses a fraction. `SoraMountRules.h` is the horseback rule set: with the legs on (W) a halted horse walks on and holds her gait; urging (Shift) asks for the next gait every 700 ms up to the ride's fastest, the road's cap and a walk while she is spooked; gathered reins (S) drop a gait every 400 ms; left alone she eases a gait every 1.5 s. Wind rises or falls per gait each second; a gallop below 20 locks her into a canter until she recovers 50. A spook forces a walk for the ride's recovery time. `CanMount` accepts a rider only at her right flank (40–220 cm to her right, within 140 cm of the saddle), `AtLeftFlank` names the refused side, and `ArcAllows` lets the katana, yumi and yari act only in their arcs of her heading (yumi −170°…+15°, katana +30°…+150°, yari −10°…+60° unless the script sets its own); nothing else acts from the saddle.

The driver also runs the siege's whole-point carry and the carry pace and loadout rules, every mount rule (walk on, urging steps and ceilings, reins, easing, spooks, forced walks, the gallop's wind and lockout, the right-side mount, the arcs and the invalid horses `HorseValid` refuses), and rides every authored route at its best pace through its gait caps. A route must be ridden to its end within its target time, or within half as long again where the script's own route length outruns its pacing estimate; it prints each overrun (ch02.b10: 133 s against 120 s; ch02.b13: 127 s against 90 s).

Fifteen mutations of the rules (no stalled-field release, hurried crank turns counting, no concession after the last loss, flags not earned, reinforcements required, phases off their health, rhythm never missing, retries forgetting losses, any detection restarting, every goal waiting for its waves, decay losing each frame's fraction, a crank slipping for the whole frame, a capture needing no hand, one awase learning the form, bouts scoring without 転) each fail the driver.

## Unreal runtime (schema 4, save schema 6)

`FSoraCatalog::Load` reads `catalog.json`, `campaign/campaign.json` and the eight chapter files and fails closed: a missing or mistyped field, an unknown speaker, line, beat, mechanic, story flag or collectible category, a task that `TaskValid` refuses, a chapter that `ChapterValid` or `TasksValid` refuses, a subtitle outside a cinematic, a conditional line naming an unknown collectible or flag, or checkpoint rows that disagree with a beat leave the catalog unloaded with the reason in `FSoraCatalog::Error`. Every route through the eight chapters must end with all 21 weapons and all 19 mechanics.

`ASoraWorldBuilder::Build` builds a chapter from its space (`SoraWorldBuilderLayout.cpp`, `SoraWorldBuilderLayoutZones.cpp`): the hub arena (its own sites left out), every zone and road with floors, walls, cover and dressing, the chapter's lighting, and the three production sites at their space's positions with their kind's structure. `PlayerStart` is the first beat's entry. The training arena is built as before, and kernel practice keeps its own map.

`USoraCampaignDirector` plays each chapter's beats in the order `SoraBeatRules` allows and each beat's task through the same functions (`SoraCampaignDirector.cpp`), with its world-facing play in `SoraCampaignDirectorWorld.cpp`. It keeps an integer beat clock. When a beat starts in another place than the hero, a travel cut (a short fade) puts him at its entry; rides and escorts start on their road. The hero entering a trigger volume raises its event once per beat: its lines play, a dialogue waiting on it starts, the waves it names come, and on a ride a scripted spook startles the horse. Waves spawn at the beat's spawns (on a road, the ones 25–65 m ahead of the hero) up to `max_alive`; guards (of a stealth zone, or of a production task under guard) stand at their patrol route's start, and the route goes to the archetype's own brain. The director keys its opponents' waves and the horse's fears by weak pointer and drops a fallen opponent's entries, so an opponent built later at a freed address never inherits them. When an encounter ends (a beat's end, a restored checkpoint, a chapter change or practice), every opponent it put on the field leaves with it: the standing, a knocked-down conscript (whose collar would otherwise drag it up untracked) and a guard's body, knocked out or killed; a combat wave's fallen leave after their short lifespan. `Travel` tracks the way to an exit along the road, or across the zone. A gold beacon marks the active point: the next objective, pickup or drop-off, the current step's station, the defended position, the escorted party, the next wave's volume, the exit, or a yielded boss to capture. E works the nearest point within reach (from the saddle, 4.2 m), then a loose collectible or an explore cache, then the horse. Explore caches stand as an unmarked chest and a lantern glow; the objective refreshes whenever progress moves, and caches already standing where they are offered are left as they are.

The task kits (`SoraWorldBuilderLayoutTasks.cpp`) show each production task as it goes: a sluice winch whose drum turns while the weir board lifts and the water rises in its channel; bellows whose furnace mouth glows brighter (with its light); an override wheel or capstan lifting a platform of goods; a ring on the ground that fills as ground is held (red while contested); a bench per manufacturing station, the current step's in gold and finished ones in teal, with the output stacking beside it; loads at each pickup (a pack horse, or a stack that empties) and what each drop-off has received; each defended target (pack horse, furnace, aid tent or villager) with a banner that pales to red as it is worn down; and the escorted party (villagers on the samurai cat rig, walking or standing, and ch04's ox cart) walking the road where the rules put them. A carried load slows the hero to its pace (no sprint), shows in his arms and leaves at most the katana in hand; other weapons are refused with a notice. Opponents standing at a defended target wear it down (`SiegeDamage`), and a destroyed target fails the defence to its checkpoint. Loose collectibles lie in their zones as small period objects with a faint glow; picking one up goes to the codex and the save at once.

Horses (`ASoraHorse`, `SoraHorse.cpp`) are native Japanese horses about 130 cm at the withers with period tack: a lacquered kura on front and rear arches, aori flaps, the girth, broad abumi on both sides with the SORA mon on their front plates, the bit, headstall, cloth tazuna and crupper; pack horses carry a 荷鞍 with two loads. Their body is a primitive proxy in the coat's colour (chestnut Kurimaru, bay pack horses): no horse mesh is imported into `Content/Generated`, only the source-only anatomy study. Legs swing in each gait's footfall order as placeholders for an equine animator's cycles. A ride's horse waits at the road's start: ch01.b06's stands bare, and E at her side puts on the kura, girth, abumi and bit in order, the bit refused twice until she has her barley; E at her right flank mounts, at her left is refused with a notice. The other rides and ch04.b16's mounted first phase start in the saddle. Ridden, she follows `SoraMountRules`: the rider's MoveForward, Sprint and MoveRight set gait and steering, auto-steer keeps her on the road while the rider leaves the reins alone, the road's walk and forced-gait stretches cap her, an opponent entering her fear radius or a spook volume spooks her, and her frame sweeps against walls. The rider sits with his eye 225 cm above the ground and dismounts to her right (her left only against a wall). From the saddle the yumi draws only to the left, the katana cuts and the yari thrusts only in their arcs, and a matchlock cannot be taken up. A convoy walks the road ahead at its pace and waits when its rider is 25 m away; a laden pack mare follows on her lead rope. A mounted fight's rider comes down as its dismounted phase begins, and a ride ends with the rider on the ground.

Cinematics play behind the letterboxed card with their subtitles on the card's clock, through a camera that blends in from the hero's eye and dollies over the beat's place; Enter skips them and the view blends back.

Who takes the field sits behind four functions, wired at the 2026-09-26 merge to the AI lane: `SpawnWaveOpponent(Type, …)` builds the `enemies.json` archetype (a sparring beat keeps the chapter-one pupil), `SpawnStealthGuard(Type, …)` builds the archetype on its space's patrol route, unaware, `SpawnDuelOpponent(Npc, …)` builds the rival duel `bosses.json` stages at the beat (Toranosuke's fukuro-shinai and steel duels; the dojo's other bouts are pupils), and `SpawnBoss(BossId, …)` builds the `bosses.json` boss on the settings' difficulty at its restored phase. Debt-bound conscripts spawn beside their wave without counting toward it; a lethal blow knocks one down, and once `seal_cut` is in play Interact held beside it for its archetype's hold time cuts the seal. A beat teaches its weapons and mechanics while it is in play (`SoraBeatRules::InPlayWeapons`, `InPlayMechanics`) and keeps them when it completes: ch02.b03's yari is in hand from its start, and ch03.b03's rear takedowns and seal cut work in that beat. A cache's weapons come only when it is opened, and a grant that makes up for a skipped cache (ch07.b01's phantom SMG) arrives as its beat completes. A stealth beat opens `USoraStealth`'s zone on the settings' difficulty with its `on_detected` answer; the zone's detection, alarm and found bodies reach the beat as `alert_state:alert`, `ai_event:alarm_raised` and `ai_event:body_found`. Work under guard (a production task with `stealth: true`: ch03.b05's deliveries, ch05.b03's escort, ch06.b08's hold) opens the zone too, and `build_campaign_data.py` posts its patrolling wave members and `x_guards` as the zone's guards rather than hunters. A hold or an escort under guard pauses only while a guard sees the hero or is alarmed (`USoraStealth::IsWorkPaused`), and goes on once none does; a guarded carry answers a detection with a fight and a dropped load.

A boss or a duel fought to its end ends as its script says. At zero health a killed boss falls (and a boss broken at its weak points collapses); a disarmed boss (ch07.b13) and a duellist who is not fought to the death (ch06.b09) are spared: they yield upright where they stand and the fight ends; a captured boss (ch06.b13, ch08.b14, bible §3.2's "captured, not killed") yields upright, stays, becomes the objective, and the fight ends only when the hero binds it with E, which raises the capture's own interaction (`interact:bulkhead_lever`, `interact:engine_spine`). `SparesOpponent` and `IsCaptive` tell `ASoraEnemy::OnDefeated` which. One blow that carries an opponent past several phase thresholds plays every phase it passes, in order (its lines and a duel's scripted event), and saves at the last one the fight saves at; a killing blow plays the phases it passes before the fall.

Chapter one's lessons follow their gates: a form wanting repetitions is learned on its last clean one (ch01.b03's second awase, each named `awase_success:N`; a guard held too long is `awase_fail:early`, one raised just after the pupil's cut `awase_fail:late`), then the lesson's scored bouts (ch01.b03's two, from `x_scored_bouts`). ch01.b04's bouts score only straight after a 転 flank, which the combat lane reports through `USoraGameEvents::OnMarobashi` (an awase left without it draws `marobashi_miss`; a bout won without it scores nothing and a fresh pupil steps in). Bouts are numbered across the chapter's lesson duels (`bout_start:N`, `bout_scored:N`: ch01.b04 scores bouts 3 and 4).

Failures follow the task: a fall in a sparring match is the rival's point, a lost match or lesson bout restarts in place, the last allowed loss moves the story on, and anything else shows the result screen and returns to the latest checkpoint with Enter. `RaiseBeatEvent(FName)` is how the world reports to the beat: it plays the event's lines, releases the waves it names, and applies the failure it raises (`alert_state:alert` or `:combat` is detection, `npc_died:<id>` an escort down, `convoy_member_*` a lost convoy, `target_destroyed:*`, `horse_down`, or the beat's exact `fail` rows such as `boss_event:mill_seal_3`). `DamageDefendedTarget` damages a defended target and fails the beat when it is destroyed. A hit on the hero drops a carried load where the carry says so.

The story HUD (`SoraHUDStoryPanels.cpp`) shows the chapter's title card before its opening cinematic, then the letterboxed frame with the beat title and subtitles. In play, a tracker at the top right names the beat (its number among the chapter's required beats and its title in both languages) and its task: progress with a bar, a hold's seconds and whether the hero has left the ground, a crank slipping, the escorted party waiting, a load being carried, the manufacturing steps done, now and next, each defended target's health, and on a ride the horse's gait (常歩, 速歩, 駈歩, 襲歩), pace and wind, a spook, and what E does (the next tack piece, mounting from her right, dismounting). Beneath it, story notices name each unlocked weapon and mechanic, each find with its codex text and each restored site. The E hints for work, caches and pickups are bilingual. A beat's HUD prompts name keys only as `{Action}` tokens for `DefaultInput.ini` actions, which the HUD replaces with the player's own keys (`SoraHUDPanels::KeyPrompt`), so they follow the device and rebinding; `validate_campaign.py` refuses any other token and any control named in brackets. The result screen's headline is bilingual: the dojo's training complete for chapter one, a district liberated for the chapters after it, Nyaagyu liberated at the end, and a fall, the training arena and practice each their own.

Dialogue is keyed by events. `FireDialogueTrigger(FName)` plays the rows an event keys in the active beat and the chapter's bark pools, and shows its HUD prompt. The director raises `beat_start`, `beat_complete`, `subtitle`, `boss_phase:N`, `duel_phase:N`, `duel_event:<id>`, `site_restored:N`, `player_died`, `point:player`/`point:rival`, `bout_scored:N`, `duel_won`, `match_lost`, `loss_continue`, `boss_defeated`, `gate_complete:<gate>`, `progress_at:X`, `idle_s:N`, `wave_start:N`, `wave_spawned[:N|:<id>]`, `interact:<id>`, `interact_start`, `item_picked:<id>` and `:<item>`, `item_delivered:<id>` (which also releases the waves waiting on it), `:<item>` and `:load_NN`, `item_dropped`, `intro_cinematic` as a boss fight opens and `outro_cinematic` as it ends, `gate_start:<gate>`, `awase_success:N`, `awase_fail:early|late`, `bout_start:N`, `marobashi_miss`, the capture's interaction, the tack-up's `interact:<piece>`, `interact_refused:<piece>:N` and `item_given:<gift>`, `mount`, `dismount`, `horse_spooked`, `rate_band:in|above|below` (a turn refused on a full crank raises nothing), `event:crank_turn_N`, `crank_released`, `step_start:<kind>`, `step_complete:<kind>:<n>`, `step_failed:<kind>`, `output_complete`, `target_hp_below:<actor>:<x>`, `lines_done:<line>`, `exit_reached`, the beat's own volume, interact and closing events, `collectible:<id>`, `collectible_found:<id>` and `chapter_complete`. The first time a beat raises an event, its `<event>:first` rows play too (ch05.b06's `rate_band:in:first`, ch01.b11's `point:rival:first`). Lines never repeat unless repeatable; repeatable rows wait out their `cooldown_s`; conditional rows wait for their find or flag. The queue plays each line for its `duration_s`; `QueuedSubtitles()` gives the queue with the speaker's Japanese and English names, the Japanese line and the English subtitle. `USoraGameEvents` announces `OnBeatStarted`, `OnBeatCompleted` and `OnBeatFailed`, and each beat event appends a JSON line (with the save slot, the beat clock, progress, count done and losses) to `Saved/Telemetry/campaign_beats.jsonl`: a beat's `start`, `resume`, `phase`, `skip`, `setback`, `retry`, `conceded`, `failed` and `complete`, an opened cache's own `complete`, and `chapter_complete`.

`USoraSaveGame` schema 6 holds the chapter, the reach, the unlocks and story flags held when the chapter began, the 48-bit collectibles mask and the checkpoint: the beat (or boss or duel phase) it starts, the beats done and the sites, weapons, mechanics, story flags and dojo forms they earned, or a finished chapter at its result. `LoadSave` starts a fresh campaign for any other schema (no schema-5 decoder), a chapter beyond the reach, entry unlocks outside `EntryValid`, story flags no earlier chapter sets, or collectibles from an unreached chapter; `ResetRound` replays the chapter from its opening when the checkpoint fails `CheckpointValid`, `ProgressValid` or `TaskCheckpointValid`, or its dojo forms differ from those taught. An optional find is kept at once. Opening a cache that checkpoints saves a checkpoint then and there when the active beat can be restored from where play stands (its start, or a boss or duel phase it saves at), so the cache's weapons and story flag are saved with it; otherwise its completion reaches the next checkpoint. A checkpoint's dojo forms are always those its completed lesson duels taught. Chapter advance carries the route's unlocks and flags forward; chapter select grants every unlock and flag the earlier chapters offer; New Campaign clears them. Nyaakoto's equipment refuses a weapon the campaign has not unlocked and the beat in play does not hand over, with a bilingual notice; the training arena lends every arm.

## In-editor acceptance

`scripts/toolchain/run-automation-mac.sh SoraArena` runs these campaign tests in real game worlds with isolated save slots:

- `SoraArena.Campaign.Playthrough` plays every beat of all eight chapters (133: the 125 required beats and the 8 optional caches) through Enter, E, the hero's position (or his horse's) and lethal damage, and records how many beats of each task goal it played; every goal the chapters author (15, the cache included) must be played. Every beat must start with the hero in its place, every cinematic (30) must play through its camera and give the view back, every ride (7) must be ridden, ch01.b06's horse tacked up (six presses: the bit twice refused), refused from her left and mounted from her right, and every rider down at the destination. Each crank's sluice or lift gauge must rise with its first turn, the first load must slow the hero to its pace, show in his arms and refuse the yumi, and nothing is worked from afar. Every chapter opens its cache (whose weapons and story flags must not be held before it) and picks up every loose collectible (28); each find reaches the disk save at once, and each of the seven caches that checkpoint writes a checkpoint with its beat done (ch08.b12's, which does not, writes none).
  - Waves and endings: every crank is turned, not fought over, and must end the moment it is full with its waves still standing (none following into the next beat); ch02.b08's drones and ch08.b02's ambushes must come as the rider passes their marks, and each ride must end at its destination with them standing. Every boss and duel fought to its end must end as its script says: a killed boss falls, a disarmed or spared opponent yields upright; ch06.b13's and ch08.b14's bosses must yield upright, stay past a fallen opponent's lifespan, be the objective, refuse E from afar and be bound by E beside them. The first in-band turn plays ch05.b06's `rate_band:in:first` line; each boss's intro lines play as it opens and its outro lines as it ends. ch01.b03's awase form is learned on its second repetition and its two scored bouts follow; in ch01.b04 an awase left without 転 draws the master's hint, a bout won without the flank scores nothing and a fresh pupil steps in, and each flanked bout scores, numbered across the dojo (`bout_scored:3`). A fallen stealth guard must stay down where it fell, off its patrol.
  - Phases: in a fresh world seeded at ch07.b13 one blow from full health to a quarter carries the gunslinger past both thresholds: both phases' lines must play in order and the last phase must save; a single killing blow from full health plays both phases' lines before her fall, and she yields upright.
  - Saves and reloads: it reads the disk save back at every checkpoint beat, boss or duel phase and checkpointing cache it reaches (120). In every chapter, the first checkpoint of each task goal past the opening (61) is restored in a fresh world (the old one torn down), and so is every boss and duel phase checkpoint (13: each opponent is struck into the phase and returns at that phase's health). Each restore must match the beat, phase, beats done, sites, weapons, mechanics, story flags, dojo forms, collectibles, the loose finds and caches still waiting and the hero's place, and play goes on from it. The chapter's result must show every beat done (the cache too) and every collectible of the chapter saved; each advance carries the route's unlocks, flags and finds forward; and the liberated city must reload with all 48 collectibles kept and saved.
  - Failure paths: two rival points and a lost sparring match retried in place (ch01.b11); an invader standing at a pack horse wearing it down, a repair making it whole, and a wounded then destroyed pack horse failing its defence to the checkpoint (ch02.b06); a defeat retried (ch03.b08); a stealth alarm calling its reinforcements (ch05.b02). A hurried crank turn slips, an off-beat stroke restarts its rhythm and holds fill only with the hero in them.
  - Unlocks: nothing may be held before the beat that unlocks it completes; the 21 weapons and 19 mechanics must arrive in the order the chapter files author them (for the weapons, the §11 order `validate_campaign.py` checks against the bible), the vault armory's phantom SMG from its cache; each arm Nyaakoto can hold that unlocks after the dojo (yari, naginata, arc carbine, monofilament naginata) is refused with a notice before its beat and equips from its beat on (the yari in ch02.b03 itself, before the beat completes); the dojo's yumi and the foundry's arc carbine are carried into later chapters; the flagship's name board sets its story flag, which is saved and carried into the final chapter; and the campaign ends with all 21 weapons and 19 mechanics. A second route enters the flagship from a save without the phantom SMG (the only optional weapon before it): the save is accepted and the war council's opening grants it beside the repeater, with a notice.
  - Telemetry: the run's rows in `campaign_beats.jsonl` (393 after the post-merge fixes, filtered by the test's save slot) must show every one of the 133 beats completed exactly once, each required beat started once, every cinematic skipped, both failures, the in-place retry, and one `resume` for each restored checkpoint and failure (76). The totals (events, each chapter's beat clock, caches, pickups, rides, cinematics, lines, checkpoints read, reloads and worlds) are logged as `SORA_CAMPAIGN_TELEMETRY` and `SORA_CAMPAIGN_PLAYTHROUGH_OK` and written to `Saved/Telemetry/campaign_playthrough_totals.json`. The beat clock there is the automation's compressed time (dialogue and journeys at half a second a frame, cinematics skipped), not a pacing measurement.
- `SoraArena.Campaign.Spaces` builds every chapter's space in a real world and checks that a trace down meets a floor at z 0 and a standing cat's capsule fits at every zone entry and road node and at every beat's entry, anchor, points, spawns, patrol posts, cache and horse, every trigger volume, exit and closing anchor, and every loose collectible (2,775 points), that each production site stands on its base, and that the hero begins at the first beat's entry. It also shows each chapter's caches, asks for the same ones eight times more and requires the very same chest glows (nothing rebuilt), then none (they leave).
- `SoraArena.Campaign.Mount` rides through the player's keys: ch01.b06's tack-up, the refusal from her left and the mount from her right with the rider's eye above her back; W walking her on at 160 cm/s, the lane's walk-only stretch holding her to a walk, Shift trotting her at 360 cm/s on the trotting stretch and never past it, auto-steer keeping her on the road, easing to a walk and a halt, the pheasant spooking her, no weapon in the saddle, and the rider on the ground at the range when the ride ends. At ch02.b08 the yumi draws only to the left and the katana cuts only to the right, the convoy walks at 450 cm/s and waits for a rider far ahead, the road's drones come as the rider gallops past their marks (his arrows bring each down before it can frighten her), and the gallop at 850 cm/s winds her into a canter below 20. At ch08.b02 the arc carbine cannot be held in the saddle and the yari thrusts forward. At ch04.b14 Bunta follows on her rope; at ch04.b16 the assessor engine's second phase is fought on foot.
- `SoraArena.Campaign.ForgedSaves` writes three valid checkpoints and fourteen forgeries (including a story flag no earlier chapter sets and an unearned flag at the checkpoint) and checks what a real world restores from each.
- `SoraArena.Campaign.SaveRoundTrip` and `SoraArena.Campaign.DiskSaveRecovery` round-trip schema-6 checkpoints, story flags included, through memory and disk.
- `SoraArena.Campaign.ChapterTitleCard`, `CombatTrace`, `DeterministicEnemyFire`, `SoraArena.Events.ScriptedFight` and the menu tests seed schema-6 checkpoints with `USoraCampaignDirector::SeedCheckpoint`. The traced yard fight runs at ch05.b05 against its enemies.json blade retainers; the traced dojo learns stance, guard, awase twice (answered from the pupil's windup) and recovery through real Block and Fire presses and wins ch01.b03's two bouts, opening the 転 lesson; and the traced final fight takes Val Amort's cane by mutō-dori, binds him with E and carries the registry from its pickup to the notice board.

Eight director mutations each fail the playthrough: no wave release after progress, every failure sent to the checkpoint, story flags not saved, the crank's band ignored, an opened cache leaving no telemetry row ("ch01.b08 completes once in the telemetry"), a restored checkpoint dropping the collectibles ("Reloaded Chapter 1 ch01.b06: collectibles"), a restored phase putting the boss back at full health ("ch02.b15 phase 2: the opponent returns at the phase's health"), and a beat's weapons unlocked as it starts ("ch01.b06 unlocks exactly its own weapons"). Eight more each fail the test that must catch them: mounting from either side, gait caps ignored and mounted arcs ignored (`SoraArena.Campaign.Mount`); and no travel cut, a load that does not slow the hero, no siege, no cinematic camera and trigger volumes that never fire (`SoraArena.Campaign.Playthrough`). Eleven more, one per review fix, each fail the test that must catch them: a checkpointing cache that only keeps its find ("ch01.b09 checkpoint: beats done"), a blow through two thresholds playing only the last phase ("ch07.b13, struck past two thresholds"), a spared opponent felled ("ch06.b09: the opponent is spared, not felled"), a captive leaving on a fallen opponent's lifespan, no `:first` rows ("ch05.b06.kozo.004 plays on the first turn in the band"), no boss intro, a fallen guard keeping its patrol, bouts numbered within their beat, one awase learning the form, the director deaf to 転 (`SoraArena.Campaign.Playthrough`), and standing caches rebuilt on every refresh (`SoraArena.Campaign.Spaces`). The whole module also builds with every source in unity blobs (`-DisableAdaptiveUnity`).

## Arms and fieldcraft

The opening distance lesson (`ch01.b02`) now retains its authored `x_maai`
contract in the task data. Holding stance alone does not restore site 0.
Nyaakoto first faces Sekireisai within 166–224 cm for a continuous 500 ms;
Sekireisai then steps back 120 cm, left 150 cm and forward 80 cm, each followed
by another measured 500 ms acquisition. He does not attack or close the gap
for the player. Turning away (facing dot below 0.70) or leaving the band resets
the hold. The moon ring is available at every difficulty; Easy adds distance,
and six seconds without a confirmed acquisition shows the floor band. The
authored step, completion and too-close lines are raised. A reload during the
lesson restores its existing beat-start checkpoint, requiring stance and all
three steps again; the following beat's checkpoint retains the completed
lesson. `SoraArena.Campaign.Maai` exercises movement keys, boundary/facing
refusals, the three mentor movements, help, lines and fresh-world reloads;
`Playthrough` and `CombatTrace` also walk the gate. The directed maai test and
the complete 133-beat playthrough passed in the October 18 integration runs;
this is engine behavior evidence, not rendered or packaged qualification.

Every arm the campaign hands over is in reach (`SoraArmsRules.h`): keys 1–6 take up the six groups (swords, polearms, the bow, firearms, chain and striking arms, explosives and support), a second press steps within a group, the mouse wheel steps the ring, and the arms wheel (X / RB) steps on a tap and, held, opens a radial wheel of every held arm while the world slows. Each beat's space carries a `fieldcraft` block (`campaign_fieldcraft.py`, read fail-closed by `SoraCatalogSpace.cpp`, checked by `validate_campaign.py`): its lamps and fires, footstep floors, water, climbing face, tsubute stones, carried candle, escorted party with its hide spots and cell doors, allies, defended people and volley ranks. `USoraFieldcraft` plays it with `SoraFieldcraftRules.h` and reports to the beat through `RaiseBeatEvent`: a held Interact snuffs a lamp, raises the downed, cuts a collar or opens a cell; Ability signals an escorted party, marks and orders a volley, or throws a stone; Jump climbs, lets go or vaults; the escorted and allies are `ASoraCompanion` characters who walk, fight, go down, are raised by hand or by the healing lance, and die past their window, failing an escort. The events the scripts key on (`look_at:*`, `npc_downed:*`, `npc_revived:*`, `npc_freed:*`, `blocking_end`, `alert_state:*`, the climb's volumes, `lure_triggered`, `signal:*`, `event:volley_*` and the rest) are raised, so their prompts and rows play. `SoraArena.Fieldcraft.*` covers each in a real beat world.

The chapters' scripted sets are staged from the same block (`SoraFieldcraftNets.cpp`, `SoraFieldcraftWatch.cpp`, `SoraFieldcraftCharge.cpp`). Each stealth zone and all guarded work read their authored detection, takedown and body rules, and each guard its authored senses and watch (`guard_row`, `stealth_block`); a detection in ch03.b02 warns ch03.b03's guards. Drones net ch02.b08's pack horses, ch04.b10's ox cart and ch04.b12's planters: a net halts the string or the cart, is cut by a held Interact (or from the saddle with the ride's blade), falls slack with its tether drone, and left too long loses the load (`convoy_member_seized`) or the planter, the defence failing at its third loss. A load freed is let be for 9 s while a cut net's drone reloads; two of ch02.b08's three ravine drones net, and past 1 020 m one of G4's crosses to the string's right (`ai:drone_crossed_right`). A net that catches the rider throws him (`horse_down`), and his whistle brings the horse back. ch06.b02's searchlights sweep the moat and raise the alarm on a head in the spot (not a diver, nor a head under the lotus), and ch02.b08's ship light frightens the horses. ch07.b04's bell draws the calm guards once, ch03.b14's cook-fires gutter and hold the kitchen until relit, ch03's ladders reach the board roofs (a drop is heard as far as its roof's script says, unless it lands on straw), ch03.b05's crates are hoisted with a held Interact that waits while a guard watches, and held objectives (ch03.b10, ch06.b04, ch06.b11) are worked with Interact held. Each volley leaves a 4 s smoke bank that hides the lane from both sides but stops no round, arrow or blade, Easy's ranks may order themselves (a setting), and in ch08.b02 twenty League riders and Toranosuke charge beside the hero while he breaks the seal stakes. The thirteen tests in `SoraFieldcraftSetsAutomation.cpp` and the playthrough cover them.

### Chapter two: the seed-rice seal and set-down

The authored `x_gate_interact` now gates ch02.b05's carry with a three-second hold at `seal_kura_sw`, using the yari's iron butt. Pickup and delivery are refused before it opens. Work pauses on a damage event or combat stagger and retains partial work when Interact is released or the player leaves; checkpoint retry resets it. First contact raises the authored notice bark. The existing pickup spot also holds the seal, and the seal tutorial volume now covers that spot. The clamp is a non-colliding gameplay proxy; a granary door, flickering ledger numerals, SORA-plaque reveal and pry animation remain art work.

Interact while carrying delivers at a drop-off with space; elsewhere on a walkable floor it sets down the load at the player's feet. The loose load remains visible and can be picked up again. Loose loads count against the store's remaining stock, so putting down all four bales does not create more. Damage-induced drops retain the existing return-to-source behavior, including after picking up a loose load. Beat-start retry/reload clears partial seal work, loose loads and deliveries; no mid-beat save format was added. Carry and loose-load shapes still need final art and animation.

`test_carry_work_data.py`, the carry-difficulty data test and the host progression driver pass: they cover seal timing, hit/release/leave pauses, checkpoint reset, distinct/store pickups and loose-load conservation through pickup, hit and delivery. `SoraArena.Campaign.CarrySealAndSetDown`, `CarryDifficulty` and the complete playthrough perform the seal with real movement and held input. All three passed at `16b7762` and again in the 62-test campaign/fieldcraft/Connect suite at `56b95f3`, with zero reported errors or warnings. No rendered or packaged acceptance is claimed.

The carry's optional `x_dropoff_capacity` is now preserved by name as normalized `task.dropoff_capacity`, retained in the catalog, and aligned with the drop-off indices used by the rules. The authored ch02.b05 capacities remain two bales per pack horse. Missing, extra or wrong names, non-integer or out-of-range capacities, and totals unable to hold all goods are refused; an absent map keeps the existing ceiling-share behavior. Delivery, Interact targeting and the objective marker use the same per-destination room check. Beat-start checkpoint retry clears occupancy and loose goods while retaining the task's capacities; horseback cargo still delivers one load to each destination.

The host data tests and progression driver cover an asymmetric one/three map, reversed dictionary order, malformed keys and counts, refusal at a full destination without consuming the carried load, source/loose-load conservation through set-down and hit return, spare destination capacity without extra goods, and checkpoint reset. All 133 authored tasks still pass host progression. Unreal catalog loading, physical interaction/objective routing, and packaged acceptance of this capacity change remain pending.

### Chapter three: the dry-well equipment recovery

`x_loadout` now restricts chapter three's opening through ch03.b05 to the wakizashi even when chapter select or earlier chapters unlocked other arms. Selecting or firing the katana, yumi, polearms or firearms is denied. The carry pre-step is mandatory: neither hoisting nor delivery progress can bypass it. A real 340 cm square opening, collision lining and floor form a 700 cm shaft; normal movement reaches its rope, held Interact sweeps the capsule down or up at 140 cm/s, and releasing holds safely at the current position. Interact at the bottom requires three uninterrupted seconds to string the bow; releasing or leaving the bundle resets that work. Completion restores the katana in hand, the bow and twelve arrows, removes the bundle, and raises `item_picked:sword_bundle` once. Nyaakoto's omitted line plays on that event and Kohagi's follows after the authored four seconds. `x_delay_s` is now normalized to the director's delayed-event form (also preserving ch03.b07's six-second line delay).

The existing checkpoint contract remains beat-start: reloading ch03.b05 repeats the retrieval and restores the wakizashi restriction; the next beat's checkpoint retains the recovered loadout. The well has a cover outside its active beat so later visits cannot strand a player below an inactive interaction. The separate saya and fallback quiver hide while equipment is unavailable; the authored skeletal hero's embedded ebira still needs separable art to hide with them. The shaft, rope, bundle and bow bag are gameplay support shapes. The braced stringing and rope-climb animation, wet well art, and placing c03's scroll fragment in the well lining remain art/layout work.

Host `test_campaign_progression.py` covers equipment permissions, refusal to hoist early, continuous stringing, one-time completion, malformed contracts and checkpoint reset. `test_recovery_data.py` covers exact authored parameters, restriction boundaries, placement and the two raised lines with their delay. These host checks and content/localization validation pass. `SoraArena.Campaign.EquipmentRecovery` performs actual W/Interact movement, interrupted/resumed descent, exact depth, timed stringing, delayed dialogue, ascent and fresh-world checkpoint reload assertions. The full campaign playthrough uses the same real-input retrieval before hoisting. The October 18 integration run passed these tests and all 133 campaign beats; the end-play cleanup removed the earlier teardown warnings without suppressing them. This does not establish rendered or packaged acceptance.

## What the offline runtime does not do yet

These wait for other lanes or later steps and are not claimed:

- The stealth beats' authored patrol routes: guards walk the space's derived patrol loops (a posted guard keeps the first point of its loop), not the chapters' named routes, until the level art places them.
- The playthrough strikes bosses and duellists to their phase thresholds with lethal damage and binds captives with E; it does not fight their counterplay (shields, weak points, floors, mutō-dori), which `SoraArena.Boss.*` and the combat trace's Val Amort check. A siege needs no targeting AI (opponents who come within 7 m of a target wear it down). A capture's interaction is worked at the yielded boss, not at a bulkhead lever or the engine's spine, until the level art places them.
- A horse mesh and animation: no horse is imported into `Content/Generated`, so every horse is the primitive proxy with period tack described above; the lateral amble and every gait cycle need an equine animator. The ch08 charge's League riders and Toranosuke are the same proxies, each with a rider built from primitives. A ride steers itself only while the player's auto-steer setting is on.
- ch04's ox cart is still a prop at the head of the party (its net and health are the fieldcraft's), and defended pack horses, furnaces and aid tents stay targets rather than characters; repairs mend a quarter of the worst-hit target. Nets, searchlights, the bell, cook-fires, ladders, roofs, stakes and smoke banks are engine shapes; the static ones wear the environment palette's CC0 PBR surfaces (timber, stone, metal, plaster), the net and the smoke bank a flat colour until the VFX lane's systems are wired in.
- Cooperative cranks in ch04.b06, ch05.b06 and ch07.b07 are implemented with visible helpers, authored contribution rates, the bellows boy's net/free interaction, Kohagi's five-metre retreat to existing cover, and 25/50/75% ratchets. The host tests cover exact rates at multiple frame sizes, decay, waves and reset. `SoraArena.Campaign.CrankCooperation`, `CrankRatchets` and `CrankNets` pass in Unreal at `56b95f3`, with zero errors/warnings. The boy contributes 0.5 × 0.4 = 0.2 turns/s without a decay waiver: the 1% loss of 90 turns is 0.9 turns/s, so idle progress still loses 0.7 turns/s while he helps. ch08.b11 now explicitly gives each named crew member 0.15 turns/s: three available helpers contribute 0.45 against 0.48 turns/s idle loss, for a net slip of 0.03 turns/s. The 0–3 helper rates and checkpoint reset also pass `CrankLiftCrew` in that Unreal run. The physical lift, gallery and cutter contact implementation is described below; its new Unreal fixtures have not run yet. Player effort and ch07's input/temporary hand occupation are implemented as described below; their Unreal qualification and final helper work animations remain outstanding.
- Blocking dialogue input holds and the production registry are implemented; their focused qualification is recorded separately. Diegetic registry presentation and final art, rendered and packaged acceptance remain outstanding.
- Sequencer cinematics (C9): cinematics are a dollying camera over the place behind the letterboxed card with subtitles.
- Authored layouts: the spaces are derived by rule. ch01–ch03's authored layout frames are not placed, so ch01's dojo, stable and range stand in separate zones rather than where the script's metres put them, and places are joined by travel cuts rather than walked between; the zones are blockout floors, walls and cover dressed with the imported props (C3 kits and C4 layouts replace them).
- Pacing: two ch02 rides are authored longer than their pacing allows at any gait (above).
- The 6–8 hour pacing, combat readability and visual quality, which need playtests and captures.


### Chapter eight: physical freight lift (runtime qualification pending)

The 6 × 6 m collision deck now moves continuously from L4 at 27 m to the
heirloom gallery at 142 m, bounded by the fastest authored capstan cadence.
The player walks from a fixed boarding landing onto an ordinary movement
base; the three crew members stand and work on that same floor. No rider is
repositioned during travel. The bars require the player to be aboard, idle
loss lowers the floor, the side gates only open at their landings, and a fall
below the shaft returns through the existing player-death checkpoint.

The gantry heights are now 55.75, 84.50 and 113.25 m, derived from 25%, 50%
and 75% of the 115 m travel above L4. The source prose and YAML use those
same heights. Waves spawn on those real landings: the first wave's drones
fly to the hawser in three dimensions, riflemen hold the second gantry, and
the shield enforcer and two retainers launch normal gravity-driven jumps
when the deck physically reaches the third landing. Only a living, flying,
unstaggered drone whose visible cutter tip touches the hawser segment
multiplies ordinary idle decay by three. Other drone errands retain their
existing ground-relative hover behavior. The rope, cutter and structure
are gameplay shapes awaiting final art.

Full work cannot complete ch08.b11 until the moving floor reaches 142 m.
Completion unlocks ch08.b12's cache at that height and leaves the player in
the gallery; the physical north stair climbs another 18 m before its summit exit starts ch08.b13. Searching remains
optional. The saved checkpoint stays at b11 until the exit, while found
collectibles save immediately. A fresh-world reload repeats the lift and
keeps those finds. No mid-lift save representation was added. The b10
spiral now has a separate source implementation, described below; b13 summit now has a separate source implementation, described below.

Four host `test_lift_data.py` checks pass: exact generated heights, landing
and crew clearances, rejection of changed wave/platform contracts, and a
compiled C++ driver covering bounded continuous motion and exact ordinary
versus triple decay with zero to three helpers at six frame sizes. The
133-task host progression driver also passes. New Unreal fixtures
`SoraArena.Campaign.LiftMotion`, `LiftEncounters`, `LiftGallery` and
`LiftReload`, plus the updated `Spaces`, `CrankLiftCrew` and `Playthrough`,
await the integration engine run. Motion/gallery fixtures hold threats
still to isolate traversal; `LiftEncounters` leaves their AI live. These
source checks do not establish movement-base, jump, rendered, packaged or
platform acceptance.


### Player crank effort and held input (runtime qualification pending)

`task.crank_player` preserves the exact authored player contract, independently
of helper rates. The four costs are 6 (ch04.b06), 2 (ch05.b06), 8 (ch07.b07)
and 5 (ch08.b11); chapter two authors no crank. Sources are the
`stamina_per_turn` entries in [chapter 04](chapter-04.md),
[chapter 05](chapter-05.md), [chapter 07](chapter-07.md) and
[chapter 08](chapter-08.md). Chapter 05 §2.2's b06 bellows flame-gauge table and
b06 `x_flame_gauge.above` explicitly charge ×2 for overspeed without progress:
that attempt costs 4. Other slips, completed goals and rejected turns cost
nothing. Insufficient reserve changes neither progress nor the rhythm's
last-action time, and never spends a partial cost. All player costs use the
existing equipment guard-stamina owner; its existing regeneration is unchanged.
Helper contributions never consume or depend on the player's reserve.

Chapter 07 §2.3's “Override wheel” and b07 `x_override` specify two hands,
`loadout_while_cranking: none`, and the optional 0.6 turns/s cadence. The saved
**Hold to crank** accessibility setting defaults off and applies only to this
authored wheel. An initial Interact press still attempts one ordinary turn;
while held, integer phase schedules 0.6 additional attempts/s through the same
rate-band and stamina admission. Ordinary held input does not repeat. A long
frame issues at most one attempt and discards extra backlog, so it cannot
burst through the rate band. Real Interact mappings cover keyboard and pad.

Active two-handed work temporarily denies weapon use/equipping/guard and
hides the viewmodel, without changing the inventory or selected weapon.
Release, leaving the work anchor, a hit, stagger, reload input, menu/dialogue,
goal completion, beat transition, retry and fresh-world load end that
permission restriction. Hits, leaving, stagger, reload and menus require a
release and fresh press before work can resume; standing near the wheel with
Interact already held never starts it. The lift uses its actual deck/base
eligibility. No hand animation or new stamina regeneration rule is claimed.

Host data and compiled rules tests cover all four exact costs, affordable and
unaffordable bellows overspeed, completed/refused/slow turns, exhausted
resource, 0.6/s at 1–500 ms frame sizes, release/interruption/reset, no implicit
assist on other cranks, and independent helper work. Gameplay/tooling source
checks passed 32/32; all 23 gameplay gates passed again after the final narrow
interruption/validation review (seven crank data tests and all 133 authored
tasks). Reports are under `Saved/SourceChecks/crank-player-work` and
`Saved/SourceChecks/crank-player-work-final` in the producing worktree. `SoraArena.Campaign.CrankPlayerCosts`,
`CrankHeldInput`, and the expanded `SoraArena.UI.SettingsPersist` fixture are
prepared for the root Unreal lane and have not been run here. The existing
cooperation, ratchet, bellows-net, lift and full campaign suites should accompany
them. No UE build, render, packaged or performance result is claimed. The
bellows' distinct alternating left/right tread controls and flame-gauge
presentation are outside this stamina/input slice.

### Chapter eight: spiral traversal (runtime qualification pending)

Chapter 08 spiral source slice: the b10 collision proxy derives its hexagon
from a 1400 cm clear inner aperture and 400 cm ramp width. The approximately
1:12 grade derives 31 hexagon sides (5 1/6 turns), with four exact landings
at 0/900/1800/2700 cm. Host/native route parity and loader checks measure
the actual aperture and grade, rather than only validating metadata. L2 has a
200 cm gantry and a reachable far marksman post; L4 connects to the parked
lift. Spawn posts use real floor heights, and the L3 wave volume checks Z.
All sixteen authored enemies must still be cleared, then the player must
walk to L4 before b11 begins; the checkpoint stays at b10 until that boundary.
`SoraArena.Campaign.SpireTraversal` covers ordinary key-input climbing,
wrong-floor trigger rejection, the L2 bridge, navigation reachability and
the lower-floor combat-clear gate. It is authored but has not been run in
Unreal by this source lane. The same route is used by the full playthrough
fixture. These are functional collision proxies awaiting Claude's art;
the auditor's L3 shortcut shutter and L1 supply cache are described below.
Visual windows, lighting and spire dressing remain open. The spire's two fighters and three guides now follow navigation paths
with height-aware arrival; the fighters keep their combat leash around the
climbing hero. Failed paths stop them instead of steering across the void.
Their committed melee hits require 3D reach, same-floor height and an actual
clear trace to the target. Other chapters retain their existing companion
posts, movement and escort behavior. `SoraArena.Fieldcraft.SpireCompanions`
walks the hero and all five allies to L2/L3/L4, then verifies cross-floor and
wall-blocked attacks fail while clear same-floor contact still damages. This
fixture is authored but unrun by this source lane.


Chapter 08 summit traversal source slice: the gallery north opening feeds a
railed stair with 18 cm maximum risers, climbing from 14200 to 16000 cm. Its
turn landings keep both walking routes open. The b11 checkpoint remains active
through the gallery and stair; only the real summit stair-head volume begins
b13. Height-bounded place zones keep the summit directly above the spire.
The 36 m disc, 1.2 m dais, 4 m by 22 m spine, desk/plinth and 60 m overhead
ring are functional proxies; cinematic camera coordinates and the boss spawn
now use the elevated floor. An actual open-edge fall deals 25 damage once
and returns a surviving hero to a firm edge position in the same boss phase.
`SoraArena.Campaign.SummitTraversal` covers the elevated checkpoint, cinematic
skip, boss staging, dais access and fall recovery. The lift gallery fixtures
now physically walk all stair flights before checking the b13 checkpoint.
These Unreal fixtures remain unrun by the source lane.

Chapter 08 seizure source slice replaces that disc with 132 convex collision
tiles on a 300 cm grid, clipped to its 36 m diameter. The boundary follows a
72-sided polygon (under 2 cm chord deviation). The existing P2 concurrent
attack schedules checker thirds, an 800–1200 cm ring band, then three tally
lines through the player cell at the mark. The tally interpretation is a row,
column and rising diagonal; the lines lock at the mark and do not track.
Marked tiles remain solid for the existing difficulty-scaled 1500 ms warning,
then lose collision for 5000 ms and rise for 1000 ms before becoming solid.
Amber edges pulse during warning/restoration. The dais and desk remain fixed.

An actual fall costs 25 health, selects the nearest clear intact edge tile,
and grants 1 s damage immunity. Ground constructs and the boss also recover,
preserving health, so a construct below the arena cannot strand the shield.
P3 restores every tile immediately. No partial tile state is added to saves;
the existing boss phase checkpoint and native encounter gate remain in charge.
`SoraArena.Campaign.SeizureTiles` checks real collision traces, a gravity-driven
fall, recovery/immunity, the real nine-second attack cadence, all three
patterns, construct recovery and phase shutoff. It is authored but unrun.
Host `test_summit_rules.py` checks coverage, clipping, width, stage boundaries
and masks. Engine compilation, procedural collision cooking, rendering,
navigation updates and runtime fixtures still require root qualification.

The held spine draw-cut source candidate preserves the take-alive outcome.
After the 1.5 s disarm interval, the hero must walk onto the dais, face the
south seam within 260 cm with a clear collision trace, and hold Interact for
the authored 1500 ms. Release, damage, loss of sight/reach, a changed
weapon, or a menu/dialogue input boundary discards partial work and requires
a fresh press. Releases clear work immediately even while paused. The hold is never
saved; the existing P3 checkpoint remains until the full cut starts b15.
The seam and first-person draw-cut remain visual proxies; no finished
animation is claimed. `SoraArena.Campaign.SpineDrawCut` covers ordinary
dais traversal, wrong-height/occlusion rejection, interruptions, paused input,
and reloading the saved P3 checkpoint after a partial cut before completing
a new full cut. Its Unreal execution remains pending root qualification.
Host checks cover the authored duration and transient hold at 1–500 ms steps.

The P2 retreat source candidate uses the normal enemy navigation/controller
and swept character movement to reach the north dais stand, clear of the
solid spine. While protected it cannot attack or summon, and its phase save
waits for both the two-second minimum transition and actual grounded arrival.
A blocked route keeps the previous save; no timeout teleports the boss. Once
there, P2 holds its stand even while exposed. The P3 draw interval lasts at
least 2.5 seconds and saves when complete. A resumed P2 checkpoint spawns on
the completed dais stand. The existing phase health gates, take-alive outcome
and generic boss arenas retain their contracts. `SummitPhases` exercises a
real blocking wall, continuous retreat, phase saves and holding the dais;
`SummitPhaseReload` covers its resumed position. These new Unreal fixtures
remain unrun by the source lane. The camera blends, moving engine ring,
coat/cane choreography and cinematic cast animation remain open. Functional
tile meshes and edge bars remain proxies for the art lane.

### Alternating bellows treads and live flame gauge

Chapter 05 b06's input and all three `x_flame_gauge` states are normalized and
validated exactly (`chapter-05.md:480–493`, `1793–1825`). Hold Interact at the
station, then press left and right using the existing movement mappings. One
left/right pair is one turn; each tread must return to neutral. A held key,
right-first press, stick crossing without neutral, or Interact alone adds no
production. Release, hit, departure and retry discard an unfinished pair.
Completed pairs use the same stamina and rate admission as other crank work.

The furnace shows the current rate: dull red with one notch when slow/idle,
山吹 gold with two in band, white with three and a capped eight-spark pool when
too fast. Idle cools the gauge independently of accumulated production. HUD
text repeats the rate and next foot, including mapped keyboard or pad labels.
The two separate tread boards and furnace are functional primitive proxies;
bespoke foot/cloth animation, final art, tone-mapped readability and hardware
haptics are not proven by this source slice.

Host coverage checks analog hysteresis, held/repeated/wrong-foot input,
interrupted half-cycles, frame sizes 1–250 ms, stamina rejection, paid overspeed,
idle gauge cooling and checkpoint reset. The directed UE fixture
`SoraArena.Campaign.BellowsTreads` exercises keyboard and pad, physical notch
visibility and capped sparks; crank cost/net fixtures and campaign playthrough
now use actual pairs. UE compilation, execution and HUD capture remain with
the root lane. Source reports: `Saved/SourceChecks/bellows-treads` and
`Saved/SourceChecks/bellows-treads-final` in the producing worktree.

### Shared rhythm assist and chapter-five phrase/pick rules

The off-by-default, persisted **Rhythm assist** option applies to ch05 b06,
b08 and b11 (`chapter-05.md:694–706`). It holds the ordinary on-beat cadence
and credits successful production at 700/1000: ten bellows cycles or successful
phrases/picks earn seven units. Bellows remain at one cycle/s, within the
normal band, and every assisted cycle still pays two stamina. Insufficient
reserve stops input without granting progress. Chapter seven's separate
0.6-turn/s hold option and other ordinary manufacturing retain their controls.

The hammer extension (`chapter-05.md:523`, `1897–1923`) now actually requires
four phrases of eight response windows, with six hits needed per phrase.
All eight windows close before judging; the sixth early hit never ends a
phrase. Failure repeats only the current phrase. Weaving (`560`, `2031–2035`)
requires twenty-four successful individual picks; a miss repeats that pick.
The first Interact asks for a cue, then the same button strikes/pulls on the
600/750 ms clock. Easy widens ±90/±120 ms to ±135/±180 without slowing cues;
bellows' .8–1.3 band expands by 1.5 about its midpoint to .675–1.425 turns/s.
Other difficulties retain the original windows. Difficulty is applied to a
fresh task copy at beat entry; it cannot compound across retries.

A continuously closing HUD ring supplies a shape cue. Hammer/loom cue
captions use localized text; native force-feedback requests are emitted once
per cue. The subsequent workshop slice below connects the cleared anvil audio
and station motions; Okinu's voice and character clips remain outstanding.
Hardware vibration, final ring placement,
small-screen legibility and audio timing require Unreal review; no rendered
or controller-device result is claimed here.

Holding Interact with assist on answers cues at their nominal times; source
coverage includes 1/16/17/33/100/250/500 ms frames, exactly 70% credit, the
inclusive/outside timing edges, all-eight-window gating, six-hit success,
five-hit failure, repeat-pick preservation, release/interruption and checkpoint
reset. Completed units and earned fractional credit remain after a release;
an unfinished phrase and held input do not. A fresh checkpoint starts clean.
No long stalled frame synthesizes a backlog of assisted actions.

Prepared UE checks: `SoraArena.Campaign.RhythmPhrases`, `RhythmAssist`, expanded
`SoraArena.UI.SettingsPersist`, and the full campaign playthrough's actual cue
responses. `SoraCapture.WeaponHUDFixture.BellowsKeyboard` and `.BellowsGamepad`
load the real bellows checkpoint, collect actual notice-producing pickups,
perform a mapped L/R pair and leave a right tread pending. Both JA and JA+EN
frames retain the actual tracker, notices and bottom HUD; the pad case checks
its displayed left-stick directions against the live axis binding. Root owns
720p/1080p captures and all UE builds/execution. Source checks are recorded at
`Saved/SourceChecks/rhythm-assist` in the producing worktree.

### Workshop cue audio and functional station motions

Chapter 05 §2.5 (`chapter-05.md:694–706`) names a small-hammer tap and glint,
an anvil ring, and Okinu's call with a shuttle flick and cord marker. The new
`Workshop` audio family connects forge cues and accepted response strikes to
two existing CC0 VCSL anvil recordings, pinned at
`c1ea7bcc3c7309650ab0da9d15c9cd1fbc4a4c7e` in `audio_vcsl.json`.
The selected Hit1/v1 and Hit2/v3 raw files were recovered byte-for-byte and
checked against both recorded SHA-256 and Git blob hashes. Two 48 kHz/24-bit,
420 ms derivatives total 242,008 bytes. Their new ledger record preserves
raw identity, spans, credit, upstream link and QA; unrelated ledger records
and their hashes are unchanged. `build_cc0_audio.py --workshop-only --check`
reproduces only these takes without requiring the unrelated raw library.

The small-hammer cue uses retained `SFX_Telegraph` loading, fixed pitch and
the actual station location; it does not depend on Music volume. The
stronger `SFX_Foley` response sounds only once per admitted manual/assisted
strike, including strikes that do not yet finish a phrase. Misses, duplicate
presses, interrupted input and fractional production credit cannot invent
extra impacts. The first cue is explicitly a count-in; response is due one
600/750 ms interval later. This game-thread presentation has not been proved
sample-accurate or reviewed for latency in Unreal.

The forge now has separate cue hammer and sledge motions, a small glint,
and a 32-segment ring closing on the anvil. The drawloom has a shuttle flick,
an anchored figure cord/marker and a beater response. These fixed component
pools move from the same task clock and accepted-response timestamps used by
scoring, without adding collision, changing controls or granting progress.
Interruptions restore idle poses. They are functional primitive station
props, not completed first-person paws or named NPC animation clips.

**Still missing:** no cleared Okinu voice recording exists in the repository.
`workshop.loom.call` is explicitly `needed`, with no waveform or voice caption;
the caption truthfully describes the visible shuttle cue. It is not silently
replaced with an anvil, UI beep or imitation voice. The first-person grips,
bellows/sledge/cord character clips, Kōzō's yokoza and Okinu's full weave cycle
remain the §5.4 deliverables. Bellows creak/furnace breathing, loom/cord foley
and the authored tempo-locked music stems (§5.6–5.7) remain open too.

CPU coverage checks both new waveform hashes/PCM layouts/raw provenance,
audio routing and the missing-voice contract; 1–500 ms rhythm frame sizes
emit exactly one response per admitted strike; station poses stay bounded,
close at their authored periods and reset on inactive clocks. The prepared
`SoraArena.Campaign.RhythmWorkshop` fixture checks the real cue family with
Music at 0, count-in versus hit, repeated-press refusal, moving tool and combat
interruption. `RhythmAssist` additionally asserts the explicit unvoiced loom
contract and separate shuttle/cord pieces. Root must run the existing audio
importer for the two new SoundWaves, then compile/run these fixtures and
inspect/listen to the station in-game; no UE, listening, render or controller
verification is claimed by this source slice. Reports live under
`Saved/SourceChecks/workshop-cues` in the producing worktree.

### Summit collateral constructs

The chapter 08 collateral source candidate gives only the summit's summoned
`collateral_construct` its authored 900 ms amber slam, 250 cm radius, 25 damage,
and 1400 ms recovery (windup retains the shared difficulty scale). Its exposed
core stays still during recovery. A visible physical core accepts a one-second
held Interact cut, or exactly two heavy contacts from the kanabō/forge hammer.
Body shots, closed-core hits and lighter arms cannot bypass it. The cut checks
grounded height, facing and visibility, and discards partial time on release,
damage, pause, dialogue or recovery expiry. No partial construct state is saved.

Released collateral remains as five intact named functional goods proxies
which settle smoothly onto queried solid floor. These are engine primitive
placeholders, not finished rice bales, lacquer chests, plough, loom or cart art;
cyan assembly fields, the core seal, proper slam/cut animation and the finished
release presentation remain Claude's art work. Released actors do not count as
live adds and leave when the encounter is removed. Ordinary loom automatons,
other summons and campaign kill contracts remain unchanged.

`SoraArena.Campaign.CollateralConstruct` covers the real summoned pair, slam
windup/damage and radius escape, visible/height-gated core contact, mapped held
input and release interruption, two actual forge-hammer sweeps, add/shield
accounting, floor settling and encounter cleanup. `test_construct_rules.py`
checks authored constants, exact core hit admission, ordinary loom catalog
values and smooth release bounds. Source checks do not qualify Unreal
collision, compilation, rendering or runtime; root owns those checks.

The summit collector's construct respawn now belongs to P2's seizure group.
Clearing it retains the ten-second exposed interval; entering P3 cancels its
pending deadline, and add deaths cannot schedule a group absent from the
current phase. While constructs shield P2, its normal ledger/cleave pattern
cannot begin or finish a pending windup. Concurrent seizure fields and summon
thresholds continue on their existing clocks. These guards apply only to the
chapter 08 summit collector; generic boss arenas retain their prior behavior.
`SoraArena.Campaign.SeizurePhaseOwnership` covers a live shield with ongoing
hazards, ordinary AI attacks during exposure, a late beam cancelled by the
returning shield, the real ten-second respawn, and a same-encounter P2-to-P3
transition followed past the old deadline and reloaded from the actual save.
`test_summit_data.py` checks that only P2 owns this group and preserves the
55% summon and nine-second hazard cadence. Engine execution remains for root
qualification; camera/ring/cast presentation is still separate art work.

The summit Collector's mutō-dori now requires the katana already sheathed.
Correctly timed guards with a sheathed hammer, kanabō or other blade cannot
capture him and retain the foreclosure's full damage. Other opponents and
the shared 700 ms sheathing rule are unchanged; the chapter's older 600 ms
animation wording remains a design/presentation discrepancy.

The actual first foreclosure windup raises its authored tutorial prompt and
replays the nonblocking mentor memory from b09 once, even when that line has
already been heard earlier in the chapter. Later windups at the 1% floor
refresh only the prompt. Generic dialogue deduplication and unrelated boss
events remain unchanged. `SoraArena.Campaign.CollectorCapture` primes the real
dialogue queue with the earlier memory, tests foreign-event rejection, uses
mapped weapon/sheath/guard inputs against real foreclosure attacks for three
wrong arms and the katana, and checks first-only memory, floor reminders and
the unchanged pending spine-cut checkpoint. Root owns Unreal qualification.
### Chapter-eight auditor shortcut shutter (source candidate)

The authored b10 alarm now has a functional proxy: a railed two-metre chord
connects the L3 landing to the ramp two hexagon sides above it. An auditor's
alarm closes only this shortcut; all original ramp segments remain available.
The upper connection has its own capsule-tested inner-rail clearance, and both
pads have perimeter rails outside the three connected walking corridors. The
existing L2/L4 crossings, wave triggers and L4 completion boundary are retained.

Only hunting auditors in the active spire descend from the L4 office to the
L3 panel approaches (the authored level table places the alarm at 18 m).
Arrival requires a living auditor on the actual panel floor; a generic shout,
death en route or matching XY on a lower winding cannot operate the shutter.
The future door volume must be clear of every pawn before collision is enabled.
Retry/staging clears both pending alarms and the solid shutter. The ch06 stealth
lectern path is unchanged.

`SoraArena.Campaign.SpireAuditorShutter` covers real auditor travel, interception,
lower-floor and shout rejection, normal-input shortcut crossings, occupied-door
deferral, capsule collision, dynamic navigation's longer route, ordinary ramp
traversal and death/retry reset. Host geometry checks cover the chord's width,
grade, shorter length and both endpoint rail clearances. Actual UE execution
is pending root qualification. Panels and the shutter are explicit functional
proxies; finished architecture, shutter drop animation and alarm presentation
remain art work.

The first actual root run at `a8d541d` failed the new shutter fixture and
existing spire navigation/companion fixtures; the playthrough and ch06 alarm
fixture passed. Normal player ramp movement still passed, but a new pad rail
cap left only 47 cm centerline clearance beyond the nearest ramp node. The
guard calculation now clips the entire local ramp footprint, with host
regressions checking two neighboring segments in each direction and a capsule
plus two navigation cells of clearance. That check fails against the original
`32e8697` geometry. The physical blocker queries now include WorldDynamic:
builder boxes inherit that engine collision object type, so the old
WorldStatic-only query could not see the corner guard or shutter. Runtime
failures now report the exact first blocker and incomplete navigation sections.
These corrections await a fresh root Unreal run; they do not erase the failed
qualification evidence.

Root subsequently qualified the repair at `62d6fe6`: SpireAuditorShutter,
SpireTraversal, SpireCompanions, the full Playthrough and AlarmLectern all
passed. The run retained one HTTP connectivity-probe timeout warning and no
selected-test errors. Its receipt is under
`Saved/Qualification/2026-10-20/spire-shutter-62d6fe6-directed` in the root
qualification checkout.

### Chapter-eight L1 supply cache (source candidate)

The authored `sp_spire_base` engineers' cache is a physical crate beside the
first ramp landing. Its nearby bilingual notice names the current Interact
binding. Walking past never refills equipment: explicit Interact requires
grounded same-floor reach and a visibility trace to that crate. Another
floor, an intervening wall, reload, bow draw, guard, strike/recovery, stagger,
step, sheathing transition or weapon cooldown refuses the refill.

The cache refills only unlocked ranged weapons to their existing catalog
magazine caps, including the twelve-arrow yumi. The held weapon's live
ammunition is authoritative even while its stored copy is stale. Equipped
weapon, completed sheath state, health, guard reserve, unlocks and checkpoint
progress are preserved. Full magazines make repeated use a no-op. Stock is
unlimited as an explicit implementation choice: the authored cache has no
finite quantity. There are no new healing or unlock rewards. Existing reload
and campaign loadout permissions are unchanged; the proposed five-slot
loadout redesign is outside this slice.

The catalog retains chapter three's object-form supply identity and later
string identities. Only this spire cache is staged in this slice; the other
named stations still need their place-specific implementation. Clearing or
retrying a beat removes/rebuilds the cache without adding save state.

Host `test_supply_rules.py` exercises catalog-derived caps, each held weapon,
locked and melee inventory preservation, stale held copies, repeated use and
spending between visits. `SoraArena.Campaign.SpireSupply` uses normal approach,
mapped interaction and actual reload/draw/guard/shot controls; checks floor,
airborne and real-wall rejection; preserves a sheathed katana; rebinds
Interact; and restocks again after ordinary death/retry. Supply Unreal and
rendered acceptance remain pending root qualification. The crate, cloth,
arrows and cartridges are functional proxies awaiting the art lane.

The first root supply run at `5f7958f` passed EquipmentRecovery, Playthrough,
SpireTraversal and SpireCompanions, but SpireSupply failed at the assumed
jump and then reported three dependent ammo/reload failures. The fixture had
teleported back from its wrong-floor check and tapped Jump after a fixed
three-frame wait without verifying a landing or an actual jump. Its follow-up
waits for a real grounded, jump-eligible capsule, faces away from low-cover
vaulting, and holds the mapped key until falling mode, upward velocity and
positive displacement establish flight. It logs those states and stops on a
failed precondition instead of cascading. Production reach rules are unchanged.
Teardown also asserts that global action/axis mappings are unchanged and the
isolated rebound profile has been deleted. Unreal requalification is pending.

## Seized-goods gallery lore

Chapter eight b12's `poi_child_toy` and `poi_covered_mon` are separate physical
interactions on the 142 m gallery. The catalog retains all six authored POI
identities, interaction text and collectible references. These two objects sit
on graphite plinths beside the east rail, clear of the existing cache and north
stair path, with warm 3,800 K light and no objective markers. Mapped Interact
requires a grounded capsule on the same floor, within 260 cm and an unobstructed
visibility trace to the actual object. The toy raises `event:poi_child_toy` and
the exact `ch08.b12.nyaakoto.002` line. Interacting with the jinbaori hides its
seizure label and reveals the existing pinned SVG mon mesh; the mon remains
hidden before the label is torn.

The additive schema-6 `GalleryPoiMask` defaults to zero for an older tagged
save. Only its two known bits are valid, and a nonzero mask requires chapter
eight to have been reached. These are durable lore discoveries, like codex
finds, rather than beat-derived story flags: immediate `SaveProgress` keeps the
existing b11 start checkpoint. Retry, fresh-world reload and chapter replay
retain them; New Campaign clears them. Repeated input does not replay the toy
line, tear the label again, award collectibles, alter weapons or complete the
optional beat. The existing cache still awards ch08.c03/c04/c05; its completion
does not disable the two lore objects. The north stair remains optional-gallery
exit and starts the b13 checkpoint.

`SoraArena.Campaign.GalleryPois` covers actual capstan travel and walking,
wrong-floor/airborne/wall rejection, a real Interact rebind, exact toy dialogue,
repeat use, unchanged inventory, cache independence, ordinary death/retry,
fresh-world reload, a second mapped-key ride and the normal summit exit.
SaveRoundTrip and ForgedSaves cover the new field, including malformed bits and
replay of an earlier chapter after discovering the gallery. Host `gallery-rules`
checks the authored identities/dialogue/rewards, mask transitions and physical
clearance from the existing route/cache. Unreal qualification remains pending.

The paper toy, jinbaori, plinths and seizure label are explicitly functional
proxies. Detailed paper craft, textile/label art, valuation lettering, the
tearing animation, the other display cases and the cloud-window vista remain
presentation work; this slice does not claim those assets are finished.

The first root gallery runtime at `a26bae5` passed ForgedSaves, LiftGallery,
LiftReload, Playthrough, SaveRoundTrip and SummitTraversal. GalleryPois stopped
at its actual-jump precondition, before the positive lore-interaction cases.
That run contained no jump state diagnostics, so it establishes neither an
airborne interaction leak nor the cause of the failed jump. A fixture-only
follow-up records setup, key press, every held frame and result with actual
movement/input/equipment state. Its timing and flight assertion are unchanged;
the cause and remaining gallery checks await root's diagnostic rerun.

The diagnostic rerun at `3c6da0f` fails the same assertion and identifies a
fixture setup error: every jump sample has `CanPlay=0`, input state 16
(`Result`), grounded/CanJump true and no vault or equipment commitment. The
mapped Space key is held, but jumping is correctly blocked. The preceding
900 cm downward teleport crosses the unchanged lift's lethal boundary, 600 cm
below its deck. The follow-up uses a real temporary floor 300 cm below the
gallery and requires ordinary play and grounded movement around the wrong-floor
input. It preserves the flight assertion and production fall protection.
Input conflict checks, two gallery rule tests and fourteen source-runner tests
pass; the repaired fixture still requires an actual Unreal run.

Root's repaired `298ed9e` run passed GalleryPois: **1/1, zero errors and
warnings, 9.354923 s**. Mapped Jump raised the capsule **8.363 cm** in
`MOVE_Falling` with vertical velocity **493.667 cm/s**, while ordinary play
remained active. The positive interactions, persistence and exit checks
completed. The earlier build failure and both failed runtime receipts remain
retained evidence; this result does not finish the visual proxies.

## Seized-gallery cache contract (source candidate)

The existing optional b12 cache now retains its declared `arrows_12` reward.
Opening it grants up to twelve arrows to the unlocked bow, capped by the
catalog's twelve-arrow magazine. The live held count is authoritative when
holding the bow; otherwise only its stored magazine changes. Other ammo,
held weapon, sheathing, health and unlocks are preserved. A draw, reload,
strike or other equipment busy state refuses the unclaimed bundle before
cache completion or collectibles change, leaving it available for a later
explicit interaction.

The additive schema-6 `GalleryArrowsClaimed` property defaults to false,
including for older saves that already contain the three gallery finds.
A true claim requires chapter eight to have been reached and all three
gallery collectible bits. The claim and finds save together through the
existing optional completion path, retaining the b11 lower-landing checkpoint.
The bundle is consumed even when the quiver is full, and cannot refill again
after spending, retry, reload or chapter replay. New Campaign clears it.
This tracks one cache pickup: ammo itself keeps the existing checkpoint
full-magazine reset and ordinary reload behavior; this slice adds no reserve
inventory system.

Newly collected items retain both existing `collectible:<id>` and
`collectible_found:<id>` events and also raise the authored
`event:collectible_<id with underscores>` name. The gallery therefore queues
the exact `ch08.b12.nyaakoto.003` Washio line and
`ch08.b12.sekireisai.004` life-giving-sword memory through their existing
script rows. Their collectible-bit guard prevents repeats after input,
retry or fresh-world load. Existing saves with those finds do not replay
the discoveries when collecting the newly available arrows.

`SoraArena.Campaign.GalleryCache` covers normal lift travel and cache walking,
actual remapped input, live-draw rejection, empty/partial/full held or stowed
quivers, exact dialogue lines, other inventory and sheath preservation,
immediate disk state, repeat input, death/retry, fresh-world reload, chapter
replay and New Campaign. SaveRoundTrip and ForgedSaves cover the additive
claim and invalid combinations. Host gallery rules exercise all ownership
combinations and finite pickups across held slots/counts, including overflow
amounts and locked weapons. This candidate still needs root's Unreal run.
The three collectible POIs still share the existing functional cache; separate
display interactions, final props, memory voice presentation and the gallery's
remaining art are not completed by this change.

## Chapter-one b07 archery candidate (source only, 2026-10-20)

The range now uses physical paper/straw target proxies instead of generic
sparring pupils. The existing chapter contract is validated at catalog load:
one 28 m, 36 cm near face (25/21/18 cm scoring radius by difficulty), six
resolved arrows with at least four hits, then three 45 cm hanging faces at
40/50/60 m, each moving ±150 cm on a 3.2 s period. A target scores only an
actual yumi projectile registered when released from the grounded shooting
line. Other damage, off-line releases, repeated completed targets, stale
identities and duplicate resolutions grant no progress. Collisions and
two-second flight expiry both resolve shots. All six near arrows must resolve
before either passing or failing the set.

The mapped Bow action (default key 3) now equips the unlocked yumi in chapter
one; key 1 or the existing key 2 returns to the training sword. Equip loads
the yumi proxy instead of the authored bokken mesh. The later b11 sparring
match retains its melee-only training slot. That slot still renders a bokken
proxy: it is **not** an art-qualified fukuro-shinai. The integrated HUD limits
its chapter-one bokken label to weapon 0, so the yumi retains its own label.

Chapter-one R no longer creates arrows. B07 starts with the own twelve-arrow
quiver. A failed six-arrow set pauses shooting for the authored eight-second
keeper retrieval, then restores those twelve arrows. The script does not
define a recovery after misses exhaust the hanging stage; the explicit
implementation choice is the same eight-second retrieval after the last
in-flight arrow resolves, retaining earned hanging hits and awarding no
progress. Menu/dialogue time does not advance retrieval. Completion
reconstructs the authored six usable and six bent arrows; b09 checkpoint
retry/reload restores that same batch. Only completion of b09's existing
manufacturing task restores twelve usable and zero bent arrows. There is no
new partial-target or per-arrow save state. Other chapters' reload/reserve
contracts and deterministic practice/kernel are unchanged by this slice.

`SoraArena.Campaign.ArcheryLesson` uses normal 60 Hz walking, mapped equip,
650 ms draw and release, actual projectile flight, failed-set retrieval,
paused/rebound input, hanging exhaustion/recovery, fresh b09 reload and
normal station interactions to repair the batch. `ArcheryReload` covers
pre-unlock/b11 loadout boundaries, ordinary menu checkpoint retry and a
fresh-world load without reseeding. `SoraArcheryAutomation::Complete` is
integrated into the aggregate playthrough in place of its former generic enemy
damage shortcut. Spaces and CombatTrace fixtures were not edited.
The host `archery-rules` gate checks all 64 six-shot hit patterns in all
720 resolution orders, retrieval boundaries at 1–500 ms, duplicate/stale
identities, exhausted-stage recovery, inventory reconstruction, and range
clearance against the current authored zone. **Unreal execution is pending
root qualification; source tests are not runtime evidence.**

The shooting line sits 420 cm beyond the existing range entry, beyond the two
instructors. Three hanging lanes have offsets −600/0/+600 cm; all centers are
40 cm above the flat range floor. Those lane placements and hanging height
are functional proxy choices inside the existing space. Final shajō/azuchi,
support frames, paper/straw surfaces, keeper retrieval animation, yumi and
arrow-rest rigging, first-equip shooting forms and yugaeri/follow-through
remain presentation work. Authored visible aim sway after four full-draw
seconds remained unimplemented in this archery checkpoint; the later sway
candidate is described below. The b08 clapper challenge and the remaining
chapter-specific reserve/pickup contracts remain separate gameplay gaps.

The integrated candidate `44ffc35` subsequently builds and passes
`ArcheryLesson`, `ArcheryReload` and the complete accelerated `Playthrough`
in the actual M2 Ultra UE 5.8.3 editor, with zero selected errors/warnings.
The range fixtures walk around instructor collision, equip/draw/release through
mapped input at 60 Hz, score real arrow impacts and expiry, reject an actual
off-line target hit, wait retrieval, exhaust and recover the hanging-stage
quiver, and repair the batch after a fresh-world smithy load. The aggregate
fixture also uses these real arrows for b07. This is automated editor evidence,
not human pacing, rendered range art or packaged qualification. The fresh Mac
package remains running. Source-only checks pass 46/46 at preceding `8fb35cf`;
its original compile failure is retained, and the narrow explicit-scopes/header
repair has its separate successful editor build receipt at `44ffc35`.

## Visible yumi aim sway candidate (source only, 2026-10-23)

Chapter 01 §b07 / `x_shaho` specifies the 650 ms draw and sway after four
seconds at full draw: onset is 4.65 seconds after Attack is pressed. It does
not specify strength, periods or a ramp. The named `SoraBowRules` defaults
are explicit **provisional implementation choices**, awaiting actual play and
visual review: pitch ±0.18°, yaw ±0.28°, periods 2.6/3.4 seconds, and a
one-second smoothstep ramp. All difficulties initially use the same profile.
Both waves start at zero and use the current draw's absolute elapsed time;
there is no random release roll or frame-accumulated drift.

The camera and control rotation stay stable. The HUD projects the bow's
current aim ray and the held proxy receives its camera-local angular offset.
The released projectile and ordinary shot event use that same ray, sampled
before clearing draw state. The reticle describes initial aim, not a gravity
or moving-target impact prediction. Pausing, dialogue input reset, switching
weapons, stagger, checkpoint retry and fresh-world load discard the draw and
its phase. There is no new serialized state or change to arrow inventory,
target scoring, keeper retrieval, lesson progression or practice/kernel.

`SoraArena.Campaign.BowAimSway` uses mapped equip/draw/release and normal
60 Hz ticks on all three difficulties. It records full-draw/onset times,
checks visible proxy rotation and unchanged camera input, compares actual
projectile initial velocity/origin with the visible ray and shot event, and
waits for a real miss resolution. `BowAimCancellation` covers paused and
remapped Attack, weapon change, dialogue and stagger cancellation, ordinary
menu retry and fresh-world reload with a held draw. Cancelled draws must
spend no arrow or issue a shot identity, and each new draw starts steady.
The host `bow-aim-rules` gate covers exact onset, independent numerical
samples, bounded long holds, smooth ramp joins and frame partition invariance.
**These are source changes and unexecuted Unreal fixtures until root records
the actual engine run.** Reticle legibility and tuning, final bow/hand rigging,
right-side arrow rest and yugaeri still need their respective visual/art review.

The separate source-only `SoraCapture.BowAim.Live` fixture prepares the actual
b07 checkpoint and grounded range view, then uses the current mapped Bow and
Attack keys in the running game. It waits for assets before starting the draw;
world time then advances normally, with no freeze, manual tick, timestamp
assignment or aim override. It requests original framebuffer screenshots on
actual HUD draw frames: steady full draw before the threshold, positive sway,
negative sway, and the centered reticle after a real release. The target must
be unobstructed, the held yumi proxy visible, camera/control rotation fixed,
and the viewmodel pose consistent with the aim offset. Fixed-step simulation
and time dilation are rejected. This is a prepared capture, not a normal
chapter playthrough or final art acceptance.

The HUD observation records the submitted reticle position. The fixture
independently projects the shared ray with the player controller and compares
those coordinates. PNG-adjacent JSON retains frame number, world/draw/wall
times, camera, ray, offset, bow rotation, target projection, actual held input
and ammunition. It records release and emitted-shot frames/times/rays
separately, including any screenshot-callback delay and whether the shot also
matched the rendered sample; callback timing alone is not an equality claim.
The mapped release must emit exactly one shot and leave eleven arrows.
Cleanup drops held inputs, removes delegates, restores HUD/title/save-slot
state, removes the throwaway save and checks control mappings and saved
control/settings bytes, restoring bytes if a failed check detects a change.
It also restores the original campaign slot's exact bytes or original absence
after the title/reset path, which can otherwise persist a default save.

Run each viewport separately on the exclusive engine lane:

```sh
scripts/toolchain/capture-editor-game.sh SoraCapture.BowAim.Live 1280 720 sm6
scripts/toolchain/capture-editor-game.sh SoraCapture.BowAim.Live 1920 1080 sm6
```

`verify-capture-report.py` requires this fixture's own `SORA_BOW_AIM_FRAME`
markers and all four phases. It preserves original PNG and observation bytes
with hashes, checks timing/projection/shot consistency, and locates the four
crosshair arms in the actual PNG using local line contrast. Pixel centers
must match the submitted reticle within 1.5 pixels, show both sway directions
and return after release. Invisible/ambiguous arms fail rather than being
painted over or inferred from metadata. The verifier's synthetic unit images
test decoding and failure paths; they are not rendered evidence. **Neither
viewport has been executed for this source candidate.** Human review still
decides whether the small motion is perceptible and comfortable, and whether
the final bow/hand/target art is acceptable.

## Dojo awase feedback and passive zanshin candidate (source only, 2026-10-20)

Chapter 01 §b04 requires Sekireisai's `ch01.b04.sekireisai.003` when a
successful awase is not followed by Step inside 400 ms. Real dojo parries
publish `OnParried`; the director incorrectly subscribed to `OnGuarded`,
and the former aggregate fixture fabricated that wrong event. The director
now listens to the actual parry event. Its existing gameplay clock pauses
in menus, an actual after-awase Step cancels the pending hint, and beat
restart clears it. The authored line and 15-second repeat cooldown remain
unchanged. Playthrough's missed-step case now uses a live pupil, its observed
telegraph, mapped Guard, and normal 60 Hz ticks.

Chapter 01 §b03 enables passive 残心 after the recovery lesson: a continuous
500 ms guard after a scored point restores 15 stamina. The hero previously
skipped the guard/stamina tick during every dojo frame. Completing all four
forms now enables that existing stamina cycle. The early forms retain their
prior training behavior. A dojo reward is armed only after the director
accepts a `Scored` or `Won` point; a pupil knocked down without b04's required
flank earns none. Ordinary non-dojo defeats retain their existing path.
Reward state is transient and reset with the class/checkpoint loadout.

`SoraArena.Campaign.DojoGuardLessons` receives actual pupil contacts and
learns Guard, two Parry repetitions, and Recovery through mapped input at
each difficulty. `DojoAwaseHint` covers ordinary guard rejection, the
400 ms opportunity, menu pause, an actual swept Step, and retry at the b04
checkpoint reached through normal b03 lessons and cuts.
`DojoZanshin` spends stamina through held guard, scores with real return
cuts during actual awase stagger, and checks a broken/restarted hold,
exactly +15 once, resumed drain, reload while the winning point's next
reward is still pending, and a refused bout.
No combat event, damage, score or stamina write substitutes for input in
those paths. **Unreal qualification is pending; CPU checks are not runtime
evidence.**

The existing pupil attack variation is still incomplete: `PupilAttack`
uses a fixed 550 ms windup and 1450 ms post-windup delay for all lessons.
The authored b04 `pupil_kesa` 600 ms/1000 ms timing and Easy ×1.30 / Hard
×0.85 windup scaling are not implemented by this repair. Tests respond to
the observed telegraph and validate the guard/parry gates; they do not
qualify those missing attack variations or the final animation.

### Authored pupil timing candidate (2026-10-23; runtime pending)

The subsequent timing slice reads the two `ext.opponent_pattern` rows
instead of sharing one drill. In b03, `pupil_men` starts every 1450 ms:
`repeat_s` is an onset-to-onset interval, not another 1450 ms after impact.
Its Normal windup is 550 ms. In b04, `pupil_kesa` has a 600 ms Normal
windup followed by a full 1000 ms recovery measured from actual contact.
Windups alone scale by Easy ×1.30 or Hard ×0.85, rounded half up to integer
milliseconds. The real telegraph and committed event carry that same
duration. Stagger and turn lock continue to defer an otherwise due attack.
The maai teacher remains non-attacking; Toranosuke retains his separate
boss-catalog attack patterns. No save, input binding or kernel rule changes.

`SoraArena.Campaign.PupilTiming` reads the real catalog and rejects malformed
or conflicting pattern fields through its loader. For both lessons on all
three difficulties, it approaches using mapped movement, holds two real
early guards, then answers the third observed telegraph with a mapped
awase. At normal 60 Hz it records attack onset, telegraph lifetime, contact,
guard age, and the next attack after recovery/stagger. It asserts the
350 ms early-guard opportunity even on Hard, the separate repeat/recovery
cadences, and the real 1200 ms stagger delay. It does not move actors,
synthesize combat events, shorten clocks, grant points, or change health.
The `dojo-timing` CPU gate checks authored data, shared timing math and
invalid cadence boundaries. **This is source evidence only until the root
lane executes the directed Unreal test.** The existing straight telegraph
and weapon animation remain presentation proxies; this timing slice does
not qualify the authored diagonal kesa edge or final animation.

## October 23 actual dojo qualification

Integrated `c841a8d` passes eight source-bound editor tests covering real awase
feedback, learned guard/recovery, zanshin, both maai paths, physical archery and
the full accelerated campaign traversal, with zero selected errors/warnings.
The same source passes 57 gameplay/tooling/asset CPU checks and the uncooked
Metal SM6 front-end tour. Its 19 menu frames are archived; only two Credits
views were reviewed in this run. These results supersede the source-only
qualification status above without establishing human pacing or final art.

Pupil timing `876f539` passes all 58 gameplay/tooling/asset CPU checks and nine
source-bound editor tests, including `PupilTiming`, the three dojo regressions,
both maai paths, physical archery, Playthrough and ScriptedFight. All nine
have zero selected errors/warnings. Real contact and telegraph timestamps
verify both authored cadences at every difficulty. Follow-up `24f27f9`
requires actual JSON numbers before conversion and rejects malformed pattern
presence outside attacking lessons. Its fresh actual `PupilTiming` run passes
the malformed-loader cases and all six lesson/difficulty combinations with
zero selected errors/warnings.

The earlier `44ffc35` Mac package passes build, cook, stage, untouched Title
startup and all 152 client tests with zero selected errors/warnings. That
package includes physical archery, but predates these latest dojo timing,
recovery and bundled-font changes. A new package is still required for them.
All evidence here is from this M2 Ultra; M1, Windows, normal-control pacing,
straight/diagonal animation and final visual acceptance remain separate.

## Chapter-one optional wood: source implementation, runtime pending

The post-range choice now has continuous collision floors and door openings.
Completing b07 leaves the hero on the range; walking into the wood starts b08,
while the south terrace reaches b09 with b08 incomplete. The wood's authored
exit alone completes b08, and the final bridge is walked to the smithy.
B09 still requires b07 alone. There is no live route teleport. Checkpoint
restoration explicitly spawns at the junction, wood entrance or smithy.

The stone grants c01 and the boundary stone grants c02 independently. Vista
and shrine interactions are separate lore discoveries. The clapper is a real
collision target: only a registered, player-owned yumi arrow released on the
vista floor can earn `codex_toshiya` on impact. Neither ordinary Interact,
melee, entering the wood, its exit, a missed arrow, nor a release outside the
vista grants that codex. It has a separate saved ledger bit and provisional
bilingual early-1600s copy, with no combat or registry-goods reward. Existing
schema-6 saves default the additive `WoodPoiMask` and `WoodJunction` fields to
zero/false. Retry retains discoveries, clears pending projectile identities,
and cannot regrant a discovery. New Campaign clears the ledger.

`test_wood_rules.py` checks the translated authored positions, separate
terrace, capsule clearance at the real door openings, malformed data, exact
45 m origin-to-target centers and exhaustive native ledger/junction cases.
`WoodExplore`, `WoodExitOnly` and `WoodLoader` are actual editor fixtures;
`ArcheryLesson` now reloads the saved physical junction and walks the terrace,
and `Playthrough` walks into the wood and visits its two separate finds.
These new fixtures are prepared but have **not been run in Unreal** in this
source-only slice. No build, render, Blender, packaged or performance proof
is claimed here.

Collision terrain remains flat and the POIs/clapper use primitive proxies.
The final 10-to-6 m slope, stone hollow, shrine, forest, vista composition,
clapper craft/sound and trail dressing are still art/layout work. The clapper
azimuth (south) and 30-by-40 cm face are configurable provisional values;
the standing-origin radius is 150 cm. The six authored trail points measure
142.92 m, whereas the prose says approximately 170 m; the points are retained.
These limitations do not qualify the authored final environment or pacing.

### Chapter-one archery HUD target clearance (source checkpoint)

The live b07 lesson now reserves a centered 20%-wide, 24%-high target window
(256 × 173 pixels at 1280 × 720), including while an arrow is released or
retrieved. Dialogue, tutorial prompts and ordinary notices use measured side
and bottom regions instead of a full-width stack lifted above the weapon.
Every Japanese and enabled English line remains present. Dialogue keeps the
selected subtitle size and speaker-name setting; glyph bounds remove only
empty font ascent/descent. Captions and projected labels avoid that same
window. The tracker reports the real near-target resolved arrows and hits,
unique hanging-target hits, and fetch countdown, rather than the task's
placeholder invader-defeat goal. Other lesson and chapter layouts retain
their previous path.

An additional synthetic load—four combat captions, the longest b07 line,
tutorial, worst-catalog locked-weapon refusal, fetch tracker, 720p and extra-
large subtitles—exceeds the measured allocator's capacity. It is not a
qualified configuration. The ordinary range does not generate those four
combat captions, and hero arrow sounds are excluded from `USoraCaptions`.
No text is dropped if such an overload is created; production layout
qualification returns failure. This limit is retained, not reported as a pass.

`test_aim_hud_layout.py` gives the shared C++ allocator independent 37/38-pixel
FreeType metrics from the shipped Noto font. It checks all ten authored b07
lines, both prompts, Japanese/English, all subtitle sizes, speaker settings,
mouse/gamepad labels, and 720p/1080p. It also checks simultaneous locked-weapon
refusals using every catalog weapon name as a conservative height envelope,
four live sound captions alongside dialogue/prompt (two when the refusal
notice is also active), actual arrow-resolution/fetch state transitions,
and rejection of the old captured center-overlap rectangles and insufficient
capacity. Existing chapter-four caption and rhythm-layout tests remain
separate regression gates. These CPU results do not establish Unreal font
rasterization or rendered contrast.

`SoraCapture.BowAim.Live` now checks the production bottom, tracker, caption
and interaction layouts on each real frame requested for a screenshot.
The existing pixel archive verifier and its contrast thresholds are unchanged.
Fresh 720p/1080p capture/archive passes and visual review remain required;
this source checkpoint does not supersede the earlier failed images.
The reservation is scoped to `IsArcheryLesson()`. General bow use, especially
the b08 wood clapper, is still **unqualified/open** for HUD clearance. Wood
NullRHI gameplay tests provide no evidence about that view.
