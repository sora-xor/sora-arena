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

**same_import** compares two imports of one asset (original and corrected): the LOD0 render arrays, the material
slots and the collision counts.

Nothing here normalizes a transform: a readback passes or fails as it was imported.
"""

import math

ADMISSION = ("Grip_R", "Grip_L", "Muzzle")
POSITION_CM, SCALE, AXIS = 0.02, 1e-4, 0.009
# How closely a real import must follow the model before the model's screen of the other files is trusted.
AGREEMENT = {"position_cm": 1e-3, "scale": 1e-4, "forward": 1e-5, "right": 1e-5, "up": 1e-5}
# How closely the corrected file's import must repeat the original's.
SAME = {"positions_cm": 1e-3, "normals": 1e-4, "uvs": 1e-6, "tangents": 1e-3}


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


def _gap(a, b):
    if len(a) != len(b):
        return math.inf
    return max((math.dist(x, y) if isinstance(x, (list, tuple)) else abs(x - y) for x, y in zip(a, b)), default=0.0)


def same_import(a, b):
    """The differences between two imports of one asset: {lod0: {sections: [{positions, indices, normals, uvs,
    tangents}]}, materials: [...], collision: {...}}. Returns (worst gaps, failures)."""
    gaps, failures = {"positions_cm": 0.0, "normals": 0.0, "uvs": 0.0, "tangents": 0.0}, []
    sa, sb = a["lod0"]["sections"], b["lod0"]["sections"]
    if len(sa) != len(sb):
        failures.append(f"sections {len(sa)} against {len(sb)}")
    for i, (x, y) in enumerate(zip(sa, sb)):
        if x["indices"] != y["indices"]:
            failures.append(f"section {i}: the triangles differ")
        for key, name in (("positions", "positions_cm"), ("normals", "normals"), ("uvs", "uvs"), ("tangents", "tangents")):
            gaps[name] = max(gaps[name], _gap(x[key], y[key]))
    failures.extend(f"{k} differ by {gaps[k]}" for k, tol in SAME.items() if gaps[k] > tol)
    if a["materials"] != b["materials"]:
        failures.append(f"material slots {a['materials']} against {b['materials']}")
    if a["collision"] != b["collision"]:
        failures.append(f"collision {a['collision']} against {b['collision']}")
    return gaps, failures
