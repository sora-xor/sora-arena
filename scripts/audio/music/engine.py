"""Score-in-code music engine for SORA Arena original music (tier OWN).

Renders scores written in Python (scripts/audio/music/scores/*.py) to 48 kHz / 24-bit WAV, with:
  * a sample player over CC0 VCSL recordings (Dan Tranh zither as the koto voice, VCSL drums re-voiced as
    taiko, claves / woodblock / slit drum, gong, hand bells, bowed psaltery, wine glasses),
  * a shakuhachi voice built by additive resynthesis from a CC0 shakuhachi recording (Wikimedia Commons
    File:Shakuhachi-flute-440Hz.ogg): its measured harmonic profile plus its own extracted breath residual,
    driven by per-note pitch gestures (atari scoop, meri bend, yuri vibrato, muraiki breath accent),
  * original synthesis for the Credit House "cold" layer (poly-BLEP saws, FM glass, sub pulses),
  * seamless loops by steady-state rendering (the loop body is rendered twice and the second pass kept, so
    reverb and ringing notes from the end of the loop are present at its start), and MIDI export.

The third-party recordings are read from the gitignored Local/ThirdPartyRaw/audio tree; run
scripts/audio/fetch_cc0_audio.py first. Sample tuning is measured, not taken from file names
(scripts/audio/music/sample_tuning.json).
"""
from __future__ import annotations

import json
import math
import struct
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'synth'))
import dsp  # noqa: E402
from dsp import SR, db, n_of  # noqa: E402

RAW = dsp.ROOT / 'Local/ThirdPartyRaw/audio'
VCSL = RAW / 'vcsl-c1ea7bc'
TUNING_FILE = HERE / 'sample_tuning.json'


