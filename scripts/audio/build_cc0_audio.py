#!/usr/bin/env python3
"""Admit the CC0 recordings the game's silent cues need (docs/audio.md section 1; plan sections 2.1 and 5).

The raw CC0 files stay in the gitignored Local/ThirdPartyRaw/audio tree with their ledger records
(scripts/assets/manifests/audio_*.json, storage local-private). This script cuts, levels and loops the takes
the cues play into Content/SourceArt/Audio/CC0/<Category>/ (48 kHz / 24-bit PCM WAV, LFS) and writes their
schema-2 PUB-CC0 ledger document, Content/SourceArt/Audio/CC0/manifest.json: one record per upstream asset
with every file made from it, the raw files and spans each came from (their SHA-256 checked against the raw
ledger before use) and its QA.

* One-shots are single takes found on the envelope (or, for a continuous texture such as a bow's creak,
  its loudest windows), resampled to 48 kHz, DC-free, trimmed, faded and levelled as the OWN renders are:
  transients peak-referenced ("P" after "limit" dB of soft-clip density), sustained sounds by their maximum
  momentary loudness ("M").
* Layered one-shots put a close take over a distant body: the explosions and the grenade launcher.
* Beds are a window of a field recording made into a seamless loop by an equal-power crossfade of the
  window's tail into its head, then levelled by gain alone (never limited, so the wrap stays exact) to
  -26 LUFS integrated at no more than -3 dBTP (docs/audio.md section 4.1).

Kenney files are ledgered "placeholder / layering only, never a hero sound": they voice only cues that would
otherwise be silent, and build_audio_data.py marks those cues placeholder-cc0 with the sound they still need.
The written files stay inside the plan's 0.5 GB for audio sources in the repository (validate_audio.py).

  python3 scripts/audio/build_cc0_audio.py --local-root <tree holding Local/ThirdPartyRaw/audio>
  python3 scripts/audio/build_cc0_audio.py --local-root <...> --check   # rebuild in memory, compare SHA-256
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'synth'))
sys.path.insert(0, str(HERE))
import dsp  # noqa: E402
from qa_audio import analyze  # noqa: E402

ROOT = dsp.ROOT
OUT = ROOT / 'Content/SourceArt/Audio/CC0'
MANIFEST = OUT / 'manifest.json'
RAW_LEDGERS = ROOT / 'scripts/assets/manifests'
RAW = 'Local/ThirdPartyRaw/audio/'
GENERATED = '/Game/Generated/Audio/CC0'
BUDGET_BYTES = 500_000_000  # free-asset plan section 5: audio sources used in the repository, <= 0.5 GB
BED_TP = -3.0
BED = {'I': -26.0, 'tp': BED_TP}

OGA = RAW + 'opengameart/'
FIREARMS = OGA + 'the-free-firearm-sound-library/extracted/Prepared SFX Library/Prepared SFX Library/'
BOWS = OGA + 'medieval-sound-effects-weapon-textures/extracted/'
KENNEY = RAW + 'kenney/impact-sounds/extracted/Audio/'
FIREWORKS = OGA + '25-cc0-bang-firework-sfx/extracted/25-CC0-bang-sfx/'
FANTOZZI = OGA + 'fantozzis-footsteps-grasssand-stone/extracted/Fantozzi-footsteps/Fantozzi-footsteps/flac/'
SPLASHES = OGA + '6-short-water-splashes/extracted/ezwa-water_splash/ezwa-water_splash/'
RAIN = OGA + 'rain-loopable/extracted/Rain OGG/'

# What each derivative changed, for its ledger record (CC0 asks for nothing; the record keeps it anyway).
CHANGES = ('Cut into single takes or loop windows, resampled to 48 kHz / 24-bit, DC removed, trimmed and '
           'faded, levelled to the docs/audio.md section 4 targets; beds looped by an equal-power crossfade; '
           'explosions and the grenade launcher layered over a distant body '
           '(scripts/audio/build_cc0_audio.py).')


def fail(message: str) -> None:
    sys.exit(f'build_cc0_audio: {message}')


class Raw:
    """The raw CC0 ledger and its files under a tree's Local/ (read-only, hash-checked)."""

    def __init__(self, local_root: Path):
        self.local_root = local_root
        self.rows: dict[str, tuple[dict, dict, str]] = {}
        for ledger in sorted(RAW_LEDGERS.glob('audio_*.json')):
            for record in json.loads(ledger.read_text(encoding='utf-8'))['assets']:
                for row in list(record.get('files', [])) + list(record.get('downloads', [])):
                    self.rows[row['file']] = (record, row, str(ledger.relative_to(ROOT)))
        self.cache: dict[str, tuple[np.ndarray, int]] = {}

    def record(self, rel: str) -> dict:
        return self.rows[rel][0]

    def read(self, rel: str) -> tuple[np.ndarray, int]:
        """[channels, frames] at the file's own rate, after checking its SHA-256 against the ledger."""
        if rel in self.cache:
            return self.cache[rel]
        if rel not in self.rows:
            fail(f'{rel} has no raw ledger record')
        record, row, _ = self.rows[rel]
        if record.get('tier') != 'PUB-CC0' or record.get('license') != 'CC0-1.0':
            fail(f'{rel} is not a PUB-CC0 / CC0-1.0 record')
        path = self.local_root / rel
        if not path.is_file():
            fail(f'{path} is missing (pass --local-root with the tree that holds Local/)')
        if hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            fail(f'{rel} differs from its ledger SHA-256')
        data, rate = sf.read(str(path), always_2d=True, dtype='float64')
        self.cache[rel] = (data.T.copy(), rate)
        return self.cache[rel]


