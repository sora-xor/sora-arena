"""Import the Tsumagizaka dojo hall kit and its scan materials into the pinned editor.

Run: scripts/toolchain/run-editor-script.sh scripts/unreal/import_nyaagyu_dojo_kit.py NYAAGYU_DOJO_KIT_READY

Reads Content/SourceArt/Environment/NyaagyuDojoKit/manifest.json, checks every
module and texture hash, and imports:

* the CC0 scan sets (Poly Haven hinoki_planks, japanese_cedar_planks,
  clay_plaster, forest_ground_05) from the pinned local raw cache that
  scripts/assets/fetch_cc0.py reproduces, verified against the
  polyhaven-first-slice ledger, into /Game/Generated/Environment/DojoKit/Textures;
* M_SoraArch, a UV-tiling scan master: UV0 is in metres, TileMeters is the
  scan's measured size, and a per-instance random offset plus a low-frequency
  luminance break-up keep repeated modules from matching;
* M_SoraArchFoliage: the same, two-sided foliage, for shoji paper that the
  dawn shines through; and flat lacquer/gilt instances;
* every module (LOD0 + authored LODs) into /Game/Generated/Environment/DojoKit,
  binding slots M_Arch_<Role> to their instances. The coffer panels use
  M_SoraCraft with the kit's own design atlas.

Nanite is enabled after the conventional import is audited, with a full
explicit fallback retaining the same authored LODs on SM5. This is renderer
enablement of existing modules, not unique-beam art or runtime acceptance.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_engine_pin import require_running_engine  # noqa: E402
from cc0_environment_library import storage_root  # noqa: E402
from dojo_nanite import enable_full_fallback, prepare_conventional  # noqa: E402

require_running_engine("Nyaagyu dojo kit import")
ROOT = Path(unreal.Paths.project_dir()).resolve()
RAW_STORAGE = storage_root(ROOT)
KIT = ROOT / "Content/SourceArt/Environment/NyaagyuDojoKit"
LEDGER = ROOT / "scripts/assets/manifests/polyhaven-first-slice.json"
DEST = "/Game/Generated/Environment/DojoKit"
TEX = f"{DEST}/Textures"

tools = unreal.AssetToolsHelpers.get_asset_tools()
assets = unreal.EditorAssetLibrary
lib = unreal.MaterialEditingLibrary
meshes = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)

# Scan per role: (asset id, tint (linear multiplier), roughness scale, roughness bias, normal strength)
SCANS = {
    "hinoki_planks": "Hinoki",
    "japanese_cedar_planks": "Cedar",
    "clay_plaster": "Plaster",
    "forest_ground_05": "Ground",
}
ROLES = {
    # role: (scan, tint, rough_scale, rough_bias, macro, two_sided)
    "Hinoki": ("hinoki_planks", (0.86, 0.72, 0.55), 0.62, 0.04, 0.18, False),
    "CedarBoard": ("japanese_cedar_planks", (0.42, 0.30, 0.24), 0.95, 0.02, 0.22, False),
    "DarkTimber": ("japanese_cedar_planks", (0.16, 0.115, 0.09), 0.85, 0.06, 0.25, False),
    "RenjiBar": ("japanese_cedar_planks", (0.14, 0.10, 0.08), 0.85, 0.06, 0.15, False),
    "Kumiko": ("japanese_cedar_planks", (0.95, 0.80, 0.64), 0.90, 0.05, 0.10, False),
    "Plaster": ("clay_plaster", (0.92, 0.80, 0.66), 1.00, 0.00, 0.20, False),
    "Stone": ("forest_ground_05", (0.80, 0.80, 0.78), 1.00, 0.00, 0.25, False),
    "ShojiPaper": ("clay_plaster", (1.25, 1.18, 1.02), 0.0, 0.88, 0.05, True),
}
FLAT = {
    # role: (base colour (linear), roughness, metallic)
    "Lacquer": ((0.012, 0.010, 0.009), 0.07, 0.0),
    "Gilt": ((1.0, 0.77, 0.34), 0.30, 1.0),
    "Iron": ((0.06, 0.058, 0.055), 0.55, 1.0),
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(f"Dojo kit import: {message}")


def node(material, cls, x, y, **properties):
    expression = lib.create_material_expression(material, cls, x, y)
    for key, value in properties.items():
        expression.set_editor_property(key, value)
    return expression


def link(a, out, b, pin):
    require(lib.connect_material_expressions(a, out, b, pin), f"link {out}->{pin}")


def to(expression, out, prop):
    require(lib.connect_material_property(expression, out, prop), f"output {prop}")


def import_texture(path: Path, name: str, kind: str):
    task = unreal.AssetImportTask()
    task.filename = str(path)
    task.destination_path = TEX
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    tools.import_asset_tasks([task])
    tex = assets.load_asset(f"{TEX}/{name}")
    require(isinstance(tex, unreal.Texture2D), f"texture {path.name}")
    tex.set_editor_property("srgb", kind == "BaseColor")
    if kind == "Normal":
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property("flip_green_channel", False)
    elif kind in ("ARM", "ORM", "Mask"):
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
    tex.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_WORLD)
    assets.save_loaded_asset(tex)
    return tex


def scan_sets():
    ledger = json.loads(LEDGER.read_text())
    records = {r["asset_id"]: r for r in ledger["records"]}
    out = {}
    for asset_id, label in SCANS.items():
        rec = records[asset_id]
        require(rec["license"] == "CC0-1.0" and rec["agent_handling"] == "allowed", f"{asset_id} licence")
        files = {}
        for f in rec["files"]:
            path = RAW_STORAGE / (f.get("path") or f["file"])
            require(path.is_file(), f"missing raw scan {path} (run scripts/assets/fetch_cc0.py)")
            require(sha(path) == f["sha256"], f"{path.name} changed")
            stem = path.name
            kind = "BaseColor" if "_diff_" in stem else "Normal" if "_nor_dx_" in stem else "ARM" if "_arm_" in stem else None
            if kind:
                files[kind] = import_texture(path, f"T_{label}_{kind}", kind)
        require(set(files) == {"BaseColor", "Normal", "ARM"}, f"{asset_id} channels {set(files)}")
        out[asset_id] = (files, rec["tile_size_cm"] / 100.0)
    return out


def arch_master(name, defaults, two_sided):
    path = f"{DEST}/{name}"
    m = assets.load_asset(path) if assets.does_asset_exist(path) else tools.create_asset(
        name, DEST, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("used_with_instanced_static_meshes", True)
    for old in list(lib.get_material_expressions(m)):
        lib.delete_material_expression(m, old)
    if two_sided:
        m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
        m.set_editor_property("two_sided", True)
    # UV: metres / TileMeters + per-instance random offset.
    uv = node(m, unreal.MaterialExpressionTextureCoordinate, -1700, 0)
    tile = node(m, unreal.MaterialExpressionScalarParameter, -1700, 120, parameter_name="TileMeters", default_value=2.0)
    div = node(m, unreal.MaterialExpressionDivide, -1500, 40)
    link(uv, "", div, "A")
    link(tile, "", div, "B")
    # Per-copy random UV offset from a hash of the object (instance) position.
    # PerInstanceRandom sampled garbage UV derivatives on instanced sets under
    # Mac Metal SM5 (blocky lowest-mip texels); the position hash is the same
    # for instanced and single components.
    opos = node(m, unreal.MaterialExpressionObjectPositionWS, -1900, 260)
    hseed = node(m, unreal.MaterialExpressionConstant3Vector, -1900, 340,
                 constant=unreal.LinearColor(0.01237, 0.00711, 0.00391, 0))
    hdot = node(m, unreal.MaterialExpressionDotProduct, -1750, 280)
    link(opos, "", hdot, "A")
    link(hseed, "", hdot, "B")
    hsin = node(m, unreal.MaterialExpressionSine, -1650, 280)
    link(hdot, "", hsin, "")
    hmul = node(m, unreal.MaterialExpressionMultiply, -1560, 280)
    link(hsin, "", hmul, "A")
    hk = node(m, unreal.MaterialExpressionConstant, -1650, 360, r=43758.5453)
    link(hk, "", hmul, "B")
    rnd = node(m, unreal.MaterialExpressionFrac, -1480, 280)
    link(hmul, "", rnd, "")
    off = node(m, unreal.MaterialExpressionMultiply, -1500, 260)
    link(rnd, "", off, "A")
    seven = node(m, unreal.MaterialExpressionConstant2Vector, -1700, 360, r=0.731, g=0.377)
    link(seven, "", off, "B")
    uvf = node(m, unreal.MaterialExpressionAdd, -1300, 100)
    link(div, "", uvf, "A")
    link(off, "", uvf, "B")
    bc = node(m, unreal.MaterialExpressionTextureSampleParameter2D, -1050, -400, parameter_name="BaseColorMap",
              texture=defaults["BaseColor"])
    nm = node(m, unreal.MaterialExpressionTextureSampleParameter2D, -1050, -50, parameter_name="NormalMap",
              sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL, texture=defaults["Normal"])
    arm = node(m, unreal.MaterialExpressionTextureSampleParameter2D, -1050, 300, parameter_name="ARMMap",
               sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_MASKS, texture=defaults["ARM"])
    for t in (bc, nm, arm):
        link(uvf, "", t, "UVs")
    # Macro break-up: the same albedo 14x larger, as luminance around 1.
    macro_uv = node(m, unreal.MaterialExpressionMultiply, -1300, -600)
    link(uvf, "", macro_uv, "A")
    k = node(m, unreal.MaterialExpressionConstant, -1500, -650, r=0.071)
    link(k, "", macro_uv, "B")
    macro = node(m, unreal.MaterialExpressionTextureSampleParameter2D, -1050, -750, parameter_name="MacroMap",
                 texture=defaults["BaseColor"])
    link(macro_uv, "", macro, "UVs")
    lum = node(m, unreal.MaterialExpressionDesaturation, -800, -750)
    link(macro, "RGB", lum, "")
    macro_amt = node(m, unreal.MaterialExpressionScalarParameter, -800, -600, parameter_name="MacroAmount",
                     default_value=0.2)
    one = node(m, unreal.MaterialExpressionConstant, -800, -520, r=1.0)
    lum_x2 = node(m, unreal.MaterialExpressionMultiply, -600, -750)
    link(lum, "", lum_x2, "A")
    two = node(m, unreal.MaterialExpressionConstant, -800, -820, r=2.2)
    link(two, "", lum_x2, "B")
    macro_mix = node(m, unreal.MaterialExpressionLinearInterpolate, -420, -700)
    link(one, "", macro_mix, "A")
    link(lum_x2, "", macro_mix, "B")
    link(macro_amt, "", macro_mix, "Alpha")
    tint = node(m, unreal.MaterialExpressionVectorParameter, -800, -300, parameter_name="Tint",
                default_value=unreal.LinearColor(1, 1, 1, 1))
    bct = node(m, unreal.MaterialExpressionMultiply, -600, -400)
    link(bc, "RGB", bct, "A")
    link(tint, "RGB", bct, "B")
    base = node(m, unreal.MaterialExpressionMultiply, -250, -450)
    link(bct, "", base, "A")
    link(macro_mix, "", base, "B")
    to(base, "", unreal.MaterialProperty.MP_BASE_COLOR)
    nstr = node(m, unreal.MaterialExpressionScalarParameter, -800, 0, parameter_name="NormalStrength", default_value=1.0)
    flat = node(m, unreal.MaterialExpressionConstant3Vector, -800, 80, constant=unreal.LinearColor(0, 0, 1, 1))
    nmix = node(m, unreal.MaterialExpressionLinearInterpolate, -550, 0)
    link(flat, "", nmix, "A")
    link(nm, "RGB", nmix, "B")
    link(nstr, "", nmix, "Alpha")
    to(nmix, "", unreal.MaterialProperty.MP_NORMAL)
    ao = node(m, unreal.MaterialExpressionComponentMask, -800, 250, r=True, g=False, b=False, a=False)
    link(arm, "RGB", ao, "")
    to(ao, "", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    rough = node(m, unreal.MaterialExpressionComponentMask, -800, 350, r=False, g=True, b=False, a=False)
    link(arm, "RGB", rough, "")
    rs = node(m, unreal.MaterialExpressionScalarParameter, -800, 450, parameter_name="RoughnessScale", default_value=1.0)
    rb = node(m, unreal.MaterialExpressionScalarParameter, -800, 530, parameter_name="RoughnessBias", default_value=0.0)
    rmul = node(m, unreal.MaterialExpressionMultiply, -550, 380)
    link(rough, "", rmul, "A")
    link(rs, "", rmul, "B")
    radd = node(m, unreal.MaterialExpressionAdd, -350, 400)
    link(rmul, "", radd, "A")
    link(rb, "", radd, "B")
    rsat = node(m, unreal.MaterialExpressionSaturate, -200, 400)
    link(radd, "", rsat, "")
    to(rsat, "", unreal.MaterialProperty.MP_ROUGHNESS)
    if two_sided:
        sss = node(m, unreal.MaterialExpressionVectorParameter, -500, 650, parameter_name="TransmissionColor",
                   default_value=unreal.LinearColor(0.85, 0.72, 0.48, 1))
        to(sss, "", unreal.MaterialProperty.MP_SUBSURFACE_COLOR)
    lib.layout_material_expressions(m)
    lib.recompile_material(m)
    assets.save_loaded_asset(m)
    return m


def flat_master():
    path = f"{DEST}/M_SoraArchFlat"
    m = assets.load_asset(path) if assets.does_asset_exist(path) else tools.create_asset(
        "M_SoraArchFlat", DEST, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("used_with_instanced_static_meshes", True)
    for old in list(lib.get_material_expressions(m)):
        lib.delete_material_expression(m, old)
    col = node(m, unreal.MaterialExpressionVectorParameter, -500, -100, parameter_name="BaseColor",
               default_value=unreal.LinearColor(0.5, 0.5, 0.5, 1))
    rough = node(m, unreal.MaterialExpressionScalarParameter, -500, 100, parameter_name="Roughness", default_value=0.5)
    metal = node(m, unreal.MaterialExpressionScalarParameter, -500, 200, parameter_name="Metallic", default_value=0.0)
    to(col, "", unreal.MaterialProperty.MP_BASE_COLOR)
    to(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    to(metal, "", unreal.MaterialProperty.MP_METALLIC)
    lib.recompile_material(m)
    assets.save_loaded_asset(m)
    return m


def instance(name, parent):
    path = f"{DEST}/{name}"
    mi = assets.load_asset(path) if assets.does_asset_exist(path) else tools.create_asset(
        name, DEST, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    lib.set_material_instance_parent(mi, parent)
    return mi


def build_instances(scans):
    first = next(iter(scans.values()))[0]
    opaque = arch_master("M_SoraArch", first, False)
    foliage = arch_master("M_SoraArchFoliage", first, True)
    flat = flat_master()
    out = {}
    for role, (scan, tint, rs, rb, macro, two_sided) in ROLES.items():
        files, tile_m = scans[scan]
        mi = instance(f"MI_Arch_{role}", foliage if two_sided else opaque)
        for param, kind in (("BaseColorMap", "BaseColor"), ("NormalMap", "Normal"), ("ARMMap", "ARM"),
                            ("MacroMap", "BaseColor")):
            lib.set_material_instance_texture_parameter_value(mi, param, files[kind])
        lib.set_material_instance_scalar_parameter_value(mi, "TileMeters", tile_m)
        lib.set_material_instance_scalar_parameter_value(mi, "RoughnessScale", rs)
        lib.set_material_instance_scalar_parameter_value(mi, "RoughnessBias", rb)
        lib.set_material_instance_scalar_parameter_value(mi, "MacroAmount", macro)
        lib.set_material_instance_vector_parameter_value(mi, "Tint", unreal.LinearColor(*tint, 1))
        if two_sided:
            lib.set_material_instance_scalar_parameter_value(mi, "NormalStrength", 0.25)
        assets.save_loaded_asset(mi)
        out[f"M_Arch_{role}"] = mi
    for role, (col, rough, metal) in FLAT.items():
        mi = instance(f"MI_Arch_{role}", flat)
        lib.set_material_instance_vector_parameter_value(mi, "BaseColor", unreal.LinearColor(*col, 1))
        lib.set_material_instance_scalar_parameter_value(mi, "Roughness", rough)
        lib.set_material_instance_scalar_parameter_value(mi, "Metallic", metal)
        assets.save_loaded_asset(mi)
        out[f"M_Arch_{role}"] = mi
    return out


def coffer_instance(manifest):
    tex = manifest["notes"]["textures"]
    files = {}
    for kind, entry in tex.items():
        path = ROOT / entry["file"]
        require(path.is_file() and sha(path) == entry["sha256"], f"{path.name} changed")
        files[kind] = import_texture(path, path.stem, kind)
    craft = assets.load_asset("/Game/Generated/Environment/SoraCraft/M_SoraCraft")
    require(craft is not None, "M_SoraCraft missing: run import_sora_craft.py first")
    mi = instance("MI_Arch_CofferPanel", craft)
    flat_normal = assets.load_asset("/Engine/EngineMaterials/DefaultNormal")
    for param, value in (("BaseColorMap", files["BaseColor"]), ("ORMMap", files["ORM"]), ("MaskMap", files["Mask"]),
                         ("NormalMap", flat_normal)):
        lib.set_material_instance_texture_parameter_value(mi, param, value)
    assets.save_loaded_asset(mi)
    return mi


def fbx_options():
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_materials = False
    options.import_textures = False
    options.import_as_skeletal = False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    data = options.static_mesh_import_data
    data.combine_meshes = True
    data.generate_lightmap_u_vs = False
    data.auto_generate_collision = False
    # First observe the unmodified conventional source. Enable Nanite below
    # only after explicit full-fallback settings and preservation checks.
    data.set_editor_property("build_nanite", False)
    return options


def import_module(module, instances):
    name = module["asset"]
    lods = module["lods"]
    for lod in lods:
        path = ROOT / lod["file"]
        require(path.is_file() and sha(path) == lod["sha256"], f"{name}: {lod['file']} changed")
    path = f"{DEST}/{name}"
    if assets.does_asset_exist(path):
        existing = assets.load_asset(path)
        require(isinstance(existing, unreal.StaticMesh), f"{name}: existing asset is not a static mesh")
        prepare_conventional(existing, meshes)
    task = unreal.AssetImportTask()
    task.filename = str(ROOT / lods[0]["file"])
    task.destination_path = DEST
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    task.options = fbx_options()
    tools.import_asset_tasks([task])
    mesh = assets.load_asset(f"{DEST}/{name}")
    require(isinstance(mesh, unreal.StaticMesh), f"{name}: import failed")
    prepare_conventional(mesh, meshes)
    for index, lod in enumerate(lods[1:], start=1):
        require(meshes.import_lod(mesh, index, str(ROOT / lod["file"])) == index, f"{name}: LOD{index}")
    # Authored LODs switch late; a one-LOD module keeps LOD0 everywhere (and
    # drops any LODs an earlier import of the same asset left behind).
    if len(lods) == 1 and meshes.get_lod_count(mesh) > 1:
        meshes.remove_lods(mesh)
    if len(lods) > 1:
        meshes.set_lod_screen_sizes(mesh, [1.0, 0.25, 0.08][:len(lods)])
    slots = [str(s.material_slot_name) for s in mesh.get_editor_property("static_materials")]
    for i, slot in enumerate(slots):
        require(slot in instances, f"{name}: unknown slot {slot}")
        mesh.set_material(i, instances[slot])
        parent = mesh.get_material(i).get_base_material()
        require(parent is not None and bool(parent.get_editor_property("used_with_instanced_static_meshes")),
                f"{name}: {slot} lacks the instanced-static-mesh material permutation")
        # Only add the required permutation. Preserve graph, blend, shading,
        # sidedness, textures and actual material-slot order (including craft).
        if not lib.has_material_usage(parent, unreal.MaterialUsage.MATUSAGE_NANITE):
            # SetBaseMaterialUsage itself recompiles when the flag changes.
            lib.set_base_material_usage(parent, unreal.MaterialUsage.MATUSAGE_NANITE, True)
            require(assets.save_loaded_asset(parent), f"{name}: could not save Nanite material usage")
    # Distance fields stand in for this geometry in software Lumen: thin
    # members need a finer field than the default.
    mesh.set_editor_property("distance_field_self_shadow_bias", 0.5)
    # The helper saves both baselines, restores source LOD thresholds after
    # the Nanite build, then audits final saved geometry before success.
    audit = enable_full_fallback(mesh, module, meshes, unreal, lib, assets)
    unreal.log("SORA_DOJO_NANITE_IMPORT " + json.dumps(audit, sort_keys=True))
    return name, slots


def main():
    manifest = json.loads((KIT / "manifest.json").read_text())
    require(manifest["generator_sha256"] == sha(ROOT / manifest["generator"]), "generator changed since the build")
    assets.make_directory(TEX)
    scans = scan_sets()
    instances = build_instances(scans)
    instances["M_Arch_CofferPanel"] = coffer_instance(manifest)
    done = []
    for module in manifest["modules"]:
        name, slots = import_module(module, instances)
        done.append(f"{name}[{len(slots)}]")
    assets.save_directory(DEST, only_if_is_dirty=False, recursive=True)
    unreal.log(f"NYAAGYU_DOJO_KIT_READY: {len(done)} modules: {', '.join(done)}")


main()
