# 第二章 異星からの侵略: The Invasion (`ch02_invasion`)

> **Monetary boundary (bible §2).** In this chapter, as in the whole campaign, SORA XOR (and the registry that leads to it) is a production-only storytelling premise. XOR is cut only against finished, inspected goods, is never shown as a balance or converted, and has no link to multiplayer XOR bonds, NFTs, wallets or IrohaConnect. It makes no claim about real-world money, investment or policy, and it does not describe the real SORA network or the design in the SORA Nexus article. **Review note (C1 lead, 2026-09-25):** names, calendar, speaker ids, Japanese punctuation and YAML field names in this file follow bible §9.1, §12.5 and §18.

**Status:** production design and script for chapter 2, written against the [story bible](story-bible.md) (§9, §10, §13 ch02, §14, §15.2, §16, §17, §20). Nothing here is implemented. Every number is a **proposal** for its owning lane to ratify: L1 for beats, layouts, saves and dialogue data; L2 for enemies; L3 for `boss_dunark`; L4 for prompts and HUD; L5 for music and barks; C2/C3 for spaces; C4 for the mission; C9 for cinematics. Fields that bible §12 does not define yet are prefixed `x_` in the YAML (§8; bible §12.5). Still pending: native Japanese review (B7) of every line and reading, and historian and practitioner review (§5). Plain § numbers refer to sections of this document; "bible §" refers to the story bible.

**Chapter at a glance**

| Item | Value |
|---|---|
| Chapter id / map | `ch02_invasion` / Arena 0 (Nyaagyu Estate), night and fire lighting variant, plus four new spaces |
| Target play time | **45 min (2 700 target-seconds)**: 16 beats. By category: C 17 · E 2 · S 0 · P 9 · M 9.5 · Cin 7.5 min, which matches the bible's §10 row exactly |
| Time in fiction | Late spring (元和九年三月下旬; bible §9.1), the same night as ch01.b13: dusk → night → grey pre-dawn → dawn |
| Weapons | Start mask {0 katana, 18 yumi}; **unlocks 19 su-yari** (ch02.b03); end mask {0, 18, 19} |
| New mechanics (flags) | `yari` (b03), `carry` (b05), `mounted_archery` (b08) |
| New mechanics (no flag) | Shield-edge thrust; seal pry; defending and treating horses; escorting a pack-horse string; cutting seizure nets from the saddle; gait and wind management; spook and fear; reading a rhythm boss; stepping past a thrust with 転 |
| Boss | `boss_dunark`, Landing Commander Dunark, a metronomic fencer (b15, 6 min, checkpoint at each phase) |
| Horse | Yes: b07 (mount), b08 convoy escort (6 min), b10 dawn ride (2 min), b13 ridge-road gallop (1.5 min) |
| Production sites | site 0 → b05 蔵の債務封印 · site 1 → b11 食糧の配給所 · site 2 → b16 屋敷の工房 (relocated to the valley). Order and mapping match bible §20 |
| Registry page | 種籾 4俵 (seed rice, 4 bales) · 食糧 36食 (food, 36 meals) |
| Voice | **112 voiced lines**: 95 character lines (matching the bible §10 budget of 95) plus 17 reusable enemy/system barks, recorded once and reused by later chapters. Also 15 UI tutorial prompts (not voiced). About 7 min of VO audio |
| Collectibles | 6 (chapter-local mask bits 0–5; global 6–11): scroll fragment ×1, seizure notice ×2, heirloom ×1, League mark ×1, registry page ×1 |
| Humor | **None by design.** Act I is loss, and none of the nine approved humor beats (bible §1.2) falls in ch02 |

---

## 1. Synopsis, cast and loadout

### 1.1 Synopsis

Dusk. The sky over Nyaagyu has split (ch01.b13). Kohagi, a calico peddler who carries messages for the house, runs in through the gate: three ships are descending, and cyan locks are clamping onto every granary. Over the estate, a polite, flat voice proclaims that the valley now belongs to the Stellar Credit House, that its granaries, fields and workshops are collateral, and that resistance will be booked as delinquency. Sekireisai orders the gate closed.

Nyaakoto, armored in haste, holds the 長屋門 gate yard with the pupils Matsukichi, Takemaru and Baiō against the first enforcers. When shield-bearers break into the armory yard, he takes a su-yari from his master's racks: 「先生、一本お借りします。」 Sekireisai gives the order that defines the chapter: 「種は明日の田じゃ。」 Take the seed rice to the Hidden Valley. The old master stays, because people are still inside the dojo.

Nyaakoto pries the debt seal off the seed granary with the spear's iron butt. Under fire he shoulders four bales onto two pack horses (one 駄 of two bales each), then holds the kura front while drop pods fall into the courtyard. At the back gate the groom climbs onto the lead horse's load, and Nyaakoto mounts Kurimaru: 「誰も置いていかない。」

On the forest highway he escorts the tied string of pack horses, shooting Inventory drones from the saddle. From horseback the bow can only shoot to the left, so the road's geometry keeps the threats there. He cuts seizure nets from the loads with right-side katana strokes and calms Kurimaru when searchlights sweep the road. At the Stone Bridge, the Credit House has built a checkpoint. Nyaakoto flanks it through the ford and silences the marksman on the outcrop.

In the grey before dawn the convoy reaches the Hidden Valley, and Nyaakoto hands out rice to three families of charcoal-burners and refugees. A child asks whether the rice is a loan. 「借りではない。田で育ったものだ。」

Kohagi returns: the estate is burning, Sekireisai is still there, and blue light is gathering over the dojo. She knows a ridge road that is half the distance. Nyaakoto gallops back under an ember-lit sky. In the burning wings he may free Takemaru from under a fallen beam and learn the truth: Sekireisai laid down his sword so that the people inside could go free. In the courtyard, Landing Commander Dunark waits beside the old man, who kneels inside a cyan seizure field. Dunark fences in fixed three-beat "notices." Nyaakoto kills him by learning to read the rhythm rather than ride it, and cuts his ledger plate through.

It is too late. High Collector Val Amort descends inside a lift beam, writes Dunark off as a loss and takes Sekireisai as collateral. Before he goes, the master asks only one thing: 「種は、届いたか。」 「……届きました。」 「ならば、よい。」

At dawn in the valley, Tetsugorō sets down the bellows and anvil the craftspeople carried out: 「道具さえありゃ、どこでも鍛冶場や。」 Nyaakoto counts what is left to protect. Toranosuke ran for his own house at the first bell and has not been seen since. The chapter ends on a vow: 「取り返す。」

### 1.2 Cast in this chapter

| Speaker id | JA label | EN label | Status | Role in ch02 and register |
|---|---|---|---|---|
| `mentor` | 師範 石鈴斎 | Sekireisai | existing | Holds the estate, trades himself for the people in the dojo, taken as collateral (b16). Archaic わし / じゃ |
| `samurai` | ニャーコト | Nyaakoto | existing | Protagonist; first armored look. Few words; 拙者 / 私 / plain だ by listener |
| `scout` | 小萩 | Kohagi | existing | Peddler-runner for the house; brings the alarm (b01) and the news (b12). Terse あたし, counts and directions |
| `banker` | 大徴収官 ヴァル・アモルト | High Collector Val Amort | existing | Proclamation (b01, voice only); descends in person in b16. Hyper-polite keigo plus finance terms |
| `gunsmith` | 鉄砲鍛冶 鉄五郎 | Tetsugorō the gunsmith | bible | The dojo smith from ch01.b09; carries the smithy's bellows and anvil to the valley (b16). Blunt, Kamigata-leaning |
| `boss_dunark` | 上陸指揮官 ドゥナーク | Landing Commander Dunark | bible | Boss (b15). Procedural keigo; notices counted like a ledger |
| `pupil_matsukichi` | 門弟 松吉 | Matsukichi | proposed | Downable ally at the gate (b02). Earnest young samurai |
| `pupil_takemaru` | 門弟 竹丸 | Takemaru | proposed | Straps on Nyaakoto's armor (b01); stays with the master; pinned in the fire (b14). Youngest, impulsive |
| `pupil_baio` | 門弟 梅翁 | Baiō | proposed | Oldest pupil; braces the gate bar (b02), leads the families out, keeps the count (b16). Calm わし / じゃ |
| `groom` | 馬子 | Groom | proposed | Rides the lead pack horse 乗掛 (b05–b11). Warm Kamigata commoner |
| `villager` | 村人 | Villager | shared generic (ch04, ch08) | Refugee mother (b11); voice variant: woman |
| `child` | 子ども | Child | shared generic (ch03, ch08) | Asks whether the rice is a loan (b11) |
| `credit_system` | 信用院・告知音声 | Credit House notice voice | proposed here; used by ch03 | Seals, drop pods, searchlight and ship broadcasts. Flat notice voice |
| `enforcer` | 執行局の兵 | Enforcement Office trooper | shared generic (ch03–ch08) | Base bark set for the Enforcement Office troops, one voice variant per enemy type (rifle, blade retainer, shield, grenadier, marksman). Reused campaign-wide; the marksman's lock bark is a captioned telegraph |
| `drone` | 目録 | Inventory drone | shared generic (ch03–ch08) | Inventory drone announcements |

- **First appearances proposed here:** Kohagi and the Credit House notice voice (`credit_system`, which ch03 already reuses). Tetsugorō is already known from the ch01.b09 dojo smithy; in b16 he carries that smithy's bellows and anvil to the valley, which is where ch04 finds him.
- **Speaker ids** follow the generic ids the other chapter docs share (`enforcer`, `drone`, `villager`, `child`). Enemy barks carry a `voice_variant` (rifle, blade retainer, shield, grenadier, marksman) for casting and for L2's per-type bark pools.
- **Toranosuke is absent on purpose.** He is only mentioned (b16), which sets up his ch03 reveal.
- **Silent roles:**
  - Kurimaru (chestnut mare) and three pack horses.
  - About 26 refugees in the valley: 19 women and children and 7 elders, counted in b16.
- **Pupil speaker ids** (`pupil_matsukichi`, `pupil_takemaru`, `pupil_baio`) match the ids in ch01's doc.

### 1.3 Loadout

| Slot (bible §11) | ch02 contents |
|---|---|
| 腰 Hip | Katana (0), always |
| 脇 Side | Empty. The wakizashi is worn as part of the daishō (visual only) and becomes a selectable weapon at ch03.b01 per bible §11 |
| 背 Back | Yumi (18) + 12-arrow ebira. Refills: armory yard (b03), the lead pack horse's spare ebira of 24 arrows (b08), the Stone Bridge (after b09), a cache in the burning wings (b14) |
| 長柄 Polearm | Su-yari (19) from ch02.b03 |
| 飛道具 Firearm | Empty (no firearm unlocks yet) |
| Mounted (b08) | Katana: right-side cuts, arc +30°…+150°. Yari: forward and right thrust, −10°…+60°. Yumi: left only, −170°…+15°. No firearms (bible §4.2, §11) |

---

## 2. Locations

**Coordinate convention.**

- Estate positions are Arena 0 world coordinates as built by `SoraWorldBuilder.cpp`, written in metres: X runs along the central road and Y across it.
- For readability this document calls −X **west** (the main gate side), +X **east** (the back gate), +Y **north** and −Y **south**. This is a naming convention only.
- New spaces use local metres from a stated origin.
- The YAML (§8) repeats every volume and spawn in centimetres.

### 2.1 `pl_estate_night`: Nyaagyu Estate at night (Arena 0, fire variant)

**Footprint and landmarks.** These already exist in the arena and must not move.

- **Walled compound:** 64 × 52 m. The 土塀 runs at X ±31.5 and Y ±25.5, built from the existing `SM_Nyaagyu_EstateWall_4m` modules.
- **Central stone route:** about 56 × 6.6 m along the X axis (existing mesh-terrain stone path).
- **Two building rows** at Y ±18: five buildings each, at X −20, −10, 0, +10, +20. Each footprint is 6.5 × 7 m and keeps its existing collision.
  - The four at X ±10 are the provision kura (`SM_Nyaagyu_ProvisionKura`, which carries the house mon).
  - The six others use the dojo-hall mesh.
- **Twelve cover stacks** (2.3 × 1.8 × 1.4 m, visual `SM_Nyaagyu_CargoStack` with the SORA crate stamp) at X −23, −14, −5, +4, +13, +22, alternating Y ±6.8 and ±8.8.
- **Two lacquered gate frames** (`SM_Nyaagyu_ToriiGate`, with the SORA mon on the lintel) on the road at X −22.5 and X +23. See the §5.4 note on their form.
- **Pines** along both long edges (Y ≈ ±22).
- **The prototype's three production nodes** (−12.5, −7), (0, +10) and (+12.5, −8) are **not spawned** in ch02. Here the sites are driven by beats (bible §12.1 `site`).

**What each building is in fiction.** The collision stand-ins stay the same; campaign dressing (non-colliding noren, fire damage, props) tells them apart.

| Row | X −20 | X −10 | X 0 | X +10 | X +20 |
|---|---|---|---|---|---|
| North (Y +18) | 母屋 main house (the first roof alight, b05) | 米蔵 rice kura (sealed) | **爪木坂道場 Tsumagizaka Dōjō** exterior; Sekireisai's seizure field on its steps in b15 | 米蔵 rice kura (sealed) | 客殿 guest hall (burns) |
| South (Y −18) | 家臣長屋 retainers' quarters | **種籾蔵 seed granary** (sealed; b05) | 厩 stable exterior (Kurimaru is led out in b07; the `pl_umaya` interior is not entered) | 雑穀蔵 grain kura (sealed); the 馬繋ぎ tie rail stands in front | 台所 kitchen and 土間 |

**Campaign-only additions.** These load in campaign mode only. Practice and multiplayer keep the closed walls and the kernel collision unchanged (bible §14). They are C2 and C3 work.

| Addition | Where | Notes |
|---|---|---|
| 長屋門 main gate | Outside the west wall, X −37…−32, Y −10…+10; gate passage Y −1.8…+1.8 | A 20 × 5 m gatehouse with retainers' rooms either side and a roof ridge at about 6 m. Its leaves are barred with a 閂 until wave 3 of b02 |
| 潜り戸 wicket | West wall, Y −5…−4 | A 1 m door, breached in b02 wave 2 |
| 埋門 wicket to the armory yard | North wall at X −10 | Reached through the 3.5 m gap between the X −20 and X −10 buildings, then the 3.5 m strip behind the north row |
| 裏門 back gate | East wall, Y −1.8…+1.8 | Used only in cinematics (b07) and at the b13 arrival |
| 茶室 tea hut | Northeast corner, centred (+27.5, +19); 2.7 × 2.7 m (four-and-a-half mats) | Has a 躙口 (crawl-in entrance) and a 炉 (hearth). Holds the heirloom collectible |
| Gate-yard set dressing | Around (−26, 0) | 2 竹束 bamboo-bundle mantlets, an overturned 長持 chest and 4 篝火 iron braziers |
| Fire dressing | North row roofs from b05; the whole north row is alight by b14 | Burning roof sections, embers and smoke. **Non-colliding.** Damage comes only from authored fire volumes |
| Alien dressing | Every kura door; the courtyard | Seal clamps on every kura door; drop-pod scars and landed pods (b06 onward) |

**Zones, routes and sightlines by beat**

- **b02, the gate yard** (`vol_gate_yard`: X −31.5…−18, Y −13…+13).
  - It is 13.5 m deep, between the gate and the west gate frame. The two stone cover stacks at (−23, ±6.8) are the only hard cover. The 竹束 mantlets at (−27, ±3) stop rifle fire but not blades.
  - **Sightlines:**
    - The nagayamon roof ridge (6 m up, 8–12 m from the yard centre) overlooks the whole yard. That is why wave 1 is a bow problem.
    - The wicket at Y −4.5 is a 1 m choke that faces the right-hand stone stack.
    - The gate leaves open straight down the road axis.
  - **Allies:**
    - Matsukichi holds the wicket side (−27, −4.5).
    - Takemaru holds the north side (−27, +4.5).
    - Baiō braces the bar at (−30.5, 0) and is not downable.
- **b04, the courtyard west end** (`vol_courtyard_west`: X −22…−10, Y −5…+5). Sekireisai waits here, beside the west gate frame.
- **b05–b06, the kura-front lane** (`vol_kura_front`: X −16…+16, Y −15…−8).
  - It runs 5 m wide between the south cover stacks and the south building fronts.
  - **Carry route:** from the seed-granary door (−10, −14.2) east to the tie rail at (+10, −10.5), about 20 m each way.
  - **Cover along the lane:** the stacks at (−14, −8.8), (−5, −6.8) and (+4, −8.8).
  - **Pressure:**
    - Rifles on the north verandas (±5, +13.5) fire across the road, which is 22–26 m away.
    - Wave 2 comes down the road from the west gate frame.
  - **Drop pods (b06)** land at (−2, +2) on the road, at (−6, +11) north, and at (−19, −3) west. The last one forces a fight on the carry lane's west end.
- **b14, the burning wings** (`vol_burning_wings`: the north half, Y +10…+25, excluding building footprints).
  - **Route:** along the verandas, through the gaps between buildings, and along the strip behind the north row to the tea hut in the northeast corner.
  - **Takemaru** is pinned under the fallen 庇 (eave section) of the dojo's east veranda at (+5.2, +17.5).
  - **Fire volumes** (8 dmg/s) block the gap between the dojo and the X −10 kura from the moment b14 starts. The route stays readable because the flames are real geometry and particles with an animated amber edge decal on the damage boundary.
- **b15, the boss courtyard** (`vol_boss_courtyard`: X −12…+14, Y −11…+11; locks on entry).
  - It is 26 × 22 m, centred on the road between the gate frames.
  - The six cover stacks at X −5, +4 and +13 (both sides) stay in the arena and give the P3 arrow game its angles.
  - **Sekireisai's seizure field** is a colliding cyan cylinder, 3 m in diameter, at (0, +13) on the dojo steps, 2 m outside the arena lock. He watches the whole fight.
  - **Phase 2:** a burning beam falls (1.5 s creak-and-dust telegraph) into the northwest quarter (`vol_fire_nw_p2`: X −12…−6, Y +5…+11). This shrinks the usable ring to about 20 × 22 m and pushes the duel toward the road.
- **Spawn and entry/exit:**
  - b02 starts at `ps_gate_yard_start` (−23, 0), facing the gate.
  - The armory yard is entered and left through the 埋門.
  - The chapter leaves the estate by cinematic at the back gate (b07) and re-enters there at the end of b13.
  - b15 is triggered on entering `vol_boss_courtyard` from any side.

**Time of day, weather, lighting**

- **b01–b07:** dusk → night.
  - Clear sky with thin high cloud; a waxing gibbous moon in the southeast (fill about 4 100 K).
  - Key light comes from the gate braziers and, from b05, the fires (1 800–2 200 K with flicker).
  - Cold contrast:
    - The underglow of the three ships at 150–300 m altitude.
    - Cyan seal clamps at 7 000–9 000 K, casting cold light on the kura plaster.
    - Searchlights at 8 500 K sweeping through the smoke (bible §16).
  - A light west wind carries smoke eastward across the back gate, which motivates the b07 exit.
- **b14–b15:** blue hour before dawn (sky about 10 000 K, low).
  - The north row is fully alight and is the key light from the north.
  - The seizure field is a cold rim light on Sekireisai. Falling embers and volumetric smoke are lit from below.
- **Mac fallback:** no more than 8 shadow-casting lights per view. Use the braziers or the two nearest fire clusters as the shadowed lights; the rest of the fire is emissive smoke cards plus unshadowed point lights. Cap ember particle counts. Seals are emissive only.

### 2.2 `pl_bugugura`: armory yard (estate sublevel)

- **Origin:** the 埋門 wicket centre at arena (−10, +25.5); same axes. The yard is 18 × 14 m (X −9…+9, Y 0…14) and walled with a 2.4 m 土塀.
- **Landmarks:**
  - The 武具蔵 armory storehouse (8 × 5 m) closes the north end. Its 下屋 lean-to eave shelters the empty armor stands.
  - A 槍掛け rack of 12 upright su-yari stands on the wall at (−2.5, +0.6), right beside the wicket. That is the pickup, so the unlock happens at beat start (bible §11).
  - A landed drop pod (2.4 m tall, hatch open, cyan underglow) sits in a crater at (−3, +6.5). The shield enforcers come out of it.
  - A section of the west wall has collapsed at (−9, +7), which is the rifles' breach.
- **Cover:**
  - The well curb at (+4.5, +5): low, 0.8 m.
  - A woodpile at (+6.5, +10): 3 × 1 × 1.6 m.
  - Two 鎧櫃 armor chests at (−6, +3.5): low.
  - A rack of 竹束 against the storehouse at (+2, +12.5).
  - The pod itself.
- **Sightlines:**
  - The breach sees the whole yard diagonally (about 15 m). The rack at the wicket is covered from the breach only past the pod.
  - Shield enforcers advance from the crater toward the wicket and pin the player against the wall unless the player keeps yari distance.
- **Lighting:** the pod's cyan hatch glow, a burning torch rack by the storehouse (1 900 K) and the moon. On Mac, 3 shadowed lights.
- **Volumes:** `vol_bugugura_yard` (bounds), `vol_spear_rack` (pickup interact).

### 2.3 `pl_kaido`: Nyaagyu Highway and the ridge road (new linear level)

- **Size:** about 1.5 km of mountain road plus a 750 m ridge-road (尾根道) branch. Chainage is measured in metres from the estate back gate. Outbound (toward the valley), the slope rises on the **right** through cedar and cypress, and falls away on the **left** into a ravine with a stream. This geometry keeps most threats in the mounted bow arc (bible §4.2).
- **Road:**
  - 2 間 (3.6 m) wide.
  - Packed earth and gravel, with stone paving only where the grade exceeds about 8% and inside the cutting (see §5.4 on paving).
  - Grass verges of 1–2 m.

| Chainage | Landmark | Gameplay (b08 outbound unless noted) |
|---|---|---|
| 0 m | Back gate 裏門, cedar avenue | Convoy forms. The player starts on the convoy's left (ravine) flank |
| 120–260 m | Cedar avenue; ravine opens on the left | Drone group G1 (2): tutorial targets on the left at 35 m, 12 m up. They scout and drop no nets |
| 150 m | Roadside group of three 石仏 Jizō under a small 覆屋 roof, with moss and offerings | Landmark |
| 300 m | 切通し cutting, 4 m mossy walls, paved | Walls block the drones' line of sight briefly |
| 400–550 m | Ravine bend: the road curves right around the spur and the stream is 25 m below on the left | G2 (3) rises out of the ravine on the left; 2 of them try nets on the loads |
| 600 m | Spur crest vista: the burning estate is visible back-left | Camera `soft_lookat` for 2 s. The convoy does not stop |
| 640–800 m | Sparse pine stand | G3 (2) plus a landing ship's **searchlight sweep** from 400 m left and 150 m up. Its footprint (about 9 m) spooks horses |
| 750 m | A pair of 石灯籠 votive lanterns and a small 丹塗 shrine torii on the right, at the 鎮守 path | Landmark (a real shrine torii, in contrast with the estate gate note in §5.4) |
| 900–1 100 m | Straight along the hillside; wooden 道しるべ signpost at the 追分 fork (1 000 m) | G4 (3). One drone **crosses to the right** at 1 020 m and must be brought back into the left arc by dropping back and crossing behind the string |
| 1 140–1 160 m | The bend before the bridge, hidden from the checkpoint by the spur | `vol_bridge_bend`: the convoy halts and b08 completes |
| 1 215–1 500 m | Beyond the bridge; Jizō group at 1 500 m; valley turnoff | b10 dawn ride (walk and trot), then a 180 m valley trail to `vol_kakuredani_mouth` |
| Ridge road, 0–750 m | From the valley's ridge trailhead, over a saddle, down to the back gate | b13 return. At 410–440 m a 30 m 桟道 plank walkway on brackets across a gully (forced walk). At 500 m, a vista of the burning estate under a glowing cloud base |

- **Lighting:**
  - **b08:** moonlight through the canopy in shafts, low mist in the ravine, the drones' cyan eyes, and the searchlight at 8 500 K. The estate's fire glow shows as a warm horizon at the vista.
  - **b10:** 払暁, grey-blue before dawn (about 10 000 K, low contrast), valley mist and the first birds.
  - **b13:** the ember-lit sky, with fire glow at about 1 800 K on the underside of low cloud over a blue pre-dawn.
  - **Mac:** no volumetric canopy shafts (use light-function cards instead), foliage density ×0.6, card cedar LODs beyond 40 m.

### 2.4 `pl_ishibashi`: Stone Bridge Checkpoint (new)

- **Origin:** the bridge's west abutment. +X runs east along the road and +Y upstream (north). The play space is 120 × 80 m.
- **Bridge and stream:**
  - A granite **slab-beam bridge** (石桁橋, not an arch; see §5.4), 14.4 m in 4 spans on 3 stone piers, 2.7 m wide.
  - The deck is 1.5 m above the water, with 20 cm curb stones and no parapet.
  - The stream is rocky and 14 m wide at the bridge.
- **Near (west) bank:**
  - A clearing (X −30…0, Y −12…+12) with cedar trunks as cover, a woodpile and a knee-high dry-stone wall along the road.
  - The player starts at `ps_near_bank_start` (−40, 0).
  - Kurimaru and the string wait at the bend 60 m west, out of sight.
- **Far (east) bank, the alien checkpoint** (the contrast is the point):
  - **Barriers:** six graphite barriers (1.1 m tall, 3 m long) in a chevron at X 18–24, Y −9…+9.
  - **Scanning gate:** two 4 m posts with a cyan scan plane at the bridge's east end (X 16). It is harmless and only plays a scan sound.
  - **Landed drop pod:** at (26, +5).
  - **Marksman's platform:** a 4 × 4 m pod platform on a **granite outcrop 6 m high** at (22, −20). It covers the bridge deck at about 25 m and the near-bank clearing at about 42 m.
- **Flank:**
  - A **ford** 45 m downstream (Y −45) crosses a 20 m gravel bar and knee-deep water: movement ×0.7 and loud splashes.
  - Willows and the outcrop's south shoulder hide the ford from the platform.
  - From the east side of the ford, a stream-side path runs under the outcrop to a scramble route onto the platform, where the marksman can be taken in melee. From there the player drops to the checkpoint's rear (`vol_checkpoint_rear`).
- **Sightlines:**
  - Crossing the bridge head-on meets the enforcers at the barriers (a 16–24 m choke), the grenadier's arcs and the marksman's lock.
  - A bow duel across the stream is viable at 30–35 m.
  - The ford route is the designed solution.
- **Volumes:**
  - `vol_ishibashi` (bounds)
  - `vol_ford` (move ×0.7, `running_water`)
  - `vol_outcrop_top`
  - `vol_bridge_deck`
  - `vol_checkpoint_rear`
