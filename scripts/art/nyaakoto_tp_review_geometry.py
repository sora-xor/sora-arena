"""The third-person paw review's shots and cameras (render_nyaakoto_tp_review.py), in plain Python.

Unreal's bundled Python has no numpy, so what the capture computes lives here, tested on the host
(test_nyaakoto_tp_review_geometry.py):
- **The shots** root asked for (2026-10-26 20:2x UTC): both paws holding and empty, each from its pads and from its
  back; both cuffs; the full guard and strike; every shot's LOD stated (in its name, and read back).
- **A paw's camera** is defined in its grip socket's posed frame (hand_r_grip, hand_l_grip), so it follows the paw as
  the clip poses it. plan_nyaakoto_tp_review.py (numpy, on the host) ranks its directions by how much of the pads or
  the back they see; choose() takes the best-ranked whose sight line clears the posed body.
- **The body** is LOD0's skin as voxels, each moved by its bone's posed transform (the planner voxelises it).

Unreal axes and centimetres throughout: X forward, Y right, Z up; the character at the origin, facing +X.
"""
from __future__ import annotations

import math

# The authored W00 katana's Grip_L from its Grip_R, cm along the blade (third_person_rig.W00["grip_l"]).
W00_GRIP_L_X = -14.242
RESOLUTION = (3840, 2160)
CLOSE_FOV_DEG = 40.0           # horizontal, as Unreal's CameraComponent field_of_view is. 30 (plan attempt 1) put
                               # the paws' 11 cm bounding sphere 81 cm away, farther into the body's way
CUFF_FOV_DEG = 35.0
BODY_FOV_DEG = 30.0
FRAME_MARGIN = 1.10            # the subject's bounding sphere fills the frame's height less this margin
CUFF_HALF_CM = 11.0            # a cuff shot frames this much either side of the wrist, vertically
MIN_CAMERA_Z_CM = 8.0          # cameras stay this far above the floor's top (z = 0)
NEAR_SKIP_CM = 12.0            # the sight line's first stretch from its target: the paw and wrist themselves
CUFF_DISTANCE_CM = None        # derived: CUFF_HALF_CM framed at CUFF_FOV_DEG (cuff_distance)
MORPHS = ("PawEmpty_R", "PawEmpty_L")
SOCKETS = {"R": "hand_r_grip", "L": "hand_l_grip"}
LODS = (0, 1, 2)

# The full-body views: azimuth from +X toward +Y (the character's right), elevation above horizontal, the point looked
# at, and the height the frame must hold.
BODY_VIEWS = {
    "guard_front": {"pose": "guard", "azimuth_deg": 30.0, "elevation_deg": 6.0, "target_cm": (12.0, 0.0, 112.0),
                    "height_cm": 236.0},
    "guard_side": {"pose": "guard", "azimuth_deg": 90.0, "elevation_deg": 4.0, "target_cm": (8.0, 0.0, 112.0),
                   "height_cm": 236.0},
    "strike_raise_front": {"pose": "raise", "azimuth_deg": 30.0, "elevation_deg": 6.0, "target_cm": (8.0, 0.0, 124.0),
                           "height_cm": 260.0},
    "strike_raise_side": {"pose": "raise", "azimuth_deg": 90.0, "elevation_deg": 4.0, "target_cm": (8.0, 0.0, 124.0),
                          "height_cm": 260.0},
    "strike_hit_side": {"pose": "hit", "azimuth_deg": 90.0, "elevation_deg": 4.0, "target_cm": (12.0, 0.0, 112.0),
                        "height_cm": 236.0},
}


def shots():
    """The review's shots, in capture order (grouped so the pose, morphs and LOD change least).

    Each: name (its LOD stated), kind (paw, cuff or body), pose (guard, raise, hit, or rest: the reference pose),
    state (holding: both morphs 0; empty: both 1), lod, and its camera's key. A paw's holding and empty shots share one
    camera, so each pair is a direct comparison and shows the morph took.

    In the guard the pads face into the curl, and the rear paw's best views pass through the body (s131: the left
    pads' clear view saw 36% of them holding, 19% empty). So both paws are also shot in the reference pose ("rest",
    named so), hanging clear of the body, ranked with only their own skin in the way ("_solo" cameras)."""
    out = []
    for pose, suffix, solo in (("guard", "", ""), ("rest", "_rest", "_solo")):
        for state in ("holding", "empty"):
            for side in ("R", "L"):
                for view in ("pads", "back"):
                    out.append({"name": f"paw_{side}_{view}_{state}{suffix}_LOD0", "kind": "paw", "pose": pose,
                                "state": state, "lod": 0, "side": side, "view": view,
                                "camera": f"paw_{side}_{view}{solo}"})
    for side in ("R", "L"):
        for view in ("outside", "below"):
            out.append({"name": f"cuff_{side}_{view}_LOD0", "kind": "cuff", "pose": "guard", "state": "holding",
                        "lod": 0, "side": side, "view": view, "camera": f"cuff_{side}_{view}"})
    for key, lod in (("guard_front", 0), ("guard_side", 0), ("guard_front", 1), ("guard_front", 2),
                     ("strike_raise_front", 0), ("strike_raise_side", 0), ("strike_hit_side", 0)):
        out.append({"name": f"{key}_LOD{lod}", "kind": "body", "pose": BODY_VIEWS[key]["pose"], "state": "holding",
                    "lod": lod, "camera": key})
    return out


