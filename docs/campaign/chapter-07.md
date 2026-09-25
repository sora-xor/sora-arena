# 第七章 異星旗艦への突撃 / Chapter 7: Alien Flagship Assault

> **Monetary boundary (bible §2).** In this chapter, as in the whole campaign, SORA XOR (and the registry that leads to it) is a production-only storytelling premise. XOR is cut only against finished, inspected goods, is never shown as a balance or converted, and has no link to multiplayer XOR bonds, NFTs, wallets or IrohaConnect. It makes no claim about real-world money, investment or policy, and it does not describe the real SORA network or the design in the SORA Nexus article. **Review note (C1 lead, 2026-09-25):** names, calendar, speaker ids, Japanese punctuation and YAML field names in this file follow bible §9.1, §12.5 and §18.

**Status:** production design and script for Wave 2 lane C1 (chapter `ch07_flagship`). It follows the [story bible](story-bible.md) and changes nothing in it; where they differ, the bible wins. All numbers here (layouts, waves, timings, HP) are **proposals** for the owning lanes to ratify:

- L1: beats, checkpoints, saves, dialogue data.
- L2: enemies, shields, stealth.
- L3: `boss_collatera`.
- L4: HUD prompts and the wind indicator.
- L5: music and sound.
- C3: flagship kit, bastion storm dressing, Kaya Moor.
- C4: mission build.
- C9: cinematics.

Voice is not recorded yet (catalog `voice_over: not_recorded`). Native Japanese review (B7) and historian and practitioner review are pending.

**Related:**

- [catalog.json](../../Content/Data/catalog.json) (schema 3, chapter index 6)
- [offline acceptance](offline-acceptance.md)
- [historical arms](../historical-arms.md)
- [horse tack references](../historical-horse-tack-art-reference.md)
- [SORA kamon runtime art](../sora-kamon-runtime-art.md)
- [photoreal acceptance](../art-direction/photoreal-acceptance.md)

## 0. At a glance

