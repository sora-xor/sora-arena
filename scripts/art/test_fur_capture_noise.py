"""Tests for fur_capture_noise: the fur speckle measurement for the run-up comparison.

Run: python3 -m unittest scripts/art/test_fur_capture_noise.py
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fur_capture_noise as F  # noqa: E402


def frame(h=60, w=80, stave_grain=0.02):
    """A dark warm background, a white fur patch (rows 10-40, cols 10-40) and a black stave (cols 50-60) with a
    faint checker grain of ``stave_grain``, as lacquer has some."""
    img = np.zeros((h, w, 3))
    img[...] = (0.35, 0.25, 0.18)
    img[10:40, 10:40] = 0.8
    img[:, 50:60] = (0.03, 0.025, 0.02)
    yy, xx = np.mgrid[0:h, 50:60]
    img[:, 50:60] += (((yy + xx) % 2) * stave_grain)[..., None]
    ids = np.zeros((h, w, 3))
    ids[10:40, 10:40] = (0.0, 0.0, 1.0)
    ids[:, 50:60] = (1.0, 0.0, 0.0)
    return img, ids


def speckle(img, rng, amount=0.12):
    """Dither-like salt noise on the fur patch only."""
    out = img.copy()
    noise = (rng.random((30, 30)) < 0.3) * amount
    out[10:40, 10:40] -= noise[..., None]
    return out


class Measure(unittest.TestCase):
    def test_speckled_fur_reads_noisier_than_smooth_fur(self):
        img, ids = frame()
        smooth = F.hold_noise(img, ids)
        noisy = F.hold_noise(speckle(img, np.random.default_rng(3)), ids)
        self.assertLess(smooth["fur"]["residual_mean"], 1e-9)
        self.assertGreater(noisy["fur"]["residual_mean"], 0.01)
        self.assertGreater(noisy["fur_over_bow"], smooth.get("fur_over_bow", 0.0))

    def test_only_bright_unsaturated_pixels_in_the_paw_class_count(self):
        img, ids = frame()
        r = F.hold_noise(img, ids)
        self.assertEqual(r["fur"]["pixels"], (30 - 2 * F.ERODE_PX) ** 2)    # eroded, the stave and ground excluded
        self.assertEqual(r["bow"]["pixels"], 60 * 8 - 2 * 8)                # eroded by 1, at the image edges too

    def test_a_perfectly_smooth_control_gives_no_ratio(self):
        img, ids = frame(stave_grain=0.0)
        r = F.hold_noise(speckle(img, np.random.default_rng(5)), ids)
        self.assertNotIn("fur_over_bow", r)
        self.assertEqual(r["bow"]["residual_mean"], 0.0)

    def test_a_camera_hold_has_no_control(self):
        img, _ids = frame()
        r = F.hold_noise(img)
        self.assertNotIn("bow", r)
        self.assertGreater(r["fur"]["pixels"], 0)


# A manifest's records as render_yumi_fp_review writes them, cut down: every value the comparisons test is real.
MATERIALS = {"/Game/Bow": {"slots": [{"index": 0, "slot": "M_Bow", "material": "/Game/MI_Bow"}],
                           "component": [{"index": 0, "material": "/Game/MI_Bow"}]},
             "/Game/Generated/Qualification/NyaakotoFPPaws/SM_Paw": {
                 "slots": [{"index": 0, "slot": "M_NyaakotoFP_FurSkin",
                            "material": "/Game/Generated/Qualification/NyaakotoFPPaws/M_NyaakotoFP_FurSkin.M_NyaakotoFP_FurSkin"},
                           {"index": 1, "slot": "M_NyaakotoFP_FurCards",
                            "material": "/Game/Generated/Qualification/NyaakotoFPPaws/M_NyaakotoFP_FurCards.M_NyaakotoFP_FurCards"}],
                 "component": [{"index": 0, "material": "/Game/Generated/Qualification/NyaakotoFPPaws/M_NyaakotoFP_FurSkin.M_NyaakotoFP_FurSkin"},
                               {"index": 1, "material": "/Game/Generated/Qualification/NyaakotoFPPaws/M_NyaakotoFP_FurCards.M_NyaakotoFP_FurCards"}]}}


def paw_materials(slot1="M_NyaakotoFP_FurShells", material1=None, slot0="M_NyaakotoFP_FurSkin"):
    """MATERIALS with the paw's two slots as given (slot 1 bound to its own material unless material1)."""
    ns = "/Game/Generated/Qualification/NyaakotoFPPaws/"
    m1 = material1 or f"{ns}{slot1}.{slot1}"
    m0 = f"{ns}{slot0}.{slot0}"
    paw = {"slots": [{"index": 0, "slot": slot0, "material": m0}, {"index": 1, "slot": slot1, "material": m1}],
           "component": [{"index": 0, "material": m0}, {"index": 1, "material": m1}]}
    return dict(MATERIALS, **{f"{ns}SM_Paw": paw})
