"""Author the original particle textures that scripts/unreal/create_sora_vfx.py imports.

Every map is procedural and seeded, so a rerun reproduces the same bytes on the
same numpy. No third-party image enters them. Flipbooks are 8x8 frames of
256 px read left to right, top to bottom; packed channels are linear data
(the importer turns sRGB off) except the colour sprites of scraps and fur.

    python3 scripts/art/create_vfx_textures.py [--preview DIR]

writes Content/SourceArt/VFX/Textures/*.png and Content/SourceArt/VFX/manifest.json
(a schema-2 OWN document the asset ledger reads). --preview also writes
contact sheets with the channels spread out for review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Content/SourceArt/VFX"
DEST = SOURCE / "Textures"
SEED = 20260926
FRAMES = 8          # flipbook grid side
FRAME_PX = 256


# ---------------------------------------------------------------- noise

class Noise:
    """Tileable 3D gradient noise with a fixed permutation."""

    def __init__(self, seed: int):
        rng = np.random.default_rng(seed)
        self.perm = np.tile(rng.permutation(256).astype(np.int32), 2)
        angles = rng.uniform(0, 2 * np.pi, (256, 2))
        z = rng.uniform(-1, 1, 256)
        r = np.sqrt(1 - z * z)
        self.grad = np.stack([r * np.cos(angles[:, 0]), r * np.sin(angles[:, 0]), z], axis=1).astype(np.float32)

    def _hash(self, x, y, z):
        p = self.perm
        return p[p[p[x & 255] + (y & 255)] + (z & 255)]

    def gradient(self, x, y, z, period):
        """Perlin noise in about [-1, 1], periodic in each axis with integer period."""
        px, py, pz = period
        xi, yi, zi = np.floor(x).astype(np.int32), np.floor(y).astype(np.int32), np.floor(z).astype(np.int32)
        xf, yf, zf = (x - xi).astype(np.float32), (y - yi).astype(np.float32), (z - zi).astype(np.float32)
        u, v, w = (t * t * t * (t * (t * 6 - 15) + 10) for t in (xf, yf, zf))
        result = 0
        for dx in (0, 1):
            for dy in (0, 1):
                for dz in (0, 1):
                    h = self._hash((xi + dx) % px, (yi + dy) % py, (zi + dz) % pz)
                    g = self.grad[h]
                    dot = g[..., 0] * (xf - dx) + g[..., 1] * (yf - dy) + g[..., 2] * (zf - dz)
                    weight = (u if dx else 1 - u) * (v if dy else 1 - v) * (w if dz else 1 - w)
                    result = result + weight * dot
        return result * 1.6

    def fbm(self, x, y, z, octaves=5, period=(256, 256, 256), gain=.5, billow=False):
        total, amplitude, norm = 0, 1.0, 0
        px, py, pz = period
        for octave in range(octaves):
            f = 2 ** octave
            n = self.gradient(x * f, y * f, z * f, (px * f, py * f, pz * f))
            total = total + amplitude * (1 - 2 * np.abs(n) if billow else n)
            norm += amplitude
            amplitude *= gain
        return total / norm


def smoothstep(edge0, edge1, x):
    t = np.clip((x - edge0) / (edge1 - edge0), 0, 1)
    return t * t * (3 - 2 * t)


def grid(size):
    coordinate = (np.arange(size, dtype=np.float32) + .5) / size * 2 - 1
    return np.meshgrid(coordinate, coordinate)


def atlas(frames):
    """Tile a list of HxWxC frames into a square atlas, row major."""
    side = int(round(len(frames) ** .5))
    rows = [np.concatenate(frames[r * side:(r + 1) * side], axis=1) for r in range(side)]
    return np.concatenate(rows, axis=0)


def to_u8(array):
    return (np.clip(array, 0, 1) * 255 + .5).astype(np.uint8)


# ---------------------------------------------------------------- flipbooks

def billow_flipbook(noise, *, grow, warp, erosion, heat, turbulence, opacity):
    """A puff that swells, breaks up and thins: R density, G heat, B thickness.

    Each frame integrates a noisy sphere along the view: the chord through the
    displaced surface times a soft internal density gives optical depth, and
    1 - exp(-depth) the coverage, so the limb thins like a real cloud. Rounded
    lobes come from ridged-inverted noise (2|n| - 1); erosion eats the thin limb
    first and then opens holes toward the core.
    """
    x, y = grid(FRAME_PX)
    frames = []
    count = FRAMES * FRAMES
    border = smoothstep(1.0, .8, np.sqrt(x * x + y * y))      # round, so rotated sprites never show a frame edge
    for index in range(count):
        t = index / (count - 1)
        radius = grow[0] + (grow[1] - grow[0]) * (1 - (1 - t) ** 2.4)
        z = np.full_like(x, t * 1.4)
        wx = noise.fbm(x * 1.2 + 3.1, y * 1.2, z, 3)
        wy = noise.fbm(x * 1.2, y * 1.2 + 7.7, z + 11.0, 3)
        qx, qy = (x + warp * radius * wx) / radius, (y + warp * radius * wy) / radius
        lobes = -noise.fbm(qx * 2.2, qy * 2.2, z * turbulence + 5.0, 4, billow=True)   # 2|n|-1: rounded bumps
        edge = np.sqrt(qx * qx + qy * qy) - .22 * lobes
        chord = np.sqrt(np.clip(1 - edge * edge, 0, 1))
        inner = .5 + .5 * noise.fbm(qx * 3.2, qy * 3.2, z * turbulence + 20.0, 5)
        fine = .5 + .5 * noise.fbm(qx * 9.0, qy * 9.0, z * 2.5 + 40.0, 3)
        e = erosion[0] + (erosion[1] - erosion[0]) * t ** 1.3
        medium = np.clip(inner * (.75 + .5 * fine) - e * (1.25 - chord), 0, None)
        depth = opacity * (1 - .55 * t) * chord * medium
        density = (1 - np.exp(-depth)) * border
        hot = np.clip(chord * inner * 1.4 - .35, 0, 1) * (1 - t) ** heat
        thickness = np.clip(depth / max(float(np.percentile(depth, 99.5)), 1e-4), 0, 1)
        frames.append(np.stack([density, hot * (density > .02), ndimage.gaussian_filter(thickness, 3)], axis=-1))
    return atlas(frames)


def fire_flipbook(noise):
    """A seamlessly looping flame sheet: R temperature, G opacity, B tongue mask.

    Height-weighted noise overtakes the envelope toward the top, so the flame
    splits into tongues and sheds detached licks; the noise is periodic in the
    rise direction and in time, so frame 63 flows into frame 0.
    """
    size = FRAME_PX
    col = (np.arange(size, dtype=np.float32) + .5) / size * 2 - 1
    row = 1 - (np.arange(size, dtype=np.float32) + .5) / size      # 0 at the bottom row
    x, y = np.meshgrid(col, row)
    count = FRAMES * FRAMES
    frames = []
    for index in range(count):
        phase = index / count
        z = np.full_like(x, phase * 4)
        rise = phase * 8
        sway = noise.fbm(x * 1.2, y * 1.0 - rise * .25, z, 3, period=(256, 2, 4))
        xd = x + .28 * y ** 1.2 * sway
        n = noise.fbm(xd * 3.0, y * 2.0 - rise, z + 1.3, 5, period=(256, 16, 4))
        width = (.40 * np.clip(1 - y, 0, 1) ** .45 + .06) * smoothstep(-.12, .22, y) ** .5   # rounded root
        core = 1 - np.abs(xd) / width
        f = core * (1 - y ** 1.3) + (.18 + .9 * y) * .75 * n
        base = smoothstep(0, .12, y) * smoothstep(1.0, .9, y) * smoothstep(1.0, .88, np.abs(x))
        body = smoothstep(.05, .75, f) * base
        temperature = body * (1 - .45 * y) * (.85 + .3 * n)
        opacity = smoothstep(.02, .3, body)
        frames.append(np.stack([np.clip(temperature, 0, 1), opacity, smoothstep(-.2, .6, n) * body], axis=-1))
    return atlas(frames)


# ---------------------------------------------------------------- single sheets

def flash_sheet(noise, rng):
    """2x2 luminance shapes: powder flash face-on, powder plume side-on, energy star, shock ring."""
    size = 512
    x, y = grid(size)
    r = np.sqrt(x * x + y * y)
    a = np.arctan2(y, x)
    z0 = np.zeros_like(x)
    # 0: black-powder flash seen down the barrel: irregular flame petals around a hot core.
    lobes = np.zeros_like(x)
    for k, amp in ((5, .45), (7, .3), (11, .18)):
        lobes += amp * np.cos(k * a + rng.uniform(0, 2 * np.pi))
    ragged = noise.fbm(x * 5, y * 5, z0 + 1, 5)
    petal_r = .5 * (1 + .5 * lobes + .3 * ragged)
    body = np.exp(-(r / np.maximum(petal_r, .05)) ** 2 * 2.0) * (.7 + .5 * noise.fbm(x * 11, y * 11, z0 + 3, 4))
    face = .95 * np.clip(body, 0, None) + .8 * np.exp(-(r / .12) ** 2)
    # 1: the same flash from the side, muzzle at the bottom edge, plume toward the top (-V),
    #    so a sprite aligned to the barrel with its pivot at the bottom points it forward.
    u = (1 - y) / 2                  # 0 at the bottom row, 1 at the top
    across = x
    tongues = noise.fbm(u * 5, across * 4, z0 + 5, 5)
    plume_w = (.06 + .38 * np.clip(np.sin(np.clip(u * 1.05, 0, 1) * np.pi), 0, 1) ** 1.2 * (1 - u) ** .35) * (1 + .45 * tongues)
    plume = np.exp(-(across / np.maximum(plume_w, .02)) ** 2) * (1 - u) ** 1.1 * smoothstep(0, .05, u)
    plume *= np.clip(.75 + .6 * noise.fbm(u * 12, across * 12, z0 + 6, 4), 0, None)
    side = .8 * plume + .7 * np.exp(-(((u - .06) / .09) ** 2 + (across / .08) ** 2))
    # 2: energy discharge: tight core, thin rays, a faint ring.
    rays = np.zeros_like(x)
    for k in range(10):
        angle = k * np.pi / 5 + rng.uniform(-.2, .2)
        along = x * np.cos(angle) + y * np.sin(angle)
        across = -x * np.sin(angle) + y * np.cos(angle)
        rays += np.exp(-(across / .012) ** 2) * np.clip(1 - np.abs(along) / rng.uniform(.6, .95), 0, 1) ** 2
    star = 1.8 * np.exp(-(r / .07) ** 2) + .5 * np.exp(-(r / .22) ** 2) + .45 * rays \
        + .35 * np.exp(-((r - .55) / .025) ** 2)
    # 3: shock ring, broken by noise sampled on the plane (no seam).
    ring = np.exp(-((r - .72) / .06) ** 2) * (.55 + .45 * noise.fbm(x * 4, y * 4, z0 + 9, 3)) \
        * smoothstep(1.0, .9, r)
    sheet = [face, side, star, ring]
    sheet = [np.clip(np.nan_to_num(sh) / float(np.nan_to_num(sh).max()), 0, 1) for sh in sheet]
    return np.concatenate([np.concatenate(sheet[:2], 1), np.concatenate(sheet[2:], 1)], 0)


def noise_sheet(noise):
    """Tileable RGBA: R broad fbm, G fine fbm, B cellular, A billow."""
    size = 512
    coordinate = np.arange(size, dtype=np.float32) / size
    x, y = np.meshgrid(coordinate, coordinate)
    z = np.zeros_like(x)
    broad = .5 + .5 * noise.fbm(x * 4, y * 4, z, 5, period=(4, 4, 256))
    fine = .5 + .5 * noise.fbm(x * 16, y * 16, z + 3, 4, period=(16, 16, 256))
    billow = .5 + .5 * noise.fbm(x * 6, y * 6, z + 7, 5, period=(6, 6, 256), billow=True)
    rng = np.random.default_rng(SEED + 5)
    points = rng.uniform(0, 1, (48, 2))
    tiles = np.concatenate([points + [dx, dy] for dx in (-1, 0, 1) for dy in (-1, 0, 1)])
    distance = np.full_like(x, 9.0)
    for px, py in tiles:
        distance = np.minimum(distance, np.hypot(x - px, y - py))
    cells = np.clip(distance / distance.max(), 0, 1)

    def stretch(channel):
        low, high = np.percentile(channel, (.5, 99.5))
        return np.clip((channel - low) / (high - low), 0, 1)
    return np.stack([stretch(broad), stretch(fine), cells, stretch(billow)], axis=-1)


def water_sheet(noise, rng):
    """2x2 water shapes, R opacity, G highlight, B thickness: spray, sheet, foam, mist."""
    size = 512
    x, y = grid(size)
    r = np.sqrt(x * x + y * y)
    z0 = np.zeros_like(x)

    def droplets(count, spread, radius_range, stretch=1.0):
        opacity = np.zeros_like(x)
        highlight = np.zeros_like(x)
        for _ in range(count):
            cx, cy = rng.normal(0, spread, 2)
            if abs(cx) > .85 or abs(cy) > .85:
                continue
            rad = rng.uniform(*radius_range) * (1.2 - .5 * min(1, np.hypot(cx, cy)))
            d = np.hypot((x - cx) / stretch, y - cy) / rad
            body = smoothstep(1.0, .7, d)
            opacity = np.maximum(opacity, body * (.55 + .45 * smoothstep(.3, .95, d)))
            spot = np.exp(-(((x - cx + .3 * rad) ** 2 + (y - cy + .3 * rad) ** 2) / (.22 * rad) ** 2))
            highlight = np.maximum(highlight, spot * body)
        return opacity, highlight

    spray_o, spray_h = droplets(300, .36, (.006, .03))
    spray = np.stack([spray_o, spray_h, ndimage.gaussian_filter(spray_o, 3)], -1)

    # A crown sheet thrown upward: thin film streaked along its throw, thinning to droplets at the rim.
    fan = np.arctan2(-y + .75, x)                      # rays from a point low in the cell
    rr = np.hypot(x, y - .75)
    along = smoothstep(.05, .35, rr) * smoothstep(1.35, .9, rr)
    spread = smoothstep(.0, .35, np.sin(np.clip(fan, 0, np.pi)))
    streaks = .5 + .5 * noise.fbm(fan * 14, rr * 1.5, z0 + 2, 4)
    tears = smoothstep(.3, .6, .5 + .5 * noise.fbm(fan * 6, rr * 5, z0 + 4, 4) + .25 * (1.2 - rr))
    sheet_o = along * spread * tears * (.25 + .5 * streaks) * smoothstep(1.0, .85, np.abs(x)) * smoothstep(1.0, .85, np.abs(y))
    rim_o, rim_h = droplets(140, .5, (.008, .026))
    rim_mask = smoothstep(.8, 1.1, rr) * spread
    sheet = np.stack([np.maximum(sheet_o, rim_o * rim_mask), np.maximum(streaks ** 8 * sheet_o, rim_h * rim_mask),
                      ndimage.gaussian_filter(sheet_o, 4)], -1)

    # Whitewater: lace from high-frequency billows plus a scatter of bubble rings.
    lace = smoothstep(.55, .85, .5 + .5 * noise.fbm(x * 9, y * 9, z0 + 6, 4, billow=True))
    bubbles = np.zeros_like(x)
    for cx, cy, rad in zip(rng.uniform(-.75, .75, 90), rng.uniform(-.75, .75, 90), rng.uniform(.01, .045, 90)):
        d = np.hypot(x - cx, y - cy) / rad
        bubbles = np.maximum(bubbles, smoothstep(.65, .9, d) * smoothstep(1.1, .9, d))
    foam_mask = smoothstep(.95, .35, r + .2 * noise.fbm(x * 2, y * 2, z0 + 7, 3))
    foam_o = np.clip(.8 * lace + .7 * bubbles + .15, 0, 1) * foam_mask
    foam = np.stack([foam_o, bubbles * foam_mask * .7, ndimage.gaussian_filter(foam_o, 5)], -1)

    mist_o = smoothstep(1.0, .2, r + .25 * noise.fbm(x * 2, y * 2, z0 + 8, 4)) * (.55 + .45 * noise.fbm(x * 6, y * 6, z0 + 9, 5))
    mist = np.stack([np.clip(mist_o, 0, 1) * .8, z0, ndimage.gaussian_filter(np.clip(mist_o, 0, 1), 12)], -1)
    return np.concatenate([np.concatenate([spray, sheet], 1), np.concatenate([foam, mist], 1)], 0)


def torn_polygon(x, y, rng, noise, z0, vertices, torn_edges):
    """Alpha of a paper-like polygon: straight cut edges, some edges torn and fibrous."""
    angles = (np.arange(vertices) + rng.uniform(-.3, .3, vertices)) * 2 * np.pi / vertices + rng.uniform(0, 2 * np.pi)
    points = np.stack([np.cos(angles), np.sin(angles)], 1) * rng.uniform(.55, .8, (vertices, 1))
    inside = np.ones_like(x)
    for index in range(vertices):
        p0, p1 = points[index], points[(index + 1) % vertices]
        edge = p1 - p0
        normal = np.array([edge[1], -edge[0]]) / np.linalg.norm(edge)
        distance = (x - p0[0]) * normal[0] + (y - p0[1]) * normal[1]      # > 0 outside
        if index in torn_edges:
            distance = distance + .035 * noise.fbm(x * 14, y * 14, z0 + index, 5) + .012 * noise.fbm(x * 70, y * 70, z0 + index, 2)
            soft = .012
        else:
            soft = .004
        inside = inside * smoothstep(soft, -soft, distance)
    return inside


def scraps_sheet(noise, rng):
    """2x2 sRGB RGBA: two torn washi talisman scraps, a dry leaf, a charred flake."""
    size = 256
    x, y = grid(size)
    z0 = np.zeros_like(x)
    fibre = noise.fbm(x * 40, y * 6, z0 + 1, 3) + .5 * noise.fbm(x * 90, y * 90, z0 + 2, 2)
    cells = []
    for index in range(2):
        alpha = torn_polygon(x, y, rng, noise, z0, 5 + index, {1, 3} if index == 0 else {0, 2, 4})
        base = np.array([.84, .81, .72])[None, None, :] * (1 + .05 * fibre[..., None])
        if index == 0:
            # a corner of a vermilion seal impression, uneven like a real stamp
            frame = np.abs(np.maximum(np.abs(x + .15), np.abs(y - .05)) - .26) < .035
            glyph = ((np.abs(y - .05 - .08 * np.sign(x + .15)) < .025) | (np.abs(x + .15 - .05 * (y - .05)) < .025)) \
                & (np.abs(x + .15) < .18) & (np.abs(y - .05) < .18)
            ink = (frame | glyph) * np.clip(.55 + .6 * noise.fbm(x * 25, y * 25, z0 + 5, 3), 0, 1)
            base = base * (1 - ink[..., None]) + np.array([.58, .1, .06])[None, None, :] * ink[..., None]
        else:
            # brushed sumi strokes of a talisman
            stroke = np.exp(-((x - .05 + .15 * np.sin(y * 3)) / .04) ** 2) * (np.abs(y) < .45) \
                * np.clip(.5 + noise.fbm(x * 12, y * 30, z0 + 6, 3), 0, 1)
            base = base * (1 - .9 * stroke[..., None])
        cells.append(np.concatenate([base, alpha[..., None]], -1))
    # dry leaf: a lobed blade with a midrib and pinnate veins
    angle = np.arctan2(y, x * 1.7)
    lobed = .75 * (1 + .12 * np.cos(5 * angle)) * (1 + .03 * noise.fbm(x * 30, y * 30, z0 + 7, 3))
    leaf_a = smoothstep(1.0, .97, np.hypot(x * 1.7, y) / lobed)
    midrib = np.exp(-(y / .012) ** 2) * (x > -.7)
    veins = np.exp(-((np.abs(y) - (x + .6) * .5) % .18 / .012 - 0) ** 2) * (np.abs(y) > .02)
    tone = 1 + .18 * noise.fbm(x * 6, y * 6, z0 + 8, 4) + .06 * fibre
    leaf_c = np.array([.40, .24, .10])[None, None, :] * tone[..., None] * (1 - .3 * np.clip(midrib + .6 * veins, 0, 1))[..., None]
    cells.append(np.concatenate([leaf_c, leaf_a[..., None]], -1))
    # charred flake: dark, curled, a thin ember-bright rim kept in the colour
    flake_r = .6 * (1 + .3 * noise.fbm(x * 3, y * 3, z0 + 10, 4))
    flake_a = smoothstep(1.0, .9, np.hypot(x, y) / flake_r)
    rim = smoothstep(.75, .95, np.hypot(x, y) / flake_r) * flake_a
    flake_c = np.array([.05, .045, .04])[None, None, :] * (1 + .3 * fibre[..., None]) \
        + rim[..., None] * np.array([.5, .16, .03])[None, None, :]
    cells.append(np.concatenate([flake_c, flake_a[..., None]], -1))
    return np.concatenate([np.concatenate(cells[:2], 1), np.concatenate(cells[2:], 1)], 0)


def fur_sheet(rng):
    """2x2 luminance+alpha locks of shed hair (agouti-banded), tinted by the particle colour."""
    size = 256
    sub = 3                                   # draw at 3x and filter down for clean strands
    big = size * sub
    cells = []
    for index in range(4):
        coverage = np.zeros((big, big), np.float32)
        shade = np.zeros((big, big), np.float32)
        lock_angle = rng.uniform(0, np.pi)
        spread = .12 + .06 * index
        centre = np.array([big / 2, big / 2]) + rng.normal(0, 10 * sub, 2)
        for _ in range(90 + 30 * index):
            angle = lock_angle + rng.normal(0, spread)
            length = rng.uniform(.35, .8) * big / 2
            wave = rng.normal(0, .004)
            offset = rng.normal(0, 18 * sub, 2)
            start = centre + offset - np.array([np.cos(angle), np.sin(angle)]) * length / 2
            s = np.linspace(0, 1, int(length * 1.5))
            heading = angle + wave * s * length + rng.normal(0, .05) * np.sin(s * np.pi * 2)
            px = start[0] + np.cumsum(np.cos(heading)) * length / len(s)
            py = start[1] + np.cumsum(np.sin(heading)) * length / len(s)
            # agouti banding: dark base, pale band, dark tip; white hairs have none
            white = rng.random() < .3
            band = np.where(white, .9, np.where(s > .82, .18, np.where(s > .55, .8, .35)))
            ix, iy = px.astype(int), py.astype(int)
            keep = (ix >= 0) & (ix < big) & (iy >= 0) & (iy < big)
            taper = np.clip((1 - s) * 1.4, 0, 1) ** .6
            np.maximum.at(coverage, (iy[keep], ix[keep]), taper[keep])
            np.maximum.at(shade, (iy[keep], ix[keep]), band[keep] if not white else np.full(keep.sum(), .9))
        coverage = ndimage.gaussian_filter(coverage, sub * .6)
        shade = ndimage.gaussian_filter(shade * (coverage > 0), sub * .6) / np.maximum(ndimage.gaussian_filter((coverage > 0).astype(np.float32), sub * .6), 1e-3)
        coverage = coverage.reshape(size, sub, size, sub).mean(axis=(1, 3))
        shade = shade.reshape(size, sub, size, sub).mean(axis=(1, 3))
        alpha = np.clip(coverage * 2.2, 0, 1)
        lum = np.clip(shade, 0, 1)
        cells.append(np.stack([lum, lum, lum, alpha], -1))
    return np.concatenate([np.concatenate(cells[:2], 1), np.concatenate(cells[2:], 1)], 0)


# ---------------------------------------------------------------- output

TEXTURES = {
    # name: (channels, srgb, role)
    "T_VFX_SmokePuff": ("RGB", False, "8x8 flipbook: R density, G heat, B thickness; a soft puff that swells and thins"),
    "T_VFX_Fireball": ("RGB", False, "8x8 flipbook: R density, G heat, B thickness; a violent fireball rolling into smoke"),
    "T_VFX_Fire": ("RGB", False, "8x8 looping flipbook: R temperature, G opacity, B tongue mask; flames rise along -V"),
    "T_VFX_Flash": ("L", False, "2x2 luminance: powder flash face-on, powder plume side-on (muzzle at the bottom edge, plume toward the top), energy star, shock ring"),
    "T_VFX_Noise": ("RGBA", False, "tileable: R broad fbm, G fine fbm, B cellular distance, A billow"),
    "T_VFX_Water": ("RGB", False, "2x2: spray droplets, splash sheet, foam, mist; R opacity, G highlight, B thickness"),
    "T_VFX_Scraps": ("RGBA", True, "2x2 colour sprites: torn washi talisman scraps (one with seal ink), dry leaf, charred flake"),
    "T_VFX_Fur": ("RGBA", False, "2x2 locks of shed hair, agouti-banded: RGB luminance, A coverage; tinted by the particle colour"),
}


def build():
    noise = Noise(SEED)
    rng = np.random.default_rng(SEED)
    return {
        "T_VFX_SmokePuff": billow_flipbook(noise, grow=(.45, .74), warp=.24, erosion=(.0, .55), heat=3.0, turbulence=1.0, opacity=3.2),
        "T_VFX_Fireball": billow_flipbook(Noise(SEED + 1), grow=(.28, .74), warp=.26, erosion=(.0, .5), heat=1.3, turbulence=1.6, opacity=4.5),
        "T_VFX_Fire": fire_flipbook(Noise(SEED + 2)),
        "T_VFX_Flash": flash_sheet(Noise(SEED + 3), rng),
        "T_VFX_Noise": noise_sheet(Noise(SEED + 4)),
        "T_VFX_Water": water_sheet(Noise(SEED + 6), np.random.default_rng(SEED + 6)),
        "T_VFX_Scraps": scraps_sheet(Noise(SEED + 7), np.random.default_rng(SEED + 7)),
        "T_VFX_Fur": fur_sheet(np.random.default_rng(SEED + 8)),
    }


def save(name, array, mode):
    path = DEST / f"{name}.png"
    if mode == "L":
        image = Image.fromarray(to_u8(array), "L")
    else:
        image = Image.fromarray(to_u8(array[..., :len(mode)]), mode)
    image.save(path, optimize=True)
    return path


def preview(images, folder: Path):
    folder.mkdir(parents=True, exist_ok=True)
    for name, array in images.items():
        if array.ndim == 2:
            panels = [array]
        else:
            panels = [array[..., c] for c in range(array.shape[-1])]
        strip = np.concatenate([np.pad(p, 4, constant_values=.5) for p in panels], axis=1)
        scale = max(1, strip.shape[1] // 2400 + 1)
        Image.fromarray(to_u8(strip[::scale, ::scale]), "L").save(folder / f"{name}_channels.png")
        if array.ndim == 3 and array.shape[-1] == 4 and TEXTURES[name][1]:
            rgb = array[..., :3] * array[..., 3:] + .25 * (1 - array[..., 3:])
            Image.fromarray(to_u8(rgb), "RGB").save(folder / f"{name}_over_grey.png")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--preview", type=Path, help="also write channel contact sheets here")
    args = parser.parse_args()
    DEST.mkdir(parents=True, exist_ok=True)
    images = build()
    files = []
    for name, (mode, srgb, role) in TEXTURES.items():
        path = save(name, images[name], mode)
        data = path.read_bytes()
        files.append({"file": path.relative_to(ROOT).as_posix(), "bytes": len(data),
                      "sha256": hashlib.sha256(data).hexdigest(), "channels": mode, "srgb": srgb,
                      "size": list(Image.open(path).size), "role": role,
                      "unreal_asset": f"/Game/Generated/VFX/Textures/{name}.{name}"})
    manifest = {
        "schema_version": 2,
        "tier": "OWN",
        "name": "SORA Arena particle textures",
        "license": "Project-owned original work (SORA Arena); procedural, no third-party imagery inside",
        "generator": "scripts/art/create_vfx_textures.py",
        "regenerate": "python3 scripts/art/create_vfx_textures.py",
        "seed": SEED,
        "numpy": np.__version__,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "used_by": ["scripts/unreal/create_sora_vfx.py"],
        "files": files,
    }
    (SOURCE / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.preview:
        preview(images, args.preview)
    for entry in files:
        print(f"{entry['file']}  {entry['size'][0]}x{entry['size'][1]}  {entry['sha256'][:12]}")


if __name__ == "__main__":
    main()
