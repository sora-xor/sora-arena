"""Independent Blender geometry check for the byte-pinned, user-supplied SORA kamon."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path

import bpy
from mathutils import Vector, kdtree


PINNED_SVG_SHA256 = "d66413a71b70e25dcb8b2f118dcfe846a6446ed1db3de53ce88fc70c16ac0910"


def reference_paths(root: Path):
    """Tessellate a fresh copy of each SVG path, normalized to a unit-square mark."""
    svg = root / "Content/SourceArt/UI/sora_logo_NOtext2.svg"
    record = json.loads((svg.parent / "sora_logo_manifest.json").read_text())
    assert hashlib.sha256(svg.read_bytes()).hexdigest() == PINNED_SVG_SHA256
    assert record["source_sha256"] == PINNED_SVG_SHA256
    before = set(bpy.data.objects)
    bpy.ops.import_curve.svg(filepath=str(svg))
    curves = [obj for obj in set(bpy.data.objects) - before if obj.type == "CURVE"]
    assert len(curves) == 2, [obj.name for obj in curves]
    corners = [obj.matrix_world @ Vector(corner) for obj in curves for corner in obj.bound_box]
    min_x, max_x = min(p.x for p in corners), max(p.x for p in corners)
    min_y, max_y = min(p.y for p in corners), max(p.y for p in corners)
    origin_x, origin_y = (min_x + max_x) / 2, (min_y + max_y) / 2
    size = max(max_x-min_x, max_y-min_y)
    assert size > 0
    paths = []
    for obj in curves:
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.convert(target="MESH")
        obj = bpy.context.object
        paths.append([(((obj.matrix_world @ vert.co).x-origin_x) / size,
                       ((obj.matrix_world @ vert.co).y-origin_y) / size)
                      for vert in obj.data.vertices])
        bpy.data.objects.remove(obj, do_unlink=True)
    assert all(len(path) > 20 for path in paths)
    return paths


def expected_paths(paths, center, diameter, plane):
    if plane == "YZ":
        return [[(center[0], center[1]+u*diameter, center[2]+v*diameter)
                 for u,v in path] for path in paths]
    assert plane == "XZ"
    return [[(center[0]+u*diameter, center[1], center[2]+v*diameter)
             for u,v in path] for path in paths]


def rounded_points(points):
    return Counter(tuple(round(float(x), 5) for x in xyz) for xyz in points)


def assert_path_objects(objects, placement, expected):
    matches = [obj for obj in objects if obj.name.startswith(f"UserSupplied_SORAKamon_{placement}_Path_")]
    assert len(matches) == 2, (placement, [obj.name for obj in matches])
    unmatched = [rounded_points(path) for path in expected]
    for obj in matches:
        assert obj.get("source_svg_sha256") == PINNED_SVG_SHA256
        assert obj.get("kamon_placement") == placement
        assert obj.get("kamon_path_index") in (0, 1)
        sample = rounded_points((obj.matrix_world @ v.co for v in obj.data.vertices))
        assert sample in unmatched, (placement, obj.name, len(sample))
        unmatched.remove(sample)
    assert not unmatched


def assert_paths_embedded(vertices, placements):
    """Check all SVG-derived vertices survive joining and FBX export."""
    available = [Vector(vertex) for vertex in vertices]
    tree = kdtree.KDTree(len(available))
    for index, vertex in enumerate(available):
        tree.insert(vertex, index)
    tree.balance()
    for placement, expected in placements.items():
        for path in expected:
            missing = [point for point in path if tree.find(Vector(point))[2] > .00002]
            assert not missing, (placement, len(missing), missing[:3])
