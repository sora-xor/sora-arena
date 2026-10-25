"""Blender look-dev material for the v2 pilot timbers (sora-timber-geometry-v2).

This is ``sora_timber_lookdev.timber_material``, which stays frozen as an input
of the v1 kit, with the three v2 changes:

* **Ring width:** the member's own (``ring_width``), as the Unreal instances
  set it, not the preset's 0.0019 m.
* **Wander:** the corrected ring-width wander of sora_timber_v2
  (``WANDER_RINGS_PER_UNIT``, ``WANDER_AMPLITUDE``), so the shaded latewood is
  the same phase the geometry's raised grain is cut from.
* **Relief:** the latewood ridge is real geometry now. The shader keeps only a
  small supplementary raise (``raise_m``) and the fibre bump.

Review renders only. Blender 5.2.
"""
from __future__ import annotations

import sys
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import create_runtime_weapon_lib as L  # noqa: E402
import sora_timber_lookdev as LD  # noqa: E402
import sora_timber_v2 as V  # noqa: E402

SUPPLEMENT_RAISE_M = 0.000005


def timber_material(name: str, preset: str, shared: dict, ring_width: float, fallback_maps: dict | None = None):
    P = dict(LD.PRESETS[preset])
    nb = L.NB(name)
    q = nb.uv("UVLogQ")
    zl, seed, _ = nb.vxyz(nb.uv("UVLogZ"))
    length = nb.node("ShaderNodeVectorMath", operation="LENGTH")
    nb.link(q, length.inputs[0])
    r = length.outputs["Value"]
    uv0 = nb.uv("UV0")
    fibre = LD._tex(nb, shared["Fibre"], nb.vmul(uv0, 1.0 / 0.25))
    fib, streak, _ = nb.sep(fibre.outputs["Color"])
    drift = nb.sep(LD._tex(nb, shared["Fibre"], nb.vmul(uv0, 0.11)).outputs["Color"])[2]
    r = nb.add(r, nb.mul(nb.sub(streak, 0.5), 0.00025))
    w = ring_width
    # v2 wander: about 3.4 texels of the log's RingNoise row per ring.
    nu = nb.add(nb.div(r, V.WANDER_RINGS_PER_UNIT * w), nb.mul(seed, 37.0))
    nv = nb.m("FRACT", nb.mul(seed, 7.31))
    var = nb.sep(LD._tex(nb, shared["RingNoise"], nb.xyz(nu, nv, 0.0)).outputs["Color"])[0]
    phase = nb.add(nb.div(r, w), nb.mul(nb.sub(var, 0.5), V.WANDER_AMPLITUDE))
    f = nb.m("FRACT", phase)
    ring = nb.m("FLOOR", phase)
    lwf = P["latewood"]
    late = nb.smoothstep(f, 1.0 - lwf - 0.07, 1.0 - lwf + 0.03)
    yu = nb.div(nb.add(ring, nb.mul(seed, 101.0)), 256.0)
    yv = nb.m("FRACT", nb.mul(seed, 3.7))
    year = nb.sep(LD._tex(nb, shared["RingRandom"], nb.xyz(yu, yv, 0.0), closest=True).outputs["Color"])[0]
    lw = nb.mul(late, nb.add(0.6, nb.mul(year, 0.4)))
    early = nb.mixc(nb.mul(f, 0.5), P["early"], tuple(c * 0.88 for c in P["early"]))
    base = nb.mixc(lw, early, P["late"])
    tone = nb.add(nb.add(0.68, nb.mul(year, 0.12)), nb.add(nb.mul(fib, 0.12), nb.add(nb.mul(streak, 0.12), nb.mul(drift, 0.34))))
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
    grime = nb.clamp01(nb.mul(wear, 2.0))
    edge = nb.clamp01(nb.sub(nb.mul(wear, 2.0), 1.0))
    base = nb.mixc(nb.mul(knot, 0.92), base, P["knot"])
    base = nb.mixc(nb.mul(soot, P["soot_amount"]), base, P["soot"])
    base = nb.mixc(nb.mul(grime, 0.55), base, tuple(c * 0.62 for c in P["early"]))
    base = nb.mixc(nb.mul(edge, P["wear_color"]), base, P["worn"])
    base = nb.mixc(nb.mul(cav, 0.65), base, (0.0, 0.0, 0.0))
    rough = nb.add(P["rough"], nb.add(nb.mul(lw, 0.06), nb.sub(nb.mul(soot, 0.15), nb.mul(edge, 0.12))))
    rough = nb.add(rough, nb.mul(nb.sub(fib, 0.5), 0.12))
    coat_rough = nb.clamp01(nb.add(P["coat_rough"], nb.sub(nb.mul(soot, 0.16), nb.mul(grime, 0.08))))
    coat_rough = nb.clamp01(nb.add(coat_rough, nb.mul(nb.sub(streak, 0.5), 0.10)))
    ridge = nb.mul(nb.smoothstep(f, 1.0 - lwf - 0.25, 1.0 - lwf + 0.05), nb.one_minus(nb.smoothstep(f, 0.82, 1.0)))
    height = nb.add(nb.mul(ridge, SUPPLEMENT_RAISE_M), nb.mul(fib, P["fibre_m"]))
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
