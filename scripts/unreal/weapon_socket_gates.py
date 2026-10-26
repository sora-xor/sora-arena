"""Gates for UE 5.8 readbacks of runtime weapon sockets.

Pure Python, with no unreal and no numpy. probe_runtime_weapon_sockets.py feeds it editor readbacks, and
scripts/art/test_weapon_socket_export.py feeds it fixtures.

**socket_failures** applies:
- SoraViewmodelComponent's admission (SoraViewmodelComponent.cpp:20-30): Grip_R, Grip_L and Muzzle present on a
  weapon's main mesh, and at scale 1 within 1e-4. Here the scale rule covers every socket;
- the viewmodel contract's frame (viewmodels.json socket_frame): each socket where its build record puts it, within
  0.02 cm, and on its authored axes. The forward (X) and up (Z) vectors are (x, -y, z) of the Blender axes, and the
  right (Y) is up x forward, as in Unreal's FRotationMatrix. Each is checked signed, within 0.009, the drone's
  tolerance.

**model_agreement** measures how far a readback lies from fbx_unreal_sockets' prediction, on every axis.

**same_import** compares two imports of one asset (original and corrected).
- It goes corner by corner through LOD0's triangles, so a vertex that one import shares and the other splits still
  compares like for like.
- Normals and tangents are measured in steps of Unreal's 8-bit packed tangent basis, the readback's resolution.
- The material slots and the collision counts must be equal.
- Probe run s85 compared whole render arrays instead. It flagged one-step flips, and one extra render vertex in W11
  and in W13, as failures.

Nothing here normalizes a transform: a readback passes or fails as it was imported.
"""

import math

ADMISSION = ("Grip_R", "Grip_L", "Muzzle")
POSITION_CM, SCALE, AXIS = 0.02, 1e-4, 0.009
# How closely a real import must follow the model before the model's screen of the other files is trusted.
AGREEMENT = {"position_cm": 1e-3, "scale": 1e-4, "forward": 1e-5, "right": 1e-5, "up": 1e-5}


def unreal_point(m):
    """Blender metres to Unreal centimetres: 100 x (x, -y, z)."""
    return (100.0 * m[0], -100.0 * m[1], 100.0 * m[2])


def unreal_axis(a):
    return (a[0], -a[1], a[2])


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def authored_axes(axes):
    """A socket's authored Blender {x, z} axes as Unreal's forward, right and up."""
    forward, up = unreal_axis(axes["x"]), unreal_axis(axes["z"])
    return {"forward": forward, "right": cross(up, forward), "up": up}


def socket_failures(readback, record_sockets, socket_axes, main_mesh):
    """The failures of one imported mesh's sockets; empty when it passes.

    readback: {socket: {position, scale, forward, right, up}} as the editor reads them. record_sockets: the build
    record's Blender positions. socket_axes: the authored Blender {x, z} axes. main_mesh: whether admission's sockets
    apply.
    """
    out = []
    if set(readback) != set(record_sockets):
        out.append(f"sockets {sorted(readback)}, record {sorted(record_sockets)}")
    if main_mesh:
        out.extend(f"{name} is missing (admission)" for name in ADMISSION if name not in readback)
    for name, row in sorted(readback.items()):
        if name not in record_sockets:
            continue
        if math.dist(row["position"], unreal_point(record_sockets[name])) >= POSITION_CM:
            out.append(f"{name} moved: {row['position']}")
        if math.dist(row["scale"], (1.0, 1.0, 1.0)) >= SCALE:
            out.append(f"{name} is scaled: {row['scale']}")
        for axis, want in authored_axes(socket_axes[name]).items():
            if math.dist(row[axis], want) >= AXIS:
                out.append(f"{name} {axis} is {row[axis]}, authored {want}")
    return out


def model_agreement(readback, predicted):
    """The worst distance, over the sockets both hold, between the readback and the model's prediction
    ({socket: {position_cm, scale, forward, right, up}})."""
    worst = {"position_cm": 0.0, "scale": 0.0, "forward": 0.0, "right": 0.0, "up": 0.0}
    for name, row in readback.items():
        p = predicted.get(name)
        if p is None:
            worst["missing"] = worst.get("missing", 0) + 1
            continue
        worst["position_cm"] = max(worst["position_cm"], math.dist(row["position"], p["position_cm"]))
        worst["scale"] = max(worst["scale"], math.dist(row["scale"], p["scale"]))
        for axis in ("forward", "right", "up"):
            worst[axis] = max(worst[axis], math.dist(row[axis], p[axis]))
    return worst


