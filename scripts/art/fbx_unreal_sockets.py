"""What UE 5.8's Interchange FBX import makes of a static mesh's sockets and vertices, from the FBX's own nodes.

It is the gate for the Inventory drone's LOD0. Root's import of fc0858a9 (0eb8c5e) read both sockets at scale 100
with +X reversed, positions right, while the Blender round trip passed.

**What Interchange does** (the installed UE 5.8 source, read 2026-10-26):
- **The axes** (Plugins/Interchange/Runtime/Source/Parsers/Fbx/Private/FbxConvert.cpp, ConvertScene). When the
  file's axis system is not the import axis (Z up, -Y front, right-handed, with Force Front X Axis off), the scene
  is converted by the rotation C between them, and C^-1 is kept for the sockets.
- **The unit.** A centimetre file (UnitScaleFactor 1) is not converted.
- **A baked vertex** (Bake Meshes, the static-mesh default) is C G v, where G is its node's global transform.
- **A socket** (Import/Private/Mesh/InterchangeMeshHelper.cpp, ImportSockets) is its node's global transform with
  C^-1 applied first, `AxisConversionInverseTransform * Transform`: so C G C^-1.
  - When C is not the identity, a socket's own axes turn by C^-1 and the vertices do not.
  - A socket carries the scale of every node above it.
- **Into Unreal's frame** (FbxConvert ConvertTransform and ConvertPos): y is negated.

test_fbx_unreal_sockets.py checks that this reproduces root's actual readback of fc0858a9.

It is pure Python and numpy. The FBX is parsed by Blender's own io_scene_fbx.parse_fbx.
"""

import importlib
import math
import os
import sys
import types
from pathlib import Path

import numpy as np

# Blender's own axes, ('Z', 'Y') in io_scene_fbx/fbx_utils.py RIGHT_HAND_AXES, as (axis, sign). They are UE 5.8's
# FBX import axes, FbxAxisSystem(eZAxis, -eParityOdd, eRightHanded): Z up, -Y front, +X coord.
UNREAL_IMPORT_AXES = {"UpAxis": (2, 1), "FrontAxis": (1, -1), "CoordAxis": (0, 1)}
MIRROR = np.diag([1.0, -1.0, 1.0, 1.0])            # right-handed FBX to Unreal: y negated
# Node properties this model does not compose. A file that sets any of them away from its default is refused.
DEFAULTS = {"PreRotation": (0, 0, 0), "PostRotation": (0, 0, 0), "RotationOffset": (0, 0, 0),
            "RotationPivot": (0, 0, 0), "ScalingOffset": (0, 0, 0), "ScalingPivot": (0, 0, 0),
            "GeometricTranslation": (0, 0, 0), "GeometricRotation": (0, 0, 0), "GeometricScaling": (1, 1, 1),
            "RotationOrder": (0,), "InheritType": (1,)}
BLENDER_FBX = Path(os.environ.get("BLENDER_FBX_ADDON",
                                  "/Applications/Blender.app/Contents/Resources/5.2/scripts/addons_core/io_scene_fbx"))


def parser():
    """Blender's parse_fbx.

    Inside Blender it is imported as usual. Elsewhere it is loaded from Blender's bundle, without the add-on's
    __init__, which needs bpy. parse_fbx itself needs only data_types and fbx_utils_threading, which are pure Python.
    """
    try:
        from io_scene_fbx import parse_fbx
        return parse_fbx
    except ImportError:
        pass
    if not (BLENDER_FBX / "parse_fbx.py").is_file():
        raise ImportError(f"no Blender FBX parser at {BLENDER_FBX}")
    if "blender_fbx_parse" not in sys.modules:
        pkg = types.ModuleType("blender_fbx_parse")
        pkg.__path__ = [str(BLENDER_FBX)]
        sys.modules["blender_fbx_parse"] = pkg
    return importlib.import_module("blender_fbx_parse.parse_fbx")


def _child(elem, name):
    return next((c for c in elem.elems if c.id == name), None)


def _props(elem):
    p = _child(elem, b"Properties70")
    return {c.props[0].decode(): list(c.props[4:]) for c in (p.elems if p is not None else [])}


def read_fbx(path):
    """The file's axes and unit, and its Model nodes: type, FBX parent, local T, R (degrees) and S, and the
    vertices of each mesh's geometry in the node's own space. Raises on a node property the model does not compose."""
    root, _version = parser().parse(str(path))
    g = _props(_child(root, b"GlobalSettings"))
    axes = {k: (int(g[k][0]), int(g[k + "Sign"][0])) for k in ("UpAxis", "FrontAxis", "CoordAxis")}
    unit = float(g.get("UnitScaleFactor", [1.0])[0])
    objects = {o.props[0]: o for o in _child(root, b"Objects").elems}
    parent, geometry = {}, {}
    for c in _child(root, b"Connections").elems:
        src = objects.get(c.props[1])
        if c.props[0] != b"OO" or src is None:
            continue
        if src.id == b"Model":
            parent[c.props[1]] = c.props[2]
        elif src.id == b"Geometry" and src.props[2] == b"Mesh":
            geometry[c.props[2]] = src
    name = lambda o: o.props[1].split(b"\x00\x01")[0].decode()  # noqa: E731
    nodes = {}
    for uid, o in objects.items():
        if o.id != b"Model":
            continue
        p = _props(o)
        for key, default in DEFAULTS.items():
            if key in p and not np.allclose(np.array(p[key], float), default, atol=1e-9):
                raise ValueError(f"{name(o)}: {key} {p[key]} is not modelled")
        geo = geometry.get(uid)
        par = objects.get(parent.get(uid))
        nodes[name(o)] = {
            "type": o.props[2].decode(), "parent": name(par) if par is not None and par.id == b"Model" else None,
            "T": tuple(float(v) for v in p.get("Lcl Translation", (0, 0, 0))),
            "R": tuple(float(v) for v in p.get("Lcl Rotation", (0, 0, 0))),
            "S": tuple(float(v) for v in p.get("Lcl Scaling", (1, 1, 1))),
            "vertices": (np.array(_child(geo, b"Vertices").props[0], float).reshape(-1, 3)
                         if geo is not None else None)}
    return {"axes": axes, "unit": unit, "nodes": nodes}


