"""SORA maku: the kamiza's hemp curtain with the SORA mon dyed in indigo.

Run (Blender 5.2.2):
  blender -b --factory-startup --python scripts/art/create_sora_maku.py -- [--res 4096] [--no-render] [--cpu]

A jinmaku-style curtain for the dojo's kamiza (scripts/art/create_nyaagyu_dojo_kit.py
kamiza): ten widths (no) of natural hemp, each 36 cm, sewn side by side into a
3.6 x 1.7 m curtain. An indigo top band carries chi loops every 30 cm on a
black-lacquered pole with gilt end caps; red silk cords and tassels hang from
the pole ends. The SORA mark, from the pinned SVG only, is dyed in indigo
across the middle widths, so its seams run through the mon as they do on a real
maku. The dye bleeds a little along the threads, and its resist edge is
slightly irregular.

The curtain hangs in front of the kamiza's back shoji. At dawn the hemp glows
and the indigo mon reads as a silhouette. The cloth is one two-sided surface:

* sagging between the loops;
* folds that grow towards the free hem;
* a ridge at every seam and a heavier double-folded hem.

Maps (numpy, authored here, nothing third-party):
T_SoraMaku_BaseColor (UV1, unique), T_SoraMaku_Transmission (UV1: how much
dawn light each part lets through) and T_SoraMaku_WeaveNormalDX (UV0, a plain
hemp weave tiling every 5 cm).

Outputs: Content/SourceArt/Environment/SoraCraft/SoraMaku/. Review renders
are Blender Cycles source renders.
"""

from __future__ import annotations

import hashlib
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
import craft_textures as CT  # noqa: E402
import create_runtime_weapon_lib as L  # noqa: E402
import sora_mark  # noqa: E402
import sora_prop_lib as PL  # noqa: E402
import sora_timber_lib as T  # noqa: E402

GEN = "scripts/art/create_sora_maku.py"
OUT = L.ROOT / "Content/SourceArt/Environment/SoraCraft/SoraMaku"
WIDTHS = 10
NO = 0.36                    # one width of hemp cloth
W = WIDTHS * NO              # 3.6 m
H = 1.70
TOP = 3.05                   # loop line above the kamiza dais floor (local z)
BAND = 0.09                  # indigo top band
LOOP_PITCH = 0.30
SAG = 0.018
FOLD = 0.060                 # fold depth at the hem
HEMP = (0.58, 0.49, 0.33)    # kinari asa, linear
INDIGO = (0.010, 0.026, 0.091)
MON_DIAMETER = 1.10
MON_CENTRE = (0.0, TOP - 0.80)


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    o = {"res": 4096, "render": True, "cpu": False, "samples": 96}
    i = 0
    while i < len(argv):
        if argv[i] == "--res":
            o["res"] = int(argv[i + 1])
            i += 1
        elif argv[i] == "--no-render":
            o["render"] = False
        elif argv[i] == "--cpu":
            o["cpu"] = True
        elif argv[i] == "--samples":
            o["samples"] = int(argv[i + 1])
            i += 1
        i += 1
    return o


# ---------------------------------------------------------------------------
# Cloth geometry
# ---------------------------------------------------------------------------

def drape(x, z, rng_waves):
    """Depth (+Y away from the room) of the hanging cloth at (x, z)."""
    down = np.clip((TOP - z) / H, 0, 1)
    amp = FOLD * down ** 0.85
    # Scallops pinned by the loops, plus a few long folds.
    loop_phase = 2 * math.pi * (x + W / 2) / LOOP_PITCH
    scallop = 0.55 * np.cos(loop_phase) * (1 - np.exp(-(TOP - z) / 0.35))
    long = rng_waves(x, 0.0)
    # Seams are stiffer: the cloth folds a little at each.
    seams = np.zeros_like(x)
    for i in range(1, WIDTHS):
        xs = -W / 2 + i * NO
        seams += 0.0015 * np.exp(-((x - xs) / 0.006) ** 2)
    creases = sum(0.004 * np.exp(-(((TOP - z) - frac * H) / 0.012) ** 2) for frac in (1 / 3, 2 / 3))
    return amp * (scallop + long) + seams + creases


