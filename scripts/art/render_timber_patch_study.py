"""The focused v2.3 timber patch study: one column and one rail against the CC0 hinoki and sugi scans, at physical scale.

Run (Blender 5.2.2, the pinned CPU path):
  blender -b --factory-startup --python-exit-code 1 --python scripts/art/render_timber_patch_study.py -- --cpu \
      --raw <ThirdPartyRaw root> [--samples 128]

Root's review of the v2.2 originals asked for one representative column and
rail, iterated against real close-up wood at the same physical scale, before
another complete batch, with ring, fibre and check character visible in clay
and grazing views as well as in the material. This is that study.

- **Members:** dojo_timber_pilot.pilot_members()'s wall column and nuki, built
  with sora_timber_v2 (sora-timber-geometry-v2.3) and checked with check_mesh,
  as the pilot builds them. Nothing is exported.
- **Patches:** fronto-parallel orthographic views of each room face:
  - the column's GrainClose region, 140 mm across the grain by 200 mm along;
  - the nuki's adzed face, 100 mm across by 240 mm along.
- **Pitch:** the sugi scan's 0.2759 mm per pixel, the finer of the two scans'
  (timber_scan_reference.json). Base colour is also rendered at the hinoki
  scan's 0.4614 mm.
- **Views:**
  - Clay_GrazeAcross and Clay_GrazeAlong: grey clay under a sun 10 degrees off
    the face, travelling across or along the grain, so the geometry alone
    shows its relief;
  - <Variant>_GrazeAcross and <Variant>_Soft: the v2 look-dev material under
    the same grazing sun, or a soft sky with a 45-degree key;
  - <Variant>_BaseColor_<pitch>: the material's base colour as emission,
    Standard view, for the measurement;
  - <Variant>_Normal: the shading normal (geometry and bump) as emission,
    Raw view, in camera space, written as EXR.
- **Variants:**
  - **v23:** the look-dev preset as built (column_fukiurushi).
  - **scan_contrast:** the same, with the late colour moved toward the early
    colour by alpha = (1 - 1/r_t) / (1 - 1/r_0). Here r_0 is v23's measured
    early-over-late base-colour luminance and r_t is the scans' mean. This
    assumes latewood luminance is linear in the late colour, and the run
    measures the result. Aged and urushi-wiped wood loses ring contrast, so
    the fresh scans' ratio is an upper bound, not a match to tune toward.
- **Measurements:**
  - base colour: timber_scan_reference.analyse on each base-colour render,
    beside the scans' reference;
  - across-grain slope: band RMS of the shading normal's across-grain slope,
    in the ring and fibre bands, for each variant and for each scan's normal
    map (DX EXR, read here because Blender decodes its DWA compression).
    Poly Haven's normal strength is a processing choice, so slopes compare as
    an order of magnitude only.
  - a render's slope is decoded by camera_normal_slope: Cycles' camera space
    looks along +z, so a face toward the camera has z near -1. The render
    must be unit normals facing the camera, or the study stops. Attempt 0
    divided by +z clamped at 1e-3, which made every render slope 1000 times
    its value; its scans' slopes were right.
- **Re-analysis** (--reanalyse <attempt>): the slopes again from an attempt's
  retained renders, each checked against the hash its study.json recorded.
  Nothing is rendered, and nothing in the attempt is written: the result goes
  to a new <attempt>_reanalysis<N>/slope_reanalysis.json, created
  exclusively.
- **Contact sheets:** one per patch, at the sugi pitch, every panel the same
  physical size. Left to right:
  - the hinoki crop and the sugi crop (base colour), each centred between
    the two seams farthest apart (a sugi plank is 80 mm wide, so its crop
    spans seams);
  - v23's and scan_contrast's base colour;
  - then v23 and scan_contrast, each Soft and then GrazeAcross;
  - then Clay GrazeAcross and Clay GrazeAlong.

Everything goes to Local/ArtCache/NyaagyuDojoTimbersV23Patch/<attempt>/,
created exclusively; nothing else is written. These are review images, not
an admission, and not photoreal.
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import camera_normal_slope as CN  # noqa: E402
import create_nyaagyu_dojo_rails as RG  # noqa: E402
import create_nyaagyu_dojo_timbers as TG  # noqa: E402
import create_runtime_weapon_lib as L  # noqa: E402
import dojo_timber_pilot as PILOT  # noqa: E402
import sora_prop_lib as PL  # noqa: E402
import sora_timber_lib as T  # noqa: E402
import sora_timber_lookdev as LD  # noqa: E402
import sora_timber_lookdev_v2 as LD2  # noqa: E402
import sora_timber_v2 as V  # noqa: E402
import timber_scan_reference as R  # noqa: E402

GEN = "scripts/art/render_timber_patch_study.py"
INPUTS = (GEN, "scripts/art/camera_normal_slope.py", "scripts/art/timber_scan_reference.py", "scripts/art/sora_timber_v2.py",
          "scripts/art/dojo_timber_pilot.py", "scripts/art/sora_timber_lookdev_v2.py", "scripts/art/sora_timber_lookdev.py",
          "scripts/art/sora_timber_lib.py", "scripts/art/create_nyaagyu_dojo_rails.py",
          "scripts/art/create_nyaagyu_dojo_timbers.py", "docs/art-direction/data/timber_scan_reference.json")
OUT = L.ROOT / "Local/ArtCache/NyaagyuDojoTimbersV23Patch"
REFERENCE = L.ROOT / "docs/art-direction/data/timber_scan_reference.json"
SCANS = ("hinoki_planks", "japanese_cedar_planks")
PRESET = "column_fukiurushi"
GRAZE_DEG = 10.0
GRAZE_SUN = 20.0           # W/m^2: clay (0.30) at sin(10 deg) reads about 0.33
MATERIAL_EXPOSURE = 2.5    # stops: the aged timber's albedo is about 0.05
# (member kind, patch name, centre (m, kit or bay frame), across axis, along axis, across mm, along mm)
PATCHES = (
    ("wall", "Column", (0.02, TG.COL_CENTRE_Y - TG.COL / 2, 1.45), "x", "z", 140.0, 200.0),
    ("Nuki", "Nuki", (0.0, RG.RAILS["Nuki"][2], (RG.RAILS["Nuki"][0] + RG.RAILS["Nuki"][1]) / 2), "z", "x", 100.0, 240.0),
)
AXIS = {"x": Vector((1.0, 0.0, 0.0)), "z": Vector((0.0, 0.0, 1.0))}


def guard(path: Path) -> Path:
    p = Path(path).resolve()
    out = OUT.resolve()
    if p != out and out not in p.parents:
        raise ValueError(f"patch study: refusing to write outside {OUT}: {p}")
    return p


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "--reanalyse" in argv:
        return {"reanalyse": Path(argv[argv.index("--reanalyse") + 1])}
    o = {"cpu": "--cpu" in argv, "samples": 128, "raw": None}
    if "--samples" in argv:
        o["samples"] = int(argv[argv.index("--samples") + 1])
    if "--raw" in argv:
        o["raw"] = Path(argv[argv.index("--raw") + 1])
    if o["raw"] is None:
        raise SystemExit("patch study: --raw <ThirdPartyRaw root> is required (the scans' cache)")
    return o


def attempt_dir():
    OUT.mkdir(parents=True, exist_ok=True)
    n = 0
    while (OUT / f"attempt{n}").exists():
        n += 1
    d = guard(OUT / f"attempt{n}")
    d.mkdir(exist_ok=False)
    return d


def read_pixels(path: Path):
    """An image's raw values as (H, W, C) float32, top row first, with no colour transform."""
    img = bpy.data.images.load(str(path), check_existing=False)
    img.colorspace_settings.name = "Non-Color"
    w, h, c = img.size[0], img.size[1], img.channels
    if w == 0 or h == 0:
        raise RuntimeError(f"patch study: could not decode {path}")
    px = np.empty(w * h * c, np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(h, w, c)[::-1]


def build_members(arrays):
    built = {}
    for m, fam, kind, rec in PILOT.pilot_members():
        if kind not in {p[0] for p in PATCHES}:
            continue
        t0 = time.time()
        B = V.build(m, arrays)
        report = V.check_mesh(B, m)
        if not report["ok"]:
            raise SystemExit(f"patch study: {m.name} fails its mesh checks: {report['failures']}")
        obj = V.to_blender(m.name, B, m)
        if fam == "rail":
            RG.lay_down(obj, m, kind)
        built[kind] = {"member": m, "obj": obj, "digest": V.canonical_digest(obj),
                       "triangles": len(obj.data.polygons), "seconds": round(time.time() - t0, 1)}
        print("PATCH_MEMBER", m.name, built[kind]["triangles"], built[kind]["seconds"], flush=True)
    return built


def variant_preset(name, late):
    """A runtime-only copy of the look-dev preset with another late colour (the file is unchanged)."""
    key = f"{PRESET}__{name}"
    P = dict(LD.PRESETS[PRESET])
    P["late"] = tuple(float(c) for c in late)
    LD.PRESETS[key] = P
    return key


def emission_of(mat, socket_name, name):
    """A copy of ``mat`` whose surface is the emission of what feeds its BSDF's ``socket_name``."""
    m = mat.copy()
    m.name = name
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = 1.0
    src = bsdf.inputs[socket_name]
    if socket_name == "Normal":
        # Camera-space shading normal, encoded n * 0.5 + 0.5.
        vt = nt.nodes.new("ShaderNodeVectorTransform")
        vt.vector_type, vt.convert_from, vt.convert_to = "NORMAL", "WORLD", "CAMERA"
        if src.is_linked:
            nt.links.new(src.links[0].from_socket, vt.inputs["Vector"])
        else:
            geo = nt.nodes.new("ShaderNodeNewGeometry")
            nt.links.new(geo.outputs["Normal"], vt.inputs["Vector"])
        enc = nt.nodes.new("ShaderNodeVectorMath")
        enc.operation = "MULTIPLY_ADD"
        enc.inputs[1].default_value = (0.5, 0.5, 0.5)
        enc.inputs[2].default_value = (0.5, 0.5, 0.5)
        nt.links.new(vt.outputs["Vector"], enc.inputs[0])
        nt.links.new(enc.outputs["Vector"], em.inputs["Color"])
    elif src.is_linked:
        nt.links.new(src.links[0].from_socket, em.inputs["Color"])
    else:
        em.inputs["Color"].default_value = src.default_value
    for link in list(out.inputs["Surface"].links):
        nt.links.remove(link)
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return m


def set_world(scene, strength):
    world = scene.world or bpy.data.worlds.new("TP_World")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    bg.inputs["Strength"].default_value = strength
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])


