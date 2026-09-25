#!/usr/bin/env python3
"""Render every original SFX cue (tier OWN) to Content/SourceArt/Audio/Original/<Category>/.

  python3 scripts/audio/synth/build_sfx.py            # all cues
  python3 scripts/audio/synth/build_sfx.py --only mel_  # cues whose name starts with a prefix

Output: 48 kHz / 24-bit stereo WAV, deterministic (seeded per cue and variant), loudness-normalised to the
per-cue target (docs/audio.md §4), DC-free, true peak <= -1 dBTP, loops carry a RIFF 'smpl' loop over the
whole file. A manifest with generator, seed, SHA-256 and QA measurements is written next to the files.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import dsp  # noqa: E402
import sfx_foley  # noqa: E402
import sfx_melee  # noqa: E402
import sfx_scifi  # noqa: E402
import sfx_ui  # noqa: E402
from qa_audio import analyze  # noqa: E402

OUT = dsp.ROOT / 'Content/SourceArt/Audio/Original'
CATEGORY = [('ui_', 'UI'), ('mel_', 'Melee'), ('wpn_', 'Weapons'), ('shd_', 'Shields'), ('amb_alien', 'Alien'),
            ('sfx_alien', 'Alien'), ('tel_', 'Telegraphs'), ('fol_', 'Foley')]
MODULES = [sfx_ui, sfx_melee, sfx_scifi, sfx_foley]


def category(name: str) -> str:
    for prefix, cat in CATEGORY:
        if name.startswith(prefix):
            return cat
    raise ValueError(name)


def trim_tail(x: np.ndarray, floor_db: float = -72.0, keep: float = 0.02) -> np.ndarray:
    env = np.max(np.abs(x), axis=0)
    idx = np.where(env > dsp.db(floor_db))[0]
    end = min(x.shape[1], (idx[-1] if idx.size else 0) + dsp.n_of(keep))
    return dsp.fade(x[:, :end], 0.0, min(0.02, end / dsp.SR / 4))


def trim_head(x: np.ndarray, floor_db: float = -70.0) -> np.ndarray:
    env = np.max(np.abs(x), axis=0)
    idx = np.where(env > dsp.db(floor_db))[0]
    start = max(0, (idx[0] if idx.size else 0) - dsp.n_of(0.001))
    return x[:, start:]


def render(module, name, fn, variant, target):
    seed = f'{name}:{variant}'
    r = dsp.rng(seed)
    y = fn(r, variant)
    if y.ndim == 1:
        y = np.vstack([y, y])
    is_loop = bool(target.get('loop'))
    if is_loop:
        y = dsp.remove_dc_circular(y)
        y = dsp.normalize_integrated(y, target['I'], -1.0, max_limit_db=0.0)
    else:
        y = trim_head(trim_tail(dsp.remove_dc(y)))
        y = dsp.fade(y, 0.0005, 0.0)
        lim = target.get('limit', 3.0)
        if 'P' in target:  # transient one-shots: fixed transient limiting, peak-referenced
            y = dsp.peak_master(y, target['P'], lim)
        elif 'M' in target:
            y = dsp.normalize_momentary(y, target['M'], -1.0, max_limit_db=lim)
        else:
            y = dsp.normalize_integrated(y, target['I'], -1.0, max_limit_db=lim)
    return y, seed, is_loop


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default='')
    args = ap.parse_args()
    rows, failures = [], 0
    for module in MODULES:
        for name, fn, variants, target in module.CUES:
            if not name.startswith(args.only):
                continue
            for v in range(variants):
                y, seed, is_loop = render(module, name, fn, v, target)
                fname = f'{name}.wav' if variants == 1 else f'{name}_{v + 1:02d}.wav'
                path = OUT / category(name) / fname
                meta = dsp.write_wav(path, y, loop=(0, y.shape[1] - 1) if is_loop else None)
                qa = analyze(path, force_loop=is_loop)
                failures += bool(qa['fail'])
                rows.append({
                    'file': dsp.rel(path), 'bytes': meta['bytes'], 'sha256': meta['sha256'],
                    'cue': name, 'variant': v + 1, 'category': category(name), 'loop': is_loop,
                    'generator': f'scripts/audio/synth/{module.__name__}.py::{fn.__name__}', 'seed': seed,
                    'target': {k: v2 for k, v2 in target.items() if k not in ('loop',)},
                    'qa': {k: qa[k] for k in qa if k not in ('file',)},
                })
                print(f"{'FAIL' if qa['fail'] else 'ok  '} {dsp.rel(path):70s} {qa['seconds']:6.2f}s "
                      f"Mmax {qa.get('momentary_max_lufs')} I {qa.get('integrated_lufs')} TP {qa.get('true_peak_dbtp')} "
                      f"{qa['fail'] or ''}", flush=True)
    manifest_path = OUT / 'manifest.json'
    existing = {}
    if manifest_path.exists() and args.only:
        import json
        for row in json.loads(manifest_path.read_text())['files']:
            existing[row['file']] = row
    for row in rows:
        existing[row['file']] = row
    dsp.save_json(manifest_path, {
        'schema_version': 2,
        'tier': 'OWN',
        'license': 'Project-owned original work (SORA Arena); generated, no third-party audio inside',
        'generator_scripts': ['scripts/audio/synth/build_sfx.py', 'scripts/audio/synth/dsp.py',
                              'scripts/audio/synth/sfx_ui.py', 'scripts/audio/synth/sfx_melee.py',
                              'scripts/audio/synth/sfx_scifi.py', 'scripts/audio/synth/sfx_foley.py'],
        'regenerate': 'python3 scripts/audio/synth/build_sfx.py',
        'format': '48 kHz / 24-bit PCM WAV, stereo; loops carry a RIFF smpl loop spanning the whole file',
        'loudness_policy': 'docs/audio.md §4 (sustained one-shots: max momentary LUFS "M"; transient one-shots: peak-referenced "P" after "limit" dB of oversampled soft-clip density; loops: integrated LUFS "I"; TP <= -1 dBTP)',
        'generated_at_utc': datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        'files': sorted(existing.values(), key=lambda r: r['file']),
    })
    print(f'{len(rows)} files rendered, {failures} failing QA')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