- **Lighting:**
  - Alien floodlights (8 500 K) wash the checkpoint.
  - The near bank is dark under the moon, with mist over the water.
  - The pod glows cyan and the barriers carry thin emissive ledger lines.
  - Mac: the floodlights are the 2 shadowed lights and the rest is emissive.

### 2.5 `pl_kakuredani`: Hidden Valley (new hub; revisited in ch07 and ch08)

- **Origin:** the log bridge at the valley mouth; +Y runs up-valley.
- **Size:** 220 m long, with a floor 40–70 m wide between steep cedar and broadleaf slopes. The stream runs along the east side and a 12 m waterfall closes the head of the valley (Y +220).
- **Entry:**
  - A gorge path 2.5 m wide beside the stream (Y 0–30) and a 丸木橋 log bridge 6 m long.
  - A boulder at the mouth carries **the first charcoal SORA mark** (collectible c05).
- **The clearing** (40 × 30 m, centred at Y +90) is where the League camp will later grow. The pack horses unload at (0, +85).
- **Three 炭焼き小屋 charcoal-burners' huts** serve as the family shelters:
  - shelter 1 at (−18, +108), about 29 m from the horses
  - shelter 2 at (+14, +129), about 46 m
  - shelter 3 at (+5, +159), about 74 m, on the terrace below the plunge-pool path
- **Other landmarks:**
  - A warm 炭窯 kiln mound, 3 m across, at (−9, +120).
  - The b16 workshop lean-to (差し掛け小屋) goes up beside the kiln at (−5, +115). That is site 2.
  - The ridge trailhead (b13 start) is at (−25, +60) and climbs west.
- **Sightline:** a bend in the gorge hides the valley from the highway. The only view out is from a rock shoulder above the trailhead.
- **Volumes:** `vol_kakuredani_mouth`, `vol_clearing`, `vol_kohagi_arrives` (armed after site 1 is restored), `vol_ridge_trailhead`.
- **Lighting:**
  - **b11–b12:** first light, with valley mist, waterfall spray and warm hut fires (2 000 K).
  - **b16 dawn:** a low sun at about 3 200 K through the mist, with god rays down the valley axis.
  - Mac: height fog only; god rays via light shafts.

### 2.6 Lighting and weather by beat (summary)

| Beat | Sky / key | Weather and FX | Mac fallback |
|---|---|---|---|
| b01 | Dusk afterglow → cyan descent; ship underglow | Clear; the first seal clamps glow; 半鐘 bell and 法螺貝 conch | Emissive ship hulls, 4 shadowed lights |
| b02–b03 | Night: moon 4 100 K, braziers 1 900 K, pod cyan | Smoke begins; a searchlight passes overhead | Braziers are the shadowed lights |
| b04–b06 | Night: first fires in the north row (1 800–2 200 K flicker) | Embers, smoke drifting east, drop-pod trails | Emissive smoke cards |
| b07–b09 | Night forest: moon shafts, drone eyes, searchlight 8 500 K, checkpoint floods | Ravine mist, stream mist | Light-function shafts; floods only shadowed |
| b10–b12 | Grey pre-dawn → first light (about 10 000 K ambient) | Valley mist, birdsong, hut smoke | Height fog only |
| b13 | Ember-lit cloud base over a blue pre-dawn | Wind in the pines | Emissive cloud-underside card |
| b14–b15 | Blue hour + full fire key + cyan field | Falling embers, heavy smoke lit from below | Two fire clusters shadowed; flash-reduction limits the beam-fall flare |
| b16 | Lift beam (cyan column) → dawn sun 3 200 K in the valley | Morning mist, god rays | Light shafts; no volumetric beam |

---

## 3. Beats

**Pacing check:** the beats sum to **2 700 s** (45.0 min, exactly the bible §10 target). By category: C 17.0, E 2.0, S 0, P 9.0, M 9.5, Cin 7.5 min, which matches bible §10 row 2. All beats save a checkpoint at their start except the dialogue and cinematic beats b04, b07 and b12. The largest gap between checkpoints is **360 target-seconds** (b08, b15 and b09→b11), exactly the bible §12.3 rule-8 limit. On 稽古 and 真剣, b15 also saves at each phase.

| # | Beat | Type | Place | Title (JA / EN) | Min | Checkpoint | Site | Unlocks |
|---|---|---|---|---|---|---|---|---|
| 1 | ch02.b01 | cinematic | pl_estate_night | 空が裂けた夜 / The Night the Sky Split | 2.0 | yes | — | — |
| 2 | ch02.b02 | combat_wave | pl_estate_night | 長屋門を守れ / Hold the Nagaya Gate | 4.0 | yes | — | — |
| 3 | ch02.b03 | combat_wave | pl_bugugura | 武具蔵の槍 / Spears from the Armory | 3.0 | yes | — | weapon 19; `yari` |
| 4 | ch02.b04 | dialogue (blocking) | pl_estate_night | 種は明日の田 / Seed Is Tomorrow's Field | 1.0 | no | — | — |
| 5 | ch02.b05 | production_task · carry | pl_estate_night | 種籾を運び出せ / Carry Out the Seed Rice | 4.0 | yes | **0** | `carry` |
| 6 | ch02.b06 | production_task · defend | pl_estate_night | 荷馬を守れ / Protect the Pack Horses | 3.0 | yes | — | — |
| 7 | ch02.b07 | cinematic | pl_estate_night | 裏門 / The Back Gate | 1.0 | no | — | — |
| 8 | ch02.b08 | horseback_ride · escort_convoy | pl_kaido | 荷駄を守って街道を行け / Escort the Pack Train | 6.0 | yes | — | `mounted_archery` |
| 9 | ch02.b09 | combat_wave | pl_ishibashi | 石橋の関を破れ / Break the Stone Bridge Checkpoint | 4.0 | yes | — | — |
| 10 | ch02.b10 | horseback_ride · travel | pl_kaido | 夜明け前の道 / The Road Before Dawn | 2.0 | yes | — | — |
| 11 | ch02.b11 | production_task · carry | pl_kakuredani | 米を配れ / Hand Out the Rice | 2.0 | yes | **1** | — |
| 12 | ch02.b12 | dialogue (blocking) | pl_kakuredani | 屋敷が燃えている / The Estate Is Burning | 1.0 | no | — | — |
| 13 | ch02.b13 | horseback_ride · travel | pl_kaido (ridge road) | 尾根道を駆け戻れ / Ride Back by the Ridge Road | 1.5 | yes | — | — |
| 14 | ch02.b14 | explore_optional | pl_estate_night | 燃える屋敷 / The Burning Wings | 2.0 | yes | — | — |
| 15 | ch02.b15 | boss | pl_estate_night | 上陸指揮官ドゥナークを討て / Defeat Landing Commander Dunark | 6.0 | yes + each phase | — | — |
| 16 | ch02.b16 | cinematic | pl_estate_night → pl_kakuredani | 担保 / Collateral | 2.5 | yes | **2** | — |

**Enemy count for the chapter:**

| Enemy | b02 | b03 | b05 | b06 | b08 | b09 | Total |
|---|---|---|---|---|---|---|---|
| `enforcer_rifle` | 6 | 3 | 3 | 7 | — | 6 | 25 |
| `blade_retainer` | 2 | — | 1 | 1 | — | — | 4 |
| `shield_enforcer` | — | 2 | — | — | — | — | 2 |
| `grenadier` | — | — | — | 1 | — | 1 | 2 |
| `marksman` | — | — | — | — | — | 1 | 1 |
| `drone` | — | — | — | — | 10 | — | 10 |

- b15 adds `boss_dunark` and 1 shield drone.
- There are no `bound_conscript`s; they first appear in ch03.
- The prototype catalog's `kills: 7` and `requires_kills` gates for chapter 2 are replaced by these beats.

### 3.1 Beat details

#### ch02.b01 · cinematic · 空が裂けた夜 / The Night the Sky Split: 2.0 min, checkpoint (chapter start)

- **Sequence:** `LS_ch02_b01_Descent`, 120 s, skippable; `fallback: camera_blend` until C9 lands.
- **Shots:**
  1. It continues from ch01.b13. The 半鐘 bell is ringing and the conch 法螺貝 sounds from the gate.
  2. Kohagi runs through the gate (catalog line 1).
  3. Three ships settle at 150–300 m, and seal clamps slam onto all four kura doors. Each is a cyan ring of tally notches (the alien ledger sigil, never the SORA mon) clamping over the kura's SORA plaque.
  4. The proclamation plays over the valley as Takemaru straps Nyaakoto's 胴 and 籠手: 紺糸威 lacing and 朱漆 plates, and a 鉢金 in place of a kabuto (§5.6).
  5. Sekireisai: 「門を閉めよ。」
- **End state:** player at `ps_gate_yard_start`, katana drawn, yumi on the back.
- **Dialogue:** 8 lines (b01 table), including canon catalog line 1.

#### ch02.b02 · combat_wave · 長屋門を守れ / Hold the Nagaya Gate: 4.0 min, checkpoint

- **Objective:** hold the gate yard (`vol_gate_yard`) until all three waves are cleared. `max_alive` 4.
- **Waves:**

| Wave | Trigger | Enemies | Spawn and behavior |
|---|---|---|---|
| 1 | `start` | `enforcer_rifle` ×3 | `sp_nagayamon_roof`: three firing positions on the gatehouse ridge, 6 m up. A bow problem, since the katana cannot reach them |
| 2 | `prev_cleared` | `enforcer_rifle` ×3 | `sp_wicket_breach`: the wicket is blown (amber breach ring, 2 s). They enter one at a time through the 1 m choke |
| 3 | `prev_cleared` | `blade_retainer` ×2 | `sp_gate_leaves`: the bar breaks and the leaves swing in. Melee with the existing 420 ms fixed-direction warning; they withdraw when crowded |

- **Allies:**
  - Matsukichi (wicket side) and Takemaru (north side) are downable. Revive takes a 3.0 s interact (tutorial prompt `tut.001`).
  - Baiō braces the bar and is not downable.
  - Allies never cause a fail. A downed pupil stays down until revived and is revived automatically at beat end.
- **Complete:** `all_waves_cleared`. **Fail:** player death → checkpoint.
- **Dialogue:** beat start (Sekireisai, Nyaakoto); the `alert`, `flank` and `retreat` barks; wave 2 and wave 3 calls; the downed line; on completion, Sekireisai sends him to the armory.

#### ch02.b03 · combat_wave · 武具蔵の槍 / Spears from the Armory: 3.0 min, checkpoint

- **Unlock at start:** weapon **19**, via the pickup `rack_suyari_01` (0.8 s interact) beside the wicket. Mechanic `yari`.
- **Waves:**
  1. `start`: `shield_enforcer` ×2 from `sp_pod_crater`, plus `enforcer_rifle` ×1 from `sp_yard_west_breach`.
  2. `alive_below:2`: `enforcer_rifle` ×2 from `sp_yard_west_breach`.
- **Teaching:** shields block 120° to the front, and the katana cannot get past them.
  - A yari thrust to the **shield rim** (`edge_thrust`) turns the shield and opens the enforcer for 1.0 s (§3.2).
  - Inside about 120 cm the yari does 0.4× damage and never staggers: 「懐に入られたら槍は死ぬ」.
  - The 水月 maai ring shows the yari's ideal band, 242–328 cm (285 cm ±15%).
- **Complete:** `all_waves_cleared`. **Fail:** player death.
- **Arrows:** a bundle by the storehouse refills the ebira to 12.

#### ch02.b04 · dialogue (blocking) · 種は明日の田 / Seed Is Tomorrow's Field: 1.0 min, no checkpoint

- **Walk-up (ambient, player in control):** as the player comes back through the 埋門, Sekireisai calls out (`.001`) and Nyaakoto asks (`.002`).
- **Blocking exchange** (triggered on `vol_courtyard_west`; 5 lines, **17.7 s**, within the 20 s cap; camera `soft_lookat`): 「わしは残る…」 → 「種は明日の田じゃ。刀は、何のためにある。」 → 「……民から、預かるもの。」, a callback to ch01.b12 → 「ならば行け。」
- **On completion (ambient):**
  - Sekireisai takes Takemaru toward the dojo, where people are still inside. This sets up b14 and b15.
  - Baiō leads the servants' families up the woodcutters' path, 杣道. This sets up c05 and the valley count in b16.

#### ch02.b05 · production_task (carry) · 種籾を運び出せ / Carry Out the Seed Rice: 4.0 min, checkpoint, **site 0**

- **Pre-step (the seal pry):** a 3.0 s interact at `seal_kura_sw` on the seed granary door. Nyaakoto levers the clamp off with the yari's 石突 iron butt cap.
  - Progress pauses while the player is hit (`contest: pause`).
  - The notice voice barks on first contact. The seal's ledger numerals flicker and die, and the kura's SORA plaque shows again.
- **Carry:**
  - Item `tanemomi_hyo` (種籾俵), 4 in total, carried one at a time on the shoulder, from `pk_kura_sw_door` to `pack_horse_a` and `pack_horse_b` at the tie rail (2 per horse: one 駄 each).
  - While carrying: katana one-handed, no bow, no sprint, move ×0.8.
  - `drop_on_hit`: off on Easy and Normal, on for Hard.
  - A bale can be set down to fight and picked up again (`tut.006`, `tut.007`).
- **Waves:**
  1. `start`: `enforcer_rifle` ×2 on the north verandas.
  2. `progress_at:0.5`: `enforcer_rifle` ×1 + `blade_retainer` ×1 down the road from the west gate frame.
- **Complete:** 4 bales loaded, which restores site 0 and shows the catalog text 「債務の封印を断ち、蔵を民に開いた。」 **Registry:** 種籾 4俵 / Seed rice, 4 bales. **Unlock:** `carry`.
- **Fail:** player death.

#### ch02.b06 · production_task (defend) · 荷馬を守れ / Protect the Pack Horses: 3.0 min, checkpoint

- **Targets:** `pack_horse_a` and `pack_horse_b`, 400 HP each. **Duration:** 150 s.
- **Treat a horse:** a 2.0 s interact beside it heals 60 HP, with a 20 s cooldown per horse. The groom calms them.
- **Drop-pod waves:**
  - Each pod's amber impact ring (350 cm) appears **2.5 s** before landing. The impact does 60 damage to anything in the ring, allies and horses included, so the rings must be read.
  - `start`: pod A on the road, `enforcer_rifle` ×3.
  - `after_s:45`: pod B to the north, `enforcer_rifle` ×2 + `grenadier` ×1. The grenadier lobs at the horses; each shell's arc decal shows 1.4 s ahead, and it fires every 6 s.
  - `after_s:95`: pod C to the west, `blade_retainer` ×1 + `enforcer_rifle` ×2.
  - `max_alive` 6.
- **Complete:** survive 150 s. The remaining enemies withdraw (retreat bark), and Kohagi calls the back gate clear.
- **Fail:** player death, or either horse reduced to 0 HP → checkpoint.

#### ch02.b07 · cinematic · 裏門 / The Back Gate: 1.0 min, no checkpoint

- **Sequence:** `LS_ch02_b07_BackGate`, 60 s.
- **Content:**
  - Kitchen servants load the third horse (`pack_horse_c`) with three 叺 straw sacks of rice and the dojo's spare ebira: 24 arrows, including the dozen Nyaakoto straightened in ch01.b09.
  - The three pack horses are tied nose to tail. The groom climbs onto the lead horse's load (乗掛).
  - Kurimaru is led out from the stable, saddled with kura, abumi and tazuna.
  - Nyaakoto mounts. He looks back once: Sekireisai, sword drawn, is turning toward the dojo.
- **End state:** mounted at highway chainage 0, yumi equipped.

#### ch02.b08 · horseback_ride (escort_convoy) · 荷駄を守って街道を行け / Escort the Pack Train: 6.0 min, checkpoint

- **Route:**
  - `spl_kaido_convoy`, 0 → 1 200 m.
  - The string moves at **450 cm/s** (a hurried trot), 4.5 m between horses. Moving time is about 267 s; nets add the rest.
  - The player's default slot is the string's **left (ravine) flank**, so threats to the loads come through the bow arc.
- **Horse:**
  - Kurimaru. Gaits: walk 170, trot 380, canter 600, gallop 850 cm/s.
  - Wind (stamina) 100: the gallop drains 8/s, the canter 2/s, and walk and trot recover 6/s.
  - `auto_steer` is an accessibility setting: the horse follows the spline while the player controls gait and aim.
  - Dismounting is allowed. `on_horse_down: dismount_continue`, with a whistle remount.
- **Weapons and arcs:** yumi −170°…+15° (left only), katana +30°…+150° (right cuts), yari −10°…+60°.
- **Threats** (10 drones in 4 groups; `x_waves`, reusing the combat_wave shape):

| Group | Trigger | Count | Where | Behavior |
|---|---|---|---|---|
| G1 | `progress_at:0.10` (≈120 m) | 2 | Left, 35 m out, 12 m up | Scout only; slow; teaching targets (`tut.010`, `tut.011`) |
| G2 | `progress_at:0.33` (≈400 m) | 3 | Rising out of the ravine, left and below | 2 of them try seizure nets on the loads |
| G3 | `progress_at:0.55` (≈660 m) | 2 + searchlight | Left; a ship's searchlight sweeps 640–800 m | Nets; the searchlight footprint spooks horses |
| G4 | `progress_at:0.75` (≈900 m) | 3 | Left; one crosses to the right at 1 020 m | Nets; the crossing drone teaches repositioning |

- **Seizure nets:**
  - The windup is **800 ms** under a cyan lock ring, then the net drops. A netted horse halts the whole tied string.
  - A 15 s lift timer starts: a tether drone tries to hoist the load.
  - **Counter:** ride up on the netted horse's left and cut to the right with the katana, or dismount and cut the net (1.0 s interact), or shoot the tethering drone.
- **Fear:** `spook_radius_cm` 900 around the searchlight footprint, net impacts and any drone passing below 4 m. A spooked horse sidesteps and drops to a trot for **2.5 s**, and aiming is disabled while Kurimaru is spooked.
- **Arrows:** riding within 3 m of the lead pack horse refills the ebira to 12 from its 24-arrow reserve (20 s cooldown).
- **Complete:** the string enters `vol_bridge_bend`. **Unlock:** `mounted_archery`.
- **Fail:** player death, a load seized (lift timer expires), or a pack horse at 0 HP → checkpoint.

#### ch02.b09 · combat_wave · 石橋の関を破れ / Break the Stone Bridge Checkpoint: 4.0 min, checkpoint

- **On foot.** The player dismounts at the bend; the groom holds the string.
- **Waves:**
  1. `start`: `enforcer_rifle` ×4 (barrier line), `grenadier` ×1 (scan gate), `marksman` ×1 (outcrop platform, 6 m up).
  2. `alive_below:3`, falling back to `after_s:120`: `enforcer_rifle` ×2 marching in from 80 m east.
- **Marksman:** a 900 ms cyan lock glint and laser line, then a 40-damage shot. He relocates after 2 shots.
- **The designed route:** the ford (`vol_ford`, move ×0.7), the stream path, the outcrop scramble, then the rear of the checkpoint.
- **Complete:** `all_waves_cleared`. **Fail:** player death.
- **Reward:** the seized-documents crate at the pod holds collectible c06, plus an arrow bundle.

#### ch02.b10 · horseback_ride (travel) · 夜明け前の道 / The Road Before Dawn: 2.0 min, checkpoint

- **Route:** `spl_kaido_dawn`, 1 215 → 1 500 m, plus the 180 m valley trail (about 465 m in all). The string walks at 250 cm/s.
- **Gaits:** walk and trot. **Weapons:** none.
- **Kohagi** splits off to check behind for stragglers (setting up b12).
- **Walk-and-talk** with the groom.
- **Optional:** bow at the Jizō group at 1 500 m (a 1.5 s interact and one line).
- **Complete:** `vol_kakuredani_mouth`. The charcoal SORA mark (c05) is on the boulder right there.

#### ch02.b11 · production_task (carry) · 米を配れ / Hand Out the Rice: 2.0 min, checkpoint, **site 1**

- **Carry:** 3 `kamasu_rice` (叺, about 2 升 ≈ 12 meals each) from `pack_horse_c` to shelters 1, 2 and 3, at about 29, 46 and 74 m.
- No enemies. The carry rules apply for consistency, and the family NPCs bow as each sack is delivered.
- **Complete:** site 1 restored (「隠されていた食糧を取り戻し、住民に分けた。」). **Registry:** 食糧 36食 / Food, 36 meals.
- **Dialogue:** the woman's and the child's lines on delivery; Nyaakoto's answer; his seed-rice line on restoration.

#### ch02.b12 · dialogue (blocking) · 屋敷が燃えている / The Estate Is Burning: 1.0 min, no checkpoint

- **Trigger:** Kohagi arrives (`vol_kohagi_arrives`, armed once site 1 is restored).
- **Blocking exchange:** 5 lines, **18.6 s**, `interrupt: cut`. She reports the fire and the blue light over the dojo, and offers the ridge road.
- **Completes into b13** at the ridge trailhead.

#### ch02.b13 · horseback_ride (travel) · 尾根道を駆け戻れ / Ride Back by the Ridge Road: 1.5 min, checkpoint

- **Route:** `spl_onemichi`, 750 m. The pack horses cannot use it, but one horse can: 「馬一頭なら通れる」.
- **Gaits:** trot, canter and gallop.
- **Wind is tuned for a story gallop:** the gallop drains 4/s and the canter nothing.
- **The plank walkway** (`vol_sando_planks`, 30 m) forces a walk: hollow hoof sounds and a drop into the gully.
- **Weapons:** none. **Dismounting:** not allowed; `on_horse_down: checkpoint`.
- **At 60% of the route**, the notice voice carries from the ships: 「資産評価を開始いたします。」
- **Complete:** `vol_back_gate`.

#### ch02.b14 · explore_optional · 燃える屋敷 / The Burning Wings: 2.0 min, checkpoint, **optional**

- `requires: [ch02.b13]`. Entering `vol_boss_courtyard` starts b15 and marks b14 skipped.
- **Points of interest** (no map markers; players find them by firelight, sound and paths):
  - **`poi_takemaru` (npc):** Takemaru calls out every 15 s while the player is near the dojo's east veranda. Lifting the fallen 庇 takes a 2.0 s interact. He reveals that Sensei laid down his sword so they would be let out, then leaves by the back gate. If b14 is skipped, Matsukichi frees him off-screen, and he is still counted at dawn (b16).
  - **`poi_dojo_pillar_notice` (lore, c03):** a seizure notice nailed to the dojo's front pillar that lists the 名札掛け. That sets up ch07's seized name board.
  - **`poi_dojo_veranda_scroll` (lore, c01):** a scroll fragment in Sekireisai's hand, scorched.
  - **`poi_chashitsu` (cache, c04):** the 肩衝茶入 tea caddy by the tea-hut hearth.
  - **`poi_ember_arrows`:** refills the ebira to 12.
- **Hazards:** fire volumes (8 dmg/s) at the dojo-to-kura gap and at the main house veranda.
- **Exit hint:** after 90 s, audio only: Dunark's tally clicks and the seizure field's hum from the courtyard.

#### ch02.b15 · boss · 上陸指揮官ドゥナークを討て / Defeat Landing Commander Dunark: 6.0 min, checkpoint at start and each phase

- **Trigger:** `vol_boss_courtyard`, which locks the arena.
- **Intro** `LS_ch02_b15_DunarkIntro` (about 32 s):
  - Sekireisai kneels in 正座 inside the seizure field.
  - His katana lies at Dunark's feet, tagged with a cyan seizure tag.
  - Dunark states that the master pledged himself as collateral in exchange for the people in the dojo.
  - Nyaakoto delivers catalog line 3.
  - Dunark announces the dunning procedure.
- **Phases and patterns:** see §3.3.
- **Defeat:** `kill`. The outro `LS_ch02_b15_DunarkOutro` (about 12 s) shows Nyaakoto's final cut through Dunark's ledger plate, and his last line.
- **Fail:** player death → phase checkpoint. Sekireisai's retry line plays.

#### ch02.b16 · cinematic · 担保 / Collateral: 2.5 min, checkpoint, **site 2**

- **Sequence:** `LS_ch02_b16_Collateral`, 150 s.
- **In the courtyard:**
  - Val Amort descends inside a lift column, untouchable. Nyaakoto's cut skids off the beam wall.
  - Val Amort writes Dunark off (償却) and delivers catalog line 2.
  - He takes Sekireisai as collateral, with account number 〇〇〇一.
  - The master's last exchange: the seed arrived; 「ならば、よい。」
  - The field and the tagged sword rise into the ship with him.
- **Cut to dawn at the Hidden Valley:**
  - Tetsugorō and the estate craftspeople set down the bellows and anvil under a lean-to by the kiln. That restores **site 2** (catalog: 「屋敷の工房に職人が戻り、修理を始めた。」).
  - The singed house 幕 curtain, salvaged by Baiō, is hung behind it, with the SORA mon half-burned (§5.9).
  - Nyaakoto counts what remains (his register-sample line).
  - Baiō gives the count and Toranosuke's absence.
  - The vow: 「取り返す。」
- **Then:** the chapter-complete registry page (§2.3 of the bible): 種籾 4俵 and 食糧 36食, sealed with the vermillion 朱印 mon.

### 3.2 Enemy baselines introduced in ch02 (proposal for L2 `enemies.json`)

ch02 is the first chapter in which every one of these types appears (bible §7), so this is where their bark set is defined. Later chapters reuse the same line ids.

| id | HP | Weapon and attacks | Telegraph | Counterplay taught in ch02 |
|---|---|---|---|---|
| `enforcer_rifle` | 100 | Levy carbine: 3-round bursts of 9 damage, 350 ms apart | 600 ms raising of shoulder and stock | Cover and yumi. Misses follow a **fixed pattern** (hit, miss, hit), never random, consistent with W0.4 |
| `blade_retainer` | 120 | Tally-blade cut, 22 damage | 420 ms fixed-direction warning (existing) | Step out of maai or around the line; awase |
| `shield_enforcer` | 160 | Baton (600 ms windup, 16 damage); bash (450 ms, 10 damage, 150 cm knockback) | Baton raise; shield dip before a bash | Immune across the front 120°. A yari rim thrust turns the shield: 1.0 s opening. Flanking also works |
| `grenadier` | 110 | Arcing shell: 35 damage, 300 cm radius, every 6 s | Arc decal 1.4 s ahead | Kill it first, or draw its fire away from the horses |
| `marksman` | 80 | Long shot, 40 damage | **900 ms** cyan glint and laser line (existing bible §7 value) | Break line of sight; flank through the ford |
| `drone` (目録) | 40 (one arrow) | Seizure net (800 ms cyan lock ring); scan cone that marks targets | Lock ring; bark | Mounted yumi on the left arc; cut nets to the right |

### 3.3 `boss_dunark`, Landing Commander Dunark (proposal for L3 `bosses.json`)

