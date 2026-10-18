# 第六章 債務金庫への潜入: Ledger-Vault Infiltration (`ch06_ledger_vault`)

> **Monetary boundary (bible §2).** In this chapter, as in the whole campaign, SORA XOR (and the registry that leads to it) is a production-only storytelling premise. XOR is cut only against finished, inspected goods, is never shown as a balance or converted, and has no link to multiplayer XOR bonds, NFTs, wallets or IrohaConnect. It makes no claim about real-world money, investment or policy, and it does not describe the real SORA network or the design in the SORA Nexus article. **Review note (C1 lead, 2026-09-25):** names, calendar, speaker ids, Japanese punctuation and YAML field names in this file follow bible §9.1, §12.5 and §18.

**Status:** production design and script for chapter 6. It follows the [story bible](story-bible.md), especially §3 (mutō-dori), §8 (`boss_eskro` and the second Toranosuke duel), §12 (beat taxonomy) and §13 (ch06 outline). All numbers here are **proposals** for their owners to ratify: L1 for beats, layouts and saves; L2 for stealth and enemies; L3 for Eskro's and Toranosuke's pattern tables; L4 for HUD prompts; L5 for music and barks; C3 for the vault and palace kits; C9 for the cinematics. Still pending: native Japanese review (B7), historian and practitioner review of the swordwork and castle details, and playtest timing. Nothing in this file edits `catalog.json`.

**Related:** [story bible](story-bible.md) · [catalog.json](../../Content/Data/catalog.json) (ch06 sites and anchor lines) · [historical arms](../historical-arms.md) · [SORA kamon runtime art](../sora-kamon-runtime-art.md) · [photoreal acceptance](../art-direction/photoreal-acceptance.md)

---

## 0. At a glance

| | |
|---|---|
| Chapter | 6 of 8, Act III (exposure and liberation) |
| Target time | **55 min (3,300 s)** on Normal (真剣), including about 12% retries. Allowed ±20% in telemetry. |
| Beats | **16** sequenced beats (b07 optional) plus 6 passive collectibles |
| Mix (min) | Combat, duel and boss 14 · explore 3 · **stealth 24** · production 4 · mounted 0 · cinematic and dialogue 10. This matches bible §10 exactly. |
| Dialogue | **143 lines**: 116 scripted and ambient lines plus 27 repeatable barks and captioned telegraphs, about 8.2 min of speech. Bible §10 budgets 110, so this runs 33 over, mostly because of the barks this brief asks for. L5 should decide whether barks count toward the campaign's 890. |
| Boss | `boss_eskro` (b13), the blind sound-hunter. **Duel:** Washio Toranosuke with real steel (b09). |
| New mechanics | Full stealth AI states (unaware, suspicious, alert, search); swimming and dives (8 s); authored wall climb; rotating-scan sweep gaps; 礫 tsubute lures; nightingale floor with a silent edge strip; carried candle as a light risk; stealth hold (progress pauses under sight); press-rhythm noise masking; rising-water exfiltration; **sheathing and 無刀取り (mutō-dori)** |
| Unlocks | Weapon **3** Needle SMG (b05); weapon **13** Phantom SMG (b07, optional, auto-granted at ch07.b01 if missed); weapon **10** Tantō (b10). Mechanic flags `tsubute` (b06) and `muto_dori` (b09). |
| Sites (catalog) | site 0 監視の中継器 → b04 · site 1 債務の帳簿 → b08 · site 2 金庫の印刷機 → b11. The order already matches `requires_sites`. |
| Map | Arena 3 (Debt Citadel) exterior plus new C3 vault and palace interiors; b16 uses Arena 1 (Lantern Ward, 高札場) |
| Horses | None |
| Kill requirement | **None.** The chapter can be finished without killing anyone: takedowns are non-lethal by default, the duel is non-lethal, and Eskro is sealed away rather than killed. |

---

## 1. Synopsis, locations and lighting

### 1.1 Synopsis

**JA.** 六月晦日、月のない夜。会計補イオタの密書に導かれ、ニャーコトと小萩は債務の城塞の堀を泳ぎ、旧水門から帯曲輪へ忍び込む。算木積みの隅を登り、隅櫓に据えられた監視の中継器を止める。文書蔵の箱の中で震えていたイオタは、鍵板と一挺の針銃を差し出す。彼が寝返った理由は、計算だった。帳簿回廊と鶯張りの廊下を抜け、御殿の大広間で、ニャーコトは蝋燭一本の灯りで三冊の総高を透かし写す。記録庫では虎之介が待っていた。真剣の立ち合いの最中、虎之介は自家の頁を目にする。「毎月払った。増えた。」ニャーコトは刀を納め、無刀取りで彼の刀を取り、そして返す。虎之介は短刀を誓いの証として差し出す。印刷所の親機を楔で止めると金庫全体が停電し、盲目の金庫番エスクロが目を覚ます。音だけの闘いを生き延びてエスクロを水底の金庫に封じ、満ちてゆく暗渠を抜けて堀へ戻る。夜明け、写しは提灯街の高札場に貼り出され、人々は初めて自分の数字を読む。その頭上を、旗艦の影が通り過ぎる。

**EN.** It is the last night of the sixth month, and there is no moon. Guided by a secret message from Junior Auditor Iota, Nyaakoto and Kohagi swim the Debt Citadel's moat and slip through the old water gate onto the narrow terrace below the keep wall. They climb the corner stones and shut down the surveillance relay built into the corner turret. Iota is found curled up in a document crate. He hands over a key-slate and a needle gun he has never fired, and he explains that he defected because of arithmetic. Past the ledger aisles and a nightingale floor, in the old palace's audience hall, Nyaakoto traces the totals of three master ledgers by the light of one candle. Toranosuke is guarding the archive. In the middle of a real-steel duel he sees his own family's page ("I paid every month. It grew."). Nyaakoto sheathes his sword, takes Toranosuke's blade with mutō-dori, and then gives it back. Toranosuke pledges his tantō. Wedging the master presses shut blacks out the vault and wakes the blind Vault Warden Eskro. Nyaakoto survives a fight fought only by sound, seals Eskro in the flooded vault, and escapes up a filling culvert to the moat. At dawn the copies go up on the Lantern Ward notice board and people read their own numbers for the first time. Overhead, the flagship's shadow moves.

**Arc function.** This chapter moves from resistance to **exposure**. The League stops fighting the ledger and publishes it (charter article 5, 帳は民の前に). Toranosuke's redemption by disarming completes theme 4, and Nyaakoto repeating Sekireisai's words, 「刀は民から預かるもの」, shows the master's teaching finished in his absence (theme 1).

### 1.2 Chapter rules

- **Loadout at chapter start.** Katana (hip), wakizashi (side), yumi and a 12-arrow ebira (back). The yumi is **unstrung** until b03: the hemp string (麻弦) travels dry in Kohagi's oiled pouch. The polearm slot is empty (a yari does not swim), the firearm slot is empty until b05, and there is no armor. Nyaakoto wears indigo and persimmon-tannin (柿渋) work clothes with 手甲 and 脚絆. Firearms stay behind because the swim would ruin matchlock powder and gunfire is too loud for this job. No weapon can be used while swimming.
- **Communications.** In b01–b03 Iota's voice comes through the message slate Nyaakoto carries (`radio`). It cuts out at the start of b04 because an audit is under way. In b04 Kohagi whispers through the turret's slatted window. At the end of b04 she takes the message slate back to hold the water gate. In b05 Iota's key-slate pairs with it, so from then on both Kohagi (at the gate) and Iota (watching the vault's reconciliation board) can speak over the radio. Radio lines duck the music by 6 dB. While any guard is alert they are queued, not cut.
- **Stealth ruleset for this chapter (L2 proposal).** The AI states are unaware → suspicious (a meter fills at `suspicion_rate`; the state is shown at 0.35) → alert (at 1.0) → search (for `search_s` after contact is lost) → unaware. After a search the guard stays *wary* (+20% suspicion rate) for the rest of the beat. **Auditors** do not fight; on alert they run to the nearest 警報台 alarm lectern (about 4 s). Stopping one before he gets there prevents the zone alarm. Unconscious bodies can be found and trigger `search` zone-wide; they can be dragged at half speed. Rear takedowns are **non-lethal by default** (当て身, a hilt strike to the collar-node); holding the input makes them lethal. Guards on Easy fall back to `combat`, as the bible requires.

| Detection (Normal) | enforcer_rifle | auditor | drone | Parapet sentry (b03) |
|---|---|---|---|---|
| Sight cone | 90° | 70° (own lamp lights 6 m) | 60°, pitched down | 60° |
| Sight range, lit / dark | 2,400 / 900 cm | 1,800 / 600 cm | 1,500 / 1,000 cm | 1,800 / 900 cm |
| Hearing | 1,200 cm | 900 cm | 600 cm | 1,000 cm |
| On alert | Engage; call support | Run to alarm lectern | Mark the player (local only once the relay is down) | Fire, 12 damage per 1.2 s |

| Player noise radius | cm | Surface multipliers and special cases |
|---|---|---|
| Sprint | 1,500 | Puddle and gravel ×1.5; tatami ×0.5; wading ×2.0; running water ×0.5 |
| Walk | 600 | Nightingale floor: walk 1,800, crouch-walk 900, **edge strip crouch-walk 0** |
| Crouch-walk | 250 | Press hall: player noise ×0.2 for 500 ms after each stamp within 800 cm |
| Swim at surface / dive | 500 / 0 | Touching the moat float line: 1,400 |
| Tsubute impact | 1,400 (at the landing point) | Guards investigate for 8 s |
| Needle SMG shot / yumi release / takedown | 1,500 / 300 / 300 | Fusuma slide 400 |

Visibility multipliers: darkness ×0.4, cyan slate light ×1.0, **lit candle ×2.0**, cupped candle ×1.2. Easy: suspicion ×0.7, search time ×0.8. Hard: ×1.25 and ×1.2.

### 1.3 Locations and layouts

Coordinates are metres in each place's local frame (+x east, +y north, z up) unless noted. Volumes are named `vol_*`, spawns `sp_*`, splines `spl_*`, player starts `ps_*`. **All of this is campaign-only geometry in chapter sublevels. It must not change Arena 3 or Arena 1 collision** used by practice and multiplayer (bible §14).

#### L1 · `pl_citadel_moat`: 堀と水門, moat and water gate (b01, b02, b14, b15)

- **Footprint.** The playable moat stretch is 220 m × 36 m of water, 2.4 m deep (3.0 m at the gate). The origin is the SW corner of the water. The outer bank (外堤, y < 0) is an earthen bank with a reed bed and willows. On the inner side (y = 36) is a low 腰巻石垣 (1.5 m) topped by a 2.2 m 土塀 with 狭間 loopholes. Behind it is the 帯曲輪, a 6 m terrace, and then the 16 m keep wall rising from its far edge. Height fog is thick: sight is 35 m in light and 12 m in darkness.
- **Landmarks.**
  - The League hide in the reeds (start, x 4–12).
  - Burned bridge pilings (x 88–96).
  - Two alien searchlights grafted onto keep-wall turrets: S1 at (60, 48, 17.5) and S2 at (150, 48, 17.5).
  - The sensor float line across the moat at x 132.
  - Three seized, moored 小舟 at (72, 33), (140, 33) and (196, 30).
  - The old 水門 at x 206–210. It is a timber and iron grille over a channel into a small 船入 basin (10 × 8 m) on the terrace. The grille's lower 0.6 m (depth 1.2–1.8 m) is unfastened.
- **Routes.**
  - **A, reed edge (y −2 to 4).** Longest and safest; the drone passes overhead twice.
  - **B, centre (pilings and lotus).** Fastest, but crosses both searchlight sweeps.
  - **C, wall base (y 30–35).** In the searchlights' blind cone (灯台下暗し), but under the parapet sentries' look-down arc and past the moored boats.
- **Cover.** The reeds, three lotus beds (x 40–70 / y 4–14, x 100–125 / y 20–32, x 165–185 / y 6–16), the pilings and the boats. Surfacing under lotus leaves hides the head.
- **Sightlines.** Each searchlight sweeps a 70° arc every 10 s with a 4 m spot. Parapet patrol A covers x 30–100 and B covers x 110–190, both at z 17.5 on the keep wall. The drone flies a figure-8 over x 40–180, y 8–28, at 6 m.
- **Exfil additions (b14).**
  - A 90 m stone culvert (暗渠), 2.4 m wide and 2.2 m high, runs from the vault core's south drain to the 船入. It has its own frame: x′ = 0 at the vault end, 90 at the gate. Iron grates in its ceiling at x′ 20, 45 and 70 open onto the terrace, where searchers shine lamps down.
  - The water gate is winched half open by Kohagi, then the swim runs south across the dark moat to the outer bank (x 180–220). A lamp boat carrying two enforcers patrols x 60–200.

```
 y(m)   S1 (x60) searchlight            S2 (x150) searchlight           keep wall 16 m, z 17.5 walk
  48  . . . . parapet A (x30-100) . . . . parapet B (x110-190) . . . . . . . . . . . . . . .
  42  ============================== obi-guruwa terrace (6 m) ======================= [funairi]
  36  ------------------ low wall 1.5 m + dobei 2.2 m (loopholes) ------------------ [GATE] x206-210
  30   route C (wall base, blind to lights)   boat@72       boat@140              boat@196
  20              lotus2 (x100-125)   ||pilings x88-96     :float line x132   lotus3 (x165-185)
  10   lotus1 (x40-70)                ||                    :
   0  ~~~~ reeds ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  -4  [START hide x4-12]            outer bank, willows                  [EXFIL bank x180-220]
      0        40        80        120        160        200   220  x(m)
```

| Volume | Box (x, y, z ranges) | Purpose |
|---|---|---|
| `vol_moat_stealth` | 0–220, −4–36, −3–3 | b02 zone |
| `vol_moat_reeds` | 0–20, −4–2 | Start cover; `ps_moat_reeds` at (10, −1, 0) |
| `vol_moat_lotus_1..3` | see Cover | Surface cover; HUD hint |
| `vol_moat_pilings` | 88–96, 4–32 | Iota's searchlight line |
| `vol_moat_boom` | 130–134, 0–36 | Float line; the tutorial to dive under it |
| `vol_moat_wallbase` | 30–200, 30–36 | Kohagi's 灯台下暗し line |
| `vol_water_gate_outer` | 200–214, 30–36 | League mark collectible ch06.c01 |
| `vol_water_gate_inner` | 204–214, 37–45 | **b02 exit** (船入 basin) |
| `vol_ankyo_start` / `_grate_1..3` / `_deep` | x′ 0–6 / 20, 45, 70 (±1.5) / 75–90 | b14 lines, lamp-beam volumes, forced dive |
| `vol_water_gate_exit` | 206–210, 34–38 | b14 gate crossing |
| `vol_moat_exfil` / `vol_moat_outer_bank` | 150–220, −4–36 / 180–220, −8–−2 | b14 zone / **b14 exit**, b15 staging |

#### L2 · `pl_ishigaki`: 石垣, the keep-wall corner (b03)

- **Footprint.** The origin is the base of the wall corner's arris, at terrace level (1.5 m above the water). The terrace runs x −40 to 20 and y −6 to 0 along the wall's south face.
- **The wall.** 16 m of 打込接ぎ masonry with a 算木積み corner, where long and short dressed stones alternate faces. It has the fan-shaped profile (扇の勾配): the lower 6 m slopes at about 60°, and the upper 10 m curves up to about 80°.
- **Landmarks.**
  - The corner turret (隅櫓) on the wall top, 12 × 10 m, z 16–24. It has a projecting 石落とし stone-drop bay at x −3 directly above the corner route.
  - The alien spire's graphite extrusion, which bites into the south face at x −10 and splits stones from z 4 to 15.
- **Routes.**
  - **Corner (`spl_climb_corner`).** 14 authored holds on the arris, with rest ledges at z 5.5 (`vol_rest_ledge_1`, a protruding long stone) and z 11 (`vol_rest_ledge_2`, a missing stone, in shadow).
  - **Extrusion (`spl_climb_extrusion`).** 8 holds and faster, but lit by a cyan ledger strip and visible from the parapet.
- **Grip.** Grip is 100; each move costs 6; ledges restore 25/s. A fall of more than 4 m does 30 damage; more than 8 m is lethal.
- **Sentry.** One `enforcer_rifle` walks the 30 m parapet (x −38 to −8, z 16). Every 20 s he stands in the stone-drop bay and looks down for 4 s, covering holds 9–14 and the upper extrusion.
- **Exit.** A 0.6 m crawl gap where the extrusion broke the turret's lower wall boards, at (0, 3, 16.5), leads into the relay room's ground floor (`vol_climb_top`).
- **Kohagi.** She climbs first and shows the line. At the top she goes up onto the turret roof.

#### L3 · `pl_relay_room`: 中継器室, the relay room in the corner turret (b04)

- **Footprint.** 20 × 10 m. x 0–12 is the old turret: 欅 posts, board floor, plaster walls with 連子窓 slatted windows. x 12–20 is the fused alien annex of black glass. The ground floor is z 0–4. A gallery 1.8 m wide runs around a central void (x 6–14, y 2.5–7.5) at z 4.
- **The relay.** A black-glass column at (10, 5), 1.6 m across and 7.5 m tall, punched up through the turret's upper floor. Its rotating scan fan sweeps 360° every 12 s, so each node is exposed for 8 s and hidden for 4 s. Nodes: `node_w` (9.2, 5, 1.2), `node_e` (10.8, 5, 1.2), `node_n` (10, 5.8, 5.2), the last reached from the north gallery. Pulling a node takes 3 s. If the fan catches the player mid-pull, suspicion rises by 0.6 and the fan locks on for 2 s.
- **Guards.** `enforcer_rifle` ×2: one on a 50 s ground-floor loop around the void, one on a 40 s gallery loop that comes down the steep turret stair (梯子段) every other lap. `auditor` ×1 seated at a reading stand (見台) at (3, 5) facing the column; he walks over to inspect any node that goes dark. `drone` ×1 orbits the column at z 5 every 30 s.
- **Cover.** Four 長持 chests, three stacks of seized village alarm bells (半鐘; loose clappers around them are loud), eight posts and the gallery railing. Light: the column's cyan glow reaches 6 m. Two alien work lamps (SE at (19, 1, 3), NW at (1, 9, 3)) can be switched off, which makes the nearest guard suspicious after 5 s.
- **Entry and exit.** Entry is the crawl gap at the west wall (0, 5), `vol_relay_entry`. Exit is the east glass door at (20, 5), `vol_relay_exit_east`, onto a glass bridge to the ledger corridors. Kohagi lies outside the upper north slatted window at (10, 10, 5.5).
- **When the relay goes down.** Drones only mark within 20 m for the rest of the chapter, and the moat searchlights freeze in place, which matters for b14.

```
 N  y=10 +---------------------------+--------------------+
        | NW lamp   stair(up)  bells | (Kohagi outside    |
        |  chests        +--------+  |  upper N window)   |
        |                |  VOID  |  |        bells       |
  entry |>    node_W -> (O) COLUMN (O) <- node_E   chests |> exit E -> glass bridge
  (0,5) |  auditor stand |node_N up|  |                    |
        |  (3,5)         +--------+  |           SE lamp  |
    y=0 +---------------------------+--------------------+
        x=0     old turret timber  x=12  alien glass  x=20
```

#### L4 · `pl_ledger_corridors`: 帳簿回廊, the ledger aisles (b05 annex, b06 part 1)

- **Footprint.** 24 × 64 m, 6 m high, with polished basalt floors. Five north–south aisles (A1–A5) each 3.2 m wide, between shelf banks 1.2 m deep and 4.5 m high of glass ledger slates. Each slate is one household, glowing cyan numerals. Cross-aisles C1–C4 run at y 12, 28, 44 and 60. Condensation drips form three puddles near the aisle ends. The hall's cold (breath vapour shows) contrasts with the humid night outside.
- **Archive annex (b05).** A 10 × 8 m document store off the bridge landing at the SW corner (x −10 to 0, y 0–8). It holds crates of seized household deeds (証文). Iota's crate is stencilled 「保存期限：永久」 ("Retention: permanent"). A wall panel here, the 照合盤 (reconciliation board), shows guard positions; this is where Iota's intel comes from.
- **Guards (b06, aisles).**
  - `auditor` ×4 carrying lamps, patrolling A1, A2, A4 and A5.
  - `enforcer_rifle` ×2 posted at C2 and C4, sweeping 90° every 8 s.
  - `drone` ×2 above the shelf tops at z 5.5, on 35 s loops.
  - Alarm lecterns at C2/A1 (2.8, 28) and C3/A5 (20.4, 44).
- **Cover and routes.** Shelf ends, slate carts, and six dark gaps where slates were "written off" (1 m hiding niches). The aisles give 64 m straight sightlines; the cross-aisles cut them into 16 m runs. Tsubute piles lie where the spire's roots cracked the old foundation: C1/A3 (11.6, 12), C3/A2 (7.2, 44) and C4/A4 (16, 60). The exit at the north end (y 64) joins the old palace.

```
        y=64  exit N -> palace nightingale corridor (leg A)
         |A1 |##|A2 |##|A3 |##|A4 |##|A5 |
  C4 y60 +---post_c4-------------rubble(16,60)--+
  C3 y44 +-rubble(7.2,44)-------------alarm(20.4,44)+
  C2 y28 +alarm(2.8,28)---post_c2-----------------+   (chatter volume vol_aisle_c2)
  C1 y12 +----------rubble(11.6,12)---------------+
         |   |##|   |##|   |##|   |##|   |
  [annex x-10..0, y0..8] <- glass bridge landing (from the relay room)   y=0
```

#### L5 · `pl_uguisu_hall`: 鶯張りの廊下 and the palace (b06 part 2, b07, b08)

This is the Nekoyama castle's surviving palace (御殿), whose fittings the Credit House has stripped and re-purposed. The origin is the SW corner of its inner garden.

- **Nightingale corridor.** It is L-shaped and 2.7 m wide (1.5 ken).
  - **Leg A** runs along the garden's south side, x −6 to 24.
  - **Leg B** runs along the east side, y 0–22, ending at the 杉戸 cedar door at (25.4, 22).
  - The whole corridor is nightingale floor. Along the fusuma side is a **0.2 m edge strip** (`vol_uguisu_edge`) where the boards rest on a sleeper, silent at crouch-walk.
  - The fusuma are partly stripped; the wall paintings are shrouded in alien plastic sheeting.
  - Two tatami rooms behind the fusuma of leg A (`vol_uguisu_rooms`) are a quiet alternative. Tatami is ×0.5 noise, but sliding a fusuma makes noise (400).
