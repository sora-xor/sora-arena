"""The shells' translucent fragments per hold, on the CPU: how many shell layers the GPU shades at each pixel.

Run with the project's pinned Python (numpy):
  python scripts/art/fp_fur_overdraw.py <capture run dir> [--out <json>]

Root's review of capture v7: the shells' material over ten translucent layers "needs measured performance before
acceptance". scripts/unreal/measure_fp_fur_cost.py times them in the engine. This counts what it is timing.

**What is counted.** A capture's own manifest (render_yumi_fp_review.py) gives each hold's anchor, rotation, draw
and camera, the mesh scale and the resolution. The geometry is the committed source's:
- the shells: nyaakoto_fp_paws.fur_shells at its config;
- the opaque parts they are depth-tested against: the paw's skin (the shells' own 1.6 mm skin), the kote
  (nyaakoto_fp_kote) and the bow (yumi_draw.skinned at the hold's draw).

**The rule.** A shell fragment is counted where a front-facing shell triangle covers a pixel centre nearer than
the opaque depth there:
- Translucent shells write no depth, so every such fragment is shaded and blended. Overlapping shell triangles each
  count, for instance one digit's shells over another's.
- Front-facing means the shell's own normal against the view ray, since the material is one-sided.
- Depth is interpolated linearly on screen. Triangles are rasterised whole: pixel centres, no antialiasing. A
  centre exactly on an edge two triangles share counts once.

Reported per hold:
- the fragments in all and per layer;
- the pixels with any;
- the mean and the most layers at such a pixel.

Review math, not a GPU measurement or an admission.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import yumi_fp_raster as R  # noqa: E402

COMPONENT_DIR = np.array([1.0, -1.0, 1.0])           # bow-metre directions -> component axes (yumi_fp_raster.COMPONENT)
EPS_CM = 0.002                                       # a shell fragment passes this much behind the opaque depth
TIE_X, TIE_Y = 1.17e-6, 2.31e-6                      # the pixel-centre nudge, in pixels


def camera_frame(cam):
    """(location (3,), rows (3, 3): forward, right, up) of a manifest camera record (Unreal rotator, degrees)."""
    p, y, _r = (math.radians(v) for v in cam["rotation_deg"])
    fwd = np.array([math.cos(p) * math.cos(y), math.cos(p) * math.sin(y), math.sin(p)])
    right = np.array([-math.sin(y), math.cos(y), 0.0])
    up = np.array([-math.sin(p) * math.cos(y), -math.sin(p) * math.sin(y), math.cos(p)])
    return np.asarray(cam["location_cm"], np.float64), np.stack([fwd, right, up])


def to_camera(points_m, hold, scale, cam):
    """Bow-metre points (n, 3) -> the hold camera's frame, centimetres (x forward, y right, z up)."""
    loc, M = camera_frame(cam)
    return (R.to_eye(points_m, hold["anchor"], hold["rot"], scale) - loc) @ M.T


def dirs_to_camera(dirs, hold, cam):
    """Bow-metre directions (n, 3) -> the camera's frame (a reflection and rotations, so normals map the same)."""
    _loc, M = camera_frame(cam)
    return ((np.asarray(dirs, np.float64) * COMPONENT_DIR) @ R.rot_rows(hold["rot"])) @ M.T


def _raster(tris_cam, fov, width, height, visit):
    """Each triangle's covered pixel centres, with its depth there: visit(k, ys, xs, depth)."""
    aspect = width / height
    keep = (tris_cam[..., 0] > R.NEAR_CM).all(1)
    px = R.project(tris_cam, fov, aspect, width, height)
    for k in np.nonzero(keep)[0]:
        p, z = px[k], tris_cam[k, :, 0]
        x0, y0 = max(int(math.floor(p[:, 0].min() - 0.5)), 0), max(int(math.floor(p[:, 1].min() - 0.5)), 0)
        x1, y1 = min(int(math.ceil(p[:, 0].max() + 0.5)), width), min(int(math.ceil(p[:, 1].max() + 0.5)), height)
        if x0 >= x1 or y0 >= y1:
            continue
        (ax, ay), (bx, by), (cx, cy) = p
        area = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
        if abs(area) < 1e-12:
            continue
        # Pixel centres nudged off any exact edge, so a centre on an edge two triangles share is counted once, as a
        # GPU's fill rule counts it (the overdraw test's squares put centres on their diagonals).
        X, Y = np.meshgrid(np.arange(x0, x1) + 0.5 + TIE_X, np.arange(y0, y1) + 0.5 + TIE_Y)
        w0 = ((bx - X) * (cy - Y) - (by - Y) * (cx - X)) / area
        w1 = ((cx - X) * (ay - Y) - (cy - Y) * (ax - X)) / area
        w2 = 1.0 - w0 - w1
        inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        if inside.any():
            ys, xs = np.nonzero(inside)
            visit(k, ys + y0, xs + x0, (w0 * z[0] + w1 * z[1] + w2 * z[2])[inside])


