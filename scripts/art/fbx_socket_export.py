"""The FBX convention for meshes whose SOCKET_ empties UE 5.8 must import on their own axes at scale 1.

The convention is Blender's own axes, which are Unreal's FBX import axes, with the unit baked into the vertices and
the socket translations. No importer converts the file, and no node carries a rotation or a scale.

The Inventory drone uses it first (create_inventory_drone.LOD0_FBX, 45a2af0a). fbx_unreal_sockets.py has the
reason: Interchange turns each socket by the inverse axis conversion and keeps its parent's scale.

The runtime weapon library's own export (create_runtime_weapon_lib.py split_and_export) writes -Y forward with
x100 on the mesh node. It is digest-frozen and stays as it is. This module copies everything else of its LOD0
export, so a socketed LOD0 re-exported here differs only in the convention. test_weapon_socket_export.py holds
both to that.

bpy is imported only inside export(); the rest is pure, for the CPU tests.
"""

import hashlib
from pathlib import Path

# The convention: create_inventory_drone.LOD0_FBX's values.
SOCKET_FBX = dict(apply_unit_scale=True, apply_scale_options="FBX_SCALE_NONE", global_scale=1.0,
                  axis_forward="Y", axis_up="Z", bake_space_transform=True)
# The rest of the library's LOD0 export call, unchanged.
LIBRARY_LOD0_REST = dict(object_types={"MESH", "EMPTY"}, mesh_smooth_type="FACE", use_tspace=True, use_triangles=True,
                         use_mesh_modifiers=True, add_leaf_bones=False, bake_anim=False, path_mode="STRIP",
                         embed_textures=False, use_custom_props=False)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def export(path, mesh, empties):
    """Write mesh and its SOCKET_ empties to path in the socket convention (Blender only)."""
    import bpy
    for obj in bpy.context.view_layer.objects:
        obj.select_set(False)
    for obj in (mesh, *empties):
        obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, **SOCKET_FBX, **LIBRARY_LOD0_REST)


def socket_axes(empties):
    """Each socket's unit X (forward) and Z axes in its mesh's Blender frame, from the empties' own matrices."""
    out = {}
    for e in empties:
        m = e.matrix_basis.to_3x3().normalized()
        out[e.name[len("SOCKET_"):]] = {"x": [round(c, 6) for c in m.col[0]], "z": [round(c, 6) for c in m.col[2]]}
    return out


def convention_record(tool):
    """The record block a re-export writes beside the files it rewrote."""
    return {"export": dict(SOCKET_FBX),
            "axes": "Blender's own (up Z, forward Y), which are UE 5.8's FBX import axes (Z up, -Y front, "
                    "right-handed). The file declares them, so no importer converts it",
            "unit": "centimetres, baked into the vertices and the socket translations. No node carries a rotation "
                    "or a scale, so each socket imports at scale 1 on its own axes",
            "gate": "scripts/art/screen_fbx_sockets.py, through scripts/art/fbx_unreal_sockets.py (Interchange's "
                    "socket rule, calibrated on root's import of the drone's fc0858a9)",
            "unchanged": "LODs without sockets keep the library's convention (-Y forward, x100 on the node). "
                         "Unreal bakes both conventions to the same vertices",
            "rewritten_by": tool}


def amend_record(record, rewritten, axes, tool):
    """The kit record after a socket re-export.

    rewritten: {asset: (lod0 file, new sha256, old sha256)}; axes: {asset: socket_axes}. LOD0's hash and the
    asset's socket_axes change; a top-level "socket_fbx" block lists the files. Nothing else changes.
    """
    out = dict(record)
    out["assets"] = {k: dict(v) for k, v in record["assets"].items()}
    files = []
    for asset, (file, new, old) in sorted(rewritten.items()):
        entry = out["assets"][asset]
        lods = [dict(l) for l in entry["lods"]]
        if lods[0]["file"] != file or lods[0]["sha256"] != old:
            raise ValueError(f"{asset}: LOD0 is not {file} at {old}")
        lods[0]["sha256"] = new
        entry["lods"] = lods
        entry["socket_axes"] = axes[asset]
        files.append({"file": file, "sha256": new, "replaces_sha256": old})
    out["socket_fbx"] = {**convention_record(tool), "files": files}
    return out
