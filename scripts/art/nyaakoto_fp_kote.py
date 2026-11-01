"""The bow arm's kote for Nyaakoto's first-person paw, in numpy.

The paw module (nyaakoto_fp_paws.py) gives the skeleton. This builds the
armour over its forearm, in the same frame (Grip_L, bow metres), following
the reference plate (docs/art-direction/Nyaakoto_Photoreal_Target.png).

- **The sleeve:** an indigo cloth sleeve from a rolled cuff at the wrist
  back past the near plane toward the elbow. It is a closed tube with real
  thickness and compression folds.
- **Shino splints:** lacquered indigo-black, sewn lengthwise on the outer
  side of the forearm, each a thick strip with rounded ends.
- **The cords:** vermilion two-ply silk cord bound round sleeve and splints
  at the cuff and along the arm.
- **The tekko:** a small lacquered plate over the back of the wrist. The
  Blender driver inlays the pinned SORA mon (SM_SoraKamon) at
  tekko()["mon"].

Every piece is (verts, tris, uv) with a material name. The Blender driver
turns them into objects.
"""
from __future__ import annotations

import math

import numpy as np

import nyaakoto_fp_paws as P

KOTE = {
    "cuff_s": -0.016,          # the cuff's edge, metres from the carpus along the forearm (negative: toward the elbow)
    "end_s": -0.300,           # past the near plane at every hold
    "radius": (0.0300, 0.0380),  # sleeve outer radius at the cuff and at the end
    "ellipse": 0.07,           # flattened across the forearm's breadth
    "thickness": 0.0012,
    "folds": {"count": 9, "depth": 0.0011, "twist": 2.6, "ripple_m": 0.026},
    # v5 (root's reviews of capture v5 and the v4 originals: "smooth sleeve", "glossy sleeve"). One regular
    # nine-lobed corrugation read as a smooth tube. A second family of other count, twist and ripple, with its own
    # slow swell, breaks the pattern. The cloth puffs between its cord bindings, tight at each cord and held flat
    # under the splints.
    "folds2": {"count": 5, "depth": 0.0008, "twist": 4.1, "ripple_m": 0.041, "phase": 1.3, "swell_m": 0.057},
    "puff": {"depth": 0.0012, "beyond": 0.7, "beyond_m": 0.02},
    "hem_r": 0.0019,
    "splints": {"count": 7, "span_deg": 196.0, "centre_deg": 72.0, "width": 0.0112, "thick": 0.0016,
                "from_s": -0.024, "to_s": -0.185, "lift": 0.0006},
    "cords": {"at_s": (-0.021, -0.063, -0.112, -0.163), "radius": 0.0011, "ply": 2, "pitch": 0.0062},
    "tekko": {"size": (0.034, 0.030), "thick": 0.0015, "corner": 0.006, "mon_d": 0.020, "centre_s": -0.046},
}


def forearm_frame(skel):
    """Origin at the carpus. a points toward the elbow; u is the forearm's
    outer (dorsal) side, away from the grip and up; v completes a right-handed set."""
    a = P.FOREARM_DIR / np.linalg.norm(P.FOREARM_DIR)
    out = np.array((0.0, 0.55, 0.85))                       # up and to the wielder's left: the arm's outer side
    u = out - a * (out @ a)
    u /= np.linalg.norm(u)
    v = np.cross(a, u)
    return skel["wrist"], a, u, v


def _grid_tris(rows, cols, closed_cols=True, flip=False):
    """Quads of a rows x cols vertex grid, columns wrapping when closed_cols."""
    tris = []
    cmax = cols if closed_cols else cols - 1
    for i in range(rows - 1):
        for j in range(cmax):
            a = i * cols + j
            b = i * cols + (j + 1) % cols
            c = (i + 1) * cols + (j + 1) % cols
            d = (i + 1) * cols + j
            tris += [(a, b, c), (a, c, d)] if not flip else [(a, c, b), (a, d, c)]
    return np.array(tris, np.int64)


