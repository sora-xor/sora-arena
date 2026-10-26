"""Import Inventory drone LOD0 FBXs with root's options, unsaved, and read back their sockets, LOD0 render vertices and
convex hulls. It is the art lane's UE 5.8 evidence for the LOD0 socket export fix.

Run (UE 5.8, headless, by the holder of the shared engine lane):
  scripts/toolchain/run-editor-script.sh scripts/unreal/probe_inventory_drone_sockets.py INVENTORY_DRONE_PROBE_DONE
      <log> -- out=<json> original=<fbx> corrected=<fbx>

**Each file** imports into /Game/ArtLaneProbes/InventoryDroneSockets/<tag>/, and nothing is saved (task.save False).

**The options are root's** (scripts/unreal/import_inventory_drone.py, 0eb8c5e): FbxImportUI as a static mesh,
combined meshes, no lightmap UVs, no generated collision, one convex hull per UCX, no materials or textures, no
Nanite.

**collision=import** changes one of them: auto_generate_collision becomes True. Run s79 found 0 convex hulls with
root's options, for the original and the corrected file alike. UE 5.8's FbxImportUI converter sets Interchange's
bCollision from auto_generate_collision (InterchangeFbxAssetImportDataConverter.cpp:316), and bCollision gates
every collision mesh, UCX included (InterchangeLODDataParser.cpp:739). With custom UCX present, no 18-DOP is
generated (InterchangeStaticMeshFactory.cpp:796).

**It reads back as root's importer reads:**
- the component's socket list, then FindSocket for each, with the relative location, the relative scale, and the
  forward vector of the relative rotation;
- the render vertices of LOD0;
- the convex and other simple collision counts.

**Gates, for "corrected"** (root's socket_readback, and geometry_readback's LOD0 rows, in scripts/unreal/inventory_drone.py
at 0eb8c5e):
- each socket within 0.02 cm of the record;
- each socket's scale within 1e-4 of 1;
- each socket's forward within 0.009 of Eye +X or NetMuzzle (0.7071, 0, -0.7071);
- LOD0's triangles as authored, within 36.5 cm of the centre, at the record's bounds within 0.02 cm;
- exactly three convex hulls and no other simple shapes.

Since root's review of d13ebfc5, the socket gates also go through weapon_socket_gates.socket_failures:
- malformed or nonfinite values fail explicitly;
- the right and up vectors are read too, and checked signed against the record's socket_axes;
- every comparison fails safe for NaN, and so do the LOD0 vertices.
The runs s79 and s80 used the earlier version, without these checks.

"original" is the control. It is read and recorded, and expected to repeat root's failure.

Asset readback only: not a render, a capture or a gameplay admission.
"""

import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_engine_pin import require_running_engine  # noqa: E402
import weapon_socket_gates as G  # noqa: E402

require_running_engine("Inventory drone socket probe")
OPTS = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
COLLISION = OPTS.get("collision", "root")
assert COLLISION in ("root", "import"), COLLISION
ROOT = Path(unreal.Paths.project_dir()).resolve()
KIT = ROOT / "Content/SourceArt/Characters/Enemies/InventoryDrone"
NAME = "SM_Drone_Inventory"
DEST = "/Game/ArtLaneProbes/InventoryDroneSockets"
record_bytes = (KIT / "build_record.json").read_bytes()
record = json.loads(record_bytes)
asset = record["assets"][NAME]
meshes = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
FORWARD = {"Eye": (1, 0, 0), "NetMuzzle": (math.sqrt(.5), 0, -math.sqrt(.5))}


def fail(message):
    raise RuntimeError("Inventory drone probe: " + message)


def options():
    ui = unreal.FbxImportUI()
    ui.import_mesh = True
    ui.import_as_skeletal = False
    ui.import_materials = False
    ui.import_textures = False
    ui.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    data = ui.static_mesh_import_data
    data.combine_meshes = True
    data.generate_lightmap_u_vs = False
    data.auto_generate_collision = COLLISION == "import"
    data.one_convex_hull_per_ucx = True
    data.set_editor_property("build_nanite", False)
    return ui


