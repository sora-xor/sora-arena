"""Validate the CC0 environment library after ``import_cc0_environment.py``.

In the pinned editor (``-ExecutePythonScript=<this file>``) it loads every
package the library declares and checks what the importer promised: texture
colour spaces, compression, DirectX normals, virtual texturing and source
hashes; lighting-only cubemaps; the weather collection; each master's exact
parameters, shading setup and collection bindings; every instance's parent,
bindings, overrides and provenance tags, with no place instance reaching an
evaluation texture; and each scanned mesh's slot, Nanite state and measured
size. ``--source-only`` runs the host part (ledger hashes, period policy,
packed ARM maps) and prints the package count the editor run must match.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cc0_environment_library as library  # noqa: E402

require = library.require


def source_check(root: Path) -> library.Plan:
    plan = library.build_plan(root)
    library.verify_packed(plan)
    return plan


def close(a, b, tolerance=1e-4):
    return abs(float(a) - float(b)) <= tolerance


def validate_textures(unreal, assets, plan, packed):
    count = 0
    for texture_set in plan.sets.values():
        if not texture_set.imported:
            continue
        for channel in texture_set.channels.values():
            texture = assets.load_asset(channel.package)
            size = (texture.blueprint_get_size_x(), texture.blueprint_get_size_y())
            for key, value in library.texture_expectations(channel, texture_set, size).items():
                if key in library.ENUM_SETTINGS:
                    value = getattr(getattr(unreal, library.ENUM_SETTINGS[key]), value)
                require(texture.get_editor_property(key) == value,
                        f"{channel.package}: {key} is {texture.get_editor_property(key)}, expected {value}")
            digest = packed[channel.file]["sha256"] if channel.root == "packed" else channel.sha256
            require(assets.get_metadata_tag(texture, "SoraSourceSha256") == digest,
                    f"{channel.package}: imported from other bytes than {channel.file}")
            require(texture.get_path_name().startswith(library.EVALUATION) == texture_set.evaluation,
                    f"{channel.package}: evaluation folder does not match the set")
            count += 1
    for record, path in plan.hdris:
        cube = assets.load_asset(path)
        require(assets.get_metadata_tag(cube, "SoraSourceSha256") == record.file("hdri")["sha256"],
                f"{path}: HDRI source changed")
        require(assets.get_metadata_tag(cube, "SoraSources") == record.key, f"{path}: HDRI provenance tag")
    return count


def validate_mpc(unreal, assets):
    mpc = assets.load_asset(library.mpc_path())
    scalars = {str(item.get_editor_property("parameter_name")): item
               for item in mpc.get_editor_property("scalar_parameters")}
    require(set(scalars) == set(library.MPC_SCALARS) and not mpc.get_editor_property("vector_parameters"),
            f"{library.MPC_NAME} parameters changed: {sorted(scalars)}")
    for name, default in library.MPC_SCALARS.items():
        require(close(scalars[name].get_editor_property("default_value"), default),
                f"{library.MPC_NAME}.{name} default changed")
    return mpc


def validate_master(unreal, assets, lib, plan, defaults, master, mpc):
    material = assets.load_asset(library.master_path(master.name))
    family = master.family
    require(assets.get_metadata_tag(material, "SoraGraphSha256")
            == library.master_graph_digest(plan, master.name, defaults[master.name]),
            f"{master.name}: built from other graph code or default maps; rerun import_cc0_environment.py")
    expected = {
        "blend_mode": unreal.BlendMode.BLEND_MASKED if family == "foliage" else unreal.BlendMode.BLEND_OPAQUE,
        "shading_model": {"foliage": unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE,
                          "cloth": unreal.MaterialShadingModel.MSM_CLOTH}.get(
                              family, unreal.MaterialShadingModel.MSM_DEFAULT_LIT),
        "two_sided": family in ("foliage", "cloth", "lantern"),
        "tangent_space_normal": family not in library.WORLD_ALIGNED_FAMILIES,
        "used_with_nanite": True,
        "used_with_instanced_static_meshes": True,
        "use_material_attributes": family == "cloth",
    }
    for key, value in expected.items():
        require(material.get_editor_property(key) == value, f"{master.name}: {key} is not {value}")
    names = {
        "scalar": lib.get_scalar_parameter_names(material), "vector": lib.get_vector_parameter_names(material),
        "switch": lib.get_static_switch_parameter_names(material),
        "texture": lib.get_texture_parameter_names(material),
    }
    for kind, wanted in library.FAMILY_PARAMETERS[family].items():
        actual = {str(name) for name in names[kind]}
        require(actual == wanted, f"{master.name}: {kind} parameters {sorted(actual ^ wanted)} differ")
    collections, customs = set(), []
    for expression in lib.get_material_expressions(material):
        if isinstance(expression, unreal.MaterialExpressionCollectionParameter):
            name = str(expression.get_editor_property("parameter_name"))
            require(expression.get_editor_property("collection") == mpc and name in library.MPC_SCALARS,
                    f"{master.name}: collection parameter {name} is not bound to {library.MPC_NAME}")
            collections.add(name)
        elif isinstance(expression, unreal.MaterialExpressionCustom):
            customs.append(str(expression.get_editor_property("description")))
    wanted = {"Wetness", "PuddleAmount"} | ({"LanternIntensity"} if family == "lantern" else set())
    require(collections == wanted, f"{master.name}: weather collection inputs {sorted(collections)}")
    require("SORA environment finish" in customs and "SORA world projection (cm)" in customs,
            f"{master.name}: shared finish/projection nodes missing: {customs}")
    if family in library.WORLD_ALIGNED_FAMILIES:
        require("SORA projected normal to world" in customs, f"{master.name}: projected normal missing")
    require(material.get_path_name() == library.master_path(master.name), f"{master.name}: path")
    return material


def validate_instance(unreal, assets, lib, plan, instance):
    path = library.instance_path(instance)
    mi = assets.load_asset(path)
    parent = mi.get_editor_property("parent")
    require(parent is not None and parent.get_path_name() == library.master_path(instance.master),
            f"{instance.name}: parent is not {instance.master}")
    for switch, value in library.resolved_switches(instance).items():
        require(lib.get_material_instance_static_switch_parameter_value(mi, switch) == value,
                f"{instance.name}: {switch} is not {value}")
    for scalar, value in instance.scalars.items():
        require(close(lib.get_material_instance_scalar_parameter_value(mi, scalar), value),
                f"{instance.name}: {scalar} is not {value}")
    for vector, value in library.resolved_vectors(plan, instance).items():
        actual = lib.get_material_instance_vector_parameter_value(mi, vector)
        require(all(close(getattr(actual, c), v) for c, v in zip("rgba", value)),
                f"{instance.name}: {vector} is not {value}")
    family = library.MASTERS[instance.master].family
    layers = plan.layers_of(instance)
    for param in library.TEXTURE_PARAMS[family]:
        layer = layers[1] if param.startswith("LayerB") else layers[0]
        expected = layer.channels[param.removeprefix("LayerB")].package
        actual = lib.get_material_instance_texture_parameter_value(mi, param)
        require(actual is not None and actual.get_path_name() == expected,
                f"{instance.name}: {param} is bound to {actual and actual.get_path_name()}, expected {expected}")
        require(instance.evaluation or not actual.get_path_name().startswith(library.EVALUATION),
                f"{instance.name}: place instance binds evaluation texture {actual.get_path_name()}")
    if instance.detail:
        actual = lib.get_material_instance_texture_parameter_value(mi, "DetailNormal")
        require(actual is not None and actual.get_path_name() == layers[0].channels["Normal"].package,
                f"{instance.name}: detail normal binding")
    overrides = mi.get_editor_property("base_property_overrides")
    require(bool(overrides.get_editor_property("override_blend_mode")) == (instance.blend_mode is not None),
            f"{instance.name}: blend-mode override state")
    if instance.blend_mode == "opaque":
        require(overrides.get_editor_property("blend_mode") == unreal.BlendMode.BLEND_OPAQUE,
                f"{instance.name}: blend-mode override value")
    for tag, value in library.metadata(plan, instance).items():
        require(assets.get_metadata_tag(mi, tag) == value, f"{instance.name}: metadata {tag} changed")
    require(path.startswith(library.EVALUATION) == instance.evaluation, f"{instance.name}: folder")
    return mi


def gltf_extents(plan, mesh, node_name):
    """Sorted |max-min| of a node's POSITION accessors, times its scale, in centimetres."""
    gltf = json.loads((plan.storage / mesh.gltf).read_text(encoding="utf-8"))
    node = next(item for item in gltf["nodes"] if item.get("name") == node_name)
    scale = node.get("scale", [1.0, 1.0, 1.0])
    low, high = [float("inf")] * 3, [float("-inf")] * 3
    for primitive in gltf["meshes"][node["mesh"]]["primitives"]:
        accessor = gltf["accessors"][primitive["attributes"]["POSITION"]]
        low = [min(a, b) for a, b in zip(low, accessor["min"])]
        high = [max(a, b) for a, b in zip(high, accessor["max"])]
    return sorted(100.0 * (h - l) * s for l, h, s in zip(low, high, scale))


