"""Validate engine-generated dojo diagnostic originals; never repaint pixels.

Mask's green/red classification comes from UE5.8 NaniteVisualize.usf's
VisBuffer64/shading-mask branches, not from asset capability flags. The
conservative pixel classifier below only establishes nonzero candidate
coverage; a reviewer must attribute it to the recorded production geometry.
It is not an exact visibility-buffer count, triangle count or performance test.
"""
import math
import hashlib
import json
from pathlib import Path
import re
import subprocess

SCHEMA = "sora-arena.nanite-draw.v3"
SCOPE = "production dojo renderer diagnostic; unadmitted art; not gameplay or platform release acceptance"
CAMERAS = ("entry", "ceiling")
MODES = ("Lit", "Mask", "Triangles")
LOCATIONS = ([8420, 0, 154], [9500, -200, 154])
ROTATIONS = ([4, 0, 0], [52, 20, 0])
# Central interior geometry, excluding engine labels and most exterior windows.
# These are fixed normalized rectangles, not edited or cropped output images.
REGION = (.2, .2, .8, .8)
COVERAGE_PENDING = {"status": "requires_archive_source_binding", "qualified": False}
CAPTURE_SCOPE = {"chapter_file": "Content/Data/campaign/chapter_01.json", "zone": "pl_tsumagizaka_dojo",
                 "rect": [8000, -1300, 11600, 1300]}
TIMBER_ROOT = "Content/SourceArt/Environment/NyaagyuDojoTimbers/"
BINDING = TIMBER_ROOT + "campaign_binding.json"
BINDER = "scripts/art/bind_dojo_timbers.py"
MANIFESTS = (TIMBER_ROOT + "manifest.json", TIMBER_ROOT + "Rails/manifest.json")
# The independent layout model below is reviewed against this immutable binder,
# its placement helper and rail layout. A changed algorithm needs a new review.
LAYOUT_SOURCES = {
    BINDER: "f114fea4e4e40e73d0b11f452e57255b5e3800d34b11e7fdea7f04489f5513c5",
    "scripts/art/dojo_hall_placements.py": "63b345dec4a31e9549a094fffbd5df6207ba5920c68c54192e412aaccf905773",
    "scripts/art/create_nyaagyu_dojo_rails.py": "d1246e47bf9c74961a18b26d7687b86425173a120f117e3068eef88ecbe63192"}
MANIFEST_INPUTS = ("scripts/art/sora_timber_lib.py", "scripts/art/sora_timber_lookdev.py",
    "scripts/art/sora_timber_bake.py", "scripts/art/dojo_hall_placements.py",
    "scripts/art/sora_prop_lib.py", "scripts/art/create_runtime_weapon_lib.py")
COVERAGE_INPUTS = tuple(f"Content/Data/campaign/chapter_{i:02}.json" for i in range(1, 9)) + (
    "Content/SourceArt/Environment/NyaagyuDojoTimbers/manifest.json",
    "Content/SourceArt/Environment/NyaagyuDojoTimbers/Rails/manifest.json",
    "Content/SourceArt/Environment/NyaagyuDojoTimbers/Floor/manifest.json",
    "scripts/art/dojo_hall_placements.py", "scripts/art/create_nyaagyu_dojo_timbers.py",
    "scripts/art/create_nyaagyu_dojo_rails.py", "scripts/art/create_nyaagyu_dojo_floor.py",
    BINDING, BINDER) + tuple(p for p in MANIFEST_INPUTS if p != "scripts/art/dojo_hall_placements.py")


def mesh_identity(mesh):
    match = re.fullmatch(r"/Game/Generated/Environment/(DojoKit|DojoTimbers)/([A-Za-z0-9_]+)\.\2", str(mesh.get("mesh", "")))
    if not match or mesh.get("asset_family") != match[1]:
        raise ValueError("invalid production dojo mesh family/object identity")
    return match[1], match[2]


def timber_kind(name):
    rect = r"(?:m?\d+_){3}m?\d+_S[0-3]_B\d{2,}"
    patterns = {"column_placement": rf"SM_DojoTimberColumn_{rect}",
                "rail_placement": rf"SM_DojoTimberRail_(?:Nageshi|Cornice|Koshi|Nuki)_{rect}",
                "floor_tile": r"SM_DojoTimberFloor_\d{2,}",
                "column_pool": r"SM_DojoTimberColumn_MAC_(?:Wall|Open)_\d{2,}",
                "rail_pool": r"SM_DojoTimberRail_MAC_(?:Nageshi|Cornice|Koshi|Nuki)_\d{2,}",
                "floor_pool": r"SM_DojoTimberFloor_MAC_\d{2,}"}
    for kind, pattern in patterns.items():
        if re.fullmatch(pattern, name):
            return kind
    raise ValueError("unexpected timber asset naming contract; placement admission is unavailable")


