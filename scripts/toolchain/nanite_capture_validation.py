"""Validate engine-generated dojo diagnostic originals; never repaint pixels.

Mask's green/red classification comes from UE5.8 NaniteVisualize.usf's
VisBuffer64/shading-mask branches, not from asset capability flags. The
conservative pixel classifier below only establishes nonzero candidate
coverage; a reviewer must attribute it to the recorded production geometry.
It is not an exact visibility-buffer count, triangle count or performance test.
"""
import math
import hashlib
from pathlib import Path
import re

SCHEMA = "sora-arena.nanite-draw.v1"
SCOPE = "production dojo renderer diagnostic; unadmitted art; not gameplay or platform release acceptance"
CAMERAS = ("entry", "ceiling")
MODES = ("Lit", "Mask", "Triangles")
LOCATIONS = ([8420, 0, 154], [9500, -200, 154])
ROTATIONS = ([4, 0, 0], [52, 20, 0])
# Central interior geometry, excluding engine labels and most exterior windows.
# These are fixed normalized rectangles, not edited or cropped output images.
REGION = (.2, .2, .8, .8)


def number(obj, key):
    value = obj.get(key)
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"invalid Nanite observation {key}")
    return value


def vector(obj, key, count):
    value = obj.get(key)
    if not isinstance(value, list) or len(value) != count or any(type(v) not in (int, float) or not math.isfinite(v) for v in value):
        raise ValueError(f"invalid Nanite observation {key}")
    return value


def integer(obj, key):
    value = number(obj, key)
    if value != int(value) or not 0 <= value <= 2**53 - 1:
        raise ValueError(f"invalid Nanite integer {key}")
    return value


