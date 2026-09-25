# Audio: cue list, buses, loudness and sources

**Status (2026-09-25):**

- **Built:**
  - a reproducible audio pipeline;
  - 133 original SFX, 3 music loops (8 WAV renders, including stems), 6 stingers and 3 MIDI scores;
  - a CC0 source library of about 3 GB, with a SHA-256 ledger;
  - a 104-cue proposal in [`Content/SourceArt/Audio/cues.proposed.json`](../Content/SourceArt/Audio/cues.proposed.json).
- **Not done:** nothing is imported into Unreal yet. No MetaSound, SoundClass or Submix assets exist.
- **Not heard:** no one has listened to any file. All QA is numerical (section 4.3).

The engineering lane owns the import and moves the approved cue data into `Content/Data`.

Related: [free-asset plan §3.11–3.12 and §4](art-research/free-asset-acquisition-plan.md), the
[story bible](campaign/story-bible.md) (L5 music states and captioned barks), and the chapter scripts
(`docs/campaign/chapter-0N.md`, "Music cues" and "Sound effects").

## 1. Sources and licences

| Tier | What | Where | Committed |
|---|---|---|---|
| **OWN** | Synthesised SFX (`scripts/audio/synth/*.py`), original scores, and their renders (`scripts/audio/music/`) | `Content/SourceArt/Audio/**` (WAV via LFS) | Yes |
| **PUB-CC0** | VCSL instruments; the 8 Kenney audio packs; 40 OpenGameArt items; Wikimedia Commons `File:Shakuhachi-flute-440Hz.ogg` | `Local/ThirdPartyRaw/audio/**` (gitignored) | Only the ledger: `scripts/assets/manifests/audio_*.json` |
| **REF** | Wikimedia Commons `File:02 Taiko2 (short).oga` (see below) | `Local/ThirdPartyRaw/audio/wikimedia/` | Only the restricted record: `scripts/assets/restricted/audio_wikimedia_reference.json` |

**Why the taiko file is REF.** The recording is CC0, but it performs Scott Harding's composition *Taiko*, whose
copyright was not cleared. It is kept as a timbre reference only and is never sampled. Its record is tier REF in
the restricted directory, so `validate_asset_ledger.py` fails if its path or content is ever tracked, and
`validate_audio.py` fails if a cue or the music manifest uses it.

**Original sources of re-hosted files.** Three CC0 files were downloaded from a site that re-hosts them. Their
records name the true source as `origin_url` and the download site as `mirror_url`. The origin page's licence
was also read (public page, no login; nothing was downloaded from Freesound) and its snapshot hash is kept
under `upstream`:

| Record | Origin (licence read there) | Downloaded from |
|---|---|---|
| `wikimedia/File:Shakuhachi-flute-440Hz.ogg` (sampled in the music) | Freesound sound 268183 by a since-deleted account, "Creative Commons 0" | Wikimedia Commons |
| `opengameart/water-waves` | Freesound sound 11505 by transitking, "Creative Commons 0" | OpenGameArt |
| `opengameart/fantozzis-footsteps-grasssand-stone` | Freesound pack 10338 (WalksForGames) by Fantozzi, "Creative Commons 0" | OpenGameArt |

`ThirdPartyNotices/ASSETS.md` lists every source, generated from these records by
`scripts/assets/generate_asset_notices.py`.

**Fetching.** `scripts/audio/fetch_cc0_audio.py`:

- fetches only from allowlisted hosts;
- re-reads each licence at fetch time from the primary page, API or LICENSE file:
  - Kenney: the page's licence field and the bundled `License.txt`;
  - OpenGameArt: the page's `License(s)` field;
  - VCSL: `LICENSE` and `README.md` at the pinned commit `c1ea7bc`;
  - Wikimedia: `extmetadata` from the API;
  - a re-hosted item's origin: its public Freesound page must state CC0 (read only, never downloaded from);
- records the evidence, a private page snapshot hash, the author, the URL, the byte size and the SHA-256 of
  every downloaded and extracted file;
- verifies VCSL files against their git blob ids;
- keeps the data volume at or above 35 GiB free and the raw tree at or below 4 GiB.

**OpenGameArt caveats.** Items that state an upstream chain, such as a Freesound origin, keep that statement in
`license_evidence.page_statement`, and the two Freesound origins above are recorded as `origin_url`. Items with an unverifiable chain were not selected. `amb-rain-loop-2` was
skipped automatically because it is larger than its size cap (113 MB against 80 MB).

