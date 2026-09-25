"""Original UI sounds (tier OWN): a period-Japanese palette of hardwood ticks (hyoshigi), a rin bowl bell,
fusuma paper slides, soroban beads and a hanko seal, plus a cold glass chime for alien interfaces.

Each generator takes a seeded RNG and returns a stereo float array at dsp.SR.
"""
from __future__ import annotations

import numpy as np

from dsp import (SR, apply_reverb, bandpass, env_exp, env_points, fade, highpass, lowpass, mix, modal, n_of, pan,
                 pink, reverb_ir, widen, white, fm, crackle, osc_sine, time_axis)

ROOM = None


def room(r):
    global ROOM
    if ROOM is None:
        ROOM = reverb_ir(0.55, np.random.default_rng(7), bright=0.45, predelay_ms=4, size=0.6)
    return ROOM


def wood_tick(r, f0: float, dur: float = 0.16, hard: float = 1.0, t60: float = 0.05) -> np.ndarray:
    """Hardwood block / hyoshigi strike: three bar modes plus a contact transient."""
    n = n_of(dur)
    ratios = np.array([1.0, 2.76, 5.40, 8.93])
    f = f0 * ratios * (1 + r.normal(0, 0.006, 4))
    body = modal(n, f, [t60, t60 * 0.55, t60 * 0.3, t60 * 0.18], [1.0, 0.45 * hard, 0.22 * hard, 0.08 * hard], r)
    click = highpass(white(n_of(0.004), r) * env_exp(n_of(0.004), 0.0015), 2500) * 0.6 * hard
    y = mix(n, (body, 0), (click, 0))
    return y


def rin(r, f0: float, dur: float, t60: float, strike: float = 1.0, beat_hz: float = 1.3) -> np.ndarray:
    """Buddhist rin / bowl bell: bowl modes as close pairs (beating), soft mallet transient."""
    n = n_of(dur)
    ratios = [1.0, 2.71, 5.06, 7.82, 11.1]
    amps = [1.0, 0.55, 0.28, 0.12, 0.05]
    decs = [t60, t60 * 0.62, t60 * 0.38, t60 * 0.24, t60 * 0.15]
    freqs, t60s, a = [], [], []
    for k, (ra, am, de) in enumerate(zip(ratios, amps, decs)):
        f = f0 * ra
        split = beat_hz * (1 + 0.6 * k) * (1 + r.normal(0, 0.1))
        freqs += [f - split / 2, f + split / 2]
        t60s += [de, de * 0.93]
        a += [am * 0.5, am * 0.5]
    y = modal(n, freqs, t60s, a, r, attack=0.001)
    y += 0.25 * strike * wood_tick(r, f0 * 3.1, dur=dur, t60=0.012)[:n]
    return y


def paper_slide(r, dur: float, lo: float = 900, hi: float = 5500, rumble: float = 0.35) -> np.ndarray:
    """Fusuma / shoji slide: paper-and-wood friction noise with a rail rumble."""
    n = n_of(dur)
    shape = env_points(n, [(0, 0), (dur * 0.12, 1), (dur * 0.7, 0.8), (dur, 0)])
    jitter = 1 + 0.35 * lowpass(white(n, r), 35)
    hiss = bandpass(pink(n, r), lo, hi) * shape * jitter
    rail = bandpass(white(n, r), 90, 420) * shape * rumble * (1 + 0.5 * lowpass(white(n, r), 12))
    return hiss * 0.5 + rail


def ui_click(r, variant: int):
    f0 = [2050, 2210, 1930, 2380][variant % 4]
    y = wood_tick(r, f0, hard=0.9)
    return apply_reverb(pan(y, 0.0), room(r), 0.06)


def ui_hover(r, variant: int):
    f0 = [3150, 3350, 2980][variant % 3]
    y = wood_tick(r, f0, dur=0.08, hard=0.4, t60=0.018) * 0.5
    return apply_reverb(pan(y, 0.0), room(r), 0.04)