def validate_metadata(meta, filenames, width, height):
    if not isinstance(meta, dict) or meta.get("schema") != SCHEMA or meta.get("scope") != SCOPE:
        raise ValueError("Nanite metadata schema/scope mismatch")
    if meta.get("passed") is not True or meta.get("restored") is not True or meta.get("null_rhi") is not False:
        raise ValueError("Nanite capture failed or did not restore its original session")
    sm6 = meta.get("sm6_requested")
    if type(sm6) is not bool or meta.get("nanite_eligible") is not sm6 or vector(meta, "viewport", 2) != [width, height]:
        raise ValueError("Nanite shader-model request/viewport mismatch")
    if meta.get("shader_platform") != ("METAL_SM6" if sm6 else "METAL_SM5"):
        raise ValueError("actual Nanite shader platform does not match the Mac diagnostic request")
    if "metal" not in str(meta.get("rhi", "")).lower() or not meta.get("adapter"):
        raise ValueError("Nanite diagnostic lacks actual Metal RHI/adapter identity")
    phases = [f"{cam}-{mode}" for cam in CAMERAS for mode in (MODES if sm6 else ("Lit",))]
    frames = meta.get("frames")
    if (not isinstance(frames, list) or integer(meta, "frame_count") != len(phases) or len(frames) != len(phases)
            or filenames != [p + ".png" for p in phases]):
        raise ValueError("Nanite diagnostic requires the exact complete ordered original frame sequence")
    previous = -1
    first_cvars = None
    for frame, phase in zip(frames, phases):
        cam, mode = phase.split("-")
        ci = CAMERAS.index(cam)
        if not isinstance(frame, dict) or any(frame.get(k) != v for k, v in
                (("name", phase), ("file", phase + ".png"), ("camera_id", cam), ("mode", mode))):
            raise ValueError("Nanite frame identity/mode mismatch")
        if (math.dist(vector(frame, "camera", 3), LOCATIONS[ci]) > .01 or
                math.dist(vector(frame, "rotation", 3), ROTATIONS[ci]) > .001 or abs(number(frame, "fov") - 94) > .001):
            raise ValueError("Nanite camera moved or differs from the production dojo view")
        if frame.get("paused") is not True or frame.get("hud_hidden") is not True or number(frame, "settle_seconds") < 3:
            raise ValueError("Nanite frame lost paused/HUD-hidden settling conditions")
        request, processed = integer(frame, "request_frame"), integer(frame, "screenshot_processed_frame")
        if request <= previous or processed < request:
            raise ValueError("Nanite screenshot frame chronology is invalid")
        previous = processed
        visualize = mode != "Lit"
        if (frame.get("show_visualize_nanite") is not visualize or
                frame.get("active_visualization") != (mode if visualize else "None") or
                (number(frame, "active_mode_id") < 0) is visualize):
            raise ValueError("engine Nanite visualization readback disagrees with requested frame")
        cvars = frame.get("cvars")
        if not isinstance(cvars, dict) or any(cvars.get(k) != v for k, v in {
                "r.Nanite.Visualize": mode if visualize else "off", "r.Nanite.Visualize.Composite": "1",
                "r.Nanite.Visualize.EdgeDetect": "0", "r.Nanite.Visualize.DebugShading": "0"}.items()):
            raise ValueError("Nanite visualization cvar readback mismatch")
        if sm6 and cvars.get("r.Nanite") != "1":
            raise ValueError("SM6 draw evidence requires enabled Nanite")
        if not sm6 and cvars.get("r.Nanite.ProxyRenderMode") != "0":
            raise ValueError("SM5 diagnostic requires the conventional fallback proxy mode")
        unchanged = {k: cvars.get(k) for k in ("r.Nanite", "r.Nanite.ProxyRenderMode", "r.ScreenPercentage", "r.AntiAliasingMethod", "sora.HallInstanced")}
        if any(v in (None, "absent") for v in unchanged.values()) or (first_cvars is not None and unchanged != first_cvars):
            raise ValueError("production renderer controls changed across Nanite comparison")
        first_cvars = unchanged
    meshes = meta.get("meshes")
    if not isinstance(meshes, list) or not meshes:
        raise ValueError("Nanite diagnostic has no actual production dojo mesh identities")
    seen = set()
    for mesh in meshes:
        if (not isinstance(mesh, dict) or not isinstance(mesh.get("component"), str) or not mesh["component"]
                or mesh["component"] in seen or not str(mesh.get("mesh", "")).startswith("/Game/Generated/Environment/DojoKit/")
                or any(type(mesh.get(k)) is not bool for k in ("has_nanite_data", "disallow_nanite", "force_disable_nanite")) or integer(mesh, "instances") < 1
                or not isinstance(mesh.get("materials"), list) or not mesh["materials"]):
            raise ValueError("invalid/duplicate production dojo component identity")
        seen.add(mesh["component"])
        vector(mesh, "bounds_origin", 3)
        if any(v <= 0 for v in vector(mesh, "bounds_extent", 3)):
            raise ValueError("invalid production dojo bounds")
    return sm6


