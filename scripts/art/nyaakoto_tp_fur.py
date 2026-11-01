"""Opaque fur strands on Nyaakoto's third-person paws (nyaakoto_tp_paws), within the 23-slot material contract.

Root's 07:12 UTC review of s97 (2026-10-26): the paws read as smooth grey rounded digits, with no resolved short fur
and no furry silhouette. The paw's own surface stays the closed, gated skin. This adds what the hero's head already
has (create_nyaagyu_hero_character.surface_fur_cards): single tapered triangles of M_Hero_GreyTabbyFur rooted on the
skin. Each leans along the coat's flow, so the outline breaks into short fur.

**Two coats:** a dense short undercoat, and sparse longer guard hairs that carry the silhouette (GUARD).

**The flow** is along the toes from the knuckles to the tips, and down the back of the paw toward the knuckles. The
two blend by the digit weight. The thumb's fur runs the other way round the channel, as the thumb does.

**Where strands grow:** they are sampled by area with a fixed seed. None grows within clear_m of the grip channel,
where the paw meets the tsuka. A strand is kept only if:
- its tip is outside the skin, fuzz included;
- its tip is clear of the channel by tip_clear_m;
- its tip is within the paw's 11 cm breadth along the channel (the rig's gate);
- it crosses the skin in neither the grip nor the empty fist (grow prunes it otherwise).
Strands may cross each other, as hairs do.

**The empty fist:** the strands are vertices of the paw part, so nyaakoto_tp_paws.empty_points (a rule of position)
moves them with the skin.

**CoatBlend and UV** are the skin's at each root.

**Shading:** each strand takes its root's skin normal (the builders set it as the strand vertices' custom normal), so
it shades as the coat beneath it does. Its own face normal lit it as a dark line or a bright bristle across the coat:
root's 14:38 UTC review of s116 (2026-10-26) saw "sparse stubble with a bright bristled fringe". For the same
reason, r3's strands lie flatter and shorter than s115/s116's (16-30 deg, 3.5-7 mm; the guard hairs 22-36 deg,
7-10 mm).
"""
from __future__ import annotations

import math

import numpy as np

import nyaakoto_tp_paws as TPP

# clear_m: no root this near the grip channel. 6 mm (s115-s121) left a bald white band between the fur and the pads
# (nyaakoto_tp_paws.pad_faces, within 4 mm); 4.5 mm lets the fur reach the pads, and tip_clear_m still keeps every tip
# 2 mm off the channel.
STRANDS = {"density_per_cm2": 8.0, "length_m": (0.0028, 0.0055), "root_width_m": (0.00030, 0.00055),
           "lift_deg": (8.0, 18.0), "root_lift_m": 0.0001, "clear_m": 0.0045, "tip_clear_m": 0.002}
GUARD = dict(STRANDS, density_per_cm2=0.7, length_m=(0.0055, 0.0080), root_width_m=(0.00022, 0.00036),
             lift_deg=(12.0, 24.0), clear_m=0.006)
LOD_DENSITY = (1.0, 0.35, 0.0)          # LOD0, LOD1, LOD2: a share of STRANDS["density_per_cm2"]
# m: a kept strand's tip clears the fuzzed skin by this much. 0.5 mm (to s122) pruned a quarter of r3's flatter,
# shorter strands (5.2k a paw in s116, 3.9k in s120-s122); grow's exact skin-crossing prune still removes any
# strand that crosses the skin.
TIP_ABOVE_FUZZ_M = 0.0001


