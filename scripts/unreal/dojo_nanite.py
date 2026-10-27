"""Dojo importer contract; plain Python helpers, no imports or editor at module load.

This enables the existing modules only. It neither creates unique beam art nor
establishes actual Nanite raster coverage or M1/package qualification.
"""
import hashlib
import json
import math
from pathlib import Path


def require(condition, message):
    if not condition:
        raise RuntimeError(f"Dojo Nanite audit: {message}")


def components(value, axes, label):
    values = []
    for axis in axes:
        component = getattr(value, axis)
        require(type(component) in (int, float) and math.isfinite(component), f"{label}: non-finite {axis}")
        # Signed zero has the same numeric content. No other rounding or
        # tolerance is used in the geometry comparison.
        values.append(float(component) if component else 0.0)
    return tuple(values)


def geometry_bounds(points):
    require(bool(points), "empty geometry has no conventional bounds")
    return {"min": [min(point[axis] for point in points) for axis in range(3)],
            "max": [max(point[axis] for point in points) for axis in range(3)]}


def canonical_section(section, label):
    """Exact oriented triangle content, independent of index/vertex order.

    The editor API reads conventional render-LOD buffers, including packed
    normal/tangent readback and UV0. It does not expose UV1+, colors, or raw
    buffer bytes. Preserve duplicates and winding; only cyclic corner order
    and ordering among complete triangles may change.
    """
    require(len(section) == 5, f"{label}: unexpected section readback")
    positions, indices, normals, uvs, tangents = section
    count = len(positions)
    require(count > 0 and len(indices) > 0 and len(indices) % 3 == 0, f"{label}: empty/malformed triangle data")
    require(all(len(values) == count for values in (normals, uvs, tangents)), f"{label}: incomplete vertex attributes")
    require(all(type(index) is int and 0 <= index < count for index in indices), f"{label}: out-of-range triangle index")
    require(set(indices) == set(range(count)), f"{label}: section API returned unreferenced vertices")
    corners = []
    for index in range(count):
        tangent = tangents[index]
        flip = tangent.get_editor_property("flip_tangent_y")
        require(type(flip) is bool, f"{label}: invalid tangent handedness")
        corners.append(components(positions[index], "xyz", label + " position") +
                       components(normals[index], "xyz", label + " normal") +
                       components(uvs[index], "xy", label + " UV0") +
                       components(tangent.get_editor_property("tangent_x"), "xyz", label + " tangent") + (flip,))
    triangles = []
    for index in range(0, len(indices), 3):
        a, b, c = (corners[indices[index + offset]] for offset in range(3))
        triangles.append(min((a, b, c), (b, c, a), (c, a, b)))
    canonical = tuple(sorted(triangles))
    return canonical, {"triangles": len(triangles), "referenced_vertices": count,
                       "bounds": geometry_bounds([corner[:3] for corner in corners]),
                       "oriented_content_sha256": hashlib.sha256(json.dumps(canonical, separators=(",", ":"), allow_nan=False).encode()).hexdigest()}


def composite_bounds(mesh, conventional_bounds):
    """Validate culling coverage without rewriting Nanite's expanded bounds."""
    bounds = mesh.get_bounds()
    origin = components(bounds.origin, "xyz", "composite bounds origin")
    extent = components(bounds.box_extent, "xyz", "composite bounds extent")
    require(all(value >= 0 for value in extent), "negative composite bounds extent")
    low = [origin[i] - extent[i] for i in range(3)]
    high = [origin[i] + extent[i] for i in range(3)]
    require(all(math.isfinite(value) for value in low + high), "non-finite composite bounds endpoints")
    require(all(low[i] <= conventional_bounds["min"][i] and high[i] >= conventional_bounds["max"][i] for i in range(3)),
            "composite culling bounds do not contain conventional geometry")
    return {"origin": list(origin), "extent": list(extent), "min": low, "max": high}


