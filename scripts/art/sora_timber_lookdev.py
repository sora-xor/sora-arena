"""Blender look-dev for unique timbers: the growth-ring material and review rigs.

The material reads the log frame the generator stores per vertex (UVLogQ: offset
from the pith in the section; UVLogZ: height along the pith and a per-log seed)
and the Masks colour attribute (R cavity, G wear, B soot, A knot). It is the
review counterpart of the Unreal timber material: same inputs, same ring model
(a ring-width table that wanders over a few rings, earlywood grading into a
latewood band, an abrupt boundary at the next year's earlywood, per-ring
latewood strength), with fibres along the grain and the latewood standing
proud by ``raise`` metres where the finish lets the grain show.

Review renders only. Blender 5.2.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import create_runtime_weapon_lib as L  # noqa: E402
import sora_prop_lib as PL  # noqa: E402

# Linear colours. Columns: aged hinoki under fuki-urushi (wiped lacquer) with a
# century of soot; floors: polished hinoki with uzukuri (raised latewood).
PRESETS = {
    "column_fukiurushi": dict(ring_width=0.0019, latewood=0.24, early=(0.066, 0.035, 0.020),
                              late=(0.040, 0.020, 0.012), knot=(0.016, 0.008, 0.005), soot=(0.012, 0.010, 0.009),
                              worn=(0.15, 0.090, 0.050), rough=0.55, coat=1.0, coat_rough=0.17, raise_m=0.00002,
                              fibre_m=0.000012, soot_amount=0.55, wear_color=0.45),
    "floor_hinoki": dict(ring_width=0.0021, latewood=0.22, early=(0.42, 0.29, 0.17), late=(0.25, 0.15, 0.080),
                         knot=(0.12, 0.060, 0.030), soot=(0.20, 0.14, 0.09), worn=(0.50, 0.37, 0.24), rough=0.45,
                         coat=0.65, coat_rough=0.09, raise_m=0.00022, fibre_m=0.00002, soot_amount=0.25,
                         wear_color=0.35),
    "raw_hinoki": dict(ring_width=0.0019, latewood=0.22, early=(0.55, 0.40, 0.25), late=(0.36, 0.22, 0.12),
                       knot=(0.20, 0.10, 0.05), soot=(0.30, 0.22, 0.15), worn=(0.60, 0.46, 0.30), rough=0.62,
                       coat=0.0, coat_rough=0.3, raise_m=0.00012, fibre_m=0.00002, soot_amount=0.2, wear_color=0.2),
}


def _tex(nb, path, vec, closest=False):
    n = nb.node("ShaderNodeTexImage")
    n.image = bpy.data.images.load(str(path), check_existing=True)
    n.image.colorspace_settings.name = "Non-Color"
    n.interpolation = "Closest" if closest else "Linear"
    n.extension = "REPEAT"
    nb.feed(n.inputs["Vector"], vec)
    return n


def timber_material(name: str, preset: str, shared: dict, fallback_maps: dict | None = None):
    """The ring material. ``shared``: {RingNoise, RingRandom, Fibre} PNG paths
    (sora_timber_lib.shared_textures), sampled exactly as the Unreal masters do.
    ``fallback_maps``: {NormalDX, Masks} baked for the SM5 fallback, read on UV1
    instead of the vertex masks (the M_SoraTimber path); None is the Nanite path."""
    P = PRESETS[preset]
    nb = L.NB(name)
    q = nb.uv("UVLogQ")
    zl, seed, _ = nb.vxyz(nb.uv("UVLogZ"))
    length = nb.node("ShaderNodeVectorMath", operation="LENGTH")
    nb.link(q, length.inputs[0])
    r = length.outputs["Value"]
    uv0 = nb.uv("UV0")
    fibre = _tex(nb, shared["Fibre"], nb.vmul(uv0, 1.0 / 0.25))
    fib, streak, _ = nb.sep(fibre.outputs["Color"])
    drift = nb.sep(_tex(nb, shared["Fibre"], nb.vmul(uv0, 0.11)).outputs["Color"])[2]
    # Fibres deviate: the ring radius wanders by a quarter millimetre.
    r = nb.add(r, nb.mul(nb.sub(streak, 0.5), 0.00025))
    w = P["ring_width"]
    # Ring widths wander over ~6 rings: the log's row of T_TimberRingNoise.
    nu = nb.add(nb.div(r, 6.0 * w), nb.mul(seed, 37.0))
    nv = nb.m("FRACT", nb.mul(seed, 7.31))
    var = nb.sep(_tex(nb, shared["RingNoise"], nb.xyz(nu, nv, 0.0)).outputs["Color"])[0]
    phase = nb.add(nb.div(r, w), nb.mul(nb.sub(var, 0.5), 3.0))
    f = nb.m("FRACT", phase)
    ring = nb.m("FLOOR", phase)
    lwf = P["latewood"]
    # Earlywood darkens slowly, then the latewood band sets in over a tenth of
    # the ring; the next year's earlywood starts abruptly (f wraps to 0).
    late = nb.smoothstep(f, 1.0 - lwf - 0.07, 1.0 - lwf + 0.03)
    yu = nb.div(nb.add(ring, nb.mul(seed, 101.0)), 256.0)
    yv = nb.m("FRACT", nb.mul(seed, 3.7))
    year = nb.sep(_tex(nb, shared["RingRandom"], nb.xyz(yu, yv, 0.0), closest=True).outputs["Color"])[0]
    lw = nb.mul(late, nb.add(0.6, nb.mul(year, 0.4)))
    early = nb.mixc(nb.mul(f, 0.5), P["early"], tuple(c * 0.88 for c in P["early"]))
    base = nb.mixc(lw, early, P["late"])
    tone = nb.add(nb.add(0.74, nb.mul(year, 0.12)), nb.add(nb.mul(fib, 0.12), nb.add(nb.mul(streak, 0.12), nb.mul(drift, 0.22))))
    base = nb.hsv(base, v=tone)
    if fallback_maps:
        uv1 = nb.uv("UV1")
        mt = nb.node("ShaderNodeTexImage")
        mt.image = bpy.data.images.load(str(fallback_maps["Masks"]), check_existing=True)
        mt.image.colorspace_settings.name = "Non-Color"
        mt.image.alpha_mode = "CHANNEL_PACKED"
        nb.feed(mt.inputs["Vector"], uv1)
        cav, wear, soot = nb.sep(mt.outputs["Color"])
        knot = mt.outputs["Alpha"]
    else:
        vc = nb.node("ShaderNodeVertexColor", layer_name="Masks")
        cav, wear, soot = nb.sep(vc.outputs["Color"])
        knot = vc.outputs["Alpha"]
    base = nb.mixc(nb.mul(knot, 0.92), base, P["knot"])
    base = nb.mixc(nb.mul(soot, P["soot_amount"]), base, P["soot"])
    base = nb.mixc(nb.mul(wear, P["wear_color"]), base, P["worn"])
    base = nb.mixc(nb.mul(cav, 0.65), base, (0.0, 0.0, 0.0))
    rough = nb.add(P["rough"], nb.add(nb.mul(lw, 0.06), nb.sub(nb.mul(soot, 0.15), nb.mul(wear, 0.12))))
    rough = nb.add(rough, nb.mul(nb.sub(fib, 0.5), 0.12))
    coat_rough = nb.clamp01(nb.add(P["coat_rough"], nb.sub(nb.mul(soot, 0.16), nb.mul(wear, 0.08))))
    coat_rough = nb.clamp01(nb.add(coat_rough, nb.mul(nb.sub(streak, 0.5), 0.10)))
    # Uzukuri: the soft earlywood wears away and the latewood stands as a
    # rounded ridge, eased on both flanks.
    ridge = nb.mul(nb.smoothstep(f, 1.0 - lwf - 0.25, 1.0 - lwf + 0.05), nb.one_minus(nb.smoothstep(f, 0.82, 1.0)))
    height = nb.add(nb.mul(ridge, P["raise_m"]), nb.mul(fib, P["fibre_m"]))
    base_normal = None
    if fallback_maps:
        nt = nb.node("ShaderNodeTexImage")
        nt.image = bpy.data.images.load(str(fallback_maps["NormalDX"]), check_existing=True)
        nt.image.colorspace_settings.name = "Non-Color"
        nb.feed(nt.inputs["Vector"], nb.uv("UV1"))
        base_normal = nb.nmap_dx(nt.outputs["Color"], 1.0, uv_map="UV1")
    normal = nb.bump_m(height, normal=base_normal)
    coat_normal = nb.bump_m(nb.mul(height, 0.45), normal=base_normal)
    nb.feed(nb.bsdf.inputs["Base Color"], base)
    nb.feed(nb.bsdf.inputs["Roughness"], nb.clamp01(rough))
    nb.feed(nb.bsdf.inputs["Normal"], normal)
    nb.feed(nb.bsdf.inputs["Coat Weight"], P["coat"])
    nb.feed(nb.bsdf.inputs["Coat Roughness"], coat_rough)
    nb.feed(nb.bsdf.inputs["Coat IOR"], 1.52)
    nb.feed(nb.bsdf.inputs["Coat Normal"], coat_normal)
    return nb.mat


def clay_material(name="TimberClay"):
    """Neutral grey, no bump: shows what the geometry alone carries."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    b = mat.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (0.30, 0.30, 0.30, 1.0)
    b.inputs["Roughness"].default_value = 0.42
    return mat