def puff(s, theta, cfg=KOTE):
    """How far the cloth puffs between its cord bindings (v5): a swell in each span between two cords, zero at each
    cord, easing up past the last cord toward the elbow, and none under the splints, which hold it flat."""
    p, cords = cfg["puff"], sorted(cfg["cords"]["at_s"], reverse=True)          # the cuff's end first
    s = np.asarray(s, np.float64)
    out = np.zeros(np.broadcast(s, theta).shape)
    for c0, c1 in zip(cords[:-1], cords[1:]):
        x = (s - c0) / (c1 - c0)
        inside = (x > 0) & (x < 1)
        out = np.where(inside, p["depth"] * np.sin(math.pi * np.clip(x, 0, 1)) ** 1.5, out)
    past = s < cords[-1]
    out = np.where(past, p["depth"] * p["beyond"] * (1 - np.exp(-(cords[-1] - s) / p["beyond_m"])), out)
    return out * (1.0 - splint_arc(theta, cfg))


def sleeve_radius(s, theta, cfg=KOTE):
    """The sleeve's outer radius at s (metres from the carpus, negative toward the elbow) and theta."""
    r0, r1 = cfg["radius"]
    w = np.clip((s - cfg["cuff_s"]) / (cfg["end_s"] - cfg["cuff_s"]), 0.0, 1.0)
    base = r0 + (r1 - r0) * w ** 0.8
    f = cfg["folds"]
    fold = f["depth"] * np.sin(f["count"] * theta + f["twist"] * np.sin(2 * math.pi * s / f["ripple_m"]))
    fold *= 0.55 + 0.45 * np.sin(2 * math.pi * s / (f["ripple_m"] * 1.7)) ** 2
    g = cfg["folds2"]
    fold2 = g["depth"] * np.sin(g["count"] * theta + g["phase"] + g["twist"] * np.sin(2 * math.pi * s / g["ripple_m"]))
    fold2 *= 0.6 + 0.4 * np.sin(2 * math.pi * s / g["swell_m"] + 2 * theta)
    return base * (1.0 + cfg["ellipse"] * np.cos(2 * theta)) + fold + fold2 + puff(s, theta, cfg)


def sleeve(skel, cfg=KOTE, n_s=140, n_t=96):
    """The cloth sleeve: outer and inner surfaces joined at both ends."""
    o, a, u, v = forearm_frame(skel)
    s = np.linspace(cfg["cuff_s"], cfg["end_s"], n_s)
    th = np.linspace(0.0, 2 * math.pi, n_t, endpoint=False)
    S, TH = np.meshgrid(s, th, indexing="ij")
    R = sleeve_radius(S, TH, cfg)
    outer = o + a * (-S)[..., None] + R[..., None] * (np.cos(TH)[..., None] * u + np.sin(TH)[..., None] * v)
    inner = o + a * (-S)[..., None] + (R - cfg["thickness"])[..., None] * (np.cos(TH)[..., None] * u +
                                                                          np.sin(TH)[..., None] * v)
    V = np.concatenate([outer.reshape(-1, 3), inner.reshape(-1, 3)])
    t_out = _grid_tris(n_s, n_t, flip=True)
    t_in = _grid_tris(n_s, n_t) + n_s * n_t
    rims = []
    for row in (0, n_s - 1):
        for j in range(n_t):
            j1 = (j + 1) % n_t
            a0, b0 = row * n_t + j, row * n_t + j1
            a1, b1 = a0 + n_s * n_t, b0 + n_s * n_t
            rims += [(a0, b0, b1), (a0, b1, a1)] if row == 0 else [(a0, b1, b0), (a0, a1, b1)]
    T = np.concatenate([t_out, t_in, np.array(rims)])
    circ = 2 * math.pi * cfg["radius"][0]
    uv_o = np.stack([TH / (2 * math.pi), (S - cfg["cuff_s"]) / -circ], -1).reshape(-1, 2)
    UV = np.concatenate([uv_o, uv_o])
    return {"name": "Kote_Sleeve", "material": "M_NyaakotoFP_KoteSilk", "verts": V, "tris": T, "uv": UV}


