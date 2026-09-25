# SORA Arena: Nyaagyu Rebellion — Campaign Story Bible

**Status:** design source for Wave 2 lane C1. It is the macro design for the offline campaign: story, cast, pacing, beat taxonomy, places, and art direction. Nothing here is implemented yet. Where this bible gives numbers (beat parameters, timings, windups), they are **proposals** for the lanes that own them to ratify: L1 for layouts, beats and saves; L2 for enemies and stealth; L3 for bosses; L4 for UI; C2–C4 for spaces and missions. Per-chapter scripts with 60–150 bilingual lines each go in `docs/campaign/chapter-0N.md`. Native Japanese review (B7) and review by a period historian and practitioner are still pending.

**Related sources:** [catalog.json](../../Content/Data/catalog.json) (schema 3), [offline acceptance](offline-acceptance.md), [historical arms](../historical-arms.md), [horse tack references](../historical-horse-tack-art-reference.md), [SORA kamon runtime art](../sora-kamon-runtime-art.md), [photoreal acceptance](../art-direction/photoreal-acceptance.md), [Nyaakoto target](../art-direction/NYAAKOTO_PHOTOREAL_TARGET.md), [Estate mesh terrain](../mesh-terrain-nyaagyu.md).

---

## 1. Logline, tone, themes, setting

### 1.1 Logline

> 空が裂けた日、猫柳生の若き侍ニャーコトは、師を「担保」として奪われた。借りに縛られた民と共に、彼は田に水を、炉に火を、街に灯を取り戻す。作られた物だけを数える新しい帳簿、SORA XOR を掲げて。
>
> The day the sky split, Nyaakoto, a young samurai of Nyaagyu, saw his master taken as "collateral." With people bound by debt, he brings water back to the fields, fire to the forges and light to the streets, under a new ledger that counts only what is actually made: SORA XOR.

The playtime target is **420 minutes (7 h)** for a first-time player on Normal (真剣). The allowed range is 360–480 min. See §10.

### 1.2 Tone rules

