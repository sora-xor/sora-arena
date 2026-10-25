"""The first-person yumi's screen pixels on the CPU: the whole skinned stave and the arrow, not their sockets.

Numpy and PIL. render_yumi_fp_review.py's ID pass counts the bow's real pixels
in the reticle's clear disc. This computes the same count for any hold,
without an engine, so a hold can be designed before it is captured. Capture
v3 showed that socket math alone (the clear line) is not enough: the root and
right_cheek holds clear the 0.12 radius by their line, yet the stave covers
1,330 and 4,956 of the disc's 13,200 pixels.

**The geometry:**
- The bow is the rig's own skinned mesh at the hold's draw fraction
  (yumi_draw.skinned, the checker's deformation). The string is included,
  because it is part of the mesh.
- The arrow is the committed ya, nocked at the posed Grip_R and laid through
  the posed Muzzle, as the capture lays it.
- The paw is the bow paw's skin and kote (nyaakoto_fp_paws, nyaakoto_fp_kote)
  at a 2 mm step, in the Grip_L frame the capture attaches it in. The fur
  cards' few millimetres are left out.
- Each part is rasterised alone, so a part hidden behind another still
  counts. The capture's ID image shows only the front part, so the two agree
  wherever nothing overlaps, as in the reticle disc.
- Both are placed as yumi_fp_holds places sockets. Component centimetres are
  100 x (x, -y, z) of bow metres. Then anchor + rotation(rot) x (mesh_scale x
  component).

**The camera** is the capture's eye view: the origin, looking down +X, with
a horizontal FOV and aspect, and triangles clipped at the near plane
(yumi_draw._clip_near). Pixel (i, j) has its centre at ((i + 0.5) / W,
(j + 0.5) / H), as analyse_yumi_fp_review measures.

**Rasterised** with PIL's polygon fill: whole-pixel coverage, no
antialiasing. So it differs from a TSR-resolved ID image by up to a pixel at
every edge. validate_against_capture() reports how far it differs.

Review math, not an admission.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import yumi_draw as Y  # noqa: E402
import yumi_fp_holds as H  # noqa: E402

NEAR_CM = 10.0
COMPONENT = np.array([100.0, -100.0, 100.0])          # bow metres -> component centimetres (Unreal axes)


def rot_rows(rot):
    return np.array(H.rotation(*rot), np.float64)


def to_eye(points_m, anchor, rot, scale):
    """Bow-metre points (n, 3) -> eye centimetres, as yumi_fp_holds.place places a socket."""
    comp = np.asarray(points_m, np.float64) * COMPONENT
    return np.asarray(anchor, np.float64) + (scale * comp) @ rot_rows(rot)


def posed_sockets_m(rig, draw=1.0):
    """Grip_R (the String_Nock bone's posed head) and the Muzzle (fixed on Grip), in bow metres."""
    M = Y._deform_at(rig, draw)
    names = [str(n) for n in rig["bones"]]
    nock_bone = names.index("String_Nock")
    head = rig["bind"][nock_bone][:3, 3]
    grip_r = M[nock_bone][:3, :3] @ head + M[nock_bone][:3, 3]
    muzzle = np.array([0.01475, -0.01975, 0.07])                    # rig_record: Muzzle on Grip, Grip at rest
    return grip_r, muzzle


def eye_triangles(rig, anchor, rot, scale, draw=1.0, arrow=True, paw=True):
    """{"bow": (n, 3, 3), "arrow": (m, 3, 3), "paw": (k, 3, 3)} triangles in eye centimetres."""
    verts = Y.skinned(rig, draw)
    out = {"bow": to_eye(verts, anchor, rot, scale)[rig["tris"]]}
    if arrow:
        grip_r, muzzle = posed_sockets_m(rig, draw)
        av = Y.arrow_at(rig, grip_r, muzzle)
        out["arrow"] = to_eye(av, anchor, rot, scale)[rig["arrow_tris"]]
    if paw:
        pt = paw_triangles_m()
        out["paw"] = to_eye(pt.reshape(-1, 3), anchor, rot, scale).reshape(pt.shape)
    return out


_PAW_CACHE = {}


def paw_triangles_m(step=0.002):
    """The bow paw's skin and its kote, (n, 3, 3) in bow metres: the Grip_L socket frame the capture attaches it in
    (nyaakoto_fp_paws, nyaakoto_fp_kote; the fur cards' few millimetres are left out). Cached per step."""
    if step not in _PAW_CACHE:
        import nyaakoto_fp_kote as K
        import nyaakoto_fp_paws as P

        m = P.mesh_bow_paw(step=step, smooth=3)
        tris = [m["verts"][m["tris"]]]
        parts, _mon = K.bow_kote(m["skeleton"])
        tris += [np.asarray(part["verts"])[np.asarray(part["tris"])] for part in parts]
        _PAW_CACHE[step] = np.concatenate(tris).astype(np.float64)
    return _PAW_CACHE[step]


def project(points, fov_h_deg, aspect, width, height):
    """Eye points (..., 3), in front of the camera -> pixel coordinates (..., 2), x right, y down."""
    tan_h = math.tan(math.radians(fov_h_deg / 2.0))
    tan_v = tan_h / aspect
    u = (points[..., 1] / points[..., 0]) / tan_h
    v = (points[..., 2] / points[..., 0]) / tan_v
    return np.stack([(u + 1.0) * 0.5 * width, (1.0 - v) * 0.5 * height], axis=-1)


def raster(tris_eye, fov_h_deg, aspect, width, height, near_cm=NEAR_CM):
    """(H, W) bool: the pixels the triangles cover, clipped at the near plane."""
    from PIL import Image, ImageDraw

    tris, _cuts = Y._clip_near(np.asarray(tris_eye, np.float64), near_cm)
    img = Image.new("1", (width, height), 0)
    if len(tris):
        px = project(tris, fov_h_deg, aspect, width, height)
        lo, hi = px.min(axis=1), px.max(axis=1)
        keep = (hi[:, 0] >= -1) & (lo[:, 0] <= width + 1) & (hi[:, 1] >= -1) & (lo[:, 1] <= height + 1)
        draw = ImageDraw.Draw(img)
        for t in px[keep]:
            # PIL fills a polygon's pixels by their integer coordinates: shift by half a pixel so pixel centres decide.
            draw.polygon([(float(x) - 0.5, float(y) - 0.5) for x, y in t], fill=1)
    return np.asarray(img, dtype=bool)


def disc(width, height, radius):
    """(H, W) bool: the reticle's clear disc, radius in half-heights (analyse_yumi_fp_review.analyse)."""
    yy, xx = np.mgrid[0:height, 0:width]
    u = (xx + 0.5 - width / 2) / (width / 2)
    v = -(yy + 0.5 - height / 2) / (height / 2)
    return np.hypot(u * (width / height), v) <= radius


def clearance(mask, width, height):
    """The covered pixels' least distance from the frame centre, in half-heights (inf when nothing is covered)."""
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return float("inf")
    u = (xs + 0.5 - width / 2) / (width / 2)
    v = -(ys + 0.5 - height / 2) / (height / 2)
    return float(np.hypot(u * (width / height), v).min())


def hold_pixels(rig, anchor, rot, scale, camera, width, height, draw=1.0):
    """Per part: pixels, pixels in the disc, and clearance, for one hold. ``camera``: the study's camera."""
    fov, aspect = camera["first_person_fov_deg"], camera["aspect"][0] / camera["aspect"][1]
    d = disc(width, height, camera["reticle_clear_radius"])
    out = {}
    for part, tris in eye_triangles(rig, anchor, rot, scale, draw).items():
        m = raster(tris, fov, aspect, width, height, camera.get("near_plane_cm", NEAR_CM))
        out[part] = {"pixels": int(m.sum()), "in_disc": int((m & d).sum()), "clearance": clearance(m, width, height),
                     "mask": m}
    out["disc_pixels"] = int(d.sum())
    return out