def coverage_inputs(meta):
    # Runtime records observations only. The archive derives expectations from
    # authenticated chapter/manifest/binder bytes, never from loaded meshes.
    coverage = meta.get("timber_placement_coverage")
    if coverage != COVERAGE_PENDING or coverage.get("qualified") is not False:
        raise ValueError("unsupported or missing timber placement coverage contract")
    records = meta.get("coverage_inputs")
    if not isinstance(records, list) or len(records) != len(COVERAGE_INPUTS):
        raise ValueError("missing timber coverage input observations")
    seen = set()
    for record in records:
        if not isinstance(record, dict) or record.get("path") not in COVERAGE_INPUTS or record["path"] in seen:
            raise ValueError("duplicate or unexpected timber coverage input")
        seen.add(record["path"])
        if type(record.get("exists")) is not bool:
            raise ValueError("invalid timber coverage input existence")
        if record["exists"]:
            if integer(record, "bytes") < 1 or not re.fullmatch(r"[0-9a-fA-F]{32}", str(record.get("md5", ""))):
                raise ValueError("invalid timber coverage input hash/size")
        elif set(record) != {"path", "exists"} or record["path"] in COVERAGE_INPUTS[:8]:
            raise ValueError("missing chapter data or invalid absent timber coverage input")
    return records


def hall_layout(rect):
    """Independent model of the reviewed 5d4308d column/rail naming contract."""
    x0, y0, x1, y1 = rect
    counts = [max(1, math.floor(((x1-x0) if s % 2 == 0 else (y1-y0)) / 180 + .5)) for s in range(4)]
    def bay(side, index):
        count = counts[side]
        if side == 0: return 4 if index % 4 == 2 else 3
        if side == 1: return 5 if count >= 8 and count//2-2 <= index < count//2+2 else (1 if index % 2 else 0)
        if side == 2: return 2 if index % 2 else 0
        return 4 if index == count-1 else (2 if index % 3 == 1 else 0)
    tag = "_".join(f"m{-v}" if v < 0 else str(v) for v in rect)
    out = {}
    for side in range(4):
        index = 0
        while index < counts[side]:
            kind = bay(side, index)
            before = bay(side, index-1) if index else bay((side+3)%4, counts[(side+3)%4]-1)
            names = [(f"SM_DojoTimberColumn_{tag}_S{side}_B{index:02d}", "open" if 4 in (kind, before) else "wall", "columns")]
            if kind != 5:
                names += [(f"SM_DojoTimberRail_{rail}_{tag}_S{side}_B{index:02d}", rail, "rails")
                          for rail in ("Nageshi", "Cornice", "Koshi", "Nuki") if rail != "Koshi" or kind in (0, 1, 2)]
            for name, wood, group in names:
                out[name] = {"rect": list(rect), "side": side, "bay": index, "kind": wood, "group": group,
                             "seed": int(hashlib.sha256(name.encode()).hexdigest()[:8], 16)}
                if group == "rails":
                    width_m = (((x1-x0) if side % 2 == 0 else (y1-y0)) / counts[side]) / 100.0
                    out[name]["length_m"] = round(width_m if wood in ("Nageshi", "Cornice") else width_m-.24, 5)
            index += 4 if kind == 5 else 1
    return out


def placement_transform(row, wall_cm):
    x0, y0, x1, y1 = row["rect"]
    side = row["side"]
    length = (x1-x0) if side % 2 == 0 else (y1-y0)
    width = length / max(1, math.floor(length / 180 + .5))
    distance = (row["bay"] + (.5 if row["group"] == "rails" else 0)) * width
    start, along = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))[side], ((1, 0), (0, 1), (-1, 0), (0, -1))[side]
    return {"location": [start[0]+along[0]*distance, start[1]+along[1]*distance, 0],
            "rotation": [0, (0, 90, 180, -90)[side], 0], "scale": [1, 1, wall_cm/700 if wall_cm > 0 else 1]}


