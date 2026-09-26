# 第五章 工房の蜂起: The Foundry Uprising

> **Monetary boundary (bible §2).** In this chapter, as in the whole campaign, SORA XOR (and the registry that leads to it) is a production-only storytelling premise. XOR is cut only against finished, inspected goods, is never shown as a balance or converted, and has no link to multiplayer XOR bonds, NFTs, wallets or IrohaConnect. It makes no claim about real-world money, investment or policy, and it does not describe the real SORA network or the design in the SORA Nexus article. **Review note (C1 lead, 2026-09-25):** names, calendar, speaker ids, Japanese punctuation and YAML field names in this file follow bible §9.1, §12.5 and §18.

**Chapter 5 production design and script.** Chapter id `ch05_silk_foundry`. Map: arena 2 (Silk Foundry) plus campaign-only sublevels. Target: 60 min (3,600 s). 18 beats. 125 voiced lines plus 16 HUD prompts. Boss: `boss_tarifa`.

**Status:** this is the Wave 2 lane C1 script for chapter 5. It is derived from and consistent with the [story bible](story-bible.md) (§§2, 3, 4, 6, 7, 8, 9, 10, 12, 13 ch05, 14, 15.2, 16, 17, 18, 19, 20). Nothing here is implemented. All numbers are **proposals** for the owning lanes to ratify:

- L1: beats, layouts, saves, dialogue data.
- L2: enemies, stealth and the loom automaton.
- L3: Tarifa's pattern tables.
- L4: HUD prompts and the registry screen.
- L5: music and captioned barks.
- C2 and C3: spaces.
- C4: the mission.
- C9: cinematics.

Fields outside the bible's §12 taxonomy are kept under `x_ext` and listed in §6 for L1 to accept or reject.

**Still pending, as for every chapter:**

- Native Japanese review of every line, reading and register (B7).
- Historian and practitioner review of the tatara, smithing, weaving, tack and weapon handling in §4.
- Playtest telemetry to confirm the 60-minute target.

**Related sources:** [catalog.json](../../Content/Data/catalog.json) (schema 3, chapter index 4 = ch05), [offline acceptance](offline-acceptance.md), [historical arms](../historical-arms.md), [horse tack references](../historical-horse-tack-art-reference.md), [SORA kamon runtime art](../sora-kamon-runtime-art.md), [photoreal acceptance](../art-direction/photoreal-acceptance.md), [Estate mesh terrain](../mesh-terrain-nyaagyu.md).

---

## 0. At a glance

| Item | Chapter 5 |
|---|---|
| In-fiction time | 元和九年 水無月七日頃 (Genna 9, about the 7th day of the 6th month; midsummer, first-quarter moon). From 22:00 (亥の刻) to dawn, about 05:00. This leaves about three weeks before ch06, which takes place on the moonless last night of the same month (六月晦日) |
| Place | The Silk Foundry (絹の工房), 5 km upriver from the Nyaagyu estate. Arena 2 is the foundry yard; the halls and the iron-sand slope are campaign sublevels |
| Target / mix (min) | 60 = combat 19 + explore 2.5 + stealth 4 + production 25 + mounted 0 + cinematic/dialogue 9.5 (matches bible §10) |
| Weapons unlocked | **20 薙刀** (b04, Okinu's, lent) → **8 鍛冶槌** (b08, Kōzō's, lent) → **1 アーク・カービン** (b09, first League-built gun), in the §11 order |
| Mechanic flag | None by default. `manufacture` is already unlocked at ch01.b09. The proposed `hammer_rhythm` flag for b08 is listed in §6 item 3 |
| Production sites | site 0 → b03 職人の避難所; site 1 → b06 絹と鋼の炉; site 2 → b12 生産の記録台. This keeps the catalog order |
| Registry | 鏃 24本 (b08), アーク・カービン 3挺 (b09), 絹幟 1旒 (b11). All three are tallied as the **first XOR** in b12 |
| Boss | `boss_tarifa`, Foundry Overseer Tarifa (工房監督官 タリファ). Hazard controller with a tether-lash; 3 phases (100–65 / 65–30 / 30–0) |
| New enemy | `loom_automaton` (織機傀儡), a levy loom stood up on its own frame (§2.4) |
| New mechanics | Rhythm manufacture ×3 (bellows rate band, aizuchi hammer call-and-response, sorabiki cord pulls). Polearm obstruction by looms. Cycling molten-channel hazards with environmental kills. The split-tally first-XOR ceremony. Tarifa's coolant mantle, which drops in steam |
| Horse | None ridden. Two pack horses (駄馬) with 荷鞍 pack saddles are loaded on foot in b17 |
| Collectibles | 6 (`ch05.c01`–`c06`, chapter-local mask bits 0–5; global 24–29) |
| Humor | 1 approved beat (the 「昼寝禁止」 notice, b01) plus 2 proposed restrained beats (b11 and b18); see §3.6 |

---

## 1. Synopsis, play time, places

### 1.1 Synopsis

**JA.** 元和九年、水無月七日。屋敷から川を五キロ遡った「絹の工房」では、糸取りと製鉄が同時に回され、首輪の職人六十人に百四十パーセントの稼働率が課されている。足りぬ分は、各人の元本に加算される。

ニャーコトと小萩は鉄穴流しの水路から忍び込み、糸取場で六人の首輪を断つ。西陣仕込みの織師お絹、鉄砲鍛冶の鉄五郎もその中にいた。炭小屋でお絹は母の形見の薙刀を「貸す」。村下の鋼蔵は言う。炉の中の鉄は二晩目、今夜が三晩目。火が絶えれば、すべてが無に帰す。

機場が蜂起する。ニャーコトは踏鞴を踏んで炎を山吹色に保ち、高殿を守り抜き、鋼蔵と相鎚を打って鏃を鍛え、鉄五郎と一揆初の銃、アーク・カービンを組み上げる。お雪とお種が一揆の鉄砲衆を連れて到着し、お絹は四十夜かけて目盛りの下で織り続けた幟を仕上げる。

改め所で、最初の SORA XOR が切られる。作り手、受け手、籤で選ばれた改め役が、在る物だけを数え、割符の割目に空紋の焼印が押される。タリファは織機を傀儡に変え、雷雨の中で湯路を開く。燃える鋳物場を抜け、高殿の足場で彼女と戦う。熱鉄に落ちる雨が彼女の外套を焼き切り、タリファは自ら開いた湯路に消える。夜明け、駄馬が鏃と銃を運び出し、空紋の幟が上がる。そして稼働率の掲示板から、見知らぬ声が届く。金庫の中の会計補、イオタである。

**EN.** The seventh night of the sixth month, Genna 9, in midsummer. Five kilometres upriver from the estate, the Silk Foundry reels silk and smelts iron at the same time. Sixty collared workers are held to 140% of a quota nobody can meet, and every shortfall is added to their principal.

Nyaakoto and Kohagi slip in through the iron-sand washing channels. In the reeling shed he cuts the collars from six captives, among them Okinu, the Nishijin-trained weaver, and Tetsugorō, the gunsmith. He leads them to the charcoal shed. There Okinu lends him her mother's naginata. Kōzō, the master smelter, explains that the iron has been in the furnace for two nights and tonight is the third. If the fire dies, all of it is lost.

The loom hall rises. Nyaakoto:

- treads the bellows until the flame burns golden;
- holds the tatara hall against the counterattack;
- strikes arrowheads with Kōzō, turn and turn about;
- helps Tetsugorō assemble the League's first gun, the Arc Carbine.

Oyuki and Otane arrive with League gunners. Okinu finishes the banner she has been weaving for forty nights under the levy meter, while Nyaakoto pulls the figure cords.

In the inspection hall the first SORA XOR is cut. Maker, receiver and an inspector drawn by lot count only what exists, and the SORA mon is branded across the split tally. Tarifa answers by standing the looms up as automata and opening the melt channels as a thunderstorm breaks. Nyaakoto crosses the burning casting floor and fights her on the tatara hall's gantry. Rain on hot iron overloads her mantle, and she falls into the channel she opened herself.

At dawn the pack horses leave with arrowheads and guns, and the nobori goes up. Then the quota board speaks in a stranger's voice: Iota, from inside the vault.

**Chapter function.** Act II ends here with the premise made physical. Registry entries written in ch04 become XOR for the first time, under all five articles of the charter (bible §2.2). Kōzō's line 「わしは鉄しか信じん」 turns into 「鉄を数えた札なら、信じてもええ」. Iota's contact sets up ch06, and the Washio transfer notice (b13) sets up Toranosuke's reveal there.

### 1.2 Target play time and pacing

| Beat | Type (category) | Min | C | E | S | P | Cin |
|---|---|---|---|---|---|---|---|
| b01 | cinematic | 2.0 | | | | | 2.0 |
| b02 | stealth_zone | 4.0 | | | 4.0 | | |
| b03 | production_task · escort | 5.0 | | | | 5.0 | |
| b04 | dialogue | 1.5 | | | | | 1.5 |
| b05 | combat_wave | 5.0 | 5.0 | | | | |
| b06 | production_task · crank | 4.0 | | | | 4.0 | |
| b07 | production_task · defend | 5.0 | | | | 5.0 | |
| b08 | production_task · manufacture | 4.0 | | | | 4.0 | |
| b09 | production_task · manufacture | 3.0 | | | | 3.0 | |
| b10 | combat_wave | 3.0 | 3.0 | | | | |
| b11 | production_task · manufacture | 2.0 | | | | 2.0 | |
| b12 | cinematic | 2.5 | | | | | 2.5 |
| b13 | explore_optional | 2.5 | | 2.5 | | | |
| b14 | cinematic | 1.5 | | | | | 1.5 |
| b15 | combat_wave | 4.0 | 4.0 | | | | |
| b16 | boss | 7.0 | 7.0 | | | | |
| b17 | production_task · carry | 2.0 | | | | 2.0 | |
| b18 | cinematic | 2.0 | | | | | 2.0 |
| **Σ** | | **60.0** | **19** | **2.5** | **4** | **25** | **9.5** |

- Targets include typical optional play and about 12% retry overhead on Normal (真剣), as in bible §10.
- Telemetry acceptance: the playtest median for the chapter falls between 48 and 72 min (±20%).
- Voiced time is about 8.3 min (497 s over 125 lines). Most lines are walk-and-talk with control kept; b04 is ambient, with two interact gates.

### 1.3 Time of day, weather and lighting

| Beats | Clock (in fiction) | Sky and key light | Weather / FX | Notes | Mac fallback |
|---|---|---|---|---|---|
| b01–b02 | 22:00–22:30 | Half moon low in the west (4100 K fill, faint). Alien floodlights 8500 K. Kagaribi braziers 1800 K | Humid haze; heat lightning far to the SW with no thunder; mist on the settling ponds | The foundry glows from its vents. The cyan floodlights are the only cold key | Height fog only; no more than 3 shadowed lights on the slope |
| b03–b05 | 22:30–23:30 | Interiors: reeling-pot braziers 1900 K, andon 2000 K, moon bars through the 連子窓 | Cocoon-pot steam, dust | Levy meters give cold cyan accents on warm interiors | Pots as emissive cards; 6 shadowed lights |
| b06–b07 | 23:30–00:30 | Furnace key about 1600 K, flickering with the bellows rate | Sparks, charcoal dust, heat shimmer | Flame colour is a gameplay gauge (red → golden → white) and must stay legible under tonemapping | Baked emissive furnace; sparks capped |
| b08–b11 | 00:30–02:30 | Forge hearths 1700 K; loom hall andon plus moonlight | Cloud cover builds; first distant thunder at b11 | The quench steam catches the hearth light | Capped sparks |
| b12 | 03:00 | Inspection hall: candles and andon 1900 K; the brand iron glows | Lightning flickers behind the shōji | Lightning follows the flash-reduction setting (bible §16) | Sky-light flicker only |
| b13–b16 | 03:15–04:15 | Thunderstorm. Molten channels 1400–1600 K emissive; lightning | Heavy rain; roof drips; steam where rain meets iron (b16 P3) | Amber telegraphs are animated edge pulses, kept distinct from the melt's steady glow | Rain as a screen layer plus limited particles; steam as cards |
| b17–b18 | 04:45–05:15 | Dawn after the storm: low sun 3500 K and washed air | Mist rising from hot ground; roofs steaming | The nobori is backlit on the ridge pole | Fewer volumetric shafts |

### 1.4 Locations and layout

#### 1.4.1 Conventions and the arena 2 rule

- **Coordinates:** metres, origin at the centre of arena 2. +X is east, +Y is north (uphill), and Z is up. The river runs along the south side and flows west toward the estate.
- **Arena 2 is the foundry yard (中庭).** In the current kernel (`first-release-6`, `map_walls(2)`) the arena is 48 × 48 m (±24 m) and has four collision boxes:
  - a west wall at x −11…−9, y −12…+10, 5 m high;
  - an east wall at x +9…+11, y −10…+12, 5 m high;
  - a south low barrier at x ±3, y −5…−3.5, 2.3 m high;
  - a north low barrier at x ±3, y +3.5…+5, 2.3 m high.
  
  C2 dresses them without collision: the west wall as a charcoal-bale stack under a lean-to, the east wall as iron-sand bins with timber retaining boards, the south barrier as pig-iron ingots on a skid, and the north barrier as quench troughs and a handcart. When L6 F4 replaces these boxes, the dressing is re-fitted; the chapter layout only assumes an open yard with two long 5 m walls and two low barriers.
- **Everything else is a campaign sublevel** (`L_Ch05_Kanna`, `L_Ch05_Foundry_Halls`, `L_Ch05_Foundry_Yard_Dressing`): the halls, the slope, the quota board and the NPC and horse actors. Halls sit outside the ±24 m kernel bounds, so they never overlap arena collision. Sublevel collision loads only in the campaign and is never written into the kernel's collision data (bible §14).
- **Texel density:** 1024 px/m for hero pieces (furnace, looms, anvil, tally, nobori) and 512 px/m for mid-ground (bible §15.1).

#### 1.4.2 Overview map (not to scale)

```
          x: −60         −28   −13    0    +13   +26        +46   +62 ─────────────▶ +222
 y +58  ┌──────────────────────────────────────────────────────────┐        (hill)
        │                ┌──── 高殿 TAKADONO ────┐┌── 鋳物場 ──┐     │
 y +54  │                │ furnace ▣ at (0,+44)   ││ IMONOBA    │     │
        │                │ gantry deck +3.0 m     ││ 4 channels ◀── east gate (+33,+46)
 y +34  │ 炭小屋 REFUGE   └──── big door (0,+34) ──┘└────────────┘     │
        │ (−28…−16,+26…+36)    charcoal apron 炭場    nobori pole (0,+22)
 y +24  │ ─────────┬──────────────────────────────────┬────────────── │
        │ 大鍛冶場  │       YARD 中庭 = ARENA 2          │ 機場 LOOM HALL │
        │ OKAJI     │   ▓ W stack wall    ▓ E bin wall   │ (+26…+56,−6…+12)
        │ (−52…−28, │        ▬ low barriers ▬            │───────────────│
        │  −4…+16)  │        ◆ quota board (0,−14)       │ 糸取場 REELING │  culvert
        │ 改め所     │                                    │ SHED (+26…+46, ◀══════ 鉄穴流し
        │ ARATAMEJO │                                    │  −30…−12)     │  KANNA-NAGASHI
 y −24  │ (−46…−30,─┴──────── south lane (y −24…−28) ─────┴───────────────│  x +62…+222,
        │  −26…−10)  取立蔵 STOREHOUSE  pack horses   drying racks         │  y −44…−8,
        │  west lane (−20…−8,−30…−40)  (−4…+8,−28…−34) (+10…+26,−28…−36) │  rising 38 m east
 y −44  └─ x −56 ─────────────── 南門 main gate (0,−44) ──────────────────┘
 y −48  ~~~~~~~~~~~~~~~~~~~~~~~ river (flows west, toward the estate) ~~~~~~~~~~~~~~~~
```

The compound is walled: the outer wall runs at x −60, x +62, y −44 and, to the north, along the hill cut at y +58. The halls face the yard on three sides. Four routes cross the site:

1. The **kanna culvert** is the way in (b02 → b03).
2. The **south lane and west lane** are the hidden escort route (b03).
3. The **yard** is the open hub for b10 and b17.
4. The **charcoal apron** leads uphill to the tatara hall and on to the casting floor (b06, b07, b14–b16).

#### 1.4.3 Places

**`pl_kanna_nagashi` 鉄穴流し (Iron-sand channels): b02. New exterior (`L_Ch05_Kanna`).**

- **Footprint:** a west-facing slope 160 × 36 m (x +62…+222, y −44…−8), dropping 38 m (average grade about 1:4.2) from the cut face at the top to two settling ponds at the bottom.
- **Top to bottom:**
  1. The **cut face (切羽)**: weathered granite (真砂) with orange-brown banding. A 1.2 m feed ditch (走り) runs along its toe.
  2. **Three stepped washing basins**, each 8 × 5 m with sluice-board weirs. Their period names (大池 / 中池 / 乗り池) are to be verified (§4.3).
  3. The **washing flume (洗樋)**: a 50 m timber flume with a boardwalk 0.8 m wide, 1.2 m above the main channel.
  4. **Tailings heaps** of loud gravel, 3–4 m high, on both flanks of the lower channel.
  5. The **laborers' hut** (6 × 4 m), with the alarm post and the alien floodlight.
  6. **Two settling ponds** (15 × 10 m, 0.6 m deep).
  7. The **culvert (暗渠)**: 1.0 m wide, 1.2 m high and 18 m long, with knee-deep running water. It runs under the east wall and the shed's footing into the reeling shed's stone trough at (+44, −27).
- **Routes:**

  | Route | Movement | Noise | Exposure |
  |---|---|---|---|
  | A: in the channels | Water ×0.7 speed | ×0.5 | Hidden by the 0.9 m channel walls when crouched |
  | B: the flume boardwalk | Fast | — | Swept by the drone and watched along the flume guard's line |
  | C: the tailings flank | — | Loud gravel, ×1.5 | High cover |
  | D: the dark upper path behind the hut | — | — | Crossed by the upper patrol loop |

- **Cover:** channel walls, tailings, flume trestles, the hut, stacked sluice boards, and reed clumps at the ponds.
- **Sightlines:**
  - From the top of the cut face you see the whole slope and the foundry roofs, a 160 m establishing vista.
  - The flume guard has a 50 m straight line along the boardwalk.
  - The drone's 30° searchlight crosses the flume and ponds.
- **Lights:** two kagaribi (at the pond and the hut), which can be put out by smothering them with sand. One alien floodlight on the hut has a cable junction at its base; an arrow to the junction cuts the light for 10 s.
- **Entry and exit:** start at `ps_ch05_kanna_ridge` (+222, −20, +38); exit at `vol_ch05_culvert`.
- **Collectible:** `ch05.c01` is chalked on a sluice board at the middle basin.

**`pl_itotoriba` 糸取場 (Reeling shed): start of b03. Hall sublevel, east of the yard.**

- **Shell:** a 20 × 18 m timber shed (x +26…+46, y −30…−12) with an earth floor. Eaves are at 3.2 m and the ridge at 7.5 m, with a steam vent along the ridge.
- **Work floor:** 12 reeling stations in two rows. Each has a cocoon pot (煮繭鍋) on a clay brazier with a cyan levy meter. There are cocoon trays on shelves and baskets of mulberry leaves.
- **Sleeping loft:** over the east half at +2.4 m, reached by a ladder (NE) and a stair (SE). The six captives sleep here, collared to a cyan tether line.
- **Entry:** the player climbs out of the culvert trough at the SE corner.
- **Doors:** a west door to the yard edge and a south door at (+34, −30) to the south lane.
- **Guards inside:** none (the overseer has been called to the yard). A drone passes the ridge vent every 30 s and throws slatted light across the loft; staying out of the light bars is the cue.
- **Collectible:** `ch05.c02` (seizure notice) is on the overseer's desk by the west door.

**Escort route `spl_ch05_escort_refuge`: b03, about 168 m.**

| Segment | From → to | Length | Threat | Hide spot |
|---|---|---|---|---|
| S1 | Reeling-shed south door (+34,−30) → drying racks (+10,−32) | 24 m | Drone `p_drying_drone` loops over the racks at 8 m (24 s cycle) | `hs_drying_racks`: soft cover, bamboo racks 1.8 m high |
| S2 | → water troughs (0,−30) → storehouse NE corner (−8,−30) | 18 m | Pair `p_south_pair` walks the south lane between x −20 and +20 (40 m, 30 s each way) | `hs_troughs`: 0.9 m |
| S3 | Along the storehouse's north wall → (−56,−28) | 48 m | Pair (far end) | — |
| S4 | North up the west lane (x −56) to (−56,+20) | 48 m | `p_west_gate`: a blade retainer pacing 12 m at the lane gate (−56,−6) | `hs_lumber` (−56,−12), `hs_fuel_leanto` (−54,+10) |
| S5 | → charcoal bales (−40,+26) → refuge door (−28,+31) | 30 m | None; the takadono smoke hides the apron | `hs_charcoal_bales` |

**`pl_sumigoya` 炭小屋 (Charcoal shed, the refuge): end of b03 and all of b04.** This is a proposed new place id.

- A 12 × 10 m low shed at the west end of the charcoal apron (x −28…−16, y +26…+36), with the tatara hall's west wall 6 m away.
- Charcoal bales (炭俵) are stacked floor to rafter on three walls. One andon lights it. The ambience is warm and charcoal-dusty.
- **Supply point** `sup_ch05_sumigoya` is a tool rack for loadout changes.
- Okinu's naginata is hidden inside a hollowed bale stack.

**`pl_hataba` 機場 (Loom hall): b05 and b11. Hall sublevel; the existing `SilkFoundryLoom` is dressed here.**

- **Shell:** 30 × 18 m (x +26…+56, y −6…+12), eaves 4.5 m. 連子窓 slatted windows on the south wall throw moon bars. An overseer gallery runs the full north wall, 1.5 m deep at +2.5 m, with a stair at the NE corner.
- **Looms:** 24 高機 in 4 rows of 6, each 3.2 × 1.95 × 2.26 m.
  - E–W row aisles are 1.8 m wide, and a perimeter aisle is 2.4 m.
  - A central N–S cross aisle 3 m wide runs at x +41.
- **East end:** Okinu's 空引機 draw loom at (+52, +3), 4.2 m tall with the drawboy's seat at +2.2 m, and the overseer's office (4 × 6 m).
- **Floor props:** indigo vats (藍甕, 1.0 m) by the south door, and silk-skein racks.
- **Doors:** a 4 m west door at (+26, +3) to the yard, and a 2 m south door at (+40, −6) toward the reeling shed. The roof vent at (+41, +3, +8) is the drone entry.
- **Cover:** looms (hard), vats (low), skein racks (soft), and the gallery balustrade.
- **Sightlines:** each row aisle is a 26 m E–W line, and the cross aisle is the only N–S line. The gallery sees everything, which makes the gallery rifle the priority yumi target.
- **Polearm rule:** loom frames block polearms. A naginata sweep in a 1.8 m row aisle clips the frame and bounces off (0.3 s). Thrusts along the aisle reach normally, and full sweeps work in the cross and perimeter aisles.

**`pl_takadono` 高殿 (Tatara hall): b06, b07 and the b16 boss arena. New interior.**

- **Shell:** 26 × 20 m (x −13…+13, y +34…+54), ridge 14 m, eaves 5.5 m. The board-and-bark roof has a 6 × 4 m ridge smoke vent (煙出し) over the furnace. The floor is earth.
- **Furnace (釜):** a clay box furnace 3.0 m long (E–W), 1.0 m wide and 1.2 m high at (0, +44). It has a row of tuyères (ほど穴) along each long side and tapping holes at both ends.
- **Channels (湯路):** four stone-lined channels, 0.6 m wide and 0.3 m deep.
  - C1 → NW slag pit (−12, +50)
  - C2 → SW slag pit (−12, +38)
  - C3 → east door and on to the casting floor (+13, +48)
  - C4 → SE slag pit (+12, +38)
  
  Each channel head has an alien graphite gate, Tarifa's addition.
- **Foot bellows (踏鞴):** two platforms, north (y +46.5…+48.5) and south (y +39.5…+41.5). Each is 3.5 × 2.0 m and 0.6 m high, with a rocking tread board. **No seesaw 天秤鞴** (bible §15.2).
- **Floor props:** charcoal bins on the west wall and iron-sand bins on the east wall. Three clay repair tubs sit at (−6,+41), (+6,+41) and (0,+51). A small shrine shelf (神棚) to 金屋子神 is on the north wall, empty: the scroll was seized (see `ch05.c04`).
- **Alien gantry deck (+3.0 m):**
  - The perimeter deck is 3 m wide on the N and S sides and 2 m on the E and W.
  - Two N–S cross-bridges at x −4 and x +4.
  - An 8 × 5 m central void over the furnace.
  - Four heat slots (1.2 × 4 m grating gaps) directly over channel runs C1–C4.
  - Access: NW stair (−11,+52), SE stair (+11,+36), NE ladder (+12,+52).
- **Doors:** a 5 m south door at (0,+34), a 3 m east door at (+13,+48), and a small west door at (−13,+40).
- **Cover:** bellows platforms, bins, gantry stanchions, and the furnace itself (contact deals 10 damage/s).
- **Boss changes (b16):** the arena volume `vol_takadono_boss` locks the whole hall, including the gantry. At phase 3, the vent and a 6 × 6 m section of roof boards tear away. Rain falls as a column over the central void and slots C1 and C3.

**`pl_okaji` 大鍛冶場 (Refining forge): b08, b09 and `ch05.c06`. Hall sublevel, west of the yard.**

- **Shell:** 24 × 20 m (x −52…−28, y −4…+16), open on the yard side under a lean-to.
- **Refining floor:** two refining hearths with box bellows, three anvils, a 2 × 0.8 m quench tub (水舟), tong racks and pig-iron (銑) stock.
- **NE bay (−34, +12):** a 小鍛冶 bay with Kōzō's hearth and anvil. Arrowheads are made here.
- **SE bay (−34, −1):** Tetsugorō's gunsmith bench, with a vise, a barrel-stock rack and a crate of captured alien coils.
- **Kindling pile** by the west hearth (−48, +6), made of seized paper: `ch05.c06`.
- **Supply point** `sup_ch05_okaji` is at the tool rack (−30, +6).

**`pl_silk_foundry` 中庭 (Foundry yard = arena 2): b10, b17 and b18.**

- **Surface:** 48 × 48 m of packed earth with a stone drain. The kernel boxes are dressed as in §1.4.1.
- **Lanes:**
  - west lane x −24…−11;
  - centre x −9…+9;
  - east lane x +11…+24.
  
  They join north of y +12 and south of y −12.
- **Campaign-only props:**
  - The quota board ◆ at (0, −14): a 3 × 2 m alien slab on a post, facing north.
  - Water troughs (0.9 m) and handcarts.
  - Two existing `SM_Nyaagyu_CargoStack` sets at (−18, +16) and (+18, −16).
- **Openings:**
  - The south lane (sp_yard_south_gate at (0,−26)), with its east end toward the river-landing path (+18,−26).
  - The charcoal apron to the north.
  - The NW apron gate (−24, +28), which is the upriver pack road; the League arrives here in b10.
