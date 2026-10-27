"""Import the 20 corrected weapon meshes with authored LODs/maps into ArtReview.

Pinned editor only. mode=validate opens and checks the saved packages in a fresh
process without changing them. out=Saved/<new-directory> retains full render
arrays and measured readback. Neither mode replaces gameplay meshes or admits art.
"""
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import sys

import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runtime_weapon_review as R
from sora_engine_pin import require_running_engine

require_running_engine("Weapon ArtReview import")
root = Path(unreal.Paths.project_dir()).resolve()
options = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
mode = options.get("mode", "import")
R.require(mode in {"import", "validate"}, "mode must be import or validate")
plan, records = R.source_plan(root)  # Complete source admission precedes every write.
out = (root / options.get("out", "Saved/WeaponReviewImports/" +
                         datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ"))).resolve()
R.require(out.is_relative_to(root / "Saved") and out != root / "Saved", "evidence must stay under Saved/")
out.mkdir(parents=True, exist_ok=False)
assets = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
materials = unreal.MaterialEditingLibrary
meshes = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)


def imported(file, destination, name, import_options=None):
    task = unreal.AssetImportTask()
    task.filename, task.destination_path, task.destination_name = str(root / file), destination, name
    task.automated, task.replace_existing, task.save = True, True, True
    if import_options is not None:
        task.options = import_options
    tools.import_asset_tasks([task])
    value = assets.load_asset(destination + "/" + name)
    R.require(value is not None, "import failed: " + name)
    return value


def save(value):
    R.require(assets.save_loaded_asset(value), "save failed: " + value.get_path_name())


def material_assets(kit, record):
    destination = R.DESTINATION + "/" + kit
    spec = R.material_plan(record)
    textures = {}
    for channel, entry in record["textures"].items():
        name = Path(entry["file"]).stem
        path = destination + "/Textures/" + name
        if mode == "import":
            assets.make_directory(destination + "/Textures")
            texture = imported(entry["file"], destination + "/Textures", name)
            texture.set_editor_property("srgb", channel == "BaseColor")
            texture.set_editor_property("max_texture_size", spec["max_texture_size"])
            if channel == "Normal":
                texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
                texture.set_editor_property("flip_green_channel", False)
            elif channel in {"ORM", "Mask"}:
                texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
            save(texture)
        else:
            texture = assets.load_asset(path)
        R.require(isinstance(texture, unreal.Texture2D), "missing texture: " + path)
        R.require(texture.get_editor_property("srgb") == (channel == "BaseColor"), "wrong texture color space")
        R.require(texture.get_editor_property("max_texture_size") == 2048, "wrong texture size policy")
        if channel == "Normal":
            R.require(texture.get_editor_property("compression_settings") == unreal.TextureCompressionSettings.TC_NORMALMAP
                      and not texture.get_editor_property("flip_green_channel"), "NormalDX changed convention")
        if channel in {"ORM", "Mask"}:
            R.require(texture.get_editor_property("compression_settings") == unreal.TextureCompressionSettings.TC_MASKS,
                      "packed map compression changed")
        textures[channel] = texture
    path = destination + "/" + spec["name"]
    material = assets.load_asset(path) if assets.does_asset_exist(path) else None
    if mode == "import":
        if material is None:
            material = tools.create_asset(spec["name"], destination, unreal.Material, unreal.MaterialFactoryNew())
        R.require(isinstance(material, unreal.Material), "wrong material type")
        for expression in list(materials.get_material_expressions(material)):
            materials.delete_material_expression(material, expression)
        material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED if spec["masked"] else unreal.BlendMode.BLEND_OPAQUE)
        material.set_editor_property("two_sided", spec["two_sided"])
        material.set_editor_property("opacity_mask_clip_value", spec["opacity_clip"])

        def node(kind, x, y, **properties):
            value = materials.create_material_expression(material, kind, x, y)
            for key, val in properties.items():
                value.set_editor_property(key, val)
            return value

        def link(left, pin, right, slot):
            R.require(materials.connect_material_expressions(left, pin, right, slot), "material link failed")

        def output(value, pin, property_name):
            R.require(materials.connect_material_property(value, pin, property_name), "material output failed")

        samples = {}
        for i, (channel, texture) in enumerate(textures.items()):
            sampler = (unreal.MaterialSamplerType.SAMPLERTYPE_COLOR if channel == "BaseColor" else
                       unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel == "Normal" else
                       unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
            samples[channel] = node(unreal.MaterialExpressionTextureSampleParameter2D, -800, i*220,
                                    parameter_name=channel+"Map", texture=texture, sampler_type=sampler)
        output(samples["BaseColor"], "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
        output(samples["Normal"], "RGB", unreal.MaterialProperty.MP_NORMAL)
        for pin, prop in (("R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION),
                          ("G", unreal.MaterialProperty.MP_ROUGHNESS), ("B", unreal.MaterialProperty.MP_METALLIC)):
            output(samples["ORM"], pin, prop)
        if spec["masked"]:
            output(samples["BaseColor"], "A", unreal.MaterialProperty.MP_OPACITY_MASK)
        color = node(unreal.MaterialExpressionVectorParameter, -500, 900, parameter_name="EmissiveColor",
                     default_value=unreal.LinearColor(*spec["emissive_color"], 1.0))
        strength = node(unreal.MaterialExpressionScalarParameter, -500, 1100, parameter_name="EmissiveStrength",
                        default_value=spec["emissive_strength"])
        masked = node(unreal.MaterialExpressionMultiply, -250, 700)
        emission = node(unreal.MaterialExpressionMultiply, 0, 700)
        link(samples["Mask"], "R", masked, "A")
        link(color, "RGB", masked, "B")
        link(masked, "", emission, "A")
        link(strength, "", emission, "B")
        output(emission, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        materials.layout_material_expressions(material)
        materials.recompile_material(material)
        save(material)
    R.require(isinstance(material, unreal.Material), "missing saved material: " + path)
    graph = verify_material(material, textures, spec)
    return material, {"path": material.get_path_name(), "spec": spec, "graph": graph,
                      "textures": {k: v.get_path_name() for k, v in textures.items()}}


def verify_material(material, textures, spec):
    R.require(material.get_editor_property("blend_mode") == (unreal.BlendMode.BLEND_MASKED if spec["masked"] else unreal.BlendMode.BLEND_OPAQUE), "wrong blend mode")
    R.require(material.get_editor_property("two_sided") == spec["two_sided"], "wrong fibre sidedness")
    R.require(abs(material.get_editor_property("opacity_mask_clip_value") - spec["opacity_clip"]) < 1e-6, "wrong alpha clip")
    expressions = list(materials.get_material_expressions(material))
    parameters = {str(e.get_editor_property("parameter_name")): e for e in expressions
                  if isinstance(e, (unreal.MaterialExpressionTextureSampleParameter2D,
                                    unreal.MaterialExpressionScalarParameter, unreal.MaterialExpressionVectorParameter))}
    R.require(len(parameters) == 6 and len(expressions) == 8, "unexpected material graph")
    for channel, texture in textures.items():
        name = channel + "Map"
        bound = materials.get_material_default_texture_parameter_value(material, name)
        R.require(bound is not None and bound.get_path_name() == texture.get_path_name(), "wrong map binding: " + channel)
        sampler = (unreal.MaterialSamplerType.SAMPLERTYPE_COLOR if channel == "BaseColor" else
                   unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel == "Normal" else unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
        R.require(parameters[name].get_editor_property("sampler_type") == sampler, "wrong map sampler: " + channel)
    graph = {}
    for name, prop, parameter, pins in (
        ("BaseColor", unreal.MaterialProperty.MP_BASE_COLOR, "BaseColorMap", {"RGB", ""}),
        ("Normal", unreal.MaterialProperty.MP_NORMAL, "NormalMap", {"RGB", ""}),
        ("AO", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION, "ORMMap", {"R"}),
        ("Roughness", unreal.MaterialProperty.MP_ROUGHNESS, "ORMMap", {"G"}),
        ("Metallic", unreal.MaterialProperty.MP_METALLIC, "ORMMap", {"B"}),
    ):
        node = materials.get_material_property_input_node(material, prop)
        pin = materials.get_material_property_input_node_output_name(material, prop)
        R.require(node == parameters[parameter] and pin in pins, "wrong material output: " + name)
        graph[name] = [parameter, pin]
    opacity = materials.get_material_property_input_node(material, unreal.MaterialProperty.MP_OPACITY_MASK)
    R.require(opacity == (parameters["BaseColorMap"] if spec["masked"] else None), "wrong opacity source")
    if spec["masked"]:
        R.require(materials.get_material_property_input_node_output_name(material, unreal.MaterialProperty.MP_OPACITY_MASK) == "A", "wrong opacity channel")
    emission = materials.get_material_property_input_node(material, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    R.require(isinstance(emission, unreal.MaterialExpressionMultiply), "wrong emission operator")
    inputs = [n for n in materials.get_inputs_for_material_expression(material, emission) if n is not None]
    R.require(len(inputs) == 2 and parameters["EmissiveStrength"] in inputs, "missing emission strength")
    masked = next(n for n in inputs if n != parameters["EmissiveStrength"])
    R.require(isinstance(masked, unreal.MaterialExpressionMultiply), "wrong emission mask operator")
    inputs = [n for n in materials.get_inputs_for_material_expression(material, masked) if n is not None]
    R.require(len(inputs) == 2 and parameters["MaskMap"] in inputs and parameters["EmissiveColor"] in inputs,
              "wrong emission inputs")
    R.require(materials.get_input_node_output_name_for_material_expression(masked, parameters["MaskMap"]) == "R", "wrong emission mask channel")
    R.require(materials.get_input_node_output_name_for_material_expression(masked, parameters["EmissiveColor"]) in {"RGB", ""},
              "wrong emission color channel")
    R.require(materials.get_input_node_output_name_for_material_expression(emission, masked) == "" and
              materials.get_input_node_output_name_for_material_expression(emission, parameters["EmissiveStrength"]) == "" and
              materials.get_material_property_input_node_output_name(material, unreal.MaterialProperty.MP_EMISSIVE_COLOR) == "",
              "wrong emission product/strength channel")
    color = materials.get_material_default_vector_parameter_value(material, "EmissiveColor")
    strength = materials.get_material_default_scalar_parameter_value(material, "EmissiveStrength")
    R.require(all(abs(a-b) < 1e-5 for a, b in zip([color.r, color.g, color.b], spec["emissive_color"])) and
              abs(strength-spec["emissive_strength"]) < 1e-5, "changed authored glow")
    return {**graph, "OpacityMask": "BaseColorMap.A" if spec["masked"] else None,
            "Emissive": {"mask": "MaskMap.R", "linear_rgb": [color.r, color.g, color.b], "strength": strength}}


def vec(v):
    return [v.x, v.y, v.z]


report = {"mode": mode, "engine": unreal.SystemLibrary.get_engine_version(), "destination": R.DESTINATION,
          "envelope_sha256": R.ENVELOPE_SHA256, "importer_sha256": R.sha(Path(__file__).read_bytes()),
          "gate_sha256": R.sha(Path(R.__file__).read_bytes()), "materials": {}, "meshes": {},
          "source_art_defects": [{"mesh": name, "lod": i, "atlas_uv_outside_corners": lod["atlas_uv_outside_corners"],
                                  "uv_min": lod["uv_min"], "uv_max": lod["uv_max"]}
                                 for name, asset in plan["assets"].items() for i, lod in enumerate(asset["lods"])
                                 if lod["atlas_uv_outside_corners"]],
          "runtime_adopted": False, "visual_accepted": False}
for kit, record in records.items():
    material, report["materials"][kit] = material_assets(kit, record)
    destination = R.DESTINATION + "/" + kit
    for name, asset in record["assets"].items():
        expected = plan["assets"][name]
        if mode == "import":
            ui = unreal.FbxImportUI()
            ui.import_mesh, ui.import_as_skeletal, ui.import_materials, ui.import_textures = True, False, False, False
            ui.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
            ui.static_mesh_import_data.combine_meshes = True
            ui.static_mesh_import_data.generate_lightmap_u_vs = False
            ui.static_mesh_import_data.auto_generate_collision = False
            ui.static_mesh_import_data.remove_degenerates = False
            ui.static_mesh_import_data.normal_import_method = unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
            ui.static_mesh_import_data.set_editor_property("build_nanite", False)
            mesh = imported(asset["lods"][0]["file"], destination, name, ui)
            R.require(isinstance(mesh, unreal.StaticMesh), "wrong mesh type")
            nanite = meshes.get_nanite_settings(mesh)
            nanite.set_editor_property("enabled", False)
            meshes.set_nanite_settings(mesh, nanite, True)
            for lod, entry in enumerate(asset["lods"][1:], 1):
                R.require(meshes.import_lod(mesh, lod, str(root / entry["file"])) == lod, "LOD import failed")
            for lod in range(3):
                build = meshes.get_lod_build_settings(mesh, lod)
                for key, value in R.BUILD.items():
                    build.set_editor_property(key, value)
                meshes.set_lod_build_settings(mesh, lod, build)
            R.require(len(mesh.get_editor_property("static_materials")) == 1, "changed material slots")
            mesh.set_material(0, material)
            R.require(meshes.set_lod_screen_sizes(mesh, asset["screen_sizes"]), "screen threshold edit failed")
            save(mesh)
        else:
            mesh = assets.load_asset(destination + "/" + name)
        R.require(isinstance(mesh, unreal.StaticMesh) and meshes.get_lod_count(mesh) == 3, "missing three-LOD mesh")
        R.require(len(mesh.get_editor_property("static_materials")) == 1 and mesh.get_material(0) == material,
                  "wrong material slot binding")
        R.require(not meshes.get_nanite_settings(mesh).get_editor_property("enabled"), "unexpected Nanite substitution")
        R.require(meshes.get_convex_collision_count(mesh) == meshes.get_simple_collision_count(mesh) == 0,
                  "unexpected weapon collision")
        lods = []
        for lod in range(3):
            build = meshes.get_lod_build_settings(mesh, lod)
            build_values = {key: build.get_editor_property(key) for key in R.BUILD}
            R.require(build_values == R.BUILD, "changed authored-geometry build policy")
            sections = []
            for section in range(mesh.get_num_sections(lod)):
                R.require(meshes.get_lod_material_slot(mesh, lod, section) == 0, "wrong LOD material slot")
                positions, indices, normals, uvs, tangents = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(mesh, lod, section)
                sections.append({"positions": [vec(v) for v in positions], "indices": list(indices),
                                 "normals": [vec(v) for v in normals], "uvs": [[v.x, v.y] for v in uvs],
                                 "tangents": [vec(t.get_editor_property("tangent_x")) for t in tangents]})
            lods.append({"sections": sections, "triangles": mesh.get_num_triangles(lod),
                         "uv_channels": meshes.get_num_uv_channels(mesh, lod), "build": build_values})
        # Keep the measured arrays even if their gate fails; a later review can
        # reproduce the comparison rather than trusting only a summary.
        raw = gzip.compress((json.dumps(lods, allow_nan=False, separators=(",", ":"))+"\n").encode(), mtime=0)
        raw_path = out / (name + ".render.json.gz")
        raw_path.write_bytes(raw)
        screens = list(meshes.get_lod_screen_sizes(mesh))
        geometry = R.geometry_readback(expected, lods, screens)
        probe = unreal.StaticMeshComponent()
        R.require(probe.set_static_mesh(mesh), "socket probe could not bind mesh")
        sockets = {}
        for socket_name in probe.get_all_socket_names():
            socket = mesh.find_socket(socket_name)
            rotation = socket.get_editor_property("relative_rotation")
            sockets[str(socket_name)] = {"position": vec(socket.get_editor_property("relative_location")),
                "scale": vec(socket.get_editor_property("relative_scale")),
                "forward": vec(unreal.MathLibrary.get_forward_vector(rotation)),
                "right": vec(unreal.MathLibrary.get_right_vector(rotation)), "up": vec(unreal.MathLibrary.get_up_vector(rotation))}
        R.socket_readback(name, asset, sockets)
        row = {"path": mesh.get_path_name(), "geometry": geometry, "screen_sizes": screens, "sockets": sockets,
               "material": material.get_path_name(), "nanite": False, "convex": 0, "other_simple": 0,
               "render_arrays": {"file": raw_path.name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}}
        report["meshes"][name] = row
        (out / (name + ".readback.json")).write_text(json.dumps(row, indent=2, allow_nan=False)+"\n")
        unreal.log("WEAPON_REVIEW_MESH " + json.dumps(row, sort_keys=True))
R.require(tuple(sorted(report["meshes"])) == R.ASSETS and len(report["materials"]) == 16, "incomplete review import")
(out / "readback.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
unreal.log("WEAPON_REVIEW_READY: " + str(out / "readback.json"))