**Not fetched, because the user step has not been approved.** Nothing was logged into and no terms were
accepted:

- Freesound needs an OAuth login (plan U2). It is the main source for horse, gravel, insects, tsurune and
  crowd sounds.
- Sonniss and the other RST libraries need the licence acknowledgement in plan U6.
- Pianobook needs a login.
- Voice is blocked on B6 and B7.

**AI-terms note.** None of the fetched sources has AI terms (all are CC0). No Epic, Fab or Sonniss content is
touched.

## 2. Mix buses

Buses map to UE SoundClasses and Submixes. The user sliders are **Master, Music, SFX, Voice, UI and Ambience**.

| Bus | Parent | Default | Notes |
|---|---|---|---|
| Master | — | 0 dB | Final limiter at -1 dBTP |
| Music | Master | -8 dB | A -16 LUFS bed sits around -24 LUFS in the full mix |
| SFX | Master | 0 dB | Parent of the SFX_* buses |
| SFX_Weapons | SFX | -2 dB | Gunfire, bows, beams |
| SFX_Melee | SFX | -1 dB | Whooshes, guards, parries |
| SFX_Impacts | SFX | -2 dB | Hits, shields, damage |
| SFX_Explosions | SFX | -3 dB | Detonations |
| SFX_Foley | SFX | -4 dB | Footsteps, horse, handling |
| SFX_Alien | SFX | -4 dB | Drones, fields, terminals |
| SFX_Telegraph | SFX | 0 dB | Boss audio telegraphs. **Never ducked or virtualised.** They stay audible at Music 0 and at low SFX settings (accessibility), and use a separate "Telegraph volume" floor |
| Voice | Master | 0 dB | Dialogue VO (Japanese primary, English subtitles) |
| Voice_Barks | Voice | 0 dB | Captioned boss barks: these are telegraphs too |
| UI | Master | -4 dB | Menus, wallet, registry |
| Ambience | Master | -3 dB | Beds and emitters |

**Ducking** (submix envelope followers or a SoundMix):

| Trigger | Target | Amount | Attack / release |
|---|---|---|---|
| Voice | Music | -6 dB | 80 / 450 ms |
| Voice | Ambience | -4 dB | 80 / 450 ms |
| SFX_Telegraph | Music | -3 dB | 20 / 300 ms |
| SFX_Explosions | Ambience | -6 dB | 10 / 800 ms |

**Attenuation presets:** `weapon_long` (80 m), `weapon_mid`, `melee_close` (25 m), `foley_short`, `foley_mid`,
`stealth_noise` (radius equals the AI hearing radius), `explosion` (150 m), `flyby` (Doppler), `drone`,
`ambient_emitter` and `far` (thunder, with distance delay). The full values are in the JSON.

## 3. Cue list (gameplay event → files)

Events are the `USoraGameEvents` delegates in `Source/SoraArena/Public/SoraGameEvents.h`. Weapon ids come from
`Content/Data/catalog.json`.

**Status key:**

- **ready-own:** project-owned renders exist.
- **needs-assembly:** OWN renders plus CC0 layers, combined in a MetaSound.
- **layers-cc0:** CC0 recordings only; import and trim them.
- **needed:** nothing usable yet.
- **blocked:** waits on a named user step.

Round-robin cues use `shuffle_no_repeat` with a small random pitch and volume range, as given in the JSON.

### 3.1 Ranged weapons: `OnWeaponFired`