def sun(direction, strength, size_deg=0.53):
    PL._clear_lights()
    s = PL._light("TP_Sun", "SUN", (0.0, 0.0, 5.0), (0.0, 0.0, 0.0), strength, size=size_deg)   # degrees
    s.rotation_euler = direction.normalized().to_track_quat("-Z", "Y").to_euler()
    return s


def rig(scene, kind, across, along):
    """``kind``: GrazeAcross, GrazeAlong, Soft or Emission. The faces look toward -Y."""
    into = Vector((0.0, 1.0, 0.0))
    e = math.radians(GRAZE_DEG)
    if kind in ("GrazeAcross", "GrazeAlong"):
        t = across if kind == "GrazeAcross" else along
        sun(t * math.cos(e) + into * math.sin(e), GRAZE_SUN)
        set_world(scene, 0.02)
    elif kind == "Soft":
        sun((into + Vector((0.4, 0.0, -0.6))).normalized(), 2.0, size_deg=8.0)
        set_world(scene, 1.0)
    else:
        PL._clear_lights()
        set_world(scene, 0.0)


def camera(scene, centre, across, along, across_mm, along_mm, face_y, pitch_mm):
    cam = bpy.data.objects.get("TP_Cam")
    if cam is None:
        cam = bpy.data.objects.new("TP_Cam", bpy.data.cameras.new("TP_Cam"))
        scene.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.sensor_fit = "AUTO"
    cam.data.clip_start, cam.data.clip_end = 0.01, 5.0
    cam.location = Vector((centre[0], face_y - 0.5, centre[2]))
    cam.rotation_euler = Vector((0.0, 1.0, 0.0)).to_track_quat("-Z", "Y").to_euler()   # image right +X, up +Z
    wide = across_mm if across.x else along_mm          # image width runs along X
    tall = along_mm if across.x else across_mm
    cam.data.ortho_scale = max(wide, tall) / 1000.0
    scene.camera = cam
    scene.render.resolution_x = int(round(wide / pitch_mm))
    scene.render.resolution_y = int(round(tall / pitch_mm))
    scene.render.resolution_percentage = 100
    return cam


