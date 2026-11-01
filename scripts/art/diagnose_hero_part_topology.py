"""Per-part topology of two hero source blends: which parts' vertex, polygon and triangle counts differ.

Written for s100: the committed hero source (0612ab5b's run) counts 128,650 triangles, and s98's study-A rebuild of the
same generator counts 128,607. Study A only moves vertices (nyaakoto_runtime_parts.apply_variant), so the parts that
differ say where the difference comes from.

Run (Blender 5.2, read-only on both blends):
    Blender -b --factory-startup --python-exit-code 1 --python scripts/art/diagnose_hero_part_topology.py --
        <old.blend> <new.blend> <out.json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy

ARGS = sys.argv[sys.argv.index("--") + 1:]
OLD, NEW, OUT = (Path(a) for a in ARGS)


def counts(path):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    rows = {}
    for o in bpy.data.collections["NyaagyuHero_Editable"].objects:
        if o.type == "MESH":
            rows[o.name] = {"vertices": len(o.data.vertices), "polygons": len(o.data.polygons),
                            "triangles": sum(len(p.vertices) - 2 for p in o.data.polygons)}
    return rows, bpy.app.version_string


a, ver_a = counts(OLD)
b, ver_b = counts(NEW)
diff = {n: {"old": a.get(n), "new": b.get(n)} for n in sorted(set(a) | set(b)) if a.get(n) != b.get(n)}
summary = {"old": str(OLD), "new": str(NEW), "blender_reading": [ver_a, ver_b], "parts": [len(a), len(b)],
           "triangles": [sum(r["triangles"] for r in a.values()), sum(r["triangles"] for r in b.values())],
           "differing_parts": diff}
OUT.write_text(json.dumps(summary, indent=2) + "\n")
print("HERO_PART_TOPOLOGY " + json.dumps({k: summary[k] for k in ("parts", "triangles")}), len(diff), flush=True)
for n, r in diff.items():
    print("DIFF", n, json.dumps(r), flush=True)