| Weapon (id) | Cue | Files / layers | Status |
|---|---|---|---|
| Arc Carbine (1) | `weapon.fired.arc_carbine` | `Original/Weapons/wpn_arc_carbine_fire_01-04` | ready-own |
| Needle SMG (3) | `weapon.fired.needle_smg` | `wpn_needle_smg_fire_01-04` | ready-own |
| Phantom SMG (13) | `weapon.fired.phantom_smg` | Needle SMG files at -2 st, with a 3 kHz low-pass and a pre-echo in the MetaSound | ready-own (variant) |
| Coil Matchlock (5) | `weapon.fired.coil_matchlock` | See note 1 | needs-assembly |
| Repeater (9) | `weapon.fired.repeater` | CC0 Model 1894 and Marlin 336 lever-action reports | layers-cc0 |
| Pulse Carbine (11) | `weapon.fired.pulse_carbine` | `wpn_pulse_carbine_fire_01-04` | ready-own |
| Plasma Matchlock (14) | `weapon.charge / hold / fired.plasma_matchlock` | `wpn_plasma_matchlock_charge` (lock at 1.55 s), `_hold_loop`, `_fire_01-03` | ready-own |
| Shock Emitter (16) | `weapon.fired.shock_emitter` | `wpn_shock_emitter_start` / `_loop` / `_stop` | ready-own |
| Grenade Launcher (7) | `weapon.fired.grenade_launcher` | CC0 cannon and firework "shot" layers | layers-cc0 (needs a tube layer) |
| Micro-Mortar (15) | `weapon.fired.micro_mortar` | CC0 firework "cannon" layers | layers-cc0 |
| Healing Lance (17) | `weapon.fired.healing_lance` | Placeholder `shd_barrier_regen` | needed (a warm League heal voice) |
| Yumi (18) | `weapon.yumi.draw`, `.nock`, `weapon.fired.yumi`, `projectile.arrow.flyby` | See note 2 | layers-cc0 |
| Beam shots and the boss beam | `projectile.beam` | `wpn_energy_beam_start` / `_loop` / `_stop` | ready-own |
| Energy reload window | `weapon.reload.cell_eject` | `wpn_cell_eject_01-02` (captioned) | ready-own |

Notes:

1. **Coil Matchlock:** the sequence is `wpn_coil_matchlock_whine`, then the CC0 pan flash (flare ignition),
   then about 40 ms later a report built from the CC0 Arisaka and Mosin-Nagant recordings.
2. **Yumi:** the layers are CC0 English longbow and Scythian recurve draw, nock, shoot and arrow pass-by. The
   **tsurune** (string ring) and yugaeri are missing. They need our own recording, or Freesound CC BY after U2.

### 3.2 Melee: `OnMeleeCommitted`, `OnStrikeResolved`, `OnGuarded`, `OnParried`

| Event and condition | Cue | Files / layers | Status |
|---|---|---|---|
| Committed: katana, wakizashi or tantō (0 / 4 / 10), WindupSeconds < 0.5 | `melee.committed.<weapon>` | `mel_whoosh_katana_light_01-04` + CC0 "Katana Swing" (short blades at +40 to +160 cents) | needs-assembly |
| Same weapons, WindupSeconds ≥ 0.5 | `.heavy` | `mel_whoosh_katana_heavy_01-03` | ready-own |
| Naginata, Monofilament Naginata (20, 12) | `melee.committed.naginata` | `mel_whoosh_naginata_sweep_01-03` | ready-own |
| Yari (19) | `melee.committed.yari` | `mel_whoosh_yari_thrust_01-03` + CC0 "Spear Swing" | needs-assembly |
| Kusarigama (2) | `melee.committed.kusarigama` | `mel_whoosh_kusarigama_chain_01-02` + CC0 chain winch | needs-assembly |
| Kanabō, Forge Hammer (6, 8) | `melee.committed.kanabo` | `mel_whoosh_kanabo_01-02` | ready-own |
| Dojo bokutō / fukuro-shinai | `melee.committed.bokuto`, `.fukuro_shinai` | `mel_whoosh_bokuto_*`, `mel_whoosh_fukuro_shinai_*` | ready-own |
| StrikeResolved, bHit | `melee.strike.hit_body` | Kenney punch and soft impacts (placeholder) | needed: own cloth, armour and cut foley |
| Guarded | `melee.guard` | `mel_guard_block_01-03` + CC0 "Katana Blade on Blade", "Hilt on Blade" (real steel) | needs-assembly |
| Parried | `melee.parry` | `mel_parry_full_light/heavy_01-03` + CC0 katana clashes; add `mel_parry_layer_sparks_*` for awase | needs-assembly |
| Guard / parry / strike with bDojo | `melee.dojo.clack` | `mel_bokuto_clack_01-04` + CC0 wood impacts | needs-assembly |
| Draw / sheathe | `melee.katana.draw`, `.sheathe` | CC0 "Katana Draw Fast/Slow", "Katana Sheath Fast/Slow" | layers-cc0 (the nōtō click needs close foley) |

`mel_parry_layer_{clang,scrape,sparks,body}_*` are also shipped as separate layers. The MetaSound can scale
them by parry quality.

### 3.3 Damage, death and explosions

