"""「複利号」 The Compound-Interest Flagship — battle loop (original composition, tier OWN).

For mus_ch07_hangar / boss_collatera P2 ("full percussion plus alien pulses", chapter-07.md §5.8).
24 bars at 132 BPM in 4/4 (43.6 s), two synchronous stems:
  synth  the Credit House: cold detuned-saw pad moving by minor thirds (C - Eb - F# - A, a symmetric,
         "ordered" cycle), sub pulse in eighths ducked like a sidechain, FM glass arpeggio on the octatonic
         (half-whole) scale, real VCSL wine-glass tones as a frozen high layer, metal hits on phrase starts
  taiko  the League: odaiko / nagado drive, shime sixteenths, kachi backbeats, fills every 8 bars
Loop mix = synth + taiko, mastered to -16 LUFS integrated.
"""
from __future__ import annotations

from common import Score

BPM = 132
BPB = 4
LOOP_BARS = 24

CYCLE = [('C', ['C3', 'G3', 'Db4', 'F#4'], 'C2'), ('Eb', ['Eb3', 'Bb3', 'E4', 'A4'], 'Eb2'),
         ('F#', ['F#2', 'C#3', 'G3', 'C4'], 'F#1'), ('A', ['A2', 'E3', 'Bb3', 'Eb4'], 'A1')]
# octatonic (half-whole) on C: C Db Eb E F# G A Bb
ARP = {'C': ['C5', 'Db5', 'G5', 'F#5', 'C6', 'G5', 'Db5', 'F#5'],
       'Eb': ['Eb5', 'E5', 'Bb5', 'A5', 'Eb6', 'Bb5', 'E5', 'A5'],
       'F#': ['F#5', 'G5', 'C6', 'Db6', 'F#6', 'C6', 'G5', 'Db6'],
       'A': ['A4', 'Bb4', 'E5', 'Eb5', 'A5', 'E5', 'Bb4', 'Eb5']}


def build():
    import dsp
    import engine
    s = Score(BPM, seed=1623_07)
    s.loop_start = 0.0
    for bar in range(LOOP_BARS):
        key, chord, root = CYCLE[(bar // 2) % 4]
        base = bar * 4
        if bar % 2 == 0:
            s.pad(base, chord, 8.0, v=0.55, cutoff=(350, 1800), track='pad')
        # sub pulse: eighths, the offbeats a touch lower (reads as a sidechained bass)
        for k in range(8):
            s.sub(base + 0.5 * k, root, 0.45, v=0.8 if k % 2 == 0 else 0.55, track='sub')
        # glass arpeggio in sixteenths on bars 5-8, 13-16, 21-24 (8th-notes elsewhere)
        dense = (bar // 4) % 2 == 1
        step = 0.25 if dense else 0.5
        notes = ARP[key]
        for k in range(int(4 / step)):
            s.bell(base + k * step, notes[k % len(notes)], 0.32 if k % 4 else 0.45, t60=0.5 if dense else 0.9,
                   track='arp', pan=(-0.5 if k % 2 else 0.5))
        if bar % 8 == 0:
            s.metal(base, 0.8, track='metal')
            s.glass(base, {'C': 'D#5', 'Eb': 'F#5', 'F#': 'A#5', 'A': 'D5'}[key], 30.0, 0.35, track='glassline')
        # ---- taiko ----
        s.taiko(base, 'odaiko', 0.9)
        s.taiko(base + 2.0, 'odaiko', 0.7)
        for b, v in [(0.75, 0.5), (1.0, 0.7), (1.5, 0.55), (2.75, 0.5), (3.0, 0.72), (3.5, 0.6)]:
            s.taiko(base + b, 'nagado', v, pan=0.15)
        for k in range(16):
            s.taiko(base + 0.25 * k, 'shime', 0.6 if k % 4 == 0 else (0.42 if k % 2 == 0 else 0.3), pan=-0.3)
        s.taiko(base + 1.0, 'kachi', 0.6, pan=0.3)
        s.taiko(base + 3.0, 'kachi', 0.6, pan=0.3)
        if bar % 8 == 7:  # fill: nagado sixteenths crescendo into the next phrase (and into the loop start)
            for k in range(8):
                s.taiko(base + 2.0 + 0.25 * k, 'nagado', 0.5 + 0.06 * k, pan=(-0.2 if k % 2 else 0.2))
    tracks = {
        'pad': engine.Track('pad', gain_db=-7.0, reverb=0.35, stem='synth', hp=60),
        'sub': engine.Track('sub', gain_db=-7.0, reverb=0.0, stem='synth', hp=28),
        'arp': engine.Track('arp', gain_db=-3.0, reverb=0.4, stem='synth', hp=300),
        'metal': engine.Track('metal', gain_db=-2.0, reverb=0.45, stem='synth'),
        'glassline': engine.Track('glassline', gain_db=20.0, reverb=0.4, stem='synth', width=1.3),
        'taiko': engine.Track('taiko', gain_db=5.5, reverb=0.16, stem='taiko', width=1.2, clip_db=7.0, hp=35),
    }
    ir = dsp.reverb_ir(2.4, dsp.rng('flagship-hangar'), bright=0.7, predelay_ms=16, size=1.5)
    return engine.Piece('mus_ch07_flagship_battle', '複利号 (The Compound-Interest Flagship)', BPM, BPB, 0, LOOP_BARS,
                        tracks, s.events, ir, -16.0,
                        'Alien flagship battle loop: cold synth stem + taiko stem (ch07 hangar / Collatera P2)',
                        programs={'pad': (4, 94), 'arp': (5, 98), 'sub': (6, 38), 'glassline': (3, 92)})