def ui_confirm(r, variant: int):
    """Wood tick + rin (A5); variant 1 is a two-note rising fourth for objective updates."""
    y1 = wood_tick(r, 2100, dur=1.8, hard=0.8)
    bell = rin(r, 880.0 if variant == 0 else 659.26, 1.8, 1.2)
    parts = [(y1 * 0.5, 0), (bell * 0.6, n_of(0.004))]
    if variant == 1:
        parts.append((rin(r, 880.0, 1.8 - 0.12, 1.1) * 0.55, n_of(0.12)))
    y = mix(n_of(1.8), *parts)
    return fade(apply_reverb(widen(y, r, 0.25), room(r), 0.12), 0, 0.3)


def ui_back(r, variant: int):
    n = n_of(0.3)
    tick = wood_tick(r, 1320, dur=0.3, hard=0.7, t60=0.06)
    slide = paper_slide(r, 0.14, 600, 3000, 0.1) * 0.25
    y = mix(n, (slide, 0), (tick, n_of(0.09)))
    return apply_reverb(pan(y, 0), room(r), 0.07)


def ui_error(r, variant: int):
    n = n_of(0.4)
    k1 = wood_tick(r, 420, dur=0.3, hard=0.3, t60=0.07)
    k2 = wood_tick(r, 395, dur=0.3, hard=0.3, t60=0.07)
    y = mix(n, (k1, 0), (k2 * 0.85, n_of(0.095)))
    y = lowpass(y, 2500)
    return apply_reverb(pan(y, 0), room(r), 0.08)


def ui_tab(r, variant: int):
    dur = 0.24 + 0.03 * variant
    y = paper_slide(r, dur, 1200, 6500, 0.2) * 0.6
    y = mix(n_of(dur + 0.08), (y, 0), (wood_tick(r, 1650, dur=0.08, hard=0.4, t60=0.02) * 0.35, n_of(dur - 0.02)))
    return apply_reverb(widen(y, r, 0.35), room(r), 0.07)


def ui_menu_open(r, variant: int):
    dur = 0.62
    slide = paper_slide(r, dur, 700, 5000, 0.45)
    stop = wood_tick(r, 900, dur=0.25, hard=0.6, t60=0.05) * 0.6
    y = mix(n_of(dur + 0.3), (slide, 0), (stop, n_of(dur - 0.03)))
    pos = np.linspace(-0.4, 0.3, y.size)
    return fade(apply_reverb(pan(y, pos), room(r), 0.1), 0.001, 0.05)


def ui_menu_close(r, variant: int):
    dur = 0.45
    slide = paper_slide(r, dur, 800, 5200, 0.4)[::-1] * 0.8
    stop = wood_tick(r, 780, dur=0.3, hard=0.9, t60=0.06)
    y = mix(n_of(dur + 0.3), (slide, 0), (stop, n_of(dur - 0.01)))
    pos = np.linspace(0.3, -0.3, y.size)
    return fade(apply_reverb(pan(y, pos), room(r), 0.1), 0.001, 0.05)


def ui_notify(r, variant: int):
    f = [1318.5, 1174.7][variant % 2]
    y = rin(r, f, 1.4, 0.8, strike=0.6, beat_hz=2.2) * 0.8
    return fade(apply_reverb(widen(y, r, 0.3), room(r), 0.1), 0, 0.2)


def ui_xor_credit(r, variant: int):
    """Soroban beads counted (production tallied) then a small rin: XOR credited."""
    n = n_of(1.6)
    parts = []
    t = 0.0
    for k in range(3 + variant):
        bead = wood_tick(r, 2900 + 120 * r.normal(), dur=0.09, hard=1.0, t60=0.022) * (0.55 + 0.1 * k)
        parts.append((bead, n_of(t)))
        t += 0.055 + 0.01 * r.random()
    parts.append((rin(r, 1046.5, 1.6 - t - 0.04, 0.9, strike=0.5) * 0.6, n_of(t + 0.04)))
    y = mix(n, *parts)
    return fade(apply_reverb(widen(y, r, 0.3), room(r), 0.1), 0, 0.2)


