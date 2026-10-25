"""Synthetic probe transport/negative tests, never renderer or art evidence."""
import copy
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("probe_test_pixels", HERE / "test_nanite_capture.py")
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)
VERIFY = BASE.VERIFY
P = VERIFY.timber_probe_capture_validation
WIDTH, HEIGHT = BASE.WIDTH, BASE.HEIGHT


def metadata(sm6=True):
    meta = {"schema": P.SCHEMA, "scope": P.SCOPE, "passed": True, "restored": True, "packages_unchanged": True,
            "sm6_requested": sm6, "nanite_eligible": sm6, "shader_platform": "METAL_SM6" if sm6 else "METAL_SM5",
            "rhi": "Metal", "adapter": "synthetic, not hardware evidence", "null_rhi": False,
            "viewport": [WIDTH, HEIGHT], "fixture_origin": [1000000]*3, "meshes": [], "frames": []}
    control = {"screen_percentage": 75, "flags": 0x02000000, "set_by": "Scalability",
               "dynamic_resolution_status": "Disabled", "test_interface_override_registered": False, "test_interface_override": None}
    meta['original_resolution_control'] = control
    meta['restored_resolution_control'] = copy.deepcopy(control)
    for i, name in enumerate(P.NAMES):
        dense = i < 5
        textures = {} if dense else {param: P.object_path("Textures/T_" + name.removeprefix("SM_") + "_" + suffix)
                                    for param, suffix in (("NormalMap", "NormalDX"), ("MasksMap", "Masks"))}
        meta["meshes"].append({"name": name, "mesh": P.object_path(name), "kind": "dense_nanite_source" if dense else "authored_conventional_pool",
            "has_nanite_data": dense, "has_platform_fallback": dense, "authoring_nanite_enabled": dense, "disallow_nanite": False, "force_disable_nanite": False,
            "nanite_input_triangles": 100000 if dense else 0, "source_triangles": 100000, "lod0_render_triangles": 5000,
            "uv_channels": 4, "bounds_origin": [1000000]*3, "bounds_extent": [20, 20, 250],
            "materials": [{"material": P.object_path("MI_" + name), "parent": P.object_path("M_SoraTimberNanite" if dense else "M_SoraTimber"),
                           "textures": textures, "scalars": {"RingWidth": .002}}],
            "uv_observations": [{"channel": channel, "scanned_vertex_instances": 12, "min": [-1, -1], "max": [1, 1],
                                 "samples": [{"vertex_instance": 0, "uv": [.1, -.2]}]} for channel in (2, 3)]})
        for view, mode in ([('full', m) for m in ('Lit', 'Mask', 'Triangles')] if sm6 else [('full', 'Lit')]) + [('detail', 'Lit')]:
            phase = f"{name}-{view}-{mode}"
            meta["frames"].append({"name": phase, "file": phase + ".png", "mesh_name": name, "view": view, "mode": mode,
                "paused": True, "hud_hidden": True, "visible_fixture_meshes": 1, "settle_seconds": 3.1,
                "camera": [1001000, 999000, 1000500], "rotation": [0, 0, 0], "fov": 35,
                "request_frame": len(meta["frames"])*100+10, "screenshot_processed_frame": len(meta["frames"])*100+11,
                "final_view_observations": 1, "final_view_frame": len(meta["frames"])*100+11,
                "final_post_process": copy.deepcopy(P.FINAL_POST_PROCESS), "final_show_flags": dict.fromkeys(P.EXCLUDED_SHOW_FLAGS, False),
                "final_resolution": {**control, "screen_percentage": 100, "primary_fraction_upper_bound": 1,
                                     "secondary_fraction": 1, "view_primary_fraction_override": -1, "screen_percentage_show_flag": True,
                                     "unscaled_view_rect": [0, 0, WIDTH, HEIGHT]},
                "active_visualization": mode if mode != 'Lit' else 'None', "active_mode_id": 1 if mode != 'Lit' else -1,
                "material_render_readback": {"proxy_present": True, "shader_map_valid": True, "shader_map_complete": True,
                                             "used_fallback_proxy": False, "default_material": False, "resource_asset": "M_SoraTimberNanite" if dense else "M_SoraTimber"},
                "show_visualize_nanite": mode != 'Lit', "cvars": {"r.Nanite": "1", "r.Nanite.ProxyRenderMode": "0", "r.ScreenPercentage": "100",
                    "r.Nanite.Visualize": mode if mode != 'Lit' else 'off', "r.Nanite.Visualize.Composite": "1",
                    "r.Nanite.Visualize.EdgeDetect": "0", "r.Nanite.Visualize.DebugShading": "0"}})
    for frame in meta['frames']:
        shader = frame['material_render_readback']
        shader.update(observation_stage='after_screenshot_processed', observation_frame=frame['screenshot_processed_frame'])
        pre = {**shader, 'observation_stage': 'before_screenshot_request', 'observation_frame': frame['request_frame']}
        first = {**shader, 'observation_stage': 'visible_readiness_poll', 'observation_frame': frame['request_frame']-1}
        frame['material_pre_request_readback'] = pre
        frame['material_readiness'] = {'polls': 2, 'rejected': 0, 'deadline_seconds': 30, 'elapsed_seconds': 3.1,
            'first_ready_frame': first['observation_frame'], 'first_ready_observation': first,
            'first_observation': first, 'last_observation': {**first, 'observation_frame': frame['request_frame']}}
    meta['frame_count'] = len(meta['frames'])
    return meta