| Event | Cue | Files / layers | Status |
|---|---|---|---|
| `OnDamaged`, victim is the local player | `player.damaged` | `mel_parry_layer_body_*` + Kenney punch; SFX-bus low-pass under 25 % health | needs-assembly (pain efforts are VO, blocked on B6) |
| `OnDied`, local player, not sparring | `player.died` | `Music/Stingers/mus_sting_player_death` | ready-own |
| `OnDied`, another actor | `enemy.died` | Body fall and armour rattle | needed |
| `OnDied` with bSparring (dojo point) | `sparring.point` | `mus_sting_duel_point` (hyoshigi and drum) | ready-own |
| `OnDetonated` | `explosion.detonated` | CC0 bangs (close), muffled explosion (tail), cannon; layers scaled by radius and damage; sub drop synthesised | layers-cc0 (needs a debris layer) |

### 3.4 Bosses: `OnBossPhase`

Telegraph timing follows story bible §8. **Cyan** means a locked aim or beam; **amber** means a cleave or an
area attack. Each telegraph file lasts exactly the Normal windup, and the strike lands at 900 or 1500 ms. For
Easy (+30 %) and Hard (−15 %), time-stretch the file; never pitch it. Telegraphs are captioned.

| Phase | Cue | Files | Status |
|---|---|---|---|
| Arrived | `boss.arrived` | `mus_sting_boss_phase` | ready-own |
| Windup, bBeam | `boss.windup.beam` | `Original/Telegraphs/tel_lock_cyan_900ms` 「［照準固定音］」 | ready-own |
| Windup, cleave | `boss.windup.cleave` | `tel_cleave_amber_01` (900 ms) | ready-own |
| Windup, 1500 ms area (seizure tiles, 追証) | `boss.windup.area_1500` | `tel_cleave_amber_02`, `tel_margin_call_riser_1500ms` | ready-own |
| Strike, beam / cleave | `boss.strike.beam`, `.cleave` | Beam start and loop / kanabō whoosh plus body | ready-own |
| Defeated | `boss.defeated` | Placeholder `mus_sting_boss_phase` | needed (a release sting per boss) |
| Shields (Collatera, drones) | `boss.shield.hit`, `.break`, `.regen`, `barrier.hum` | `shd_barrier_*` | ready-own |

**Still needed:**

- Eskro's 700 ms reconciliation chirp and sonar ring;
- Dunark's tally clicks (these must stay audible at Music 0);
- Hakari's weigh-coil hum and kneel tick;
- the Val Amort shard orbit.

### 3.5 Campaign progression

| Event | Cue | Files | Status |
|---|---|---|---|
| `OnChapterStarted` | `chapter.started` | `mus_sting_chapter_start`: hyoshigi ×2, then the ōdaiko and gong hit at 1.0 s, where the vermillion seal lands | ready-own |
| `OnChapterCompleted` | `chapter.completed` | `mus_sting_chapter_complete` | ready-own |
| `OnSiteRestored` | `site.restored` | `mus_sting_site_restored` (Music bus) + `ui_xor_credit_soroban_*` (UI bus, when the registry entry is written) | ready-own |
| Sky splits (ch01.b13), debt seals (ch02) | `sfx.alien.sky_seam`, `sfx.alien.debt_seal_clamp` | `Original/Alien/sfx_alien_*` | ready-own |

### 3.6 Footsteps (anim notify × physical material)

| Surface | Cue | Files / layers | Status |
|---|---|---|---|
| Hinoki boards, engawa | `foot.wood` | Kenney wood steps (placeholder) + `fol_board_creak_*` (stealth layer) | layers-cc0 (needs suri-ashi foley) |
| Tatami | `foot.tatami` | Kenney carpet (placeholder) | needed |
| Packed earth, sand | `foot.earth` | CC0 Fantozzi sand steps | layers-cc0 |
| Stone, ishigaki | `foot.stone` | CC0 Fantozzi stone steps | layers-cc0 |
| Grass | `foot.grass` | Kenney grass (placeholder) | layers-cc0 |
| Paddy, puddle (stealth class "puddle") | `foot.water` | CC0 short water splashes | layers-cc0 |
| Gravel (stealth class) | `foot.gravel` | — | needed |
| Nightingale floor (ch06) | `foot.nightingale_floor` | `Original/Foley/fol_nightingale_floor_01-06` (captioned; deliberately unlike birdsong) | ready-own |
| Ship gantry grating (ch07) | `foot.metal_grating` | — | needed |

