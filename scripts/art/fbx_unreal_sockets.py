"""What UE 5.8's Interchange FBX import makes of a static mesh's sockets and vertices, from the FBX's own nodes.

It is the gate for the Inventory drone's LOD0. Root's import of fc0858a9 (0eb8c5e) read both sockets at scale 100
with +X reversed, positions right, while the Blender round trip passed.

**What Interchange does** (the installed UE 5.8 source, read 2026-10-26):
- **The axes** (Plugins/Interchange/Runtime/Source/Parsers/Fbx/Private/FbxConvert.cpp, ConvertScene). When the
  file's axis system is not the import axis (Z up, -Y front, right-handed, with Force Front X Axis off), the scene
  is converted by the rotation C between them. The vertices and positions of root's real imports confirm C.
- **The unit.** A centimetre file (UnitScaleFactor 1) is not converted.
- **A baked vertex** (Bake Meshes, the static-mesh default) is C G v, where G is its node's global transform.
- **A socket** (Import/Private/Mesh/InterchangeMeshHelper.cpp, ImportSockets) is its node's global transform with
  an inverse applied first, `AxisConversionInverseTransform * Transform`: so C G A^-1.
  - A socket carries the scale of every node above it.
  - A^-1 is not C^-1. FbxConvert.cpp derives it from FbxAxisSystem::GetMatrix, whose source the FBX SDK does not
    ship, so it is modelled only where a real import measured it (SOCKET_INVERSE).
- **Into Unreal's frame** (FbxConvert ConvertTransform and ConvertPos): y is negated.

**The measurement.** For Blender's ('Z', '-Y') axes, the runtime weapon library's, C is a 180 deg turn about Z.
Root's import of the drone's fc0858a9 read the sockets' rotators as (0, -180, 180) and (45, -180, 180). So each
socket's forward and up are reversed and its right is kept: A^-1 is a 180 deg turn about Y.
- The first version of this module (45a2af0a) used C^-1, a turn about Z. It matched that import's forward vectors,
  positions and scales, which were all it compared, but it predicted the up axes kept.

test_fbx_unreal_sockets.py checks the rule against both of root's real imports, rotators included.

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
# Blender's ('Z', '-Y') axes, which the runtime weapon library exports: Maya Z-up (Z up, +Y front, -X coord).
LIBRARY_AXES = {"UpAxis": (2, 1), "FrontAxis": (1, 1), "CoordAxis": (0, -1)}
# Interchange's socket inverse A^-1, only for the file axes a real UE 5.8 import measured it in.
# - Unreal's own axes: there is no conversion, so it is the identity (root's import of 45a2af0a).
# - The library's: a 180 deg turn about Y (root's import of fc0858a9, rotators (0, -180, 180) and (45, -180, 180)).
SOCKET_INVERSE = ((UNREAL_IMPORT_AXES, np.eye(3)), (LIBRARY_AXES, np.diag([-1.0, 1.0, -1.0])))
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


def socket_inverse(axes):
    """Interchange's measured socket inverse A^-1 for these file axes (SOCKET_INVERSE); other axes are refused."""
    for known, inverse in SOCKET_INVERSE:
        if axes == known:
            return inverse
    raise ValueError(f"no real import has measured the socket inverse for the file axes {axes}")


def interchange(scene):
    """Unreal's sockets and baked vertices for a parsed scene (read_fbx), in Unreal's frame and the file's unit.

    sockets[name]: position_cm, scale (the lengths of the transform's axes), x, y and z (its unit axes: forward,
    right and up), det. vertices[mesh]: (n, 3).
    """
    if not abs(scene["unit"] - 1.0) <= 1e-12:
        raise ValueError(f"UnitScaleFactor {scene['unit']}: only centimetre files are modelled")
    for name, node in scene["nodes"].items():         # nonfinite input is refused, never carried through as NaN
        if not all(np.isfinite(np.asarray(node[k], float)).all() for k in ("T", "R", "S")):
            raise ValueError(f"{name}: a nonfinite node transform {node['T']} {node['R']} {node['S']}")
        if node["vertices"] is not None and not np.isfinite(node["vertices"]).all():
            raise ValueError(f"{name}: nonfinite vertices")
    c = np.eye(4)
    c[:3, :3] = conversion(scene["axes"])
    nodes = scene["nodes"]
    sockets, vertices = {}, {}
    if any(name.startswith("SOCKET_") for name in nodes):
        inverse = np.eye(4)
        inverse[:3, :3] = socket_inverse(scene["axes"])
    for name, node in nodes.items():
        g = global_matrix(nodes, name)
        if name.startswith("SOCKET_"):
            m = MIRROR @ c @ g @ inverse @ MIRROR
            lengths = np.linalg.norm(m[:3, :3], axis=0)
            unit_axes = m[:3, :3] / lengths
            sockets[name[len("SOCKET_"):]] = {"position_cm": m[:3, 3], "scale": lengths, "x": unit_axes[:, 0],
                                              "y": unit_axes[:, 1], "z": unit_axes[:, 2],
                                              "det": float(np.linalg.det(unit_axes))}
        if node["vertices"] is not None:
            m = MIRROR @ c @ g
            vertices[name] = node["vertices"] @ m[:3, :3].T + m[:3, 3]
    return {"conversion": c[:3, :3], "sockets": sockets, "vertices": vertices}


def rotator_axes(pitch, yaw, roll):
    """An Unreal FRotator's unit X (forward), Y (right) and Z (up) axes, as rows of FRotationMatrix."""
    sp, cp = math.sin(math.radians(pitch)), math.cos(math.radians(pitch))
    sy, cy = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
    sr, cr = math.sin(math.radians(roll)), math.cos(math.radians(roll))
    return (np.array([cp * cy, cp * sy, sp]), np.array([sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp]),
            np.array([-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp]))


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
