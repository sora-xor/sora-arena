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

`SoraCapture.WeaponHUDFixture` provides four rendering-client tests:

- `Bokken`: ch01.b09, including the long nonlethal training weapon name.
- `Katana`: ch04.b11, including the full distance/cut/thrust/zanshin text.
- `BowDraw`: ch04.b11, including the bound fire key, arrow counts and actual
  held bow draw/release indicator plus the real arm-group change notice.
- `BokkenDialogue`: ch01.b09 with its actual ambient arrival line and
  manufacturing instructions still visible.

Each uses the production checkpoint validator, a temporary save slot,
normal load/start and the actual campaign equipment unlock gate. Ambient
arrival dialogue runs to completion except for `BokkenDialogue`, which
retains it. The fixture then freezes the prepared
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

Review all eight frames per viewport for readable complete weapon names,
descriptions and key prompts; separated draw/guard indicators; and any overlap
with the real gameplay overlays. A measured fit alone is not visual approval.
These commands run the editor binary's standalone game, not a packaged build.

Each fresh PNG is acknowledged with `SORA_WEAPON_HUD_FIXTURE_FRAME` and archived
by the capture wrapper with dimensions, original bytes and SHA-256. Its
`capture_kind` is **prepared gameplay UI fixture; not playthrough evidence**.
The screenshot `index.tsv` records its authored checkpoint and setup. This
fixture does not establish completed playthrough, packaged compatibility,
performance, or final art quality.

Host-only archive regression:

```sh
python3 -m unittest discover -s scripts/toolchain -p test_capture_report.py
python3 scripts/unreal/native_japanese_localization.py --check
```