- **Inner garden.** 24 × 16 m of raked white gravel (×1.5 noise) with three stones, a pine, an unlit stone lantern and a 蹲踞 water basin. The eave shadow gives cover from the corridor. It is also where the door guard can be lured (`vol_garden_edge`).
- **Guards (b06, palace).** `auditor` ×2: one posted at the corridor corner facing up leg B, one pacing leg B. `enforcer_rifle` ×2: one pacing leg A (40 s), one posted at the cedar door facing down leg B. He must be lured into the garden with a tsubute, or the player takes the quiet tatami route and comes at him from behind.
- **Vestibule** (溜の間, x 22–30, y 22–28), beyond the cedar door. `vol_sugido` (b06 exit) is here.
- **Seized-goods store** (b07, `vol_vault_armory`; the bible's "vault armory"). The palace 納戸 storeroom east of the vestibule, x 30–44, y 20–30. It holds racks of seized swords and matchlocks with alien tags, a contraband crate, the Phantom SMG locker (opened with the key-slate), an arrow cache, and a slatted window looking south over the wall to the town (`vol_poi_vista`).
- **Registry hall** (記帳の間, b08, `vol_ohiroma_kicho`). The palace audience hall west of the vestibule, x −6 to 22, y 22–34, in shoin style with three stepped levels:
  - 下段 x 10–22, with desk `desk_tagata` (田方, fields) at (16, 29).
  - 中段 x 2–10, 15 cm higher, with `desk_machikata` (町方, town) at (6, 29).
  - 上段 x −6 to 2, 30 cm higher, with `desk_shokukata` (職方, crafts) at (−2, 29), in front of the 床の間 alcove and the ornamental 帳台構え door on the north wall.
  - The aliens have stacked the tatami against the walls, so the floor is bare boards (normal noise). A 1.8 m perimeter corridor (入側) runs along the south side. The coffered 格天井 ceiling is at about 5 m.
  - The `auditor` ×3 patrols each stop at a desk for 6–10 s and switch on a cold desk lamp while they are there. `enforcer_rifle` ×1 walks the perimeter corridor on a 60 s loop; `drone` ×1 flies at 4 m on a 30 s loop.
  - The only warm light is the player's candle (手燭 with a 和蝋燭).
  - The 帳台構え door leads north into the archive.

```
                 N   archive (pl_archive) via the ornamental door
  y=34 +----------------------------------------+ +--------------+
       | JODAN (+30cm)| CHUDAN (+15cm)| GEDAN    | |  vestibule   | storeroom (armory, b07)
       | desk_shoku   | desk_machi    | desk_ta  | |  [cedar door]| x30-44, y20-30
  y=22 +----(perimeter corridor)------------------+ +-----+--------+
       x=-6          x=2             x=10     x=22    |leg B (22 m, x24-26.7)
       +---------------------------------------+      |
       |   inner garden 24x16: white gravel,   |      |
       |   3 stones, pine, lantern, basin      |      |
  y=0  +---------------------------------------+------+ corner (auditor post)
   <- from aisles  ======== leg A (30 m, y -2.7..0) =========
```

#### L6 · `pl_archive`: 記録庫, the archive (b09, b10)

- **Footprint.** The castle's old book store (文庫), converted: 26 × 18 m, 6 m ceiling with exposed 梁 beams, old board floor (not nightingale).
- **Contents.** Alien slate racks line both long walls (x 0–1.2 and 24.8–26). They hold the 武家方 records, the samurai households. The 鷲尾家 slate is on the east rack at (25, 9, 1.5).
- **Duel ring** (`vol_archive_ring`, x 7–19, y 4–14). Four 欅 posts stand inside it near the corners at (9, 6), (17, 6), (9, 12) and (17, 12). They block blade arcs (the same reach-obstruction rule as ch05), which rewards the 転 flank.
- **Entry and exit.** Entry is the ornamental door at the south wall centre (13, 0). The exit, north door (13, 18), leads to a stair down to the press hall.
- **Light.** Cyan racks, and one dark high window on the north wall.

#### L7 · `pl_press_hall`: 印刷所, the press hall (b11)

- **Footprint.** 42 × 24 m, 9 m high, with a 1.2 m catwalk around the walls at z 4. The stair from the archive lands on the catwalk at the NW corner, and a ladder drops to the floor.
- **Presses.** Eight alien presses (4 × 3 m, 3.5 m tall) in three rows. Row A (y 5): A1 (8), **A2** (18), A3 (28). Row B (y 12): B1 (8), **B2** (18), B3 (28). Row C (y 19): **C1** (12), C2 (24). The three bold ones are **master presses (親機)**, each marked by a hanging die lamp. Every press stamps every 1.6 s.
- **Dressing and cover.** Seized washi bales along the west wall (x 1–4, y 4–16), drying racks of printed notices (x 34–40, y 6–20; see-through silhouettes), and the binding table and conveyor (x 32–40, y 1–4, `vol_press_binding`, where the auditor chatter and collectible ch06.c06 are). Scattered type slugs are loud (`vol_press_slugs_1/2`).
- **Guards.** `auditor` ×2 on 45 s inspection loops that visit each press. `enforcer_rifle` ×3: floor loops over rows A–B and B–C, plus one on the catwalk with a height advantage. `drone` ×1 over the rows on a 30 s loop.
- **Jamming.** 4 s per press: drive one of Kōzō's iron wedges into the platen gear and pull the die plate (刻印版). A jammed press stops stamping, so its noise masking disappears and an auditor comes to inspect it within 20 s.
- **Exit.** The freight lift at the SE corner (x 38–42, y 0–4, `vol_press_lift`).

#### L8 · `pl_vault_core`: 金庫核, the vault core (b12, b13)

- **Footprint.** A circular chamber 34 m across under a 14 m dome. A 2 m walkway ring runs at r 15–17, z 0; the floor inside it is sunk to z −1. The reconciliation column (照合柱), 4 m across and 14 m tall, stands at the centre; this is Eskro's roost. The origin is the centre at walkway level; 0° is north and angles run clockwise.
- **Terrain.** Eight raised shelf blocks at r 7–13, each 6 m long radially, 1.2 m wide and 1.4 m above the sunk floor, set at 22.5° + 45°·n. Four drain grates sit at r 10 at 0°, 90°, 180° and 270°, between the shelves. In phase 2 they reverse and flood the floor to 25 cm. Three rubble piles for tsubute are on the walkway at 90°, 210° and 330°.
- **Entry and exit.** The freight lift arrives at 0°, with the bulkhead lever beside it. The exit is the south drain (180°), which opens into the culvert once the column's sump is sealed.
- **Light.** Near black. Faint cyan leaks from seams in the column. Eskro's pulse shows as a refractive ring that distorts the dim light.

```
                     0 deg N: lift + bulkhead lever
                 .-~~~~~~~~~~~~~~~~~~~~-.
            330 rubble   shelf   shelf    \
          /  shelf    drain(0)     shelf    \
         |  drain(270)   (COLUMN)   drain(90)| 90 rubble
          \  shelf     drain(180)    shelf  /
       210 rubble   shelf    shelf        /
                 '-~~~~~~~~~~~~~~~~~~~~-'
                     180 deg S: exit drain -> culvert (b14)
```

#### L9 · `pl_kosatsuba`: 高札場, the Lantern Ward notice square at dawn (b16)

- The existing Arena 1 centre, cinematic only.
- **The kōsatsu board.** Timber boards about 5.4 m wide (3 ken) and 2.4 m tall under a small roof, on a stone base behind a low fence. League scribes paste paper sheets (張札) onto the frame with paste pots and broad brushes. Each sheet carries Oyuki's vermillion SORA seal.
- **Other dressing.** The scorched base of the Street Debt Terminal destroyed in ch03 (existing `StreetDebtTerminal` asset, burnt variant). SORA-mon lanterns from ch03, now unlit in daylight. A crowd of about 40. Optionally, a reed ring (茅の輪) from the previous night's summer purification rite, 夏越の祓, which was banned as an "unbillable gathering".
- **Camera.** It starts on the board, pulls back over the crowd, and tilts up to the sky as the flagship's shadow crosses the square.

### 1.4 Time of day, weather and lighting

Fiction date: 元和九年 六月晦日, the last night of the sixth lunar month (moonless), into the dawn of the seventh month's first day. Bible §16 row 6.

| Location | Key / fill | Weather and FX | Photoreal notes | Mac fallback |
|---|---|---|---|---|
| Moat and wall (b01–b03, b14, b15) | No moon. Cold 8,500 K searchlights; sky ambient near black with starlight 0.02 lux in the fog. The League hide uses one shaded candle. | Thick ground fog (0–6 m) with height falloff; still, humid late-summer air; drips from the wall; insect chorus. Searchlight shafts through the fog are volumetric. | Wet stone needs a wetness-mask transition at the waterline. After the swim, Nyaakoto's fur is **wet** (clumped, darker, dripping) and dries over about 5 min. The moat surface must carry stable reflections of the searchlights. | Height fog only; searchlights as a light cone plus a card shaft; wet fur as a material-parameter blend on card fur |
| Relay room (b04) | Cyan column 8,000 K is the key; two cold work lamps; deep blacks | Dust in the column light; a low hum | Aged 欅 and plaster against black glass, with the seam where they fuse as the hero detail | Column as an emissive mesh plus one shadowed light |
| Ledger aisles (b05–b06) | Slate emissives 7,000–9,000 K; auditor lamps 6,500 K | Condensation and breath vapour; drips | Thousands of emissive numerals: use a data-driven material with per-instance random household balances. The numerals must not form a readable repeating pattern. | Slates as emissive only; auditor lamps unshadowed except the nearest two |
| Palace, garden and registry hall (b06–b08) | Almost no ambient; the **player's candle at about 1,800 K** is the only warm source; cold desk lamps when auditors stop | Still air; garden gravel with dew | The warm-against-cold rule of §15 carries this beat. The 和蝋燭's large, swaying flame should be visible on the gilded fusuma edges and the coffered ceiling. | The candle counts as one of the ≤ 8 shadowed lights |
| Archive (b09–b10) | Cyan racks; a rim light from the high window (starlight) | Dust shaken from beams on post hits | The 鷲尾家 slate lighting up is the mid-duel event's key light | — |
| Press hall (b11) | Die lamps 5,500 K over the master presses; cyan status strips | Paper dust and stamp puffs every 1.6 s | Stamp rhythm drives light flicker and dust | Cap particles |
| Vault core (b12–b13) | Near black; the column's seams; the player's candle once placed (it does not reveal the player to Eskro) | Phase 2 water; phase 3 red emergency strobes that respect flash reduction | Refractive pulse ring, not a bright effect; readability comes from audio | Pulse as a screen-space distortion ring |
| Lantern Ward dawn (b16) | Low sun about 3,800 K rising to 5,000 K through clearing haze; sky 7,000 K | Dew, thin smoke; evening cicadas (ヒグラシ) at dawn | The flagship's shadow is a moving occluder: a large blocking volume casting a soft shadow across the square | Shadow as a moving light-function mask |

---

## 2. Beat list

### 2.1 Summary

| Beat | Type | Place | Min | Checkpoint | Site | Unlocks | Category |
|---|---|---|---|---|---|---|---|
| ch06.b01 | cinematic | pl_citadel_moat | 2.0 | yes | | | Cin |
| ch06.b02 | stealth_zone (swim) | pl_citadel_moat | 4.0 | yes | | | S |
| ch06.b03 | stealth_zone (climb) | pl_ishigaki | 3.0 | yes | | | S |
| ch06.b04 | stealth_zone | pl_relay_room | 4.0 | yes | **0** | | S |
| ch06.b05 | dialogue | pl_ledger_corridors (annex) | 2.0 | yes | | weapon 3 | Cin |
| ch06.b06 | stealth_zone | pl_ledger_corridors + pl_uguisu_hall | 6.0 | yes | | `tsubute` | S |
| ch06.b07 | explore_optional | pl_uguisu_hall (storeroom) | 3.0 | yes | | weapon 13 (optional) | E |
| ch06.b08 | production_task (hold, stealth) | pl_uguisu_hall (registry hall) | 4.0 | yes | **1** | | P |
| ch06.b09 | duel | pl_archive | 7.0 | yes, plus the mid-duel event | | `muto_dori` | C |
| ch06.b10 | dialogue | pl_archive | 1.5 | yes | | weapon 10 | Cin |
| ch06.b11 | stealth_zone | pl_press_hall | 4.0 | yes | **2** | | S |
| ch06.b12 | cinematic | pl_vault_core | 1.5 | no | | | Cin |
| ch06.b13 | boss | pl_vault_core | 7.0 | yes, per phase | | | C |
| ch06.b14 | stealth_zone (exfil) | pl_citadel_moat | 3.0 | yes | | | S |
| ch06.b15 | dialogue | pl_citadel_moat (bank) | 1.0 | yes | | | Cin |
| ch06.b16 | cinematic | pl_kosatsuba | 2.0 | no | | | Cin |
| **Σ** | | | **55.0** | longest gap 360 s | 3 sites | 3 weapons, 2 flags | C 14 · E 3 · S 24 · P 4 · M 0 · Cin 10 |

Dependencies: b07 and b08 each require b06; b09 requires b08. b07 is the only optional beat. The longest gap between checkpoints is b14 + b15 + b16 = 360 s, which is exactly the bible's limit.

### 2.2 Beat details

**ch06.b01 · cinematic · 燃やさず、写せ / "Copy it. Do not burn it." · 2.0 min · checkpoint**

- *Content.*
  - In the reeds, Oyuki, Kohagi and Nyaakoto crouch behind a half-sunk 田舟 flat boat. Iota's message slate projects a small cyan map of the vault (alien light, alien object; League objects never glow cyan).
  - Oyuki gives the order to copy, not burn, and explains why: burnt records are simply rewritten, while copied numbers can be read by the people they bind. The totals and rates are enough.
  - Kohagi takes the bowstring into her oiled pouch.
  - Closing shot, and approved humor beat #5: Nyaakoto's ears flatten at the black water. 「泳ぐよ。」 A pause. 「……泳ぐ。」
- *Sequence:* `LS_Ch06_B01_MoatBriefing`, 110 s, skippable; fallback `camera_blend`. End state: player in the water at `ps_moat_reeds`, weapons stowed for the swim.
- *Catalog anchor:* line 1 (scout).
- *Fail:* none.

**ch06.b02 · stealth_zone (swim) · 堀を泳ぎ、旧水門へ / Swim the moat to the old water gate · 4.0 min · checkpoint**

- *Traversal.* Surface swim 180 cm/s (noise 500), dive 140 cm/s (silent). Dives last at most **8 s**; breath recovers in 3 s at the surface; at 0 breath the player takes 10 damage per second. No weapons in the water.
- *Enemies.* `enforcer_rifle` ×2 on the keep-wall parapet (patrols A and B, sight range 3,500 cm, fog-limited). `drone` ×1 on a figure-8 at 6 m (50° cone, 1,200 cm).
- *Sensors.* Searchlights S1 and S2: 70° sweep every 10 s, 4 m spot. A head in the spot turns a guard suspicious after 0.5 s and alert after 1.5 s. The float line makes 1,400 noise if touched and is cleared by diving deeper than 80 cm.
- *Detection.* suspicion 0.8/s, search 20 s. `on_detected: reinforce:w_moat_alarm`: both searchlights lock onto the last-seen point for 6 s, two more enforcers join the parapet (`sp_moat_parapet_c`), and the drone drops to 3 m. Diving blocks hitscan below 1 m depth. The player escapes by diving to cover, then waits out a 20 s search.
- *Ally.* Kohagi leads the swim and cannot be detected; she waits at the gate.
- *Objective.* Reach `vol_water_gate_inner`.
- *Fail:* death (drowned or shot) → checkpoint.
- *Collectible:* ch06.c01 (league mark) at the gate lintel.
- *Dialogue:* Kohagi's breath rule at beat start; Iota's searchlight timing at the pilings; the float line; 灯台下暗し at the wall base; moat barks.

**ch06.b03 · stealth_zone (climb) · 算木積みの隅を登れ / Climb the corner stones · 3.0 min · checkpoint**

- *Setup.* At the start Nyaakoto strings the yumi (3 s, non-blocking animation with Kohagi's string). **The yumi is usable from here.**
- *Traversal.* 14 corner holds or 8 extrusion holds; grip 100, −6 per move, +25/s on a ledge. A fall over 4 m does 30 damage; over 8 m is lethal.
- *Enemies.* The parapet sentry (`enforcer_rifle` ×1): 30 m parapet patrol, stone-drop look-down every 20 s for 4 s, 60° cone, 1,800 / 900 cm.
- *Detection.* `on_detected: combat`. The sentry fires 12 damage every 1.2 s. The player can finish the climb under fire, or shoot him from a rest ledge with the yumi.
- *Objective.* Reach `vol_climb_top`.
- *Fail:* death → checkpoint.
- *Dialogue:* string the bow; the hold lesson (長短の互い違い); the freeze call on each look-down; the split at the top.

**ch06.b04 · stealth_zone · 監視の中継器を止めよ / Disable the surveillance relay · 4.0 min · checkpoint · site 0**

- *Objectives.* Pull `node_w`, `node_e` and `node_n` (3 s each, during the 4 s gaps in the fan's 12 s rotation), then exit east.
- *Enemies.* `enforcer_rifle` ×2 (ground-floor loop 50 s, gallery loop 40 s), `auditor` ×1 (posted; investigates dark nodes), `drone` ×1 (column orbit 30 s).
- *Teaches* the four AI states, with HUD marks and Kohagi's calls, and non-lethal rear takedowns (`takedown` is already unlocked in ch03). Bodies can be dragged; a body that is found triggers a search.
- *Detection.* `on_detected: reinforce:w_relay`: two enforcers from the east door after 8 s, and the nodes lock for 30 s.
- *On completion:* `site_restored:0` (catalog: 「監視の中継器を止め、潜入路を開いた。」). Drones mark only locally from now on; the moat searchlights freeze.
- *Fail:* death → checkpoint.
- *Collectible:* ch06.c02 (seizure notice) pinned to the bell stack.
- *Dialogue:* Iota cut off mid-sentence at beat start; Kohagi at the window; the first `suspicious` coaching; the generic enforcer and auditor bark sets are introduced; Kohagi takes the slate at beat end.

**ch06.b05 · dialogue · 会計補イオタを探せ / Find Junior Auditor Iota · 2.0 min · checkpoint · unlocks weapon 3**

- *Trigger.* `interact:crate_iota` in the annex. A faint chirp from the key-slate leads the player to the crate.
- *Mode.* The crate reveal is `blocking` (4 lines, about 9 s, under the 20 s cap). The rest is `ambient`, with the player free in the annex and `soft_lookat`.
- *Content.* Iota curled in the crate (approved humor beat #4). His reason for defecting: 「計算しました。四百年分。」 He hands over the **key-slate** and weapon **3**, his never-fired needle gun, which is quieter than enforcer carbines (noise 1,500 against 4,000). He warns that Eskro hunts by ear and that a Washio guards the archive. He stays hidden to watch the reconciliation board and report patrols over the radio.
- *Collectible:* ch06.c05 (scroll fragment) among Sekireisai's confiscated papers in the annex.
- *Fail:* none.

**ch06.b06 · stealth_zone · 帳簿回廊と鶯張りを抜けよ / Cross the ledger aisles and the nightingale floor · 6.0 min · checkpoint · unlocks `tsubute`**

- *Enemies.* The bible's count exactly: `auditor` ×6, `enforcer_rifle` ×4, `drone` ×2.
  - Aisles: 4 auditors, 2 posted enforcers, 2 shelf-top drones.
  - Palace: 2 auditors, 2 enforcers, one of them at the door and lurable.
- *Mechanics.*
  - **Tsubute** (礫): pick up at three rubble piles, carry up to 3, throw on an arc. The landing makes 1,400 noise; guards investigate for 8 s.
  - **Nightingale floor**: walk 1,800, crouch 900, edge strip 0.
  - Gravel garden ×1.5; tatami rooms ×0.5 (fusuma slide 400).
  - **Auditor alarm run**: 4 s to either lectern.
- *Detection.* search 25 s, then wary (×1.2). `on_detected: reinforce:w_lockdown`: if the alarm is raised, 4 enforcers come from the north and south doors and the C3 shutter closes for 30 s.
- *Objective.* Reach `vol_sugido`.
- *Fail:* death → checkpoint.
- *Dialogue:* Iota's patrol count; the tsubute lesson; auditor gossip about Iota's absence and the Warden being awake; Kohagi's singing-floor warning; the "nightingale at night?" bark; Iota's warning at the cedar door.

**ch06.b07 · explore_optional · 押収品庫を調べる / Search the seized-goods store · 3.0 min · checkpoint · optional · unlocks weapon 13**

- *Volume.* `vol_vault_armory`. POIs:
  - The Phantom SMG locker (weapon **13**, special; key-slate).
  - A contraband crate of SORA-mon items: a child's paper fan, chalk, a 手拭い. They carry alien ledger-sigil tags, never the mon.
  - Heirlooms ch06.c03 (Taemon's water-rights map) and ch06.c04 (Okinu's mother's boxwood shuttle).
  - An arrow cache (+6).
  - The slatted-window vista. The Lantern Ward glows warm with SORA lanterns among other districts still cold with cyan door numerals.
- *Rules.* No enemies; `exit_hint_after_s: 150` (a soft radio chirp; no markers). If the player skips it, weapon 13 is auto-granted at ch07.b01.
- *Fail:* none.

**ch06.b08 · production_task (hold, `stealth: true`) · 三つの帳台で総高を写せ / Copy the totals at three desks · 4.0 min · checkpoint · site 1**

- *Task.* Hold at `desk_tagata`, `desk_machikata` and `desk_shokukata` for 30 s each (`contest: pause`). **Progress pauses while any guard has line of sight.**
- *Method.* Tracing (透かし写し): Nyaakoto lays thin 雁皮紙 over the page and traces it by candlelight.
- *Candle.* It must be lit to copy. Lit: light radius 350 cm, visibility ×2.0. Cupped (hold Guard): visibility ×1.2 but copying at half speed.
- *Enemies (patrol wave at start).* `auditor` ×3 (each stops at desks and switches on a cold lamp), `enforcer_rifle` ×1 (perimeter corridor), `drone` ×1.
- *Alert.* Progress stays paused until the guard is dealt with or the search times out. There is no reinforcement wave: the tension is time and light, not combat.
- *Registry on completion:* 債務帳の写し 3冊 (Ledger copy, 3 volumes). `site_restored:1` (catalog: 「人々を縛る債務の記録を解放した。」).
- *Fail:* death → checkpoint.
- *Dialogue:* Iota names the desks; Kohagi on cupping the candle; Nyaakoto on tracing; Iota's rate line at 0.33 and 「閉じない仕様」 at 0.66; the auditors admire the "beautiful curve"; the warm-light bark.

**ch06.b09 · duel · 虎之介と立ち合え / Face Toranosuke · 7.0 min · checkpoint and mid-duel checkpoint · unlocks `muto_dori`**

- *Set-up.* Opponent `npc_toranosuke` with a real katana; the player has weapon 0. `lethal: false`; scoring by HP (600 on Normal). HP floor 10%: while the blade is in hand he cannot be beaten, only disarmed. Ring `vol_archive_ring` with four posts.
- *Phase 1 (100–50%), `toranosuke_steel_p1`.* Aggressive combinations (§2.3): 袈裟連撃 (parryable), 諸手突き (guard-breaking; answer with 転), 見せ上段 feint, 体当たり against a turtling guard.
- *Event at 50% (`family_page`).* A 20 s blocking cinematic, then a checkpoint. A post-strike slams Toranosuke into the east rack; the 鷲尾家 slate lights up. Nyaakoto reads it aloud: principal 120 koku, paid 40, **still owed 190**, bought for **30**. Toranosuke: 「黙れ！」
- *Phase 2 (50–0%), `toranosuke_steel_p2`.* Only desperate committed vertical cuts, all `muto_eligible`. Sekireisai's remembered voice cues the lesson, and the HUD teaches **sheathing** (hold Weapon Switch, 700 ms 納刀).
  - **Mutō-dori.** While sheathed, press Guard within **180 ms** of a committed vertical cut landing (234 ms Easy, 153 ms Hard). Nyaakoto steps inside the arc, takes control of the hands and hilt, turns the blade away and takes it. A mistimed attempt takes the hit.
  - `finisher: muto_dori`; the lethal finisher is disabled.
- *Loss.* `retry`. If Nyaakoto falls, Toranosuke stops the blade at his throat (「……立て。」) and play resumes from the phase checkpoint.
- *Dialogue:* the challenge echoes ch01 ("This time it is not bamboo"); combat barks; the family-page exchange; the memory voice. The first 真っ向 and the first 斬り落とし each carry a one-time voiced line, 「全部、払ったんだ！」 and 「なのに、なぜ減らん！」. After that the tells are visual (amber blade edge, rising to 上段) plus a kiai sound effect.

**ch06.b10 · dialogue · 誓い / The pledge · 1.5 min · checkpoint · unlocks weapon 10**

- 「毎月払った。増えた。」 Nyaakoto hands Toranosuke's katana back hilt-first and repeats Sekireisai's ch01 words: 「刀は、民から預かるものだ。」
- Toranosuke, down on one knee, offers his **tantō**, a 鎧通し worn on the right hip under his partial armor (馬手差し). He presents it hilt-first as a pledge (`blocking`, about 5 s). **Weapon 10** is unlocked.
- He keeps the grey Credit House haori for one more night, as a disguise for escorting Iota "under arrest" to the water gate (the haori burns in ch08). He calls Nyaakoto 弟弟子 for the first time.
- *Fail:* none.

**ch06.b11 · stealth_zone · 親機三台を止めよ / Jam the three master presses · 4.0 min · checkpoint · site 2**

- *Objectives.* `press_a2`, `press_b2`, `press_c1` (4 s each: wedge, then pull the die plate), then the lift.
- *Mechanics.*
  - **Noise masking**: within 800 cm of a running press, the player's noise is ×0.2 for 500 ms after each 1.6 s stamp (the music locks to this; §5.7).
  - **Silent-press inspection**: an auditor walks to a jammed press within 20 s.
  - Die lamps can be shot out with an arrow; the nearest guard turns suspicious after 5 s.
- *Enemies.* `auditor` ×2, `enforcer_rifle` ×3 (one on the catwalk), `drone` ×1.
- *Detection.* `on_detected: reinforce:w_press`: three enforcers from the lift after 10 s.
- *On completion:* `site_restored:2` (catalog: 「印刷機を止め、民の修理道具へ作り替えた。」). The three die plates are carried out; Tetsugorō reforges them in b16, which pays off the catalog's "repurposed" text.
- *Fail:* death → checkpoint.
- *Collectible:* ch06.c06 (collateral receipt No. 1 for Sekireisai) at the binding table.

**ch06.b12 · cinematic · 停電 / Blackout · 1.5 min · no checkpoint**

- The third wedge chokes the current the presses share with the vault core. The lights cascade out and the freight lift drops into the vault core.
- In the dark, the vault's dedication inscription is played in Val Amort's recorded voice (**catalog anchor line 2**). Eskro unfolds from the column: 「照合を、開始いたします。」
- `LS_Ch06_B12_Blackout`, 80 s. End state: player at `ps_vault_core_lift`, katana equipped.

**ch06.b13 · boss · 金庫番エスクロを封じよ / Seal away Vault Warden Eskro · 7.0 min · checkpoint per phase**

- `boss_eskro`, HP 1,800 (Normal). The arena is `vol_vault_core`, locked. Phases: hunt 100–60, flood 60–25, frenzy 25–0 (§2.3).
- *Core loop.* Stand still during pulses. Throw tsubute to draw a pounce onto empty floor. Strike during the 1.5 s recovery after a miss (rear ×1.5).
- *Light.* **Light never reveals the player to Eskro.** The candle can be set on a shelf to light an area safely in phases 1–2. In phase 3 the audit-hounds *can* see it, so light becomes a risk again.
- *Defeat* (`capture`). At 0 HP Eskro collapses into the sump at the column's base. The player holds the bulkhead lever for 2 s to seal him in the flooding vault. Whether he survives is left ambiguous.
- *Fail:* death → phase checkpoint.
- *Barks:* every pattern has a captioned voice telegraph.

**ch06.b14 · stealth_zone (exfil) · 満ちる暗渠を抜けよ / Escape through the flooding culvert · 3.0 min · checkpoint**

- *Hazard.* The culvert water rises from 40 to 160 cm over 150 s. The final 15 m (`vol_ankyo_deep`) needs a dive (at most 8 s). This is not a hard timer: slow play means more swimming, not failure.
- *Enemies.*
  - `enforcer_rifle` ×3 above the grates, shining lamps down; the beam volumes are the danger.
  - `drone` ×1 at the gate. With the relay down it only marks locally; it can be shot with an arrow or a Needle burst, which makes noise.
  - `enforcer_rifle` ×2 in a lamp boat on the moat (60 s loop).
  - `on_detected: combat`.
- *Allies.* Toranosuke and Iota follow and cannot be detected; Toranosuke carries Iota through the deep section. Kohagi holds the gate winch.
- *Objective.* Reach `vol_moat_outer_bank`.
- *Fail:* death → checkpoint.

**ch06.b15 · dialogue · 数字を読む / Reading the numbers · 1.0 min · checkpoint**

- In the reeds under a shaded candle, Oyuki reads the copies: principal 18,000 koku, 年五割, a fourteen-year term, **5.25 million koku at term, 400 years of the valley's output**. Iota confirms it.
- Toranosuke asks whether his house is in there too; everyone's is, which is why it goes up in front of everyone.
- Nyaakoto: **catalog anchor line 3**.

**ch06.b16 · cinematic · 帳は民の前に / The ledger before the people · 2.0 min · no checkpoint**

- Dawn at the Lantern Ward notice board. Scribes paste up the copies under the SORA seal. A woman realises her debt began as two bales. A man who cannot read is helped by Tōkichi.
- Oyuki names charter article 5. Tetsugorō weighs the three die plates: 「ええ鉄や。鍬になる。」
- The flagship's shadow crosses the square. Toranosuke names it; Nyaakoto: 「なら、取り返しに行く。」
- Chapter complete: the registry page (§2.3 of the bible) shows 債務帳の写し 3冊. Leads into ch07.b01.

### 2.3 Pattern tables (L3 / L2 proposals)

Windups are for Normal; Easy ×1.3, Hard ×0.85 (bible §8). Every telegraph precedes its damage by at least its windup. Amber is for cleaves and area attacks; there is no cyan lock in this chapter.

**Washio Toranosuke, real steel (b09).** HP 600, floor 10% until disarmed.

| Phase | Attack | Windup | Damage | Recovery | Counterplay | `muto_eligible` |
|---|---|---|---|---|---|---|
| P1 | 袈裟連撃 kesa combo (3 diagonal cuts, 300 ms apart) | 450 ms (first) | 22 each | 700 ms | Awase any cut (260 ms) → 1.2 s stagger | no |
| P1 | 諸手突き two-handed thrust | 600 ms | 30 (guard takes 50% + 40 stamina) | 900 ms | Cannot be parried; 転 within 400 ms → flank, 0.8 s opening | no |
| P1 | 見せ上段 feint: raises to jōdan (300 ms tilt tell), then a low dō cut | 500 ms after the switch | 26 | 700 ms | Read the tilt; guard low or step out of maai | no |
| P1 | 体当たり shoulder check (if guard is held for more than 1.5 s) | 400 ms | 10, 150 cm knockback, −25 stamina | 600 ms | Do not turtle | no |
| P2 | 真っ向斬り vertical cut from jōdan (amber blade-edge flash) | 800 ms | 40 | 1,100 ms | **Mutō-dori** (sheathed, 180 ms) or awase | **yes** |
| P2 | 踏込み斬り落とし 3 m lunge, then a vertical cut | 700 ms | 38 | 1,200 ms | Mutō-dori; the post-flank breaks his line | **yes** |
| P2 | 二段真っ向 two vertical cuts | 800 / 500 ms | 34 each | 1,300 ms | Mutō-dori on either cut | **yes** |

**Vault Warden Eskro (b13).** HP 1,800; rear strikes ×1.5; blind (sound only).

| Phase (HP) | Pattern | Windup | Effect / damage | Recovery | Counterplay | Voice telegraph |
|---|---|---|---|---|---|---|
| All | 照合 reconcile pulse: every 8 s (P1, P2), every 4 s (P3) | 700 ms rising chirp | An 18 m refractive ring expanding over 720 ms. It reveals the player if moving faster than 120 cm/s or making any noise event as it passes. No damage. | — | Stand still | 「照合。」 |
| All | 聴取 listen: stands 2–4 s, head tilting | — | Hears walking within 12 m and crouch-walking within 6 m | — | Stay still or crouch far away | — |
| All | 飛掛り pounce onto the last noise, up to 15 m | 600 ms, amber landing decal | 45 in a 2.5 m radius | 800 ms on a hit / **1,500 ms on a miss** (claws stuck) | Tsubute bait; rear strikes during a miss | 「……不一致。」 (at windup) / 「……誤差。」 (on a miss) |
| All | 連爪 claw flurry (when revealed within 3 m) | 500 ms | 3 swipes over 900 ms, 18 each, 120° arc | 900 ms | Front guard; awase the 3rd swipe → 1.2 s stagger | 「端数、切り捨て。」 |
| P2 (60–25) | Floor floods 25 cm; wading ×2 noise; shelf tops silent | — | — | — | Move along the shelves | 「水は、帳尻を誤魔化しません。」 |
| P2+ | 棚払い shelf rake | 900 ms, amber arc | 35 in a 120°, 4.5 m arc; knocks the player off shelves | 1,200 ms | Drop to the other side of the shelf, or back off | 「棚卸し。」 |
| P2+ | 水走り wade charge, 12 m lane | 700 ms, amber lane | 40 | 1,000 ms | Sidestep; his own splash reveals where he is | 「取り立て。」 |
| P3 (25–0) | 二段飛掛り double pounce | 600 + 600 ms | 45 each | 1,500 ms after the second miss | Two baits, or bait and then move | 「……不一致。」 |
| P3 | Adds: 2 audit-hounds (a `drone` variant, 60 HP each, 9 m 70° sight, **see light**) | 600 ms chirp | Reveals the player's position to Eskro | — | Shoot them first (1 arrow or a Needle burst) | 「全件照合。猟犬を、放ちます。」 |
| 0 HP | Collapse into the sump | — | Hold `bulkhead_lever` for 2 s | — | — | 「……照合、不能。」 |

### 2.4 Collectibles (6; `collectible_id` ch06.c01–c06; chapter-local mask bits 0–5, global 30–35)

| Id (bit) | Category | Where (beat) | Codex JA | Codex EN |
|---|---|---|---|---|
| ch06.c01 (0) | 空紋の目印 league mark | Water-gate lintel (b02) | 水門の水位目盛りの横に、小萩が先月残した小さな空紋。 | A small Sora mark Kohagi left last month beside the gate's water gauge. |
| ch06.c02 (1) | 差押状 seizure notice | Relay room, bell stack (b04) | 差押状：猫柳生谷の半鐘、四十二口。理由：無許可の警報は与信を損なうため。 | Seizure notice: 42 alarm bells, Nyaagyu valley. Reason: unlicensed alarms damage creditworthiness. |
| ch06.c03 (2) | 家宝 heirloom | Storeroom (b07) | 庄屋田右衛門家の水利絵図。堰と水路ごとに、どの田へ何日水を回すかが描かれている。 | Headman Taemon's water-rights map: which paddy gets water from which channel, and for how many days. |
| ch06.c04 (3) | 家宝 heirloom | Storeroom (b07) | お絹の母の黄楊の杼。手の脂で飴色に光る。 | Okinu's mother's boxwood shuttle, polished amber by years of hands. |
| ch06.c05 (4) | 伝書の断簡 scroll fragment | Archive annex, confiscated papers (b05) | 無刀とは、人の刀を取る芸にあらず。わが手の内を知り、斬られぬことなり。――石鈴斎 | No-sword is not the art of taking another's blade. It is knowing your own hands, and not being cut. (Sekireisai) |
| ch06.c06 (5) | 差押状 seizure notice | Press hall, binding table (b11) | 担保受領書 第一号：猫柳生石鈴斎（隠居）一名。保管先、担保牢。状態、良好。 | Collateral Receipt No. 1: Nyaagyu Sekireisai (retired), one. Held in the collateral cells. Condition: good. |

ch06.c05 is an original line **inspired by** the 無刀 section of 柳生宗矩『兵法家伝書』; it is not a quotation. ch06.c06 tells the player that the master is alive and where he is held, setting up ch08.b07–b08. The returned heirlooms appear in Taemon's and Okinu's homes in the epilogue. Mask bits follow the sibling scripts (ch04, ch07, ch08): chapter-local 0–5, with the global bit (chapter − 1) × 6 + n if L1 keeps one 48-bit mask.

### 2.5 HUD tutorial prompts (L4 `ui_strings`; not voiced)

Bracketed tokens are input actions that L4 resolves per device. Prompts never show map markers.

| Prompt id | Beat | Shown on | Japanese (UI) | English |
|---|---|---|---|---|
| `hud.ch06.swim_dive` | b02 | `beat_start` | 潜る：{Crouch}　息は8秒まで | Dive: {Crouch}. Breath lasts 8 s. |
| `hud.ch06.surface_cover` | b02 | `volume_enter:vol_moat_lotus_1` | 蓮と葦の陰なら、浮いても見つかりにくい | Lotus and reeds hide you at the surface. |
| `hud.ch06.float_line` | b02 | `volume_enter:vol_moat_boom` | 浮き綱に触れると鳴る。下を潜る | The float line rings if touched. Dive under it. |
| `hud.ch06.climb` | b03 | `volume_enter:vol_climb_start` | 手掛かりへ進む。握力に注意 | Reach for the holds. Watch your grip. |
| `hud.ch06.climb_rest` | b03 | `volume_enter:vol_rest_ledge_1` | 足場で握力が戻る | Ledges restore grip. |
| `hud.ch06.ai_states` | b04 | `alert_state:suspicious` | 頭上の印：不審・警戒・捜索 | Marks above heads: Suspicious, Alert, Search. |
| `hud.ch06.sweep_gap` | b04 | `volume_enter:vol_relay_entry` | 柱の目が背を向けた隙に、{Interact}で節を抜く | Pull a node with {Interact} while the eye faces away. |
| `hud.ch06.takedown` | b04 | `ai_event:first_rear_reach` | 背後から当て身：{Melee}（殺さない） | Rear takedown: {Melee}. Non-lethal. |
| `hud.ch06.drag` | b04 | `ai_event:first_takedown` | 倒れた者を引きずる：{Interact}長押し | Drag a body: hold {Interact}. |
| `hud.ch06.tsubute` | b06 | `volume_enter:vol_rubble_c1` | 礫（つぶて）：音で見張りを誘う | Tsubute: lure a guard with noise. |
| `hud.ch06.nightingale` | b06 | `volume_enter:vol_uguisu_entry` | 鶯張り：しゃがんで壁際の端を歩く | Nightingale floor: crouch along the wall edge. |
| `hud.ch06.candle` | b08 | `beat_start` | 蝋燭を覆う：{Block}長押し　写しは半速 | Cup the candle: hold {Block}. Copying slows. |
| `hud.ch06.copy_pause` | b08 | `ai_event:copy_paused` | 見られている間は、写しが止まる | Copying pauses while you are seen. |
| `hud.ch06.sheathe` | b09 | `duel_phase:2` | 納刀：{Sheathe} | Sheathe: press {Sheathe}. |
| `hud.ch06.muto` | b09 | `ai_event:player_sheathed` | 無刀取り：納刀中、真っ向斬りに踏み込み{Block} | Mutō-dori: while sheathed, step into a vertical cut with {Block}. |
| `hud.ch06.press_mask` | b11 | `volume_enter:vol_press_floor` | 印刷機の打音が足音を隠す | Press slams mask your footsteps. |
| `hud.ch06.pulse` | b13 | `beat_start` | 脈動の間は動かない | Stay still while the pulse passes. |
| `hud.ch06.flood` | b13 | `boss_phase:2` | 水の中は音が大きい。棚の上は静か | Water is loud. Shelf tops are silent. |
| `hud.ch06.bulkhead` | b13 | `ai_event:boss_hp_zero` | 隔壁を落とす：{Interact} | Drop the bulkhead: {Interact}. |

### 2.6 In-fiction numbers (keep consistent in later chapters)

- **The valley's yearly output** is about 13,000 koku in rice-equivalent: rice, barley, silk, iron and crafts together. The domain's rice assessment is lower.
- **The master ledger.** Principal 18,000 koku. **年五割**, 50% a year effective, with a nightly tick of about ×1.00111. Fourteen-year term.
  - Year-1 interest is 9,000 koku. From **year 2** the interest alone (13,500) exceeds the valley's entire yearly output.
  - At term the balance is about **5.25 million koku, about 404 years** of output. This is Iota's 「四百年分」.
- **The 鷲尾家 slate (b09 prop text).** 元本 120 · 利息 22 · 延滞金 36 · 手数料 52 · 返済 △40 · **残高 190** · 買取価格 **30** (koku). The fees are front-loaded by the Credit House's "restructuring" when it bought the Osaka brokers' debt.
- These are fiction only (bible §2 boundary). They make no claim about any real currency or about SORA.

---

## 3. Dialogue (bilingual)

**Conventions.** Line ids are `ch06.bMM.<speaker>.<nnn>` (bible §18); the tables show the part after `ch06.`. Durations follow JA delivery at about 7.5 mora/s plus pauses, never below the EN reading floor (at most 17 cps) or 1.5 s. Catalog anchor lines keep their catalog 4.8 s. Every EN subtitle fits in 2 lines of 42 characters, and every JA caption is at most 32 characters (2 × 16). Barks marked *repeatable* have a cooldown of at least 20 s per speaker, which L5 sets. Registers: `samurai_polite` / `samurai_plain` (Nyaakoto with superiors / peers), `business_keigo` (Oyuki), `scout_terse` (Kohagi), `manual_keigo` (Iota, who honours objects: 石板様, 鍵板様, 探照灯様), `rival_brash` → `rival_humbled` (Toranosuke before and after the page), `mentor_archaic`, `alien_corporate` (collar DSP, no contractions in EN), `kamigata_commoner`, `artisan_gentle`, `artisan_blunt`, `inscription`.

**Tokens and speaker ids.** As in the bible's §12.4 example and the sibling scripts, the id token is the character's name and the `speaker` field holds the speaker id: `nyaakoto` → `samurai`, `kohagi` → `scout`, `oyuki` → `leader`, `iota` → `clerk`, `toranosuke` → `rival`, `sekireisai` → `mentor`, `eskro` → `boss_eskro`, `valamort` → `banker`, `tokichi` → `lantern_maker`, `tetsugoro` → `gunsmith`. `mentor`, `samurai`, `scout` and `banker` already exist in the catalog; the rest are bible §6 proposals. The generic ids **`enforcer`** (執行兵), **`auditor`** (監査官) and **`resident`** (町の衆) match the ch07 and ch08 proposals.

**Counts.** 143 lines (nyaakoto 26, kohagi 24, iota 22, toranosuke 20, auditor 13, enforcer 12, eskro 10, oyuki 9, sekireisai 2, resident 2, valamort 1, tokichi 1, tetsugoro 1).

**Bark precedence.** Beats list shared bark sets (`ch06_enforcer`, `ch06_auditor`, `ch06_moat`). Where a beat has its own line for the same event, the beat line replaces the set line in that beat (b03 and b11 have their own `alert` lines). Barks are captioned like any other line.

**Iota's keigo slip.** 「鷲尾様と申されます」 (b05) uses the humble verb 申す with an honorific ending, a well-known keigo error. It is deliberate: Iota learned keigo from manuals and over-applies it. B7 should confirm it reads as character rather than a writing mistake.

**Register note, catalog line 2.** 「契約は永遠だ。誰も帳簿からは逃れられぬ。」 is canon and kept verbatim, but its plain だ/ぬ form breaks the aliens' keigo rule (§6.3). It is therefore staged as the vault's **dedication inscription** (銘) played in Val Amort's recorded voice: inscriptions are written style, not speech. If B7 prefers speech register, the proposed alternative is 「契約は永遠でございます。帳簿からは、どなた様も逃れられません。」 That would be a catalog change for L1.

**Restrained humor in this chapter** (5 light moments in 55 min, none in the duel, the boss or grief): 泳ぐよ／泳ぐ (b01, approved #5); the "presumed fish" bark (b02); 「……大変、快適でございました。」 (b05, approved #4); the pay-cut gossip (b06, satire played flat); 「……鶯？ 夜に？」 (b06).

#### ch06.b01 · cinematic · 燃やさず、写せ / Copy it. Do not burn it.

| Line id | Trigger · mode | Speaker | Japanese | Readings | English subtitle | s |
|---|---|---|---|---|---|---|
| `iota.001` | sequence · radio | イオタ Iota | 水門の格子は、水の下で外してございます。 | 格子=こうし | The water-gate grille is unfastened below the waterline. | 3.8 |
| `kohagi.001` | sequence · subtitle · **catalog line 1** | 小萩 Kohagi | 金庫の奥に、街を縛る装置がある。 |  | The machine binding the city lies deep inside the vault. | 4.8 |
| `oyuki.001` | sequence · subtitle | お雪 Oyuki | 燃やさず、写しなさい。 |  | Copy it. Do not burn it. | 1.9 |
| `nyaakoto.001` | sequence · subtitle | ニャーコト Nyaakoto | 燃やせば早い。なぜ写すのですか。 |  | Burning is faster. Why copy it? | 2.8 |
| `oyuki.002` | sequence · subtitle | お雪 Oyuki | 燃やせば、彼らは「失われた」と言って、書き直すだけです。 |  | Burn it, and they call it lost and simply write it again. | 4.5 |
| `oyuki.003` | sequence · subtitle | お雪 Oyuki | 写せば、民が自分の数字を読めます。 |  | Copy it, and people can read their own numbers. | 3.4 |
| `oyuki.004` | sequence · subtitle | お雪 Oyuki | 総高と利率だけで足ります。欲張らぬように。 | 総高=そうだか | Totals and rates are enough. Do not be greedy. | 4.0 |
| `kohagi.002` | sequence · subtitle | 小萩 Kohagi | 弦は、あたしが濡らさず運ぶ。 | 弦=つる | I'll carry your bowstring. It stays dry. | 2.7 |
| `kohagi.003` | sequence · subtitle | 小萩 Kohagi | 泳ぐよ。 |  | We swim. | 1.5 |
| `nyaakoto.002` | sequence · subtitle | ニャーコト Nyaakoto | ……泳ぐ。 |  | …We swim. | 1.5 |

#### ch06.b02 · stealth_zone · 堀を泳ぎ、旧水門へ / Swim the moat to the old water gate

| Line id | Trigger · mode | Speaker | Japanese | Readings | English subtitle | s |
|---|---|---|---|---|---|---|
| `kohagi.001` | `beat_start` · ambient | 小萩 Kohagi | 息は八つまで。潜って、灯りをやり過ごす。 |  | Eight counts of breath. Dive, and let the light pass. | 3.6 |
| `iota.001` | `volume_enter:vol_moat_pilings` · radio | イオタ Iota | 探照灯様の周期は十秒。本日も定刻どおりでございます。 | 探照灯=たんしょうとう | The searchlights sweep every ten seconds. Punctual as ever. | 5.3 |
| `kohagi.002` | `volume_enter:vol_moat_boom` · ambient | 小萩 Kohagi | 浮きの綱。触ると鳴る。下をくぐって。 |  | A float line. It rings if touched. Go under. | 3.5 |
| `kohagi.003` | `volume_enter:vol_moat_wallbase` · ambient | 小萩 Kohagi | 灯台下暗し。壁際を行く。 | 灯台下暗し=とうだいもとくらし | Darkest under the lamp. We hug the wall. | 2.8 |
| `enforcer.001` | `alert_state:suspicious` · bark, repeatable · set `ch06_moat` (b02) | 執行兵 Enforcer | 水面に波紋。……魚類と推定いたします。 | 魚類=ぎょるい | Ripples on the water. Presumed to be fish. | 4.1 |
| `enforcer.002` | `alert_state:alert` · bark, repeatable · set `ch06_moat` (b02) | 執行兵 Enforcer | 侵入者を確認。照射を集中いたします。 | 照射=しょうしゃ | Intruder confirmed. Concentrating the beams. | 3.9 |
| `enforcer.003` | `alert_state:search` · bark, repeatable · set `ch06_moat` (b02) | 執行兵 Enforcer | 潜水中と推定。浮上をお待ちいたします。 | 浮上=ふじょう | Presumed submerged. We will await surfacing. | 3.9 |

#### ch06.b03 · stealth_zone · 算木積みの隅を登れ / Climb the corner stones

| Line id | Trigger · mode | Speaker | Japanese | Readings | English subtitle | s |
|---|---|---|---|---|---|---|
| `kohagi.001` | `beat_start` · ambient | 小萩 Kohagi | 弦。張って。 |  | Your string. String the bow. | 1.9 |
| `kohagi.002` | `volume_enter:vol_climb_start` · ambient | 小萩 Kohagi | 角の石は長短の互い違い。そこが手掛かり。 | 長短=ちょうたん<br>手掛かり=てがかり | The corner stones alternate long and short. Those are your holds. | 4.4 |
| `kohagi.003` | `ai_event:sentry_lookdown` · bark, repeatable | 小萩 Kohagi | 上、石落とし。……止まって。 | 石落とし=いしおとし | Drop-bay above. …Freeze. | 2.9 |
| `enforcer.001` | `alert_state:alert` · bark, repeatable | 執行兵 Enforcer | 壁面に債務者。落下による回収を試みます。 | 債務者=さいむしゃ | Debtor on the wall. Attempting recovery by fall. | 4.3 |
| `kohagi.004` | `volume_enter:vol_climb_top` · ambient | 小萩 Kohagi | あたしは屋根に回る。中は、あんたが。 |  | I'll take the roof. Inside is yours. | 3.2 |

#### ch06.b04 · stealth_zone · 監視の中継器を止めよ / Disable the surveillance relay

| Line id | Trigger · mode | Speaker | Japanese | Readings | English subtitle | s |
|---|---|---|---|---|---|---|
| `iota.001` | `beat_start` · radio | イオタ Iota | 申し訳ございません、ただいま監査が—— |  | My apologies. An audit is under way— | 3.1 |
| `kohagi.001` | `volume_enter:vol_relay_entry` · ambient | 小萩 Kohagi | 窓から見てる。光る柱の目が、回ってる。 |  | I'm at the window. The glowing pillar's eye is turning. | 3.7 |
| `kohagi.002` | `volume_enter:vol_relay_entry` · ambient | 小萩 Kohagi | 目が背を向けたら、節を抜いて。三つ。 | 節=ふし | When the eye turns away, pull a node. Three. | 3.5 |
| `kohagi.003` | `alert_state:suspicious` · ambient | 小萩 Kohagi | 首を傾げたら、怪しんでる。まだ間に合う。 | 傾げ=かしげ | A tilted head means suspicion. You still have time. | 3.6 |
| `auditor.001` | `ai_event:node_dark` · bark, repeatable | 監査官 Auditor | 第一節、応答なし。……記載漏れでしょうか。 | 記載漏れ=きさいもれ | Node one, no response. …An omission in the record? | 4.2 |
| `auditor.002` | `alert_state:suspicious` · bark, repeatable · set `ch06_auditor` (b04, b06, b08, b11) | 監査官 Auditor | ……おや。帳尻が合いませんね。 | 帳尻=ちょうじり | Hm. The figures do not reconcile. | 2.9 |
| `auditor.003` | `ai_event:alarm_run` · bark, repeatable · set `ch06_auditor` (b04, b06, b08, b11) | 監査官 Auditor | 警報を、起票いたします！ | 起票=きひょう | Filing an alarm! | 2.3 |
| `enforcer.001` | `alert_state:suspicious` · bark, repeatable · set `ch06_enforcer` (b03, b04, b06, b08, b11, b14) | 執行兵 Enforcer | 音源、未登録。確認いたします。 | 未登録=みとうろく | Unregistered sound. Verifying. | 3.2 |
| `enforcer.002` | `alert_state:alert` · bark, repeatable · set `ch06_enforcer` (b03, b04, b06, b08, b11, b14) | 執行兵 Enforcer | 延滞者を発見。回収に移ります。 | 延滞者=えんたいしゃ | Delinquent located. Proceeding to collection. | 3.3 |
| `enforcer.003` | `alert_state:search` · bark, repeatable · set `ch06_enforcer` (b03, b04, b06, b08, b11, b14) | 執行兵 Enforcer | 勘定を、再照合いたします。 | 再照合=さいしょうごう | Re-reconciling the count. | 2.6 |
| `enforcer.004` | `alert_state:unaware` · bark, repeatable · set `ch06_enforcer` (b03, b04, b06, b08, b11, b14); set `ch06_moat` (b02) | 執行兵 Enforcer | 誤差として処理いたします。 | 誤差=ごさ | Recording it as a rounding error. | 2.4 |
| `enforcer.005` | `ai_event:retreat` · bark, repeatable · set `ch06_enforcer` (b03, b04, b06, b08, b11, b14) | 執行兵 Enforcer | 損切りいたします。後退。 | 損切り=そんぎり | Cutting losses. Withdrawing. | 2.4 |
| `enforcer.006` | `ai_event:body_found` · bark, repeatable · set `ch06_enforcer` (b03, b04, b06, b08, b11, b14) | 執行兵 Enforcer | 職員一名、未稼働。監査を要請いたします。 | 未稼働=みかどう | One staff member non-performing. Requesting an audit. | 4.4 |
| `kohagi.004` | `beat_complete` · ambient | 小萩 Kohagi | 石板、借りる。水門で帰り道を守る。 | 石板=せきばん | I'll take the slate. I'll hold the gate for the way home. | 3.8 |

#### ch06.b05 · dialogue · 会計補イオタを探せ / Find Junior Auditor Iota

| Line id | Trigger · mode | Speaker | Japanese | Readings | English subtitle | s |
|---|---|---|---|---|---|---|
| `nyaakoto.001` | `interact:crate_iota` · blocking | ニャーコト Nyaakoto | ……イオタ殿か。 |  | …Are you Iota? | 1.5 |
| `iota.001` | `interact:crate_iota` · blocking | イオタ Iota | は、はい。会計補イオタでございます。 | 会計補=かいけいほ | Y-yes. Junior Auditor Iota, at your service. | 3.1 |
| `nyaakoto.002` | `interact:crate_iota` · blocking | ニャーコト Nyaakoto | 箱の中に、いたのか。 |  | You were in the crate? | 1.8 |
| `iota.002` | `interact:crate_iota` · blocking | イオタ Iota | ……大変、快適でございました。 |  | It was… comfortable. | 2.9 |
| `nyaakoto.003` | `lines_done:ch06.b05.iota.002` · ambient | ニャーコト Nyaakoto | なぜ、我らに文を寄こした。 | 文=ふみ | Why did you send us word? | 2.3 |
| `iota.003` | `lines_done:ch06.b05.iota.002` · ambient | イオタ Iota | 計算しました。四百年分。 |  | I ran the numbers. Four hundred years' worth. | 3.0 |
| `iota.004` | `lines_done:ch06.b05.iota.002` · ambient | イオタ Iota | 閉じない帳簿は、帳簿ではございません。……判決でございます。 | 判決=はんけつ | A ledger that never closes is not a ledger. It is a sentence. | 5.4 |
| `iota.005` | `lines_done:ch06.b05.iota.002` · ambient | イオタ Iota | 鍵板様と、護身の針銃を。一度も撃っておりません。 | 鍵板=かぎいた<br>針銃=はりじゅう | The honored key-slate, and my needle gun. Never once fired. | 4.8 |
| `iota.006` | `lines_done:ch06.b05.iota.002` · ambient | イオタ Iota | 金庫番エスクロ様には、目がございません。耳で帳尻を合わせます。 | 金庫番=きんこばん | Vault Warden Eskro has no eyes. He balances the books by ear. | 5.6 |
| `iota.007` | `lines_done:ch06.b05.iota.002` · ambient | イオタ Iota | それと……記録庫の番は土地のお侍様。鷲尾様と申されます。 | 鷲尾=わしお | Also… the archive guard is a local samurai. A Washio. | 5.8 |
| `nyaakoto.004` | `lines_done:ch06.b05.iota.002` · ambient | ニャーコト Nyaakoto | ……虎之介。 |  | …Toranosuke. | 1.5 |
| `iota.008` | `lines_done:ch06.b05.iota.002` · ambient | イオタ Iota | わたくしはここで照合盤を見て、巡回をお知らせいたします。 | 照合盤=しょうごうばん<br>巡回=じゅんかい | I will watch the reconciliation board here and report the patrols. | 4.9 |

#### ch06.b06 · stealth_zone · 帳簿回廊と鶯張りを抜けよ / Cross the ledger aisles and the nightingale floor

| Line id | Trigger · mode | Speaker | Japanese | Readings | English subtitle | s |
|---|---|---|---|---|---|---|
| `iota.001` | `beat_start` · radio | イオタ Iota | 回廊に監査官様が四名、執行兵が二名。棚の上に目録が二機。 | 監査官=かんさかん<br>目録=もくろく | Aisles: four auditors, two enforcers. Two drones over the shelves. | 6.6 |
| `iota.002` | `beat_start` · radio | イオタ Iota | 監査官様は戦えませんが、警報台へ走られます。 | 警報台=けいほうだい | Auditors cannot fight, but they will run for the alarm. | 4.3 |
| `nyaakoto.001` | `volume_enter:vol_rubble_c1` · ambient | ニャーコト Nyaakoto | 石垣の崩れか。……礫になる。 | 礫=つぶて | Broken rampart stone. …These will do for throwing. | 3.4 |
| `kohagi.001` | `volume_enter:vol_rubble_c1` · radio | 小萩 Kohagi | 礫を投げて。音のした方を、あいつら見に行く。 |  | Throw a stone. They'll go and look where it lands. | 4.0 |
| `auditor.001` | `volume_enter:vol_aisle_c2` · ambient | 監査官 Auditor | 会計補イオタ、本日無断欠勤。減給処理いたします。 | 無断欠勤=むだんけっきん<br>減給=げんきゅう | Junior Auditor Iota, absent without notice. Processing a pay cut. | 5.2 |
| `auditor.002` | `volume_enter:vol_aisle_c2` · ambient | 監査官 Auditor | 金庫番様が、今夜はお目覚めです。筆の音も、お控えを。 |  | The Warden is awake tonight. Keep even your brushstrokes quiet. | 5.2 |
| `auditor.003` | `ai_event:lure_heard` · bark, repeatable · set `ch06_auditor` (b04, b06, b08, b11) | 監査官 Auditor | 物音、一件。記録いたします。 |  | One noise. Logging it. | 3.0 |
| `kohagi.002` | `volume_enter:vol_uguisu_entry` · radio | 小萩 Kohagi | 鳴く床。真ん中は鳴る。壁際の端だけ、黙ってる。 |  | A singing floor. The middle chirps. Only the wall edge is silent. | 4.7 |
| `auditor.004` | `ai_event:floor_chirp` · bark, repeatable | 監査官 Auditor | ……鶯？　夜に、でございますか。 | 鶯=うぐいす | …A nightingale? At night? | 2.7 |
| `iota.003` | `volume_enter:vol_sugido` · radio | イオタ Iota | その杉戸の先に、記帳の間と記録庫。……鷲尾様も、そちらに。 | 杉戸=すぎど<br>記帳=きちょう | Past that cedar door: the Registry Hall and the archive. …Washio too. | 6.0 |

#### ch06.b07 · explore_optional · 押収品庫を調べる（任意） / Search the seized-goods store (optional)

| Line id | Trigger · mode | Speaker | Japanese | Readings | English subtitle | s |
|---|---|---|---|---|---|---|
| `iota.001` | `volume_enter:vol_vault_armory` · radio | イオタ Iota | 押収品庫でございます。鍵板様をかざせば、棚が開きます。 | 押収品=おうしゅうひん | The seized-goods store. Raise the key-slate and the lockers open. | 5.1 |
| `nyaakoto.001` | `volume_enter:vol_poi_contraband` · ambient | ニャーコト Nyaakoto | 空紋の扇……子どもの物まで、禁制品か。 | 空紋=そらもん<br>禁制品=きんせいひん | A Sora-mon fan… Even a child's toy is contraband. | 4.0 |
| `nyaakoto.002` | `volume_enter:vol_poi_heirloom_map` · ambient | ニャーコト Nyaakoto | 田右衛門殿の水利絵図……谷へ返す。 | 田右衛門=たえもん<br>水利絵図=すいりえず | Headman Taemon's water-rights map. It goes back to the valley. | 4.2 |
| `nyaakoto.003` | `volume_enter:vol_poi_vista` · ambient | ニャーコト Nyaakoto | 提灯街だけが、温かい色をしている。 |  | Only the Lantern Ward still glows warm. | 3.1 |

#### ch06.b08 · production_task · 三つの帳台で総高を写せ / Copy the totals at three desks

| Line id | Trigger · mode | Speaker | Japanese | Readings | English subtitle | s |
|---|---|---|---|---|---|---|
| `iota.001` | `beat_start` · radio | イオタ Iota | 記帳の間でございます。帳台は三つ。田方、町方、職方。 | 帳台=ちょうだい<br>田方=たかた<br>町方=まちかた<br>職方=しょくかた | The Registry Hall. Three desks: fields, town and crafts. | 5.5 |
| `kohagi.001` | `beat_start` · radio | 小萩 Kohagi | 蝋燭は手で覆って。遅くなるけど、見えにくい。 | 蝋燭=ろうそく | Cup the candle. It's slower, but harder to see. | 4.0 |
| `nyaakoto.001` | `interact:desk_tagata` · ambient | ニャーコト Nyaakoto | 雁皮紙を重ねて、透かし写す。 | 雁皮紙=がんぴし<br>透かし写す=すかしうつす | Thin gampi paper over the page. I trace it through. | 3.4 |
| `iota.002` | `progress_at:0.33` · radio | イオタ Iota | 利率は年五割。夜ごとに、利が付きます。 | 年五割=ねんごわり<br>利=り | The rate is fifty percent a year, added nightly. | 3.9 |
| `iota.003` | `progress_at:0.66` · radio | イオタ Iota | 恐れ入りますが、この帳簿は、閉じない仕様でございます。 | 仕様=しよう | Pardon me, but this ledger is designed never to close. | 4.7 |
| `auditor.001` | `volume_enter:vol_kicho_chudan` · ambient | 監査官 Auditor | 町方帳、本日分の利を加算。……美しい曲線です。 | 加算=かさん | Town ledger: today's interest added. …A beautiful curve. | 5.1 |
| `auditor.002` | `volume_enter:vol_kicho_chudan` · ambient | 監査官 Auditor | 右肩上がりは、秩序の証でございます。 | 右肩上がり=みぎかたあがり<br>証=あかし | A rising line is proof of order. | 3.4 |
| `auditor.003` | `ai_event:light_seen` · bark, repeatable | 監査官 Auditor | ……灯り？　温かい色の灯りは、支給しておりません。 | 支給=しきゅう | …A light? Warm lights are not standard issue. | 4.5 |

#### ch06.b09 · duel · 虎之介と立ち合え / Face Toranosuke

| Line id | Trigger · mode | Speaker | Japanese | Readings | English subtitle | s |
|---|---|---|---|---|---|---|
| `toranosuke.001` | `beat_start` · ambient | 虎之介 Toranosuke | 来ると思っていた。お前は、退くことを知らん。 | 退く=ひく | I knew you would come. You never learned to stay away. | 3.9 |
| `nyaakoto.001` | `beat_start` · ambient | ニャーコト Nyaakoto | 虎之介。そこを退いてくれ。 | 退いて=どいて | Toranosuke. Stand aside. | 2.5 |
| `toranosuke.002` | `beat_start` · ambient | 虎之介 Toranosuke | 退けば、鷲尾の家が潰れる。 | 退けば=ひけば | If I stand aside, the House of Washio falls. | 3.0 |
| `toranosuke.003` | `beat_start` · ambient | 虎之介 Toranosuke | 礼はいい。抜け、ニャーコト。今度は竹じゃない。 |  | Skip the bow. Draw, Nyaakoto. This time it is not bamboo. | 3.9 |
| `toranosuke.004` | `pattern:kesa_combo` · bark, repeatable | 虎之介 Toranosuke | 遅い！ |  | Too slow! | 1.5 |
| `toranosuke.005` | `duel_event:family_page` · blocking | 虎之介 Toranosuke | ……鷲尾家。これは……。 |  | …House of Washio. This is… | 2.6 |
| `nyaakoto.002` | `duel_event:family_page` · blocking | ニャーコト Nyaakoto | 元本百二十石。返済四十石。残高、百九十石。 | 元本=がんぽん<br>石=こく<br>残高=ざんだか | Principal 120 koku. Paid 40. Still owed: 190. | 5.5 |
| `nyaakoto.003` | `duel_event:family_page` · blocking | ニャーコト Nyaakoto | 買取は三十石。……彼らは、三十石で買っている。 | 買取=かいとり | Bought at thirty. …They paid thirty koku for your debt. | 4.9 |
| `toranosuke.006` | `duel_event:family_page` · blocking | 虎之介 Toranosuke | 黙れ！　黙って、構えろ！ | 構えろ=かまえろ | Quiet! Quiet, and take your stance! | 2.4 |
| `sekireisai.001` | `duel_phase:2` · radio, memory voice | 石鈴斎 Sekireisai (memory) | 刀なき時こそ、手の内を見よ。 | 手の内=てのうち | When you have no sword, watch his hands. | 2.7 |
| `sekireisai.002` | `duel_phase:2` · radio, memory voice | 石鈴斎 Sekireisai (memory) | 無刀とは、奪う芸にあらず。斬られぬための心得じゃ。 | 無刀=むとう<br>心得=こころえ | No-sword is not an art of taking. It is how one is not cut. | 4.4 |
| `toranosuke.007` | `ai_event:player_sheathed` · bark | 虎之介 Toranosuke | 刀を納めるだと？　俺を、侮るな！ | 納める=おさめる<br>侮る=あなどる | You sheathe your sword? Do not mock me! | 2.8 |
| `toranosuke.008` | `pattern:makko_giri` · captioned telegraph | 虎之介 Toranosuke | 全部、払ったんだ！ |  | I paid all of it! | 1.8 |
| `toranosuke.009` | `pattern:kiriotoshi_rush` · captioned telegraph | 虎之介 Toranosuke | なのに、なぜ減らん！ |  | Then why will it not shrink?! | 1.8 |
| `toranosuke.010` | `player_died` · blocking, repeatable | 虎之介 Toranosuke | ……立て。こんな終わり方は、させん。 |  | …Get up. I will not let it end like this. | 3.3 |

#### ch06.b10 · dialogue · 誓い / The pledge

| Line id | Trigger · mode | Speaker | Japanese | Readings | English subtitle | s |
|---|---|---|---|---|---|---|
| `toranosuke.001` | `beat_start` · ambient | 虎之介 Toranosuke | 毎月払った。増えた。 |  | I paid every month. It grew. | 2.1 |
| `toranosuke.002` | `beat_start` · ambient | 虎之介 Toranosuke | 払うほど、利が肥える。……俺は、何を守っていた。 | 肥える=こえる | The more I paid, the fatter it grew. …What was I guarding? | 4.5 |
| `nyaakoto.001` | `beat_start` · ambient | ニャーコト Nyaakoto | 刀は、民から預かるものだ。……先生の言葉だ。 | 預かる=あずかる | A blade is held in trust from the people. …Sensei's words. | 4.4 |
| `toranosuke.003` | `beat_start` · ambient | 虎之介 Toranosuke | ……受け取れん。負けた者の刀だ。 |  | …I cannot take it. It is a beaten man's sword. | 3.3 |
| `nyaakoto.002` | `beat_start` · ambient | ニャーコト Nyaakoto | なら、預ける。民のために抜け。 |  | Then I entrust it to you. Draw it for the people. | 3.3 |
| `toranosuke.004` | `lines_done:ch06.b10.nyaakoto.002` · blocking | 虎之介 Toranosuke | これを。鷲尾虎之介、誓いの証だ。 | 証=あかし | Take this. My pledge, as Washio Toranosuke. | 3.4 |
| `nyaakoto.003` | `lines_done:ch06.b10.nyaakoto.002` · blocking | ニャーコト Nyaakoto | 確かに、預かった。 |  | I will hold it in trust. | 1.6 |
| `toranosuke.005` | `lines_done:ch06.b10.nyaakoto.003` · ambient | 虎之介 Toranosuke | この羽織、まだ使える。イオタは俺が水門まで「連行」する。 | 羽織=はおり<br>連行=れんこう | This haori still has its uses. I will 'escort' Iota to the gate. | 4.8 |
| `nyaakoto.004` | `lines_done:ch06.b10.nyaakoto.003` · ambient | ニャーコト Nyaakoto | 印刷所は、私が止める。 |  | I will stop the presses. | 2.3 |
| `toranosuke.006` | `lines_done:ch06.b10.nyaakoto.003` · ambient | 虎之介 Toranosuke | ……死ぬなよ、弟弟子。 | 弟弟子=おとうとでし | …Do not die, little brother. | 2.4 |

#### ch06.b11 · stealth_zone · 親機三台を止めよ / Jam the three master presses

| Line id | Trigger · mode | Speaker | Japanese | Readings | English subtitle | s |
|---|---|---|---|---|---|---|
| `kohagi.001` | `beat_start` · radio | 小萩 Kohagi | 虎之介とイオタ、水門に着いた。 |  | Toranosuke and Iota reached the gate. | 3.0 |
| `iota.001` | `beat_start` · radio | イオタ Iota | 親機は三台。吊られた灯りが目印でございます。 | 親機=おやき | Three master presses. Look for the hanging lamps. | 4.3 |
| `kohagi.002` | `volume_enter:vol_press_floor` · radio | 小萩 Kohagi | 槌が落ちる音に、足音を隠して。 | 槌=つち | Move when the press slams. It hides your steps. | 3.2 |
| `nyaakoto.001` | `interact:press_any_first` · ambient | ニャーコト Nyaakoto | 鋼蔵殿の楔、三本。ちょうどだ。 | 鋼蔵=こうぞう<br>楔=くさび | Kōzō's wedges. Three. Just enough. | 3.0 |
| `auditor.001` | `volume_enter:vol_press_binding` · ambient | 監査官 Auditor | 本日の督促状、四千二百枚。紙が足りません。 | 督促状=とくそくじょう | Dunning notices today: four thousand two hundred. Paper is short. | 4.7 |
| `auditor.002` | `volume_enter:vol_press_binding` · ambient | 監査官 Auditor | 提灯街から、また和紙を差し押さえましょう。 | 差し押さえ=さしおさえ | We will seize more washi from the Lantern Ward. | 3.8 |
| `auditor.003` | `ai_event:press_silent` · bark, repeatable | 監査官 Auditor | 親機、停止。……点検いたします。 | 点検=てんけん | Master press stopped. …Inspecting. | 3.4 |
| `enforcer.001` | `alert_state:alert` · bark, repeatable | 執行兵 Enforcer | 印刷妨害を確認。債務に上乗せいたします。 | 妨害=ぼうがい<br>上乗せ=うわのせ | Press sabotage confirmed. It will be added to your debt. | 4.3 |

#### ch06.b12 · cinematic · 停電 / Blackout

| Line id | Trigger · mode | Speaker | Japanese | Readings | English subtitle | s |
|---|---|---|---|---|---|---|
| `iota.001` | sequence · radio | イオタ Iota | い、いけません。印刷機と金庫核は、同じ流れに—— | 金庫核=きんこかく | N-no. The presses share a current with the vault core— | 4.4 |
| `valamort.001` | sequence · subtitle · **catalog line 2** | ヴァル・アモルト Val Amort (recorded) | 契約は永遠だ。誰も帳簿からは逃れられぬ。 |  | The contract is eternal. No one escapes the ledger. | 4.8 |
| `nyaakoto.001` | sequence · subtitle | ニャーコト Nyaakoto | ……アモルトの声か。 |  | …Amort's voice. | 1.8 |
| `eskro.001` | sequence · subtitle | エスクロ Eskro | 停電を記録。……照合を、開始いたします。 | 照合=しょうごう | Outage recorded. …Commencing reconciliation. | 4.2 |
| `kohagi.001` | sequence · radio | 小萩 Kohagi | ニャーコト、聞こえる？　下は真っ暗—— |  | Nyaakoto, can you hear me? It's pitch black down— | 3.3 |

#### ch06.b13 · boss · 金庫番エスクロを封じよ / Seal away Vault Warden Eskro

| Line id | Trigger · mode | Speaker | Japanese | Readings | English subtitle | s |
|---|---|---|---|---|---|---|
| `kohagi.001` | `beat_start` · radio | 小萩 Kohagi | 目がないなら、音を消して。動くのは、鳴いた後。 |  | It has no eyes. Kill your sound. Move after it chirps. | 4.2 |
| `nyaakoto.001` | `beat_start` · ambient | ニャーコト Nyaakoto | ……見えぬ相手か。なら、灯りは使える。 |  | …He cannot see. Then the flame is safe. | 3.7 |
| `eskro.002` | `pattern:reconcile_pulse` · captioned telegraph, repeatable | エスクロ Eskro | 照合。 |  | Reconciling. | 1.5 |
| `eskro.003` | `pattern:pounce` · captioned telegraph, repeatable | エスクロ Eskro | ……不一致。 | 不一致=ふいっち | …Mismatch. | 1.5 |
| `eskro.004` | `pattern:pounce_miss` · bark, repeatable | エスクロ Eskro | ……誤差。 |  | …A rounding error. | 1.5 |
| `nyaakoto.002` | `pattern:pounce_miss` · ambient | ニャーコト Nyaakoto | 跳んだ後が、隙だ。 | 隙=すき | After the leap, he is open. | 1.8 |
| `eskro.005` | `pattern:claw_flurry` · captioned telegraph, repeatable | エスクロ Eskro | 端数、切り捨て。 | 端数=はすう | Fractions: discarded. | 1.8 |
| `eskro.006` | `boss_phase:2` · captioned telegraph | エスクロ Eskro | 水は、帳尻を誤魔化しません。 | 誤魔化す=ごまかす | Water does not cook the books. | 2.8 |
| `eskro.007` | `pattern:shelf_rake` · captioned telegraph, repeatable | エスクロ Eskro | 棚卸し。 | 棚卸し=たなおろし | Stocktaking. | 1.5 |
| `eskro.008` | `pattern:wade_charge` · captioned telegraph, repeatable | エスクロ Eskro | 取り立て。 | 取り立て=とりたて | Collection. | 1.5 |
| `eskro.009` | `boss_phase:3` · captioned telegraph | エスクロ Eskro | 全件照合。猟犬を、放ちます。 | 猟犬=りょうけん | Full reconciliation. Releasing the hounds. | 3.1 |
| `kohagi.002` | `boss_phase:3` · radio | 小萩 Kohagi | 小さいのが二つ。先に落として。灯りも見られる。 |  | Two small ones. Drop them first. They can see your flame. | 4.3 |
| `eskro.010` | `ai_event:boss_hp_zero` · subtitle | エスクロ Eskro | ……照合、不能。 | 不能=ふのう | …Unable to reconcile. | 2.0 |
| `nyaakoto.003` | `interact:bulkhead_lever` · subtitle | ニャーコト Nyaakoto | その帳簿は、ここで閉じる。 |  | This ledger closes here. | 2.3 |

#### ch06.b14 · stealth_zone · 満ちる暗渠を抜けよ / Escape through the flooding culvert

| Line id | Trigger · mode | Speaker | Japanese | Readings | English subtitle | s |
|---|---|---|---|---|---|---|
| `toranosuke.001` | `volume_enter:vol_ankyo_start` · ambient | 虎之介 Toranosuke | 遅いぞ。水が上がってる。 |  | You are late. The water is rising. | 2.3 |
| `iota.001` | `volume_enter:vol_ankyo_start` · ambient | イオタ Iota | わたくし、泳いだことが……ございません。 |  | I have never… swum before. | 3.2 |
| `toranosuke.002` | `volume_enter:vol_ankyo_start` · ambient | 虎之介 Toranosuke | 背に乗れ。しっかり掴まってろ。 | 掴まって=つかまって | Get on my back. Hold on tight. | 2.7 |
| `kohagi.001` | `volume_enter:vol_ankyo_grate_1` · radio | 小萩 Kohagi | 水門、半分まで上げた。これ以上は音が出る。 |  | Gate's half up. Any higher and it'll make noise. | 4.3 |
| `enforcer.001` | `volume_enter:vol_ankyo_grate_1` · ambient | 執行兵 Enforcer | 停電につき、手作業で捜索いたします。 | 捜索=そうさく | Owing to the outage, we are searching by hand. | 3.5 |
| `nyaakoto.001` | `volume_enter:vol_ankyo_deep` · ambient | ニャーコト Nyaakoto | ここから潜る。八つ、数えろ。 |  | We dive from here. Count to eight. | 2.6 |
| `kohagi.002` | `volume_enter:vol_water_gate_exit` · radio | 小萩 Kohagi | 抜けた。舟は葦の陰。右に灯りの舟が一艘。 | 葦=あし<br>一艘=いっそう | You're out. Our boat's in the reeds. A lamp boat to the right. | 4.3 |

#### ch06.b15 · dialogue · 数字を読む / Reading the numbers

| Line id | Trigger · mode | Speaker | Japanese | Readings | English subtitle | s |
|---|---|---|---|---|---|---|
| `oyuki.001` | `beat_start` · ambient | お雪 Oyuki | お帰りなさいませ。……写しを、拝見いたします。 | 拝見=はいけん | Welcome back. …May I see the copies? | 4.1 |
| `oyuki.002` | `beat_start` · ambient | お雪 Oyuki | 元本、一万八千石。年五割。期限は十四年。 | 元本=がんぽん<br>石=こく | Principal: eighteen thousand koku. Fifty percent a year. Fourteen years. | 5.1 |
| `oyuki.003` | `beat_start` · ambient | お雪 Oyuki | 期限の日には五百二十五万石。谷の、四百年分でございます。 |  | At term: 5.25 million koku. Four hundred years of our valley. | 6.0 |
| `iota.001` | `beat_start` · ambient | イオタ Iota | わたくしの計算と、一致いたしました。 |  | That matches my calculation. | 3.1 |
| `toranosuke.001` | `beat_start` · ambient | 虎之介 Toranosuke | ……俺の家の分も、そこに入っているのか。 |  | …My house's page is in there too? | 3.6 |
| `oyuki.004` | `beat_start` · ambient | お雪 Oyuki | はい。皆の分が。だから、皆の前に貼るのです。 | 貼る=はる | Yes. Everyone's is. That is why we post it before everyone. | 4.0 |
| `nyaakoto.001` | `beat_start` · ambient · **catalog line 3** | ニャーコト Nyaakoto | 人を縛る文字より、人が作る明日を選ぶ。 |  | I choose the future people build over the words that bind them. | 4.8 |

#### ch06.b16 · cinematic · 帳は民の前に / The ledger before the people

| Line id | Trigger · mode | Speaker | Japanese | Readings | English subtitle | s |
|---|---|---|---|---|---|---|
| `resident.001` | sequence · subtitle | 町の衆 Resident | ……うちの借り、元はたった二俵やで。 | 俵=ひょう | …Our debt started at just two bales. | 3.3 |
| `resident.002` | sequence · subtitle | 町の衆 Resident | 字ぃ読めへん。誰か、読んでくれ。 |  | I can't read. Someone read it for me. | 2.8 |
| `tokichi.001` | sequence · subtitle | 灯吉 Tōkichi | どれ、わしが読もう。……おまえさんの家は、ここや。 |  | Here, let me read it. …Your house is this line. | 4.1 |
| `oyuki.001` | sequence · subtitle | お雪 Oyuki | 帳は、民の前に。五箇条の五でございます。 | 帳=ちょう<br>五箇条=ごかじょう | The ledger belongs before the people. Article five. | 3.9 |
| `tetsugoro.001` | sequence · subtitle | 鉄五郎 Tetsugorō | ええ鉄や。鍬になる。 | 鍬=くわ | Good iron. It'll make hoes. | 1.9 |
| `toranosuke.001` | sequence · subtitle | 虎之介 Toranosuke | 旗艦だ。谷の物を、あれに積んでいる。 | 旗艦=きかん | The flagship. They are loading the valley's goods onto it. | 3.8 |
| `nyaakoto.001` | sequence · subtitle | ニャーコト Nyaakoto | なら、取り返しに行く。 |  | Then we go and take them back. | 2.0 |


---

## 4. Historical and cultural accuracy notes

These are working notes for the historian and practitioner review (bible §20, open item 2). Sources are starting points to verify, not settled citations.

### 4.1 Kenjutsu and the duel

- **無刀取り (mutō-dori).** Tradition holds that 柳生石舟斎宗厳 demonstrated taking a sword barehanded before Tokugawa Ieyasu in 文禄三年 (1594). His son 柳生宗矩 discusses 無刀 in 『兵法家伝書』 (1632): it is **not** a trick for snatching swords but the ability not to be cut when you have no blade, and to use whatever is at hand (source: 『兵法家伝書 付・新陰流兵法目録事』, 渡辺一郎校注, 岩波文庫, 1985).
  - The game depicts it as **entering inside the cut and controlling the hands and hilt**, never the theatrical palm-clap on the blade (真剣白刃取り), which is a later dramatic image.
  - Sekireisai's lines and ch06.c05 paraphrase the idea in original words. They do **not** quote the text or reproduce any named kata of the living school (bible §3.1).
- **Technique vocabulary** is general period sword language, not school kata: 袈裟 (diagonal cut), 真っ向 (vertical cut), 諸手突き (two-handed thrust), 上段 (overhead guard), 体当たり, 斬り落とし. The duel's names are descriptive labels for readable game attacks, not claims about any curriculum.
- **納刀 (sheathing)** is animated in full, as bible §4.1 requires. The katana is worn edge-up in the obi; the left paw controls the 鯉口 (scabbard mouth) while the right returns the blade along the saya. This needs a motion reviewer for the cat hands.
- **Passing a blade.** Nyaakoto returns Toranosuke's katana hilt-first with the edge turned toward himself; Toranosuke offers his tantō the same way. Toranosuke kneels on one knee in partial armor. Formal 正座 as the standard samurai posture is more characteristic of later Edo, so a kneel or 蹲踞 is safer for 1623.
- **Toranosuke's tantō** is a 鎧通し, a thick-backed armor-piercing tantō worn **馬手差し** on the right hip with armor. That is period-appropriate for a guard captain in 小具足 (partial armor) and explains why he carries one.
- **Real steel against the ch01 bout.** "This time it is not bamboo" refers to the 袋竹刀 of ch01.b11 (bible §4.1).

### 4.2 Archery, thrown stones and firearms

- **The bowstring.** Traditional strings are hemp (麻弦) dressed with くすね, a pine-resin paste. Keeping the string dry on a swim and stringing the yumi afterwards is sound practice; spares were carried on a 弦巻 string reel. The stringing animation should brace the lower limb against the foot and bend the bow as a kyūdō stringing does; the All Japan Kyudo Federation materials cited in [historical-arms.md](../historical-arms.md) are the reference.
- **Tsubute (礫).** Stone-throwing was a real practice: 印地打ち, the stone fights of medieval festivals, and stones used in warfare. Thrown stones as lures are a game mechanic, but the prop and throw should look like a real stone and a short overhand throw, not a ninja gadget. Source: 日本大百科全書「印地打」.
- **No matchlocks on this mission.** Bible §4.4 notes that rain and damp spoil a matchlock's reliability; a moat swim would ruin the powder, and the report would wake the castle. This justifies the empty firearm slot until Iota's needle gun.

### 4.3 Castle architecture (early 17th century)

- **打込接ぎ with 算木積み corners** is typical of castle walls of the 慶長 era (1596–1615): dressed long stones alternating faces at the corners, with the fan-shaped curve (扇の勾配) that steepens toward the top. Kumamoto Castle's 武者返し walls are the famous example. Climbing a real 石垣 was hard, so the game keeps the climb to authored corner holds (source: 三浦正幸『城のつくり方図典』小学館, 2005, for 石垣, 石落とし, 狭間, 櫓 and 帯曲輪 terms).
- **Other castle elements.** 石落とし (projecting stone-drop bays on turrets), 狭間 loopholes in 土塀, 隅櫓, 帯曲輪 terraces, and 水門 / 船入 water gates and basins all fit a castle of this period.
- **Assumption to verify.** The stone culvert (暗渠) from the keep's drainage to the water gate is plausible but specific to our layout. The historian should confirm that a 船入 on a 帯曲輪 is credible for a hilltop castle with a wet moat, or suggest a drainage alternative.
- **Nightingale floor (鶯張り).** The best-known example is the Ninomaru Palace of 二条城 (built 1603, much extended 1626; [official site](https://nijo-jocastle.city.kyoto.lg.jp/)). The chirp comes from the clamps (目かすがい) rubbing against their nails as the boards flex. **Many scholars think the sound was a by-product of construction rather than a designed alarm; the security story is popular tradition.** The game uses the popular reading on purpose, and the codex should say so. The silent edge strip, where boards rest on a sleeper, is a gameplay simplification.
- **Shoin audience hall.** The 上段 / 中段 / 下段 stepped levels, 床の間, 違い棚, 付書院, 帳台構え (the ornamental door, whose name is a happy echo of 帳), 格天井 coffered ceiling and gold-ground fusuma follow early-Edo palace halls such as Nijō's. Do not copy identifiable Kanō-school paintings; the shrouded panels must be original designs.
- **Crests on the palace.** The Nekoyama palace is not the Nyaagyu house's. Its nail covers (釘隠し) use a generic 六葉 design, and its eave tiles use the generic 三つ巴. The SORA mon must not appear on castle fabric (§4.6).

### 4.4 Paper, lighting and records

- **Tracing on 雁皮紙.** Thin, strong, translucent gampi paper (薄様) was used to copy text and images by tracing (透き写し). It is period-appropriate and explains why the copy needs a light behind the page. Source: 日本大百科全書「雁皮紙」.
- **Candle.** A 手燭 (handheld candlestick) with a 和蝋燭 (sumac-wax candle, 木蝋). The hollow paper-and-rush wick gives a large, swaying flame, which is visually distinctive and a good VFX reference. Candles were costly, so a League candle is a deliberate expense.
- **Units.** 石 (koku) for rice-equivalent value; 俵 (bales); 冊 for bound volumes. The copies are 和綴じ thread-bound volumes. Alien ledgers show alien numerals with a translation overlay in-world, never Arabic numerals on League props.
- **高札 and 張札.** Official 高札 were wooden boards with ink text. The League **pastes paper sheets (張札) onto the kōsatsu frame**, which subverts the official medium. Pasting in the art should show the paste pot and broad brush.
- **夏越の祓.** The summer purification on the last day of the sixth month, with a 茅の輪 reed ring, is a long-attested shrine rite. That fixes the chapter's night and is optional dressing in b16.
- **Literacy.** The townsman who cannot read and Tōkichi reading for him reflect uneven commoner literacy in 1623. Terakoya schooling spread later.

### 4.5 Clothing and characters

- **Infiltration dress, not a ninja suit.** Nyaakoto and Kohagi wear indigo or persimmon-tannin (柿渋) work clothes, 手甲, 脚絆 and head cloths, following bible §4.6 and §19. The all-black theatrical costume must not be used.
- **Toranosuke** wears 籠手, 佩楯 and 臑当 (partial armor) under the grey Credit House haori. His black-lacquer, scarlet-laced armor from the bible is left behind for this guard duty; the haori is the costume point.
- **Swimming.** Samurai swimming (水練; the later 日本泳法 schools) was a practised skill. Use a quiet, head-up breaststroke-like stroke and a scissor kick, not a modern crawl. Source: 日本水泳連盟 日本泳法 materials, for the stroke look.

### 4.6 The SORA kamon in this chapter

| Surface | Beat | Treatment |
|---|---|---|
| League mark at the water gate | b02 | Small chalk SORA mon by Kohagi, beside a water-level gauge (collectible ch06.c01) |
| Contraband crate | b07 | Confiscated SORA-mon items (a child's paper fan, a 手拭い, chalk) tagged with the **alien ledger sigil**. Aliens never display the mon; they only seize it. |
| Copied ledger volumes | b15 | Oyuki stamps each cover with the vermillion SORA seal (朱印) |
| Posted sheets on the kōsatsu | b16 | Every 張札 carries the vermillion seal; SORA-mon lanterns (from ch03) hang around the square |
| UI | all | Small mon objective marker, rotating-mon save indicator, and the chapter title card's vermillion seal beside the brush title 「第六章 債務金庫への潜入」 |
| **Not used** | — | Not on Nyaakoto's infiltration dress (deliberately unmarked for stealth), not on castle fabric (§4.3), and not on any alien object or UI |

All placements use the exact SVG from `Content/SourceArt/UI/sora_logo_NOtext2.svg` (SHA-256 `d66413a7…0910`), imported from its two original paths and never redrawn ([SORA kamon runtime art](../sora-kamon-runtime-art.md)).

---

## 5. Art and audio asset list

Status key: **Existing** means it is in `Content/SourceArt` or `catalog.json` and can be reused (still subject to the photoreal gates). **Study** means a source study exists that has not passed a gate. **Placeholder** means a primitive or prototype exists that needs replacing. **Needed** means nothing usable exists. Every asset must pass [photoreal acceptance](../art-direction/photoreal-acceptance.md): a packaged fixed-camera A/B comparison, a recorded license, and frame cost on both platforms.

### 5.1 Environment kits (C3 unless noted)

| Asset | Status | Source / notes |
|---|---|---|
| Moat water, reeds, lotus beds, willow | Needed | Water material with fog-scattered searchlight reflections; lotus cards; PolyHaven `Fern02` and `TreeSmall02` are existing CC0 references for foliage shading only |
| 打込接ぎ 石垣 kit: blocks, 算木積み corner stones, 腰巻 low wall, 扇の勾配 curve modules, climb-hold decals | Needed | Use the existing `NyaagyuEstateWall/ScanRock01` scan and PolyHaven `stone_floor` as granite references; authored hold stones are needed |
| 土塀 with 狭間 | Existing (adapt) | `Environment/NyaagyuEstateWall/SM_Nyaagyu_EstateWall_4m.fbx`; add loophole modules and wetness |
| 水門 gate and grille, 船入 basin, stone culvert with grates | Needed | Iron-strapped timber; the grille's unfastened lower section is a hero detail |
| 隅櫓 turret kit: plaster, 下見板, 連子窓, 石落とし bay, 梯子段 | Needed | Roof uses the existing `NyaagyuKawaraBay` ibushi kawara textures (`T_NyaagyuIbushi_*`); eave tiles use a **generic 三つ巴**, not `NyaagyuSoraEaveCapStudy` |
| Alien spire graft: graphite extrusions, black glass, cyan ledger strips | Needed | Must read as extruded and seamless against hand-laid stone |
| Relay column with nodes and scan fan | Needed | Hero prop |
| Vault kit: ledger-slate shelves, cross-aisles, basalt floor, slate carts, dead-slate gaps | Needed | Data-driven emissive numeral material |
| Alarm lectern (警報台) | Existing (adapt) | Derive from `Environment/Original/SM_Alien_DebtKiosk.fbx` |
| Palace kit: nightingale corridor (縁側, sleeper edge), 杉戸, fusuma with shroud sheeting, shoin hall (上段/中段/下段, 床の間, 帳台構え, 格天井), tatami stacks, 釘隠し 六葉 | Needed | Timber can start from the dojo's 欅/檜 (`Environment/NyaagyuDojo`); shōji from `ShojiPaperArtReview` (currently failing its fibre-repeat gate) |
| Inner garden: raked gravel, stones, pine, stone lantern, 蹲踞 | Needed / Existing (adapt) | Basin water: `NyaagyuWaterCourt` / `BambooRill`; pine from the `PineSaplingSmall` scan is too young, so a mature pine is needed |
| Archive: slate racks, 箪笥, exposed beams | Needed | |
| Press hall: 8 alien presses (3 master variants with die lamps), washi bales, drying racks, conveyor, binding table, catwalk, freight lift | Needed | |
| Vault core: domed chamber, column, 8 shelf blocks, drains, bulkhead | Needed | |
| Arena 3 (Debt Citadel) exterior | Placeholder | Currently engine primitives (completion map §1); C2 owns it |
| Lantern Ward square and kōsatsu board | Existing (Arena 1) / Needed (board) | Arena 1 exists as a blockout; `StreetDebtTerminal` exists (burnt variant needed); the 高札 board and 張札 sheets are needed |
| Texture palette | Existing | PolyHaven CC0: `wood_planks_dirt`, `stone_floor`, `WhitePlaster02`, `GreyRoofTiles`, `rusty_metal_02`, `brown_mud_leaves_01` |

### 5.2 Props

| Asset | Status | Notes |
|---|---|---|
| Iota's document crate (「保存期限：永久」) and seized-deed crates | Existing (adapt) / Needed | Crates can derive from `NyaagyuCargoStack`; the stencil is needed |
| Key-slate and twin message slate | Needed | Alien handheld; cyan is allowed (alien object) |
| 手燭 with 和蝋燭 | Needed | Hero warm light; placeable in b13 |
| 雁皮紙 sheets; three 和綴じ copied volumes; master ledgers on 見台 stands | Needed | |
| Kōzō's iron wedges ×3; die plates (刻印版) ×3 | Needed | The die plates reappear in b16 |
| Seized 半鐘 bells (stacks, loose clappers) | Needed | |
| Contraband: SORA-mon paper fan, 手拭い, chalk; alien ledger-sigil tags | Needed | Uses the exact SVG |
| Heirlooms: water-rights map scroll, boxwood shuttle | Needed | Epilogue re-use |
| Rubble piles (tsubute) and a throwable stone | Needed | |
| 田舟 (League), 小舟 (seized), charred bridge pilings | Needed | |
| 鷲尾家 ledger slate with readable balance | Needed | Text from §2.6 |
| Toranosuke's katana and 鎧通し tantō | Placeholder | `SM_Weapon_10.fbx` (tantō) is primitive; the katana can reuse the `HeroKatana` pipeline as a variant |
| Needle SMG (3), Phantom SMG (13) | Placeholder | `SM_Weapon_03.fbx` and `SM_Weapon_13.fbx` are primitives; C5 owns them |
| Yumi, katana, saya | Existing (study) | `Weapons/NyaagyuYumi`, `Weapons/HeroKatana`, `SM_Nyaagyu_HeroSaya.fbx` |

### 5.3 Characters

| Character | Status | Notes |
|---|---|---|
| Nyaakoto: infiltration costume (柿渋 / 紺, 手甲, 脚絆), **wet-fur state** | Study / Needed | Base: `Characters/Hero` (runtime skin), `NyaakotoFirstPersonPaws` (katana and yumi grip studies). The costume and the wet and drying fur states are needed; first-person paws need 手甲 |
| Kohagi (swim-ready peddler dress) | Needed | |
| Oyuki, Tōkichi, Tetsugorō | Needed | Shared with other chapters |
| Toranosuke (小具足 plus grey haori) | Needed | Shared ch01–ch08 |
| Iota | Needed | Small, lavender-grey, big ears, oversized ocular, suit a size too large |
| Eskro | Needed | Eyeless face with sensor ridges, long arms and claws, vault robes. Unsettling, not gory |
| `enforcer_rifle`, `auditor` (slate and lamp), `drone` plus the audit-hound variant | Placeholder | `SK_AlienBanker.fbx` is a prototype rig and body; the enemy kits are needed |
| Townsfolk crowd (about 8 variants), League scribes | Needed | Shared with ch03 and ch08 |

### 5.4 Animation

| Set | Status |
|---|---|
| Player: surface swim, dive, surface-breath gasp; climb reach, shimmy, rest and fall; crouch-walk and edge walk; tsubute pick-up and throw; non-lethal rear takedown (当て身); drag body; candle cup and set down; tracing loop; node pull; wedge drive and die pull; stringing the yumi; **納刀 sheathe**; **mutō-dori** success and fail | Needed |
| Toranosuke: P1 set (袈裟連撃, 諸手突き, 見せ上段, 体当たり), P2 set (真っ向, 斬り落とし rush, 二段), hit reacts, disarmed, one-knee pledge, carrying Iota | Needed. Practitioner review is required (bible §3.1) |
| Eskro: listen, pulse chirp, pounce (windup, leap, land, stuck), claw flurry, shelf rake, wade charge, stagger, collapse into the sump | Needed |
| Iota: curled in the crate, emerge, carried on a back; enemies: patrol, look-down, investigate, search, alarm run, retreat | Needed (enemy locomotion can start from `A_AlienBanker_Walk.fbx`, a prototype) |

### 5.5 VFX (C8)

Moat fog with volumetric searchlight shafts · water surface ripples, splash and bubbles · wet-fur drips · drone scan cone · relay scan fan (cyan plane) · slate numeral emissives · breath vapour and condensation · candle flame (large swaying 和蝋燭 flame, light flicker) · Eskro's refractive pulse ring · pounce dust and claw sparks on basalt · flood water rising and wading wakes · audit-hound chirp ring · press stamp dust and paper puffs · blackout cascade · culvert water surge · dawn haze · the flagship's moving shadow. All flashes respect the flash-reduction setting.

### 5.6 SFX (L5; CC0 or original, per the audio plan)

Late-summer night ambience (insects such as bell crickets, frogs, distant water) · fog drips · swim strokes above and under water, bubbles, breath · searchlight hum · float-line alien chime · stone scrape and grip on the wall · turret creak · relay hum, node pull, fan whoosh · **nightingale-floor chirps** (synthesised or recorded with permission; must be distinct from real birdsong) · gravel, tatami and fusuma slides · tsubute throw and impacts on stone, wood and glass · auditor slate taps · alien alarm chime and lockdown shutter · **press stamps every 1.6 s** · paper rustle, wedge hammer, die pull · power-down blackout · Eskro chirp (700 ms rising), pounce, claws on basalt · flood gush · hound chirps · bulkhead slam · culvert roar · gate windlass · dawn cicadas (ヒグラシ) and crows · crowd murmur · paste brush on paper.

### 5.7 Music cues (L5 stem states)

| State id | Beats | Direction |
|---|---|---|
| `ch06_briefing` | b01 | Low shakuhachi breath over a cold synth drone; ends on the humor beat with a held silence |
| `ch06_moat_stealth` | b02–b03 | Sparse: water-drum pulses; tension stem rises with suspicion |
| `ch06_vault_stealth` | b04, b06–b07 | Four stems for unaware / suspicious / alert / search; alert adds taiko; search is a ticking figure |
| `ch06_iota` | b05 | A small, earnest motif: koto with a glassy alien bell. Iota's theme returns in ch07 |
| `ch06_copy` | b08 | Slow koto ostinato that pauses whenever copying pauses (driven by progress) |
| `ch06_duel_toranosuke` | b09 | Taiko and shinobue. The P1 stem is driving; the family-page stinger cuts to silence; the P2 stem is broken and desperate; mutō-dori resolves on one struck bell |
| `ch06_pledge` | b10 | Solo shakuhachi |
| `ch06_press` | b11 | Percussion **locked to the press period (1.6 s, 75 BPM two-beat)** so the player can move on the beat |
| `ch06_boss_eskro_intro` / `ch06_boss_eskro` | b12–b13 | Near silence. Percussion hits only on pulses. P2 adds water textures; P3 a frantic high string |
| `ch06_exfil` | b14 | Rising water drone; tension stem |
| `ch06_numbers` | b15 | Quiet koto |
| `ch06_dawn_kosatsu` | b16 | Hopeful, then a low brass stinger as the flagship's shadow passes |

---

## 6. Data hand-off notes

- **L1 (catalog schema 4).**
  - ch06 sites map 0 → b04, 1 → b08, 2 → b11, and the existing `requires_sites` chain ([] → [0] → [1]) already matches. No renumbering is needed, unlike ch08.
  - The schema-3 values `kills: 14` and `requires_kills` 3/8/14 should be dropped or set to 0 for ch06: the chapter supports a no-kill run, and freeing records is not a kill quota.
  - The catalog's ch06 `narrative` and `objective` still read well as the chapter card.
  - Anchor lines: 1 → `ch06.b01.kohagi.001`, 2 → `ch06.b12.valamort.001`, 3 → `ch06.b15.nyaakoto.001`. Their `start_s` values are replaced by event triggers.
- **Schema proposals raised by this chapter** (flagged so the validator can decide). In the YAML every beat-level proposal below carries the `x_` prefix (`x_traversal`, `x_sensors`, `x_muto`, `x_boss_hp` …), and chapter-level blocks are `x_stealth_defaults`, `x_bark_sets` and `x_pattern_tables` (bible §12.5):
  - Stealth parameters: `traversal` (swim / climb / wade_swim), `sensors[]` (searchlight, float line, rotating scan), `light_carried`, `noise_mask`, `hazard` (rising water), `bodies`, `alarm_points`, and `allies[].detectable`.
  - Duel parameters: `pattern_tables`, `hp_floor_pct`, `muto{}`, `events[].checkpoint`, `checkpoint_per_phase`.
  - Boss parameters: `defeat_interact` and `boss_hp`.
  - Dialogue events: `ai_event:<name>`, `interact:<id>`, `lines_done:<line id>`, `duel_event:<id>`, `duel_phase:<n>`, `pattern:<id>` (already used in the bible's §12.4 example), and `seq` for cinematic subtitles.
  - Mechanic flags `swim` and `climb` are not in the §12.1 list. This chapter teaches them without a flag; add them if L4's tutorial log needs them.
  - **Checkpoint validation** (rule 8) must count per-phase checkpoints inside b09 (420 s over 2 phases) and b13 (420 s over 3 phases), as it must for the ch08 finale.
- **L2:** the detection tables in §1.2, the `auditor` alarm-run behaviour, and `drone` variant `audit_hound`. No `bound_conscript` appears in ch06: the vault is staffed by aliens.
- **L3:** `toranosuke_steel_p1/p2` and `eskro_hunt/flood/frenzy` (§2.3 and YAML). `muto_eligible` appears only in the b09 duel, whose `finisher` allows it (rule 4).
- **L4:** 19 HUD prompts (§2.5); the sheathe input; the candle-cup input; AI-state marks above heads. Captions for all telegraphs are required.
- **L5:** 13 music states (§5.7); 3 bark sets (`ch06_enforcer`, `ch06_auditor`, `ch06_moat`) plus beat-specific barks.
- **C9:** sequences `LS_Ch06_B01_MoatBriefing`, `LS_Ch06_B09_FamilyPage`, `LS_Ch06_B12_Blackout`, `LS_Ch06_B13_Sealed`, `LS_Ch06_B16_KosatsuDawn`.
- **Cross-chapter continuity.**
  - ch07.b01 auto-grants weapon 13 if b07 was skipped.
  - ch07.b09 has Iota on the slate; the twin slates set up here are that channel.
  - Toranosuke's riders (ch07) are his house's retainers, freed by the page he read.
  - ch08.b07–b08 find Sekireisai where ch06.c06 said he was.
  - Tetsugorō's hoes from the die plates can appear as dressing at the ch08 field forge.

---

## 7. Machine-readable beat data (YAML)

This is generated from the same source as the tables above and checked by a round-trip parse. Lines are referenced by id from each beat's `dialogue`, `subtitles`, `barks` or `bark_sets`.

```yaml
chapter: "ch06_ledger_vault"
schema: "catalog schema 4 proposal (L1); units cm / ms / s as named"
title_ja: "債務金庫への潜入"
title_en: "Ledger-Vault Infiltration"
map: 3
maps_also: [1]
target_s: 3300
mix_min: {C: 14, E: 3, S: 24, P: 4, M: 0, Cin: 10}
start_loadout: {hip: 0, side: 4, back: 18, back_strung_at: "ch06.b03", polearm: null, firearm: null, quiver_arrows: 12, armor: "none_infiltration_dress"}
x_stealth_defaults:
  detection: {suspicion_rate: 1.0, suspicious_at: 0.35, alert_threshold: 1.0, search_s: 25}
  player_noise_cm:
    sprint: 1500
    walk: 600
    crouch_walk: 250
    still: 0
    swim_surface: 500
    dive: 0
    tsubute_impact: 1400
    needle_smg_shot: 1500
    yumi_release: 300
    takedown: 300
    fusuma_slide: 400
  surface_mult: {puddle: 1.5, gravel: 1.5, tatami: 0.5, running_water: 0.5, wading: 2.0}
  nightingale_floor_cm: {walk: 1800, crouch_walk: 900, edge_strip_crouch: 0}
  visibility_mult: {dark: 0.4, cyan_slate_light: 1.0, candle_lit: 2.0, candle_cupped: 1.2}
  difficulty: {easy: {suspicion_rate_mult: 0.7, search_s_mult: 0.8, on_detected: "combat"}, hard: {suspicion_rate_mult: 1.25, search_s_mult: 1.2}}
  takedowns: {rear: true, lethal_default: false}
  kills_required: 0
sites:
  - {site: 0, beat: "ch06.b04", catalog_name: "監視の中継器", requires_sites: []}
  - {site: 1, beat: "ch06.b08", catalog_name: "債務の帳簿", requires_sites: [0]}
  - {site: 2, beat: "ch06.b11", catalog_name: "金庫の印刷機", requires_sites: [1]}
catalog_anchor_lines: [{index: 1, line: "ch06.b01.kohagi.001"}, {index: 2, line: "ch06.b12.valamort.001"}, {index: 3, line: "ch06.b15.nyaakoto.001"}]
speakers_proposed: [{id: "enforcer", ja: "執行兵", en: "Enforcer"}, {id: "auditor", ja: "監査官", en: "Auditor"}, {id: "resident", ja: "町の衆", en: "Resident"}]
x_event_proposals: ["ai_event:<name>", "interact:<id>", "lines_done:<line id>", "duel_event:<id>", "duel_phase:<n>", "pattern:<id>", "seq"]
beats:
  - id: "ch06.b01"
    type: "cinematic"
    place: "pl_citadel_moat"
    title_ja: "燃やさず、写せ"
    title_en: "Copy it. Do not burn it."
    target_s: 120
    checkpoint: true
    sequence: "/Game/Campaign/Ch06/Sequences/LS_Ch06_B01_MoatBriefing"
    duration_s: 110
    skippable: true
    fallback: "camera_blend"
    end_state: {player_transform: "ps_moat_reeds", equipped: "swim_stowed"}
    music: "ch06_briefing"
    subtitles:
      - "ch06.b01.iota.001"
      - "ch06.b01.kohagi.001"
      - "ch06.b01.oyuki.001"
      - "ch06.b01.nyaakoto.001"
      - "ch06.b01.oyuki.002"
      - "ch06.b01.oyuki.003"
      - "ch06.b01.oyuki.004"
      - "ch06.b01.kohagi.002"
      - "ch06.b01.kohagi.003"
      - "ch06.b01.nyaakoto.002"
  - id: "ch06.b02"
    type: "stealth_zone"
    place: "pl_citadel_moat"
    title_ja: "堀を泳ぎ、旧水門へ"
    title_en: "Swim the moat to the old water gate"
    target_s: 240
    checkpoint: true
    zone: "vol_moat_stealth"
    x_traversal:
      mode: "swim"
      surface_speed_cm_s: 180
      dive_speed_cm_s: 140
      dive_max_s: 8
      breath_recover_s: 3
      drown_dps: 10
      surface_noise_cm: 500
      dive_noise_cm: 0
      weapons_usable: false
    guards:
      - id: "g_moat_parapet_a"
        type: "enforcer_rifle"
        patrol: "spl_moat_parapet_a"
        sight: {cone_deg: 90, range_cm: 3500, dark_range_cm: 1200}
        hearing_cm: 1200
      - id: "g_moat_parapet_b"
        type: "enforcer_rifle"
        patrol: "spl_moat_parapet_b"
        sight: {cone_deg: 90, range_cm: 3500, dark_range_cm: 1200}
        hearing_cm: 1200
      - {id: "g_moat_drone", type: "drone", patrol: "spl_moat_drone_fig8", sight: {cone_deg: 50, range_cm: 1200, dark_range_cm: 1000}, hearing_cm: 600}
    x_sensors:
      - id: "s_searchlight_1"
        kind: "searchlight"
        mount: "yagura_s1"
        sweep_deg: 70
        period_s: 10
        spot_radius_cm: 400
        suspicious_after_s: 0.5
        alert_after_s: 1.5
      - id: "s_searchlight_2"
        kind: "searchlight"
        mount: "yagura_s2"
        sweep_deg: 70
        period_s: 10
        spot_radius_cm: 400
        suspicious_after_s: 0.5
        alert_after_s: 1.5
      - {id: "s_float_line", kind: "float_line", volume: "vol_moat_boom", touch_noise_cm: 1400, clear_depth_cm: 80}
    x_cover: ["vol_moat_reeds", "vol_moat_lotus_1", "vol_moat_lotus_2", "vol_moat_lotus_3", "vol_moat_pilings", "vol_moat_boats"]
    detection: {suspicion_rate: 0.8, suspicious_at: 0.35, alert_threshold: 1.0, search_s: 20}
    noise_surfaces: [{kind: "water_swim", volume: "vol_moat_stealth"}]
    on_detected: "reinforce:w_moat_alarm"
    waves:
      - id: "w_moat_alarm"
        trigger: "alert_state:alert"
        enemies: [{type: "enforcer_rifle", count: 2, spawn: "sp_moat_parapet_c"}]
        effects: ["searchlights_lock_last_seen_6s", "drone_descend_to_300cm"]
    complete: "exit_reached"
    x_exit: "vol_water_gate_inner"
    allies: [{npc: "npc_kohagi", role: "swim_lead", detectable: false}]
    music: "ch06_moat_stealth"
    fail: {"on": "player_died", to: "checkpoint"}
    dialogue:
      - {"on": "beat_start", mode: "ambient", lines: ["ch06.b02.kohagi.001"]}
      - {"on": "volume_enter:vol_moat_pilings", mode: "radio", lines: ["ch06.b02.iota.001"]}
      - {"on": "volume_enter:vol_moat_boom", mode: "ambient", lines: ["ch06.b02.kohagi.002"]}
      - {"on": "volume_enter:vol_moat_wallbase", mode: "ambient", lines: ["ch06.b02.kohagi.003"]}
    x_bark_sets: ["ch06_moat"]
  - id: "ch06.b03"
    type: "stealth_zone"
    place: "pl_ishigaki"
    title_ja: "算木積みの隅を登れ"
    title_en: "Climb the corner stones"
    target_s: 180
    checkpoint: true
    zone: "vol_obiguruwa_climb"
    x_setup: {string_bow_at_start: true, string_anim_s: 3}
    x_traversal:
      mode: "climb"
      route: "spl_climb_corner"
      holds: 14
      alt_route: "spl_climb_extrusion"
      alt_holds: 8
      rest_ledges: ["vol_rest_ledge_1", "vol_rest_ledge_2"]
      grip_max: 100
      grip_per_move: 6
      grip_regen_on_ledge_per_s: 25
      fall_damage: {over_cm: 400, damage: 30, lethal_over_cm: 800}
    guards:
      - id: "g_yagura_sentry"
        type: "enforcer_rifle"
        patrol: "spl_yagura_parapet"
        lookdown: {at: "ishiotoshi_1", every_s: 20, hold_s: 4}
        sight: {cone_deg: 60, range_cm: 1800, dark_range_cm: 900}
        hearing_cm: 1000
    light_sources:
      - {id: "l_sentry_lamp", carried_by: "g_yagura_sentry", extinguishable: false}
      - {id: "l_extrusion_strip", kind: "cyan_ledger_strip", extinguishable: false}
    detection: {suspicion_rate: 1.0, suspicious_at: 0.35, alert_threshold: 1.0, search_s: 25}
    on_detected: "combat"
    complete: "exit_reached"
    x_exit: "vol_climb_top"
    allies: [{npc: "npc_kohagi", role: "climb_guide", detectable: false}]
    music: "ch06_moat_stealth"
    fail: {"on": "player_died", to: "checkpoint"}
    dialogue:
      - {"on": "beat_start", mode: "ambient", lines: ["ch06.b03.kohagi.001"]}
      - {"on": "volume_enter:vol_climb_start", mode: "ambient", lines: ["ch06.b03.kohagi.002"]}
      - {"on": "ai_event:sentry_lookdown", mode: "ambient", lines: ["ch06.b03.kohagi.003"]}
      - {"on": "alert_state:alert", mode: "ambient", lines: ["ch06.b03.enforcer.001"]}
      - {"on": "volume_enter:vol_climb_top", mode: "ambient", lines: ["ch06.b03.kohagi.004"]}
    x_bark_sets: ["ch06_enforcer"]
  - id: "ch06.b04"
    type: "stealth_zone"
    place: "pl_relay_room"
    title_ja: "監視の中継器を止めよ"
    title_en: "Disable the surveillance relay"
    target_s: 240
    checkpoint: true
    site: 0
    zone: "vol_relay_room"
    objectives:
      - {id: "node_w", interact_s: 3, at: "relay_node_w"}
      - {id: "node_e", interact_s: 3, at: "relay_node_e"}
      - {id: "node_n", interact_s: 3, at: "relay_node_n"}
      - {id: "exit", volume: "vol_relay_exit_east"}
    x_sensors: [{id: "s_relay_fan", kind: "rotating_scan", period_s: 12, exposed_s: 8, gap_s: 4, on_interact_exposed: {suspicion_add: 0.6, fan_lock_s: 2}}]
    guards:
      - {id: "g_relay_1f", type: "enforcer_rifle", patrol: "spl_relay_1f_loop_50s", sight: {cone_deg: 90, range_cm: 2400, dark_range_cm: 900}, hearing_cm: 1200}
      - {id: "g_relay_2f", type: "enforcer_rifle", patrol: "spl_relay_2f_loop_40s", sight: {cone_deg: 90, range_cm: 2400, dark_range_cm: 900}, hearing_cm: 1200}
      - id: "g_relay_auditor"
        type: "auditor"
        post: "post_relay_mitai"
        investigates: "dark_node"
        sight: {cone_deg: 70, range_cm: 1800, dark_range_cm: 600}
        hearing_cm: 900
      - {id: "g_relay_drone", type: "drone", patrol: "spl_relay_orbit_30s", sight: {cone_deg: 60, range_cm: 1500, dark_range_cm: 1000}, hearing_cm: 600}
    takedowns: {rear: true, lethal_default: false}
    x_bodies: {discoverable: true, drag: true, drag_speed_mult: 0.5}
    light_sources: [{id: "l_worklamp_se", extinguishable: true, suspicion_delay_s: 5}, {id: "l_worklamp_nw", extinguishable: true, suspicion_delay_s: 5}]
    noise_surfaces: [{kind: "gravel", volume: "vol_bell_clappers_1"}, {kind: "gravel", volume: "vol_bell_clappers_2"}]
    detection: {suspicion_rate: 1.0, suspicious_at: 0.35, alert_threshold: 1.0, search_s: 25}
    on_detected: "reinforce:w_relay"
    waves:
      - id: "w_relay"
        trigger: "alert_state:alert"
        enemies: [{type: "enforcer_rifle", count: 2, spawn: "sp_relay_east_door", delay_s: 8}]
        effects: ["relay_nodes_locked_30s"]
    x_on_complete_effects: ["drone_marks_local_only_20m", "moat_searchlights_fixed"]
    complete: "objectives"
    allies: [{npc: "npc_kohagi", role: "lookout_roof", detectable: false}]
    music: "ch06_vault_stealth"
    fail: {"on": "player_died", to: "checkpoint"}
    dialogue:
      - {"on": "beat_start", mode: "radio", lines: ["ch06.b04.iota.001"]}
      - {"on": "volume_enter:vol_relay_entry", mode: "ambient", lines: ["ch06.b04.kohagi.001", "ch06.b04.kohagi.002"]}
      - {"on": "alert_state:suspicious", mode: "ambient", lines: ["ch06.b04.kohagi.003"]}
      - {"on": "ai_event:node_dark", mode: "ambient", lines: ["ch06.b04.auditor.001"]}
      - {"on": "beat_complete", mode: "ambient", lines: ["ch06.b04.kohagi.004"]}
    x_bark_sets: ["ch06_enforcer", "ch06_auditor"]
  - id: "ch06.b05"
    type: "dialogue"
    place: "pl_ledger_corridors"
    title_ja: "会計補イオタを探せ"
    title_en: "Find Junior Auditor Iota"
    target_s: 120
    checkpoint: true
    volume: "vol_archive_annex"
    trigger: "interact:crate_iota"
    mode: "ambient"
    camera: "soft_lookat"
    x_max_blocking_s: 20
    unlocks: {weapons: [3], mechanics: []}
    x_grants: ["key_slate"]
    music: "ch06_iota"
    lines:
      - "ch06.b05.nyaakoto.001"
      - "ch06.b05.iota.001"
      - "ch06.b05.nyaakoto.002"
      - "ch06.b05.iota.002"
      - "ch06.b05.nyaakoto.003"
      - "ch06.b05.iota.003"
      - "ch06.b05.iota.004"
      - "ch06.b05.iota.005"
      - "ch06.b05.iota.006"
      - "ch06.b05.iota.007"
      - "ch06.b05.nyaakoto.004"
      - "ch06.b05.iota.008"
    dialogue:
      - {"on": "interact:crate_iota", mode: "blocking", lines: ["ch06.b05.nyaakoto.001", "ch06.b05.iota.001", "ch06.b05.nyaakoto.002", "ch06.b05.iota.002"]}
      - "on": "lines_done:ch06.b05.iota.002"
        mode: "ambient"
        lines:
          - "ch06.b05.nyaakoto.003"
          - "ch06.b05.iota.003"
          - "ch06.b05.iota.004"
          - "ch06.b05.iota.005"
          - "ch06.b05.iota.006"
          - "ch06.b05.iota.007"
          - "ch06.b05.nyaakoto.004"
          - "ch06.b05.iota.008"
  - id: "ch06.b06"
    type: "stealth_zone"
    place: "pl_ledger_corridors"
    x_places_also: ["pl_uguisu_hall"]
    title_ja: "帳簿回廊と鶯張りを抜けよ"
    title_en: "Cross the ledger aisles and the nightingale floor"
    target_s: 360
    checkpoint: true
    zone: ["vol_ledger_aisles", "vol_uguisu_corridor", "vol_uguisu_garden"]
    guards:
      - {id: "g_aisle_aud_1", type: "auditor", patrol: "spl_aisle_a1", sight: {cone_deg: 70, range_cm: 1800, dark_range_cm: 600}, hearing_cm: 900}
      - {id: "g_aisle_aud_2", type: "auditor", patrol: "spl_aisle_a2", sight: {cone_deg: 70, range_cm: 1800, dark_range_cm: 600}, hearing_cm: 900}
      - {id: "g_aisle_aud_3", type: "auditor", patrol: "spl_aisle_a4", sight: {cone_deg: 70, range_cm: 1800, dark_range_cm: 600}, hearing_cm: 900}
      - {id: "g_aisle_aud_4", type: "auditor", patrol: "spl_aisle_a5", sight: {cone_deg: 70, range_cm: 1800, dark_range_cm: 600}, hearing_cm: 900}
      - id: "g_aisle_enf_c2"
        type: "enforcer_rifle"
        post: "post_c2"
        scan: {sweep_deg: 90, every_s: 8}
        sight: {cone_deg: 90, range_cm: 2400, dark_range_cm: 900}
        hearing_cm: 1200
      - id: "g_aisle_enf_c4"
        type: "enforcer_rifle"
        post: "post_c4"
        scan: {sweep_deg: 90, every_s: 8}
        sight: {cone_deg: 90, range_cm: 2400, dark_range_cm: 900}
        hearing_cm: 1200
      - {id: "g_aisle_drone_a", type: "drone", patrol: "spl_shelf_top_a", sight: {cone_deg: 60, range_cm: 1500, dark_range_cm: 1000}, hearing_cm: 600}
      - {id: "g_aisle_drone_b", type: "drone", patrol: "spl_shelf_top_b", sight: {cone_deg: 60, range_cm: 1500, dark_range_cm: 1000}, hearing_cm: 600}
      - {id: "g_uguisu_aud_corner", type: "auditor", post: "post_uguisu_corner", sight: {cone_deg: 70, range_cm: 1800, dark_range_cm: 600}, hearing_cm: 900}
      - {id: "g_uguisu_aud_legb", type: "auditor", patrol: "spl_uguisu_legb", sight: {cone_deg: 70, range_cm: 1800, dark_range_cm: 600}, hearing_cm: 900}
      - id: "g_uguisu_enf_lega"
        type: "enforcer_rifle"
        patrol: "spl_uguisu_lega"
        sight: {cone_deg: 90, range_cm: 2400, dark_range_cm: 900}
        hearing_cm: 1200
      - id: "g_uguisu_enf_door"
        type: "enforcer_rifle"
        post: "post_sugido"
        lure_to: "vol_garden_edge"
        sight: {cone_deg: 90, range_cm: 2400, dark_range_cm: 900}
        hearing_cm: 1200
    x_alarm_points: [{id: "alarm_c2_a1", run_s: 4}, {id: "alarm_c3_a5", run_s: 4}]
    lures: {tsubute: {max_carried: 3, pickups: ["vol_rubble_c1", "vol_rubble_c3", "vol_rubble_c4"], impact_noise_cm: 1400, investigate_s: 8}}
    noise_surfaces:
      - {kind: "nightingale_floor", volume: "vol_uguisu_corridor", edge_strip: "vol_uguisu_edge", walk_cm: 1800, crouch_cm: 900, edge_crouch_cm: 0}
      - {kind: "gravel", volume: "vol_uguisu_garden", mult: 1.5}
      - {kind: "puddle", volume: "vol_aisle_condensation", mult: 1.5}
      - {kind: "tatami", volume: "vol_uguisu_rooms", mult: 0.5, fusuma_slide_cm: 400}
    takedowns: {rear: true, lethal_default: false}
    x_bodies: {discoverable: true, drag: true, drag_speed_mult: 0.5}
    detection: {suspicion_rate: 1.0, suspicious_at: 0.35, alert_threshold: 1.0, search_s: 25, wary_after_search: {suspicion_rate_mult: 1.2}}
    on_detected: "reinforce:w_lockdown"
    waves:
      - id: "w_lockdown"
        trigger: "ai_event:alarm_raised"
        enemies: [{type: "enforcer_rifle", count: 2, spawn: "sp_aisle_north_door"}, {type: "enforcer_rifle", count: 2, spawn: "sp_aisle_south_door"}]
        effects: ["shutter_c3_closed_30s"]
    complete: "exit_reached"
    x_exit: "vol_sugido"
    unlocks: {weapons: [], mechanics: ["tsubute"]}
    music: "ch06_vault_stealth"
    fail: {"on": "player_died", to: "checkpoint"}
    dialogue:
      - {"on": "beat_start", mode: "radio", lines: ["ch06.b06.iota.001", "ch06.b06.iota.002"]}
      - {"on": "volume_enter:vol_rubble_c1", mode: "ambient", lines: ["ch06.b06.nyaakoto.001"]}
      - {"on": "volume_enter:vol_rubble_c1", mode: "radio", lines: ["ch06.b06.kohagi.001"]}
      - {"on": "volume_enter:vol_aisle_c2", mode: "ambient", lines: ["ch06.b06.auditor.001", "ch06.b06.auditor.002"]}
      - {"on": "volume_enter:vol_uguisu_entry", mode: "radio", lines: ["ch06.b06.kohagi.002"]}
      - {"on": "ai_event:floor_chirp", mode: "ambient", lines: ["ch06.b06.auditor.004"]}
      - {"on": "volume_enter:vol_sugido", mode: "radio", lines: ["ch06.b06.iota.003"]}
    x_bark_sets: ["ch06_enforcer", "ch06_auditor"]
  - id: "ch06.b07"
    type: "explore_optional"
    place: "pl_uguisu_hall"
    title_ja: "押収品庫を調べる（任意）"
    title_en: "Search the seized-goods store (optional)"
    target_s: 180
    checkpoint: true
    optional: true
    requires: ["ch06.b06"]
    volume: "vol_vault_armory"
    pois:
      - {id: "poi_phantom_locker", kind: "cache"}
      - {id: "poi_contraband", kind: "lore"}
      - {id: "poi_heirloom_map", kind: "lore"}
      - {id: "poi_heirloom_shuttle", kind: "lore"}
      - {id: "poi_arrow_cache", kind: "cache"}
      - {id: "poi_vista", kind: "vista"}
    rewards: ["ch06.c03", "ch06.c04", "arrows:6"]
    exit_hint_after_s: 150
    unlocks: {weapons: [13], mechanics: []}
    x_auto_grant_if_missed: "ch07.b01"
    music: "ch06_vault_stealth"
    dialogue:
      - {"on": "volume_enter:vol_vault_armory", mode: "radio", lines: ["ch06.b07.iota.001"]}
      - {"on": "volume_enter:vol_poi_contraband", mode: "ambient", lines: ["ch06.b07.nyaakoto.001"]}
      - {"on": "volume_enter:vol_poi_heirloom_map", mode: "ambient", lines: ["ch06.b07.nyaakoto.002"]}
      - {"on": "volume_enter:vol_poi_vista", mode: "ambient", lines: ["ch06.b07.nyaakoto.003"]}
  - id: "ch06.b08"
    type: "production_task"
    task: "hold"
    place: "pl_uguisu_hall"
    title_ja: "三つの帳台で総高を写せ"
    title_en: "Copy the totals at three desks"
    target_s: 240
    checkpoint: true
    site: 1
    requires: ["ch06.b06"]
    hold: {volume: "vol_ohiroma_kicho", interact_points: ["desk_tagata", "desk_machikata", "desk_shokukata"], per_point_s: 30, contest: "pause"}
    stealth: true
    x_light_carried: {item: "teshoku_candle", radius_cm: 350, visibility_mult: 2.0, cupped: {visibility_mult: 1.2, progress_mult: 0.5}}
    waves:
      - id: "w_kicho_patrol"
        trigger: "start"
        enemies:
          - {type: "auditor", count: 3, spawn: "sp_kicho_aud", patrol: ["spl_kicho_a", "spl_kicho_b", "spl_kicho_c"]}
          - {type: "enforcer_rifle", count: 1, spawn: "sp_kicho_enf", patrol: "spl_kicho_irigawa"}
          - {type: "drone", count: 1, spawn: "sp_kicho_air", patrol: "spl_kicho_air"}
    detection: {suspicion_rate: 1.0, suspicious_at: 0.35, alert_threshold: 1.0, search_s: 25}
    takedowns: {rear: true, lethal_default: false}
    x_bodies: {discoverable: true, drag: true, drag_speed_mult: 0.5}
    registry: {item_ja: "債務帳の写し", item_en: "Ledger copy", qty: 3, unit_ja: "冊", unit_en: "volumes"}
    music: "ch06_copy"
    fail: {"on": "player_died", to: "checkpoint"}
    dialogue:
      - {"on": "beat_start", mode: "radio", lines: ["ch06.b08.iota.001", "ch06.b08.kohagi.001"]}
      - {"on": "interact:desk_tagata", mode: "ambient", lines: ["ch06.b08.nyaakoto.001"]}
      - {"on": "progress_at:0.33", mode: "radio", lines: ["ch06.b08.iota.002"]}
      - {"on": "progress_at:0.66", mode: "radio", lines: ["ch06.b08.iota.003"]}
      - {"on": "volume_enter:vol_kicho_chudan", mode: "ambient", lines: ["ch06.b08.auditor.001", "ch06.b08.auditor.002"]}
      - {"on": "ai_event:light_seen", mode: "ambient", lines: ["ch06.b08.auditor.003"]}
    x_bark_sets: ["ch06_enforcer", "ch06_auditor"]
  - id: "ch06.b09"
    type: "duel"
    place: "pl_archive"
    title_ja: "虎之介と立ち合え"
    title_en: "Face Toranosuke"
    target_s: 420
    checkpoint: true
    requires: ["ch06.b08"]
    opponent: "npc_toranosuke"
    weapons: {player: [0], opponent: "katana"}
    lethal: false
    scoring: {mode: "hp"}
    ring: "vol_archive_ring"
    x_opponent_hp: 600
    x_hp_floor_pct: 10
    x_pattern_tables: [{from_hp_pct: 100, table: "toranosuke_steel_p1"}, {from_hp_pct: 50, table: "toranosuke_steel_p2"}]
    events: [{at_hp_pct: 50, id: "family_page", cinematic: "LS_Ch06_B09_FamilyPage", max_s: 20, checkpoint: true}]
    finisher: "muto_dori"
    x_muto:
      requires_sheathed: true
      sheathe_ms: 700
      window_ms: 180
      window_ms_easy: 234
      window_ms_hard: 153
      eligible: ["makko_giri", "kiriotoshi_rush", "nidan_makko"]
      miss_takes_hit: true
    loss_policy: "retry"
    checkpoint_per_phase: true
    unlocks: {weapons: [], mechanics: ["muto_dori"]}
    music: "ch06_duel_toranosuke"
    fail: {"on": "player_died", to: "checkpoint"}
    dialogue:
      - {"on": "beat_start", mode: "ambient", lines: ["ch06.b09.toranosuke.001", "ch06.b09.nyaakoto.001", "ch06.b09.toranosuke.002", "ch06.b09.toranosuke.003"]}
      - "on": "duel_event:family_page"
        mode: "blocking"
        lines: ["ch06.b09.toranosuke.005", "ch06.b09.nyaakoto.002", "ch06.b09.nyaakoto.003", "ch06.b09.toranosuke.006"]
      - {"on": "duel_phase:2", mode: "radio", lines: ["ch06.b09.sekireisai.001", "ch06.b09.sekireisai.002"], fx: "memory_reverb"}
      - {"on": "ai_event:player_sheathed", mode: "ambient", lines: ["ch06.b09.toranosuke.007"]}
      - {"on": "player_died", mode: "blocking", lines: ["ch06.b09.toranosuke.010"]}
    barks:
      - {"on": "pattern:kesa_combo", line: "ch06.b09.toranosuke.004"}
      - {"on": "pattern:makko_giri", line: "ch06.b09.toranosuke.008"}
      - {"on": "pattern:kiriotoshi_rush", line: "ch06.b09.toranosuke.009"}
  - id: "ch06.b10"
    type: "dialogue"
    place: "pl_archive"
    title_ja: "誓い"
    title_en: "The pledge"
    target_s: 90
    checkpoint: true
    trigger: "beat_start"
    mode: "ambient"
    camera: "soft_lookat"
    x_max_blocking_s: 20
    unlocks: {weapons: [10], mechanics: []}
    music: "ch06_pledge"
    lines:
      - "ch06.b10.toranosuke.001"
      - "ch06.b10.toranosuke.002"
      - "ch06.b10.nyaakoto.001"
      - "ch06.b10.toranosuke.003"
      - "ch06.b10.nyaakoto.002"
      - "ch06.b10.toranosuke.004"
      - "ch06.b10.nyaakoto.003"
      - "ch06.b10.toranosuke.005"
      - "ch06.b10.nyaakoto.004"
      - "ch06.b10.toranosuke.006"
    dialogue:
      - "on": "beat_start"
        mode: "ambient"
        lines: ["ch06.b10.toranosuke.001", "ch06.b10.toranosuke.002", "ch06.b10.nyaakoto.001", "ch06.b10.toranosuke.003", "ch06.b10.nyaakoto.002"]
      - {"on": "lines_done:ch06.b10.nyaakoto.002", mode: "blocking", lines: ["ch06.b10.toranosuke.004", "ch06.b10.nyaakoto.003"]}
      - {"on": "lines_done:ch06.b10.nyaakoto.003", mode: "ambient", lines: ["ch06.b10.toranosuke.005", "ch06.b10.nyaakoto.004", "ch06.b10.toranosuke.006"]}
  - id: "ch06.b11"
    type: "stealth_zone"
    place: "pl_press_hall"
    title_ja: "親機三台を止めよ"
    title_en: "Jam the three master presses"
    target_s: 240
    checkpoint: true
    site: 2
    zone: "vol_press_hall"
    objectives:
      - {id: "press_a2", interact_s: 4, at: "press_a2"}
      - {id: "press_b2", interact_s: 4, at: "press_b2"}
      - {id: "press_c1", interact_s: 4, at: "press_c1"}
      - {id: "exit", volume: "vol_press_lift"}
    x_noise_mask: {source: "press_stamp", period_ms: 1600, window_ms: 500, radius_cm: 800, player_noise_mult: 0.2}
    x_press_silent_inspection: {auditor_investigates_within_s: 20}
    guards:
      - {id: "g_press_aud_1", type: "auditor", patrol: "spl_press_inspect_a", sight: {cone_deg: 70, range_cm: 1800, dark_range_cm: 600}, hearing_cm: 900}
      - {id: "g_press_aud_2", type: "auditor", patrol: "spl_press_inspect_b", sight: {cone_deg: 70, range_cm: 1800, dark_range_cm: 600}, hearing_cm: 900}
      - {id: "g_press_enf_1", type: "enforcer_rifle", patrol: "spl_press_floor_ab", sight: {cone_deg: 90, range_cm: 2400, dark_range_cm: 900}, hearing_cm: 1200}
      - {id: "g_press_enf_2", type: "enforcer_rifle", patrol: "spl_press_floor_bc", sight: {cone_deg: 90, range_cm: 2400, dark_range_cm: 900}, hearing_cm: 1200}
      - {id: "g_press_enf_3", type: "enforcer_rifle", patrol: "spl_press_catwalk", sight: {cone_deg: 90, range_cm: 3000, dark_range_cm: 1000}, hearing_cm: 1000}
      - {id: "g_press_drone", type: "drone", patrol: "spl_press_air_30s", sight: {cone_deg: 60, range_cm: 1500, dark_range_cm: 1000}, hearing_cm: 600}
    light_sources:
      - {id: "l_die_lamp_a2", extinguishable: "arrow", suspicion_delay_s: 5}
      - {id: "l_die_lamp_b2", extinguishable: "arrow", suspicion_delay_s: 5}
      - {id: "l_die_lamp_c1", extinguishable: "arrow", suspicion_delay_s: 5}
    noise_surfaces: [{kind: "gravel", volume: "vol_press_slugs_1"}, {kind: "gravel", volume: "vol_press_slugs_2"}]
    takedowns: {rear: true, lethal_default: false}
    x_bodies: {discoverable: true, drag: true, drag_speed_mult: 0.5}
    detection: {suspicion_rate: 1.0, suspicious_at: 0.35, alert_threshold: 1.0, search_s: 25}
    on_detected: "reinforce:w_press"
    waves: [{id: "w_press", trigger: "alert_state:alert", enemies: [{type: "enforcer_rifle", count: 3, spawn: "sp_press_lift", delay_s: 10}]}]
    complete: "objectives"
    music: "ch06_press"
    fail: {"on": "player_died", to: "checkpoint"}
    dialogue:
      - {"on": "beat_start", mode: "radio", lines: ["ch06.b11.kohagi.001", "ch06.b11.iota.001"]}
      - {"on": "volume_enter:vol_press_floor", mode: "radio", lines: ["ch06.b11.kohagi.002"]}
      - {"on": "interact:press_any_first", mode: "ambient", lines: ["ch06.b11.nyaakoto.001"]}
      - {"on": "volume_enter:vol_press_binding", mode: "ambient", lines: ["ch06.b11.auditor.001", "ch06.b11.auditor.002"]}
      - {"on": "ai_event:press_silent", mode: "ambient", lines: ["ch06.b11.auditor.003"]}
      - {"on": "alert_state:alert", mode: "ambient", lines: ["ch06.b11.enforcer.001"]}
    x_bark_sets: ["ch06_enforcer", "ch06_auditor"]
  - id: "ch06.b12"
    type: "cinematic"
    place: "pl_vault_core"
    title_ja: "停電"
    title_en: "Blackout"
    target_s: 90
    checkpoint: false
    sequence: "/Game/Campaign/Ch06/Sequences/LS_Ch06_B12_Blackout"
    duration_s: 80
    skippable: true
    fallback: "camera_blend"
    end_state: {player_transform: "ps_vault_core_lift", equipped: [0]}
    music: "ch06_boss_eskro_intro"
    subtitles: ["ch06.b12.iota.001", "ch06.b12.valamort.001", "ch06.b12.nyaakoto.001", "ch06.b12.eskro.001", "ch06.b12.kohagi.001"]
  - id: "ch06.b13"
    type: "boss"
    place: "pl_vault_core"
    title_ja: "金庫番エスクロを封じよ"
    title_en: "Seal away Vault Warden Eskro"
    target_s: 420
    checkpoint: true
    boss: "boss_eskro"
    x_boss_hp: 1800
    arena: {volume: "vol_vault_core", lock: true}
    phases:
      - {hp_pct_start: 100, pattern_table: "eskro_hunt"}
      - {hp_pct_start: 60, pattern_table: "eskro_flood", arena_mod: "flood_25cm"}
      - {hp_pct_start: 25, pattern_table: "eskro_frenzy", adds: "audit_hound_pair"}
    defeat: "capture"
    x_defeat_interact: {id: "bulkhead_lever", hold_s: 2}
    checkpoint_per_phase: true
    telegraph: {palette: "default", min_windup_ms: 500}
    x_arena_props: {tsubute_piles: ["vol_core_rubble_090", "vol_core_rubble_210", "vol_core_rubble_330"], shelves: 8, candle_placeable: true}
    intro_cinematic: "ch06.b12"
    outro_cinematic: "LS_Ch06_B13_Sealed"
    music: "ch06_boss_eskro"
    fail: {"on": "player_died", to: "checkpoint"}
    dialogue:
      - {"on": "beat_start", mode: "radio", lines: ["ch06.b13.kohagi.001"]}
      - {"on": "beat_start", mode: "ambient", lines: ["ch06.b13.nyaakoto.001"]}
      - {"on": "pattern:pounce_miss", mode: "ambient", lines: ["ch06.b13.nyaakoto.002"]}
      - {"on": "boss_phase:3", mode: "radio", lines: ["ch06.b13.kohagi.002"]}
      - {"on": "ai_event:boss_hp_zero", mode: "ambient", lines: ["ch06.b13.eskro.010"]}
      - {"on": "interact:bulkhead_lever", mode: "ambient", lines: ["ch06.b13.nyaakoto.003"]}
    barks:
      - {"on": "pattern:reconcile_pulse", line: "ch06.b13.eskro.002"}
      - {"on": "pattern:pounce", line: "ch06.b13.eskro.003"}
      - {"on": "pattern:pounce_miss", line: "ch06.b13.eskro.004"}
      - {"on": "pattern:claw_flurry", line: "ch06.b13.eskro.005"}
      - {"on": "boss_phase:2", line: "ch06.b13.eskro.006"}
      - {"on": "pattern:shelf_rake", line: "ch06.b13.eskro.007"}
      - {"on": "pattern:wade_charge", line: "ch06.b13.eskro.008"}
      - {"on": "boss_phase:3", line: "ch06.b13.eskro.009"}
  - id: "ch06.b14"
    type: "stealth_zone"
    place: "pl_citadel_moat"
    title_ja: "満ちる暗渠を抜けよ"
    title_en: "Escape through the flooding culvert"
    target_s: 180
    checkpoint: true
    zone: ["vol_ankyo_conduit", "vol_moat_exfil"]
    x_hazard: {kind: "rising_water", from_cm: 40, to_cm: 160, over_s: 150, deep_volume: "vol_ankyo_deep"}
    x_traversal: {mode: "wade_swim", wade_noise_mult: 2.0, dive_max_s: 8}
    guards:
      - id: "g_grate_1"
        type: "enforcer_rifle"
        post: "post_grate_1"
        lamp_beam: "vol_grate_beam_1"
        sight: {cone_deg: 90, range_cm: 2400, dark_range_cm: 900}
        hearing_cm: 1200
      - id: "g_grate_2"
        type: "enforcer_rifle"
        post: "post_grate_2"
        lamp_beam: "vol_grate_beam_2"
        sight: {cone_deg: 90, range_cm: 2400, dark_range_cm: 900}
        hearing_cm: 1200
      - id: "g_grate_3"
        type: "enforcer_rifle"
        patrol: "spl_obiguruwa_search"
        lamp_beam: "vol_grate_beam_3"
        sight: {cone_deg: 90, range_cm: 2400, dark_range_cm: 900}
        hearing_cm: 1200
      - {id: "g_gate_drone", type: "drone", patrol: "spl_gate_drone", sight: {cone_deg: 60, range_cm: 1500, dark_range_cm: 1000}, hearing_cm: 600}
      - {id: "g_boat_1", type: "enforcer_rifle", patrol: "spl_moat_boat_60s", sight: {cone_deg: 90, range_cm: 2400, dark_range_cm: 900}, hearing_cm: 1200}
      - {id: "g_boat_2", type: "enforcer_rifle", patrol: "spl_moat_boat_60s", sight: {cone_deg: 90, range_cm: 2400, dark_range_cm: 900}, hearing_cm: 1200}
    noise_surfaces: [{kind: "running_water", volume: "vol_ankyo_conduit", mult: 0.5}, {kind: "water_swim", volume: "vol_moat_exfil"}]
    detection: {suspicion_rate: 0.9, suspicious_at: 0.35, alert_threshold: 1.0, search_s: 20}
    on_detected: "combat"
    complete: "exit_reached"
    x_exit: "vol_moat_outer_bank"
    allies:
      - {npc: "npc_toranosuke", role: "follow", detectable: false}
      - {npc: "npc_iota", role: "follow", carried_after: "vol_ankyo_deep", detectable: false}
      - {npc: "npc_kohagi", role: "gate_winch", detectable: false}
    music: "ch06_exfil"
    fail: {"on": "player_died", to: "checkpoint"}
    dialogue:
      - {"on": "volume_enter:vol_ankyo_start", mode: "ambient", lines: ["ch06.b14.toranosuke.001", "ch06.b14.iota.001", "ch06.b14.toranosuke.002"]}
      - {"on": "volume_enter:vol_ankyo_grate_1", mode: "radio", lines: ["ch06.b14.kohagi.001"]}
      - {"on": "volume_enter:vol_ankyo_grate_1", mode: "ambient", lines: ["ch06.b14.enforcer.001"]}
      - {"on": "volume_enter:vol_ankyo_deep", mode: "ambient", lines: ["ch06.b14.nyaakoto.001"]}
      - {"on": "volume_enter:vol_water_gate_exit", mode: "radio", lines: ["ch06.b14.kohagi.002"]}
    x_bark_sets: ["ch06_enforcer"]
  - id: "ch06.b15"
    type: "dialogue"
    place: "pl_citadel_moat"
    title_ja: "数字を読む"
    title_en: "Reading the numbers"
    target_s: 60
    checkpoint: true
    volume: "vol_moat_outer_bank"
    trigger: "beat_start"
    mode: "ambient"
    camera: "soft_lookat"
    music: "ch06_numbers"
    lines:
      - "ch06.b15.oyuki.001"
      - "ch06.b15.oyuki.002"
      - "ch06.b15.oyuki.003"
      - "ch06.b15.iota.001"
      - "ch06.b15.toranosuke.001"
      - "ch06.b15.oyuki.004"
      - "ch06.b15.nyaakoto.001"
    dialogue:
      - "on": "beat_start"
        mode: "ambient"
        lines:
          - "ch06.b15.oyuki.001"
          - "ch06.b15.oyuki.002"
          - "ch06.b15.oyuki.003"
          - "ch06.b15.iota.001"
          - "ch06.b15.toranosuke.001"
          - "ch06.b15.oyuki.004"
          - "ch06.b15.nyaakoto.001"
  - id: "ch06.b16"
    type: "cinematic"
    place: "pl_kosatsuba"
    title_ja: "帳は民の前に"
    title_en: "The ledger before the people"
    target_s: 120
    checkpoint: false
    sequence: "/Game/Campaign/Ch06/Sequences/LS_Ch06_B16_KosatsuDawn"
    duration_s: 115
    skippable: true
    fallback: "camera_blend"
    end_state: {chapter_complete: true, registry_page: "ch06"}
    music: "ch06_dawn_kosatsu"
    subtitles:
      - "ch06.b16.resident.001"
      - "ch06.b16.resident.002"
      - "ch06.b16.tokichi.001"
      - "ch06.b16.oyuki.001"
      - "ch06.b16.tetsugoro.001"
      - "ch06.b16.toranosuke.001"
      - "ch06.b16.nyaakoto.001"
x_bark_sets:
  ch06_enforcer:
    - {"on": "alert_state:suspicious", line: "ch06.b04.enforcer.001"}
    - {"on": "alert_state:alert", line: "ch06.b04.enforcer.002"}
    - {"on": "alert_state:search", line: "ch06.b04.enforcer.003"}
    - {"on": "alert_state:unaware", line: "ch06.b04.enforcer.004"}
    - {"on": "ai_event:retreat", line: "ch06.b04.enforcer.005"}
    - {"on": "ai_event:body_found", line: "ch06.b04.enforcer.006"}
  ch06_auditor:
    - {"on": "alert_state:suspicious", line: "ch06.b04.auditor.002"}
    - {"on": "ai_event:alarm_run", line: "ch06.b04.auditor.003"}
    - {"on": "ai_event:lure_heard", line: "ch06.b06.auditor.003"}
  ch06_moat:
    - {"on": "alert_state:suspicious", line: "ch06.b02.enforcer.001"}
    - {"on": "alert_state:alert", line: "ch06.b02.enforcer.002"}
    - {"on": "alert_state:search", line: "ch06.b02.enforcer.003"}
    - {"on": "alert_state:unaware", line: "ch06.b04.enforcer.004"}
x_pattern_tables:
  toranosuke_steel_p1:
    - id: "kesa_combo"
      ja: "袈裟連撃"
      windup_ms: 450
      hits: 3
      gap_ms: 300
      damage_each: 22
      parry: "awase_260ms"
      on_parry: "stagger_1.2s"
      recovery_ms: 700
      muto_eligible: false
    - id: "morote_tsuki"
      ja: "諸手突き"
      windup_ms: 600
      damage: 30
      parry: "none"
      guard: "50pct_plus_40_stamina"
      counter: "marobashi_400ms_flank_0.8s"
      recovery_ms: 900
      muto_eligible: false
    - id: "feint_jodan"
      ja: "見せ上段"
      tell_ms: 300
      windup_ms: 500
      damage: 26
      note: "raises to jodan, switches to a low do cut"
      recovery_ms: 700
      muto_eligible: false
    - id: "taiatari"
      ja: "体当たり"
      trigger: "player_guard_held_over_1.5s"
      windup_ms: 400
      damage: 10
      knockback_cm: 150
      stamina: -25
      recovery_ms: 600
      muto_eligible: false
  toranosuke_steel_p2:
    - {id: "makko_giri", ja: "真っ向斬り", windup_ms: 800, damage: 40, telegraph: "amber_blade_edge", recovery_ms: 1100, muto_eligible: true}
    - {id: "kiriotoshi_rush", ja: "踏込み斬り落とし", dash_cm: 300, windup_ms: 700, damage: 38, telegraph: "amber_blade_edge", recovery_ms: 1200, muto_eligible: true}
    - {id: "nidan_makko", ja: "二段真っ向", windup_ms: [800, 500], damage_each: 34, telegraph: "amber_blade_edge", recovery_ms: 1300, muto_eligible: true}
  eskro_hunt:
    - id: "reconcile_pulse"
      ja: "照合"
      windup_ms: 700
      period_s: 8
      radius_cm: 1800
      expand_ms: 720
      reveal_if: {speed_over_cm_s: 120, noise_event: true}
      damage: 0
      telegraph: "audio_chirp_and_refractive_ring"
      bark: "ch06.b13.eskro.002"
    - {id: "listen", ja: "聴取", duration_s: [2, 4], hearing_cm: {walk: 1200, crouch_walk: 600}}
    - id: "pounce"
      ja: "飛掛り"
      windup_ms: 600
      range_cm: 1500
      radius_cm: 250
      damage: 45
      target: "last_noise"
      recovery_hit_ms: 800
      recovery_miss_ms: 1500
      telegraph: "amber_landing_decal"
      bark: "ch06.b13.eskro.003"
      miss_bark: "ch06.b13.eskro.004"
    - id: "claw_flurry"
      ja: "連爪"
      trigger: "revealed_within_300cm"
      windup_ms: 500
      hits: 3
      span_ms: 900
      damage_each: 18
      arc_deg: 120
      range_cm: 300
      guardable: true
      awase_on_hit: 3
      on_parry: "stagger_1.2s"
      recovery_ms: 900
      bark: "ch06.b13.eskro.005"
  eskro_flood:
    - {inherits: "eskro_hunt"}
    - id: "shelf_rake"
      ja: "棚払い"
      windup_ms: 900
      arc_deg: 120
      range_cm: 450
      damage: 35
      knock_off_shelf: true
      telegraph: "amber_arc"
      recovery_ms: 1200
      bark: "ch06.b13.eskro.007"
    - id: "wade_charge"
      ja: "水走り"
      windup_ms: 700
      length_cm: 1200
      damage: 40
      self_noise: true
      telegraph: "amber_lane"
      recovery_ms: 1000
      bark: "ch06.b13.eskro.008"
  eskro_frenzy:
    - {inherits: "eskro_flood", override: {reconcile_pulse: {period_s: 4}}}
    - id: "double_pounce"
      ja: "二段飛掛り"
      windup_ms: [600, 600]
      damage_each: 45
      recovery_miss_ms: 1500
      telegraph: "amber_landing_decal"
      bark: "ch06.b13.eskro.003"
    - id: "adds_audit_hound"
      type: "drone"
      variant: "audit_hound"
      count: 2
      hp: 60
      sight: {cone_deg: 70, range_cm: 900, dark_range_cm: 900}
      sees_light: true
      chirp_windup_ms: 600
      effect: "reveal_player_to_boss"
  modifiers:
    - rear_damage_mult: 1.5
      easy_windup_mult: 1.3
      hard_windup_mult: 0.85
      note: "Eskro is blind: light never reveals the player to him, only sound and the hounds"
collectibles:
  - id: "ch06.c01"
    collectible_id: "ch06.c01"
    category: "league_mark"
    place: "pl_citadel_moat"
    volume: "vol_water_gate_outer"
    mask_bit: 0
    found_in: "ch06.b02"
    codex: {ja: "水門の水位目盛りの横に、小萩が先月残した小さな空紋。", en: "A small Sora mark Kohagi left last month beside the gate's water gauge."}
  - id: "ch06.c02"
    collectible_id: "ch06.c02"
    category: "seizure_notice"
    place: "pl_relay_room"
    volume: "vol_bell_pile_w"
    mask_bit: 1
    found_in: "ch06.b04"
    codex:
      ja: "差押状：猫柳生谷の半鐘、四十二口。理由：無許可の警報は与信を損なうため。"
      en: "Seizure notice: 42 alarm bells, Nyaagyu valley. Reason: unlicensed alarms damage creditworthiness."
  - id: "ch06.c03"
    collectible_id: "ch06.c03"
    category: "heirloom"
    place: "pl_uguisu_hall"
    volume: "vol_poi_heirloom_map"
    mask_bit: 2
    found_in: "ch06.b07"
    codex:
      ja: "庄屋田右衛門家の水利絵図。堰と水路ごとに、どの田へ何日水を回すかが描かれている。"
      en: "Headman Taemon's water-rights map: which paddy gets water from which channel, and for how many days."
  - id: "ch06.c04"
    collectible_id: "ch06.c04"
    category: "heirloom"
    place: "pl_uguisu_hall"
    volume: "vol_poi_heirloom_shuttle"
    mask_bit: 3
    found_in: "ch06.b07"
    codex: {ja: "お絹の母の黄楊の杼。手の脂で飴色に光る。", en: "Okinu's mother's boxwood shuttle, polished amber by years of hands."}
  - id: "ch06.c05"
    collectible_id: "ch06.c05"
    category: "scroll_fragment"
    place: "pl_ledger_corridors"
    volume: "vol_archive_annex"
    mask_bit: 4
    found_in: "ch06.b05"
    codex:
      ja: "無刀とは、人の刀を取る芸にあらず。わが手の内を知り、斬られぬことなり。――石鈴斎"
      en: "No-sword is not the art of taking another's blade. It is knowing your own hands, and not being cut. (Sekireisai)"
  - id: "ch06.c06"
    collectible_id: "ch06.c06"
    category: "seizure_notice"
    place: "pl_press_hall"
    volume: "vol_press_binding"
    mask_bit: 5
    found_in: "ch06.b11"
    codex:
      ja: "担保受領書 第一号：猫柳生石鈴斎（隠居）一名。保管先、担保牢。状態、良好。"
      en: "Collateral Receipt No. 1: Nyaagyu Sekireisai (retired), one. Held in the collateral cells. Condition: good."
ui_prompts:
  - {id: "hud.ch06.swim_dive", beat: "ch06.b02", "on": "beat_start", ja: "潜る：{Crouch}　息は8秒まで", en: "Dive: {Crouch}. Breath lasts 8 s."}
  - {id: "hud.ch06.surface_cover", beat: "ch06.b02", "on": "volume_enter:vol_moat_lotus_1", ja: "蓮と葦の陰なら、浮いても見つかりにくい", en: "Lotus and reeds hide you at the surface."}
  - {id: "hud.ch06.float_line", beat: "ch06.b02", "on": "volume_enter:vol_moat_boom", ja: "浮き綱に触れると鳴る。下を潜る", en: "The float line rings if touched. Dive under it."}
  - {id: "hud.ch06.climb", beat: "ch06.b03", "on": "volume_enter:vol_climb_start", ja: "{Jump}で手掛かりへ。握力に注意", en: "{Jump} to reach for the holds. Watch your grip."}
  - {id: "hud.ch06.climb_rest", beat: "ch06.b03", "on": "volume_enter:vol_rest_ledge_1", ja: "足場で握力が戻る", en: "Ledges restore grip."}
  - {id: "hud.ch06.ai_states", beat: "ch06.b04", "on": "alert_state:suspicious", ja: "頭上の印：不審・警戒・捜索", en: "Marks above heads: Suspicious, Alert, Search."}
  - {id: "hud.ch06.sweep_gap", beat: "ch06.b04", "on": "volume_enter:vol_relay_entry", ja: "柱の目が背を向けた隙に、{Interact}で節を抜く", en: "Pull a node with {Interact} while the eye faces away."}
  - {id: "hud.ch06.takedown", beat: "ch06.b04", "on": "ai_event:first_rear_reach", ja: "背後から当て身：{Melee}（殺さない）", en: "Rear takedown: {Melee}. Non-lethal."}
  - {id: "hud.ch06.drag", beat: "ch06.b04", "on": "ai_event:first_takedown", ja: "倒れた者を引きずる：{Interact}長押し", en: "Drag a body: hold {Interact}."}
  - {id: "hud.ch06.tsubute", beat: "ch06.b06", "on": "volume_enter:vol_rubble_c1", ja: "礫（つぶて）：{Interact}で拾い{Ability}で投げ、音で見張りを誘う", en: "Tsubute: pick up with {Interact}, throw with {Ability} to lure a guard."}
  - {id: "hud.ch06.nightingale", beat: "ch06.b06", "on": "volume_enter:vol_uguisu_entry", ja: "鶯張り：しゃがんで壁際の端を歩く", en: "Nightingale floor: crouch along the wall edge."}
  - {id: "hud.ch06.candle", beat: "ch06.b08", "on": "beat_start", ja: "蝋燭を覆う：{Block}長押し　写しは半速", en: "Cup the candle: hold {Block}. Copying slows."}
  - {id: "hud.ch06.copy_pause", beat: "ch06.b08", "on": "ai_event:copy_paused", ja: "見られている間は、写しが止まる", en: "Copying pauses while you are seen."}
  - {id: "hud.ch06.sheathe", beat: "ch06.b09", "on": "duel_phase:2", ja: "納刀：{Sheathe}", en: "Sheathe: press {Sheathe}."}
  - {id: "hud.ch06.muto", beat: "ch06.b09", "on": "ai_event:player_sheathed", ja: "無刀取り：納刀中、真っ向斬りに踏み込み{Block}", en: "Mutō-dori: while sheathed, step into a vertical cut with {Block}."}
  - {id: "hud.ch06.press_mask", beat: "ch06.b11", "on": "volume_enter:vol_press_floor", ja: "印刷機の打音が足音を隠す", en: "Press slams mask your footsteps."}
  - {id: "hud.ch06.pulse", beat: "ch06.b13", "on": "beat_start", ja: "脈動の間は動かない", en: "Stay still while the pulse passes."}
  - {id: "hud.ch06.flood", beat: "ch06.b13", "on": "boss_phase:2", ja: "水の中は音が大きい。棚の上は静か", en: "Water is loud. Shelf tops are silent."}
  - {id: "hud.ch06.bulkhead", beat: "ch06.b13", "on": "ai_event:boss_hp_zero", ja: "隔壁を落とす：{Interact}", en: "Drop the bulkhead: {Interact}."}
lines:
  - {id: "ch06.b01.iota.001", speaker: "clerk", register: "manual_keigo", ja: "水門の格子は、水の下で外してございます。", en: "The water-gate grille is unfastened below the waterline.", duration_s: 3.8}
  - {id: "ch06.b01.kohagi.001", speaker: "scout", register: "scout_terse", ja: "金庫の奥に、街を縛る装置がある。", en: "The machine binding the city lies deep inside the vault.", duration_s: 4.8, catalog_anchor: 1}
  - {id: "ch06.b01.oyuki.001", speaker: "leader", register: "business_keigo", ja: "燃やさず、写しなさい。", en: "Copy it. Do not burn it.", duration_s: 1.9}
  - {id: "ch06.b01.nyaakoto.001", speaker: "samurai", register: "samurai_polite", ja: "燃やせば早い。なぜ写すのですか。", en: "Burning is faster. Why copy it?", duration_s: 2.8}
  - {id: "ch06.b01.oyuki.002", speaker: "leader", register: "business_keigo", ja: "燃やせば、彼らは「失われた」と言って、書き直すだけです。", en: "Burn it, and they call it lost and simply write it again.", duration_s: 4.5}
  - {id: "ch06.b01.oyuki.003", speaker: "leader", register: "business_keigo", ja: "写せば、民が自分の数字を読めます。", en: "Copy it, and people can read their own numbers.", duration_s: 3.4}
  - {id: "ch06.b01.oyuki.004", speaker: "leader", register: "business_keigo", ja: "総高と利率だけで足ります。欲張らぬように。", en: "Totals and rates are enough. Do not be greedy.", duration_s: 4.0}
  - {id: "ch06.b01.kohagi.002", speaker: "scout", register: "scout_terse", ja: "弦は、あたしが濡らさず運ぶ。", en: "I'll carry your bowstring. It stays dry.", duration_s: 2.7}
  - {id: "ch06.b01.kohagi.003", speaker: "scout", register: "scout_terse", ja: "泳ぐよ。", en: "We swim.", duration_s: 1.5}
  - {id: "ch06.b01.nyaakoto.002", speaker: "samurai", register: "samurai_plain", ja: "……泳ぐ。", en: "…We swim.", duration_s: 1.5}
  - {id: "ch06.b02.kohagi.001", speaker: "scout", register: "scout_terse", ja: "息は八つまで。潜って、灯りをやり過ごす。", en: "Eight counts of breath. Dive, and let the light pass.", duration_s: 3.6}
  - {id: "ch06.b02.iota.001", speaker: "clerk", register: "manual_keigo", ja: "探照灯様の周期は十秒。本日も定刻どおりでございます。", en: "The searchlights sweep every ten seconds. Punctual as ever.", duration_s: 5.3}
  - {id: "ch06.b02.kohagi.002", speaker: "scout", register: "scout_terse", ja: "浮きの綱。触ると鳴る。下をくぐって。", en: "A float line. It rings if touched. Go under.", duration_s: 3.5}
  - {id: "ch06.b02.kohagi.003", speaker: "scout", register: "scout_terse", ja: "灯台下暗し。壁際を行く。", en: "Darkest under the lamp. We hug the wall.", duration_s: 2.8}
  - {id: "ch06.b02.enforcer.001", speaker: "enforcer", register: "alien_corporate", ja: "水面に波紋。……魚類と推定いたします。", en: "Ripples on the water. Presumed to be fish.", duration_s: 4.1, repeatable: true}
  - {id: "ch06.b02.enforcer.002", speaker: "enforcer", register: "alien_corporate", ja: "侵入者を確認。照射を集中いたします。", en: "Intruder confirmed. Concentrating the beams.", duration_s: 3.9, repeatable: true}
  - {id: "ch06.b02.enforcer.003", speaker: "enforcer", register: "alien_corporate", ja: "潜水中と推定。浮上をお待ちいたします。", en: "Presumed submerged. We will await surfacing.", duration_s: 3.9, repeatable: true}
  - {id: "ch06.b03.kohagi.001", speaker: "scout", register: "scout_terse", ja: "弦。張って。", en: "Your string. String the bow.", duration_s: 1.9}
  - {id: "ch06.b03.kohagi.002", speaker: "scout", register: "scout_terse", ja: "角の石は長短の互い違い。そこが手掛かり。", en: "The corner stones alternate long and short. Those are your holds.", duration_s: 4.4}
  - {id: "ch06.b03.kohagi.003", speaker: "scout", register: "scout_terse", ja: "上、石落とし。……止まって。", en: "Drop-bay above. …Freeze.", duration_s: 2.9, repeatable: true}
  - {id: "ch06.b03.enforcer.001", speaker: "enforcer", register: "alien_corporate", ja: "壁面に債務者。落下による回収を試みます。", en: "Debtor on the wall. Attempting recovery by fall.", duration_s: 4.3, repeatable: true}
  - {id: "ch06.b03.kohagi.004", speaker: "scout", register: "scout_terse", ja: "あたしは屋根に回る。中は、あんたが。", en: "I'll take the roof. Inside is yours.", duration_s: 3.2}
  - {id: "ch06.b04.iota.001", speaker: "clerk", register: "manual_keigo", ja: "申し訳ございません、ただいま監査が——", en: "My apologies. An audit is under way—", duration_s: 3.1}
  - {id: "ch06.b04.kohagi.001", speaker: "scout", register: "scout_terse", ja: "窓から見てる。光る柱の目が、回ってる。", en: "I'm at the window. The glowing pillar's eye is turning.", duration_s: 3.7}
  - {id: "ch06.b04.kohagi.002", speaker: "scout", register: "scout_terse", ja: "目が背を向けたら、節を抜いて。三つ。", en: "When the eye turns away, pull a node. Three.", duration_s: 3.5}
  - {id: "ch06.b04.kohagi.003", speaker: "scout", register: "scout_terse", ja: "首を傾げたら、怪しんでる。まだ間に合う。", en: "A tilted head means suspicion. You still have time.", duration_s: 3.6}
  - {id: "ch06.b04.auditor.001", speaker: "auditor", register: "alien_corporate", ja: "第一節、応答なし。……記載漏れでしょうか。", en: "Node one, no response. …An omission in the record?", duration_s: 4.2, repeatable: true}
  - {id: "ch06.b04.auditor.002", speaker: "auditor", register: "alien_corporate", ja: "……おや。帳尻が合いませんね。", en: "Hm. The figures do not reconcile.", duration_s: 2.9, repeatable: true}
  - {id: "ch06.b04.auditor.003", speaker: "auditor", register: "alien_corporate", ja: "警報を、起票いたします！", en: "Filing an alarm!", duration_s: 2.3, repeatable: true}
  - {id: "ch06.b04.enforcer.001", speaker: "enforcer", register: "alien_corporate", ja: "音源、未登録。確認いたします。", en: "Unregistered sound. Verifying.", duration_s: 3.2, repeatable: true}
  - {id: "ch06.b04.enforcer.002", speaker: "enforcer", register: "alien_corporate", ja: "延滞者を発見。回収に移ります。", en: "Delinquent located. Proceeding to collection.", duration_s: 3.3, repeatable: true}
  - {id: "ch06.b04.enforcer.003", speaker: "enforcer", register: "alien_corporate", ja: "勘定を、再照合いたします。", en: "Re-reconciling the count.", duration_s: 2.6, repeatable: true}
  - {id: "ch06.b04.enforcer.004", speaker: "enforcer", register: "alien_corporate", ja: "誤差として処理いたします。", en: "Recording it as a rounding error.", duration_s: 2.4, repeatable: true}
  - {id: "ch06.b04.enforcer.005", speaker: "enforcer", register: "alien_corporate", ja: "損切りいたします。後退。", en: "Cutting losses. Withdrawing.", duration_s: 2.4, repeatable: true}
  - {id: "ch06.b04.enforcer.006", speaker: "enforcer", register: "alien_corporate", ja: "職員一名、未稼働。監査を要請いたします。", en: "One staff member non-performing. Requesting an audit.", duration_s: 4.4, repeatable: true}
  - {id: "ch06.b04.kohagi.004", speaker: "scout", register: "scout_terse", ja: "石板、借りる。水門で帰り道を守る。", en: "I'll take the slate. I'll hold the gate for the way home.", duration_s: 3.8}
  - {id: "ch06.b05.nyaakoto.001", speaker: "samurai", register: "samurai_polite", ja: "……イオタ殿か。", en: "…Are you Iota?", duration_s: 1.5}
  - {id: "ch06.b05.iota.001", speaker: "clerk", register: "manual_keigo", ja: "は、はい。会計補イオタでございます。", en: "Y-yes. Junior Auditor Iota, at your service.", duration_s: 3.1}
  - {id: "ch06.b05.nyaakoto.002", speaker: "samurai", register: "samurai_plain", ja: "箱の中に、いたのか。", en: "You were in the crate?", duration_s: 1.8}
  - {id: "ch06.b05.iota.002", speaker: "clerk", register: "manual_keigo", ja: "……大変、快適でございました。", en: "It was… comfortable.", duration_s: 2.9}
  - {id: "ch06.b05.nyaakoto.003", speaker: "samurai", register: "samurai_plain", ja: "なぜ、我らに文を寄こした。", en: "Why did you send us word?", duration_s: 2.3}
  - {id: "ch06.b05.iota.003", speaker: "clerk", register: "manual_keigo", ja: "計算しました。四百年分。", en: "I ran the numbers. Four hundred years' worth.", duration_s: 3.0}
  - {id: "ch06.b05.iota.004", speaker: "clerk", register: "manual_keigo", ja: "閉じない帳簿は、帳簿ではございません。……判決でございます。", en: "A ledger that never closes is not a ledger. It is a sentence.", duration_s: 5.4}
  - {id: "ch06.b05.iota.005", speaker: "clerk", register: "manual_keigo", ja: "鍵板様と、護身の針銃を。一度も撃っておりません。", en: "The honored key-slate, and my needle gun. Never once fired.", duration_s: 4.8}
  - {id: "ch06.b05.iota.006", speaker: "clerk", register: "manual_keigo", ja: "金庫番エスクロ様には、目がございません。耳で帳尻を合わせます。", en: "Vault Warden Eskro has no eyes. He balances the books by ear.", duration_s: 5.6}
  - {id: "ch06.b05.iota.007", speaker: "clerk", register: "manual_keigo", ja: "それと……記録庫の番は土地のお侍様。鷲尾様と申されます。", en: "Also… the archive guard is a local samurai. A Washio.", duration_s: 5.8}
  - {id: "ch06.b05.nyaakoto.004", speaker: "samurai", register: "samurai_plain", ja: "……虎之介。", en: "…Toranosuke.", duration_s: 1.5}
  - {id: "ch06.b05.iota.008", speaker: "clerk", register: "manual_keigo", ja: "わたくしはここで照合盤を見て、巡回をお知らせいたします。", en: "I will watch the reconciliation board here and report the patrols.", duration_s: 4.9}
  - {id: "ch06.b06.iota.001", speaker: "clerk", register: "manual_keigo", ja: "回廊に監査官様が四名、執行兵が二名。棚の上に目録が二機。", en: "Aisles: four auditors, two enforcers. Two drones over the shelves.", duration_s: 6.6}
  - {id: "ch06.b06.iota.002", speaker: "clerk", register: "manual_keigo", ja: "監査官様は戦えませんが、警報台へ走られます。", en: "Auditors cannot fight, but they will run for the alarm.", duration_s: 4.3}
  - {id: "ch06.b06.nyaakoto.001", speaker: "samurai", register: "samurai_plain", ja: "石垣の崩れか。……礫になる。", en: "Broken rampart stone. …These will do for throwing.", duration_s: 3.4}
  - {id: "ch06.b06.kohagi.001", speaker: "scout", register: "scout_terse", ja: "礫を投げて。音のした方を、あいつら見に行く。", en: "Throw a stone. They'll go and look where it lands.", duration_s: 4.0}
  - {id: "ch06.b06.auditor.001", speaker: "auditor", register: "alien_corporate", ja: "会計補イオタ、本日無断欠勤。減給処理いたします。", en: "Junior Auditor Iota, absent without notice. Processing a pay cut.", duration_s: 5.2}
  - {id: "ch06.b06.auditor.002", speaker: "auditor", register: "alien_corporate", ja: "金庫番様が、今夜はお目覚めです。筆の音も、お控えを。", en: "The Warden is awake tonight. Keep even your brushstrokes quiet.", duration_s: 5.2}
  - {id: "ch06.b06.auditor.003", speaker: "auditor", register: "alien_corporate", ja: "物音、一件。記録いたします。", en: "One noise. Logging it.", duration_s: 3.0, repeatable: true}
  - {id: "ch06.b06.kohagi.002", speaker: "scout", register: "scout_terse", ja: "鳴く床。真ん中は鳴る。壁際の端だけ、黙ってる。", en: "A singing floor. The middle chirps. Only the wall edge is silent.", duration_s: 4.7}
  - {id: "ch06.b06.auditor.004", speaker: "auditor", register: "alien_corporate", ja: "……鶯？　夜に、でございますか。", en: "…A nightingale? At night?", duration_s: 2.7, repeatable: true}
  - {id: "ch06.b06.iota.003", speaker: "clerk", register: "manual_keigo", ja: "その杉戸の先に、記帳の間と記録庫。……鷲尾様も、そちらに。", en: "Past that cedar door: the Registry Hall and the archive. …Washio too.", duration_s: 6.0}
  - {id: "ch06.b07.iota.001", speaker: "clerk", register: "manual_keigo", ja: "押収品庫でございます。鍵板様をかざせば、棚が開きます。", en: "The seized-goods store. Raise the key-slate and the lockers open.", duration_s: 5.1}
  - {id: "ch06.b07.nyaakoto.001", speaker: "samurai", register: "samurai_plain", ja: "空紋の扇……子どもの物まで、禁制品か。", en: "A Sora-mon fan… Even a child's toy is contraband.", duration_s: 4.0}
  - {id: "ch06.b07.nyaakoto.002", speaker: "samurai", register: "samurai_plain", ja: "田右衛門殿の水利絵図……谷へ返す。", en: "Headman Taemon's water-rights map. It goes back to the valley.", duration_s: 4.2}
  - {id: "ch06.b07.nyaakoto.003", speaker: "samurai", register: "samurai_plain", ja: "提灯街だけが、温かい色をしている。", en: "Only the Lantern Ward still glows warm.", duration_s: 3.1}
  - {id: "ch06.b08.iota.001", speaker: "clerk", register: "manual_keigo", ja: "記帳の間でございます。帳台は三つ。田方、町方、職方。", en: "The Registry Hall. Three desks: fields, town and crafts.", duration_s: 5.5}
  - {id: "ch06.b08.kohagi.001", speaker: "scout", register: "scout_terse", ja: "蝋燭は手で覆って。遅くなるけど、見えにくい。", en: "Cup the candle. It's slower, but harder to see.", duration_s: 4.0}
  - {id: "ch06.b08.nyaakoto.001", speaker: "samurai", register: "samurai_plain", ja: "雁皮紙を重ねて、透かし写す。", en: "Thin gampi paper over the page. I trace it through.", duration_s: 3.4}
  - {id: "ch06.b08.iota.002", speaker: "clerk", register: "manual_keigo", ja: "利率は年五割。夜ごとに、利が付きます。", en: "The rate is fifty percent a year, added nightly.", duration_s: 3.9}
  - {id: "ch06.b08.iota.003", speaker: "clerk", register: "manual_keigo", ja: "恐れ入りますが、この帳簿は、閉じない仕様でございます。", en: "Pardon me, but this ledger is designed never to close.", duration_s: 4.7}
  - {id: "ch06.b08.auditor.001", speaker: "auditor", register: "alien_corporate", ja: "町方帳、本日分の利を加算。……美しい曲線です。", en: "Town ledger: today's interest added. …A beautiful curve.", duration_s: 5.1}
  - {id: "ch06.b08.auditor.002", speaker: "auditor", register: "alien_corporate", ja: "右肩上がりは、秩序の証でございます。", en: "A rising line is proof of order.", duration_s: 3.4}
  - {id: "ch06.b08.auditor.003", speaker: "auditor", register: "alien_corporate", ja: "……灯り？　温かい色の灯りは、支給しておりません。", en: "…A light? Warm lights are not standard issue.", duration_s: 4.5, repeatable: true}
  - {id: "ch06.b09.toranosuke.001", speaker: "rival", register: "rival_brash", ja: "来ると思っていた。お前は、退くことを知らん。", en: "I knew you would come. You never learned to stay away.", duration_s: 3.9}
  - {id: "ch06.b09.nyaakoto.001", speaker: "samurai", register: "samurai_plain", ja: "虎之介。そこを退いてくれ。", en: "Toranosuke. Stand aside.", duration_s: 2.5}
  - {id: "ch06.b09.toranosuke.002", speaker: "rival", register: "rival_brash", ja: "退けば、鷲尾の家が潰れる。", en: "If I stand aside, the House of Washio falls.", duration_s: 3.0}
  - {id: "ch06.b09.toranosuke.003", speaker: "rival", register: "rival_brash", ja: "礼はいい。抜け、ニャーコト。今度は竹じゃない。", en: "Skip the bow. Draw, Nyaakoto. This time it is not bamboo.", duration_s: 3.9}
  - {id: "ch06.b09.toranosuke.004", speaker: "rival", register: "rival_brash", ja: "遅い！", en: "Too slow!", duration_s: 1.5, repeatable: true}
  - {id: "ch06.b09.toranosuke.005", speaker: "rival", register: "rival_brash", ja: "……鷲尾家。これは……。", en: "…House of Washio. This is…", duration_s: 2.6}
  - {id: "ch06.b09.nyaakoto.002", speaker: "samurai", register: "samurai_plain", ja: "元本百二十石。返済四十石。残高、百九十石。", en: "Principal 120 koku. Paid 40. Still owed: 190.", duration_s: 5.5}
  - {id: "ch06.b09.nyaakoto.003", speaker: "samurai", register: "samurai_plain", ja: "買取は三十石。……彼らは、三十石で買っている。", en: "Bought at thirty. …They paid thirty koku for your debt.", duration_s: 4.9}
  - {id: "ch06.b09.toranosuke.006", speaker: "rival", register: "rival_brash", ja: "黙れ！　黙って、構えろ！", en: "Quiet! Quiet, and take your stance!", duration_s: 2.4}
  - {id: "ch06.b09.sekireisai.001", speaker: "mentor", register: "mentor_archaic", ja: "刀なき時こそ、手の内を見よ。", en: "When you have no sword, watch his hands.", duration_s: 2.7}
  - {id: "ch06.b09.sekireisai.002", speaker: "mentor", register: "mentor_archaic", ja: "無刀とは、奪う芸にあらず。斬られぬための心得じゃ。", en: "No-sword is not an art of taking. It is how one is not cut.", duration_s: 4.4}
  - {id: "ch06.b09.toranosuke.007", speaker: "rival", register: "rival_brash", ja: "刀を納めるだと？　俺を、侮るな！", en: "You sheathe your sword? Do not mock me!", duration_s: 2.8}
  - {id: "ch06.b09.toranosuke.008", speaker: "rival", register: "rival_brash", ja: "全部、払ったんだ！", en: "I paid all of it!", duration_s: 1.8}
  - {id: "ch06.b09.toranosuke.009", speaker: "rival", register: "rival_brash", ja: "なのに、なぜ減らん！", en: "Then why will it not shrink?!", duration_s: 1.8}
  - {id: "ch06.b09.toranosuke.010", speaker: "rival", register: "rival_brash", ja: "……立て。こんな終わり方は、させん。", en: "…Get up. I will not let it end like this.", duration_s: 3.3, repeatable: true}
  - {id: "ch06.b10.toranosuke.001", speaker: "rival", register: "rival_humbled", ja: "毎月払った。増えた。", en: "I paid every month. It grew.", duration_s: 2.1}
  - {id: "ch06.b10.toranosuke.002", speaker: "rival", register: "rival_humbled", ja: "払うほど、利が肥える。……俺は、何を守っていた。", en: "The more I paid, the fatter it grew. …What was I guarding?", duration_s: 4.5}
  - {id: "ch06.b10.nyaakoto.001", speaker: "samurai", register: "samurai_plain", ja: "刀は、民から預かるものだ。……先生の言葉だ。", en: "A blade is held in trust from the people. …Sensei's words.", duration_s: 4.4}
  - {id: "ch06.b10.toranosuke.003", speaker: "rival", register: "rival_humbled", ja: "……受け取れん。負けた者の刀だ。", en: "…I cannot take it. It is a beaten man's sword.", duration_s: 3.3}
  - {id: "ch06.b10.nyaakoto.002", speaker: "samurai", register: "samurai_plain", ja: "なら、預ける。民のために抜け。", en: "Then I entrust it to you. Draw it for the people.", duration_s: 3.3}
  - {id: "ch06.b10.toranosuke.004", speaker: "rival", register: "rival_humbled", ja: "これを。鷲尾虎之介、誓いの証だ。", en: "Take this. My pledge, as Washio Toranosuke.", duration_s: 3.4}
  - {id: "ch06.b10.nyaakoto.003", speaker: "samurai", register: "samurai_plain", ja: "確かに、預かった。", en: "I will hold it in trust.", duration_s: 1.6}
  - {id: "ch06.b10.toranosuke.005", speaker: "rival", register: "rival_humbled", ja: "この羽織、まだ使える。イオタは俺が水門まで「連行」する。", en: "This haori still has its uses. I will 'escort' Iota to the gate.", duration_s: 4.8}
  - {id: "ch06.b10.nyaakoto.004", speaker: "samurai", register: "samurai_plain", ja: "印刷所は、私が止める。", en: "I will stop the presses.", duration_s: 2.3}
  - {id: "ch06.b10.toranosuke.006", speaker: "rival", register: "rival_humbled", ja: "……死ぬなよ、弟弟子。", en: "…Do not die, little brother.", duration_s: 2.4}
  - {id: "ch06.b11.kohagi.001", speaker: "scout", register: "scout_terse", ja: "虎之介とイオタ、水門に着いた。", en: "Toranosuke and Iota reached the gate.", duration_s: 3.0}
  - {id: "ch06.b11.iota.001", speaker: "clerk", register: "manual_keigo", ja: "親機は三台。吊られた灯りが目印でございます。", en: "Three master presses. Look for the hanging lamps.", duration_s: 4.3}
  - {id: "ch06.b11.kohagi.002", speaker: "scout", register: "scout_terse", ja: "槌が落ちる音に、足音を隠して。", en: "Move when the press slams. It hides your steps.", duration_s: 3.2}
  - {id: "ch06.b11.nyaakoto.001", speaker: "samurai", register: "samurai_plain", ja: "鋼蔵殿の楔、三本。ちょうどだ。", en: "Kōzō's wedges. Three. Just enough.", duration_s: 3.0}
  - {id: "ch06.b11.auditor.001", speaker: "auditor", register: "alien_corporate", ja: "本日の督促状、四千二百枚。紙が足りません。", en: "Dunning notices today: four thousand two hundred. Paper is short.", duration_s: 4.7}
  - {id: "ch06.b11.auditor.002", speaker: "auditor", register: "alien_corporate", ja: "提灯街から、また和紙を差し押さえましょう。", en: "We will seize more washi from the Lantern Ward.", duration_s: 3.8}
  - {id: "ch06.b11.auditor.003", speaker: "auditor", register: "alien_corporate", ja: "親機、停止。……点検いたします。", en: "Master press stopped. …Inspecting.", duration_s: 3.4, repeatable: true}
  - {id: "ch06.b11.enforcer.001", speaker: "enforcer", register: "alien_corporate", ja: "印刷妨害を確認。債務に上乗せいたします。", en: "Press sabotage confirmed. It will be added to your debt.", duration_s: 4.3, repeatable: true}
  - {id: "ch06.b12.iota.001", speaker: "clerk", register: "manual_keigo", ja: "い、いけません。印刷機と金庫核は、同じ流れに——", en: "N-no. The presses share a current with the vault core—", duration_s: 4.4}
  - {id: "ch06.b12.valamort.001", speaker: "banker", register: "inscription", ja: "契約は永遠だ。誰も帳簿からは逃れられぬ。", en: "The contract is eternal. No one escapes the ledger.", duration_s: 4.8, catalog_anchor: 2}
  - {id: "ch06.b12.nyaakoto.001", speaker: "samurai", register: "samurai_plain", ja: "……アモルトの声か。", en: "…Amort's voice.", duration_s: 1.8}
  - {id: "ch06.b12.eskro.001", speaker: "boss_eskro", register: "alien_corporate", ja: "停電を記録。……照合を、開始いたします。", en: "Outage recorded. …Commencing reconciliation.", duration_s: 4.2}
  - {id: "ch06.b12.kohagi.001", speaker: "scout", register: "scout_terse", ja: "ニャーコト、聞こえる？　下は真っ暗——", en: "Nyaakoto, can you hear me? It's pitch black down—", duration_s: 3.3}
  - {id: "ch06.b13.kohagi.001", speaker: "scout", register: "scout_terse", ja: "目がないなら、音を消して。動くのは、鳴いた後。", en: "It has no eyes. Kill your sound. Move after it chirps.", duration_s: 4.2}
  - {id: "ch06.b13.nyaakoto.001", speaker: "samurai", register: "samurai_plain", ja: "……見えぬ相手か。なら、灯りは使える。", en: "…He cannot see. Then the flame is safe.", duration_s: 3.7}
  - {id: "ch06.b13.eskro.002", speaker: "boss_eskro", register: "alien_corporate", ja: "照合。", en: "Reconciling.", duration_s: 1.5, repeatable: true}
  - {id: "ch06.b13.eskro.003", speaker: "boss_eskro", register: "alien_corporate", ja: "……不一致。", en: "…Mismatch.", duration_s: 1.5, repeatable: true}
  - {id: "ch06.b13.eskro.004", speaker: "boss_eskro", register: "alien_corporate", ja: "……誤差。", en: "…A rounding error.", duration_s: 1.5, repeatable: true}
  - {id: "ch06.b13.nyaakoto.002", speaker: "samurai", register: "samurai_plain", ja: "跳んだ後が、隙だ。", en: "After the leap, he is open.", duration_s: 1.8}
  - {id: "ch06.b13.eskro.005", speaker: "boss_eskro", register: "alien_corporate", ja: "端数、切り捨て。", en: "Fractions: discarded.", duration_s: 1.8, repeatable: true}
  - {id: "ch06.b13.eskro.006", speaker: "boss_eskro", register: "alien_corporate", ja: "水は、帳尻を誤魔化しません。", en: "Water does not cook the books.", duration_s: 2.8}
  - {id: "ch06.b13.eskro.007", speaker: "boss_eskro", register: "alien_corporate", ja: "棚卸し。", en: "Stocktaking.", duration_s: 1.5, repeatable: true}
  - {id: "ch06.b13.eskro.008", speaker: "boss_eskro", register: "alien_corporate", ja: "取り立て。", en: "Collection.", duration_s: 1.5, repeatable: true}
  - {id: "ch06.b13.eskro.009", speaker: "boss_eskro", register: "alien_corporate", ja: "全件照合。猟犬を、放ちます。", en: "Full reconciliation. Releasing the hounds.", duration_s: 3.1}
  - {id: "ch06.b13.kohagi.002", speaker: "scout", register: "scout_terse", ja: "小さいのが二つ。先に落として。灯りも見られる。", en: "Two small ones. Drop them first. They can see your flame.", duration_s: 4.3}
  - {id: "ch06.b13.eskro.010", speaker: "boss_eskro", register: "alien_corporate", ja: "……照合、不能。", en: "…Unable to reconcile.", duration_s: 2.0}
  - {id: "ch06.b13.nyaakoto.003", speaker: "samurai", register: "samurai_plain", ja: "その帳簿は、ここで閉じる。", en: "This ledger closes here.", duration_s: 2.3}
  - {id: "ch06.b14.toranosuke.001", speaker: "rival", register: "rival_humbled", ja: "遅いぞ。水が上がってる。", en: "You are late. The water is rising.", duration_s: 2.3}
  - {id: "ch06.b14.iota.001", speaker: "clerk", register: "manual_keigo", ja: "わたくし、泳いだことが……ございません。", en: "I have never… swum before.", duration_s: 3.2}
  - {id: "ch06.b14.toranosuke.002", speaker: "rival", register: "rival_humbled", ja: "背に乗れ。しっかり掴まってろ。", en: "Get on my back. Hold on tight.", duration_s: 2.7}
  - {id: "ch06.b14.kohagi.001", speaker: "scout", register: "scout_terse", ja: "水門、半分まで上げた。これ以上は音が出る。", en: "Gate's half up. Any higher and it'll make noise.", duration_s: 4.3}
  - {id: "ch06.b14.enforcer.001", speaker: "enforcer", register: "alien_corporate", ja: "停電につき、手作業で捜索いたします。", en: "Owing to the outage, we are searching by hand.", duration_s: 3.5}
  - {id: "ch06.b14.nyaakoto.001", speaker: "samurai", register: "samurai_plain", ja: "ここから潜る。八つ、数えろ。", en: "We dive from here. Count to eight.", duration_s: 2.6}
  - {id: "ch06.b14.kohagi.002", speaker: "scout", register: "scout_terse", ja: "抜けた。舟は葦の陰。右に灯りの舟が一艘。", en: "You're out. Our boat's in the reeds. A lamp boat to the right.", duration_s: 4.3}
  - {id: "ch06.b15.oyuki.001", speaker: "leader", register: "business_keigo", ja: "お帰りなさいませ。……写しを、拝見いたします。", en: "Welcome back. …May I see the copies?", duration_s: 4.1}
  - {id: "ch06.b15.oyuki.002", speaker: "leader", register: "business_keigo", ja: "元本、一万八千石。年五割。期限は十四年。", en: "Principal: eighteen thousand koku. Fifty percent a year. Fourteen years.", duration_s: 5.1}
  - {id: "ch06.b15.oyuki.003", speaker: "leader", register: "business_keigo", ja: "期限の日には五百二十五万石。谷の、四百年分でございます。", en: "At term: 5.25 million koku. Four hundred years of our valley.", duration_s: 6.0}
  - {id: "ch06.b15.iota.001", speaker: "clerk", register: "manual_keigo", ja: "わたくしの計算と、一致いたしました。", en: "That matches my calculation.", duration_s: 3.1}
  - {id: "ch06.b15.toranosuke.001", speaker: "rival", register: "rival_humbled", ja: "……俺の家の分も、そこに入っているのか。", en: "…My house's page is in there too?", duration_s: 3.6}
  - {id: "ch06.b15.oyuki.004", speaker: "leader", register: "business_keigo", ja: "はい。皆の分が。だから、皆の前に貼るのです。", en: "Yes. Everyone's is. That is why we post it before everyone.", duration_s: 4.0}
  - {id: "ch06.b15.nyaakoto.001", speaker: "samurai", register: "samurai_polite", ja: "人を縛る文字より、人が作る明日を選ぶ。", en: "I choose the future people build over the words that bind them.", duration_s: 4.8, catalog_anchor: 3}
  - {id: "ch06.b16.resident.001", speaker: "resident", register: "kamigata_commoner", ja: "……うちの借り、元はたった二俵やで。", en: "…Our debt started at just two bales.", duration_s: 3.3}
  - {id: "ch06.b16.resident.002", speaker: "resident", register: "kamigata_commoner", ja: "字ぃ読めへん。誰か、読んでくれ。", en: "I can't read. Someone read it for me.", duration_s: 2.8}
  - {id: "ch06.b16.tokichi.001", speaker: "lantern_maker", register: "artisan_gentle", ja: "どれ、わしが読もう。……おまえさんの家は、ここや。", en: "Here, let me read it. …Your house is this line.", duration_s: 4.1}
  - {id: "ch06.b16.oyuki.001", speaker: "leader", register: "business_keigo", ja: "帳は、民の前に。五箇条の五でございます。", en: "The ledger belongs before the people. Article five.", duration_s: 3.9}
  - {id: "ch06.b16.tetsugoro.001", speaker: "gunsmith", register: "artisan_blunt", ja: "ええ鉄や。鍬になる。", en: "Good iron. It'll make hoes.", duration_s: 1.9}
  - {id: "ch06.b16.toranosuke.001", speaker: "rival", register: "rival_humbled", ja: "旗艦だ。谷の物を、あれに積んでいる。", en: "The flagship. They are loading the valley's goods onto it.", duration_s: 3.8}
  - {id: "ch06.b16.nyaakoto.001", speaker: "samurai", register: "samurai_plain", ja: "なら、取り返しに行く。", en: "Then we go and take them back.", duration_s: 2.0}
```
