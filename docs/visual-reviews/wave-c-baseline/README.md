# Wave C rendered baseline: packaged Mac, 1920×1080

**Verdict: the game is nowhere near the photoreal AAA target.** These 43
frames come from the packaged Mac game on 2026-09-27 JST, rendered by Metal at
1920×1080 under the Mac graphics preset. The front end is readable and fully
bilingual. The HUD shows the objective, subtitles, boss telegraphs, the kill
feed, the scoreboard and the results. The 3D world, however, is a prototype.
Characters are toy-like, the horse is built from primitive shapes, most
spaces are boxes with one stretched texture, and several scenes are
underexposed silhouettes or lit against a flat white void. The frames are a
baseline for later A/B comparison. They do not approve any art.

The frames are unedited. [frames.tsv](frames.tsv) lists each file's SHA-256,
its beat, and what the capture harness recorded when it saved the frame.
Every frame in the set was viewed before it was committed.

## How they were made

- **Package.** `Local/Packages/mac-capture-harness5/SoraArena.app`
  (gitignored), a Development build signed ad hoc under bundle id
  `org.sora.soraarena`. Its game executable (sha256 `029eaacc…2bfd9`) was
  built from this commit's `Source/SoraArena/Private/SoraCaptureAutomation.cpp`
  on top of `139508f`. Because only that harness file changed, the package is
  the rebuilt `Binaries/Mac/SoraArena.app` cloned whole. Every other file in
  it has the same SHA-256 as the earlier harness package, except the
  executable and the `Info.plist` build number (`…0.13` → `…0.14`). That
  includes `SoraArena-Mac.utoc` and `.pak` (`1173fdaf…`), the cooked content
  of the green package `mac-capture-green`. The package was not restaged:
  free disk (20–25 GiB) was below the 32 GiB floor set for staging and
  cooking.
- **Rendering.** The frames are real Metal rendering through
  `-RenderOffscreen` at `-ResX=1920 -ResY=1080`, never `-NullRHI`, on the
  Apple M1 Ultra. The preset renders at a 75% screen percentage (1440×810)
  and upscales with TSR (`r.AntiAliasingMethod=4`). Lumen global
  illumination and reflections are on (`r.DynamicGlobalIlluminationMethod=1`,
  `r.ReflectionMethod=1`). Nanite and virtual shadow maps are off.
- **No Nanite on this Mac.** The log says "To use SM6 on this system, please
  ensure you are running Mac OS 15. Falling back to SM5". The machine runs
  macOS 27.0, so that message is misleading. UE 5.8.3 enables SM6 on macOS
  only on Apple8-family GPUs (M2 or later; `MetalRHI.cpp`, the
  `bSupportsSM6` check). The M1 Ultra is Apple7, so it always runs
  `METAL_SM5`, and Nanite and virtual shadow maps cannot appear in any frame
  from this machine.
- **Command.**
  `SORA_MIN_FREE_GIB=19 SORA_CAPTURE_IDLE_WAIT=3600 scripts/toolchain/capture-packaged-mac.sh Local/Packages/mac-capture-harness5 Saved/PackagedCapture/full5`
  The free-space guard was lowered because the disk had 20 GiB free. The run
  made two launches. The `frontend` launch ran
  `SoraArena.UIRendered.FrontEndScreens` (19 screens; 1 of 1 passed). The
  `capture` launch ran `SoraCapture`: 8 campaign chapters and 4 practice
  arenas, 12 of 12 passed with no errors and no warnings. Together they saved
  61 frames at 1920×1080. The script ended with `PASS`. Its logs, index,
  frame list and profiles are in `Saved/PackagedCapture/full5` (gitignored).

