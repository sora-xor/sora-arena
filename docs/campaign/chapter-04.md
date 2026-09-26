# Chapter 4: 第四章 田畑の解放 / Agricultural Liberation

> **Monetary boundary (bible §2).** In this chapter, as in the whole campaign, SORA XOR (and the registry that leads to it) is a production-only storytelling premise. XOR is cut only against finished, inspected goods, is never shown as a balance or converted, and has no link to multiplayer XOR bonds, NFTs, wallets or IrohaConnect. It makes no claim about real-world money, investment or policy, and it does not describe the real SORA network or the design in the SORA Nexus article. **Review note (C1 lead, 2026-09-25):** names, calendar, speaker ids, Japanese punctuation and YAML field names in this file follow bible §9.1, §12.5 and §18.

**Status:** production design and script for `ch04_irrigation`. It follows the [story bible](story-bible.md) and uses its beat taxonomy (§12), cast (§6), enemies (§7), boss rules (§8), pacing (§10) and places (§14). Every number here is a **proposal** for the lane that owns it: L1 for beats and saves, L2 for enemies, stealth and weapon feel, L3 for the boss, L4 for UI, L5 for music and barks, C2/C3 for spaces, C4 for missions and C9 for cinematics. Nothing is implemented yet. Voice-over is not recorded (catalog `voice_over: not_recorded`). Native Japanese review (B7), historian and practitioner review, and playtest timing are still pending (§10).

| | |
|---|---|
| Chapter id | `ch04_irrigation` (catalog chapter index 3, `map: 0`, entered from the Arena 0 lower gate) |
| Target | **60 min** (3,600 s). C 13 · E 4 · S 4 · P 21.5 · M 8 · Cin 9.5 min, exactly the bible §10 row |
| Beats | **18** sequenced beats, plus 6 passive collectibles (not counted) |
| Voice lines | **115**, matching §10, plus 15 HUD tutorial prompts (text only) |
| Weapons unlocked | **2** 鎖鎌 Kusarigama and **5** コイル火縄銃 Coil Matchlock, both at `ch04.b03` |
| Mechanic flags | `hayago_reload` (b03) and `crank` (b06). Also new in play: the hold task, the kusarigama bind (flag `kusarigama_bind` proposed in §6.2), tall-barley sight rules, paddy mud, mounted cargo with a lead horse, and a mounted boss phase |
| Boss | `boss_hakari`, 査定機「秤」 (Assessor Engine *Hakari*), piloted by 査定官 マルジナ (Assessor Margina) |
| Production sites | 0 → `ch04.b06` 水路の取水口 · 1 → `ch04.b11` 田畑の水車 · 2 → `ch04.b17` 収穫の分配所. This is the catalog order, so no remap is needed |
| Registry page | 用水 12枚 · 水車 1基 · 麦 30束 · 麦（返還） 120束 |
| Horse segments | b02 (travel), b14 (cargo, leading a pack horse), b16 phase 1 (mounted boss) |
| Light moment | One, proposed and pending tone sign-off (b14: Kurimaru and the barley) |

Catalog canon lines (schema 3, chapter 4) are placed as bible §20 says: line 1 → `ch04.b01.taemon.001`, line 2 → `ch04.b06.nyaakoto.003`, line 3 → `ch04.b17.taemon.004`. Their Japanese and English are verbatim.

---

## 1. Synopsis

**Early summer, 元和九年四月中旬 (Genna 9, mid 4th month; about mid to late May by the solar calendar; bible §9.1).** In Yamato this is 麦秋, "barley autumn": the barley stands gold on the drained paddies and must be cut before the rice goes in. Ten days after the Lantern Ward rose, Oyuki brings the League down to **Shimomura (下村)**, the lower village 2 km below the ruined estate.

The Credit House got there first. It has clamped a cyan debt seal on the First Weir of the Great Reservoir, set meter posts on every channel to sell water "by the measure", and seized the village waterwheel and its 竜骨車 chain pumps. It has also bought the unplanted rice on credit (青田買い). The balance on every door ticks up each night, and without water the seedlings in the nursery beds will die within ten days.

Nyaakoto scouts the bank roads with **Otane**, the village's young sluice keeper. Tetsugorō comes down from the Hidden Valley with Headman Taemon's old crow-scaring gun, rebuilt with a captured coil breech. Otane lends Nyaakoto her brother's kusarigama. The brother, **Yosaku**, was collared and set to guard the dam. She *entrusts* the weapon rather than lending it (「借りやない。預けるんや。」), which echoes Sekireisai's 「刀は民から預かるものじゃ」.

The party breaks a collection patrol in the tall barley, then slips past the collared guards on the dam. Nyaakoto cranks open the First Weir, and when the debt seal breaks every collar on the dam goes dark. He holds the weir while the gate boards rise, and water runs down the valley and fills the paddies.

In a sun-shower (狐の嫁入り) he escorts the carpenters' ox-cart to the mill and helps rebuild the lifting wheel. Then he guards the planters while they plant under drone nets. On the dike Oyuki opens the **生産改帳**, copying the tallies of chapters 1–3 onto its first page and then writing the day's water and wheel. Taemon: 「紙は紙や。」 Oyuki: only what exists goes on paper. Nyaakoto delivers barley to the three hamlets, riding Kurimaru and leading Bunta, the village pack mare.

At the granary, **Hakari**, an 8 m balance-beam walker, wades out of the river haze. Margina announces that the whole harvest is seized as collateral. Nyaakoto fights it on horseback around the paddy block, circling left and shooting the weigh-coils as each leg plants. Then he fights on foot at the mill, where the engine kneels to "assess" the new waterwheel. The machine collapses into a paddy, and Margina ejects and flees (「損切りいたします」). The barley goes back into the granary with each grower's name on it.

At dusk the fireflies rise. Otane joins the League, and Oyuki records one new member. On the east ridge Toranosuke watches from Arashi, then turns away.

**What the chapter proves.** It is the first time the League *makes* something at village scale and writes it down: water, a wheel, planted paddies and distributed barley. This is the bible's production premise (§2) in its plainest form, and it comes before the first XOR tally in ch05.b12. The chapter-complete screen shows the registry page instead of a score.

**Themes carried** (bible §1.3):

- 活人剣 extends to livelihoods: Otane's 預ける, and the non-lethal dam.
- Extraction against sharing: water sold by the measure, against the old rotation (番水) and the shrine of the god who *divides* water (水分).
- Debt as a chain: Yosaku's collar goes dark only when the means of production is freed.

**Tone.** This is serious drama. The only light moment (b14) is animal behavior, not a joke, and it happens far from the boss and from any grief beat. Margina's menace is polite arithmetic: 「ご異議は書面にて。受付は、秋でございます。」

---

## 2. Time of day, weather and lighting

Bible §16 row 4: hazy early-summer day, height fog, a sun-shower mid-chapter, fireflies at dusk. The sun rises in the east-north-east and sets in the west-north-west; the valley runs north (reservoir) to south (river).

| Beats | In-fiction time | Key light and sky | Weather and FX | Notes |
|---|---|---|---|---|
| b01–b04 | 07:30–09:30 | Hazy sun about 5,600 K at 25–40° elevation; humid height fog, densest over the paddies | Dry, cracked nursery beds; heat shimmer over the barley from 09:00 | Gold barley against bleached, dry paddies: the "before" picture |
| b05–b07 | 10:00–11:30 | 5,600–5,800 K; the reservoir water is a bright specular sheet | Light breeze on the water (wind 2 m/s) | Crest silhouettes read against the bright water, which helps stealth readability |
| b08–b09 | 12:00–12:40 | Midday 5,800 K; paddies become mirrors of the haze and cumulus | Flowing water, foam at drops, a heron takeoff | Mirror paddies need stable reflections (below) |
| b10–b12 | 13:00–14:30 | Sun stays out (5,600 K) under a single towering cumulus | **狐の嫁入り sun-shower** from b10 at 50% to b12 at 50%: backlit rain streaks, rain rings on the paddies, wet timber and straw. When it stops: steam wisps off the dikes and an optional faint rainbow over the reservoir end | The sun-shower is also a gameplay beat: a villager's slow-match fizzles while the coil matchlock still fires (b12) |
| b13–b14 | 15:00–16:00 | 4,800 K, lower sun, humid haze; swallows over the water | Dry | Warm, calm registry and delivery beats |
| b15–b16 | 16:30–17:15 | 4,200 K and long shadows; haze thickens from the river (height fog ×1.8 toward the south) | The frog chorus stops when Hakari appears | Hakari's cold 8,500 K ledger lights cut the warm haze. **Amber telegraph decals must use animated edge pulses** (§15.1) to stay distinct from golden-hour light; accessible palette available |
| b17 | 17:30 | Golden 3,800 K | Dust and chaff in shafts of light | |
| b18 | 19:10, blue hour | Ambient sky about 9,000 K; last warm band on the east ridge | Fireflies (Genji type, 2–3 s blink cycles): about 300 on Windows, 80 on Mac; hearth and 行灯 glow at 1,900 K in the farmhouses | Toranosuke is a silhouette against the ridge light |

**Rendering notes.**

- Mirror paddies: Lumen reflections on Windows. On Mac, SSR plus reflection captures per paddy block. Planar reflections are not budgeted.
- Barley: Nanite foliage with world-position-offset wind on Windows. Card LODs and reduced density on Mac (bible §16 fallback).
- Cyan meter numerals must not bloom across whole paddies in reflection. Cap emissive at 8 nits and let them go dark at b08.
- Mac: software Lumen, no more than 8 shadow-casting dynamic lights per view (lanterns only in b18), rain particles capped at 40% of the Windows count, and 80 fireflies.

---

## 3. Locations and layouts

Coordinates are in metres: +X east, +Y north, Z up. Each place has its own origin, given below. Everything here is campaign-only geometry in chapter sublevels. None of it touches Arena 0 collision (bible §14). The open valley is a World Partition level. Terrain follows the Mesh Terrain research path and its limits in [mesh-terrain-nyaagyu.md](../mesh-terrain-nyaagyu.md), with a conventional-LOD Mac tier.

### 3.1 `pl_shimomura` 下村: Lower Village fields (new open area, 800 × 600 m)

**Frame.** X −400…+400, Y −300…+300. The origin is the village crossroads (辻) between the headman's house and the granary. Ground falls from z = 16 m at the north edge (the gorge mouth) to z = 0 at the river on the south edge. The west edge rises into the terraces (`pl_tanada`). Packed-earth roads and dikes throughout; there is no paving (bible §15.1).

| # | Landmark | Position (X, Y) | Size and notes |
|---|---|---|---|
| L01 | Estate road descent, the portal to Arena 0's lower gate | (+390, +295) | 4 m packed-earth road; b01's aerial shot starts here. Streaming boundary |
| L02 | Gorge mouth and canal head → `pl_otameike` | (−80, +300) | 220 m gorge path climbing 8 m, beside the stone-lined outlet channel |
| L03 | Main canal 用水路 (大井手) | X −80, from Y +300 to −300 | 1.8 m wide and 1.0 m deep with 石積み banks; 3 m bank road on the east bank (X −74) |
| L04 | Headman's house 庄屋屋敷 (`pl_shoya_yashiki`, §3.2) | (+10, +90) | Compound 42 × 34 m |
| L05 | Granary and distribution square (`pl_gogura`, §3.6) | (+70, −20) | 郷蔵 9 × 5.4 m; square 30 × 24 m to its south |
| L06 | Mill 水車小屋 (`pl_suisha_goya`, §3.5) | (−84, −66) | West bank of the canal; plank bridge to the bank road |
| L07 | Upper hamlet 上垣内 (かみがいと) | (+150, +110) | 6 thatched farmhouses; drop-off `hamlet_kami` |
| L08 | Middle hamlet 中垣内 (なかがいと) | (+150, −80) | 8 farmhouses; drop-off `hamlet_naka` |
| L09 | Lower hamlet 下垣内 (しもがいと) | (+60, −215) | 5 farmhouses under river willows; drop-off `hamlet_shimo` |
| L10 | Barley fields 麦畑 (drained paddies) | X +120…+380, Y −260…+240 | Plots 30 × 20 m divided by 0.5 m 畦; 3 m farm roads every 90 m (X +160, +250, +340; Y −100, −20, +60) |
| L11 | Credit House collection station 徴収所 | (+320, −10) | Graphite pad 20 × 12 m, 1.4 m barriers (hard cover), drone rack, ledger kiosk |
| L12 | Flooded paddies 水田 | X −360…+110, outside compounds | 5–8 cm water over 20 cm mud; plots 30 × 20 m |
| L13 | Boss paddy block (`vol_paddies_boss`, §3.7) | X −70…+110, Y −190…−70 | 180 × 120 m of flooded paddy inside a 600 m ring road |
| L14 | Meter posts ×6 | MP01 (−80, +250), MP02 (−80, +130), MP03 (−80, −140), MP04 (+20, +40), MP05 (+250, +150), MP06 (+250, −150) | 2.2 m graphite posts with cyan numerals and the alien ledger sigil. They go dark in b08 |
| L15 | Terrace approach → `pl_tanada` | (−360, +40) | Stone steps into the west slope |
| L16 | Planting paddies (b12) | X −300…−120, Y −200…−160 | A row of six plots of 30 × 40 m (about 1 反 each), flooded in b08 and planted as one front; the far dike is at Y −230 |
| L17 | Nursery beds 苗代 | around (−20, +40) and (+40, +150) | Cracked and dry at the start; flooded after b08 |
| L18 | East ridge (outside the bounds) | (+470, +100), z +42 m | Red pines; Toranosuke's vantage in b18 |
| L19 | River and willows | Y −300 | Hard bounds; the ford is closed by flood debris |

**Routes (splines).**

| Spline | Used by | Path | Length |
|---|---|---|---|
| `spl_dote_scout` | b02 | Headman's gate → canal bank at MP02 → north on the bank road to MP01 → east on the upper road to (+150, +250) → south to the upper hamlet → barley overlook (+160, +60) → west back to the gate | about 790 m |
| `spl_mugi_sweep_a` / `_b` | b04 patrols | North–south farm roads at X +250 and X +340, Y −100…+60 | 160 m each |
| `spl_mill_road` | b10 ox-cart | Headman's yard → west to the canal bank (−74, +90) → south on the bank road to the mill bridge (−74, −60) | about 235 m |
| `spl_aze_loop` | b14 cargo | Granary → upper hamlet (X +150 road) → middle hamlet (toll post at (+150, +20)) → lower hamlet (via Y −190) → granary (X +110 road and the north road). West bypass of the toll post on the X +110 ring road adds about 80 m | about 900 m |
| `spl_boss_ring` | b16 P1 | North road Y −70, east road X +110, south road Y −190, canal bank road X −74. 4 m wide, dry packed earth | 600 m |

**Movement rules.** Horses use only the bank roads, farm roads and the ring road. The 0.3–0.6 m 畦 ridges and the flooded paddies block horses, or slow them in mud (§6.6). On foot the player can cross everything: 畦 at walk speed, paddies at ×0.6 speed.

**Cover.**

| Cover | Kind | Where and notes |
|---|---|---|
| Barley | Soft cover: blocks sight, stops no projectiles | §6.6 sight rules |
| Farmhouse walls, stone footings, canal walls (1.0 m) | Hard | |
| Collection-station barriers (1.4 m) | Hard | |
| Dikes (0.5–0.8 m) | Hard when crouched | |
| Stored 稲架 pole stacks | Partial | |
| Villager cart barricades | Hard | Arena edges in b16 |

**Sightlines.**

- The flat, flooded floor gives 300 m+ views. Chapter 4 therefore uses no `marksman` at all, which keeps the paddies readable.
- Inside the barley, sight drops below 5 m.
- The headman's compound breaks the north–south view.
- The gorge mouth can be seen from the canal bank road.
- The boss block is open on all four sides, so mounted archery always has a line.
- From the east ridge the planted paddies are visible (b18).

**Spawn, entry and exit.**

- Player starts: `ps_shoya_doma` (+8, +88) after b01; `ps_canal_head_bank` (−74, +280) after b08; `ps_boss_ring_ne_mounted` (+110, −70) after b15; `ps_chapter_end` (−150, −150) on the dike above the planted paddies.
- Kurimaru hitch points: the headman's yard (+18, +96), the gorge foot in `pl_otameike`, and the mill yard (−90, −56). A whistle recalls her within 3 s anywhere on the roads.
- There is no walk-out exit. The chapter ends in b18 and loads ch05 from the registry screen.

**Trigger volumes (this place).**

| Volume | Position and size | Used by |
|---|---|---|
| `vol_shoya_gate` | (+31, +90), 6 × 6 m | b02 complete |
| `vol_meter_post_02` | (−76, +130), r 12 m | b02 line |
| `vol_mugi_overlook` | (+160, +60), r 15 m, on a bank 1.5 m high | b02 lines and scout marks |
| `vol_scout_end` | (+100, +75), r 15 m | b02 line |
| `vol_mugibatake_b04` | X +160…+340, Y −100…+60 | b04 bounds |
| `vol_barley_tall` | All barley plots | Sight occluder (b04; also active in b14) |
| `vol_escort_mid` | (−74, +20), r 10 m | b10 wave 1 |
| `vol_toll_post` | (+150, +40), 20 × 8 m | b14 wave 1 |
| `vol_paddies_boss` | X −100…+130, Y −210…−50, including the mill yard | b16 arena (locked) |

**Spawn points and pickups (this place).**

| Id | Position | Id | Position |
|---|---|---|---|
| `sp_mugi_north` | (+250, +50) | `sp_paddy_air_e` | (−100, −160), z +15 |
| `sp_mugi_south` | (+250, −95) | `sp_paddy_air_n` | (−210, −90), z +15 |
| `sp_collect_station` | (+320, −10) | `sp_far_dike` | (−210, −230) |
| `sp_collect_station_air` | (+320, −10), z +8 | `sp_toll_post` | (+150, +20) |
| `sp_paddy_bank_east` | (−30, +20) | `sp_toll_air` | (+150, +20), z +10 |
| `sp_canal_air` | (−60, −20), z +12 | `pk_arrows_se` / `pk_arrows_nw` | (+110, −190) / (−74, −70) |
| `sp_mill_road` | (−74, −110) | `pk_hopper_spill_01…03` | (+40…+80, −70) |

### 3.2 `pl_shoya_yashiki` 庄屋屋敷: the headman's house (proposed place id, a sub-place of L04)

- **Compound:** 42 × 34 m inside a 1.6 m hedge (生垣) and bamboo fence. A 冠木門 gate on the east side (`vol_shoya_gate`).
- **Main house:** 16 × 10 m, thatched hipped-and-gabled roof.
  - A 5 × 10 m 土間 with 竈 and water jars.
  - A raised 板の間 with the 囲炉裏 (the b01 staging).
  - A back 座敷 with the writing desk that holds collectible `ch04.c06`.
- **Yard:** 20 × 14 m of packed earth with straw drying mats.
  - Two seized 竜骨車 chain pumps, chained and tagged with cyan ledger sigils. These are the "pumps" of the canon EN line.
  - A stone well, and a 納屋 shed with 鍬, 鋤, 馬鍬, 鎌, 箕, 扱箸 and 唐竿.
- **Practice (b03):** three straw bales in the dry nursery field east of the gate at 15, 25 and 40 m. The player shoots from the gate step.
- **No combat** takes place here.

### 3.3 `pl_otameike` 大溜池・一の堰: Great Reservoir and First Weir

**Frame.** Separate sublevel, reached by the 220 m gorge path from L02. The origin is the winch platform on the dam crest; +Y is toward the water.

| Element | Position (X, Y) | Size and notes |
|---|---|---|
| Earth dam 堤 | Crest X −170…+30, Y 0…+6 | 200 m long; crest 6 m wide, gravel-surfaced; 10 m above the downstream toe (toe at Y −25) |
| First Weir sluice | (0, +4), set into the upstream face | Existing `SM_Nyaagyu_IrrigationSluice` (3.5 × 1.7 × 3.2 m) with a new windlass drum, rope and 堰板 gate boards |
| Winch platform | (0, −3) | 8 × 6 m timber deck; actor `sluice_winch_01` |
| Outlet channel 放水路 | From (0, −25) south down the gorge | Stone walls 2.5 m, climbable at two authored points |
| Stone stair | Toe (−20, −25) → crest (−20, 0) | 22 steps; guard point `pt_stair_top` (−20, +1) |
| Guard huts ×2 (alien prefabs) | A (−60, +3), B (−110, +3) | 6 × 4 m graphite boxes. Hut B holds heirloom `ch04.c04` |
| Meter kiosk | (+6, −8) | 8 m sensor cone facing the outlet walls |
| Spillway 余水吐 | West end (−170, 0) → toe | 3 m stone channel of shallow running water (`vol_spillway`, footstep noise ×0.5) |
| Toe ditch and reed bed | Along Y −27; reeds at X −170…−120 | `vol_toe_ditch` (puddle noise), `vol_reed_bed_west` (shade) |
| Willows | (−40, −30), (+20, −32) | `vol_willow_shade_01` / `_02`: guards' sight falls to 700 cm here |
| Water-side revetment ledge | X −170…−10, Y +7…+9, 1 m below the crest | Out of the crest guards' sight, but under the water drone's loop |
| Reservoir | North of the dam, about 320 × 240 m | Drone loop `spl_reservoir_loop`: a 200 × 120 m ellipse centred on (−70, +80), 8 m up |
| Gorge foot | (0, −180) | `vol_gorge_foot`; the horses are hitched at (−5, −185) |

**Stealth routes (b05).**

1. **Stone stair:** short but watched by `g_stair_top` scanning 120° every 6 s.
2. **West route:** through the reed ditch → up the spillway (running water halves noise) → along the revetment ledge (hidden from the crest; time it against the drone) → up onto the crest behind hut B.
3. **East route:** up the outlet-channel walls beside the sluice. Fastest, but it crosses the kiosk's sensor cone, which sees only moving targets; stop inside it to stay safe.

**Patrols.**

- `spl_crest_a` walks X −100…−20.
- `spl_crest_b` (Yosaku) walks X −170…−100 and pauses 6 s at the spillway lip to look down.
- `spl_hut_loop` circles hut A.

**Sightlines.** The crest overlooks the last 60 m of the gorge path, which is exposed. Within 8 m of the dam face the toe ditch is dead ground. The drone can see the revetment ledge and the crest's water edge.

**Hold (b07).**

- `vol_weir_platform` is a 12 m radius around the winch.
- Enemies arrive from three sides: the crest from the west (`sp_dam_west` (−150, +3)), the east abutment road (`sp_dam_east` (+30, +3)), and a skiff landing on the revetment (`sp_dam_north` (−30, +10)). Drones come from `sp_reservoir_air` (−70, +80, z +12).
- The 6 m crest makes shield enforcers come single-file, so the player can bind the shield edge from the side.

**Entry and exit.** Enter from the gorge foot. After b07, the exit is the gorge path back down to `ps_canal_head_bank`, which b08's cinematic covers.

### 3.4 `pl_tanada` 棚田・水分社: terraces and the water shrine (optional)

- **Frame.** West-slope sublevel, 220 m wide × 260 m deep, climbing 34 m westward from the L15 approach. The origin is the approach step.
- **Terraces.** 14 of them, 6–14 m deep, on 1.2–2.4 m dry-stone risers (野面積み). A zigzag path with stone steps.
- **Water.** A spring at the top feeds the terraces through wooden 水口 inlet boards at each terrace end.
- **Shrine.** At the top, (−200, +200) local, z +34 m: a small 水分社 小祠 (1.2 × 0.9 × 1.6 m) on a stone base, a 2.8 m vermillion 明神 torii, two stone lanterns, a 鈴緒 bell rope, and the spring in a hollowed stone basin. The shrine keeper (villager pool) sits on the step.
- **Points of interest.**

| POI | Location | What it is |
|---|---|---|
| `poi_minakuchi_order` | Terraces T11–T14 | Open the four upper inlets top-down. Opening them out of order floods the path, and a reset lever sits at the spring |
| `poi_field_hut_cache` | T6 野小屋 field hut | 6 arrows and 10 早合; Kohagi's chalk mark `ch04.c02` |
| `poi_tanada_vista` | T10 lip (`vol_tanada_vista`) | View north-east over the valley and up to the burned estate roofline 2 km away |
| `ch04.c01` | Behind the shrine | Revealed when the inlet puzzle is solved |

- **Guidance.** There are no markers. The sound of the spring and the bell rope, and the white stepping stones of the path, lead the player up.

### 3.5 `pl_suisha_goya` 水車小屋: the mill (at L06)

- **Hut.** 7.2 × 5.4 m (4 × 3 間) with board walls and a thatched roof. Inside: the brake lever (`st_wheel_brake`), spare boards and the axle cradle.
- **Wheel.** An undershot **lifting wheel** (揚水水車), 4.5 m in diameter and 0.9 m wide, with 12 paddles (6 broken at the start) and 12 wooden buckets on the rim. It sits in a 12 m stone millrace, 1.2 m wide with 1.0 m walls. The buckets pour into a wooden flume (樋) on trestles at 3.4 m, which runs 40 m west to the upper paddies.
- **Stations.** `st_wheel_rim` is a plank platform at the wheel's lower arc. `st_axle_seat` is the pair of bearing blocks on both sides.
- **Yard.** 25 × 20 m on the west bank. A 1.2 m stone footing along the millrace serves as boss P2 cover. A 4 m plank bridge crosses to the ring road.

### 3.6 `pl_gogura` 郷蔵: granary and distribution square (at L05)

- **Granary.** 郷蔵 9 × 5.4 m on a 0.6 m stone footing, with earthen plastered walls and a tiled roof. The mon on the door has been scraped off and covered by a cyan seal. It is restored in b17, when a child chalks the SORA mon back on. The door is `dp_gogura_door` (+70, −23).
- **Square.** 30 × 24 m, with a 高札 notice board covered by a Credit House leaflet and an alien kiosk (seizure notice `ch04.c03` is on the nearby collection station). Sheaves are stacked on 稲架 poles laid flat for the b15 seizure.
- **Registry page.** Collectible `ch04.c05` lies on the intake desk inside the door.

### 3.7 Boss arena `vol_paddies_boss`

- **Phase 1 (mounted).**
  - The player rides the 600 m ring road around the flooded 180 × 120 m block while Hakari wades inside it, turning to track. A counter-clockwise lap keeps Hakari on the bow side.
  - Corner features: the mill (NW); the granary square (NE, the start); a persimmon tree and a 石仏 (SE, arrow pickup `pk_arrows_se`); stored 稲架 pole stacks (SW).
  - Arrow pickup `pk_arrows_nw` is at the mill bridge.
  - Villager cart barricades close the four outward roads.