def cuff_hem(skel, cfg=KOTE, n_t=96, n_c=12):
    """The rolled hem at the cuff: a torus round the sleeve's edge."""
    o, a, u, v = forearm_frame(skel)
    s0 = cfg["cuff_s"]
    th = np.linspace(0.0, 2 * math.pi, n_t, endpoint=False)
    ph = np.linspace(0.0, 2 * math.pi, n_c, endpoint=False)
    TH, PH = np.meshgrid(th, ph, indexing="ij")
    R = sleeve_radius(np.full_like(TH, s0), TH, cfg) - cfg["thickness"] * 0.5
    radial = np.cos(TH)[..., None] * u + np.sin(TH)[..., None] * v
    c = o + a * (-s0) + R[..., None] * radial
    hr = cfg["hem_r"]
    p = c + hr * (np.cos(PH)[..., None] * radial + np.sin(PH)[..., None] * (-a))
    V = p.reshape(-1, 3)
    T = _grid_tris(n_t, n_c)
    rows = []
    for i in range(n_t):
        for j in range(n_c):
            a0 = i * n_c + j
            b0 = i * n_c + (j + 1) % n_c
            a1 = ((i + 1) % n_t) * n_c + j
            b1 = ((i + 1) % n_t) * n_c + (j + 1) % n_c
            rows += [(a0, a1, b1), (a0, b1, b0)]
    UV = np.stack([TH / (2 * math.pi) * 6, PH / (2 * math.pi)], -1).reshape(-1, 2)
    return {"name": "Kote_CuffHem", "material": "M_NyaakotoFP_KoteSilk", "verts": V, "tris": np.array(rows), "uv": UV}


def splint_base_r(s, theta, cfg=KOTE):
    """The radius the splints sit at, angle by angle: the sleeve's elliptical
    section plus its fold crests and the splints' lift, so they lie on the
    cloth all the way round instead of standing off it at the narrow sides. Both fold families' crests count (v5);
    the cloth does not puff under the splints (puff)."""
    sp = cfg["splints"]
    w = np.clip((s - cfg["cuff_s"]) / (cfg["end_s"] - cfg["cuff_s"]), 0, 1) ** 0.8
    return (cfg["radius"][0] + (cfg["radius"][1] - cfg["radius"][0]) * w) * (1 + cfg["ellipse"] * np.cos(2 * theta)) + \
        cfg["folds"]["depth"] + cfg["folds2"]["depth"] + sp["lift"]


def splint_arc(theta, cfg=KOTE, ramp_deg=9.0):
    """1 over the splints' angular span, 0 off it, ramped at the edges."""
    sp = cfg["splints"]
    c = math.radians(sp["centre_deg"])
    half = math.radians(sp["span_deg"]) * 0.5 + sp["width"] / cfg["radius"][0] * 0.5
    d = np.abs((theta - c + math.pi) % (2 * math.pi) - math.pi)
    return np.clip((half + math.radians(ramp_deg) - d) / math.radians(ramp_deg), 0.0, 1.0)