The harness continues the campaign from checkpoints it seeds on a throwaway
save slot; the player's save is never read or written. It moves the hero to a
working distance from which nothing blocks his view of the beat's subject
(an opponent, a guard, a boss in a telegraph, the task, the horse, or the
road from the saddle), faces it, and saves the frame with its HUD. The world
is paused from the moment the harness sees what the shot is for until the
frame is written, so the telegraph or fight it recorded is the one drawn. In
practice it plays a zero-stake match with the hero on the kernel's bot
policy against Veteran bots, measures frame time, and saves the fight, the
held scoreboard and the results table.

## Harness fixes in this run

The first run (`full1`, 2026-09-26) missed three shots and left two capture
artifacts. All of them are fixed, and a shot that misses what it is for now
fails its test instead of warning.

- **C1_13_SkySplits** failed because `ch01.b13` keeps no checkpoint. The
  harness now seeds the checkpoint of the dialogue beat before it
  (`ch01.b12`). The hero walks to that beat's trigger and presses E, the
  seven lines play out in real time, and the cinematic begins. The frame
  shows it on its card.
- **C5_01_SilkFoundry** showed beat 2 because the harness pressed Enter a
  second time after the round began, which skips a cinematic. A cinematic
  beat is now checked on its card, not in live play. The harness waits for
  the cinematic's first subtitle and checks that the view is the
  cinematic's own camera.
- **C6_13_EskroTelegraph** showed no telegraph. Eskro hunts by ear, and the
  hero stood still. The harness now walks him sideways while a blind boss has
  not heard him. After two frames Eskro heard him and began 連爪 / CLAW
  FLURRY.
- **The CSV profiler's frame counter** no longer appears in any frame. After
  each measured window the harness waits until the profile has stopped and
  its file is written.
- **Framing.** The hero no longer faces an opponent through a box (C5_05 is
  back in the set). Nor is he placed on a ledge or table above the floor his
  subject stands on, or at arm's length from a stealth guard (C7_04, now
  about 10 m). Dunark's head is no longer behind the boss panel (C2_15).
  In C3_17 and C4_16 no side at 12 m gave a clear line to both the boss's
  head and legs, and frames.tsv says so. The boss is still in full view in
  both frames.

## What the frames show

Recurring art problems:

- **Characters.** The cats have oversized spherical heads, paws and
  shoulders, flat single-colour robes and a box chest plate with a teal
  "screen" (the alien side). The armoured tabby model worn by the dojo
  opponent (C1_02), Toranosuke (C6_09) and a practice ally (A3) has a
  stretched photo texture on its head and a stiff, arms-out pose. Bosses
  hold a long bar straight across the frame (C2_15, C6_13). See also C2_02,
  C5_05 and A2.
- **The horse.** Kurimaru is built from cylinders, spheres and boxes with a
  box saddle (C1_06). From the saddle the rider sees a box head with two cone
  ears (C2_08, C4_02, C8_02).
- **Spaces.** Most interiors are boxes. One rust texture covers most floors,
  walls and boxes in the chapter 5–8 frames and in the Silk Foundry and Debt
  Citadel arenas (C5_05, C5_06, C5_16, C6_06, C6_09, C6_13, C7_04, C7_13,
  C8_04, C8_14, A3, A4). The loom hall (C5_05) has no ceiling: its walls
  stop at a flat white void. Both production tasks shown (arrow work, C1_09,
  and the waterwheel, C4_11) take place in the same plank-walled room with
  box stations; no waterwheel is visible.
- **Story beats without visuals.** "The sky splits" (C1_13) shows the estate
  courtyard under a plain grey sky 31 s into the cinematic, while Takemaru
  says "Sensei… the sky…". Nothing in the sky has split. The cinematics are
  a camera dolly over the beat's place behind a letterboxed card; there is
  no Sequencer content yet.
- **Light.** The occupied streets (C3_02, C3_07, C3_17) are underexposed to
  near-silhouette. The best-developed spaces are the Nyaagyu Estate gate and
  courtyard (C1_13, C2_02): torii, capped walls, shōji buildings, lanterns
  and trees. Even there, box crates stand on flat ground.
