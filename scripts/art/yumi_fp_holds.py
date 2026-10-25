"""First-person review holds for the drawn yumi, solved from its posed sockets.

Pure math, with no numpy and no Unreal. Unreal's Python
(render_yumi_fp_review.py) and the host tests both import it, so a capture
solves its holds from the sockets it actually poses: after a rebuild, the
rebuilt ones.

**Conventions:** check_viewmodel_framing's.
- Eye space is centimetres: X forward, Y right, Z up, the camera at the
  origin looking down +X.
- A hold places the bow's mesh (Grip_L at its origin) at ``anchor``, turned
  by the Unreal FRotator ``rot`` (pitch, yaw, roll in degrees, as
  FRotationMatrix rows) and scaled by mesh_scale.
- A posed socket is anchor + rotate(rot, scale x socket).

**right_cheek** is Codex's construction
(Saved/Qualification/2026-10-25/yumi-right-cheek-study/candidate.json):
- keep the control hold's full-draw nock X and Z and mirror its Y, so the
  nock sits as far right of the eye as the control's sits left;
- turn the bow, roll 0, until the posed nock-to-Muzzle arrow line passes
  through the aim point (AIM_CM, 20 m ahead on the view axis);
- place the anchor so the posed nock lands on that target.
It is socket math only. Real originals decide paw and stave pixels,
near-plane clipping, reticle occlusion and how it reads.
"""
from __future__ import annotations

import math

AIM_CM = (2000.0, 0.0, 0.0)


def rotation(pitch, yaw, roll):
    """Unreal FRotationMatrix rows: the rotated X, Y and Z axes."""
    sp, cp = math.sin(math.radians(pitch)), math.cos(math.radians(pitch))
    sy, cy = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
    sr, cr = math.sin(math.radians(roll)), math.cos(math.radians(roll))
    return ((cp * cy, cp * sy, sp),
            (sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp),
            (-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp))


def apply(rows, v):
    """v in the rotated frame ``rows`` -> parent coordinates."""
    return tuple(sum(v[k] * rows[k][i] for k in range(3)) for i in range(3))


def place(anchor, rot, scale, socket_cm):
    """A mesh socket (cm, component space, Grip_L at the origin) in eye space."""
    d = apply(rotation(*rot), tuple(scale * c for c in socket_cm))
    return tuple(anchor[i] + d[i] for i in range(3))


def _unit(v):
    n = math.sqrt(sum(c * c for c in v))
    return tuple(c / n for c in v)


def solve_aim(d_mesh, direction):
    """(pitch, yaw) in degrees, roll 0, turning the mesh direction ``d_mesh`` onto ``direction``.

    With roll 0, the rows give R d = (k cy - b sy, k sy + b cy, a sp + c cp),
    where (a, b, c) = unit(d_mesh) and k = a cp - c sp. So the pitch solves
    the Z component, and the yaw turns (k, b) onto the target's X and Y."""
    a, b, c = _unit(d_mesh)
    ux, uy, uz = _unit(direction)
    r = math.hypot(a, c)
    p = math.asin(max(-1.0, min(1.0, uz / r))) - math.atan2(c, a)
    k = a * math.cos(p) - c * math.sin(p)
    y = math.atan2(uy, ux) - math.atan2(b, k)
    return math.degrees(p), math.degrees(y)


def aim_miss(nock, muzzle, aim=AIM_CM):
    """(dy, dz) cm: where the nock-to-Muzzle line crosses x = aim X, less the aim point."""
    t = (aim[0] - nock[0]) / (muzzle[0] - nock[0])
    return (nock[1] + t * (muzzle[1] - nock[1]) - aim[1], nock[2] + t * (muzzle[2] - nock[2]) - aim[2])


def right_cheek(control_anchor, control_rot, scale, grip_r_cm, muzzle_cm, aim=AIM_CM):
    """The right_cheek hold for full-draw sockets grip_r_cm and muzzle_cm (cm, component space)."""
    nock_control = place(control_anchor, control_rot, scale, grip_r_cm)
    target = (nock_control[0], -nock_control[1], nock_control[2])
    d_mesh = tuple(m - g for m, g in zip(muzzle_cm, grip_r_cm))
    pitch, yaw = solve_aim(d_mesh, tuple(aim[i] - target[i] for i in range(3)))
    rot = (pitch, yaw, 0.0)
    nock_rel = apply(rotation(*rot), tuple(scale * c for c in grip_r_cm))
    anchor = tuple(target[i] - nock_rel[i] for i in range(3))
    posed = {"Grip_R": place(anchor, rot, scale, grip_r_cm), "Muzzle": place(anchor, rot, scale, muzzle_cm),
             "Grip_L": tuple(anchor)}
    return {"anchor": anchor, "rot": rot, "control_nock": nock_control, "target_nock": target, "posed": posed,
            "aim_miss_cm": aim_miss(posed["Grip_R"], posed["Muzzle"], aim)}


def screen_uv(p, fov_h_deg, aspect):
    """Pinhole screen coordinates in half-widths and half-heights, as check_viewmodel_framing.Screen.uv."""
    tan_h = math.tan(math.radians(fov_h_deg / 2.0))
    tan_v = tan_h / aspect
    return (p[1] / p[0]) / tan_h, (p[2] / p[0]) / tan_v


def in_box(uv, box):
    return box["u"][0] <= uv[0] <= box["u"][1] and box["v"][0] <= uv[1] <= box["v"][1]


def segment_behind(p0, p1, near_cm):
    """The fraction of segment p0-p1 nearer the eye than the near plane (eye X below near_cm)."""
    x0, x1 = p0[0], p1[0]
    if x0 >= near_cm and x1 >= near_cm:
        return 0.0
    if x0 < near_cm and x1 < near_cm:
        return 1.0
    t = (near_cm - x0) / (x1 - x0)
    return t if x0 < near_cm else 1.0 - t
