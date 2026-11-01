"""The third-person grip contract's math (docs/art-direction/THIRD_PERSON_GRIP_CONTRACT.md): numpy only, so the
Blender rig script (rig_nyaakoto_runtime.py), the import and the CPU tests share one implementation.

Frames:
- **Blender** world metres: +X forward, +Y the character's left, +Z up. This is the hero source and the rig.
- **Unreal** component cm: +X forward, +Y the character's right, +Z up. Unreal = 100 x (x, -y, z) of Blender for
  these (-Y forward, Z up) FBXs; a direction maps as (x, -y, z).

Sides are anatomical: "R" is the character's right (Blender -Y, Unreal +Y).
"""
from __future__ import annotations

import math

import numpy as np

# The authored W00 katana (Content/SourceArt/Weapons/Runtime/W00_Katana/build_record.json; its FBX's sockets read back
# in Saved/W18Rebuild/s60_grip_contract/arms_weapons_measure.json), in Unreal cm from Grip_R.
W00 = {"grip_l": (-14.242, 0.0, 0.0), "muzzle": (81.973, 0.0, 7.59), "machi_x": 9.52, "kashira_x": -18.99,
       "fuchi_x": 5.5, "tsuka_section_cm": (3.12, 4.05),
       # Sheathed, the saya's Koiguchi meets the front seppa's face: the machi less the 3.2 cm habaki
       # (create_runtime_weapon_nihonto.py: build_saya(..., x_m - Lh, ...)). The rig build measures it from the mesh.
       "sheath_seat_x": 6.32}
# The paw's grip channel: W00's tsuka oval with 0.1 cm clearance (across, deep), and the paw's breadth along it.
CHANNEL_CM = (3.3, 4.3)
PAW_BREADTH_MAX_CM = 11.0
# The contract's stances (section 4.5): the left paw's grip (Grip_L) in Unreal mesh cm, and the blade's elevation.
STANCES = {"guard": {"grip_l": (24.0, 0.0, 100.0), "elevation_deg": 30.0},
           "raise": {"grip_l": (30.0, 0.0, 128.0), "elevation_deg": 80.0},
           "hit": {"grip_l": (22.0, 0.0, 108.0), "elevation_deg": -5.0}}
REACH_MAX = 0.98                       # a solved arm reaches at most this share of its length (no locked elbow)


def ue_to_blender_point(p_cm):
    p = np.asarray(p_cm, np.float64)
    return np.array([p[0], -p[1], p[2]]) / 100.0


def blender_to_ue_point(p_m):
    p = np.asarray(p_m, np.float64)
    return np.array([p[0], -p[1], p[2]]) * 100.0


def flip_y(v):
    v = np.asarray(v, np.float64)
    return np.array([v[0], -v[1], v[2]])


def unit(v):
    v = np.asarray(v, np.float64)
    n = np.linalg.norm(v)
    if n < 1e-12:
        raise ValueError("zero vector")
    return v / n


def frame(x, z):
    """A rotation (columns X, Y, Z) from X and an approximate Z (Z is made orthogonal to X; Y = Z x X)."""
    x = unit(x)
    z = unit(np.asarray(z, np.float64) - np.dot(z, x) * x)
    return np.stack([x, np.cross(z, x), z], 1)


def blade_axes(elevation_deg, yaw_deg=0.0):
    """The katana's +X (toward the kissaki) and +Z (the mune side, in the vertical plane through +X), in Unreal axes.
    Elevation is above horizontal; yaw turns the blade about the vertical, positive toward +Y (the character's
    right)."""
    e, y = math.radians(elevation_deg), math.radians(yaw_deg)
    return (np.array([math.cos(e) * math.cos(y), math.cos(e) * math.sin(y), math.sin(e)]),
            np.array([-math.sin(e) * math.cos(y), -math.sin(e) * math.sin(y), math.cos(e)]))


def frotator_rows(pitch, yaw, roll):
    """UE FRotationMatrix rows, the rotated X, Y and Z axes in Unreal axes (check_viewmodel_framing.rotation)."""
    sp, cp = math.sin(math.radians(pitch)), math.cos(math.radians(pitch))
    sy, cy = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
    sr, cr = math.sin(math.radians(roll)), math.cos(math.radians(roll))
    return np.array([[cp * cy, cp * sy, sp],
                     [sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp],
                     [-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp]])


def gear_socket_blender(entry):
    """A viewmodels.json hero_gear socket (bind_component_cm; rotation_deg as pitch, yaw, roll) as a Blender
    position (m) and rotation (columns X, Y, Z). The X and Z directions keep their meaning; Y = Z x X in Blender."""
    rows = frotator_rows(*entry["rotation_deg"])
    return ue_to_blender_point(entry["bind_component_cm"]), frame(flip_y(rows[0]), flip_y(rows[2]))


