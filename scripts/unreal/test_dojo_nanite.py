"""CPU contract tests with explicit fake editor objects; no engine execution."""
import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace as NS
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("dojo_nanite", HERE / "dojo_nanite.py")
D = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(D)
U = NS(NaniteGenerateFallback=NS(ENABLED="Enabled"), NaniteFallbackTarget=NS(PERCENT_TRIANGLES="PercentTriangles"),
       MaterialDomain=NS(MD_SURFACE="Surface"), BlendMode=NS(BLEND_OPAQUE="Opaque", BLEND_MASKED="Masked"),
       MaterialShadingModel=NS(MSM_DEFAULT_LIT="DefaultLit", MSM_TWO_SIDED_FOLIAGE="TwoSidedFoliage"),
       MaterialUsage=NS(MATUSAGE_INSTANCED_STATIC_MESHES="Instanced", MATUSAGE_NANITE="Nanite"))


class Settings:
    def __init__(self):
        self.values = dict(enabled=False, generate_fallback="PlatformDefault", fallback_target="Auto",
                           fallback_percent_triangles=.25, fallback_relative_error=1., keep_percent_triangles=.5, trim_relative_error=.1)
    def get_editor_property(self, name): return self.values[name]
    def set_editor_property(self, name, value): self.values[name] = value


class Material:
    def __init__(self, name, foliage=False):
        self.name = name
        self.props = dict(material_domain="Surface", blend_mode="Opaque", shading_model="TwoSidedFoliage" if foliage else "DefaultLit", two_sided=foliage)
        self.overrides = NS(override_blend_mode=False, blend_mode="Translucent", override_shading_model=False, shading_model="Water", override_two_sided=False, two_sided=False)
        self.usages = {"Instanced", "Nanite"}
    def get_base_material(self): return self
    def get_editor_property(self, name): return self.overrides if name == "base_property_overrides" else self.props[name]
    def get_path_name(self): return "/Game/Generated/Environment/DojoKit/" + self.name


class Mesh:
    def __init__(self):
        self.settings = Settings()
        self.lods = [[704, 1000, 1, [0, 1]], [352, 500, 1, [0, 1]], [176, 250, 1, [0, 1]]]
        self.names = ["M_Timber", "M_Paper"]
        self.materials = [Material("MI_Timber"), Material("MI_Paper", True)]
        self.screens = [1., .25, .08]
        self.bounds = NS(origin=NS(x=0,y=0,z=350), box_extent=NS(x=90,y=20,z=350))
        self.simple = 0; self.complexity = "Default"; self.collision = False; self.shadow = True
        self.nanite_triangles = 704; self.nanite_vertices = 1000
    def get_editor_property(self, name):
        assert name == "static_materials"
        return [NS(material_slot_name=n) for n in self.names]
    def get_bounds(self): return self.bounds
    def get_num_triangles(self, lod): return self.lods[lod][0]
    def get_num_vertices(self, lod): return self.lods[lod][1]
    def get_num_tex_coords(self, lod): return self.lods[lod][2]
    def get_num_sections(self, lod): return len(self.lods[lod][3])
    def get_material(self, index): return self.materials[index]
    def get_num_nanite_triangles(self): return self.nanite_triangles if self.settings.values["enabled"] else 0
    def get_num_nanite_vertices(self): return self.nanite_vertices if self.settings.values["enabled"] else 0


class Editor:
    def __init__(self, changed=None): self.changed = changed; self.applied = 0
    def get_lod_count(self, mesh): return len(mesh.lods)
    def get_lod_screen_sizes(self, mesh): return mesh.screens
    def get_lod_material_slot(self, mesh, lod, section): return mesh.lods[lod][3][section]
    def is_section_collision_enabled(self, mesh, lod, section): return mesh.collision
    def is_section_cast_shadow_enabled(self, mesh, lod, section): return mesh.shadow
    def get_simple_collision_count(self, mesh): return mesh.simple
    def get_collision_complexity(self, mesh): return mesh.complexity
    def get_nanite_settings(self, mesh): return copy.deepcopy(mesh.settings)
    def set_nanite_settings(self, mesh, settings, apply):
        assert apply is True
        mesh.settings = copy.deepcopy(settings); self.applied += 1
        if self.changed: self.changed(mesh)


