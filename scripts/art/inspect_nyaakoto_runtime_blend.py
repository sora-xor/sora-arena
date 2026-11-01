"""Read-only inspection of Nyaakoto's runtime blend: its mesh's structure, for the r4 paw-surface candidate's assembly.

Prints NYAAKOTO_RUNTIME_BLEND <json> and writes the same JSON to the path after "--". It reports:
- the objects (type, transform, parent);
- the skinned mesh's vertex, face and corner counts;
- its vertex groups, shape keys, UV layers and colour attributes (name, domain, type);
- its material slots, and whether it has custom normals;
- the paws (hand_R, hand_L at weight 1): their vertices, strand vertices (each on one face) and skin faces.
Nothing is saved.

Run (lane holder): Blender -b --factory-startup --python-exit-code 1 <runtime blend> --python <this> -- <out.json>
"""
import json
import sys
from pathlib import Path

import bpy
import numpy as np

out = Path(sys.argv[sys.argv.index("--") + 1])
if out.exists():
    raise SystemExit(f"{out} exists")
info = {"blend": bpy.data.filepath, "objects": []}
for o in bpy.data.objects:
    info["objects"].append({"name": o.name, "type": o.type, "parent": o.parent.name if o.parent else None,
                            "matrix_world_identity": bool(np.allclose(np.array(o.matrix_world), np.eye(4), atol=1e-9)),
                            "location": list(o.location), "scale": list(o.scale)})
meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.vertex_groups]
mesh_obj = max(meshes, key=lambda o: len(o.data.vertices))
me = mesh_obj.data
row = {"object": mesh_obj.name, "vertices": len(me.vertices), "faces": len(me.polygons), "corners": len(me.loops),
       "vertex_groups": [g.name for g in mesh_obj.vertex_groups],
       "shape_keys": [k.name for k in me.shape_keys.key_blocks] if me.shape_keys else [],
       "uv_layers": [u.name for u in me.uv_layers],
       "color_attributes": [{"name": a.name, "domain": a.domain, "type": a.data_type} for a in me.color_attributes],
       "attributes": [{"name": a.name, "domain": a.domain, "type": a.data_type} for a in me.attributes],
       "materials": [m.name if m else None for m in me.materials],
       "has_custom_normals": bool(me.has_custom_normals),
       "polygon_sizes": sorted({len(p.vertices) for p in me.polygons})}
for side in ("R", "L"):
    g = mesh_obj.vertex_groups[f"hand_{side}"].index
    w = np.zeros(len(me.vertices))
    for v in me.vertices:
        for e in v.groups:
            if e.group == g:
                w[v.index] = e.weight
    in_hand = w > 0.5
    face_v = [list(p.vertices) for p in me.polygons]
    uses = np.zeros(len(me.vertices), int)
    for fv in face_v:
        for v in fv:
            uses[v] += 1
    hand_faces = [i for i, fv in enumerate(face_v) if all(in_hand[v] for v in fv)]
    strand_faces = [i for i in hand_faces if all(uses[v] == 1 for v in face_v[i])]
    mats = sorted({me.materials[me.polygons[i].material_index].name for i in hand_faces})
    row[f"paw_{side}"] = {"vertices": int(in_hand.sum()), "weights": sorted({round(float(x), 6) for x in w[in_hand]}),
                          "faces": len(hand_faces), "strand_faces": len(strand_faces),
                          "skin_faces": len(hand_faces) - len(strand_faces), "materials": mats}
info["mesh"] = row
out.write_text(json.dumps(info, indent=1) + "\n")
print("NYAAKOTO_RUNTIME_BLEND " + json.dumps({k: row[k] for k in ("object", "vertices", "faces", "shape_keys", "uv_layers",
                                                                  "color_attributes", "has_custom_normals", "paw_R", "paw_L")}),
      flush=True)