def socket_targets(stance, breath=0.0):
    """Blender positions (m) and rotations for the grip sockets a stance uses.
    - Two paws ("grip_l" given): the right paw on Grip_R and the left on Grip_L.
    - One paw ("grip_r" given): the right paw on Grip_R. The left paw goes to "left_paw" if given: its grip socket at
      that Unreal point, the paw upright. Otherwise it stays at rest.
    breath lifts the grips by that many metres."""
    x, z = blade_axes(stance["elevation_deg"], stance.get("yaw_deg", 0.0))
    rot = frame(flip_y(x), flip_y(z))
    lift = np.array([0.0, 0.0, breath * 100.0])
    if "grip_r" in stance:
        out = {"R": (ue_to_blender_point(np.asarray(stance["grip_r"], np.float64) + lift), rot)}
        if "left_paw" in stance:
            out["L"] = (ue_to_blender_point(np.asarray(stance["left_paw"], np.float64) + lift),
                        frame(np.array([0.0, -1.0, 0.0]), np.array([0.0, 0.0, 1.0])))
        return out
    gl = np.asarray(stance["grip_l"], np.float64) + lift
    gr = gl - W00["grip_l"][0] * x
    return {"R": (ue_to_blender_point(gr), rot), "L": (ue_to_blender_point(gl), rot)}


def stance_targets(name, scale=1.0):
    """Unreal mesh cm: Grip_R and Grip_L positions, the blade's X and Z, the kissaki, for a contract stance."""
    s = STANCES[name]
    x, z = blade_axes(s["elevation_deg"])
    gl = np.asarray(s["grip_l"], np.float64) * scale
    gr = gl - np.asarray(W00["grip_l"])[0] * x * scale
    m = np.asarray(W00["muzzle"])
    kissaki = gr + (m[0] * x + m[2] * z) * scale
    return {"grip_r": gr, "grip_l": gl, "x": x, "z": z, "kissaki": kissaki}


def ease(x):
    """Smoothstep on [0, 1]: a key is reached, and left, at rest."""
    x = min(1.0, max(0.0, float(x)))
    return x * x * (3.0 - 2.0 * x)


def keyed_stance(keys, times, u):
    """The stance at normalised time u between keyed two-paw stances (Grip_L, the elevation, and the elbow poles when
    every key has them), eased in and out of each key. A_NyaagyuSamurai_StrikeMakko is keyed so (contract 4.5)."""
    if not 0.0 <= u <= 1.0 or len(keys) != len(times) or times[0] != 0.0 or times[-1] != 1.0:
        raise ValueError(f"keyed_stance: u {u}, {len(keys)} keys at {times}")
    i = len(times) - 2 if u >= 1.0 else max(k for k in range(len(times) - 1) if times[k] <= u)
    f = ease((u - times[i]) / (times[i + 1] - times[i]))
    a, b = keys[i], keys[i + 1]
    out = {"grip_l": tuple((1.0 - f) * np.asarray(a["grip_l"], np.float64) + f * np.asarray(b["grip_l"], np.float64)),
           "elevation_deg": (1.0 - f) * a["elevation_deg"] + f * b["elevation_deg"]}
    if all(k.get("poles") for k in (a, b)):
        out["poles"] = {s: tuple(unit((1.0 - f) * np.asarray(a["poles"][s], np.float64) + f * np.asarray(b["poles"][s], np.float64)))
                        for s in ("R", "L")}
    return out


def two_bone(shoulder, wrist, a, b, pole):
    """The elbow for a two-bone chain from shoulder to wrist (lengths a, b), bending toward pole. ValueError when the
    wrist is out of reach (beyond REACH_MAX of a + b) or too close (|a - b|)."""
    s, w = np.asarray(shoulder, np.float64), np.asarray(wrist, np.float64)
    d = np.linalg.norm(w - s)
    if d > REACH_MAX * (a + b):
        raise ValueError(f"out of reach: {d:.4f} m against {a + b:.4f} m (at most {REACH_MAX:.0%})")
    if d < abs(a - b) + 1e-6:
        raise ValueError(f"too close: {d:.4f} m against |a - b| = {abs(a - b):.4f} m")
    u = (w - s) / d
    v = np.asarray(pole, np.float64) - np.dot(pole, u) * u
    v = unit(v)
    cos_a = (a * a + d * d - b * b) / (2 * a * d)
    alpha = math.acos(max(-1.0, min(1.0, cos_a)))
    return s + a * (math.cos(alpha) * u + math.sin(alpha) * v)


def hand_pose(socket_bind_pos, socket_bind_rot, wrist_bind, target_pos, target_rot):
    """The hand bone's pose: its rotation R (applied to the bind) and the wrist's position, so that the socket (rigid
    on the hand) lands on the target. Positions in one frame; rotations as 3x3 column frames."""
    R = np.asarray(target_rot) @ np.asarray(socket_bind_rot).T
    wrist = np.asarray(target_pos) - R @ (np.asarray(socket_bind_pos) - np.asarray(wrist_bind))
    return R, wrist


def segment_distance(p0, p1, points):
    """Each point's distance from the segment p0-p1."""
    p0, p1 = np.asarray(p0, np.float64), np.asarray(p1, np.float64)
    q = np.atleast_2d(np.asarray(points, np.float64))
    d = p1 - p0
    t = np.clip(((q - p0) @ d) / max(d @ d, 1e-12), 0.0, 1.0)
    return np.linalg.norm(q - (p0 + t[:, None] * d), axis=1)


def angle_deg(r1, r2):
    """The angle of the rotation taking frame r1 to r2."""
    c = (np.trace(np.asarray(r1).T @ np.asarray(r2)) - 1.0) / 2.0
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))
