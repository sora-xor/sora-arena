"""Shared DSP for SORA Arena original sound design (tier OWN).

Everything here is deterministic (seeded RNG) so every WAV under Content/SourceArt/Audio/Original and
Content/SourceArt/Audio/Music can be regenerated bit-for-bit from the scripts that call it.

Dependencies: numpy, scipy, soundfile, pyloudnorm (pip install --user; see scripts/audio/requirements.txt).
"""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

SR = 48000
ROOT = Path(__file__).resolve().parents[3]
TWO_PI = 2.0 * np.pi


# ----------------------------------------------------------------------------------------------
# Basics
# ----------------------------------------------------------------------------------------------
def rng(seed: int | str) -> np.random.Generator:
    if isinstance(seed, str):
        seed = int(hashlib.sha256(seed.encode()).hexdigest()[:12], 16)
    return np.random.default_rng(seed)


def n_of(seconds: float) -> int:
    return int(round(seconds * SR))


def time_axis(n: int) -> np.ndarray:
    return np.arange(n, dtype=np.float64) / SR


def db(x: float) -> float:
    return 10.0 ** (x / 20.0)


def to_db(x: float) -> float:
    return 20.0 * np.log10(max(abs(x), 1e-12))


def pad_to(x: np.ndarray, n: int) -> np.ndarray:
    if x.shape[-1] >= n:
        return x[..., :n]
    pad = [(0, 0)] * (x.ndim - 1) + [(0, n - x.shape[-1])]
    return np.pad(x, pad)


def mix(n: int, *parts: tuple[np.ndarray, int]) -> np.ndarray:
    """Sum (signal, offset_samples) pairs into a buffer of length n (mono or stereo [2, n])."""
    stereo = any(p.ndim == 2 for p, _ in parts)
    out = np.zeros((2, n) if stereo else n)
    for sig, off in parts:
        if stereo and sig.ndim == 1:
            sig = np.vstack([sig, sig])
        end = min(n, off + sig.shape[-1])
        if end > off:
            out[..., off:end] += sig[..., : end - off]
    return out


# ----------------------------------------------------------------------------------------------
# Envelopes
# ----------------------------------------------------------------------------------------------
def env_exp(n: int, t60: float) -> np.ndarray:
    """Exponential decay reaching -60 dB after t60 seconds."""
    return np.exp(-6.907755 * time_axis(n) / max(t60, 1e-4))


def env_adsr(n: int, a: float, d: float, s: float, r: float, curve: float = 3.0) -> np.ndarray:
    na, nd, nr = n_of(a), n_of(d), n_of(r)
    ns = max(0, n - na - nd - nr)
    parts = [
        (np.linspace(0, 1, max(na, 1), endpoint=False)) ** (1.0 / 1.5),
        s + (1 - s) * np.exp(-curve * np.linspace(0, 1, max(nd, 1))),
        np.full(ns, s),
        s * np.exp(-curve * 2 * np.linspace(0, 1, max(nr, 1))),
    ]
    e = np.concatenate(parts)
    return pad_to(e, n)


def env_points(n: int, points: list[tuple[float, float]], shape: str = 'linear') -> np.ndarray:
    """Piecewise envelope from (time_seconds, value) points. shape: linear | exp (log-domain)."""
    ts = np.array([p[0] for p in points]) * SR
    vs = np.array([p[1] for p in points], dtype=np.float64)
    x = np.arange(n)
    if shape == 'exp':
        return np.exp(np.interp(x, ts, np.log(np.maximum(vs, 1e-6))))
    return np.interp(x, ts, vs)


def fade(x: np.ndarray, fin: float = 0.002, fout: float = 0.01) -> np.ndarray:
    y = x.copy()
    ni, no = n_of(fin), n_of(fout)
    if ni > 0:
        y[..., :ni] *= np.sin(np.linspace(0, np.pi / 2, ni)) ** 2
    if no > 0:
        y[..., -no:] *= np.cos(np.linspace(0, np.pi / 2, no)) ** 2
    return y


