# Cargo transfer rendered capture

`SoraCapture.Cargo.Transfer` is an assisted review of the chapter-four cargo HUD,
load shares, drying stands and provisional lead rope. It is not a playthrough,
combat/balance test, photoreal acceptance or packaged qualification. Claude
retains final art ownership. No production gameplay or visual behavior changes
are part of this capture helper.

Run through `scripts/toolchain/capture-editor-game.sh SoraCapture.Cargo.Transfer
1280 720 sm5` (or 1920 1080 and the actual supported shader model). This runner
builds and renders; the author source-only handoff does not execute it. Root owns
that integration and the original-image review. A warm run takes over 100 seconds;
the helper has a 240-second wall timeout. It rejects fixed simulation clocks and
non-unit world/hero time dilation.

The helper preserves raw campaign, control and settings save bytes/existence,
action/axis mappings, the HUD switch and the English subtitle switch. It uses a
unique temporary ch04.b14 checkpoint and GUID screenshot directory. It starts
with an ordinary mapped Interact dismount at the original mounted start. Each
hamlet then receives explicitly recorded hero/horse positions and an external
side camera. Enemy actor, movement and controller ticks are frozen to isolate
presentation. This setup bypasses travel and threat exposure; it never edits
deliveries, task progress, cargo quantities, notices, damage, collision or fear.
The standing hero must be grounded and within ordinary unload reach, beyond
remount reach. Each transfer uses the current Interact binding and an ordinary
running-world three-second hold, followed by release.

The ordered originals are:

- `remaining-30.png`: the first empty destination, both horses and full pack.
- `remaining-20.png`: after the first accepted transfer, at the first stand.
- `remaining-10.png`: after the second accepted transfer, at the second stand.
- `remaining-0.png`: the real Registry zero notice after the whole following
  90-second cinematic. The previous cargo pack/stands have naturally gone; this
  frame does not recreate them. Terminal 0/10/10/10 component quantities come
  from the separate pre-teardown completion callback and are labelled as such.

The first three frames require actual pack/stand quantities, both objective
languages, twelve noncolliding rope segments, and transformed segment endpoints
matching the animated halter/tack anchors. Camera projection checks keep both
horse centers, the current stand and rope endpoints inside the viewport. These
are framing and state checks, not proof that pixels are unoccluded or attractive.
The final frame requires one unexpired Registry notice containing both zero
strings, actual cargo teardown and the returning b16 HUD. It observes the full
b15 task duration and both ordinary clocks; it never skips, fast-forwards or
manually ticks the cinematic. Its seven-second visible notice lifetime is not
extended in production. Each screenshot pauses only its static accepted state
for a three-second streaming/render settle; metadata explicitly records that.

HUD drawing requests a screenshot with UI included, and its processed callback
must match the same engine frame and unchanged paused world time. Existing
measured HUD layout checks run before every request. The metadata still does
not establish that the zero text is legible: inspect all four untouched PNGs,
especially the post-cinematic notice, before any rendered acceptance.

`capture.json` is written after cleanup. The archive verifier requires one exact
four-frame run, original acknowledgement order, fresh in-folder sidecar, viewport,
byte-valid PNGs, actual quantities, source clocks, component endpoints, notice
lifetime and successful profile/input cleanup. It hashes and copies original
image/JSON bytes without re-encoding. Semantic failures retain the originals and
manifest associations as failure evidence. Missing files, stale metadata,
multiple runs, replayed log acknowledgements, mismatched clocks or incomplete
sequences fail. Tooling source checks include `test_cargo_capture.py`.

Clock gates allow explicit measurement quantization: the three-second world
hold must measure at least 2.999 s (wall 2.9 s), and the completed 90,000 ms
cinematic must measure at least 89.9 world seconds and 89.5 wall seconds. The
recorded timestamps remain unchanged for review; these tolerances do not alter
or shorten gameplay timers. The final original must be within one active world
second of cinematic completion, with its positive notice lifetime still intact.

