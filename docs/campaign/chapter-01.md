# Chapter 1: 第一章 道場の修行 (Dojo Apprenticeship)

> **Monetary boundary (bible §2).** In this chapter, as in the whole campaign, SORA XOR (and the registry that leads to it) is a production-only storytelling premise. XOR is cut only against finished, inspected goods, is never shown as a balance or converted, and has no link to multiplayer XOR bonds, NFTs, wallets or IrohaConnect. It makes no claim about real-world money, investment or policy, and it does not describe the real SORA network or the design in the SORA Nexus article. **Review note (C1 lead, 2026-09-25):** names, calendar, speaker ids, Japanese punctuation and YAML field names in this file follow bible §9.1, §12.5 and §18.

**Status:** production design and script for `ch01_dojo`, written against the [campaign story bible](story-bible.md). Nothing here is implemented. All numbers are **proposals** for the lanes that own them: L1 for beats, layouts and saves; L2 for opponents and archery; L4 for prompts and UI; L5 for music and barks; C2 and C3 for spaces; C4 for the mission; C9 for cinematics. Native Japanese review (B7), historian and practitioner review, and equine animation review are still pending. The places are listed in §3, the beats in §4, the script in §5, accuracy notes in §6, assets in §7, hand-offs and deviations from the bible in §8, and the machine-readable data in §9.

**Related sources:** [story bible](story-bible.md) §3, §4, §6, §9, §12–§20; [catalog.json](../../Content/Data/catalog.json) (chapter 0); [offline acceptance](offline-acceptance.md); [historical arms](../historical-arms.md); [horse tack references](../historical-horse-tack-art-reference.md); [SORA kamon runtime art](../sora-kamon-runtime-art.md); [Estate mesh terrain](../mesh-terrain-nyaagyu.md); `Source/SoraArena/Public/SoraDojoRules.h` (read only).

---

## 0. At a glance

| Item | Value |
|---|---|
| Chapter id | `ch01_dojo` (catalog chapter index 0, map 0) |
| Title | 第一章 道場の修行 / Chapter 1: Dojo Apprenticeship |
| Target play time | **40 min (2,400 s)**, first playthrough on Normal (真剣), cinematics watched |
| Mix (min) | Combat and duels 22 · Exploration 4 · Stealth 0 · Production 3 · Mounted 3 · Cinematic and dialogue 8 (matches bible §10) |
| Beats | 13, plus 6 collectibles (not counted as beats) |
| Checkpoints | 10 (largest gap 360 target-seconds, b11 → b12) |
| Script | 117 voiced lines and 22 tutorial prompts (139 rows) |
| Weapons unlocked | 18 和弓 yumi (b07), 0 刀 katana (b12) |
| Mechanics unlocked | `kamae`, `maai_ring` (b02) · `awase` (b03) · `marobashi` (b04) · `mount` (b06) · `yumi` (b07) · `manufacture` (b09) |
| Production sites | site 0 → b02 間合いの稽古場 · site 1 → b03 木刀の試合場 · site 2 → b09 道場の鍛冶場 |
| Registry | 矢 12本 (arrows ×12), written at b09 |
| Boss | None. The chapter's climax is a non-lethal 袋竹刀 (fukuro-shinai) duel with Washio Toranosuke (b11) |
| Horse | Yes: Kurimaru, tack-up and a walk-and-trot ride (b06) |
| Enemies | None. There are no aliens on the ground until ch02; the sky splits in the final cinematic |
| Fail states | No death is possible. Lessons retry in place; the duel allows retries and then continues on a loss branch |

---

## 1. Synopsis

**Late spring, Genna 9 (1623).** Dawn at the Tsumagizaka Dōjō, the Nyaagyu house's sword hall on the terrace above the estate. The pupils finish a hundred 素振り (practice swings). Sekireisai asks Nyaakoto how many of those swings were truly his. "Sixty, perhaps." "Honest. Win back the other forty in practice." The camera passes the name board: Toranosuke's plaque in the senior row, with no one standing below it.

The morning is a lesson in distance and timing. Against Sekireisai, Nyaakoto learns 正眼 (seigan) and the 水月 (suigetsu, "moon in water") distance read: stand where the opponent's sword cannot reach and your own can. Against the pupils Matsukichi and Takemaru he learns to receive a cut, to meet it (合わせ, awase), to let the blade recover before cutting again, and then, in the yard, to roll to the flank after meeting a cut (転, marobashi). Toranosuke rides in late on his black-bay stallion Arashi. The pupils whisper that he met "the man from Osaka" again. Everyone, Toranosuke included, bows around Baiō, the oldest pupil, who is asleep in the veranda's one sunbeam.

Sekireisai sends Nyaakoto to the stable. Kurimaru, his chestnut mare, accepts the saddle, the girth and the stirrups, but refuses the bit until he finds the ear of barley in his sleeve. He rides the hill lane to the archery range, where Baiō, wide awake now, hands him his yumi. Nyaakoto shoots at the 28 m mark and then at swinging straw targets. Six shafts bend on a stone in the target mound. The footpath home runs through the cedar wood of the One-Claw Stone, which the house's founder is said to have split with a single claw. At the dojo smithy, Tetsugorō makes him straighten and refletch the arrows, count all twelve, and write them in the smithy's book: "What you make, you count and keep."

In the afternoon, on the estate veranda, Sekireisai speaks of 殺人刀 and 活人剣, the sword that kills and the sword that gives life, and says they are one blade. Toranosuke interrupts and demands a bout: "Today is all I have. Tomorrow, a man comes from Osaka." They fight first to three points with fukuro-shinai in the courtyard. Win or lose, Sekireisai then returns Nyaakoto's katana: 「刀は民から預かるものじゃ。」 ("A blade is held in trust from the people.") At dusk a seam of cold light opens in the western sky. Lights descend toward Nekoyama. Baiō rings the alarm bell, and Sekireisai's last words of the chapter are an order to remember what Nyaakoto now holds in trust.

**Chapter arc.** Nyaakoto begins as a capable pupil who swings without full intent and ends holding a real blade he has been told he does not own. Toranosuke's haste, which is really his house's debt, is set up as the thing that will break him. The first registry entry, twelve arrows written in a smith's day-book, is the seed of the League's production registry.

---

## 2. Time, weather and lighting

The chapter runs through one day in late April by the solar calendar: 元和九年三月下旬, late in the lunar 3rd month (campaign calendar, bible §9.1). The sun angles below are approximate values for the Yamato highlands (about 34.7° N) and are meant for lighting blockout. Azimuth is a compass bearing: 90° is +X (east) in the layout frame.

| Beat | Clock | Sun (az / el) | Key light | Weather and FX | Lighting notes | Mac fallback |
|---|---|---|---|---|---|---|
| b01 | 05:20 dawn (明け六つ) | 72° / 2° | Sky 6,500 K; first sun 4,500 K through thin cloud | Valley mist, dust motes indoors, birdsong (uguisu) | Raking bars of light through the east 連子窓 across the hinoki floor; the SORA 幕 behind the master's seat reads in silhouette | Software Lumen; cap dust motes at 400 |
| b02–b04 | 06:00–08:30 | 78–95° / 8–35° | Sun 5,200 K through thin cloud; sky 6,500 K | Thin high overcast | Interior lit mainly by bounce from the yard; b04 yard in soft, even light for readable footwork | Same |
| b05 | 09:00 | 104° / 45° | 5,200 K | Clearing | The only sunbeam on the south 縁側 falls at its east end, where the sun slips under the eave from the side | Same |
| b06 | 10:00 | 118° / 55° | 5,400 K | Light breeze | Dappled shade in cedar and tea hedges; first view of the whole valley at the hill shoulder (14 m) | Reduce hedge foliage density |
| b07 | 10:30–11:00 | 130–148° / 60–65° | 5,600 K | Breeze, no gameplay wind | The range runs south to north, so the sun is behind the archer and lights the target faces. Straw and paper targets must not bloom | Same |
| b08 | 11:15 | 155° / 67° | 5,600 K | Mist still pooled in the stream-fed hollow | God rays through cedar; the split stone sits in soft shade. The vista shows Nekoyama 2 ri (8 km) away through aerial haze | Height fog only; card ferns |
| b09 | 12:30 | 200° / 69° | Daylight bounce 6,000 K; hearth 1,700 K | Charcoal smoke, sparks, heat shimmer | Warm hearth key against cool daylight fill; shafts gleam when they are ready | Baked emissive hearth; cap sparks |
| b10 | 15:30 | 255° / 40° | 4,500 K | Clear, westerly breeze | Veranda half in shade; courtyard gravel warm | Same |
| b11 | 16:30 | 265° / 28° | Golden 3,800 K | Clear | The ring runs north–south so the low western sun is **side** light. Neither fighter looks into it. Long shadows help read footwork | Same |
| b12 | 17:30 | 275° / 16° | 3,500 K | Clear | Katana hand-over in low warm light under the eave | Same |
| b13 | 18:30 sunset (暮れ六つ) | 288° / 0° | Sunset 3,000 K; alien light 8,000 K cyan | Crows lifting, first lanterns lit | A thin seam of cold 8,000 K light opens across the warm sunset and cold lights descend toward the south-west. No readable ship silhouettes yet (ch02 reveals them). Respect the flash-reduction setting | Descending lights as emissive cards; one shadowed light |

---

## 3. Locations and layout

### 3.1 Chapter footprint

All positions are in metres. The origin is the centre of Arena 0, +X is east, +Y is north, and Z is height above the courtyard grade. **Arena 0 collision is not changed.** Every campaign-only space is a separate sublevel north and west of the arena wall, and the only way into the arena is a fade transition at the north wall (`vol_ch01_ura_mon`).

```
 N (+Y)
  ^          hill shoulder (22,102) +14 m ─── estate lane spl_ch01_umaba_lane (~300 m) ──┐
  |        ┌──────────────── lane follows the ridge west ──────────────────┐               │
  |        │                                                               │               │
  | [pl_matoba]  (targets north)   [pl_issoseki_wood 110 × 85 m]           │               │
  |  tsuri frames Y60–80 ▲           hokora (−118,100)                     │               │
  |  azuchi Y48          ▲           One-Claw Stone (−100,88) in hollow    │               │
  |  shajo  Y20  ● hitch ◄─lane      trail spl_ch01_wood_trail (~170 m) ───► smithy (−28,52) ── yard ── DOJO (0,61.6) ── stable (25,60)
  |                                  vista ledge (−90,26)  boundary stone (−60,34)          terrace Z +6 m
  |                                                                            爪木坂 steps, Y 34 → 26
  | ══════════════════════════ Arena 0 north wall (Y 25.5) ══ ura-mon fade (4.5,27.5) ══════════════════════
  |                          pl_estate_day: Arena 0, 64 × 52 m; north hall veranda (0,14); duel ring r 5 m at (0,0)
  +──────────────────────────────────────────────────────────────────────────────────────────────> E (+X)
                                        (not to scale)
```

| Sublevel | Contains | Streaming rule |
|---|---|---|
| `SL_Ch01_Tsumagizaka` | Dojo hall and yard, stable, smithy, 爪木坂 steps | Loaded b01–b10; unloaded after the ura-mon fade |
| `SL_Ch01_Lane` | Estate lane from the stable to the range | Loaded from b05 to the end of b07 |
| `SL_Ch01_Matoba` | Archery range | Loaded from b06 to the end of b08 |
| `SL_Ch01_IssosekiWood` | Wood and trail | Loaded from b07 to the end of b09 |
| Arena 0 plus `SL_Ch01_EstateActors` | Campaign NPCs, bell frame, ring rope and props only | Loaded from b09; campaign actors are non-colliding or use capsule collision only |

### 3.2 `pl_tsumagizaka_dojo`: 爪木坂道場 (Tsumagizaka Dōjō), hall, yard and veranda

