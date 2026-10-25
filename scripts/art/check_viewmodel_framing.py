#!/usr/bin/env python3
"""Screen framing of the first-person viewmodel contract (Content/Data/viewmodels.json).

  python3 scripts/art/check_viewmodel_framing.py [--table]

For every weapon and pose in the contract, this projects the weapon's sockets
into the first-person view. The weapon is held at its pose's rest transform,
with the contract's mesh scale. Sockets come from the weapon's build record,
or from the contract where a mesh has none yet. The checks:

* the pose's visible sockets fall inside its screen box;
* the blade, shaft or barrel keeps clear of the reticle zone (the line from the
  anchor to the business end, sampled);
* a drawn bow's arrow line reaches the reticle at the aim distance;
* every socket is in front of the near plane after FirstPersonScale.

These checks are the pinhole math of UE's first-person projection (horizontal
FOV and aspect; FirstPersonScale moves points along their rays, so not on
screen). They check framing only, and they never replace real first-person
captures. Exit 1 on any failure. Pure Python.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "Content/Data/viewmodels.json"


def rotation(pitch: float, yaw: float, roll: float):
    """UE FRotationMatrix rows: the rotated X, Y and Z axes."""
    sp, cp = math.sin(math.radians(pitch)), math.cos(math.radians(pitch))
    sy, cy = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
    sr, cr = math.sin(math.radians(roll)), math.cos(math.radians(roll))
    return ((cp * cy, cp * sy, sp),
            (sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp),
            (-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp))


def to_ue_cm(metres):
    """A socket from Blender metres (+Y the wielder's left) to UE centimetres (+Y right)."""
    x, y, z = metres
    return (100.0 * x, -100.0 * y, 100.0 * z)


def place(rest: dict, sockets: dict, anchor: str, scale: float):
    """Eye-space positions (cm; X forward, Y right, Z up) of every socket."""
    axes = rotation(*rest["rotation_deg"])
    origin = rest["anchor_cm"]
    a = to_ue_cm(sockets[anchor])
    out = {}
    for name, metres in sockets.items():
        p = [scale * (c - ac) for c, ac in zip(to_ue_cm(metres), a)]
        out[name] = tuple(origin[i] + sum(p[k] * axes[k][i] for k in range(3)) for i in range(3))
    return out


class Screen:
    def __init__(self, camera: dict):
        self.tan_h = math.tan(math.radians(camera["first_person_fov_deg"] / 2.0))
        aw, ah = camera["aspect"]
        self.aspect = aw / ah
        self.tan_v = self.tan_h / self.aspect
        self.scale = camera["first_person_scale"]
        self.near = camera["near_plane_cm"]
        self.clear = camera["reticle_clear_radius"]

    def uv(self, p):
        x, y, z = p
        return (y / x) / self.tan_h, (z / x) / self.tan_v

    def reticle_distance(self, p):
        """Distance from the screen centre, in half-heights."""
        u, v = self.uv(p)
        return math.hypot(u * self.aspect, v)


def check_pose(label, pose, sockets, contract, screen, failures, rows):
    rest = pose["rest"]
    pts = place(rest, sockets, pose["anchor"], contract["mesh_scale"])
    for name, p in pts.items():
        if p[0] * screen.scale <= screen.near:
            failures.append(f"{label}: {name} is behind the near plane ({p[0]:.1f} cm)")
    for name, box in pose.get("screen", {}).items():
        if name not in pts:
            failures.append(f"{label}: no socket {name}")
            continue
        u, v = screen.uv(pts[name])
        (u0, u1), (v0, v1) = box["u"], box["v"]
        rows.append((label, name, u, v))
        if not (u0 <= u <= u1 and v0 <= v <= v1):
            failures.append(f"{label}: {name} at u {u:+.2f}, v {v:+.2f}, outside u {box['u']} v {box['v']}")
    line = pose.get("clear_line")
    if line:
        a, b = pts[line[0]], pts[line[1]]
        worst = min(screen.reticle_distance(tuple(a[i] + (b[i] - a[i]) * t / 20 for i in range(3))) for t in range(21))
        rows.append((label, f"{line[0]}-{line[1]} reticle gap", worst, None))
        if worst < screen.clear:
            failures.append(f"{label}: {line[0]}-{line[1]} comes {worst:.3f} half-heights from the reticle "
                            f"(needs {screen.clear})")
    aim = pose.get("aim_line")
    if aim:
        axes = rotation(*rest["rotation_deg"])
        start = pts[aim["from"]]
        far = tuple(start[i] + aim["distance_cm"] * axes[0][i] for i in range(3))
        miss = screen.reticle_distance(far)
        rows.append((label, f"aim at {aim['distance_cm'] / 100:.0f} m", miss, None))
        if miss > aim["tolerance"]:
            failures.append(f"{label}: the arrow line misses the reticle by {miss:.3f} half-heights at "
                            f"{aim['distance_cm'] / 100:.0f} m")


def sockets_for(entry: dict) -> dict:
    """The weapon mesh's sockets in Blender metres: from its build record, or the contract."""
    if "sockets_m" in entry:
        return entry["sockets_m"]
    record = json.loads((ROOT / entry["sockets_from"]).read_text())
    return record["assets"][entry["first_person_mesh"].rsplit("/", 1)[-1]]["sockets"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--table", action="store_true", help="print every checked socket's screen position")
    ap.add_argument("--contract", type=Path, default=CONTRACT)
    a = ap.parse_args(argv)
    contract = json.loads(a.contract.read_text())
    screen = Screen(contract["camera"])
    failures, rows = [], []
    for entry in contract["weapons"]:
        sockets = sockets_for(entry)
        for state in entry.get("states", ["rest"]):
            pose_name = entry["pose"] if state == "rest" else f"{entry['pose']}.{state}"
            check_pose(f"{entry['key']} {pose_name}", contract["poses"][pose_name], sockets, contract,
                       screen, failures, rows)
    if a.table:
        for label, name, u, v in rows:
            print(f"{label:34s} {name:26s} " + (f"u {u:+.2f} v {v:+.2f}" if v is not None else f"{u:.3f}"))
    for f in failures:
        print(f"FRAMING_FAIL {f}", file=sys.stderr)
    print(f"VIEWMODEL_FRAMING {'FAIL' if failures else 'PASS'}: {len(contract['weapons'])} weapons, "
          f"{len(rows)} checks, {len(failures)} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
