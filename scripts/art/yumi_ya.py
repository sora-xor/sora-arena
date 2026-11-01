"""The ya's yadake shaft (SM_Weapon_18_Ya): its taper and its four nodes.

Pure math, with no Blender. The generator (create_runtime_weapon_yumi.py)
builds the shaft from it, and the host tests test the same profile.

Root's review of the first lit first-person originals (Saved/YumiFP/v2) found
the arrow uniformly yellow and plastic-looking. Its four nodes were evenly
placed and identical, and its material was lacquered (roughness about 0.25)
with no node bands. Here each node is placed, raised and shaped a little
differently, as a culm's nodes are. The generator gives the material the
nodes' own positions, browning and a polished, unlacquered roughness
(create_runtime_weapon_lib.mat_bamboo).
"""
from __future__ import annotations

import math

L_YA = 0.98                                   # nock to tip, m
YA_NODES_M = (0.085, 0.36, 0.63, 0.905)       # nominal nodes (fushi) from the nock: four, as kyudo arrows have them
NODE_PLACE_M = 0.012                          # each node within this of its nominal place
NODE_BULGE_M = (0.00030, 0.00050)             # its ridge's height
NODE_WIDTH_M = (0.0018, 0.0026)               # its ridge's width (Gaussian sigma)
SEED = 18


def hash01(*k):
    """The generator's hash (create_runtime_weapon_yumi.hash01), in [0, 1)."""
    h = 0
    for v in k:
        h = (h * 1000003) ^ (int(v) & 0xFFFFFFFF)
        h = ((h ^ (h >> 13)) * 0x5BD1E995) & 0xFFFFFFFF
    h ^= h >> 15
    return (h & 0xFFFFFF) / float(0x1000000)


def jit(*k):
    return hash01(*k) * 2.0 - 1.0


def r_shaft(x):
    """The shaft's radius at x from the nock, before its nodes: barrelled to 4.6 mm mid-length."""
    u = x / L_YA
    return 0.0041 + 0.0005 * math.sin(math.pi * min(max(u, 0), 1)) ** 0.8


def ya_nodes():
    """[(position from the nock, bulge, width)] for the four nodes."""
    (b0, b1), (w0, w1) = NODE_BULGE_M, NODE_WIDTH_M
    out = []
    for k, x in enumerate(YA_NODES_M):
        out.append((x + NODE_PLACE_M * jit(SEED, k, 1),
                    (b0 + b1) / 2 + (b1 - b0) / 2 * jit(SEED, k, 2),
                    (w0 + w1) / 2 + (w1 - w0) / 2 * jit(SEED, k, 3)))
    return out


def node_bulge(x, nodes):
    """The extra radius at x from the nodes: each ridge sharper on its nock side, softer toward the point."""
    r = 0.0
    for xn, amp, sig in nodes:
        w = sig * (0.75 if x < xn else 1.3)
        r += amp * math.exp(-((x - xn) / w) ** 2)
    return r


FINE_M, MID_M = 0.008, 0.015      # a node's fine and middle zones, either side


def stations(nodes, x_start=0.018, x_end=L_YA - 0.05):
    """The shaft's section stations from the nock: 1.5 mm within FINE_M of a
    node (the ridge is about 2 mm wide), 4 mm within MID_M, 20 mm elsewhere.
    A step never runs past the edge of a zone ahead, or a 20 mm step could
    jump a node's whole approach (the generator's first loop did)."""
    centres = sorted(xn for xn, _a, _s in nodes)
    xs = []
    x = x_start
    while x < x_end:
        xs.append(x)
        near = min(abs(x - xn) for xn in centres)
        step = 0.0015 if near < FINE_M else 0.004 if near < MID_M else 0.02
        for xn in centres:
            for edge in (xn - MID_M, xn - FINE_M):
                if x + 0.0005 < edge < x + step:
                    step = edge - x
        x += step
    return xs