def originals(meta):
    images = {}
    for frame in meta['frames']:
        mode = frame['mode']
        kind = 'lit' if mode == 'Lit' else 'triangle' if mode == 'Triangles' else ('mask' if P.NAMES.index(frame['mesh_name']) < 5 else 'red')
        images[frame['file']] = BASE.png(kind)
    return images


class ProbeEvidence(unittest.TestCase):
    def inspect(self, meta=None, images=None):
        meta = metadata() if meta is None else meta
        return P.inspect(meta, originals(meta) if images is None else images, WIDTH, HEIGHT, VERIFY.bow_capture_validation.rgb8)

    def test_five_dense_and_four_negative_controls_are_separate(self):
        result = self.inspect()
        self.assertTrue(result['nanite_draw_evidence'])
        self.assertEqual(len(result['meshes']), 9)
        self.assertTrue(result['human_geometry_material_review_required'])
        self.assertFalse(result['release_qualified'])

    def test_flags_and_positive_cpu_counts_do_not_pass_copied_lit(self):
        meta = metadata(); images = {name: BASE.png('lit') for name in originals(meta)}
        result = self.inspect(meta, images)
        self.assertFalse(result['nanite_draw_evidence']); self.assertEqual(len(result['errors']), 9)

    def test_green_material_and_mask_without_triangles_do_not_prove_draw(self):
        meta = metadata()
        for kind in ('green-material', 'lit'):
            images = originals(meta)
            for name in P.NAMES[:5]:
                if kind == 'lit': images[f'{name}-full-Triangles.png'] = BASE.png('lit')
                else:
                    for mode in ('Lit', 'Mask', 'Triangles'): images[f'{name}-full-{mode}.png'] = BASE.png(kind)
            self.assertFalse(self.inspect(meta, images)['nanite_draw_evidence'])

    def test_dense_red_and_pool_green_fail_separately(self):
        meta = metadata(); images = originals(meta)
        images[f'{P.NAMES[0]}-full-Mask.png'] = BASE.png('red')
        images[f'{P.NAMES[5]}-full-Mask.png'] = BASE.png('mask')
        result = self.inspect(meta, images)
        self.assertEqual(len(result['errors']), 2)
        self.assertFalse(result['nanite_draw_evidence'])

    def test_sm5_generated_dense_fallback_is_not_authored_pool_or_m1_proof(self):
        meta = metadata(False); result = self.inspect(meta)
        self.assertEqual(meta['frame_count'], 18)
        self.assertFalse(result['nanite_draw_evidence']); self.assertFalse(result['hardware_m1_qualified'])
        self.assertEqual(result['meshes'][P.NAMES[0]]['render_path'], 'generated dense-asset fallback')
        self.assertEqual(result['meshes'][P.NAMES[5]]['render_path'], 'authored conventional pool')

    def test_missing_duplicate_wrong_model_restoration_and_resource_flags_fail(self):
        changes = [lambda d: d['meshes'].pop(), lambda d: d['meshes'].__setitem__(8, copy.deepcopy(d['meshes'][0])),
                   lambda d: d.update(shader_platform='METAL_SM5'), lambda d: d.update(null_rhi=True),
                   lambda d: d.update(restored=False), lambda d: d.update(packages_unchanged=False),
                   lambda d: d['meshes'][0].update(has_nanite_data=False), lambda d: d['meshes'][0].update(force_disable_nanite=True)]
        for change in changes:
            meta = metadata(); change(meta)
            with self.assertRaises(ValueError): self.inspect(meta)

    def test_wrong_parent_or_pool_map_rejected_even_with_valid_pixels(self):
        for index, key in ((0, 'parent'), (5, 'textures')):
            meta = metadata(); material = meta['meshes'][index]['materials'][0]
            material[key] = '/Game/Unreviewed.Mat' if key == 'parent' else {}
            with self.assertRaises(ValueError): self.inspect(meta)

    def test_missing_unbounded_nonfinite_and_outside_saved_uv_observations_fail(self):
        changes = [lambda u: u.update(samples=[]), lambda u: u.update(scanned_vertex_instances=3000001),
                   lambda u: u.update(min=[float('nan'), 0]), lambda u: u['samples'][0].update(uv=[2, 0])]
        for change in changes:
            meta = metadata(); change(meta['meshes'][0]['uv_observations'][0])
            with self.assertRaises(ValueError): self.inspect(meta)

    def test_moved_paired_camera_mode_chronology_extra_visible_mesh_and_missing_detail_fail(self):
        changes = [lambda d: d['frames'][1].update(camera=[1, 2, 3]), lambda d: d['frames'][1].update(active_visualization='None'),
                   lambda d: d['frames'][1].update(request_frame=0), lambda d: d['frames'][0].update(visible_fixture_meshes=2),
                   lambda d: d['frames'].pop()]
        for change in changes:
            meta = metadata(); change(meta)
            with self.assertRaises(ValueError): self.inspect(meta)

    def test_sm5_dense_requires_actual_generated_platform_fallback(self):
        meta = metadata(False); meta['meshes'][0]['has_platform_fallback'] = False
        with self.assertRaises(ValueError): self.inspect(meta)

    def test_fallback_shader_or_incomplete_material_cannot_pass_green_pixels(self):
        for key, value in (("used_fallback_proxy", True), ("default_material", True), ("shader_map_valid", False), ("shader_map_complete", False)):
            meta = metadata(); meta['frames'][0]['material_render_readback'][key] = value
            with self.assertRaises(ValueError): self.inspect(meta)

    def test_ready_before_request_does_not_admit_stale_or_failed_final_observation(self):
        mutations = [lambda f: f['material_render_readback'].update(observation_stage='before_screenshot_request'),
                     lambda f: f['material_render_readback'].update(observation_frame=f['request_frame']),
                     lambda f: f['material_pre_request_readback'].update(observation_frame=f['request_frame']-1),
                     lambda f: f['material_render_readback'].update(used_fallback_proxy=True),
                     lambda f: f['material_pre_request_readback'].update(shader_map_complete=False),
                     lambda f: f['material_render_readback'].update(resource_asset='M_Other'),
                     lambda f: f.update(final_view_frame=f['request_frame']),
                     lambda f: f.pop('material_pre_request_readback')]
        for sm6 in (False, True):
            for mutation in mutations:
                meta = metadata(sm6); mutation(meta['frames'][0])
                with self.assertRaises(ValueError): self.inspect(meta)
        meta = metadata(); meta['schema'] = 'sora-arena.timber-probe.v2'
        with self.assertRaises(ValueError): self.inspect(meta)

    def test_two_distinct_ready_frames_and_deadline_are_required(self):
        mutations = [lambda r: r.update(polls=1), lambda r: r.update(rejected=1),
                     lambda r: r.update(elapsed_seconds=30), lambda r: r.update(elapsed_seconds=float('nan')),
                     lambda r: r.update(deadline_seconds=31), lambda r: r.update(first_ready_frame=10),
                     lambda r: r['first_ready_observation'].update(used_fallback_proxy=True),
                     lambda r: r['last_observation'].update(observation_frame=9)]
        for mutation in mutations:
            meta = metadata(); mutation(meta['frames'][0]['material_readiness'])
            with self.assertRaises(ValueError): self.inspect(meta)
        meta = metadata(); r = meta['frames'][1]['material_readiness']
        r['first_ready_frame'] = r['first_ready_observation']['observation_frame'] = 9
        with self.assertRaises(ValueError): self.inspect(meta)  # previous view's readiness cannot be reused
        # A prior failed poll remains diagnostic evidence once two later
        # observations and the saved frame all resolve the correct base master.
        meta = metadata(); r = meta['frames'][0]['material_readiness']
        bad = {**r['first_observation'], 'used_fallback_proxy': True, 'resource_asset': 'WorldGridMaterial', 'observation_frame': 8}
        r.update(polls=3, rejected=1, first_observation=bad, last_rejected_observation=bad)
        self.assertTrue(self.inspect(meta)['nanite_draw_evidence'])

    def test_actual_readiness_gate_rejects_duplicate_frames_regression_and_deadline(self):
        # Compile only this dependency-free admission policy, never Unreal.
        compiler = shutil.which('c++')
        self.assertIsNotNone(compiler, 'the host source gate requires a C++ compiler')
        driver = r"""
#include "World/SoraCaptureReadiness.h"
#include <cassert>
using namespace SoraCaptureReadiness;
int main() {
    FGate g; g.Started=100;
    assert(g.Observe(103,10,false)==EResult::Wait);
    assert(g.Observe(104,11,true)==EResult::Wait);
    assert(g.Observe(104.1,11,true)==EResult::Wait);
    assert(g.Observe(104.2,10,true)==EResult::Wait);
    assert(g.Polls==2 && g.Rejected==1);
    assert(g.Observe(105,12,false)==EResult::Wait); // ready state regresses
    assert(!g.HasReady && g.FirstReadyFrame==0);
    assert(g.Observe(106,13,true)==EResult::Wait);
    assert(g.Observe(107,14,true)==EResult::Capture);
    assert(g.Polls==5 && g.Rejected==2 && g.FirstReadyFrame==13);
    g={}; g.Started=200; // next mesh cannot inherit readiness
    assert(g.Observe(203,20,true)==EResult::Wait);
    assert(g.Observe(230,21,true)==EResult::TimedOut);
    assert(g.Observe(231,22,false)==EResult::TimedOut);
    g={};
    for (unsigned i=0;i<1000;++i) assert(g.Observe(3+i*.02,i,false)==EResult::Wait);
    assert(g.Observe(30,1000,false)==EResult::TimedOut);
    assert(g.Rejected==1000 && !g.HasReady);
}
"""
        with tempfile.TemporaryDirectory() as td:
            path = Path(td); (path/'gate.cpp').write_text(driver)
            subprocess.run([compiler, '-std=c++17', '-Wall', '-Wextra', '-Werror', '-I', str(HERE.parents[1]/'Source/SoraArena/Private'),
                            str(path/'gate.cpp'), '-o', str(path/'gate')], check=True, capture_output=True, timeout=30)
            subprocess.run([str(path/'gate')], check=True, capture_output=True, timeout=5)

    def test_engine_success_leaves_proxy_output_unchanged_and_real_fallback_is_rejected(self):
        # Pinned UE5.8 MaterialRenderProxy.cpp:870-892 writes its output only
        # inside the fallback branch. Exercise that contract against the actual
        # capture initializer without compiling/launching any Unreal code.
        import re
        source = (HERE.parents[1] / 'Source/SoraArena/Private/SoraTimberProbeCapture.cpp').read_text()
        match = re.search(r'const FMaterialRenderProxy\* ResolvedProxy=(Proxy|nullptr);\s*const FMaterial& Resolved=Proxy->GetMaterialWithFallback\(Feature,ResolvedProxy\);\s*Shader.Fallback=ResolvedProxy!=Proxy;', source)
        self.assertIsNotNone(match, 'review the engine-output contract if the capture call changes')
        proxy, fallback = object(), object()

        def observed_fallback(initializer, shader_complete):
            out_proxy = proxy if initializer == 'Proxy' else None
            if not shader_complete:
                out_proxy = fallback  # engine writes this only on fallback
            return out_proxy is not proxy

        self.assertTrue(observed_fallback('nullptr', True), 'reproduces the old false fallback')
        healthy = observed_fallback(match[1], True)
        self.assertFalse(healthy, 'a complete base shader must not be classified as fallback')
        meta = metadata(); meta['frames'][0]['material_render_readback']['used_fallback_proxy'] = healthy
        self.assertTrue(self.inspect(meta)['nanite_draw_evidence'])
        meta['frames'][0]['material_render_readback']['used_fallback_proxy'] = observed_fallback(match[1], False)
        with self.assertRaises(ValueError): self.inspect(meta)

    def test_actual_production_sun_grade_gi_or_reflections_prevent_fixture_acceptance(self):
        for flag in P.EXCLUDED_SHOW_FLAGS:
            meta = metadata(); meta['frames'][0]['final_show_flags'][flag] = True
            with self.assertRaises(ValueError): self.inspect(meta)
        for key, value in (('ColorSaturation', [.96, .96, .96, 1]), ('BloomIntensity', .2),
                           ('DynamicGlobalIlluminationMethod', 1), ('ReflectionMethod', 1)):
            meta = metadata(); meta['frames'][0]['final_post_process'][key] = value
            with self.assertRaises(ValueError): self.inspect(meta)

    def test_requested_camera_settings_without_unique_current_final_view_are_rejected(self):
        for field, value in (('final_view_observations', 0), ('final_view_observations', 2), ('final_view_frame', 0), ('final_post_process', {})):
            meta = metadata(); meta['frames'][0][field] = value
            with self.assertRaises(ValueError): self.inspect(meta)

    def test_cpp_fixed_asset_order_schema_and_scope_match_transport(self):
        import re
        source = (HERE.parents[1] / 'Source/SoraArena/Private/SoraTimberProbeCapture.cpp').read_text()
        declaration = source.split('const TCHAR* Names[]={', 1)[1].split('};', 1)[0]
        self.assertEqual(tuple(re.findall(r'TEXT\("([^"\n]+)"\)', declaration)), P.NAMES)
        self.assertIn(P.SCHEMA, source); self.assertIn(P.SCOPE, source)

    def test_100_cvar_cannot_hide_dynamic_secondary_or_wrong_final_view_scaling(self):
        for sm6 in (False, True):
            for field, value in (('screen_percentage', 75), ('dynamic_resolution_status', 'Enabled'),
                    ('dynamic_resolution_status', 'Paused'), ('dynamic_resolution_status', 'DebugForceEnabled'),
                    ('test_interface_override', 1), ('primary_fraction_upper_bound', .75), ('primary_fraction_upper_bound', float('nan')),
                    ('view_primary_fraction_override', .75), ('view_primary_fraction_override', 1), ('view_primary_fraction_override', float('nan')),
                    ('secondary_fraction', .5), ('unscaled_view_rect', [0, 0, WIDTH-1, HEIGHT]),
                    ('set_by', 'Console'), ('flags', 0x10000000)):
                with self.subTest(sm6=sm6, field=field, value=value):
                    meta = metadata(sm6); meta['frames'][-1]['final_resolution'][field] = value
                    with self.assertRaises(ValueError): self.inspect(meta)
            meta = metadata(sm6); meta['frames'][-1].pop('final_resolution')
            with self.assertRaises(ValueError): self.inspect(meta)

    def test_absent_test_cvar_is_explicit_and_active_or_unknown_controls_fail(self):
        for registered, value in ((False, None), (True, 0)):
            meta = metadata()
            for frame in meta['frames']:
                frame['final_resolution'].update(test_interface_override_registered=registered, test_interface_override=value)
            self.assertTrue(self.inspect(meta)['nanite_draw_evidence'])
        for registered, value in ((False, -1), (False, 0), (True, None), (True, -1), (True, 1), (True, False), (None, None)):
            meta = metadata()
            meta['frames'][0]['final_resolution'].update(test_interface_override_registered=registered, test_interface_override=value)
            with self.assertRaises(ValueError): self.inspect(meta)
        for key in ('test_interface_override_registered', 'test_interface_override', 'view_primary_fraction_override'):
            meta = metadata(); meta['frames'][0]['final_resolution'].pop(key)
            with self.assertRaises(ValueError): self.inspect(meta)
        meta = metadata(); meta['schema'] = 'sora-arena.timber-probe.v1'
        with self.assertRaises(ValueError): self.inspect(meta)

    def test_resolution_value_and_priority_must_both_restore(self):
        for field, value in (('screen_percentage', 100), ('flags', 0x10000000), ('set_by', 'Console')):
            meta = metadata(); meta['restored_resolution_control'][field] = value
            with self.assertRaises(ValueError): self.inspect(meta)