def opaque_depth(tris_cam, fov, width, height):
    """(height, width) nearest opaque depth (cm forward), inf where nothing is drawn."""
    depth = np.full((height, width), np.inf)

    def visit(_k, ys, xs, z):
        np.minimum.at(depth, (ys, xs), z)
    _raster(tris_cam, fov, width, height, visit)
    return depth


def shell_fragments(tris_cam, normals_cam, layer_of, layers, depth, fov, width, height):
    """Per layer, the count image of front-facing shell fragments in front of ``depth``."""
    centre = tris_cam.mean(1)
    front = np.einsum("ij,ij->i", normals_cam, centre) < 0.0       # the normal faces back along the view ray
    counts = np.zeros((layers, height, width), np.int32)

    def visit(k, ys, xs, z):
        ok = z < depth[ys, xs] + EPS_CM
        np.add.at(counts[layer_of[k]], (ys[ok], xs[ok]), 1)
    idx = np.nonzero(front)[0]
    _raster(tris_cam[idx], fov, width, height, lambda k, ys, xs, z: visit(idx[k], ys, xs, z))
    return counts


def hold_overdraw(manifest, hold, shells, opaque_m, bow_m):
    """One hold's shell fragments, from a capture manifest's hold, camera, scale and resolution."""
    width, height = manifest["resolution"]
    h, cam, scale = manifest["holds"][hold], manifest["cameras"][hold], manifest["mesh_scale"]
    fov = cam["field_of_view_deg"]
    opaque = np.concatenate([to_camera(opaque_m.reshape(-1, 3), h, scale, cam).reshape(opaque_m.shape),
                             to_camera(bow_m.reshape(-1, 3), h, scale, cam).reshape(bow_m.shape)])
    depth = opaque_depth(opaque, fov, width, height)
    V = to_camera(shells["verts"], h, scale, cam)
    T = shells["tris"]
    N = dirs_to_camera(shells["normals"], h, cam)
    per = len(T) // shells["layers"]
    counts = shell_fragments(V[T], N[T].mean(1), np.arange(len(T)) // per, shells["layers"], depth, fov, width, height)
    total = counts.sum(0)
    lit = total > 0
    return {"resolution": [width, height], "fragments": int(total.sum()),
            "per_layer": [int(c.sum()) for c in counts], "pixels_with_shells": int(lit.sum()),
            "mean_layers": round(float(total[lit].mean()), 3) if lit.any() else 0.0,
            "max_layers": int(total.max()), "opaque_pixels": int(np.isfinite(depth).sum())}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("run", type=Path)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args(argv)
    import nyaakoto_fp_kote as K
    import nyaakoto_fp_paws as P
    import yumi_draw as Y

    manifest = json.loads((a.run / "manifest.json").read_text(encoding="utf-8"))
    skel = P.bow_paw_skeleton()
    base = P.mesh_bow_paw(step=P.SHELLS["step_m"], smooth=6)
    shells = P.fur_shells(skel, lambda p: P.paw_sdf(p, skel)[0], base=base)
    parts, _mon = K.bow_kote(skel)
    opaque_m = np.concatenate([base["verts"][base["tris"]]] +
                              [np.asarray(q["verts"])[np.asarray(q["tris"])] for q in parts])
    rig = Y.load_rig()
    out = {"schema_version": 1, "generator": "scripts/art/fp_fur_overdraw.py", "run": a.run.as_posix(),
           "layers": shells["layers"], "shell_triangles": int(len(shells["tris"])), "holds": {},
           "scope": "CPU count of the shells' translucent fragments: review math, not a GPU measurement"}
    for hold in manifest["holds"]:
        bow_m = Y.skinned(rig, manifest["holds"][hold]["draw"])[rig["tris"]]
        out["holds"][hold] = hold_overdraw(manifest, hold, shells, opaque_m, bow_m)
        print(hold, json.dumps(out["holds"][hold]), flush=True)
    if a.out:
        with open(a.out, "x", encoding="utf-8") as fh:
            fh.write(json.dumps(out, indent=1) + "\n")
    return out


if __name__ == "__main__":
    main()
