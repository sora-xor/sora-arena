# Wave C rendered baseline: packaged Mac, 1920×1080

**Verdict: the game is nowhere near the photoreal AAA target.** These 40 frames
come from the packaged Mac game on 2026-09-26 JST, rendered by Metal at
1920×1080 under the Mac graphics preset. The front end is readable and fully
bilingual. The HUD shows the objective, subtitles, boss telegraphs, the kill
feed, the scoreboard and the results. The 3D world, however, is a prototype.
Characters are toy-like, the horse is built from primitive shapes, most
spaces are boxes with one stretched texture, and several scenes are
underexposed silhouettes or lit against a flat white void. The frames are a
baseline for later A/B comparison. They do not approve any art.

The frames are unedited. [frames.tsv](frames.tsv) lists each file's SHA-256,
its beat, and what the capture harness recorded when it saved the frame.

## How they were made

- **Package.** `Local/Packages/mac-capture-harness/SoraArena.app`
  (gitignored), a Development build signed ad hoc under bundle id
  `org.sora.soraarena`. Its game executable (sha256 `05257481…5465`) was
  built from `c3be5e4` plus the capture harness,
  `Source/SoraArena/Private/SoraCaptureAutomation.cpp`. Its cooked content is
  byte-identical to the green package `mac-capture-green` (same
  `SoraArena-Mac.utoc`/`.pak` hashes, 919 cooked packages). The staged kernel
  is the prebuilt `libarena_ffi.dylib` (sha256 `1bd6e8fa…d494`).
- **Rendering.** The frames are real Metal rendering through
  `-RenderOffscreen` at `-ResX=1920 -ResY=1080`, never `-NullRHI`. The Mac's
  screen was locked (since 19:40 JST). Offscreen rendering needs no window,
  so the lock did not matter. The preset renders at a 75% screen percentage
  (1440×810) and upscales with TSR (`r.AntiAliasingMethod=4`). Lumen global
  illumination and reflections are on (`r.DynamicGlobalIlluminationMethod=1`,
  `r.ReflectionMethod=1`). Nanite and virtual shadow maps are off.
- **No Nanite on this Mac.** The log says "To use SM6 on this system, please
  ensure you are running Mac OS 15. Falling back to SM5". The machine runs
  macOS 27.0, so that message is misleading. UE 5.8.3 enables SM6 on macOS
  only on Apple8-family GPUs (M2 or later; `MetalRHI.cpp`, the
  `bSupportsSM6` check). The M1 Ultra is Apple7, so it always runs
  `METAL_SM5`, and Nanite and virtual shadow maps cannot appear in any frame
  from this machine.
- **Commands.**
  `scripts/toolchain/capture-packaged-mac.sh Local/Packages/mac-capture-harness Saved/PackagedCapture/full1`
  made these frames with `SORA_MIN_FREE_GIB` lowered because disk was below
  30 GiB. It made two launches. The `frontend` launch ran
  `SoraArena.UIRendered.FrontEndScreens` at 1080p (19 screens, 1 of 1
  passed). The `capture` launch ran `SoraCapture`: eight campaign tests (6 of
  8 passed; see below) and four practice arenas (4 of 4 passed). Together
  they saved 61 frames at 1920×1080. The run's logs, index, frame list and
  profiles are in `Saved/PackagedCapture/full1` (gitignored).

The harness continues the campaign from checkpoints it seeds on a throwaway
save slot; the player's save is never read or written. It turns the hero
toward the beat's subject (an opponent, a guard, a boss in a telegraph, the
task, the horse, or the road from the saddle) and saves the frame with its
HUD. In practice it plays a zero-stake match with the hero on the kernel's
bot policy against Veteran bots. It then measures frame time and saves the
fight, the held scoreboard and the results table.

## What the frames show

Recurring art problems:

- **Characters.** The cats have oversized spherical heads, paws and
  shoulders, flat single-colour robes and a box chest plate with a teal
  "screen" (the alien side). The armoured tabby model worn by the dojo
  opponent (C1_02), Toranosuke (C6_09) and the practice allies (A3, A4) has a
  stretched fur texture and a stiff, arms-out pose. See also C2_02, C2_15 and
  A2.
- **The horse.** Kurimaru is built from cylinders, spheres and boxes with a
  box saddle (C1_06). From the saddle the rider sees a box head with two cone
  ears (C2_08, C4_02, C8_02).
- **Spaces.** Most interiors are boxes. One rust texture covers floors and
  walls throughout chapters 5–8 and in Silk Foundry and Debt Citadel (C5_06,
  C5_16, C6_09, C6_13, C7_13, C8_04, C8_14). Both production tasks shown
  (arrow work, C1_09, and the waterwheel, C4_11) take place in the same
  plank-walled room with box stations; no waterwheel is visible. C6_06 and
  C7_10 show guards floating against a flat white or grey void.
