#!/usr/bin/env python3
"""Listen-free audio QA for SORA Arena source audio.

For every WAV it measures: sample peak, true peak (4x oversampled), integrated loudness (ITU-R BS.1770-4
via pyloudnorm), maximum momentary loudness (400 ms), RMS, DC offset, full-scale clipping runs, leading /
trailing silence and, for loops (files with a RIFF 'smpl' loop or listed as loops), wrap continuity:
  * sample jump at the wrap vs. the file's own 99.9th-percentile sample-to-sample step,
  * high-frequency (> 6 kHz) click energy in a 5 ms window across the wrap vs. 200 interior windows,
  * curvature (second difference) across the wrap vs. the file's own 99.9th percentile,
  * level of the last vs. the first 100 ms (reported only: a loop may start on a downbeat).

Usage:
  python3 scripts/audio/qa_audio.py Content/SourceArt/Audio            # all WAVs under a folder
  python3 scripts/audio/qa_audio.py file.wav --json report.json
Exit status is 1 if any file fails a hard check (clipping, true peak > -0.5 dBTP, DC, all-silent, loop click).
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

sys.path.insert(0, str(Path(__file__).resolve().parent / 'synth'))
import dsp  # noqa: E402

DC_LIMIT = 10 ** (-54 / 20)       # |mean| above -54 dBFS is flagged
TP_LIMIT_DB = -0.5                # hard fail above this true peak
SILENCE_DB = -60.0


def read_smpl_loop(path: Path):
    data = path.read_bytes()
    if data[:4] != b'RIFF':
        return None
    pos = 12
    while pos + 8 <= len(data):
        cid = data[pos:pos + 4]
        size = struct.unpack('<I', data[pos + 4:pos + 8])[0]
        if cid == b'smpl' and size >= 36 + 24:
            body = data[pos + 8:pos + 8 + size]
            nloops = struct.unpack('<I', body[28:32])[0]
            if nloops:
                _cue, _typ, start, end, _frac, _count = struct.unpack('<6I', body[36:60])
                return start, end
        pos += 8 + size + (size & 1)
    return None


def hf_energy(seg: np.ndarray) -> float:
    return float(np.mean(seg ** 2))


def wrap_click(x: np.ndarray, sr: int) -> dict:
    """x: [channels, n] one loop period."""
    n = x.shape[1]
    ctx = min(4096, n // 2)
    sos = signal.butter(4, 6000, 'highpass', fs=sr, output='sos')
    win = int(0.005 * sr)

    def measure(center: int) -> float:
        seg = np.take(x, np.arange(center - ctx, center + ctx) % n, axis=1)
        hp = signal.sosfilt(sos, seg, axis=1)
        return hf_energy(hp[:, ctx - win // 2: ctx + win // 2])

    at_wrap = measure(0)
    rs = np.random.default_rng(0)
    interior = np.array([measure(int(c)) for c in rs.integers(ctx, n - ctx, 200)]) if n > 4 * ctx else np.array([at_wrap])
    p95 = float(np.percentile(interior, 95)) + 1e-20
    steps = np.abs(np.diff(x, axis=1))
    p999 = float(np.percentile(steps, 99.9)) + 1e-12
    jump = float(np.max(np.abs(x[:, 0] - x[:, -1])))
    # curvature across the wrap (a click is a kink even when the step itself is small)
    curv = np.abs(np.diff(x, 2, axis=1))
    c999 = float(np.percentile(curv, 99.9)) + 1e-12
    wrap_curv = float(max(np.max(np.abs(x[:, 0] - 2 * x[:, -1] + x[:, -2])),
                          np.max(np.abs(x[:, 1] - 2 * x[:, 0] + x[:, -1]))))
    tail = x[:, -int(0.1 * sr):]
    head = x[:, :int(0.1 * sr)]
    lvl = 20 * np.log10((np.sqrt(np.mean(tail ** 2)) + 1e-9) / (np.sqrt(np.mean(head ** 2)) + 1e-9))
    return {
        # informational: > 6 kHz energy at the wrap vs. interior windows (high on loops that start on a hit)
        'wrap_hf_ratio_vs_p95': round(at_wrap / p95, 3),
        'wrap_jump_vs_p999_step': round(jump / p999, 3),
        'wrap_curvature_vs_p999': round(wrap_curv / c999, 3),
        # informational: a loop that starts on a downbeat is legitimately louder at its head than its tail
        'wrap_level_delta_db': round(float(lvl), 2),
        'loop_click': bool(jump / p999 > 3.0 or wrap_curv / c999 > 3.0),
    }


def analyze(path: Path, force_loop: bool = False) -> dict:
    info = sf.info(str(path))
    data, sr = sf.read(str(path), always_2d=True)
    x = data.T.astype(np.float64)
    res = {'file': str(path), 'sr': sr, 'channels': info.channels, 'subtype': info.subtype,
           'seconds': round(x.shape[1] / sr, 3)}
    peak = float(np.max(np.abs(x)))
    res['sample_peak_dbfs'] = round(dsp.to_db(peak), 2)
    if sr == dsp.SR:
        res['true_peak_dbtp'] = round(dsp.true_peak_db(x), 2)
        res['integrated_lufs'] = round(dsp.integrated_lufs(x), 2)
        res['momentary_max_lufs'] = round(dsp.momentary_max_lufs(x), 2)
    res['rms_dbfs'] = round(dsp.to_db(float(np.sqrt(np.mean(x ** 2)))), 2)
    # DC: whole-file mean for material >= 1 s; for short transients the mean of an asymmetric decay is not
    # a bias, so use the mean of the final 20 % (where a real bias would persist) instead.
    if x.shape[1] >= sr:
        dc = np.abs(x.mean(axis=1))
    elif x.shape[1] >= sr // 4:
        dc = np.abs(x[:, -int(0.2 * x.shape[1]):].mean(axis=1))
    else:  # < 250 ms: too short for a meaningful DC estimate (the 12 Hz DC filter still ran)
        dc = np.zeros(x.shape[0])
    res['dc_offset_dbfs'] = round(dsp.to_db(float(dc.max())), 1) if dc.any() else None
    full = np.abs(x) >= (1.0 - 2.0 ** -22)
    runs = 0
    for ch in full:
        d = np.diff(np.concatenate([[0], ch.astype(int), [0]]))
        starts, ends = np.where(d == 1)[0], np.where(d == -1)[0]
        runs = max(runs, int(np.max(ends - starts)) if starts.size else 0)
    res['max_fullscale_run'] = runs
    env = np.max(np.abs(x), axis=0)
    above = np.where(env > 10 ** (SILENCE_DB / 20))[0]
    res['leading_silence_ms'] = round(1000 * (above[0] / sr), 1) if above.size else None
    res['trailing_silence_ms'] = round(1000 * ((x.shape[1] - 1 - above[-1]) / sr), 1) if above.size else None
    loop = read_smpl_loop(path)
    res['loop'] = list(loop) if loop else None
    is_loop = force_loop or loop is not None
    if is_loop:
        s, e = loop if loop else (0, x.shape[1] - 1)
        res.update(wrap_click(x[:, s:e + 1], sr))
    fails = []
    if runs >= 2:
        fails.append('clipping')
    if res.get('true_peak_dbtp', -99) > TP_LIMIT_DB:
        fails.append('true_peak')
    if dc.max() > DC_LIMIT:
        fails.append('dc_offset')
    if not above.size:
        fails.append('silent')
    if is_loop and res.get('loop_click'):
        fails.append('loop_click')
    warns = []
    if not is_loop and res['leading_silence_ms'] and res['leading_silence_ms'] > 20:
        warns.append('leading_silence>20ms')
    if sr != dsp.SR:
        warns.append(f'sample_rate_{sr}')
    res['fail'] = fails
    res['warn'] = warns
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('paths', nargs='+')
    ap.add_argument('--json')
    args = ap.parse_args()
    files = []
    for p in map(Path, args.paths):
        files += sorted(p.rglob('*.wav')) if p.is_dir() else [p]
    rows = [analyze(f) for f in files]
    bad = 0
    for r in rows:
        flag = 'FAIL ' + ','.join(r['fail']) if r['fail'] else 'ok'
        bad += bool(r['fail'])
        loop = (f" loop jump={r.get('wrap_jump_vs_p999_step')} curv={r.get('wrap_curvature_vs_p999')} "
                f"lvl={r.get('wrap_level_delta_db')}dB") if r['loop'] else ''
        print(f"{flag:14s} {Path(r['file']).name:52s} {r['seconds']:7.2f}s TP {r.get('true_peak_dbtp')} "
              f"I {r.get('integrated_lufs')} Mmax {r.get('momentary_max_lufs')} DC {r['dc_offset_dbfs']}{loop}")
    if args.json:
        Path(args.json).write_text(json.dumps(rows, indent=1) + '\n')
    print(f'{len(rows)} files, {bad} failing')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
