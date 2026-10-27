# Weapon HUD capture fixture

The weapon panel retains the existing dark panel and ivory/gold/muted text.
Its Japanese name, English name and ammunition/action descriptions now wrap
within the measured text column. The panel grows upward from the existing
bottom-right anchor. Draw/strike windup sits immediately above it and the
guard reserve remains below the text. The font measurement is the same
`UCanvas::ClippedStrLen` used by canvas text sizing; no maximum-line cutoff
drops text. Japanese and English text retain readable size floors at 720p.
The transient arm-change notice stacks above windup. Full-width dialogue,
notices and manufacturing instructions start above that entire measured
stack, with fieldcraft prompts placed above the story area. Wrapped
instruction text keeps every character. Other gameplay overlays and action
prompts remain enabled.

`SoraCapture.WeaponHUDFixture` provides nine rendering-client tests:

- `Bokken`: ch01.b09, including the long nonlethal training weapon name.
- `Katana`: ch04.b11, including the full distance/cut/thrust/zanshin text.
- `BowDraw`: ch04.b11, including the bound fire key, arrow counts and actual
  held bow draw/release indicator plus the real arm-group change notice.
- `BokkenDialogue`: ch01.b09 with its actual ambient arrival line and
  manufacturing instructions still visible.
- `PickupNotices`: actual partial manufacturing progress and four collected
  world pickups, including their newest titles and explicit condensed summary.
- `EightTargets`: ch04.b12 with all eight named planters and different live
  health values, retaining its arrival dialogue.
- `BellowsKeyboard` and `BellowsGamepad`: actual held work and alternating
  tread inputs, next-foot cue, bound key labels and pickup notices.
- `CaptionPressure`: ch04.b12 with all eight targets, arrival dialogue, four
  live sound captions with repeat counts/directions and ExtraLarge subtitles.

Each uses the production checkpoint validator, a temporary save slot,
normal load/start and the actual campaign equipment unlock gate. Ambient
arrival dialogue runs to completion except for the dialogue and eight-target
fixtures, which retain it. The fixture then freezes the prepared
gameplay state while asset compilation settles, with engine diagnostics
enabled. It checks actual HUD text widths, heights, preserved characters,
readable sizes, weapon identity, language and windup state. It also checks
the actual rectangles of weapon, windup, arm-change notice, vitals, dialogue
and instruction/notice strips for overlap and viewport bounds before
requesting each fresh screenshot. Japanese-only and Japanese-plus-English frames are
both saved. The player's save slot and HUD visibility are restored afterward.

After building/importing the required game assets, run on the single Unreal
process lane:

```sh
scripts/toolchain/capture-editor-game.sh SoraCapture.WeaponHUDFixture 1920 1080 sm6
scripts/toolchain/capture-editor-game.sh SoraCapture.WeaponHUDFixture 1280 720 sm6
```

Review all 18 frames per viewport for readable complete weapon names,
descriptions and key prompts; separated draw/guard indicators; and any overlap
with the real gameplay overlays. A measured fit alone is not visual approval.
These commands run the editor binary's standalone game, not a packaged build.

Each fresh PNG is acknowledged with `SORA_WEAPON_HUD_FIXTURE_FRAME` and archived
by the capture wrapper with dimensions, original bytes and SHA-256. Its
`capture_kind` is **prepared gameplay UI fixture; not playthrough evidence**.
The screenshot `index.tsv` records its authored checkpoint and setup. This
fixture does not establish completed playthrough, packaged compatibility,
performance, or final art quality.

Live captions reserve their measured glyph bounds before the tracker/notices
are placed. A bounded search uses clear left/right columns and the open
regions beside the weapon stack, above or beside health, when the top-right
stack cannot fit. Full-width dialogue and prompts remain reserved. The selected caption font size is
unchanged. Bilingual captions retain both sound and direction translations and
show the shared repeat count once. The compact tracker trims empty font padding
while retaining every target name and health bar; ordinary caption-free tracker
spacing stays unchanged. The lower story/weapon reservation stays unchanged.
When bilingual dialogue leaves too little height, the tracker retries the
same measured compact spacing even without sound captions. Notices can use
the clear column below the objective and beside the rhythm cue. The action
translation stacks beneath its Japanese label when inline text would cross
into the tracker. Projected site/objective labels and the site examine prompt
retain their text and move to the nearest measured free region, including
clearance from each other. The runtime fixture checks that every caption
clears the actual fixed gameplay panels, rhythm cue, tracker/notices and lower
story stack. These source changes
still require fresh 720p/1080p captures and visual review.

Host-only font/packing and archive regression (materialize the tracked Noto
font with Git LFS first):

```sh
python3 scripts/unreal/test_caption_layout.py
python3 -m unittest discover -s scripts/toolchain -p test_capture_report.py
python3 scripts/unreal/native_japanese_localization.py --check
```
