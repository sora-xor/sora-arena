"""「猫柳生の風」 Wind over Nyaagyū — title / menu theme (original composition, tier OWN).

Form: 4-bar free intro (solo shakuhachi over soft koto and gong) + 16-bar loop at 66 BPM in 4/4:
  A  (bars 1-4)   koto ostinato, shakuhachi states the main theme
  A' (bars 5-8)   theme a fourth higher, nagado-daiko and kachi enter
  B  (bars 9-12)  climax: odaiko, shime ostinato, shakuhachi in the kan (upper) register
  A''(bars 13-16) settles; the last bar thins to koto alone so the loop wraps quietly
Mode: miyako-bushi / hirajoshi on D (D Eb G A Bb); koto tuned hirajoshi from D3.
Harmonic cycle per 4 bars: D - Eb(over G) - G - A (the A bar carries the Bb-A tension that resolves home).
The main theme is the League / main theme sketch for credits_main and ch03_oath (story bible, L5 states).
"""
from __future__ import annotations

from common import Score, midi_of

BPM = 66
BPB = 4
INTRO_BARS = 4
LOOP_BARS = 16

# koto ostinato cells (8 eighth notes per bar)
CELLS = {
    'D': ['D3', 'A3', 'D4', 'Eb4', 'A4', 'D4', 'A3', 'Eb4'],
    'Eb': ['G3', 'Bb3', 'Eb4', 'G4', 'Bb4', 'G4', 'Eb4', 'Bb3'],
    'G': ['G3', 'D4', 'G4', 'A4', 'Bb4', 'A4', 'G4', 'D4'],
    'A': ['A3', 'Eb4', 'A4', 'Bb4', 'D5', 'Bb4', 'A4', 'Eb4'],
}
PROGRESSION = ['D', 'Eb', 'G', 'A']

# shakuhachi theme, loop-relative beats: (beat, note, dur, velocity, options)
THEME = [
    # A
    (0.0, 'D4', 1.5, 0.62, {'muraiki': 0.4}), (1.5, 'Eb4', 0.5, 0.55, {}), (2.0, 'G4', 2.0, 0.66, {}),
    (4.0, 'A4', 1.5, 0.7, {}), (5.5, 'G4', 0.5, 0.55, {}), (6.0, 'Eb4', 2.0, 0.6, {'bend': [(0, 0), (1.3, 0), (1.9, -100)]}),
    (8.0, 'D4', 3.0, 0.62, {}), (11.5, 'G4', 0.5, 0.55, {}), (12.0, 'A4', 3.6, 0.7, {'vib_depth': 26}),
    # A'
    (16.0, 'G4', 1.5, 0.66, {'muraiki': 0.4}), (17.5, 'A4', 0.5, 0.58, {}),
    (18.0, 'Bb4', 2.0, 0.72, {'bend': [(0, -100), (0.25, 0)]}), (20.0, 'D5', 1.5, 0.76, {}),
    (21.5, 'Bb4', 0.5, 0.6, {}), (22.0, 'A4', 2.0, 0.68, {}), (24.0, 'G4', 3.0, 0.66, {}),
    (27.0, 'Eb4', 0.5, 0.55, {}), (27.5, 'G4', 0.5, 0.58, {}), (28.0, 'D4', 3.6, 0.64, {'vib_depth': 24}),
    # B (kan register)
    (32.0, 'D5', 2.0, 0.84, {'muraiki': 0.8}), (34.0, 'Eb5', 1.0, 0.8, {}), (35.0, 'D5', 1.0, 0.78, {}),
    (36.0, 'Bb4', 2.0, 0.76, {}), (38.0, 'A4', 1.0, 0.72, {}), (39.0, 'Bb4', 1.0, 0.74, {}),
    (40.0, 'D5', 3.0, 0.84, {'vib_depth': 28}), (43.0, 'Eb5', 1.0, 0.8, {'bend': [(0, -100), (0.3, 0)]}),
    (44.0, 'G5', 2.0, 0.9, {'muraiki': 0.6, 'vib_depth': 30}), (46.0, 'Eb5', 1.0, 0.8, {}), (47.0, 'D5', 1.0, 0.78, {}),
    # A''
    (48.0, 'A4', 3.0, 0.66, {}), (51.0, 'G4', 1.0, 0.6, {}),
    (52.0, 'Eb4', 2.0, 0.6, {'bend': [(0, 0), (1.4, 0), (1.9, -100)]}),
    (54.0, 'D4', 5.0, 0.58, {'vib_depth': 22, 'swell': 0.15}),
]


