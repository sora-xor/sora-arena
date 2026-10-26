"""Source admission and measured Unreal readback for the Inventory drone.

No editor import at module load. The reviewed kit is fc0858a9; replacing its
record requires another source/visual review, not a silent importer fallback.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import struct

SOURCE = Path("Content/SourceArt/Characters/Enemies/InventoryDrone")
NAME = "SM_Drone_Inventory"
DESTINATION = "/Game/Generated/Characters/Enemies/InventoryDrone"
RECORD_SHA256 = "346a2b86cdc626b57cb1ee245dce38b3948b35aedc0625d10e87b1d75530aedb"


def require(condition, message):
    if not condition:
        raise RuntimeError("Inventory drone: " + message)


def source_record(root):
    root = Path(root).resolve()
    data = (root / SOURCE / "build_record.json").read_bytes()
    require(hashlib.sha256(data).hexdigest() == RECORD_SHA256, "unreviewed build record")
    record = json.loads(data)
    for entry in record["assets"][NAME]["lods"] + list(record["textures"].values()) + [record["blend"]]:
        path = (root / entry["file"]).resolve()
        require(path.parent == root / SOURCE, "source escaped the drone folder")
        content = path.read_bytes()
        require(hashlib.sha256(content).hexdigest() == entry["sha256"], "changed source: " + entry["file"])
        if path.suffix == ".png":
            require(content[:8] == b"\x89PNG\r\n\x1a\n" and
                    struct.unpack(">II", content[16:24]) == (2048, 2048), "map is not authored 2048 PNG")
    return record


def vector(values, label):
    require(len(values) == 3 and all(type(v) in (int, float) and math.isfinite(v) for v in values),
            "invalid " + label)
    return tuple(float(v) for v in values)


def geometry_readback(record, lods, screens):
    """Validate real render-buffer positions, not the FBX's claimed bounds."""
    require(len(lods) == 3 and len(screens) == 3, "expected three authored LODs")
    require(all(math.isfinite(v) and abs(v-w) < 1e-5 for v, w in
                zip(screens, record["assets"][NAME]["screen_sizes"])), "changed LOD screens")
    rows = []
    for index, (points, triangles) in enumerate(lods):
        points = [vector(p, "render vertex") for p in points]
        require(bool(points), "empty render LOD")
        expected = record["envelope"]["lods"][index]
        require(triangles == expected["triangles"], f"LOD{index} lost authored triangles")
        radius = max(math.dist(p, (0, 0, 0)) for p in points)
        require(radius <= 36.5, f"LOD{index} escaped its design sphere")
        low = [min(p[a] for p in points) for a in range(3)]
        high = [max(p[a] for p in points) for a in range(3)]
        # Blender +Y becomes Unreal -Y; the source pivot remains at the centre.
        want_low = [100*expected["bounds_min_m"][0], -100*expected["bounds_max_m"][1], 100*expected["bounds_min_m"][2]]
        want_high = [100*expected["bounds_max_m"][0], -100*expected["bounds_min_m"][1], 100*expected["bounds_max_m"][2]]
        require(all(abs(a-b) < .02 for a, b in zip(low+high, want_low+want_high)),
                f"LOD{index} changed scale, orientation or pivot")
        rows.append({"lod": index, "triangles": triangles, "vertices": len(points),
                     "radius_cm": radius, "min_cm": low, "max_cm": high})
    return rows


def socket_readback(record, sockets):
    require(set(sockets) == {"Eye", "NetMuzzle"}, "missing or extra sockets")
    for name, row in sockets.items():
        source = record["assets"][NAME]["sockets"][name]
        want = (100*source[0], -100*source[1], 100*source[2])
        require(math.dist(vector(row["position"], "socket position"), want) < .02, name + " moved")
        require(math.dist(vector(row["scale"], "socket scale"), (1, 1, 1)) < 1e-4, name + " is scaled")
        forward = vector(row["forward"], "socket forward")
        direction = (1, 0, 0) if name == "Eye" else (math.sqrt(.5), 0, -math.sqrt(.5))
        require(math.dist(forward, direction) < .009, name + " points the wrong way")
    return sockets
