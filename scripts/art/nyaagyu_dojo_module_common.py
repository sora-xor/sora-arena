"""Shared, Blender-only geometry checks for the source-only Dojo split."""

from __future__ import annotations

from collections import Counter
import hashlib

from mathutils import Vector


STEM_COUNTS = {
    "Cedar_Post": 10,
    "Dojo_FrontSign": 1, "Dojo_JapaneseSign": 1,
    "Eave_Bracket": 28, "Eave_Fascia": 2,
    "Engawa_Board": 13, "Engawa_Foot": 3,
    "Exposed_Rafter": 18,
    "Floor_Joist": 5, "Foundation_Core": 1,
    "FrontBack_Quoin": 50, "Front_Engawa": 1,
    "Gable_Nuki": 6, "Gable_Plaster": 6, "Gable_PlasterTriangle": 2,
    "Gable_Post": 8, "Gable_Quoin": 50, "Gable_TimberDiagonal": 4,
    "Gable_Vergebord": 4, "Gable_Wainscot": 6, "Gable_WainscotSeam": 30,
    "Kamon_Disc": 2,
    "Kawara_CurvedTileCourses": 1, "Kawara_Overlap": 22,
    "Lantern_Bracket": 2, "Lantern_Frame": 2, "Lantern_Glow": 2,
    "Lantern_Horiz": 4, "Lantern_Vert": 4,
    "Nuki_FrontBack": 6, "Raised_Timber": 1,
    "Rear_Plaster": 4, "Rear_Wainscot": 4,
    "Ridge_RoundCap": 34, "Roof_Ceiling": 1,
    "Shikidai_Step": 3,
    "Shoji_Jamb": 8, "Shoji_KumikoH": 32, "Shoji_KumikoV": 16,
    "Shoji_Paper": 4, "Shoji_Pull": 4,
    "Underfloor_Pier": 15, "UserSupplied_SORAKamon": 4,
}

MODULE_STEMS = {
    "Roof": {
        "Kawara_CurvedTileCourses", "Kawara_Overlap", "Ridge_RoundCap",
        "Gable_Vergebord", "Gable_PlasterTriangle", "Gable_TimberDiagonal",
    },
    "Eaves": {"Roof_Ceiling", "Exposed_Rafter", "Eave_Fascia", "Eave_Bracket"},
    "Shoji": {
        "Shoji_Paper", "Shoji_Jamb", "Shoji_KumikoH", "Shoji_KumikoV",
        "Shoji_Pull", "Front_Engawa", "Engawa_Board", "Engawa_Foot",
        "Shikidai_Step", "Dojo_FrontSign", "Dojo_JapaneseSign",
        "Kamon_Disc", "UserSupplied_SORAKamon", "Lantern_Bracket",
        "Lantern_Frame", "Lantern_Glow", "Lantern_Horiz", "Lantern_Vert",
    },
    "Body": {
        "Cedar_Post", "Floor_Joist", "Foundation_Core", "FrontBack_Quoin",
        "Gable_Nuki", "Gable_Plaster", "Gable_Post", "Gable_Quoin",
        "Gable_Wainscot", "Gable_WainscotSeam", "Nuki_FrontBack",
        "Raised_Timber", "Rear_Plaster", "Rear_Wainscot", "Underfloor_Pier",
    },
}
assert set().union(*MODULE_STEMS.values()) == set(STEM_COUNTS)
assert sum(map(len, MODULE_STEMS.values())) == len(STEM_COUNTS)


def stem(name: str) -> str:
    return "_".join(name.split("_")[:2])


def classify(parts) -> dict[str, list]:
    counts = Counter(stem(obj.name) for obj in parts)
    if counts != STEM_COUNTS:
        raise AssertionError(f"Dojo part inventory changed: {counts - Counter(STEM_COUNTS)}; "
                             f"missing={Counter(STEM_COUNTS) - counts}")
    result = {name: [] for name in MODULE_STEMS}
    for obj in sorted(parts, key=lambda item: item.name):
        matches = [name for name, stems in MODULE_STEMS.items() if stem(obj.name) in stems]
        if len(matches) != 1:
            raise AssertionError((obj.name, matches))
        result[matches[0]].append(obj)
    if [len(result[name]) for name in ("Roof", "Eaves", "Body", "Shoji")] != [67, 49, 202, 106]:
        raise AssertionError("Dojo module part counts changed")
    return result


def material_name(obj, polygon) -> str:
    slot = obj.material_slots[polygon.material_index]
    if not slot.material:
        raise AssertionError((obj.name, polygon.index, "missing material"))
    return slot.material.name.split(".", 1)[0]


def triangle_records(objects) -> list[str]:
    """World-space oriented triangle multiset, quantized to 10 micrometres."""
    records = []
    for obj in objects:
        if obj.type != "MESH":
            raise AssertionError((obj.name, obj.type))
        world = obj.matrix_world
        data = obj.data
        for poly in data.polygons:
            points = []
            for vertex_id in poly.vertices:
                pos = world @ data.vertices[vertex_id].co
                points.append(tuple(round(float(pos[axis]) * 100000) for axis in range(3)))
            mat = material_name(obj, poly)
            for index in range(1, len(points) - 1):
                tri = (points[0], points[index], points[index + 1])
                canonical = min((tri[0], tri[1], tri[2]),
                                (tri[1], tri[2], tri[0]),
                                (tri[2], tri[0], tri[1]))
                records.append(f"{mat}|{canonical}")
    records.sort()
    return records


def triangle_digest(records: list[str]) -> str:
    return hashlib.sha256("\n".join(records).encode()).hexdigest()


def world_bounds(objects) -> dict[str, list[float]]:
    points = [obj.matrix_world @ vertex.co
              for obj in objects for vertex in obj.data.vertices]
    if not points:
        raise AssertionError("Dojo geometry has no vertices")
    return {
        "min": [round(min(p[axis] for p in points), 6) for axis in range(3)],
        "max": [round(max(p[axis] for p in points), 6) for axis in range(3)],
    }


def material_triangle_counts(objects) -> dict[str, int]:
    counts = Counter()
    for obj in objects:
        for poly in obj.data.polygons:
            counts[material_name(obj, poly)] += len(poly.vertices) - 2
    return dict(sorted(counts.items()))


def triangle_count(objects) -> int:
    return sum(len(poly.vertices) - 2 for obj in objects for poly in obj.data.polygons)


def union_bounds(bounds: list[dict]) -> dict[str, list[float]]:
    return {
        "min": [round(min(box["min"][axis] for box in bounds), 6) for axis in range(3)],
        "max": [round(max(box["max"][axis] for box in bounds), 6) for axis in range(3)],
    }


def bounds_close(left: dict, right: dict, tolerance: float = 0.00002) -> bool:
    return all(abs(left[key][axis] - right[key][axis]) <= tolerance
               for key in ("min", "max") for axis in range(3))
