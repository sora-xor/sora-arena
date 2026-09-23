"""Audit the first UV channel of exported art as Unreal will sample it.

Run from the project root with Blender 5.2.2 LTS:

    blender -b --factory-startup --python scripts/art/audit_fbx_primary_uv.py -- \
      Content/SourceArt/Environment/NyaagyuDojo/SM_Nyaagyu_EstateDojo.fbx \
      Content/SourceArt/Environment/NyaagyuKura/SM_Nyaagyu_ProvisionKura.fbx

This is an export diagnostic, not an image-quality verdict. It catches a common
failure where an authored UV atlas is present, but FBX placed an empty UVMap
first. Unreal's default TextureCoordinate node then samples a single texel.
Plain-color material zones may intentionally have collapsed UVs; the audit
reports them separately instead of rejecting every asset.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import bpy


def inspect(path: Path) -> dict:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.fbx(filepath=str(path), use_anim=False)
    zones: dict[str, dict] = defaultdict(lambda: {"faces": 0, "channels": defaultdict(list)})
    render_meshes = 0
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH" or obj.name.upper().startswith(("UCX_", "UBX_", "USP_", "UCP_")):
            continue
        render_meshes += 1
        mesh = obj.data
        for poly in mesh.polygons:
            name = mesh.materials[poly.material_index].name if mesh.materials and mesh.materials[poly.material_index] else "<none>"
            zone = zones[name]
            zone["faces"] += 1
            for layer_index, layer in enumerate(mesh.uv_layers):
                for loop_index in poly.loop_indices:
                    uv = layer.data[loop_index].uv
                    zone["channels"][layer_index].append((float(uv.x), float(uv.y)))
    rendered = []
    for name, zone in sorted(zones.items()):
        channels = []
        for index, coordinates in sorted(zone["channels"].items()):
            us = [u for u, _ in coordinates]
            vs = [v for _, v in coordinates]
            channels.append({
                "index": index,
                "span_u": round(max(us) - min(us), 6),
                "span_v": round(max(vs) - min(vs), 6),
            })
        primary = channels[0] if channels else None
        alternate = any(max(ch["span_u"], ch["span_v"]) > .1 for ch in channels[1:])
        collapsed = primary is None or max(primary["span_u"], primary["span_v"]) < .01
        rendered.append({
            "material": name,
            "faces": zone["faces"],
            "uv_channels": channels,
            "primary_collapsed": collapsed,
            "secondary_has_coverage": alternate,
            "likely_wrong_primary": collapsed and alternate and zone["faces"] >= 20,
        })
    return {"fbx": str(path), "render_meshes": render_meshes, "zones": rendered}


def main() -> int:
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not args:
        raise SystemExit("Pass one or more FBX paths after --")
    reports = []
    for item in args:
        path = Path(item).resolve()
        if not path.is_file() or path.suffix.lower() != ".fbx":
            raise SystemExit(f"Missing FBX: {path}")
        reports.append(inspect(path))
    suspects = [
        (report["fbx"], zone["material"], zone["faces"])
        for report in reports for zone in report["zones"]
        if zone["likely_wrong_primary"]
    ]
    print("FBX_PRIMARY_UV_AUDIT " + json.dumps({"assets": reports, "suspects": suspects}, sort_keys=True))
    print(f"FBX primary UV audit: {len(reports)} assets, {len(suspects)} likely wrong-primary material zones")
    return 1 if suspects else 0


if __name__ == "__main__":
    raise SystemExit(main())