- **Light.** The occupied streets (C3_02, C3_07, C3_17) are underexposed to
  near-silhouette. C6_06 is overexposed. The best-developed space is the
  Nyaagyu Estate gate (C2_02): torii, capped walls, a shōji building and
  trees. Even there, box crates stand on flat ground.
- **Weapons.** The first-person matchlock is a white cylinder with brown
  blocks (A1).

HUD defects for the UI lane:

- The weapon panel's English line is cut off at the right screen edge in
  every campaign frame ("Distance: cut, thrust, za…").
- In stealth beats the stealth meter ("COMBAT", 明るさ, "STANDING / LIGHT")
  draws over the objective text in the top-right panel (C3_02, C6_06,
  C7_04).
- World marker labels overprint one another (C3_02 bottom right, C4_02,
  C7_04).
- The English line of a boss telegraph runs past its panel's edge (C4_16,
  C5_16).
- On every results screen, the "稽古終了 / Practice over … Enter でもう一度"
  notice shows through the table.

Capture artifacts (the harness's fault, not the game's):

- The CSV profiler's on-screen counter, "CsvProfiler フレーム:1,198", appears
  in A3 and A4 Combat because the frame is saved soon after the profile
  stops.
- The hero stands very close to Dunark in C2_15, so the boss's head is behind
  the HUD.
- C7_04 puts the hero face to face with a guard, with the bow limb across
  the view.

