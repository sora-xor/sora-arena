#!/usr/bin/env python3
"""Render short original music stingers (tier OWN) to Content/SourceArt/Audio/Music/Stingers/.

Stingers answer USoraGameEvents: chapter start / complete, site restored, boss phase, player death, duel
point. They use the same instruments as the scores (engine.py) and the title theme's D miyako-bushi mode,
so they sit with the music beds. One-shots: max momentary loudness -16 LUFS, true peak <= -1 dBTP.

  python3 scripts/audio/music/render_stingers.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / 'synth'))

import dsp  # noqa: E402
import engine  # noqa: E402
from qa_audio import analyze  # noqa: E402

OUT = dsp.ROOT / 'Content/SourceArt/Audio/Music/Stingers'
KOTO, SHAKU, TAIKO, PERC, COLD = engine.Koto(), engine.Shakuhachi(), engine.Taiko(), engine.Perc(), engine.ColdSynth()
IR = dsp.reverb_ir(2.3, dsp.rng('title-hall'), bright=0.5, predelay_ms=18, size=1.4)
IR_COLD = dsp.reverb_ir(2.4, dsp.rng('flagship-hangar'), bright=0.7, predelay_ms=16, size=1.5)
M = engine.midi_of

# per-instrument trims so the layers balance (same relative levels as the title theme mix)
TRIM = {'koto': 6.5, 'shaku': -17.0, 'taiko': 8.0, 'perc': 6.0, 'cold': 0.0}


def build(events, seconds, ir=IR, wet=0.3):
    n = dsp.n_of(seconds)
    buf = np.zeros((2, n))
    for t, kind, sig in events:
        sig = sig * dsp.db(TRIM[kind])
        o = dsp.n_of(t)
        end = min(n, o + sig.shape[1])
        buf[:, o:end] += sig[:, : end - o]
    y = dsp.apply_reverb(buf, ir, wet)
    return y


def chapter_start(r):
    ev = [(0.0, 'perc', PERC.render('hyoshigi', 0.8, r)), (0.42, 'perc', PERC.render('hyoshigi', 0.9, r)),
          (1.0, 'taiko', TAIKO.render('odaiko', 0.95, r)), (1.0, 'perc', PERC.render('gong', 0.55, r) * 0.6),
          (1.05, 'shaku', SHAKU.render(M('D5'), 0.85, 1.6, r, muraiki=0.9, vib_delay=0.6, vib_depth=26))]
    return build(ev, 6.0)


def chapter_complete(r):
    ev = [(0.25 * i, 'koto', KOTO.render(M(n), 0.55 + 0.05 * i, 0.5, r)) for i, n in enumerate(['D4', 'G4', 'A4', 'D5'])]
    ev += [(1.0, 'perc', PERC.render('rin', 0.6, r)),
           (1.0, 'koto', KOTO.render(M('D3'), 0.5, 3.0, r)), (1.02, 'koto', KOTO.render(M('A3'), 0.42, 3.0, r)),
           (1.1, 'shaku', SHAKU.render(M('A4'), 0.7, 0.8, r)),
           (1.9, 'shaku', SHAKU.render(M('D5'), 0.75, 2.6, r, vib_delay=0.5, vib_depth=24, swell=0.2))]
    return build(ev, 7.5)


def site_restored(r):
    ev = [(0.0, 'koto', KOTO.render(M('A4'), 0.55, 0.3, r)), (0.18, 'koto', KOTO.render(M('Bb4'), 0.5, 0.3, r)),
          (0.36, 'koto', KOTO.render(M('D5'), 0.62, 1.5, r)), (0.36, 'perc', PERC.render('rin', 0.5, r))]
    return build(ev, 4.0)


def boss_phase(r):
    ev = [(0.0, 'taiko', TAIKO.render('odaiko', 1.0, r)), (0.0, 'cold', COLD.hit(0.9, r)),
          (0.05, 'cold', COLD.bell(M('F#5'), 0.5, r, 2.0)), (0.05, 'cold', COLD.bell(M('C6'), 0.4, r, 2.0)),
          (0.3, 'taiko', TAIKO.render('nagado', 0.8, r))]
    return build(ev, 4.0, IR_COLD, 0.3)


def player_death(r):
    ev = [(0.0, 'perc', PERC.render('gong', 0.35, r) * 0.7),
          (0.0, 'koto', KOTO.render(M('D3'), 0.5, 3.0, r, art='trem')),
          (0.3, 'shaku', SHAKU.render(M('A4'), 0.6, 2.2, r, bend=[(0, 0), (1.0, 0), (2.0, -200)], vib_depth=10,
                                      swell=0.0))]
    return build(ev, 6.0)


def duel_point(r):
    ev = [(0.0, 'perc', PERC.render('hyoshigi', 0.95, r)), (0.0, 'taiko', TAIKO.render('nagado', 0.6, r) * 0.6)]
    return build(ev, 2.0)


STINGERS = [('mus_sting_chapter_start', chapter_start, 'OnChapterStarted'),
            ('mus_sting_chapter_complete', chapter_complete, 'OnChapterCompleted'),
            ('mus_sting_site_restored', site_restored, 'OnSiteRestored'),
            ('mus_sting_boss_phase', boss_phase, 'OnBossPhase(Arrived / new phase)'),
            ('mus_sting_player_death', player_death, 'OnDied (victim = local player, not sparring)'),
            ('mus_sting_duel_point', duel_point, 'OnDied (bSparring) / dojo point scored')]


def main() -> int:
    rows = []
    fails = 0
    for name, fn, event in STINGERS:
        r = dsp.rng(name)
        y = fn(r)
        y = dsp.remove_dc(y)
        env = np.max(np.abs(y), axis=0)
        idx = np.where(env > dsp.db(-72))[0]
        y = dsp.fade(y[:, : idx[-1] + dsp.n_of(0.02)], 0.0005, 0.05)
        y = dsp.normalize_momentary(y, -16.0, -1.0, max_limit_db=3.0)
        path = OUT / f'{name}.wav'
        meta = dsp.write_wav(path, y)
        qa = analyze(path)
        fails += bool(qa['fail'])
        rows.append({'file': dsp.rel(path), 'bytes': meta['bytes'], 'sha256': meta['sha256'], 'piece': name,
                     'role': 'stinger', 'event': event, 'loop': False,
                     'generator': f'scripts/audio/music/render_stingers.py::{fn.__name__}', 'seed': name,
                     'qa': {k: qa[k] for k in qa if k != 'file'}})
        print(f"{'FAIL' if qa['fail'] else 'ok  '} {dsp.rel(path):70s} {qa['seconds']:5.2f}s Mmax {qa['momentary_max_lufs']} "
              f"TP {qa['true_peak_dbtp']}")
    manifest_path = dsp.ROOT / 'Content/SourceArt/Audio/Music/manifest.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {'schema_version': 2, 'tier': 'OWN', 'files': []}
    files = {row['file']: row for row in manifest.get('files', [])}
    for row in rows:
        files[row['file']] = row
    manifest['files'] = sorted(files.values(), key=lambda r: r['file'])
    manifest['stingers_generated_at_utc'] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    dsp.save_json(manifest_path, manifest)
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
