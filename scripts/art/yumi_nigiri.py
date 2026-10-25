"""The yumi's nigiri (W18): a built-up underlay wound with one skived deerskin strip.

Pure math, with no Blender. The generator (create_runtime_weapon_yumi.py)
builds the grip from it, and the host tests (test_yumi_draw.py) test the same
section.

**Why it changed.** Root's review of the first lit first-person originals
(Saved/YumiFP/v2) found the grip wraps read as large stepped plates. The cause
was the first generator's wound_strip. It lapped a 19 mm, 1.1 mm strip by
shearing its whole section by thick / (width x overlap) x 0.9, about 0.29.
That tilted every turn about 16 degrees, so each turn rose 2.75 mm at one edge
and sank into the underlay at the other: a tilted plate, stepping up to
3.8 mm at every seam.

**The wrap now:**

- **Underlay:** UNDERLAY_M of built-up padding, which sets the grip's girth.
  It is full in the body and tapers over its last SHOULDER_M to a fifth at
  either end.
- **Strip:** deerskin, WIDTH_M wide and THICK_M thick. Each turn laps the turn
  before by OVERLAP of its width, so the pitch is WIDTH_M x (1 - OVERLAP).
- **Section across one pitch, along the stave:**
  - at its start, the turn's cut edge, skived, stands EDGE_M proud of the
    turn before;
  - it rises to LAP_M over the covered edge it rides, about a third of the
    way into the lap;
  - it drapes back down by the lap's end, then lies flat on the underlay.
  Turn k+1 starts where turn k's section ends, so the wrap is one surface with
  a fine spiral step, not a stack of plates.

The outermost leather stands UNDERLAY_M + THICK_M + LAP_M (3.85 mm) off the
stave. That keeps the girth the bow paw is fitted to
(nyaakoto_fp_paws.GRIP_WRAP, measured from the rig), and stays inside
yumi_draw.ENVELOPE_GRIP_M (4 mm).
"""
from __future__ import annotations

import math

UNDERLAY_M = 0.0028
WIDTH_M = 0.013
THICK_M = 0.0006
OVERLAP = 0.30
EDGE_M = 0.00022
LAP_M = 0.00045
CREST = 0.35                 # the lap's crest, as a fraction of the lapped part
BURY_M = 0.0003              # the section's floor, inside the underlay
SHOULDER_M = 0.006
# How far inside the underlay's ends the strip's section reaches (lower,
# upper). The strip runs on over the shoulders, riding their taper, because a
# helix leaves bare underlay within one pitch of either end at some angles.
# Its covered span (every angle round the grip) must hold the bow paw's grip.
WRAP_INSET_M = (0.0005, 0.0005)
# The section's samples across the pitch (v = 0 at the cut edge), densest at the edge.
V_SAMPLES = (0.0, 0.015, 0.04, 0.08)


def smooth01(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def pitch():
    """The strip's advance per turn, along the stave."""
    return WIDTH_M * (1.0 - OVERLAP)


def lapped():
    """The part of a pitch that rides over the turn before (v from 0)."""
    return WIDTH_M * OVERLAP / pitch()


def shoulder(sig, grip_half):
    """The underlay's height, as a fraction of UNDERLAY_M, at arc position sig."""
    return 0.2 + 0.8 * smooth01((grip_half - abs(sig)) / SHOULDER_M)


def height(v):
    """The strip's top above the underlay at v in [0, 1] across one pitch."""
    v_lap = lapped()
    v_crest = v_lap * CREST
    if v <= v_crest:
        return THICK_M + EDGE_M + (LAP_M - EDGE_M) * smooth01(v / v_crest)
    if v <= v_lap:
        return THICK_M + LAP_M * (1.0 - smooth01((v - v_crest) / (v_lap - v_crest)))
    return THICK_M


def section_vs():
    """The v of each top sample, in order from the cut edge (0) to the next turn (1)."""
    v_lap = lapped()
    v_crest = v_lap * CREST
    vs = set(V_SAMPLES) | {v_crest, v_crest + (v_lap - v_crest) * 0.35, v_crest + (v_lap - v_crest) * 0.7, v_lap,
                           0.6, 0.8, 1.0}
    return sorted(vs)


def section():
    """One turn's section as (radial, along) points, a closed loop.

    The top runs from the turn's cut edge (along = -pitch/2) to where the next
    turn starts (+pitch/2), then the floor runs back BURY_M inside the underlay.
    Radial is off the underlay; along is along the stave, toward the upper limb."""
    p = pitch()
    top = [(height(v), (v - 0.5) * p) for v in section_vs()]
    floor = [(-BURY_M, 0.5 * p), (-BURY_M, -0.5 * p)]
    return top + floor


def wrap_span(grip_half):
    """(sig0, sig1): the strip's path from end to end, half a pitch inside its
    full-height span, which is WRAP_INSET_M inside the underlay's ends."""
    half = pitch() / 2
    return -grip_half + WRAP_INSET_M[0] + half, grip_half - WRAP_INSET_M[1] - half


def reach(grip_half):
    """The arc span (lower, upper) the strip's section reaches at some angle."""
    sig0, sig1 = wrap_span(grip_half)
    return sig0 - pitch() / 2, sig1 + pitch() / 2


def covered_span(grip_half):
    """The arc span (lower, upper) the strip covers at every angle round the grip."""
    sig0, sig1 = wrap_span(grip_half)
    return sig0 + pitch() / 2, sig1 - pitch() / 2


def max_elevation():
    """The outermost leather's height off the stave."""
    return UNDERLAY_M + THICK_M + LAP_M
