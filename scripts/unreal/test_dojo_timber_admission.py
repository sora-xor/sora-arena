"""Regression tests for the dojo timber importer's host-side admission checks.

Run: python3 -m unittest scripts/unreal/test_dojo_timber_admission.py

No Unreal: dojo_timber_admission.py is the pure part of
scripts/unreal/import_nyaagyu_dojo_timbers.py.
"""
from __future__ import annotations

import hashlib
import ast
import json
import sys
import tempfile
import unittest
import time
from types import SimpleNamespace
from unittest.mock import Mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dojo_timber_admission as A  # noqa: E402

KEY = "Local/ArtCache/NyaagyuDojoTimbers/Unique/SM_DojoTimberColumn_8000_m1300_11600_1300_S0_B00.fbx"
POOL_KEY = "Content/SourceArt/Environment/NyaagyuDojoTimbers/FBX/SM_DojoTimberColumn_MAC_Wall_00.fbx"
MANIFESTS = ["Content/SourceArt/Environment/NyaagyuDojoTimbers/manifest.json",
             "Content/SourceArt/Environment/NyaagyuDojoTimbers/Rails/manifest.json"]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


class CacheEvidence(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.root, self.moved = base / "project", base / "elsewhere"
        self.root.mkdir()
        self.data = b"dense log"
        self.evidence = {"fbx": {KEY: {"digest": "g1", "sha256": digest(self.data)},
                                 POOL_KEY: {"digest": "g2", "sha256": digest(b"pool")}}}

    def tearDown(self):
        self.tmp.cleanup()

    def test_default_cache_is_the_projects(self):
        cache = A.cache_root(self.root, {})
        self.assertEqual(cache, self.root / "Local/ArtCache")
        write(self.root / KEY, self.data)
        self.assertEqual(A.check_evidence(self.root, cache, KEY, "g1", self.evidence, "col"), self.root / KEY)

    def test_moved_cache_governs_the_dense_fbx(self):
        # The reproduction: evidence and FBX live only in the moved cache, keyed canonically.
        cache = A.cache_root(self.root, {"SORA_ART_CACHE": str(self.moved)})
        moved_file = write(self.moved / KEY.removeprefix("Local/ArtCache/"), self.data)
        self.assertEqual(A.check_evidence(self.root, cache, KEY, "g1", self.evidence, "col"), moved_file)

    def test_moved_cache_never_falls_back_to_the_project_copy(self):
        cache = A.cache_root(self.root, {"SORA_ART_CACHE": str(self.moved)})
        write(self.root / KEY, self.data)
        with self.assertRaisesRegex(A.AdmissionError, "missing"):
            A.check_evidence(self.root, cache, KEY, "g1", self.evidence, "col")

    def test_committed_keys_stay_in_the_project(self):
        cache = A.cache_root(self.root, {"SORA_ART_CACHE": str(self.moved)})
        pool = write(self.root / POOL_KEY, b"pool")
        self.assertEqual(A.check_evidence(self.root, cache, POOL_KEY, "g2", self.evidence, "pool"), pool)

    def test_rejections(self):
        cache = A.cache_root(self.root, {"SORA_ART_CACHE": str(self.moved)})
        target = write(self.moved / KEY.removeprefix("Local/ArtCache/"), self.data)
        with self.assertRaisesRegex(A.AdmissionError, "digest differs"):
            A.check_evidence(self.root, cache, KEY, "other", self.evidence, "col")
        with self.assertRaisesRegex(A.AdmissionError, "no rebuild evidence"):
            A.check_evidence(self.root, cache, KEY, "g1", {"fbx": {}}, "col")
        target.write_bytes(b"edited")
        with self.assertRaisesRegex(A.AdmissionError, "not the file"):
            A.check_evidence(self.root, cache, KEY, "g1", self.evidence, "col")


class Binding(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        files = {"scripts/art/bind_dojo_timbers.py": b"binder", MANIFESTS[0]: b"columns", MANIFESTS[1]: b"rails",
                 "Content/Data/campaign/chapter_01.json": b"{}", "Content/Data/campaign/chapter_02.json": b"[]"}
        for rel, data in files.items():
            write(self.root / rel, data)
        self.binding = {
            "schema": A.BINDING_SCHEMA,
            "binder": "scripts/art/bind_dojo_timbers.py", "binder_sha256": digest(b"binder"),
            "manifests": {MANIFESTS[0]: digest(b"columns"), MANIFESTS[1]: digest(b"rails")},
            "campaign": {"Content/Data/campaign/chapter_01.json": digest(b"{}"),
                         "Content/Data/campaign/chapter_02.json": digest(b"[]")},
        }

    def tearDown(self):
        self.tmp.cleanup()

    def check(self, binding=None):
        return A.check_binding(self.root, json.loads(json.dumps(binding or self.binding)), MANIFESTS)

    def test_current_binding_passes(self):
        self.assertEqual(self.check()["schema"], A.BINDING_SCHEMA)

    def test_changed_chapter_rejects(self):
        write(self.root / "Content/Data/campaign/chapter_02.json", b'["moved hall"]')
        with self.assertRaisesRegex(A.AdmissionError, "chapter_02.json changed"):
            self.check()

    def test_added_and_missing_chapters_reject(self):
        write(self.root / "Content/Data/campaign/chapter_03.json", b"{}")
        with self.assertRaisesRegex(A.AdmissionError, "not the ones bound"):
            self.check()
        (self.root / "Content/Data/campaign/chapter_03.json").unlink()
        (self.root / "Content/Data/campaign/chapter_02.json").unlink()
        with self.assertRaisesRegex(A.AdmissionError, "not the ones bound"):
            self.check()

    def test_changed_manifest_binder_or_schema_rejects(self):
        write(self.root / MANIFESTS[1], b"rails, rebuilt")
        with self.assertRaisesRegex(A.AdmissionError, "Rails/manifest.json changed"):
            self.check()
        write(self.root / MANIFESTS[1], b"rails")
        write(self.root / "scripts/art/bind_dojo_timbers.py", b"binder, edited")
        with self.assertRaisesRegex(A.AdmissionError, "binder changed"):
            self.check()
        with self.assertRaisesRegex(A.AdmissionError, "schema"):
            self.check({**self.binding, "schema": "v0"})

    def test_other_manifests_reject(self):
        with self.assertRaisesRegex(A.AdmissionError, "other manifests"):
            self.check({**self.binding, "manifests": {MANIFESTS[0]: digest(b"columns")}})


class Probe(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.manifests = {MANIFESTS[0]: {"pool": [{"asset": "ColumnPool"}], "placements": [{"asset": "Column"}]},
                          MANIFESTS[1]: {"pool": [{"asset": "RailPool"}], "placements": [{"asset": "Rail"}]}}
        for rel, value in self.manifests.items():
            write(self.root / rel, json.dumps(value).encode())
        self.binding_path = self.root / "Content/SourceArt/Environment/NyaagyuDojoTimbers/campaign_binding.json"
        write(self.binding_path, b"binding")
        self.spec = {"schema": A.PROBE_SCHEMA, "base_source_commit": "a" * 40,
                     "manifest_sha256": {rel: A.sha(self.root / rel) for rel in self.manifests},
                     "binding_sha256": A.sha(self.binding_path), "assets": ["Column", "RailPool"]}

    def check(self, spec=None):
        return A.check_probe(self.root, self.spec if spec is None else spec, self.manifests)

    def test_explicit_selection(self):
        self.assertEqual(self.check(), {"Column", "RailPool"})

    def test_empty_unknown_duplicate_or_nonlist_selection_rejects(self):
        for names in ([], ["missing"], ["Column", "Column"], "Column", [1], [""], ["Column*"]):
            with self.subTest(names=names), self.assertRaises(A.AdmissionError):
                self.check({**self.spec, "assets": names})

    def test_schema_and_destination_injection_reject(self):
        for spec in ({**self.spec, "schema": "old"}, {**self.spec, "destination": "/Game/Generated/Environment/DojoTimbers"},
                     {**self.spec, "base_source_commit": "6e951e5"}, None, [], {}):
            with self.subTest(spec=spec), self.assertRaises(A.AdmissionError):
                A.check_probe(self.root, spec, self.manifests)

    def test_stale_source_binding_and_manifest_set_reject(self):
        with self.assertRaisesRegex(A.AdmissionError, "other manifests"):
            self.check({**self.spec, "manifest_sha256": {}})
        with self.assertRaisesRegex(A.AdmissionError, "manifest changed"):
            self.check({**self.spec, "manifest_sha256": {rel: "0" * 64 for rel in self.manifests}})
        write(self.binding_path, b"new binding")
        with self.assertRaisesRegex(A.AdmissionError, "binding changed"):
            self.check()

    def test_duplicate_manifest_names_reject(self):
        self.manifests[MANIFESTS[1]]["pool"][0]["asset"] = "Column"
        with self.assertRaisesRegex(A.AdmissionError, "duplicate asset in probe manifests"):
            self.check()

    def test_selection_cannot_expand_to_bulk(self):
        names = [f"Column{i}" for i in range(17)]
        self.manifests[MANIFESTS[0]]["placements"] = [{"asset": name} for name in names]
        with self.assertRaisesRegex(A.AdmissionError, "limited to 16"):
            self.check({**self.spec, "assets": names})

    def importer_functions(self):
        # Execute real boundary functions with editor fakes; never load Unreal.
        path = Path(__file__).with_name("import_nyaagyu_dojo_timbers.py")
        parsed = ast.parse(path.read_text())
        functions = [node for node in parsed.body if isinstance(node, ast.FunctionDef)]
        ns = {"__file__": str(path), "Path": Path, "json": json, "time": time, "hashlib": hashlib,
              "admission": A, "ROOT": self.root, "KIT": self.root / "kit", "CACHE": self.root / "cache",
              "DEST": "/Game/Generated/Environment/DojoTimbers", "PROBE_REPORT": None,
              "unreal": SimpleNamespace(log=Mock()), "assets": Mock()}
        exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), "exec"), ns)
        ns["load_kit"] = lambda folder, cache: (self.manifests[MANIFESTS[1] if folder.name == "Rails" else MANIFESTS[0]], {})
        ns["load_binding"] = Mock(return_value={})
        ns["create_materials"] = Mock(side_effect=AssertionError("asset write reached"))
        return ns

    def test_bad_selection_rejected_before_editor_mutation(self):
        ns = self.importer_functions()
        spec_path = write(self.root / "probe.json", json.dumps({**self.spec, "assets": ["unknown"]}).encode())
        with self.assertRaisesRegex(A.AdmissionError, "unknown probe assets"):
            ns["run_probe"](spec_path)
        self.assertEqual(ns["assets"].mock_calls, [])
        ns["create_materials"].assert_not_called()
        self.assertEqual(ns["DEST"], "/Game/Generated/Environment/DojoTimbers")
        report = json.loads(next((self.root / "Saved").rglob("report.json")).read_text())
        self.assertEqual(report["status"], "failed")
        self.assertIn("unknown probe assets", report["error"])

    def test_existing_probe_registry_or_disk_blocks_all_writes(self):
        for disk in (False, True):
            with self.subTest(disk=disk):
                ns = self.importer_functions()
                ns["assets"].does_directory_exist.return_value = not disk
                ns["assets"].list_assets.return_value = [] if disk else [A.PROBE_DEST + "/old"]
                if disk:
                    write(self.root / "Content/Generated/Qualification/DojoTimberProbe/old.uasset", b"old")
                spec_path = write(self.root / "probe.json", json.dumps(self.spec).encode())
                with self.assertRaisesRegex(RuntimeError, "destination is occupied"):
                    ns["run_probe"](spec_path)
                ns["create_materials"].assert_not_called()
                self.assertEqual(len(ns["assets"].mock_calls), 1 if disk else 2)

    def test_absent_namespace_skips_enumeration_and_reaches_source_preflight(self):
        ns = self.importer_functions()
        ns["assets"].does_directory_exist.return_value = False
        for manifest in self.manifests.values():
            for group in ("pool", "placements"):
                for rec in manifest[group]:
                    rec.update({"cache_fbx": "dense.fbx", "fallback_fbx": "pool.fbx", "digest": "x"})
        ns["verified"] = Mock(side_effect=RuntimeError("missing source at preflight"))
        spec_path = write(self.root / "probe.json", json.dumps(self.spec).encode())
        with self.assertRaisesRegex(RuntimeError, "missing source at preflight"):
            ns["run_probe"](spec_path)
        ns["assets"].list_assets.assert_not_called()
        ns["verified"].assert_called_once()
        ns["create_materials"].assert_not_called()

    def test_bad_slot_stops_before_material_assignment(self):
        ns = self.importer_functions()
        class Mesh:
            def get_editor_property(self, prop):
                return [SimpleNamespace(get_editor_property=lambda prop: "WrongSlot")]
        ns["unreal"] = SimpleNamespace(AssetImportTask=SimpleNamespace, StaticMesh=Mesh)
        ns["tools"] = SimpleNamespace(import_asset_tasks=Mock())
        ns["assets"].load_asset.return_value = Mesh()
        ns["fbx_options"] = Mock(return_value=None)
        ns["verified"] = Mock(return_value=self.root / "mesh.fbx")
        ns["instance"] = Mock(side_effect=AssertionError("MI assignment reached"))
        ns["PROBE_REPORT"] = {"assets": [{}]}
        with self.assertRaisesRegex(A.AdmissionError, "one M_Timber"):
            ns["import_placement"]({"asset": "Column", "cache_fbx": "mesh.fbx", "digest": "x"}, None, {})
        ns["instance"].assert_not_called()
        self.assertEqual(ns["PROBE_REPORT"]["assets"][0]["slot_names"], ["WrongSlot"])

    def test_slot_count_and_name(self):
        A.check_slots(["M_Timber"])
        for names in ([], ["M_Timber", "M_Timber"], ["Other"], ["M_Timber", "Other"]):
            with self.subTest(names=names), self.assertRaises(A.AdmissionError):
                A.check_slots(names)

    def readback_fixture(self, resource_triangles=120, uv_channels=4):
        ns = self.importer_functions()
        values = {"enabled": True, "fallback_target": "relative", "fallback_relative_error": 1.0}
        build = {"use_full_precision_u_vs": True, "remove_degenerates": False, "generate_lightmap_u_vs": False,
                 "recompute_normals": False, "recompute_tangents": True, "use_mikk_t_space": True}
        ns["unreal"] = SimpleNamespace(NaniteFallbackTarget=SimpleNamespace(RELATIVE_ERROR="relative"))
        ns["meshes"] = SimpleNamespace(get_lod_build_settings=lambda mesh, lod: SimpleNamespace(get_editor_property=build.__getitem__),
                                       get_lod_count=lambda mesh: 1, get_lod_material_slot=lambda *args: 0)
        mesh = SimpleNamespace(get_editor_property=lambda key: SimpleNamespace(get_editor_property=values.__getitem__),
                               get_num_triangles=lambda lod: 40, get_num_vertices=lambda lod: 80,
                               get_num_tex_coords=lambda lod: uv_channels, get_num_sections=lambda lod: 1,
                               get_num_nanite_triangles=lambda: resource_triangles, get_num_nanite_vertices=lambda: 100,
                               get_material=lambda slot: SimpleNamespace(get_path_name=lambda: ns["DEST"] + "/MI_Column.MI_Column"))
        ns["PROBE_REPORT"] = {"assets": [{"manifest_source_triangles": 120}]}
        return ns, mesh

    def test_readback_keeps_source_fallback_and_nanite_counts_separate(self):
        ns, mesh = self.readback_fixture()
        ns["probe_readback"](mesh, {"asset": "Column", "triangles": 120}, True)
        row = ns["PROBE_REPORT"]["assets"][0]
        self.assertEqual((row["manifest_source_triangles"], row["actual_lod0_triangles"], row["nanite_triangles"]),
                         (120, 40, 120))

    def test_enabled_without_resources_or_wrong_count_rejects_and_records(self):
        for triangles, message in ((0, "no built Nanite resources"), (121, "input triangle count differs")):
            with self.subTest(triangles=triangles):
                ns, mesh = self.readback_fixture(resource_triangles=triangles)
                with self.assertRaisesRegex(RuntimeError, message):
                    ns["probe_readback"](mesh, {"asset": "Column", "triangles": 120}, True)
                row = ns["PROBE_REPORT"]["assets"][0]
                self.assertTrue(row["nanite_enabled"])
                self.assertEqual(row["nanite_triangles"], triangles)

    def test_missing_log_uv_channel_rejects(self):
        ns, mesh = self.readback_fixture(uv_channels=3)
        with self.assertRaisesRegex(RuntimeError, "four timber UV channels"):
            ns["probe_readback"](mesh, {"asset": "Column", "triangles": 120}, True)

    def test_production_does_not_run_probe_resource_checks(self):
        ns = self.importer_functions()
        mesh = Mock()
        ns["probe_readback"](mesh, {}, True)
        self.assertEqual(mesh.mock_calls, [])


