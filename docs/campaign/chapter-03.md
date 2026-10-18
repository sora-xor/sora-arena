# 第三章 占領された街 / Chapter 3: Occupied Streets

> **Monetary boundary (bible §2).** In this chapter, as in the whole campaign, SORA XOR (and the registry that leads to it) is a production-only storytelling premise. XOR is cut only against finished, inspected goods, is never shown as a balance or converted, and has no link to multiplayer XOR bonds, NFTs, wallets or IrohaConnect. It makes no claim about real-world money, investment or policy, and it does not describe the real SORA network or the design in the SORA Nexus article. **Review note (C1 lead, 2026-09-25):** names, calendar, speaker ids, Japanese punctuation and YAML field names in this file follow bible §9.1, §12.5 and §18.

**Chapter id:** `ch03_lantern_ward` · **Map:** arena 1 (Lantern Ward) plus campaign-only sublevels · **Target:** 55 min

**Status:** production design and script for C4 (the ch03 mission). It hands off to L1 (beats, saves, dialogue data), L2 (enemies and stealth), L3 (Penalta), L4 (prompts and HUD), L5 (music and barks), C2/C3 (spaces) and C9 (cinematics).

The chapter follows the [story bible](story-bible.md) and changes none of its fixed numbers:
- 55 min over 18 beats;
- weapons 4 and 7;
- the boss `boss_penalta`;
- sites 0–2 at b05, b09 and b14, in catalog order;
- the three catalog anchor lines at b02, b06 and b18.

Everything else here is a **proposal** for the owning lane: layout dimensions, patrol timings, detection values, boss numbers, speaker ids and `x_`-prefixed fields. Native Japanese review (B7) and historian and practitioner review are still pending, and no VO has been recorded.

**Related sources:** [story bible](story-bible.md) §§3, 4, 7, 8, 13–19 · [catalog.json](../../Content/Data/catalog.json) (chapter index 2) · [historical arms](../historical-arms.md) · [SORA kamon runtime art](../sora-kamon-runtime-art.md) · [photoreal acceptance](../art-direction/photoreal-acceptance.md)

| At a glance | |
|---|---|
| Target time | 55 min (3300 s) on 真剣 (Normal). The beat `target_s` values sum exactly to the bible budget. |
| Beats | 18, plus 6 passive collectibles (not counted) |
| Mix (minutes) | Combat 14 · Explore 3 · Stealth 12 · Production 15 · Mounted 0 · Cinematic and dialogue 11 |
| Weapons unlocked | **4 脇差 Wakizashi** (b01) · **7 擲弾筒 Grenade Launcher** (b09) |
| Mechanic flags | `stealth` (b02) · `takedown`, `seal_cut` (b03) |
| Also taught | Light, noise and puddles; alert states; 峰打ち; escort with hide-on-signal (b07); arcing explosives (b08 enemy, b09 player) |
| Boss | `boss_penalta`, 取立頭 ペナルタ, Enforcer-Chief Penalta (b17), shield bruiser in 2 phases |
| Production sites | 0 道具の隠し場 (b05) · 1 提灯の工房 (b09) · 2 共同の炊き出し (b14) |
| Registry page | 提灯 40張 · 炊き出し 120食 |
| Dialogue | 143 lines: 117 story lines and 26 repeatable barks; about 7.9 min of VO |
| Horse | None (no mounted beats in ch03) |

---

## 1. Synopsis, play time, time of day and locations

### 1.1 Synopsis

Ten days after the sky split, the long rains of early summer have set in: 卯の花腐し (unohana-kutashi), the fourth-month rains that come weeks before the 五月雨 proper (bible §9.1). The Stellar Credit House governs the castle town of Nekoyama by arithmetic. In its Lantern Ward every door glows with a cyan balance that grows overnight, and every flame needs a licence, so the ward named for its lanterns sits in the dark. Kohagi poles a riverboat up the canal carrying Nyaakoto, disguised as a townsman in a straw raincoat and sedge hat, with only a travelling short sword. The neighbours have hidden his katana and bow in a dry well.

Nyaakoto slips past the drones on the landing and through the ward gate. He spares the collared townsfolk the Credit House has pressed into service: he knocks them down with the back of the blade and cuts their collars. In the back tenements he recovers his swords and the lantern-makers' hidden tools. He escorts old Tōkichi, the cheerful fireworks-maker Tamakichi and two craftspeople past three patrols to their sealed workshop, and holds its yard when the seal calls the enforcers. That night the workshop makes lanterns again, and Tamakichi turns a dozen festival shells into a hand-mortar.

With one of those shells, Nyaakoto destroys the debt terminal at the notice square. Every number in the ward goes dark, and people step out into the rain. Shirasumi Oyuki, who kept the domain's accounts, explains what the Credit House's "credit" really is, and offers the only answer she trusts: count only what is made. In a tenement room the ward swears the 一味神水 oath and signs in a circle around the SORA mon. The Sora League (空紋一揆) is born, and its first act is a hot meal for everyone.

Then the Credit House demands collateral for its terminal. At the Lantern Wharf, collared residents are being penned. From the canal bridge Nyaakoto sees his senior pupil Toranosuke, wearing a Credit House haori, take the ledger away by boat: 「うちの家の借りは、買われた。」 ("My house's debt was bought.") Nyaakoto fights down the canal lane and defeats Enforcer-Chief Penalta, whose own hammer drags him into the canal. Before dawn the freed ward lights forty new lanterns, each painted with the SORA mon, and Oyuki turns to the next need: water.

**The chapter's job in the campaign:**
- It opens Act II (rebuilding). The League is founded, and Oyuki's principle of counting only what is made seeds the charter; her draft of the articles is collectible c05. XOR itself is first cut in ch05.
- It teaches the stealth basics that ch06 builds on: light, noise, alert states, rear takedown and the non-lethal seal-cut.
- It makes 活人剣 a rule of play: debt-bound conscripts can only be subdued, and they never count as kills.
- It sets up Toranosuke's fall (the ch06 duel) and the rival's grey haori, which is burned in ch08.

### 1.2 Play-time budget

| Category | Beats | Minutes | Bible §10 |
|---|---|---|---|
| Combat (C) | b08, b16, b17 | 14 | 14 |
| Explore (E) | b04 | 3 | 3 |
| Stealth (S) | b02, b03, b10 | 12 | 12 |
| Production (P) | b05, b07, b09, b14 | 15 | 15 |
| Mounted (M) | none | 0 | 0 |
| Cinematic and dialogue (Cin) | b01, b06, b11, b12, b13, b15, b18 | 11 | 11 |
| **Total** | **18** | **55** | **55** |

The targets assume a first-time player on Normal who watches the cinematics and does typical optional exploration, with about 12% retry overhead (bible §10). A completionist who finds all 6 collectibles and reads every POI adds about 6–9 min. On Easy, detection always falls back to combat, which removes most stealth retries (about −4 min).

**Player loadout through the chapter.**

| Beats | 腰 Hip | 脇 Side | 背 Back | 長柄 Polearm | 飛道具 Firearm |
|---|---|---|---|---|---|
| b01 to the b05 sword bundle | locked (disguise) | 4 wakizashi | locked | locked | locked |
| b05 bundle to b09 | 0 katana | 4 | 18 yumi, 12 arrows | — | — |
| b09 to b14 | 0 | 4 | 18 | — | 7 (5 shells) |
| b14 supply point onward | 0 | 4 | 18 | 19 yari, optional (obstructed in 1.8 m alleys) | 7 |

### 1.3 Time of day, weather and lighting

In fiction it is early in the lunar 4th month (元和九年四月上旬, early May by the solar calendar), in the long early-summer rains called 卯の花腐し (bible §9.1, §16 ch3 row), from dusk to just before dawn. Wet surfaces carry the image.

| Beats | In-fiction time | Sky and key light | Weather and FX | Lighting notes | Mac fallback |
|---|---|---|---|---|---|
| b01 | 暮れ六つ (the dusk bell), blue hour | Sky about 9000 K with no sun; cyan door numerals about 8000 K; drone spotlight 8500 K | Steady rain, rain rings on the canal, low fog on the water | The ward is dark by decree. The only warm light is far off, behind shutters. Title card over black water. | SSR on water; halve rain-splash particles |
| b02–b10 | Early night | Very low ambient; licensed 行灯 1900 K; brazier 1800 K; numerals; drone cones | Steady rain, eave drips, puddle rings, gutter flow | Darkness is gameplay: clamp the auto-exposure range per stealth zone so shadows are never brightened into safety or out of it. Lumen reflections on Windows. | At most 8 shadowed lights per view; numerals as emissive decals |
| b09 | Night, interior | 行灯 1900 K and the oil-warmed hearth; half-made lanterns glowing through washi | Rain drumming on the board roof | The first warm interior. Washi transmission matters (see §5, lantern washi). | Baked-emissive lanterns |
| b11–b14 | Night after the blackout | Numerals off; residents' hand lamps and kitchen fires 1800 K | Rain | Warmth returns in pools; b13 is lit by a single 行灯. | Kitchen fires as 3 shadowed lights |
| b15–b17 | Late night | Two alien floodlights 8000 K, a boat's 篝火 1800 K, Penalta's chest lamp 8500 K | Heavier rain, gusts on the basin, spray off the 雁木 steps | Amber telegraphs must read against the 篝火: use animated edge-pulse decals (about 3 Hz) with a hatch pattern, never a static warm glow; accessible palette via L4 | Floodlights shadowed; 篝火 unshadowed |
| b18 | Before dawn (明け六つ前) | Sky 9000 K brightening toward 7000 K; 40 new lanterns 1900 K | Drizzle easing, mist | A flame-to-flame chain of lanterns down the street; MegaLights on Windows | 8 shadowed lanterns nearest the camera, the rest emissive |

### 1.4 Locations and layouts

**Coordinates.** Metres in prose, centimetres in the YAML. The origin is the centre of the 高札場 crossing (the arena 1 origin); +X is east, +Y is north, and Z is up from street level. The canal runs east–west along the ward's south side.

**Arena 1 rule.** The arena 1 core is the crossing and the street stubs around it. C2 owns its final dimensions and collision. The prototype builder already places `SM_Alien_StreetDebtTerminal` at (−7.3, +4.6) m, and this chapter uses that position. Everything else lives in ch03 layout data and sublevels and **never changes arena collision**: the landing, gate plaza, tenements, workshop, canal lane and wharf, and all campaign cover and props. Where the arena core differs from the numbers below, the arena wins and the campaign dressing adapts.

**Layout sketch (schematic, not to scale):**

```text
NORTH (+Y)
  +36 .. +42   manager's house: 8-mat room (b13), writing desk (c05), supply door (b14)
  +28 .. +36   tenement court: working well, dry well, 3 cook-fires (b05, b14)
  +29 .. +31   north alley runs east from the court to X -10, then south to the notice board (b10)
  +12 .. +28   back-tenement alley 1.8 m, two rows of six 2.7 x 3.6 m units (b04)
   +4 .. +12   front shops; Tokichi's hiding place at the alley mouth (b06)
 -3.6 .. +3.6  MAIN STREET 7.2 m:  X -62 (ward gate) ... 0 (notice square) ... +48 (east end)
   -4 .. -22   back lots: oil shop X -8..-2, storehouse A X +5..+11,
               lantern workshop X +16..+23 with yard X +16..+34, storehouse B X +38..+44
  -22 .. -28   CANAL LANE 6 m, X -56 .. +50 (escort b07, pursuit b16)
  -28 .. -38   CANAL 10 m; timber bridge at X 0 (b15 viewpoint)
SOUTH (-Y)

WEST (-X) ...................................................................... EAST (+X)
 X -220..-120 canal approach (b01) | X -120..-76 west landing (b02) | X -80..-62 gate plaza (b03)
 X -62..+48 the ward (b04-b16)      | X +50..+86 Lantern Wharf (b17), canal basin to Y -40
```

#### `pl_horiwari`, 堀割: canal approach and west landing (b01, b02). New space.

- **Canal:** 10 m wide, with 石積み dry-laid stone banks standing 1.6 m above the water. The approach runs 100 m from X −220 to −120 under a timber bridge at X −160 (2.4 m clearance).
- **West landing:** 44 × 16 m of packed earth at X −120 to −76, Y −28 to −12, with rut puddles along its centre (6 noise volumes).
- **Landmarks:**
  - The 雁木 stone landing steps at X −116 to −110: 6 m wide, six steps into the water. The player starts at the top (`ps_b02_start`).
  - Three plastered 土蔵 warehouses along the north edge. Each is 7.2 × 5.4 m, two storeys, with south-facing doors and 2 m dark gaps between them. W1 and W3 have licensed lamps.
  - An open shed at X −90 to −82, Y −20 to −16, with a stone-weighted board roof, a lit lamp and bales.
  - Five cargo stacks (the existing `SM_Nyaagyu_CargoStack`, 2.3 × 1.8 × 1.4 m).
  - Two boats moored east of the steps.
- **Cover:**
  - Cargo stacks: full cover when crouched.
  - The shed.
  - Boats: low cover.
  - The warehouse eaves: a 1.2 m dry, dark strip under a 0.9 m overhang, broken at the gaps.
