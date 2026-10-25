"""The across-grain slope of a camera-space normal render, with the camera-space sign convention checked.

Numpy only, so the host can test it; render_timber_patch_study.py applies it
to its <Variant>_Normal EXRs.

**The convention.** The study writes Cycles' Vector Transform of the shading
normal from world to camera space, encoded n * 0.5 + 0.5. Cycles' camera
space looks along +z: a face turned toward the camera has z near -1, not +1.
Attempt 0's EXRs show it (Column v23: every pixel's z is below -0.12, the
median -0.99997, with unit length).

**The bug this replaces.** Attempt 0 divided the across-grain component by z
clamped at 1e-3. With z near -1 everywhere, every pixel took the clamp, so
each slope was the across-grain component times 1000.

**Here:** the slope is the across-grain component over the facing component,
-z. The render must hold unit normals facing the camera (median length
within LENGTH_RANGE, median facing above FACING_MIN), as the study already
requires of each scan's normal map, or it is refused.
"""
from __future__ import annotations

import numpy as np

LENGTH_RANGE = (0.95, 1.05)
FACING_MIN = 0.9
FACING_FLOOR = 1e-3        # only a grazing or back-facing pixel reaches it


class NormalRenderError(ValueError):
    """The render is not unit camera-space normals facing the camera."""


def decode(encoded):
    """(H, W, >=3) values encoded n * 0.5 + 0.5 -> (H, W, 3) normals."""
    return np.asarray(encoded, dtype=np.float64)[..., :3] * 2.0 - 1.0


def check(n):
    """The render's unit-normal and facing statistics, or NormalRenderError."""
    length = np.linalg.norm(n, axis=2)
    facing = -n[..., 2]
    stats = {"median_length": float(np.median(length)), "median_facing": float(np.median(facing)),
             "min_facing": float(facing.min()), "pixels_below_floor": int((facing < FACING_FLOOR).sum())}
    if not (LENGTH_RANGE[0] < stats["median_length"] < LENGTH_RANGE[1] and stats["median_facing"] > FACING_MIN):
        raise NormalRenderError(f"not unit camera-space normals facing the camera: {stats}")
    return stats


def across_slope(n, across):
    """(slope (H, W), check statistics). ``across`` is the image axis across the grain: "x" (columns) or "y"
    (rows); its sign is irrelevant to a band RMS."""
    if across not in ("x", "y"):
        raise ValueError(f"across must be 'x' or 'y', not {across!r}")
    stats = check(n)
    component = n[..., 0] if across == "x" else n[..., 1]
    return component / np.maximum(-n[..., 2], FACING_FLOOR), stats