| Frame | What it shows |
|---|---|
| [FE_01_Title](FE_01_Title.png) | Title: SORA mon, 猫柳生 / NYAAGYU REBELLION, the bilingual tagline, and Enter はじめる / Begin. The background is labelled on screen as a generated key visual, not gameplay. |
| [FE_02_MainKeyboard](FE_02_MainKeyboard.png) | Main menu (keyboard prompts): new campaign, chapter select, practice, IrohaConnect wallet, settings, credits and quit, each in Japanese with English. |
| [FE_04_PracticeLobby](FE_04_PracticeLobby.png) | Practice lobby: mode, arena, class, special weapon, difficulty and player count. It states that nothing is bonded or paid. |
| [FE_12_Graphics](FE_12_Graphics.png) | Graphics: Mac preset, TSR 75%, 60 fps cap, VSync, borderless. Its note still says performance on this machine has not been measured. |
| [FE_16_ControlsBindings](FE_16_ControlsBindings.png) | Controls: keyboard and mouse beside pad bindings, with the rebind hint. |
| [C1_02_SeiganDuel](C1_02_SeiganDuel.png) | Ch. 1 dojo sparring, beat 2: the form prompt, the Sekireisai subtitle and the opponent 1 m away (fills the frame). |
| [C1_06_KurimaruTack](C1_06_KurimaruTack.png) | Ch. 1 beat 6, tack on (the harness counted 4 pieces) and not yet mounted: Kurimaru in profile in the riding ground; mount prompt and Takemaru's line. |
| [C1_09_ArrowWork](C1_09_ArrowWork.png) | Ch. 1 production task (arrow straightening, step 1 of 6), with the step list and Tetsugorō's line. |
| [C2_02_NagayaGate](C2_02_NagayaGate.png) | Ch. 2 Nagaya Gate: estate walls, torii, lanterns, invaders approaching, objective 0 of 8. |
| [C2_08_PackTrainRide](C2_08_PackTrainRide.png) | Ch. 2 pack-train escort from the saddle: the long walled road, objective marker at 1185 m, rein prompts. |
| [C2_15_DunarkTelegraph](C2_15_DunarkTelegraph.png) | Ch. 2 boss: Dunark telegraphs 早斬り / QUICK CUT at 42% of its warning, with a 0.2 s bar. |
| [C3_02_LandingStealth](C3_02_LandingStealth.png) | Ch. 3 stealth zone: two guards with alert marks, silhouetted against a flat sky; the crouch hint and the inventory drone's line. |
| [C3_07_CraftspeopleEscort](C3_07_CraftspeopleEscort.png) | Ch. 3 escort at dusk: a dark street, one lantern, the escorted artisan in silhouette. |
| [C3_17_PenaltaTelegraph](C3_17_PenaltaTelegraph.png) | Ch. 3 boss: Penalta telegraphs 槌落とし / HAMMER SLAM (35%); the boss is a dark silhouette. |
| [C4_02_BankRoadRide](C4_02_BankRoadRide.png) | Ch. 4 bank-road ride from the saddle, with Otane's line about the paddy ridges. |
| [C4_11_Waterwheel](C4_11_Waterwheel.png) | Ch. 4 production task (waterwheel repair, step 1 of 4) in the generic workshop room. |
| [C4_16_AssessorTelegraph](C4_16_AssessorTelegraph.png) | Ch. 4 boss: the Assessor Engine telegraphs 差押え網 / SEIZURE NET (40%), seen from the saddle. |
| [C5_06_Bellows](C5_06_Bellows.png) | Ch. 5 production task (tatara bellows, 0 of 90) facing a dark box and a brick wall. |
| [C5_16_TarifaTelegraph](C5_16_TarifaTelegraph.png) | Ch. 5 boss: Tarifa telegraphs 鉤縄 / TETHER LASH (33%), with the marobashi dodge hint. |
| [C6_06_LedgerAisles](C6_06_LedgerAisles.png) | Ch. 6 stealth: two guards with alert marks against a white void, more alert marks along the bottom edge. |
| [C6_09_ToranosukeDuel](C6_09_ToranosukeDuel.png) | Ch. 6 duel: Toranosuke (the armoured tabby model, with bow and quiver) at 2 m in a rust-textured corridor. |
| [C6_13_EskroTelegraph](C6_13_EskroTelegraph.png) | Ch. 6 boss: Eskro stands with **no** telegraph. Its panel reads "A blind sound-hunter: stay still while it pulses", and the hero stood still (see below). |
| [C7_04_CargoHold](C7_04_CargoHold.png) | Ch. 7 stealth in the cargo hold: a guard with alert marks at arm's length, Kohagi's line. |
| [C7_10_HullRidge](C7_10_HullRidge.png) | Ch. 7 hull ridge: one enemy against a grey sky above a roof edge. |
| [C7_13_CollateraTelegraph](C7_13_CollateraTelegraph.png) | Ch. 7 boss: Collatera telegraphs 利払いの双銃 / TWIN BURST (38%) with its laser line. |
| [C8_02_CausewayRide](C8_02_CausewayRide.png) | Ch. 8 causeway charge from the saddle down a street of box houses; mounted-yari hint. |
| [C8_04_FieldForge](C8_04_FieldForge.png) | Ch. 8 defence of the field forge and aid station (146 s left) among rust-textured boxes. |
| [C8_14_HighCollectorTelegraph](C8_14_HighCollectorTelegraph.png) | Ch. 8 boss: Val Amort telegraphs 帳簿光線 / LEDGER BEAM (31%) with three ledger shards. |
| [A1_NyaagyuEstate_Combat](A1_NyaagyuEstate_Combat.png) | Estate free-for-all, 8 cats (hero: Teppō): an opponent in the sights between wall blocks, kill feed and top-four list. |
| [A1_NyaagyuEstate_Scoreboard](A1_NyaagyuEstate_Scoreboard.png) | Held scoreboard (Tab), 9:14 left. |
| [A1_NyaagyuEstate_Results](A1_NyaagyuEstate_Results.png) | Results: 薬師 3 wins; zero-stake XOR settlement conserved (0 = 0 + 0). |
| [A2_LanternWard_Combat](A2_LanternWard_Combat.png) | Lantern Ward control, 12 cats (hero: Shinobi): a cluster of cats with enemy (blue) health bars at point-blank on the contested point; red damage edge. |
| [A2_LanternWard_Scoreboard](A2_LanternWard_Scoreboard.png) | Team scoreboard: 空紋一揆 / The Sora League against 恒星信用院 / The Stellar Credit House. |
| [A2_LanternWard_Results](A2_LanternWard_Results.png) | Results: defeat, the enemy held the point 3:00. |
| [A3_SilkFoundry_Combat](A3_SilkFoundry_Combat.png) | Silk Foundry payload, 12 cats (hero: Hanabi): an allied cat with bow and matchlock, an enemy behind; the profiler counter is visible. |
| [A3_SilkFoundry_Scoreboard](A3_SilkFoundry_Scoreboard.png) | Team scoreboard with respawn timers. |
| [A3_SilkFoundry_Results](A3_SilkFoundry_Results.png) | Results: defeat, cart 59% and 2 of 3 checkpoints at 10:00. |
| [A4_DebtCitadel_Combat](A4_DebtCitadel_Combat.png) | Debt Citadel melee-only, 8 cats (hero: Samurai, katana): an opponent past rust-textured cover with cyan floor strips; the profiler counter is visible. |
| [A4_DebtCitadel_Scoreboard](A4_DebtCitadel_Scoreboard.png) | Melee scoreboard: katana, kusarigama, kanabō, forge hammer, tantō, wakizashi. |
| [A4_DebtCitadel_Results](A4_DebtCitadel_Results.png) | Results: victory on most kills (56). |