- **Sightline:** in b10, a marksman on the reeling shed's ridge (+36, −21, +7.5) covers the east lane and the centre to the forge front, about 65 m on the diagonal. The west stack wall and the low barriers break the line.
- **Nobori pole** for b18: a 6 m pole with 乳 loops at (0, +22).

**`pl_aratamejo` 改め所 (Inspection hall): b12 and the b17 pickups. Hall sublevel.**

- **Shell:** 16 × 16 m (x −46…−30, y −26…−10), raised wooden floor (+0.5 m) with an earthen 土間 entry, and shōji along the east side.
- **Roof:** kawara with SORA eave caps. In the fiction this was the Nyaagyu domain's ironworks office (鉄山役所) before the invasion, which is why it carries the house mon.
- **Ceremony props:** a 6 × 1 m long table, balance scales (天秤), a soroban, the registry box, the tally box (割符箱), a lots box (籤箱), and a brazier holding the SORA brand iron.
- **Staging:** 30 freed workers stand on the 土間 and in the yard beyond; the camera favours paws and faces.

**`pl_toritategura` 取立蔵 (Levy storehouse): b13.** This is a proposed new place id.

- A 12 × 10 m two-storey 土蔵 (x −20…−8, y −40…−30) built from the existing kura kit. The heavy doors are open because the alien lock burned out in the uprising.
- **Ground floor:** shelves of levy ledgers (slates and paper), seized goods under glowing cyan alien tags, and the clerk's desk.
- **Upper floor** (0.8 m stair): crated heirlooms, the output book, and a window over the SW ridge where the storm front comes in.
- **POIs:**

  | POI | Floor | What it is |
  |---|---|---|
  | `poi_quota_sheet` | Ground (desk) | Quota sheet |
  | `poi_washio_notice` | Ground (desk) | Washio transfer notice; collectible `c03` |
  | `poi_arrow_cache` | Ground | Arrow cache |
  | `poi_kanayago_scroll` | Upper | Kanayago scroll; collectible `c04` |
  | `poi_output_book` | Upper | Output book; collectible `c05` |
  | `poi_storm_window` | Upper | Storm window; vista |

**`pl_imonoba` 鋳物場 (Casting floor): b14 and b15. New interior.**

- **Shell:** 20 × 16 m (x +13…+33, y +38…+54), joined to the tatara hall's east door at (+13, +48).
- **Channels:** four E–W casting channels fed from the tapping line. Each has an alien gate at its head that cycles every 12 s: a 2 s amber glow ramp, then 5 s of flow.
- **Floor:** three rows of sand casting beds (0.4 m) with plank walkways 0.6 m high between them. Ingot stacks (1.5 m) and crucible stands give cover.
- **Tarifa's gantry** runs along the north wall at +3 m (b14 vantage).
- **Spawns:** `sp_imonoba_east_gate` (+33, +46) is where the automata walk in from the loom hall; also `sp_imonoba_gantry` and `sp_imonoba_south_door` (+23, +38).
- **Exit:** back through the east door into the tatara hall (b16).
- **Rain:** after b14, water leaks through a split roof. Where it hits the channel lips it hisses; this is visual only in b15 and becomes steam in b16.

**Pack-horse stand (`pl_silk_foundry`, south lane): b17.**

- Two pack horses (駄馬), a bay and a chestnut native horse about 130 cm at the withers, at (−4…+8, −28…−34). They wear 荷鞍 pack saddles, 腹帯, 鞦 and straw 馬沓, with a hitching rail and a mounting block.
- **Dropoffs:** `pack_horse_valley` (+2, −28) and `pack_horse_ward` (+10, −28).
- **Pickups:**
  - `pk_aratamejo_arrowheads` and `pk_aratamejo_carbines` at the inspection-hall steps (−30, −18);
  - `pk_okaji_coils` at (−28, +2);
  - `pk_storehouse_silk` at (−14, −30).
- The route totals about 264 m of carrying at 0.8× walk, about 95 s.

#### 1.4.4 Volumes, spawns, player starts, patrols

| Kind | Ids (place) | Notes |
|---|---|---|
| Zone and bounds volumes | `vol_ch05_kanna` 160×36×40 m; `vol_ch05_hataba` 30×18×6; `vol_takadono` and `vol_takadono_boss` 26×20×14; `vol_ch05_okaji` 24×20×6; `vol_ch05_yard` 48×48×10 (arena footprint); `vol_ch05_storehouse` 12×10×7; `vol_ch05_imonoba` 20×16×8 | Beat bounds and arena lock |
| Noise volumes | `vol_kanna_channel_main`, `vol_kanna_channel_east` (0.9 m spline volumes, running water ×0.5), `vol_kanna_tailings` (2 × 12×6 m, gravel ×1.5), `vol_kanna_pond_edge` (1.5 m ring, puddle ×1.3), `vol_ch05_culvert` (running water) | b02 |
| Trigger volumes | `vol_kanna_laborers` (r 6 m), `vol_kanna_laborers_near` (r 2.5 m), `vol_ch05_culvert` (b02 exit), `vol_itotoriba_loft`, `vol_refuge` (b03 complete), `vol_poi_quota_sheet`, `vol_poi_washio_notice`, `vol_poi_kanayago` (r 1.5 m) | Dialogue and completion |
| Enemy spawns | `sp_kanna_hut`, `sp_kanna_shovel_a/b`, `sp_south_gate_inner`, `sp_hataba_office`, `sp_hataba_gallery`, `sp_hataba_south_door`, `sp_hataba_west_door`, `sp_hataba_roof_vent`, `sp_takadono_south_door`, `sp_takadono_west_door`, `sp_takadono_gantry_ne`, `sp_takadono_vent`, `sp_yard_south_gate`, `sp_yard_river_gate`, `sp_yard_river_air`, `sp_itotoriba_roof_ridge`, `sp_imonoba_east_gate`, `sp_imonoba_gantry`, `sp_imonoba_south_door` | See each beat |
| Player starts (checkpoints) | `ps_ch05_kanna_ridge` (b02), `ps_ch05_itotoriba_trough` (b03), `ps_ch05_refuge` (b04), `ps_ch05_hataba_west` (b05, b11), `ps_ch05_takadono_bellows` (b06, b07), `ps_ch05_okaji` (b08, b09), `ps_ch05_yard_forge` (b10), `ps_ch05_aratamejo_door` (b13), `ps_ch05_imonoba_south` (b15), `ps_ch05_takadono_south` (b16 and its phases), `ps_ch05_yard_north` (b17) | One per checkpointed beat |
| Patrol splines | `pr_kanna_upper_loop` (60 m loop, 45 s), `pr_kanna_flume_line` (50 m linear, 35 s each way with 5 s look-outs), `pr_kanna_pond_loop` (45 m, 40 s), `pr_kanna_air_figure8` (drone at 8 m, 30 s), `pr_south_lane` (40 m, 30 s each way), `pr_drying_racks` (drone loop, 24 s), `pr_west_lane_gate` (12 m beat) | Speeds from L2 defaults |
| Supply points | `sup_ch05_sumigoya` (after b04), `sup_ch05_okaji` (b08–b10), `sup_ch05_yard` (b17) | Diegetic registry depots (bible §11) |

---

## 2. Beats

### 2.1 Beat list

| Beat | Type | Place | Min | CP | Site | Unlocks | Registry | Title (JA / EN) |
|---|---|---|---|---|---|---|---|---|
| ch05.b01 | cinematic | pl_silk_foundry | 2.0 | ✓ | | | | 絹の工房 / The Silk Foundry |
| ch05.b02 | stealth_zone | pl_kanna_nagashi | 4.0 | ✓ | | | | 鉄穴の水路を抜けよ / Slip through the iron-sand channels |
| ch05.b03 | production_task · escort | pl_itotoriba → pl_sumigoya | 5.0 | ✓ | 0 | | | 職人を解き放ち、炭小屋へ導け / Free the craftspeople and lead them to the charcoal shed |
| ch05.b04 | dialogue | pl_sumigoya | 1.5 | ✓ | | weapon 20 | | 炭小屋の談合 / Council in the charcoal shed |
| ch05.b05 | combat_wave | pl_hataba | 5.0 | ✓ | | | | 機場を取り戻せ / Take back the loom hall |
| ch05.b06 | production_task · crank | pl_takadono | 4.0 | ✓ | 1 | | | 踏鞴を踏み、炉を保て / Tread the bellows and keep the furnace alive |
| ch05.b07 | production_task · defend | pl_takadono | 5.0 | ✓ | | | | 炉と村下を守れ / Defend the furnace and the master smelter |
| ch05.b08 | production_task · manufacture | pl_okaji | 4.0 | ✓ | | weapon 8 (+ proposed `hammer_rhythm`) | 鏃 24本 | 鏃を打て / Forge arrowheads |
| ch05.b09 | production_task · manufacture | pl_okaji | 3.0 | ✓ | | weapon 1 | アーク・カービン 3挺 | アーク・カービンを組め / Assemble the Arc Carbine |
| ch05.b10 | combat_wave | pl_silk_foundry | 3.0 | ✓ | | | | 反撃を退けよ / Repel the counterattack |
| ch05.b11 | production_task · manufacture | pl_hataba | 2.0 | ✓ | | | 絹幟 1旒 | 空紋の幟を織れ / Weave the Sora banner |
| ch05.b12 | cinematic | pl_aratamejo | 2.5 | ✓ | 2 | | (tallies b08, b09, b11) | 初めての割符 / The first tally |
| ch05.b13 | explore_optional | pl_toritategura | 2.5 | ✓ | | | | 取立蔵を調べる / Search the levy storehouse |
| ch05.b14 | cinematic | pl_imonoba | 1.5 | — | | | | 湯路、全開 / The channels open |
| ch05.b15 | combat_wave | pl_imonoba | 4.0 | ✓ | | | | 鋳物場を突破せよ / Cross the casting floor |
| ch05.b16 | boss | pl_takadono | 7.0 | ✓ + per phase | | | | 工房監督官タリファを倒せ / Defeat Foundry Overseer Tarifa |
| ch05.b17 | production_task · carry | pl_silk_foundry | 2.0 | ✓ | | | — | 荷を駄馬に積め / Load the pack horses |
| ch05.b18 | cinematic | pl_silk_foundry | 2.0 | — | | | | 夜明けの幟 / Banner at dawn |

`requires` is the previous beat by default. The exceptions are b13 (optional; requires b12) and b14 (requires b12, so skipping b13 is allowed).

