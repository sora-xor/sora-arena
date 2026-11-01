"""Does each LOD of the imported SK_NyaagyuSamurai render every triangle with the material our FBX gave it?

Unreal's FBX export of the mesh (import_nyaakoto_third_person.py --morph-export) writes each LOD section's own
MaterialIndex (FbxSkeletalMeshExport.cpp:226), one triangle at a time, section after section. The renderer instead
routes a section through LODInfo.LODMaterialMap. readback_nyaakoto_lod_materials.py reads that routing from Unreal
(GetLODMaterialSlot).

**Pairing.** Each LOD's run of equal material indices in the export is one section, in order. The pairing holds only
when the run count equals Unreal's section count; otherwise the check fails rather than guess.

**The check:** per LOD, triangles per material as Unreal renders them must equal triangles per material in our FBX
for that LOD, by name. It also reports the same count for the export's raw indices, to show what the export alone
would claim.

Run (host Python with numpy): python3 scripts/art/check_nyaakoto_lod_materials.py <readback.json> <Unreal's export
    .fbx> <our LOD0 .fbx> <our LOD1 .fbx> <our LOD2 .fbx> <out.json>
"""
from __future__ import annotations

import collections
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fbx_unreal_sockets as FUS  # noqa: E402

READBACK, EXPORT, OURS, OUT = Path(sys.argv[1]), Path(sys.argv[2]), [Path(p) for p in sys.argv[3:6]], Path(sys.argv[6])


def meshes(path):
    """Each mesh model's name -> (its materials in connection order, per polygon material index, triangles per polygon)."""
    root, _ = FUS.parser().parse(str(path))
    objs = {o.props[0]: o for o in FUS._child(root, b"Objects").elems}
    links = [(c.props[0], c.props[1], c.props[2]) for c in FUS._child(root, b"Connections").elems]
    name = lambda o: o.props[1].split(b"\x00\x01")[0].decode()  # noqa: E731
    out = {}
    for gid, g in objs.items():
        if g.id != b"Geometry" or g.props[2] != b"Mesh":
            continue
        mid = next(d for k, s, d in links if s == gid and objs.get(d) is not None and objs[d].id == b"Model")
        mats = [name(objs[s]) for k, s, d in links if d == mid and objs.get(s) is not None and objs[s].id == b"Material"]
        layer = FUS._child(g, b"LayerElementMaterial")
        if FUS._child(layer, b"MappingInformationType").props[0] != b"ByPolygon":
            raise SystemExit(f"{path.name}: {name(objs[mid])}'s materials are not by polygon")
        idx = np.array(FUS._child(layer, b"Materials").props[0], np.int64)
        pvi = np.array(FUS._child(g, b"PolygonVertexIndex").props[0], np.int64)
        tris = np.diff(np.concatenate([[-1], np.flatnonzero(pvi < 0)])) - 2
        out[name(objs[mid])] = (mats, idx, tris)
    return out


def per_material(names, idx, tris):
    c = collections.Counter()
    for i, t in zip(idx.tolist(), tris.tolist()):
        c[names[i]] += t
    return dict(c)


readback = json.loads(READBACK.read_text())
if "lod_materials" in readback:                    # the import's own readback (import_nyaakoto_third_person.py)
    readback = readback["lod_materials"]
ue = meshes(EXPORT)
report = {"readback": str(READBACK), "export": str(EXPORT),
          "export_sha256": hashlib.sha256(EXPORT.read_bytes()).hexdigest(), "lods": [], "failed": []}
for lod, ours_path in enumerate(OURS):
    rb = next(r for r in readback["lods"] if r["lod"] == lod)
    names, idx, tris = ue[f"SK_NyaagyuSamurai_LOD{lod}"]
    if not (tris == 1).all():
        raise SystemExit(f"Unreal's LOD{lod} export is not all triangles")
    starts = np.flatnonzero(np.concatenate([[True], idx[1:] != idx[:-1]]))
    runs = [(int(idx[s]), int(e - s)) for s, e in zip(starts, list(starts[1:]) + [len(idx)])]
    ours = next(iter(meshes(ours_path).values()))
    expected = per_material(*ours)
    row = {"lod": lod, "ours": str(ours_path), "ours_sha256": hashlib.sha256(ours_path.read_bytes()).hexdigest(),
           "unreal_sections": rb["sections"], "export_runs": len(runs),
           "export_raw_matches_ours": per_material(names, idx, tris) == expected}
    if len(runs) != rb["sections"]:
        row["failed"] = "the export's runs do not pair with Unreal's sections"
        report["failed"].append(f"LOD{lod}")
    else:
        rendered = collections.Counter()
        remapped = 0
        for (raw, n), slot in zip(runs, rb["section_slots"]):
            rendered[readback["slots"][slot]["material"]] += n
            remapped += raw != slot
        rendered = dict(rendered)
        row.update(sections_remapped_by_lod_material_map=remapped, rendered_matches_ours=rendered == expected,
                   mismatched_materials=sorted(set(rendered.items()) ^ set(expected.items())))
        if rendered != expected:
            report["failed"].append(f"LOD{lod}")
    report["lods"].append(row)
OUT.write_text(json.dumps(report, indent=2) + "\n")
print("NYAAKOTO_LOD_MATERIALS " + json.dumps([{k: r.get(k) for k in ("lod", "unreal_sections", "export_runs",
                                                                     "sections_remapped_by_lod_material_map",
                                                                     "export_raw_matches_ours", "rendered_matches_ours")}
                                              for r in report["lods"]] + [{"failed": report["failed"]}]))
if report["failed"]:
    raise SystemExit(f"NYAAKOTO_LOD_MATERIALS_FAILED {report['failed']}")