Pending root: Unreal compilation, rendered automation at the declared actual
shader model, independent original PNG review, and any needed camera adjustment.
This source checkpoint claims none of those results.

## Corrections from the first actual rendered attempt

The initial SM6 1280×720 run exposed the English objective drawing at viewport
width outside its narrower header panel. It also paused 20/10 during delivery
barks, covering the drying stands. Its final screenshot was refused because the
Registry notice crossed the unchanged lower-story limit beside the b16 tracker,
boss readout and dialogue. The three original failed-run PNGs remain evidence;
there was no final-zero PNG and no accepted rendered sequence.

Objective drawing and its new runtime layout gate now share complete wrapped
rows measured against the panel's inner width, actual font heights and padding.
Upper gameplay obstacles and the adjacent dojo panel consume those same bounds.
The notice fallback searches actual free rectangles above the existing lower
story limit, checks all fixed panels, and first tries complete titles/details:
omitting a short Registry detail can otherwise add a taller condensed summary.
No subtitle, notice or HUD content is hidden to satisfy the capture.

The source capture waits for real delivery dialogue and its queue to clear on
ordinary active time before pausing 20/10. Metadata schema v2 records that quiet
state; its verifier requires it for all three cargo-stock originals. The final
zero timing and screenshot policy are unchanged. New host tests use independent
37/38 px measurements of the shipped Noto font and the existing production
free-region planner; they are capacity checks, not Canvas or image acceptance.

The prepared side-camera aim also moves the horses below the tracker. The v2
capture checks each horse's complete projected actor bounds against the actual
upper gameplay/tracker/notice/caption rectangles, and archives those rectangles.
This addresses the pack horse head/ears covered in the first failed originals;
mesh occlusion, overall composition and art still require original-image review.

The final-zero sidecar also requires the specific Registry title index in the
actual drawn layout's retained notice rows. A condensed-only summary cannot
qualify merely because an unseen zero string remains in StoryNotices.

## Boss overlap found in the second rendered attempt

The subsequent 720p suite passed its automation checks, but original-image
review rejected the final cargo image: the fixed boss panel crossed the tracker,
which covered its English name and description. The zero notice itself was
visible. The passing test result is not acceptance of that original sequence.

The shared boss readout now measures complete names, live defenses/weak points,
styles, active tells, countdowns and Muto/Marobashi hints at their existing sizes.
It keeps health, phase, barrier and warning meters. Story panels are allocated
around fixed objective/dojo/stealth bounds first; the boss then uses a measured
free region around the actual tracker, notices, captions, lower-story strips,
weapon/vitals, rhythm and aim area. That includes clear space below dialogue.
Later projected labels reserve the resulting boss rectangle. An unsupported
layout keeps all content and fails qualification instead of omitting rows.

The shared screenshot gate checks the exact boss draw rows, retained strings,
meters and every obstacle, and the existing campaign boss-telegraph screenshot
path invokes it from the actual HUD draw before requesting a frame. It requires
a visible HUD, the unchanged paused world time at native double precision, and
a processed PNG in the same engine frame, with delegate cleanup after every
shot or timeout. New host tests cover the rejected
geometry, all authored boss tells, conservative defense/weak-point/ward strings,
both action hints, JA/bilingual modes and 720p/1080p font capacity. These are
source/host checks only. The idle final cargo image does not qualify rendered
telegraphs, barrier/ward states or Muto/Marobashi hints; those need separate
actual captures. All previous failed originals and receipts stay unchanged.

Campaign originals use the existing capture archive. The verifier reads the
shot inventory and authored beat IDs from Git blobs at the recorded source
commit, requires the complete requested chapter sequence, and accepts only
original `LogTemp` acknowledgements of accepted fresh frames. It archives the
unchanged PNGs and their hashes with the exact assisted observation notes and
source/catalog identities. Missing, stale, duplicate, reordered, mismatched or
replayed records fail; already authenticated fresh partial originals remain
associated as failure evidence. A note naming a telegraph does not independently
prove its pixels or qualify other attack states. The campaign continuation now
omits both the success marker and index row after any rejected or missing frame.
