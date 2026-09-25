"""Original melee sound design (tier OWN): blade whooshes shaped by a swing-speed profile, and parry /
guard layers (steel ring, scrape, sparks, body) meant to be stacked with real CC0 steel recordings
(OpenGameArt 'Medieval sound effects', see scripts/assets/manifests/audio_opengameart.json).

Physics notes:
  * A swing whoosh is turbulence noise whose level ~ v^6 and centre frequency ~ v (Strouhal), so both
    follow the blade-speed profile. A katana's hi (fuller) adds a tonal whistle (tachikaze) around
    a Strouhal frequency of a few hundred Hz to ~1.2 kHz; Doppler raises it on approach.
  * Steel-on-steel contact excites free-free bar modes (ratios 1, 2.756, 5.404, 8.933, 13.34).
    A held blade is damped by the hands, so modes decay in 0.2-0.7 s rather than ringing like a bell.
"""
from __future__ import annotations

import numpy as np

from dsp import (SR, rng, apply_reverb, bandpass, bell_curve, crackle, env_exp, env_points, fade, highpass, lowpass, mix,
                 modal, n_of, pan, pink, reverb_ir, tv_filter, white, widen, osc_sine, phase_from_freq, time_axis)

_IRS = {}


def space(name):
    if name not in _IRS:
        cfg = {'dojo': (0.9, 0.45, 6, 0.8), 'yard': (0.5, 0.55, 12, 1.4), 'hall': (1.6, 0.5, 10, 1.3)}[name]
        _IRS[name] = reverb_ir(cfg[0], rng('ir-' + name), bright=cfg[1], predelay_ms=cfg[2], size=cfg[3])
    return _IRS[name]


def swing(r, dur: float, peak_at: float, width: float, f_lo: float, f_hi: float, q: float,
          whistle: float = 0.0, whistle_f: float = 700.0, body: float = 0.3, pan_from=-0.6, pan_to=0.6) -> np.ndarray:
    n = n_of(dur)
    speed = bell_curve(n, peak_at, width)  # 0..1 normalised blade speed
    level = speed ** 3  # perceptual compromise between v^6 power and headroom
    centre = f_lo + (f_hi - f_lo) * speed
    # Doppler: approaching (before peak) slightly higher, receding lower
    t = np.linspace(0, 1, n)
    doppler = 1 + 0.06 * np.tanh((peak_at - t) / (width * 0.8))
    noise = pink(n, r) * 0.6 + white(n, r) * 0.4
    air = tv_filter(noise, 'bandpass', centre * doppler, q=q)
    air_hi = tv_filter(white(n, r), 'bandpass', np.minimum(centre * 2.6 * doppler, 16000), q=1.2) * 0.35
    y = (air + air_hi) * level
    if whistle > 0:
        wf = whistle_f * (0.55 + 0.45 * speed) * doppler * (1 + 0.004 * lowpass(white(n, r), 30))
        tone = np.sin(phase_from_freq(wf)) * (speed ** 5) * whistle
        tone += 0.3 * np.sin(2 * phase_from_freq(wf)) * (speed ** 6) * whistle
        y = y + tone * 0.35
    if body > 0:
        cloth = bandpass(pink(n, r), 120, 900) * bell_curve(n, peak_at * 0.8, width * 1.3) ** 2 * body
        y = y + cloth
    y /= np.max(np.abs(y)) + 1e-9
    posn = pan_from + (pan_to - pan_from) * np.clip((t - peak_at + width * 2) / (width * 4), 0, 1)
    return pan(y, posn)


def whoosh_katana_light(r, v):
    d = 0.42 + 0.04 * r.random()
    y = swing(r, d, 0.45 + 0.05 * r.normal(), 0.11, 350, 2600, 1.4, whistle=0.8, whistle_f=780 + 90 * r.normal(),
              body=0.25, pan_from=-0.7 + 0.2 * v, pan_to=0.7)
    return apply_reverb(y, space('dojo'), 0.08)


def whoosh_katana_heavy(r, v):
    d = 0.7 + 0.05 * r.random()
    y = swing(r, d, 0.5, 0.13, 220, 2000, 1.2, whistle=1.0, whistle_f=620 + 60 * r.normal(), body=0.45,
              pan_from=0.7, pan_to=-0.6)
    return apply_reverb(y, space('dojo'), 0.1)


def whoosh_bokuto(r, v):
    """Oak bokuto: no fuller, broader and lower turbulence than a steel blade."""
    d = 0.5
    y = swing(r, d, 0.48, 0.12, 180, 1400, 0.9, whistle=0.0, body=0.4, pan_from=-0.5, pan_to=0.5)
    return apply_reverb(y, space('dojo'), 0.1)


def whoosh_fukuro_shinai(r, v):
    """Split bamboo in a leather sleeve: airy with a papery rattle."""
    d = 0.48
    y = swing(r, d, 0.47, 0.12, 300, 2400, 0.8, whistle=0.0, body=0.3)
    n = y.shape[1]
    rattle = crackle(n, r, 900 * bell_curve(n, 0.47, 0.1), 1500, 6000, 0.0008) * 3.0
    y = y + pan(rattle / (np.max(np.abs(rattle)) + 1e-9) * 0.25, 0)
    return apply_reverb(y, space('dojo'), 0.1)