- **Weapons.** The first-person matchlock is a white cylinder with brown
  blocks (A1, A3).

HUD defects for the UI lane:

- The weapon panel's English line is cut off at the right screen edge in
  every campaign frame ("Distance: cut, thrust, za…").
- In stealth beats the stealth meter ("COMBAT", しゃがみ, 明るさ) draws over
  the objective text in the top-right panel (C3_02, C6_06, C7_04).
- World marker labels overprint one another (C3_02, C4_02, C6_06).
- The English line of a boss telegraph runs past its panel's edge (C4_16,
  C5_16), and in C3_17 it runs into the warning timer.
- On every results screen, the "稽古終了 / Practice over … Enter でもう一度"
  notice shows through the table.
- The game's own "処理負荷により、稽古時間を減速しています" notice (practice
  time slowed under processing load) has no English line, and it overlaps
  the objective panel (A2, A3). It appeared because other GPU work slowed
  those frames (see below).
- FE_12 still says performance on this machine has not been measured.

| Frame | What it shows |
|---|---|
| [FE_01_Title](FE_01_Title.png) | Title: SORA mon, 猫柳生 / NYAAGYU REBELLION, the bilingual tagline, and Enter はじめる / Begin. The background is labelled on screen as a generated key visual, not gameplay. |
| [FE_02_MainKeyboard](FE_02_MainKeyboard.png) | Main menu (keyboard prompts): new campaign, chapter select, practice, IrohaConnect wallet, settings, credits and quit, each in Japanese with English. |
| [FE_04_PracticeLobby](FE_04_PracticeLobby.png) | Practice lobby: mode, arena, class, special weapon, difficulty and player count. It states that nothing is bonded or paid. |
| [FE_12_Graphics](FE_12_Graphics.png) | Graphics: Mac preset, TSR 75%, 60 fps cap, VSync, borderless. Its note still says performance on this machine has not been measured. |
| [FE_16_ControlsBindings](FE_16_ControlsBindings.png) | Controls: keyboard and mouse beside pad bindings, with the rebind hint. |
| [C1_02_SeiganDuel](C1_02_SeiganDuel.png) | Ch. 1 dojo sparring, beat 2: the armoured tabby opponent 2 m away, the seigan prompt and Sekireisai's line. |
| [C1_06_KurimaruTack](C1_06_KurimaruTack.png) | Ch. 1 beat 6, tack on (4 pieces), not yet mounted: Kurimaru in profile in the riding ground; mount prompt and Takemaru's line. |
| [C1_09_ArrowWork](C1_09_ArrowWork.png) | Ch. 1 production task (arrow straightening, step 1 of 6), with the step list and Tetsugorō's line. |
| [C1_13_SkySplits](C1_13_SkySplits.png) | Ch. 1 closing cinematic 空が裂ける / The sky splits on its letterboxed card, 31 s in: the estate courtyard from above, the hero on the path, Takemaru's line. The sky is plain grey. |
| [C2_02_NagayaGate](C2_02_NagayaGate.png) | Ch. 2 Nagaya Gate: an invader 4 m away before a wooden storehouse, Nyaakoto's orders, objective 0 of 8. |
| [C2_08_PackTrainRide](C2_08_PackTrainRide.png) | Ch. 2 pack-train escort from the saddle: the long walled road, objective marker at 1185 m, rein prompts. |
| [C2_15_DunarkTelegraph](C2_15_DunarkTelegraph.png) | Ch. 2 boss: Dunark close, telegraphing 早斬り / QUICK CUT (0.3 s left), with his line. |
| [C3_02_LandingStealth](C3_02_LandingStealth.png) | Ch. 3 stealth zone, hero crouched: two guards with alert marks, silhouetted against a flat sky; the crouch hint and the inventory drone's line. |
| [C3_07_CraftspeopleEscort](C3_07_CraftspeopleEscort.png) | Ch. 3 escort at dusk: a dark street, one lantern, the escorted artisan in silhouette in front of the hero. |
| [C3_17_PenaltaTelegraph](C3_17_PenaltaTelegraph.png) | Ch. 3 boss: Penalta telegraphs 槌落とし / HAMMER SLAM (0.7 s); the boss is a dark silhouette. |
| [C4_02_BankRoadRide](C4_02_BankRoadRide.png) | Ch. 4 bank-road ride from the saddle, with Otane's line about the paddy ridges. |
| [C4_11_Waterwheel](C4_11_Waterwheel.png) | Ch. 4 production task (waterwheel repair, step 1 of 4) in the generic workshop room. |
| [C4_16_AssessorTelegraph](C4_16_AssessorTelegraph.png) | Ch. 4 boss: the Assessor Engine telegraphs 差押え網 / SEIZURE NET (0.6 s), seen from the saddle. |
| [C5_01_SilkFoundry](C5_01_SilkFoundry.png) | Ch. 5 opening cinematic 絹の工房 / The Silk Foundry on its card, 4 s in: a lantern-lit courtyard with a torii and crates; Kohagi's line. |
| [C5_05_LoomHall](C5_05_LoomHall.png) | Ch. 5 loom hall: two invaders in clear view past a rust-textured box, under an open white void; Tarifa's line. |
| [C5_06_Bellows](C5_06_Bellows.png) | Ch. 5 production task (tatara bellows, 0 of 90) facing a dark box and a brick wall. |
| [C5_16_TarifaTelegraph](C5_16_TarifaTelegraph.png) | Ch. 5 boss: Tarifa telegraphs 鉤縄 / TETHER LASH (0.5 s), with the marobashi dodge hint. |
| [C6_06_LedgerAisles](C6_06_LedgerAisles.png) | Ch. 6 stealth, hero crouched: guards with alert marks down a rust aisle and two drones above, as Iota's line says. |
| [C6_09_ToranosukeDuel](C6_09_ToranosukeDuel.png) | Ch. 6 duel: Toranosuke (the armoured tabby model, with bow and quiver) at 2 m in a rust-textured corridor. |
| [C6_13_EskroTelegraph](C6_13_EskroTelegraph.png) | Ch. 6 boss: Eskro telegraphs 連爪 / CLAW FLURRY (0.3 s) after hearing the hero move. |
| [C7_04_CargoHold](C7_04_CargoHold.png) | Ch. 7 cargo hold, hero crouched: guards about 10 m off with alert marks and two drones above; Kohagi's line. |
| [C7_10_HullRidge](C7_10_HullRidge.png) | Ch. 7 hull ridge: one enemy high against a grey sky above a dark roof edge; Kohagi's line. |
| [C7_13_CollateraTelegraph](C7_13_CollateraTelegraph.png) | Ch. 7 boss: Collatera telegraphs 利払いの双銃 / TWIN BURST (0.3 s) with its laser line to the hero. |
| [C8_02_CausewayRide](C8_02_CausewayRide.png) | Ch. 8 causeway charge from the saddle down a street of box houses; mounted-yari hint. |
| [C8_04_FieldForge](C8_04_FieldForge.png) | Ch. 8 defence of the field forge and aid station (147 s left) among rust-textured boxes; Okuzu's line. |
| [C8_14_HighCollectorTelegraph](C8_14_HighCollectorTelegraph.png) | Ch. 8 boss: Val Amort telegraphs 帳簿光線 / LEDGER BEAM (0.2 s) with three ledger shards. |
| [A1_NyaagyuEstate_Combat](A1_NyaagyuEstate_Combat.png) | Estate free-for-all, 8 cats (hero: Teppō): an opponent at a wall corner in the sights, kill feed and top-four list. |
| [A1_NyaagyuEstate_Scoreboard](A1_NyaagyuEstate_Scoreboard.png) | Held scoreboard (Tab), 9:15 left. |
| [A1_NyaagyuEstate_Results](A1_NyaagyuEstate_Results.png) | Results: 薬師 3 wins; zero-stake XOR settlement conserved (0 = 0 + 0). |
| [A2_LanternWard_Combat](A2_LanternWard_Combat.png) | Lantern Ward control, 12 cats (hero: Shinobi): a crowd of cats at point-blank on the contested point, with an enemy 2 m away in the sights. |
| [A2_LanternWard_Scoreboard](A2_LanternWard_Scoreboard.png) | Team scoreboard: 空紋一揆 / The Sora League against 恒星信用院 / The Stellar Credit House. |
| [A2_LanternWard_Results](A2_LanternWard_Results.png) | Results: defeat, the enemy held the point 3:00. |
| [A3_SilkFoundry_Combat](A3_SilkFoundry_Combat.png) | Silk Foundry payload, 12 cats (hero: Hanabi): the cart with two enemies beside it and an allied Teppō in the armoured tabby model; no profiler counter. |
| [A3_SilkFoundry_Scoreboard](A3_SilkFoundry_Scoreboard.png) | Team scoreboard with respawn timers. |
| [A3_SilkFoundry_Results](A3_SilkFoundry_Results.png) | Results: defeat, cart 59% and 2 of 3 checkpoints at 10:00. |
| [A4_DebtCitadel_Combat](A4_DebtCitadel_Combat.png) | Debt Citadel melee-only, 8 cats (hero: Samurai, katana): two opponents in a dark rust room with cyan floor strips; no profiler counter. |
| [A4_DebtCitadel_Scoreboard](A4_DebtCitadel_Scoreboard.png) | Melee scoreboard: katana, kusarigama, kanabō, tantō, wakizashi, forge hammer. |
| [A4_DebtCitadel_Results](A4_DebtCitadel_Results.png) | Results: victory on most kills (56). |