def bell_curve(n: int, peak: float, width: float) -> np.ndarray:
    t = np.linspace(0, 1, n)
    return np.exp(-0.5 * ((t - peak) / width) ** 2)


# ----------------------------------------------------------------------------------------------
# Noise
# ----------------------------------------------------------------------------------------------
def white(n: int, r: np.random.Generator) -> np.ndarray:
    return r.standard_normal(n)


def colored(n: int, r: np.random.Generator, exponent: float, circular: bool = False) -> np.ndarray:
    """1/f^exponent noise via FFT shaping (exponent 1 pink, 2 brown). Periodic when circular."""
    m = n if circular else int(2 ** np.ceil(np.log2(n + 1)))
    spec = np.fft.rfft(r.standard_normal(m))
    f = np.fft.rfftfreq(m, 1 / SR)
    f[0] = f[1]
    spec /= f ** (exponent / 2.0)
    y = np.fft.irfft(spec, m)[:n]
    return y / (np.std(y) + 1e-12)


def pink(n, r, circular=False):
    return colored(n, r, 1.0, circular)


def brown(n, r, circular=False):
    return colored(n, r, 2.0, circular)


def circular_band_noise(n: int, r: np.random.Generator, lo: float, hi: float, slope_db_oct: float = 0.0) -> np.ndarray:
    """Perfectly periodic band-limited noise (loops seamlessly at length n)."""
    spec = np.fft.rfft(r.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    mask = ((f >= lo) & (f <= hi)).astype(float)
    # soft edges (1/3 octave)
    mask = np.maximum(mask, np.exp(-0.5 * (np.log2(np.maximum(f, 1) / lo) / 0.33) ** 2) * (f < lo))
    mask = np.maximum(mask, np.exp(-0.5 * (np.log2(np.maximum(f, 1) / hi) / 0.33) ** 2) * (f > hi))
    if slope_db_oct:
        mask *= (np.maximum(f, lo) / lo) ** (slope_db_oct / 6.0206)
    y = np.fft.irfft(spec * mask, n)
    return y / (np.std(y) + 1e-12)


# ----------------------------------------------------------------------------------------------
# Filters
# ----------------------------------------------------------------------------------------------
def _sos(kind: str, freq, order: int = 2):
    nyq = SR / 2 * 0.999
    if isinstance(freq, (list, tuple)):
        freq = [min(max(f, 5.0), nyq) for f in freq]
    else:
        freq = min(max(freq, 5.0), nyq)
    return signal.butter(order, freq, btype=kind, fs=SR, output='sos')


def lowpass(x, f, order=2):
    return signal.sosfilt(_sos('lowpass', f, order), x, axis=-1)


def highpass(x, f, order=2):
    return signal.sosfilt(_sos('highpass', f, order), x, axis=-1)


def bandpass(x, lo, hi, order=2):
    return signal.sosfilt(_sos('bandpass', [lo, hi], order), x, axis=-1)


def zerophase_highpass(x, f, order=2):
    return signal.sosfiltfilt(_sos('highpass', f, order), x, axis=-1)


def biquad_coeffs(kind: str, f0: float, q: float, gain_db: float = 0.0):
    """RBJ cookbook biquad."""
    f0 = min(max(f0, 10.0), SR * 0.49)
    w0 = TWO_PI * f0 / SR
    cw, sw = np.cos(w0), np.sin(w0)
    alpha = sw / (2 * q)
    a_lin = 10 ** (gain_db / 40)
    if kind == 'lowpass':
        b = [(1 - cw) / 2, 1 - cw, (1 - cw) / 2]
        a = [1 + alpha, -2 * cw, 1 - alpha]
    elif kind == 'highpass':
        b = [(1 + cw) / 2, -(1 + cw), (1 + cw) / 2]
        a = [1 + alpha, -2 * cw, 1 - alpha]
    elif kind == 'bandpass':
        b = [alpha, 0, -alpha]
        a = [1 + alpha, -2 * cw, 1 - alpha]
    elif kind == 'peak':
        b = [1 + alpha * a_lin, -2 * cw, 1 - alpha * a_lin]
        a = [1 + alpha / a_lin, -2 * cw, 1 - alpha / a_lin]
    elif kind == 'notch':
        b = [1, -2 * cw, 1]
        a = [1 + alpha, -2 * cw, 1 - alpha]
    else:
        raise ValueError(kind)
    b = np.array(b) / a[0]
    a = np.array(a) / a[0]
    return b, a


def peq(x, f0, q, gain_db):
    b, a = biquad_coeffs('peak', f0, q, gain_db)
    return signal.lfilter(b, a, x, axis=-1)


def tv_filter(x: np.ndarray, kind: str, freqs: np.ndarray, q: float = 0.707, block: int = 64) -> np.ndarray:
    """Time-varying biquad (block-wise coefficient update, DF2T state carried across blocks)."""
    y = np.zeros_like(x)
    zi = np.zeros(2)
    freqs = np.broadcast_to(freqs, x.shape)
    for start in range(0, len(x), block):
        end = min(len(x), start + block)
        b, a = biquad_coeffs(kind, float(freqs[start]), q)
        y[start:end], zi = signal.lfilter(b, a, x[start:end], zi=zi)
    return y


def resonator_bank(x: np.ndarray, freqs, qs, gains) -> np.ndarray:
    y = np.zeros_like(x)
    for f, q, g in zip(freqs, qs, gains):
        b, a = biquad_coeffs('bandpass', f, q)
        y += g * signal.lfilter(b, a, x)
    return y


# ----------------------------------------------------------------------------------------------
# Oscillators / synthesis
# ----------------------------------------------------------------------------------------------
def phase_from_freq(freq: np.ndarray, phase0: float = 0.0) -> np.ndarray:
    return phase0 + TWO_PI * np.cumsum(freq) / SR


def osc_sine(freq, n=None, phase0=0.0):
    if np.isscalar(freq):
        return np.sin(phase0 + TWO_PI * freq * time_axis(n))
    return np.sin(phase_from_freq(np.asarray(freq, dtype=np.float64), phase0))


def osc_saw_blep(freq: np.ndarray) -> np.ndarray:
    """Band-limited-ish saw via additive partials up to Nyquist (vectorised for moderate lengths)."""
    freq = np.asarray(freq, dtype=np.float64)
    ph = phase_from_freq(freq)
    top = int(SR / 2 / max(float(np.max(freq)), 20.0))
    top = max(1, min(top, 60))
    y = np.zeros_like(ph)
    for k in range(1, top + 1):
        # fade partials that would alias as freq rises
        weight = np.clip((SR / 2 - k * freq) / (0.1 * SR), 0, 1)
        y += weight * np.sin(k * ph) / k
    return y * (2 / np.pi)


def fm(carrier: np.ndarray, ratio: float, index: np.ndarray, feedback: float = 0.0) -> np.ndarray:
    carrier = np.asarray(carrier, dtype=np.float64)
    mod = np.sin(phase_from_freq(carrier * ratio))
    return np.sin(phase_from_freq(carrier) + index * mod)


def modal(n: int, freqs, t60s, amps, r: np.random.Generator | None = None, attack: float = 0.0005) -> np.ndarray:
    """Sum of exponentially decaying sinusoids (modal synthesis) with random phases."""
    t = time_axis(n)
    y = np.zeros(n)
    for f, t60, a in zip(freqs, t60s, amps):
        if f >= SR / 2 * 0.98 or a == 0:
            continue
        ph = r.uniform(0, TWO_PI) if r is not None else 0.0
        y += a * np.sin(TWO_PI * f * t + ph) * np.exp(-6.907755 * t / t60)
    na = n_of(attack)
    if na > 1:
        y[:na] *= np.linspace(0, 1, na)
    return y


def karplus(n: int, freq: float, r: np.random.Generator, damping: float = 0.996, bright: float = 0.5) -> np.ndarray:
    """Extended Karplus-Strong plucked string (used only for synthetic alien plucks)."""
    period = SR / freq
    p = int(period)
    frac = period - p
    buf = r.uniform(-1, 1, p)
    buf = lowpass(buf, 2000 + bright * 10000, 1)
    y = np.zeros(n)
    idx = 0
    last = 0.0
    for i in range(n):
        cur = buf[idx]
        nxt = buf[(idx + 1) % p]
        val = damping * ((1 - frac) * cur + frac * nxt) * 0.5 + damping * 0.5 * last
        last = cur
        y[i] = cur
        buf[idx] = val
        idx = (idx + 1) % p
    return y


def crackle(n: int, r: np.random.Generator, density_hz: np.ndarray | float, lo: float, hi: float,
            decay: float = 0.0015, amp_jitter: float = 0.6) -> np.ndarray:
    """Sparse random impulses (sparks, electric crackle, embers) filtered into a band."""
    dens = np.broadcast_to(np.asarray(density_hz, dtype=np.float64), (n,))
    impulses = (r.random(n) < dens / SR).astype(float)
    impulses *= (1 - amp_jitter) + amp_jitter * r.random(n)
    impulses *= r.choice([-1.0, 1.0], n)
    k = env_exp(n_of(decay * 8), decay) * r.standard_normal(n_of(decay * 8))
    y = signal.fftconvolve(impulses, k)[:n]
    return bandpass(y, lo, hi, 2)


def circ(fn, x: np.ndarray, periods: int = 3) -> np.ndarray:
    """Run an LTI process on a periodic signal and return one steady-state period (seamless loops).

    The input is tiled `periods` times, processed, and the middle period is returned, so filter
    memory and reverb tails from the "previous" loop pass are included exactly (tail < one period).
    """
    n = x.shape[-1]
    reps = [1] * (x.ndim - 1) + [periods]
    y = fn(np.tile(x, reps))
    mid = (periods // 2) * n
    return y[..., mid:mid + n]


def place_circular(buf: np.ndarray, sig: np.ndarray, offset: int) -> None:
    """Add sig into buf at offset, wrapping past the end back to the start (loops)."""
    n = buf.shape[-1]
    idx = (offset + np.arange(sig.shape[-1])) % n
    if buf.ndim == 1:
        np.add.at(buf, idx, sig if sig.ndim == 1 else sig.mean(axis=0))
    else:
        s2 = sig if sig.ndim == 2 else np.vstack([sig, sig])
        for ch in range(buf.shape[0]):
            np.add.at(buf[ch], idx, s2[ch])


def crackle_periodic(n: int, r: np.random.Generator, density_hz, lo: float, hi: float, decay: float = 0.0015,
                     amp_jitter: float = 0.6) -> np.ndarray:
    """Periodic version of crackle() for seamless loops."""
    dens = np.broadcast_to(np.asarray(density_hz, dtype=np.float64), (n,))
    impulses = (r.random(n) < dens / SR).astype(float)
    impulses *= ((1 - amp_jitter) + amp_jitter * r.random(n)) * r.choice([-1.0, 1.0], n)
    k = env_exp(n_of(decay * 8), decay) * r.standard_normal(n_of(decay * 8))
    return circ(lambda s: bandpass(signal.fftconvolve(s, k)[: s.size], lo, hi, 2), impulses)


# ----------------------------------------------------------------------------------------------
# Space
# ----------------------------------------------------------------------------------------------
def pan(mono: np.ndarray, position: float | np.ndarray) -> np.ndarray:
    """Constant-power pan, position -1 (L) .. +1 (R); position may be an array."""
    p = (np.asarray(position) + 1) * np.pi / 4
    return np.vstack([mono * np.cos(p), mono * np.sin(p)])


def widen(mono: np.ndarray, r: np.random.Generator, amount: float = 0.5, decor_ms: float = 12.0,
          mono_below_hz: float = 200.0) -> np.ndarray:
    """Decorrelated stereo from mono: two different short noise-burst decorrelators, bass kept mono."""
    k = max(8, n_of(decor_ms / 1000))
    e = env_exp(k, decor_ms / 1000)
    sides = []
    for _ in range(2):
        h = r.standard_normal(k) * e
        h /= np.sqrt(np.sum(h ** 2)) + 1e-12
        sides.append(highpass(signal.fftconvolve(mono, h)[: len(mono)], mono_below_hz))
    out = np.vstack([mono + amount * sides[0], mono + amount * sides[1]])
    return out / np.sqrt(1 + amount ** 2)


def reverb_ir(seconds: float, r: np.random.Generator, bright: float = 0.5, predelay_ms: float = 8.0,
              early: int = 12, size: float = 1.0, low_t60_mult: float = 1.2) -> np.ndarray:
    """Synthetic stereo IR: early reflections + frequency-dependent exponential diffuse tail."""
    n = n_of(seconds * 1.3 + predelay_ms / 1000)
    t = time_axis(n)
    out = np.zeros((2, n))
    bands = [(20, 400, low_t60_mult), (400, 2500, 1.0), (2500, 8000, 0.65 + 0.3 * bright), (8000, 20000, 0.35 + 0.35 * bright)]
    pd = n_of(predelay_ms / 1000)
    for ch in range(2):
        tail = np.zeros(n)
        noise = r.standard_normal(n)
        for lo, hi, mult in bands:
            b = bandpass(noise, lo, min(hi, SR * 0.45), 2)
            tail += b * np.exp(-6.907755 * t / (seconds * mult))
        onset = np.clip((t - predelay_ms / 1000) / (0.02 * size + 1e-3), 0, 1) ** 2
        tail *= onset
        for _ in range(early):
            tap = pd + n_of(r.uniform(0.002, 0.045) * size)
            if tap < n:
                out[ch, tap] += r.uniform(0.2, 0.7) * r.choice([-1, 1])
        out[ch] += tail * 0.12
    out /= np.sqrt(np.sum(out ** 2) / 2) + 1e-12
    return out


def apply_reverb(x: np.ndarray, ir: np.ndarray, wet: float, dry: float = 1.0) -> np.ndarray:
    if x.ndim == 1:
        x = np.vstack([x, x])
    n = x.shape[1] + ir.shape[1] - 1
    wet_sig = np.vstack([signal.fftconvolve(x[0], ir[0]), signal.fftconvolve(x[1], ir[1])])
    y = pad_to(dry * x, n) + wet * wet_sig
    return y


def apply_reverb_circular(x: np.ndarray, ir: np.ndarray, wet: float, dry: float = 1.0) -> np.ndarray:
    """Reverb for loops: circular convolution so the tail wraps into the loop start (seamless)."""
    if x.ndim == 1:
        x = np.vstack([x, x])
    n = x.shape[1]
    out = dry * x.copy()
    for ch in range(2):
        full = signal.fftconvolve(x[ch], ir[ch])
        wrapped = full[:n].copy()
        rest = full[n:]
        while rest.size:
            k = min(n, rest.size)
            wrapped[:k] += rest[:k]
            rest = rest[k:]
        out[ch] += wet * wrapped
    return out


# ----------------------------------------------------------------------------------------------
# Dynamics and loudness
# ----------------------------------------------------------------------------------------------
_K1_B = np.array([1.53512485958697, -2.69169618940638, 1.19839281085285])
_K1_A = np.array([1.0, -1.69065929318241, 0.73248077421585])
_K2_B = np.array([1.0, -2.0, 1.0])
_K2_A = np.array([1.0, -1.99004745483398, 0.99007225036621])


def k_weight(x: np.ndarray) -> np.ndarray:
    return signal.lfilter(_K2_B, _K2_A, signal.lfilter(_K1_B, _K1_A, x, axis=-1), axis=-1)


def as_channels(x: np.ndarray) -> np.ndarray:
    return x[None, :] if x.ndim == 1 else x


def momentary_max_lufs(x: np.ndarray) -> float:
    """Maximum momentary loudness (400 ms window, 100 ms hop), ITU-R BS.1770 K-weighting at 48 kHz."""
    xc = as_channels(x)
    w = n_of(0.4)
    if xc.shape[1] < w:
        xc = np.pad(xc, ((0, 0), (0, w - xc.shape[1])))
    kw = k_weight(xc) ** 2
    cs = np.cumsum(np.pad(kw.sum(axis=0), (1, 0)))
    hop = n_of(0.1)
    starts = np.arange(0, xc.shape[1] - w + 1, hop)
    ms = (cs[starts + w] - cs[starts]) / w
    return float(-0.691 + 10 * np.log10(np.max(ms) + 1e-20))


def integrated_lufs(x: np.ndarray) -> float:
    import pyloudnorm as pyln
    xc = as_channels(x)
    w = n_of(0.4)
    if xc.shape[1] < w:
        xc = np.pad(xc, ((0, 0), (0, w - xc.shape[1])))
    meter = pyln.Meter(SR)
    return float(meter.integrated_loudness(xc.T))


def true_peak_db(x: np.ndarray) -> float:
    xc = as_channels(x)
    up = signal.resample_poly(xc, 4, 1, axis=-1)
    return to_db(float(np.max(np.abs(up))))


def limiter_gain(x: np.ndarray, ceiling_db: float = -1.0, release: float = 0.08, lookahead: float = 0.002) -> np.ndarray:
    """Gain curve (n,) of a look-ahead true-peak-ish limiter (4x oversampled detector, smoothed release)."""
    from scipy.ndimage import maximum_filter1d
    xc = as_channels(x).astype(np.float64)
    ceiling = db(ceiling_db)
    up = signal.resample_poly(np.max(np.abs(xc), axis=0), 4, 1)
    peak = np.maximum.reduceat(np.abs(up), np.arange(0, up.size, 4))[: xc.shape[1]]
    peak = pad_to(peak, xc.shape[1])
    la = max(1, n_of(lookahead))
    pk = maximum_filter1d(peak, size=2 * la + 1, origin=0)
    target = np.minimum(1.0, ceiling / np.maximum(pk, 1e-12))
    coef = np.exp(-1.0 / (release * SR))
    g = np.empty_like(target)
    cur = 1.0
    for i in range(target.size):  # instant attack (the detector already looks ahead), exponential release
        t = target[i]
        cur = t if t < cur else t + (cur - t) * coef
        g[i] = cur
    return g


def limiter(x: np.ndarray, ceiling_db: float = -1.0, release: float = 0.08, lookahead: float = 0.002) -> np.ndarray:
    g = limiter_gain(x, ceiling_db, release, lookahead)
    return x * g


def _normalize(x: np.ndarray, measure, target: float, tp_ceiling: float, max_limit_db: float, release: float):
    """Find the pre-gain whose limited output meets `target` (by bisection), never limiting more than
    max_limit_db of true-peak overshoot. If the target needs more, the loudest allowed result is kept
    (the achieved value is what QA reports)."""
    g0 = target - measure(x)
    tp0 = true_peak_db(x)
    g_max = tp_ceiling + max_limit_db - tp0  # pre-gain at which overshoot equals the allowance

    def run(g):
        y = x * db(g)
        if true_peak_db(y) > tp_ceiling:
            y = limiter(y, tp_ceiling - 0.1, release)
        return y

    if g0 <= tp_ceiling - tp0:  # no limiting needed
        return x * db(g0)
    lo, hi = min(g0, tp_ceiling - tp0), min(g_max, g0 + max_limit_db)
    if measure(run(hi)) <= target:
        return run(hi)
    for _ in range(10):
        mid = 0.5 * (lo + hi)
        if measure(run(mid)) < target:
            lo = mid
        else:
            hi = mid
    return run(0.5 * (lo + hi))


def normalize_integrated(x: np.ndarray, target_lufs: float, tp_ceiling: float = -1.0, max_limit_db: float = 3.0,
                         release: float = 0.08):
    return _normalize(x, integrated_lufs, target_lufs, tp_ceiling, max_limit_db, release)


def normalize_momentary(x: np.ndarray, target_lufs_m: float, tp_ceiling: float = -1.0, max_limit_db: float = 3.0,
                        release: float = 0.012):
    return _normalize(x, momentary_max_lufs, target_lufs_m, tp_ceiling, max_limit_db, release)


def soft_clip(x: np.ndarray, drive_db: float) -> np.ndarray:
    """4x-oversampled tanh saturation, normalised so a full-scale input stays at full scale. Reduces the
    crest factor of transient noise (gunshots, impacts) by roughly drive_db."""
    if drive_db <= 0:
        return x
    g = db(drive_db)
    peak = float(np.max(np.abs(x))) + 1e-12
    up = signal.resample_poly(x / peak, 4, 1, axis=-1)
    up = np.tanh(g * up) / np.tanh(g)
    return signal.resample_poly(up, 1, 4, axis=-1)[..., : x.shape[-1]] * peak


def peak_master(x: np.ndarray, tp_target: float, drive_db: float) -> np.ndarray:
    y = soft_clip(x, drive_db)
    y = y * db(tp_target - true_peak_db(y))
    if true_peak_db(y) > tp_target + 0.05:
        y = limiter(y, tp_target - 0.1, release=0.012)
    return y


def remove_dc(x: np.ndarray) -> np.ndarray:
    return zerophase_highpass(x, 12.0, 2)


def remove_dc_circular(x: np.ndarray) -> np.ndarray:
    """DC removal for loops without breaking periodicity (FFT bins below 12 Hz zeroed)."""
    xc = as_channels(x)
    n = xc.shape[1]
    spec = np.fft.rfft(xc, axis=-1)
    f = np.fft.rfftfreq(n, 1 / SR)
    spec[:, f < 12.0] = 0
    y = np.fft.irfft(spec, n, axis=-1)
    return y[0] if x.ndim == 1 else y


# ----------------------------------------------------------------------------------------------
# WAV writing with optional loop (smpl) chunk
# ----------------------------------------------------------------------------------------------
def write_wav(path: Path, x: np.ndarray, loop: tuple[int, int] | None = None, subtype: str = 'PCM_24') -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = as_channels(x).T if x.ndim == 2 else x
    peak = float(np.max(np.abs(data)))
    if peak > 1.0:
        raise ValueError(f'{path.name}: sample peak {peak:.3f} > 1.0 (would clip)')
    # TPDF dither to 24-bit is below audibility; write straight
    sf.write(str(path), data, SR, subtype=subtype)
    if loop is not None:
        add_smpl_chunk(path, loop[0], loop[1])
    return {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size}


def add_smpl_chunk(path: Path, start: int, end_inclusive: int) -> None:
    """Append a RIFF 'smpl' chunk with one forward loop (sample offsets, end inclusive)."""
    raw = bytearray(path.read_bytes())
    assert raw[:4] == b'RIFF' and raw[8:12] == b'WAVE'
    period_ns = int(round(1e9 / SR))
    header = struct.pack('<9I', 0, 0, period_ns, 60, 0, 0, 0, 1, 0)
    loop = struct.pack('<6I', 0, 0, start, end_inclusive, 0, 0)
    body = header + loop
    chunk = b'smpl' + struct.pack('<I', len(body)) + body
    raw += chunk
    raw[4:8] = struct.pack('<I', len(raw) - 8)
    path.write_bytes(bytes(raw))


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