CAMERA = {"field_of_view_deg": 70.0, "aspect_ratio": 1.3333, "constrain_aspect_ratio": True,
          "location_cm": [0.0, 0.0, 0.0], "rotation_deg": [0.0, 0.0, 0.0], "resolution": [80, 60]}
SETUP = {"fov": 70.0, "mesh_scale": 0.75,
         "holds": {"rest": {"anchor": [45, -15, -12], "rot": [0, 0, 0], "draw": 0.0},
                   "paw": {"anchor": [60, -3, -9.5], "rot": [0, 0, 0], "draw": 1.0, "camera": {"fov": 32.0}}},
         "sockets_cm": {"rest": {"Grip_R": [1.0, 2.0, 3.0]}, "paw": {"Grip_R": [1.0, 2.0, 3.5]}},
         "poses_component_cm": {"rest": {"bound_cm": 0.02}, "paw": {"bound_cm": 0.02}},
         "materials": MATERIALS, "materials_after_id_pass": {"rest": MATERIALS},
         "solved": {}, "id_colours": {"bow": [1.0, 0.0, 0.0]}, "control": {"source_sha256": "c"},
         "study": {"sha256": "s"}, "requested_holds": ["rest", "paw"], "ids_enabled": True, "eye_view_holds": ["rest"],
         "resolution": [80, 60], "cameras": {"rest": CAMERA, "paw": dict(CAMERA, field_of_view_deg=32.0)},
         "assessment_camera": {"reticle_clear_radius": 0.12},
         "set_materials": {"floor": ["M_Floor", [0.09, 0.055, 0.035], 0.22]}, "sun": {"lux": 20000.0},
         "ev100": 12.97, "exposure_bias": -11.97,
         "assets_sha256": {"Content/Generated/Qualification/NyaakotoFPPaws/SM_Paw.uasset": "a" * 64,
                           "Content/Generated/Qualification/W18YumiRig/SK_Weapon_18.uasset": "b" * 64}}


def setup(**changes):
    """A deep copy of SETUP with dotted-path changes (None deletes), as override= for write_run."""
    import copy

    out = copy.deepcopy(SETUP)
    for path, value in changes.items():
        *parents, key = path.split(".")
        node = out
        for k in parents:
            node = node[k]
        if value is None:
            del node[key]
        else:
            node[key] = value
    return out


def write_run(root, name="run", runup=4, speckled=True, tamper=False, base=None, **override):
    """A capture directory like render_yumi_fp_review's: rest (eye view, with its ID image) and paw (camera).
    base replaces SETUP (keys it lacks stay absent); override sets top-level keys."""
    from PIL import Image

    run = Path(root) / name
    run.mkdir()
    img, ids = frame()
    lit = speckle(img, np.random.default_rng(1)) if speckled else img
    files = {}
    for fname, a in (("rest.png", lit), ("rest_ids.png", ids), ("paw.png", lit)):
        Image.fromarray((np.clip(a, 0, 1) * 255).round().astype(np.uint8)).save(run / fname)
        files[fname] = hashlib.sha256((run / fname).read_bytes()).hexdigest()
    if tamper:
        files["paw.png"] = "0" * 64
    manifest = dict(SETUP if base is None else base, files=files, id_files={"rest": "rest_ids.png"},
                    highres_runup={"r.HighResScreenshotDelay": runup}, level=f"/Game/L_{name}")
    manifest.update(override)
    (run / "manifest.json").write_text(json.dumps(manifest))
    return run


