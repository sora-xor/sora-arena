"""Gates for UE 5.8 readbacks of runtime weapon sockets.

Pure Python, with no unreal and no numpy. probe_runtime_weapon_sockets.py feeds it editor readbacks, and
scripts/art/test_weapon_socket_export.py feeds it fixtures.

**Malformed and nonfinite inputs fail explicitly.** Every vector a gate reads must be present, of its length,
numeric (bools excluded) and finite (finite_vector). Otherwise the gate reports it. Root's review of d13ebfc5 found
that a NaN passed every check: a NaN fails every comparison, so `distance >= tolerance` never fired, and max() could
drop it. Every comparison is now also written to fail safe: `not (distance < tolerance)`.

**socket_failures** applies:
- SoraViewmodelComponent's admission (SoraViewmodelComponent.cpp:20-30): Grip_R, Grip_L and Muzzle present on a
  weapon's main mesh, and at scale 1 within 1e-4. Here the scale rule covers every socket;
- the viewmodel contract's frame (viewmodels.json socket_frame): each socket where its build record puts it, within
  0.02 cm, and on its authored axes. The forward (X) and up (Z) vectors are (x, -y, z) of the Blender axes, and the
  right (Y) is up x forward, as in Unreal's FRotationMatrix. Each is checked signed, within 0.009, the drone's
  tolerance.

**model_agreement** measures how far a readback lies from fbx_unreal_sockets' prediction, on every axis. A
nonfinite or malformed value on either side is counted, and agrees() refuses it.

**same_import** compares two imports of one asset (original and corrected).
- It validates both imports' LOD0 sections first: array lengths, index ranges, and every vector finite.
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
FIELDS = ("position", "scale", "forward", "right", "up")


def finite_vector(v, n=3):
    """v as a tuple of n finite floats, or None when it is missing, of another length, not numeric (bools
    excluded) or not finite."""
    if not isinstance(v, (list, tuple)) or len(v) != n:
        return None
    if not all(type(c) in (int, float) and math.isfinite(c) for c in v):
        return None
    return tuple(float(c) for c in v)


def unreal_point(m):
    """Blender metres to Unreal centimetres: 100 x (x, -y, z)."""
    return (100.0 * m[0], -100.0 * m[1], 100.0 * m[2])


def unreal_axis(a):
    return (a[0], -a[1], a[2])


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def authored_axes(axes):
    """A socket's authored Blender {x, z} axes as Unreal's forward, right and up; None if either is malformed."""
    x, z = finite_vector((axes or {}).get("x")), finite_vector((axes or {}).get("z"))
    if x is None or z is None:
        return None
    forward, up = unreal_axis(x), unreal_axis(z)
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
        got = {f: finite_vector(row.get(f)) if isinstance(row, dict) else None for f in FIELDS}
        for f, v in got.items():
            if v is None:
                out.append(f"{name} {f} is malformed or nonfinite: {row.get(f) if isinstance(row, dict) else row!r}")
        want_position = finite_vector(record_sockets[name])
        want_axes = authored_axes(socket_axes.get(name))
        if want_position is None:
            out.append(f"{name}: the record's position is malformed or nonfinite: {record_sockets[name]!r}")
        if want_axes is None:
            out.append(f"{name}: the authored axes are missing, malformed or nonfinite: {socket_axes.get(name)!r}")
        if got["position"] and want_position and not math.dist(got["position"], unreal_point(want_position)) < POSITION_CM:
            out.append(f"{name} moved: {row['position']}")
        if got["scale"] and not math.dist(got["scale"], (1.0, 1.0, 1.0)) < SCALE:
            out.append(f"{name} is scaled: {row['scale']}")
        for axis, want in (want_axes or {}).items():
            if got[axis] and not math.dist(got[axis], want) < AXIS:
                out.append(f"{name} {axis} is {row[axis]}, authored {want}")
    return out


def model_agreement(readback, predicted):
    """The worst distance, over the sockets both hold, between the readback and the model's prediction
    ({socket: {position_cm, scale, forward, right, up}}). Malformed or nonfinite values on either side are counted
    under "nonfinite" and kept out of the maxima, which agrees() refuses."""
    worst = {"position_cm": 0.0, "scale": 0.0, "forward": 0.0, "right": 0.0, "up": 0.0, "nonfinite": 0}
    for name, row in readback.items():
        p = predicted.get(name)
        if p is None:
            worst["missing"] = worst.get("missing", 0) + 1
            continue
        for key, rkey, pkey in (("position_cm", "position", "position_cm"), ("scale", "scale", "scale"),
                                ("forward", "forward", "forward"), ("right", "right", "right"), ("up", "up", "up")):
            u = finite_vector(row.get(rkey)) if isinstance(row, dict) else None
            v = finite_vector(p.get(pkey)) if isinstance(p, dict) else None
            if u is None or v is None:
                worst["nonfinite"] += 1
                continue
            d = math.dist(u, v)
            if d > worst[key]:
                worst[key] = d
    return worst


def agrees(worst):
    return (not worst.get("missing") and not worst.get("nonfinite") and
            all(math.isfinite(worst[k]) and worst[k] <= v for k, v in AGREEMENT.items()))


STEP = 1.0 / 127.0              # Unreal's packed 8-bit tangent basis (FPackedNormal): the readback's resolution
# Corner-by-corner gates between two imports of one asset.
SAME = {"positions_cm": 1e-3, "uvs": 1e-6, "normal_steps": 1, "tangent_deg": 2.0}
SECTION_ARRAYS = (("positions", 3), ("normals", 3), ("tangents", 3), ("uvs", 2))


def section_problems(section):
    """What is malformed in one LOD0 section: array lengths, index range and type, nonfinite vectors."""
    out = []
    try:
        count = len(section["positions"])
        for key, n in SECTION_ARRAYS:
            if len(section[key]) != count:
                out.append(f"{key}: {len(section[key])} entries for {count} vertices")
                continue
            bad = sum(1 for v in section[key] if finite_vector(v, n) is None)
            if bad:
                out.append(f"{key}: {bad} malformed or nonfinite")
        idx = section["indices"]
        if len(idx) % 3:
            out.append(f"indices: {len(idx)} is not a whole number of triangles")
        bad = sum(1 for i in idx if type(i) is not int or not 0 <= i < count)
        if bad:
            out.append(f"indices: {bad} malformed or out of range")
    except (KeyError, TypeError) as e:
        out.append(f"malformed section: {e!r}")
    return out


def _angle_deg(a, b):
    """The angle between two vectors, from atan2 of the cross and dot products (well conditioned near 0)."""
    c = cross(a, b)
    return math.degrees(math.atan2(math.sqrt(c[0] ** 2 + c[1] ** 2 + c[2] ** 2), sum(x * y for x, y in zip(a, b))))


def _triangles(section):
    idx = section["indices"]
    return [tuple(idx[k:k + 3]) for k in range(0, len(idx), 3)]


def corner_pairs(x, y, tol=None):
    """The corner pairs (vertex i of x, vertex j of y) of two valid sections' triangles (section_problems is
    empty for both), and how they were paired.

    - "ordered": the triangle lists match corner for corner, each within tol cm.
    - "matched": Unreal ordered the triangles differently (s86, W11 and W13). Each triangle of y is then matched
      to an unused triangle of x with the same corners in a cyclic rotation, which keeps the winding, found
      through a spatial hash of the centroids.

    None when a triangle finds no match.
    """
    tol = SAME["positions_cm"] if tol is None else tol
    tx, ty = _triangles(x), _triangles(y)
    px, py = x["positions"], y["positions"]
    if len(tx) != len(ty):
        return None
    if all(math.dist(px[i], py[j]) <= tol for a, b in zip(tx, ty) for i, j in zip(a, b)):
        return [(i, j) for a, b in zip(tx, ty) for i, j in zip(a, b)], "ordered"
    cell = 0.05
    def centroid(tri, p):
        return [sum(p[i][k] for i in tri) / 3.0 for k in range(3)]
    def key(c):
        return tuple(math.floor(v / cell) for v in c)
    grid = {}
    for n, tri in enumerate(tx):
        grid.setdefault(key(centroid(tri, px)), []).append(n)
    used, pairs = set(), []
    for tri in ty:
        k0 = key(centroid(tri, py))
        found = None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for n in grid.get((k0[0] + dx, k0[1] + dy, k0[2] + dz), ()):
                        if n in used or found:
                            continue
                        a = tx[n]
                        for r in range(3):
                            rot = a[r:] + a[:r]
                            if all(math.dist(px[i], py[j]) <= tol for i, j in zip(rot, tri)):
                                found = (n, rot)
                                break
        if found is None:
            return None
        used.add(found[0])
        pairs.extend(zip(found[1], tri))
    return pairs, "matched"


DEGENERATE = 0.5                # a packed tangent-basis vector shorter than this is degenerate (Unreal writes 0)


def same_import(a, b, detail=0):
    """Two imports of one asset, compared corner by corner: each triangle's three corners, so that a vertex the
    importer shares in one import and splits in the other still compares like for like.

    a, b: {lod0: {sections: [{positions, indices, normals, uvs, tangents}]}, materials, collision}.
    Each section is validated first (section_problems): a malformed or nonfinite one fails, and is not compared.
    The corners are paired by corner_pairs: in index order where that lines up, otherwise by matching triangles.
    Returns (gaps, failures). The gaps hold the worst position (cm) and UV distances, the worst normal and tangent
    differences in 8-bit steps and in degrees, how many corners differ, and each import's render vertex count.
    Angles are measured only between valid vectors. A corner where one import's vector is degenerate (shorter than
    DEGENERATE) and the other's is not is counted apart, and gated: run s87's angles missed one, because
    atan2(0, 0) reads 0 deg. detail=N keeps the N corners with the largest normal or tangent steps, in full.

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
            "render_vertices": [], "pairing": [], "normal_degenerate_mismatches": 0, "tangent_degenerate_mismatches": 0}
    worst_corners = []
    failures = []
    try:
        sa, sb = a["lod0"]["sections"], b["lod0"]["sections"]
        gaps["render_vertices"] = [sum(len(s["positions"]) for s in sa), sum(len(s["positions"]) for s in sb)]
    except (KeyError, TypeError) as e:
        return gaps, [f"malformed import: {e!r}"]
    if len(sa) != len(sb):
        failures.append(f"sections {len(sa)} against {len(sb)}")
    for k, (x, y) in enumerate(zip(sa, sb)):
        problems = [f"first import {p}" for p in section_problems(x)] + [f"second import {p}" for p in section_problems(y)]
        if problems:
            failures.extend(f"section {k}: {p}" for p in problems)
            continue
        if len(x["indices"]) != len(y["indices"]):
            failures.append(f"section {k}: {len(x['indices']) // 3} triangles against {len(y['indices']) // 3}")
            continue
        paired = corner_pairs(x, y)
        if paired is None:
            failures.append(f"section {k}: a triangle has no match within {SAME['positions_cm']} cm")
            continue
        pairs, how = paired
        gaps["pairing"].append(how)
        for i, j in pairs:
            gaps["corners"] += 1
            gaps["positions_cm"] = max(gaps["positions_cm"], math.dist(x["positions"][i], y["positions"][j]))
            gaps["uvs"] = max(gaps["uvs"], math.dist(x["uvs"][i], y["uvs"][j]))
            corner_steps = 0
            for key, name in (("normals", "normal"), ("tangents", "tangent")):
                u, v = x[key][i], y[key][j]
                steps = round(max(abs(p - q) for p, q in zip(u, v)) / STEP)
                corner_steps = max(corner_steps, steps)
                if steps:
                    gaps[f"{name}_corners_differing"] += 1
                    gaps[f"{name}_steps"] = max(gaps[f"{name}_steps"], steps)
                    valid = [math.sqrt(sum(c * c for c in w)) >= DEGENERATE for w in (u, v)]
                    if all(valid):
                        gaps[f"{name}_deg"] = max(gaps[f"{name}_deg"], _angle_deg(u, v))
                    elif any(valid):
                        gaps[f"{name}_degenerate_mismatches"] += 1
            if detail and corner_steps:
                worst_corners.append((corner_steps, {key: [x[key][i], y[key][j]] for key in
                                                     ("positions", "normals", "tangents", "uvs")}))
    for key in ("positions_cm", "uvs", "tangent_deg"):
        if not gaps[key] <= SAME[key]:
            failures.append(f"{key} differ by {gaps[key]}")
    for name in ("normal", "tangent"):
        if gaps[f"{name}_degenerate_mismatches"]:
            failures.append(f"{gaps[f'{name}_degenerate_mismatches']} corners have a degenerate {name} in one import only")
    if detail:
        gaps["worst_corners"] = [c for _s, c in sorted(worst_corners, key=lambda w: -w[0])[:detail]]
    if not gaps["normal_steps"] <= SAME["normal_steps"]:
        failures.append(f"normals differ by {gaps['normal_steps']} steps")
    if a.get("materials") != b.get("materials"):
        failures.append(f"material slots {a.get('materials')} against {b.get('materials')}")
    if a.get("collision") != b.get("collision"):
        failures.append(f"collision {a.get('collision')} against {b.get('collision')}")
    return gaps, failures