def prepare_conventional(mesh, subsystem):
    # UE's FBX reimport restores the existing mesh's Nanite enablement over
    # the import option. Explicitly reset that before importing source again.
    settings = subsystem.get_nanite_settings(mesh)
    if settings.get_editor_property("enabled"):
        settings.set_editor_property("enabled", False)
        subsystem.set_nanite_settings(mesh, settings, True)
    # A previous import's dedicated Nanite source must not survive the new
    # ordinary FBX import. The engine removes its source data when this named
    # source is cleared; a false/ineffective reset is not an admissible base.
    if subsystem.get_nanite_source_filename(mesh):
        require(subsystem.update_nanite_source_filename(mesh, ""), "could not remove previous Nanite source")
    require(not subsystem.get_nanite_source_filename(mesh), "previous Nanite source remained after reset")
    require(subsystem.get_nanite_settings(mesh).get_editor_property("enabled") is False,
            "could not establish the conventional import baseline")


def conventional(mesh, subsystem, procedural):
    """Return a compact report plus exact geometry for direct comparison.

    GetSectionFromStaticMesh warns about CPU access in editor when disabled;
    its cooked-build warning is recorded, never bypassed by changing the flag.
    """
    lods, geometry, all_points = [], [], []
    for index in range(subsystem.get_lod_count(mesh)):
        sections, section_geometry, lod_points = [], [], []
        for section in range(mesh.get_num_sections(index)):
            canonical, observed = canonical_section(procedural.get_section_from_static_mesh(mesh, index, section), f"LOD{index} section{section}")
            sections.append({"material_slot": subsystem.get_lod_material_slot(mesh, index, section),
                             "collision": subsystem.is_section_collision_enabled(mesh, index, section),
                             "cast_shadow": subsystem.is_section_cast_shadow_enabled(mesh, index, section),
                             "geometry": observed})
            section_geometry.append(canonical)
            lod_points.extend((observed["bounds"]["min"], observed["bounds"]["max"]))
        require(sum(section["geometry"]["triangles"] for section in sections) == mesh.get_num_triangles(index),
                f"LOD{index}: section readback does not cover reported render triangles")
        lods.append({"triangles": mesh.get_num_triangles(index), "vertices": mesh.get_num_vertices(index),
                     "uv_channels": mesh.get_num_tex_coords(index), "sections": sections,
                     "geometry_bounds": geometry_bounds(lod_points)})
        geometry.append(tuple(section_geometry))
        all_points.extend(lod_points)
    slots = mesh.get_editor_property("static_materials")
    bounds = geometry_bounds(all_points)
    screens = list(subsystem.get_lod_screen_sizes(mesh))
    require(len(screens) == len(lods) and all(type(value) in (int, float) and math.isfinite(value) and value >= 0 for value in screens),
            "invalid conventional screen sizes")
    return {"lods": lods, "screen_sizes": screens,
            "slot_names": [str(slot.material_slot_name) for slot in slots],
            "materials": [mesh.get_material(index).get_path_name() if mesh.get_material(index) else None
                          for index in range(len(slots))],
            "geometry_bounds": bounds, "composite_bounds": composite_bounds(mesh, bounds),
            "allow_cpu_access": bool(mesh.get_editor_property("allow_cpu_access")),
            "simple_collision_count": subsystem.get_simple_collision_count(mesh),
            "collision_complexity": str(subsystem.get_collision_complexity(mesh))}, tuple(geometry)