def ui_seal_stamp(r, variant: int):
    """Hanko seal on paper: signature / transaction approved in the wallet flow."""
    n = n_of(0.5)
    thump_f = 140 + 15 * variant
    body = modal(n, [thump_f, thump_f * 2.3, 610], [0.05, 0.03, 0.02], [1.0, 0.35, 0.15], r)
    paper = bandpass(white(n_of(0.03), r), 1500, 7000) * env_exp(n_of(0.03), 0.012) * 0.5
    press = lowpass(white(n_of(0.09), r), 500) * env_points(n_of(0.09), [(0, 0), (0.02, 1), (0.09, 0)]) * 0.35
    y = mix(n, (press, 0), (body * 0.9, n_of(0.018)), (paper, n_of(0.02)))
    return apply_reverb(pan(y, 0), room(r), 0.06)


def ui_slider_tick(r, variant: int):
    y = wood_tick(r, 4200, dur=0.04, hard=0.3, t60=0.008) * 0.4
    return pan(y, 0)


def ui_alien_chime(r, variant: int):
    """Credit House interface chime: cold FM glass, cyan. Never used for League / player UI."""
    dur = 1.2
    n = n_of(dur)
    base = [1567.98, 1396.9][variant % 2]
    e = env_exp(n, 0.7)
    tone = fm(np.full(n, base), 3.5, 1.8 * env_exp(n, 0.15)) * e
    tone2 = fm(np.full(n, base * 1.498), 3.5, 1.2 * env_exp(n, 0.1)) * env_exp(n, 0.5) * 0.5
    y = (tone + np.concatenate([np.zeros(n_of(0.09)), tone2[:-n_of(0.09)]])) * 0.4
    return fade(apply_reverb(widen(y, r, 0.5), reverb_ir(1.4, np.random.default_rng(11), bright=0.9), 0.25), 0, 0.2)


def ui_alien_deny(r, variant: int):
    dur = 0.55
    n = n_of(dur)
    f = np.full(n, 311.13)
    y = fm(f, 1.0, 2.5 * env_exp(n, 0.3)) * env_points(n, [(0, 0), (0.005, 1), (0.18, 0.8), (0.2, 0), (0.24, 0), (0.245, 1), (0.5, 0.0)])
    y = lowpass(y, 3500) * 0.5
    return apply_reverb(pan(y, 0), reverb_ir(0.8, np.random.default_rng(12), bright=0.8), 0.15)


# (name, generator, variants, loudness target {'M': max momentary LUFS})
CUES = [
    ('ui_click_wood', ui_click, 4, {'P': -3.0, 'limit': 3.0}),
    ('ui_hover_wood', ui_hover, 3, {'M': -26.0}),
    ('ui_confirm_rin', ui_confirm, 1, {'M': -19.0}),
    ('ui_objective_update_rin', lambda r, v: ui_confirm(r, 1), 1, {'M': -19.0}),
    ('ui_back_wood', ui_back, 2, {'M': -21.0}),
    ('ui_error_knock', ui_error, 2, {'M': -20.0}),
    ('ui_tab_paper', ui_tab, 3, {'M': -23.0}),
    ('ui_menu_open_fusuma', ui_menu_open, 1, {'M': -21.0}),
    ('ui_menu_close_fusuma', ui_menu_close, 1, {'M': -21.0}),
    ('ui_notify_bell', ui_notify, 2, {'M': -21.0}),
    ('ui_xor_credit_soroban', ui_xor_credit, 2, {'M': -19.0}),
    ('ui_wallet_seal_stamp', ui_seal_stamp, 2, {'P': -2.0, 'limit': 4.0}),
    ('ui_slider_tick', ui_slider_tick, 1, {'P': -12.0, 'limit': 0.0}),
    ('ui_alien_chime', ui_alien_chime, 2, {'M': -21.0}),
    ('ui_alien_deny', ui_alien_deny, 1, {'M': -21.0}),
]