# ------------------------------------------------------------------------------------------------
# Sample loading and pitch analysis
# ------------------------------------------------------------------------------------------------
@lru_cache(maxsize=None)
def load(path: str) -> np.ndarray:
    """Load a sample as float64 [2, n] at 48 kHz."""
    x, sr = sf.read(path, always_2d=True)
    x = x.T.astype(np.float64)
    if x.shape[0] == 1:
        x = np.vstack([x, x])
    x = x[:2]
    if sr != SR:
        g = math.gcd(SR, sr)
        x = signal.resample_poly(x, SR // g, sr // g, axis=1)
    return x


def hps_f0(x: np.ndarray, lo: float, hi: float, start: float = 0.05, dur: float = 1.0) -> float:
    mono = x.mean(axis=0)
    seg = mono[n_of(start): n_of(start) + n_of(dur)]
    spec = np.abs(np.fft.rfft(seg * np.hanning(seg.size), 4 * seg.size))
    df = SR / (4 * seg.size)
    best, best_f = -1e9, lo
    for f in np.arange(lo, hi, 0.25):
        s = 0.0
        for k in range(1, 6):
            i = int(round(k * f / df))
            if i + 3 < spec.size:
                s += math.log(spec[max(0, i - 2): i + 3].max() + 1e-9)
        if s > best:
            best, best_f = s, f
    return float(best_f)


NOTE = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8,
        'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}


def midi_of(name: str) -> float:
    """'D4' -> 62, 'Bb3' -> 58."""
    i = 2 if len(name) > 2 and name[1] in '#b' else 1
    return 12 * (int(name[i:]) + 1) + NOTE[name[:i]]


def hz(m: float) -> float:
    return 440.0 * 2 ** ((m - 69) / 12)


def m_of_hz(f: float) -> float:
    return 69 + 12 * math.log2(f / 440.0)


def dan_tranh_files() -> dict:
    """{articulation: [(file, nominal_name, layer)]} for the Dan Tranh (VCSL names are one octave low)."""
    base = VCSL / 'Chordophones/Zithers/Dan Tranh'
    out = {'normal': [], 'vib': [], 'trem': []}
    for p in sorted((base / 'Normal').glob('*.wav')):
        name, layer = p.stem.split('_')[0], p.stem.split('_')[1]
        out['normal'].append((str(p), name, layer))
    for p in sorted((base / 'Vibrato').glob('*.wav')):
        name, layer = p.stem.split('_')[0], p.stem.split('_')[2]
        out['vib'].append((str(p), name, layer))
    for p in sorted((base / 'Tremolo').glob('*.wav')):
        out['trem'].append((str(p), p.stem.split('_')[0], 'mf'))
    return out


def build_tuning() -> dict:
    """Measure every pitched sample's real fundamental (the VCSL names are nominal and an octave low for
    the Dan Tranh; the beixiao / shakuhachi recordings are untuned). Cached in sample_tuning.json."""
    table = {}
    for art, rows in dan_tranh_files().items():
        for path, name, layer in rows:
            nominal = hz(midi_of(name.upper().replace('B2', 'B2')) + 12)
            x = load(path)
            table[str(Path(path).relative_to(dsp.ROOT))] = round(hps_f0(x, nominal * 0.9, nominal * 1.1), 2)
    for p in sorted((VCSL / 'Chordophones/Zithers/Psaltery, Bowed and Plucked').rglob('*.wav')):
        name = p.stem.split('_')[1]
        nominal = hz(midi_of(name))
        table[str(p.relative_to(dsp.ROOT))] = round(hps_f0(load(str(p)), nominal * 0.9, nominal * 1.1, 0.3), 2)
    shaku = RAW / 'wikimedia/Shakuhachi-flute-440Hz.ogg'
    table[str(shaku.relative_to(dsp.ROOT))] = round(hps_f0(load(str(shaku)), 400, 480, 1.0, 3.0), 2)
    TUNING_FILE.write_text(json.dumps({'note': 'Measured fundamentals (Hz) by harmonic-sum analysis; '
                                                'regenerate with engine.build_tuning()', 'f0': table},
                                      indent=1) + '\n')
    return table


@lru_cache(maxsize=None)
def tuning() -> dict:
    if not TUNING_FILE.exists():
        return build_tuning()
    return json.loads(TUNING_FILE.read_text())['f0']


# ------------------------------------------------------------------------------------------------
# Resampling playback
# ------------------------------------------------------------------------------------------------
def play(sample: np.ndarray, ratio, length: int | None = None, start: int = 0) -> np.ndarray:
    """Variable-rate playback with 4-point Hermite interpolation. ratio: scalar or per-output-sample array."""
    n_in = sample.shape[1] - start
    if np.isscalar(ratio):
        n_out = int(min(length or 1e12, (n_in - 3) / ratio))
        pos = np.arange(n_out) * ratio
    else:
        ratio = np.asarray(ratio, dtype=np.float64)
        pos = np.concatenate([[0.0], np.cumsum(ratio[:-1])])
        n_out = int(np.searchsorted(pos, n_in - 3))
        pos = pos[:n_out]
        if length:
            pos = pos[:length]
    pos = pos + start
    i = np.floor(pos).astype(np.int64)
    t = pos - i
    s = sample
    xm1 = s[:, np.maximum(i - 1, 0)]
    x0 = s[:, i]
    x1 = s[:, i + 1]
    x2 = s[:, i + 2]
    c1 = 0.5 * (x1 - xm1)
    c2 = xm1 - 2.5 * x0 + 2 * x1 - 0.5 * x2
    c3 = 0.5 * (x2 - xm1) + 1.5 * (x0 - x1)
    return ((c3 * t + c2) * t + c1) * t + x0


# ------------------------------------------------------------------------------------------------
# Instruments
# ------------------------------------------------------------------------------------------------
class Koto:
    """Koto voice from the VCSL Dan Tranh (16-string zither, finger picks). Supports oshide (press bends),
    vibrato and tremolo articulations; notes ring unless damped."""

    LAYERS = {'normal': ['mf', 'f', 'ff'], 'vib': ['mf', 'ff'], 'trem': ['mf']}

    def __init__(self):
        tun = tuning()
        self.samples = {}
        for art, rows in dan_tranh_files().items():
            for path, name, layer in rows:
                key = str(Path(path).relative_to(dsp.ROOT))
                self.samples.setdefault(art, []).append((path, layer.lower(), tun[key]))

    def render(self, pitch: float, vel: float, dur: float, r: np.random.Generator, art: str = 'normal',
               bend: list[tuple[float, float]] | None = None, damp: bool = False, ring: float = 4.0) -> np.ndarray:
        layers = self.LAYERS[art]
        li = min(len(layers) - 1, int(vel * len(layers)))
        layer = layers[li]
        target = hz(pitch)
        cands = [(abs(m_of_hz(f0) - pitch), p, f0) for p, lay, f0 in self.samples[art] if lay == layer]
        if not cands:
            cands = [(abs(m_of_hz(f0) - pitch), p, f0) for p, lay, f0 in self.samples[art]]
        _, path, f0 = min(cands)
        smp = load(path)
        base = target / f0
        length = n_of(dur + ring) if not damp else n_of(dur + 0.15)
        if bend:
            cents = dsp.env_points(length, [(t, c) for t, c in bend])
            ratio = base * 2 ** (cents / 1200)
            y = play(smp, ratio, length)
        else:
            y = play(smp, base, length)
        n = y.shape[1]
        if damp:
            e = np.ones(n)
            k = min(n, n_of(dur))
            e[k:] = np.exp(-np.arange(n - k) / (0.03 * SR))
            y = y * e
        else:
            y = dsp.fade(y, 0.0, min(0.3, n / SR / 3))
        # velocity within the layer
        return y * (0.55 + 0.45 * vel) * r.uniform(0.94, 1.0)


class Shakuhachi:
    """Additive resynthesis from the CC0 shakuhachi A4 recording (harmonic profile + breath residual)."""

    def __init__(self):
        path = RAW / 'wikimedia/Shakuhachi-flute-440Hz.ogg'
        x = load(str(path)).mean(axis=0)
        f0 = tuning()[str(path.relative_to(dsp.ROOT))]
        seg = x[n_of(1.0): n_of(7.5)]
        spec = np.abs(np.fft.rfft(seg * np.hanning(seg.size)))
        df = SR / seg.size
        h, ratios = [], []
        for k in range(1, 17):
            i = int(round(k * f0 / df))
            w = int(round(12 * k / df))  # partials of a real bore are slightly stretched: search +-12k Hz
            lo = max(0, i - w)
            j = lo + int(np.argmax(spec[lo: i + w + 1]))
            h.append(spec[j])
            ratios.append(j * df / f0)
        h = np.array(h)
        self.harm = h / h[0]
        self.ratios = np.array(ratios) / ratios[0]
        # breath residual: STFT, remove bins near harmonics, resynthesise
        f, t, Z = signal.stft(x, SR, nperseg=4096, noverlap=3072)
        mask = np.ones_like(f)
        for k in range(1, 40):
            mask[np.abs(f - k * f0) < 45] = 0.0
        _, res = signal.istft(Z * mask[:, None], SR, nperseg=4096, noverlap=3072)
        res = res[n_of(0.8): n_of(8.0)]
        self.breath = res / (np.std(res) + 1e-12)
        tone_rms = np.sqrt(np.mean(seg ** 2))
        res_rms = np.std(res) if res.size else 0
        self.breath_ratio = float(res_rms / (tone_rms + 1e-12))

    def render(self, pitch: float, vel: float, dur: float, r: np.random.Generator,
               bend: list[tuple[float, float]] | None = None, scoop: float = 60.0, vib_depth: float = 18.0,
               vib_rate: float = 5.0, vib_delay: float = 0.5, muraiki: float = 0.0, breathy: float = 1.0,
               release: float = 0.25, swell: float = 0.3, breathy_base: float = 3.0) -> np.ndarray:
        n = n_of(dur + release)
        t = np.arange(n) / SR
        # pitch gestures (cents)
        cents = -scoop * np.exp(-t / 0.07)  # atari: attack from slightly below
        if bend:
            cents = cents + dsp.env_points(n, bend)
        vib_env = np.clip((t - vib_delay) / 0.4, 0, 1) * (t < dur)
        cents = cents + vib_depth * vib_env * np.sin(2 * np.pi * vib_rate * t + r.uniform(0, 6.28))
        cents = cents + 4 * dsp.lowpass(r.standard_normal(n), 4)  # breath-driven drift
        f = hz(pitch) * 2 ** (cents / 1200)
        ph = dsp.phase_from_freq(f, r.uniform(0, 6.28))
        # amplitude: breath attack, swell towards the middle, release
        a = np.clip(t / 0.09, 0, 1) ** 1.5
        a *= 1 + swell * np.sin(np.pi * np.clip(t / max(dur, 0.1), 0, 1)) ** 2
        a *= np.where(t < dur, 1.0, np.exp(-(t - dur) / (release / 4)))
        a *= 1 + 0.06 * dsp.lowpass(r.standard_normal(n), 6)
        amp = a * vel
        y = np.zeros(n)
        for k, (hk, rk) in enumerate(zip(self.harm, self.ratios), start=1):
            if rk * hz(pitch) > SR * 0.45:
                break
            bright = (0.35 + 0.65 * vel) ** (0.6 * (k - 1))
            jitter = 1 + 0.08 * dsp.lowpass(r.standard_normal(n), 5)
            y += hk * bright * jitter * np.sin(rk * ph + (k - 1) * 0.7)
        y *= amp
        # breath residual (real recording), shaped by the note and by pitch
        off = r.integers(0, max(1, self.breath.size - n - 1))
        br = self.breath[off: off + n] if self.breath.size > n else np.resize(self.breath, n)
        br = dsp.bandpass(br, 300, 9000) * self.breath_ratio * breathy_base * breathy * (0.8 + 0.6 * (1 - vel))
        br_env = a * (0.8 + 1.2 * np.exp(-t / 0.12))
        y += br * br_env * vel
        if muraiki > 0:  # explosive breath accent
            burst = dsp.bandpass(r.standard_normal(n_of(0.25)), 400, 6000) * dsp.env_points(
                n_of(0.25), [(0, 0), (0.02, 1), (0.25, 0)]) * muraiki * 0.5 * vel
            y[: burst.size] += burst
        return np.vstack([y, y])


class Sampler:
    """Generic one-shot sample voice with velocity layers, round robin, re-pitch and optional envelope."""

    def __init__(self, layers: list[list[str]], pitch_ratio: float = 1.0, gain: float = 1.0,
                 decay: float | None = None, lp: float | None = None, hp: float | None = None):
        self.layers = [[str(VCSL / p) for p in lay] for lay in layers]
        self.ratio = pitch_ratio
        self.gain = gain
        self.decay = decay
        self.lp = lp
        self.hp = hp
        self.rr = 0

    def render(self, vel: float, r: np.random.Generator, ratio_mult: float = 1.0) -> np.ndarray:
        li = min(len(self.layers) - 1, int(vel * len(self.layers)))
        choices = self.layers[li]
        path = choices[int(r.integers(len(choices)))]  # round robin drawn from the piece's seeded RNG
        y = play(load(path), self.ratio * ratio_mult * 2 ** (r.normal(0, 8) / 1200))
        if self.decay:
            y = y * dsp.env_exp(y.shape[1], self.decay)
        if self.lp:
            y = dsp.lowpass(y, self.lp)
        if self.hp:
            y = dsp.highpass(y, self.hp)
        return y * self.gain * (0.35 + 0.65 * vel)


class Taiko:
    """Taiko stand-in built from VCSL concert bass drums, toms and claves (re-pitched and layered).
    Voices: 'odaiko' (big drum), 'nagado' (chu-daiko), 'shime' (high tension), 'kachi' (rim / bachi click)."""

    def __init__(self):
        bd2 = 'Membranophones/Struck Membranophones/Bass Drum 2/'
        bd1 = 'Membranophones/Struck Membranophones/Bass Drum 1/'
        t1 = 'Membranophones/Struck Membranophones/Tom 1/'
        t2 = 'Membranophones/Struck Membranophones/Tom 2/'
        cl = 'Idiophones/Struck Idiophones/Claves/'
        self.od = Sampler([[bd2 + 'bassdrum_hit_mp1.wav', bd2 + 'bassdrum_hit_mp2.wav'],
                           [bd2 + 'bassdrum_hit_mf1.wav', bd2 + 'bassdrum_hit_mf2.wav'],
                           [bd2 + 'bassdrum_hit_f.wav', bd2 + 'bassdrum_hit_ff.wav']], 1.19, 1.0, decay=1.6)
        self.od_skin = Sampler([[t2 + 'Mallet/TomL_HitM_v3_rr1_Mid.wav', t2 + 'Mallet/TomL_HitM_v3_rr2_Mid.wav'],
                                [t2 + 'Mallet/TomL_HitM_v4_rr1_Mid.wav', t2 + 'Mallet/TomL_HitM_v4_rr2_Mid.wav']],
                               0.62, 0.55, decay=0.7)
        self.na = Sampler([[bd1 + 'BDrumNew_hit_v3_rr1_Sum.wav', bd1 + 'BDrumNew_hit_v3_rr2_Sum.wav'],
                           [bd1 + 'BDrumNew_hit_v5_rr1_Sum.wav', bd1 + 'BDrumNew_hit_v5_rr2_Sum.wav'],
                           [bd1 + 'BDrumNew_hit_v7_rr1_Sum.wav', bd1 + 'BDrumNew_hit_v7_rr2_Sum.wav']], 1.5, 0.8,
                          decay=0.9)
        self.na_skin = Sampler([[t2 + 'Mallet/TomL_HitM_v2_rr1_Mid.wav', t2 + 'Mallet/TomL_HitM_v2_rr2_Mid.wav'],
                                [t2 + 'Mallet/TomL_HitM_v4_rr1_Mid.wav', t2 + 'Mallet/TomL_HitM_v4_rr2_Mid.wav']],
                               0.84, 0.7, decay=0.5)
        self.sh = Sampler([[t1 + 'Stick/TomH_HitS_v2_rr1_Mid.wav', t1 + 'Stick/TomH_HitS_v2_rr2_Mid.wav'],
                           [t1 + 'Stick/TomH_HitS_v3_rr1_Mid.wav', t1 + 'Stick/TomH_HitS_v3_rr2_Mid.wav'],
                           [t1 + 'Stick/TomH_HitS_v4_rr1_Mid.wav', t1 + 'Stick/TomH_HitS_v4_rr2_Mid.wav']], 1.42,
                          1.4, decay=0.16, hp=180)
        self.kachi = Sampler([[t1 + 'TomH_rimS_v2_rr1_Mid.wav', t1 + 'TomH_rimS_v2_rr2_Mid.wav'],
                              [t1 + 'TomH_rimS_v4_rr1_Mid.wav', t1 + 'TomH_rimS_v4_rr2_Mid.wav']], 1.0, 2.0,
                             decay=0.12)
        self.bachi = Sampler([[cl + 'Claves1_Hit_v1_rr1_Mid.wav', cl + 'Claves2_Hit_v1_rr1_Mid.wav'],
                              [cl + 'Claves1_Hit_v3_rr1_Mid.wav', cl + 'Claves2_Hit_v3_rr1_Mid.wav']], 0.7, 0.12,
                             decay=0.02, lp=2500)

    def render(self, voice: str, vel: float, r: np.random.Generator) -> np.ndarray:
        if voice == 'odaiko':
            parts = [self.od.render(vel, r), self.od_skin.render(vel, r) * 0.8, self.bachi.render(vel, r) * 0.6]
        elif voice == 'nagado':
            parts = [self.na.render(vel, r), self.na_skin.render(vel, r), self.bachi.render(vel, r)]
        elif voice == 'shime':
            parts = [self.sh.render(vel, r)]
        elif voice == 'kachi':
            parts = [self.kachi.render(vel, r)]
        else:
            raise ValueError(voice)
        n = max(p.shape[1] for p in parts)
        return dsp.mix(n, *[(p, 0) for p in parts])


class Perc:
    """Other struck instruments: hyoshigi (claves), mokugyo-like slit drum, woodblock, gong, rin (hand bell)."""

    def __init__(self):
        cl = 'Idiophones/Struck Idiophones/Claves/'
        sl = 'Idiophones/Struck Idiophones/Slit Drum/'
        wb = 'Idiophones/Struck Idiophones/Woodblock/'
        gg = 'Idiophones/Struck Idiophones/Gong 1/'
        hb = 'Idiophones/Struck Idiophones/Hand Bells, Nepalese/'
        self.v = {
            'hyoshigi': Sampler([[cl + 'Claves1_Hit_v2_rr1_Mid.wav', cl + 'Claves2_Hit_v2_rr1_Mid.wav'],
                                 [cl + 'Claves1_Hit_v3_rr1_Mid.wav', cl + 'Claves2_Hit_v3_rr1_Mid.wav']], 0.82, 0.8),
            'mokugyo': Sampler([[sl + 'LogDrumLo_MedM_v1_rr1_Sum.wav', sl + 'LogDrumHi_MedM_v1_rr1_Sum.wav'],
                                [sl + 'LogDrumLo_MedM_v3_rr1_Sum.wav', sl + 'LogDrumHi_MedM_v3_rr1_Sum.wav']], 1.0, 0.8),
            'woodblock': Sampler([[wb + 'wood_click_pp_rr1.wav', wb + 'wood_click_pp_rr2.wav'],
                                  [wb + 'wood_click_f_rr1.wav', wb + 'wood_click_f_rr2.wav']], 0.9, 0.6),
            'gong': Sampler([[gg + 'gong_p.wav'], [gg + 'gong_mf.wav'], [gg + 'gong_f.wav']], 1.0, 0.9, decay=9.0),
            'rin': Sampler([[hb + 'HB_1.wav', hb + 'HB_2.wav', hb + 'HB_3.wav']], 1.0, 0.7),
        }

    def render(self, voice: str, vel: float, r: np.random.Generator, ratio: float = 1.0) -> np.ndarray:
        return self.v[voice].render(vel, r, ratio)


class Psaltery:
    """Bowed psaltery long tones (eerie sustained metal strings) and plucks, from VCSL."""

    def __init__(self):
        tun = tuning()
        base = VCSL / 'Chordophones/Zithers/Psaltery, Bowed and Plucked'
        self.s = {}
        for art in ('LongBow', 'Pluck', 'Spiccato'):
            for p in sorted((base / art).glob('*.wav')):
                self.s.setdefault(art, []).append((str(p), tun[str(p.relative_to(dsp.ROOT))]))

    def render(self, pitch: float, vel: float, dur: float, r, art: str = 'LongBow') -> np.ndarray:
        _, path, f0 = min((abs(m_of_hz(f0) - pitch), p, f0) for p, f0 in self.s[art])
        y = play(load(path), hz(pitch) / f0, n_of(dur + 1.0))
        y = dsp.fade(y, 0.01, min(0.8, y.shape[1] / SR / 3))
        return y * vel


class Glass:
    """VCSL wine glasses (real friction-glass tones), re-pitched: the Credit House's cold sustained layer."""

    def __init__(self):
        base = VCSL / 'Idiophones/Friction Idiophones/Wine Glasses/Sustains/Slow'
        self.s = []
        for p in sorted(base.glob('*.wav')):
            name = p.stem.split('_')[1]
            self.s.append((str(p), hz(midi_of(name))))

    def render(self, pitch: float, vel: float, dur: float, r) -> np.ndarray:
        _, path, f0 = min((abs(m_of_hz(f0) - pitch), p, f0) for p, f0 in self.s)
        smp = load(path)
        start = n_of(1.0)
        y = play(smp, hz(pitch) / f0, n_of(dur + 1.5), start=start)
        y = dsp.fade(y, 0.4, min(1.5, y.shape[1] / SR / 3))
        return y * vel


def saw_blep(f: np.ndarray, phase0: float = 0.0) -> np.ndarray:
    """Poly-BLEP saw, vectorised."""
    dt = f / SR
    ph = (phase0 + np.cumsum(dt)) % 1.0
    y = 2 * ph - 1
    m = ph < dt
    t = ph[m] / dt[m]
    y[m] -= t + t - t * t - 1
    m2 = ph > 1 - dt
    t2 = (ph[m2] - 1) / dt[m2]
    y[m2] -= t2 * t2 + t2 + t2 + 1
    return y


class ColdSynth:
    """Original Credit House synth voices: detuned saw pad, FM glass bell, sub pulse, metal hit."""

    def pad(self, pitches: list[float], dur: float, r, cutoff=(300, 1400), vel: float = 0.6) -> np.ndarray:
        n = n_of(dur + 1.5)
        t = np.arange(n) / SR
        out = np.zeros((2, n))
        for p in pitches:
            for ch in range(2):
                v = np.zeros(n)
                for det in (-9, -3, 4, 10):
                    f = np.full(n, hz(p) * 2 ** ((det + r.normal(0, 1)) / 1200))
                    v += saw_blep(f, r.random())
                out[ch] += v / 4
        env = np.clip(t / 0.8, 0, 1) * np.where(t < dur, 1, np.exp(-(t - dur) / 0.4))
        cut = cutoff[0] + (cutoff[1] - cutoff[0]) * (0.5 - 0.5 * np.cos(2 * np.pi * t / max(dur, 1) * 0.5))
        out = np.vstack([dsp.tv_filter(out[c], 'lowpass', cut, 0.9, 256) for c in range(2)])
        return out * env * vel / max(1, len(pitches)) ** 0.5

    def bell(self, pitch: float, vel: float, r, t60: float = 1.8) -> np.ndarray:
        n = n_of(t60 * 1.2)
        f = np.full(n, hz(pitch))
        y = dsp.fm(f, 3.5, 2.2 * dsp.env_exp(n, t60 * 0.25)) * dsp.env_exp(n, t60)
        y += 0.35 * dsp.fm(f * 1.593, 2.0, 1.0 * dsp.env_exp(n, t60 * 0.2)) * dsp.env_exp(n, t60 * 0.6)
        return np.vstack([y, y]) * vel * 0.5

    def sub(self, pitch: float, dur: float, vel: float) -> np.ndarray:
        n = n_of(dur)
        t = np.arange(n) / SR
        y = np.sin(2 * np.pi * hz(pitch) * t) * np.clip(t / 0.005, 0, 1) * np.exp(-t / (dur * 0.5))
        y *= np.clip((dur - t) / 0.01, 0, 1)
        return np.vstack([y, y]) * vel

    def hit(self, vel: float, r) -> np.ndarray:
        n = n_of(1.6)
        freqs = np.array([180, 367, 522, 781, 1106, 1590, 2210, 3170]) * r.uniform(0.97, 1.03)
        y = dsp.modal(n, freqs, np.linspace(1.2, 0.2, freqs.size), np.linspace(1, 0.3, freqs.size), r)
        click = dsp.highpass(r.standard_normal(n_of(0.05)) * dsp.env_exp(n_of(0.05), 0.02), 800)
        y[: click.size] += 0.6 * click
        y = y / (np.max(np.abs(y)) + 1e-9)
        return np.vstack([y, y]) * vel * 0.6


# ------------------------------------------------------------------------------------------------
# Score, mixing, rendering
# ------------------------------------------------------------------------------------------------
@dataclass
class Ev:
    track: str
    beat: float
    fn: object  # callable(r) -> stereo array
    midi: tuple | None = None  # (channel, note, velocity 1-127, dur_beats) for export
    pan: float = 0.0


@dataclass
class Track:
    name: str
    gain_db: float = 0.0
    pan: float = 0.0
    reverb: float = 0.2
    stem: str = 'main'
    hp: float | None = None
    lp: float | None = None
    eq: list = field(default_factory=list)  # [(f0, q, gain_db)]
    width: float = 1.0
    clip_db: float = 0.0  # oversampled soft-clip drive on the track's loudest transients (drums)


@dataclass
class Piece:
    name: str
    title: str
    bpm: float
    beats_per_bar: int
    intro_bars: int
    loop_bars: int
    tracks: dict
    events: list  # intro events use beats < intro_bars*bpb; loop events use beats in the loop
    reverb_ir: np.ndarray
    target_lufs: float = -16.0
    description: str = ''
    programs: dict = field(default_factory=dict)  # track -> (channel, GM program 0-127) for MIDI export
    reference_stems: list | None = None  # stems summed for the loop mix / mastering (None = all stems)

    @property
    def beat_s(self) -> float:
        return 60.0 / self.bpm

    def samples_at(self, beat: float) -> int:
        return int(round(beat * self.beat_s * SR))


def place(piece: Piece, bufs: dict, ev: Ev, sig: np.ndarray, start: int, circular_n: int | None) -> None:
    if sig.ndim == 1:
        sig = np.vstack([sig, sig])
    if ev.pan:
        p = (ev.pan + 1) * np.pi / 4
        sig = np.vstack([sig[0] * np.cos(p) * 1.414, sig[1] * np.sin(p) * 1.414])
    buf = bufs[ev.track]
    if circular_n:
        dsp.place_circular(buf, sig, start % circular_n)
    else:
        end = min(buf.shape[1], start + sig.shape[1])
        if 0 <= start < end:
            buf[:, start:end] += sig[:, : end - start]


def process_track(tr: Track, x: np.ndarray) -> np.ndarray:
    y = x
    if tr.hp:
        y = dsp.highpass(y, tr.hp)
    if tr.lp:
        y = dsp.lowpass(y, tr.lp)
    for f0, q, g in tr.eq:
        y = dsp.peq(y, f0, q, g)
    if tr.pan:
        p = (tr.pan + 1) * np.pi / 4
        y = np.vstack([y[0] * np.cos(p) * 1.414, y[1] * np.sin(p) * 1.414])
    if tr.width != 1.0:
        mid = 0.5 * (y[0] + y[1])
        side = 0.5 * (y[0] - y[1]) * tr.width
        y = np.vstack([mid + side, mid - side])
    y = y * db(tr.gain_db)
    if tr.clip_db > 0:  # loudness-preserving: peaks come down by roughly clip_db, the body stays put
        c = dsp.soft_clip(y, tr.clip_db)
        y = c * (np.sqrt(np.mean(y ** 2)) / (np.sqrt(np.mean(c ** 2)) + 1e-12))
    return y


def glue_gain(x: np.ndarray, threshold_db: float = -18.0, ratio: float = 2.0, attack: float = 0.03,
              release: float = 0.25) -> np.ndarray:
    """Gain curve [1, n] of a gentle stereo-linked RMS bus compressor."""
    ms = np.maximum(dsp.lowpass(np.mean(x ** 2, axis=0), 1 / (2 * np.pi * attack), 1), 0)
    lvl_db = 10 * np.log10(ms + 1e-12)
    over = np.maximum(0, lvl_db - threshold_db)
    gr = dsp.lowpass(over * (1 - 1 / ratio), 1 / (2 * np.pi * release), 1)
    return (10 ** (-gr / 20))[None, :]


def render_piece(piece: Piece, seed: str, glue_db: float | None = -20.0) -> dict:
    """Render a piece. The loop is built circularly: every loop event is rendered once and placed modulo
    the loop length (ringing tails wrap into the loop start), and all mixing / reverb / bus processing
    runs through dsp.circ, so the loop file is exactly periodic. The intro is rendered linearly with its
    own tail (the engine starts the loop at `handoff` samples while the intro tail keeps playing).
    Returns {'intro', 'loop', 'stems', 'handoff', 'loop_n'}."""
    r = dsp.rng(seed)
    bpb = piece.beats_per_bar
    intro_beats = piece.intro_bars * bpb
    loop_n = piece.samples_at(piece.loop_bars * bpb)
    intro_n = piece.samples_at(intro_beats)
    tail_n = n_of(6.0)
    loop_bufs = {name: np.zeros((2, loop_n)) for name in piece.tracks}
    intro_bufs = {name: np.zeros((2, intro_n + tail_n)) for name in piece.tracks}
    has_intro = False
    for ev in piece.events:
        sig = ev.fn(r)
        if ev.beat < intro_beats:
            has_intro = True
            place(piece, intro_bufs, ev, sig, piece.samples_at(ev.beat), None)
        else:
            place(piece, loop_bufs, ev, sig, piece.samples_at(ev.beat - intro_beats), loop_n)

    def chain(tr):
        return lambda s: dsp.apply_reverb(process_track(tr, s), piece.reverb_ir, tr.reverb)[:, : s.shape[1]]

    loop_stems = {}
    for name, tr in piece.tracks.items():
        y = dsp.circ(chain(tr), loop_bufs[name])
        loop_stems[tr.stem] = loop_stems.get(tr.stem, 0) + y
    ref = piece.reference_stems or list(loop_stems)
    loop_mix = sum(loop_stems[k] for k in ref)
    intro_mix = None
    if has_intro:
        intro_mix = sum(chain(tr)(intro_bufs[name]) for name, tr in piece.tracks.items())
    if glue_db is not None:
        # bus glue measured on the full loop mix; the same gain curve scales every stem so they still sum
        # exactly to the mix (and the curve is computed circularly, so the loop stays periodic)
        g = dsp.circ(lambda s: glue_gain(s, glue_db), loop_mix)
        loop_mix = loop_mix * g
        loop_stems = {k: v * g for k, v in loop_stems.items()}
        if intro_mix is not None:
            intro_mix = intro_mix * glue_gain(intro_mix, glue_db)
    return {'intro': intro_mix, 'loop': loop_mix, 'stems': loop_stems, 'handoff': intro_n, 'loop_n': loop_n}


def master(parts: dict, target_lufs: float, tp: float = -1.0, max_limit_db: float = 4.0) -> dict:
    """One gain (plus one shared limiter gain curve) for the loop mix and all its stems, found by bisection
    so the limited loop mix meets the integrated target with true peak <= tp. The limiter curve is computed
    circularly, so the loop stays seamless, and applied to every stem, so stems still sum to the mix."""
    # DC / sub-audio removal (circular, LTI: applied identically to the mix and every stem)
    loop = dsp.remove_dc_circular(parts['loop'])
    parts = dict(parts, stems={k: dsp.remove_dc_circular(v) for k, v in parts['stems'].items()},
                 intro=dsp.remove_dc(parts['intro']) if parts['intro'] is not None else None)
    base = target_lufs - dsp.integrated_lufs(loop)

    def run(g):
        y = loop * db(g)
        if dsp.true_peak_db(y) <= tp - 0.05:
            return y, None
        curve = dsp.circ(lambda s: dsp.limiter_gain(s, tp - 0.25, release=0.15)[None, :], y)
        return y * curve, curve

    lo, hi = base, base + max_limit_db
    y, curve = run(lo)
    if dsp.integrated_lufs(y) < target_lufs - 0.05:
        for _ in range(12):
            mid = 0.5 * (lo + hi)
            y, curve = run(mid)
            if dsp.integrated_lufs(y) < target_lufs:
                lo = mid
            else:
                hi = mid
        g = 0.5 * (lo + hi)
        y, curve = run(g)
    else:
        g = lo
    out = {'gain_db': round(g, 2), 'loop': y, 'limiter_max_gr_db': round(-dsp.to_db(float(curve.min())), 2) if curve is not None else 0.0}
    out['stems'] = {k: v * db(g) * (curve if curve is not None else 1.0) for k, v in parts['stems'].items()}
    if parts['intro'] is not None:
        intro = parts['intro'] * db(g)
        if dsp.true_peak_db(intro) > tp:
            intro = dsp.limiter(intro, tp - 0.25, release=0.15)
        out['intro'] = intro
    return out


# ------------------------------------------------------------------------------------------------
# MIDI export (SMF type 1)
# ------------------------------------------------------------------------------------------------
def _vlq(v: int) -> bytes:
    out = [v & 0x7F]
    v >>= 7
    while v:
        out.append(0x80 | (v & 0x7F))
        v >>= 7
    return bytes(reversed(out))


def write_midi(piece: Piece, path: Path, ppq: int = 480) -> None:
    tracks = {}
    for e in piece.events:
        if e.midi:
            tracks.setdefault(e.track, []).append((e.beat, e.midi))
    chunks = []
    tempo = int(round(60_000_000 / piece.bpm))
    intro_beats = piece.intro_bars * piece.beats_per_bar
    loop_end = intro_beats + piece.loop_bars * piece.beats_per_bar
    meta = []
    meta.append((0, b'\xff\x03' + _vlq(len(piece.title.encode())) + piece.title.encode()))
    meta.append((0, b'\xff\x51\x03' + tempo.to_bytes(3, 'big')))
    meta.append((0, b'\xff\x58\x04' + bytes([piece.beats_per_bar, 2, 24, 8])))
    for beat, text in [(intro_beats, b'loopStart'), (loop_end, b'loopEnd')]:
        meta.append((int(beat * ppq), b'\xff\x06' + _vlq(len(text)) + text))
    chunks.append(meta)
    for name, evs in tracks.items():
        rows = [(0, b'\xff\x03' + _vlq(len(name.encode())) + name.encode())]
        if name in piece.programs:
            ch, prog = piece.programs[name]
            rows.append((0, bytes([0xC0 | ch, prog])))
        for beat, (ch, note, vel, dur) in evs:
            on = int(round(beat * ppq))
            off = int(round((beat + dur) * ppq))
            rows.append((on, bytes([0x90 | ch, int(note), max(1, min(127, int(vel)))])))
            rows.append((off, bytes([0x80 | ch, int(note), 0])))
        chunks.append(rows)
    data = b'MThd' + struct.pack('>IHHH', 6, 1, len(chunks), ppq)
    for rows in chunks:
        rows.sort(key=lambda x: (x[0], x[1][0] & 0xF0 == 0x90))
        body = b''
        last = 0
        for tick, msg in rows:
            body += _vlq(tick - last) + msg
            last = tick
        body += b'\x00\xff\x2f\x00'
        data += b'MTrk' + struct.pack('>I', len(body)) + body
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
