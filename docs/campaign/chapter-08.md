# 第八章 最後の解放: Final Liberation (`ch08_debt_citadel`)

> **Monetary boundary (bible §2).** In this chapter, as in the whole campaign, SORA XOR (and the registry that leads to it) is a production-only storytelling premise. XOR is cut only against finished, inspected goods, is never shown as a balance or converted, and has no link to multiplayer XOR bonds, NFTs, wallets or IrohaConnect. It makes no claim about real-world money, investment or policy, and it does not describe the real SORA network or the design in the SORA Nexus article. **Review note (C1 lead, 2026-09-25):** names, calendar, speaker ids, Japanese punctuation and YAML field names in this file follow bible §9.1, §12.5 and §18.

**Status:** chapter design and script for Wave 2 lane C1. It follows the [story bible](story-bible.md) and changes none of its decisions. Numbers in this chapter are **proposals** for the lanes that own them: L1 (beats, saves, triggers), L2 (enemies), L3 (the Val Amort pattern tables), L4 (UI prompts), L5 (music and barks), C2/C3 (spaces), C4 (mission build) and C9 (cinematics). Nothing here is implemented. The Japanese still needs native review (B7). The kenjutsu, archery, tack, castle and festival details need review by a historian and a practitioner.

**Related sources:** [story bible](story-bible.md) §8 (bosses), §9 (story), §12 (beat taxonomy), §13 (ch08 outline), §14 (places), §15–17 (art, lighting, kamon); [catalog.json](../../Content/Data/catalog.json) chapter 8; [combat rules](../combat-rules.md); [historical arms](../historical-arms.md); [horse tack references](../historical-horse-tack-art-reference.md); [SORA kamon runtime art](../sora-kamon-runtime-art.md); [photoreal acceptance](../art-direction/photoreal-acceptance.md).

---

## 0. At a glance

| Item | Value |
|---|---|
| Chapter id / title | `ch08_debt_citadel` · 第八章 最後の解放 / Final Liberation |
| Target play time | **55 min** (3,300 target-seconds). Playtest acceptance ±20%: 44–66 min. A completionist adds about 6–8 min. |
| Beats | **18** sequenced beats, plus 6 passive collectibles |
| Mix (min) | C 21 · E 2 · S 0 · P 14 · M 5 · Cin 13 (bible §10: C 21 · E 2 · S 0 · P 14 · M 5 · Cin 13) |
| Voiced lines | **140** (bible budget 140), plus 14 HUD prompts (UI strings, not voiced) |
| Boss | `boss_val_amort`: three phases, a checkpoint per phase, defeat by **capture** (mutō-dori, then the engine's spine is cut) |
| Weapons unlocked | 12 単分子薙刀 and 17 治癒の槍 (b01), 15 小型迫撃砲 (b03), 6 金棒 (b06). This completes all 21 (bible §11). |
| New mechanics | Mounted charge with the yari; `volley_command` (rotating volley ranks); heavy-impact anchor plates; a capstan on a moving lift; seizure-tile arena hazard; a capture finale (sheathed mutō-dori, then the spine cut) |
| Horse | Yes: b02 charge on Kurimaru, beside Toranosuke on Arashi and 20 League riders |
| Maps | Primary **Arena 3** (Debt Citadel) plus campaign sublevels; **Arena 1** festival variant for the epilogue (bible §14 map index change) |
| Sites | site 1 → b04, site 0 → b07, site 2 → b16. The order reverses the catalog's `requires_sites` chain; see §6. |

---

## 1. Synopsis, locations and conditions

### 1.1 Synopsis

> 台風一過の秋の朝。大徴収官ヴァル・アモルトは「期限の利益の喪失」を宣言し、谷じゅうの残高を正午に一括請求した。払えぬ者は、家も道具も人も「回収」される。空紋一揆は夜明け前に隠れ谷を発ち、虎之介と並んで猫山の土手道を駆け抜け、外郭で輪番撃ちを組み、野鍛冶で道具を直しながら大手門の封印錨を金棒で砕く。担保牢から民を救い出したニャーコトは、一番奥の蔵で師・石鈴斎と再会する。「遅かったのう。」帳簿塔を轆轤で昇り、雲の上の帳簿機関でアモルトの「返済条件の変更」を硯ごと退け、三段の戦いの末、鞘の内の無刀取りで彼を捕らえ、機関の背骨を一太刀で断つ。谷じゅうの封印が消える。三日後の秋祭りの夜、生産改帳は高札場に掲げられ、夜明けの東の鳥居で、石鈴斎は名札を掛け直す。
>
> Autumn, the morning after the typhoon. High Collector Val Amort invokes **acceleration**: every balance in the valley falls due at noon, and whatever cannot pay (homes, tools, people) will be "collected." The Sora League rides out before dawn. Nyaakoto charges the Nekoyama causeway beside Toranosuke, commands rotating volley ranks in the outer bailey, keeps the field forge mending tools, and smashes the main gate's seal anchors with a kanabō. He frees the collateral cells and finds his master in the last storehouse: 「遅かったのう。」 He rides a capstan-hauled lift up the Ledger Spire, pushes Val Amort's "restructuring" off the desk along with the inkstone, and after three phases disarms him with a sheathed mutō-dori. He does not kill him; one cut through the Ledger Engine's spine does the rest. Every seal in the valley goes dark. Three nights later the production registry is posted before the whole Lantern Ward, and at dawn at the Eastern Torii, Sekireisai rehangs the pupils' plaques.

**Theme landing (bible §1.3):** 活人剣 is resolved *mechanically*. The lethal finisher is disabled, the boss is captured, and the "one thing to cut" (scroll fragment 8, b12) is the machine that makes perpetual debt, not the collector.

### 1.2 Play time and mix

| Beat | Type | Place | Objective (JA / EN) | Min | Mix | CP | Site | Unlocks |
|---|---|---|---|---|---|---|---|---|
| ch08.b01 | cinematic | `pl_kakuredani` | 夜明け前の軍議 / War council before dawn | 2.5 | Cin | yes | — | weapon 12, weapon 17 |
| ch08.b02 | horseback_ride (charge) | `pl_causeway` | 土手道を突破せよ / Break through on the causeway | 5.0 | M | yes | — | — |
| ch08.b03 | combat_wave | `pl_outer_bailey` | 輪番撃ちで外郭を制せよ / Take the outer bailey with rotating volleys | 4.0 | C | yes | — | weapon 15, `volley_command` |
| ch08.b04 | production_task (defend) | `pl_outer_bailey` | 野鍛冶と手当所を守れ / Defend the field forge and aid station | 3.0 | P | yes | 1 | — |
| ch08.b05 | production_task (carry) | `pl_outer_bailey` | 兵糧と早合を三つの組へ / Bring rations and cartridges to three squads | 2.0 | P | yes | — | — |
| ch08.b06 | combat_wave | `pl_otemon` | 大手門の封印錨を砕け / Smash the main gate's seal anchors | 4.0 | C | yes | — | weapon 6 |
| ch08.b07 | production_task (escort) | `pl_collateral_cells` | 担保牢の民を避難所へ / Lead the prisoners to the refuge | 4.0 | P | yes | 0 | — |
| ch08.b08 | cinematic | `pl_collateral_cells` | 一番奥の蔵 / The last storehouse | 2.0 | Cin | yes | — | — |
| ch08.b09 | dialogue (ambient) | `pl_collateral_cells` | 塔へ向かえ / Head for the spire | 1.0 | Cin | no | — | — |
| ch08.b10 | combat_wave | `pl_ledger_spire` | 帳簿塔を登れ / Climb the Ledger Spire | 4.0 | C | yes | — | — |
| ch08.b11 | production_task (crank) | `pl_ledger_spire` | 轆轤を回して昇れ / Crank the capstan to rise | 3.0 | P | yes | — | — |
| ch08.b12 | explore_optional | `pl_ledger_spire` | 押収品を調べる / Search the seized goods | 2.0 | E | no | — | — |
| ch08.b13 | cinematic | `pl_ledger_engine` | 帳簿機関 / The Ledger Engine | 2.0 | Cin | yes | — | — |
| ch08.b14 | boss | `pl_ledger_engine` | 大徴収官を捕らえよ / Capture the High Collector | 9.0 | C | yes (+2 phase) | — | — |
| ch08.b15 | cinematic | `pl_ledger_engine` | 封印、消ゆ / The seals go dark | 2.5 | Cin | yes | — | — |
| ch08.b16 | production_task (carry) | `pl_lantern_ward_festival` | 生産改帳を掲げよ / Post the production registry | 2.0 | P | yes | 2 | — |
| ch08.b17 | dialogue (ambient) | `pl_higashi_torii` | 東の鳥居へ / To the Eastern Torii | 1.5 | Cin | no | — | — |
| ch08.b18 | cinematic | `pl_higashi_torii` | 一束 / One sheaf | 1.5 | Cin | no | — | — |
| **Σ** | | | | **55.0** | C 21 · E 2 · S 0 · P 14 · M 5 · Cin 13 | | | |

Mix key (bible §10): C = combat, duel, boss; E = explore; S = stealth; P = production; M = horseback; Cin = cinematic and dialogue. Checkpoint spacing never exceeds 300 target-seconds (rule 8 allows 360), counting the boss's per-phase saves.

Checkpoint times (target-seconds from chapter start): 0, 150, 450, 690, 870, 990, 1230, 1470, 1650, 1890, 2190, 2310, 2460, 2640, 2850, 3000; chapter end 3300.

### 1.3 In-fiction clock

| Beat | Time (temporal hours, autumn) | Note |
|---|---|---|
| b01 | 八月十二日 寅の刻, about 04:00 (bible §9.1) | Council; the host rides out. Four 刻 (about eight hours) remain to noon. |
| b02 | first light, about 05:15 | Civil twilight; the sun is still below the eastern ridge, so the light is soft and blue with no hard shadows |
| b03–b07 | about 05:30–06:30 | Siege of the outer bailey, gate and cells. The sun clears the eastern ridge as the gate falls (b06). |
| b08–b12 | about 06:30–07:00 | Reunion, spire, lift |
| b13–b15 | about 07:00–07:30 | The summit sits above a basin cloud sea (雲海) with the sun only a few degrees over the ridge, so it still reads as sunrise (bible §15.2). Noon remains the deadline. |
| b16 | three days later: 八月十五夜, the mid-autumn full moon (中秋) | Harvest festival, Lantern Ward |
| b17–b18 | the next dawn | Eastern Torii; epilogue |

### 1.4 Locations and layouts

Dimensions are in metres, in the local frame of each space. **Arena rule (bible §14):** everything the campaign adds to Arena 3 or Arena 1 lives in a campaign-only layer (`L_Ch08_Arena3_Campaign`, `L_Ch08_Arena1_Festival`) that practice and multiplayer never load. The kernel-derived arena collision (C2, L6 F4) is untouched, and C2's collision-diff script must still pass with the layer unloaded.

#### pl_kakuredani: Hidden Valley (b01, cinematic only)

The existing League hub (ch02, ch07). The council is held in an 18 × 12 m **陣幕** enclosure on the flat beside the charcoal-burners' huts, open to the south, with SORA-mon curtains on three sides and four 篝火 baskets. The map table is a 戸板 laid on trestles, with 床几 stools around it. Horse lines for 20 riders and 4 pack horses run along the stream 25 m east. There are no gameplay volumes; the cinematic's end state moves the player to `ps_ch08_causeway_start`.

#### pl_causeway: Nekoyama causeway (b02), sublevel `L_Ch08_Causeway`

A new ride space (C3). The playable corridor is about 1.9 km × 0.25 km inside a 3 × 2 km visual landscape (mesh terrain; far ridges as HLOD). The ride runs north toward the castle hill. The **Ledger Spire** (black glass, 160 m above the hill) is visible dead ahead the whole way and is the navigation landmark.

```
            N  ▲  Nekoyama castle hill · Ledger Spire always ahead
 1,750 m ── 冠木門 (outer earthwork gate; breached by Tamakichi) ── vol_outer_koguchi  [EXIT]
 1,580 m ══ 土橋 earthen bridge 20 × 6 m over the 30 m wet outer moat ── G4 ×4 · vol_moat_bridge
 1,380 m ── seal stake 3 (vol_pylon_3)
 1,150 m ── drones ×3 (sp_cw_air_2)
 1,050 m ── seal stake 2 (vol_pylon_2) ········ walker R, 45 m east in the paddies
   900 m ── G3 ×3 on the WEST dike, 35–60 m left of the causeway  (yumi, left arc only)
   700 m ── seal stake 1 + G2 ×4 barricade (vol_pylon_1)
   550 m ── walker L, 60 m west in the paddies
   450 m ── causeway begins: top 7 m wide, 2.2 m above the paddies, willows every 30 m
   350 m ── G1 ×3 barricade at the knoll foot · drones ×3 (sp_cw_air_1)
     0 m ── 物見塚 knoll · forward camp · ps_ch08_causeway_start  [SPAWN, mounted]
```

- **Landmarks:**
  - 稲架 racks of drying rice on the knoll slope (soft obstacles; riders weave between them).
  - Patches of typhoon-flattened rice (倒伏).
  - Willows along the causeway, the moat's stone revetment (石積み), and the burnt-out 冠木門.
- **Routes:** the causeway is the route. Riding off it into the paddies drops Kurimaru to a walk (mud) and raises fear, and a soft "return" nudge steers back (and full auto-steer if the accessibility setting is on). The 土橋 forces single file.
- **Cover and sightlines:** open paddies on both sides give long, clean sightlines. Enemies use graphite barricades (G1, G2, G4) and the dike crest (G3). Walker beams are telegraphed as a cyan line across the causeway.
- **Trigger volumes:** `vol_pylon_1..3`, `vol_moat_bridge`, `vol_outer_koguchi`. `progress_at` uses the spline fraction of `spl_ch08_causeway_charge`.

#### pl_outer_bailey and pl_otemon: Debt Citadel (Arena 3, b03–b06)

Arena 3 footprint 64 × 52 m. Local frame: +X is north (64 m, −32…+32) and +Y is east (52 m, −26…+26). The outer bailey (外郭) is the open ground south of the 二の丸 wall. The main gate (大手門) is a masugata in the north-east corner.

```
        W  Y=-26                                  Y=+26  E
 X=+32  ========m===========m=========m=#===========Y========
        |                               #        1     2    |
        |                               #                   |
        |                               #                   |
 X=+24  |                               #                   |
        |                               K                  3|
        |                               #                  g|
        |     W           M         E   #                  g|
 X=+16  |    ttt         ttt       ttt  #                  g|
        |                               #                  g|
        |                               #####################
        S                                                   |
  X=+8  |                                                   |
        |                                                   |
        |     xxxxxxxxxxxxxxxxxxxxxxxxx                     |
        |                                                   |
  X=+0  |                                                   |
        |                                                   |
        |                                                   |
        |                                                   |
  X=-8  |                                                   |
        |                                                   |
        |           ttttttttttttttttt                       |
        |           v v v v v v v v v                       |
 X=-16  |                                                   |
        |                                                   |
        |                                                   |
        |         F         A                               |
 X=-24  |                                                   |
        |                                                   |
        |                                                   |
        |                                                   |
 X=-32  --------------------------G--------------------------
```

Legend (to scale: one column = 1 m east–west, one row = 2 m north–south):

- `=` 二の丸 石垣 (9 m) topped by the 多聞櫓; `m` marksman loopholes (狭間).
- `#` masugata walls (5 m). `K` 高麗門 (outer gate, west face). `Y` 櫓門 (inner gate, north face), which leads to the ramp and `pl_collateral_cells`.
- `1` `2` seal anchors on the 櫓門's 鏡柱; `3` the anchor on the east wall-walk; `g` the 雁木 steps up to it.
- `W` `M` `E` the pinned League squads (b05) behind `t` 竹束 mantlets.
- `x` alien graphite barricades (b03 wave 1).
- `v` League volley ranks A/B/C (b03) behind a `t` 竹束 line.
- `S` 埋門 sally port (enemy spawn); `F` 野鍛冶 field forge; `A` aid station and refuge; `G` 冠木門 (entry from the causeway).

- **Landmarks:**
  - The 9 m 二の丸 石垣 in 打込接ぎ masonry with 算木積み corners, topped by a 多聞櫓 with 鉄砲狭間 and 石落とし.
  - The alien black-glass spire rising behind it.
  - The forge's smoke column and the SORA 陣幕.
- **Routes:**
  - Center: the direct push over the barricades.
  - West: along the west wall, under the sally port. This is the flank.
  - East: past the masugata's west face, under fire from the gate's turret.
- **Cover:** 竹束 mantlets (campaign layer; League cover that also blocks enemy fire), rice-bale stacks (reuse of `NyaagyuCargoStack`), the graphite barricades, and the forge's anvil block and quench tubs.
- **Sightlines:** the north wall sees the whole bailey (marksmen, 900 ms glint). Volley smoke banks deliberately break these lanes for 4 s.
- **Masugata** (b06): 20 × 20 m, with 5 m inner walls. The 高麗門 is on the west face at (+22, +6) and the 櫓門 on the north face at (+32, +18), at a right angle to each other. Anchor A1 is on the left 鏡柱 at (+30, +15), A2 on the right 鏡柱 at (+30, +21), and A3 on the east wall-walk at (+22, +25), reached by 雁木 steps from (+14, +25).
- **Spawn and exit:** the player enters from the 冠木門 (south) at the end of b02. The masugata's 櫓門 leads out of the arena footprint up the ramp (b07).
- **Trigger volumes:** `vol_outer_bailey` (b03), `vol_nokaji` (b04), `vol_wall_line` (b05), `vol_masugata`, `vol_gangi_top` (b06), `vol_refuge` (b07 drop-off).

#### pl_collateral_cells: the 二の丸 storehouses (b07–b09), sublevel `L_Ch08_Ninomaru`

- **Approach:** a 36 m 坂 ramp with one switchback climbs 9 m from the 櫓門 to a 48 × 30 m courtyard, walled by 土塀 with 狭間.
- **Cells:** four two-storey 米蔵 on the north side, each 5 × 3 ken (about 9.1 × 5.5 m): white 漆喰 over 土蔵 walls and ibushi kawara roofs. Alien glass cell fronts are inset in the original doorways, with inventory-tag rails inside.
- **Other buildings:** a converted 番所 guard office on the east (auditors, with an alarm bell). The **last storehouse** (特別担保蔵) stands at the west end, set back behind its own 土塀 and gate.
- **Cover:** 天水桶 rain barrels, stacked 俵, the storehouse corners, the ramp parapet.
- **Choke point:** the ramp is the escort's chokepoint (b07 wave 3 spawns at its top).
- **Escort path:** `spl_cells_to_refuge`, about 180 m: courtyard 40 m, ramp 36 m, masugata 30 m, then bailey 74 m to the aid station.
- **Exit:** a gate in the north-west corner of the courtyard opens onto the 本丸 approach and the spire (b09).
- **Trigger volumes:** `vol_cells_courtyard`, `vol_ramp`, `vol_deep_kura` (b08), `vol_spire_entrance` (b09 end).

#### pl_ledger_spire: Ledger Spire (b10–b12), sublevel `L_Ch08_Spire`

The old keep is gone. On its stone 天守台 (24 × 20 m, 12 m high) stands a hexagonal black-glass spire, 30 m across the flats and 160 m tall, with seamless extrusions biting into the masonry (bible §15.2).

| Level | Height above the 天守台 | Content |
|---|---|---|
| L1 | 0 m | Entry through the old 穴蔵 (keep basement) door; League supply cache `sp_spire_base` |
| L2 | 9 m | Ramp landing; glass gantry across the void (marksman) |
| L3 | 18 m | Ramp landing; alarm panel; `vol_spire_L3` |
| L4 | 27 m | Ramp landing; gantry; freight lift parked in the void |
| Lift gantries | 55.75 / 84.50 / 113.25 m | b11 wave spawns |
| Gallery | 142 m | Seized-heirloom gallery, 40 × 10 m (b12); north stair, 18 m, to the summit |

- **Core:** a 14 m-diameter central void; a 4 m ramp climbing the walls at about 1:12; continuous railings; ledger-line slit windows admitting low warm sun.
- **Sightlines:** across the void, 14–20 m, plus vertical lines through the gantries.
- **Cover:** the ramp's inner parapet, gantry bulkheads and the lift's machinery housings.
- **Trigger volumes:** `vol_spire_L1_L4` (b10 bounds), `vol_spire_void_edge`, `vol_spire_L3`, `vol_freight_lift`, `vol_heirloom_hall`, `vol_summit_stair`.

#### pl_ledger_engine: Ledger Engine summit (b13–b15), sublevel `L_Ch08_Summit`

```
                        N  Val Amort's desk (seized 文机 on a plinth)
                 ·  ·  ·  ·  ·  ·  ·  ·  ·
             ·   ┌──┬──┬──┬──┬──┬──┬──┐   ·        disc Ø 36 m, 3 m tiles (~104 outside the dais)
          ·      ├──┼──┼──┼──┼──┼──┼──┤      ·     tiles mark amber → void (P2)
         ·       ├──┼──┼ (DAIS Ø8 m)┼──┤       ·   dais +1.2 m; spine Ø4 m rising 22 m
          ·      ├──┼──┼──┼──┼──┼──┼──┤      ·     engine ring Ø60 m, 14 m above the disc
             ·   └──┴──┴──┴──┴──┴──┴──┘   ·        no rail: void edge (fall = respawn + 25 dmg)
                 ·  ·  ·  ·  ·  ·  ·  ·  ·
                        S  stair head (ps_engine_disc_south)  [ENTRY]
```

- **Landmarks:** the rotating ring of glass abacus rods, the spine with its vertebra-like ledger drums and the seam that b14 cuts, the desk, and 360° of cloud sea with Nekoyama and the valley showing through gaps.
- **Cover:** none, deliberately. The dais blocks lines of sight in P1, collateral constructs block them in P2, and P3 is a duel in the open.
- **Arena lock:** `vol_engine_disc`.
- **Exit:** none (b15 cinematic).

#### pl_lantern_ward_festival: Lantern Ward harvest festival (b16), Arena 1 plus `L_Ch08_Arena1_Festival`

The Arena 1 footprint (64 × 52 m, packed-earth streets; bible §15.1) dressed for the autumn festival: about 1,000 lanterns on lines and at shopfronts (提灯, 行灯, 辻行灯), 振売 hawkers, 見世棚 stalls, a small 神楽 stage, susuki grass and new-rice offerings, and returned heirlooms on tables outside the houses.

- **Route:** from the canal steps in the south-west (−30, −20) along the main street, about 110 m, to the 高札場 at the centre (+4, +2). The new 高札 board carries a SORA-mon header.
- **Crowd:** instanced crowd lanes with 1.8 m clearance along the route. There are no weapons and no combat.
- **Trigger volumes:** `vol_fest_a` to `vol_fest_d` (ambient lines), `vol_assembly`, `do_kosatsu_board`.

#### pl_higashi_torii: Eastern Torii (b17–b18), Arena 1 east edge

The existing vermillion torii (`SM_Nyaagyu_ToriiGate` with the `ToriiLacquer` maps and the torii-foot study) stands on the scanned stone path under cedars. The procession area is 30 × 20 m. The name board's stand stands 3 m south of the torii's west pillar, off the shrine axis. Trigger volume `vol_torii`.

### 1.5 Time of day, weather and lighting

| Beats | Sky and key | Weather and FX | Lighting notes | Mac fallback |
|---|---|---|---|---|
| b01 | Blue hour before dawn, sky about 9,000 K; 篝火 1,800 K | Valley mist, breath vapour, sparks | Faces lit from below by bonfires; the SORA 陣幕 glows warm | Two shadowed fire lights; mist as height fog |
| b02 | First light: sun below the ridge, clear sky about 7,500 K; clear, washed air after the typhoon | Dew, hoof dust off the causeway, mud splash, siege smoke columns | Soft shadowless light across the 稲架 and flattened rice; walker beams 8,500 K read strongly; the spire's cyan is the brightest thing in frame | Card rice lodging; 50% dust particles |
| b03–b07 | Pre-sunrise sky about 7,000 K through b05; the sun (3,500 K) clears the ridge during b06 and rises to about 4,300 K by b07; cold cyan emissives on barricades and anchors | White matchlock smoke banks (gameplay), forge sparks, drifting ash | The first sun hits the 櫓門 as the last anchor dies. Keep amber telegraphs distinct from sun and forge light (animated edge decals, bible §15.1). | Smoke as lit cards; at most 8 shadowed lights |
| b08–b09 | Storehouse interior: one high barred window, a shaft of 4,000 K | Dust motes | Sekireisai in half-light; no fill on the cell tags | Baked shaft plus a single spot |
| b10–b12 | Interior 8,000 K strip light; warm 3,800 K shafts through slit windows | Condensation, drifting dust in the void | Deep blacks; the gallery's warm spill marks each case | Software Lumen; shafts as light cards |
| b13–b15 | Above the cloud sea: low sun about 3,800 K a few degrees over the ridge, sky 7,000 K | Wind (VFX only), the cloud sea below, falling tiles | The ring's cyan against the gold; in P3 the cyan dims so the duel reads in warm light | Skybox cloud sea; simplified volumetrics |
| b16 | Full-moon night, moon about 4,100 K; lanterns 1,900 K | Clear, starry; orange-gold 和火 at the end | MegaLights for the lantern field (Windows) | Lantern clusters as emissive cards; 8 shadowed |
| b17–b18 | Dawn: sun 3,500 K rising to 5,000 K | Mist under the cedars, dew on the torii | Vermillion lacquer catching first sun | Height fog; baked sky |

The in-game clock is fixed per beat (no dynamic time of day). The flash-reduction setting (L4) caps the spine-cut flash and the festival fireworks.

---

## 2. Beat list

### 2.1 Beat cards

Each card gives the beat's design, its parameters (the same data as the YAML in §7), fail conditions, dialogue triggers and unlocks. Enemy ids come from bible §7. Numbers are for Normal (真剣).

#### ch08.b01 · cinematic · 夜明け前の軍議 / War council before dawn

| Place | Minutes | Checkpoint | Site | Music |
|---|---|---|---|---|
| `pl_kakuredani` | 2.5 | yes | — | `ch08_council` |

寅の刻 (about 04:00). The League's 陣幕 enclosure in the Hidden Valley, SORA-mon curtains lit from below by 篝火 bonfires, breath visible in the cold. Iota explains the stakes in his manual keigo: Val Amort has invoked **期限の利益の喪失** (acceleration). Every household's whole balance falls due at noon, and anything unpaid, people included, will be collected by the seizure walkers. Oyuki gives the numbers with her soroban, and Kohagi gives the reconnaissance, which lays out the chapter for the player: causeway, gate, cells. Kōzō speaks the catalog anchor line and hands over the **Monofilament Naginata (12)**; Okinu has bound the filament to the blade. Okuzu gives the **Healing Lance (17)**. Toranosuke feeds his grey Credit House haori into the bonfire (bible §6.1). Nyaakoto counts what they protect and ends on 「先生が、お一人」. Oyuki: 「帳尻を、合わせに。」 Hard cut to the host riding out under SORA sashimono, then to first light on the 物見塚 knoll: the player is mounted on Kurimaru with the yari in hand.

Staging: the map table is a 戸板 (door board) on trestles with the castle plan brushed on washi, the 割符 box and the registry. Toranosuke's riders hold their horses at the enclosure's edge; Arashi worries a sleeve (silent, background only). No UI during the cinematic; the unlock notice appears at the cut to gameplay (HUD prompt `ch08.b01.prompt.001`).

**Parameters.**

- **sequence:** `/Game/Campaign/Ch08/Cinematics/LS_Ch08_B01_Council`
- **duration_s:** 150
- **skippable:** yes
- **fallback:** camera_blend
- **end_state:**
  - `player_transform`: ps_ch08_causeway_start
  - `mounted`: kurimaru
  - `equipped`: {hip: 0, back: 18, polearm: 19, side: keep, firearm: keep}

**Fail conditions.** None: non-interactive and skippable.

**Unlocks.** weapon **12** (単分子薙刀 Monofilament Naginata), weapon **17** (治癒の槍 Healing Lance)

**Dialogue triggers.**

Subtitles: `cine@8` → `ch08.b01.iota.001`; `cine@15` → `ch08.b01.iota.002`; `cine@25` → `ch08.b01.oyuki.003`; `cine@34` → `ch08.b01.kohagi.004`; `cine@44` → `ch08.b01.kozo.005`; `cine@50` → `ch08.b01.kozo.006`; `cine@56` → `ch08.b01.okinu.007`; `cine@66` → `ch08.b01.okuzu.008`; `cine@80` → `ch08.b01.toranosuke.009`; `cine@96` → `ch08.b01.nyaakoto.010`; `cine@106` → `ch08.b01.nyaakoto.011`; `cine@116` → `ch08.b01.oyuki.012`.

#### ch08.b02 · horseback_ride (charge) · 土手道を突破せよ / Break through on the causeway

| Place | Minutes | Checkpoint | Site | Music |
|---|---|---|---|---|
| `pl_causeway` | 5.0 | yes | — | `ch08_charge` |

The set piece the whole campaign has been teaching toward: mount, mounted archery to the left, the yari from ch02. Twenty League riders pour off the knoll in a column of twos with Toranosuke on Arashi at Nyaakoto's right (馬手). The route runs 450 m down the knoll and through harvested paddies hung with 稲架 racks, 1,130 m along the raised causeway, then over the 20 m 土橋 and 150 m of moat-side road to the breached outer gate (1,750 m in total).

- **Rhythm:** four barricade groups alternate with three seal stakes (差押え杭), each projecting a cyan barrier across the causeway. A yari thrust at canter or faster breaks a stake as you pass. So do two arrows, but the stakes stand on the causeway ahead and right, so the bow rarely has the angle. That is the lesson: spear forward-right, bow left. A missed stake is broken by the riders behind after 8 s; it costs time and a line from Toranosuke, never a fail.
- **Left-arc targets:** group G3 stands on the west dike 35–60 m off the causeway, where only the yumi can reach from the saddle. The player rises in the abumi and shoots to the left while Kurimaru holds her line.
- **Walkers:** two seizure walkers stand in the paddies and never enter the causeway. Each plants and throws a cyan ground line across the causeway, then fires 1,100 ms later for 1.5 s. The player can gallop through before it fires, or rein in to a trot and let it pass. Both are taught, and the rein-in is prompted. A hit does 30 damage and spooks the horse (fear radius 900 cm, 2.5 s).
- **End:** Tamakichi's siege mortars fell the right-hand walker and blow the outer 冠木門 (scripted). The beat completes on entering `vol_outer_koguchi`.

The player never fires a firearm mounted (bible §4.4, §11). The loadout forces the yari into the polearm slot for this beat and restores the player's choice at b03.

**Parameters.**

- **horse:** kurimaru
- **route:** spl_ch08_causeway_charge
- **route_length_m:** 1750
- **complete:** volume_enter:vol_outer_koguchi
- **gaits:** [walk, trot, canter, gallop]
- **weapons:** [19, 18, 0]
- **arcs_deg:** {19: [-10, 90], 18: [-170, 15], 0: [20, 110]}
- **fear:**
  - `spook_radius_cm`: 900
  - `recover_s`: 2.5
- **horse_stamina:**
  - `max`: 100
  - `gallop_drain_per_s`: 6
  - `canter_regen_per_s`: 3
  - `trot_regen_per_s`: 8
- **auto_steer:** setting
- **dismount_allowed:** no
- **on_horse_down:** checkpoint
- **charge:**
  - `riders`: 20
  - `rival`: {npc: toranosuke, horse: arashi, slot: right}
  - `formation`: column_of_twos
  - `lance_bonus_gallop`: 1.5
  - `catch_up_cm_s`: 150
  - `riders_break_missed_pylon_after_s`: 8
- **objectives:**
  - `pylon_1`: kind destroy, actor seal_stake_01, volume vol_pylon_1, breaks_on [yari_thrust_canter_or_faster, arrow_x2], optional yes
  - `pylon_2`: kind destroy, actor seal_stake_02, volume vol_pylon_2, breaks_on [yari_thrust_canter_or_faster, arrow_x2], optional yes
  - `pylon_3`: kind destroy, actor seal_stake_03, volume vol_pylon_3, breaks_on [yari_thrust_canter_or_faster, arrow_x2], optional yes
- **scripted:**
  - `walker_sweep_beam`: {telegraph: cyan ground line across the causeway, windup_ms: 1100, beam_s: 1.5, width_cm: 300, damage: 30, spooks_horse: yes}
  - `outro`: Tamakichi's siege mortars fell walker_right and breach the outer 冠木門; walker_left withdraws into the bailey (returns in b03 wave 3).
- **waves:**
  1. `start`: `enforcer_rifle` ×3 @ `sp_cw_barricade_1`
  2. `progress_at:0.2`: `drone` ×3 @ `sp_cw_air_1`
  3. `progress_at:0.25`: `seizure_walker` ×1 @ `sp_cw_paddy_left` (invulnerable: yes, script: sweep_only)
  4. `progress_at:0.35`: `enforcer_rifle` ×4 @ `sp_cw_barricade_2`
  5. `progress_at:0.5`: `enforcer_rifle` ×3 @ `sp_cw_west_dike`
  6. `progress_at:0.55`: `seizure_walker` ×1 @ `sp_cw_paddy_right` (invulnerable: yes, script: sweep_only)
  7. `progress_at:0.65`: `drone` ×3 @ `sp_cw_air_2`
  8. `progress_at:0.85`: `enforcer_rifle` ×4 @ `sp_cw_moat_bridge`

**Fail conditions.** Player death → checkpoint (beat start). A horse down (stumble and throw) → checkpoint. A missed seal stake is never a fail.

**Unlocks.** —

**Dialogue triggers.**

- `beat_start` (ambient) → `ch08.b02.toranosuke.001`
- `progress_at:0.05` (ambient) → `ch08.b02.toranosuke.002`
- `alert_state:alert` (bark) → `ch08.b02.enforcer.003`
- `pattern:walker_sweep_beam` (radio) → `ch08.b02.iota.004`
- `volume_enter:vol_pylon_1` (ambient) → `ch08.b02.toranosuke.005`
- `event:horse_spooked` (bark, repeatable, cooldown 30 s) → `ch08.b02.nyaakoto.006`
- `event:enemy_retreat` (bark, repeatable, cooldown 45 s) → `ch08.b02.enforcer.007`
- `progress_at:0.55` (ambient) → `ch08.b02.toranosuke.008`
- `progress_at:0.95` (ambient) → `ch08.b02.tamakichi.009`
- `player_died` (ambient, repeatable, cooldown 120 s) → `ch08.b02.toranosuke.010`

#### ch08.b03 · combat_wave · 輪番撃ちで外郭を制せよ / Take the outer bailey with rotating volleys

| Place | Minutes | Checkpoint | Site | Music |
|---|---|---|---|---|
| `pl_outer_bailey` | 4.0 | yes | — | `ch08_siege` |

The outer bailey is Arena 3's southern two-thirds: open packed earth and gravel, a graphite barricade line across the middle, and the 二の丸 wall with its 多聞櫓 overlooking everything from the north. Tetsugorō forms three ranks of four League gunners behind a line of 竹束 (bamboo-bundle mantlets), and Oyuki hands the order to Nyaakoto. Tamakichi hands over the **Micro-Mortar (15)** as the beat starts.

- **Volley command (`volley_command`):** hold Command to show a 4 m ring at the aim point, up to 60 m away, and release to order. The ready rank shouts 「前の組、構え！」, fires 800 ms later with visible match glow, then files back to reload with 早合 while the next rank steps up. Each rank cycles in 9 s, so an order is available about every 3 s. A volley is deterministic (no random misses): 288 damage split across up to four unshielded targets in the ring, a 2 s shield stagger on shield enforcers, or a small leg stagger on a walker. The white smoke bank it leaves hides that lane for 4 s, for both sides.
- **Wave 1:** six enforcers behind the barricade and a marksman in the 多聞櫓 turret. The volleys pin them while Nyaakoto and Toranosuke flank along the west wall.
- **Wave 2:** three shield enforcers and two blade retainers come out of the 埋門 sally port. A volley staggers the shields; then flank or break them with the yari (bible §7).
- **Wave 3:** the surviving walker from b02 steps out from behind the north turret with three drones. Tamakichi's line teaches the mortar's arc and self-damage (catalog: 460 cm blast, 3 rounds). Mortar hits on the glowing weigh-coils as a leg plants do double damage. Mortar or volleys bring it down.

Easy (稽古) offers an auto-order toggle. Downed gunners stand up after a 3 s revive by any ally; while a rank is down its turn is skipped, so the cycle lengthens.

**Parameters.**

- **bounds:** vol_outer_bailey
- **max_alive:** 8
- **allies:** `league_teppo_rank_a` ×4 (volley_rank, downable yes); `league_teppo_rank_b` ×4 (volley_rank, downable yes); `league_teppo_rank_c` ×4 (volley_rank, downable yes); `toranosuke` (melee_flank, downable yes); `league_yari` ×6 (hold_line, downable yes); `tamakichi` (mortar_crew, downable no); `oyuki` (noncombat, downable no)
- **volley_command:**
  - `ranks`: 3
  - `gunners_per_rank`: 4
  - `weapon`: 5
  - `order_delay_ms`: 800
  - `rank_cycle_s`: 9.0
  - `target_radius_cm`: 400
  - `max_range_cm`: 6000
  - `effect`: {unshielded: 288 damage split across up to 4 targets in the ring, fixed order nearest-first, shield_enforcer: shield stagger 2.0 s, seizure_walker: 8% max HP and a 1.0 s leg stagger}
  - `smoke_obscure_s`: 4.0
  - `easy_auto_order`: yes
- **complete:** all_waves_cleared
- **nonlethal_types:** [bound_conscript]
- **waves:**
  1. `start`: `enforcer_rifle` ×6 @ `sp_ob_barricade`; `marksman` ×1 @ `sp_ob_tamon_turret`
  2. `alive_below:3`: `shield_enforcer` ×3 @ `sp_ob_sally_port`; `blade_retainer` ×2 @ `sp_ob_sally_port`
  3. `prev_cleared`: `seizure_walker` ×1 @ `sp_ob_north_turret`; `drone` ×3 @ `sp_ob_air`

**Fail conditions.** Player death → checkpoint. Allies are downable and revive; they never cause a fail.

**Unlocks.** weapon **15** (小型迫撃砲 Micro-Mortar), mechanic `volley_command`

**Dialogue triggers.**

- `beat_start` (ambient) → `ch08.b03.tetsugoro.001`
- `event:volley_tutorial` (ambient) → `ch08.b03.oyuki.002`
- `event:volley_ready` (bark, repeatable, cooldown 6 s) → `ch08.b03.ashigaru.003`
- `event:volley_ordered` (bark, repeatable, cooldown 2 s) → `ch08.b03.nyaakoto.004`
- `event:volley_rotate` (bark, repeatable, cooldown 8 s) → `ch08.b03.ashigaru.005`
- `event:volley_ordered_3` (ambient) → `ch08.b03.oyuki.006`
- `event:wave_start_2` (bark) → `ch08.b03.enforcer.007`
- `event:wave_start_3` (ambient) → `ch08.b03.tamakichi.008`
- `beat_complete` (ambient) → `ch08.b03.oyuki.009`

#### ch08.b04 · production_task (defend) · 野鍛冶と手当所を守れ / Defend the field forge and aid station

| Place | Minutes | Checkpoint | Site | Music |
|---|---|---|---|---|
| `pl_outer_bailey` | 3.0 | yes | 1 | `ch08_forge` |

The League's field forge (野鍛冶) sits under a 陣幕 in the bailey's south-west corner, with Okuzu's aid station 10 m east of it. Kōzō and Tetsugorō repair what the siege broke and what the villages brought: hoes, sickles, saws, gun locks. The forge is also this chapter's first **supply point**. From here the player can move the Monofilament Naginata into the polearm slot and pick any unlocked firearm.

- **Hold 150 s.** Enforcers push from the sally port, and two grenadiers on the north-west wall lob shells at the forge (visible arc decals, bible §7).
- **At 80 s,** blade retainers and two drones arrive. The drones drop seizure nets on the anvil; while a net is on, Kōzō stops and the bar pauses until the player cuts it (2 s interact).
- **At 115 s,** the Credit House drives four **debt-bound conscripts** at the forge. They are non-lethal only: 峰打ち knockdown, then seal-cut (bible §3.2). Freed conscripts sit down at the aid station. They never count as kills (validation rule 7).

On completion Kōzō says 「……直った。三十六や。」 and the registry writes **修理した道具 36点**. This is **site 1** (共同の修理工房), which ch08 completes before site 0 (see §6).

**Parameters.**

- **defend:**
  - `targets`: {actor: nokaji_forge, hp: 1200}; {actor: aid_station, hp: 800}
  - `duration_s`: 150
  - `fail_on_target_destroyed`: yes
  - `repair_interact`: {actor: nokaji_anvil_net, hold_s: 2.0, rule: a drone net on the anvil pauses repairs and the progress bar until cut}
- **nonlethal_types:** [bound_conscript]
- **allies:** `kozo` (noncombat, downable no); `tetsugoro` (noncombat, downable no); `okuzu` (noncombat, downable no); `league_yari` ×4 (hold_line, downable yes)
- **supply_point:** sp_nokaji
- **waves:**
  1. `start`: `enforcer_rifle` ×4 @ `sp_ob_sally_port`
  2. `after_s:40`: `grenadier` ×2 @ `sp_ob_wall_nw` (focus_target: nokaji_forge)
  3. `after_s:80`: `blade_retainer` ×3 @ `sp_ob_sally_port`; `drone` ×2 @ `sp_ob_air` (behavior: net_anvil)
  4. `after_s:115`: `bound_conscript` ×4 @ `sp_ob_sally_port`
- **registry:** 修理した道具 36点 (Tools repaired, 36 items)

**Fail conditions.** Player death, or the forge (1,200 HP) or aid station (800 HP) reaching 0 → checkpoint.

**Unlocks.** —

**Dialogue triggers.**

- `beat_start` (ambient) → `ch08.b04.kozo.001`, `ch08.b04.okuzu.002`
- `progress_at:0.25` (ambient) → `ch08.b04.kohagi.003`
- `progress_at:0.3` (bark) → `ch08.b04.enforcer.004`
- `event:net_on_anvil` (ambient, repeatable, cooldown 40 s) → `ch08.b04.kozo.005`
- `event:wave_start_4` (bark) → `ch08.b04.conscript.006`
- `site_restored:1` (ambient) → `ch08.b04.kozo.007`

#### ch08.b05 · production_task (carry) · 兵糧と早合を三つの組へ / Bring rations and cartridges to three squads

| Place | Minutes | Checkpoint | Site | Music |
|---|---|---|---|---|
| `pl_outer_bailey` | 2.0 | yes | — | `ch08_siege_low` |

Three League squads have pushed up to 竹束 mantlets 14 m from the 二の丸 wall and are pinned there by marksmen firing through the 多聞櫓 loopholes (狭間). The player carries one bundle at a time: 握り飯 in bamboo-sheath wrappers, plus 早合 cartridges in a 胴乱 pouch. Each trip is about 40 m from the forge, with the katana one-handed, no sprint and no bow.

- **Cover:** every 8–10 m there is a mantlet, a rice-bale stack (existing CargoStack source) or the lee of an abandoned alien barricade.
- **Marksmen:** they show a 900 ms lock glint with the bark 「照準、確定。」. Getting behind cover breaks the lock. A hit makes the player drop the bundle; it can be picked up again, or it returns to the forge pile after 20 s.
- **Each delivery changes the fight:** the west squad suppresses one marksman, the middle squad kills the other, and the third delivery turns all three squads on the wall. That sets up the gate assault.

Registry: **兵糧 36食**.

**Parameters.**

- **carry:**
  - `item`: ration_bundle
  - `count`: 3
  - `pickups`: [pk_nokaji_rations]
  - `dropoffs`: [do_squad_west, do_squad_mid, do_squad_east]
  - `loadout_while_carrying`: [katana_one_hand]
  - `move_speed_mult`: 0.8
  - `drop_on_hit`: yes
  - `dropped_item_returns_after_s`: 20
- **scripted:**
  - `do_squad_west`: squad west suppresses the western marksman (no fire for 20 s)
  - `do_squad_mid`: squad mid's volley kills the eastern marksman
  - `do_squad_east`: all three squads open fire on the 多聞櫓 loopholes (b06 set-up)
- **waves:**
  1. `start`: `marksman` ×2 @ `sp_ob_tamon_loophole`
  2. `progress_at:0.34`: `drone` ×2 @ `sp_ob_air`
- **registry:** 兵糧 36食 (Rations, 36 meals)

**Fail conditions.** Player death → checkpoint. A hit drops the bundle; it can be picked up again or returns to the pile after 20 s. That is not a fail.

**Unlocks.** —

**Dialogue triggers.**

- `beat_start` (ambient) → `ch08.b05.okuzu.001`, `ch08.b05.kohagi.002`
- `pattern:marksman_lock` (bark, repeatable, cooldown 10 s) → `ch08.b05.enforcer.003`
- `item_delivered:do_squad_west` (ambient) → `ch08.b05.ashigaru.004`
- `item_delivered:do_squad_east` (ambient) → `ch08.b05.ashigaru.005`
- `beat_complete` (ambient) → `ch08.b05.oyuki.006`

#### ch08.b06 · combat_wave · 大手門の封印錨を砕け / Smash the main gate's seal anchors

| Place | Minutes | Checkpoint | Site | Music |
|---|---|---|---|---|
| `pl_otemon` | 4.0 | yes | — | `ch08_gate` |

Kōzō hands over the **Kanabō (6)**: oak shod with iron studs, forged at the field forge during b04. The main gate is an early-17th-century **枡形虎口** (masugata): a 20 × 20 m walled courtyard entered through the outer 高麗門 on its west face. The exit is the 櫓門 (gatehouse gate) on its north face, at a right angle. The design makes attackers turn under fire from three sides, and the aliens use it exactly that way.

- **Anchors:** three cyan seal anchors clamp the 櫓門 shut. A1 and A2 are bolted to the left and right 鏡柱 (main gateposts). A3 powers the clamp from the east 多聞櫓 wall-walk, reached by the 雁木 stone steps along the inside of the east wall.
- **Breaking one:** each anchor has three graphite plates. One kanabō strike or a mortar direct hit breaks a plate; the forge hammer takes two strikes. The kanabō follows the kernel rule (combat-rules.md): hold attack for 18 ticks (300 ms) and the strike lands on the 19th, then 800 ms of recovery. Releasing or guarding restarts the windup. After the third plate the core overloads for 2 s and goes dark.
- **Cover:** four League spearmen carry 竹束 mantlets into the masugata and plant them where the player stops. Two gunner ranks at the 高麗門 answer to the same volley command as b03.
- **Waves:** they escalate as anchors fall. The wave triggers use `progress_at` as the fraction of anchors destroyed. The last wave (drones, a grenadier and a marksman on the east wall) arrives once the player is committed to the steps.

The completion condition uses `objectives[]` (same shape as `stealth_zone`). It is a proposed extension for `combat_wave` and is listed in §6.

**Parameters.**

- **bounds:** vol_masugata
- **max_alive:** 7
- **allies:** `toranosuke` (melee_flank, downable yes); `league_teppo_rank_a` ×4 (volley_rank, downable yes); `league_teppo_rank_b` ×4 (volley_rank, downable yes); `league_yari` ×4 (mantlet_bearer, downable yes)
- **volley_command:**
  - `ranks`: 2
  - `gunners_per_rank`: 4
  - `weapon`: 5
  - `order_delay_ms`: 800
  - `rank_cycle_s`: 9.0
  - `target_radius_cm`: 400
  - `max_range_cm`: 4000
  - `note`: same rules as b03; two ranks at the 高麗門
- **complete: objectives:**
  - `anchor_1`: kind destroy, actor seal_anchor_left, plates 3, damage_filter {6: 1, 8: 0.5, 15: 1}, overload_s 2.0
  - `anchor_2`: kind destroy, actor seal_anchor_right, plates 3, damage_filter {6: 1, 8: 0.5, 15: 1}, overload_s 2.0
  - `anchor_3`: kind destroy, actor seal_anchor_wallwalk, plates 3, damage_filter {6: 1, 8: 0.5, 15: 1}, overload_s 2.0
- **nonlethal_types:** [bound_conscript]
- **waves:**
  1. `start`: `enforcer_rifle` ×4 @ `sp_ms_tamon_wall`; `grenadier` ×1 @ `sp_ms_yaguramon_top`
  2. `progress_at:0.33`: `shield_enforcer` ×2 @ `sp_ms_kuguri_door`; `blade_retainer` ×2 @ `sp_ms_kuguri_door`
  3. `progress_at:0.66`: `drone` ×3 @ `sp_ms_air`; `grenadier` ×1 @ `sp_ms_yaguramon_top`; `marksman` ×1 @ `sp_ms_tamon_wall_e`

**Fail conditions.** Player death → checkpoint. Allies are downable and revive; they never cause a fail.

**Unlocks.** weapon **6** (金棒 Kanabō)

**Dialogue triggers.**

- `beat_start` (ambient) → `ch08.b06.kozo.001`
- `volume_enter:vol_masugata` (ambient) → `ch08.b06.toranosuke.002`, `ch08.b06.kohagi.003`
- `alert_state:alert` (bark) → `ch08.b06.enforcer.004`
- `event:objective_done_anchor_1` (radio) → `ch08.b06.iota.005`
- `event:objective_done_anchor_2` (bark) → `ch08.b06.enforcer.006`
- `event:enemy_retreat` (bark) → `ch08.b06.enforcer.007`
- `beat_complete` (ambient) → `ch08.b06.ashigaru.008`

#### ch08.b07 · production_task (escort) · 担保牢の民を避難所へ / Lead the prisoners to the refuge

| Place | Minutes | Checkpoint | Site | Music |
|---|---|---|---|---|
| `pl_collateral_cells` | 4.0 | yes | 0 | `ch08_cells` |

Through the 櫓門, a 36 m 坂 ramp climbs to the 二の丸. Its row of 米蔵 storehouses has been turned into the **担保牢**: plastered 土蔵 with alien glass fronts, and people standing on straw mats wearing hanging inventory tags. The staging keeps their dignity. They are standing, dressed and together, never caged like animals, and the camera never lingers on distress.

- **Open the doors:** seal-cut four cell doors (2 s each). Auditors run for the office bell. If one rings it, wave 2 starts at once.
- **Escort:** twelve prisoners walk 180 m back down the ramp, through the masugata and across the bailey to Okuzu's aid station, which becomes the refuge. They include lower-village farmers, the pupil Takemaru and a child. They move at 260 cm/s and wait when the player is more than 12 m ahead.
- **Signal:** Nyaakoto can signal them to crouch in cover (`hide_on_signal`).
- **Drones:** they drop nets that root prisoners until cut (1.5 s).
- **Downed prisoners:** they can be revived in 3 s, or in 1 s with the **Healing Lance** (campaign rule proposal, §2.3 item 7). They bleed out after 30 s, which fails the beat.
- **Last wave:** the ramp-top wave includes three debt-bound conscripts, the Credit House using people against people one last time.

On arrival Taemon recognises his villagers, and Oyuki opens the refuge: **site 0** (住民の避難所). Takemaru tells Nyaakoto that the master is in the last storehouse and that he should go alone.

**Parameters.**

- **release:**
  - `interact_points`: [cell_door_1, cell_door_2, cell_door_3, cell_door_4]
  - `per_point_s`: 2.0
  - `action`: seal_cut
- **escort:**
  - `npcs`: {group: prisoners_a, count: 4}; {group: prisoners_b, count: 4}; {group: prisoners_c, count: 3, includes: [takemaru]}; {group: child_1, count: 1}
  - `path`: spl_cells_to_refuge
  - `path_length_m`: 180
  - `speed_cm_s`: 260
  - `wait_for_player_cm`: 1200
  - `fail_on_npc_death`: yes
  - `hide_on_signal`: yes
  - `npc_health`: 150
  - `down_revive_s`: 3
  - `bleedout_s`: 30
  - `healing_lance_revive_s`: 1.0
- **scripted:**
  - `auditor_alarm`: an auditor who reaches the office bell triggers wave 2 immediately
- **nonlethal_types:** [bound_conscript]
- **waves:**
  1. `start`: `enforcer_rifle` ×3 @ `sp_cells_guard`; `auditor` ×2 @ `sp_cells_office`
  2. `progress_at:0.4`: `drone` ×3 @ `sp_cells_air` (behavior: net_npc, net_cut_s: 1.5)
  3. `progress_at:0.7`: `blade_retainer` ×2 @ `sp_ramp_top`; `shield_enforcer` ×1 @ `sp_ramp_top`; `bound_conscript` ×3 @ `sp_ramp_top`

**Fail conditions.** Player death, or any prisoner bleeding out (30 s after going down, unrevived) → checkpoint.

**Unlocks.** —

**Dialogue triggers.**

- `beat_start` (ambient) → `ch08.b07.kohagi.001`
- `event:door_1_open` (ambient) → `ch08.b07.villager.002`, `ch08.b07.nyaakoto.003`
- `event:door_2_open` (ambient) → `ch08.b07.child.004`
- `event:door_3_open` (ambient) → `ch08.b07.takemaru.005`
- `event:first_hide_signal` (ambient) → `ch08.b07.nyaakoto.006`
- `volume_enter:vol_refuge` (ambient) → `ch08.b07.taemon.007`
- `site_restored:0` (ambient) → `ch08.b07.oyuki.008`
- `beat_complete` (ambient) → `ch08.b07.takemaru.009`

#### ch08.b08 · cinematic · 一番奥の蔵 / The last storehouse

| Place | Minutes | Checkpoint | Site | Music |
|---|---|---|---|---|
| `pl_collateral_cells` | 2.0 | yes | — | `ch08_reunion` |

The last storehouse sits apart behind a 土塀, and its glass door is tagged 特別担保 (special collateral). Inside, lit only by a high barred window, Sekireisai sits in seiza on a straw mat. He is thinner, his 十徳 is gone and his kimono is plain, but his back is straight. Nyaakoto seal-cuts the door, kneels and says 「先生。」 Sekireisai takes two beats and says 「遅かったのう。」 (approved humor beat 8: dry, not a gag, no music sting). Then: 「して、何を数えてきた。」 Nyaakoto answers with what they protect. Toranosuke, who followed at a distance, kneels in the doorway: 「合わせる顔が、ございません。」 Sekireisai: 「顔はそこにある。上げよ。」 Toranosuke raises his head. Performance note: the master's warmth is in a single hand on Toranosuke's shoulder as he stands, and nothing else.

**Parameters.**

- **sequence:** `/Game/Campaign/Ch08/Cinematics/LS_Ch08_B08_LastStorehouse`
- **duration_s:** 120
- **skippable:** yes
- **fallback:** camera_blend
- **end_state:**
  - `player_transform`: ps_deep_kura_door
  - `equipped`: keep

**Fail conditions.** None: non-interactive and skippable.

**Unlocks.** —

**Dialogue triggers.**

Subtitles: `cine@16` → `ch08.b08.nyaakoto.001`; `cine@22` → `ch08.b08.sekireisai.002`; `cine@29` → `ch08.b08.nyaakoto.003`; `cine@35` → `ch08.b08.sekireisai.004`; `cine@42` → `ch08.b08.sekireisai.005`; `cine@48` → `ch08.b08.nyaakoto.006`; `cine@66` → `ch08.b08.sekireisai.007`; `cine@72` → `ch08.b08.toranosuke.008`; `cine@80` → `ch08.b08.sekireisai.009`.

#### ch08.b09 · dialogue (ambient) · 塔へ向かえ / Head for the spire

| Place | Minutes | Checkpoint | Site | Music |
|---|---|---|---|---|
| `pl_collateral_cells` | 1.0 | no | — | `ch08_reunion_walk` |

Walk and talk across the 二の丸 toward the 本丸 and the base of the spire, with player control kept. Nyaakoto offers his wakizashi. Sekireisai refuses: he will guard the refugees **unarmed** (無刀), because empty hands are better before the people. He gives the one piece of teaching the finale needs, without naming the technique: at the end his opponent will raise his blade high, and then Nyaakoto must keep his own sword in its sheath. Nyaakoto admits he learned mutō-dori alone (ch06). 「一人で覚えたなら、本物じゃ。行け。」 Sekireisai turns back toward the refuge; Toranosuke, Kohagi, Tetsugorō and two engineers join Nyaakoto at the spire door. The beat ends in `vol_spire_entrance`.

**Parameters.**

- **trigger:** beat_start
- **interrupt:** queue
- **camera:** soft_lookat
- **complete:** volume_enter:vol_spire_entrance

**Fail conditions.** None: walk-and-talk; it cannot fail.

**Unlocks.** —

**Dialogue triggers.**

- `beat_start` (ambient) → `ch08.b09.nyaakoto.001`, `ch08.b09.sekireisai.002`, `ch08.b09.sekireisai.003`, `ch08.b09.nyaakoto.004`, `ch08.b09.sekireisai.005`

#### ch08.b10 · combat_wave · 帳簿塔を登れ / Climb the Ledger Spire

| Place | Minutes | Checkpoint | Site | Music |
|---|---|---|---|---|
| `pl_ledger_spire` | 4.0 | yes | — | `ch08_spire` |

The fight becomes vertical. The spire's interior is a hexagonal shaft around a 14 m central void. A 4 m spiral ramp climbs the walls through four landings (L1–L4, 9 m apart), and 2 m glass gantries cross the void at L2 and L4. Slit windows cut in ledger-line patterns let low, warm sun into cold 8,000 K strip light.

- **Sightlines:** they run across the void, 14–20 m. The L2 marksman on the far gantry is the first problem. The yumi (visible arc) and the mortar (arcing over the railings) are the tools, and melee has to walk the ramp.
- **Waves:** shield enforcers and blade retainers come down the ramp from L3 in wave 2. Wave 3 fills the void with drones while a grenadier drops shells from the L4 gantry and two auditors run for alarm panels.
- **Allies:** Kohagi and Toranosuke fight as downable allies. Tetsugorō and two League engineers follow and hide; they carry the timber capstan for b11.
- **Search barks:** breaking line of sight around the ramp's central column puts enforcers into the search state (lane L2's AI states), which triggers the search bark.
- **Falls:** railings are continuous. There is no instant-death fall in combat; the void edge only triggers Toranosuke's warning.
- **Supply point:** the engineers' cache at the base of L1.