- **Phase 2 (on foot).**
  - When the fourth coil breaks, Hakari lurches about 120 m north-west to the mill and kneels in the millrace facing the wheel. Kurimaru bolts to the headman's yard (arena mod `dismount`) and the player lands on the mill-bridge approach.
  - The P2 space is the mill yard, the bank road and the millrace edge, about 40 × 30 m.
  - Cover against the low beam: the stone footing and millrace walls. Cover against the claw sweep: the hut corners.
- **Outro.** Hakari staggers 120 m east along the north road and falls into the paddy at the NE corner, 50 m from the granary door. That is where b17 starts.

---

## 4. Beat list

Beats run in this order. `requires` defaults to the previous beat; b09 (optional) and b10 both require b08, so the terraces stay open while the escort waits in the headman's yard. Checkpoint spacing never exceeds 360 target-seconds; the largest gap is 330 s (b07 → b09, or b07 → b10 when the optional b09 is skipped). Enemy archetypes are only those in bible §7. `bound_conscript` stays in `nonlethal_types` and never counts toward defeats. Lethal defeats pass the catalog's `kills: 10` by the end of b04 (12 enemies), which also satisfies the old `requires_kills` 2/5/10 gates before each site. The dialogue triggers name line ids from §7. Lines grouped together play queued in order.

| # | Beat | Type | Place | Min | Checkpoint | Site | Unlocks / registry |
|---|---|---|---|---|---|---|---|
| 1 | `ch04.b01` At the Headman's House | cinematic | `pl_shoya_yashiki` | 2.0 | yes |  | — |
| 2 | `ch04.b02` Scout the bank roads with Otane | horseback_ride (travel) | `pl_shimomura` | 3.0 | yes |  | — |
| 3 | `ch04.b03` The Crow-Scarer and the Kusarigama | dialogue (ambient) | `pl_shoya_yashiki` | 1.5 | no |  | weapons 2, 5; `hayago_reload` |
| 4 | `ch04.b04` Drive off the collection patrol | combat_wave | `pl_shimomura` | 5.0 | yes |  | — |
| 5 | `ch04.b05` Slip past the dam guards | stealth_zone | `pl_otameike` | 4.0 | yes |  | — |
| 6 | `ch04.b06` Open the First Weir | production_task (crank) | `pl_otameike` | 4.0 | yes | 0 | `crank`; 用水 12枚 |
| 7 | `ch04.b07` Hold the weir while the water rises | production_task (hold) | `pl_otameike` | 4.0 | yes |  | — |
| 8 | `ch04.b08` The Water Runs | cinematic | `pl_shimomura` | 1.5 | no |  | — |
| 9 | `ch04.b09` The Terraces and the Water Shrine | explore_optional | `pl_tanada` | 4.0 | yes |  | — |
| 10 | `ch04.b10` Escort the ox-cart to the mill | production_task (escort) | `pl_shimomura` | 4.0 | yes |  | — |
| 11 | `ch04.b11` Repair the waterwheel | production_task (manufacture) | `pl_suisha_goya` | 3.0 | yes | 1 | 水車 1基 |
| 12 | `ch04.b12` Guard the planting line | production_task (defend) | `pl_shimomura` | 4.0 | yes |  | — |
| 13 | `ch04.b13` Open the Production Registry | dialogue (blocking) | `pl_shimomura` | 1.0 | no |  | — |
| 14 | `ch04.b14` Deliver barley to three hamlets | horseback_ride (cargo) | `pl_shimomura` | 5.0 | yes |  | 麦 30束 |
| 15 | `ch04.b15` The Scales Arrive | cinematic | `pl_gogura` | 1.5 | yes |  | — |
| 16 | `ch04.b16` Bring down the Assessor Engine | boss | `pl_shimomura` | 8.0 | yes + per phase |  | — |
| 17 | `ch04.b17` Return the barley to the granary | production_task (carry) | `pl_gogura` | 2.5 | yes | 2 | 麦（返還） 120束 |
| 18 | `ch04.b18` Fireflies | cinematic | `pl_shimomura` | 2.0 | no |  | — |
| | **Σ** | | | **60.0** | | | |

### ch04.b01 庄屋屋敷にて / At the Headman's House

**Type:** `cinematic` · **Place:** `pl_shoya_yashiki` · **Target:** 120 s (2.0 min) · **Checkpoint:** yes

Title card 第四章 田畑の解放 with the vermillion SORA seal (0-6 s). Aerial push down the valley: dry, cracked nursery beds, cyan meter posts on every channel, the sealed reservoir glinting up the gorge. Inside the headman's 土間 around the 囲炉裏: Taemon, Otane, Oyuki, Kohagi (silent, on the beam) and Nyaakoto. Seized 竜骨車 chain pumps stand tagged in the yard, which is why the canon EN line says 'pumps'. Ends with Otane pulling on her head towel and walking out to the horses.

- Sequence `/Game/Campaign/Ch04/Cinematics/LS_Ch04_B01_ShoyaHouse`, 120 s, skippable, fallback `camera_blend`; end state `ps_shoya_doma`, equipped [0, 18].
- **Music:** `ch04_fields_morning`.
- **Fail:** None (skippable).
- **Dialogue triggers:** t=8.0 s → `ch04.b01.taemon.001`; t=14.5 s → `ch04.b01.taemon.002`; t=21.0 s → `ch04.b01.oyuki.003`; t=27.5 s → `ch04.b01.oyuki.004`; t=36.0 s → `ch04.b01.otane.005`; t=43.0 s → `ch04.b01.nyaakoto.006`; t=45.5 s → `ch04.b01.taemon.007`; t=53.0 s → `ch04.b01.otane.008`.

### ch04.b02 お種と土手道を見回る / Scout the bank roads with Otane

**Type:** `horseback_ride / travel` · **Place:** `pl_shimomura` · **Target:** 180 s (3.0 min) · **Checkpoint:** yes

A loop of about 790 m on the bank roads at walk and trot, with a canter stretch on the canal bank. Otane rides ahead on Bunta, sitting on the pack saddle. At the barley overlook the player holds a 2 s look at each patrol group, which gives it a faint ink-wash outline that lasts until b04 ends. There are no map markers. No enemies engage: patrols are 150 m or more away and on a scripted route.

- Horse `kurimaru`, mode `travel`, route `spl_dote_scout`, gaits walk/trot/canter, weapons [0, 18] (katana right side, yumi left arc −170° to +15°).
- Fear: spook radius 900 cm, recover 2.5 s; auto-steer `setting`; on horse down `checkpoint`.
- Companion: Otane on Bunta (`pack_horse`) 600 cm ahead.
- Scout marks (2 s look each): `grp_mugi_north`, `grp_mugi_south`, `grp_collect_station`.
- Complete: {"volume_enter": "vol_shoya_gate"}.
- **Music:** `ch04_ride_scout`.
- **Fail:** Leaving the valley bounds for 10 s triggers a Kurimaru auto-turn (no fail).
- **Dialogue triggers:** `beat_start` → `ch04.b02.otane.001`; `volume_enter:vol_meter_post_02` → `ch04.b02.otane.002`; `volume_enter:vol_mugi_overlook` → `ch04.b02.otane.003`, `ch04.b02.nyaakoto.004`, `ch04.b02.otane.005`; `volume_enter:vol_scout_end` → `ch04.b02.otane.006`.

### ch04.b03 鳥威しと鎖鎌 / The Crow-Scarer and the Kusarigama

**Type:** `dialogue / ambient` · **Place:** `pl_shoya_yashiki` · **Target:** 90 s (1.5 min) · **Checkpoint:** no

Walk-and-talk in the headman's yard. Tetsugorō has come down from the Hidden Valley workshop. Two blocking handovers of at most 8 s each (weapon 5, then weapon 2); control stays free otherwise. Three straw practice bales stand at 15, 25 and 40 m. Shooting them is optional and teaches cheek-stock aim and the hayagō reload. The unlock array is [2, 5] to match the bible §11 order.

- Mode `ambient`, camera `soft_lookat`, interrupt `queue`.
- **Unlocks:** weapons 2, 5; mechanics `hayago_reload`.
- **Music:** `ch04_fields_morning`.
- **Fail:** None.
- **Dialogue triggers:** `beat_start` (ambient) → `ch04.b03.tetsugoro.001`, `ch04.b03.tetsugoro.002`, `ch04.b03.tetsugoro.003`, `ch04.b03.tetsugoro.004`, `ch04.b03.tetsugoro.005`, `ch04.b03.otane.006`, `ch04.b03.nyaakoto.007`, `ch04.b03.otane.008`.

### ch04.b04 麦畑の徴収隊を退けよ / Drive off the collection patrol

**Type:** `combat_wave` · **Place:** `pl_shimomura` · **Target:** 300 s (5.0 min) · **Checkpoint:** yes

12 enemies in three waves across a 180 × 160 m barley block. Barley stands 110–130 cm, so a crouched player is hidden beyond 3 m and standing aliens show their heads and shoulders. Anyone moving through the barley makes the heads sway, and that sway is the tell for both sides. The kusarigama bind is taught on the first blade retainer. Wave 3 retreats to the collection station and makes a stand behind its graphite barriers.

- Bounds `vol_mugibatake_b04`; complete `all_waves_cleared`; max alive 6; allies: Otane (downable).
- Sight occluder `vol_barley_tall`: AI sight 500 cm inside barley; a crouched player is hidden beyond 300 cm; swaying heads give both sides away.
- W1 on `start`: `enforcer_rifle` ×3 @ `sp_mugi_north` (patrol `spl_mugi_sweep_a`), `blade_retainer` ×1 @ `sp_mugi_north`, `drone` ×1 @ `sp_collect_station_air`
- W2 on `alive_below:2`: `enforcer_rifle` ×3 @ `sp_mugi_south` (patrol `spl_mugi_sweep_b`), `blade_retainer` ×1 @ `sp_mugi_south`, `drone` ×1 @ `sp_collect_station_air`
- W3 on `alive_below:2`: `enforcer_rifle` ×2 @ `sp_collect_station`
- **Music:** `ch04_combat_barley`.
- **Fail:** player_died → checkpoint. Otane downs but never dies (auto-revive after 20 s).
- **Dialogue triggers:** `beat_start` → `ch04.b04.otane.001`; `progress_at:0.15` → `ch04.b04.otane.002`; `alert_state:alert` → `ch04.b04.enforcer.003`; `alert_state:search` → `ch04.b04.enforcer.004`; `alert_state:suspicious` → `ch04.b04.drone.006`; `progress_at:0.8` → `ch04.b04.enforcer.005`; `npc_downed:otane` → `ch04.b04.otane.007`; `beat_complete` → `ch04.b04.otane.008`.

### ch04.b05 堤の見張りを抜けよ / Slip past the dam guards

**Type:** `stealth_zone` · **Place:** `pl_otameike` · **Target:** 240 s (4.0 min) · **Checkpoint:** yes

A 90 s ride from the barley to the gorge foot, where the horses are hitched, then about 160 s of stealth up the 10 m earth dam. Three routes: (1) the stone stair, short and watched by g_stair_top; (2) the west route through the reed ditch and up the running-water spillway, then along the stone revetment ledge on the water side (hidden from the crest but inside the water drone's loop); (3) up the outlet channel walls next to the sluice (fast, but in the meter kiosk's 8 m sensor cone). Conscripts are reluctant: their suspicion rate is ×0.8 of the L2 default, and their search barks ask the player to stay hidden. Seal-cutting a conscript is optional; any still collared are freed when the debt seal breaks at ch04.b06 progress 0.25.

- Zone `vol_otameike_stealth`; complete: reach `vol_winch_platform`; on detected `combat`; detection: suspicion ×0.8, alert at 1.0, search 20 s.
- Guard `g_crest_a`: `bound_conscript`, patrol `spl_crest_a`, sight 90° / 1500 cm (shade 700 cm), hearing 800 cm.
- Guard `g_crest_b_yosaku`: `bound_conscript`, patrol `spl_crest_b`, sight 90° / 1500 cm (shade 700 cm), hearing 800 cm.
- Guard `g_stair_top`: `bound_conscript`, patrol `static:pt_stair_top:scan_120deg_6s`, sight 90° / 1800 cm (shade 700 cm), hearing 800 cm.
- Guard `g_hut`: `bound_conscript`, patrol `spl_hut_loop`, sight 90° / 1200 cm (shade 600 cm), hearing 800 cm.
- Guard `g_drone_water`: `drone`, patrol `spl_reservoir_loop`, sight 30° / 2500 cm (shade 1200 cm), hearing 0 cm.
- Noise: gravel in `vol_crest_gravel`; running_water in `vol_spillway` ×0.5; puddle in `vol_toe_ditch`. Shade: `vol_willow_shade_01`, `vol_willow_shade_02`, `vol_reed_bed_west`. Rear takedowns non-lethal. No lures (tsubute arrives in ch06).
- **Music:** `ch04_stealth_dam`.
- **Fail:** Detection → combat (non-lethal conscripts with bamboo staves, plus the drone). On Easy (稽古) detection is always combat. player_died → checkpoint.
- **Dialogue triggers:** `volume_enter:vol_gorge_foot` → `ch04.b05.kohagi.001`, `ch04.b05.kohagi.002`; `idle_s:20` → `ch04.b05.conscript.003`; `alert_state:suspicious` → `ch04.b05.conscript.004`, `ch04.b05.drone.007`; `alert_state:search` → `ch04.b05.conscript.005`; `alert_state:alert` → `ch04.b05.conscript.006`; `npc_freed:yosaku` → `ch04.b05.yosaku.008`; `beat_complete` → `ch04.b05.kohagi.009`.

### ch04.b06 一の堰を開けよ / Open the First Weir

**Type:** `production_task / crank` · **Place:** `pl_otameike` · **Target:** 240 s (4.0 min) · **Checkpoint:** yes · **Site:** 0

Matches the bible §12.4 excerpt, with the co-op NPC added. The windlass (巻き上げ) lifts the 堰板 gate boards of the existing SM_Nyaagyu_IrrigationSluice. The cyan debt seal on the drum breaks at 25% progress with a cold shatter, and every collar at the dam goes dark. When the player leaves to fight, Otane cranks at 0.2 turns/s. Enforcers from wave 1 land by skiff on the north revetment. On completion the League paints the SORA mon on the gate in 弁柄 red (site 0 restored).

- Crank `sluice_winch_01`: 12 turns, band [0.4, 1.2] turns/s, decay 0.05/s, stamina 6/turn, interruptible; co-op NPC `otane` at 0.2 turns/s.
- Event at progress 0.25: `debt_seal_broken` (collars_dark:pl_otameike).
- W1 on `progress_at:0.25`: `enforcer_rifle` ×3 @ `sp_dam_north`
- W2 on `progress_at:0.6`: `drone` ×2 @ `sp_reservoir_air`
- **Unlocks:** mechanics `crank`.
- **Registry:** 用水 12枚 (Irrigation water, 12 paddies).
- **Music:** `ch04_crank`.
- **Fail:** player_died → checkpoint. Progress decays at 0.05/s while nobody cranks; it never fails.
- **Dialogue triggers:** `beat_start` → `ch04.b06.otane.001`; `progress_at:0.25` → `ch04.b06.enforcer.004`, `ch04.b06.conscript.005`; `progress_at:0.3` → `ch04.b05.yosaku.008`; `progress_at:0.5` → `ch04.b06.taemon.002`; `progress_at:0.75` → `ch04.b06.nyaakoto.003`; `beat_complete` → `ch04.b06.taemon.006`.

### ch04.b07 水が満ちるまで堰を守れ / Hold the weir while the water rises

**Type:** `production_task / hold` · **Place:** `pl_otameike` · **Target:** 240 s (4.0 min) · **Checkpoint:** yes

The gate boards ride up on their own while the outlet channel fills; a readable water-level gauge is carved on the stone. Progress pauses whenever an enemy stands inside the 12 m platform volume (contest: pause). The shield enforcers come along the crest, 6 m wide, where only one of them can face the player at a time; the lesson is to bind the shield edge from the side. Wave 3 lands blade retainers on the water-side revetment.

- Hold `vol_weir_platform` for 90 s; contest `pause` (progress pauses while an enemy is inside); max alive 6; ally Otane.
- W1 on `start`: `enforcer_rifle` ×3 @ `sp_dam_west`
- W2 on `progress_at:0.33`: `shield_enforcer` ×2 @ `sp_dam_east`, `enforcer_rifle` ×2 @ `sp_dam_east`
- W3 on `progress_at:0.66`: `blade_retainer` ×2 @ `sp_dam_north`, `drone` ×2 @ `sp_reservoir_air`
- **Music:** `ch04_hold`.
- **Fail:** player_died → checkpoint.
- **Dialogue triggers:** `beat_start` → `ch04.b07.otane.001`; `progress_at:0.33` → `ch04.b07.enforcer.002`, `ch04.b07.otane.003`; `progress_at:0.5` → `ch04.b07.taemon.004`; `progress_at:0.9` → `ch04.b07.enforcer.005`; `beat_complete` → `ch04.b07.taemon.006`.

### ch04.b08 水が走る / The Water Runs

**Type:** `cinematic` · **Place:** `pl_shimomura` · **Target:** 90 s (1.5 min) · **Checkpoint:** no

The water follows the stone-lined channel down the gorge. The six meter posts go dark one by one as the water reaches them. The flow feeds the laterals, and the dry nursery beds and paddies fill into mirrors of the hazy sky. Villagers come out of the farmhouses. A heron lifts off. The planters gather with seedling bundles and 菅笠 hats.

- Sequence `/Game/Campaign/Ch04/Cinematics/LS_Ch04_B08_WaterRuns`, 90 s, skippable, fallback `camera_blend`; end state `ps_canal_head_bank`, equipped [0, 18].
- **Music:** `ch04_water_release`.
- **Fail:** None.
- **Dialogue triggers:** t=18.0 s → `ch04.b08.taemon.001`; t=40.0 s → `ch04.b08.villager.002`; t=62.0 s → `ch04.b08.otane.003`.

### ch04.b09 棚田と水分社 / The Terraces and the Water Shrine

**Type:** `explore_optional` · **Place:** `pl_tanada` · **Target:** 240 s (4.0 min) · **Checkpoint:** yes · **Optional** · **Requires:** `ch04.b08`

An optional climb up 14 dry-stone terraces to the small 水分社. Challenge (poi_minakuchi_order): the terrace inlets (水口) must be opened top-down, one by one, so that each terrace fills before the next. Doing it out of order sends the water down the path, and a simple reset lever at the spring restarts the puzzle. Solving it reveals scroll fragment ch04.c01 behind the shrine. Kohagi's chalk mark ch04.c02 is on the field hut. The vista looks up-valley to the burned estate's roofline. There are no markers; sound (the spring and the shrine bell rope) and the zigzag path lead the player up.

- Volume `vol_tanada`; POIs `poi_mikumari_sha` (lore), `poi_tanada_vista` (vista), `poi_minakuchi_order` (challenge), `poi_shrine_keeper` (npc), `poi_field_hut_cache` (cache); rewards `ch04.c01`, `ch04.c02`, `arrows:6`, `hayago:10`; exit hint after 180 s; no map markers.
- **Music:** `ch04_explore_terraces`.
- **Fail:** None (optional).
- **Dialogue triggers:** `volume_enter:vol_mikumari_sha` → `ch04.b09.villager.001`, `ch04.b09.villager.002`; `volume_enter:vol_tanada_vista` → `ch04.b09.nyaakoto.003`.

### ch04.b10 牛車を水車小屋へ / Escort the ox-cart to the mill

**Type:** `production_task / escort` · **Place:** `pl_shimomura` · **Target:** 240 s (4.0 min) · **Checkpoint:** yes · **Requires:** `ch04.b08`

A two-wheeled, ox-drawn freight cart (牛車, read うしぐるま) carries six paddle boards and a new axle about 235 m from the headman's yard, along the canal bank road, to the mill (about 215 s at the ox's pace). The ox walks at 110 cm/s and cannot be hurried. The cart has 600 HP. A drone's seizure net on the ox stops the cart until the player cuts the net (1.0 s interact). On the player's signal the two carpenters crouch behind the cart. The sun-shower (狐の嫁入り) starts at the halfway point and runs until ch04.b12 reaches 50%.

- Escort `ox_cart_01`, `carpenter_genroku`, `carpenter_kichiji` along `spl_mill_road` at 110 cm/s; waits if the player is over 1500 cm away; NPC health 250; revive within 6 s; hide on signal.
- W1 on `volume_enter:vol_escort_mid`: `enforcer_rifle` ×3 @ `sp_paddy_bank_east`
- W2 on `progress_at:0.75`: `drone` ×2 @ `sp_canal_air`, `blade_retainer` ×1 @ `sp_mill_road`
- Weather: `sun_shower_on` at progress 0.5.
- **Music:** `ch04_escort_sunshower`.
- **Fail:** A carpenter downed and not revived within 6 s, or the cart reduced to 0 HP → checkpoint. player_died → checkpoint.
- **Dialogue triggers:** `beat_start` → `ch04.b10.genroku.001`, `ch04.b10.genroku.002`; `volume_enter:vol_escort_mid` → `ch04.b10.enforcer.003`; `player_signal` → `ch04.b10.nyaakoto.004`; `progress_at:0.5` → `ch04.b10.otane.005`, `ch04.b10.genroku.006`.

### ch04.b11 水車を直せ / Repair the waterwheel

**Type:** `production_task / manufacture` · **Place:** `pl_suisha_goya` · **Target:** 180 s (3.0 min) · **Checkpoint:** yes · **Site:** 1

A quiet workshop beat in the rain with no enemies. The player seats 6 paddle boards (羽根板) on the rim and drives 2 wedges (楔) into each with a carpenter's 玄翁 mallet, in time with Genroku's calls (700 ms beat). A mistimed strike just repeats that strike; the beat is pass/fail with no quality grade. The axle (心棒) is seated with a co-op heave on 「せえの」. Releasing the brake (歯止め) completes the beat: the undershot wheel turns, the bucket rims pour into the flume 3.4 m up, and the upper paddies begin to fill (site 1 restored). The League paints the mon on the hub.

- Recipe `waterwheel_repair` at `st_wheel_rim`, `st_axle_seat`, `st_wheel_brake`: assemble ×6; hammer_rhythm ×12 (700 ±150 ms); assemble ×1 (900 ±200 ms); inspect ×1 → output waterwheel ×1.
- **Registry:** 水車 1基 (Waterwheel, 1 wheel).
- **Music:** `ch04_mill_repair`.
- **Fail:** player_died only (no hazards).
- **Dialogue triggers:** `beat_start` → `ch04.b11.genroku.001`; `progress_at:0.6` → `ch04.b11.genroku.002`; `progress_at:0.9` → `ch04.b11.genroku.003`; `beat_complete` → `ch04.b11.otane.004`, `ch04.b11.nyaakoto.005`.

### ch04.b12 田植えの列を守れ / Guard the planting line

**Type:** `production_task / defend` · **Place:** `pl_shimomura` · **Target:** 240 s (4.0 min) · **Checkpoint:** yes

Eight planters work one moving front across a row of six newly flooded paddies (about 1 反 each), stepping backwards as they plant. The front advances 12 m over 150 s. Drones lock a planter for 800 ms (a cyan ring on the water around the planter), then drop a net. A netted planter is hauled up by a tether after 12 s unless the player cuts the net or shoots the drone. The player's speed in the paddy mud is ×0.6 with no sprint; the dikes are firm. Four enforcers shoot from the far dike 40 m away. The beat pushes the coil matchlock and the yumi against air targets, with the kusarigama pulling low drones down. The work song continues whenever no net is active.

- Defend 8 downable planters (`planter_01`–`08`) for 150 s; netted planters are hauled away after 12 s; fail at 3 lost; free with a 1.0 s net-cut.
- W1 on `start`: `drone` ×3 @ `sp_paddy_air_e`
- W2 on `after_s:40`: `drone` ×3 @ `sp_paddy_air_n`, `enforcer_rifle` ×2 @ `sp_far_dike`
- W3 on `after_s:85`: `drone` ×3 @ `sp_paddy_air_e`, `enforcer_rifle` ×2 @ `sp_far_dike`
- W4 on `after_s:120`: `drone` ×3 @ `sp_paddy_air_n`
- Weather: `sun_shower_off` at progress 0.5.
- **Music:** `ch04_planting_defend`.
- **Fail:** Three planters hauled away → checkpoint. player_died → checkpoint.
- **Dialogue triggers:** `beat_start` → `ch04.b12.planter.001`, `ch04.b12.planter.002`; `progress_at:0.05` → `ch04.b12.otane.003`; `pattern:net_lock` → `ch04.b12.drone.004`; `npc_downed:planter_*` → `ch04.b12.planter.005`; `progress_at:0.5` → `ch04.b12.villager.006`; `beat_complete` → `ch04.b12.otane.007`.

### ch04.b13 生産改帳を開く / Open the Production Registry

**Type:** `dialogue / blocking` · **Place:** `pl_shimomura` · **Target:** 60 s (1.0 min) · **Checkpoint:** no

Oyuki sits on a straw mat on the dike at a portable writing box (硯箱 and 矢立), with the registry on her knee. Its cover carries the vermillion SORA seal. She copies the earlier chapters' tallies onto the first page, then writes today's entries in brush. Lines 001–003 are blocking (about 14 s, under the 20 s cap) while the registry UI opens for the first time. Taemon's skeptic line and Oyuki's answer play ambient as control returns. No XOR is issued yet: the three-party inspection and the split tallies wait for ch05.b12.

- Mode `blocking`, camera `soft_lookat`, interrupt `queue`.
- **Music:** `ch04_registry`.
- **Fail:** None.
- **Dialogue triggers:** `beat_start` (blocking) → `ch04.b13.oyuki.001`, `ch04.b13.oyuki.002`, `ch04.b13.oyuki.003`, `ch04.b13.taemon.004`, `ch04.b13.oyuki.005`.

### ch04.b14 麦を三つの集落へ / Deliver barley to three hamlets

**Type:** `horseback_ride / cargo` · **Place:** `pl_shimomura` · **Target:** 300 s (5.0 min) · **Checkpoint:** yes

