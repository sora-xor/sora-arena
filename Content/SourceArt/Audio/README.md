# Source audio

Source audio for *SORA Arena: Nyaagyu Rebellion*. Everything in this folder is **project-owned (tier OWN)** and
regenerates from the scripts in `scripts/audio/`. No third-party recording is stored here. The CC0 recordings
that the music renders use as instruments, and the CC0 layers the cue list points to, stay in the gitignored
`Local/ThirdPartyRaw/audio/`. Their ledger records (URL, license evidence, SHA-256, retrieval date) are in
`scripts/assets/manifests/audio_*.json`.

The cue mapping, buses and loudness targets are in [docs/audio.md](../../../docs/audio.md). The
machine-readable proposal is [`cues.proposed.json`](cues.proposed.json). The engineering lane moves it into
`Content/Data`.

## Layout

| Path | What | Count |
|---|---|---|
| `Original/UI/` | Period-Japanese UI palette: hardwood ticks (hyoshigi), rin bowl bell, fusuma paper slides, soroban beads (XOR credited), hanko seal (wallet signature), plus cold glass chimes for Credit House interfaces | 28 |
| `Original/Melee/` | Blade whooshes shaped by a swing-speed profile (katana light/heavy, bokutō, fukuro-shinai, yari, naginata, kanabō, kusarigama chain), parry/guard layers (steel ring, scrape, sparks, body) and full parries, bokutō clacks | 49 |
| `Original/Weapons/` | Credit House weapons: Plasma Matchlock charge / hold loop / fire, Arc Carbine, Pulse Carbine, Needle SMG, Shock Emitter start/loop/stop, energy beam start/loop/stop, cell eject, coil-matchlock whine | 26 |
| `Original/Shields/` | Barrier hum loop, hits, break, regeneration | 8 |
| `Original/Alien/` | Alien machinery loops (flagship engine core, Ledger Engine 5/8 abacus ostinato, drone hover ×2, seizure field, debt terminal), sky-seam tear (ch01.b13), debt-seal clamp | 9 |
| `Original/Telegraphs/` | Boss audio telegraphs: cyan lock (900 ms), amber cleave (900 / 1500 ms), margin-call riser (1500 ms) | 4 |
| `Original/Foley/` | Nightingale floor (uguisubari) chirps, board creaks | 9 |
| `Music/mus_title_nyaagyu_wind/` | 「猫柳生の風」 title theme: intro + seamless loop, MIDI | 2 WAV + MIDI |
| `Music/mus_ch03_occupation_stealth/` | 「占領の街」 stealth loop, 4 synchronous stems + alert mix, MIDI | 5 WAV + MIDI |
| `Music/mus_ch07_flagship_battle/` | 「複利号」 flagship battle loop, synth + taiko stems + mix, MIDI | 3 WAV + MIDI |
| `Music/Stingers/` | Chapter start/complete, site restored, boss phase, player death, duel point | 6 |

Each music folder also has a `<name>.json` sidecar with tempo, bars, loop length and handoff sample, the stem
list and measured loudness. `Original/manifest.json` and `Music/manifest.json` hold one record per file. Each
record has the SHA-256, the generator function and seed, the loudness target and the full QA measurements.

## Formats

- **WAV:** 48 kHz, 24-bit PCM, stereo.
- **Loops:** each loop carries a RIFF `smpl` loop over the whole file and is periodic by construction, so the
  wrap is sample-exact:
  - noise is filtered circularly (FFT);
  - every oscillator and LFO completes whole cycles per loop;
  - reverb and bus processing run through `dsp.circ`, which renders three periods and keeps the middle one;
  - music events are placed modulo the loop length, so ringing notes wrap into the loop start.
- **Stems:** stems share the mix gain and the mix's limiter gain curve, so they sum exactly to the loop mix.
- **Title intro:** the intro file includes its own reverb tail. Start the loop at `handoff_sample` (698,182)
  while the intro keeps ringing.

## Regenerate

```sh
python3 -m pip install --user -r scripts/audio/requirements.txt   # numpy, scipy, soundfile, pyloudnorm
python3 scripts/audio/fetch_cc0_audio.py        # CC0 sources -> Local/ThirdPartyRaw/audio (~3 GB)
python3 scripts/audio/synth/build_sfx.py        # Original/** (pure synthesis, needs no downloads)
python3 scripts/audio/music/render_music.py     # Music/** (needs the VCSL and Wikimedia samples)
python3 scripts/audio/music/render_stingers.py  # Music/Stingers/**
python3 scripts/audio/build_cue_proposal.py     # cues.proposed.json
python3 scripts/audio/validate_audio.py         # ledger + hashes + listen-free QA
```

Renders are deterministic. Every cue, variant and piece has its own seed, and re-running gives byte-identical
WAVs on this machine (checked 2026-09-25). A different numpy or scipy build may change the least significant
bits. The recorded SHA-256 values are for numpy 1.23.5, scipy 1.13.1 and soundfile 0.13.1 on Python 3.9.6
(macOS arm64).

## How the music is made

The scores are Python code in `scripts/audio/music/scores/`. `scripts/audio/music/engine.py` renders them. Its
voices:

- **Koto:** the Dan Tranh from VCSL (CC0), a plucked zither with finger picks. It supports oshide press bends,
  vibrato and tremolo. Sample pitch is measured, not taken from file names: the VCSL names are an octave low,
  and several strings are 10–50 cents off. The measured pitches are in `scripts/audio/music/sample_tuning.json`.
- **Shakuhachi:** additive resynthesis of a CC0 shakuhachi recording (Wikimedia Commons
  `File:Shakuhachi-flute-440Hz.ogg`, originally Freesound sound 268183, CC0). The voice uses the recording's measured harmonic amplitudes and slightly
  stretched partial ratios, plus its own breath residual, extracted by removing the harmonics from the STFT. Each
  note has an atari scoop, meri bends, delayed yuri vibrato and muraiki breath accents.
- **Taiko:** a stand-in built from VCSL concert bass drums, toms and claves, re-pitched and layered:
  - ōdaiko: bass drum plus skin plus bachi click;
  - nagadō: small bass drum plus low tom;
  - shime: high tom with a stick;
  - kachi: tom rim.
- **Other VCSL instruments:** claves (hyoshigi), slit drum (mokugyo), woodblock, gong, Nepalese hand bells
  (rin), bowed psaltery and wine glasses.
- **Credit House layer:** original synthesis (poly-BLEP detuned saws, FM glass, sub pulses, modal metal hits).

## Honest status

These are working source assets and a reproducible pipeline. **They are not final AAA audio.**

- **Stand-in instruments:**
  - the koto is a Vietnamese zither;
  - the taiko is re-voiced Western drums;
  - the shakuhachi is resynthesised from a single A4 tone.

  The plan's route to AAA music is still performers who release recordings under CC0 or assign the rights
  (plan §3.12). The scores and MIDI files carry over to real instruments.
- **No listening test.** Nothing has been checked by ear. QA is numerical only: loudness, true peak, DC,
  clipping, silence and loop continuity. A human listening and mix review is required (plan §4.3).
- **Synthetic SFX:** the SFX are synthesised. That fits the sci-fi, UI, telegraph and alien sounds. For melee
  and foley, the synthesised layers should be stacked with the CC0 steel and wood recordings listed in the cue
  proposal. Use our own foley sessions where the cue list says `needed`.
- **Master limiting:** the music masters use 2.6–4.7 dB of peak limiting on the loudest taiko hits (recorded in
  each sidecar as `master_limiter_max_gr_db`).