## Frame time at 1080p (M1 Ultra, Mac preset)

**No window is free of other GPU work, so none is the game's own frame
time.** Other lanes' Blender jobs ran on this shared GPU during almost
every window measured with App Nap off. The last run (`full5`) waited 380 s
for an idle GPU with no Blender, Unreal or shader-worker process, then
launched. A Blender job started 13 s later and ran through every window.
What the runs do show:

- **Render cost.** Uncapped, Debt Citadel, Lantern Ward and Silk Foundry took
  12.7–14.8 ms per frame (GPU 11.7–13.6 ms), about 68–79 fps, in the two
  runs where the other work was light (`full1`, where nothing was recorded,
  and `practice-idle3`). Nyaagyu Estate took 11.9 ms in `full1` and 15.7 ms
  in `full5`.
- **As shipped (60 fps cap).** Two windows held the cap. Debt Citadel in
  `practice-idle3` held it with almost no other GPU work: 1200 frames in
  20 s, mean 16.68 ms, p99 16.71 ms. Nyaagyu Estate in `full5` held it beside
  a Blender job: 1199 frames in 20 s, mean 16.69 ms, p99 16.79 ms, 8 frames
  over 16.7 ms. Every other capped window beside Blender reached 2–54 fps.
  Debt Citadel's capped window ran at 60.0 fps in one run and 11.3 fps in
  another; the swing follows the other GPU load, not the game.