def agrees(worst):
    return not worst.get("missing") and all(worst[k] <= v for k, v in AGREEMENT.items())


STEP = 1.0 / 127.0              # Unreal's packed 8-bit tangent basis (FPackedNormal): the readback's resolution
# Corner-by-corner gates between two imports of one asset.
SAME = {"positions_cm": 1e-3, "uvs": 1e-6, "normal_steps": 1, "tangent_deg": 2.0}


def _angle_deg(a, b):
    """The angle between two vectors, from atan2 of the cross and dot products (well conditioned near 0)."""
    c = cross(a, b)
    return math.degrees(math.atan2(math.sqrt(c[0] ** 2 + c[1] ** 2 + c[2] ** 2), sum(x * y for x, y in zip(a, b))))


def same_import(a, b):
    """Two imports of one asset, compared corner by corner: each triangle's three corners, so that a vertex the
    importer shares in one import and splits in the other still compares like for like.

    a, b: {lod0: {sections: [{positions, indices, normals, uvs, tangents}]}, materials, collision}.
    Returns (gaps, failures). The gaps hold the worst position (cm) and UV distances, the worst normal and tangent
    differences in 8-bit steps and in degrees, how many corners differ, and each import's render vertex count.

    Gates (SAME):
    - triangles in the same order;
    - positions within 1e-3 cm;
    - UVs within 1e-6;
    - normals within one 8-bit step per component;
    - tangents within 2 deg. Unreal derives the tangents (MikkTSpace) and packs them in 8 bits, so at an
      ill-conditioned vertex a tiny input change can move them by several steps;
    - the material slots and the collision counts equal.
    """
    gaps = {"positions_cm": 0.0, "uvs": 0.0, "normal_steps": 0, "normal_deg": 0.0, "tangent_steps": 0,
            "tangent_deg": 0.0, "corners": 0, "normal_corners_differing": 0, "tangent_corners_differing": 0,
            "render_vertices": [sum(len(s["positions"]) for s in m["lod0"]["sections"]) for m in (a, b)]}
    failures = []
    sa, sb = a["lod0"]["sections"], b["lod0"]["sections"]
    if len(sa) != len(sb):
        failures.append(f"sections {len(sa)} against {len(sb)}")
    for k, (x, y) in enumerate(zip(sa, sb)):
        if len(x["indices"]) != len(y["indices"]):
            failures.append(f"section {k}: {len(x['indices']) // 3} triangles against {len(y['indices']) // 3}")
            continue
        for i, j in zip(x["indices"], y["indices"]):
            gaps["corners"] += 1
            gaps["positions_cm"] = max(gaps["positions_cm"], math.dist(x["positions"][i], y["positions"][j]))
            gaps["uvs"] = max(gaps["uvs"], math.dist(x["uvs"][i], y["uvs"][j]))
            for key, name in (("normals", "normal"), ("tangents", "tangent")):
                u, v = x[key][i], y[key][j]
                steps = round(max(abs(p - q) for p, q in zip(u, v)) / STEP)
                if steps:
                    gaps[f"{name}_corners_differing"] += 1
                    gaps[f"{name}_steps"] = max(gaps[f"{name}_steps"], steps)
                    gaps[f"{name}_deg"] = max(gaps[f"{name}_deg"], _angle_deg(u, v))
    for key in ("positions_cm", "uvs", "tangent_deg"):
        if gaps[key] > SAME[key]:
            failures.append(f"{key} differ by {gaps[key]}")
    if gaps["normal_steps"] > SAME["normal_steps"]:
        failures.append(f"normals differ by {gaps['normal_steps']} steps")
    if a["materials"] != b["materials"]:
        failures.append(f"material slots {a['materials']} against {b['materials']}")
    if a["collision"] != b["collision"]:
        failures.append(f"collision {a['collision']} against {b['collision']}")
    return gaps, failures
