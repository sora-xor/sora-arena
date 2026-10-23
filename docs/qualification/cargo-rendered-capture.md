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