Each arena measures a **capped** window (20 s, `t.MaxFPS=60` as the preset
ships) and then an **uncapped** window (15 s, `t.MaxFPS=0`) in live 8- or
12-cat practice. The figures come from the engine's stat-unit timers and a
`csvprofile` of the same window, and the CSV columns agree with stat unit to
within a few percent. [frame-times.tsv](frame-times.tsv) has every window of
all seven runs.

| Run (JST) | App Nap | Arena | Window | fps | Frame mean / p95 / p99 ms | GPU mean ms | Other GPU work |
|---|---|---|---|---|---|---|---|
| full1 09-26 21:32 | on | Nyaagyu Estate | uncapped | 84.1 | 11.89 / 13.84 / 18.06 | 10.93 | not sampled |
| full1 | on | Lantern Ward | uncapped | 70.1 | 14.27 / 16.21 / 17.68 | 13.31 | not sampled |
| full1 | on | Silk Foundry | uncapped | 78.5 | 12.74 / 14.97 / 18.61 | 11.74 | not sampled |
| full1 | on | Debt Citadel | uncapped | 75.2 | 13.35 / 19.10 / 36.46 | 11.92 | not sampled |
| full1 | on | all four | capped | 20.2–24.7 | 40.6–49.4 mean | 15.3–19.9 | not sampled; App Nap |
| practice-idle3 09-26 23:53 | off | Debt Citadel | capped | 60.0 | 16.68 / 16.70 / 16.71 | 13.40 | Blender in the last sample only |
| practice-idle3 | off | Debt Citadel | uncapped | 75.1 | 13.31 / 14.65 / 27.82 | 12.18 | Blender |
| practice-idle3 | off | Lantern Ward | uncapped | 67.8 | 14.75 / 16.97 / 23.25 | 13.63 | Blender |
| practice-idle3 | off | Silk Foundry | uncapped | 72.5 | 13.80 / 17.81 / 31.96 | 12.67 | Blender |
| full5 09-27 01:02 | off | Nyaagyu Estate | capped | 59.9 | 16.69 / 16.69 / 16.79 | 12.93 | Blender |
| full5 | off | Nyaagyu Estate | uncapped | 63.8 | 15.68 / 43.37 / 52.69 | 14.41 | Blender |
| full5 | off | Lantern Ward | capped | 53.6 | 18.68 / 26.41 / 65.21 | 17.16 | Blender |
| full5 | off | Debt Citadel | uncapped | 57.2 | 17.47 / 18.26 / 200.58 | 16.30 | Blender |
| full5 | off | Silk Foundry | uncapped | 2.4 | 416.63 / 1459.39 / 1618.85 | 412.73 | Blender |