def render(scene, path: Path, samples, view, exposure, fmt="PNG", depth="8", denoise=False):
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = denoise
    scene.view_settings.view_transform = view
    scene.view_settings.look = "None"
    scene.view_settings.exposure = exposure
    scene.view_settings.gamma = 1.0
    s = scene.render.image_settings
    s.file_format = fmt
    s.color_depth = depth
    if fmt == "OPEN_EXR":
        s.exr_codec = "ZIP"
    scene.render.filepath = str(guard(path))
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print("PATCH_RENDER", L.rel(path), round(time.time() - t0, 1), flush=True)
    return {"file": L.rel(path), "sha256": L.sha256(path), "seconds": round(time.time() - t0, 1)}


def face_plane(obj, centre, across_mm, along_mm, across_axis):
    """The face's room-side envelope (its 1st percentile y) inside the patch, and the patch's vertices."""
    co = np.empty(len(obj.data.vertices) * 3)
    obj.data.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    a = 0 if across_axis == "x" else 2
    l = 2 if across_axis == "x" else 0
    sel = ((np.abs(co[:, a] - centre[a]) < across_mm / 2000.0) & (np.abs(co[:, l] - centre[l]) < along_mm / 2000.0)
           & (np.abs(co[:, 1] - centre[1]) < 0.01))
    if sel.sum() < 100:
        raise RuntimeError(f"patch study: only {int(sel.sum())} face vertices in the patch at {centre}")
    return float(np.percentile(co[sel, 1], 1.0)), co[sel]