def pixel_evidence(lit, mask, triangles):
    width, height, _, _ = lit
    if mask[:2] != (width, height) or triangles[:2] != (width, height):
        raise ValueError("Nanite image dimensions differ")
    x0, y0, x1, y1 = [round(v * (width if i % 2 == 0 else height)) for i, v in enumerate(REGION)]
    green = red = changed_triangles = 0
    colors = set()
    for y in range(y0, y1):
        for x in range(x0, x1):
            def pixel(image):
                return image[3][y][x * image[2]:x * image[2] + 3]
            l, m, t = pixel(lit), pixel(mask), pixel(triangles)
            # Mask opacity=.5 blends green or red over the rendered scene.
            # Require a new dominant channel relative to the paired Lit image,
            # so an ordinary green/red material alone cannot count as evidence.
            is_green = m[1] > max(m[0], m[2]) + 24 and m[1] - max(m[0], m[2]) > l[1] - max(l[0], l[2]) + 24
            is_red = m[0] > max(m[1], m[2]) + 24 and m[0] - max(m[1], m[2]) > l[0] - max(l[1], l[2]) + 24
            green += is_green
            red += is_red
            if is_green and sum(abs(a - b) for a, b in zip(l, t)) > 48 and max(t) - min(t) > 24:
                changed_triangles += 1
                colors.add(tuple(v // 16 for v in t))
    # Guard against a single hot pixel or the mode label. This is deliberately
    # tiny coverage, not an artistic/performance threshold or an exact count.
    valid = green >= 24 and changed_triangles >= 24 and len(colors) >= 4
    return {"roi_pixels": [x0, y0, x1, y1], "mask_green_candidates": green,
            "mask_red_candidates": red, "triangles_changed_at_green": changed_triangles,
            "triangle_color_bins_at_green": len(colors), "nonzero_candidate_coverage": valid}


def inspect(meta, images, width, height, decode):
    """Return an archivable result even when genuine SM6 draw evidence is absent."""
    sm6 = validate_metadata(meta, list(images), width, height)
    result = {"schema": "sora-arena.nanite-pixel-review.v1", "actual_shader_platform": meta["shader_platform"],
              "adapter": meta["adapter"], "scope": SCOPE, "human_geometry_review_required": True,
              "hardware_m1_qualified": False, "release_qualified": False, "errors": [], "cameras": {}}
    if not sm6:
        result.update(evidence="SM5 conventional fallback originals only; not M1 hardware proof", nanite_draw_evidence=False)
        return result
    result["evidence"] = "engine Mask/Triangles original-pixel candidates; not GPU counters or artistic acceptance"
    for cam in CAMERAS:
        samples = [decode(images[f"{cam}-{mode}.png"]) for mode in MODES]
        if any(s[:2] != (width, height) for s in samples):
            raise ValueError("Nanite original pixel dimensions differ from viewport")
        observation = pixel_evidence(*samples)
        result["cameras"][cam] = observation
        if not observation["nonzero_candidate_coverage"]:
            result["errors"].append(f"{cam}: no resolved green Mask/Triangles evidence on the dojo interior")
    if not any(mesh["has_nanite_data"] and not mesh["disallow_nanite"] and not mesh["force_disable_nanite"] for mesh in meta["meshes"]):
        result["errors"].append("production dojo components have no Nanite resource data")
    result["nanite_draw_evidence"] = not result["errors"]
    return result


def asset_identities(meta, project):
    """Bind runtime-read loose generated package bytes to the immutable archive.

    MD5 is the engine's observed file hash; archive identities also use SHA256.
    Neither substitutes for recording the exact source commit in the wrapper.
    """
    files = meta.get("asset_files")
    if not isinstance(files, list) or not files:
        raise ValueError("Nanite metadata has no runtime-observed dojo package bytes")
    root = (project / "Content/Generated/Environment/DojoKit").resolve()
    out, seen = [], set()
    for record in files:
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            raise ValueError("invalid Nanite asset file identity")
        path = Path(record["path"]).resolve()
        path.relative_to(root)
        if path in seen or path.suffix not in (".uasset", ".uexp", ".ubulk"):
            raise ValueError("duplicate or unexpected Nanite asset file")
        seen.add(path)
        data = path.read_bytes()
        if (integer(record, "bytes") != len(data) or not re.fullmatch(r"[0-9a-fA-F]{32}", str(record.get("md5", "")))
                or hashlib.md5(data).hexdigest() != record["md5"].lower()):
            raise ValueError("dojo package bytes changed since the runtime inventory")
        out.append({"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "runtime_md5": record["md5"]})
    for mesh in meta.get("meshes", []):
        path = Path(mesh.get("package_file", "")).resolve()
        expected = root / (str(mesh.get("mesh", "")).split("/")[-1].split(".")[0] + ".uasset")
        if path != expected or path not in seen:
            raise ValueError("dojo component identity lacks its exact original package bytes")
    return out