| | |
|---|---|
| Chapter id / map | `ch07_flagship` / map 3 (Debt Citadel, storm variant) plus new flagship spaces (C3) |
| Target | **50 min** (3,000 s), 16 beats; bible §10 range per chapter ±20% in telemetry |
| Mix (min) | Combat 28 · Explore 2 · Stealth 4 · Production 7 · Mounted 0 · Cinematic/dialogue 9 (identical to bible §10) |
| Boss | `boss_collatera` (旗艦提督コラテラ), 3 phases, checkpoint per phase |
| Weapons unlocked | 9 連発銃 (b01), 11 パルス・カービン (b06), 14 プラズマ火縄銃 (b08), 16 電撃放射器 (b11); 13 auto-granted at b01 if missed in ch06 |
| Mechanic flags | `shield_break` (b06); proposed `charged_shot` (b08), `wind_brace` (b10) |
| New systems | Personal energy shields; charged shots; wind push and arrow drift; reverse-torque override crank with ratchet locks; one-shot bell lure; hull-boom noise masking; helm-trim events inside a hold |
| Production sites | site 0 地上の通信塔 → b02 · site 1 収奪の動力炉 → b07 · site 2 脱出の信号機 → b14 (catalog order kept) |
| Registry page | 押収品の返還 430駄 (recorded as returned; **no tally cut**, per charter article 1) |
| Dialogue | **137 lines** (113 one-shot, 24 repeatable barks) |
| Collectibles | 6 (chapter-local mask bits 0–5) |
| Humor | H1 (approved #6, b03 「くしゃみ、するな。」); H2 proposed (b09, Iota's recount). Never during the boss, grief or captivity. |

---

## 1. Synopsis, play time, locations and conditions

### 1.1 Synopsis

> 野分の夜、旗艦『複利号』は城塞の錨台から一本の綱を垂らし、猫柳生の米も刀も寺の鐘も空へ吸い上げていた。空紋一揆は嵐の中で錨台を襲い、ニャーコトと小萩は米俵に潜んで艦へ上がる。二人は収奪の昇降機を逆に回して荷を地上へ返し、外殻の稜線を渡って艦橋へ至る。提督コラテラを退け、信号灯で民を逃がし、死にゆく艦を無人の萱野原へ落とす。だが瓦礫の上に響いたのは、大徴収官の新たな布告だった。

Ten days after the vault raid, an early-autumn typhoon (野分, *nowaki*) crosses Yamato. The Credit House picked this night on purpose: its books value a league in a storm at zero. The flagship 『複利号』 (Fukuri-gō, "Compound Interest") holds station in the storm's calm eye above the Debt Citadel. It is moored by a single tether to an anchor pylon grafted onto the castle's old stonework. Up that tether a cargo lift hauls the valley's seized goods, 1,200 horse-loads planned for tonight: rice, lacquer chests, swords, armor, and the village temple bell.

**The plan (b01).** At the Hidden Valley war council, Oyuki lays out three tasks: cut the relay, send the goods down, bring the ship down where no one lives. Iota supplies the loading schedule and the only safe landing ground, Kaya Moor. Toranosuke, newly sworn to the League, will wait there with riders. Tetsugorō issues the foundry-built Repeater.

**Boarding (b02–b05).** In driving rain the League storms the anchor bastion, and Nyaakoto cuts the ground signal relay (site 0). With the ship's cargo inspection blind, he and Kohagi ride up the lift inside hollow rice bales. A collared loader recognizes the chalk mon on their bale and says nothing; an enforcer logs the extra weight as "within the margin of error." In the hold they slip among Nyaagyu's tagged heirlooms. In an optional side vault Nyaakoto finds the dojo's own name board, every pupil's plaque stuck with an account number.

**The lift reversed (b06–b07).** In the reckoning engine, a slow halo of glass abaci computes interest without end. There the League meets personal energy shields for the first time and captures the Pulse Carbine. Nyaakoto throws his weight against the manual override wheel, Kohagi setting the pawls, until the lift runs backwards and the goods ride down to the League (site 1). Oyuki records them as returned, not issued: nothing new was made, so no tally is cut.

**To the bridge (b08–b11).** Nyaakoto fights through the hangar and captures a Plasma Matchlock from a marksman. With the spine corridor sealed, he climbs out onto the hull ridge above a moonlit sea of cloud, where gusts at the edge of the eye push him and bend his arrows. At the bridge approach he takes a Shock Emitter from a security rack and breaks through the tower shields.

**Collatera (b12–b14).** Admiral Collatera offers a "survival loan"; Nyaakoto answers that the League can make what it needs. She fights as a twin-pistol gunslinger behind a regenerating shield. Then she lists the ship and calls "margin" on his cover. Finally, her shield burned out, she draws her Liquidation Blade for a short duel. Nyaakoto knocks her down and does not finish her. With the ship dying, he holds the helm while Kohagi lights the evacuation beacon (site 2). Through the window, a line of Sora lanterns climbs the ridge as villagers move to safety.

**The fall (b15–b16).** Nyaakoto offers Collatera his hand; she refuses: "The liability goes down with the ship." He and Kohagi leap from the hangar on a cargo sled as the flagship ploughs into the empty moor. Toranosuke's riders come out of the rain with Kurimaru. Then every hull horn in the wreck, and every door numeral in the valley, carries Val Amort's decree: all collateral is now called, and people, too, are collateral. At dawn, the castle.

### 1.2 Target play time and pacing

| Category | Beats | Minutes | Bible §10 |
|---|---|---|---|
| Combat (C) | b02, b06, b08, b10, b11, b13 | 28.0 | 28 |
| Explore (E) | b05 | 2.0 | 2 |
| Stealth (S) | b04 | 4.0 | 4 |
| Production (P) | b07, b14 | 7.0 | 7 |
| Mounted (M) | none | 0 | 0 |
| Cinematic/dialogue (Cin) | b01, b03, b09, b12, b15, b16 | 9.0 | 9 |
| **Total** | 16 | **50.0** | **50** |

Minutes include typical optional engagement and about 12% retry overhead on Normal (真剣), as in bible §10. Combat intensity peaks twice, at b08 and b13, with a breath at b09 (radio, walk-and-talk) and a vista at the start of b10. A player who skips b05 finishes about 2 min sooner.

### 1.3 Time, weather and lighting

The chapter plays in one night, 元和九年八月十一日 (Genna 9, 8th month, 11th night; about early September by the solar calendar; bible §9.1). In fiction the storm's eye passes over the Citadel: the ship waits inside the eye, so the chapter moves from the storm front (b02) up into the calm eye (b03–b10) and back out through the rear eyewall (b13–b16). Lightning always respects the flash-reduction setting (L4).

| Beats / place | Sky and key light | Weather and FX | Special notes | Mac fallback |
|---|---|---|---|---|
| b01 `pl_kakuredani` | Night. Andon key 1900 K inside the 陣幕; Iota's slate projection 8500 K on faces | Outer rain bands; gusts shake the 陣幕 (cloth sim); distant lightning, no thunder until the cut | Andon, not hand lanterns: hand lanterns blow out | Baked lantern bounce; 2 shadowed lights |
| b02 `pl_anchor_bastion` | Near-black storm sky; alien floodlights 8500 K from the pylon; lightning fill on a fixed schedule (17/23/15/21 s) | Horizontal rain, sheet runoff on the 石垣, puddles; visibility 45 m; wind is visual only in the walled bailey | Wet stone and timber carry the image (roughness 0.2–0.35 wet); muzzle flashes are the only warm light | Height fog in place of volumetric; rain particle cap; ≤ 8 shadowed lights |
| b03 lift (cinematic) | Rain → inside cloud (grey-white volumetric) → breaking out into the eye: moonlight 4100 K | Cloud ascent; spray; the tether's cold glow | Reveal of the stadium-shaped eyewall and the cloud sea below | Pre-rendered cloud cards plus skybox |
| b04–b09 ship interior | Cold low-key strip lights 8000 K; warm goods lit only by reflection | Hull groans; condensation; drum-pit steam in the engine room | Reckoning-engine abaci throw slow cyan light bands. They are soft and must never read as beam telegraphs | Emissive strips unshadowed; bands as a light function |
| b05 `pl_seized_vault` | One seized andon at 1900 K, lit by the loaders to work by | Dust in the lamp's cone | Warm light leaking under the door is the discovery cue | Same |
| b10 `pl_hull_ridge` | Clear eye sky; moon high to the south-west, 4100 K; stars | Cloud sea 400 m below with in-cloud lightning; the eyewall stadium on the horizon 8–12 km away; spindrift in gusts | The chapter's vista. The tenugui strip on the bow shows the wind | Skybox cloud sea; simplified volumetric clouds |
| b11–b14 bridge | Cold amphitheatre, low-key 7000–9000 K; the window shows the approaching eyewall | b14: the ship enters the eyewall: rain lashing the glass, strobing lightning | Through the window in b14: a line of mon-painted lanterns (warm points) climbing the ridge | Lightning as a clamped directional pulse |
| b15–b16 `pl_kayanohara` | Storm rear bands; no torches (wind); the wreck's dying cyan ledger lines and lightning are the light | Rain easing, strong wind through 芒 (susuki) grass | Riders emerge as lightning silhouettes | Card grass; wreck emissive baked |

### 1.4 Locations and layouts

Coordinates are in metres in each place's own frame: +X forward, +Y right (starboard or east), +Z up. Every `sp_` (spawn), `ps_` (player start), `vol_` (volume) and `pt_` (patrol) id below is referenced by the YAML in §7.

**Arena collision rule (bible §14).** All campaign geometry for `pl_anchor_bastion` lives in a campaign-only sublevel. It never changes Arena 3's multiplayer or practice collision.

#### `pl_kakuredani`: Hidden Valley war council (b01, cinematic only)

- **Space:** reuses the ch02 hub. The council sits in a 10 × 7 m 陣幕 enclosure under the workshop lean-to. At its centre is a 2.4 × 1.2 m map table with the registry books, a soroban and the 割符 box.
- **Projection:** Iota's key-slate throws the flagship's schematic onto a stretched washi screen: alien light on hand-made paper, the chapter's visual thesis.
- **Camera path:** from the registry desk, to the table, to the screen. The cinematic ends when a gust tears a 陣幕 panel loose to reveal the Citadel under lightning and the tether rising into cloud.
- **End state:** a fade to `ps_ch07_b02_start`.

#### `pl_anchor_bastion`: tether anchor bastion (b02, b03; Arena 3 storm variant)

- **Frame and bounds:** origin at the foot of the 雁木 stone steps at the south breach. `vol_bastion_bounds` is X −10…70, Y −35…35, Z −2…30. The bailey (曲輪) floor is at Z 6 m: packed earth and gravel with standing water.
- **Staging (safe):**
  - `ps_ch07_b02_start` at (−18, 0, 0) under a League lean-to behind the outer moat bank.
  - `vol_bastion_staging` covers X −24…−10, Y −10…10.
  - It holds the chapter's first supply point, `sup_ch07_bastion` (weapon 13 selectable here if it was auto-granted), plus Okuzu's aid mat and Tamakichi's useless damp shells.
- **Approach:** a 粗朶 (brushwood fascine) causeway the League laid across the flooded moat (X −10…0, Y −3…3). It leads to the 6 m 石垣 (打込接ぎ, 算木積み corners).
- **Two ways up:**
  - The 雁木 (4 m wide, about 30°) at Y −4…0. `vol_bastion_steps` (X −2…4, Y −6…2) starts wave 1.
  - A rubble ramp through a collapsed section at Y 17…24, the east flank.
- **Wall line:** a surviving 狭間塀 parapet runs along X 0…2, and the League 鉄砲 fire through its loopholes. Ally marks: `teppo_1` (1, −8), `teppo_2` (1, −4), `teppo_3` (1, 20), `teppo_4` (1, 23). Otane takes the rubble ramp.
- **多聞櫓 (tamon yagura):** a two-storey long turret along the east wall, X 5…50, Y 28…35.
  - The marksman `sp_tamon_upper` (30, 30, 10) shoots from an upper 狭間.
  - A south door at (8, 28, 6) lets the player climb inside and take him at sword range. This is the optional third route.
- **Anchor pylon:** north end, centred (62, 0, 6). A 10 m black-glass pylon bolted onto the old 天守台, with the tether rising from its top at Z 36.
  - The lift cradle (12 × 8 m) docks at its foot; `vol_lift_cradle` is X 49…61, Y −4…4.
  - A service gantry rings it at Z 18 (`sp_pylon_gantry` (60, −6, 18)).
- **Signal relay:** a 14 m lattice mast on the west 櫓台 at (40, −28). Three junction boxes, 2 s each to cut:
  - `relay_j1` (38, −25, 6) at the mast foot;
  - `relay_j2` (41, −31, 9) on the 櫓台 stair landing;
  - `relay_j3` (30, −31, 6) on the cable run along the wall.
  - `vol_relay_foot` (X 28…46, Y −35…−20) triggers Kohagi's callout.
- **Cover:**
  - Seized rice-bale stacks awaiting loading at (15, −10), (20, 8), (32, −4), (45, 10), built from the existing cargo stack.
  - Toppled alien cargo pods at (25, 18) and (48, −12).
  - A 土塀 fragment (10…18, 20).
  - A stone lantern base (36, 6).
- **Enemy spawns:** `sp_bastion_gate` (12, −2, 6) guards the stair head with patrol `pt_gangi_top`. `sp_lift_platform` (55, 0, 6) and `sp_bastion_north` (68, 25, 6), a sally port, bring the later waves.
- **Sightlines:**
  - The bailey is a 55 m open yard. The turret marksman covers it laterally (about 30–45 m) and the gantry marksman looks down its long axis (50–60 m).
  - Rain limits clear sight to 45 m; each lightning flash shows both marksmen's glints for 0.5 s.
  - The relay sits under the tamon marksman's cone, so the flank or the tower route pays off.
- **Exit:** once all waves are cleared and all three junctions are cut, enter `vol_lift_cradle` to start b03.

#### `pl_cargo_hold`: the belly hold (b04)

- **Size:** 120 m (X 0…120, aft to fore) × 36 m (Y −18…18) × 18 m high; `vol_cargo_hold`. The floor is graphite deck plate with grated drainage channels.
- **Entry:** the aft lift well (X 0…10). `ps_ch07_b04_start` (6, 12, 0.8) is inside the stowaway bale on the starboard conveyor; the prompt is 「俵から出る」.
- **Aisles:** port (Y −14…−10), centre (Y −2…2) and starboard (Y 10…14).
  - Between them, 8 m-wide stack bays (Y −10…−2 and 2…10) of goods stacked 4 m high.
  - Dark 1.5 m crawl gaps cross the stacks every 12 m (X 12, 24 … 108).
  - Along the hull walls, rice bales are stacked to 6 m (Y ±14…±18).
- **Three routes, three risks:**
  - **Aisle floor:** fast, patrolled, lit.
  - **Crawl gaps:** slow, dark; spilled rice in two gaps is loud: `vol_spilled_rice_01` (X 30…36, Y −2…2) and `vol_spilled_rice_02` (X 86…92, Y −14…−10).
  - **Overhead gantry:** Y −1…1 at Z 10, X 20…110, ladders at X 25 and X 95. Quick, but the grating is loud (×1.5) and it sits inside the drones' cones.
- **Conveyor:** starboard, X 0…100 (`vol_conveyor_stbd`), moving goods forward at 0.8 m/s. It halves footstep noise within 3 m.
- **Landmark, the village bell:** a 1.2 m temple bell hangs from a gantry hook over the centre aisle at (60, 0, 6), `bell_bonsho`.
  - One 礫 strike rings it: every unaware or suspicious guard within 25 m converges and inspects for 12 s.
  - It works once. `vol_hold_bell` (X 50…70, Y −6…6) triggers the lines.
- **Manifest desk:** at (45, −6). The auditor (`pt_manifest_desk_turn`) faces aft and turns 180° every 20 s. `vol_manifest_desk` is X 38…52, Y −12…0.
- **Appraisal bay:** at (70, 4), where `g_e2` pauses 8 s to tag goods. The overheard line plays in `vol_hold_appraisal` (X 64…76, Y −2…10).
- **Lamps:** three inspection lamps on stands, `lamp_hold_01` (30, 6), `lamp_hold_02` (60, −8) and `lamp_hold_03` (90, 6), can be put out. The ceiling strips cannot.
- **Patrols:**
  - `pt_hold_port_loop`: X 10↔110 along Y −12, 120 cm/s, 4 s pause at each end.
  - `pt_hold_centre_loop`: X 30↔100 along Y 0, past the bell, 8 s pause at the appraisal bay.
  - `pt_hold_stbd_desk_loop`: X 20→60 along Y 12, across to the desk, then back.
  - `pt_gantry_sweep_a` / `_b`: drones at Z 9, X 20↔110, 150 cm/s, half a period apart, cones pointing down.
  - `pt_cart_x40` / `pt_cart_x84`: collared loaders pushing hand-carts through the cross-gaps at X 40 and X 84, Y −14↔14, 90 cm/s.
- **Side door:** the seized vault (b05) opens off the port wall at (72, −18), `vol_vault_door`.
- **Exit:** the forward hatch `vol_hold_fwd_hatch` (X 114…120, Y −3…3). Alarm reinforcements enter from `sp_hold_fwd_hatch` (116, 0, 0) and `sp_hold_gantry_fwd` (108, 0, 10).
- **Hull booms:** every 12 s the storm flexes the hull. There is an 800 ms rising creak, then a 2 s boom during which all player noise is ×0.3.

#### `pl_seized_vault`: seized-goods vault (b05, optional)

- **Size:** 24 × 16 × 6 m (X 64…88, Y −34…−18); `vol_seized_vault`. The door (72, −18) opens with the key-slate (2 s).
- **Discovery:** warm light leaks under the door from a seized andon the loaders lit to work by, at (70, −22). It is the only warm light in the ship.
- **Contents:** "high-value collateral": family swords on 刀掛け racks, a 屏風 in alien film, tea caddies in 仕覆 bags, 具足櫃 armor chests, lacquered 長持 with the Nyaagyu mon in gold maki-e under glowing alien tags.
- **POIs:**
  - `poi_nafudakake`: the dojo name board on the far wall (76, −33, 1.5). Interact to peel off its tags; Kohagi chalks the mon on it for the return lift.
  - `poi_armor_chest` (84, −30): scroll fragment VII.
  - `poi_notice_rack` (66, −28): seizure notice.
  - `poi_andon`: the lamp itself, a vista.

#### `pl_reckoning_engine`: reckoning engine (b06, b07)

- **Size:** a circular chamber 40 m across and 22 m high (`vol_engine_chamber`); origin at the centre. Entry through the west door, `ps_ch07_b06_start` (−18, 0, 0).
- **The ring (landmark):** a horizontal halo of glass abaci, 28 m across, turning once every 90 s at Z 12–15. Beads of light slide along its rods.
- **Drum pit:** below the ring, 10 m across, fenced by a 1.2 m rail with a steam vent. It holds the drum that winds the lift cable; a view port shows the cradle and the storm below.
- **Floor ring:** eight bead hoppers (2.5 m, full cover) at 10 m from centre, every 45°, plus six waist-high consoles at 16 m.
- **Mezzanine:** a ring at Z 6 (16–20 m from centre) with ramps at 45°, 135°, 225° and 315°. It gives height over the floor.
- **Override wheel:** a 2.4 m wheel on a 3 m dais on the east side at (0, 17, 3), reached by steps from (0, 13).
- **Spawns:**
  - `sp_engine_floor_n` (12, −6, 0) and `sp_engine_floor_s` (−10, −12, 0);
  - `sp_engine_mezz_e` (4, 18, 6), which pressures the wheel, and `sp_engine_mezz_w` (−4, −18, 6);
  - `sp_engine_door_n` (19, 0, 6) at the north door;
  - `sp_engine_ring_air` (0, 0, 16), where drones drop through the ring.
- **Exit:** the north door (20, 0, 6) leads down a corridor to the hangar.

#### `pl_hangar`: hangar (b08, b09, b15 launch)

- **Size and frame:** 80 × 45 × 20 m (`vol_hangar`); origin at the aft-starboard floor corner.
- **The mouth:** open to the storm on the port side (Y 45, X 20…60, 14 m high) behind a failing force curtain.
  - `vol_hangar_mouth_wind` (X 20…60, Y 33…45) pushes the player toward the mouth at 120 cm/s. A ledge guard stops the push at the lip.
  - Arrows and shells drift here as on the ridge.
- **Cover:** three shuttles (the landers of ch02) in cradles at X 15, 40 and 65 (Y 18…32), 18 m long each. They are large, walk-around cover.
- **Canisters:** three glowing fuel canisters, `fc_01` (28, 12), `fc_02` (52, 12) and `fc_03` (40, 38). Each bursts in a 360 cm radius for 80 damage, and hurts the player too.
- **Gallery:** an upper gallery along the starboard wall (Y 0…4, Z 8, X 5…75) with stairs at X 10 and X 70. The marksman is at `sp_hangar_gallery` (40, 2, 8) and the grenadier at `sp_hangar_gallery_fwd` (66, 2, 8).
- **Sled bay:** cargo sleds on launch rails at X 20…30, Y 30…44, aimed out of the mouth (`vol_sled_bay`). It is foreshadowed in b08 and used in b15.
- **Spawns:** `sp_hangar_fwd` (72, 22, 0), `sp_hangar_shuttle_2` (40, 25, 0) down shuttle 2's ramp, and `sp_hangar_mouth_air` (40, 52, 6) for drones from outside.
- **Entry and exit:**
  - Entry is `ps_ch07_b08_start` (4, 6, 0).
  - The exit is the dorsal hatch ladder at (78, 10); `vol_dorsal_hatch` (X 75…80, Y 7…13) closes b09.
  - Collectible `ch07.c06` is in shuttle 2's cockpit (40, 31, 2.5).

#### `pl_hull_ridge`: hull ridge (b10)

- **Shape:** the ship's dorsal spine, 180 m from the dorsal hatch (X 0) to the bridge's rear hatch (X 178). `vol_hull_ridge` is X 0…180, Y −12…12.
  - The walkable crown is 6 m wide, widening to 14 m at the "shoulder" (X 60…120).
  - Plates slope away at 20° for 4 m, then drop into the cloud sea.
  - The ridge falls 2 m along its length toward the bridge dome.
- **Wind:** steady 8 m/s from starboard, gusting to 18 m/s on a fixed schedule (11/9/14/10/12 s, repeating), with a 1 s warning and a 2.5 s hold. Gusts push toward the port side.
- **Cover:**
  - Engraved ribs cross the walkway every 12 m (1.2 m high: low cover and a lee when crouched).
  - Sensor fins at X 30, 70, 110 and 150 (3 m tall, 4 m long): full cover and full lee.
  - A 15 m sensor mast at X 90, where drones dock.
- **Cables:** cable runs along Y ±4, with brace anchors every 6 m. They are missing at three open gaps, all on the downwind (port) side: X 45…55, 95…105 and 135…145. A ledge guard still stops gust push at every lip, so only a deliberate step or jump off the edge is lethal.
- **Start and spawns:** `ps_ch07_b10_start` (2, 0, 0). Drones come from `sp_ridge_aft_air` (20, −25, 6), `sp_ridge_mast` (90, 0, 15) and `sp_ridge_fwd_air` (160, 20, 8).
- **Triggers:** `vol_ridge_mid` (X 80…100) and `vol_ridge_fwd` (X 140…160). The exit is `vol_bridge_rear_hatch` (X 176…180, Y −2…2).
- **Vista:** at X ≈ 60 the moon, the eyewall stadium and the cloud sea line up. Nyaakoto's first line is a soft look-at.

#### `pl_bridge_approach`: bridge approach (b11; **new place id**, a sub-area of the `pl_bridge` sublevel)

- **Shape:** a 60 m corridor, 12 m wide and 7 m high (X 0…60), widening at an atrium (X 25…40) to 24 m wide and 12 m high under hanging glass ledger slates. `vol_bridge_approach` is X 0…60, Y −12…12.
- **Start and pickup:** `ps_ch07_b11_start` (1, 0, 0) at the ladder foot. The security alcove is on the starboard side at (5, 6), with `security_rack` (key-slate, 2 s).
- **Doors:**
  - Blast door A (X 20) opens only after the rack is opened; `vol_appr_door_a` (X 16…22) starts wave 1.
  - Blast door B (X 45) opens with wave 2.
  - The bridge doors are at X 60; `vol_bridge_doors` starts b12.
- **Cover:** bulkhead half-walls (1.2 m) at X 10, 30, 40 and 52, plus console pedestals in the atrium.
- **Spawns:** `sp_appr_door_a` (24, 0, 0), `sp_appr_atrium` (35, ±8, 0), `sp_appr_door_b` (50, 0, 0), `sp_appr_bridge_doors` (58, 0, 0).
- **Sightlines:** the corridor is long and narrow (≤ 22 m effective between half-walls), which suits the Shock Emitter's 2,200 cm range.

#### `pl_bridge`: bridge amphitheatre (b12, b13, b14)

- **Frame:** origin at the window's centre on the lowest floor; +X aft toward the doors.
- **Window:** 30 × 12 m of black glass on the X 0 plane (unbreakable), showing the eye, then the eyewall.
- **Tiers:** the amphitheatre steps up aft; its width grows from a 30 m chord at the window to 36 m at the landing.

  | Tier | X (m) | Z (m) | Contents |
  |---|---|---|---|
  | Tier 0, helm floor | 0…6 | 0 | Helm and beacon |
  | T1 | 6…10 | 1.2 | 5 consoles |
  | T2 | 10…14 | 2.4 | 5 consoles |
  | T3 | 14…18 | 3.6 | 5 consoles |
  | Landing | 18…24 | 4.8 | Doors |

- **Consoles:** 15 in all (1.1 m high, 3 m long), all destructible (2 margin-call strikes each). After 6 are destroyed the rest become reinforced, so cover never runs out.
- **Fixtures:**
  - The admiral's ledger pulpit at (2, 0, 0).
  - `helm_trim_wheel` at (3, −5, 0) and the beacon console at (3, 6, 0).
  - A ring of 8 ceiling emitters at Z 14, the margin-call strikers.
  - 6 console chairs and 4 cargo pods loose on the tiers; they slide to port in phase 2.
- **Volumes:** `vol_bridge_arena` (X 0…24, Y −18…18, Z 0…16) is locked during the boss. `vol_helm` (X 0…6, Y −8…8) is the b14 hold zone.
- **Start and spawns:**
  - `ps_ch07_b13_start` (21, 0, 4.8) is on the landing; Collatera starts at the pulpit.
  - `sp_bridge_rear_doors` (23, 0, 4.8), `sp_bridge_port_hatch` (12, −17, 2.4), `sp_bridge_stbd_hatch` (12, 17, 2.4), `sp_bridge_dome` (10, 0, 12).
- **Sightlines:** Collatera fires up the tiers. The consoles break her lines but not the ceiling strikes, which is the point of phase 2. The phase 3 duel is drawn down to tier 0 and T1.

#### `pl_kayanohara`: Kaya Moor (b15 end, b16; **new place id**)

- **Terrain:** about 1.2 × 0.8 km of rolling 芒 (susuki) hills, 3 km north of Nekoyama. The flagship ploughs a 600 m furrow and comes to rest against a low hill.
- **Playable area:** 80 × 50 m around the sled's stopping point (`ps_ch07_b16_start` (0, 0, 0)).
  - The wreck's hangar mouth is 60 m behind.
  - Riders approach at a walk from +X and stop at (25, 0); `vol_riders` has a 10 m radius.
  - The Citadel shows 3 km to the south-west on the horizon in lightning; the camera looks there for the broadcast.
  - Soft bounds: tall grass, slope and wreck debris; no invisible-wall text.

---

## 2. Beat list

### 2.1 Summary

| Beat | Type | Objective (JA / EN) | Place | Min | Start (mm:ss) | Checkpoint | Site | Unlocks |
|---|---|---|---|---|---|---|---|---|
| ch07.b01 | cinematic | 軍議 / The war council | `pl_kakuredani` | 2.0 | 00:00 | yes | — | weapon 9; auto-grant 13 if missing |
| ch07.b02 | combat_wave | 錨台の通信塔を断て / Cut the anchor bastion's relay | `pl_anchor_bastion` | 4.0 | 02:00 | yes | 0 | — |
| ch07.b03 | cinematic | 俵に潜め / Hide in the rice bales | `pl_anchor_bastion` | 1.5 | 06:00 | no | — | — |
| ch07.b04 | stealth_zone | 貨物倉を抜けよ / Cross the cargo hold unseen | `pl_cargo_hold` | 4.0 | 07:30 | yes | — | — |
| ch07.b05 | explore_optional (optional) | 押収品倉を調べる / Search the seized-goods vault | `pl_seized_vault` | 2.0 | 11:30 | yes | — | — |
| ch07.b06 | combat_wave | 算術機関室を制圧せよ / Take the reckoning engine | `pl_reckoning_engine` | 4.0 | 13:30 | yes | — | weapon 11; `shield_break` |
| ch07.b07 | production_task (crank) | 昇降機を逆転させよ / Reverse the extraction lift | `pl_reckoning_engine` | 4.0 | 17:30 | yes | 1 | — |
| ch07.b08 | combat_wave | 格納庫を突破せよ / Break through the hangar | `pl_hangar` | 4.0 | 21:30 | yes | — | weapon 14 |
| ch07.b09 | dialogue (radio) | 地上からの報せ / Word from the ground | `pl_hangar` | 1.0 | 25:30 | no | — | — |
| ch07.b10 | combat_wave | 外殻の稜線を渡れ / Cross the hull ridge | `pl_hull_ridge` | 4.0 | 26:30 | yes | — | — |
| ch07.b11 | combat_wave | 艦橋へ迫れ / Push to the bridge | `pl_bridge_approach` | 4.0 | 30:30 | yes | — | weapon 16 |
| ch07.b12 | cinematic | 提督コラテラ / Admiral Collatera | `pl_bridge` | 1.5 | 34:30 | no | — | — |
| ch07.b13 | boss | 旗艦提督コラテラを倒せ / Defeat Admiral Collatera | `pl_bridge` | 8.0 | 36:00 | yes | — | — |
| ch07.b14 | production_task (hold) | 信号灯と舵を守れ / Hold the beacon and the helm | `pl_bridge` | 3.0 | 44:00 | yes | 2 | — |
| ch07.b15 | cinematic | 墜落 / The fall | `pl_hangar` | 2.0 | 47:00 | no | — | — |
| ch07.b16 | dialogue (ambient) | 萱野原 / Kaya Moor | `pl_kayanohara` | 1.0 | 49:00 | yes | — | — |
| **Σ** | | | | **50** | | | | |

### 2.2 Checkpoint spacing

The rule is at most 360 target-seconds between checkpoints (bible §12.3 rule 8). Checkpoints fall at beat starts and at the boss's phase starts; the table is the worst case, with the optional b05 played. b03, b09, b12 and b15 are non-interactive or walk-and-talk and do not checkpoint. b16 checkpoints so that a reload after the crash never replays b14.

| From | To | Gap (s) |
|---|---|---|
| ch07.b01 | ch07.b02 | 120 |
| ch07.b02 | ch07.b04 | 330 |
| ch07.b04 | ch07.b05 | 240 |
| ch07.b05 | ch07.b06 | 120 |
| ch07.b06 | ch07.b07 | 240 |
| ch07.b07 | ch07.b08 | 240 |
| ch07.b08 | ch07.b10 | 300 |
| ch07.b10 | ch07.b11 | 240 |
| ch07.b11 | ch07.b13 | 330 |
| ch07.b13 | ch07.b13 P2 | 192 |
| ch07.b13 P2 | ch07.b13 P3 | 168 |
| ch07.b13 P3 | ch07.b14 | 120 |
| ch07.b14 | ch07.b16 | 300 |
| ch07.b16 | chapter end | 60 |

### 2.3 Chapter systems

These are proposals for L2 (enemy and weapon rules) and L4 (HUD). They introduce what bible §10 lists for ch07: "Energy shields and charged shots; wind drift on arrows; override crank."

**Energy shields (障壁, `shield_break`, from b06).**

| Profile | Applies to | Shield | Regeneration | On break | Damage multipliers vs shield | Pierce |
|---|---|---|---|---|---|---|
| `shielded` | `enforcer_rifle` variant | 60 | after 4.0 s unhit, 30/s | 0.8 s stagger | default ×1.0 · melee ×1.25 · Pulse Carbine (11) ×1.5 · Shock Emitter (16) ×2.5 | charged Plasma Matchlock (14) |
| `tower_field` | `shield_enforcer` | frontal 120° field on the tower shield; blocks hitscan, arrows and melee | — | — | Shock Emitter: field down 4 s and guard lowered; charged 14: field down 4 s | — |
| Collatera | boss | 240 | after 4.0 s unhit, 80/s | "Undercapitalized" bark | as `shielded`; charged 14 removes 50% of max | offline for 1.6 s during every reload |

- **Readability:** shields render as a pale silver-violet thin-film shimmer with a hit ripple, never cyan. Cyan stays reserved for locked-aim telegraphs (bible §8). The break shatters into falling ledger-numeral fragments with a distinct glass-crack sound.
- **HUD:** a thin shield bar sits above the enemy health bar (L4).

**Charged shot (`charged_shot`, proposed flag, from b08).**

- **How it works:** hold fire to charge the Plasma Matchlock (14) for 800 ms. Movement is ×0.6 while charging, and the charge holds up to 3 s. On release it fires the catalog shot (95 damage) that also **pierces shields**. An uncharged shot does normal damage but shields absorb it.
- **Feedback:** audio is a rising coil whine and a click at full charge; the barrel glow brightens. Catalog stats stay unchanged; the charge adds the plan's "shield penetration versus charge time" trade-off.

**Wind (b08 hangar mouth, b10 ridge; proposed flag `wind_brace`).**

- **Wind model:**
  - Steady 8 m/s from starboard; gusts to 18 m/s on a fixed, non-random schedule (11/9/14/10/12 s).
  - Warning 1 s: a rising roar, the tenugui strip snapping out, spindrift. The gust holds 2.5 s.
- **Push:** 120 cm/s standing, 60 crouched, 0 when braced on a cable or in the lee of a rib or fin. A ledge guard stops gust push at every edge. Falling (by deliberate movement) respawns at the last brace anchor for 25 HP, up to 3 times per checkpoint.
- **Arrow and shell drift:** lateral acceleration is 0.35 m/s² per m/s of wind. It applies to arrows (18), grenade shells (7) and enemy shells, but never to hitscan.
  - At the arrow's 65 m/s this is about 0.3 m of drift at 30 m in steady wind, and about 0.7 m in a gust. That is readable, and fixed by aiming half a body upwind.
- **Indicator:** Kohagi ties an indigo tenugui strip to the bow's upper limb (末弭); the diegetic indicator is always on. L4 can add an optional HUD wind arrow for accessibility.
- **Drones:** they drift in gusts, and their aim is disrupted for 0.6 s.

**Override crank (b07).**

- **Reverse torque:** the wheel is geared against the engine, so released progress decays at 0.04 per second.
- **Ratchet:** Kohagi sets a pawl at 25%, 50% and 75%, and progress never falls below the last pawl.
- **Rate:** turning faster than the 0.9 turns/s band slips the gear (a loud clank, no progress). The accessibility option is hold-to-crank at 0.6 turns/s.
- **Two-handed:** the player sheathes the katana (納刀) and cannot fight while cranking.
- **Kohagi as co-op NPC:** when the player leaves the wheel she cranks at 0.15 turns/s and decay is suspended. She leaves the wheel for cover if an enemy comes within 5 m, so defending her keeps the progress moving.

**Stealth aids (b04).**

- **Hull booms:** every 12 s, after an 800 ms warning creak, 2 s of ×0.3 player noise.
- **The bell:** a one-shot lure, 25 m radius, 12 s inspection.
- **Surfaces:** spilled rice (`gravel`) and the conveyor (`running_water`, ×0.5).
- **Metal grating:** the gantry, proposed surface `x_metal_grate`, ×1.5.
- **Bodies:** a body in a lit aisle adds 0.5 suspicion to a guard who sees it; in the dark it goes unnoticed.

**Helm trim (b14).**

- **Trim events:** at 25%, 50% and 75% of the hold the heading drifts. There is an alarm bark, and a 2 s interact at `helm_trim_wheel` corrects it within an 8 s grace. Ignored, the hold decays at 0.02/s until it is fixed.
- **Fail timer:** 150 s on Normal (200 Easy, 130 Hard). In fiction, the ship's glide reaches the ridge villages.

### 2.4 Beat details

#### ch07.b01: cinematic · 軍議 / The war council · 2.0 min

The first council after ch06 with Toranosuke in it. Oyuki numbers the goods, Iota numbers the schedule, Kohagi says who goes in the bales, and Toranosuke offers his riders and a debt he means to repay alive. Nyaakoto tells him it is no debt, the chapter's thematic hinge (bible §1.3, theme 3). Tetsugorō hands over the Repeater (weapon 9), built at the Silk Foundry's refining forge with the SORA mon on its receiver. If weapon 13 was missed in ch06.b07, it is added to the mask here (bible §11) and becomes selectable at the b02 supply point. The shot list ends on the torn 陣幕 and the tether.

**Parameters**

- Sequence `/Game/Cinematics/Ch07/LS_Ch07_B01_WarCouncil`, 120 s, skippable; fallback `camera_blend` (letterboxed in-engine camera until C9).
- End state: player at `ps_ch07_b02_start`, equipped {"firearm": 9}.
- Proposed extensions: `x_auto_grant_if_missing` [13].
- Fail: none (cinematic). Music state `mus_ch07_council`.

**Dialogue triggers**

- cinematic subtitles: lines 001–014

#### ch07.b02: combat_wave · 錨台の通信塔を断て / Cut the anchor bastion's relay · 4.0 min · site 0

A storm assault with allies.

- **Staging:** the staging area is safe: supply point, Okuzu, Tamakichi.
- **Routes:** crossing the fascine causeway and reaching the 雁木 starts wave 1. The player can:
  - push up the steps under the League's loophole fire;
  - flank up the rubble ramp with Otane;
  - climb through the 多聞櫓 to take the turret marksman up close.
- **Objective:** junction cuts are 2 s interacts that can be interrupted without losing progress. Each cut advances the objective, and waves 2 and 3 key off it: at the first cut enemies drop from the lift cradle, at the second they flank from the north sally port.
- **Allies:** the League 鉄砲 use coil matchlocks (weapon 5, bible §4.4), the reason they can fire in this rain. Their coil breeches spark jade-green, and their muzzle flashes are the only warm light in the yard.
- **Completion:** when all waves are cleared and the relay is cut, the relay's cold lights die, the pylon's scan beams stop sweeping the cargo cradle, and site 0 is restored. The catalog's `restored` text is shown.

**Parameters**

- Bounds `vol_bastion_bounds`; `max_alive` 6; complete: `all_waves_cleared`.
- Waves:
  - **W1** on `volume_enter:vol_bastion_steps`: `enforcer_rifle` ×4 @ `sp_bastion_gate`, patrol `pt_gangi_top`; `marksman` ×1 @ `sp_tamon_upper`
  - **W2** on `progress_at:0.34`: `enforcer_rifle` ×3 @ `sp_lift_platform`; `marksman` ×1 @ `sp_pylon_gantry`
  - **W3** on `progress_at:0.67`: `enforcer_rifle` ×3 @ `sp_bastion_north`
- Allies (downable, revive 4 s): `otane` (flank_melee), `teppo_1` (suppress_ranged), `teppo_2` (suppress_ranged), `teppo_3` (suppress_ranged), `teppo_4` (suppress_ranged).
- Proposed extensions: `x_objective` {kind: interact_points, points: [relay_j1, relay_j2, relay_j3], per_point_s: 2.0, interruptible: true, progress_persists: true, complete_requires: [all_points, all_waves_cleared]}; `x_staging` {volume: vol_bastion_staging, supply_point: sup_ch07_bastion, safe: true}; `x_environment` {weather: typhoon_front, visibility_m: 45, wind: {visual_only: true, reason: "bailey is in the lee of the ishigaki and tamon yagura"}, lightning_schedule_s: [17, 23, 15, 21], flash_reduction: respect_setting}.
- Fail: `player_died` → `checkpoint`. Music state `mus_ch07_bastion_storm`.

**Dialogue triggers**

- `volume_enter:vol_bastion_staging` (ambient): lines 001–003
- `volume_enter:vol_bastion_steps` (ambient): lines 004–005
- `volume_enter:vol_relay_foot` (ambient): line 006
- `progress_at:0.34` (ambient): lines 007–008
- `progress_at:0.67` (ambient): line 009
- `site_restored:0` (ambient): line 010
- `beat_complete` (radio): line 011
- `alert_state:alert` (ambient): line 012 (repeatable)
- `wave_spawned` (ambient): line 013 (repeatable)
- `enemy_retreat` (ambient): line 014 (repeatable)
- `pattern:marksman_lock` (ambient): line 015 (repeatable)
- `npc_downed:teppo_*` (ambient): line 016 (repeatable)

#### ch07.b03: cinematic · 俵に潜め / Hide in the rice bales · 1.5 min

- **The bales:** the League's hollow 大俵 (straw over a bamboo frame, about 1.2 m long) are rolled onto the cradle among real bales by collared loaders.
- **Two quiet moments:**
  - One loader sees the chalk mon on the straw, pats the bale once and whispers.
  - An enforcer, his scanner dead, logs the bales by hand, notes the extra weight and rounds it away: the Credit House's own arithmetic lets the League aboard.
- **The ascent:** the cradle rises along the tether through rain and cloud into the eye. Rice dust, a twitching whisker, and Kohagi's 「くしゃみ、するな。」 (approved humor #6). Nyaakoto says nothing; the silence is the joke.
- **End:** the ship voice announces the cargo on arrival.

**Parameters**

- Sequence `/Game/Cinematics/Ch07/LS_Ch07_B03_Stowaways`, 90 s, skippable; fallback `camera_blend` (letterboxed in-engine camera until C9).
- End state: player at `ps_ch07_b04_start`, equipped "keep".
- Fail: none (cinematic). Music state `mus_ch07_ascent`.

**Dialogue triggers**

- cinematic subtitles: lines 001–007

#### ch07.b04: stealth_zone · 貨物倉を抜けよ / Cross the cargo hold unseen · 4.0 min

The goods are warm and hand-made under cold light, and every object wears a glowing tag. The level teaches its toolkit through Kohagi in the first 20 s: counts and directions, then the hull-boom rule. The bell and the loaders are optional tools.

- **Loaders:** seal-cutting a collared loader from behind (峰打ち is not needed; they are not fighting) frees them. The first one tells the player there is one guard at the forward door; both then hide among the bales. Freed loaders never count toward any kill quota.
- **Takedowns:** rear takedowns on aliens are lethal by default. Loaders are always non-lethal.
- **If seen:** the ship voice calls security. 3 enforcers and a drone enter from the forward hatch, and stealth can resume once the 20 s search ends out of sight.
- **The auditor:** weak in combat, but his alarm skips the suspicious stage.

**Parameters**

- Zone `vol_cargo_hold`; complete: `exit_reached` at `vol_hold_fwd_hatch`; on detected: `reinforce:hold_alarm` (Easy: `combat`).
- Detection: suspicion rate 1.0/s at full light and ≤5 m, alert threshold 1.0, search 20 s.
- Guards:
  - `g_e1` `enforcer_rifle` on `pt_hold_port_loop`: cone 90°, 1800 cm lit / 700 cm dark, hearing 900 cm
  - `g_e2` `enforcer_rifle` on `pt_hold_centre_loop`: cone 90°, 1800 cm lit / 700 cm dark, hearing 900 cm
  - `g_e3` `enforcer_rifle` on `pt_hold_stbd_desk_loop`: cone 90°, 1800 cm lit / 700 cm dark, hearing 900 cm
  - `g_d1` `drone` on `pt_gantry_sweep_a`: cone 60°, 1400 cm lit / 900 cm dark, hearing 0 cm
  - `g_d2` `drone` on `pt_gantry_sweep_b`: cone 60°, 1400 cm lit / 900 cm dark, hearing 0 cm
  - `g_a1` `auditor` on `pt_manifest_desk_turn`: cone 70°, 1200 cm lit / 500 cm dark, hearing 1200 cm
  - `g_c1` `bound_conscript` on `pt_cart_x40`: cone 80°, 1000 cm lit / 400 cm dark, hearing 600 cm
  - `g_c2` `bound_conscript` on `pt_cart_x84`: cone 80°, 1000 cm lit / 400 cm dark, hearing 600 cm
- Reinforcement wave:
  - **hold_alarm** on `alert_state:alert`: `enforcer_rifle` ×3 @ `sp_hold_fwd_hatch`; `drone` ×1 @ `sp_hold_gantry_fwd`
- Takedowns: rear, lethal by default on aliens; `bound_conscript` always non-lethal (seal-cut).
- Lights (extinguishable): `lamp_hold_01`, `lamp_hold_02`, `lamp_hold_03`. Noise: `gravel` in `vol_spilled_rice_01`, `vol_spilled_rice_02`; `running_water` in `vol_conveyor_stbd` ×0.5; `x_metal_grate` in `vol_gantry` ×1.5.
- Proposed extensions: `x_lure_objects` [{id: bell_bonsho, radius_cm: 2500, uses: 1, draws: [unaware, suspicious], hold_s: 12}]; `x_ambient_noise_mask` {source: hull_boom, schedule_s: [12, 12, 12], duration_s: 2.0, warn_ms: 800, noise_mult: 0.3}; `x_body_discovery` {lit_aisle_suspicion: 0.5, dark_suspicion: 0.0}.
- Fail: `player_died` → `checkpoint`. Music state `mus_ch07_hold_stealth`.

**Dialogue triggers**

- `beat_start` (ambient): lines 001–002
- `volume_enter:vol_hold_bell` (ambient): lines 003–004
- `volume_enter:vol_hold_appraisal` (ambient): line 005
- `volume_enter:vol_manifest_desk` (ambient): line 006
- `seal_cut:g_c1` (ambient): line 007
- `seal_cut:g_c2` (ambient): line 008
- `alert_state:suspicious` (ambient): line 009 (repeatable)
- `alert_state:search` (ambient): line 010 (repeatable)
- `alert_state:alert` (ambient): line 011 (repeatable)
- `alert_state:unaware` (ambient): line 012 (repeatable)
- `auditor_alarm` (ambient): line 013 (repeatable)
- `lure_triggered:bell_bonsho` (ambient): line 014
- `wave_spawned:hold_alarm` (ambient): line 015

#### ch07.b05: explore_optional · 押収品倉を調べる / Search the seized-goods vault · 2.0 min (optional)

- **Access:** a side vault off the hold. There are no markers; the andon's warm light under the door and Kohagi's line are the cues.
- **The name board:** peeling the account tags off the name board plays the three-line exchange ending 「名は、番号ではない。」 Kohagi chalks the mon on it, and it rides down on the b07 cradle. This sets `nafudakake_marked`, which ch08 can read for the rehanging at the Eastern Torii.
- **Rewards:** three collectibles (heirloom, seizure notice, scroll fragment VII) and 12 arrows.
- **Exit hint:** after 90 s of idling, Kohagi nudges the player on.

**Parameters**

- Volume `vol_seized_vault`; POIs: `poi_nafudakake` (lore), `poi_armor_chest` (cache), `poi_notice_rack` (lore), `poi_andon` (vista).
- Rewards: `ch07.c01`, `ch07.c02`, `ch07.c03`, `arrows_12`; exit hint after 90 s; no map markers.
- Proposed extensions: `x_entry` {door: door_seized_vault, lock: key_slate, interact_s: 2.0}; `x_story_flag` {set: nafudakake_marked, effect: "name board rides down on the b07 cradle; ch08 reads the flag"}.
- Fail: `player_died` → `checkpoint`. Music state `mus_ch07_vault_quiet`.

**Dialogue triggers**

- `volume_enter:vol_vault_door` (ambient): line 001
- `poi_found:poi_nafudakake` (ambient): lines 002–004
- `idle_s:90` (ambient): line 005

#### ch07.b06: combat_wave · 算術機関室を制圧せよ / Take the reckoning engine · 4.0 min

The shield tutorial by play.

- **Wave 1:** only shielded enforcers, so the regeneration rule is felt before it is explained. Iota's line fires on the first shield hit, and Kohagi's "keep firing" follows.
- **The Pulse Carbine:** the first shielded enforcer to fall always drops it (3 magazines). Picking it up unlocks weapon 11 and plays Iota's ×1.5 line.
- **Waves 2 and 3:** blades from the floor, rifles on the mezzanine, then a grenadier at the north door. Players use the hoppers and the mezzanine ramps.
- **Collectible:** `ch07.c05` sits on an auditor's desk on the west mezzanine (−12, −14, 6).

**Parameters**

- Bounds `vol_engine_chamber`; `max_alive` 6; complete: `all_waves_cleared`.
- Waves:
  - **W1** on `start`: `enforcer_rifle` ×3 (shielded) @ `sp_engine_floor_n`
  - **W2** on `alive_below:2`: `enforcer_rifle` ×2 (shielded) @ `sp_engine_mezz_e`; `blade_retainer` ×2 @ `sp_engine_floor_s`
  - **W3** on `alive_below:2`: `enforcer_rifle` ×2 (shielded) @ `sp_engine_mezz_w`; `grenadier` ×1 @ `sp_engine_door_n`
- Proposed extensions: `x_guaranteed_drop` {weapon: 11, from: first_defeated_shielded_enforcer, ammo_mags: 3}.
- Fail: `player_died` → `checkpoint`. Music state `mus_ch07_engine`.

**Dialogue triggers**

- `beat_start` (ambient): line 001
- `beat_start` (radio): line 002
- `shield_hit_first` (radio): line 003
- `shield_hit_first` (ambient): line 004
- `pickup:11` (radio): line 005
- `shield_broken` (ambient): line 006 (repeatable)
- `pattern:grenadier_throw` (ambient): line 007 (repeatable)
- `pattern:retainer_close` (ambient): line 008 (repeatable)

#### ch07.b07: production_task (crank) · 昇降機を逆転させよ / Reverse the extraction lift · 4.0 min · site 1

The chapter's production beat. It is about **giving back**, not making.

- **The task:** 16 turns of the override wheel against the engine, while waves arrive at 25%, 50% and 75% of progress.
- **The choice:** keep cranking behind Kohagi's pawls, or step off to fight while she turns slowly. Players learn the pawls make stepping off safe.
- **The view:** through the drum pit's port the cradle is seen descending into the storm with the goods, and with the name board if b05 was done.
- **Registry:** on completion the chapter's registry entry is written: 押収品の返還 430駄 (Seized goods returned, 430 horse-loads).
  - Oyuki records it **as a return**. Nothing was made, so no XOR tally is cut (charter article 1, bible §2.2).
  - The registry screen shows the entry with 「返還のみ記帳・札は切らず」 and no split-tally icon.
  - L1 needs a `record_only` registry mode (§6).

**Parameters**

- Crank `override_wheel_01`: 16 turns, rate band [0.3, 0.9] turns/s, decay 0.04/s when nobody is on the wheel, 8 stamina/turn, interruptible, co-op NPC `kohagi`.
- Waves:
  - **W1** on `progress_at:0.25`: `drone` ×2 @ `sp_engine_ring_air`
  - **W2** on `progress_at:0.5`: `enforcer_rifle` ×2 (shielded) @ `sp_engine_mezz_w`
  - **W3** on `progress_at:0.75`: `blade_retainer` ×2 @ `sp_engine_floor_s`; `enforcer_rifle` ×1 @ `sp_engine_door_n`
- Registry on completion: 押収品の返還 430駄 / Seized goods returned, 430 horse-loads (mode `record_only`).
- Proposed extensions: `x_override` {reverse_torque: true, ratchet_locks: [0.25, 0.5, 0.75], two_handed: true, loadout_while_cranking: none, overspeed: gear_slip_no_progress, coop_npc_rate_turns_s: 0.15, coop_npc_suspends_decay: true, coop_npc_leaves_if_enemy_within_cm: 500, accessibility_hold_to_crank_turns_s: 0.6}; `x_registry_mode` record_only.
- Fail: `player_died` → `checkpoint`. Music state `mus_ch07_engine_crank`.

**Dialogue triggers**

- `beat_start` (radio): lines 001–002
- `progress_at:0.25` (ambient): line 003
- `progress_at:0.5` (ambient): line 004
- `progress_at:0.75` (ambient): line 005
- `crank_released` (ambient): line 006 (repeatable)
- `beat_complete` (radio): line 007
- `site_restored:1` (radio): lines 008–009

#### ch07.b08: combat_wave · 格納庫を突破せよ / Break through the hangar · 4.0 min

- **The marksman:** a glint marksman on the gallery. His 900 ms lock glint is paired with the captioned bark 「照準、査定完了。」
- **The Plasma Matchlock:** killing him drops weapon 14 (6 rounds), and Iota explains the charge.
- **Wave 2:** two tower shields. Players flank round the shuttles, or pop a canister behind them.
- **Wave 3:** a grenadier on the gallery and drones through the mouth.
- **The mouth:** its wind zone is a hazard and a lesson for b10: shells drift there.
- **Foreshadowing:** Kohagi points out the sleds. Collectible `ch07.c06` is in shuttle 2's cockpit.

**Parameters**

- Bounds `vol_hangar`; `max_alive` 6; complete: `all_waves_cleared`.
- Waves:
  - **W1** on `start`: `enforcer_rifle` ×2 (shielded) @ `sp_hangar_fwd`; `enforcer_rifle` ×1 @ `sp_hangar_fwd`; `marksman` ×1 @ `sp_hangar_gallery`
  - **W2** on `alive_below:2`: `shield_enforcer` ×2 @ `sp_hangar_shuttle_2`; `enforcer_rifle` ×2 @ `sp_hangar_fwd`
  - **W3** on `alive_below:2`: `grenadier` ×1 @ `sp_hangar_gallery_fwd`; `drone` ×2 @ `sp_hangar_mouth_air`
- Proposed extensions: `x_guaranteed_drop` {weapon: 14, from: marksman, ammo_rounds: 6}; `x_hazards` [{kind: explosive_canister, ids: [fc_01, fc_02, fc_03], blast_radius_cm: 360, damage: 80, hurts_player: true}]; `x_environment` {wind_volume: vol_hangar_mouth_wind, push_cm_s: 120, toward: mouth, ledge_guard: true, projectile_drift: true}; `x_mechanics_proposed` [charged_shot].
- Fail: `player_died` → `checkpoint`. Music state `mus_ch07_hangar`.

**Dialogue triggers**

- `beat_start` (ambient): line 001
- `alert_state:alert` (ambient): line 002
- `volume_enter:vol_hangar_canisters` (ambient): line 003
- `pickup:14` (radio): lines 004–005
- `wave_spawned:2` (ambient): line 006
- `volume_enter:vol_sled_bay` (ambient): line 007

#### ch07.b09: dialogue (radio) · 地上からの報せ / Word from the ground · 1.0 min

- **Walk-and-talk:** player control stays. Kohagi resupplies (2 Repeater magazines, 12 arrows) while Iota reports over the slate. He gives Toranosuke's rider count, corrects it by one (proposed light moment H2), says the spine corridor is sealed, and warns of gusts at the edge of the calm.
- **Completion:** when the lines end **and** the player enters `vol_dorsal_hatch`.

**Parameters**

- Mode `radio`, trigger `beat_start`, interrupt `queue`, camera `none`.
- Proposed extensions: `x_complete_also` "volume_enter:vol_dorsal_hatch".
- Fail: `player_died` → `checkpoint`. Music state `mus_ch07_radio`.

**Dialogue triggers**

- `beat_start` (radio): lines 001–006

#### ch07.b10: combat_wave · 外殻の稜線を渡れ / Cross the hull ridge · 4.0 min

The set piece above the clouds: the moon, the stadium of the eye, lightning in the cloud sea.

- **Wind tutorial:** in the first 30 s Kohagi ties the tenugui strip to the bow and Nyaakoto reads it. The first gust warning teaches the cable brace.
- **Drones:** eight in three groups. Arrows are the best tool against them: one arrow downs a drone, while hitscan needs several hits on a jinking target. But arrows drift, so the chapter's wind rule finally matters.
- **The lee:** ribs and fins are lee shelters where the player can shoot freely.
- **Nets:** a drone's seizure net roots the player for 1.2 s. It never pushes, and the ledge guard holds.

**Parameters**

- Bounds `vol_hull_ridge`; `max_alive` 4; complete: `all_waves_cleared`.
- Waves:
  - **W1** on `start`: `drone` ×2 @ `sp_ridge_aft_air`
  - **W2** on `volume_enter:vol_ridge_mid`: `drone` ×3 @ `sp_ridge_mast`
  - **W3** on `volume_enter:vol_ridge_fwd`: `drone` ×3 @ `sp_ridge_fwd_air`
- Proposed extensions: `x_environment` {wind: ridge_wind}; `x_fall_respawn` {to: last_brace_anchor, hp_cost: 25, max_per_checkpoint: 3, then: checkpoint}; `x_mechanics_proposed` [wind_brace].
- Fail: `player_died` → `checkpoint`. Music state `mus_ch07_ridge`.

**Dialogue triggers**

- `beat_start` (ambient): lines 001–003
- `gust_warning:first` (ambient): line 004
- `gust_warning` (ambient): line 005 (repeatable)
- `volume_enter:vol_ridge_mid` (ambient): line 006
- `volume_enter:vol_ridge_fwd` (ambient): line 007

#### ch07.b11: combat_wave · 艦橋へ迫れ / Push to the bridge · 4.0 min

- **The Shock Emitter:** the key-slate opens the security rack, and blast door A only opens after the pickup (weapon 16).
- **Tower shields:** three across the waves. The shock drops a tower field and lowers the guard for 4 s, and the corridor's short sightlines suit the weapon's range.
- **Ending:** the last wave falls back toward the bridge doors, and entering `vol_bridge_doors` starts b12.

**Parameters**

- Bounds `vol_bridge_approach`; `max_alive` 6; complete: `all_waves_cleared`.
- Waves:
  - **W1** on `volume_enter:vol_appr_door_a`: `shield_enforcer` ×1 @ `sp_appr_door_a`; `enforcer_rifle` ×2 (shielded) @ `sp_appr_atrium`
  - **W2** on `alive_below:2`: `shield_enforcer` ×2 @ `sp_appr_door_b`; `blade_retainer` ×1 @ `sp_appr_door_b`
  - **W3** on `alive_below:2`: `enforcer_rifle` ×2 (shielded) @ `sp_appr_bridge_doors`; `grenadier` ×1 @ `sp_appr_bridge_doors`
- Proposed extensions: `x_pickup` {id: security_rack, weapon: 16, interact_s: 2.0, lock: key_slate, gates: door_a_opens_after_pickup}.
- Fail: `player_died` → `checkpoint`. Music state `mus_ch07_approach`.

**Dialogue triggers**

- `beat_start` (radio): lines 001–002
- `pickup:16` (radio): line 003
- `pattern:shield_advance` (ambient): line 004 (repeatable)
- `wave_spawned:2` (ambient): line 005
- `wave_spawned:3` (ambient): line 006

#### ch07.b12: cinematic · 提督コラテラ / Admiral Collatera · 1.5 min

- **Staging:** Collatera stands at the ledger pulpit with her back to the eyewall. She is polite, precise and unhurried.
- **The offer:** she welcomes Nyaakoto by account number, observes that interest never goes down, and makes the catalog's survival-loan offer. This is the catalog's line 2, delivered in plain 「やろう」: her one deliberate drop into condescension (see §6).
- **The answer:** Nyaakoto answers with catalog line 3. 「与信、否決。」 Two pistols.

**Parameters**

- Sequence `/Game/Cinematics/Ch07/LS_Ch07_B12_SurvivalLoan`, 90 s, skippable; fallback `camera_blend` (letterboxed in-engine camera until C9).
- End state: player at `ps_ch07_b13_start`, equipped "keep".
- Fail: none (cinematic). Music state `mus_ch07_collatera_intro`.

**Dialogue triggers**

- cinematic subtitles: lines 001–005

#### ch07.b13: boss · 旗艦提督コラテラを倒せ / Defeat Admiral Collatera · 8.0 min

The **ranged gunslinger** of bible §8, in three phases that each ask a different question. There is no mutō-dori here: it is reserved for Toranosuke (ch06) and Val Amort (ch08).

- **P1 (100–60%), "manage the shield":**
  - Her 240-point shield regenerates after 4 s unhit.
  - Break it with a charged Plasma Matchlock (−50% of max per hit) or the Shock Emitter (×2.5).
  - Or wait for the reload: every third burst she swaps power cells for 1.6 s and her shield is offline. Any hit lands then, including an arrow. Kohagi calls this out the first time.
- **P2 (60–30%), "keep moving":**
  - 「担保価値の下落を確認。」 The bridge lists 10° to port: uphill movement ×0.85, downhill ×1.1.
  - Every 7 s she calls margin on up to three pieces of cover near the player. Each strike is announced by the bark 「追証を請求します。」 and a 1500 ms amber ring.
  - Loose chairs and pods slide downslope every 6 s after a 700 ms scrape.
  - Two drones mark the player for strikes. Staying in cover more than 6 s draws 「その遮蔽物も、担保です。」, and the next strike targets that cover.
- **P3 (30–0%), "the duel":**
  - Her shield cell burns out and she draws the 清算刀 (Liquidation Blade).
  - A two-cut combination (450 ms) and a long lunge (800 ms, amber floor line, bark 「清算。」) can both be met with 合わせ for a 1.2 s stagger. 転 around the lunge opens a 1.5 s flank.
  - An off-hand pistol snap shot (400 ms cyan dot) cannot be parried; sidestep it.
- **Defeat:** at 0 HP she is knocked down and her blade skids away (`defeat: disarm`). Nyaakoto holds 残心 and does not finish her (katsujinken).

**Parameters**

- Boss `boss_collatera`, arena `vol_bridge_arena` (locked); defeat `disarm`; checkpoint per phase; telegraph min windup 400 ms (Normal).
  - From 100% HP: `collatera_p1_pistols`
  - From 60% HP: `collatera_p2_margin_call`, adds `drone_pair`, arena_mod `list_port_10deg`
  - From 30% HP: `collatera_p3_sabre`, arena_mod `shield_burnout`
- Proposed extensions: `x_fate` knocked_down_left_on_bridge; `x_boss_stats` {hp: 2000, shield_hp: 240, shield_regen_delay_s: 4.0, shield_regen_per_s: 80, shield_offline_on_reload_s: 1.6, awase_stagger_s: 1.2, damage_mult_vs_shield: {default: 1.0, melee: 1.25, w11: 1.5, w16: 2.5}, w14_charged_vs_shield: removes_50pct_max}.
- Fail: `player_died` → `checkpoint`. Music state `mus_boss_collatera`.

**Dialogue triggers**

- `boss_phase:1` (bark): line 001
- `pattern:twin_burst` (bark): line 002 (repeatable)
- `pattern:reload` (bark): line 003 (repeatable)
- `pattern:reload:first` (ambient): line 004
- `shield_broken` (bark): line 005 (repeatable)
- `boss_phase:2` (bark): line 006
- `pattern:margin_call` (bark): line 007 (repeatable)
- `boss_phase:2` (ambient): line 008
- `idle_in_cover_s:6` (bark): line 009 (repeatable)
- `boss_phase:3` (bark): line 010
- `pattern:fleche_lunge` (bark): line 011 (repeatable)
- `player_died` (ambient): line 012 (repeatable)
- `boss_defeated` (bark): line 013

Attack tables (proposal for L3 `bosses.json`; Normal; Easy +30% windup, Hard −15%):

**`collatera_p1_pistols`** (cadence [2.4, 2.6, 2.2] s)

| Attack | Windup (ms) | Telegraph | Damage | Recovery (ms) | Parry | Counterplay / notes |
|---|---|---|---|---|---|---|
| `twin_burst` | 400 | cyan_laser_dots | 9 × 6 | 500 | no | strafe 150 cm or more during windup breaks the lock |
| `sidestep_burst` | 400 | cyan_laser_dots | — | 500 | no | dash_cm 400; then twin_burst |
| `reload` | — | cell_eject_hiss | — | — | no | any hit lands, including arrows; shield offline; every_n_bursts 3; duration_ms 1600 |

**`collatera_p2_margin_call`** (cadence [3.0, 3.0, 3.0] s)

| Attack | Windup (ms) | Telegraph | Damage | Recovery (ms) | Parry | Counterplay / notes |
|---|---|---|---|---|---|---|
| `margin_call` | 1500 | amber_ring_250cm | 60 | — | no | targeting cover nearest the player, else the player's position; every_s 7.0; cover_hits_to_destroy 2; max_cover_destroyed 6 |
| `twin_burst` | 400 | cyan_laser_dots | 9 × 6 | 500 | no |  |
| `reload` | — | cell_eject_hiss | — | — | no | shield offline; every_n_bursts 3; duration_ms 1600 |
| `slide_props` | 700 | scrape_audio_and_wobble | 30 | — | no | every_s 6.0; knockdown_s 0.6 |

**`collatera_p3_sabre`** (cadence: cut_pair, offhand_shot, fleche_lunge; gaps 1.0/1.2/1.5 s)

| Attack | Windup (ms) | Telegraph | Damage | Recovery (ms) | Parry | Counterplay / notes |
|---|---|---|---|---|---|---|
| `cut_pair` | 450 | amber_edge_flash | 22 | 600 | yes | on_awase stagger_1200ms_on_second_cut |
| `fleche_lunge` | 800 | amber_floor_line_500cm | 35 | 1100 | yes | on_awase stagger_1200ms; on_marobashi flank_window_1500ms |
| `offhand_shot` | 400 | cyan_laser_dot | 14 | 400 | no | sidestep |


#### ch07.b14: production_task (hold) · 信号灯と舵を守れ / Hold the beacon and the helm · 3.0 min · site 2

- **The hold:** Nyaakoto holds the helm floor for 60 s of progress while Kohagi lights the beacon behind its armored housing. She is not downable here.
- **Enemies and trim:** reinforcements come from the rear doors, the side hatches and the dome. At each trim alarm the player must step to the helm wheel within 8 s.
- **Stakes:** a 150 s fail timer gives the hold real stakes without a surprise death. The ship lists 5°.
- **Through the window:** at 50% the window shows a line of warm lanterns climbing the ridge: Oyuki's evacuation route, marked with ch03's mon-painted lanterns. The catalog's `restored` text ("The beacon marked a safe evacuation route for residents") is shown on completion.
- **Collatera:** she lies unconscious by the pulpit throughout.

**Parameters**

- Hold `vol_helm` for 60 s; contest `pause` (progress pauses while an enemy stands inside the volume).
- Waves:
  - **W1** on `start`: `enforcer_rifle` ×3 @ `sp_bridge_rear_doors`
  - **W2** on `progress_at:0.4`: `blade_retainer` ×2 @ `sp_bridge_port_hatch`; `drone` ×2 @ `sp_bridge_dome`
  - **W3** on `progress_at:0.75`: `shield_enforcer` ×1 @ `sp_bridge_stbd_hatch`; `enforcer_rifle` ×2 (shielded) @ `sp_bridge_rear_doors`
- Proposed extensions: `x_allies` [{npc: kohagi, role: beacon, downable: false}]; `x_trim_events` {at_progress: [0.25, 0.5, 0.75], interact_point: helm_trim_wheel, interact_s: 2.0, grace_s: 8, decay_per_s_if_ignored: 0.02}; `x_fail_timer` {normal_s: 150, easy_s: 200, hard_s: 130, on_expire: fail, fiction: "the ship's glide reaches the ridge villages"}; `x_environment` {list_deg: 5}; `x_fail_extra` {"on": x_timer_expired, to: checkpoint}.
- Fail: `player_died` → `checkpoint`; `x_timer_expired` → `checkpoint`. Music state `mus_ch07_helm`.

**Dialogue triggers**

- `beat_start` (ambient): line 001
- `beat_start` (radio): line 002
- `trim_event` (ambient): line 003 (repeatable)
- `trim_event:first` (ambient): line 004
- `progress_at:0.4` (radio): line 005
- `progress_at:0.5` (ambient): line 006
- `beat_complete` (radio): line 007

#### ch07.b15: cinematic · 墜落 / The fall · 2.0 min

- **The offer:** the moor rushes up in the window. Nyaakoto kneels and offers Collatera his hand. She refuses and stays, her fate left open, consistent with "lost in the controlled crash" (bible §8).
- **The leap:** Kohagi drags him to the hangar. They ride a cargo sled down its rails and out of the mouth as the belly touches the moor. The sled skids through the grass while the flagship ploughs a 600 m furrow.
- **The wreck:** there is no fireball. The hull's ledger lines go dark one by one.

**Parameters**

- Sequence `/Game/Cinematics/Ch07/LS_Ch07_B15_TheFall`, 120 s, skippable; fallback `camera_blend` (letterboxed in-engine camera until C9).
- End state: player at `ps_ch07_b16_start`, equipped "keep".
- Proposed extensions: `x_places_spanned` [pl_bridge, pl_hangar, pl_kayanohara].
- Fail: none (cinematic). Music state `mus_ch07_fall`.

**Dialogue triggers**

- cinematic subtitles: lines 001–004

#### ch07.b16: dialogue · 萱野原 / Kaya Moor · 1.0 min

- **The riders:** walk-and-talk in the rain. Toranosuke's riders come out of the storm with Kurimaru, and the b01 exchange about catching whatever falls closes.
- **The broadcast:** entering `vol_riders` starts a blocking broadcast of 3 lines (≤ 20 s) with a soft look toward the Citadel. The source is Val Amort, through every hull horn in the wreck and every door numeral in the valley. The bible's line 「全担保を回収する。」 is followed by "People, too, are collateral."
- **Ending:** Oyuki's radio line, then Nyaakoto's 「先生を、取り戻す。」 Chapter complete, then the registry page.

**Parameters**

- Mode `ambient`, trigger `beat_start`, interrupt `queue`, camera `soft_lookat`.
- Proposed extensions: `x_on_complete` "chapter_complete -> registry_page".
- Fail: `player_died` → `checkpoint`. Music state `mus_ch07_aftermath`.

**Dialogue triggers**

- `beat_start` (ambient): lines 001–003
- `volume_enter:vol_riders` (blocking): lines 004–006
- `volume_enter:vol_riders` (radio): line 007
- `volume_enter:vol_riders` (ambient): line 008

### 2.5 Collectibles

These are six passive `collectible` entries (bible §10), not counted as beats and never granting stats. Rewards are codex entries plus epilogue restoration: the returned name board hangs again in ch08.

| Id (`collectible_id`) | Art slug | Category | Place | Mask bit | Codex (JA) | Codex (EN) |
|---|---|---|---|---|---|---|
| `ch07.c01` | `ch07_heirloom_nafudakake` | heirloom | `pl_seized_vault` | 0 | 爪木坂道場の名札掛け。門弟の名札一枚ごとに、取立猫の番号札が貼られていた。 | The Tsumagizaka Dōjō name board. Every pupil's plaque bore a Collector's number tag. |
| `ch07.c02` | `ch07_notice_debtor_7031` | seizure_notice | `pl_seized_vault` | 1 | 差押状。債務者番号七〇三一。差押物件、和弓一張、矢十二本。「執行保留：所持者未確保」 | Seizure notice. Debtor 7031. Items: one yumi, twelve arrows. 'Execution pending: holder not secured.' |
| `ch07.c03` | `ch07_scroll_wind` | scroll_fragment | `pl_seized_vault` | 2 | 伝書の断簡、其の七。「風に逆らう矢は落ち、風を読む矢は届く。刀もまた同じ。」石鈴斎 | Scroll fragment VII. 'An arrow that fights the wind falls; one that reads it arrives. So too the sword.' Sekireisai |
| `ch07.c04` | `ch07_league_mark_bale` | league_mark | `pl_cargo_hold` | 3 | 俵の内側に、爪で刻まれた空紋。積み込みの債縛衆の誰かが、味方だ。 | A Sora mark scratched inside a bale. One of the collared loaders is with us. |
| `ch07.c05` | `ch07_registry_annotated` | registry_page | `pl_reckoning_engine` | 4 | 提灯街の改帳の写し。欄外に異星の注記。「無担保。債務にあらず。分類不能」 | A copy of the Lantern Ward registry. An alien note in the margin: 'Unsecured. Not debt. Unclassifiable.' |
| `ch07.c06` | `ch07_notice_shuttle_manifest` | seizure_notice | `pl_hangar` | 5 | 輸送艇の積荷目録。「押収予定：猫柳生の住民、全員。区分：担保（生体）」 | A shuttle manifest. 'Scheduled for seizure: all Nyaagyu residents. Category: collateral (living).' |

Placement:

- `c01`–`c03` are in the seized vault (b05): name board, notice rack and armor chest.
- `c04` is inside an outer bale bay in the hold at (54, 16, 0.5), reached through a dark crawl gap.
- `c05` is on the engine room's west mezzanine desk.
- `c06` is in shuttle 2's cockpit in the hangar.

`c02` and `c06` foreshadow Val Amort's closing decree.

---

## 3. Dialogue script

### 3.1 Conventions

- **Line ids** follow bible §18, `ch07.bMM.<name>.<nnn>`, numbered in order within each beat. The `speaker` column holds the schema-4 speaker id.
- **Durations** are estimated for VO: about 6 kana/kanji per second plus pauses, then checked against 17 cps of English. They are placeholders until recorded.
- **Subtitles:**
  - EN is split into at most 2 lines of ≤ 42 characters (shown split with " / ").
  - JA captions stay within 32 characters (2 lines of 16).
  - Minimum 1.0 s on screen.
- **Modes:** `cinematic` (subtitle of a cinematic beat), `ambient` (walk-and-talk, control kept), `radio` (slate audio with the radio DSP), `blocking` (≤ 20 s) and `bark` (a boss's captioned audio telegraph). `rep` marks a repeatable bark with a cooldown.
- **Readings** give furigana for rare words for VO and the native reviewer.
- **Registers** follow bible §6 and §18:
  - Aliens speak flat keigo through the 通訳襟 (band-limited formant chorus, no pitch shift) and use no English contractions.
  - Samurai English is measured ("I will").
  - Kamigata speech becomes warm colloquial English.

### 3.2 Speakers in this chapter

| Speaker id | JA | EN | Status | Lines |
|---|---|---|---|---|
| `samurai` | ニャーコト | Nyaakoto | in catalog schema 3 | 17 |
| `scout` | 小萩 | Kohagi | in catalog schema 3 | 34 |
| `leader` | お雪 | Oyuki | proposed in bible §6 | 8 |
| `clerk` | イオタ | Iota | proposed in bible §6 | 22 |
| `rival` | 虎之介 | Toranosuke | proposed in bible §6 | 4 |
| `gunsmith` | 鉄五郎 | Tetsugorō | proposed in bible §6 | 1 |
| `farmer_young` | お種 | Otane | proposed in bible §6 | 2 |
| `fireworks` | 玉吉 | Tamakichi | proposed in bible §6 | 1 |
| `apothecary` | お葛 | Okuzu | proposed in bible §6 | 1 |
| `boss_collatera` | コラテラ | Collatera | proposed in bible §6 | 15 |
| `banker` | ヴァル・アモルト | Val Amort | in catalog schema 3 | 3 |
| `enforcer` | 執行兵 | Enforcer | **new proposal (this chapter)** | 18 |
| `auditor` | 監査官 | Auditor | **new proposal (this chapter)** | 2 |
| `league_ashigaru` | 一揆の足軽 | League ashigaru | **new proposal (this chapter)** | 2 |
| `conscript` | 債縛の人足 | Collared loader | **new proposal (this chapter)** | 3 |
| `ship_voice` | 艦内通達 | Ship announcement | **new proposal (this chapter)** | 4 |

### 3.3 Lines by beat

#### ch07.b01: 軍議 / The war council

| # | Line id | Trigger (mode) | Speaker | Japanese | Readings | English subtitle | s | Notes |
|---|---|---|---|---|---|---|---|---|
| 001 | `ch07.b01.kohagi.001` | cinematic subtitle | 小萩 / Kohagi | 旗艦が城塞から最後の力を吸い上げている。 | 旗艦(きかん) | The flagship is drawing the / last power from the citadel. | 4.0 | Catalog anchor, ch07 line 1 (speaker scout); text unchanged. |
| 002 | `ch07.b01.oyuki.002` | cinematic subtitle | お雪 / Oyuki | 力だけではございません。米、長持、刀、寺の鐘まで。 | 長持(ながもち) | Not only power. Rice, chests, / swords, even the temple bell. | 4.9 | — |
| 003 | `ch07.b01.iota.003` | cinematic subtitle | イオタ / Iota | 今夜のうちに、千二百駄を積み上げる予定でございます。 | 駄(だ) | They plan to haul up / 1,200 horse-loads tonight. | 4.8 | 駄 = one pack-horse load; see §4.1. |
| 004 | `ch07.b01.nyaakoto.004` | cinematic subtitle | ニャーコト / Nyaakoto | 嵐の夜なら、誰も来ぬと踏んだか。 | — | They wagered no one would come in a storm. | 3.1 | — |
| 005 | `ch07.b01.oyuki.005` | cinematic subtitle | お雪 / Oyuki | 嵐の中の一揆は、あちらの帳簿では「零」の査定です。 | 一揆(いっき)、査定(さてい) | In their books, / a league in a storm is valued at zero. | 4.3 | — |
| 006 | `ch07.b01.oyuki.006` | cinematic subtitle | お雪 / Oyuki | その査定、覆してさしあげましょう。 | 覆(くつがえ)して | Let us correct their appraisal. | 3.3 | Dry wit, not a gag. |
| 007 | `ch07.b01.iota.007` | cinematic subtitle | イオタ / Iota | 通信塔を切れば検品が止まり、俵の中身はどなたも確かめません。 | 検品(けんぴん)、俵(たわら) | Cut the relay and inspection stops. / No one will check the bales. | 5.5 | — |
| 008 | `ch07.b01.kohagi.008` | cinematic subtitle | 小萩 / Kohagi | 俵に入る。あたしと、あんた。 | — | We go in the bales. Me. You. | 2.9 | — |
| 009 | `ch07.b01.oyuki.009` | cinematic subtitle | お雪 / Oyuki | 務めは三つ。通信塔を切る。荷を下ろす。艦を落とす。 | 務(つと)め | Three tasks. Cut the relay. / Send the goods down. Bring the ship down. | 4.9 | A briefing list; bare verbs are natural here. |
| 010 | `ch07.b01.iota.010` | cinematic subtitle | イオタ / Iota | 無人の落下地点は、萱野原のみでございます。 | 萱野原(かやのはら) | The only uninhabited / landing site is Kaya Moor. | 4.0 | — |
| 011 | `ch07.b01.toranosuke.011` | cinematic subtitle | 虎之介 / Toranosuke | 俺は騎馬を集めて、萱野原で待つ。 | — | I will gather riders / and wait at Kaya Moor. | 3.1 | — |
| 012 | `ch07.b01.toranosuke.012` | cinematic subtitle | 虎之介 / Toranosuke | ……お前への借りは、生きて返す。 | — | …What I owe you, I will repay alive. | 3.4 | Theme 3: debt as chain vs obligation among makers. |
| 013 | `ch07.b01.nyaakoto.013` | cinematic subtitle | ニャーコト / Nyaakoto | 借りではない。 | — | It is no debt. | 1.5 | — |
| 014 | `ch07.b01.tetsugoro.014` | cinematic subtitle | 鉄五郎 / Tetsugorō | 連発銃だ。三十六発、雨でも黙らん。 | 連発銃(れんぱつじゅう) | The repeater. Thirty-six rounds. / Rain won't silence it. | 3.9 | Plays on the weapon 9 unlock. |

#### ch07.b02: 錨台の通信塔を断て / Cut the anchor bastion's relay

| # | Line id | Trigger (mode) | Speaker | Japanese | Readings | English subtitle | s | Notes |
|---|---|---|---|---|---|---|---|---|
| 001 | `ch07.b02.tamakichi.001` | `volume_enter:vol_bastion_staging` (ambient) | 玉吉 / Tamakichi | 湿気た玉は、ただの紙や。今夜はわしの出番なしやな。 | 湿気(しけ)た | Damp shells are just paper. / No work for me tonight. | 4.8 | — |
| 002 | `ch07.b02.okuzu.002` | `volume_enter:vol_bastion_staging` (ambient) | お葛 / Okuzu | 傷薬は腰に。濡らさないようにね。 | 傷薬(きずぐすり) | Salve's at your hip. Keep it dry. | 3.2 | — |
| 003 | `ch07.b02.ashigaru.003` | `volume_enter:vol_bastion_staging` (ambient) | 一揆の足軽 / League ashigaru | 空紋の幟は畳んどけ。風に持っていかれるぞ。 | 空紋(そらもん)、幟(のぼり) | Keep the Sora banners furled. / The wind will take them. | 4.0 | Explains why no nobori fly in ch07. |
| 004 | `ch07.b02.otane.004` | `volume_enter:vol_bastion_steps` (ambient) | お種 / Otane | 雨で火縄は死ぬけどな、鉄五郎さんのは生きとる！　撃てえ！ | 火縄(ひなわ) | Rain kills a match, / but Tetsugorō's guns live! Fire! | 4.8 | Callback to the gunsmith's register sample (§6.5). |
| 005 | `ch07.b02.kohagi.005` | `volume_enter:vol_bastion_steps` (ambient) | 小萩 / Kohagi | 櫓に照準査定兵、一。石段の上に四。 | 櫓(やぐら)、照準査定兵(しょうじゅんさていへい) | Marksman in the turret, / one. Four atop the steps. | 3.5 | — |
| 006 | `ch07.b02.kohagi.006` | `volume_enter:vol_relay_foot` (ambient) | 小萩 / Kohagi | 塔の根元に繋ぎ箱が三つ。全部切って。 | 繋(つな)ぎ箱 | Three junction boxes at the tower's foot. / Cut them all. | 3.9 | — |
| 007 | `ch07.b02.kohagi.007` | `progress_at:0.34` (ambient) | 小萩 / Kohagi | 一つ切れた。あと二つ。 | — | One cut. Two left. | 2.4 | — |
| 008 | `ch07.b02.otane.008` | `progress_at:0.34` (ambient) | お種 / Otane | 上から降りてくるで！　昇降台や！ | 昇降台(しょうこうだい) | They're coming down! Off the lift! | 2.7 | — |
| 009 | `ch07.b02.kohagi.009` | `progress_at:0.67` (ambient) | 小萩 / Kohagi | 二つ目。……北の門から回ってくる。 | — | That's two. / …They're flanking from the north gate. | 3.7 | — |
| 010 | `ch07.b02.nyaakoto.010` | `site_restored:0` (ambient) | ニャーコト / Nyaakoto | これで、艦は目を失った。 | — | Now the ship is blind. | 2.5 | — |
| 011 | `ch07.b02.iota.011` | `beat_complete` (radio) | イオタ / Iota | 検品網、停止を確認。……帳簿様、申し訳ございません。 | 帳簿様(ちょうぼさま) | Inspection net offline. / …My apologies, Honored Ledger. | 5.3 | Iota honors objects (§6.3). |
| 012 | `ch07.b02.enforcer.012` | `alert_state:alert` (ambient, rep) | 執行兵 / Enforcer | 無許可の集会を確認。解散を勧告します。 | 勧告(かんこく) | Unauthorized assembly. / You are advised to disperse. | 3.7 | — |
| 013 | `ch07.b02.enforcer.013` | `wave_spawned` (ambient, rep) | 執行兵 / Enforcer | 延滞者多数。回収を開始します。 | 延滞者(えんたいしゃ) | Multiple delinquents. Commencing recovery. | 3.0 | — |
| 014 | `ch07.b02.enforcer.014` | `enemy_retreat` (ambient, rep) | 執行兵 / Enforcer | 損失拡大。後退し、再評価します。 | — | Losses rising. Withdrawing to reassess. | 3.3 | — |
| 015 | `ch07.b02.marksman.015` | `pattern:marksman_lock` (ambient, rep) | 執行兵 / Enforcer | 照準、査定完了。 | — | Aim assessed. | 1.8 | Marksman voice variant. Plays at the start of the 900 ms glint, so it doubles as an audio telegraph. |
| 016 | `ch07.b02.ashigaru.016` | `npc_downed:teppo_*` (ambient, rep) | 一揆の足軽 / League ashigaru | やられた……！　誰か！ | — | I'm hit…! Someone! | 2.1 | — |

#### ch07.b03: 俵に潜め / Hide in the rice bales

| # | Line id | Trigger (mode) | Speaker | Japanese | Readings | English subtitle | s | Notes |
|---|---|---|---|---|---|---|---|---|
| 001 | `ch07.b03.kohagi.001` | cinematic subtitle | 小萩 / Kohagi | 息は浅く。耳、伏せて。 | — | Breathe shallow. Ears down. | 2.4 | — |
| 002 | `ch07.b03.conscript.002` | cinematic subtitle | 債縛の人足 / Collared loader | ……空紋や。ご武運を。 | ご武運(ぶうん) | …The Sora mark. Good fortune to you. | 2.8 | Collared loader sees the chalk mon on the bale. Whispered. |
| 003 | `ch07.b03.enforcer.003` | cinematic subtitle | 執行兵 / Enforcer | 検品端末、応答なし。手動で計上します。 | 計上(けいじょう) | Scanner unresponsive. Logging manually. | 3.8 | — |
| 004 | `ch07.b03.enforcer.004` | cinematic subtitle | 執行兵 / Enforcer | 米、二俵。……重量、やや超過。 | 二俵(にひょう) | Rice, two bales. …Slightly overweight. | 3.4 | — |
| 005 | `ch07.b03.enforcer.005` | cinematic subtitle | 執行兵 / Enforcer | 誤差の範囲内とします。積載。 | 誤差(ごさ) | Within the margin of error. Load them. | 2.9 | Their own arithmetic lets the League aboard. |
| 006 | `ch07.b03.kohagi.006` | cinematic subtitle | 小萩 / Kohagi | くしゃみ、するな。 | — | Don't sneeze. | 2.0 | Approved humor beat #6 (bible §1.2). Nyaakoto answers with silence. |
| 007 | `ch07.b03.shipvoice.007` | cinematic subtitle | 艦内通達 / Ship announcement | 積荷を受領。貨物倉へ搬入します。 | 積荷(つみに)、搬入(はんにゅう) | Cargo received. Transferring to the hold. | 3.2 | — |

#### ch07.b04: 貨物倉を抜けよ / Cross the cargo hold unseen

| # | Line id | Trigger (mode) | Speaker | Japanese | Readings | English subtitle | s | Notes |
|---|---|---|---|---|---|---|---|---|
| 001 | `ch07.b04.kohagi.001` | `beat_start` (ambient) | 小萩 / Kohagi | 右に二。上に目録が一。……灯りは、あっち。 | 目録(もくろく) | Two right. One drone above. / …Light's that way. | 4.5 | Whispered. 目録 ('Inventory') is the drone type's name (bible §7). |
| 002 | `ch07.b04.kohagi.002` | `beat_start` (ambient) | 小萩 / Kohagi | 艦が鳴ってる間は、足音が消える。 | — | While the hull groans, / your steps can't be heard. | 3.5 | Tutorial: hull-boom noise masking. |
| 003 | `ch07.b04.nyaakoto.003` | `volume_enter:vol_hold_bell` (ambient) | ニャーコト / Nyaakoto | 村の鐘まで……。 | — | Even the village bell… | 2.0 | — |
| 004 | `ch07.b04.kohagi.004` | `volume_enter:vol_hold_bell` (ambient) | 小萩 / Kohagi | 鐘に礫を当てたら、みんな寄ってく。一度きり。 | 礫(つぶて) | Hit the bell with a stone and / they'll all go to it. Once only. | 4.4 | Tutorial: one-shot bell lure. |
| 005 | `ch07.b04.enforcer.005` | `volume_enter:vol_hold_appraisal` (ambient) | 執行兵 / Enforcer | 品目四四七、漆の長持。付帯する思い出は、評価対象外。 | 四四七(よんよんなな)、長持(ながもち) | Item 447, lacquered chest. / Attached memories: not appraisable. | 5.0 | Overheard. Menace through politeness. |
| 006 | `ch07.b04.auditor.006` | `volume_enter:vol_manifest_desk` (ambient) | 監査官 / Auditor | 米二俵、検品記録なし。……後ほど照合を。 | 照合(しょうごう) | Two rice bales, no inspection record. / …Reconcile later. | 4.2 | Overheard. Tension: they have noticed the bales. |
| 007 | `ch07.b04.conscript.007` | `seal_cut:g_c1` (ambient) | 債縛の人足 / Collared loader | ……首が軽い。前の扉、見張りは一人や。 | — | …My neck's light. / One guard at the forward door. | 4.0 | Freed loader gives intel, then hides. |
| 008 | `ch07.b04.conscript.008` | `seal_cut:g_c2` (ambient) | 債縛の人足 / Collared loader | 助かった……。黙って隠れとく。 | — | Thank you… I'll hide and keep quiet. | 3.3 | — |
| 009 | `ch07.b04.enforcer.009` | `alert_state:suspicious` (ambient, rep) | 執行兵 / Enforcer | ……在庫の移動を検知。 | 在庫(ざいこ) | …Inventory movement detected. | 2.5 | — |
| 010 | `ch07.b04.enforcer.010` | `alert_state:search` (ambient, rep) | 執行兵 / Enforcer | 未登録品を捜索します。 | 捜索(そうさく) | Searching for unregistered items. | 2.5 | — |
| 011 | `ch07.b04.enforcer.011` | `alert_state:alert` (ambient, rep) | 執行兵 / Enforcer | 密航者です。差し押さえます。 | 密航者(みっこうしゃ) | Stowaway. Seizing. | 2.9 | — |
| 012 | `ch07.b04.enforcer.012` | `alert_state:unaware` (ambient, rep) | 執行兵 / Enforcer | 誤差の範囲内と判断します。 | — | Judged within the margin of error. | 2.5 | Search ends without contact. Echoes b03 on purpose. |
| 013 | `ch07.b04.auditor.013` | `auditor_alarm` (ambient, rep) | 監査官 / Auditor | 照合不一致！　警報を！ | — | Records do not match! Raise the alarm! | 2.8 | — |
| 014 | `ch07.b04.kohagi.014` | `lure_triggered:bell_bonsho` (ambient) | 小萩 / Kohagi | 今。 | — | Now. | 1.2 | — |
| 015 | `ch07.b04.shipvoice.015` | `wave_spawned:hold_alarm` (ambient) | 艦内通達 / Ship announcement | 貨物倉に未登録品。保安要員は急行してください。 | 保安要員(ほあんよういん) | Unregistered item in the hold. / Security, respond. | 4.3 | — |

#### ch07.b05: 押収品倉を調べる / Search the seized-goods vault

| # | Line id | Trigger (mode) | Speaker | Japanese | Readings | English subtitle | s | Notes |
|---|---|---|---|---|---|---|---|---|
| 001 | `ch07.b05.kohagi.001` | `volume_enter:vol_vault_door` (ambient) | 小萩 / Kohagi | 左の壁に錠。鍵板で開く。 | 錠(じょう)、鍵板(かぎいた) | Lock on the left wall. / The key-slate opens it. | 3.3 | — |
| 002 | `ch07.b05.nyaakoto.002` | `poi_found:poi_nafudakake` (ambient) | ニャーコト / Nyaakoto | ……名札掛けだ。先生の道場の。 | 名札掛(なふだか)け | …The name board. From Sensei's dojo. | 3.3 | — |
| 003 | `ch07.b05.kohagi.003` | `poi_found:poi_nafudakake` (ambient) | 小萩 / Kohagi | 札の一枚ずつに、番号が貼ってある。 | — | They've stuck a number on every plaque. | 3.3 | — |
| 004 | `ch07.b05.nyaakoto.004` | `poi_found:poi_nafudakake` (ambient) | ニャーコト / Nyaakoto | 名は、番号ではない。 | — | A name is not a number. | 2.1 | — |
| 005 | `ch07.b05.kohagi.005` | `idle_s:90` (ambient) | 小萩 / Kohagi | そろそろ。機関室は前。 | — | Time to go. The engine room is forward. | 2.9 | Exit hint (exit_hint_after_s: 90). |

#### ch07.b06: 算術機関室を制圧せよ / Take the reckoning engine

| # | Line id | Trigger (mode) | Speaker | Japanese | Readings | English subtitle | s | Notes |
|---|---|---|---|---|---|---|---|---|
| 001 | `ch07.b06.nyaakoto.001` | `beat_start` (ambient) | ニャーコト / Nyaakoto | 算盤か……。利子を数え続けている。 | 算盤(そろばん) | An abacus… / counting interest, without end. | 3.6 | — |
| 002 | `ch07.b06.iota.002` | `beat_start` (radio) | イオタ / Iota | ご注意ください。その先の執行兵は、個人障壁をお持ちです。 | 執行兵(しっこうへい)、障壁(しょうへき) | Caution. The enforcers ahead / carry personal shields. | 5.3 | — |
| 003 | `ch07.b06.iota.003` | `shield_hit_first` (radio) | イオタ / Iota | 障壁は、四秒間被弾がなければ、再充填されます。 | 被弾(ひだん)、再充填(さいじゅうてん) | A shield recharges after / four seconds unhit. | 4.4 | Tutorial: shield regeneration rule. |
| 004 | `ch07.b06.kohagi.004` | `shield_hit_first` (ambient) | 小萩 / Kohagi | 休ませるな。撃ち続けて。 | — | Don't let it rest. Keep firing. | 2.5 | — |
| 005 | `ch07.b06.iota.005` | `pickup:11` (radio) | イオタ / Iota | そのパルス・カービンは、障壁に対し一・五倍の効率でございます。 | 一・五(いってんご) | That pulse carbine works / 1.5 times better on shields. | 5.3 | Tutorial: weapon 11 vs shields. |
| 006 | `ch07.b06.enforcer.006` | `shield_broken` (ambient, rep) | 執行兵 / Enforcer | 障壁、喪失。 | 喪失(そうしつ) | Shield lost. | 1.5 | Feedback bark: confirms the break. |
| 007 | `ch07.b06.enforcer.007` | `pattern:grenadier_throw` (ambient, rep) | 執行兵 / Enforcer | 広域回収、実行します。 | — | Executing area recovery. | 2.3 | Grenadier; plays with the arc decal. |
| 008 | `ch07.b06.enforcer.008` | `pattern:retainer_close` (ambient, rep) | 執行兵 / Enforcer | 取り立てます。 | — | Collecting. | 1.5 | Collection Blade closing distance (flavor, not the 420 ms telegraph). |

#### ch07.b07: 昇降機を逆転させよ / Reverse the extraction lift

| # | Line id | Trigger (mode) | Speaker | Japanese | Readings | English subtitle | s | Notes |
|---|---|---|---|---|---|---|---|---|
| 001 | `ch07.b07.iota.001` | `beat_start` (radio) | イオタ / Iota | その大きな輪が、昇降機の手動制御でございます。 | 昇降機(しょうこうき) | That large wheel is the / lift's manual override. | 4.3 | — |
| 002 | `ch07.b07.iota.002` | `beat_start` (radio) | イオタ / Iota | 機関の回転と、逆へお回しください。 | — | Turn it against the engine. | 3.3 | Tutorial: reverse-torque crank. |
| 003 | `ch07.b07.kohagi.003` | `progress_at:0.25` (ambient) | 小萩 / Kohagi | 爪、掛けた。もう戻らない。 | 爪(つめ) | Pawl's set. It won't slip back. | 2.8 | Tutorial: ratchet locks at 25/50/75%. |
| 004 | `ch07.b07.nyaakoto.004` | `progress_at:0.5` (ambient) | ニャーコト / Nyaakoto | 重い……！ | — | Heavy…! | 1.3 | — |
| 005 | `ch07.b07.kohagi.005` | `progress_at:0.75` (ambient) | 小萩 / Kohagi | あと少し。 | — | Almost. | 1.2 | — |
| 006 | `ch07.b07.kohagi.006` | `crank_released` (ambient, rep) | 小萩 / Kohagi | 手、離すな。戻される。 | — | Don't let go. It'll pull back. | 2.4 | Cooldown 30 s. |
| 007 | `ch07.b07.iota.007` | `beat_complete` (radio) | イオタ / Iota | 昇降機、逆転。積荷、降下中でございます。 | 降下(こうか) | Lift reversed. Cargo descending. | 4.0 | — |
| 008 | `ch07.b07.oyuki.008` | `site_restored:1` (radio) | お雪 / Oyuki | 受け取りました。駄数を記帳いたします。 | 駄数(だすう)、記帳(きちょう) | Received. We are recording the loads. | 3.7 | — |
| 009 | `ch07.b07.oyuki.009` | `site_restored:1` (radio) | お雪 / Oyuki | 返還は記帳のみ。札は切りません。持ち主へ、お返しするだけです。 | 札(ふだ) | Returns are recorded, / no tally cut. They simply go home. | 5.9 | Charter article 1: nothing new was made, so no XOR is cut. |

#### ch07.b08: 格納庫を突破せよ / Break through the hangar

| # | Line id | Trigger (mode) | Speaker | Japanese | Readings | English subtitle | s | Notes |
|---|---|---|---|---|---|---|---|---|
| 001 | `ch07.b08.kohagi.001` | `beat_start` (ambient) | 小萩 / Kohagi | 上の回廊に照準査定兵。光ったら隠れて。 | 回廊(かいろう) | Marksman on the gallery. / When it glints, take cover. | 3.7 | — |
| 002 | `ch07.b08.enforcer.002` | `alert_state:alert` (ambient) | 執行兵 / Enforcer | 格納庫に侵入者。資産を保全してください。 | 格納庫(かくのうこ)、保全(ほぜん) | Intruder in the hangar. Secure the assets. | 3.8 | — |
| 003 | `ch07.b08.kohagi.003` | `volume_enter:vol_hangar_canisters` (ambient) | 小萩 / Kohagi | 光る筒は、撃てば弾ける。 | 弾(はじ)ける | Those glowing canisters burst when shot. | 2.9 | — |
| 004 | `ch07.b08.iota.004` | `pickup:14` (radio) | イオタ / Iota | プラズマ火縄銃は、溜めて撃つ設計でございます。 | 火縄銃(ひなわじゅう)、溜(た)めて | The plasma matchlock is / designed to be charged. | 4.3 | Tutorial: charged shot. |
| 005 | `ch07.b08.iota.005` | `pickup:14` (radio) | イオタ / Iota | 溜めた一発は、障壁を貫きます。 | 貫(つらぬ)きます | A charged shot pierces shields. | 3.0 | — |
| 006 | `ch07.b08.kohagi.006` | `wave_spawned:2` (ambient) | 小萩 / Kohagi | 大盾、二。回り込んで。 | 大盾(おおだて) | Two big shields. Go around them. | 2.4 | — |
| 007 | `ch07.b08.kohagi.007` | `volume_enter:vol_sled_bay` (ambient) | 小萩 / Kohagi | あの橇、覚えといて。 | 橇(そり) | Those sleds. Remember them. | 2.1 | Sets up the b15 sled leap. |

#### ch07.b09: 地上からの報せ / Word from the ground

| # | Line id | Trigger (mode) | Speaker | Japanese | Readings | English subtitle | s | Notes |
|---|---|---|---|---|---|---|---|---|
| 001 | `ch07.b09.iota.001` | `beat_start` (radio) | イオタ / Iota | 地上より報告。鷲尾様の騎馬、萱野原に集結。二十騎でございます。 | 鷲尾(わしお)、騎(き) | Word from the ground. Lord Washio's / riders are at Kaya Moor. Twenty. | 5.9 | — |
| 002 | `ch07.b09.iota.002` | `beat_start` (radio) | イオタ / Iota | ……訂正いたします。二十一騎。ただいま一騎、到着いたしました。 | — | …Correction. Twenty-one. / One more has just arrived. | 6.2 | Proposed light moment H2 (Iota's literalism); needs tone sign-off. |
| 003 | `ch07.b09.iota.003` | `beat_start` (radio) | イオタ / Iota | 背骨通路は、提督が封鎖いたしました。 | 背骨(せぼね)、提督(ていとく) | The admiral has sealed the spine corridor. | 3.5 | — |
| 004 | `ch07.b09.iota.004` | `beat_start` (radio) | イオタ / Iota | 艦橋へは、外殻の上を通るほかございません。 | 艦橋(かんきょう)、外殻(がいかく) | The only way to the / bridge is over the hull. | 4.0 | — |
| 005 | `ch07.b09.iota.005` | `beat_start` (radio) | イオタ / Iota | 外は静穏域の縁でございます。突風にご注意を。 | 静穏域(せいおんいき)、縁(ふち) | Outside is the edge of the calm. / Beware of gusts. | 4.2 | — |
| 006 | `ch07.b09.nyaakoto.006` | `beat_start` (radio) | ニャーコト / Nyaakoto | 風を読む。 | — | I will read the wind. | 1.6 | — |

#### ch07.b10: 外殻の稜線を渡れ / Cross the hull ridge

| # | Line id | Trigger (mode) | Speaker | Japanese | Readings | English subtitle | s | Notes |
|---|---|---|---|---|---|---|---|---|
| 001 | `ch07.b10.nyaakoto.001` | `beat_start` (ambient) | ニャーコト / Nyaakoto | ……雲の上に、月か。 | — | …The moon, above the clouds. | 2.4 | Vista; camera soft_lookat to the moon and the eyewall. |
| 002 | `ch07.b10.kohagi.002` | `beat_start` (ambient) | 小萩 / Kohagi | 弓に、これ。風が見える。 | — | Tie this to your bow. You'll see the wind. | 3.0 | Tutorial: the tenugui wind strip on the upper limb (末弭). |
| 003 | `ch07.b10.nyaakoto.003` | `beat_start` (ambient) | ニャーコト / Nyaakoto | 風上へ、狙いをずらす。 | 風上(かざかみ) | Aim off, into the wind. | 2.3 | Tutorial: arrow drift. |
| 004 | `ch07.b10.kohagi.004` | `gust_warning:first` (ambient) | 小萩 / Kohagi | 綱を掴めば、飛ばされない。 | 綱(つな)、掴(つか)めば | Grab a cable and you won't be blown off. | 2.9 | Tutorial: cable brace. |
| 005 | `ch07.b10.kohagi.005` | `gust_warning` (ambient, rep) | 小萩 / Kohagi | 来る！　伏せて！ | — | Here it comes! Get down! | 1.8 | Cooldown 30 s; the audio riser is the primary telegraph. |
| 006 | `ch07.b10.shipvoice.006` | `volume_enter:vol_ridge_mid` (ambient) | 艦内通達 / Ship announcement | 外殻に異物。目録は排除してください。 | 異物(いぶつ)、排除(はいじょ) | Foreign object on the hull. / Inventory units, remove it. | 3.9 | — |
| 007 | `ch07.b10.kohagi.007` | `volume_enter:vol_ridge_fwd` (ambient) | 小萩 / Kohagi | 艦橋が見えた。前へ。 | — | There's the bridge. Keep going. | 2.3 | — |

#### ch07.b11: 艦橋へ迫れ / Push to the bridge

| # | Line id | Trigger (mode) | Speaker | Japanese | Readings | English subtitle | s | Notes |
|---|---|---|---|---|---|---|---|---|
| 001 | `ch07.b11.iota.001` | `beat_start` (radio) | イオタ / Iota | 右手の保安棚に、電撃放射器がございます。 | 保安棚(ほあんだな)、電撃放射器(でんげきほうしゃき) | The security rack on your / right holds a shock emitter. | 3.8 | — |
| 002 | `ch07.b11.iota.002` | `beat_start` (radio) | イオタ / Iota | 鍵板を、おかざしください。 | 鍵板(かぎいた) | Hold up the key-slate. | 2.6 | — |
| 003 | `ch07.b11.iota.003` | `pickup:16` (radio) | イオタ / Iota | 大盾の障壁も、電撃で落ちます。お近くで。 | 電撃(でんげき) | Even tower-shield fields fall to a shock. / Up close. | 3.9 | Tutorial: weapon 16 vs shield_enforcer. |
| 004 | `ch07.b11.enforcer.004` | `pattern:shield_advance` (ambient, rep) | 執行兵 / Enforcer | 前進。資産を保全します。 | — | Advancing. Protecting assets. | 2.5 | — |
| 005 | `ch07.b11.kohagi.005` | `wave_spawned:2` (ambient) | 小萩 / Kohagi | 盾、二。後ろに刃が一。 | 刃(やいば) | Two shields. A blade behind them. | 2.5 | — |
| 006 | `ch07.b11.enforcer.006` | `wave_spawned:3` (ambient) | 執行兵 / Enforcer | 艦橋へ後退。提督をお守りします。 | — | Fall back to the bridge. / Protect the admiral. | 3.2 | — |

#### ch07.b12: 提督コラテラ / Admiral Collatera

| # | Line id | Trigger (mode) | Speaker | Japanese | Readings | English subtitle | s | Notes |
|---|---|---|---|---|---|---|---|---|
| 001 | `ch07.b12.collatera.001` | cinematic subtitle | コラテラ / Collatera | ようこそ、債務者番号七〇三一。旗艦『複利号』へ。 | 債務者番号(さいむしゃばんごう)、七〇三一(ななまるさんいち)、複利号(ふくりごう) | Welcome aboard the Compound Interest, / debtor seven-zero-three-one. | 4.3 | 7031 follows the banker sample in bible §6.5; keep one number campaign-wide. |
| 002 | `ch07.b12.collatera.002` | cinematic subtitle | コラテラ / Collatera | 荷は下りました。ですが、利息は下りません。 | 下(お)りました、利息(りそく) | Your goods went down. / Interest never goes down. | 4.1 | — |
| 003 | `ch07.b12.collatera.003` | cinematic subtitle | コラテラ / Collatera | 従えば、生き残るための融資をやろう。 | 融資(ゆうし) | Submit, / and we may lend you enough to survive. | 3.5 | Catalog anchor, ch07 line 2. Text unchanged; speaker remapped banker → boss_collatera. Plain やろう breaks the alien keigo rule; staged as her one deliberate drop into condescension. B7 review. |
| 004 | `ch07.b12.nyaakoto.004` | cinematic subtitle | ニャーコト / Nyaakoto | 借りる必要はない。私たちは作れる。 | — | We need no loan. We can make what we need. | 3.3 | Catalog anchor, ch07 line 3 (speaker samurai); text unchanged. |
| 005 | `ch07.b12.collatera.005` | cinematic subtitle | コラテラ / Collatera | ……与信、否決。 | 与信(よしん)、否決(ひけつ) | …Credit denied. | 2.1 | — |

#### ch07.b13: 旗艦提督コラテラを倒せ / Defeat Admiral Collatera

| # | Line id | Trigger (mode) | Speaker | Japanese | Readings | English subtitle | s | Notes |
|---|---|---|---|---|---|---|---|---|
| 001 | `ch07.b13.collatera.001` | `boss_phase:1` (bark) | コラテラ / Collatera | 返済計画を、ご提示いたします。 | 返済(へんさい) | Presenting your repayment schedule. | 3.0 | — |
| 002 | `ch07.b13.collatera.002` | `pattern:twin_burst` (bark, rep) | コラテラ / Collatera | 利払いです。 | 利払(りばら)い | Interest due. | 1.4 | Audio telegraph for the 400 ms cyan laser-dot windup. Cooldown 8 s. |
| 003 | `ch07.b13.collatera.003` | `pattern:reload` (bark, rep) | コラテラ / Collatera | 残高、補充。 | 残高(ざんだか) | Replenishing balance. | 1.6 | Marks the 1.6 s shield-offline window. |
| 004 | `ch07.b13.kohagi.004` | `pattern:reload:first` (ambient) | 小萩 / Kohagi | 弾を込める間、障壁が消える！ | 込(こ)める | Her shield drops while she reloads! | 2.6 | Tutorial callout, first reload only. |
| 005 | `ch07.b13.collatera.005` | `shield_broken` (bark, rep) | コラテラ / Collatera | ……資本不足。 | 資本(しほん) | …Undercapitalized. | 1.8 | Cooldown 20 s. |
| 006 | `ch07.b13.collatera.006` | `boss_phase:2` (bark) | コラテラ / Collatera | 担保価値の下落を確認。 | 担保(たんぽ)、下落(げらく) | Collateral value is falling. | 2.2 | — |
| 007 | `ch07.b13.collatera.007` | `pattern:margin_call` (bark, rep) | コラテラ / Collatera | 追証を請求します。 | 追証(おいしょう) | Issuing a margin call. | 1.9 | Bible §8 voice telegraph. Precedes every 1500 ms amber ring. |
| 008 | `ch07.b13.kohagi.008` | `boss_phase:2` (ambient) | 小萩 / Kohagi | 床が傾く！　物が滑ってくる！ | 傾(かたむ)く | The floor's tilting! Things are sliding! | 2.9 | — |
| 009 | `ch07.b13.collatera.009` | `idle_in_cover_s:6` (bark, rep) | コラテラ / Collatera | その遮蔽物も、担保です。 | 遮蔽物(しゃへいぶつ) | That cover is collateral, too. | 2.5 | Anti-camping telegraph; the next margin call targets that cover. |
| 010 | `ch07.b13.collatera.010` | `boss_phase:3` (bark) | コラテラ / Collatera | 残る資産は、これのみ。 | 資産(しさん) | This is my last asset. | 2.3 | Draws the 清算刀 (Liquidation Blade). |
| 011 | `ch07.b13.collatera.011` | `pattern:fleche_lunge` (bark, rep) | コラテラ / Collatera | 清算。 | 清算(せいさん) | Liquidation. | 1.2 | Audio telegraph for the 800 ms lunge. |
| 012 | `ch07.b13.kohagi.012` | `player_died` (ambient, rep) | 小萩 / Kohagi | 立って。まだ終わってない。 | — | Get up. It isn't over. | 2.7 | Plays on retry from the phase checkpoint. |
| 013 | `ch07.b13.collatera.013` | `boss_defeated` (bark) | コラテラ / Collatera | ……不渡り、ですか。 | 不渡(ふわた)り | …Dishonored, then. | 2.4 | A dishonored bill. She is knocked down, not killed. |

#### ch07.b14: 信号灯と舵を守れ / Hold the beacon and the helm

| # | Line id | Trigger (mode) | Speaker | Japanese | Readings | English subtitle | s | Notes |
|---|---|---|---|---|---|---|---|---|
| 001 | `ch07.b14.kohagi.001` | `beat_start` (ambient) | 小萩 / Kohagi | 信号灯、点けた！　下から見えるはず！ | 信号灯(しんごうとう) | Beacon's lit! They should see it below! | 3.1 | — |
| 002 | `ch07.b14.iota.002` | `beat_start` (radio) | イオタ / Iota | 艦首を萱野原へ。舵を左へ三度、保ってください。 | 艦首(かんしゅ)、舵(かじ) | Bow toward Kaya Moor. / Hold the helm three degrees to port. | 4.4 | — |
| 003 | `ch07.b14.shipvoice.003` | `trim_event` (ambient, rep) | 艦内通達 / Ship announcement | 針路、逸脱。 | 針路(しんろ)、逸脱(いつだつ) | Off course. | 1.5 | Audio telegraph for each trim event. |
| 004 | `ch07.b14.kohagi.004` | `trim_event:first` (ambient) | 小萩 / Kohagi | 舵がずれてる！　戻して！ | — | The helm's drifting! Bring it back! | 2.6 | Tutorial: trim correction. |
| 005 | `ch07.b14.oyuki.005` | `progress_at:0.4` (radio) | お雪 / Oyuki | 灯りが見えます。村の者は、尾根へ逃がしております。 | 尾根(おね) | We see your light. / The villagers are moving to the ridge. | 4.8 | — |
| 006 | `ch07.b14.nyaakoto.006` | `progress_at:0.5` (ambient) | ニャーコト / Nyaakoto | ……空紋の提灯だ。 | 提灯(ちょうちん) | …Sora lanterns. | 2.1 | Through the window: the evacuation line of mon-painted lanterns (ch03). |
| 007 | `ch07.b14.iota.007` | `beat_complete` (radio) | イオタ / Iota | 降下角、確定。ここからは、重力のお仕事でございます。 | 降下角(こうかかく) | Descent angle locked. / From here, it is gravity's work. | 5.0 | — |

#### ch07.b15: 墜落 / The fall

| # | Line id | Trigger (mode) | Speaker | Japanese | Readings | English subtitle | s | Notes |
|---|---|---|---|---|---|---|---|---|
| 001 | `ch07.b15.nyaakoto.001` | cinematic subtitle | ニャーコト / Nyaakoto | 来い。まだ間に合う。 | — | Come. There is still time. | 2.2 | He offers Collatera his hand (katsujinken). |
| 002 | `ch07.b15.collatera.002` | cinematic subtitle | コラテラ / Collatera | ……負債は、艦と共に。 | 負債(ふさい) | …The liability goes down with the ship. | 3.0 | She refuses and stays. Her fate is left open. |
| 003 | `ch07.b15.kohagi.003` | cinematic subtitle | 小萩 / Kohagi | ニャーコト！　橇！ | — | Nyaakoto! The sled! | 1.5 | — |
| 004 | `ch07.b15.nyaakoto.004` | cinematic subtitle | ニャーコト / Nyaakoto | 掴まれ！ | — | Hold on! | 1.2 | — |

#### ch07.b16: 萱野原 / Kaya Moor

| # | Line id | Trigger (mode) | Speaker | Japanese | Readings | English subtitle | s | Notes |
|---|---|---|---|---|---|---|---|---|
| 001 | `ch07.b16.toranosuke.001` | `beat_start` (ambient) | 虎之介 / Toranosuke | ……生きていたな。 | — | …You are alive. | 2.1 | — |
| 002 | `ch07.b16.nyaakoto.002` | `beat_start` (ambient) | ニャーコト / Nyaakoto | 受け止めると言った男が、いたからな。 | — | Someone promised to catch whatever fell. | 3.5 | Answers b01 (he said he would catch what falls). |
| 003 | `ch07.b16.toranosuke.003` | `beat_start` (ambient) | 虎之介 / Toranosuke | 栗丸も連れてきた。……乗れ。 | 栗丸(くりまる) | I brought Kurimaru. …Mount up. | 3.1 | — |
| 004 | `ch07.b16.valamort.004` | `volume_enter:vol_riders` (blocking) | ヴァル・アモルト / Val Amort | 恒星信用院より、全債務者の皆様へ通達いたします。 | 恒星信用院(こうせいしんよういん)、通達(つうたつ) | The Stellar Credit House / addresses all debtors. | 4.5 | Broadcast through the wreck's hull horns and every door numeral in the valley. |
| 005 | `ch07.b16.valamort.005` | `volume_enter:vol_riders` (blocking) | ヴァル・アモルト / Val Amort | 全担保を回収する。 | 回収(かいしゅう) | All collateral is now called. | 2.2 | Bible §9 line, verbatim. Plain form reads as a written decree. |
| 006 | `ch07.b16.valamort.006` | `volume_enter:vol_riders` (blocking) | ヴァル・アモルト / Val Amort | 人もまた、担保でございます。 | — | People, too, are collateral. | 2.8 | Sets up the ch08 collateral cells. |
| 007 | `ch07.b16.oyuki.007` | `volume_enter:vol_riders` (radio) | お雪 / Oyuki | ……夜明けに、城へ参ります。 | 参(まい)ります | …At dawn, we go to the castle. | 3.1 | — |
| 008 | `ch07.b16.nyaakoto.008` | `volume_enter:vol_riders` (ambient) | ニャーコト / Nyaakoto | 先生を、取り戻す。 | — | We take Sensei back. | 2.0 | Final line of the chapter. |


### 3.4 HUD prompts and tips (L4 `ui_strings`; not voiced)

| String id | JA | EN | Beats |
|---|---|---|---|
| `ui.ch07.prompt.cut_junction` | 繋ぎ箱を切る | Cut the junction | b02 |
| `ui.ch07.prompt.leave_bale` | 俵から出る | Leave the bale | b04 |
| `ui.ch07.prompt.throw_tsubute` | 礫を投げる | Throw a stone | b04 |
| `ui.ch07.prompt.seal_cut` | 首輪を断つ | Cut the collar | b04 |
| `ui.ch07.prompt.douse_lamp` | 灯りを消す | Put out the lamp | b04 |
| `ui.ch07.prompt.key_slate` | 鍵板をかざす | Use the key-slate | b05, b11 |
| `ui.ch07.prompt.peel_tags` | 番号札を剥がす | Peel off the tags | b05 |
| `ui.ch07.prompt.crank` | 輪を回す | Turn the wheel | b07 |
| `ui.ch07.prompt.charge` | 長押しで溜め撃ち | Hold to charge | b08 |
| `ui.ch07.prompt.brace` | 綱を掴む | Brace on the cable | b10 |
| `ui.ch07.prompt.trim` | 舵を戻す | Correct the helm | b14 |
| `ui.ch07.tip.shield` | 障壁は四秒被弾なしで再充填 | Shields recharge after 4 s unhit | b06 |
| `ui.ch07.tip.charge` | 溜め撃ちは障壁を貫く | Charged shots pierce shields | b08 |
| `ui.ch07.tip.wind` | 矢は風に流される。風上を狙え | Arrows drift. Aim into the wind. | b10 |
| `ui.ch07.tip.lee` | 肋材や鰭の陰は風を防ぐ | Ribs and fins block the wind | b10 |
| `ui.ch07.tip.reload_window` | 装填中は障壁が消える | Her shield drops while reloading | b13 |
| `ui.ch07.registry.note` | 返還のみ記帳・札は切らず | Recorded as returned. No tally cut. | chapter end |

### 3.5 Line statistics

- Total lines: **137** (113 one-shot, 24 repeatable barks). One-shot VO runtime ≈ 6.3 min.
- Highest EN reading speed: 14.2 cps (`ch07.b11.iota.001`); limit 17 cps. Longest EN subtitle: 69 characters (2 lines of ≤ 42). Longest JA caption: 31 characters (2 lines of ≤ 16).
- Lines per beat: b01 14, b02 16, b03 7, b04 15, b05 5, b06 8, b07 9, b08 7, b09 6, b10 7, b11 6, b12 5, b13 13, b14 7, b15 4, b16 8.
- Lines per speaker: `scout` 34, `clerk` 22, `enforcer` 18, `samurai` 17, `boss_collatera` 15, `leader` 8, `rival` 4, `ship_voice` 4, `conscript` 3, `banker` 3, `league_ashigaru` 2, `farmer_young` 2, `auditor` 2, `gunsmith` 1, `fireworks` 1, `apothecary` 1.

The bible's §10 estimate for ch07 is 90 VO lines. This script has 137: 24 are short repeatable barks, and the rest carry the chapter's walk-and-talk, tutorials and stealth chatter. It stays inside the 60–150 per-chapter range. If VO budget (B6) forces a cut, the first candidates are the ambient chatter in b02 (Tamakichi, Okuzu, ashigaru, 3 lines) and b04 (the overheard appraisal and auditor lines). Cutting them loses tone, not information.

---

## 4. Historical and cultural accuracy notes

These are working notes for the historian, practitioner and native-speaker reviews (bible §20, open items 1–2). Items marked **flag** need sign-off.

### 4.1 Language, terms and units

- **野分 (のわき) for the typhoon.** It is the classical word: the 『源氏物語』 chapter "Nowaki" and 『枕草子』 「野分のまたの日こそ」.
  - Locals say 野分 or 大風, never 台風, which is a modern coinage (颱風/台風, late 19th to 20th century). **Flag** for confirmation of the exact date.
  - The aliens say 静穏域 ("calm region") for the eye. Nobody in 1623 has a word for it, so no local names it; Kohagi would only say the wind has stopped.
- **二百十日 is deliberately avoided.** The traditional typhoon day entered official calendars with the Jōkyō reform (貞享暦, 1685). **Flag.**
- **駄 (だ), one pack-horse load.** It is used for cargo because it is the period's own unit. Early-Edo post-station practice put a full load (本馬) at roughly 36–40 貫, about 135–150 kg. 430駄 is therefore about 60 t, plausible for a night of hauling. **Flag** the figure.
- **米俵.** A bale of about 4 斗 of rice (domain practice varied, 3斗5升–4斗) weighs about 60 kg and is roughly 70–80 cm long.
  - The stowaway bales are League-made hollow 大俵 on bamboo frames, about 1.2 m long. That is fiction, which is why the enforcer notices the weight.
  - The Met's *Farmers' Lives in the Twelve Months* shows period baling and storehouses.
- **Time.** Characters avoid clock time. Iota's numbers are alien precision; locals think in 刻 (unequal hours).
- **Alien jargon.** 与信, 追証, 不渡り, 融資, 資本不足 and 債務者番号 are modern financial Japanese, used **only** by aliens through the translation collar (bible §6.3). Locals never use them. 不渡り ("a dishonored bill") is apt: bills of exchange (為替手形) were already in use among merchants, but the word itself stays alien.
- **Honorifics.** Iota's 「鷲尾様」 is subtitled "Lord Washio"; 「先生」 is "Sensei" (bible §18).

### 4.2 The bastion: castle architecture

- **石垣:** 打込接ぎ (dressed-stone) masonry with 算木積み corners, as in bible §15.2 ch06.
- **雁木 (がんぎ):** straight stone stairs built against the inner face of a wall to reach the rampart. That is the main route up.
- **多聞櫓 (たもんやぐら):** a long single- or two-storey turret running along the top of a wall. By tradition the name comes from Matsunaga Hisahide's 多聞山城 in Nara, a fitting Yamato touch.
- **狭間 (さま):** loopholes in 土塀 and turrets. The League shoots through them: 鉄砲狭間 are square or triangular, 矢狭間 tall rectangles.
- **粗朶 (そだ) fascines:** brushwood bundles long used in river and moat works. The League's causeway is built of them.
- **The alien pylon** bites into the old 天守台 with seamless black-glass extrusions (bible §15.2). The contrast is the point, and the stones must read as intact period work around the wound.

### 4.3 Arms and swordsmanship in this chapter

- **The fictional school.** Nyaagyū Shinkage-ryū is fictional; no named Yagyū kata are reproduced (bible §3.1). In the Collatera duel Nyaakoto uses only the bible's general principles:
  - 合わせ (meeting cut) on her cuts and lunge;
  - 転 (まろばし), rolling around the lunge to the flank;
  - 水月, the distance read (her blade's reach is 210 cm, the lunge covers 5 m);
  - 残心 after she falls.
  - The duel's motion capture needs practitioner review before release, as all kenjutsu motion does.
- **納刀 (sheathing)** is animated before the crank (b07) and the helm (b14). It is the same explicit animation needed later for mutō-dori (bible §4.1).
- **Katsujinken, twice.** Nyaakoto knocks Collatera down, does not kill her, and offers his hand when the ship falls. This continues the arc toward the ch08 capture (bible §1.3).
- **峰打ち + seal-cut** is not needed on the collared loaders in b04, who are not fighting: the collar is cut from behind. They still use `nonlethal_types` and never count as kills.
- **Yumi in wind.**
  - The arrow sits on the right of the bow; the draw is 650 ms; the bow rotates (弓返り) after release (bible §4.2).
  - Aiming off into the wind is natural archer's practice. The game's drift values are exaggerated for readability.
  - The tenugui strip tied at the 末弭 (upper tip) is **a game device, not a period practice**. Archers read wind from flags, grass and trees. **Flag.**
- **Matchlocks in rain.** Period matchlocks misfire in rain even with 雨火縄 (bible §4.4), which is why Otane's line credits Tetsugorō's coil breeches (weapon 5). The League 鉄砲 still load with 早合 paper cartridges.
- **Alien arms** (Repeater 9, Pulse Carbine 11, Plasma Matchlock 14, Shock Emitter 16, Collatera's pistols and blade) are fiction and carry no period claim. The Repeater is League-built at the Silk Foundry: bronze, iron and timber with the mon on its receiver, never cyan.

### 4.4 Dress and armor

- **Nyaakoto (stowaway kit):**
  - The 紺糸威 dō with vermillion-lacquered plates (mon on the dō), plus 籠手, 佩楯 and 臑当.
  - For the bale he leaves his kabuto and sode with the League and wears a 鉢金 (iron-plated headband) carrying the mon. It is a period-plausible light head guard, and it continues the existing prototype's headband mon placement.
  - **Flag** the sode's absence against the key art.
- **Kohagi:** indigo peddler's clothes with 手甲 and a hidden short blade. Never the theatrical black suit (bible §4.6, §19).
- **League 鉄砲 and ashigaru:** 蓑 and 菅笠 in the storm, 胴乱 cartridge pouches. The mon-painted 陣笠 and 旗指物 debut in ch08 (bible §17), and the banners are furled tonight (b02 line).
- **Toranosuke:** black-lacquer armor with scarlet lacing under a 蓑. His grey Credit House haori is rolled and tied behind Arashi's saddle; he burns it in ch08 (bible §6.1).
- **Oyuki:** 小袖 with tasuki, indoors at the council.
- **Iota:** a pale lavender-grey suit a size too large.
- **Collatera:** a black naval-cut coat with cyan piping. Alien, and not a period claim.

### 4.5 Horses and tack (b16)

- **Horses:** native horses about 130 cm at the withers, unshod, wearing straw 馬沓 for the wet moor (bible §4.5).
  - Kurimaru is a chestnut mare; Arashi a black-bay stallion; the rest are bay and chestnut.
  - They spook at the hissing wreck (fear animation).
- **Riders:** in 蓑 over armor, with the full kura, abumi and cloth tazuna set.
  - The SORA mon is on the League riders' abumi front plates.
  - Arashi's abumi carry the **Washio house mon**, to be designed. It must resemble neither the SORA mon nor the alien ledger sigil. **Flag** for art.
- **No torches:** they would not survive the wind; lightning lights the scene.
- **Review:** the tack source is still stylized ([tack reference](../historical-horse-tack-art-reference.md)), and the equine gait needs its own review.

### 4.6 Objects in the hold and vault

- **Period goods:** 米俵; 長持 (lacquered chests carried on a pole); 具足櫃 (armor chests); swords on 刀掛け; 屏風; tea caddies in 仕覆 bags; silk 反物; andon; a village temple bell.
  - A small bell of about 1.2 m and 400 kg is plausible for a village temple.
  - No 招き猫 anywhere (bible §19).
- **名札掛け (the dojo name board):** the custom of hanging pupils' wooden name plaques is well known in later dojo practice. Its use in 1623 is **not established**. **Flag**; it is shared with ch01 and ch08.
- **Alien tags:** they carry the Credit House's ledger sigil (a closed ring of tally notches) and numerals in cyan. They are pasted **over** the house mon on the chests, never replacing or imitating it.

### 4.7 The SORA kamon in this chapter

The source is the exact SVG (`Content/SourceArt/UI/sora_logo_NOtext2.svg`, SHA-256 `d66413a7…0910`), imported from its two original paths and never redrawn. Aliens never display it.

| Where | Treatment | Beat |
|---|---|---|
| Chapter title card | Vermillion 朱印 seal beside the brush title 「第七章 異星旗艦への突撃」 | b01 |
| Nyaakoto's dō and 鉢金 | Existing runtime-skin dō placement; headband plate (existing prototype placement) | all |
| Repeater receiver | Branded on both receiver cheeks, like the Arc Carbine | b01 on |
| Stowaway bales | Hasty chalk mon on the straw: the loaders' recognition sign | b03 |
| League mark collectible | Scratched inside a bale by a collared loader | b04 |
| Seized chests | Gold maki-e house mon, half-covered by an alien tag | b04, b05 |
| Dojo name board | Mon on the header (bible §17); Kohagi's chalk mon added for return | b05, b07 |
| Evacuation line | Warm points of mon-painted lanterns (from ch03) seen through the bridge window | b14 |
| League riders | Abumi front plates | b16 |
| Registry page | 押収品の返還 430駄 with the vermillion registry seal; no split-tally icon (nothing issued) | chapter end |
| UI | Objective marker, save indicator (slowly turning mon) | all |

The banners are deliberately furled tonight (the b02 line), so the silk nobori does not appear in ch07. It returns in ch08.

### 4.8 Sources

- Yagyū Munenori, 『兵法家伝書』 (1632), sections 殺人刀 and 活人剣. Annotated edition: 渡辺一郎校注『兵法家伝書 付・新陰流兵法目録事』 (岩波文庫, 1985). Used for the katsujinken framing only.
- The Met, [Edo katana, 638804](https://www.metmuseum.org/art/collection/search/638804) and [foot yari, 27609](https://www.metmuseum.org/art/collection/search/27609), via [historical-arms.md](../historical-arms.md).
- All Japan Kyudo Federation, [射法八節](https://www.kyudo.jp/howto/syaho.html) (shooting sequence), via historical-arms.md.
- The Met, [kura 2000.405](https://www.metmuseum.org/art/collection/search/26572), [abumi 2008.120.1–2](https://www.metmuseum.org/art/collection/search/35376) (family mon at the front) and [hato-mune abumi 2016.205](https://www.metmuseum.org/art/collection/search/712927), via the [tack reference](../historical-horse-tack-art-reference.md).
- The Met, [*Farmers' Lives in the Twelve Months*](https://www.metmuseum.org/art/collection/search/44674): rice baling and storehouses, as cited by the cargo-stack source art.
- 『源氏物語』 (第二十八帖「野分」) and 『枕草子』 for the classical use of 野分.
- Castle terms (雁木, 多聞櫓, 狭間, 打込接ぎ, 算木積み) follow standard Japanese castle-architecture usage; the historian should confirm per element.

### 4.9 Review flags (summary)

1. The 台風 dating and the avoidance of 二百十日 (§4.1).
2. The 駄 load weight and the 430駄 figure (§4.1).
3. 名札掛け in a 1623 dojo (§4.6).
4. The tenugui wind strip on the yumi as a game device (§4.3).
5. Nyaakoto's stowaway kit without sode and kabuto (§4.4).
6. The Washio house mon design (§4.5).
7. The register of catalog line 2 (plain 「やろう」) against the alien keigo rule, and Val Amort's plain-form decree 「全担保を回収する。」 (§6.1).
8. Proposed light moment H2, Iota's recount in b09. Tone sign-off.

---

## 5. Art and audio asset list

**Status key:**

- **Existing:** in the repository today; the path is given. "Placeholder" means a primitive or a study that does not yet meet the photoreal gate.
- **Needed:** to be built, from original art or free assets whose licenses allow it (user directive 17). Shared assets name the chapters that reuse them.

Every entry must pass the [photoreal acceptance](../art-direction/photoreal-acceptance.md) gates before it ships (bible §15): a packaged A/B capture, a recorded license, and a measured frame cost on both platforms.

### 5.1 Environment kits

| Asset | Use | Status | Owner / notes |
|---|---|---|---|
| Flagship hard-surface kit: graphite hull plates with engraved ledger lines, black glass with thin-film tint, bulkheads, grating, strip lights | b04–b15 | Needed | C3. Nanite on Windows, LODs on Mac |
| Cargo hold module: bay racks, 1.5 m crawl gaps, conveyor, lift well, gantry catwalk and ladders | b04 | Needed | C3 |
| Seized vault room | b05 | Needed | C3; reuses hold kit |
| Reckoning engine: glass abacus ring (hero), drum pit and cable drum, mezzanine, bead hoppers | b06, b07 | Needed | C3; ring is a hero asset (rotation, emissive beads) |
| Hangar: shuttle cradles, force-curtain mouth, gallery, launch rails | b08, b15 | Needed | C3 |
| Hull ridge exterior: dorsal spine, ribs, sensor fins, cable runs, sensor mast | b10 | Needed | C3 |
| Bridge amphitheatre: tiers, consoles (intact, damaged, destroyed), ledger pulpit, helm wheel, beacon console, ceiling emitter ring, window | b12–b14 | Needed | C3 |
| Flagship exterior hero mesh, intact and wrecked | b01 projection, b03, b15, b16 | Needed | C3/C9; hammerhead silhouette (bible §15.2) |
| Anchor bastion (Arena 3 storm variant): 石垣 with 算木積み corners, 雁木, 狭間塀, 多聞櫓 (two storeys, interior upper floor), 櫓台, fascine causeway | b02, b03 | Needed. Arena 3 exists only as a primitive blockout. Materials exist: `Content/Generated/Environment/MI_Nyaagyu_Stone`, `MI_Nyaagyu_Plaster`, `MI_Nyaagyu_Timber`, `MI_Nyaagyu_Kawara` | C2 (arena shell), C3 (campaign sublevel) |
| 土塀 fragment | b02 | Existing: `Content/Generated/Environment/Props/SM_Nyaagyu_EstateWall_4m` (source `Content/SourceArt/Environment/NyaagyuEstateWall`) | Charred/wet variant needed |
| Anchor pylon, tether, lift cradle | b02, b03, b07 view | Needed | C3 |
| Signal relay mast with 3 junction boxes (intact, cut states) | b02 | Needed | C3 |
| Hidden Valley council: 陣幕 with mon, lean-to, map table, washi projection screen | b01 | Needed (shared with ch02, ch08) | C3 |
| Kaya Moor: 芒 grass (cards and geometry, wind animation), furrow and debris decals | b15, b16 | Needed. The existing PolyHaven set (`Content/SourceArt/Environment/PolyHaven`: Fern02, TreeSmall02, PineSaplingSmall) has no susuki | C3; photoreal foliage per [photoreal-foliage.md](../photoreal-foliage.md) |
| Sky: storm front, cloud-ascent volume, eye stadium and cloud sea, rear eyewall | b02–b16 | Needed | C3/C8; Mac skybox fallback |
| PBR base materials: stone, wood, plaster, roof tile, metal | b02 | Existing (CC0): `Content/SourceArt/Environment/PolyHaven` (stone_floor, wood_planks_dirt, WhitePlaster02, GreyRoofTiles, rusty_metal_02) | Wet variants needed |

### 5.2 Props

| Asset | Use | Status | Notes |
|---|---|---|---|
| Rice-bale and crate stacks | b02 cover, b04 bays | Existing: `Content/SourceArt/Environment/NyaagyuCargoStack/SM_Nyaagyu_CargoStack.fbx`; imported `Content/Generated/Environment/Props/SM_Nyaagyu_CargoStack` | Visual only; its cube collision is arena cover. Needs wet and tagged variants |
| Single 米俵 and the hollow stowaway 大俵 (openable, hero) | b03, b04 | Needed | Chalk-mon decal variant |
| 長持 with gold maki-e mon, 具足櫃, 刀掛け with swords, 屏風 in alien film, tea caddies in 仕覆, silk 反物, andon | b04, b05 | Needed (shared with ch08 hall of heirlooms) | Heirloom set |
| Village temple bell (梵鐘, 1.2 m) on a gantry hook | b04 | Needed | Hero; strike animation and VFX |
| 名札掛け with plaques (hero) | b05 | Needed (shared with ch01, ch08) | Plaques in brush script; tag and chalk decals |
| Alien tags, notices and labels (ledger sigil, cyan numerals) | b04, b05 | Needed | Decal atlas; the sigil must not resemble the mon |
| Alien consoles, manifest desk, security rack | b04, b11, b13 | Partly existing: derive from `Content/SourceArt/Environment/Original/SM_Alien_DebtKiosk.fbx` and `Content/SourceArt/Environment/StreetDebtTerminal/SM_Alien_StreetDebtTerminal.fbx` | Same design language |
| Hand-carts (loaders'), inspection lamps on stands | b04 | Needed | |
| Fuel canisters (intact, burst) | b08 | Needed | |
| Cargo sled on rails | b08, b15 | Needed | Hero for the cinematic |
| Iota's key-slate | b05, b11 | Needed (shared with ch06) | Cyan light is allowed: it is an alien object |
| Indigo tenugui strip (cloth sim) on the yumi's upper tip | b10 | Needed | Diegetic wind indicator |
| 鉢金 with the mon | all | Needed | Mon from the SVG paths |
| Mon-painted 提灯 (far-LOD evacuation line) | b14 | Needed (shared with ch03); lantern post exists: `Content/Generated/Environment/Props/SM_Edo_LanternPost` | Emissive cards at distance |
| Registry page with 押収品の返還 entry | chapter end | Needed (L4 registry screen) | |

### 5.3 Characters

| Character | Use | Status | Notes |
|---|---|---|---|
| Nyaakoto, stowaway kit (no kabuto or sode, 鉢金) | all | Existing prototype: `Content/SourceArt/SK_NyaagyuSamurai.fbx`, runtime skin `Content/SourceArt/Characters/Hero/Nyaakoto_RuntimeSkin.blend`. The photoreal target is pending (B5) | Kit variant needed |
| First-person paws: katana, yumi | all | Existing studies: `Content/SourceArt/Characters/NyaakotoFirstPersonPaws/` | Firearm, crank, cable-brace and helm grips needed (C7) |
| Kohagi | b01–b16 | Needed (shared) | Companion; storm-wet cloth |
| Oyuki, Iota, Tetsugorō, Otane, Tamakichi, Okuzu | b01, b02, radio | Needed (shared) | Iota and Oyuki are mostly heard over the radio here |
| Toranosuke, with 蓑 | b01, b16 | Needed (shared) | |
| League 鉄砲 ×4, ashigaru, riders ×20 | b02, b16 | Needed (shared with ch08) | 蓑 and 菅笠 variants |
| Collared loaders (債縛衆) | b03, b04 | Needed (shared with ch03, ch05) | Glowing collar, dignified staging |
| Admiral Collatera | b12–b15 | Needed (hero boss) | Hairless (no groom), naval coat, twin pistols, 清算刀 |
| Enforcers: rifle (shielded variant), shield enforcer, grenadier, marksman, blade retainer, auditor | b02–b14 | Base prototype exists: `Content/SourceArt/SK_AlienBanker.fbx` (20-bone rig, idle and walk in `Content/Generated/Animations/`) | Enemy kits needed (C6); hairless saves fur cost |
| Inventory drones (目録) | b04–b14 | Needed (shared) | |
| Horses: Kurimaru, Arashi, rider horses | b16 | Existing static study: `Content/SourceArt/Horses/Nyaagyu/SM_Nyaagyu_HorseAndTack.fbx` (stylized, not rigged for deformation) | Rigged photoreal horses needed (B5), plus the equine review |

### 5.4 Weapons

| Weapon | Use | Status | Notes |
|---|---|---|---|
| 9 連発銃 Repeater | from b01 | Placeholder primitive: `Content/SourceArt/SM_Weapon_09.fbx` | C5 hard-surface, League-built (bronze, iron, timber), mon on the receiver |
| 11 パルス・カービン Pulse Carbine | from b06 | Placeholder: `SM_Weapon_11.fbx` | Alien levy carbine; ledger sigil |
| 14 プラズマ火縄銃 Plasma Matchlock | from b08 | Placeholder: `SM_Weapon_14.fbx`, imported `Content/Generated/Meshes/SM_Weapon_14` | Long matchlock silhouette with a charge coil; charge glow states |
| 16 電撃放射器 Shock Emitter | from b11 | Placeholder: `SM_Weapon_16.fbx`, imported `Content/Generated/Meshes/SM_Weapon_16` | |
| 13 幻影短機関銃 Phantom SMG | auto-grant | Placeholder: `SM_Weapon_13.fbx` | |
| 0 Katana and saya | all | Existing: `Content/SourceArt/SM_Nyaagyu_HeroKatana.fbx`, `SM_Nyaagyu_HeroSaya.fbx` (review pending) | 納刀 needed |
| 18 Yumi, red-fletched arrows | all | Existing study: `Content/SourceArt/Weapons/NyaagyuYumi/SM_Nyaagyu_Yumi_Study.fbx`; material `Content/Generated/Meshes/M_Hero_BambooArrowShaft` | Tenugui attach point at the 末弭 |
| 5 Coil matchlock (League allies) | b02 | Placeholder: `SM_Weapon_05.fbx`; jade coil material exists (`Content/Generated/Meshes/M_CoilJade`) | Shared with ch04 |
| Collatera's twin pistols and 清算刀 | b12–b15 | Needed | |
| Levy carbine, marksman rifle, tower shield with field, grenadier drum pack | enemies | Needed | L2/C5 |

### 5.5 Animations

| Set | Clips | Status |
|---|---|---|
| Nyaakoto, first person | Leave bale; peel tags; key-slate hold; seal-cut from behind; rear takedown; tsubute throw; put out lamp; 納刀 then crank (loop, strain, gear-slip recoil); brace-and-shuffle on cable; crouch in lee; gust stagger; Plasma charge hold and release; Shock Emitter fire and reload; Repeater and Pulse Carbine reloads; helm trim; parry/awase vs sabre; 転 flank step | Needed (C7) |
| Nyaakoto, cinematic | Council; bale entry; offer hand; sled ride; mount Kurimaru | Needed (C9) |
| Kohagi | Crouch-follow companion; signal gestures; pawl set; slow crank; beacon ignition; tie the tenugui strip; resupply hand-off; drag to sled | Needed |
| Collatera | Twin-pistol burst; sidestep dash; cell-swap reload (shield-off tell); helm command; sabre draw; two-cut combination; lunge; off-hand snap shot; stagger; knockdown; refuse hand | Needed (L3/C7) |
| Enforcers and others | Shield raise, hit ripple, break stagger; tower field down and guard lowered; retreat; search; auditor alarm; grenadier throw; marksman glint aim; blade retainer 420 ms warning; loaders' cart push, freed-hide; drones hover, jink in gusts, net drop | Needed (L2/C7). Alien idle and walk exist: `Content/Generated/Animations/A_AlienBanker_Idle`, `A_AlienBanker_Walk` |
| League allies | Coil-matchlock fire, 早合 reload, downed, revive; Otane kusarigama | Needed (shared) |
| Horses | Walk and trot on wet ground; spook; mount (scripted) | Needed; equine animator review |

### 5.6 Visual effects (C8, Niagara; respect flash reduction)

| Effect | Beats | Notes |
|---|---|---|
| Wind-driven horizontal rain, sheet runoff, puddle rings, eave and wall drips | b02, b14–b16 | Mac: particle cap plus screen-space rain |
| Lightning on a fixed schedule (flash-reduction clamp); in-cloud lightning below | b02, b10, b14 | Never full-screen white at reduced flash |
| Cloud ascent volume; eye stadium; moonlit cloud sea; spindrift in gusts | b03, b10 | Mac: skybox and cards |
| Alien floodlights through rain; tether glow; relay sparks and die-off | b02 | |
| Shield shimmer (silver-violet thin film), hit ripple, break shatter into ledger numerals | b06 on | Never cyan |
| Cyan laser dots (locked aim); amber rings, edge flash and floor line (animated edge-decal pulse) | b13 | Accessible palette (L4) |
| Plasma charge glow; Shock Emitter arcs; Repeater and Pulse Carbine muzzle | b08, b11 on | |
| Coil-matchlock jade spark and smoke (allies) | b02 | League glow is jade or warm, never cyan |
| Abacus ring light bands and bead trails; drum-pit steam | b06, b07 | Soft, never beam-like |
| Fuel canister burst | b08 | |
| Bell strike ring (subtle air shimmer) | b04 | |
| Hull ledger lines going dark in sequence; crash dust in rain; sled sparks and grass spray | b15 | |
| Distant mon-lantern line (emissive points) | b14 | |
| Drone seizure net | b10, b13 | |

### 5.7 Sound effects (L5; CC0 or original synthesis only)

| Group | Sounds |
|---|---|
| Storm | Typhoon wind beds (3 intensities), rain on stone, timber, straw and graphite, thunder (distance-delayed), gust riser (the 1 s telegraph), tenugui flutter |
| Ship | Hull groan with an 800 ms creak (stealth telegraph), lift winch, tether hum, conveyor, gantry grating steps, hangar force-curtain flicker, ship-voice chime, trim alarm, beacon ignition, list creaks, crash sequence |
| Hold | Straw creak, cart wheels, the bell strike and long decay (lure), inspection-lamp snuff, loaders' whispers, collar cut |
| Engine | Abacus bead clicks, ring rotation, drum rumble, override wheel ratchet, pawl clank at 25/50/75%, gear-slip clank |
| Weapons | Repeater (mechanical), Pulse Carbine, Plasma charge whine, full-charge click and shot, Shock Emitter crackle, coil matchlock, arrow release in wind, canister burst |
| Shields | Hum, hit, regeneration start (4 s), break |
| Telegraphs | Marksman glint tone (900 ms), laser-dot lock tone (400 ms), margin-call riser (1500 ms), prop scrape (700 ms), lunge whoosh, cell-eject hiss (reload window) |
| Aliens | Translation-collar DSP chain (band-limited formant chorus, no pitch shift); drone chirps and scan |
| Horses | Hooves on wet grass, snorts, spook, tack jingle |
| Sword | Sabre draw, cuts, parry impact, 納刀 click |

### 5.8 Music cues (L5 stem states)

| State id | Beats | Direction |
|---|---|---|
| `mus_ch07_council` | b01 | Low taiko pulse under a solo shakuhachi; wind outside |
| `mus_ch07_bastion_storm` | b02 | Taiko ensemble and 鼓 with storm; the alien layer is cold glass drones |
| `mus_ch07_ascent` | b03 | Near silence: winch, straw, breath. At the cloud break, one sustained 篠笛 note |
| `mus_ch07_hold_stealth` | b04 | Sparse biwa plucks over sub-bass hum; ducks under hull booms |
| `mus_ch07_vault_quiet` | b05 | Solo koto or biwa motif of the dojo (ch01 theme), fragile |
| `mus_ch07_engine` / `_crank` | b06 / b07 | Mechanical ostinato in 5 built from abacus clicks and taiko; the crank variant rises with progress |
| `mus_ch07_hangar` | b08 | Full percussion plus alien pulses |
| `mus_ch07_radio` | b09 | Low bed, ducked |
| `mus_ch07_ridge` | b10 | Wind as instrument; shakuhachi over the cloud sea, drums on drone waves |
| `mus_ch07_approach` | b11 | Tension build |
| `mus_ch07_collatera_intro` / `mus_boss_collatera` (P1/P2/P3 stems) | b12 / b13 | P1 cold and precise; P2 adds tilt and brass-like synth hits; P3 strips to taiko and a single 鼓 for the duel |
| `mus_ch07_helm` | b14 | Driving, with the League motif surfacing at 50% |
| `mus_ch07_fall` | b15 | Rising strings-like synth into silence at impact |
| `mus_ch07_aftermath` | b16 | Rain; Val Amort's cold motif under the broadcast |

### 5.9 UI (L4)

- Chapter title card with the vermillion mon seal.
- Enemy shield bar; Plasma charge meter; optional wind arrow; trim alarm indicator.
- Registry page variant with a "recorded only" state (no split-tally icon).
- The HUD prompts in §3.4.

---

## 6. Hand-offs and open items

### 6.1 Catalog mapping (schema 3 → this chapter)

- **Sites:** 0 地上の通信塔 → b02; 1 収奪の動力炉 → b07; 2 脱出の信号機 → b14. This is the catalog's order, so its `requires_sites` chain ([], [0], [1]) stands and **no renumbering is needed** for ch07.
- **Other fields:** `map: 3` stands. The catalog `kills: 16` and `requires_kills` are replaced by the beat waves.
- **Anchor lines:**
  - Line 1 (scout) → `ch07.b01.kohagi.001`.
  - Line 2 → `ch07.b12.collatera.003`, with a **speaker remap `banker` → `boss_collatera`**. This remap is not listed in bible §20; L1 should record it as it did for ch05. It follows bible §13 ("Collatera offers a survival loan") and keeps Val Amort's voice for the b16 decree. The line's plain 「やろう」 breaks the alien keigo rule. It is staged as Collatera's one condescending drop, and a keigo alternative is offered for B7: 「従っていただければ、生存のための融資をご用意いたします。」
  - Line 3 (samurai) → `ch07.b12.nyaakoto.004`.
  - Text is unchanged for all three.
- **Debtor number:** 7031 (from bible §6.5) is used for Nyaakoto in b12 and in collectible `ch07.c02`. Other chapters should use the same number.

### 6.2 Proposed schema extensions (L1/L2 to ratify or drop)

Keys prefixed `x_` in §7 are outside the bible §12 schema.

| Key | Where | Purpose |
|---|---|---|
| `x_auto_grant_if_missing` | b01 | Bible §11 auto-grant of 13 |
| `x_objective` | b02 | Interact points (relay junctions) that drive `progress_at` in a `combat_wave` |
| `x_staging` | b02 | Safe pre-combat area with a supply point |
| `x_environment`, `x_chapter_systems.ridge_wind` | b02, b08, b10, b14 | Weather, wind, list angle |
| `x_exit` | b02, b04, b10, b11 | Exit volume gating the next beat |
| `waves[].id` in `stealth_zone` | b04 | Target of `on_detected: reinforce:<wave>` |
| `x_lure_objects`, `x_ambient_noise_mask`, `x_body_discovery`, noise kind `x_metal_grate` | b04 | Stealth aids |
| `x_entry`, `x_story_flag` | b05 | Key-slate lock; `nafudakake_marked` for ch08 |
| `x_variant: shielded`, `x_chapter_systems.shield_profiles` | b06–b14 | Enemy shield variant |
| `x_guaranteed_drop`, `x_pickup` | b06, b08, b11 | Deterministic weapon unlock pickups |
| `x_override` | b07 | Reverse torque, ratchet locks, gear slip, co-op rules |
| `x_registry_mode: record_only` | b07 | Registry entry without a tally (charter article 1) |
| `x_hazards` | b08 | Explosive canisters |
| `x_mechanics_proposed` | b08, b10 | New flags `charged_shot`, `wind_brace` for the §12.1 list |
| `x_complete_also` | b09 | Dialogue beat also waits for a volume |
| `x_fall_respawn` | b10 | Respawn at the last brace anchor |
| `x_boss_stats`, `x_pattern_tables`, `x_fate` | b13 | For L3's `bosses.json` |
| `x_allies`, `x_trim_events`, `x_fail_timer`, `x_fail_extra` | b14 | Hold extras; second fail condition |
| `x_places_spanned`, `x_on_complete` | b15, b16 | Cinematic spans; chapter-end hook |
| `x_companion`, `ui_prompts` | chapter | Kohagi's companion rules; L4 strings (`ui_prompts` is the campaign-wide name, bible §12.5) |

**Proposed dialogue and trigger events.** These are not in the §12.1 list:

- `wave_spawned[:n]`, `enemy_retreat`
- `pattern:<id>` for regular enemies (marksman lock, grenadier throw), and `pattern:<id>:first`
- `npc_downed:teppo_*` (wildcard)
- `seal_cut:<guard>`, `auditor_alarm`, `lure_triggered:<id>`, `poi_found:<id>`
- `shield_hit_first`, `shield_broken`, `pickup:<weapon id>`, `crank_released`
- `gust_warning[:first]`, `trim_event[:first]`
- `idle_in_cover_s:<n>`, `boss_defeated`, `x_timer_expired`

`cinematic` in the line tables marks a cinematic subtitle, not an event.

**Other proposals:**

- **Places** for bible §14: `pl_bridge_approach` (艦橋前回廊, かんきょうまえかいろう, a sub-area of the bridge sublevel) and `pl_kayanohara` (萱野原, かやのはら, Kaya Moor, a new small exterior).
- **Speakers** for L1 `dialogue_speakers`: `enforcer` (執行兵 / Enforcer; also the marksman voice), `auditor` (監査官 / Auditor), `league_ashigaru` (一揆の足軽 / League ashigaru), `conscript` (債縛の人足 / Collared loader), `ship_voice` (艦内通達 / Ship announcement). The ids `leader`, `clerk`, `rival`, `gunsmith`, `farmer_young`, `fireworks`, `apothecary` and `boss_collatera` come from bible §6.
- **Collectibles** follow bible §12.5 (resolved in review): `collectible_id` equals the `chNN.cMM` id (`ch07.c01`–`c06`) and `mask_bit` is chapter-local 0–5. If L1 keeps one flat 48-bit mask, the global bit is (chapter − 1) × 6 + `mask_bit`, which gives 36–41 here. The former descriptive slugs are kept in §2.5 as art-handoff names only.

### 6.3 Open items

1. Native Japanese review of every line, reading and register (B7). This especially covers Iota's manual keigo, Otane's and Tamakichi's Kamigata, and the conscripts' Yamato speech.
2. The historian and practitioner flags in §4.9.
3. Telemetry to confirm the 50 min target, especially b13 (8 min with retries) and b04 (stealth variance).
4. A VO budget decision (B6) against 137 lines (§3.5).
5. Tone sign-off for H2.
6. The English ship name "Compound Interest" for 『複利号』 (Fukuri-gō): the bible gives no English name.

---

## 7. Machine-readable beat data (YAML)

The block below is generated from the same data as the tables above. It parses as YAML (checked with Ruby Psych). Field names follow bible §12; `x_` keys are the proposals in §6.2. `lines` carries every dialogue line with `ja`, `en`, `speaker`, `register`, `duration_s` and `readings`, so L1 can build `chapter_07.json` and the dialogue tables without re-typing text.

```yaml
chapter: ch07_flagship
title_ja: "異星旗艦への突撃"
title_en: "Alien Flagship Assault"
map: 3
target_s: 3000
season_time: early_autumn_typhoon_night
loadout_at_start:
  cumulative_mask: [0, 18, 19, 4, 7, 2, 5, 20, 8, 1, 3, 10]
  conditional: {"13": "held if picked up in ch06.b07, else auto-granted at ch07.b01"}
x_companion:
  npc: kohagi
  from: ch07.b03
  to: ch07.b15
  detectable_in_stealth: false
  downable: false
  resupply: {weapon_9_mags: 2, arrows: 12, per: checkpoint}
x_chapter_systems:
  shield_profiles:
    shielded:
      applies_to: [enforcer_rifle]
      shield_hp: 60
      regen_delay_s: 4.0
      regen_per_s: 30
      break_stagger_s: 0.8
      visual: thin_film_silver_violet
      damage_mult: {default: 1.0, melee: 1.25, w11: 1.5, w16: 2.5}
      pierce: [w14_charged]
    tower_field:
      applies_to: [shield_enforcer]
      frontal_arc_deg: 120
      blocks: [hitscan, arrows, melee]
      w16_effect: field_down_4s_and_guard_lowered
      w14_charged_effect: field_down_4s
      counter: "flank, or shock then strike"
  charged_shot:
    weapon: 14
    charge_ms: 800
    hold_max_ms: 3000
    move_speed_mult_while_charging: 0.6
    damage: 95
    effect: pierce_shield
    uncharged: "normal shot, shields absorb"
    telegraph_to_enemies: none
    audio: "rising coil whine; click at full charge"
  ridge_wind:
    base_mps: 8
    base_from: starboard
    gust_mps: 18
    gust_schedule_s: [11, 9, 14, 10, 12]
    gust_warn_ms: 1000
    gust_hold_s: 2.5
    push_cm_s: {standing: 120, crouched: 60, braced: 0, in_lee: 0}
    lee_volumes: "behind ribs and fins"
    ledge_guard: true
    projectile_drift: {affects: [w18_arrows, w7_shells, enemy_shells], lateral_accel_mps2_per_mps: 0.35}
    hitscan_affected: false
    drone_aim_disruption_s: 0.6
    indicator: "tenugui strip on the yumi upper limb; optional HUD arrow (L4)"
  hull_boom: {where: [pl_cargo_hold], schedule_s: [12, 12, 12], duration_s: 2.0, warn_ms: 800, noise_mult: 0.3}
  bell_lure: {id: bell_bonsho, radius_cm: 2500, uses: 1, hold_s: 12}
beats:
  - id: ch07.b01
    type: cinematic
    place: pl_kakuredani
    title_ja: "軍議"
    title_en: "The war council"
    target_s: 120
    checkpoint: true
    unlocks: {weapons: [9], mechanics: []}
    sequence: "/Game/Cinematics/Ch07/LS_Ch07_B01_WarCouncil"
    duration_s: 120
    skippable: true
    fallback: camera_blend
    end_state: {player_transform: ps_ch07_b02_start, equipped: {firearm: 9}}
    subtitles:
      - ch07.b01.kohagi.001
      - ch07.b01.oyuki.002
      - ch07.b01.iota.003
      - ch07.b01.nyaakoto.004
      - ch07.b01.oyuki.005
      - ch07.b01.oyuki.006
      - ch07.b01.iota.007
      - ch07.b01.kohagi.008
      - ch07.b01.oyuki.009
      - ch07.b01.iota.010
      - ch07.b01.toranosuke.011
      - ch07.b01.toranosuke.012
      - ch07.b01.nyaakoto.013
      - ch07.b01.tetsugoro.014
    music: mus_ch07_council
    x_auto_grant_if_missing: [13]
  - id: ch07.b02
    type: combat_wave
    place: pl_anchor_bastion
    title_ja: "錨台の通信塔を断て"
    title_en: "Cut the anchor bastion's relay"
    target_s: 240
    checkpoint: true
    site: 0
    bounds: vol_bastion_bounds
    waves:
      - enemies:
          - {type: enforcer_rifle, count: 4, spawn: sp_bastion_gate, patrol: pt_gangi_top}
          - {type: marksman, count: 1, spawn: sp_tamon_upper}
        trigger: "volume_enter:vol_bastion_steps"
      - enemies:
          - {type: enforcer_rifle, count: 3, spawn: sp_lift_platform}
          - {type: marksman, count: 1, spawn: sp_pylon_gantry}
        trigger: "progress_at:0.34"
      - enemies:
          - {type: enforcer_rifle, count: 3, spawn: sp_bastion_north}
        trigger: "progress_at:0.67"
    complete: all_waves_cleared
    max_alive: 6
    allies:
      - {npc: otane, role: flank_melee, downable: true}
      - {npc: teppo_1, role: suppress_ranged, downable: true}
      - {npc: teppo_2, role: suppress_ranged, downable: true}
      - {npc: teppo_3, role: suppress_ranged, downable: true}
      - {npc: teppo_4, role: suppress_ranged, downable: true}
    nonlethal_types: [bound_conscript]
    target_kind: enemy
    dialogue:
      - "on": "volume_enter:vol_bastion_staging"
        lines: [ch07.b02.tamakichi.001, ch07.b02.okuzu.002, ch07.b02.ashigaru.003]
        mode: ambient
      - {"on": "volume_enter:vol_bastion_steps", lines: [ch07.b02.otane.004, ch07.b02.kohagi.005], mode: ambient}
      - {"on": "volume_enter:vol_relay_foot", lines: [ch07.b02.kohagi.006], mode: ambient}
      - {"on": "progress_at:0.34", lines: [ch07.b02.kohagi.007, ch07.b02.otane.008], mode: ambient}
      - {"on": "progress_at:0.67", lines: [ch07.b02.kohagi.009], mode: ambient}
      - {"on": "site_restored:0", lines: [ch07.b02.nyaakoto.010], mode: ambient}
      - {"on": beat_complete, lines: [ch07.b02.iota.011], mode: radio}
      - {"on": "alert_state:alert", lines: [ch07.b02.enforcer.012], mode: ambient}
      - {"on": wave_spawned, lines: [ch07.b02.enforcer.013], mode: ambient}
      - {"on": enemy_retreat, lines: [ch07.b02.enforcer.014], mode: ambient}
      - {"on": "pattern:marksman_lock", lines: [ch07.b02.marksman.015], mode: ambient}
      - {"on": "npc_downed:teppo_*", lines: [ch07.b02.ashigaru.016], mode: ambient}
    music: mus_ch07_bastion_storm
    x_objective:
      kind: interact_points
      points: [relay_j1, relay_j2, relay_j3]
      per_point_s: 2.0
      interruptible: true
      progress_persists: true
      complete_requires: [all_points, all_waves_cleared]
    x_staging: {volume: vol_bastion_staging, supply_point: sup_ch07_bastion, safe: true}
    x_environment:
      weather: typhoon_front
      visibility_m: 45
      wind: {visual_only: true, reason: "bailey is in the lee of the ishigaki and tamon yagura"}
      lightning_schedule_s: [17, 23, 15, 21]
      flash_reduction: respect_setting
    x_exit: {volume: vol_lift_cradle, requires: complete}
  - id: ch07.b03
    type: cinematic
    place: pl_anchor_bastion
    title_ja: "俵に潜め"
    title_en: "Hide in the rice bales"
    target_s: 90
    checkpoint: false
    sequence: "/Game/Cinematics/Ch07/LS_Ch07_B03_Stowaways"
    duration_s: 90
    skippable: true
    fallback: camera_blend
    end_state: {player_transform: ps_ch07_b04_start, equipped: keep}
    subtitles:
      - ch07.b03.kohagi.001
      - ch07.b03.conscript.002
      - ch07.b03.enforcer.003
      - ch07.b03.enforcer.004
      - ch07.b03.enforcer.005
      - ch07.b03.kohagi.006
      - ch07.b03.shipvoice.007
    music: mus_ch07_ascent
  - id: ch07.b04
    type: stealth_zone
    place: pl_cargo_hold
    title_ja: "貨物倉を抜けよ"
    title_en: "Cross the cargo hold unseen"
    target_s: 240
    checkpoint: true
    zone: vol_cargo_hold
    guards:
      - id: g_e1
        type: enforcer_rifle
        patrol: pt_hold_port_loop
        sight: {cone_deg: 90, range_cm: 1800, dark_range_cm: 700}
        hearing_cm: 900
      - id: g_e2
        type: enforcer_rifle
        patrol: pt_hold_centre_loop
        sight: {cone_deg: 90, range_cm: 1800, dark_range_cm: 700}
        hearing_cm: 900
      - id: g_e3
        type: enforcer_rifle
        patrol: pt_hold_stbd_desk_loop
        sight: {cone_deg: 90, range_cm: 1800, dark_range_cm: 700}
        hearing_cm: 900
      - id: g_d1
        type: drone
        patrol: pt_gantry_sweep_a
        sight: {cone_deg: 60, range_cm: 1400, dark_range_cm: 900}
        hearing_cm: 0
      - id: g_d2
        type: drone
        patrol: pt_gantry_sweep_b
        sight: {cone_deg: 60, range_cm: 1400, dark_range_cm: 900}
        hearing_cm: 0
      - id: g_a1
        type: auditor
        patrol: pt_manifest_desk_turn
        sight: {cone_deg: 70, range_cm: 1200, dark_range_cm: 500}
        hearing_cm: 1200
      - id: g_c1
        type: bound_conscript
        patrol: pt_cart_x40
        sight: {cone_deg: 80, range_cm: 1000, dark_range_cm: 400}
        hearing_cm: 600
      - id: g_c2
        type: bound_conscript
        patrol: pt_cart_x84
        sight: {cone_deg: 80, range_cm: 1000, dark_range_cm: 400}
        hearing_cm: 600
    on_detected: "reinforce:hold_alarm"
    complete: exit_reached
    detection: {suspicion_rate: 1.0, alert_threshold: 1.0, search_s: 20}
    takedowns: {rear: true, lethal_default: true}
    nonlethal_types: [bound_conscript]
    light_sources: [lamp_hold_01, lamp_hold_02, lamp_hold_03]
    noise_surfaces:
      - {kind: gravel, volumes: [vol_spilled_rice_01, vol_spilled_rice_02]}
      - {kind: running_water, volumes: [vol_conveyor_stbd], mult: 0.5}
      - {kind: x_metal_grate, volumes: [vol_gantry], mult: 1.5}
    lures: [tsubute]
    waves:
      - id: hold_alarm
        enemies:
          - {type: enforcer_rifle, count: 3, spawn: sp_hold_fwd_hatch}
          - {type: drone, count: 1, spawn: sp_hold_gantry_fwd}
        trigger: "alert_state:alert"
    dialogue:
      - {"on": beat_start, lines: [ch07.b04.kohagi.001, ch07.b04.kohagi.002], mode: ambient}
      - {"on": "volume_enter:vol_hold_bell", lines: [ch07.b04.nyaakoto.003, ch07.b04.kohagi.004], mode: ambient}
      - {"on": "volume_enter:vol_hold_appraisal", lines: [ch07.b04.enforcer.005], mode: ambient}
      - {"on": "volume_enter:vol_manifest_desk", lines: [ch07.b04.auditor.006], mode: ambient}
      - {"on": "seal_cut:g_c1", lines: [ch07.b04.conscript.007], mode: ambient}
      - {"on": "seal_cut:g_c2", lines: [ch07.b04.conscript.008], mode: ambient}
      - {"on": "alert_state:suspicious", lines: [ch07.b04.enforcer.009], mode: ambient}
      - {"on": "alert_state:search", lines: [ch07.b04.enforcer.010], mode: ambient}
      - {"on": "alert_state:alert", lines: [ch07.b04.enforcer.011], mode: ambient}
      - {"on": "alert_state:unaware", lines: [ch07.b04.enforcer.012], mode: ambient}
      - {"on": auditor_alarm, lines: [ch07.b04.auditor.013], mode: ambient}
      - {"on": "lure_triggered:bell_bonsho", lines: [ch07.b04.kohagi.014], mode: ambient}
      - {"on": "wave_spawned:hold_alarm", lines: [ch07.b04.shipvoice.015], mode: ambient}
    music: mus_ch07_hold_stealth
    x_exit: {volume: vol_hold_fwd_hatch}
    x_lure_objects:
      - {id: bell_bonsho, radius_cm: 2500, uses: 1, draws: [unaware, suspicious], hold_s: 12}
    x_ambient_noise_mask:
      source: hull_boom
      schedule_s: [12, 12, 12]
      duration_s: 2.0
      warn_ms: 800
      noise_mult: 0.3
    x_body_discovery: {lit_aisle_suspicion: 0.5, dark_suspicion: 0.0}
  - id: ch07.b05
    type: explore_optional
    place: pl_seized_vault
    title_ja: "押収品倉を調べる"
    title_en: "Search the seized-goods vault"
    target_s: 120
    checkpoint: true
    requires: [ch07.b04]
    optional: true
    volume: vol_seized_vault
    pois:
      - {id: poi_nafudakake, kind: lore}
      - {id: poi_armor_chest, kind: cache}
      - {id: poi_notice_rack, kind: lore}
      - {id: poi_andon, kind: vista}
    rewards: [ch07.c01, ch07.c02, ch07.c03, arrows_12]
    exit_hint_after_s: 90
    dialogue:
      - {"on": "volume_enter:vol_vault_door", lines: [ch07.b05.kohagi.001], mode: ambient}
      - "on": "poi_found:poi_nafudakake"
        lines: [ch07.b05.nyaakoto.002, ch07.b05.kohagi.003, ch07.b05.nyaakoto.004]
        mode: ambient
      - {"on": "idle_s:90", lines: [ch07.b05.kohagi.005], mode: ambient}
    music: mus_ch07_vault_quiet
    x_entry: {door: door_seized_vault, lock: key_slate, interact_s: 2.0}
    x_story_flag: {set: nafudakake_marked, effect: "name board rides down on the b07 cradle; ch08 reads the flag"}
  - id: ch07.b06
    type: combat_wave
    place: pl_reckoning_engine
    title_ja: "算術機関室を制圧せよ"
    title_en: "Take the reckoning engine"
    target_s: 240
    checkpoint: true
    requires: [ch07.b04]
    unlocks: {weapons: [11], mechanics: [shield_break]}
    bounds: vol_engine_chamber
    waves:
      - enemies:
          - {type: enforcer_rifle, count: 3, spawn: sp_engine_floor_n, x_variant: shielded}
        trigger: start
      - enemies:
          - {type: enforcer_rifle, count: 2, spawn: sp_engine_mezz_e, x_variant: shielded}
          - {type: blade_retainer, count: 2, spawn: sp_engine_floor_s}
        trigger: "alive_below:2"
      - enemies:
          - {type: enforcer_rifle, count: 2, spawn: sp_engine_mezz_w, x_variant: shielded}
          - {type: grenadier, count: 1, spawn: sp_engine_door_n}
        trigger: "alive_below:2"
    complete: all_waves_cleared
    max_alive: 6
    nonlethal_types: [bound_conscript]
    target_kind: enemy
    dialogue:
      - {"on": beat_start, lines: [ch07.b06.nyaakoto.001], mode: ambient}
      - {"on": beat_start, lines: [ch07.b06.iota.002], mode: radio}
      - {"on": shield_hit_first, lines: [ch07.b06.iota.003], mode: radio}
      - {"on": shield_hit_first, lines: [ch07.b06.kohagi.004], mode: ambient}
      - {"on": "pickup:11", lines: [ch07.b06.iota.005], mode: radio}
      - {"on": shield_broken, lines: [ch07.b06.enforcer.006], mode: ambient}
      - {"on": "pattern:grenadier_throw", lines: [ch07.b06.enforcer.007], mode: ambient}
      - {"on": "pattern:retainer_close", lines: [ch07.b06.enforcer.008], mode: ambient}
    music: mus_ch07_engine
    x_guaranteed_drop: {weapon: 11, from: first_defeated_shielded_enforcer, ammo_mags: 3}
  - id: ch07.b07
    type: production_task
    task: crank
    place: pl_reckoning_engine
    title_ja: "昇降機を逆転させよ"
    title_en: "Reverse the extraction lift"
    target_s: 240
    checkpoint: true
    site: 1
    registry: {item_ja: "押収品の返還", item_en: "Seized goods returned", qty: 430, unit_ja: "駄", unit_en: horse-loads}
    crank:
      actor: override_wheel_01
      turns_required: 16
      turn_rate_band: [0.3, 0.9]
      progress_decay_per_s: 0.04
      stamina_per_turn: 8
      interruptible: true
      coop_npc: kohagi
    waves:
      - enemies:
          - {type: drone, count: 2, spawn: sp_engine_ring_air}
        trigger: "progress_at:0.25"
      - enemies:
          - {type: enforcer_rifle, count: 2, spawn: sp_engine_mezz_w, x_variant: shielded}
        trigger: "progress_at:0.5"
      - enemies:
          - {type: blade_retainer, count: 2, spawn: sp_engine_floor_s}
          - {type: enforcer_rifle, count: 1, spawn: sp_engine_door_n}
        trigger: "progress_at:0.75"
    dialogue:
      - {"on": beat_start, lines: [ch07.b07.iota.001, ch07.b07.iota.002], mode: radio}
      - {"on": "progress_at:0.25", lines: [ch07.b07.kohagi.003], mode: ambient}
      - {"on": "progress_at:0.5", lines: [ch07.b07.nyaakoto.004], mode: ambient}
      - {"on": "progress_at:0.75", lines: [ch07.b07.kohagi.005], mode: ambient}
      - {"on": crank_released, lines: [ch07.b07.kohagi.006], mode: ambient}
      - {"on": beat_complete, lines: [ch07.b07.iota.007], mode: radio}
      - {"on": "site_restored:1", lines: [ch07.b07.oyuki.008, ch07.b07.oyuki.009], mode: radio}
    music: mus_ch07_engine_crank
    x_override:
      reverse_torque: true
      ratchet_locks: [0.25, 0.5, 0.75]
      two_handed: true
      loadout_while_cranking: none
      overspeed: gear_slip_no_progress
      coop_npc_rate_turns_s: 0.15
      coop_npc_suspends_decay: true
      coop_npc_leaves_if_enemy_within_cm: 500
      accessibility_hold_to_crank_turns_s: 0.6
    x_registry_mode: record_only
  - id: ch07.b08
    type: combat_wave
    place: pl_hangar
    title_ja: "格納庫を突破せよ"
    title_en: "Break through the hangar"
    target_s: 240
    checkpoint: true
    unlocks: {weapons: [14], mechanics: []}
    bounds: vol_hangar
    waves:
      - enemies:
          - {type: enforcer_rifle, count: 2, spawn: sp_hangar_fwd, x_variant: shielded}
          - {type: enforcer_rifle, count: 1, spawn: sp_hangar_fwd}
          - {type: marksman, count: 1, spawn: sp_hangar_gallery}
        trigger: start
      - enemies:
          - {type: shield_enforcer, count: 2, spawn: sp_hangar_shuttle_2}
          - {type: enforcer_rifle, count: 2, spawn: sp_hangar_fwd}
        trigger: "alive_below:2"
      - enemies:
          - {type: grenadier, count: 1, spawn: sp_hangar_gallery_fwd}
          - {type: drone, count: 2, spawn: sp_hangar_mouth_air}
        trigger: "alive_below:2"
    complete: all_waves_cleared
    max_alive: 6
    nonlethal_types: [bound_conscript]
    target_kind: enemy
    dialogue:
      - {"on": beat_start, lines: [ch07.b08.kohagi.001], mode: ambient}
      - {"on": "alert_state:alert", lines: [ch07.b08.enforcer.002], mode: ambient}
      - {"on": "volume_enter:vol_hangar_canisters", lines: [ch07.b08.kohagi.003], mode: ambient}
      - {"on": "pickup:14", lines: [ch07.b08.iota.004, ch07.b08.iota.005], mode: radio}
      - {"on": "wave_spawned:2", lines: [ch07.b08.kohagi.006], mode: ambient}
      - {"on": "volume_enter:vol_sled_bay", lines: [ch07.b08.kohagi.007], mode: ambient}
    music: mus_ch07_hangar
    x_guaranteed_drop: {weapon: 14, from: marksman, ammo_rounds: 6}
    x_hazards:
      - {kind: explosive_canister, ids: [fc_01, fc_02, fc_03], blast_radius_cm: 360, damage: 80, hurts_player: true}
    x_environment:
      wind_volume: vol_hangar_mouth_wind
      push_cm_s: 120
      toward: mouth
      ledge_guard: true
      projectile_drift: true
    x_mechanics_proposed: [charged_shot]
  - id: ch07.b09
    type: dialogue
    place: pl_hangar
    title_ja: "地上からの報せ"
    title_en: "Word from the ground"
    target_s: 60
    checkpoint: false
    trigger: beat_start
    mode: radio
    priority: high
    interrupt: queue
    camera: none
    lines:
      - ch07.b09.iota.001
      - ch07.b09.iota.002
      - ch07.b09.iota.003
      - ch07.b09.iota.004
      - ch07.b09.iota.005
      - ch07.b09.nyaakoto.006
    music: mus_ch07_radio
    x_complete_also: "volume_enter:vol_dorsal_hatch"
  - id: ch07.b10
    type: combat_wave
    place: pl_hull_ridge
    title_ja: "外殻の稜線を渡れ"
    title_en: "Cross the hull ridge"
    target_s: 240
    checkpoint: true
    bounds: vol_hull_ridge
    waves:
      - enemies:
          - {type: drone, count: 2, spawn: sp_ridge_aft_air}
        trigger: start
      - enemies:
          - {type: drone, count: 3, spawn: sp_ridge_mast}
        trigger: "volume_enter:vol_ridge_mid"
      - enemies:
          - {type: drone, count: 3, spawn: sp_ridge_fwd_air}
        trigger: "volume_enter:vol_ridge_fwd"
    complete: all_waves_cleared
    max_alive: 4
    target_kind: enemy
    dialogue:
      - {"on": beat_start, lines: [ch07.b10.nyaakoto.001, ch07.b10.kohagi.002, ch07.b10.nyaakoto.003], mode: ambient}
      - {"on": "gust_warning:first", lines: [ch07.b10.kohagi.004], mode: ambient}
      - {"on": gust_warning, lines: [ch07.b10.kohagi.005], mode: ambient}
      - {"on": "volume_enter:vol_ridge_mid", lines: [ch07.b10.shipvoice.006], mode: ambient}
      - {"on": "volume_enter:vol_ridge_fwd", lines: [ch07.b10.kohagi.007], mode: ambient}
    music: mus_ch07_ridge
    x_environment: {wind: ridge_wind}
    x_exit: {volume: vol_bridge_rear_hatch, requires: complete}
    x_fall_respawn: {to: last_brace_anchor, hp_cost: 25, max_per_checkpoint: 3, then: checkpoint}
    x_mechanics_proposed: [wind_brace]
  - id: ch07.b11
    type: combat_wave
    place: pl_bridge_approach
    title_ja: "艦橋へ迫れ"
    title_en: "Push to the bridge"
    target_s: 240
    checkpoint: true
    unlocks: {weapons: [16], mechanics: []}
    bounds: vol_bridge_approach
    waves:
      - enemies:
          - {type: shield_enforcer, count: 1, spawn: sp_appr_door_a}
          - {type: enforcer_rifle, count: 2, spawn: sp_appr_atrium, x_variant: shielded}
        trigger: "volume_enter:vol_appr_door_a"
      - enemies:
          - {type: shield_enforcer, count: 2, spawn: sp_appr_door_b}
          - {type: blade_retainer, count: 1, spawn: sp_appr_door_b}
        trigger: "alive_below:2"
      - enemies:
          - {type: enforcer_rifle, count: 2, spawn: sp_appr_bridge_doors, x_variant: shielded}
          - {type: grenadier, count: 1, spawn: sp_appr_bridge_doors}
        trigger: "alive_below:2"
    complete: all_waves_cleared
    max_alive: 6
    target_kind: enemy
    dialogue:
      - {"on": beat_start, lines: [ch07.b11.iota.001, ch07.b11.iota.002], mode: radio}
      - {"on": "pickup:16", lines: [ch07.b11.iota.003], mode: radio}
      - {"on": "pattern:shield_advance", lines: [ch07.b11.enforcer.004], mode: ambient}
      - {"on": "wave_spawned:2", lines: [ch07.b11.kohagi.005], mode: ambient}
      - {"on": "wave_spawned:3", lines: [ch07.b11.enforcer.006], mode: ambient}
    music: mus_ch07_approach
    x_pickup: {id: security_rack, weapon: 16, interact_s: 2.0, lock: key_slate, gates: door_a_opens_after_pickup}
    x_exit: {volume: vol_bridge_doors, requires: complete}
  - id: ch07.b12
    type: cinematic
    place: pl_bridge
    title_ja: "提督コラテラ"
    title_en: "Admiral Collatera"
    target_s: 90
    checkpoint: false
    sequence: "/Game/Cinematics/Ch07/LS_Ch07_B12_SurvivalLoan"
    duration_s: 90
    skippable: true
    fallback: camera_blend
    end_state: {player_transform: ps_ch07_b13_start, equipped: keep}
    subtitles:
      - ch07.b12.collatera.001
      - ch07.b12.collatera.002
      - ch07.b12.collatera.003
      - ch07.b12.nyaakoto.004
      - ch07.b12.collatera.005
    music: mus_ch07_collatera_intro
  - id: ch07.b13
    type: boss
    place: pl_bridge
    title_ja: "旗艦提督コラテラを倒せ"
    title_en: "Defeat Admiral Collatera"
    target_s: 480
    checkpoint: true
    boss: boss_collatera
    arena: {volume: vol_bridge_arena, lock: true}
    phases:
      - {hp_pct_start: 100, pattern_table: collatera_p1_pistols}
      - {hp_pct_start: 60, pattern_table: collatera_p2_margin_call, adds: drone_pair, arena_mod: list_port_10deg}
      - {hp_pct_start: 30, pattern_table: collatera_p3_sabre, arena_mod: shield_burnout}
    defeat: disarm
    intro_cinematic: ch07.b12
    outro_cinematic: "camera_blend:collatera_knockdown_4s"
    checkpoint_per_phase: true
    telegraph: {palette: default, min_windup_ms: 400}
    barks:
      - {"on": "boss_phase:1", line: ch07.b13.collatera.001}
      - {"on": "pattern:twin_burst", line: ch07.b13.collatera.002}
      - {"on": "pattern:reload", line: ch07.b13.collatera.003}
      - {"on": shield_broken, line: ch07.b13.collatera.005}
      - {"on": "boss_phase:2", line: ch07.b13.collatera.006}
      - {"on": "pattern:margin_call", line: ch07.b13.collatera.007}
      - {"on": "idle_in_cover_s:6", line: ch07.b13.collatera.009}
      - {"on": "boss_phase:3", line: ch07.b13.collatera.010}
      - {"on": "pattern:fleche_lunge", line: ch07.b13.collatera.011}
      - {"on": boss_defeated, line: ch07.b13.collatera.013}
    dialogue:
      - {"on": "pattern:reload:first", lines: [ch07.b13.kohagi.004], mode: ambient}
      - {"on": "boss_phase:2", lines: [ch07.b13.kohagi.008], mode: ambient}
      - {"on": player_died, lines: [ch07.b13.kohagi.012], mode: ambient}
    music: mus_boss_collatera
    x_fate: knocked_down_left_on_bridge
    x_boss_stats:
      hp: 2000
      shield_hp: 240
      shield_regen_delay_s: 4.0
      shield_regen_per_s: 80
      shield_offline_on_reload_s: 1.6
      awase_stagger_s: 1.2
      damage_mult_vs_shield: {default: 1.0, melee: 1.25, w11: 1.5, w16: 2.5}
      w14_charged_vs_shield: removes_50pct_max
    x_pattern_tables:
      collatera_p1_pistols:
        cadence_s: [2.4, 2.6, 2.2]
        attacks:
          - id: twin_burst
            windup_ms: 400
            telegraph: cyan_laser_dots
            rounds: 6
            interval_ms: 90
            damage_per_round: 9
            recovery_ms: 500
            parry: false
            guard: chip_50
            counter: "strafe 150 cm or more during windup breaks the lock"
          - id: sidestep_burst
            dash_cm: 400
            windup_ms: 400
            telegraph: cyan_laser_dots
            then: twin_burst
            recovery_ms: 500
          - id: reload
            every_n_bursts: 3
            duration_ms: 1600
            telegraph: cell_eject_hiss
            shield: offline
            counter: "any hit lands, including arrows"
      collatera_p2_margin_call:
        cadence_s: [3.0, 3.0, 3.0]
        attacks:
          - id: margin_call
            windup_ms: 1500
            telegraph: amber_ring_250cm
            targets: 3
            targeting: "cover nearest the player, else the player's position"
            damage: 60
            every_s: 7.0
            cover_hits_to_destroy: 2
            max_cover_destroyed: 6
          - id: twin_burst
            windup_ms: 400
            telegraph: cyan_laser_dots
            rounds: 6
            interval_ms: 90
            damage_per_round: 9
            recovery_ms: 500
            parry: false
          - {id: reload, every_n_bursts: 3, duration_ms: 1600, telegraph: cell_eject_hiss, shield: offline}
          - id: slide_props
            every_s: 6.0
            windup_ms: 700
            telegraph: scrape_audio_and_wobble
            damage: 30
            knockdown_s: 0.6
            direction: port
        adds: {drone_pair: {type: drone, count: 2, spawn: sp_bridge_dome, behavior: mark_player_for_margin_call}}
        arena: {list_deg: 10, uphill_speed_mult: 0.85, downhill_speed_mult: 1.1}
      collatera_p3_sabre:
        cadence: "cut_pair, offhand_shot, fleche_lunge; gaps 1.0/1.2/1.5 s"
        attacks:
          - id: cut_pair
            windup_ms: 450
            telegraph: amber_edge_flash
            hits: 2
            damage: 22
            recovery_ms: 600
            parry: true
            on_awase: stagger_1200ms_on_second_cut
          - id: fleche_lunge
            windup_ms: 800
            telegraph: amber_floor_line_500cm
            damage: 35
            recovery_ms: 1100
            parry: true
            on_awase: stagger_1200ms
            on_marobashi: flank_window_1500ms
          - id: offhand_shot
            windup_ms: 400
            telegraph: cyan_laser_dot
            damage: 14
            recovery_ms: 400
            parry: false
            counter: sidestep
        muto_eligible: []
        arena: {list_deg: 10}
  - id: ch07.b14
    type: production_task
    task: hold
    place: pl_bridge
    title_ja: "信号灯と舵を守れ"
    title_en: "Hold the beacon and the helm"
    target_s: 180
    checkpoint: true
    site: 2
    hold: {volume: vol_helm, hold_s: 60, contest: pause, decay_per_s: 0.0}
    waves:
      - enemies:
          - {type: enforcer_rifle, count: 3, spawn: sp_bridge_rear_doors}
        trigger: start
      - enemies:
          - {type: blade_retainer, count: 2, spawn: sp_bridge_port_hatch}
          - {type: drone, count: 2, spawn: sp_bridge_dome}
        trigger: "progress_at:0.4"
      - enemies:
          - {type: shield_enforcer, count: 1, spawn: sp_bridge_stbd_hatch}
          - {type: enforcer_rifle, count: 2, spawn: sp_bridge_rear_doors, x_variant: shielded}
        trigger: "progress_at:0.75"
    dialogue:
      - {"on": beat_start, lines: [ch07.b14.kohagi.001], mode: ambient}
      - {"on": beat_start, lines: [ch07.b14.iota.002], mode: radio}
      - {"on": trim_event, lines: [ch07.b14.shipvoice.003], mode: ambient}
      - {"on": "trim_event:first", lines: [ch07.b14.kohagi.004], mode: ambient}
      - {"on": "progress_at:0.4", lines: [ch07.b14.oyuki.005], mode: radio}
      - {"on": "progress_at:0.5", lines: [ch07.b14.nyaakoto.006], mode: ambient}
      - {"on": beat_complete, lines: [ch07.b14.iota.007], mode: radio}
    music: mus_ch07_helm
    x_allies:
      - {npc: kohagi, role: beacon, downable: false}
    x_trim_events:
      at_progress: [0.25, 0.5, 0.75]
      interact_point: helm_trim_wheel
      interact_s: 2.0
      grace_s: 8
      decay_per_s_if_ignored: 0.02
    x_fail_timer:
      normal_s: 150
      easy_s: 200
      hard_s: 130
      on_expire: fail
      fiction: "the ship's glide reaches the ridge villages"
    x_environment: {list_deg: 5}
    x_fail_extra: {"on": x_timer_expired, to: checkpoint}
  - id: ch07.b15
    type: cinematic
    place: pl_hangar
    title_ja: "墜落"
    title_en: "The fall"
    target_s: 120
    checkpoint: false
    sequence: "/Game/Cinematics/Ch07/LS_Ch07_B15_TheFall"
    duration_s: 120
    skippable: true
    fallback: camera_blend
    end_state: {player_transform: ps_ch07_b16_start, equipped: keep}
    subtitles: [ch07.b15.nyaakoto.001, ch07.b15.collatera.002, ch07.b15.kohagi.003, ch07.b15.nyaakoto.004]
    music: mus_ch07_fall
    x_places_spanned: [pl_bridge, pl_hangar, pl_kayanohara]
  - id: ch07.b16
    type: dialogue
    place: pl_kayanohara
    title_ja: "萱野原"
    title_en: "Kaya Moor"
    target_s: 60
    checkpoint: true
    trigger: beat_start
    mode: ambient
    priority: high
    interrupt: queue
    camera: soft_lookat
    lines: [ch07.b16.toranosuke.001, ch07.b16.nyaakoto.002, ch07.b16.toranosuke.003]
    dialogue:
      - "on": "volume_enter:vol_riders"
        lines: [ch07.b16.valamort.004, ch07.b16.valamort.005, ch07.b16.valamort.006]
        mode: blocking
      - {"on": "volume_enter:vol_riders", lines: [ch07.b16.oyuki.007], mode: radio}
      - {"on": "volume_enter:vol_riders", lines: [ch07.b16.nyaakoto.008], mode: ambient}
    music: mus_ch07_aftermath
    x_on_complete: "chapter_complete -> registry_page"
collectibles:
  - id: ch07.c01
    collectible_id: ch07.c01
    category: heirloom
    place: pl_seized_vault
    mask_bit: 0
    codex:
      ja: "爪木坂道場の名札掛け。門弟の名札一枚ごとに、取立猫の番号札が貼られていた。"
      en: "The Tsumagizaka Dōjō name board. Every pupil's plaque bore a Collector's number tag."
  - id: ch07.c02
    collectible_id: ch07.c02
    category: seizure_notice
    place: pl_seized_vault
    mask_bit: 1
    codex:
      ja: "差押状。債務者番号七〇三一。差押物件、和弓一張、矢十二本。「執行保留：所持者未確保」"
      en: "Seizure notice. Debtor 7031. Items: one yumi, twelve arrows. 'Execution pending: holder not secured.'"
  - id: ch07.c03
    collectible_id: ch07.c03
    category: scroll_fragment
    place: pl_seized_vault
    mask_bit: 2
    codex:
      ja: "伝書の断簡、其の七。「風に逆らう矢は落ち、風を読む矢は届く。刀もまた同じ。」石鈴斎"
      en: "Scroll fragment VII. 'An arrow that fights the wind falls; one that reads it arrives. So too the sword.' Sekireisai"
  - id: ch07.c04
    collectible_id: ch07.c04
    category: league_mark
    place: pl_cargo_hold
    mask_bit: 3
    codex:
      ja: "俵の内側に、爪で刻まれた空紋。積み込みの債縛衆の誰かが、味方だ。"
      en: "A Sora mark scratched inside a bale. One of the collared loaders is with us."
  - id: ch07.c05
    collectible_id: ch07.c05
    category: registry_page
    place: pl_reckoning_engine
    mask_bit: 4
    codex:
      ja: "提灯街の改帳の写し。欄外に異星の注記。「無担保。債務にあらず。分類不能」"
      en: "A copy of the Lantern Ward registry. An alien note in the margin: 'Unsecured. Not debt. Unclassifiable.'"
  - id: ch07.c06
    collectible_id: ch07.c06
    category: seizure_notice
    place: pl_hangar
    mask_bit: 5
    codex:
      ja: "輸送艇の積荷目録。「押収予定：猫柳生の住民、全員。区分：担保（生体）」"
      en: "A shuttle manifest. 'Scheduled for seizure: all Nyaagyu residents. Category: collateral (living).'"
lines:
  - {id: ch07.b01.kohagi.001, beat: ch07.b01, "on": cinematic, mode: cinematic, speaker: scout, ja: "旗艦が城塞から最後の力を吸い上げている。", en: "The flagship is drawing the last power from the citadel.", register: terse, duration_s: 4.0, readings: "旗艦(きかん)", repeatable: false, audio: null}
  - {id: ch07.b01.oyuki.002, beat: ch07.b01, "on": cinematic, mode: cinematic, speaker: leader, ja: "力だけではございません。米、長持、刀、寺の鐘まで。", en: "Not only power. Rice, chests, swords, even the temple bell.", register: business_keigo, duration_s: 4.9, readings: "長持(ながもち)", repeatable: false, audio: null}
  - {id: ch07.b01.iota.003, beat: ch07.b01, "on": cinematic, mode: cinematic, speaker: clerk, ja: "今夜のうちに、千二百駄を積み上げる予定でございます。", en: "They plan to haul up 1,200 horse-loads tonight.", register: manual_keigo, duration_s: 4.8, readings: "駄(だ)", repeatable: false, audio: null}
  - {id: ch07.b01.nyaakoto.004, beat: ch07.b01, "on": cinematic, mode: cinematic, speaker: samurai, ja: "嵐の夜なら、誰も来ぬと踏んだか。", en: "They wagered no one would come in a storm.", register: samurai_plain, duration_s: 3.1, repeatable: false, audio: null}
  - {id: ch07.b01.oyuki.005, beat: ch07.b01, "on": cinematic, mode: cinematic, speaker: leader, ja: "嵐の中の一揆は、あちらの帳簿では「零」の査定です。", en: "In their books, a league in a storm is valued at zero.", register: business_keigo, duration_s: 4.3, readings: "一揆(いっき)、査定(さてい)", repeatable: false, audio: null}
  - {id: ch07.b01.oyuki.006, beat: ch07.b01, "on": cinematic, mode: cinematic, speaker: leader, ja: "その査定、覆してさしあげましょう。", en: "Let us correct their appraisal.", register: business_keigo, duration_s: 3.3, readings: "覆(くつがえ)して", repeatable: false, audio: null}
  - {id: ch07.b01.iota.007, beat: ch07.b01, "on": cinematic, mode: cinematic, speaker: clerk, ja: "通信塔を切れば検品が止まり、俵の中身はどなたも確かめません。", en: "Cut the relay and inspection stops. No one will check the bales.", register: manual_keigo, duration_s: 5.5, readings: "検品(けんぴん)、俵(たわら)", repeatable: false, audio: null}
  - {id: ch07.b01.kohagi.008, beat: ch07.b01, "on": cinematic, mode: cinematic, speaker: scout, ja: "俵に入る。あたしと、あんた。", en: "We go in the bales. Me. You.", register: terse, duration_s: 2.9, repeatable: false, audio: null}
  - {id: ch07.b01.oyuki.009, beat: ch07.b01, "on": cinematic, mode: cinematic, speaker: leader, ja: "務めは三つ。通信塔を切る。荷を下ろす。艦を落とす。", en: "Three tasks. Cut the relay. Send the goods down. Bring the ship down.", register: business_keigo, duration_s: 4.9, readings: "務(つと)め", repeatable: false, audio: null}
  - {id: ch07.b01.iota.010, beat: ch07.b01, "on": cinematic, mode: cinematic, speaker: clerk, ja: "無人の落下地点は、萱野原のみでございます。", en: "The only uninhabited landing site is Kaya Moor.", register: manual_keigo, duration_s: 4.0, readings: "萱野原(かやのはら)", repeatable: false, audio: null}
  - {id: ch07.b01.toranosuke.011, beat: ch07.b01, "on": cinematic, mode: cinematic, speaker: rival, ja: "俺は騎馬を集めて、萱野原で待つ。", en: "I will gather riders and wait at Kaya Moor.", register: samurai_brash_humbled, duration_s: 3.1, repeatable: false, audio: null}
  - {id: ch07.b01.toranosuke.012, beat: ch07.b01, "on": cinematic, mode: cinematic, speaker: rival, ja: "……お前への借りは、生きて返す。", en: "…What I owe you, I will repay alive.", register: samurai_brash_humbled, duration_s: 3.4, repeatable: false, audio: null}
  - {id: ch07.b01.nyaakoto.013, beat: ch07.b01, "on": cinematic, mode: cinematic, speaker: samurai, ja: "借りではない。", en: "It is no debt.", register: samurai_plain, duration_s: 1.5, repeatable: false, audio: null}
  - {id: ch07.b01.tetsugoro.014, beat: ch07.b01, "on": cinematic, mode: cinematic, speaker: gunsmith, ja: "連発銃だ。三十六発、雨でも黙らん。", en: "The repeater. Thirty-six rounds. Rain won't silence it.", register: blunt, duration_s: 3.9, readings: "連発銃(れんぱつじゅう)", repeatable: false, audio: null}
  - {id: ch07.b02.tamakichi.001, beat: ch07.b02, "on": "volume_enter:vol_bastion_staging", mode: ambient, speaker: fireworks, ja: "湿気た玉は、ただの紙や。今夜はわしの出番なしやな。", en: "Damp shells are just paper. No work for me tonight.", register: kamigata_cheerful, duration_s: 4.8, readings: "湿気(しけ)た", repeatable: false, audio: null}
  - {id: ch07.b02.okuzu.002, beat: ch07.b02, "on": "volume_enter:vol_bastion_staging", mode: ambient, speaker: apothecary, ja: "傷薬は腰に。濡らさないようにね。", en: "Salve's at your hip. Keep it dry.", register: calm, duration_s: 3.2, readings: "傷薬(きずぐすり)", repeatable: false, audio: null}
  - {id: ch07.b02.ashigaru.003, beat: ch07.b02, "on": "volume_enter:vol_bastion_staging", mode: ambient, speaker: league_ashigaru, ja: "空紋の幟は畳んどけ。風に持っていかれるぞ。", en: "Keep the Sora banners furled. The wind will take them.", register: rough_plain, duration_s: 4.0, readings: "空紋(そらもん)、幟(のぼり)", repeatable: false, audio: null}
  - {id: ch07.b02.otane.004, beat: ch07.b02, "on": "volume_enter:vol_bastion_steps", mode: ambient, speaker: farmer_young, ja: "雨で火縄は死ぬけどな、鉄五郎さんのは生きとる！　撃てえ！", en: "Rain kills a match, but Tetsugorō's guns live! Fire!", register: kamigata, duration_s: 4.8, readings: "火縄(ひなわ)", repeatable: false, audio: null}
  - {id: ch07.b02.kohagi.005, beat: ch07.b02, "on": "volume_enter:vol_bastion_steps", mode: ambient, speaker: scout, ja: "櫓に照準査定兵、一。石段の上に四。", en: "Marksman in the turret, one. Four atop the steps.", register: terse, duration_s: 3.5, readings: "櫓(やぐら)、照準査定兵(しょうじゅんさていへい)", repeatable: false, audio: null}
  - {id: ch07.b02.kohagi.006, beat: ch07.b02, "on": "volume_enter:vol_relay_foot", mode: ambient, speaker: scout, ja: "塔の根元に繋ぎ箱が三つ。全部切って。", en: "Three junction boxes at the tower's foot. Cut them all.", register: terse, duration_s: 3.9, readings: "繋(つな)ぎ箱", repeatable: false, audio: null}
  - {id: ch07.b02.kohagi.007, beat: ch07.b02, "on": "progress_at:0.34", mode: ambient, speaker: scout, ja: "一つ切れた。あと二つ。", en: "One cut. Two left.", register: terse, duration_s: 2.4, repeatable: false, audio: null}
  - {id: ch07.b02.otane.008, beat: ch07.b02, "on": "progress_at:0.34", mode: ambient, speaker: farmer_young, ja: "上から降りてくるで！　昇降台や！", en: "They're coming down! Off the lift!", register: kamigata, duration_s: 2.7, readings: "昇降台(しょうこうだい)", repeatable: false, audio: null}
  - {id: ch07.b02.kohagi.009, beat: ch07.b02, "on": "progress_at:0.67", mode: ambient, speaker: scout, ja: "二つ目。……北の門から回ってくる。", en: "That's two. …They're flanking from the north gate.", register: terse, duration_s: 3.7, repeatable: false, audio: null}
  - {id: ch07.b02.nyaakoto.010, beat: ch07.b02, "on": "site_restored:0", mode: ambient, speaker: samurai, ja: "これで、艦は目を失った。", en: "Now the ship is blind.", register: samurai_plain, duration_s: 2.5, repeatable: false, audio: null}
  - {id: ch07.b02.iota.011, beat: ch07.b02, "on": beat_complete, mode: radio, speaker: clerk, ja: "検品網、停止を確認。……帳簿様、申し訳ございません。", en: "Inspection net offline. …My apologies, Honored Ledger.", register: manual_keigo, duration_s: 5.3, readings: "帳簿様(ちょうぼさま)", repeatable: false, audio: null}
  - {id: ch07.b02.enforcer.012, beat: ch07.b02, "on": "alert_state:alert", mode: ambient, speaker: enforcer, ja: "無許可の集会を確認。解散を勧告します。", en: "Unauthorized assembly. You are advised to disperse.", register: corporate_keigo_bark, duration_s: 3.7, readings: "勧告(かんこく)", repeatable: true, audio: null}
  - {id: ch07.b02.enforcer.013, beat: ch07.b02, "on": wave_spawned, mode: ambient, speaker: enforcer, ja: "延滞者多数。回収を開始します。", en: "Multiple delinquents. Commencing recovery.", register: corporate_keigo_bark, duration_s: 3.0, readings: "延滞者(えんたいしゃ)", repeatable: true, audio: null}
  - {id: ch07.b02.enforcer.014, beat: ch07.b02, "on": enemy_retreat, mode: ambient, speaker: enforcer, ja: "損失拡大。後退し、再評価します。", en: "Losses rising. Withdrawing to reassess.", register: corporate_keigo_bark, duration_s: 3.3, repeatable: true, audio: null}
  - {id: ch07.b02.marksman.015, beat: ch07.b02, "on": "pattern:marksman_lock", mode: ambient, speaker: enforcer, ja: "照準、査定完了。", en: "Aim assessed.", register: corporate_keigo_bark, duration_s: 1.8, repeatable: true, audio: null}
  - {id: ch07.b02.ashigaru.016, beat: ch07.b02, "on": "npc_downed:teppo_*", mode: ambient, speaker: league_ashigaru, ja: "やられた……！　誰か！", en: "I'm hit…! Someone!", register: rough_plain, duration_s: 2.1, repeatable: true, audio: null}
  - {id: ch07.b03.kohagi.001, beat: ch07.b03, "on": cinematic, mode: cinematic, speaker: scout, ja: "息は浅く。耳、伏せて。", en: "Breathe shallow. Ears down.", register: terse, duration_s: 2.4, repeatable: false, audio: null}
  - {id: ch07.b03.conscript.002, beat: ch07.b03, "on": cinematic, mode: cinematic, speaker: conscript, ja: "……空紋や。ご武運を。", en: "…The Sora mark. Good fortune to you.", register: yamato_whisper, duration_s: 2.8, readings: "ご武運(ぶうん)", repeatable: false, audio: null}
  - {id: ch07.b03.enforcer.003, beat: ch07.b03, "on": cinematic, mode: cinematic, speaker: enforcer, ja: "検品端末、応答なし。手動で計上します。", en: "Scanner unresponsive. Logging manually.", register: corporate_keigo, duration_s: 3.8, readings: "計上(けいじょう)", repeatable: false, audio: null}
  - {id: ch07.b03.enforcer.004, beat: ch07.b03, "on": cinematic, mode: cinematic, speaker: enforcer, ja: "米、二俵。……重量、やや超過。", en: "Rice, two bales. …Slightly overweight.", register: corporate_keigo, duration_s: 3.4, readings: "二俵(にひょう)", repeatable: false, audio: null}
  - {id: ch07.b03.enforcer.005, beat: ch07.b03, "on": cinematic, mode: cinematic, speaker: enforcer, ja: "誤差の範囲内とします。積載。", en: "Within the margin of error. Load them.", register: corporate_keigo, duration_s: 2.9, readings: "誤差(ごさ)", repeatable: false, audio: null}
  - {id: ch07.b03.kohagi.006, beat: ch07.b03, "on": cinematic, mode: cinematic, speaker: scout, ja: "くしゃみ、するな。", en: "Don't sneeze.", register: terse, duration_s: 2.0, repeatable: false, audio: null}
  - {id: ch07.b03.shipvoice.007, beat: ch07.b03, "on": cinematic, mode: cinematic, speaker: ship_voice, ja: "積荷を受領。貨物倉へ搬入します。", en: "Cargo received. Transferring to the hold.", register: announcement_keigo, duration_s: 3.2, readings: "積荷(つみに)、搬入(はんにゅう)", repeatable: false, audio: null}
  - {id: ch07.b04.kohagi.001, beat: ch07.b04, "on": beat_start, mode: ambient, speaker: scout, ja: "右に二。上に目録が一。……灯りは、あっち。", en: "Two right. One drone above. …Light's that way.", register: terse, duration_s: 4.5, readings: "目録(もくろく)", repeatable: false, audio: null}
  - {id: ch07.b04.kohagi.002, beat: ch07.b04, "on": beat_start, mode: ambient, speaker: scout, ja: "艦が鳴ってる間は、足音が消える。", en: "While the hull groans, your steps can't be heard.", register: terse, duration_s: 3.5, repeatable: false, audio: null}
  - {id: ch07.b04.nyaakoto.003, beat: ch07.b04, "on": "volume_enter:vol_hold_bell", mode: ambient, speaker: samurai, ja: "村の鐘まで……。", en: "Even the village bell…", register: samurai_plain, duration_s: 2.0, repeatable: false, audio: null}
  - {id: ch07.b04.kohagi.004, beat: ch07.b04, "on": "volume_enter:vol_hold_bell", mode: ambient, speaker: scout, ja: "鐘に礫を当てたら、みんな寄ってく。一度きり。", en: "Hit the bell with a stone and they'll all go to it. Once only.", register: terse, duration_s: 4.4, readings: "礫(つぶて)", repeatable: false, audio: null}
  - {id: ch07.b04.enforcer.005, beat: ch07.b04, "on": "volume_enter:vol_hold_appraisal", mode: ambient, speaker: enforcer, ja: "品目四四七、漆の長持。付帯する思い出は、評価対象外。", en: "Item 447, lacquered chest. Attached memories: not appraisable.", register: corporate_keigo, duration_s: 5.0, readings: "四四七(よんよんなな)、長持(ながもち)", repeatable: false, audio: null}
  - {id: ch07.b04.auditor.006, beat: ch07.b04, "on": "volume_enter:vol_manifest_desk", mode: ambient, speaker: auditor, ja: "米二俵、検品記録なし。……後ほど照合を。", en: "Two rice bales, no inspection record. …Reconcile later.", register: corporate_keigo, duration_s: 4.2, readings: "照合(しょうごう)", repeatable: false, audio: null}
  - {id: ch07.b04.conscript.007, beat: ch07.b04, "on": "seal_cut:g_c1", mode: ambient, speaker: conscript, ja: "……首が軽い。前の扉、見張りは一人や。", en: "…My neck's light. One guard at the forward door.", register: yamato_whisper, duration_s: 4.0, repeatable: false, audio: null}
  - {id: ch07.b04.conscript.008, beat: ch07.b04, "on": "seal_cut:g_c2", mode: ambient, speaker: conscript, ja: "助かった……。黙って隠れとく。", en: "Thank you… I'll hide and keep quiet.", register: yamato_whisper, duration_s: 3.3, repeatable: false, audio: null}
  - {id: ch07.b04.enforcer.009, beat: ch07.b04, "on": "alert_state:suspicious", mode: ambient, speaker: enforcer, ja: "……在庫の移動を検知。", en: "…Inventory movement detected.", register: corporate_keigo_bark, duration_s: 2.5, readings: "在庫(ざいこ)", repeatable: true, audio: null}
  - {id: ch07.b04.enforcer.010, beat: ch07.b04, "on": "alert_state:search", mode: ambient, speaker: enforcer, ja: "未登録品を捜索します。", en: "Searching for unregistered items.", register: corporate_keigo_bark, duration_s: 2.5, readings: "捜索(そうさく)", repeatable: true, audio: null}
  - {id: ch07.b04.enforcer.011, beat: ch07.b04, "on": "alert_state:alert", mode: ambient, speaker: enforcer, ja: "密航者です。差し押さえます。", en: "Stowaway. Seizing.", register: corporate_keigo_bark, duration_s: 2.9, readings: "密航者(みっこうしゃ)", repeatable: true, audio: null}
  - {id: ch07.b04.enforcer.012, beat: ch07.b04, "on": "alert_state:unaware", mode: ambient, speaker: enforcer, ja: "誤差の範囲内と判断します。", en: "Judged within the margin of error.", register: corporate_keigo_bark, duration_s: 2.5, repeatable: true, audio: null}
  - {id: ch07.b04.auditor.013, beat: ch07.b04, "on": auditor_alarm, mode: ambient, speaker: auditor, ja: "照合不一致！　警報を！", en: "Records do not match! Raise the alarm!", register: corporate_keigo_bark, duration_s: 2.8, repeatable: true, audio: null}
  - {id: ch07.b04.kohagi.014, beat: ch07.b04, "on": "lure_triggered:bell_bonsho", mode: ambient, speaker: scout, ja: "今。", en: Now., register: terse, duration_s: 1.2, repeatable: false, audio: null}
  - {id: ch07.b04.shipvoice.015, beat: ch07.b04, "on": "wave_spawned:hold_alarm", mode: ambient, speaker: ship_voice, ja: "貨物倉に未登録品。保安要員は急行してください。", en: "Unregistered item in the hold. Security, respond.", register: announcement_keigo, duration_s: 4.3, readings: "保安要員(ほあんよういん)", repeatable: false, audio: null}
  - {id: ch07.b05.kohagi.001, beat: ch07.b05, "on": "volume_enter:vol_vault_door", mode: ambient, speaker: scout, ja: "左の壁に錠。鍵板で開く。", en: "Lock on the left wall. The key-slate opens it.", register: terse, duration_s: 3.3, readings: "錠(じょう)、鍵板(かぎいた)", repeatable: false, audio: null}
  - {id: ch07.b05.nyaakoto.002, beat: ch07.b05, "on": "poi_found:poi_nafudakake", mode: ambient, speaker: samurai, ja: "……名札掛けだ。先生の道場の。", en: "…The name board. From Sensei's dojo.", register: samurai_plain, duration_s: 3.3, readings: "名札掛(なふだか)け", repeatable: false, audio: null}
  - {id: ch07.b05.kohagi.003, beat: ch07.b05, "on": "poi_found:poi_nafudakake", mode: ambient, speaker: scout, ja: "札の一枚ずつに、番号が貼ってある。", en: "They've stuck a number on every plaque.", register: terse, duration_s: 3.3, repeatable: false, audio: null}
  - {id: ch07.b05.nyaakoto.004, beat: ch07.b05, "on": "poi_found:poi_nafudakake", mode: ambient, speaker: samurai, ja: "名は、番号ではない。", en: "A name is not a number.", register: samurai_plain, duration_s: 2.1, repeatable: false, audio: null}
  - {id: ch07.b05.kohagi.005, beat: ch07.b05, "on": "idle_s:90", mode: ambient, speaker: scout, ja: "そろそろ。機関室は前。", en: "Time to go. The engine room is forward.", register: terse, duration_s: 2.9, repeatable: false, audio: null}
  - {id: ch07.b06.nyaakoto.001, beat: ch07.b06, "on": beat_start, mode: ambient, speaker: samurai, ja: "算盤か……。利子を数え続けている。", en: "An abacus… counting interest, without end.", register: samurai_plain, duration_s: 3.6, readings: "算盤(そろばん)", repeatable: false, audio: null}
  - {id: ch07.b06.iota.002, beat: ch07.b06, "on": beat_start, mode: radio, speaker: clerk, ja: "ご注意ください。その先の執行兵は、個人障壁をお持ちです。", en: "Caution. The enforcers ahead carry personal shields.", register: manual_keigo, duration_s: 5.3, readings: "執行兵(しっこうへい)、障壁(しょうへき)", repeatable: false, audio: null}
  - {id: ch07.b06.iota.003, beat: ch07.b06, "on": shield_hit_first, mode: radio, speaker: clerk, ja: "障壁は、四秒間被弾がなければ、再充填されます。", en: "A shield recharges after four seconds unhit.", register: manual_keigo, duration_s: 4.4, readings: "被弾(ひだん)、再充填(さいじゅうてん)", repeatable: false, audio: null}
  - {id: ch07.b06.kohagi.004, beat: ch07.b06, "on": shield_hit_first, mode: ambient, speaker: scout, ja: "休ませるな。撃ち続けて。", en: "Don't let it rest. Keep firing.", register: terse, duration_s: 2.5, repeatable: false, audio: null}
  - {id: ch07.b06.iota.005, beat: ch07.b06, "on": "pickup:11", mode: radio, speaker: clerk, ja: "そのパルス・カービンは、障壁に対し一・五倍の効率でございます。", en: "That pulse carbine works 1.5 times better on shields.", register: manual_keigo, duration_s: 5.3, readings: "一・五(いってんご)", repeatable: false, audio: null}
  - {id: ch07.b06.enforcer.006, beat: ch07.b06, "on": shield_broken, mode: ambient, speaker: enforcer, ja: "障壁、喪失。", en: "Shield lost.", register: corporate_keigo_bark, duration_s: 1.5, readings: "喪失(そうしつ)", repeatable: true, audio: null}
  - {id: ch07.b06.enforcer.007, beat: ch07.b06, "on": "pattern:grenadier_throw", mode: ambient, speaker: enforcer, ja: "広域回収、実行します。", en: "Executing area recovery.", register: corporate_keigo_bark, duration_s: 2.3, repeatable: true, audio: null}
  - {id: ch07.b06.enforcer.008, beat: ch07.b06, "on": "pattern:retainer_close", mode: ambient, speaker: enforcer, ja: "取り立てます。", en: Collecting., register: corporate_keigo_bark, duration_s: 1.5, repeatable: true, audio: null}
  - {id: ch07.b07.iota.001, beat: ch07.b07, "on": beat_start, mode: radio, speaker: clerk, ja: "その大きな輪が、昇降機の手動制御でございます。", en: "That large wheel is the lift's manual override.", register: manual_keigo, duration_s: 4.3, readings: "昇降機(しょうこうき)", repeatable: false, audio: null}
  - {id: ch07.b07.iota.002, beat: ch07.b07, "on": beat_start, mode: radio, speaker: clerk, ja: "機関の回転と、逆へお回しください。", en: "Turn it against the engine.", register: manual_keigo, duration_s: 3.3, repeatable: false, audio: null}
  - {id: ch07.b07.kohagi.003, beat: ch07.b07, "on": "progress_at:0.25", mode: ambient, speaker: scout, ja: "爪、掛けた。もう戻らない。", en: "Pawl's set. It won't slip back.", register: terse, duration_s: 2.8, readings: "爪(つめ)", repeatable: false, audio: null}
  - {id: ch07.b07.nyaakoto.004, beat: ch07.b07, "on": "progress_at:0.5", mode: ambient, speaker: samurai, ja: "重い……！", en: "Heavy…!", register: effort_bark, duration_s: 1.3, repeatable: false, audio: null}
  - {id: ch07.b07.kohagi.005, beat: ch07.b07, "on": "progress_at:0.75", mode: ambient, speaker: scout, ja: "あと少し。", en: Almost., register: terse, duration_s: 1.2, repeatable: false, audio: null}
  - {id: ch07.b07.kohagi.006, beat: ch07.b07, "on": crank_released, mode: ambient, speaker: scout, ja: "手、離すな。戻される。", en: "Don't let go. It'll pull back.", register: terse, duration_s: 2.4, repeatable: true, audio: null}
  - {id: ch07.b07.iota.007, beat: ch07.b07, "on": beat_complete, mode: radio, speaker: clerk, ja: "昇降機、逆転。積荷、降下中でございます。", en: "Lift reversed. Cargo descending.", register: manual_keigo, duration_s: 4.0, readings: "降下(こうか)", repeatable: false, audio: null}
  - {id: ch07.b07.oyuki.008, beat: ch07.b07, "on": "site_restored:1", mode: radio, speaker: leader, ja: "受け取りました。駄数を記帳いたします。", en: "Received. We are recording the loads.", register: business_keigo, duration_s: 3.7, readings: "駄数(だすう)、記帳(きちょう)", repeatable: false, audio: null}
  - {id: ch07.b07.oyuki.009, beat: ch07.b07, "on": "site_restored:1", mode: radio, speaker: leader, ja: "返還は記帳のみ。札は切りません。持ち主へ、お返しするだけです。", en: "Returns are recorded, no tally cut. They simply go home.", register: business_keigo, duration_s: 5.9, readings: "札(ふだ)", repeatable: false, audio: null}
  - {id: ch07.b08.kohagi.001, beat: ch07.b08, "on": beat_start, mode: ambient, speaker: scout, ja: "上の回廊に照準査定兵。光ったら隠れて。", en: "Marksman on the gallery. When it glints, take cover.", register: terse, duration_s: 3.7, readings: "回廊(かいろう)", repeatable: false, audio: null}
  - {id: ch07.b08.enforcer.002, beat: ch07.b08, "on": "alert_state:alert", mode: ambient, speaker: enforcer, ja: "格納庫に侵入者。資産を保全してください。", en: "Intruder in the hangar. Secure the assets.", register: corporate_keigo, duration_s: 3.8, readings: "格納庫(かくのうこ)、保全(ほぜん)", repeatable: false, audio: null}
  - {id: ch07.b08.kohagi.003, beat: ch07.b08, "on": "volume_enter:vol_hangar_canisters", mode: ambient, speaker: scout, ja: "光る筒は、撃てば弾ける。", en: "Those glowing canisters burst when shot.", register: terse, duration_s: 2.9, readings: "弾(はじ)ける", repeatable: false, audio: null}
  - {id: ch07.b08.iota.004, beat: ch07.b08, "on": "pickup:14", mode: radio, speaker: clerk, ja: "プラズマ火縄銃は、溜めて撃つ設計でございます。", en: "The plasma matchlock is designed to be charged.", register: manual_keigo, duration_s: 4.3, readings: "火縄銃(ひなわじゅう)、溜(た)めて", repeatable: false, audio: null}
  - {id: ch07.b08.iota.005, beat: ch07.b08, "on": "pickup:14", mode: radio, speaker: clerk, ja: "溜めた一発は、障壁を貫きます。", en: "A charged shot pierces shields.", register: manual_keigo, duration_s: 3.0, readings: "貫(つらぬ)きます", repeatable: false, audio: null}
  - {id: ch07.b08.kohagi.006, beat: ch07.b08, "on": "wave_spawned:2", mode: ambient, speaker: scout, ja: "大盾、二。回り込んで。", en: "Two big shields. Go around them.", register: terse, duration_s: 2.4, readings: "大盾(おおだて)", repeatable: false, audio: null}
  - {id: ch07.b08.kohagi.007, beat: ch07.b08, "on": "volume_enter:vol_sled_bay", mode: ambient, speaker: scout, ja: "あの橇、覚えといて。", en: "Those sleds. Remember them.", register: terse, duration_s: 2.1, readings: "橇(そり)", repeatable: false, audio: null}
  - {id: ch07.b09.iota.001, beat: ch07.b09, "on": beat_start, mode: radio, speaker: clerk, ja: "地上より報告。鷲尾様の騎馬、萱野原に集結。二十騎でございます。", en: "Word from the ground. Lord Washio's riders are at Kaya Moor. Twenty.", register: manual_keigo, duration_s: 5.9, readings: "鷲尾(わしお)、騎(き)", repeatable: false, audio: null}
  - {id: ch07.b09.iota.002, beat: ch07.b09, "on": beat_start, mode: radio, speaker: clerk, ja: "……訂正いたします。二十一騎。ただいま一騎、到着いたしました。", en: "…Correction. Twenty-one. One more has just arrived.", register: manual_keigo, duration_s: 6.2, repeatable: false, audio: null}
  - {id: ch07.b09.iota.003, beat: ch07.b09, "on": beat_start, mode: radio, speaker: clerk, ja: "背骨通路は、提督が封鎖いたしました。", en: "The admiral has sealed the spine corridor.", register: manual_keigo, duration_s: 3.5, readings: "背骨(せぼね)、提督(ていとく)", repeatable: false, audio: null}
  - {id: ch07.b09.iota.004, beat: ch07.b09, "on": beat_start, mode: radio, speaker: clerk, ja: "艦橋へは、外殻の上を通るほかございません。", en: "The only way to the bridge is over the hull.", register: manual_keigo, duration_s: 4.0, readings: "艦橋(かんきょう)、外殻(がいかく)", repeatable: false, audio: null}
  - {id: ch07.b09.iota.005, beat: ch07.b09, "on": beat_start, mode: radio, speaker: clerk, ja: "外は静穏域の縁でございます。突風にご注意を。", en: "Outside is the edge of the calm. Beware of gusts.", register: manual_keigo, duration_s: 4.2, readings: "静穏域(せいおんいき)、縁(ふち)", repeatable: false, audio: null}
  - {id: ch07.b09.nyaakoto.006, beat: ch07.b09, "on": beat_start, mode: radio, speaker: samurai, ja: "風を読む。", en: "I will read the wind.", register: samurai_plain, duration_s: 1.6, repeatable: false, audio: null}
  - {id: ch07.b10.nyaakoto.001, beat: ch07.b10, "on": beat_start, mode: ambient, speaker: samurai, ja: "……雲の上に、月か。", en: "…The moon, above the clouds.", register: samurai_plain, duration_s: 2.4, repeatable: false, audio: null}
  - {id: ch07.b10.kohagi.002, beat: ch07.b10, "on": beat_start, mode: ambient, speaker: scout, ja: "弓に、これ。風が見える。", en: "Tie this to your bow. You'll see the wind.", register: terse, duration_s: 3.0, repeatable: false, audio: null}
  - {id: ch07.b10.nyaakoto.003, beat: ch07.b10, "on": beat_start, mode: ambient, speaker: samurai, ja: "風上へ、狙いをずらす。", en: "Aim off, into the wind.", register: samurai_plain, duration_s: 2.3, readings: "風上(かざかみ)", repeatable: false, audio: null}
  - {id: ch07.b10.kohagi.004, beat: ch07.b10, "on": "gust_warning:first", mode: ambient, speaker: scout, ja: "綱を掴めば、飛ばされない。", en: "Grab a cable and you won't be blown off.", register: terse, duration_s: 2.9, readings: "綱(つな)、掴(つか)めば", repeatable: false, audio: null}
  - {id: ch07.b10.kohagi.005, beat: ch07.b10, "on": gust_warning, mode: ambient, speaker: scout, ja: "来る！　伏せて！", en: "Here it comes! Get down!", register: terse, duration_s: 1.8, repeatable: true, audio: null}
  - {id: ch07.b10.shipvoice.006, beat: ch07.b10, "on": "volume_enter:vol_ridge_mid", mode: ambient, speaker: ship_voice, ja: "外殻に異物。目録は排除してください。", en: "Foreign object on the hull. Inventory units, remove it.", register: announcement_keigo, duration_s: 3.9, readings: "異物(いぶつ)、排除(はいじょ)", repeatable: false, audio: null}
  - {id: ch07.b10.kohagi.007, beat: ch07.b10, "on": "volume_enter:vol_ridge_fwd", mode: ambient, speaker: scout, ja: "艦橋が見えた。前へ。", en: "There's the bridge. Keep going.", register: terse, duration_s: 2.3, repeatable: false, audio: null}
  - {id: ch07.b11.iota.001, beat: ch07.b11, "on": beat_start, mode: radio, speaker: clerk, ja: "右手の保安棚に、電撃放射器がございます。", en: "The security rack on your right holds a shock emitter.", register: manual_keigo, duration_s: 3.8, readings: "保安棚(ほあんだな)、電撃放射器(でんげきほうしゃき)", repeatable: false, audio: null}
  - {id: ch07.b11.iota.002, beat: ch07.b11, "on": beat_start, mode: radio, speaker: clerk, ja: "鍵板を、おかざしください。", en: "Hold up the key-slate.", register: manual_keigo, duration_s: 2.6, readings: "鍵板(かぎいた)", repeatable: false, audio: null}
  - {id: ch07.b11.iota.003, beat: ch07.b11, "on": "pickup:16", mode: radio, speaker: clerk, ja: "大盾の障壁も、電撃で落ちます。お近くで。", en: "Even tower-shield fields fall to a shock. Up close.", register: manual_keigo, duration_s: 3.9, readings: "電撃(でんげき)", repeatable: false, audio: null}
  - {id: ch07.b11.enforcer.004, beat: ch07.b11, "on": "pattern:shield_advance", mode: ambient, speaker: enforcer, ja: "前進。資産を保全します。", en: "Advancing. Protecting assets.", register: corporate_keigo_bark, duration_s: 2.5, repeatable: true, audio: null}
  - {id: ch07.b11.kohagi.005, beat: ch07.b11, "on": "wave_spawned:2", mode: ambient, speaker: scout, ja: "盾、二。後ろに刃が一。", en: "Two shields. A blade behind them.", register: terse, duration_s: 2.5, readings: "刃(やいば)", repeatable: false, audio: null}
  - {id: ch07.b11.enforcer.006, beat: ch07.b11, "on": "wave_spawned:3", mode: ambient, speaker: enforcer, ja: "艦橋へ後退。提督をお守りします。", en: "Fall back to the bridge. Protect the admiral.", register: corporate_keigo, duration_s: 3.2, repeatable: false, audio: null}
  - {id: ch07.b12.collatera.001, beat: ch07.b12, "on": cinematic, mode: cinematic, speaker: boss_collatera, ja: "ようこそ、債務者番号七〇三一。旗艦『複利号』へ。", en: "Welcome aboard the Compound Interest, debtor seven-zero-three-one.", register: corporate_keigo, duration_s: 4.3, readings: "債務者番号(さいむしゃばんごう)、七〇三一(ななまるさんいち)、複利号(ふくりごう)", repeatable: false, audio: null}
  - {id: ch07.b12.collatera.002, beat: ch07.b12, "on": cinematic, mode: cinematic, speaker: boss_collatera, ja: "荷は下りました。ですが、利息は下りません。", en: "Your goods went down. Interest never goes down.", register: corporate_keigo, duration_s: 4.1, readings: "下(お)りました、利息(りそく)", repeatable: false, audio: null}
  - {id: ch07.b12.collatera.003, beat: ch07.b12, "on": cinematic, mode: cinematic, speaker: boss_collatera, ja: "従えば、生き残るための融資をやろう。", en: "Submit, and we may lend you enough to survive.", register: plain_condescending, duration_s: 3.5, readings: "融資(ゆうし)", repeatable: false, audio: null}
  - {id: ch07.b12.nyaakoto.004, beat: ch07.b12, "on": cinematic, mode: cinematic, speaker: samurai, ja: "借りる必要はない。私たちは作れる。", en: "We need no loan. We can make what we need.", register: samurai_formal, duration_s: 3.3, repeatable: false, audio: null}
  - {id: ch07.b12.collatera.005, beat: ch07.b12, "on": cinematic, mode: cinematic, speaker: boss_collatera, ja: "……与信、否決。", en: "…Credit denied.", register: corporate_keigo, duration_s: 2.1, readings: "与信(よしん)、否決(ひけつ)", repeatable: false, audio: null}
  - {id: ch07.b13.collatera.001, beat: ch07.b13, "on": "boss_phase:1", mode: bark, speaker: boss_collatera, ja: "返済計画を、ご提示いたします。", en: "Presenting your repayment schedule.", register: corporate_keigo, duration_s: 3.0, readings: "返済(へんさい)", repeatable: false, audio: null}
  - {id: ch07.b13.collatera.002, beat: ch07.b13, "on": "pattern:twin_burst", mode: bark, speaker: boss_collatera, ja: "利払いです。", en: "Interest due.", register: corporate_keigo, duration_s: 1.4, readings: "利払(りばら)い", repeatable: true, audio: null}
  - {id: ch07.b13.collatera.003, beat: ch07.b13, "on": "pattern:reload", mode: bark, speaker: boss_collatera, ja: "残高、補充。", en: "Replenishing balance.", register: corporate_keigo, duration_s: 1.6, readings: "残高(ざんだか)", repeatable: true, audio: null}
  - {id: ch07.b13.kohagi.004, beat: ch07.b13, "on": "pattern:reload:first", mode: ambient, speaker: scout, ja: "弾を込める間、障壁が消える！", en: "Her shield drops while she reloads!", register: terse, duration_s: 2.6, readings: "込(こ)める", repeatable: false, audio: null}
  - {id: ch07.b13.collatera.005, beat: ch07.b13, "on": shield_broken, mode: bark, speaker: boss_collatera, ja: "……資本不足。", en: "…Undercapitalized.", register: corporate_keigo, duration_s: 1.8, readings: "資本(しほん)", repeatable: true, audio: null}
  - {id: ch07.b13.collatera.006, beat: ch07.b13, "on": "boss_phase:2", mode: bark, speaker: boss_collatera, ja: "担保価値の下落を確認。", en: "Collateral value is falling.", register: corporate_keigo, duration_s: 2.2, readings: "担保(たんぽ)、下落(げらく)", repeatable: false, audio: null}
  - {id: ch07.b13.collatera.007, beat: ch07.b13, "on": "pattern:margin_call", mode: bark, speaker: boss_collatera, ja: "追証を請求します。", en: "Issuing a margin call.", register: corporate_keigo, duration_s: 1.9, readings: "追証(おいしょう)", repeatable: true, audio: null}
  - {id: ch07.b13.kohagi.008, beat: ch07.b13, "on": "boss_phase:2", mode: ambient, speaker: scout, ja: "床が傾く！　物が滑ってくる！", en: "The floor's tilting! Things are sliding!", register: terse, duration_s: 2.9, readings: "傾(かたむ)く", repeatable: false, audio: null}
  - {id: ch07.b13.collatera.009, beat: ch07.b13, "on": "idle_in_cover_s:6", mode: bark, speaker: boss_collatera, ja: "その遮蔽物も、担保です。", en: "That cover is collateral, too.", register: corporate_keigo, duration_s: 2.5, readings: "遮蔽物(しゃへいぶつ)", repeatable: true, audio: null}
  - {id: ch07.b13.collatera.010, beat: ch07.b13, "on": "boss_phase:3", mode: bark, speaker: boss_collatera, ja: "残る資産は、これのみ。", en: "This is my last asset.", register: corporate_keigo, duration_s: 2.3, readings: "資産(しさん)", repeatable: false, audio: null}
  - {id: ch07.b13.collatera.011, beat: ch07.b13, "on": "pattern:fleche_lunge", mode: bark, speaker: boss_collatera, ja: "清算。", en: Liquidation., register: corporate_keigo, duration_s: 1.2, readings: "清算(せいさん)", repeatable: true, audio: null}
  - {id: ch07.b13.kohagi.012, beat: ch07.b13, "on": player_died, mode: ambient, speaker: scout, ja: "立って。まだ終わってない。", en: "Get up. It isn't over.", register: terse, duration_s: 2.7, repeatable: true, audio: null}
  - {id: ch07.b13.collatera.013, beat: ch07.b13, "on": boss_defeated, mode: bark, speaker: boss_collatera, ja: "……不渡り、ですか。", en: "…Dishonored, then.", register: corporate_keigo, duration_s: 2.4, readings: "不渡(ふわた)り", repeatable: false, audio: null}
  - {id: ch07.b14.kohagi.001, beat: ch07.b14, "on": beat_start, mode: ambient, speaker: scout, ja: "信号灯、点けた！　下から見えるはず！", en: "Beacon's lit! They should see it below!", register: terse, duration_s: 3.1, readings: "信号灯(しんごうとう)", repeatable: false, audio: null}
  - {id: ch07.b14.iota.002, beat: ch07.b14, "on": beat_start, mode: radio, speaker: clerk, ja: "艦首を萱野原へ。舵を左へ三度、保ってください。", en: "Bow toward Kaya Moor. Hold the helm three degrees to port.", register: manual_keigo, duration_s: 4.4, readings: "艦首(かんしゅ)、舵(かじ)", repeatable: false, audio: null}
  - {id: ch07.b14.shipvoice.003, beat: ch07.b14, "on": trim_event, mode: ambient, speaker: ship_voice, ja: "針路、逸脱。", en: "Off course.", register: announcement_keigo, duration_s: 1.5, readings: "針路(しんろ)、逸脱(いつだつ)", repeatable: true, audio: null}
  - {id: ch07.b14.kohagi.004, beat: ch07.b14, "on": "trim_event:first", mode: ambient, speaker: scout, ja: "舵がずれてる！　戻して！", en: "The helm's drifting! Bring it back!", register: terse, duration_s: 2.6, repeatable: false, audio: null}
  - {id: ch07.b14.oyuki.005, beat: ch07.b14, "on": "progress_at:0.4", mode: radio, speaker: leader, ja: "灯りが見えます。村の者は、尾根へ逃がしております。", en: "We see your light. The villagers are moving to the ridge.", register: business_keigo, duration_s: 4.8, readings: "尾根(おね)", repeatable: false, audio: null}
  - {id: ch07.b14.nyaakoto.006, beat: ch07.b14, "on": "progress_at:0.5", mode: ambient, speaker: samurai, ja: "……空紋の提灯だ。", en: "…Sora lanterns.", register: samurai_plain, duration_s: 2.1, readings: "提灯(ちょうちん)", repeatable: false, audio: null}
  - {id: ch07.b14.iota.007, beat: ch07.b14, "on": beat_complete, mode: radio, speaker: clerk, ja: "降下角、確定。ここからは、重力のお仕事でございます。", en: "Descent angle locked. From here, it is gravity's work.", register: manual_keigo, duration_s: 5.0, readings: "降下角(こうかかく)", repeatable: false, audio: null}
  - {id: ch07.b15.nyaakoto.001, beat: ch07.b15, "on": cinematic, mode: cinematic, speaker: samurai, ja: "来い。まだ間に合う。", en: "Come. There is still time.", register: samurai_plain, duration_s: 2.2, repeatable: false, audio: null}
  - {id: ch07.b15.collatera.002, beat: ch07.b15, "on": cinematic, mode: cinematic, speaker: boss_collatera, ja: "……負債は、艦と共に。", en: "…The liability goes down with the ship.", register: corporate_keigo, duration_s: 3.0, readings: "負債(ふさい)", repeatable: false, audio: null}
  - {id: ch07.b15.kohagi.003, beat: ch07.b15, "on": cinematic, mode: cinematic, speaker: scout, ja: "ニャーコト！　橇！", en: "Nyaakoto! The sled!", register: terse, duration_s: 1.5, repeatable: false, audio: null}
  - {id: ch07.b15.nyaakoto.004, beat: ch07.b15, "on": cinematic, mode: cinematic, speaker: samurai, ja: "掴まれ！", en: "Hold on!", register: combat_bark, duration_s: 1.2, repeatable: false, audio: null}
  - {id: ch07.b16.toranosuke.001, beat: ch07.b16, "on": beat_start, mode: ambient, speaker: rival, ja: "……生きていたな。", en: "…You are alive.", register: samurai_brash_humbled, duration_s: 2.1, repeatable: false, audio: null}
  - {id: ch07.b16.nyaakoto.002, beat: ch07.b16, "on": beat_start, mode: ambient, speaker: samurai, ja: "受け止めると言った男が、いたからな。", en: "Someone promised to catch whatever fell.", register: samurai_plain, duration_s: 3.5, repeatable: false, audio: null}
  - {id: ch07.b16.toranosuke.003, beat: ch07.b16, "on": beat_start, mode: ambient, speaker: rival, ja: "栗丸も連れてきた。……乗れ。", en: "I brought Kurimaru. …Mount up.", register: samurai_brash_humbled, duration_s: 3.1, readings: "栗丸(くりまる)", repeatable: false, audio: null}
  - {id: ch07.b16.valamort.004, beat: ch07.b16, "on": "volume_enter:vol_riders", mode: blocking, speaker: banker, ja: "恒星信用院より、全債務者の皆様へ通達いたします。", en: "The Stellar Credit House addresses all debtors.", register: corporate_keigo, duration_s: 4.5, readings: "恒星信用院(こうせいしんよういん)、通達(つうたつ)", repeatable: false, audio: null}
  - {id: ch07.b16.valamort.005, beat: ch07.b16, "on": "volume_enter:vol_riders", mode: blocking, speaker: banker, ja: "全担保を回収する。", en: "All collateral is now called.", register: proclamation, duration_s: 2.2, readings: "回収(かいしゅう)", repeatable: false, audio: null}
  - {id: ch07.b16.valamort.006, beat: ch07.b16, "on": "volume_enter:vol_riders", mode: blocking, speaker: banker, ja: "人もまた、担保でございます。", en: "People, too, are collateral.", register: corporate_keigo, duration_s: 2.8, repeatable: false, audio: null}
  - {id: ch07.b16.oyuki.007, beat: ch07.b16, "on": "volume_enter:vol_riders", mode: radio, speaker: leader, ja: "……夜明けに、城へ参ります。", en: "…At dawn, we go to the castle.", register: business_keigo, duration_s: 3.1, readings: "参(まい)ります", repeatable: false, audio: null}
  - {id: ch07.b16.nyaakoto.008, beat: ch07.b16, "on": "volume_enter:vol_riders", mode: ambient, speaker: samurai, ja: "先生を、取り戻す。", en: "We take Sensei back.", register: samurai_plain, duration_s: 2.0, repeatable: false, audio: null}
ui_prompts:
  - {id: ui.ch07.prompt.cut_junction, ja: "繋ぎ箱を切る", en: "Cut the junction", beat: ch07.b02}
  - {id: ui.ch07.prompt.leave_bale, ja: "俵から出る", en: "Leave the bale", beat: ch07.b04}
  - {id: ui.ch07.prompt.throw_tsubute, ja: "礫を投げる", en: "Throw a stone", beat: ch07.b04}
  - {id: ui.ch07.prompt.seal_cut, ja: "首輪を断つ", en: "Cut the collar", beat: ch07.b04}
  - {id: ui.ch07.prompt.douse_lamp, ja: "灯りを消す", en: "Put out the lamp", beat: ch07.b04}
  - {id: ui.ch07.prompt.key_slate, ja: "鍵板をかざす", en: "Use the key-slate", beat: ch07.b05, x_also_beats: [ch07.b11]}
  - {id: ui.ch07.prompt.peel_tags, ja: "番号札を剥がす", en: "Peel off the tags", beat: ch07.b05}
  - {id: ui.ch07.prompt.crank, ja: "輪を回す", en: "Turn the wheel", beat: ch07.b07}
  - {id: ui.ch07.prompt.charge, ja: "長押しで溜め撃ち", en: "Hold to charge", beat: ch07.b08}
  - {id: ui.ch07.prompt.brace, ja: "綱を掴む", en: "Brace on the cable", beat: ch07.b10}
  - {id: ui.ch07.prompt.trim, ja: "舵を戻す", en: "Correct the helm", beat: ch07.b14}
  - {id: ui.ch07.tip.shield, ja: "障壁は四秒被弾なしで再充填", en: "Shields recharge after 4 s unhit", beat: ch07.b06}
  - {id: ui.ch07.tip.charge, ja: "溜め撃ちは障壁を貫く", en: "Charged shots pierce shields", beat: ch07.b08}
  - {id: ui.ch07.tip.wind, ja: "矢は風に流される。風上を狙え", en: "Arrows drift. Aim into the wind.", beat: ch07.b10}
  - {id: ui.ch07.tip.lee, ja: "肋材や鰭の陰は風を防ぐ", en: "Ribs and fins block the wind", beat: ch07.b10}
  - {id: ui.ch07.tip.reload_window, ja: "装填中は障壁が消える", en: "Her shield drops while reloading", beat: ch07.b13}
  - {id: ui.ch07.registry.note, ja: "返還のみ記帳・札は切らず", en: "Recorded as returned. No tally cut.", beat: ch07.b16, "on": beat_complete}
```