def slope_stats(slope, lum, mm):
    """Band RMS of across-grain slope profiles, over the windows the base-colour analysis keeps:
    the same layout and seam keep-out, and the same orientation test on the luminance."""
    gx = float((np.diff(lum, axis=1) ** 2).mean())
    gy = float((np.diff(lum, axis=0) ** 2).mean())
    if not gx < gy:
        slope, lum = slope.T, lum.T
    rows = R.seams(np.median(lum, axis=1), mm)
    keep_out = int(np.ceil(R.SEAM_KEEP_OUT_MM / mm))
    blocked = np.zeros(lum.shape[0], bool)
    for s_ in rows:
        blocked[max(0, s_ - keep_out): s_ + keep_out + 1] = True
    wa, wl = int(round(R.WINDOW_ACROSS_MM / mm)), int(round(R.WINDOW_ALONG_MM / mm))
    sa, sl = int(round(R.STEP_ACROSS_MM / mm)), int(round(R.STEP_ALONG_MM / mm))
    ring, fibre = [], []
    for a0 in range(0, lum.shape[0] - wa, sa):
        if blocked[a0: a0 + wa].any():
            continue
        for l0 in range(0, lum.shape[1] - wl, sl):
            win = lum[a0: a0 + wa, l0: l0 + wl]
            g_across = np.diff(win, axis=0)[:, :-1]
            g_along = np.diff(win, axis=1)[:-1, :]
            jaa, jll, jal = (g_across ** 2).sum(), (g_along ** 2).sum(), (g_across * g_along).sum()
            tr = jaa + jll
            if tr <= 0.0:
                continue
            coherence = np.sqrt((jaa - jll) ** 2 + 4.0 * jal ** 2) / tr
            angle = 0.5 * np.degrees(np.arctan2(2.0 * jal, jaa - jll))
            if coherence < R.COHERENCE_MIN or abs(angle) > R.ORIENT_MAX_DEG:
                continue
            p = slope[a0: a0 + wa, l0: l0 + wl].mean(axis=1)
            ring.append(R.band_rms(p, mm, R.RING_BAND_MM))
            fibre.append(R.band_rms(p, mm, R.FIBRE_BAND_MM))

    def pct(v):
        return {f"p{q}": round(float(np.percentile(v, q)), 5) for q in (10, 50, 90)} if v else None

    return {"windows": len(ring), "ring_band_rms": pct(ring), "fibre_band_rms": pct(fibre)}