Nyaakoto rides Kurimaru, the only mount with a war saddle and abumi, and leads Bunta, the village pack mare, on a 3 m lead rope. Bunta carries 30 sheaves slung either side of her 荷鞍 in 振り分け bundles. The loop of about 900 m runs gogura → upper hamlet → middle hamlet → lower hamlet → gogura. Gaits are limited to walk and trot while Bunta is laden. A toll post (a meter kiosk with 2 enforcers and a drone) sits on the direct bank road between the upper and middle hamlets. The player can fight through it from the saddle (katana to the right, yumi to the left) or take the parallel ring road to the west, adding about 80 m. At the upper hamlet Kurimaru stops at the barley stook until she is allowed a mouthful (the light moment). Deviation from the bible §12.4 excerpt: see §6.4 of this document.

- Horse `kurimaru`, mode `cargo`, route `spl_aze_loop`, gaits walk/trot, weapons [0, 18] (katana right side, yumi left arc −170° to +15°).
- Fear: spook radius 900 cm, recover 2.5 s; auto-steer `setting`; on horse down `dismount_continue`.
- Cargo: `barley_sheaf` ×30 on `pack_horse`, 10 per drop-off at `hamlet_kami`, `hamlet_naka`, `hamlet_shimo`; unload hold 3.0 s.
- W1 on `volume_enter:vol_toll_post`: `enforcer_rifle` ×2 @ `sp_toll_post`, `drone` ×1 @ `sp_toll_air`
- W2 on `item_delivered:hamlet_naka`: `drone` ×2 @ `sp_canal_air`
- **Registry:** 麦 30束 (Barley, 30 sheaves).
- **Music:** `ch04_harvest_ride`.
- **Fail:** None beyond player_died → checkpoint. If Kurimaru is spooked or netted the rider dismounts and continues on foot (dismount_continue); the rider whistles and she returns in 3 s.
- **Dialogue triggers:** `beat_start` → `ch04.b14.otane.001`; `item_delivered:hamlet_kami` → `ch04.b14.villager.002`; `idle_s:4` → `ch04.b14.otane.003`, `ch04.b14.nyaakoto.004`; `item_delivered:hamlet_naka` → `ch04.b14.villager.005`; `item_delivered:hamlet_shimo` → `ch04.b14.villager.006`.

### ch04.b15 秤、現る / The Scales Arrive

**Type:** `cinematic` · **Place:** `pl_gogura` · **Target:** 90 s (1.5 min) · **Checkpoint:** yes

Late-afternoon haze thickens over the river. Frogs go silent. Hakari, an 8 m balance-beam quadruped, wades out of the haze with its two seizure hoppers swinging. It plants a foreleg beside the granary, and a cyan ledger sigil stamps onto the 郷蔵 door. Its hoppers scoop the stacked sheaves from the distribution square. Margina's proclamation is heard over the translation collar. Villagers pull back. Nyaakoto swings up onto Kurimaru, and the title strip 査定機「秤」 appears.

- Sequence `/Game/Campaign/Ch04/Cinematics/LS_Ch04_B15_HakariSeizure`, 90 s, skippable, fallback `camera_blend`; end state `ps_boss_ring_ne_mounted`, equipped [0, 18].
- **Music:** `ch04_hakari_reveal`.
- **Fail:** None.
- **Dialogue triggers:** t=22.0 s → `ch04.b15.margina.001`; t=27.5 s → `ch04.b15.margina.002`; t=34.0 s → `ch04.b15.margina.003`; t=48.0 s → `ch04.b15.otane.004`; t=78.0 s → `ch04.b15.nyaakoto.005`.

### ch04.b16 査定機「秤」を倒せ / Bring down the Assessor Engine

**Type:** `boss` · **Place:** `pl_shimomura` · **Target:** 480 s (8.0 min) · **Checkpoint:** yes (+ each phase)

See §5 of this document for the full pattern tables. P1 (100–55%) is mounted: the player circles counter-clockwise on the 600 m ring road so that Hakari stays on the bow (left) side, and shoots the four weigh-coils while each leg is planted. P2 (55–0%) is on foot at the mill: Hakari kneels to 'assess' the waterwheel, and the ledger drum under its belly is exposed. Interrupting each assessment protects the mill; three completed assessments seal the mill and fail the phase.

- Boss `boss_hakari`; arena `vol_paddies_boss` (locked); defeat `destroy_weakpoints`; checkpoint each phase; telegraph min windup 800 ms (Normal).
- Phases: P1 100–55% `hakari_mounted` (Kurimaru on `spl_boss_ring`, adds `drone_release`); P2 55–0% `hakari_mill` (arena mod `dismount`, adds `drone_pair`).
- Weak points: 4 weigh-coils × 450 HP (P1) and ledger drum 2200 HP (P2) of a 4000 HP pool. Arrow pickups at `pk_arrows_se` and `pk_arrows_nw` (6 arrows, respawn 45 s).
- **Music:** `ch04_boss_hakari`.
- **Fail:** player_died → phase checkpoint. Third mill seal in P2 → phase checkpoint. Kurimaru is never killed: hits on her throw the rider (15 damage) and she returns on a whistle within 3 s.
- **Dialogue triggers:** `beat_start` → `ch04.b16.margina.001`, `ch04.b16.otane.006`; `pattern:step_plant` → `ch04.b16.kohagi.007`; `weakpoint_destroyed:coil_*` → `ch04.b16.margina.008`; `boss_phase:2` → `ch04.b16.margina.009`, `ch04.b16.otane.010`; `boss_event:mill_seal` → `ch04.b16.margina.013`; `player_died` → `ch04.b16.otane.014`; `beat_complete` → `ch04.b16.margina.015`.

### ch04.b17 麦を郷蔵へ戻せ / Return the barley to the granary

**Type:** `production_task / carry` · **Place:** `pl_gogura` · **Target:** 150 s (2.5 min) · **Checkpoint:** yes · **Site:** 2

In its outro Hakari lurches 120 m east along the north road, still trying to carry off its hoppers, and falls face-first into the paddy at the block's north-east corner. The hoppers burst, and the sheaves spill onto the north road about 50 m from the granary door. The player carries 3 back-loads (15 sheaves each) to the 郷蔵. Villagers carry the rest in a relay, as crowd animation. Each load is tagged with a wooden 札 naming the field it came from. A child chalks the SORA mon back over the scraped door. On completion site 2 is restored and the registry records 120 sheaves returned. No combat.

- Carry `barley_load` ×3 from `pk_hopper_spill_01`, `pk_hopper_spill_02`, `pk_hopper_spill_03` to `dp_gogura_door`; loadout while carrying `katana_one_hand`, speed ×0.8, no sprint.
- **Registry:** 麦（返還） 120束 (Barley returned to growers, 120 sheaves).
- **Music:** `ch04_return_harvest`.
- **Fail:** None (no hazards).
- **Dialogue triggers:** `beat_start` → `ch04.b17.oyuki.001`; `item_delivered:barley_load` → `ch04.b17.villager.002`; `progress_at:1.0` → `ch04.b17.oyuki.003`; `beat_complete` → `ch04.b17.taemon.004`.

### ch04.b18 蛍 / Fireflies

**Type:** `cinematic` · **Place:** `pl_shimomura` · **Target:** 120 s (2.0 min) · **Checkpoint:** no

Blue-hour dusk over the planted paddies. Hakari's wreck lies half-sunk in the paddy, cold. Fireflies rise from the canal. Otane ties a tenugui with the painted mon and joins the League. Oyuki notes it. The camera finds the east ridge: a black-bay stallion and an orange rider against the last light. Toranosuke turns Arashi away without a word. Cut to the chapter registry page: 用水 12枚, 水車 1基, 麦 30束, 麦（返還）120束.

- Sequence `/Game/Campaign/Ch04/Cinematics/LS_Ch04_B18_Fireflies`, 120 s, skippable, fallback `camera_blend`; end state `ps_chapter_end`, equipped [0, 18].
- **Music:** `ch04_dusk_fireflies`.
- **Fail:** None.
- **Dialogue triggers:** t=20.0 s → `ch04.b18.otane.001`; t=26.0 s → `ch04.b18.oyuki.002`; t=44.0 s → `ch04.b18.taemon.003`; t=78.0 s → `ch04.b18.kohagi.004`; t=86.0 s → `ch04.b18.nyaakoto.005`.

---

## 5. Boss: 査定機「秤」 (`boss_hakari`)

**Bible §8 anchor.** A colossal walker fought mounted and then on foot, in phases P1 (100–55%, mounted) and P2 (55–0%, on foot).

- Signature attacks: the seizure net (800 ms, cyan lock), the low sweep beam (1,100 ms) and drones.
- Counterplay: circle counter-clockwise for the mounted yumi, shoot the 4 weigh-coils as legs plant, and in P2 cut the exposed ledger drum.
- Voice telegraph: 「査定中……評価額、零。」
- Fate: collapses into a paddy; Margina ejects.

The tables below turn that anchor into numbers for L3.

**Silhouette.** Hakari is an 8 m quadruped built as a walking **balance beam**. A horizontal beam body carries two hanging seizure hoppers, one on each side. Four jointed legs each have a knee **weigh-coil** (秤環) of brushed titanium ringed with cyan numerals. A black-glass cockpit ocular sits at the front with Margina visible inside, lit by her ocular. The **ledger drum** (帳簿胴), a rotating cylinder of glass tally rings, hangs under the belly.

- Footprint 10 × 7 m; stride 4 m; walk speed 1.2 m/s, lurch 2.5 m/s.
- It bears the alien ledger sigil, never the SORA mon.
- It is the large variant of the ch08 `seizure_walker` (4 m) and shares its rig family.

**HP and weak points** (4,000 HP pool, proposal):

| Weak point | Phase | HP | Share of pool | Exposed when | Damage multipliers |
|---|---|---|---|---|---|
| `coil_fl`, `coil_fr`, `coil_rl`, `coil_rr` | P1 | 450 each | 11.25% each; the four together take the pool from 100% to 55% | The leg is planted (3.0 s window after each step; all four for 3.5 s after `plant_stomp`) | Arrow ×2.0 (104 per hit, so about 5 arrows per coil); katana cannot reach (knee height 3.5 m) |
| `ledger_drum` | P2 | 2,200 | 55% | During `assessment_kneel` (6.0 s; 4.5 s below 25%) | Melee ×2.5 (katana 130, yari 122, kusarigama 100); ranged ×1.5 (coil matchlock 108, arrow 78, grenade 99) |

**Arrow economy in P1.**

- About 20 arrow hits are needed against a 12-arrow quiver.
- Two ride-through arrow pickups on the ring (6 arrows each, respawning every 45 s) and a full quiver at the phase checkpoint cover this with margin.
- A lap at canter (5.5 m/s) takes about 110 s. P1 is expected to take about 2.5 laps (about 270 s).

**Mill seals in P2.**

- Each kneel fills a cyan assessment ring over the waterwheel.
- Dealing 250 damage to the drum during the kneel (about 2 katana cuts) interrupts it and staggers Hakari for 2.0 s, which is the best damage window.
- A completed assessment stamps a seal on the mill, and Margina calls 「一件、差押え完了。」 A three-pip counter shows the seals.
- The third seal fails the phase back to its checkpoint.
- About 4 kneel cycles are expected (about 210 s).

**Horse rules in P1.**

- Kurimaru cannot be killed. A beam or net hit on her throws the rider, who takes 15 damage, and she returns on a whistle within 3 s.
- She spooks within 900 cm of a beam or stomp (2.0 s recovery).
- Gallop (襲歩) is allowed only in this fight and costs horse stamina (§6.5).
- No firearms from the saddle (bible §11).

**Telegraph rules.**

- Cyan marks a locked aim or beam; amber marks an area attack. Amber decals use an animated edge pulse so they stay distinct from golden-hour light.
- Every attack's windup on Normal is at least 800 ms (`telegraph.min_windup_ms`). Easy multiplies windups by 1.3, Hard by 0.85.
- Every attack has a captioned voice telegraph. Kohagi calls the first coil glow.

**P1 mounted (100–55%)**: pattern table `hakari_mounted`

| Attack | Telegraph | Windup ms | Active ms | Recovery ms | Cooldown s | Effect | Counterplay | Voice telegraph |
|---|---|---|---|---|---|---|---|---|
| `step_plant` | none | — | 3000 | — | 4.0 | one leg plants; its weigh-coil glows and is damageable for 3.0 s | shoot the glowing coil (left arc) | 脚の環が光った。踏んだ時だけ。 (`ch04.b16.kohagi.007`) |
| `seizure_net` | cyan | 800 | 400 | 1400 | 9.0 | net projectile 3500 cm/s, 250 cm radius; roots Kurimaru 2.0 s (rider can still shoot) | change gait or direction during the lock tone | 差押え網、展開。 (`ch04.b16.margina.002`) |
| `sweep_beam` | cyan | 1100 | 900 | 1800 | 14.0 | 180-degree sweep at 80 cm height, reach 3000 cm, 45 damage and a spook | gallop out beyond 3000 cm (襲歩, horse stamina) | 査定中……評価額、零。 (`ch04.b16.margina.003`) |
| `plant_stomp` | amber | 1000 | 300 | 3500 | 20.0 | 600 cm ring, 40 damage, rider thrown if inside; then all four coils glow for the 3.5 s recovery | leave the ring, then punish the long recovery | 計量。 (`ch04.b16.margina.004`) |
| `drone_release` | none | 1200 | — | 800 | 40.0 | 2 drones, max 3 alive; a marking drone makes the next seizure_net track the rider through its 800 ms windup | shoot or katana-cut the marking drone (its cyan eye) to clear the mark | 目録、放出。 (`ch04.b16.margina.005`) |

**P2 on foot (55–0%)**: pattern table `hakari_mill`

| Attack | Telegraph | Windup ms | Active ms | Recovery ms | Cooldown s | Effect | Counterplay | Voice telegraph |
|---|---|---|---|---|---|---|---|---|
| `assessment_kneel` | cyan | 1500 | 6000 | 1000 | 22.0 | kneels at the mill, exposing the ledger drum (x2.5 melee, x1.5 ranged); an assessment ring fills over 6 s | deal 250 damage during the kneel to interrupt (2.0 s stagger); otherwise the mill takes 1 seal (3 = fail) | 担保価値を、算定中。 (`ch04.b16.margina.011`) |
| `claw_sweep` | amber | 1000 | 400 | 1500 | 7.0 | 240-degree front arc, 700 cm, 50 damage and knockback; cannot be parried | step out of the arc or guard (60% reduction); flank during recovery | 減価償却。 (`ch04.b16.margina.012`) |
| `seizure_net` | cyan | 800 | 400 | 1400 | 10.0 | roots the player 1.5 s | sidestep during the lock tone | 差押え網、展開。 (`ch04.b16.margina.002`) |
| `sweep_beam` | cyan | 1100 | 900 | 1800 | 16.0 | head turret sweep at 80 cm, reach 1800 cm on foot | crouch behind the mill footing or millrace wall (stone blocks the beam) or leave range | 査定中……評価額、零。 (`ch04.b16.margina.003`) |

**Revaluation (P2 below 25% HP).** The kneel window shortens to 4.5 s, the sweep-beam windup to 950 ms and the claw-sweep windup to 850 ms. All stay at or above the 800 ms Normal floor. The bark `ch04.b16.margina.003` repeats as the audio cue.

**Adds.** P1: `drone_release`, 2 drones every 40 s with at most 3 alive. P2: `drone_pair`, 2 drones at phase start, and 2 more 30 s after each pair is cleared.

**Fate.** When the drum breaks, the outro (`LS_Ch04_B16_HakariCollapse`, about 12 s, skippable) plays. Hakari lurches east with its hoppers and falls into the paddy. Its cockpit blows its canopy, and Margina rides a drone tether into the haze: 「……損切りいたします。」 Nobody is killed on screen, which is consistent with katsujinken.

---

## 6. New mechanics in this chapter (proposed parameters)

The bible §10 lists chapter 4's new mechanics as: crank, hold, 早合 reload, kusarigama bind, mounted cargo and mounted boss. The parameters below are proposals for L2 (feel) and L1 (data). Catalog weapon stats are unchanged.

### 6.1 早合 reload (`hayago_reload`, unlocked at b03)

- **Weapon 5 as catalogued:** magazine 5, reload 2.3 s, cooldown 0.95 s, 72 damage, hitscan, range 10,000 cm. In the fiction, Tetsugorō's coil breech takes a strip of five 早合 paper cartridges from the 胴乱 belt pouch. It fires in rain because the coil replaces the slow-match (bible §4.4), but it still burns black powder, so each shot smokes.
- **Active reload:** the 2.3 s reload animation opens the breech, presses the strip in and locks the lever. At 1.2 s a click sounds and a brush-stroke tick appears on the reload arc. Pressing reload again within ±120 ms of the click locks early, and the reload ends at 1.6 s.
- A missed press only means the normal 2.3 s reload. There is no jam and no penalty, in keeping with the bible's pass/fail philosophy.
- The gun is **cheek-stocked** (頬付け). The aim animation holds the stock to the cheek, never to the shoulder (b03 line 004).
- It cannot be used on horseback (bible §11). Mounting stows it.

### 6.2 Kusarigama bind (proposed mechanic flag `kusarigama_bind`)

The bible §10 names this mechanic but the §12.1 flag list lacks it. L1 should add the flag or treat the bind as intrinsic to weapon 2.

- **Primary:** the sickle, per catalog weapon 2 (40 damage, 0.48 s cooldown, 250 cm range).
- **Alternate: throw the 分銅.** Windup 300 ms, reach 550 cm, chain speed 2,400 cm/s, cooldown 5.0 s. Effects by target:

| Target | Effect of a bind | Follow-up |
|---|---|---|
| `blade_retainer` | Its blade is snared for 1.6 s and it cannot attack | The next sickle cut deals ×1.5 |
| `shield_enforcer` | The shield edge is pulled open for 1.2 s | A flank or frontal hit lands |
| `enforcer_rifle` | The rifle is snared for 1.2 s and cannot fire | |
| `drone` at 6 m or lower | Pulled down and stunned for 2.0 s | Can be cut |
| `bound_conscript` | Its staff is snared for 1.2 s | Pairs with 峰打ち |
| Boss | No effect | |

