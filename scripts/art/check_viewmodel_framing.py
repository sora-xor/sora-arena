#!/usr/bin/env python3
"""Source checks of the first-person viewmodel contract (Content/Data/viewmodels.json).

  python3 scripts/art/check_viewmodel_framing.py [--table] [--contract FILE] [--root DIR]

Source-only: pinhole math on socket points. It never replaces real
first-person captures, which alone show paw-mesh pixels, near-plane clipping
of real geometry and the final look. Exit 1 on any failure.

* **Schema:** the version, the required blocks, and the poses and envelope
  states the weapons name.
* **Completeness:** the weapon table is exactly the catalog's ``weapons`` and
  ``campaign_weapons`` ids plus the dojo bokken. Every id and key is unique,
  and English names match the catalog.
* **References:**
  - each build record exists, carries the weapon's key, and holds its
    first-person mesh asset with every socket the pose uses;
  - contract-only sockets are complete;
  - every builder call quoted for a rotated socket still exists verbatim in
    its builder.
* **Envelopes:** each pose is placed in every envelope state:
  - the transform is Qaction * Qrest about the anchor, plus eye-space bob and
    lift;
  - at rest and in the bob extremes, visible sockets stay in their screen
    boxes, partial ones in the edge band, and the clear line keeps off the
    reticle;
  - in action states, every socket stays in front of the near plane, and
    visible and partial sockets stay in the action band.
* **Drawn bow:**
  - the arrow line meets the reticle at the aim distance;
  - the legacy -15 degree drawing pitch, stacked on the pose, must miss;
  - for each checked BowAimOffset, the gameplay ray's screen point in the
    world camera is compared with the drawn arrow's in the first-person
    camera, both uncorrected and with the presentation correction;
    the corrected one must agree.

Counts are reported by category.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "Content/Data/viewmodels.json"
BLOCKS = ("schema_version", "kind", "scope", "camera", "mesh_scale", "composition", "motion", "aim_presentation",
          "envelopes", "poses", "weapons", "hero_gear")


def rotation(pitch: float, yaw: float, roll: float):
    """UE FRotationMatrix rows: the rotated X, Y and Z axes."""
    sp, cp = math.sin(math.radians(pitch)), math.cos(math.radians(pitch))
    sy, cy = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
    sr, cr = math.sin(math.radians(roll)), math.cos(math.radians(roll))
    return ((cp * cy, cp * sy, sp),
            (sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp),
            (-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp))


def apply(rows, v):
    """v expressed in the rotated frame ``rows`` -> parent coordinates."""
    return tuple(sum(v[k] * rows[k][i] for k in range(3)) for i in range(3))


def compose(outer, inner):
    """Rows of the rotation 'inner first, then outer' (both in parent coordinates)."""
    return tuple(apply(outer, inner[k]) for k in range(3))


def to_ue_cm(metres):
    """A socket from Blender metres (+Y the wielder's left) to UE centimetres (+Y right)."""
    x, y, z = metres
    return (100.0 * x, -100.0 * y, 100.0 * z)


def place(rest: dict, sockets: dict, anchor: str, scale: float, state: dict | None = None, aim=None):
    """Eye-space positions (cm; X forward, Y right, Z up) of every socket.

    Qpresentation = Qaim * Qaction * Qrest about the anchor; bob and lift move
    the anchor in eye coordinates."""
    state = state or {}
    q = rotation(*rest["rotation_deg"])
    if state.get("pitch") or state.get("roll"):
        q = compose(rotation(state.get("pitch", 0.0), 0.0, state.get("roll", 0.0)), q)
    if aim is not None:
        q = compose(aim, q)
    by, bz = state.get("bob", (0.0, 0.0))
    origin = (rest["anchor_cm"][0], rest["anchor_cm"][1] + by, rest["anchor_cm"][2] + bz + state.get("lift", 0.0))
    a = to_ue_cm(sockets[anchor])
    out = {}
    for name, metres in sockets.items():
        p = [scale * (c - ac) for c, ac in zip(to_ue_cm(metres), a)]
        d = apply(q, p)
        out[name] = tuple(origin[i] + d[i] for i in range(3))
    return out, q


class Screen:
    def __init__(self, camera: dict, fov_key="first_person_fov_deg"):
        self.tan_h = math.tan(math.radians(camera[fov_key] / 2.0))
        aw, ah = camera["aspect"]
        self.aspect = aw / ah
        self.tan_v = self.tan_h / self.aspect
        self.scale = camera["first_person_scale"]
        self.near = camera["near_plane_cm"]
        self.clear = camera["reticle_clear_radius"]

    def uv(self, p):
        x, y, z = p
        return (y / x) / self.tan_h, (z / x) / self.tan_v

    def direction(self, u, v):
        """The eye-space direction that lands on screen point (u, v)."""
        return (1.0, u * self.tan_h, v * self.tan_v)

    def reticle_distance(self, p):
        """Distance from the screen centre, in half-heights."""
        u, v = self.uv(p)
        return math.hypot(u * self.aspect, v)

    def distance_uv(self, a, b):
        return math.hypot((a[0] - b[0]) * self.aspect, a[1] - b[1])


class Report:
    def __init__(self):
        self.failures, self.rows, self.counts = [], [], {}

    def check(self, category, ok, message):
        self.counts[category] = self.counts.get(category, 0) + 1
        if not ok:
            self.failures.append(f"{category}: {message}")
        return ok


def load_sockets(entry: dict, root: Path, rep: Report):
    """The weapon mesh's sockets in Blender metres: from its build record, or the contract."""
    if "sockets_m" in entry:
        return entry["sockets_m"]
    path = root / entry.get("sockets_from", "")
    if not rep.check("reference", path.is_file(), f"{entry.get('key')}: no build record {entry.get('sockets_from')}"):
        return None
    record = json.loads(path.read_text())
    rep.check("reference", record.get("key") == entry.get("key"),
              f"{entry.get('key')}: build record key is {record.get('key')!r}")
    asset = entry["first_person_mesh"].rsplit("/", 1)[-1]
    info = (record.get("assets") or {}).get(asset)
    if not rep.check("reference", info is not None and "sockets" in info, f"{entry.get('key')}: record has no {asset} sockets"):
        return None
    return info["sockets"]


def check_axes(entry: dict, root: Path, rep: Report):
    for name, ax in (entry.get("socket_axes") or {}).items():
        builder = root / ax.get("builder", "")
        text = builder.read_text() if builder.is_file() else ""
        rep.check("provenance", ax.get("call", "") in text and ax.get("call"),
                  f"{entry.get('key')}: {name}'s builder call is no longer in {ax.get('builder')}")
        x, z = ax.get("x"), ax.get("z")
        rep.check("provenance", isinstance(x, list) and isinstance(z, list) and len(x) == 3 and len(z) == 3
                  and f"x=({', '.join(str(v) for v in x)})" in ax.get("call", "")
                  and f"z=({', '.join(str(v) for v in z)})" in ax.get("call", ""),
                  f"{entry.get('key')}: {name}'s axes do not match the quoted call")


def check_catalog(contract: dict, root: Path, rep: Report):
    weapons = contract.get("weapons")
    if not rep.check("schema", isinstance(weapons, list) and weapons, "the weapon table is empty or missing"):
        return
    catalog = json.loads((root / "Content/Data/catalog.json").read_text())
    names = {w["id"]: w.get("name_en") for w in catalog.get("weapons", []) + catalog.get("campaign_weapons", [])}
    expected = sorted(names) + ["bokken"]
    ids = [w.get("id") for w in weapons]
    keys = [w.get("key") for w in weapons]
    rep.check("completeness", len(ids) == len(set(map(str, ids))), f"duplicate weapon ids {sorted({str(i) for i in ids if ids.count(i) > 1})}")
    rep.check("completeness", len(keys) == len(set(keys)), f"duplicate weapon keys {sorted({k for k in keys if keys.count(k) > 1})}")
    missing = [i for i in expected if i not in ids]
    extra = [i for i in ids if i not in expected]
    rep.check("completeness", not missing and not extra, f"weapon ids differ from the catalog: missing {missing}, extra {extra}")
    for w in weapons:
        if isinstance(w.get("id"), int) and w["id"] in names:
            rep.check("completeness", w.get("en") == names[w["id"]],
                      f"{w.get('key')}: name {w.get('en')!r} is not the catalog's {names[w['id']]!r}")


def needed_sockets(pose: dict):
    names = {pose["anchor"], *pose.get("screen", {}), *pose.get("visible", []), *pose.get("partial", {})}
    names |= set(pose.get("clear_line") or [])
    if pose.get("aim_line"):
        names.add(pose["aim_line"]["from"])
    return names


def check_pose(label, pose, sockets, contract, screen, world, rep: Report):
    env = contract["envelopes"]
    scale = contract["mesh_scale"]
    states = ["rest", "bob_up_right", "bob_down_left", *pose.get("actions", [])]
    for state_name in states:
        if not rep.check("schema", state_name in env["states"], f"{label}: unknown state {state_name}"):
            continue
        state = {**env["states"][state_name],
                 **{k: v for k, v in (pose.get("motion_overrides") or {}).get(state_name, {}).items() if k != "why"}}
        pts, q = place(pose["rest"], sockets, pose["anchor"], scale, state)
        tag = f"{label} [{state_name}]"
        for name, p in pts.items():
            rep.check("near-plane", p[0] * screen.scale > screen.near,
                      f"{tag}: {name} behind the near plane ({p[0]:.1f} cm)")
        if state.get("action"):
            (u0, u1), (v0, v1) = env["action_band"]["u"], env["action_band"]["v"]
            for name in pose.get("visible", []):
                u, v = screen.uv(pts[name])
                rep.check("envelope", u0 <= u <= u1 and v0 <= v <= v1,
                          f"{tag}: {name} at u {u:+.2f}, v {v:+.2f} leaves the action band")
            continue
        for name, box in pose.get("screen", {}).items():
            u, v = screen.uv(pts[name])
            if state_name == "rest":
                rep.rows.append((label, name, u, v))
            (bu0, bu1), (bv0, bv1) = box["u"], box["v"]
            rep.check("screen", bu0 <= u <= bu1 and bv0 <= v <= bv1,
                      f"{tag}: {name} at u {u:+.2f}, v {v:+.2f}, outside u {box['u']} v {box['v']}")
        for name in pose.get("visible", []):
            u, v = screen.uv(pts[name])
            rep.check("screen", -1.0 <= u <= 1.0 and -1.0 <= v <= 1.0, f"{tag}: visible {name} at u {u:+.2f}, v {v:+.2f} is off the frame")
        for name in pose.get("partial", {}):
            u, v = screen.uv(pts[name])
            rep.check("screen", -1.1 <= u <= 1.1 and env["edge_band_v"] <= v <= 1.0,
                      f"{tag}: partial {name} at u {u:+.2f}, v {v:+.2f} is beyond the edge band")
        line = pose.get("clear_line")
        if line:
            a, b = pts[line[0]], pts[line[1]]
            worst = min(screen.reticle_distance(tuple(a[i] + (b[i] - a[i]) * t / 20 for i in range(3))) for t in range(21))
            if state_name == "rest":
                rep.rows.append((label, f"{line[0]}-{line[1]} reticle gap", worst, None))
            rep.check("reticle", worst >= screen.clear,
                      f"{tag}: {line[0]}-{line[1]} comes {worst:.3f} half-heights from the reticle (needs {screen.clear})")
        aim = pose.get("aim_line")
        if aim and state_name == "rest":
            check_aim(label, pose, sockets, contract, screen, world, rep)


def arrow_screen_point(pose, sockets, contract, screen, aim_rows=None, extra_pitch=0.0):
    aim = pose["aim_line"]
    state = {"pitch": extra_pitch} if extra_pitch else {}
    pts, q = place(pose["rest"], sockets, pose["anchor"], contract["mesh_scale"], state, aim_rows)
    start = pts[aim["from"]]
    far = tuple(start[i] + aim["distance_cm"] * q[0][i] for i in range(3))
    return screen.uv(far)


def aim_rows_toward(direction, pose):
    """The rotation (applied after the rest) that turns the rest arrow's +X
    onto ``direction``: yaw and pitch only."""
    q_rest = rotation(*pose["rest"]["rotation_deg"])
    x_rest = q_rest[0]
    yaw_rest = math.degrees(math.atan2(x_rest[1], x_rest[0]))
    pitch_rest = math.degrees(math.atan2(x_rest[2], math.hypot(x_rest[0], x_rest[1])))
    yaw = math.degrees(math.atan2(direction[1], direction[0]))
    pitch = math.degrees(math.atan2(direction[2], math.hypot(direction[0], direction[1])))
    return compose(rotation(pitch, yaw, 0.0), tuple(zip(*rotation(pitch_rest, yaw_rest, 0.0))))


def check_aim(label, pose, sockets, contract, screen, world, rep: Report):
    aim = pose["aim_line"]
    u, v = arrow_screen_point(pose, sockets, contract, screen)
    miss = math.hypot(u * screen.aspect, v)
    rep.rows.append((label, f"aim at {aim['distance_cm'] / 100:.0f} m", miss, None))
    rep.check("aim", miss <= aim["tolerance"], f"{label}: the arrow line misses the reticle by {miss:.3f} at rest")
    # The legacy -15 degree drawing pitch must not be stacked on the drawn pose.
    su, sv = arrow_screen_point(pose, sockets, contract, screen, extra_pitch=-15.0)
    stacked = math.hypot(su * screen.aspect, sv)
    rep.rows.append((label, "stacked legacy -15 miss", stacked, None))
    rep.check("aim", stacked > aim["tolerance"], f"{label}: stacking the legacy -15 pitch no longer misses; recheck the pose")
    ap = contract["aim_presentation"]
    for yaw, pitch in ap["check_offsets_deg"]:
        ray = rotation(pitch, yaw, 0.0)[0]           # the gameplay ray, eye space
        hud = world.uv(ray)                          # where the HUD ray lands (world camera)
        same = arrow_screen_point(pose, sockets, contract, screen, aim_rows=rotation(pitch, yaw, 0.0))
        corrected = arrow_screen_point(pose, sockets, contract, screen,
                                       aim_rows=aim_rows_toward(screen.direction(*hud), pose))
        e_same, e_corr = screen.distance_uv(same, hud), screen.distance_uv(corrected, hud)
        pts, _ = place(pose["rest"], sockets, pose["anchor"], contract["mesh_scale"], None,
                       aim_rows_toward(screen.direction(*hud), pose))
        for name, p in pts.items():
            rep.check("near-plane", p[0] * screen.scale > screen.near,
                      f"{label} [aim {yaw:+.0f},{pitch:+.0f}]: {name} behind the near plane ({p[0]:.1f} cm)")
        rep.rows.append((label, f"aim offset ({yaw:+.0f},{pitch:+.0f}) same-angle error", e_same, None))
        rep.rows.append((label, f"aim offset ({yaw:+.0f},{pitch:+.0f}) corrected error", e_corr, None))
        rep.check("aim", e_corr <= ap["tolerance"],
                  f"{label}: corrected arrow misses the HUD ray by {e_corr:.3f} at offset ({yaw}, {pitch})")


def status(entry: dict, root: Path):
    """What the current tree records for a weapon (informational; never import or visual status)."""
    rec = entry.get("sockets_from")
    manifest = root / "Content/SourceArt/Weapons/Runtime/manifest.json"
    listed = None
    if manifest.is_file():
        listed = any(w.get("key") == entry.get("key") for w in json.loads(manifest.read_text()).get("weapons", []))
    return {"sockets": "build record" if rec and (root / rec).is_file() else "contract (approximate)",
            "runtime_manifest_listed": listed, "imported_or_visually_qualified": "not established by source"}


def run(contract: dict, root: Path):
    rep = Report()
    for key in BLOCKS:
        rep.check("schema", key in contract, f"missing block {key}")
    if rep.failures:
        return rep, []
    rep.check("schema", contract["schema_version"] == 2, f"schema_version {contract['schema_version']}, expected 2")
    rep.check("schema", "bow_drawing" in contract["motion"] and "pitch_deg" in contract["motion"]
              and "bow_drawing" not in contract["motion"]["pitch_deg"],
              "the drawn bow must replace, not add, a drawing pitch")
    check_catalog(contract, root, rep)
    screen = Screen(contract["camera"])
    world = Screen(contract["camera"], "world_fov_deg")
    statuses = []
    for entry in contract.get("weapons") or []:
        pose_name = entry.get("pose")
        if not rep.check("schema", pose_name in contract["poses"], f"{entry.get('key')}: unknown pose {pose_name}"):
            continue
        sockets = load_sockets(entry, root, rep)
        check_axes(entry, root, rep)
        if sockets is None:
            continue
        for state in entry.get("states", ["rest"]):
            name = pose_name if state == "rest" else f"{pose_name}.{state}"
            if not rep.check("schema", name in contract["poses"], f"{entry.get('key')}: unknown pose {name}"):
                continue
            pose = contract["poses"][name]
            missing = sorted(needed_sockets(pose) - set(sockets))
            if not rep.check("reference", not missing, f"{entry.get('key')} {name}: no sockets {missing}"):
                continue
            check_pose(f"{entry['key']} {name}", pose, sockets, contract, screen, world, rep)
        statuses.append((entry.get("key"), status(entry, root)))
    return rep, statuses


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--table", action="store_true", help="print every checked rest position and aim error")
    ap.add_argument("--contract", type=Path, default=CONTRACT)
    ap.add_argument("--root", type=Path, default=ROOT, help="checkout whose catalog, records and builders to read")
    a = ap.parse_args(argv)
    contract = json.loads(a.contract.read_text())
    rep, statuses = run(contract, a.root.resolve())
    if a.table:
        for label, name, u, v in rep.rows:
            print(f"{label:34s} {name:40s} " + (f"u {u:+.2f} v {v:+.2f}" if v is not None else f"{u:.3f}"))
        for key, st in statuses:
            print(f"status {key}: {st}")
    for f in rep.failures:
        print(f"FRAMING_FAIL {f}", file=sys.stderr)
    counts = ", ".join(f"{k} {v}" for k, v in sorted(rep.counts.items()))
    print(f"VIEWMODEL_FRAMING {'FAIL' if rep.failures else 'PASS'}: {len(contract.get('weapons') or [])} weapons; "
          f"{sum(rep.counts.values())} checks ({counts}); {len(rep.failures)} failures")
    return 1 if rep.failures else 0


if __name__ == "__main__":
    sys.exit(main())
