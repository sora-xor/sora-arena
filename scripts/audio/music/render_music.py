#!/usr/bin/env python3
"""Render the original music scores to Content/SourceArt/Audio/Music/ (tier OWN).

  python3 scripts/audio/music/render_music.py              # all pieces
  python3 scripts/audio/music/render_music.py title        # pieces whose module name contains 'title'

For each piece it writes:
  <name>_intro.wav        (if the piece has an intro; includes the intro's own reverb tail — start the loop at
                           `handoff_sample` while the intro keeps playing)
  <name>_loop.wav         seamless loop (RIFF smpl loop over the whole file)
  <name>_stem_<x>.wav     loop stems (same length and gain as the loop; stems sum to the loop mix)
  <name>.mid              the score as Standard MIDI (loopStart / loopEnd markers)
  <name>.json             sidecar: tempo, bars, loop points, stems, measured loudness
and updates Content/SourceArt/Audio/Music/manifest.json.
"""
from __future__ import annotations

import argparse
import importlib
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / 'scores'))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / 'synth'))

import dsp  # noqa: E402
import engine  # noqa: E402
from qa_audio import analyze  # noqa: E402

OUT = dsp.ROOT / 'Content/SourceArt/Audio/Music'
PIECES = ['title_nyaagyu_wind', 'occupation_stealth', 'flagship_battle']


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('only', nargs='?', default='')
    args = ap.parse_args()
    manifest_path = OUT / 'manifest.json'
    import json
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {'files': []}
    files = {row['file']: row for row in manifest.get('files', [])}
    pieces_meta = {p['name']: p for p in manifest.get('pieces', [])}
    failures = 0
    for mod_name in PIECES:
        if args.only not in mod_name:
            continue
        mod = importlib.import_module(mod_name)
        piece = mod.build()
        print(f'== {piece.name}: {piece.bpm} BPM, intro {piece.intro_bars} bars, loop {piece.loop_bars} bars, '
              f'{len(piece.events)} events', flush=True)
        parts = engine.render_piece(piece, seed=piece.name)
        mastered = engine.master(parts, piece.target_lufs)
        folder = OUT / piece.name
        outputs = []
        if 'intro' in mastered:
            p = folder / f'{piece.name}_intro.wav'
            meta = dsp.write_wav(p, mastered['intro'])
            outputs.append((p, meta, 'intro', False))
        p = folder / f'{piece.name}_loop.wav'
        meta = dsp.write_wav(p, mastered['loop'], loop=(0, mastered['loop'].shape[1] - 1))
        outputs.append((p, meta, 'loop', True))
        stems = mastered['stems']
        if len(stems) > 1:
            for stem, y in stems.items():
                p = folder / f'{piece.name}_stem_{stem}.wav'
                meta = dsp.write_wav(p, y, loop=(0, y.shape[1] - 1))
                outputs.append((p, meta, f'stem:{stem}', True))
        midi_path = folder / f'{piece.name}.mid'
        engine.write_midi(piece, midi_path)
        rows = []
        for path, meta, role, is_loop in outputs:
            qa = analyze(path, force_loop=is_loop)
            failures += bool(qa['fail'])
            row = {'file': dsp.rel(path), 'bytes': meta['bytes'], 'sha256': meta['sha256'], 'piece': piece.name,
                   'role': role, 'loop': is_loop, 'qa': {k: qa[k] for k in qa if k != 'file'}}
            files[row['file']] = row
            rows.append(row)
            print(f"{'FAIL' if qa['fail'] else 'ok  '} {dsp.rel(path):82s} {qa['seconds']:6.2f}s I {qa.get('integrated_lufs')} "
                  f"TP {qa.get('true_peak_dbtp')} {qa['fail'] or ''}"
                  + (f" wrap jump {qa.get('wrap_jump_vs_p999_step')} curv {qa.get('wrap_curvature_vs_p999')}" if is_loop else ''),
                  flush=True)
        import hashlib
        files[dsp.rel(midi_path)] = {'file': dsp.rel(midi_path), 'bytes': midi_path.stat().st_size,
                                     'sha256': hashlib.sha256(midi_path.read_bytes()).hexdigest(),
                                     'piece': piece.name, 'role': 'score-midi', 'loop': False}
        sidecar = {
            'name': piece.name, 'title': piece.title, 'description': piece.description,
            'bpm': piece.bpm, 'beats_per_bar': piece.beats_per_bar, 'intro_bars': piece.intro_bars,
            'loop_bars': piece.loop_bars, 'sample_rate': dsp.SR,
            'handoff_sample': parts['handoff'] if 'intro' in mastered else 0,
            'loop_length_samples': parts['loop_n'],
            'loop_seconds': round(parts['loop_n'] / dsp.SR, 4),
            'master_gain_db': mastered['gain_db'], 'master_limiter_max_gr_db': mastered['limiter_max_gr_db'],
            'target_integrated_lufs': piece.target_lufs,
            'stems': sorted(stems) if len(stems) > 1 else [],
            'loop_mix_is': ('sum of stems ' + ', '.join(piece.reference_stems)) if piece.reference_stems else 'sum of all stems',
            'score_module': f'scripts/audio/music/scores/{mod_name}.py',
            'files': rows,
        }
        dsp.save_json(folder / f'{piece.name}.json', sidecar)
        pieces_meta[piece.name] = {k: sidecar[k] for k in sidecar if k != 'files'}
    dsp.save_json(manifest_path, {
        'schema_version': 2,
        'tier': 'OWN',
        'license': 'Project-owned original compositions and renders (SORA Arena). Rendered with CC0 samples '
                   '(VCSL, Wikimedia Commons File:Shakuhachi-flute-440Hz.ogg) used as instruments; see '
                   'scripts/assets/manifests/audio_vcsl.json and audio_wikimedia.json',
        'sample_sources': ['scripts/assets/manifests/audio_vcsl.json', 'scripts/assets/manifests/audio_wikimedia.json'],
        'regenerate': 'python3 scripts/audio/fetch_cc0_audio.py --source vcsl --source wikimedia && '
                      'python3 scripts/audio/music/render_music.py',
        'format': '48 kHz / 24-bit PCM WAV stereo; loops carry a RIFF smpl loop over the whole file',
        'loudness_policy': 'docs/audio.md §4: music loop mixes -16 LUFS integrated, true peak <= -1 dBTP; '
                           'stems share the mix gain (they sum to the loop mix) and are not individually normalised',
        'generated_at_utc': datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        'pieces': sorted(pieces_meta.values(), key=lambda p: p['name']),
        'files': sorted(files.values(), key=lambda r: r['file']),
    })
    print('failing QA:', failures)
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