def probe(tag, fbx):
    task = unreal.AssetImportTask()
    task.filename = str(fbx)
    task.destination_path = f"{DEST}/{tag}"
    task.destination_name = NAME
    task.automated = True
    task.replace_existing = True
    task.save = False
    task.options = options()
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = unreal.EditorAssetLibrary.load_asset(f"{DEST}/{tag}/{NAME}")
    if not isinstance(mesh, unreal.StaticMesh):
        fail(f"{tag} did not import as a static mesh")
    points, triangles = [], 0
    for section in range(mesh.get_num_sections(0)):
        positions, indices, _n, _uv, _t = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(mesh, 0, section)
        points.extend((p.x, p.y, p.z) for p in positions)
        triangles += len(indices) // 3
    probe_component = unreal.StaticMeshComponent()
    if not probe_component.set_static_mesh(mesh):
        fail("socket probe could not bind " + tag)
    sockets = {}
    for socket_name in probe_component.get_all_socket_names():
        socket = mesh.find_socket(socket_name)
        position = socket.get_editor_property("relative_location")
        scale = socket.get_editor_property("relative_scale")
        rotation = socket.get_editor_property("relative_rotation")
        forward = unreal.MathLibrary.get_forward_vector(rotation)
        right = unreal.MathLibrary.get_right_vector(rotation)
        up = unreal.MathLibrary.get_up_vector(rotation)
        sockets[str(socket_name)] = {"position": [position.x, position.y, position.z],
                                     "scale": [scale.x, scale.y, scale.z],
                                     "forward": [forward.x, forward.y, forward.z],
                                     "right": [right.x, right.y, right.z], "up": [up.x, up.y, up.z],
                                     "rotation_pyr": [rotation.pitch, rotation.yaw, rotation.roll]}
    finite = [p for p in points if G.finite_vector(list(p)) is not None]
    low = [min(p[a] for p in finite) for a in range(3)] if finite else None
    high = [max(p[a] for p in finite) for a in range(3)] if finite else None
    return {"fbx": str(Path(fbx).resolve().relative_to(ROOT)), "sha256": hashlib.sha256(Path(fbx).read_bytes()).hexdigest(),
            "sockets": sockets, "lod0": {"triangles": triangles, "mesh_triangles": mesh.get_num_triangles(0),
                                         "vertices": len(points), "nonfinite_vertices": len(points) - len(finite),
                                         "min_cm": low, "max_cm": high,
                                         "radius_cm": max((math.dist(p, (0, 0, 0)) for p in finite), default=None)},
            "convex_count": meshes.get_convex_collision_count(mesh),
            "other_simple_count": meshes.get_simple_collision_count(mesh)}


def gates(row):
    """Root's gates (0eb8c5e) and the signed-axis gates; the failures, empty when it passes.

    The sockets go through weapon_socket_gates.socket_failures: malformed and nonfinite values fail explicitly,
    and so do position, unit scale and signed forward, right and up against the record. Root's own forward
    directions are checked too, failing safe: a NaN cannot pass `not distance < tolerance`.
    """
    out = []
    if set(row["sockets"]) != {"Eye", "NetMuzzle"}:
        out.append(f"sockets {sorted(row['sockets'])}")
    out.extend(G.socket_failures(row["sockets"], asset["sockets"], record["socket_axes"], main_mesh=False))
    for name, s in row["sockets"].items():
        forward = G.finite_vector(s.get("forward"))
        if name in FORWARD and (forward is None or not math.dist(forward, FORWARD[name]) < .009):
            out.append(f"{name} points the wrong way: {s.get('forward')}")
    lod = row["lod0"]
    if lod["nonfinite_vertices"] or lod["radius_cm"] is None:
        out.append(f"LOD0 has {lod['nonfinite_vertices']} malformed or nonfinite render vertices")
        return out
    env = record["envelope"]["lods"][0]
    want_low = [100*env["bounds_min_m"][0], -100*env["bounds_max_m"][1], 100*env["bounds_min_m"][2]]
    want_high = [100*env["bounds_max_m"][0], -100*env["bounds_min_m"][1], 100*env["bounds_max_m"][2]]
    if lod["triangles"] != env["triangles"] or lod["mesh_triangles"] != env["triangles"]:
        out.append(f"LOD0 triangles {lod['triangles']}, {lod['mesh_triangles']}")
    if not lod["radius_cm"] <= 36.5:
        out.append(f"LOD0 radius {lod['radius_cm']}")
    if not all(abs(a - b) < .02 for a, b in zip(lod["min_cm"] + lod["max_cm"], want_low + want_high)):
        out.append(f"LOD0 bounds {lod['min_cm']} {lod['max_cm']}")
    if row["convex_count"] != 3 or row["other_simple_count"] != 0:
        out.append(f"collision {row['convex_count']} convex, {row['other_simple_count']} other")
    return out


rows = {}
for tag in ("original", "corrected"):
    rows[tag] = probe(tag, OPTS[tag])
    rows[tag]["root_gate_failures"] = gates(rows[tag])
    unreal.log(f"INVENTORY_DRONE_PROBE {tag}: " + json.dumps(rows[tag], sort_keys=True))
if rows["corrected"]["sha256"] != asset["lods"][0]["sha256"]:
    fail("corrected is not the record's LOD0")
report = {"engine": unreal.SystemLibrary.get_engine_version(),
          "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          "record_sha256": hashlib.sha256(record_bytes).hexdigest(), "saved_packages": False,
          "options": {"collision": COLLISION, "auto_generate_collision": COLLISION == "import",
                      "otherwise": "root's 0eb8c5e FbxImportUI options"}, "imports": rows,
          "status": "asset readback only: sockets, LOD0 render vertices and hull counts as UE 5.8 imports them"}
out = ROOT / OPTS["out"]
out.parent.mkdir(parents=True, exist_ok=True)
with open(out, "x", encoding="utf-8") as fh:
    fh.write(json.dumps(report, indent=1) + "\n")
if rows["corrected"]["root_gate_failures"]:
    fail("corrected fails root's gates: " + "; ".join(rows["corrected"]["root_gate_failures"]))
unreal.log("INVENTORY_DRONE_PROBE_DONE " + json.dumps({t: r["root_gate_failures"] for t, r in rows.items()}))
