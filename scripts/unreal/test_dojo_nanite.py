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


class Overrides:
    # Match the engine's editor reflection surface. No direct field attributes.
    __slots__ = ("values",)
    def __init__(self):
        self.values = dict(override_blend_mode=False, blend_mode="Translucent", override_shading_model=False,
                           shading_model="Water", override_two_sided=False, two_sided=False)
    def get_editor_property(self, name): return self.values[name]
    def set_editor_property(self, name, value): self.values[name] = value


class Material:
    def __init__(self, name, foliage=False):
        self.name = name
        self.props = dict(material_domain="Surface", blend_mode="Opaque", shading_model="TwoSidedFoliage" if foliage else "DefaultLit", two_sided=foliage)
        self.overrides = Overrides()
        self.usages = {"Instanced", "Nanite"}
    def get_base_material(self): return self
    def get_editor_property(self, name): return self.overrides if name == "base_property_overrides" else self.props[name]
    def get_path_name(self): return "/Game/Generated/Environment/DojoKit/" + self.name


class Tangent:
    __slots__ = ("values",)
    def __init__(self): self.values = {"tangent_x": NS(x=1., y=0., z=0.), "flip_tangent_y": False}
    def get_editor_property(self, name): return self.values[name]


def section_geometry(lod, section):
    positions = [NS(x=x, y=-20. if section == 0 else 20., z=z)
                 for x, z in ((-90., 0.), (90., 0.), (90., 700.), (-90., 700.))]
    indices = [0, 1, 2, 0, 2, 3] if lod == 0 else [0, 1, 2]
    if lod > 0: positions.pop()
    normals = [NS(x=0., y=-1. if section == 0 else 1., z=0.) for _ in positions]
    uvs = [NS(x=x, y=y) for x, y in ((0., 0.), (1., 0.), (1., 1.), (0., 1.))][:len(positions)]
    return [positions, indices, normals, uvs, [Tangent() for _ in positions]]


class Procedural:
    @staticmethod
    def get_section_from_static_mesh(mesh, lod, section):
        # The real API returns copied conventional render buffers, including
        # only referenced section vertices. It never sets CPU access for us.
        return copy.deepcopy(mesh.geometry[lod][section])


U.ProceduralMeshLibrary = Procedural


class Mesh:
    def __init__(self):
        self.settings = Settings()
        self.lods = [[4, 8, 2, [0, 1]], [2, 6, 1, [0, 1]], [2, 6, 1, [0, 1]]]
        self.geometry = [[section_geometry(lod, section) for section in range(2)] for lod in range(3)]
        self.names = ["M_Timber", "M_Paper"]
        self.materials = [Material("MI_Timber"), Material("MI_Paper", True)]
        self.screens = [1., .25, .08]
        self.bounds = NS(origin=NS(x=0,y=0,z=350), box_extent=NS(x=90,y=20,z=350))
        self.simple = 0; self.complexity = "Default"; self.collision = False; self.shadow = True
        self.nanite_triangles = 704; self.nanite_vertices = 1000
        self.cpu_access = False
    def get_editor_property(self, name):
        if name == "allow_cpu_access": return self.cpu_access
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
    def __init__(self, changed=None):
        self.changed = changed; self.applied = 0; self.restore_screens = True; self.bad_restored_screens = False
    def get_lod_count(self, mesh): return len(mesh.lods)
    def get_lod_screen_sizes(self, mesh): return mesh.screens
    def get_lod_material_slot(self, mesh, lod, section): return mesh.lods[lod][3][section]
    def is_section_collision_enabled(self, mesh, lod, section): return mesh.collision
    def is_section_cast_shadow_enabled(self, mesh, lod, section): return mesh.shadow
    def get_simple_collision_count(self, mesh): return mesh.simple
    def get_collision_complexity(self, mesh): return mesh.complexity
    def get_nanite_settings(self, mesh): return copy.deepcopy(mesh.settings)
    def set_lod_screen_sizes(self, mesh, values):
        if not self.restore_screens: return False
        mesh.screens = list(values[:len(mesh.lods)])
        if self.bad_restored_screens: mesh.screens[-1] += .1
        return True
    def set_nanite_settings(self, mesh, settings, apply):
        assert apply is True
        mesh.settings = copy.deepcopy(settings); self.applied += 1
        if self.changed: self.changed(mesh)


class Assets:
    def __init__(self): self.saves = 0; self.fail_save = 0; self.on_save = None
    def save_loaded_asset(self, mesh, only_if_is_dirty=True):
        assert only_if_is_dirty is False
        self.saves += 1
        if self.on_save: self.on_save(mesh, self.saves)
        return self.saves != self.fail_save