- **Sightlines:** the canal edge is open for 40 m (drone D2's lane). D1 sees most of the yard from 5 m up, but only inside its 50° cone.
- **Exit:** a 3.6 m lane at X −80 to −76.4 running north from Y −12 to −7 into the gate plaza (`vol_b02_exit`).
- **Triggers:** `vol_b02_drones`, `vol_b02_puddles`, `vol_b02_andon` (Kohagi's tutorial lines) and `vol_b02_exit`.

#### `pl_kido`, 木戸: the ward gate (b03). Arena 1 west edge, campaign-only plaza.

- **Plaza:** 18 × 14 m (X −80 to −62, Y −7 to +7) of packed earth. A 0.6 m wide, 0.4 m deep ditch runs along its south edge.
- **Gate:** a 2.4 m board fence runs north–south along X −62. Its 3.6 m two-leaf gate is shut, and a graphite scanning arch fills the frame; its cyan sheet raises an instant alert. The 0.9 × 1.2 m 潜り戸 wicket is in the south leaf at (−63, +1.5).
- **Hut:** the 木戸番屋 (3.6 × 2.7 m) stands at X −68 to −64.4, Y −7 to −4.3. A brazier at (−66, −3.8) gives warm light (4 m radius) and cannot be put out. The lamp on the hut's eave can be.
- **Roof route:**
  1. A shop two storeys tall with a 卯建 firewall lines the plaza's north side. A roofer's ladder leans against its east wall at (−64, +6.5).
  2. Climb the ladder to the stone-weighted board roof (eave 3.2 m).
  3. Go over the 卯建 and drop inside the ward onto a straw pile at (−60, +5). Missing the pile makes a 900 cm landing noise.
- **Culvert:** a 暗渠 culvert at the south end of the fence (X −62, Y −6.5), 0.9 m high, 1.0 m wide and 3 m long. It is crouch-only, and its running water halves noise.
- **Guards** (see b03): C1, the kido-ban, at the wicket; C2 on the ditch line; C3 at the brazier; E1 at the arch facing west; E2 walking the plaza perimeter.
- **Sightlines:** E1 covers the plaza centre, and the brazier lights its southern third. The north side is dark except for E2's passes.
- **Exit:** `vol_b03_exit`, just inside the gate (X −60 to −56, Y ±3.6).

#### `pl_lantern_ward_rain`, 提灯街・雨: main street, canal lane and bridge (b07, b16, b18). Arena 1 plus campaign extension.

- **Main street:** X −62 to +48, 7.2 m (4 ken) of packed earth crowned for drainage, with cart ruts and puddles. 0.45 m 溝板 board gutters run along both frontages.
- **Frontages:**
  - 町家 3–5 ken wide (5.4–9 m), built as 厨子二階 with a low upper storey (eave about 3.2 m, ridge about 6.5 m).
  - 格子 lattices and 卯建 on party walls.
  - 暖簾: most are taken in, since the shops are shut.
  - Stone-weighted board roofs. Kawara appears only on the 両替屋 and the storehouses.
  - Each door shows 0.3 m cyan numerals: the dominant light until b11.
- **North–south street:** 5.4 m wide, crossing at X 0. It runs from Y +40 (the northern playable edge, toward the castle hill) down to the canal.
- **Canal lane (河岸通り):** Y −22 to −28 from X −56 to +50, packed earth with a dressed-stone canal edge and no railing. A player who falls in swims to the nearest 雁木 in about 3 s and makes noise.
  - **Cover:** sake barrels stacked in threes, moored boats, and eave recesses.
  - **Landmarks along the north side:** the oil shop's storehouse (X −8 to −2), storehouse A (X +5 to +11, roof 6.5 m), the workshop yard's back gate (X +20) and storehouse B (X +38 to +44, roof 6.5 m).
- **中橋 bridge:** at X 0 across the canal. It is a gently arched timber bridge with its crown 2.2 m above the lane and 0.9 m rails. It is the b15 viewpoint (`ps_b16_bridge`), 50–86 m from the wharf.
- **Escort route (b07):** `spl_b07_escort`, about 84 m, with ten hide spots (`hs_b07_01`–`10`) in doorways, behind barrels and in boat shadow.
- **Pursuit route (b16):** 50 m from the bridge foot (0, −25) to the wharf's west edge (+50, −25).

#### `pl_ura_nagaya`, 裏長屋: the back tenements (b04, b05, b06, b13, b14). Arena 1 extension, campaign-only.

- **Entry:** the 路地木戸 at X −28, Y +4, a 1.8 m gateway under a front shop's upper floor.
- **Tōkichi's hiding place:** the back storeroom (2.7 × 3 m) of the front shop east of the alley. Its door opens onto the alley at (−27.1, +10.5). It is the carry drop-off (`dp_b05_hideout`) and the b06 scene.
- **Alley:** X −28.9 to −27.1, Y +12 to +28.2, with a 溝板 gutter down its centre (it rattles except along the edges) and laundry poles overhead.
  - Twelve 九尺二間 units face each other across it (2.7 m frontage, 3.6 m deep): the west row at X −32.5 to −28.9 and the east row at X −27.1 to −23.5.
  - Each 腰高障子 door shows its balance.
- **Court:** 12 × 7.8 m (X −34 to −22, Y +28.2 to +36).
  - The working well with its 釣瓶 pulley at (−26, +31) is the crate hoist.
  - The dry well at (−31, +32) has a 0.75 m stone curb and a 0.9 m bore, is 7 m deep, and has a knotted rope.
  - A lean-to (下屋) along the west side holds three clay 竈.
  - There is a rubbish corner, and a 1.8 m bamboo back fence on the west with a gap toward the canal-side lots (the b14 drone approach).
- **Manager's house:** Y +36 to +42, X −32 to −24. Its raised eight-mat room is the b13 oath room, and its writing desk holds c05. Its door at (−24, +36) is the b14 supply point.
- **North alley (b10 route):** it leaves the court's east side at (−22, +31) and runs east along Y +29 to +31 to X −10. It then turns south down a 1.2 m side passage to the rear of the notice board at (−7.3, +7). Its east–west run is the blast-safe volume.
- **Sightlines:** the alley is a 24 m straight shot from the main street. That is why the b05 patrol at the alley mouth matters, and why a 暖簾 and laundry screen it.

#### `pl_chochin_kobo`, 提灯の工房: the lantern workshop (b08, b09). Interior and yard, campaign-only.

- **Building:** X +16 to +23.2, Y −4 to −15 (7.2 × 11 m), fronting the main street.
  - A 1.8 m 通り土間 earth passage runs along the west wall beside a 5.4 × 11 m plank floor raised 45 cm.
  - Lanterns dry on poles in the rafters.
  - The front door to the street is barred. The back door to the yard at (+19, −15) carries the cyan debt seal.
- **Yard:** X +16 to +34, Y −9 to −22 (18 × 13 m). It wraps behind the shallow east-neighbour building (X +23.2 to +34, Y −4 to −9).
  - Bamboo stock racks along the north side and drying boards.
  - A well curb at (+26, −14).
  - Oil jars against the house wall at (+23, −12): a fire hazard.
  - A storehouse at X +29 to +34, Y −16 to −22 (roof 6.5 m, the grenadier's perch).
  - A back gate to the canal lane at (+20, −22).
  - A side passage from the main street along X +34 that enters the yard at its north-east corner.
- **Cover:**
  - Hard: the well curb, the storehouse corners, and the oil jars until they ignite.
  - Soft and destructible: the bamboo racks and drying boards.
- **Sightlines:** rifle ranges are short (18 m at most). The grenadier sees the whole yard from the roof.
- **b09 stations:**
  - The rib form at the front of the plank floor.
  - The paste bench in the middle of the floor.
  - The oil rack by the yard door.
  - Tamakichi's shell bench in the yard under the storehouse eaves, deliberately away from the oil and flame.

#### `pl_kosatsuba`, 高札場: the notice square (b10, b11, b12). Arena 1 centre.

- **Crossing:** X −9 to +9, Y −7 to +7. It is a widened crossing, not a 広小路 firebreak (a later form, bible §19), with stubs of the main street and the north–south street.
- **Notice board and terminal (north-west corner):**
  - The 高札場: a roofed board 3.6 m wide and 2.4 m tall on a 0.6 m stone base at (−7.3, +6.5), behind a 5.4 × 1.8 m 矢来 fence.
  - The terminal stands in front of it at (−7.3, +4.6), with its screen facing south and a 6 m glow.
  - Its rear service panel faces north, reached through a 0.6 m gap along the 矢来.
- **Corner buildings:**
  - North-east: the 両替屋 (X +6 to +13.2, Y +4 to +13), two storeys with a kawara roof. The marksman perches on its 7.5 m ridge at (+9, +8).
  - South-east: a sake shop (酒屋).
  - South-west: a pawnbroker (質屋), with a ladder on its west wall up to the board roofs.
- **Lights and noise:** two licensed 辻行灯 (the existing `SM_Edo_LanternPost`) at (−8, −6) and (+8, −6). 溝板 run along all four frontages, with a silent edge strip.
- **Routes** (see b10): the north alley (dark and intended), over the roofs, or along the main-street eaves (lit).
- **After the blast:** residents stand in doorways (b11). Oyuki steps out from under the 高札場 roof (b12).

#### `pl_chochin_gashi`, 提灯河岸: the Lantern Wharf (b15 target, b17 boss arena). New space.

- **Size:** 36 × 24 m (X +50 to +86, Y −28 to −4). A 3 m strip of dressed stone runs along the canal edge; wharves are one of the places the bible allows stone, and it is slick in the rain. The rest is packed earth.
- **South:** the canal basin (Y −28 to −40).
  - 雁木 steps at X +76 to +80.
  - A moored 高瀬舟 with a 篝火 brazier at (+78, −30), and a barge at (+60, −31).
- **North:** two plastered storehouses (X +56 to +63.2 and +66 to +73.2, Y −4 to +1.4) with iron-fitted doors.
- **West:** the bamboo 矢来 pen of seized residents (X +51 to +57, Y −12 to −7). It is protected: attacks stop at its fence. Tamakichi's shell crate is at (+53, −13).
- **East:** a shear-leg hoist (二又, 7 m tall) with a 轆轤 windlass. Its base sits at X +81 to +85, Y −19 to −15, and its pulley hangs over the drop zone (centre (+78, −20), radius 2 m). The rope's cleat is at (+84, −14). Two nets of rice bales hang on two hooks.
- **Cargo stacks** (6): at (+58, −22), (+66, −22), (+62, −13), (+70, −13), (+76, −9) and (+72, −25). They are staggered so that a flank route always exists.
- **Lights:** alien floodlight masts at (+52, −6) and (+84, −6).
- **Entry:** from the canal lane at (+51, −25) (`ps_b17_entry`). On the lock, drones stretch seizure nets across the lane and across the main-street ramp at (+49, −2).
- **Penalta's start:** (+68, −16).
- **Sightlines:** the whole wharf is visible from the entry. The stacks break Penalta's line to the player's flank, and the steps are the edge he falls from.

---

## 2. Beat list

### 2.1 Overview

| Beat | Type | Place | Min | CP | Site | Unlocks | Summary |
|---|---|---|---|---|---|---|---|
| ch03.b01 | cinematic | `pl_horiwari` | 2 | yes | — | weapon 4 | Title card. Rain, dusk. Kohagi poles a 高瀬舟 into the dark ward; wakizashi handed over. |
| ch03.b02 | stealth_zone | `pl_horiwari` | 4 | yes | — | `stealth` | Stealth tutorial on the west landing: 2 drones, puddles, snuffable andon. |
| ch03.b03 | stealth_zone | `pl_kido` | 4 | yes | — | `takedown`, `seal_cut` | Ward gate: 3 debt-bound + 2 enforcers. Rear takedown, 峰打ち, seal-cut; 3 routes in. |
| ch03.b04 | explore_optional | `pl_ura_nagaya` | 3 | yes | — | — | Optional walk-through: well-side gossip, chalk SORA marks, glowing balance doors. 2 collectibles. |
| ch03.b05 | production_task (carry) | `pl_ura_nagaya` | 4 | yes | 0 | — | Site 0. Climb into the dry well, recover katana and yumi, hoist and carry 3 tool crates to Tōkichi. |
| ch03.b06 | dialogue | `pl_ura_nagaya` | 1 | no | — | — | Hideout: Tōkichi (catalog line 2) and Tamakichi; the workshop seal; festival shells; escort plan. |
| ch03.b07 | production_task (escort) | `pl_lantern_ward_rain` | 5 | yes | — | — | Escort 4 craftspeople ~84 m through back ways past 3 patrols with hide-on-signal. |
| ch03.b08 | combat_wave | `pl_chochin_kobo` | 4 | yes | — | — | Breaking the seal trips an alarm: 3 waves, 8 enforcers incl. first grenadier arcs. NPCs shelter indoors. |
| ch03.b09 | production_task (manufacture) | `pl_chochin_kobo` | 3 | yes | 1 | weapon 7 | Site 1. Bend ribs → paste washi → oil; pack shells with Tamakichi. Unlocks weapon 7. Registry 提灯 40張. |
| ch03.b10 | stealth_zone | `pl_kosatsuba` | 4 | yes | — | — | Notice square: marksman on a roof, drone, 3 patrols. Plant Tamakichi's charge on the terminal's rear panel, light, clear out. |
| ch03.b11 | cinematic | `pl_kosatsuba` | 1.5 | yes | — | — | The terminal blows; every door numeral in the ward goes dark; residents step into the rain. |
| ch03.b12 | dialogue | `pl_kosatsuba` | 1.5 | no | — | — | Oyuki introduced: 「彼らの“信用”は、借りとして生まれるのです。」 She asks to bind a league. |
| ch03.b13 | cinematic | `pl_ura_nagaya` | 2 | no | — | — | League founded: 起請文 burned into sacred water; names signed in a circle around the SORA mon. |
| ch03.b14 | production_task (hold) | `pl_ura_nagaya` | 3 | yes | 2 | — | Site 2. Keep 3 cook-fires lit and the serving line open for 120 s while a patrol probes. Registry 炊き出し 120食. |
| ch03.b15 | cinematic | `pl_chochin_gashi` | 1.5 | no | — | — | From the canal bridge Nyaakoto sees Toranosuke in a Credit House haori beside Penalta. 「うちの家の借りは、買われた。」 |
| ch03.b16 | combat_wave | `pl_lantern_ward_rain` | 4 | yes | — | — | Pursuit along the canal lane: 6 enforcers, 2 roof marksmen; arcing shells over parapets. |
| ch03.b17 | boss | `pl_chochin_gashi` | 6 | yes | — | — | Shield bruiser on the wet wharf: flank via cargo, shoot rear vents, 3 shells break the shield, drop the crane net. |
| ch03.b18 | cinematic | `pl_lantern_ward_rain` | 1.5 | yes | — | — | Collars cut, pen opened; the ward lights 40 new lanterns painted with the SORA mon (catalog line 3). Next: the fields. |

Checkpoint flags are chosen so that no gap exceeds 360 target-seconds (bible §12.3 rule 8); the longest gap is 360 s, across the boss. b04 is `optional` and b05 `requires` only b03, so the carry objective is live while the player explores. b06, b12, b13 and b15 are dialogue or cinematic beats that take the previous save.

**Catalog compatibility.** Schema 3 gates site 1 at 4 lethal defeats and site 2 at 8. b08 alone gives 8 lethal defeats before site 1, so both gates are met without change. Conscripts never count (`nonlethal_types`). The site order is the catalog order, so unlike ch08 **no renumbering is needed**.

### 2.2 Beat details

#### ch03.b01 · cinematic · 高瀬舟で提灯街へ / By riverboat to Lantern Ward

| Field | Value |
|---|---|
| Place | `pl_horiwari` |
| Target | 2 min (120 s) |
| Checkpoint | yes |
| Requires | previous beat |
| Unlocks | weapons 4 |
| Music state | `ch03_canal_rain` |
| Fail | None (non-interactive, skippable). |

Title card 第三章 占領された街 with the vermillion SORA 朱印 seal, over rain on black canal water. A 高瀬舟 (flat-bottomed river boat, about 13 m) loaded with firewood bundles and straw bales slides east along the canal from X −220 m. Kohagi poles from the stern. Nyaakoto sits among the bales in a 蓑 and 菅笠 over a plain indigo 小袖, ears low. The boat passes under a timber bridge at X −160 m. Ahead, Lantern Ward has no lanterns lit; the only light is cold cyan numerals glowing on every door and a drone's spotlight sweeping the water. The Credit House notice voice, broadcast from the passing drone, announces the day's interest and the lamp licence. Kohagi hands over a plain-mounted 脇差 (weapon 4) as a 道中差: the katana, yumi and ebira went ahead into the tenement's dry well. The boat noses against the 雁木 landing steps at (−113, −30) m. The last shot is the player's view, and the camera blends into control at `ps_b02_start`.

Loadout for b01–b05: only the wakizashi is equipped (hip, back, polearm and firearm slots locked by the disguise) until the sword bundle is picked up in b05.

**Subtitles:** ch03.b01.system.001 @ 8 s, ch03.b01.system.002 @ 16 s, ch03.b01.kohagi.003 @ 31 s, ch03.b01.nyaakoto.004 @ 36 s, ch03.b01.kohagi.005 @ 42 s, ch03.b01.kohagi.006 @ 63 s, ch03.b01.kohagi.007 @ 71 s, ch03.b01.nyaakoto.008 @ 76 s, ch03.b01.kohagi.009 @ 82 s

#### ch03.b02 · stealth_zone · 河岸を抜けよ / Slip past the landing

| Field | Value |
|---|---|
| Place | `pl_horiwari` |
| Target | 4 min (240 s) |
| Checkpoint | yes |
| Requires | previous beat |
| Unlocks | mechanics `stealth` |
| Guards | `drone` ×2 |
| On detected | `combat` |
| Music state | `ch03_stealth` |
| Fail | player_died → checkpoint (only possible if the player stands in seizure nets under fire; drones do 5 dmg zaps). Detection → combat, never a restart. |

Teaches crouch-walk, light and noise. The west landing is 44 × 16 m of packed earth between the canal and a row of three 土蔵 warehouses. Two drones sweep it: D1 flies a figure-eight over the yard at 5 m (40 s loop), and D2 runs the canal edge and back (30 s loop) with its spotlight raking the 雁木 steps. Three licensed 行灯 on posts light the warehouse doors and the open shed; holding Interact for 1 s snuffs one (a smoke curl and a soft hiss). Six rut puddles double footstep noise.

Three routes lead to the exit lane at the north-east corner (X −80 to −76.4 m):
- **The eaves (軒下) of the warehouses:** dry and dark, but two door lamps must be snuffed first.
- **The water's edge behind two moored boats:** low cover, but puddles and D2's sweep.
- **Through the open shed:** full cover, but its lamp is lit.

If a drone detects the player, it marks (900 ms cyan lock), then drops to 2.5 m and releases a seizure net (roots for 1.5 s). While low, a drone can be cut down with one wakizashi strike. Detection is not a fail. Instead the ward gate in b03 starts with its guards `suspicious` (`x_on_detected_carryover`). There are no takedowns in this beat; drones cannot be taken down from behind.

**Dialogue triggers:**
- `beat_start` → ch03.b02.kohagi.001 (radio)
- `volume_enter:vol_b02_drones` → ch03.b02.kohagi.002 (radio)
- `volume_enter:vol_b02_puddles` → ch03.b02.kohagi.003 (radio)
- `volume_enter:vol_b02_andon` → ch03.b02.kohagi.004 (radio)
- `alert_state:suspicious` → ch03.b02.drone.005 (ambient, repeatable, spoken by drone)
- `alert_state:alert` → ch03.b02.drone.006 (ambient, repeatable, spoken by drone)
- `alert_state:search` → ch03.b02.drone.007 (ambient, repeatable, spoken by drone)
- `x_alert_state:search_to_unaware` → ch03.b02.drone.008 (ambient, repeatable, spoken by drone)
- `beat_complete` → ch03.b02.kohagi.009 (radio)
- `player_died` → ch03.b02.kohagi.010 (radio, repeatable)

#### ch03.b03 · stealth_zone · 木戸を越えよ / Get through the ward gate

| Field | Value |
|---|---|
| Place | `pl_kido` |
| Target | 4 min (240 s) |
| Checkpoint | yes |
| Requires | previous beat |
| Unlocks | mechanics `takedown`, `seal_cut` |
| Guards | `bound_conscript` ×3, `enforcer_rifle` ×2 |
| On detected | `combat` |
| Music state | `ch03_stealth` |
| Fail | player_died → checkpoint. Conscripts cannot be killed (峰打ち is forced). Walking through the scan arch → alert → combat. On Easy, any detection → combat (bible §12.2). |

The ward gate (木戸) is a 3.6 m two-leaf timber gate in a 2.4 m board fence running north–south at X −62 m. The plaza outside is 18 × 14 m. The Credit House has bolted a graphite scanning arch inside the gate frame; walking through its cyan sheet raises an immediate alert. The 木戸番屋 hut (3.6 × 2.7 m) stands at the plaza's south side with a charcoal brazier in front of it (a warm light, radius 4 m, cannot be put out) and a snuffable lamp on its eave.

Guards:
- **C1, the kido-ban:** an elderly conscript with a 六尺棒 staff standing at the 潜り戸 wicket, turning every 12 s.
- **C2:** patrols the drainage ditch along the south fence (40 s loop).
- **C3:** warms his paws at the brazier.
- **E1:** an enforcer standing at the arch, facing west.
- **E2:** an enforcer walking the plaza perimeter (50 s loop).

Conscripts are reluctant, so their suspicion builds at 0.7× the enforcers' rate.

Routes:
1. **Wicket:** take C1 down from behind while E1 faces away. A strike on a conscript is always a 峰打ち knockdown; hold Interact for 1.5 s within 8 s to cut the collar. The freed kido-ban tells the player the wicket's bar is off and stays hidden in place.
2. **Culvert:** a 0.9 m 暗渠 culvert under the south fence, crouch only. Running water halves noise, but C2's patrol passes its mouth.
3. **Roof:** a roofer's ladder on the north shop wall leads onto the board roof and over the 卯建 firewall. The drop inside makes a 900 cm landing noise unless the player lands on the straw pile.

A rear takedown on an enforcer is lethal (a wakizashi thrust under the gorget) and takes 2.2 s. It teaches `takedown` and `seal_cut`.

**Dialogue triggers:**
- `beat_start` → ch03.b03.kohagi.001 (radio)
- `volume_enter:vol_b03_first_conscript` → ch03.b03.kohagi.002 (radio)
- `volume_enter:vol_b03_bansho_rear` → ch03.b03.kohagi.003 (radio)
- `alert_state:suspicious` → ch03.b03.conscript.004 (ambient, repeatable, spoken by bound_conscript)
- `alert_state:alert` → ch03.b03.conscript.005 (ambient, repeatable, spoken by bound_conscript)
- `x_alert_state:search_to_unaware` → ch03.b03.conscript.006 (ambient, repeatable, spoken by bound_conscript)
- `alert_state:suspicious` → ch03.b03.enforcer.007 (ambient, repeatable, spoken by enforcer_rifle/blade_retainer/shield_enforcer)
- `alert_state:alert` → ch03.b03.enforcer.008 (ambient, repeatable, spoken by enforcer_rifle/blade_retainer/shield_enforcer)
- `alert_state:search` → ch03.b03.enforcer.009 (ambient, repeatable, spoken by enforcer_rifle/blade_retainer/shield_enforcer)
- `x_npc_freed:kidoban` → ch03.b03.kidoban.010, ch03.b03.kidoban.011 (ambient)
- `player_died` → ch03.b02.kohagi.010 (radio, repeatable)

#### ch03.b04 · explore_optional · 裏長屋を歩け / Walk the back tenements

| Field | Value |
|---|---|
| Place | `pl_ura_nagaya` |
| Target | 3 min (180 s) |
| Checkpoint | yes |
| Requires | ch03.b03 |
| Optional | yes |
| Unlocks | — |
| Music state | `ch03_ward_explore` |
| Fail | None (no enemies inside the tenement court during b04). |

Inside the gate, the main street is empty. Its doors are shut and its cyan numerals glow through the rain. A 路地木戸 at X −28 m leads under a front house into the 1.8 m alley of the back tenements. Two facing rows of six 九尺二間 units (2.7 × 3.6 m each) line the alley, with a 溝板 board gutter down its centre, laundry poles, and a 腰高障子 door on each unit showing its balance in cyan. At the north end the alley opens into a 12 × 7.8 m court with two wells. The working well has a 釣瓶 pulley frame; the old one has run dry.

Points of interest (no map markers; light, sound and paths lead the player):
- **Well-side gossip (`poi_idobata`):** three women at the working well.
- **Chalk marks (`poi_chalk`):** two children drawing the SORA mon low on a wall, at child height. The mark here is collectible c01.
- **Leaflet (`poi_leaflet`):** an old man pasting Credit House leaflets onto a lantern frame.
- **Balance door (`poi_balance_door`):** a widow's door with the highest balance; the seizure notice pasted on it is collectible c02.
- **Dead end (`poi_dead_end`):** a view through a gap in the back fence toward the dark main street and the terminal's glow.

Because the beat is optional and b05 also requires only b03, the carry objective is live throughout. After 150 s a hint lamp in the court flickers toward the dry well.

**Dialogue triggers:**
- `volume_enter:poi_idobata` → ch03.b04.resident.001, ch03.b04.resident.002, ch03.b04.resident.003 (ambient)
- `volume_enter:poi_chalk` → ch03.b04.child.004, ch03.b04.child.005 (ambient)
- `volume_enter:poi_leaflet` → ch03.b04.resident.006 (ambient)
- `volume_enter:poi_balance_door` → ch03.b04.nyaakoto.007 (ambient)

#### ch03.b05 · production_task · carry · 空井戸の道具を運べ / Carry the hidden tools

| Field | Value |
|---|---|
| Place | `pl_ura_nagaya` |
| Target | 4 min (240 s) |
| Checkpoint | yes |
| Requires | ch03.b03 |
| Site | 0 |
| Unlocks | — |
| Patrols / waves | W1 (start): `enforcer_rifle` ×1, `bound_conscript` ×1 |
| Music state | `ch03_ward_explore` |
| Fail | player_died → checkpoint. Crates dropped on hit stay where they fall (re-pick). No fail on detection. |

**Site 0, 道具の隠し場 (hidden tool cache).**
1. Climb down the knotted rope into the 7 m dry well (the stone lining is wet and moss-dark). At the bottom, the player unwraps an oiled-paper bundle holding the katana in its saya, the unstrung yumi in a cloth bow-bag, and the ebira with 12 red-fletched arrows. Nyaakoto strings the bow in a shortened 3 s braced motion. The loadout is restored to katana (hip), wakizashi (side) and yumi (back). A crack in the well lining hides collectible c03, a scroll fragment.
2. Climb out. At the working well's 釣瓶 pulley, hold Interact for 3 s to hoist each tool crate from the bottom.
3. Carry each crate 21 m down the alley to Tōkichi's hiding place (dp_b05_hideout), the back storeroom of a front shop near the alley mouth. Carrying runs toward the danger. While carrying, the player moves at 0.8× speed, can use only the katana one-handed, and has no bow.

A two-guard patrol (an enforcer and a conscript) walks the main street past the alley mouth every 45 s. The alley mouth is screened by a 暖簾 and hanging laundry. Because the beat has `stealth: true`, hoisting pauses while a guard has line of sight into the court. If the patrol spots the player carrying, it investigates; being hit drops the crate, which can be picked up again.

**Dialogue triggers:**
- `beat_start` → ch03.b05.kohagi.001 (radio)
- `x_item_picked:sword_bundle` → ch03.b05.nyaakoto.002 (ambient)
- `x_item_picked:sword_bundle` → ch03.b05.kohagi.003 (radio)
- `volume_enter:vol_b05_alley_mouth` → ch03.b05.conscript.004 (ambient)
- `progress_at:0.33` → ch03.b05.tokichi.005 (ambient)
- `beat_complete` → ch03.b05.tokichi.006 (ambient)
- `alert_state:suspicious` → ch03.b03.conscript.004 (ambient, repeatable, spoken by bound_conscript)
- `alert_state:alert` → ch03.b03.conscript.005 (ambient, repeatable, spoken by bound_conscript)
- `x_alert_state:search_to_unaware` → ch03.b03.conscript.006 (ambient, repeatable, spoken by bound_conscript)
- `alert_state:suspicious` → ch03.b03.enforcer.007 (ambient, repeatable, spoken by enforcer_rifle/blade_retainer/shield_enforcer)
- `alert_state:alert` → ch03.b03.enforcer.008 (ambient, repeatable, spoken by enforcer_rifle/blade_retainer/shield_enforcer)
- `alert_state:search` → ch03.b03.enforcer.009 (ambient, repeatable, spoken by enforcer_rifle/blade_retainer/shield_enforcer)
- `player_died` → ch03.b02.kohagi.010 (radio, repeatable)

#### ch03.b06 · dialogue · 灯吉と玉吉 / Tōkichi and Tamakichi

| Field | Value |
|---|---|
| Place | `pl_ura_nagaya` |
| Target | 1 min (60 s) |
| Checkpoint | no |
| Requires | ch03.b05 |
| Unlocks | — |
| Music state | `ch03_hideout` |
| Fail | None. |

A walk-and-talk in Tōkichi's hiding place (the back storeroom of a front shop, at the alley's south end) and the alley outside it; the player keeps control. Tōkichi opens the first crate: rib forms, brushes, a split-bamboo knife. He speaks catalog line 2 and explains the debt seal on his workshop door. Tamakichi enters from the back fence too loudly, is hushed, and promises to blow the seal off; twelve festival shells are hidden under the floor. Nyaakoto commits to escorting the four craftspeople. The fourth is the paper-paster お蓮 (Oren), a silent NPC. Kohagi reports three patrols on the back way. Once the last line is done, the four NPCs gather at the alley mouth, and walking into `vol_b07_start` begins b07.

**Dialogue:** `beat_start` → ch03.b06.tokichi.001, ch03.b06.tokichi.002, ch03.b06.tamakichi.003, ch03.b06.tokichi.004, ch03.b06.tamakichi.005, ch03.b06.tamakichi.006, ch03.b06.nyaakoto.007, ch03.b06.kohagi.008 (mode `ambient`, camera `soft_lookat`)

#### ch03.b07 · production_task · escort · 職人たちを工房へ / Escort the craftspeople to the workshop

| Field | Value |
|---|---|
| Place | `pl_lantern_ward_rain` |
| Target | 5 min (300 s) |
| Checkpoint | yes |
| Requires | previous beat |
| Unlocks | — |
| Patrols / waves | W1 (start): `bound_conscript` ×2, `drone` ×1; W2 (start): `enforcer_rifle` ×2; W3 (start): `enforcer_rifle` ×1, `blade_retainer` ×1 |
| Music state | `ch03_escort` |
| Fail | Any escort dies (downed and not revived within 8 s) → checkpoint. player_died → checkpoint. |

The escort route `spl_b07_escort` is about 84 m long:
1. Hideout.
2. Tenement alley down to its mouth at the main street (6 m).
3. A 7.2 m exposed crossing of the main street at X −28 m.
4. A dark 1.5 m side passage between south-side houses (17 m).
5. East along the canal lane for 40 m.
6. Behind a storehouse to the workshop's back gate at (+20, −22.5) m.

Escorts walk crouched at 160 cm/s and stop if the player falls more than 8 m behind.

Signal (one button): the first press sends each escort to the nearest free hide spot (a doorway recess, stacked barrels, a moored boat's shadow; 10 authored `hs_` spots) and makes them crouch still; the next press sends them on. Escorts in a hide spot cannot be seen beyond 300 cm.

Patrols:
- **P1:** two conscripts pacing the main street between X −45 and −12 m (60 s loop), with a drone sweeping the street overhead (30 s cycle). This is the crossing puzzle: wait for the drone to pass, then cross while P1 has its backs turned.
- **P2:** two enforcers on the canal lane near the old oil shop (40 s loop). The player can hide the group and take one down from behind, or hold them until the pair turns.
- **P3:** an enforcer and a blade retainer behind storehouse A (35 s loop). The retainer walks close to the wall, so a rear takedown on it is the intended solution.

If a patrol detects the group, it engages, and the escorts hide automatically. A downed escort can be revived within 8 s (hold Interact for 2 s).

**Dialogue triggers:**
- `beat_start` → ch03.b07.kohagi.001 (radio)
- `beat_start` → ch03.b07.isa.002 (ambient)
- `x_signal:hide` → ch03.b07.nyaakoto.003 (ambient, repeatable)
- `x_signal:go` → ch03.b07.nyaakoto.004 (ambient, repeatable)
- `volume_enter:vol_b07_patrol1` → ch03.b07.tamakichi.005 (ambient)
- `volume_enter:vol_b07_oilshop` → ch03.b07.tokichi.006 (ambient)
- `npc_downed:isa` → ch03.b07.isa.007 (ambient, repeatable)
- `x_npc_revived:any` → ch03.b07.nyaakoto.008 (ambient, repeatable)
- `volume_enter:vol_b07_patrol3` → ch03.b07.kohagi.009 (radio)
- `beat_complete` → ch03.b07.tokichi.010 (ambient)
- `alert_state:suspicious` → ch03.b03.conscript.004 (ambient, repeatable, spoken by bound_conscript)
- `alert_state:alert` → ch03.b03.conscript.005 (ambient, repeatable, spoken by bound_conscript)
- `x_alert_state:search_to_unaware` → ch03.b03.conscript.006 (ambient, repeatable, spoken by bound_conscript)
- `alert_state:suspicious` → ch03.b03.enforcer.007 (ambient, repeatable, spoken by enforcer_rifle/blade_retainer/shield_enforcer)
- `alert_state:alert` → ch03.b03.enforcer.008 (ambient, repeatable, spoken by enforcer_rifle/blade_retainer/shield_enforcer)
- `alert_state:search` → ch03.b03.enforcer.009 (ambient, repeatable, spoken by enforcer_rifle/blade_retainer/shield_enforcer)
- `alert_state:suspicious` → ch03.b02.drone.005 (ambient, repeatable, spoken by drone)
- `alert_state:alert` → ch03.b02.drone.006 (ambient, repeatable, spoken by drone)
- `alert_state:search` → ch03.b02.drone.007 (ambient, repeatable, spoken by drone)
- `x_alert_state:search_to_unaware` → ch03.b02.drone.008 (ambient, repeatable, spoken by drone)
- `x_ai:withdraw` → ch03.b08.enforcer.006 (ambient, repeatable, spoken by enforcer_rifle/blade_retainer/shield_enforcer)
- `player_died` → ch03.b02.kohagi.010 (radio, repeatable)

#### ch03.b08 · combat_wave · 工房の庭を守れ / Hold the workshop yard

| Field | Value |
|---|---|
| Place | `pl_chochin_kobo` |
| Target | 4 min (240 s) |
| Checkpoint | yes |
| Requires | previous beat |
| Unlocks | — |
| Waves | W1 (start): `enforcer_rifle` ×3; W2 (alive_below:2): `blade_retainer` ×2, `enforcer_rifle` ×2; W3 (alive_below:2): `grenadier` ×1 |
| Music state | `ch03_combat` |
| Fail | player_died → checkpoint. |

Nyaakoto cuts the cyan debt seal on the workshop's back door (a 2 s interact). The seal speaks, and the four craftspeople bar themselves inside; they are not targetable in this beat. The yard is 18 × 13 m of wet packed earth: bamboo stock leaning in racks (soft cover that shreds), paper-drying boards, a well curb (hard cover), a stack of oil jars against the house wall (a grenadier shell or any explosion ignites a 6 s fire patch), and a 土蔵 in the south-east corner whose roof the grenadier uses.

Waves:
- **Wave 1:** three enforcers enter through the side passage from the main street.
- **Wave 2** (when fewer than 2 remain): two blade retainers vault the east fence and two enforcers come through the canal-lane gate. The blade retainers teach reading the 420 ms fixed-direction warning in a crowd.
- **Wave 3:** one grenadier on the storehouse roof. Its arcing shells show the visible arc decal before they land, which prepares the player to use the same arc with weapon 7 next beat.

All enemies are lethal archetypes. The 8 defeats satisfy the catalog's `requires_kills` gates (4 before site 1, 8 before site 2).

**Dialogue triggers:**
- `beat_start` → ch03.b08.system.001, ch03.b08.nyaakoto.002, ch03.b08.tokichi.003 (ambient)
- `x_wave_start:1` → ch03.b08.enforcer.004 (ambient)
- `pattern:grenadier_fire` → ch03.b08.grenadier.005 (ambient, repeatable, spoken by grenadier)
- `x_ai:withdraw` → ch03.b08.enforcer.006 (ambient, repeatable, spoken by enforcer_rifle/blade_retainer/shield_enforcer)
- `beat_complete` → ch03.b08.tamakichi.007 (ambient)
- `player_died` → ch03.b08.kohagi.008 (radio, repeatable)
- `alert_state:alert` → ch03.b03.enforcer.008 (ambient, repeatable, spoken by enforcer_rifle/blade_retainer/shield_enforcer)
- `alert_state:search` → ch03.b03.enforcer.009 (ambient, repeatable, spoken by enforcer_rifle/blade_retainer/shield_enforcer)

#### ch03.b09 · production_task · manufacture · 提灯を張れ / Make the lanterns

| Field | Value |
|---|---|
| Place | `pl_chochin_kobo` |
| Target | 3 min (180 s) |
| Checkpoint | yes |
| Requires | previous beat |
| Site | 1 |
| Registry | 提灯 40張 (Paper lanterns, 40 lanterns) |
| Unlocks | weapons 7 |
| Music state | `ch03_craft` |
| Fail | None (no enemies; a failed step repeats). |

**Site 1, 提灯の工房 (lantern workshop).** Inside, the 通り土間 earth passage runs along the west wall. The raised plank floor holds the stations:
- **Rib form (型台):** a collapsible wooden form. **Bend** ×6: each bamboo strip is flexed into a hoop and hooked onto the form. A flex gauge swings, and the player releases in the green band on an 800 ms beat (±160 ms). A failed bend splits the strip, and a fresh one is handed over.
- **Paste bench (糊台):** **Paste** ×4 washi panels (hold 1.5 s along each seam, overlapping) and **assemble** the top and bottom rims.
- **Oil rack:** **paste** ×1, brushing perilla oil (荏油) over the finished lantern, which is then hung from the rafters beside dozens of others the craftspeople are making.
- **Tamakichi's shell bench:** out in the yard under the storehouse eaves, away from oil and flame. **Assemble** ×3: wrap each festival shell in paper and seat it to the tube's bore. **Inspect** ×1: check the fuse.

Steps pass or fail; there is no quality grade. On completion Tamakichi hands over the 花火筒 (weapon 7, UI 擲弾筒), and the registry entry 提灯 40張 is written for the whole workshop's night of work. `site_restored:1` fires, and the workshop's windows glow warm for the rest of the chapter. Collectible c04 (heirloom) is in the yard storehouse.

**Dialogue triggers:**
- `beat_start` → ch03.b09.tokichi.001 (ambient)
- `progress_at:0.3` → ch03.b09.tokichi.002 (ambient)
- `progress_at:0.5` → ch03.b09.tokichi.003 (ambient)
- `progress_at:0.65` → ch03.b09.tokichi.004 (ambient)
- `progress_at:0.72` → ch03.b09.nyaakoto.005 (ambient)
- `progress_at:0.78` → ch03.b09.isa.006 (ambient)
- `progress_at:0.8` → ch03.b09.tamakichi.007 (ambient)
- `beat_complete` → ch03.b09.tamakichi.008, ch03.b09.tamakichi.009 (ambient)

#### ch03.b10 · stealth_zone · 端末に火薬を仕掛けよ / Plant a charge on the debt terminal

| Field | Value |
|---|---|
| Place | `pl_kosatsuba` |
| Target | 4 min (240 s) |
| Checkpoint | yes |
| Requires | previous beat |
| Unlocks | — |
| Guards | `marksman` ×1, `drone` ×1, `enforcer_rifle` ×2, `bound_conscript` ×2, `blade_retainer` ×1 |
| Patrols / waves | W1 (x_on_detected): `enforcer_rifle` ×3, `grenadier` ×1 |
| On detected | `reinforce:w_b10_reinforce` |
| Music state | `ch03_stealth` |
| Fail | player_died → checkpoint (including own blast). Detection → reinforcement wave, not a restart. |

The 高札場 is a widened crossing (18 × 14 m, not a firebreak plaza) where the main street meets the north–south street. The old roofed notice board stands on a stone base behind a low 矢来 fence at the north-west corner. The Credit House `StreetDebtTerminal` has been planted in front of it at (−7.3, +4.6) m, with its screen facing the main street. Its cyan glow lights everything within 6 m and cannot be turned off. The service panel is on its **north** face, reached by squeezing along the 矢来 between the board and the terminal. That approach rewards the dark route.

Guards:
- **Marksman:** on the ridge of the two-storey 両替屋 (money-changer's) at the north-east corner, about 7.5 m up. He sweeps a 120° arc over the square every 14 s. When he detects the player, he locks on with a 900 ms glint before firing.
- **Drone:** circles the square at 6 m (radius 12 m, 36 s).
- **P1:** two enforcers loop the square, 4 s apart (60 s).
- **P2:** two conscripts pace the north–south street (45 s).
- **P3:** a blade retainer walks the main street between X −40 and +40 m (70 s).
- **Lamps:** two licensed 辻行灯 (the existing `SM_Edo_LanternPost`) at the south-west and south-east corners can be snuffed.
- **Noise:** 溝板 drain boards along both frontages rattle (×1.5 noise) except along their silent edge strip; the board roofs are also noisy.

Routes:
1. **North alley (intended):** from the tenement court east behind the north lots, then down a side passage to the notice board. It is dark and wet, with puddles.
2. **Roof:** a ladder at the pawnbroker's side leads onto the roofs. From there the player can take the marksman down from behind (lethal), which removes the glint threat.
3. **Main-street eaves:** lit and fast, but risky.

Objectives: plant the charge (hold 4 s), light the 火縄 fuse (1 s), then reach any point in `vol_b10_blast_safe` (at least 15 m away and out of sight) within the 20 s fuse. Standing within 8 m at detonation damages the player. If detected, reinforcements come from the east: three enforcers and a grenadier. On Easy, detection falls back to plain combat.

**Dialogue triggers:**
- `beat_start` → ch03.b10.kohagi.001 (radio)
- `volume_enter:vol_b10_glint` → ch03.b10.kohagi.002 (radio)
- `volume_enter:vol_b10_dobuita` → ch03.b10.kohagi.003 (radio)
- `idle_s:20` → ch03.b10.system.004 (ambient)
- `alert_state:suspicious` → ch03.b10.marksman.005 (ambient, repeatable, spoken by marksman)
- `alert_state:alert` → ch03.b10.marksman.006 (ambient, repeatable, spoken by marksman)
- `x_reinforce:w_b10_reinforce` → ch03.b10.enforcer.007 (ambient)
- `x_objective:obj_light_fuse` → ch03.b10.nyaakoto.008 (ambient)
- `alert_state:suspicious` → ch03.b03.conscript.004 (ambient, repeatable, spoken by bound_conscript)
- `alert_state:alert` → ch03.b03.conscript.005 (ambient, repeatable, spoken by bound_conscript)
- `x_alert_state:search_to_unaware` → ch03.b03.conscript.006 (ambient, repeatable, spoken by bound_conscript)
- `alert_state:suspicious` → ch03.b03.enforcer.007 (ambient, repeatable, spoken by enforcer_rifle/blade_retainer/shield_enforcer)
- `alert_state:alert` → ch03.b03.enforcer.008 (ambient, repeatable, spoken by enforcer_rifle/blade_retainer/shield_enforcer)
- `alert_state:search` → ch03.b03.enforcer.009 (ambient, repeatable, spoken by enforcer_rifle/blade_retainer/shield_enforcer)
- `alert_state:suspicious` → ch03.b02.drone.005 (ambient, repeatable, spoken by drone)
- `alert_state:alert` → ch03.b02.drone.006 (ambient, repeatable, spoken by drone)
- `alert_state:search` → ch03.b02.drone.007 (ambient, repeatable, spoken by drone)
- `x_alert_state:search_to_unaware` → ch03.b02.drone.008 (ambient, repeatable, spoken by drone)
- `x_ai:withdraw` → ch03.b08.enforcer.006 (ambient, repeatable, spoken by enforcer_rifle/blade_retainer/shield_enforcer)
- `pattern:grenadier_fire` → ch03.b08.grenadier.005 (ambient, repeatable, spoken by grenadier)
- `player_died` → ch03.b02.kohagi.010 (radio, repeatable)

#### ch03.b11 · cinematic · 数字が消える / The numbers go dark

| Field | Value |
|---|---|
| Place | `pl_kosatsuba` |
| Target | 1.5 min (90 s) |
| Checkpoint | yes |
| Requires | previous beat |
| Unlocks | — |
| Music state | `ch03_blackout` |
| Fail | None. |

The festival-shell charge bursts gold and white, a warm palette distinct from alien cyan, and the terminal's glass face cracks in a spray of cyan shards that die in the rain. A ripple of darkness runs down the street as each door's numerals flicker out, the nearest first, then the tenement doors, then the far end of the ward. For a beat there is only rain. Then a 腰高障子 slides open. A mother and child look out, and one by one residents step into the street under 蓑 and 笠. Someone lights a small hand lamp; nothing happens; another lamp is lit. Nyaakoto, soaked, looks at the broken terminal: one terminal is gone, but the ledger is still out there. The camera ends on a white-sleeved figure watching from under the 高札場 eave.

**Subtitles:** ch03.b11.resident.001 @ 24 s, ch03.b11.child.002 @ 31 s, ch03.b11.resident.003 @ 36 s, ch03.b11.nyaakoto.004 @ 70 s

#### ch03.b12 · dialogue · 白澄お雪 / Shirasumi Oyuki

| Field | Value |
|---|---|
| Place | `pl_kosatsuba` |
| Target | 1.5 min (90 s) |
| Checkpoint | no |
| Requires | previous beat |
| Unlocks | — |
| Music state | `ch03_oyuki` |
| Fail | None. |

Oyuki steps out from under the 高札場 eave: white fur, one blue and one gold eye, a 小袖 with 襷, a 算盤 on a cord, and a 矢立 brush case at her obi. She walks with Nyaakoto toward the tenements while she talks (walk-and-talk; control kept; the camera soft-looks at her on each of her lines). She is precise and dry, and she explains the Credit House's arithmetic in three sentences, not a lecture: credit is created as debt, from nothing, with interest no one can out-produce. Her answer is to count only what is made. She has gathered the ward in the tenement court and asks to bind a league. Her well-thumbed arithmetic primer, 『割算書』 (1622), is visible in her sleeve.

**Dialogue:** `beat_start` → ch03.b12.oyuki.001, ch03.b12.nyaakoto.002, ch03.b12.oyuki.003, ch03.b12.oyuki.004, ch03.b12.oyuki.005, ch03.b12.nyaakoto.006, ch03.b12.oyuki.007, ch03.b12.oyuki.008 (mode `ambient`, camera `soft_lookat`)

#### ch03.b13 · cinematic · 一味神水 / The shared sacred water

| Field | Value |
|---|---|
| Place | `pl_ura_nagaya` |
| Target | 2 min (120 s) |
| Checkpoint | no |
| Requires | previous beat |
| Unlocks | — |
| Music state | `ch03_oath` |
| Fail | None. |

In the eight-mat room of the tenement manager's house, by 行灯 light, about twenty townsfolk kneel shoulder to shoulder with the craftspeople, Kohagi and Nyaakoto. Oyuki reads the oath, a 起請文 written on shrine 牛玉宝印 talisman paper. It is burned in a dish, and the ash is stirred into a bowl of water from the court's well. The bowl passes hand to hand and each person drinks (一味神水).

Then comes the League's founding image. On a large sheet, the SORA mon is brushed in the centre in vermillion by Tōkichi, and each member signs their name radiating outward like spokes (傘連判状), so that no name is first. Kohagi, who cannot write, presses the butt of the brush in a small circle (筆軸印), and Oyuki accepts it. Nyaakoto signs and adds his 花押; the camera does not linger on his name.

The last shot pulls back from the sheet, which is now 空紋一揆 (the Sora League), through the paper-screen window to the rain outside and the ward's first small warm lights. Music: the first full statement of the League theme.

**Subtitles:** ch03.b13.oyuki.001 @ 6 s, ch03.b13.oyuki.002 @ 18 s, ch03.b13.tokichi.003 @ 29 s, ch03.b13.nyaakoto.004 @ 35 s, ch03.b13.oyuki.005 @ 43 s, ch03.b13.kohagi.006 @ 62 s, ch03.b13.oyuki.007 @ 67 s, ch03.b13.nyaakoto.008 @ 98 s

#### ch03.b14 · production_task · hold · 炊き出しを守れ / Keep the communal kitchen going

| Field | Value |
|---|---|
| Place | `pl_ura_nagaya` |
| Target | 3 min (180 s) |
| Checkpoint | yes |
| Requires | previous beat |
| Site | 2 |
| Registry | 炊き出し 120食 (Communal meals, 120 meals) |
| Unlocks | — |
| Patrols / waves | W1 (progress_at:0.3): `enforcer_rifle` ×2, `bound_conscript` ×2; W2 (progress_at:0.6): `drone` ×2; W3 (progress_at:0.8): `blade_retainer` ×1, `enforcer_rifle` ×1 |
| Music state | `ch03_craft` |
| Fail | player_died → checkpoint. Residents in the queue are non-targetable (they scatter indoors when enemies enter the volume). |

**Site 2, 共同の炊き出し (communal kitchen).** The tenement court becomes a kitchen. Three clay 竈 stand under the lean-to on its west side with rice pots and a miso-soup cauldron, and serving boards on trestles face a queue of residents that runs back down the alley. The rice came from the ward's store, which Oyuki struck from the Credit House's books before the seizure.

The hold volume is the whole court (12 × 7.8 m) plus the first 6 m of the alley. Progress (120 s) pauses while any enemy is inside it. At 25%, 55% and 80% progress, rain from a leaking roof or a gust gutters one fire. Progress also pauses until the player relights it (hold Interact for 2 s at that 竈).

Waves:
- **At 30%:** the patrol probes the alley mouth (two enforcers and two conscripts).
- **At 60%:** two drones come over the back fence toward the queue.
- **At 80%:** a blade retainer and an enforcer come up the alley.

Tamakichi sets up a League 補給所 (supply point) at the manager's-house door. It is the chapter's first place to change the side, polearm and firearm slots: the yari (19) is available here (brought in by the League boat), and arrows and shells are refilled. Collectible c05 (Oyuki's draft of the five articles) is on her writing desk inside the manager's house.

**Dialogue triggers:**
- `beat_start` → ch03.b14.oyuki.001, ch03.b14.oyuki.002 (ambient)
- `progress_at:0.15` → ch03.b14.resident.003 (ambient)
- `progress_at:0.28` → ch03.b14.kohagi.004 (radio)
- `x_wave_start:1` → ch03.b14.enforcer.005 (ambient)
- `x_fire_out` → ch03.b14.oyuki.006 (ambient, repeatable)
- `volume_enter:vol_b14_supply` → ch03.b14.tamakichi.007 (ambient)
- `beat_complete` → ch03.b14.oyuki.008 (ambient)
- `alert_state:suspicious` → ch03.b03.conscript.004 (ambient, repeatable, spoken by bound_conscript)
- `alert_state:alert` → ch03.b03.conscript.005 (ambient, repeatable, spoken by bound_conscript)
- `x_alert_state:search_to_unaware` → ch03.b03.conscript.006 (ambient, repeatable, spoken by bound_conscript)
- `alert_state:alert` → ch03.b03.enforcer.008 (ambient, repeatable, spoken by enforcer_rifle/blade_retainer/shield_enforcer)
- `alert_state:search` → ch03.b03.enforcer.009 (ambient, repeatable, spoken by enforcer_rifle/blade_retainer/shield_enforcer)
- `alert_state:alert` → ch03.b02.drone.006 (ambient, repeatable, spoken by drone)
- `x_ai:withdraw` → ch03.b08.enforcer.006 (ambient, repeatable, spoken by enforcer_rifle/blade_retainer/shield_enforcer)
- `player_died` → ch03.b08.kohagi.008 (radio, repeatable)

#### ch03.b15 · cinematic · 灰色の羽織 / The grey haori

| Field | Value |
|---|---|
| Place | `pl_chochin_gashi` |
| Target | 1.5 min (90 s) |
| Checkpoint | no |
| Requires | previous beat |
| Unlocks | — |
| Music state | `ch03_rival` |
| Fail | None. |

Kohagi drops from a roof into the kitchen: residents are being rounded up at the wharf as collateral for the terminal. Cut to the 中橋 bridge over the canal at (0, −33) m. Nyaakoto reaches its crown and looks east along the canal, 55–85 m away. Under two cold floodlight masts, collared residents are being herded into a bamboo pen on the Lantern Wharf. Penalta stands among them: huge, in graphite armor, with a tower shield and a seal-hammer. Beside him, in a grey Credit House 羽織 over his black armor, is Toranosuke, holding a lacquered ledger chest.

Across the water, Toranosuke sees Nyaakoto. Their exchange is short, with rain between them. Penalta addresses Toranosuke by account number and orders the ledger taken to the citadel. Toranosuke boards a boat with the chest and is poled away into the dark, without looking back. Penalta turns his lamp on the bridge, and two marksmen climb to the storehouse roofs along the canal lane. Control resumes on the bridge crown.

**Subtitles:** ch03.b15.kohagi.001 @ 4 s, ch03.b15.penalta.002 @ 17 s, ch03.b15.nyaakoto.003 @ 31 s, ch03.b15.toranosuke.004 @ 35 s, ch03.b15.toranosuke.005 @ 40 s, ch03.b15.nyaakoto.006 @ 49 s, ch03.b15.toranosuke.007 @ 54 s, ch03.b15.penalta.008 @ 63 s

#### ch03.b16 · combat_wave · 河岸へ急げ / Fight through to the wharf

| Field | Value |
|---|---|
| Place | `pl_lantern_ward_rain` |
| Target | 4 min (240 s) |
| Checkpoint | yes |
| Requires | previous beat |
| Unlocks | — |
| Waves | W1 (start): `enforcer_rifle` ×3, `marksman` ×1; W2 (volume_enter:vol_b16_mid): `enforcer_rifle` ×3, `marksman` ×1 |
| Music state | `ch03_combat` |
| Fail | player_died → checkpoint. |

From the bridge foot, the canal lane runs 50 m east to the wharf. It is 6 m of packed earth between the canal's stone edge and the back lots, with stacked sake barrels, moored boats and eave recesses for cover. Storehouse A (X +5 to +11 m) and storehouse B (X +38 to +44 m) stand on the lane's north side with 6.5 m roofs.

- **Wave 1:** three enforcers hold the lane mid-way; marksman 1 is on storehouse A. His glint telegraph (900 ms) returns.
- **Wave 2** (when the player passes the workshop's back gate): three enforcers from the wharf end and marksman 2 on storehouse B.

The marksmen sit behind low roof ridges that block flat shots. A lofted 花火筒 shell (weapon 7) over the ridge is the readable answer. An arrow when a marksman stands up to fire also works. The retainer and grenadier barks from earlier beats recur.

**Dialogue triggers:**
- `beat_start` → ch03.b16.kohagi.001 (radio)
- `x_wave_start:1` → ch03.b16.enforcer.002 (ambient)
- `volume_enter:vol_b16_mid` → ch03.b16.nyaakoto.003 (ambient)
- `x_wave_start:2` → ch03.b16.kohagi.004 (radio)
- `alert_state:suspicious` → ch03.b10.marksman.005 (ambient, repeatable, spoken by marksman)
- `alert_state:alert` → ch03.b10.marksman.006 (ambient, repeatable, spoken by marksman)
- `alert_state:alert` → ch03.b03.enforcer.008 (ambient, repeatable, spoken by enforcer_rifle/blade_retainer/shield_enforcer)
- `alert_state:search` → ch03.b03.enforcer.009 (ambient, repeatable, spoken by enforcer_rifle/blade_retainer/shield_enforcer)
- `x_ai:withdraw` → ch03.b08.enforcer.006 (ambient, repeatable, spoken by enforcer_rifle/blade_retainer/shield_enforcer)
- `player_died` → ch03.b08.kohagi.008 (radio, repeatable)

#### ch03.b17 · boss · 取立頭ペナルタを倒せ / Defeat Enforcer-Chief Penalta

| Field | Value |
|---|---|
| Place | `pl_chochin_gashi` |
| Target | 6 min (360 s) |
| Checkpoint | yes, plus one per phase |
| Requires | previous beat |
| Unlocks | — |
| Music state | `boss_penalta` |
| Fail | player_died → phase checkpoint (checkpoint_per_phase on 稽古 and 真剣). Pen residents cannot be harmed. |

Pattern tables are in §2.1 and the YAML `boss_proposals`; L3 ratifies. The arena is the 36 × 24 m Lantern Wharf.

**P1 (100–50%), shield up.** Penalta advances behind a 120° frontal block that deflects arrows and katana alike. He turns slowly (90°/s), which is what makes flanking work.
- **Shield bash:** 600 ms windup with an amber rim pulse and the bark 「ご返済を。」.
- **Hammer slam:** 1000 ms windup with a 350 cm amber ring and the bark 「延滞金が発生しております。」. After a slam he needs 1.8 s to recover, and the two rear cooling vents glow open for 2.0 s.

Counterplay:
- Circle through the staggered cargo stacks to reach his back.
- Awase the bash. It does not stagger him, but it opens the 400 ms 転 (marobashi) window, and the flank step puts the player behind him.
- Shoot or cut the open vents (×2.5 damage).
- Three direct 花火筒 hits break the shield.
- When he stands in the marked drop zone under the shear-leg hoist, cut its rope at the cleat (or shoot the rope). A net of rice bales drops for a 3 s stun.

**P2 (50–0%), shield broken.** If the shield is still intact when he reaches 50%, an overheating vent blowout breaks it. He is now faster, turns at 140°/s, and adds two attacks:
- **Hammer spin:** 1200 ms windup, 400 cm amber ring.
- **延滞 seal traps:** two thrown discs that root for 1.5 s. One arrow or cut destroys a disc.

The second net hangs on the hoist's other hook.

The bamboo pen of seized residents on the west side is protected: attacks stop at its fence. A crate of Tamakichi's shells beside it refills 5 shells once per phase.

**Defeat:** at 0 HP he staggers backward onto the slick 雁木 steps, and the hammer's weight takes him. The outro holds on Nyaakoto; there is a heavy splash, and a cyan glow sinks and goes out. The fall stays off-screen.

**Dialogue triggers:**
- `beat_start` → ch03.b17.penalta.001 (ambient)
- `pattern:hammer_slam` → ch03.b17.penalta.002 (ambient, repeatable)
- `pattern:shield_bash` → ch03.b17.penalta.003 (ambient, repeatable)
- `x_boss_hint:front_blocked` → ch03.b17.kohagi.004 (radio)
- `x_boss_hint:crane` → ch03.b17.kohagi.005 (radio)
- `boss_phase:2` → ch03.b17.penalta.006, ch03.b17.nyaakoto.007 (ambient)
- `pattern:hammer_spin` → ch03.b17.penalta.008 (ambient, repeatable)
- `pattern:seal_trap` → ch03.b17.penalta.009 (ambient, repeatable)
- `player_died` → ch03.b17.penalta.010 (ambient, repeatable)
- `x_boss_defeated` → ch03.b17.penalta.011 (ambient)

#### ch03.b18 · cinematic · 灯が戻る / The lanterns return

| Field | Value |
|---|---|
| Place | `pl_lantern_ward_rain` |
| Target | 1.5 min (90 s) |
| Checkpoint | yes |
| Requires | previous beat |
| Unlocks | — |
| Music state | `ch03_lanterns_relit` |
| Fail | None. |

Pre-dawn, and the rain is easing to drizzle. Nyaakoto cuts the pen's lashing, and the residents' collars are cut one by one; the freed walk up into the main street. There, Tōkichi's forty new lanterns are handed out, each painted with the SORA mon in vermillion on white washi. Oyuki's quiet cue is followed by Nyaakoto's catalog line 3. The first lantern is lit from a kitchen ember and passed flame to flame down the street until the whole ward is a line of warm light reflected in the wet earth. The reverse shot shows the broken terminal dark under the 高札場. Oyuki names the next need, water, and Kohagi leaves for the Lower Village. Nyaakoto looks up the line of lights and speaks to the absent Sekireisai. The chapter-complete screen shows the ch03 registry page: 提灯 40張, 炊き出し 120食.

**Subtitles:** ch03.b18.oyuki.001 @ 10 s, ch03.b18.nyaakoto.002 @ 16 s, ch03.b18.tokichi.003 @ 34 s, ch03.b18.oyuki.004 @ 52 s, ch03.b18.kohagi.005 @ 62 s, ch03.b18.nyaakoto.006 @ 78 s


### 2.3 `boss_penalta` pattern tables (proposal for L3)

HP on Normal is 2000 (Easy 1600, Hard 2400). Windups scale by +30% on Easy and −15% on Hard (bible §8); the Normal values are shown. Every telegraph precedes damage by at least its windup, amber marks area and cleave attacks, and each attack has a captioned voice bark.

| Phase | Attack | Windup | Telegraph | Effect | Recovery | Counterplay |
|---|---|---|---|---|---|---|
| P1 100–50% | Shield advance | — (continuous) | Shield face lit | Pushes 150 cm, 10 dmg on contact; 120° frontal block against melee, arrows and hitscan | — | Flank through the cargo stacks; he turns at only 90°/s |
| P1 | Shield bash | 600 ms (780 / 510) | Amber rim pulse + 「ご返済を。」 | 250 cm range, 25 dmg, 0.6 s stagger | 700 ms | Guard (30 stamina) or awase. Awase does not stagger him but opens the 400 ms 転 window, and the flank step lands behind him |
| P1 | Hammer slam | 1000 ms (1300 / 850) | 350 cm amber ring grows + 「延滞金が発生しております。」 | 45 dmg at the centre, 20 at the edge; knockdown within 150 cm | 1800 ms; vents open for 2000 ms | Leave the ring, then hit the glowing rear vents (×2.5 damage) |
| P1 | (shield) | — | — | Breaks after 3 direct 花火筒 hits, or automatically at 50% HP (vent blowout) | — | Loft shells; hits on the shield do no HP damage |
| P1/P2 | Crane net (environment) | — | Rope sways and highlights amber when he is in the drop zone + Kohagi's hint | 3000 ms stun, damage taken ×1.5 | — | Cut the rope at the cleat, or shoot it; 2 nets, 1 per phase |
| P2 50–0% | Hammer spin | 1200 ms (1560 / 1020) | 400 cm amber ring + 「一括にて、回収いたします。」 | 30 dmg per hit, at most 2 hits over 1.8 s | 2200 ms, dizzy; vents open for 2200 ms | Leave the ring; punish his dizzy recovery from behind |
| P2 | 延滞 seal traps | 700 ms throw (910 / 595) | 150 cm amber decal on landing + 「延滞の印を、押させていただきます。」 | Two discs arm after 800 ms, root for 1.5 s, last 12 s, at most 4 active | — | One arrow or one cut destroys a disc; keep your lanes clear |
| P2 | Hammer slam | 1000 ms | As in P1 | As in P1 | 1800 ms; vents open for 2000 ms | As in P1 |

**Selection.** P1 bashes when the player is in front within 250 cm and the bash is off cooldown (3 s). He slams when the player is within 350 cm on his flank or behind him, or on every third action (7 s cooldown). P2 spins when the player is within 400 cm (10 s cooldown), throws traps when the player is more than 6 m away (9 s cooldown), and otherwise slams (6 s cooldown).

**Movement.** P1 moves at 180 cm/s; P2 at 250 cm/s, turning at 140°/s.

**Phase transition.** At 50% (or at the forced shield break) he roars. The shield splits along its seam, a vent blows steam into the rain, and a 1.5 s invulnerable stagger lets the player reposition. A per-phase checkpoint saves here.

**Fate.** At 0 HP he staggers backward across the slick stone strip. The outro camera (`cin_ch03_penalta_canal`) holds on Nyaakoto: a heavy splash, a cyan glow sinking and going out. The fall stays off-screen (bible §8).

---

## 3. Dialogue: full bilingual script

### 3.1 Conventions

- **Line ids:** `ch03.bMM.<name>.<nnn>`, where nnn is sequential within the beat. The `speaker` field uses the schema-4 speaker id.
- **Durations:** estimates of max(1.2 s, 0.45 s + 0.16 s per JA character, EN length ÷ 15 cps), rounded up to 0.1 s. They will be re-timed to the recorded VO.
- **Checked limits (all lines pass):**
  - EN wraps to at most 2 lines of 42 characters and stays at or below 17 cps (bible §18).
  - JA is at most 32 full-width characters, so it fits two caption lines of 16.
  - Alien EN has no contractions.
- **Triggers:**
  - Bible §12.1 events: `beat_start`, `beat_complete`, `volume_enter:<id>`, `alert_state:<state>`, `progress_at:<x>`, `player_died`, `npc_downed:<id>`, `idle_s:<n>`, `boss_phase:<n>`.
  - `pattern:<id>`, as in the bible's §12.4 example.
  - `cin +N s`, a subtitle time inside a cinematic.
  - `after previous`, the next line of a dialogue beat.
  - `x_…` events are proposals (§6).
  - `+N s` is a delay after the event (YAML `x_delay_s`).
- **Modes:**
  - `ambient`: positional, walk-and-talk, control kept.
  - `radio`: non-positional delivery. It is used for Kohagi's close whispers from the rooftops and implies no device.
  - `cinematic`: goes into the sequence's `subtitles[]`.
  - No ch03 line is `blocking`.
- **Barks:** repeatable combat and stealth barks are recorded once and reused. First-use rows are below; the beats that reuse them are listed under each beat's "Dialogue triggers". Their YAML `x_source` names the enemy types that may speak each line.
- **Humour:** there are two light moments, both within bible §1.2: the posture callback (b01.009 → b04.005) and Tamakichi's whispered repeat (b06.005). The leaflet line (b04.006) is the bible's approved paper-reuse detail. There is no humour in the boss fight, the oath, the rival scene or the blackout.

### 3.2 Speakers

| Speaker id | JA | EN | Status | Lines |
|---|---|---|---|---|
| `samurai` | ニャーコト | Nyaakoto | existing | 22 |
| `scout` | 小萩 | Kohagi | existing | 31 |
| `artisan` | 伊三 | Isa (bamboo-splitter) | existing id; bible remaps the old catalog artisan line to lantern_maker | 3 |
| `lantern_maker` | 灯吉 | Tōkichi | bible §6.2 | 14 |
| `fireworks` | 玉吉 | Tamakichi | bible §6.2 | 9 |
| `leader` | お雪 | Oyuki | bible §6.1 | 16 |
| `rival` | 虎之介 | Toranosuke | bible §6.1 | 3 |
| `boss_penalta` | ペナルタ | Penalta | bible §6.3 | 10 |
| `enforcer` | 執行兵 | Enforcer | proposed generic (as in ch04, ch06–ch08): all alien rank-and-file; voice variants rifle / grenadier / marksman | 11 |
| `conscript` | 債縛衆 | Debt-Bound | proposed generic (as in ch04, ch08): collared townsfolk, incl. the kido-ban | 6 |
| `drone` | 目録 | Inventory drone | proposed generic (as in ch02, ch04): drone barks | 4 |
| `credit_system` | 信用院・告知音声 | Credit House notice voice | proposed in ch02: seals, terminals and PA broadcasts | 4 |
| `resident` | 町の衆 | Resident | proposed generic (as in ch08): voice variants f / elder_f / elder_m / m / mother | 7 |
| `child` | 子ども | Child | proposed generic (as in ch08) | 3 |

**Registers.**
- Nyaakoto:
  - `samurai_plain`: 「だ」 with Kohagi and the craftspeople.
  - `samurai_polite`: 「です」 with Oyuki and elders.
  - `samurai_bark`: low commands.
  - English is measured ("I will", not "I'll").
- Kohagi (`terse`): 「あたし」, clipped counts and directions.
- Tōkichi (`artisan_gentle`): soft, elderly Kamigata speech (「わし」, 「〜や」, 「〜で」).
- Tamakichi (`kamigata_cheerful`): 「わい」, quick and warm.
- Isa (`artisan_gruff`).
- Oyuki (`business_keigo`): 「わたくし」, 「〜でございます」, 「〜くださいまし」; she never raises her voice.
- Toranosuke (`rival_clipped`): 「俺」.
- Aliens (`alien_*`): flat, hyper-polite corporate keigo with financial vocabulary, delivered through the translation-collar DSP (band-limited formant chorus, no pitch shift). They read account numbers digit by digit.
- Conscripts (`townsfolk_compelled`): frightened Yamato townsfolk whose bodies move against their will.
- English for Kamigata speech is warm and colloquial, never a caricatured dialect (bible §18).

### 3.3 Script

#### ch03.b01 · 高瀬舟で提灯街へ / By riverboat to Lantern Ward (9 lines)

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Notes (readings, register) |
|---|---|---|---|---|---|---|
| `ch03.b01.system.001` | cin +8 s | 信用院・告知音声 Credit House notice voice | 告知。本日の利息を、各戸の残高に計上いたしました。 | Notice. Today's interest has been added to each household's balance. | 4.6 | 計上（けいじょう）. Distant PA from a passing drone; flat, band-limited. Register `alien_device_pa`. |
| `ch03.b01.system.002` | cin +16 s | 信用院・告知音声 Credit House notice voice | 消灯の刻限です。無許可の灯火は、延滞として処理いたします。 | It is lights-out. Unlicensed flames will be processed as arrears. | 5.1 | 刻限（こくげん）, 灯火（とうか）, 延滞（えんたい）. Establishes the lamp-licence levy. Register `alien_device_pa`. |
| `ch03.b01.kohagi.003` | cin +31 s | 小萩 Kohagi | 十日で、この有様。 | Ten days, and look at it. | 1.9 | Low, poling the boat. Register `terse`. |
| `ch03.b01.nyaakoto.004` | cin +36 s | ニャーコト Nyaakoto | ……灯りが、一つもない。 | …Not a single light. | 2.4 | Register `samurai_plain`. |
| `ch03.b01.kohagi.005` | cin +42 s | 小萩 Kohagi | 灯せば借りが増える。だから、誰も灯さない。 | Light a lamp and the debt grows. So no one does. | 3.9 | Register `terse`. |
| `ch03.b01.kohagi.006` | cin +63 s | 小萩 Kohagi | 刀と弓は先に運んだ。裏長屋の、空井戸の底。 | Your sword and bow went ahead. Bottom of the dry well, back tenements. | 4.7 | 空井戸（からいど）, 裏長屋（うらながや）. Register `terse`. |
| `ch03.b01.kohagi.007` | cin +71 s | 小萩 Kohagi | それまでは、これで。 | Until then, use this. | 2.1 | Hands over the wakizashi: weapon 4 unlock moment. Register `terse`. |
| `ch03.b01.nyaakoto.008` | cin +76 s | ニャーコト Nyaakoto | 道中差か。……町人に見えるか。 | A travelling short sword. …Do I pass for a townsman? | 3.5 | 道中差（どうちゅうざし）. Register `samurai_plain`. |
| `ch03.b01.kohagi.009` | cin +82 s | 小萩 Kohagi | 背筋、伸ばしすぎ。 | Your back's too straight. | 1.9 | Restrained, character humour; paid off by ch03.b04.child.005. Register `terse`. |

#### ch03.b02 · 河岸を抜けよ / Slip past the landing (10 lines)

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Notes (readings, register) |
|---|---|---|---|---|---|---|
| `ch03.b02.kohagi.001` | `beat_start` | 小萩 Kohagi | 提灯街の工房は三つとも止められた。 | All three workshops in Lantern Ward have been shut down. | 3.8 | Catalog anchor line 1 (speaker `scout`), text kept verbatim. Register `terse`. |
| `ch03.b02.kohagi.002` | `volume_enter:vol_b02_drones` | 小萩 Kohagi | 目録が二つ、水の上。光の輪に入らないで。 | Two Inventories over the water. Stay out of their light. | 3.8 | 目録（もくろく）: locals' name for the drones. Tutorial: drone light cone. Register `terse`. |
| `ch03.b02.kohagi.003` | `volume_enter:vol_b02_puddles` | 小萩 Kohagi | 水たまりは鳴る。雨でも。 | Puddles splash loud. Even in the rain. | 2.6 | Tutorial: puddle noise. Register `terse`. |
| `ch03.b02.kohagi.004` | `volume_enter:vol_b02_andon` | 小萩 Kohagi | 行灯は消せる。暗いほど、見つからない。 | You can snuff the lamps. The darker, the safer. | 3.5 | 行灯（あんどん）. Tutorial: extinguishable light. Register `terse`. |
| `ch03.b02.drone.005` | `alert_state:suspicious` | 目録 Inventory drone | ……未登録の熱源を検知。 | …Unregistered heat source detected. | 2.4 | Shared drone bark set (first use). Captioned. Repeatable. Register `alien_device`. |
| `ch03.b02.drone.006` | `alert_state:alert` | 目録 Inventory drone | 債務者を捕捉。番号を照合します。 | Debtor acquired. Verifying account number. | 3.1 | 捕捉（ほそく）, 照合（しょうごう）. Repeatable. Register `alien_device`. |
| `ch03.b02.drone.007` | `alert_state:search` | 目録 Inventory drone | 照合できません。捜索を継続いたします。 | Unable to verify. Search continues. | 3.5 | Repeatable. Register `alien_device`. |
| `ch03.b02.drone.008` | `x_alert_state:search_to_unaware` | 目録 Inventory drone | 記録なし。巡回に戻ります。 | No record. Resuming patrol. | 2.6 | Plays when a search times out (search → unaware). Repeatable. Register `alien_device`. |
| `ch03.b02.kohagi.009` | `beat_complete` | 小萩 Kohagi | 木戸は北。あたしは屋根から行く。 | The ward gate is north. I'll take the roofs. | 3.1 | 木戸（きど）. Register `terse`. |
| `ch03.b02.kohagi.010` | `player_died` | 小萩 Kohagi | ……もう一度。今度は、静かに。 | …Again. Quieter this time. | 2.9 | Chapter-wide stealth retry line (b02, b03, b05, b07, b10). Plays after reload. Repeatable. Register `terse`. |

#### ch03.b03 · 木戸を越えよ / Get through the ward gate (11 lines)

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Notes (readings, register) |
|---|---|---|---|---|---|---|
| `ch03.b03.kohagi.001` | `beat_start` | 小萩 Kohagi | 番は五人。首輪の三人は、町の者。 | Five guards. The three in collars are townsfolk. | 3.2 | Register `terse`. |
| `ch03.b03.kohagi.002` | `volume_enter:vol_b03_first_conscript` | 小萩 Kohagi | 首輪の者は斬らないで。峰で倒して、首輪を切る。 | Don't cut the collared. Use the blade's back, then cut the collar. | 4.4 | 峰（みね）. Tutorial: 峰打ち + seal-cut. Register `terse`. |
| `ch03.b03.kohagi.003` | `volume_enter:vol_b03_bansho_rear` | 小萩 Kohagi | 後ろを取れば、声も出させずに済む。 | Take them from behind and they won't make a sound. | 3.4 | Tutorial: rear takedown. Register `terse`. |
| `ch03.b03.conscript.004` | `alert_state:suspicious` | 債縛衆 Debt-Bound | ……誰や？　誰か、おるんか。 | …Who's that? Is someone there? | 2.7 | Shared conscript bark set (first use). Repeatable. Register `townsfolk_compelled`. |
| `ch03.b03.conscript.005` | `alert_state:alert` | 債縛衆 Debt-Bound | 堪忍や……体が、勝手に……！ | Forgive me… my body won't stop…! | 2.7 | 堪忍（かんにん）. The collar drives the body; the voice resists. Repeatable. Register `townsfolk_compelled`. |
| `ch03.b03.conscript.006` | `x_alert_state:search_to_unaware` | 債縛衆 Debt-Bound | ……おらん。おらんかった、ことにしとこ。 | …Nobody. Let's say there was nobody. | 3.7 | Reluctance, not comedy: deliver tired and quiet. Repeatable. Register `townsfolk_compelled`. |
| `ch03.b03.enforcer.007` | `alert_state:suspicious` | 執行兵 Enforcer | 確認いたします。その場を動かないでください。 | Verifying. Please remain where you are. | 4.0 | Shared enforcer bark set (first use). Repeatable. Register `alien_corporate`. |
| `ch03.b03.enforcer.008` | `alert_state:alert` | 執行兵 Enforcer | 未払い者を確認。回収を開始します。 | Non-payer confirmed. Commencing collection. | 3.2 | Repeatable. Register `alien_corporate`. |
| `ch03.b03.enforcer.009` | `alert_state:search` | 執行兵 Enforcer | 記録上、この位置に存在するはずです。 | Per the record, you should exist at this location. | 3.4 | Literal-minded; no contraction in EN. Repeatable. Register `alien_corporate`. |
| `ch03.b03.kidoban.010` | `x_npc_freed:kidoban` | 債縛衆 Debt-Bound | ……軽い。首が、軽い。 | …Light. My neck feels light. | 2.3 | Kido-ban (gatekeeper), first collar cut. Register `townsfolk_elder`. |
| `ch03.b03.kidoban.011` | `x_npc_freed:kidoban +2 s` | 債縛衆 Debt-Bound | 潜り戸の閂は、外してある。行きなされ。 | The wicket's bar is off. Go on through. | 3.5 | 潜り戸（くぐりど）, 閂（かんぬき）. Opens the wicket route. Register `townsfolk_elder`. |

#### ch03.b04 · 裏長屋を歩け / Walk the back tenements (7 lines)

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Notes (readings, register) |
|---|---|---|---|---|---|---|
| `ch03.b04.resident.001` | `volume_enter:poi_idobata` | 町の衆 Resident | うちの戸の数、また増えとる。寝とる間に。 | The number on my door went up again. While I slept. | 3.7 | Well-side gossip (井戸端), woman A. Register `townsfolk_f`. |
| `ch03.b04.resident.002` | `volume_enter:poi_idobata +4 s` | 町の衆 Resident | 働く前から借りがある。けったいな世の中や。 | In debt before you've worked a day. Strange world. | 3.9 | Woman B. けったい = odd (Kamigata). Register `townsfolk_f`. |
| `ch03.b04.resident.003` | `volume_enter:poi_idobata +9 s` | 町の衆 Resident | お侍さんやったら、こんな時どないしはるやろな。 | What would a samurai do at a time like this, I wonder. | 4.2 | Dramatic irony: she does not know he is one. Register `townsfolk_elder_f`. |
| `ch03.b04.child.004` | `volume_enter:poi_chalk` | 子ども Child | これな、空の紋。描いたら、あいつら怒るねん。 | This is the sky crest. They get angry when we draw it. | 4.0 | Child chalking the SORA mon at child height. Register `child`. |
| `ch03.b04.child.005` | `volume_enter:poi_chalk +5 s` | 子ども Child | お兄ちゃん、お侍？　歩き方が、お侍や。 | Mister, are you a samurai? You walk like one. | 3.5 | Callback to ch03.b01.kohagi.009. Restrained humour (1 of 2 this chapter). Register `child`. |
| `ch03.b04.resident.006` | `volume_enter:poi_leaflet` | 町の衆 Resident | 紙だけは上等や。提灯の紙にしたろ。 | Their paper's good, at least. It'll make fine lanterns. | 3.7 | Leaflet reused as lantern paper (bible §15.2). Register `townsfolk_elder_m`. |
| `ch03.b04.nyaakoto.007` | `volume_enter:poi_balance_door` | ニャーコト Nyaakoto | ……数で、人を縛るのか。 | …They bind people with numbers. | 2.4 | At the widow's glowing door; seizure-notice collectible beside it. Register `samurai_plain`. |

#### ch03.b05 · 空井戸の道具を運べ / Carry the hidden tools (6 lines)

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Notes (readings, register) |
|---|---|---|---|---|---|---|
| `ch03.b05.kohagi.001` | `beat_start` | 小萩 Kohagi | その井戸。縄は結んである。 | That well. The rope's tied off. | 2.6 | Register `terse`. |
| `ch03.b05.nyaakoto.002` | `x_item_picked:sword_bundle` | ニャーコト Nyaakoto | 刀は民から預かるもの……。預かり直す。 | A blade is held in trust from the people. …I take it up again. | 4.2 | Callback to ch01.b12 「刀は民から預かるものじゃ」. Quiet, not heroic. Register `samurai_plain`. |
| `ch03.b05.kohagi.003` | `x_item_picked:sword_bundle +4 s` | 小萩 Kohagi | 箱は三つ。釣瓶で上げて、灯吉さんのとこへ。 | Three crates. Haul them up on the well rope, then take them to Tōkichi. | 4.8 | 釣瓶（つるべ）. Register `terse`. |
| `ch03.b05.conscript.004` | `volume_enter:vol_b05_alley_mouth` | 債縛衆 Debt-Bound | 雨の見回りは、骨にこたえる……。 | Rain patrols get into your bones… | 3.1 | Passing patrol, unaware. One-shot. Register `townsfolk_compelled`. |
| `ch03.b05.tokichi.005` | `progress_at:0.33` | 灯吉 Tōkichi | おお……わしの型や。よう無事で。 | Oh… my forms. Safe and sound. | 3.1 | 型（かた）: the wooden lantern forms. Register `artisan_gentle`. |
| `ch03.b05.tokichi.006` | `beat_complete` | 灯吉 Tōkichi | これで全部や。おおきに、お侍さん。 | That's all of them. Thank you, samurai. | 3.2 | Register `artisan_gentle`. |

#### ch03.b06 · 灯吉と玉吉 / Tōkichi and Tamakichi (8 lines)

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Notes (readings, register) |
|---|---|---|---|---|---|---|
| `ch03.b06.tokichi.001` | `beat_start` | 灯吉 Tōkichi | 道具は隠した。火さえ戻れば、また作れる。 | We hid the tools. Restore the fires, and we can make things again. | 4.4 | Catalog anchor line 2 (speaker `artisan` → `lantern_maker`), text verbatim. Register `artisan_gentle`. |
| `ch03.b06.tokichi.002` | after previous | 灯吉 Tōkichi | けど工房の戸に、あの青い封が貼られとる。 | But that blue seal is fixed on the workshop door. | 3.7 | 封（ふう）: the debt seal. Register `artisan_gentle`. |
| `ch03.b06.tamakichi.003` | after previous | 玉吉 Tamakichi | 封なら、わいが吹っ飛ばしたる！ | A seal? I'll blow it clean off! | 2.9 | Too loud. Register `kamigata_cheerful`. |
| `ch03.b06.tokichi.004` | after previous | 灯吉 Tōkichi | 玉吉、声。 | Tamakichi. Your voice. | 1.5 | Register `artisan_gentle`. |
| `ch03.b06.tamakichi.005` | after previous | 玉吉 Tamakichi | ……吹っ飛ばしたる。 | …I'll blow it clean off. | 2.1 | Whispered repeat. Restrained humour (2 of 2 this chapter). Register `kamigata_cheerful`. |
| `ch03.b06.tamakichi.006` | after previous | 玉吉 Tamakichi | 祭りの玉が十二、床下にある。筒さえ組めば、武器になるで。 | Twelve festival shells under the floor. Build a tube and they're a weapon. | 5.0 | 玉（たま）: firework shell. Register `kamigata_cheerful`. |
| `ch03.b06.nyaakoto.007` | after previous | ニャーコト Nyaakoto | 工房までは私が守る。皆、私の合図で伏せてくれ。 | I will guard you to the workshop. Everyone, get down on my signal. | 4.4 | Sets up hide_on_signal. Register `samurai_polite`. |
| `ch03.b06.kohagi.008` | after previous | 小萩 Kohagi | 裏道は見てきた。見回りは三組。 | I've checked the back way. Three patrols. | 2.9 | Register `terse`. |

#### ch03.b07 · 職人たちを工房へ / Escort the craftspeople to the workshop (10 lines)

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Notes (readings, register) |
|---|---|---|---|---|---|---|
| `ch03.b07.kohagi.001` | `beat_start` | 小萩 Kohagi | 一組目は辻。目録が過ぎるまで待って。 | First patrol's at the crossing. Wait for the Inventory to pass. | 4.2 | 辻（つじ）. Register `terse`. |
| `ch03.b07.isa.002` | `beat_start +6 s` | 伊三 Isa (bamboo-splitter) | 竹割りの伊三や。足は遅いが、口は堅いで。 | Isa, bamboo-splitter. Slow feet, tight lips. | 3.7 | Register `artisan_gruff`. |
| `ch03.b07.nyaakoto.003` | `x_signal:hide` | ニャーコト Nyaakoto | 伏せろ。 | Down. | 1.2 | Player signal; low voice. Repeatable. Register `samurai_bark`. |
| `ch03.b07.nyaakoto.004` | `x_signal:go` | ニャーコト Nyaakoto | 今だ。進め。 | Now. Move. | 1.5 | Player signal; low voice. Repeatable. Register `samurai_bark`. |
| `ch03.b07.tamakichi.005` | `volume_enter:vol_b07_patrol1` | 玉吉 Tamakichi | ……心の臓が、玉みたいに跳ねとる。 | …My heart's jumping like a shell. | 3.2 | 心の臓（しんのぞう）. Whispered, frightened. Register `kamigata_cheerful`. |
| `ch03.b07.tokichi.006` | `volume_enter:vol_b07_oilshop` | 灯吉 Tōkichi | ここは油屋やった。灯りの油も、今は奴らの帳面の中や。 | This was the oil shop. Now even lamp oil lives in their ledger. | 4.7 | 油屋（あぶらや）. Register `artisan_gentle`. |
| `ch03.b07.isa.007` | `npc_downed:isa` | 伊三 Isa (bamboo-splitter) | すまん、足が……！ | Sorry—my leg…! | 1.9 | Other escorts use non-verbal efforts when downed. Repeatable. Register `artisan_gruff`. |
| `ch03.b07.nyaakoto.008` | `x_npc_revived:any` | ニャーコト Nyaakoto | 立てるか。肩を貸す。 | Can you stand? Lean on me. | 2.1 | Repeatable. Register `samurai_plain`. |
| `ch03.b07.kohagi.009` | `volume_enter:vol_b07_patrol3` | 小萩 Kohagi | 最後の組は蔵の裏。刀持ちがいる。 | Last patrol's behind the storehouse. One carries a blade. | 3.8 | 蔵（くら）. Register `terse`. |
| `ch03.b07.tokichi.010` | `beat_complete` | 灯吉 Tōkichi | 着いた……。ここが、わしの工房や。 | We made it… This is my workshop. | 3.2 | Register `artisan_gentle`. |

#### ch03.b08 · 工房の庭を守れ / Hold the workshop yard (8 lines)

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Notes (readings, register) |
|---|---|---|---|---|---|---|
| `ch03.b08.system.001` | `beat_start` | 信用院・告知音声 Credit House notice voice | 封印への接触を検知。執行班を要請します。 | Seal contact detected. Requesting an enforcement team. | 3.7 | The debt seal on the workshop door speaks with the Credit House notice voice (ch02 `credit_system`). Register `alien_device`. |
| `ch03.b08.nyaakoto.002` | `beat_start +3 s` | ニャーコト Nyaakoto | 中へ！　戸を閉めて、伏せていろ。 | Inside! Close the door and stay down. | 3.1 | Register `samurai_bark`. |
| `ch03.b08.tokichi.003` | `beat_start +6 s` | 灯吉 Tōkichi | 頼んだで……！ | We're counting on you…! | 1.6 | Register `artisan_gentle`. |
| `ch03.b08.enforcer.004` | `x_wave_start:1` | 執行兵 Enforcer | 業務妨害を確認。関係者全員が回収対象です。 | Obstruction confirmed. All involved parties are subject to collection. | 4.7 | 業務妨害（ぎょうむぼうがい）. Register `alien_corporate`. |
| `ch03.b08.grenadier.005` | `pattern:grenadier_fire` | 執行兵 Enforcer | 区画を整理いたします。 | Clearing the section. | 2.3 | Audio telegraph at shell launch; shared grenadier bark. Repeatable. Register `alien_corporate_grenadier`. |
| `ch03.b08.enforcer.006` | `x_ai:withdraw` | 執行兵 Enforcer | 損失を計上。後退いたします。 | Loss recorded. Withdrawing. | 2.7 | Shared retreat bark. Repeatable. Register `alien_corporate`. |
| `ch03.b08.tamakichi.007` | `beat_complete` | 玉吉 Tamakichi | ……静かになった。もう、ええか？ | …It's gone quiet. Is it safe? | 3.1 | From behind the door. Register `kamigata_cheerful`. |
| `ch03.b08.kohagi.008` | `player_died` | 小萩 Kohagi | 立って。まだ終わってない。 | Get up. It isn't over. | 2.6 | Chapter-wide combat retry line (b08, b14, b16). Plays after reload. Repeatable. Register `terse`. |

#### ch03.b09 · 提灯を張れ / Make the lanterns (9 lines)

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Notes (readings, register) |
|---|---|---|---|---|---|---|
| `ch03.b09.tokichi.001` | `beat_start` | 灯吉 Tōkichi | 竹を割って、輪にする。型に掛けて、六つや。 | Split the bamboo, bend it into hoops. Six on the form. | 3.9 | 輪（わ）骨. Tutorial: bend step. Register `artisan_gentle`. |
| `ch03.b09.tokichi.002` | `progress_at:0.3` | 灯吉 Tōkichi | そうや。力やない、竹の癖に合わせるんや。 | That's it. Not force—follow the bamboo's grain. | 3.7 | 癖（くせ）. Echoes the school: go with, not against. Register `artisan_gentle`. |
| `ch03.b09.tokichi.003` | `progress_at:0.5` | 灯吉 Tōkichi | 紙は継ぎ目を重ねて貼る。雨が入らんようにな。 | Overlap the seams as you paste. Keep the rain out. | 4.0 | 継ぎ目（つぎめ）. Register `artisan_gentle`. |
| `ch03.b09.tokichi.004` | `progress_at:0.65` | 灯吉 Tōkichi | 仕上げに荏の油を引く。これで五月雨にも負けん。 | Finish with perilla oil. Then it will stand up to the rains. | 4.2 | 荏の油（えのあぶら）, 五月雨（さみだれ）. Register `artisan_gentle`. |
| `ch03.b09.nyaakoto.005` | `progress_at:0.72` | ニャーコト Nyaakoto | ……刀より、難しい。 | …Harder than the sword. | 2.1 | Understated. Register `samurai_plain`. |
| `ch03.b09.isa.006` | `progress_at:0.78` | 伊三 Isa (bamboo-splitter) | 四十張、朝までに仕上げたる。 | Forty lanterns, done by morning. | 2.7 | 張（はり）: counter for lanterns. Register `artisan_gruff`. |
| `ch03.b09.tamakichi.007` | `progress_at:0.8` | 玉吉 Tamakichi | 次はこっちや。玉を紙で巻いて、筒に合わせる。 | Over here now. Wrap the shell in paper, fit it to the tube. | 4.0 | Station 2 (yard, away from the oil). Register `kamigata_cheerful`. |
| `ch03.b09.tamakichi.008` | `beat_complete` | 玉吉 Tamakichi | ほれ、花火筒や。高う上げて落とす。弧を読むんやで。 | Here—the shell tube. Loft it high and let it fall. Read the arc. | 4.5 | 花火筒（はなびづつ）: in-fiction name of weapon 7 (UI: 擲弾筒). Register `kamigata_cheerful`. |
| `ch03.b09.tamakichi.009` | `beat_complete +5 s` | 玉吉 Tamakichi | 近うで撃ったら、自分も焦げるで。 | Fire it up close and you'll get singed too. | 3.1 | Self-damage warning (catalog tradeoff). Register `kamigata_cheerful`. |

#### ch03.b10 · 端末に火薬を仕掛けよ / Plant a charge on the debt terminal (8 lines)

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Notes (readings, register) |
|---|---|---|---|---|---|---|
| `ch03.b10.kohagi.001` | `beat_start` | 小萩 Kohagi | 高札場。端末の上、屋根に鉄砲持ちが一人。 | The notice square. A marksman on the roof above the terminal. | 4.1 | 高札場（こうさつば）. Register `terse`. |
| `ch03.b10.kohagi.002` | `volume_enter:vol_b10_glint` | 小萩 Kohagi | 光ったら、狙われてる。すぐ物陰へ。 | If you see a glint, you're targeted. Get behind cover. | 3.6 | Tutorial: marksman 900 ms glint. Register `terse`. |
| `ch03.b10.kohagi.003` | `volume_enter:vol_b10_dobuita` | 小萩 Kohagi | 溝板は鳴る。端を踏んで。 | The drain boards rattle. Walk the edges. | 2.7 | 溝板（どぶいた）. Tutorial: loose drain covers. Register `terse`. |
| `ch03.b10.system.004` | `idle_s:20` | 信用院・告知音声 Credit House notice voice | 端末は、正常に稼働しております。 | The terminal is operating normally. | 3.1 | From the terminal speaker. Register `alien_device_pa`. |
| `ch03.b10.marksman.005` | `alert_state:suspicious` | 執行兵 Enforcer | 照準内に不明な影。査定します。 | Unknown shadow in my sights. Assessing. | 2.9 | Shared marksman bark set (first use). Repeatable. Register `alien_corporate_marksman`. |
| `ch03.b10.marksman.006` | `alert_state:alert` | 執行兵 Enforcer | 査定完了。価値、なし。 | Assessment complete. Value: none. | 2.3 | Plays at the start of the 900 ms glint lock: audio telegraph. Repeatable. Register `alien_corporate_marksman`. |
| `ch03.b10.enforcer.007` | `x_reinforce:w_b10_reinforce` | 執行兵 Enforcer | 端末付近に不正接触。至急、増援を。 | Unauthorized contact near the terminal. Reinforcements, at once. | 4.3 | Register `alien_corporate`. |
| `ch03.b10.nyaakoto.008` | `x_objective:obj_light_fuse` | ニャーコト Nyaakoto | 火縄に火を。……離れる。 | Light the fuse. …Now, clear out. | 2.4 | 火縄（ひなわ）: slow-match fuse on Tamakichi's charge. Register `samurai_plain`. |

#### ch03.b11 · 数字が消える / The numbers go dark (4 lines)

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Notes (readings, register) |
|---|---|---|---|---|---|---|
| `ch03.b11.resident.001` | cin +24 s | 町の衆 Resident | ……戸の数が、消えた。 | …The number on the door. It's gone. | 2.4 | Register `townsfolk_mother`. |
| `ch03.b11.child.002` | cin +31 s | 子ども Child | 母ちゃん、外、出てもええの？ | Mama, can we go outside? | 2.7 | Register `child`. |
| `ch03.b11.resident.003` | cin +36 s | 町の衆 Resident | ……ええよ。雨やけど、ええよ。 | …Yes. It's raining, but yes. | 2.9 | Register `townsfolk_mother`. |
| `ch03.b11.nyaakoto.004` | cin +70 s | ニャーコト Nyaakoto | 消えたのは端末一つ。帳面は、まだどこかにある。 | One terminal is gone. The ledger is still out there. | 4.2 | Sets up ch06. Register `samurai_plain`. |

#### ch03.b12 · 白澄お雪 / Shirasumi Oyuki (8 lines)

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Notes (readings, register) |
|---|---|---|---|---|---|---|
| `ch03.b12.oyuki.001` | `beat_start` | お雪 Oyuki | 見事な火薬でございました。ただ、あれは帳簿の写しにすぎません。 | Splendid powder. But that was only a copy of their ledger. | 5.5 | 写し（うつし）. Register `business_keigo`. |
| `ch03.b12.nyaakoto.002` | after previous | ニャーコト Nyaakoto | ……どなたか。 | …And you are? | 1.6 | Register `samurai_polite`. |
| `ch03.b12.oyuki.003` | after previous | お雪 Oyuki | 白澄の雪と申します。父に代わり、勘定を預かっておりました。 | Oyuki, of the Shirasumi. I kept the domain accounts for my father. | 5.1 | 白澄（しらすみ）, 勘定（かんじょう）. She omits the familiar お when naming herself. Register `business_keigo`. |
| `ch03.b12.oyuki.004` | after previous | お雪 Oyuki | 彼らの“信用”は、借りとして生まれるのです。 | Their 'credit' is born as debt. | 4.0 | Bible §13 key line. 信用（しんよう）. Register `business_keigo`. |
| `ch03.b12.oyuki.005` | after previous | お雪 Oyuki | 無から貸し、利を付ける。返す物など、どこにもございません。 | They lend from nothing and add interest. What is owed exists nowhere. | 5.1 | 利（り）: interest. Register `business_keigo`. |
| `ch03.b12.nyaakoto.006` | after previous | ニャーコト Nyaakoto | では、いかがすれば。 | Then what is to be done? | 2.1 | Register `samurai_polite`. |
| `ch03.b12.oyuki.007` | after previous | お雪 Oyuki | 作った物だけを数えるのです。今夜の提灯は、確かにございます。 | We count only what is made. Tonight's lanterns—those are real. | 5.3 | Seeds charter article 1 (物なくして札なし). Register `business_keigo`. |
| `ch03.b12.oyuki.008` | after previous | お雪 Oyuki | 皆様、長屋にお集まりです。一揆を、結びとうございます。 | Everyone waits at the tenements. I wish to bind a league. | 4.8 | 一揆（いっき）を結ぶ: period phrase for forming a sworn league. Register `business_keigo`. |

#### ch03.b13 · 一味神水 / The shared sacred water (8 lines)

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Notes (readings, register) |
|---|---|---|---|---|---|---|
| `ch03.b13.oyuki.001` | cin +6 s | お雪 Oyuki | これより、一味神水の儀を執り行います。 | We now begin the rite of the shared sacred water. | 3.5 | 一味神水（いちみしんすい）. Formal, quiet. Register `business_keigo`. |
| `ch03.b13.oyuki.002` | cin +18 s | お雪 Oyuki | 名は輪にして書きます。誰が先でも、後でもございません。 | We sign in a circle. No one is first, and no one last. | 4.8 | The 傘連判状 rationale (flagged stretch, §4.5). Register `business_keigo`. |
| `ch03.b13.tokichi.003` | cin +29 s | 灯吉 Tōkichi | 輪の真ん中には、空の紋を。 | And the sky crest at the centre. | 2.6 | Register `artisan_gentle`. |
| `ch03.b13.nyaakoto.004` | cin +35 s | ニャーコト Nyaakoto | 猫柳生の紋です。……我が師の、家の紋です。 | The crest of Nyaagyu. …My master's house. | 3.9 | 猫柳生（ニャーギュウ）. Register `samurai_polite`. |
| `ch03.b13.oyuki.005` | cin +43 s | お雪 Oyuki | では今日からは、皆の紋に。 | Then from today, it belongs to all of us. | 2.8 | Register `business_keigo`. |
| `ch03.b13.kohagi.006` | cin +62 s | 小萩 Kohagi | あたし、字は書けない。印でいい？ | I can't write. Will a mark do? | 3.1 | 略押 / 筆軸印 (see §4.5). Register `terse`. |
| `ch03.b13.oyuki.007` | cin +67 s | お雪 Oyuki | 印で十分でございます。 | A mark is quite enough. | 2.3 | Register `business_keigo`. |
| `ch03.b13.nyaakoto.008` | cin +98 s | ニャーコト Nyaakoto | 斬るのは最後だ。まず、守るものを数える。 | Cutting comes last. First, count what we protect. | 3.7 | Bible §6.5 register anchor; spoken after drinking the water. Register `samurai_plain`. |

#### ch03.b14 · 炊き出しを守れ / Keep the communal kitchen going (8 lines)

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Notes (readings, register) |
|---|---|---|---|---|---|---|
| `ch03.b14.oyuki.001` | `beat_start` | お雪 Oyuki | 炊き出しを始めます。火を絶やさず、列をお守りくださいまし。 | We begin serving. Keep the fires lit and guard the line. | 5.1 | 炊き出し（たきだし）. Register `business_keigo`. |
| `ch03.b14.oyuki.002` | `beat_start +7 s` | お雪 Oyuki | 米は町の蔵から。差し押さえの前に、帳面から外しておきました。 | The rice is from the ward store. I took it off their books first. | 5.3 | 差し押さえ（さしおさえ）. Register `business_keigo`. |
| `ch03.b14.resident.003` | `progress_at:0.15` | 町の衆 Resident | 温かい飯なんて、十日ぶりや。 | First hot meal in ten days. | 2.7 | In the queue. Register `townsfolk_m`. |
| `ch03.b14.kohagi.004` | `progress_at:0.28` | 小萩 Kohagi | 見回りが来る。路地の口。 | Patrol coming. Mouth of the alley. | 2.4 | Warns ~2 s before wave 1. Register `terse`. |
| `ch03.b14.enforcer.005` | `x_wave_start:1` | 執行兵 Enforcer | 無許可の集会を確認。帳簿に記載いたします。 | Unlicensed assembly observed. Entering it in the ledger. | 3.9 | Register `alien_corporate`. |
| `ch03.b14.oyuki.006` | `x_fire_out` | お雪 Oyuki | 竈の火が細っております。 | A cook-fire is dying down. | 2.4 | 竈（かまど）. Repeatable. Register `business_keigo`. |
| `ch03.b14.tamakichi.007` | `volume_enter:vol_b14_supply` | 玉吉 Tamakichi | 玉はここに置いとく。要るだけ持っていき。 | I'll leave shells here. Take what you need. | 3.7 | Supply point. Register `kamigata_cheerful`. |
| `ch03.b14.oyuki.008` | `beat_complete` | お雪 Oyuki | 提灯四十張、炊き出し百二十食。……書き留めました。 | Forty lanterns. A hundred and twenty meals. …Recorded. | 4.5 | First in-fiction record; the formal 生産改帳 opens in ch04. Register `business_keigo`. |

#### ch03.b15 · 灰色の羽織 / The grey haori (8 lines)

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Notes (readings, register) |
|---|---|---|---|---|---|---|
| `ch03.b15.kohagi.001` | cin +4 s | 小萩 Kohagi | 河岸で人を集めてる。……担保だって。 | They're rounding people up at the wharf. …As collateral. | 3.8 | 河岸（かし）, 担保（たんぽ）. Register `terse`. |
| `ch03.b15.penalta.002` | cin +17 s | ペナルタ Penalta | 端末損壊の弁済として、当区画の住民を担保に計上いたします。 | For damages to the terminal, residents are now booked as collateral. | 5.1 | 損壊（そんかい）, 弁済（べんさい）. Register `alien_corporate_boss`. |
| `ch03.b15.nyaakoto.003` | cin +31 s | ニャーコト Nyaakoto | ……虎之介？ | …Toranosuke? | 1.5 | Register `samurai_plain`. |
| `ch03.b15.toranosuke.004` | cin +35 s | 虎之介 Toranosuke | 見るな、ニャーコト。 | Do not look at me, Nyaakoto. | 2.1 | Register `rival_clipped`. |
| `ch03.b15.toranosuke.005` | cin +40 s | 虎之介 Toranosuke | うちの家の借りは、買われた。今の俺は、奴らの物だ。 | My house's debt was bought. I am theirs now. | 4.5 | Bible §9 key line. Register `rival_clipped`. |
| `ch03.b15.nyaakoto.006` | cin +49 s | ニャーコト Nyaakoto | その羽織は、似合わない。 | That haori does not suit you. | 2.4 | 羽織（はおり）. Register `samurai_plain`. |
| `ch03.b15.toranosuke.007` | cin +54 s | 虎之介 Toranosuke | ……黙れ。 | …Silence. | 1.3 | He boards a boat with the ledger chest and leaves. Register `rival_clipped`. |
| `ch03.b15.penalta.008` | cin +63 s | ペナルタ Penalta | 債務者番号二二〇四、鷲尾殿。帳簿を城へお運びください。 | Debtor two-two-zero-four, Washio. Kindly deliver the ledger to the citadel. | 5.0 | Number read digit by digit: に・に・れい・よん. 鷲尾（わしお）. Register `alien_corporate_boss`. |

#### ch03.b16 · 河岸へ急げ / Fight through to the wharf (4 lines)

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Notes (readings, register) |
|---|---|---|---|---|---|---|
| `ch03.b16.kohagi.001` | `beat_start` | 小萩 Kohagi | 屋根に二人！　花火筒で落として！ | Two on the roofs! Knock them down with the shell tube! | 3.6 | Register `terse`. |
| `ch03.b16.enforcer.002` | `x_wave_start:1` | 執行兵 Enforcer | 追跡中。対象は河岸方面へ移動。 | In pursuit. Target moving toward the wharf. | 2.9 | Register `alien_corporate`. |
| `ch03.b16.nyaakoto.003` | `volume_enter:vol_b16_mid` | ニャーコト Nyaakoto | 河岸へ。一人も渡さぬ。 | To the wharf. We give up no one. | 2.3 | 渡さぬ: archaic negative, measured. Register `samurai_plain`. |
| `ch03.b16.kohagi.004` | `x_wave_start:2` | 小萩 Kohagi | 右の蔵、屋根の上！ | Right storehouse—on the roof! | 2.0 | Calls marksman 2. Register `terse`. |

#### ch03.b17 · 取立頭ペナルタを倒せ / Defeat Enforcer-Chief Penalta (11 lines)

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Notes (readings, register) |
|---|---|---|---|---|---|---|
| `ch03.b17.penalta.001` | `beat_start` | ペナルタ Penalta | 債務者番号、未登録。……では、新規にお作りいたします。 | Account number: unregistered. …Then we shall open one for you. | 4.8 | Intro bark during the 6 s camera blend. Register `alien_corporate_boss`. |
| `ch03.b17.penalta.002` | `pattern:hammer_slam` | ペナルタ Penalta | 延滞金が発生しております。 | Late fees have been incurred. | 2.6 | Bible §8 voice telegraph. Starts with the 1000 ms windup; captioned. Repeatable. Register `alien_corporate_boss`. |
| `ch03.b17.penalta.003` | `pattern:shield_bash` | ペナルタ Penalta | ご返済を。 | Repayment, please. | 1.3 | Starts with the 600 ms windup; captioned. Repeatable. Register `alien_corporate_boss`. |
| `ch03.b17.kohagi.004` | `x_boss_hint:front_blocked` | 小萩 Kohagi | 前は無駄！　回り込んで、背中の排気口！ | The front's no use! Get round—the vents on his back! | 3.5 | After 4 blocked frontal hits in P1. Register `terse`. |
| `ch03.b17.kohagi.005` | `x_boss_hint:crane` | 小萩 Kohagi | 上の網！　綱を切れば落ちる！ | The net above! Cut the rope and it drops! | 2.8 | First time Penalta enters the crane drop zone. Register `terse`. |
| `ch03.b17.penalta.006` | `boss_phase:2` | ペナルタ Penalta | ……盾の損耗は、貴殿の口座に計上いたします。 | …The shield's depreciation will be charged to your account. | 4.0 | 損耗（そんもう）, 貴殿（きでん）. Register `alien_corporate_boss`. |
| `ch03.b17.nyaakoto.007` | `boss_phase:2 +3 s` | ニャーコト Nyaakoto | 重さに頼る者は、重さに崩れる。 | Those who lean on weight fall by it. | 2.9 | Marobashi principle, said to himself. Register `samurai_plain`. |
| `ch03.b17.penalta.008` | `pattern:hammer_spin` | ペナルタ Penalta | 一括にて、回収いたします。 | Collecting in full. | 2.6 | 一括（いっかつ）. Starts with the 1200 ms windup. Repeatable. Register `alien_corporate_boss`. |
| `ch03.b17.penalta.009` | `pattern:seal_trap` | ペナルタ Penalta | 延滞の印を、押させていただきます。 | Allow me to stamp you delinquent. | 3.2 | Starts with the 700 ms throw windup. Repeatable. Register `alien_corporate_boss`. |
| `ch03.b17.penalta.010` | `player_died` | ペナルタ Penalta | お支払い、ありがとうございました。 | Thank you for your payment. | 3.2 | Plays over the death fade, before reload. Repeatable. Register `alien_corporate_boss`. |
| `ch03.b17.penalta.011` | `x_boss_defeated` | ペナルタ Penalta | ……計算に……ない…… | …This is not… in the calculation… | 2.3 | Outro, as he slides on the wet steps. Fall happens off-screen. Register `alien_corporate_boss`. |

#### ch03.b18 · 灯が戻る / The lanterns return (6 lines)

| Line id | Trigger | Speaker | Japanese | English subtitle | s | Notes (readings, register) |
|---|---|---|---|---|---|---|
| `ch03.b18.oyuki.001` | cin +10 s | お雪 Oyuki | 皆様、灯を。 | Everyone—the lanterns. | 1.5 | 灯（ひ）. Register `business_keigo`. |
| `ch03.b18.nyaakoto.002` | cin +16 s | ニャーコト Nyaakoto | 火を灯そう。街の明かりは民のものだ。 | Then let us light them. This ward's lanterns belong to its people. | 4.4 | Catalog anchor line 3 (speaker `samurai`), text verbatim. Register `samurai_plain`. |
| `ch03.b18.tokichi.003` | cin +34 s | 灯吉 Tōkichi | どの提灯にも、空の紋を描いといたで。 | I painted the sky crest on every one. | 3.4 | Register `artisan_gentle`. |
| `ch03.b18.oyuki.004` | cin +52 s | お雪 Oyuki | 次は田でございます。水がなければ、何一つ作れません。 | Next, the fields. Without water, nothing can be made. | 4.7 | Hands off to ch04. Register `business_keigo`. |
| `ch03.b18.kohagi.005` | cin +62 s | 小萩 Kohagi | 下村の堤、見てくる。 | I'll go look at the Lower Village dikes. | 2.7 | 下村（しもむら）, 堤（つつみ）. Register `terse`. |
| `ch03.b18.nyaakoto.006` | cin +78 s | ニャーコト Nyaakoto | ……先生。一つ、灯りました。 | …Sensei. One light is lit. | 2.7 | To the absent master, looking up the lantern line. Register `samurai_polite`. |

### 3.4 HUD tutorial prompts (UI strings, not VO; L4 owns key glyphs)

| String id | Beat | Japanese | English | Shown |
|---|---|---|---|---|
| `ui.ch03.crouch` | b02 | しゃがむと足音が小さくなる | Crouch to move quietly | First 10 s of b02 |
| `ui.ch03.puddle` | b02 | 水たまりは大きな音を立てる | Puddles make noise | On `vol_b02_puddles` |
| `ui.ch03.snuff` | b02 | {Interact}長押し：灯りを消す | Hold {Interact}: snuff the lamp | Near a snuffable lamp |
| `ui.ch03.states` | b02 | 気配：不審 → 警戒 → 捜索 | Awareness: Suspicious → Alert → Searching | First suspicion |
| `ui.ch03.takedown` | b03 | 背後から{Melee}：不意討ち | From behind, {Melee}: takedown | Behind an unaware guard |
| `ui.ch03.mineuchi` | b03 | 首輪の者には峰打ちになる | Strikes on the collared use the blade's back | Aiming at a conscript |
| `ui.ch03.sealcut` | b03 | 倒れた者のそばで{Interact}長押し：首輪を切る | Hold {Interact} beside the downed: cut the collar | Downed conscript, 8 s window |
| `ui.ch03.carry` | b05 | 運搬中：刀は片手、弓は使えない | Carrying: katana one-handed, no bow | First pickup |
| `ui.ch03.signal` | b07 | 同行者はあなたがそばにいる間だけ進む | The escort moves on only while you stay close | b07 start |
| `ui.ch03.revive` | b07 | {Interact}長押し：助け起こす | Hold {Interact}: help them up | Escort downed |
| `ui.ch03.bend` | b09 | 緑の間で離す | Release in the green | First bend |
| `ui.ch03.grenade` | b09 | 擲弾筒：弧を描いて飛ぶ。近いと自分も巻き込む | Grenade Launcher: arcing shells. Close blasts hurt you too | Unlock |
| `ui.ch03.glint` | b10 | 光が見えたら狙われている | A glint means you are targeted | First marksman lock |
| `ui.ch03.dobuita` | b10 | 溝板は端を歩けば鳴らない | Walk the drain boards' edges to stay silent | On `vol_b10_dobuita_*` |
| `ui.ch03.fuse` | b10 | 導火二十秒。離れよ | Fuse: 20 s. Get clear | On lighting the fuse |
| `ui.ch03.fire` | b14 | 消えた竈は{Interact}長押しで点け直す | Hold {Interact} to relight a cook-fire | First guttered fire |
| `ui.ch03.supply` | b14 | 補給所：持ち物を替えられる | Supply point: change your loadout | On `vol_b14_supply` |
| `ui.ch03.rope` | b17 | 綱を斬る：網を落とす | Cut the rope: drop the net | 稽古 (Easy) only, first time in the drop zone |
| `ui.ch03.vents` | b17 | 背の排気口が弱点 | The rear vents are the weak point | 稽古 (Easy) only, after 4 blocked hits |

---

## 4. Historical and cultural accuracy

These are campaign rules and review flags, not certified history. Items marked **verify** go to the historian and practitioner review (bible §20, open item 2).

### 4.1 Swords, bows and fighting

- **The 脇差 as 道中差 (weapon 4).** Early-17th-century townsmen and travellers commonly wore a single short sword, especially on the road. Later bakufu edicts progressively restricted townsmen's long swords; the 1683 order is the one usually cited. The disguise mount is plain: black-lacquered saya, iron tsuba, no mon. It is worn edge-up in the obi. **Verify** the extent of commoner wear in the 1620s.
- **峰打ち (mine-uchi).** A strike with the back (峰, 棟) of the blade to subdue. A real one could still break bones or bend the blade; the game abstracts it as a knockdown and applies it automatically against `bound_conscript` (bible §3.2). The animation should show the wrist turning the edge away (刃を返す) before the strike, so the non-lethal choice reads clearly.
- **Rear takedown.** No named koryū technique is claimed. The UI calls it 不意討ち ("surprise attack"). Against aliens it is a lethal wakizashi thrust into the gorget gap; against conscripts it is a 峰打ち to the nape.
- **Crouch-walk.** The left hand steadies the saya at the 鯉口 so it does not knock, a small period-true detail. After a takedown, a brief 残心 settle follows (the bible's 0.5 s passive).
- **Sword care.** The recovered katana is wrapped in oiled paper (油紙) and cloth, with the blade oiled with 丁子油 (clove oil), a period sword-care practice.
- **Yumi (weapon 18).** Stored unstrung in a 弓袋. Stringing a 221 cm asymmetric yumi (弦張り) is a braced action, often done with a helper or a stringing post; b05 shows a shortened 3 s solo brace. **Verify** with a kyūdō practitioner. The arrow is on the right side of the bow, and the release shows 弓返り (bible §4.2; the All Japan Kyudo Federation's [射法八節](https://www.kyudo.jp/howto/syaho.html)).
- **転 against Penalta.** Marobashi is used only as a movement principle (awase, then a flank step). No kata sequence is reproduced (bible §3.1).
- **The 擲弾筒 (weapon 7).**
  - 擲弾筒 is a 20th-century military term. It is kept only as the catalog and UI name; in fiction, characters call it 花火筒.
  - Period touchstones: the fireworks tradition (Ieyasu's 1613 viewing, bible §19), and the Sengoku-era 焙烙火矢, clay incendiary grenades used in naval warfare.
  - **Burst colour:** Japanese fireworks before the Meiji era were 和火: charcoal-and-saltpetre sparks in orange and gold. Coloured chemistry (strontium red, barium green) came much later. Shell bursts must be gold, orange and white only (iron-filing sparks give the white). That keeps them distinct from alien cyan. Because they are brief airborne sparks, they do not compete with the amber telegraphs, which are animated ground decals with a hatch pattern.
- **The charge's fuse** is a 火縄 slow-match, the same material as a matchlock's match.

### 4.2 Town and architecture

- **Visual sources for the period:**
  - The 舟木本『洛中洛外図屏風』 by Iwasa Matabei (about 1614–15, Tokyo National Museum, National Treasure): Kyoto streets, 町家, 卯建, 格子, 暖簾, clothing and crowd life within a decade of our date.
  - The 『江戸図屏風』 (National Museum of Japanese History, 1630s).
  - Use them for massing, dress and street use, not for copying specific buildings.
- **Roofs.** In the 1620s most town houses had shingle or board roofs weighted with stones. Kawara was costly and appeared mainly on storehouses, temples and wealthy merchants' houses. Here, ordinary 町家 get stone-weighted board roofs; the 両替屋 and the 土蔵 get kawara (the existing `NyaagyuKawaraBay` and ibushi study).
- **Streets.** Packed earth with 溝板-covered drains (bible §15.1). There is no paving; dressed stone appears only at the bridge, the 雁木 steps and the wharf's edge strip.
- **Tenements.** Back-lot tenements (裏店) existed in castle towns. The 九尺二間 棟割長屋 module is best documented for later Edo, and is used here as a plausible module. **Verify** the unit size for the 1620s.
- **Ward gates.** Town gates (町木戸) that were shut at night, with a gatekeeper's hut, are documented in Kyoto from the late 16th century and in early Edo.
- **高札場.** Public notice boards at crossings and bridge ends; the bakufu posted its edicts of the 1610s on 高札 (bible §19).
- **土蔵.** Thick plastered walls (漆喰), 腰板 wainscot and iron-fitted doors. Avoid presenting 海鼠壁 tiled walls as typical of 1623.
- **Wharf.** 河岸 quays with 雁木 steps are period-appropriate. Cargo was handled with 轆轤 windlasses and pulleys. The bible's "timber crane" is built as a shear-leg (二又) hoist rather than a European jib crane. **Verify**.
- **Avoid in this chapter** (in addition to bible §19):
  - 天水桶 rain barrels on every corner (later fire-prevention dressing).
  - 番傘 paper umbrellas for commoners (mid-Edo).
  - 合羽 capes on commoners (rare and costly).
  - 大八車 carts (traditionally dated after 1657).
  - 招き猫.
  - Glass.
  - 小田原提灯.
  - Ukiyo-e posters.

### 4.3 Lanterns and light

- **Lantern forms.** Folding paper lanterns spread in the late 16th and early 17th centuries. Hero forms for 1623 are the lidded 箱提灯 and simple hanging lanterns; the heirloom c04 is a 箱提灯.
- **Rib construction.** The continuous spiral-rib method is traditionally credited to 19th-century Yame makers. So the b09 minigame hooks **separate hoops** (輪骨) onto a form. **Verify** with a lantern-craft historian.
- **Oils.** 荏油 (perilla oil) is the traditional drying oil for waterproof paper (油紙, umbrellas). Lamp oil was 荏胡麻油 in the medieval period, with 菜種油 (rapeseed) spreading through the 17th century. Tōkichi's "oil shop" line fits either.
- **Candles.** Japanese wax candles (和蝋燭) were costly in the 1620s, so b18's forty lit lanterns are framed as a communal extravagance: the ward's hoarded candles, lit together. Do not dress candle stockpiles as ordinary.
- **Street lamps.** 行灯 are indoor and shop lamps. Street-corner 辻行灯 as a municipal institution are better documented later. Here they are Credit House licensed lamps, which sidesteps the question; the prop is the existing `SM_Edo_LanternPost`.
- **Crest lanterns.** Lanterns bearing a house's crest (家紋入りの提灯) are a real tradition; the SORA-mon lanterns in b18 draw on it.

### 4.4 Clothing and people

- **Rain gear.** 蓑 (straw raincoat) and 菅笠 (sedge hat). Residents wear 足駄, the high-toothed clogs for mud; their footsteps make a clack on packed earth.
- **Workwear.** 小袖 for everyone. Artisans wear 前掛け (apron), 襷 and 手拭い, with a 頬被り (cloth over the head) in rain. Kohagi wears indigo peddler's clothes with 手甲 (hand guards), 脚絆 (leggings) and 草鞋 (straw sandals), never a black "ninja suit" (bible §4.4).
- **Nyaakoto's costume.** In b01–b05 he wears the disguise: an indigo 小袖, 蓑 and 菅笠. After the well he drops the 蓑. From b14 he wears 襷 and a white 鉢巻. His armour stays in the Hidden Valley this chapter, so the SORA mon is **not** on his costume in ch03.
- **Oyuki's props.** She carries a 算盤 (soroban) and a 矢立 brush case, and her arithmetic primer is Mōri Shigeyoshi's 『割算書』 (1622), the oldest surviving Japanese printed arithmetic book (bible §19). Do **not** use 『塵劫記』 (1627), which is four years too late.
- **Toranosuke's grey 羽織.** Haori were in samurai use by the early 17th century. The alien grey cloth with a ledger-sigil back is the costume's point.

### 4.5 The oath: 一味神水, 起請文, 傘連判状

- **一味神水.** The members write an oath (起請文), burn it, stir the ash into water offered to the gods, and all drink it. It is widely documented for medieval 一揆; see 勝俣鎮夫『一揆』 (Iwanami Shinsho, 1982). 一揆を結ぶ is the period idiom Oyuki uses.
- **起請文.** Commonly written on the back of 牛玉宝印 (goō hōin) talisman sheets issued by shrines and temples; see Chijiwa Itaru's studies of 起請文 and 牛玉宝印. The b13 prop is a 牛玉宝印 sheet with the talisman printed in black and red seals.
- **傘連判状 (flagged stretch, bible §19).** Most surviving examples come from later Edo peasant uprisings. A circular signature among Sengoku warrior leagues is reportedly attested earlier, for example in the Mōri house documents of the mid-16th century. **Verify.** If confirmed, the stretch narrows to "a warrior-league form adopted by townsfolk". Oyuki's line states its purpose: no name is first.
- **Signatures.** People who could not write signed with a simplified mark (略押) or by stamping a circle with the butt of the brush (筆軸印). Both are common on Edo village documents; Kohagi uses 筆軸印. Nyaakoto signs with a 花押. His formal kanji name appears only on the dojo's 起請文 (bible §6.1), so the camera does not read his signature.

### 4.6 Money words

The aliens' vocabulary is modern financial Japanese by design (bible §6.3): 信用, 担保, 延滞, 計上, 回収, 口座. Locals use period words: 借り, 利, 勘定, 帳面, 町の蔵. When Kohagi says 担保, she is quoting the aliens (「……担保だって。」). The contrast makes the invaders sound foreign without any exposition. Oyuki's "count only what is made" seeds charter article 1 (物なくして札なし, bible §2.2); XOR itself is not named or cut until ch05. The §2 boundary holds: this is fiction, not a description of the real SORA network.

### 4.7 The SORA kamon in this chapter

| Where | Beat | Treatment |
|---|---|---|
| Children's chalk marks | b04 (c01) | 60–80 cm off the ground (child height), repeated along the alley. The decal comes from the exact SVG paths with a chalk-stroke mask; the texture is treated, the shape is never redrawn. |
| Large charcoal mark | b16 (c06) | On storehouse B's canal wall at adult height: the bible's "growing bolder". |
| The oath sheet (傘連判状) | b13 | Placed at the centre in vermillion brush texture from the SVG, with signature spokes radiating from it. |
| The relit lanterns | b18 | A vermillion mon on white washi, one per face (家紋入り提灯). |
| UI | all | Chapter title card with the vermillion 朱印 seal; objective marker; save indicator (bible §17). |
| **Never** | — | Alien objects (the terminal, seals, drones, leaflets, the scan arch, Penalta) carry only the ledger sigil, a closed ring of tally notches. Cyan never appears on League objects. |

Source: `Content/SourceArt/UI/sora_logo_NOtext2.svg` (SHA-256 `d66413a7…0910`), imported from its two original paths (see [sora-kamon-runtime-art.md](../sora-kamon-runtime-art.md)).

### 4.8 Sources

- 柳生宗矩『兵法家伝書』 (1632); 渡辺一郎 校注『兵法家伝書 付・新陰流兵法目録事』 (Iwanami Bunko, 1985). Background for 活人剣 and 転.
- 勝俣鎮夫『一揆』 (Iwanami Shinsho, 1982). 一味神水 and league oaths.
- Chijiwa Itaru, studies of 起請文 and 牛玉宝印.
- 舟木本『洛中洛外図屏風』 (Tokyo National Museum), about 1614–15; 『江戸図屏風』 (National Museum of Japanese History), 1630s.
- 毛利重能『割算書』 (1622).
- All Japan Kyudo Federation, [射法八節](https://www.kyudo.jp/howto/syaho.html); the Met's [Edo katana](https://www.metmuseum.org/art/collection/search/638804) (both cited in [historical-arms.md](../historical-arms.md)).
- Story bible §§3, 4, 19 (the respect rules and the period checklist).

---

## 5. Art and audio asset list

**Status key.**
- **Existing:** in `Content/SourceArt` or `catalog.json`, usable as a base.
- **Existing (prototype):** present, but fails or has not passed the [photoreal gates](../art-direction/photoreal-acceptance.md).
- **Needed:** to be created or sourced with a recorded licence.

Photoreal is non-negotiable (bible §15), and every asset still needs the packaged A/B, a recorded licence and measured frame cost.

### 5.1 Environment kits

| Asset | Beats | Status | Source and notes |
|---|---|---|---|
| Canal kit: 石積み banks, 雁木 steps, bridge, basin water with rain rings | b01, b02, b15–b17 | Needed | Start the dressed stone from the CC0 `PolyHaven/stone_floor`; the water shader must hold stable rain-ring reflections |
| 町家 frontage kit: 厨子二階 bays of 3–5 ken, 格子, 暖簾, 卯建, stone-weighted board roofs, 腰高障子 | b03–b18 | Needed | Materials start from CC0 `wood_planks_dirt` and `WhitePlaster02`; kawara from `NyaagyuKawaraBay` (ibushi maps) |
| Back-tenement kit: 九尺二間 units, 路地木戸, 溝板 gutter, laundry poles, lean-to | b04–b06, b13, b14 | Needed | 溝板 needs a loose-board rattle mesh and a silent edge strip |
| Wet packed-earth street material: ruts, puddles, wetness mask | all | Needed | Start from CC0 `brown_mud_leaves_01`. Stone path sets (`NyaagyuHeroPath`, `NyaagyuTerrain` paths) are wrong for streets. |
| 土蔵 storehouse (town variant) | b02, b08, b16, b17 | Existing (prototype) | `NyaagyuKura/SM_Nyaagyu_ProvisionKura` and the `NyaagyuKuraFront` candidate are source-only; they need a plaster, kawara and iron-door town variant |
| Ward gate: fence, 2-leaf gate, 潜り戸, 木戸番屋 | b03 | Needed | |
| 高札場: roofed board, stone base, 矢来 | b10–b12 | Needed | |
| Lantern workshop interior: 通り土間, plank floor, rafters | b08, b09 | Needed | |
| Wharf set: shear-leg hoist, 轆轤, pulley, bale nets, bamboo pen, mooring posts | b15, b17 | Needed | Nets and rope need breakable states |
| Cargo stacks | b02, b17 | Existing (prototype) | `NyaagyuCargoStack/SM_Nyaagyu_CargoStack` with PBR straw, wood and indigo maps; source-only, and collision is still the C++ proxy |
| Shōji and washi material | b09, b13, b18 | Existing (prototype) | `ShojiPaperArtReview` fails its gate (repeating fibres, unmeasured transmission); lantern washi needs **measured transmission** |

### 5.2 Props

| Asset | Beats | Status | Notes |
|---|---|---|---|
| `SM_Alien_StreetDebtTerminal` | b10, b11 | Existing | Already placed by the arena 1 builder at (−7.3, +4.6) m. Needed: a rear service panel, a charge socket and a destroyed state |
| `SM_Edo_LanternPost` as 辻行灯 | b02, b10 | Existing (prototype) | Needed: a snuffed state and a licence-seal decal (ledger sigil) |
| `SM_Alien_DebtKiosk` | — | Existing | Not used; the scan arch is a separate new asset |
| Scan arch, debt-seal door clamp, cyan door-numeral decal (animated tick and flicker-out), Credit House leaflets | b01–b11 | Needed | Coordinate the seal clamp with ch02's granary seals |
| 行灯 (snuffable), brazier, 篝火 | b02, b03, b13, b17 | Needed | |
| 提灯 set: ribs on a form, half-papered, finished unlit, lit, SORA-painted, collapsed; the 箱提灯 heirloom | b09, b18 | Needed | Separate-hoop construction (§4.3) |
| Lantern tools: 型 forms, bamboo strips, splitting knife, paste pots, brushes, oil jars, drying boards | b05, b09 | Needed | |
| Festival shells, shell bench, 火縄 fuse, charge | b09, b10 | Needed | |
| Wells: stone curb, 釣瓶 pulley frame, rope, the dry-well interior | b05 | Needed | |
| Carry items: tool crate, oiled-paper sword bundle, 弓袋 | b05 | Needed | |
| Kitchen: 3 clay 竈, rice pots, miso cauldron, trestle boards, bowls | b14 | Needed | |
| Oath: 牛玉宝印 sheet, 傘連判状 sheet with the mon, ash dish, water bowl, 矢立 | b13 | Needed | The mon comes from the SVG (§4.7) |
| Boats: 高瀬舟 with 棹 pole, small boats, barge | b01, b02, b15–b17 | Needed | |
| Street dressing: sake barrels (樽), straw bales, laundry, 暖簾 with 屋号 marks, 足駄 | all | Needed | Straw can reuse the cargo PBR maps |
| Collectible props c01–c06 | — | Needed | c01 and c06 are SVG-derived decals |
| Weapon 4 wakizashi (disguise mount) | all | Existing (prototype) | `SM_Weapon_04.fbx` (generic original). Needed: a plain black saya and iron-tsuba photoreal mount |
| Weapon 7 hand-mortar | b09–b17 | Existing (prototype) | `SM_Weapon_07.fbx` (generic original). Needed: a bamboo-and-iron 花火筒 look consistent with §4.1 |
| Katana and saya | b05– | Existing (prototype) | `SM_Nyaagyu_HeroKatana.fbx`, `SM_Nyaagyu_HeroSaya.fbx` with PBR (length flagged long for the period) |
| Yumi | b05– | Existing (prototype) | `Weapons/NyaagyuYumi/SM_Nyaagyu_Yumi_Study.fbx` (study). Needed: unstrung and stringing states |
| Yari | b14 | Existing (prototype) | `Weapons/NyaagyuYari/SM_Nyaagyu_Suyari_SourceStudy.fbx` |

### 5.3 Characters

| Character | Status | Notes |
|---|---|---|
| Nyaakoto | Existing (prototype) | `SK_NyaagyuSamurai` runtime skin (grey tabby); fails the face and fur gate. **Needed:** the ch03 disguise costume (indigo 小袖, 蓑, 菅笠), a 襷/鉢巻 variant, and an indigo-sleeve variant of the first-person paws (`NyaakotoFirstPersonPaws` source exists). |
| Kohagi, Tōkichi, Tamakichi, Isa, Oren, Oyuki | Needed | Looks per bible §6.1–6.2 |
| Toranosuke (grey Credit House haori) | Needed | Base model shared with ch01; the haori is a ch03–06 variant |
| Penalta (boss) | Needed | Hairless, huge; graphite armour, tower shield, seal-hammer, two rear cooling vents with glow and steam states, shield break state |
| Enforcer archetypes (rifle, grenadier, marksman, blade retainer) | Existing (prototype) | `SK_AlienBanker`/`SM_AlienBanker` and the walk animation are generic prototypes. **Needed:** archetype kits with readable silhouettes (bible §7) |
| Inventory drone (目録) | Needed | Floating disc with a cyan eye, spotlight and net launcher |
| Debt-bound conscripts (3 variants plus the kido-ban) | Needed | Local clothes, glowing collar, 六尺棒 staff |
| Residents (6 variants) and children (2) | Needed | 蓑, 足駄, head towels; the mother in b11 |

### 5.4 Animations

| Set | Status | Contents |
|---|---|---|
| Player stealth | Needed | Crouch locomotion with the hand on the 鯉口; snuffing a lamp; lethal wakizashi takedown; 峰打ち takedown with the blade flip; seal-cut; rope climb in the well; bow stringing (3 s); 釣瓶 hoist; one-handed katana carry; hide and go signals; revive |
| Player craft | Needed | Rib bend (flex gauge), paste, rim assembly, oil brushing, shell wrapping, fuse inspection; planting the charge, lighting the fuse; cutting the rope |
| Player weapon 7 | Needed | Loft fire, reload, self-damage flinch |
| NPC | Needed | Escort crouch-walk, hiding, downed and revived; serving; oath (writing, burning, drinking, 筆軸印); opening doors; passing lantern flame; Kohagi poling the boat |
| Enemies | Needed | Drone patrol, mark and net; conscript "compelled" motion (limbs resisting); enforcer alert states; marksman glint; grenadier lob; the Penalta set (advance, bash, slam, spin, seal throw, net stun, phase stagger, shield break, fall start) |
| Existing | Existing (prototype) | `A_NyaagyuSamurai_Walk.fbx`, `A_AlienBanker_Walk.fbx` (prototype walk cycles only) |

### 5.5 VFX (Niagara)

| Effect | Beats | Status |
|---|---|---|
| Rain system: streaks, ground splash, eave drips, puddle rings, canal rain rings, low fog | all | Needed |
| Lantern flame and flicker; 行灯 snuff smoke; brazier and 篝火 embers in rain | b02–b18 | Needed |
| Drone volumetric spotlight cone; scan-arch sheet; marksman glint (900 ms) | b02, b03, b07, b10, b16 | Needed |
| Cyan door numerals flickering out in a wave across the ward | b11 | Needed |
| Seal break; collar cut spark | b03, b08, b18 | Needed |
| Grenadier arc decal (enemy); player shell arc preview | b08, b09–b17 | Needed |
| 和火 shell burst (gold, orange, white only); terminal explosion with cyan shards dying in the rain | b09–b17 | Needed |
| Oil fire patch (6 s) | b08 | Needed |
| Penalta: amber ring decals (animated edge pulse and hatch), vent steam in rain, shield split, seal-trap discs, net-drop splash, canal sink glow | b17 | Needed |
| Flame-to-flame lantern relight chain | b18 | Needed |

### 5.6 SFX

All needed; L5 sources CC0 or synthesises (no audio exists in the repo yet).

| Group | Sounds |
|---|---|
| Weather | Rain on packed earth, board roofs, kawara, washi and water; eave drips; gutter flow; gusts across the basin |
| Footsteps | Wet earth, puddle splash, 溝板 rattle (edge silent), board roof, stone steps, plank floor, straw landing; residents' 足駄 clacks |
| Player | Crouch cloth; saya knock (suppressed when the 鯉口 is held); takedown thrust and 峰打ち thud; collar-cut hum dropping out; rope climb; 釣瓶 pulley creak; crate lift and drop; bow stringing |
| Stealth feedback | Soft suspicion rise, alert sting, search-timeout release |
| Credit House | Drone hum and servos, spotlight click, net launch; scan-arch hum; seal alarm chime; terminal and PA voice (DSP); enforcer armour foley; marksman glint tick; grenadier launcher thunk |
| Workshop | Bamboo splitting, hoop flex, brush and paste, paper crinkle, oil brush, shell paper wrap |
| Weapon 7 | 花火筒 thump, shell whistle, 和火 crackle burst |
| Blackout | Terminal blast with electrical die-off; a descending chime rippling across the ward as the numerals die |
| Kitchen and oath | Fire crackle, boiling pot, ladles, crowd walla in Kamigata speech; brush on paper, paper burning, water poured |
| Penalta | Heavy steps, shield impacts and deflected arrows, slam, spin whoosh, trap arm tick, vent hiss in rain, net thud and splash, shield split, final splash |
| b18 | Wicks catching, a quiet crowd, rain easing to drips |

### 5.7 Music cues (L5 state ids)

Instruments are period-safe: shakuhachi, shamisen (in use by the late 16th century), biwa, koto and taiko. The alien layer uses cold synth pads and metallic hits and never carries the League theme.

| State | Beats | Cue |
|---|---|---|
| `ch03_canal_rain` | b01 | Solo shakuhachi over rain; a low alien drone swells under the PA |
| `ch03_stealth` | b02, b03, b10 | Stems by alert state. Unaware: sparse taiko rim ticks and biwa harmonics. Suspicious: adds a low string pulse. Alert: full percussion. Search: percussion drops out, the pulse stays. |
| `ch03_ward_explore` | b04, b05 | A quiet koto figure with the rain ambience forward |
| `ch03_hideout` | b06 | Warm, restrained shamisen pizzicato |
| `ch03_escort` | b07 | Stealth stems at a slower tempo, with a heartbeat taiko |
| `ch03_combat` | b08, b16 | Taiko ensemble over an alien synth ostinato |
| `ch03_craft` | b09, b14 | Work rhythm at 75 BPM, locked to the 800 ms bend beat |
| `ch03_blackout` | b11 | Silence, then a single shakuhachi phrase as the doors open |
| `ch03_oyuki` | b12 | Koto with a soft soroban-click motif |
| `ch03_oath` | b13 | **League theme, first full statement** (shakuhachi, koto, taiko) |
| `ch03_rival` | b15 | Toranosuke's motif on biwa, unresolved |
| `boss_penalta` | b17 | P1: heavy odaiko, with metallic alien hits on his steps. P2: tempo up, adding the spin whoosh as a rhythmic element. |
| `ch03_lanterns_relit` | b18 | League theme reprise, warm, ending on the registry page |

---

## 6. Hand-offs, proposals and open items

**L1 (beats, saves, dialogue data):**
- Generic speaker ids, shared with the other chapter scripts: `enforcer`, `conscript`, `drone`, `resident`, `child` (as in ch04 and ch06–ch08), and `credit_system` (proposed in ch02) for seals, terminals and PA. The existing `artisan` becomes Isa, since the bible moves the old artisan anchor line to `lantern_maker`.
- Proposed fields (all `x_`-prefixed):
  - Beat and task fields: `x_exit`, `x_loadout`, `x_pre_step`, `x_hoist`, `x_on_detected_carryover`, `x_seal_cut`, `x_charge`, `x_fire_out_at`, `x_supply_point`.
  - Guard, light and hazard fields: `x_static_lights`, `x_hazards`, `x_scan_arc_deg`, `x_scan_period_s`, `x_patrol_offset_s`, `x_suspicion_mult`, `x_turn_every_s`.
  - Other: `x_detection`, `x_interactables`, `x_resupply`, `x_protected`, `x_hide_spots`, `x_note` (a manufacture-step label), `x_delay_s`, `x_source`, `x_stealth_defaults` (including `x_rain_hearing_mult`).
- Proposed events: `x_npc_freed:<id>`, `x_npc_revived:<id>`, `x_item_picked:<id>`, `x_signal:hide|go`, `x_alert_state:search_to_unaware`, `x_ai:withdraw`, `x_reinforce:<wave>`, `x_objective:<id>`, `x_fire_out`, `x_wave_start:<n>`, `x_boss_hint:<id>`, `x_boss_defeated`, `x_on_detected` (a wave trigger).
- Other points for L1:
  - b04 is optional; b05 requires b03.
  - The loadout is locked from b01 until the sword bundle in b05.
  - The first supply point is at b14.
  - Collectible ids `ch03.c01`–`c06` use mask bits 0–5.

**L2 (enemies and stealth):**
- The detection values per archetype are in the YAML (`sight`, `hearing_cm`, `x_stealth_defaults`).
- Conscript suspicion runs at 0.7×, and rain lowers hearing to 0.8×.
- New noise surfaces: `x_dobuita` (×1.5 with a silent edge) and `x_board_roof` (×1.5).
- The seal-cut window is 8 s, with a 1.5 s hold.
- A drone lowers itself to net and can then be cut down.
- If the player is detected in b02, the b03 guards start `suspicious`.

**L3:** the `boss_penalta` tables in §2.3 and the YAML `boss_proposals`, including awase→転 on the bash, the forced shield break at 50%, and the two crane nets.

**L4:** the prompt strings in §3.4, the awareness indicator states, the carry indicator, and an accessible amber palette for the wharf.

**L5:** the music states in §5.7. Bark sets are recorded once and reused; the 和火 burst stays distinct from alien sounds.

**C2/C3:** the layouts in §1.4, following the arena 1 rule (campaign geometry never touches arena collision).

**C9:** five sequences (b01, b11, b13, b15, b18) plus the Penalta intro and outro. Until Sequencer lands, each uses `fallback: camera_blend`.

**VO budget.** The chapter has 143 lines against the bible's 130. Of these, 26 are repeatable barks and retry lines that later chapters reuse (the drone, conscript, enforcer, marksman and grenadier sets). That leaves 117 story lines, within budget.

**Open items:**
1. Native Japanese review (B7) of every line, especially the Kamigata registers and Oyuki's keigo.
2. Historian review of the §4 items marked **verify**:
   - commoners carrying a wakizashi in the 1620s;
   - the 九尺二間 module;
   - 辻行灯;
   - the shear-leg hoist;
   - separate-hoop lanterns;
   - the earlier 傘連判状 precedent.
3. Practitioner review of the solo bow-stringing brace and the 峰打ち blade flip.
4. Playtest telemetry for the 55 min target and b07's escort pacing (the most variable beat).
5. Lantern washi transmission measured before b18's lighting is authored.

---

## 7. Machine-readable beat data (YAML)

This block is generated from the same source as the tables above and was checked by a parse round-trip. It contains:
- the chapter header;
- `beats` (bible §12 fields plus `x_` proposals);
- `collectibles`;
- `layout` (volumes, spawns, patrols and splines, in cm);
- `boss_proposals` (for `bosses.json`);
- `lines` (every dialogue line with `ja`, `en`, `speaker`, `register`, `mode` and `duration_s`);
- `ui_prompts` (the §3.4 HUD strings, added in the C1 review so that every chapter carries the same required keys; bible §12.5).

L1 converts it to `Content/Data/campaign/chapter_03.json` (schema 4).

```yaml
chapter: ch03_lantern_ward
title_ja: "占領された街"
title_en: "Occupied Streets"
map: 1
target_s: 3300
pacing_min: {C: 14, E: 3, S: 12, P: 15, M: 0, Cin: 11}
weapons_unlocked: [4, 7]
boss: boss_penalta
sites: {"0": ch03.b05, "1": ch03.b09, "2": ch03.b14}
catalog_anchor_lines: {"1": ch03.b02.kohagi.001, "2": ch03.b06.tokichi.001, "3": ch03.b18.nyaakoto.002}
x_stealth_defaults:
  noise_radius_cm: {crouch: 250, walk: 600, run: 1200, land_1_5m: 900, takedown: 150}
  surface_mult: {puddle: 2.0, running_water: 0.5, x_dobuita: 1.5, x_board_roof: 1.5}
  x_rain_hearing_mult: 0.8
  lit_definition: "inside any light_source radius, a drone spotlight, or terminal glow"
  states: [unaware, suspicious, alert, search]
  easy_on_detected: combat
schema_note: "Bible §12 beat taxonomy. Keys prefixed x_ (and x_ events) are proposals listed in §6 of chapter-03.md; L1 ratifies or drops them."
speakers_new:
  - {id: enforcer, ja: "執行兵", en: Enforcer}
  - {id: conscript, ja: "債縛衆", en: Debt-Bound}
  - {id: drone, ja: "目録", en: "Inventory drone"}
  - {id: credit_system, ja: "信用院・告知音声", en: "Credit House notice voice"}
  - {id: resident, ja: "町の衆", en: Resident}
  - {id: child, ja: "子ども", en: Child}
beats:
  - id: ch03.b01
    type: cinematic
    place: pl_horiwari
    title_ja: "高瀬舟で提灯街へ"
    title_en: "By riverboat to Lantern Ward"
    target_s: 120
    checkpoint: true
    sequence: "/Game/Cinematics/Ch03/LS_Ch03_B01_Takasebune"
    duration_s: 120
    skippable: true
    fallback: camera_blend
    end_state: {player_transform: ps_b02_start, equipped: [4]}
    unlocks: {weapons: [4]}
    music: ch03_canal_rain
    x_loadout: {equipped: [4], locked_slots: [hip, back, polearm, firearm], until: "x_item_picked:sword_bundle"}
    subtitles:
      - {line: ch03.b01.system.001, at_s: 8.0}
      - {line: ch03.b01.system.002, at_s: 16.0}
      - {line: ch03.b01.kohagi.003, at_s: 31.0}
      - {line: ch03.b01.nyaakoto.004, at_s: 36.0}
      - {line: ch03.b01.kohagi.005, at_s: 42.0}
      - {line: ch03.b01.kohagi.006, at_s: 63.0}
      - {line: ch03.b01.kohagi.007, at_s: 71.0}
      - {line: ch03.b01.nyaakoto.008, at_s: 76.0}
      - {line: ch03.b01.kohagi.009, at_s: 82.0}
  - id: ch03.b02
    type: stealth_zone
    place: pl_horiwari
    title_ja: "河岸を抜けよ"
    title_en: "Slip past the landing"
    target_s: 240
    checkpoint: true
    zone: vol_b02_landing
    guards:
      - {type: drone, id: g_b02_d1, patrol: pt_b02_d1, sight: {cone_deg: 50, range_cm: 1800, dark_range_cm: 700}, hearing_cm: 600}
      - {type: drone, id: g_b02_d2, patrol: pt_b02_d2, sight: {cone_deg: 50, range_cm: 1800, dark_range_cm: 700}, hearing_cm: 600}
    detection: {suspicion_rate: 1.0, alert_threshold: 1.0, search_s: 20}
    takedowns: {rear: false}
    light_sources: [andon_b02_w1, andon_b02_w3, andon_b02_shed]
    noise_surfaces:
      - {kind: puddle, volumes: [pud_b02_01, pud_b02_02, pud_b02_03, pud_b02_04, pud_b02_05, pud_b02_06]}
    on_detected: combat
    complete: exit_reached
    x_exit: vol_b02_exit
    x_on_detected_carryover: {beat: ch03.b03, start_state: suspicious}
    unlocks: {mechanics: [stealth]}
    music: ch03_stealth
    dialogue:
      - {"on": beat_start, lines: [ch03.b02.kohagi.001], mode: radio}
      - {"on": "volume_enter:vol_b02_drones", lines: [ch03.b02.kohagi.002], mode: radio}
      - {"on": "volume_enter:vol_b02_puddles", lines: [ch03.b02.kohagi.003], mode: radio}
      - {"on": "volume_enter:vol_b02_andon", lines: [ch03.b02.kohagi.004], mode: radio}
      - {"on": "alert_state:suspicious", lines: [ch03.b02.drone.005], mode: ambient, x_source: [drone], repeatable: true}
      - {"on": "alert_state:alert", lines: [ch03.b02.drone.006], mode: ambient, x_source: [drone], repeatable: true}
      - {"on": "alert_state:search", lines: [ch03.b02.drone.007], mode: ambient, x_source: [drone], repeatable: true}
      - {"on": "x_alert_state:search_to_unaware", lines: [ch03.b02.drone.008], mode: ambient, x_source: [drone], repeatable: true}
      - {"on": beat_complete, lines: [ch03.b02.kohagi.009], mode: radio}
      - {"on": player_died, lines: [ch03.b02.kohagi.010], mode: radio, repeatable: true}
    fail: {"on": player_died, to: checkpoint}
  - id: ch03.b03
    type: stealth_zone
    place: pl_kido
    title_ja: "木戸を越えよ"
    title_en: "Get through the ward gate"
    target_s: 240
    checkpoint: true
    zone: vol_b03_kido
    guards:
      - type: bound_conscript
        id: kidoban
        patrol: "static:sp_b03_wicket"
        x_turn_every_s: 12
        sight: {cone_deg: 90, range_cm: 1500, dark_range_cm: 600}
        hearing_cm: 700
        x_suspicion_mult: 0.7
      - type: bound_conscript
        id: g_b03_c2
        patrol: pt_b03_c2
        sight: {cone_deg: 90, range_cm: 1500, dark_range_cm: 600}
        hearing_cm: 700
        x_suspicion_mult: 0.7
      - type: bound_conscript
        id: g_b03_c3
        patrol: "static:sp_b03_brazier"
        sight: {cone_deg: 90, range_cm: 1500, dark_range_cm: 600}
        hearing_cm: 700
        x_suspicion_mult: 0.7
      - type: enforcer_rifle
        id: g_b03_e1
        patrol: "static:sp_b03_arch"
        sight: {cone_deg: 70, range_cm: 2200, dark_range_cm: 800}
        hearing_cm: 900
      - {type: enforcer_rifle, id: g_b03_e2, patrol: pt_b03_e2, sight: {cone_deg: 70, range_cm: 2200, dark_range_cm: 800}, hearing_cm: 900}
    detection: {suspicion_rate: 1.0, alert_threshold: 1.0, search_s: 20}
    takedowns: {rear: true, lethal_default: true}
    nonlethal_types: [bound_conscript]
    x_seal_cut: {downed_s: 8, hold_s: 1.5, freed_behavior: hide_in_place}
    light_sources: [andon_b03_bansho]
    x_static_lights: [brazier_b03, scan_arch_b03]
    noise_surfaces:
      - {kind: puddle, volumes: [pud_b03_01, pud_b03_02, pud_b03_03]}
      - {kind: running_water, volumes: [vol_b03_culvert]}
    x_hazards: [{id: scan_arch_b03, on_enter: alert}]
    on_detected: combat
    complete: exit_reached
    x_exit: vol_b03_exit
    x_ladders:
      - {id: ladder_b03_shop, roof: vol_b03_shop_roof, height_cm: 320, drop_noise_cm: 900, straw: vol_b03_straw}
    unlocks: {mechanics: [takedown, seal_cut]}
    music: ch03_stealth
    dialogue:
      - {"on": beat_start, lines: [ch03.b03.kohagi.001], mode: radio}
      - {"on": "volume_enter:vol_b03_first_conscript", lines: [ch03.b03.kohagi.002], mode: radio}
      - {"on": "volume_enter:vol_b03_bansho_rear", lines: [ch03.b03.kohagi.003], mode: radio}
      - {"on": "alert_state:suspicious", lines: [ch03.b03.conscript.004], mode: ambient, x_source: [bound_conscript], repeatable: true}
      - {"on": "alert_state:alert", lines: [ch03.b03.conscript.005], mode: ambient, x_source: [bound_conscript], repeatable: true}
      - "on": "x_alert_state:search_to_unaware"
        lines: [ch03.b03.conscript.006]
        mode: ambient
        x_source: [bound_conscript]
        repeatable: true
      - "on": "alert_state:suspicious"
        lines: [ch03.b03.enforcer.007]
        mode: ambient
        x_source: [enforcer_rifle, blade_retainer, shield_enforcer]
        repeatable: true
      - "on": "alert_state:alert"
        lines: [ch03.b03.enforcer.008]
        mode: ambient
        x_source: [enforcer_rifle, blade_retainer, shield_enforcer]
        repeatable: true
      - "on": "alert_state:search"
        lines: [ch03.b03.enforcer.009]
        mode: ambient
        x_source: [enforcer_rifle, blade_retainer, shield_enforcer]
        repeatable: true
      - {"on": "x_npc_freed:kidoban", lines: [ch03.b03.kidoban.010, ch03.b03.kidoban.011], mode: ambient}
      - {"on": player_died, lines: [ch03.b02.kohagi.010], mode: radio, repeatable: true}
    fail: {"on": player_died, to: checkpoint}
  - id: ch03.b04
    type: explore_optional
    place: pl_ura_nagaya
    title_ja: "裏長屋を歩け"
    title_en: "Walk the back tenements"
    target_s: 180
    checkpoint: true
    optional: true
    requires: [ch03.b03]
    volume: vol_b04_nagaya
    pois:
      - {id: poi_idobata, kind: npc}
      - {id: poi_chalk, kind: npc}
      - {id: poi_leaflet, kind: lore}
      - {id: poi_balance_door, kind: lore}
      - {id: poi_dead_end, kind: vista}
    rewards: [ch03.c01, ch03.c02]
    exit_hint_after_s: 150
    music: ch03_ward_explore
    dialogue:
      - {"on": "volume_enter:poi_idobata", lines: [ch03.b04.resident.001, ch03.b04.resident.002, ch03.b04.resident.003], mode: ambient}
      - {"on": "volume_enter:poi_chalk", lines: [ch03.b04.child.004, ch03.b04.child.005], mode: ambient}
      - {"on": "volume_enter:poi_leaflet", lines: [ch03.b04.resident.006], mode: ambient}
      - {"on": "volume_enter:poi_balance_door", lines: [ch03.b04.nyaakoto.007], mode: ambient}
  - id: ch03.b05
    type: production_task
    task: carry
    place: pl_ura_nagaya
    title_ja: "空井戸の道具を運べ"
    title_en: "Carry the hidden tools"
    target_s: 240
    checkpoint: true
    requires: [ch03.b03]
    site: 0
    carry:
      item: tool_crate
      count: 3
      pickups: [pk_b05_tsurube]
      dropoffs: [dp_b05_hideout]
      loadout_while_carrying: [katana_one_hand]
      move_speed_mult: 0.8
      drop_on_hit: true
    stealth: true
    waves:
      - enemies:
          - {type: enforcer_rifle, count: 1, spawn: sp_b05_street_w, patrol: pt_b05_omote}
          - {type: bound_conscript, count: 1, spawn: sp_b05_street_w, patrol: pt_b05_omote}
        trigger: start
    nonlethal_types: [bound_conscript]
    x_pre_step:
      interact: act_b05_dry_well_rope
      descend_cm: 700
      pickup: sword_bundle
      restores: {equipped: [0, 4, 18], quiver: 12}
      string_bow_s: 3.0
    x_hoist: {interact: act_b05_tsurube, hold_s: 3, per_item: true}
    unlocks: {}
    music: ch03_ward_explore
    dialogue:
      - {"on": beat_start, lines: [ch03.b05.kohagi.001], mode: radio}
      - {"on": "x_item_picked:sword_bundle", lines: [ch03.b05.nyaakoto.002], mode: ambient}
      - {"on": "x_item_picked:sword_bundle", lines: [ch03.b05.kohagi.003], mode: radio, x_delay_s: 4.0}
      - {"on": "volume_enter:vol_b05_alley_mouth", lines: [ch03.b05.conscript.004], mode: ambient}
      - {"on": "progress_at:0.33", lines: [ch03.b05.tokichi.005], mode: ambient}
      - {"on": beat_complete, lines: [ch03.b05.tokichi.006], mode: ambient}
      - {"on": "alert_state:suspicious", lines: [ch03.b03.conscript.004], mode: ambient, x_source: [bound_conscript], repeatable: true}
      - {"on": "alert_state:alert", lines: [ch03.b03.conscript.005], mode: ambient, x_source: [bound_conscript], repeatable: true}
      - "on": "x_alert_state:search_to_unaware"
        lines: [ch03.b03.conscript.006]
        mode: ambient
        x_source: [bound_conscript]
        repeatable: true
      - "on": "alert_state:suspicious"
        lines: [ch03.b03.enforcer.007]
        mode: ambient
        x_source: [enforcer_rifle, blade_retainer, shield_enforcer]
        repeatable: true
      - "on": "alert_state:alert"
        lines: [ch03.b03.enforcer.008]
        mode: ambient
        x_source: [enforcer_rifle, blade_retainer, shield_enforcer]
        repeatable: true
      - "on": "alert_state:search"
        lines: [ch03.b03.enforcer.009]
        mode: ambient
        x_source: [enforcer_rifle, blade_retainer, shield_enforcer]
        repeatable: true
      - {"on": player_died, lines: [ch03.b02.kohagi.010], mode: radio, repeatable: true}
    fail: {"on": player_died, to: checkpoint}
  - id: ch03.b06
    type: dialogue
    place: pl_ura_nagaya
    title_ja: "灯吉と玉吉"
    title_en: "Tōkichi and Tamakichi"
    target_s: 60
    checkpoint: false
    requires: [ch03.b05]
    trigger: beat_start
    mode: ambient
    camera: soft_lookat
    music: ch03_hideout
    lines:
      - ch03.b06.tokichi.001
      - ch03.b06.tokichi.002
      - ch03.b06.tamakichi.003
      - ch03.b06.tokichi.004
      - ch03.b06.tamakichi.005
      - ch03.b06.tamakichi.006
      - ch03.b06.nyaakoto.007
      - ch03.b06.kohagi.008
  - id: ch03.b07
    type: production_task
    task: escort
    place: pl_lantern_ward_rain
    title_ja: "職人たちを工房へ"
    title_en: "Escort the craftspeople to the workshop"
    target_s: 300
    checkpoint: true
    escort:
      npcs: [tokichi, tamakichi, isa, oren]
      path: spl_b07_escort
      speed_cm_s: 160
      wait_for_player_cm: 800
      fail_on_npc_death: true
      hide_on_signal: true
      npc_health: 100
      down_revive_s: 8
      x_hide_spots: [hs_b07_01, hs_b07_02, hs_b07_03, hs_b07_04, hs_b07_05, hs_b07_06, hs_b07_07, hs_b07_08, hs_b07_09, hs_b07_10]
    waves:
      - enemies:
          - {type: bound_conscript, count: 2, spawn: sp_b07_tsuji, patrol: pt_b07_p1}
          - {type: drone, count: 1, spawn: sp_b07_air, patrol: pt_b07_d3}
        trigger: start
      - enemies: [{type: enforcer_rifle, count: 2, spawn: sp_b07_lane, patrol: pt_b07_p2}]
        trigger: start
      - enemies:
          - {type: enforcer_rifle, count: 1, spawn: sp_b07_kura, patrol: pt_b07_p3}
          - {type: blade_retainer, count: 1, spawn: sp_b07_kura, patrol: pt_b07_p3}
        trigger: start
    x_detection: {uses: chapter_stealth_defaults, on_detected: "patrol_engages; escorts auto-hide"}
    nonlethal_types: [bound_conscript]
    music: ch03_escort
    dialogue:
      - {"on": beat_start, lines: [ch03.b07.kohagi.001], mode: radio}
      - {"on": beat_start, lines: [ch03.b07.isa.002], mode: ambient, x_delay_s: 6.0}
      - {"on": "x_signal:hide", lines: [ch03.b07.nyaakoto.003], mode: ambient, repeatable: true}
      - {"on": "x_signal:go", lines: [ch03.b07.nyaakoto.004], mode: ambient, repeatable: true}
      - {"on": "volume_enter:vol_b07_patrol1", lines: [ch03.b07.tamakichi.005], mode: ambient}
      - {"on": "volume_enter:vol_b07_oilshop", lines: [ch03.b07.tokichi.006], mode: ambient}
      - {"on": "npc_downed:isa", lines: [ch03.b07.isa.007], mode: ambient, repeatable: true}
      - {"on": "x_npc_revived:any", lines: [ch03.b07.nyaakoto.008], mode: ambient, repeatable: true}
      - {"on": "volume_enter:vol_b07_patrol3", lines: [ch03.b07.kohagi.009], mode: radio}
      - {"on": beat_complete, lines: [ch03.b07.tokichi.010], mode: ambient}
      - {"on": "alert_state:suspicious", lines: [ch03.b03.conscript.004], mode: ambient, x_source: [bound_conscript], repeatable: true}
      - {"on": "alert_state:alert", lines: [ch03.b03.conscript.005], mode: ambient, x_source: [bound_conscript], repeatable: true}
      - "on": "x_alert_state:search_to_unaware"
        lines: [ch03.b03.conscript.006]
        mode: ambient
        x_source: [bound_conscript]
        repeatable: true
      - "on": "alert_state:suspicious"
        lines: [ch03.b03.enforcer.007]
        mode: ambient
        x_source: [enforcer_rifle, blade_retainer, shield_enforcer]
        repeatable: true
      - "on": "alert_state:alert"
        lines: [ch03.b03.enforcer.008]
        mode: ambient
        x_source: [enforcer_rifle, blade_retainer, shield_enforcer]
        repeatable: true
      - "on": "alert_state:search"
        lines: [ch03.b03.enforcer.009]
        mode: ambient
        x_source: [enforcer_rifle, blade_retainer, shield_enforcer]
        repeatable: true
      - {"on": "alert_state:suspicious", lines: [ch03.b02.drone.005], mode: ambient, x_source: [drone], repeatable: true}
      - {"on": "alert_state:alert", lines: [ch03.b02.drone.006], mode: ambient, x_source: [drone], repeatable: true}
      - {"on": "alert_state:search", lines: [ch03.b02.drone.007], mode: ambient, x_source: [drone], repeatable: true}
      - {"on": "x_alert_state:search_to_unaware", lines: [ch03.b02.drone.008], mode: ambient, x_source: [drone], repeatable: true}
      - "on": "x_ai:withdraw"
        lines: [ch03.b08.enforcer.006]
        mode: ambient
        x_source: [enforcer_rifle, blade_retainer, shield_enforcer]
        repeatable: true
      - {"on": player_died, lines: [ch03.b02.kohagi.010], mode: radio, repeatable: true}
    fail: [{"on": player_died, to: checkpoint}, {"on": "npc_died:any_escort", to: checkpoint}]
  - id: ch03.b08
    type: combat_wave
    place: pl_chochin_kobo
    title_ja: "工房の庭を守れ"
    title_en: "Hold the workshop yard"
    target_s: 240
    checkpoint: true
    bounds: vol_b08_kobo_yard
    waves:
      - enemies: [{type: enforcer_rifle, count: 3, spawn: sp_b08_street}]
        trigger: start
      - enemies: [{type: blade_retainer, count: 2, spawn: sp_b08_eastfence}, {type: enforcer_rifle, count: 2, spawn: sp_b08_canal}]
        trigger: "alive_below:2"
      - enemies: [{type: grenadier, count: 1, spawn: sp_b08_kura_roof}]
        trigger: "alive_below:2"
    complete: all_waves_cleared
    max_alive: 6
    nonlethal_types: [bound_conscript]
    x_hazards: [{id: oil_jars_b08, kind: fire_patch, ignite_on: explosion, duration_s: 6, dps: 12}]
    music: ch03_combat
    dialogue:
      - {"on": beat_start, lines: [ch03.b08.system.001, ch03.b08.nyaakoto.002, ch03.b08.tokichi.003], mode: ambient}
      - {"on": "x_wave_start:1", lines: [ch03.b08.enforcer.004], mode: ambient}
      - {"on": "pattern:grenadier_fire", lines: [ch03.b08.grenadier.005], mode: ambient, x_source: [grenadier], repeatable: true}
      - "on": "x_ai:withdraw"
        lines: [ch03.b08.enforcer.006]
        mode: ambient
        x_source: [enforcer_rifle, blade_retainer, shield_enforcer]
        repeatable: true
      - {"on": beat_complete, lines: [ch03.b08.tamakichi.007], mode: ambient}
      - {"on": player_died, lines: [ch03.b08.kohagi.008], mode: radio, repeatable: true}
      - "on": "alert_state:alert"
        lines: [ch03.b03.enforcer.008]
        mode: ambient
        x_source: [enforcer_rifle, blade_retainer, shield_enforcer]
        repeatable: true
      - "on": "alert_state:search"
        lines: [ch03.b03.enforcer.009]
        mode: ambient
        x_source: [enforcer_rifle, blade_retainer, shield_enforcer]
        repeatable: true
    fail: {"on": player_died, to: checkpoint}
  - id: ch03.b09
    type: production_task
    task: manufacture
    place: pl_chochin_kobo
    title_ja: "提灯を張れ"
    title_en: "Make the lanterns"
    target_s: 180
    checkpoint: true
    site: 1
    manufacture:
      recipe: chochin_and_hanabizutsu
      stations: [st_b09_rib_form, st_b09_paste_bench, st_b09_oil_rack, st_b09_shell_bench]
      steps:
        - {kind: bend, count: 6, timing: {beat_ms: 800, tolerance_ms: 160}, station: st_b09_rib_form}
        - {kind: paste, count: 4, station: st_b09_paste_bench}
        - {kind: assemble, count: 1, station: st_b09_paste_bench, x_note: "fit top and bottom rims (口輪)"}
        - {kind: paste, count: 1, station: st_b09_oil_rack, x_note: "brush perilla oil (荏油)"}
        - {kind: assemble, count: 3, station: st_b09_shell_bench, x_note: "wrap and seat festival shells"}
        - {kind: inspect, count: 1, station: st_b09_shell_bench, x_note: "check the fuse"}
      output: {item: chochin, qty: 40}
    registry: {item_ja: "提灯", item_en: "Paper lanterns", qty: 40, unit_ja: "張", unit_en: lanterns}
    unlocks: {weapons: [7]}
    music: ch03_craft
    dialogue:
      - {"on": beat_start, lines: [ch03.b09.tokichi.001], mode: ambient}
      - {"on": "progress_at:0.3", lines: [ch03.b09.tokichi.002], mode: ambient}
      - {"on": "progress_at:0.5", lines: [ch03.b09.tokichi.003], mode: ambient}
      - {"on": "progress_at:0.65", lines: [ch03.b09.tokichi.004], mode: ambient}
      - {"on": "progress_at:0.72", lines: [ch03.b09.nyaakoto.005], mode: ambient}
      - {"on": "progress_at:0.78", lines: [ch03.b09.isa.006], mode: ambient}
      - {"on": "progress_at:0.8", lines: [ch03.b09.tamakichi.007], mode: ambient}
      - {"on": beat_complete, lines: [ch03.b09.tamakichi.008, ch03.b09.tamakichi.009], mode: ambient}
    fail: {"on": none, to: none}
  - id: ch03.b10
    type: stealth_zone
    place: pl_kosatsuba
    title_ja: "端末に火薬を仕掛けよ"
    title_en: "Plant a charge on the debt terminal"
    target_s: 240
    checkpoint: true
    zone: vol_b10_kosatsuba
    guards:
      - type: marksman
        id: g_b10_m1
        patrol: "static:sp_b10_roof"
        x_scan_arc_deg: 120
        x_scan_period_s: 14
        sight: {cone_deg: 40, range_cm: 4000, dark_range_cm: 1500}
        hearing_cm: 400
      - {type: drone, id: g_b10_d1, patrol: pt_b10_d, sight: {cone_deg: 50, range_cm: 1800, dark_range_cm: 700}, hearing_cm: 600}
      - {type: enforcer_rifle, id: g_b10_p1a, patrol: pt_b10_p1, sight: {cone_deg: 70, range_cm: 2200, dark_range_cm: 800}, hearing_cm: 900}
      - type: enforcer_rifle
        id: g_b10_p1b
        patrol: pt_b10_p1
        x_patrol_offset_s: 4
        sight: {cone_deg: 70, range_cm: 2200, dark_range_cm: 800}
        hearing_cm: 900
      - type: bound_conscript
        id: g_b10_p2a
        patrol: pt_b10_p2
        sight: {cone_deg: 90, range_cm: 1500, dark_range_cm: 600}
        hearing_cm: 700
        x_suspicion_mult: 0.7
      - type: bound_conscript
        id: g_b10_p2b
        patrol: pt_b10_p2
        x_patrol_offset_s: 3
        sight: {cone_deg: 90, range_cm: 1500, dark_range_cm: 600}
        hearing_cm: 700
        x_suspicion_mult: 0.7
      - {type: blade_retainer, id: g_b10_p3, patrol: pt_b10_p3, sight: {cone_deg: 80, range_cm: 1600, dark_range_cm: 600}, hearing_cm: 900}
    detection: {suspicion_rate: 1.0, alert_threshold: 1.0, search_s: 20}
    takedowns: {rear: true, lethal_default: true}
    nonlethal_types: [bound_conscript]
    light_sources: [tsuji_andon_sw, tsuji_andon_se]
    x_static_lights: [terminal_glow_b10]
    noise_surfaces:
      - {kind: puddle, volumes: [pud_b10_01, pud_b10_02, pud_b10_03, pud_b10_04]}
      - {kind: x_dobuita, mult: 1.5, volumes: [vol_b10_dobuita_n, vol_b10_dobuita_s], silent_edge: true}
      - {kind: x_board_roof, mult: 1.5, volumes: [vol_b10_roofs]}
    x_ladders:
      - {id: ladder_b10_pawnshop, roof: vol_b10_roofs, height_cm: 320, drop_noise_cm: 900, guards: [g_b10_m1]}
    on_detected: "reinforce:w_b10_reinforce"
    waves:
      - id: w_b10_reinforce
        enemies: [{type: enforcer_rifle, count: 3, spawn: sp_b10_east}, {type: grenadier, count: 1, spawn: sp_b10_east}]
        trigger: x_on_detected
    complete:
      objectives:
        - {id: obj_plant_charge, interact: act_b10_terminal_rear_panel, hold_s: 4}
        - {id: obj_light_fuse, interact: act_b10_fuse, hold_s: 1}
        - {id: obj_reach_safe, volume: vol_b10_blast_safe, within_s: 20}
    x_charge: {fuse_s: 20, blast_radius_cm: 800, damages_player: true}
    music: ch03_stealth
    dialogue:
      - {"on": beat_start, lines: [ch03.b10.kohagi.001], mode: radio}
      - {"on": "volume_enter:vol_b10_glint", lines: [ch03.b10.kohagi.002], mode: radio}
      - {"on": "volume_enter:vol_b10_dobuita", lines: [ch03.b10.kohagi.003], mode: radio}
      - {"on": "idle_s:20", lines: [ch03.b10.system.004], mode: ambient}
      - {"on": "alert_state:suspicious", lines: [ch03.b10.marksman.005], mode: ambient, x_source: [marksman], repeatable: true}
      - {"on": "alert_state:alert", lines: [ch03.b10.marksman.006], mode: ambient, x_source: [marksman], repeatable: true}
      - {"on": "x_reinforce:w_b10_reinforce", lines: [ch03.b10.enforcer.007], mode: ambient}
      - {"on": "x_objective:obj_light_fuse", lines: [ch03.b10.nyaakoto.008], mode: ambient}
      - {"on": "alert_state:suspicious", lines: [ch03.b03.conscript.004], mode: ambient, x_source: [bound_conscript], repeatable: true}
      - {"on": "alert_state:alert", lines: [ch03.b03.conscript.005], mode: ambient, x_source: [bound_conscript], repeatable: true}
      - "on": "x_alert_state:search_to_unaware"
        lines: [ch03.b03.conscript.006]
        mode: ambient
        x_source: [bound_conscript]
        repeatable: true
      - "on": "alert_state:suspicious"
        lines: [ch03.b03.enforcer.007]
        mode: ambient
        x_source: [enforcer_rifle, blade_retainer, shield_enforcer]
        repeatable: true
      - "on": "alert_state:alert"
        lines: [ch03.b03.enforcer.008]
        mode: ambient
        x_source: [enforcer_rifle, blade_retainer, shield_enforcer]
        repeatable: true
      - "on": "alert_state:search"
        lines: [ch03.b03.enforcer.009]
        mode: ambient
        x_source: [enforcer_rifle, blade_retainer, shield_enforcer]
        repeatable: true
      - {"on": "alert_state:suspicious", lines: [ch03.b02.drone.005], mode: ambient, x_source: [drone], repeatable: true}
      - {"on": "alert_state:alert", lines: [ch03.b02.drone.006], mode: ambient, x_source: [drone], repeatable: true}
      - {"on": "alert_state:search", lines: [ch03.b02.drone.007], mode: ambient, x_source: [drone], repeatable: true}
      - {"on": "x_alert_state:search_to_unaware", lines: [ch03.b02.drone.008], mode: ambient, x_source: [drone], repeatable: true}
      - "on": "x_ai:withdraw"
        lines: [ch03.b08.enforcer.006]
        mode: ambient
        x_source: [enforcer_rifle, blade_retainer, shield_enforcer]
        repeatable: true
      - {"on": "pattern:grenadier_fire", lines: [ch03.b08.grenadier.005], mode: ambient, x_source: [grenadier], repeatable: true}
      - {"on": player_died, lines: [ch03.b02.kohagi.010], mode: radio, repeatable: true}
    fail: {"on": player_died, to: checkpoint}
  - id: ch03.b11
    type: cinematic
    place: pl_kosatsuba
    title_ja: "数字が消える"
    title_en: "The numbers go dark"
    target_s: 90
    checkpoint: true
    sequence: "/Game/Cinematics/Ch03/LS_Ch03_B11_TerminalBlackout"
    duration_s: 90
    skippable: true
    fallback: camera_blend
    end_state: {player_transform: ps_b12_square, equipped: [0, 4, 18, 7]}
    music: ch03_blackout
    subtitles:
      - {line: ch03.b11.resident.001, at_s: 24.0}
      - {line: ch03.b11.child.002, at_s: 31.0}
      - {line: ch03.b11.resident.003, at_s: 36.0}
      - {line: ch03.b11.nyaakoto.004, at_s: 70.0}
  - id: ch03.b12
    type: dialogue
    place: pl_kosatsuba
    title_ja: "白澄お雪"
    title_en: "Shirasumi Oyuki"
    target_s: 90
    checkpoint: false
    trigger: beat_start
    mode: ambient
    camera: soft_lookat
    music: ch03_oyuki
    lines:
      - ch03.b12.oyuki.001
      - ch03.b12.nyaakoto.002
      - ch03.b12.oyuki.003
      - ch03.b12.oyuki.004
      - ch03.b12.oyuki.005
      - ch03.b12.nyaakoto.006
      - ch03.b12.oyuki.007
      - ch03.b12.oyuki.008
  - id: ch03.b13
    type: cinematic
    place: pl_ura_nagaya
    title_ja: "一味神水"
    title_en: "The shared sacred water"
    target_s: 120
    checkpoint: false
    sequence: "/Game/Cinematics/Ch03/LS_Ch03_B13_IchimiShinsui"
    duration_s: 120
    skippable: true
    fallback: camera_blend
    end_state: {player_transform: ps_b14_kitchen, equipped: [0, 4, 18, 7]}
    music: ch03_oath
    subtitles:
      - {line: ch03.b13.oyuki.001, at_s: 6.0}
      - {line: ch03.b13.oyuki.002, at_s: 18.0}
      - {line: ch03.b13.tokichi.003, at_s: 29.0}
      - {line: ch03.b13.nyaakoto.004, at_s: 35.0}
      - {line: ch03.b13.oyuki.005, at_s: 43.0}
      - {line: ch03.b13.kohagi.006, at_s: 62.0}
      - {line: ch03.b13.oyuki.007, at_s: 67.0}
      - {line: ch03.b13.nyaakoto.008, at_s: 98.0}
  - id: ch03.b14
    type: production_task
    task: hold
    place: pl_ura_nagaya
    title_ja: "炊き出しを守れ"
    title_en: "Keep the communal kitchen going"
    target_s: 180
    checkpoint: true
    site: 2
    hold:
      volume: vol_b14_kitchen
      hold_s: 120
      contest: pause
      interact_points: [kamado_b14_1, kamado_b14_2, kamado_b14_3]
      per_point_s: 2
    x_fire_out_at: [0.25, 0.55, 0.8]
    waves:
      - enemies: [{type: enforcer_rifle, count: 2, spawn: sp_b14_alley_mouth}, {type: bound_conscript, count: 2, spawn: sp_b14_alley_mouth}]
        trigger: "progress_at:0.3"
      - enemies: [{type: drone, count: 2, spawn: sp_b14_backfence_air}]
        trigger: "progress_at:0.6"
      - enemies: [{type: blade_retainer, count: 1, spawn: sp_b14_alley_mouth}, {type: enforcer_rifle, count: 1, spawn: sp_b14_alley_mouth}]
        trigger: "progress_at:0.8"
    nonlethal_types: [bound_conscript]
    x_supply_point:
      id: vol_b14_supply
      slots: {side: [4], polearm: [19], firearm: [7]}
      refill: [arrows, shells]
    registry: {item_ja: "炊き出し", item_en: "Communal meals", qty: 120, unit_ja: "食", unit_en: meals}
    music: ch03_craft
    dialogue:
      - {"on": beat_start, lines: [ch03.b14.oyuki.001, ch03.b14.oyuki.002], mode: ambient}
      - {"on": "progress_at:0.15", lines: [ch03.b14.resident.003], mode: ambient}
      - {"on": "progress_at:0.28", lines: [ch03.b14.kohagi.004], mode: radio}
      - {"on": "x_wave_start:1", lines: [ch03.b14.enforcer.005], mode: ambient}
      - {"on": x_fire_out, lines: [ch03.b14.oyuki.006], mode: ambient, repeatable: true}
      - {"on": "volume_enter:vol_b14_supply", lines: [ch03.b14.tamakichi.007], mode: ambient}
      - {"on": beat_complete, lines: [ch03.b14.oyuki.008], mode: ambient}
      - {"on": "alert_state:suspicious", lines: [ch03.b03.conscript.004], mode: ambient, x_source: [bound_conscript], repeatable: true}
      - {"on": "alert_state:alert", lines: [ch03.b03.conscript.005], mode: ambient, x_source: [bound_conscript], repeatable: true}
      - "on": "x_alert_state:search_to_unaware"
        lines: [ch03.b03.conscript.006]
        mode: ambient
        x_source: [bound_conscript]
        repeatable: true
      - "on": "alert_state:alert"
        lines: [ch03.b03.enforcer.008]
        mode: ambient
        x_source: [enforcer_rifle, blade_retainer, shield_enforcer]
        repeatable: true
      - "on": "alert_state:search"
        lines: [ch03.b03.enforcer.009]
        mode: ambient
        x_source: [enforcer_rifle, blade_retainer, shield_enforcer]
        repeatable: true
      - {"on": "alert_state:alert", lines: [ch03.b02.drone.006], mode: ambient, x_source: [drone], repeatable: true}
      - "on": "x_ai:withdraw"
        lines: [ch03.b08.enforcer.006]
        mode: ambient
        x_source: [enforcer_rifle, blade_retainer, shield_enforcer]
        repeatable: true
      - {"on": player_died, lines: [ch03.b08.kohagi.008], mode: radio, repeatable: true}
    fail: {"on": player_died, to: checkpoint}
  - id: ch03.b15
    type: cinematic
    place: pl_chochin_gashi
    title_ja: "灰色の羽織"
    title_en: "The grey haori"
    target_s: 90
    checkpoint: false
    sequence: "/Game/Cinematics/Ch03/LS_Ch03_B15_WharfRival"
    duration_s: 90
    skippable: true
    fallback: camera_blend
    end_state: {player_transform: ps_b16_bridge, equipped: [0, 4, 18, 7]}
    music: ch03_rival
    subtitles:
      - {line: ch03.b15.kohagi.001, at_s: 4.0}
      - {line: ch03.b15.penalta.002, at_s: 17.0}
      - {line: ch03.b15.nyaakoto.003, at_s: 31.0}
      - {line: ch03.b15.toranosuke.004, at_s: 35.0}
      - {line: ch03.b15.toranosuke.005, at_s: 40.0}
      - {line: ch03.b15.nyaakoto.006, at_s: 49.0}
      - {line: ch03.b15.toranosuke.007, at_s: 54.0}
      - {line: ch03.b15.penalta.008, at_s: 63.0}
  - id: ch03.b16
    type: combat_wave
    place: pl_lantern_ward_rain
    title_ja: "河岸へ急げ"
    title_en: "Fight through to the wharf"
    target_s: 240
    checkpoint: true
    bounds: vol_b16_canal_lane
    waves:
      - enemies: [{type: enforcer_rifle, count: 3, spawn: sp_b16_lane_mid}, {type: marksman, count: 1, spawn: sp_b16_kura_a_roof}]
        trigger: start
      - enemies: [{type: enforcer_rifle, count: 3, spawn: sp_b16_wharf_lane}, {type: marksman, count: 1, spawn: sp_b16_kura_b_roof}]
        trigger: "volume_enter:vol_b16_mid"
    complete: all_waves_cleared
    max_alive: 6
    nonlethal_types: [bound_conscript]
    music: ch03_combat
    dialogue:
      - {"on": beat_start, lines: [ch03.b16.kohagi.001], mode: radio}
      - {"on": "x_wave_start:1", lines: [ch03.b16.enforcer.002], mode: ambient}
      - {"on": "volume_enter:vol_b16_mid", lines: [ch03.b16.nyaakoto.003], mode: ambient}
      - {"on": "x_wave_start:2", lines: [ch03.b16.kohagi.004], mode: radio}
      - {"on": "alert_state:suspicious", lines: [ch03.b10.marksman.005], mode: ambient, x_source: [marksman], repeatable: true}
      - {"on": "alert_state:alert", lines: [ch03.b10.marksman.006], mode: ambient, x_source: [marksman], repeatable: true}
      - "on": "alert_state:alert"
        lines: [ch03.b03.enforcer.008]
        mode: ambient
        x_source: [enforcer_rifle, blade_retainer, shield_enforcer]
        repeatable: true
      - "on": "alert_state:search"
        lines: [ch03.b03.enforcer.009]
        mode: ambient
        x_source: [enforcer_rifle, blade_retainer, shield_enforcer]
        repeatable: true
      - "on": "x_ai:withdraw"
        lines: [ch03.b08.enforcer.006]
        mode: ambient
        x_source: [enforcer_rifle, blade_retainer, shield_enforcer]
        repeatable: true
      - {"on": player_died, lines: [ch03.b08.kohagi.008], mode: radio, repeatable: true}
    fail: {"on": player_died, to: checkpoint}
  - id: ch03.b17
    type: boss
    place: pl_chochin_gashi
    title_ja: "取立頭ペナルタを倒せ"
    title_en: "Defeat Enforcer-Chief Penalta"
    target_s: 360
    checkpoint: true
    boss: boss_penalta
    arena: {volume: vol_b17_wharf, lock: true}
    phases: [{hp_pct_start: 100, pattern_table: penalta_p1}, {hp_pct_start: 50, pattern_table: penalta_p2, arena_mod: shield_broken}]
    defeat: kill
    checkpoint_per_phase: true
    intro_cinematic: cin_ch03_penalta_intro
    outro_cinematic: cin_ch03_penalta_canal
    telegraph: {palette: amber_cyan, min_windup_ms: 600}
    x_interactables:
      - {id: crane_net_1, cut: [act_b17_cleat, rope_b17_1], drop_zone: vol_b17_crane_drop, stun_ms: 3000, damage_taken_mult: 1.5, phase: 1}
      - {id: crane_net_2, cut: [act_b17_cleat, rope_b17_2], drop_zone: vol_b17_crane_drop, stun_ms: 3000, damage_taken_mult: 1.5, phase: 2}
    x_resupply: {id: sup_b17_shells, shells: 5, per_phase: 1}
    x_protected: [vol_b17_pen]
    music: boss_penalta
    dialogue:
      - {"on": beat_start, lines: [ch03.b17.penalta.001], mode: ambient}
      - {"on": "pattern:hammer_slam", lines: [ch03.b17.penalta.002], mode: ambient, repeatable: true}
      - {"on": "pattern:shield_bash", lines: [ch03.b17.penalta.003], mode: ambient, repeatable: true}
      - {"on": "x_boss_hint:front_blocked", lines: [ch03.b17.kohagi.004], mode: radio}
      - {"on": "x_boss_hint:crane", lines: [ch03.b17.kohagi.005], mode: radio}
      - {"on": "boss_phase:2", lines: [ch03.b17.penalta.006, ch03.b17.nyaakoto.007], mode: ambient}
      - {"on": "pattern:hammer_spin", lines: [ch03.b17.penalta.008], mode: ambient, repeatable: true}
      - {"on": "pattern:seal_trap", lines: [ch03.b17.penalta.009], mode: ambient, repeatable: true}
      - {"on": player_died, lines: [ch03.b17.penalta.010], mode: ambient, repeatable: true}
      - {"on": x_boss_defeated, lines: [ch03.b17.penalta.011], mode: ambient}
    fail: {"on": player_died, to: phase_checkpoint}
    barks:
      - {"on": "pattern:shield_bash", line: ch03.b17.penalta.003}
      - {"on": "pattern:hammer_slam", line: ch03.b17.penalta.002}
      - {"on": "pattern:hammer_spin", line: ch03.b17.penalta.008}
      - {"on": "pattern:seal_trap", line: ch03.b17.penalta.009}
      - {"on": "boss_phase:2", line: ch03.b17.penalta.006}
      - {"on": player_died, line: ch03.b17.penalta.010}
  - id: ch03.b18
    type: cinematic
    place: pl_lantern_ward_rain
    title_ja: "灯が戻る"
    title_en: "The lanterns return"
    target_s: 90
    checkpoint: true
    sequence: "/Game/Cinematics/Ch03/LS_Ch03_B18_LanternsRelit"
    duration_s: 90
    skippable: true
    fallback: camera_blend
    end_state: {player_transform: ps_ch04_handoff, equipped: [0, 4, 18, 7]}
    music: ch03_lanterns_relit
    subtitles:
      - {line: ch03.b18.oyuki.001, at_s: 10.0}
      - {line: ch03.b18.nyaakoto.002, at_s: 16.0}
      - {line: ch03.b18.tokichi.003, at_s: 34.0}
      - {line: ch03.b18.oyuki.004, at_s: 52.0}
      - {line: ch03.b18.kohagi.005, at_s: 62.0}
      - {line: ch03.b18.nyaakoto.006, at_s: 78.0}
collectibles:
  - collectible_id: ch03.c01
    category: league_mark
    place: pl_ura_nagaya
    mask_bit: 0
    codex: {ja: "子どもの白墨の空紋。大人の目の高さには描かれていない。", en: "A child's chalk sky crest, drawn below adult eye level."}
  - collectible_id: ch03.c02
    category: seizure_notice
    place: pl_ura_nagaya
    mask_bit: 1
    codex: {ja: "差押状。後家の家財一式、担保として計上済み。", en: "Seizure notice: a widow's household goods, booked as collateral."}
  - collectible_id: ch03.c03
    category: scroll_fragment
    place: pl_ura_nagaya
    mask_bit: 2
    codex: {ja: "伝書の断簡。「刀を抜くより先に、足もとを見よ。」", en: "Scroll fragment: 'Before you draw, look at where you stand.'"}
  - collectible_id: ch03.c04
    category: heirloom
    place: pl_chochin_kobo
    mask_bit: 3
    codex: {ja: "灯吉の師匠の箱提灯。押収札が付いたまま。", en: "Tōkichi's master's box lantern, still wearing its seizure tag."}
  - collectible_id: ch03.c05
    category: registry_page
    place: pl_ura_nagaya
    mask_bit: 4
    codex: {ja: "お雪の下書き。五箇条のうち、まだ三条しかない。", en: "Oyuki's draft of the charter. Only three articles so far."}
  - collectible_id: ch03.c06
    category: league_mark
    place: pl_lantern_ward_rain
    mask_bit: 5
    codex: {ja: "蔵の壁に炭で描かれた大きな空紋。もう子どもの高さではない。", en: "A large charcoal sky crest on a storehouse. No longer at child height."}
layout:
  origin: "Arena 1 origin = centre of the 高札場 crossing; +X east, +Y north, Z up; cm"
  volumes:
    vol_b02_landing: {min: [-12000, -2800, 0], max: [-7600, -1200, 800]}
    vol_b02_drones: {min: [-11800, -2800, 0], max: [-10800, -2000, 400]}
    vol_b02_puddles: {min: [-10800, -2400, 0], max: [-10000, -1800, 400]}
    vol_b02_andon: {min: [-11800, -1700, 0], max: [-10800, -1200, 400]}
    vol_b02_exit: {min: [-8000, -1000, 0], max: [-7640, -700, 400]}
    vol_b03_kido: {min: [-8000, -700, 0], max: [-5600, 700, 900]}
    vol_b03_first_conscript: {min: [-7600, -700, 0], max: [-7000, 700, 400]}
    vol_b03_bansho_rear: {min: [-7000, -700, 0], max: [-6700, -430, 400]}
    vol_b03_culvert: {min: [-6300, -700, -90], max: [-6100, -600, 0]}
    vol_b03_exit: {min: [-6000, -360, 0], max: [-5600, 360, 400]}
    vol_b04_nagaya: {min: [-3400, 400, 0], max: [-2200, 4200, 800]}
    vol_b05_alley_mouth: {min: [-2890, 400, 0], max: [-2710, 900, 400]}
    vol_b07_start: {min: [-2890, 900, 0], max: [-2710, 1200, 400]}
    vol_b07_patrol1: {min: [-3100, 300, 0], max: [-2500, 900, 400]}
    vol_b07_oilshop: {min: [-900, -2800, 0], max: [-300, -2200, 400]}
    vol_b07_patrol3: {min: [400, -2800, 0], max: [900, -2200, 400]}
    vol_b08_kobo_yard: {min: [1600, -2200, 0], max: [3400, -900, 900]}
    vol_b10_kosatsuba: {min: [-2200, -1000, 0], max: [1600, 3200, 1200]}
    vol_b10_glint: {min: [-900, -700, 0], max: [900, 700, 500]}
    vol_b10_dobuita_n: {min: [-900, 360, 0], max: [900, 405, 50]}
    vol_b10_dobuita_s: {min: [-900, -405, 0], max: [900, -360, 50]}
    vol_b10_roofs: {min: [-1600, 405, 450], max: [1600, 1300, 900]}
    vol_b10_blast_safe: {min: [-2200, 2900, 0], max: [-1000, 3100, 400]}
    vol_b14_kitchen: {min: [-3400, 2220, 0], max: [-2200, 3600, 600]}
    vol_b14_supply: {min: [-2500, 3500, 0], max: [-2300, 3700, 300]}
    vol_b16_canal_lane: {min: [-300, -2800, 0], max: [5000, -1500, 900]}
    vol_b16_mid: {min: [1900, -2800, 0], max: [2300, -2200, 400]}
    vol_b17_wharf: {min: [5000, -2800, 0], max: [8600, -400, 1200]}
    vol_b17_crane_drop: {centre: [7800, -2000, 0], radius: 200}
    vol_b17_pen: {min: [5100, -1200, 0], max: [5700, -700, 300]}
  spawns:
    ps_b02_start: [-11300, -2700, 0]
    sp_b03_wicket: [-6300, 150, 0]
    sp_b03_brazier: [-6600, -380, 0]
    sp_b03_arch: [-6250, 0, 0]
    sp_b05_street_w: [-4500, 0, 0]
    sp_b07_tsuji: [-3000, 0, 0]
    sp_b07_air: [-3500, 0, 600]
    sp_b07_lane: [-600, -2500, 0]
    sp_b07_kura: [1200, -2450, 0]
    sp_b08_street: [3400, -1000, 0]
    sp_b08_canal: [2000, -2250, 0]
    sp_b08_eastfence: [3400, -1600, 0]
    sp_b08_kura_roof: [3150, -1900, 650]
    sp_b10_roof: [900, 800, 750]
    sp_b10_east: [3000, 0, 0]
    ps_b12_square: [0, -300, 0]
    ps_b14_kitchen: [-2800, 3000, 0]
    sp_b14_alley_mouth: [-2800, 450, 0]
    sp_b14_backfence_air: [-3500, 3600, 600]
    ps_b16_bridge: [0, -3300, 220]
    sp_b16_lane_mid: [1800, -2500, 0]
    sp_b16_kura_a_roof: [800, -1900, 650]
    sp_b16_wharf_lane: [4800, -2500, 0]
    sp_b16_kura_b_roof: [4100, -1900, 650]
    ps_b17_entry: [5100, -2500, 0]
    sp_b17_penalta: [6800, -1600, 0]
    act_b17_cleat: [8400, -1400, 0]
    sup_b17_shells: [5300, -1300, 0]
    pk_b05_tsurube: [-2600, 3100, 0]
    dp_b05_hideout: [-2550, 1050, 0]
    act_b05_dry_well_rope: [-3100, 3200, 0]
    act_b10_terminal_rear_panel: [-730, 560, 0]
  patrols:
    pt_b02_d1:
      loop_s: 40
      alt_cm: 500
      points: [[-11400, -2000], [-10200, -1500], [-9000, -2000], [-10200, -2500]]
    pt_b02_d2:
      loop_s: 30
      alt_cm: 400
      points: [[-11800, -2700], [-7800, -2700]]
    pt_b03_c2:
      loop_s: 40
      points: [[-7900, -650], [-6300, -650]]
    pt_b03_e2:
      loop_s: 50
      points: [[-7900, -600], [-7900, 600], [-6400, 600], [-6400, -600]]
    pt_b05_omote:
      loop_s: 45
      points: [[-4500, 0], [-1000, 0]]
    pt_b07_p1:
      loop_s: 60
      points: [[-4500, 100], [-1200, 100]]
    pt_b07_d3:
      loop_s: 30
      alt_cm: 600
      points: [[-5000, 0], [1000, 0]]
    pt_b07_p2:
      loop_s: 40
      points: [[-1500, -2500], [200, -2500]]
    pt_b07_p3:
      loop_s: 35
      points: [[500, -2300], [1600, -2300], [1600, -2700], [500, -2700]]
    pt_b10_d:
      loop_s: 36
      alt_cm: 600
      circle: {centre: [0, 0], radius: 1200}
    pt_b10_p1:
      loop_s: 60
      points: [[-800, -600], [800, -600], [800, 600], [-800, 600]]
    pt_b10_p2:
      loop_s: 45
      points: [[0, -2000], [0, 3800]]
    pt_b10_p3:
      loop_s: 70
      points: [[-4000, 0], [4000, 0]]
  splines:
    spl_b07_escort:
      - [-2800, 1050, 0]
      - [-2800, 450, 0]
      - [-2800, -450, 0]
      - [-2800, -2200, 0]
      - [-2800, -2500, 0]
      - [1200, -2500, 0]
      - [2000, -2250, 0]
boss_proposals:
  boss_penalta:
    owner: "L3 (bosses.json); values are proposals"
    hp: {easy: 1600, normal: 2000, hard: 2400}
    windup_scaling: {easy: 1.3, normal: 1.0, hard: 0.85}
    weak_points: [{id: vent_l, mult_open: 2.5, mult_closed: 1.25}, {id: vent_r, mult_open: 2.5, mult_closed: 1.25}]
    shield: {frontal_arc_deg: 120, blocks: [melee, arrow, hitscan], break_on: {weapon: 7, direct_hits: 3}, forced_break_at_hp_pct: 50}
    pattern_tables:
      penalta_p1:
        move: {speed_cm_s: 180, turn_deg_s: 90, mode: shield_advance, contact_push_cm: 150, contact_dmg: 10}
        attacks:
          - id: shield_bash
            windup_ms: 600
            telegraph: amber_rim_pulse
            range_cm: 250
            dmg: 25
            effect: stagger_0.6s
            recovery_ms: 700
            cooldown_s: 3
            guardable: true
            awase: "no_stagger; opens marobashi 400 ms"
            bark: ch03.b17.penalta.003
          - id: hammer_slam
            windup_ms: 1000
            telegraph: amber_ring_350cm
            radius_cm: 350
            dmg_centre: 45
            dmg_edge: 20
            knockdown_radius_cm: 150
            recovery_ms: 1800
            vents_open_ms: 2000
            cooldown_s: 7
            guardable: false
            bark: ch03.b17.penalta.002
        selection: "bash if player in front ≤250 cm and off cooldown; slam if player ≤350 cm and flanking/behind, or every 3rd action"
      penalta_p2:
        move: {speed_cm_s: 250, turn_deg_s: 140, mode: chase}
        attacks:
          - id: hammer_spin
            windup_ms: 1200
            telegraph: amber_ring_400cm
            radius_cm: 400
            active_ms: 1800
            dmg_per_hit: 30
            max_hits: 2
            recovery_ms: 2200
            vents_open_ms: 2200
            cooldown_s: 10
            bark: ch03.b17.penalta.008
          - id: seal_trap
            windup_ms: 700
            telegraph: amber_ring_150cm_on_landing
            count: 2
            arm_ms: 800
            root_ms: 1500
            lifetime_s: 12
            max_active: 4
            destroyed_by: "1 arrow or 1 melee hit"
            cooldown_s: 9
            bark: ch03.b17.penalta.009
          - id: hammer_slam
            windup_ms: 1000
            telegraph: amber_ring_350cm
            radius_cm: 350
            dmg_centre: 45
            dmg_edge: 20
            recovery_ms: 1800
            vents_open_ms: 2000
            cooldown_s: 6
            bark: ch03.b17.penalta.002
        selection: "spin if player ≤400 cm and off cooldown; seal_trap if player >600 cm; else slam"
    voice_telegraph: ch03.b17.penalta.002
    fate: "falls into the canal off-screen (outro cin_ch03_penalta_canal)"
lines:
  - {id: ch03.b01.system.001, speaker: credit_system, ja: "告知。本日の利息を、各戸の残高に計上いたしました。", en: "Notice. Today's interest has been added to each household's balance.", register: alien_device_pa, mode: cinematic, duration_s: 4.6, trigger: "cin@8"}
  - {id: ch03.b01.system.002, speaker: credit_system, ja: "消灯の刻限です。無許可の灯火は、延滞として処理いたします。", en: "It is lights-out. Unlicensed flames will be processed as arrears.", register: alien_device_pa, mode: cinematic, duration_s: 5.1, trigger: "cin@16"}
  - {id: ch03.b01.kohagi.003, speaker: scout, ja: "十日で、この有様。", en: "Ten days, and look at it.", register: terse, mode: cinematic, duration_s: 1.9, trigger: "cin@31"}
  - {id: ch03.b01.nyaakoto.004, speaker: samurai, ja: "……灯りが、一つもない。", en: "…Not a single light.", register: samurai_plain, mode: cinematic, duration_s: 2.4, trigger: "cin@36"}
  - {id: ch03.b01.kohagi.005, speaker: scout, ja: "灯せば借りが増える。だから、誰も灯さない。", en: "Light a lamp and the debt grows. So no one does.", register: terse, mode: cinematic, duration_s: 3.9, trigger: "cin@42"}
  - {id: ch03.b01.kohagi.006, speaker: scout, ja: "刀と弓は先に運んだ。裏長屋の、空井戸の底。", en: "Your sword and bow went ahead. Bottom of the dry well, back tenements.", register: terse, mode: cinematic, duration_s: 4.7, trigger: "cin@63"}
  - {id: ch03.b01.kohagi.007, speaker: scout, ja: "それまでは、これで。", en: "Until then, use this.", register: terse, mode: cinematic, duration_s: 2.1, trigger: "cin@71"}
  - {id: ch03.b01.nyaakoto.008, speaker: samurai, ja: "道中差か。……町人に見えるか。", en: "A travelling short sword. …Do I pass for a townsman?", register: samurai_plain, mode: cinematic, duration_s: 3.5, trigger: "cin@76"}
  - {id: ch03.b01.kohagi.009, speaker: scout, ja: "背筋、伸ばしすぎ。", en: "Your back's too straight.", register: terse, mode: cinematic, duration_s: 1.9, trigger: "cin@82"}
  - {id: ch03.b02.kohagi.001, speaker: scout, ja: "提灯街の工房は三つとも止められた。", en: "All three workshops in Lantern Ward have been shut down.", register: terse, mode: radio, duration_s: 3.8, trigger: beat_start}
  - {id: ch03.b02.kohagi.002, speaker: scout, ja: "目録が二つ、水の上。光の輪に入らないで。", en: "Two Inventories over the water. Stay out of their light.", register: terse, mode: radio, duration_s: 3.8, trigger: "volume_enter:vol_b02_drones"}
  - {id: ch03.b02.kohagi.003, speaker: scout, ja: "水たまりは鳴る。雨でも。", en: "Puddles splash loud. Even in the rain.", register: terse, mode: radio, duration_s: 2.6, trigger: "volume_enter:vol_b02_puddles"}
  - {id: ch03.b02.kohagi.004, speaker: scout, ja: "行灯は消せる。暗いほど、見つからない。", en: "You can snuff the lamps. The darker, the safer.", register: terse, mode: radio, duration_s: 3.5, trigger: "volume_enter:vol_b02_andon"}
  - {id: ch03.b02.drone.005, speaker: drone, ja: "……未登録の熱源を検知。", en: "…Unregistered heat source detected.", register: alien_device, mode: ambient, duration_s: 2.4, repeatable: true, trigger: "alert_state:suspicious"}
  - {id: ch03.b02.drone.006, speaker: drone, ja: "債務者を捕捉。番号を照合します。", en: "Debtor acquired. Verifying account number.", register: alien_device, mode: ambient, duration_s: 3.1, repeatable: true, trigger: "alert_state:alert"}
  - {id: ch03.b02.drone.007, speaker: drone, ja: "照合できません。捜索を継続いたします。", en: "Unable to verify. Search continues.", register: alien_device, mode: ambient, duration_s: 3.5, repeatable: true, trigger: "alert_state:search"}
  - {id: ch03.b02.drone.008, speaker: drone, ja: "記録なし。巡回に戻ります。", en: "No record. Resuming patrol.", register: alien_device, mode: ambient, duration_s: 2.6, repeatable: true, trigger: "x_alert_state:search_to_unaware"}
  - {id: ch03.b02.kohagi.009, speaker: scout, ja: "木戸は北。あたしは屋根から行く。", en: "The ward gate is north. I'll take the roofs.", register: terse, mode: radio, duration_s: 3.1, trigger: beat_complete}
  - {id: ch03.b02.kohagi.010, speaker: scout, ja: "……もう一度。今度は、静かに。", en: "…Again. Quieter this time.", register: terse, mode: radio, duration_s: 2.9, repeatable: true, trigger: player_died}
  - {id: ch03.b03.kohagi.001, speaker: scout, ja: "番は五人。首輪の三人は、町の者。", en: "Five guards. The three in collars are townsfolk.", register: terse, mode: radio, duration_s: 3.2, trigger: beat_start}
  - {id: ch03.b03.kohagi.002, speaker: scout, ja: "首輪の者は斬らないで。峰で倒して、首輪を切る。", en: "Don't cut the collared. Use the blade's back, then cut the collar.", register: terse, mode: radio, duration_s: 4.4, trigger: "volume_enter:vol_b03_first_conscript"}
  - {id: ch03.b03.kohagi.003, speaker: scout, ja: "後ろを取れば、声も出させずに済む。", en: "Take them from behind and they won't make a sound.", register: terse, mode: radio, duration_s: 3.4, trigger: "volume_enter:vol_b03_bansho_rear"}
  - {id: ch03.b03.conscript.004, speaker: conscript, ja: "……誰や？　誰か、おるんか。", en: "…Who's that? Is someone there?", register: townsfolk_compelled, mode: ambient, duration_s: 2.7, repeatable: true, trigger: "alert_state:suspicious"}
  - {id: ch03.b03.conscript.005, speaker: conscript, ja: "堪忍や……体が、勝手に……！", en: "Forgive me… my body won't stop…!", register: townsfolk_compelled, mode: ambient, duration_s: 2.7, repeatable: true, trigger: "alert_state:alert"}
  - {id: ch03.b03.conscript.006, speaker: conscript, ja: "……おらん。おらんかった、ことにしとこ。", en: "…Nobody. Let's say there was nobody.", register: townsfolk_compelled, mode: ambient, duration_s: 3.7, repeatable: true, trigger: "x_alert_state:search_to_unaware"}
  - {id: ch03.b03.enforcer.007, speaker: enforcer, ja: "確認いたします。その場を動かないでください。", en: "Verifying. Please remain where you are.", register: alien_corporate, mode: ambient, duration_s: 4.0, repeatable: true, trigger: "alert_state:suspicious"}
  - {id: ch03.b03.enforcer.008, speaker: enforcer, ja: "未払い者を確認。回収を開始します。", en: "Non-payer confirmed. Commencing collection.", register: alien_corporate, mode: ambient, duration_s: 3.2, repeatable: true, trigger: "alert_state:alert"}
  - {id: ch03.b03.enforcer.009, speaker: enforcer, ja: "記録上、この位置に存在するはずです。", en: "Per the record, you should exist at this location.", register: alien_corporate, mode: ambient, duration_s: 3.4, repeatable: true, trigger: "alert_state:search"}
  - {id: ch03.b03.kidoban.010, speaker: conscript, ja: "……軽い。首が、軽い。", en: "…Light. My neck feels light.", register: townsfolk_elder, mode: ambient, duration_s: 2.3, trigger: "x_npc_freed:kidoban"}
  - {id: ch03.b03.kidoban.011, speaker: conscript, ja: "潜り戸の閂は、外してある。行きなされ。", en: "The wicket's bar is off. Go on through.", register: townsfolk_elder, mode: ambient, duration_s: 3.5, trigger: "x_npc_freed:kidoban+2s"}
  - {id: ch03.b04.resident.001, speaker: resident, ja: "うちの戸の数、また増えとる。寝とる間に。", en: "The number on my door went up again. While I slept.", register: townsfolk_f, mode: ambient, duration_s: 3.7, trigger: "volume_enter:poi_idobata"}
  - {id: ch03.b04.resident.002, speaker: resident, ja: "働く前から借りがある。けったいな世の中や。", en: "In debt before you've worked a day. Strange world.", register: townsfolk_f, mode: ambient, duration_s: 3.9, trigger: "volume_enter:poi_idobata+4s"}
  - {id: ch03.b04.resident.003, speaker: resident, ja: "お侍さんやったら、こんな時どないしはるやろな。", en: "What would a samurai do at a time like this, I wonder.", register: townsfolk_elder_f, mode: ambient, duration_s: 4.2, trigger: "volume_enter:poi_idobata+9s"}
  - {id: ch03.b04.child.004, speaker: child, ja: "これな、空の紋。描いたら、あいつら怒るねん。", en: "This is the sky crest. They get angry when we draw it.", register: child, mode: ambient, duration_s: 4.0, trigger: "volume_enter:poi_chalk"}
  - {id: ch03.b04.child.005, speaker: child, ja: "お兄ちゃん、お侍？　歩き方が、お侍や。", en: "Mister, are you a samurai? You walk like one.", register: child, mode: ambient, duration_s: 3.5, trigger: "volume_enter:poi_chalk+5s"}
  - {id: ch03.b04.resident.006, speaker: resident, ja: "紙だけは上等や。提灯の紙にしたろ。", en: "Their paper's good, at least. It'll make fine lanterns.", register: townsfolk_elder_m, mode: ambient, duration_s: 3.7, trigger: "volume_enter:poi_leaflet"}
  - {id: ch03.b04.nyaakoto.007, speaker: samurai, ja: "……数で、人を縛るのか。", en: "…They bind people with numbers.", register: samurai_plain, mode: ambient, duration_s: 2.4, trigger: "volume_enter:poi_balance_door"}
  - {id: ch03.b05.kohagi.001, speaker: scout, ja: "その井戸。縄は結んである。", en: "That well. The rope's tied off.", register: terse, mode: radio, duration_s: 2.6, trigger: beat_start}
  - {id: ch03.b05.nyaakoto.002, speaker: samurai, ja: "刀は民から預かるもの……。預かり直す。", en: "A blade is held in trust from the people. …I take it up again.", register: samurai_plain, mode: ambient, duration_s: 4.2, trigger: "x_item_picked:sword_bundle"}
  - {id: ch03.b05.kohagi.003, speaker: scout, ja: "箱は三つ。釣瓶で上げて、灯吉さんのとこへ。", en: "Three crates. Haul them up on the well rope, then take them to Tōkichi.", register: terse, mode: radio, duration_s: 4.8, trigger: "x_item_picked:sword_bundle+4s"}
  - {id: ch03.b05.conscript.004, speaker: conscript, ja: "雨の見回りは、骨にこたえる……。", en: "Rain patrols get into your bones…", register: townsfolk_compelled, mode: ambient, duration_s: 3.1, trigger: "volume_enter:vol_b05_alley_mouth"}
  - {id: ch03.b05.tokichi.005, speaker: lantern_maker, ja: "おお……わしの型や。よう無事で。", en: "Oh… my forms. Safe and sound.", register: artisan_gentle, mode: ambient, duration_s: 3.1, trigger: "progress_at:0.33"}
  - {id: ch03.b05.tokichi.006, speaker: lantern_maker, ja: "これで全部や。おおきに、お侍さん。", en: "That's all of them. Thank you, samurai.", register: artisan_gentle, mode: ambient, duration_s: 3.2, trigger: beat_complete}
  - {id: ch03.b06.tokichi.001, speaker: lantern_maker, ja: "道具は隠した。火さえ戻れば、また作れる。", en: "We hid the tools. Restore the fires, and we can make things again.", register: artisan_gentle, mode: ambient, duration_s: 4.4, trigger: beat_start}
  - {id: ch03.b06.tokichi.002, speaker: lantern_maker, ja: "けど工房の戸に、あの青い封が貼られとる。", en: "But that blue seal is fixed on the workshop door.", register: artisan_gentle, mode: ambient, duration_s: 3.7, trigger: seq}
  - {id: ch03.b06.tamakichi.003, speaker: fireworks, ja: "封なら、わいが吹っ飛ばしたる！", en: "A seal? I'll blow it clean off!", register: kamigata_cheerful, mode: ambient, duration_s: 2.9, trigger: seq}
  - {id: ch03.b06.tokichi.004, speaker: lantern_maker, ja: "玉吉、声。", en: "Tamakichi. Your voice.", register: artisan_gentle, mode: ambient, duration_s: 1.5, trigger: seq}
  - {id: ch03.b06.tamakichi.005, speaker: fireworks, ja: "……吹っ飛ばしたる。", en: "…I'll blow it clean off.", register: kamigata_cheerful, mode: ambient, duration_s: 2.1, trigger: seq}
  - {id: ch03.b06.tamakichi.006, speaker: fireworks, ja: "祭りの玉が十二、床下にある。筒さえ組めば、武器になるで。", en: "Twelve festival shells under the floor. Build a tube and they're a weapon.", register: kamigata_cheerful, mode: ambient, duration_s: 5.0, trigger: seq}
  - {id: ch03.b06.nyaakoto.007, speaker: samurai, ja: "工房までは私が守る。皆、私の合図で伏せてくれ。", en: "I will guard you to the workshop. Everyone, get down on my signal.", register: samurai_polite, mode: ambient, duration_s: 4.4, trigger: seq}
  - {id: ch03.b06.kohagi.008, speaker: scout, ja: "裏道は見てきた。見回りは三組。", en: "I've checked the back way. Three patrols.", register: terse, mode: ambient, duration_s: 2.9, trigger: seq}
  - {id: ch03.b07.kohagi.001, speaker: scout, ja: "一組目は辻。目録が過ぎるまで待って。", en: "First patrol's at the crossing. Wait for the Inventory to pass.", register: terse, mode: radio, duration_s: 4.2, trigger: beat_start}
  - {id: ch03.b07.isa.002, speaker: artisan, ja: "竹割りの伊三や。足は遅いが、口は堅いで。", en: "Isa, bamboo-splitter. Slow feet, tight lips.", register: artisan_gruff, mode: ambient, duration_s: 3.7, trigger: "beat_start+6s"}
  - {id: ch03.b07.nyaakoto.003, speaker: samurai, ja: "伏せろ。", en: Down., register: samurai_bark, mode: ambient, duration_s: 1.2, repeatable: true, trigger: "x_signal:hide"}
  - {id: ch03.b07.nyaakoto.004, speaker: samurai, ja: "今だ。進め。", en: "Now. Move.", register: samurai_bark, mode: ambient, duration_s: 1.5, repeatable: true, trigger: "x_signal:go"}
  - {id: ch03.b07.tamakichi.005, speaker: fireworks, ja: "……心の臓が、玉みたいに跳ねとる。", en: "…My heart's jumping like a shell.", register: kamigata_cheerful, mode: ambient, duration_s: 3.2, trigger: "volume_enter:vol_b07_patrol1"}
  - {id: ch03.b07.tokichi.006, speaker: lantern_maker, ja: "ここは油屋やった。灯りの油も、今は奴らの帳面の中や。", en: "This was the oil shop. Now even lamp oil lives in their ledger.", register: artisan_gentle, mode: ambient, duration_s: 4.7, trigger: "volume_enter:vol_b07_oilshop"}
  - {id: ch03.b07.isa.007, speaker: artisan, ja: "すまん、足が……！", en: "Sorry—my leg…!", register: artisan_gruff, mode: ambient, duration_s: 1.9, repeatable: true, trigger: "npc_downed:isa"}
  - {id: ch03.b07.nyaakoto.008, speaker: samurai, ja: "立てるか。肩を貸す。", en: "Can you stand? Lean on me.", register: samurai_plain, mode: ambient, duration_s: 2.1, repeatable: true, trigger: "x_npc_revived:any"}
  - {id: ch03.b07.kohagi.009, speaker: scout, ja: "最後の組は蔵の裏。刀持ちがいる。", en: "Last patrol's behind the storehouse. One carries a blade.", register: terse, mode: radio, duration_s: 3.8, trigger: "volume_enter:vol_b07_patrol3"}
  - {id: ch03.b07.tokichi.010, speaker: lantern_maker, ja: "着いた……。ここが、わしの工房や。", en: "We made it… This is my workshop.", register: artisan_gentle, mode: ambient, duration_s: 3.2, trigger: beat_complete}
  - {id: ch03.b08.system.001, speaker: credit_system, ja: "封印への接触を検知。執行班を要請します。", en: "Seal contact detected. Requesting an enforcement team.", register: alien_device, mode: ambient, duration_s: 3.7, trigger: beat_start}
  - {id: ch03.b08.nyaakoto.002, speaker: samurai, ja: "中へ！　戸を閉めて、伏せていろ。", en: "Inside! Close the door and stay down.", register: samurai_bark, mode: ambient, duration_s: 3.1, trigger: "beat_start+3s"}
  - {id: ch03.b08.tokichi.003, speaker: lantern_maker, ja: "頼んだで……！", en: "We're counting on you…!", register: artisan_gentle, mode: ambient, duration_s: 1.6, trigger: "beat_start+6s"}
  - {id: ch03.b08.enforcer.004, speaker: enforcer, ja: "業務妨害を確認。関係者全員が回収対象です。", en: "Obstruction confirmed. All involved parties are subject to collection.", register: alien_corporate, mode: ambient, duration_s: 4.7, trigger: "x_wave_start:1"}
  - {id: ch03.b08.grenadier.005, speaker: enforcer, ja: "区画を整理いたします。", en: "Clearing the section.", register: alien_corporate_grenadier, mode: ambient, duration_s: 2.3, repeatable: true, trigger: "pattern:grenadier_fire"}
  - {id: ch03.b08.enforcer.006, speaker: enforcer, ja: "損失を計上。後退いたします。", en: "Loss recorded. Withdrawing.", register: alien_corporate, mode: ambient, duration_s: 2.7, repeatable: true, trigger: "x_ai:withdraw"}
  - {id: ch03.b08.tamakichi.007, speaker: fireworks, ja: "……静かになった。もう、ええか？", en: "…It's gone quiet. Is it safe?", register: kamigata_cheerful, mode: ambient, duration_s: 3.1, trigger: beat_complete}
  - {id: ch03.b08.kohagi.008, speaker: scout, ja: "立って。まだ終わってない。", en: "Get up. It isn't over.", register: terse, mode: radio, duration_s: 2.6, repeatable: true, trigger: player_died}
  - {id: ch03.b09.tokichi.001, speaker: lantern_maker, ja: "竹を割って、輪にする。型に掛けて、六つや。", en: "Split the bamboo, bend it into hoops. Six on the form.", register: artisan_gentle, mode: ambient, duration_s: 3.9, trigger: beat_start}
  - {id: ch03.b09.tokichi.002, speaker: lantern_maker, ja: "そうや。力やない、竹の癖に合わせるんや。", en: "That's it. Not force—follow the bamboo's grain.", register: artisan_gentle, mode: ambient, duration_s: 3.7, trigger: "progress_at:0.3"}
  - {id: ch03.b09.tokichi.003, speaker: lantern_maker, ja: "紙は継ぎ目を重ねて貼る。雨が入らんようにな。", en: "Overlap the seams as you paste. Keep the rain out.", register: artisan_gentle, mode: ambient, duration_s: 4.0, trigger: "progress_at:0.5"}
  - {id: ch03.b09.tokichi.004, speaker: lantern_maker, ja: "仕上げに荏の油を引く。これで五月雨にも負けん。", en: "Finish with perilla oil. Then it will stand up to the rains.", register: artisan_gentle, mode: ambient, duration_s: 4.2, trigger: "progress_at:0.65"}
  - {id: ch03.b09.nyaakoto.005, speaker: samurai, ja: "……刀より、難しい。", en: "…Harder than the sword.", register: samurai_plain, mode: ambient, duration_s: 2.1, trigger: "progress_at:0.72"}
  - {id: ch03.b09.isa.006, speaker: artisan, ja: "四十張、朝までに仕上げたる。", en: "Forty lanterns, done by morning.", register: artisan_gruff, mode: ambient, duration_s: 2.7, trigger: "progress_at:0.78"}
  - {id: ch03.b09.tamakichi.007, speaker: fireworks, ja: "次はこっちや。玉を紙で巻いて、筒に合わせる。", en: "Over here now. Wrap the shell in paper, fit it to the tube.", register: kamigata_cheerful, mode: ambient, duration_s: 4.0, trigger: "progress_at:0.8"}
  - {id: ch03.b09.tamakichi.008, speaker: fireworks, ja: "ほれ、花火筒や。高う上げて落とす。弧を読むんやで。", en: "Here—the shell tube. Loft it high and let it fall. Read the arc.", register: kamigata_cheerful, mode: ambient, duration_s: 4.5, trigger: beat_complete}
  - {id: ch03.b09.tamakichi.009, speaker: fireworks, ja: "近うで撃ったら、自分も焦げるで。", en: "Fire it up close and you'll get singed too.", register: kamigata_cheerful, mode: ambient, duration_s: 3.1, trigger: "beat_complete+5s"}
  - {id: ch03.b10.kohagi.001, speaker: scout, ja: "高札場。端末の上、屋根に鉄砲持ちが一人。", en: "The notice square. A marksman on the roof above the terminal.", register: terse, mode: radio, duration_s: 4.1, trigger: beat_start}
  - {id: ch03.b10.kohagi.002, speaker: scout, ja: "光ったら、狙われてる。すぐ物陰へ。", en: "If you see a glint, you're targeted. Get behind cover.", register: terse, mode: radio, duration_s: 3.6, trigger: "volume_enter:vol_b10_glint"}
  - {id: ch03.b10.kohagi.003, speaker: scout, ja: "溝板は鳴る。端を踏んで。", en: "The drain boards rattle. Walk the edges.", register: terse, mode: radio, duration_s: 2.7, trigger: "volume_enter:vol_b10_dobuita"}
  - {id: ch03.b10.system.004, speaker: credit_system, ja: "端末は、正常に稼働しております。", en: "The terminal is operating normally.", register: alien_device_pa, mode: ambient, duration_s: 3.1, trigger: "idle_s:20"}
  - {id: ch03.b10.marksman.005, speaker: enforcer, ja: "照準内に不明な影。査定します。", en: "Unknown shadow in my sights. Assessing.", register: alien_corporate_marksman, mode: ambient, duration_s: 2.9, repeatable: true, trigger: "alert_state:suspicious"}
  - {id: ch03.b10.marksman.006, speaker: enforcer, ja: "査定完了。価値、なし。", en: "Assessment complete. Value: none.", register: alien_corporate_marksman, mode: ambient, duration_s: 2.3, repeatable: true, trigger: "alert_state:alert"}
  - {id: ch03.b10.enforcer.007, speaker: enforcer, ja: "端末付近に不正接触。至急、増援を。", en: "Unauthorized contact near the terminal. Reinforcements, at once.", register: alien_corporate, mode: ambient, duration_s: 4.3, trigger: "x_reinforce:w_b10_reinforce"}
  - {id: ch03.b10.nyaakoto.008, speaker: samurai, ja: "火縄に火を。……離れる。", en: "Light the fuse. …Now, clear out.", register: samurai_plain, mode: ambient, duration_s: 2.4, trigger: "x_objective:obj_light_fuse"}
  - {id: ch03.b11.resident.001, speaker: resident, ja: "……戸の数が、消えた。", en: "…The number on the door. It's gone.", register: townsfolk_mother, mode: cinematic, duration_s: 2.4, trigger: "cin@24"}
  - {id: ch03.b11.child.002, speaker: child, ja: "母ちゃん、外、出てもええの？", en: "Mama, can we go outside?", register: child, mode: cinematic, duration_s: 2.7, trigger: "cin@31"}
  - {id: ch03.b11.resident.003, speaker: resident, ja: "……ええよ。雨やけど、ええよ。", en: "…Yes. It's raining, but yes.", register: townsfolk_mother, mode: cinematic, duration_s: 2.9, trigger: "cin@36"}
  - {id: ch03.b11.nyaakoto.004, speaker: samurai, ja: "消えたのは端末一つ。帳面は、まだどこかにある。", en: "One terminal is gone. The ledger is still out there.", register: samurai_plain, mode: cinematic, duration_s: 4.2, trigger: "cin@70"}
  - {id: ch03.b12.oyuki.001, speaker: leader, ja: "見事な火薬でございました。ただ、あれは帳簿の写しにすぎません。", en: "Splendid powder. But that was only a copy of their ledger.", register: business_keigo, mode: ambient, duration_s: 5.5, trigger: beat_start}
  - {id: ch03.b12.nyaakoto.002, speaker: samurai, ja: "……どなたか。", en: "…And you are?", register: samurai_polite, mode: ambient, duration_s: 1.6, trigger: seq}
  - {id: ch03.b12.oyuki.003, speaker: leader, ja: "白澄の雪と申します。父に代わり、勘定を預かっておりました。", en: "Oyuki, of the Shirasumi. I kept the domain accounts for my father.", register: business_keigo, mode: ambient, duration_s: 5.1, trigger: seq}
  - {id: ch03.b12.oyuki.004, speaker: leader, ja: "彼らの“信用”は、借りとして生まれるのです。", en: "Their 'credit' is born as debt.", register: business_keigo, mode: ambient, duration_s: 4.0, trigger: seq}
  - {id: ch03.b12.oyuki.005, speaker: leader, ja: "無から貸し、利を付ける。返す物など、どこにもございません。", en: "They lend from nothing and add interest. What is owed exists nowhere.", register: business_keigo, mode: ambient, duration_s: 5.1, trigger: seq}
  - {id: ch03.b12.nyaakoto.006, speaker: samurai, ja: "では、いかがすれば。", en: "Then what is to be done?", register: samurai_polite, mode: ambient, duration_s: 2.1, trigger: seq}
  - {id: ch03.b12.oyuki.007, speaker: leader, ja: "作った物だけを数えるのです。今夜の提灯は、確かにございます。", en: "We count only what is made. Tonight's lanterns—those are real.", register: business_keigo, mode: ambient, duration_s: 5.3, trigger: seq}
  - {id: ch03.b12.oyuki.008, speaker: leader, ja: "皆様、長屋にお集まりです。一揆を、結びとうございます。", en: "Everyone waits at the tenements. I wish to bind a league.", register: business_keigo, mode: ambient, duration_s: 4.8, trigger: seq}
  - {id: ch03.b13.oyuki.001, speaker: leader, ja: "これより、一味神水の儀を執り行います。", en: "We now begin the rite of the shared sacred water.", register: business_keigo, mode: cinematic, duration_s: 3.5, trigger: "cin@6"}
  - {id: ch03.b13.oyuki.002, speaker: leader, ja: "名は輪にして書きます。誰が先でも、後でもございません。", en: "We sign in a circle. No one is first, and no one last.", register: business_keigo, mode: cinematic, duration_s: 4.8, trigger: "cin@18"}
  - {id: ch03.b13.tokichi.003, speaker: lantern_maker, ja: "輪の真ん中には、空の紋を。", en: "And the sky crest at the centre.", register: artisan_gentle, mode: cinematic, duration_s: 2.6, trigger: "cin@29"}
  - {id: ch03.b13.nyaakoto.004, speaker: samurai, ja: "猫柳生の紋です。……我が師の、家の紋です。", en: "The crest of Nyaagyu. …My master's house.", register: samurai_polite, mode: cinematic, duration_s: 3.9, trigger: "cin@35"}
  - {id: ch03.b13.oyuki.005, speaker: leader, ja: "では今日からは、皆の紋に。", en: "Then from today, it belongs to all of us.", register: business_keigo, mode: cinematic, duration_s: 2.8, trigger: "cin@43"}
  - {id: ch03.b13.kohagi.006, speaker: scout, ja: "あたし、字は書けない。印でいい？", en: "I can't write. Will a mark do?", register: terse, mode: cinematic, duration_s: 3.1, trigger: "cin@62"}
  - {id: ch03.b13.oyuki.007, speaker: leader, ja: "印で十分でございます。", en: "A mark is quite enough.", register: business_keigo, mode: cinematic, duration_s: 2.3, trigger: "cin@67"}
  - {id: ch03.b13.nyaakoto.008, speaker: samurai, ja: "斬るのは最後だ。まず、守るものを数える。", en: "Cutting comes last. First, count what we protect.", register: samurai_plain, mode: cinematic, duration_s: 3.7, trigger: "cin@98"}
  - {id: ch03.b14.oyuki.001, speaker: leader, ja: "炊き出しを始めます。火を絶やさず、列をお守りくださいまし。", en: "We begin serving. Keep the fires lit and guard the line.", register: business_keigo, mode: ambient, duration_s: 5.1, trigger: beat_start}
  - {id: ch03.b14.oyuki.002, speaker: leader, ja: "米は町の蔵から。差し押さえの前に、帳面から外しておきました。", en: "The rice is from the ward store. I took it off their books first.", register: business_keigo, mode: ambient, duration_s: 5.3, trigger: "beat_start+7s"}
  - {id: ch03.b14.resident.003, speaker: resident, ja: "温かい飯なんて、十日ぶりや。", en: "First hot meal in ten days.", register: townsfolk_m, mode: ambient, duration_s: 2.7, trigger: "progress_at:0.15"}
  - {id: ch03.b14.kohagi.004, speaker: scout, ja: "見回りが来る。路地の口。", en: "Patrol coming. Mouth of the alley.", register: terse, mode: radio, duration_s: 2.4, trigger: "progress_at:0.28"}
  - {id: ch03.b14.enforcer.005, speaker: enforcer, ja: "無許可の集会を確認。帳簿に記載いたします。", en: "Unlicensed assembly observed. Entering it in the ledger.", register: alien_corporate, mode: ambient, duration_s: 3.9, trigger: "x_wave_start:1"}
  - {id: ch03.b14.oyuki.006, speaker: leader, ja: "竈の火が細っております。", en: "A cook-fire is dying down.", register: business_keigo, mode: ambient, duration_s: 2.4, repeatable: true, trigger: x_fire_out}
  - {id: ch03.b14.tamakichi.007, speaker: fireworks, ja: "玉はここに置いとく。要るだけ持っていき。", en: "I'll leave shells here. Take what you need.", register: kamigata_cheerful, mode: ambient, duration_s: 3.7, trigger: "volume_enter:vol_b14_supply"}
  - {id: ch03.b14.oyuki.008, speaker: leader, ja: "提灯四十張、炊き出し百二十食。……書き留めました。", en: "Forty lanterns. A hundred and twenty meals. …Recorded.", register: business_keigo, mode: ambient, duration_s: 4.5, trigger: beat_complete}
  - {id: ch03.b15.kohagi.001, speaker: scout, ja: "河岸で人を集めてる。……担保だって。", en: "They're rounding people up at the wharf. …As collateral.", register: terse, mode: cinematic, duration_s: 3.8, trigger: "cin@4"}
  - {id: ch03.b15.penalta.002, speaker: boss_penalta, ja: "端末損壊の弁済として、当区画の住民を担保に計上いたします。", en: "For damages to the terminal, residents are now booked as collateral.", register: alien_corporate_boss, mode: cinematic, duration_s: 5.1, trigger: "cin@17"}
  - {id: ch03.b15.nyaakoto.003, speaker: samurai, ja: "……虎之介？", en: "…Toranosuke?", register: samurai_plain, mode: cinematic, duration_s: 1.5, trigger: "cin@31"}
  - {id: ch03.b15.toranosuke.004, speaker: rival, ja: "見るな、ニャーコト。", en: "Do not look at me, Nyaakoto.", register: rival_clipped, mode: cinematic, duration_s: 2.1, trigger: "cin@35"}
  - {id: ch03.b15.toranosuke.005, speaker: rival, ja: "うちの家の借りは、買われた。今の俺は、奴らの物だ。", en: "My house's debt was bought. I am theirs now.", register: rival_clipped, mode: cinematic, duration_s: 4.5, trigger: "cin@40"}
  - {id: ch03.b15.nyaakoto.006, speaker: samurai, ja: "その羽織は、似合わない。", en: "That haori does not suit you.", register: samurai_plain, mode: cinematic, duration_s: 2.4, trigger: "cin@49"}
  - {id: ch03.b15.toranosuke.007, speaker: rival, ja: "……黙れ。", en: "…Silence.", register: rival_clipped, mode: cinematic, duration_s: 1.3, trigger: "cin@54"}
  - {id: ch03.b15.penalta.008, speaker: boss_penalta, ja: "債務者番号二二〇四、鷲尾殿。帳簿を城へお運びください。", en: "Debtor two-two-zero-four, Washio. Kindly deliver the ledger to the citadel.", register: alien_corporate_boss, mode: cinematic, duration_s: 5.0, trigger: "cin@63"}
  - {id: ch03.b16.kohagi.001, speaker: scout, ja: "屋根に二人！　花火筒で落として！", en: "Two on the roofs! Knock them down with the shell tube!", register: terse, mode: radio, duration_s: 3.6, trigger: beat_start}
  - {id: ch03.b16.enforcer.002, speaker: enforcer, ja: "追跡中。対象は河岸方面へ移動。", en: "In pursuit. Target moving toward the wharf.", register: alien_corporate, mode: ambient, duration_s: 2.9, trigger: "x_wave_start:1"}
  - {id: ch03.b16.nyaakoto.003, speaker: samurai, ja: "河岸へ。一人も渡さぬ。", en: "To the wharf. We give up no one.", register: samurai_plain, mode: ambient, duration_s: 2.3, trigger: "volume_enter:vol_b16_mid"}
  - {id: ch03.b16.kohagi.004, speaker: scout, ja: "右の蔵、屋根の上！", en: "Right storehouse—on the roof!", register: terse, mode: radio, duration_s: 2.0, trigger: "x_wave_start:2"}
  - {id: ch03.b17.penalta.001, speaker: boss_penalta, ja: "債務者番号、未登録。……では、新規にお作りいたします。", en: "Account number: unregistered. …Then we shall open one for you.", register: alien_corporate_boss, mode: ambient, duration_s: 4.8, trigger: beat_start}
  - {id: ch03.b17.penalta.002, speaker: boss_penalta, ja: "延滞金が発生しております。", en: "Late fees have been incurred.", register: alien_corporate_boss, mode: ambient, duration_s: 2.6, repeatable: true, trigger: "pattern:hammer_slam"}
  - {id: ch03.b17.penalta.003, speaker: boss_penalta, ja: "ご返済を。", en: "Repayment, please.", register: alien_corporate_boss, mode: ambient, duration_s: 1.3, repeatable: true, trigger: "pattern:shield_bash"}
  - {id: ch03.b17.kohagi.004, speaker: scout, ja: "前は無駄！　回り込んで、背中の排気口！", en: "The front's no use! Get round—the vents on his back!", register: terse, mode: radio, duration_s: 3.5, trigger: "x_boss_hint:front_blocked"}
  - {id: ch03.b17.kohagi.005, speaker: scout, ja: "上の網！　綱を切れば落ちる！", en: "The net above! Cut the rope and it drops!", register: terse, mode: radio, duration_s: 2.8, trigger: "x_boss_hint:crane"}
  - {id: ch03.b17.penalta.006, speaker: boss_penalta, ja: "……盾の損耗は、貴殿の口座に計上いたします。", en: "…The shield's depreciation will be charged to your account.", register: alien_corporate_boss, mode: ambient, duration_s: 4.0, trigger: "boss_phase:2"}
  - {id: ch03.b17.nyaakoto.007, speaker: samurai, ja: "重さに頼る者は、重さに崩れる。", en: "Those who lean on weight fall by it.", register: samurai_plain, mode: ambient, duration_s: 2.9, trigger: "boss_phase:2+3s"}
  - {id: ch03.b17.penalta.008, speaker: boss_penalta, ja: "一括にて、回収いたします。", en: "Collecting in full.", register: alien_corporate_boss, mode: ambient, duration_s: 2.6, repeatable: true, trigger: "pattern:hammer_spin"}
  - {id: ch03.b17.penalta.009, speaker: boss_penalta, ja: "延滞の印を、押させていただきます。", en: "Allow me to stamp you delinquent.", register: alien_corporate_boss, mode: ambient, duration_s: 3.2, repeatable: true, trigger: "pattern:seal_trap"}
  - {id: ch03.b17.penalta.010, speaker: boss_penalta, ja: "お支払い、ありがとうございました。", en: "Thank you for your payment.", register: alien_corporate_boss, mode: ambient, duration_s: 3.2, repeatable: true, trigger: player_died}
  - {id: ch03.b17.penalta.011, speaker: boss_penalta, ja: "……計算に……ない……", en: "…This is not… in the calculation…", register: alien_corporate_boss, mode: ambient, duration_s: 2.3, trigger: x_boss_defeated}
  - {id: ch03.b18.oyuki.001, speaker: leader, ja: "皆様、灯を。", en: "Everyone—the lanterns.", register: business_keigo, mode: cinematic, duration_s: 1.5, trigger: "cin@10"}
  - {id: ch03.b18.nyaakoto.002, speaker: samurai, ja: "火を灯そう。街の明かりは民のものだ。", en: "Then let us light them. This ward's lanterns belong to its people.", register: samurai_plain, mode: cinematic, duration_s: 4.4, trigger: "cin@16"}
  - {id: ch03.b18.tokichi.003, speaker: lantern_maker, ja: "どの提灯にも、空の紋を描いといたで。", en: "I painted the sky crest on every one.", register: artisan_gentle, mode: cinematic, duration_s: 3.4, trigger: "cin@34"}
  - {id: ch03.b18.oyuki.004, speaker: leader, ja: "次は田でございます。水がなければ、何一つ作れません。", en: "Next, the fields. Without water, nothing can be made.", register: business_keigo, mode: cinematic, duration_s: 4.7, trigger: "cin@52"}
  - {id: ch03.b18.kohagi.005, speaker: scout, ja: "下村の堤、見てくる。", en: "I'll go look at the Lower Village dikes.", register: terse, mode: cinematic, duration_s: 2.7, trigger: "cin@62"}
  - {id: ch03.b18.nyaakoto.006, speaker: samurai, ja: "……先生。一つ、灯りました。", en: "…Sensei. One light is lit.", register: samurai_polite, mode: cinematic, duration_s: 2.7, trigger: "cin@78"}
ui_prompts:
  - {id: ui.ch03.crouch, beat: ch03.b02, ja: "しゃがむと足音が小さくなる", en: "Crouch to move quietly", x_shown: "First 10 s of b02"}
  - {id: ui.ch03.puddle, beat: ch03.b02, "on": "volume_enter:vol_b02_puddles", ja: "水たまりは大きな音を立てる", en: "Puddles make noise", x_shown: "On vol_b02_puddles"}
  - {id: ui.ch03.snuff, beat: ch03.b02, "on": "look_at:andon", ja: "{Interact}長押し：灯りを消す", en: "Hold {Interact}: snuff the lamp", x_shown: "Near a snuffable lamp"}
  - {id: ui.ch03.states, beat: ch03.b02, "on": "alert_state:suspicious:first", ja: "気配：不審 → 警戒 → 捜索", en: "Awareness: Suspicious → Alert → Searching", x_shown: "First suspicion"}
  - {id: ui.ch03.takedown, beat: ch03.b03, "on": "ai_event:first_rear_reach", ja: "背後から{Melee}：不意討ち", en: "From behind, {Melee}: takedown", x_shown: "Behind an unaware guard"}
  - {id: ui.ch03.mineuchi, beat: ch03.b03, ja: "首輪の者には峰打ちになる", en: "Strikes on the collared use the blade's back", x_shown: "Aiming at a conscript"}
  - {id: ui.ch03.sealcut, beat: ch03.b03, "on": "conscript_downed", ja: "倒れた者のそばで{Interact}長押し：首輪を切る", en: "Hold {Interact} beside the downed: cut the collar", x_shown: "Downed conscript, 8 s window"}
  - {id: ui.ch03.carry, beat: ch03.b05, "on": "event:first_pickup", ja: "運搬中：刀は片手、弓は使えない", en: "Carrying: katana one-handed, no bow", x_shown: "First pickup"}
  - {id: ui.ch03.signal, beat: ch03.b07, ja: "同行者はあなたがそばにいる間だけ進む", en: "The escort moves on only while you stay close", x_shown: "b07 start"}
  - {id: ui.ch03.revive, beat: ch03.b07, "on": "npc_downed:any", ja: "{Interact}長押し：助け起こす", en: "Hold {Interact}: help them up", x_shown: "Escort downed"}
  - {id: ui.ch03.bend, beat: ch03.b09, ja: "緑の間で離す", en: "Release in the green", x_shown: "First bend"}
  - {id: ui.ch03.grenade, beat: ch03.b09, "on": "equip:7", ja: "擲弾筒：弧を描いて飛ぶ。近いと自分も巻き込む", en: "Grenade Launcher: arcing shells. Close blasts hurt you too", x_shown: "Unlock"}
  - {id: ui.ch03.glint, beat: ch03.b10, "on": "pattern:marksman_lock:first", ja: "光が見えたら狙われている", en: "A glint means you are targeted", x_shown: "First marksman lock"}
  - {id: ui.ch03.dobuita, beat: ch03.b10, "on": "volume_enter:vol_b10_dobuita", ja: "溝板は端を歩けば鳴らない", en: "Walk the drain boards' edges to stay silent", x_shown: "On vol_b10_dobuita_*"}
  - {id: ui.ch03.fuse, beat: ch03.b10, "on": "interact:obj_light_fuse", ja: "導火二十秒。離れよ", en: "Fuse: 20 s. Get clear", x_shown: "On lighting the fuse"}
  - {id: ui.ch03.fire, beat: ch03.b14, "on": "fire_out:first", ja: "消えた竈は{Interact}長押しで点け直す", en: "Hold {Interact} to relight a cook-fire", x_shown: "First guttered fire"}
  - {id: ui.ch03.supply, beat: ch03.b14, "on": "volume_enter:vol_b14_supply", ja: "補給所：持ち物を替えられる", en: "Supply point: change your loadout", x_shown: "On vol_b14_supply"}
  - {id: ui.ch03.rope, beat: ch03.b17, ja: "綱を斬る：網を落とす", en: "Cut the rope: drop the net", x_shown: "稽古 (Easy) only, first time in the drop zone"}
  - {id: ui.ch03.vents, beat: ch03.b17, ja: "背の排気口が弱点", en: "The rear vents are the weak point", x_shown: "稽古 (Easy) only, after 4 blocked hits"}
```