def build():
    import engine
    s = Score(BPM, seed=1623)
    intro_beats = INTRO_BARS * BPB
    s.loop_start = intro_beats

    # ---------------- intro (free, honkyoku-like) ----------------
    s.perc(0.0, 'gong', 0.35, ratio=0.9)
    s.koto(0.0, 'D3', 6.0, 0.45, ring=6.0)
    s.koto(0.02, 'A3', 6.0, 0.35, ring=6.0)
    s.shaku(0.5, 'D4', 4.0, 0.6, muraiki=0.7, vib_delay=1.2, vib_depth=22)
    s.shaku(5.0, 'Eb4', 1.0, 0.55, bend=[(0, -100), (0.35, 0)])
    s.shaku(6.0, 'G4', 2.5, 0.64, vib_delay=0.8)
    s.koto(8.0, 'G3', 4.0, 0.4, ring=5.0)
    s.koto(8.03, 'D4', 4.0, 0.34, ring=5.0)
    s.shaku(9.0, 'A4', 1.0, 0.62)
    s.shaku(10.0, 'Bb4', 2.2, 0.7, bend=[(0, 0), (1.5, 0), (2.1, -100)], vib_delay=0.6)
    s.perc(11.0, 'rin', 0.4)
    s.shaku(12.6, 'A4', 2.6, 0.58, vib_depth=20, swell=0.1)
    for i, n in enumerate(['D4', 'G4', 'A4', 'D5']):  # sukui-style rising arpeggio into the loop
        s.koto(14.0 + 0.5 * i, n, 1.0, 0.45 + 0.05 * i)

    # ---------------- loop ----------------
    L = intro_beats
    for bar in range(LOOP_BARS):
        chord = PROGRESSION[bar % 4]
        phrase = bar // 4
        base = L + bar * BPB
        cell = CELLS[chord]
        if phrase in (0, 1, 2) or bar < 14:
            for i, note in enumerate(cell):
                accent = 0.66 if i in (0, 4) else 0.5
                if phrase == 2:
                    accent += 0.08
                art = 'normal'
                bend = None
                if chord == 'A' and i == 3 and phrase in (1, 2):  # oshide: press Bb up a semitone and release
                    bend = [(0, 0), (0.25, 100), (0.45, 0)]
                spread = max(-0.6, min(0.5, -0.6 + (midi_of(note) - 50) / 26))  # low strings left, high right
                s.koto(base + 0.5 * i, note, 0.5, accent, art=art, bend=bend, ring=2.5, pan=spread)
            if phrase == 2:  # tremolo colour on the climax downbeats
                s.koto(base, {'D': 'D5', 'Eb': 'Eb5', 'G': 'G4', 'A': 'A4'}[chord], 2.0, 0.45, art='trem', pan=0.35,
                       ring=1.5)
        else:  # bars 14-15: quarter notes, then a single low D to let the loop breathe
            if bar == 14:
                for i, note in enumerate(cell[::2]):
                    s.koto(base + i, note, 1.0, 0.5, ring=3.0, pan=-0.2)
            else:
                s.koto(base, 'D3', 4.0, 0.46, ring=4.0, pan=-0.2)
                s.koto(base + 0.02, 'A3', 4.0, 0.38, ring=4.0, pan=-0.2)
                s.koto(base + 2.5, 'D4', 1.5, 0.36, ring=3.0, pan=-0.2)

    for beat, note, dur, v, opt in THEME:
        s.shaku(L + beat, note, dur, v, **opt)

    # percussion
    s.perc(L + 0.0, 'rin', 0.4)
    s.taiko(L + 0.0, 'odaiko', 0.35)
    for bar in range(4, 8):  # A': nagado on 1 and 3, kachi on the 'and' of 4
        base = L + bar * BPB
        s.taiko(base, 'nagado', 0.5)
        s.taiko(base + 2, 'nagado', 0.42)
        s.taiko(base + 3.5, 'kachi', 0.4)
    s.perc(L + 30.0, 'hyoshigi', 0.7)
    s.perc(L + 31.0, 'hyoshigi', 0.8)
    s.perc(L + 32.0, 'gong', 0.5)
    for bar in range(8, 12):  # B: full ensemble
        base = L + bar * BPB
        s.taiko(base, 'odaiko', 0.85)
        s.taiko(base + 1.5, 'nagado', 0.6)
        s.taiko(base + 2.0, 'nagado', 0.72)
        s.taiko(base + 2.75, 'nagado', 0.5)
        s.taiko(base + 3.0, 'odaiko', 0.6)
        for k in range(8):
            s.taiko(base + 0.5 * k, 'shime', 0.5 + (0.2 if k % 2 == 0 else 0.0))
        s.taiko(base + 1.0, 'kachi', 0.45)
        s.taiko(base + 3.5, 'kachi', 0.5)
    base = L + 11 * BPB  # fill into A''
    for k in range(8):
        s.taiko(base + 2.0 + 0.25 * k, 'shime', 0.45 + 0.06 * k)
    s.taiko(L + 48.0, 'odaiko', 0.95)
    s.perc(L + 48.0, 'gong', 0.45)
    s.taiko(L + 50.0, 'nagado', 0.4)
    s.taiko(L + 52.0, 'odaiko', 0.45)
    s.taiko(L + 54.0, 'nagado', 0.32)
    s.perc(L + 60.0, 'rin', 0.3)

    tracks = {
        'koto': engine.Track('koto', gain_db=6.5, reverb=0.28, eq=[(3500, 0.8, 1.5)], clip_db=3.0),
        'shaku': engine.Track('shaku', gain_db=-17.0, pan=0.08, reverb=0.34, hp=120),
        'taiko': engine.Track('taiko', gain_db=8.0, reverb=0.2, width=1.2, clip_db=6.0, hp=35),
        'perc': engine.Track('perc', gain_db=6.0, reverb=0.35),
    }
    ir = __import__('dsp').reverb_ir(2.3, __import__('dsp').rng('title-hall'), bright=0.5, predelay_ms=18, size=1.4)
    return engine.Piece('mus_title_nyaagyu_wind', '猫柳生の風 (Wind over Nyaagyu)', BPM, BPB, INTRO_BARS, LOOP_BARS,
                        tracks, s.events, ir, -16.0,
                        'Title / main menu theme: shakuhachi theme over hirajoshi koto and taiko',
                        programs={'koto': (0, 107), 'shaku': (1, 77)})