def whoosh_yari_thrust(r, v):
    d = 0.32
    y = swing(r, d, 0.35, 0.08, 500, 3200, 1.6, whistle=0.25, whistle_f=1100, body=0.35, pan_from=0.0, pan_to=0.05)
    return apply_reverb(y, space('yard'), 0.06)


def whoosh_naginata_sweep(r, v):
    d = 0.95
    y = swing(r, d, 0.52, 0.16, 160, 1600, 1.0, whistle=0.6, whistle_f=480, body=0.5, pan_from=-0.9, pan_to=0.9)
    return apply_reverb(y, space('yard'), 0.08)


def whoosh_kanabo(r, v):
    """Iron-studded club: slow, low, rough (studs add broadband turbulence)."""
    d = 0.9
    y = swing(r, d, 0.55, 0.15, 90, 900, 0.8, whistle=0.0, body=0.8, pan_from=0.6, pan_to=-0.6)
    n = y.shape[1]
    grit = bandpass(white(n, r), 2000, 7000) * bell_curve(n, 0.55, 0.12) ** 4 * 0.25
    y = y + pan(grit, 0)
    return apply_reverb(y, space('yard'), 0.08)


def whoosh_kusarigama_chain(r, v):
    """Weighted chain whirled: periodic whoosh at the rotation rate plus link jingle."""
    dur = 1.4
    n = n_of(dur)
    rate = 3.2 + 0.3 * v
    t = time_axis(n)
    rot = 0.5 + 0.5 * np.sin(2 * np.pi * rate * t) ** 8
    envl = env_points(n, [(0, 0), (0.15, 1), (dur - 0.2, 1), (dur, 0)])
    air = tv_filter(pink(n, r), 'bandpass', 300 + 1500 * rot, 1.0) * rot * envl
    links = crackle(n, r, 350 * envl * (0.4 + rot), 2500, 9000, 0.004) * 4
    y = air / (np.max(np.abs(air)) + 1e-9) + 0.25 * links / (np.max(np.abs(links)) + 1e-9)
    return apply_reverb(pan(y, 0.4 * np.sin(2 * np.pi * rate * t)), space('yard'), 0.07)


# ------------------------------------------------------------------------------------------------
# Parry / guard layers
# ------------------------------------------------------------------------------------------------
BAR = np.array([1.0, 2.756, 5.404, 8.933, 13.34, 18.64])


def steel_ring(r, f0: float, t60: float, dur: float, bright: float = 1.0) -> np.ndarray:
    n = n_of(dur)
    freqs = f0 * BAR * (1 + r.normal(0, 0.004, BAR.size))
    # torsional + lateral families: add a second, slightly offset family for richness
    freqs2 = f0 * 1.37 * BAR[:4] * (1 + r.normal(0, 0.006, 4))
    amps = np.array([0.7, 1.0, 0.8, 0.55, 0.35, 0.2]) * np.array([1, 1, bright, bright, bright, bright])
    decs = t60 * np.array([1.0, 0.8, 0.55, 0.4, 0.28, 0.18])
    y = modal(n, freqs, decs, amps, r) + 0.5 * modal(n, freqs2, decs[:4] * 0.8, amps[:4] * 0.6, r)
    return y


def contact(r, dur=0.006, lo=1800):
    n = n_of(dur)
    return highpass(white(n, r) * env_exp(n, dur / 3), lo)


def parry_clang(r, v):
    """Layer: the steel ring (edge-to-flat, damped by grip)."""
    f0 = [610, 690, 560, 740][v % 4] * (1 + 0.02 * r.normal())
    n = n_of(1.2)
    ring = steel_ring(r, f0, 0.55 + 0.1 * r.random(), 1.2)
    y = mix(n, (ring / np.max(np.abs(ring)), 0), (contact(r) * 0.5, 0))
    y = fade(y, 0, 0.15)
    return apply_reverb(widen(y, r, 0.35), space('yard'), 0.12)


def parry_scrape(r, v):
    """Layer: blade sliding along blade (stick-slip friction) as in awase / suriage."""
    dur = 0.16 + 0.05 * v
    n = n_of(dur)
    envl = env_points(n, [(0, 0), (0.005, 1), (dur * 0.6, 0.7), (dur, 0)])
    stick = (r.random(n) < 2200 / SR).astype(float) * r.uniform(0.3, 1, n)
    stick = np.convolve(stick, env_exp(n_of(0.002), 0.0007), 'same')
    fric = bandpass(white(n, r), 2500, 11000) * (0.4 + 0.6 * lowpass(np.abs(white(n, r)), 400))
    ring = steel_ring(r, 1650 + 200 * r.normal(), 0.08, dur) * 0.4
    y = (fric * 0.6 + bandpass(stick, 1500, 9000) * 2.5 + ring) * envl
    y = mix(n_of(dur + 0.1), (y, 0))
    return apply_reverb(widen(y / (np.max(np.abs(y)) + 1e-9), r, 0.5), space('yard'), 0.08)