def sag(x):
    """Drop of the top edge between loops (a shallow catenary)."""
    t = ((x + W / 2) % LOOP_PITCH) / LOOP_PITCH
    return SAG * 4 * t * (1 - t)


def cloth(res_x=361, res_z=171):
    rng = np.random.default_rng(611)
    waves = T.Waves(rng, 6, (0.35, 1.2), 0.45)
    xs = np.linspace(-W / 2, W / 2, res_x)
    us = np.linspace(0.0, 1.0, res_z)
    X, U = np.meshgrid(xs, us)                      # U: 0 top .. 1 hem
    Z = TOP - U * H - sag(X) * np.exp(-U * H / 0.12)
    # The hem's double fold weighs it down slightly between folds.
    Z -= 0.004 * np.clip((U - 0.97) / 0.03, 0, 1)
    Y = drape(X, Z, waves)
    verts = np.stack([X, Y, Z], -1).reshape(-1, 3)
    idx = np.arange(res_x * res_z).reshape(res_z, res_x)
    a, b, c, d = idx[:-1, :-1], idx[:-1, 1:], idx[1:, 1:], idx[1:, :-1]
    tris = np.concatenate([np.stack([a, d, b], -1).reshape(-1, 3), np.stack([b, d, c], -1).reshape(-1, 3)])
    uv1 = np.stack([(X + W / 2) / W, 1.0 - U], -1).reshape(-1, 2)
    uv0 = np.stack([X, Z], -1).reshape(-1, 2)        # metres, for the weave tile
    return verts, tris, uv0, uv1


def make_mesh(name, verts, tris, uvs: dict, material):
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(verts))
    me.vertices.foreach_set("co", verts.astype(np.float32).ravel())
    nt = len(tris)
    me.loops.add(nt * 3)
    me.loops.foreach_set("vertex_index", tris.astype(np.int32).ravel())
    me.polygons.add(nt)
    me.polygons.foreach_set("loop_start", np.arange(0, nt * 3, 3, dtype=np.int32))
    me.update(calc_edges=True)
    me.polygons.foreach_set("use_smooth", np.ones(nt, bool))
    vi = tris.ravel()
    for layer, arr in uvs.items():
        uv = me.uv_layers.new(name=layer)
        uv.data.foreach_set("uv", arr[vi].astype(np.float32).ravel())
    me.materials.append(material)
    me.validate(clean_customdata=False)
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    return obj


# ---------------------------------------------------------------------------
# Maps
# ---------------------------------------------------------------------------

def blur(a, sigma_px):
    """Separable Gaussian blur (numpy)."""
    if sigma_px <= 0:
        return a
    r = int(math.ceil(3 * sigma_px))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma_px) ** 2)
    k /= k.sum()
    out = np.apply_along_axis(lambda v: np.convolve(np.pad(v, r, mode="edge"), k, mode="valid"), 1, a)
    return np.apply_along_axis(lambda v: np.convolve(np.pad(v, r, mode="edge"), k, mode="valid"), 0, out)