class DojoNaniteTests(unittest.TestCase):
    def setUp(self):
        self.mesh = Mesh(); self.editor = Editor()
        self.module = dict(asset="SM_Dojo", lods=[{"triangles": n} for n in (704, 352, 176)], material_slots=self.mesh.names[:])
        self.library = NS(has_material_usage=lambda material, usage: usage in material.usages)
    def enable(self): return D.enable_full_fallback(self.mesh, self.module, self.editor, U, self.library)

    def test_explicit_full_fallback_retains_three_authored_lods_slots_and_foliage(self):
        before = D.conventional(self.mesh, self.editor)
        result = self.enable()
        self.assertEqual(result["conventional_before"], before)
        self.assertEqual(result["conventional_after"], before)
        self.assertEqual(result["materials"][1]["shading"], "TwoSidedFoliage")
        self.assertTrue(result["materials"][1]["two_sided"])
        self.assertEqual(result["settings"], dict(enabled=True, generate_fallback="Enabled", fallback_target="PercentTriangles",
            fallback_percent_triangles=1., fallback_relative_error=0., keep_percent_triangles=1., trim_relative_error=0.))
        self.assertFalse(result["m1_qualified"]); self.assertFalse(result["unique_beam_art"])
        json.dumps(result)

    def test_repeat_import_explicitly_resets_old_nanite_before_baseline_and_reenables(self):
        first = self.enable()
        D.prepare_conventional(self.mesh, self.editor)
        self.assertIs(self.mesh.settings.values["enabled"], False)
        second = self.enable()
        self.assertEqual(first, second)
        self.assertEqual(self.editor.applied, 3)

    def test_preserved_enable_flag_refusal_stops_reimport(self):
        self.mesh.settings.values["enabled"] = True
        self.editor.changed = lambda m: m.settings.values.update(enabled=True)
        with self.assertRaisesRegex(RuntimeError, "conventional import baseline"): D.prepare_conventional(self.mesh, self.editor)

    def test_each_rejected_setting_readback_stops_import(self):
        bad = dict(enabled=False, generate_fallback="PlatformDefault", fallback_target="Auto", fallback_percent_triangles=.9,
                   fallback_relative_error=1., keep_percent_triangles=.5, trim_relative_error=.01)
        for key, value in bad.items():
            with self.subTest(key=key):
                self.setUp(); self.editor.changed = lambda m: m.settings.values.update({key: value})
                with self.assertRaisesRegex(RuntimeError, key): self.enable()

    def test_positive_settings_without_built_root_data_cannot_pass(self):
        for field in ("nanite_triangles", "nanite_vertices"):
            self.setUp(); setattr(self.mesh, field, 0)
            with self.assertRaisesRegex(RuntimeError, "root resources are absent"): self.enable()

    def test_fallback_reduction_uv_loss_lod_drop_and_slot_reordering_are_rejected(self):
        def reduce(m): m.lods[0][0] -= 1
        def vertices(m): m.lods[0][1] -= 1
        def uv(m): m.lods[0][2] = 0
        def lod_drop(m): m.lods.pop()
        def slot(m): m.names.reverse()
        def sections(m): m.lods[0][3].reverse()
        def distances(m): m.screens[1] = .5
        for change in (reduce, vertices, uv, lod_drop, slot, sections, distances):
            with self.subTest(change=change.__name__):
                self.setUp(); self.editor.changed = change
                with self.assertRaisesRegex(RuntimeError, "full fallback changed"): self.enable()

    def test_bounds_collision_shadow_and_material_changes_are_rejected(self):
        def bounds(m): m.bounds.box_extent.x += 1
        def simple(m): m.simple = 1
        def complex_(m): m.complexity = "UseComplexAsSimple"
        def section(m): m.collision = True
        def shadow(m): m.shadow = False
        def materials(m): m.materials.reverse()
        for change in (bounds, simple, complex_, section, shadow, materials):
            with self.subTest(change=change.__name__):
                self.setUp(); self.editor.changed = change
                with self.assertRaisesRegex(RuntimeError, "full fallback changed"): self.enable()

    def test_unreviewed_material_models_and_instance_overrides_are_not_rewritten(self):
        for change in (lambda m: m.props.update(blend_mode="Translucent"), lambda m: m.props.update(material_domain="PostProcess"),
                       lambda m: m.props.update(shading_model="Water"), lambda m: setattr(m.overrides, "override_blend_mode", True),
                       lambda m: setattr(m.overrides, "override_shading_model", True), lambda m: m.usages.remove("Nanite"),
                       lambda m: m.usages.remove("Instanced")):
            self.setUp(); change(self.mesh.materials[0])
            with self.assertRaises(RuntimeError): self.enable()
            self.assertEqual(self.editor.applied, 0)

    def test_authored_missing_or_duplicate_slots_and_triangle_changes_stop_before_enabling(self):
        for key, value in (("lods", [{"triangles": 700}]), ("material_slots", ["M_Timber", "M_Timber"])):
            self.setUp(); self.module[key] = value
            with self.assertRaises(RuntimeError): self.enable()
            self.assertEqual(self.editor.applied, 0)

    def test_production_importer_enables_only_after_source_lods_and_materials_are_bound(self):
        text = (HERE / "import_nyaagyu_dojo_kit.py").read_text()
        self.assertLess(text.index("prepare_conventional(existing, meshes)"), text.index("task.filename = str(ROOT / lods[0]"))
        self.assertLess(text.index("meshes.import_lod(mesh"), text.index("audit = enable_full_fallback("))
        self.assertLess(text.index("mesh.set_material(i, instances[slot])"), text.index("audit = enable_full_fallback("))
        self.assertIn('data.auto_generate_collision = False', text)
        self.assertIn('set_base_material_usage(parent, unreal.MaterialUsage.MATUSAGE_NANITE, True)', text)
        self.assertIn('SORA_DOJO_NANITE_IMPORT', text)
        manifest = json.loads((HERE.parents[1] / "Content/SourceArt/Environment/NyaagyuDojoKit/manifest.json").read_text())
        self.assertEqual(len(manifest["modules"]), 12)
        self.assertTrue(all(lod["triangles"] > 0 for module in manifest["modules"] for lod in module["lods"]))


if __name__ == "__main__": unittest.main()