class DojoNaniteTests(unittest.TestCase):
    def setUp(self):
        self.mesh = Mesh(); self.editor = Editor()
        self.module = dict(asset="SM_Dojo", lods=[{"triangles": n} for n in (4, 2, 2)], material_slots=self.mesh.names[:])
        self.library = NS(has_material_usage=lambda material, usage: usage in material.usages)
        self.assets = Assets()
    def enable(self): return D.enable_full_fallback(self.mesh, self.module, self.editor, U, self.library, self.assets)

    def test_explicit_full_fallback_retains_three_authored_lods_slots_and_foliage(self):
        before, _ = D.conventional(self.mesh, self.editor, Procedural)
        result = self.enable()
        self.assertEqual(result["conventional_before"], before)
        self.assertEqual(result["conventional_after"], before)
        self.assertEqual(result["materials"][1]["shading"], "TwoSidedFoliage")
        self.assertTrue(result["materials"][1]["two_sided"])
        self.assertEqual(result["settings"], dict(enabled=True, generate_fallback="Enabled", fallback_target="PercentTriangles",
            fallback_percent_triangles=1., fallback_relative_error=0., keep_percent_triangles=1., trim_relative_error=0.))
        self.assertFalse(result["m1_qualified"]); self.assertFalse(result["unique_beam_art"])
        self.assertFalse(result["conventional_after"]["allow_cpu_access"])
        self.assertIn("UV1+ values", result["geometry_readback"]["not_compared"])
        self.assertEqual(self.assets.saves, 2)
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
        def reduce(m):
            for section in range(2): m.geometry[0][section] = copy.deepcopy(m.geometry[1][section])
            m.lods[0][0] = 2; m.lods[0][1] = 6
        def vertices(m): m.lods[0][1] -= 1
        def uv(m): m.lods[0][2] = 0
        def lod_drop(m): m.lods.pop()
        def slot(m): m.names.reverse()
        def sections(m): m.lods[0][3].reverse()
        for change in (reduce, vertices, uv, lod_drop, slot, sections):
            with self.subTest(change=change.__name__):
                self.setUp(); self.editor.changed = change
                with self.assertRaisesRegex(RuntimeError, "full fallback changed"): self.enable()

    def test_collision_shadow_and_material_changes_are_rejected(self):
        def simple(m): m.simple = 1
        def complex_(m): m.complexity = "UseComplexAsSimple"
        def section(m): m.collision = True
        def shadow(m): m.shadow = False
        def materials(m): m.materials.reverse()
        def cpu_access(m): m.cpu_access = True
        for change in (simple, complex_, section, shadow, materials, cpu_access):
            with self.subTest(change=change.__name__):
                self.setUp(); self.editor.changed = change
                with self.assertRaisesRegex(RuntimeError, "full fallback changed"): self.enable()

    def test_same_counts_do_not_hide_geometry_or_vertex_attribute_changes(self):
        def position(s): s[0][0].x += .00000001
        def normal(s): s[2][0].z += .00000001
        def uv(s): s[3][0].x += .00000001
        def tangent(s): s[4][0].values["tangent_x"].z += .00000001
        def handedness(s): s[4][0].values["flip_tangent_y"] = True
        def winding(s): s[1][0], s[1][1] = s[1][1], s[1][0]
        def connectivity(s): s[1][:] = [0, 1, 3, 1, 2, 3]
        for change in (position, normal, uv, tangent, handedness, winding, connectivity):
            for lod in (0, 2) if change not in (connectivity,) else (0,):
                with self.subTest(change=change.__name__, lod=lod):
                    self.setUp()
                    self.editor.changed = lambda m: change(m.geometry[lod][0])
                    with self.assertRaisesRegex(RuntimeError, "oriented triangle geometry/attributes"): self.enable()

    def test_vertex_index_triangle_and_cyclic_corner_reordering_preserves_exact_content(self):
        def reorder(mesh):
            for lod in mesh.geometry:
                for section in lod:
                    permutation = list(reversed(range(len(section[0]))))
                    remap = {old: new for new, old in enumerate(permutation)}
                    for channel in (0, 2, 3, 4): section[channel] = [section[channel][old] for old in permutation]
                    indices = [remap[index] for index in section[1]]
                    triangles = [indices[index:index+3] for index in range(0, len(indices), 3)]
                    section[1] = [index for triangle in reversed(triangles) for index in triangle[1:] + triangle[:1]]
        self.editor.changed = reorder
        result = self.enable()
        self.assertEqual(result["conventional_before"], result["conventional_after"])

    def test_canonicalization_preserves_duplicate_triangle_multiplicity(self):
        a = section_geometry(0, 0); b = copy.deepcopy(a)
        a[1] = [0, 1, 2, 0, 1, 2, 0, 2, 3]
        b[1] = [0, 1, 2, 0, 2, 3, 0, 2, 3]
        ca, ra = D.canonical_section(a, "a"); cb, rb = D.canonical_section(b, "b")
        self.assertEqual(set(ca), set(cb))
        self.assertNotEqual(ca, cb)
        self.assertNotEqual(ra["oriented_content_sha256"], rb["oriented_content_sha256"])

    def test_nanite_bounds_can_expand_but_must_contain_all_conventional_lods(self):
        def expand(m): m.bounds.origin.z += 1; m.bounds.box_extent.z += 3; m.bounds.box_extent.x += 1
        self.editor.changed = expand
        result = self.enable()
        before, after = result["conventional_before"], result["conventional_after"]
        self.assertNotEqual(before["composite_bounds"], after["composite_bounds"])
        self.assertEqual(before["geometry_bounds"], after["geometry_bounds"])
        self.assertEqual(before["lods"], after["lods"])
        for field, value in (("x", 89.99999), ("y", -1.), ("z", float("nan")), ("z", float("inf"))):
            with self.subTest(field=field, value=value):
                self.setUp(); self.editor.changed = lambda m: setattr(m.bounds.box_extent, field, value)
                with self.assertRaisesRegex(RuntimeError, "composite.*bounds"): self.enable()
        self.setUp(); self.editor.changed = lambda m: setattr(m.bounds.origin, "z", 351.)
        with self.assertRaisesRegex(RuntimeError, "contain conventional"): self.enable()

    def test_malformed_or_nonfinite_readback_cannot_be_a_geometry_pass(self):
        for change in (lambda s: s[2].pop(), lambda s: s[1].append(0), lambda s: s[1].__setitem__(0, 99),
                       lambda s: setattr(s[0][0], "x", float("nan")), lambda s: setattr(s[3][0], "y", float("inf")),
                       lambda s: s[4][0].values.update(flip_tangent_y=1)):
            with self.subTest(change=change):
                self.setUp(); self.editor.changed = lambda m: change(m.geometry[0][0])
                with self.assertRaises(RuntimeError): self.enable()
        self.setUp(); self.editor.changed = lambda m: m.lods[0].__setitem__(0, 3)
        with self.assertRaisesRegex(RuntimeError, "does not cover reported render triangles"): self.enable()

    def test_restore_original_screen_thresholds_then_audit_saved_result(self):
        self.editor.changed = lambda m: setattr(m, "screens", [0., 0., 0.])
        result = self.enable()
        self.assertEqual(result["conventional_before"]["screen_sizes"], [1., .25, .08])
        self.assertEqual(result["conventional_after"]["screen_sizes"], [1., .25, .08])
        for failure in ("restore_screens", "bad_restored_screens"):
            self.setUp(); setattr(self.editor, failure, failure != "restore_screens")
            with self.assertRaisesRegex(RuntimeError, "screen sizes|screen_sizes"): self.enable()
        self.setUp()
        self.assets.on_save = lambda m, ordinal: setattr(m.geometry[0][0][3][0], "x", .125) if ordinal == 2 else None
        with self.assertRaisesRegex(RuntimeError, "oriented triangle geometry/attributes"): self.enable()
        self.setUp()
        self.assets.on_save = lambda m, ordinal: setattr(m, "screens", [1., .5, .08]) if ordinal == 2 else None
        with self.assertRaisesRegex(RuntimeError, "screen_sizes"): self.enable()

    def test_failed_baseline_or_final_save_cannot_emit_success(self):
        for ordinal in (1, 2):
            self.setUp(); self.assets.fail_save = ordinal
            with self.assertRaisesRegex(RuntimeError, "could not save"): self.enable()

    def test_unreviewed_material_models_and_instance_overrides_are_not_rewritten(self):
        for change in (lambda m: m.props.update(blend_mode="Translucent"), lambda m: m.props.update(material_domain="PostProcess"),
                       lambda m: m.props.update(shading_model="Water"), lambda m: m.overrides.set_editor_property("override_blend_mode", True),
                       lambda m: m.overrides.set_editor_property("override_shading_model", True), lambda m: m.usages.remove("Nanite"),
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
