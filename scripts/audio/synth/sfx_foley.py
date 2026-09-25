"""Original foley synthesis (tier OWN) for sounds with no usable CC0 recording.

uguisubari (nightingale floor, ch06): the floor chirps because nails rub in their clamps when a board
flexes. The sound is a short friction squeak: a few quickly swept, slightly inharmonic partials with a
rough onset. It must stay distinct from real birdsong (chapter-06.md §5.6), so it is kept dry, woody and
short, with a board-creak body under it.
"""
from __future__ import annotations

import numpy as np

from dsp import (apply_reverb, bandpass, env_points, fade, lowpass, mix, modal, n_of, pan, phase_from_freq,
                 reverb_ir, rng, white, widen)

_IR = None


def room():
    global _IR
    if _IR is None:
        _IR = reverb_ir(0.8, rng('ir-vault-corridor'), bright=0.4, predelay_ms=6, size=0.8)
    return _IR


def nightingale_floor(r, v):
    n_chirps = 2 + v % 2
    total = n_of(0.45)
    parts = []
    t0 = 0.0
    for c in range(n_chirps):
        d = r.uniform(0.05, 0.11)
        n = n_of(d)
        tt = np.linspace(0, 1, n)
        f0 = r.uniform(1500, 2400)
        sweep = f0 * (1 + r.uniform(0.25, 0.6) * np.sin(np.pi * tt) ** 0.7)
        roughness = 1 + 0.35 * lowpass(white(n, r), 900)
        tone = sum(np.sin(phase_from_freq(sweep * k * (1 + 0.01 * k))) / k ** 1.3 for k in (1, 2, 3)) * roughness
        tone *= env_points(n, [(0, 0), (0.006, 1), (d * 0.7, 0.7), (d, 0)])
        parts.append((tone * r.uniform(0.6, 1.0), n_of(t0)))
        t0 += d + r.uniform(0.01, 0.05)
    creak = modal(total, [180, 410, 730], [0.08, 0.05, 0.03], [1, 0.5, 0.25], r) * 0.25
    y = mix(total, (creak, 0), *parts)
    y = bandpass(y, 120, 9000)
    return apply_reverb(pan(fade(y, 0.001, 0.02), r.uniform(-0.2, 0.2)), room(), 0.1)


def board_creak(r, v):
    """Old hinoki board flexing underfoot (quiet stealth-floor cue)."""
    d = 0.35
    n = n_of(d)
    stick = (r.random(n) < 900 / 48000).astype(float) * r.uniform(0.3, 1, n)
    body = modal(n_of(0.05), [210 + 30 * v, 470, 820], [0.03, 0.02, 0.012], [1, 0.4, 0.2], r)
    y = np.convolve(stick, body)[:n] * env_points(n, [(0, 0), (0.03, 1), (d * 0.8, 0.6), (d, 0)])
    return apply_reverb(pan(y, 0), room(), 0.08)


CUES = [
    ('fol_nightingale_floor', nightingale_floor, 6, {'M': -20.0}),
    ('fol_board_creak', board_creak, 3, {'M': -24.0}),
]