**Parameters.**

- **bounds:** vol_spire_L1_L4
- **max_alive:** 7
- **allies:** `kohagi` (skirmisher, downable yes); `toranosuke` (melee_flank, downable yes); `tetsugoro` (noncombat_follow, downable no); `league_engineer` ×2 (noncombat_follow, downable no)
- **complete:** all_waves_cleared
- **scripted:**
  - `auditor_alarm`: an auditor at an alarm panel drops a shutter over the L3 shortcut (route gets longer, never a fail)
- **supply_point:** sp_spire_base
- **nonlethal_types:** [bound_conscript]
- **waves:**
  1. `start`: `enforcer_rifle` ×4 @ `sp_sp_L2_ramp`; `marksman` ×1 @ `sp_sp_L2_gantry_far`
  2. `alive_below:2`: `shield_enforcer` ×2 @ `sp_sp_L3_ramp_down`; `blade_retainer` ×2 @ `sp_sp_L3_ramp_down`
  3. `volume_enter:vol_spire_L3`: `drone` ×4 @ `sp_sp_void_air`; `grenadier` ×1 @ `sp_sp_L4_gantry`; `auditor` ×2 @ `sp_sp_L4_office`

**Fail conditions.** Player death → checkpoint. Allies are downable and revive; they never cause a fail.

**Unlocks.** —

**Dialogue triggers.**

- `beat_start` (ambient) → `ch08.b10.kohagi.001`
- `alert_state:alert` (bark) → `ch08.b10.enforcer.002`
- `alert_state:search` (bark, repeatable, cooldown 30 s) → `ch08.b10.enforcer.003`
- `volume_enter:vol_spire_void_edge` (ambient) → `ch08.b10.toranosuke.004`
- `volume_enter:vol_spire_L3` (radio) → `ch08.b10.iota.005`
- `event:wave_start_3` (ambient) → `ch08.b10.tetsugoro.006`
- `event:enemy_retreat` (bark) → `ch08.b10.enforcer.007`

#### ch08.b11 · production_task (crank) · 轆轤を回して昇れ / Crank the capstan to rise

| Place | Minutes | Checkpoint | Site | Music |
|---|---|---|---|---|
| `pl_ledger_spire` | 3.0 | yes | — | `ch08_lift` |

Iota has cut the freight lift's power through his key-slate (the ch06 relay access), so the lift is dead. Tetsugorō lashes a timber **轆轤** (vertical capstan with a pawl) to the 6 × 6 m platform and wraps the lift's own hawser around its drum. The platform winds itself up the void from 27 m to the heirloom gallery at 142 m: a moving arena. Turning inside the band (0.4–1.0 turns/s) raises the lift. Faster than the band burns the rope (progress stops and smokes); slower than the band lets the pawl slip back 1% per second.

- **Coop:** when the player leaves the bars to fight, Tetsugorō and the two engineers each keep turning at 0.15 turns/s. With all three working, their combined 0.45 turns/s offsets most of the ordinary decay of 1% of 48 turns each second (0.48 turns/s), so the lift slips by 0.03 turns/s and roughly holds its height. This is a per-person contribution, not a decay waiver; unavailable crew members contribute nothing.
- **Waves:** they come from the gantries the platform passes at 55.75, 84.50 and 113.25 m. Drones try to cut the hawser (decay ×3 while touching). Riflemen fire from a gantry. At 113.25 m a shield enforcer and two retainers jump onto the platform.
- **Height contract:** the three gantries are at 25%, 50% and 75% of the 115 m travel above L4 (27 m). Their heights follow these authored release thresholds, so boarders reach a platform passing their landing.
- **Clouds:** past 60% the platform rises through the morning cloud sea and the light turns gold.

Toranosuke and Kohagi step off at the gallery landing to hold the shaft against reinforcements: from here Nyaakoto goes alone.

**Parameters.**