def material_audit(material, unreal, library):
    """Conservative support audit for the actual opaque/craft/shoji bindings.

    Does not rewrite blends, shading, sidedness, overrides or shader graphs.
    Engine Nanite audit and original rendered comparison remain required.
    """
    parent = material.get_base_material()
    require(parent is not None, "bound material has no base")
    overrides = material.get_editor_property("base_property_overrides")
    # These reflected UPROPERTY fields are editor-only in the Python wrapper;
    # direct attribute access is not generated for them in the pinned engine.
    prop = overrides.get_editor_property
    blend = prop("blend_mode") if prop("override_blend_mode") else parent.get_editor_property("blend_mode")
    shading = prop("shading_model") if prop("override_shading_model") else parent.get_editor_property("shading_model")
    require(parent.get_editor_property("material_domain") == unreal.MaterialDomain.MD_SURFACE, "non-surface dojo material")
    require(blend in (unreal.BlendMode.BLEND_OPAQUE, unreal.BlendMode.BLEND_MASKED), "unsupported dojo blend; keep this section conventional pending review")
    require(shading in (unreal.MaterialShadingModel.MSM_DEFAULT_LIT, unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE),
            "unreviewed dojo shading model; do not silently replace its material")
    require(library.has_material_usage(material, unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES), "missing instanced material usage")
    require(library.has_material_usage(material, unreal.MaterialUsage.MATUSAGE_NANITE), "missing/overridden Nanite material usage")
    return {"material": material.get_path_name(), "parent": parent.get_path_name(), "blend": str(blend), "shading": str(shading),
            "two_sided": bool(prop("two_sided") if prop("override_two_sided") else parent.get_editor_property("two_sided"))}


def verify_lod0_source(module, source_root):
    source = (Path(source_root) / module["lods"][0]["file"]).resolve()
    require(source.is_file(), f"{module['asset']}: original LOD0 source is missing")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    require(digest == module["lods"][0]["sha256"], f"{module['asset']}: original LOD0 source hash changed")
    return source, digest


def require_nanite_source(mesh, subsystem, source):
    filename = subsystem.get_nanite_source_filename(mesh)
    require(bool(filename) and Path(filename).resolve() == source, "dedicated Nanite source filename differs from verified LOD0")
    return str(filename)


def audit_saved_module(module, source_root, unreal, subsystem, assets, library):
    """Reopen one imported package and inspect it without saving or repairing it."""
    name = module["asset"]
    mesh = assets.load_asset("/Game/Generated/Environment/DojoKit/" + name)
    require(isinstance(mesh, unreal.StaticMesh), f"{name}: saved static mesh is missing")
    source, digest = verify_lod0_source(module, source_root)
    filename = require_nanite_source(mesh, subsystem, source)
    report, _ = conventional(mesh, subsystem, unreal.ProceduralMeshLibrary)
    require([lod["triangles"] for lod in report["lods"]] == [lod["triangles"] for lod in module["lods"]],
            f"{name}: saved fallback LODs differ from the authored triangle counts")
    require(len(report["slot_names"]) == len(set(report["slot_names"])) and
            set(report["slot_names"]) == set(module["material_slots"]), f"{name}: saved material slots differ")
    settings = subsystem.get_nanite_settings(mesh)
    expected = {"enabled": True, "generate_fallback": unreal.NaniteGenerateFallback.ENABLED,
                "fallback_target": unreal.NaniteFallbackTarget.PERCENT_TRIANGLES,
                "fallback_percent_triangles": 1.0, "fallback_relative_error": 0.0,
                "keep_percent_triangles": 1.0, "trim_relative_error": 0.0}
    require(all(settings.get_editor_property(k) == v for k, v in expected.items()),
            f"{name}: saved Nanite/full-fallback settings differ")
    triangles, vertices = mesh.get_num_nanite_triangles(), mesh.get_num_nanite_vertices()
    require(triangles > 0 and vertices > 0, f"{name}: saved Nanite resources are empty")
    require(all(mesh.get_material(i) is not None for i in range(len(report["slot_names"]))),
            f"{name}: saved material binding is missing")
    materials = [material_audit(mesh.get_material(i), unreal, library) for i in range(len(report["slot_names"]))]
    return {"asset": name, "conventional": report, "materials": materials,
            "source": {"file": str(source), "sha256": digest, "readback": filename},
            "nanite_triangles": triangles, "nanite_vertices": vertices,
            "settings": {k: v if isinstance(v, (bool, float)) else str(v) for k, v in expected.items()}}