**Style:** a metronomic fencer. He fights in fixed three-beat "notices" (督促): measures at a steady tempo, each beat marked by a **tally click** (an alien abacus-bead sound; the heavy blow gets a double click). The music cue `ch02_boss_dunark` is locked to the same tempo, so rhythm, sound and animation all telegraph together. His long, straight 帳刃 (tally blade) reaches 230 cm. Easy scales every windup ×1.3 and Hard ×0.85 (bible §8). HP on Normal is **1 400**. Stagger windows take ×1.25 damage and flank cuts ×1.5.

| Phase | HP % | Tempo | Measures (fixed order) | Attacks: windup / active / recovery / damage | Counterplay | Voice telegraph (captioned) |
|---|---|---|---|---|---|---|
| P1 | 100–60 | 1 beat per 1 300 ms; pause 1 500 ms | [quick, quick, **heavy**] repeated | Quick cut 500 / 120 / 350 ms, 18 dmg. **Heavy overhead 900 / 150 / 1 100 ms, 45 dmg, amber blade edge**; guarding it costs 12 chip damage + 40 stamina | **Awase the heavy → 1.2 s stagger.** Awase on a quick cut deflects it and restarts his measure. In the pause, frontal arrows are deflected, but arrows from more than 45° off his facing and yari thrusts land | 「督促、第一回。」 First notice. |
| P2 | 60–25 | 1 beat per 1 100 ms; pause 1 200 ms | B, A, B, B, where A = [quick, quick, heavy] and B = [quick, **thrust**, heavy] | **Thrust 700 / 150 / 900 ms, 40 dmg, 4 m lunge, cannot be parried**; amber tip flare + bark. Guarding takes 20 chip damage and breaks the guard | **転 around the thrust:** a directional step in the last 400 ms of the windup puts the player at his flank. His turn lag is 0.8 s, so a flank cut does ×1.5. The awase on the heavy still staggers | 「第二回。」 Second notice; each thrust: 「一括。」 In full. |
| P3 | 25–0 | 1 beat per 1 000 ms; pause 1 000 ms | C, C, B, where C = [quick, **heavy or feint**, quick] | **Feint** (every second heavy, fixed): the blade tilts 15° with the edge turned out and his left shoulder does not drop. After the 900 ms windup he holds 400 ms, then makes a quick cut (500 ms). **Shield drone** (40 HP) orbits 3 m out and blocks arrows aimed at him | Read the shoulder (Sekireisai: 「偽りは肩に出る」). An awase on a feint whiffs, so guard instead. Shoot the drone during its **1.2 s re-index** (every 8 s, or right after it blocks an arrow) to reopen arrow damage in the pauses | 「最終督促。」 Final notice; drone: 「保全措置。」 Protective measure. |

- **Arena modifier at P2:** a burning beam falls into the northwest quarter after a 1.5 s creak-and-dust telegraph. The fire volume does 8 dmg/s.
- **Stagger bark:** 「……計算外。」 plays at most once every 20 s.
- **Checkpoints:** at fight start, 60% and 25% (6 min boss on Easy and Normal, per the bible §12.1 rule).
- **Fate:** killed; the outro cuts his ledger plate through (bible §8).
- **Change requested from L2 and L3.** The bible defines 転 as a step taken *after a successful awase* (bible §3.2). Its Dunark entry, however, asks for "転 around the thrust," and that thrust cannot be parried. This chapter proposes that L2 also accept the 転 input **during the last 400 ms of an attack flagged `marobashi_eligible`**, keeping the 0.8 s turn lag. That keeps the ch01 lesson and makes the Dunark counter work.
- **Rule-4 check:** no attack here is `muto_eligible`. Mutō-dori belongs to ch06 and ch08.

---

## 4. Dialogue: full bilingual script

**Conventions**