def to48(x: np.ndarray, rate: int) -> np.ndarray:
    g = math.gcd(dsp.SR, rate)
    up, down = dsp.SR // g, rate // g
    return x if up == down == 1 else signal.resample_poly(x, up, down, axis=-1)


def envelope(x: np.ndarray, rate: int, window: float = 0.01) -> np.ndarray:
    power = np.max(np.abs(x), axis=0) ** 2
    n = max(1, int(window * rate))
    running = np.concatenate([np.zeros(n // 2 + 1), np.cumsum(power), np.full(n - n // 2, np.sum(power))])
    return np.sqrt(np.maximum(running[n:n + power.size] - running[:power.size], 0.0) / n)


def events(x: np.ndarray, rate: int, floor_db: float = -40.0, gap: float = 0.25) -> list[tuple[int, int, float]]:
    """(start, end, peak dB against the file's loudest) of each sound above floor_db, gaps under `gap` merged."""
    env = envelope(x, rate)
    top = env.max()
    on = np.r_[0, (env > top * dsp.db(floor_db)).astype(int), 0]
    edges = np.flatnonzero(np.diff(on))
    merged: list[list[int]] = []
    for start, end in zip(edges[::2], edges[1::2]):
        if merged and start - merged[-1][1] < gap * rate:
            merged[-1][1] = end
        else:
            merged.append([start, end])
    return [(s, e, 20 * math.log10(env[s:e].max() / top)) for s, e in merged]


class Build:
    """Collects every derivative: its audio at 48 kHz, cue, target and the raw spans it came from."""

    def __init__(self, raw: Raw):
        self.raw = raw
        self.items: list[dict] = []

    def add(self, name: str, category: str, cue: str, audio: np.ndarray, spans: list, target: dict, loop=False):
        self.items.append({'name': name, 'category': category, 'cue': cue, 'audio': audio, 'target': target,
                           'spans': spans, 'loop': loop})

    # --- sources ---------------------------------------------------------------------------------------
    def span(self, rel: str, start: int, end: int, rate: int) -> dict:
        return {'asset_id': self.raw.record(rel)['asset_id'], 'file': rel, 'sha256': self.raw.rows[rel][1]['sha256'],
                'start_s': round(start / rate, 4), 'end_s': round(end / rate, 4)}

    def whole(self, rel: str) -> tuple[np.ndarray, dict]:
        x, rate = self.raw.read(rel)
        return to48(x, rate), self.span(rel, 0, x.shape[1], rate)

    def takes(self, rel: str, min_peak_db: float, max_s: float, tail_s: float = 0.4, floor_db: float = -40.0,
              gap: float = 0.25, pre_s: float = 0.005) -> list[tuple[np.ndarray, dict]]:
        """Each take at least min_peak_db against the loudest, cut before the next sound starts."""
        x, rate = self.raw.read(rel)
        found = events(x, rate, floor_db, gap)
        out = []
        for index, (start, end, peak) in enumerate(found):
            if peak < min_peak_db:
                continue
            a = max(0, start - int(pre_s * rate))
            b = min(x.shape[1], end + int(tail_s * rate), a + int(max_s * rate))
            if index + 1 < len(found):
                b = min(b, found[index + 1][0] - int(0.02 * rate))
            out.append((to48(x[:, a:b], rate), self.span(rel, a, b, rate)))
        if not out:
            fail(f'no take in {rel}')
        return out

    def loudest_windows(self, rel: str, count: int, length_s: float) -> list[tuple[np.ndarray, dict]]:
        """The `count` loudest non-overlapping windows of a continuous texture, in time order."""
        x, rate = self.raw.read(rel)
        power = np.mean(x ** 2, axis=0)
        n = int(length_s * rate)
        hop = int(0.05 * rate)
        running = np.concatenate([[0.0], np.cumsum(power)])
        sums = (running[n:] - running[:-n])[::hop]
        chosen: list[int] = []
        for index in np.argsort(-sums, kind='stable'):
            start = int(index) * hop
            if all(abs(start - other) >= n for other in chosen):
                chosen.append(start)
            if len(chosen) == count:
                break
        return [(to48(x[:, s:s + n], rate), self.span(rel, s, s + n, rate)) for s in sorted(chosen)]

    def bed_window(self, rel: str, length_s: float, mode: str, margin_s: float = 1.0) -> tuple[np.ndarray, dict, int]:
        """A window of a long field recording, with margin_s of pre-roll for filters: 'even' is the window
        whose loudest 400 ms stands least above its median among those at least as busy as the file's median
        (no passing event dominates), 'loudest' the one with the highest median (the windiest)."""
        x, rate = self.raw.read(rel)
        block = int(0.4 * rate)
        blocks = 10 * np.log10(np.add.reduceat(np.mean(x ** 2, axis=0), np.arange(0, x.shape[1], block)) / block + 1e-20)
        width = int(math.ceil((length_s + margin_s) * rate / block))
        overall = float(np.median(blocks))
        best, best_score = None, None
        for index in range(0, len(blocks) - width):
            window = blocks[index:index + width]
            median = float(np.median(window))
            if mode == 'even':
                if median < overall:
                    continue
                score = float(window.max()) - median
            else:
                score = -median
            if best_score is None or score < best_score:
                best, best_score = index, score
        if best is None:
            fail(f'{rel} is shorter than a {length_s} s bed')
        start = best * block
        end = start + int((length_s + margin_s) * rate)
        return to48(x[:, start:end], rate), self.span(rel, start, end, rate), dsp.n_of(margin_s)


# --- processing -------------------------------------------------------------------------------------------
def trim(y: np.ndarray, head_db: float = -40.0, tail_db: float = -60.0) -> np.ndarray:
    env = np.max(np.abs(y), axis=0)
    above_head = np.flatnonzero(env > env.max() * dsp.db(head_db))
    above_tail = np.flatnonzero(env > env.max() * dsp.db(tail_db))
    start = max(0, above_head[0] - dsp.n_of(0.002))
    end = min(y.shape[1], above_tail[-1] + dsp.n_of(0.03))
    return y[:, start:end]


def level(y: np.ndarray, target: dict) -> np.ndarray:
    if 'I' in target:
        return dsp.normalize_integrated(y, target['I'], target.get('tp', -1.0), max_limit_db=0.0)
    if 'P' in target:
        y = dsp.peak_master(y, target['P'], target.get('limit', 3.0))
    else:
        y = dsp.normalize_momentary(y, target['M'], -1.0, max_limit_db=target.get('limit', 3.0))
    # The limiter's detector can miss an inter-sample peak by a fraction of a dB; one-shots end at -1 dBTP.
    peak = dsp.true_peak_db(y)
    return y * dsp.db(-1.0 - peak) if peak > -1.0 else y


def one_shot(y: np.ndarray, target: dict, fade_in: float = 0.0005, fade_out: float = 0.12) -> np.ndarray:
    y = trim(dsp.remove_dc(y))
    y = dsp.fade(y, fade_in, min(fade_out, y.shape[1] / dsp.SR / 3))
    return level(y, target)


def crossfade_loop(y: np.ndarray, loop_s: float, crossfade_s: float) -> np.ndarray:
    """One loop of loop_s: the window's next crossfade_s fade out over its head, equal power, so the last
    sample runs straight on into the first."""
    n, nx = dsp.n_of(loop_s), dsp.n_of(crossfade_s)
    if y.shape[1] < n + nx:
        fail(f'a {loop_s} s loop needs {loop_s + crossfade_s} s of source')
    out = y[:, :n].copy()
    t = np.linspace(0.0, np.pi / 2, nx)
    out[:, :nx] = y[:, :nx] * np.sin(t) + y[:, n:n + nx] * np.cos(t)
    return out


def bed(y: np.ndarray, target: dict) -> np.ndarray:
    return level(dsp.remove_dc_circular(y), dict(target, tp=BED_TP))


def at(y: np.ndarray, length: int) -> np.ndarray:
    out = np.zeros((y.shape[0], length))
    out[:, :min(length, y.shape[1])] = y[:, :length]
    return out


def stereo(y: np.ndarray) -> np.ndarray:
    return y if y.shape[0] == 2 else np.vstack([y[0], y[0]])


# --- the cues ---------------------------------------------------------------------------------------------
def weapons(b: Build) -> None:
    shots = []
    for rel in (FIREARMS + 'Model 1894/L_17P.wav', FIREARMS + 'Model 1894/L_23P.wav',
                FIREARMS + 'Marlin 336/I_17P.wav', FIREARMS + 'Marlin 336/I_22P.wav'):
        shots += b.takes(rel, -6.0, 1.4, tail_s=0.6)
    gun = {'P': -1.0, 'limit': 6.0}
    for index, (y, span) in enumerate(shots, 1):
        b.add(f'cc0_wpn_repeater_fire_{index:02d}', 'Weapons', 'weapon.fired.repeater', one_shot(y, gun, fade_out=0.3),
              [span], gun)

    # A tube's thump over a cannon's low body, well down.
    cannon, cannon_span = b.whole(OGA + 'cannon-fire/download/cannon_fire_0.ogg')
    body = dsp.fade(dsp.lowpass(trim(cannon), 700.0, 4)[:, :dsp.n_of(1.4)], 0.0, 0.5) * dsp.db(-9.0)
    for index in (1, 2, 3):
        shot, span = b.whole(FIREWORKS + f'shot_0{index}.ogg')
        shot = trim(shot)
        mix = at(shot, max(shot.shape[1], body.shape[1])) + at(stereo(body), max(shot.shape[1], body.shape[1]))
        b.add(f'cc0_wpn_grenade_launcher_fire_{index:02d}', 'Weapons', 'weapon.fired.grenade_launcher',
              one_shot(mix, gun, fade_out=0.4), [span, cannon_span], gun)
    for index in range(1, 6):
        y, span = b.whole(FIREWORKS + f'cannon_0{index}.ogg')
        b.add(f'cc0_wpn_micro_mortar_fire_{index:02d}', 'Weapons', 'weapon.fired.micro_mortar',
              one_shot(y[:, :dsp.n_of(1.8)], gun, fade_out=0.4), [span], gun)

    # The yumi: a draw's creak and the release. The tsurune is still to be recorded.
    draws = []
    for rel in (BOWS + 'medieval_sfx_textures_1_of_2/English Longbow Draw.wav',
                BOWS + 'medieval_sfx_textures_1_of_2/Scythian Recurve Draw.wav'):
        draws += b.loudest_windows(rel, 2, 1.5)
    for index, (y, span) in enumerate(draws, 1):
        y = dsp.fade(dsp.remove_dc(y), 0.06, 0.3)
        b.add(f'cc0_wpn_yumi_draw_{index:02d}', 'Weapons', 'weapon.yumi.draw', level(y, {'M': -22.0}), [span], {'M': -22.0})
    releases = b.takes(BOWS + 'medieval_sfx_textures_1_of_2/English Longbow Shoot.wav', -6.0, 1.2)
    releases += b.takes(BOWS + 'medieval_sfx_textures_1_of_2/Scythian Recurve Shoot.wav', -3.0, 1.0)
    for index, (y, span) in enumerate(releases, 1):
        b.add(f'cc0_wpn_yumi_release_{index:02d}', 'Weapons', 'weapon.fired.yumi',
              one_shot(y, {'P': -1.0, 'limit': 5.0}, fade_out=0.25), [span], {'P': -1.0, 'limit': 5.0})


def blades(b: Build) -> None:
    draws = b.takes(BOWS + 'medieval_sfx_textures_2_of_2/Katana Draw Fast.wav', -40.0, 0.9, tail_s=0.15, pre_s=0.01)
    for index, (y, span) in enumerate(draws, 1):
        b.add(f'cc0_mel_katana_draw_{index:02d}', 'Melee', 'melee.katana.draw', one_shot(y, {'M': -18.0}), [span],
              {'M': -18.0})
    sheathes = b.takes(BOWS + 'medieval_sfx_textures_1_of_2/Katana Sheath Fast.wav', -20.0, 0.9, tail_s=0.15, pre_s=0.01)
    for index, (y, span) in enumerate(sheathes, 1):
        b.add(f'cc0_mel_katana_sheathe_{index:02d}', 'Melee', 'melee.katana.sheathe', one_shot(y, {'M': -20.0}), [span],
              {'M': -20.0})
    # Placeholders (Kenney): a heavy punch for a blow landing, a heavy soft fall for a body.
    for index in range(5):
        y, span = b.whole(KENNEY + f'impactPunch_heavy_00{index}.ogg')
        b.add(f'cc0_mel_body_hit_{index + 1:02d}', 'Melee', 'melee.strike.hit_body',
              one_shot(y, {'P': -1.0, 'limit': 4.0}), [span], {'P': -1.0, 'limit': 4.0})
        y, span = b.whole(KENNEY + f'impactSoft_heavy_00{index}.ogg')
        b.add(f'cc0_imp_body_fall_{index + 1:02d}', 'Impacts', 'enemy.died',
              one_shot(y, {'P': -2.0, 'limit': 3.0}), [span], {'P': -2.0, 'limit': 3.0})


def explosions(b: Build) -> None:
    # A close bang over a distant, muffled blast: crack, then weight and tail.
    tail, tail_span = b.whole(OGA + 'muffled-distant-explosion/download/NenadSimic - Muffled Distant Explosion.wav')
    tail = trim(tail)
    length = dsp.n_of(3.2)
    for index in range(1, 7):
        bang, span = b.whole(FIREWORKS + f'bang_{index:02d}.ogg')
        bang = trim(bang)
        mix = at(stereo(bang), length)
        offset = dsp.n_of(0.015)
        mix[:, offset:] += at(stereo(tail), length - offset) * dsp.db(-8.0)
        mix = dsp.fade(mix, 0.0, 0.8)
        b.add(f'cc0_exp_detonation_{index:02d}', 'Explosions', 'explosion.detonated',
              one_shot(mix, {'P': -1.0, 'limit': 8.0}, fade_out=0.8), [span, tail_span], {'P': -1.0, 'limit': 8.0})


def footsteps(b: Build) -> None:
    sets = [
        ('earth', 'foot.earth', [FANTOZZI + f'Fantozzi-Sand{side}{n}.flac' for side in 'LR' for n in (1, 2, 3)], -22.0),
        ('stone', 'foot.stone', [FANTOZZI + f'Fantozzi-Stone{side}{n}.flac' for side in 'LR' for n in (1, 2, 3)], -22.0),
        ('water', 'foot.water', [SPLASHES + f'water_splash-0{n}.flac' for n in range(1, 7)], -20.0),
        # Placeholders (Kenney).
        ('grass', 'foot.grass', [KENNEY + f'footstep_grass_00{n}.ogg' for n in range(5)], -24.0),
        ('tatami', 'foot.tatami', [KENNEY + f'footstep_carpet_00{n}.ogg' for n in range(5)], -26.0),
    ]
    for surface, cue, sources, loudness in sets:
        for index, rel in enumerate(sources, 1):
            y, span = b.whole(rel)
            b.add(f'cc0_fol_step_{surface}_{index:02d}', 'Foley', cue, one_shot(y, {'M': loudness}, fade_out=0.08), [span],
                  {'M': loudness})


def beds(b: Build) -> None:
    # The estate by day: birds in a copse of trees before rain, rumble below 80 Hz removed.
    y, span, margin = b.bed_window(OGA + 'park-ambiences/download/park_ambience_birds.wav', 78.0, 'even')
    y = dsp.highpass(y, 80.0, 2)[:, margin:]
    b.add('cc0_amb_estate_day_loop', 'Ambience', 'amb.estate.day', bed(crossfade_loop(y, 75.0, 3.0), BED), [span], BED,
          loop=True)
    # Rain: two loopable recordings, one bed each.
    for index, (name, seconds) in enumerate((('3.ogg', 45.0), ('4.ogg', 37.5)), 1):
        y, span = b.whole(RAIN + name)
        b.add(f'cc0_amb_rain_loop_{index:02d}', 'Ambience', 'amb.rain', bed(crossfade_loop(y, seconds - 2.0, 2.0), BED),
              [span], BED, loop=True)
    # Far thunder: the long roll at 20 s of a rain recording, its rain hiss rolled off.
    x, rate = b.raw.read(OGA + 'rain-long-thunder/download/rain-thunder.ogg')
    a, e = int(20.5 * rate), int(36.5 * rate)
    y = dsp.lowpass(to48(x[:, a:e], rate), 1800.0, 4)
    y = dsp.fade(dsp.remove_dc(y), 0.25, 2.5)
    b.add('cc0_amb_thunder_01', 'Ambience', 'amb.thunder', level(y, {'M': -14.0}),
          [b.span(OGA + 'rain-long-thunder/download/rain-thunder.ogg', a, e, rate)], {'M': -14.0})
    # Fire: a fireplace loop.
    y, span = b.whole(OGA + 'fireplace-sound-loop/download/fire.wav')
    b.add('cc0_amb_fire_loop', 'Ambience', 'amb.fire', bed(crossfade_loop(y, 27.0, 2.0), BED), [span], BED, loop=True)
    # Typhoon: the park's windiest stretch with weight added, under heavy rain.
    wind, wind_span, margin = b.bed_window(OGA + 'park-ambiences/download/park_ambience_wind.wav', 45.0, 'loudest')
    wind = dsp.peq(wind, 120.0, 0.7, 3.0)[:, margin:]
    rain, rain_span = b.whole(RAIN + '3.ogg')
    storm = crossfade_loop(wind, 43.0, 2.0) + crossfade_loop(rain, 43.0, 2.0) * dsp.db(-3.0)
    storm_target = {'I': -23.0, 'tp': BED_TP}
    b.add('cc0_amb_typhoon_loop', 'Ambience', 'amb.typhoon', bed(storm, storm_target), [wind_span, rain_span], storm_target,
          loop=True)
    # The festival: a fireworks bed with single bursts scattered over it (seeded, wrapping round the loop).
    base, base_span = b.whole(FIREWORKS + 'fw_loop.ogg')
    loop = crossfade_loop(np.concatenate([base] * 4, axis=1), 56.0, 2.0)
    r = dsp.rng('cc0_amb_festival_loop')
    spans = [base_span]
    bursts = []
    for index in range(1, 7):
        y, span = b.whole(FIREWORKS + f'fw_0{index}.ogg')
        bursts.append(stereo(trim(y)))
        spans.append(span)
    for k in range(12):
        dsp.place_circular(loop, bursts[k % 6] * dsp.db(float(r.uniform(-10.0, -2.0))), int(r.integers(0, loop.shape[1])))
    b.add('cc0_amb_festival_loop', 'Ambience', 'amb.festival', bed(loop, BED), spans, BED, loop=True)


def workshop(b: Build) -> None:
    """Ch05 aizuchi's distinct cue and response; never a substitute for Okinu's voice."""
    prefix = RAW + 'vcsl-c1ea7bc/Idiophones/Struck Idiophones/Anvil/'
    for name, source, cue, peak in (
        ('cc0_workshop_small_hammer', 'Anvil_Hit1_v1_rr1_Mid.wav', 'workshop.hammer.cue', -9.0),
        ('cc0_workshop_sledge', 'Anvil_Hit2_v3_rr1_Mid.wav', 'workshop.hammer.hit', -5.0),
    ):
        y, span = b.whole(prefix + source)
        # Keep the recorded attack, with a bounded tail inside the 600 ms
        # cadence; no pitch randomisation that could move the attack.
        y = trim(dsp.remove_dc(y))[:, :dsp.n_of(.42)]
        target = {'P': peak, 'limit': 0.0}
        b.add(name, 'Workshop', cue, one_shot(y, target, fade_out=.06), [span], target)


def render(raw: Raw, workshop_only: bool = False) -> Build:
    b = Build(raw)
    for part in ((workshop,) if workshop_only else (weapons, blades, explosions, footsteps, beds, workshop)):
        part(b)
    names = [item['name'] for item in b.items]
    if len(names) != len(set(names)):
        fail('two derivatives share a name')
    return b


def write(b: Build, out: Path) -> list[dict]:
    rows = []
    for item in b.items:
        path = out / item['category'] / f"{item['name']}.wav"
        y = item['audio']
        meta = dsp.write_wav(path, y, loop=(0, y.shape[1] - 1) if item['loop'] else None)
        qa = analyze(path, force_loop=item['loop'])
        if qa['fail']:
            fail(f"{item['name']} fails QA: {qa['fail']}")
        rows.append({'item': item, 'path': path, 'bytes': meta['bytes'], 'sha256': meta['sha256'],
                     'qa': {k: v for k, v in qa.items() if k != 'file'}})
    return rows


def manifest(raw: Raw, rows: list[dict]) -> dict:
    copied = ('tier', 'license', 'license_url', 'legal_code_url', 'commercial_use', 'redistribution', 'derivatives',
              'platform_restriction', 'ai_terms', 'agent_handling', 'attribution_text', 'access', 'acquired_at_utc',
              'acquired_by', 'asset_id', 'name', 'origin_url', 'mirror_url', 'authors', 'license_evidence', 'upstream',
              'placeholder_only')
    records: dict[str, dict] = {}
    for row in rows:
        item = row['item']
        rel = f"{OUT.relative_to(ROOT)}/{item['category']}/{item['name']}.wav"
        package = f"{GENERATED}/{item['category']}/{item['name']}"
        for position, span in enumerate(item['spans']):
            raw_record = raw.record(span['file'])
            record = records.setdefault(raw_record['asset_id'], {
                **{key: raw_record[key] for key in copied if key in raw_record},
                'role': raw_record.get('role'),
                'raw_ledger': raw.rows[span['file']][2],
                'changes': CHANGES,
                'storage': 'repo-lfs',
                'committed': True,
                'fallback': None,
                'used_by': [],
                'layered_into': [],
                'files': [],
            })
            if position == 0:
                record['files'].append({
                    'file': rel, 'bytes': row['bytes'], 'sha256': row['sha256'], 'cue': item['cue'],
                    'loop': item['loop'], 'target': item['target'], 'derived_from': item['spans'], 'qa': row['qa'],
                })
            else:
                record['layered_into'].append(rel)
            object_path = f"{package}.{item['name']}"
            if object_path not in record['used_by']:
                record['used_by'].append(object_path)
    total = sum(row['bytes'] for row in rows)
    if total > BUDGET_BYTES:
        fail(f'{total} bytes of CC0 audio exceed the {BUDGET_BYTES} byte budget')
    return {
        'schema_version': 2,
        'kind': 'asset-ledger',
        'ledger_id': 'audio-cc0-derivatives',
        'source': 'SORA Arena CC0 audio derivatives (Content/SourceArt/Audio/CC0)',
        'tier': 'PUB-CC0',
        'purpose': 'The CC0 recordings the runtime cues play, cut and levelled from the raw ledger '
                   '(scripts/assets/manifests/audio_*.json); docs/audio.md sections 1 and 2.1.',
        'generator': 'scripts/audio/build_cc0_audio.py',
        'regenerate': 'python3 scripts/audio/build_cc0_audio.py --local-root <tree holding Local/ThirdPartyRaw/audio>',
        'format': '48 kHz / 24-bit PCM WAV, mono or stereo as recorded; beds carry a RIFF smpl loop over the whole file',
        'loudness_policy': 'docs/audio.md section 4: transients peak-referenced ("P" after "limit" dB of soft-clip '
                           'density), sustained one-shots by maximum momentary loudness ("M"), beds by integrated '
                           'loudness ("I", gain only, <= -3 dBTP)',
        'budget_bytes': BUDGET_BYTES,
        'total_bytes': total,
        'records': sorted(records.values(), key=lambda record: record['asset_id']),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n', 1)[0])
    parser.add_argument('--local-root', type=Path, default=ROOT,
                        help='the tree whose Local/ThirdPartyRaw/audio holds the raw CC0 files (default: this tree)')
    parser.add_argument('--check', action='store_true', help='rebuild in a temporary folder and compare with the manifest')
    parser.add_argument('--workshop-only', action='store_true',
                        help='build/check only the two pinned workshop takes; preserve all other ledger rows')
    args = parser.parse_args()
    raw = Raw(args.local_root.resolve())
    built = render(raw, args.workshop_only)
    if args.check:
        recorded = {row['file']: row['sha256'] for record in json.loads(MANIFEST.read_text(encoding='utf-8'))['records']
                    for row in record['files'] if not args.workshop_only or '/Workshop/' in row['file']}
        with tempfile.TemporaryDirectory(prefix='sora-cc0-audio-') as temp:
            rows = write(built, Path(temp))
            fresh = {f"{OUT.relative_to(ROOT)}/{row['item']['category']}/{row['item']['name']}.wav": row['sha256']
                     for row in rows}
        if fresh != recorded:
            differ = sorted(set(fresh.items()) ^ set(recorded.items()))
            fail(f'the committed CC0 audio differs from a fresh build: {differ[:4]}')
        print(f'CC0_AUDIO_CURRENT: {len(fresh)} files')
        return 0
    rows = write(built, OUT)
    fresh = manifest(raw, rows)
    if args.workshop_only:
        existing = json.loads(MANIFEST.read_text(encoding='utf-8'))
        # Replacing this bounded record never refreshes unrelated hashes.
        replaced = {record['asset_id'] for record in fresh['records']}
        for record in existing['records']:
            if record['asset_id'] in replaced and any('/Workshop/' not in row['file'] for row in record['files']):
                fail('workshop-only refuses to replace an anvil record with non-workshop derivatives')
        existing['records'] = sorted([record for record in existing['records'] if record['asset_id'] not in replaced]
                                     + fresh['records'], key=lambda record: record['asset_id'])
        existing['total_bytes'] = sum(row['bytes'] for record in existing['records'] for row in record['files'])
        if existing['total_bytes'] > BUDGET_BYTES:
            fail('workshop derivatives would exceed the audio budget')
        fresh = existing
    dsp.save_json(MANIFEST, fresh)
    loops = sum(1 for row in rows if row['item']['loop'])
    total = sum(row['bytes'] for row in rows)
    for row in rows:
        qa = row['qa']
        print(f"ok   {row['item']['cue']:30s} {row['path'].name:40s} {qa['channels']}ch {qa['seconds']:6.2f}s "
              f"M {qa.get('momentary_max_lufs')} I {qa.get('integrated_lufs')} TP {qa.get('true_peak_dbtp')}")
    print(f'CC0_AUDIO_BUILT: {len(rows)} files ({loops} loops), {total} bytes of the {BUDGET_BYTES} byte budget')
    return 0


if __name__ == '__main__':
    sys.exit(main())