def euler_xyz(degrees):
    """FBX eEulerXYZ: about X first, then Y, then Z, all about the parent's axes."""
    rx, ry, rz = (math.radians(a) for a in degrees)
    x = np.array([[1, 0, 0], [0, math.cos(rx), -math.sin(rx)], [0, math.sin(rx), math.cos(rx)]])
    y = np.array([[math.cos(ry), 0, math.sin(ry)], [0, 1, 0], [-math.sin(ry), 0, math.cos(ry)]])
    z = np.array([[math.cos(rz), -math.sin(rz), 0], [math.sin(rz), math.cos(rz), 0], [0, 0, 1]])
    return z @ y @ x


def local_matrix(node):
    m = np.eye(4)
    m[:3, :3] = euler_xyz(node["R"]) @ np.diag(node["S"])
    m[:3, 3] = node["T"]
    return m


def global_matrix(nodes, name):
    node = nodes[name]
    m = local_matrix(node)
    return global_matrix(nodes, node["parent"]) @ m if node["parent"] else m


def axis_frame(axes):
    """Columns: the file's coord, front and up vectors."""
    frame = np.zeros((3, 3))
    for col, key in enumerate(("CoordAxis", "FrontAxis", "UpAxis")):
        axis, sign = axes[key]
        frame[axis, col] = sign
    return frame


def conversion(axes):
    """C, which takes the file's coord, front and up vectors to the import axis's."""
    return axis_frame(UNREAL_IMPORT_AXES) @ np.linalg.inv(axis_frame(axes))


def interchange(scene):
    """Unreal's sockets and baked vertices for a parsed scene (read_fbx), in Unreal's frame and the file's unit.

    sockets[name]: position_cm, scale (the lengths of the transform's axes), x and z (its unit axes; x is the
    socket's forward), det. vertices[mesh]: (n, 3).
    """
    if abs(scene["unit"] - 1.0) > 1e-12:
        raise ValueError(f"UnitScaleFactor {scene['unit']}: only centimetre files are modelled")
    c = np.eye(4)
    c[:3, :3] = conversion(scene["axes"])
    nodes = scene["nodes"]
    sockets, vertices = {}, {}
    for name, node in nodes.items():
        g = global_matrix(nodes, name)
        if name.startswith("SOCKET_"):
            m = MIRROR @ c @ g @ np.linalg.inv(c) @ MIRROR
            lengths = np.linalg.norm(m[:3, :3], axis=0)
            unit_axes = m[:3, :3] / lengths
            sockets[name[len("SOCKET_"):]] = {"position_cm": m[:3, 3], "scale": lengths, "x": unit_axes[:, 0],
                                              "z": unit_axes[:, 2], "det": float(np.linalg.det(unit_axes))}
        if node["vertices"] is not None:
            m = MIRROR @ c @ g
            vertices[name] = node["vertices"] @ m[:3, :3].T + m[:3, 3]
    return {"conversion": c[:3, :3], "sockets": sockets, "vertices": vertices}


def to_unreal(blender_m):
    """A Blender point in metres, as Unreal centimetres: 100 x (x, -y, z)."""
    return np.array([100.0 * blender_m[0], -100.0 * blender_m[1], 100.0 * blender_m[2]])


def to_unreal_axis(blender_axis):
    return np.array([blender_axis[0], -blender_axis[1], blender_axis[2]], float)


def geometry_arrays(path):
    """Each mesh's geometry arrays as the file holds them, by its Model's name: vertices, polygon indices, and
    every layer element's data and index arrays (normals, tangents, binormals, UVs, materials)."""
    root, _version = parser().parse(str(path))
    objects = {o.props[0]: o for o in _child(root, b"Objects").elems}
    owner = {}
    for c in _child(root, b"Connections").elems:
        src, dst = objects.get(c.props[1]), objects.get(c.props[2])
        if src is not None and dst is not None and src.id == b"Geometry" and dst.id == b"Model":
            owner[c.props[1]] = dst.props[1].split(b"\x00\x01")[0].decode()
    out = {}
    for uid, o in objects.items():
        if o.id != b"Geometry" or o.props[2] != b"Mesh":
            continue
        arrays = {}
        for e in o.elems:
            if e.id in (b"Vertices", b"PolygonVertexIndex", b"Edges"):
                arrays[e.id.decode()] = np.array(e.props[0])
            elif e.id.startswith(b"LayerElement"):
                for sub in e.elems:
                    if sub.props and hasattr(sub.props[0], "__len__") and not isinstance(sub.props[0], (bytes, str)):
                        arrays[f"{e.id.decode()}[{e.props[0]}].{sub.id.decode()}"] = np.array(sub.props[0])
        out[owner[uid]] = arrays
    return out