def read_import_baselines(log_path, expected_names):
    """Read audit data from the completed import, never execute log contents."""
    lines = Path(log_path).read_text(errors="replace").splitlines()
    require(not any("LogPython: Error" in line or "Traceback (most recent call last)" in line for line in lines),
            "import baseline contains a Python failure")
    marker = f"LogPython: NYAAGYU_DOJO_KIT_READY: {len(expected_names)} modules:"
    require(any(marker in line for line in lines), "import baseline has no full completion marker")
    rows = {}
    for line in lines:
        _, separator, payload = line.partition("LogPython: SORA_DOJO_NANITE_IMPORT ")
        if separator:
            row = json.loads(payload)
            require(row["asset"] not in rows, "duplicate import baseline module")
            rows[row["asset"]] = row
    require(set(rows) == set(expected_names), "import baseline module inventory differs")
    return rows


def verify_saved_import(observed, baseline):
    """Bind reopened geometry, material behavior and resources to import output."""
    require(observed["asset"] == baseline["asset"], "saved/imported module identity differs")
    for key, original in (("conventional", "conventional_after"), ("materials", "materials"),
                          ("settings", "settings"), ("nanite_triangles", "nanite_input_triangles"),
                          ("nanite_vertices", "nanite_input_vertices")):
        require(observed[key] == baseline[original], f"{observed['asset']}: saved {key} differs from completed import")
    require(observed["source"]["sha256"] == baseline["nanite_source"]["sha256"] and
            observed["source"]["file"] == baseline["nanite_source"]["resolved_file"],
            "saved/imported original source identity differs")