def render_slope_stats(npath, base_png, ax, mm):
    """(normal check, slope statistics) of one normal render, over the windows its base-colour render keeps.
    Across the grain is image x for the column (world x) and image y for the nuki (world z)."""
    slope, check = CN.across_slope(CN.decode(read_pixels(npath)), "x" if ax == "x" else "y")
    lum = R.srgb_to_linear(read_pixels(base_png)[..., :3].astype(np.float64)) @ R.REC709
    return check, slope_stats(slope, lum, mm)


def reanalyse(attempt: Path):
    """The slopes again from a finished attempt's retained renders; see the module's Re-analysis."""
    attempt = guard(attempt if attempt.is_absolute() else L.ROOT / attempt)
    study_path = attempt / "study.json"
    study_sha = L.sha256(study_path)
    study = json.loads(study_path.read_text(encoding="utf-8"))
    fine = min(study["pitch_mm"].values())
    record = {"schema_version": 1, "generator": GEN, "inputs": {p: L.sha256(L.ROOT / p) for p in INPUTS},
              "blender": bpy.app.version_string, "run_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "attempt": attempt.name, "study_sha256": study_sha,
              "decode": "camera_normal_slope.across_slope: the across-grain component over -z (Cycles' camera space "
                        "looks along +z), on unit normals facing the camera",
              "scope": "a re-analysis of retained review renders: not an admission, not photoreal",
              "scans": {a: study["scans"][a]["slope"] for a in SCANS}, "patches": {}}
    for name, P in study["patches"].items():
        Q = record["patches"][name] = {"across": P["across"], "variants": {}}
        for vname in ("v23", "scan_contrast"):
            files = {}
            for label in (f"{vname}_Normal", f"{vname}_BaseColor_japanese_cedar_planks"):
                r = P["renders"][label]
                digest = L.sha256(L.ROOT / r["file"])
                if digest != r["sha256"]:
                    raise RuntimeError(f"patch study re-analysis: {r['file']} is {digest[:12]}..., its study recorded "
                                       f"{r['sha256'][:12]}...")
                files[label] = {"file": r["file"], "sha256": digest}
            check, slope = render_slope_stats(L.ROOT / files[f"{vname}_Normal"]["file"],
                                              L.ROOT / files[f"{vname}_BaseColor_japanese_cedar_planks"]["file"],
                                              P["across"], fine)
            Q["variants"][vname] = {"files": files, "normal_check": check, "slope": slope,
                                    "attempt_slope": P["variants"][vname]["slope"]}
            print("PATCH_REANALYSIS", name, vname, json.dumps({"normal_check": check, "slope": slope}), flush=True)
    n = 0
    while (OUT / f"{attempt.name}_reanalysis{n}").exists():
        n += 1
    out = guard(OUT / f"{attempt.name}_reanalysis{n}")
    out.mkdir(exist_ok=False)
    with open(guard(out / "slope_reanalysis.json"), "x", encoding="utf-8") as f:
        f.write(json.dumps(record, indent=1) + "\n")
    print("PATCH_REANALYSIS_READY", L.rel(out / "slope_reanalysis.json"), flush=True)