def splints(skel, cfg=KOTE, n_s=60, n_w=10):
    """Shino splints: thick strips on the sleeve's outer side, rounded at both ends."""
    o, a, u, v = forearm_frame(skel)
    sp = cfg["splints"]
    out = []
    centres = np.radians(sp["centre_deg"]) + np.radians(sp["span_deg"]) * (np.arange(sp["count"]) /
                                                                            (sp["count"] - 1) - 0.5)
    for k, c_th in enumerate(centres):
        s = np.linspace(sp["from_s"], sp["to_s"], n_s)
        L = abs(sp["to_s"] - sp["from_s"])
        hw = sp["width"] * 0.5 * (0.88 + 0.12 * (s - sp["from_s"]) / (sp["to_s"] - sp["from_s"]))
        # semicircular ends: the half-width shrinks over the last half-width of length
        d_end = np.minimum(np.abs(s - sp["from_s"]), np.abs(s - sp["to_s"]))
        end = np.clip(d_end / hw, 0.0, 1.0)
        hw_s = hw * np.sqrt(np.maximum(1.0 - (1.0 - end) ** 2, 0.0))
        hw_s = np.maximum(hw_s, 1e-5)
        w = np.linspace(-1.0, 1.0, n_w)
        S, W = np.meshgrid(s, w, indexing="ij")
        base_r = splint_base_r(S, np.full_like(S, c_th), cfg)
        th = c_th + W * hw_s[:, None] / base_r
        base_r = splint_base_r(S, th, cfg)
        dome = 0.00035 * (1.0 - W ** 2)                       # a slight crown across each splint
        bot = o + a * (-S)[..., None] + base_r[..., None] * (np.cos(th)[..., None] * u + np.sin(th)[..., None] * v)
        top = o + a * (-S)[..., None] + (base_r + sp["thick"] + dome)[..., None] * (
            np.cos(th)[..., None] * u + np.sin(th)[..., None] * v)
        V = np.concatenate([top.reshape(-1, 3), bot.reshape(-1, 3)])
        t_top = _grid_tris(n_s, n_w, closed_cols=False, flip=True)
        t_bot = _grid_tris(n_s, n_w, closed_cols=False) + n_s * n_w
        side = []
        for i in range(n_s - 1):                               # the two long edges
            for j in (0, n_w - 1):
                a0, a1 = i * n_w + j, (i + 1) * n_w + j
                b0, b1 = a0 + n_s * n_w, a1 + n_s * n_w
                side += [(a0, b1, a1), (a0, b0, b1)] if j == 0 else [(a0, a1, b1), (a0, b1, b0)]
        for i in (0, n_s - 1):                                 # the (pinched) end rows
            for j in range(n_w - 1):
                a0, a1 = i * n_w + j, i * n_w + j + 1
                b0, b1 = a0 + n_s * n_w, a1 + n_s * n_w
                side += [(a0, a1, b1), (a0, b1, b0)] if i == 0 else [(a0, b1, a1), (a0, b0, b1)]
        T = np.concatenate([t_top, t_bot, np.array(side)])
        uv = np.stack([(W + 1) * 0.5 * 0.12 + 0.13 * k, (S - sp["from_s"]) / -L], -1).reshape(-1, 2)
        out.append({"name": f"Kote_Shino_{k + 1:02d}", "material": "M_NyaakotoFP_KoteUrushi", "verts": V, "tris": T,
                    "uv": np.concatenate([uv, uv])})
    return out


def cords(skel, cfg=KOTE, n_t=160, n_c=8):
    """Two-ply cord wraps: each ply a tube on a helix round the wrap's circle."""
    o, a, u, v = forearm_frame(skel)
    cd = cfg["cords"]
    sp = cfg["splints"]
    out = []
    for k, s0 in enumerate(cd["at_s"]):
        over_splints = sp["to_s"] <= s0 <= sp["from_s"] + 0.004
        th = np.linspace(0.0, 2 * math.pi, n_t, endpoint=False)
        # Tight round the cloth, rising only over the splints' arc (with a short ramp at its edges).
        R = sleeve_radius(np.full_like(th, s0), th, cfg) + cd["radius"] * 1.2
        if over_splints:
            on = splint_arc(th, cfg)
            top = splint_base_r(s0, th, cfg) + sp["thick"] + cd["radius"] * 1.2
            R = R * (1 - on) + np.maximum(R, top) * on
        radial = np.cos(th)[:, None] * u + np.sin(th)[:, None] * v
        centre = o + a * (-s0) + R[:, None] * radial
        tangent = np.gradient(centre, axis=0)
        tangent /= np.linalg.norm(tangent, axis=1, keepdims=True)
        side = np.cross(tangent, radial)
        circ = float(np.sum(np.linalg.norm(np.diff(np.vstack([centre, centre[:1]]), axis=0), axis=1)))
        turns = round(circ / cd["pitch"])
        for ply in range(cd["ply"]):
            phase = th * turns + ply * 2 * math.pi / cd["ply"]
            off = 0.55 * cd["radius"] * (np.cos(phase)[:, None] * radial + np.sin(phase)[:, None] * side)
            path = centre + off
            ph = np.linspace(0.0, 2 * math.pi, n_c, endpoint=False)
            rr = 0.62 * cd["radius"]
            ring = path[:, None, :] + rr * (np.cos(ph)[None, :, None] * radial[:, None, :] +
                                            np.sin(ph)[None, :, None] * side[:, None, :])
            V = ring.reshape(-1, 3)
            T = []
            for i in range(n_t):
                for j in range(n_c):
                    a0 = i * n_c + j
                    b0 = i * n_c + (j + 1) % n_c
                    a1 = ((i + 1) % n_t) * n_c + j
                    b1 = ((i + 1) % n_t) * n_c + (j + 1) % n_c
                    T += [(a0, a1, b1), (a0, b1, b0)]
            UVg = np.stack(np.meshgrid(th / (2 * math.pi) * turns, ph / (2 * math.pi), indexing="ij"), -1)
            out.append({"name": f"Kote_Cord_{k + 1}_{ply + 1}", "material": "M_NyaakotoFP_CordVermilion",
                        "verts": V, "tris": np.array(T), "uv": UVg.reshape(-1, 2)})
    return out


