"""Dojo importer contract; plain Python helpers, no imports or editor at module load.

This enables the existing modules only. It neither creates unique beam art nor
establishes actual Nanite raster coverage or M1/package qualification.
"""
import math


def require(condition, message):
    if not condition:
        raise RuntimeError(f"Dojo Nanite audit: {message}")


def xyz(value):
    return [float(value.x), float(value.y), float(value.z)]


def prepare_conventional(mesh, subsystem):
    # UE's FBX reimport restores the existing mesh's Nanite enablement over
    # the import option. Explicitly reset that before importing source again.
    settings = subsystem.get_nanite_settings(mesh)
    if settings.get_editor_property("enabled"):
        settings.set_editor_property("enabled", False)
        subsystem.set_nanite_settings(mesh, settings, True)
    require(subsystem.get_nanite_settings(mesh).get_editor_property("enabled") is False,
            "could not establish the conventional import baseline")


def conventional(mesh, subsystem):
    """Observe real conventional render data; never change LODs/collision/slots."""
    bounds = mesh.get_bounds()
    lods = []
    for index in range(subsystem.get_lod_count(mesh)):
        sections = [{"material_slot": subsystem.get_lod_material_slot(mesh, index, section),
                     "collision": subsystem.is_section_collision_enabled(mesh, index, section),
                     "cast_shadow": subsystem.is_section_cast_shadow_enabled(mesh, index, section)}
                    for section in range(mesh.get_num_sections(index))]
        lods.append({"triangles": mesh.get_num_triangles(index), "vertices": mesh.get_num_vertices(index),
                     "uv_channels": mesh.get_num_tex_coords(index), "sections": sections})
    slots = mesh.get_editor_property("static_materials")
    return {"lods": lods, "screen_sizes": list(subsystem.get_lod_screen_sizes(mesh)),
            "slot_names": [str(slot.material_slot_name) for slot in slots],
            "materials": [mesh.get_material(index).get_path_name() if mesh.get_material(index) else None
                          for index in range(len(slots))],
            "bounds_origin": xyz(bounds.origin), "bounds_extent": xyz(bounds.box_extent),
            "simple_collision_count": subsystem.get_simple_collision_count(mesh),
            "collision_complexity": str(subsystem.get_collision_complexity(mesh))}


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


def enable_full_fallback(mesh, module, subsystem, unreal, library):
    before = conventional(mesh, subsystem)
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
    subsystem.set_nanite_settings(mesh, settings, True)
    actual = subsystem.get_nanite_settings(mesh)
    for key, value in values.items():
        require(actual.get_editor_property(key) == value, f"{module['asset']}: Nanite setting {key} was not retained")
    # UE GetRenderData waits for asynchronous render data before these queries;
    # GetNumNanite* returns zero without valid page/root resource data.
    nanite_triangles, nanite_vertices = mesh.get_num_nanite_triangles(), mesh.get_num_nanite_vertices()
    require(nanite_triangles > 0 and nanite_vertices > 0, f"{module['asset']}: built Nanite root resources are absent")
    after = conventional(mesh, subsystem)
    for key in before:
        if key in ("screen_sizes", "bounds_origin", "bounds_extent"):
            same = len(before[key]) == len(after[key]) and all(math.isclose(a, b, rel_tol=0, abs_tol=1e-5) for a, b in zip(before[key], after[key]))
        else:
            same = before[key] == after[key]
        require(same, f"{module['asset']}: full fallback changed conventional {key}")
    require(materials == [material_audit(mesh.get_material(index), unreal, library) for index in range(len(before["slot_names"]))],
            f"{module['asset']}: material behavior changed during Nanite build")
    return {"asset": module["asset"], "nanite_input_triangles": nanite_triangles, "nanite_input_vertices": nanite_vertices,
            "settings": {key: value if isinstance(value, (bool, float)) else str(value) for key, value in values.items()},
            "conventional_before": before, "conventional_after": after, "materials": materials,
            "draw_evidence": "not established by import; run original dojo Lit/Mask/Triangles diagnostic",
            "m1_qualified": False, "unique_beam_art": False}