## Harness failures in this run

Three campaign shots failed or missed. Fixing them needs a harness change
and a game rebuild, which were not done because free disk was below the
32 GiB floor for builds (27 GiB at the start of this step). None of the three
frames is in the set above.

- **C1_13_SkySplits (chapter 1, beat 13): failed.** `ch01.b13` has
  `"checkpoint": false`, so `SeedCheckpoint` refuses it. The saved frame
  repeats C1_09. Use a checkpoint beat instead.
- **C5_01_SilkFoundry (chapter 5, beat 1): failed.** The check that the
  seeded opening cinematic is the beat in play failed; the log does not say
  which condition. The frame saved a few seconds later shows beat 2, the
  iron-sand channel stealth zone, with the "Checkpoint restored." notice. The
  harness needs its own handling for cinematic beats.
- **C6_13_EskroTelegraph: no telegraph in 40 s** (a warning; the frame is in
  the set as the boss at rest). Eskro hunts by sound, and the hero stood
  still, 250 cm away with the boss facing him, and the boss never began an
  attack (serial 0). The harness must make noise (move or strike) to draw
  one.

## Frame time at 1080p (M1 Ultra, Mac preset)

**No clean 60 fps figure exists yet.** The best available data suggests the
Mac preset needs 11.9–14.3 ms a frame on average in practice combat on the
four arenas, with spikes in Debt Citadel. That result comes from a run whose
contention was not recorded.

Each arena measures a **capped** window (20 s, `t.MaxFPS=60` as the preset
ships) and then an **uncapped** window (15 s, `t.MaxFPS=0`) in live 8- or
12-cat practice. The figures are the engine's stat-unit timers and a
`csvprofile` of the same window. The CSV columns agree with stat unit within
a few percent.

| Run (JST) | Arena | Window | fps | Frame mean / p95 / p99 ms | GPU mean ms | Other GPU work |
|---|---|---|---|---|---|---|
| full1 21:32–21:39 | Nyaagyu Estate | uncapped | 84.1 | 11.89 / 13.84 / 18.06 | 10.93 | not sampled |
| full1 | Lantern Ward | uncapped | 70.1 | 14.27 / 16.21 / 17.68 | 13.31 | not sampled |
| full1 | Silk Foundry | uncapped | 78.5 | 12.74 / 14.97 / 18.61 | 11.74 | not sampled |
| full1 | Debt Citadel | uncapped | 75.2 | 13.35 / 19.10 / 36.46 | 11.92 | not sampled |
| full1 | all four | capped | 20.2–24.7 | 40.6–49.4 mean | 15.3–19.9 | App Nap (below) |
| practice-idle1 23:35–23:39 | all four | both | 19.2–47.0 | 21.3–52.1 mean | 15.2–50.6 | Blender in every window |

- **App Nap.** The full1 capped windows measured macOS App Nap, not the
  game. An offscreen, silent app has no visible window, so macOS coalesces
  its timers. The harness's probe found a requested 5 ms sleep taking
  8.6–32 ms (mean), and the frame cap waits by sleeping. The capture script
  now passes `-NSAppSleepDisabled YES`, after which the same probe measures
  6.0 ms. The uncapped windows never sleep, so App Nap did not affect them.
- **Contention.** With App Nap off, two later practice-only runs could not
  measure the game alone. Other lanes' Blender jobs (the runtime-weapon and
  cat-head builds in this checkout) ran on the GPU throughout, as the capture
  script's new process sampler recorded in `practice-idle1` (Blender in 114
  of 118 samples, 1-minute load 18–32). In `practice-nap1` (23:21–23:25,
  before the sampler existed) the GPU time rose to 186 ms in Lantern Ward;
  what caused it is not recorded. Nine orphaned `CrashReportClient` processes
  from earlier crashes each spin one core at about 100%, and so does Activity
  Monitor, in every sample. Those runs' numbers are in `Saved/PackagedCapture`
  and are not the game's frame time.

To measure cleanly, run
`SORA_CAPTURE_FRONTEND=0 SORA_CAPTURE_FILTER=SoraCapture.Practice SORA_CAPTURE_IDLE_WAIT=3600 scripts/toolchain/capture-packaged-mac.sh Local/Packages/mac-capture-harness`
when no other lane is rendering. The script waits until the GPU is idle and
no Blender, Unreal or shader-worker process runs. It writes `frame-times.tsv`
with the other GPU work and load seen in each window, and `contention.txt`.