def validate_meshes(unreal, assets, plan, instances):
    count = 0
    for mesh in plan.meshes:
        material = instances[mesh.instance]
        for node_name, asset_name in mesh.assets:
            path = f"{mesh.folder}/{asset_name}.{asset_name}"
            static_mesh = assets.load_asset(path)
            slots = static_mesh.get_editor_property("static_materials")
            require(len(slots) == 1 and slots[0].get_editor_property("material_interface") == material,
                    f"{path}: slot is not {mesh.instance}")
            require(bool(static_mesh.get_editor_property("nanite_settings").get_editor_property("enabled")),
                    f"{path}: Nanite is off")
            box = static_mesh.get_bounding_box()
            extents = sorted(abs(getattr(box.max, axis) - getattr(box.min, axis)) for axis in "xyz")
            wanted = gltf_extents(plan, mesh, node_name)
            require(all(abs(a - b) <= max(0.05, 0.005 * b) for a, b in zip(extents, wanted)),
                    f"{path}: size {extents} cm does not match the scan's {wanted} cm")
            require(assets.get_metadata_tag(static_mesh, "SoraSources") == mesh.record.key,
                    f"{path}: provenance tag")
            count += 1
    return count


def main():
    if "--source-only" in sys.argv:
        plan = source_check(Path(__file__).resolve().parents[2])
        print(f"SORA_CC0_SOURCE_CHECK_COMPLETE: {len(plan.expected)} expected Unreal packages")
        return
    import unreal
    from sora_engine_pin import require_running_engine

    require_running_engine("CC0 environment library validation")
    assets, lib = unreal.EditorAssetLibrary, unreal.MaterialEditingLibrary
    plan = source_check(Path(unreal.Paths.project_dir()).resolve())
    packed = library.read_packed_manifest(plan.project_root)["outputs"]
    for path, class_name in plan.expected.items():
        asset = assets.load_asset(path)
        require(asset is not None and isinstance(asset, getattr(unreal, class_name)),
                f"{path}: expected {class_name}, found {asset and asset.get_class().get_name()}")
    textures = validate_textures(unreal, assets, plan, packed)
    mpc = validate_mpc(unreal, assets)
    defaults = library.master_defaults(plan)
    masters = {name: validate_master(unreal, assets, lib, plan, defaults, master, mpc)
               for name, master in library.MASTERS.items()}
    instances = {instance.name: validate_instance(unreal, assets, lib, plan, instance)
                 for instance in plan.instances}
    meshes = validate_meshes(unreal, assets, plan, instances)
    places = sum(not instance.evaluation for instance in plan.instances)
    unreal.log(f"SORA_CC0_ENVIRONMENT_VALIDATED: {len(plan.expected)} packages loaded with expected types "
               f"({textures} textures, {len(masters)} masters, {places} place and "
               f"{len(instances) - places} evaluation instances, {meshes} meshes)")


main()
