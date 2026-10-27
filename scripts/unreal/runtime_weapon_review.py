"""Pinned source admission and readback gates for the corrected weapon ArtReview import.

No Unreal, Blender, numpy or filesystem writes at module load. Source admission
does not authorize changing the gameplay meshes or relaxing viewmodel admission.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import struct

import weapon_socket_gates as G

SOURCE = "Content/SourceArt/Weapons/Runtime"
ENVELOPE = "scripts/unreal/data/runtime_weapon_review.json"
ENVELOPE_SHA256 = "0f84ef765a6f3e8cbd7967123dd260c5cbd21467d5634c26c259a63d9cc5886e"
DESTINATION = "/Game/ArtReview/RuntimeWeapons"
KIT_IDS = (0, 1, 2, 4, 5, 6, 7, 8, 9, 10, 12, 14, 15, 17, 19, 20)
ASSETS = tuple(sorted([f"SM_Weapon_{i:02}" for i in KIT_IDS] +
                      ["SM_Weapon_00_Saya", "SM_Weapon_02_Chain", "SM_Weapon_04_Saya", "SM_Weapon_10_Saya"]))
CHANNELS = ("BaseColor", "Normal", "ORM", "Mask")
BUILD = {"use_full_precision_u_vs": True, "remove_degenerates": False,
         "generate_lightmap_u_vs": False, "recompute_normals": False, "recompute_tangents": False}


def require(condition, message):
    if not condition:
        raise RuntimeError("Weapon review: " + message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def checked_file(root, entry):
    path = root / entry["file"]
    require(path.resolve().is_relative_to(root / SOURCE) and path == path.resolve(), "source path escaped kit")
    data = path.read_bytes()
    require(sha(data) == entry["sha256"], "changed source: " + entry["file"])
    return data


def material_plan(record):
    """Use each kit's authored emission and alpha; never treat hamon as glow."""
    require(set(record["textures"]) == set(CHANNELS), "expected the four authored maps")
    masked = record["material"]["BaseColor"] == "sRGB, A = opacity mask (masked blend)"
    require(masked or record["material"]["BaseColor"] == "sRGB", "unreviewed BaseColor semantics")
    require("DirectX (green down)" in record["material"]["NormalDX"], "unknown normal-map convention")
    emission = record.get("emissive")
    color, strength = [0.0, 0.0, 0.0], 0.0
    if emission:
        require(emission["mask"] == "Mask R" and len(emission["glows"]) == 1, "ambiguous emission atlas")
        glow = emission["glows"][0]
        color, strength = glow["linear_rgb"], glow["strength"]
        require(G.finite_vector(color) is not None and all(v >= 0 for v in color), "invalid emission color")
        require(type(strength) in (int, float) and math.isfinite(strength) and strength > 0,
                "invalid emission strength")
    return {"name": record["material"]["name"], "masked": masked, "two_sided": masked,
            "opacity_clip": 0.333, "emissive_color": color, "emissive_strength": strength,
            "normal_flip_green": False, "max_texture_size": record["texture_res"]}


