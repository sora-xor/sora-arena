"""Shared Blender 5.2 pipeline for SORA craft props (lacquer, raden, maki-e, silk).

Builds on create_runtime_weapon_lib: the same procedural authoring materials,
the Cycles bake to one UV0 atlas (BaseColor, DirectX normal, ORM, Mask), LOD
decimation and FBX export. Props differ from weapons in three ways:

* a prop spec dict replaces the weapon table (key, asset, Japanese/English
  names, texture resolution, output folder);
* Mask channels are R raden (mother-of-pearl) coverage, G gold (maki-e and
  gilt metal) coverage, B raden film thickness, so the Unreal material can
  evaluate view-dependent thin-film iridescence and gold sparkle per pixel;
* review renders use fixed studio, golden-hour and lantern rigs at 1 m and
  gameplay distance.

Every 2D design that carries the SORA mark is rasterized from the pinned SVG
through sora_mark.py; nothing redraws the mark.
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import create_runtime_weapon_lib as L  # noqa: E402
import sora_mark  # noqa: E402

ROOT = L.ROOT
CRAFT = ROOT / "Content/SourceArt/Environment/SoraCraft"
DESIGN_CACHE = ROOT / "Saved/SoraCraftDesigns"


def write_design(name: str, array: np.ndarray, colorspace: str = "Non-Color") -> Path:
    """Save a float design map (H, W) or (H, W, 3) in [0, 1] as a 16-bit PNG for authoring."""
    from PIL import Image  # Blender's Python does not ship Pillow; fall back below

    DESIGN_CACHE.mkdir(parents=True, exist_ok=True)
    path = DESIGN_CACHE / f"{name}.png"
    arr = np.clip(array, 0.0, 1.0)
    if arr.ndim == 2:
        Image.fromarray(np.round(arr * 65535).astype(np.uint16), "I;16").save(path)
    else:
        Image.fromarray(np.round(arr * 255).astype(np.uint8), "RGB").save(path)
    return path


def design_image(name: str, array: np.ndarray, colorspace: str = "Non-Color"):
    """Create a float Blender image directly from a numpy design map (no disk round trip)."""
    arr = np.clip(np.asarray(array, dtype=np.float32), 0.0, 1.0)
    h, w = arr.shape[:2]
    img = bpy.data.images.get(name)
    if img is not None:
        bpy.data.images.remove(img)
    img = bpy.data.images.new(name, w, h, alpha=False, float_buffer=True)
    img.colorspace_settings.name = colorspace
    rgba = np.ones((h, w, 4), dtype=np.float32)
    if arr.ndim == 2:
        rgba[..., 0] = rgba[..., 1] = rgba[..., 2] = arr
    else:
        rgba[..., :3] = arr[..., :3]
    # Blender images are stored bottom row first.
    img.pixels.foreach_set(rgba[::-1].ravel())
    img.pack()
    return img


class PropBuild(L.Build):
    """Weapon Build pipeline driven by a prop spec instead of the weapon table."""

    def __init__(self, spec: dict, opts: dict):
        self.id = spec["key"]
        self.spec = spec
        self.opts = opts
        self.key = spec["key"]
        self.dir = CRAFT / spec["folder"]
        self.dir.mkdir(parents=True, exist_ok=True)
        self.res = opts.get("res") or spec.get("texture_res", 4096)
        self.groups = {"main": dict(asset=spec["asset"], offset=Vector(), origin=Vector(), parts=[])}
        self.sockets = {"main": []}
        self.notes = {}
        self.measure = {}
        self.t0 = time.time()
        self.scene = L.reset_scene()
        L.USED_SOURCES.clear()
        L.REG.clear()

    def finalize(self):
        self.log("parts", sum(len(g["parts"]) for g in self.groups.values()))
        for gname, g in self.groups.items():
            if not g["parts"]:
                raise RuntimeError(f"group {gname} has no parts")
        self.unwrap_parts()
        bake_obj = self.build_bake_mesh()
        self.pack_uv0(bake_obj)
        if not self.opts.get("no_bake"):
            self.bake(bake_obj)
            self.final_material(bake_obj)
        exports = self.split_and_export(bake_obj)
        self.save_blend()
        if not self.opts.get("no_render"):
            self.render(exports)
        self.write_record(exports)
        self.log("done", f"{time.time() - self.t0:.1f}s")

    def split_and_export(self, bake):
        # Props export LOD0 only: Unreal's reducer builds LOD1/LOD2 at import
        # (scripts/unreal/import_sora_craft.py) and keeps the atlas's UV seams.
        saved = L.SPECS.LOD_RATIOS
        L.SPECS.LOD_RATIOS = (1.0,)
        try:
            return super().split_and_export(bake)
        finally:
            L.SPECS.LOD_RATIOS = saved

    def render(self, exports):
        render_prop(self, exports)

    def write_record(self, exports):
        super().write_record(exports)
        path = self.dir / "build_record.json"
        rec = json.loads(path.read_text(encoding="utf-8"))
        rec.pop("faction", None)
        rec["library"] = "scripts/art/sora_prop_lib.py (over create_runtime_weapon_lib.py)"
        rec["axes"] = "+Z up, +X along the prop's length, -Y toward the viewer (front); origin on the floor"
        rec["origin"] = "floor contact, centred"
        if "material" in rec:
            rec["material"]["Mask"] = ("R raden (mother-of-pearl) coverage, G gold (maki-e/gilt) coverage, "
                                       "B raden thin-film thickness (0 = 260 nm, 1 = 720 nm)")
        rec["sora_mark"] = {"svg": L.rel(sora_mark.SVG_PATH), "sha256": sora_mark.PINNED_SVG_SHA256,
                            "method": "scanline rasterization of the SVG's two filled paths (sora_mark.py)"}
        path.write_text(json.dumps(rec, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Authoring materials
# ---------------------------------------------------------------------------

def _design_sampler(nb: L.NB, img, origin, u_axis, v_axis, size_uv, facing=None):
    """Planar-project a design image in object space; returns a coverage socket.

    ``origin`` is the design's lower-left corner, ``u_axis``/``v_axis`` unit
    object-space directions and ``size_uv`` its (width, height) in metres.
    ``facing`` limits the projection to faces whose normal points that way.
    """
    o = nb.obj()
    rel = nb.node("ShaderNodeVectorMath", operation="SUBTRACT")
    nb.link(o, rel.inputs[0])
    rel.inputs[1].default_value = tuple(origin)
    du = nb.node("ShaderNodeVectorMath", operation="DOT_PRODUCT")
    nb.link(rel.outputs[0], du.inputs[0])
    du.inputs[1].default_value = tuple(Vector(u_axis) / size_uv[0])
    dv = nb.node("ShaderNodeVectorMath", operation="DOT_PRODUCT")
    nb.link(rel.outputs[0], dv.inputs[0])
    dv.inputs[1].default_value = tuple(Vector(v_axis) / size_uv[1])
    comb = nb.node("ShaderNodeCombineXYZ")
    nb.link(du.outputs["Value"], comb.inputs[0])
    nb.link(dv.outputs["Value"], comb.inputs[1])
    tex = nb.node("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = "Cubic"
    tex.extension = "CLIP"
    nb.link(comb.outputs[0], tex.inputs["Vector"])
    cov = nb.bw(tex.outputs["Color"])
    if facing is not None:
        dot = nb.node("ShaderNodeVectorMath", operation="DOT_PRODUCT")
        nb.link(nb.geo().outputs["Normal"], dot.inputs[0])
        dot.inputs[1].default_value = tuple(Vector(facing).normalized())
        cov = nb.mul(cov, nb.smoothstep(dot.outputs["Value"], 0.55, 0.85))
    return cov


def mat_lacquer_design(name, designs, *, ground=(0.010, 0.009, 0.008), rough=0.045, wear=0.12,
                       undercoat=(0.20, 0.045, 0.025), scale=1.0):
    """Roiro urushi with planar-projected maki-e gold and raden designs.

    ``designs`` is a list of dicts: {img_gold, img_raden, img_film, origin, u, v, size} where
    any image may be None. Gold areas are burnished powder (metallic, roughness ~0.3);
    raden areas are the shell's near-white body with low roughness. The Mask
    output carries (raden, gold, film) for the Unreal shader.
    """
    nb = L.NB(name)
    o = nb.obj()
    # Base black urushi with orange-peel, polishing haze and edge wear.
    edge = nb.edge(0.0016 * scale, 4.0)
    wn = nb.noise(o, 140.0 / scale, 5.0, 0.65, 0.4)
    wear_mask = nb.clamp01(nb.mul(nb.sub(nb.add(nb.mul(edge, 1.2), nb.mul(wn, 0.9)), 1.08), 3.5 * wear))
    peel = nb.noise(o, 250.0 / scale, 2.0, 0.5)
    haze = nb.noise(nb.vmul(o, (40.0, 900.0, 900.0)), 1.0, 2.0, 0.5)
    base = nb.rgb(ground)
    base = nb.mixc(wear_mask, base, nb.rgb(undercoat))
    rgh = nb.add(rough, nb.mul(nb.sub(haze, 0.5), 0.04))
    rgh = nb.lerp(rgh, 0.42, wear_mask)
    height = nb.mul(nb.sub(peel, 0.5), 0.000060)
    gold_cov = 0.0
    raden_cov = 0.0
    film = 0.0
    for d in designs:
        frame = (d["origin"], d["u"], d["v"], d["size"], d.get("facing"))
        if d.get("img_gold") is not None:
            g = _design_sampler(nb, d["img_gold"], *frame)
            gold_cov = g if gold_cov == 0.0 else nb.maxi(gold_cov, g)
        if d.get("img_raden") is not None:
            r = _design_sampler(nb, d["img_raden"], *frame)
            raden_cov = r if raden_cov == 0.0 else nb.maxi(raden_cov, r)
        if d.get("img_film") is not None:
            f = _design_sampler(nb, d["img_film"], *frame)
            film = f if film == 0.0 else nb.maxi(film, f)
    if gold_cov != 0.0:
        grain = nb.noise(o, 6000.0 / scale, 2.0, 0.6)
        gold_col = nb.rgb((1.0, 0.766, 0.336))
        gold_col = nb.mixc(nb.mul(grain, 0.35), gold_col, nb.rgb((0.93, 0.66, 0.30)))
        base = nb.mixc(gold_cov, base, gold_col)
        rgh = nb.lerp(rgh, nb.add(0.26, nb.mul(grain, 0.12)), gold_cov)
        # Hiramaki-e sits a few microns proud of the polished ground.
        height = nb.add(height, nb.mul(gold_cov, 0.000012))
        height = nb.add(height, nb.mul(nb.mul(gold_cov, grain), 0.000004))
    if raden_cov != 0.0:
        shell = nb.rgb((0.80, 0.79, 0.775))
        base = nb.mixc(raden_cov, base, shell)
        rgh = nb.lerp(rgh, 0.06, raden_cov)
        height = nb.add(height, nb.mul(raden_cov, 0.000008))
    metal = gold_cov if gold_cov != 0.0 else 0.0
    normal = nb.bump_m(height)
    mask = (raden_cov if raden_cov != 0.0 else 0.0, gold_cov if gold_cov != 0.0 else 0.0,
            film if film != 0.0 else 0.0)
    out = nb.finish(base, rgh, metal, normal, mask=mask, ao_dist=0.02)
    # Blender preview: physically based thin-film iridescence on the raden.
    if raden_cov != 0.0 and film != 0.0 and "Thin Film Thickness" in nb.bsdf.inputs:
        thick = nb.add(260.0, nb.mul(film, 460.0))
        nb.link(nb.mul(thick, raden_cov), nb.bsdf.inputs["Thin Film Thickness"])
        nb.bsdf.inputs["Thin Film IOR"].default_value = 1.53
    return out


def mat_gilt_copper(name, *, nanako_pitch=0.0011, engrave_img=None, engrave_frame=None, rough=0.24,
                    wear=0.35, scale=1.0):
    """Fire-gilt copper (kinkise) fittings: nanako fish-roe punched ground,
    optional engraved design (image coverage: 1 = cut line), darkened recesses
    and gold worn to copper on high points."""
    nb = L.NB(name)
    o = nb.obj()
    vor = nb.voronoi(o, 1.0 / (nanako_pitch * scale), "F1", 0.15)
    dimple = nb.smoothstep(vor.outputs["Distance"], 0.18, 0.42)  # 0 at dimple centre
    height = nb.mul(dimple, 0.000045)
    cut = None
    if engrave_img is not None and engrave_frame is not None:
        cut = _design_sampler(nb, engrave_img, *engrave_frame)
        height = nb.sub(height, nb.mul(cut, 0.00012))
    edge = nb.edge(0.0008 * scale, 5.0)
    wn = nb.noise(o, 300.0 / scale, 4.0, 0.6)
    worn = nb.clamp01(nb.mul(nb.sub(nb.add(nb.mul(edge, 1.1), nb.mul(wn, 0.6)), 0.95), 3.0 * wear))
    gold = nb.rgb((1.0, 0.766, 0.336))
    copper = nb.rgb((0.955, 0.638, 0.538))
    tarnish = nb.rgb((0.42, 0.28, 0.12))
    base = nb.mixc(worn, gold, copper)
    recess = nb.one_minus(dimple)
    if cut is not None:
        recess = nb.maxi(recess, cut)
    base = nb.mixc(nb.mul(recess, 0.55), base, tarnish)
    rgh = nb.lerp(rough, 0.5, nb.mul(recess, 0.6))
    rgh = nb.lerp(rgh, 0.16, worn)
    normal = nb.bump_m(height)
    return nb.finish(base, rgh, 1.0, normal, mask=(0.0, 1.0, 0.0), ao_dist=0.006)


def mat_silk_cord(name, color=(0.42, 0.018, 0.016), pitch=0.0016, sheen=0.6, rough=0.45):
    """Flat-braided silk cord (sanada-himo/kumihimo): chevron braid relief."""
    return L.mat_braid(name, color, scale=pitch / 0.0024, sheen=sheen, rough=rough, kind="flat")


# ---------------------------------------------------------------------------
# Review renders: studio, golden hour, lantern
# ---------------------------------------------------------------------------

RIGS = ("Studio", "GoldenHour", "Lantern")


def _clear_lights():
    for obj in list(bpy.data.objects):
        if obj.type == "LIGHT":
            bpy.data.objects.remove(obj, do_unlink=True)


def _world_sky(scene, sun_elev_deg, sun_rot_deg, strength=1.0):
    world = scene.world or bpy.data.worlds.new("RV_World")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    sky = nt.nodes.new("ShaderNodeTexSky")
    for kind in ("MULTIPLE_SCATTERING", "NISHITA"):
        try:
            sky.sky_type = kind
            break
        except TypeError:
            continue
    sky.sun_elevation = math.radians(sun_elev_deg)
    sky.sun_rotation = math.radians(sun_rot_deg)
    if hasattr(sky, "air_density"):
        sky.air_density = 1.2
    if hasattr(sky, "aerosol_density"):
        sky.aerosol_density = 2.0
    elif hasattr(sky, "dust_density"):
        sky.dust_density = 2.0
    bg.inputs["Strength"].default_value = strength
    nt.links.new(sky.outputs[0], bg.inputs[0])
    nt.links.new(bg.outputs[0], out.inputs[0])


def _world_flat(scene, color, strength):
    world = scene.world or bpy.data.worlds.new("RV_World")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs[0].default_value = (*color, 1.0)
    bg.inputs["Strength"].default_value = strength
    nt.links.new(bg.outputs[0], out.inputs[0])


def _light(name, kind, loc, rot, energy, color=(1, 1, 1), size=0.5):
    data = bpy.data.lights.new(name, kind)
    data.energy = energy
    data.color = color
    if kind == "AREA":
        data.size = size
    elif kind in ("POINT", "SPOT"):
        data.shadow_soft_size = size
    elif kind == "SUN":
        data.angle = math.radians(size)
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = rot
    return obj


def setup_rig(scene, rig):
    _clear_lights()
    vs = scene.view_settings
    vs.view_transform = "AgX" if "AgX" in [v.identifier for v in type(vs).bl_rna.properties["view_transform"].enum_items] else "Filmic"
    vs.look = "None"
    if rig == "Studio":
        _world_flat(scene, (0.18, 0.18, 0.18), 0.6)
        _light("RV_Key", "AREA", (1.4, -1.6, 1.8), (math.radians(55), 0, math.radians(40)), 220, size=1.2)
        _light("RV_Fill", "AREA", (-1.8, -1.0, 1.0), (math.radians(70), 0, math.radians(-60)), 60, size=1.5)
        _light("RV_Rim", "AREA", (0.0, 1.8, 1.6), (math.radians(-55), 0, math.radians(180)), 140, size=1.0)
        vs.exposure = 0.0
    elif rig == "GoldenHour":
        _world_sky(scene, 7.0, 205.0, 0.35)
        sun = _light("RV_Sun", "SUN", (0, 0, 5), (math.radians(83), 0, math.radians(-155)), 4.2,
                     color=(1.0, 0.72, 0.45), size=0.6)
        vs.exposure = -0.4
    elif rig == "Lantern":
        _world_flat(scene, (0.010, 0.012, 0.020), 1.0)
        _light("RV_LanternL", "POINT", (-0.9, -0.6, 0.7), (0, 0, 0), 55, color=(1.0, 0.62, 0.32), size=0.12)
        _light("RV_LanternR", "POINT", (1.1, 0.4, 1.1), (0, 0, 0), 30, color=(1.0, 0.58, 0.28), size=0.12)
        vs.exposure = 0.3


def render_prop(build, exports, distances=(1.0, 2.5), size=(1600, 1000)):
    """Fixed-camera review renders of LOD0 for each rig and distance."""
    scene = build.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = build.opts.get("samples", 128)
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = size
    scene.render.image_settings.file_format = "PNG"
    lod0 = exports["main"]["lods"][0]
    lod0.hide_render = False
    lod0.hide_set(False)
    for o in exports["main"]["lods"][1:]:
        o.hide_render = True
    dims = lod0.dimensions
    centre = Vector((0.0, 0.0, dims.z * 0.45))
    # Floor: dark polished hinoki-like boards stand-in (neutral, no texture).
    floor = bpy.data.objects.get("RV_Floor")
    if floor is None:
        bpy.ops.mesh.primitive_plane_add(size=12.0, location=(0, 0, 0))
        floor = bpy.context.object
        floor.name = "RV_Floor"
        fm = bpy.data.materials.new("RV_FloorMat")
        fm.use_nodes = True
        b = fm.node_tree.nodes.get("Principled BSDF")
        b.inputs["Base Color"].default_value = (0.08, 0.05, 0.035, 1)
        b.inputs["Roughness"].default_value = 0.32
        floor.data.materials.append(fm)
    cam_data = bpy.data.cameras.new("RV_Cam")
    cam_data.lens = 50.0
    cam = bpy.data.objects.new("RV_Cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    files = []
    renders = build.dir / "Renders"
    renders.mkdir(parents=True, exist_ok=True)
    for rig in RIGS:
        setup_rig(scene, rig)
        for dist in distances:
            for view, yaw in (("ThreeQuarter", -35.0), ("Front", 0.0)):
                a = math.radians(yaw)
                eye = centre + Vector((math.sin(a) * dist, -math.cos(a) * dist, 0.35 * dist + 0.25))
                cam.location = eye
                direction = centre - eye
                cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
                path = renders / f"{build.spec['asset']}_{rig}_{view}_{dist:.1f}m.png"
                scene.render.filepath = str(path)
                bpy.ops.render.render(write_still=True)
                files.append(path)
                build.log("rendered", L.rel(path))
    build.render_files = files