def _unit(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def flow(points, normals, skel):
    """The coat's direction at each point, in the skin's tangent plane (unit)."""
    fr = skel["frame"]
    s, t, e = TPP.channel_coords(points, fr)
    tu, tv = -fr["a"] * np.sin(t), fr["b"] * np.cos(t)                 # the oval's tangent, increasing t
    along = _unit(tu[:, None] * fr["z"] + tv[:, None] * fr["w"])
    thumb = TPP._chain(points, skel["thumb"])
    digits = np.minimum.reduce([TPP._chain(points, c) for c in skel["digits"]])
    along = np.where((thumb < digits)[:, None], -along, along)          # the thumb wraps the other way
    palm = np.broadcast_to(-fr["z"], points.shape)                      # down the back toward the knuckles
    w = TPP.digit_weight(points, skel)[:, None]
    d = w * along + (1.0 - w) * palm
    d = d - (d * normals).sum(1, keepdims=True) * normals
    return _unit(d)


def strands(verts, tris, uvs, coat, skel, density_share=1.0, seed=11, cfg=STRANDS):
    """Fur strands on a mesh_paw skin: (strand verts (3 per strand), tris, per-corner UVs, per-corner CoatBlend, and
    per-vertex normals, each its root's skin normal)."""
    if density_share <= 0.0:
        return np.zeros((0, 3)), np.zeros((0, 3), np.int64), np.zeros((0, 3, 2)), np.zeros((0, 3)), np.zeros((0, 3))
    rng = np.random.default_rng(seed)
    a, b, c = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    cross = np.cross(b - a, c - a)
    area = 0.5 * np.linalg.norm(cross, axis=1)
    count = int(round(area.sum() * 1e4 * cfg["density_per_cm2"] * density_share))
    pick = rng.choice(len(tris), size=count, p=area / area.sum())
    u, v = rng.random(count), rng.random(count)
    flip = u + v > 1.0
    u, v = np.where(flip, 1.0 - u, u), np.where(flip, 1.0 - v, v)
    n = _unit(cross[pick])
    root = a[pick] + (b[pick] - a[pick]) * u[:, None] + (c[pick] - a[pick]) * v[:, None] + cfg["root_lift_m"] * n
    d = flow(root, n, skel)
    lift = np.radians(rng.uniform(*cfg["lift_deg"], count))
    growth = _unit(np.cos(lift)[:, None] * d + np.sin(lift)[:, None] * n)
    length = rng.uniform(*cfg["length_m"], count)
    half = 0.5 * rng.uniform(*cfg["root_width_m"], count)
    side = _unit(np.cross(n, growth))
    tip = root + length[:, None] * growth
    fr = skel["frame"]
    keep = ((TPP.channel_sdf(root, fr) > cfg["clear_m"]) & (TPP.channel_sdf(tip, fr) > cfg["tip_clear_m"])
            & (TPP.paw_sdf(tip, skel) > TPP.FUZZ_MAX + TIP_ABOVE_FUZZ_M)
            & (np.abs((tip - fr["c"]) @ TPP.Y) < TPP.PAW_HALF - 0.0003))      # the rig's 11 cm breadth gate
    root, tip, side, half, n = root[keep], tip[keep], side[keep], half[keep], n[keep]
    # Wound so each strand's face looks outward with its root's normal: side x growth is about -n for a strand lying
    # this flat, so the corners go root + side, root - side, tip. s115-s120 wound them the other way: every face
    # looked into the skin (face . root normal about -0.97), so Cycles shaded them as backfaces (root's "dark lines")
    # and a one-sided Unreal material would cull them.
    sv = np.stack([root + half[:, None] * side, root - half[:, None] * side, tip], 1).reshape(-1, 3)
    st = np.arange(len(sv)).reshape(-1, 3)
    bary_uv = (uvs[pick, 0] * (1.0 - u - v)[:, None] + uvs[pick, 1] * u[:, None] + uvs[pick, 2] * v[:, None])[keep]
    bary_coat = (coat[pick, 0] * (1.0 - u - v) + coat[pick, 1] * u + coat[pick, 2] * v)[keep]
    return (sv, st, np.repeat(bary_uv[:, None, :], 3, 1), np.repeat(bary_coat[:, None], 3, 1),
            np.repeat(n[:, None, :], 3, 1).reshape(-1, 3))


def skin_crossing_strands(skin_v, skin_t, sv, st):
    """The strands (indices) whose triangle crosses the skin. Strands may cross each other, as hairs do."""
    V = np.concatenate([skin_v, sv])
    T = np.concatenate([skin_t, st + len(skin_v)])
    pairs = TPP.self_crossings(V, T)
    n = len(skin_t)
    mixed = pairs[(pairs[:, 0] < n) != (pairs[:, 1] < n)]
    return np.unique(np.where(mixed[:, 0] >= n, mixed[:, 0], mixed[:, 1]) - n)


def grow(m, density_share=1.0, seed=11, coats=(STRANDS, GUARD)):
    """Strands for a mesh_paw result, both coats (each its own seed), pruned of every strand that crosses the skin in
    the grip or the empty fist: (verts, tris, corner UVs, corner CoatBlend, how many were pruned). Their vertex
    normals, each its root's skin normal, are m["strand_normals"] afterwards."""
    grown = [strands(m["verts"], m["tris"], m["uvs"], m["coat"], m["skeleton"], density_share, seed + k, cfg)
             for k, cfg in enumerate(coats)]
    sv = np.concatenate([g[0] for g in grown])
    st = np.arange(len(sv)).reshape(-1, 3)
    suv = np.concatenate([g[2] for g in grown])
    scoat = np.concatenate([g[3] for g in grown])
    sn = np.concatenate([g[4] for g in grown])
    m["strand_normals"] = sn
    if not len(st):
        return sv, st, suv, scoat, 0
    bad = set()
    for state in ("grip", "empty"):
        sk = m["verts"] if state == "grip" else TPP.empty_points(m["verts"], m["skeleton"])
        sx = sv if state == "grip" else TPP.empty_points(sv, m["skeleton"])
        bad |= set(skin_crossing_strands(sk, m["tris"], sx, st).tolist())
    keep = np.setdiff1d(np.arange(len(st)), np.array(sorted(bad), np.int64))
    sv = sv.reshape(-1, 3, 3)[keep].reshape(-1, 3)
    m["strand_normals"] = sn.reshape(-1, 3, 3)[keep].reshape(-1, 3)
    return sv, np.arange(len(sv)).reshape(-1, 3), suv[keep], scoat[keep], len(bad)
