"""「占領の街」 Occupied Streets — stealth loop with vertical layers (original composition, tier OWN).

Implements the ch03_stealth state design from docs/campaign/chapter-03.md §5.7 as four stems of one
16-bar loop at 84 BPM (45.7 s). All stems share length, gain and loop points, so the music system can
fade them in and out sample-synchronously:
  base    (unaware)    sparse kachi rim ticks, koto harmonics-like high plucks, low Credit House drone
  pulse   (suspicious) low string pulse (bowed psaltery + damped low koto) in eighths
  perc    (alert)      full taiko: odaiko, nagado pattern, shime ostinato
  search  (search)     percussion drops out; a ticking mokugyo / woodblock figure with a cold glass tick
State mixes: unaware = base; suspicious = base+pulse; alert = base+pulse+perc; search = base+pulse+search.
Mode: miyako-bushi on A (A Bb D E F), the Credit House drone a tritone-laced fifth under it.
"""
from __future__ import annotations

from common import Score

BPM = 84
BPB = 4
LOOP_BARS = 16


def build():
    import dsp
    import engine
    s = Score(BPM, seed=1623_03)
    s.loop_start = 0.0

    # ---- base: drone + rim ticks + high plucks ----
    for ph in range(4):  # a 4-bar cold drone, re-voiced each phrase
        root = ['A1', 'A1', 'Bb1', 'A1'][ph]
        fifth = ['E2', 'E2', 'F2', 'Eb2'][ph]  # the last phrase darkens to a tritone
        s.pad(ph * 16, [root, fifth], 16.0, v=0.5, cutoff=(140, 520), track='drone')
    tick_pattern = [(1.0, 0.45), (2.5, 0.3), (3.0, 0.4)]
    for bar in range(LOOP_BARS):
        for b, v in tick_pattern:
            if bar % 4 == 3 and b == 2.5:
                continue
            s.taiko(bar * 4 + b, 'kachi', v, track='rim', pan=0.25)
    harmonics = [(0.0, 'A5'), (6.0, 'E5'), (10.5, 'F5'), (16.0, 'D5'), (22.0, 'Bb4'), (26.5, 'A4'),
                 (32.0, 'A5'), (38.0, 'F5'), (42.5, 'E5'), (48.0, 'D5'), (54.0, 'Bb4'), (58.0, 'E5')]
    for beat, note in harmonics:  # biwa-like sparse high plucks, slightly bent
        s.koto(beat, note, 1.5, 0.42, bend=[(0, 0), (0.6, 0), (1.0, -35)], ring=3.0, track='pluck', pan=-0.3)

    # ---- pulse: low string eighths ----
    cell = ['A2', 'A2', 'A2', 'Bb2', 'A2', 'A2', 'E2', 'A2']
    for bar in range(LOOP_BARS):
        c = cell if bar % 4 != 2 else ['Bb2', 'Bb2', 'Bb2', 'A2', 'Bb2', 'Bb2', 'F2', 'Bb2']
        for i, note in enumerate(c):
            accent = 0.62 if i % 4 == 0 else 0.44
            s.koto(bar * 4 + 0.5 * i, note, 0.35, accent, damp=True, track='pulse_koto', pan=-0.1)
        if bar % 2 == 0:
            s.psaltery(bar * 4, 'A#3' if bar % 8 == 4 else 'A#3', 7.5, 0.35, track='pulse_bow', pan=0.3)

    # ---- perc: taiko ensemble ----
    for bar in range(LOOP_BARS):
        base = bar * 4
        s.taiko(base, 'odaiko', 0.8, track='taiko')
        for b, v in [(1.0, 0.55), (1.5, 0.45), (2.5, 0.6), (3.0, 0.5), (3.75, 0.4)]:
            s.taiko(base + b, 'nagado', v, track='taiko', pan=0.1)
        for k in range(16):
            v = 0.55 if k % 4 == 0 else (0.38 if k % 2 == 0 else 0.26)
            s.taiko(base + 0.25 * k, 'shime', v, track='taiko', pan=-0.25)
        if bar % 4 == 3:
            for k in range(4):
                s.taiko(base + 2.0 + 0.5 * k, 'odaiko', 0.5 + 0.1 * k, track='taiko')

    # ---- search: ticking figure ----
    for bar in range(LOOP_BARS):
        base = bar * 4
        for k in range(8):
            s.perc(base + 0.5 * k, 'woodblock' if k % 2 else 'mokugyo', 0.5 if k % 2 == 0 else 0.35, track='tick',
                   ratio=1.0 if k % 2 == 0 else 1.12)
        s.bell(base + 3.5, 'A6' if bar % 2 else 'Bb6', 0.25, t60=0.6, track='glass_tick', pan=0.4)

    tracks = {
        'drone': engine.Track('drone', gain_db=-13.0, reverb=0.3, stem='base', hp=35),
        'rim': engine.Track('rim', gain_db=22.0, reverb=0.35, stem='base', clip_db=3.0),
        'pluck': engine.Track('pluck', gain_db=7.0, reverb=0.45, stem='base', eq=[(4000, 0.7, 2.0)], clip_db=3.0),
        'pulse_koto': engine.Track('pulse_koto', gain_db=9.0, reverb=0.15, stem='pulse', lp=2500, clip_db=6.0),
        'pulse_bow': engine.Track('pulse_bow', gain_db=12.0, reverb=0.3, stem='pulse'),
        'taiko': engine.Track('taiko', gain_db=7.5, reverb=0.18, stem='perc', width=1.2, clip_db=8.0, hp=35),
        'tick': engine.Track('tick', gain_db=12.0, reverb=0.25, stem='search'),
        'glass_tick': engine.Track('glass_tick', gain_db=-7.0, reverb=0.4, stem='search'),
    }
    ir = dsp.reverb_ir(1.6, dsp.rng('ward-rain'), bright=0.4, predelay_ms=12, size=1.1)
    return engine.Piece('mus_ch03_occupation_stealth', '占領の街 (Occupied Streets)', BPM, BPB, 0, LOOP_BARS,
                        tracks, s.events, ir, -16.0,
                        'Stealth loop in four synchronous stems (unaware / suspicious / alert / search) for ch03',
                        programs={'pluck': (0, 107), 'pulse_koto': (0, 107), 'pulse_bow': (2, 110)},
                        reference_stems=['base', 'pulse', 'perc'])