def source_plan(root):
    root = Path(root).resolve()
    data = (root / ENVELOPE).read_bytes()
    require(sha(data) == ENVELOPE_SHA256, "unreviewed geometry envelope")
    plan = json.loads(data)
    require(plan["schema"] == "sora.weapon-review.v1" and tuple(sorted(plan["assets"])) == ASSETS,
            "changed review inventory")
    manifest = json.loads(checked_file(root, plan["source_manifest"]))
    listed = {r["file"]: r["sha256"] for r in manifest["files"]}
    require(len(listed) == len(manifest["files"]), "duplicate ledger entry")
    records = {}
    for kit, entry in plan["kits"].items():
        require(listed.get(entry["file"]) == entry["sha256"], "record absent from source ledger")
        record = json.loads(checked_file(root, entry))
        require(record["key"] == kit and record["id"] in KIT_IDS and "socket_fbx" in record,
                "uncorrected or held kit")
        require(record["id"] not in {r["id"] for r in records.values()}, "duplicate kit ID")
        checked_file(root, record["blend"])
        for channel, texture in record["textures"].items():
            raw = checked_file(root, texture)
            require(listed.get(texture["file"]) == texture["sha256"], "unlisted map")
            require(raw[:8] == b"\x89PNG\r\n\x1a\n" and struct.unpack(">II", raw[16:24]) == (2048, 2048),
                    "expected authored 2048 PNG: " + channel)
        material_plan(record)
        records[kit] = record
    require(sorted(r["id"] for r in records.values()) == list(KIT_IDS), "missing review kit")
    for name, expected in plan["assets"].items():
        record = records[expected["kit"]]
        asset = record["assets"][name]
        require(len(asset["lods"]) == len(expected["lods"]) == 3, "missing authored LOD")
        require(set(asset["socket_axes"]) == set(asset["sockets"]), "missing authored socket frame")
        for lod, envelope in zip(asset["lods"], expected["lods"]):
            require(all(lod[k] == envelope[k] for k in ("file", "sha256", "triangles")), "changed LOD envelope")
            require(listed.get(lod["file"]) == lod["sha256"], "LOD absent from source ledger")
            checked_file(root, lod)
        require(expected["screen_sizes"] == asset["screen_sizes"], "changed screen thresholds")
    return plan, records


def geometry_readback(expected, lods, screens):
    """Actual render sections: finite frames/UVs, indices, counts, signed bounds and pivot."""
    require(len(lods) == 3 and G.finite_vector(screens) is not None, "expected three finite LODs/screens")
    require(all(abs(a-b) < 1e-5 for a, b in zip(screens, expected["screen_sizes"])), "wrong screen thresholds")
    result = []
    for index, (lod, reference) in enumerate(zip(lods, expected["lods"])):
        require(len(lod["sections"]) == 1 and lod["uv_channels"] == reference["uv_channels"],
                f"LOD{index} lost its baked section/UV channels")
        section = lod["sections"][0]
        points, indices = section["positions"], section["indices"]
        require(bool(points) and bool(indices) and len(indices) % 3 == 0, f"LOD{index} empty or malformed")
        for key, width in (("positions", 3), ("normals", 3), ("tangents", 3), ("uvs", 2)):
            require(len(section[key]) == len(points) and all(G.finite_vector(v, width) is not None for v in section[key]),
                    f"LOD{index} invalid {key}")
        require(all(type(i) is int and 0 <= i < len(points) for i in indices), f"LOD{index} invalid indices")
        require(len(indices) // 3 == reference["triangles"] == lod["triangles"], f"LOD{index} lost triangles")
        low = [min(p[a] for p in points) for a in range(3)]
        high = [max(p[a] for p in points) for a in range(3)]
        require(all(abs(a-b) < .002 for a, b in zip(low+high, reference["min_cm"]+reference["max_cm"])),
                f"LOD{index} changed scale, axes or pivot")
        uv_low = [min(uv[a] for uv in section["uvs"]) for a in range(2)]
        uv_high = [max(uv[a] for uv in section["uvs"]) for a in range(2)]
        require(all(abs(a-b) < .000002 for a, b in zip(uv_low+uv_high, reference["uv_min"]+reference["uv_max"])),
                f"LOD{index} UV0 changed from source")
        outside = sum(any(v < 0 or v > 1 for v in section["uvs"][i]) for i in indices)
        require(outside == reference["atlas_uv_outside_corners"], f"LOD{index} changed atlas overshoot")
        result.append({"lod": index, "vertices": len(points), "triangles": lod["triangles"],
                       "min_cm": low, "max_cm": high, "uv_channels": lod["uv_channels"],
                       "uv_min": uv_low, "uv_max": uv_high, "atlas_uv_outside_corners": outside})
    return result


def socket_readback(name, asset, sockets):
    failures = G.socket_failures(sockets, asset["sockets"], asset["socket_axes"], len(name) == 12)
    require(not failures, name + ": " + "; ".join(failures))
    return sockets