class TimberMaterialInputs(unittest.TestCase):
    """Exercise both real graph builders with UE's hidden root pins absent."""
    def graph(self, missing_pin=None, reject_pin=None, reject_output=False):
        class Node:
            def __init__(self, kind):
                self.kind, self.props, self.inputs = kind, {}, {}
            def set_editor_property(self, key, value):
                self.props[key] = value
            def get_name(self):
                return self.kind
            def get_editor_property(self, key):
                return self.props[key]
        class PublicUnreal(SimpleNamespace):
            def __getattr__(self, name):
                if name.startswith("MaterialExpression"):
                    return name
                raise AttributeError(name)
        class CustomInput:
            def __init__(self):
                self.props = {}
            def set_editor_property(self, key, value):
                self.props[key] = value
        unreal = PublicUnreal(
            MaterialProperty=SimpleNamespace(MP_BASE_COLOR="BaseColor", MP_ROUGHNESS="Roughness",
                                             MP_NORMAL="Normal", MP_MATERIAL_ATTRIBUTES="Attributes"),
            MaterialShadingModel=SimpleNamespace(MSM_CLEAR_COAT="ClearCoat"),
            MaterialSamplerType=SimpleNamespace(SAMPLERTYPE_LINEAR_COLOR="linear", SAMPLERTYPE_LINEAR_GRAYSCALE="linear_grayscale",
                                                SAMPLERTYPE_MASKS="masks", SAMPLERTYPE_NORMAL="normal"),
            MaterialVectorCoordTransformSource=SimpleNamespace(TRANSFORMSOURCE_TANGENT="tangent"),
            MaterialVectorCoordTransform=SimpleNamespace(TRANSFORM_WORLD="world"),
            WorldPositionIncludedOffsets=SimpleNamespace(WPT_CAMERA_RELATIVE_NO_OFFSETS="camera_relative"),
            CustomMaterialOutputType=SimpleNamespace(CMOT_FLOAT3="float3"),
            CustomInput=CustomInput, LinearColor=lambda *args: args)
        material, nodes, outputs = Node("material"), [], []
        def create(material, kind, x, y):
            node = Node(kind); nodes.append(node); return node
        def connect(source, output, target, pin):
            if target.kind == "MaterialExpressionMakeMaterialAttributes" and pin == reject_pin:
                return False
            target.inputs[pin] = (source, output)
            return True
        def root(source, output, prop):
            outputs.append((source, output, prop))
            return not reject_output
        pins = {"BaseColor", "Roughness", "ClearCoat", "ClearCoatRoughness", "Normal"} - {missing_pin}
        lib = SimpleNamespace(create_material_expression=create, get_material_expressions=lambda m: [],
                              get_material_expression_input_names=lambda n: pins,
                              connect_material_expressions=connect, connect_material_property=root,
                              layout_material_expressions=Mock(), recompile_material=Mock())
        assets = SimpleNamespace(does_asset_exist=lambda path: True, load_asset=lambda path: material, save_loaded_asset=Mock())
        path = Path(__file__).with_name("import_nyaagyu_dojo_timbers.py")
        parsed = ast.parse(path.read_text())
        selected = [n for n in parsed.body if isinstance(n, (ast.ClassDef, ast.FunctionDef)) and n.name in ("Graph", "require", "timber_master", "import_texture", "create_materials")]
        ns = {"unreal": unreal, "lib": lib, "assets": assets, "DEST": A.PROBE_DEST, "BUMP_HLSL": "unchanged source shader"}
        exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), "exec"), ns)
        shared = {key: Node(key) for key in ("Fibre", "RingNoise", "RingRandom", "DefaultNormal", "DefaultMasks")}
        return ns, shared, material, nodes, outputs, assets

    def test_both_masters_keep_all_five_outputs_and_clearcoat_controls(self):
        for fallback in (False, True):
            with self.subTest(fallback=fallback):
                ns, shared, material, nodes, outputs, assets = self.graph()
                ns["timber_master"]("M_SoraTimber", shared, fallback)
                attributes = next(n for n in nodes if n.kind == "MaterialExpressionMakeMaterialAttributes")
                self.assertEqual(set(attributes.inputs), {"BaseColor", "Roughness", "ClearCoat", "ClearCoatRoughness", "Normal"})
                self.assertEqual(outputs, [(attributes, "", "Attributes")])
                self.assertTrue(material.props["use_material_attributes"])
                self.assertEqual(material.props["shading_model"], "ClearCoat")
                self.assertFalse(material.props["tangent_space_normal"])
                self.assertTrue(material.props["used_with_nanite"])
                coat = attributes.inputs["ClearCoat"][0]
                self.assertEqual((coat.props["parameter_name"], coat.props["default_value"]), ("ClearCoat", 1.0))
                self.assertEqual(attributes.inputs["ClearCoatRoughness"][0].kind, "MaterialExpressionSaturate")
                params = {n.props["parameter_name"]: n for n in nodes if "parameter_name" in n.props}
                self.assertEqual(params["ClearCoatRoughness"].props["default_value"], 0.17)
                normal = attributes.inputs["Normal"][0]
                self.assertEqual(normal.kind, "MaterialExpressionCustom")
                self.assertEqual([item.props["input_name"] for item in normal.props["inputs"]], ["P", "H", "N"])
                self.assertEqual(set(normal.inputs), {"P", "H", "N"})
                self.assertEqual("NormalMap" in params, fallback)
                self.assertEqual("MasksMap" in params, fallback)
                assets.save_loaded_asset.assert_called_once_with(material)

    def test_real_texture_import_settings_match_every_master_sampler(self):
        # Execute create_materials/import_texture as well as both real graph
        # builders. UE's sampler contract depends on texture compression/SRGB,
        # not merely the graph's declared sampler enum. This is CPU validation,
        # not shader compilation or a material rendering test.
        ns, shared, material, nodes, _, assets = self.graph()
        unreal = ns["unreal"]
        unreal.AssetImportTask = SimpleNamespace
        unreal.Texture2D = type(shared["Fibre"])
        unreal.TextureCompressionSettings = SimpleNamespace(
            TC_NORMALMAP="normal", TC_MASKS="masks", TC_GRAYSCALE="grayscale")
        unreal.TextureMipGenSettings = SimpleNamespace(TMGS_NO_MIPMAPS="no_mips")
        unreal.TextureFilter = SimpleNamespace(TF_BILINEAR="bilinear", TF_NEAREST="nearest")
        unreal.TextureGroup = SimpleNamespace(TEXTUREGROUP_WORLD="world")
        shared["DefaultNormal"].props.update(compression_settings="normal", srgb=False)
        black = type(material)("Black")
        black.props.update(compression_settings="default", srgb=True)
        imported = {}
        def import_tasks(tasks):
            for task in tasks:
                imported[task.destination_path + "/" + task.destination_name] = type(material)(task.destination_name)
        def load(path):
            if path.endswith("/DefaultNormal"):
                return shared["DefaultNormal"]
            if path.endswith("/Black"):
                return black
            return imported.get(path, material)
        assets.load_asset = load
        assets.make_directory = Mock()
        ns["tools"] = SimpleNamespace(import_asset_tasks=import_tasks)
        ns["TEX"] = A.PROBE_DEST + "/Textures"
        ns["sha"] = lambda path: digest(path.read_bytes())
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ns["ROOT"] = root
            manifest = {"shared_textures": {}}
            actual = json.loads((Path(__file__).resolve().parents[2] /
                "Content/SourceArt/Environment/NyaagyuDojoTimbers/manifest.json").read_text())
            for kind, entry in actual["shared_textures"].items():
                path = write(root / (kind + ".png"), b"CPU fixture; no texture decoding")
                manifest["shared_textures"][kind] = {"file": path.name,
                    "sha256": digest(path.read_bytes()), "kind": entry["kind"]}
            ns["create_materials"](manifest)
        samples = [n for n in nodes if "sampler_type" in n.props]
        self.assertEqual(len(samples), 10)  # four shared per master + two baked
        for node in samples:
            texture = node.props["texture"]
            compression, srgb = texture.props["compression_settings"], texture.props["srgb"]
            expected = {"normal": "normal", "masks": "masks",
                        "grayscale": "grayscale" if srgb else "linear_grayscale",
                        "default": "color" if srgb else "linear"}[compression]
            with self.subTest(texture=texture.kind, parameter=node.props.get("parameter_name")):
                self.assertEqual(node.props["sampler_type"], expected)
                self.assertFalse(srgb)
        default = next(n.props["texture"] for n in samples if n.props.get("parameter_name") == "MasksMap")
        self.assertIs(default, imported[ns["TEX"] + "/Fibre"])
        self.assertEqual(len(imported), 3)  # default adds no package/input
        self.assertEqual(imported[ns["TEX"] + "/RingNoise"].props["filter"], "bilinear")
        self.assertEqual(imported[ns["TEX"] + "/RingRandom"].props["filter"], "nearest")

    def test_vertex_and_baked_masks_preserve_all_four_channel_values(self):
        # UE5.8 MaterialExpressions.cpp declares RGB as output zero on both
        # nodes; MaterialEditingLibrary resolves named R/G/B/A to scalars.
        # Model those output widths so alpha-from-default-RGB cannot pass.
        rgba = (0.13, 0.27, 0.59, 0.83)
        for fallback in (False, True):
            ns, shared, _, nodes, _, _ = self.graph()
            ns["timber_master"]("M_SoraTimber", shared, fallback)
            source = next(n for n in nodes if
                (n.props.get("parameter_name") == "MasksMap" if fallback else
                 n.kind == "MaterialExpressionVertexColor"))
            masks = [n for n in nodes if n.kind == "MaterialExpressionComponentMask"
                     and n.inputs[""][0] is source]
            self.assertEqual(len(masks), 4)
            values = []
            for node in masks:
                output = node.inputs[""][1]
                outputs = {"": rgba[:3], "RGB": rgba[:3],
                           **{c: (v,) for c, v in zip("RGBA", rgba)}}
                if fallback:
                    outputs["RGBA"] = rgba  # VertexColor has no RGBA output
                self.assertIn(output, outputs)
                available = outputs[output]
                selected = [i for i, c in enumerate("rgba") if node.props[c]]
                self.assertTrue(all(i < len(available) for i in selected),
                                f"{source.kind}.{output or 'default RGB'} cannot supply {selected}")
                self.assertEqual(len(selected), 1)
                values.append(available[selected[0]])
            self.assertEqual(tuple(values), rgba)

    def test_missing_clearcoat_attribute_rejects_before_save(self):
        ns, shared, _, _, _, assets = self.graph(missing_pin="ClearCoat")
        with self.assertRaisesRegex(RuntimeError, "required timber material attributes"):
            ns["timber_master"]("M_SoraTimber", shared, True)
        assets.save_loaded_asset.assert_not_called()

    def test_rejected_attribute_links_do_not_silently_weaken_material(self):
        for pin in ("ClearCoat", "ClearCoatRoughness", "Normal"):
            with self.subTest(pin=pin):
                ns, shared, _, _, _, assets = self.graph(reject_pin=pin)
                with self.assertRaisesRegex(RuntimeError, "link"):
                    ns["timber_master"]("M_SoraTimber", shared, True)
                assets.save_loaded_asset.assert_not_called()

    def test_failed_material_attributes_root_rejects_before_save(self):
        ns, shared, _, _, _, assets = self.graph(reject_output=True)
        with self.assertRaisesRegex(RuntimeError, "material attributes output failed"):
            ns["timber_master"]("M_SoraTimber", shared, False)
        assets.save_loaded_asset.assert_not_called()


if __name__ == "__main__":
    unittest.main()
