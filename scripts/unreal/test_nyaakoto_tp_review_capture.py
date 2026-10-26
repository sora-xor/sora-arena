"""Host tests: render_nyaakoto_tp_review.py binds the game's materials, poses clips, and exits as it must.

Run: python3 -m unittest scripts/unreal/test_nyaakoto_tp_review_capture.py

The capture needs Unreal, so these read its source:
- **The material binding** is SoraCharacterBase::BuildCat's own rule, read from the game source here: the slot name's
  M_Hero_ prefix becomes MI_Nyaakoto_ under /Game/Generated/Characters/Nyaakoto.
- **A clip change** goes through SetAnimation. OverrideAnimationData keeps a single-node instance's asset.
- **The exit** releases the keep-alive and never calls quit_editor (the exit hang, EDITOR_EXIT_HANG.md).
- **The image settings** are set and read back: r.ScreenPercentage 100, texture streaming off, the run-up from TSR's
  history.
- **A failure** leaves manifest.partial.json.
"""
from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAPTURE = HERE / "render_nyaakoto_tp_review.py"
GAME = HERE.parents[1] / "Source/SoraArena/Private/Characters/SoraCharacterBase.cpp"


class Capture(unittest.TestCase):
    text = CAPTURE.read_text(encoding="utf-8")
    tree = ast.parse(text)

    def function(self, name):
        node = next(n for n in ast.walk(self.tree) if isinstance(n, ast.FunctionDef) and n.name == name)
        return ast.get_source_segment(self.text, node)

    def test_the_binding_is_the_games(self):
        game = GAME.read_text(encoding="utf-8")
        self.assertIn('TEXT("MI_Nyaakoto_")+Slot.RightChop(7)', game)
        self.assertIn('/Game/Generated/Characters/Nyaakoto/%s.%s', game)
        self.assertIn('Slot.StartsWith(TEXT("M_Hero_"))', game)
        src = self.function("bind_game_materials")
        self.assertIn('"MI_Nyaakoto_" + name[len("M_Hero_"):]', src)
        self.assertIn('f"{MATERIALS}/{inst}.{inst}"', src)
        self.assertIn('MATERIALS = "/Game/Generated/Characters/Nyaakoto"', self.text)
        self.assertIn("self.comp.set_material(i, mi)", src)

    def test_every_shot_is_gated_before_and_after(self):
        step = self.function("main")
        self.assertIn('ch.check_materials(f"before {shot[\'name\']}")', step)
        self.assertIn('gates = ch.check_state(status["want"])', step)
        self.assertIn('["gates_after"] = ch.check_state(status["want"])', step)

    def test_a_clip_change_sets_the_instances_asset(self):
        src = self.function("set_state")
        self.assertLess(src.index("self.comp.set_animation("), src.index("self.comp.override_animation_data("))
        self.assertIn("self.comp.set_forced_lod(lod + 1)", src)
        self.assertIn("self.comp.set_morph_target(name, weight, False)", src)

    def test_the_exit_releases_the_keep_alive_and_never_quits_from_slate(self):
        self.assertNotIn("quit_editor(", re.sub(r"#.*", "", self.text))
        src = self.function("main")
        self.assertIn("unreal.EditorPythonScripting.set_keep_python_script_alive(False)", src)
        self.assertIn('write_manifest("manifest.partial.json")', src)

    def test_the_image_settings_are_set_and_read_back(self):
        src = self.function("build_level")
        self.assertIn('("r.ScreenPercentage 100", "r.ScreenPercentage", 100.0)', src)
        self.assertIn('("r.TextureStreaming 0", "r.TextureStreaming", 0.0)', src)
        self.assertIn('runup = highres_runup(opts["runup"])', self.function("main"))
        self.assertIn('get_console_variable_int_value("r.HighResScreenshotDelay")', self.function("highres_runup"))

    def test_originals_go_to_a_new_folder(self):
        src = self.function("main")
        self.assertIn("if out.exists():", src)
        self.assertIn("out.mkdir(parents=True)", src)


if __name__ == "__main__":
    unittest.main()