def parry_sparks(r, v):
    """Layer: incandescent steel particles: dense crackle falling off in ~250 ms, very high band."""
    dur = 0.45
    n = n_of(dur)
    dens = 9000 * env_exp(n, 0.18) + 200 * env_exp(n, 0.4)
    y = crackle(n, r, dens, 3500, 15000, 0.0004, 0.8)
    fizz = bandpass(white(n, r), 6000, 16000) * env_exp(n, 0.07) * 0.25
    y = (y / (np.max(np.abs(y)) + 1e-9) + fizz)
    # sparks fly outward: widen strongly and let them drift
    st = widen(y, r, 0.9, decor_ms=6, mono_below_hz=2000)
    return fade(st, 0, 0.05)


def parry_body(r, v):
    """Layer: low body impact felt through the arms (weight of the exchange)."""
    dur = 0.35
    n = n_of(dur)
    f = 95 + 20 * v
    sweep = f * (1 + 0.6 * env_exp(n, 0.02))
    y = np.sin(phase_from_freq(sweep)) * env_exp(n, 0.14)
    y += lowpass(white(n, r), 380) * env_exp(n, 0.03) * 0.6
    return pan(y / np.max(np.abs(y)), 0)


def parry_full(r, v, heavy=False):
    n = n_of(1.3)
    clang = parry_clang(r, v)
    parts = [(clang, 0), (parry_sparks(r, v) * (0.35 if heavy else 0.22), n_of(0.002)),
             (parry_body(r, v) * (0.5 if heavy else 0.3), 0),
             (parry_scrape(r, v) * (0.25 if heavy else 0.15), n_of(0.01))]
    y = mix(n + n_of(1.0), *parts)
    return fade(y, 0, 0.3)


def guard_block(r, v):
    """Blade caught on the guard / flat: shorter ring, more thud, no sparks."""
    n = n_of(0.9)
    f0 = 480 + 60 * v
    ring = steel_ring(r, f0, 0.22, 0.9, bright=0.6)
    thud = parry_body(r, v)
    y = mix(n + n_of(1.0), (widen(ring / np.max(np.abs(ring)), r, 0.3) * 0.8, 0), (thud * 0.45, 0),
            (pan(contact(r, 0.01, 900), 0) * 0.4, 0))
    return apply_reverb(y, space('yard'), 0.1)


def bokuto_clack(r, v):
    """White-oak bokuto contact (kata practice): hard wood bar modes, no ring."""
    n = n_of(0.5)
    f0 = [740, 820, 690, 900][v % 4] * (1 + 0.02 * r.normal())
    body = modal(n, f0 * np.array([1, 2.76, 5.4, 8.93]), [0.13, 0.08, 0.05, 0.03], [1, 0.7, 0.4, 0.2], r)
    snap = highpass(white(n_of(0.004), r) * env_exp(n_of(0.004), 0.001), 1500) * 0.45
    y = mix(n, (body / np.max(np.abs(body)), 0), (snap, 0))
    return apply_reverb(widen(y, r, 0.25), space('dojo'), 0.14)


CUES = [
    ('mel_whoosh_katana_light', whoosh_katana_light, 4, {'M': -18.0}),
    ('mel_whoosh_katana_heavy', whoosh_katana_heavy, 3, {'M': -16.0}),
    ('mel_whoosh_bokuto', whoosh_bokuto, 3, {'M': -18.0}),
    ('mel_whoosh_fukuro_shinai', whoosh_fukuro_shinai, 3, {'M': -18.0}),
    ('mel_whoosh_yari_thrust', whoosh_yari_thrust, 3, {'M': -17.0}),
    ('mel_whoosh_naginata_sweep', whoosh_naginata_sweep, 3, {'M': -16.0}),
    ('mel_whoosh_kanabo', whoosh_kanabo, 2, {'M': -15.0}),
    ('mel_whoosh_kusarigama_chain', whoosh_kusarigama_chain, 2, {'M': -18.0}),
    ('mel_parry_layer_clang', parry_clang, 4, {'P': -1.0, 'limit': 6.0}),
    ('mel_parry_layer_scrape', parry_scrape, 3, {'M': -18.0}),
    ('mel_parry_layer_sparks', parry_sparks, 4, {'M': -20.0}),
    ('mel_parry_layer_body', parry_body, 2, {'P': -1.0, 'limit': 4.0}),
    ('mel_parry_full_light', lambda r, v: parry_full(r, v, False), 3, {'P': -1.0, 'limit': 6.0}),
    ('mel_parry_full_heavy', lambda r, v: parry_full(r, v, True), 3, {'P': -1.0, 'limit': 8.0}),
    ('mel_guard_block', guard_block, 3, {'P': -1.0, 'limit': 6.0}),
    ('mel_bokuto_clack', bokuto_clack, 4, {'P': -1.0, 'limit': 5.0}),
]