- **Line ids** follow `ch02.bMM.<character>.<nnn>`, where `nnn` runs in order within the beat (bible §12.4, §18). The speaker column gives the `dialogue_speakers` id.
- **Triggers** use the bible §12.1 events: `beat_start`, `beat_complete`, `volume_enter:<id>`, `site_restored:<n>`, `boss_phase:<n>`, `player_died`, `npc_downed:<id>`, `alert_state:<state>`, `item_delivered:<id>`, `progress_at:<x>`. The chapter also needs these new events, which are proposed to L1 in §7:
  - `wave_start:<n>`
  - `pattern:<id>` (as in the bible's §12.4 example)
  - `ai:<event>` for L2 AI moments
  - `interact_start:` / `interact_complete:<actor>`
  - `enemy_killed:<type>`
  - `collectible:<id>`
  - `target_hp_below:<actor|any>:<fraction>`
  - `cine@<s>` / `intro@<s>` / `outro@<s>` for subtitle cues inside a sequence
  - `event:<name>` for one-off tutorial hooks

  Modifiers: `@1` means the first occurrence only, and `+Ns` means N seconds later. "(after .nnn)" means the line is queued behind that line.
- **Modes:** ambient (walk-and-talk, player in control) unless marked `[blocking]` (at most 20 s; b04 runs 17.7 s and b12 18.6 s) or `[radio]` (Sekireisai calling from out of view).
- **Seconds column:** max(estimated VO length, English reading time at 17 cps). VO length is estimated from the mora count: kanji ≈ 1.8 morae, with pauses at 。、…; the old master and the aliens are delivered slower. Every line keeps its English at or below **17 cps** (the chapter's maximum is 14.9). Every English subtitle wraps into **2 lines of 42 characters or fewer**. Every Japanese caption is **32 characters or fewer** (2 × 16).
- **Register** follows bible §6. The aliens never contract in English; Nyaakoto, Sekireisai and the pupils use measured English ("I will").
  - Kohagi: terse, あたし.
  - The groom and the villagers: light Kamigata colouring (〜や, あかん, 〜とる), rendered as warm colloquial English.
  - Tetsugorō: blunt, Kamigata-leaning (〜や, ありゃ).
- **Counts:**
  - **112 voiced lines:** 95 character lines (89 story + 6 captioned Dunark telegraphs), matching the bible §10 budget of 95, plus 17 reusable enemy/system barks.
  - **15 UI tutorial prompts.**
  - Canon anchors placed as bible §20 requires: catalog line 1 → b01, line 2 (banker) → b16, line 3 (samurai) → b15 intro. The register samples used are 勝とうとするな… (b15) and 斬るのは最後だ… (b16).

#### ch02.b01 · 空が裂けた夜 / The Night the Sky Split (cinematic)

| Trigger | Line id | Speaker | 日本語 | Readings / notes | English subtitle | s |
|---|---|---|---|---|---|---|
| `cine@8.0` | `ch02.b01.kohagi.001` | Kohagi (`scout`) | 空から船が来た。蔵に見知らぬ封印が！ | canon: catalog ch02 line 1 | Ships came from the sky. Strange seals cover the granaries! | 4.6 |
| `cine@13.0` | `ch02.b01.sekireisai.002` | Sekireisai (`mentor`) | 落ち着け。数を言え。 |  | Steady. Give me numbers. | 3.2 |
| `cine@16.6` | `ch02.b01.kohagi.003` | Kohagi (`scout`) | 船、三つ。蔵に一つずつ、青い錠。 |  | Three ships. A blue lock on every granary. | 4.0 |
| `cine@24.0` | `ch02.b01.valamort.004` | High Collector Val Amort (`banker`) | 告知いたします。本日より、猫柳生の地は当院の管理下となりました。 | 当院(とういん) | Notice. As of today, the Nyaagyu lands are managed by this House. | 8.5 |
| `cine@32.9` | `ch02.b01.valamort.005` | High Collector Val Amort (`banker`) | 蔵、田畑、工房は、未払い債務の担保として差し押さえました。 | 担保(たんぽ)・差し押さえ(さしおさえ) | Granaries, fields and workshops are seized as collateral for unpaid debt. | 7.7 |
| `cine@41.0` | `ch02.b01.valamort.006` | High Collector Val Amort (`banker`) | 抵抗は延滞とみなされ、利息が発生いたします。 | 延滞(えんたい) | Resistance will be treated as delinquency. Interest will accrue. | 5.7 |
| `cine@47.1` | `ch02.b01.nyaakoto.007` | Nyaakoto (`samurai`) | 借りた覚えは、ない。 |  | We never borrowed a thing. | 2.4 |
| `cine@50.0` | `ch02.b01.sekireisai.008` | Sekireisai (`mentor`) | 借りは向こうが書くものらしいのう。……門を閉めよ。 |  | It seems they write the debt themselves. …Close the gate. | 6.3 |

#### ch02.b02 · 長屋門を守れ / Hold the Nagaya Gate (combat_wave)

| Trigger | Line id | Speaker | 日本語 | Readings / notes | English subtitle | s |
|---|---|---|---|---|---|---|
| `beat_start` | `ch02.b02.sekireisai.001` | Sekireisai (`mentor`) | 門を守れ。一歩も入れるな。 |  | Hold the gate. Not one step inside. | 3.9 |
| `beat_start (after .001)` | `ch02.b02.nyaakoto.002` | Nyaakoto (`samurai`) | 松吉は右、竹丸は左。屋根の者は私が射る。 |  | Matsukichi, right. Takemaru, left. I will take the roof. | 5.5 |
| `alert_state:alert` | `ch02.b02.enforcer.003` | Enforcement Office trooper, rifle voice (`enforcer`) | 債務者の抵抗を確認。制圧いたします。 | 債務者(さいむしゃ); bark, repeatable, cd 12 s | Debtor resistance confirmed. Suppressing. | 4.4 |
| `ai:flank` | `ch02.b02.enforcer.004` | Enforcement Office trooper, rifle voice (`enforcer`) | 側面より回収いたします。 | bark, repeatable, cd 15 s | Collecting from the flank. | 2.7 |
| `wave_start:2` | `ch02.b02.matsukichi.005` | Matsukichi (`pupil_matsukichi`) | 潜り戸が破られた！ | 潜り戸(くぐりど) | The wicket is breached! | 2.3 |
| `npc_downed:pupil_matsukichi` | `ch02.b02.matsukichi.006` | Matsukichi (`pupil_matsukichi`) | くっ……足を、やられた。 | repeatable, cd 30 s | My leg… they got my leg. | 2.6 |
| `wave_start:3` | `ch02.b02.baio.007` | Baiō (`pupil_baio`) | 閂が持たぬ！　門が開くぞ！ | 閂(かんぬき) | The bar will not hold! The gate is opening! | 3.2 |
| `wave_start:3 (after .007)` | `ch02.b02.retainer.008` | Enforcement Office trooper, blade retainer voice (`enforcer`) | 取り立てに参りました。 | 取り立て(とりたて); bark, repeatable, cd 20 s | We have come to collect. | 2.5 |
| `ai:retreat` | `ch02.b02.enforcer.009` | Enforcement Office trooper, rifle voice (`enforcer`) | 損耗率、許容値を超過。後退いたします。 | 損耗率(そんもうりつ); bark, repeatable, cd 20 s | Losses exceed tolerance. Withdrawing. | 4.6 |
| `beat_complete` | `ch02.b02.sekireisai.010` | Sekireisai (`mentor`) | 武具蔵に盾の者が入った。槍を取れ。刀では届かぬ。 | 武具蔵(ぶぐぐら) | Shield-bearers are in the armory. Take a spear. A sword will not reach. | 7.0 |

#### ch02.b03 · 武具蔵の槍 / Spears from the Armory (combat_wave)

| Trigger | Line id | Speaker | 日本語 | Readings / notes | English subtitle | s |
|---|---|---|---|---|---|---|
| `beat_start` | `ch02.b03.nyaakoto.001` | Nyaakoto (`samurai`) | 先生、一本お借りします。 |  | Sensei, I will borrow one. | 3.2 |
| `beat_start (after .001) [radio]` | `ch02.b03.sekireisai.002` | Sekireisai (`mentor`) | 盾の縁を突け。正面は鉄じゃ。 | 縁(ふち) | Thrust at the shield's edge. Its face is iron. | 4.1 |
| `alert_state:alert` | `ch02.b03.shield.003` | Enforcement Office trooper, shield voice (`enforcer`) | 前進。資産を保全いたします。 | 保全(ほぜん); bark, repeatable, cd 15 s | Advancing. Securing assets. | 3.4 |
| `ai:shield_turned` | `ch02.b03.shield.004` | Enforcement Office trooper, shield voice (`enforcer`) | 盾、姿勢を喪失。 | 喪失(そうしつ); bark, repeatable, cd 10 s | Shield displaced. | 2.3 |
| `ai:player_inside_polearm_min [radio]` | `ch02.b03.sekireisai.005` | Sekireisai (`mentor`) | 懐に入られたら槍は死ぬ。退いて間を取れ。 | 懐(ふところ)・間(ま); once | Let him inside and the spear is dead. Step back. Take distance. | 5.6 |

#### ch02.b04 · 種は明日の田 / Seed Is Tomorrow's Field (dialogue)

| Trigger | Line id | Speaker | 日本語 | Readings / notes | English subtitle | s |
|---|---|---|---|---|---|---|
| `beat_start` | `ch02.b04.sekireisai.001` | Sekireisai (`mentor`) | ニャーコト。蔵の種籾を、隠れ谷へ運べ。 | 種籾(たねもみ)・隠れ谷(かくれだに) | Nyaakoto. Take the seed rice to the Hidden Valley. | 5.0 |
| `beat_start (after .001)` | `ch02.b04.nyaakoto.002` | Nyaakoto (`samurai`) | 先生は。 |  | And you, Sensei? | 1.5 |
| `volume_enter:vol_courtyard_west [blocking]` | `ch02.b04.sekireisai.003` | Sekireisai (`mentor`) | わしは残る。年寄りの足では荷の邪魔じゃ。 |  | I stay. Old legs would only slow the load. | 5.4 |
| `volume_enter:vol_courtyard_west [blocking]` | `ch02.b04.nyaakoto.004` | Nyaakoto (`samurai`) | しかし—— |  | But— | 1.3 |
| `volume_enter:vol_courtyard_west [blocking]` | `ch02.b04.sekireisai.005` | Sekireisai (`mentor`) | 種は明日の田じゃ。刀は、何のためにある。 | canon: bible §9 key line 「種は明日の田じゃ」 | Seed is tomorrow's field. What is the sword for? | 5.2 |
| `volume_enter:vol_courtyard_west [blocking]` | `ch02.b04.nyaakoto.006` | Nyaakoto (`samurai`) | ……民から、預かるもの。 | callback ch01.b12 | …It is held in trust from the people. | 2.8 |
| `volume_enter:vol_courtyard_west [blocking]` | `ch02.b04.sekireisai.007` | Sekireisai (`mentor`) | ならば行け。 |  | Then go. | 1.8 |
| `beat_complete` | `ch02.b04.sekireisai.008` | Sekireisai (`mentor`) | 竹丸、ついて参れ。道場にまだ人がおる。 |  | Takemaru, with me. There are still people in the dojo. | 5.2 |
| `beat_complete (after .008)` | `ch02.b04.baio.009` | Baiō (`pupil_baio`) | 皆、裏山の杣道へ。子らを先に。 | 杣道(そまみち) | Everyone, to the woodcutters' path. Children first. | 3.9 |

#### ch02.b05 · 種籾を運び出せ / Carry Out the Seed Rice (production_task)

| Trigger | Line id | Speaker | 日本語 | Readings / notes | English subtitle | s |
|---|---|---|---|---|---|---|
| `beat_start` | `ch02.b05.groom.001` | Groom (`groom`) | ニャーコト様、馬は二頭。一頭に二俵ずつ！ | 二俵(にひょう) | Sir, two horses. Two bales on each! | 4.7 |
| `interact_start:seal_kura_sw` | `ch02.b05.system.002` | Credit House notice voice (`credit_system`) | 封印への接触を検知。延滞として記録いたします。 | bark, repeatable, cd 8 s | Seal contact detected. Recorded as delinquency. | 5.2 |
| `ai:carry_spotted` | `ch02.b05.enforcer.003` | Enforcement Office trooper, rifle voice (`enforcer`) | 差押物件の搬出を確認。阻止いたします。 | 差押物件(さしおさえぶっけん)・搬出(はんしゅつ); bark, repeatable, cd 20 s | Removal of seized property detected. Intercepting. | 4.6 |
| `progress_at:0.5` | `ch02.b05.groom.004` | Groom (`groom`) | 一駄、積んだ！ | 一駄(いちだ) | One load is on! | 2.0 |
| `progress_at:1.0` | `ch02.b05.groom.005` | Groom (`groom`) | 二駄目も積みました！　行けます！ | 二駄目(にだめ) | Second load on! We can go! | 3.8 |

#### ch02.b06 · 荷馬を守れ / Protect the Pack Horses (production_task)

| Trigger | Line id | Speaker | 日本語 | Readings / notes | English subtitle | s |
|---|---|---|---|---|---|---|
| `beat_start` | `ch02.b06.kohagi.001` | Kohagi (`scout`) | 上。落ちてくる。三つ。 |  | Above. Falling. Three. | 3.0 |
| `ai:drop_pod_launch` | `ch02.b06.system.002` | Credit House notice voice (`credit_system`) | 回収班、降下いたします。 | bark, repeatable, cd 30 s | Collection team, descending. | 2.8 |
| `ai:grenadier_fire` | `ch02.b06.grenadier.003` | Enforcement Office trooper, grenadier voice (`enforcer`) | 曲射、開始。 | 曲射(きょくしゃ); bark, repeatable, cd 12 s | Arcing fire, commencing. | 1.9 |
| `target_hp_below:any:0.5` | `ch02.b06.groom.004` | Groom (`groom`) | 馬が怯えとる！　これ以上はあかん！ | 怯え(おびえ); once | The horses are panicking! They can't take more! | 3.8 |
| `progress_at:0.5 [radio]` | `ch02.b06.sekireisai.005` | Sekireisai (`mentor`) | ニャーコト、急げ！　長くは持たぬ！ |  | Nyaakoto, hurry! We cannot hold long! | 4.1 |
| `beat_complete` | `ch02.b06.kohagi.006` | Kohagi (`scout`) | 裏門、空いた。今。 | 裏門(うらもん) | Back gate's clear. Now. | 2.6 |

#### ch02.b07 · 裏門 / The Back Gate (cinematic)

| Trigger | Line id | Speaker | 日本語 | Readings / notes | English subtitle | s |
|---|---|---|---|---|---|---|
| `cine@9.0` | `ch02.b07.kohagi.001` | Kohagi (`scout`) | 道は、あたしが先に見る。 |  | I'll scout the road ahead. | 2.8 |
| `cine@18.0` | `ch02.b07.groom.002` | Groom (`groom`) | 乗掛で参ります。遅れたら、置いていってくだされ。 | 乗掛(のりかけ) | I'll ride atop the load. If I fall behind, leave me. | 5.1 |
| `cine@24.0` | `ch02.b07.nyaakoto.003` | Nyaakoto (`samurai`) | 誰も置いていかない。 |  | I leave no one behind. | 2.5 |
| `cine@40.0` | `ch02.b07.nyaakoto.004` | Nyaakoto (`samurai`) | 栗丸。今夜は、走ってくれ。 | 栗丸(くりまる) | Kurimaru. Tonight, run for me. | 3.5 |

#### ch02.b08 · 荷駄を守って街道を行け / Escort the Pack Train (horseback_ride)

| Trigger | Line id | Speaker | 日本語 | Readings / notes | English subtitle | s |
|---|---|---|---|---|---|---|
| `wave_start:1` | `ch02.b08.drone.001` | Inventory drone (`drone`) | 目録に記載。動産、馬三頭。 | 目録(もくろく)・動産(どうさん); bark, repeatable, cd 60 s | Entered into inventory. Movables: three horses. | 3.7 |
| `ai:net_windup` | `ch02.b08.drone.002` | Inventory drone (`drone`) | 差押網、投下いたします。 | 差押網(さしおさえあみ); bark, repeatable, cd 10 s | Seizure net, deploying. | 2.8 |
| `ai:convoy_netted` | `ch02.b08.groom.003` | Groom (`groom`) | 網や！　網が掛かった！ | repeatable, cd 20 s | A net! They've netted us! | 2.8 |
| `ai:convoy_netted (after .003)` | `ch02.b08.nyaakoto.004` | Nyaakoto (`samurai`) | 右に寄せろ。切る。 | once | Pull right. I will cut it. | 2.6 |
| `wave_start:3` | `ch02.b08.system.005` | Credit House notice voice (`credit_system`) | 照合中。……照合中。 | 照合(しょうごう); bark, repeatable, cd 25 s | Verifying. …Verifying. | 3.0 |
| `ai:horse_spooked:convoy` | `ch02.b08.groom.006` | Groom (`groom`) | 光や！　馬を下げなされ！ | once | The light! Pull the horses back! | 2.9 |
| `ai:horse_spooked:kurimaru` | `ch02.b08.nyaakoto.007` | Nyaakoto (`samurai`) | どう、どう……栗丸、大丈夫だ。 | once | Easy, easy… Kurimaru, you are all right. | 3.7 |
| `ai:drone_crossed_right` | `ch02.b08.nyaakoto.008` | Nyaakoto (`samurai`) | 右に回った……下がって取る。 | once | It went right… I will drop back and take it. | 3.5 |
| `beat_complete` | `ch02.b08.kohagi.009` | Kohagi (`scout`) | 橋に関所。兵が六、擲弾が一。向こう岸の上に、光る目が一。 | 関所(せきしょ)・擲弾(てきだん) | Bridge checkpoint. Six troops, one grenadier. A glinting eye on the far bank. | 7.0 |

#### ch02.b09 · 石橋の関を破れ / Break the Stone Bridge Checkpoint (combat_wave)

| Trigger | Line id | Speaker | 日本語 | Readings / notes | English subtitle | s |
|---|---|---|---|---|---|---|
| `beat_start` | `ch02.b09.nyaakoto.001` | Nyaakoto (`samurai`) | 馬を頼む。ここで待て。 |  | Watch the horses. Wait here. | 2.9 |
| `beat_start (after .001)` | `ch02.b09.kohagi.002` | Kohagi (`scout`) | 浅瀬がある。下流に五十歩。 | 浅瀬(あさせ) | There's a ford. Fifty paces downstream. | 3.6 |
| `ai:marksman_lock` | `ch02.b09.marksman.003` | Enforcement Office trooper, marksman voice (`enforcer`) | 照準、査定中。 | 査定(さてい); bark, repeatable, cd 6 s; captioned telegraph (900 ms lock glint) | Sighting. Assessing. | 2.1 |
| `alert_state:alert` | `ch02.b09.enforcer.004` | Enforcement Office trooper, rifle voice (`enforcer`) | 未登録の債務者を確認。 | bark, repeatable, cd 15 s | Unregistered debtor sighted. | 3.0 |
| `alert_state:search` | `ch02.b09.enforcer.005` | Enforcement Office trooper, rifle voice (`enforcer`) | 対象を見失いました。探索に移行します。 | bark, repeatable, cd 15 s | Target lost. Beginning search. | 4.4 |
| `enemy_killed:marksman` | `ch02.b09.kohagi.006` | Kohagi (`scout`) | 目、潰れた。 | 潰れた(つぶれた); once | The eye's out. | 1.7 |
| `wave_start:2` | `ch02.b09.enforcer.007` | Enforcement Office trooper, rifle voice (`enforcer`) | 検問所に増援を要請。至急。 | 検問所(けんもんじょ); bark, repeatable, cd 60 s | Requesting reinforcement at the checkpoint. Urgent. | 3.7 |

#### ch02.b10 · 夜明け前の道 / The Road Before Dawn (horseback_ride)

| Trigger | Line id | Speaker | 日本語 | Readings / notes | English subtitle | s |
|---|---|---|---|---|---|---|
| `beat_start` | `ch02.b10.kohagi.001` | Kohagi (`scout`) | あたしは後ろを見てくる。はぐれた人がいるかも。 |  | I'll check behind us. There may be stragglers. | 4.7 |
| `progress_at:0.3` | `ch02.b10.groom.002` | Groom (`groom`) | ……先生は、ご無事でしょうか。 |  | …Do you think Sensei is safe? | 3.3 |
| `progress_at:0.3 (after .002)` | `ch02.b10.nyaakoto.003` | Nyaakoto (`samurai`) | 先生は、猫柳生で一番強い。 |  | Sensei is the strongest in Nyaagyu. | 3.7 |
| `interact:jizo_bow` | `ch02.b10.nyaakoto.004` | Nyaakoto (`samurai`) | ……道中、お守りください。 | once; optional | …Watch over the road. | 3.1 |

#### ch02.b11 · 米を配れ / Hand Out the Rice (production_task)

| Trigger | Line id | Speaker | 日本語 | Readings / notes | English subtitle | s |
|---|---|---|---|---|---|---|
| `item_delivered:shelter_1` | `ch02.b11.villager.001` | Villager (`villager`) | ありがたや……子らが朝から何も。 |  | Bless you… The children haven't eaten since morning. | 3.5 |
| `item_delivered:shelter_2` | `ch02.b11.child.002` | Child (`child`) | このお米、借り？　返さなあかんの？ |  | Is this rice a loan? Do we have to pay it back? | 3.7 |
| `item_delivered:shelter_2 (after .002)` | `ch02.b11.nyaakoto.003` | Nyaakoto (`samurai`) | 借りではない。田で育ったものだ。 |  | It is not a loan. It grew in our fields. | 3.8 |
| `site_restored:1` | `ch02.b11.nyaakoto.004` | Nyaakoto (`samurai`) | 種籾には手をつけるな。あれは来年の田だ。 | 種籾(たねもみ) | Do not touch the seed rice. That is next year's field. | 4.8 |

#### ch02.b12 · 屋敷が燃えている / The Estate Is Burning (dialogue)

| Trigger | Line id | Speaker | 日本語 | Readings / notes | English subtitle | s |
|---|---|---|---|---|---|---|
| `beat_start [blocking]` | `ch02.b12.kohagi.001` | Kohagi (`scout`) | 屋敷が燃えてる。 |  | The estate is burning. | 2.2 |
| `beat_start [blocking]` | `ch02.b12.nyaakoto.002` | Nyaakoto (`samurai`) | 先生は。 |  | Sensei? | 1.5 |
| `beat_start [blocking]` | `ch02.b12.kohagi.003` | Kohagi (`scout`) | 残ってる。道場の上に、青い光が集まってた。 |  | Still there. Blue light was gathering over the dojo. | 4.9 |
| `beat_start [blocking]` | `ch02.b12.kohagi.004` | Kohagi (`scout`) | 尾根道なら、半分で着く。馬一頭なら通れる。 | 尾根道(おねみち) | The ridge road is half the distance. One horse can pass. | 5.3 |
| `beat_start [blocking]` | `ch02.b12.nyaakoto.005` | Nyaakoto (`samurai`) | 種は届いた。次は、先生だ。 |  | The seed is safe. Now, Sensei. | 3.5 |

#### ch02.b13 · 尾根道を駆け戻れ / Ride Back by the Ridge Road (horseback_ride)

| Trigger | Line id | Speaker | 日本語 | Readings / notes | English subtitle | s |
|---|---|---|---|---|---|---|
| `beat_start` | `ch02.b13.nyaakoto.001` | Nyaakoto (`samurai`) | 走れ、栗丸……！ |  | Run, Kurimaru…! | 2.3 |
| `progress_at:0.6` | `ch02.b13.system.002` | Credit House notice voice (`credit_system`) | 告知。猫柳生家の資産評価を開始いたします。 | 資産評価(しさんひょうか) | Notice. Asset appraisal of House Nyaagyu has begun. | 5.5 |

#### ch02.b14 · 燃える屋敷 / The Burning Wings (explore_optional)

| Trigger | Line id | Speaker | 日本語 | Readings / notes | English subtitle | s |
|---|---|---|---|---|---|---|
| `volume_enter:vol_dojo_east_veranda` | `ch02.b14.takemaru.001` | Takemaru (`pupil_takemaru`) | 誰か……！　ここだ！ | repeatable, cd 15 s | Someone…! Over here! | 2.5 |
| `interact_complete:beam_takemaru` | `ch02.b14.takemaru.002` | Takemaru (`pupil_takemaru`) | 先生が……俺たちを出す代わりに、刀を置かれた。 |  | Sensei… He laid down his sword so they would let us out. | 5.1 |
| `interact_complete:beam_takemaru (after .002)` | `ch02.b14.nyaakoto.003` | Nyaakoto (`samurai`) | 裏門から谷へ行け。道は開いている。 |  | Take the back gate to the valley. The road is open. | 4.3 |
| `collectible:ch02.c03` | `ch02.b14.nyaakoto.004` | Nyaakoto (`samurai`) | 名札掛けまで……差し押さえたのか。 | 名札掛け(なふだかけ); once | Even the name board… They seized that too. | 4.1 |

#### ch02.b15 · 上陸指揮官ドゥナークを討て / Defeat Landing Commander Dunark (boss)

| Trigger | Line id | Speaker | 日本語 | Readings / notes | English subtitle | s |
|---|---|---|---|---|---|---|
| `intro@6.0` | `ch02.b15.dunark.001` | Landing Commander Dunark (`boss_dunark`) | 猫柳生石鈴斎様は、ご自身を担保として差し入れられました。 | 石鈴斎(せきれいさい)・差し入れ(さしいれ) | Nyaagyu Sekireisai has pledged himself as collateral. | 7.4 |
| `intro@13.8` | `ch02.b15.dunark.002` | Landing Commander Dunark (`boss_dunark`) | 引き換えに、道場内の人員は解放いたしました。 | 人員(じんいん) | In exchange, the personnel in the dojo were released. | 5.7 |
| `intro@19.9` | `ch02.b15.nyaakoto.003` | Nyaakoto (`samurai`) | 民の手を縛る帳簿なら、ここで断つ。 | 帳簿(ちょうぼ); canon: catalog ch02 line 3 | If your ledger binds their hands, I will break its hold here. | 4.2 |
| `intro@24.5` | `ch02.b15.dunark.004` | Landing Commander Dunark (`boss_dunark`) | 上陸指揮官ドゥナーク。督促手続きを開始いたします。 | 督促(とくそく) | Landing Commander Dunark. Commencing dunning procedure. | 6.6 |
| `boss_phase:1` | `ch02.b15.dunark.005` | Landing Commander Dunark (`boss_dunark`) | 督促、第一回。 | 督促(とくそく); canon: bible §8 voice telegraph; captioned telegraph | First notice. | 2.5 |
| `boss_phase:1 (after .005)` | `ch02.b15.sekireisai.006` | Sekireisai (`mentor`) | 勝とうとするな。相手の太刀が、おぬしの道を教えてくれる。 | 太刀(たち); canon: bible §6.5 register sample | Do not try to win. His sword will show you your path. | 7.1 |
| `boss_phase:2` | `ch02.b15.dunark.007` | Landing Commander Dunark (`boss_dunark`) | 第二回。 | canon: bible §8 voice telegraph; captioned telegraph | Second notice. | 1.7 |
| `pattern:thrust` | `ch02.b15.dunark.008` | Landing Commander Dunark (`boss_dunark`) | 一括。 | 一括(いっかつ); captioned telegraph, repeatable | In full. | 1.3 |
| `boss_phase:2 (after .007)` | `ch02.b15.sekireisai.009` | Sekireisai (`mentor`) | 突きは受けるな。転じて横を取れ。 | 転じて(てんじて; 転(まろばし)の教え) | Do not meet the thrust. Roll aside and take his flank. | 4.5 |
| `boss_phase:3` | `ch02.b15.dunark.010` | Landing Commander Dunark (`boss_dunark`) | 最終督促。 | canon: bible §8 voice telegraph; captioned telegraph | Final notice. | 2.0 |
| `pattern:shield_drone` | `ch02.b15.dunark.011` | Landing Commander Dunark (`boss_dunark`) | 保全措置。 | captioned telegraph; once | Protective measure. | 2.0 |
| `boss_phase:3 (after .010)` | `ch02.b15.sekireisai.012` | Sekireisai (`mentor`) | 刃の傾きを見よ。偽りは肩に出る。 | 偽り(いつわり) | Watch the tilt of his blade. A lie shows in the shoulder. | 4.7 |
| `pattern:stagger` | `ch02.b15.dunark.013` | Landing Commander Dunark (`boss_dunark`) | ……計算外。 | captioned telegraph, repeatable | …Unaccounted for. | 2.1 |
| `player_died` | `ch02.b15.sekireisai.014` | Sekireisai (`mentor`) | 立て。拍子に乗るな。拍子を読め。 | 拍子(ひょうし); repeatable, cd 0 s | Stand. Do not ride his rhythm. Read it. | 5.0 |
| `outro@3.0` | `ch02.b15.dunark.015` | Landing Commander Dunark (`boss_dunark`) | 未回収の……まま、とは。 | 未回収(みかいしゅう) | To fall… with the account still open. | 3.1 |

#### ch02.b16 · 担保 / Collateral (cinematic)

| Trigger | Line id | Speaker | 日本語 | Readings / notes | English subtitle | s |
|---|---|---|---|---|---|---|
| `cine@14.0` | `ch02.b16.valamort.001` | High Collector Val Amort (`banker`) | 上陸指揮官ドゥナーク。損失として、償却いたします。 | 償却(しょうきゃく) | Landing Commander Dunark. Written off as a loss. | 6.4 |
| `cine@21.0` | `ch02.b16.valamort.002` | High Collector Val Amort (`banker`) | 今日から、その収穫も労働も我らへの負債だ。 | 負債(ふさい); canon: catalog ch02 line 2 | From today, your harvest and labor are debts owed to us. | 5.7 |
| `cine@28.0` | `ch02.b16.valamort.003` | High Collector Val Amort (`banker`) | 債務者番号〇〇〇一。石鈴斎様を、担保としてお預かりいたします。 | 〇〇〇一(まる・まる・まる・いち; B7 to confirm) | Debtor zero-zero-zero-one. The honorable Sekireisai is held as collateral. | 8.9 |
| `cine@37.3` | `ch02.b16.nyaakoto.004` | Nyaakoto (`samurai`) | 先生！ |  | Sensei! | 1.3 |
| `cine@39.0` | `ch02.b16.sekireisai.005` | Sekireisai (`mentor`) | 来るな。……種は、届いたか。 |  | Stay back. …Did the seed arrive? | 3.8 |
| `cine@43.2` | `ch02.b16.nyaakoto.006` | Nyaakoto (`samurai`) | ……届きました。 |  | …It arrived. | 2.1 |
| `cine@46.0` | `ch02.b16.sekireisai.007` | Sekireisai (`mentor`) | ならば、よい。 |  | Then it is well. | 1.8 |
| `cine@52.0` | `ch02.b16.valamort.008` | High Collector Val Amort (`banker`) | ご安心を。利息は毎晩、きちんと計上いたします。 | 計上(けいじょう) | Rest assured. Interest will be booked faithfully every night. | 6.1 |
| `cine@82.0` | `ch02.b16.tetsugoro.009` | Tetsugorō the gunsmith (`gunsmith`) | 鞴も金床も担いできた。道具さえありゃ、どこでも鍛冶場や。 | 鞴(ふいご)・金床(かなとこ) | We carried the bellows and the anvil. With tools, anywhere is a smithy. | 6.1 |
| `cine@95.0` | `ch02.b16.nyaakoto.010` | Nyaakoto (`samurai`) | 斬るのは最後だ。まず、守るものを数える。 | canon: bible §6.5 register sample | Cutting comes last. First, count what we protect. | 4.7 |
| `cine@101.0` | `ch02.b16.baio.011` | Baiō (`pupil_baio`) | 女子供が十九、年寄りが七。門弟は、わしと松吉と竹丸。 | 門弟(もんてい) | Nineteen women and children, seven elders. Pupils: Matsukichi, Takemaru and I. | 6.5 |
| `cine@108.0` | `ch02.b16.nyaakoto.012` | Nyaakoto (`samurai`) | 虎之介は。 | 虎之介(とらのすけ) | And Toranosuke? | 1.8 |
| `cine@110.2` | `ch02.b16.baio.013` | Baiō (`pupil_baio`) | 鐘と同時に、鷲尾の家へ走ったきりじゃ。 | 鷲尾(わしお) | He ran for the Washio house at the first bell. Nothing since. | 4.2 |
| `cine@118.0` | `ch02.b16.baio.014` | Baiō (`pupil_baio`) | 先生のお席は、空けておこう。 |  | We will keep Sensei's seat empty. | 3.2 |
| `cine@128.0` | `ch02.b16.nyaakoto.015` | Nyaakoto (`samurai`) | 取り返す。先生も、蔵も、田も。 |  | I will take it all back. Sensei, the granaries, the fields. | 4.0 |

### 4.1 Tutorial prompts (UI text for L4 `ui_strings.json`, not voiced)

`{Action}` tokens are replaced with device-aware glyphs by L4. Each prompt shows once, until the action is performed or for 6 s, and can be recalled from the pause menu's 心得 (tips) list.

| Trigger | Prompt id | 日本語 (UI) | English (UI) |
|---|---|---|---|
| `npc_downed:any` | `ch02.b02.tut.001` | 倒れた門弟のそばで{Interact}長押し：助け起こす。 | Hold {Interact} beside a downed pupil to help them up. |
| `beat_start` | `ch02.b03.tut.002` | 槍を得た。{WeaponTwo}（長柄）／{ArmsWheel}で持ち替え。 | Yari acquired. Press {WeaponTwo} (polearms) or {ArmsWheel} to switch. |
| `volume_enter:vol_bugugura_yard` | `ch02.b03.tut.003` | 盾の縁を槍で突けば、構えが崩れる。 | Thrust at a shield's edge to break its guard. |
| `ai:player_inside_polearm_min` | `ch02.b03.tut.004` | 懐では槍は弱い。退いて間合いを取れ。 | The yari is weak up close. Step back to regain distance. |
| `volume_enter:vol_kura_sw_door` | `ch02.b05.tut.005` | {Interact}長押し：石突で封印をこじ開ける。 | Hold {Interact}: pry the seal off with the spear butt. |
| `event:first_pickup` | `ch02.b05.tut.006` | 俵を担ぐ間は片手の刀のみ。弓は使えず、走れない。 | Carrying a bale: one-handed katana only. No bow, no sprint. |
| `event:first_pickup+4s` | `ch02.b05.tut.007` | {Interact}で俵を下ろせる。後で拾い直せる。 | Press {Interact} to set a bale down. Pick it up again later. |
| `beat_start` | `ch02.b06.tut.008` | 荷馬を守れ。そばで{Interact}：傷の手当て。 | Protect the pack horses. Press {Interact} beside one to treat it. |
| `ai:drop_pod_launch@1` | `ch02.b06.tut.009` | 橙の輪は降下ポッドの着弾点。輪から離れよ。 | Amber rings mark where pods will land. Get clear. |
| `beat_start` | `ch02.b08.tut.010` | 手綱を結び{Fire}長押しで引き分け。馬上の弓は左（弓手）のみ。 | Reins knotted. Hold {Fire} to draw. In the saddle, the bow shoots left only. |
| `beat_start+6s` | `ch02.b08.tut.011` | 前進しながら{Sprint}で歩度を上げ、後ろへ引いて緩める。荷馬の速さに合わせよ。 | Hold {Sprint} while moving forward to quicken the gait; pull back to slow. Keep pace with the pack train. |
| `ai:convoy_netted@1` | `ch02.b08.tut.012` | 網の掛かった荷馬の左に並び、右へ斬って網を切れ。 | Ride on a netted horse's left and cut to your right to free it. |
| `event:arrows_below:4` | `ch02.b08.tut.013` | 先頭の荷馬に並ぶと、予備の箙から矢を補える。 | Ride beside the lead pack horse to refill arrows from its spare quiver. |
| `beat_start` | `ch02.b13.tut.014` | 襲歩は馬の息を使う。尽きる前に駈歩へ落とせ。 | The gallop spends the horse's wind. Ease to a canter before it runs out. |
| `pattern:thrust@1` | `ch02.b15.tut.015` | 突きは合わせられない。構えの終わりに横へ踏め（転）。 | The thrust cannot be parried. Step aside just before it lands (marobashi). |

### 4.2 Notes for native review (B7) and casting

1. **Catalog line 2 is off-register.** Val Amort's 「今日から、その収穫も労働も我らへの負債だ。」 is canon, but its plain だ clashes with the bible's hyper-polite alien register (bible §6.3). If canon may be revised, the proposed variant is 「本日より、その収穫も労働も、当院への負債でございます。」
2. **Account number reading.** Read 〇〇〇一 digit by digit, as in the bible's 七〇三一 example. Proposed reading まる・まる・まる・いち; confirm this or れい・れい・れい・いち.
3. **Dialect.** The groom's and villagers' Kamigata colouring (あかん, 〜とる, 〜や) must stay light. It is Yamato, not Osaka comedy. Review fix: the later Osaka contraction なはれ became the period form なされ (「馬を下げなされ！」); the same rule applies campaign-wide (no なはれ, まっせ or あきまへん).
4. **Pronouns.** Nyaakoto uses 私 with the pupils (b02) and 拙者 register with Sekireisai, omitting the pronoun where Japanese allows.
5. **Takemaru's 俺** (b14) is the one place a pupil is informal, under stress. Confirm it is acceptable for a young samurai speaking to a peer.
6. **Delivery.** 「しかし——」 (b04) is cut off by Sekireisai; record it as an interrupted breath, not a full word.
7. **Finance terms.** 差し入れる (b15) is the financial usage 担保を差し入れる (to pledge collateral), deliberately bureaucratic in Dunark's mouth. Confirm it reads naturally.
8. **Placement.** In cinematics, the subtitle "speaker name in both scripts" (bible §18) sits above the line and is not counted in the 16-character JA line limit.

---

## 5. Historical and cultural accuracy

These are campaign choices, and each still needs review by a historian and a practitioner (bible §20 open item 2). The sources are listed at the end of the section.

### 5.1 Kenjutsu vocabulary and the fictional school

- **Terms used, all general period vocabulary:**
  - 正眼 (seigan, the base stance)
  - 間合い / 水月 (maai; the "moon in water" distance read)
  - 受け (uke)
  - 合わせ (awase)
  - 転 (marobashi)
  - 残心 (zanshin)
  - 懐 (futokoro, the space inside a weapon's reach)
  - 拍子 (hyōshi, rhythm and timing)
  
  **No named kata** of the living Yagyū Shinkage-ryū is reproduced or referenced (bible §3.1).
- **Dunark's measures are a game abstraction.** His three-beat "notices" are an alien fencing system. The Japanese answer, 「拍子に乗るな。拍子を読め。」, uses 拍子 as general vocabulary. It is not a quotation: the best-known period discussions of 拍子 (柳生宗矩『兵法家伝書』, 1632; 宮本武蔵『五輪書』, c. 1645) postdate Genna 9 (1623), so the chapter quotes neither.
- **The scroll fragment (c01) is original text.** 「刀を抜くは易し。納むるは難し。」 foreshadows the sheathed mutō-dori of ch06 and ch08. It is not taken from 兵法家伝書.
- **Sekireisai's surrender.** In period ethos, giving up one's swords is grave. The chapter frames it as 活人剣: a master buying the release of the people in the dojo with his own person. It is staged with dignity: 正座 inside the field, never bound on screen. This beat needs the practitioner's and the native reviewer's reading.
- **Animation guidance:** committed, readable cuts with real recovery and no spinning combos (bible §4.1). The pupils fight with real daishō, not training blades. Motion capture and cinematic sword work must be reviewed before release, and marketing must not call them authentic Yagyū practice.

### 5.2 Yari (su-yari)

- **Form:** a straight, double-edged point on a long shaft (素槍), not the later 管槍 with a sliding tube. Its reference is British Museum **OA+.7199**, a middle-Edo su-yari: 1.93 m overall, 18 cm blade, 48 cm tang. The existing source study `Content/SourceArt/Weapons/NyaagyuYari` matches those envelopes. The Met's 1727 foot yari notes that foot spears were commonly about seven feet long. The catalog reach of 285 cm includes the wielder's extension.
- **Handling:**
  - Thrusts are driven by both hands, with the rear hand sliding the shaft forward.
  - The weapon is weak inside its useful distance (bible §4.3).
  - The 石突 iron butt cap is used as a lever on the seal. That is a plausible improvised use of a real fitting; the study models a steel shoe there.
- **Mounted use:** forward and right-side (馬手) thrusts only (bible §4.3, §11).
- **The shield rim thrust is game logic** against an alien tower shield, not a claim about period technique.

### 5.3 Yumi and mounted archery

- **On foot:** the arrow rests on the right of the bow, the draw carries past the ear, and the bow rotates in the hand after release (弓返り, yugaeri). The draw takes 650 ms, and the arrows fly visibly and fall under gravity (bible §4.2; All Japan Kyudo Federation).
- **Mounted, left side only.** Yabusame tradition places the targets on the rider's left (弓手) side. The rider opens the knees and rises in the stirrups, with the reins released while shooting (Japanese Wikipedia's 流鏑馬 article, which describes the 鞍まわり posture and the left-side 男埒/女埒 course rails). The campaign's arc of −170° to +15°, the knotted tazuna and the rise in the broad abumi follow bible §4.2. The b08 road is laid out so this is a strength (threats come up from the ravine on the left), and the crossing drone in G4 teaches repositioning instead of an impossible right-side shot.
- **Red fletching** is Nyaakoto's character choice, not a period claim. The arrows are three-fletched (三立羽) and carried in a war 箙.

### 5.4 Architecture, roads and bridges

- **長屋門** is the gate type of early-modern daimyo and samurai residences: a row of retainers' rooms with the gate cut through it. It is plausible for a small house in 1623, and many were built through the Edo period (Japanese Wikipedia, 長屋門).
- **The existing torii-shaped estate gates.** `SM_Nyaagyu_ToriiGate`, on the road at X −22.5 and +23, reads as a **shrine torii**, and torii mark shrine precincts. **Recommendation for C2:** in campaign mode, re-dress them visually as a **冠木門** (kabukimon: two posts and a tie-beam, the simplest residence gate) or a **薬医門** for the inner gate. The alternative is to treat them as the approach to the estate's 屋敷神 shrine, with a small 祠 behind each. Collision does not change.
- **The b08 shrine torii** at chainage 750 m is a real shrine torii, correctly placed at a 鎮守 path, in 丹塗 using the existing `ToriiLacquer` material.
- **Stone bridge, not stone arch.** Nagasaki's **眼鏡橋**, built in **1634**, is regarded as Japan's oldest stone arch bridge. A stone arch in 1623 Yamato would be an anachronism, so the Stone Bridge is a **granite slab-beam bridge** (石桁橋). This refines the bible's "arch or slab" (§15.2) to slab only.
- **Road paving.** The famous Hakone stone paving was laid in **1680**, 2 間 (about 3.6 m) wide; before that the road was bamboo matting laid against the mud. The highway therefore takes 2 間 as its width reference but is **packed earth and gravel**, with stones only on steep pitches and in the cutting. This softens the bible's "stone-paved forest road," is flagged for the historian, and avoids presenting an Edo-era 石畳 as the norm in 1623.
- **Roadside furniture:**
  - Stone 石仏 (Jizō) and votive 石灯籠 at shrine paths are consistent with the period.
  - Signposts are **wooden** 道しるべ; carved stone 道標 are mostly later.
  - There are no 一里塚 milestone mounds, which were a feature of the main shogunal highways.
- **Alarm bell:** the 半鐘 hangs in a timber bell frame by the gate, **not** on a 火の見櫓 fire-watch tower (post-1657 urbanism; bible §19). The 法螺貝 conch is a period signal.
- **Field defenses:**
  - 竹束 (bamboo-bundle mantlets) were used against matchlock fire from the Sengoku period into the Edo period.
  - 篝火 iron braziers are also period.
- **Tea hut:** a small wabi 茶室 with a 躙口 crawl-in entrance and a sunken 炉 hearth fits early-17th-century tea practice. The **肩衝茶入** (katatsuki, "square-shouldered" tea caddy) was among the most prized utensil types of the Momoyama and early Edo periods, so it is a fitting heirloom. Its name, 銘「猫柳」 ("Pussy Willow"), is fictional; it is a quiet echo of 猫柳生, not a joke beat.
- **Kura:** 土蔵 with lime 漆喰 over a timber frame (existing asset). Do not add the diamond-tile 海鼠壁 cladding as a hero feature.
- **Valley:** 炭焼き小屋 charcoal-burners' huts, a 炭窯 kiln and a 丸木橋 log bridge are appropriate for a Yamato upland valley.

### 5.5 Horses, tack and loads

- **Kurimaru** is a native mare about 130 cm at the withers, chestnut (栗毛) and unshod. The size reference is the last purebred Kiso horse, recorded at 132 cm (Nagoya University Museum). Her tack is the bible §4.5 list:
  - kura (a four-piece wooden tree with lacing)
  - 肌付 / 切付 pads (to verify)
  - 障泥 aori
  - 腹帯 girth
  - 力革
  - 舌長鐙 / 鳩胸鐙 abumi with the SORA mon on the front plate
  - 轡, 面繋, 胸繋
  - 鞦 crupper with mon fittings
  - cloth 手綱
  
  Straw 馬沓 are not needed for one night's ride.
- **Pack horses and loads.** The bible's "carts" become **pack horses** in this chapter. Wheeled freight was marginal on upland Yamato roads, and horse-drawn carts were not used in Edo Japan.
  - A standard rice bale weighed about **60 kg** (the shogunate's 3 斗 7 升 bale).
  - A 本馬 post horse could carry up to **40 貫 (about 150 kg)**.
  - So each seed horse takes **two bales, one 駄**, slung either side of a **荷鞍** pack saddle (振り分け).
  - The groom rides **乗掛** on the lead horse: a rider seated on a futon over a light load of about 20 貫 or less, which here is the three 叺 sacks of rice and the spare ebira.
  - The three horses are tied nose to tail, a normal way to move a pack string. That is also why one net stops them all.
- **Gait:** the travel gait at 450 cm/s is a hurried trot. The lateral 側対歩 amble noted in bible §4.5 needs an equine animator's check.
- **Flags:** mounted archery, horse fear and nets are game systems. The saddle and tack study (`Content/SourceArt/Horses/Nyaagyu`) remains stylized and needs the review in `docs/historical-horse-tack-art-reference.md`.

### 5.6 Clothing and armor

- **Nyaakoto:** a hasty 着具 in b01 puts him in 当世具足: 胴, 袖, 籠手, 臑当 and 佩楯, with 紺糸威 (dark-blue lacing) and 朱漆 (vermillion lacquer) plates, over 小袖 and 袴 (bible §4.6).
  - **He wears a 鉢金 (forehead-plate headband) instead of a kabuto in ch02.** That keeps his face and ears readable in cinematics and is plausible for armor put on in minutes. A full kabuto can appear in ch08.
  - The **first-person 籠手** (blue lacing and vermillion plates) are the visible sign of the change from ch01's keikogi.
- **Pupils:** keikogi and hakama with 襷 and 鉢巻 and their own daishō. Takemaru has one 籠手. They are unarmored because they were caught at dusk practice.
- **Sekireisai:** a 十徳 over kimono. After surrendering his swords he wears no daishō, which is visually important.
- **Kohagi:** indigo peddler's clothes, 手甲, 脚絆, a 菅笠 slung on her back and a hidden short blade. **Not** the theatrical black ninja suit (bible §19).
- **Groom:** a short kimono tucked up (尻端折り), 股引, 脚絆, 草鞋 and a 手拭い. Avoid the 18th-century 半纏 and 腹掛 look.
- **Villagers:** 小袖 with 前掛け; children in 小袖 and narrow 帯; elders in 十徳 or 袖無し.
- **Tetsugorō:** a work 小袖 with 襷, a leather apron and burn-scarred paws.

### 5.7 Agriculture

- **Nursery timing.** Seed rice (種籾) is soaked and sown into 苗代 nurseries. The seedlings grow for about **a month** before transplanting (MAFF, 苗つくりの歴史).
- **What that means for the story.** A late-spring seizure of the estate's seed stock threatens the early-summer planting of ch04. That is the literal sense of 「種は明日の田じゃ」.
- **Food vs. seed.** The food handed out in b11 is **separate** hulled rice (three 叺 of about 2 升 each). Nyaakoto's order not to touch the seed is agronomically correct.

### 5.8 Avoid list for ch02

- 招き猫 anywhere, including the tea hut and kitchen.
- A stone arch bridge.
- A continuous 石畳 highway.
- Horse-drawn carts and the later 大八車 handcart.
- A 火の見櫓.
- 半纏-style workwear.
- A kabuto with cut-out cat ears as a hero asset (do not improvise one; if a kabuto is needed later, design it with the historian).
- Modern 組太鼓 ensemble drumming in the score.
- The SORA mon on any alien object.

### 5.9 SORA kamon in ch02

Source: the exact user SVG (`Content/SourceArt/UI/sora_logo_NOtext2.svg`), imported from its two original paths and never redrawn (bible §17; `docs/sora-kamon-runtime-art.md`).

| Surface | Treatment | Beats | Asset status |
|---|---|---|---|
| Estate gate frames, lintel | Existing exact-SVG relief on `SM_Nyaagyu_ToriiGate` | b01–b06, b14–b15 | Existing source (see the §5.4 form recommendation) |
| Kura plaques | The house mon on the provision kura. **The debt seal clamps over it; prying the seal off shows it again** (b05) | b01, b05 | Mon: existing (`SM_Nyaagyu_ProvisionKura`). Seal: needed |
| Roof end tiles | 軒丸瓦 with the raised ceramic mon (`NyaagyuSoraEaveCapStudy`) | All estate beats | Source-only study |
| Nyaakoto's armor | Sode and dō (existing runtime placements: chest, waist, two sode) | From b01 | Existing runtime skin; the photoreal pass is pending (B5) |
| Kurimaru | Abumi front plates (Met 2008.120 placement); crupper fittings | b07–b13 | Abumi and saddlecloth mon: existing study. Crupper fittings: needed |
| Seed bales | Wooden 荷札 tags branded with the mon (foreshadowing ch05's branded 割符) | b05–b11 | Needed |
| Cover crates | Existing SORA crate stamp on `SM_Nyaagyu_CargoStack` | Estate | Existing source |
| House curtain (幕) | 染め抜き white-on-indigo mon. Seen on the dojo in b01; salvaged, **singed and half-burned**, hung behind the valley workshop in b16. The League takes it up in ch03 | b01, b16 | Needed |
| Valley-mouth mark | Charcoal mon on a boulder, the first "League mark" (c05) | b10 | Needed (decal) |
| UI | Chapter title card with the vermillion 朱印 mon seal beside brush calligraphy; small-mon objective marker; slowly rotating mon save indicator; registry page seal | All | L4 (existing SVG) |

**Alien iconography.** The "ledger sigil" is a closed ring of tally notches (bible §17). It appears on the seal clamps, pods, drones, barriers, the scan gate, Dunark's helmet and ledger plate, and the lift column. It must not resemble the SORA mon or any real bank mark, and aliens never display the SORA mon.

### 5.10 Sources

- 長崎県の文化財「日本最古の石造りアーチ橋」(眼鏡橋, 寛永11年/1634): <https://www.pref.nagasaki.jp/bunkadb/index.php/view/10>; 長崎市 文化財課「眼鏡橋」: <https://www.city.nagasaki.lg.jp/page/1245.html>
- 文化庁 日本遺産ポータル「箱根旧街道（石畳）」: <https://japan-heritage.bunka.go.jp/ja/culturalproperties/result/3884/>; 箱根町観光協会「旧街道石畳」(延宝8年/1680, 2間幅): <https://www.hakone.or.jp/6316>
- 古文書ネット「駄馬の種類と積載量」(本馬 40貫, 乗掛 20貫 + 人, 軽尻, 駄荷): <https://komonjyo.net/dabanosyurui.html>
- 国税庁 税務大学校「年貢の米俵をめぐる雑税」(3斗7升俵 ≈ 60 kg): <https://www.nta.go.jp/about/organization/ntc/sozei/quiz/2208/index.htm>
- 農林水産省「苗つくりの歴史」: <https://www.maff.go.jp/j/kids/rice_history/stage2.html>
- 流鏑馬 (Japanese Wikipedia; the left-side course rails and the 鞍まわり posture): <https://ja.wikipedia.org/wiki/流鏑馬>
- 竹束 (Japanese Wikipedia): <https://ja.wikipedia.org/wiki/竹束>; NDL レファレンス協同データベース (竹束): <https://crd.ndl.go.jp/reference/detail?page=ref_view&id=1000060521>
- 長屋門 (Japanese Wikipedia): <https://ja.wikipedia.org/wiki/長屋門>; 門の格式と冠木門・薬医門 (JIA東海「木割の話 第2回」): <https://jia-tokai.org/archive/sibu/architect/2008/05/kiwari.html>
- British Museum OA+.7199 (suyari): <https://www.britishmuseum.org/collection/object/A_OA-7199>; The Met 27609 (foot yari): <https://www.metmuseum.org/art/collection/search/27609>
- All Japan Kyudo Federation 射法: <https://www.kyudo.jp/howto/syaho.html>
- The Met saddle and abumi records 2000.405, 2008.120.1–2 and 2016.205a–b, and the Nagoya University Museum's Kiso horse (132 cm), as collected in `docs/historical-horse-tack-art-reference.md` and `Content/SourceArt/Horses/Nyaagyu/README.md`

---

## 6. Art and audio asset list

**Status key:**

- **Existing (source):** a project-owned source asset exists under `Content/SourceArt` (the asset paths in the tables below are relative to it) or in `catalog.json`. Runtime admission still needs the photoreal gates (packaged A/B comparison, recorded license, frame cost on both platforms; `docs/art-direction/photoreal-acceptance.md`).
- **Existing (study):** a source-only study that is not approved for runtime.
- **Needed:** does not exist.

Licenses: project-owned or CC0 (Poly Haven) as recorded in each manifest. No paid assets.

### 6.1 Environments and set dressing

| Asset | Used in | Status | Notes |
|---|---|---|---|
| Estate mesh terrain, HI and MAC tiers | pl_estate_night | Existing (source): `Environment/NyaagyuTerrain` | Night and wet-edge variant material only |
| Stone route, road-scan variation | Estate | Existing (source): `Environment/NyaagyuHeroPath`, `NyaagyuTerrain/GreyStonePath` | — |
| Estate wall modules (土塀) | Estate, armory yard | Existing (source): `Environment/NyaagyuEstateWall` | Needs a charred and collapsed variant for the yard breach |
| Dojo hall (six instances; the dojo, main house and guest hall roles) | Estate | Existing (source): `Environment/NyaagyuDojo` (+ `LumenModules`) | Needed: fire-damaged 庇 and veranda variant, a burning-roof VFX anchor set and the Takemaru beam |
| Provision kura ×4 | Estate | Existing (source): `Environment/NyaagyuKura`; `NyaagyuKuraFront` door candidate (study) | Check the door yaw faces the road (KuraFront README). Needed: seal-clamp socket |
| Kawara roof and SORA eave caps | Estate | Existing (study): `NyaagyuKawaraBay`, `NyaagyuSoraEaveCapStudy` | — |
| Roji ground variant, roadside leaf silt, pines, ferns | Estate, highway | Existing (source): `NyaagyuIntegratedRoji`, `NyaagyuGroundDressing`, Poly Haven `PineSaplingSmall`, `Fern02` | Fern contact still fails its gate (`docs/art-direction/photoreal-acceptance.md`) |
| Cargo-stack cover with SORA stamp | Estate | Existing (source): `Environment/NyaagyuCargoStack` | — |
| Lacquered estate gate frames | Estate | Existing (source): `Environment/Original/SM_Nyaagyu_ToriiGate` | See the §5.4 kabukimon recommendation |
| Street lantern post | Gate yard | Existing (source): `Environment/Original/SM_Edo_LanternPost` | Optional |
| Poly Haven CC0 palette (plaster, planks, stone, roof tiles, mud and leaves, rusty metal, overcast HDRI) | All | Existing (source): `Environment/PolyHaven` | A night HDRI is needed (CC0) |
| 長屋門 gatehouse with 潜り戸, 閂 and breakable leaves | b02 | Needed | Campaign-only; roof ridge firing positions |
| 裏門 and 埋門 wicket gates | b03, b07, b13 | Needed | Campaign-only openings |
| 茶室 tea hut (躙口, 炉, 床の間) | b14 | Needed | Its roji path uses existing ground |
| Gate-yard kit: 竹束 ×2, 長持, 篝火 ×4, bell frame with 半鐘 | b01–b02 | Needed | — |
| Armory yard kit: 武具蔵 exterior, 槍掛け with 12 yari, 鎧櫃, well, woodpile, torch rack | b03 | Needed | The yari reuse the su-yari study mesh |
| 馬繋ぎ tie rail, stable exterior dressing | b05–b07 | Needed | — |
| Forest highway kit: cedar and cypress (photoreal, Nanite on Windows; card LODs on Mac), ravine and stream, 切通し walls, spur vista | b08, b10, b13 | Needed | The largest new kit; C3 |
| Roadside 石仏 group with 覆屋, 石灯籠 pair, shrine torii (丹塗), wooden 道しるべ | b08, b10 | Needed | Torii material: existing `Environment/ToriiLacquer` |
| Ridge road with a 30 m 桟道 plank walkway | b13 | Needed | — |
| Stone Bridge kit: granite slab-beam bridge (4 spans, 3 piers), rocky stream, gravel ford, willows, 6 m granite outcrop | b09 | Needed | Rock scans: existing CC0 `ScanRock01` / `MossyRock` usable as a base |
| Alien checkpoint kit: graphite barriers ×6, scan gate, landed pod with platform | b09 | Needed | Shares the alien material family with `StreetDebtTerminal` (existing source) |
| Hidden Valley: 炭焼き小屋 ×3, 炭窯, 丸木橋, 12 m waterfall, lean-to workshop, plunge pool | b10–b12, b16 | Needed | Water details can borrow from `NyaagyuWaterCourt` (existing source) |

### 6.2 Props

| Asset | Used in | Status |
|---|---|---|
| Debt seal clamp (ledger-sigil ring, emissive numerals, pry-off animation state) | b01, b05 | Needed |
| 種籾俵 bale with branded 荷札 tag | b05–b11 | Needed |
| 叺 straw rice sack | b07, b11 | Needed |
| 荷鞍 pack saddle ×3 with lashings; spare ebira | b05–b11 | Needed (also for ch04 and ch05) |
| Seizure notices (alien print on seized washi) ×2; the dojo's pale name-board outline on the wall | b05, b14 | Needed |
| 肩衝茶入 tea caddy with 仕覆 pouch | b14 | Needed |
| Scroll fragment; estate 出入帳 page; charcoal-mon decal | b14, b09, b10 | Needed |
| Drop pods (falling, landed, open) | b03, b06, b09 | Needed |
| Seizure net and tether | b08 | Needed |
| Seizure field emitter (colliding field); lift column | b15, b16 | Needed |
| Landing ships ×3 (distant silhouettes) | b01, b08, b13, b16 | Needed |
| House 幕 curtain (intact and singed) | b01, b16 | Needed |
| Bellows (吹差鞴 box bellows), anvil, tool chests | b16 | Needed |

### 6.3 Characters

| Character | Status | Notes |
|---|---|---|
| Nyaakoto, ch02 armored look (紺糸威, 朱漆, 鉢金) | Existing (source): `Characters/Hero`, runtime skin `SK_NyaagyuSamurai` with SORA placements | The photoreal face and coat gates have failed (B5). Needed: armor pass and first-person 籠手 |
| First-person paws, katana and yumi grips | Existing (study): `Characters/NyaakotoFirstPersonPaws` | Needed: yari grip, carry pose and mounted draw |
| Sekireisai (十徳; seiza in the field; unarmed) | Needed | Also ch08 |
| Kohagi (indigo peddler) | Needed | Recurring |
| Pupils Matsukichi, Takemaru, Baiō | Needed | One body with three variants |
| Groom | Needed | Also a base for ch04 farmers |
| Village woman, child, elder + about 26 background refugees | Needed | Crowd variants |
| Tetsugorō | Needed | Also in ch01, ch04 and ch05 |
| Val Amort | Needed | Base: existing prototype `SK_AlienBanker.fbx` / `A_AlienBanker_Walk.fbx` in `Content/SourceArt` |
| Dunark (armored duelist, ledger-line helmet, ledger plate, 帳刃) | Needed | — |
| Enforcer family (rifle, shield, grenadier, marksman) and blade retainer | Needed | Same base; hairless skin, no fur grooms (bible §1.4) |
| Inventory drone; shield drone | Needed | — |

### 6.4 Horses and tack

| Asset | Status | Notes |
|---|---|---|
| Kurimaru (chestnut native mare, about 130 cm) with kura, abumi, tazuna and aori | Existing (study): `Horses/Nyaagyu` (static tack study, SORA on the abumi), `Horses/Nyaagyu/RigStudy` (walk study), `Horses/NyaagyuAbumiTazunaStudy` (PBR textures), `Horses/Nyaagyu/AnatomyStudy` | Needed: photoreal sculpt and groom, chestnut coat, full rig, crupper mon fittings, and the tack review (`docs/historical-horse-tack-art-reference.md`) |
| Pack horses ×3 (鹿毛 and 黒鹿毛 variants) with 荷鞍 | Needed | Shares the Kurimaru base |

### 6.5 Weapons

| Weapon | Status | Notes |
|---|---|---|
| Katana (0) | Existing (source): `SM_Nyaagyu_HeroKatana` + `Weapons/HeroKatana/PBR` | Needed: Sekireisai's katana variant with a seizure tag |
| Yumi (18), arrows and ebira | Existing (study): `Weapons/NyaagyuYumi` | Needed: red-fletched arrow mesh and war ebira (verify against the hero reference) |
| Su-yari (19) | Existing (study): `Weapons/NyaagyuYari` (commit a0a8d83; BM OA+.7199 envelope) | Needed: runtime import, `Grip_R`/`Grip_L` sockets, first-person grip and the 石突 contact point |
| Catalog stats 0, 18, 19 | Existing: `Content/Data/catalog.json` (`weapons[0]`, `campaign_weapons` 18 and 19) | Unchanged |
| Dunark's 帳刃 tally blade; enforcer carbine, tower shield, baton, grenade drum, marksman rifle | Needed | Alien material family |

### 6.6 Animation

| Set | Status |
|---|---|
| Nyaakoto: yari thrust (forward, rim thrust, weak inside jab, recovery); seal pry with the 石突; shoulder-carry bale (pick up, walk, put down on 荷鞍, drop to fight); treat horse; revive pupil | Needed |
| Mounted: mount and dismount (ch01), walk / trot / canter / gallop, amble check, reins-knotted left-arc yumi draw with the rise in the abumi and yugaeri, right-side katana cut, forward and right yari thrust, spook sidestep, forced walk on planks | Needed (the horse walk study exists) |
| Pack horses: loaded trot in a tied string, netted struggle, groom riding 乗掛 | Needed |
| Dunark: quick cuts left and right, heavy overhead, thrust lunge, feint tilt, stagger, tally-pause stance, death and ledger-plate break | Needed |
| Enemies: rifle cover and burst, shield advance, bash and turn, grenadier lob, marksman lock and relocate, retainer 420 ms warning, drone net drop | Needed |
| Pupils: combat, downed, revive; Takemaru pinned and freed. Sekireisai: 正座 in the field, lift. Villagers: receive and bow | Needed |

### 6.7 VFX (C8, Niagara)

- **Fire:** burning roof sections (non-colliding), falling embers, volumetric smoke lit from below (emissive cards on Mac), charring decals, and the burning-beam fall with dust.
- **Alien:**
  - seal clamp slam and hum, with numerals flickering out on pry
  - drop-pod trail and impact scar, with an amber landing ring (animated edge decal, distinct from firelight)
  - ship underglow and 8 500 K searchlight cones
  - drone cyan eye, scan cone and net
  - seizure field (a refractive cyan cylinder with ledger numerals)
  - lift column
  - pod hatch glow
  - scan-gate plane
- **Combat:**
  - visible arrow flight with red fletching
  - yari thrust spark on the shield rim
  - Dunark's amber blade edge on the heavy and the thrust-tip flare
  - the tilt tell on the feint (no glow: it must be read)
  - shield-drone barrier disc and its re-index dimming
- **Ambient:** ravine and stream mist, waterfall spray, hoof dust and mud, and dawn god rays. Every flash respects the flash-reduction setting.

### 6.8 SFX (L5; CC0 or original)

- **Estate:** 半鐘 bell, 法螺貝 conch, 閂 bar strain and break, wicket breach, braziers.
- **Alien:**
  - ship descent (sub-bass)
  - seal clamp thunk and hum; seal pry (iron creak and crackle)
  - drop-pod whistle and impact
  - carbine bursts, grenade thump and shell whistle, marksman charge whine
  - drone hum, net launch and net impact
  - scan gate, lift beam, seizure-field hum
  - **Dunark's tally click** (single and double; tempo-locked)
- **Weapons:** steel against alien alloy, yari thrust and shaft, bow creak, release and yugaeri, arrow flight.
- **Horses:** hooves on earth, stone and planks; snorts, whinnies, tack jingle and bit; straw bales and ropes.
- **Fire:** roof crackle, beam collapse.
- **Water:** stream, ford splashes, waterfall.
- **Night forest:** frogs, wind in cedar. **Pre-dawn:** 鶯, and ホトトギス at night.
- **Valley:** charcoal kiln; **the first anvil strikes at dawn** (b16).
- **UI:** 朱印 stamp and brush stroke on the registry page.

### 6.9 Music cues (L5 stem states)

| State id | Beats | Direction |
|---|---|---|
| `ch02_descent` | b01 | Silence broken by the bell and conch; a sustained low cluster; an alien tone that does not resolve |
| `ch02_combat_estate` | b02–b03, b05–b06 | 締太鼓 and 大太鼓 in irregular period-style patterns (not kumi-daiko), 能管 stabs, a low synth pulse for the aliens |
| `ch02_resolve` | b04 | Solo 尺八 phrase under the dialogue |
| `ch02_ride` | b07–b08 | Driving percussion with 篠笛 melody; intensity rises with the drone groups |
| `ch02_combat_bridge` | b09 | Sparse, tense; the floodlight hum sits in the mix |
| `ch02_dawn_quiet` | b10–b11 | 箏 and 尺八; birdsong carries the mix |
| `ch02_dread` | b12 | A low 琵琶 swell |
| `ch02_ride_return` | b13 | Urgent restatement of `ch02_ride` |
| `ch02_estate_burning` | b14 | Fire bed, 箏 tremolo |
| `ch02_boss_dunark` | b15 | **Tempo-locked to Dunark's measures** (P1 about 46 BPM, P2 about 55 BPM, P3 60 BPM in 3/4), so the rhythm itself teaches the fight. Accessibility: the tally clicks stay audible when music volume is 0 |
| `ch02_collateral_lament` | b16 | 尺八 lament; at the dawn cut, the first anvil strikes become the pulse of a restrained resolve theme |

---

## 7. Hand-offs, changes to the bible and open issues

| Owner | Takes from this chapter |
|---|---|
| L1 | Beats and `target_s` (sums to 2 700); the checkpoint pattern (none at b04, b07 or b12); sites 0/1/2 → b05/b11/b16, unchanged from bible §20; unlocks (19 at b03 start; `yari`, `carry`, `mounted_archery`); **proposed speaker ids** (§1.2); **proposed events** (`wave_start`, `pattern`, `ai:*`, `interact_start`/`interact_complete`, `enemy_killed`, `collectible`, `target_hp_below`, and the `cine@`/`intro@`/`outro@` cue times); **proposed fields**: `x_gate_interact` (b05), `x_pickup` (b03), `x_dropoff_capacity`, `x_waves` / `x_seizure` / `x_resupply` on `horseback_ride`, `x_forced_gait_volumes`, `x_hazards`, `x_movement_volumes`; `fail.on` values joined with `\|` mean "any of"; the layout proposal (§8 `x_layout`); collectible mask bits 0–5, chapter-local (global bit = (chapter − 1) × 6 + local index, bible §12.5) |
| L2 | Enemy baselines (§3.2) and the ch02 bark pool (17 lines). The **marobashi extension**: accept the input in the last 400 ms of a `marobashi_eligible` windup. Deterministic deflect rules for Dunark's pause (no randomness). Drone net behavior. Horse fear rules |
| L3 | `boss_dunark` pattern tables, HP, phase thresholds, feint rule and shield drone (§3.3 and YAML `x_boss`) |
| L4 | 15 tutorial prompts; the mounted arc HUD (a left-arc wedge on the reticle); gait and wind meter; a load-seizure timer ring over netted horses; registry page and 朱印 title card |
| L5 | 11 music states, including the tempo-locked boss cue; captioned telegraph barks; SFX list (§6.8) |
| C2 | Campaign-only openings in the Arena 0 walls (practice/MP collision untouched); fire dressing without collision; building roles; the gate-form recommendation (§5.4) |
| C3 | Highway (with ridge road), Stone Bridge, Hidden Valley and armory-yard kits |
| C4 | Mission scripting for all 16 beats and the b14/b15 skip rule |
| C9 | Sequences `LS_ch02_b01_Descent` (120 s), `LS_ch02_b07_BackGate` (60 s), `LS_ch02_b15_DunarkIntro` (about 32 s), `LS_ch02_b15_DunarkOutro` (about 12 s), `LS_ch02_b16_Collateral` (150 s) |

**Changes to the bible (all five confirmed in the C1 review and written into the bible: §3.2, §4.5, §13, §14, §15.2):**

1. **Carts become a tied pack-horse string** with 荷鞍 (§5.5). The field names (`targets[].actor`, `convoy.npcs`) are unchanged.
2. **Stone Bridge:** slab-beam only, not arch (§5.4).
3. **Highway:** packed earth and gravel with paving only on steep pitches, instead of a fully stone-paved road (§5.4).
4. **Estate gate frames:** recommend a visual re-dress (§5.4).
5. **Marobashi against unparryable thrusts:** the rule extension above.

**Open issues:**

- Native review of every line (§4.2).
- Historian and practitioner sign-off on:
  - Sekireisai's surrender staging
  - the pack loads and the 乗掛 usage
  - the hachigane-for-kabuto choice
  - the tea-caddy heirloom
  - the gate form
- Speaker ids are checked against the sibling chapter docs as of this writing: ch01 uses the same `pupil_*` ids, and ch03–ch08 use the same generic `enforcer`, `drone`, `villager` and `child` ids. Collectible id formats still differ between chapters; L1 should normalize them.
- **Telemetry.** A 6.0-minute target for b08 assumes about 1.5 min of halts for nets. If playtests show the string moving without interruption, add a fifth drone to G2 rather than slowing the string.

---

## 8. Machine-readable beat data (YAML)

This mirrors §3–§4 for conversion into `Content/Data/campaign/chapter_02.json` (L1, schema 4).

- Units: centimetres, seconds and degrees unless a key says otherwise.
- Keys prefixed `x_` are not yet in bible §12 and need L1's decision. Lines live in `lines` and prompts in `ui_prompts` (bible §12.5).
- The block was generated from one data source and checked for:
  - the sum of `target_s` (2 700) and the category mix against bible §10
  - checkpoint spacing (≤ 360 s)
  - site order 0 → 1 → 2
  - the unique weapon unlock (19)
  - `horseback_ride.weapons` ⊆ {0, 18, 19}
  - `registry` only on `production_task`
  - every speaker defined
  - ja and en non-empty
  - EN ≤ 17 cps and ≤ 2 × 42 characters
  - JA ≤ 32 characters
  - blocking dialogue ≤ 20 s
  - non-overlapping cinematic cues
  
  It parses as YAML 1.1 (PyYAML 6).

```yaml
chapter: ch02_invasion
schema_target: catalog schema 4 (L1); proposal fields are prefixed x_ (bible §12.5)
map: 0
title_ja: 異星からの侵略
title_en: The Invasion
target_s: 2700
pacing_min: {C: 17.0, E: 2.0, S: 0, P: 9.0, M: 9.5, Cin: 7.5}
unlocked_weapons_at_start: [0, 18]
unlocked_weapons_at_end: [0, 18, 19]
sites:
- {site: 0, beat: ch02.b05, name_ja: 蔵の債務封印}
- {site: 1, beat: ch02.b11, name_ja: 食糧の配給所}
- {site: 2, beat: ch02.b16, name_ja: 屋敷の工房, note: relocated to pl_kakuredani in fiction}
speakers:
- {id: mentor, ja: 師範 石鈴斎, en: Sekireisai, status: existing}
- {id: samurai, ja: ニャーコト, en: Nyaakoto, status: existing}
- {id: scout, ja: 小萩, en: Kohagi, status: existing}
- {id: banker, ja: 大徴収官 ヴァル・アモルト, en: High Collector Val Amort, status: existing}
- {id: gunsmith, ja: 鉄砲鍛冶 鉄五郎, en: Tetsugorō the gunsmith, status: bible}
- {id: boss_dunark, ja: 上陸指揮官 ドゥナーク, en: Landing Commander Dunark, status: bible}
- {id: pupil_matsukichi, ja: 門弟 松吉, en: Matsukichi, status: proposed}
- {id: pupil_takemaru, ja: 門弟 竹丸, en: Takemaru, status: proposed}
- {id: pupil_baio, ja: 門弟 梅翁, en: Baiō, status: proposed}
- {id: groom, ja: 馬子, en: Groom, status: proposed}
- {id: villager, ja: 村人, en: Villager, status: 'shared generic (ch04, ch08)'}
- {id: child, ja: 子ども, en: Child, status: 'shared generic (ch03, ch08)'}
- {id: credit_system, ja: 信用院・告知音声, en: Credit House notice voice, status: proposed here; used by ch03}
- {id: enforcer, ja: 執行局の兵, en: Enforcement Office trooper, status: shared generic (ch03–ch08)}
- {id: drone, ja: 目録, en: Inventory drone, status: shared generic (ch03–ch08)}
beats:
- id: ch02.b01
  type: cinematic
  place: pl_estate_night
  title_ja: 空が裂けた夜
  title_en: The Night the Sky Split
  target_s: 120
  checkpoint: true
  sequence: /Game/Campaign/Ch02/Cinematics/LS_ch02_b01_Descent
  duration_s: 120
  skippable: true
  fallback: camera_blend
  subtitles:
  - {line: ch02.b01.kohagi.001, at_s: 8.0}
  - {line: ch02.b01.sekireisai.002, at_s: 13.0}
  - {line: ch02.b01.kohagi.003, at_s: 16.6}
  - {line: ch02.b01.valamort.004, at_s: 24.0}
  - {line: ch02.b01.valamort.005, at_s: 32.9}
  - {line: ch02.b01.valamort.006, at_s: 41.0}
  - {line: ch02.b01.nyaakoto.007, at_s: 47.1}
  - {line: ch02.b01.sekireisai.008, at_s: 50.0}
  end_state:
    player_transform: ps_gate_yard_start
    equipped: [0, 18]
  music: ch02_descent
- id: ch02.b02
  type: combat_wave
  place: pl_estate_night
  title_ja: 長屋門を守れ
  title_en: Hold the Nagaya Gate
  target_s: 240
  checkpoint: true
  bounds: vol_gate_yard
  max_alive: 4
  target_kind: enemy
  allies:
  - {npc: pupil_matsukichi, role: hold_wicket_side, downable: true, revive_s: 3.0}
  - {npc: pupil_takemaru, role: hold_north_side, downable: true, revive_s: 3.0}
  - {npc: pupil_baio, role: brace_gate_bar, downable: false}
  waves:
  - enemies:
    - {type: enforcer_rifle, count: 3, spawn: sp_nagayamon_roof}
    trigger: start
  - enemies:
    - {type: enforcer_rifle, count: 3, spawn: sp_wicket_breach}
    trigger: prev_cleared
  - enemies:
    - {type: blade_retainer, count: 2, spawn: sp_gate_leaves}
    trigger: prev_cleared
  complete: all_waves_cleared
  music: ch02_combat_estate
  fail: {'on': player_died, to: checkpoint}
  dialogue:
  - 'on': beat_start
    lines: [ch02.b02.sekireisai.001, ch02.b02.nyaakoto.002]
    mode: ambient
  - 'on': alert_state:alert
    lines: [ch02.b02.enforcer.003]
    mode: ambient
  - 'on': ai:flank
    lines: [ch02.b02.enforcer.004]
    mode: ambient
  - 'on': wave_start:2
    lines: [ch02.b02.matsukichi.005]
    mode: ambient
  - 'on': npc_downed:pupil_matsukichi
    lines: [ch02.b02.matsukichi.006]
    mode: ambient
  - 'on': wave_start:3
    lines: [ch02.b02.baio.007, ch02.b02.retainer.008]
    mode: ambient
  - 'on': ai:retreat
    lines: [ch02.b02.enforcer.009]
    mode: ambient
  - 'on': beat_complete
    lines: [ch02.b02.sekireisai.010]
    mode: ambient
- id: ch02.b03
  type: combat_wave
  place: pl_bugugura
  title_ja: 武具蔵の槍
  title_en: Spears from the Armory
  target_s: 180
  checkpoint: true
  unlocks:
    weapons: [19]
    mechanics: [yari]
  x_unlock_at: beat_start
  x_pickup: {actor: rack_suyari_01, interact_s: 0.8, grants_weapon: 19, slot: polearm}
  bounds: vol_bugugura_yard
  max_alive: 4
  target_kind: enemy
  waves:
  - enemies:
    - {type: shield_enforcer, count: 2, spawn: sp_pod_crater}
    - {type: enforcer_rifle, count: 1, spawn: sp_yard_west_breach}
    trigger: start
  - enemies:
    - {type: enforcer_rifle, count: 2, spawn: sp_yard_west_breach}
    trigger: alive_below:2
  complete: all_waves_cleared
  music: ch02_combat_estate
  fail: {'on': player_died, to: checkpoint}
  dialogue:
  - 'on': beat_start
    lines: [ch02.b03.nyaakoto.001]
    mode: ambient
  - 'on': beat_start
    lines: [ch02.b03.sekireisai.002]
    mode: radio
  - 'on': alert_state:alert
    lines: [ch02.b03.shield.003]
    mode: ambient
  - 'on': ai:shield_turned
    lines: [ch02.b03.shield.004]
    mode: ambient
  - 'on': ai:player_inside_polearm_min
    lines: [ch02.b03.sekireisai.005]
    mode: radio
- id: ch02.b04
  type: dialogue
  place: pl_estate_night
  title_ja: 種は明日の田
  title_en: Seed Is Tomorrow's Field
  target_s: 60
  checkpoint: false
  trigger: volume_enter:vol_courtyard_west
  mode: blocking
  camera: soft_lookat
  priority: 10
  interrupt: queue
  lines: [ch02.b04.sekireisai.003, ch02.b04.nyaakoto.004, ch02.b04.sekireisai.005, ch02.b04.nyaakoto.006, ch02.b04.sekireisai.007]
  dialogue:
  - 'on': beat_start
    lines: [ch02.b04.sekireisai.001, ch02.b04.nyaakoto.002]
    mode: ambient
  - 'on': beat_complete
    lines: [ch02.b04.sekireisai.008, ch02.b04.baio.009]
    mode: ambient
  music: ch02_resolve
- id: ch02.b05
  type: production_task
  task: carry
  place: pl_estate_night
  title_ja: 種籾を運び出せ
  title_en: Carry Out the Seed Rice
  target_s: 240
  checkpoint: true
  site: 0
  unlocks:
    mechanics: [carry]
  x_gate_interact:
    interact_points: [seal_kura_sw]
    per_point_s: 3.0
    contest: pause
    tool: yari_ishizuki
    note: hold interact-point shape (§12.2 hold) used as a pre-step
  carry:
    item: tanemomi_hyo
    count: 4
    pickups: [pk_kura_sw_door]
    dropoffs: [pack_horse_a, pack_horse_b]
    x_dropoff_capacity: {pack_horse_a: 2, pack_horse_b: 2}
    loadout_while_carrying: [katana_one_hand]
    move_speed_mult: 0.8
    drop_on_hit: {easy: false, normal: false, hard: true}
  waves:
  - enemies:
    - {type: enforcer_rifle, count: 2, spawn: sp_court_north_veranda}
    trigger: start
  - enemies:
    - {type: enforcer_rifle, count: 1, spawn: sp_west_torii}
    - {type: blade_retainer, count: 1, spawn: sp_west_torii}
    trigger: progress_at:0.5
  registry: {item_ja: 種籾, item_en: Seed rice, qty: 4, unit_ja: 俵, unit_en: bales}
  music: ch02_combat_estate
  fail: {'on': player_died, to: checkpoint}
  dialogue:
  - 'on': beat_start
    lines: [ch02.b05.groom.001]
    mode: ambient
  - 'on': interact_start:seal_kura_sw
    lines: [ch02.b05.system.002]
    mode: ambient
  - 'on': ai:carry_spotted
    lines: [ch02.b05.enforcer.003]
    mode: ambient
  - 'on': progress_at:0.5
    lines: [ch02.b05.groom.004]
    mode: ambient
  - 'on': progress_at:1.0
    lines: [ch02.b05.groom.005]
    mode: ambient
- id: ch02.b06
  type: production_task
  task: defend
  place: pl_estate_night
  title_ja: 荷馬を守れ
  title_en: Protect the Pack Horses
  target_s: 180
  checkpoint: true
  defend:
    targets:
    - {actor: pack_horse_a, hp: 400}
    - {actor: pack_horse_b, hp: 400}
    duration_s: 150
    fail_on_target_destroyed: true
    repair_interact: {kind: treat_horse, hold_s: 2.0, heal: 60, cooldown_s: 20}
  x_hazards:
  - {kind: drop_pod_impact, telegraph: amber_ring, radius_cm: 350, windup_ms: 2500, damage: 60, hits_allies: true}
  max_alive: 6
  waves:
  - enemies:
    - {type: enforcer_rifle, count: 3, spawn: sp_pod_a_road}
    trigger: start
  - enemies:
    - {type: enforcer_rifle, count: 2, spawn: sp_pod_b_north}
    - {type: grenadier, count: 1, spawn: sp_pod_b_north}
    trigger: after_s:45
  - enemies:
    - {type: blade_retainer, count: 1, spawn: sp_pod_c_west}
    - {type: enforcer_rifle, count: 2, spawn: sp_pod_c_west}
    trigger: after_s:95
  music: ch02_combat_estate
  fail: {'on': player_died|target_destroyed, to: checkpoint}
  dialogue:
  - 'on': beat_start
    lines: [ch02.b06.kohagi.001]
    mode: ambient
  - 'on': ai:drop_pod_launch
    lines: [ch02.b06.system.002]
    mode: ambient
  - 'on': ai:grenadier_fire
    lines: [ch02.b06.grenadier.003]
    mode: ambient
  - 'on': target_hp_below:any:0.5
    lines: [ch02.b06.groom.004]
    mode: ambient
  - 'on': progress_at:0.5
    lines: [ch02.b06.sekireisai.005]
    mode: radio
  - 'on': beat_complete
    lines: [ch02.b06.kohagi.006]
    mode: ambient
- id: ch02.b07
  type: cinematic
  place: pl_estate_night
  title_ja: 裏門
  title_en: The Back Gate
  target_s: 60
  checkpoint: false
  sequence: /Game/Campaign/Ch02/Cinematics/LS_ch02_b07_BackGate
  duration_s: 60
  skippable: true
  fallback: camera_blend
  subtitles:
  - {line: ch02.b07.kohagi.001, at_s: 9.0}
  - {line: ch02.b07.groom.002, at_s: 18.0}
  - {line: ch02.b07.nyaakoto.003, at_s: 24.0}
  - {line: ch02.b07.nyaakoto.004, at_s: 40.0}
  end_state:
    player_transform: pl_kaido/ps_kaido_ch0000_mounted
    mounted: kurimaru
    equipped: [18]
  music: ch02_ride
- id: ch02.b08
  type: horseback_ride
  mode: escort_convoy
  horse: kurimaru
  place: pl_kaido
  title_ja: 荷駄を守って街道を行け
  title_en: Escort the Pack Train
  target_s: 360
  checkpoint: true
  route: spl_kaido_convoy
  x_route_length_m: 1200
  gaits: [walk, trot, canter, gallop]
  x_gait_speeds_cm_s: {walk: 170, trot: 380, canter: 600, gallop: 850}
  weapons: [0, 18, 19]
  x_arcs_deg:
    '18': [-170, 15]
    '0': [30, 150]
    '19': [-10, 60]
  convoy:
    npcs: [pack_horse_c, pack_horse_a, pack_horse_b]
    riders: {pack_horse_c: 'groom (乗掛: rider on a futon over a light load)'}
    string: tied nose-to-tail; a net on any horse halts the string
    loads: {pack_horse_c: 3 kamasu of rice + spare ebira (24 arrows), pack_horse_a: 2 tanemomi_hyo (一駄), pack_horse_b: 2 tanemomi_hyo
        (一駄)}
    speed_cm_s: 450
    hp: 400
    spacing_cm: 450
    player_slot: left_flank
    halt_when_netted: true
  x_waves:
  - enemies:
    - {type: drone, count: 2, spawn: sp_kaido_g1_left}
    trigger: progress_at:0.10
    behavior: scout_only
  - enemies:
    - {type: drone, count: 3, spawn: sp_kaido_g2_ravine}
    trigger: progress_at:0.33
    behavior: net_convoy
  - enemies:
    - {type: drone, count: 2, spawn: sp_kaido_g3_left}
    trigger: progress_at:0.55
    behavior: net_convoy
    with: ship_searchlight_sweep
  - enemies:
    - {type: drone, count: 3, spawn: sp_kaido_g4_left}
    trigger: progress_at:0.75
    behavior: net_convoy
    one_crosses_right_at_m: 1020
  x_seizure:
    net_windup_ms: 800
    telegraph: cyan_lock_ring
    lift_timer_s: 15
    cut: {mounted_weapon: 0, side: right, dismounted_interact_s: 1.0}
    kill_tether_drone_cancels: true
  fear:
    spook_radius_cm: 900
    recover_s: 2.5
    sources: [searchlight_footprint, net_impact, drone_pass_below_400cm]
  horse_stamina: {max: 100, gallop_drain_per_s: 8, canter_drain_per_s: 2, recover_per_s: 6}
  x_resupply: {actor: pack_horse_c, reserve_arrows: 24, radius_cm: 300, refill_to: 12, cooldown_s: 20}
  auto_steer: setting
  dismount_allowed: true
  on_horse_down: dismount_continue
  unlocks:
    mechanics: [mounted_archery]
  complete: volume_enter:vol_bridge_bend
  fail: {'on': player_died|convoy_member_seized|convoy_member_hp0, to: checkpoint}
  music: ch02_ride
  dialogue:
  - 'on': wave_start:1
    lines: [ch02.b08.drone.001]
    mode: ambient
  - 'on': ai:net_windup
    lines: [ch02.b08.drone.002]
    mode: ambient
  - 'on': ai:convoy_netted
    lines: [ch02.b08.groom.003, ch02.b08.nyaakoto.004]
    mode: ambient
  - 'on': wave_start:3
    lines: [ch02.b08.system.005]
    mode: ambient
  - 'on': ai:horse_spooked:convoy
    lines: [ch02.b08.groom.006]
    mode: ambient
  - 'on': ai:horse_spooked:kurimaru
    lines: [ch02.b08.nyaakoto.007]
    mode: ambient
  - 'on': ai:drone_crossed_right
    lines: [ch02.b08.nyaakoto.008]
    mode: ambient
  - 'on': beat_complete
    lines: [ch02.b08.kohagi.009]
    mode: ambient
- id: ch02.b09
  type: combat_wave
  place: pl_ishibashi
  title_ja: 石橋の関を破れ
  title_en: Break the Stone Bridge Checkpoint
  target_s: 240
  checkpoint: true
  bounds: vol_ishibashi
  max_alive: 6
  target_kind: enemy
  waves:
  - enemies:
    - {type: enforcer_rifle, count: 4, spawn: sp_barrier_line}
    - {type: grenadier, count: 1, spawn: sp_scan_gate}
    - {type: marksman, count: 1, spawn: sp_outcrop_platform}
    trigger: start
  - enemies:
    - {type: enforcer_rifle, count: 2, spawn: sp_far_road_east}
    trigger: alive_below:3
  x_wave2_fallback_trigger: after_s:120
  x_movement_volumes:
  - {volume: vol_ford, move_speed_mult: 0.7, surface: running_water}
  complete: all_waves_cleared
  music: ch02_combat_bridge
  fail: {'on': player_died, to: checkpoint}
  dialogue:
  - 'on': beat_start
    lines: [ch02.b09.nyaakoto.001, ch02.b09.kohagi.002]
    mode: ambient
  - 'on': ai:marksman_lock
    lines: [ch02.b09.marksman.003]
    mode: ambient
  - 'on': alert_state:alert
    lines: [ch02.b09.enforcer.004]
    mode: ambient
  - 'on': alert_state:search
    lines: [ch02.b09.enforcer.005]
    mode: ambient
  - 'on': enemy_killed:marksman
    lines: [ch02.b09.kohagi.006]
    mode: ambient
  - 'on': wave_start:2
    lines: [ch02.b09.enforcer.007]
    mode: ambient
- id: ch02.b10
  type: horseback_ride
  mode: travel
  horse: kurimaru
  place: pl_kaido
  title_ja: 夜明け前の道
  title_en: The Road Before Dawn
  target_s: 120
  checkpoint: true
  route: spl_kaido_dawn
  x_route_length_m: 465
  gaits: [walk, trot]
  weapons: []
  convoy:
    npcs: [pack_horse_c, pack_horse_a, pack_horse_b]
    speed_cm_s: 250
    hp: 400
  x_optional_interacts:
  - {actor: jizo_group_1500, kind: bow, interact_s: 1.5}
  auto_steer: setting
  dismount_allowed: true
  on_horse_down: dismount_continue
  complete: volume_enter:vol_kakuredani_mouth
  music: ch02_dawn_quiet
  dialogue:
  - 'on': beat_start
    lines: [ch02.b10.kohagi.001]
    mode: ambient
  - 'on': progress_at:0.3
    lines: [ch02.b10.groom.002, ch02.b10.nyaakoto.003]
    mode: ambient
  - 'on': interact:jizo_bow
    lines: [ch02.b10.nyaakoto.004]
    mode: ambient
- id: ch02.b11
  type: production_task
  task: carry
  place: pl_kakuredani
  title_ja: 米を配れ
  title_en: Hand Out the Rice
  target_s: 120
  checkpoint: true
  site: 1
  carry:
    item: kamasu_rice
    count: 3
    pickups: [pack_horse_c]
    dropoffs: [shelter_1, shelter_2, shelter_3]
    loadout_while_carrying: [katana_one_hand]
    move_speed_mult: 0.8
    drop_on_hit: false
  registry: {item_ja: 食糧, item_en: Food, qty: 36, unit_ja: 食, unit_en: meals}
  music: ch02_dawn_quiet
  dialogue:
  - 'on': item_delivered:shelter_1
    lines: [ch02.b11.villager.001]
    mode: ambient
  - 'on': item_delivered:shelter_2
    lines: [ch02.b11.child.002, ch02.b11.nyaakoto.003]
    mode: ambient
  - 'on': site_restored:1
    lines: [ch02.b11.nyaakoto.004]
    mode: ambient
- id: ch02.b12
  type: dialogue
  place: pl_kakuredani
  title_ja: 屋敷が燃えている
  title_en: The Estate Is Burning
  target_s: 60
  checkpoint: false
  trigger: volume_enter:vol_kohagi_arrives
  mode: blocking
  camera: soft_lookat
  priority: 10
  interrupt: cut
  lines: [ch02.b12.kohagi.001, ch02.b12.nyaakoto.002, ch02.b12.kohagi.003, ch02.b12.kohagi.004, ch02.b12.nyaakoto.005]
  music: ch02_dread
- id: ch02.b13
  type: horseback_ride
  mode: travel
  horse: kurimaru
  place: pl_kaido
  title_ja: 尾根道を駆け戻れ
  title_en: Ride Back by the Ridge Road
  target_s: 90
  checkpoint: true
  route: spl_onemichi
  x_route_length_m: 750
  gaits: [trot, canter, gallop]
  weapons: []
  horse_stamina: {max: 100, gallop_drain_per_s: 4, canter_drain_per_s: 0, recover_per_s: 6}
  x_forced_gait_volumes:
  - {volume: vol_sando_planks, gait: walk, length_m: 30}
  auto_steer: setting
  dismount_allowed: false
  on_horse_down: checkpoint
  complete: volume_enter:vol_back_gate
  music: ch02_ride_return
  dialogue:
  - 'on': beat_start
    lines: [ch02.b13.nyaakoto.001]
    mode: ambient
  - 'on': progress_at:0.6
    lines: [ch02.b13.system.002]
    mode: ambient
- id: ch02.b14
  type: explore_optional
  place: pl_estate_night
  title_ja: 燃える屋敷
  title_en: The Burning Wings
  target_s: 120
  checkpoint: true
  optional: true
  requires: [ch02.b13]
  volume: vol_burning_wings
  pois:
  - {id: poi_takemaru, kind: npc, interact: beam_takemaru, interact_s: 2.0}
  - {id: poi_dojo_pillar_notice, kind: lore, collectible: ch02.c03}
  - {id: poi_dojo_veranda_scroll, kind: lore, collectible: ch02.c01}
  - {id: poi_chashitsu, kind: cache, collectible: ch02.c04}
  - {id: poi_ember_arrows, kind: cache, reward: arrows_refill_12}
  rewards: [ch02.c01, ch02.c03, ch02.c04, arrows_refill_12]
  x_hazards:
  - {kind: fire_volume, damage_per_s: 8, telegraph: visible_flame+amber_edge_decal}
  exit_hint_after_s: 90
  x_exit_hint: 'audio: Dunark''s tally-clicks and the seizure-field hum from the courtyard'
  x_skip_rule: entering vol_boss_courtyard starts ch02.b15; b14 is then marked skipped
  music: ch02_estate_burning
  dialogue:
  - 'on': volume_enter:vol_dojo_east_veranda
    lines: [ch02.b14.takemaru.001]
    mode: ambient
  - 'on': interact_complete:beam_takemaru
    lines: [ch02.b14.takemaru.002, ch02.b14.nyaakoto.003]
    mode: ambient
  - 'on': collectible:ch02.c03
    lines: [ch02.b14.nyaakoto.004]
    mode: ambient
- id: ch02.b15
  type: boss
  boss: boss_dunark
  place: pl_estate_night
  title_ja: 上陸指揮官ドゥナークを討て
  title_en: Defeat Landing Commander Dunark
  target_s: 360
  checkpoint: true
  requires: [ch02.b13]
  trigger: volume_enter:vol_boss_courtyard
  arena: {volume: vol_boss_courtyard, lock: true}
  intro_cinematic: /Game/Campaign/Ch02/Cinematics/LS_ch02_b15_DunarkIntro
  outro_cinematic: /Game/Campaign/Ch02/Cinematics/LS_ch02_b15_DunarkOutro
  phases:
  - {hp_pct_start: 100, pattern_table: dunark_p1_notice}
  - {hp_pct_start: 60, pattern_table: dunark_p2_notice, arena_mod: beam_fall_nw}
  - {hp_pct_start: 25, pattern_table: dunark_p3_final, adds: shield_drone_1}
  checkpoint_per_phase: true
  defeat: kill
  telegraph: {palette: standard, min_windup_ms: 500}
  barks:
  - {'on': 'boss_phase:1', line: ch02.b15.dunark.005}
  - {'on': 'boss_phase:2', line: ch02.b15.dunark.007}
  - {'on': 'pattern:thrust', line: ch02.b15.dunark.008}
  - {'on': 'boss_phase:3', line: ch02.b15.dunark.010}
  - {'on': 'pattern:shield_drone', line: ch02.b15.dunark.011}
  - {'on': 'pattern:stagger', line: ch02.b15.dunark.013}
  music: ch02_boss_dunark
  fail: {'on': player_died, to: phase_checkpoint}
  dialogue:
  - 'on': intro@6.0
    lines: [ch02.b15.dunark.001]
    mode: cinematic
  - 'on': intro@13.8
    lines: [ch02.b15.dunark.002]
    mode: cinematic
  - 'on': intro@19.9
    lines: [ch02.b15.nyaakoto.003]
    mode: cinematic
  - 'on': intro@24.5
    lines: [ch02.b15.dunark.004]
    mode: cinematic
  - 'on': boss_phase:1
    lines: [ch02.b15.dunark.005, ch02.b15.sekireisai.006]
    mode: ambient
  - 'on': boss_phase:2
    lines: [ch02.b15.dunark.007, ch02.b15.sekireisai.009]
    mode: ambient
  - 'on': pattern:thrust
    lines: [ch02.b15.dunark.008]
    mode: ambient
  - 'on': boss_phase:3
    lines: [ch02.b15.dunark.010, ch02.b15.sekireisai.012]
    mode: ambient
  - 'on': pattern:shield_drone
    lines: [ch02.b15.dunark.011]
    mode: ambient
  - 'on': pattern:stagger
    lines: [ch02.b15.dunark.013]
    mode: ambient
  - 'on': player_died
    lines: [ch02.b15.sekireisai.014]
    mode: ambient
  - 'on': outro@3.0
    lines: [ch02.b15.dunark.015]
    mode: cinematic
- id: ch02.b16
  type: cinematic
  place: pl_estate_night
  title_ja: 担保
  title_en: Collateral
  target_s: 150
  checkpoint: true
  site: 2
  sequence: /Game/Campaign/Ch02/Cinematics/LS_ch02_b16_Collateral
  duration_s: 150
  skippable: true
  fallback: camera_blend
  subtitles:
  - {line: ch02.b16.valamort.001, at_s: 14.0}
  - {line: ch02.b16.valamort.002, at_s: 21.0}
  - {line: ch02.b16.valamort.003, at_s: 28.0}
  - {line: ch02.b16.nyaakoto.004, at_s: 37.3}
  - {line: ch02.b16.sekireisai.005, at_s: 39.0}
  - {line: ch02.b16.nyaakoto.006, at_s: 43.2}
  - {line: ch02.b16.sekireisai.007, at_s: 46.0}
  - {line: ch02.b16.valamort.008, at_s: 52.0}
  - {line: ch02.b16.tetsugoro.009, at_s: 82.0}
  - {line: ch02.b16.nyaakoto.010, at_s: 95.0}
  - {line: ch02.b16.baio.011, at_s: 101.0}
  - {line: ch02.b16.nyaakoto.012, at_s: 108.0}
  - {line: ch02.b16.baio.013, at_s: 110.2}
  - {line: ch02.b16.baio.014, at_s: 118.0}
  - {line: ch02.b16.nyaakoto.015, at_s: 128.0}
  x_site_note: site 2 (屋敷の工房) is restored at the dawn cut, relocated to pl_kakuredani in fiction
  end_state:
    player_transform: pl_kakuredani/ps_workshop_lean_to
    equipped: [0, 18, 19]
    then: chapter_complete_registry_page
  music: ch02_collateral_lament
collectibles:
- collectible_id: ch02.c01
  category: scroll_fragment
  place: pl_estate_night
  mask_bit: 0
  actor: col_dojo_veranda_scroll
  found_in: ch02.b14
  codex: {ja: 伝書の断簡（二）――「刀を抜くは易し。納むるは難し。」石鈴斎の筆。端が焦げている。, en: 'Scroll fragment II: "Drawing the sword is easy. Sheathing it
      is hard." In Sekireisai''s hand; the edge is scorched.'}
- collectible_id: ch02.c02
  category: seizure_notice
  place: pl_estate_night
  mask_bit: 1
  actor: col_kura_sw_notice
  found_in: ch02.b05
  codex: {ja: 差押状――猫柳生家 蔵 壱番。種籾 四俵 ほか一式。担保として保全。異議の申立ては延滞とみなす。, en: 'Seizure notice: House Nyaagyu, Granary No. 1. Seed rice,
      four bales, and all contents. Held as collateral. Objections count as delinquency.'}
- collectible_id: ch02.c03
  category: seizure_notice
  place: pl_estate_night
  mask_bit: 2
  actor: col_dojo_pillar_notice
  found_in: ch02.b14
  codex: {ja: 差押状――爪木坂道場。名札掛け 一式、刀掛け 三基、木刀 四十振。評価額は後日通知。, en: 'Seizure notice: Tsumagizaka Dōjō. One name board, three sword
      racks, forty bokutō. Valuation to follow.'}
- collectible_id: ch02.c04
  category: heirloom
  place: pl_estate_night
  mask_bit: 3
  actor: col_chashitsu_chaire
  found_in: ch02.b14
  codex: {ja: 家宝：肩衝茶入 銘「猫柳」。石鈴斎が茶室の炉脇に置いていた。仕覆（袋）ごと煤けている。, en: 'Heirloom: katatsuki tea caddy named "Pussy Willow." Sekireisai
      kept it by the tea-room hearth; its silk pouch is sooted.'}
- collectible_id: ch02.c05
  category: league_mark
  place: pl_kakuredani
  mask_bit: 4
  actor: col_valley_mouth_mark
  found_in: ch02.b10
  codex: {ja: 空紋の目印（最初の一つ）――谷口の岩に炭で描かれた空紋。梅翁が逃げる者の道しるべに描いた。, en: 'League mark, the first: the SORA mon drawn in charcoal on
      a rock at the valley mouth. Baiō drew it to guide those fleeing.'}
- collectible_id: ch02.c06
  category: registry_page
  place: pl_ishibashi
  mask_bit: 5
  actor: col_checkpoint_seized_docs
  found_in: ch02.b09
  codex: {ja: 生産の記録：猫柳生家の蔵の出入帳、元和八年の頁。収めた俵と出した俵が、一俵の狂いもなく並ぶ。, en: 'Registry page: the estate granary''s in-and-out book, Genna
      8. Bales stored and bales issued, every one accounted for.'}
x_boss:
  id: boss_dunark
  hp_normal: 1400
  difficulty_windup_scale: {easy: 1.3, normal: 1.0, hard: 0.85}
  stagger_damage_mult: 1.25
  flank_damage_mult: 1.5
  pattern_tables:
    dunark_p1_notice:
      beat_ms: 1300
      measure: [quick_cut, quick_cut, heavy_overhead]
      pause_ms: 1500
      attacks:
        quick_cut: {windup_ms: 500, active_ms: 120, recovery_ms: 350, damage: 18, telegraph: blade_raise+tally_click, on_awase: measure_reset,
          guard_stamina: 12}
        heavy_overhead: {windup_ms: 900, active_ms: 150, recovery_ms: 1100, damage: 45, telegraph: amber_blade_edge+double_click,
          on_awase: stagger_1200ms, guard_chip: 12, guard_stamina: 40}
      pause_rule: frontal arrows deflected; arrows from > 45 deg off his facing and yari thrusts land
    dunark_p2_notice:
      beat_ms: 1100
      measures:
        A: [quick_cut, quick_cut, heavy_overhead]
        B: [quick_cut, thrust, heavy_overhead]
      sequence: [B, A, B, B]
      pause_ms: 1200
      attacks:
        thrust: {windup_ms: 700, active_ms: 150, recovery_ms: 900, damage: 40, lunge_cm: 400, parryable: false, guard_chip: 20,
          guard_break: true, telegraph: amber_tip_flare+bark, bark: ch02.b15.dunark.008, marobashi_window_ms: 400, turn_lag_ms: 800}
      arena_mod:
        beam_fall_nw: {volume: vol_fire_nw_p2, damage_per_s: 8, at: phase_start, telegraph_ms: 1500}
    dunark_p3_final:
      beat_ms: 1000
      measures:
        C: [quick_cut, heavy_or_feint, quick_cut]
        B: [quick_cut, thrust, heavy_overhead]
      sequence: [C, C, B]
      pause_ms: 1000
      feint_rule: 'every 2nd heavy is a feint (deterministic): blade tilts 15 deg, edge turned out, left shoulder does not
        drop; after the 900 ms windup he holds 400 ms then a quick_cut (500 ms)'
      adds:
        shield_drone_1: {hp: 40, orbit_radius_cm: 300, blocks: arrows toward Dunark, reindex_every_s: 8, reindex_window_ms: 1200,
          window_after_block_ms: 1200, respawn: false, bark: ch02.b15.dunark.011}
  checkpoint_per_phase: true
  defeat: kill; outro cuts his ledger-plate through
x_enemy_baseline:
  enforcer_rifle: {hp: 100, weapon: levy carbine, burst: '3 rounds x 9 dmg, 350 ms apart', tell: 600 ms shoulder-and-stock
      raise, misses: 'fixed pattern hit/miss/hit (W0.4), never random'}
  blade_retainer: {hp: 120, cut_damage: 22, warning_ms: 420, rule: fixed-direction warning; withdraws when crowded (existing)}
  shield_enforcer:
    hp: 160
    front_block_deg: 120
    baton: {windup_ms: 600, damage: 16}
    bash: {windup_ms: 450, damage: 10, knockback_cm: 150}
    edge_thrust: 'yari thrust to the shield rim: shield turns, 1000 ms opening'
  grenadier:
    hp: 110
    shell: {damage: 35, radius_cm: 300, arc_decal_ms: 1400, interval_s: 6}
  marksman: {hp: 80, lock_ms: 900, lock_telegraph: cyan glint + laser line, damage: 40, relocate_after_shots: 2}
  drone:
    hp: 40
    net: {windup_ms: 800, telegraph: cyan lock ring}
    scan: cyan cone marks target
    note: one yumi arrow (52) destroys
x_layout:
  pl_estate_night:
    source: Arena 0 (Nyaagyu Estate) + campaign-only sublevels; world cm, arena axes as built by SoraWorldBuilder
    practice_mp_collision_unchanged: true
    campaign_only_openings:
    - id: opening_nagayamon
      wall: west (X=-3150)
      y_range_cm: [-180, 180]
      note: gate leaves; closed until wave 3
    - id: opening_wicket_west
      wall: west (X=-3150)
      y_range_cm: [-500, -400]
      note: 潜り戸, breached at wave 2
    - id: opening_bugugura_wicket
      wall: north (Y=+2550)
      x_range_cm: [-1060, -940]
      note: 埋門 to pl_bugugura
    - id: opening_back_gate
      wall: east (X=+3150)
      y_range_cm: [-180, 180]
      note: 裏門; cinematic and b13 arrival only
    volumes:
      vol_gate_yard:
        center_cm: [-2475, 0, 400]
        size_cm: [1350, 2600, 800]
      vol_courtyard_west:
        center_cm: [-1600, 0, 200]
        size_cm: [1200, 1000, 400]
      vol_kura_front:
        center_cm: [0, -1150, 200]
        size_cm: [3200, 700, 400]
      vol_kura_sw_door:
        center_cm: [-1000, -1400, 150]
        size_cm: [400, 200, 300]
      vol_back_gate:
        center_cm: [2900, 0, 200]
        size_cm: [500, 800, 400]
      vol_burning_wings:
        center_cm: [0, 1750, 300]
        size_cm: [6200, 1500, 600]
        exclude: building footprints
      vol_dojo_east_veranda:
        center_cm: [500, 1800, 150]
        size_cm: [350, 700, 300]
      vol_boss_courtyard:
        center_cm: [100, 0, 400]
        size_cm: [2600, 2200, 800]
      vol_fire_nw_p2:
        center_cm: [-900, 800, 150]
        size_cm: [600, 600, 300]
      vol_seizure_field:
        center_cm: [0, 1300, 150]
        size_cm: [300, 300, 400]
        collides: true
    spawns:
      ps_gate_yard_start: [-2300, 0, 0]
      sp_nagayamon_roof:
      - [-3450, -600, 550]
      - [-3450, 0, 600]
      - [-3450, 600, 550]
      sp_wicket_breach: [-3450, -450, 0]
      sp_gate_leaves: [-3450, 0, 0]
      sp_court_north_veranda:
      - [-500, 1350, 0]
      - [500, 1350, 0]
      sp_west_torii: [-2250, 0, 0]
      sp_pod_a_road: [-200, 200, 0]
      sp_pod_b_north: [-600, 1100, 0]
      sp_pod_c_west: [-1900, -300, 0]
      pk_kura_sw_door: [-1000, -1420, 0]
      pack_horse_a: [800, -1050, 0]
      pack_horse_b: [1200, -1050, 0]
      ally_matsukichi: [-2700, -450, 0]
      ally_takemaru: [-2700, 450, 0]
      ally_baio: [-3050, 0, 0]
      mentor_seizure_field: [0, 1300, 0]
      col_kura_sw_notice: [-1150, -1440, 160]
      col_dojo_pillar_notice: [-300, 1440, 170]
      col_dojo_veranda_scroll: [250, 1500, 60]
      col_chashitsu_chaire: [2750, 1900, 40]
      beam_takemaru: [520, 1750, 0]
  pl_bugugura:
    source: estate sublevel north of the arena wall; local cm, origin = wicket centre at arena (-1000, 2550), same axes
    size_m: [18, 14]
    volumes:
      vol_bugugura_yard:
        center_cm: [0, 700, 400]
        size_cm: [1800, 1400, 800]
      vol_spear_rack:
        center_cm: [-250, 80, 150]
        size_cm: [200, 120, 300]
    spawns:
      rack_suyari_01: [-250, 60, 0]
      sp_pod_crater: [-300, 650, 0]
      sp_yard_west_breach: [-900, 700, 0]
    cover:
      well: [450, 500]
      woodpile: [650, 1000]
      armor_chests:
      - [-600, 350]
      - [-650, 450]
      taketaba_rack: [200, 1250]
      pod: [-300, 650]
  pl_kaido:
    source: new linear level (~1.5 km) + 750 m ridge-road branch; chainage in metres from the estate back gate
    road: {width_m: 3.6, surface: packed earth + gravel; stone paving only on grades > 8% and in the cutting}
    splines:
      spl_kaido_convoy: {from_m: 0, to_m: 1200}
      spl_kaido_dawn: {from_m: 1215, to_m: 1500, then: valley trail 180 m}
      spl_onemichi: {length_m: 750, from: pl_kakuredani ridge trailhead, to: estate back gate}
    spawns:
      sp_kaido_g1_left:
        chainage_m: 180
        offset_m: [-35, 12]
      sp_kaido_g2_ravine:
        chainage_m: 460
        offset_m: [-25, -20]
      sp_kaido_g3_left:
        chainage_m: 700
        offset_m: [-30, 15]
      sp_kaido_g4_left:
        chainage_m: 950
        offset_m: [-30, 12]
      ship_searchlight:
        chainage_m: [640, 800]
        offset_m: [-400, 150]
    volumes:
      vol_bridge_bend:
        chainage_m: [1140, 1160]
      vol_kakuredani_mouth: {note: end of valley trail}
      vol_sando_planks:
        route: spl_onemichi
        chainage_m: [410, 440]
      vol_back_gate: {note: shared with pl_estate_night}
  pl_ishibashi:
    source: new; local cm, origin = west abutment centre, +X east along the road, +Y upstream (north)
    size_m: [120, 80]
    bridge:
      type: granite slab-beam (石桁橋), 4 spans
      deck_cm:
        x: [0, 1440]
        y: [-135, 135]
        z: 150
    volumes:
      vol_ishibashi:
        center_cm: [1500, -1500, 500]
        size_cm: [12000, 8000, 1500]
      vol_ford:
        center_cm: [700, -4500, 0]
        size_cm: [2000, 1200, 200]
      vol_outcrop_top:
        center_cm: [2200, -2000, 650]
        size_cm: [400, 400, 300]
      vol_bridge_deck:
        center_cm: [720, 0, 200]
        size_cm: [1440, 270, 300]
      vol_checkpoint_rear:
        center_cm: [2900, -300, 200]
        size_cm: [900, 2400, 400]
      ps_near_bank_start: [-4000, 0, 0]
    spawns:
      sp_barrier_line:
      - [1800, -600, 0]
      - [1900, 200, 0]
      - [2150, 700, 0]
      - [2300, -200, 0]
      sp_scan_gate: [1600, 0, 0]
      sp_outcrop_platform: [2200, -2000, 600]
      sp_far_road_east: [8000, 0, 0]
      convoy_hold: [-6000, 0, 0]
  pl_kakuredani:
    source: new hub; local cm, origin = valley-mouth log bridge, +Y up-valley
    size_m: [70, 220]
    volumes:
      vol_kakuredani_mouth:
        center_cm: [0, 600, 200]
        size_cm: [800, 800, 400]
      vol_clearing:
        center_cm: [0, 9000, 300]
        size_cm: [4000, 3000, 600]
      vol_kohagi_arrives:
        center_cm: [0, 9000, 300]
        size_cm: [4000, 3000, 600]
        gate: after site_restored:1
      vol_ridge_trailhead:
        center_cm: [-2500, 6000, 200]
        size_cm: [600, 600, 400]
    spawns:
      pack_horse_c_unload: [0, 8500, 0]
      shelter_1: [-1800, 10800, 0]
      shelter_2: [1400, 12900, 0]
      shelter_3: [500, 15900, 0]
      kiln: [-900, 12000, 0]
      ps_workshop_lean_to: [-500, 11500, 0]
      col_valley_mouth_mark: [-300, 800, 120]
lines:
- {id: ch02.b01.kohagi.001, beat: ch02.b01, speaker: scout, register: terse, ja: 空から船が来た。蔵に見知らぬ封印が！, en: Ships came from the sky. Strange seals cover the granaries!, duration_s: 4.6, kind: story, 'on': cine@8.0, mode: cinematic, canon: catalog ch02 line 1, audio: null}
- {id: ch02.b01.sekireisai.002, beat: ch02.b01, speaker: mentor, register: archaic_samurai, ja: 落ち着け。数を言え。, en: Steady. Give me numbers., duration_s: 3.2, kind: story, 'on': cine@13.0, mode: cinematic, audio: null}
- {id: ch02.b01.kohagi.003, beat: ch02.b01, speaker: scout, register: terse, ja: 船、三つ。蔵に一つずつ、青い錠。, en: Three ships. A blue lock on every granary., duration_s: 4.0, kind: story, 'on': cine@16.6, mode: cinematic, audio: null}
- {id: ch02.b01.valamort.004, beat: ch02.b01, speaker: banker, register: alien_corporate_keigo, ja: 告知いたします。本日より、猫柳生の地は当院の管理下となりました。, en: 'Notice. As of today, the Nyaagyu lands are managed by this House.', duration_s: 8.5, kind: story, 'on': cine@24.0, mode: cinematic, readings: 当院(とういん), audio: null}
- {id: ch02.b01.valamort.005, beat: ch02.b01, speaker: banker, register: alien_corporate_keigo, ja: 蔵、田畑、工房は、未払い債務の担保として差し押さえました。, en: 'Granaries, fields and workshops are seized as collateral for unpaid debt.', duration_s: 7.7, kind: story, 'on': cine@32.9, mode: cinematic, readings: 担保(たんぽ)・差し押さえ(さしおさえ), audio: null}
- {id: ch02.b01.valamort.006, beat: ch02.b01, speaker: banker, register: alien_corporate_keigo, ja: 抵抗は延滞とみなされ、利息が発生いたします。, en: Resistance will be treated as delinquency. Interest will accrue., duration_s: 5.7, kind: story, 'on': cine@41.0, mode: cinematic, readings: 延滞(えんたい), audio: null}
- {id: ch02.b01.nyaakoto.007, beat: ch02.b01, speaker: samurai, register: samurai_restrained, ja: 借りた覚えは、ない。, en: We never borrowed a thing., duration_s: 2.4, kind: story, 'on': cine@47.1, mode: cinematic, audio: null}
- {id: ch02.b01.sekireisai.008, beat: ch02.b01, speaker: mentor, register: archaic_samurai, ja: 借りは向こうが書くものらしいのう。……門を閉めよ。, en: It seems they write the debt themselves. …Close the gate., duration_s: 6.3, kind: story, 'on': cine@50.0, mode: cinematic, audio: null}
- {id: ch02.b02.sekireisai.001, beat: ch02.b02, speaker: mentor, register: archaic_samurai, ja: 門を守れ。一歩も入れるな。, en: Hold the gate. Not one step inside., duration_s: 3.9, kind: story, 'on': beat_start, mode: ambient, audio: null}
- {id: ch02.b02.nyaakoto.002, beat: ch02.b02, speaker: samurai, register: samurai_restrained, ja: 松吉は右、竹丸は左。屋根の者は私が射る。, en: 'Matsukichi, right. Takemaru, left. I will take the roof.', duration_s: 5.5, kind: story, 'on': beat_start, mode: ambient, queue_after: ch02.b02.sekireisai.001, audio: null}
- {id: ch02.b02.enforcer.003, beat: ch02.b02, speaker: enforcer, register: alien_corporate_bark, ja: 債務者の抵抗を確認。制圧いたします。, en: Debtor resistance confirmed. Suppressing., duration_s: 4.4, kind: bark, 'on': 'alert_state:alert', mode: ambient, repeatable: true, cooldown_s: 12, voice_variant: rifle, readings: 債務者(さいむしゃ), audio: null}
- {id: ch02.b02.enforcer.004, beat: ch02.b02, speaker: enforcer, register: alien_corporate_bark, ja: 側面より回収いたします。, en: Collecting from the flank., duration_s: 2.7, kind: bark, 'on': 'ai:flank', mode: ambient, repeatable: true, cooldown_s: 15, voice_variant: rifle, audio: null}
- {id: ch02.b02.matsukichi.005, beat: ch02.b02, speaker: pupil_matsukichi, register: young_samurai, ja: 潜り戸が破られた！, en: The wicket is breached!, duration_s: 2.3, kind: story, 'on': 'wave_start:2', mode: ambient, readings: 潜り戸(くぐりど), audio: null}
- {id: ch02.b02.matsukichi.006, beat: ch02.b02, speaker: pupil_matsukichi, register: young_samurai, ja: くっ……足を、やられた。, en: My leg… they got my leg., duration_s: 2.6, kind: story, 'on': 'npc_downed:pupil_matsukichi', mode: ambient, repeatable: true, cooldown_s: 30, audio: null}
- {id: ch02.b02.baio.007, beat: ch02.b02, speaker: pupil_baio, register: elder_samurai, ja: 閂が持たぬ！　門が開くぞ！, en: The bar will not hold! The gate is opening!, duration_s: 3.2, kind: story, 'on': 'wave_start:3', mode: ambient, readings: 閂(かんぬき), audio: null}
- {id: ch02.b02.retainer.008, beat: ch02.b02, speaker: enforcer, register: alien_corporate_bark, ja: 取り立てに参りました。, en: We have come to collect., duration_s: 2.5, kind: bark, 'on': 'wave_start:3', mode: ambient, queue_after: ch02.b02.baio.007, repeatable: true, cooldown_s: 20, voice_variant: blade retainer, readings: 取り立て(とりたて), audio: null}
- {id: ch02.b02.enforcer.009, beat: ch02.b02, speaker: enforcer, register: alien_corporate_bark, ja: 損耗率、許容値を超過。後退いたします。, en: Losses exceed tolerance. Withdrawing., duration_s: 4.6, kind: bark, 'on': 'ai:retreat', mode: ambient, repeatable: true, cooldown_s: 20, voice_variant: rifle, readings: 損耗率(そんもうりつ), audio: null}
- {id: ch02.b02.sekireisai.010, beat: ch02.b02, speaker: mentor, register: archaic_samurai, ja: 武具蔵に盾の者が入った。槍を取れ。刀では届かぬ。, en: Shield-bearers are in the armory. Take a spear. A sword will not reach., duration_s: 7.0, kind: story, 'on': beat_complete, mode: ambient, readings: 武具蔵(ぶぐぐら), audio: null}
- {id: ch02.b03.nyaakoto.001, beat: ch02.b03, speaker: samurai, register: samurai_restrained, ja: 先生、一本お借りします。, en: 'Sensei, I will borrow one.', duration_s: 3.2, kind: story, 'on': beat_start, mode: ambient, audio: null}
- {id: ch02.b03.sekireisai.002, beat: ch02.b03, speaker: mentor, register: archaic_samurai, ja: 盾の縁を突け。正面は鉄じゃ。, en: Thrust at the shield's edge. Its face is iron., duration_s: 4.1, kind: story, 'on': beat_start, mode: radio, queue_after: ch02.b03.nyaakoto.001, readings: 縁(ふち), audio: null}
- {id: ch02.b03.shield.003, beat: ch02.b03, speaker: enforcer, register: alien_corporate_bark, ja: 前進。資産を保全いたします。, en: Advancing. Securing assets., duration_s: 3.4, kind: bark, 'on': 'alert_state:alert', mode: ambient, repeatable: true, cooldown_s: 15, voice_variant: shield, readings: 保全(ほぜん), audio: null}
- {id: ch02.b03.shield.004, beat: ch02.b03, speaker: enforcer, register: alien_corporate_bark, ja: 盾、姿勢を喪失。, en: Shield displaced., duration_s: 2.3, kind: bark, 'on': 'ai:shield_turned', mode: ambient, repeatable: true, cooldown_s: 10, voice_variant: shield, readings: 喪失(そうしつ), audio: null}
- {id: ch02.b03.sekireisai.005, beat: ch02.b03, speaker: mentor, register: archaic_samurai, ja: 懐に入られたら槍は死ぬ。退いて間を取れ。, en: Let him inside and the spear is dead. Step back. Take distance., duration_s: 5.6, kind: story, 'on': 'ai:player_inside_polearm_min', mode: radio, once: true, readings: 懐(ふところ)・間(ま), audio: null}
- {id: ch02.b04.sekireisai.001, beat: ch02.b04, speaker: mentor, register: archaic_samurai, ja: ニャーコト。蔵の種籾を、隠れ谷へ運べ。, en: Nyaakoto. Take the seed rice to the Hidden Valley., duration_s: 5.0, kind: story, 'on': beat_start, mode: ambient, readings: 種籾(たねもみ)・隠れ谷(かくれだに), audio: null}
- {id: ch02.b04.nyaakoto.002, beat: ch02.b04, speaker: samurai, register: samurai_restrained, ja: 先生は。, en: 'And you, Sensei?', duration_s: 1.5, kind: story, 'on': beat_start, mode: ambient, queue_after: ch02.b04.sekireisai.001, audio: null}
- {id: ch02.b04.sekireisai.003, beat: ch02.b04, speaker: mentor, register: archaic_samurai, ja: わしは残る。年寄りの足では荷の邪魔じゃ。, en: I stay. Old legs would only slow the load., duration_s: 5.4, kind: story, 'on': 'volume_enter:vol_courtyard_west', mode: blocking, audio: null}
- {id: ch02.b04.nyaakoto.004, beat: ch02.b04, speaker: samurai, register: samurai_restrained, ja: しかし——, en: But—, duration_s: 1.3, kind: story, 'on': 'volume_enter:vol_courtyard_west', mode: blocking, audio: null}
- {id: ch02.b04.sekireisai.005, beat: ch02.b04, speaker: mentor, register: archaic_samurai, ja: 種は明日の田じゃ。刀は、何のためにある。, en: 'Seed is tomorrow''s field. What is the sword for?', duration_s: 5.2, kind: story, 'on': 'volume_enter:vol_courtyard_west', mode: blocking, canon: bible §9 key line 「種は明日の田じゃ」, audio: null}
- {id: ch02.b04.nyaakoto.006, beat: ch02.b04, speaker: samurai, register: samurai_restrained, ja: ……民から、預かるもの。, en: …It is held in trust from the people., duration_s: 2.8, kind: story, 'on': 'volume_enter:vol_courtyard_west', mode: blocking, audio: null}
- {id: ch02.b04.sekireisai.007, beat: ch02.b04, speaker: mentor, register: archaic_samurai, ja: ならば行け。, en: Then go., duration_s: 1.8, kind: story, 'on': 'volume_enter:vol_courtyard_west', mode: blocking, audio: null}
- {id: ch02.b04.sekireisai.008, beat: ch02.b04, speaker: mentor, register: archaic_samurai, ja: 竹丸、ついて参れ。道場にまだ人がおる。, en: 'Takemaru, with me. There are still people in the dojo.', duration_s: 5.2, kind: story, 'on': beat_complete, mode: ambient, audio: null}
- {id: ch02.b04.baio.009, beat: ch02.b04, speaker: pupil_baio, register: elder_samurai, ja: 皆、裏山の杣道へ。子らを先に。, en: 'Everyone, to the woodcutters'' path. Children first.', duration_s: 3.9, kind: story, 'on': beat_complete, mode: ambient, queue_after: ch02.b04.sekireisai.008, readings: 杣道(そまみち), audio: null}
- {id: ch02.b05.groom.001, beat: ch02.b05, speaker: groom, register: kamigata_commoner, ja: ニャーコト様、馬は二頭。一頭に二俵ずつ！, en: 'Sir, two horses. Two bales on each!', duration_s: 4.7, kind: story, 'on': beat_start, mode: ambient, readings: 二俵(にひょう), audio: null}
- {id: ch02.b05.system.002, beat: ch02.b05, speaker: credit_system, register: alien_device_pa, ja: 封印への接触を検知。延滞として記録いたします。, en: Seal contact detected. Recorded as delinquency., duration_s: 5.2, kind: bark, 'on': 'interact_start:seal_kura_sw', mode: ambient, repeatable: true, cooldown_s: 8, audio: null}
- {id: ch02.b05.enforcer.003, beat: ch02.b05, speaker: enforcer, register: alien_corporate_bark, ja: 差押物件の搬出を確認。阻止いたします。, en: Removal of seized property detected. Intercepting., duration_s: 4.6, kind: bark, 'on': 'ai:carry_spotted', mode: ambient, repeatable: true, cooldown_s: 20, voice_variant: rifle, readings: 差押物件(さしおさえぶっけん)・搬出(はんしゅつ), audio: null}
- {id: ch02.b05.groom.004, beat: ch02.b05, speaker: groom, register: kamigata_commoner, ja: 一駄、積んだ！, en: One load is on!, duration_s: 2.0, kind: story, 'on': 'progress_at:0.5', mode: ambient, readings: 一駄(いちだ), audio: null}
- {id: ch02.b05.groom.005, beat: ch02.b05, speaker: groom, register: kamigata_commoner, ja: 二駄目も積みました！　行けます！, en: Second load on! We can go!, duration_s: 3.8, kind: story, 'on': 'progress_at:1.0', mode: ambient, readings: 二駄目(にだめ), audio: null}
- {id: ch02.b06.kohagi.001, beat: ch02.b06, speaker: scout, register: terse, ja: 上。落ちてくる。三つ。, en: Above. Falling. Three., duration_s: 3.0, kind: story, 'on': beat_start, mode: ambient, audio: null}
- {id: ch02.b06.system.002, beat: ch02.b06, speaker: credit_system, register: alien_device_pa, ja: 回収班、降下いたします。, en: 'Collection team, descending.', duration_s: 2.8, kind: bark, 'on': 'ai:drop_pod_launch', mode: ambient, repeatable: true, cooldown_s: 30, audio: null}
- {id: ch02.b06.grenadier.003, beat: ch02.b06, speaker: enforcer, register: alien_corporate_bark, ja: 曲射、開始。, en: 'Arcing fire, commencing.', duration_s: 1.9, kind: bark, 'on': 'ai:grenadier_fire', mode: ambient, repeatable: true, cooldown_s: 12, voice_variant: grenadier, readings: 曲射(きょくしゃ), audio: null}
- {id: ch02.b06.groom.004, beat: ch02.b06, speaker: groom, register: kamigata_commoner, ja: 馬が怯えとる！　これ以上はあかん！, en: The horses are panicking! They can't take more!, duration_s: 3.8, kind: story, 'on': 'target_hp_below:any:0.5', mode: ambient, once: true, readings: 怯え(おびえ), audio: null}
- {id: ch02.b06.sekireisai.005, beat: ch02.b06, speaker: mentor, register: archaic_samurai, ja: ニャーコト、急げ！　長くは持たぬ！, en: 'Nyaakoto, hurry! We cannot hold long!', duration_s: 4.1, kind: story, 'on': 'progress_at:0.5', mode: radio, audio: null}
- {id: ch02.b06.kohagi.006, beat: ch02.b06, speaker: scout, register: terse, ja: 裏門、空いた。今。, en: Back gate's clear. Now., duration_s: 2.6, kind: story, 'on': beat_complete, mode: ambient, readings: 裏門(うらもん), audio: null}
- {id: ch02.b07.kohagi.001, beat: ch02.b07, speaker: scout, register: terse, ja: 道は、あたしが先に見る。, en: I'll scout the road ahead., duration_s: 2.8, kind: story, 'on': cine@9.0, mode: cinematic, audio: null}
- {id: ch02.b07.groom.002, beat: ch02.b07, speaker: groom, register: kamigata_commoner, ja: 乗掛で参ります。遅れたら、置いていってくだされ。, en: 'I''ll ride atop the load. If I fall behind, leave me.', duration_s: 5.1, kind: story, 'on': cine@18.0, mode: cinematic, readings: 乗掛(のりかけ), audio: null}
- {id: ch02.b07.nyaakoto.003, beat: ch02.b07, speaker: samurai, register: samurai_restrained, ja: 誰も置いていかない。, en: I leave no one behind., duration_s: 2.5, kind: story, 'on': cine@24.0, mode: cinematic, audio: null}
- {id: ch02.b07.nyaakoto.004, beat: ch02.b07, speaker: samurai, register: samurai_restrained, ja: 栗丸。今夜は、走ってくれ。, en: 'Kurimaru. Tonight, run for me.', duration_s: 3.5, kind: story, 'on': cine@40.0, mode: cinematic, readings: 栗丸(くりまる), audio: null}
- {id: ch02.b08.drone.001, beat: ch02.b08, speaker: drone, register: alien_device, ja: 目録に記載。動産、馬三頭。, en: 'Entered into inventory. Movables: three horses.', duration_s: 3.7, kind: bark, 'on': 'wave_start:1', mode: ambient, repeatable: true, cooldown_s: 60, readings: 目録(もくろく)・動産(どうさん), audio: null}
- {id: ch02.b08.drone.002, beat: ch02.b08, speaker: drone, register: alien_device, ja: 差押網、投下いたします。, en: 'Seizure net, deploying.', duration_s: 2.8, kind: bark, 'on': 'ai:net_windup', mode: ambient, repeatable: true, cooldown_s: 10, readings: 差押網(さしおさえあみ), audio: null}
- {id: ch02.b08.groom.003, beat: ch02.b08, speaker: groom, register: kamigata_commoner, ja: 網や！　網が掛かった！, en: A net! They've netted us!, duration_s: 2.8, kind: story, 'on': 'ai:convoy_netted', mode: ambient, repeatable: true, cooldown_s: 20, audio: null}
- {id: ch02.b08.nyaakoto.004, beat: ch02.b08, speaker: samurai, register: samurai_restrained, ja: 右に寄せろ。切る。, en: Pull right. I will cut it., duration_s: 2.6, kind: story, 'on': 'ai:convoy_netted', mode: ambient, queue_after: ch02.b08.groom.003, once: true, audio: null}
- {id: ch02.b08.system.005, beat: ch02.b08, speaker: credit_system, register: alien_device_pa, ja: 照合中。……照合中。, en: Verifying. …Verifying., duration_s: 3.0, kind: bark, 'on': 'wave_start:3', mode: ambient, repeatable: true, cooldown_s: 25, readings: 照合(しょうごう), audio: null}
- {id: ch02.b08.groom.006, beat: ch02.b08, speaker: groom, register: kamigata_commoner, ja: 光や！　馬を下げなされ！, en: The light! Pull the horses back!, duration_s: 2.9, kind: story, 'on': 'ai:horse_spooked:convoy', mode: ambient, once: true, audio: null}
- {id: ch02.b08.nyaakoto.007, beat: ch02.b08, speaker: samurai, register: samurai_restrained, ja: どう、どう……栗丸、大丈夫だ。, en: 'Easy, easy… Kurimaru, you are all right.', duration_s: 3.7, kind: story, 'on': 'ai:horse_spooked:kurimaru', mode: ambient, once: true, audio: null}
- {id: ch02.b08.nyaakoto.008, beat: ch02.b08, speaker: samurai, register: samurai_restrained, ja: 右に回った……下がって取る。, en: It went right… I will drop back and take it., duration_s: 3.5, kind: story, 'on': 'ai:drone_crossed_right', mode: ambient, once: true, audio: null}
- {id: ch02.b08.kohagi.009, beat: ch02.b08, speaker: scout, register: terse, ja: 橋に関所。兵が六、擲弾が一。向こう岸の上に、光る目が一。, en: 'Bridge checkpoint. Six troops, one grenadier. A glinting eye on the far bank.', duration_s: 7.0, kind: story, 'on': beat_complete, mode: ambient, readings: 関所(せきしょ)・擲弾(てきだん), audio: null}
- {id: ch02.b09.nyaakoto.001, beat: ch02.b09, speaker: samurai, register: samurai_restrained, ja: 馬を頼む。ここで待て。, en: Watch the horses. Wait here., duration_s: 2.9, kind: story, 'on': beat_start, mode: ambient, audio: null}
- {id: ch02.b09.kohagi.002, beat: ch02.b09, speaker: scout, register: terse, ja: 浅瀬がある。下流に五十歩。, en: There's a ford. Fifty paces downstream., duration_s: 3.6, kind: story, 'on': beat_start, mode: ambient, queue_after: ch02.b09.nyaakoto.001, readings: 浅瀬(あさせ), audio: null}
- {id: ch02.b09.marksman.003, beat: ch02.b09, speaker: enforcer, register: alien_corporate_bark, ja: 照準、査定中。, en: Sighting. Assessing., duration_s: 2.1, kind: bark, 'on': 'ai:marksman_lock', mode: ambient, repeatable: true, cooldown_s: 6, voice_variant: marksman, readings: 査定(さてい), audio: null}
- {id: ch02.b09.enforcer.004, beat: ch02.b09, speaker: enforcer, register: alien_corporate_bark, ja: 未登録の債務者を確認。, en: Unregistered debtor sighted., duration_s: 3.0, kind: bark, 'on': 'alert_state:alert', mode: ambient, repeatable: true, cooldown_s: 15, voice_variant: rifle, audio: null}
- {id: ch02.b09.enforcer.005, beat: ch02.b09, speaker: enforcer, register: alien_corporate_bark, ja: 対象を見失いました。探索に移行します。, en: Target lost. Beginning search., duration_s: 4.4, kind: bark, 'on': 'alert_state:search', mode: ambient, repeatable: true, cooldown_s: 15, voice_variant: rifle, audio: null}
- {id: ch02.b09.kohagi.006, beat: ch02.b09, speaker: scout, register: terse, ja: 目、潰れた。, en: The eye's out., duration_s: 1.7, kind: story, 'on': 'enemy_killed:marksman', mode: ambient, once: true, readings: 潰れた(つぶれた), audio: null}
- {id: ch02.b09.enforcer.007, beat: ch02.b09, speaker: enforcer, register: alien_corporate_bark, ja: 検問所に増援を要請。至急。, en: Requesting reinforcement at the checkpoint. Urgent., duration_s: 3.7, kind: bark, 'on': 'wave_start:2', mode: ambient, repeatable: true, cooldown_s: 60, voice_variant: rifle, readings: 検問所(けんもんじょ), audio: null}
- {id: ch02.b10.kohagi.001, beat: ch02.b10, speaker: scout, register: terse, ja: あたしは後ろを見てくる。はぐれた人がいるかも。, en: I'll check behind us. There may be stragglers., duration_s: 4.7, kind: story, 'on': beat_start, mode: ambient, audio: null}
- {id: ch02.b10.groom.002, beat: ch02.b10, speaker: groom, register: kamigata_commoner, ja: ……先生は、ご無事でしょうか。, en: '…Do you think Sensei is safe?', duration_s: 3.3, kind: story, 'on': 'progress_at:0.3', mode: ambient, audio: null}
- {id: ch02.b10.nyaakoto.003, beat: ch02.b10, speaker: samurai, register: samurai_restrained, ja: 先生は、猫柳生で一番強い。, en: Sensei is the strongest in Nyaagyu., duration_s: 3.7, kind: story, 'on': 'progress_at:0.3', mode: ambient, queue_after: ch02.b10.groom.002, audio: null}
- {id: ch02.b10.nyaakoto.004, beat: ch02.b10, speaker: samurai, register: samurai_restrained, ja: ……道中、お守りください。, en: …Watch over the road., duration_s: 3.1, kind: story, 'on': 'interact:jizo_bow', mode: ambient, once: true, audio: null}
- {id: ch02.b11.villager.001, beat: ch02.b11, speaker: villager, register: yamato_rural, ja: ありがたや……子らが朝から何も。, en: Bless you… The children haven't eaten since morning., duration_s: 3.5, kind: story, 'on': 'item_delivered:shelter_1', mode: ambient, audio: null}
- {id: ch02.b11.child.002, beat: ch02.b11, speaker: child, register: child, ja: このお米、借り？　返さなあかんの？, en: 'Is this rice a loan? Do we have to pay it back?', duration_s: 3.7, kind: story, 'on': 'item_delivered:shelter_2', mode: ambient, audio: null}
- {id: ch02.b11.nyaakoto.003, beat: ch02.b11, speaker: samurai, register: samurai_restrained, ja: 借りではない。田で育ったものだ。, en: It is not a loan. It grew in our fields., duration_s: 3.8, kind: story, 'on': 'item_delivered:shelter_2', mode: ambient, queue_after: ch02.b11.child.002, audio: null}
- {id: ch02.b11.nyaakoto.004, beat: ch02.b11, speaker: samurai, register: samurai_restrained, ja: 種籾には手をつけるな。あれは来年の田だ。, en: Do not touch the seed rice. That is next year's field., duration_s: 4.8, kind: story, 'on': 'site_restored:1', mode: ambient, readings: 種籾(たねもみ), audio: null}
- {id: ch02.b12.kohagi.001, beat: ch02.b12, speaker: scout, register: terse, ja: 屋敷が燃えてる。, en: The estate is burning., duration_s: 2.2, kind: story, 'on': beat_start, mode: blocking, audio: null}
- {id: ch02.b12.nyaakoto.002, beat: ch02.b12, speaker: samurai, register: samurai_restrained, ja: 先生は。, en: 'Sensei?', duration_s: 1.5, kind: story, 'on': beat_start, mode: blocking, audio: null}
- {id: ch02.b12.kohagi.003, beat: ch02.b12, speaker: scout, register: terse, ja: 残ってる。道場の上に、青い光が集まってた。, en: Still there. Blue light was gathering over the dojo., duration_s: 4.9, kind: story, 'on': beat_start, mode: blocking, audio: null}
- {id: ch02.b12.kohagi.004, beat: ch02.b12, speaker: scout, register: terse, ja: 尾根道なら、半分で着く。馬一頭なら通れる。, en: The ridge road is half the distance. One horse can pass., duration_s: 5.3, kind: story, 'on': beat_start, mode: blocking, readings: 尾根道(おねみち), audio: null}
- {id: ch02.b12.nyaakoto.005, beat: ch02.b12, speaker: samurai, register: samurai_restrained, ja: 種は届いた。次は、先生だ。, en: 'The seed is safe. Now, Sensei.', duration_s: 3.5, kind: story, 'on': beat_start, mode: blocking, audio: null}
- {id: ch02.b13.nyaakoto.001, beat: ch02.b13, speaker: samurai, register: samurai_restrained, ja: 走れ、栗丸……！, en: 'Run, Kurimaru…!', duration_s: 2.3, kind: story, 'on': beat_start, mode: ambient, audio: null}
- {id: ch02.b13.system.002, beat: ch02.b13, speaker: credit_system, register: alien_device_pa, ja: 告知。猫柳生家の資産評価を開始いたします。, en: Notice. Asset appraisal of House Nyaagyu has begun., duration_s: 5.5, kind: story, 'on': 'progress_at:0.6', mode: ambient, readings: 資産評価(しさんひょうか), audio: null}
- {id: ch02.b14.takemaru.001, beat: ch02.b14, speaker: pupil_takemaru, register: young_samurai, ja: 誰か……！　ここだ！, en: Someone…! Over here!, duration_s: 2.5, kind: story, 'on': 'volume_enter:vol_dojo_east_veranda', mode: ambient, repeatable: true, cooldown_s: 15, audio: null}
- {id: ch02.b14.takemaru.002, beat: ch02.b14, speaker: pupil_takemaru, register: young_samurai, ja: 先生が……俺たちを出す代わりに、刀を置かれた。, en: Sensei… He laid down his sword so they would let us out., duration_s: 5.1, kind: story, 'on': 'interact_complete:beam_takemaru', mode: ambient, audio: null}
- {id: ch02.b14.nyaakoto.003, beat: ch02.b14, speaker: samurai, register: samurai_restrained, ja: 裏門から谷へ行け。道は開いている。, en: Take the back gate to the valley. The road is open., duration_s: 4.3, kind: story, 'on': 'interact_complete:beam_takemaru', mode: ambient, queue_after: ch02.b14.takemaru.002, audio: null}
- {id: ch02.b14.nyaakoto.004, beat: ch02.b14, speaker: samurai, register: samurai_restrained, ja: 名札掛けまで……差し押さえたのか。, en: Even the name board… They seized that too., duration_s: 4.1, kind: story, 'on': 'collectible:ch02.c03', mode: ambient, once: true, readings: 名札掛け(なふだかけ), audio: null}
- {id: ch02.b15.dunark.001, beat: ch02.b15, speaker: boss_dunark, register: alien_corporate_keigo, ja: 猫柳生石鈴斎様は、ご自身を担保として差し入れられました。, en: Nyaagyu Sekireisai has pledged himself as collateral., duration_s: 7.4, kind: story, 'on': intro@6.0, mode: cinematic, readings: 石鈴斎(せきれいさい)・差し入れ(さしいれ), audio: null}
- {id: ch02.b15.dunark.002, beat: ch02.b15, speaker: boss_dunark, register: alien_corporate_keigo, ja: 引き換えに、道場内の人員は解放いたしました。, en: 'In exchange, the personnel in the dojo were released.', duration_s: 5.7, kind: story, 'on': intro@13.8, mode: cinematic, readings: 人員(じんいん), audio: null}
- {id: ch02.b15.nyaakoto.003, beat: ch02.b15, speaker: samurai, register: samurai_restrained, ja: 民の手を縛る帳簿なら、ここで断つ。, en: 'If your ledger binds their hands, I will break its hold here.', duration_s: 4.2, kind: story, 'on': intro@19.9, mode: cinematic, readings: 帳簿(ちょうぼ), canon: catalog ch02 line 3, audio: null}
- {id: ch02.b15.dunark.004, beat: ch02.b15, speaker: boss_dunark, register: alien_corporate_keigo, ja: 上陸指揮官ドゥナーク。督促手続きを開始いたします。, en: Landing Commander Dunark. Commencing dunning procedure., duration_s: 6.6, kind: story, 'on': intro@24.5, mode: cinematic, readings: 督促(とくそく), audio: null}
- {id: ch02.b15.dunark.005, beat: ch02.b15, speaker: boss_dunark, register: alien_corporate_keigo, ja: 督促、第一回。, en: First notice., duration_s: 2.5, kind: telegraph, 'on': 'boss_phase:1', mode: ambient, readings: 督促(とくそく), canon: bible §8 voice telegraph, audio: null}
- {id: ch02.b15.sekireisai.006, beat: ch02.b15, speaker: mentor, register: archaic_samurai, ja: 勝とうとするな。相手の太刀が、おぬしの道を教えてくれる。, en: Do not try to win. His sword will show you your path., duration_s: 7.1, kind: story, 'on': 'boss_phase:1', mode: ambient, queue_after: ch02.b15.dunark.005, readings: 太刀(たち), canon: bible §6.5 register sample, audio: null}
- {id: ch02.b15.dunark.007, beat: ch02.b15, speaker: boss_dunark, register: alien_corporate_keigo, ja: 第二回。, en: Second notice., duration_s: 1.7, kind: telegraph, 'on': 'boss_phase:2', mode: ambient, canon: bible §8 voice telegraph, audio: null}
- {id: ch02.b15.dunark.008, beat: ch02.b15, speaker: boss_dunark, register: alien_corporate_keigo, ja: 一括。, en: In full., duration_s: 1.3, kind: telegraph, 'on': 'pattern:thrust', mode: ambient, repeatable: true, cooldown_s: 0, readings: 一括(いっかつ), audio: null}
- {id: ch02.b15.sekireisai.009, beat: ch02.b15, speaker: mentor, register: archaic_samurai, ja: 突きは受けるな。転じて横を取れ。, en: Do not meet the thrust. Roll aside and take his flank., duration_s: 4.5, kind: story, 'on': 'boss_phase:2', mode: ambient, queue_after: ch02.b15.dunark.007, readings: 転じて(てんじて; 転(まろばし)の教え), audio: null}
- {id: ch02.b15.dunark.010, beat: ch02.b15, speaker: boss_dunark, register: alien_corporate_keigo, ja: 最終督促。, en: Final notice., duration_s: 2.0, kind: telegraph, 'on': 'boss_phase:3', mode: ambient, canon: bible §8 voice telegraph, audio: null}
- {id: ch02.b15.dunark.011, beat: ch02.b15, speaker: boss_dunark, register: alien_corporate_keigo, ja: 保全措置。, en: Protective measure., duration_s: 2.0, kind: telegraph, 'on': 'pattern:shield_drone', mode: ambient, once: true, audio: null}
- {id: ch02.b15.sekireisai.012, beat: ch02.b15, speaker: mentor, register: archaic_samurai, ja: 刃の傾きを見よ。偽りは肩に出る。, en: Watch the tilt of his blade. A lie shows in the shoulder., duration_s: 4.7, kind: story, 'on': 'boss_phase:3', mode: ambient, queue_after: ch02.b15.dunark.010, readings: 偽り(いつわり), audio: null}
- {id: ch02.b15.dunark.013, beat: ch02.b15, speaker: boss_dunark, register: alien_corporate_keigo, ja: ……計算外。, en: …Unaccounted for., duration_s: 2.1, kind: telegraph, 'on': 'pattern:stagger', mode: ambient, repeatable: true, cooldown_s: 20, audio: null}
- {id: ch02.b15.sekireisai.014, beat: ch02.b15, speaker: mentor, register: archaic_samurai, ja: 立て。拍子に乗るな。拍子を読め。, en: Stand. Do not ride his rhythm. Read it., duration_s: 5.0, kind: story, 'on': player_died, mode: ambient, repeatable: true, cooldown_s: 0, readings: 拍子(ひょうし), audio: null}
- {id: ch02.b15.dunark.015, beat: ch02.b15, speaker: boss_dunark, register: alien_corporate_keigo, ja: 未回収の……まま、とは。, en: To fall… with the account still open., duration_s: 3.1, kind: story, 'on': outro@3.0, mode: cinematic, readings: 未回収(みかいしゅう), audio: null}
- {id: ch02.b16.valamort.001, beat: ch02.b16, speaker: banker, register: alien_corporate_keigo, ja: 上陸指揮官ドゥナーク。損失として、償却いたします。, en: Landing Commander Dunark. Written off as a loss., duration_s: 6.4, kind: story, 'on': cine@14.0, mode: cinematic, readings: 償却(しょうきゃく), audio: null}
- {id: ch02.b16.valamort.002, beat: ch02.b16, speaker: banker, register: alien_corporate_keigo, ja: 今日から、その収穫も労働も我らへの負債だ。, en: 'From today, your harvest and labor are debts owed to us.', duration_s: 5.7, kind: story, 'on': cine@21.0, mode: cinematic, readings: 負債(ふさい), canon: catalog ch02 line 2, audio: null}
- {id: ch02.b16.valamort.003, beat: ch02.b16, speaker: banker, register: alien_corporate_keigo, ja: 債務者番号〇〇〇一。石鈴斎様を、担保としてお預かりいたします。, en: Debtor zero-zero-zero-one. The honorable Sekireisai is held as collateral., duration_s: 8.9, kind: story, 'on': cine@28.0, mode: cinematic, readings: 〇〇〇一(まる・まる・まる・いち; B7 to confirm), audio: null}
- {id: ch02.b16.nyaakoto.004, beat: ch02.b16, speaker: samurai, register: samurai_restrained, ja: 先生！, en: Sensei!, duration_s: 1.3, kind: story, 'on': cine@37.3, mode: cinematic, audio: null}
- {id: ch02.b16.sekireisai.005, beat: ch02.b16, speaker: mentor, register: archaic_samurai, ja: 来るな。……種は、届いたか。, en: 'Stay back. …Did the seed arrive?', duration_s: 3.8, kind: story, 'on': cine@39.0, mode: cinematic, audio: null}
- {id: ch02.b16.nyaakoto.006, beat: ch02.b16, speaker: samurai, register: samurai_restrained, ja: ……届きました。, en: …It arrived., duration_s: 2.1, kind: story, 'on': cine@43.2, mode: cinematic, audio: null}
- {id: ch02.b16.sekireisai.007, beat: ch02.b16, speaker: mentor, register: archaic_samurai, ja: ならば、よい。, en: Then it is well., duration_s: 1.8, kind: story, 'on': cine@46.0, mode: cinematic, audio: null}
- {id: ch02.b16.valamort.008, beat: ch02.b16, speaker: banker, register: alien_corporate_keigo, ja: ご安心を。利息は毎晩、きちんと計上いたします。, en: Rest assured. Interest will be booked faithfully every night., duration_s: 6.1, kind: story, 'on': cine@52.0, mode: cinematic, readings: 計上(けいじょう), audio: null}
- {id: ch02.b16.tetsugoro.009, beat: ch02.b16, speaker: gunsmith, register: blunt_artisan, ja: 鞴も金床も担いできた。道具さえありゃ、どこでも鍛冶場や。, en: 'We carried the bellows and the anvil. With tools, anywhere is a smithy.', duration_s: 6.1, kind: story, 'on': cine@82.0, mode: cinematic, readings: 鞴(ふいご)・金床(かなとこ), audio: null}
- {id: ch02.b16.nyaakoto.010, beat: ch02.b16, speaker: samurai, register: samurai_restrained, ja: 斬るのは最後だ。まず、守るものを数える。, en: 'Cutting comes last. First, count what we protect.', duration_s: 4.7, kind: story, 'on': cine@95.0, mode: cinematic, canon: bible §6.5 register sample, audio: null}
- {id: ch02.b16.baio.011, beat: ch02.b16, speaker: pupil_baio, register: elder_samurai, ja: 女子供が十九、年寄りが七。門弟は、わしと松吉と竹丸。, en: 'Nineteen women and children, seven elders. Pupils: Matsukichi, Takemaru and I.', duration_s: 6.5, kind: story, 'on': cine@101.0, mode: cinematic, readings: 門弟(もんてい), audio: null}
- {id: ch02.b16.nyaakoto.012, beat: ch02.b16, speaker: samurai, register: samurai_restrained, ja: 虎之介は。, en: 'And Toranosuke?', duration_s: 1.8, kind: story, 'on': cine@108.0, mode: cinematic, readings: 虎之介(とらのすけ), audio: null}
- {id: ch02.b16.baio.013, beat: ch02.b16, speaker: pupil_baio, register: elder_samurai, ja: 鐘と同時に、鷲尾の家へ走ったきりじゃ。, en: He ran for the Washio house at the first bell. Nothing since., duration_s: 4.2, kind: story, 'on': cine@110.2, mode: cinematic, readings: 鷲尾(わしお), audio: null}
- {id: ch02.b16.baio.014, beat: ch02.b16, speaker: pupil_baio, register: elder_samurai, ja: 先生のお席は、空けておこう。, en: We will keep Sensei's seat empty., duration_s: 3.2, kind: story, 'on': cine@118.0, mode: cinematic, audio: null}
- {id: ch02.b16.nyaakoto.015, beat: ch02.b16, speaker: samurai, register: samurai_restrained, ja: 取り返す。先生も、蔵も、田も。, en: 'I will take it all back. Sensei, the granaries, the fields.', duration_s: 4.0, kind: story, 'on': cine@128.0, mode: cinematic, audio: null}
ui_prompts:
- {id: ch02.b02.tut.001, beat: ch02.b02, 'on': 'npc_downed:any', ja: '倒れた門弟のそばで{Interact}長押し：助け起こす。', en: 'Hold {Interact} beside a downed pupil to help them up.'}
- {id: ch02.b03.tut.002, beat: ch02.b03, 'on': beat_start, ja: '槍を得た。{WeaponTwo}（長柄）／{ArmsWheel}で持ち替え。', en: 'Yari acquired. Press {WeaponTwo} (polearms) or {ArmsWheel} to switch.'}
- {id: ch02.b03.tut.003, beat: ch02.b03, 'on': 'volume_enter:vol_bugugura_yard', ja: 盾の縁を槍で突けば、構えが崩れる。, en: Thrust at a shield's edge to break its guard.}
- {id: ch02.b03.tut.004, beat: ch02.b03, 'on': 'ai:player_inside_polearm_min', ja: 懐では槍は弱い。退いて間合いを取れ。, en: The yari is weak up close. Step back to regain distance.}
- {id: ch02.b05.tut.005, beat: ch02.b05, 'on': 'volume_enter:vol_kura_sw_door', ja: '{Interact}長押し：石突で封印をこじ開ける。', en: 'Hold {Interact}: pry the seal off with the spear butt.'}
- {id: ch02.b05.tut.006, beat: ch02.b05, 'on': 'event:first_pickup', ja: 俵を担ぐ間は片手の刀のみ。弓は使えず、走れない。, en: 'Carrying a bale: one-handed katana only. No bow, no sprint.'}
- {id: ch02.b05.tut.007, beat: ch02.b05, 'on': 'event:first_pickup+4s', ja: '{Interact}で俵を下ろせる。後で拾い直せる。', en: 'Press {Interact} to set a bale down. Pick it up again later.'}
- {id: ch02.b06.tut.008, beat: ch02.b06, 'on': beat_start, ja: '荷馬を守れ。そばで{Interact}：傷の手当て。', en: 'Protect the pack horses. Press {Interact} beside one to treat it.'}
- {id: ch02.b06.tut.009, beat: ch02.b06, 'on': 'ai:drop_pod_launch@1', ja: 橙の輪は降下ポッドの着弾点。輪から離れよ。, en: Amber rings mark where pods will land. Get clear.}
- {id: ch02.b08.tut.010, beat: ch02.b08, 'on': beat_start, ja: '手綱を結び{Fire}長押しで引き分け。馬上の弓は左（弓手）のみ。', en: 'Reins knotted. Hold {Fire} to draw. In the saddle, the bow shoots left only.'}
- {id: ch02.b08.tut.011, beat: ch02.b08, 'on': beat_start+6s, ja: '前進しながら{Sprint}で歩度を上げ、後ろへ引いて緩める。荷馬の速さに合わせよ。', en: 'Hold {Sprint} while moving forward to quicken the gait; pull back to slow. Keep pace with the pack train.'}
- {id: ch02.b08.tut.012, beat: ch02.b08, 'on': 'ai:convoy_netted@1', ja: 網の掛かった荷馬の左に並び、右へ斬って網を切れ。, en: Ride on a netted horse's left and cut to your right to free it.}
- {id: ch02.b08.tut.013, beat: ch02.b08, 'on': 'event:arrows_below:4', ja: 先頭の荷馬に並ぶと、予備の箙から矢を補える。, en: Ride beside the lead pack horse to refill arrows from its spare quiver.}
- {id: ch02.b13.tut.014, beat: ch02.b13, 'on': beat_start, ja: 襲歩は馬の息を使う。尽きる前に駈歩へ落とせ。, en: The gallop spends the horse's wind. Ease to a canter before it runs out.}
- {id: ch02.b15.tut.015, beat: ch02.b15, 'on': 'pattern:thrust@1', ja: 突きは合わせられない。構えの終わりに横へ踏め（転）。, en: The thrust cannot be parried. Step aside just before it lands (marobashi).}
```