- Taught at b04 (the first blade retainer, Otane's line 002) and at b07 (shields, line 003). It is useful against low drones in b12.
- Handling note: which hand holds the sickle and which swings the chain differs between schools. The first-person animation must be reviewed by a practitioner (§8.3).

### 6.3 Crank and hold (`crank`, unlocked at b06)

- **Crank:** exactly as in the bible §12.4 excerpt: 12 turns, band 0.4–1.2 turns/s, decay 0.05/s, 6 stamina per turn, interruptible. Added here: `coop_npc: otane`, who cranks at 0.2 turns/s while the player fights.
  - HUD: a brush-stroke arc with the band shaded. Going above the band makes the rope creak and then slip, which drops 0.5 turn. Going below the band lets the load sink back at the decay rate.
  - The debt seal breaks at 25% progress (`debt_seal_broken` event), which also darkens the collars at the dam.
- **Hold:** `vol_weir_platform` (r 12 m), 90 s, `contest: pause`. Progress pauses while any enemy stands inside the volume.
  - The diegetic gauge is the water line on a carved stone depth marker (水位石) beside the gate. The HUD mirrors it as a thin vertical bar.

### 6.4 Mounted cargo with a lead horse (b14)

- **Proposal.** Nyaakoto rides **Kurimaru** (full kura, abumi, tazuna) and leads **Bunta** on a 3 m lead rope (差縄). Bunta is a bay (鹿毛) village pack mare under a 荷鞍 with 30 barley sheaves slung either side in 振り分け bundles.
- **While Bunta is laden:**
  - Gaits are limited to walk (170 cm/s) and trot (350 cm/s).
  - Bunta spooks within 900 cm of cyan light (2.5 s recovery), and the lead rope pulls Kurimaru's head, costing 1 s of steering.
  - Drop-offs are a 3.0 s hold at each hamlet's 稲架 stand, 10 sheaves each.
  - The katana cuts to the right and the yumi shoots in the left arc, as usual.
- **Deviation from bible §12.4.** The excerpt sets `"horse": "pack_horse"` for ch04.b14. This design sets `horse: kurimaru` and `cargo.carrier: pack_horse`, because only a war saddle with broad abumi lets the rider stand for mounted archery (bible §4.2). A rider perched on a pack load (the later 乗掛 style) should not shoot a yumi. If L1 prefers the excerpt, set `horse: pack_horse`, drop `carrier`, and restrict `weapons` to `[0]`.

### 6.5 Horse gaits and stamina (all rides; mounted boss)

| Gait | JA | Speed (cm/s) | Stamina | Where allowed |
|---|---|---|---|---|
| Walk | 常歩 | 170 | Regenerates +8/s | Everywhere a horse can go; also the maximum in paddy mud |
| Trot | 速歩 | 350 | Regenerates +8/s | Roads; the maximum while leading a laden pack horse |
| Canter | 駈歩 | 550 | Neutral | Roads |
| Gallop | 襲歩 | 800 | −12/s from 100; locked out below 20 until back to 50 | Roads; only b16 in this chapter (the bible's "gallop out" of the sweep beam) |

- **Paddy mud:** horse speed ×0.45, walk only. Horses never enter the 畦 ridges; blocking volumes enforce this.
- **The lateral amble (側対歩)** at travel speed is used in b02 and b14 walking stretches, pending the equine animator's review (bible §4.5).
- **Kurimaru is never killed** in any beat (§5).

### 6.6 Terrain rules introduced here

- **Tall barley (`vol_barley_tall`).** Premodern barley at 110–130 cm (to verify).
  - AI sight inside barley is capped at 500 cm.
  - A crouched player is invisible to AI beyond 300 cm unless moving faster than walk.
  - Standing aliens' heads and shoulders show above the crop.
  - Any movement makes the heads sway with a visible 2 m ripple. This is the tell for both sides.
  - Barley stops no projectiles.
- **Paddy mud (`vol_paddy_*`).**
  - On foot: speed ×0.6 and no sprint. Every step splashes, a loud noise class (same as a puddle).
  - Planted clumps are cosmetic, never collision.
  - Dikes are firm ground and hard cover when crouched.
- **畦 ridges.** Walkable on foot (walk speed only); impassable to horses.

### 6.7 Schema additions this chapter asks L1 to ratify

| Kind | Addition | Why |
|---|---|---|
| Place id | `pl_shoya_yashiki` 庄屋屋敷 (しょうややしき) | Bible §13 names the headman's house but §14 has no id |
| Speaker ids (generic, shareable across chapters) | `enforcer`, `drone`, `conscript`, `villager`, `planter` | Barks and crowd lines need captioned speakers (§18) |
| Speaker ids (minor) | `yosaku` 与作, `carpenter` (大工 源六 Genroku) | Named minor characters |
| Dialogue events | `pattern:<attack>` (already used in §12.4), `npc_freed:<id>`, `player_signal`, `weakpoint_destroyed:<id>`, `boss_event:<id>` | Stealth, escort and boss barks |
| Line chaining | Lines listed together in one `lines[]` play queued in order. "after <id>" in §7 means that queue order | Avoids a new event type |
| Optional params | `horseback_ride.companions`, `.scout_marks`, `.waves` (enemies on rides; ch02.b08 needs the same), `cargo.carrier / per_dropoff / unload_hold_s`; `combat_wave.sight_occluders`; `stealth_zone.shade_volumes / approach`; `production_task.events`; `defend.fail_after_targets_lost`, `targets[].haul_after_s`, object-form `repair_interact`; `weather_events`; `boss.weakpoints / ammo_pickups / phases[].mount`; `fail` as a list | Parameters used in §4 |
| Mechanic flag | `kusarigama_bind` | §6.2 |
| Collectible ids | `ch04.c01`–`ch04.c06` (pattern `chNN.cMM`) | §12.1 defines only `chNN.bMM` for beats |
| Collectible mix | ch04: scroll 1, league mark 1, seizure notice 1, heirloom 1, registry page 2 | L1 reconciles the campaign totals of 8/12/10/8/10 across chapters |

---

## 7. Dialogue script (bilingual)

**Conventions** (bible §18):

- Line ids are `chNN.bMM.<speaker>.<nnn>`, numbered in order within each beat. `ch04.b06.otane.001`, `ch04.b06.taemon.002` and `ch04.b16.margina.003` keep the ids fixed by the bible §12.4 excerpt.
- EN subtitles fit 2 lines of 42 characters and never exceed 17 cps. The highest in this chapter is 15.0 cps.
- JA lines are at most 32 characters, which fits two caption lines of 16; the native reviewer confirms the limit.
- Durations are estimates from mora count and register pace, with a minimum of 1.2 s. They are for timing the VO recording, which has not happened yet.
- Readings are given for rare words.
- "after <id>" means queued after that line in the same `lines[]` group.
- "(repeatable)" marks barks that may replay. Every other line plays once.
- Cinematic lines are subtitles on the sequence timeline (`t=` in seconds). Blocking lines lock control for at most 20 s per beat.

**Registers.**

- Nyaakoto: restrained samurai speech with few words.
- Taemon, Otane, Genroku and the villagers: Yamato and Kamigata speech, rendered as warm colloquial English with contractions.
- Oyuki: precise business keigo that leads with numbers.
- Kohagi: counts and directions.
- Aliens: hyper-polite corporate keigo with financial terms, and **no contractions** in English (bible §6.3, §18).

**Totals.** 115 voiced lines (bible §10 budget: 115) across 14 speakers, about 7.6 min of speech.

### 7.1 Speakers

| Token | Speaker id | JA | EN | Register | Lines | Status |
|---|---|---|---|---|---|---|
| `nyaakoto` | `samurai` | ニャーコト | Nyaakoto | `samurai_restrained` | 10 | existing |
| `taemon` | `farmer` | 田右衛門 | Taemon | `yamato_elder` | 11 | existing id (bible §6.2) |
| `otane` | `farmer_young` | お種 | Otane | `kamigata_bright` | 28 | bible §6.2 |
| `oyuki` | `leader` | お雪 | Oyuki | `business_keigo` | 9 | bible §6.1 |
| `kohagi` | `scout` | 小萩 | Kohagi | `terse` | 5 | existing |
| `tetsugoro` | `gunsmith` | 鉄五郎 | Tetsugorō | `blunt_artisan` | 5 | bible §6.2 |
| `margina` | `boss_margina` | マルジナ | Margina | `alien_corporate_keigo` | 14 | bible §6.3 |
| `enforcer` | `enforcer` | 執行兵 | Enforcer | `alien_corporate_keigo` | 7 | PROPOSED generic |
| `drone` | `drone` | 目録 | Inventory drone | `alien_machine` | 3 | PROPOSED generic |
| `conscript` | `conscript` | 債縛衆 | Debt-Bound | `yamato_rural_distressed` | 5 | PROPOSED generic |
| `yosaku` | `yosaku` | 与作 | Yosaku | `yamato_rural_distressed` | 1 | PROPOSED minor (Otane's brother) |
| `villager` | `villager` | 村人 | Villager | `yamato_rural` | 8 | PROPOSED generic |
| `planter` | `planter` | 早乙女 | Planter | `work_song` | 3 | PROPOSED generic |
| `genroku` | `carpenter` | 大工 源六 | Genroku the carpenter | `kamigata_artisan` | 6 | PROPOSED minor |

### 7.2 Lines by beat

#### ch04.b01 庄屋屋敷にて / At the Headman's House

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Readings / notes |
|---|---|---|---|---|---|---|
| `ch04.b01.taemon.001` | cinematic t=8.0 | 田右衛門 / Taemon | 水車を奪われた。稲はまだ芽も出ていないのに。 | They took the pumps before the rice had even sprouted. | 5.0 | Catalog canon ch04 line 1 (verbatim). 水車(すいしゃ) |
| `ch04.b01.taemon.002` | cinematic t=14.5 | 田右衛門 / Taemon | 溜池には封を貼られてな。水は升で量り売りや。 | They sealed the reservoir. Now water is sold by the measure. | 5.5 | 溜池(ためいけ) 升(ます) 量り売り(はかりうり) |
| `ch04.b01.oyuki.003` | cinematic t=21.0 | お雪 / Oyuki | 青田買い、でございます。植える前の稲を「買う」のです。 | It is aotagai. They 'buy' the rice before it is planted. | 5.0 | 青田買い(あおたがい): period term, bible §2.1 |
| `ch04.b01.oyuki.004` | cinematic t=27.5 | お雪 / Oyuki | 代金は「信用」、つまり借りです。利息は実りより速く増えます。 | Paid in 'Credit', which is to say debt. The interest outgrows any harvest. | 5.5 | 信用(しんよう) 利息(りそく) |
| `ch04.b01.otane.005` | cinematic t=36.0 | お種 / Otane | 田植えは今しかあらへん。水が来な、苗は十日で枯れる。 | It's planting now or never. No water, and the seedlings die in ten days. | 5.0 | 苗(なえ). 「来な」= 来なければ (Kamigata) |
| `ch04.b01.nyaakoto.006` | cinematic t=43.0 | ニャーコト / Nyaakoto | 堰は、どこに。 | Where is the weir? | 1.5 | 堰(せき) |
| `ch04.b01.taemon.007` | cinematic t=45.5 | 田右衛門 / Taemon | 大溜池の、一の堰や。爺さまの代から、皆で分けてきた水や。 | The First Weir, up at the Great Reservoir. We've shared it since Grandad's day. | 7.0 | 大溜池(おおためいけ) 一の堰(いちのせき) 爺さま(じいさま) |
| `ch04.b01.otane.008` | cinematic t=53.0 | お種 / Otane | 案内したる。馬で通れる土手は、限られとるで。 | I'll show you. Only some banks will take a horse. | 4.5 | 土手(どて) |

#### ch04.b02 お種と土手道を見回る / Scout the bank roads with Otane

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Readings / notes |
|---|---|---|---|---|---|---|
| `ch04.b02.otane.001` | beat_start | お種 / Otane | 畦は細いで、馬は無理や。土手道だけ通ってな。 | The paddy ridges are too narrow for horses. Keep to the bank roads. | 4.5 | 畦(あぜ) 土手道(どてみち). Diegetic tutorial for route rules |
| `ch04.b02.otane.002` | volume_enter:vol_meter_post_02 | お種 / Otane | あの杭、見える？　水を量る杭や。一升ごとに戸口の数字が増える。 | See that post? It meters the water. Every measure adds to the number on our doors. | 6.0 | 杭(くい) 一升(いっしょう) |
| `ch04.b02.otane.003` | volume_enter:vol_mugi_overlook | お種 / Otane | 麦はもう刈り頃や。刈ったそばから「徴収」や。 | The barley's ready to cut. They 'collect' it as fast as we cut it. | 4.5 | 刈り頃(かりごろ) 徴収(ちょうしゅう) |
| `ch04.b02.nyaakoto.004` | after ch04.b02.otane.003 | ニャーコト / Nyaakoto | 見張りは、いくつだ。 | How many guards? | 2.5 |  |
| `ch04.b02.otane.005` | after ch04.b02.nyaakoto.004 | お種 / Otane | 麦畑に八つか九つ。空に「目録」が二つ。 | Eight or nine in the barley. Two 'Inventories' in the sky. | 4.0 | 目録(もくろく): the drones' local name. Triggers scout_marks |
| `ch04.b02.otane.006` | volume_enter:vol_scout_end | お種 / Otane | 去年の今ごろは、田植え歌がここまで聞こえとった。 | This time last year, you could hear the planting songs from here. | 4.5 | 田植え歌(たうえうた) |

#### ch04.b03 鳥威しと鎖鎌 / The Crow-Scarer and the Kusarigama

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Readings / notes |
|---|---|---|---|---|---|---|
| `ch04.b03.tetsugoro.001` | beat_start | 鉄五郎 / Tetsugorō | 田右衛門の鳥威しだ。筒は生きとった。 | Taemon's crow-scaring gun. The barrel was still sound. | 4.0 | 鳥威し(とりおどし) 筒(つつ) |
| `ch04.b03.tetsugoro.002` | after ch04.b03.tetsugoro.001 | 鉄五郎 / Tetsugorō | 尾栓に、奴らのコイルを噛ませた。 | I fitted one of their coils into the breech. | 3.5 | 尾栓(びせん): matchlock breech plug. Blocking ≤ 8 s: handover of weapon 5 |
| `ch04.b03.tetsugoro.003` | after ch04.b03.tetsugoro.002 | 鉄五郎 / Tetsugorō | 雨で火縄が死ぬんなら、火縄をやめりゃええ。 | If rain kills the match, stop using a match. | 4.0 | Bible §6.5 register sample. 火縄(ひなわ) |
| `ch04.b03.tetsugoro.004` | after ch04.b03.tetsugoro.003 | 鉄五郎 / Tetsugorō | 頬に付けて撃て。肩には当てるな。 | Stock to your cheek. Not your shoulder. | 3.5 | 頬(ほお). Japanese matchlocks are cheek-stocked (頬付け) |
| `ch04.b03.tetsugoro.005` | after ch04.b03.tetsugoro.004 | 鉄五郎 / Tetsugorō | 早合を込めて、カチッと鳴ったら締めろ。 | Load the hayagō. When it clicks, lock it. | 4.0 | 早合(はやごう). Pairs with HUD prompt ui.ch04.b03.hayago |
| `ch04.b03.otane.006` | after ch04.b03.tetsugoro.005 | お種 / Otane | これ、兄やんの鎖鎌。持っとき。うちのは、こっちや。 | This is my brother's kusarigama. Keep it. I've got my own. | 4.5 | 兄やん(あにやん) 鎖鎌(くさりがま). Blocking ≤ 8 s: handover of weapon 2 |
| `ch04.b03.nyaakoto.007` | after ch04.b03.otane.006 | ニャーコト / Nyaakoto | ……お借りする。 | …Then I will borrow it. | 2.0 |  |
| `ch04.b03.otane.008` | after ch04.b03.nyaakoto.007 | お種 / Otane | 借りやない。預けるんや。兄やんを取り返すまで。 | It's not a loan. I'm trusting it to you. Until we get my brother back. | 5.0 | 預ける(あずける): echoes 「刀は民から預かるもの」 (ch01.b12) |

#### ch04.b04 麦畑の徴収隊を退けよ / Drive off the collection patrol

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Readings / notes |
|---|---|---|---|---|---|---|
| `ch04.b04.otane.001` | beat_start | お種 / Otane | 来たで。麦の中や。……向こうも、こっちが見えてへん。 | Here they come, through the barley. …They can't see us either. | 5.0 | Diegetic tutorial: tall barley blocks sight both ways |
| `ch04.b04.otane.002` | progress_at:0.15 | お種 / Otane | 分銅を投げて！　刃ぁ絡めたら、こっちのもんや！ | Throw the weight! Snag the blade and they're ours! | 4.0 | 分銅(ふんどう). Pairs with ui.ch04.b04.bind |
| `ch04.b04.enforcer.003` | alert_state:alert (repeatable) | 執行兵 / Enforcer | 債務者を確認。回収を開始いたします。 | Debtor identified. Commencing collection. | 4.5 | 債務者(さいむしゃ) 回収(かいしゅう). Shared enforcer bark pool |
| `ch04.b04.enforcer.004` | alert_state:search (repeatable) | 執行兵 / Enforcer | 対象を見失いました。当該区画を精査いたします。 | Target lost. Auditing this sector. | 5.5 | 当該(とうがい) 精査(せいさ). Shared bark pool |
| `ch04.b04.enforcer.005` | progress_at:0.8 / squad retreat (repeatable) | 執行兵 / Enforcer | 損失が許容範囲を超過。撤収いたします。 | Losses exceed tolerance. Withdrawing. | 5.0 | 許容(きょよう) 撤収(てっしゅう). Shared bark pool |
| `ch04.b04.drone.006` | alert_state:suspicious [drone] (repeatable) | 目録 / Inventory drone | 差押え対象を記録。 | Seizure target logged. | 2.5 | 差押え(さしおさえ). Plays with the cyan mark |
| `ch04.b04.otane.007` | npc_downed:otane | お種 / Otane | 足、取られた……！　起こして！ | They got my leg…! Get me up! | 3.0 |  |
| `ch04.b04.otane.008` | beat_complete | お種 / Otane | ……麦、踏まれてもうた。まあ、麦は起きる。 | …They trampled the barley. Well—barley stands back up. | 4.0 | Nods to 麦踏み (winter barley-treading) |

#### ch04.b05 堤の見張りを抜けよ / Slip past the dam guards

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Readings / notes |
|---|---|---|---|---|---|---|
| `ch04.b05.kohagi.001` | volume_enter:vol_gorge_foot | 小萩 / Kohagi | 堤の上に四。首輪つき。水の上に目録が一。 | Four on the dam. Collared. One Inventory over the water. | 5.0 | 堤(つつみ) 首輪(くびわ) |
| `ch04.b05.kohagi.002` | after ch04.b05.kohagi.001 | 小萩 / Kohagi | 首輪の者は斬らないで。峰で。 | Don't cut the collared ones. Use the back of the blade. | 4.0 | 峰(みね): 峰打ち reminder |
| `ch04.b05.conscript.003` | idle_s:20 [guard in view] (repeatable) | 債縛衆 / Debt-Bound | ……首輪が熱い。日が高うなると、焼けるようや。 | …The collar's hot. Once the sun's high, it burns. | 4.5 | Ambient guard chatter |
| `ch04.b05.conscript.004` | alert_state:suspicious (repeatable) | 債縛衆 / Debt-Bound | 誰や……？　誰か、おるんか。 | Who's that…? Someone there? | 3.0 |  |
| `ch04.b05.conscript.005` | alert_state:search (repeatable) | 債縛衆 / Debt-Bound | 頼む、出てこんといてくれ。見つけたら、報せなあかんのや。 | Please, stay hidden. If I find you, I have to report it. | 5.0 | 報せ(しらせ). Reluctant watchman |
| `ch04.b05.conscript.006` | alert_state:alert (repeatable) | 債縛衆 / Debt-Bound | すまん！　見つけてもうた！　首輪が勝手に叫ぶんや！ | Sorry! I found you! The collar cries out on its own! | 4.5 |  |
| `ch04.b05.drone.007` | alert_state:suspicious [drone] (repeatable) | 目録 / Inventory drone | 動体を検知。照合中。 | Movement detected. Reconciling. | 3.0 | 照合(しょうごう) |
| `ch04.b05.yosaku.008` | npc_freed:yosaku (fallback: ch04.b06 progress_at:0.3) | 与作 / Yosaku | ……お種の兄の、与作や。恩に着る。 | …I'm Yosaku, Otane's brother. I owe you. | 4.0 | 恩に着る(おんにきる) |
| `ch04.b05.kohagi.009` | beat_complete | 小萩 / Kohagi | 堤、抜けた。巻き上げは、そこ。 | Dam's clear. The winch is there. | 3.5 | 巻き上げ(まきあげ) |

#### ch04.b06 一の堰を開けよ / Open the First Weir

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Readings / notes |
|---|---|---|---|---|---|---|
| `ch04.b06.otane.001` | beat_start | お種 / Otane | 封されてから一度も回ってへん。重いで。速すぎたら綱が切れる。 | Hasn't turned since they sealed it. It's heavy. Too fast and the rope snaps. | 5.5 | 綱(つな). Diegetic tutorial for turn_rate_band. Id fixed by bible §12.4 |
| `ch04.b06.taemon.002` | progress_at:0.5 | 田右衛門 / Taemon | ほんまに水、戻るんか。戻ったかて、また取られるんやないか。 | Will the water really come back? And won't they just take it again? | 6.0 | Id fixed by bible §12.4 |
| `ch04.b06.nyaakoto.003` | progress_at:0.75 | ニャーコト / Nyaakoto | 水を戻す。収穫は育てた者に渡そう。 | We will restore the water. The harvest will go to those who grew it. | 5.0 | Catalog canon ch04 line 2 (verbatim) |
| `ch04.b06.enforcer.004` | progress_at:0.25 (with wave 1) | 執行兵 / Enforcer | 無許可の取水を確認。延滞金が加算されます。 | Unauthorized intake detected. Late fees will be applied. | 5.5 | 取水(しゅすい) 延滞金(えんたいきん) |
| `ch04.b06.conscript.005` | progress_at:0.25 (debt seal breaks) | 債縛衆 / Debt-Bound | 首輪の光が……消えた。 | The collar's light… it's gone out. | 2.5 | Seal break frees the remaining conscripts |
| `ch04.b06.taemon.006` | beat_complete | 田右衛門 / Taemon | ……水の音や。 | …That's the sound of water. | 2.0 |  |

#### ch04.b07 水が満ちるまで堰を守れ / Hold the weir while the water rises

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Readings / notes |
|---|---|---|---|---|---|---|
| `ch04.b07.otane.001` | beat_start | お種 / Otane | 堰板が上がりきるまで、ここを守るで！ | Hold here until the gate boards are all the way up! | 3.5 | 堰板(せきいた) |
| `ch04.b07.enforcer.002` | progress_at:0.33 (wave 2) | 執行兵 / Enforcer | 盾列、前進。担保を保全いたします。 | Shield line, advance. Securing the collateral. | 4.5 | 盾列(たてれつ) 担保(たんぽ) 保全(ほぜん) |
| `ch04.b07.otane.003` | after ch04.b07.enforcer.002 | お種 / Otane | 盾は前だけや！　横から絡めたれ！ | Shields only cover the front! Snag them from the side! | 4.0 | Tutorial: kusarigama bind vs shield_enforcer |
| `ch04.b07.taemon.004` | progress_at:0.5 | 田右衛門 / Taemon | 水位、あと半分や！　踏ん張れ！ | Halfway there! Hold on! | 4.0 | 水位(すいい) |
| `ch04.b07.enforcer.005` | progress_at:0.9 (repeatable) | 執行兵 / Enforcer | 採算が合いません。後退いたします。 | This is no longer profitable. Falling back. | 4.0 | 採算(さいさん). Shared bark pool |
| `ch04.b07.taemon.006` | beat_complete | 田右衛門 / Taemon | 溢れる……！　田に、水が入る！ | It's spilling over…! Water's reaching the fields! | 3.5 | 溢れる(あふれる) |

#### ch04.b08 水が走る / The Water Runs

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Readings / notes |
|---|---|---|---|---|---|---|
| `ch04.b08.taemon.001` | cinematic t=18.0 | 田右衛門 / Taemon | 水はな、借りるもんやない。上から下へ、皆に回るもんや。 | Water isn't something you borrow. It runs downhill, round to everyone. | 6.0 | Bible §6.5 register sample |
| `ch04.b08.villager.002` | cinematic t=40.0 | 村人 / Villager | 水や……！　水が来たで！ | Water…! The water's here! | 3.0 |  |
| `ch04.b08.otane.003` | cinematic t=62.0 | お種 / Otane | 早乙女、呼んできて！　今日のうちに植えるで！ | Call the planters! We plant today! | 4.0 | 早乙女(さおとめ) |

#### ch04.b09 棚田と水分社 / The Terraces and the Water Shrine

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Readings / notes |
|---|---|---|---|---|---|---|
| `ch04.b09.villager.001` | volume_enter:vol_mikumari_sha | 村人 / Villager | 水分の神さんはな、水を分ける神さんや。独り占めはなさらん。 | Mikumari is the god who divides the water. Never hoards it. | 6.0 | 水分(みくまり) 独り占め(ひとりじめ). Speaker: old shrine keeper (villager pool) |
| `ch04.b09.villager.002` | after ch04.b09.villager.001 | 村人 / Villager | 猫柳生の先生も、昔はようお参りに来はった。 | Your old sensei used to come up here to pray, years ago. | 4.5 | Hints at collectible ch04.c01 |
| `ch04.b09.nyaakoto.003` | volume_enter:vol_tanada_vista | ニャーコト / Nyaakoto | ……屋敷が、見える。 | …I can see the estate from here. | 2.5 | Restrained grief: the burned estate up-valley |

#### ch04.b10 牛車を水車小屋へ / Escort the ox-cart to the mill

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Readings / notes |
|---|---|---|---|---|---|---|
| `ch04.b10.genroku.001` | beat_start | 大工 源六 / Genroku the carpenter | 牛は急かしたらあかん。牛の足で行くで。 | Don't rush the ox. We go at the ox's pace. | 4.0 |  |
| `ch04.b10.genroku.002` | after ch04.b10.genroku.001 | 大工 源六 / Genroku the carpenter | 羽根板六枚に、心棒一本。濡らしたらあかんで。 | Six paddles, one axle. They mustn't get wet. | 5.0 | 羽根板(はねいた) 心棒(しんぼう) |
| `ch04.b10.enforcer.003` | volume_enter:vol_escort_mid (wave 1) | 執行兵 / Enforcer | 搬送中の資産を確認。差し押さえます。 | Assets in transit identified. Seizing them. | 4.5 | 搬送(はんそう) |
| `ch04.b10.nyaakoto.004` | player_signal (repeatable) | ニャーコト / Nyaakoto | 伏せろ。 | Get down. | 1.5 | Voiced with the hide_on_signal command |
| `ch04.b10.otane.005` | progress_at:0.5 (sun-shower starts) | お種 / Otane | ……狐の嫁入りや。日ぃ照っとんのに。 | A fox's wedding. Rain, with the sun still out. | 3.5 | 狐の嫁入り(きつねのよめいり): sun-shower |
| `ch04.b10.genroku.006` | after ch04.b10.otane.005 | 大工 源六 / Genroku the carpenter | 言うたそばから！　板に蓑、掛けたって！ | Of course it rains now! Get the straw capes over the boards! | 4.0 | 蓑(みの) |

#### ch04.b11 水車を直せ / Repair the waterwheel

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Readings / notes |
|---|---|---|---|---|---|---|
| `ch04.b11.genroku.001` | beat_start | 大工 源六 / Genroku the carpenter | 羽根板は一枚ずつ。楔は二度打ちや。 | One paddle at a time. Two strikes on each wedge. | 4.0 | 楔(くさび). Diegetic tutorial for hammer_rhythm |
| `ch04.b11.genroku.002` | progress_at:0.6 (axle step) | 大工 源六 / Genroku the carpenter | 心棒、据えるで。息、合わせてや。……せえの！ | Seating the axle. Breathe with me… Heave! | 5.0 | 据える(すえる). 「せえの」 is the heave cue for the timing window |
| `ch04.b11.genroku.003` | progress_at:0.9 (brake step) | 大工 源六 / Genroku the carpenter | よっしゃ。歯止め、外してみい。 | Right. Go on—release the brake. | 3.5 | 歯止め(はどめ) |
| `ch04.b11.otane.004` | beat_complete | お種 / Otane | 回った……！　樋に水が上がる！ | It's turning…! Water's climbing into the flume! | 3.5 | 樋(とい) |
| `ch04.b11.nyaakoto.005` | after ch04.b11.otane.004 | ニャーコト / Nyaakoto | 水車にも、紋を。 | Paint the mon on the wheel, too. | 2.5 | 紋(もん): SORA mon painted on the hub |

#### ch04.b12 田植えの列を守れ / Guard the planting line

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Readings / notes |
|---|---|---|---|---|---|---|
| `ch04.b12.planter.001` | beat_start (loop) | 早乙女 / Planter | 〽今日植える苗は　秋には黄金 | ♪ The seedlings we plant today / turn to gold by autumn | 5.5 | Original lyric. 黄金(こがね). Sung, not spoken |
| `ch04.b12.planter.002` | after ch04.b12.planter.001 (loop) | 早乙女 / Planter | 〽水は上から　皆の田へ | ♪ Water from above / to everyone's fields | 4.0 | Original lyric |
| `ch04.b12.otane.003` | progress_at:0.05 (first net lock) | お種 / Otane | 網が来る！　早乙女を守って！ | Nets incoming! Protect the planters! | 3.0 | 網(あみ) |
| `ch04.b12.drone.004` | pattern:net_lock [drone] (repeatable) | 目録 / Inventory drone | 労働資産を差し押さえます。 | Seizing labor assets. | 3.0 | 労働資産(ろうどうしさん). Audio telegraph for the 800 ms net lock |
| `ch04.b12.planter.005` | npc_downed:planter_* (repeatable) | 早乙女 / Planter | 網や……！　動かれへん！ | A net…! I can't move! | 4.0 |  |
| `ch04.b12.villager.006` | progress_at:0.5 | 村人 / Villager | あかん、火縄が湿気てもうた！　お侍、その鉄砲は撃てるんか！ | No good, my match is soaked! Samurai—does yours still fire? | 6.0 | 湿気る(しける). Answered by the player's coil-matchlock shot |
| `ch04.b12.otane.007` | beat_complete | お種 / Otane | ……植わった。一列、全部。 | …Planted. The whole line. | 3.0 |  |

#### ch04.b13 生産改帳を開く / Open the Production Registry

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Readings / notes |
|---|---|---|---|---|---|---|
| `ch04.b13.oyuki.001` | beat_start | お雪 / Oyuki | 生産改帳、本日より付けます。まずは、これまでの分から。 | The production registry begins today. First, what came before. | 5.5 | 生産改帳(せいさんあらためちょう): reading to confirm (B7). Blocking with 002-003, about 14 s in total |
| `ch04.b13.oyuki.002` | after ch04.b13.oyuki.001 | お雪 / Oyuki | 矢十二本、種籾四俵、提灯四十張。 | Twelve arrows. Four bales of seed rice. Forty lanterns. | 4.0 | 種籾(たねもみ) 俵(ひょう) 張(はり). Carried over from ch01-ch03 |
| `ch04.b13.oyuki.003` | after ch04.b13.oyuki.002 | お雪 / Oyuki | そして本日、用水十二枚、水車一基。 | And today: water for twelve paddies. One waterwheel. | 4.0 | 枚(まい) 一基(いっき) |
| `ch04.b13.taemon.004` | after ch04.b13.oyuki.003 | 田右衛門 / Taemon | 紙は紙や。 | Paper is paper. | 1.5 | Bible §2.3 skeptic line (verbatim) |
| `ch04.b13.oyuki.005` | after ch04.b13.taemon.004 | お雪 / Oyuki | ええ。ですから、紙には、在る物しか書きません。 | Indeed. That is why paper records only what exists. | 4.5 | Article 1: 物なくして札なし |

#### ch04.b14 麦を三つの集落へ / Deliver barley to three hamlets

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Readings / notes |
|---|---|---|---|---|---|---|
| `ch04.b14.otane.001` | beat_start | お種 / Otane | 文太は臆病やで。青い光に寄せたら暴れる。 | Bunta scares easily. Keep her clear of the blue light. | 4.0 | 文太(ぶんた): the village pack mare. Tutorial for fear radius |
| `ch04.b14.villager.002` | item_delivered:hamlet_kami | 村人 / Villager | 麦や……！　上垣内に、麦が戻った！ | Barley…! Barley's back in the upper hamlet! | 4.0 | 上垣内(かみがいと) |
| `ch04.b14.otane.003` | idle_s:4 at hamlet_kami (Kurimaru stops to eat) | お種 / Otane | その馬、麦で動くんか。 | Does that horse run on barley? | 2.5 | Proposed light moment (callback to ch01.b06). Needs tone sign-off |
| `ch04.b14.nyaakoto.004` | after ch04.b14.otane.003 | ニャーコト / Nyaakoto | ……麦で動く。 | …She runs on barley. | 2.0 |  |
| `ch04.b14.villager.005` | item_delivered:hamlet_naka | 村人 / Villager | これで子らに食わせられる。おおきに。 | Now I can feed the children. Thank you. | 3.5 | 子ら(こら) |
| `ch04.b14.villager.006` | item_delivered:hamlet_shimo | 村人 / Villager | 下垣内まで、来てくれはったんか。 | You came all the way down to the lower hamlet? | 3.5 | 下垣内(しもがいと) |

#### ch04.b15 秤、現る / The Scales Arrive

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Readings / notes |
|---|---|---|---|---|---|---|
| `ch04.b15.margina.001` | cinematic t=22.0 | マルジナ / Margina | 下村の皆様。査定の結果が出ました。 | Residents of Shimomura. The assessment is complete. | 4.5 | 査定(さてい) |
| `ch04.b15.margina.002` | cinematic t=27.5 | マルジナ / Margina | 当区画の収穫は、全て担保として差し押さえます。 | All harvest in this sector is seized as collateral. | 5.5 |  |
| `ch04.b15.margina.003` | cinematic t=34.0 | マルジナ / Margina | ご異議は書面にて。受付は、秋でございます。 | Objections are accepted in writing. The office opens in autumn. | 5.0 | 異議(いぎ) |
| `ch04.b15.otane.004` | cinematic t=48.0 | お種 / Otane | 郷蔵の麦が……！　皆の麦が！ | The granary barley…! Everyone's barley! | 3.0 | 郷蔵(ごうぐら) |
| `ch04.b15.nyaakoto.005` | cinematic t=78.0 | ニャーコト / Nyaakoto | 栗丸。……行くぞ。 | Kurimaru. …We ride. | 2.5 | 栗丸(くりまる) |

#### ch04.b16 査定機「秤」を倒せ / Bring down the Assessor Engine

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Readings / notes |
|---|---|---|---|---|---|---|
| `ch04.b16.margina.001` | beat_start | マルジナ / Margina | 査定を開始いたします。動かないでください。値が狂います。 | Commencing assessment. Please hold still. Movement distorts the value. | 6.0 | 値(あたい) |
| `ch04.b16.margina.002` | pattern:seizure_net (repeatable) | マルジナ / Margina | 差押え網、展開。 | Deploying seizure net. | 2.5 | Audio telegraph, 800 ms cyan lock |
| `ch04.b16.margina.003` | pattern:sweep_beam (repeatable) | マルジナ / Margina | 査定中……評価額、零。 | Assessing… Value: zero. | 3.5 | Bible §8 voice telegraph; id fixed by §12.4. 評価額(ひょうかがく) 零(ぜろ/れい: confirm B7) |
| `ch04.b16.margina.004` | pattern:plant_stomp (repeatable) | マルジナ / Margina | 計量。 | Weighing. | 1.5 | 計量(けいりょう). Audio telegraph, 1000 ms amber ring |
| `ch04.b16.margina.005` | pattern:drone_release (repeatable) | マルジナ / Margina | 目録、放出。 | Releasing Inventory. | 2.0 | 放出(ほうしゅつ) |
| `ch04.b16.otane.006` | beat_start +6 s | お種 / Otane | 左回りや！　相手をずっと左に置いて射るんや！ | Circle left! Keep it on your left and shoot! | 4.0 | Tutorial for counter-clockwise mounted archery |
| `ch04.b16.kohagi.007` | pattern:step_plant (first only) | 小萩 / Kohagi | 脚の環が光った。踏んだ時だけ。 | Leg ring's glowing. Only when it plants. | 3.5 | 環(わ) |
| `ch04.b16.margina.008` | weakpoint_destroyed:coil_* (repeatable) | マルジナ / Margina | 秤に誤差。……許容外です。 | Scale error. …Outside tolerance. | 3.5 | 秤(はかり) |
| `ch04.b16.margina.009` | boss_phase:2 | マルジナ / Margina | 再評価いたします。……水車小屋に、担保価値あり。 | Revaluing. …The mill has collateral value. | 6.0 | 再評価(さいひょうか) |
| `ch04.b16.otane.010` | after ch04.b16.margina.009 | お種 / Otane | 水車の前で膝ついた！　腹の太鼓、叩き斬ったれ！ | It's kneeling at the mill! Cut the drum in its belly! | 4.5 | Tutorial for the ledger-drum weakpoint |
| `ch04.b16.margina.011` | pattern:assessment_kneel (repeatable) | マルジナ / Margina | 担保価値を、算定中。 | Calculating collateral value. | 3.0 | 算定(さんてい) |
| `ch04.b16.margina.012` | pattern:claw_sweep (repeatable) | マルジナ / Margina | 減価償却。 | Depreciation. | 1.5 | 減価償却(げんかしょうきゃく). Audio telegraph, 1000 ms amber arc |
| `ch04.b16.margina.013` | boss_event:mill_seal (repeatable) | マルジナ / Margina | 一件、差押え完了。 | One item seized. | 2.5 | Warns of the 3-seal fail counter |
| `ch04.b16.otane.014` | player_died (plays on respawn, repeatable) | お種 / Otane | 立って！　まだ終わってへん！ | Get up! It's not over! | 2.5 |  |
| `ch04.b16.margina.015` | beat_complete (outro) | マルジナ / Margina | ……損切りいたします。 | …I am cutting my losses. | 2.5 | 損切り(そんぎり): Margina ejects and flees |

#### ch04.b17 麦を郷蔵へ戻せ / Return the barley to the granary

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Readings / notes |
|---|---|---|---|---|---|---|
| `ch04.b17.oyuki.001` | beat_start | お雪 / Oyuki | 郷蔵へ運びましょう。どの田の麦か、札を付けてくださいませ。 | Let us take it to the granary. Tag each load with its field. | 5.5 | 札(ふだ) |
| `ch04.b17.villager.002` | item_delivered:barley_load (first) | 村人 / Villager | うちの麦や。……ほんまに、うちの麦や。 | It's our barley. …It really is ours. | 4.0 |  |
| `ch04.b17.oyuki.003` | progress_at:1.0 (last load delivered) | お雪 / Oyuki | 麦、百二十束。育てた者の名と共に、記しました。 | Barley, 120 sheaves. Recorded with the names of those who grew it. | 5.0 | 束(そく) in the formal count; farmers say たば. 記す(しるす) |
| `ch04.b17.taemon.004` | beat_complete | 田右衛門 / Taemon | ならば、皆で食べられるだけ作ろう。 | Then we will grow enough for everyone to eat. | 3.5 | Catalog canon ch04 line 3 (verbatim) |

#### ch04.b18 蛍 / Fireflies

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Readings / notes |
|---|---|---|---|---|---|---|
| `ch04.b18.otane.001` | cinematic t=20.0 | お種 / Otane | うちも入れて。空紋の一揆に。 | Count me in. The Sora League. | 3.0 | 空紋一揆(そらもんいっき) |
| `ch04.b18.oyuki.002` | cinematic t=26.0 | お雪 / Oyuki | 歓迎いたします。……一名、確かに記しました。 | Welcome. …One member, duly recorded. | 4.5 |  |
| `ch04.b18.taemon.003` | cinematic t=44.0 | 田右衛門 / Taemon | 蛍が出たら、田はもう大丈夫や。 | When the fireflies come out, the fields will be fine. | 4.0 | 蛍(ほたる) |
| `ch04.b18.kohagi.004` | cinematic t=78.0 | 小萩 / Kohagi | 尾根に一騎。……黒鹿毛。 | One rider on the ridge. …A black-bay. | 3.5 | 尾根(おね) 一騎(いっき) 黒鹿毛(くろかげ) |
| `ch04.b18.nyaakoto.005` | cinematic t=86.0 | ニャーコト / Nyaakoto | ……虎之介。 | …Toranosuke. | 2.0 | 虎之介(とらのすけ) |

### 7.3 HUD tutorial prompts (text only, not voiced)

Tokens in braces are input actions that L4 resolves to the current binding (keyboard, mouse or controller glyph).

| Prompt id | When | Japanese | English |
|---|---|---|---|
| `ui.ch04.b02.bank_roads` | ch04.b02 beat_start | 畦は馬で通れない。土手道を進め | Horses cannot use paddy ridges. Keep to the bank roads. |
| `ui.ch04.b03.hayago` | ch04.b03 after weapon 5 unlock | {Reload}で早合を込める。カチッと鳴った瞬間にもう一度{Reload}で素早く締める | {Reload} loads a hayagō. Press {Reload} again on the click to lock it faster. |
| `ui.ch04.b03.cheek` | ch04.b03 first aim with weapon 5 | 頬付けで構える。馬上では鉄砲を使えない | Cheek-stocked aim. Firearms cannot be used on horseback. |
| `ui.ch04.b04.bind` | ch04.b04 progress_at:0.15 | 鎖鎌の分銅は刃・盾・目録を絡め取る | The kusarigama weight snares a blade, shield or drone. |
| `ui.ch04.b04.barley` | ch04.b04 beat_start | 高い麦の中では互いに見えにくい。揺れる穂に注意 | In tall barley no one sees far. Watch for swaying heads. |
| `ui.ch04.b05.nonlethal` | ch04.b05 beat_start | 首輪の者は峰打ちで倒し、{Interact}長押しで首輪を断つ | Subdue the collared with the back of the blade, then hold {Interact} to cut the collar. |
| `ui.ch04.b06.crank` | ch04.b06 beat_start | {Interact}を一定の調子で押して巻き上げる。速さを帯の中に保て | Press {Interact} at a steady pace to crank. Keep your speed inside the band. |
| `ui.ch04.b07.hold` | ch04.b07 beat_start | 堰の周りに留まれ。敵が入ると水位が止まる | Stay by the weir. Enemies inside stop the water rising. |
| `ui.ch04.b10.signal` | ch04.b10 beat_start | 同行者はあなたがそばにいる間だけ進む | The escort moves on only while you stay close. |
| `ui.ch04.b12.net` | ch04.b12 first npc_downed | 網に捕らわれた者は{Interact}で解放。12秒で連れ去られる | {Interact} to free netted planters. They are taken after 12 s. |
| `ui.ch04.b13.registry` | ch04.b13 beat_complete | 生産改帳が開いた。{Menu}からいつでも見られる | The registry is open. View it any time from {Menu}. |
| `ui.ch04.b14.pack` | ch04.b14 beat_start | 荷を積んだ駄馬がいる間は常歩と速歩のみ | While leading a laden pack horse you can only walk or trot. |
| `ui.ch04.b16.ccw` | ch04.b16 beat_start | 左回りに走り、敵を弓手（左）に置け | Circle left to keep the target on your bow side. |
| `ui.ch04.b16.coils` | ch04.b16 first step_plant | 脚の秤環は踏み込んだ時だけ光る | Leg coils glow only while that leg is planted. |
| `ui.ch04.b16.drum` | ch04.b16 boss_phase:2 | 膝をついた時、腹の帳簿胴を斬れ | When it kneels, strike the ledger drum. |

---

## 8. Historical and cultural accuracy notes

These notes cover the chapter's period claims (early 17th century, Yamato/Kinai). "Verify" marks items that need the historian's sign-off before any release copy calls them accurate (bible §20, open item 2). The bible's §19 checklist still applies.

### 8.1 The season and the fields

- **麦秋 and double cropping.** Barley or wheat grown over winter on drained paddies (田麦) and harvested before rice transplanting was established in the Kinai by the medieval period. The Kamakura shogunate's order of 1264 (文永元年), which forbade stewards to tax 田麦, is the evidence usually cited. The early-summer order is therefore right: barley harvest in late May–early June, then flooding and transplanting in June.
- **Harvest tools.** Use:
  - 鎌 sickles, and sheaves (束) stooked to dry.
  - Threshing with 扱箸 (こきばし) and the 唐竿 flail; winnowing with the 箕 basket.
  - The 竜骨車 chain pump for lifting water (bible §19 "use").
- **Tools to avoid:**
  - The 千歯扱き comb-thresher (Genroku era, c. 1688–1704).
  - The 唐箕 winnowing machine and the 踏車 treadle wheel as hero props (both spread in the later 17th century; verify dates).
- **Planting.**
  - 苗代 nursery beds, then 代掻き puddling with horse or ox and a 馬鍬 harrow.
  - 早乙女 planters work a front, stepping backwards as they plant.
  - **Avoid rope-guided grid planting (正条植え).** It spread in the Meiji era. In 1623 paddies are planted by eye in loose rows, which is also why planted clumps are cosmetic and not collision.
- **Work songs.** 田植え歌 are right for the period. Elaborate drummed ritual planting (such as Hiroshima's 壬生の花田植, inscribed on UNESCO's Representative List in 2011) is a regional form and should not be copied. Shimomura's song is unaccompanied or has a single hand drum, and its lyric (§7, b12) is original.
- **Barley height.** Premodern landraces stood taller than modern short-straw varieties. The 110–130 cm stand is a gameplay value; verify it against an agronomic reference.
- **Crow-scaring guns.** Villages kept firearms for scaring birds and beasts from crops (威し鉄砲) through the Edo period. Fujiki Hisashi's work on Hideyoshi's sword hunt (『刀狩り』, 2005) argues that villages kept many firearms after 1588. Taemon's gun is plausible; verify.

### 8.2 Water, the weir and the wheel

- **Reservoirs.** 溜池 are characteristic of the Yamato basin and the wider Kinai, where rainfall and rivers are limited. Water was allocated by rotation (番水), and disputes (水論) were serious village business. The headman kept the rotation, which is Taemon's role and the story behind heirloom `ch04.c04`.
- **Outlets.** Historical reservoir outlets were usually a bottom culvert (底樋) with a vertical intake (竪樋, 尺八樋) whose plugs were pulled by rope. The game's windlass-lifted gate boards on the existing `SM_Nyaagyu_IrrigationSluice` are a readable simplification; verify.
  - A period reference for timber outlet construction is Sayama-ike (狭山池, Osaka), Japan's oldest reservoir. It was repaired in 1608 (慶長十三年) under Katagiri Katsumoto, and its excavated Keichō-era wooden culvert is displayed at the Osaka Prefectural Sayamaike Museum.
- **Lifting waterwheels.** 『徒然草』第五十一段 (c. 1330) tells how villagers of Uji built a working waterwheel to lift river water for the Kameyama palace, so lifting wheels existed in the Kinai long before 1623.
  - Surviving wheels such as the 朝倉三連水車 (1789) are later. Use them only as construction references for bucket rims, axle bearings and flumes.
  - The 4.5 m wheel lifting to 3.4 m respects the rule that a lifting wheel raises water to less than its own diameter.
- **水分 (みくまり).** The 延喜式 norito for the 祈年祭 names the four 水分 of Yamato: 吉野, 宇陀, 都祁 and 葛木. Shimomura's 水分社 is a **fictional village shrine**, not a depiction of any real shrine. The torii and 小祠 are generic, and no real shrine's crest or name board appears.

### 8.3 Arms and swordsmanship

- **No new sword-school content.** Chapter 4 uses only vocabulary already established: the 間合い ring, 受け and 合わせ against blade retainers, 転 flanking, and 残心 stamina recovery (bible §3.2). Collared conscripts are subdued with 峰打ち and freed with a seal-cut (bible §3.2, §7). The real school's named kata are not referenced.
- **Mounted weapons.** Katana cuts go to the 馬手 (right) side and yumi shots to the 弓手 (left) side, arc −170° to +15°. When shooting, the tazuna are knotted on the neck and the rider rises in the broad abumi (bible §4.2). Firearms are never used mounted.
- **Kusarigama.** A sickle joined by a chain to a weight (分銅). Several koryū preserve kusarigama curricula (see the [Nihon Kobudō Kyōkai](https://www.nihonkobudokyoukai.org/) member listings).
  - The popular story that it began as a peasant's farm sickle is not established history. Otane's weapon, a farm sickle fitted to a chain, is a **fictional** village make, and the game reproduces no school's techniques.
  - Hand conventions (which hand holds the sickle and which swings the weight) differ between schools, so the animation needs practitioner review.
- **Matchlocks.**
  - The tanegashima pattern is **cheek-stocked** (頬付け). It has a 火皿 pan with a 火蓋 cover, a serpentine holding the 火縄, and a 尾栓 breech plug.
  - 早合 cartridges were carried in a 胴乱 pouch. Slow-match fails in rain even when treated (雨火縄), which is what b12 shows.
  - The coil breech is fiction (bible §4.4).

### 8.4 Horses, tack and transport

- **Kurimaru.** A native mare of about 130 cm, with kura, aori, girth, abumi, kutsuwa, headstall, breastcollar, crupper and cloth tazuna (bible §4.5; [horse tack references](../historical-horse-tack-art-reference.md)). The current source is a stylized study that still needs review.
- **Pack horse.** Bunta carries a 荷鞍 pack saddle with 振り分け loads and is led on a rope. Edo post-station rules later set a full pack load (本馬) at about 40 貫 (about 150 kg). 30 dry sheaves fit within one horse load (verify sheaf weight, about 4–5 kg).
- **No geldings.** Horses were not castrated in Japan until the Meiji era (the 1901 馬匹去勢法), so period horses are mares or stallions. Arashi is a stallion; Kurimaru and Bunta are mares.
- **Horses in paddies.** Horses and oxen puddled flooded paddies at a walk. That is why mud allows a walk only, and why horses keep to the roads.
- **The ox-cart.** A two-wheeled ox-drawn freight cart (牛車, read **うしぐるま**), in the tradition of the medieval Kyoto freight carters (車借).
  - It is not the Heian court carriage (牛車, ぎっしゃ).
  - Avoid the 大八車 (commonly dated after the 1657 Meireki fire) and any four-wheeled wagon.
  - The ox is a black native bullock with a nose rope.

### 8.5 Village society and documents

- **Headman and officials.** 庄屋 is the Kinai term for the headman (bible §6.2), assisted by 年寄 elders. The third village office, 百姓代, belongs to the later 17th century, so the granary intake page (`ch04.c05`) carries only the 庄屋 and 年寄 seals.
- **爪印.** A nail print was used as a mark by people without a seal. The grower's claw-print is its feline equivalent.
- **垣内 (かいと).** A Yamato-area word for a hamlet or neighborhood unit within a village. It is used for the three hamlets. Readings vary by district (かいと / がいと / かきうち); confirm with B7.
- **郷蔵.** A village storehouse for tax rice and relief grain. It is mainly documented from the Edo period and is already on the bible §19 "use" list.
- **Other.** 高札 notice boards and 青田買い are period terms (bible §2.1, §19). The 生産改帳 is fiction. Its reading, せいさんあらためちょう, follows 宗門改帳 (しゅうもんあらためちょう); confirm with B7.

### 8.6 Architecture and dress

- **Farmhouses.**
  - 茅葺 thatch, packed-earth 土間 with 竈, a board-floored 板の間 around the 囲炉裏, and earthen walls.
  - Paper 障子 only in the better rooms. No glass (bible §19).
  - The distinctive Yamato 大和棟 (高塀造り) roof survives mostly in 18th–19th-century examples. Use it at most for the headman's house, and only after historian sign-off; elsewhere use plain hipped thatch.
- **Granary and mill.** Plastered earthen walls on a stone footing for the granary; board walls and thatch for the mill hut.
- **Dress.**
  - 野良着 of cotton or hemp (cotton growing had spread in the Kinai by the early 17th century), 襷 sleeve ties, 手拭い head towels, 脚絆 and 手甲.
  - 菅笠 and 蓑 in the sun-shower; straw 草鞋, or barefoot in the paddies.
  - Planters wear simple 小袖 with 襷 and 菅笠. **Avoid** the later festival image of uniform red-sashed 早乙女.
  - Taemon wears a 十徳 over his work clothes at the registry scene (bible §4.6).
  - Oyuki carries a 矢立 brush case, a 硯箱 writing box and a soroban (bible §6.1, §19).

### 8.7 Nature and sound

- Genji fireflies emerge in late May and June in the Kinai, the same weeks as transplanting.
- The ホトトギス (lesser cuckoo) is the classic early-summer call. In classical poetry it is the bird that announces rice planting (早苗鳥, 田長鳥), so use it in the b08–b12 ambience.
- Grey herons, little egrets, frogs (トノサマガエル and シュレーゲルアオガエル) and swallows.
- 狐の嫁入り is the folk name for a sun-shower.

### 8.8 The SORA kamon in chapter 4 (bible §17)

| Surface | Treatment | Beat |
|---|---|---|
| Chapter title card | Vermillion 朱印 seal beside the brush title | b01 |
| Nyaakoto's sode and dō | Existing runtime skin placements | All |
| Kurimaru's abumi front plates and crupper fittings | Existing tack source placements | b02, b14, b16 |
| Freed First Weir | Painted on the gate's timber header in **弁柄** (red iron oxide), not 朱: cinnabar was costly and 弁柄 was the everyday village red | b06 complete |
| Freed waterwheel | Painted on the hub in 弁柄 | b11 complete |
| 生産改帳 cover | Vermillion seal impression | b13 |
| League chalk marks | Kohagi's field-hut mark (`ch04.c02`); a child re-chalks the granary door | b09, b17 |
| Otane's tenugui | Hand-painted mon when she joins | b18 |
| UI | Objective marker, rotating save mon, registry screen | All |

The Credit House scrapes the house mon off the granary door and seals over it. Alien objects (meter posts, kiosks, the collection station, Hakari) carry only the alien **ledger sigil**, a closed ring of tally notches, and never the SORA mon. All mon art is imported from the pinned SVG's two original paths ([sora-kamon-runtime-art.md](../sora-kamon-runtime-art.md)).

### 8.9 Sources

- The Met, *Farmers' Lives in the Twelve Months* (rice baling and storage): <https://www.metmuseum.org/art/collection/search/44674>
- The Met, kura 2000.405: <https://www.metmuseum.org/art/collection/search/26572>; abumi 2008.120: <https://www.metmuseum.org/art/collection/search/35376>; saddle kit 36.25.571: <https://www.metmuseum.org/art/collection/search/23992> (via [historical-horse-tack-art-reference.md](../historical-horse-tack-art-reference.md))
- All Japan Kyudo Federation, 射法: <https://www.kyudo.jp/howto/syaho.html> (via [historical-arms.md](../historical-arms.md))
- Nihon Kobudō Kyōkai: <https://www.nihonkobudokyoukai.org/>
- 吉田兼好『徒然草』第五十一段 (c. 1330): the Uji waterwheel
- 『延喜式』巻八 祝詞「祈年祭」: the four 水分 of Yamato
- Kamakura shogunate order on 田麦, 文永元年 (1264)
- Osaka Prefectural Sayamaike Museum (大阪府立狭山池博物館): the Keichō repair of 1608 and its wooden culvert
- UNESCO Representative List of the Intangible Cultural Heritage, *Mibu no Hana Taue* (2011)
- 藤木久志『刀狩り』(岩波新書, 2005)
- 馬匹去勢法 (1901)

---

## 9. Art and audio asset list

Status key:

- **Existing:** in the repo; path given.
- **Existing (study):** source or prototype exists but has not passed the photoreal gates.
- **Needed:** must be created, or taken from a license-verified free source.

Every asset must pass the [photoreal acceptance](../art-direction/photoreal-acceptance.md) gates before it enters the campaign: a packaged fixed-camera A/B, a recorded license, and measured frame cost on both platforms (bible §15). Paths are relative to `Content/SourceArt/` unless they start with `/Game/`.

### 9.1 Environment

| Asset | Status | Source and what it still needs |
|---|---|---|
| First Weir sluice | **Existing (study)** | `Environment/NyaagyuSluice/SM_Nyaagyu_IrrigationSluice.fbx` (10,524 triangles). Its manifest already targets chapter 4 irrigation sites. Imported as `/Game/Generated/Environment/Props/SM_Nyaagyu_IrrigationSluice` with `M_Sluice_*` (including `M_Sluice_DebtRed`, `M_Sluice_FlowCyan`). Needs: photoreal pass, windlass drum and rope, animated 堰板 gate boards, a cyan seal clamp with a shatter state, and a 弁柄 mon decal state |
| Stone basin, rill and bamboo | **Existing (study)** | `Environment/NyaagyuWaterCourt/` (`SM_Nyaagyu_WaterCourt_4m`, `SM_Nyaagyu_BambooRill_4m`, source-only). Reuse the basin and bamboo for the 水分社 spring |
| Kura → village 郷蔵 | **Existing (study)** | `Environment/NyaagyuKura/SM_Nyaagyu_ProvisionKura.fbx`, `Environment/NyaagyuKuraFront/`, `/Game/Generated/Environment/Props/M_Kura_*`. Derive a rural variant with a 0.6 m stone footing and a scraped-mon, sealed door state |
| Vermillion torii | **Existing (study)** | `Environment/Original/SM_Nyaagyu_ToriiGate.fbx`, `Environment/ToriiLacquer/` textures, and `Environment/NyaagyuToriiFootStudy/` (moss). Scale to 2.8 m and remove the estate name plaque |
| Alien kiosk → meter, toll and ledger kiosks | **Existing (study)** | `Environment/Original/SM_Alien_DebtKiosk.fbx`; `StreetDebtTerminal` materials (`M_StreetTerminal_*`). Derive the collection-station and toll-post kiosks |
| Cargo stack (crates, straw bundles) | **Existing** | `Environment/NyaagyuCargoStack/`: League supplies in the headman's yard |
| Roadside leaf silt | **Existing** | `Environment/NyaagyuGroundDressing/`: dike edges and road verges |
| Stone path and steps scans | **Existing** | `Environment/NyaagyuHeroPath/`, `Environment/NyaagyuTerrain/GreyStonePath`: the dam stair and shrine steps |
| CC0 palette | **Existing** | `Environment/PolyHaven/`: `wood_planks_dirt`, `stone_floor`, `brown_mud_leaves_01`, `rusty_metal_02`, `kloofendal_overcast_puresky`, `GreyRoofTiles`, `WhitePlaster02`, `Fern02` (shrine), `PineSaplingSmall` / `NyaagyuPine` (east ridge), `TreeSmall02` / `NyaagyuTree` |
| Shimomura terrain (800 × 600 m) plus reservoir and terrace sublevels | Needed | C3. Mesh Terrain research path with HI/MAC tiers, matching the Estate source conventions ([mesh-terrain-nyaagyu.md](../mesh-terrain-nyaagyu.md)). The Estate terrain tiles are not reused |
| Paddy water and mud material | Needed | Mirror reflection, wetness, footprint and hoof decals, rain rings, planted-clump masks. Lumen reflections on Windows; SSR plus captures on Mac |
| Barley 麦 (ripe six-row, 110–130 cm) | Needed | Wind animation, stubble, sheaves (束) and stooks, trample and sway response. Nanite on Windows; card LODs on Mac |
| Rice seedlings 苗 | Needed | Bundles and planted clumps (instanced, no collision) |
| Dike, 畦, canal and flume kits | Needed | 石積み canal banks, lateral gates, wooden 樋 flumes on trestles, 水口 inlet boards |
| Thatched farmhouse kit | Needed | Three variants plus the headman's house: 茅葺, 土間, 囲炉裏, 竈, 納屋 |
| Lifting waterwheel and mill | Needed | 4.5 m wheel with swappable broken and new paddles, 12 buckets, axle and bearings, brake; hut, millrace, plank bridge |
| Earth dam | Needed | Crest, revetment, spillway, outlet channel, stone stair, and a carved 水位石 depth marker |
| Terraces | Needed | 野面積み dry-stone risers, zigzag path, field hut |
| 水分社 | Needed | 小祠, stone lanterns ×2, 鈴緒 bell rope, offerings |
| Credit House field kit | Needed | Collection-station pad and barriers, guard-hut prefabs, 2.2 m meter posts with numerals, seal clamps, drone rack, notice leaflets. The kiosk can be derived from the existing kiosk |
| Farm props | Needed | Seized 竜骨車 chain pumps, 鍬, 鋤, 馬鍬, 鎌, 箕, 扱箸, 唐竿, stored 稲架 poles, straw mats, water jars, practice bales |
| Ox-drawn freight cart | Needed | Two-wheeled, with yoke and load straps; the paddle boards and axle as cargo |
| Registry and tallies | Needed | 生産改帳 book with seal, 硯箱, 矢立, wooden 札 field tags. Shared with ch05's 割符 set |

### 9.2 Characters and creatures

| Asset | Status | Source and what it still needs |
|---|---|---|
| Nyaakoto (world, cinematic and first person) | **Existing (study)** | `Characters/Hero/`, `Characters/NyaakotoFirstPersonPaws/`, runtime skin `SK_NyaagyuSamurai`. In progress toward the photoreal target |
| Otane (はちわれ; 野良着, head towel, kusarigama) | Needed | Hero NPC; also rides Bunta |
| Taemon, Oyuki, Kohagi, Tetsugorō | Needed | Shared cast (ch02–ch08) |
| Minor NPCs | Needed | Genroku and the apprentice Kichiji; 8 planter variants; 6 villager variants; the shrine keeper; Yosaku (collared variant); children |
| Enforcer, blade retainer, shield enforcer | Needed | `SK_AlienBanker` / `A_AlienBanker_*` exist only as a prototype base rig. Hairless skin: no strand grooms needed (bible §1.4) |
| `drone` (目録) | Needed | Floating disc with a cyan eye, a net launcher and a haul tether |
| `bound_conscript` | Needed | Local clothes, a glowing debt collar with a dark state, bamboo staff |
| Hakari (8 m walker) with cockpit and Margina | Needed | Shares a rig family with the ch08 `seizure_walker`. Weigh-coils, ledger drum and hoppers as breakable parts; collapse state |
| Kurimaru with full tack | **Existing (study)** | `Horses/Nyaagyu/SM_Nyaagyu_HorseAndTack.fbx`, `Horses/Nyaagyu/RigStudy/SK_Nyaagyu_Horse_RigStudy.fbx` (walk study), `Horses/NyaagyuAbumiTazunaStudy/` textures, `Horses/Nyaagyu/AnatomyStudy/`. Needs a photoreal chestnut coat, a deforming rig, all four gaits plus the amble, spook and rear, eating, and a mounted-archery rider pose |
| Bunta (bay pack mare) | Needed | Coat variant of the Kurimaru rig, 荷鞍 pack saddle, 振り分け sheaf load, lead rope |
| Arashi (black-bay stallion) | Needed | Silhouette-level for b18; full asset later for ch06–ch08 |
| Ox | Needed | Black native bullock with nose rope; walk, stop and low |
| Wildlife | Needed | Heron and egret (takeoff), frogs (ambient FX), swallows (flock FX), fireflies (Niagara) |

### 9.3 Weapons and handheld props

| Asset | Status | Source and what it still needs |
|---|---|---|
| Kusarigama (weapon 2) | **Existing (study)** | `SM_Weapon_02.fbx` → `/Game/Generated/Meshes/SM_Weapon_02` is a prototype. Needs a photoreal sickle, chain and 分銅, chain physics, and first-person grip |
| Coil matchlock (weapon 5) | **Existing (study)** | `SM_Weapon_05.fbx` → `/Game/Generated/Meshes/SM_Weapon_05` is a prototype. Needs a cheek-stocked tanegashima form with 火皿 and 火蓋, a 尾栓 breech with the alien coil grafted on, 早合 cartridges and a 胴乱 pouch. Being a village gun, it carries no SORA mon |
| Katana (0), yumi (18), yari (19) | **Existing (study)** | `Weapons/HeroKatana/`, `Weapons/NyaagyuYumi/`, `Weapons/NyaagyuYari/` (source-only study) |
| Carpenter's 玄翁 mallet, 楔 wedges | Needed | b11 manufacture props |
| Old slow-match gun | Needed | Villager prop for b12: glowing match and a fizzle |

### 9.4 Animation

All animation is **Needed**: first-person, third-person and cinematic.

- **Crank:** windlass crank loop in three speed bands plus a rope slip.
- **Hold:** hold stance.
- **Carry:** 背負い back-load carry and drop.
- **Seal and nets:** seal-cut; net-cut (1.0 s).
- **Kusarigama:** throw the weight, bind, pull and follow-up cut.
- **Coil matchlock:** 早合 reload (open, insert, lock, early lock); cheek-stock aim.
- **Horseback:** tie the lead rope; mount and dismount; whistle recall; mounted yumi left-arc draw (rider rising in the abumi, reins knotted); mounted katana right-side cut; thrown from the horse.
- **NPCs:** planting (backward step, about 3 clumps per 2 s), netted-planter struggle, drone haul, ox-cart hide on signal, villager relay hand-off, Oyuki writing, Tetsugorō and Otane handovers.
- **Hakari:** four-beat walk, leg plant, stomp, net fire, beam sweep, kneel, claw sweep, stagger, collapse; Margina's ejection.
- **Kurimaru:** stops to eat barley (b14).

### 9.5 VFX

All VFX are **Needed**.

- **Water:** water release down the channel (foam at drops), paddy fill, mirror and ripples.
- **Weather:** sun-shower rain with backlit streaks and rain rings, steam wisps, optional faint rainbow, heat shimmer.
- **Barley:** sway ripple and chaff; the burst of sheaves from Hakari's hoppers.
- **Credit House:** cyan debt-seal shatter, meter numerals dimming, collar glow turning off, seizure-net launch and wrap.
- **Boss telegraphs:** sweep beam with a scorch-line preview, amber stomp-ring and claw-arc decals with animated edge pulses, weigh-coil glow, ledger-drum sparks and glass shards, the walker's mud-splash collapse.
- **Other:** matchlock smoke (black powder), fireflies, 弁柄 paint drying.
- **Mac:** caps on rain, fireflies and particles as in §2.

### 9.6 Sound

All sound is **Needed**.

- **Nature:** the 麦秋 soundscape: skylarks over the barley, the ホトトギス call, frog chorus with a stop cue for b15, heron, swallows, water in channels, the spring.
- **Barley and mud:** barley rustle, and mud and paddy footsteps (a loud noise class).
- **Weir and mill:** crank ratchet and rope creak, gate boards grinding, rushing water; wheel creak, bucket pour, wedge strikes.
- **Animals:** ox lowing, cart axle; horse gaits on earth and in mud, snort, spook.
- **Weapons:** kusarigama chain whirr and bind; coil matchlock (coil whine, then the black-powder report); 早合 paper tear and lock click (the reload cue); old matchlock fizzle.
- **Credit House:** drone hum, net launcher, haul tether.
- **Hakari:** hydraulic footfalls with tally clicks, weigh-coil hum, beam charge, kneel, drum spin, collapse.
- **Voice processing:** Margina and the enforcers use the translation-collar treatment (band-limited formant chorus, never pitch-shifted; bible §6.3).
- **Village:** sun-shower on straw hats and water, villagers' work sounds, and the planting song as a diegetic performance with one hand drum.

### 9.7 Music cues (L5 stem states)

| State | Beats | Brief |
|---|---|---|
| `ch04_fields_morning` | b01, b03 | Sparse 篠笛 and low strings; unresolved and humid |
| `ch04_ride_scout` | b02 | Walking pulse in time with the hoofbeat; open fifths |
| `ch04_combat_barley` | b04 | Taiko and low strings. Stems thin out while the player is hidden in the barley |
| `ch04_stealth_dam` | b05 | Near-silence; a water drone tone; the alert stem is triggered by alert states |
| `ch04_crank` | b06 | A ratchet-locked ostinato that speeds up with the crank's progress |
| `ch04_hold` | b07 | Driving percussion; a rising figure tied to the water level |
| `ch04_water_release` | b08 | The chapter's first full statement of the League theme; strings and 篠笛 |
| `ch04_explore_terraces` | b09 | Ambient; shrine bell and spring; very quiet |
| `ch04_escort_sunshower` | b10 | Plodding ox tempo; light 箏 figures in the rain |
| `ch04_mill_repair` | b11 | Work rhythm (700 ms pulse) matching the wedge beat |
| `ch04_planting_defend` | b12 | Built around the diegetic planting song; combat stems layer under it |
| `ch04_registry` | b13 | Solo 箏 and brush sounds |
| `ch04_harvest_ride` | b14 | A warm variant of `ch04_ride_scout` |
| `ch04_hakari_reveal` | b15 | Cold synth pad with a metronomic tick (the "assessment") that breaks the pastoral key |
| `ch04_boss_hakari` | b16 | P1 is a gallop ostinato; P2 is heavy, with the tick stem speeding up during each kneel (an audio telegraph) |
| `ch04_return_harvest` | b17 | The League theme, reduced |
| `ch04_dusk_fireflies` | b18 | Near-silence and frogs; a single 尺八-like breath note on the ridge reveal |

### 9.8 UI (L4)

All UI is **Needed**.

- The first-open registry screen (brush entries and the seal).
- The chapter title card with the 朱印 seal.
- Ink-wash scout-mark outlines.
- The crank arc with its shaded band.
- The water-level bar for the hold.
- Planter status pips.
- The cargo counter (30 → 20 → 10 → 0).
- The gait indicator (常歩 / 速歩 / 駈歩 / 襲歩) and horse stamina.
- The boss bar with four coil pips and a drum segment.
- The mill-seal counter (0/3).
- The 早合 reload tick.
- The HUD prompts in §7.

---

## 10. Hand-offs and open items

| Owner | Takes from this chapter |
|---|---|
| L1 | The 18 beats and their `target_s` (sum 3,600), checkpoints, sites 0/1/2 in catalog order, registry entries, unlock mask [2, 5], `hayago_reload`, `crank`, and the schema additions in §6.7 |
| L2 | Enemy compositions per beat (§4), dam stealth parameters, and the 早合 reload, kusarigama bind, barley and mud rules (§6) |
| L3 | `boss_hakari`: HP, weak points and pattern tables (§5) |
| L4 | HUD prompts (§7.3), first-open registry screen, crank, hold, gait and cargo widgets, and the golden-hour amber-decal readability check |
| L5 | Music states (§9.7) and captioned barks |
| C2/C3 | `pl_shimomura`, `pl_shoya_yashiki`, `pl_otameike`, `pl_tanada`, `pl_suisha_goya`, `pl_gogura` (§3), as campaign-only sublevels with no Arena 0 collision changes |
| C4 | Mission scripting for b02–b17 |
| C9 | Sequences `LS_Ch04_B01_ShoyaHouse`, `LS_Ch04_B08_WaterRuns`, `LS_Ch04_B15_HakariSeizure`, `LS_Ch04_B16_HakariCollapse` (outro) and `LS_Ch04_B18_Fireflies`. Each falls back to `camera_blend` until Sequencer lands |

**Open items.**

1. **B7 native review:**
   - Every line, especially the Kamigata and Yamato speech of Otane, Taemon, Genroku and the villagers.
   - The readings of 生産改帳, 垣内 and 零 (in the 評価額 line).
   - The planting-song lyric.
2. **Historian review:**
   - The windlass gate against 尺八樋 outlets.
   - The lifting wheel in 1623 Yamato.
   - 大和棟 dating.
   - Rural ox-cart freight.
   - Planter dress.
   - The crow-scaring gun.
   - The 郷蔵 and village-office details.
3. **Practitioner review:** kusarigama hand conventions and the mounted-archery rider pose.
4. **Equine review:** the lateral amble; pack-horse loading and lead-rope behavior.
5. **Tone sign-off:** the b14 barley moment, the only light beat in this chapter. It is not on the bible §1.2 approved list, so cut it if declined; lines `ch04.b14.otane.003` and `nyaakoto.004` would then be dropped, leaving 113 lines.
6. **Canon wording:** catalog line 1 reads 水車を奪われた in JA and "pumps" in EN. It is kept verbatim. The seized 竜骨車 in b01 make both true on screen. If canon may change, L1 could revise the EN to "waterwheel".
7. **Playtest:** measure b10 (ox pace) and b16 (arrow economy) first. They are the likeliest to miss the ±20% chapter-time gate.

---

## 11. Machine-readable beat data (YAML)

This block is generated from the same source as the tables above and was parse-checked. Field names follow bible §12.1–12.2. Additions proposed in §6.7 are marked in §6.7, not inline.

Top-level keys:

- `beats`: the sequenced beats.
- `collectibles`: passive beats, not counted in the totals.
- `x_boss_patterns`: for L3's `bosses.json`.
- `lines`: every voiced line, with `ja`, `en`, `speaker`, `register`, `mode` and `duration_s`.
- `ui_prompts`: the HUD prompts.

```yaml
chapter: ch04_irrigation
title_ja: 田畑の解放
title_en: Agricultural Liberation
map: 0
target_s: 3600
places: [pl_shimomura, pl_shoya_yashiki, pl_otameike, pl_tanada, pl_suisha_goya, pl_gogura]
speakers:
- {token: nyaakoto, id: samurai, ja: ニャーコト, en: Nyaakoto, register: samurai_restrained, status: existing}
- {token: taemon, id: farmer, ja: 田右衛門, en: Taemon, register: yamato_elder, status: existing id (bible §6.2)}
- {token: otane, id: farmer_young, ja: お種, en: Otane, register: kamigata_bright, status: bible §6.2}
- {token: oyuki, id: leader, ja: お雪, en: Oyuki, register: business_keigo, status: bible §6.1}
- {token: kohagi, id: scout, ja: 小萩, en: Kohagi, register: terse, status: existing}
- {token: tetsugoro, id: gunsmith, ja: 鉄五郎, en: Tetsugorō, register: blunt_artisan, status: bible §6.2}
- {token: margina, id: boss_margina, ja: マルジナ, en: Margina, register: alien_corporate_keigo, status: bible §6.3}
- {token: enforcer, id: enforcer, ja: 執行兵, en: Enforcer, register: alien_corporate_keigo, status: PROPOSED generic}
- {token: drone, id: drone, ja: 目録, en: Inventory drone, register: alien_machine, status: PROPOSED generic}
- {token: conscript, id: conscript, ja: 債縛衆, en: Debt-Bound, register: yamato_rural_distressed, status: PROPOSED generic}
- {token: yosaku, id: yosaku, ja: 与作, en: Yosaku, register: yamato_rural_distressed, status: PROPOSED minor (Otane's brother)}
- {token: villager, id: villager, ja: 村人, en: Villager, register: yamato_rural, status: PROPOSED generic}
- {token: planter, id: planter, ja: 早乙女, en: Planter, register: work_song, status: PROPOSED generic}
- {token: genroku, id: carpenter, ja: 大工 源六, en: Genroku the carpenter, register: kamigata_artisan, status: PROPOSED minor}
beats:
- id: ch04.b01
  type: cinematic
  place: pl_shoya_yashiki
  title_ja: 庄屋屋敷にて
  title_en: At the Headman's House
  target_s: 120
  checkpoint: true
  sequence: /Game/Campaign/Ch04/Cinematics/LS_Ch04_B01_ShoyaHouse
  duration_s: 120
  skippable: true
  fallback: camera_blend
  subtitles:
  - {line: ch04.b01.taemon.001, t: 8.0}
  - {line: ch04.b01.taemon.002, t: 14.5}
  - {line: ch04.b01.oyuki.003, t: 21.0}
  - {line: ch04.b01.oyuki.004, t: 27.5}
  - {line: ch04.b01.otane.005, t: 36.0}
  - {line: ch04.b01.nyaakoto.006, t: 43.0}
  - {line: ch04.b01.taemon.007, t: 45.5}
  - {line: ch04.b01.otane.008, t: 53.0}
  end_state:
    player_transform: ps_shoya_doma
    equipped: [0, 18]
  music: ch04_fields_morning
- id: ch04.b02
  type: horseback_ride
  place: pl_shimomura
  title_ja: お種と土手道を見回る
  title_en: Scout the bank roads with Otane
  target_s: 180
  checkpoint: true
  horse: kurimaru
  mode: travel
  route: spl_dote_scout
  complete: {volume_enter: vol_shoya_gate}
  gaits: [walk, trot, canter]
  weapons: [0, 18]
  fear: {spook_radius_cm: 900, recover_s: 2.5}
  auto_steer: setting
  dismount_allowed: false
  on_horse_down: checkpoint
  x_companions:
  - {npc: otane, horse: pack_horse, lead_cm: 600}
  x_scout_marks: [grp_mugi_north, grp_mugi_south, grp_collect_station]
  music: ch04_ride_scout
  dialogue:
  - 'on': beat_start
    lines: [ch04.b02.otane.001]
    mode: ambient
  - 'on': volume_enter:vol_meter_post_02
    lines: [ch04.b02.otane.002]
    mode: ambient
  - 'on': volume_enter:vol_mugi_overlook
    lines: [ch04.b02.otane.003, ch04.b02.nyaakoto.004, ch04.b02.otane.005]
    mode: ambient
  - 'on': volume_enter:vol_scout_end
    lines: [ch04.b02.otane.006]
    mode: ambient
- id: ch04.b03
  type: dialogue
  place: pl_shoya_yashiki
  title_ja: 鳥威しと鎖鎌
  title_en: The Crow-Scarer and the Kusarigama
  target_s: 90
  checkpoint: false
  trigger: beat_start
  mode: ambient
  camera: soft_lookat
  interrupt: queue
  lines:
  - ch04.b03.tetsugoro.001
  - ch04.b03.tetsugoro.002
  - ch04.b03.tetsugoro.003
  - ch04.b03.tetsugoro.004
  - ch04.b03.tetsugoro.005
  - ch04.b03.otane.006
  - ch04.b03.nyaakoto.007
  - ch04.b03.otane.008
  unlocks:
    weapons: [2, 5]
    mechanics: [hayago_reload]
  music: ch04_fields_morning
- id: ch04.b04
  type: combat_wave
  place: pl_shimomura
  title_ja: 麦畑の徴収隊を退けよ
  title_en: Drive off the collection patrol
  target_s: 300
  checkpoint: true
  bounds: vol_mugibatake_b04
  waves:
  - enemies:
    - {type: enforcer_rifle, count: 3, spawn: sp_mugi_north, patrol: spl_mugi_sweep_a}
    - {type: blade_retainer, count: 1, spawn: sp_mugi_north}
    - {type: drone, count: 1, spawn: sp_collect_station_air}
    trigger: start
  - enemies:
    - {type: enforcer_rifle, count: 3, spawn: sp_mugi_south, patrol: spl_mugi_sweep_b}
    - {type: blade_retainer, count: 1, spawn: sp_mugi_south}
    - {type: drone, count: 1, spawn: sp_collect_station_air}
    trigger: alive_below:2
  - enemies:
    - {type: enforcer_rifle, count: 2, spawn: sp_collect_station}
    trigger: alive_below:2
  complete: all_waves_cleared
  max_alive: 6
  allies:
  - {npc: otane, role: kusarigama_melee, downable: true}
  nonlethal_types: [bound_conscript]
  target_kind: enemy
  x_sight_occluders:
  - {volume: vol_barley_tall, ai_sight_cm: 500, crouched_hidden_beyond_cm: 300, sway_tell: true}
  music: ch04_combat_barley
  dialogue:
  - 'on': beat_start
    lines: [ch04.b04.otane.001]
    mode: ambient
  - 'on': progress_at:0.15
    lines: [ch04.b04.otane.002]
    mode: ambient
  - 'on': alert_state:alert
    lines: [ch04.b04.enforcer.003]
    mode: ambient
  - 'on': alert_state:search
    lines: [ch04.b04.enforcer.004]
    mode: ambient
  - 'on': alert_state:suspicious
    lines: [ch04.b04.drone.006]
    mode: ambient
  - 'on': progress_at:0.8
    lines: [ch04.b04.enforcer.005]
    mode: ambient
  - 'on': npc_downed:otane
    lines: [ch04.b04.otane.007]
    mode: ambient
  - 'on': beat_complete
    lines: [ch04.b04.otane.008]
    mode: ambient
- id: ch04.b05
  type: stealth_zone
  place: pl_otameike
  title_ja: 堤の見張りを抜けよ
  title_en: Slip past the dam guards
  target_s: 240
  checkpoint: true
  zone: vol_otameike_stealth
  guards:
  - id: g_crest_a
    type: bound_conscript
    patrol: spl_crest_a
    sight: {cone_deg: 90, range_cm: 1500, dark_range_cm: 700}
    hearing_cm: 800
  - id: g_crest_b_yosaku
    type: bound_conscript
    patrol: spl_crest_b
    sight: {cone_deg: 90, range_cm: 1500, dark_range_cm: 700}
    hearing_cm: 800
  - id: g_stair_top
    type: bound_conscript
    patrol: static:pt_stair_top:scan_120deg_6s
    sight: {cone_deg: 90, range_cm: 1800, dark_range_cm: 700}
    hearing_cm: 800
  - id: g_hut
    type: bound_conscript
    patrol: spl_hut_loop
    sight: {cone_deg: 90, range_cm: 1200, dark_range_cm: 600}
    hearing_cm: 800
  - id: g_drone_water
    type: drone
    patrol: spl_reservoir_loop
    sight: {cone_deg: 30, range_cm: 2500, dark_range_cm: 1200}
    hearing_cm: 0
  on_detected: combat
  complete: {exit_reached: vol_winch_platform}
  detection: {suspicion_rate: 0.8, alert_threshold: 1.0, search_s: 20}
  takedowns: {rear: true, lethal_default: false}
  light_sources: []
  x_shade_volumes: [vol_willow_shade_01, vol_willow_shade_02, vol_reed_bed_west]
  noise_surfaces:
  - {kind: gravel, volume: vol_crest_gravel}
  - {kind: running_water, volume: vol_spillway, mult: 0.5}
  - {kind: puddle, volume: vol_toe_ditch}
  lures: []
  x_approach: {mount: kurimaru, from: vol_mugibatake_b04, to: vol_gorge_foot, est_s: 90}
  music: ch04_stealth_dam
  dialogue:
  - 'on': volume_enter:vol_gorge_foot
    lines: [ch04.b05.kohagi.001, ch04.b05.kohagi.002]
    mode: ambient
  - 'on': idle_s:20
    lines: [ch04.b05.conscript.003]
    mode: ambient
  - 'on': alert_state:suspicious
    lines: [ch04.b05.conscript.004, ch04.b05.drone.007]
    mode: ambient
  - 'on': alert_state:search
    lines: [ch04.b05.conscript.005]
    mode: ambient
  - 'on': alert_state:alert
    lines: [ch04.b05.conscript.006]
    mode: ambient
  - 'on': npc_freed:yosaku
    lines: [ch04.b05.yosaku.008]
    mode: ambient
  - 'on': beat_complete
    lines: [ch04.b05.kohagi.009]
    mode: ambient
- id: ch04.b06
  type: production_task
  task: crank
  place: pl_otameike
  title_ja: 一の堰を開けよ
  title_en: Open the First Weir
  target_s: 240
  checkpoint: true
  site: 0
  crank:
    actor: sluice_winch_01
    turns_required: 12
    turn_rate_band: [0.4, 1.2]
    progress_decay_per_s: 0.05
    stamina_per_turn: 6
    interruptible: true
    coop_npc: otane
  waves:
  - enemies:
    - {type: enforcer_rifle, count: 3, spawn: sp_dam_north}
    trigger: progress_at:0.25
  - enemies:
    - {type: drone, count: 2, spawn: sp_reservoir_air}
    trigger: progress_at:0.6
  x_events:
  - at_progress: 0.25
    id: debt_seal_broken
    effects: ['collars_dark:pl_otameike']
  registry: {item_ja: 用水, item_en: Irrigation water, qty: 12, unit_ja: 枚, unit_en: paddies}
  unlocks:
    mechanics: [crank]
  music: ch04_crank
  dialogue:
  - 'on': beat_start
    lines: [ch04.b06.otane.001]
    mode: ambient
  - 'on': progress_at:0.25
    lines: [ch04.b06.enforcer.004, ch04.b06.conscript.005]
    mode: ambient
  - 'on': progress_at:0.3
    lines: [ch04.b05.yosaku.008]
    mode: ambient
  - 'on': progress_at:0.5
    lines: [ch04.b06.taemon.002]
    mode: ambient
  - 'on': progress_at:0.75
    lines: [ch04.b06.nyaakoto.003]
    mode: ambient
  - 'on': beat_complete
    lines: [ch04.b06.taemon.006]
    mode: ambient
- id: ch04.b07
  type: production_task
  task: hold
  place: pl_otameike
  title_ja: 水が満ちるまで堰を守れ
  title_en: Hold the weir while the water rises
  target_s: 240
  checkpoint: true
  hold: {volume: vol_weir_platform, hold_s: 90, contest: pause}
  waves:
  - enemies:
    - {type: enforcer_rifle, count: 3, spawn: sp_dam_west}
    trigger: start
  - enemies:
    - {type: shield_enforcer, count: 2, spawn: sp_dam_east}
    - {type: enforcer_rifle, count: 2, spawn: sp_dam_east}
    trigger: progress_at:0.33
  - enemies:
    - {type: blade_retainer, count: 2, spawn: sp_dam_north}
    - {type: drone, count: 2, spawn: sp_reservoir_air}
    trigger: progress_at:0.66
  max_alive: 6
  allies:
  - {npc: otane, role: kusarigama_melee, downable: true}
  music: ch04_hold
  dialogue:
  - 'on': beat_start
    lines: [ch04.b07.otane.001]
    mode: ambient
  - 'on': progress_at:0.33
    lines: [ch04.b07.enforcer.002, ch04.b07.otane.003]
    mode: ambient
  - 'on': progress_at:0.5
    lines: [ch04.b07.taemon.004]
    mode: ambient
  - 'on': progress_at:0.9
    lines: [ch04.b07.enforcer.005]
    mode: ambient
  - 'on': beat_complete
    lines: [ch04.b07.taemon.006]
    mode: ambient
- id: ch04.b08
  type: cinematic
  place: pl_shimomura
  title_ja: 水が走る
  title_en: The Water Runs
  target_s: 90
  checkpoint: false
  sequence: /Game/Campaign/Ch04/Cinematics/LS_Ch04_B08_WaterRuns
  duration_s: 90
  skippable: true
  fallback: camera_blend
  subtitles:
  - {line: ch04.b08.taemon.001, t: 18.0}
  - {line: ch04.b08.villager.002, t: 40.0}
  - {line: ch04.b08.otane.003, t: 62.0}
  end_state:
    player_transform: ps_canal_head_bank
    equipped: [0, 18]
  music: ch04_water_release
- id: ch04.b09
  type: explore_optional
  place: pl_tanada
  title_ja: 棚田と水分社
  title_en: The Terraces and the Water Shrine
  target_s: 240
  checkpoint: true
  optional: true
  requires: [ch04.b08]
  volume: vol_tanada
  pois:
  - {id: poi_mikumari_sha, kind: lore}
  - {id: poi_tanada_vista, kind: vista}
  - {id: poi_minakuchi_order, kind: challenge}
  - {id: poi_shrine_keeper, kind: npc}
  - {id: poi_field_hut_cache, kind: cache}
  rewards: [ch04.c01, ch04.c02, 'arrows:6', 'hayago:10']
  exit_hint_after_s: 180
  music: ch04_explore_terraces
  dialogue:
  - 'on': volume_enter:vol_mikumari_sha
    lines: [ch04.b09.villager.001, ch04.b09.villager.002]
    mode: ambient
  - 'on': volume_enter:vol_tanada_vista
    lines: [ch04.b09.nyaakoto.003]
    mode: ambient
- id: ch04.b10
  type: production_task
  task: escort
  place: pl_shimomura
  title_ja: 牛車を水車小屋へ
  title_en: Escort the ox-cart to the mill
  target_s: 240
  checkpoint: true
  requires: [ch04.b08]
  escort:
    npcs: [ox_cart_01, carpenter_genroku, carpenter_kichiji]
    path: spl_mill_road
    speed_cm_s: 110
    wait_for_player_cm: 1500
    fail_on_npc_death: true
    hide_on_signal: true
    npc_health: 250
    down_revive_s: 6
  waves:
  - enemies:
    - {type: enforcer_rifle, count: 3, spawn: sp_paddy_bank_east}
    trigger: volume_enter:vol_escort_mid
  - enemies:
    - {type: drone, count: 2, spawn: sp_canal_air}
    - {type: blade_retainer, count: 1, spawn: sp_mill_road}
    trigger: progress_at:0.75
  max_alive: 6
  x_weather_events:
  - {at_progress: 0.5, set: sun_shower_on}
  music: ch04_escort_sunshower
  dialogue:
  - 'on': beat_start
    lines: [ch04.b10.genroku.001, ch04.b10.genroku.002]
    mode: ambient
  - 'on': volume_enter:vol_escort_mid
    lines: [ch04.b10.enforcer.003]
    mode: ambient
  - 'on': player_signal
    lines: [ch04.b10.nyaakoto.004]
    mode: ambient
  - 'on': progress_at:0.5
    lines: [ch04.b10.otane.005, ch04.b10.genroku.006]
    mode: ambient
- id: ch04.b11
  type: production_task
  task: manufacture
  place: pl_suisha_goya
  title_ja: 水車を直せ
  title_en: Repair the waterwheel
  target_s: 180
  checkpoint: true
  site: 1
  manufacture:
    recipe: waterwheel_repair
    stations: [st_wheel_rim, st_axle_seat, st_wheel_brake]
    steps:
    - {kind: assemble, count: 6}
    - kind: hammer_rhythm
      count: 12
      timing: {beat_ms: 700, tolerance_ms: 150}
    - kind: assemble
      count: 1
      timing: {beat_ms: 900, tolerance_ms: 200}
    - {kind: inspect, count: 1}
    output: {item: waterwheel, qty: 1}
  waves: []
  registry: {item_ja: 水車, item_en: Waterwheel, qty: 1, unit_ja: 基, unit_en: wheel}
  music: ch04_mill_repair
  dialogue:
  - 'on': beat_start
    lines: [ch04.b11.genroku.001]
    mode: ambient
  - 'on': progress_at:0.6
    lines: [ch04.b11.genroku.002]
    mode: ambient
  - 'on': progress_at:0.9
    lines: [ch04.b11.genroku.003]
    mode: ambient
  - 'on': beat_complete
    lines: [ch04.b11.otane.004, ch04.b11.nyaakoto.005]
    mode: ambient
- id: ch04.b12
  type: production_task
  task: defend
  place: pl_shimomura
  title_ja: 田植えの列を守れ
  title_en: Guard the planting line
  target_s: 240
  checkpoint: true
  defend:
    targets:
    - {actor: planter_01, hp: 100, downable: true, haul_after_s: 12}
    - {actor: planter_02, hp: 100, downable: true, haul_after_s: 12}
    - {actor: planter_03, hp: 100, downable: true, haul_after_s: 12}
    - {actor: planter_04, hp: 100, downable: true, haul_after_s: 12}
    - {actor: planter_05, hp: 100, downable: true, haul_after_s: 12}
    - {actor: planter_06, hp: 100, downable: true, haul_after_s: 12}
    - {actor: planter_07, hp: 100, downable: true, haul_after_s: 12}
    - {actor: planter_08, hp: 100, downable: true, haul_after_s: 12}
    duration_s: 150
    fail_on_target_destroyed: true
    fail_after_targets_lost: 3
    repair_interact: {kind: net_cut, hold_s: 1.0}
  waves:
  - enemies:
    - {type: drone, count: 3, spawn: sp_paddy_air_e}
    trigger: start
  - enemies:
    - {type: drone, count: 3, spawn: sp_paddy_air_n}
    - {type: enforcer_rifle, count: 2, spawn: sp_far_dike}
    trigger: after_s:40
  - enemies:
    - {type: drone, count: 3, spawn: sp_paddy_air_e}
    - {type: enforcer_rifle, count: 2, spawn: sp_far_dike}
    trigger: after_s:85
  - enemies:
    - {type: drone, count: 3, spawn: sp_paddy_air_n}
    trigger: after_s:120
  max_alive: 6
  allies:
  - {npc: otane, role: kusarigama_melee, downable: true}
  x_weather_events:
  - {at_progress: 0.5, set: sun_shower_off}
  music: ch04_planting_defend
  dialogue:
  - 'on': beat_start
    lines: [ch04.b12.planter.001, ch04.b12.planter.002]
    mode: ambient
  - 'on': progress_at:0.05
    lines: [ch04.b12.otane.003]
    mode: ambient
  - 'on': pattern:net_lock
    lines: [ch04.b12.drone.004]
    mode: ambient
  - 'on': npc_downed:planter_*
    lines: [ch04.b12.planter.005]
    mode: ambient
  - 'on': progress_at:0.5
    lines: [ch04.b12.villager.006]
    mode: ambient
  - 'on': beat_complete
    lines: [ch04.b12.otane.007]
    mode: ambient
- id: ch04.b13
  type: dialogue
  place: pl_shimomura
  title_ja: 生産改帳を開く
  title_en: Open the Production Registry
  target_s: 60
  checkpoint: false
  trigger: beat_start
  mode: blocking
  camera: soft_lookat
  interrupt: queue
  lines:
  - ch04.b13.oyuki.001
  - ch04.b13.oyuki.002
  - ch04.b13.oyuki.003
  - ch04.b13.taemon.004
  - ch04.b13.oyuki.005
  music: ch04_registry
- id: ch04.b14
  type: horseback_ride
  mode: cargo
  place: pl_shimomura
  title_ja: 麦を三つの集落へ
  title_en: Deliver barley to three hamlets
  target_s: 300
  checkpoint: true
  horse: kurimaru
  route: spl_aze_loop
  cargo:
    item: barley_sheaf
    qty: 30
    dropoffs: [hamlet_kami, hamlet_naka, hamlet_shimo]
    per_dropoff: 10
    carrier: pack_horse
    unload_hold_s: 3.0
  gaits: [walk, trot]
  weapons: [0, 18]
  fear: {spook_radius_cm: 900, recover_s: 2.5}
  auto_steer: setting
  dismount_allowed: true
  on_horse_down: dismount_continue
  waves:
  - enemies:
    - {type: enforcer_rifle, count: 2, spawn: sp_toll_post}
    - {type: drone, count: 1, spawn: sp_toll_air}
    trigger: volume_enter:vol_toll_post
  - enemies:
    - {type: drone, count: 2, spawn: sp_canal_air}
    trigger: item_delivered:hamlet_naka
  registry: {item_ja: 麦, item_en: Barley, qty: 30, unit_ja: 束, unit_en: sheaves}
  music: ch04_harvest_ride
  dialogue:
  - 'on': beat_start
    lines: [ch04.b14.otane.001]
    mode: ambient
  - 'on': item_delivered:hamlet_kami
    lines: [ch04.b14.villager.002]
    mode: ambient
  - 'on': idle_s:4
    lines: [ch04.b14.otane.003, ch04.b14.nyaakoto.004]
    mode: ambient
  - 'on': item_delivered:hamlet_naka
    lines: [ch04.b14.villager.005]
    mode: ambient
  - 'on': item_delivered:hamlet_shimo
    lines: [ch04.b14.villager.006]
    mode: ambient
- id: ch04.b15
  type: cinematic
  place: pl_gogura
  title_ja: 秤、現る
  title_en: The Scales Arrive
  target_s: 90
  checkpoint: true
  sequence: /Game/Campaign/Ch04/Cinematics/LS_Ch04_B15_HakariSeizure
  duration_s: 90
  skippable: true
  fallback: camera_blend
  subtitles:
  - {line: ch04.b15.margina.001, t: 22.0}
  - {line: ch04.b15.margina.002, t: 27.5}
  - {line: ch04.b15.margina.003, t: 34.0}
  - {line: ch04.b15.otane.004, t: 48.0}
  - {line: ch04.b15.nyaakoto.005, t: 78.0}
  end_state:
    player_transform: ps_boss_ring_ne_mounted
    equipped: [0, 18]
  music: ch04_hakari_reveal
- id: ch04.b16
  type: boss
  place: pl_shimomura
  title_ja: 査定機「秤」を倒せ
  title_en: Bring down the Assessor Engine
  target_s: 480
  checkpoint: true
  boss: boss_hakari
  arena: {volume: vol_paddies_boss, lock: true}
  phases:
  - hp_pct_start: 100
    pattern_table: hakari_mounted
    adds: drone_release
    mount:
      horse: kurimaru
      route: spl_boss_ring
      weapons: [0, 18]
      gaits: [walk, trot, canter, gallop]
      fear: {spook_radius_cm: 900, recover_s: 2.0}
  - {hp_pct_start: 55, pattern_table: hakari_mill, adds: drone_pair, arena_mod: dismount}
  x_weakpoints:
  - {id: coil_fl, phase: 1, hp: 450, exposed_when: leg_planted}
  - {id: coil_fr, phase: 1, hp: 450, exposed_when: leg_planted}
  - {id: coil_rl, phase: 1, hp: 450, exposed_when: leg_planted}
  - {id: coil_rr, phase: 1, hp: 450, exposed_when: leg_planted}
  - {id: ledger_drum, phase: 2, hp: 2200, exposed_when: assessment_kneel}
  x_ammo_pickups:
  - {at: pk_arrows_se, arrows: 6, respawn_s: 45}
  - {at: pk_arrows_nw, arrows: 6, respawn_s: 45}
  checkpoint_per_phase: true
  defeat: destroy_weakpoints
  outro_cinematic: /Game/Campaign/Ch04/Cinematics/LS_Ch04_B16_HakariCollapse
  telegraph: {palette: default, min_windup_ms: 800}
  barks:
  - {'on': 'pattern:seizure_net', line: ch04.b16.margina.002}
  - {'on': 'pattern:sweep_beam', line: ch04.b16.margina.003}
  - {'on': 'pattern:plant_stomp', line: ch04.b16.margina.004}
  - {'on': 'pattern:drone_release', line: ch04.b16.margina.005}
  - {'on': 'pattern:assessment_kneel', line: ch04.b16.margina.011}
  - {'on': 'pattern:claw_sweep', line: ch04.b16.margina.012}
  fail:
  - {'on': player_died, to: checkpoint}
  - {'on': 'boss_event:mill_seal_3', to: checkpoint}
  music: ch04_boss_hakari
  dialogue:
  - 'on': beat_start
    lines: [ch04.b16.margina.001, ch04.b16.otane.006]
    mode: ambient
  - 'on': pattern:step_plant
    lines: [ch04.b16.kohagi.007]
    mode: ambient
  - 'on': weakpoint_destroyed:coil_*
    lines: [ch04.b16.margina.008]
    mode: ambient
  - 'on': boss_phase:2
    lines: [ch04.b16.margina.009, ch04.b16.otane.010]
    mode: ambient
  - 'on': boss_event:mill_seal
    lines: [ch04.b16.margina.013]
    mode: ambient
  - 'on': player_died
    lines: [ch04.b16.otane.014]
    mode: ambient
  - 'on': beat_complete
    lines: [ch04.b16.margina.015]
    mode: ambient
- id: ch04.b17
  type: production_task
  task: carry
  place: pl_gogura
  title_ja: 麦を郷蔵へ戻せ
  title_en: Return the barley to the granary
  target_s: 150
  checkpoint: true
  site: 2
  carry:
    item: barley_load
    count: 3
    pickups: [pk_hopper_spill_01, pk_hopper_spill_02, pk_hopper_spill_03]
    dropoffs: [dp_gogura_door]
    loadout_while_carrying: [katana_one_hand]
    move_speed_mult: 0.8
    drop_on_hit: false
  waves: []
  registry: {item_ja: 麦（返還）, item_en: Barley returned to growers, qty: 120, unit_ja: 束, unit_en: sheaves}
  music: ch04_return_harvest
  dialogue:
  - 'on': beat_start
    lines: [ch04.b17.oyuki.001]
    mode: ambient
  - 'on': item_delivered:barley_load
    lines: [ch04.b17.villager.002]
    mode: ambient
  - 'on': progress_at:1.0
    lines: [ch04.b17.oyuki.003]
    mode: ambient
  - 'on': beat_complete
    lines: [ch04.b17.taemon.004]
    mode: ambient
- id: ch04.b18
  type: cinematic
  place: pl_shimomura
  title_ja: 蛍
  title_en: Fireflies
  target_s: 120
  checkpoint: false
  sequence: /Game/Campaign/Ch04/Cinematics/LS_Ch04_B18_Fireflies
  duration_s: 120
  skippable: true
  fallback: camera_blend
  subtitles:
  - {line: ch04.b18.otane.001, t: 20.0}
  - {line: ch04.b18.oyuki.002, t: 26.0}
  - {line: ch04.b18.taemon.003, t: 44.0}
  - {line: ch04.b18.kohagi.004, t: 78.0}
  - {line: ch04.b18.nyaakoto.005, t: 86.0}
  end_state:
    player_transform: ps_chapter_end
    equipped: [0, 18]
  music: ch04_dusk_fireflies
collectibles:
- id: ch04.c01
  type: collectible
  collectible_id: ch04.c01
  category: scroll_fragment
  place: pl_tanada
  mask_bit: 0
  codex: {ja: 水月の巻・断簡。「水は器に随いて争わず。されど堰を切れば石をも運ぶ。剣もまた然り。」 石鈴斎の手。, en: 'Moon-in-Water scroll, fragment: ''Water yields to its vessel and does not quarrel. Loose the weir, and it carries stones. So too the
      sword.'' In Sekireisai''s hand.'}
- id: ch04.c02
  type: collectible
  collectible_id: ch04.c02
  category: league_mark
  place: pl_tanada
  mask_bit: 1
  codex: {ja: 小萩の白墨の印。空紋の横に四本の線と矢印。「堤に見張り四。東の石段は見られている。」, en: 'Kohagi''s chalk mark: the Sora mon, four strokes and an arrow. ''Four guards on the dam. The east stair is watched.'''}
- id: ch04.c03
  type: collectible
  collectible_id: ch04.c03
  category: seizure_notice
  place: pl_shimomura
  mask_bit: 2
  codex: {ja: 用水従量課金のお知らせ。「用水は一升ごとに課金されます。未払い分は翌朝の利息に算入いたします。恒星信用院 下村徴収所」, en: 'Notice of metered irrigation: ''Water is billed per measure. Unpaid amounts are added to the next morning''s interest. Stellar
      Credit House, Shimomura Collection Office.'''}
- id: ch04.c04
  type: collectible
  collectible_id: ch04.c04
  category: heirloom
  place: pl_otameike
  mask_bit: 3
  codex: {ja: 番水の割符。上・中・下の垣内が水を回す順を刻んだ木札。天正の頃より三つに割り、一つずつ持ち合った。徴収所に「無効契約」として吊るされていた。, en: 'The water-rotation tally: a wooden board carved with the order in which the three hamlets take the water. Split
      in three since the Tenshō years, one piece per hamlet. Found hung in the guard hut as a ''void contract''.'}
- id: ch04.c05
  type: collectible
  collectible_id: ch04.c05
  category: registry_page
  place: pl_gogura
  mask_bit: 4
  codex: {ja: 郷蔵の納め帳・一葉。去年の麦の納め。束の数の横に、庄屋と年寄の印、そして作り手の爪印。, en: 'A leaf from the granary intake book: last year''s barley. Beside each count, the headman''s and elder''s seals and the grower''s claw-print.'}
- id: ch04.c06
  type: collectible
  collectible_id: ch04.c06
  category: registry_page
  place: pl_shoya_yashiki
  mask_bit: 5
  codex: {ja: 五箇条の下書き。お雪の筆。「利をもって利を生まず」の横に、消された一行。「ただし急ぎの時は」。, en: 'A draft of the five articles in Oyuki''s hand. Beside ''Interest begets no interest'', one line struck out: ''Except in emergencies.'''}
x_boss_patterns:
  boss_id: boss_hakari
  display: {ja: 査定機「秤」, en: Assessor Engine Hakari, pilot: boss_margina}
  hp: 4000
  difficulty_scaling: {easy_windup_mult: 1.3, hard_windup_mult: 0.85}
  hakari_mounted:
  - {id: step_plant, color: none, windup_ms: 0, active_ms: 3000, recovery_ms: 0, cooldown_s: 4.0, effect: one leg plants; its weigh-coil glows and is damageable for 3.0 s, counter: shoot the glowing coil
      (left arc)}
  - {id: seizure_net, color: cyan, windup_ms: 800, active_ms: 400, recovery_ms: 1400, cooldown_s: 9.0, effect: 'net projectile 3500 cm/s, 250 cm radius; roots Kurimaru 2.0 s (rider can still shoot)', counter: change
      gait or direction during the lock tone}
  - {id: sweep_beam, color: cyan, windup_ms: 1100, active_ms: 900, recovery_ms: 1800, cooldown_s: 14.0, effect: '180-degree sweep at 80 cm height, reach 3000 cm, 45 damage and a spook', counter: 'gallop
      out beyond 3000 cm (襲歩, horse stamina)'}
  - {id: plant_stomp, color: amber, windup_ms: 1000, active_ms: 300, recovery_ms: 3500, cooldown_s: 20.0, effect: '600 cm ring, 40 damage, rider thrown if inside; then all four coils glow for the 3.5 s
      recovery', counter: 'leave the ring, then punish the long recovery'}
  - {id: drone_release, color: none, windup_ms: 1200, active_ms: 0, recovery_ms: 800, cooldown_s: 40.0, effect: '2 drones, max 3 alive; a marking drone makes the next seizure_net track the rider through
      its 800 ms windup', counter: shoot or katana-cut the marking drone (its cyan eye) to clear the mark}
  hakari_mill:
  - {id: assessment_kneel, color: cyan, windup_ms: 1500, active_ms: 6000, recovery_ms: 1000, cooldown_s: 22.0, effect: 'kneels at the mill, exposing the ledger drum (x2.5 melee, x1.5 ranged); an assessment
      ring fills over 6 s', counter: deal 250 damage during the kneel to interrupt (2.0 s stagger); otherwise the mill takes 1 seal (3 = fail)}
  - {id: claw_sweep, color: amber, windup_ms: 1000, active_ms: 400, recovery_ms: 1500, cooldown_s: 7.0, effect: '240-degree front arc, 700 cm, 50 damage and knockback; cannot be parried', counter: step
      out of the arc or guard (60% reduction); flank during recovery}
  - {id: seizure_net, color: cyan, windup_ms: 800, active_ms: 400, recovery_ms: 1400, cooldown_s: 10.0, effect: roots the player 1.5 s, counter: sidestep during the lock tone}
  - {id: sweep_beam, color: cyan, windup_ms: 1100, active_ms: 900, recovery_ms: 1800, cooldown_s: 16.0, effect: 'head turret sweep at 80 cm, reach 1800 cm on foot', counter: crouch behind the mill footing
      or millrace wall (stone blocks the beam) or leave range}
  hakari_mill_revaluation_at_hp_pct: 25
  revaluation_mods: {assessment_kneel.active_ms: 4500, sweep_beam.windup_ms: 950, claw_sweep.windup_ms: 850}
  adds:
    drone_release: see pattern
    drone_pair: {type: drone, count: 2, respawn_after_clear_s: 30}
  defeat: destroy_weakpoints
  fate: collapses into the paddy; Margina ejects and flees
lines:
- {id: ch04.b01.taemon.001, speaker: farmer, register: yamato_elder, mode: cinematic, ja: 水車を奪われた。稲はまだ芽も出ていないのに。, en: They took the pumps before the rice had even sprouted., duration_s: 5.0, repeatable: false}
- {id: ch04.b01.taemon.002, speaker: farmer, register: yamato_elder, mode: cinematic, ja: 溜池には封を貼られてな。水は升で量り売りや。, en: They sealed the reservoir. Now water is sold by the measure., duration_s: 5.5, repeatable: false}
- {id: ch04.b01.oyuki.003, speaker: leader, register: business_keigo, mode: cinematic, ja: 青田買い、でございます。植える前の稲を「買う」のです。, en: It is aotagai. They 'buy' the rice before it is planted., duration_s: 5.0, repeatable: false}
- {id: ch04.b01.oyuki.004, speaker: leader, register: business_keigo, mode: cinematic, ja: 代金は「信用」、つまり借りです。利息は実りより速く増えます。, en: 'Paid in ''Credit'', which is to say debt. The interest outgrows any harvest.',
  duration_s: 5.5, repeatable: false}
- {id: ch04.b01.otane.005, speaker: farmer_young, register: kamigata_bright, mode: cinematic, ja: 田植えは今しかあらへん。水が来な、苗は十日で枯れる。, en: 'It''s planting now or never. No water, and the seedlings die in ten days.',
  duration_s: 5.0, repeatable: false}
- {id: ch04.b01.nyaakoto.006, speaker: samurai, register: samurai_restrained, mode: cinematic, ja: 堰は、どこに。, en: 'Where is the weir?', duration_s: 1.5, repeatable: false}
- {id: ch04.b01.taemon.007, speaker: farmer, register: yamato_elder, mode: cinematic, ja: 大溜池の、一の堰や。爺さまの代から、皆で分けてきた水や。, en: 'The First Weir, up at the Great Reservoir. We''ve shared it since Grandad''s
    day.', duration_s: 7.0, repeatable: false}
- {id: ch04.b01.otane.008, speaker: farmer_young, register: kamigata_bright, mode: cinematic, ja: 案内したる。馬で通れる土手は、限られとるで。, en: I'll show you. Only some banks will take a horse., duration_s: 4.5, repeatable: false}
- {id: ch04.b02.otane.001, speaker: farmer_young, register: kamigata_bright, mode: ambient, ja: 畦は細いで、馬は無理や。土手道だけ通ってな。, en: The paddy ridges are too narrow for horses. Keep to the bank roads., duration_s: 4.5,
  repeatable: false}
- {id: ch04.b02.otane.002, speaker: farmer_young, register: kamigata_bright, mode: ambient, ja: 'あの杭、見える？　水を量る杭や。一升ごとに戸口の数字が増える。', en: 'See that post? It meters the water. Every measure adds to the number
    on our doors.', duration_s: 6.0, repeatable: false}
- {id: ch04.b02.otane.003, speaker: farmer_young, register: kamigata_bright, mode: ambient, ja: 麦はもう刈り頃や。刈ったそばから「徴収」や。, en: The barley's ready to cut. They 'collect' it as fast as we cut it., duration_s: 4.5,
  repeatable: false}
- {id: ch04.b02.nyaakoto.004, speaker: samurai, register: samurai_restrained, mode: ambient, ja: 見張りは、いくつだ。, en: 'How many guards?', duration_s: 2.5, repeatable: false}
- {id: ch04.b02.otane.005, speaker: farmer_young, register: kamigata_bright, mode: ambient, ja: 麦畑に八つか九つ。空に「目録」が二つ。, en: Eight or nine in the barley. Two 'Inventories' in the sky., duration_s: 4.0, repeatable: false}
- {id: ch04.b02.otane.006, speaker: farmer_young, register: kamigata_bright, mode: ambient, ja: 去年の今ごろは、田植え歌がここまで聞こえとった。, en: 'This time last year, you could hear the planting songs from here.', duration_s: 4.5,
  repeatable: false}
- {id: ch04.b03.tetsugoro.001, speaker: gunsmith, register: blunt_artisan, mode: ambient, ja: 田右衛門の鳥威しだ。筒は生きとった。, en: Taemon's crow-scaring gun. The barrel was still sound., duration_s: 4.0, repeatable: false}
- {id: ch04.b03.tetsugoro.002, speaker: gunsmith, register: blunt_artisan, mode: blocking, ja: 尾栓に、奴らのコイルを噛ませた。, en: I fitted one of their coils into the breech., duration_s: 3.5, repeatable: false}
- {id: ch04.b03.tetsugoro.003, speaker: gunsmith, register: blunt_artisan, mode: ambient, ja: 雨で火縄が死ぬんなら、火縄をやめりゃええ。, en: 'If rain kills the match, stop using a match.', duration_s: 4.0, repeatable: false}
- {id: ch04.b03.tetsugoro.004, speaker: gunsmith, register: blunt_artisan, mode: ambient, ja: 頬に付けて撃て。肩には当てるな。, en: Stock to your cheek. Not your shoulder., duration_s: 3.5, repeatable: false}
- {id: ch04.b03.tetsugoro.005, speaker: gunsmith, register: blunt_artisan, mode: ambient, ja: 早合を込めて、カチッと鳴ったら締めろ。, en: 'Load the hayagō. When it clicks, lock it.', duration_s: 4.0, repeatable: false}
- {id: ch04.b03.otane.006, speaker: farmer_young, register: kamigata_bright, mode: blocking, ja: これ、兄やんの鎖鎌。持っとき。うちのは、こっちや。, en: This is my brother's kusarigama. Keep it. I've got my own., duration_s: 4.5,
  repeatable: false}
- {id: ch04.b03.nyaakoto.007, speaker: samurai, register: samurai_restrained, mode: ambient, ja: ……お借りする。, en: …Then I will borrow it., duration_s: 2.0, repeatable: false}
- {id: ch04.b03.otane.008, speaker: farmer_young, register: kamigata_bright, mode: ambient, ja: 借りやない。預けるんや。兄やんを取り返すまで。, en: It's not a loan. I'm trusting it to you. Until we get my brother back., duration_s: 5.0,
  repeatable: false}
- {id: ch04.b04.otane.001, speaker: farmer_young, register: kamigata_bright, mode: ambient, ja: 来たで。麦の中や。……向こうも、こっちが見えてへん。, en: 'Here they come, through the barley. …They can''t see us either.', duration_s: 5.0,
  repeatable: false}
- {id: ch04.b04.otane.002, speaker: farmer_young, register: kamigata_bright, mode: ambient, ja: 分銅を投げて！　刃ぁ絡めたら、こっちのもんや！, en: Throw the weight! Snag the blade and they're ours!, duration_s: 4.0, repeatable: false}
- {id: ch04.b04.enforcer.003, speaker: enforcer, register: alien_corporate_keigo, mode: ambient, ja: 債務者を確認。回収を開始いたします。, en: Debtor identified. Commencing collection., duration_s: 4.5, repeatable: true}
- {id: ch04.b04.enforcer.004, speaker: enforcer, register: alien_corporate_keigo, mode: ambient, ja: 対象を見失いました。当該区画を精査いたします。, en: Target lost. Auditing this sector., duration_s: 5.5, repeatable: true}
- {id: ch04.b04.enforcer.005, speaker: enforcer, register: alien_corporate_keigo, mode: ambient, ja: 損失が許容範囲を超過。撤収いたします。, en: Losses exceed tolerance. Withdrawing., duration_s: 5.0, repeatable: true}
- {id: ch04.b04.drone.006, speaker: drone, register: alien_machine, mode: ambient, ja: 差押え対象を記録。, en: Seizure target logged., duration_s: 2.5, repeatable: true}
- {id: ch04.b04.otane.007, speaker: farmer_young, register: kamigata_bright, mode: ambient, ja: 足、取られた……！　起こして！, en: They got my leg…! Get me up!, duration_s: 3.0, repeatable: false}
- {id: ch04.b04.otane.008, speaker: farmer_young, register: kamigata_bright, mode: ambient, ja: ……麦、踏まれてもうた。まあ、麦は起きる。, en: …They trampled the barley. Well—barley stands back up., duration_s: 4.0, repeatable: false}
- {id: ch04.b05.kohagi.001, speaker: scout, register: terse, mode: ambient, ja: 堤の上に四。首輪つき。水の上に目録が一。, en: Four on the dam. Collared. One Inventory over the water., duration_s: 5.0, repeatable: false}
- {id: ch04.b05.kohagi.002, speaker: scout, register: terse, mode: ambient, ja: 首輪の者は斬らないで。峰で。, en: Don't cut the collared ones. Use the back of the blade., duration_s: 4.0, repeatable: false}
- {id: ch04.b05.conscript.003, speaker: conscript, register: yamato_rural_distressed, mode: ambient, ja: ……首輪が熱い。日が高うなると、焼けるようや。, en: '…The collar''s hot. Once the sun''s high, it burns.', duration_s: 4.5,
  repeatable: true}
- {id: ch04.b05.conscript.004, speaker: conscript, register: yamato_rural_distressed, mode: ambient, ja: '誰や……？　誰か、おるんか。', en: 'Who''s that…? Someone there?', duration_s: 3.0, repeatable: true}
- {id: ch04.b05.conscript.005, speaker: conscript, register: yamato_rural_distressed, mode: ambient, ja: 頼む、出てこんといてくれ。見つけたら、報せなあかんのや。, en: 'Please, stay hidden. If I find you, I have to report it.', duration_s: 5.0,
  repeatable: true}
- {id: ch04.b05.conscript.006, speaker: conscript, register: yamato_rural_distressed, mode: ambient, ja: すまん！　見つけてもうた！　首輪が勝手に叫ぶんや！, en: Sorry! I found you! The collar cries out on its own!, duration_s: 4.5,
  repeatable: true}
- {id: ch04.b05.drone.007, speaker: drone, register: alien_machine, mode: ambient, ja: 動体を検知。照合中。, en: Movement detected. Reconciling., duration_s: 3.0, repeatable: true}
- {id: ch04.b05.yosaku.008, speaker: yosaku, register: yamato_rural_distressed, mode: ambient, ja: ……お種の兄の、与作や。恩に着る。, en: '…I''m Yosaku, Otane''s brother. I owe you.', duration_s: 4.0, repeatable: false}
- {id: ch04.b05.kohagi.009, speaker: scout, register: terse, mode: ambient, ja: 堤、抜けた。巻き上げは、そこ。, en: Dam's clear. The winch is there., duration_s: 3.5, repeatable: false}
- {id: ch04.b06.otane.001, speaker: farmer_young, register: kamigata_bright, mode: ambient, ja: 封されてから一度も回ってへん。重いで。速すぎたら綱が切れる。, en: Hasn't turned since they sealed it. It's heavy. Too fast and the rope
    snaps., duration_s: 5.5, repeatable: false}
- {id: ch04.b06.taemon.002, speaker: farmer, register: yamato_elder, mode: ambient, ja: ほんまに水、戻るんか。戻ったかて、また取られるんやないか。, en: 'Will the water really come back? And won''t they just take it again?', duration_s: 6.0,
  repeatable: false}
- {id: ch04.b06.nyaakoto.003, speaker: samurai, register: samurai_restrained, mode: ambient, ja: 水を戻す。収穫は育てた者に渡そう。, en: We will restore the water. The harvest will go to those who grew it., duration_s: 5.0,
  repeatable: false}
- {id: ch04.b06.enforcer.004, speaker: enforcer, register: alien_corporate_keigo, mode: ambient, ja: 無許可の取水を確認。延滞金が加算されます。, en: Unauthorized intake detected. Late fees will be applied., duration_s: 5.5,
  repeatable: false}
- {id: ch04.b06.conscript.005, speaker: conscript, register: yamato_rural_distressed, mode: ambient, ja: 首輪の光が……消えた。, en: The collar's light… it's gone out., duration_s: 2.5, repeatable: false}
- {id: ch04.b06.taemon.006, speaker: farmer, register: yamato_elder, mode: ambient, ja: ……水の音や。, en: …That's the sound of water., duration_s: 2.0, repeatable: false}
- {id: ch04.b07.otane.001, speaker: farmer_young, register: kamigata_bright, mode: ambient, ja: 堰板が上がりきるまで、ここを守るで！, en: Hold here until the gate boards are all the way up!, duration_s: 3.5, repeatable: false}
- {id: ch04.b07.enforcer.002, speaker: enforcer, register: alien_corporate_keigo, mode: ambient, ja: 盾列、前進。担保を保全いたします。, en: 'Shield line, advance. Securing the collateral.', duration_s: 4.5, repeatable: false}
- {id: ch04.b07.otane.003, speaker: farmer_young, register: kamigata_bright, mode: ambient, ja: 盾は前だけや！　横から絡めたれ！, en: Shields only cover the front! Snag them from the side!, duration_s: 4.0, repeatable: false}
- {id: ch04.b07.taemon.004, speaker: farmer, register: yamato_elder, mode: ambient, ja: 水位、あと半分や！　踏ん張れ！, en: Halfway there! Hold on!, duration_s: 4.0, repeatable: false}
- {id: ch04.b07.enforcer.005, speaker: enforcer, register: alien_corporate_keigo, mode: ambient, ja: 採算が合いません。後退いたします。, en: This is no longer profitable. Falling back., duration_s: 4.0, repeatable: true}
- {id: ch04.b07.taemon.006, speaker: farmer, register: yamato_elder, mode: ambient, ja: 溢れる……！　田に、水が入る！, en: It's spilling over…! Water's reaching the fields!, duration_s: 3.5, repeatable: false}
- {id: ch04.b08.taemon.001, speaker: farmer, register: yamato_elder, mode: cinematic, ja: 水はな、借りるもんやない。上から下へ、皆に回るもんや。, en: 'Water isn''t something you borrow. It runs downhill, round to everyone.', duration_s: 6.0,
  repeatable: false}
- {id: ch04.b08.villager.002, speaker: villager, register: yamato_rural, mode: cinematic, ja: 水や……！　水が来たで！, en: Water…! The water's here!, duration_s: 3.0, repeatable: false}
- {id: ch04.b08.otane.003, speaker: farmer_young, register: kamigata_bright, mode: cinematic, ja: 早乙女、呼んできて！　今日のうちに植えるで！, en: Call the planters! We plant today!, duration_s: 4.0, repeatable: false}
- {id: ch04.b09.villager.001, speaker: villager, register: yamato_rural, mode: ambient, ja: 水分の神さんはな、水を分ける神さんや。独り占めはなさらん。, en: Mikumari is the god who divides the water. Never hoards it., duration_s: 6.0,
  repeatable: false}
- {id: ch04.b09.villager.002, speaker: villager, register: yamato_rural, mode: ambient, ja: 猫柳生の先生も、昔はようお参りに来はった。, en: 'Your old sensei used to come up here to pray, years ago.', duration_s: 4.5, repeatable: false}
- {id: ch04.b09.nyaakoto.003, speaker: samurai, register: samurai_restrained, mode: ambient, ja: ……屋敷が、見える。, en: …I can see the estate from here., duration_s: 2.5, repeatable: false}
- {id: ch04.b10.genroku.001, speaker: carpenter, register: kamigata_artisan, mode: ambient, ja: 牛は急かしたらあかん。牛の足で行くで。, en: Don't rush the ox. We go at the ox's pace., duration_s: 4.0, repeatable: false}
- {id: ch04.b10.genroku.002, speaker: carpenter, register: kamigata_artisan, mode: ambient, ja: 羽根板六枚に、心棒一本。濡らしたらあかんで。, en: 'Six paddles, one axle. They mustn''t get wet.', duration_s: 5.0, repeatable: false}
- {id: ch04.b10.enforcer.003, speaker: enforcer, register: alien_corporate_keigo, mode: ambient, ja: 搬送中の資産を確認。差し押さえます。, en: Assets in transit identified. Seizing them., duration_s: 4.5, repeatable: false}
- {id: ch04.b10.nyaakoto.004, speaker: samurai, register: samurai_restrained, mode: ambient, ja: 伏せろ。, en: Get down., duration_s: 1.5, repeatable: true}
- {id: ch04.b10.otane.005, speaker: farmer_young, register: kamigata_bright, mode: ambient, ja: ……狐の嫁入りや。日ぃ照っとんのに。, en: 'A fox''s wedding. Rain, with the sun still out.', duration_s: 3.5, repeatable: false}
- {id: ch04.b10.genroku.006, speaker: carpenter, register: kamigata_artisan, mode: ambient, ja: 言うたそばから！　板に蓑、掛けたって！, en: Of course it rains now! Get the straw capes over the boards!, duration_s: 4.0, repeatable: false}
- {id: ch04.b11.genroku.001, speaker: carpenter, register: kamigata_artisan, mode: ambient, ja: 羽根板は一枚ずつ。楔は二度打ちや。, en: One paddle at a time. Two strikes on each wedge., duration_s: 4.0, repeatable: false}
- {id: ch04.b11.genroku.002, speaker: carpenter, register: kamigata_artisan, mode: ambient, ja: 心棒、据えるで。息、合わせてや。……せえの！, en: Seating the axle. Breathe with me… Heave!, duration_s: 5.0, repeatable: false}
- {id: ch04.b11.genroku.003, speaker: carpenter, register: kamigata_artisan, mode: ambient, ja: よっしゃ。歯止め、外してみい。, en: Right. Go on—release the brake., duration_s: 3.5, repeatable: false}
- {id: ch04.b11.otane.004, speaker: farmer_young, register: kamigata_bright, mode: ambient, ja: 回った……！　樋に水が上がる！, en: It's turning…! Water's climbing into the flume!, duration_s: 3.5, repeatable: false}
- {id: ch04.b11.nyaakoto.005, speaker: samurai, register: samurai_restrained, mode: ambient, ja: 水車にも、紋を。, en: 'Paint the mon on the wheel, too.', duration_s: 2.5, repeatable: false}
- {id: ch04.b12.planter.001, speaker: planter, register: work_song, mode: ambient, ja: 〽今日植える苗は　秋には黄金, en: ♪ The seedlings we plant today / turn to gold by autumn, duration_s: 5.5, repeatable: true}
- {id: ch04.b12.planter.002, speaker: planter, register: work_song, mode: ambient, ja: 〽水は上から　皆の田へ, en: ♪ Water from above / to everyone's fields, duration_s: 4.0, repeatable: true}
- {id: ch04.b12.otane.003, speaker: farmer_young, register: kamigata_bright, mode: ambient, ja: 網が来る！　早乙女を守って！, en: Nets incoming! Protect the planters!, duration_s: 3.0, repeatable: false}
- {id: ch04.b12.drone.004, speaker: drone, register: alien_machine, mode: ambient, ja: 労働資産を差し押さえます。, en: Seizing labor assets., duration_s: 3.0, repeatable: true}
- {id: ch04.b12.planter.005, speaker: planter, register: work_song, mode: ambient, ja: 網や……！　動かれへん！, en: A net…! I can't move!, duration_s: 4.0, repeatable: true}
- {id: ch04.b12.villager.006, speaker: villager, register: yamato_rural, mode: ambient, ja: あかん、火縄が湿気てもうた！　お侍、その鉄砲は撃てるんか！, en: 'No good, my match is soaked! Samurai—does yours still fire?', duration_s: 6.0,
  repeatable: false}
- {id: ch04.b12.otane.007, speaker: farmer_young, register: kamigata_bright, mode: ambient, ja: ……植わった。一列、全部。, en: …Planted. The whole line., duration_s: 3.0, repeatable: false}
- {id: ch04.b13.oyuki.001, speaker: leader, register: business_keigo, mode: blocking, ja: 生産改帳、本日より付けます。まずは、これまでの分から。, en: 'The production registry begins today. First, what came before.', duration_s: 5.5,
  repeatable: false}
- {id: ch04.b13.oyuki.002, speaker: leader, register: business_keigo, mode: blocking, ja: 矢十二本、種籾四俵、提灯四十張。, en: Twelve arrows. Four bales of seed rice. Forty lanterns., duration_s: 4.0, repeatable: false}
- {id: ch04.b13.oyuki.003, speaker: leader, register: business_keigo, mode: blocking, ja: そして本日、用水十二枚、水車一基。, en: 'And today: water for twelve paddies. One waterwheel.', duration_s: 4.0, repeatable: false}
- {id: ch04.b13.taemon.004, speaker: farmer, register: yamato_elder, mode: ambient, ja: 紙は紙や。, en: Paper is paper., duration_s: 1.5, repeatable: false}
- {id: ch04.b13.oyuki.005, speaker: leader, register: business_keigo, mode: ambient, ja: ええ。ですから、紙には、在る物しか書きません。, en: Indeed. That is why paper records only what exists., duration_s: 4.5, repeatable: false}
- {id: ch04.b14.otane.001, speaker: farmer_young, register: kamigata_bright, mode: ambient, ja: 文太は臆病やで。青い光に寄せたら暴れる。, en: Bunta scares easily. Keep her clear of the blue light., duration_s: 4.0, repeatable: false}
- {id: ch04.b14.villager.002, speaker: villager, register: yamato_rural, mode: ambient, ja: 麦や……！　上垣内に、麦が戻った！, en: Barley…! Barley's back in the upper hamlet!, duration_s: 4.0, repeatable: false}
- {id: ch04.b14.otane.003, speaker: farmer_young, register: kamigata_bright, mode: ambient, ja: その馬、麦で動くんか。, en: 'Does that horse run on barley?', duration_s: 2.5, repeatable: false}
- {id: ch04.b14.nyaakoto.004, speaker: samurai, register: samurai_restrained, mode: ambient, ja: ……麦で動く。, en: …She runs on barley., duration_s: 2.0, repeatable: false}
- {id: ch04.b14.villager.005, speaker: villager, register: yamato_rural, mode: ambient, ja: これで子らに食わせられる。おおきに。, en: Now I can feed the children. Thank you., duration_s: 3.5, repeatable: false}
- {id: ch04.b14.villager.006, speaker: villager, register: yamato_rural, mode: ambient, ja: 下垣内まで、来てくれはったんか。, en: 'You came all the way down to the lower hamlet?', duration_s: 3.5, repeatable: false}
- {id: ch04.b15.margina.001, speaker: boss_margina, register: alien_corporate_keigo, mode: cinematic, ja: 下村の皆様。査定の結果が出ました。, en: Residents of Shimomura. The assessment is complete., duration_s: 4.5, repeatable: false}
- {id: ch04.b15.margina.002, speaker: boss_margina, register: alien_corporate_keigo, mode: cinematic, ja: 当区画の収穫は、全て担保として差し押さえます。, en: All harvest in this sector is seized as collateral., duration_s: 5.5,
  repeatable: false}
- {id: ch04.b15.margina.003, speaker: boss_margina, register: alien_corporate_keigo, mode: cinematic, ja: ご異議は書面にて。受付は、秋でございます。, en: Objections are accepted in writing. The office opens in autumn., duration_s: 5.0,
  repeatable: false}
- {id: ch04.b15.otane.004, speaker: farmer_young, register: kamigata_bright, mode: cinematic, ja: 郷蔵の麦が……！　皆の麦が！, en: The granary barley…! Everyone's barley!, duration_s: 3.0, repeatable: false}
- {id: ch04.b15.nyaakoto.005, speaker: samurai, register: samurai_restrained, mode: cinematic, ja: 栗丸。……行くぞ。, en: Kurimaru. …We ride., duration_s: 2.5, repeatable: false}
- {id: ch04.b16.margina.001, speaker: boss_margina, register: alien_corporate_keigo, mode: ambient, ja: 査定を開始いたします。動かないでください。値が狂います。, en: Commencing assessment. Please hold still. Movement distorts the
    value., duration_s: 6.0, repeatable: false}
- {id: ch04.b16.margina.002, speaker: boss_margina, register: alien_corporate_keigo, mode: ambient, ja: 差押え網、展開。, en: Deploying seizure net., duration_s: 2.5, repeatable: true}
- {id: ch04.b16.margina.003, speaker: boss_margina, register: alien_corporate_keigo, mode: ambient, ja: 査定中……評価額、零。, en: 'Assessing… Value: zero.', duration_s: 3.5, repeatable: true}
- {id: ch04.b16.margina.004, speaker: boss_margina, register: alien_corporate_keigo, mode: ambient, ja: 計量。, en: Weighing., duration_s: 1.5, repeatable: true}
- {id: ch04.b16.margina.005, speaker: boss_margina, register: alien_corporate_keigo, mode: ambient, ja: 目録、放出。, en: Releasing Inventory., duration_s: 2.0, repeatable: true}
- {id: ch04.b16.otane.006, speaker: farmer_young, register: kamigata_bright, mode: ambient, ja: 左回りや！　相手をずっと左に置いて射るんや！, en: Circle left! Keep it on your left and shoot!, duration_s: 4.0, repeatable: false}
- {id: ch04.b16.kohagi.007, speaker: scout, register: terse, mode: ambient, ja: 脚の環が光った。踏んだ時だけ。, en: Leg ring's glowing. Only when it plants., duration_s: 3.5, repeatable: false}
- {id: ch04.b16.margina.008, speaker: boss_margina, register: alien_corporate_keigo, mode: ambient, ja: 秤に誤差。……許容外です。, en: Scale error. …Outside tolerance., duration_s: 3.5, repeatable: true}
- {id: ch04.b16.margina.009, speaker: boss_margina, register: alien_corporate_keigo, mode: ambient, ja: 再評価いたします。……水車小屋に、担保価値あり。, en: Revaluing. …The mill has collateral value., duration_s: 6.0, repeatable: false}
- {id: ch04.b16.otane.010, speaker: farmer_young, register: kamigata_bright, mode: ambient, ja: 水車の前で膝ついた！　腹の太鼓、叩き斬ったれ！, en: It's kneeling at the mill! Cut the drum in its belly!, duration_s: 4.5, repeatable: false}
- {id: ch04.b16.margina.011, speaker: boss_margina, register: alien_corporate_keigo, mode: ambient, ja: 担保価値を、算定中。, en: Calculating collateral value., duration_s: 3.0, repeatable: true}
- {id: ch04.b16.margina.012, speaker: boss_margina, register: alien_corporate_keigo, mode: ambient, ja: 減価償却。, en: Depreciation., duration_s: 1.5, repeatable: true}
- {id: ch04.b16.margina.013, speaker: boss_margina, register: alien_corporate_keigo, mode: ambient, ja: 一件、差押え完了。, en: One item seized., duration_s: 2.5, repeatable: true}
- {id: ch04.b16.otane.014, speaker: farmer_young, register: kamigata_bright, mode: ambient, ja: 立って！　まだ終わってへん！, en: Get up! It's not over!, duration_s: 2.5, repeatable: true}
- {id: ch04.b16.margina.015, speaker: boss_margina, register: alien_corporate_keigo, mode: cinematic, ja: ……損切りいたします。, en: …I am cutting my losses., duration_s: 2.5, repeatable: false}
- {id: ch04.b17.oyuki.001, speaker: leader, register: business_keigo, mode: ambient, ja: 郷蔵へ運びましょう。どの田の麦か、札を付けてくださいませ。, en: Let us take it to the granary. Tag each load with its field., duration_s: 5.5,
  repeatable: false}
- {id: ch04.b17.villager.002, speaker: villager, register: yamato_rural, mode: ambient, ja: うちの麦や。……ほんまに、うちの麦や。, en: It's our barley. …It really is ours., duration_s: 4.0, repeatable: false}
- {id: ch04.b17.oyuki.003, speaker: leader, register: business_keigo, mode: ambient, ja: 麦、百二十束。育てた者の名と共に、記しました。, en: 'Barley, 120 sheaves. Recorded with the names of those who grew it.', duration_s: 5.0,
  repeatable: false}
- {id: ch04.b17.taemon.004, speaker: farmer, register: yamato_elder, mode: ambient, ja: ならば、皆で食べられるだけ作ろう。, en: Then we will grow enough for everyone to eat., duration_s: 3.5, repeatable: false}
- {id: ch04.b18.otane.001, speaker: farmer_young, register: kamigata_bright, mode: cinematic, ja: うちも入れて。空紋の一揆に。, en: Count me in. The Sora League., duration_s: 3.0, repeatable: false}
- {id: ch04.b18.oyuki.002, speaker: leader, register: business_keigo, mode: cinematic, ja: 歓迎いたします。……一名、確かに記しました。, en: 'Welcome. …One member, duly recorded.', duration_s: 4.5, repeatable: false}
- {id: ch04.b18.taemon.003, speaker: farmer, register: yamato_elder, mode: cinematic, ja: 蛍が出たら、田はもう大丈夫や。, en: 'When the fireflies come out, the fields will be fine.', duration_s: 4.0, repeatable: false}
- {id: ch04.b18.kohagi.004, speaker: scout, register: terse, mode: cinematic, ja: 尾根に一騎。……黒鹿毛。, en: One rider on the ridge. …A black-bay., duration_s: 3.5, repeatable: false}
- {id: ch04.b18.nyaakoto.005, speaker: samurai, register: samurai_restrained, mode: cinematic, ja: ……虎之介。, en: …Toranosuke., duration_s: 2.0, repeatable: false}
ui_prompts:
- {id: ui.ch04.b02.bank_roads, beat: ch04.b02, "on": beat_start, ja: 畦は馬で通れない。土手道を進め, en: Horses cannot use paddy ridges. Keep to the bank roads.}
- {id: ui.ch04.b03.hayago, beat: ch04.b03, "on": after weapon 5 unlock, ja: '{Reload}で早合を込める。カチッと鳴った瞬間にもう一度{Reload}で素早く締める', en: '{Reload} loads a hayagō. Press {Reload} again on the click to lock it faster.'}
- {id: ui.ch04.b03.cheek, beat: ch04.b03, "on": first aim with weapon 5, ja: 頬付けで構える。馬上では鉄砲を使えない, en: Cheek-stocked aim. Firearms cannot be used on horseback.}
- {id: ui.ch04.b04.bind, beat: ch04.b04, "on": 'progress_at:0.15', ja: '鎖鎌の分銅は刃・盾・目録を絡め取る', en: 'The kusarigama weight snares a blade, shield or drone.'}
- {id: ui.ch04.b04.barley, beat: ch04.b04, "on": beat_start, ja: 高い麦の中では互いに見えにくい。揺れる穂に注意, en: In tall barley no one sees far. Watch for swaying heads.}
- {id: ui.ch04.b05.nonlethal, beat: ch04.b05, "on": beat_start, ja: '首輪の者は峰打ちで倒し、{Interact}長押しで首輪を断つ', en: 'Subdue the collared with the back of the blade, then hold {Interact} to cut the collar.'}
- {id: ui.ch04.b06.crank, beat: ch04.b06, "on": beat_start, ja: '{Interact}を一定の調子で押して巻き上げる。速さを帯の中に保て', en: 'Press {Interact} at a steady pace to crank. Keep your speed inside the band.'}
- {id: ui.ch04.b07.hold, beat: ch04.b07, "on": beat_start, ja: 堰の周りに留まれ。敵が入ると水位が止まる, en: Stay by the weir. Enemies inside stop the water rising.}
- {id: ui.ch04.b10.signal, beat: ch04.b10, "on": beat_start, ja: '同行者はあなたがそばにいる間だけ進む', en: 'The escort moves on only while you stay close.'}
- {id: ui.ch04.b12.net, beat: ch04.b12, "on": first npc_downed, ja: '網に捕らわれた者は{Interact}で解放。12秒で連れ去られる', en: '{Interact} to free netted planters. They are taken after 12 s.'}
- {id: ui.ch04.b13.registry, beat: ch04.b13, "on": beat_complete, ja: '生産改帳が開いた。{Menu}からいつでも見られる', en: 'The registry is open. View it any time from {Menu}.'}
- {id: ui.ch04.b14.pack, beat: ch04.b14, "on": beat_start, ja: 荷を積んだ駄馬がいる間は常歩と速歩のみ, en: While leading a laden pack horse you can only walk or trot.}
- {id: ui.ch04.b16.ccw, beat: ch04.b16, "on": beat_start, ja: 左回りに走り、敵を弓手（左）に置け, en: Circle left to keep the target on your bow side.}
- {id: ui.ch04.b16.coils, beat: ch04.b16, "on": first step_plant, ja: 脚の秤環は踏み込んだ時だけ光る, en: Leg coils glow only while that leg is planted.}
- {id: ui.ch04.b16.drum, beat: ch04.b16, "on": 'boss_phase:2', ja: 膝をついた時、腹の帳簿胴を斬れ, en: 'When it kneels, strike the ledger drum.'}
```