def scan_inputs(raw, asset, mm):
    """A scan's linear base colour and its across-grain slope field from the DX normal map."""
    base = raw / "cc0/polyhaven" / asset
    diff = read_pixels(base / f"{asset}_diff_4k.jpg")[..., :3].astype(np.float64)
    rgb = R.srgb_to_linear(diff)
    nor = read_pixels(base / f"{asset}_nor_dx_4k.exr")[..., :3].astype(np.float64) * 2.0 - 1.0
    # The EXR must hold unit normals encoded n * 0.5 + 0.5, like its PNG; anything else stops the study.
    length = np.linalg.norm(nor, axis=2)
    if not (0.95 < float(np.median(length)) < 1.05 and float(np.median(nor[..., 2])) > 0.9):
        raise RuntimeError(f"patch study: {asset}'s normal map is not n * 0.5 + 0.5 unit normals "
                           f"(median length {float(np.median(length)):.3f}, z {float(np.median(nor[..., 2])):.3f})")
    nz = np.maximum(nor[..., 2], 1e-3)
    lum = rgb @ R.REC709
    gx = float((np.diff(lum, axis=1) ** 2).mean())
    gy = float((np.diff(lum, axis=0) ** 2).mean())
    # Across the grain: image y (DX green, flipped; sign is irrelevant to an RMS) when the grain runs along x.
    slope = (nor[..., 1] if gx < gy else nor[..., 0]) / nz
    return rgb, lum, slope


