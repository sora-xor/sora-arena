# Ward culvert stream: source checkpoint, 2026-10-26 UTC

This is source work on top of the uncompiled ward-gate checkpoint `3f115e51` and its documentation
follow-up `81f18daa`. It does not qualify an Unreal build, imported SoundWave, audible mix, or release.
Claude retains the exclusive engine/Blender lane for the r3 character export and readback.

## Recording and derivative

- Source: Thimras, [Park ambiences](https://opengameart.org/content/park-ambiences), CC0-1.0. The existing
  raw ledger is `scripts/assets/manifests/audio_opengameart.json`; only its river WAV was retrieved.
- Exact raw file: 99,072,736 bytes, SHA-256
  `da0c0c9b1249a83a1611cc116d5737b0864a8db9f45f1ae8dcc079d0f7c0bbbf`.
  Retrieval receipt: `Saved/Qualification/2026-10-26/stream-audio-source/retrieval.json` in the source worktree.
- The source window is 272–321 s, including a 1 s filter pre-roll. Processing averages stereo to mono,
  removes rumble with a second-order 80 Hz high-pass, makes a 45 s loop with a 3 s equal-power crossfade,
  removes circular DC and applies gain alone to the ambience loudness target.
- Derivative: `Content/SourceArt/Audio/CC0/Ambience/cc0_amb_stream_loop.wav`, 48 kHz / PCM24 mono,
  6,480,112 bytes, SHA-256 `e7259184cb084f4fd5aa0ae1b1fe2aa6bd5dfe631e531114d8a4bde1e2b97438`.
  RIFF `smpl` loop: frames 0–2,159,999 inclusive.
- Numerical QA: −26.0 LUFS integrated, −10.69 dBTP, no clipping, DC or loop-click failures. These
  measurements do not establish that the recording sounds appropriate.
- The 88 existing CC0 derivative rows and file hashes remain unchanged. There are now 89 derivatives
  totalling 107,823,144 bytes, within the 500 MB budget. The schema-2 ledger and generated asset notices
  include the new file. Raw audio remains ignored; the derivative uses Git LFS.

`build_cc0_audio.py --stream-only` reads only the pinned river file. `--stream-only --check` checks both
the committed derivative bytes and a deterministic fresh render. Partial builds now merge by derivative
path, preserving siblings from the same source. Changing their source identity or rights is refused.

## Runtime source changes

`audio.json.emitters.ward_culvert` selects `amb.stream`. Staging the ward positions it at
`(-6200, -650, -85)` cm, just above the culvert water. Its existing `ambient_emitter` attenuation has a 3 m
inner radius and 35 m falloff. It is a spatial Ambience loop, not a global bed; other stream locations have
not yet been bound.

Emitter lifetime belongs to the staging actor. Repeated starts at the same location keep one logical
loop; a moved emitter replaces that loop. Fieldcraft clear stops its actor's emitters, and audio ticks reap
destroyed owners even while paused. Spatial components use world pause. Stopping a loop also cancels
pending delayed starts, so clearing a beat cannot later spawn that old loop.

Current runtime data has 115 cues, 99 with waves and 16 without. The stream's `needs` field still calls
for listening, ecology and in-game mix review. The field recording contains Adelaide wildlife; it has not
been accepted as a Japanese soundscape.

## Verification and remaining gates

Targeted host checks passed before this checkpoint: 17 audio processing/ledger tests, 11 import-spec
tests, runtime-data validation, deterministic stream rebuild, and an independent comparison of all 88
pre-existing derivative rows and bytes.

Signed source `ac46015eca7675785b93ca5441f26dfce2ee807c` (tree
`44936fe8afb3970d4fbf19ee3b3aeb0fbfc858e4`) then passed **55/55** selected source gates: 27 tooling,
22 assets and 6 audio. The checkout stayed clean and unchanged. Gameplay and Rust groups were not rerun.
The report is `Saved/Qualification/2026-10-26/ward-stream-source/report.json` in the source-validation
worktree, SHA-256 `fa31811c7e9d01b01be75ad7320d1580352653b13605ef21fc1cd873b66d3d25`.
The separate inventory, 55-log, LFS-pointer and preserved-derivative audit is `independent-review.json`,
SHA-256 `580039c5377c612cb011a1afb0e3d34aa49a9f844c0ed226c6fa2195460940f3`.

The following new UE fixtures exist but have **not been compiled or run**:

- `SoraArena.Audio.PositionedEmitterLifetime`: voiced spatial request and world position; duplicate
  prevention; independent owners; explicit clear; paused destruction; resume; restage and relocation.
- `SoraArena.Campaign.WardGate.Ambience`: staging the actual ward starts its culvert loop, and clearing
  and restaging fieldcraft leaves exactly one stream.

After Claude explicitly returns the lane: compile the editor, import the changed audio, validate the
generated SoundWave and buses, run the two fixtures and existing audio/ward/landing regressions, then
review ordinary play, attenuation, pause/retry and the audible mix. Numerical QA does not replace that
review. The first release and final art remain incomplete.