- **Hall.** 6 × 5 ken (10.9 × 9.1 m interior) under an 入母屋 roof of ibushi kawara, with the SORA-mon 軒丸瓦 end tiles. The training floor is hinoki, 10.9 × 7.3 m (Y 57.1–64.4), raised 0.6 m above the yard. The 上座 (kamiza) is a 1.8 m platform along the north wall, raised 30 cm, carrying the 神棚, a 刀掛け sword rack and a hemp 幕 with the SORA mon dyed in indigo behind the master's seat. The west wall holds the 名札掛け: a 3.6 m board, headed by the mon, with two rows of plaques. The east wall is 羽目板 panelling with three 連子窓 slatted windows (the dawn light source). The south side is sliding 舞良戸 and 明障子 opening onto a 1.2 m 縁側 that wraps round the east side. The entrance (玄関) is at the south-west corner (−6.5, 56.5).
- **Yard.** 16 × 12 m of packed earth (Y 43.9–55.9). An old 欅 (zelkova) stands at the south-west corner (−7, 44.5) and a well with a 釣瓶 bucket at the south-east (6, 45). Both are at least 3 m from the yard's centre, so a marobashi roll never clips them. An optional 藤棚 (wisteria trellis) in flower can dress the east edge.
- **Routes.** Genkan ↔ yard ↔ stable (east, 20 m) ↔ smithy (west, 22 m) ↔ 爪木坂 steps (south, down to the arena's north wall).
- **Cover and obstacles.** None needed: there is no ranged combat. The well and zelkova are orientation landmarks.
- **Sightlines.** From the lesson mark the frame is Sekireisai → kamiza → SORA 幕. From the yard, the hall façade with its SORA eave tiles. From the veranda's east end, the stable and the lane climbing the hill.
- **Spawns and marks.** `ps_ch01_lesson_mark` (0, 58.6) facing north, 3.0 m from `ps_ch01_mentor_mark` (0, 61.6), so the player starts **outside** the maai band. `ps_ch01_yard_mark` (0, 48).

### 3.3 `pl_umaya`: 厩 (stable) and the estate lane

- **Stable.** 12.7 × 5.5 m (7 × 3 ken) board-walled building with a cedar-bark roof at (25, 60). It has three stalls along the north wall: Kurimaru (west), Arashi (middle, from b05) and a pack horse (east). The west end is a tack corner: the lacquered kura on a 鞍掛け stand, the abumi on pegs, cloth tazuna, the crupper, straw 馬沓 hanging on nails, a 飼葉桶 feed trough and straw bales.
- **Tie rail.** `ps_ch01_tie_rail` (21.8, 56.5). Kurimaru stands facing south, so tack-up happens on her **right** side, which is the side a period rider mounts from (§6.3).
- **Lane** `spl_ch01_umaba_lane`, about 300 m of packed earth 3–5 m wide. It climbs north-east to the hill shoulder (22, 102, +14 m), which has the first full view of the valley, follows the ridge west past tea hedges and a 道祖神 roadside stone, then runs south along the wood's west edge to the range's hitching post (−163, 22). Gait zones: walk 0–70 m, trot 70–240 m (the lane is straight and 5 m wide here), walk 240–300 m. A pheasant flushes from the hedge at 150 m.
- **Bounds.** Dry-stone retaining walls, tea hedges and bamboo fences. Leaving the lane is soft-blocked, and `auto_steer` is available as an accessibility setting.

### 3.4 `pl_matoba`: 的場・安土 (archery range)

- **Orientation.** The range runs south to north so the sun is behind the archer. The 射場 (shajō) is an 8 × 5 m open shed at the south end, with 弓立て racks, a 矢立て and a bench. Its inside wall carries collectible `ch01.c06`. The shooting line is `vol_ch01_shajo_line` (Y 19.5).
- **Kinteki lane.** A 28 m 矢道 lawn, 8 m wide (X −178…−170), runs to a 安土 sand mound 6 × 2.5 × 1.8 m under a small roof. The 尺二 (36 cm) paper target stands at `sp_ch01_kinteki_a` (−174, 48). A stone buried in the mound is the story reason for the bent shafts.
- **Long lane.** 8 m wide (X −186…−178). Three 吊り的 (hanging straw targets) hang from timber frames at 40, 50 and 60 m (Y 60, 70, 80) and swing ±1.5 m on a 3.2 s period.
- **看的所 (target keeper's hut).** At (−167, 50), behind an earth berm and outside the arrow corridor. Matsukichi calls hits from here and fetches arrows (矢取り).
- **Safety.** The arrow corridor `vol_ch01_matoba` (24 × 70 m) is fenced. The lane passes outside its east fence. The bow can be drawn only inside `vol_ch01_shajo_line` during b07.

### 3.5 `pl_issoseki_wood`: 一爪石の森 (One-Claw Stone Wood)

- **Size and planting.** 110 × 85 m of cedar (杉) and hinoki on a slope falling from +10 m (west) to +6 m (east). Moss and ferns cover the floor; this is where the bible's fern-contact gate applies.
- **Trail.** `spl_ch01_wood_trail`, about 170 m, runs from the range's south-east corner (−152, 30) in a loose S north past the stone hollow and east to the smithy's back gate (−36, 54.5). Walking straight through takes about 60 s.
- **Points of interest.** There are no map markers; each one is found by light, sound or path wear.
  - **One-Claw Stone** (−100, 88): a 3 m boulder split cleanly in two, in a hollow 2 m below the trail beside a stream. It carries a 注連縄 rope with 紙垂 streamers and offerings of rice and a sake cup. Collectible `ch01.c01` is a wooden plaque tied to the rope post. Mist pools here.
  - **Hokora** (−118, 100): a small roadside shrine, lore only.
  - **Vista ledge** (−90, 26): a rock shelf on the wood's south edge. Looking south-south-west, Nekoyama castle town and its castle hill are visible 2 ri away; ch02 raises the Debt Citadel there. A 鳴子 clapper hangs 45 m away across the ravine as the optional challenge.
  - **Boundary stone** (−60, 34): a 境石 carved with the house mon in relief, moss in the grooves. This is collectible `ch01.c02`.
- **Exit hint.** After 180 s, the smithy's hammer becomes audible from the east and a smoke plume shows above the trees.

### 3.6 `pl_dojo_smithy`: 道場の鍛冶場 (dojo smithy)

- **Structure.** A 6.4 × 5.5 m open-sided timber shed with a board roof at (−28, 52), west of the yard.
- **Stations.** `st_ch01_fuigo`: the sunken 火床 hearth and a 箱鞴 box bellows (not the later seesaw bellows). `st_ch01_hibachi`: a charcoal brazier for warming shafts. `st_ch01_tamegi`: the notched 矯め木 straightening block. `st_ch01_hagi_dai`: the fletching bench with a 膠鍋 glue pot, feather boxes and silk thread.
- **Dressing.** Anvil, quench tub, tongs rack, and two village matchlocks on wall pegs (foreshadowing ch04). The founder's tsuba hangs above the anvil (`ch01.c04`). The loft shelf holds the old day-book (`ch01.c05`).
- **Entry.** From the yard (east) or the wood's back gate (north-west).

### 3.7 `pl_estate_day`: 猫柳生の屋敷・昼 (Arena 0, day)

- **Existing arena.** 64 × 52 m inside the estate wall (existing `SM_Nyaagyu_EstateWall_4m` modules). The stone road runs east–west between the two gate frames at X −22.5 and +23 (the `SM_Nyaagyu_ToriiGate` meshes; in campaign mode they are dressed as 冠木門 residence gates, because a torii marks a shrine, not a samurai house; bible §15.2). Halls and kura stand at X −20, −10, 0, +10, +20 on both sides (Y ±18). Cover blocks sit at Y ±6.8 and ±8.8. All of this is unchanged.
- **Entry.** Down the 爪木坂 steps to `vol_ch01_ura_mon` outside the north wall, then a 1.2 s fade to `ps_ch01_estate_entry` (4.8, 23.6) in the 3.5 m gap between the north-centre hall and the kura to its east.
- **Veranda.** Sekireisai sits on the engawa of the north-centre hall (0, 14). In fiction this is the estate's 書院; it reuses the existing dojo-hall visual. `vol_ch01_estate_engawa` has a radius of 4 m.
- **Duel ring.** `vol_ch01_duel_ring`, radius 5 m at (0, 0), marked by a straw rope laid on the ground (a campaign actor). It is clear of the nearest cover corner by 7 m. Start marks are 4 m apart on the north–south axis: player (0, 2) facing south, Toranosuke (0, −2). Sekireisai judges from `ps_ch01_judge` (−5.8, 0), on the sun side. Pupils kneel along the ring's north edge (Y 5.6, X −2…+2); household members watch from beside the kura.
- **Legacy nodes.** The arena's production nodes at (−12.5, −7), (0, 10) and (12.5, −8) keep their training-kind props (sword racks and practice beam) as set dressing. In ch01 the sites are restored at the sublevel stations instead (§8).
- **Bell.** A 半鐘 hangs in a timber frame beside the east gate for b13. It is a campaign actor with no collision.

### 3.8 Trigger volumes

Every volume, point and spline, with coordinates, is in the YAML (§9 `layout`).

| Volume | Place | Centre (m) | Size / radius (m) | Use |
|---|---|---|---|---|
| `vol_ch01_dojo_floor` | `pl_tsumagizaka_dojo` | (0, 60.75, 8.1) | 10.9 × 7.3 × 3 | b02-b03 lesson ring (hinoki training floor) |
| `vol_ch01_dojo_yard` | `pl_tsumagizaka_dojo` | (0, 49.9, 7.5) | 16 × 12 × 3 | b04 marobashi ring; flood line |
| `vol_ch01_engawa_sunbeam` | `pl_tsumagizaka_dojo` | (4.6, 56.5, 7.6) | 2 × 1.2 × 2 | b05 Baiō asleep; optional bow prompt |
| `vol_ch01_engawa_east` | `pl_tsumagizaka_dojo` | (7.5, 56, 7) | 4 × 5 × 2.5 | b05 Toranosuke exchange |
| `vol_ch01_engawa_mentor` | `pl_tsumagizaka_dojo` | (-3, 56.5, 7.6) | 4 × 2.4 × 2 | b05 objective from Sekireisai |
| `vol_ch01_umaya` | `pl_umaya` | (25, 58, 7.5) | 14 × 9 × 3 | completes b05; starts b06 |
| `vol_ch01_lane_trot` | `pl_umaya` | on `spl_ch01_umaba_lane` | 70–240 m along, 6 wide | b06 trot prompt zone |
| `vol_ch01_lane_pheasant` | `pl_umaya` | on `spl_ch01_umaba_lane` | 146–154 m along, 6 wide | b06 scripted spook |
| `vol_ch01_matoba_hitch` | `pl_matoba` | (-163, 22, 9) | 6 × 6 × 3 | b06 complete (dismount at the hitching post) |
| `vol_ch01_matoba` | `pl_matoba` | (-176, 50, 10) | 24 × 70 × 8 | b07 bounds; arrow corridor |
| `vol_ch01_shajo_line` | `pl_matoba` | (-178, 19.5, 9) | 12 × 1.5 × 3 | b07 shooting line (bow draws only here) |
| `vol_ch01_wood` | `pl_issoseki_wood` | (-95, 67.5, 12) | 110 × 85 × 20 | b08 bounds |
| `vol_ch01_wood_exit` | `pl_issoseki_wood` | (-36, 54.5, 7.5) | 4 × 4 × 3 | b08 complete; smithy back gate |
| `vol_ch01_smithy` | `pl_dojo_smithy` | (-28, 52, 7.5) | 9 × 8 × 3 | b09 start (also reachable by the terrace path) |
| `vol_ch01_ura_mon` | `pl_estate_day` | (4.5, 27.5, 1.5) | 3 × 2 × 3 | fade into Arena 0; outside the north wall, no collision change |
| `vol_ch01_estate_north_gate` | `pl_estate_day` | (4.8, 22.5, 1.5) | 3 × 3 × 3 | b10 household chatter |
| `vol_ch01_estate_engawa` | `pl_estate_day` | (0, 12.5, 1.5) | r 4 | b10 and b12 veranda talk; katana hand-over |
| `vol_ch01_duel_ring` | `pl_estate_day` | (0, 0, 1.5) | r 5, h 3 | b11 ring; leaving it resets the exchange |

---

## 4. Beats

### 4.1 Beat list

| Beat | Type | Place | Min | Checkpoint | Site | Unlocks | Fail |
|---|---|---|---:|---|---|---|---|
| ch01.b01 | cinematic | `pl_tsumagizaka_dojo` | 2 | yes | — | — | none |
| ch01.b02 | duel | `pl_tsumagizaka_dojo` | 4 | yes | 0 | `kamae`, `maai_ring` | none |
| ch01.b03 | duel | `pl_tsumagizaka_dojo` | 4 | yes | 1 | `awase` | none |
| ch01.b04 | duel | `pl_tsumagizaka_dojo` | 3 | yes | — | `marobashi` | none |
| ch01.b05 | dialogue | `pl_tsumagizaka_dojo` | 1.5 | no | — | — | none |
| ch01.b06 | horseback_ride | `pl_umaya` | 3 | yes | — | `mount` | none |
| ch01.b07 | combat_wave | `pl_matoba` | 5 | yes | — | weapon 18; `yumi` | none |
| ch01.b08 | explore_optional (optional) | `pl_issoseki_wood` | 4 | yes | — | — | none |
| ch01.b09 | production_task (manufacture) | `pl_dojo_smithy` | 3 | yes | 2 | `manufacture` | none |
| ch01.b10 | dialogue | `pl_estate_day` | 1.5 | no | — | — | none |
| ch01.b11 | duel | `pl_estate_day` | 6 | yes | — | — | match lost → retry; 3rd loss → loss branch |
| ch01.b12 | dialogue | `pl_estate_day` | 1 | yes | — | weapon 0 | none |
| ch01.b13 | cinematic | `pl_estate_day` | 2 | no | — | — | none |
| **Σ** | | | **40** | | | | |

Checkpoints are saved at beat start. The dojo lesson mask stays valid under the existing `SoraDojoRules::CheckpointValid`:

| Checkpoint | Lesson mask | Scored bouts | Sites |
|---|---|---|---|
| b02 start | 0 | 0 | 0 |
| b03 start | bit 0 | 0 | site 0 |
| b04 start | bits 0–3 | 2 | sites 0, 1 |
| b06 start onward | bits 0–3 | 4 | sites 0, 1 (site 2 from b09 on) |

### 4.2 Beat details

The `x_` fields named below are chapter proposals outside the bible's §12 contract. They are listed in §4.6.

#### ch01.b01: cinematic, 夜明けの素振り (Dawn practice), 120 s

- **Sequence** `LS_Ch01_B01_DawnSuburi` (C9), skippable. Fallback: `camera_blend`.
- **Shots:**
  - 0–12 s: black; birdsong and the rhythm of wooden swords.
  - 12–30 s: the valley mist; the dojo roof, where the SORA end tiles catch the first light.
  - 30–55 s: the interior. Pupils in two rows swing to counted 掛け声 (kakegoe: shouted counts, not captioned); dust in the raking light.
  - 55–60 s: dolly along the 名札掛け. Sekireisai's plaque heads the board; Toranosuke's is in the senior row with an **empty place** below it (he is late); Nyaakoto's (in katakana, see §6.1) is in the junior row.
  - 60–75 s: lines 1–4.
  - 75–96 s: a seated bow (座礼); Sekireisai takes up a bokutō.
  - 96–110 s: the title card 「第一章 道場の修行」 in brush calligraphy with the vermillion SORA 朱印 seal.
  - 110–120 s: blend to gameplay at `ps_ch01_lesson_mark` with the bokutō in hand.

#### ch01.b02: duel (lesson) vs Sekireisai, 正眼に構え、間合いを読め (Take seigan and read the distance), 240 s, site 0

- **Opponent and ring.** `npc_sekireisai`, bokutō against bokutō, `lethal: false`, in `vol_ch01_dojo_floor`. Sekireisai does not attack in this beat.
- **Gate 1, `stance_hold {ms: 600}`.** Hold Guard in seigan for 600 ms. This is the existing `EAction::Stance`, lesson bit 0.
- **Gate 2, `maai_step {count: 3}`.** The 水月 ring appears when the player is at ideal distance: the bokutō's range of 195 cm ±15%, so 166–224 cm, while facing the opponent (dot ≥ 0.70). Hold 500 ms to confirm. Sekireisai then moves three times: back 120 cm, left 150 cm, forward 80 cm. The player re-establishes distance each time. Coming closer than 166 cm plays the "too close" hint. Being too far shows no ring and has no voice line. After 6 s without progress a floor marker shows the band.
- **Complete.** Site 0 is restored and the catalog's restored text is shown. Unlocks `kamae` and `maai_ring`.
- **Accessibility.** The ring shows on every difficulty; Easy adds a distance meter.

#### ch01.b03: duel (lesson) vs Matsukichi, then Takemaru, 受けて、合わせよ (Receive the cut, then meet it), 240 s, site 1

- **Opponent pattern `pupil_men`.** The existing pupil strike: a 550 ms amber windup, repeated every 1.45 s. Windups scale +30% on Easy and −15% on Hard, as in bible §8.
- **Gate 1, `front_guard_survive {after_ms: 350}`.** Face him, raise the guard at least 350 ms before impact, stamina ≥ 18. Lesson bit 1.
- **Gate 2, `awase {window_ms: 260, count: 2}`.** Press Guard within 260 ms before impact; he staggers for 1.2 s. The first success sets lesson bit 2 (`EAction::Parry`). Early and late presses get separate hints.
- **Gate 3, `recovery_complete`.** Cut once, release, and wait out the katana's 0.75 s recovery. Lesson bit 3. From here the passive 残心 (zanshin) is active: holding guard for 0.5 s after a scored point restores 15 stamina (bible §3.2).
- **Two scored bouts (`x_scored_bouts`).** Meet the cut, then land a cut in the stagger after your own recovery. Matsukichi yields and Sekireisai rotates in Takemaru for the second. Each bout counts as one catalog "kill" (the existing `OpponentDefeated`). Two bouts satisfy site 1's `requires_kills: 2`, and the catalog's restored text ("sparred with two pupils") becomes true.
- **Unlocks.** `awase`.

#### ch01.b04: duel (lesson), 転（まろばし）(Marobashi: roll with the flood), 180 s

- **Setting.** The yard, `vol_ch01_dojo_yard`. The pupils now cut 袈裟 (a diagonal cut): pattern `pupil_kesa`, 600 ms windup, 1,000 ms recovery, with a diagonal amber edge.
- **Gate `marobashi_flank {count: 2}`.** After a successful awase, press Left or Right plus Step within 400 ms. The player rolls 120 cm laterally on a 70° arc around the opponent, who needs 0.8 s to turn, and a cut to the exposed side scores. If the player meets the cut but does not step, Sekireisai's "do not stop" hint plays.
- **Opponents.** Matsukichi, then Takemaru. Scored bouts 3 and 4 bring the chapter's catalog kill count to 4.
- **Unlocks.** `marobashi`.

#### ch01.b05: dialogue (ambient), 縁側の陽だまり (The sunbeam on the veranda), 90 s, no checkpoint

- **Walk-and-talk.** The player keeps control and the camera uses soft look-at.
- **Toranosuke arrives.** He rides Arashi in from the lane gate, dismounts and hands the reins to Takemaru, who leads the stallion to the stable. This puts Arashi in the stable for b06.
- **Humor beat 1 (bible §1.2).** Baiō is asleep in the only sunbeam, at the east end of the south veranda. The pupils bow around him without comment, and so does Toranosuke. The player can also bow (optional prompt). Nobody remarks on it.
- **Dialogue.** The pupils' whisper about Osaka carries the debt hint. The exchange with Toranosuke plays in `vol_ch01_engawa_east`, and Sekireisai gives the objective in `vol_ch01_engawa_mentor`.
- **Collectible.** `ch01.c03` (oath roll) is reachable on the kamiza.
- **Complete.** Entering `vol_ch01_umaya`.

#### ch01.b06: horseback_ride (travel), 栗丸に鞍を置き、的場へ (Tack up Kurimaru and ride to the range), 180 s

- **Tack-up (`x_tack_up`, fixed order).** Takemaru calls out each piece:
  1. **Kura:** the saddle, set over the under-pad (下鞍).
  2. **Haruobi:** the girth, tightened twice because the mare puffs out her belly.
  3. **Abumi:** the stirrups, hung on the 力革 leathers.
  4. **Kutsuwa and omogai:** the bit and headstall.
- **Humor beat 2 (bible §1.2).** Kurimaru turns her head away from the bit twice, ears back but never aggressive, until the player offers the ear of barley from his sleeve. Takemaru: 「……毎朝、これです。」
- **Mounting.** From the horse's **right** side, per period practice (§6.3), at the tie rail.
- **Ride.** Horse `kurimaru`, route `spl_ch01_umaba_lane`, gaits walk (160 cm/s) and trot (360 cm/s). No canter or gallop, so horse stamina is not used. `weapons: []`: nothing is unlocked yet and the bokutō stays on its rack.
- **Scripted spook.** At 150 m a pheasant flushes. Kurimaru sidesteps and stops for 1.5 s, and input is ignored for 0.8 s. This teaches `fear {spook_radius_cm: 600, recover_s: 1.5}` before ch02's beams.
- **Complete.** Reach `vol_ch01_matoba_hitch` and dismount. Unlocks `mount`.
- **Fail.** None. `on_horse_down: checkpoint` is unreachable in ch01.

#### ch01.b07: combat_wave (`target_kind: mato`), 的場で弓を引け (Draw the bow at the range), 300 s

- **Unlock.** Weapon 18 (yumi) and mechanic `yumi` at beat start, when Baiō hands over the bow.
- **Shooting sequence (`x_shaho`).**
  - On first equip, 弓構え (ready the bow) and 打起し (raise it) play in full.
  - Hold Attack to draw (引分け, 650 ms) to 会 (full draw), then release (離れ). Aim sway begins after 4 s at full draw.
  - The arrow rests on the right of the bow. The bow turns in the hand after release (弓返り).
  - 残心 (follow-through) is a cosmetic hold.
  - The bow cannot be drawn while sprinting.
- **Wave 1: the near target (近的).** One 尺二 target at 28 m. Shoot sets of 6 arrows; 4 hits in a set are needed. The hit collider radius is 25 cm on Easy, 21 cm on Normal and 18 cm on Hard. After a failed set, Matsukichi fetches the arrows (矢取り, 8 s) and a new set starts. Tuning assumption: an average Normal player hits 60–70% of shots at this distance.
- **Wave 2: three 吊り的 (hanging straw targets).** At 40, 50 and 60 m, swinging ±150 cm on a 3.2 s period. One hit each. The arrow drop and flight time are visible, so the player must lead the swing.
- **Arrows.** Arrow speed (6,500 cm/s) and gravity are L2's; arrows fly visibly. The player uses his own 12-arrow quiver, and arrows are fetched between sets.
- **Allies.** Baiō (instructor) and Matsukichi (看的, target keeper). Neither can be downed.
- **Complete.** All waves cleared. The quiver is then **6 usable and 6 bent**, which motivates b09.
- **Collectible.** `ch01.c06` is on the shajō wall.

#### ch01.b08: explore_optional, 一爪石の森 (One-Claw Stone Wood), 240 s, optional

- **Route.** The trail crosses the wood in about 60 s. The points of interest take the beat to its 4 minute target.
- **Rewards.** Collectibles `ch01.c01` (scroll fragment plaque) and `ch01.c02` (boundary stone).
- **Challenge.** From the vista ledge, hit the 鳴子 clapper 45 m across the ravine with one arrow. The reward is a codex entry on 通し矢, the long-distance archery fashion of the early 1600s. It grants no stats.
- **Exit hint.** At 180 s: hammer sound plus a line.
- **Gating.** Complete on `vol_ch01_wood_exit`. b09 requires b07, not b08, so skipping the wood (taking the terrace path) is allowed.

#### ch01.b09: production_task (manufacture), 矢を矯め、羽を付け直せ (Straighten and refletch the arrows), 180 s, site 2

- **Recipe `ya_repair`.** Steps, in order:
  1. **Rekindle the hearth.** Hold interact at the box bellows.
  2. **Heat ×6.** Hold each shaft over the brazier and lift it when it gleams: a 2.0 s ±0.5 s window. Scorching resets that shaft with no penalty.
  3. **Bend ×6.** Press the shaft in the 矯め木 and release when the sight line runs true: a 700 ms beat, ±150 ms on Normal, ±200 on Easy and ±120 on Hard.
  4. **Paste.** Glue on new feathers with 膠 (three feathers, all facing the same way).
  5. **Assemble.** Bind with thread.
  6. **Inspect.** Count all 12.
- **No grind.** A failed step repeats in place; there is no quality grade.
- **Output.** 12 arrows. The quiver refills to 12. Registry **矢 12本** is written in the smithy's 帳面, shown through the L4 registry screen. Site 2 is restored: the catalog's "you rekindled the forge". Unlocks `manufacture`.
- **Foreshadowing.** Tetsugorō's closing line about rain killing the match sets up ch04's coil-breech matchlock.

#### ch01.b10: dialogue (ambient), 殺人刀と活人剣 (The sword that kills, the sword that gives life), 90 s, no checkpoint

- **Entry.** Takemaru's summons ends b09. The player walks down the 爪木坂 steps and fades in through `vol_ch01_ura_mon`. Household chatter plays at `vol_ch01_estate_north_gate`.
- **The teaching.** At `vol_ch01_estate_engawa`, Sekireisai teaches the paired terms (paraphrasing 『兵法家伝書』, §6.1).
- **The challenge.** Toranosuke challenges Nyaakoto. Two lines carry the debt hint: "Tomorrow, a man comes from Osaka" and "Proof that the Washio name is not yet broken."

#### ch01.b11: duel, 袋竹刀で虎之介と立ち合う (Fukuro-shinai bout with Toranosuke), 360 s

- **Setup.** Opponent `npc_toranosuke`. Both fighters use `fukuro_shinai`, a non-lethal presentation variant of weapon 0. `scoring {mode: points, first_to: 3}`, `ring: vol_ch01_duel_ring`, `finisher: none`, `loss_policy: continue_after:3`.
- **Point rules (`x_point_rules`).** A clean hit to 面 (head), 小手 (wrist) or 胴 (torso) scores when it lands unguarded and outside the striker's own recovery.
  - Hits by both fighters within 150 ms of each other are a 相打ち (mutual strike): no point, and the judge calls it.
  - After each point, both return to the start marks and bow; the reset takes 3 s.
  - Leaving the ring resets the exchange with no point.
- **Toranosuke's attacks (`tora_fukuro`, L2).**

| Attack | JA | Windup (ms, Normal) | Recovery (ms) | Telegraph | Guard | Awase | 転 after awase | Notes |
|---|---|---:|---:|---|---|---|---|---|
| `tora_men` | 面打ち | 500 | 900 | amber_solid | yes | yes | no | — |
| `tora_kote` | 小手打ち | 380 | 700 | amber_solid | yes | yes | no | — |
| `tora_kesa` | 袈裟 | 600 | 1000 | amber_diagonal | yes | yes | yes | — |
| `tora_feint` | 誘い（面から小手） | 630 | 700 | amber_hollow_then_solid | yes | on the real kote only | no | fake phase 250 ms; tell: rear foot does not drive during the fake |
| `tora_nidan` | 二段（小手から面） | 380 | 1100 | amber_solid_x2 | yes | either cut | yes | second gap 450 ms |
| `tora_seme` | 攻め（押し込み） | 0 | 0 | none | — | — | — | duration 1200 ms; steps in 120 cm to crowd the player toward the ring edge |

- **Score states (`x_score_states`).** Toranosuke's haste is his character, and it is also the player's opening:

| State | Attack interval | Weights |
|---|---|---|
| Even, or Toranosuke leads | 1.6–2.4 s | men 35 · kote 25 · kesa 25 · feint 15 |
| Player leads by 1 | 1.3–2.0 s | men 25 · kote 20 · kesa 10 · feint 25 · nidan 20 |
| Player leads by 2 ("急げ") | 1.0–1.6 s, recovery +150 ms (he over-commits) | men 20 · feint 30 · nidan 35 · seme 15 |

- **Difficulty.** Windups ×1.30 on Easy and ×0.85 on Hard. On Easy the feint weight is halved.
- **Feint tell.** During the fake phase the telegraph ring is hollow and his rear foot does not push. Sekireisai names the foot tell after the first feint lands.
- **Loss policy.** Losing a match (Toranosuke reaches 3) offers a retry with a coaching line. After the **third** lost match the loss branch plays and the chapter continues. The save stores `ch01_duel_result` (`win` or `loss`) for b12 and for later callbacks. Toranosuke's defeat or victory never blocks progress.
- **Not a boss.** Toranosuke is not in `bosses.json`. The table above is an L2 duel-opponent pattern.

#### ch01.b12: dialogue (blocking), 刀を預かる (The blade held in trust), 60 s

- **Loss branch.** If the player lost b11, Sekireisai's two loss-branch lines play first as ambient lines while the player approaches.
- **Hand-over.** Interact at `ip_ch01_katana` (0, 14, 0.6). The blocking hand-over is four lines, 16.9 s including gaps, within the 20 s cap: the bible's katsujinken line and catalog anchor lines 2 and 3.
- **Unlocks.** Weapon 0 (katana). The draw and sheathe prompt introduces 納刀 (sheathing), which ch06's mutō-dori will need.
- **Complete.** When the player sheathes, or 20 s after the blocking ends.

#### ch01.b13: cinematic, 空が裂ける (The sky splits), 120 s, no checkpoint

- **Sequence** `LS_Ch01_B13_SkySplits` (C9).
- **Shots:**
  - 0–14 s: the golden courtyard. Household members light 行灯 lanterns. Toranosuke mounts Arashi at the east gate.
  - 14–30 s: crows lift from the cedars. Kurimaru lifts her head in the stable. A seam of cold light opens across the western sky.
  - 31–46 s: lines. The seam widens like torn washi, and lights descend in formation toward Nekoyama.
  - 46–58 s: Toranosuke, from the gate.
  - 58–86 s: Sekireisai orders the bell. Baiō crosses briskly to the 半鐘 and strikes it in rapid continuous strokes.
  - 88–95 s: Sekireisai to Nyaakoto. Nyaakoto's hand settles on the tsuka.
  - 95–112 s: wide shot. Cold cyan over a warm valley, the estate's lanterns tiny below.
  - 112–120 s: cut to black on a bell stroke, then the chapter-complete registry page (矢 12本) with the three restored sites.
- **End state.** Katana sheathed; the chapter continues at `ch02.b01`.

### 4.3 Not used in chapter 1

These appear in the brief's list of parameters but have no content in ch01:

- **Stealth:** no patrol routes or detection rules. S = 0 min in bible §10; stealth starts in ch03.
- **Escort and carry:** none. The only "cargo" is the rider.
- **Enemy compositions:** there are no hostile archetypes. The opponents are training NPCs (`pupil`, `mato`, and the rival). Alert, search and retreat barks start in ch02. Their ch01 counterparts are the judge's calls, the target keeper's calls and Toranosuke's taunts.
- **Bosses:** none. The Toranosuke duel uses the pattern table above instead of HP phases; its "phases" are the score states.

### 4.4 Collectibles

There are 6 of the chapter's 6. They are passive `collectible` beats and are not in the beat count. Mask bits are chapter-local 0–5 and `collectible_id` equals the `chNN.cMM` id (bible §12.5); the global bit is (chapter − 1) × 6 + `mask_bit`, which is also 0–5 here. Categories: 1 scroll fragment, 2 League marks, 2 heirlooms, 1 registry page. Seizure notices begin in ch02. The heirlooms are recorded here and seized in ch02; the bible's epilogue returns them to their homes.

| Id | Category | Title | Where | Available in | Mask bit | Codex (EN) |
|---|---|---|---|---|---:|---|
| `ch01.c01` | scroll_fragment | 伝書の断簡 其の一 / Scroll fragment I | wooden plaque tied to the shimenawa post at the One-Claw Stone | ch01.b08 | 0 | Distance is not the length of the sword. It is how far the mind reaches. —Sekireisai |
| `ch01.c02` | league_mark | 空紋の目印 其の一 / League mark I | boundary stone carved with the house mon, south-east of the wood | ch01.b08 | 1 | A Nyaagyu boundary stone carved with the sky mon. No one remembers who carved it, or when. |
| `ch01.c03` | heirloom | 家宝 門弟起請文の巻 / Heirloom: the pupils' oath roll | lacquered box on the kamiza, dojo interior | ch01.b04, ch01.b05 | 2 | A roll of the pupils' entry oaths. One is signed with Nyaakoto's formal name, 猫琴, beside a monogram and a small blood seal. |
| `ch01.c04` | heirloom | 家宝 初代の鐔 / Heirloom: the founder's tsuba | hanging on a peg above the anvil, waiting for its yearly cleaning | ch01.b09 | 3 | The first Nyaagyu lord's iron tsuba, pierced in the shape of the sky mon. Once a year the forge cleans off its rust. |
| `ch01.c05` | registry_page | 生産の記録 先代の控え帳 / Registry page: the old smith's day-book | loft shelf above the tool rack | ch01.b09 | 4 | An old smith's day-book. Forty hoes, a hundred and twenty sickles, twelve spades. Only what was made is written here. |
| `ch01.c06` | league_mark | 空紋の目印 其の二 / League mark II | charcoal drawing on the inside wall of the shajo | ch01.b07, ch01.b08 | 5 | The sky mon drawn in charcoal on the range wall, with rows of strokes counting hits beside it. |

Each codex entry also has a Japanese text, in the YAML.

### 4.5 Catalog and existing-rules mapping

| Catalog (schema 3, chapter 0) | This chapter |
|---|---|
| `kills: 4` | Four scored pupil bouts: two in b03, two in b04. Toranosuke's bout does not count |
| Site 0 間合いの稽古場, `requires_kills 0` | b02 complete |
| Site 1 木刀の試合場, `requires_kills 2`, `requires_sites [0]` | b03 complete, after the two scored bouts |
| Site 2 道場の鍛冶場, `requires_kills 4`, `requires_sites [1]` | b09 complete |
| Dialogue lines 1–3 | Line 1 → `ch01.b02.sekireisai.001`; lines 2 and 3 → `ch01.b12.nyaakoto.005`, `ch01.b12.sekireisai.006` (text unchanged, 4.8 s kept) |
| `SoraDojoRules` Stance / Guard / Parry / Recovery | b02 gate 1 / b03 gates 1, 2 (first success), 3 |
| Existing HUD lesson strings (壱 構え … 肆 残心) | Superseded by the prompts in §5, which L4 owns. 捌き in the HUD becomes 合わせ, per bible §3.2 |

### 4.6 Proposed extensions to the §12 contract

**Trigger events.** These are needed by the script and are not in bible §12.1. L1 can adopt, rename or fold them into `progress_at`:

| Group | Events |
|---|---|
| Lesson gates | `gate_start:<gate>`, `gate_complete:<gate>`, `gate_retry:<gate>`, `maai_step_ok`, `awase_success:<n>`, `awase_fail:early`, `awase_fail:late`, `marobashi_miss` |
| Bouts | `bout_start:<n>`, `bout_scored:<n>` (running pupil total, which is the catalog kill count) |
| Interaction | `interact:<id>`, `interact_refused:<id>:<n>`, `item_given:<item>`, `mount`, `horse_spooked` |
| Archery | `equip:<weapon id>`, `draw_complete:first`, `release:first`, `mato_hit`, `mato_miss`, `set_failed`, `wave_start:<n>` |
| Manufacture | `step_start:<kind>`, `step_complete:<kind>:<n>`, `step_failed:<kind>`, `output_complete` |
| Duel | `point:player`, `point:rival`, `point:rival:first`, `feint_landed:first`, `score:player_leads_2`, `ring_out`, `match_lost`, `duel_won`, `loss_continue` |
| Flow | `branch:<flag>`, `blocking_end`, `seq` (cinematic subtitle time `t_s`) |

**Beat fields.** `x_prompts`, `x_maai`, `x_dojo_rules`, `x_scored_bouts`, `x_opponent_rotation`, `x_opponent_pattern`, `x_marobashi`, `x_tack_up`, `x_gait_zones`, `x_speeds_cm_s`, `x_scripted_spook`, `x_mato_rules`, `x_tsuri`, `x_shaho`, `x_quiver_after`, `x_main_trail`, `x_challenge`, `x_complete`, `x_point_rules`, `x_pattern_table`, `x_score_states`, `x_branches`, `x_blocking_lines`, `x_blocking_max_s`, `x_title_card`, `x_chapter_complete`, `x_entry`, `x_unlock_at`, `x_failure`, `x_tolerance_by_difficulty_ms`, `x_ambient_actions`, `x_next`.

**Other conventions.**

- `fail: {on: none, to: none}` marks beats with no fail state. The whole chapter is non-lethal.
- Lesson gates are written `{gate: <name>, <param>: <value>}`.

---

## 5. Script

### 5.1 Conventions

- **Line ids** follow `ch01.bMM.<character>.<nnn>`, numbered in order within each beat (bible §18). Tutorial prompts are `ch01.bMM.prompt.NN`. They are L4 `ui_strings` with input-glyph placeholders like ［防御］/[Guard], not voice lines.
- **Speakers** are bible ids: `mentor`, `samurai`, `rival`, `gunsmith`. New minor ids are proposed for L1's `dialogue_speakers`: `pupil_matsukichi`, `pupil_takemaru`, `pupil_baio`, `household`. The catalog's `mentor` display name 師範 / Master should become 石鈴斎 / Sekireisai.
- **Registers:**
  - `archaic_samurai` (Sekireisai): わし, おぬし, 〜じゃ, 〜ぬ.
  - `jidaigeki_restrained` (Nyaakoto): polite to superiors, plain だ with peers, few words.
  - `brash_samurai` (Toranosuke): 俺 with Nyaakoto; `formal_samurai` when he addresses Sekireisai.
  - `young_samurai` (Matsukichi, Takemaru).
  - `elder_samurai` (Baiō): slow, 〜なされ.
  - `blunt_artisan` (Tetsugorō).
  - `yamato_commoner` (household): 〜や, 〜とる.
- **English subtitles.** Samurai speakers use no contractions, per bible §18. The artisan and household may use them.
- **Limits.** Every line was checked by script against bible §18 and §12.3:
  - JA ≤ 32 characters (2 × 16).
  - EN ≤ 84 characters, wrapping into at most 2 lines of 42.
  - EN reading speed ≤ 17 cps.
  - Duration ≥ 1.0 s.
- **Durations.** The larger of the Japanese delivery estimate (about 4.8 characters/s plus 0.45 s per ……) and the English reading time at 15 cps. The three catalog anchor lines keep their 4.8 s.
- **Reading notes.** Each note gives the reading (furigana) of a rare or period word so that captions can carry ruby text and the actors can prepare.
- **Uncaptioned sounds.** 掛け声 (kakegoe, shouted counts) and kiai are SFX and VO "efforts", not captions.
- **Humor.** Two approved moments, Baiō's sunbeam and the barley, both from bible §1.2. Neither falls in the duel, the hand-over or the final cinematic.

### 5.2 Line counts

| Speaker | Lines |
|---|---:|
| `mentor` (石鈴斎 / Sekireisai) | 52 |
| `samurai` (ニャーコト / Nyaakoto) | 14 |
| `rival` (虎之介 / Toranosuke) | 14 |
| `pupil_takemaru` (竹丸 / Takemaru) | 12 |
| `gunsmith` (鉄五郎 / Tetsugorō) | 9 |
| `pupil_baio` (梅翁 / Baiō) | 8 |
| `pupil_matsukichi` (松吉 / Matsukichi) | 6 |
| `household` (屋敷の者 / Household) | 2 |
| **Voiced total** | **117** |
| Tutorial prompts (UI text) | 22 |
| **All rows** | **139** |

117 voiced lines (13 repeatable barks or hints, 10 branch-only), 22 tutorial prompts, 139 rows in total. Voiced audio totals about 6.3 minutes. A single playthrough hears about 100 of the voiced lines, because the rest are repeatable hints or belong to the branch not taken.

### 5.3 Dialogue by beat

#### ch01.b01 · Dawn practice (夜明けの素振り)

| # | Line id | Trigger | Speaker | Japanese | Reading notes | English subtitle | s |
|---:|---|---|---|---|---|---|---:|
| 1 | `ch01.b01.sekireisai.001` | `seq t=60.0 s` | 石鈴斎 / Sekireisai | 止め。 | — | Stop. | 1.0 |
| 2 | `ch01.b01.sekireisai.002` | `seq t=61.6 s` | 石鈴斎 / Sekireisai | 百本振って、おぬしの剣は何本あった。 | — | A hundred swings. How many were truly yours? | 3.7 |
| 3 | `ch01.b01.nyaakoto.003` | `seq t=65.9 s` | ニャーコト / Nyaakoto | ……六十本ほどかと。 | — | …Sixty, perhaps. | 2.3 |
| 4 | `ch01.b01.sekireisai.004` | `seq t=68.8 s` | 石鈴斎 / Sekireisai | 正直でよい。残りの四十は、稽古で取り戻せ。 | — | Honest. Win back the other forty in practice. | 4.1 |

#### ch01.b02 · Take seigan and read the distance (正眼に構え、間合いを読め)

| # | Line id | Trigger | Speaker | Japanese | Reading notes | English subtitle | s |
|---:|---|---|---|---|---|---|---:|
| 5 | `ch01.b02.sekireisai.001` | `beat_start` (anchor: catalog ch01 line 1) | 石鈴斎 / Sekireisai | 刃を急がせるな。相手の足音を聞け。 | — | Do not hurry your blade. Listen to your opponent's footing. | 4.8 |
| 6 | `ch01.b02.sekireisai.002` | `beat_start` | 石鈴斎 / Sekireisai | 正眼に構えよ。切っ先は、わしの喉へ。 | 正眼（せいがん）・切っ先（きっさき） | Take seigan. Point your tip at my throat. | 3.5 |
| 7 | `ch01.b02.sekireisai.003` | `gate_complete:stance_hold` | 石鈴斎 / Sekireisai | 水に映る月を思え。 | 水月（すいげつ）の教え | Think of the moon upon the water. | 2.2 |
| 8 | `ch01.b02.sekireisai.004` | `gate_complete:stance_hold` | 石鈴斎 / Sekireisai | わしの太刀は届かず、おぬしの太刀は届く。そこに立て。 | 太刀（たち） | Stand where my sword cannot reach, and yours can. | 5.1 |
| 9 | `ch01.b02.nyaakoto.005` | `gate_complete:stance_hold` | ニャーコト / Nyaakoto | 木刀の長さは、同じでございますが。 | 木刀（ぼくとう） | But our swords are the same length, Sensei. | 3.5 |
| 10 | `ch01.b02.sekireisai.006` | `gate_complete:stance_hold` | 石鈴斎 / Sekireisai | 長さは同じ。心の長さが違う。 | — | The length is the same. The reach of the mind is not. | 3.6 |
| 11 | `ch01.b02.sekireisai.007` | `maai_step_ok` (repeatable; steps 1 and 2) | 石鈴斎 / Sekireisai | うむ。 | — | Good. | 1.0 |
| 12 | `ch01.b02.sekireisai.008` | `gate_complete:maai_step` | 石鈴斎 / Sekireisai | ……三つ。よし。 | — | …Three. Good. | 1.6 |
| 13 | `ch01.b02.sekireisai.009` | `gate_retry:maai_step` (repeatable; cooldown 20 s) | 石鈴斎 / Sekireisai | 近い。それでは互いに斬られる。 | — | Too close. There, we would both be cut. | 3.1 |
| 14 | `ch01.b02.sekireisai.010` | `beat_complete` | 石鈴斎 / Sekireisai | 間合いは、剣の半分じゃ。 | 間合い（まあい） | Distance is half the art of the sword. | 2.6 |

Tutorial prompts (L4 `ui_strings`, not voiced):

| Prompt id | Trigger | Japanese | English |
|---|---|---|---|
| `ch01.b02.prompt.01` | `beat_start` | {Block}長押しで正眼に構える（0.6秒） | Hold {Block} to take seigan (0.6 s). |
| `ch01.b02.prompt.02` | `gate_start:maai_step` | 水月の輪が浮かぶ間合いで止まり、師に向く | Stop where the moon ring appears, facing Sensei. |

#### ch01.b03 · Receive the cut, then meet it (受けて、合わせよ)

| # | Line id | Trigger | Speaker | Japanese | Reading notes | English subtitle | s |
|---:|---|---|---|---|---|---|---:|
| 15 | `ch01.b03.sekireisai.001` | `beat_start` | 石鈴斎 / Sekireisai | 松吉、打ち込め。ニャーコトは受けよ。 | — | Matsukichi, attack. Nyaakoto, receive. | 3.5 |
| 16 | `ch01.b03.sekireisai.002` | `gate_complete:front_guard_survive` | 石鈴斎 / Sekireisai | 受けは壁ではない。柳じゃ。 | 受け（うけ） | A guard is no wall. It is a willow. | 2.6 |
| 17 | `ch01.b03.sekireisai.003` | `gate_start:awase` | 石鈴斎 / Sekireisai | 次は合わせ。打たれる刹那に、こちらから迎えに行け。 | 合わせ（あわせ）・刹那（せつな） | Now, awase. The instant he cuts, go out to meet it. | 4.9 |
| 18 | `ch01.b03.sekireisai.004` | `awase_success:1` | 石鈴斎 / Sekireisai | そうじゃ。太刀と太刀が、言葉を交わしたろう。 | — | Yes. Did you hear the swords speak? | 3.9 |
| 19 | `ch01.b03.sekireisai.005` | `awase_fail:early` (repeatable; cooldown 15 s) | 石鈴斎 / Sekireisai | 早い。相手の太刀を待て。 | — | Too early. Wait for his sword. | 2.4 |
| 20 | `ch01.b03.sekireisai.006` | `awase_fail:late` (repeatable; cooldown 15 s) | 石鈴斎 / Sekireisai | 遅い。見てから動いては、間に合わぬ。 | — | Too late. Move after you see it, and you are late. | 3.5 |
| 21 | `ch01.b03.sekireisai.007` | `gate_start:recovery_complete` | 石鈴斎 / Sekireisai | 打ったら、刃の戻りを待て。二の太刀を急ぐな。 | 二の太刀（にのたち） | After a cut, wait for the blade to return. Do not rush the next. | 4.3 |
| 22 | `ch01.b03.sekireisai.008` | `gate_complete:recovery_complete` | 石鈴斎 / Sekireisai | それが残心の始まりじゃ。 | 残心（ざんしん） | That is where zanshin begins. | 2.6 |
| 23 | `ch01.b03.matsukichi.009` | `bout_scored:1` | 松吉 / Matsukichi | ……一本。参りました。 | 一本（いっぽん） | …A clean point. I yield. | 2.3 |
| 24 | `ch01.b03.sekireisai.010` | `bout_scored:1` | 石鈴斎 / Sekireisai | 竹丸、代われ。 | — | Takemaru, take his place. | 1.7 |
| 25 | `ch01.b03.sekireisai.011` | `beat_complete` | 石鈴斎 / Sekireisai | 二人とも、よう打った。よう打たれた。 | — | Both of you struck well. And were struck well. | 3.5 |

Tutorial prompts (L4 `ui_strings`, not voiced):

| Prompt id | Trigger | Japanese | English |
|---|---|---|---|
| `ch01.b03.prompt.01` | `beat_start` | 相手に向き、{Block}を保って一撃を受ける | Face him and hold {Block} through the strike. |
| `ch01.b03.prompt.02` | `gate_start:awase` | 金色の予兆に合わせて{Block}を押す | Press {Block} as the gold warning flashes. |
| `ch01.b03.prompt.03` | `gate_start:recovery_complete` | 一度振り、{Fire}を離して刃の戻りを待つ | Swing once, release {Fire}, and wait for the blade to return. |
| `ch01.b03.prompt.04` | `bout_start:1` | 合わせて崩し、その隙に打って一本を取る | Meet his cut, then strike the opening to score. |

#### ch01.b04 · Marobashi: roll with the flood (転（まろばし）)

| # | Line id | Trigger | Speaker | Japanese | Reading notes | English subtitle | s |
|---:|---|---|---|---|---|---|---:|
| 26 | `ch01.b04.sekireisai.001` | `beat_start` | 石鈴斎 / Sekireisai | 外へ出よ。転を教える。 | 転（まろばし） | Outside. I will teach you marobashi. | 2.4 |
| 27 | `ch01.b04.sekireisai.002` | `volume_enter:vol_ch01_dojo_yard` | 石鈴斎 / Sekireisai | 濁流に逆らうな。流れと共に、転がれ。 | 濁流（だくりゅう） | Do not stand against the flood. Roll with it. | 3.5 |
| 28 | `ch01.b04.sekireisai.003` | `marobashi_miss` (repeatable; cooldown 15 s) | 石鈴斎 / Sekireisai | 止まるな。合わせたら、もう転がっておれ。 | — | Do not stop. Once you meet the cut, be rolling already. | 3.9 |
| 29 | `ch01.b04.matsukichi.004` | `bout_scored:3` | 松吉 / Matsukichi | 竹丸、さっきの試合、足がもつれてたぞ。 | — | Takemaru, your feet were tangled in that last bout. | 3.7 |
| 30 | `ch01.b04.takemaru.005` | `bout_scored:3` | 竹丸 / Takemaru | 松吉さんこそ。 | — | So were yours. | 1.6 |
| 31 | `ch01.b04.sekireisai.006` | `beat_complete` | 石鈴斎 / Sekireisai | 相手が強いほど、よう転がる。覚えておけ。 | — | The stronger the opponent, the better you roll. Remember it. | 4.0 |

Tutorial prompts (L4 `ui_strings`, not voiced):

| Prompt id | Trigger | Japanese | English |
|---|---|---|---|
| `ch01.b04.prompt.01` | `volume_enter:vol_ch01_dojo_yard` | 合わせた直後（0.4秒以内）に 左右＋{Jump} | Within 0.4 s of an awase: Left/Right + {Jump}. |

#### ch01.b05 · The sunbeam on the veranda (縁側の陽だまり)

| # | Line id | Trigger | Speaker | Japanese | Reading notes | English subtitle | s |
|---:|---|---|---|---|---|---|---:|
| 32 | `ch01.b05.takemaru.001` | `beat_start` | 竹丸 / Takemaru | 虎之介さまだ。また朝稽古に遅れて……。 | 朝稽古（あさげいこ） | It is Lord Toranosuke. Late for morning practice again… | 3.9 |
| 33 | `ch01.b05.matsukichi.002` | `beat_start` | 松吉 / Matsukichi | また大坂の使いと会っていたらしい。 | 大坂（おおさか） | They say he met the man from Osaka again. | 3.7 |
| 34 | `ch01.b05.toranosuke.003` | `volume_enter:vol_ch01_engawa_east` | 虎之介 / Toranosuke | 先生の相手をしたそうだな。『刃を急がせるな』か。 | — | I hear you faced Sensei. 'Do not hurry your blade,' was it? | 4.5 |
| 35 | `ch01.b05.toranosuke.004` | `volume_enter:vol_ch01_engawa_east` | 虎之介 / Toranosuke | 俺は急ぐ。急がねば、間に合わぬこともある。 | — | I hurry. Some things will not wait. | 4.1 |
| 36 | `ch01.b05.nyaakoto.005` | `volume_enter:vol_ch01_engawa_east` | ニャーコト / Nyaakoto | ……何があった、虎之介。 | — | …What happened, Toranosuke? | 2.5 |
| 37 | `ch01.b05.toranosuke.006` | `volume_enter:vol_ch01_engawa_east` | 虎之介 / Toranosuke | 何も。稽古の話だ。 | — | Nothing. This is about practice. | 2.2 |
| 38 | `ch01.b05.sekireisai.007` | `volume_enter:vol_ch01_engawa_mentor` | 石鈴斎 / Sekireisai | 厩へ行け。栗丸が退屈しておる。弓も引いてこい。 | 厩（うまや）・栗丸（くりまる） | Go to the stable. Kurimaru is bored. Then draw your bow. | 4.5 |

Tutorial prompts (L4 `ui_strings`, not voiced):

| Prompt id | Trigger | Japanese | English |
|---|---|---|---|
| `ch01.b05.prompt.01` | `volume_enter:vol_ch01_engawa_sunbeam` | {Interact}で一礼（任意） | {Interact} to bow (optional). |

#### ch01.b06 · Tack up Kurimaru and ride to the range (栗丸に鞍を置き、的場へ)

| # | Line id | Trigger | Speaker | Japanese | Reading notes | English subtitle | s |
|---:|---|---|---|---|---|---|---:|
| 39 | `ch01.b06.takemaru.001` | `beat_start` | 竹丸 / Takemaru | 鞍はそこに。下鞍を敷いてから置いてください。 | 鞍（くら）・下鞍（したぐら） | The saddle is there. Lay the pad first, then set it. | 4.5 |
| 40 | `ch01.b06.takemaru.002` | `interact:ip_ch01_kura` | 竹丸 / Takemaru | 腹帯を締めて。……栗丸、また腹をふくらませてます。 | 腹帯（はるび） | Tighten the girth. …She is puffing out her belly again. | 5.0 |
| 41 | `ch01.b06.takemaru.003` | `interact:ip_ch01_haruobi` | 竹丸 / Takemaru | 鐙は力革に。左右の長さをそろえて。 | 鐙（あぶみ）・力革（ちからがわ） | Stirrups on the leathers. Match the two sides. | 3.5 |
| 42 | `ch01.b06.takemaru.004` | `interact:ip_ch01_abumi` | 竹丸 / Takemaru | 次は轡を……あ、またそっぽを向いた。 | 轡（くつわ） | Now the bit… ah, she has turned her head away again. | 3.7 |
| 43 | `ch01.b06.nyaakoto.005` | `interact_refused:ip_ch01_kutsuwa:1` | ニャーコト / Nyaakoto | ……栗丸。 | — | …Kurimaru. | 1.2 |
| 44 | `ch01.b06.takemaru.006` | `interact_refused:ip_ch01_kutsuwa:2` | 竹丸 / Takemaru | 大麦の穂、袖に入れてたでしょう。 | 大麦（おおむぎ） | You have an ear of barley in your sleeve, do you not? | 3.6 |
| 45 | `ch01.b06.takemaru.007` | `item_given:barley_ear` | 竹丸 / Takemaru | ……毎朝、これです。 | — | …Every morning, this. | 2.0 |
| 46 | `ch01.b06.takemaru.008` | `interact:ip_ch01_kutsuwa` | 竹丸 / Takemaru | 面繋よし、轡よし。手綱を取って、乗ってください。 | 面繋（おもがい）・手綱（たづな） | Headstall, bit, all good. Take the reins and mount. | 4.5 |
| 47 | `ch01.b06.takemaru.009` | `mount` | 竹丸 / Takemaru | 嵐には近づかないで。袖を噛みますから。 | 嵐（あらし） | Keep clear of Arashi. He bites sleeves. | 3.9 |
| 48 | `ch01.b06.nyaakoto.010` | `volume_enter:vol_ch01_lane_pheasant` | ニャーコト / Nyaakoto | どう、どう……。雉だ。ただの雉だ。 | 雉（きじ） | Easy, easy… A pheasant. Only a pheasant. | 3.1 |

Tutorial prompts (L4 `ui_strings`, not voiced):

| Prompt id | Trigger | Japanese | English |
|---|---|---|---|
| `ch01.b06.prompt.01` | `beat_start` | 光る馬具で{Interact}：鞍・腹帯・鐙・轡の順 | {Interact} at each tack piece: saddle, girth, stirrups, bit. |
| `ch01.b06.prompt.02` | `interact_refused:ip_ch01_kutsuwa:2` | もう一度{Interact}で大麦の穂を与える | Press {Interact} again to offer the ear of barley. |
| `ch01.b06.prompt.03` | `interact:ip_ch01_kutsuwa` | {Interact}で栗丸に乗る（右から） | {Interact} to mount Kurimaru (from the right). |
| `ch01.b06.prompt.04` | `mount` | 前進で常歩。前進しながら{Sprint}長押しで歩度を上げる | Move forward to walk. Hold {Sprint} while moving forward to quicken her gait. |
| `ch01.b06.prompt.05` | `horse_spooked` | 馬が驚いた。手綱を引かず、落ち着くのを待つ | She is spooked. Ease the reins and let her settle. |

#### ch01.b07 · Draw the bow at the range (的場で弓を引け)

| # | Line id | Trigger | Speaker | Japanese | Reading notes | English subtitle | s |
|---:|---|---|---|---|---|---|---:|
| 49 | `ch01.b07.baio.001` | `beat_start` | 梅翁 / Baiō | 来なされたか。弓は、ここに。 | — | So you have come. Your bow is here. | 2.6 |
| 50 | `ch01.b07.baio.002` | `equip:18` | 梅翁 / Baiō | 弓構え。……打起し。 | 弓構え（ゆがまえ）・打起し（うちおこし） | Ready the bow. …Raise it. | 2.0 |
| 51 | `ch01.b07.baio.003` | `draw_complete:first` | 梅翁 / Baiō | 引分けて……会。息を止めず、満ちるのを待ちなされ。 | 引分け（ひきわけ）・会（かい） | Draw… and hold. Keep breathing. Let the draw fill. | 5.0 |
| 52 | `ch01.b07.baio.004` | `release:first` | 梅翁 / Baiō | 離れたら、弓を追うな。残心。 | 離れ（はなれ）・残心（ざんしん） | After the release, do not chase the bow. Zanshin. | 3.3 |
| 53 | `ch01.b07.matsukichi.005` | `mato_hit` (repeatable) | 松吉 / Matsukichi | 中り！ | 中り（あたり） | Hit! | 1.0 |
| 54 | `ch01.b07.matsukichi.006` | `mato_miss` (repeatable) | 松吉 / Matsukichi | 外れ！ | 外れ（はずれ） | Miss! | 1.0 |
| 55 | `ch01.b07.baio.007` | `set_failed` (repeatable) | 梅翁 / Baiō | 矢取りを待ちなされ。もう一度、六本。 | 矢取り（やとり） | Wait while the arrows are fetched. Six more. | 3.5 |
| 56 | `ch01.b07.baio.008` | `wave_start:2` | 梅翁 / Baiō | よろしい。次は吊り的。揺れる的は、行く先を射なされ。 | 吊り的（つりまと） | Good. Now the hanging marks. Shoot where a swinging mark is going. | 4.9 |
| 57 | `ch01.b07.baio.009` | `beat_complete` | 梅翁 / Baiō | ……よい弓を引かれるようになった。 | — | …You draw a good bow now. | 2.3 |
| 58 | `ch01.b07.matsukichi.010` | `beat_complete` | 松吉 / Matsukichi | 六本、安土の石で曲がってます。鍛冶場へどうぞ。 | 安土（あづち） | Six shafts bent on a stone in the azuchi. The smithy can fix them. | 4.5 |

Tutorial prompts (L4 `ui_strings`, not voiced):

| Prompt id | Trigger | Japanese | English |
|---|---|---|---|
| `ch01.b07.prompt.01` | `equip:18` | {Fire}長押しで引分け（0.65秒）。会で狙い、離して放つ | Hold {Fire} to draw (0.65 s). Aim at full draw; release to loose. |
| `ch01.b07.prompt.02` | `wave_start:2` | 遠い的ほど矢は落ちる。揺れの先を狙う | Arrows drop over distance. Lead the swing. |

#### ch01.b08 · The One-Claw Stone Wood (一爪石の森)

| # | Line id | Trigger | Speaker | Japanese | Reading notes | English subtitle | s |
|---:|---|---|---|---|---|---|---:|
| 59 | `ch01.b08.nyaakoto.001` | `interact:poi_ch01_issoseki` | ニャーコト / Nyaakoto | 一爪石……。初代さまが、爪一本で割ったという。 | 一爪石（いっそうせき） | The One-Claw Stone… The founder split it with one claw, they say. | 4.5 |
| 60 | `ch01.b08.nyaakoto.002` | `interact:poi_ch01_issoseki` | ニャーコト / Nyaakoto | 割れた石より、割った心を見よ……か。 | — | 'Look not at the split stone, but the mind that split it.' | 3.9 |
| 61 | `ch01.b08.nyaakoto.003` | `interact:poi_ch01_vista` | ニャーコト / Nyaakoto | 猫山まで二里。今日は城がよく見える。 | 猫山（ねこやま）・二里（にり） | Two ri to Nekoyama. The castle is clear today. | 3.7 |
| 62 | `ch01.b08.nyaakoto.004` | `interact:poi_ch01_sakaiishi` | ニャーコト / Nyaakoto | 家の紋……。誰が刻んだのだろう。 | 紋（もん） | The house mon… I wonder who carved it. | 3.3 |
| 63 | `ch01.b08.nyaakoto.005` | `idle_s:180` | ニャーコト / Nyaakoto | 槌の音……鍛冶場はあちらか。 | 槌（つち） | A hammer… The smithy is that way. | 3.1 |

#### ch01.b09 · Straighten and refletch the arrows (矢を矯め、羽を付け直せ)

| # | Line id | Trigger | Speaker | Japanese | Reading notes | English subtitle | s |
|---:|---|---|---|---|---|---|---:|
| 64 | `ch01.b09.tetsugoro.001` | `beat_start` | 鉄五郎 / Tetsugorō | 矢を曲げてきたな。六本か。 | — | Bent some arrows, did you? Six? | 2.6 |
| 65 | `ch01.b09.tetsugoro.002` | `beat_start` | 鉄五郎 / Tetsugorō | 火を起こせ。竹は熱で素直になる。 | — | Wake the fire. Heat makes bamboo honest. | 3.3 |
| 66 | `ch01.b09.tetsugoro.003` | `step_failed:heat` (repeatable; cooldown 20 s) | 鉄五郎 / Tetsugorō | 焦がすな。竹が泣く。冷まして、もう一度。 | — | Don't scorch it. Bamboo weeps. Let it cool, then again. | 3.7 |
| 67 | `ch01.b09.tetsugoro.004` | `step_complete:bend:3` | 鉄五郎 / Tetsugorō | 曲がった矢は、嘘をつく。 | — | A bent arrow lies. | 2.4 |
| 68 | `ch01.b09.tetsugoro.005` | `step_start:paste` | 鉄五郎 / Tetsugorō | 膠は薄く。羽は三枚、向きをそろえろ。 | 膠（にかわ） | Thin glue. Three feathers, all facing the same way. | 3.5 |
| 69 | `ch01.b09.tetsugoro.006` | `step_start:assemble` | 鉄五郎 / Tetsugorō | 糸で巻いて締めろ。……赤羽か。遠目にもよく見える。 | 赤羽（あかばね）・遠目（とおめ） | Bind it tight. …Red feathers. Easy to find from afar. | 5.0 |
| 70 | `ch01.b09.tetsugoro.007` | `step_start:inspect` | 鉄五郎 / Tetsugorō | 数えろ。 | — | Count them. | 1.0 |
| 71 | `ch01.b09.nyaakoto.008` | `step_start:inspect` | ニャーコト / Nyaakoto | 十二本。 | — | Twelve. | 1.0 |
| 72 | `ch01.b09.tetsugoro.009` | `output_complete` | 鉄五郎 / Tetsugorō | 帳面に書いとけ。作ったもんは数えて残す。それがここの決まりだ。 | 帳面（ちょうめん） | Write it in the book. What you make, you count and keep. That's the rule here. | 6.2 |
| 73 | `ch01.b09.tetsugoro.010` | `site_restored:2` | 鉄五郎 / Tetsugorō | ……雨が続くと火縄が死ぬ。何か手はないもんか。 | 火縄（ひなわ） | …When the rain keeps on, the match dies. There must be a way. | 4.8 |
| 74 | `ch01.b09.takemaru.011` | `beat_complete` | 竹丸 / Takemaru | ニャーコト殿！　先生がお呼びです。表の縁側へ。 | 縁側（えんがわ） | Nyaakoto! Sensei is asking for you. The front veranda. | 4.3 |

Tutorial prompts (L4 `ui_strings`, not voiced):

| Prompt id | Trigger | Japanese | English |
|---|---|---|---|
| `ch01.b09.prompt.01` | `beat_start` | {Interact}で鞴を押し、火床を起こす | Press {Interact} to work the bellows and wake the hearth. |
| `ch01.b09.prompt.02` | `step_start:heat` | 矢を炭にかざし、艶が出たら離す | Warm the shaft over the coals; lift it when it gleams. |
| `ch01.b09.prompt.03` | `step_start:bend` | 矯め木で押し、筋がまっすぐになったら離す | Press it in the tamegi; release when the line runs true. |
| `ch01.b09.prompt.04` | `step_start:paste` | {Interact}で膠を引き、羽を付ける | {Interact} to spread glue and set the feathers. |

#### ch01.b10 · The sword that kills, the sword that gives life (殺人刀と活人剣)

| # | Line id | Trigger | Speaker | Japanese | Reading notes | English subtitle | s |
|---:|---|---|---|---|---|---|---:|
| 75 | `ch01.b10.household.001` | `volume_enter:vol_ch01_estate_north_gate` | 屋敷の者 / Household | 先生が縁側におられるうちは、この屋敷は安泰や。 | 安泰（あんたい） | While Sensei sits on that veranda, this house is safe. | 4.7 |
| 76 | `ch01.b10.sekireisai.002` | `volume_enter:vol_ch01_estate_engawa` | 石鈴斎 / Sekireisai | 殺人刀、活人剣。聞いたことはあるな。 | 殺人刀（せつにんとう）・活人剣（かつにんけん） | Setsunintō and katsujinken. You have heard the words. | 3.6 |
| 77 | `ch01.b10.nyaakoto.003` | `volume_enter:vol_ch01_estate_engawa` | ニャーコト / Nyaakoto | 人を斬る刀と、人を活かす剣、と。 | 活かす（いかす） | A blade that kills, and a sword that gives life. | 3.2 |
| 78 | `ch01.b10.sekireisai.004` | `volume_enter:vol_ch01_estate_engawa` | 石鈴斎 / Sekireisai | 違う。同じ一振りの話じゃ。 | 一振り（ひとふり） | No. They are one and the same blade. | 2.6 |
| 79 | `ch01.b10.sekireisai.005` | `volume_enter:vol_ch01_estate_engawa` | 石鈴斎 / Sekireisai | 一人の悪を斬り、万人を活かす。刀が許されるのは、そこまでじゃ。 | 万人（ばんにん） | Cut one evil so ten thousand may live. A blade is forgiven that far, no further. | 6.0 |
| 80 | `ch01.b10.sekireisai.006` | `volume_enter:vol_ch01_estate_engawa` | 石鈴斎 / Sekireisai | だが斬る前に、何を活かすかを数えよ。 | — | But before you cut, count what you mean to keep alive. | 3.7 |
| 81 | `ch01.b10.toranosuke.007` | `volume_enter:vol_ch01_estate_engawa` | 虎之介 / Toranosuke | 先生、御免。……ニャーコト、表で立ち合え。袋竹刀でいい。 | 御免（ごめん）・袋竹刀（ふくろじない） | Pardon me, Sensei. …Nyaakoto, face me outside. Fukuro-shinai will do. | 5.2 |
| 82 | `ch01.b10.toranosuke.008` | `volume_enter:vol_ch01_estate_engawa` | 虎之介 / Toranosuke | 今日しかない。……明日、大坂から使いが来る。 | — | Today is all I have. …Tomorrow, a man comes from Osaka. | 4.3 |
| 83 | `ch01.b10.sekireisai.009` | `volume_enter:vol_ch01_estate_engawa` | 石鈴斎 / Sekireisai | 鷲尾。勝って、何を得る。 | 鷲尾（わしお） | Washio. If you win, what do you gain? | 2.5 |
| 84 | `ch01.b10.toranosuke.010` | `volume_enter:vol_ch01_estate_engawa` | 虎之介 / Toranosuke | 名にございます。鷲尾の名が、まだ折れておらぬ証を。 | 証（あかし） | A name, Sensei. Proof that the Washio name is not yet broken. | 4.9 |
| 85 | `ch01.b10.sekireisai.011` | `volume_enter:vol_ch01_estate_engawa` | 石鈴斎 / Sekireisai | ……よかろう。先に三本じゃ。ニャーコト、受けよ。 | 先に三本: first to three points (not 三本勝負, which is best of three) | …Very well. First to three. Nyaakoto, accept. | 4.5 |

#### ch01.b11 · Fukuro-shinai bout with Toranosuke (袋竹刀で虎之介と立ち合う)

| # | Line id | Trigger | Speaker | Japanese | Reading notes | English subtitle | s |
|---:|---|---|---|---|---|---|---:|
| 86 | `ch01.b11.sekireisai.001` | `beat_start` | 石鈴斎 / Sekireisai | 両者、礼。 | 礼（れい） | Both of you, bow. | 1.2 |
| 87 | `ch01.b11.toranosuke.002` | `beat_start` (anchor: bible §6.5 register sample) | 虎之介 / Toranosuke | 礼はいい。来い、ニャーコト。今日こそ一本取る。 | — | Skip the bow. Come, Nyaakoto. Today I take a point. | 4.3 |
| 88 | `ch01.b11.sekireisai.003` | `beat_start` | 石鈴斎 / Sekireisai | 礼はせよ。……構えて、始め！ | 構え（かまえ） | You will bow. …Kamae. Begin! | 2.7 |
| 89 | `ch01.b11.sekireisai.004` | `point:player` (repeatable; points 1-2) | 石鈴斎 / Sekireisai | 一本。ニャーコト。 | — | Point. Nyaakoto. | 1.8 |
| 90 | `ch01.b11.sekireisai.005` | `point:rival` (repeatable; points 1-2) | 石鈴斎 / Sekireisai | 一本。鷲尾。 | — | Point. Washio. | 1.2 |
| 91 | `ch01.b11.sekireisai.006` | `ring_out` (repeatable) | 石鈴斎 / Sekireisai | 縄を出たぞ。戻れ。 | 縄（なわ）: the straw rope marking the ring; the modern kendo call 場外 is avoided | Out of the ring. Return. | 1.6 |
| 92 | `ch01.b11.toranosuke.007` | `point:rival:first` | 虎之介 / Toranosuke | どうした。先生の教えは、それだけか。 | — | What is wrong? Is that all Sensei taught you? | 3.5 |
| 93 | `ch01.b11.sekireisai.008` | `feint_landed:first` (diegetic tell for tora_feint) | 石鈴斎 / Sekireisai | 目を見るな、足を見よ。蹴らぬ足は、打たぬ足じゃ。 | 蹴る（ける） | Do not watch his eyes. Watch his feet. A foot that does not push does not strike. | 5.4 |
| 94 | `ch01.b11.toranosuke.009` | `score:player_leads_2` | 虎之介 / Toranosuke | くそっ……急げ、急げ……！ | — | Damn it… Faster. Faster…! | 2.7 |
| 95 | `ch01.b11.sekireisai.010` | `duel_won` (branch: win) | 石鈴斎 / Sekireisai | それまで。三本、ニャーコト。 | — | Enough. Three points to Nyaakoto. | 2.6 |
| 96 | `ch01.b11.toranosuke.011` | `duel_won` (branch: win) | 虎之介 / Toranosuke | ……もう一度だ。 | — | …Again. | 1.8 |
| 97 | `ch01.b11.sekireisai.012` | `duel_won` (branch: win) | 石鈴斎 / Sekireisai | 今日の一本は、今日かぎりじゃ。 | — | Today's point belongs to today alone. | 3.1 |
| 98 | `ch01.b11.toranosuke.013` | `duel_won` (branch: win) | 虎之介 / Toranosuke | ……失礼いたす。 | — | …By your leave. | 1.8 |
| 99 | `ch01.b11.sekireisai.014` | `loss_continue` (branch: loss) | 石鈴斎 / Sekireisai | それまで。三本、鷲尾。 | — | Enough. Three points to Washio. | 2.1 |
| 100 | `ch01.b11.toranosuke.015` | `loss_continue` (branch: loss) | 虎之介 / Toranosuke | ……勝った。勝ったぞ。 | — | …I won. I won. | 2.3 |
| 101 | `ch01.b11.sekireisai.016` | `loss_continue` (branch: loss) | 石鈴斎 / Sekireisai | 勝ちを急いだな、虎之介。 | — | You hurried to win, Toranosuke. | 2.4 |
| 102 | `ch01.b11.toranosuke.017` | `loss_continue` (branch: loss) | 虎之介 / Toranosuke | 急がねば、間に合わぬのです。 | — | If I do not hurry, I will be too late. | 2.8 |
| 103 | `ch01.b11.sekireisai.018` | `match_lost` (repeatable; attempts 1-2 only) | 石鈴斎 / Sekireisai | もう一度。今度は、あやつの急ぎを使え。 | — | Again. This time, use his haste. | 3.7 |

Tutorial prompts (L4 `ui_strings`, not voiced):

| Prompt id | Trigger | Japanese | English |
|---|---|---|---|
| `ch01.b11.prompt.01` | `beat_start` | 三本先取。面・小手・胴への一撃で一本 | First to three. A clean hit to head, wrist or body scores. |
| `ch01.b11.prompt.02` | `beat_start` | 輪の外へ出ると仕切り直し | Step out of the ring and the exchange resets. |

#### ch01.b12 · The blade held in trust (刀を預かる)

| # | Line id | Trigger | Speaker | Japanese | Reading notes | English subtitle | s |
|---:|---|---|---|---|---|---|---:|
| 104 | `ch01.b12.sekireisai.001` | `branch:b11_loss` (branch: loss) | 石鈴斎 / Sekireisai | 負けて受け取る刀は、重いか。 | — | Is a blade heavy, when taken after a loss? | 2.8 |
| 105 | `ch01.b12.sekireisai.002` | `branch:b11_loss` (branch: loss) | 石鈴斎 / Sekireisai | 重さを知る者にしか、刀は預けられぬ。 | — | Only one who feels its weight can be trusted with it. | 3.7 |
| 106 | `ch01.b12.sekireisai.003` | `interact:ip_ch01_katana` (blocking) | 石鈴斎 / Sekireisai | おぬしの刀じゃ。研ぎから戻った。 | 研ぎ（とぎ） | Your blade. It is back from the polisher. | 3.3 |
| 107 | `ch01.b12.sekireisai.004` | `interact:ip_ch01_katana` (blocking; anchor: bible §3.2 katsujinken line) | 石鈴斎 / Sekireisai | 刀は民から預かるものじゃ。 | 民（たみ） | A blade is held in trust from the people. | 2.8 |
| 108 | `ch01.b12.nyaakoto.005` | `interact:ip_ch01_katana` (blocking; anchor: catalog ch01 line 2) | ニャーコト / Nyaakoto | 間合いを測り、命を守ります。 | — | I will measure the distance and protect life. | 4.8 |
| 109 | `ch01.b12.sekireisai.006` | `interact:ip_ch01_katana` (blocking; anchor: catalog ch01 line 3) | 石鈴斎 / Sekireisai | それが猫柳生新陰流。剣は民のためにある。 | 猫柳生新陰流（ニャーギュウしんかげりゅう） | That is Nyaagyū Shinkage-ryū. The sword serves the people. | 4.8 |
| 110 | `ch01.b12.sekireisai.007` | `blocking_end` | 石鈴斎 / Sekireisai | 夕餉まで、刀と語らっておけ。 | 夕餉（ゆうげ） | Until supper, keep company with your sword. | 2.9 |

Tutorial prompts (L4 `ui_strings`, not voiced):

| Prompt id | Trigger | Japanese | English |
|---|---|---|---|
| `ch01.b12.prompt.01` | `blocking_end` | {Sheathe}で抜刀・納刀 | Press {Sheathe} to draw or sheathe the blade. |

#### ch01.b13 · The sky splits (空が裂ける)

| # | Line id | Trigger | Speaker | Japanese | Reading notes | English subtitle | s |
|---:|---|---|---|---|---|---|---:|
| 111 | `ch01.b13.takemaru.001` | `seq t=31.0 s` | 竹丸 / Takemaru | 先生……空が……。 | — | Sensei… the sky… | 2.1 |
| 112 | `ch01.b13.household.002` | `seq t=33.7 s` | 屋敷の者 / Household | 火事か……いや、空や！　空が割れとる！ | — | A fire? No, the sky! The sky's splitting! | 3.5 |
| 113 | `ch01.b13.toranosuke.003` | `seq t=46.0 s` | 虎之介 / Toranosuke | なんだ……あれは。 | — | What… is that? | 2.0 |
| 114 | `ch01.b13.sekireisai.004` | `seq t=58.0 s` | 石鈴斎 / Sekireisai | 梅翁、鐘を打て。 | 梅翁（ばいおう） | Baiō. Ring the bell. | 1.6 |
| 115 | `ch01.b13.baio.005` | `seq t=60.2 s` | 梅翁 / Baiō | ……承知。 | — | …At once. | 1.2 |
| 116 | `ch01.b13.sekireisai.006` | `seq t=88.0 s` | 石鈴斎 / Sekireisai | ニャーコト。預けたものを、忘れるな。 | — | Nyaakoto. Do not forget what you hold in trust. | 3.5 |
| 117 | `ch01.b13.nyaakoto.007` | `seq t=92.1 s` | ニャーコト / Nyaakoto | ……はい、先生。 | — | …Yes, Sensei. | 1.6 |


---

## 6. Historical and cultural accuracy

These notes are for the historian and practitioner review (bible §20, open item 2). Anything marked **flag** needs sign-off before release copy calls it accurate.

### 6.1 Sword school and training

- **Respect rule.** Bible §3.1 applies: 猫柳生新陰流 is fictional. No kata of the living Yagyū Shinkage-ryū, and in particular nothing from the 三学円之太刀 set, is named, sequenced or motion-captured. The attacks are generic targets (面, 小手, 胴) plus 袈裟. The pupils' lesson motions need practitioner review before motion capture.
- **殺人刀 / 活人剣.** The paired phrase comes from Zen: the introduction to case 12 of the 『碧巌録』 (Blue Cliff Record) calls "the killing blade, the life-giving sword" an ancient rule and a present essential. Yagyū Munenori built two sections of 『兵法家伝書』 (1632) around it, including the idea of killing one evil so that ten thousand may live. Sekireisai's b10 line paraphrases that idea and does not quote the text. In 1623 the book is nine years in the future, so in the fiction the idea is an oral teaching drawn from its Zen source. Readings: せつにんとう and かつにんけん (さつじんとう is also heard). Sources: [Aishinkan Kyoto on 兵法家伝書](https://www.aishinkankyoto.jp/heiho-kadensho1/), [Japanese Wikipedia, 兵法家伝書](https://ja.wikipedia.org/wiki/%E5%85%B5%E6%B3%95%E5%AE%B6%E4%BC%9D%E6%9B%B8), [禅語 殺人刀活人剣](https://zengo.sk46.com/data/setsuninto.html). Print edition to cite: 渡辺一郎校注『兵法家伝書 付・新陰流兵法目録事』岩波文庫 (verify the edition).
- **水月.** 『兵法家伝書』 treats 水月 as a matter of position and distance. The game's ring is an abstraction of that idea, not the text's method.
- **転 (marobashi).** A core Shinkage principle of rolling, adaptive response. The official Yagyūkai description of the school stresses natural, whole-body response to the opponent ([Yagyūkai](https://yagyu-shinkage-ryu.jp/?page_id=944&lang=en)). The 120 cm flank step is a game mechanic, not the school's technique.
- **正眼.** Also written 青眼, 晴眼 and 清眼 depending on the school; it is a centre (中段) guard. Pointing the tip at the throat is a generic description.
- **Training blades.**
  - The 木刀 is white oak (白樫), which matches the existing `DojoBokkenPBR` white-oak texture set.
  - The 袋竹刀 is split bamboo in a leather sleeve. Shinkage tradition credits it to Kamiizumi Nobutsuna and calls it 蟇肌 (hikihada, "toad skin") after the wrinkled lacquered leather ([Japanese Wikipedia, 袋竹刀](https://ja.wikipedia.org/wiki/%E8%A2%8B%E7%AB%B9%E5%88%80)). To avoid imitating a living school's signature equipment, ours is **undyed, unlacquered leather**.
- **No armour in the bout.** Protective gear and full-contact shinai practice are credited to 長沼四郎左衛門国郷 of 直心影流 in the Shōtoku era (1711–16) ([AJKF column](https://www.kendo.or.jp/knowledge/books/column_02/), [kotobank](https://kotobank.jp/word/%E9%95%B7%E6%B2%BC%E5%9B%9B%E9%83%8E%E5%B7%A6%E8%A1%9B%E9%96%80-1382296)). The 1623 bout is therefore fought without 防具 and without modern kendo calls: no 「面あり」 and no 「始め」 with a flag.
- **Scoring words (flag).** 「一本」 is used because the bible's arc depends on it: 「今日こそ一本取る」 now, and 「ようやく、一本じゃ」 in the finale. Whether this bout-scoring vocabulary was in use in 1623 needs historian confirmation. The bout is **first to three points**, so Sekireisai says 「先に三本じゃ」. 「三本勝負」 is deliberately avoided: in later usage it means a best-of-three match (first to two), which would contradict the rules (review fix).
- **Oath roll (heirloom `ch01.c03`).** Edo martial oath rolls put the deity names and penalty clauses at the head of a roll, and each pupil then added the date, name and a blood seal (血判). Earlier oaths were often written on Kumano 牛王宝印 paper ([Japanese Wikipedia, 起請文](https://ja.wikipedia.org/wiki/%E8%B5%B7%E8%AB%8B%E6%96%87), [kotobank](https://kotobank.jp/word/%E8%B5%B7%E8%AB%8B%E6%96%87-50517)). The prop is a roll with the formal name 猫琴; this is the only place those kanji appear (bible §6.1).
- **Name board (flag).** The 名札掛け is well attested in later dojos. In 1623 it is a storytelling device, because it sets up ch07's seized board and ch08's rehanging. Nyaakoto's plaque is written in katakana, because the bible reserves the formal kanji for the oath roll.
- **The dojo building (flag).** A separate purpose-built dojo hall is more typical of later Edo, but plausible for a house that teaches the sword. The existing dojo source took its massing from samurai-residence references (its `manifest.json` cites the Iwakura residence and Nihon Minka-en).
- **Etiquette.** A seated bow (座礼) opens practice. There are no modern commands such as 正面に礼 or 黙想.

### 6.2 Archery

- **The bow.** About 221 cm, asymmetric, gripped about one-third from the bottom ([Kyudo Federation equipment rules](https://www.kyudo.jp/pdf/schedule/taikai/20240607_tebiki.pdf)). The arrow rests on the right; the archer wears a 弽 glove; the bow turns in the hand after release (弓返り); arrows have three feathers. All as bible §4.2.
- **Shooting stages (flag).** The names 弓構え / 打起し / 引分け / 会 / 離れ / 残心 come from the 射法八節, which was standardized in the 1953 『弓道教本』 ([All Japan Kyudo Federation](https://www.kyudo.jp/howto/syaho.html)). Period Heki lines used their own vocabulary. The modern names are used for clarity.
- **Target and distance.** 28 m and the 尺二 (36 cm) target are the modern 近的 standard; period ranges varied. Baiō does not give the distance in metres (the HUD does), and 間 and 里 are used in voice.
- **Range words.** 中り (hit), 矢取り (arrow retrieval) and 看的 (target keeper) are standard range vocabulary ([Kyudo Federation terminology](https://www.kyudo.jp/howto/terminology.html)).
- **Swinging targets.** The 吊り的 are a **game drill**, not a named period practice.
- **通し矢.** The long-distance archery fashion, attested from the early 1600s (bible §19), appears only as a codex entry.
- **Hand words.** The bow hand is 弓手 (ゆんで) and the rein hand is 馬手 (めて), which is why mounted archery shoots to the left. This is used from ch02.

### 6.3 Horse and tack

- **Kurimaru.** A native mare of the Kiso type. Kiso horses average about 133 cm at the withers for mares and 136 cm for stallions ([Japan Heritage portal](https://japan-heritage.bunka.go.jp/ja/culturalproperties/result/2011/)), which matches the bible's 130 cm. She is chestnut (栗毛). Arashi is a black-bay (黒鹿毛) stallion.
- **Hooves and gait.** Horses are unshod; straw 馬沓 hang in the stable. Only walk and trot are used in ch01. The lateral 側対歩 question (bible §4.5) must be settled by the equine animator before the trot is final.
- **Mounting from the right.** Japanese riders mounted from the horse's right until Western riding arrived. Picture scrolls such as the 平治物語絵巻 show it ([Edo-Tokyo Museum library answer](https://www.edo-tokyo-museum.or.jp/purpose/library/reference/alphabet/30775/%E6%99%82%E4%BB%A3%E5%8A%87%E3%81%A7%E9%A6%AC%E3%81%AB%E4%B9%97%E3%82%8B%E3%81%A8%E3%81%8D%E3%80%81%E5%8F%B3%E5%81%B4%E3%81%8B%E3%82%89%E4%B9%97%E3%81%A3%E3%81%A6%E3%81%84%E3%82%8B%E3%81%AE%E3%82%92)). The animation and tie-rail layout use the right side.
- **Tack order.** Pad, kura, haruobi, abumi on 力革, kutsuwa and omogai, then tazuna, following bible §4.5.
- **Saddle-pad names (flag).** The bible's 肌付 / 切付 names are still to be verified, so the voice uses the generic 下鞍.
- **Measured references.** The four-piece kura tree is Met 2000.405 ([record](https://www.metmuseum.org/art/collection/search/26572)). The broad-toed, open-heeled abumi with a front mon is Met 2008.120 ([record](https://www.metmuseum.org/art/collection/search/35376)).
- **Horse behaviour.** Puffing the belly against the girth, so that it has to be retightened, is real behaviour. 「どう、どう」 is the traditional calming call. Barley as a bribe is the bible's humor beat.

### 6.4 Architecture, props and landscape

- **Dojo materials.** 入母屋 roof, ibushi kawara, 欅 pillars, hinoki floor, 羽目板, 連子窓 and 明障子. No glass anywhere (bible §19).
- **半鐘.** Before Edo's fire-watch towers (the first came after the Meireki fire of 1657), 半鐘 served as signal bells in temples and military camps ([Japanese Wikipedia, 半鐘](https://ja.wikipedia.org/wiki/%E5%8D%8A%E9%90%98), [kotobank](https://kotobank.jp/word/%E5%8D%8A%E9%90%98-606566)). Ours hangs in a timber frame at the estate gate, never on a 火の見櫓 (on the bible's avoid list). The strike pattern is rapid and continuous; the later standardized fire-code patterns are not used.
- **The One-Claw Stone.** A respectful counterpart to Yagyū's 一刀石, the granite boulder of about 8 × 7 × 2 m split by a straight diagonal crack near Amanoiwatate Shrine. Legend says Yagyū Sekishūsai cut a tengu and found he had split the rock ([Nara City tourism](https://www.city.nara.lg.jp/sightseeing/naraharu/111494.html)). Ours is 3 m (bible §15.2), attributed to the fictional founder's claw, with no tengu and no shrine name.
- **Arrow straightening.** Arrow makers heat bamboo shafts and work out every bend with a notched 矯め木 ([Koyamaya arrow-making process](http://www.koyamaya.com/takeyanodekirumade.htm)). b09's heat → bend steps follow this. Fletching uses 膠 glue and thread binding.
- **Smithy bellows.** The smithy uses a box bellows (箱鞴). The seesaw 天秤鞴 of the 1690s is on the bible's avoid list.
- **Units.** 間 (about 1.82 m) and 里 (about 3.9 km; Nekoyama at 8 km ≈ 2 里) in voice. Metric in the HUD.
- **Late-spring nature.** Uguisu song, pheasant, young barley in ear, wisteria in flower. No cherry blossom (it is past), and no cicadas (too early).
- **Avoid.** 招き猫, ukiyo-e posters, 火の見櫓, glass windows, the theatrical black ninja suit, paved lanes (bible §19).

### 6.5 Clothing

| Character | Dress in ch01 |
|---|---|
| Nyaakoto | Practice 小袖 and 袴 with a 襷 sleeve tie, per bible §6.1's keikogi and hakama. Not the modern heavy kendo jacket, and no 防具. Armour arrives in ch02 |
| Sekireisai | 十徳 over a kimono (bible §6.1); in b02 the 十徳 is set aside and he wears 襷 |
| Toranosuke | Riding 野袴 and a rust-coloured 小袖. Black lacquer armour and the grey haori belong to later chapters |
| Pupils | 小袖, 袴, 襷. Baiō's are faded and patched |
| Tetsugorō | Narrow-sleeved work 筒袖, 前掛け apron, 手拭い, burn-scarred paw |
| Household | 小袖, 前掛け, 手拭い |

### 6.6 The SORA kamon in chapter 1

Every instance is built from the **two original paths** of `Content/SourceArt/UI/sora_logo_NOtext2.svg` (SHA-256 `d66413a7…0910`) and is never redrawn ([kamon rules](../sora-kamon-runtime-art.md)). Relief, openwork and dyed versions are derived from those paths. No alien object shows the mon.

| Surface | Treatment | Beat | Asset status |
|---|---|---|---|
| Dojo roof end tiles (軒丸瓦) | Raised ceramic | b01, b04 | Existing study: `Content/SourceArt/Environment/NyaagyuSoraEaveCapStudy/` |
| 幕 behind the master's seat | Indigo dye on undyed hemp (染め抜き) | b01–b03 | Needed |
| 名札掛け header | Carved and ink-filled | b01 | Needed |
| Title card | Vermillion 朱印 seal beside brush calligraphy | b01 | Needed (SVG exists) |
| Kurimaru's abumi front plates and crupper fittings | Lacquer or inlay, placed as on Met 2008.120 | b06 | Existing stylized source: `Content/SourceArt/Horses/Nyaagyu/` (review pending) |
| Yumi grip marker | Inlay | b07 | Existing study: `Content/SourceArt/Weapons/NyaagyuYumi/` |
| Charcoal drawing with hit tallies (`ch01.c06`) | Charcoal on board | b07 | Needed |
| Boundary stone (`ch01.c02`) | Weathered relief | b08 | Needed |
| Founder's tsuba (`ch01.c04`) | Iron openwork | b09 | Needed |
| UI | Objective marker, rotating save mon, registry page seal | all | Needed (L4) |

---

## 7. Art and audio assets

Status was checked against `Content/SourceArt`, `Content/Generated`, `Content/ArtReview` and `catalog.json` on 2026-09-25.

- **Existing** means a source or imported asset is in the repo.
- **Existing study** means it is source-only or has not passed the photoreal gate.
- **Needed** means nothing usable exists yet.

Every asset still has to pass the [photoreal acceptance](../art-direction/photoreal-acceptance.md) gates before it enters the campaign: an A/B comparison, a recorded license and a measured frame cost.

### 7.1 Environment kits and props

| Asset | Used in | Status | Source or notes |
|---|---|---|---|
| Estate dojo hall exterior (424 parts, 4 Lumen modules) | b01 exterior, Arena 0 halls | Existing | `Content/SourceArt/Environment/NyaagyuDojo/SM_Nyaagyu_EstateDojo.fbx`, `…/LumenModules/`; `/Game/Generated/Environment/Props/SM_Nyaagyu_EstateDojo` |
| **Hero dojo interior**: 6 × 5 ken hinoki floor, 羽目板, 連子窓, kamiza, 神棚, 刀掛け, 名札掛け with about 20 plaques, SORA 幕, 舞良戸, wraparound engawa | b01–b05 | Needed | Extend the dojo kit. The existing hall is 7.3 × 7.9 m, too small for the lesson floor |
| SORA 軒丸瓦 end tile | Roofs | Existing study | `Content/SourceArt/Environment/NyaagyuSoraEaveCapStudy/` |
| Kawara roof bay | Roofs | Existing study | `Content/SourceArt/Environment/NyaagyuKawaraBay/` |
| Shōji paper | Dojo, hall | Existing study; fails the fiber-repetition gate | `Content/SourceArt/Environment/ShojiPaperArtReview/` |
| Estate wall, kura, kura front, roji, stone path, mesh terrain, leaf silt, cargo stacks | Arena 0 | Existing | `NyaagyuEstateWall/`, `NyaagyuKura/`, `NyaagyuKuraFront/`, `NyaagyuIntegratedRoji/`, `NyaagyuHeroPath/`, `NyaagyuTerrain/`, `NyaagyuGroundDressing/`, `NyaagyuCargoStack/` under `Content/SourceArt/Environment/` |
| Broadleaf tree, pine saplings, fern, small tree, CC0 PBR palette and overcast HDRI | Arena 0, wood, lane | Existing | `/Game/Generated/Environment/Foliage/SM_NyaagyuTree_HI`; `Content/SourceArt/Environment/PolyHaven/` (Fern02, PineSaplingSmall, TreeSmall02, brown_mud_leaves_01, stone_floor, wood_planks_dirt, WhitePlaster02, GreyRoofTiles, kloofendal_overcast_puresky; CC0, NOTICE.txt) |
| Gate frames (torii mesh, re-dressed as 冠木門) and lacquer | Arena 0, b13 | Existing | `Content/SourceArt/Environment/Original/SM_Nyaagyu_ToriiGate.fbx`, `ToriiLacquer/`, `NyaagyuToriiFootStudy/` |
| Edo lantern post | Arena 0, b13 | Existing | `Content/SourceArt/Environment/Original/SM_Edo_LanternPost.fbx` |
| Photoreal 杉 and 檜 (hinoki cypress) trees, three growth stages; moss carpet; forest-floor litter | Wood, lane | Needed | Free CC0 or scan sources only if their licenses allow it |
| Stable (厩): building, stalls, tie rail, 鞍掛け stand, 飼葉桶, straw, 馬沓 on nails | b05–b06 | Needed | |
| Lane kit: packed-earth lane, dry-stone retaining walls, tea hedges, bamboo fence, 道祖神 roadside stone | b06 | Needed | Leaf silt dressing exists |
| Range kit: 射場 shed, 弓立て, 矢立て, 安土 mound and roof, 的台 stand, 尺二 paper target, 吊り的 frames and straw targets, 看的所 hut, earth berms | b07 | Needed | |
| Wood set pieces: split boulder with 注連縄 and 紙垂, offerings, hokora, carved 境石, 鳴子 clapper, stream bed, vista rock shelf | b08 | Needed | Photogrammetry-grade granite |
| Smithy kit: shed, 火床, 箱鞴, anvil, quench tub, tongs rack, 火鉢, 矯め木, 膠鍋, fletching bench, feather boxes, two village matchlocks, loft shelf | b09 | Needed | |
| Yard set: well with 釣瓶, zelkova, wisteria trellis | b04–b05 | Needed | |
| 半鐘 bell and timber frame; ring rope; 行灯 lanterns | b11–b13 | Needed | |
| Distant Nekoyama castle town and castle hill (matte or far mesh) | b08 vista, b13 | Needed | Reused in ch02 |

### 7.2 Characters and horses

| Asset | Status | Source or notes |
|---|---|---|
| Nyaakoto (hero sculpt, runtime skin, first-person paws, bokutō grip study) | Existing study | `Content/SourceArt/Characters/Hero/` (`SM_Nyaagyu_HeroCharacter`, runtime skin, LOD, PBR), `Content/SourceArt/SK_NyaagyuSamurai.fbx`, `Characters/NyaakotoFirstPersonPaws/`, `Characters/NyaakotoBokutoViewmodel/`, head and anatomy studies |
| Nyaakoto ch01 practice outfit (小袖, 袴, 襷) | Needed | Armour is the ch02 look |
| Sekireisai, Toranosuke, Matsukichi, Takemaru, Baiō, Tetsugorō, household ×2 (male, female) | Needed | Fur cards on crowd LODs; strand grooms for cinematics where supported |
| Horse and tack (stylized static source, walk rig study, abumi/tazuna texture study) | Existing study | `Content/SourceArt/Horses/Nyaagyu/SM_Nyaagyu_HorseAndTack.fbx`, `…/RigStudy/SK_Nyaagyu_Horse_RigStudy.fbx`, `Content/SourceArt/Horses/NyaagyuAbumiTazunaStudy/` (untracked in git at time of writing) |
| Kurimaru (chestnut mare), Arashi (black-bay stallion), pack horse: coats, manes, a functional rig, and tack in "on stand" and "on horse" states | Needed | The existing coat is a seal-brown art-review material |
| Pheasant, crows (flight cards), frogs (audio only) | Needed | |

### 7.3 Weapons and hand props

| Asset | Status | Source or notes |
|---|---|---|
| Bokutō | Existing | `/Game/Generated/Meshes/SM_Nyaagyu_DojoBokken`; `Content/SourceArt/Weapons/DojoBokkenPBR/`, `DojoBokutoForm/` |
| Fukuro-shinai (undyed leather over split bamboo) | Needed | A presentation variant of weapon 0 |
| Katana and saya | Existing | `Content/SourceArt/SM_Nyaagyu_HeroKatana.fbx`, `SM_Nyaagyu_HeroSaya.fbx`, `Weapons/HeroKatana/PBR/` |
| Yumi | Existing study | `Content/SourceArt/Weapons/NyaagyuYumi/SM_Nyaagyu_Yumi_Study.fbx` (source only, not bound; needs a draw rig), `…/HistoricalStudy/` (untracked) |
| Ya with red fletching; ebira quiver | Existing study | Static pose on the hero art review (`M_Hero_RedArrowFletch`, `M_Hero_BambooArrowShaft`). Functional arrow, bent-shaft variant and quiver meshes needed |
| 弽 glove | Needed | |
| Ear of barley, oath-roll box, founder's tsuba, day-book, plaque | Needed | Collectible props |

### 7.4 Animations (all needed)

The only animation sources in the repo are prototype walks (`A_NyaagyuSamurai_Walk.fbx`, `A_AlienBanker_Walk.fbx`) and the horse walk study frames.

- **Sword (first and third person).** 素振り; seigan idle; すり足 footwork (forward, back, side); guard raise and hold; awase; the 1.2 s stagger; cut and recovery; the 120 cm marobashi flank roll; pupil 面 and 袈裟 attacks; Toranosuke's set (men, kote, kesa, feint, nidan, seme); point reset and 立礼; yield; 座礼; kneeling watchers. Practitioner review is required before motion capture (bible §3.1).
- **Katana.** Two-handed receiving of a sword; 抜刀; 納刀 (explicit, needed for ch06).
- **Archery.** 弓構え, 打起し, 引分け, 会 hold with sway, 離れ, 弓返り, 残心; nocking on the right of the bow; the target keeper's calls and 矢取り.
- **Horse.** Saddle placement, girth and retightening, stirrups, bit refusal ×2, barley eating, bit acceptance, mounting from the right and dismounting, walk, trot, the pheasant spook, the stallion's sleeve reach (Arashi, idle).
- **Smithy.** Box bellows pumping, warming a shaft, bending in the 矯め木, gluing, binding, counting.
- **Ambient.** Baiō asleep, with an ear twitch; pupils bowing around him; lantern lighting; bell striking.
- **Faces.** Blinks, ear and whisker idles, and lip-sync for all voiced lines.

### 7.5 VFX (all needed except where noted)

- **Light and air.** Dust motes in light shafts. Valley and hollow mist volumes. God rays in the wood.
- **Smithy.** Charcoal glow, sparks, heat shimmer over the brazier, the gleam on a ready shaft, a scorch tint.
- **Archery.** A subtle arrow trail on Easy only; a straw puff on hit; a paper tear on the 尺二 target; a sand puff at the 安土.
- **Duel.** Fukuro-shinai impact as dust and cloth ripple, never blood. A dust ring on ring-out.
- **Telegraphs.**
  - The 水月 maai ring: a faint moon-on-water ripple.
  - Amber telegraph edges. An existing prototype is the pupil's golden warning; this chapter needs the solid, hollow, diagonal and double variants, plus the accessible palette.
  - A flank highlight after marobashi.
- **The sky split.** A tearing seam, cold volumetric shafts, and descending lights with the flash-reduction option.

### 7.6 Sound effects (all needed; the repo has no audio yet)

- **Sword.** Bokutō clacks (white oak), fukuro-shinai slaps, すり足 on hinoki and on packed earth, VO efforts (kiai, grunts).
- **Crowd.** Counted 掛け声 for the dawn practice (crowd VO).
- **Archery.** Bowstring release (弦音), arrow flight, hits on paper, straw and sand, the 弓返り creak, the 鳴子 clack and its echo.
- **Horse.** Hooves at walk and trot on earth, snorts, chewing barley, tack creak and bit jingle, the stable ambience.
- **Nature.** Pheasant call and flush, uguisu, crows, stream, cedar creak, breeze.
- **Smithy.** Bellows, charcoal hiss, bending bamboo, glue pot, thread binding, hammer ring (for the exit hint).
- **Estate.** 半鐘 strokes. The sky seam's low tear and cold glassy harmonics, which are the first appearance of the alien sound palette.

### 7.7 Music states (L5; all needed)

| State | Beats | Direction |
|---|---|---|
| `ch01_dawn` | b01 | Solo shakuhachi over the natural ambience; restrained |
| `ch01_keiko` | b02–b04 | Light 拍子木 and hand drum, pulsing with the lesson; drops out during gates |
| `ch01_veranda` | b05, b10 | Koto and flute, warm, sparse |
| `ch01_ride` | b06 | 篠笛 over a gentle percussion gait that follows walk and trot |
| `ch01_matoba` | b07 | Near-silence; wind and bowstring, with a low drone at full draw |
| `ch01_wood` | b08 | Drones and a small bell motif near the stone |
| `ch01_smithy` | b09 | Percussion locked to the step rhythm |
| `ch01_duel_rival` | b11 | Taiko pulse that tightens with the score state; stops dead on each point |
| `ch01_katana` | b12 | Shakuhachi and koto, the chapter's theme resolved |
| `ch01_sky_splits` | b13 | Cold dissonant cluster, first statement of the alien "ledger" motif, cut against the 半鐘 |

### 7.8 UI (L4)

- **Title card.** Brush calligraphy for 「第一章 道場の修行」. This needs a font licensed for the purpose or hand-made calligraphy art. The existing `Content/SourceArt/Fonts/NotoSansCJKjp-Regular.otf` (SIL OFL) covers body text only.
- **Existing SORA art.** `Content/SourceArt/UI/sora_logo_NOtext2.svg`, `SORA_Resistance_Logo.png`, `Nyaagyu_Title_KeyArt.png`, and `/Game/Generated/UI/T_SoraResistanceLogo`, `T_NyaagyuTitle`.
- **Needed screens and widgets.** The maai ring widget, input-glyph prompts, unlock notices (weapons 18 and 0), the registry page for 矢 12本, the chapter-complete screen, a gait indicator (常歩 / 速歩), and the ring-out warning.

---

## 8. Hand-offs, deviations and open items

**Deviations from the bible.** The C1 review accepted items 1–5 and 7 and wrote them into the bible (§6.2, §6.4.1, §10, §11, §12.1, §12.3, §13). Items 6 and 8 stand as written.

1. **b03 has two opponents.** The bible's b03 is against Matsukichi alone. Here Takemaru rotates in for the second scored bout, so that catalog site 1's `requires_kills: 2` and its restored text ("sparred with two pupils") both hold.
2. **Tetsugorō first appears in ch01** as the estate's smith (b09). This seeds his ch04 coil breech. The ch04 and ch05 scripts should treat him as already known.
3. **Baiō is written as elderly** (`elder_samurai`), following the 翁 in his name. The bible gives all the pupils young samurai speech. He also appears as the range instructor, which gives the sleeping pupil some dignity. He rings the bell in b13.
4. **`manufacture` unlocks in ch01.b09**, per bible §10. The ch05.b08 outline's "unlocks `manufacture` rhythm" should use no flag or a new one such as `hammer_rhythm`, so that no flag unlocks twice.
5. **Weapon order.** Chronologically ch01 unlocks 18 (b07) before 0 (b12), but the §11 table lists 0 first. L1's validation rule 3 should compare unlock order by beat, not table row.
6. **Training blades.** During b02–b11 the bokutō and fukuro-shinai are presentation variants of weapon 0. The duel beat equips them even though weapon 0 is not in the unlock mask until b12.
7. **Script length.** 117 voiced lines against the bible's estimate of 90 (§10). The extra lines are hints and branch lines; a single run hears about 100.
8. **The lane has no bible place id.** It is route `spl_ch01_umaba_lane` under `pl_umaya`.

**Owner hand-offs:**

| Owner | Takes |
|---|---|
| L1 | §4 beats, §9 YAML, §4.6 events and `x_` fields, the new speaker ids, the collectible mask bits, the `ch01_duel_result` save flag, and the mentor display name |
| L2 | Pupil patterns, Toranosuke's `tora_fukuro` table and score states, marobashi timings, archery tuning (colliders, sway, gravity) |
| L4 | 22 prompts, maai ring widget, unlock notices, registry page, title card seal, gait indicator |
| L5 | 10 music states; judge and target keeper barks as captioned audio |
| C2 and C3 | §3 sublevels (dojo interior, stable, lane, range, wood, smithy) and the Arena 0 campaign actors |
| C4 | The ch01 mission from §4 |
| C9 | `LS_Ch01_B01_DawnSuburi`, `LS_Ch01_B13_SkySplits`, and b12's hand-over camera |

**Open reviews:**

1. Native Japanese review of every line, reading and register (B7), especially Baiō's 〜なされ and the household's Yamato speech.
2. Historian review of the §6 flags: 一本 scoring in 1623, the name board, the standalone dojo hall, the shooting-stage names, the saddle-pad names, and the 半鐘 placement.
3. Practitioner review of every sword motion before motion capture.
4. Equine animator review of the trot (側対歩), the right-side mount and the bit refusal.
5. Playtest telemetry for the 40 min target: the target on b07 (60–70% hit rate on Normal) and b11 (about 6 min including retries) are the two most uncertain numbers.

---

## 9. Machine-readable data (YAML)

This block is generated from the same source as the tables above and was checked by parsing it back.

- Top-level keys: `chapter`, `places`, `layout`, `music_states`, `patterns`, `beats`, `collectibles`, `lines` and `ui_prompts`.
- `dialogue` beats carry their own `lines` inline, as §12.2 requires. `lines` holds every other voiced line.
- `audio: null` means not yet recorded.
- `on` is quoted, so that YAML 1.1 parsers do not read it as a boolean.

```yaml
chapter: ch01_dojo
schema_note: "Proposal for catalog schema 4 (story bible §12). Keys prefixed x_ are chapter proposals outside the §12 contract."
title_ja: "道場の修行"
title_en: "Dojo Apprenticeship"
target_s: 2400
map: 0
season: "Genna 9 (1623), late spring; dawn to dusk; overcast morning clearing to a golden evening"
category_minutes: {C: 22, E: 4, S: 0, P: 3, M: 3, Cin: 8}
speakers_new:
  - {id: rival, ja: "鷲尾 虎之介", en: "Washio Toranosuke", status: "bible §6.1"}
  - {id: gunsmith, ja: "鉄砲鍛冶 鉄五郎", en: "Tetsugorō the gunsmith", status: "bible §6.2"}
  - {id: pupil_matsukichi, ja: "門弟 松吉", en: Matsukichi, status: "new (bible lists as minor)"}
  - {id: pupil_takemaru, ja: "門弟 竹丸", en: Takemaru, status: "new (bible lists as minor)"}
  - {id: pupil_baio, ja: "門弟 梅翁", en: "Baiō", status: "new (bible lists as minor)"}
  - {id: household, ja: "屋敷の者", en: Household, status: "new generic; two voice variants"}
places:
  - id: pl_tsumagizaka_dojo
    ja: "爪木坂道場"
    en: "Tsumagizaka Dojo"
    source: "estate sublevel SL_Ch01_Tsumagizaka (new hero interior; existing SM_Nyaagyu_EstateDojo is the exterior reference)"
    origin_m: [0.0, 61.6, 6.0]
    size_m: [16.0, 23.5]
  - id: pl_umaya
    ja: "厩"
    en: Stable
    source: "estate sublevel SL_Ch01_Tsumagizaka"
    origin_m: [25.0, 60.0, 6.0]
    size_m: [12.7, 5.5]
  - id: pl_matoba
    ja: "的場・安土"
    en: "Archery range"
    source: "new sublevel SL_Ch01_Matoba"
    origin_m: [-176.0, 50.0, 8.0]
    size_m: [24.0, 70.0]
  - id: pl_issoseki_wood
    ja: "一爪石の森"
    en: "One-Claw Stone Wood"
    source: "new sublevel SL_Ch01_IssosekiWood"
    origin_m: [-95.0, 67.5, 9.0]
    size_m: [110.0, 85.0]
  - id: pl_dojo_smithy
    ja: "道場の鍛冶場"
    en: "Dojo smithy"
    source: "estate sublevel SL_Ch01_Tsumagizaka"
    origin_m: [-28.0, 52.0, 6.0]
    size_m: [6.4, 5.5]
  - id: pl_estate_day
    ja: "猫柳生の屋敷・昼"
    en: "Nyaagyu Estate, day"
    source: "Arena 0 (collision unchanged); campaign actors only"
    origin_m: [0.0, 0.0, 0.0]
    size_m: [64.0, 52.0]
layout:
  frame: "metres; origin = Arena 0 centre; +X east, +Y north, Z up (courtyard grade = 0); yaw 0 = +X, 90 = +Y"
  volumes:
    - {id: vol_ch01_dojo_floor, place: pl_tsumagizaka_dojo, center: [0.0, 60.75, 8.1], size: [10.9, 7.3, 3.0], use: "b02-b03 lesson ring (hinoki training floor)"}
    - {id: vol_ch01_dojo_yard, place: pl_tsumagizaka_dojo, center: [0.0, 49.9, 7.5], size: [16.0, 12.0, 3.0], use: "b04 marobashi ring; flood line"}
    - {id: vol_ch01_engawa_sunbeam, place: pl_tsumagizaka_dojo, center: [4.6, 56.5, 7.6], size: [2.0, 1.2, 2.0], use: "b05 Baiō asleep; optional bow prompt"}
    - {id: vol_ch01_engawa_east, place: pl_tsumagizaka_dojo, center: [7.5, 56.0, 7.0], size: [4.0, 5.0, 2.5], use: "b05 Toranosuke exchange"}
    - {id: vol_ch01_engawa_mentor, place: pl_tsumagizaka_dojo, center: [-3.0, 56.5, 7.6], size: [4.0, 2.4, 2.0], use: "b05 objective from Sekireisai"}
    - {id: vol_ch01_umaya, place: pl_umaya, center: [25.0, 58.0, 7.5], size: [14.0, 9.0, 3.0], use: "completes b05; starts b06"}
    - {id: vol_ch01_lane_trot, place: pl_umaya, spline: spl_ch01_umaba_lane, from_m: 70, to_m: 240, width: 6.0, use: "b06 trot prompt zone"}
    - {id: vol_ch01_lane_pheasant, place: pl_umaya, spline: spl_ch01_umaba_lane, from_m: 146, to_m: 154, width: 6.0, use: "b06 scripted spook"}
    - {id: vol_ch01_matoba_hitch, place: pl_matoba, center: [-163.0, 22.0, 9.0], size: [6.0, 6.0, 3.0], use: "b06 complete (dismount at the hitching post)"}
    - {id: vol_ch01_matoba, place: pl_matoba, center: [-176.0, 50.0, 10.0], size: [24.0, 70.0, 8.0], use: "b07 bounds; arrow corridor"}
    - {id: vol_ch01_shajo_line, place: pl_matoba, center: [-178.0, 19.5, 9.0], size: [12.0, 1.5, 3.0], use: "b07 shooting line (bow draws only here)"}
    - {id: vol_ch01_wood, place: pl_issoseki_wood, center: [-95.0, 67.5, 12.0], size: [110.0, 85.0, 20.0], use: "b08 bounds"}
    - {id: vol_ch01_wood_exit, place: pl_issoseki_wood, center: [-36.0, 54.5, 7.5], size: [4.0, 4.0, 3.0], use: "b08 complete; smithy back gate"}
    - {id: vol_ch01_smithy, place: pl_dojo_smithy, center: [-28.0, 52.0, 7.5], size: [9.0, 8.0, 3.0], use: "b09 start (also reachable by the terrace path)"}
    - {id: vol_ch01_ura_mon, place: pl_estate_day, center: [4.5, 27.5, 1.5], size: [3.0, 2.0, 3.0], use: "fade into Arena 0; outside the north wall, no collision change"}
    - {id: vol_ch01_estate_north_gate, place: pl_estate_day, center: [4.8, 22.5, 1.5], size: [3.0, 3.0, 3.0], use: "b10 household chatter"}
    - {id: vol_ch01_estate_engawa, place: pl_estate_day, center: [0.0, 12.5, 1.5], radius: 4.0, use: "b10 and b12 veranda talk; katana hand-over"}
    - {id: vol_ch01_duel_ring, place: pl_estate_day, center: [0.0, 0.0, 1.5], radius: 5.0, height: 3.0, use: "b11 ring; leaving it resets the exchange"}
  points:
    - {id: ps_ch01_lesson_mark, pos: [0.0, 58.6, 6.6], yaw_deg: 90}
    - {id: ps_ch01_mentor_mark, pos: [0.0, 61.6, 6.6], yaw_deg: 270}
    - {id: ps_ch01_yard_mark, pos: [0.0, 48.0, 6.0], yaw_deg: 90}
    - {id: ps_ch01_tie_rail, pos: [21.8, 56.5, 6.0], yaw_deg: 270}
    - {id: ps_ch01_shajo_kinteki, pos: [-174.0, 20.0, 8.0], yaw_deg: 90}
    - {id: ps_ch01_shajo_enteki, pos: [-182.0, 20.0, 8.0], yaw_deg: 90}
    - {id: sp_ch01_kinteki_a, pos: [-174.0, 48.0, 8.4]}
    - {id: sp_ch01_tsuri_frames, pos: [[-182.0, 60.0, 9.5], [-182.0, 70.0, 9.5], [-182.0, 80.0, 9.5]]}
    - {id: ps_ch01_kanteki_hut, pos: [-167.0, 50.0, 8.0], yaw_deg: 180}
    - {id: st_ch01_fuigo, pos: [-29.8, 52.4, 6.0]}
    - {id: st_ch01_hibachi, pos: [-26.0, 50.6, 6.0]}
    - {id: st_ch01_tamegi, pos: [-25.4, 51.4, 6.0]}
    - {id: st_ch01_hagi_dai, pos: [-26.8, 49.9, 6.0]}
    - {id: ip_ch01_katana, pos: [0.0, 14.0, 0.6]}
    - {id: ps_ch01_estate_entry, pos: [4.8, 23.6, 0.0], yaw_deg: 270}
    - {id: ps_ch01_duel_player, pos: [0.0, 2.0, 0.0], yaw_deg: 270}
    - {id: ps_ch01_duel_rival, pos: [0.0, -2.0, 0.0], yaw_deg: 90}
    - {id: ps_ch01_judge, pos: [-5.8, 0.0, 0.0], yaw_deg: 0}
    - {id: ps_ch01_b13_end, pos: [0.0, 6.0, 0.0], yaw_deg: 180}
  splines:
    - id: spl_ch01_umaba_lane
      length_m: 300
      nodes:
        - [21.8, 55.0, 6.0]
        - [34.0, 72.0, 9.0]
        - [22.0, 102.0, 14.0]
        - [-60.0, 118.0, 13.0]
        - [-150.0, 96.0, 10.0]
        - [-158.0, 40.0, 8.0]
        - [-163.0, 22.0, 8.0]
    - id: spl_ch01_wood_trail
      length_m: 170
      nodes:
        - [-152.0, 30.0, 8.0]
        - [-130.0, 55.0, 9.0]
        - [-105.0, 80.0, 8.5]
        - [-80.0, 70.0, 8.0]
        - [-58.0, 58.0, 7.0]
        - [-36.0, 54.5, 6.0]
    - id: spl_ch01_rival_exit
      length_m: 30
      nodes: [[2.0, -3.0, 0.0], [12.0, -2.0, 0.0], [23.0, 0.0, 0.0]]
music_states:
  - {id: ch01_dawn, beats: [ch01.b01]}
  - {id: ch01_keiko, beats: [ch01.b02, ch01.b03, ch01.b04]}
  - {id: ch01_veranda, beats: [ch01.b05, ch01.b10]}
  - {id: ch01_ride, beats: [ch01.b06]}
  - {id: ch01_matoba, beats: [ch01.b07]}
  - {id: ch01_wood, beats: [ch01.b08]}
  - {id: ch01_smithy, beats: [ch01.b09]}
  - {id: ch01_duel_rival, beats: [ch01.b11]}
  - {id: ch01_katana, beats: [ch01.b12]}
  - {id: ch01_sky_splits, beats: [ch01.b13]}
patterns:
  - id: tora_fukuro
    owner: "L2 (duel opponent; not a bosses.json boss)"
    difficulty_windup_scale: {easy: 1.3, normal: 1.0, hard: 0.85}
    attacks:
      - id: tora_men
        ja: "面打ち"
        windup_ms: 500
        recovery_ms: 900
        telegraph: amber_solid
        guard: true
        awase: true
        marobashi_after_awase: false
      - id: tora_kote
        ja: "小手打ち"
        windup_ms: 380
        recovery_ms: 700
        telegraph: amber_solid
        guard: true
        awase: true
        marobashi_after_awase: false
      - id: tora_kesa
        ja: "袈裟"
        windup_ms: 600
        recovery_ms: 1000
        telegraph: amber_diagonal
        guard: true
        awase: true
        marobashi_after_awase: true
      - id: tora_feint
        ja: "誘い（面から小手）"
        windup_ms: 630
        fake_phase_ms: 250
        recovery_ms: 700
        telegraph: amber_hollow_then_solid
        tell: "rear foot does not drive during the fake"
        guard: true
        awase: "on the real kote only"
        marobashi_after_awase: false
      - id: tora_nidan
        ja: "二段（小手から面）"
        windup_ms: 380
        second_gap_ms: 450
        recovery_ms: 1100
        telegraph: amber_solid_x2
        guard: true
        awase: "either cut"
        marobashi_after_awase: true
      - id: tora_seme
        ja: "攻め（押し込み）"
        windup_ms: 0
        duration_ms: 1200
        recovery_ms: 0
        telegraph: none
        effect: "steps in 120 cm to crowd the player toward the ring edge"
beats:
  - id: ch01.b01
    type: cinematic
    place: pl_tsumagizaka_dojo
    title_ja: "夜明けの素振り"
    title_en: "Dawn practice"
    target_s: 120
    checkpoint: true
    requires: []
    music: ch01_dawn
    fail: {"on": none, to: none}
    sequence: "/Game/Campaign/Ch01/Sequences/LS_Ch01_B01_DawnSuburi"
    duration_s: 120
    skippable: true
    fallback: camera_blend
    subtitles:
      - {line: ch01.b01.sekireisai.001, t_s: 60.0}
      - {line: ch01.b01.sekireisai.002, t_s: 61.6}
      - {line: ch01.b01.nyaakoto.003, t_s: 65.9}
      - {line: ch01.b01.sekireisai.004, t_s: 68.8}
    end_state: {player_transform: ps_ch01_lesson_mark, equipped: bokuto}
    x_title_card:
      ja: "第一章 道場の修行"
      en: "Chapter 1: Dojo Apprenticeship"
      seal: sora_mon_shuin
      in_s: 96
      out_s: 110
  - id: ch01.b02
    type: duel
    place: pl_tsumagizaka_dojo
    title_ja: "正眼に構え、間合いを読め"
    title_en: "Take seigan and read the distance"
    target_s: 240
    checkpoint: true
    requires: [ch01.b01]
    site: 0
    unlocks: {weapons: [], mechanics: [kamae, maai_ring]}
    music: ch01_keiko
    fail: {"on": none, to: none}
    dialogue:
      - {"on": beat_start, lines: [ch01.b02.sekireisai.001, ch01.b02.sekireisai.002], mode: ambient}
      - {"on": "gate_complete:stance_hold", lines: [ch01.b02.sekireisai.003, ch01.b02.sekireisai.004, ch01.b02.nyaakoto.005, ch01.b02.sekireisai.006], mode: ambient}
      - {"on": maai_step_ok, lines: [ch01.b02.sekireisai.007], mode: ambient}
      - {"on": "gate_complete:maai_step", lines: [ch01.b02.sekireisai.008], mode: ambient}
      - {"on": "gate_retry:maai_step", lines: [ch01.b02.sekireisai.009], mode: ambient}
      - {"on": beat_complete, lines: [ch01.b02.sekireisai.010], mode: ambient}
    opponent: npc_sekireisai
    weapons: {player: bokuto, opponent: bokuto}
    lethal: false
    scoring: {mode: lesson_gates}
    ring: vol_ch01_dojo_floor
    lesson_gates: [{gate: stance_hold, ms: 600}, {gate: maai_step, count: 3}]
    finisher: none
    loss_policy: retry
    x_prompts: [ch01.b02.prompt.01, ch01.b02.prompt.02]
    x_maai:
      weapon_range_cm: 195
      ring_inner_cm: 166
      ring_outer_cm: 224
      hold_ms: 500
      facing_dot_min: 0.7
      hint_after_s: 6.0
      mentor_moves:
        - {step: 1, move: back, cm: 120}
        - {step: 2, move: left, cm: 150}
        - {step: 3, move: forward, cm: 80}
    x_dojo_rules: {lesson_bits: [0], actions: [Stance], scored_bouts: 0}
  - id: ch01.b03
    type: duel
    place: pl_tsumagizaka_dojo
    title_ja: "受けて、合わせよ"
    title_en: "Receive the cut, then meet it"
    target_s: 240
    checkpoint: true
    requires: [ch01.b02]
    site: 1
    unlocks: {weapons: [], mechanics: [awase]}
    music: ch01_keiko
    fail: {"on": none, to: none}
    dialogue:
      - {"on": beat_start, lines: [ch01.b03.sekireisai.001], mode: ambient}
      - {"on": "gate_complete:front_guard_survive", lines: [ch01.b03.sekireisai.002], mode: ambient}
      - {"on": "gate_start:awase", lines: [ch01.b03.sekireisai.003], mode: ambient}
      - {"on": "awase_success:1", lines: [ch01.b03.sekireisai.004], mode: ambient}
      - {"on": "awase_fail:early", lines: [ch01.b03.sekireisai.005], mode: ambient}
      - {"on": "awase_fail:late", lines: [ch01.b03.sekireisai.006], mode: ambient}
      - {"on": "gate_start:recovery_complete", lines: [ch01.b03.sekireisai.007], mode: ambient}
      - {"on": "gate_complete:recovery_complete", lines: [ch01.b03.sekireisai.008], mode: ambient}
      - {"on": "bout_scored:1", lines: [ch01.b03.matsukichi.009, ch01.b03.sekireisai.010], mode: ambient}
      - {"on": beat_complete, lines: [ch01.b03.sekireisai.011], mode: ambient}
    opponent: npc_matsukichi
    weapons: {player: bokuto, opponent: bokuto}
    lethal: false
    scoring: {mode: lesson_gates}
    ring: vol_ch01_dojo_floor
    lesson_gates:
      - {gate: front_guard_survive, after_ms: 350}
      - {gate: awase, window_ms: 260, count: 2}
      - {gate: recovery_complete}
    finisher: none
    loss_policy: retry
    x_prompts: [ch01.b03.prompt.01, ch01.b03.prompt.02, ch01.b03.prompt.03, ch01.b03.prompt.04]
    x_opponent_rotation: [{npc: npc_takemaru, "on": "bout_scored:1"}]
    x_opponent_pattern:
      id: pupil_men
      windup_ms: 550
      repeat_s: 1.45
      telegraph: amber_edge
      stagger_on_awase_s: 1.2
    x_scored_bouts:
      count: 2
      opponents: [npc_matsukichi, npc_takemaru]
      rule: "awase, then a cut that lands in the stagger after blade recovery"
      counts_toward: "catalog requires_kills"
    x_dojo_rules: {lesson_bits: [1, 2, 3], actions: [Guard, Parry, Recovery], scored_bouts_after: 2}
  - id: ch01.b04
    type: duel
    place: pl_tsumagizaka_dojo
    title_ja: "転（まろばし）"
    title_en: "Marobashi: roll with the flood"
    target_s: 180
    checkpoint: true
    requires: [ch01.b03]
    unlocks: {weapons: [], mechanics: [marobashi]}
    music: ch01_keiko
    fail: {"on": none, to: none}
    dialogue:
      - {"on": beat_start, lines: [ch01.b04.sekireisai.001], mode: ambient}
      - {"on": "volume_enter:vol_ch01_dojo_yard", lines: [ch01.b04.sekireisai.002], mode: ambient}
      - {"on": marobashi_miss, lines: [ch01.b04.sekireisai.003], mode: ambient}
      - {"on": "bout_scored:3", lines: [ch01.b04.matsukichi.004, ch01.b04.takemaru.005], mode: ambient}
      - {"on": beat_complete, lines: [ch01.b04.sekireisai.006], mode: ambient}
    opponent: npc_matsukichi
    weapons: {player: bokuto, opponent: bokuto}
    lethal: false
    scoring: {mode: lesson_gates}
    ring: vol_ch01_dojo_yard
    lesson_gates: [{gate: marobashi_flank, count: 2}]
    finisher: none
    loss_policy: retry
    x_prompts: [ch01.b04.prompt.01]
    x_opponent_rotation: [{npc: npc_takemaru, "on": "bout_scored:3"}]
    x_opponent_pattern: {id: pupil_kesa, windup_ms: 600, recovery_ms: 1000, telegraph: amber_edge_diagonal}
    x_marobashi:
      input_window_ms: 400
      lateral_step_cm: 120
      arc_deg: 70
      opponent_turn_lag_s: 0.8
      clearance_cm: 150
    x_scored_bouts:
      count: 2
      opponents: [npc_matsukichi, npc_takemaru]
      counts_toward: "catalog requires_kills"
      running_total: 4
  - id: ch01.b05
    type: dialogue
    place: pl_tsumagizaka_dojo
    title_ja: "縁側の陽だまり"
    title_en: "The sunbeam on the veranda"
    target_s: 90
    checkpoint: false
    requires: [ch01.b04]
    music: ch01_veranda
    fail: {"on": none, to: none}
    lines:
      - {id: ch01.b05.takemaru.001, speaker: pupil_takemaru, ja: "虎之介さまだ。また朝稽古に遅れて……。", en: "It is Lord Toranosuke. Late for morning practice again…", register: young_samurai, audio: null, duration_s: 3.9}
      - {id: ch01.b05.matsukichi.002, speaker: pupil_matsukichi, ja: "また大坂の使いと会っていたらしい。", en: "They say he met the man from Osaka again.", register: young_samurai, audio: null, duration_s: 3.7}
      - {id: ch01.b05.toranosuke.003, speaker: rival, ja: "先生の相手をしたそうだな。『刃を急がせるな』か。", en: "I hear you faced Sensei. 'Do not hurry your blade,' was it?", register: brash_samurai, audio: null, duration_s: 4.5}
      - {id: ch01.b05.toranosuke.004, speaker: rival, ja: "俺は急ぐ。急がねば、間に合わぬこともある。", en: "I hurry. Some things will not wait.", register: brash_samurai, audio: null, duration_s: 4.1}
      - {id: ch01.b05.nyaakoto.005, speaker: samurai, ja: "……何があった、虎之介。", en: "…What happened, Toranosuke?", register: jidaigeki_restrained, audio: null, duration_s: 2.5}
      - {id: ch01.b05.toranosuke.006, speaker: rival, ja: "何も。稽古の話だ。", en: "Nothing. This is about practice.", register: brash_samurai, audio: null, duration_s: 2.2}
      - {id: ch01.b05.sekireisai.007, speaker: mentor, ja: "厩へ行け。栗丸が退屈しておる。弓も引いてこい。", en: "Go to the stable. Kurimaru is bored. Then draw your bow.", register: archaic_samurai, audio: null, duration_s: 4.5}
    trigger: beat_start
    mode: ambient
    camera: soft_lookat
    interrupt: queue
    priority: 2
    dialogue:
      - {"on": beat_start, lines: [ch01.b05.takemaru.001, ch01.b05.matsukichi.002], mode: ambient}
      - {"on": "volume_enter:vol_ch01_engawa_east", lines: [ch01.b05.toranosuke.003, ch01.b05.toranosuke.004, ch01.b05.nyaakoto.005, ch01.b05.toranosuke.006], mode: ambient}
      - {"on": "volume_enter:vol_ch01_engawa_mentor", lines: [ch01.b05.sekireisai.007], mode: ambient}
    x_prompts: [ch01.b05.prompt.01]
    x_ambient_actions:
      - baio_asleep_in_sunbeam
      - pupils_bow_around_baio
      - toranosuke_dismounts_hands_arashi_to_takemaru
      - toranosuke_bows_around_baio
    x_complete: {volume_enter: vol_ch01_umaya}
  - id: ch01.b06
    type: horseback_ride
    place: pl_umaya
    title_ja: "栗丸に鞍を置き、的場へ"
    title_en: "Tack up Kurimaru and ride to the range"
    target_s: 180
    checkpoint: true
    requires: [ch01.b05]
    unlocks: {weapons: [], mechanics: [mount]}
    music: ch01_ride
    fail: {"on": none, to: none}
    dialogue:
      - {"on": beat_start, lines: [ch01.b06.takemaru.001], mode: ambient}
      - {"on": "interact:ip_ch01_kura", lines: [ch01.b06.takemaru.002], mode: ambient}
      - {"on": "interact:ip_ch01_haruobi", lines: [ch01.b06.takemaru.003], mode: ambient}
      - {"on": "interact:ip_ch01_abumi", lines: [ch01.b06.takemaru.004], mode: ambient}
      - {"on": "interact_refused:ip_ch01_kutsuwa:1", lines: [ch01.b06.nyaakoto.005], mode: ambient}
      - {"on": "interact_refused:ip_ch01_kutsuwa:2", lines: [ch01.b06.takemaru.006], mode: ambient}
      - {"on": "item_given:barley_ear", lines: [ch01.b06.takemaru.007], mode: ambient}
      - {"on": "interact:ip_ch01_kutsuwa", lines: [ch01.b06.takemaru.008], mode: ambient}
      - {"on": mount, lines: [ch01.b06.takemaru.009], mode: ambient}
      - {"on": "volume_enter:vol_ch01_lane_pheasant", lines: [ch01.b06.nyaakoto.010], mode: ambient}
    horse: kurimaru
    mode: travel
    route: spl_ch01_umaba_lane
    complete: {reach: vol_ch01_matoba_hitch, dismount: true}
    gaits: [walk, trot]
    weapons: []
    fear: {spook_radius_cm: 600, recover_s: 1.5}
    auto_steer: setting
    dismount_allowed: true
    on_horse_down: checkpoint
    x_prompts:
      - ch01.b06.prompt.01
      - ch01.b06.prompt.02
      - ch01.b06.prompt.03
      - ch01.b06.prompt.04
      - ch01.b06.prompt.05
    x_tack_up:
      order: fixed
      interact_points:
        - {id: ip_ch01_kura, part: kura, action: "set saddle over the under-pad", hold_s: 1.5}
        - {id: ip_ch01_haruobi, part: haruobi, action: "tighten girth twice (she bloats)", hold_s: 1.0}
        - {id: ip_ch01_abumi, part: abumi, action: "hang both stirrups on the chikaragawa", hold_s: 1.0}
        - id: ip_ch01_kutsuwa
          part: kutsuwa
          action: "bit and omogai; refused twice until barley"
          hold_s: 1.0
          refusals: 2
          unlock_item: barley_ear
      mount_side: right
      mount_point: ps_ch01_tie_rail
    x_gait_zones:
      - {from_m: 0, to_m: 70, gait: walk}
      - {from_m: 70, to_m: 240, gait: trot, volume: vol_ch01_lane_trot}
      - {from_m: 240, to_m: 300, gait: walk}
    x_speeds_cm_s: {walk: 160, trot: 360}
    x_scripted_spook: {volume: vol_ch01_lane_pheasant, at_m: 150, cause: pheasant_flush}
  - id: ch01.b07
    type: combat_wave
    place: pl_matoba
    title_ja: "的場で弓を引け"
    title_en: "Draw the bow at the range"
    target_s: 300
    checkpoint: true
    requires: [ch01.b06]
    unlocks: {weapons: [18], mechanics: [yumi]}
    music: ch01_matoba
    fail: {"on": none, to: none}
    dialogue:
      - {"on": beat_start, lines: [ch01.b07.baio.001], mode: ambient}
      - {"on": "equip:18", lines: [ch01.b07.baio.002], mode: ambient}
      - {"on": "draw_complete:first", lines: [ch01.b07.baio.003], mode: ambient}
      - {"on": "release:first", lines: [ch01.b07.baio.004], mode: ambient}
      - {"on": mato_hit, lines: [ch01.b07.matsukichi.005], mode: ambient}
      - {"on": mato_miss, lines: [ch01.b07.matsukichi.006], mode: ambient}
      - {"on": set_failed, lines: [ch01.b07.baio.007], mode: ambient}
      - {"on": "wave_start:2", lines: [ch01.b07.baio.008], mode: ambient}
      - {"on": beat_complete, lines: [ch01.b07.baio.009, ch01.b07.matsukichi.010], mode: ambient}
    bounds: vol_ch01_matoba
    target_kind: mato
    max_alive: 3
    waves:
      - {enemies: [{type: mato_kinteki, count: 1, spawn: sp_ch01_kinteki_a}], trigger: start}
      - {enemies: [{type: mato_tsuri, count: 3, spawn: sp_ch01_tsuri_frames}], trigger: prev_cleared}
    complete: all_waves_cleared
    allies:
      - {npc: npc_baio, role: instructor, downable: false}
      - {npc: npc_matsukichi, role: kanteki_target_keeper, downable: false}
    x_prompts: [ch01.b07.prompt.01, ch01.b07.prompt.02]
    x_unlock_at: beat_start
    x_mato_rules:
      distance_m: 28
      target_cm: 36
      shots_per_set: 6
      hits_required: 4
      hit_collider_radius_cm: {easy: 25, normal: 21, hard: 18}
      between_sets: yatori_arrow_fetch_8s
      ammo: own_quiver_12
    x_tsuri:
      distances_m: [40, 50, 60]
      hits_each: 1
      swing_amplitude_cm: 150
      period_s: 3.2
      target_cm: 45
    x_shaho:
      draw_ms: 650
      hold_sway_after_s: 4.0
      no_fire_while_sprinting: true
      arrow_rest: right_of_bow
      yugaeri_anim: true
    x_quiver_after: {usable: 6, bent: 6, reason: "stone in the azuchi"}
  - id: ch01.b08
    type: explore_optional
    place: pl_issoseki_wood
    title_ja: "一爪石の森"
    title_en: "The One-Claw Stone Wood"
    target_s: 240
    checkpoint: true
    requires: [ch01.b07]
    optional: true
    music: ch01_wood
    fail: {"on": none, to: none}
    dialogue:
      - {"on": "interact:poi_ch01_issoseki", lines: [ch01.b08.nyaakoto.001, ch01.b08.nyaakoto.002], mode: ambient}
      - {"on": "interact:poi_ch01_vista", lines: [ch01.b08.nyaakoto.003], mode: ambient}
      - {"on": "interact:poi_ch01_sakaiishi", lines: [ch01.b08.nyaakoto.004], mode: ambient}
      - {"on": "idle_s:180", lines: [ch01.b08.nyaakoto.005], mode: ambient}
    volume: vol_ch01_wood
    pois:
      - {id: poi_ch01_issoseki, kind: lore}
      - {id: poi_ch01_vista, kind: vista}
      - {id: poi_ch01_sakaiishi, kind: lore}
      - {id: poi_ch01_hokora, kind: lore}
      - {id: poi_ch01_naruko, kind: challenge}
    rewards: [ch01.c01, ch01.c02]
    exit_hint_after_s: 180
    x_complete: {volume_enter: vol_ch01_wood_exit}
    x_main_trail: {spline: spl_ch01_wood_trail, length_m: 170, straight_through_s: 60}
    x_challenge: {id: poi_ch01_naruko, distance_m: 45, reward: codex_toshiya}
  - id: ch01.b09
    type: production_task
    task: manufacture
    place: pl_dojo_smithy
    title_ja: "矢を矯め、羽を付け直せ"
    title_en: "Straighten and refletch the arrows"
    target_s: 180
    checkpoint: true
    requires: [ch01.b07]
    site: 2
    unlocks: {weapons: [], mechanics: [manufacture]}
    registry: {item_ja: "矢", item_en: Arrows, qty: 12, unit_ja: "本", unit_en: arrows}
    music: ch01_smithy
    fail: {"on": none, to: none}
    dialogue:
      - {"on": beat_start, lines: [ch01.b09.tetsugoro.001, ch01.b09.tetsugoro.002], mode: ambient}
      - {"on": "step_failed:heat", lines: [ch01.b09.tetsugoro.003], mode: ambient}
      - {"on": "step_complete:bend:3", lines: [ch01.b09.tetsugoro.004], mode: ambient}
      - {"on": "step_start:paste", lines: [ch01.b09.tetsugoro.005], mode: ambient}
      - {"on": "step_start:assemble", lines: [ch01.b09.tetsugoro.006], mode: ambient}
      - {"on": "step_start:inspect", lines: [ch01.b09.tetsugoro.007, ch01.b09.nyaakoto.008], mode: ambient}
      - {"on": output_complete, lines: [ch01.b09.tetsugoro.009], mode: ambient}
      - {"on": "site_restored:2", lines: [ch01.b09.tetsugoro.010], mode: ambient}
      - {"on": beat_complete, lines: [ch01.b09.takemaru.011], mode: ambient}
    recipe: ya_repair
    stations: [st_ch01_fuigo, st_ch01_hibachi, st_ch01_tamegi, st_ch01_hagi_dai]
    steps:
      - {kind: heat, count: 1, station: st_ch01_fuigo, label: rekindle_hodo}
      - {kind: heat, count: 6, station: st_ch01_hibachi, timing: {beat_ms: 2000, tolerance_ms: 500}}
      - {kind: bend, count: 6, station: st_ch01_tamegi, timing: {beat_ms: 700, tolerance_ms: 150}}
      - {kind: paste, count: 1, station: st_ch01_hagi_dai}
      - {kind: assemble, count: 1, station: st_ch01_hagi_dai}
      - {kind: inspect, count: 1, station: st_ch01_hagi_dai}
    output: {item: ya, qty: 12}
    x_prompts: [ch01.b09.prompt.01, ch01.b09.prompt.02, ch01.b09.prompt.03, ch01.b09.prompt.04]
    x_tolerance_by_difficulty_ms: {easy: 200, normal: 150, hard: 120}
    x_failure: "a failed step repeats in place; there is no quality grade"
    x_quiver_after: {usable: 12}
  - id: ch01.b10
    type: dialogue
    place: pl_estate_day
    title_ja: "殺人刀と活人剣"
    title_en: "The sword that kills, the sword that gives life"
    target_s: 90
    checkpoint: false
    requires: [ch01.b09]
    music: ch01_veranda
    fail: {"on": none, to: none}
    lines:
      - {id: ch01.b10.household.001, speaker: household, ja: "先生が縁側におられるうちは、この屋敷は安泰や。", en: "While Sensei sits on that veranda, this house is safe.", register: yamato_commoner, audio: null, duration_s: 4.7}
      - {id: ch01.b10.sekireisai.002, speaker: mentor, ja: "殺人刀、活人剣。聞いたことはあるな。", en: "Setsunintō and katsujinken. You have heard the words.", register: archaic_samurai, audio: null, duration_s: 3.6}
      - {id: ch01.b10.nyaakoto.003, speaker: samurai, ja: "人を斬る刀と、人を活かす剣、と。", en: "A blade that kills, and a sword that gives life.", register: jidaigeki_restrained, audio: null, duration_s: 3.2}
      - {id: ch01.b10.sekireisai.004, speaker: mentor, ja: "違う。同じ一振りの話じゃ。", en: "No. They are one and the same blade.", register: archaic_samurai, audio: null, duration_s: 2.6}
      - {id: ch01.b10.sekireisai.005, speaker: mentor, ja: "一人の悪を斬り、万人を活かす。刀が許されるのは、そこまでじゃ。", en: "Cut one evil so ten thousand may live. A blade is forgiven that far, no further.", register: archaic_samurai, audio: null, duration_s: 6.0}
      - {id: ch01.b10.sekireisai.006, speaker: mentor, ja: "だが斬る前に、何を活かすかを数えよ。", en: "But before you cut, count what you mean to keep alive.", register: archaic_samurai, audio: null, duration_s: 3.7}
      - {id: ch01.b10.toranosuke.007, speaker: rival, ja: "先生、御免。……ニャーコト、表で立ち合え。袋竹刀でいい。", en: "Pardon me, Sensei. …Nyaakoto, face me outside. Fukuro-shinai will do.", register: formal_samurai, audio: null, duration_s: 5.2}
      - {id: ch01.b10.toranosuke.008, speaker: rival, ja: "今日しかない。……明日、大坂から使いが来る。", en: "Today is all I have. …Tomorrow, a man comes from Osaka.", register: brash_samurai, audio: null, duration_s: 4.3}
      - {id: ch01.b10.sekireisai.009, speaker: mentor, ja: "鷲尾。勝って、何を得る。", en: "Washio. If you win, what do you gain?", register: archaic_samurai, audio: null, duration_s: 2.5}
      - {id: ch01.b10.toranosuke.010, speaker: rival, ja: "名にございます。鷲尾の名が、まだ折れておらぬ証を。", en: "A name, Sensei. Proof that the Washio name is not yet broken.", register: formal_samurai, audio: null, duration_s: 4.9}
      - {id: ch01.b10.sekireisai.011, speaker: mentor, ja: "……よかろう。先に三本じゃ。ニャーコト、受けよ。", en: "…Very well. First to three. Nyaakoto, accept.", register: archaic_samurai, audio: null, duration_s: 4.5}
    trigger: "volume_enter:vol_ch01_estate_engawa"
    mode: ambient
    camera: soft_lookat
    interrupt: queue
    priority: 3
    dialogue:
      - {"on": "volume_enter:vol_ch01_estate_north_gate", lines: [ch01.b10.household.001], mode: ambient}
      - {"on": "volume_enter:vol_ch01_estate_engawa", lines: [ch01.b10.sekireisai.002, ch01.b10.nyaakoto.003, ch01.b10.sekireisai.004, ch01.b10.sekireisai.005, ch01.b10.sekireisai.006, ch01.b10.toranosuke.007, ch01.b10.toranosuke.008, ch01.b10.sekireisai.009, ch01.b10.toranosuke.010, ch01.b10.sekireisai.011], mode: ambient}
    x_entry: {transition: vol_ch01_ura_mon, spawn: ps_ch01_estate_entry, fade_s: 1.2}
  - id: ch01.b11
    type: duel
    place: pl_estate_day
    title_ja: "袋竹刀で虎之介と立ち合う"
    title_en: "Fukuro-shinai bout with Toranosuke"
    target_s: 360
    checkpoint: true
    requires: [ch01.b10]
    music: ch01_duel_rival
    fail: {"on": match_lost, to: retry}
    dialogue:
      - {"on": beat_start, lines: [ch01.b11.sekireisai.001, ch01.b11.toranosuke.002, ch01.b11.sekireisai.003], mode: ambient}
      - {"on": "point:player", lines: [ch01.b11.sekireisai.004], mode: ambient}
      - {"on": "point:rival", lines: [ch01.b11.sekireisai.005], mode: ambient}
      - {"on": ring_out, lines: [ch01.b11.sekireisai.006], mode: ambient}
      - {"on": "point:rival:first", lines: [ch01.b11.toranosuke.007], mode: ambient}
      - {"on": "feint_landed:first", lines: [ch01.b11.sekireisai.008], mode: ambient}
      - {"on": "score:player_leads_2", lines: [ch01.b11.toranosuke.009], mode: ambient}
      - {"on": duel_won, lines: [ch01.b11.sekireisai.010, ch01.b11.toranosuke.011, ch01.b11.sekireisai.012, ch01.b11.toranosuke.013], mode: ambient}
      - {"on": loss_continue, lines: [ch01.b11.sekireisai.014, ch01.b11.toranosuke.015, ch01.b11.sekireisai.016, ch01.b11.toranosuke.017], mode: ambient}
      - {"on": match_lost, lines: [ch01.b11.sekireisai.018], mode: ambient}
    opponent: npc_toranosuke
    weapons: {player: fukuro_shinai, opponent: fukuro_shinai}
    lethal: false
    scoring: {mode: points, first_to: 3}
    ring: vol_ch01_duel_ring
    finisher: none
    loss_policy: "continue_after:3"
    x_prompts: [ch01.b11.prompt.01, ch01.b11.prompt.02]
    x_point_rules:
      targets: [men, kote, do]
      clean_hit: "lands outside own recovery, unguarded"
      aiuchi_window_ms: 150
      reset_s: 3.0
      start_gap_cm: 400
      ring_out: reset_no_point
    x_pattern_table: tora_fukuro
    x_score_states:
      - state: even_or_rival_leads
        interval_s: [1.6, 2.4]
        weights: {tora_men: 35, tora_kote: 25, tora_kesa: 25, tora_feint: 15}
      - state: player_leads_1
        interval_s: [1.3, 2.0]
        weights: {tora_men: 25, tora_kote: 20, tora_kesa: 10, tora_feint: 25, tora_nidan: 20}
      - state: player_leads_2
        interval_s: [1.0, 1.6]
        recovery_bonus_ms: 150
        weights: {tora_men: 20, tora_feint: 30, tora_nidan: 35, tora_seme: 15}
    x_branches: {win: b11_win, loss: b11_loss, save_flag: ch01_duel_result}
  - id: ch01.b12
    type: dialogue
    place: pl_estate_day
    title_ja: "刀を預かる"
    title_en: "The blade held in trust"
    target_s: 60
    checkpoint: true
    requires: [ch01.b11]
    unlocks: {weapons: [0], mechanics: []}
    music: ch01_katana
    fail: {"on": none, to: none}
    lines:
      - {id: ch01.b12.sekireisai.001, speaker: mentor, ja: "負けて受け取る刀は、重いか。", en: "Is a blade heavy, when taken after a loss?", register: archaic_samurai, audio: null, duration_s: 2.8}
      - {id: ch01.b12.sekireisai.002, speaker: mentor, ja: "重さを知る者にしか、刀は預けられぬ。", en: "Only one who feels its weight can be trusted with it.", register: archaic_samurai, audio: null, duration_s: 3.7}
      - {id: ch01.b12.sekireisai.003, speaker: mentor, ja: "おぬしの刀じゃ。研ぎから戻った。", en: "Your blade. It is back from the polisher.", register: archaic_samurai, audio: null, duration_s: 3.3}
      - {id: ch01.b12.sekireisai.004, speaker: mentor, ja: "刀は民から預かるものじゃ。", en: "A blade is held in trust from the people.", register: archaic_samurai, audio: null, duration_s: 2.8}
      - {id: ch01.b12.nyaakoto.005, speaker: samurai, ja: "間合いを測り、命を守ります。", en: "I will measure the distance and protect life.", register: jidaigeki_restrained, audio: null, duration_s: 4.8}
      - {id: ch01.b12.sekireisai.006, speaker: mentor, ja: "それが猫柳生新陰流。剣は民のためにある。", en: "That is Nyaagyū Shinkage-ryū. The sword serves the people.", register: archaic_samurai, audio: null, duration_s: 4.8}
      - {id: ch01.b12.sekireisai.007, speaker: mentor, ja: "夕餉まで、刀と語らっておけ。", en: "Until supper, keep company with your sword.", register: archaic_samurai, audio: null, duration_s: 2.9}
    trigger: "interact:ip_ch01_katana"
    mode: blocking
    camera: soft_lookat
    interrupt: queue
    priority: 5
    dialogue:
      - {"on": "branch:b11_loss", lines: [ch01.b12.sekireisai.001, ch01.b12.sekireisai.002], mode: ambient}
      - {"on": "interact:ip_ch01_katana", lines: [ch01.b12.sekireisai.003, ch01.b12.sekireisai.004, ch01.b12.nyaakoto.005, ch01.b12.sekireisai.006], mode: blocking}
      - {"on": blocking_end, lines: [ch01.b12.sekireisai.007], mode: ambient}
    x_prompts: [ch01.b12.prompt.01]
    x_blocking_lines:
      - ch01.b12.sekireisai.003
      - ch01.b12.sekireisai.004
      - ch01.b12.nyaakoto.005
      - ch01.b12.sekireisai.006
    x_blocking_max_s: 20
    x_complete: {"on": sheathe_or_after_s, after_s: 20}
  - id: ch01.b13
    type: cinematic
    place: pl_estate_day
    title_ja: "空が裂ける"
    title_en: "The sky splits"
    target_s: 120
    checkpoint: false
    requires: [ch01.b12]
    music: ch01_sky_splits
    fail: {"on": none, to: none}
    sequence: "/Game/Campaign/Ch01/Sequences/LS_Ch01_B13_SkySplits"
    duration_s: 120
    skippable: true
    fallback: camera_blend
    subtitles:
      - {line: ch01.b13.takemaru.001, t_s: 31.0}
      - {line: ch01.b13.household.002, t_s: 33.7}
      - {line: ch01.b13.toranosuke.003, t_s: 46.0}
      - {line: ch01.b13.sekireisai.004, t_s: 58.0}
      - {line: ch01.b13.baio.005, t_s: 60.2}
      - {line: ch01.b13.sekireisai.006, t_s: 88.0}
      - {line: ch01.b13.nyaakoto.007, t_s: 92.1}
    end_state: {player_transform: ps_ch01_b13_end, equipped: katana_sheathed}
    x_next: ch02_invasion/ch02.b01
    x_chapter_complete: {registry_page: [ch01.b09], restored_sites: [0, 1, 2]}
collectibles:
  - id: ch01.c01
    type: collectible
    place: pl_issoseki_wood
    target_s: 0
    title_ja: "伝書の断簡 其の一"
    title_en: "Scroll fragment I"
    collectible_id: ch01.c01
    category: scroll_fragment
    mask_bit: 0
    x_location: "wooden plaque tied to the shimenawa post at the One-Claw Stone"
    x_available: [ch01.b08]
    codex:
      ja: "間合いは刀の長さにあらず。心の届く所なり。――石鈴斎"
      en: "Distance is not the length of the sword. It is how far the mind reaches. —Sekireisai"
  - id: ch01.c02
    type: collectible
    place: pl_issoseki_wood
    target_s: 0
    title_ja: "空紋の目印 其の一"
    title_en: "League mark I"
    collectible_id: ch01.c02
    category: league_mark
    mask_bit: 1
    x_location: "boundary stone carved with the house mon, south-east of the wood"
    x_available: [ch01.b08]
    codex:
      ja: "猫柳生の境石。空の紋が刻まれている。いつ誰が刻んだかは伝わらない。"
      en: "A Nyaagyu boundary stone carved with the sky mon. No one remembers who carved it, or when."
  - id: ch01.c03
    type: collectible
    place: pl_tsumagizaka_dojo
    target_s: 0
    title_ja: "家宝 門弟起請文の巻"
    title_en: "Heirloom: the pupils' oath roll"
    collectible_id: ch01.c03
    category: heirloom
    mask_bit: 2
    x_location: "lacquered box on the kamiza, dojo interior"
    x_available: [ch01.b04, ch01.b05]
    codex:
      ja: "入門の誓いを綴じた巻物。『猫琴』の名と花押、小さな血判がある。"
      en: "A roll of the pupils' entry oaths. One is signed with Nyaakoto's formal name, 猫琴, beside a monogram and a small blood seal."
  - id: ch01.c04
    type: collectible
    place: pl_dojo_smithy
    target_s: 0
    title_ja: "家宝 初代の鐔"
    title_en: "Heirloom: the founder's tsuba"
    collectible_id: ch01.c04
    category: heirloom
    mask_bit: 3
    x_location: "hanging on a peg above the anvil, waiting for its yearly cleaning"
    x_available: [ch01.b09]
    codex:
      ja: "猫柳生初代の鉄鐔。空の紋を透かしに彫る。年に一度、鍛冶場で錆を落とす。"
      en: "The first Nyaagyu lord's iron tsuba, pierced in the shape of the sky mon. Once a year the forge cleans off its rust."
  - id: ch01.c05
    type: collectible
    place: pl_dojo_smithy
    target_s: 0
    title_ja: "生産の記録 先代の控え帳"
    title_en: "Registry page: the old smith's day-book"
    collectible_id: ch01.c05
    category: registry_page
    mask_bit: 4
    x_location: "loft shelf above the tool rack"
    x_available: [ch01.b09]
    codex:
      ja: "先代の鍛冶の控え帳。鍬四十、鎌百二十、鋤十二。作った物だけが書いてある。"
      en: "An old smith's day-book. Forty hoes, a hundred and twenty sickles, twelve spades. Only what was made is written here."
  - id: ch01.c06
    type: collectible
    place: pl_matoba
    target_s: 0
    title_ja: "空紋の目印 其の二"
    title_en: "League mark II"
    collectible_id: ch01.c06
    category: league_mark
    mask_bit: 5
    x_location: "charcoal drawing on the inside wall of the shajo"
    x_available: [ch01.b07, ch01.b08]
    codex:
      ja: "射場の板壁に炭で描いた空の紋。横に中りを数えた線が並ぶ。"
      en: "The sky mon drawn in charcoal on the range wall, with rows of strokes counting hits beside it."
lines:
  - {id: ch01.b01.sekireisai.001, beat: ch01.b01, "on": seq, speaker: mentor, ja: "止め。", en: Stop., register: archaic_samurai, duration_s: 1.0, mode: cinematic, kind: cinematic, t_s: 60.0, audio: null}
  - {id: ch01.b01.sekireisai.002, beat: ch01.b01, "on": seq, speaker: mentor, ja: "百本振って、おぬしの剣は何本あった。", en: "A hundred swings. How many were truly yours?", register: archaic_samurai, duration_s: 3.7, mode: cinematic, kind: cinematic, t_s: 61.6, audio: null}
  - {id: ch01.b01.nyaakoto.003, beat: ch01.b01, "on": seq, speaker: samurai, ja: "……六十本ほどかと。", en: "…Sixty, perhaps.", register: jidaigeki_restrained, duration_s: 2.3, mode: cinematic, kind: cinematic, t_s: 65.9, audio: null}
  - {id: ch01.b01.sekireisai.004, beat: ch01.b01, "on": seq, speaker: mentor, ja: "正直でよい。残りの四十は、稽古で取り戻せ。", en: "Honest. Win back the other forty in practice.", register: archaic_samurai, duration_s: 4.1, mode: cinematic, kind: cinematic, t_s: 68.8, audio: null}
  - {id: ch01.b02.sekireisai.001, beat: ch01.b02, "on": beat_start, speaker: mentor, ja: "刃を急がせるな。相手の足音を聞け。", en: "Do not hurry your blade. Listen to your opponent's footing.", register: archaic_samurai, duration_s: 4.8, mode: ambient, kind: vo, anchor: "catalog ch01 line 1", audio: null}
  - {id: ch01.b02.sekireisai.002, beat: ch01.b02, "on": beat_start, speaker: mentor, ja: "正眼に構えよ。切っ先は、わしの喉へ。", en: "Take seigan. Point your tip at my throat.", register: archaic_samurai, duration_s: 3.5, mode: ambient, kind: vo, reading: "正眼（せいがん）・切っ先（きっさき）", audio: null}
  - {id: ch01.b02.sekireisai.003, beat: ch01.b02, "on": "gate_complete:stance_hold", speaker: mentor, ja: "水に映る月を思え。", en: "Think of the moon upon the water.", register: archaic_samurai, duration_s: 2.2, mode: ambient, kind: vo, reading: "水月（すいげつ）の教え", audio: null}
  - {id: ch01.b02.sekireisai.004, beat: ch01.b02, "on": "gate_complete:stance_hold", speaker: mentor, ja: "わしの太刀は届かず、おぬしの太刀は届く。そこに立て。", en: "Stand where my sword cannot reach, and yours can.", register: archaic_samurai, duration_s: 5.1, mode: ambient, kind: vo, reading: "太刀（たち）", audio: null}
  - {id: ch01.b02.nyaakoto.005, beat: ch01.b02, "on": "gate_complete:stance_hold", speaker: samurai, ja: "木刀の長さは、同じでございますが。", en: "But our swords are the same length, Sensei.", register: jidaigeki_restrained, duration_s: 3.5, mode: ambient, kind: vo, reading: "木刀（ぼくとう）", audio: null}
  - {id: ch01.b02.sekireisai.006, beat: ch01.b02, "on": "gate_complete:stance_hold", speaker: mentor, ja: "長さは同じ。心の長さが違う。", en: "The length is the same. The reach of the mind is not.", register: archaic_samurai, duration_s: 3.6, mode: ambient, kind: vo, audio: null}
  - {id: ch01.b02.sekireisai.007, beat: ch01.b02, "on": maai_step_ok, speaker: mentor, ja: "うむ。", en: Good., register: archaic_samurai, duration_s: 1.0, mode: ambient, kind: vo, repeatable: true, audio: null}
  - {id: ch01.b02.sekireisai.008, beat: ch01.b02, "on": "gate_complete:maai_step", speaker: mentor, ja: "……三つ。よし。", en: "…Three. Good.", register: archaic_samurai, duration_s: 1.6, mode: ambient, kind: vo, audio: null}
  - {id: ch01.b02.sekireisai.009, beat: ch01.b02, "on": "gate_retry:maai_step", speaker: mentor, ja: "近い。それでは互いに斬られる。", en: "Too close. There, we would both be cut.", register: archaic_samurai, duration_s: 3.1, mode: ambient, kind: vo, repeatable: true, audio: null}
  - {id: ch01.b02.sekireisai.010, beat: ch01.b02, "on": beat_complete, speaker: mentor, ja: "間合いは、剣の半分じゃ。", en: "Distance is half the art of the sword.", register: archaic_samurai, duration_s: 2.6, mode: ambient, kind: vo, reading: "間合い（まあい）", audio: null}
  - {id: ch01.b03.sekireisai.001, beat: ch01.b03, "on": beat_start, speaker: mentor, ja: "松吉、打ち込め。ニャーコトは受けよ。", en: "Matsukichi, attack. Nyaakoto, receive.", register: archaic_samurai, duration_s: 3.5, mode: ambient, kind: vo, audio: null}
  - {id: ch01.b03.sekireisai.002, beat: ch01.b03, "on": "gate_complete:front_guard_survive", speaker: mentor, ja: "受けは壁ではない。柳じゃ。", en: "A guard is no wall. It is a willow.", register: archaic_samurai, duration_s: 2.6, mode: ambient, kind: vo, reading: "受け（うけ）", audio: null}
  - {id: ch01.b03.sekireisai.003, beat: ch01.b03, "on": "gate_start:awase", speaker: mentor, ja: "次は合わせ。打たれる刹那に、こちらから迎えに行け。", en: "Now, awase. The instant he cuts, go out to meet it.", register: archaic_samurai, duration_s: 4.9, mode: ambient, kind: vo, reading: "合わせ（あわせ）・刹那（せつな）", audio: null}
  - {id: ch01.b03.sekireisai.004, beat: ch01.b03, "on": "awase_success:1", speaker: mentor, ja: "そうじゃ。太刀と太刀が、言葉を交わしたろう。", en: "Yes. Did you hear the swords speak?", register: archaic_samurai, duration_s: 3.9, mode: ambient, kind: vo, audio: null}
  - {id: ch01.b03.sekireisai.005, beat: ch01.b03, "on": "awase_fail:early", speaker: mentor, ja: "早い。相手の太刀を待て。", en: "Too early. Wait for his sword.", register: archaic_samurai, duration_s: 2.4, mode: ambient, kind: vo, repeatable: true, audio: null}
  - {id: ch01.b03.sekireisai.006, beat: ch01.b03, "on": "awase_fail:late", speaker: mentor, ja: "遅い。見てから動いては、間に合わぬ。", en: "Too late. Move after you see it, and you are late.", register: archaic_samurai, duration_s: 3.5, mode: ambient, kind: vo, repeatable: true, audio: null}
  - {id: ch01.b03.sekireisai.007, beat: ch01.b03, "on": "gate_start:recovery_complete", speaker: mentor, ja: "打ったら、刃の戻りを待て。二の太刀を急ぐな。", en: "After a cut, wait for the blade to return. Do not rush the next.", register: archaic_samurai, duration_s: 4.3, mode: ambient, kind: vo, reading: "二の太刀（にのたち）", audio: null}
  - {id: ch01.b03.sekireisai.008, beat: ch01.b03, "on": "gate_complete:recovery_complete", speaker: mentor, ja: "それが残心の始まりじゃ。", en: "That is where zanshin begins.", register: archaic_samurai, duration_s: 2.6, mode: ambient, kind: vo, reading: "残心（ざんしん）", audio: null}
  - {id: ch01.b03.matsukichi.009, beat: ch01.b03, "on": "bout_scored:1", speaker: pupil_matsukichi, ja: "……一本。参りました。", en: "…A clean point. I yield.", register: young_samurai, duration_s: 2.3, mode: ambient, kind: vo, reading: "一本（いっぽん）", audio: null}
  - {id: ch01.b03.sekireisai.010, beat: ch01.b03, "on": "bout_scored:1", speaker: mentor, ja: "竹丸、代われ。", en: "Takemaru, take his place.", register: archaic_samurai, duration_s: 1.7, mode: ambient, kind: vo, audio: null}
  - {id: ch01.b03.sekireisai.011, beat: ch01.b03, "on": beat_complete, speaker: mentor, ja: "二人とも、よう打った。よう打たれた。", en: "Both of you struck well. And were struck well.", register: archaic_samurai, duration_s: 3.5, mode: ambient, kind: vo, audio: null}
  - {id: ch01.b04.sekireisai.001, beat: ch01.b04, "on": beat_start, speaker: mentor, ja: "外へ出よ。転を教える。", en: "Outside. I will teach you marobashi.", register: archaic_samurai, duration_s: 2.4, mode: ambient, kind: vo, reading: "転（まろばし）", audio: null}
  - {id: ch01.b04.sekireisai.002, beat: ch01.b04, "on": "volume_enter:vol_ch01_dojo_yard", speaker: mentor, ja: "濁流に逆らうな。流れと共に、転がれ。", en: "Do not stand against the flood. Roll with it.", register: archaic_samurai, duration_s: 3.5, mode: ambient, kind: vo, reading: "濁流（だくりゅう）", audio: null}
  - {id: ch01.b04.sekireisai.003, beat: ch01.b04, "on": marobashi_miss, speaker: mentor, ja: "止まるな。合わせたら、もう転がっておれ。", en: "Do not stop. Once you meet the cut, be rolling already.", register: archaic_samurai, duration_s: 3.9, mode: ambient, kind: vo, repeatable: true, audio: null}
  - {id: ch01.b04.matsukichi.004, beat: ch01.b04, "on": "bout_scored:3", speaker: pupil_matsukichi, ja: "竹丸、さっきの試合、足がもつれてたぞ。", en: "Takemaru, your feet were tangled in that last bout.", register: young_samurai, duration_s: 3.7, mode: ambient, kind: vo, audio: null}
  - {id: ch01.b04.takemaru.005, beat: ch01.b04, "on": "bout_scored:3", speaker: pupil_takemaru, ja: "松吉さんこそ。", en: "So were yours.", register: young_samurai, duration_s: 1.6, mode: ambient, kind: vo, audio: null}
  - {id: ch01.b04.sekireisai.006, beat: ch01.b04, "on": beat_complete, speaker: mentor, ja: "相手が強いほど、よう転がる。覚えておけ。", en: "The stronger the opponent, the better you roll. Remember it.", register: archaic_samurai, duration_s: 4.0, mode: ambient, kind: vo, audio: null}
  - {id: ch01.b06.takemaru.001, beat: ch01.b06, "on": beat_start, speaker: pupil_takemaru, ja: "鞍はそこに。下鞍を敷いてから置いてください。", en: "The saddle is there. Lay the pad first, then set it.", register: young_samurai, duration_s: 4.5, mode: ambient, kind: vo, reading: "鞍（くら）・下鞍（したぐら）", audio: null}
  - {id: ch01.b06.takemaru.002, beat: ch01.b06, "on": "interact:ip_ch01_kura", speaker: pupil_takemaru, ja: "腹帯を締めて。……栗丸、また腹をふくらませてます。", en: "Tighten the girth. …She is puffing out her belly again.", register: young_samurai, duration_s: 5.0, mode: ambient, kind: vo, reading: "腹帯（はるび）", audio: null}
  - {id: ch01.b06.takemaru.003, beat: ch01.b06, "on": "interact:ip_ch01_haruobi", speaker: pupil_takemaru, ja: "鐙は力革に。左右の長さをそろえて。", en: "Stirrups on the leathers. Match the two sides.", register: young_samurai, duration_s: 3.5, mode: ambient, kind: vo, reading: "鐙（あぶみ）・力革（ちからがわ）", audio: null}
  - {id: ch01.b06.takemaru.004, beat: ch01.b06, "on": "interact:ip_ch01_abumi", speaker: pupil_takemaru, ja: "次は轡を……あ、またそっぽを向いた。", en: "Now the bit… ah, she has turned her head away again.", register: young_samurai, duration_s: 3.7, mode: ambient, kind: vo, reading: "轡（くつわ）", audio: null}
  - {id: ch01.b06.nyaakoto.005, beat: ch01.b06, "on": "interact_refused:ip_ch01_kutsuwa:1", speaker: samurai, ja: "……栗丸。", en: "…Kurimaru.", register: jidaigeki_restrained, duration_s: 1.2, mode: ambient, kind: vo, audio: null}
  - {id: ch01.b06.takemaru.006, beat: ch01.b06, "on": "interact_refused:ip_ch01_kutsuwa:2", speaker: pupil_takemaru, ja: "大麦の穂、袖に入れてたでしょう。", en: "You have an ear of barley in your sleeve, do you not?", register: young_samurai, duration_s: 3.6, mode: ambient, kind: vo, reading: "大麦（おおむぎ）", audio: null}
  - {id: ch01.b06.takemaru.007, beat: ch01.b06, "on": "item_given:barley_ear", speaker: pupil_takemaru, ja: "……毎朝、これです。", en: "…Every morning, this.", register: young_samurai, duration_s: 2.0, mode: ambient, kind: vo, audio: null}
  - {id: ch01.b06.takemaru.008, beat: ch01.b06, "on": "interact:ip_ch01_kutsuwa", speaker: pupil_takemaru, ja: "面繋よし、轡よし。手綱を取って、乗ってください。", en: "Headstall, bit, all good. Take the reins and mount.", register: young_samurai, duration_s: 4.5, mode: ambient, kind: vo, reading: "面繋（おもがい）・手綱（たづな）", audio: null}
  - {id: ch01.b06.takemaru.009, beat: ch01.b06, "on": mount, speaker: pupil_takemaru, ja: "嵐には近づかないで。袖を噛みますから。", en: "Keep clear of Arashi. He bites sleeves.", register: young_samurai, duration_s: 3.9, mode: ambient, kind: vo, reading: "嵐（あらし）", audio: null}
  - {id: ch01.b06.nyaakoto.010, beat: ch01.b06, "on": "volume_enter:vol_ch01_lane_pheasant", speaker: samurai, ja: "どう、どう……。雉だ。ただの雉だ。", en: "Easy, easy… A pheasant. Only a pheasant.", register: jidaigeki_restrained, duration_s: 3.1, mode: ambient, kind: vo, reading: "雉（きじ）", audio: null}
  - {id: ch01.b07.baio.001, beat: ch01.b07, "on": beat_start, speaker: pupil_baio, ja: "来なされたか。弓は、ここに。", en: "So you have come. Your bow is here.", register: elder_samurai, duration_s: 2.6, mode: ambient, kind: vo, audio: null}
  - {id: ch01.b07.baio.002, beat: ch01.b07, "on": "equip:18", speaker: pupil_baio, ja: "弓構え。……打起し。", en: "Ready the bow. …Raise it.", register: elder_samurai, duration_s: 2.0, mode: ambient, kind: vo, reading: "弓構え（ゆがまえ）・打起し（うちおこし）", audio: null}
  - {id: ch01.b07.baio.003, beat: ch01.b07, "on": "draw_complete:first", speaker: pupil_baio, ja: "引分けて……会。息を止めず、満ちるのを待ちなされ。", en: "Draw… and hold. Keep breathing. Let the draw fill.", register: elder_samurai, duration_s: 5.0, mode: ambient, kind: vo, reading: "引分け（ひきわけ）・会（かい）", audio: null}
  - {id: ch01.b07.baio.004, beat: ch01.b07, "on": "release:first", speaker: pupil_baio, ja: "離れたら、弓を追うな。残心。", en: "After the release, do not chase the bow. Zanshin.", register: elder_samurai, duration_s: 3.3, mode: ambient, kind: vo, reading: "離れ（はなれ）・残心（ざんしん）", audio: null}
  - {id: ch01.b07.matsukichi.005, beat: ch01.b07, "on": mato_hit, speaker: pupil_matsukichi, ja: "中り！", en: "Hit!", register: young_samurai, duration_s: 1.0, mode: ambient, kind: bark, reading: "中り（あたり）", repeatable: true, audio: null}
  - {id: ch01.b07.matsukichi.006, beat: ch01.b07, "on": mato_miss, speaker: pupil_matsukichi, ja: "外れ！", en: "Miss!", register: young_samurai, duration_s: 1.0, mode: ambient, kind: bark, reading: "外れ（はずれ）", repeatable: true, audio: null}
  - {id: ch01.b07.baio.007, beat: ch01.b07, "on": set_failed, speaker: pupil_baio, ja: "矢取りを待ちなされ。もう一度、六本。", en: "Wait while the arrows are fetched. Six more.", register: elder_samurai, duration_s: 3.5, mode: ambient, kind: vo, reading: "矢取り（やとり）", repeatable: true, audio: null}
  - {id: ch01.b07.baio.008, beat: ch01.b07, "on": "wave_start:2", speaker: pupil_baio, ja: "よろしい。次は吊り的。揺れる的は、行く先を射なされ。", en: "Good. Now the hanging marks. Shoot where a swinging mark is going.", register: elder_samurai, duration_s: 4.9, mode: ambient, kind: vo, reading: "吊り的（つりまと）", audio: null}
  - {id: ch01.b07.baio.009, beat: ch01.b07, "on": beat_complete, speaker: pupil_baio, ja: "……よい弓を引かれるようになった。", en: "…You draw a good bow now.", register: elder_samurai, duration_s: 2.3, mode: ambient, kind: vo, audio: null}
  - {id: ch01.b07.matsukichi.010, beat: ch01.b07, "on": beat_complete, speaker: pupil_matsukichi, ja: "六本、安土の石で曲がってます。鍛冶場へどうぞ。", en: "Six shafts bent on a stone in the azuchi. The smithy can fix them.", register: young_samurai, duration_s: 4.5, mode: ambient, kind: vo, reading: "安土（あづち）", audio: null}
  - {id: ch01.b08.nyaakoto.001, beat: ch01.b08, "on": "interact:poi_ch01_issoseki", speaker: samurai, ja: "一爪石……。初代さまが、爪一本で割ったという。", en: "The One-Claw Stone… The founder split it with one claw, they say.", register: jidaigeki_restrained, duration_s: 4.5, mode: ambient, kind: vo, reading: "一爪石（いっそうせき）", audio: null}
  - {id: ch01.b08.nyaakoto.002, beat: ch01.b08, "on": "interact:poi_ch01_issoseki", speaker: samurai, ja: "割れた石より、割った心を見よ……か。", en: "'Look not at the split stone, but the mind that split it.'", register: jidaigeki_restrained, duration_s: 3.9, mode: ambient, kind: vo, audio: null}
  - {id: ch01.b08.nyaakoto.003, beat: ch01.b08, "on": "interact:poi_ch01_vista", speaker: samurai, ja: "猫山まで二里。今日は城がよく見える。", en: "Two ri to Nekoyama. The castle is clear today.", register: jidaigeki_restrained, duration_s: 3.7, mode: ambient, kind: vo, reading: "猫山（ねこやま）・二里（にり）", audio: null}
  - {id: ch01.b08.nyaakoto.004, beat: ch01.b08, "on": "interact:poi_ch01_sakaiishi", speaker: samurai, ja: "家の紋……。誰が刻んだのだろう。", en: "The house mon… I wonder who carved it.", register: jidaigeki_restrained, duration_s: 3.3, mode: ambient, kind: vo, reading: "紋（もん）", audio: null}
  - {id: ch01.b08.nyaakoto.005, beat: ch01.b08, "on": "idle_s:180", speaker: samurai, ja: "槌の音……鍛冶場はあちらか。", en: "A hammer… The smithy is that way.", register: jidaigeki_restrained, duration_s: 3.1, mode: ambient, kind: vo, reading: "槌（つち）", audio: null}
  - {id: ch01.b09.tetsugoro.001, beat: ch01.b09, "on": beat_start, speaker: gunsmith, ja: "矢を曲げてきたな。六本か。", en: "Bent some arrows, did you? Six?", register: blunt_artisan, duration_s: 2.6, mode: ambient, kind: vo, audio: null}
  - {id: ch01.b09.tetsugoro.002, beat: ch01.b09, "on": beat_start, speaker: gunsmith, ja: "火を起こせ。竹は熱で素直になる。", en: "Wake the fire. Heat makes bamboo honest.", register: blunt_artisan, duration_s: 3.3, mode: ambient, kind: vo, audio: null}
  - {id: ch01.b09.tetsugoro.003, beat: ch01.b09, "on": "step_failed:heat", speaker: gunsmith, ja: "焦がすな。竹が泣く。冷まして、もう一度。", en: "Don't scorch it. Bamboo weeps. Let it cool, then again.", register: blunt_artisan, duration_s: 3.7, mode: ambient, kind: vo, repeatable: true, audio: null}
  - {id: ch01.b09.tetsugoro.004, beat: ch01.b09, "on": "step_complete:bend:3", speaker: gunsmith, ja: "曲がった矢は、嘘をつく。", en: "A bent arrow lies.", register: blunt_artisan, duration_s: 2.4, mode: ambient, kind: vo, audio: null}
  - {id: ch01.b09.tetsugoro.005, beat: ch01.b09, "on": "step_start:paste", speaker: gunsmith, ja: "膠は薄く。羽は三枚、向きをそろえろ。", en: "Thin glue. Three feathers, all facing the same way.", register: blunt_artisan, duration_s: 3.5, mode: ambient, kind: vo, reading: "膠（にかわ）", audio: null}
  - {id: ch01.b09.tetsugoro.006, beat: ch01.b09, "on": "step_start:assemble", speaker: gunsmith, ja: "糸で巻いて締めろ。……赤羽か。遠目にもよく見える。", en: "Bind it tight. …Red feathers. Easy to find from afar.", register: blunt_artisan, duration_s: 5.0, mode: ambient, kind: vo, reading: "赤羽（あかばね）・遠目（とおめ）", audio: null}
  - {id: ch01.b09.tetsugoro.007, beat: ch01.b09, "on": "step_start:inspect", speaker: gunsmith, ja: "数えろ。", en: "Count them.", register: blunt_artisan, duration_s: 1.0, mode: ambient, kind: vo, audio: null}
  - {id: ch01.b09.nyaakoto.008, beat: ch01.b09, "on": "step_start:inspect", speaker: samurai, ja: "十二本。", en: Twelve., register: jidaigeki_restrained, duration_s: 1.0, mode: ambient, kind: vo, audio: null}
  - {id: ch01.b09.tetsugoro.009, beat: ch01.b09, "on": output_complete, speaker: gunsmith, ja: "帳面に書いとけ。作ったもんは数えて残す。それがここの決まりだ。", en: "Write it in the book. What you make, you count and keep. That's the rule here.", register: blunt_artisan, duration_s: 6.2, mode: ambient, kind: vo, reading: "帳面（ちょうめん）", audio: null}
  - {id: ch01.b09.tetsugoro.010, beat: ch01.b09, "on": "site_restored:2", speaker: gunsmith, ja: "……雨が続くと火縄が死ぬ。何か手はないもんか。", en: "…When the rain keeps on, the match dies. There must be a way.", register: blunt_artisan, duration_s: 4.8, mode: ambient, kind: vo, reading: "火縄（ひなわ）", audio: null}
  - {id: ch01.b09.takemaru.011, beat: ch01.b09, "on": beat_complete, speaker: pupil_takemaru, ja: "ニャーコト殿！　先生がお呼びです。表の縁側へ。", en: "Nyaakoto! Sensei is asking for you. The front veranda.", register: young_samurai, duration_s: 4.3, mode: ambient, kind: vo, reading: "縁側（えんがわ）", audio: null}
  - {id: ch01.b11.sekireisai.001, beat: ch01.b11, "on": beat_start, speaker: mentor, ja: "両者、礼。", en: "Both of you, bow.", register: archaic_samurai, duration_s: 1.2, mode: ambient, kind: vo, reading: "礼（れい）", audio: null}
  - {id: ch01.b11.toranosuke.002, beat: ch01.b11, "on": beat_start, speaker: rival, ja: "礼はいい。来い、ニャーコト。今日こそ一本取る。", en: "Skip the bow. Come, Nyaakoto. Today I take a point.", register: brash_samurai, duration_s: 4.3, mode: ambient, kind: vo, anchor: "bible §6.5 register sample", audio: null}
  - {id: ch01.b11.sekireisai.003, beat: ch01.b11, "on": beat_start, speaker: mentor, ja: "礼はせよ。……構えて、始め！", en: "You will bow. …Kamae. Begin!", register: archaic_samurai, duration_s: 2.7, mode: ambient, kind: vo, reading: "構え（かまえ）", audio: null}
  - {id: ch01.b11.sekireisai.004, beat: ch01.b11, "on": "point:player", speaker: mentor, ja: "一本。ニャーコト。", en: "Point. Nyaakoto.", register: archaic_samurai, duration_s: 1.8, mode: ambient, kind: bark, repeatable: true, audio: null}
  - {id: ch01.b11.sekireisai.005, beat: ch01.b11, "on": "point:rival", speaker: mentor, ja: "一本。鷲尾。", en: "Point. Washio.", register: archaic_samurai, duration_s: 1.2, mode: ambient, kind: bark, repeatable: true, audio: null}
  - {id: ch01.b11.sekireisai.006, beat: ch01.b11, "on": ring_out, speaker: mentor, ja: "縄を出たぞ。戻れ。", en: "Out of the ring. Return.", register: archaic_samurai, duration_s: 1.6, mode: ambient, kind: bark, reading: "場外（じょうがい）", repeatable: true, audio: null}
  - {id: ch01.b11.toranosuke.007, beat: ch01.b11, "on": "point:rival:first", speaker: rival, ja: "どうした。先生の教えは、それだけか。", en: "What is wrong? Is that all Sensei taught you?", register: brash_samurai, duration_s: 3.5, mode: ambient, kind: bark, audio: null}
  - {id: ch01.b11.sekireisai.008, beat: ch01.b11, "on": "feint_landed:first", speaker: mentor, ja: "目を見るな、足を見よ。蹴らぬ足は、打たぬ足じゃ。", en: "Do not watch his eyes. Watch his feet. A foot that does not push does not strike.", register: archaic_samurai, duration_s: 5.4, mode: ambient, kind: vo, reading: "蹴る（ける）", audio: null}
  - {id: ch01.b11.toranosuke.009, beat: ch01.b11, "on": "score:player_leads_2", speaker: rival, ja: "くそっ……急げ、急げ……！", en: "Damn it… Faster. Faster…!", register: brash_samurai, duration_s: 2.7, mode: ambient, kind: bark, audio: null}
  - {id: ch01.b11.sekireisai.010, beat: ch01.b11, "on": duel_won, speaker: mentor, ja: "それまで。三本、ニャーコト。", en: "Enough. Three points to Nyaakoto.", register: archaic_samurai, duration_s: 2.6, mode: ambient, kind: vo, branch: win, audio: null}
  - {id: ch01.b11.toranosuke.011, beat: ch01.b11, "on": duel_won, speaker: rival, ja: "……もう一度だ。", en: "…Again.", register: brash_samurai, duration_s: 1.8, mode: ambient, kind: vo, branch: win, audio: null}
  - {id: ch01.b11.sekireisai.012, beat: ch01.b11, "on": duel_won, speaker: mentor, ja: "今日の一本は、今日かぎりじゃ。", en: "Today's point belongs to today alone.", register: archaic_samurai, duration_s: 3.1, mode: ambient, kind: vo, branch: win, audio: null}
  - {id: ch01.b11.toranosuke.013, beat: ch01.b11, "on": duel_won, speaker: rival, ja: "……失礼いたす。", en: "…By your leave.", register: brash_samurai, duration_s: 1.8, mode: ambient, kind: vo, branch: win, audio: null}
  - {id: ch01.b11.sekireisai.014, beat: ch01.b11, "on": loss_continue, speaker: mentor, ja: "それまで。三本、鷲尾。", en: "Enough. Three points to Washio.", register: archaic_samurai, duration_s: 2.1, mode: ambient, kind: vo, branch: loss, audio: null}
  - {id: ch01.b11.toranosuke.015, beat: ch01.b11, "on": loss_continue, speaker: rival, ja: "……勝った。勝ったぞ。", en: "…I won. I won.", register: brash_samurai, duration_s: 2.3, mode: ambient, kind: vo, branch: loss, audio: null}
  - {id: ch01.b11.sekireisai.016, beat: ch01.b11, "on": loss_continue, speaker: mentor, ja: "勝ちを急いだな、虎之介。", en: "You hurried to win, Toranosuke.", register: archaic_samurai, duration_s: 2.4, mode: ambient, kind: vo, branch: loss, audio: null}
  - {id: ch01.b11.toranosuke.017, beat: ch01.b11, "on": loss_continue, speaker: rival, ja: "急がねば、間に合わぬのです。", en: "If I do not hurry, I will be too late.", register: formal_samurai, duration_s: 2.8, mode: ambient, kind: vo, branch: loss, audio: null}
  - {id: ch01.b11.sekireisai.018, beat: ch01.b11, "on": match_lost, speaker: mentor, ja: "もう一度。今度は、あやつの急ぎを使え。", en: "Again. This time, use his haste.", register: archaic_samurai, duration_s: 3.7, mode: ambient, kind: vo, repeatable: true, audio: null}
  - {id: ch01.b13.takemaru.001, beat: ch01.b13, "on": seq, speaker: pupil_takemaru, ja: "先生……空が……。", en: "Sensei… the sky…", register: young_samurai, duration_s: 2.1, mode: cinematic, kind: cinematic, t_s: 31.0, audio: null}
  - {id: ch01.b13.household.002, beat: ch01.b13, "on": seq, speaker: household, ja: "火事か……いや、空や！　空が割れとる！", en: "A fire? No, the sky! The sky's splitting!", register: yamato_commoner, duration_s: 3.5, mode: cinematic, kind: cinematic, t_s: 33.7, audio: null}
  - {id: ch01.b13.toranosuke.003, beat: ch01.b13, "on": seq, speaker: rival, ja: "なんだ……あれは。", en: "What… is that?", register: brash_samurai, duration_s: 2.0, mode: cinematic, kind: cinematic, t_s: 46.0, audio: null}
  - {id: ch01.b13.sekireisai.004, beat: ch01.b13, "on": seq, speaker: mentor, ja: "梅翁、鐘を打て。", en: "Baiō. Ring the bell.", register: archaic_samurai, duration_s: 1.6, mode: cinematic, kind: cinematic, reading: "梅翁（ばいおう）", t_s: 58.0, audio: null}
  - {id: ch01.b13.baio.005, beat: ch01.b13, "on": seq, speaker: pupil_baio, ja: "……承知。", en: "…At once.", register: elder_samurai, duration_s: 1.2, mode: cinematic, kind: cinematic, t_s: 60.2, audio: null}
  - {id: ch01.b13.sekireisai.006, beat: ch01.b13, "on": seq, speaker: mentor, ja: "ニャーコト。預けたものを、忘れるな。", en: "Nyaakoto. Do not forget what you hold in trust.", register: archaic_samurai, duration_s: 3.5, mode: cinematic, kind: cinematic, t_s: 88.0, audio: null}
  - {id: ch01.b13.nyaakoto.007, beat: ch01.b13, "on": seq, speaker: samurai, ja: "……はい、先生。", en: "…Yes, Sensei.", register: jidaigeki_restrained, duration_s: 1.6, mode: cinematic, kind: cinematic, t_s: 92.1, audio: null}
ui_prompts:
  - {id: ch01.b02.prompt.01, beat: ch01.b02, "on": beat_start, ja: "{Block}長押しで正眼に構える（0.6秒）", en: "Hold {Block} to take seigan (0.6 s)."}
  - {id: ch01.b02.prompt.02, beat: ch01.b02, "on": "gate_start:maai_step", ja: "水月の輪が浮かぶ間合いで止まり、師に向く", en: "Stop where the moon ring appears, facing Sensei."}
  - {id: ch01.b03.prompt.01, beat: ch01.b03, "on": beat_start, ja: "相手に向き、{Block}を保って一撃を受ける", en: "Face him and hold {Block} through the strike."}
  - {id: ch01.b03.prompt.02, beat: ch01.b03, "on": "gate_start:awase", ja: "金色の予兆に合わせて{Block}を押す", en: "Press {Block} as the gold warning flashes."}
  - {id: ch01.b03.prompt.03, beat: ch01.b03, "on": "gate_start:recovery_complete", ja: "一度振り、{Fire}を離して刃の戻りを待つ", en: "Swing once, release {Fire}, and wait for the blade to return."}
  - {id: ch01.b03.prompt.04, beat: ch01.b03, "on": "bout_start:1", ja: "合わせて崩し、その隙に打って一本を取る", en: "Meet his cut, then strike the opening to score."}
  - {id: ch01.b04.prompt.01, beat: ch01.b04, "on": "volume_enter:vol_ch01_dojo_yard", ja: "合わせた直後（0.4秒以内）に 左右＋{Jump}", en: "Within 0.4 s of an awase: Left/Right + {Jump}."}
  - {id: ch01.b05.prompt.01, beat: ch01.b05, "on": "volume_enter:vol_ch01_engawa_sunbeam", ja: "{Interact}で一礼（任意）", en: "{Interact} to bow (optional)."}
  - {id: ch01.b06.prompt.01, beat: ch01.b06, "on": beat_start, ja: "光る馬具で{Interact}：鞍・腹帯・鐙・轡の順", en: "{Interact} at each tack piece: saddle, girth, stirrups, bit."}
  - {id: ch01.b06.prompt.02, beat: ch01.b06, "on": "interact_refused:ip_ch01_kutsuwa:2", ja: "もう一度{Interact}で大麦の穂を与える", en: "Press {Interact} again to offer the ear of barley."}
  - {id: ch01.b06.prompt.03, beat: ch01.b06, "on": "interact:ip_ch01_kutsuwa", ja: "{Interact}で栗丸に乗る（右から）", en: "{Interact} to mount Kurimaru (from the right)."}
  - {id: ch01.b06.prompt.04, beat: ch01.b06, "on": mount, ja: "前進で常歩。前進しながら{Sprint}長押しで歩度を上げる", en: "Move forward to walk. Hold {Sprint} while moving forward to quicken her gait."}
  - {id: ch01.b06.prompt.05, beat: ch01.b06, "on": horse_spooked, ja: "馬が驚いた。手綱を引かず、落ち着くのを待つ", en: "She is spooked. Ease the reins and let her settle."}
  - {id: ch01.b07.prompt.01, beat: ch01.b07, "on": "equip:18", ja: "{Fire}長押しで引分け（0.65秒）。会で狙い、離して放つ", en: "Hold {Fire} to draw (0.65 s). Aim at full draw; release to loose."}
  - {id: ch01.b07.prompt.02, beat: ch01.b07, "on": "wave_start:2", ja: "遠い的ほど矢は落ちる。揺れの先を狙う", en: "Arrows drop over distance. Lead the swing."}
  - {id: ch01.b09.prompt.01, beat: ch01.b09, "on": beat_start, ja: "{Interact}で鞴を押し、火床を起こす", en: "Press {Interact} to work the bellows and wake the hearth."}
  - {id: ch01.b09.prompt.02, beat: ch01.b09, "on": "step_start:heat", ja: "矢を炭にかざし、艶が出たら離す", en: "Warm the shaft over the coals; lift it when it gleams."}
  - {id: ch01.b09.prompt.03, beat: ch01.b09, "on": "step_start:bend", ja: "矯め木で押し、筋がまっすぐになったら離す", en: "Press it in the tamegi; release when the line runs true."}
  - {id: ch01.b09.prompt.04, beat: ch01.b09, "on": "step_start:paste", ja: "{Interact}で膠を引き、羽を付ける", en: "{Interact} to spread glue and set the feathers."}
  - {id: ch01.b11.prompt.01, beat: ch01.b11, "on": beat_start, ja: "三本先取。面・小手・胴への一撃で一本", en: "First to three. A clean hit to head, wrist or body scores."}
  - {id: ch01.b11.prompt.02, beat: ch01.b11, "on": beat_start, ja: "輪の外へ出ると仕切り直し", en: "Step out of the ring and the exchange resets."}
  - {id: ch01.b12.prompt.01, beat: ch01.b12, "on": blocking_end, ja: "{Sheathe}で抜刀・納刀", en: "Press {Sheathe} to draw or sheathe the blade."}
```