def placement_coverage(meta, project, commit=None):
    """Fail closed while retaining a report for genuine, complete originals.

    Only the named first dojo's unique logs can qualify. Pool/floor instance
    counts remain inventory; estate source coverage is not runtime coverage.
    """
    result = {"status": "rejected_source_binding", "qualified": False, "errors": [],
              "scope": CAPTURE_SCOPE, "estate_qualified": False, "pool_placement_qualified": False,
              "floor_placement_qualified": False, "photoreal_qualified": False}
    active = any(mesh_identity(m)[0] == "DojoTimbers" for m in meta.get("meshes", [])) or any(
        r["exists"] for r in coverage_inputs(meta) if r["path"] in COVERAGE_INPUTS[8:])
    if not active:
        return {**result, "status": "no_timber_inputs_or_instances", "errors": []}
    try:
        if not re.fullmatch(r"[0-9a-f]{40}", str(commit)):
            raise ValueError("timber binding requires the archive's exact source commit")
        project = project.resolve()
        observed = {r["path"]: r for r in coverage_inputs(meta)}
        raw = {}
        def read(path):
            if path not in raw:
                if path not in observed or not observed[path]["exists"]:
                    raise ValueError(f"missing runtime binding source: {path}")
                data = (project / path).read_bytes()
                r = observed[path]
                if len(data) != r["bytes"] or hashlib.md5(data).hexdigest() != r["md5"].lower():
                    raise ValueError(f"stale runtime binding source: {path}")
                blob = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=project, capture_output=True)
                if blob.returncode or blob.stdout != data:
                    raise ValueError(f"binding source differs from archive commit: {path}")
                raw[path] = data
            return raw[path]
        def sha(path): return hashlib.sha256(read(path)).hexdigest()
        def unique_object(pairs):
            value = {}
            for key, item in pairs:
                if key in value: raise ValueError(f"duplicate binding JSON key: {key}")
                value[key] = item
            return value
        def doc(path): return json.loads(read(path), object_pairs_hook=unique_object)
        for path, digest in LAYOUT_SOURCES.items():
            if sha(path) != digest: raise ValueError(f"unreviewed timber layout source: {path}")
        binding = doc(BINDING)
        if (binding.get("schema") != "sora-dojo-timber-campaign-binding-v1" or binding.get("binder") != BINDER
                or binding.get("binder_sha256") != sha(BINDER)):
            raise ValueError("stale/unsupported timber binder identity")
        if binding.get("campaign") != {path: sha(path) for path in COVERAGE_INPUTS[:8]}:
            raise ValueError("stale or incomplete chapter binding")
        if binding.get("manifests") != {path: sha(path) for path in MANIFESTS}:
            raise ValueError("stale or incomplete timber manifest binding")
        halls, chapters, expected = {}, {}, {}
        for path in COVERAGE_INPUTS[:8]:
            chapter = doc(path); chapters[path] = chapter
            ids = set()
            for zone in chapter["space"]["zones"]:
                if zone["id"] in ids: raise ValueError("duplicate chapter zone identity")
                ids.add(zone["id"])
                if zone.get("style") != "estate" or zone.get("form") != "hall": continue
                rect = tuple(vector(zone, "rect", 4))
                if any(v != int(v) for v in rect) or rect[0] >= rect[2] or rect[1] >= rect[3]:
                    raise ValueError("unsupported nonintegral/empty estate hall rectangle")
                rect = tuple(int(v) for v in rect)
                halls.setdefault(rect, []).append(f"{Path(path).name}:{zone['id']}")
                expected.update(hall_layout(rect))
        built = {}
        for path, kit, generator, inputs in (
            (MANIFESTS[0], "NyaagyuDojoTimbers", "scripts/art/create_nyaagyu_dojo_timbers.py", set(MANIFEST_INPUTS)),
            (MANIFESTS[1], "NyaagyuDojoRails", "scripts/art/create_nyaagyu_dojo_rails.py",
             set(MANIFEST_INPUTS)-{"scripts/art/sora_timber_lookdev.py", "scripts/art/sora_prop_lib.py"})):
            manifest = doc(path)
            if (manifest.get("schema_version") != 1 or manifest.get("kit") != kit or manifest.get("generator") != generator
                    or manifest.get("generator_sha256") != sha(generator)
                    or manifest.get("inputs") != {p: sha(p) for p in inputs}):
                raise ValueError(f"stale timber generator/input binding: {path}")
            for row in manifest["placements"]:
                name = row["asset"]
                if name in built: raise ValueError(f"duplicate timber manifest placement: {name}")
                if name not in expected: raise ValueError(f"unexpected/stale timber manifest placement: {name}")
                ref = expected[name]
                if (ref["group"] != ("columns" if kit == "NyaagyuDojoTimbers" else "rails") or
                        any(row.get(k) != ref[k] for k in ("rect", "side", "bay", "kind", "seed")) or
                        ("name" in row and row["name"] != name)):
                    raise ValueError(f"timber manifest placement differs from chapter layout: {name}")
                if ref["group"] == "rails" and number(row, "length_m") != ref["length_m"]:
                    raise ValueError(f"timber rail length differs from chapter bay: {name}")
                built[name] = ref
        rows = []
        for rect, uses in sorted(halls.items()):
            layout = hall_layout(rect)
            row = {"rect": list(rect), "zones": uses}
            for group in ("columns", "rails"):
                names = {n for n, r in layout.items() if r["group"] == group}
                own = names & built.keys()
                if group == "rails" and own and own != names: raise ValueError("partial rail hall violates binder contract")
                row[group], row[group+"_with_own_log"] = len(names), len(own)
            rows.append(row)
        totals = {k: sum(r[k] for r in rows) for k in ("columns", "columns_with_own_log", "rails", "rails_with_own_log")}
        if binding.get("halls") != rows or binding.get("coverage") != totals:
            raise ValueError("binding hall/estate counts differ from current chapter-derived placement sets")
        chapter = chapters[CAPTURE_SCOPE["chapter_file"]]
        zones = [z for z in chapter["space"]["zones"] if z.get("style") == "estate" and z.get("form") == "hall"]
        declared = [{"zone": z["id"], "rect": z["rect"], "wall_cm": z.get("wall_cm", 0)} for z in zones]
        if meta.get("capture_scope") != CAPTURE_SCOPE or meta.get("chapter_id") != chapter["id"] or meta.get("chapter_estate_halls") != declared:
            raise ValueError("runtime chapter/scope differs from current chapter source")
        scope = [z for z in zones if z["id"] == CAPTURE_SCOPE["zone"] and z["rect"] == CAPTURE_SCOPE["rect"]]
        if len(scope) != 1: raise ValueError("named capture scope is absent/ambiguous")
        chapter_expected = {}
        for zone in zones:
            for name, row in hall_layout(zone["rect"]).items():
                if name in chapter_expected: raise ValueError("chapter repeats a unique timber placement")
                chapter_expected[name] = (row, zone.get("wall_cm", 0))
        scope_names = set(hall_layout(scope[0]["rect"]))
        if not scope_names <= built.keys(): raise ValueError("named dojo lacks complete column/rail manifests")
        observed_names = set()
        for mesh in meta["meshes"]:
            family, name = mesh_identity(mesh)
            if family != "DojoTimbers" or not timber_kind(name).endswith("_placement"): continue
            if name in observed_names or mesh["instances"] != 1: raise ValueError("duplicate runtime timber placement")
            observed_names.add(name)
            if name not in chapter_expected or name not in built: raise ValueError(f"unexpected runtime timber placement: {name}")
            row, wall = chapter_expected[name]
            transforms = mesh.get("instance_transforms")
            if not isinstance(transforms, list) or len(transforms) != 1: raise ValueError("unique timber lacks its instance transform")
            transform = transforms[0]
            for key, reference in placement_transform(row, wall).items():
                actual = vector(transform, key, 3)
                delta = [((a-b+180)%360-180) if key == "rotation" else a-b for a, b in zip(actual, reference)]
                if math.sqrt(sum(d*d for d in delta)) > (.05 if key == "location" else .001):
                    raise ValueError(f"timber {key} differs from chapter placement: {name}")
            if meta["sm6_requested"] and (not mesh["has_nanite_data"] or mesh["disallow_nanite"] or mesh["force_disable_nanite"]):
                raise ValueError(f"unique timber lacks enabled Nanite resources: {name}")
        required = set(chapter_expected) & built.keys()
        if not meta["sm6_requested"] and observed_names:
            raise ValueError("SM5 unexpectedly selected unique Nanite timber placements")
        if meta["sm6_requested"] and observed_names != required:
            raise ValueError(f"missing runtime timber placements: {len(required-observed_names)}")
        result.update(status="bound_unique_scope" if meta["sm6_requested"] else "bound_sources_sm5_inventory_only",
            qualified=bool(meta["sm6_requested"]), source_commit=commit,
            expected_scope_assets=sorted(scope_names), observed_unique_assets=sorted(observed_names),
            chapter_halls=[r for r in rows if any(z.startswith("chapter_01.json:") for z in r["zones"])],
            estate={"coverage": totals, "halls": rows, "complete_source_logs": all(r[g] == r[g+"_with_own_log"] for r in rows for g in ("columns", "rails"))},
            source_sha256={p: hashlib.sha256(data).hexdigest() for p, data in sorted(raw.items())},
            qualification="source/placement/resource binding only; draw candidates and human geometry review are separate")
    except (ValueError, OSError, KeyError, TypeError) as error:
        result["errors"].append(f"timber placement coverage: {error}")
    return result


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
    coverage_inputs(meta)
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
    seen, unique_timbers = set(), set()
    for mesh in meshes:
        if (not isinstance(mesh, dict) or not isinstance(mesh.get("component"), str) or not mesh["component"]
                or mesh["component"] in seen
                or any(type(mesh.get(k)) is not bool for k in ("has_nanite_data", "disallow_nanite", "force_disable_nanite")) or integer(mesh, "instances") < 1
                or not isinstance(mesh.get("materials"), list) or not mesh["materials"]):
            raise ValueError("invalid/duplicate production dojo component identity")
        seen.add(mesh["component"])
        family, name = mesh_identity(mesh)
        if family == "DojoTimbers":
            kind = timber_kind(name)
            if kind.endswith("_placement"):
                if name in unique_timbers or mesh["instances"] != 1:
                    raise ValueError("duplicate unique timber placement; a pool is not placement coverage")
                unique_timbers.add(name)
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


