# Persistent Codex reader

The main menu and campaign pause menu offer **図鑑 / Codex**. It lists only
records already present in the loaded campaign save. Accept/Enter/pad A or a
row click opens the full text; Back/Esc/pad B returns to the same index row,
then to the menu that opened it. The campaign stays paused throughout.

The reader shows Japanese and the existing optional English subtitles. Its
body, title and index labels use the selected Standard/Large/Extra large text
size. Up/Down, the d-pad/left stick, the mouse wheel, clickable up/down prompts,
and the scrollbar move the reader. The title and full bilingual body share a
clipped scroll region; Back and prompts stay outside it. No body is truncated
into a notice or summary.

## Authored content and implementation choices

- [Story bible collectible contract](story-bible.md) declares 48 passive
  collectibles, six per chapter, with Codex rewards and no stat grants. The
  reader uses the existing `Collectibles` bits and the catalog's entire JA/EN
  bodies. It never writes a save or grants a reward.
- [Chapter 1 §4.4](chapter-01.md) supplies six title pairs. Chapters 2–8 declare
  no titles. Those entries receive a neutral localized chapter/category/item
  number label, not a newly invented object name or historical account. The
  catalog accepts exactly two nonempty strings or two explicit null values.
- The chapter-one vista arrow challenge's existing `codex_toshiya` uses its
  separate `WoodPoiMask` bit. It appears as an archery challenge after the
  collectibles and does not turn the count into 49/48. Its short historical
  account uses the institutional sources and date limits below.
- Other wood/gallery lore flags do not silently become additional Codex
  entries. The production registry operation remains a separate player flow.
- Main/Pause → index → reader, index order by the existing saved bit, and a
  scroll step of one fifth of the laid-out overflow are implementation choices;
  the authored documents do not specify a Codex layout.

No new save schema or property is added. Existing saves with zero discoveries
show an empty state. Fresh loading and chapter replay retain discoveries;
starting a new campaign uses the existing clearing behavior. Viewing the
Codex changes neither checkpoint nor weapon/collectible state.

## Toshiya copy and historical limits

The reader and earned-reward notice share this Japanese/English account:

> 京都の三十三間堂では、西の縁側に沿って約百二十メートル先まで矢を通し、その本数を競った。慶長十一年（一六〇六）には、百本のうち五十一本を通した射手の記録が残る。

> At Kyoto's Sanjūsangen-dō, archers competed to send arrows along the western veranda, a distance of about 120 metres. A record from Keichō 11 (1606) describes an archer sending 51 arrows through from 100 shots.

Sources reviewed on 2026-10-23:

- [Sanjūsangen-dō, 楊枝のお加持と大的大会](https://www.sanjusangendo.jp/event/yanagi/):
  the temple's account describes the western veranda, 120-metre course and
  counting arrows that passed through. It says the beginnings are uncertain
  and mentions Momoyama precedents; **1606 is not called the origin** here.
  The page's indexed institutional text was available; direct retrieval
  returned HTTP 502 during this review.
- [All Nippon Kyudo Federation, 弓道の歴史](https://www.kyudo.jp/howto/history.html),
  “心身鍛練としての弓”: supports the 1606 / Keichō 11 record of 51 arrows
  through from 100 shots. This is a modern institutional account; the original
  1606 record has not been inspected. The brief copy omits the archer's name
  because institutional pages use different kanji spellings.
- [Suntory Museum of Art, 三十三間堂通し矢図屛風](https://www.suntory.co.jp/sma/collection/data/detail?id=576):
  the collection record corroborates the western veranda and sixty-six ken,
  approximately 120 metres. The screen is seventeenth century and its depicted
  event may date to the late 1660s; those later scene details are not evidence
  for the game's 1623 setting.

The entry mentions no later 1686 record, later clan rivalry, origin date, or
combat benefit. The wood's 45-metre clapper challenge is fictional gameplay,
not a reconstruction of the temple course. Its distance, arrow-only trigger,
separate persistent reward and lack of stat grants are unchanged. The prose
contains no production status or “provisional draft” label.

## Verification and pending engine work

Source-only tests live in `scripts/unreal/test_codex_data.py`: all 48 unique
saved-bit identities, complete bilingual bodies, category totals, authored and
absent title pairs, and native/translated UI labels. The localization pipeline
compiles and checks the new UI copy. These checks do **not** establish Slate
layout, controller feel, rendering or gameplay completion.

The directed engine filters are:

- `SoraArena.UI.CodexTitleData`: exact title JSON types, null pairs, missing,
  mismatched, empty and coercible bad inputs against the actual loader helper.
- `SoraArena.UI.CodexEarned`: prepared b08 start, then real mapped Interact at
  the stone and mapped yumi draw/release at the vista; notice expiry; pause
  navigation and the exact complete bodies; repeated reading with identical
  campaign bytes; fresh-world load and main-menu reopening without reseeding.
- `SoraArena.UI.CodexLibrary`: a clearly prepared 48-item + challenge save,
  every entry reached by pad, keyboard Back/focus retention, all three text
  sizes with English on/off, read-only campaign bytes, chapter replay, and
  existing New Campaign clearing.
- Regression filters: `SoraArena.UI.EveryScreenByPadAndKeyboard`,
  `SoraArena.UI.SlateReadableAt720p`, `SoraArena.Menu`,
  `SoraArena.Campaign.WoodExplore`, and `SoraArena.Campaign.SaveRoundTrip`.

`SoraCapture.Codex.Live` must run separately in a rendering game at each of
1280×720 and 1920×1080. It uses the actual focused Slate widget and normal key
routing, including the settings menu to choose extra-large text and F10 for
English. It captures empty/index first/index last, the longest collectible
reader at Standard and Extra large top/end, Japanese-only, and Toshiya at
Extra large top/end. The ninth `toshiya-end` phase uses normal d-pad Down
input with English enabled; it must reach a positive actual scroll end and
place the content tail inside the reader clip. Both end phases also retain
their preceding top phase's content extent and viewport; Back stays outside
the clip and inside the viewport. The original PNGs and
`capture.json` are under `Saved/Screenshots/SoraCodex/<resolution>/<run-id>/`.
Each successfully written original emits `LogTemp: Display: SORA_CODEX_FRAME`.
The v2 capture wrapper requires all nine unique phases in order and archives the
unchanged PNGs plus the original source `capture.json`. The metadata must be
fresh (including after the PNGs), passed, schema/viewport/count/filename matched,
and explicitly scoped as a prepared discovery ledger. Frame IDs, language,
selected entry and actual end-scroll observations are checked. Missing,
duplicate, stale, failed or inconsistent evidence cannot qualify an archive.
The earlier v1 eight-frame receipts remain historical evidence for their own
source; neither they nor a relabelled eight-frame receipt qualify the new
Toshiya end phase. Collector tests explicitly reject a wrong entry, English
disabled, zero/partial scroll, out-of-clip tail and reused frame identity.
Prepared discovery ledgers are explicitly labeled; these images cannot prove
all records were earned. The fixture preserves original campaign, control and
settings bytes/existence, restores current subtitle preferences, and releases
all injected keys. Root owns both the engine tests and visual review. The new
copy and ninth phase have only source/CPU validation until root runs the integrated candidate
and reviews both original `toshiya` and `toshiya-end` PNGs at both resolutions.

Example rendering invocation, after root has built the integrated candidate:

```sh
scripts/toolchain/run-editor.sh -game -windowed -ResX=1280 -ResY=720 \
  -ExecCmds="Automation RunTests SoraCapture.Codex.Live;Quit"
```

Repeat at 1920×1080; inspect the original images for readable JA/EN bodies,
uncut final lines, accessible Back, stable focus, and no overlap. Passing
source assertions or submitting strings to Slate is not visual acceptance.