def tekko(skel, cfg=KOTE, n=24):
    """The mon plate: a small lacquered plate sewn over the splints on the
    forearm's outer side just behind the cuff, where the first-person view
    sees it. Returns the plate and where the mon sits (centre, outward
    normal, along-arm axis)."""
    o, a, u, v = forearm_frame(skel)
    tk = cfg["tekko"]
    w, h = tk["size"]
    centre_s = tk["centre_s"]                                  # on the splints, just behind the cuff
    r = splint_base_r(centre_s, 0.0, cfg) + cfg["splints"]["thick"] + 0.0003
    x = np.linspace(-1, 1, n)
    X, Y = np.meshgrid(x, x, indexing="ij")
    # rounded rectangle: pull the grid's corners in onto a superellipse outline
    pw = 6.0
    m = np.maximum((np.abs(X) ** pw + np.abs(Y) ** pw) ** (1 / pw), 1e-9)
    sq = np.maximum(np.abs(X), np.abs(Y))
    X2, Y2 = X * sq / m, Y * sq / m
    th = X2 * (w * 0.5) / r
    s = centre_s + Y2 * (h * 0.5)
    dome = 0.0012 * (1 - X2 ** 2) * (1 - 0.5 * Y2 ** 2)
    top = o + a * (-s)[..., None] + (r + tk["thick"] + dome)[..., None] * (np.cos(th)[..., None] * u +
                                                                            np.sin(th)[..., None] * v)
    bot = o + a * (-s)[..., None] + (r + dome * 0.6)[..., None] * (np.cos(th)[..., None] * u +
                                                                    np.sin(th)[..., None] * v)
    V = np.concatenate([top.reshape(-1, 3), bot.reshape(-1, 3)])
    t_top = _grid_tris(n, n, closed_cols=False, flip=True)
    t_bot = _grid_tris(n, n, closed_cols=False) + n * n
    side = []
    border = [(i, 0) for i in range(n - 1)] + [(n - 1, j) for j in range(n - 1)] + \
             [(i, n - 1) for i in range(n - 1, 0, -1)] + [(0, j) for j in range(n - 1, 0, -1)]
    for (i0, j0), (i1, j1) in zip(border, border[1:] + border[:1]):
        a0, a1 = i0 * n + j0, i1 * n + j1
        b0, b1 = a0 + n * n, a1 + n * n
        side += [(a0, b0, b1), (a0, b1, a1)]
    T = np.concatenate([t_top, t_bot, np.array(side)])
    UV = np.stack([(X2 + 1) * 0.5, (Y2 + 1) * 0.5], -1).reshape(-1, 2)
    mon_c = o + a * (-centre_s) + (r + tk["thick"] + 0.0012) * u
    return {"name": "Kote_Tekko", "material": "M_NyaakotoFP_KoteUrushi", "verts": V, "tris": T,
            "uv": np.concatenate([UV, UV]),
            "mon": {"centre": mon_c, "normal": u, "up": -a, "diameter": tk["mon_d"]}}


def outward(part):
    """Wind a closed part so its signed volume is positive (normals out)."""
    V, T = part["verts"], part["tris"]
    vol = np.einsum("ij,ij->i", V[T[:, 0]], np.cross(V[T[:, 1]], V[T[:, 2]])).sum() / 6.0
    if vol < 0:
        part["tris"] = T[:, ::-1].copy()
    return part


def bow_kote(skel, cfg=KOTE):
    """Every piece of the bow arm's kote, each closed and wound outward."""
    parts = [sleeve(skel, cfg), cuff_hem(skel, cfg)]
    parts += splints(skel, cfg)
    parts += cords(skel, cfg)
    t = tekko(skel, cfg)
    parts.append(t)
    return [outward(p) for p in parts], t["mon"]