def inspect(meta, images, width, height, decode, placement=None):
    """Return an archivable result even when genuine SM6 draw evidence is absent."""
    sm6 = validate_metadata(meta, list(images), width, height)
    result = {"schema": "sora-arena.nanite-pixel-review.v1", "actual_shader_platform": meta["shader_platform"],
              "adapter": meta["adapter"], "scope": SCOPE, "human_geometry_review_required": True,
              "hardware_m1_qualified": False, "release_qualified": False, "errors": [], "cameras": {}}
    families = {family: {"components": 0, "instances": 0, "assets": set()} for family in ("DojoKit", "DojoTimbers")}
    kinds = {}
    for mesh in meta["meshes"]:
        family, name = mesh_identity(mesh)
        families[family]["components"] += 1
        families[family]["instances"] += mesh["instances"]
        families[family]["assets"].add(name)
        if family == "DojoTimbers":
            kind = timber_kind(name)
            kinds[kind] = kinds.get(kind, 0) + mesh["instances"]
    for family in families.values():
        family["assets"] = sorted(family["assets"])
    result["observed_families"] = families
    result["timber_placement_coverage"] = {**(placement or COVERAGE_PENDING), "observed_kinds": kinds}
    if placement is not None:
        result["errors"].extend(placement["errors"])
    elif kinds or any(record["exists"] for record in meta["coverage_inputs"] if record["path"] in COVERAGE_INPUTS[8:]):
        result["errors"].append("timber placement coverage is incomplete: frozen current-chapter-bound manifest contract required")
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
    project = project.resolve()
    roots = {family: (project / "Content/Generated/Environment" / family).resolve() for family in ("DojoKit", "DojoTimbers")}
    expected = set()
    for mesh in meta.get("meshes", []):
        family, name = mesh_identity(mesh)
        expected.add(roots[family] / (name + ".uasset"))
    out, seen = [], set()
    for record in files:
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            raise ValueError("invalid Nanite asset file identity")
        path = Path(record["path"]).resolve()
        if path in seen or path.suffix not in (".uasset", ".uexp", ".ubulk") or path.with_suffix(".uasset") not in expected:
            raise ValueError("duplicate or unexpected Nanite asset file")
        seen.add(path)
        data = path.read_bytes()
        if (integer(record, "bytes") != len(data) or not re.fullmatch(r"[0-9a-fA-F]{32}", str(record.get("md5", "")))
                or hashlib.md5(data).hexdigest() != record["md5"].lower()):
            raise ValueError("dojo package bytes changed since the runtime inventory")
        out.append({"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "runtime_md5": record["md5"]})
    for mesh in meta.get("meshes", []):
        path = Path(mesh.get("package_file", "")).resolve()
        family, name = mesh_identity(mesh)
        if path != roots[family] / (name + ".uasset") or path not in seen:
            raise ValueError("dojo component identity lacks its exact original package bytes")
    for record in coverage_inputs(meta):
        path = (project / record["path"]).resolve()
        if path != project / record["path"] or path.is_file() is not record["exists"]:
            raise ValueError("timber coverage input path/existence changed since runtime")
        identity = {"path": str(path), "exists": record["exists"], "role": "unqualified_placement_coverage_input"}
        if record["exists"]:
            data = path.read_bytes()
            if len(data) != record["bytes"] or hashlib.md5(data).hexdigest() != record["md5"].lower():
                raise ValueError("timber coverage input bytes changed since runtime")
            identity.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), runtime_md5=record["md5"])
        out.append(identity)
    return out
