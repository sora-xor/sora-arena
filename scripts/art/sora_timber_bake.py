"""Bake a unique timber's SM5 fallback maps from its dense Nanite source.

The fallback (``sora_timber_lib.fallback_of``) carries the macro shape; this
bakes what only the dense mesh has into the fallback's UV1 atlas:

* ``NormalDX``: tangent-space normals (DirectX green, 8-bit), the checks,
  dents, plane strokes, adze scoops, knot swell and arris detail. Tangents come
  from UV1, whose islands keep UV0's orientation (U along the perimeter, V
  along the member), so Unreal's UV0 MikkTSpace frame agrees.
* ``Masks``: the dense mesh's mask colours (R cavity, G wear, B soot, A knot),
  so the fallback keeps knots and check shadows its coarse vertices can't hold.

Blender 5.2, Cycles (GPU where available).
"""

from __future__ import annotations

from pathlib import Path

import bpy
import numpy as np


def _image(name, res, float_buffer, colorspace):
    img = bpy.data.images.get(name)
    if img is not None:
        bpy.data.images.remove(img)
    img = bpy.data.images.new(name, res, res, alpha=True, float_buffer=float_buffer)
    img.colorspace_settings.name = colorspace
    return img


def _bake_target_material(coarse, img):
    """A throwaway material on the fallback whose active node is the target image."""
    mat = bpy.data.materials.new(f"BAKE_{coarse.name}")
    mat.use_nodes = True
    nt = mat.node_tree
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UV1"
    nt.links.new(uv.outputs[0], tex.inputs["Vector"])
    nt.nodes.active = tex
    coarse.data.materials.clear()
    coarse.data.materials.append(mat)
    return mat


def _emit_material(name, source):
    """Emission of the Masks colour attribute: ``source`` is 'rgb' or 'alpha'."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    vc = nt.nodes.new("ShaderNodeVertexColor")
    vc.layer_name = "Masks"
    nt.links.new(vc.outputs["Color" if source == "rgb" else "Alpha"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return mat


def _select(dense, coarse):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    dense.hide_set(False)
    dense.hide_render = False
    coarse.hide_set(False)
    coarse.hide_render = False
    dense.select_set(True)
    coarse.select_set(True)
    bpy.context.view_layer.objects.active = coarse
    # The bake writes through, and takes its tangent frame from, UV1.
    coarse.data.uv_layers.active = coarse.data.uv_layers["UV1"]
    coarse.data.uv_layers["UV1"].active_render = True


def _pixels(img):
    a = np.empty(img.size[0] * img.size[1] * 4, np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(img.size[1], img.size[0], 4)


def _save(arr, path: Path, bits, colorspace="Non-Color"):
    h, w = arr.shape[:2]
    img = bpy.data.images.new(path.stem, w, h, alpha=True, float_buffer=bits == 16)
    img.colorspace_settings.name = colorspace
    img.pixels.foreach_set(np.ascontiguousarray(arr, np.float32).ravel())
    img.filepath_raw = str(path)
    img.file_format = "PNG"
    scene = bpy.context.scene
    settings = scene.render.image_settings
    settings.file_format = "PNG"
    settings.color_mode = "RGBA"
    settings.color_depth = str(bits)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save_render(str(path), scene=scene)
    bpy.data.images.remove(img)
    return path


def bake_fallback(dense, coarse, out_dir: Path, name: str, res=2048, extrusion=0.004, ray=0.045, samples=8):
    """Bake NormalDX and Masks for ``coarse`` from ``dense``; returns {kind: path}."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    bake = scene.render.bake
    bake.use_selected_to_active = True
    bake.cage_extrusion = extrusion
    bake.max_ray_distance = ray
    bake.margin = 16
    bake.margin_type = "EXTEND"
    bake.use_clear = True
    keep_dense = list(dense.data.materials)
    keep_coarse = list(coarse.data.materials)
    out = {}
    # Masks: RGB then alpha, each as emission from the dense mesh's colours.
    masks = np.zeros((res, res, 4), np.float32)
    for source in ("rgb", "alpha"):
        img = _image(f"{name}_Mask_{source}", res, True, "Non-Color")
        _bake_target_material(coarse, img)
        dense.data.materials.clear()
        dense.data.materials.append(_emit_material(f"BAKE_Emit_{source}", source))
        _select(dense, coarse)
        bpy.ops.object.bake(type="EMIT", use_selected_to_active=True, cage_extrusion=extrusion,
                            max_ray_distance=ray, margin=16)
        p = _pixels(img)
        bpy.data.images.remove(img)
        if source == "rgb":
            masks[..., :3] = p[..., :3]
        else:
            masks[..., 3] = p[..., 0]
    masks = np.clip(masks, 0, 1)
    out["Masks"] = _save(masks, out_dir / f"T_{name}_Masks.png", 8)
    dense.data.materials.clear()
    for m in keep_dense:
        dense.data.materials.append(m)
    # Normals.
    nimg = _image(f"{name}_Normal", res, True, "Non-Color")
    _bake_target_material(coarse, nimg)
    _select(dense, coarse)
    bake.normal_space = "TANGENT"
    bpy.ops.object.bake(type="NORMAL", normal_space="TANGENT", use_selected_to_active=True,
                        cage_extrusion=extrusion, max_ray_distance=ray, margin=16)
    n = _pixels(nimg)
    bpy.data.images.remove(nimg)
    # Both meshes carry the checks as geometry, at different resolutions; what
    # the bake records inside a crack is the coarse groove's facets, not detail.
    # Flatten it there (the fallback's own groove shades the crack, the baked
    # cavity darkens it), feathered over the band the groove's samples cover.
    crack = (masks[..., 0] > 0.25).astype(np.float32)
    for _ in range(3):
        crack = np.maximum.reduce([crack, np.roll(crack, 1, 0), np.roll(crack, -1, 0),
                                   np.roll(crack, 1, 1), np.roll(crack, -1, 1)])
    feather = crack.copy()
    for _ in range(2):
        feather = (feather + np.roll(feather, 1, 0) + np.roll(feather, -1, 0) + np.roll(feather, 1, 1)
                   + np.roll(feather, -1, 1)) / 5.0
    flat = np.array([0.5, 0.5, 1.0], np.float32)
    n[..., :3] = n[..., :3] * (1.0 - feather[..., None]) + flat * feather[..., None]
    n[..., 1] = 1.0 - n[..., 1]          # OpenGL (Blender) -> DirectX (Unreal) green
    n[..., 3] = 1.0
    out["NormalDX"] = _save(n, out_dir / f"T_{name}_NormalDX.png", 8)   # BC5 keeps 8 bits per channel
    coarse.data.materials.clear()
    for m in keep_coarse:
        coarse.data.materials.append(m)
    return out