def crop_between_seams(rgb, lum, mm, across_mm, along_mm):
    """A crop of the patch's physical size, centred between the two seams farthest apart, at the scan's pitch."""
    gx = float((np.diff(lum, axis=1) ** 2).mean())
    gy = float((np.diff(lum, axis=0) ** 2).mean())
    along_x = gx < gy
    prof = np.median(lum, axis=1 if along_x else 0)
    s = R.seams(prof, mm)
    edges = [0] + s + [len(prof)]
    i = int(np.argmax(np.diff(edges)))
    c_across = (edges[i] + edges[i + 1]) // 2
    na, nl = int(round(across_mm / mm)), int(round(along_mm / mm))
    a0 = int(np.clip(c_across - na // 2, 0, len(prof) - na))
    l0 = (rgb.shape[1 if along_x else 0] - nl) // 2
    if along_x:
        return rgb[a0: a0 + na, l0: l0 + nl]          # rows across, columns along
    return rgb[l0: l0 + nl, a0: a0 + na]              # rows along, columns across


def resample(img, shape):
    """Bilinear resampling of (H, W, C) to ``shape`` (H, W)."""
    h, w = img.shape[:2]
    y = np.clip((np.arange(shape[0]) + 0.5) * h / shape[0] - 0.5, 0, h - 1)
    x = np.clip((np.arange(shape[1]) + 0.5) * w / shape[1] - 0.5, 0, w - 1)
    y0, x0 = np.floor(y).astype(int), np.floor(x).astype(int)
    y1, x1 = np.minimum(y0 + 1, h - 1), np.minimum(x0 + 1, w - 1)
    fy, fx = (y - y0)[:, None, None], (x - x0)[None, :, None]
    top = img[y0][:, x0] * (1 - fx) + img[y0][:, x1] * fx
    bot = img[y1][:, x0] * (1 - fx) + img[y1][:, x1] * fx
    return top * (1 - fy) + bot * fy


def save_sheet(panels, path: Path):
    """Panels (H, W, 3) display-referred 0..1, side by side with 4 px gaps, as an 8-bit PNG."""
    h = max(p.shape[0] for p in panels)
    gap = np.full((h, 4, 3), 0.5)
    row = [np.pad(p, ((0, h - p.shape[0]), (0, 0), (0, 0)), constant_values=0.5) for p in panels]
    sheet = np.concatenate([x for p in row for x in (p, gap)][:-1], axis=1)
    img = bpy.data.images.new(path.stem, sheet.shape[1], sheet.shape[0], alpha=True)
    img.colorspace_settings.name = "Non-Color"
    rgba = np.concatenate([sheet, np.ones(sheet.shape[:2] + (1,))], axis=2)[::-1]
    img.pixels.foreach_set(rgba.astype(np.float32).ravel())
    img.filepath_raw = str(guard(path))
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    return {"file": L.rel(path), "sha256": L.sha256(path)}


def main():
    o = parse()
    if "reanalyse" in o:
        reanalyse(o["reanalyse"])
        return
    scene = L.reset_scene()
    if o["cpu"]:
        scene.cycles.device = "CPU"
    ref = json.loads(REFERENCE.read_text(encoding="utf-8"))
    pitch = {a: ref["scans"][a]["mm_per_px"] for a in SCANS}
    fine = min(pitch.values())
    out = attempt_dir()
    record = {"schema_version": 1, "generator": GEN, "inputs": {p: L.sha256(L.ROOT / p) for p in INPUTS},
              "blender": bpy.app.version_string, "run_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "digest_version": V.DIGEST_VERSION, "attempt": out.name, "pitch_mm": pitch, "graze_deg": GRAZE_DEG,
              "scope": "focused review study: not an admission, not photoreal", "members": {}, "patches": {},
              "scans": {}}
    shared = {k: p for k, (p, _) in T.shared_textures(guard(out / "Shared")).items()}
    built = build_members(V.shared_arrays())
    for kind, e in built.items():
        record["members"][kind] = {k: e[k] for k in ("digest", "triangles", "seconds")} | {
            "asset": e["member"].name, "ring_width_m": e["member"].log.ring_width}
    scans = {}
    for a in SCANS:
        rgb, lum, slope = scan_inputs(o["raw"], a, pitch[a])
        scans[a] = (rgb, lum)
        record["scans"][a] = {"base_colour": {k: ref["scans"][a][k] for k in (
            "apparent_ring_spacing_mm", "latewood_fraction", "contrast_p95_over_p5", "early_over_late_luminance",
            "fibre_over_ring_rms")}, "slope": slope_stats(slope, lum, pitch[a])}
        print("PATCH_SCAN", a, json.dumps(record["scans"][a]["slope"]), flush=True)
    r_target = float(np.mean([ref["scans"][a]["early_over_late_luminance"] for a in SCANS]))
    clay = LD.clay_material()
    for kind, name, centre, ax, al, across_mm, along_mm in PATCHES:
        e = built[kind]
        obj, m = e["obj"], e["member"]
        for other in built.values():
            other["obj"].hide_render = other is not e
        face_y, _ = face_plane(obj, centre, across_mm, along_mm, ax)
        across, along = AXIS[ax], AXIS[al]
        P = record["patches"][name] = {"member": m.name, "centre_m": list(centre), "face_y_m": face_y,
                                       "across": ax, "along": al, "size_mm": [across_mm, along_mm],
                                       "renders": {}, "variants": {}}

        def shoot(label, mat, rig_kind, pitch_mm, **kw):
            obj.data.materials.clear()
            obj.data.materials.append(mat)
            rig(scene, rig_kind, across, along)
            camera(scene, centre, across, along, across_mm, along_mm, face_y, pitch_mm)
            ext = ".exr" if kw.get("fmt") == "OPEN_EXR" else ".png"
            P["renders"][label] = render(scene, out / name / f"{name}_{label}{ext}", **kw)
            return out / name / f"{name}_{label}{ext}"

        shots = {}
        for rk in ("GrazeAcross", "GrazeAlong"):
            shots[f"Clay_{rk}"] = shoot(f"Clay_{rk}", clay, rk, fine, samples=o["samples"], view="AgX", exposure=0.0)
        early, late0 = LD.PRESETS[PRESET]["early"], LD.PRESETS[PRESET]["late"]
        measured = {}
        for vi in range(2):
            if vi == 0:
                vname, preset = "v23", PRESET
            else:
                r0 = measured["v23"][fine]["early_over_late_luminance"]
                alpha = (1.0 - 1.0 / r_target) / (1.0 - 1.0 / r0)
                late = [ec - alpha * (ec - lc) for ec, lc in zip(early, late0)]
                vname, preset = "scan_contrast", variant_preset("scan_contrast", late)
                P["variants"]["scan_contrast_rule"] = {"r0": r0, "r_target": r_target, "alpha": alpha,
                                                       "late": late, "late_v23": list(late0)}
            mat = LD2.timber_material(f"TP_{m.name}_{vname}", preset, shared, m.log.ring_width)
            for rk in ("GrazeAcross", "Soft"):
                shots[f"{vname}_{rk}"] = shoot(f"{vname}_{rk}", mat, rk, fine, samples=o["samples"], view="AgX",
                                               exposure=MATERIAL_EXPOSURE)
            base_mat = emission_of(mat, "Base Color", f"TP_{m.name}_{vname}_Base")
            measured[vname] = {}
            for a in SCANS:
                path = shots[f"{vname}_BaseColor_{a}"] = shoot(f"{vname}_BaseColor_{a}", base_mat, "Emission", pitch[a],
                                                               samples=16, view="Standard", exposure=0.0, depth="16")
                rgb = R.srgb_to_linear(read_pixels(path)[..., :3].astype(np.float64))
                measured[vname][pitch[a]] = R.analyse(rgb, pitch[a])
            nmat = emission_of(mat, "Normal", f"TP_{m.name}_{vname}_Normal")
            npath = shoot(f"{vname}_Normal", nmat, "Emission", fine, samples=16, view="Raw", exposure=0.0,
                          fmt="OPEN_EXR", depth="32")
            base_png = out / name / f"{name}_{vname}_BaseColor_japanese_cedar_planks.png"
            normal_check, slope = render_slope_stats(npath, base_png, ax, fine)
            P["variants"][vname] = {"base_colour": {f"{k:.4f}": v for k, v in measured[vname].items()},
                                    "normal_check": normal_check, "slope": slope}
            print("PATCH_VARIANT", name, vname, json.dumps({k: measured[vname][fine].get(k) for k in (
                "apparent_ring_spacing_mm", "contrast_p95_over_p5", "early_over_late_luminance",
                "fibre_over_ring_rms")}), flush=True)
        # The contact sheet, at the sugi pitch; scans and renders as display sRGB.
        shape = (int(round((along_mm if ax == "x" else across_mm) / fine)),
                 int(round((across_mm if ax == "x" else along_mm) / fine)))
        panels = []
        for a in SCANS:
            rgb, lum = scans[a]
            crop = crop_between_seams(rgb, lum, pitch[a], across_mm, along_mm)
            # The crop's rows run along the grain for a vertical grain; turn it to the patch's own orientation.
            if (crop.shape[0] > crop.shape[1]) != (shape[0] > shape[1]):
                crop = np.transpose(crop, (1, 0, 2))
            disp = np.where(crop <= 0.0031308, 12.92 * crop, 1.055 * np.clip(crop, 0, 1) ** (1 / 2.4) - 0.055)
            panels.append(resample(disp, shape))
        for label in ("v23_BaseColor_japanese_cedar_planks", "scan_contrast_BaseColor_japanese_cedar_planks",
                      "v23_Soft", "v23_GrazeAcross", "scan_contrast_Soft", "scan_contrast_GrazeAcross",
                      "Clay_GrazeAcross", "Clay_GrazeAlong"):
            panels.append(resample(read_pixels(shots[label])[..., :3].astype(np.float64), shape))
        P["sheet"] = save_sheet(panels, out / f"{name}_sheet.png")
        P["sheet"]["panels"] = ["hinoki scan (base colour)", "sugi scan (base colour)", "v23 base colour",
                                "scan_contrast base colour", "v23 Soft", "v23 GrazeAcross", "scan_contrast Soft",
                                "scan_contrast GrazeAcross", "Clay GrazeAcross", "Clay GrazeAlong"]
    (guard(out / "study.json")).write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    print("PATCH_STUDY_READY", L.rel(out), flush=True)


main()