class Run(unittest.TestCase):
    def test_a_run_is_measured_per_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = F.run_noise(write_run(tmp))
            self.assertEqual(sorted(r["holds"]), ["paw", "rest"])
            self.assertIn("fur_over_bow", r["holds"]["rest"])
            self.assertEqual(r["highres_runup"], {"r.HighResScreenshotDelay": 4})

    def test_a_file_unlike_its_manifest_hash_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(F.NoiseError):
                F.run_noise(write_run(tmp, tamper=True))

    def test_empty_or_invalid_requested_holds_fail_rather_than_measure_nothing(self):
        for bad in ([], None, "rest", ["rest", "rest"], ["rest", 3], [""]):
            with self.subTest(requested_holds=bad), tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(F.NoiseError) as cm:
                    F.run_noise(write_run(tmp, requested_holds=bad))
                self.assertIn("requested_holds", str(cm.exception))

    def test_eye_view_holds_must_be_requested(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(F.NoiseError):
                F.run_noise(write_run(tmp, eye_view_holds=["rest", "root"]))

    def test_an_eye_view_hold_without_its_id_image_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(F.NoiseError) as cm:
                F.run_noise(write_run(tmp, id_files={}))
            self.assertIn("rest: an eye-view hold with no ID image", str(cm.exception))

    def test_eye_view_holds_need_the_id_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(F.NoiseError) as cm:
                F.run_noise(write_run(tmp, ids_enabled=False))
            self.assertIn("ids_enabled", str(cm.exception))

    def test_the_command_never_overwrites_its_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = write_run(tmp)
            out = Path(tmp) / "noise.json"
            self.assertEqual(F.main([str(run), "--out", str(out)]), 0)
            self.assertEqual(F.main([str(run), "--out", str(out)]), 1)

    def test_the_command_takes_one_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = write_run(tmp)
            out = Path(tmp) / "noise.json"
            self.assertEqual(F.main(["--out", str(out)]), 1)
            self.assertEqual(F.main([str(run), "--compare", str(run), str(run), "--out", str(out)]), 1)


class Compare(unittest.TestCase):
    def test_both_runs_are_measured_on_their_common_region(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = write_run(tmp, "runup4", runup=4, speckled=True)
            smooth = write_run(tmp, "auto", runup=32, speckled=False)
            r = F.compare_runs(raw, smooth)
            self.assertFalse(r["same_runup"])
            h = r["holds"]["rest"]
            self.assertGreater(h["common_pixels"], 0)
            self.assertEqual(h["a_on_common"]["pixels"], h["b_on_common"]["pixels"])        # one region for both
            self.assertGreater(h["a_on_common"]["residual_mean"], h["b_on_common"]["residual_mean"])
            for side in ("a", "b"):                                    # and each run's own selection, reported apart
                self.assertIn("pixels", h[side]["fur"])

    def test_runs_set_up_differently_are_refused(self):
        for key, value in (("ev100", 12.0), ("cameras", {"rest": {"fov": 60}}), ("holds", {"rest": {}})):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as tmp:
                a = write_run(tmp, "a", runup=4)
                b = write_run(tmp, "b", runup=32, **{key: value})
                with self.assertRaises(F.NoiseError) as cm:
                    F.compare_runs(a, b)
                self.assertIn(key, str(cm.exception))

    def test_the_command_compares(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = write_run(tmp, "a", runup=4), write_run(tmp, "b", runup=32, speckled=False)
            out = Path(tmp) / "compare.json"
            self.assertEqual(F.main(["--compare", str(a), str(b), "--out", str(out)]), 0)
            self.assertTrue(json.loads(out.read_text())["compare"])

    def test_a_controlled_run_binds_its_assets_by_content(self):
        # Root's review of capture v6: matching setups and material paths accepted v5 and v6, whose paw bytes differ.
        changed = setup()
        changed["assets_sha256"]["Content/Generated/Qualification/NyaakotoFPPaws/SM_Paw.uasset"] = "c" * 64
        with tempfile.TemporaryDirectory() as tmp:
            a = write_run(tmp, "a", runup=4)
            b = write_run(tmp, "b", runup=32, speckled=False, base=changed)
            with self.assertRaises(F.NoiseError) as cm:
                F.compare_runs(a, b)
            self.assertIn("assets_sha256", str(cm.exception))
        with tempfile.TemporaryDirectory() as tmp:                     # runs from before the binding
            a = write_run(tmp, "a", runup=4, base=setup(assets_sha256=None))
            b = write_run(tmp, "b", runup=32, speckled=False, base=setup(assets_sha256=None))
            with self.assertRaises(F.NoiseError) as cm:
                F.compare_runs(a, b)
            self.assertIn("no assets_sha256", str(cm.exception))

    def test_a_key_absent_from_both_runs_is_no_match(self):
        # As --assets (root's review of 148c5c1): an absent key, or an intact post-ID readback missing from both.
        for case, change, needle in (("ev100 deleted from both", {"ev100": None}, "ev100"),
                                     ("post-ID readback emptied in both", {"materials_after_id_pass.rest": {}},
                                      "materials_after_id_pass[rest]"),
                                     ("cameras[rest] deleted from both", {"cameras.rest": None}, "cameras[rest]")):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                a = write_run(tmp, "a", runup=4, base=setup(**change))
                b = write_run(tmp, "b", runup=32, base=setup(**change), speckled=False)
                with self.assertRaises(F.NoiseError) as cm:
                    F.compare_runs(a, b)
                self.assertIn(needle, str(cm.exception))


class Assets(unittest.TestCase):
    def test_two_assets_are_measured_on_their_common_region(self):
        with tempfile.TemporaryDirectory() as tmp:
            before, after = write_run(tmp, "before"), write_run(tmp, "after", speckled=False)
            r = F.compare_assets(before, after)
            self.assertEqual(sorted(r["holds"]), ["paw", "rest"])
            h = r["holds"]["rest"]
            self.assertEqual(h["a_on_common"]["pixels"], h["b_on_common"]["pixels"])
            self.assertGreater(h["a_on_common"]["residual_mean"], h["b_on_common"]["residual_mean"])
            self.assertTrue(r["study_same"])

    def test_a_hold_solved_in_another_order_is_the_same_hold(self):
        # v5 solved right_cheek_clear first and v4 fourth: its values differ by about 1e-12 cm.
        with tempfile.TemporaryDirectory() as tmp:
            a = write_run(tmp, "a")
            b = write_run(tmp, "b", base=setup(**{"holds.rest.anchor": [45 + 2e-12, -15, -12]}), study={"sha256": "t"})
            r = F.compare_assets(a, b)
            self.assertFalse(r["study_same"])

    def test_a_different_setup_is_refused(self):
        for key, change in (("ev100", {"ev100": 12.0}), ("highres_runup", None),
                            ("cameras", {"cameras.rest.field_of_view_deg": 60.0}),
                            ("holds", {"holds.rest.anchor": [45.001, -15, -12]})):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as tmp:
                a = write_run(tmp, "a")
                b = write_run(tmp, "b", runup=32) if change is None else write_run(tmp, "b", base=setup(**change))
                with self.assertRaises(F.NoiseError) as cm:
                    F.compare_assets(a, b)
                self.assertIn(key, str(cm.exception))

    def test_only_the_holds_both_ran_are_compared(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = write_run(tmp, "a")
            b = write_run(tmp, "b", requested_holds=["rest"])
            self.assertEqual(sorted(F.compare_assets(a, b)["holds"]), ["rest"])
            c = write_run(tmp, "c", requested_holds=["paw"], eye_view_holds=[], materials_after_id_pass={})
            d = write_run(tmp, "d", requested_holds=["rest"])
            with self.assertRaises(F.NoiseError):
                F.compare_assets(c, d)

    def test_root_review_of_148c5c1_four_malformed_copies_are_refused(self):
        # Root's probes (art-148c5c1-comparator-review): each was accepted before this check.
        cases = {
            "cameras[rest] deleted from both": ({"cameras.rest": None}, {"cameras.rest": None}, "cameras[rest]"),
            "B's eye_view_holds empty": ({}, {"eye_view_holds": []}, "ID policy"),
            "B's post-ID readback emptied": ({}, {"materials_after_id_pass.rest": {}}, "materials_after_id_pass[rest]"),
            "ev100 deleted from both": ({"ev100": None}, {"ev100": None}, "ev100"),
        }
        for case, (ca, cb, needle) in cases.items():
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                a = write_run(tmp, "a", base=setup(**ca))
                b = write_run(tmp, "b", base=setup(**cb), speckled=False)
                with self.assertRaises(F.NoiseError) as cm:
                    F.compare_assets(a, b)
                self.assertIn(needle, str(cm.exception))

    def test_an_invalid_value_is_no_match_for_itself(self):
        for key, value in (("ev100", float("nan")), ("fov", -70.0), ("resolution", [80, 0]), ("sun", {})):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as tmp:
                a = write_run(tmp, "a", **{key: value})
                b = write_run(tmp, "b", speckled=False, **{key: value})
                with self.assertRaises(F.NoiseError) as cm:
                    F.compare_assets(a, b)
                self.assertIn(key, str(cm.exception))

    def test_a_post_id_readback_unlike_its_runs_own_is_refused(self):
        other = {"/Game/Bow": {"slots": [{"index": 0, "slot": "M_Bow", "material": "/Game/MI_Bow"}],
                               "component": [{"index": 0, "material": "/Engine/WorldGridMaterial"}]}}
        with tempfile.TemporaryDirectory() as tmp:
            a = write_run(tmp, "a")
            b = write_run(tmp, "b", base=setup(**{"materials_after_id_pass.rest": other}), speckled=False)
            with self.assertRaises(F.NoiseError) as cm:
                F.compare_assets(a, b)
            self.assertIn("materials_after_id_pass[rest]", str(cm.exception))

    def test_it_names_the_assets_that_differ_where_both_runs_bind_them(self):
        paw = "Content/Generated/Qualification/NyaakotoFPPaws/SM_Paw.uasset"
        changed = setup()
        changed["assets_sha256"][paw] = "c" * 64
        with tempfile.TemporaryDirectory() as tmp:
            a = write_run(tmp, "a")
            b = write_run(tmp, "b", speckled=False, base=changed)
            self.assertEqual(F.compare_assets(a, b)["assets"], {"bound": True, "differ": [paw]})
            c = write_run(tmp, "c", speckled=False, base=setup(assets_sha256=None))
            self.assertFalse(F.compare_assets(a, c)["assets"]["bound"])

    def test_only_the_enumerated_paw_slot_change_is_permitted(self):
        # Fur v6 replaced the cards' slot with the shells' (PERMITTED_PAW_SLOTS); nothing else may differ.
        def run(tmp, name, mats):
            return write_run(tmp, name, speckled=False, materials=mats, materials_after_id_pass={"rest": mats})

        with tempfile.TemporaryDirectory() as tmp:
            a = write_run(tmp, "a")
            r = F.compare_assets(a, run(tmp, "shells", paw_materials()))
            self.assertEqual(r["paw_material_changes"], [{"asset": "/Game/Generated/Qualification/NyaakotoFPPaws/SM_Paw",
                                                          "index": 1, "a": "M_NyaakotoFP_FurCards",
                                                          "b": "M_NyaakotoFP_FurShells"}])
            refused = {
                "another slot name": paw_materials(slot1="M_NyaakotoFP_Fins"),
                "the shells' slot on another material": paw_materials(material1="/Engine/WorldGridMaterial"),
                "a second paw slot changed": paw_materials(slot0="M_NyaakotoFP_SkinB"),
            }
            for case, mats in refused.items():
                with self.subTest(case=case):
                    with self.assertRaises(F.NoiseError) as cm:
                        F.compare_assets(a, run(tmp, case.replace(" ", "_").replace("'", ""), mats))
                    self.assertIn("not a permitted change", str(cm.exception))
            bow = {"slots": [{"index": 0, "slot": "M_Bow", "material": "/Game/MI_Other"}],
                   "component": [{"index": 0, "material": "/Game/MI_Other"}]}
            with self.assertRaises(F.NoiseError) as cm:
                F.compare_assets(a, run(tmp, "bow", dict(MATERIALS, **{"/Game/Bow": bow})))
            self.assertIn("other than the paw's", str(cm.exception))

    def test_the_controlled_mode_permits_no_slot_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = write_run(tmp, "a", runup=4)
            mats = paw_materials()
            b = write_run(tmp, "b", runup=32, speckled=False, materials=mats, materials_after_id_pass={"rest": mats})
            with self.assertRaises(F.NoiseError) as cm:
                F.compare_runs(a, b)
            self.assertIn("materials", str(cm.exception))

    def test_the_command_compares_assets_and_takes_one_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = write_run(tmp, "a"), write_run(tmp, "b", speckled=False)
            out = Path(tmp) / "assets.json"
            self.assertEqual(F.main(["--assets", str(a), str(b), "--out", str(out)]), 0)
            self.assertTrue(json.loads(out.read_text())["compare_assets"])
            self.assertEqual(F.main(["--assets", str(a), str(b), "--compare", str(a), str(b), "--out",
                                     str(Path(tmp) / "x.json")]), 1)


if __name__ == "__main__":
    unittest.main()