def enable_full_fallback(mesh, module, subsystem, unreal, library, assets, source_root):
    source, source_digest = verify_lod0_source(module, source_root)
    require(subsystem.get_nanite_settings(mesh).get_editor_property("enabled") is False and
            not subsystem.get_nanite_source_filename(mesh), "ordinary baseline must precede dedicated Nanite source import")
    require(assets.save_loaded_asset(mesh, only_if_is_dirty=False), f"{module['asset']}: could not save conventional baseline")
    before, before_geometry = conventional(mesh, subsystem, unreal.ProceduralMeshLibrary)
    expected = [lod["triangles"] for lod in module["lods"]]
    require([lod["triangles"] for lod in before["lods"]] == expected,
            f"{module['asset']}: conventional source LOD triangle counts differ from the authored manifest")
    require(len(before["slot_names"]) == len(module["material_slots"]) and
            set(before["slot_names"]) == set(module["material_slots"]), f"{module['asset']}: source material slot set changed")
    require(all(lod["vertices"] > 0 and lod["uv_channels"] > 0 and lod["sections"] for lod in before["lods"]), "empty conventional geometry/UVs/sections")
    for index, lod in enumerate(before["lods"]):
        require(all(0 <= s["material_slot"] < len(before["slot_names"]) for s in lod["sections"]), f"LOD{index} has invalid material section")
    materials = [material_audit(mesh.get_material(index), unreal, library) for index in range(len(before["slot_names"]))]
    settings = subsystem.get_nanite_settings(mesh)
    values = {"enabled": True, "generate_fallback": unreal.NaniteGenerateFallback.ENABLED,
              "fallback_target": unreal.NaniteFallbackTarget.PERCENT_TRIANGLES, "fallback_percent_triangles": 1.0,
              "fallback_relative_error": 0.0, "keep_percent_triangles": 1.0, "trim_relative_error": 0.0}
    for key, value in values.items(): settings.set_editor_property(key, value)
    # At full fallback the Nanite input builder still uses different corner
    # overlap rules than ordinary LOD0. Keep the verified FBX as a dedicated
    # Nanite source so conventional LODs retain their ordinary build path.
    # Capture before_geometry above BEFORE this API can change the asset.
    subsystem.set_nanite_settings(mesh, settings, False)
    verify_lod0_source(module, source_root)
    require(subsystem.import_nanite_hi_res_mesh(mesh, str(source), False), f"{module['asset']}: dedicated Nanite source import failed")
    source_readback = require_nanite_source(mesh, subsystem, source)
    subsystem.set_nanite_settings(mesh, settings, True)
    # The Nanite build can zero render screen sizes even though source-model
    # thresholds remain. Saving alone does not reliably restore them. The
    # engine setter updates source and render thresholds without rebuilding.
    require(subsystem.set_lod_screen_sizes(mesh, before["screen_sizes"]), f"{module['asset']}: could not restore source LOD screen sizes")
    require(assets.save_loaded_asset(mesh, only_if_is_dirty=False), f"{module['asset']}: could not save Nanite/fallback mesh before final audit")
    source_readback = require_nanite_source(mesh, subsystem, source)
    verify_lod0_source(module, source_root)
    actual = subsystem.get_nanite_settings(mesh)
    for key, value in values.items():
        require(actual.get_editor_property(key) == value, f"{module['asset']}: Nanite setting {key} was not retained")
    # UE GetRenderData waits for asynchronous render data before these queries;
    # GetNumNanite* returns zero without valid page/root resource data.
    nanite_triangles, nanite_vertices = mesh.get_num_nanite_triangles(), mesh.get_num_nanite_vertices()
    require(nanite_triangles > 0 and nanite_vertices > 0, f"{module['asset']}: built Nanite root resources are absent")
    after, after_geometry = conventional(mesh, subsystem, unreal.ProceduralMeshLibrary)
    require(before_geometry == after_geometry, f"{module['asset']}: full fallback changed conventional oriented triangle geometry/attributes")
    for key in before:
        if key == "composite_bounds":
            # Nanite hierarchy simplification can expand these culling
            # bounds. Both snapshots separately proved geometry containment.
            continue
        if key == "screen_sizes":
            same = len(before[key]) == len(after[key]) and all(math.isclose(a, b, rel_tol=0, abs_tol=1e-5) for a, b in zip(before[key], after[key]))
        else:
            same = before[key] == after[key]
        require(same, f"{module['asset']}: full fallback changed conventional {key}")
    require(materials == [material_audit(mesh.get_material(index), unreal, library) for index in range(len(before["slot_names"]))],
            f"{module['asset']}: material behavior changed during Nanite build")
    return {"asset": module["asset"], "nanite_input_triangles": nanite_triangles, "nanite_input_vertices": nanite_vertices,
            "nanite_source": {"mode": "dedicated source; identical verified LOD0 FBX", "file": module["lods"][0]["file"],
                              "resolved_file": str(source), "readback_file": source_readback, "sha256": source_digest},
            "settings": {key: value if isinstance(value, (bool, float)) else str(value) for key, value in values.items()},
            "conventional_before": before, "conventional_after": after, "materials": materials,
            "geometry_readback": {"method": "ProceduralMeshLibrary.get_section_from_static_mesh", "editor_only": True,
                                  "comparison": "exact oriented per-section triangles; cyclic corner and vertex/index reorder allowed",
                                  "attributes": ["position", "normal", "UV0", "tangent_x", "flip_tangent_y"],
                                  "not_compared": ["UV1+ values", "vertex colors", "raw buffer byte layout"],
                                  "cpu_access_flag_changed": False,
                                  "expected_editor_warning": None if before["allow_cpu_access"] else "GetSectionFromStaticMesh: Allow CPU Access is required for cooked conversion; flag remains disabled"},
            "draw_evidence": "not established by import; run original dojo Lit/Mask/Triangles diagnostic",
            "m1_qualified": False, "unique_beam_art": False}
