"""Helpers shared by the score modules: shared instrument instances and event constructors."""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import engine  # noqa: E402
from engine import Ev, midi_of  # noqa: E402

GM_DRUM = {'odaiko': 35, 'nagado': 41, 'shime': 38, 'kachi': 37, 'hyoshigi': 75, 'mokugyo': 76, 'woodblock': 77,
           'gong': 52, 'rin': 81, 'metal_hit': 55}


@lru_cache(maxsize=None)
def inst(name: str):
    return {'koto': engine.Koto, 'shaku': engine.Shakuhachi, 'taiko': engine.Taiko, 'perc': engine.Perc,
            'psaltery': engine.Psaltery, 'glass': engine.Glass, 'cold': engine.ColdSynth}[name]()


class Score:
    """Collects events in beats; `human` adds deterministic timing / velocity variation."""

    def __init__(self, bpm: float, seed: int):
        self.bpm = bpm
        self.beat_s = 60.0 / bpm
        self.events: list[Ev] = []
        self.r = np.random.default_rng(seed)
        self.loop_start = 0.0  # beats; events at/after it belong to the loop and are never jittered before it

    def when(self, beat: float, ms: float) -> float:
        floor = self.loop_start if beat >= self.loop_start else 0.0
        return max(floor, beat + self.jitter(ms))

    def jitter(self, ms: float) -> float:
        return self.r.normal(0, ms / 1000) / self.beat_s

    def vel(self, v: float, spread: float = 0.05) -> float:
        return float(np.clip(v + self.r.normal(0, spread), 0.05, 1.0))

    # --- melodic -------------------------------------------------------------------------------
    def koto(self, beat, note, dur, v=0.6, art='normal', bend=None, damp=False, ring=4.0, track='koto', pan=0.0,
             human=True):
        m = midi_of(note) if isinstance(note, str) else note
        vv = self.vel(v) if human else v
        b = self.when(beat, 7) if human else beat
        d = dur * self.beat_s
        bend_s = [(t * self.beat_s, c) for t, c in bend] if bend else None
        self.events.append(Ev(track, b, lambda r, m=m, vv=vv, d=d, art=art, bend_s=bend_s, damp=damp, ring=ring:
                              inst('koto').render(m, vv, d, r, art, bend_s, damp, ring),
                              (0, int(m), int(vv * 127), dur), pan))

    def shaku(self, beat, note, dur, v=0.7, bend=None, track='shaku', **kw):
        m = midi_of(note) if isinstance(note, str) else note
        d = dur * self.beat_s
        bend_s = [(t * self.beat_s, c) for t, c in bend] if bend else None
        self.events.append(Ev(track, beat, lambda r, m=m, v=v, d=d, bend_s=bend_s, kw=kw:
                              inst('shaku').render(m, v, d, r, bend_s, **kw), (1, int(m), int(v * 127), dur)))

    def psaltery(self, beat, note, dur, v=0.5, art='LongBow', track='psaltery', pan=0.0):
        m = midi_of(note) if isinstance(note, str) else note
        d = dur * self.beat_s
        self.events.append(Ev(track, beat, lambda r, m=m, v=v, d=d, art=art: inst('psaltery').render(m, v, d, r, art),
                              (2, int(m), int(v * 127), dur), pan))

    def glass(self, beat, note, dur, v=0.5, track='glass', pan=0.0):
        m = midi_of(note) if isinstance(note, str) else note
        d = dur * self.beat_s
        self.events.append(Ev(track, beat, lambda r, m=m, v=v, d=d: inst('glass').render(m, v, d, r),
                              (3, int(m), int(v * 127), dur), pan))

    # --- percussion ----------------------------------------------------------------------------
    def taiko(self, beat, voice, v=0.7, track='taiko', pan=0.0, human=True):
        vv = self.vel(v, 0.06) if human else v
        b = self.when(beat, 6) if human else beat
        self.events.append(Ev(track, b, lambda r, voice=voice, vv=vv: inst('taiko').render(voice, vv, r),
                              (9, GM_DRUM[voice], int(vv * 127), 0.25), pan))

    def perc(self, beat, voice, v=0.6, track='perc', pan=0.0, ratio=1.0):
        vv = self.vel(v, 0.04)
        self.events.append(Ev(track, beat, lambda r, voice=voice, vv=vv, ratio=ratio: inst('perc').render(voice, vv, r, ratio),
                              (9, GM_DRUM[voice], int(vv * 127), 0.25), pan))

    # --- cold synth ----------------------------------------------------------------------------
    def pad(self, beat, notes, dur, v=0.6, cutoff=(300, 1400), track='pad'):
        ms = [midi_of(n) if isinstance(n, str) else n for n in notes]
        d = dur * self.beat_s
        self.events.append(Ev(track, beat, lambda r, ms=ms, d=d, v=v, cutoff=cutoff: inst('cold').pad(ms, d, r, cutoff, v),
                              (4, int(ms[0]), int(v * 127), dur)))

    def bell(self, beat, note, v=0.5, t60=1.6, track='bell', pan=0.0):
        m = midi_of(note) if isinstance(note, str) else note
        self.events.append(Ev(track, beat, lambda r, m=m, v=v, t60=t60: inst('cold').bell(m, v, r, t60),
                              (5, int(m), int(v * 127), 0.5), pan))

    def sub(self, beat, note, dur, v=0.7, track='sub'):
        m = midi_of(note) if isinstance(note, str) else note
        d = dur * self.beat_s
        self.events.append(Ev(track, beat, lambda r, m=m, d=d, v=v: inst('cold').sub(m, d, v),
                              (6, int(m), int(v * 127), dur)))

    def metal(self, beat, v=0.6, track='metal', pan=0.0):
        self.events.append(Ev(track, beat, lambda r, v=v: inst('cold').hit(v, r), (9, GM_DRUM['metal_hit'], int(v * 127), 0.5), pan))