# --- Vectors ------------------------------------------------------------------------------------------------------------
def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def scale(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    """The standard cross product, as Unreal's FVector operator^ computes it."""
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def norm(a):
    return math.sqrt(dot(a, a))


def unit(a):
    n = norm(a)
    if n < 1e-12:
        raise ValueError("zero vector")
    return scale(a, 1.0 / n)


def lerp(a, b, f):
    return add(a, scale(sub(b, a), f))


# --- Frames -------------------------------------------------------------------------------------------------------------
def axes_from_xz(x, z):
    """(X, Y, Z) as FRotationMatrix::MakeFromXZ makes them: X, then Y = Z ^ X, then Z = X ^ Y (each unit). A posed
    socket's forward, right and up vectors are these for its own X and Z."""
    x = unit(x)
    y = unit(cross(z, x))
    return x, y, cross(x, y)


def to_world(origin, axes, local):
    x, y, z = axes
    return add(origin, add(scale(x, local[0]), add(scale(y, local[1]), scale(z, local[2]))))


def to_local(origin, axes, point):
    d = sub(point, origin)
    return tuple(dot(d, a) for a in axes)


def dir_to_world(axes, local):
    return to_world((0.0, 0.0, 0.0), axes, local)


def dir_to_local(axes, direction):
    return tuple(dot(direction, a) for a in axes)


# --- The poses' grip targets (import_nyaakoto_third_person.py's, the readback's tolerance) ------------------------------
def blade_axes(elevation_deg):
    e = math.radians(elevation_deg)
    return (math.cos(e), 0.0, math.sin(e)), (-math.sin(e), 0.0, math.cos(e))


def two_paw_targets(stance):
    """{socket: (position cm, X, Z)} for a two-paw stance: Grip_L at the stance's point, Grip_R up the blade."""
    x, z = blade_axes(stance["elevation_deg"])
    gl = tuple(float(v) for v in stance["grip_l"])
    gr = sub(gl, scale(x, W00_GRIP_L_X))
    return {"hand_r_grip": (gr, x, z), "hand_l_grip": (gl, x, z)}


def bind_targets(tp):
    """{socket: (position cm, X, Z)}: the grip sockets at the reference pose, as the record places them."""
    return {name: (tuple(s["component_cm"]), tuple(s["x_axis"]), tuple(s["z_axis"]))
            for name, s in tp["sockets"].items() if name in SOCKETS.values()}


def ease(f):
    f = min(1.0, max(0.0, f))
    return f * f * (3.0 - 2.0 * f)


def keyed(keys, times, u):
    """third_person_rig.keyed_stance's Grip_L and elevation (the strike's keys), in plain Python."""
    i = len(times) - 2 if u >= 1.0 else max(k for k in range(len(times) - 1) if times[k] <= u)
    f = ease((u - times[i]) / (times[i + 1] - times[i]))
    a, b = keys[i], keys[i + 1]
    return {"grip_l": tuple((1.0 - f) * a["grip_l"][j] + f * b["grip_l"][j] for j in range(3)),
            "elevation_deg": (1.0 - f) * a["elevation_deg"] + f * b["elevation_deg"]}


def pose_stance(pose, tp):
    """The two-paw stance a pose holds (the runtime manifest's "third_person"), and its normalised clip time u. The
    reference pose ("rest") holds none: its grips are the record's bind sockets (bind_targets)."""
    if pose == "rest":
        return None, 0.0
    stance = tp["guard"]["stance"]
    if pose == "guard":
        return stance, 0.0
    strike = tp["strike"]
    frame = strike[f"{pose}_frame"]
    u = (frame - 1) / strike["frames"]
    keys = [stance] + [strike["keys"][k] for k in ("raise", "hit", "follow")] + [stance]
    return keyed(keys, strike["times"], u), u


def angle_deg(a, b):
    return math.degrees(math.acos(max(-1.0, min(1.0, dot(unit(a), unit(b))))))


# --- The body: voxels on the posed bones -----------------------------------------------------------------------------
# The planner voxelises LOD0's skin at bind (VOXEL_CM cells, the paws left out), each voxel moving with the bone that
# weights its samples most. A sight line is blocked by a voxel it passes within VOXEL_RADIUS_CM of. Capsules (plan
# attempt 2) could not hold the body: the bow, quiver, arrows and saya, weighted to the pelvis and spine, gave the torso
# a 99th-percentile radius of 89.5 cm, which wraps the guard's paws themselves.
VOXEL_CM = 4.0
VOXEL_RADIUS_CM = 3.0


def point_segment_distance(p, a, b):
    ab = sub(b, a)
    den = dot(ab, ab)
    t = 0.0 if den <= 1e-12 else min(1.0, max(0.0, dot(sub(p, a), ab) / den))
    return norm(sub(p, add(a, scale(ab, t))))


def blocking(camera, target, voxels, radius=VOXEL_RADIUS_CM, near_skip=NEAR_SKIP_CM, skip_bones=()):
    """{bone: voxels} the sight line from the camera to the target passes within radius of, beyond near_skip of the
    target. voxels: [(bone, point)] posed."""
    span = norm(sub(camera, target))
    if span <= near_skip:
        return {}
    a = lerp(target, camera, near_skip / span)
    lo = [min(a[i], camera[i]) - radius for i in range(3)]
    hi = [max(a[i], camera[i]) + radius for i in range(3)]
    out = {}
    for bone, p in voxels:
        if bone in skip_bones or not all(lo[i] <= p[i] <= hi[i] for i in range(3)):
            continue
        if point_segment_distance(p, a, camera) < radius:
            out[bone] = out.get(bone, 0) + 1
    return out


def choose(candidates, target, distance, voxels, to_world_dir=lambda d: d, min_z=MIN_CAMERA_Z_CM,
           near_skip=NEAR_SKIP_CM, skip_bones=(), radius=VOXEL_RADIUS_CM):
    """The best-ranked candidate whose camera (the target plus distance along its direction) is above min_z and whose
    sight line passes no body voxel. Candidates are in rank order, each {"direction": unit vector in the frame
    to_world_dir maps from}.

    Returns {"rank", "camera", "direction", "clear", "blocked"}. If none clears, the one blocked by the fewest voxels (the
    best ranked of those), with "clear" False and what blocks it, by bone: the shot is still taken, and its record says
    so."""
    best = None
    for rank, cand in enumerate(candidates):
        d = unit(to_world_dir(tuple(cand["direction"])))
        camera = add(target, scale(d, distance))
        blocked = blocking(camera, target, voxels, radius, near_skip, skip_bones)
        if camera[2] < min_z:
            blocked["floor"] = 1
        row = {"rank": rank, "camera": camera, "direction": d, "clear": not blocked, "blocked": blocked}
        if not blocked:
            return row
        if best is None or sum(blocked.values()) < sum(best["blocked"].values()):
            best = row
    if best is None:
        raise ValueError("no candidates")
    return best


# --- Framing ------------------------------------------------------------------------------------------------------------
def vertical_half_fov(fov_deg, aspect):
    return math.atan(math.tan(math.radians(fov_deg) / 2.0) / aspect)


def fit_distance(radius, fov_deg, aspect, margin=FRAME_MARGIN):
    """How far a camera stands for a sphere of this radius to fill its frame's height, less the margin."""
    return radius * margin / math.sin(vertical_half_fov(fov_deg, aspect))


def cuff_distance(aspect):
    return CUFF_HALF_CM * FRAME_MARGIN / math.tan(vertical_half_fov(CUFF_FOV_DEG, aspect))


def body_camera(key, aspect):
    """A full-body view's camera position and the point it looks at."""
    v = BODY_VIEWS[key]
    distance = (v["height_cm"] / 2.0) * FRAME_MARGIN / math.tan(vertical_half_fov(BODY_FOV_DEG, aspect))
    az, el = math.radians(v["azimuth_deg"]), math.radians(v["elevation_deg"])
    d = (math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el))
    return add(v["target_cm"], scale(d, distance)), tuple(v["target_cm"]), distance


def cuff_candidates(wrist, elbow, side, view, steps=24):
    """Directions round the forearm at the wrist, best first: for "outside", away from the body's midline and a little
    up; for "below", down and a little out. Each is square to the forearm, tilted 15 deg toward the paw."""
    axis = unit(sub(wrist, elbow))
    ref = (0.0, 0.0, 1.0) if abs(axis[2]) < 0.9 else (1.0, 0.0, 0.0)
    e1 = unit(cross(axis, ref))
    e2 = cross(axis, e1)
    lateral = (0.0, 1.0 if side == "R" else -1.0, 0.0)
    want = unit(add(lateral, (0.0, 0.0, 0.45))) if view == "outside" else unit(add((0.0, 0.0, -1.0), scale(lateral, 0.35)))
    tilt = math.radians(15.0)
    rows = []
    for k in range(steps):
        a = 2.0 * math.pi * k / steps
        ring = add(scale(e1, math.cos(a)), scale(e2, math.sin(a)))
        d = unit(add(scale(ring, math.cos(tilt)), scale(axis, math.sin(tilt))))
        rows.append({"direction": d, "preference": dot(d, want), "around_deg": math.degrees(a)})
    rows.sort(key=lambda r: -r["preference"])
    return rows