### 3.7 Horse

All horse cues are **blocked**: `horse.trot`, `.walk`, `.gallop`, `.snort`, `.whinny` and `.tack`.

- The only CC0 file, OpenGameArt "Horse Trotting", is jacket-on-bottle foley. It is a placeholder only.
- Unshod hooves on earth and wood, snorts, bit and abumi jingle, and saddle creak need either the Freesound
  login (U2: about 135 CC0 gallops, 34 snorts, 40 whinnies) or our own recordings.

### 3.8 Ambience by location and weather

| Place / weather | Cue | Files / layers | Status |
|---|---|---|---|
| Nyaagyu Estate by day (ch01, Arena 1) | `amb.estate.day` | CC0 park field recordings (birds before rain, wind; 48 kHz, over 8 min) + crow | layers-cc0 (uguisu and pheasant needed) |
| Streams (estate, fields, foundry) | `amb.stream` | CC0 small-river recording + waves | layers-cc0 |
| Rain (ch03 卯の花腐し, Lantern Ward) | `amb.rain` | CC0 rain loops + drip loop for eave emitters | layers-cc0 |
| Thunder (ch05, ch07) | `amb.thunder` | CC0 rain with long thunder | layers-cc0 |
| Fire (ch02 burning estate, forges) | `amb.fire` | CC0 fireplace loop + crackle | layers-cc0 |
| Smithy (ch01.b09), Silk Foundry (ch05, Arena 3) | `amb.smithy` | CC0 workshop hammering + 45 lb anvil + VCSL anvil | layers-cc0 |
| Flagship interiors (ch07), Ledger Engine (ch07–08) | `amb.alien.flagship_engine`, `.ledger_engine` | `amb_alien_engine_core_loop` (12 s), `amb_alien_ledger_engine_loop` (5/8, 8 s) | ready-own |
| Drones, seizure fields, debt terminals | `amb.alien.drone`, `.seizure_field`, `.debt_terminal` | `amb_alien_*_loop` | ready-own |
| Ledger vault (ch06, Arena 4 Debt Citadel) | `amb.vault` | CC0 drips + low-passed Ledger Engine | needs-assembly |
| Night insects, frogs (ch04, ch06) | `amb.night_insects` | — | needed |
| Typhoon (ch07) | `amb.typhoon` | CC0 park wind as a base only | needed |
| Festival (ch08) | `amb.festival` | CC0 fireworks; crowd and 祭囃子 needed | needed |

### 3.9 UI (all ready-own, `Original/UI/`, 2D)

| Cue | File | Cue | File |
|---|---|---|---|
| `ui.click` | `ui_click_wood_01-04` | `ui.hover` | `ui_hover_wood_01-03` |
| `ui.confirm` | `ui_confirm_rin` | `ui.back` | `ui_back_wood_01-02` |
| `ui.error` | `ui_error_knock_01-02` | `ui.tab` | `ui_tab_paper_01-03` |
| `ui.menu.open` | `ui_menu_open_fusuma` | `ui.menu.close` | `ui_menu_close_fusuma` |
| `ui.notify` | `ui_notify_bell_01-02` | `ui.objective` | `ui_objective_update_rin` |
| `ui.xor.credited` | `ui_xor_credit_soroban_01-02` | `ui.wallet.signed` | `ui_wallet_seal_stamp_01-02` |
| `ui.slider` | `ui_slider_tick` | `ui.alien.chime`, `ui.alien.deny` | `ui_alien_chime_01-02`, `ui_alien_deny` (Credit House only) |

### 3.10 Music states

The chapter scripts define **108 L5 music states** (ch01 10, ch02 11, ch03 13, ch04 17, ch05 18, ch06 12,
ch07 14, ch08 13). Three are written and rendered:

| State | Piece | Files | Use |
|---|---|---|---|
| Title / main menu (and a sketch for `credits_main`, `ch03_oath`) | 「猫柳生の風」 Wind over Nyaagyū: 66 BPM, D miyako-bushi; shakuhachi theme over hirajoshi koto and taiko | `mus_title_nyaagyu_wind_intro.wav` (20.5 s) + `_loop.wav` (58.2 s, 16 bars) | Play the intro, then start the loop at **sample 698,182** (Quartz, sample-accurate) while the intro tail rings |
| `ch03_stealth` (and `ch03_escort`, `ch06_vault_stealth` until they have their own) | 「占領の街」 Occupied Streets: 84 BPM, A miyako-bushi | `_stem_base`, `_stem_pulse`, `_stem_perc`, `_stem_search` + `_loop` (the alert mix), 45.7 s | See the stem table below |
| `mus_ch07_hangar`, `mus_boss_collatera` P1–P2 | 「複利号」 The Compound-Interest Flagship: 132 BPM, a minor-third cycle and octatonic glass arpeggios against taiko | `_stem_synth`, `_stem_taiko` + `_loop`, 43.6 s | P1 = synth; P2 = synth + taiko; P3 = taiko (the design's single tsuzumi is still needed) |

**Stealth stem mixes:**

| State | Stems |
|---|---|
| Unaware | base |
| Suspicious | base + pulse |
| Alert | base + pulse + perc |
| Search | base + pulse + search |

Crossfade times: 250 ms into alert, 2.5 s out of alert.

The six stingers (section 3.5, plus death and duel point) use the same instruments and mode.

**Music rules:**

- Loops are sample-exact; loop the whole file. Every file carries a `smpl` loop chunk.
- Stems start together and change only in gain.
- A stinger ducks the bed -6 dB for its length. Never stack two stingers.
- Dunark's measures (ch02, 46/55/60 BPM) and the bellows, aizuchi and press tempos (ch05, ch06) must lock to
  gameplay timing through Quartz. Those states are not written yet.

## 4. Loudness targets and QA

### 4.1 Targets

| Class | Target (as authored) | Achieved |
|---|---|---|
| Full game mix | **-24 LUFS integrated ±2 LU, ≤ -1 dBTP** over 30+ minutes of play (Sony ASWG-R001 home-console guideline) | To measure in a packaged build |
| Music loop beds | **-16 LUFS integrated, ≤ -1 dBTP** | All three loops -16.0 LUFS, -1.2 dBTP. The master limiter took 2.6–4.7 dB off the loudest taiko hits (see note 1) |
| Music stingers | Max momentary -16 LUFS, ≤ -1 dBTP | -16.0 M; true peak -1.1 to -6.7 dBTP |
| Ambience beds | -26 LUFS integrated, ≤ -3 dBTP | CC0 beds are imported and levelled at import (not done yet) |
| Alien machinery loops | -24 LUFS integrated (debt terminal -28) | -24.0 / -28.0 |
| Weapon loops and beams | -18 to -22 LUFS integrated | -18.0 / -20.0 / -22.0 |
| Sustained one-shots (whooshes, charges, shields, telegraphs, alien events) | Max momentary -12 to -21 LUFS by category | On target (the manifest lists each file) |
| Transient one-shots (gunfire, parries, guards, clacks, UI clicks) | Peak-referenced at -1 dBTP (UI clicks -3, slider -12) after 3–9 dB of 4× oversampled soft-clip density; momentary loudness reported (note 2) | Gunfire -10 to -20 M; parries -10 to -16 M |
| UI | Max momentary -19 to -26 LUFS | On target |
| Dialogue VO | -20 LUFS integrated per line, ≤ -2 dBTP | Not recorded (B6 / B7) |

Notes:

1. The limiter amount is recorded per piece as `master_limiter_max_gr_db`. Stems share the mix gain and its
   limiter curve, so a stem is not normalised on its own. Stem loudness: stealth base -23.9, pulse -22.3,
   perc -18.1, search -23.2; flagship synth -18.2, taiko -20.1 LUFS.
2. A 400 ms momentary window under-reads sounds shorter than about 100 ms. Driving a 50 ms shot to -12 LUFS M
   would crush it, so transients are peak-referenced instead.

### 4.2 Normalisation

- **One-shots:** DC removal (12 Hz zero-phase), head and tail trim at -72 dBFS, then gain to the target by
  bisection. Look-ahead true-peak limiting is allowed only up to each cue's `limit`.
- **Loops:** DC is removed in the frequency domain. Gain only, never limiting, so the wrap stays exact.
- **Music:** one master gain plus one shared, circularly computed limiter curve, found by bisection so that the
  limited loop mix meets -16 LUFS.

### 4.3 Listen-free QA (`scripts/audio/qa_audio.py`, run by every build and by `validate_audio.py`)

For every WAV the script measures:

- sample peak and true peak (4× oversampled);
- integrated loudness (ITU-R BS.1770-4, via pyloudnorm);
- max momentary loudness;
- RMS;
- DC offset;
- full-scale clipping runs;
- leading and trailing silence.

**Loop checks:**

- the sample jump at the wrap against the file's own 99.9th-percentile step;
- the curvature (second difference) across the wrap against its 99.9th percentile;
- informational only: the > 6 kHz energy across the wrap, and the head/tail level difference.

**Hard failures:**

- clipping (two or more consecutive full-scale samples);
- true peak above -0.5 dBTP;
- DC above -54 dBFS;
- an all-silent file;
- a loop click (a wrap jump or curvature above 3× the file's own 99.9th percentile).

**Current result: 149 WAVs (19 of them loops), 0 failures.**

- The largest wrap jump is 1.0× the percentile. That is the flagship synth stem and mix, whose loop starts on
  note onsets, as music at bar 1 does. Every other loop is at or below 0.77× (the energy beam).
- The largest DC estimate is -55.1 dBFS (a UI bell tail; the limit is -54).
- The highest true peak is -1.0 dBTP.

`scripts/audio/validate_audio.py` also re-hashes the 2,119 raw CC0 files against the ledger. It checks that
every file under `Content/SourceArt/Audio` has an OWN record with a matching SHA-256, that `Local/` is ignored
and untracked, and that every path in the cue proposal exists.

## 5. Accessibility

- **Captions:** telegraph and stealth-critical cues carry a caption (`［照準固定音］`, `［鶯張りが鳴る］`,
  `［障壁が砕ける］` …). Captions are shown in Japanese first with English subtitles, following bible §18.
- **Telegraph bus:** boss telegraphs have their own bus with a minimum-volume floor. They are never ducked or
  virtualised.
- **Music at 0:** gameplay-timing sounds (Dunark tally clicks, bellows and press beats) must stay on SFX
  buses, so they remain audible when music is off.
- **Mono and headroom:** mono downmix and a "night mode" (lower Master dynamic range) apply at the Master
  submix. The music loops' side-to-mid energy ratio is 0.07–0.18, so there is no strongly out-of-phase
  content, but a mono fold-down has not been listened to.

## 6. Pipeline and files

| Path | What |
|---|---|
| `scripts/audio/fetch_cc0_audio.py` | Allowlisted CC0 fetch, licence verification and ledger manifests |
| `scripts/audio/synth/` | `dsp.py` (DSP, loudness, loop-safe processing, WAV with `smpl` loops), `sfx_ui.py`, `sfx_melee.py`, `sfx_scifi.py`, `sfx_foley.py`, `build_sfx.py` |
| `scripts/audio/music/` | `engine.py` (instruments, circular loop renderer, mastering, MIDI export), `scores/*.py` (the three scores), `render_music.py`, `render_stingers.py`, `sample_tuning.json` (measured sample pitches) |
| `scripts/audio/qa_audio.py`, `validate_audio.py`, `build_cue_proposal.py` | QA, ledger validation, cue proposal |
| `scripts/assets/manifests/audio_{vcsl,kenney,opengameart,wikimedia}.json` | Schema-2 ledger records for the raw CC0 sources |
| `Content/SourceArt/Audio/` | The OWN renders, their manifests and [README](../Content/SourceArt/Audio/README.md) |

## 7. Gaps, in priority order

1. **Import into UE 5.8.** This belongs to the engineering lane. Import the 149 WAVs as SoundWaves, build
   SoundClasses and Submixes from §2, build MetaSounds for the multi-layer cues (`needs-assembly`), and set up
   Quartz music transitions. It also means moving the approved `cues.proposed.json` into `Content/Data`.
2. **Human listening and mix review** of everything here (plan §4.3). No file has been auditioned.
3. **User steps:**
   - Freesound OAuth (U2) unblocks horse, gravel, insects, tatami, crowd and tsurune.
   - The Sonniss acknowledgement (U6) unblocks professional melee and foley layers (RST, with an OWN or CC0
     fallback required).
4. **Own foley and performances:**
   - suri-ashi on hinoki;
   - armour and cloth;
   - tsurune;
   - nōtō click;
   - a real koto, shakuhachi and taiko session for the final score (the path to AAA in plan §3.12).
5. **The remaining 105 music states**, the per-boss telegraph voices, and VO (B6 / B7).