- **Serious samurai drama.** Loss, duty, debt, and the choice between cutting and protecting. Deaths, captivity and grief are played straight.
- **Restrained cat humor.** Humor comes from character and feline behavior, never slapstick. There is at most about one light moment per 10 minutes, and **never** during a boss fight, a death, captivity, or grief. Approved examples:
  1. ch01: the oldest pupil, 梅翁 (Baiō), is asleep in the dojo's one sunbeam, and the pupils bow around him without comment.
  2. ch01: Kurimaru, the horse, refuses the bit until he is given an ear of barley.
  3. ch05: a Credit House notice on the foundry wall reads 「昼寝禁止」 ("No napping — downtime is billable").
  4. ch06: the alien clerk Iota is found hiding inside a document crate. "It was… comfortable."
  5. ch06: before the moat swim, Nyaakoto's ears flatten. Kohagi: 「泳ぐよ。」 Nyaakoto, after a pause: 「……泳ぐ。」
  6. ch07: stowing away inside rice bales. Kohagi: 「くしゃみ、するな。」 ("Don't sneeze.")
  7. ch08: Val Amort slides a "restructuring" contract across the desk. Nyaakoto holds his gaze and pushes the inkstone off the edge.
  8. ch08: Sekireisai, freed from his cell: 「遅かったのう。」 ("You came late.")
  9. Epilogue: Val Amort, now a prisoner, counting barley sheaves under Iota's supervision: 「……一束。」
  10. ch04 (added in review): on the barley delivery Kurimaru stops to eat from the load. Otane: 「その馬、麦で動くんか。」 Nyaakoto: 「……麦で動く。」 It pays off humor beat 2.
  11. ch07 (added in review): Iota corrects the rider count over the slate, 「……訂正いたします。二十一騎。」 It is played flat and never in combat.
  
  Chapter scripts may add other small character moments (for example ch06's "presumed to be fish" bark) if they stay within the one-per-10-minutes budget and the exclusions above. Each chapter doc lists its light moments.
- The aliens are **not cartoon villains.** They sincerely believe credit creates order and that debt is discipline. Their menace comes from politeness and arithmetic.

### 1.3 Themes

1. **活人剣 (katsujinken, "the life-giving sword").** Protecting life includes protecting livelihoods. Nyaakoto's arc runs from knowing the phrase to living it. He ends as someone who rebuilds, not only someone who cuts.
2. **Production against extraction.** Value comes from made things, inspected in public. Debt created from nothing, at interest the world cannot out-produce, becomes perpetual.
3. **Obligation and dignity.** Debt as a chain (Toranosuke's house) contrasts with mutual obligation among people who make things together (the League).
4. **Master, pupil, rival.** Sekireisai's teaching is completed in his absence. Toranosuke falls and is redeemed by being disarmed rather than killed (無刀取り, mutō-dori).

### 1.4 Setting and world rules

- **When:** an alternate 元和九年 (Genna 9, 1623), from late spring through autumn. The architecture, dress, arms and props belong to the early 17th century (慶長–寛永, 1596–1644). See §19.
- **Where:** the 猫柳生 (ニャーギュウ, Nyaagyu) valley in the 大和 (Yamato) highlands. It is a small samurai house's domain, modeled respectfully on the Yagyū of Yamato. The key locations and distances:
  - The hill estate and dojo.
  - The lower village fields, 2 km downhill.
  - The Silk Foundry, 5 km upriver.
  - The castle town of 猫山 (ねこやま, Nekoyama), 8 km along the 猫柳生街道. The Lantern Ward is one of its districts.
  - The Debt Citadel, raised by the invaders on the Nekoyama castle hill.
- **Edo is silent.** Messengers do not return. The story stays local.
- **People are cats.** They have anthropomorphic feline anatomy, paw grips and full clothing. Horses, oxen, birds and fish are ordinary animals. There are no humans.
- **The invaders are cats too.** They are hairless, sphynx-like alien cats from the Stellar Credit House. Beyond the story contrast, this has a production benefit: hairless enemies need no strand grooms, which saves fur cost on crowds.
- **Language:** Japanese voice and UI are primary, with English subtitles on by default (catalog `default_language: ja`, `english_subtitles_default: true`). See §18.

---

## 2. The fictional monetary premise: production-only XOR

**Boundary (binding).** The campaign's SORA XOR is a **storytelling premise**: in the fiction it is created *only* against verified production. It deliberately does **not** describe the real SORA network or the supplied SORA Nexus article, which describes a broader design with a purchasing-power anchor, reserves and separate Phoenix investment interests (see [README](../../README.md)).

- The game makes no claims about real-world money, investment, returns or policy.
- Campaign XOR is never a wallet balance, is never convertible, never calls IrohaConnect, and has no relation to multiplayer XOR bonds or NFTs.
- The campaign works fully offline with no wallet.
- XOR appears only as a physical split tally and a registry entry that names **what was made and how many**. It is never shown as a number in a purse, a balance, a price or an exchange rate.
- Every chapter document repeats this boundary in a note under its title, so that release copy drawn from any single chapter keeps it.

### 2.1 The invaders' system (in fiction)

- The Stellar Credit House issues **信用 (shin'yō, "Credit")** as loans against *future* production. Its interest is set above anything the borrower can grow, so the balance can never close.
- It buys crops before they are planted, using the period term **青田買い (aotagai)**. It places cyan **債務封印 (debt seals)** on granaries, sluices, forges and looms: sealed means of production cannot be used until the debt is "serviced."
- Every household door shows its balance in cold cyan numerals, and the balance ticks upward each night.
- The master record is the **帳簿機関 (Ledger Engine)** inside the Debt Citadel.

### 2.2 The League's charter (in fiction)

The charter is 生産改帳の五箇条, the five articles of the production registry, drafted by Shirasumi Oyuki in ch03 and first applied in ch05:

| # | Article (JA) | Meaning (EN) | How gameplay shows it |
|---|---|---|---|
| 1 | 物なくして札なし | No goods, no tally. XOR is cut only when a finished good or delivered service physically exists. | Registry entries appear only when a `production_task` completes. |
| 2 | 三者改め | Three-party inspection: maker, receiver and a rotating inspector. | ch05.b12 ceremony; later entries show three seals. |
| 3 | 割符 (わりふ) | The wooden tally is split in two. The SORA mon is branded across the split, and each party keeps one half. | Diegetic tally prop; the registry UI shows the split tally icon. |
| 4 | 利をもって利を生まず | XOR bears no interest. The League lends tools, not money. | Tools are issued at supply points; there is no shop and no currency grind. |
| 5 | 帳は民の前に | The registry is public, posted at every 高札場 (notice board). | ch06 and ch08: pages are posted on kōsatsu boards. |

### 2.3 Registry (生産改帳) as feedback, not economy

Each production task writes a brush entry with a period counter word:

- 矢 12本 (arrows), 種籾 4俵 (bales of seed rice), 提灯 40張 (lanterns), 用水 12枚 (paddies watered), 水車 1基 (waterwheel), 麦 30束 (sheaves of barley), 鏃 24本 (arrowheads), アーク・カービン 3挺 (carbines), 絹幟 1旒 (silk banner).

The chapter-complete screen shows that chapter's registry page instead of a score.

**Unlocks are deterministic story progression (§11). They are never purchases.** Skeptics are voiced so the premise is argued rather than preached:

- Taemon: 「紙は紙や。」 ("Paper is paper.")
- Kōzō: 「わしは鉄しか信じん。」 ("I trust iron.")

Oyuki answers with deeds, and Iota defects because of arithmetic, not ideology.

---

## 3. 猫柳生新陰流 (ニャーギュウしんかげりゅう), Nyaagyū Shinkage-ryū

The user's spelling is "Nyaagyushinkageryuu." It is a **fictional school** in an alternate Edo, inspired by the historical Yagyū Shinkage-ryū.

### 3.1 Respect rules (binding)

- Consistent with [historical-arms.md](../historical-arms.md): the game does not teach, reproduce or claim authorization from the living Yagyū Shinkage-ryū.
- In-game techniques use **general period martial vocabulary** and original names. The school's actual named kata (for example the 三学円之太刀 set) and their sequences are **not** reproduced.
- Philosophical anchors come from widely documented sources:
  - 柳生宗矩『兵法家伝書』(1632) and its sections 殺人刀 / 活人剣.
  - The tradition of Sekishūsai's 無刀取り demonstration (1594).
  - The Shinkage principle of 転 (まろばし).
- Motion capture and cinematic kata require review by a qualified practitioner or historian before release. Marketing must never call them authentic Yagyū practice.

### 3.2 Principles → mechanics

Timings are proposals; L2 owns the combat rules. The existing dojo gates in `SoraDojoRules.h` are kept.

| Principle | JA (reading) | In the story | Mechanic | Proposed parameters (Normal) | Taught |
|---|---|---|---|---|---|
| The life-giving sword | 活人剣 (かつにんけん / かつじんけん) | Sekireisai: 「刀は民から預かるものじゃ。」 ("A blade is held in trust from the people.") | Non-lethal options against the debt-bound (峰打ち + seal-cut); final boss captured, not killed | — | ch01 (idea), ch03 (mechanic) |
| Centre stance | 正眼の構え (せいがん) | Base kamae | Stance hold before scoring | Hold 600 ms (existing gate) | ch01.b02 |
| Moon in water: the distance read | 水月 (すいげつ) | "Stand where his blade cannot reach and yours can." | Maai ring: a faint moon-in-water reticle ring when at ideal distance for the equipped weapon | Ring inner/outer = weapon range ±15% | ch01.b02 |
| Receiving | 受け (うけ) | Front guard | Directional guard with stamina cost | Guard survives a strike landing 350 ms after raise (existing) | ch01.b03 |
| Meeting cut | 合わせ (あわせ) | Parry by meeting the cut | Timed parry → stagger | Fresh parry within 260 ms (existing); stagger 1.2 s | ch01.b03 |
| Rolling | 転 (まろばし) | "Do not stand against the flood; roll with it." | Directional step that repositions to the flank: after a successful awase, **or** during the last 400 ms before an attack flagged `marobashi_eligible` lands (introduced for Dunark's unparryable thrust in ch02; later thrusts that the scripts answer with 転, such as Collatera's lunge and Val Amort's cane thrust, should carry the same flag in L3's tables) | Input window 400 ms; opponent turn lag 0.8 s | ch01.b04 (after awase); ch02.b15 (vs `marobashi_eligible`) |
| Lingering mind | 残心 (ざんしん) | Awareness after the cut | Holding guard for 0.5 s after a defeat restores 15 stamina | — | ch01 (passive) |
| Back of the blade | 峰打ち (みねうち) | Strike to subdue | Automatic against `bound_conscript`: knockdown, never death | — | ch03.b03 |
| No-sword capture | 無刀取り (むとうどり) | The master's last teaching, learned alone | With the katana **sheathed**, a perfect parry of a *committed vertical cut* disarms the attacker | Window 180 ms; only vs attacks flagged `muto_eligible` | ch06.b09 |

---

## 4. Historical arms, archery and horsemanship

These are campaign rules. Final claims of historical accuracy still require expert review (see [photoreal-acceptance.md](../art-direction/photoreal-acceptance.md)).

### 4.1 Katana (刀)

- Worn edge-up in the obi as a daishō (katana plus wakizashi).
- Early-Edo 慶長新刀 blades have a typical nagasa of about 70–76 cm. The hero source uses 77–82 cm (see historical-arms.md), which should be reviewed as long for the period.
- Two-handed grip at the tsuka with a visible tsuba.
- Cuts are committed and readable, with recovery (catalog weapon 0: 0.75 s cooldown). There are no spinning combos.
- Sheathing (納刀) is an explicit animation, needed for mutō-dori.
- Training blades:
  - 木刀 (bokutō) for forms.
  - 袋竹刀 (fukuro-shinai), a leather-covered split-bamboo sword, for full-contact bouts. This is historically associated with the Shinkage lineage. It is a presentation variant of weapon 0 flagged non-lethal, not a new catalog weapon.

### 4.2 Yumi (和弓)

- About 221 cm, asymmetric, with the grip about one-third from the lower end (All Japan Kyudo Federation).
- Construction is laminated bamboo and wood, transitional for this period.
- The arrow rests on the **right** side of the bow. The draw uses a 弽 (yugake) thumb glove and carries past the ear. After release the bow rotates in the hand (弓返り, yugaeri); this must be animated.
- Simplified 射法 sequence for gameplay: 弓構え → 打起し → 引分け → 会 (hold) → 離れ → 残心. The draw takes 650 ms, the release is gravity-affected, and arrows fly visibly (catalog 18). The game does not simulate formal kyūdō.
- Arrows are three-fletched (三立羽) and carried in a war 箙 (ebira). Nyaakoto's red fletching is a character choice, not a period claim. The quiver holds 12 arrows (catalog `quiver_arrows`).
- Bushi archery of the period was dominated by the Heki (日置) lineage. The game uses a generic, unattributed form.
- **Mounted archery shoots to the left (弓手側).** The mounted fire arc is −170° to +15° of the horse's heading (0° = forward, negative = left). When shooting, the tazuna are knotted and left on the neck and the rider rises in the broad abumi.

### 4.3 Yari (槍) and naginata (薙刀)

- **Su-yari (素槍):** a straight point on a long shaft. It thrusts forward, is weak inside the shaft's useful distance, and works from horseback as a forward or right-side thrust (catalog 19).
- **Naginata:** a wide committed cut with a longer recovery. In Edo it is strongly associated with samurai women; Okinu wields it (catalog 20).
- Polearm collision is layout-aware: reach is obstructed by looms and pillars (ch05).

### 4.4 Matchlocks (火縄銃)

- The period weapon is the tanegashima-pattern matchlock with a 火皿 pan and 火縄 slow-match. 早合 (hayagō) paper cartridges speed loading.
- Rain degrades reliability even with treated rain-match (雨火縄).
- A short horseback matchlock (馬上筒) existed, but the player never fires firearms mounted.
- League 鉄砲 NPCs in night scenes show the match's glow and smoke.
- The catalog's **コイル火縄銃 (Coil Matchlock, 5)** is, in fiction, a village matchlock with an alien coil-ignition breech. It fires in rain, which is why the League adopts it in the early-summer rains (ch04). **プラズマ火縄銃 (14)** is a captured alien-built design.

### 4.5 Horses and tack

- **Horses:** native Japanese horses (在来馬, e.g. Kiso type), about 130 cm at the withers: stocky, short-legged, heavy-maned, with large heads.
  - Coats: 鹿毛 bay, 栗毛 chestnut, 黒鹿毛 black-bay.
  - Unshod; they wear straw 馬沓 (umagutsu) on long rides.
  - Human-sized cat riders look large on them, as period riders did.
  - A lateral ambling gait (側対歩) at travel speed must be verified with an equine animator.
- **Gaits in the UI:** 常歩 walk, 速歩 trot, 駈歩 canter, 襲歩 gallop.
- **Riding tack:**
  - 鞍 kura: a four-piece wooden tree of 前輪 (front arch), 後輪 (rear arch) and two 居木, with lacquer and lacing (Met 2000.405).
  - Under-saddle pads 肌付 / 切付 (to verify).
  - 障泥 aori leg flaps.
  - 腹帯 (はるび) girth.
  - 力革 stirrup leathers.
  - 舌長鐙 / 鳩胸鐙 abumi: broad-toed with an open heel (Met 2016.205).
  - 轡 kutsuwa bit, 面繋 headstall, 胸繋 breastcollar, 鞦 crupper.
  - 手綱 tazuna: broad dyed-cloth reins.
- **Pack horses (駄馬)** carry a 荷鞍 pack saddle with 振り分け loads (ch02, ch04, ch05, ch08). A load (駄) is two rice bales, about 120 kg; post-station rules later put a full 本馬 load at about 40 貫 (150 kg).
- **No horse-drawn carts or wagons** (they were not used in Edo Japan) and no 大八車 handcart (after 1657). Heavy local freight goes by pack horse; the only wheeled vehicle is the ox-drawn freight cart (牛車, うしぐるま) in ch04.
- **No geldings.** Horses were not castrated in Japan until the Meiji era, so every horse is a mare or a stallion: Kurimaru and the pack mare Bunta are mares, Arashi is a stallion.
- The **SORA mon** appears on the front plate of the abumi (following the Met 2008.120 family-mon placement) and on the crupper fittings.
- The current tack source is stylized and needs the review in [historical-horse-tack-art-reference.md](../historical-horse-tack-art-reference.md).

### 4.6 Armor and dress

- Period armor is 当世具足 (tōsei gusoku).
  - **Nyaakoto:** 紺糸威 (dark-blue lacing) with 朱漆 (vermillion lacquer) plates, matching the reference. The SORA mon is on the sode and dō.
  - **League ashigaru:** 陣笠 (jingasa) with a painted SORA mon, 腹当 (haraate) chest guards, and 旗指物 (sashimono) back-banners in ch08.
- Everyday dress: 小袖, 袴, 襷 (tasuki) sleeve ties, 手拭い, 蓑 and 菅笠 in rain.
- Elders wear 十徳 (jittoku) jackets. Kohagi dresses as an indigo-clad peddler, not in the later theatrical black "ninja suit."

---

## 5. Factions

| JA | Reading | English | Description |
|---|---|---|---|
| 猫柳生家 / 猫柳生藩 | ニャーギュウけ / ニャーギュウはん | House of Nyaagyu / Nyaagyu domain | Small samurai house of the valley. Its house mon **is the SORA logo**. |
| 猫柳生新陰流 | ニャーギュウしんかげりゅう | Nyaagyū Shinkage-ryū | The house's sword school at Tsumagizaka Dōjō. |
| 空紋一揆 | そらもんいっき | The Sora League | The resistance: an oath-bound league (一揆) of samurai, farmers and craftspeople under the SORA mon, founded in ch03. |
| 恒星信用院 | こうせいしんよういん | The Stellar Credit House | The invaders' own name for themselves. Locals call them 取立猫 (とりたてねこ, "the Collector Cats"). |
| 執行局 | しっこうきょく | The Enforcement Office | The Credit House's armed arm. |
| 債縛衆 | さいばくしゅう | The Debt-Bound | Locals forced into service by 縛債の首輪 (debt collars). Non-lethal targets; freed by cutting the collar. |

---

## 6. Cast

The speaker-id column proposes ids for L1's schema-4 `dialogue_speakers`. Existing ids are kept: `mentor`, `samurai`, `scout`, `farmer`, `artisan`, `banker`.

### 6.1 Principal cast

| Speaker id | JA name | Reading | English | Role | Look (photoreal) | Voice register |
|---|---|---|---|---|---|---|
| `samurai` | ニャーコト (formal: 猫琴) | ニャーコト | Nyaakoto | Protagonist, apprentice | Silver-grey mackerel tabby, white muzzle, chin and chest, blue eyes, lean. Keikogi and hakama in ch01; 紺糸威 armor with vermillion lacquer from ch02. Katana, yumi, red-fletched ebira. The formal kanji appears only on the dojo's 起請文. | Restrained, polite 時代劇 register (NHK taiga style): 「拙者」 with superiors, 「私」 when formal, plain 「だ」 with peers. Few words; never shouts except in combat barks. |
| `mentor` | 猫柳生 石鈴斎 | ニャーギュウ せきれいさい | Nyaagyu Sekireisai | Retired lord (隠居), head of the school | Elderly faded brown-grey tabby going silver, notched left ear, amber eyes, 十徳 over kimono. Taken as "collateral" in ch02, freed in ch08. | Archaic samurai speech: 「わし」, 「〜じゃ」, 「〜ぬ」, 「よいか」. Koan-like and dry; warmth is rare and brief. |
| `rival` | 鷲尾 虎之介 | わしお とらのすけ | Washio Toranosuke | Senior pupil (兄弟子) from a house deep in pre-invasion debt | Big orange mackerel tabby, green-gold eyes, scar across the nose; black lacquer armor with scarlet lacing. Wears a grey Credit House haori in ch03–06, burned in ch08. | Brash samurai: 「俺」 with Nyaakoto, 「拙者」 in formal speech. Clipped and proud; his humility after ch06 is audible. |
| `leader` | 白澄 お雪 | しらすみ おゆき | Shirasumi Oyuki | Leader of the Sora League; kept the domain accounts (勘定) for her ailing father | White shorthair, odd eyes (blue and gold), slender. 小袖 with tasuki; carries a 算盤 (soroban), a 矢立 (brush case) and a well-thumbed arithmetic primer. | Precise business keigo: 「わたくし」, 「〜でございます」. Numbers first, dry wit. Never raises her voice. |
| `scout` | 三毛の小萩 | みけの こはぎ | Kohagi | League scout and infiltrator | Small calico, green eyes. Indigo peddler's clothes, 手甲, hidden short blade. | Terse, low, clipped: 「あたし」. Reports in counts and directions. |

### 6.2 Craftspeople and farmers

| Speaker id | JA name | Reading | English | Role | Look | Voice register |
|---|---|---|---|---|---|---|
| `farmer` | 庄屋 田右衛門 | しょうや たえもん | Headman Taemon | Village headman (庄屋 is the Kinai usage) and keeper of water rights | Elderly brown tabby, stooped, 蓑 and 菅笠 | Slow Yamato/Kamigata-flavored speech (「〜や」, 「あかん」). Skeptical; proverbs. |
| `farmer_young` | お種 | おたね | Otane | Young farmer and sluice keeper; fights with a kusarigama | Black-and-white はちわれ, strong; 野良着 and head towel | Quick, bright Kamigata speech, spirited. |
| `lantern_maker` | 提灯師 灯吉 | ちょうちんし とうきち | Tōkichi the lantern-maker | Hid the Lantern Ward's tools | Elderly cream tabby; squints; paper-cut paws | Gentle artisan speech. |
| `fireworks` | 花火師 玉吉 | はなびし たまきち | Tamakichi the fireworks-maker | Builds the hand-mortar (擲弾筒) from festival shells | Ginger-and-white, singed whiskers | Cheerful Kamigata; restrained comic relief. |
| `gunsmith` | 鉄砲鍛冶 鉄五郎 | てっぽうかじ てつごろう | Tetsugorō the gunsmith | The estate smith in ch01; carries the smithy to the Hidden Valley in ch02; builds the coil-breech matchlock (ch04); taken by a collection patrol after ch04 and freed at the foundry (ch05.b03), where he builds the Arc Carbine and later the Repeater | Grey-and-white bicolor, burn-scarred paw | Blunt and practical, Kamigata-leaning (〜や, ええ). First person おれ, never わし. |
| `foundry_master` | 村下 鋼蔵 | むらげ こうぞう | Murage Kōzō | Master smelter (村下) of the Silk Foundry's tatara | Smoke-dark brown, singed whiskers, massive forearms; a clouded left eye from years of reading the flame | Gruff, few words, Yamato speech (わし, 〜や, 〜とる). |
| `weaver` | 織師 お絹 | おりし おきぬ | Okinu the weaver | Daughter of a samurai household, trained in Nishijin; leads the loom workers. Her naginata was her mother's (ch05.b04) | Sleek black, yellow eyes; indigo 小袖 with tasuki | Soft Kyoto speech (「〜どす」, 「〜おす」) over a steel core. |
| `apothecary` | 薬師 お葛 | くすし おくず | Okuzu the apothecary | League medic; gives the Healing Lance | Tortoiseshell (さび); medicine chest | Calm, maternal, practical. |
| `pupil_matsukichi`, `pupil_takemaru`, `pupil_baio` | 門弟 松吉 / 竹丸 / 梅翁 | まつきち / たけまる / ばいおう | Pupils Matsukichi, Takemaru, Baiō | Dojo pupils. Baiō is the oldest and naps. Takemaru reaches the Hidden Valley in ch02, is taken in the sweep after ch07's decree, and is freed in ch08.b07 | Assorted tabbies | Matsukichi and Takemaru: young samurai speech, polite to Nyaakoto (「ニャーコト殿」). Baiō, despite being a pupil, is an old man, as the 翁 in his name says: elder speech (わし, 〜なされ, 〜じゃ). |

### 6.3 The Stellar Credit House

All aliens speak Japanese through a 通訳襟 (translation collar). Their delivery is flat and even-tempered, with light DSP: a band-limited formant chorus that never pitch-shifts. They use hyper-polite corporate keigo combined with dehumanizing financial terms: 債務者番号, 担保, 元本, 利息, 延滞, 差押え, 回収, 償却, 与信, 追証. They never use contractions in English subtitles and address people by account number. Name etymologies are never explained in-game.

| Speaker id | Title + name (JA) | Reading | English | Role | Look | Name logic |
|---|---|---|---|---|---|---|
| `banker` | 大徴収官 ヴァル・アモルト | だいちょうしゅうかん ヴァル・アモルト | High Collector Val Amort | Head of the occupation; **final boss** | Tall, age-wrinkled hairless skin, platinum ocular, long high-collared grey coat, alien sword-cane (仕込み杖) | amortization |
| `boss_collatera` | 旗艦提督 コラテラ | きかんていとく コラテラ | Admiral Collatera | Commander of the flagship 『複利号』; ch07 boss | Black naval-cut coat with cyan piping, twin pistols | collateral |
| `boss_eskro` | 金庫番 エスクロ | きんこばん エスクロ | Vault Warden Eskro | Blind keeper of the Ledger Vault; ch06 boss | Eyeless face with sensor ridges, long arms and claws, vault robes (unsettling, not gory) | escrow |
| `boss_tarifa` | 工房監督官 タリファ | こうぼうかんとくかん タリファ | Foundry Overseer Tarifa | Runs the Silk Foundry at 140% quota; ch05 boss | Soot-stained grey coat, goggles, tether-cable on the right arm | tariff |
| `boss_margina` | 査定官 マルジナ | さていかん マルジナ | Assessor Margina | Pilots the walker 査定機「秤」; ch04 boss | Seen in the cockpit; thin, ocular-lit | margin |
| `boss_penalta` | 取立頭 ペナルタ | とりたてがしら ペナルタ | Enforcer-Chief Penalta | Lantern Ward enforcer; ch03 boss | Huge, heavy graphite armor, tower shield, seal-hammer | penalty |
| `boss_dunark` | 上陸指揮官 ドゥナーク | じょうりくしきかん ドゥナーク | Landing Commander Dunark | Leads the first landing; ch02 boss | Tall armored duelist; helmet engraved with ledger lines; long straight 帳刃 (tally blade) | dunning |
| `clerk` | 会計補 イオタ | かいけいほ イオタ | Junior Auditor Iota | Vault clerk who **defects** in ch06 | Small, pale lavender-grey, big ears, oversized ocular lens, suit a size too large | iota (the smallest amount) |

**Iota's register:** over-formal keigo learned from manuals. He sometimes honors objects (「帳簿様」) and speaks literally. English subtitles are stilted and exact. His defection comes from arithmetic: 「計算しました。四百年分。」 ("I ran the numbers. Four hundred years' worth.")

### 6.4 Horses

- 栗丸 (くりまる, Kurimaru): Nyaakoto's chestnut native mare. Patient, unimpressed, food-motivated.
- 嵐 (あらし, Arashi): Toranosuke's black-bay stallion. He bites sleeves.
- 文太 (ぶんた, Bunta): Shimomura's bay pack mare (ch04), led from Kurimaru's saddle. She is timid near cyan light.

### 6.4.1 Minor and generic speaker ids (ratified in review)

The chapter scripts share these ids. L1 adds them to schema-4 `dialogue_speakers`. Generic ids carry a `voice_variant` for casting.

| Speaker id | JA label | EN label | Used in | Notes |
|---|---|---|---|---|
| `pupil_matsukichi`, `pupil_takemaru`, `pupil_baio` | 門弟 松吉 / 竹丸 / 梅翁 | Matsukichi / Takemaru / Baiō | ch01, ch02, ch08 | See §6.2 |
| `household` | 屋敷の者 | Household | ch01 | Estate servants |
| `groom` | 馬子 | Groom | ch02 | Rides 乗掛 on the lead pack horse |
| `carpenter` | 大工 源六 | Genroku the carpenter | ch04 | Waterwheel repair |
| `yosaku` | 与作 | Yosaku | ch04 | Otane's brother, a freed conscript (one line) |
| `planter` | 早乙女 | Planter | ch04 | Planting song |
| `villager` | 村人 | Villager | ch02, ch04, ch08 | Rural voices |
| `resident` | 町の衆 | Resident | ch03, ch06, ch08 | Town voices |
| `child` | 子ども | Child | ch02, ch03, ch08 | |
| `artisan` | 職人 | Artisan | ch03, ch05 | Existing catalog id (Isa the bamboo-splitter; foundry workers) |
| `league_ashigaru` | 一揆の足軽 | League ashigaru | ch07, ch08 | |
| `enforcer` | 執行兵 | Enforcer | ch02–ch08 | All alien rank-and-file; variants rifle, blade, shield, grenadier, marksman |
| `conscript` | 債縛衆 | Debt-Bound | ch03–ch08 | Collared locals |
| `auditor` | 監査官 | Auditor | ch06, ch07 | |
| `drone` | 目録 | Inventory drone | ch02–ch04 | |
| `credit_system` | 信用院・告知音声 | Credit House notice voice | ch02, ch03 | Seals, terminals, PA |
| `ship_voice` | 艦内通達 | Ship announcement | ch07 | |
| `boss_collatera` | 旗艦提督 コラテラ | Admiral Collatera | ch07 | Takes catalog ch07 line 2 from `banker` (§20) |

### 6.5 Register samples

These are anchor lines for casting and translation.

| Speaker | JA | EN |
|---|---|---|
| mentor | 勝とうとするな。相手の太刀が、おぬしの道を教えてくれる。 | Do not try to win. His sword will show you your path. |
| samurai | 斬るのは最後だ。まず、守るものを数える。 | Cutting comes last. First, count what we protect. |
| rival | 礼はいい。来い、ニャーコト。今日こそ一本取る。 | Skip the bow. Come, Nyaakoto. Today I take a point. |
| leader | 数字は嘘をつきません。嘘をつくのは、数字を隠す者です。 | Numbers do not lie. Those who hide them do. |
| scout | 東に三。屋根に一。……灯り、消して。 | Three east. One on the roof. …Lamp. Out. |
| farmer | 水はな、借りるもんやない。上から下へ、皆に回るもんや。 | Water isn't something you borrow. It runs downhill, round to everyone. |
| farmer_young | この鎌な、稲も刈るし、あんたらも刈るで。 | This sickle cuts rice. It'll cut you too. |
| foundry_master | 鉄は三晩で生まれる。急かすな。 | Iron is born over three nights. Don't rush it. |
| weaver | 糸は一本では弱おす。けど、織ったら旗になりますえ。 | One thread alone is weak. Woven, it becomes a banner. |
| gunsmith | 雨で火縄が死ぬんなら、火縄をやめりゃええ。 | If rain kills the match, stop using a match. |
| clerk | 恐れ入りますが、この帳簿は、閉じない仕様でございます。 | Pardon me, but this ledger is designed never to close. |
| banker | 債務者番号七〇三一。貴殿の未来は、既に担保として計上済みでございます。 | Debtor seven-zero-three-one. Your future has already been booked as collateral. |

---

## 7. Enemies

L2 owns `enemies.json`. Each type needs a readable silhouette. The first six types are L2's planned roster.

| id | JA | Reading | English | Silhouette / weapon | Behavior | First seen |
|---|---|---|---|---|---|---|
| `enforcer_rifle` | 執行兵 | しっこうへい | Enforcer | Graphite armor, levy carbine | Cover, suppress, flank | ch02 |
| `blade_retainer` | 取立刃兵 | とりたてじんぺい | Collection Blade | Tally blade | Closes outside maai; 420 ms fixed-direction warning; withdraws when crowded (existing) | ch02 |
| `shield_enforcer` | 盾執行兵 | たてしっこうへい | Shield Enforcer | Tower shield, baton | Frontal block; flank or break | ch02 |
| `grenadier` | 擲弾兵 | てきだんへい | Grenadier | Drum-magazine backpack | Arcing shells with a visible arc decal | ch02 |
| `marksman` | 照準査定兵 | しょうじゅんさていへい | Assessor-Marksman | Long barrel, monocle glint | Rooftops; 900 ms lock glint | ch02 |
| `drone` | 目録 | もくろく | "Inventory" drone | Floating disc with a cyan eye | Scouts, marks, drops seizure nets | ch02 |
| `bound_conscript` | 債縛衆 | さいばくしゅう | Debt-Bound conscript | Local clothes, glowing collar | Non-lethal only: 峰打ち knockdown, then seal-cut. Freed conscripts flee or join. | ch03 |
| `auditor` | 監査官 | かんさかん | Auditor | Slate, lamp | Weak in combat; raises the alarm | ch06 |
| `loom_automaton` | 織機傀儡 | しょっきくぐつ | Loom Automaton | Spindly shuttle-limbed machine | Tarifa's adds; slow, hits hard | ch05 |
| `seizure_walker` | 差押機 | さしおさえき | Seizure Walker | 4 m quadruped | Sweeping beams, nets; heavy | ch08 (the ch04 boss is its large variant) |

Freeing conscripts **never** counts toward lethal kill quotas. The `nonlethal_types` beat parameter handles this.

---

## 8. Bosses

There are seven bosses, each with a distinct fighting style, plus two duels with Toranosuke (ch01, ch06). L3 owns `bosses.json`. Telegraph rules:

- Every telegraph must precede damage by at least its windup.
- Cyan means a locked aim or beam; amber means a cleave or area attack. This matches the existing collector prototype.
- An accessible palette is available (L4).
- Windups listed below are for Normal. Easy (稽古) adds 30%; Hard (免許皆伝) subtracts 15%.
- Each boss's **voice bark is also an audio telegraph**, and it is captioned.

| Boss id | Chapter / place | Style | Phases (HP %) | Signature attacks (windup) | Counterplay | Voice telegraph | Fate |
|---|---|---|---|---|---|---|---|
| `boss_dunark` | ch02.b15 / estate courtyard, burning | **Metronomic fencer.** A sword duel in fixed "notices" (3-beat measures). | P1 100–60 / P2 60–25 / P3 25–0 | P1: two quick cuts (500 ms) + heavy overhead (900 ms, amber). P2 speeds up and adds a thrust (700 ms, cannot be parried). P3 adds feints (blade tilt tell) and a shield drone that blocks arrows. | Awase the heavy overhead → 1.2 s stagger. 転 around the thrust → flank cut. Shoot the drone in its recovery. | 「督促、第一回。」 / 「第二回。」 / 「最終督促。」 | Killed; his ledger-plate is cut through. |
| `boss_penalta` | ch03.b17 / Lantern Wharf, heavy rain | **Shield bruiser.** | P1 100–50 / P2 50–0 | P1: shield advance, bash (600 ms), hammer slam (1000 ms, amber ring 350 cm). P2, with the shield broken: hammer spin (1200 ms) and 延滞 seal traps that root for 1.5 s. | Frontal immunity: flank via the cargo stacks. Shoot the rear cooling vents with the yumi. Three grenade hits break the shield. Cut the crane rope to drop a cargo net (3 s stun). | 「延滞金が発生しております。」 | Dragged into the canal by his own hammer (off-screen). |
| `boss_hakari` | ch04.b16 / paddies and mill | **Colossal walker; mounted fight.** An 8 m assessor engine. | P1 mounted 100–55 / P2 on foot 55–0 | Seizure net (800 ms, cyan lock) roots the horse. Low sweep beam (1100 ms): gallop out. Drones. | Circle **counter-clockwise** so the target stays on the left for mounted yumi. Shoot 4 weigh-coils that glow when a leg plants. P2: it kneels to "assess" the mill; cut the exposed ledger-drum. | 「査定中……評価額、零。」 | The machine collapses into a paddy; Margina ejects and flees. |
| `boss_tarifa` | ch05.b16 / tatara hall catwalks | **Hazard controller** with a tether-lash. | P1 100–65 / P2 65–30 / P3 30–0 | Tether lash (700 ms) pulls the player 4 m toward molten channels. Channel gates cycle every 12 s (2 s glow ramp). P2 adds 2 loom automata per wave and a double lash. P3: rain on hot iron causes steam bursts (900 ms hiss). | Parry the lash → the cable snaps (2 s stun). Naginata reach vs automata. Lure her into steam: her shield drops. | 「稼働率百四十パーセント。」 / 「休憩は計上されません。」 | Falls into the channel she opened (off-screen). |
| `boss_eskro` | ch06.b13 / vault core, darkness | **Blind sound-hunter.** A stealth boss. | P1 hunt 100–60 / P2 flood 60–25 / P3 frenzy 25–0 | Reconciliation pulse every 8 s (700 ms chirp; sonar ring 1800 cm) reveals moving players. Pounce (600 ms) onto the last noise. Claw flurry. P2 floods the floor, so splashing is loud: use the raised shelves. P3: pulses every 4 s plus 2 audit-hound drones. | Stand still during pulses. Throw 礫 (tsubute) to lure. Rear strikes during the 1.5 s recovery after a missed pounce. Noise: run > walk > crouch. | 「照合。」 / 「……不一致。」 | Sealed inside the flooded vault; fate left ambiguous. |
| `boss_collatera` | ch07.b13 / flagship bridge | **Ranged gunslinger** with a personal shield. | P1 100–60 / P2 60–30 / P3 30–0 | Twin-pistol 3-round bursts (400 ms, cyan laser dots). The shield regenerates after 4 s without damage. P2: 追証 barrage of orbital strikes on cover (1500 ms amber rings); the bridge lists 10° and props slide. P3: draws a sabre for a short blade duel. | Break the shield with a charged Plasma Matchlock or the Shock Emitter, or with the yumi during reload. Keep moving through P2. Awase the sabre in P3. | 「追証を請求します。」 | Knocked down; lost in the controlled crash. |
| `boss_val_amort` | ch08.b14 / Ledger Engine summit | **Multi-phase collector.** Beam, arena seizure, then a final sword duel. | P1 100–70 / P2 70–40 / P3 40–0 (checkpoint each phase) | P1: locked-aim cyan beam (900 ms lock) + amber cleave (existing prototype patterns) + orbiting ledger shards. P2: 差押え seizure field: marked floor tiles become void after 1500 ms; 担保傀儡 (collateral constructs) made from heaps of seized goods. P3: sword-cane duel; "final foreclosure" overhead (1000 ms, `muto_eligible`). | Guard or parry the cleave, sidestep the beam. Read the tiles. In P3, **sheathe** and perform mutō-dori on the foreclosure, then interact to cut the engine's spine. | 「元本、回収。」 / 「差押えを執行いたします。」 | **Disarmed and captured** (katsujinken); counting barley in the epilogue. |

Duels with Toranosuke:

- **ch01.b11:** fukuro-shinai, first to 3 clean points, feints.
- **ch06.b09:** real steel.
  - Phase 1: fast aggressive combinations.
  - Mid-duel event: he sees his family's ledger page.
  - Phase 2: desperate committed cuts, all `muto_eligible`.
  - The finish must be mutō-dori; the lethal finisher is disabled.

---

## 9. Story by chapter

The campaign runs in three acts. **Act I** (ch01–02) is loss. **Act II** (ch03–05) is rebuilding, and the League and XOR are born. **Act III** (ch06–08) is exposure and liberation.

**第一章 道場の修行: Dojo Apprenticeship.** Late spring. At the Tsumagizaka Dōjō, Nyaakoto trains under Sekireisai in stance, distance, guard, awase and marobashi. He shoots at the matoba, rides Kurimaru and straightens arrows at the dojo smithy. Toranosuke, the proud senior pupil whose house is sunk in debt to Osaka rice brokers, challenges him to a fukuro-shinai bout in the estate courtyard. Afterwards Sekireisai returns Nyaakoto's katana with the lesson of katsujinken: a blade is held in trust from the people. At dusk the sky splits.

**第二章 異星からの侵略: The Invasion.** Ships descend and cyan debt seals clamp onto the granaries. Nyaakoto holds the gate and takes a su-yari from the armory. Sekireisai orders him to save the seed rice and the people: 「種は明日の田じゃ」 ("Seed is tomorrow's field"). Nyaakoto breaks the granary seal, loads the bales onto pack horses, and escorts the string on horseback along the forest highway, shooting Inventory drones from the saddle. He clears the Stone Bridge checkpoint and hands out food in the Hidden Valley. Kohagi brings word that the master stayed behind. Nyaakoto rides back and kills Landing Commander Dunark in the burning courtyard, too late: Val Amort's lift beam takes Sekireisai as 担保 (collateral). At dawn, craftspeople set up a workshop in the valley with what they carried.

**第三章 占領された街: Occupied Streets.** Ten days later, in the long early-summer rains of the fourth month (卯の花腐し), Nyaakoto enters the Lantern Ward by riverboat, disguised as a commoner with only a travel short sword. Every door glows with a balance that grows overnight. He recovers the hidden tool cache (and his katana), escorts the lantern-makers, relights their workshop, and destroys the debt terminal at the notice square. Oyuki steps out of hiding. Around the SORA mon, with the oath of 一味神水, the Sora League is founded. At the wharf Nyaakoto sees Toranosuke in a Credit House haori: "My house's debt was bought." Penalta attacks.

**第四章 田畑の解放: Agricultural Liberation.** Early summer: barley harvest and rice planting. The Credit House has sealed the Great Reservoir, sells water by the measure, and has bought the unplanted rice on credit. Nyaakoto rides the dikes with Otane and receives the rebuilt coil-breech matchlock and a kusarigama. He cranks open the First Weir and holds it while the water rises, repairs the waterwheel, guards the planting line, and delivers barley to three hamlets by pack horse. Oyuki writes the first entries in the 生産改帳. The Assessor Engine Hakari seizes the harvest, and Nyaakoto brings it down in a mounted fight across the paddies. At dusk there are fireflies, and Toranosuke watches from a ridge.

**第五章 工房の蜂起: The Foundry Uprising.** Midsummer night at the Silk Foundry: collared workers and a 140% quota. Nyaakoto enters through the iron-sand channels and frees the craftspeople, among them Tetsugorō, taken by a collection patrol after ch04. Okinu, who lends him her mother's naginata, and Kōzō start the uprising. The bellows are worked, the smelt is defended, arrowheads are forged and the first Arc Carbine is assembled, and Okinu weaves the League's silk banner. Then the first XOR is cut: three parties count only what exists and split the tally under the SORA mon. Tarifa opens the furnace channels as a thunderstorm breaks, and falls. At dawn the silk nobori flies, and a message arrives from inside the vault: the quota board ejects a message slate paired with Iota's, which is the League's only "radio" from ch06 on.

**第六章 債務金庫への潜入: Ledger-Vault Infiltration.** New moon. Nyaakoto swims the moat, climbs the castle walls and silences the relay. Iota, found hiding in a crate, provides a key-slate. Nyaakoto crosses ledger corridors and nightingale floors and **copies** the master ledger rather than burning it: the interest exceeds everything Nyaagyu could ever make. In the archive Toranosuke stands guard. Mid-duel he reads his own family's page: "I paid every month. It grew." Nyaakoto disarms him with mutō-dori, and Toranosuke pledges his tantō. Nyaakoto jams the presses, evades the blind warden Eskro in the dark, and escapes through the flooding water gate. At dawn the copied pages are posted on every kōsatsu. The flagship's shadow moves.

**第七章 異星旗艦への突撃: Alien Flagship Assault.** Typhoon. The flagship 『複利号』 hauls Nyaagyu's seized goods up a tether from the Citadel. The League storms the anchor bastion, and Nyaakoto and Kohagi stow away in rice bales. Inside they cross the hold of seized heirlooms, fight in the reckoning engine, and reverse the lift to send the goods back down. They fight across the hangar and the hull ridge above the storm, and duel Admiral Collatera on the bridge. Nyaakoto holds the evacuation beacon while the dying ship is steered onto empty hills, then leaps clear on a cargo sled. Toranosuke's riders are waiting. Val Amort broadcasts: 「全担保を回収する。」 ("All collateral is now called.") Before dawn his collectors sweep the lower village and take people as collateral, among them the pupil Takemaru, who was guarding the refugees.

**第八章 最後の解放: Final Liberation.** Autumn dawn. The League rides under SORA sashimono, and Kōzō and Okinu present the Monofilament Naginata. The campaign's set pieces follow in order:

1. A mounted charge across the causeway beside Toranosuke.
2. Volley ranks at the outer bailey.
3. The field forge defended and rations carried to the squads.
4. The main gate's seal anchors smashed with a kanabō.
5. The collateral cells opened (Takemaru and Taemon's villagers among the prisoners), and Sekireisai freed: 「遅かったのう。」
6. The Ledger Spire climbed; Val Amort offers restructuring, and the inkstone goes off the desk.
7. Three phases, mutō-dori, and the engine's spine cut. Every seal in the valley goes dark.

At the harvest festival the public registry is carried to the assembly and posted. At the Eastern Torii at dawn, Sekireisai rehangs the dojo's name board. Final exchange:

- Nyaakoto: 「剣は、作る手を守るためにある。」 ("The sword exists to protect the hands that make.")
- Sekireisai: 「……ようやく、一本じゃ。」 ("…At last, a point.")

### 9.1 Campaign calendar (binding for all chapter scripts)

The fiction uses the lunar calendar of 元和九年 (Genna 9, 1623). Solar dates are approximate. They are anchored on Tokugawa Iemitsu's appointment as shogun on 元和九年七月二十七日, 23 August 1623. Genna 9 has a leap month (閏八月) only after the regular 8th month, so ch07 and ch08 fall in the regular 8th month. The dates must be checked by the historian before any release copy quotes them. Characters never name solar dates, and they avoid clock time: they speak in 刻 and in seasonal words.

| Ch | Lunar date (JA) | About (solar) | Season words and sky | Continuity anchor |
|---|---|---|---|---|
| 1 | 元和九年 三月下旬, one day | Late April | 晩春. Wisteria, uguisu; cherries are over | The sky splits at sunset (b13) |
| 2 | Same night into dawn | Late April | Moonlit night, fire | The seed reaches the Hidden Valley at dawn |
| 3 | 四月上旬 (ten days later), dusk to before dawn | Early May | 初夏. The long 4th-month rains, 卯の花腐し, a few weeks before the 五月雨 proper | 「十日で、この有様。」 |
| 4 | 四月中旬 (ten days after ch03) | Mid to late May | 麦秋. Barley harvest, transplanting, fireflies at dusk, a sun-shower (狐の嫁入り) | Seedlings die "in ten days" without water |
| 5 | 六月七日頃, 22:00 to dawn | Early July | Midsummer night, first-quarter moon, thunderstorm | About three weeks before ch06 |
| 6 | 六月晦日, the last night of the 6th month, into 七月一日 | Late July | Moonless night (晦), late summer by the lunar seasons | Pages posted at dawn on the 1st of the 7th month |
| 7 | 八月十一日, one night | Early September | 初秋. A typhoon (locals say 野分 or 大風, never 台風; 二百十日 is not named) | The ship falls on 萱野原 before dawn |
| 8 | 八月十二日, from 寅の刻; festival 八月十五夜; epilogue 八月十六日 at dawn | Early to mid September | Harvest, rice on 稲架, susuki; the festival is the mid-autumn full moon (中秋) | Barley is sown after the rice (二毛作) |

---

## 10. Macro pacing

The mix columns are **minutes** by beat category:

- **C** = combat, duel, boss.
- **E** = explore_optional.
- **S** = stealth_zone.
- **P** = production_task (and mounted cargo delivery is counted under M).
- **M** = horseback_ride.
- **Cin** = cinematic and dialogue.

Targets include typical optional engagement and about 12% retry overhead on Normal, with cinematics watched. A completionist adds about 60–90 min. **Acceptance:** in telemetry, playtest median chapter times fall within ±20% of target and the total falls within 360–480 min.

| Ch | id | Title (JA / EN) | Target min | Beats | C | E | S | P | M | Cin | VO lines | New mechanic | Weapons unlocked (catalog id) | Boss | Horse |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `ch01_dojo` | 道場の修行 / Dojo Apprenticeship | 40 | 13 | 22 | 4 | 0 | 3 | 3 | 8 | 117 | Kamae, 水月 maai ring, guard, awase, 転; yumi draw; mount and dismount; manufacture | 18 和弓, 0 刀 | — (duel: Toranosuke) | Yes (intro ride) |
| 2 | `ch02_invasion` | 異星からの侵略 / The Invasion | 45 | 16 | 17 | 2 | 0 | 9 | 9.5 | 7.5 | 112 | Yari reach vs shields; carry; defend; mounted archery (left arc); convoy escort | 19 槍 | `boss_dunark` | Yes |
| 3 | `ch03_lantern_ward` | 占領された街 / Occupied Streets | 55 | 18 | 14 | 3 | 12 | 15 | 0 | 11 | 143 | Stealth (light, noise, puddles); rear takedown; 峰打ち + seal-cut; escort; arcing explosives | 4 脇差, 7 擲弾筒 | `boss_penalta` | — |
| 4 | `ch04_irrigation` | 田畑の解放 / Agricultural Liberation | 60 | 18 | 13 | 4 | 4 | 21.5 | 8 | 9.5 | 115 | Crank; hold; 早合 reload; kusarigama bind; mounted cargo; mounted boss | 2 鎖鎌, 5 コイル火縄銃 | `boss_hakari` | Yes |
| 5 | `ch05_silk_foundry` | 工房の蜂起 / The Foundry Uprising | 60 | 18 | 19 | 2.5 | 4 | 25 | 0 | 9.5 | 125 | Rhythm manufacture (bellows, forge, loom); furnace hazards; registry and first XOR | 20 薙刀, 8 鍛冶槌, 1 アーク・カービン | `boss_tarifa` | — |
| 6 | `ch06_ledger_vault` | 債務金庫への潜入 / Ledger-Vault Infiltration | 55 | 16 | 14 | 3 | 24 | 4 | 0 | 10 | 143 | Full stealth AI states; nightingale floors; 礫 lure; stealth-hold; **無刀取り** | 3 ニードル短機関銃, 13 幻影短機関銃 (optional, auto-granted ch07), 10 短刀 | `boss_eskro` (duel: Toranosuke) | — |
| 7 | `ch07_flagship` | 異星旗艦への突撃 / Alien Flagship Assault | 50 | 16 | 28 | 2 | 4 | 7 | 0 | 9 | 137 | Energy shields and charged shots; wind drift on arrows; override crank | 9 連発銃, 11 パルス・カービン, 14 プラズマ火縄銃, 16 電撃放射器 | `boss_collatera` | — |
| 8 | `ch08_debt_citadel` | 最後の解放 / Final Liberation | 55 | 18 | 21 | 2 | 0 | 14 | 5 | 13 | 140 | Mounted charge (yari); volley-rank command; arena-seizure hazards; multi-phase finale | 12 単分子薙刀, 17 治癒の槍, 15 小型迫撃砲, 6 金棒 | `boss_val_amort` | Yes (charge) |
| **Σ** | | | **420** | **133** | **148** | **22.5** | **48** | **98.5** | **25.5** | **77.5** | **1,032** | | **21 of 21** | **7 bosses + 2 duels** | **4 chapters** |

Share of total time: combat 35%, production 23%, cinematic and dialogue 18%, stealth 11%, mounted 6%, exploration 5%. Most dialogue beats are walk-and-talk with player control kept. Only lines flagged `blocking` lock control, for at most 20 s.

**VO lines (review, 2026-09-25).** The column now gives the lines actually scripted in the chapter documents: 1,032 bilingual voiced lines in total, every chapter inside the 60–150 band. The original 890 budget counted story lines only; the difference is mostly repeatable barks, retry hints and branch-only lines (for example ch01's win and loss branches), so a single playthrough hears fewer. The beat `target_s` values in the chapter YAML sum to exactly **25,200 s (420 min)**, and every chapter matches its row's category minutes. On-screen tutorial prompts are UI strings and are not counted here.

**Collectibles:** 6 per chapter, 48 in total. They are passive `collectible` beats and are not counted in the beat totals.

| Category | JA | EN | Count |
|---|---|---|---|
| Scroll fragments of Sekireisai's teaching | 伝書の断簡 | Scroll fragment | 8 (one per chapter) |
| Seizure notices (alien documents) | 差押状 | Seizure notice | 11 |
| League chalk marks | 空紋の目印 | League mark | 10 |
| Heirlooms | 家宝 | Heirloom | 11 |
| Registry pages | 生産の記録 | Registry page | 8 |

The counts are those of the eight chapter scripts, reconciled in review; the total stays 48. No heirloom appears twice: Okinu's mother's shuttle is ch06.c04 only, and ch08.c04 is Tamakichi's master's festival mortar.

Rewards are codex entries and visual restoration in the epilogue (returned heirlooms appear in homes). **Collectibles never grant stats.**

---

## 11. Weapon unlocks and campaign loadout

All 21 catalog weapons (IDs 0–20) unlock exactly once across the campaign. The table below is in unlock order, which is beat order (weapon 18 at ch01.b07 comes before weapon 0 at ch01.b12); the chapter scripts match it exactly. The unlocked-weapons mask lives in the local save (L1 save schema 6). **Chapter select** grants the cumulative mask as it stands at that chapter's start. Optional pickups are auto-granted at the next chapter's first supply point, so the mask stays deterministic.

**Campaign unlocks are offline-only.** They never grant multiplayer entitlement. Special weapons (12–17) still require their NFT or the extra `B` bond in P2P play. The campaign never contacts a wallet.

| ID | JA | Reading | EN | Kind | Unlock beat | In-fiction source |
|---|---|---|---|---|---|---|
| 18 | 和弓 | わきゅう | Yumi | bow | ch01.b07 | His bow, taken up at the matoba |
| 0 | 刀 | かたな | Katana | melee | ch01.b12 | Nyaakoto's own blade, returned by Sekireisai after the dojo trials |
| 19 | 槍 | やり | Yari (su-yari) | melee | ch02.b03 | Estate armory rack |
| 4 | 脇差 | わきざし | Wakizashi | melee | ch03.b01 | Carried as a travel short sword (道中差) while disguised |
| 7 | 擲弾筒 | てきだんとう | Grenade Launcher | explosive | ch03.b09 | Tamakichi's hand-mortar packed with festival shells |
| 2 | 鎖鎌 | くさりがま | Kusarigama | melee | ch04.b03 | Otane's; a farm sickle on a chain |
| 5 | コイル火縄銃 | コイルひなわじゅう | Coil Matchlock | hitscan | ch04.b03 | Taemon's bird-scaring village gun with Tetsugorō's coil breech |
| 20 | 薙刀 | なぎなた | Naginata | melee | ch05.b04 | Okinu's |
| 8 | 鍛冶槌 | かじづち | Forge Hammer | melee | ch05.b08 | Kōzō's forge; used in manufacture |
| 1 | アーク・カービン | アーク・カービン | Arc Carbine | hitscan | ch05.b09 | First League-built firearm; SORA mon on the receiver (matches the existing asset) |
| 3 | ニードル短機関銃 | ニードルたんきかんじゅう | Needle SMG | hitscan | ch06.b05 | Given by Iota |
| 13 | 幻影短機関銃 | げんえいたんきかんじゅう | Phantom SMG | hitscan (special) | ch06.b07 (optional; auto at ch07.b01) | Vault armory locker |
| 10 | 短刀 | たんとう | Tantō | melee | ch06.b10 | Toranosuke's pledge |
| 9 | 連発銃 | れんぱつじゅう | Repeater | hitscan | ch07.b01 | Foundry-built, issued at the war council |
| 11 | パルス・カービン | パルス・カービン | Pulse Carbine | hitscan | ch07.b06 | Captured from enforcers |
| 14 | プラズマ火縄銃 | プラズマひなわじゅう | Plasma Matchlock | hitscan (special) | ch07.b08 | Captured from an alien marksman |
| 16 | 電撃放射器 | でんげきほうしゃき | Shock Emitter | hitscan (special) | ch07.b11 | Captured on the bridge approach |
| 12 | 単分子薙刀 | たんぶんしなぎなた | Monofilament Naginata | melee (special) | ch08.b01 | Kōzō and Okinu: alien filament bound to tamahagane |
| 17 | 治癒の槍 | ちゆのやり | Healing Lance | healing (special) | ch08.b01 | Okuzu; small self-heal per catalog, reduced damage |
| 15 | 小型迫撃砲 | こがたはくげきほう | Micro-Mortar | explosive (special) | ch08.b03 | League siege train (Tamakichi) |
| 6 | 金棒 | かなぼう | Kanabō | melee | ch08.b06 | Used to smash the gate's seal anchors |

**Loadout (proposal for L1/L4).** There are five carry slots:

| Slot | Contents |
|---|---|
| 腰 Hip | Katana, always |
| 脇 Side | Wakizashi, tantō, kusarigama or forge hammer |
| 背 Back | Yumi and a 12-arrow ebira, always from ch01 |
| 長柄 Polearm | Yari, naginata, monofilament naginata or kanabō |
| 飛道具 Firearm or explosive | One of 1, 3, 5, 7, 9, 11, 13, 14, 15, 16, 17 |

- Side, Polearm and Firearm choices are changed at League 補給所 (supply points), which are diegetic registry depots, and at checkpoints.
- Enemy weapons can be picked up with limited ammo.
- Current input maps yumi, yari and naginata to keyboard 4/5/6 and cycles them with the right shoulder. L4 will remap the slots.
- **Mounted weapons:** katana (right-side cuts), yari (forward and right thrust), yumi (left arc only). There are no firearms on horseback.

---

## 12. Beat taxonomy (engineering contract)

A chapter is an ordered list of beats in `Content/Data/campaign/chapter_0N.json` (L1, schema 4). The rules live in `SoraBeatRules.h`. Beat events go through `USoraGameEvents`: `beat_started`, `beat_completed`, `beat_failed`, `site_restored`, plus combat events. Telemetry writes per-beat timestamps to `Saved/Telemetry`.

### 12.1 Common fields (all beat types)

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string `chNN.bMM` | yes | Stable. Used by the save checkpoint, telemetry and dialogue line ids. |
| `type` | enum | yes | `combat_wave`, `duel`, `stealth_zone`, `production_task`, `horseback_ride`, `boss`, `dialogue`, `explore_optional`, `collectible`, `cinematic` |
| `place` | place id (§14) | yes | |
| `title_ja`, `title_en` | string | yes | Objective text. The HUD shows JA with an EN subtitle line. |
| `target_s` | int | yes | Pacing target. The sum per chapter must be within ±5% of §10. |
| `checkpoint` | bool | default `true` | Save at beat start. Rule: no more than 6 target-minutes between checkpoints; bosses of 6 min or more also checkpoint per phase on 稽古 and 真剣. |
| `requires` | beat ids | default: previous beat | Explicit gating for parallel optional beats. |
| `optional` | bool | default `false` | Only `explore_optional` and `collectible` may be optional. |
| `unlocks` | `{weapons:[ids], mechanics:[flags]}` | no | Weapons are unique campaign-wide. Mechanic flags: `kamae`, `maai_ring`, `awase`, `marobashi`, `yumi`, `mount`, `mounted_archery`, `yari`, `carry`, `stealth`, `takedown`, `seal_cut`, `hayago_reload`, `crank`, `manufacture`, `tsubute`, `muto_dori`, `shield_break`, `volley_command`. Each flag unlocks once (`manufacture` at ch01.b09). Chapter proposals not yet in this list: `kusarigama_bind` (ch04), `hammer_rhythm` (ch05), `swim` and `climb` (ch06), `charged_shot` and `wind_brace` (ch07). |
| `site` | 0–2 or null | no | Maps to the existing three-sites-per-chapter production mask. Each site is used exactly once. |
| `registry` | `{item_ja,item_en,qty,unit_ja,unit_en}` | no | Registry entry written on completion (§2.3). Only allowed on `production_task` and cargo-mode `horseback_ride`. |
| `dialogue` | `[{on:event, lines:[line ids], mode}]` | no | Events: `beat_start`, `beat_complete`, `volume_enter:<id>`, `site_restored:<n>`, `boss_phase:<n>`, `player_died`, `npc_downed:<id>`, `alert_state:<state>`, `item_delivered:<id>`, `progress_at:<0–1>`, `idle_s:<n>`. |
| `music` | state id | no | L5 stem state. |
| `fail` | `{on, to}` | default `{on:"player_died", to:"checkpoint"}` | |

### 12.2 Type-specific parameters

| Type | Required parameters | Optional parameters / rules |
|---|---|---|
| `combat_wave` | `bounds` (volume); `waves[]`: `{enemies:[{type,count,spawn,patrol?}], trigger}` with trigger `start` / `prev_cleared` / `alive_below:N` / `after_s:N` / `volume_enter:id` / `progress_at:x`; `complete`: `all_waves_cleared` / `{survive_s}` / `{defeat_count}` | `max_alive` (default 6); `allies[] {npc, role, downable:true}`; `nonlethal_types[]` (default `["bound_conscript"]`, never counted as kills); `target_kind` `enemy` / `mato` (training targets) / `pupil` |
| `duel` | `opponent` (npc or boss id); `weapons {player:[ids] or "bokuto" / "fukuro_shinai", opponent}`; `lethal` bool; `scoring`: `{mode:"points", first_to}` / `{mode:"hp"}` / `{mode:"lesson_gates"}`; `ring` (volume) | `lesson_gates[]`: `stance_hold{ms}`, `maai_step{count}`, `front_guard_survive{after_ms}`, `awase{window_ms,count}`, `recovery_complete`, `marobashi_flank{count}`; `finisher` `none` / `muto_dori`; `events[] {at_hp_pct, cinematic?}`; `loss_policy` `retry` / `continue_after:N` (alternate dialogue) |
| `stealth_zone` | `zone` (volume); `guards[] {type, patrol, sight{cone_deg, range_cm, dark_range_cm}, hearing_cm}`; `on_detected`: `combat` / `restart_checkpoint` / `reinforce:<wave>`; `complete`: `exit_reached` / `objectives[]` | `detection {suspicion_rate, alert_threshold, search_s}` (L2 states: unaware, suspicious, alert, search); `takedowns {rear:true, lethal_default}`; `light_sources[]` (extinguishable); `noise_surfaces[]` (`puddle`, `gravel`, `nightingale_floor` with an edge-walk silent strip, `running_water` ×0.5); `lures` (`tsubute`). On Easy, `on_detected` always falls back to `combat`. |
| `production_task` | `task`: `hold` / `escort` / `carry` / `manufacture` / `defend` / `crank`; plus the task block below | `site`, `registry`, `waves[]` (same shape as `combat_wave`), `stealth:true` (progress pauses while any guard has line of sight) |
| · `hold` | `volume`, `hold_s`, `contest` `pause` / `decay`, `decay_per_s` | Interact-hold variant: `interact_points[]`, `per_point_s` |
| · `escort` | `npcs[]`, `path`, `speed_cm_s`, `wait_for_player_cm`, `fail_on_npc_death` | `hide_on_signal` (NPCs crouch and hide on the player's signal), `npc_health`, `down_revive_s` |
| · `carry` | `item`, `count`, `pickups[]`, `dropoffs[]` | `loadout_while_carrying` (default `["katana_one_hand"]`; no bow); `move_speed_mult` (default 0.8, no sprint); `drop_on_hit` |
| · `manufacture` | `recipe`, `stations[]`, `steps[] {kind: heat / hammer_rhythm / bend / paste / assemble / weave_rhythm / quench / inspect, count, timing{beat_ms, tolerance_ms}?}`, `output {item, qty}` | Pass/fail only, with no quality grind; enemy interruptions come from `waves` |
| · `defend` | `targets[] {actor, hp}`, `duration_s` or `waves`, `fail_on_target_destroyed:true` | `repair_interact` |
| · `crank` | `actor`, `turns_required`, `turn_rate_band [min,max] turns/s`, `progress_decay_per_s`, `stamina_per_turn` | `interruptible`, `coop_npc` (NPC cranks slowly when the player leaves) |
| `horseback_ride` | `horse` (`kurimaru` / `arashi` / `pack_horse`); `mode` `travel` / `escort_convoy` / `chase` / `charge` / `cargo`; `route` (spline) or `open{bounds}`; `complete` | `gaits[]`; `weapons` must be a subset of `{0,18,19}` with arcs from §4.2; `convoy {npcs, speed_cm_s, hp}`; `fear {spook_radius_cm, recover_s}`; `horse_stamina`; `auto_steer` (accessibility); `dismount_allowed`; `on_horse_down` `dismount_continue` / `checkpoint`; `cargo {item, qty, dropoffs[], carrier?}` with `registry` (`carrier: pack_horse` when the rider leads a laden pack horse) |
| `boss` | `boss` (bosses.json id), `arena` (volume + lock), `phases[] {hp_pct_start, pattern_table, adds?, arena_mod?}`, `defeat` `kill` / `disarm` / `destroy_weakpoints` / `capture` | `intro_cinematic`, `outro_cinematic`, `checkpoint_per_phase`, `telegraph {palette, min_windup_ms}`, `barks[] {on, line}` (captioned audio telegraphs) |
| `dialogue` | `lines[] {id, speaker, ja, en, audio?, register}`, `trigger`, `mode` `ambient` / `blocking` / `radio` | `priority`, `interrupt` `queue` / `cut`, `camera` `none` / `soft_lookat`. Blocking lasts at most 20 s. Lines never repeat unless `repeatable`. `radio` means an **off-screen voice** not attached to a visible actor (a call from a rooftop, the master calling from another yard, a memory). Only the paired message slates (Iota's key-slate and the slate from ch05.b18) and alien PA take a device filter; no local owns a radio in 1623. |
| `explore_optional` | `volume`, `pois[] {id, kind: lore / vista / cache / npc / challenge}` | `rewards[]` (collectible ids, arrows, pickups); **no map markers**; the space is discoverable by light, sound and paths; `exit_hint_after_s` |
| `collectible` | `collectible_id`, `category` (§10), `place`, `mask_bit`, `codex {ja, en}` | Passive. Registered per chapter but not sequenced. |
| `cinematic` | `sequence` (Level Sequence path), `duration_s`, `skippable:true`, `subtitles[]` | `fallback: "camera_blend"` (letterboxed in-engine camera until C9 Sequencer lands); `end_state {player_transform, equipped}` |

### 12.3 Validation rules (for `validate_content.py`, owned by L1)

1. Every chapter's `target_s` sum is within ±5% of §10, and the campaign total is within 21 600–28 800 s.
2. Each chapter uses sites 0, 1 and 2 exactly once. Their order follows the beats' `requires` chain; `requires_sites` in the data must agree (ch08 completes site 1 before site 0).
3. Across the campaign, every weapon id 0–20 appears in exactly one `unlocks`, and the unlock beats are in the order given in §11 (compare beat ids, not table rows or weapon ids). Weapons unlocked in the same beat (ch04.b03: 2, 5; ch08.b01: 12, 17) may appear in either order. An optional pickup's auto-grant (`x_auto_grant_if_missed`, ch06.b07 → ch07.b01) is not a second unlock.
4. Every `boss` id exists in `bosses.json`. Every `muto_eligible` attack appears only in bosses and duels whose `defeat` or `finisher` allows mutō-dori.
5. `horseback_ride.weapons` ⊆ {0, 18, 19}. Only `mode:"cargo"` may carry `registry`.
6. Every dialogue line has non-empty `ja` and `en` and a speaker in `dialogue_speakers`. EN reading speed is at most 17 cps.
7. `nonlethal_types` never contribute to `defeat_count`.
8. Checkpoint spacing is at most 360 target-seconds. Per-phase checkpoints inside a boss or duel with `checkpoint_per_phase: true` count (a duel's phases are its `events`, as in ch06.b09's 50% event). With that rule every chapter passes; the largest gap is 360 s.

### 12.4 Example (excerpt from `ch04_irrigation`)

```json
{
  "chapter": "ch04_irrigation",
  "beats": [
    {
      "id": "ch04.b06", "type": "production_task", "task": "crank",
      "place": "pl_otameike", "title_ja": "一の堰を開けよ", "title_en": "Open the First Weir",
      "target_s": 240, "checkpoint": true, "site": 0,
      "crank": { "actor": "sluice_winch_01", "turns_required": 12, "turn_rate_band": [0.4, 1.2],
                 "progress_decay_per_s": 0.05, "stamina_per_turn": 6, "interruptible": true },
      "waves": [ { "enemies": [ { "type": "enforcer_rifle", "count": 3, "spawn": "sp_dam_north" } ],
                   "trigger": "progress_at:0.25" },
                 { "enemies": [ { "type": "drone", "count": 2, "spawn": "sp_reservoir_air" } ],
                   "trigger": "progress_at:0.6" } ],
      "registry": { "item_ja": "用水", "item_en": "Irrigation water", "qty": 12, "unit_ja": "枚", "unit_en": "paddies" },
      "dialogue": [ { "on": "beat_start", "lines": ["ch04.b06.otane.001"], "mode": "ambient" },
                    { "on": "progress_at:0.5", "lines": ["ch04.b06.taemon.002"], "mode": "ambient" } ]
    },
    {
      "id": "ch04.b14", "type": "horseback_ride", "mode": "cargo", "horse": "kurimaru",
      "place": "pl_shimomura", "title_ja": "麦を三つの集落へ", "title_en": "Deliver barley to three hamlets",
      "target_s": 300, "route": "spl_aze_loop",
      "cargo": { "item": "barley_sheaf", "qty": 30, "dropoffs": ["hamlet_kami", "hamlet_naka", "hamlet_shimo"],
                 "carrier": "pack_horse" },
      "weapons": [0, 18], "fear": { "spook_radius_cm": 900, "recover_s": 2.5 }, "auto_steer": "setting",
      "on_horse_down": "dismount_continue",
      "registry": { "item_ja": "麦", "item_en": "Barley", "qty": 30, "unit_ja": "束", "unit_en": "sheaves" }
    },
    {
      "id": "ch04.b16", "type": "boss", "boss": "boss_hakari", "place": "pl_shimomura",
      "title_ja": "査定機「秤」を倒せ", "title_en": "Bring down the Assessor Engine",
      "target_s": 480, "arena": { "volume": "vol_paddies_boss", "lock": true },
      "phases": [ { "hp_pct_start": 100, "pattern_table": "hakari_mounted" },
                  { "hp_pct_start": 55, "pattern_table": "hakari_mill", "adds": "drone_pair", "arena_mod": "dismount" } ],
      "checkpoint_per_phase": true, "defeat": "destroy_weakpoints",
      "barks": [ { "on": "pattern:sweep_beam", "line": "ch04.b16.margina.003" } ]
    }
  ]
}
```

### 12.5 Data conventions for the chapter YAML (ratified in review)

The eight chapter scripts were written in parallel and drifted apart. In review they were normalized to the conventions below; L1's importer and `validate_content.py` can rely on them.

- **YAML dialect.** Blocks parse as YAML 1.1 (PyYAML) and 1.2 (Ruby Psych). The key `on` must be quoted (`"on":` or `'on':`): YAML 1.1 reads a bare `on`, `off`, `yes` or `no` as a boolean. ch05 had 85 bare `on:` keys that loaded as `True`; they are now quoted.
- **Required top-level keys:** `chapter` (the chapter id string), `title_ja`, `title_en`, `map`, `target_s`, `beats`, `collectibles`, `lines`, and `ui_prompts` when the chapter has HUD prompts. Other top-level keys are informational: chapter metadata, or proposals for another lane's file (bosses, enemies, layout), which carry an `x_` prefix where they were renamed.
- **Beat keys.** Only the §12.1 and §12.2 fields appear unprefixed. Every chapter proposal starts with `x_` (ch05 groups its proposals in one `x_ext` block per beat). The earlier `_proposal` suffix (ch02) and bare extension keys (ch04, ch06, ch08) were renamed.
- **Line records** in `lines`: `id`, `speaker`, `ja`, `en`, `register`, `duration_s` (never `dur_s`), plus optional `mode`, `repeatable`, `readings`, `audio`. The trigger lives in the beat's `dialogue` entry, not on the line. A `dialogue`-type beat may carry its lines inline under `lines[]` (§12.2), as ch01 (25 lines) and ch05.b04 (9 lines) do; every other line is in the top-level `lines`.
- **Line ids:** `chNN.bMM.<token>.<nnn>`. The token is the character's lowercase short name (`nyaakoto`, `sekireisai`, `toranosuke`, `oyuki`, `kohagi`, `kozo`, `okinu`, `tetsugoro`, `otane`, `taemon`, `tokichi`, `tamakichi`, `okuzu`, `iota`, `valamort`, `dunark`, `penalta`, `margina`, `tarifa`, `eskro`, `collatera`) or a generic role (`enforcer`, `resident`, `drone` …); the `speaker` field holds the speaker id (§6). `nnn` is unique within the beat; most chapters number all lines in beat order, ch06 numbers per token. `chNN.b00.*` is a chapter-wide bark pool.
- **Collectibles:** `collectible_id` is `chNN.cMM`; `mask_bit` is chapter-local 0–5. If L1 keeps one 48-bit mask, the global bit is (chapter − 1) × 6 + `mask_bit`.
- **HUD prompts** in `ui_prompts`: `{id, beat, "on"?, ja, en}`. They are UI strings, not voice lines, and do not count toward the VO budget. Id styles differ by chapter (`ch01.b02.prompt.01`, `ui.ch04.b02.bank_roads`, `hud.ch06.swim_dive` …); they only need to be unique.
- **Text style** is set in §18.

---

## 13. Chapter beat outlines

The Min column is target minutes. `site n` refers to the chapter's production-site mask bit. The catalog anchor lines already in `catalog.json` are placed as noted in §20.

### ch01_dojo: 第一章 道場の修行 (40 min)

| Beat | Type | Place | Min | Content / key parameters |
|---|---|---|---|---|
| ch01.b01 | cinematic | pl_tsumagizaka_dojo | 2.0 | Dawn 素振り. Title card with the vermillion SORA seal. The camera passes the 名札掛け (name board) with Nyaakoto's and Toranosuke's plaques. |
| ch01.b02 | duel (lesson) | pl_tsumagizaka_dojo | 4.0 | vs Sekireisai with bokutō. Gates: `stance_hold 600`, `maai_step ×3` (水月 ring). Unlocks `kamae`, `maai_ring`. site 0 (間合いの稽古場). |
| ch01.b03 | duel (lesson) | pl_tsumagizaka_dojo | 4.0 | vs Matsukichi, then Takemaru (two scored bouts, so catalog site 1's "two pupils" and `requires_kills: 2` hold). Gates: `front_guard_survive after 350`, `awase 260 ×2`, `recovery_complete`. Unlocks `awase`. site 1 (木刀の試合場). |
| ch01.b04 | duel (lesson) | dojo yard | 3.0 | vs Matsukichi, then Takemaru. Gate: `marobashi_flank ×2`. Unlocks `marobashi`. |
| ch01.b05 | dialogue (ambient) | dojo veranda | 1.5 | Toranosuke introduced. Baiō asleep in the sunbeam; the pupils bow around him. |
| ch01.b06 | horseback_ride (travel) | pl_umaya → pl_matoba | 3.0 | Tacking up (kura, abumi, tazuna called out). Kurimaru refuses the bit until offered barley. Walk and trot the estate lane. Unlocks `mount`. |
| ch01.b07 | combat_wave (`target_kind: mato`) | pl_matoba | 5.0 | Simplified 射法: 6 shots at a 尺二的 (36 cm target) at 28 m, 4 hits required. Then 3 swinging straw targets at 40–60 m. Unlocks weapon 18, `yumi`. |
| ch01.b08 | explore_optional | pl_issoseki_wood | 4.0 | The One-Claw Stone legend. Vista of distant Nekoyama. 2 collectibles (scroll fragment 1, league mark). |
| ch01.b09 | production_task (manufacture) | pl_dojo_smithy | 3.0 | 矢矯め: straighten 6 shafts (heat → bend-check ×6), then refletch. Quiver restocked to 12. Registry 矢 12本. site 2 (道場の鍛冶場). |
| ch01.b10 | dialogue (ambient) | estate veranda | 1.5 | Sekireisai on 殺人刀 and 活人剣. Toranosuke challenges Nyaakoto; his house's debt is hinted at. |
| ch01.b11 | duel | pl_estate_day courtyard | 6.0 | vs Toranosuke, `fukuro_shinai`, first to 3 points, feints. `loss_policy: continue_after:3`. |
| ch01.b12 | dialogue (blocking) | estate | 1.0 | The katana is returned: 「刀は民から預かるものじゃ」. Unlocks weapon 0. |
| ch01.b13 | cinematic | estate | 2.0 | Dusk. The sky splits and cold cyan lights descend. The 半鐘 alarm bell rings. |

### ch02_invasion: 第二章 異星からの侵略 (45 min)

| Beat | Type | Place | Min | Content / key parameters |
|---|---|---|---|---|
| ch02.b01 | cinematic | pl_estate_night | 2.0 | Ships descend. Debt seals clamp onto the kura. The Credit House proclamation is read. |
| ch02.b02 | combat_wave | 長屋門 gate | 4.0 | 3 waves: `enforcer_rifle` ×6, `blade_retainer` ×2. Pupils fight as downable allies. Katana and yumi. |
| ch02.b03 | combat_wave | pl_bugugura | 3.0 | Unlock 19 at start. `shield_enforcer` ×2 and `enforcer_rifle` ×3: yari reach against the shield edge. Unlocks `yari`. |
| ch02.b04 | dialogue (blocking) | estate | 1.0 | Sekireisai: save the seed and the people. 「種は明日の田じゃ。」 |
| ch02.b05 | production_task (carry) | 蔵 | 4.0 | Pry the granary seal off with the yari's iron butt (3 s interact under fire). Carry 種籾俵 ×4 to two pack horses (one 駄 of two bales each), katana one-handed. Registry 種籾 4俵. site 0 (蔵の債務封印). Unlocks `carry`. |
| ch02.b06 | production_task (defend) | 蔵前 | 3.0 | Defend the 2 laden pack horses (HP 400 each) for 150 s against drop-pod waves, including a `grenadier`. |
| ch02.b07 | cinematic | back gate | 1.0 | The pack-horse string departs, the groom riding 乗掛 on the lead horse; Nyaakoto mounts Kurimaru. |
| ch02.b08 | horseback_ride (escort_convoy) | pl_kaido | 6.0 | 1.2 km spline; convoy at 450 cm/s. `drone` ×10 in 4 groups. Mounted yumi fires to the left only. Fear radius near beams. Unlocks `mounted_archery`. |
| ch02.b09 | combat_wave | pl_ishibashi | 4.0 | On foot: `enforcer_rifle` ×6, `grenadier` ×1, `marksman` ×1 on the far bank. Flanking route through the stream ford. |
| ch02.b10 | horseback_ride (travel) | pl_kaido | 2.0 | Grey pre-dawn. Quiet stretch into the valley. |
| ch02.b11 | production_task (carry) | pl_kakuredani | 2.0 | Hand out rice (separate food rice, never the seed) from the pack loads to 3 family shelters. Registry 食糧 36食. site 1 (食糧の配給所). |
| ch02.b12 | dialogue | pl_kakuredani | 1.0 | Kohagi: the estate is burning and the master stayed. |
| ch02.b13 | horseback_ride (travel) | pl_kaido | 1.5 | Return gallop under an ember-lit sky. |
| ch02.b14 | explore_optional | burning estate wings | 2.0 | Rescue a trapped pupil (optional). Seizure notice and heirloom collectibles. |
| ch02.b15 | boss | estate courtyard | 6.0 | `boss_dunark` (§8). |
| ch02.b16 | cinematic | estate → valley | 2.5 | Sekireisai is lifted away as 担保. Val Amort appears. At dawn, artisans set up the valley workshop. site 2 (屋敷の工房, relocated to the valley in fiction). |

### ch03_lantern_ward: 第三章 占領された街 (55 min)

| Beat | Type | Place | Min | Content / key parameters |
|---|---|---|---|---|
| ch03.b01 | cinematic | pl_horiwari | 2.0 | 高瀬舟 riverboat in the rain; Kohagi poles. Commoner disguise; katana and yumi are hidden with the League. Unlocks weapon 4. |
| ch03.b02 | stealth_zone | pl_horiwari wharf | 4.0 | `drone` ×2 sweeping. Puddles are loud; andon lamps can be put out. `on_detected: combat`. Unlocks `stealth`. |
| ch03.b03 | stealth_zone | pl_kido | 4.0 | Ward gate: `bound_conscript` ×3 and `enforcer_rifle` ×2. Rear takedown; 峰打ち + seal-cut. Unlocks `takedown`, `seal_cut`. |
| ch03.b04 | explore_optional | pl_ura_nagaya | 3.0 | Well-side gossip, children's chalk SORA marks, glowing balance doors. 2 collectibles. |
| ch03.b05 | production_task (carry) | pl_ura_nagaya well | 4.0 | Recover the cache from the dry well; katana and yumi are re-equipped. Carry 3 tool crates to Tōkichi. site 0 (道具の隠し場). |
| ch03.b06 | dialogue | hideout | 1.0 | Tōkichi and Tamakichi. |
| ch03.b07 | production_task (escort) | backstreets | 5.0 | Escort 4 craftspeople past 3 patrols, with `hide_on_signal`. |
| ch03.b08 | combat_wave | pl_chochin_kobo yard | 4.0 | Discovered: `enforcer_rifle` ×5, `blade_retainer` ×2, `grenadier` ×1. NPCs shelter indoors. |
| ch03.b09 | production_task (manufacture) | pl_chochin_kobo | 3.0 | Bend bamboo ribs → paste washi → oil. Tamakichi packs shells. Unlocks weapon 7. Registry 提灯 40張. site 1 (提灯の工房). |
| ch03.b10 | stealth_zone | pl_kosatsuba | 4.0 | Plant a shell charge on the debt terminal. `marksman` on a roof, a drone, 3 patrols. `on_detected: reinforce`. |
| ch03.b11 | cinematic | pl_kosatsuba | 1.5 | The terminal blows. The door numbers go dark, and residents step out into the rain. |
| ch03.b12 | dialogue | pl_kosatsuba | 1.5 | Oyuki introduced: 「彼らの"信用"は、借りとして生まれるのです。」 ("Their 'credit' is born as debt.") |
| ch03.b13 | cinematic | nagaya meeting room | 2.0 | 一味神水; the circular oath sheet around the SORA mon. The League is founded. |
| ch03.b14 | production_task (hold) | communal kitchen | 3.0 | Keep the fires and serving line open for 120 s while a patrol probes. Registry 炊き出し 120食. site 2 (共同の炊き出し). |
| ch03.b15 | cinematic | wharf | 1.5 | Toranosuke in a grey haori beside Penalta. |
| ch03.b16 | combat_wave | streets → wharf | 4.0 | Pursuit: `marksman` ×2 on roofs, `enforcer_rifle` ×6. Grenade arcs. |
| ch03.b17 | boss | pl_chochin_gashi | 6.0 | `boss_penalta`. |
| ch03.b18 | cinematic | Lantern Ward | 1.5 | Lanterns relit, now painted with the SORA mon. Oyuki: next, the fields. |

### ch04_irrigation: 第四章 田畑の解放 (60 min)

| Beat | Type | Place | Min | Content / key parameters |
|---|---|---|---|---|
| ch04.b01 | cinematic | 庄屋屋敷 | 2.0 | Taemon: the reservoir is sealed, water is sold by the measure, and the unplanted rice was bought on credit (青田買い). |
| ch04.b02 | horseback_ride (travel) | pl_shimomura | 3.0 | Scouting along the aze dikes with Otane. Patrols are marked. |
| ch04.b03 | dialogue | 庄屋屋敷 | 1.5 | Village gun rebuilt → weapon 5; Otane's kusarigama → weapon 2. Unlocks `hayago_reload`. |
| ch04.b04 | combat_wave | barley fields | 5.0 | Collection patrol: `enforcer_rifle` ×8, `blade_retainer` ×2, `drone` ×2. Tall barley blocks sight both ways. |
| ch04.b05 | stealth_zone | reservoir guard post | 4.0 | Non-lethal route past `bound_conscript` guards; a drone patrols over the water. `on_detected: combat`. |
| ch04.b06 | production_task (crank) | pl_otameike | 4.0 | Sluice winch, 12 turns (see §12.4). site 0 (水路の取水口). Unlocks `crank`. |
| ch04.b07 | production_task (hold) | pl_otameike | 4.0 | Hold 90 s while the water rises, against waves including `shield_enforcer` ×2. |
| ch04.b08 | cinematic | canals | 1.5 | Water runs down the channels and the paddies mirror the sky. Planting begins. |
| ch04.b09 | explore_optional | pl_tanada | 4.0 | Terraces and the 水分社 (Mikumari water-god shrine). Vista. 2 collectibles. |
| ch04.b10 | production_task (escort) | aze roads | 4.0 | Escort the ox-cart carrying carpenters and paddles to the mill. |
| ch04.b11 | production_task (manufacture) | pl_suisha_goya | 3.0 | Replace 6 paddles → seat the axle → release the brake. Registry 水車 1基. site 1 (田畑の水車). |
| ch04.b12 | production_task (defend) | paddies | 4.0 | Defend the planting line (8 downable planters) for 150 s against drone seizure nets. |
| ch04.b13 | dialogue | paddies | 1.0 | Oyuki opens the 生産改帳; first entries. |
| ch04.b14 | horseback_ride (cargo) | pl_gogura → 3 hamlets | 5.0 | Nyaakoto on Kurimaru leads the pack mare Bunta (荷鞍, 振り分け loads), delivering 3 × 10 sheaves. Registry 麦 30束. |
| ch04.b15 | cinematic | distribution point | 1.5 | Hakari strides out of the haze and seizes the barley. |
| ch04.b16 | boss | pl_shimomura + pl_suisha_goya | 8.0 | `boss_hakari` (mounted P1, on foot P2). |
| ch04.b17 | production_task (carry) | pl_gogura | 2.5 | Return the seized barley and record it. site 2 (収穫の分配所). |
| ch04.b18 | cinematic | paddies, dusk | 2.0 | Fireflies. Otane joins the League. Toranosuke watches from a ridge on Arashi. |

### ch05_silk_foundry: 第五章 工房の蜂起 (60 min)

| Beat | Type | Place | Min | Content / key parameters |
|---|---|---|---|---|
| ch05.b01 | cinematic | pl_silk_foundry | 2.0 | Quota board at 140%. Collared workers. The 「昼寝禁止」 notice. |
| ch05.b02 | stealth_zone | pl_kanna_nagashi | 4.0 | Iron-sand channels; running water halves footstep noise. |
| ch05.b03 | production_task (escort) | pl_itotoriba → refuge | 5.0 | Seal-cut 6 collared workers and escort them to the refuge. site 0 (職人の避難所). |
| ch05.b04 | dialogue | refuge | 1.5 | Okinu (weapon 20). Kōzō: 「三晩かかる。今夜しかない。」 ("It takes three nights. We have tonight.") |
| ch05.b05 | combat_wave | pl_hataba | 5.0 | Loom-hall uprising with artisan allies. Naginata reach is obstructed by looms. |
| ch05.b06 | production_task (crank) | pl_takadono | 4.0 | Foot-bellows rhythm held inside `turn_rate_band`; flame color works as a temperature gauge. site 1 (絹と鋼の炉). |
| ch05.b07 | production_task (defend) | pl_takadono | 5.0 | Defend the furnace (HP) and Kōzō for 180 s. Grenadiers target the furnace. |
| ch05.b08 | production_task (manufacture) | pl_okaji | 4.0 | Forge Hammer (weapon 8): heat → `hammer_rhythm {600 ±90 ms}` → quench. 24 arrowheads; quiver refilled. Registry 鏃 24本. (`manufacture` is already unlocked at ch01.b09; the rhythm variant's flag `hammer_rhythm` is a proposal.) |
| ch05.b09 | production_task (manufacture) | pl_okaji | 3.0 | With Tetsugorō: barrel + alien coil + SORA receiver plates. Unlocks weapon 1. Registry アーク・カービン 3挺. |
| ch05.b10 | combat_wave | foundry yard | 3.0 | Test-fire against the counterattack. |
| ch05.b11 | production_task (manufacture) | pl_hataba | 2.0 | Okinu's 高機: `weave_rhythm` to make the SORA nobori. Registry 絹幟 1旒. |
| ch05.b12 | cinematic | pl_aratamejo | 2.5 | **First XOR:** three-party inspection and the split 割符 (§2.2). site 2 (生産の記録台). |
| ch05.b13 | explore_optional | foundry storehouse | 2.5 | Levy ledgers, an heirloom, collectibles. |
| ch05.b14 | cinematic | pl_imonoba | 1.5 | Tarifa opens the channels as the storm breaks. |
| ch05.b15 | combat_wave | pl_imonoba | 4.0 | Molten hazard volumes; `loom_automaton` ×4 and enforcers. |
| ch05.b16 | boss | pl_takadono catwalks | 7.0 | `boss_tarifa`. |
| ch05.b17 | production_task (carry) | yard | 2.0 | Load finished goods onto pack horses bound for Lantern Ward and the League. |
| ch05.b18 | cinematic | foundry, dawn | 2.0 | The nobori is raised. Iota's message arrives. |

### ch06_ledger_vault: 第六章 債務金庫への潜入 (55 min)

| Beat | Type | Place | Min | Content / key parameters |
|---|---|---|---|---|
| ch06.b01 | cinematic | moat edge | 2.0 | Iota's hologram map. Oyuki: 「燃やさず、写しなさい。」 ("Copy it. Do not burn it.") |
| ch06.b02 | stealth_zone | pl_citadel_moat | 4.0 | Swim under searchlights, with dives of 8 s maximum. Enter through the old water gate. |
| ch06.b03 | stealth_zone | pl_ishigaki | 3.0 | Climb the 算木積み corner at authored holds while a sentry watches from the yagura. |
| ch06.b04 | stealth_zone | pl_relay_room | 4.0 | Disable the relay during sweep gaps; alert states taught. site 0 (監視の中継器). |
| ch06.b05 | dialogue | archive annex | 2.0 | Iota in the crate. Weapon 3 and the key-slate. |
| ch06.b06 | stealth_zone | pl_ledger_corridors + pl_uguisu_hall | 6.0 | `auditor` ×6, `enforcer_rifle` ×4, `drone` ×2. Nightingale floor (the edge strip is silent). Unlocks `tsubute`. |
| ch06.b07 | explore_optional | vault armory | 3.0 | Weapon 13 (optional pickup). Heirloom collectibles. |
| ch06.b08 | production_task (hold, `stealth:true`) | ledger desks | 4.0 | Copy the master ledger at 3 desks × 30 s; progress pauses under any guard's line of sight. site 1 (債務の帳簿). |
| ch06.b09 | duel | pl_archive | 7.0 | vs Toranosuke with real steel. Event at 50%: his family's page. `finisher: muto_dori`. Unlocks `muto_dori`. |
| ch06.b10 | dialogue | pl_archive | 1.5 | 「毎月払った。増えた。」 ("I paid every month. It grew.") The tantō is pledged: weapon 10. |
| ch06.b11 | stealth_zone | pl_press_hall | 4.0 | Jam 3 presses (4 s interact each) unseen. site 2 (金庫の印刷機). |
| ch06.b12 | cinematic | vault | 1.5 | Blackout. Eskro wakes. |
| ch06.b13 | boss | pl_vault_core | 7.0 | `boss_eskro`. |
| ch06.b14 | stealth_zone | water gate | 3.0 | Exfiltrate with Toranosuke and Iota as the gate floods. |
| ch06.b15 | dialogue | moat bank | 1.0 | Oyuki reads the numbers. |
| ch06.b16 | cinematic | Lantern Ward kōsatsu | 2.0 | Pages are posted at dawn and people read their own balances. The flagship's shadow passes. |

### ch07_flagship: 第七章 異星旗艦への突撃 (50 min)

| Beat | Type | Place | Min | Content / key parameters |
|---|---|---|---|---|
| ch07.b01 | cinematic | pl_kakuredani | 2.0 | War council. Weapon 9 issued, plus weapon 13 if missed in ch06. |
| ch07.b02 | combat_wave | pl_anchor_bastion | 4.0 | Typhoon. League teppō allies against `enforcer_rifle` ×10 and `marksman` ×2. Cut the ground signal relay. site 0 (地上の通信塔). |
| ch07.b03 | cinematic | cargo lift | 1.5 | Rice-bale stowaways: 「くしゃみ、するな。」 |
| ch07.b04 | stealth_zone | pl_cargo_hold | 4.0 | Move among seized goods tagged by the aliens. |
| ch07.b05 | explore_optional | pl_seized_vault | 2.0 | The dojo's seized name board (heirloom) and collectibles. |
| ch07.b06 | combat_wave | pl_reckoning_engine | 4.0 | Energy shields introduced. Weapon 11 from enforcers. Unlocks `shield_break`. |
| ch07.b07 | production_task (crank) | pl_reckoning_engine | 4.0 | Manual override wheel reverses the extraction lift, sending goods down. Registry 押収品 返還 (seized goods returned). site 1 (収奪の動力炉). |
| ch07.b08 | combat_wave | pl_hangar | 4.0 | Weapon 14 from a marksman; `shield_enforcer` ×2. |
| ch07.b09 | dialogue (radio) | pl_hangar | 1.0 | Iota over the slate; Toranosuke's riders are gathering below. |
| ch07.b10 | combat_wave | pl_hull_ridge | 4.0 | Wind gusts push movement and drift arrows; `drone` ×8. |
| ch07.b11 | combat_wave | bridge approach | 4.0 | Weapon 16; `shield_enforcer` ×3. |
| ch07.b12 | cinematic | pl_bridge | 1.5 | Collatera offers a "survival loan"; Nyaakoto refuses. |
| ch07.b13 | boss | pl_bridge | 8.0 | `boss_collatera`. |
| ch07.b14 | production_task (hold) | pl_bridge | 3.0 | Hold the evacuation beacon and helm trim for 60 s under waves. site 2 (脱出の信号機). |
| ch07.b15 | cinematic | falling ship | 2.0 | The ship is steered onto empty hills; the cargo-sled leap. |
| ch07.b16 | dialogue | crash edge | 1.0 | Toranosuke's riders arrive. Val Amort: 「全担保を回収する。」 |

### ch08_debt_citadel: 第八章 最後の解放 (55 min)

| Beat | Type | Place | Min | Content / key parameters |
|---|---|---|---|---|
| ch08.b01 | cinematic | pl_kakuredani, dawn | 2.5 | Council under SORA sashimono. Weapons 12 and 17 unlocked. |
| ch08.b02 | horseback_ride (charge) | pl_causeway | 5.0 | Charge with 20 League riders; mounted yari thrusts; `seizure_walker` beams to dodge. |
| ch08.b03 | combat_wave | pl_outer_bailey | 4.0 | Command the rotating volley ranks. Weapon 15. Unlocks `volley_command`. |
| ch08.b04 | production_task (defend) | field forge (野鍛冶) | 3.0 | Defend the forge and aid station for 150 s. Registry 修理 道具 (tools repaired). site 1 (共同の修理工房). |
| ch08.b05 | production_task (carry) | wall line | 2.0 | Carry rations and 早合 to 3 pinned squads. |
| ch08.b06 | combat_wave | pl_otemon | 4.0 | Weapon 6. Smash 3 gate seal anchors under fire. |
| ch08.b07 | production_task (escort) | pl_collateral_cells | 4.0 | Free the prisoners and escort them to the gate. site 0 (住民の避難所). |
| ch08.b08 | cinematic | pl_collateral_cells | 2.0 | Sekireisai: 「遅かったのう。」 |
| ch08.b09 | dialogue | pl_collateral_cells | 1.0 | He stays to guard the refugees, unarmed (無刀). |
| ch08.b10 | combat_wave | pl_ledger_spire | 4.0 | Vertical interior fights. |
| ch08.b11 | production_task (crank) | spire freight lift | 3.0 | Winch the lift with League engineers while fending off attackers. |
| ch08.b12 | explore_optional | hall of seized heirlooms | 2.0 | Final scroll fragment: Sekireisai on katsujinken. |
| ch08.b13 | cinematic | pl_ledger_engine | 2.0 | The restructuring offer; the inkstone. |
| ch08.b14 | boss | pl_ledger_engine | 9.0 | `boss_val_amort`, with a checkpoint at each phase. |
| ch08.b15 | cinematic | montage | 2.5 | Every seal goes dark: granary, sluice, foundry, Lantern Ward. |
| ch08.b16 | production_task (carry) | pl_lantern_ward_festival | 2.0 | Carry the public registry through the festival crowd and post it at the assembly. No combat. site 2 (解放の集会所). |
| ch08.b17 | dialogue | pl_higashi_torii | 1.5 | The name board is rehung; the final exchange (§9). |
| ch08.b18 | cinematic | pl_higashi_torii, dawn | 1.5 | Credits. Val Amort counting barley. |

---

## 14. Places and levels

**Arena reuse:** 0 Nyaagyu Estate, 1 Lantern Ward, 2 Silk Foundry, 3 Debt Citadel. **Campaign-only geometry lives in chapter layout data and sublevels. It must never change arena collision** used by practice or multiplayer (C2 builds arena collision from kernel data). New spaces come from C3 kits.

| Ch | Place id | JA (reading) | English | Source | Notes |
|---|---|---|---|---|---|
| 1 | pl_tsumagizaka_dojo | 爪木坂道場 (つまぎざかどうじょう) | Tsumagizaka Dōjō | Estate sublevel (existing `NyaagyuDojo` source) | Interior and yard |
| 1 | pl_estate_day | 猫柳生の屋敷・昼 (ニャーギュウのやしき) | Nyaagyu Estate, day | **Arena 0** | Duel courtyard |
| 1 | pl_umaya | 厩 (うまや) | Stable | Estate sublevel | Horse and tack hero set |
| 1 | pl_matoba | 的場・安土 (まとば・あづち) | Archery range | New, small | 28 m and 60 m lanes |
| 1 | pl_issoseki_wood | 一爪石の森 (いっそうせきのもり) | One-Claw Stone Wood | New, small | Optional |
| 1 | pl_dojo_smithy | 道場の鍛冶場 (どうじょうのかじば) | Dojo smithy | Estate sublevel | |
| 2 | pl_estate_night | 猫柳生の屋敷・夜 | Nyaagyu Estate, night/fire | **Arena 0** (lighting variant) | Fire dressing is non-colliding |
| 2 | pl_bugugura | 武具蔵 (ぶぐぐら) | Armory yard | Estate sublevel | |
| 2 | pl_kaido | 猫柳生街道 (ニャーギュウかいどう) | Nyaagyu Highway | New linear, about 1.5 km | Packed-earth and gravel forest road about 2 間 wide, stones only on steep pitches (Hakone's 石畳 dates from 1680); roadside 石仏, wooden 道しるべ |
| 2 | pl_ishibashi | 石橋の関 (いしばしのせき) | Stone Bridge Checkpoint | New | Granite slab-beam bridge (石桁橋), never an arch: Japan's oldest stone arch, Nagasaki's 眼鏡橋, dates from 1634. Ford flank |
| 2 | pl_kakuredani | 隠れ谷 (かくれだに) | Hidden Valley | New hub | League camp; revisited in ch07 and ch08 briefings; the registry lives here |
| 3 | pl_horiwari | 堀割 (ほりわり) | Canal approach | New | 高瀬舟 dock |
| 3 | pl_lantern_ward_rain | 提灯街・雨 (ちょうちんまち) | Lantern Ward, dusk rain | **Arena 1** | |
| 3 | pl_ura_nagaya | 裏長屋 (うらながや) | Back tenements | Arena 1 extension | |
| 3 | pl_kido | 木戸 (きど) | Ward gate | Arena 1 edge | |
| 3 | pl_chochin_kobo | 提灯の工房 (ちょうちんのこうぼう) | Lantern workshop | Interior | |
| 3 | pl_kosatsuba | 高札場 (こうさつば) | Notice-board square | Arena 1 centre | Existing `StreetDebtTerminal` asset |
| 3 | pl_chochin_gashi | 提灯河岸 (ちょうちんがし) | Lantern Wharf | New | Boss arena, with crane |
| 4 | pl_shoya_yashiki | 庄屋屋敷 (しょうややしき) | Headman's house | Sub-place of pl_shimomura | Proposed by ch04 (b01, b03) |
| 4 | pl_shimomura | 下村 (しもむら) | Lower Village fields | New open area, about 800 × 600 m (C3) | Accessed from the Arena 0 lower gate |
| 4 | pl_otameike | 大溜池・一の堰 (おおためいけ・いちのせき) | Great Reservoir and First Weir | New | Existing `NyaagyuSluice`, `NyaagyuWaterCourt` sources |
| 4 | pl_tanada | 棚田・水分社 (たなだ・みくまりのやしろ) | Terraces and water shrine | New | Optional |
| 4 | pl_suisha_goya | 水車小屋 (すいしゃごや) | Waterwheel mill | New | |
| 4 | pl_gogura | 郷蔵 (ごうぐら) | Village granary | New | |
| 5 | pl_kanna_nagashi | 鉄穴流し (かんなながし) | Iron-sand channels | New | |
| 5 | pl_silk_foundry | 絹の工房 (きぬのこうぼう) | Silk Foundry | **Arena 2** | |
| 5 | pl_itotoriba | 糸取場 (いととりば) | Reeling shed | Arena 2 interior | |
| 5 | pl_hataba | 機場 (はたば) | Loom hall | Arena 2 interior | Existing `SilkFoundryLoom` |
| 5 | pl_takadono | 高殿 (たかどの) | Tatara hall | New interior | Boss catwalks |
| 5 | pl_okaji | 大鍛冶場 (おおかじば) | Refining forge | Interior | |
| 5 | pl_aratamejo | 改め所 (あらためじょ) | Inspection hall | Interior | First XOR |
| 5 | pl_sumigoya | 炭小屋 (すみごや) | Charcoal shed (the refuge) | Arena 2 edge | Proposed by ch05 (b03, b04) |
| 5 | pl_toritategura | 取立蔵 (とりたてぐら) | Levy storehouse | Interior | Proposed by ch05 (b13) |
| 5 | pl_imonoba | 鋳物場 (いものば) | Casting floor | Interior | Molten hazards |
| 6 | pl_citadel_moat | 堀と水門 (ほりとすいもん) | Moat and water gate | **Arena 3** exterior, fog | |
| 6 | pl_ishigaki | 石垣 (いしがき) | Castle ramparts | Arena 3 exterior | |
| 6 | pl_relay_room | 中継器室 (ちゅうけいきしつ) | Relay room | New (C3 vault kit) | |
| 6 | pl_ledger_corridors | 帳簿回廊 (ちょうぼかいろう) | Ledger corridors | New (C3 vault kit) | |
| 6 | pl_uguisu_hall | 鶯張りの廊下 (うぐいすばりのろうか) | Nightingale-floor hall | New | Surviving old castle palace |
| 6 | pl_archive | 記録庫 (きろくこ) | Archive | New | Duel |
| 6 | pl_press_hall | 印刷所 (いんさつじょ) | Press hall | New | |
| 6 | pl_vault_core | 金庫核 (きんこかく) | Vault core | New | Boss, darkness |
| 7 | pl_anchor_bastion | 錨台 (いかりだい) | Tether anchor bastion | **Arena 3** (storm variant) | |
| 7 | pl_cargo_hold | 貨物倉 (かもつそう) | Cargo hold | New (C3 flagship kit) | |
| 7 | pl_seized_vault | 押収品倉 (おうしゅうひんそう) | Seized-goods vault | New | Optional |
| 7 | pl_reckoning_engine | 算術機関室 (さんじゅつきかんしつ) | Reckoning engine | New | |
| 7 | pl_hangar | 格納庫 (かくのうこ) | Hangar | New | |
| 7 | pl_hull_ridge | 外殻の稜線 (がいかくのりょうせん) | Hull ridge | New exterior | Above the storm |
| 7 | pl_bridge_approach | 艦橋前通路 (かんきょうまえつうろ) | Bridge approach | New | Proposed by ch07 (b11) |
| 7 | pl_bridge | 艦橋 (かんきょう) | Bridge | New | Boss |
| 7 | pl_kayanohara | 萱野原 (かやのはら) | Kaya Moor, the crash site | New exterior | Proposed by ch07 (b15, b16) |
| 8 | pl_causeway | 猫山の土手道 (ねこやまのどてみち) | Nekoyama causeway | New ride space | |
| 8 | pl_outer_bailey | 外郭 (がいかく) | Outer bailey | **Arena 3** | |
| 8 | pl_otemon | 大手門 (おおてもん) | Main gate | Arena 3 | |
| 8 | pl_collateral_cells | 担保牢 (たんぽろう) | Collateral cells | New | |
| 8 | pl_ledger_spire | 帳簿塔 (ちょうぼとう) | Ledger Spire | New vertical | |
| 8 | pl_ledger_engine | 帳簿機関 (ちょうぼきかん) | Ledger Engine summit | New | Final boss |
| 8 | pl_lantern_ward_festival | 提灯街・秋祭り | Lantern Ward, harvest festival | **Arena 1** (festival variant) | |
| 8 | pl_higashi_torii | 東の鳥居 (ひがしのとりい) | Eastern Torii | Arena 1 edge | Existing `ToriiLacquer`, `NyaagyuToriiFootStudy` |

Map index change against catalog schema 3: ch08's primary space moves from arena 1 to **arena 3**, and arena 1 is used for the epilogue.

---

## 15. Environmental art direction (photoreal AAA)

Photoreal is non-negotiable (user directives 11, 13, 14, 17). No stylized fallback ships.

**Admission rule:** an asset enters the campaign only after it passes the [photoreal acceptance](../art-direction/photoreal-acceptance.md) gates:

- A packaged fixed-camera A/B comparison.
- A recorded license.
- A measured frame cost on both platforms.

Free assets are allowed only when their licenses allow it (for example the existing CC0 Poly Haven palette). Restricted-redistribution assets stay out of the public repo.

### 15.1 Global palette and material library

- **The core contrast is warm and hand-made against cold and extruded.**
  - Warm: weathered timber, urushi lacquer, silk, washi, rain-soaked stone, lantern light at 1800–2200 K.
  - Cold: alien graphite, black glass, and emissive "ledger lines" in cyan at 7000–9000 K.
- **League accents:** 朱 vermillion, 藍 indigo, gold leaf on the mon. **Cyan never appears on League objects.**
- **Telegraph readability:** amber telegraphs must stay distinguishable from lantern light. Use saturated animated edge decals with a pulse, not static warm glows, and provide an accessible palette.
- **Master material families.** PBR ranges are guidance and must be checked against measured references.

| Material | JA | Notes |
|---|---|---|
| Weathered timber | 杉 / 檜 / 欅 | UV-silvered grain, end-grain checks, iron nail stains. Dry roughness 0.6–0.85; wet 0.2–0.35 with albedo darkened about 25–35% by a wetness mask. |
| Hinoki floor | 檜の床 | Pale, polished by feet, darker oiled edges. |
| Urushi lacquer | 漆 (黒 / 朱) | Clear-coat. New roughness 0.15–0.35; wear-through to 木地 at edges and handles. |
| Washi and shōji | 和紙 / 障子 | Measured transmission for lanterns and shōji; fiber must not repeat (the current study fails this gate). |
| Silk | 絹 | Anisotropic sheen; shot-silk hue shift for the nobori. |
| Kawara roof tile | 燻し瓦 | Silver-black, roughness 0.35–0.5, non-metallic. The house-mon 軒丸瓦 end tiles carry the SORA mon (existing `NyaagyuSoraEaveCapStudy`). |
| Plaster | 漆喰 | Lime plaster; rain streaks and hairline cracks. |
| Granite | 花崗岩 | Wet and dry states; moss in joints. |
| Packed earth | 土 | Streets and dikes, with puddles. Edo streets are **packed earth**, not paving; stone appears only at bridges, steps and wharves. |
| Thatch | 茅葺 | Farmhouses. |
| Iron | 鉄 | Forged versus cast finishes. |
| Alien | — | Micro-engraved graphite, black glass with thin-film tint, brushed titanium, emissive ledger numerals. |

- **Platforms:**
  - Windows: Nanite for static architecture and terrain, and MegaLights for lantern-dense scenes.
  - Mac: conventional LODs, software Lumen, card fur, and no more than 8 shadow-casting dynamic lights per view, with lanterns beyond that as emissive washi plus unshadowed lights.
  - Mesh Terrain and Lumen probe inclusion: follow [mesh-terrain-nyaagyu.md](../mesh-terrain-nyaagyu.md).
- **Texel density:** hero set pieces 1024 px/m; mid-ground 512 px/m. Metric scale throughout.

### 15.2 Per-location direction

**ch01: Estate, dojo, range and wood**

- **Tsumagizaka Dōjō:**
  - Structure: 入母屋 roof in ibushi kawara, 欅 pillars, hinoki floor, 羽目板 walls, 連子窓 slatted windows throwing raking bars of light and dust motes.
  - Fittings: 神棚, 刀掛け, and the 名札掛け with brush-lettered plaques.
  - Kamon: a SORA-mon 幕 curtain behind the master's seat.
  - Storytelling: the worn-smooth sunbeam spot on the veranda.
- **Stable (umaya):**
  - Tack hero set: lacquered kura on a stand, abumi, cloth tazuna, crupper, and straw umagutsu hanging on pegs.
  - Surroundings: 飼葉桶 feed trough, 藁, dust in shafts of light.
- **Matoba:**
  - Structure: sand 安土 under a small roof, 尺二的 targets, 矢道 lawn, 射場 shed with 弓立て racks.
  - Details: arrows show real fletching and nock detail.
- **One-Claw Stone Wood:**
  - A cedar forest floor of moss and ferns (the fern-contact gate applies) around a 3 m boulder split cleanly in two, with a small 注連縄 rope and offerings.
  - Morning mist.
- **Estate day (Arena 0):**
  - 長屋門, 土塀 (existing `NyaagyuEstateWall`), 蔵 (existing `NyaagyuKura`/`KuraFront`), 露地 garden (existing `NyaagyuIntegratedRoji`), the stone path (existing scan).
  - **Gates.** The arena's two `SM_Nyaagyu_ToriiGate` frames read as shrine torii, and a torii marks a shrine, not a samurai residence. In campaign mode, dress them as 冠木門 (two posts and a tie-beam), or a 薬医門 for the inner gate, without changing collision. Real torii appear only at shrines (the ch02 roadside shrine, ch04's 水分社, ch08's Eastern Torii).

**ch02: Estate at night, highway, bridge, Hidden Valley**

- **Estate fire variant:**
  - Fire: burning roof sections (non-colliding), falling embers, volumetric smoke lit from below, charring decals.
  - Invaders: cyan debt seals clamped onto the kura doors, humming and casting cold light onto the plaster; alien drop-pod scars in the courtyard.
- **Nyaagyu Highway:** packed-earth and gravel forest road (cedar and cypress) with stones only on steep pitches, roadside 石仏 with moss and offerings, votive stone lanterns at shrine paths, a ridge vista toward the burning estate.
- **Stone Bridge:** a granite slab-beam bridge (not an arch; see §14) over a rocky stream. The alien checkpoint is prefabricated graphite barriers with scanning gates; the contrast is the point.
- **Hidden Valley:**
  - A narrow wooded valley with a waterfall and a charcoal-burner's huts.
  - League camp: 陣幕 curtains with the SORA mon, pack saddles (荷鞍) and tethered pack horses, rice bales, the workshop under a lean-to.
  - The registry desk: 帳面, 矢立, and 割符 tallies in a box.

**ch03: Lantern Ward**

- **Architecture:** early-17th-century 町家 with 格子 lattices, 暖簾 carrying shop marks, 卯建 firewalls, board or kawara roofs with stone weights on the poorer ones, 長屋 tenements, and 溝板-covered gutters on **packed-earth** streets.
- **Lanterns:** collapsible bamboo-rib 提灯 and 行灯 at shopfronts, 辻行灯 at crossings.
- **Invader dressing:**
  - Glowing cyan balance numerals on every door.
  - Credit House leaflets pasted over shop signs; locals reuse them as lantern paper (restrained humor).
  - The `StreetDebtTerminal` replacing the notice boards at the 高札場.
- **League marks:** chalk SORA marks low on the walls (children's height) that grow bolder through the chapter.
- **Canal and wharf:**
  - 石積み embankments, 高瀬舟 moored, bales and crates, a timber crane with rope and pulley (the boss interaction).
  - Rain rings on the water; lantern reflections stretched by the ripples.
- **Lantern workshop:** rib-bending jigs, washi stacks, brush pots, oil jars, half-finished lanterns hanging from the rafters.

**ch04: Lower Village**

- **Landscape:**
  - Flooded rice paddies (mirror water) beside **golden barley** (麦秋): the early-summer double-cropping picture.
  - Earthen 畦 dikes with grass; 棚田 terraces with dry-stone risers.
  - 用水路 with 石積み and wooden 樋 flumes.
- **Structures:**
  - The reservoir weir with its hand-cranked timber and stone sluice (existing `NyaagyuSluice`), wearing an alien meter and seal.
  - An undershot 水車 with an overgrown millrace.
  - 茅葺 farmhouses with 土間 and 囲炉裏.
  - A 郷蔵 on stone footings.
  - The 水分社 small shrine with a vermillion torii.
- **Details:** hanging 稲架 poles stored for autumn; frogs; herons; fireflies at dusk.
- **Invader dressing:** meter posts on every channel billing water "by the measure."
- **League marks:** the SORA mon is painted on the sluice once it is freed.

**ch05: Silk Foundry (Arena 2 plus interiors)**

- **Tatara hall (高殿):**
  - A tall timber hall around a waist-high clay furnace rebuilt for each smelt.
  - Iron-sand piles, charcoal stacks.
  - Foot-trodden bellows. The seesaw 天秤鞴 is later (c. 1690s); **do not use it**.
  - Slag, glowing tuyères, soot-black rafters.
- **Refining forge (大鍛冶):** anvils, quench tubs, tongs racks.
- **Loom hall (機場):** 高機 looms (existing `SilkFoundryLoom`), indigo vats, silk skeins, cocoons and mulberry leaves in the reeling shed.
- **Inspection hall:** a long table, scales, soroban, the registry, a box of tallies and the SORA brand iron.
- **Invader dressing:** a quota board at 140%, levy meters on each loom, the 「昼寝禁止」 notice.
- **Kamon progression:** the silk SORA nobori woven in-scene becomes the League's main banner.

**ch06: Debt Citadel and Ledger Vault**

- **Exterior:**
  - The old 石垣 in 打込接ぎ masonry with 算木積み corners; 櫓 turrets still standing.
  - The alien black-glass spire grafted on, with seamless extrusions biting into the stone.
  - Moat with reeds.
- **Surviving palace:** 鶯張り (nightingale) corridors of dark polished floor, fusuma panels partly stripped, paintings shrouded in alien plastic.
- **Vault interior:**
  - Endless cold aisles of glass ledger slates, each glowing a household's number.
  - Polished basalt floors, condensation, breath vapor, a deep low hum.
- **Press hall:** ranks of presses stamping debt notes on paper made from seized washi.
- **Vault core:** near-black; Eskro's pulses visualized as a subtle refractive ring.
- **The only warm light** is the copied ledger's candle under the player's control. Treat it as a stealth risk.

**ch07: The flagship 『複利号』**

- **Silhouette:** a long, hammerhead-like hull of graphite plates engraved with ledger lines.
- **Cargo hold:** Nyaagyu's goods in warm materials under cold light: rice bales, lacquer chests, silk bolts, swords and armor all tagged with glowing alien labels.
- **Reckoning engine:** a rotating ring of glass abaci.
- **Hangar:** alien shuttles.
- **Hull ridge:** exterior above a moonlit cloud sea, with rain bands below and lightning inside the clouds.
- **Bridge:** a cold amphitheatre facing a window over Nyaagyu.

**ch08: Causeway, citadel siege, spire, festival**

- **Morning after the typhoon:** washed-clean air, a golden rice harvest below, smoke from the siege.
- **League host:** SORA sashimono and nobori everywhere, jingasa bearing the mon.
- **Siege:** ladders, the field forge under a 陣幕.
- **Collateral cells:** austere, with people treated as inventory (tags); dignity is preserved in how they are staged.
- **Ledger Spire:** vertical, cold, precise.
- **Summit:** the Ledger Engine's ring above the clouds at sunrise.
- **Festival (Arena 1 variant):** thousands of lanterns (MegaLights on Windows), food stalls, children with SORA-mon paper fans, the returned heirlooms displayed.
- **Eastern Torii at dawn:** vermillion 丹塗 lacquer on the existing torii source.

---

## 16. Lighting and weather by chapter

| Ch | Season / time (in fiction) | Sky and key light | Weather and FX | Special lighting notes | Mac fallback |
|---|---|---|---|---|---|
| 1 | Late spring, dawn → dusk | Overcast morning, soft sky about 6500 K, sun about 5200 K through thin cloud → golden 3800 K late afternoon | Morning mist in the wood; dust motes indoors | Raking light through the renjimado; final shot: cold 8000 K cyan descending into a warm sunset | Software Lumen; limit dust particles |
| 2 | Same night | Moonlight fill about 4100 K; firelight key 1800–2200 K with flicker | Fire, embers, volumetric smoke, wind | Alien searchlights at 8500 K cutting the smoke | Fewer shadowed fire lights; emissive smoke cards |
| 3 | Early-summer rains of the 4th month (卯の花腐し), dusk rain (blue hour) | Ambient sky about 9000 K; lanterns 1900 K | Steady rain, eave drips, puddle rings, low fog | Wet surfaces carry the image: Lumen reflections on Windows, SSR on Mac. MegaLights for 60+ lanterns (Windows). | At most 8 shadowed lanterns per view; the rest emissive |
| 4 | Early summer day → dusk | Hazy sun 5600 K, high humidity height-fog → golden dusk | Passing sun-shower (狐の嫁入り) mid-chapter; heat shimmer; fireflies at dusk | Mirror paddies need stable reflections; barley needs wind animation | Reduce foliage density; card barley LODs |
| 5 | Midsummer night | Furnace key about 1600 K; andon fill | Sparks, smoke, soot; thunderstorm late; steam where rain meets iron | Lightning flashes respect the flash-reduction setting | Cap spark counts; baked emissive furnace |
| 6 | New moon, late summer night | No moon; exterior lit only by cold alien light and fog | Thick fog outside; condensation inside | Interior 7000–9000 K with deep blacks; the player's only warm source is the candle | Fog as height fog only |
| 7 | Early-autumn typhoon night | Lightning-lit storm below; moonlit cloud sea above (4100 K) | Horizontal rain, gusts (gameplay wind), lightning | Ship interior cold, low-key strip lights | Simplify volumetric clouds; skybox cloud sea |
| 8 | Autumn dawn after the typhoon → festival night → dawn | Low clear sun 3500 K → 5000 K, long shadows | Dew, siege smoke; festival: clear starry night | Festival lantern field (MegaLights); final dawn at the torii | Lantern clusters as emissive cards |

---

## 17. SORA kamon usage

The source is the exact user-supplied SVG (`Content/SourceArt/UI/sora_logo_NOtext2.svg`, SHA-256 `d66413a7…0910`), imported from its **two original paths** and never redrawn (see [sora-kamon-runtime-art.md](../sora-kamon-runtime-art.md)).

**The House of Nyaagyu's mon is the SORA logo.** The Credit House bans and seizes it, and the League takes it up as its banner.

| Surface | Treatment | First appears |
|---|---|---|
| House and dojo | 幕 curtain, 軒丸瓦 roof end-tiles (raised ceramic), 名札掛け header | ch01 |
| Nyaakoto's armor | Sode, dō (existing runtime skin placements) | ch02 |
| Horse tack | Abumi front plate, crupper fittings | ch01 |
| League marks | Chalk and charcoal on walls, growing bolder chapter by chapter | ch03 |
| League oath | Centre of the circular oath sheet | ch03 |
| Lanterns | Painted on relit 提灯 | ch03 |
| Freed infrastructure | Painted on the sluice gate and waterwheel | ch04 |
| XOR tallies | Brand across the 割符 split; seal on registry entries | ch05 |
| Silk nobori | Woven white-on-indigo (染め抜き style) | ch05 |
| Firearms | Arc Carbine receiver cheeks (existing asset) | ch05 |
| Jingasa, sashimono, nobori | Painted or dyed on League ashigaru and cavalry | ch08 |
| **UI** | Objective marker (small mon); save indicator (slowly rotating mon); chapter title cards carry the mon as a vermillion 朱印 seal beside brush-calligraphy titles; registry screen; menu backgrounds | all |

**Alien iconography** is a separate "ledger sigil": a closed ring of tally notches. It must not resemble the SORA mon or any real-world bank mark. Aliens **never** display the SORA mon.

---

## 18. Language, subtitles and voice

- **Japanese is primary:** all VO and all UI are in Japanese. English subtitles are on by default. A same-language Japanese caption option is available for accessibility.
- **Line ids:** `chNN.bMM.<speaker>.<nnn>`. Each line carries `ja`, `en`, `speaker`, `register` and `audio`. VO is not recorded yet (catalog `voice_over: not_recorded`), and casting native Japanese actors is a human dependency (B7).
- **Subtitles:**
  - At most 2 lines. EN is at most 42 characters per line and 17 cps; JA captions are at most 16 full-width characters per line (to be confirmed by the native reviewer).
  - Minimum 1.0 s on screen.
  - The speaker name is shown in both scripts.
  - Boss barks are always captioned, because they are telegraphs.
- **Translation voice:**
  - Samurai speech becomes measured, slightly formal English: "I will," not "I'll."
  - Kamigata-flavored speech becomes warm colloquial English, never a caricatured dialect.
  - Alien jargon becomes corporate English ("Per the terms," "your outstanding balance," "non-performing").
- **Honorifics:** keep 様/殿/先生 as meaning rather than transliteration. Sekireisai is addressed as 「先生」 and subtitled "Sensei."
- **Dialogue triggers** are event-based (§12.1). This replaces the absolute-timed lines and their 45 s cap.
- **Japanese text style (normalized in review):**
  - Full-width 「！」 and 「？」, never ASCII. When the sentence continues after them, a full-width space follows: 「網や！　動かれへん！」.
  - Ellipsis 「……」 (two three-dot characters), dash 「——」, quotes 「」 and 『』 for titles.
  - Pupils address Nyaakoto as 「ニャーコト殿」; everyone addresses the master as 「先生」.
  - Period units in voice (間, 里, 刻, 石, 俵, 駄, 文); metric only in the HUD.
  - Alien speech keeps its modern finance vocabulary; locals never use it except when quoting the aliens.
  - Kamigata and Yamato colour stays light and early-modern: 〜や, あかん, 〜とる, ええ, and なされ as the polite imperative. Later Osaka merchant forms (なはれ, まっせ, あきまへん) are not used. The negative 〜へん is later Edo; it is tolerated as colour in Otane's and the villagers' lines until the native reviewer (B7) decides. Okinu's Kyoto speech (〜どす, 〜おす, 〜しまへん) is a character register and is kept.
- **English text style:** the ellipsis is the single character 「…」, never three periods. Samurai (Nyaakoto, Sekireisai, Toranosuke, Oyuki) and aliens never use contractions; commoners, craftspeople and Kohagi may.
- **Register vocabulary.** The `register` field is a casting note, and the chapters use these families (aliases in brackets): `archaic_samurai` [mentor_archaic, archaic_memory]; `samurai_restrained` [jidaigeki_restrained, samurai_plain, samurai_polite, samurai_formal, jidaigeki_plain, jidaigeki_polite, jidaigeki_formal]; `brash_samurai` → `humbled_samurai` [rival_brash, rival_clipped, rival_humbled, samurai_brash_humbled, formal_samurai]; `young_samurai`; `elder_samurai`; `business_keigo`; `terse` [terse_report, scout_terse]; `manual_keigo`; `kyoto_soft`; `kamigata_bright` / `kamigata_cheerful` / `kamigata_commoner`; `yamato_elder` / `yamato_gruff` / `yamato_rural`; `blunt_artisan` [kansai_blunt, artisan_blunt]; `artisan_gentle` [gentle_artisan]; `alien_corporate_keigo` [alien_corporate, corporate_keigo, alien_corporate_bark, corporate_keigo_bark]; `alien_device` / `alien_device_pa` / `announcement_keigo`; `inscription`; `proclamation`; `child`; `work_song`. Suffixes such as `_raised`, `_whisper` or `_strained` are delivery notes. L1 maps the aliases on import.
- **Canon lines that break register.** Six catalog lines are plain-form in speakers whose register is formal or soft: Val Amort's ch02 line 2, ch06 line 2 (staged as an engraved inscription) and ch08 line 3; Collatera's ch07 line 2 (「〜やろう」); Okinu's ch05 line 1; and Oyuki's ch05 line 2. The scripts stage each as a deliberate break and give a register-true alternative. Changing the text is a `catalog.json` decision for L1 after native review (B7).

---

## 19. Period-accuracy checklist (early 17th century)

**Use:**

- 当世具足; daishō worn edge-up.
- 袋竹刀 and bokutō; 高札場; 木戸 ward gates.
- 高瀬舟 (river opened in the early 1610s).
- Fireworks: tradition dates Ieyasu's fireworks viewing to 1613.
- 通し矢 long-distance archery craze (from the 1600s), usable as an optional challenge.
- Nightingale floors: the Nijō palace corridors are the best-known example.
- 竜骨車; undershot waterwheels; 郷蔵; 庄屋 (Kinai usage).
- 早合; 馬沓; soroban.
- Printed arithmetic primers (e.g. the 1622 『割算書』).
- 一味神水 and 起請文 oaths; 陣笠 with mon; 幟; 旗指物.

**Flagged stretch:** the circular 傘連判状 oath sheet is attested mainly in later Edo uprisings. It is used deliberately for the League's founding image and needs historian sign-off.

**Avoid:**

- 招き猫 (a much later Edo motif), a tempting cat-themed anachronism.
- Ukiyo-e posters.
- 小田原提灯 and other later lantern forms as hero props.
- 火の見櫓 and 広小路 (post-1657 fire-safety urbanism).
- The tenbin-fuigo (1690s).
- The theatrical black ninja suit.
- Paved town streets.
- Glass windows.
- Named later firework houses (鍵屋, 玉屋) as businesses. Tamakichi is an independent maker.
- Presenting the "three-rank volley" as established fact. Call it "rotating volley ranks."

---

## 20. Mapping to current data and open items

**Current catalog (schema 3) against this bible.** Each chapter's three `sites` map to beats in §13. All 24 are used:

| Ch | site 0 | site 1 | site 2 |
|---|---|---|---|
| 1 | b02 | b03 | b09 |
| 2 | b05 | b11 | b16 (relocated to the valley) |
| 3 | b05 | b09 | b14 |
| 4 | b06 | b11 | b17 |
| 5 | b03 | b06 | b12 |
| 6 | b04 | b08 | b11 |
| 7 | b02 | b07 | b14 |
| 8 | b07 | b04 | b16 |

In ch08 the site order no longer matches the catalog order (0 → b07, 1 → b04, 2 → b16). L1 must either reorder `requires_sites` or renumber the sites.

**Catalog anchor lines.** The 25 existing cues are canon and are placed as follows:

| Ch | Lines → beat |
|---|---|
| 1 | Lines 1–3 → b02 and b12 |
| 2 | Line 1 → b01; line 2 (banker) → b16; line 3 (samurai) → b15 intro |
| 3 | Line 1 → b02; line 2 → b06 (speaker `lantern_maker`); line 3 → b18 |
| 4 | Lines 1 and 3 → b01 and b17; line 2 → b06 |
| 5 | Line 1 → b04 (`weaver`); lines 2–3 → b12 (line 2 speaker changes `scout` → `leader`) |
| 6 | Line 1 → b01; line 2 → b12 (staged as the vault's engraved inscription in Val Amort's recorded voice); line 3 → b15 |
| 7 | Line 1 → b01; lines 2–3 → b12 (line 2 speaker changes `banker` → `boss_collatera`) |
| 8 | Line 1 → b01 (`foundry_master`); line 2 → b15; line 3 → b13; line 4 → b17 (`scout`) |

All 25 are used verbatim in JA and EN in the chapter scripts (checked in review).

The prototype's absolute `start_s` timings are replaced by event triggers.

**Owner hand-offs.** This bible does not edit data files.

| Owner | Takes from this bible |
|---|---|
| L1 | Chapter ids, beat lists, `target_s`, the unlock mask order (§11), new speaker ids, site remaps |
| L2 | Enemy ids (§7), `nonlethal_types`, stealth surfaces |
| L3 | Seven boss pattern tables (§8) |
| L4 | Loadout slots, registry screen, title-card seal |
| L5 | Music states and captioned barks |
| C2/C3 | Places (§14) and art direction (§15–16) |
| C4 | Missions (§13) |
| C9 | Cinematic ids (every `cinematic` beat, plus boss intros and outros) |

**Open items and reviews.**

1. Native Japanese review of every name, reading and register (B7).
2. Historian and practitioner review of the fictional school's motions, archery, tack, armor and the §19 stretches.
3. Playtest verification of the 7 h target through telemetry. Target minutes are estimates until measured.
4. Equine animation review, including the lateral gait.
5. Sign-off that the monetary boundary in §2 is sufficient for release copy.
6. Catalog-line register decisions (§18): keep the six plain-form canon lines as staged breaks, or adopt the register-true alternatives given in the chapter scripts.
7. Historian confirmation of the §9.1 calendar and of the flags collected in the chapter scripts: 一本 as a scoring word in 1623; the 名札掛け; the tall permanent 高殿 and tatara in Yamato; the 座繰り reel; the circular oath sheet; mounted spear use; festival fireworks scale.
8. Data follow-ups for L1: the ch08 site chain (1 → 0 → 2); ch06 kill quotas set to 0 (no-kill run).

**Review log (C1 lead, 2026-09-25).** The eight chapter scripts were reviewed against this bible, and the fixes are in the files:
- ch03's script tables had been garbled by a generator bug (the notes column spliced into each row, and 26 rows lost); §3.3 was rebuilt from the chapter's YAML.
- ch05's YAML loaded 85 `on:` keys as boolean `True`; they are now quoted.
- Field names, collectible ids and mask bits, and line-id tokens were normalized (§12.5), and all JA and EN punctuation now follows §18.
- Continuity fixes: the §9.1 calendar (ch03's rains are the 4th-month 卯の花腐し, not 五月雨); Takemaru's capture (ch08); pack horses instead of carts, a slab bridge and a packed-earth highway (ch02); re-dressed estate gates; the duplicated heirloom (ch06 and ch08); weapon-table order; and Tetsugorō's first person.
- Line fixes: 「先に三本」 for 「三本勝負」 (ch01); 太刀 for 刃 on wooden swords (ch01); 「ニャーコト殿」 (ch08); 三文 (ch08); and English contractions removed from samurai lines (ch06).