**Enemy budget** (from the beat data; the boss's adds are listed separately):

| Enemy | Count | Where |
|---|---|---|
| `enforcer_rifle` | 28 | b02 3, b03 2, b05 6, b07 7, b10 6, b15 4. Up to 4 more if the b02 alarm or b03 detection fires |
| `blade_retainer` | 6 | b03 1, b05 2, b07 2, b15 1 |
| `shield_enforcer` | 3 | b05, b07, b10 |
| `grenadier` | 4 | b07 2, b10 1, b15 1 |
| `marksman` | 1 | b10 |
| `drone` | 8 | b02, b03, b05, b06, b07 ×2, b10 ×2 |
| `bound_conscript` | 3 hostile, non-lethal | b05 |
| `bound_conscript` "witnesses" | 2 | b02; they never attack |
| `loom_automaton` | 4 | b15; the boss adds 4 more in P2 |
| Boss | 1 | `boss_tarifa` |

### 2.2 Beat details

**ch05.b01: cinematic, 2.0 min, checkpoint (chapter start).**

- **Sequence:** `LS_Ch05_B01_QuotaBoard`, skippable, with a letterboxed `camera_blend` fallback.
- **Shots:**
  1. The ridge above the foundry at night: Kohagi and Nyaakoto in the grass, heat lightning far off. Below, smoke rises from the tatara vent and cyan floodlights and kagaribi dot the slope.
  2. Inside the reeling shed: collared paws in steaming cocoon water, levy meters ticking.
  3. Tarifa's PA voice with an insert of the quota board: 「目標稼働率 140% / 現在 98%」.
  4. **Humor beat #3, as approved in the bible:** the 「昼寝禁止」 notice is pasted on a pillar. A collared reeler passes under it and her ears flatten. No line is spoken.
  5. Back on the ridge, Kohagi points to the channels.
- **End state:** `ps_ch05_kanna_ridge`, with katana and yumi equipped. Kohagi is an invulnerable companion for b02–b03.
- **Lines:** 5 (§3.3).

**ch05.b02: stealth_zone, 4.0 min, checkpoint.**

- **Guards:**

  | Guard | Type | Patrol | Sight (cone / range / in dark) | Hearing |
  |---|---|---|---|---|
  | `g_kanna_upper` | `enforcer_rifle` | Upper loop | 90° / 22 m / 9 m | 12 m |
  | `g_kanna_flume` | `enforcer_rifle` | Flume line | 90° / 22 m / 9 m | 12 m |
  | `g_kanna_pond` | `enforcer_rifle` | Pond loop | 90° / 22 m / 9 m | 12 m |
  | `g_kanna_air` | `drone` | Figure-eight at 8 m, searchlight | 30° / 25 m / 25 m | 6 m |
  | `g_kanna_laborer_a`, `_b` | `bound_conscript` "witnesses" | Static, shovelling | 60° / 6 m / 4 m | 3 m |

- **The witnesses** look away and never attack. Their **collars** report, at 0.5× suspicion. This is the chapter's quiet idea: the collar sees, the worker does not.
- **Detection:** L2 states, `suspicion_rate` 1.0/s at close range, falling off with distance and darkness; `alert_threshold` 1.0; `search_s` 20. After a search the guard returns to unaware and barks "booking as a loss."
- **Noise radii:** crouch 2.5 m, walk 6 m, run 12 m. Running water ×0.5, gravel ×1.5, pond edge ×1.3.
- **Lights:** two braziers (hold for 1.5 s to smother) and one floodlight (arrow the cable junction to cut it for 10 s).
- **`on_detected: reinforce:w_kanna_alarm`:** two `enforcer_rifle` come out of the hut and the drone switches to dropping seizure nets. On Easy, detection falls back to `combat`. There are no `tsubute` lures yet (ch06).
- **Takedowns:** rear takedowns are on and lethal by default against enforcers. Conscripts are always non-lethal.
- **Complete:** `exit_reached` at `vol_ch05_culvert`.
- **Fail:** death sends you back to the checkpoint.
- **Unlocks:** none; stealth, takedown and seal-cut come from ch03.
- **Prompts:** `ui.ch05.tut.01`–`04`.

**ch05.b03: production_task · escort, 5.0 min, checkpoint, site 0.**

- **Pre-phase** (`x_ext.pre_interacts`): seal-cut six collars in the loft, holding 2 s each, while staying out of the drone's slatted light bars.
- **Escort:**

  | Parameter | Value |
  |---|---|
  | NPCs | Okinu, Tetsugorō, reelers A/B/C, bellows boy (6) |
  | Path | `spl_ch05_escort_refuge` (168 m) |
  | Speed | 180 cm/s crouch-walk |
  | `wait_for_player_cm` | 800 |
  | `hide_on_signal` | yes, 5 hide spots |
  | NPC health | 120 HP; downed NPCs revive in 4 s |
  | `fail_on_npc_death` | true |
  | `stealth` | true (progress pauses while any patrol has line of sight on the group) |

- **Patrols:**
  - `p_south_pair`: 2 × `enforcer_rifle`, 90° / 20 m.
  - `p_drying_drone`: 1 × `drone`.
  - `p_west_gate`: 1 × `blade_retainer`, 100° / 16 m.
- **If detected** (`x_ext.on_detected: combat`): the group hides where it stands, and 2 × `enforcer_rifle` come from `sp_south_gate_inner`. Clear them and the escort resumes.
- **Complete:** all six inside `vol_refuge`. This fires `site_restored:0` (職人の避難所).
- **Fail:** death, or the death of an escorted NPC, sends you back to the checkpoint.

**ch05.b04: dialogue (ambient, `soft_lookat`), 1.5 min, checkpoint.**

- **Line gates:** after line 001 an interact prompt hands over the naginata; this unlocks **weapon 20** and plays lines 002–005. After line 005 comes a seal-cut prompt on Kōzō's collar (he came in to fetch charcoal); this plays lines 006–009.
- **Supply point:** the polearm slot now defaults to the naginata.
- **Off-screen:** from here the freed workers cut the remaining collars with shears and chisels (crowd animation).
- **Nine lines.** They include catalog anchor 1 and two bible lines (§6.2 「三晩かかる。今夜しかない。」 and §2.3 「わしは鉄しか信じん。」).

**ch05.b05: combat_wave, 5.0 min, checkpoint.**

- **Bounds:** `vol_ch05_hataba`.
- **Waves:**

  | Wave | Trigger | Enemies (spawn) |
  |---|---|---|
  | W1 | `start` | `blade_retainer` ×2 (office), `enforcer_rifle` ×2 (gallery) |
  | W2 | `alive_below:2` | `bound_conscript` ×3 (south door), `enforcer_rifle` ×2 (west door) |
  | W3 | `prev_cleared` | `shield_enforcer` ×1 (west door), `enforcer_rifle` ×2 (gallery), `drone` ×1 (roof vent) |

- **Allies:** Okinu (naginata) and four weavers who smash levy meters. All are downable.
- **Rules:** `nonlethal_types: [bound_conscript]`, `max_alive` 6, `all_waves_cleared`.
- **Design:** this is the first naginata fight, and the looms teach its limits. It sweeps freely in the cross and perimeter aisles, catches on frames in the row aisles, and thrusts along them. The gallery rifles are for the yumi. Okinu shields the conscripts, so seal-cut them.
- **Fail:** death.

**ch05.b06: production_task · crank (foot bellows), 4.0 min, checkpoint, site 1.**

- **Crank parameters:**

  | Parameter | Value |
  |---|---|
  | Actor | `tatara_bellows_south` |
  | `turns_required` | 90 (one turn = one left + right tread) |
  | `turn_rate_band` | [0.8, 1.3] turns/s |
  | `progress_decay_per_s` | 0.01 when out of band or idle |
  | `stamina_per_turn` | 2 |
  | `interruptible` | yes |
  | `coop_npc` | Bellows boy: 0.5 turns/s, counted at 40% while the player is away |

- **Flame gauge** (color plus notch shape, so it is readable without color):

  | Rate | Flame | Notches | Effect |
  |---|---|---|---|
  | Below band | Dull red | 1 | — |
  | In band | Golden 山吹 | 2 | — |
  | Above band | White with sparks | 3 | Stamina cost ×2 |

- **Wave:** at `progress_at:0.6`, one `drone` enters by the vent. If you ignore it, it nets the bellows boy and his co-op stops until freed.
- **Complete:** fires `site_restored:1` (絹と鋼の炉).
- **Time:** about 90 s of treading, plus tutorial and the drone.

**ch05.b07: production_task · defend, 5.0 min, checkpoint.**

- **Targets:** the furnace (1500 HP) and Kōzō (300 HP; downable, revives in 4 s). The beat fails if he stays down for more than 25 s.
- **Duration:** 180 s. `fail_on_target_destroyed: true`.
- **Repair:** three clay tubs, each usable once. Hold for 3 s to restore 150 HP to the furnace.
- **Waves** (`max_alive` 6):

  | Trigger | Enemies (spawn) |
  |---|---|
  | `start` | `enforcer_rifle` ×3 (south door) |
  | `after_s:40` | `grenadier` ×1 (NE gantry) + `blade_retainer` ×2 (south door) |
  | `after_s:90` | `drone` ×2 (vent) + `enforcer_rifle` ×2 (west door) |
  | `after_s:130` | `grenadier` ×1 (NE gantry) + `shield_enforcer` ×1 + `enforcer_rifle` ×2 (south door) |

- **Grenadiers** target the furnace. Their visible arc decal and the captioned bark 「区画を清算します。」 are the counterplay cue.
- **Drones** net the bellows crew. While the crew is netted, the furnace loses 5 HP/s.
- **Fail:** the furnace is destroyed, Kōzō is down for 25 s, or the player dies.

**ch05.b08: production_task · manufacture (arrowheads), 4.0 min, checkpoint.**

- **Weapon 8** (the forge hammer, a striker's sledge) is granted at beat start (`x_ext.weapon_grant_at`).
- **Stations:** the kokaji hearth, Kōzō's anvil, the quench tub.
- **Steps:**
  1. Heat ×4: hold the bar in the hearth until it glows 山吹, 2 s.
  2. `hammer_rhythm` ×4 phrases of 8 strikes. Kōzō's small-hammer tap is the cue; strike 600 ms later, ±90 ms. Passing a phrase needs 6 of 8 strikes. A failed phrase simply repeats, with no penalty.
  3. Quench ×4.
  4. Inspect ×1: count the 24 heads on the tray.
- **Output:** 24 尖根 arrowheads. The quiver refills to 12, with 12 more held at the supply rack.
- **Registry:** 鏃 24本. **Unlocks:** weapon 8. The `manufacture` flag is already unlocked at ch01.b09; `x_ext.proposed_mechanic_flag: hammer_rhythm` is offered in case L1 wants a flag for the rhythm variant (§6 item 3).
- **Collectible:** `ch05.c06` is in the kindling pile. Picking it up plays Sekireisai's memory line.

**ch05.b09: production_task · manufacture (Arc Carbine), 3.0 min, checkpoint.**

- **Stations:** gunsmith bench and vise.
- **Steps:**
  1. Inspect: sight down the bore against a lamp.
  2. Assemble: seat the captured coil (align, hold 1.5 s).
  3. Assemble ×2: the left and right receiver plates, which carry the SORA mon (they match the existing asset).
  4. Inspect: dry-fire check.
- **Output:** 3 carbines. In the fiction the player builds one and Tetsugorō finishes two.
- **Registry:** アーク・カービン 3挺. **Unlocks:** weapon 1.
- The coil's glow is re-tinted League jade (bible §15.1: no cyan on League objects).

**ch05.b10: combat_wave (yard), 3.0 min, checkpoint.** The Arc Carbine goes into the firearm slot at the start.

- **Waves:**

  | Wave | Trigger | Enemies (spawn) |
  |---|---|---|
  | W1 | `start` | `enforcer_rifle` ×4 (south gate) |
  | W2 | `alive_below:2` | `marksman` ×1 (reeling-shed ridge; 900 ms lock glint), `drone` ×2 (river air) |
  | W3 | `prev_cleared` | `shield_enforcer` ×1 (south gate), `enforcer_rifle` ×2 + `grenadier` ×1 (south lane, east end) |

- **Allies:** Tetsugorō (Arc Carbine). With W3, Otane (kusarigama) and two League 鉄砲 (coil matchlocks) join through the NW apron gate. All are downable.
- **Complete:** `all_waves_cleared`. Oyuki arrives with the registry box. Diegetically she now enters the b08 and b09 counts; the registry toasts have already fired at those beats' completion.

**ch05.b11: production_task · manufacture (sorabiki weave), 2.0 min, checkpoint.**

- **Station:** Okinu's 空引機. The player sits in the drawboy's seat.
- **Steps:**
  1. Inspect: find 3 broken figure cords.
  2. `weave_rhythm` ×24 picks: pull the cords on Okinu's call, 750 ms, ±120 ms.
  3. Inspect: unroll the cloth and the mon rises on the face.
- **Output:** 1 nobori. **Registry:** 絹幟 1旒.
- **Fiction:** the banner has been growing on this loom for forty nights, one pick at a time, under the levy meter. Tonight only the final field is woven (§4.4).

**ch05.b12: cinematic, 2.5 min, checkpoint, site 2: the first XOR.**

- **Sequence:** `LS_Ch05_B12_FirstXOR`.
- **Shots:**
  1. Oyuki opens the registry and reads Article 1.
  2. Lots are drawn from the 籤箱, and the lot names Nyaakoto as inspector.
  3. Each maker declares their goods, and Otane declares as receiver.
  4. Nyaakoto counts all 24 arrowheads aloud.
  5. The carbines and the banner are declared.
  6. The brand iron comes out of the brazier. It is **branded across the split line** of each 割符, split with a wedge, and the halves go to maker and receiver.
  7. Three seals go on each registry entry: Nyaakoto's 花押, Kōzō's 爪印 and Otane's 印.
  8. Oyuki's explanation. Kōzō's turn. Anchors 2 and 3.
  9. **Last shot:** Oyuki pastes the registry page over the yard quota board's "140%" (Article 5, 帳は民の前に). The board's scanner glints cyan behind the paper, which sets up b18.
- **Interaction:** one player press on the brand. It cannot fail.
- **Site:** `site_restored:2` fires at the end of the sequence or on skip.
- **Registry UI:** the b08, b09 and b11 entries show three-seal split-tally icons.

**ch05.b13: explore_optional, 2.5 min, checkpoint (optional; requires b12).**

- **Volume:** `vol_ch05_storehouse`. There are no map markers; lamplight and the storm window draw the eye.
- **POIs:** quota sheet (lore), Washio transfer notice (lore, collectible `c03`), arrow cache (+12 arrows, +48 carbine rounds), Kanayago scroll (heirloom `c04`), output book (registry page `c05`), storm window (vista).
- `exit_hint_after_s: 150`.

**ch05.b14: cinematic, 1.5 min, no checkpoint (b12 or b13 precedes it; the next checkpoint is b15, within 240 s).**

- **Sequence:** `LS_Ch05_B14_ChannelsOpen`.
- **Shots:**
  1. Tarifa on the casting-floor gantry, polite and thankful.
  2. Oyuki quotes Article 5 back at her.
  3. Tarifa's tether snakes into the loom hall and four looms stand up as automata.
  4. The channel gates open, the melt floods the casting beds, and the first thunderclap breaks as the rain arrives.
- **End state:** `ps_ch05_imonoba_south`.

**ch05.b15: combat_wave, 4.0 min, checkpoint.**

- **Waves** (`max_alive` 5):

  | Wave | Trigger | Enemies (spawn) |
  |---|---|---|
  | W1 | `start` | `loom_automaton` ×1 (east gate, the teaching unit), `enforcer_rifle` ×2 (gantry) |
  | W2 | `prev_cleared` | `loom_automaton` ×2 (east gate), `blade_retainer` ×1 (south door) |
  | W3 | `alive_below:1` | `loom_automaton` ×1, `grenadier` ×1 (gantry), `enforcer_rifle` ×2 (south door) |

- **Hazard:** four molten channels on a 12 s cycle (2 s amber glow ramp, then 5 s of flow). The player takes 35 damage/s plus a 2 s burn.
- **Environmental kills count.** Automata caught in the flow are destroyed; other enemies take 60 damage/s.
- **Fail:** death.

**ch05.b16: boss `boss_tarifa`, 7.0 min, checkpoint plus a checkpoint at each phase.** See §2.3. `defeat: kill`; the outro shows the fall.

**ch05.b17: production_task · carry, 2.0 min, checkpoint.**

- **Carry:** 4 loads, katana one-handed only, 0.8× speed, `drop_on_hit: false`. There is no combat.
- **Routing:**
  - arrowheads, carbines and captured coils → `pack_horse_valley` (Hidden Valley);
  - returned levy silk → `pack_horse_ward` (Lantern Ward).
- **No registry entry.** These goods were entered at b08, b09 and b11 and tallied at b12, and the silk is returned levy silk, not new production. Entering them again would break Article 1.
- **Supply point:** `sup_ch05_yard`.

**ch05.b18: cinematic, 2.0 min, no checkpoint (chapter end).**

- **Sequence:** `LS_Ch05_B18_NoboriDawn`.
- **Shots:**
  1. The third night's bloom (鉧) is levered out of the broken furnace.
  2. The nobori goes up on the pole.
  3. **Proposed humor beat:** two freed reelers asleep in the first sunbeam, directly under the 「昼寝禁止」 notice. Kohagi: 「……起こすな。」 This echoes Baiō's sunbeam in ch01.
  4. The quota board flickers. Its cyan numerals rearrange into Japanese, and Iota speaks through its grille.
  5. A slot in the board's base ejects a palm-sized **message slate** and Kohagi catches it. This is the twin slate that carries Iota's secret message and his voice in ch06.b01–b05 (see the ch06 script).
  6. Oyuki weighs the risk. Nyaakoto looks downriver toward the citadel.
- **Then:** the chapter-complete screen shows the **ch05 registry page** instead of a score.

### 2.3 Boss: Foundry Overseer Tarifa (`boss_tarifa`, ch05.b16)

- **Look (bible §6.3):** a soot-stained grey coat, goggles, a tether-cable on the right arm, and a process rod (工程棒) in the left paw.
- **Coolant mantle (冷却外套):** a heat-shield field that lets her stand on the channel lips.
  - While it is up, she takes **70% less damage** from every source.
  - It drops for **4 s** after a snapped-cable stun (P1–P3) or when she is caught in a steam burst (P3).
  - This is deliberately not a ch07 energy shield. There is no `shield_break` here; that flag stays in ch07.
- **HP:** 3000 on Normal; L3 tunes it.
- **Windups:** Easy (稽古) +30%, Hard (免許皆伝) −15%.
- **Telegraph palette:** cyan for the locked tether aim; amber for sweeps, rings and channels. Every damage source is preceded by at least its windup, and every signature attack has a captioned bark or captioned SFX.

| Phase | Attack | Windup | Active | Recovery | Damage | Telegraph | Counterplay | Bark |
|---|---|---|---|---|---|---|---|---|
| P1 100–65 | Tether lash | 700 ms | 250 | 900 | 12 + pull 4 m toward the nearest open heat slot | Cyan filament locks on | **Awase** (260 ms) snaps the cable: 2.0 s stun and mantle down for 4 s. Guard halves the pull. A 転 sidestep avoids it | 「引き当てます。」 |
| P1 | Rod sweep | 500 ms | 450 (2 hits) | 800 | 28 ×2, reach 2.6 m | Amber arc | Guard both hits. Awase on the second hit → 1.2 s stagger | 「休憩は計上されません。」 |
| P1 | Quota slam | 900 ms | 200 | 1100 | 40 + knockback 2.5 m | Amber ring, 3 m | Step out and punish the recovery | [captioned impact SFX] |
| P1 | Channel cycle (arena) | 2000 ms glow ramp | 5000 flow | — | 35/s in the channel; 20/s heat column over its deck slot | Amber pulse on the gate and slot | Read the glow; stand on the bridges | 「稼働率百四十パーセント。」 |
| P2 65–30 | Double lash | 700 ms, then a second 700 ms lash 500 ms into the first's recovery | 250 | 900 | 12 + pull, twice | Two cyan locks | Awase either lash to snap the cable | 「増産体制に移行いたします。」 (phase), then 「引き当てます。」 |
| P2 | Adds | — | — | — | — | Loom automata step off the imonoba bridge | 2 at phase start and 2 at 45% HP (max 2 alive). Naginata reach and the forge hammer's stagger | — |
| P2 | Channel cycle | Every **10 s** | | | | | | |
| P3 30–0 | Roof breach (arena) | 3 s event, control kept | | | | | Rain column over the void and slots C1 and C3 | Kōzō: 「雨が湯に落ちたら、湯気が吹くで！」 |
| P3 | Steam burst (wet slots) | 900 ms hiss | 600 | — | 25 in r 2.5 m, 1 s blur | [蒸気の噴く音 / Steam hissing] caption plus vapor | Stand clear. **Lure her in**: she follows at 6–9 m, and a burst on her overloads the mantle | Her 「……外套、過負荷。」 confirms the 4 s window |
| P3 | Full open (once, at 10%) | 1500 ms | 4000 | 1500 | 35/s, all channels and slots | All four gates glow at once | Stand on a cross-bridge | — |

**Falling.** A lash can pull you into an open heat slot. On Normal and Hard that deals 80 damage and drops you to the floor; climb back by either stair. On Easy, rails prevent the fall.

**Phase checkpoints** are at 65% and 30% (`checkpoint_per_phase: true`). On a checkpoint restart, the adds already killed stay dead.

**Intro (20 s).** Tarifa reads his number and finds none: 「債務者番号……未登録。」 Nyaakoto answers 「その帳には載らぬ。」

**Outro (20 s).** The fall:

1. At 0 HP she staggers back onto the C3 slot grating and opens the gate, meaning to flood his side.
2. The grating gives way.
3. Nyaakoto lunges for her tether: 「掴まれ！」 The cable slips through his paw.
4. The glow and steam cover the rest; her fall stays off-screen.
5. Silence, then Kōzō: 「……鉄は、誰も選ばん。」

This is played straight, per the tone rules. Nyaakoto's reach is katsujinken, even for her.

### 2.4 New enemy: `loom_automaton` 織機傀儡 (for L2's `enemies.json`)

| Field | Proposal (Normal) |
|---|---|
| Silhouette | 2.3 m tall. A loom-frame torso on four beam legs. Shuttle arms. Warp threads run like tendons and glow cyan; a levy meter on the back is its core |
| HP / speed | 420 / 150 cm/s. Turns slowly (90°/s) |
| Shuttle thrust | 800 ms windup (amber line), 35 damage, reach 2.5 m, 1000 ms recovery |
| Beater slam | 1100 ms windup (amber ring 2 m), 45 damage, 1400 ms recovery |
| Weak point | Rear levy core, ×2 damage |
| Reactions | The forge hammer staggers it (0.8 s). A naginata sweep hit interrupts a windup. It is immune to 峰打ち rules (it is a machine, not a person) |
| Environment | The melt destroys it instantly, which counts as a defeat. Luring one into a flowing channel is the intended lesson in b15 |
| First seen | ch05.b14 (cinematic) and b15 W1 (a single teaching unit) |

### 2.5 Systems introduced in this chapter

**Rhythm manufacture** (b06, b08, b11). These are three flavors of one pass/fail rule set:

| | Bellows (b06) | Aizuchi (b08) | Sorabiki (b11) |
|---|---|---|---|
| Input | Alternate left and right treads | One strike per cue | One pull per call |
| Timing | Rate band 0.8–1.3 turns/s | Cue → strike 600 ms, ±90 | Call → pull 750 ms, ±120 |
| Feedback | Flame color plus notch gauge; Kōzō's lines | Kōzō's tap (sound plus hammer glint); a ring closes on the anvil | Okinu's call (voice plus a shuttle flick); a cord marker |
| Failure | Progress decays at 0.01/s | The phrase repeats | The pick repeats |
| Music | `ch05_bellows` locked to the player's rate (60–78 BPM) | `ch05_aizuchi` at 100 BPM | `ch05_sorabiki` at 80 BPM |

**Accessibility (L4):**

- On 稽古, tolerances are ×1.5.
- A **rhythm assist** setting: holding the button performs on-beat actions at 70% progress speed.
- There is a visual metronome ring, controller haptics on each cue, and captioned cue sounds.
- No cue depends on color alone.
- There is no quality grade and no grind (bible §12.2).

**Molten channels** (b15, b16):

- Each gate cycles: a 2 s **animated amber edge pulse** (distinct from the melt's steady 1400–1600 K glow, per bible §15.1), then 5 s of flow.
- They deal 35 damage/s to the player and destroy automata.
- On Mac they are emissive meshes with capped particles.

**Registry → first XOR** (b08, b09, b11 → b12):

1. When a production beat completes, it writes a brush entry to the 生産改帳 (a toast plus a registry-page line).
2. b12 turns each entry into a **three-seal split tally**. The UI shows the split-tally icon; the maker's and receiver's halves are diegetic props.
3. The chapter-complete page is headed 「生産改帳 其の五 絹の工房」 and lists the three entries, their seals, and the vermillion SORA 朱印.
4. **XOR never appears as a number, a balance or a purse** (bible §2 boundary). The tally names what was made and how many. Oyuki's b12 line says so in the fiction.

### 2.6 Checkpoints, failure and difficulty

- **Checkpoints:** every beat except b14 and b18, plus Tarifa's two phase checkpoints. The longest target-time gap is 300 s (b03 → b04, b05 → b06, b07 → b08), within the 360 s rule on both the optional-taken and optional-skipped paths.
- **Default failure:** `{on: player_died, to: checkpoint}`.
- **Extra fail conditions:**
  - b03: an escorted NPC dies.
  - b07: the furnace is destroyed, or Kōzō is down for more than 25 s.
- **Easy (稽古):**
  - windups +30%;
  - rhythm tolerances ×1.5;
  - stealth detection → `combat`;
  - escort NPC health ×1.5;
  - boss slot rails prevent falls.
- **Hard (免許皆伝):**
  - windups −15%;
  - rhythm tolerances ×0.8;
  - furnace HP ×0.8;
  - no extra enemy counts (pacing stays comparable).

---

## 3. Script (bilingual)

### 3.1 Cast in this chapter and speaker ids

| Speaker id | JA | EN | Status | Lines |
|---|---|---|---|---|
| `samurai` | ニャーコト | Nyaakoto | existing | 16 |
| `scout` | 小萩 | Kohagi | existing | 11 |
| `weaver` | お絹 | Okinu | bible §6.2 | 14 |
| `foundry_master` | 鋼蔵 | Kōzō | bible §6.2 | 27 |
| `gunsmith` | 鉄五郎 | Tetsugorō | bible §6.2 | 8 |
| `leader` | お雪 | Oyuki | bible §6.1 | 11 |
| `farmer_young` | お種 | Otane | bible §6.2 | 3 |
| `boss_tarifa` | タリファ | Tarifa | bible §6.3 | 16 |
| `clerk` | イオタ | Iota | bible §6.3 | 4 |
| `artisan` | 職人 | Artisan | existing | 4 |
| `enforcer` | 執行兵 | Enforcer | proposed (new) | 6 |
| `conscript` | 債縛衆 | Debt-Bound | proposed (new) | 4 |
| `mentor` | 石鈴斎 | Sekireisai | existing | 1 |

`enforcer` and `conscript` are proposed speaker ids for L1's schema-4 `dialogue_speakers`, covering generic bark voices. The bible's §6 ids are used unchanged. Iota is heard in ch05 only (through the quota board); he is first seen in ch06.

**Registers in ch05:**

- **Nyaakoto (`samurai`):** few words. Polite to elders (村下殿, 〜ですか), plain with Kohagi, formal in the ceremony (務めます). English is measured and uncontracted ("I will").
- **Kohagi (`scout`):** counts and directions, with particles dropped (見張り九。首輪つきが六十。).
- **Okinu (`weaver`):** soft Kyoto speech (〜どす, 〜おす, 〜え, 〜はる, 〜とくれやす) over a steel core. She drops the softness exactly once, for catalog anchor 1, answering Tarifa's claim that the goods are collateral; play it flat and low. In b15 her register breaks into grief.
- **Kōzō (`foundry_master`):** gruff Yamato speech (わし, 〜や, 〜とる, 〜ん, ええ, あかん). Short sentences. His warmth comes out in what he asks others to count.
- **Tetsugorō (`gunsmith`):** blunt Kansai (おれ, 〜や, ええ). Practical. He never jokes on purpose.
- **Oyuki (`leader`):** business keigo (〜でございます), numbers first. She speaks **plainly once**, for catalog anchor 2 (「〜にしよう」), to the crowd as one of them. That is the only unguarded line she has before ch08.
- **Otane (`farmer_young`):** bright Kamigata (〜で, 〜や, あんた).
- **Tarifa (`boss_tarifa`):** hyper-polite corporate keigo with finance jargon (稼働率, 元本, 延滞, 担保, 計上, 引当, 増産) delivered flat through the translation collar. The English never uses contractions.
- **Iota (`clerk`):** manual-learned keigo. He honors the ledger as 帳簿様, rendered "the esteemed Ledger", and is literal.
- **Enforcers:** clipped reporting keigo (〜します). **Conscripts and artisans:** local colloquial speech, with warm English contractions.
- **Sekireisai (`mentor`):** archaic (〜じゃ), as a memory with reverb.

### 3.2 Conventions

- **Line ids** follow `ch05.bMM.<token>.<nnn>` (bible §12.5, §18): the token is the character's short name (`kohagi`, `okinu`, `kozo`, `tetsugoro`, `oyuki`, `otane`, `tarifa`, `iota`, `sekireisai`, `nyaakoto`) or a generic role, and nnn runs within the beat. `ch05.b00.*` is a proposed chapter-wide bark pool.
- **Triggers** are §12.1 events. `(ext)` marks a proposed event (§6 item 1). "↳ follows" means the line plays in the same `dialogue` entry as the previous line; §12.1 plays a `lines` list in sequence.
- **Durations** are max(JA speaking estimate + 0.3 s, EN characters ÷ 15, 1.0), rounded up to 0.5 s.
  - EN fits in 2 lines of 42 characters or fewer; the highest reading speed in this chapter is 14.9 cps (the limit is 17).
  - JA fits in 2 × 16 full-width characters.
  - Blocking lines: none. b04 is ambient, with two interact gates.
- **Anchors:** the three catalog ch05 cues are used verbatim in JA and EN, placed as bible §20 says:
  - line 1 → b04, speaker `weaver`;
  - line 2 → b12, speaker changed from `scout` to `leader`;
  - line 3 → b12.
  
  Three §6.5 register samples are reused verbatim: Kōzō's 「鉄は三晩で生まれる。急かすな。」, Okinu's 「糸は一本では弱おす。…」, and the §2.3 skeptic line 「わしは鉄しか信じん。」.
- **Readings** list only rare or technical words, for the furigana-style caption option and the voice actors.

### 3.3 Lines by beat (125 voiced lines)

#### ch05.b01 絹の工房 / The Silk Foundry (cinematic, 5 lines)

| Line id | Trigger | Speaker | JA | Readings | EN subtitle | s |
|---|---|---|---|---|---|---|
| `ch05.b01.kohagi.001` | `cinematic` — LS 0:08 ridge, foundry lights below | 小萩 / Kohagi | 絹の工房。見張り九。首輪つきが六十。 | — | The Silk Foundry. Nine guards. Sixty in collars. | 4.5 |
| `ch05.b01.nyaakoto.002` | `cinematic` — LS 0:14 | ニャーコト / Nyaakoto | 六十人……夜通しか。 | — | Sixty of them… all through the night? | 3.0 |
| `ch05.b01.tarifa.003` | `cinematic` — LS 0:40 PA over the reeling shed; quota board insert | タリファ / Tarifa | 目標稼働率、百四十パーセント。現在、九十八。 | 稼働率(かどうりつ) | Target utilization: one hundred forty percent. Current: ninety-eight. | 5.5 |
| `ch05.b01.tarifa.004` | `cinematic` — LS 0:48 PA; collared paws in cocoon water | タリファ / Tarifa | 不足分は、各位の元本に加算いたします。 | 各位(かくい)、元本(がんぽん) | The shortfall will be added to each of your principals. | 4.5 |
| `ch05.b01.kohagi.005` | `cinematic` — LS 1:40 after the 昼寝禁止 notice insert; back on the ridge | 小萩 / Kohagi | 入るのは下から。鉄穴の水路。 | 鉄穴(かんな) | We go in from below. Through the iron-sand channels. | 3.5 |

#### ch05.b02 鉄穴の水路を抜けよ / Slip through the iron-sand channels (stealth_zone, 5 lines)

| Line id | Trigger | Speaker | JA | Readings | EN subtitle | s |
|---|---|---|---|---|---|---|
| `ch05.b02.kohagi.001` | `beat_start` | 小萩 / Kohagi | 水路を歩いて。水音が足音を隠す。 | 水音(みずおと) | Walk in the channels. The water hides your steps. | 4.0 |
| `ch05.b02.kohagi.002` | `volume_enter:vol_kanna_tailings` — tailings heaps | 小萩 / Kohagi | 砂利山は鳴る。避けて。 | 砂利(じゃり) | The tailings crunch. Go around. | 3.0 |
| `ch05.b02.kohagi.003` | `volume_enter:vol_kanna_laborers` — 6 m of the two laborers | 小萩 / Kohagi | 首輪の二人、目をそらしてる。……首輪は、そらさない。 | — | Those two look away. …Their collars don't. | 6.0 |
| `ch05.b02.conscript.004` | `volume_enter:vol_kanna_laborers_near` — passing within 2.5 m while unaware | 債縛衆 / Debt-Bound | ……行け。見とらん。 | — | …Go. I saw nothing. | 3.0 |
| `ch05.b02.nyaakoto.005` | ↳ follows conscript.004 | ニャーコト / Nyaakoto | 必ず戻る。 | — | I will come back for you. | 2.0 |

#### ch05.b03 職人を解き放ち、炭小屋へ導け / Free the craftspeople and lead them to the charcoal shed (production_task, 7 lines)

| Line id | Trigger | Speaker | JA | Readings | EN subtitle | s |
|---|---|---|---|---|---|---|
| `ch05.b03.artisan.001` | `interact_done:collar_reeler_a` (ext) — first collar cut | 職人 / Artisan | ……軽い。首が、軽い。 | — | …Light. My neck is light. | 3.5 |
| `ch05.b03.okinu.002` | `interact_done:collar_okinu` (ext) — Okinu's collar cut | お絹 / Okinu | どちらさんどす？　……いえ、その紋で分かりますえ。 | — | And who might you be? …No. That crest tells me. | 5.0 |
| `ch05.b03.nyaakoto.003` | ↳ follows weaver.002 | ニャーコト / Nyaakoto | 猫柳生のニャーコト。皆を外へ出す。 | 猫柳生(ニャーギュウ) | Nyaakoto of Nyaagyu. I am getting you all out. | 4.0 |
| `ch05.b03.tetsugoro.004` | `interact_done:collar_tetsugoro` (ext) — Tetsugorō's collar cut | 鉄五郎 / Tetsugorō | 礼は後や。先に、若いのを出したってくれ。 | — | Thanks can wait. Get the young ones out first. | 4.5 |
| `ch05.b03.kohagi.005` | `progress_at:0.05` — escort path starts | 小萩 / Kohagi | 炭小屋まで。見回り三つ。合図で伏せて。 | 炭小屋(すみごや) | To the charcoal shed. Three patrols. Down on my signal. | 5.0 |
| `ch05.b03.okinu.006` | `progress_at:0.5` — halfway, west lane | お絹 / Okinu | 外の風、四十日ぶりどす。 | — | Forty days since I last felt the wind. | 3.0 |
| `ch05.b03.kohagi.007` | `beat_complete` — all six inside the refuge | 小萩 / Kohagi | 全員。六人。 | — | All of them. Six. | 2.0 |

#### ch05.b04 炭小屋の談合 / Council in the charcoal shed (dialogue, 9 lines)

| Line id | Trigger | Speaker | JA | Readings | EN subtitle | s |
|---|---|---|---|---|---|---|
| `ch05.b04.okinu.001` | `beat_start` — Okinu pulls a bale apart | お絹 / Okinu | 炭は数えはっても、中までは見はらしまへん。 | — | They count the charcoal. They never look inside. | 4.5 |
| `ch05.b04.okinu.002` | `interact:naginata_handover` (ext) — naginata handover (weapon 20) | お絹 / Okinu | 母の形見どす。貸すだけどすえ。 | 形見(かたみ) | It was my mother's. It is only a loan, mind. | 3.5 |
| `ch05.b04.nyaakoto.003` | ↳ follows weaver.002 | ニャーコト / Nyaakoto | ……預かる。 | 預かる(あずかる) | …I will hold it in trust. | 2.0 |
| `ch05.b04.tarifa.004` | ↳ follows samurai.003 | タリファ / Tarifa | 本工房の生産物は、全て当院の担保でございます。 | 担保(たんぽ) | All output of this foundry is collateral of this House. | 5.5 |
| `ch05.b04.okinu.005` | ↳ follows boss_tarifa.004 | お絹 / Okinu | 絹も鋼も、作ったのはこの手だ。 | 鋼(はがね) | Silk and steel were made by these hands. **[catalog anchor 1]** | 3.5 |
| `ch05.b04.kozo.006` | `interact_done:collar_kozo` (ext) — Kōzō enters for charcoal; collar cut | 鋼蔵 / Kōzō | 炉ん中で、鉄が二晩寝とる。 | 炉(ろ) | There's iron two nights deep in that furnace. | 3.5 |
| `ch05.b04.kozo.007` | ↳ follows foundry_master.006 | 鋼蔵 / Kōzō | 三晩かかる。今夜しかない。 | 三晩(みばん) | It takes three nights. We have tonight. *[bible line]* | 3.5 |
| `ch05.b04.kohagi.008` | ↳ follows foundry_master.007 | 小萩 / Kohagi | 一揆がここを取る。作った物は、帳に付ける。 | 一揆(いっき)、帳(ちょう) | The League takes this place. What's made goes in the registry. | 5.0 |
| `ch05.b04.kozo.009` | ↳ follows scout.008 | 鋼蔵 / Kōzō | 帳面はええ。わしは鉄しか信じん。 | 帳面(ちょうめん) | Spare me the ledgers. I trust iron. *[bible line]* | 3.5 |

#### ch05.b05 機場を取り戻せ / Take back the loom hall (combat_wave, 6 lines)

| Line id | Trigger | Speaker | JA | Readings | EN subtitle | s |
|---|---|---|---|---|---|---|
| `ch05.b05.okinu.001` | `beat_start` — she climbs a loom frame | お絹 / Okinu | 皆はん、杼を置いて！　今夜は織らしまへん！ | 杼(ひ) | Everyone, set down your shuttles! Tonight, we do not weave! | 4.5 |
| `ch05.b05.tarifa.002` | `wave_start:1` (ext) — wave 1 +6 s, PA | タリファ / Tarifa | 持ち場に戻らない場合、延滞として処理いたします。 | 延滞(えんたい) | Failure to return to your station will be processed as default. | 5.5 |
| `ch05.b05.okinu.003` | `wave_start:2` (ext) — collared weavers are driven in | お絹 / Okinu | その子らは斬らんといて！　首輪だけ！ | — | Don't cut them down! Just the collars! | 4.0 |
| `ch05.b05.nyaakoto.004` | `polearm_obstructed:first` (ext) — first naginata sweep caught on a loom | ニャーコト / Nyaakoto | 狭い……突きで行く。 | — | Too tight… Thrusts, then. | 3.0 |
| `ch05.b05.artisan.005` | `wave_start:3` (ext) — a weaver smashes a levy meter | 職人 / Artisan | 毎日この目盛りを睨んできたんや。 | 目盛り(めもり)、睨む(にらむ) | Every day, I've glared at this meter. | 3.5 |
| `ch05.b05.artisan.006` | `beat_complete` — runner at the west door | 職人 / Artisan | 村下が呼んどる！　炉が冷える！ | 村下(むらげ) | The murage is calling! The furnace is cooling! | 3.5 |

#### ch05.b06 踏鞴を踏み、炉を保て / Tread the bellows and keep the furnace alive (production_task, 8 lines)

| Line id | Trigger | Speaker | JA | Readings | EN subtitle | s |
|---|---|---|---|---|---|---|
| `ch05.b06.kozo.001` | `beat_start` | 鋼蔵 / Kōzō | 番子が逃げた。お前が踏め。 | 番子(ばんこ) | The bellows crew fled. You tread. | 3.5 |
| `ch05.b06.kozo.002` | ↳ follows foundry_master.001 | 鋼蔵 / Kōzō | 深う踏め。同じ間でな。 | 間(ま) | Tread deep. Keep an even beat. | 3.0 |
| `ch05.b06.kozo.003` | `rate_band:below` (ext) — tread rate below band (repeatable, 15 s cooldown) | 鋼蔵 / Kōzō | 浅い。炎が赤い。 | — | Too shallow. The flame's red. *(repeatable)* | 2.5 |
| `ch05.b06.kozo.004` | `rate_band:in:first` (ext) — first time inside the band | 鋼蔵 / Kōzō | ……そうや。その山吹色や。 | 山吹色(やまぶきいろ) | …That's it. That golden yellow. | 3.5 |
| `ch05.b06.kozo.005` | `rate_band:above` (ext) — tread rate above band (repeatable, 15 s cooldown) | 鋼蔵 / Kōzō | 急くな。白い炎は、炭を食うだけや。 | 急く(せく) | Don't rush. White flame only eats charcoal. *(repeatable)* | 4.0 |
| `ch05.b06.kozo.006` | `progress_at:0.4` — progress 40% | 鋼蔵 / Kōzō | 鉄は三晩で生まれる。急かすな。 | — | Iron is born over three nights. Don't rush it. *[bible line]* | 3.5 |
| `ch05.b06.nyaakoto.007` | `progress_at:0.7` — progress 70% | ニャーコト / Nyaakoto | 村下殿、その目は…… | 村下殿(むらげどの) | Master smelter, your eye… | 3.0 |
| `ch05.b06.kozo.008` | ↳ follows samurai.007 | 鋼蔵 / Kōzō | 炎を見すぎた。村下は片目で鉄を読む。 | — | Watched the flame too long. A murage reads iron one-eyed. | 4.5 |

#### ch05.b07 炉と村下を守れ / Defend the furnace and the master smelter (production_task, 5 lines)

| Line id | Trigger | Speaker | JA | Readings | EN subtitle | s |
|---|---|---|---|---|---|---|
| `ch05.b07.tarifa.001` | `beat_start` — PA | タリファ / Tarifa | 高殿の無許可稼働を確認。没収いたします。 | 高殿(たかどの)、没収(ぼっしゅう) | Unauthorized operation in the tatara hall. Confiscating. | 5.0 |
| `ch05.b07.kozo.002` | ↳ follows boss_tarifa.001 | 鋼蔵 / Kōzō | 炉を守れ！　釜が割れたら三晩が灰や！ | 釜(かま) | Guard the furnace! If it cracks, three nights turn to ash! | 4.0 |
| `ch05.b07.kozo.003` | `target_hp_below:tatara_furnace:0.7` (ext) — furnace below 70% HP | 鋼蔵 / Kōzō | 釜に土を塗れ！　桶の粘土や！ | 粘土(ねんど) | Clay on the furnace wall! From the tubs! | 3.5 |
| `ch05.b07.kozo.004` | `npc_downed:kozo` — Kōzō downed | 鋼蔵 / Kōzō | 構うな……炉を……！ | — | Never mind me… the furnace…! | 3.0 |
| `ch05.b07.kozo.005` | `beat_complete` — timer complete | 鋼蔵 / Kōzō | ……持ちこたえた。鉧が育っとる。 | 鉧(けら) | …We held. The bloom is growing. | 4.0 |

#### ch05.b08 鏃を打て / Forge arrowheads (production_task, 7 lines)

| Line id | Trigger | Speaker | JA | Readings | EN subtitle | s |
|---|---|---|---|---|---|---|
| `ch05.b08.kozo.001` | `beat_start` — weapon 8 in hand | 鋼蔵 / Kōzō | 向こう鎚や。わしの小鎚が叩いた所を打て。 | 向こう鎚(むこうづち)、小鎚(こづち) | The striker's sledge. Hit where my small hammer taps. | 4.5 |
| `ch05.b08.kozo.002` | ↳ follows foundry_master.001 | 鋼蔵 / Kōzō | わしが打つ、お前が打つ。それが相鎚や。 | 相鎚(あいづち) | I strike, you strike. That is aizuchi. | 4.5 |
| `ch05.b08.nyaakoto.003` | `progress_at:0.5` — halfway | ニャーコト / Nyaakoto | 刀を打つのと、同じ鉄ですか。 | — | Is this the same iron as a sword? | 3.5 |
| `ch05.b08.kozo.004` | ↳ follows samurai.003 | 鋼蔵 / Kōzō | 同じや。何になるかは、打つ者が決める。 | — | Same iron. The one who strikes decides what it becomes. | 4.5 |
| `ch05.b08.kozo.005` | `beat_complete` — 24 heads on the tray | 鋼蔵 / Kōzō | 二十四本。数えてみい。 | — | Twenty-four. Count them yourself. | 3.0 |
| `ch05.b08.kozo.006` | ↳ follows foundry_master.005 | 鋼蔵 / Kōzō | その鎚、貸しとく。 | 鎚(つち) | Keep the hammer. It's a loan. | 2.5 |
| `ch05.b08.sekireisai.007` | `collectible_found:ch05.c06` (ext) — scroll fragment c06 picked up (memory voice) | 石鈴斎 / Sekireisai | 鍛冶は鉄に逆らわず、鉄の欲する所を打つ。剣も同じじゃ。 | 鍛冶(かじ)、欲する(ほっする) | A smith never fights the iron. He strikes where it wants to go. So with the sword. | 6.0 |

#### ch05.b09 アーク・カービンを組め / Assemble the Arc Carbine (production_task, 5 lines)

| Line id | Trigger | Speaker | JA | Readings | EN subtitle | s |
|---|---|---|---|---|---|---|
| `ch05.b09.tetsugoro.001` | `beat_start` | 鉄五郎 / Tetsugorō | 連中の銃の芯、見てきた。あれは使える。 | 芯(しん) | I've seen the cores in their guns. We can use them. | 4.5 |
| `ch05.b09.tetsugoro.002` | `step_start:inspect` (ext) — step 1: bore sighting | 鉄五郎 / Tetsugorō | 筒を覗け。灯りが真っ直ぐなら、ええ筒や。 | 筒(つつ)、覗く(のぞく) | Look down the barrel. If the light runs true, it's good. | 4.5 |
| `ch05.b09.tetsugoro.003` | `step_start:assemble` (ext) — step 2: seat the coil | 鉄五郎 / Tetsugorō | 芯を逆さに入れたら、手が飛ぶで。 | — | Seat the core backwards and you'll lose a paw. | 3.5 |
| `ch05.b09.tetsugoro.004` | `step_complete:assemble:1` (ext) — coil seated; step 3: receiver plates with the mon | 鉄五郎 / Tetsugorō | 空紋や。一から作った、おれらの初めての銃や。 | 空紋(そらもん) | The Sora crest. Our first gun, built from scratch. | 5.0 |
| `ch05.b09.tetsugoro.005` | `beat_complete` — dry-fire passes; weapon 1 unlocked | 鉄五郎 / Tetsugorō | 一挺はお前のや。試し撃ちは、すぐ来るで。 | 一挺(いっちょう) | One is yours. You'll get to test it soon enough. | 4.5 |

#### ch05.b10 反撃を退けよ / Repel the counterattack (combat_wave, 4 lines)

| Line id | Trigger | Speaker | JA | Readings | EN subtitle | s |
|---|---|---|---|---|---|---|
| `ch05.b10.tetsugoro.001` | `beat_start` | 鉄五郎 / Tetsugorō | 肩に付けて、息を吐きながら引け！ | — | Shoulder it. Squeeze as you breathe out! | 3.5 |
| `ch05.b10.kohagi.002` | `wave_start:2` (ext) — marksman spawns on the reeling-shed roof | 小萩 / Kohagi | 屋根に一。光ったら隠れて。 | — | One on the roof. When it glints, take cover. | 3.5 |
| `ch05.b10.otane.003` | `wave_start:3` (ext) — League gunners enter by the NW apron gate | お種 / Otane | 待たせたな！　一揆の鉄砲衆、連れてきたで！ | 鉄砲衆(てっぽうしゅう) | Sorry to keep you! I brought the League's gunners! | 4.5 |
| `ch05.b10.oyuki.004` | `beat_complete` — yard cleared; Oyuki at the gate with the registry box | お雪 / Oyuki | 遅くなりました。帳を運んでまいりました。 | — | Forgive the delay. I have brought the registry. | 4.0 |

#### ch05.b11 空紋の幟を織れ / Weave the Sora banner (production_task, 5 lines)

| Line id | Trigger | Speaker | JA | Readings | EN subtitle | s |
|---|---|---|---|---|---|---|
| `ch05.b11.okinu.001` | `beat_start` — at the draw loom | お絹 / Okinu | 四十夜、あの目盛りの下で織ってきた幟どす。 | 四十夜(しじゅうや)、幟(のぼり) | Forty nights I wove this banner, right under their meter. | 4.5 |
| `ch05.b11.okinu.002` | ↳ follows weaver.001 | お絹 / Okinu | 上に乗って、うちが言うたら紋糸を引いとくれやす。 | 紋糸(もんいと) | Sit up top. When I call, pull the figure cords. | 5.0 |
| `ch05.b11.okinu.003` | `progress_at:0.5` — halfway (restrained humor) | お絹 / Okinu | ええ手どすなあ。お侍より機屋向きやわ。 | 機屋(はたや) | Such good paws. More weaver than samurai, you. | 4.0 |
| `ch05.b11.okinu.004` | `beat_complete` — the mon comes up on the face | お絹 / Okinu | 糸は一本では弱おす。けど、織ったら旗になりますえ。 | — | One thread alone is weak. Woven, it becomes a banner. *[bible line]* | 5.5 |
| `ch05.b11.oyuki.005` | ↳ follows weaver.004 | お雪 / Oyuki | 絹幟、一旒。記しました。 | 絹幟(きぬのぼり)、一旒(いちりゅう) | Silk banner, one. Entered. | 3.5 |

#### ch05.b12 初めての割符 / The first tally (cinematic, 14 lines)

| Line id | Trigger | Speaker | JA | Readings | EN subtitle | s |
|---|---|---|---|---|---|---|
| `ch05.b12.oyuki.001` | `cinematic` — LS 0:06 Oyuki opens the registry | お雪 / Oyuki | 五箇条の一。物なくして札なし。 | 五箇条(ごかじょう)、札(ふだ) | Article one: no goods, no tally. | 3.5 |
| `ch05.b12.oyuki.002` | `cinematic` — LS 0:12 | お雪 / Oyuki | 改めは三者。作り手、受け手、籤で選ぶ改め役。 | 改め(あらため)、籤(くじ) | Three inspect: maker, receiver, and an inspector drawn by lot. | 5.5 |
| `ch05.b12.nyaakoto.003` | `cinematic` — LS 0:22 the lot shows his name | ニャーコト / Nyaakoto | 改め役、ニャーコト。務めます。 | 務める(つとめる) | Inspector: Nyaakoto. I will serve. | 3.5 |
| `ch05.b12.kozo.004` | `cinematic` — LS 0:30 maker declares | 鋼蔵 / Kōzō | 鏃、二十四本。作り手、村下鋼蔵。 | 鏃(やじり)、鋼蔵(こうぞう) | Arrowheads, twenty-four. Maker: Murage Kōzō. | 4.5 |
| `ch05.b12.otane.005` | `cinematic` — LS 0:36 receiver declares | お種 / Otane | 受け手、お種。村の弓衆に回します。 | 弓衆(ゆみしゅう) | Receiver: Otane. They go to the village archers. | 4.0 |
| `ch05.b12.nyaakoto.006` | `cinematic` — LS 0:44 counting on the tray | ニャーコト / Nyaakoto | ……二十二、二十三、二十四。確かに。 | — | …Twenty-two, twenty-three, twenty-four. Confirmed. | 5.0 |
| `ch05.b12.tetsugoro.007` | `cinematic` — LS 0:56 | 鉄五郎 / Tetsugorō | アーク・カービン三挺。作り手、鉄五郎。おれが撃った。 | 挺(ちょう) | Arc Carbines, three. Maker: Tetsugorō. I fired each one. | 6.0 |
| `ch05.b12.okinu.008` | `cinematic` — LS 1:04 | お絹 / Okinu | 絹幟、一旒。織り手、お絹。 | — | Silk banner, one. Weaver: Okinu. | 3.5 |
| `ch05.b12.oyuki.009` | `cinematic` — LS 1:14 brand iron from the brazier | お雪 / Oyuki | 割目に紋の焼印を。半分は作り手、半分は受け手に。 | 割目(わりめ)、焼印(やきいん) | Brand the crest across the split. Half to the maker, half to the receiver. | 6.0 |
| `ch05.b12.oyuki.010` | `cinematic` — LS 1:30 the halves are handed over | お雪 / Oyuki | 札は財布の数字ではございません。作られた物の証でございます。 | 証(あかし) | This tally is no number in a purse. It is proof a thing was made. | 6.0 |
| `ch05.b12.oyuki.011` | `cinematic` — LS 1:40 | お雪 / Oyuki | 利は付きません。貸すのは道具。金ではございません。 | 利(り) | It bears no interest. We lend tools, not money. | 5.5 |
| `ch05.b12.kozo.012` | `cinematic` — LS 1:50 Kōzō turns his half in the light | 鋼蔵 / Kōzō | ……鉄を数えた札なら、信じてもええ。 | — | …A tally that counts iron. That, I can trust. | 4.0 |
| `ch05.b12.oyuki.013` | `cinematic` — LS 2:02 to the crowd, plainly | お雪 / Oyuki | 生産を記録し、民の新しい通貨にしよう。 | — | Let us record our production as the basis for a new currency. **[catalog anchor 2]** | 4.5 |
| `ch05.b12.nyaakoto.014` | `cinematic` — LS 2:12 before the posted page | ニャーコト / Nyaakoto | SORA XOR。ここで生まれた価値を、ここへ返す。 | — | SORA XOR. Value made here will return to the people here. **[catalog anchor 3]** | 5.0 |

#### ch05.b13 取立蔵を調べる / Search the levy storehouse (explore_optional, 3 lines)

| Line id | Trigger | Speaker | JA | Readings | EN subtitle | s |
|---|---|---|---|---|---|---|
| `ch05.b13.nyaakoto.001` | `volume_enter:vol_poi_quota_sheet` — reads the quota sheet | ニャーコト / Nyaakoto | 足りぬ分が元本に足され、その元本に利がつく。……終わらぬ勘定だ。 | 勘定(かんじょう) | The shortfall joins the principal, which draws interest. …It never ends. | 7.0 |
| `ch05.b13.nyaakoto.002` | `volume_enter:vol_poi_washio_notice` — reads the Washio transfer notice (c03) | ニャーコト / Nyaakoto | 鷲尾家、債権譲渡済み……虎之介。 | 鷲尾(わしお)、債権譲渡(さいけんじょうと) | Washio house: debt transferred… Toranosuke. | 4.5 |
| `ch05.b13.kozo.003` | `volume_enter:vol_poi_kanayago` — Kōzō at the upper-floor crate (c04) | 鋼蔵 / Kōzō | 金屋子さんの掛軸に、評価額零、やと。 | 金屋子(かなやご)、掛軸(かけじく)、零(れい) | They tagged the Kanayago scroll 'Assessed value: zero.' | 4.5 |

#### ch05.b14 湯路、全開 / The channels open (cinematic, 5 lines)

| Line id | Trigger | Speaker | JA | Readings | EN subtitle | s |
|---|---|---|---|---|---|---|
| `ch05.b14.tarifa.001` | `cinematic` — LS 0:06 Tarifa on the casting-floor gantry | タリファ / Tarifa | 稼働再開を確認。ご協力に感謝いたします。 | — | Resumed operations confirmed. Thank you for your cooperation. | 5.0 |
| `ch05.b14.oyuki.002` | `cinematic` — LS 0:16 | お雪 / Oyuki | 帳は民の前に。あなた様の帳は、どこに掲げてございますか。 | — | A registry belongs before the people. Where is yours posted? | 5.5 |
| `ch05.b14.tarifa.003` | `cinematic` — LS 0:24 | タリファ / Tarifa | ……非公開でございます。 | — | …That is confidential. | 3.0 |
| `ch05.b14.tarifa.004` | `cinematic` — LS 0:40 tether into the looms; gates open; first thunder | タリファ / Tarifa | 設備を自律稼働へ。湯路、全開。 | 湯路(ゆみち) | Equipment to autonomous operation. All channels open. | 4.0 |
| `ch05.b14.kozo.005` | `cinematic` — LS 1:05 melt floods the casting beds | 鋼蔵 / Kōzō | あかん、湯を流しよった！　鋳物場が火の海や！ | 湯(ゆ)、鋳物場(いものば) | No! She's let the melt run! The casting floor's a sea of fire! | 5.0 |

#### ch05.b15 鋳物場を突破せよ / Cross the casting floor (combat_wave, 3 lines)

| Line id | Trigger | Speaker | JA | Readings | EN subtitle | s |
|---|---|---|---|---|---|---|
| `ch05.b15.kozo.001` | `beat_start` — (shouted from the east door) | 鋼蔵 / Kōzō | 湯路の口が光ったら、すぐ湯が来るで！ | — | When a channel mouth glows, the melt is coming! | 4.0 |
| `ch05.b15.okinu.002` | `wave_start:1` (ext) — first loom automaton stands up | お絹 / Okinu | うちの機が……。堪忍え、壊しとくれやす。 | 機(はた)、堪忍(かんにん) | My looms… Forgive me. Break them. | 4.5 |
| `ch05.b15.kohagi.003` | `beat_complete` — floor cleared | 小萩 / Kohagi | 高殿へ逃げた。上。 | — | She ran to the tatara hall. Up top. | 2.5 |

#### ch05.b16 工房監督官タリファを倒せ / Defeat Foundry Overseer Tarifa (boss, 12 lines)

| Line id | Trigger | Speaker | JA | Readings | EN subtitle | s |
|---|---|---|---|---|---|---|
| `ch05.b16.tarifa.001` | `intro_cinematic` — boss intro (20 s) | タリファ / Tarifa | 債務者番号……未登録。ただ今、登録いたします。 | 債務者(さいむしゃ) | Debtor number… unregistered. I shall register you now. | 6.0 |
| `ch05.b16.nyaakoto.002` | `intro_cinematic` — boss intro | ニャーコト / Nyaakoto | その帳には載らぬ。 | — | I will not be in your book. | 2.5 |
| `ch05.b16.tarifa.003` | `pattern:channel_cycle` — captioned telegraph: a channel gate starts its 2 s glow | タリファ / Tarifa | 稼働率百四十パーセント。 | — | Utilization: one hundred forty percent. *[bible line]* *(repeatable)* | 3.0 |
| `ch05.b16.tarifa.004` | `pattern:tether_lash` — captioned telegraph: 700 ms lash windup | タリファ / Tarifa | 引き当てます。 | 引き当てる(ひきあてる) | Drawing down. *(repeatable)* | 2.0 |
| `ch05.b16.tarifa.005` | `pattern:rod_sweep` — captioned telegraph: 500 ms sweep windup | タリファ / Tarifa | 休憩は計上されません。 | 計上(けいじょう) | Breaks will not be booked. *[bible line]* *(repeatable)* | 3.0 |
| `ch05.b16.tarifa.006` | `boss_phase:2` — phase 2 (65%) | タリファ / Tarifa | 増産体制に移行いたします。 | 増産(ぞうさん) | Transitioning to increased production. | 3.0 |
| `ch05.b16.tarifa.007` | `pattern_countered:tether_lash` (ext) — lash parried; cable snaps | タリファ / Tarifa | ……設備に損傷。 | 損傷(そんしょう) | …Equipment damage. *(repeatable)* | 2.5 |
| `ch05.b16.kozo.008` | `boss_phase:3` — phase 3 (30%), roof breach (shouted from the floor) | 鋼蔵 / Kōzō | 雨が湯に落ちたら、湯気が吹くで！ | 湯気(ゆげ) | Rain on the melt means steam bursts! | 4.0 |
| `ch05.b16.tarifa.009` | `boss_state:mantle_down` (ext) — steam overloads her mantle | タリファ / Tarifa | ……外套、過負荷。 | 外套(がいとう)、過負荷(かふか) | …Mantle overloaded. *(repeatable)* | 3.0 |
| `ch05.b16.tarifa.010` | `outro_cinematic` — boss outro: the slot grating gives | タリファ / Tarifa | ……想定外の、損失で…… | 想定外(そうていがい) | …An unforeseen… loss… | 3.5 |
| `ch05.b16.nyaakoto.011` | `outro_cinematic` — he reaches for the cable | ニャーコト / Nyaakoto | 掴まれ！ | 掴む(つかむ) | Take my hand! | 1.5 |
| `ch05.b16.kozo.012` | `outro_cinematic` — silence after | 鋼蔵 / Kōzō | ……鉄は、誰も選ばん。 | — | …Iron chooses no one. | 3.0 |

#### ch05.b17 荷を駄馬に積め / Load the pack horses (production_task, 3 lines)

| Line id | Trigger | Speaker | JA | Readings | EN subtitle | s |
|---|---|---|---|---|---|---|
| `ch05.b17.oyuki.001` | `beat_start` | お雪 / Oyuki | 鏃と銃は隠れ谷へ。絹は提灯街へ。 | 隠れ谷(かくれだに)、提灯街(ちょうちんまち) | Arrowheads and guns to the Hidden Valley. Silk to the Lantern Ward. | 4.5 |
| `ch05.b17.otane.002` | `item_delivered:load_01` — first load on a pack saddle | お種 / Otane | 荷鞍、締めといたで。足は短いけど、根性ある子らや。 | 荷鞍(にぐら) | Pack saddles are cinched. Short legs, but these two have grit. | 5.5 |
| `ch05.b17.artisan.003` | `idle_s:20` — ambient, near the gate | 職人 / Artisan | 朝や……。朝の匂いがする。 | — | Morning… It smells like morning. | 3.5 |

#### ch05.b18 夜明けの幟 / Banner at dawn (cinematic, 9 lines)

| Line id | Trigger | Speaker | JA | Readings | EN subtitle | s |
|---|---|---|---|---|---|---|
| `ch05.b18.kozo.001` | `cinematic` — LS 0:05 the bloom is levered out | 鋼蔵 / Kōzō | 三晩目の鉧、出たで。ええ鉄や。 | — | The third night's bloom is out. Good iron. | 4.0 |
| `ch05.b18.okinu.002` | `cinematic` — LS 0:18 at the pole | お絹 / Okinu | 上げとくれやす。 | — | Raise it, please. | 2.0 |
| `ch05.b18.kohagi.003` | `cinematic` — LS 0:34 two reelers asleep under the 昼寝禁止 notice | 小萩 / Kohagi | ……起こすな。 | — | …Let them sleep. | 2.0 |
| `ch05.b18.iota.004` | `cinematic` — LS 0:52 the quota board flickers; voice through its grille | イオタ / Iota | 恐れ入ります。帳簿機関、会計補のイオタと申します。 | 帳簿機関(ちょうぼきかん)、会計補(かいけいほ) | Pardon the intrusion. I am Junior Auditor Iota, of the Ledger Engine. | 5.5 |
| `ch05.b18.iota.005` | `cinematic` — LS 1:02 | イオタ / Iota | 貴工房の掲示を、帳簿様が読みました。数字が、閉じております。 | 掲示(けいじ) | The esteemed Ledger has read your posting. Its numbers… close. | 6.5 |
| `ch05.b18.iota.006` | `cinematic` — LS 1:12 | イオタ / Iota | ……ご相談がございます。金庫の中から。 | 金庫(きんこ) | …I wish to consult with you. From inside the vault. | 4.5 |
| `ch05.b18.iota.007` | `cinematic` — LS 1:18 a slot in the board's base ejects a palm-sized slate; Kohagi catches it | イオタ / Iota | 連絡用の石板様を一枚、払い出しいたします。お持ちください。 | 石板(せきばん)、払い出し(はらいだし) | Disbursing one honored message slate. Please keep it with you. | 6.5 |
| `ch05.b18.oyuki.008` | `cinematic` — LS 1:28 | お雪 / Oyuki | 罠かもしれません。けれど、中の数字です。 | 罠(わな) | It may be a trap. But those are the numbers from inside. | 4.5 |
| `ch05.b18.nyaakoto.009` | `cinematic` — LS 1:44 looking downriver toward Nekoyama | ニャーコト / Nyaakoto | 先生も、あの城のどこかに。 | — | Sensei is somewhere in that citadel too. | 3.0 |

#### ch05.b00 戦闘・潜入の掛け声 / Combat and stealth barks (chapter-wide pool) (bark pool, 10 lines)

| Line id | Trigger | Speaker | JA | Readings | EN subtitle | s |
|---|---|---|---|---|---|---|
| `ch05.b00.enforcer.001` | `alert_state:suspicious` — any enforcer turns suspicious | 執行兵 / Enforcer | ……音。照合します。 | 照合(しょうごう) | …A sound. Reconciling. *(repeatable)* | 3.0 |
| `ch05.b00.enforcer.002` | `alert_state:search` — search begins | 執行兵 / Enforcer | 未登録の足跡。捜索を開始します。 | 捜索(そうさく) | Unregistered tracks. Commencing search. *(repeatable)* | 4.0 |
| `ch05.b00.enforcer.003` | `alert_state:alert` — full alert | 執行兵 / Enforcer | 債務者を視認。回収します。 | 視認(しにん)、回収(かいしゅう) | Debtor sighted. Commencing collection. *(repeatable)* | 3.5 |
| `ch05.b00.enforcer.004` | `alert_state:unaware` — search times out | 執行兵 / Enforcer | 所在不明。損失として計上します。 | — | Whereabouts unknown. Booking as a loss. *(repeatable)* | 4.0 |
| `ch05.b00.enforcer.005` | `enemy_retreat` (ext) — enforcer withdraws below 25% HP or when its wave breaks | 執行兵 / Enforcer | 後退します。資産の保全を優先。 | 保全(ほぜん) | Withdrawing. Asset preservation takes priority. *(repeatable)* | 4.0 |
| `ch05.b00.enforcer.006` | `pattern:grenade_throw` — grenadier telegraph (captioned) | 執行兵 / Enforcer | 区画を清算します。 | 清算(せいさん) | Liquidating the sector. *(repeatable)* | 2.5 |
| `ch05.b00.conscript.007` | `conscript_attack` (ext) — a bound conscript attacks | 債縛衆 / Debt-Bound | すまん……体が、勝手に……！ | — | Sorry— my body won't stop—! *(repeatable)* | 4.0 |
| `ch05.b00.conscript.008` | `conscript_downed` (ext) — 峰打ち knockdown | 債縛衆 / Debt-Bound | 頼む……首輪を……！ | — | Please… the collar…! *(repeatable)* | 3.0 |
| `ch05.b00.conscript.009` | `conscript_freed` (ext) — seal cut | 債縛衆 / Debt-Bound | ……恩に着る。 | — | …I owe you. *(repeatable)* | 2.5 |
| `ch05.b00.nyaakoto.010` | `nonlethal_focus` (ext) — first lock-on to a bound conscript each beat | ニャーコト / Nyaakoto | 峰で打つ。 | 峰(みね) | The back of the blade. *(repeatable)* | 1.5 |

### 3.4 HUD tutorial prompts (L4 `ui_strings`, not voiced; 16)

| Id | Beat | Shown on | JA | EN |
|---|---|---|---|---|
| `ui.ch05.tut.01` | ch05.b02 | `beat_start` | 水の中を歩くと、足音が小さくなる | Walking in water makes your steps quieter |
| `ui.ch05.tut.02` | ch05.b02 | `volume_enter:vol_kanna_tailings` | 砂利の上は足音が大きい | Gravel is loud underfoot |
| `ui.ch05.tut.03` | ch05.b02 | `look_at:kagaribi` | {Interact}長押し：篝火に砂をかけて消す | Hold {Interact}: smother the brazier with sand |
| `ui.ch05.tut.04` | ch05.b02 | `look_at:flood_upper` | 照明の根元の線を射ると、しばらく消える | Shoot the floodlight's base cable to cut it briefly |
| `ui.ch05.tut.05` | ch05.b03 | `look_at:collar` | {Interact}長押し：首輪を断つ | Hold {Interact}: cut the collar |
| `ui.ch05.tut.06` | ch05.b03 | `progress_at:0.05` | 見張りに見られている間、同行者は足を止める | While a guard sees you, your companions stop and wait |
| `ui.ch05.tut.07` | ch05.b05 | `polearm_obstructed:first` | 薙刀の払いは機に当たる。狭い所では突け | Naginata sweeps catch on looms. Thrust in narrow aisles |
| `ui.ch05.tut.08` | ch05.b06 | `beat_start` | 左右交互に一定の間で踏む。炎の色と印が目安 | Tread left-right at a steady pace. Watch the flame and gauge |
| `ui.ch05.tut.09` | ch05.b07 | `target_hp_below:tatara_furnace:0.7` | {Interact}：粘土で釜を補修 | Press {Interact}: patch the furnace with clay |
| `ui.ch05.tut.10` | ch05.b08 | `beat_start` | 小鎚の合図の一拍後に打つ | Strike one beat after the small hammer's cue |
| `ui.ch05.tut.11` | ch05.b10 | `beat_start` | アーク・カービン: 構えて撃つ/弾を込め直す | Arc Carbine: aim, fire, reload |
| `ui.ch05.tut.12` | ch05.b11 | `beat_start` | お絹の呼び声に合わせて紋糸を引く | Pull the figure cords on Okinu's call |
| `ui.ch05.tut.13` | ch05.b15 | `beat_start` | 光る湯路の口から離れよ。敵を誘い込める | Keep clear of glowing channel mouths. Lure enemies in |
| `ui.ch05.tut.14` | ch05.b16 | `pattern:tether_lash:first` | 鉤縄は「合わせ」で断てる | Meet the tether with awase to snap it |
| `ui.ch05.tut.15` | ch05.b16 | `boss_phase:3` | 湯気の中ではタリファの外套が落ちる | Steam overloads Tarifa's mantle |
| `ui.ch05.tut.16` | ch05.b17 | `beat_start` | 荷を運ぶ間は刀を片手でのみ使える | While carrying, you fight one-handed with the katana |

### 3.5 Diegetic text (on-screen captions for signs; not voiced)

| Id | Seen in | JA | EN caption |
|---|---|---|---|
| `sign.ch05.nap` | b01, b18 | 昼寝禁止 ― 休止時間は課金の対象となります。恒星信用院 執行局 | NO NAPPING — Downtime is billable. Stellar Credit House, Enforcement Office |
| `sign.ch05.quota` | b01, b10, b12 | 目標稼働率 140% / 現在 98% | Target utilization 140% / Current 98% |
| `sign.ch05.tag` | b13 | 装飾品 評価額 零 | Decorative item. Assessed value: 0 |

### 3.6 Humor audit (bible §1.2)

There is at most one light moment per 10 minutes, and none during a boss fight, a death, captivity or grief.

| Where | Moment | Status |
|---|---|---|
| b01 | The 「昼寝禁止」 notice; a reeler's ears flatten as she passes. No line | **Approved** (bible §1.2 #3) |
| b11 | Okinu: 「ええ手どすなあ。お侍より機屋向きやわ。」 Nyaakoto does not answer | Proposed. Character wit, after the fighting, during manufacture |
| b18 | Two freed reelers asleep under the 「昼寝禁止」 notice. Kohagi: 「……起こすな。」 | Proposed. A callback that is about rest restored, not a gag; echoes Baiō in ch01 |

Checked and kept non-humorous: Tetsugorō's release line (captivity) is practical, not a quip. His "lose a paw" warning is a safety instruction. The enforcers' "booking as a loss" is menace through arithmetic (bible §1.2), not comedy.

---

## 4. Historical and cultural accuracy

These notes are for the historian and practitioner review. Claims marked **verify** must be checked before any release copy says "historically accurate".

### 4.1 Tatara smelting (たたら製鉄)

**Used:**

- A low clay box furnace (釜) is **rebuilt for every smelting campaign** (一代, ひとよ). It is charged alternately with iron sand and charcoal and blown by **foot bellows** (踏鞴, the word that gave the whole process its name).
- The crew: the 村下 (murage) directs, the 炭坂 (sumisaka) charge the charcoal, and the 番子 (banko) work the bellows.
- A 鉧押し (kera-oshi) campaign runs about **three days and nights**. At the end the furnace is broken open and the bloom (鉧, kera) is levered out; 玉鋼 is sorted from it. This is the source of Kōzō's "three nights".
- The murage judges the furnace by the colour of the flame and sparks at the tuyères (ほど穴). Traditional accounts of murage losing sight in one eye are used as Kōzō's personal detail (a clouded left eye, proposed), not as a claim about all smelters.
- 真砂 (masa) iron sand from weathered granite is associated with kera-oshi; 赤目 (akome) sand with pig-iron smelting (銑押し). The Nyaagyu slope is granite, so it gives masa (**verify**).
- 金屋子神 (Kanayago-kami) is the tatara workers' deity. The tatara hall has her shrine shelf, and her seized scroll is heirloom `ch05.c04`. The traditional exclusion of women from the tatara floor, associated with this deity, is respected **through staging**, never through dialogue: Okinu never steps onto the furnace floor in b06, b07 or b16. She leads the loom hall and calls from the casting-floor door in b15.

**Avoided:** the seesaw bellows 天秤鞴 (c. 1690s; bible §15.2).

**Flagged stretches, for sign-off:**

1. **The tall permanent 高殿 with a fixed underground structure** is best known from the later Edo 永代たたら. The surviving example, 菅谷たたら山内 in Unnan, Shimane, was an Edo-period operation active from the mid-18th century. An early-17th-century smelt would more plausibly sit in a smaller shed. The game uses the tall hall because the boss needs the space.
2. **Large-scale tatara and 鉄穴流し** belong mainly to the Chūgoku mountains (Izumo, Hōki, Aki), not Yamato. The Nyaagyu foundry is fiction.
3. **One compound that reels, weaves and smelts** is the Credit House's own arrangement (the "Silk Foundry" of the catalog), not a period institution.

### 4.2 Refining forge, smithing and arrowheads

- **大鍛冶 and 小鍛冶:** 大鍛冶 (ōkaji) refined pig iron (銑) into wrought iron (包丁鉄); 小鍛冶 (kokaji) forged blades and tools. Arrowheads are kokaji work, so `pl_okaji` has a kokaji bay.
- **相槌 (aizuchi):** the master (横座, yokoza) taps with a small hammer (小鎚) to call where and when the striker (先手) brings down the sledge (向こう鎚). The everyday phrase 相槌を打つ ("to chime in") comes from this. The b08 call-and-response mechanic is built on it.
- **Arrowhead shapes:** war arrows (征矢, soya) carried pointed heads such as 尖根 (togari-ne) and 柳葉 (yanagi-ba). Broad 平根 (hira-ne) and forked 雁股 (karimata) heads served other purposes. Kōzō forges 尖根 for armoured enforcers (**verify** the shape references with the historian).
- **Simplifications:** heat treatment and quenching are pass/fail. There is no attempt at metallurgical realism.

### 4.3 Iron-sand washing (鉄穴流し)

- **The method:** weathered granite is cut from a face and washed down channels, so the heavy iron sand settles through successive basins while the light sand is carried off.
- **The downstream cost:** the method silted rivers and brought ironworks into conflict with farmers over water. This is a design seed for a later League meeting with Taemon; nothing is scripted.
- **Layout:** cut face (切羽) → feed ditch (走り) → basins → washing flume (洗樋) → settling ponds. The basin names 大池 / 中池 / 乗り池 need to be **verified**.

### 4.4 Silk, looms and the nobori

- **Reeling:** cocoons are simmered in pots and the filaments drawn by hand onto frames. The treadle reel 座繰り (zaguri) spread later in the Edo period; do not model it as the hero device (**verify** dates).
- **高機 (takabata):** a raised loom with the weaver on a bench, in use in Nishijin by the late 16th century.
- **空引機 (sorabiki-bata):** a draw loom. An assistant sits high on the frame and pulls figure cords (空引き) to raise the pattern. It wove figured silks in Nishijin until the Jacquard arrived in the Meiji era. Okinu weaves the mon on one, with the player as her 空引き. Avoid punched-card Jacquard machinery. The name's 空 (sora) is a happy coincidence with the SORA mon; it is never remarked on in dialogue.
- **幟 (nobori):** a tall, narrow banner held on an L-shaped pole by 乳 (chi) loops, widespread in late-16th-century warfare.
  - The League's banner is about 70 × 360 cm: two loom widths joined, with the mon worked in white on indigo so it reads like 染め抜き at a distance (bible §17).
  - Weaving it in one night would be impossible. In the fiction Okinu has woven it over forty nights under the levy meter, keeping the mon on the hidden face, and only the final field is finished on screen.
- **Okinu's naginata:** her background as the daughter of a samurai household who trained in Nishijin is proposed. It makes her mother's naginata a fitting heirloom, since in the Edo period the naginata was strongly associated with samurai women (bible §4.3).

### 4.5 Arms and techniques in ch05

- **Naginata** (catalog 20): wide committed cuts, thrusts and a longer recovery. Following the bible (§4.3), looms and pillars block its reach. Its distance, timing and zanshin framing follows the [All Japan Naginata Federation's description](https://naginata.jp/naginata/viewpoint.html). No named kata are reproduced.
- **Katana:**
  - 峰打ち (back of the blade) against the Debt-Bound, then the seal-cut.
  - **合わせ** against Tarifa's tether. This is the school's meeting cut (bible §3.2) applied to a pull, not a kata.
  - 転 to sidestep the lash.
  - 残心 as the existing passive.
- **Yumi** (catalog 18): the arrow sits on the right and the draw takes 650 ms (bible §4.2). It is used against the floodlight cable, the gallery rifle and the marksman. The 24 new heads refill the ebira to 12.
- **Forge hammer** (catalog 8): a striker's sledge. Committed and heavy; it staggers automata.
- **Arc Carbine** (catalog 1): fiction, a League-built barrel with a captured alien coil. There is no period claim. Sighting down the bore against a lamp is a plausible gunsmith's check.
- **Technique vocabulary** is general period martial usage only, per the respect rules (bible §3.1).

### 4.6 Tallies, seals and counting (the first XOR)

- **割符 (warifu):** a wooden tally written across and split along a line, so that only the two true halves match.
  - In medieval Japan, 割符 read as さいふ also meant bills of exchange, which were credit instruments.
  - The League's tally deliberately goes back to the physical sense: it records a made thing, not a promise of money (bible §2.2 Article 3).
- **焼印 (brand):** the iron's face must be **mirror-reversed** so the mon reads correctly on the wood. It is pressed **across the split**, so each half carries half the mark and only the two halves together show the whole mon.
- **Seals:**
  - samurai sign with a 花押 (kaō), so Nyaakoto uses his;
  - Kōzō presses a 爪印 (nail mark);
  - Otane uses a small 印判.
  
  All three were period practice for their classes (**verify** for 1623 village usage).
- **Lots (籤):** drawing lots to choose an inspector reflects village decision practice. The soroban and Oyuki's 『割算書』 (1622) primer follow bible §19.
- **Boundary:** the tally never displays an XOR amount. XOR is shown as proof of goods, never as a balance (bible §2).

### 4.7 Architecture and materials

- **Work floors:** earthen 土間 in all the work halls. 連子窓 slatted windows in the loom hall. The storehouse is a 土蔵 with thick lime plaster.
- **Roofs:** board or bark on the industrial halls. Kawara is kept for the inspection hall, the former domain office, which also justifies its SORA eave caps.
- **No glass windows.** The yard is **packed earth**; stone appears only at drains, steps and the river landing (bible §15.1).
- **Surfaces:** soot-black rafters, slag-strewn earth, clay furnace walls in dry, wet and cracked states, and weathered granite at the cut face.

### 4.8 Clothing

- **Workers:** 小袖 with 襷 and 手拭い, 前掛け aprons, bare feet or 草鞋. Hemp (麻) is still common among labourers; cotton was spreading in this period (**verify** the mix).
- **Smiths:** short-sleeved work kosode with heavy aprons and 手甲. Avoid later 半纏-style livery as a hero costume.
- **Okinu:** indigo kosode and tasuki. **Kohagi:** indigo peddler's clothes and 手甲, never the black "ninja suit" (bible §4.6). **Oyuki:** kosode and tasuki, with her 矢立 and soroban.
- **Aliens:** grey coats. They carry the ledger sigil, **never** the SORA mon.

### 4.9 Horses and tack (b17)

- **Pack horses (駄馬):** native horses about 130 cm at the withers, one bay and one chestnut.
- **Tack:** the 荷鞍 pack saddle, 腹帯, 鞦 and straw 馬沓, with loads balanced on both sides and SORA-dyed 荷覆い covers.
- **Riding:** nobody rides in ch05.
- See bible §4.5 and the [tack references](../historical-horse-tack-art-reference.md). The pack saddle is a new asset shared with ch04.

### 4.10 Period checklist for ch05

**Use:**

- foot bellows and a clay furnace rebuilt for each smelt;
- 大鍛冶 and 小鍛冶;
- 高機 and 空引機;
- 幟 with 乳 loops;
- 割符, 焼印, 花押, 爪印, 算盤;
- 土間, 連子窓, 土蔵;
- 駄馬 with 荷鞍.

**Avoid:**

- 天秤鞴;
- 座繰り as a hero prop (**verify**);
- Jacquard cards;
- glass windows;
- 招き猫;
- paved yards;
- the black ninja suit;
- cyan on any League object (the carbine coil glows jade);
- the SORA mon on any alien object.

### 4.11 How the SORA kamon appears in ch05

Source: the exact supplied SVG, from its two original paths (`Content/SourceArt/UI/sora_logo_NOtext2.svg`, SHA-256 `d66413a7…0910`; see [SORA kamon runtime art](../sora-kamon-runtime-art.md)).

| Surface | Beat | Treatment |
|---|---|---|
| Nyaakoto's sode and dō | All | Existing runtime placements |
| League chalk marks | b02 (`c01`); the tatara hall door after b06 | Charcoal, bolder than in ch04 |
| Arc Carbine receiver cheeks | b09, b10 | Existing `SM_Nyaagyu_ArcCarbine` placements |
| **Brand across the split tally** | b12 | Mirror-reversed brand face. Half the mark on each half |
| Registry seal | b08, b09, b11 toasts; b12; chapter-complete page | Vermillion 朱印 in the UI |
| **Silk nobori** | b11 (woven), b18 (raised) | White on indigo; becomes the League's main banner |
| Inspection-hall eave caps | b12 | Existing `NyaagyuSoraEaveCap` study |
| Crate stamp | Yard, b17 | Existing `SM_Nyaagyu_CargoStack` |
| Pack covers (荷覆い) | b17 | Dyed cloth |
| Registry page pasted over the quota board | End of b12, b18 | The only time the mon sits on alien hardware, as paper over it. The board itself shows only the ledger sigil |
| UI | All | Objective marker, save indicator, the 第五章 title card with its vermillion seal |

### 4.12 Sources and references

Links are given only where they already appear in project documents. Institutions without links are named for the historian to cite exactly.

- **Tatara:**
  - The Society for the Preservation of Japanese Art Swords (日本美術刀剣保存協会), which operates the 日刀保たたら in Okuizumo, Shimane;
  - the 和鋼博物館 (Yasugi, Shimane);
  - 菅谷たたら山内 (Unnan, Shimane), the surviving takadono;
  - 金屋子神社 (Yasugi).
- **Weaving:** the 西陣織会館 and 西陣織工業組合 (Kyoto), for 高機 and 空引機 history.
- **Naginata:** [All Japan Naginata Federation](https://naginata.jp/naginata/viewpoint.html).
- **Kyūdō:** [All Japan Kyudo Federation, 射法](https://www.kyudo.jp/howto/syaho.html).
- **Tack:** [The Met 2000.405 (kura)](https://www.metmuseum.org/art/collection/search/26572) and the other records in the [tack reference](../historical-horse-tack-art-reference.md).
- **Dictionaries:** standard Japanese dictionaries (日本国語大辞典, デジタル大辞泉) for 相槌, 割符 and 爪印. The 国史大辞典 for 割符 as a bill of exchange.
- **Bible cross-references:** §2.2 (charter), §3 (school), §4 (arms, tack), §15.2 (ch05 direction), §17 (kamon), §19 (checklist).

---

## 5. Art and audio asset list

Status key:

- **Existing:** in the repo now (path given). Source art has not passed the photoreal gate unless stated.
- **Partial:** existing source that needs a photoreal pass or a variant.
- **Needed:** to be made, or taken from a free asset whose license allows it (bible §15; user directive 17).

Every asset must pass the [photoreal acceptance](../art-direction/photoreal-acceptance.md) gates before it ships.

### 5.1 Environment kits and materials

| Asset | Use (beats) | Status | Source / owner |
|---|---|---|---|
| Arena 2 yard dressing: charcoal-bale stack wall, iron-sand bin wall, ingot skid, trough and cart over the kernel boxes | b10, b17, b18 | Needed | C2 |
| Tatara hall shell: timber frame, board-and-bark roof, ridge vent, earth floor | b06, b07, b16 | Needed | C3. Reference 菅谷たたら (§4.1) |
| Clay furnace (釜) with tuyères, tapping holes, and dry, wet and cracked states; 床釣り cutaway for the codex | b06, b07, b16, b18 | Needed | C3 |
| Foot bellows (踏鞴) platforms with tread boards | b06, b07 | Needed | C3. **Not** 天秤鞴 |
| Alien gantry deck, gratings, stanchions, channel gates | b14–b16 | Needed | C3, sharing the hard-surface kit with the vault and flagship |
| Iron-sand slope: cut face, basins, flume and boardwalk, tailings, hut | b02 | Needed | C3, with a mesh terrain tile per [mesh-terrain-nyaagyu.md](../mesh-terrain-nyaagyu.md) |
| Sluice boards and weirs | b02 | Partial | `Content/SourceArt/Environment/NyaagyuSluice/SM_Nyaagyu_IrrigationSluice.fbx` (kitbash) |
| Channel and flume segments | b02, b03 culvert | Partial | `Content/SourceArt/Environment/NyaagyuWaterCourt/SM_Nyaagyu_WaterCourt_4m.fbx`, `SM_Nyaagyu_BambooRill_4m.fbx` |
| Slope vegetation | b02 | Existing (CC0) | `Content/SourceArt/Environment/PolyHaven/Fern02`, `PineSaplingSmall`, `TreeSmall02` |
| PBR palette: timber, rusty iron, stone floor, plaster, mud and leaves, roof tiles | All | Existing (CC0) | `Content/SourceArt/Environment/PolyHaven/{wood_planks_dirt, rusty_metal_02, stone_floor, WhitePlaster02, brown_mud_leaves_01, GreyRoofTiles}` |
| New materials: 真砂 granite cut face; soot-black rafters; slag-strewn earth; molten iron and slag; wet clay; indigo-stained floorboards | b02–b16 | Needed | C3 |
| Reeling shed: pots on braziers, cocoon shelves, loft, ridge vent | b01, b03 | Needed | C3 |
| Loom hall shell: 連子窓, overseer gallery, office | b05, b11 | Needed | C3 |
| Levy loom | b01, b05, b11 | Partial | `Content/SourceArt/Environment/SilkFoundryLoom/SM_SilkFoundry_LevyLoom.fbx`, imported at `/Game/Generated/Environment/Props/SM_SilkFoundry_LevyLoom`. The procedural wood is stylized and needs a photoreal pass |
| Loom variants: meter smashed; **空引機 draw-loom tower**; automaton donor frame | b05, b11, b14 | Needed | C3, derived from the levy loom source |
| Refining forge: hearths, anvils, quench tub, tong racks, pig-iron stock | b08, b09 | Needed | C3. Reuse `/Game/Generated/Meshes/M_ForgedSteel` and `/Game/Generated/Environment/Props/M_Dojo_BlackenedIron` |
| Inspection hall roof | b12 | Partial | `Content/SourceArt/Environment/NyaagyuKawaraBay`, `NyaagyuSoraEaveCapStudy` (studies) |
| Shōji | b12 | Partial | `Content/SourceArt/Environment/ShojiPaperArtReview`. Fails the fibre-repetition gate |
| Levy storehouse (土蔵) | b13 | Existing | `Content/SourceArt/Environment/NyaagyuKura`, `NyaagyuKuraFront`; `/Game/Generated/Environment/Props/SM_Nyaagyu_ProvisionKura`. Interior shelves are Needed |
| Casting floor: sand beds, crucibles, ingot stacks, channel heads | b14, b15 | Needed | C3 |
| Charcoal shed and charcoal-bale (炭俵) kit | b03, b04, yard | Needed | C3 |

### 5.2 Props

| Asset | Beats | Status | Source / owner |
|---|---|---|---|
| Quota board (alien slab) with animated numerals and scanner | b01, b10, b12, b18 | Partial | Derive from `Content/SourceArt/Environment/StreetDebtTerminal/SM_Alien_StreetDebtTerminal.fbx` and `/Game/Generated/Environment/Props/M_StreetTerminal_*` |
| Iota's twin message slate (palm-sized alien handheld, ejected from the quota board) | b18 (and ch06) | Needed | C3, shared with the ch06 script's "key-slate and twin message slate"; cyan is allowed on alien objects |
| 「昼寝禁止」 notice (decal on seized washi) | b01, b18 | Needed | C3 / L4 font (SIL OFL font already in the project) |
| Levy meters, pot variant | b01, b03 | Partial | Meter exists on the levy loom source |
| Debt collars (縛債の首輪) with a cut state | b02–b05 | Needed | C6 (shared with ch03 and ch04) |
| Cocoon pots, braziers, trays, mulberry baskets, skeins, indigo vats | b01, b03, b05 | Needed | C3 |
| Iron-sand bins, clay repair tubs | b06, b07 | Needed | C3 |
| Kōzō's 小鎚; hero 向こう鎚 (weapon 8), tongs, anvil | b08 | Needed | C5. `SM_Weapon_08` exists only as a primitive placeholder |
| 尖根 arrowheads (24) and finished war arrows | b08, b12 | Needed | C5. Shaft and fletch materials exist: `/Game/ArtReview/Characters/M_Hero_BambooArrowShaft`, `M_Hero_RedArrowFletch` |
| Arc Carbine | b09, b10 | Existing | `Content/SourceArt/Weapons/Original/SM_Nyaagyu_ArcCarbine.fbx` (SORA mon on receivers); `/Game/Generated/Meshes/SM_Nyaagyu_ArcCarbine` |
| Arc Carbine exploded assembly and a jade coil re-tint | b09 | Needed | C5 (variant of the above; `M_Arc_IonJade` exists) |
| Captured alien coil crates | b09, b17 | Needed | C3 |
| 割符 tally stick and halves; **SORA brand iron** with a mirror-reversed face from the pinned SVG | b12 | Needed | C3. SVG exists: `Content/SourceArt/UI/sora_logo_NOtext2.svg` |
| Registry book, 矢立, soroban, balance scale, lots box, tally box | b10–b12 | Needed | C3 (shared with the Hidden Valley registry desk, ch02/ch04) |
| Silk nobori (cloth sim) with the woven mon, and its L-pole | b11, b18 | Needed | C3 / C8 |
| Kanayago scroll, levy ledgers, Washio notice, output book | b13 | Needed | C3 (paper kit shared with seizure notices) |
| Cargo stacks | Yard | Existing | `Content/SourceArt/Environment/NyaagyuCargoStack/SM_Nyaagyu_CargoStack.fbx` |
| Lantern post | South lane | Existing | `Content/SourceArt/Environment/Original/SM_Edo_LanternPost.fbx` |
| Andon, kagaribi stands | b02–b12 | Needed | C3 |
| Alien floodlight post with cable junction | b02 | Needed | C3 |
| Pack saddle 荷鞍, loads, 荷覆い, straw 馬沓 | b17 | Needed | C6 (shared with ch04) |

### 5.3 Characters

| Character | Status | Notes |
|---|---|---|
| Nyaakoto | Partial | `Content/SourceArt/SK_NyaagyuSamurai.fbx` runtime skin and `Characters/Hero` studies. Photoreal gate pending (B5) |
| Kohagi, Okinu, Kōzō, Tetsugorō, Oyuki, Otane | Needed | Shared across chapters. Kōzō gets a clouded left eye (proposal) |
| Tarifa | Needed | Goggles, soot coat, tether arm, coolant-mantle shimmer |
| Iota | Not needed in ch05 | Voice plus quota-board glyphs only |
| Artisans: 4 reelers, 4 weavers, 2 bellows crew, 2 laborers; crowd variants to 30 | Needed | Hairless-alien cost savings do not apply; use card fur for crowds (bible §15.1) |
| Enforcer family: rifle, blade, shield, grenadier, marksman | Partial | `Content/SourceArt/SK_AlienBanker.fbx` prototype as the base |
| Drone | Needed | Floating disc with a cyan eye (bible §7) |
| **Loom automaton** | Needed | New (§2.4); built from the loom kit plus alien servos |
| Pack horses ×2 | Partial | `Content/SourceArt/Horses/Nyaagyu/SM_Nyaagyu_HorseAndTack.fbx` (stylized) with bay and chestnut coats and a pack-saddle swap |

### 5.4 Animation

Existing: `A_NyaagyuSamurai_Walk.fbx` and `A_AlienBanker_Walk.fbx` (prototype walks only). First-person paw grips exist for katana and yumi (`Content/SourceArt/Characters/NyaakotoFirstPersonPaws`). Everything else below is **Needed** (C7, with review by a practitioner and an equine animator where marked).

- **First person:**
  - bellows tread, left and right;
  - sledge strike, looping on the 600 ms cue;
  - 空引き cord pull;
  - Arc Carbine shoulder, fire and reload;
  - naginata thrust, sweep and obstructed bounce (practitioner review);
  - seal-cut;
  - one-handed carry;
  - brand press;
  - naginata, hammer and carbine paw grips.
- **NPCs:**
  - Kōzō's yokoza taps;
  - Okinu's weave cycle (treadle, shuttle, beater) and naginata set;
  - reeling;
  - escort crouch-walk and hide;
  - meter smashing and crowd;
  - loading the pack horses (equine review of their idles);
  - curled sleep (b18).
- **Enemies:**
  - the loom automaton's locomotion, thrust, slam, stagger and melt death;
  - Tarifa's set: lash, double lash, rod sweep, slam, snapped-cable stun, mantle overload, fall;
  - the conscript's knockdown and freed reactions.
- **Cinematics (C9):** `LS_Ch05_B01_QuotaBoard`, `B12_FirstXOR`, `B14_ChannelsOpen`, `B16_TarifaIntro`, `B16_TarifaFall`, `B18_NoboriDawn`. All have letterboxed `camera_blend` fallbacks.

### 5.5 VFX (C8, Niagara; all Needed)

- **Furnace and forge:**
  - furnace flame with 3 gauge states (red / 山吹 / white) driven by the bellows rate;
  - tuyère glow;
  - sparks, capped on Mac;
  - soot and smoke volumes;
  - quench steam;
  - brand-iron smoke.
- **Melt and storm:**
  - molten flow;
  - **channel-gate amber pulse** (animated edges, distinct from the melt glow);
  - slag crust;
  - steam bursts;
  - rain on hot iron;
  - thunderstorm rain and lightning, respecting flash reduction.
- **Water and silk:** channel foam and splashes, culvert drips, cocoon-pot steam, nobori cloth in the wind (dawn).
- **Combat telegraphs:**
  - seal-cut (the cyan seal dies);
  - drone searchlight cone;
  - marksman lock glint (900 ms);
  - Tarifa's cyan tether filament;
  - amber sweep and ring decals;
  - automaton core glow and warp-thread tendons.

### 5.6 SFX (L5; CC0 or synthesized, with hashes and license pins; all Needed)

- **Tatara and forge:**
  - bellows creak and furnace roar, scaled to rate;
  - furnace "breathing";
  - kera extraction;
  - aizuchi pair: the small-hammer *tink* and the sledge's *thud*;
  - quench hiss.
- **Silk:** loom clack and beater thump, shuttle whirr, figure-cord pull, reeling-pot bubble.
- **Water and footsteps:** running water in the channels, gravel footsteps on tailings, culvert echo.
- **Weather:** rain on board roofs, rain on kawara, thunder.
- **Melt and machines:**
  - captioned steam hiss telegraph;
  - molten pour;
  - channel-gate clank plus a 2 s rising hum;
  - tether whine and snap;
  - automaton servos and shuttle-arm clatter.
- **Aliens:** PA chime, levy-meter ticks, collar chime and snap, drone hum, enemy carbine, grenade arc whistle.
- **League:** Arc Carbine fire and reload, coil-matchlock shots (League allies).
- **Horses:** pack-horse snorts, hooves on packed earth, harness creak.
- **Ceremony and crowd:** brand press, tally split crack, crowd murmur and the crowd's quiet cheer.

### 5.7 Music cues (L5 stem states; all Needed)

| State | Beats | Direction |
|---|---|---|
| `ch05_ridge_night` | b01 | Shakuhachi and low drone; distant heat lightning |
| `ch05_stealth_water` | b02 | Sparse; the water sound carries the texture |
| `ch05_escort_hush` | b03 | Pulse drops out whenever the signal is given |
| `ch05_refuge` | b04 | Warm, close, quiet koto |
| `ch05_uprising` | b05 | Taiko entry as the shuttles are dropped |
| `ch05_bellows` | b06 | **Tempo-locked** to the player's tread rate (60–78 BPM) |
| `ch05_defend_furnace` | b07 | Driving taiko over a furnace drone |
| `ch05_aizuchi` | b08 | 100 BPM; the anvil is the percussion |
| `ch05_gunsmith` | b09 | Restrained; clockwork plucks |
| `ch05_yard_counter` | b10 | Combat stem B |
| `ch05_sorabiki` | b11 | 80 BPM; the loom's clack on the beat |
| `ch05_first_xor` | b12 | Theme statement: the League motif in full for the first time, on strings and shō |
| `ch05_storehouse_storm` | b13 | Rain, low strings |
| `ch05_storm_break` | b14 | Alien low brass against a thunder hit |
| `ch05_casting_floor` | b15 | Combat stem A with metallic percussion |
| `boss_tarifa` (P1 → P2 → P3) | b16 | The mechanical ostinato accelerates by phase; P3 adds the rain |
| `ch05_dawn_loading` | b17 | Morning birds, a solo flute |
| `ch05_nobori_dawn` | b18 | League motif, then an alien tone under it as Iota speaks |

### 5.8 UI (L4)

- The chapter title card 第五章 工房の蜂起 with the vermillion SORA seal.
- The ch05 registry page, with three entries, split-tally icons and three seals.
- Registry toasts.
- The flame gauge (color plus notches).
- The aizuchi cue ring and the sorabiki call marker.
- A heat-slot warning icon.
- Tarifa's boss bar, with a mantle-state pip.
- Objective marker and save indicator using the SORA mon (the SVG exists).
- The 16 prompts in §3.4.

---

## 6. Open items and decisions for owners

1. **Proposed dialogue events** (L1, for the §12.1 event list):

   | Event | Meaning |
   |---|---|
   | `wave_start:<n>` | Wave n spawns |
   | `interact:<id>`, `interact_done:<id>` | An interact starts or completes |
   | `polearm_obstructed[:first]` | A polearm sweep is blocked by a layout collider |
   | `rate_band:<below\|in\|above>[:first]` | Crank rate against its band, with a 15 s cooldown when repeatable |
   | `target_hp_below:<actor>:<frac>` | A defend target falls below a fraction of its HP |
   | `step_start:<kind>`, `step_complete:<kind>:<n>` | A manufacture step starts or completes (the ch01 script's names) |
   | `collectible_found:<id>` | A collectible is picked up |
   | `pattern_countered:<pattern>`, `boss_state:<state>` | Boss reactions |
   | `enemy_retreat`, `conscript_attack`, `conscript_downed`, `conscript_freed`, `nonlethal_focus` | L2 bark hooks |
   | `look_at:<actor>` | HUD prompts only |

   `pattern:<id>` is already used in the bible's §12.4 example.
2. **Proposed beat fields** (all under `x_ext`):
   - escort `pre_interacts`, `guards`, `on_detected`, `detected_wave`, `hide_spots`;
   - wave trigger `reinforce` (for waves named by `on_detected: reinforce:<id>`);
   - `equip_on_start`, `polearm_obstruction`, `flame_gauge`, `coop_npc_rate`, `weapon_grant_at`, `proposed_mechanic_flag`, `hammer_rhythm_phrase`, `hazards`, `interactive_press`, `posts_registry_page_on`, `site_restores_on`, `fall_policy`, the mantle values, and the `interacts` gates on the b04 dialogue.
3. **The `manufacture` flag.** The ch01 script unlocks `manufacture` at ch01.b09 (bible §10), so ch05.b08 unlocks only weapon 8 and keeps a flag unlocking only once. If L1 wants a flag for the rhythm variant, this script proposes `hammer_rhythm` (the name the ch01 script suggests) under `x_ext.proposed_mechanic_flag`. It would need adding to the §12.1 list.
4. **New place ids:** `pl_sumigoya` (炭小屋, the refuge) and `pl_toritategura` (取立蔵, the levy storehouse). The bible names them only as "refuge" and "foundry storehouse".
5. **New speaker ids:** `enforcer` and `conscript` (bark voices), plus the bible's `weaver`, `foundry_master`, `gunsmith`, `leader`, `farmer_young`, `boss_tarifa` and `clerk` for schema 4.
6. **Collectible ids and mask bits.** Resolved in review (bible §12.5): `collectible_id` is `ch05.c01`–`c06` and `mask_bit` is chapter-local 0–5 in every chapter; the global bit is (chapter − 1) × 6 + `mask_bit` (24–29 here).
7. **Story additions for the bible owner's sign-off:**
   - Tetsugorō was taken by a collection patrol after ch04 and is freed in b03. The ch01 script introduces him as the estate smith, and in ch04 he comes down from the Hidden Valley; the capture sits between those scripts and ch05. In ch07 he issues the foundry-built Repeater, which is consistent with him working at the foundry from here on.
   - Okinu comes from a samurai household, and the naginata was her mother's.
   - Kōzō's clouded eye.
   - Otane is present as the receiver in b12.
   - Iota's contact comes through the quota board's scanner reading the posted registry page, and the board ejects the **twin message slate** that the ch06 script assumes Nyaakoto carries (the bible says only "a message arrives from inside the vault").
   - The Washio transfer notice foreshadows ch06.
   - The forty-night banner.
8. **Catalog anchors.** Lines 1 and 2 are plain-register lines in the mouths of the Kyoto-speaking Okinu and the keigo-speaking Oyuki. They are kept verbatim and staged as deliberate register breaks (§3.1). If the native reviewer (B7) prefers register-true versions, the data team must change `catalog.json` itself; this document does not.
9. **Tarifa's "shield"** is defined as a coolant mantle (70% damage reduction that drops in steam), so ch07 keeps the first energy shields and `shield_break`. L3 should confirm.
10. **Historian flags** (§4): the tall 高殿 is a late form; tatara and kanna-nagashi in Yamato are fiction; the basin names; the 座繰り dating; the seal practices; arrowhead shapes. **Practitioner review:** naginata motion in tight aisles, and the "awase against a pull" presentation.
11. **Kernel dependency:** the yard dressing assumes `map_walls(2)` from `first-release-6`. C2 must re-fit it when L6 F4 lands.
12. **Cross-chapter conventions** (these differ between the parallel chapter scripts, so L1 should normalize them):
    - **Line-id token:** resolved in review (bible §12.5): every chapter now uses character tokens (`ch05.b04.okinu.005`, `kozo`, `otane`), as in the §12.4 example; the `speaker` field keeps the speaker id.
    - **Line numbering:** ch05 numbers lines running within the beat.
    - **Extension fields:** resolved in review: ch05 keeps them in one `x_ext` block per beat; other chapters use `x_` keys (bible §12.5).
    - **Shared event names:** `wave_start:<n>`, `interact:<id>`, `step_start:<kind>` and `step_complete:<kind>:<n>` follow the ch01 script's §4.6 names.
    - **Other continuity:** the ch06 script's archive posts reuse this chapter's reach-obstruction rule. The ch08 script's forge motif reuses `ch05_aizuchi`. Its forward camp flies this chapter's nobori.

---

## 7. Machine-readable beat data (YAML)

Generated from the same source as the tables above, and checked:

- the beat `target_s` values sum to 3,600;
- sites 0, 1 and 2 are each used once, in order;
- weapon unlocks come in the order 20 → 8 → 1;
- the only registry entries are on `production_task` beats;
- checkpoint spacing is at most 300 s;
- every line has `ja`, `en` and a known speaker;
- EN is at most 2 lines of 42 characters and at most 17 cps;
- the file parses as YAML.

Taxonomy fields follow bible §12, and extensions sit under `x_ext`. The b04 lines are inline in the `dialogue` beat, as §12.2 specifies; every other line is in `lines` (bible §12.5). The chapter-wide bark pool is `x_bark_pool`.

```yaml
schema: "sora-campaign-chapter/proposal-1 (story-bible §12; convert to Content/Data/campaign/chapter_05.json, schema 4)"
chapter: "ch05_silk_foundry"
title_ja: "工房の蜂起"
title_en: "The Foundry Uprising"
map: 2
target_s: 3600
x_chapter_meta:
  index: 5
  in_fiction_time: "元和九年 水無月七日頃 (Genna 9, about the 7th day of the 6th month; first-quarter moon), 22:00 → 05:00"
  unlock_order: [20, 8, 1]
  sites:
    "0": "ch05.b03"
    "1": "ch05.b06"
    "2": "ch05.b12"
  boss: "boss_tarifa"
  new_places_proposed: ["pl_sumigoya", "pl_toritategura"]
  new_speakers_proposed: ["enforcer", "conscript"]
beats:
  - id: "ch05.b01"
    type: "cinematic"
    place: "pl_silk_foundry"
    title_ja: "絹の工房"
    title_en: "The Silk Foundry"
    target_s: 120
    checkpoint: true
    sequence: "/Game/Cinematics/Ch05/LS_Ch05_B01_QuotaBoard"
    duration_s: 120
    skippable: true
    fallback: "camera_blend"
    end_state:
      player_transform: "ps_ch05_kanna_ridge"
      equipped: [0, 18]
    music: "ch05_ridge_night"
    x_ext:
      diegetic_text: ["sign.ch05.quota", "sign.ch05.nap"]
    subtitles: ["ch05.b01.kohagi.001", "ch05.b01.nyaakoto.002", "ch05.b01.tarifa.003", "ch05.b01.tarifa.004", "ch05.b01.kohagi.005"]
  - id: "ch05.b02"
    type: "stealth_zone"
    place: "pl_kanna_nagashi"
    title_ja: "鉄穴の水路を抜けよ"
    title_en: "Slip through the iron-sand channels"
    target_s: 240
    checkpoint: true
    zone: "vol_ch05_kanna"
    guards:
      - id: "g_kanna_upper"
        type: "enforcer_rifle"
        patrol: "pr_kanna_upper_loop"
        sight:
          cone_deg: 90
          range_cm: 2200
          dark_range_cm: 900
        hearing_cm: 1200
      - id: "g_kanna_flume"
        type: "enforcer_rifle"
        patrol: "pr_kanna_flume_line"
        sight:
          cone_deg: 90
          range_cm: 2200
          dark_range_cm: 900
        hearing_cm: 1200
      - id: "g_kanna_pond"
        type: "enforcer_rifle"
        patrol: "pr_kanna_pond_loop"
        sight:
          cone_deg: 90
          range_cm: 2200
          dark_range_cm: 900
        hearing_cm: 1200
      - id: "g_kanna_air"
        type: "drone"
        patrol: "pr_kanna_air_figure8"
        sight:
          cone_deg: 30
          range_cm: 2500
          dark_range_cm: 2500
        hearing_cm: 600
      - id: "g_kanna_laborer_a"
        type: "bound_conscript"
        patrol: "static:sp_kanna_shovel_a"
        sight:
          cone_deg: 60
          range_cm: 600
          dark_range_cm: 400
        hearing_cm: 300
      - id: "g_kanna_laborer_b"
        type: "bound_conscript"
        patrol: "static:sp_kanna_shovel_b"
        sight:
          cone_deg: 60
          range_cm: 600
          dark_range_cm: 400
        hearing_cm: 300
    detection:
      suspicion_rate: 1.0
      alert_threshold: 1.0
      search_s: 20
    takedowns:
      rear: true
      lethal_default: true
    light_sources:
      - {id: "kagaribi_pond", kind: "brazier", extinguish: "interact_hold_s:1.5"}
      - {id: "kagaribi_hut", kind: "brazier", extinguish: "interact_hold_s:1.5"}
      - {id: "flood_upper", kind: "alien_floodlight", extinguish: "arrow:cable_junction", relight_s: 10}
    noise_surfaces:
      - kind: "running_water"
        mult: 0.5
        volumes: ["vol_kanna_channel_main", "vol_kanna_channel_east", "vol_ch05_culvert"]
      - {kind: "gravel", mult: 1.5, volumes: ["vol_kanna_tailings"]}
      - {kind: "puddle", mult: 1.3, volumes: ["vol_kanna_pond_edge"]}
    on_detected: "reinforce:w_kanna_alarm"
    waves:
      - id: "w_kanna_alarm"
        enemies:
          - {type: "enforcer_rifle", count: 2, spawn: "sp_kanna_hut"}
        trigger: "reinforce"
    complete: "exit_reached"
    music: "ch05_stealth_water"
    x_ext:
      exit_volume: "vol_ch05_culvert"
      easy_on_detected: "combat"
      laborer_behavior: "witness: look away; collar-eye reports at 0.5x suspicion; never attack"
      collectibles_here: ["ch05.c01"]
    dialogue:
      - {"on": "beat_start", lines: ["ch05.b02.kohagi.001"], mode: "ambient"}
      - {"on": "volume_enter:vol_kanna_tailings", lines: ["ch05.b02.kohagi.002"], mode: "ambient"}
      - {"on": "volume_enter:vol_kanna_laborers", lines: ["ch05.b02.kohagi.003"], mode: "ambient"}
      - "on": "volume_enter:vol_kanna_laborers_near"
        lines: ["ch05.b02.conscript.004", "ch05.b02.nyaakoto.005"]
        mode: "ambient"
  - id: "ch05.b03"
    type: "production_task"
    task: "escort"
    place: "pl_itotoriba"
    title_ja: "職人を解き放ち、炭小屋へ導け"
    title_en: "Free the craftspeople and lead them to the charcoal shed"
    target_s: 300
    checkpoint: true
    site: 0
    escort:
      npcs: ["okinu", "tetsugoro", "reeler_a", "reeler_b", "reeler_c", "bellows_boy"]
      path: "spl_ch05_escort_refuge"
      speed_cm_s: 180
      wait_for_player_cm: 800
      fail_on_npc_death: true
      hide_on_signal: true
      npc_health: 120
      down_revive_s: 4
    stealth: true
    music: "ch05_escort_hush"
    x_ext:
      pre_interacts:
        kind: "seal_cut"
        interact_s: 2.0
        targets: ["collar_okinu", "collar_tetsugoro", "collar_reeler_a", "collar_reeler_b", "collar_reeler_c", "collar_bellows_boy"]
      guards:
        - id: "p_south_pair"
          type: "enforcer_rifle"
          count: 2
          patrol: "pr_south_lane"
          sight:
            cone_deg: 90
            range_cm: 2000
            dark_range_cm: 800
          hearing_cm: 1000
        - id: "p_drying_drone"
          type: "drone"
          count: 1
          patrol: "pr_drying_racks"
          sight:
            cone_deg: 30
            range_cm: 2200
            dark_range_cm: 2200
          hearing_cm: 500
        - id: "p_west_gate"
          type: "blade_retainer"
          count: 1
          patrol: "pr_west_lane_gate"
          sight:
            cone_deg: 100
            range_cm: 1600
            dark_range_cm: 700
          hearing_cm: 900
      on_detected: "combat"
      detected_wave:
        enemies:
          - {type: "enforcer_rifle", count: 2, spawn: "sp_south_gate_inner"}
      hide_spots: ["hs_drying_racks", "hs_troughs", "hs_lumber", "hs_fuel_leanto", "hs_charcoal_bales"]
      complete_volume: "vol_refuge"
      companion_invulnerable: ["kohagi"]
      collectibles_here: ["ch05.c02"]
    dialogue:
      - {"on": "interact_done:collar_reeler_a", lines: ["ch05.b03.artisan.001"], mode: "ambient"}
      - "on": "interact_done:collar_okinu"
        lines: ["ch05.b03.okinu.002", "ch05.b03.nyaakoto.003"]
        mode: "ambient"
      - {"on": "interact_done:collar_tetsugoro", lines: ["ch05.b03.tetsugoro.004"], mode: "ambient"}
      - {"on": "progress_at:0.05", lines: ["ch05.b03.kohagi.005"], mode: "ambient"}
      - {"on": "progress_at:0.5", lines: ["ch05.b03.okinu.006"], mode: "ambient"}
      - {"on": "beat_complete", lines: ["ch05.b03.kohagi.007"], mode: "ambient"}
  - id: "ch05.b04"
    type: "dialogue"
    place: "pl_sumigoya"
    title_ja: "炭小屋の談合"
    title_en: "Council in the charcoal shed"
    target_s: 90
    checkpoint: true
    trigger: "beat_start"
    mode: "ambient"
    camera: "soft_lookat"
    priority: "high"
    unlocks:
      weapons: [20]
    music: "ch05_refuge"
    x_ext:
      interacts:
        - id: "naginata_handover"
          grants_weapon: 20
          prompt_after_line: "ch05.b04.okinu.001"
          on_complete_play_from: "ch05.b04.okinu.002"
        - id: "seal_cut_kozo"
          kind: "seal_cut"
          interact_s: 2.0
          prompt_after_line: "ch05.b04.okinu.005"
          on_complete_play_from: "ch05.b04.kozo.006"
      supply_point: "sup_ch05_sumigoya"
      background: "freed artisans cut the remaining collars with shears and chisels from here on (crowd animation)"
    lines:
      - id: "ch05.b04.okinu.001"
        speaker: "weaver"
        ja: "炭は数えはっても、中までは見はらしまへん。"
        en: "They count the charcoal. They never look inside."
        register: "kyoto_soft"
        duration_s: 4.5
      - id: "ch05.b04.okinu.002"
        speaker: "weaver"
        ja: "母の形見どす。貸すだけどすえ。"
        en: "It was my mother's. It is only a loan, mind."
        register: "kyoto_soft"
        duration_s: 3.5
      - id: "ch05.b04.nyaakoto.003"
        speaker: "samurai"
        ja: "……預かる。"
        en: "…I will hold it in trust."
        register: "jidaigeki_plain"
        duration_s: 2.0
      - id: "ch05.b04.tarifa.004"
        speaker: "boss_tarifa"
        ja: "本工房の生産物は、全て当院の担保でございます。"
        en: "All output of this foundry is collateral of this House."
        register: "alien_corporate_keigo"
        duration_s: 5.5
      - id: "ch05.b04.okinu.005"
        speaker: "weaver"
        ja: "絹も鋼も、作ったのはこの手だ。"
        en: "Silk and steel were made by these hands."
        register: "kyoto_plain_steel"
        duration_s: 3.5
      - id: "ch05.b04.kozo.006"
        speaker: "foundry_master"
        ja: "炉ん中で、鉄が二晩寝とる。"
        en: "There's iron two nights deep in that furnace."
        register: "yamato_gruff"
        duration_s: 3.5
      - id: "ch05.b04.kozo.007"
        speaker: "foundry_master"
        ja: "三晩かかる。今夜しかない。"
        en: "It takes three nights. We have tonight."
        register: "yamato_gruff"
        duration_s: 3.5
      - id: "ch05.b04.kohagi.008"
        speaker: "scout"
        ja: "一揆がここを取る。作った物は、帳に付ける。"
        en: "The League takes this place. What's made goes in the registry."
        register: "terse_report"
        duration_s: 5.0
      - id: "ch05.b04.kozo.009"
        speaker: "foundry_master"
        ja: "帳面はええ。わしは鉄しか信じん。"
        en: "Spare me the ledgers. I trust iron."
        register: "yamato_gruff"
        duration_s: 3.5
  - id: "ch05.b05"
    type: "combat_wave"
    place: "pl_hataba"
    title_ja: "機場を取り戻せ"
    title_en: "Take back the loom hall"
    target_s: 300
    checkpoint: true
    bounds: "vol_ch05_hataba"
    waves:
      - enemies:
          - {type: "blade_retainer", count: 2, spawn: "sp_hataba_office"}
          - {type: "enforcer_rifle", count: 2, spawn: "sp_hataba_gallery"}
        trigger: "start"
      - enemies:
          - {type: "bound_conscript", count: 3, spawn: "sp_hataba_south_door"}
          - {type: "enforcer_rifle", count: 2, spawn: "sp_hataba_west_door"}
        trigger: "alive_below:2"
      - enemies:
          - {type: "shield_enforcer", count: 1, spawn: "sp_hataba_west_door"}
          - {type: "enforcer_rifle", count: 2, spawn: "sp_hataba_gallery"}
          - {type: "drone", count: 1, spawn: "sp_hataba_roof_vent"}
        trigger: "prev_cleared"
    complete: "all_waves_cleared"
    max_alive: 6
    allies:
      - {npc: "okinu", role: "melee_naginata", downable: true}
      - {npc: "weaver_a", role: "meter_breaker", downable: true}
      - {npc: "weaver_b", role: "meter_breaker", downable: true}
      - {npc: "weaver_c", role: "meter_breaker", downable: true}
      - {npc: "weaver_d", role: "meter_breaker", downable: true}
    nonlethal_types: ["bound_conscript"]
    music: "ch05_uprising"
    x_ext:
      equip_on_start:
        polearm_slot: 20
      polearm_obstruction:
        colliders: "loom_frames"
        feedback: "bounce_s:0.3"
        thrust_unaffected: true
    dialogue:
      - {"on": "beat_start", lines: ["ch05.b05.okinu.001"], mode: "ambient"}
      - {"on": "wave_start:1", lines: ["ch05.b05.tarifa.002"], mode: "radio"}
      - {"on": "wave_start:2", lines: ["ch05.b05.okinu.003"], mode: "ambient"}
      - {"on": "polearm_obstructed:first", lines: ["ch05.b05.nyaakoto.004"], mode: "ambient"}
      - {"on": "wave_start:3", lines: ["ch05.b05.artisan.005"], mode: "ambient"}
      - {"on": "beat_complete", lines: ["ch05.b05.artisan.006"], mode: "ambient"}
  - id: "ch05.b06"
    type: "production_task"
    task: "crank"
    place: "pl_takadono"
    title_ja: "踏鞴を踏み、炉を保て"
    title_en: "Tread the bellows and keep the furnace alive"
    target_s: 240
    checkpoint: true
    site: 1
    crank:
      actor: "tatara_bellows_south"
      turns_required: 90
      turn_rate_band: [0.8, 1.3]
      progress_decay_per_s: 0.01
      stamina_per_turn: 2
      interruptible: true
      coop_npc: "bellows_boy"
    waves:
      - enemies:
          - {type: "drone", count: 1, spawn: "sp_takadono_vent"}
        trigger: "progress_at:0.6"
    music: "ch05_bellows"
    x_ext:
      input: "alternate_left_right_tread (one turn = one L+R cycle)"
      flame_gauge:
        below: "dull_red + 1 notch"
        in: "golden_yellow (山吹) + 2 notches"
        above: "white with sparks + 3 notches; stamina cost x2"
      coop_npc_rate: 0.5
      coop_npc_progress_mult: 0.4
    dialogue:
      - "on": "beat_start"
        lines: ["ch05.b06.kozo.001", "ch05.b06.kozo.002"]
        mode: "ambient"
      - {"on": "rate_band:below", lines: ["ch05.b06.kozo.003"], mode: "ambient"}
      - {"on": "rate_band:in:first", lines: ["ch05.b06.kozo.004"], mode: "ambient"}
      - {"on": "rate_band:above", lines: ["ch05.b06.kozo.005"], mode: "ambient"}
      - {"on": "progress_at:0.4", lines: ["ch05.b06.kozo.006"], mode: "ambient"}
      - "on": "progress_at:0.7"
        lines: ["ch05.b06.nyaakoto.007", "ch05.b06.kozo.008"]
        mode: "ambient"
  - id: "ch05.b07"
    type: "production_task"
    task: "defend"
    place: "pl_takadono"
    title_ja: "炉と村下を守れ"
    title_en: "Defend the furnace and the master smelter"
    target_s: 300
    checkpoint: true
    defend:
      targets:
        - {actor: "tatara_furnace", hp: 1500}
        - {actor: "npc:kozo", hp: 300}
      duration_s: 180
      fail_on_target_destroyed: true
      repair_interact:
        actors: ["clay_tub_w", "clay_tub_e", "clay_tub_n"]
        hold_s: 3
        heal: 150
        uses_each: 1
    waves:
      - enemies:
          - {type: "enforcer_rifle", count: 3, spawn: "sp_takadono_south_door"}
        trigger: "start"
      - enemies:
          - {type: "grenadier", count: 1, spawn: "sp_takadono_gantry_ne"}
          - {type: "blade_retainer", count: 2, spawn: "sp_takadono_south_door"}
        trigger: "after_s:40"
      - enemies:
          - {type: "drone", count: 2, spawn: "sp_takadono_vent"}
          - {type: "enforcer_rifle", count: 2, spawn: "sp_takadono_west_door"}
        trigger: "after_s:90"
      - enemies:
          - {type: "grenadier", count: 1, spawn: "sp_takadono_gantry_ne"}
          - {type: "shield_enforcer", count: 1, spawn: "sp_takadono_south_door"}
          - {type: "enforcer_rifle", count: 2, spawn: "sp_takadono_south_door"}
        trigger: "after_s:130"
    max_alive: 6
    music: "ch05_defend_furnace"
    x_ext:
      kozo:
        downable: true
        revive_s: 4
        fail_after_down_s: 25
      grenadier_target_priority: "tatara_furnace"
      drone_behavior: "seizure_net on bellows crew; netted crew stop the bellows (furnace takes 5 HP/s until freed)"
    dialogue:
      - {"on": "beat_start", lines: ["ch05.b07.tarifa.001", "ch05.b07.kozo.002"], mode: "radio"}
      - {"on": "target_hp_below:tatara_furnace:0.7", lines: ["ch05.b07.kozo.003"], mode: "ambient"}
      - {"on": "npc_downed:kozo", lines: ["ch05.b07.kozo.004"], mode: "ambient"}
      - {"on": "beat_complete", lines: ["ch05.b07.kozo.005"], mode: "ambient"}
  - id: "ch05.b08"
    type: "production_task"
    task: "manufacture"
    place: "pl_okaji"
    title_ja: "鏃を打て"
    title_en: "Forge arrowheads"
    target_s: 240
    checkpoint: true
    manufacture:
      recipe: "arrowhead_togarine_x24"
      stations: ["okaji_kokaji_hearth", "okaji_anvil_kozo", "okaji_quench_tub"]
      steps:
        - {kind: "heat", count: 4}
        - kind: "hammer_rhythm"
          count: 4
          timing:
            beat_ms: 600
            tolerance_ms: 90
        - {kind: "quench", count: 4}
        - {kind: "inspect", count: 1}
      output:
        item: "arrowhead"
        qty: 24
    registry:
      item_ja: "鏃"
      item_en: "Arrowheads"
      qty: 24
      unit_ja: "本"
      unit_en: "pieces"
    unlocks:
      weapons: [8]
    music: "ch05_aizuchi"
    x_ext:
      weapon_grant_at: "beat_start"
      proposed_mechanic_flag: "hammer_rhythm"
      hammer_rhythm_phrase:
        strikes: 8
        pass_ratio: 0.75
        cue: "kozo_kozuchi_tap"
        cue_to_strike_ms: 600
      quiver_refill: 12
      arrow_reserve_at_supply: 12
      collectibles_here: ["ch05.c06"]
    dialogue:
      - "on": "beat_start"
        lines: ["ch05.b08.kozo.001", "ch05.b08.kozo.002"]
        mode: "ambient"
      - "on": "progress_at:0.5"
        lines: ["ch05.b08.nyaakoto.003", "ch05.b08.kozo.004"]
        mode: "ambient"
      - "on": "beat_complete"
        lines: ["ch05.b08.kozo.005", "ch05.b08.kozo.006"]
        mode: "ambient"
      - {"on": "collectible_found:ch05.c06", lines: ["ch05.b08.sekireisai.007"], mode: "ambient"}
  - id: "ch05.b09"
    type: "production_task"
    task: "manufacture"
    place: "pl_okaji"
    title_ja: "アーク・カービンを組め"
    title_en: "Assemble the Arc Carbine"
    target_s: 180
    checkpoint: true
    manufacture:
      recipe: "arc_carbine"
      stations: ["gunsmith_bench", "gunsmith_vise"]
      steps:
        - {kind: "inspect", count: 1}
        - {kind: "assemble", count: 1}
        - {kind: "assemble", count: 2}
        - {kind: "inspect", count: 1}
      output:
        item: "arc_carbine"
        qty: 3
    registry:
      item_ja: "アーク・カービン"
      item_en: "Arc Carbines"
      qty: 3
      unit_ja: "挺"
      unit_en: "guns"
    unlocks:
      weapons: [1]
    music: "ch05_gunsmith"
    x_ext:
      step_labels: ["bore sighting against a lamp", "seat the captured coil (align, hold 1.5 s)", "receiver plates L and R with the SORA mon", "dry-fire check"]
      fiction_split: "player builds 1; Tetsugorō finishes 2 (registry qty 3)"
      supply_point: "sup_ch05_okaji"
    dialogue:
      - {"on": "beat_start", lines: ["ch05.b09.tetsugoro.001"], mode: "ambient"}
      - {"on": "step_start:inspect", lines: ["ch05.b09.tetsugoro.002"], mode: "ambient"}
      - {"on": "step_start:assemble", lines: ["ch05.b09.tetsugoro.003"], mode: "ambient"}
      - {"on": "step_complete:assemble:1", lines: ["ch05.b09.tetsugoro.004"], mode: "ambient"}
      - {"on": "beat_complete", lines: ["ch05.b09.tetsugoro.005"], mode: "ambient"}
  - id: "ch05.b10"
    type: "combat_wave"
    place: "pl_silk_foundry"
    title_ja: "反撃を退けよ"
    title_en: "Repel the counterattack"
    target_s: 180
    checkpoint: true
    bounds: "vol_ch05_yard"
    waves:
      - enemies:
          - {type: "enforcer_rifle", count: 4, spawn: "sp_yard_south_gate"}
        trigger: "start"
      - enemies:
          - {type: "marksman", count: 1, spawn: "sp_itotoriba_roof_ridge"}
          - {type: "drone", count: 2, spawn: "sp_yard_river_air"}
        trigger: "alive_below:2"
      - enemies:
          - {type: "shield_enforcer", count: 1, spawn: "sp_yard_south_gate"}
          - {type: "enforcer_rifle", count: 2, spawn: "sp_yard_river_gate"}
          - {type: "grenadier", count: 1, spawn: "sp_yard_river_gate"}
        trigger: "prev_cleared"
    complete: "all_waves_cleared"
    max_alive: 6
    allies:
      - {npc: "tetsugoro", role: "arc_carbine", downable: true}
      - {npc: "otane", role: "kusarigama", downable: true}
      - {npc: "league_teppo_a", role: "coil_matchlock", downable: true}
      - {npc: "league_teppo_b", role: "coil_matchlock", downable: true}
    music: "ch05_yard_counter"
    x_ext:
      equip_on_start:
        firearm_slot: 1
      allies_join:
        otane: "wave:3"
        league_teppo_a: "wave:3"
        league_teppo_b: "wave:3"
      marksman_glint_ms: 900
    dialogue:
      - {"on": "beat_start", lines: ["ch05.b10.tetsugoro.001"], mode: "ambient"}
      - {"on": "wave_start:2", lines: ["ch05.b10.kohagi.002"], mode: "ambient"}
      - {"on": "wave_start:3", lines: ["ch05.b10.otane.003"], mode: "ambient"}
      - {"on": "beat_complete", lines: ["ch05.b10.oyuki.004"], mode: "ambient"}
  - id: "ch05.b11"
    type: "production_task"
    task: "manufacture"
    place: "pl_hataba"
    title_ja: "空紋の幟を織れ"
    title_en: "Weave the Sora banner"
    target_s: 120
    checkpoint: true
    manufacture:
      recipe: "sora_nobori"
      stations: ["hataba_sorabiki_loom"]
      steps:
        - {kind: "inspect", count: 1}
        - kind: "weave_rhythm"
          count: 24
          timing:
            beat_ms: 750
            tolerance_ms: 120
        - {kind: "inspect", count: 1}
      output:
        item: "sora_nobori"
        qty: 1
    registry:
      item_ja: "絹幟"
      item_en: "Silk banner"
      qty: 1
      unit_ja: "旒"
      unit_en: "banner"
    music: "ch05_sorabiki"
    x_ext:
      player_role: "sorabiki (drawboy on the figure harness)"
      npc_role: "okinu: treadle, shuttle, beater"
      step_labels: ["find 3 broken figure cords", "24 picks on Okinu's call", "unroll the mon"]
    dialogue:
      - {"on": "beat_start", lines: ["ch05.b11.okinu.001", "ch05.b11.okinu.002"], mode: "ambient"}
      - {"on": "progress_at:0.5", lines: ["ch05.b11.okinu.003"], mode: "ambient"}
      - {"on": "beat_complete", lines: ["ch05.b11.okinu.004", "ch05.b11.oyuki.005"], mode: "ambient"}
  - id: "ch05.b12"
    type: "cinematic"
    place: "pl_aratamejo"
    title_ja: "初めての割符"
    title_en: "The first tally"
    target_s: 150
    checkpoint: true
    site: 2
    sequence: "/Game/Cinematics/Ch05/LS_Ch05_B12_FirstXOR"
    duration_s: 150
    skippable: true
    fallback: "camera_blend"
    end_state:
      player_transform: "ps_ch05_aratamejo_door"
      equipped: "keep"
    music: "ch05_first_xor"
    x_ext:
      site_restores_on: "sequence_end_or_skip"
      interactive_press:
        prompt: "brand_tally"
        can_fail: false
      posts_registry_page_on: "yard_quota_board"
      registry_ui: "three-seal split-tally icons on the b08, b09 and b11 entries"
    subtitles: ["ch05.b12.oyuki.001", "ch05.b12.oyuki.002", "ch05.b12.nyaakoto.003", "ch05.b12.kozo.004", "ch05.b12.otane.005", "ch05.b12.nyaakoto.006", "ch05.b12.tetsugoro.007", "ch05.b12.okinu.008", "ch05.b12.oyuki.009", "ch05.b12.oyuki.010", "ch05.b12.oyuki.011", "ch05.b12.kozo.012", "ch05.b12.oyuki.013", "ch05.b12.nyaakoto.014"]
  - id: "ch05.b13"
    type: "explore_optional"
    place: "pl_toritategura"
    title_ja: "取立蔵を調べる"
    title_en: "Search the levy storehouse"
    target_s: 150
    checkpoint: true
    optional: true
    requires: ["ch05.b12"]
    volume: "vol_ch05_storehouse"
    pois:
      - {id: "poi_quota_sheet", kind: "lore"}
      - {id: "poi_washio_notice", kind: "lore"}
      - {id: "poi_arrow_cache", kind: "cache"}
      - {id: "poi_kanayago_scroll", kind: "lore"}
      - {id: "poi_output_book", kind: "lore"}
      - {id: "poi_storm_window", kind: "vista"}
    rewards: ["ch05.c03", "ch05.c04", "ch05.c05", "arrows:12", "arc_carbine_rounds:48"]
    exit_hint_after_s: 150
    music: "ch05_storehouse_storm"
    dialogue:
      - {"on": "volume_enter:vol_poi_quota_sheet", lines: ["ch05.b13.nyaakoto.001"], mode: "ambient"}
      - {"on": "volume_enter:vol_poi_washio_notice", lines: ["ch05.b13.nyaakoto.002"], mode: "ambient"}
      - {"on": "volume_enter:vol_poi_kanayago", lines: ["ch05.b13.kozo.003"], mode: "ambient"}
  - id: "ch05.b14"
    type: "cinematic"
    place: "pl_imonoba"
    title_ja: "湯路、全開"
    title_en: "The channels open"
    target_s: 90
    checkpoint: false
    requires: ["ch05.b12"]
    sequence: "/Game/Cinematics/Ch05/LS_Ch05_B14_ChannelsOpen"
    duration_s: 90
    skippable: true
    fallback: "camera_blend"
    end_state:
      player_transform: "ps_ch05_imonoba_south"
      equipped: "keep"
    music: "ch05_storm_break"
    subtitles: ["ch05.b14.tarifa.001", "ch05.b14.oyuki.002", "ch05.b14.tarifa.003", "ch05.b14.tarifa.004", "ch05.b14.kozo.005"]
  - id: "ch05.b15"
    type: "combat_wave"
    place: "pl_imonoba"
    title_ja: "鋳物場を突破せよ"
    title_en: "Cross the casting floor"
    target_s: 240
    checkpoint: true
    bounds: "vol_ch05_imonoba"
    waves:
      - enemies:
          - {type: "loom_automaton", count: 1, spawn: "sp_imonoba_east_gate"}
          - {type: "enforcer_rifle", count: 2, spawn: "sp_imonoba_gantry"}
        trigger: "start"
      - enemies:
          - {type: "loom_automaton", count: 2, spawn: "sp_imonoba_east_gate"}
          - {type: "blade_retainer", count: 1, spawn: "sp_imonoba_south_door"}
        trigger: "prev_cleared"
      - enemies:
          - {type: "loom_automaton", count: 1, spawn: "sp_imonoba_east_gate"}
          - {type: "grenadier", count: 1, spawn: "sp_imonoba_gantry"}
          - {type: "enforcer_rifle", count: 2, spawn: "sp_imonoba_south_door"}
        trigger: "alive_below:1"
    complete: "all_waves_cleared"
    max_alive: 5
    music: "ch05_casting_floor"
    x_ext:
      hazards:
        molten_channels:
          count: 4
          cycle_s: 12
          glow_ramp_s: 2
          flow_s: 5
          player_dps: 35
          burn_s: 2
          enemy_contact: "loom_automaton destroyed; others 60 dps"
      environmental_kills_count: true
    dialogue:
      - {"on": "beat_start", lines: ["ch05.b15.kozo.001"], mode: "ambient"}
      - {"on": "wave_start:1", lines: ["ch05.b15.okinu.002"], mode: "ambient"}
      - {"on": "beat_complete", lines: ["ch05.b15.kohagi.003"], mode: "ambient"}
  - id: "ch05.b16"
    type: "boss"
    boss: "boss_tarifa"
    place: "pl_takadono"
    title_ja: "工房監督官タリファを倒せ"
    title_en: "Defeat Foundry Overseer Tarifa"
    target_s: 420
    checkpoint: true
    arena:
      volume: "vol_takadono_boss"
      lock: true
    phases:
      - {hp_pct_start: 100, pattern_table: "tarifa_p1"}
      - hp_pct_start: 65
        pattern_table: "tarifa_p2"
        adds: "loom_automaton_pair_x2"
        arena_mod: "channel_cycle_10s"
      - {hp_pct_start: 30, pattern_table: "tarifa_p3", arena_mod: "roof_breach_rain_steam"}
    defeat: "kill"
    intro_cinematic: "/Game/Cinematics/Ch05/LS_Ch05_B16_TarifaIntro"
    outro_cinematic: "/Game/Cinematics/Ch05/LS_Ch05_B16_TarifaFall"
    checkpoint_per_phase: true
    telegraph:
      palette: "default"
      min_windup_ms: 500
    music: "boss_tarifa"
    x_ext:
      hp_normal: 3000
      mantle_damage_reduction: 0.7
      mantle_down_s: 4
      fall_policy: "pulled into an open slot: 80 damage, dropped to the floor, climb back by stair; rails block the fall on 稽古"
    x_intro_subtitles: ["ch05.b16.tarifa.001", "ch05.b16.nyaakoto.002"]
    x_outro_subtitles: ["ch05.b16.tarifa.010", "ch05.b16.nyaakoto.011", "ch05.b16.kozo.012"]
    barks:
      - {"on": "pattern:channel_cycle", line: "ch05.b16.tarifa.003"}
      - {"on": "pattern:tether_lash", line: "ch05.b16.tarifa.004"}
      - {"on": "pattern:double_lash", line: "ch05.b16.tarifa.004"}
      - {"on": "pattern:rod_sweep", line: "ch05.b16.tarifa.005"}
      - {"on": "boss_phase:2", line: "ch05.b16.tarifa.006"}
      - {"on": "pattern_countered:tether_lash", line: "ch05.b16.tarifa.007"}
      - {"on": "boss_phase:3", line: "ch05.b16.kozo.008"}
      - {"on": "boss_state:mantle_down", line: "ch05.b16.tarifa.009"}
  - id: "ch05.b17"
    type: "production_task"
    task: "carry"
    place: "pl_silk_foundry"
    title_ja: "荷を駄馬に積め"
    title_en: "Load the pack horses"
    target_s: 120
    checkpoint: true
    carry:
      item: "goods_load"
      count: 4
      pickups: ["pk_aratamejo_arrowheads", "pk_aratamejo_carbines", "pk_okaji_coils", "pk_storehouse_silk"]
      dropoffs: ["pack_horse_valley", "pack_horse_ward"]
      loadout_while_carrying: ["katana_one_hand"]
      move_speed_mult: 0.8
      drop_on_hit: false
    music: "ch05_dawn_loading"
    x_ext:
      routing:
        pk_aratamejo_arrowheads: "pack_horse_valley"
        pk_aratamejo_carbines: "pack_horse_valley"
        pk_okaji_coils: "pack_horse_valley"
        pk_storehouse_silk: "pack_horse_ward"
      no_registry_reason: "goods were entered at b08/b09/b11 and tallied at b12; the silk is returned levy silk, not new production"
      supply_point: "sup_ch05_yard"
    dialogue:
      - {"on": "beat_start", lines: ["ch05.b17.oyuki.001"], mode: "ambient"}
      - {"on": "item_delivered:load_01", lines: ["ch05.b17.otane.002"], mode: "ambient"}
      - {"on": "idle_s:20", lines: ["ch05.b17.artisan.003"], mode: "ambient"}
  - id: "ch05.b18"
    type: "cinematic"
    place: "pl_silk_foundry"
    title_ja: "夜明けの幟"
    title_en: "Banner at dawn"
    target_s: 120
    checkpoint: false
    sequence: "/Game/Cinematics/Ch05/LS_Ch05_B18_NoboriDawn"
    duration_s: 120
    skippable: true
    fallback: "camera_blend"
    end_state:
      player_transform: "ps_ch05_yard_north"
      equipped: "keep"
    music: "ch05_nobori_dawn"
    x_ext:
      chapter_complete_screen: "registry_page_ch05"
      diegetic_text: ["sign.ch05.nap"]
      grants_item: "iota_message_slate (twin slate used in ch06.b01-b05)"
    subtitles: ["ch05.b18.kozo.001", "ch05.b18.okinu.002", "ch05.b18.kohagi.003", "ch05.b18.iota.004", "ch05.b18.iota.005", "ch05.b18.iota.006", "ch05.b18.iota.007", "ch05.b18.oyuki.008", "ch05.b18.nyaakoto.009"]
x_boss_pattern_tables:
  tarifa_p1:
    - id: "tether_lash"
      windup_ms: 700
      active_ms: 250
      recovery_ms: 900
      telegraph: "cyan filament lock"
      damage: 12
      effect: "pull 400 cm toward nearest open heat slot"
      cooldown_s: 6
      counter: "awase within 260 ms: cable snaps, 2.0 s stun, mantle down 4 s; guard halves pull; marobashi sidestep avoids"
      bark: "ch05.b16.tarifa.004"
    - id: "rod_sweep"
      windup_ms: 500
      active_ms: 450
      recovery_ms: 800
      telegraph: "amber arc, two hits 450 ms apart"
      damage: 28
      effect: "two-hit sweep, reach 260 cm"
      cooldown_s: 4
      counter: "guard both; awase on hit 2: 1.2 s stagger"
      bark: "ch05.b16.tarifa.005"
    - id: "quota_slam"
      windup_ms: 900
      active_ms: 200
      recovery_ms: 1100
      telegraph: "amber ring 300 cm"
      damage: 40
      effect: "knockback 250 cm"
      cooldown_s: 10
      counter: "step out of the ring; punish recovery"
    - id: "channel_cycle"
      windup_ms: 2000
      active_ms: 5000
      recovery_ms: 0
      telegraph: "amber glow ramp on the gate and slot"
      damage: 35
      effect: "one channel flows every 12 s; slot heat column 20/s on the deck"
      cooldown_s: 12
      counter: "read the glow; stand on bridges"
      bark: "ch05.b16.tarifa.003"
  tarifa_p2:
    - id: "double_lash"
      windup_ms: 700
      active_ms: 250
      recovery_ms: 900
      telegraph: "cyan lock, then second cyan lock 500 ms after the first recovery begins"
      damage: 12
      effect: "two pulls of 400 cm"
      cooldown_s: 8
      counter: "awase either lash to snap the cable"
      bark: "ch05.b16.tarifa.004"
    - {id: "rod_sweep", inherit: "tarifa_p1"}
    - {id: "quota_slam", inherit: "tarifa_p1"}
    - {id: "channel_cycle", inherit: "tarifa_p1", cooldown_s: 10}
    - {id: "adds", effect: "loom_automaton x2 at phase start and x2 at 45% HP (max 2 alive)"}
  tarifa_p3:
    - {id: "tether_lash", inherit: "tarifa_p1"}
    - {id: "rod_sweep", inherit: "tarifa_p1"}
    - id: "steam_burst"
      windup_ms: 900
      active_ms: 600
      recovery_ms: 0
      telegraph: "captioned hiss + white vapor at a wet slot"
      damage: 25
      effect: "radius 250 cm, 1 s blur; overloads Tarifa's mantle for 4 s if she is inside"
      cooldown_s: 5
      counter: "stand clear; lure her to wet slots (she follows at 6-9 m)"
    - id: "full_open"
      windup_ms: 1500
      active_ms: 4000
      recovery_ms: 1500
      telegraph: "all four gates glow amber at once (once, at 10% HP)"
      damage: 35
      effect: "all channels flow; all slots vent"
      cooldown_s: 0
      counter: "stand on a cross-bridge"
collectibles:
  - collectible_id: "ch05.c01"
    category: "league_mark"
    place: "pl_kanna_nagashi"
    mask_bit: 0
    codex:
      ja: "空紋の目印。鉄穴の堰板に、小萩の仲間が炭で描いた印。「水路は西の暗渠へ抜ける」。"
      en: "League mark. Charcoal on a sluice board, left by Kohagi's scouts: 'The channel runs west to the culvert.'"
  - collectible_id: "ch05.c02"
    category: "seizure_notice"
    place: "pl_itotoriba"
    mask_bit: 1
    codex:
      ja: "差押状。煮繭鍋十二口、元本の一部として差し押さえる。使用料は日割りで加算。"
      en: "Seizure notice. Twelve cocoon pots seized as partial principal. Usage fees accrue daily."
  - collectible_id: "ch05.c03"
    category: "seizure_notice"
    place: "pl_toritategura"
    mask_bit: 2
    codex:
      ja: "債権譲渡通知。鷲尾家の借財、大坂の米商より恒星信用院へ譲渡済み。"
      en: "Notice of transfer. The Washio house's debt, sold by Osaka rice brokers to the Stellar Credit House."
  - collectible_id: "ch05.c04"
    category: "heirloom"
    place: "pl_toritategura"
    mask_bit: 3
    codex:
      ja: "家宝。金屋子神の掛軸。高殿の神棚から差し押さえられ、「評価額 零」の札が付いていた。"
      en: "Heirloom. A hanging scroll of Kanayago, deity of the smelters, seized from the tatara hall's shrine shelf and tagged 'Assessed value: 0'."
  - collectible_id: "ch05.c05"
    category: "registry_page"
    place: "pl_toritategura"
    mask_bit: 4
    codex:
      ja: "生産の記録。侵略前の鉄山の出来高帳。鉄と絹の量が、村下の筆で記されている。"
      en: "Registry page. The ironworks' pre-invasion output book, in the master smelter's own hand."
  - collectible_id: "ch05.c06"
    category: "scroll_fragment"
    place: "pl_okaji"
    mask_bit: 5
    codex:
      ja: "伝書の断簡。焚き付けの山から救い出した、石鈴斎の教えの一片。"
      en: "Scroll fragment. A piece of Sekireisai's teaching, rescued from the forge's kindling pile."
x_bark_pool:
  - {id: "ch05.b00.enforcer.001", speaker: "enforcer", "on": "alert_state:suspicious", repeatable: true}
  - {id: "ch05.b00.enforcer.002", speaker: "enforcer", "on": "alert_state:search", repeatable: true}
  - {id: "ch05.b00.enforcer.003", speaker: "enforcer", "on": "alert_state:alert", repeatable: true}
  - {id: "ch05.b00.enforcer.004", speaker: "enforcer", "on": "alert_state:unaware", repeatable: true}
  - {id: "ch05.b00.enforcer.005", speaker: "enforcer", "on": "enemy_retreat", repeatable: true}
  - {id: "ch05.b00.enforcer.006", speaker: "enforcer", "on": "pattern:grenade_throw", repeatable: true}
  - {id: "ch05.b00.conscript.007", speaker: "conscript", "on": "conscript_attack", repeatable: true}
  - {id: "ch05.b00.conscript.008", speaker: "conscript", "on": "conscript_downed", repeatable: true}
  - {id: "ch05.b00.conscript.009", speaker: "conscript", "on": "conscript_freed", repeatable: true}
  - {id: "ch05.b00.nyaakoto.010", speaker: "samurai", "on": "nonlethal_focus", repeatable: true}
ui_prompts:
  - id: "ui.ch05.tut.01"
    beat: "ch05.b02"
    "on": "beat_start"
    ja: "水の中を歩くと、足音が小さくなる"
    en: "Walking in water makes your steps quieter"
  - id: "ui.ch05.tut.02"
    beat: "ch05.b02"
    "on": "volume_enter:vol_kanna_tailings"
    ja: "砂利の上は足音が大きい"
    en: "Gravel is loud underfoot"
  - id: "ui.ch05.tut.03"
    beat: "ch05.b02"
    "on": "look_at:kagaribi"
    ja: "{Interact}長押し：篝火に砂をかけて消す"
    en: "Hold {Interact}: smother the brazier with sand"
  - id: "ui.ch05.tut.04"
    beat: "ch05.b02"
    "on": "look_at:flood_upper"
    ja: "照明の根元の線を射ると、しばらく消える"
    en: "Shoot the floodlight's base cable to cut it briefly"
  - id: "ui.ch05.tut.05"
    beat: "ch05.b03"
    "on": "look_at:collar"
    ja: "{Interact}長押し：首輪を断つ"
    en: "Hold {Interact}: cut the collar"
  - id: "ui.ch05.tut.06"
    beat: "ch05.b03"
    "on": "progress_at:0.05"
    ja: "見張りに見られている間、同行者は足を止める"
    en: "While a guard sees you, your companions stop and wait"
  - id: "ui.ch05.tut.07"
    beat: "ch05.b05"
    "on": "polearm_obstructed:first"
    ja: "薙刀の払いは機に当たる。狭い所では突け"
    en: "Naginata sweeps catch on looms. Thrust in narrow aisles"
  - id: "ui.ch05.tut.08"
    beat: "ch05.b06"
    "on": "beat_start"
    ja: "左右交互に一定の間で踏む。炎の色と印が目安"
    en: "Tread left-right at a steady pace. Watch the flame and gauge"
  - id: "ui.ch05.tut.09"
    beat: "ch05.b07"
    "on": "target_hp_below:tatara_furnace:0.7"
    ja: "{Interact}：粘土で釜を補修"
    en: "Press {Interact}: patch the furnace with clay"
  - id: "ui.ch05.tut.10"
    beat: "ch05.b08"
    "on": "beat_start"
    ja: "小鎚の合図の一拍後に打つ"
    en: "Strike one beat after the small hammer's cue"
  - id: "ui.ch05.tut.11"
    beat: "ch05.b10"
    "on": "beat_start"
    ja: "アーク・カービン: 構えて撃つ/弾を込め直す"
    en: "Arc Carbine: aim, fire, reload"
  - id: "ui.ch05.tut.12"
    beat: "ch05.b11"
    "on": "beat_start"
    ja: "お絹の呼び声に合わせて紋糸を引く"
    en: "Pull the figure cords on Okinu's call"
  - id: "ui.ch05.tut.13"
    beat: "ch05.b15"
    "on": "beat_start"
    ja: "光る湯路の口から離れよ。敵を誘い込める"
    en: "Keep clear of glowing channel mouths. Lure enemies in"
  - id: "ui.ch05.tut.14"
    beat: "ch05.b16"
    "on": "pattern:tether_lash:first"
    ja: "鉤縄は「合わせ」で断てる"
    en: "Meet the tether with awase to snap it"
  - id: "ui.ch05.tut.15"
    beat: "ch05.b16"
    "on": "boss_phase:3"
    ja: "湯気の中ではタリファの外套が落ちる"
    en: "Steam overloads Tarifa's mantle"
  - id: "ui.ch05.tut.16"
    beat: "ch05.b17"
    "on": "beat_start"
    ja: "荷を運ぶ間は刀を片手でのみ使える"
    en: "While carrying, you fight one-handed with the katana"
x_diegetic_text:
  - id: "sign.ch05.nap"
    beats: "b01, b18"
    ja: "昼寝禁止 ― 休止時間は課金の対象となります。恒星信用院 執行局"
    en: "NO NAPPING — Downtime is billable. Stellar Credit House, Enforcement Office"
  - id: "sign.ch05.quota"
    beats: "b01, b10, b12"
    ja: "目標稼働率 140% / 現在 98%"
    en: "Target utilization 140% / Current 98%"
  - {id: "sign.ch05.tag", beats: "b13", ja: "装飾品 評価額 零", en: "Decorative item. Assessed value: 0"}
lines:
  - id: "ch05.b01.kohagi.001"
    speaker: "scout"
    ja: "絹の工房。見張り九。首輪つきが六十。"
    en: "The Silk Foundry. Nine guards. Sixty in collars."
    register: "terse_report"
    duration_s: 4.5
  - id: "ch05.b01.nyaakoto.002"
    speaker: "samurai"
    ja: "六十人……夜通しか。"
    en: "Sixty of them… all through the night?"
    register: "jidaigeki_plain"
    duration_s: 3.0
  - id: "ch05.b01.tarifa.003"
    speaker: "boss_tarifa"
    ja: "目標稼働率、百四十パーセント。現在、九十八。"
    en: "Target utilization: one hundred forty percent. Current: ninety-eight."
    register: "alien_corporate_keigo"
    duration_s: 5.5
  - id: "ch05.b01.tarifa.004"
    speaker: "boss_tarifa"
    ja: "不足分は、各位の元本に加算いたします。"
    en: "The shortfall will be added to each of your principals."
    register: "alien_corporate_keigo"
    duration_s: 4.5
  - id: "ch05.b01.kohagi.005"
    speaker: "scout"
    ja: "入るのは下から。鉄穴の水路。"
    en: "We go in from below. Through the iron-sand channels."
    register: "terse_report"
    duration_s: 3.5
  - id: "ch05.b02.kohagi.001"
    speaker: "scout"
    ja: "水路を歩いて。水音が足音を隠す。"
    en: "Walk in the channels. The water hides your steps."
    register: "terse_report"
    duration_s: 4.0
  - id: "ch05.b02.kohagi.002"
    speaker: "scout"
    ja: "砂利山は鳴る。避けて。"
    en: "The tailings crunch. Go around."
    register: "terse_report"
    duration_s: 3.0
  - id: "ch05.b02.kohagi.003"
    speaker: "scout"
    ja: "首輪の二人、目をそらしてる。……首輪は、そらさない。"
    en: "Those two look away. …Their collars don't."
    register: "terse_report"
    duration_s: 6.0
  - id: "ch05.b02.conscript.004"
    speaker: "conscript"
    ja: "……行け。見とらん。"
    en: "…Go. I saw nothing."
    register: "local_colloquial_whisper"
    duration_s: 3.0
  - id: "ch05.b02.nyaakoto.005"
    speaker: "samurai"
    ja: "必ず戻る。"
    en: "I will come back for you."
    register: "jidaigeki_plain_whisper"
    duration_s: 2.0
  - id: "ch05.b03.artisan.001"
    speaker: "artisan"
    ja: "……軽い。首が、軽い。"
    en: "…Light. My neck is light."
    register: "local_colloquial"
    duration_s: 3.5
  - id: "ch05.b03.okinu.002"
    speaker: "weaver"
    ja: "どちらさんどす？　……いえ、その紋で分かりますえ。"
    en: "And who might you be? …No. That crest tells me."
    register: "kyoto_soft"
    duration_s: 5.0
  - id: "ch05.b03.nyaakoto.003"
    speaker: "samurai"
    ja: "猫柳生のニャーコト。皆を外へ出す。"
    en: "Nyaakoto of Nyaagyu. I am getting you all out."
    register: "jidaigeki_polite"
    duration_s: 4.0
  - id: "ch05.b03.tetsugoro.004"
    speaker: "gunsmith"
    ja: "礼は後や。先に、若いのを出したってくれ。"
    en: "Thanks can wait. Get the young ones out first."
    register: "kansai_blunt"
    duration_s: 4.5
  - id: "ch05.b03.kohagi.005"
    speaker: "scout"
    ja: "炭小屋まで。見回り三つ。合図で伏せて。"
    en: "To the charcoal shed. Three patrols. Down on my signal."
    register: "terse_report"
    duration_s: 5.0
  - id: "ch05.b03.okinu.006"
    speaker: "weaver"
    ja: "外の風、四十日ぶりどす。"
    en: "Forty days since I last felt the wind."
    register: "kyoto_soft"
    duration_s: 3.0
  - id: "ch05.b03.kohagi.007"
    speaker: "scout"
    ja: "全員。六人。"
    en: "All of them. Six."
    register: "terse_report"
    duration_s: 2.0
  - id: "ch05.b05.okinu.001"
    speaker: "weaver"
    ja: "皆はん、杼を置いて！　今夜は織らしまへん！"
    en: "Everyone, set down your shuttles! Tonight, we do not weave!"
    register: "kyoto_raised"
    duration_s: 4.5
  - id: "ch05.b05.tarifa.002"
    speaker: "boss_tarifa"
    ja: "持ち場に戻らない場合、延滞として処理いたします。"
    en: "Failure to return to your station will be processed as default."
    register: "alien_corporate_keigo"
    duration_s: 5.5
  - id: "ch05.b05.okinu.003"
    speaker: "weaver"
    ja: "その子らは斬らんといて！　首輪だけ！"
    en: "Don't cut them down! Just the collars!"
    register: "kyoto_raised"
    duration_s: 4.0
  - id: "ch05.b05.nyaakoto.004"
    speaker: "samurai"
    ja: "狭い……突きで行く。"
    en: "Too tight… Thrusts, then."
    register: "jidaigeki_plain"
    duration_s: 3.0
  - id: "ch05.b05.artisan.005"
    speaker: "artisan"
    ja: "毎日この目盛りを睨んできたんや。"
    en: "Every day, I've glared at this meter."
    register: "local_colloquial"
    duration_s: 3.5
  - id: "ch05.b05.artisan.006"
    speaker: "artisan"
    ja: "村下が呼んどる！　炉が冷える！"
    en: "The murage is calling! The furnace is cooling!"
    register: "local_colloquial"
    duration_s: 3.5
  - id: "ch05.b06.kozo.001"
    speaker: "foundry_master"
    ja: "番子が逃げた。お前が踏め。"
    en: "The bellows crew fled. You tread."
    register: "yamato_gruff"
    duration_s: 3.5
  - id: "ch05.b06.kozo.002"
    speaker: "foundry_master"
    ja: "深う踏め。同じ間でな。"
    en: "Tread deep. Keep an even beat."
    register: "yamato_gruff"
    duration_s: 3.0
  - id: "ch05.b06.kozo.003"
    speaker: "foundry_master"
    ja: "浅い。炎が赤い。"
    en: "Too shallow. The flame's red."
    register: "yamato_gruff"
    duration_s: 2.5
    repeatable: true
  - id: "ch05.b06.kozo.004"
    speaker: "foundry_master"
    ja: "……そうや。その山吹色や。"
    en: "…That's it. That golden yellow."
    register: "yamato_gruff"
    duration_s: 3.5
  - id: "ch05.b06.kozo.005"
    speaker: "foundry_master"
    ja: "急くな。白い炎は、炭を食うだけや。"
    en: "Don't rush. White flame only eats charcoal."
    register: "yamato_gruff"
    duration_s: 4.0
    repeatable: true
  - id: "ch05.b06.kozo.006"
    speaker: "foundry_master"
    ja: "鉄は三晩で生まれる。急かすな。"
    en: "Iron is born over three nights. Don't rush it."
    register: "yamato_gruff"
    duration_s: 3.5
  - id: "ch05.b06.nyaakoto.007"
    speaker: "samurai"
    ja: "村下殿、その目は……"
    en: "Master smelter, your eye…"
    register: "jidaigeki_polite"
    duration_s: 3.0
  - id: "ch05.b06.kozo.008"
    speaker: "foundry_master"
    ja: "炎を見すぎた。村下は片目で鉄を読む。"
    en: "Watched the flame too long. A murage reads iron one-eyed."
    register: "yamato_gruff"
    duration_s: 4.5
  - id: "ch05.b07.tarifa.001"
    speaker: "boss_tarifa"
    ja: "高殿の無許可稼働を確認。没収いたします。"
    en: "Unauthorized operation in the tatara hall. Confiscating."
    register: "alien_corporate_keigo"
    duration_s: 5.0
  - id: "ch05.b07.kozo.002"
    speaker: "foundry_master"
    ja: "炉を守れ！　釜が割れたら三晩が灰や！"
    en: "Guard the furnace! If it cracks, three nights turn to ash!"
    register: "yamato_gruff_raised"
    duration_s: 4.0
  - id: "ch05.b07.kozo.003"
    speaker: "foundry_master"
    ja: "釜に土を塗れ！　桶の粘土や！"
    en: "Clay on the furnace wall! From the tubs!"
    register: "yamato_gruff_raised"
    duration_s: 3.5
  - id: "ch05.b07.kozo.004"
    speaker: "foundry_master"
    ja: "構うな……炉を……！"
    en: "Never mind me… the furnace…!"
    register: "yamato_gruff_strained"
    duration_s: 3.0
  - id: "ch05.b07.kozo.005"
    speaker: "foundry_master"
    ja: "……持ちこたえた。鉧が育っとる。"
    en: "…We held. The bloom is growing."
    register: "yamato_gruff"
    duration_s: 4.0
  - id: "ch05.b08.kozo.001"
    speaker: "foundry_master"
    ja: "向こう鎚や。わしの小鎚が叩いた所を打て。"
    en: "The striker's sledge. Hit where my small hammer taps."
    register: "yamato_gruff"
    duration_s: 4.5
  - id: "ch05.b08.kozo.002"
    speaker: "foundry_master"
    ja: "わしが打つ、お前が打つ。それが相鎚や。"
    en: "I strike, you strike. That is aizuchi."
    register: "yamato_gruff"
    duration_s: 4.5
  - id: "ch05.b08.nyaakoto.003"
    speaker: "samurai"
    ja: "刀を打つのと、同じ鉄ですか。"
    en: "Is this the same iron as a sword?"
    register: "jidaigeki_polite"
    duration_s: 3.5
  - id: "ch05.b08.kozo.004"
    speaker: "foundry_master"
    ja: "同じや。何になるかは、打つ者が決める。"
    en: "Same iron. The one who strikes decides what it becomes."
    register: "yamato_gruff"
    duration_s: 4.5
  - id: "ch05.b08.kozo.005"
    speaker: "foundry_master"
    ja: "二十四本。数えてみい。"
    en: "Twenty-four. Count them yourself."
    register: "yamato_gruff"
    duration_s: 3.0
  - id: "ch05.b08.kozo.006"
    speaker: "foundry_master"
    ja: "その鎚、貸しとく。"
    en: "Keep the hammer. It's a loan."
    register: "yamato_gruff"
    duration_s: 2.5
  - id: "ch05.b08.sekireisai.007"
    speaker: "mentor"
    ja: "鍛冶は鉄に逆らわず、鉄の欲する所を打つ。剣も同じじゃ。"
    en: "A smith never fights the iron. He strikes where it wants to go. So with the sword."
    register: "archaic_memory"
    duration_s: 6.0
  - id: "ch05.b09.tetsugoro.001"
    speaker: "gunsmith"
    ja: "連中の銃の芯、見てきた。あれは使える。"
    en: "I've seen the cores in their guns. We can use them."
    register: "kansai_blunt"
    duration_s: 4.5
  - id: "ch05.b09.tetsugoro.002"
    speaker: "gunsmith"
    ja: "筒を覗け。灯りが真っ直ぐなら、ええ筒や。"
    en: "Look down the barrel. If the light runs true, it's good."
    register: "kansai_blunt"
    duration_s: 4.5
  - id: "ch05.b09.tetsugoro.003"
    speaker: "gunsmith"
    ja: "芯を逆さに入れたら、手が飛ぶで。"
    en: "Seat the core backwards and you'll lose a paw."
    register: "kansai_blunt"
    duration_s: 3.5
  - id: "ch05.b09.tetsugoro.004"
    speaker: "gunsmith"
    ja: "空紋や。一から作った、おれらの初めての銃や。"
    en: "The Sora crest. Our first gun, built from scratch."
    register: "kansai_blunt"
    duration_s: 5.0
  - id: "ch05.b09.tetsugoro.005"
    speaker: "gunsmith"
    ja: "一挺はお前のや。試し撃ちは、すぐ来るで。"
    en: "One is yours. You'll get to test it soon enough."
    register: "kansai_blunt"
    duration_s: 4.5
  - id: "ch05.b10.tetsugoro.001"
    speaker: "gunsmith"
    ja: "肩に付けて、息を吐きながら引け！"
    en: "Shoulder it. Squeeze as you breathe out!"
    register: "kansai_blunt_raised"
    duration_s: 3.5
  - id: "ch05.b10.kohagi.002"
    speaker: "scout"
    ja: "屋根に一。光ったら隠れて。"
    en: "One on the roof. When it glints, take cover."
    register: "terse_report"
    duration_s: 3.5
  - id: "ch05.b10.otane.003"
    speaker: "farmer_young"
    ja: "待たせたな！　一揆の鉄砲衆、連れてきたで！"
    en: "Sorry to keep you! I brought the League's gunners!"
    register: "kamigata_bright"
    duration_s: 4.5
  - id: "ch05.b10.oyuki.004"
    speaker: "leader"
    ja: "遅くなりました。帳を運んでまいりました。"
    en: "Forgive the delay. I have brought the registry."
    register: "business_keigo"
    duration_s: 4.0
  - id: "ch05.b11.okinu.001"
    speaker: "weaver"
    ja: "四十夜、あの目盛りの下で織ってきた幟どす。"
    en: "Forty nights I wove this banner, right under their meter."
    register: "kyoto_soft"
    duration_s: 4.5
  - id: "ch05.b11.okinu.002"
    speaker: "weaver"
    ja: "上に乗って、うちが言うたら紋糸を引いとくれやす。"
    en: "Sit up top. When I call, pull the figure cords."
    register: "kyoto_soft"
    duration_s: 5.0
  - id: "ch05.b11.okinu.003"
    speaker: "weaver"
    ja: "ええ手どすなあ。お侍より機屋向きやわ。"
    en: "Such good paws. More weaver than samurai, you."
    register: "kyoto_soft"
    duration_s: 4.0
  - id: "ch05.b11.okinu.004"
    speaker: "weaver"
    ja: "糸は一本では弱おす。けど、織ったら旗になりますえ。"
    en: "One thread alone is weak. Woven, it becomes a banner."
    register: "kyoto_soft"
    duration_s: 5.5
  - id: "ch05.b11.oyuki.005"
    speaker: "leader"
    ja: "絹幟、一旒。記しました。"
    en: "Silk banner, one. Entered."
    register: "business_keigo"
    duration_s: 3.5
  - id: "ch05.b12.oyuki.001"
    speaker: "leader"
    ja: "五箇条の一。物なくして札なし。"
    en: "Article one: no goods, no tally."
    register: "business_keigo"
    duration_s: 3.5
  - id: "ch05.b12.oyuki.002"
    speaker: "leader"
    ja: "改めは三者。作り手、受け手、籤で選ぶ改め役。"
    en: "Three inspect: maker, receiver, and an inspector drawn by lot."
    register: "business_keigo"
    duration_s: 5.5
  - id: "ch05.b12.nyaakoto.003"
    speaker: "samurai"
    ja: "改め役、ニャーコト。務めます。"
    en: "Inspector: Nyaakoto. I will serve."
    register: "jidaigeki_formal"
    duration_s: 3.5
  - id: "ch05.b12.kozo.004"
    speaker: "foundry_master"
    ja: "鏃、二十四本。作り手、村下鋼蔵。"
    en: "Arrowheads, twenty-four. Maker: Murage Kōzō."
    register: "yamato_gruff_formal"
    duration_s: 4.5
  - id: "ch05.b12.otane.005"
    speaker: "farmer_young"
    ja: "受け手、お種。村の弓衆に回します。"
    en: "Receiver: Otane. They go to the village archers."
    register: "kamigata_formal"
    duration_s: 4.0
  - id: "ch05.b12.nyaakoto.006"
    speaker: "samurai"
    ja: "……二十二、二十三、二十四。確かに。"
    en: "…Twenty-two, twenty-three, twenty-four. Confirmed."
    register: "jidaigeki_formal"
    duration_s: 5.0
  - id: "ch05.b12.tetsugoro.007"
    speaker: "gunsmith"
    ja: "アーク・カービン三挺。作り手、鉄五郎。おれが撃った。"
    en: "Arc Carbines, three. Maker: Tetsugorō. I fired each one."
    register: "kansai_blunt"
    duration_s: 6.0
  - id: "ch05.b12.okinu.008"
    speaker: "weaver"
    ja: "絹幟、一旒。織り手、お絹。"
    en: "Silk banner, one. Weaver: Okinu."
    register: "kyoto_formal"
    duration_s: 3.5
  - id: "ch05.b12.oyuki.009"
    speaker: "leader"
    ja: "割目に紋の焼印を。半分は作り手、半分は受け手に。"
    en: "Brand the crest across the split. Half to the maker, half to the receiver."
    register: "business_keigo"
    duration_s: 6.0
  - id: "ch05.b12.oyuki.010"
    speaker: "leader"
    ja: "札は財布の数字ではございません。作られた物の証でございます。"
    en: "This tally is no number in a purse. It is proof a thing was made."
    register: "business_keigo"
    duration_s: 6.0
  - id: "ch05.b12.oyuki.011"
    speaker: "leader"
    ja: "利は付きません。貸すのは道具。金ではございません。"
    en: "It bears no interest. We lend tools, not money."
    register: "business_keigo"
    duration_s: 5.5
  - id: "ch05.b12.kozo.012"
    speaker: "foundry_master"
    ja: "……鉄を数えた札なら、信じてもええ。"
    en: "…A tally that counts iron. That, I can trust."
    register: "yamato_gruff"
    duration_s: 4.0
  - id: "ch05.b12.oyuki.013"
    speaker: "leader"
    ja: "生産を記録し、民の新しい通貨にしよう。"
    en: "Let us record our production as the basis for a new currency."
    register: "plain_to_crowd"
    duration_s: 4.5
    anchor: "catalog ch05 line 2"
  - id: "ch05.b12.nyaakoto.014"
    speaker: "samurai"
    ja: "SORA XOR。ここで生まれた価値を、ここへ返す。"
    en: "SORA XOR. Value made here will return to the people here."
    register: "jidaigeki_formal"
    duration_s: 5.0
    anchor: "catalog ch05 line 3"
  - id: "ch05.b13.nyaakoto.001"
    speaker: "samurai"
    ja: "足りぬ分が元本に足され、その元本に利がつく。……終わらぬ勘定だ。"
    en: "The shortfall joins the principal, which draws interest. …It never ends."
    register: "jidaigeki_plain"
    duration_s: 7.0
  - id: "ch05.b13.nyaakoto.002"
    speaker: "samurai"
    ja: "鷲尾家、債権譲渡済み……虎之介。"
    en: "Washio house: debt transferred… Toranosuke."
    register: "jidaigeki_plain"
    duration_s: 4.5
  - id: "ch05.b13.kozo.003"
    speaker: "foundry_master"
    ja: "金屋子さんの掛軸に、評価額零、やと。"
    en: "They tagged the Kanayago scroll 'Assessed value: zero.'"
    register: "yamato_gruff_quiet"
    duration_s: 4.5
  - id: "ch05.b14.tarifa.001"
    speaker: "boss_tarifa"
    ja: "稼働再開を確認。ご協力に感謝いたします。"
    en: "Resumed operations confirmed. Thank you for your cooperation."
    register: "alien_corporate_keigo"
    duration_s: 5.0
  - id: "ch05.b14.oyuki.002"
    speaker: "leader"
    ja: "帳は民の前に。あなた様の帳は、どこに掲げてございますか。"
    en: "A registry belongs before the people. Where is yours posted?"
    register: "business_keigo"
    duration_s: 5.5
  - id: "ch05.b14.tarifa.003"
    speaker: "boss_tarifa"
    ja: "……非公開でございます。"
    en: "…That is confidential."
    register: "alien_corporate_keigo"
    duration_s: 3.0
  - id: "ch05.b14.tarifa.004"
    speaker: "boss_tarifa"
    ja: "設備を自律稼働へ。湯路、全開。"
    en: "Equipment to autonomous operation. All channels open."
    register: "alien_corporate_keigo"
    duration_s: 4.0
  - id: "ch05.b14.kozo.005"
    speaker: "foundry_master"
    ja: "あかん、湯を流しよった！　鋳物場が火の海や！"
    en: "No! She's let the melt run! The casting floor's a sea of fire!"
    register: "yamato_gruff_raised"
    duration_s: 5.0
  - id: "ch05.b15.kozo.001"
    speaker: "foundry_master"
    ja: "湯路の口が光ったら、すぐ湯が来るで！"
    en: "When a channel mouth glows, the melt is coming!"
    register: "yamato_gruff_raised"
    duration_s: 4.0
  - id: "ch05.b15.okinu.002"
    speaker: "weaver"
    ja: "うちの機が……。堪忍え、壊しとくれやす。"
    en: "My looms… Forgive me. Break them."
    register: "kyoto_soft_grief"
    duration_s: 4.5
  - id: "ch05.b15.kohagi.003"
    speaker: "scout"
    ja: "高殿へ逃げた。上。"
    en: "She ran to the tatara hall. Up top."
    register: "terse_report"
    duration_s: 2.5
  - id: "ch05.b16.tarifa.001"
    speaker: "boss_tarifa"
    ja: "債務者番号……未登録。ただ今、登録いたします。"
    en: "Debtor number… unregistered. I shall register you now."
    register: "alien_corporate_keigo"
    duration_s: 6.0
  - id: "ch05.b16.nyaakoto.002"
    speaker: "samurai"
    ja: "その帳には載らぬ。"
    en: "I will not be in your book."
    register: "jidaigeki_plain"
    duration_s: 2.5
  - id: "ch05.b16.tarifa.003"
    speaker: "boss_tarifa"
    ja: "稼働率百四十パーセント。"
    en: "Utilization: one hundred forty percent."
    register: "alien_corporate_keigo"
    duration_s: 3.0
    repeatable: true
  - id: "ch05.b16.tarifa.004"
    speaker: "boss_tarifa"
    ja: "引き当てます。"
    en: "Drawing down."
    register: "alien_corporate_keigo"
    duration_s: 2.0
    repeatable: true
  - id: "ch05.b16.tarifa.005"
    speaker: "boss_tarifa"
    ja: "休憩は計上されません。"
    en: "Breaks will not be booked."
    register: "alien_corporate_keigo"
    duration_s: 3.0
    repeatable: true
  - id: "ch05.b16.tarifa.006"
    speaker: "boss_tarifa"
    ja: "増産体制に移行いたします。"
    en: "Transitioning to increased production."
    register: "alien_corporate_keigo"
    duration_s: 3.0
  - id: "ch05.b16.tarifa.007"
    speaker: "boss_tarifa"
    ja: "……設備に損傷。"
    en: "…Equipment damage."
    register: "alien_corporate_keigo"
    duration_s: 2.5
    repeatable: true
  - id: "ch05.b16.kozo.008"
    speaker: "foundry_master"
    ja: "雨が湯に落ちたら、湯気が吹くで！"
    en: "Rain on the melt means steam bursts!"
    register: "yamato_gruff_raised"
    duration_s: 4.0
  - id: "ch05.b16.tarifa.009"
    speaker: "boss_tarifa"
    ja: "……外套、過負荷。"
    en: "…Mantle overloaded."
    register: "alien_corporate_keigo"
    duration_s: 3.0
    repeatable: true
  - id: "ch05.b16.tarifa.010"
    speaker: "boss_tarifa"
    ja: "……想定外の、損失で……"
    en: "…An unforeseen… loss…"
    register: "alien_corporate_keigo_failing"
    duration_s: 3.5
  - id: "ch05.b16.nyaakoto.011"
    speaker: "samurai"
    ja: "掴まれ！"
    en: "Take my hand!"
    register: "jidaigeki_raised"
    duration_s: 1.5
  - id: "ch05.b16.kozo.012"
    speaker: "foundry_master"
    ja: "……鉄は、誰も選ばん。"
    en: "…Iron chooses no one."
    register: "yamato_gruff_quiet"
    duration_s: 3.0
  - id: "ch05.b17.oyuki.001"
    speaker: "leader"
    ja: "鏃と銃は隠れ谷へ。絹は提灯街へ。"
    en: "Arrowheads and guns to the Hidden Valley. Silk to the Lantern Ward."
    register: "business_keigo"
    duration_s: 4.5
  - id: "ch05.b17.otane.002"
    speaker: "farmer_young"
    ja: "荷鞍、締めといたで。足は短いけど、根性ある子らや。"
    en: "Pack saddles are cinched. Short legs, but these two have grit."
    register: "kamigata_bright"
    duration_s: 5.5
  - id: "ch05.b17.artisan.003"
    speaker: "artisan"
    ja: "朝や……。朝の匂いがする。"
    en: "Morning… It smells like morning."
    register: "local_colloquial"
    duration_s: 3.5
  - id: "ch05.b18.kozo.001"
    speaker: "foundry_master"
    ja: "三晩目の鉧、出たで。ええ鉄や。"
    en: "The third night's bloom is out. Good iron."
    register: "yamato_gruff"
    duration_s: 4.0
  - id: "ch05.b18.okinu.002"
    speaker: "weaver"
    ja: "上げとくれやす。"
    en: "Raise it, please."
    register: "kyoto_soft"
    duration_s: 2.0
  - id: "ch05.b18.kohagi.003"
    speaker: "scout"
    ja: "……起こすな。"
    en: "…Let them sleep."
    register: "terse_report"
    duration_s: 2.0
  - id: "ch05.b18.iota.004"
    speaker: "clerk"
    ja: "恐れ入ります。帳簿機関、会計補のイオタと申します。"
    en: "Pardon the intrusion. I am Junior Auditor Iota, of the Ledger Engine."
    register: "manual_keigo"
    duration_s: 5.5
  - id: "ch05.b18.iota.005"
    speaker: "clerk"
    ja: "貴工房の掲示を、帳簿様が読みました。数字が、閉じております。"
    en: "The esteemed Ledger has read your posting. Its numbers… close."
    register: "manual_keigo"
    duration_s: 6.5
  - id: "ch05.b18.iota.006"
    speaker: "clerk"
    ja: "……ご相談がございます。金庫の中から。"
    en: "…I wish to consult with you. From inside the vault."
    register: "manual_keigo"
    duration_s: 4.5
  - id: "ch05.b18.iota.007"
    speaker: "clerk"
    ja: "連絡用の石板様を一枚、払い出しいたします。お持ちください。"
    en: "Disbursing one honored message slate. Please keep it with you."
    register: "manual_keigo"
    duration_s: 6.5
  - id: "ch05.b18.oyuki.008"
    speaker: "leader"
    ja: "罠かもしれません。けれど、中の数字です。"
    en: "It may be a trap. But those are the numbers from inside."
    register: "business_keigo"
    duration_s: 4.5
  - id: "ch05.b18.nyaakoto.009"
    speaker: "samurai"
    ja: "先生も、あの城のどこかに。"
    en: "Sensei is somewhere in that citadel too."
    register: "jidaigeki_plain"
    duration_s: 3.0
  - id: "ch05.b00.enforcer.001"
    speaker: "enforcer"
    ja: "……音。照合します。"
    en: "…A sound. Reconciling."
    register: "alien_corporate_keigo"
    duration_s: 3.0
    repeatable: true
  - id: "ch05.b00.enforcer.002"
    speaker: "enforcer"
    ja: "未登録の足跡。捜索を開始します。"
    en: "Unregistered tracks. Commencing search."
    register: "alien_corporate_keigo"
    duration_s: 4.0
    repeatable: true
  - id: "ch05.b00.enforcer.003"
    speaker: "enforcer"
    ja: "債務者を視認。回収します。"
    en: "Debtor sighted. Commencing collection."
    register: "alien_corporate_keigo"
    duration_s: 3.5
    repeatable: true
  - id: "ch05.b00.enforcer.004"
    speaker: "enforcer"
    ja: "所在不明。損失として計上します。"
    en: "Whereabouts unknown. Booking as a loss."
    register: "alien_corporate_keigo"
    duration_s: 4.0
    repeatable: true
  - id: "ch05.b00.enforcer.005"
    speaker: "enforcer"
    ja: "後退します。資産の保全を優先。"
    en: "Withdrawing. Asset preservation takes priority."
    register: "alien_corporate_keigo"
    duration_s: 4.0
    repeatable: true
  - id: "ch05.b00.enforcer.006"
    speaker: "enforcer"
    ja: "区画を清算します。"
    en: "Liquidating the sector."
    register: "alien_corporate_keigo"
    duration_s: 2.5
    repeatable: true
  - id: "ch05.b00.conscript.007"
    speaker: "conscript"
    ja: "すまん……体が、勝手に……！"
    en: "Sorry— my body won't stop—!"
    register: "local_colloquial_strained"
    duration_s: 4.0
    repeatable: true
  - id: "ch05.b00.conscript.008"
    speaker: "conscript"
    ja: "頼む……首輪を……！"
    en: "Please… the collar…!"
    register: "local_colloquial_strained"
    duration_s: 3.0
    repeatable: true
  - id: "ch05.b00.conscript.009"
    speaker: "conscript"
    ja: "……恩に着る。"
    en: "…I owe you."
    register: "local_colloquial"
    duration_s: 2.5
    repeatable: true
  - id: "ch05.b00.nyaakoto.010"
    speaker: "samurai"
    ja: "峰で打つ。"
    en: "The back of the blade."
    register: "jidaigeki_plain"
    duration_s: 1.5
    repeatable: true
```