def maps(res):
    """BaseColor, Transmission (UV1) for the cloth, res x res/2."""
    w, h = res, res // 2
    px_m = W / w
    rng = np.random.default_rng(612)
    tone = CT.fbm(max(w, h), 612, octaves=5, base=5.0)[:h, :w]
    # Slubs: hemp yarn varies in thickness, so warp and weft show streaks.
    warp = np.repeat(rng.normal(0, 1, (1, w)), h, 0)
    weft = np.repeat(rng.normal(0, 1, (h, 1)), w, 1)
    slub = blur(0.6 * warp + 0.4 * weft, 0.6) * 0.035
    base = np.empty((h, w, 3), np.float32)
    for i in range(3):
        base[..., i] = HEMP[i] * (0.92 + 0.12 * tone + slub)
    # The mon: the pinned SVG, dyed indigo with a slightly irregular resist
    # edge and a little bleed along the threads.
    mon_px = int(MON_DIAMETER / px_m)
    size = 1 << int(math.ceil(math.log2(mon_px)))
    cov = sora_mark.coverage(size, scale=mon_px / size, supersample=4)
    ragged = blur(rng.normal(0, 1, cov.shape), 1.2) * 0.18
    cov = np.clip((cov - 0.5 + ragged) * 2.5 + 0.5, 0, 1)
    cov = np.maximum(blur(cov, 0.7), 0.6 * blur(cov, 2.0))      # bleed
    mon = np.zeros((h, w), np.float32)
    cx = int(w / 2)
    cy = int((TOP - MON_CENTRE[1]) / H * h)                     # rows from the top
    y0, x0 = cy - size // 2, cx - size // 2
    ys, xs_ = slice(max(0, y0), min(h, y0 + size)), slice(max(0, x0), min(w, x0 + size))
    mon[ys, xs_] = cov[ys.start - y0:ys.stop - y0, xs_.start - x0:xs_.stop - x0]
    band = np.zeros((h, w), np.float32)
    band[: int(BAND / H * h)] = 1.0
    dye = np.clip(np.maximum(mon, band) * (0.94 + 0.06 * tone), 0, 1)
    indigo = np.asarray(INDIGO, np.float32) * (0.85 + 0.3 * tone[..., None])
    base = base * (1 - dye[..., None]) + indigo * dye[..., None]
    # Seams: a seam shadow and a line of hand stitches either side.
    seam = np.zeros((h, w), np.float32)
    for i in range(1, WIDTHS):
        xs = int(i * NO / px_m)
        seam[:, max(0, xs - 2):xs + 2] = 1.0
        stitch = ((np.arange(h) // max(1, int(0.006 / px_m))) % 2 == 0)
        for off in (-6, 6):
            col = min(w - 1, max(0, xs + off))
            seam[stitch, col] = np.maximum(seam[stitch, col], 0.6)
    base *= (1 - 0.25 * blur(seam, 0.8))[..., None]
    # Kept folded in thirds between uses, a maku keeps two faint creases.
    crease = np.zeros((h, w), np.float32)
    for frac in (1 / 3, 2 / 3):
        crease[int(frac * h) - 1:int(frac * h) + 1] = 1.0
    base *= (1 - 0.06 * blur(crease, 1.5))[..., None]
    # Transmission: hemp lets about 40 % of the dawn through; indigo, the
    # band and the doubled seams far less.
    trans = 0.42 * (0.9 + 0.2 * tone) * (1 - 0.8 * dye) * (1 - 0.6 * blur(seam, 1.0))
    return base, trans          # row 0 is the top hem (UV1 v = 1)


def weave_normal(res=1024, tile_m=0.05, threads=36):
    """Plain hemp weave: warp over-under weft, slubby threads; DirectX normal."""
    rng = np.random.default_rng(613)
    t = np.linspace(0, threads, res, endpoint=False)
    U, V = np.meshgrid(t, t)
    warp_w = 0.75 + 0.25 * rng.random(threads)
    weft_w = 0.75 + 0.25 * rng.random(threads)
    iu, iv = U.astype(int) % threads, V.astype(int) % threads
    fu, fv = U % 1.0, V % 1.0
    over = ((iu + iv) % 2 == 0)
    warp_h = np.sin(np.pi * fu) ** 0.6 * warp_w[iu] * np.where(over, 1.0, 0.55)
    weft_h = np.sin(np.pi * fv) ** 0.6 * weft_w[iv] * np.where(over, 0.55, 1.0)
    height = np.maximum(warp_h, weft_h)
    height_m = height * (tile_m / threads) * 0.35
    return CT.normal_from_height(height_m, 1.0 / (tile_m / res), directx=True)


def save(arr, path: Path, bits=8):
    a = np.clip(arr, 0, 1)
    if a.ndim == 2:
        a = a[..., None].repeat(3, -1)
    a = (a * (65535 if bits == 16 else 255)).astype(np.uint16 if bits == 16 else np.uint8)
    return T.write_png(path, a)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def mats(textures):
    nb = L.NB("M_Maku_Hemp")
    base = nb.img(textures["BaseColor"], nb.uv("UV1"), "sRGB")
    tr = nb.img(textures["Transmission"], nb.uv("UV1"), "Non-Color")
    weave = nb.img(textures["WeaveNormalDX"], nb.vmul(nb.uv("UV0"), 1.0 / 0.05), "Non-Color")
    normal = nb.nmap_dx(weave.outputs["Color"], 1.0, uv_map="UV0")
    bsdf = nb.bsdf
    nb.feed(bsdf.inputs["Base Color"], base.outputs["Color"])
    nb.feed(bsdf.inputs["Roughness"], 0.88)
    nb.feed(bsdf.inputs["Normal"], normal)
    nb.feed(bsdf.inputs["Sheen Weight"], 0.35)
    # Thin cloth: mix in a translucent lobe by the transmission map.
    tl = nb.node("ShaderNodeBsdfTranslucent")
    nb.feed(tl.inputs["Color"], base.outputs["Color"])
    nb.feed(tl.inputs["Normal"], normal)
    mix = nb.node("ShaderNodeMixShader")
    nb.link(tr.outputs["Color"], mix.inputs["Fac"])
    nb.link(bsdf.outputs[0], mix.inputs[1])
    nb.link(tl.outputs[0], mix.inputs[2])
    nb.link(mix.outputs[0], nb.out.inputs["Surface"])
    hemp = nb.mat
    # Review stand-ins for the hardware (no scan inputs): roiro lacquer, gilt
    # copper, red silk. Unreal binds its SoraCraft masters to these slots.
    pole = plain("M_Maku_Pole", (0.012, 0.010, 0.009), 0.10, coat=1.0)
    gilt = plain("M_Maku_Gilt", (1.0, 0.77, 0.34), 0.26, metal=1.0)
    cord = plain("M_Maku_Cord", (0.42, 0.018, 0.016), 0.45, sheen=0.8)
    return hemp, pole, gilt, cord


def plain(name, color, rough, metal=0.0, coat=0.0, sheen=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    b = mat.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Coat Weight"].default_value = coat
    b.inputs["Sheen Weight"].default_value = sheen
    return mat


def hardware(pole_m, gilt_m, cord_m, hemp_m):
    """Pole, gilt end caps, chi loops and the silk cords with tassels."""
    parts = []
    r = 0.016
    z = TOP + 0.022
    y = 0.0
    end = W / 2 + 0.12
    parts.append(L.tube("Maku_Pole", [(-end, r, r, y, z), (end, r, r, y, z)], pole_m, sides=24))
    for s in (-1, 1):
        secs = [(s * end, r * 1.25, r * 1.25, y, z), (s * (end + 0.04), r * 1.25, r * 1.25, y, z),
                (s * (end + 0.055), r * 0.6, r * 0.6, y, z)]
        parts.append(L.tube(f"Maku_Cap{s}", secs if s > 0 else secs[::-1], gilt_m, sides=24))
    # Chi loops: hemp tabs folded over the pole, a little proud of it.
    n = int(round(W / LOOP_PITCH))
    for k in range(n + 1):
        x = -W / 2 + k * LOOP_PITCH
        rr = r * 1.35
        parts.append(L.tube(f"Maku_Chi{k}", [(x - 0.02, rr, rr, y, z), (x + 0.02, rr, rr, y, z)], hemp_m, sides=16))
    # Silk cords knotted to the pole ends, ending in tassels (fusa).
    for s in (-1, 1):
        x = s * (end - 0.03)
        path = [Vector((x, y, z - r)), Vector((x, y - 0.012, z - 0.22)), Vector((x, y, z - 0.44))]
        parts.append(L.sweep(f"Maku_Cord{s}", path, L.circle2d(0.004, 10), cord_m))
        # Built along +X, then stood up: a knot head and a flaring skirt.
        tassel = L.tube(f"Maku_Tassel{s}", [(0.0, 0.007, 0.007), (0.02, 0.016, 0.016), (0.05, 0.012, 0.012),
                                            (0.20, 0.024, 0.024)], cord_m, sides=20)
        L.transform(tassel, L.trans(x, y, z - 0.44) @ L.rot("Y", 90))
        parts.append(tassel)
    return parts


def main():
    o = parse()
    scene = L.reset_scene()
    if o["cpu"]:
        scene.cycles.device = "CPU"
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    base, trans = maps(o["res"])
    textures = {"BaseColor": save(base ** (1 / 2.2), OUT / "T_SoraMaku_BaseColor.png"),
                "Transmission": save(trans, OUT / "T_SoraMaku_Transmission.png"),
                "WeaveNormalDX": save(weave_normal(), OUT / "T_SoraMaku_WeaveNormalDX.png")}
    hemp, pole, gilt, cord = mats(textures)
    verts, tris, uv0, uv1 = cloth()
    cloth_obj = make_mesh("Maku_Cloth", verts, tris, {"UV0": uv0, "UV1": uv1}, hemp)
    parts = [cloth_obj] + hardware(pole, gilt, cord, hemp)
    print("MAKU_BUILT", len(parts), "parts", round(time.time() - t0, 1), "s", flush=True)
    maku = L.join(parts, "SM_SoraMaku")
    maku.data.name = "SM_SoraMaku"
    fbx = OUT / "SM_SoraMaku.fbx"
    L.deselect_all()
    maku.select_set(True)
    bpy.context.view_layer.objects.active = maku
    bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={"MESH"}, apply_unit_scale=True,
                             apply_scale_options="FBX_SCALE_NONE", global_scale=1.0, axis_forward="-Y", axis_up="Z",
                             mesh_smooth_type="FACE", use_tspace=True, use_triangles=True, add_leaf_bones=False,
                             bake_anim=False, path_mode="STRIP", embed_textures=False, use_custom_props=False)
    renders = review(o, maku) if o["render"] else []
    rec = {"asset": "SM_SoraMaku", "generator": GEN, "generator_sha256": L.sha256(L.ROOT / GEN),
           "svg": L.rel(sora_mark.SVG_PATH), "svg_sha256": sora_mark.PINNED_SVG_SHA256, "size_m": [W, H],
           "widths": WIDTHS, "loop_pitch_m": LOOP_PITCH, "mon_diameter_m": MON_DIAMETER,
           "frame": "kamiza back wall: X along it centred, -Y the room, Z up from the dais floor; loops at z 3.05",
           "material_slots": sorted({m.name for m in maku.data.materials if m}),
           "triangles": len(maku.data.polygons), "fbx": L.rel(fbx), "fbx_sha256": L.sha256(fbx),
           "textures": {k: {"file": L.rel(p), "sha256": L.sha256(p)} for k, p in textures.items()},
           "renders": renders}
    (OUT / "build_record.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1) + "\n")
    print("MAKU_READY", rec["triangles"], flush=True)


def review(o, maku):
    """Dawn behind the shoji (the mon in silhouette) and lantern light in front."""
    import sora_timber_lookdev as LD

    scene = bpy.context.scene
    files = []
    shoji = bpy.data.materials.new("LD_ShojiGlow")
    shoji.use_nodes = True
    nt = shoji.node_tree
    nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (1.0, 0.78, 0.55, 1.0)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0.0, 0.30, TOP - H / 2 + 0.1), rotation=(math.pi / 2, 0, 0))
    glow = bpy.context.object
    glow.name = "LD_Shoji"
    glow.scale = (W + 1.2, H + 1.0, 1.0)
    glow.data.materials.append(shoji)
    for rig, strength in (("Dawn", 6.0), ("Lantern", 0.0)):
        PL._clear_lights()
        PL._world_flat(scene, (0.010, 0.010, 0.012), 1.0)
        em.inputs["Strength"].default_value = strength
        if rig == "Lantern":
            PL._light("LD_Lantern", "POINT", (0.9, -1.6, 1.9), (0, 0, 0), 160, color=(1.0, 0.60, 0.30), size=0.15)
        scene.view_settings.exposure = 0.0
        LD.camera(scene, "LD_Cam", (1.9, -4.2, 1.6), (0.15, 0.0, TOP - H / 2), 40.0)
        path = OUT / "Renders" / f"SM_SoraMaku_{rig}.png"
        t0 = time.time()
        LD.render(scene, path, (1600, 1000), o["samples"])
        files.append({"file": L.rel(path), "rig": rig, "kind": "Blender Cycles source render",
                      "seconds": round(time.time() - t0, 1)})
        print("MAKU_RENDER", L.rel(path), files[-1]["seconds"], flush=True)
    return files


if __name__ == "__main__":
    main()