def plain_material(name, color, rough):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    b = mat.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = rough
    return mat


def stage(width=1.8, height=7.0, infill_y=0.02):
    """A dojo bay around the column: polished dark floor, plaster infill at the
    kit's infill plane either side of the column."""
    objs = []
    floor_m = plain_material("LD_Floor", (0.09, 0.055, 0.035), 0.22)
    plaster_m = plain_material("LD_Plaster", (0.50, 0.44, 0.35), 0.85)
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0, -1.5, 0))
    fl = bpy.context.object
    fl.name = "LD_Floor"
    fl.scale = (8.0, 6.0, 1.0)
    fl.data.materials.append(floor_m)
    objs.append(fl)
    for side in (-1, 1):
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        w = bpy.context.object
        w.name = f"LD_Infill{side}"
        w.scale = (width / 2 - 0.12, 0.18, height)
        w.location = (side * (0.12 + (width / 2 - 0.12) / 2), infill_y + 0.09, height / 2)
        w.data.materials.append(plaster_m)
        objs.append(w)
    return objs


def raking_rig(scene, elevation=9.0, along=12.0):
    """Late sun grazing the room-facing (-Y) face from +X: reveals relief."""
    PL._clear_lights()
    PL._world_sky(scene, elevation, 90.0, 0.25)
    sun = PL._light("RV_RakeSun", "SUN", (0, 0, 5), (0, 0, 0), 5.0, color=(1.0, 0.70, 0.44), size=0.55)
    # Direction the light travels: from +X towards -X, skimming the -Y face.
    d = Vector((-math.cos(math.radians(along)), math.sin(math.radians(along)), -math.tan(math.radians(elevation))))
    sun.rotation_euler = (-d).to_track_quat("Z", "Y").to_euler()
    scene.view_settings.exposure = -0.3


def camera(scene, name, eye, target, lens):
    cam = bpy.data.objects.get(name)
    if cam is None:
        cam = bpy.data.objects.new(name, bpy.data.cameras.new(name))
        scene.collection.objects.link(cam)
    cam.data.lens = lens
    cam.location = eye
    cam.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    return cam


def render(scene, path: Path, size, samples=96):
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)
    return path