- **crank:**
  - `actor`: lift_capstan_01
  - `turns_required`: 48
  - `turn_rate_band`: [0.4, 1.0]
  - `progress_decay_per_s`: 0.01
  - `stamina_per_turn`: 5
  - `interruptible`: yes
  - `coop_npc`: {npcs: [tetsugoro, league_engineer_1, league_engineer_2], turns_per_s_per_npc: 0.15}
  - `moving_platform`: {actor: freight_lift_platform, size_cm: [600, 600], travel_cm: 11500, from: L4_27m, to: hall_142m}
  - `rope_hazard`: {rule: while a drone's cutter touches the hawser, decay x3, cut_drone_to_clear: yes}
- **nonlethal_types:** [bound_conscript]
- **waves:**
  1. `progress_at:0.25`: `drone` ×3 @ `sp_lift_gantry_5575cm` (behavior: cut_rope)
  2. `progress_at:0.5`: `enforcer_rifle` ×3 @ `sp_lift_gantry_8450cm`
  3. `progress_at:0.75`: `shield_enforcer` ×1 @ `sp_lift_gantry_11325cm` (behavior: board_platform); `blade_retainer` ×2 @ `sp_lift_gantry_11325cm` (behavior: board_platform)

**Fail conditions.** Player death → checkpoint. Lift progress only decays; it never fails.

**Unlocks.** —

**Dialogue triggers.**

- `beat_start` (ambient) → `ch08.b11.tetsugoro.001`
- `event:crank_turn_6` (bark, repeatable, cooldown 8 s) → `ch08.b11.ashigaru.002`
- `progress_at:0.25` (ambient) → `ch08.b11.kohagi.003`
- `event:player_left_capstan` (ambient, repeatable, cooldown 45 s) → `ch08.b11.tetsugoro.004`
- `progress_at:0.5` (bark) → `ch08.b11.enforcer.005`
- `progress_at:0.75` (radio) → `ch08.b11.iota.006`
- `beat_complete` (ambient) → `ch08.b11.toranosuke.007`

#### ch08.b12 · explore_optional · 押収品を調べる / Search the seized goods

| Place | Minutes | Checkpoint | Site | Music |
|---|---|---|---|---|
| `pl_ledger_spire` | 2.0 | no | — | `ch08_heirlooms` |

A 40 × 10 m curved gallery on the spire's north-east face. Floor-to-ceiling black glass looks out over the cloud sea. Warm objects sit under cold light on graphite plinths, each with an alien valuation label: a farmer's 鋤 (0), a child's 張子 toy (三文, three coppers), Tamakichi's master's festival mortar (0), lacquer bowls, a temple bell and the Washio house sword tagged 「代物弁済」 (payment in kind).

There are no markers. The player finds things by light and path: warm spill-light marks each case. The Nyaagyu 陣羽織 hangs under an alien seizure label that covers its mon. The aliens never display the SORA mon (bible §17), so the player tears the label off to reveal it.

The scroll case holds **scroll fragment 8**, the last: Sekireisai's line on 活人剣, voiced as a memory. It re-frames the finale: the life-giving sword finds the one thing to cut. The exit is the north stair to the summit, with a hint after 60 s idle.

**Parameters.**

- **volume:** vol_heirloom_hall
- **pois:** `poi_child_toy` (lore); `poi_washio_sword` (cache, ch08.c03); `poi_tamakichi_mortar` (lore, ch08.c04); `poi_scroll_case` (lore, ch08.c05); `poi_covered_mon` (lore); `poi_cloud_window` (vista)
- **rewards:** [ch08.c03, ch08.c04, ch08.c05, arrows_12]
- **exit_hint_after_s:** 60
- **requires:** ch08.b11
- **optional:** yes

**Fail conditions.** None (optional).

**Unlocks.** —

**Dialogue triggers.**

- `volume_enter:vol_heirloom_hall` (radio) → `ch08.b12.iota.001`
- `event:poi_child_toy` (ambient) → `ch08.b12.nyaakoto.002`
- `event:collectible_ch08_c03` (ambient) → `ch08.b12.nyaakoto.003`
- `event:collectible_ch08_c05` (ambient) → `ch08.b12.sekireisai.004`
- `idle_s:60` (radio) → `ch08.b12.iota.005`

#### ch08.b13 · cinematic · 帳簿機関 / The Ledger Engine

| Place | Minutes | Checkpoint | Site | Music |
|---|---|---|---|---|
| `pl_ledger_engine` | 2.0 | yes | — | `ch08_amort_intro` |

The summit disc sits above the clouds with the low sun just clearing the eastern ridge. The Ledger Engine's glass-abacus ring turns overhead around the spine. Val Amort stands behind a seized Nyaagyu 文机 (low writing desk) that the Credit House has raised on a graphite plinth to standing height. On it lie a contract and Sekireisai's inkstone.

He welcomes debtor 7031 and offers **restructuring**: the rate unchanged, the term perpetual. The catalog anchor line (「最後の帳簿は私が守る…」) is the only moment his politeness drops into plain speech. 「署名を。硯は用意してございます。……貴殿の師のものですが。」

Nyaakoto holds his gaze and, without a word, pushes the inkstone off the edge (approved humor beat 7). It falls a long way, and we never hear it land. Val Amort: 「……備品の毀損として、計上いたします。」 Nyaakoto: 「記せ。それが、お前の最後の一行だ。」 Val Amort sets down his pen and lifts his cane: 「交渉は決裂。元本を、回収いたします。」 Cut to gameplay.

**Parameters.**

- **sequence:** `/Game/Campaign/Ch08/Cinematics/LS_Ch08_B13_Restructuring`
- **duration_s:** 120
- **skippable:** yes
- **fallback:** camera_blend
- **end_state:**
  - `player_transform`: ps_engine_disc_south
  - `equipped`: keep
- **requires:** ch08.b11

**Fail conditions.** None: non-interactive and skippable.

**Unlocks.** —

**Dialogue triggers.**

Subtitles: `cine@12` → `ch08.b13.valamort.001`; `cine@20` → `ch08.b13.valamort.002`; `cine@30` → `ch08.b13.nyaakoto.003`; `cine@36` → `ch08.b13.valamort.004`; `cine@46` → `ch08.b13.valamort.005`; `cine@72` → `ch08.b13.valamort.006`; `cine@82` → `ch08.b13.nyaakoto.007`; `cine@94` → `ch08.b13.valamort.008`.

#### ch08.b14 · boss · 大徴収官を捕らえよ / Capture the High Collector

| Place | Minutes | Checkpoint | Site | Music |
|---|---|---|---|---|
| `pl_ledger_engine` | 9.0 | yes + each phase | — | `ch08_amort` |

Three phases with a checkpoint at each (bible §8, §12.1), then capture, not a kill. Summary below; §2.2 has the full pattern tables.

- **P1, the Collector (100–70%).** The existing prototype's deterministic pattern: a locked-aim cyan ledger beam (550 ms tracking + 900 ms lock = 1,450 ms) and an amber cleave (1,200 ms, 330 cm, ±28°). Three ledger shards orbit him and intercept arrows and bullets; break all three to stagger him for 3 s. Counterplay: guard or awase the cleave for a 1.2 s stagger, and sidestep the beam.
- **P2, the Seizure (70–40%).** He retreats to the spine's dais behind a seizure shield. The disc's 3 m tiles are marked with pulsing amber edges and fall away into the clouds 1,500 ms later, in a fixed cycle of three patterns. **Collateral constructs** rise from heaps of seized goods. Destroying a construct's cyan core *releases* the goods, which settle gently to the floor and are never smashed. When no construct stands, his shield drops for 10 s.
- **P3, the Cane (40–0%).** The seizure field shuts off and the ring lowers. He draws the blade from his sword-cane. Quick pair (500 ms), locked thrust (600 ms, cyan, cannot be parried: roll around it with 転), and the **final foreclosure** overhead (1,000 ms, amber, `muto_eligible`). Parrying it with the blade drawn staggers him. **Sheathing** and meeting it inside the 180 ms mutō-dori window disarms him and ends the fight at any HP in P3. At 1% HP his HP stops falling; he repeats the foreclosure every 4 s and the prompt appears.

After the disarm Val Amort kneels, and his cane is in Nyaakoto's paws. The prompt 「機関の背骨を断て」 appears. Nyaakoto draws and cuts the spine's seam in one 抜き付け (draw-cut): 「一太刀で、足りる。」

**Parameters.**

- **boss:** boss_val_amort
- **arena:**
  - `volume`: vol_engine_disc
  - `lock`: yes
- **phases:** P1 from 100% → `amort_p1_collector` (~150 s); P2 from 70% → `amort_p2_seizure`, adds `collateral_constructs`, arena_mod `seizure_tiles` (~180 s); P3 from 40% → `amort_p3_cane`, arena_mod `field_off` (~210 s)
- **defeat:** capture
- **finisher:** muto_dori
- **lethal_finisher:** no
- **checkpoint_per_phase:** yes
- **telegraph:**
  - `palette`: default
  - `min_windup_ms`: 500
- **intro_cinematic:** ch08.b13
- **outro_cinematic:** ch08.b15
- **hp:**
  - `normal`: 2400
  - `easy`: 1900
  - `hard`: 2800
- **post_defeat:**
  - `interact`: engine_spine
  - `hold_s`: 1.5
  - `animation`: nukitsuke_draw_cut
- **pattern_tables:** see §2.2 and the top-level pattern_tables block in §7 (proposal for L3 bosses.json)

**Fail conditions.** Player death → the current phase's checkpoint. A fall through a void tile is **not** death: 25 damage and a respawn on an edge tile.

**Unlocks.** —

**Dialogue triggers.**

- `boss_phase:3` (bark) → `ch08.b14.valamort.006`
- `player_died` (bark, repeatable, cooldown 0 s) → `ch08.b14.valamort.008`
- `event:muto_dori_success` (bark) → `ch08.b14.valamort.009`
- `event:muto_dori_success` (ambient) → `ch08.b14.nyaakoto.010`
- `event:spine_prompt` (ambient) → `ch08.b14.nyaakoto.011`
- `event:first_foreclosure` (ambient) → `ch08.b09.sekireisai.003`
- `pattern:amort_ledger_beam` (captioned boss telegraph) → `ch08.b14.valamort.001`
- `pattern:amort_cleave` (captioned boss telegraph) → `ch08.b14.valamort.002`
- `pattern:amort_shards` (captioned boss telegraph) → `ch08.b14.valamort.003`
- `pattern:amort_seizure_field` (captioned boss telegraph) → `ch08.b14.valamort.004`
- `pattern:construct_spawn` (captioned boss telegraph) → `ch08.b14.valamort.005`
- `pattern:amort_final_foreclosure` (captioned boss telegraph) → `ch08.b14.valamort.007`

#### ch08.b15 · cinematic · 封印、消ゆ / The seals go dark

| Place | Minutes | Checkpoint | Site | Music |
|---|---|---|---|---|
| `pl_ledger_engine` | 2.5 | yes | — | `ch08_release` |

The spine splits along its seam. The ring stops, and its glass rods fall silent one by one. A ripple of darkness runs down the spire and out across the valley. Toranosuke, Kohagi and Oyuki come up the north stair. Val Amort, kneeling: 「帳簿なくして、この谷に秩序はございません。」 Oyuki: 「帳簿なら、ございます。わたくしどもの帳簿が。」 Toranosuke binds him with a 捕縄: 「縄目の恥とは言わせん。生きて、数えろ。」

The montage follows, each shot a location from an earlier chapter as its cyan seal dies:

- the estate kura (ch02);
- the First Weir sluice, with Taemon (ch04);
- the loom hall's levy gauges, with Okinu (ch05);
- the Lantern Ward's door balances, with Tōkichi (ch03);
- the refugees at the gate, where Sekireisai stands unarmed among them and allows himself one small nod.

It ends back at the summit on Nyaakoto looking down at the Lantern Ward, speaking the catalog anchor line 「あとはこの街だ。誰も借りに縛られぬように。」 Fade: 「三日後」 (three days later).

**Parameters.**

- **sequence:** `/Game/Campaign/Ch08/Cinematics/LS_Ch08_B15_SealsDark`
- **duration_s:** 150
- **skippable:** yes
- **fallback:** camera_blend
- **end_state:**
  - `player_transform`: ps_festival_canal_steps
  - `equipped`: {all: stowed}

**Fail conditions.** None: non-interactive and skippable.

**Unlocks.** —

**Dialogue triggers.**

Subtitles: `cine@14` → `ch08.b15.valamort.001`; `cine@21` → `ch08.b15.oyuki.002`; `cine@30` → `ch08.b15.toranosuke.003`; `cine@56` → `ch08.b15.taemon.004`; `cine@72` → `ch08.b15.okinu.005`; `cine@88` → `ch08.b15.tokichi.006`; `cine@128` → `ch08.b15.nyaakoto.007`.

#### ch08.b16 · production_task (carry) · 生産改帳を掲げよ / Post the production registry

| Place | Minutes | Checkpoint | Site | Music |
|---|---|---|---|---|
| `pl_lantern_ward_festival` | 2.0 | yes | 2 | `ch08_festival` |

Three days later: the Lantern Ward's autumn festival on the night of the full moon, the Arena 1 festival variant. There is no combat and no weapon is drawn. The player carries the lacquered box holding the bound **生産改帳** (production registry) from the canal steps to the 高札場 assembly, about 110 m through the crowd.

- **Crowd:** hawkers (振売) with shoulder poles, 見世棚 stalls, a small 神楽 stage, and children with paper 団扇 printed with the SORA mon.
- **Heirlooms:** returned ones stand on tables outside the houses, some still wearing their seizure tags.
- **The terminal:** the dead StreetDebtTerminal from ch03 stands dark, chalked with League marks by children.
- **Ambient lines:** they trigger as the player passes: Tōkichi's thousand lanterns, Otane's new rice, and Taemon's payoff 「この紙は、ええ紙や。」

At the board Tamakichi asks to set off the fireworks, and Oyuki says only after it is in the ledger (restrained humor). The player pastes the pages (3 s hold). Oyuki posts the registry before everyone: **site 2** (解放の集会所). Its restored text matches the catalog: residents take charge of their own records. Small orange-gold 和火 fireworks follow; there are no colored bursts (§4.6).

**Parameters.**

- **carry:**
  - `item`: public_registry_box
  - `count`: 1
  - `pickups`: [pk_registry_canal_steps]
  - `dropoffs`: [do_kosatsu_board]
  - `loadout_while_carrying`: []
  - `move_speed_mult`: 0.7
  - `drop_on_hit`: no
  - `post_interact`: {actor: kosatsu_board, hold_s: 3.0, action: paste_pages}
- **combat:** no
- **crowd:**
  - `windows_visible`: 120
  - `mac_visible`: 60
  - `path_clearance_cm`: 180
  - `no_markers`: no

**Fail conditions.** None: there is no combat and it cannot fail.

**Unlocks.** —

**Dialogue triggers.**

- `beat_start` (ambient) → `ch08.b16.oyuki.001`
- `volume_enter:vol_fest_a` (ambient) → `ch08.b16.resident.002`
- `volume_enter:vol_fest_b` (ambient) → `ch08.b16.tokichi.003`
- `volume_enter:vol_fest_c` (ambient) → `ch08.b16.otane.004`
- `volume_enter:vol_fest_d` (ambient) → `ch08.b16.taemon.005`
- `volume_enter:vol_assembly` (ambient) → `ch08.b16.tamakichi.006`, `ch08.b16.oyuki.007`
- `site_restored:2` (ambient) → `ch08.b16.oyuki.008`

#### ch08.b17 · dialogue (ambient) · 東の鳥居へ / To the Eastern Torii

| Place | Minutes | Checkpoint | Site | Music |
|---|---|---|---|---|
| `pl_higashi_torii` | 1.5 | no | — | `ch08_torii_dawn` |

At the assembly Kohagi says the catalog anchor line (「東の鳥居で待つ…」). Fade to dawn at the Eastern Torii, where the Nekoyama road turns home to Nyaagyu. The procession gathers: pack horses with 荷鞍, Kurimaru carrying the dojo's **名札掛け** (name board) recovered from the flagship in ch07, and villagers going home with their heirlooms. The player walks the last 60 m.

- **Iota:** at the torii, 「朝というものは……無償で来るのですね。」
- **If the player took the Washio sword in b12:** Nyaakoto returns it. Toranosuke: 「……借りが、できたな。」 Nyaakoto: 「貸しではない。」
- **The name board:** Sekireisai has it set on a plain wooden stand beside the torii's base; nothing is hung on the torii itself (§4.6). He **rehangs the plaques**: Toranosuke's back in its place, and Nyaakoto's moved up the board. This is the only `blocking` segment, capped at 20 s.
- **Final exchange (bible §9):** 「剣は、作る手を守るためにある。」 「……ようやく、一本じゃ。」

**Parameters.**

- **trigger:** beat_start
- **interrupt:** queue
- **camera:** soft_lookat
- **blocking_max_s:** 20
- **complete:** event:plaque_rehang_done

**Fail conditions.** None: walk-and-talk; it cannot fail.

**Unlocks.** —

**Dialogue triggers.**

- `beat_start` (ambient) → `ch08.b17.kohagi.001`
- `volume_enter:vol_torii` (ambient) → `ch08.b17.iota.002`
- `event:washio_sword_return` (ambient, only if `collectible:ch08.c03`) → `ch08.b17.nyaakoto.003`, `ch08.b17.toranosuke.004`, `ch08.b17.nyaakoto.005`
- `event:plaque_rehang` (blocking) → `ch08.b17.sekireisai.006`, `ch08.b17.sekireisai.007`, `ch08.b17.nyaakoto.008`, `ch08.b17.sekireisai.009`

#### ch08.b18 · cinematic · 一束 / One sheaf

| Place | Minutes | Checkpoint | Site | Music |
|---|---|---|---|---|
| `pl_higashi_torii` | 1.5 | no | — | `credits_main` |

The procession passes under the torii into the sunrise. A short epilogue montage plays over the first credits:

- returned heirlooms in their homes: Okinu's mother's shuttle on her loom (found in ch06.b07), Tamakichi's master's mortar beside the festival stage, the Washio sword in a 床の間 if it was returned;
- the SORA nobori over the rebuilt dojo's frame;
- a registry page posted at every 高札場.

Last, in Taemon's village granary (郷蔵): Val Amort, coat gone, sits among barley sheaves with a tally board, while Iota stands over him with a brush. 「……一束。」 Iota: 「はい。一束、確かに在ります。」 Taemon, at the door: 「数え終わったら、蒔きに行くで。麦は秋に蒔くんや。」 (approved humor beat 9). Cut to the vermillion SORA seal and the full credits (skippable, outside the 55-minute budget).

**Parameters.**

- **sequence:** `/Game/Campaign/Ch08/Cinematics/LS_Ch08_B18_Epilogue`
- **duration_s:** 90
- **skippable:** yes
- **fallback:** camera_blend
- **end_state:**
  - `player_transform`: None
  - `equipped`: None
  - `next`: credits_full

**Fail conditions.** None: non-interactive and skippable.

**Unlocks.** —

**Dialogue triggers.**

Subtitles: `cine@40` → `ch08.b18.valamort.001`; `cine@45` → `ch08.b18.iota.002`; `cine@52` → `ch08.b18.taemon.003`.


### 2.2 Boss: 大徴収官 ヴァル・アモルト (`boss_val_amort`)

- **Health:** 2,400 on Normal (1,900 Easy, 2,800 Hard), a proposal for L3.
- **Phases:** thresholds at 70% and 40%, each with a checkpoint.
- **Telegraphs** follow bible §8:
  - Cyan means a locked aim or beam; amber means a cleave or area attack.
  - Every telegraph precedes damage by at least its windup, and the minimum windup is 500 ms.
  - Easy adds 30% to windups and Hard subtracts 15%.
  - Every voice bark is captioned and is itself a telegraph.
- **Deterministic:** no attack choice is random. P1 reuses the existing prototype's selection rule and timings (`SoraCharacter.cpp`: beam windup 1.45 s, cleave windup 1.2 s, recovery 1.15 s falling to 0.9 s, approach to 740 cm).

**P1 `amort_p1_collector` (100–70%, ~150 s).** Deterministic: approach at 0.72 move scale until <= 740 cm; beam if distance > 340 cm or attack_index is even, else cleave (existing prototype rule).

| Attack | Colour | Windup (ms) | Damage | Guard | Parry / counter | Recovery (ms) | Notes |
|---|---|---|---|---|---|---|---|
| `amort_ledger_beam` | cyan | 1450 | 22 | front guard absorbs 70% | no; sidestep out of the locked line | 1150 | track_ms 550; lock_ms 900; length_cm 1500; bark at lock_start |
| `amort_cleave` | amber | 1200 | 30 | yes | awase within 260 ms -> 1.2 s stagger | 1150 | reach_cm 330; arc_deg 28; bark at windup_start |
| `amort_shards` | cyan | — | — | — | — | — | count 3; orbit_radius_cm 250; shard_hp 104; respawn_s 20; all_broken reconcile_stagger 3000 ms, damage taken x1.5; intercepts [arrows, bullets, mortar_shells]; bark at spawn |

**P2 `amort_p2_seizure` (70–40%, ~180 s).** On the dais behind a seizure shield while any construct is alive; shield drops for 10 s when none are alive; uses ledger_beam (recovery 900 ms) and cleave (recovery 900 ms) while exposed.

| Attack | Colour | Windup (ms) | Damage | Guard | Parry / counter | Recovery (ms) | Notes |
|---|---|---|---|---|---|---|---|
| `amort_seizure_field` | amber | 1500 | 25 on a fall | — | — | — | tile_cm 300; mark_ms 1500; void_ms 5000; restore_ms 1000; cadence_ms 9000; patterns_in_order [checker_third, ring_band_800_1200cm, tally_lines_3_through_player]; fall respawn at nearest intact edge tile, 25 damage, 1 s invulnerable (no instant death); bark at mark |
| `construct_spawn` | — | — | — | — | — | — | count 2; adds collateral_construct; at [phase_start, hp_pct:55]; max_alive 3; bark at spawn |

*Add `collateral_construct`:* HP 260; slam amber, 900 ms windup, radius 250 cm, 25 damage, 1400 ms recovery; core: exposed during slam recovery; seal-cut 1.0 s or 2 heavy hits; on defeat: goods settle gently to the floor (release, not destruction).

**P3 `amort_p3_cane` (40–0%, ~210 s).** Fixed order: `amort_final_foreclosure` → `amort_cane_pair` → `amort_cane_thrust` → `amort_cane_pair` → `amort_final_foreclosure` → `repeat_from_index_1`. HP floor 1%: at the floor, repeat amort_final_foreclosure every 4000 ms; show prompt ch08.b14.prompt.002.

| Attack | Colour | Windup (ms) | Damage | Guard | Parry / counter | Recovery (ms) | Notes |
|---|---|---|---|---|---|---|---|
| `amort_cane_pair` | amber | 500 | 18 ×2 | yes | yes | 700 |  |
| `amort_cane_thrust` | cyan | 600 | 28 | front guard absorbs 50% | no; marobashi (転) around the locked line, flank cut | 900 |  |
| `amort_final_foreclosure` | amber | 1000 | 45 | no | blade drawn: awase -> 1.2 s stagger | 1300 | **muto_eligible**; muto_window_ms {easy: 234, normal: 180, hard: 153}; on_muto disarm -> defeat:capture (any HP in P3); bark at windup_start |

**Difficulty.** Easy ×1.3 windups, Hard ×0.85 (bible §8); the mutō-dori window scales by the same factor (proposal).

**Phase transitions:**

- **P1 → P2:** a 2 s in-engine camera blend while he steps onto the dais and the tiles' edges light up. The P2 checkpoint is saved after the blend.
- **P2 → P3:** the field shuts off, the ring lowers 6 m, and he drops his coat and draws the cane's blade (2.5 s blend, with the bark 「剣は非効率です。ですが、確実です。」). The P3 checkpoint is saved after the blend.

**Capture:**

1. A successful mutō-dori plays a 1.5 s first-person disarm: Nyaakoto's paws take the cane at the tsuba and turn it out of his grip.
2. Val Amort drops to one knee.
3. The spine's seam lights amber and the interact prompt appears. Holding it for 1.5 s plays the 抜き付け draw-cut.
4. b15 follows. The lethal finisher is disabled throughout (validation rule 4: the only `muto_eligible` attack is in a boss whose `defeat` is `capture`).

### 2.3 New mechanics (specs for L1, L2 and L4)

1. **Mounted charge (`horseback_ride`, `mode: charge`).**
   - *Pacing:* the route spline carries a pack of 20 AI riders in a column of twos. The rival holds the slot on the player's right. If the player falls more than 30 m behind, the pack eases off by up to 150 cm/s; it never waits completely.
   - *Arcs* (degrees from the horse's heading, negative = left; bible §4.2 and §11):
     - yari: −10° to +90°, forward and right thrust;
     - yumi: −170° to +15°;
     - katana: +20° to +110°, right-side cuts.
   - *Speed bonus:* a yari thrust at a gallop does ×1.5 damage (proposal).
   - *Stamina:* galloping drains it at 6/s. Canter regenerates 3/s and trot 8/s.
   - *Fear* comes from beams and blasts.
   - *Horse down:* `on_horse_down: checkpoint`. The horse is never killed on screen; a "down" is a stumble and throw.
2. **Rotating volley ranks (`volley_command`).**
   - *Order:* hold Command to place a 4 m target ring up to 60 m away; release to order. L4 proposes Q-hold on keyboard and LB-hold on gamepad, and the binding is remappable.
   - *Rotation:* three ranks of four NPC gunners with coil matchlocks (catalog 5). The ready rank fires 800 ms after the order. It then withdraws, reloads with 早合 and 込め矢 (ramrod), and steps up again on a 9 s cycle, so an order is available every 3 s or so.
   - *Results are deterministic:* 288 damage is split nearest-first across up to four unshielded targets in the ring; shield enforcers are shield-staggered for 2 s; a walker takes 8% plus a leg stagger.
   - *Smoke:* each volley leaves a 4 s smoke bank that blocks sight for both sides.
   - *HUD:* three rank pips (装填 / 構え). Easy offers auto-order.
   - *Period note:* the historical cycle was far slower than 9 s (§4.2), and the term is "rotating volley ranks," never an established "three-rank volley" (bible §19).
3. **Heavy-impact objectives (anchor plates).**
   - Destructible objective actors with N plates and a per-weapon plate value: kanabō 1, mortar direct hit 1, forge hammer 0.5. Other weapons spark off.
   - After the last plate the core overloads for 2 s.
   - The kanabō uses the kernel's hold-to-strike rule (18 held ticks, lands on the 19th, 48-tick recovery).
   - Proposed as a `combat_wave` completion `objectives[]`, the same shape as in `stealth_zone`.
4. **Capstan on a moving platform.**
   - A `crank` task whose actor rides a lift. Height is progress: 48 turns carry the platform 115 m.
   - The turn-rate band is 0.4–1.0 turns/s. Above the band the rope overheats and progress stops; below it, the pawl slips at 1%/s.
   - Each available coop NPC turns at 0.15 turns/s while the player fights (0.45 combined for all three, against 0.48 turns/s ordinary decay).
   - A drone cutting the hawser triples decay.
   - Enemies board from gantries as the platform passes (a `board_platform` behaviour for L2).
5. **Seizure tiles (arena hazard).**
   - A 3 m tile grid with a per-tile state machine: `solid → marked (amber edge pulse, 1,500 ms) → void (5,000 ms) → restoring (1,000 ms) → solid`.
   - Three fixed patterns cycle every 9 s.
   - A fall is never an instant death: the player respawns on the nearest solid edge tile with 25 damage and 1 s of invulnerability.
   - Accessibility: the accessible palette (L4) replaces amber with the chosen area colour, and a floor-grid overlay option outlines marked tiles.
6. **Capture finale.** The bible's `muto_dori` mechanic (window 180 ms, `muto_eligible` attacks only), applied to a boss:
   - It requires the katana to be **sheathed** before the foreclosure windup ends. 納刀 is its own animation, 0.6 s.
   - A failed sheathed attempt takes the full 45 damage, so the risk is real.
   - After the disarm, the fight ends on an interaction, the spine cut, not on a kill.
7. **Healing Lance in the campaign** (proposal for L1/L2; catalog 17: "restores a small amount of user health … reduced damage").
   - Each enemy hit restores 4 HP to Nyaakoto.
   - Shooting a downed ally or escort NPC revives them in 1 s instead of 3 s.
   - It never raises the dead and never heals enemies.
8. **Festival carry (no-combat traversal).** `production_task: carry` with empty `waves`, an empty `loadout_while_carrying` (both paws on the box) and crowd lanes. It cannot fail. Ambient lines trigger on volumes, not timers.

### 2.4 Collectibles (passive; not counted in the beat totals)

| Id | Category | Place (beat) | Bit | Codex (JA) | Codex (EN) |
|---|---|---|---|---|---|
| `ch08.c01` | 空紋の目印 / league_mark | `pl_collateral_cells` (ch08.b07) | 0 | 担保牢の壁に、爪で刻まれた空紋。日を数える線ではない。待つための印。 | A Sora crest scratched into a cell wall. Not a tally of days: a sign of waiting. |
| `ch08.c02` | 差押状 / seizure_notice | `pl_otemon` (ch08.b06) | 1 | 期限の利益喪失通知。本日午の刻をもって、全残高を一括請求する。 | Notice of acceleration: at noon today, every balance falls due in full. |
| `ch08.c03` | 家宝 / heirloom | `pl_ledger_spire` (ch08.b12) | 2 | 鷲尾家伝来の打刀。評価札には「代物弁済」とある。 | The Washio house sword. Its tag reads "payment in kind." |
| `ch08.c04` | 家宝 / heirloom | `pl_ledger_spire` (ch08.b12) | 3 | 玉吉の師匠の打ち上げ筒。祭りの夜にだけ火を入れた。評価額、零。 | Tamakichi's master's festival mortar, fired only on festival nights. Valuation: zero. |
| `ch08.c05` | 伝書の断簡 / scroll_fragment | `pl_ledger_spire` (ch08.b12) | 4 | 活人剣とは、斬らぬ剣にあらず。斬るべき一つを、見定めた剣じゃ。 | The life-giving sword does not refuse to cut. It finds the one thing to cut. |
| `ch08.c06` | 生産の記録 / registry_page | `pl_lantern_ward_festival` (ch08.b16) | 5 | 提灯街の一頁。提灯四十張。三者の印と、割符の片方。 | A Lantern Ward page. Lanterns: forty. Three seals and one half of a tally. |

The per-chapter split is 1 league mark, 1 seizure notice, 2 heirlooms, 1 scroll fragment and 1 registry page. Picking up `ch08.c03` sets the flag for b17's conditional exchange (`requires_flag: collectible:ch08.c03`). Collectibles never grant stats (bible §10).

Ch08 holds **scroll fragment 8**, the last of eight, which the bible places in b12. The campaign-wide category totals were reconciled in review (bible §10): 8 scroll fragments, 11 seizure notices, 10 League marks, 11 heirlooms and 8 registry pages. ch08.c04 is Tamakichi's master's festival mortar; Okinu's mother's shuttle is found once only, in ch06.b07 (ch06.c04).

### 2.5 Enemy budget

| Beat | `enforcer_rifle` | `blade_retainer` | `shield_enforcer` | `grenadier` | `marksman` | `drone` | `auditor` | `seizure_walker` | `bound_conscript` | Lethal total |
|---|---|---|---|---|---|---|---|---|---|---|
| ch08.b02 | 14 |  |  |  |  | 6 |  | 2 |  | 20 |
| ch08.b03 | 6 | 2 | 3 |  | 1 | 3 |  | 1 |  | 16 |
| ch08.b04 | 4 | 3 |  | 2 |  | 2 |  |  | 4 | 11 |
| ch08.b05 |  |  |  |  | 2 | 2 |  |  |  | 4 |
| ch08.b06 | 4 | 2 | 2 | 2 | 1 | 3 |  |  |  | 14 |
| ch08.b07 | 3 | 2 | 1 |  |  | 3 | 2 |  | 3 | 11 |
| ch08.b10 | 4 | 2 | 2 | 1 | 1 | 4 | 2 |  |  | 16 |
| ch08.b11 | 3 | 2 | 1 |  |  | 3 |  |  |  | 9 |
| **Σ** | **38** | **13** | **9** | **5** | **5** | **26** | **4** | **3** | **7** | **101** |

The lethal total leaves out invulnerable scripted actors.

- **b02 walkers:** the two are scripted and invulnerable, so they are not in b02's lethal total. One is felled in b02's outro; the other returns as b03's wave-3 walker and is counted there.
- **b02 kills:** the League riders kill part of the b02 roster, so the player's own lethal defeats there are about 6–14.
- **Boss adds:** at least 4 collateral constructs (2 at P2 start, 2 at 55%). They are boss adds, not `enemies.json` types.
- **Non-lethal:** `bound_conscript` (7 in total: 4 in b04, 3 in b07) are subdued, never killed, and never count as kills (validation rule 7).

---

## 3. Dialogue

### 3.1 Conventions

- **Line ids** are `ch08.bMM.<token>.<nnn>`, with `nnn` sequential within each beat (bible §18). Tokens are character names; the **speaker id** column is what goes into `dialogue_speakers`.
- **Triggers** are bible §12.1 events: `beat_start`, `beat_complete`, `volume_enter:<id>`, `site_restored:<n>`, `boss_phase:<n>`, `player_died`, `alert_state:<state>`, `item_delivered:<id>`, `progress_at:<x>`, `idle_s:<n>`. Also used:
  - `pattern:<id>`, the boss and enemy attack pattern (used in the bible's own §12.4 example);
  - `cine@<s>`, the subtitle time inside a cinematic's `subtitles[]`;
  - `event:<id>`, a scripted beat event. This is proposed as a generic L1 event and listed in §6.
- **Modes:**
  - `ambient`: walk-and-talk; control is kept.
  - `blocking`: only in b17, at most 20 s.
  - `radio`: in ch08 only **Iota** speaks over a device, the key-slate, band-limited. Campaign-wide, `radio` means an off-screen voice (bible §12.2): device DSP applies only to the paired slates and alien PA, and no local owns a radio in 1623.
  - `bark`: short, captioned, and repeatable with a cooldown.
  - `cinematic`: subtitles.
- **Subtitles:** EN at most 2 × 42 characters and 17 cps; JA at most 2 × 16 full-width characters (bible §18). The generator that built this table checked both. Durations are approximate VO lengths, derived from reading speed; cinematic timings are subtitle start times.
- **Readings:** the readings column gives furigana-worthy readings for rare or ambiguous words, for VO casting and for an optional furigana caption layer.
- **English voice:** samurai speech is measured ("I will"); Kamigata and artisan speech is warm and colloquial; the aliens never use contractions (bible §6.3, §18).
- **Catalog anchor lines:** the four existing ch08 cues are used verbatim: b01 (Kōzō, speaker changed `artisan` → `foundry_master`), b15, b13 and b17 (bible §20). They are marked ⚓ in the tables.

**Speakers in this chapter:**

| Token | Speaker id | JA | EN | Register(s) | Lines | Status |
|---|---|---|---|---|---|---|
| `nyaakoto` | `samurai` | ニャーコト | Nyaakoto | `samurai_restrained`, `samurai_plain` | 21 | existing |
| `sekireisai` | `mentor` | 猫柳生 石鈴斎 | Nyaagyu Sekireisai | `archaic_samurai` | 12 | existing |
| `toranosuke` | `rival` | 鷲尾 虎之介 | Washio Toranosuke | `humbled_samurai`, `brash_samurai` | 12 | bible §6.1 |
| `oyuki` | `leader` | 白澄 お雪 | Shirasumi Oyuki | `business_keigo` | 11 | bible §6.1 |
| `kohagi` | `scout` | 小萩 | Kohagi | `terse` | 8 | existing |
| `taemon` | `farmer` | 庄屋 田右衛門 | Headman Taemon | `yamato_elder` | 4 | existing |
| `otane` | `farmer_young` | お種 | Otane | `kamigata_bright` | 1 | bible §6.2 |
| `tokichi` | `lantern_maker` | 提灯師 灯吉 | Tōkichi | `gentle_artisan` | 2 | bible §6.2 |
| `tamakichi` | `fireworks` | 花火師 玉吉 | Tamakichi | `kamigata_cheerful` | 3 | bible §6.2 |
| `tetsugoro` | `gunsmith` | 鉄砲鍛冶 鉄五郎 | Tetsugorō | `blunt_artisan` | 4 | bible §6.2 |
| `kozo` | `foundry_master` | 村下 鋼蔵 | Murage Kōzō | `gruff_yamato` | 6 | bible §6.2 |
| `okinu` | `weaver` | 織師 お絹 | Okinu | `kyoto_soft` | 2 | bible §6.2 |
| `okuzu` | `apothecary` | 薬師 お葛 | Okuzu | `calm_maternal` | 3 | bible §6.2 |
| `iota` | `clerk` | 会計補 イオタ | Junior Auditor Iota | `manual_keigo` | 10 | bible §6.3 |
| `valamort` | `banker` | 大徴収官 ヴァル・アモルト | High Collector Val Amort | `alien_corporate_keigo`, `alien_corporate_plain` | 17 | existing |
| `enforcer` | `enforcer` | 執行兵 | Enforcer | `alien_corporate_keigo` | 12 | PROPOSED generic |
| `conscript` | `conscript` | 債縛衆 | Debt-Bound | `yamato_rural_distressed` | 1 | PROPOSED generic |
| `villager` | `villager` | 村人 | Villager | `yamato_rural_weak` | 1 | PROPOSED generic |
| `resident` | `resident` | 町の衆 | Resident | `kamigata_townsfolk` | 1 | PROPOSED generic |
| `child` | `child` | 子ども | Child | `child` | 1 | PROPOSED generic |
| `ashigaru` | `league_ashigaru` | 空紋の足軽 | League soldier | `ashigaru_shout` | 6 | PROPOSED generic |
| `takemaru` | `pupil_takemaru` | 門弟 竹丸 | Takemaru | `young_samurai` | 2 | PROPOSED minor |

### 3.2 Script

#### ch08.b01 · 夜明け前の軍議 / War council before dawn (cinematic): 12 lines

| Line id | Trigger (mode) | Speaker | Japanese | Readings | English subtitle | s |
|---|---|---|---|---|---|---|
| `ch08.b01.iota.001` | `cine@8` (cinematic) | Iota (`clerk`) | 大徴収官が、期限の利益の喪失を宣言されました。 | 大徴収官=だいちょうしゅうかん・期限の利益=きげんのりえき・喪失=そうしつ | The High Collector has declared acceleration. Every loan is called. | 5.0 |
| `ch08.b01.iota.002` | `cine@15` (cinematic) | Iota (`clerk`) | 正午までに未払いの場合、家も道具も……人も、回収です。 | 未払い=みはらい・回収=かいしゅう | If unpaid by noon, homes, tools… and people are collected. | 5.6 |
| `ch08.b01.oyuki.003` | `cine@25` (cinematic) | Oyuki (`leader`) | 騎馬二十一、鉄砲三十六。正午まで、あと四刻でございます。 | 騎馬=きば・四刻=よとき | Twenty-one riders. Thirty-six guns. Eight hours to noon. | 6.1 |
| `ch08.b01.kohagi.004` | `cine@34` (cinematic) | Kohagi (`scout`) | 土手道に柵が四つ、差押機が二。門に錨が三。 | 土手道=どてみち・差押機=さしおさえき・錨=いかり | Causeway: four barricades, two walkers. Gate: three anchors. | 4.9 |
| `ch08.b01.kozo.005` | `cine@44` (cinematic) ⚓ | Kōzō (`foundry_master`) | 工房も田畑も、また動き始めた。 | 田畑=たはた | The workshops and fields are working again. | 3.1 |
| `ch08.b01.kozo.006` | `cine@50` (cinematic) | Kōzō (`foundry_master`) | ……これは、その礼や。持っていき。 |  | …This is our thanks. Take it. | 3.0 |
| `ch08.b01.okinu.007` | `cine@56` (cinematic) | Okinu (`weaver`) | 異星の糸を、玉鋼に巻き留めましたえ。ほどけしまへん。 | 異星=いせい・玉鋼=たまはがね・巻き留め=まきとめ | I bound the alien thread to tamahagane. It will not come loose. | 4.9 |
| `ch08.b01.okuzu.008` | `cine@66` (cinematic) | Okuzu (`apothecary`) | こちらは、斬るより繋ぐ槍です。倒れた人に向けなさい。 | 繋ぐ=つなぐ | This lance mends more than it cuts. Aim it at the fallen. | 4.7 |
| `ch08.b01.toranosuke.009` | `cine@80` (cinematic) | Toranosuke (`rival`) | この羽織は燃やす。……灰なら、もう数えられまい。 | 羽織=はおり | This haori goes in the fire. …Ash cannot be counted. | 4.4 |
| `ch08.b01.nyaakoto.010` | `cine@96` (cinematic) | Nyaakoto (`samurai`) | 数えました。田が三百十二枚、機が四十、提灯が千。 | 機=はた・提灯=ちょうちん | I have counted. Three hundred twelve paddies, forty looms, a thousand lanterns. | 5.5 |
| `ch08.b01.nyaakoto.011` | `cine@106` (cinematic) | Nyaakoto (`samurai`) | ……それと、先生が、お一人。 |  | …And one master. | 2.8 |
| `ch08.b01.oyuki.012` | `cine@116` (cinematic) | Oyuki (`leader`) | では、参りましょう。帳尻を、合わせに。 | 帳尻=ちょうじり | Then let us go and balance the books. | 3.4 |

- `ch08.b01.iota.001`: Real legal term for an acceleration clause; Iota states it like a manual.
- `ch08.b01.oyuki.003`: Temporal hours (不定時法): 寅の刻 to 午の刻 is four 刻, about eight hours.
- `ch08.b01.kozo.005`: CATALOG ANCHOR ch08 line 1 (speaker artisan -> foundry_master, bible §20). Text verbatim.
- `ch08.b01.kozo.006`: Hands over weapon 12.
- `ch08.b01.okuzu.008`: Hands over weapon 17.
- `ch08.b01.toranosuke.009`: Feeds the grey Credit House haori to the bonfire (bible §6.1).
- `ch08.b01.nyaakoto.010`: Counters: 枚 for paddies, bare numbers for looms and lanterns in speech.

#### ch08.b02 · 土手道を突破せよ / Break through on the causeway (horseback_ride (charge)): 10 lines

| Line id | Trigger (mode) | Speaker | Japanese | Readings | English subtitle | s |
|---|---|---|---|---|---|---|
| `ch08.b02.toranosuke.001` | `beat_start` (ambient) | Toranosuke (`rival`) | 前は譲る。右は俺が持つ。行くぞ！ | 譲る=ゆずる | The front is yours. I hold your right. Ride! | 3.4 |
| `ch08.b02.toranosuke.002` | `progress_at:0.05` (ambient) | Toranosuke (`rival`) | 槍は右へ突け、弓は左だ！ |  | Spear to the right! Bow to the left! | 2.6 |
| `ch08.b02.enforcer.003` | `alert_state:alert` (bark) | Enforcer (`enforcer`) | 未登録の騎馬を確認。与信を否認します。 | 与信=よしん・否認=ひにん | Unregistered cavalry detected. Credit denied. | 4.4 |
| `ch08.b02.iota.004` | `pattern:walker_sweep_beam` (radio) | Iota (`clerk`) | 差押機の照準線です！　あの線の上に、いてはいけません！ | 照準線=しょうじゅんせん | The walker's aiming line! Do not stay on that line! | 4.9 |
| `ch08.b02.toranosuke.005` | `volume_enter:vol_pylon_1` (ambient) | Toranosuke (`rival`) | 杭だ！　すれ違いざまに突け！ | 杭=くい | A seal stake! Thrust as you pass! | 2.5 |
| `ch08.b02.nyaakoto.006` | `event:horse_spooked` (bark) ↻30s | Nyaakoto (`samurai`) | 栗丸、こらえよ。 | 栗丸=くりまる | Steady, Kurimaru. | 1.7 |
| `ch08.b02.enforcer.007` | `event:enemy_retreat` (bark) ↻45s | Enforcer (`enforcer`) | 損切りいたします。後退します。 | 損切り=そんぎり | Cutting losses. Withdrawing. | 3.0 |
| `ch08.b02.toranosuke.008` | `progress_at:0.55` (ambient) | Toranosuke (`rival`) | 見ろ、城だ。あそこに先生がいる。 |  | Look—the castle. Sensei is in there. | 3.1 |
| `ch08.b02.tamakichi.009` | `progress_at:0.95` (ambient) | Tamakichi (`fireworks`) | どいてや！　門、吹っ飛ばしたるで！ |  | Make way! I'm blowing that gate wide open! | 3.0 |
| `ch08.b02.toranosuke.010` | `player_died` (ambient) ↻120s | Toranosuke (`rival`) | 立て、ニャーコト！　まだ終わっておらん！ |  | Up, Nyaakoto! This is not finished! | 3.0 |

- `ch08.b02.toranosuke.002`: Diegetic tutorial for the mounted arcs (§4.2, §11).
- `ch08.b02.iota.004`: First sweep only. Key-slate filter.
- `ch08.b02.tamakichi.009`: Siege mortars breach the outer 冠木門.
- `ch08.b02.toranosuke.010`: Plays after checkpoint reload.

#### ch08.b03 · 輪番撃ちで外郭を制せよ / Take the outer bailey with rotating volleys (combat_wave): 9 lines

| Line id | Trigger (mode) | Speaker | Japanese | Readings | English subtitle | s |
|---|---|---|---|---|---|---|
| `ch08.b03.tetsugoro.001` | `beat_start` (ambient) | Tetsugorō (`gunsmith`) | 鉄砲衆、三列！　撃ったら下がれ、込めたら出ろ！ | 鉄砲衆=てっぽうしゅう・込め=こめ | Gunners, three ranks! Fire, fall back. Loaded, step up! | 4.5 |
| `ch08.b03.oyuki.002` | `event:volley_tutorial` (ambient) | Oyuki (`leader`) | 号令は、ニャーコト殿に。的を示して『放て』と。 | 号令=ごうれい・的=まと・放て=はなて | The command is yours, Nyaakoto. Mark the target, then call 'Fire.' | 4.6 |
| `ch08.b03.ashigaru.003` | `event:volley_ready` (bark) ↻6s | League soldier (`league_ashigaru`) | 前の組、構え！ | 構え=かまえ | Front rank, ready! | 1.6 |
| `ch08.b03.nyaakoto.004` | `event:volley_ordered` (bark) ↻2s | Nyaakoto (`samurai`) | 放て！ | 放て=はなて | Fire! | 1.2 |
| `ch08.b03.ashigaru.005` | `event:volley_rotate` (bark) ↻8s | League soldier (`league_ashigaru`) | 下がって込めろ！　次の組、前へ！ | 込めろ=こめろ | Fall back and load! Next rank, forward! | 3.0 |
| `ch08.b03.oyuki.006` | `event:volley_ordered_3` (ambient) | Oyuki (`leader`) | 一斉射ごとに、玉を数えております。 | 一斉射=いっせいしゃ・玉=たま | I am counting every round, volley by volley. | 3.3 |
| `ch08.b03.enforcer.007` | `event:wave_start_2` (bark) | Enforcer (`enforcer`) | 盾列、前進。債権を保全します。 | 盾列=たてれつ・債権=さいけん・保全=ほぜん | Shield line, advance. Secure the claim. | 3.5 |
| `ch08.b03.tamakichi.008` | `event:wave_start_3` (ambient) | Tamakichi (`fireworks`) | 迫撃の筒や！　落ちる所を見て撃ちや。足元はあかんで！ | 迫撃=はくげき・筒=つつ | Mortar! Watch where it lands. Not at your own feet! | 5.0 |
| `ch08.b03.oyuki.009` | `beat_complete` (ambient) | Oyuki (`leader`) | 外郭、確保。手負いは七名。手当てを急ぎます。 | 外郭=がいかく・手負い=ておい | Outer bailey secured. Seven wounded. We treat them now. | 5.0 |

- `ch08.b03.nyaakoto.004`: Player bark on every order; also usable in b06.
- `ch08.b03.tamakichi.008`: Hands over weapon 15 (granted at beat start).

#### ch08.b04 · 野鍛冶と手当所を守れ / Defend the field forge and aid station (production_task (defend)): 7 lines

| Line id | Trigger (mode) | Speaker | Japanese | Readings | English subtitle | s |
|---|---|---|---|---|---|---|
| `ch08.b04.kozo.001` | `beat_start` (ambient) | Kōzō (`foundry_master`) | 火床が熾った。鍬も鋸も、ここで直す。 | 火床=ほど・熾った=おこった・鍬=くわ・鋸=のこぎり | The fire's up. Hoes, saws—we mend them here. | 3.6 |
| `ch08.b04.okuzu.002` | `beat_start` (ambient) | Okuzu (`apothecary`) | 手負いはこちらへ。急がず、止まらず。 | 手負い=ておい | Wounded, this way. Don't rush. Don't stop. | 3.4 |
| `ch08.b04.kohagi.003` | `progress_at:0.25` (ambient) | Kohagi (`scout`) | 擲弾兵、二。北西、塀の上。 | 擲弾兵=てきだんへい・塀=へい | Two grenadiers. Northwest, on the wall. | 3.3 |
| `ch08.b04.enforcer.004` | `progress_at:0.3` (bark) | Enforcer (`enforcer`) | 設備の差押えを執行します。 | 差押え=さしおさえ・執行=しっこう | Executing seizure of equipment. | 2.9 |
| `ch08.b04.kozo.005` | `event:net_on_anvil` (ambient) ↻40s | Kōzō (`foundry_master`) | 網や！　金床にかかった、切れ！ | 金床=かなとこ | A net! On the anvil—cut it! | 2.8 |
| `ch08.b04.conscript.006` | `event:wave_start_4` (bark) | Debt-bound (`conscript`) | すまん……体が、勝手に……！ |  | Sorry… my body won't stop…! | 2.6 |
| `ch08.b04.kozo.007` | `site_restored:1` (ambient) | Kōzō (`foundry_master`) | ……直った。三十六や。 |  | …Mended. Thirty-six. | 2.5 |

- `ch08.b04.kozo.007`: Registry entry 修理した道具 36点.

#### ch08.b05 · 兵糧と早合を三つの組へ / Bring rations and cartridges to three squads (production_task (carry)): 6 lines

| Line id | Trigger (mode) | Speaker | Japanese | Readings | English subtitle | s |
|---|---|---|---|---|---|---|
| `ch08.b05.okuzu.001` | `beat_start` (ambient) | Okuzu (`apothecary`) | 兵糧と早合を、三つの組へ。生きて届けなさい。 | 兵糧=ひょうろう・早合=はやごう | Rations and cartridges to three squads. Arrive alive. | 4.5 |
| `ch08.b05.kohagi.002` | `beat_start` (ambient) | Kohagi (`scout`) | 櫓に狙い手、二。光ったら、伏せて。 | 櫓=やぐら・狙い手=ねらいて | Two marksmen in the turret. If it glints, get down. | 3.6 |
| `ch08.b05.enforcer.003` | `pattern:marksman_lock` (bark) ↻10s | Enforcer (`enforcer`) | 照準、確定。 | 照準=しょうじゅん | Aim locked. | 1.7 |
| `ch08.b05.ashigaru.004` | `item_delivered:do_squad_west` (ambient) | League soldier (`league_ashigaru`) | 来てくれたか！　玉が尽きかけとった。 | 尽き=つき | You came! We were nearly out. | 3.1 |
| `ch08.b05.ashigaru.005` | `item_delivered:do_squad_east` (ambient) | League soldier (`league_ashigaru`) | 握り飯や……ありがたい。 | 握り飯=にぎりめし | Rice balls… Bless you. | 2.2 |
| `ch08.b05.oyuki.006` | `beat_complete` (ambient) | Oyuki (`leader`) | 兵糧三十六食、届きました。 | 三十六食=さんじゅうろくしょく | Thirty-six rations, delivered. | 3.0 |

- `ch08.b05.enforcer.003`: Audio telegraph with the 900 ms lock glint.

#### ch08.b06 · 大手門の封印錨を砕け / Smash the main gate's seal anchors (combat_wave): 8 lines

| Line id | Trigger (mode) | Speaker | Japanese | Readings | English subtitle | s |
|---|---|---|---|---|---|---|
| `ch08.b06.kozo.001` | `beat_start` (ambient) | Kōzō (`foundry_master`) | 門を割るなら、これや。振りかぶったら、迷うな。 | 割る=わる | For breaking gates, this. Once it's up, don't hesitate. | 4.1 |
| `ch08.b06.toranosuke.002` | `volume_enter:vol_masugata` (ambient) | Toranosuke (`rival`) | 枡形だ。三方から撃たれる。止まるな！ | 枡形=ますがた | A masugata. Fire from three sides. Keep moving! | 3.7 |
| `ch08.b06.kohagi.003` | `volume_enter:vol_masugata` (ambient) | Kohagi (`scout`) | 錨は三。左の柱、右の柱、雁木の上。 | 錨=いかり・雁木=がんぎ | Three anchors. Left post, right post, top of the steps. | 3.9 |
| `ch08.b06.enforcer.004` | `alert_state:alert` (bark) | Enforcer (`enforcer`) | 侵入者、枡形内。十字射撃を開始します。 | 十字射撃=じゅうじしゃげき | Intruders in the masugata. Commencing crossfire. | 4.6 |
| `ch08.b06.iota.005` | `event:objective_done_anchor_1` (radio) | Iota (`clerk`) | 錨は三つとも、独立採算でございます。一つずつ、お願いいたします。 | 独立採算=どくりつさいさん | Each anchor is accounted separately. One at a time, please. | 5.8 |
| `ch08.b06.enforcer.006` | `event:objective_done_anchor_2` (bark) | Enforcer (`enforcer`) | 第二錨、毀損。損害を計上します。 | 毀損=きそん・計上=けいじょう | Anchor two damaged. Loss recorded. | 3.8 |
| `ch08.b06.enforcer.007` | `event:enemy_retreat` (bark) | Enforcer (`enforcer`) | 門の維持は、不採算です。撤収。 | 不採算=ふさいさん・撤収=てっしゅう | Holding the gate is unprofitable. Withdraw. | 3.5 |
| `ch08.b06.ashigaru.008` | `beat_complete` (ambient) | League soldier (`league_ashigaru`) | 大手門、開いたぞぉ！ | 大手門=おおてもん | The main gate is open! | 2.0 |

- `ch08.b06.kozo.001`: Hands over weapon 6 (kanabō forged at the field forge).

#### ch08.b07 · 担保牢の民を避難所へ / Lead the prisoners to the refuge (production_task (escort)): 9 lines

| Line id | Trigger (mode) | Speaker | Japanese | Readings | English subtitle | s |
|---|---|---|---|---|---|---|
| `ch08.b07.kohagi.001` | `beat_start` (ambient) | Kohagi (`scout`) | 蔵が四つ。中の人に、札が付いてる。 | 札=ふだ | Four storehouses. The people inside are tagged. | 3.5 |
| `ch08.b07.villager.002` | `event:door_1_open` (ambient) | Villager (`villager`) | ……外か？　本当に、外なのか？ |  | …Outside? Truly outside? | 2.8 |
| `ch08.b07.nyaakoto.003` | `event:door_1_open` (ambient) | Nyaakoto (`samurai`) | 猫柳生の者だ。門まで、私が守る。 | 猫柳生=ニャーギュウ | I am of Nyaagyu. I will guard you to the gate. | 3.5 |
| `ch08.b07.child.004` | `event:door_2_open` (ambient) | Child (`child`) | 空の紋だ！　お侍さま、空の紋だよ！ | 紋=もん・侍=さむらい | The sky crest! Look, sir—the sky crest! | 3.2 |
| `ch08.b07.takemaru.005` | `event:door_3_open` (ambient) | Takemaru (`pupil_takemaru`) | ニャーコト殿！　先生は、一番奥の蔵に……！ |  | Nyaakoto! Sensei is in the last storehouse…! | 3.9 |
| `ch08.b07.nyaakoto.006` | `event:first_hide_signal` (ambient) | Nyaakoto (`samurai`) | 伏せて。合図まで、動くな。 | 合図=あいず | Get down. Do not move until I signal. | 2.7 |
| `ch08.b07.taemon.007` | `volume_enter:vol_refuge` (ambient) | Taemon (`farmer`) | 下村の衆や……よう生きとった。 | 下村=しもむら・衆=しゅう | Lower-village folk… You're alive. | 2.9 |
| `ch08.b07.oyuki.008` | `site_restored:0` (ambient) | Oyuki (`leader`) | 避難所を開きました。十二名、全員です。 | 避難所=ひなんじょ | The refuge is open. Twelve people. All of them. | 4.2 |
| `ch08.b07.takemaru.009` | `beat_complete` (ambient) | Takemaru (`pupil_takemaru`) | 一番奥です。……お一人で、行ってください。 |  | The very last one. …Go alone. | 4.1 |

- `ch08.b07.child.004`: Sees the SORA mon on Nyaakoto's sode.
- `ch08.b07.takemaru.005`: Takemaru reached the Hidden Valley in ch02 (b14/b16). He was taken in the overnight sweep that followed Val Amort's 「全担保を回収する」 decree (ch07.b16), while guarding the lower-village refugees, which is why he is in the cells with Taemon's villagers (review fix: continuity with ch02).
- `ch08.b07.nyaakoto.006`: Diegetic tutorial for hide_on_signal.

#### ch08.b08 · 一番奥の蔵 / The last storehouse (cinematic): 9 lines

| Line id | Trigger (mode) | Speaker | Japanese | Readings | English subtitle | s |
|---|---|---|---|---|---|---|
| `ch08.b08.nyaakoto.001` | `cine@16` (cinematic) | Nyaakoto (`samurai`) | 先生。 |  | Sensei. | 1.2 |
| `ch08.b08.sekireisai.002` | `cine@22` (cinematic) | Sekireisai (`mentor`) | 遅かったのう。 |  | You came late. | 1.4 |
| `ch08.b08.nyaakoto.003` | `cine@29` (cinematic) | Nyaakoto (`samurai`) | ……申し訳ございません。 |  | …Forgive me. | 2.2 |
| `ch08.b08.sekireisai.004` | `cine@35` (cinematic) | Sekireisai (`mentor`) | よい。道草も修行のうちじゃ。 | 道草=みちくさ・修行=しゅぎょう | No matter. Detours are training too. | 2.7 |
| `ch08.b08.sekireisai.005` | `cine@42` (cinematic) | Sekireisai (`mentor`) | して、何を数えてきた。 |  | So. What have you counted? | 2.1 |
| `ch08.b08.nyaakoto.006` | `cine@48` (cinematic) | Nyaakoto (`samurai`) | 守るものを。田と、炉と、灯と……人を。 | 炉=ろ・灯=あかり | What we protect. Fields, forges, lamps… and people. | 3.7 |
| `ch08.b08.sekireisai.007` | `cine@66` (cinematic) | Sekireisai (`mentor`) | 虎之介。 | 虎之介=とらのすけ | Toranosuke. | 1.2 |
| `ch08.b08.toranosuke.008` | `cine@72` (cinematic) | Toranosuke (`rival`) | ……合わせる顔が、ございません。 |  | …I cannot face you. | 2.8 |
| `ch08.b08.sekireisai.009` | `cine@80` (cinematic) | Sekireisai (`mentor`) | 顔はそこにある。上げよ。 |  | Your face is right there. Raise it. | 2.5 |

- `ch08.b08.sekireisai.002`: Approved humor beat 8 (bible §1.2). Dry, not warm; hold two beats before the next line.

#### ch08.b09 · 塔へ向かえ / Head for the spire (dialogue (ambient)): 5 lines

| Line id | Trigger (mode) | Speaker | Japanese | Readings | English subtitle | s |
|---|---|---|---|---|---|---|
| `ch08.b09.nyaakoto.001` | `beat_start` (ambient) | Nyaakoto (`samurai`) | 先生、せめてこれを。 |  | Sensei, at least take this. | 2.0 |
| `ch08.b09.sekireisai.002` | `beat_start` (ambient) | Sekireisai (`mentor`) | 要らぬ。民の前に立つには、手が空いておるほうがよい。 | 要らぬ=いらぬ・民=たみ | No need. To stand before the people, empty hands are better. | 4.7 |
| `ch08.b09.sekireisai.003` | `beat_start` (ambient) | Sekireisai (`mentor`) | 上の者は、最後に大きく振りかぶる。その時、刀は鞘の内に置け。 | 鞘=さや | At the end, he will raise his blade high. Then keep yours in its sheath. | 5.9 |
| `ch08.b09.nyaakoto.004` | `beat_start` (ambient) | Nyaakoto (`samurai`) | 無刀取りは……一人で覚えました。 | 無刀取り=むとうどり | Mutō-dori… I learned it alone. | 3.3 |
| `ch08.b09.sekireisai.005` | `beat_start` (ambient) | Sekireisai (`mentor`) | 一人で覚えたなら、本物じゃ。行け。 | 本物=ほんもの | If you learned it alone, it is real. Go. | 3.4 |

- `ch08.b09.nyaakoto.001`: Offers his wakizashi.
- `ch08.b09.sekireisai.003`: Diegetic hint for the b14 P3 mutō-dori; re-used as a memory echo in b14.

#### ch08.b10 · 帳簿塔を登れ / Climb the Ledger Spire (combat_wave): 7 lines

| Line id | Trigger (mode) | Speaker | Japanese | Readings | English subtitle | s |
|---|---|---|---|---|---|---|
| `ch08.b10.kohagi.001` | `beat_start` (ambient) | Kohagi (`scout`) | 上に四。橋の向こうに、狙い手が一。 | 狙い手=ねらいて | Four above. One marksman across the bridge. | 3.6 |
| `ch08.b10.enforcer.002` | `alert_state:alert` (bark) | Enforcer (`enforcer`) | 帳簿塔への無断立入りを検知。 | 帳簿塔=ちょうぼとう・無断立入り=むだんたちいり・検知=けんち | Unauthorized entry to the Ledger Spire detected. | 3.4 |
| `ch08.b10.enforcer.003` | `alert_state:search` (bark) ↻30s | Enforcer (`enforcer`) | 対象を見失いました。直近の取引を照会します。 | 直近=ちょっきん・照会=しょうかい | Target lost. Querying recent transactions. | 4.7 |
| `ch08.b10.toranosuke.004` | `volume_enter:vol_spire_void_edge` (ambient) | Toranosuke (`rival`) | 吹き抜けに落ちるなよ。拾いには行けん。 | 吹き抜け=ふきぬけ | Do not fall into the shaft. I cannot fetch you. | 3.6 |
| `ch08.b10.iota.005` | `volume_enter:vol_spire_L3` (radio) | Iota (`clerk`) | この塔は、一階ごとに、債務の桁が一つ上がります。 | 桁=けた | Each floor of this tower adds a digit to the debt. | 4.6 |
| `ch08.b10.tetsugoro.006` | `event:wave_start_3` (ambient) | Tetsugorō (`gunsmith`) | あの吊り台は止まっとる。轆轤を噛ませる、時間くれ。 | 吊り台=つりだい・轆轤=ろくろ・噛ませる=かませる | The lift's dead. I'll rig a capstan. Buy me time. | 4.9 |
| `ch08.b10.enforcer.007` | `event:enemy_retreat` (bark) | Enforcer (`enforcer`) | 損失が許容範囲を超過。上層へ移管します。 | 許容範囲=きょようはんい・超過=ちょうか・移管=いかん | Losses exceed tolerance. Transferring upstairs. | 4.7 |

- `ch08.b10.tetsugoro.006`: 吊り台 (hanging platform) is his own period word for the alien lift; aliens say 昇降機.

#### ch08.b11 · 轆轤を回して昇れ / Crank the capstan to rise (production_task (crank)): 7 lines

| Line id | Trigger (mode) | Speaker | Japanese | Readings | English subtitle | s |
|---|---|---|---|---|---|---|
| `ch08.b11.tetsugoro.001` | `beat_start` (ambient) | Tetsugorō (`gunsmith`) | 押して回せ。速すぎりゃ綱が焼ける、遅けりゃ下がる。 | 綱=つな | Push it round. Too fast burns the rope. Too slow, we sink. | 4.5 |
| `ch08.b11.ashigaru.002` | `event:crank_turn_6` (bark) ↻8s | League soldier (`league_ashigaru`) | せーの！ |  | Heave! | 1.2 |
| `ch08.b11.kohagi.003` | `progress_at:0.25` (ambient) | Kohagi (`scout`) | 上の橋から、目録が三。 | 目録=もくろく | Three drones, off the upper bridge. | 2.5 |
| `ch08.b11.tetsugoro.004` | `event:player_left_capstan` (ambient) ↻45s | Tetsugorō (`gunsmith`) | おれらだけじゃ遅い！　早う戻れ！ |  | Too slow without you! Get back here! | 2.6 |
| `ch08.b11.enforcer.005` | `progress_at:0.5` (bark) | Enforcer (`enforcer`) | 昇降機の無断使用。料金を請求します。 | 昇降機=しょうこうき・請求=せいきゅう | Unauthorized use of the lift. You will be charged. | 4.3 |
| `ch08.b11.iota.006` | `progress_at:0.75` (radio) | Iota (`clerk`) | 頂上の機関が、正午の一括請求を準備中でございます。 | 機関=きかん・一括請求=いっかつせいきゅう | The summit engine is preparing the noon collection. | 5.4 |
| `ch08.b11.toranosuke.007` | `beat_complete` (ambient) | Toranosuke (`rival`) | ここから先は、お前一人だ。下は俺たちが守る。 |  | From here, you go alone. We hold below. | 4.3 |

- `ch08.b11.tetsugoro.001`: Diegetic tutorial for turn_rate_band.
- `ch08.b11.ashigaru.002`: Engineers' hauling call, every sixth turn.

#### ch08.b12 · 押収品を調べる / Search the seized goods (explore_optional): 5 lines

| Line id | Trigger (mode) | Speaker | Japanese | Readings | English subtitle | s |
|---|---|---|---|---|---|---|
| `ch08.b12.iota.001` | `volume_enter:vol_heirloom_hall` (radio) | Iota (`clerk`) | 押収品の陳列室でございます。どれにも、評価額が。 | 押収品=おうしゅうひん・陳列室=ちんれつしつ・評価額=ひょうかがく | The seized-goods gallery. Every item has a valuation. | 4.9 |
| `ch08.b12.nyaakoto.002` | `event:poi_child_toy` (ambient) | Nyaakoto (`samurai`) | ……子どもの張子に、三文か。 | 張子=はりこ・三文=さんもん | …A child's paper toy. Three coppers. | 2.9 |
| `ch08.b12.nyaakoto.003` | `event:collectible_ch08_c03` (ambient) | Nyaakoto (`samurai`) | 鷲尾家の刀……虎之介に、返さねば。 | 鷲尾家=わしおけ | The Washio sword… This goes back to Toranosuke. | 3.7 |
| `ch08.b12.sekireisai.004` | `event:collectible_ch08_c05` (ambient) | Sekireisai (`mentor`) | 活人剣とは、斬らぬ剣にあらず。斬るべき一つを、見定めた剣じゃ。 | 活人剣=かつにんけん・見定めた=みさだめた | The life-giving sword does not refuse to cut. It finds the one thing to cut. | 5.8 |
| `ch08.b12.iota.005` | `idle_s:60` (radio) | Iota (`clerk`) | 上へは、北の階段でございます。 |  | The way up is the north stair. | 2.9 |

- `ch08.b12.nyaakoto.002`: The label reads 0.3 in alien numerals; Nyaakoto reads it in period decimal notation (分 = one tenth).
- `ch08.b12.sekireisai.004`: Scroll fragment 8 read in Sekireisai's voice (memory filter). Paraphrases the 殺人刀/活人剣 idea; not a quotation.
- `ch08.b12.iota.005`: exit hint

#### ch08.b13 · 帳簿機関 / The Ledger Engine (cinematic): 8 lines

| Line id | Trigger (mode) | Speaker | Japanese | Readings | English subtitle | s |
|---|---|---|---|---|---|---|
| `ch08.b13.valamort.001` | `cine@12` (cinematic) | Val Amort (`banker`) | ようこそ、債務者番号七〇三一。お掛けください。 | 債務者番号=さいむしゃばんごう・七〇三一=ななまるさんいち | Welcome, debtor seven-zero-three-one. Please, be seated. | 4.9 |
| `ch08.b13.valamort.002` | `cine@20` (cinematic) | Val Amort (`banker`) | ご提案です。返済条件の変更——金利は据え置き、期間は永久。 | 返済=へんさい・据え置き=すえおき・永久=えいきゅう | A proposal. Restructured terms: the rate unchanged, the term perpetual. | 6.4 |
| `ch08.b13.nyaakoto.003` | `cine@30` (cinematic) | Nyaakoto (`samurai`) | ……永久。 | 永久=えいきゅう | …Perpetual. | 1.3 |
| `ch08.b13.valamort.004` | `cine@36` (cinematic) ⚓ | Val Amort (`banker`) | 最後の帳簿は私が守る。街の未来まで担保に取ろう。 | 担保=たんぽ | I guard the final ledger. Even this city's future is collateral. | 5.2 |
| `ch08.b13.valamort.005` | `cine@46` (cinematic) | Val Amort (`banker`) | 署名を。硯は用意してございます。……貴殿の師のものですが。 | 署名=しょめい・硯=すずり・貴殿=きでん | Your signature. An inkstone is provided. It was your master's. | 5.5 |
| `ch08.b13.valamort.006` | `cine@72` (cinematic) | Val Amort (`banker`) | ……備品の毀損として、計上いたします。 | 備品=びひん・毀損=きそん・計上=けいじょう | …Recorded as damage to fixtures. | 3.7 |
| `ch08.b13.nyaakoto.007` | `cine@82` (cinematic) | Nyaakoto (`samurai`) | 記せ。それが、お前の最後の一行だ。 | 記せ=しるせ・一行=いちぎょう | Write it down. It is your last line. | 3.5 |
| `ch08.b13.valamort.008` | `cine@94` (cinematic) | Val Amort (`banker`) | 交渉は決裂。元本を、回収いたします。 | 交渉=こうしょう・決裂=けつれつ・元本=がんぽん | Negotiations have failed. The principal will be recovered. | 4.1 |

- `ch08.b13.valamort.001`: Same account number as the bible §6.5 register sample.
- `ch08.b13.valamort.004`: CATALOG ANCHOR ch08 line 3, verbatim. Its plain register is played as the one moment his politeness drops.
- `ch08.b13.valamort.006`: Follows the approved inkstone beat (bible §1.2 #7). No music sting.

#### ch08.b14 · 大徴収官を捕らえよ / Capture the High Collector (boss): 11 lines

| Line id | Trigger (mode) | Speaker | Japanese | Readings | English subtitle | s |
|---|---|---|---|---|---|---|
| `ch08.b14.valamort.001` | `pattern:amort_ledger_beam` (bark) ↻ | Val Amort (`banker`) | 元本、回収。 | 元本=がんぽん | Recovering the principal. | 1.9 |
| `ch08.b14.valamort.002` | `pattern:amort_cleave` (bark) ↻ | Val Amort (`banker`) | 償却。 | 償却=しょうきゃく | Write-off. | 1.2 |
| `ch08.b14.valamort.003` | `pattern:amort_shards` (bark) ↻15s | Val Amort (`banker`) | 残高照会。 | 残高照会=ざんだかしょうかい | Balance inquiry. | 1.5 |
| `ch08.b14.valamort.004` | `pattern:amort_seizure_field` (bark) ↻ | Val Amort (`banker`) | 差押えを執行いたします。 | 差押え=さしおさえ・執行=しっこう | Executing seizure. | 2.5 |
| `ch08.b14.valamort.005` | `pattern:construct_spawn` (bark) ↻ | Val Amort (`banker`) | 担保物件、稼働。 | 担保物件=たんぽぶっけん・稼働=かどう | Collateral assets: activate. | 2.2 |
| `ch08.b14.valamort.006` | `boss_phase:3` (bark) | Val Amort (`banker`) | 剣は非効率です。ですが、確実です。 | 非効率=ひこうりつ・確実=かくじつ | The sword is inefficient. But it is certain. | 3.5 |
| `ch08.b14.valamort.007` | `pattern:amort_final_foreclosure` (bark) ↻ | Val Amort (`banker`) | 最終、抵当権実行。 | 抵当権=ていとうけん・実行=じっこう | Final foreclosure. | 2.5 |
| `ch08.b14.valamort.008` | `player_died` (bark) ↻ | Val Amort (`banker`) | 延滞として、処理いたします。 | 延滞=えんたい・処理=しょり | Processed as delinquent. | 2.7 |
| `ch08.b14.valamort.009` | `event:muto_dori_success` (bark) | Val Amort (`banker`) | ……計算に、ありません。 |  | …This is not in the calculation. | 2.3 |
| `ch08.b14.nyaakoto.010` | `event:muto_dori_success` (ambient) | Nyaakoto (`samurai`) | お前は、無いものを数えた。 |  | You counted what did not exist. | 2.5 |
| `ch08.b14.nyaakoto.011` | `event:spine_prompt` (ambient) | Nyaakoto (`samurai`) | 一太刀で、足りる。 | 一太刀=ひとたち | One cut is enough. | 2.1 |

- `ch08.b14.valamort.001`: Captioned audio telegraph at lock start (900 ms before damage). Bible §8.
- `ch08.b14.valamort.002`: Captioned telegraph at windup start (1200 ms).
- `ch08.b14.valamort.004`: Bible §8 voice telegraph; plays with every tile mark (1500 ms before void).
- `ch08.b14.valamort.007`: Captioned telegraph at windup start (1000 ms); marks the muto_eligible attack.
- `ch08.b14.valamort.008`: Plays over the phase-checkpoint reload.
- Re-used line `ch08.b09.sekireisai.003` on `event:first_foreclosure`: Memory echo, filtered; captioned.

#### ch08.b15 · 封印、消ゆ / The seals go dark (cinematic): 7 lines

| Line id | Trigger (mode) | Speaker | Japanese | Readings | English subtitle | s |
|---|---|---|---|---|---|---|
| `ch08.b15.valamort.001` | `cine@14` (cinematic) | Val Amort (`banker`) | 帳簿なくして、この谷に秩序はございません。 | 秩序=ちつじょ | Without the ledger, this valley has no order. | 3.8 |
| `ch08.b15.oyuki.002` | `cine@21` (cinematic) | Oyuki (`leader`) | 帳簿なら、ございます。わたくしどもの帳簿が。 |  | There is a ledger. Ours. | 3.9 |
| `ch08.b15.toranosuke.003` | `cine@30` (cinematic) | Toranosuke (`rival`) | 縄目の恥とは言わせん。生きて、数えろ。 | 縄目=なわめ・恥=はじ | This rope is no disgrace. Live. And count. | 3.8 |
| `ch08.b15.taemon.004` | `cine@56` (cinematic) | Taemon (`farmer`) | ……封が、消えよった。 | 封=ふう | …The seal. It's gone dark. | 2.1 |
| `ch08.b15.okinu.005` | `cine@72` (cinematic) | Okinu (`weaver`) | 取り立ての目盛りが、消えましたえ。 | 取り立て=とりたて・目盛り=めもり | The levy gauges have gone dark. | 3.3 |
| `ch08.b15.tokichi.006` | `cine@88` (cinematic) | Tōkichi (`lantern_maker`) | 戸の数字が……消えた。 | 戸=と | The numbers on the doors… gone. | 2.4 |
| `ch08.b15.nyaakoto.007` | `cine@128` (cinematic) ⚓ | Nyaakoto (`samurai`) | あとはこの街だ。誰も借りに縛られぬように。 | 縛られぬ=しばられぬ | Only this ward remains. No one will be bound by debt again. | 4.1 |

- `ch08.b15.toranosuke.003`: Binds Val Amort with a 捕縄.
- `ch08.b15.taemon.004`: At the First Weir sluice (ch04).
- `ch08.b15.okinu.005`: Loom hall, Silk Foundry (ch05).
- `ch08.b15.tokichi.006`: Lantern Ward back tenements (ch03).
- `ch08.b15.nyaakoto.007`: CATALOG ANCHOR ch08 line 2, verbatim; over the view of the Lantern Ward.

#### ch08.b16 · 生産改帳を掲げよ / Post the production registry (production_task (carry)): 8 lines

| Line id | Trigger (mode) | Speaker | Japanese | Readings | English subtitle | s |
|---|---|---|---|---|---|---|
| `ch08.b16.oyuki.001` | `beat_start` (ambient) | Oyuki (`leader`) | 改帳を集会所へ。皆の前で、貼り出します。 | 改帳=かいちょう・集会所=しゅうかいじょ | Take the registry to the assembly. We post it before everyone. | 4.3 |
| `ch08.b16.resident.002` | `volume_enter:vol_fest_a` (ambient) | Resident (`resident`) | うちの鍋、戻ってきたんよ。差押えの札付きで。 | 差押え=さしおさえ・札=ふだ | Our pot came back. Seizure tag and all. | 4.2 |
| `ch08.b16.tokichi.003` | `volume_enter:vol_fest_b` (ambient) | Tōkichi (`lantern_maker`) | 千張り、灯しました。一つも、借りた灯ではございません。 | 千張り=せんはり・灯し=ともし・灯=ひ | A thousand lanterns lit. Not one of them borrowed. | 4.9 |
| `ch08.b16.otane.004` | `volume_enter:vol_fest_c` (ambient) | Otane (`farmer_young`) | 新米や！　今年は全部、うちらの米やで！ | 新米=しんまい | New rice! This year, every grain is ours! | 3.7 |
| `ch08.b16.taemon.005` | `volume_enter:vol_fest_d` (ambient) | Taemon (`farmer`) | 紙は紙や、言うたけどな。この紙は、ええ紙や。 |  | I said paper is paper. But this is good paper. | 4.1 |
| `ch08.b16.tamakichi.006` | `volume_enter:vol_assembly` (ambient) | Tamakichi (`fireworks`) | 花火、上げてもええか？ | 花火=はなび | Can I set off the fireworks now? | 2.3 |
| `ch08.b16.oyuki.007` | `volume_enter:vol_assembly` (ambient) | Oyuki (`leader`) | 帳面に載せてからです。 | 帳面=ちょうめん | Once they are in the ledger. | 2.2 |
| `ch08.b16.oyuki.008` | `site_restored:2` (ambient) | Oyuki (`leader`) | 生産改帳、ここに掲げます。明日からの帳は、皆さまの手で。 | 生産改帳=せいさんかいちょう・掲げ=かかげ・帳=ちょう | The production registry is posted. From tomorrow, you keep the books. | 5.5 |

- `ch08.b16.taemon.005`: Pays off his skeptic line 「紙は紙や。」 (bible §2.3).
- `ch08.b16.oyuki.007`: Restrained humor (character, not gag).

#### ch08.b17 · 東の鳥居へ / To the Eastern Torii (dialogue (ambient)): 9 lines

| Line id | Trigger (mode) | Speaker | Japanese | Readings | English subtitle | s |
|---|---|---|---|---|---|---|
| `ch08.b17.kohagi.001` | `beat_start` (ambient) ⚓ | Kohagi (`scout`) | 東の鳥居で待つ。皆で新しい朝を迎えよう。 | 鳥居=とりい | We will wait at the eastern torii. Let us greet a new morning together. | 4.9 |
| `ch08.b17.iota.002` | `volume_enter:vol_torii` (ambient) | Iota (`clerk`) | 朝というものは……無償で来るのですね。 | 無償=むしょう | So morning… comes free of charge. | 3.4 |
| `ch08.b17.nyaakoto.003` | `event:washio_sword_return` (ambient) ◇ if Washio sword taken | Nyaakoto (`samurai`) | 鷲尾の刀だ。上で見つけた。 | 鷲尾=わしお | Your house's sword. I found it up there. | 2.9 |
| `ch08.b17.toranosuke.004` | `event:washio_sword_return` (ambient) ◇ if Washio sword taken | Toranosuke (`rival`) | ……借りが、できたな。 | 借り=かり | …Now I owe you. | 2.0 |
| `ch08.b17.nyaakoto.005` | `event:washio_sword_return` (ambient) ◇ if Washio sword taken | Nyaakoto (`samurai`) | 貸しではない。 | 貸し=かし | It is not a loan. | 1.4 |
| `ch08.b17.sekireisai.006` | `event:plaque_rehang` (blocking) | Sekireisai (`mentor`) | 虎之介の札は、ここじゃ。 | 札=ふだ | Toranosuke's plaque goes here. | 2.3 |
| `ch08.b17.sekireisai.007` | `event:plaque_rehang` (blocking) | Sekireisai (`mentor`) | ニャーコト。おぬしの札は……ここじゃな。 |  | Nyaakoto. Yours goes… here. | 3.0 |
| `ch08.b17.nyaakoto.008` | `event:plaque_rehang` (blocking) | Nyaakoto (`samurai`) | 剣は、作る手を守るためにある。 | 剣=けん | The sword exists to protect the hands that make. | 3.4 |
| `ch08.b17.sekireisai.009` | `event:plaque_rehang` (blocking) | Sekireisai (`mentor`) | ……ようやく、一本じゃ。 | 一本=いっぽん | …At last, a point. | 2.1 |

- `ch08.b17.kohagi.001`: CATALOG ANCHOR ch08 line 4, verbatim; said at the assembly before the fade to dawn.
- `ch08.b17.nyaakoto.008`: Bible §9 final exchange, verbatim.
- `ch08.b17.sekireisai.009`: Bible §9 final exchange, verbatim.

#### ch08.b18 · 一束 / One sheaf (cinematic): 3 lines

| Line id | Trigger (mode) | Speaker | Japanese | Readings | English subtitle | s |
|---|---|---|---|---|---|---|
| `ch08.b18.valamort.001` | `cine@40` (cinematic) | Val Amort (`banker`) | ……一束。 | 一束=ひとたば | …One sheaf. | 1.3 |
| `ch08.b18.iota.002` | `cine@45` (cinematic) | Iota (`clerk`) | はい。一束、確かに在ります。 | 在ります=あります | Yes. One sheaf. It truly exists. | 2.9 |
| `ch08.b18.taemon.003` | `cine@52` (cinematic) | Taemon (`farmer`) | 数え終わったら、蒔きに行くで。麦は秋に蒔くんや。 | 蒔き=まき | Done counting? Then we sow. Barley goes in come autumn. | 4.6 |

- `ch08.b18.valamort.001`: Approved humor beat 9 (bible §1.2).
- `ch08.b18.taemon.003`: Autumn sowing of barley after the rice harvest (二毛作).


### 3.3 HUD tutorial prompts (L4 `ui_strings`, not voiced)

| Prompt id | Trigger | JA | EN |
|---|---|---|---|
| `ch08.b01.prompt.001` | `beat_complete` | 新たな武具：単分子薙刀・治癒の槍 | New arms: Monofilament Naginata, Healing Lance |
| `ch08.b02.prompt.001` | `beat_start` | 馬上の槍：前と右へ突く | Mounted yari: thrust forward and to the right |
| `ch08.b02.prompt.002` | `progress_at:0.05` | 馬上の弓：左側にだけ射てる | Mounted yumi: you can shoot to the left only |
| `ch08.b02.prompt.003` | `pattern:walker_sweep_beam` | 手綱を引くと速度が落ちる | Pull the reins to slow down |
| `ch08.b03.prompt.001` | `event:volley_tutorial` | {Ability}長押しで的を示し、離すと斉射 | Hold {Ability} to mark a target, release to fire a volley |
| `ch08.b03.prompt.002` | `event:wave_start_3` | 迫撃砲：弧の落下点を見て撃つ | Micro-Mortar: check where the arc lands |
| `ch08.b06.prompt.001` | `beat_start` | 金棒：攻撃を押し続けると振り下ろす | Kanabō: keep holding attack to bring it down |
| `ch08.b07.prompt.001` | `event:first_hide_signal` | 合図で民を隠す／進ませる | Signal the people to hide or to move |
| `ch08.b07.prompt.002` | `npc_downed:any` | 治癒の槍：倒れた味方を撃つと早く起きる | Healing Lance: shoot a downed ally to revive faster |
| `ch08.b11.prompt.001` | `beat_start` | 轆轤：同じ速さで回し続ける | Capstan: keep turning at a steady pace |
| `ch08.b14.prompt.001` | `boss_phase:2` | 琥珀の縁の床は、まもなく消える | Amber-edged tiles are about to fall away |
| `ch08.b14.prompt.002` | `event:first_foreclosure` | 納刀して待ち、振り下ろしを無刀取り | Sheathe, wait, then take the overhead: mutō-dori |
| `ch08.b14.prompt.003` | `event:spine_prompt` | 機関の背骨を断て | Cut the engine's spine |
| `ch08.b16.prompt.001` | `beat_start` | 改帳を高札場まで運ぶ | Carry the registry to the notice board |

Button glyphs are appended by L4 per device. Prompts show once per save unless the player fails the same step twice. Prompts are text only: the Japanese line with the English subtitle line under it (bible §12.1 objective text). None is voiced.

---

## 4. Historical and cultural accuracy

These are campaign rules and review notes, not claims of authenticity. Anything marked **verify** needs historian or practitioner sign-off before release copy uses it.

### 4.1 Kenjutsu and the fictional school

- **活人剣 / 殺人刀.** Yagyū Munenori's 『兵法家伝書』 (1632) contrasts the killing sword with the life-giving sword, including the idea that cutting down one evil can let many live. Scroll fragment 8's line (b12) is an **original paraphrase** written for Sekireisai, not a quotation. The game's reading, that the "one thing to cut" is the debt engine rather than the collector, is our interpretation and must not be marketed as Yagyū doctrine (bible §3.1).
- **無刀取り.** It is used as the tradition of Sekishūsai's 1594 demonstration describes it, as a principle. No real kata sequence is reproduced. In-game the technique is performed **with the katana sheathed** (bible §3.2), so b09's hint says 「刀は鞘の内に置け」 rather than naming a form.
- **納刀 and 抜き付け.** The sheathing before mutō-dori and the single draw-cut through the spine are generic early-Edo sword handling, not a named school technique. Motion capture needs a qualified performer and a practitioner's review (B5).
- **転 (まろばし)** against the cane thrust, and 合わせ against the cleave and foreclosure, reuse the timings taught in ch01 (bible §3.2: parry within 260 ms, stagger 1.2 s).
- **Respect rule:** the scroll is voiced as Sekireisai's own teaching. No real Yagyū text, kata name or 目録 heading appears on screen.

### 4.2 Weapons

- **Mounted yari (b02).** A straight su-yari (existing source study `Content/SourceArt/Weapons/NyaagyuYari`, 1.93 m, after British Museum OA+.7199). Mounted use is a forward or right-side thrust with the reins in the left paw (bible §4.3). The ×1.5 speed bonus is a game rule. **Verify** the right-side emphasis with a practitioner of mounted spear.
- **Mounted yumi.** Left side only (弓手). The rider knots the tazuna on the neck and rises in the broad abumi to shoot (bible §4.2); arcs −170° to +15°.
- **Matchlocks and 早合.**
  - The League gunners' cycle is 火蓋 (pan cover), 口薬 (priming), 早合 (paper cartridge), 込め矢 (ramrod), 火縄 (match).
  - A real matchlock reload took on the order of **tens of seconds** even with 早合. The 9 s rank cycle is a compressed game rule, and the fiction's coil breech (catalog 5, bible §4.4) is the in-world excuse.
  - The white smoke bank after every volley is accurate and doubles as a gameplay screen.
  - The rotating ranks are **not** presented as the Nagashino "three-rank volley," whose historicity is debated (bible §19). The HUD term is 輪番撃ち (rotation fire), a game term.
- **Kanabō (金棒 / 金砕棒).** An oak club shod with iron studs. By 1623 it was a largely obsolete battlefield weapon, which is why Kōzō forges one for a single purpose: breaking graphite plates. It is not a samurai's standard arm.
- **Naginata (12).** The Monofilament Naginata is fictional (catalog special 12). Existing source art: `Content/SourceArt/Weapons/MonofilamentNaginata` (2.31 m, smoked-oak and indigo-urushi shaft).
- **Healing Lance (17).** Fictional (catalog special 17). Okuzu's line frames it as a tool that "mends more than it cuts."

### 4.3 Horses and tack

- **Horses.** Native horses about 130 cm at the withers (the Kiso reference is 132 cm, Nagoya University Museum; see the horse README), stocky and heavy-maned. Coats: Kurimaru 栗毛 (chestnut), Arashi 黒鹿毛 (black-bay), League horses 鹿毛, 栗毛 and 黒鹿毛. They are **unshod**. Straw 馬沓 appear only on the pack horses for the long walk home in b17, not in the charge.
- **Riding tack** (bible §4.5):
  - 鞍 with a four-piece tree (前輪 and 後輪 arches, 居木);
  - 障泥 leg flaps, 腹帯 girth and 力革 stirrup leathers;
  - broad-toed 舌長鐙 with an open heel;
  - 轡, 面繋, 胸繋 and 鞦;
  - broad dyed-cloth 手綱.

  Pack horses carry a 荷鞍 (b17).
- **SORA mon:** on the abumi front plates (the family-mon placement of Met 2008.120) and the crupper fittings.
- **Scale warning (existing reference doc):** the current kura tree is larger than the museum saddles; the mounted pose must be reconciled before any accuracy claim.
- **Cavalry realism.** Contemporary European observers noted that Japanese warriors often **dismounted** to fight (Luís Fróis, *Tratado*, 1585; **verify** wording). The b02 charge is therefore staged as a small-unit dash along a causeway to seize a breached gate, with riders fighting from the saddle when it pays. It is not a European shock line.

### 4.4 Castle architecture and siege

- **枡形虎口 (masugata).** A square gate court with an outer 高麗門 and an inner 櫓門 at right angles. It was standard in Keichō–Kan'ei castle building; compare the Tokugawa rebuild of Osaka Castle, whose 大手門 dates from 1628 (Important Cultural Property). It is designed so attackers are shot at from three sides, and b06 plays it exactly that way.
- **多聞櫓.** A long wall-turret, traditionally named after Matsunaga Hisahide's 多聞山城 in Nara, a Yamato connection that fits the setting. It carries 鉄砲狭間 (round, triangular or square loopholes), 矢狭間 (tall rectangles) and 石落とし.
- **石垣:** 打込接ぎ with 算木積み corners (Keichō era; bible §15.2). **雁木:** stone steps up the inside of a wall to the wall-walk. **埋門:** a small gate set into the wall base, here an enemy sally port.
- **竹束 (bamboo-bundle mantlets).** Portable cover against matchlock fire in late-Sengoku siege works (仕寄り). **Verify** construction details (bundle diameter, bindings, props).
- **米蔵 / 土蔵.** Two-storey plastered storehouses with ibushi kawara. No 海鼠壁 (namako walls; a later, regional look). The Credit House has chiselled the mon faces off the castle's 軒丸瓦. The game deliberately does not say whose mon they were.
- **轆轤 (capstan).** Vertical hand capstans hauled stone and timber in castle building. The type later called 神楽桟 is the model (**verify** the term for 1623). The League's capstan has a wooden pawl (歯止め).
- **捕縄.** Binding a captive with rope (捕縄術) and the idiom 縄目の恥 are period-appropriate. Toranosuke's binding is a plain restraint, not a formal status-coded knot pattern.

### 4.5 Clothing and armor

- **Nyaakoto:** 当世具足 in 紺糸威 lacing with 朱漆 plates, and the SORA mon on the sode and dō (existing runtime skin placements).
- **Toranosuke:** black lacquer armor with scarlet lacing. His grey Credit House haori is burned in b01 (bible §6.1).
- **League ashigaru:** 陣笠 painted with the mon, 腹当, 旗指物 with the SORA mon, and lent armor (御貸具足) of mixed quality.
- **Sekireisai in captivity:** a plain kimono with no 十徳 (seized). He wears a 十徳 again at the torii (b17): Okinu made him a new one.
- **Oyuki:** 小袖 with tasuki. At the festival she wears a better 小袖, still with the soroban at her obi.
- **Commoners at the festival:** 小袖, 手拭い; children in short kimono.
- **Avoid:** the theatrical black "ninja" suit (Kohagi stays in indigo peddler's clothes), later-Edo 浴衣 fashions as festival wear, and 招き猫 anywhere.

### 4.6 Festival, season and daily life

- **Season.** An early-autumn typhoon (ch07) is followed by the rice harvest, with rice drying on 稲架. **Barley is sown in autumn** after the rice (二毛作), hence Taemon's b18 line. Avoid naming 二百十日 as a calendar date: it entered the official calendar only with the 貞享暦 (1685) (**verify**).
- **Harvest festival on the full-moon night.** Offerings are new rice and susuki grass. Taro offerings (芋名月) are the older custom; stacked 月見団子 as a fixed form are better attested later (**verify**; keep them off hero props).
- **Stalls.** The movable 屋台 is a later-Edo development. Use 振売 (hawkers with shoulder poles) and 見世棚 / 床店 (simple fixed stalls). Food: 団子, 田楽, 甘酒, 焼き餅.
- **Fireworks (Tamakichi).** Keep them small, low and **orange-gold (和火)**. Coloured fireworks arrived only in the Meiji era, and large spherical aerial shells are a later-Edo development (bible §19 also forbids 鍵屋 and 玉屋 as businesses; **verify** scale with a fireworks historian).
- **Paper fans.** Flat 団扇 with the printed mon for children; folding 扇 for adults.
- **The name board (名札掛け).** Pupils' plaques ordered by rank; rehanging and moving a plaque is the promotion gesture. **Nothing is hung on the torii itself.** The board stands on a plain wooden stand beside it, off the shrine axis, out of respect for the shrine gate.

### 4.7 SORA kamon in this chapter

The exact user SVG (`Content/SourceArt/UI/sora_logo_NOtext2.svg`, SHA-256 `d66413a7…0910`), imported from its two original paths and never redrawn (bible §17).

| Surface | Where in ch08 | Treatment |
|---|---|---|
| 陣幕 curtains | b01 council, b04 field forge | Dyed white-on-indigo mon on each panel |
| 旗指物 (sashimono) and 幟 | b01–b07, the whole League host | Painted or dyed; the ch05 silk nobori flies over the forward camp |
| 陣笠 | League ashigaru | Painted mon on the crown |
| Armor | Nyaakoto's sode and dō | Existing runtime placements |
| Tack | Kurimaru's abumi front plates and crupper fittings | Per bible §4.5 |
| 割符 tally and registry seal | b04 and b05 registry entries; b16 posted registry | Brand across the split; vermillion 朱印 on each page |
| Seized 陣羽織 | b12 gallery | Hidden under an alien seizure label until the player tears it off. The aliens never display the mon. |
| Children's 団扇 and the new 高札 header | b16 festival | Printed on paper; carved and painted on the board header |
| 名札掛け header | b17 | The ch01 board's header mon (recovered in ch07) |
| UI | All beats | Objective marker, rotating save mon, the vermillion seal on the chapter title card and on the final credits card |

The alien **ledger sigil** (a closed ring of tally notches) marks anchors, stakes, walkers, cell tags and valuation labels. It must never resemble the SORA mon.

### 4.8 Sources

- 柳生宗矩『兵法家伝書』(1632); for example 渡辺一郎 校注『兵法家伝書 付・新陰流兵法目録事』(岩波文庫, 1985).
- Yagyū Shinkage-ryū characteristics (school account) and the Japan Kobudō Association school profile, as cited in [historical-arms.md](../historical-arms.md).
- All Japan Kyudo Federation, 射法八節 and equipment rules (cited in historical-arms.md).
- British Museum OA+.7199 su-yari (cited in the yari source study README).
- The Met 2000.405 (kura, 1658), 2008.120.1–2 (abumi with a family mon at the front), 2016.205a–b (hato-mune abumi); Nagoya University Museum on the Kiso horse (all cited in [historical-horse-tack-art-reference.md](../historical-horse-tack-art-reference.md) and the horse README).
- Osaka Castle 大手門 (1628, Important Cultural Property): Osaka Castle Park / Osaka City cultural-property records.
- 多聞櫓 and 多聞山城: standard Japanese castle-architecture references (**verify** the preferred citation with the historian).
- Luís Fróis, *Tratado das contradições e diferenças de costumes* (1585), the chapter on warfare (**verify** exact wording).
- 日本煙火協会, history of Japanese fireworks (和火 / 洋火) (**verify**).
- Bible §19 checklist items (高瀬舟, 早合, 馬沓, soroban, 一味神水, 陣笠, 幟, 旗指物).

---

## 5. Art and audio asset list

**Status key.** **Existing (source):** original or CC0 source art in `Content/SourceArt`. None of it has passed the photoreal gate yet; every item must pass [photoreal acceptance](../art-direction/photoreal-acceptance.md) (packaged fixed-camera A/B, license, measured frame cost on both platforms) before it ships. **Existing (catalog):** a data entry that needs a real mesh. **Needed:** does not exist yet.

### 5.1 Existing assets reused

| Asset | Path | ch08 use | Status and gap |
|---|---|---|---|
| SORA kamon SVG | `Content/SourceArt/UI/sora_logo_NOtext2.svg` (+ `SORA_Resistance_Logo.png`) | Every kamon surface in §4.7 | Existing; pinned hash |
| Monofilament Naginata | `Content/SourceArt/Weapons/MonofilamentNaginata/` (in `Content/ArtReview/Weapons`) | Weapon 12, b01 hand-over | Existing (source/ArtReview); needs the first-person grip and a review in Unreal |
| Su-yari study | `Content/SourceArt/Weapons/NyaagyuYari/` | Mounted yari, b02 | Existing (source-only); needs mounted-thrust fitting |
| Yumi study | `Content/SourceArt/Weapons/NyaagyuYumi/` | Mounted and foot archery | Existing (source-only); draw rig needed |
| Hero katana and saya | `Content/SourceArt/SM_Nyaagyu_HeroKatana.fbx`, `SM_Nyaagyu_HeroSaya.fbx`, `Weapons/HeroKatana/PBR` | Mutō-dori needs the sheathed state; 抜き付け | Existing: both FBXs are present. The root manifest lists only the drawn katana as a runtime export, so the sheathed state for mutō-dori still needs the saya worn at the hip and a 納刀 animation. |
| Arc Carbine | `Content/SourceArt/Weapons/Original/SM_Nyaagyu_ArcCarbine.fbx` | League firearms, background | Existing; SORA mon on the receiver |
| Weapon placeholders 5, 6, 15, 17 | `Content/SourceArt/SM_Weapon_05/06/15/17.fbx` | Coil matchlock (gunners), kanabō, micro-mortar, healing lance | Existing **primitives**; real meshes needed (C5) |
| Horse and tack study | `Content/SourceArt/Horses/Nyaagyu/` (+ `AnatomyStudy`, `RigStudy`, `NyaagyuAbumiTazunaStudy` textures) | Kurimaru, Arashi, 20 League horses | Existing (stylized, static); chestnut and black-bay coats, rig, gaits and the photoreal pass needed |
| Nyaakoto runtime skin and hero sources | `Content/SourceArt/Characters/Hero/`, `NyaakotoFirstPersonPaws/`, `NyaakotoDoStudy/` | Player body, first-person paws, cinematics | Existing; fails the photoreal head gate (B5) |
| Alien banker prototype | `Content/SourceArt/SK_AlienBanker.fbx`, `A_AlienBanker_Walk.fbx` | Blockout stand-in for Val Amort and enforcers | Existing prototype only |
| Provision kura / kura front | `Content/SourceArt/Environment/NyaagyuKura/`, `NyaagyuKuraFront/` | Base for the 二の丸 米蔵 cells | Existing; needs a two-storey variant and alien cell fronts |
| Estate wall | `Content/SourceArt/Environment/NyaagyuEstateWall/` | 土塀 around the courtyard and the last storehouse | Existing |
| Kawara bay and SORA eave cap | `Content/SourceArt/Environment/NyaagyuKawaraBay/`, `NyaagyuSoraEaveCapStudy/` | Storehouse and 多聞櫓 roofs (the castle's caps chiselled blank) | Existing (source-only) |
| Cargo stack | `Content/SourceArt/Environment/NyaagyuCargoStack/` | Rice-bale cover in the bailey; forge supplies | Existing |
| Torii, torii foot, lacquer | `Content/SourceArt/Environment/Original/SM_Nyaagyu_ToriiGate.fbx`, `NyaagyuToriiFootStudy/`, `ToriiLacquer/` | b17–b18 | Existing |
| Hero stone path, terrain, leaf silt | `NyaagyuHeroPath/`, `NyaagyuTerrain/`, `NyaagyuGroundDressing/` | Torii path, causeway verges | Existing (Estate-specific; reuse the materials) |
| Street debt terminal | `Content/SourceArt/Environment/StreetDebtTerminal/` | Dead terminal at the festival; b15 montage | Existing; needs a "dark" material state |
| Debt kiosk, lantern post | `Content/SourceArt/Environment/Original/SM_Alien_DebtKiosk.fbx`, `SM_Edo_LanternPost.fbx` | Citadel dressing; festival | Existing |
| Sluice, levy loom | `Content/SourceArt/Environment/NyaagyuSluice/`, `SilkFoundryLoom/` | b15 montage shots | Existing |
| Poly Haven CC0 palette | `Content/SourceArt/Environment/PolyHaven/` (wood_planks_dirt, stone_floor, brown_mud_leaves_01, GreyRoofTiles, WhitePlaster02, rusty_metal_02, Fern02, TreeSmall02, PineSaplingSmall, kloofendal HDRI) | Timber, stone, plaster, mud, foliage | Existing, CC0 (NOTICE recorded) |
| Fonts | `Content/SourceArt/Fonts/NotoSansCJKjp-Regular.otf` (OFL) | Subtitles, prompts, valuation labels | Existing |
| Catalog data | `catalog.json` chapter 8, weapons 5/6/12/15/17/18/19, 4 dialogue cues | Beat data, unlocks, anchor lines | Existing (catalog); schema 4 migration by L1 |

### 5.2 Environment kits needed (C2/C3)

| Kit | Contents | Notes |
|---|---|---|
| Causeway ride space | Earthen causeway modules (grass, willow roots, cart ruts); paddies harvested, flattened and flooded; 稲架 racks with drying rice; wet-moat stone revetment; 土橋; burnt 冠木門 (intact and breached); forward-camp knoll | Mesh terrain (bible §15.1); card rice LODs on Mac |
| Castle kit (Arena 3 campaign layer and 二の丸) | 石垣 modules (9 m and 5 m, 打込接ぎ, 算木積み corners); 多聞櫓 wall-turret with 狭間 and 石落とし; 高麗門; 櫓門 with 鏡柱 and 潜り戸; 雁木 steps; 坂 ramp with parapet; 埋門; two-storey 米蔵; 番所 | Photographed or authored calibrated plaster, stone and timber; Nanite on Windows |
| Siege dressing | 竹束 mantlets (with collision in the campaign layer only), ladders, forward-camp 陣幕, field forge enclosure, aid station | Cloth simulation for the 陣幕 |
| Alien citadel kit | Graphite barricades, seal stakes, seal anchors (3-plate states), cell glass fronts and tag rails, hexagonal spire modules, ramps, gantries, slit windows, lift platform and hawser, summit disc tiles (solid / marked / void states), dais, spine (with seam), engine ring, plinths and display cases | Shares ledger-line emissive materials with the C3 vault and flagship kits |
| Festival layer (Arena 1) | About 1,000 lanterns (lines, shopfronts, crossings), 振売 props, 見世棚 stalls, 神楽 stage, offerings, heirloom display tables, the new 高札 board | MegaLights on Windows; emissive clusters on Mac |
| Torii procession | Name-board stand, pack-horse loads, cedar grove dressing | Uses the existing torii |

### 5.3 Props needed

- **Council (b01):** 戸板 map table with the castle plan on washi, soroban, 矢立, 割符 box, 篝火 baskets, 床几.
- **Field forge (b04, b05):** 火床 (field hearth), 箱鞴 box bellows, 金床, quench tub, tongs rack, broken and mended tools (鍬, 鎌, 鋸, gun locks), 薬箱, bandage cloth, 筵 mats, ration bundles (握り飯 in bamboo-sheath wrappers), 胴乱 pouches with 早合.
- **Kanabō:** the hero mesh (oak body, forged iron studs, iron-bound butt) replaces the `SM_Weapon_06` primitive.
- **Cells (b07, b08):** alien inventory tags on cords, straw mats, 天水桶, 俵 stacks, the office alarm bell.
- **Gallery (b12):** 張子 toy, Washio 打刀 with a 代物弁済 tag, Tamakichi's master's 打ち上げ筒 (festival mortar), farmer's 鋤, lacquer bowls, a temple bell, the Nyaagyu 陣羽織 with its seizure label (torn state), valuation labels.
- **Summit (b13, b14):** Val Amort's plinth-mounted 文机, the restructuring contract, Sekireisai's 硯 (and its fall), the sword-cane (仕込み杖) with blade and cane states, collateral-construct goods sets (rice bales, lacquer chests, a plough, a loom frame, a cart wheel).
- **Epilogue (b15–b18):** 捕縄 rope; the lacquered registry box with bound pages and paste pot; SORA 団扇; the 名札掛け with pupils' plaques (a ch01 asset, reused); barley sheaves and a tally board (a ch04 asset, reused).

### 5.4 Characters needed (C6)

| Character | Notes |
|---|---|
| Val Amort (`banker`) | Final boss and cinematic hero: tall, age-wrinkled hairless skin, platinum ocular, long high-collared grey coat (removable in P3), sword-cane. A captured and kneeling state; the epilogue has him coatless. |
| Collateral constructs | Procedural assemblies of seized goods held in cyan fields, with assemble, slam and release states |
| Seizure walker | 4 m quadruped (bible §7), first seen here. Weigh-coils, sweep beam emitter, net launcher. |
| Enforcer family | `enforcer_rifle`, `blade_retainer`, `shield_enforcer`, `grenadier`, `marksman`, `drone`, `auditor` (L2/C6 shared) |
| Debt-bound conscripts | Local clothes with glowing collars; collar-cut state |
| League host | Ashigaru kit variants (at least 6: 陣笠, 腹当, sashimono), gunners with coil matchlocks and match cords, 20 riders in 当世具足 variants, engineers |
| Principals | Sekireisai (captive and freed states), Toranosuke (armor; haori-burning costume state), Oyuki (siege and festival dress), Kohagi, Kōzō, Tetsugorō, Okinu, Okuzu, Tamakichi, Tōkichi, Taemon, Otane, Iota, pupil Takemaru |
| Civilians | 12 prisoners (lower-village farmers, one child, elders), festival crowd (instanced; at least 10 costume variants), children |
| Horses | Kurimaru (chestnut mare), Arashi (black-bay stallion), 20 League horses (3 coats), 4 pack horses with 荷鞍 |

### 5.5 Animations needed (C7; mocap needs human performers, B5)

- **Mounted:** walk, trot and canter with the lateral amble checked by an equine animator; gallop; rein-in; spook, sidestep and rear; stumble-and-throw. Rider: yari thrust forward and right at gallop; yumi draw and release to the left while rising in the abumi (弓返り on release); katana right-side cut.
- **Volley ranks:** ready (構え, match to pan), fire, file back, 早合 reload with 込め矢, step up. Plus the player's command gesture.
- **Carry:** bundle carry with one-handed katana; two-handed box carry through a crowd.
- **Kanabō:** 300 ms windup, strike and 800 ms recovery (kernel timing); plate-break reaction on anchors.
- **Escort:** weak walk, crouch and hide on signal, cower, revive (hand and Healing Lance).
- **Capstan:** push loop for the player and NPCs; rope-slip stagger.
- **Val Amort:** beam cast (track, then lock), cleave, shard summon, seizure cast, cane draw, cane pair, thrust, foreclosure overhead, disarm reaction, kneel.
- **Nyaakoto first person:** 納刀 (0.6 s), sheathed mutō-dori catch-and-turn (1.5 s), 抜き付け draw-cut into the spine.
- **Cinematic performances:** council; haori burning; the storehouse reunion (seiza, kneeling, hand on shoulder); the inkstone push; rope binding; plaque rehang; barley counting.

### 5.6 VFX needed (C8, Niagara, honours flash reduction)

- **Charge:** hoof dust and mud clods, straw scatter from the 稲架, horse breath.
- **Alien:** cyan seal barriers and stake flare-outs; walker ground-line telegraph and sweep beam; seizure nets; seal-anchor plate shatter and core overload.
- **League:** match-cord glow; matchlock muzzle flash and a persistent white smoke bank (a gameplay occluder, 4 s); mortar arc decal and orange-brown blast; forge sparks, embers and heat haze.
- **Spire:** slit-window sun shafts; lift hawser friction smoke; gantry sparks.
- **Boss:** P1 beam lock line and amber cleave decals (replacing the prototype `Beam()` cylinders); orbiting shards and their breakage; amber tile-edge pulses; tiles falling into the cloud sea; construct assembly and gentle release of goods; mutō-dori hit-stop; the spine-seam split and a power-down wave down the spire.
- **Montage and epilogue:** cyan decaying out of every seal in the montage; lantern-field shimmer (MegaLights); small orange-gold 和火 fountains and rockets; dawn mist.

### 5.7 SFX needed (L5, CC0 or original)

- **Horses:** hooves on earth, causeway grass, the wooden bridge deck and 土橋 earth; snorts and whinnies; tack creak (leather, wood, iron). Kurimaru's barley-chewing idle is reused from ch01.
- **League signals:** 法螺貝 (conch) for "advance," 陣太鼓 for volley rhythm, rank calls.
- **Matchlocks:** match hiss, pan flash, report and the coil-breech whine; 早合 paper tear and ramrod.
- **Alien:** barrier hum; stake shatter; walker servo, footfalls, beam charge and fire; drones and nets.
- **Siege:** kanabō whoosh, graphite plate crack and core overload; forge anvil, bellows and quench hiss.
- **Cells and spire:** cell glass seal-cut; alarm bell (Japanese 半鐘 timbre for the office bell, which the aliens repurposed); capstan creak, pawl clicks and rope strain; wind in the void.
- **Boss:** the lift ascent into the clouds; the ring's glass-rod chimes (tonal, falling silent in b15); beam charge; cleave whoosh; shard pings; tile crack-and-drop; construct assembly (goods lifting, wood and straw) and release; cane unsheathing click; the mutō-dori grab; the draw-cut and spine shear; valley-wide power-down.
- **Festival:** crowd bed; 祭囃子 (篠笛, 締太鼓, 鉦); hawkers' calls; fireworks (small, dry pops).
- **Dawn:** birds and cedar wind.
- **Translation collar:** VO DSP (a band-limited formant chorus, never pitch-shifted; bible §6.3) and the key-slate radio filter for Iota.

### 5.8 Music cues (L5 stem states)

| State id | Beats | Direction |
|---|---|---|
| `ch08_council` | b01 | Low 尺八 and 琵琶 over a sustained taiko roll; the League motif stated once, quietly |
| `ch08_charge` | b02 | Full 和太鼓 ensemble with 法螺貝 calls; tempo follows gait (stems per gait); an alien sub-drone under the walkers |
| `ch08_siege` / `ch08_siege_low` | b03, b05 | Taiko ostinato locked to the volley cycle (9 s bar); the low variant for carrying |
| `ch08_forge` | b04 | Anvil-rhythm percussion (the ch05 manufacture motif) under the siege stems |
| `ch08_gate` | b06 | The siege stems at their densest; drops to a single drum as each anchor overloads |
| `ch08_cells` | b07 | Sparse 箏 and low strings; tension without percussion |
| `ch08_reunion` / `ch08_reunion_walk` | b08, b09 | Silence under 遅かったのう; then solo 尺八, the master's theme (ch01) |
| `ch08_spire` / `ch08_lift` | b10, b11 | Cold synthetic pulses interlocking with taiko; the lift cue rises in pitch with the platform's height |
| `ch08_heirlooms` | b12 | Near-silence; a music-box-like 箏 figure for the child's toy |
| `ch08_amort_intro` / `ch08_amort` | b13, b14 | Three phase stems: P1 cold and metric (glass chimes plus low brass-like synth); P2 adds taiko as goods are released; P3 strips to 尺八, 篠笛 and heartbeat drum for the duel |
| `ch08_release` | b15 | The League motif in full, then the master's theme; the alien pulses end one by one |
| `ch08_festival` | b16 | Diegetic 祭囃子 mixed with a warm score bed |
| `ch08_torii_dawn` / `credits_main` | b17, b18 | Solo 尺八 into the full main theme; the vermillion seal lands on the downbeat |

---

## 6. Data hand-off and open items

**For L1 (schema 4, save schema 6):**

1. **Site order.** ch08 completes site 1 (b04), then site 0 (b07), then site 2 (b16), which reverses the catalog's chain (site 0 `requires_sites: []`, site 1 `[0]`, site 2 `[1]`). Recommendation: keep the ids and names and re-chain them as site 1 `[]`, site 0 `[1]`, site 2 `[0]`. The mask bits then keep their meaning and the names still match bible §20. (Renumbering also works, but then every reference to "site 0 = refuge" changes.)
2. **Kill gates.** The catalog's `requires_kills` 4, 9 and 18 and the host driver's "collector spawns at 17 of 18" gate (offline-acceptance.md) are superseded by the beat chain. If L1 keeps kill floors, they stay reachable: b02 and b03 field 36 lethal enemies before b04 (§2.5). Volley-command kills should then be credited to the player.
3. **Map index.** The chapter's primary map changes from 1 to **3**; the epilogue beats b16–b18 use map 1 (bible §14).
4. **Objective text.** The catalog objective 「最後の街区を解放し、仲間と合流する」 should become 「債務の城塞を落とし、帳簿機関を断て」 / "Take the Debt Citadel and cut the Ledger Engine." `narrative` / `narrative_en` still fit and can stay.
5. **Anchor lines.** Catalog line 1 changes speaker from `artisan` to `foundry_master`. All four cues keep their exact text; the absolute `start_s` timings are dropped in favour of the triggers in §3.2.
6. **Proposed speaker ids** (aligned with the sibling chapter drafts): `enforcer`, `conscript`, `villager`, `resident`, `child`, `league_ashigaru`, `pupil_takemaru`. The pupil ids need one naming decision across ch01, ch02 and ch08.
7. **Proposed trigger and parameter extensions** (each marked in §7):
   - `event:<id>` scripted events, and `requires_flag` on a dialogue trigger (for b17's conditional exchange);
   - `combat_wave.complete.objectives[]` (b06);
   - `production_task.release` (b07 door seal-cuts) and `escort.bleedout_s` / `healing_lance_revive_s`;
   - `crank.moving_platform` and `rope_hazard` (b11);
   - `horseback_ride.charge`, `objectives`, `waves` and `arcs_deg` (b02);
   - `volley_command` (b03, b06);
   - `boss.hp`, `post_defeat` and `pattern_tables` (b14);
   - `supply_point` (b04, b10);
   - `carry.post_interact` and `crowd` (b16).
8. **Unlock mask.** Weapons 12, 17, 15, 6 in that order complete the §11 order. Chapter select for ch08 grants the ch01–ch07 mask plus 13 (the Phantom SMG auto-grant has already happened at ch07.b01).

**Other lanes.**

- **L2:** `seizure_walker` (first appearance), the `board_platform` and `cut_rope` drone behaviours, the `net_anvil` and `net_npc` behaviours, anchor plates, and deterministic volley resolution.
- **L3:** the §2.2 tables for `bosses.json`.
- **L4:** the §3.3 prompts, Command binding, rank pips, floor-grid overlay option, and the accessible palette for tile edges.
- **L5:** the §5.8 states and captioned barks.
- **C9:** sequences `LS_Ch08_B01`, `B08`, `B13`, `B15` and `B18`, plus the boss phase blends.

**Open reviews:**

- Native Japanese review of every line and reading (B7), especially Kamigata, Kyoto and alien-keigo registers, and the temporal-hour phrasing 「あと四刻」.
- Historian and practitioner review of the **verify** items in §4.
- Equine review of the charge.
- A practitioner's review of the sheathed mutō-dori and 抜き付け motion.
- Playtest telemetry for the 55-minute target (the boss's 540 s and b02's 300 s are the biggest risks).

---

## 7. Machine-readable beat data (YAML)

This is the complete chapter in bible §12 shape, with the schema 4 proposal and its extensions marked. Line text lives once, in `lines:`. Beats refer to line ids in their `dialogue`, `subtitles` and `barks` fields; `dialogue`-type beats list their line ids in `lines`. This block was generated from the same data as the tables above and was parsed back to check the round trip.

```yaml
chapter: ch08_debt_citadel
schema_proposal: 4
title_ja: "最後の解放"
title_en: "Final Liberation"
objective_ja: "債務の城塞を落とし、帳簿機関を断て"
objective_en: "Take the Debt Citadel and cut the Ledger Engine."
map: 3
epilogue_map: 1
target_s: 3300
mix_min: {C: 21.0, E: 2.0, S: 0.0, P: 14.0, M: 5.0, Cin: 13.0}
places:
  - pl_kakuredani
  - pl_causeway
  - pl_outer_bailey
  - pl_otemon
  - pl_collateral_cells
  - pl_ledger_spire
  - pl_ledger_engine
  - pl_lantern_ward_festival
  - pl_higashi_torii
unlock_order: [12, 17, 15, 6]
sites:
  - {site: 1, beat: ch08.b04, name_ja: "共同の修理工房", name_en: "Communal repair workshop", requires_sites: []}
  - {site: 0, beat: ch08.b07, name_ja: "住民の避難所", name_en: "Civilian refuge", requires_sites: [1]}
  - {site: 2, beat: ch08.b16, name_ja: "解放の集会所", name_en: "Liberation assembly", requires_sites: [0]}
speakers:
  - {token: nyaakoto, id: samurai, ja: "ニャーコト", en: Nyaakoto, status: existing}
  - {token: sekireisai, id: mentor, ja: "猫柳生 石鈴斎", en: "Nyaagyu Sekireisai", status: existing}
  - {token: toranosuke, id: rival, ja: "鷲尾 虎之介", en: "Washio Toranosuke", status: "bible §6.1"}
  - {token: oyuki, id: leader, ja: "白澄 お雪", en: "Shirasumi Oyuki", status: "bible §6.1"}
  - {token: kohagi, id: scout, ja: "小萩", en: Kohagi, status: existing}
  - {token: taemon, id: farmer, ja: "庄屋 田右衛門", en: "Headman Taemon", status: existing}
  - {token: otane, id: farmer_young, ja: "お種", en: Otane, status: "bible §6.2"}
  - {token: tokichi, id: lantern_maker, ja: "提灯師 灯吉", en: "Tōkichi", status: "bible §6.2"}
  - {token: tamakichi, id: fireworks, ja: "花火師 玉吉", en: Tamakichi, status: "bible §6.2"}
  - {token: tetsugoro, id: gunsmith, ja: "鉄砲鍛冶 鉄五郎", en: "Tetsugorō", status: "bible §6.2"}
  - {token: kozo, id: foundry_master, ja: "村下 鋼蔵", en: "Murage Kōzō", status: "bible §6.2"}
  - {token: okinu, id: weaver, ja: "織師 お絹", en: Okinu, status: "bible §6.2"}
  - {token: okuzu, id: apothecary, ja: "薬師 お葛", en: Okuzu, status: "bible §6.2"}
  - {token: iota, id: clerk, ja: "会計補 イオタ", en: "Junior Auditor Iota", status: "bible §6.3"}
  - {token: valamort, id: banker, ja: "大徴収官 ヴァル・アモルト", en: "High Collector Val Amort", status: existing}
  - {token: enforcer, id: enforcer, ja: "執行兵", en: Enforcer, status: "PROPOSED generic"}
  - {token: conscript, id: conscript, ja: "債縛衆", en: Debt-Bound, status: "PROPOSED generic"}
  - {token: villager, id: villager, ja: "村人", en: Villager, status: "PROPOSED generic"}
  - {token: resident, id: resident, ja: "町の衆", en: Resident, status: "PROPOSED generic"}
  - {token: child, id: child, ja: "子ども", en: Child, status: "PROPOSED generic"}
  - {token: ashigaru, id: league_ashigaru, ja: "空紋の足軽", en: "League soldier", status: "PROPOSED generic"}
  - {token: takemaru, id: pupil_takemaru, ja: "門弟 竹丸", en: Takemaru, status: "PROPOSED minor"}
extensions_proposed:
  - "event:<id> dialogue trigger (scripted beat events) and requires_flag on a dialogue group"
  - "cine@<s> is written as subtitles[].at_s"
  - "horseback_ride: charge{}, objectives[], waves[], arcs_deg{}, route_length_m, horse_stamina{} as object"
  - "combat_wave: complete.objectives[] (same shape as stealth_zone), volley_command{}, scripted{}"
  - "production_task: release{} (pre-escort seal-cuts), escort.bleedout_s, escort.healing_lance_revive_s, escort.path_length_m"
  - "production_task.crank: moving_platform{}, rope_hazard{}; coop_npc as {npcs, turns_per_s_per_npc}"
  - "production_task.carry: dropped_item_returns_after_s, post_interact{}; beat-level crowd{}, combat:false"
  - "supply_point on beats that host a League 補給所"
  - "boss: hp{}, finisher, lethal_finisher, post_defeat{}, phases[].target_s, pattern_tables (L3 owns the table content)"
  - "cinematic end_state.mounted and end_state.next"
beats:
  - id: ch08.b01
    type: cinematic
    place: pl_kakuredani
    title_ja: "夜明け前の軍議"
    title_en: "War council before dawn"
    target_s: 150
    checkpoint: true
    sequence: "/Game/Campaign/Ch08/Cinematics/LS_Ch08_B01_Council"
    duration_s: 150
    skippable: true
    fallback: camera_blend
    end_state:
      player_transform: ps_ch08_causeway_start
      mounted: kurimaru
      equipped: {hip: 0, back: 18, polearm: 19, side: keep, firearm: keep}
    unlocks: {weapons: [12, 17], mechanics: []}
    music: ch08_council
    subtitles:
      - {line: ch08.b01.iota.001, at_s: 8.0}
      - {line: ch08.b01.iota.002, at_s: 15.0}
      - {line: ch08.b01.oyuki.003, at_s: 25.0}
      - {line: ch08.b01.kohagi.004, at_s: 34.0}
      - {line: ch08.b01.kozo.005, at_s: 44.0}
      - {line: ch08.b01.kozo.006, at_s: 50.0}
      - {line: ch08.b01.okinu.007, at_s: 56.0}
      - {line: ch08.b01.okuzu.008, at_s: 66.0}
      - {line: ch08.b01.toranosuke.009, at_s: 80.0}
      - {line: ch08.b01.nyaakoto.010, at_s: 96.0}
      - {line: ch08.b01.nyaakoto.011, at_s: 106.0}
      - {line: ch08.b01.oyuki.012, at_s: 116.0}
  - id: ch08.b02
    type: horseback_ride
    mode: charge
    place: pl_causeway
    title_ja: "土手道を突破せよ"
    title_en: "Break through on the causeway"
    target_s: 300
    checkpoint: true
    horse: kurimaru
    route: spl_ch08_causeway_charge
    x_route_length_m: 1750
    complete: "volume_enter:vol_outer_koguchi"
    gaits: [walk, trot, canter, gallop]
    weapons: [19, 18, 0]
    x_arcs_deg: {"19": [-10, 90], "18": [-170, 15], "0": [20, 110]}
    fear: {spook_radius_cm: 900, recover_s: 2.5}
    horse_stamina: {max: 100, gallop_drain_per_s: 6, canter_regen_per_s: 3, trot_regen_per_s: 8}
    auto_steer: setting
    dismount_allowed: false
    on_horse_down: checkpoint
    x_charge:
      riders: 20
      rival: {npc: toranosuke, horse: arashi, slot: right}
      formation: column_of_twos
      lance_bonus_gallop: 1.5
      catch_up_cm_s: 150
      riders_break_missed_pylon_after_s: 8
    objectives:
      - id: pylon_1
        kind: destroy
        actor: seal_stake_01
        volume: vol_pylon_1
        breaks_on: [yari_thrust_canter_or_faster, arrow_x2]
        optional: true
      - id: pylon_2
        kind: destroy
        actor: seal_stake_02
        volume: vol_pylon_2
        breaks_on: [yari_thrust_canter_or_faster, arrow_x2]
        optional: true
      - id: pylon_3
        kind: destroy
        actor: seal_stake_03
        volume: vol_pylon_3
        breaks_on: [yari_thrust_canter_or_faster, arrow_x2]
        optional: true
    waves:
      - trigger: start
        enemies:
          - {type: enforcer_rifle, count: 3, spawn: sp_cw_barricade_1}
      - trigger: "progress_at:0.2"
        enemies:
          - {type: drone, count: 3, spawn: sp_cw_air_1}
      - trigger: "progress_at:0.25"
        enemies:
          - {type: seizure_walker, count: 1, spawn: sp_cw_paddy_left, invulnerable: true, script: sweep_only}
      - trigger: "progress_at:0.35"
        enemies:
          - {type: enforcer_rifle, count: 4, spawn: sp_cw_barricade_2}
      - trigger: "progress_at:0.5"
        enemies:
          - {type: enforcer_rifle, count: 3, spawn: sp_cw_west_dike}
      - trigger: "progress_at:0.55"
        enemies:
          - {type: seizure_walker, count: 1, spawn: sp_cw_paddy_right, invulnerable: true, script: sweep_only}
      - trigger: "progress_at:0.65"
        enemies:
          - {type: drone, count: 3, spawn: sp_cw_air_2}
      - trigger: "progress_at:0.85"
        enemies:
          - {type: enforcer_rifle, count: 4, spawn: sp_cw_moat_bridge}
    x_scripted:
      walker_sweep_beam:
        telegraph: "cyan ground line across the causeway"
        windup_ms: 1100
        beam_s: 1.5
        width_cm: 300
        damage: 30
        spooks_horse: true
      outro: "Tamakichi's siege mortars fell walker_right and breach the outer 冠木門; walker_left withdraws into the bailey (returns in b03 wave 3)."
    music: ch08_charge
    dialogue:
      - {"on": beat_start, lines: [ch08.b02.toranosuke.001], mode: ambient}
      - {"on": "progress_at:0.05", lines: [ch08.b02.toranosuke.002], mode: ambient}
      - {"on": "alert_state:alert", lines: [ch08.b02.enforcer.003], mode: bark}
      - {"on": "pattern:walker_sweep_beam", lines: [ch08.b02.iota.004], mode: radio}
      - {"on": "volume_enter:vol_pylon_1", lines: [ch08.b02.toranosuke.005], mode: ambient}
      - {"on": "event:horse_spooked", lines: [ch08.b02.nyaakoto.006], mode: bark, repeatable: true, cooldown_s: 30}
      - {"on": "event:enemy_retreat", lines: [ch08.b02.enforcer.007], mode: bark, repeatable: true, cooldown_s: 45}
      - {"on": "progress_at:0.55", lines: [ch08.b02.toranosuke.008], mode: ambient}
      - {"on": "progress_at:0.95", lines: [ch08.b02.tamakichi.009], mode: ambient}
      - {"on": player_died, lines: [ch08.b02.toranosuke.010], mode: ambient, repeatable: true, cooldown_s: 120}
    fail: {"on": player_died, to: checkpoint}
  - id: ch08.b03
    type: combat_wave
    place: pl_outer_bailey
    title_ja: "輪番撃ちで外郭を制せよ"
    title_en: "Take the outer bailey with rotating volleys"
    target_s: 240
    checkpoint: true
    bounds: vol_outer_bailey
    max_alive: 8
    allies:
      - {npc: league_teppo_rank_a, role: volley_rank, count: 4, downable: true}
      - {npc: league_teppo_rank_b, role: volley_rank, count: 4, downable: true}
      - {npc: league_teppo_rank_c, role: volley_rank, count: 4, downable: true}
      - {npc: toranosuke, role: melee_flank, downable: true}
      - {npc: league_yari, role: hold_line, count: 6, downable: true}
      - {npc: tamakichi, role: mortar_crew, downable: false}
      - {npc: oyuki, role: noncombat, downable: false}
    x_volley_command:
      ranks: 3
      gunners_per_rank: 4
      weapon: 5
      order_delay_ms: 800
      rank_cycle_s: 9.0
      target_radius_cm: 400
      max_range_cm: 6000
      effect:
        unshielded: "288 damage split across up to 4 targets in the ring, fixed order nearest-first"
        shield_enforcer: "shield stagger 2.0 s"
        seizure_walker: "8% max HP and a 1.0 s leg stagger"
      smoke_obscure_s: 4.0
      easy_auto_order: true
    waves:
      - trigger: start
        enemies:
          - {type: enforcer_rifle, count: 6, spawn: sp_ob_barricade}
          - {type: marksman, count: 1, spawn: sp_ob_tamon_turret}
      - trigger: "alive_below:3"
        enemies:
          - {type: shield_enforcer, count: 3, spawn: sp_ob_sally_port}
          - {type: blade_retainer, count: 2, spawn: sp_ob_sally_port}
      - trigger: prev_cleared
        enemies:
          - {type: seizure_walker, count: 1, spawn: sp_ob_north_turret}
          - {type: drone, count: 3, spawn: sp_ob_air}
    complete: all_waves_cleared
    nonlethal_types: [bound_conscript]
    unlocks: {weapons: [15], mechanics: [volley_command]}
    music: ch08_siege
    dialogue:
      - {"on": beat_start, lines: [ch08.b03.tetsugoro.001], mode: ambient}
      - {"on": "event:volley_tutorial", lines: [ch08.b03.oyuki.002], mode: ambient}
      - {"on": "event:volley_ready", lines: [ch08.b03.ashigaru.003], mode: bark, repeatable: true, cooldown_s: 6}
      - {"on": "event:volley_ordered", lines: [ch08.b03.nyaakoto.004], mode: bark, repeatable: true, cooldown_s: 2}
      - {"on": "event:volley_rotate", lines: [ch08.b03.ashigaru.005], mode: bark, repeatable: true, cooldown_s: 8}
      - {"on": "event:volley_ordered_3", lines: [ch08.b03.oyuki.006], mode: ambient}
      - {"on": "event:wave_start_2", lines: [ch08.b03.enforcer.007], mode: bark}
      - {"on": "event:wave_start_3", lines: [ch08.b03.tamakichi.008], mode: ambient}
      - {"on": beat_complete, lines: [ch08.b03.oyuki.009], mode: ambient}
    fail: {"on": player_died, to: checkpoint}
  - id: ch08.b04
    type: production_task
    task: defend
    place: pl_outer_bailey
    title_ja: "野鍛冶と手当所を守れ"
    title_en: "Defend the field forge and aid station"
    target_s: 180
    checkpoint: true
    site: 1
    defend:
      targets:
        - {actor: nokaji_forge, hp: 1200}
        - {actor: aid_station, hp: 800}
      duration_s: 150
      fail_on_target_destroyed: true
      repair_interact:
        actor: nokaji_anvil_net
        hold_s: 2.0
        rule: "a drone net on the anvil pauses repairs and the progress bar until cut"
    waves:
      - trigger: start
        enemies:
          - {type: enforcer_rifle, count: 4, spawn: sp_ob_sally_port}
      - trigger: "after_s:40"
        enemies:
          - {type: grenadier, count: 2, spawn: sp_ob_wall_nw, focus_target: nokaji_forge}
      - trigger: "after_s:80"
        enemies:
          - {type: blade_retainer, count: 3, spawn: sp_ob_sally_port}
          - {type: drone, count: 2, spawn: sp_ob_air, behavior: net_anvil}
      - trigger: "after_s:115"
        enemies:
          - {type: bound_conscript, count: 4, spawn: sp_ob_sally_port}
    nonlethal_types: [bound_conscript]
    allies:
      - {npc: kozo, role: noncombat, downable: false}
      - {npc: tetsugoro, role: noncombat, downable: false}
      - {npc: okuzu, role: noncombat, downable: false}
      - {npc: league_yari, role: hold_line, count: 4, downable: true}
    registry: {item_ja: "修理した道具", item_en: "Tools repaired", qty: 36, unit_ja: "点", unit_en: items}
    x_supply_point: sp_nokaji
    music: ch08_forge
    dialogue:
      - {"on": beat_start, lines: [ch08.b04.kozo.001, ch08.b04.okuzu.002], mode: ambient}
      - {"on": "progress_at:0.25", lines: [ch08.b04.kohagi.003], mode: ambient}
      - {"on": "progress_at:0.3", lines: [ch08.b04.enforcer.004], mode: bark}
      - {"on": "event:net_on_anvil", lines: [ch08.b04.kozo.005], mode: ambient, repeatable: true, cooldown_s: 40}
      - {"on": "event:wave_start_4", lines: [ch08.b04.conscript.006], mode: bark}
      - {"on": "site_restored:1", lines: [ch08.b04.kozo.007], mode: ambient}
    fail: {"on": player_died, to: checkpoint}
  - id: ch08.b05
    type: production_task
    task: carry
    place: pl_outer_bailey
    title_ja: "兵糧と早合を三つの組へ"
    title_en: "Bring rations and cartridges to three squads"
    target_s: 120
    checkpoint: true
    carry:
      item: ration_bundle
      count: 3
      pickups: [pk_nokaji_rations]
      dropoffs: [do_squad_west, do_squad_mid, do_squad_east]
      loadout_while_carrying: [katana_one_hand]
      move_speed_mult: 0.8
      drop_on_hit: true
      dropped_item_returns_after_s: 20
    waves:
      - trigger: start
        enemies:
          - {type: marksman, count: 2, spawn: sp_ob_tamon_loophole}
      - trigger: "progress_at:0.34"
        enemies:
          - {type: drone, count: 2, spawn: sp_ob_air}
    x_scripted:
      do_squad_west: "squad west suppresses the western marksman (no fire for 20 s)"
      do_squad_mid: "squad mid's volley kills the eastern marksman"
      do_squad_east: "all three squads open fire on the 多聞櫓 loopholes (b06 set-up)"
    registry: {item_ja: "兵糧", item_en: Rations, qty: 36, unit_ja: "食", unit_en: meals}
    music: ch08_siege_low
    dialogue:
      - {"on": beat_start, lines: [ch08.b05.okuzu.001, ch08.b05.kohagi.002], mode: ambient}
      - {"on": "pattern:marksman_lock", lines: [ch08.b05.enforcer.003], mode: bark, repeatable: true, cooldown_s: 10}
      - {"on": "item_delivered:do_squad_west", lines: [ch08.b05.ashigaru.004], mode: ambient}
      - {"on": "item_delivered:do_squad_east", lines: [ch08.b05.ashigaru.005], mode: ambient}
      - {"on": beat_complete, lines: [ch08.b05.oyuki.006], mode: ambient}
    fail: {"on": player_died, to: checkpoint}
  - id: ch08.b06
    type: combat_wave
    place: pl_otemon
    title_ja: "大手門の封印錨を砕け"
    title_en: "Smash the main gate's seal anchors"
    target_s: 240
    checkpoint: true
    bounds: vol_masugata
    max_alive: 7
    allies:
      - {npc: toranosuke, role: melee_flank, downable: true}
      - {npc: league_teppo_rank_a, role: volley_rank, count: 4, downable: true}
      - {npc: league_teppo_rank_b, role: volley_rank, count: 4, downable: true}
      - {npc: league_yari, role: mantlet_bearer, count: 4, downable: true}
    x_volley_command:
      ranks: 2
      gunners_per_rank: 4
      weapon: 5
      order_delay_ms: 800
      rank_cycle_s: 9.0
      target_radius_cm: 400
      max_range_cm: 4000
      note: "same rules as b03; two ranks at the 高麗門"
    waves:
      - trigger: start
        enemies:
          - {type: enforcer_rifle, count: 4, spawn: sp_ms_tamon_wall}
          - {type: grenadier, count: 1, spawn: sp_ms_yaguramon_top}
      - trigger: "progress_at:0.33"
        enemies:
          - {type: shield_enforcer, count: 2, spawn: sp_ms_kuguri_door}
          - {type: blade_retainer, count: 2, spawn: sp_ms_kuguri_door}
      - trigger: "progress_at:0.66"
        enemies:
          - {type: drone, count: 3, spawn: sp_ms_air}
          - {type: grenadier, count: 1, spawn: sp_ms_yaguramon_top}
          - {type: marksman, count: 1, spawn: sp_ms_tamon_wall_e}
    complete:
      objectives:
        - id: anchor_1
          kind: destroy
          actor: seal_anchor_left
          plates: 3
          damage_filter: {"6": 1, "8": 0.5, "15": 1}
          overload_s: 2.0
        - id: anchor_2
          kind: destroy
          actor: seal_anchor_right
          plates: 3
          damage_filter: {"6": 1, "8": 0.5, "15": 1}
          overload_s: 2.0
        - id: anchor_3
          kind: destroy
          actor: seal_anchor_wallwalk
          plates: 3
          damage_filter: {"6": 1, "8": 0.5, "15": 1}
          overload_s: 2.0
    nonlethal_types: [bound_conscript]
    unlocks: {weapons: [6], mechanics: []}
    music: ch08_gate
    dialogue:
      - {"on": beat_start, lines: [ch08.b06.kozo.001], mode: ambient}
      - {"on": "volume_enter:vol_masugata", lines: [ch08.b06.toranosuke.002, ch08.b06.kohagi.003], mode: ambient}
      - {"on": "alert_state:alert", lines: [ch08.b06.enforcer.004], mode: bark}
      - {"on": "event:objective_done_anchor_1", lines: [ch08.b06.iota.005], mode: radio}
      - {"on": "event:objective_done_anchor_2", lines: [ch08.b06.enforcer.006], mode: bark}
      - {"on": "event:enemy_retreat", lines: [ch08.b06.enforcer.007], mode: bark}
      - {"on": beat_complete, lines: [ch08.b06.ashigaru.008], mode: ambient}
    fail: {"on": player_died, to: checkpoint}
  - id: ch08.b07
    type: production_task
    task: escort
    place: pl_collateral_cells
    title_ja: "担保牢の民を避難所へ"
    title_en: "Lead the prisoners to the refuge"
    target_s: 240
    checkpoint: true
    site: 0
    x_release:
      interact_points: [cell_door_1, cell_door_2, cell_door_3, cell_door_4]
      per_point_s: 2.0
      action: seal_cut
    escort:
      npcs:
        - {group: prisoners_a, count: 4}
        - {group: prisoners_b, count: 4}
        - {group: prisoners_c, count: 3, includes: [takemaru]}
        - {group: child_1, count: 1}
      path: spl_cells_to_refuge
      path_length_m: 180
      speed_cm_s: 260
      wait_for_player_cm: 1200
      fail_on_npc_death: true
      hide_on_signal: true
      npc_health: 150
      down_revive_s: 3
      bleedout_s: 30
      healing_lance_revive_s: 1.0
    waves:
      - trigger: start
        enemies:
          - {type: enforcer_rifle, count: 3, spawn: sp_cells_guard}
          - {type: auditor, count: 2, spawn: sp_cells_office}
      - trigger: "progress_at:0.4"
        enemies:
          - {type: drone, count: 3, spawn: sp_cells_air, behavior: net_npc, net_cut_s: 1.5}
      - trigger: "progress_at:0.7"
        enemies:
          - {type: blade_retainer, count: 2, spawn: sp_ramp_top}
          - {type: shield_enforcer, count: 1, spawn: sp_ramp_top}
          - {type: bound_conscript, count: 3, spawn: sp_ramp_top}
    x_scripted: {auditor_alarm: "an auditor who reaches the office bell triggers wave 2 immediately"}
    nonlethal_types: [bound_conscript]
    music: ch08_cells
    dialogue:
      - {"on": beat_start, lines: [ch08.b07.kohagi.001], mode: ambient}
      - {"on": "event:door_1_open", lines: [ch08.b07.villager.002, ch08.b07.nyaakoto.003], mode: ambient}
      - {"on": "event:door_2_open", lines: [ch08.b07.child.004], mode: ambient}
      - {"on": "event:door_3_open", lines: [ch08.b07.takemaru.005], mode: ambient}
      - {"on": "event:first_hide_signal", lines: [ch08.b07.nyaakoto.006], mode: ambient}
      - {"on": "volume_enter:vol_refuge", lines: [ch08.b07.taemon.007], mode: ambient}
      - {"on": "site_restored:0", lines: [ch08.b07.oyuki.008], mode: ambient}
      - {"on": beat_complete, lines: [ch08.b07.takemaru.009], mode: ambient}
    fail: {"on": player_died, to: checkpoint}
  - id: ch08.b08
    type: cinematic
    place: pl_collateral_cells
    title_ja: "一番奥の蔵"
    title_en: "The last storehouse"
    target_s: 120
    checkpoint: true
    sequence: "/Game/Campaign/Ch08/Cinematics/LS_Ch08_B08_LastStorehouse"
    duration_s: 120
    skippable: true
    fallback: camera_blend
    end_state: {player_transform: ps_deep_kura_door, equipped: keep}
    music: ch08_reunion
    subtitles:
      - {line: ch08.b08.nyaakoto.001, at_s: 16.0}
      - {line: ch08.b08.sekireisai.002, at_s: 22.0}
      - {line: ch08.b08.nyaakoto.003, at_s: 29.0}
      - {line: ch08.b08.sekireisai.004, at_s: 35.0}
      - {line: ch08.b08.sekireisai.005, at_s: 42.0}
      - {line: ch08.b08.nyaakoto.006, at_s: 48.0}
      - {line: ch08.b08.sekireisai.007, at_s: 66.0}
      - {line: ch08.b08.toranosuke.008, at_s: 72.0}
      - {line: ch08.b08.sekireisai.009, at_s: 80.0}
  - id: ch08.b09
    type: dialogue
    mode: ambient
    place: pl_collateral_cells
    title_ja: "塔へ向かえ"
    title_en: "Head for the spire"
    target_s: 60
    checkpoint: false
    trigger: beat_start
    interrupt: queue
    camera: soft_lookat
    complete: "volume_enter:vol_spire_entrance"
    music: ch08_reunion_walk
    lines:
      - ch08.b09.nyaakoto.001
      - ch08.b09.sekireisai.002
      - ch08.b09.sekireisai.003
      - ch08.b09.nyaakoto.004
      - ch08.b09.sekireisai.005
    dialogue:
      - "on": beat_start
        lines:
          - ch08.b09.nyaakoto.001
          - ch08.b09.sekireisai.002
          - ch08.b09.sekireisai.003
          - ch08.b09.nyaakoto.004
          - ch08.b09.sekireisai.005
        mode: ambient
  - id: ch08.b10
    type: combat_wave
    place: pl_ledger_spire
    title_ja: "帳簿塔を登れ"
    title_en: "Climb the Ledger Spire"
    target_s: 240
    checkpoint: true
    bounds: vol_spire_L1_L4
    max_alive: 7
    allies:
      - {npc: kohagi, role: skirmisher, downable: true}
      - {npc: toranosuke, role: melee_flank, downable: true}
      - {npc: tetsugoro, role: noncombat_follow, downable: false}
      - {npc: league_engineer, role: noncombat_follow, count: 2, downable: false}
    waves:
      - trigger: start
        enemies:
          - {type: enforcer_rifle, count: 4, spawn: sp_sp_L2_ramp}
          - {type: marksman, count: 1, spawn: sp_sp_L2_gantry_far}
      - trigger: "alive_below:2"
        enemies:
          - {type: shield_enforcer, count: 2, spawn: sp_sp_L3_ramp_down}
          - {type: blade_retainer, count: 2, spawn: sp_sp_L3_ramp_down}
      - trigger: "volume_enter:vol_spire_L3"
        enemies:
          - {type: drone, count: 4, spawn: sp_sp_void_air}
          - {type: grenadier, count: 1, spawn: sp_sp_L4_gantry}
          - {type: auditor, count: 2, spawn: sp_sp_L4_office}
    complete: all_waves_cleared
    x_scripted:
      auditor_alarm: "an auditor at an alarm panel drops a shutter over the L3 shortcut (route gets longer, never a fail)"
    x_supply_point: sp_spire_base
    nonlethal_types: [bound_conscript]
    music: ch08_spire
    dialogue:
      - {"on": beat_start, lines: [ch08.b10.kohagi.001], mode: ambient}
      - {"on": "alert_state:alert", lines: [ch08.b10.enforcer.002], mode: bark}
      - {"on": "alert_state:search", lines: [ch08.b10.enforcer.003], mode: bark, repeatable: true, cooldown_s: 30}
      - {"on": "volume_enter:vol_spire_void_edge", lines: [ch08.b10.toranosuke.004], mode: ambient}
      - {"on": "volume_enter:vol_spire_L3", lines: [ch08.b10.iota.005], mode: radio}
      - {"on": "event:wave_start_3", lines: [ch08.b10.tetsugoro.006], mode: ambient}
      - {"on": "event:enemy_retreat", lines: [ch08.b10.enforcer.007], mode: bark}
    fail: {"on": player_died, to: checkpoint}
  - id: ch08.b11
    type: production_task
    task: crank
    place: pl_ledger_spire
    title_ja: "轆轤を回して昇れ"
    title_en: "Crank the capstan to rise"
    target_s: 180
    checkpoint: true
    crank:
      actor: lift_capstan_01
      turns_required: 48
      turn_rate_band: [0.4, 1.0]
      progress_decay_per_s: 0.01
      stamina_per_turn: 5
      interruptible: true
      coop_npc: {npcs: [tetsugoro, league_engineer_1, league_engineer_2], turns_per_s_per_npc: 0.15}
      moving_platform:
        actor: freight_lift_platform
        size_cm: [600, 600]
        travel_cm: 11500
        from: L4_27m
        to: hall_142m
      rope_hazard: {rule: "while a drone's cutter touches the hawser, decay x3", cut_drone_to_clear: true}
    waves:
      - trigger: "progress_at:0.25"
        enemies:
          - {type: drone, count: 3, spawn: sp_lift_gantry_5575cm, behavior: cut_rope}
      - trigger: "progress_at:0.5"
        enemies:
          - {type: enforcer_rifle, count: 3, spawn: sp_lift_gantry_8450cm}
      - trigger: "progress_at:0.75"
        enemies:
          - {type: shield_enforcer, count: 1, spawn: sp_lift_gantry_11325cm, behavior: board_platform}
          - {type: blade_retainer, count: 2, spawn: sp_lift_gantry_11325cm, behavior: board_platform}
    nonlethal_types: [bound_conscript]
    music: ch08_lift
    dialogue:
      - {"on": beat_start, lines: [ch08.b11.tetsugoro.001], mode: ambient}
      - {"on": "event:crank_turn_6", lines: [ch08.b11.ashigaru.002], mode: bark, repeatable: true, cooldown_s: 8}
      - {"on": "progress_at:0.25", lines: [ch08.b11.kohagi.003], mode: ambient}
      - "on": "event:player_left_capstan"
        lines: [ch08.b11.tetsugoro.004]
        mode: ambient
        repeatable: true
        cooldown_s: 45
      - {"on": "progress_at:0.5", lines: [ch08.b11.enforcer.005], mode: bark}
      - {"on": "progress_at:0.75", lines: [ch08.b11.iota.006], mode: radio}
      - {"on": beat_complete, lines: [ch08.b11.toranosuke.007], mode: ambient}
    fail: {"on": player_died, to: checkpoint}
  - id: ch08.b12
    type: explore_optional
    place: pl_ledger_spire
    title_ja: "押収品を調べる"
    title_en: "Search the seized goods"
    target_s: 120
    checkpoint: false
    requires: [ch08.b11]
    optional: true
    volume: vol_heirloom_hall
    pois:
      - {id: poi_child_toy, kind: lore}
      - {id: poi_washio_sword, kind: cache, collectible: ch08.c03}
      - {id: poi_tamakichi_mortar, kind: lore, collectible: ch08.c04}
      - {id: poi_scroll_case, kind: lore, collectible: ch08.c05}
      - {id: poi_covered_mon, kind: lore, interact: "tear the seizure label off the Nyaagyu 陣羽織"}
      - {id: poi_cloud_window, kind: vista}
    rewards: [ch08.c03, ch08.c04, ch08.c05, arrows_12]
    exit_hint_after_s: 60
    music: ch08_heirlooms
    dialogue:
      - {"on": "volume_enter:vol_heirloom_hall", lines: [ch08.b12.iota.001], mode: radio}
      - {"on": "event:poi_child_toy", lines: [ch08.b12.nyaakoto.002], mode: ambient}
      - {"on": "event:collectible_ch08_c03", lines: [ch08.b12.nyaakoto.003], mode: ambient}
      - {"on": "event:collectible_ch08_c05", lines: [ch08.b12.sekireisai.004], mode: ambient}
      - {"on": "idle_s:60", lines: [ch08.b12.iota.005], mode: radio}
  - id: ch08.b13
    type: cinematic
    place: pl_ledger_engine
    title_ja: "帳簿機関"
    title_en: "The Ledger Engine"
    target_s: 120
    checkpoint: true
    requires: [ch08.b11]
    sequence: "/Game/Campaign/Ch08/Cinematics/LS_Ch08_B13_Restructuring"
    duration_s: 120
    skippable: true
    fallback: camera_blend
    end_state: {player_transform: ps_engine_disc_south, equipped: keep}
    music: ch08_amort_intro
    subtitles:
      - {line: ch08.b13.valamort.001, at_s: 12.0}
      - {line: ch08.b13.valamort.002, at_s: 20.0}
      - {line: ch08.b13.nyaakoto.003, at_s: 30.0}
      - {line: ch08.b13.valamort.004, at_s: 36.0}
      - {line: ch08.b13.valamort.005, at_s: 46.0}
      - {line: ch08.b13.valamort.006, at_s: 72.0}
      - {line: ch08.b13.nyaakoto.007, at_s: 82.0}
      - {line: ch08.b13.valamort.008, at_s: 94.0}
  - id: ch08.b14
    type: boss
    place: pl_ledger_engine
    title_ja: "大徴収官を捕らえよ"
    title_en: "Capture the High Collector"
    target_s: 540
    checkpoint: true
    boss: boss_val_amort
    arena: {volume: vol_engine_disc, lock: true}
    phases:
      - {hp_pct_start: 100, pattern_table: amort_p1_collector, target_s: 150}
      - hp_pct_start: 70
        pattern_table: amort_p2_seizure
        adds: collateral_constructs
        arena_mod: seizure_tiles
        target_s: 180
      - {hp_pct_start: 40, pattern_table: amort_p3_cane, arena_mod: field_off, target_s: 210}
    defeat: capture
    finisher: muto_dori
    x_lethal_finisher: false
    checkpoint_per_phase: true
    telegraph: {palette: default, min_windup_ms: 500}
    intro_cinematic: ch08.b13
    outro_cinematic: ch08.b15
    x_hp: {normal: 2400, easy: 1900, hard: 2800}
    x_post_defeat: {interact: engine_spine, hold_s: 1.5, animation: nukitsuke_draw_cut}
    barks:
      - {"on": "pattern:amort_ledger_beam", line: ch08.b14.valamort.001}
      - {"on": "pattern:amort_cleave", line: ch08.b14.valamort.002}
      - {"on": "pattern:amort_shards", line: ch08.b14.valamort.003}
      - {"on": "pattern:amort_seizure_field", line: ch08.b14.valamort.004}
      - {"on": "pattern:construct_spawn", line: ch08.b14.valamort.005}
      - {"on": "pattern:amort_final_foreclosure", line: ch08.b14.valamort.007}
    music: ch08_amort
    dialogue:
      - {"on": "boss_phase:3", lines: [ch08.b14.valamort.006], mode: bark}
      - {"on": player_died, lines: [ch08.b14.valamort.008], mode: bark, repeatable: true, cooldown_s: 0}
      - {"on": "event:muto_dori_success", lines: [ch08.b14.valamort.009], mode: bark}
      - {"on": "event:muto_dori_success", lines: [ch08.b14.nyaakoto.010], mode: ambient}
      - {"on": "event:spine_prompt", lines: [ch08.b14.nyaakoto.011], mode: ambient}
      - {"on": "event:first_foreclosure", lines: [ch08.b09.sekireisai.003], mode: ambient}
    x_pattern_tables: [amort_p1_collector, amort_p2_seizure, amort_p3_cane]
    fail: {"on": player_died, to: checkpoint}
  - id: ch08.b15
    type: cinematic
    place: pl_ledger_engine
    title_ja: "封印、消ゆ"
    title_en: "The seals go dark"
    target_s: 150
    checkpoint: true
    sequence: "/Game/Campaign/Ch08/Cinematics/LS_Ch08_B15_SealsDark"
    duration_s: 150
    skippable: true
    fallback: camera_blend
    end_state:
      player_transform: ps_festival_canal_steps
      equipped: {all: stowed}
    music: ch08_release
    subtitles:
      - {line: ch08.b15.valamort.001, at_s: 14.0}
      - {line: ch08.b15.oyuki.002, at_s: 21.0}
      - {line: ch08.b15.toranosuke.003, at_s: 30.0}
      - {line: ch08.b15.taemon.004, at_s: 56.0}
      - {line: ch08.b15.okinu.005, at_s: 72.0}
      - {line: ch08.b15.tokichi.006, at_s: 88.0}
      - {line: ch08.b15.nyaakoto.007, at_s: 128.0}
  - id: ch08.b16
    type: production_task
    task: carry
    place: pl_lantern_ward_festival
    title_ja: "生産改帳を掲げよ"
    title_en: "Post the production registry"
    target_s: 120
    checkpoint: true
    site: 2
    carry:
      item: public_registry_box
      count: 1
      pickups: [pk_registry_canal_steps]
      dropoffs: [do_kosatsu_board]
      loadout_while_carrying: []
      move_speed_mult: 0.7
      drop_on_hit: false
      post_interact: {actor: kosatsu_board, hold_s: 3.0, action: paste_pages}
    waves: []
    x_combat: false
    x_crowd: {windows_visible: 120, mac_visible: 60, path_clearance_cm: 180, no_markers: false}
    music: ch08_festival
    dialogue:
      - {"on": beat_start, lines: [ch08.b16.oyuki.001], mode: ambient}
      - {"on": "volume_enter:vol_fest_a", lines: [ch08.b16.resident.002], mode: ambient}
      - {"on": "volume_enter:vol_fest_b", lines: [ch08.b16.tokichi.003], mode: ambient}
      - {"on": "volume_enter:vol_fest_c", lines: [ch08.b16.otane.004], mode: ambient}
      - {"on": "volume_enter:vol_fest_d", lines: [ch08.b16.taemon.005], mode: ambient}
      - {"on": "volume_enter:vol_assembly", lines: [ch08.b16.tamakichi.006, ch08.b16.oyuki.007], mode: ambient}
      - {"on": "site_restored:2", lines: [ch08.b16.oyuki.008], mode: ambient}
  - id: ch08.b17
    type: dialogue
    mode: ambient
    place: pl_higashi_torii
    title_ja: "東の鳥居へ"
    title_en: "To the Eastern Torii"
    target_s: 90
    checkpoint: false
    trigger: beat_start
    interrupt: queue
    camera: soft_lookat
    x_blocking_max_s: 20
    complete: "event:plaque_rehang_done"
    music: ch08_torii_dawn
    lines:
      - ch08.b17.kohagi.001
      - ch08.b17.iota.002
      - ch08.b17.nyaakoto.003
      - ch08.b17.toranosuke.004
      - ch08.b17.nyaakoto.005
      - ch08.b17.sekireisai.006
      - ch08.b17.sekireisai.007
      - ch08.b17.nyaakoto.008
      - ch08.b17.sekireisai.009
    dialogue:
      - {"on": beat_start, lines: [ch08.b17.kohagi.001], mode: ambient}
      - {"on": "volume_enter:vol_torii", lines: [ch08.b17.iota.002], mode: ambient}
      - "on": "event:washio_sword_return"
        lines: [ch08.b17.nyaakoto.003, ch08.b17.toranosuke.004, ch08.b17.nyaakoto.005]
        mode: ambient
        requires_flag: "collectible:ch08.c03"
      - "on": "event:plaque_rehang"
        lines: [ch08.b17.sekireisai.006, ch08.b17.sekireisai.007, ch08.b17.nyaakoto.008, ch08.b17.sekireisai.009]
        mode: blocking
  - id: ch08.b18
    type: cinematic
    place: pl_higashi_torii
    title_ja: "一束"
    title_en: "One sheaf"
    target_s: 90
    checkpoint: false
    sequence: "/Game/Campaign/Ch08/Cinematics/LS_Ch08_B18_Epilogue"
    duration_s: 90
    skippable: true
    fallback: camera_blend
    end_state: {player_transform: null, equipped: null, next: credits_full}
    music: credits_main
    subtitles:
      - {line: ch08.b18.valamort.001, at_s: 40.0}
      - {line: ch08.b18.iota.002, at_s: 45.0}
      - {line: ch08.b18.taemon.003, at_s: 52.0}
collectibles:
  - id: ch08.c01
    type: collectible
    collectible_id: ch08.c01
    category: league_mark
    place: pl_collateral_cells
    mask_bit: 0
    beat_hint: ch08.b07
    codex:
      ja: "担保牢の壁に、爪で刻まれた空紋。日を数える線ではない。待つための印。"
      en: "A Sora crest scratched into a cell wall. Not a tally of days: a sign of waiting."
  - id: ch08.c02
    type: collectible
    collectible_id: ch08.c02
    category: seizure_notice
    place: pl_otemon
    mask_bit: 1
    beat_hint: ch08.b06
    codex:
      ja: "期限の利益喪失通知。本日午の刻をもって、全残高を一括請求する。"
      en: "Notice of acceleration: at noon today, every balance falls due in full."
  - id: ch08.c03
    type: collectible
    collectible_id: ch08.c03
    category: heirloom
    place: pl_ledger_spire
    mask_bit: 2
    beat_hint: ch08.b12
    sets_flag: "collectible:ch08.c03"
    codex: {ja: "鷲尾家伝来の打刀。評価札には「代物弁済」とある。", en: "The Washio house sword. Its tag reads \"payment in kind.\""}
  - id: ch08.c04
    type: collectible
    collectible_id: ch08.c04
    category: heirloom
    place: pl_ledger_spire
    mask_bit: 3
    beat_hint: ch08.b12
    codex: {ja: "玉吉の師匠の打ち上げ筒。祭りの夜にだけ火を入れた。評価額、零。", en: "Tamakichi's master's festival mortar, fired only on festival nights. Valuation: zero."}
  - id: ch08.c05
    type: collectible
    collectible_id: ch08.c05
    category: scroll_fragment
    place: pl_ledger_spire
    mask_bit: 4
    beat_hint: ch08.b12
    codex:
      ja: "活人剣とは、斬らぬ剣にあらず。斬るべき一つを、見定めた剣じゃ。"
      en: "The life-giving sword does not refuse to cut. It finds the one thing to cut."
  - id: ch08.c06
    type: collectible
    collectible_id: ch08.c06
    category: registry_page
    place: pl_lantern_ward_festival
    mask_bit: 5
    beat_hint: ch08.b16
    codex:
      ja: "提灯街の一頁。提灯四十張。三者の印と、割符の片方。"
      en: "A Lantern Ward page. Lanterns: forty. Three seals and one half of a tally."
x_pattern_tables:
  amort_p1_collector:
    selection: "deterministic: approach at 0.72 move scale until <= 740 cm; beam if distance > 340 cm or attack_index is even, else cleave (existing prototype rule)"
    attacks:
      - id: amort_ledger_beam
        color: cyan
        windup_ms: 1450
        track_ms: 550
        lock_ms: 900
        length_cm: 1500
        damage: 22
        guard: "front guard absorbs 70%"
        parry: false
        counter: "sidestep out of the locked line"
        recovery_ms: 1150
        bark_at: lock_start
      - id: amort_cleave
        color: amber
        windup_ms: 1200
        reach_cm: 330
        arc_deg: 28
        damage: 30
        guard: true
        parry: "awase within 260 ms -> 1.2 s stagger"
        recovery_ms: 1150
        bark_at: windup_start
      - id: amort_shards
        color: cyan
        count: 3
        orbit_radius_cm: 250
        orbit_period_s: 4.0
        shard_hp: 104
        intercepts: [arrows, bullets, mortar_shells]
        respawn_s: 20
        all_broken: "reconcile_stagger 3000 ms, damage taken x1.5"
        bark_at: spawn
  amort_p2_seizure:
    boss_state: "on the dais behind a seizure shield while any construct is alive; shield drops for 10 s when none are alive; uses ledger_beam (recovery 900 ms) and cleave (recovery 900 ms) while exposed"
    attacks:
      - id: amort_seizure_field
        color: amber
        windup_ms: 1500
        damage: "25 on a fall"
        tile_cm: 300
        mark_ms: 1500
        void_ms: 5000
        restore_ms: 1000
        cadence_ms: 9000
        patterns_in_order: [checker_third, ring_band_800_1200cm, tally_lines_3_through_player]
        fall: "respawn at nearest intact edge tile, 25 damage, 1 s invulnerable (no instant death)"
        bark_at: mark
      - id: construct_spawn
        adds: collateral_construct
        count: 2
        at: [phase_start, "hp_pct:55"]
        max_alive: 3
        bark_at: spawn
    adds:
      collateral_construct:
        hp: 260
        slam: {color: amber, windup_ms: 900, radius_cm: 250, damage: 25, recovery_ms: 1400}
        core: "exposed during slam recovery; seal-cut 1.0 s or 2 heavy hits"
        on_defeat: "goods settle gently to the floor (release, not destruction)"
  amort_p3_cane:
    order:
      - amort_final_foreclosure
      - amort_cane_pair
      - amort_cane_thrust
      - amort_cane_pair
      - amort_final_foreclosure
      - repeat_from_index_1
    hp_floor_pct: 1
    at_floor: "repeat amort_final_foreclosure every 4000 ms; show prompt ch08.b14.prompt.002"
    attacks:
      - id: amort_cane_pair
        color: amber
        hits: 2
        windup_ms: 500
        damage_each: 18
        guard: true
        parry: true
        recovery_ms: 700
      - id: amort_cane_thrust
        color: cyan
        windup_ms: 600
        damage: 28
        guard: "front guard absorbs 50%"
        parry: false
        counter: "marobashi (転) around the locked line, flank cut"
        recovery_ms: 900
      - id: amort_final_foreclosure
        color: amber
        windup_ms: 1000
        damage: 45
        guard: false
        parry: "blade drawn: awase -> 1.2 s stagger"
        muto_eligible: true
        muto_window_ms: {easy: 234, normal: 180, hard: 153}
        on_muto: "disarm -> defeat:capture (any HP in P3)"
        recovery_ms: 1300
        bark_at: windup_start
  difficulty:
    easy_windup_mult: 1.3
    hard_windup_mult: 0.85
    note: "bible §8; mutō-dori window scaled by the same factor (proposal)"
lines:
  - id: ch08.b01.iota.001
    speaker: clerk
    ja: "大徴収官が、期限の利益の喪失を宣言されました。"
    en: "The High Collector has declared acceleration. Every loan is called."
    register: manual_keigo
    readings: "大徴収官=だいちょうしゅうかん; 期限の利益=きげんのりえき; 喪失=そうしつ"
    duration_s: 5.0
    audio: null
  - id: ch08.b01.iota.002
    speaker: clerk
    ja: "正午までに未払いの場合、家も道具も……人も、回収です。"
    en: "If unpaid by noon, homes, tools… and people are collected."
    register: manual_keigo
    readings: "未払い=みはらい; 回収=かいしゅう"
    duration_s: 5.6
    audio: null
  - id: ch08.b01.oyuki.003
    speaker: leader
    ja: "騎馬二十一、鉄砲三十六。正午まで、あと四刻でございます。"
    en: "Twenty-one riders. Thirty-six guns. Eight hours to noon."
    register: business_keigo
    readings: "騎馬=きば; 四刻=よとき"
    duration_s: 6.1
    audio: null
  - id: ch08.b01.kohagi.004
    speaker: scout
    ja: "土手道に柵が四つ、差押機が二。門に錨が三。"
    en: "Causeway: four barricades, two walkers. Gate: three anchors."
    register: terse
    readings: "土手道=どてみち; 差押機=さしおさえき; 錨=いかり"
    duration_s: 4.9
    audio: null
  - id: ch08.b01.kozo.005
    speaker: foundry_master
    ja: "工房も田畑も、また動き始めた。"
    en: "The workshops and fields are working again."
    register: gruff_yamato
    readings: "田畑=たはた"
    duration_s: 3.1
    audio: null
  - id: ch08.b01.kozo.006
    speaker: foundry_master
    ja: "……これは、その礼や。持っていき。"
    en: "…This is our thanks. Take it."
    register: gruff_yamato
    readings: null
    duration_s: 3.0
    audio: null
  - id: ch08.b01.okinu.007
    speaker: weaver
    ja: "異星の糸を、玉鋼に巻き留めましたえ。ほどけしまへん。"
    en: "I bound the alien thread to tamahagane. It will not come loose."
    register: kyoto_soft
    readings: "異星=いせい; 玉鋼=たまはがね; 巻き留め=まきとめ"
    duration_s: 4.9
    audio: null
  - id: ch08.b01.okuzu.008
    speaker: apothecary
    ja: "こちらは、斬るより繋ぐ槍です。倒れた人に向けなさい。"
    en: "This lance mends more than it cuts. Aim it at the fallen."
    register: calm_maternal
    readings: "繋ぐ=つなぐ"
    duration_s: 4.7
    audio: null
  - id: ch08.b01.toranosuke.009
    speaker: rival
    ja: "この羽織は燃やす。……灰なら、もう数えられまい。"
    en: "This haori goes in the fire. …Ash cannot be counted."
    register: humbled_samurai
    readings: "羽織=はおり"
    duration_s: 4.4
    audio: null
  - id: ch08.b01.nyaakoto.010
    speaker: samurai
    ja: "数えました。田が三百十二枚、機が四十、提灯が千。"
    en: "I have counted. Three hundred twelve paddies, forty looms, a thousand lanterns."
    register: samurai_restrained
    readings: "機=はた; 提灯=ちょうちん"
    duration_s: 5.5
    audio: null
  - id: ch08.b01.nyaakoto.011
    speaker: samurai
    ja: "……それと、先生が、お一人。"
    en: "…And one master."
    register: samurai_restrained
    readings: null
    duration_s: 2.8
    audio: null
  - id: ch08.b01.oyuki.012
    speaker: leader
    ja: "では、参りましょう。帳尻を、合わせに。"
    en: "Then let us go and balance the books."
    register: business_keigo
    readings: "帳尻=ちょうじり"
    duration_s: 3.4
    audio: null
  - id: ch08.b02.toranosuke.001
    speaker: rival
    ja: "前は譲る。右は俺が持つ。行くぞ！"
    en: "The front is yours. I hold your right. Ride!"
    register: brash_samurai
    readings: "譲る=ゆずる"
    duration_s: 3.4
    audio: null
  - id: ch08.b02.toranosuke.002
    speaker: rival
    ja: "槍は右へ突け、弓は左だ！"
    en: "Spear to the right! Bow to the left!"
    register: brash_samurai
    readings: null
    duration_s: 2.6
    audio: null
  - id: ch08.b02.enforcer.003
    speaker: enforcer
    ja: "未登録の騎馬を確認。与信を否認します。"
    en: "Unregistered cavalry detected. Credit denied."
    register: alien_corporate_keigo
    readings: "与信=よしん; 否認=ひにん"
    duration_s: 4.4
    audio: null
  - id: ch08.b02.iota.004
    speaker: clerk
    ja: "差押機の照準線です！　あの線の上に、いてはいけません！"
    en: "The walker's aiming line! Do not stay on that line!"
    register: manual_keigo
    readings: "照準線=しょうじゅんせん"
    duration_s: 4.9
    audio: null
  - id: ch08.b02.toranosuke.005
    speaker: rival
    ja: "杭だ！　すれ違いざまに突け！"
    en: "A seal stake! Thrust as you pass!"
    register: brash_samurai
    readings: "杭=くい"
    duration_s: 2.5
    audio: null
  - id: ch08.b02.nyaakoto.006
    speaker: samurai
    ja: "栗丸、こらえよ。"
    en: "Steady, Kurimaru."
    register: samurai_restrained
    readings: "栗丸=くりまる"
    duration_s: 1.7
    audio: null
  - id: ch08.b02.enforcer.007
    speaker: enforcer
    ja: "損切りいたします。後退します。"
    en: "Cutting losses. Withdrawing."
    register: alien_corporate_keigo
    readings: "損切り=そんぎり"
    duration_s: 3.0
    audio: null
  - id: ch08.b02.toranosuke.008
    speaker: rival
    ja: "見ろ、城だ。あそこに先生がいる。"
    en: "Look—the castle. Sensei is in there."
    register: brash_samurai
    readings: null
    duration_s: 3.1
    audio: null
  - id: ch08.b02.tamakichi.009
    speaker: fireworks
    ja: "どいてや！　門、吹っ飛ばしたるで！"
    en: "Make way! I'm blowing that gate wide open!"
    register: kamigata_cheerful
    readings: null
    duration_s: 3.0
    audio: null
  - id: ch08.b02.toranosuke.010
    speaker: rival
    ja: "立て、ニャーコト！　まだ終わっておらん！"
    en: "Up, Nyaakoto! This is not finished!"
    register: brash_samurai
    readings: null
    duration_s: 3.0
    audio: null
  - id: ch08.b03.tetsugoro.001
    speaker: gunsmith
    ja: "鉄砲衆、三列！　撃ったら下がれ、込めたら出ろ！"
    en: "Gunners, three ranks! Fire, fall back. Loaded, step up!"
    register: blunt_artisan
    readings: "鉄砲衆=てっぽうしゅう; 込め=こめ"
    duration_s: 4.5
    audio: null
  - id: ch08.b03.oyuki.002
    speaker: leader
    ja: "号令は、ニャーコト殿に。的を示して『放て』と。"
    en: "The command is yours, Nyaakoto. Mark the target, then call 'Fire.'"
    register: business_keigo
    readings: "号令=ごうれい; 的=まと; 放て=はなて"
    duration_s: 4.6
    audio: null
  - id: ch08.b03.ashigaru.003
    speaker: league_ashigaru
    ja: "前の組、構え！"
    en: "Front rank, ready!"
    register: ashigaru_shout
    readings: "構え=かまえ"
    duration_s: 1.6
    audio: null
  - id: ch08.b03.nyaakoto.004
    speaker: samurai
    ja: "放て！"
    en: "Fire!"
    register: samurai_restrained
    readings: "放て=はなて"
    duration_s: 1.2
    audio: null
  - id: ch08.b03.ashigaru.005
    speaker: league_ashigaru
    ja: "下がって込めろ！　次の組、前へ！"
    en: "Fall back and load! Next rank, forward!"
    register: ashigaru_shout
    readings: "込めろ=こめろ"
    duration_s: 3.0
    audio: null
  - id: ch08.b03.oyuki.006
    speaker: leader
    ja: "一斉射ごとに、玉を数えております。"
    en: "I am counting every round, volley by volley."
    register: business_keigo
    readings: "一斉射=いっせいしゃ; 玉=たま"
    duration_s: 3.3
    audio: null
  - id: ch08.b03.enforcer.007
    speaker: enforcer
    ja: "盾列、前進。債権を保全します。"
    en: "Shield line, advance. Secure the claim."
    register: alien_corporate_keigo
    readings: "盾列=たてれつ; 債権=さいけん; 保全=ほぜん"
    duration_s: 3.5
    audio: null
  - id: ch08.b03.tamakichi.008
    speaker: fireworks
    ja: "迫撃の筒や！　落ちる所を見て撃ちや。足元はあかんで！"
    en: "Mortar! Watch where it lands. Not at your own feet!"
    register: kamigata_cheerful
    readings: "迫撃=はくげき; 筒=つつ"
    duration_s: 5.0
    audio: null
  - id: ch08.b03.oyuki.009
    speaker: leader
    ja: "外郭、確保。手負いは七名。手当てを急ぎます。"
    en: "Outer bailey secured. Seven wounded. We treat them now."
    register: business_keigo
    readings: "外郭=がいかく; 手負い=ておい"
    duration_s: 5.0
    audio: null
  - id: ch08.b04.kozo.001
    speaker: foundry_master
    ja: "火床が熾った。鍬も鋸も、ここで直す。"
    en: "The fire's up. Hoes, saws—we mend them here."
    register: gruff_yamato
    readings: "火床=ほど; 熾った=おこった; 鍬=くわ; 鋸=のこぎり"
    duration_s: 3.6
    audio: null
  - id: ch08.b04.okuzu.002
    speaker: apothecary
    ja: "手負いはこちらへ。急がず、止まらず。"
    en: "Wounded, this way. Don't rush. Don't stop."
    register: calm_maternal
    readings: "手負い=ておい"
    duration_s: 3.4
    audio: null
  - id: ch08.b04.kohagi.003
    speaker: scout
    ja: "擲弾兵、二。北西、塀の上。"
    en: "Two grenadiers. Northwest, on the wall."
    register: terse
    readings: "擲弾兵=てきだんへい; 塀=へい"
    duration_s: 3.3
    audio: null
  - id: ch08.b04.enforcer.004
    speaker: enforcer
    ja: "設備の差押えを執行します。"
    en: "Executing seizure of equipment."
    register: alien_corporate_keigo
    readings: "差押え=さしおさえ; 執行=しっこう"
    duration_s: 2.9
    audio: null
  - id: ch08.b04.kozo.005
    speaker: foundry_master
    ja: "網や！　金床にかかった、切れ！"
    en: "A net! On the anvil—cut it!"
    register: gruff_yamato
    readings: "金床=かなとこ"
    duration_s: 2.8
    audio: null
  - id: ch08.b04.conscript.006
    speaker: conscript
    ja: "すまん……体が、勝手に……！"
    en: "Sorry… my body won't stop…!"
    register: yamato_rural_distressed
    readings: null
    duration_s: 2.6
    audio: null
  - id: ch08.b04.kozo.007
    speaker: foundry_master
    ja: "……直った。三十六や。"
    en: "…Mended. Thirty-six."
    register: gruff_yamato
    readings: null
    duration_s: 2.5
    audio: null
  - id: ch08.b05.okuzu.001
    speaker: apothecary
    ja: "兵糧と早合を、三つの組へ。生きて届けなさい。"
    en: "Rations and cartridges to three squads. Arrive alive."
    register: calm_maternal
    readings: "兵糧=ひょうろう; 早合=はやごう"
    duration_s: 4.5
    audio: null
  - id: ch08.b05.kohagi.002
    speaker: scout
    ja: "櫓に狙い手、二。光ったら、伏せて。"
    en: "Two marksmen in the turret. If it glints, get down."
    register: terse
    readings: "櫓=やぐら; 狙い手=ねらいて"
    duration_s: 3.6
    audio: null
  - id: ch08.b05.enforcer.003
    speaker: enforcer
    ja: "照準、確定。"
    en: "Aim locked."
    register: alien_corporate_keigo
    readings: "照準=しょうじゅん"
    duration_s: 1.7
    audio: null
  - id: ch08.b05.ashigaru.004
    speaker: league_ashigaru
    ja: "来てくれたか！　玉が尽きかけとった。"
    en: "You came! We were nearly out."
    register: ashigaru_shout
    readings: "尽き=つき"
    duration_s: 3.1
    audio: null
  - id: ch08.b05.ashigaru.005
    speaker: league_ashigaru
    ja: "握り飯や……ありがたい。"
    en: "Rice balls… Bless you."
    register: ashigaru_shout
    readings: "握り飯=にぎりめし"
    duration_s: 2.2
    audio: null
  - id: ch08.b05.oyuki.006
    speaker: leader
    ja: "兵糧三十六食、届きました。"
    en: "Thirty-six rations, delivered."
    register: business_keigo
    readings: "三十六食=さんじゅうろくしょく"
    duration_s: 3.0
    audio: null
  - id: ch08.b06.kozo.001
    speaker: foundry_master
    ja: "門を割るなら、これや。振りかぶったら、迷うな。"
    en: "For breaking gates, this. Once it's up, don't hesitate."
    register: gruff_yamato
    readings: "割る=わる"
    duration_s: 4.1
    audio: null
  - id: ch08.b06.toranosuke.002
    speaker: rival
    ja: "枡形だ。三方から撃たれる。止まるな！"
    en: "A masugata. Fire from three sides. Keep moving!"
    register: brash_samurai
    readings: "枡形=ますがた"
    duration_s: 3.7
    audio: null
  - id: ch08.b06.kohagi.003
    speaker: scout
    ja: "錨は三。左の柱、右の柱、雁木の上。"
    en: "Three anchors. Left post, right post, top of the steps."
    register: terse
    readings: "錨=いかり; 雁木=がんぎ"
    duration_s: 3.9
    audio: null
  - id: ch08.b06.enforcer.004
    speaker: enforcer
    ja: "侵入者、枡形内。十字射撃を開始します。"
    en: "Intruders in the masugata. Commencing crossfire."
    register: alien_corporate_keigo
    readings: "十字射撃=じゅうじしゃげき"
    duration_s: 4.6
    audio: null
  - id: ch08.b06.iota.005
    speaker: clerk
    ja: "錨は三つとも、独立採算でございます。一つずつ、お願いいたします。"
    en: "Each anchor is accounted separately. One at a time, please."
    register: manual_keigo
    readings: "独立採算=どくりつさいさん"
    duration_s: 5.8
    audio: null
  - id: ch08.b06.enforcer.006
    speaker: enforcer
    ja: "第二錨、毀損。損害を計上します。"
    en: "Anchor two damaged. Loss recorded."
    register: alien_corporate_keigo
    readings: "毀損=きそん; 計上=けいじょう"
    duration_s: 3.8
    audio: null
  - id: ch08.b06.enforcer.007
    speaker: enforcer
    ja: "門の維持は、不採算です。撤収。"
    en: "Holding the gate is unprofitable. Withdraw."
    register: alien_corporate_keigo
    readings: "不採算=ふさいさん; 撤収=てっしゅう"
    duration_s: 3.5
    audio: null
  - id: ch08.b06.ashigaru.008
    speaker: league_ashigaru
    ja: "大手門、開いたぞぉ！"
    en: "The main gate is open!"
    register: ashigaru_shout
    readings: "大手門=おおてもん"
    duration_s: 2.0
    audio: null
  - id: ch08.b07.kohagi.001
    speaker: scout
    ja: "蔵が四つ。中の人に、札が付いてる。"
    en: "Four storehouses. The people inside are tagged."
    register: terse
    readings: "札=ふだ"
    duration_s: 3.5
    audio: null
  - id: ch08.b07.villager.002
    speaker: villager
    ja: "……外か？　本当に、外なのか？"
    en: "…Outside? Truly outside?"
    register: yamato_rural_weak
    readings: null
    duration_s: 2.8
    audio: null
  - id: ch08.b07.nyaakoto.003
    speaker: samurai
    ja: "猫柳生の者だ。門まで、私が守る。"
    en: "I am of Nyaagyu. I will guard you to the gate."
    register: samurai_restrained
    readings: "猫柳生=ニャーギュウ"
    duration_s: 3.5
    audio: null
  - id: ch08.b07.child.004
    speaker: child
    ja: "空の紋だ！　お侍さま、空の紋だよ！"
    en: "The sky crest! Look, sir—the sky crest!"
    register: child
    readings: "紋=もん; 侍=さむらい"
    duration_s: 3.2
    audio: null
  - id: ch08.b07.takemaru.005
    speaker: pupil_takemaru
    ja: "ニャーコト殿！　先生は、一番奥の蔵に……！"
    en: "Nyaakoto! Sensei is in the last storehouse…!"
    register: young_samurai
    readings: null
    duration_s: 3.9
    audio: null
  - id: ch08.b07.nyaakoto.006
    speaker: samurai
    ja: "伏せて。合図まで、動くな。"
    en: "Get down. Do not move until I signal."
    register: samurai_restrained
    readings: "合図=あいず"
    duration_s: 2.7
    audio: null
  - id: ch08.b07.taemon.007
    speaker: farmer
    ja: "下村の衆や……よう生きとった。"
    en: "Lower-village folk… You're alive."
    register: yamato_elder
    readings: "下村=しもむら; 衆=しゅう"
    duration_s: 2.9
    audio: null
  - id: ch08.b07.oyuki.008
    speaker: leader
    ja: "避難所を開きました。十二名、全員です。"
    en: "The refuge is open. Twelve people. All of them."
    register: business_keigo
    readings: "避難所=ひなんじょ"
    duration_s: 4.2
    audio: null
  - id: ch08.b07.takemaru.009
    speaker: pupil_takemaru
    ja: "一番奥です。……お一人で、行ってください。"
    en: "The very last one. …Go alone."
    register: young_samurai
    readings: null
    duration_s: 4.1
    audio: null
  - id: ch08.b08.nyaakoto.001
    speaker: samurai
    ja: "先生。"
    en: Sensei.
    register: samurai_restrained
    readings: null
    duration_s: 1.2
    audio: null
  - id: ch08.b08.sekireisai.002
    speaker: mentor
    ja: "遅かったのう。"
    en: "You came late."
    register: archaic_samurai
    readings: null
    duration_s: 1.4
    audio: null
  - id: ch08.b08.nyaakoto.003
    speaker: samurai
    ja: "……申し訳ございません。"
    en: "…Forgive me."
    register: samurai_restrained
    readings: null
    duration_s: 2.2
    audio: null
  - id: ch08.b08.sekireisai.004
    speaker: mentor
    ja: "よい。道草も修行のうちじゃ。"
    en: "No matter. Detours are training too."
    register: archaic_samurai
    readings: "道草=みちくさ; 修行=しゅぎょう"
    duration_s: 2.7
    audio: null
  - id: ch08.b08.sekireisai.005
    speaker: mentor
    ja: "して、何を数えてきた。"
    en: "So. What have you counted?"
    register: archaic_samurai
    readings: null
    duration_s: 2.1
    audio: null
  - id: ch08.b08.nyaakoto.006
    speaker: samurai
    ja: "守るものを。田と、炉と、灯と……人を。"
    en: "What we protect. Fields, forges, lamps… and people."
    register: samurai_restrained
    readings: "炉=ろ; 灯=あかり"
    duration_s: 3.7
    audio: null
  - id: ch08.b08.sekireisai.007
    speaker: mentor
    ja: "虎之介。"
    en: Toranosuke.
    register: archaic_samurai
    readings: "虎之介=とらのすけ"
    duration_s: 1.2
    audio: null
  - id: ch08.b08.toranosuke.008
    speaker: rival
    ja: "……合わせる顔が、ございません。"
    en: "…I cannot face you."
    register: humbled_samurai
    readings: null
    duration_s: 2.8
    audio: null
  - id: ch08.b08.sekireisai.009
    speaker: mentor
    ja: "顔はそこにある。上げよ。"
    en: "Your face is right there. Raise it."
    register: archaic_samurai
    readings: null
    duration_s: 2.5
    audio: null
  - id: ch08.b09.nyaakoto.001
    speaker: samurai
    ja: "先生、せめてこれを。"
    en: "Sensei, at least take this."
    register: samurai_restrained
    readings: null
    duration_s: 2.0
    audio: null
  - id: ch08.b09.sekireisai.002
    speaker: mentor
    ja: "要らぬ。民の前に立つには、手が空いておるほうがよい。"
    en: "No need. To stand before the people, empty hands are better."
    register: archaic_samurai
    readings: "要らぬ=いらぬ; 民=たみ"
    duration_s: 4.7
    audio: null
  - id: ch08.b09.sekireisai.003
    speaker: mentor
    ja: "上の者は、最後に大きく振りかぶる。その時、刀は鞘の内に置け。"
    en: "At the end, he will raise his blade high. Then keep yours in its sheath."
    register: archaic_samurai
    readings: "鞘=さや"
    duration_s: 5.9
    audio: null
  - id: ch08.b09.nyaakoto.004
    speaker: samurai
    ja: "無刀取りは……一人で覚えました。"
    en: "Mutō-dori… I learned it alone."
    register: samurai_restrained
    readings: "無刀取り=むとうどり"
    duration_s: 3.3
    audio: null
  - id: ch08.b09.sekireisai.005
    speaker: mentor
    ja: "一人で覚えたなら、本物じゃ。行け。"
    en: "If you learned it alone, it is real. Go."
    register: archaic_samurai
    readings: "本物=ほんもの"
    duration_s: 3.4
    audio: null
  - id: ch08.b10.kohagi.001
    speaker: scout
    ja: "上に四。橋の向こうに、狙い手が一。"
    en: "Four above. One marksman across the bridge."
    register: terse
    readings: "狙い手=ねらいて"
    duration_s: 3.6
    audio: null
  - id: ch08.b10.enforcer.002
    speaker: enforcer
    ja: "帳簿塔への無断立入りを検知。"
    en: "Unauthorized entry to the Ledger Spire detected."
    register: alien_corporate_keigo
    readings: "帳簿塔=ちょうぼとう; 無断立入り=むだんたちいり; 検知=けんち"
    duration_s: 3.4
    audio: null
  - id: ch08.b10.enforcer.003
    speaker: enforcer
    ja: "対象を見失いました。直近の取引を照会します。"
    en: "Target lost. Querying recent transactions."
    register: alien_corporate_keigo
    readings: "直近=ちょっきん; 照会=しょうかい"
    duration_s: 4.7
    audio: null
  - id: ch08.b10.toranosuke.004
    speaker: rival
    ja: "吹き抜けに落ちるなよ。拾いには行けん。"
    en: "Do not fall into the shaft. I cannot fetch you."
    register: brash_samurai
    readings: "吹き抜け=ふきぬけ"
    duration_s: 3.6
    audio: null
  - id: ch08.b10.iota.005
    speaker: clerk
    ja: "この塔は、一階ごとに、債務の桁が一つ上がります。"
    en: "Each floor of this tower adds a digit to the debt."
    register: manual_keigo
    readings: "桁=けた"
    duration_s: 4.6
    audio: null
  - id: ch08.b10.tetsugoro.006
    speaker: gunsmith
    ja: "あの吊り台は止まっとる。轆轤を噛ませる、時間くれ。"
    en: "The lift's dead. I'll rig a capstan. Buy me time."
    register: blunt_artisan
    readings: "吊り台=つりだい; 轆轤=ろくろ; 噛ませる=かませる"
    duration_s: 4.9
    audio: null
  - id: ch08.b10.enforcer.007
    speaker: enforcer
    ja: "損失が許容範囲を超過。上層へ移管します。"
    en: "Losses exceed tolerance. Transferring upstairs."
    register: alien_corporate_keigo
    readings: "許容範囲=きょようはんい; 超過=ちょうか; 移管=いかん"
    duration_s: 4.7
    audio: null
  - id: ch08.b11.tetsugoro.001
    speaker: gunsmith
    ja: "押して回せ。速すぎりゃ綱が焼ける、遅けりゃ下がる。"
    en: "Push it round. Too fast burns the rope. Too slow, we sink."
    register: blunt_artisan
    readings: "綱=つな"
    duration_s: 4.5
    audio: null
  - id: ch08.b11.ashigaru.002
    speaker: league_ashigaru
    ja: "せーの！"
    en: "Heave!"
    register: ashigaru_shout
    readings: null
    duration_s: 1.2
    audio: null
  - id: ch08.b11.kohagi.003
    speaker: scout
    ja: "上の橋から、目録が三。"
    en: "Three drones, off the upper bridge."
    register: terse
    readings: "目録=もくろく"
    duration_s: 2.5
    audio: null
  - id: ch08.b11.tetsugoro.004
    speaker: gunsmith
    ja: "おれらだけじゃ遅い！　早う戻れ！"
    en: "Too slow without you! Get back here!"
    register: blunt_artisan
    readings: null
    duration_s: 2.6
    audio: null
  - id: ch08.b11.enforcer.005
    speaker: enforcer
    ja: "昇降機の無断使用。料金を請求します。"
    en: "Unauthorized use of the lift. You will be charged."
    register: alien_corporate_keigo
    readings: "昇降機=しょうこうき; 請求=せいきゅう"
    duration_s: 4.3
    audio: null
  - id: ch08.b11.iota.006
    speaker: clerk
    ja: "頂上の機関が、正午の一括請求を準備中でございます。"
    en: "The summit engine is preparing the noon collection."
    register: manual_keigo
    readings: "機関=きかん; 一括請求=いっかつせいきゅう"
    duration_s: 5.4
    audio: null
  - id: ch08.b11.toranosuke.007
    speaker: rival
    ja: "ここから先は、お前一人だ。下は俺たちが守る。"
    en: "From here, you go alone. We hold below."
    register: humbled_samurai
    readings: null
    duration_s: 4.3
    audio: null
  - id: ch08.b12.iota.001
    speaker: clerk
    ja: "押収品の陳列室でございます。どれにも、評価額が。"
    en: "The seized-goods gallery. Every item has a valuation."
    register: manual_keigo
    readings: "押収品=おうしゅうひん; 陳列室=ちんれつしつ; 評価額=ひょうかがく"
    duration_s: 4.9
    audio: null
  - id: ch08.b12.nyaakoto.002
    speaker: samurai
    ja: "……子どもの張子に、三文か。"
    en: "…A child's paper toy. Three coppers."
    register: samurai_restrained
    readings: "張子=はりこ; 三文=さんもん"
    duration_s: 2.9
    audio: null
  - id: ch08.b12.nyaakoto.003
    speaker: samurai
    ja: "鷲尾家の刀……虎之介に、返さねば。"
    en: "The Washio sword… This goes back to Toranosuke."
    register: samurai_restrained
    readings: "鷲尾家=わしおけ"
    duration_s: 3.7
    audio: null
  - id: ch08.b12.sekireisai.004
    speaker: mentor
    ja: "活人剣とは、斬らぬ剣にあらず。斬るべき一つを、見定めた剣じゃ。"
    en: "The life-giving sword does not refuse to cut. It finds the one thing to cut."
    register: archaic_samurai
    readings: "活人剣=かつにんけん; 見定めた=みさだめた"
    duration_s: 5.8
    audio: null
  - id: ch08.b12.iota.005
    speaker: clerk
    ja: "上へは、北の階段でございます。"
    en: "The way up is the north stair."
    register: manual_keigo
    readings: null
    duration_s: 2.9
    audio: null
  - id: ch08.b13.valamort.001
    speaker: banker
    ja: "ようこそ、債務者番号七〇三一。お掛けください。"
    en: "Welcome, debtor seven-zero-three-one. Please, be seated."
    register: alien_corporate_keigo
    readings: "債務者番号=さいむしゃばんごう; 七〇三一=ななまるさんいち"
    duration_s: 4.9
    audio: null
  - id: ch08.b13.valamort.002
    speaker: banker
    ja: "ご提案です。返済条件の変更——金利は据え置き、期間は永久。"
    en: "A proposal. Restructured terms: the rate unchanged, the term perpetual."
    register: alien_corporate_keigo
    readings: "返済=へんさい; 据え置き=すえおき; 永久=えいきゅう"
    duration_s: 6.4
    audio: null
  - id: ch08.b13.nyaakoto.003
    speaker: samurai
    ja: "……永久。"
    en: "…Perpetual."
    register: samurai_restrained
    readings: "永久=えいきゅう"
    duration_s: 1.3
    audio: null
  - id: ch08.b13.valamort.004
    speaker: banker
    ja: "最後の帳簿は私が守る。街の未来まで担保に取ろう。"
    en: "I guard the final ledger. Even this city's future is collateral."
    register: alien_corporate_plain
    readings: "担保=たんぽ"
    duration_s: 5.2
    audio: null
  - id: ch08.b13.valamort.005
    speaker: banker
    ja: "署名を。硯は用意してございます。……貴殿の師のものですが。"
    en: "Your signature. An inkstone is provided. It was your master's."
    register: alien_corporate_keigo
    readings: "署名=しょめい; 硯=すずり; 貴殿=きでん"
    duration_s: 5.5
    audio: null
  - id: ch08.b13.valamort.006
    speaker: banker
    ja: "……備品の毀損として、計上いたします。"
    en: "…Recorded as damage to fixtures."
    register: alien_corporate_keigo
    readings: "備品=びひん; 毀損=きそん; 計上=けいじょう"
    duration_s: 3.7
    audio: null
  - id: ch08.b13.nyaakoto.007
    speaker: samurai
    ja: "記せ。それが、お前の最後の一行だ。"
    en: "Write it down. It is your last line."
    register: samurai_restrained
    readings: "記せ=しるせ; 一行=いちぎょう"
    duration_s: 3.5
    audio: null
  - id: ch08.b13.valamort.008
    speaker: banker
    ja: "交渉は決裂。元本を、回収いたします。"
    en: "Negotiations have failed. The principal will be recovered."
    register: alien_corporate_keigo
    readings: "交渉=こうしょう; 決裂=けつれつ; 元本=がんぽん"
    duration_s: 4.1
    audio: null
  - id: ch08.b14.valamort.001
    speaker: banker
    ja: "元本、回収。"
    en: "Recovering the principal."
    register: alien_corporate_keigo
    readings: "元本=がんぽん"
    duration_s: 1.9
    audio: null
  - id: ch08.b14.valamort.002
    speaker: banker
    ja: "償却。"
    en: Write-off.
    register: alien_corporate_keigo
    readings: "償却=しょうきゃく"
    duration_s: 1.2
    audio: null
  - id: ch08.b14.valamort.003
    speaker: banker
    ja: "残高照会。"
    en: "Balance inquiry."
    register: alien_corporate_keigo
    readings: "残高照会=ざんだかしょうかい"
    duration_s: 1.5
    audio: null
  - id: ch08.b14.valamort.004
    speaker: banker
    ja: "差押えを執行いたします。"
    en: "Executing seizure."
    register: alien_corporate_keigo
    readings: "差押え=さしおさえ; 執行=しっこう"
    duration_s: 2.5
    audio: null
  - id: ch08.b14.valamort.005
    speaker: banker
    ja: "担保物件、稼働。"
    en: "Collateral assets: activate."
    register: alien_corporate_keigo
    readings: "担保物件=たんぽぶっけん; 稼働=かどう"
    duration_s: 2.2
    audio: null
  - id: ch08.b14.valamort.006
    speaker: banker
    ja: "剣は非効率です。ですが、確実です。"
    en: "The sword is inefficient. But it is certain."
    register: alien_corporate_keigo
    readings: "非効率=ひこうりつ; 確実=かくじつ"
    duration_s: 3.5
    audio: null
  - id: ch08.b14.valamort.007
    speaker: banker
    ja: "最終、抵当権実行。"
    en: "Final foreclosure."
    register: alien_corporate_keigo
    readings: "抵当権=ていとうけん; 実行=じっこう"
    duration_s: 2.5
    audio: null
  - id: ch08.b14.valamort.008
    speaker: banker
    ja: "延滞として、処理いたします。"
    en: "Processed as delinquent."
    register: alien_corporate_keigo
    readings: "延滞=えんたい; 処理=しょり"
    duration_s: 2.7
    audio: null
  - id: ch08.b14.valamort.009
    speaker: banker
    ja: "……計算に、ありません。"
    en: "…This is not in the calculation."
    register: alien_corporate_keigo
    readings: null
    duration_s: 2.3
    audio: null
  - id: ch08.b14.nyaakoto.010
    speaker: samurai
    ja: "お前は、無いものを数えた。"
    en: "You counted what did not exist."
    register: samurai_restrained
    readings: null
    duration_s: 2.5
    audio: null
  - id: ch08.b14.nyaakoto.011
    speaker: samurai
    ja: "一太刀で、足りる。"
    en: "One cut is enough."
    register: samurai_restrained
    readings: "一太刀=ひとたち"
    duration_s: 2.1
    audio: null
  - id: ch08.b15.valamort.001
    speaker: banker
    ja: "帳簿なくして、この谷に秩序はございません。"
    en: "Without the ledger, this valley has no order."
    register: alien_corporate_keigo
    readings: "秩序=ちつじょ"
    duration_s: 3.8
    audio: null
  - id: ch08.b15.oyuki.002
    speaker: leader
    ja: "帳簿なら、ございます。わたくしどもの帳簿が。"
    en: "There is a ledger. Ours."
    register: business_keigo
    readings: null
    duration_s: 3.9
    audio: null
  - id: ch08.b15.toranosuke.003
    speaker: rival
    ja: "縄目の恥とは言わせん。生きて、数えろ。"
    en: "This rope is no disgrace. Live. And count."
    register: humbled_samurai
    readings: "縄目=なわめ; 恥=はじ"
    duration_s: 3.8
    audio: null
  - id: ch08.b15.taemon.004
    speaker: farmer
    ja: "……封が、消えよった。"
    en: "…The seal. It's gone dark."
    register: yamato_elder
    readings: "封=ふう"
    duration_s: 2.1
    audio: null
  - id: ch08.b15.okinu.005
    speaker: weaver
    ja: "取り立ての目盛りが、消えましたえ。"
    en: "The levy gauges have gone dark."
    register: kyoto_soft
    readings: "取り立て=とりたて; 目盛り=めもり"
    duration_s: 3.3
    audio: null
  - id: ch08.b15.tokichi.006
    speaker: lantern_maker
    ja: "戸の数字が……消えた。"
    en: "The numbers on the doors… gone."
    register: gentle_artisan
    readings: "戸=と"
    duration_s: 2.4
    audio: null
  - id: ch08.b15.nyaakoto.007
    speaker: samurai
    ja: "あとはこの街だ。誰も借りに縛られぬように。"
    en: "Only this ward remains. No one will be bound by debt again."
    register: samurai_restrained
    readings: "縛られぬ=しばられぬ"
    duration_s: 4.1
    audio: null
  - id: ch08.b16.oyuki.001
    speaker: leader
    ja: "改帳を集会所へ。皆の前で、貼り出します。"
    en: "Take the registry to the assembly. We post it before everyone."
    register: business_keigo
    readings: "改帳=かいちょう; 集会所=しゅうかいじょ"
    duration_s: 4.3
    audio: null
  - id: ch08.b16.resident.002
    speaker: resident
    ja: "うちの鍋、戻ってきたんよ。差押えの札付きで。"
    en: "Our pot came back. Seizure tag and all."
    register: kamigata_townsfolk
    readings: "差押え=さしおさえ; 札=ふだ"
    duration_s: 4.2
    audio: null
  - id: ch08.b16.tokichi.003
    speaker: lantern_maker
    ja: "千張り、灯しました。一つも、借りた灯ではございません。"
    en: "A thousand lanterns lit. Not one of them borrowed."
    register: gentle_artisan
    readings: "千張り=せんはり; 灯し=ともし; 灯=ひ"
    duration_s: 4.9
    audio: null
  - id: ch08.b16.otane.004
    speaker: farmer_young
    ja: "新米や！　今年は全部、うちらの米やで！"
    en: "New rice! This year, every grain is ours!"
    register: kamigata_bright
    readings: "新米=しんまい"
    duration_s: 3.7
    audio: null
  - id: ch08.b16.taemon.005
    speaker: farmer
    ja: "紙は紙や、言うたけどな。この紙は、ええ紙や。"
    en: "I said paper is paper. But this is good paper."
    register: yamato_elder
    readings: null
    duration_s: 4.1
    audio: null
  - id: ch08.b16.tamakichi.006
    speaker: fireworks
    ja: "花火、上げてもええか？"
    en: "Can I set off the fireworks now?"
    register: kamigata_cheerful
    readings: "花火=はなび"
    duration_s: 2.3
    audio: null
  - id: ch08.b16.oyuki.007
    speaker: leader
    ja: "帳面に載せてからです。"
    en: "Once they are in the ledger."
    register: business_keigo
    readings: "帳面=ちょうめん"
    duration_s: 2.2
    audio: null
  - id: ch08.b16.oyuki.008
    speaker: leader
    ja: "生産改帳、ここに掲げます。明日からの帳は、皆さまの手で。"
    en: "The production registry is posted. From tomorrow, you keep the books."
    register: business_keigo
    readings: "生産改帳=せいさんかいちょう; 掲げ=かかげ; 帳=ちょう"
    duration_s: 5.5
    audio: null
  - id: ch08.b17.kohagi.001
    speaker: scout
    ja: "東の鳥居で待つ。皆で新しい朝を迎えよう。"
    en: "We will wait at the eastern torii. Let us greet a new morning together."
    register: terse
    readings: "鳥居=とりい"
    duration_s: 4.9
    audio: null
  - id: ch08.b17.iota.002
    speaker: clerk
    ja: "朝というものは……無償で来るのですね。"
    en: "So morning… comes free of charge."
    register: manual_keigo
    readings: "無償=むしょう"
    duration_s: 3.4
    audio: null
  - id: ch08.b17.nyaakoto.003
    speaker: samurai
    ja: "鷲尾の刀だ。上で見つけた。"
    en: "Your house's sword. I found it up there."
    register: samurai_plain
    readings: "鷲尾=わしお"
    duration_s: 2.9
    audio: null
  - id: ch08.b17.toranosuke.004
    speaker: rival
    ja: "……借りが、できたな。"
    en: "…Now I owe you."
    register: humbled_samurai
    readings: "借り=かり"
    duration_s: 2.0
    audio: null
  - id: ch08.b17.nyaakoto.005
    speaker: samurai
    ja: "貸しではない。"
    en: "It is not a loan."
    register: samurai_plain
    readings: "貸し=かし"
    duration_s: 1.4
    audio: null
  - id: ch08.b17.sekireisai.006
    speaker: mentor
    ja: "虎之介の札は、ここじゃ。"
    en: "Toranosuke's plaque goes here."
    register: archaic_samurai
    readings: "札=ふだ"
    duration_s: 2.3
    audio: null
  - id: ch08.b17.sekireisai.007
    speaker: mentor
    ja: "ニャーコト。おぬしの札は……ここじゃな。"
    en: "Nyaakoto. Yours goes… here."
    register: archaic_samurai
    readings: null
    duration_s: 3.0
    audio: null
  - id: ch08.b17.nyaakoto.008
    speaker: samurai
    ja: "剣は、作る手を守るためにある。"
    en: "The sword exists to protect the hands that make."
    register: samurai_restrained
    readings: "剣=けん"
    duration_s: 3.4
    audio: null
  - id: ch08.b17.sekireisai.009
    speaker: mentor
    ja: "……ようやく、一本じゃ。"
    en: "…At last, a point."
    register: archaic_samurai
    readings: "一本=いっぽん"
    duration_s: 2.1
    audio: null
  - id: ch08.b18.valamort.001
    speaker: banker
    ja: "……一束。"
    en: "…One sheaf."
    register: alien_corporate_keigo
    readings: "一束=ひとたば"
    duration_s: 1.3
    audio: null
  - id: ch08.b18.iota.002
    speaker: clerk
    ja: "はい。一束、確かに在ります。"
    en: "Yes. One sheaf. It truly exists."
    register: manual_keigo
    readings: "在ります=あります"
    duration_s: 2.9
    audio: null
  - id: ch08.b18.taemon.003
    speaker: farmer
    ja: "数え終わったら、蒔きに行くで。麦は秋に蒔くんや。"
    en: "Done counting? Then we sow. Barley goes in come autumn."
    register: yamato_elder
    readings: "蒔き=まき"
    duration_s: 4.6
    audio: null
ui_prompts:
  - id: ch08.b01.prompt.001
    beat: ch08.b01
    "on": beat_complete
    ja: "新たな武具：単分子薙刀・治癒の槍"
    en: "New arms: Monofilament Naginata, Healing Lance"
  - id: ch08.b02.prompt.001
    beat: ch08.b02
    "on": beat_start
    ja: "馬上の槍：前と右へ突く"
    en: "Mounted yari: thrust forward and to the right"
  - id: ch08.b02.prompt.002
    beat: ch08.b02
    "on": "progress_at:0.05"
    ja: "馬上の弓：左側にだけ射てる"
    en: "Mounted yumi: you can shoot to the left only"
  - id: ch08.b02.prompt.003
    beat: ch08.b02
    "on": "pattern:walker_sweep_beam"
    ja: "手綱を引くと速度が落ちる"
    en: "Pull the reins to slow down"
  - id: ch08.b03.prompt.001
    beat: ch08.b03
    "on": "event:volley_tutorial"
    ja: "{Ability}長押しで的を示し、離すと斉射"
    en: "Hold {Ability} to mark a target, release to fire a volley"
  - id: ch08.b03.prompt.002
    beat: ch08.b03
    "on": "event:wave_start_3"
    ja: "迫撃砲：弧の落下点を見て撃つ"
    en: "Micro-Mortar: check where the arc lands"
  - id: ch08.b06.prompt.001
    beat: ch08.b06
    "on": beat_start
    ja: "金棒：攻撃を押し続けると振り下ろす"
    en: "Kanabō: keep holding attack to bring it down"
  - id: ch08.b07.prompt.001
    beat: ch08.b07
    "on": beat_start
    ja: "{Ability}で合図：民を伏せさせる／進ませる"
    en: "{Ability}: signal the people to hide or to move"
  - id: ch08.b07.prompt.002
    beat: ch08.b07
    "on": "npc_downed:any"
    ja: "治癒の槍：倒れた味方を撃つと早く起きる"
    en: "Healing Lance: shoot a downed ally to revive faster"
  - {id: ch08.b11.prompt.001, beat: ch08.b11, "on": beat_start, ja: "轆轤：同じ速さで回し続ける", en: "Capstan: keep turning at a steady pace"}
  - id: ch08.b14.prompt.001
    beat: ch08.b14
    "on": "boss_phase:2"
    ja: "琥珀の縁の床は、まもなく消える"
    en: "Amber-edged tiles are about to fall away"
  - id: ch08.b14.prompt.002
    beat: ch08.b14
    "on": "event:first_foreclosure"
    ja: "納刀して待ち、振り下ろしを無刀取り"
    en: "Sheathe, wait, then take the overhead: mutō-dori"
  - {id: ch08.b14.prompt.003, beat: ch08.b14, "on": "event:spine_prompt", ja: "機関の背骨を断て", en: "Cut the engine's spine"}
  - {id: ch08.b16.prompt.001, beat: ch08.b16, "on": beat_start, ja: "改帳を高札場まで運ぶ", en: "Carry the registry to the notice board"}
```