class ProvenanceAndTransport(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name).resolve() / 'project'; self.project.mkdir()
        self.meta = metadata()
        self.meta['asset_files'] = []
        for name in P.PACKAGES:
            path = self.project / 'Content/Generated/Qualification/DojoTimberProbe' / (name + '.uasset')
            path.parent.mkdir(parents=True, exist_ok=True); raw = (name + ' synthetic package').encode(); path.write_bytes(raw)
            self.meta['asset_files'].append({'path': str(path), 'bytes': len(raw), 'md5': hashlib.md5(raw).hexdigest()})
        self.meta['source_inputs'] = []
        for name in P.INPUTS:
            path = self.project / name; path.parent.mkdir(parents=True, exist_ok=True); raw = (name + ' synthetic source').encode(); path.write_bytes(raw)
            self.meta['source_inputs'].append({'path': name, 'bytes': len(raw), 'md5': hashlib.md5(raw).hexdigest()})
        self.commit = '1'*40

    def identities(self):
        def blob(command, **kwargs):
            return subprocess.CompletedProcess(command, 0, (self.project / command[-1].split(':', 1)[1]).read_bytes(), b'')
        with patch.object(P.subprocess, 'run', side_effect=blob):
            return P.identities(self.meta, self.project, self.commit)

    def test_all_31_packages_and_current_importer_source_pinned(self):
        identity = self.identities()
        self.assertEqual(len(identity['packages']), 31); self.assertEqual([row['path'] for row in identity['source_inputs']], list(P.INPUTS))
        self.assertTrue(all(len(row['sha256']) == 64 for row in identity['packages']))

    def test_changed_package_missing_package_and_unreviewed_extra_fail(self):
        path = Path(self.meta['asset_files'][0]['path']); original = path.read_bytes()
        path.write_bytes(original + b'changed')
        with self.assertRaises(ValueError): self.identities()
        path.write_bytes(original)
        extra = path.with_name('unreviewed.uasset'); extra.write_bytes(b'extra')
        with self.assertRaises(ValueError): self.identities()
        extra.unlink(); self.meta['asset_files'].pop()
        with self.assertRaises(ValueError): self.identities()

    def test_wrong_source_hash_and_package_symlink_rejected(self):
        self.meta['source_inputs'][0]['md5'] = '0'*32
        with self.assertRaises(ValueError): self.identities()
        self.meta['source_inputs'][0]['md5'] = hashlib.md5((self.project / P.INPUTS[0]).read_bytes()).hexdigest()
        path = Path(self.meta['asset_files'][0]['path']); saved = path.with_suffix('.retained'); path.rename(saved); path.symlink_to(saved)
        with self.assertRaises(ValueError): self.identities()

    def archive(self, fail=False):
        folder = self.project / 'Saved/Screenshots/SoraTimberProbe/fixture'; folder.mkdir(parents=True)
        if fail == 'partial':
            self.meta.update(passed=False, frame_count=1, frames=self.meta['frames'][:1])
            self.meta['frames'][0]['material_render_readback']['used_fallback_proxy'] = True
        images = originals(self.meta)
        if fail is True: images = {name: BASE.png('lit') for name in images}
        elif fail == 'shader': self.meta['frames'][0]['material_render_readback']['used_fallback_proxy'] = True
        lines = []
        for name, data in images.items():
            path = folder / name; path.write_bytes(data); lines.append('LogTemp: Display: SORA_TIMBER_PROBE_FRAME ' + str(path))
        (folder / 'capture.json').write_text(json.dumps(self.meta))
        output = self.project / 'Saved/Archive'; output.mkdir(); (output / 'source-commit.txt').write_text(self.commit)
        report = {'tests': [{'fullTestPath': 'SoraCapture.TimberProbe.SM6'}], 'devices': [{'renderMode': 'SM6'}]}
        with patch.object(P, 'identities', return_value={'synthetic': True}):
            if fail:
                with self.assertRaises(VERIFY.NaniteDrawEvidenceError) as error:
                    VERIFY.archive_frames('\n'.join(lines), report, self.project, self.project, output, 0, WIDTH, HEIGHT)
                frames = error.exception.frames
            else:
                frames = VERIFY.archive_frames('\n'.join(lines), report, self.project, self.project, output, 0, WIDTH, HEIGHT)
        self.assertEqual(len(frames), len(images))
        for frame in frames:
            self.assertEqual((output / frame['path']).read_bytes(), Path(frame['source']).read_bytes())
            self.assertTrue((output / frame['observations']).is_file())
            review = json.loads((output / frame['pixel_review']).read_text())
            self.assertEqual(review['nanite_draw_evidence'], not fail)

    def test_archiver_preserves_all_36_originals_and_observations(self): self.archive()
    def test_zero_draw_failure_still_preserves_all_36_originals(self): self.archive(True)
    def test_shader_failure_still_preserves_all_36_originals(self): self.archive('shader')
    def test_failed_final_proxy_still_archives_last_saved_original_and_sidecar(self): self.archive('partial')


if __name__ == '__main__': unittest.main()
