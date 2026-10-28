# Opening text and dojo controls — October 28

The ordinary look at preserved Mac package `1b6dfadc` exposed English words
breaking across lines and small dojo hints missing their guard binding. The
isolated fix uses Unreal's word-aware wrapper, measures actual glyph extents,
keeps the subtitle readability floor, and places early dojo dialogue/notices
with the existing measured story layout. Lessons resolve the current `Block`
and `Fire` mappings, including remapped keys and controller labels. English
and Japanese localization archives are updated; all 506 keys validate.

Signed runtime source `c5c5092e44cca6c1ed0422a34c15ffc39f7d9b13` passes all
nine selected native tests with zero selected errors or warnings: opening
wrapping, dojo prompt layout, key prompts, captions/subtitles, English
subtitles, guard lessons, awase, zanshin and authored dialogue modes. The new
fixtures cover Japanese/bilingual text, keyboard/controller labels, a remapped
guard key, full text retention and measured panel separation at 1280×720,
1920×1080 and 2560×1080. Directed guard/parry transitions exercise later lessons.
This is not an ordinary playthrough.

The M2 Ultra UE 5.8.3 Editor build and NullRHI run finish naturally. Independent
review authenticates all 20 original files and unchanged source/native,
Config, Generated and frozen integration inputs. The log retains 19 raw
pre-initialization `Condition failed` diagnostics outside the selected tests.
The four prior failed runs remain archived: wrong `Guard` action lookup,
720p dialogue/notice collision, its diagnostic reproduction, and a two-row
actual-glyph overflow. The fix does not lower the readable font size.

Signed capture source `9eeadad480f2dc9756e26d3f8163f4a8c4ccd9a5` adds only the
capture fixture and evidence-collector support after the runtime-tested
implementation. One offscreen SM6 capture case passes with zero selected
errors or warnings. All 25 original files authenticate; all three original
1280×720 PNGs were displayed and reviewed. The actual New Campaign card keeps
the complete narrative, including “distance,” at word boundaries. Keyboard
`Left Ctrl` and controller `LT` hints are readable and separated from story
panels. No shader-preparation overlay is visible. The fixture waits for
compilation/streaming while its game clock is paused.

Capture `70d32a6b` failed compilation because `Freeze` collided with an Unreal
name; the qualified helper fixes it. Capture `97590935` technically passed,
but visual review rejected its nominal chapter card: it showed a resumed
cinematic. Both results and originals are preserved. The corrected fixture
starts New Campaign and asserts the opening state before saving the image.

Focused host checks pass: six aim-HUD layout checks and 55 capture-collector
tests. The earlier 66 gameplay source gates retain their recorded initial
HUD implementation, rather than being relabeled as current-head CI.

Evidence is in `Saved/Qualification/2026-10-28/` in the source-validation
worktree:

| Record | SHA-256 |
| --- | --- |
| Nine-test runtime review | `cea0fbc2a581ebbcc3ff3fa30208dbe31e1d1c0adffd147f2e78269d97a33e2d` |
| Corrected capture status | `2d58e46c461aa4f7c36d597917f3ba79daa097ef5aa7c4548ad6127c7cb52fa3` |
| Corrected capture review | `7aeffb13b1c9ca2752176c73e151e0a7de9945f53902920cfea470295695bda9` |

The three original frames are under
`opening-hud-capture-9eeadad4-attempt1/capture/frames/SoraCapture/1280x720/`.
The separate `opening-hud-capture-9eeadad4-attempt1-visual-review.json`
records observations and scope. Bright clipping, repetitive timbers,
placeholder props and substantial HUD coverage remain visible. This is not
final art, whole-UI, performance, actual-M1, Windows or new-package acceptance.
ROOT remains frozen at `b6ba3c11`; its preserved package remains `1b6dfadc`.