- **App Nap.** The full1 capped windows measured App Nap, not the game. An
  offscreen app launched with `-nosound` has no visible window, so macOS
  coalesces its timers. The harness's probe found that a requested 5 ms sleep
  took 8.6–32 ms on average, and the frame cap waits by sleeping. The capture
  script now passes `-NSAppSleepDisabled YES`. With it, the same probe
  measures 5.9–6.1 ms in every later arena. The uncapped windows never sleep,
  so App Nap did not affect them.
- **Contention.** The capture script samples, every 2 s, the GPU's busy
  figure and every other process that uses half a core or can load the GPU.
  Blender ran in every measured window of `practice-idle1`, `full2`, `full3`
  and `full5`, and in all but the first window of `practice-idle3`. These
  were the runtime-weapon and cat-head builds in this checkout. Nine orphaned
  `CrashReportClient` processes from earlier game crashes, and Activity
  Monitor, each kept one core at about 100% in every sample; the 1-minute
  load stayed at 16–32. They were left running: stopping them needs the
  user's go-ahead. In `full3` the Lantern Ward uncapped window drew only 25
  frames in 15 s beside Blender, and its test failed its own check that each
  window samples more than 30 frames. The contended runs' numbers are in
  `frame-times.tsv` for reference and are not the game's own frame time.

To measure cleanly, stop the stray `CrashReportClient` processes and run the
following while no other lane is rendering:
`SORA_CAPTURE_FRONTEND=0 SORA_CAPTURE_FILTER=SoraCapture.Practice SORA_CAPTURE_IDLE_WAIT=3600 scripts/toolchain/capture-packaged-mac.sh Local/Packages/mac-capture-harness5`
The script waits for an idle GPU. Its `frame-times.tsv` names the other GPU
work and the load seen in each window, and its `contention.txt` summarises
the whole launch.
