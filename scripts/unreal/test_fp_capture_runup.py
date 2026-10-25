"""Host tests: the first-person capture sets HighResShot's run-up from TSR's history, and records it.

Run: python3 -m unittest scripts/unreal/test_fp_capture_runup.py

A candidate cause of capture v3's speckled fur was HighResShot's default
four-frame run-up, too short for TSR to resolve dithered coverage
(render_yumi_fp_review.highres_runup). Capture v4's controlled comparison
did not support it in that pair. These pin that the capture sets
r.HighResScreenshotDelay from r.TSR.History.SampleCount (or to an explicit
runup=<n> for a controlled comparison), and that its manifest records the
values, as v4's two runs did. The engine part pins the installed source the
reasoning rests on, and is skipped where the engine source is not installed.
"""
from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAPTURE = HERE / "render_yumi_fp_review.py"
ENGINE = Path("/Users/Shared/Epic Games/UE_5.8/Engine")
CLIENT = ENGINE / "Source/Runtime/Engine/Private/UnrealClient.cpp"
CONSOLE = ENGINE / "Source/Runtime/Core/Private/HAL/ConsoleManager.cpp"
TSR = ENGINE / "Source/Runtime/Renderer/Private/PostProcess/TemporalSuperResolution.cpp"


def collapsed(path):
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8", errors="replace"))


class Capture(unittest.TestCase):
    text = CAPTURE.read_text(encoding="utf-8")
    tree = ast.parse(text)

    def test_main_sets_the_runup_from_its_option_and_the_manifest_records_it(self):
        main = next(n for n in ast.walk(self.tree) if isinstance(n, ast.FunctionDef) and n.name == "main")
        src = ast.get_source_segment(self.text, main)
        self.assertIn('runup = highres_runup(opts["runup"])', src)
        self.assertIn('"highres_runup": runup,', src)

    def test_the_runup_reads_tsr_and_reads_back_what_it_set(self):
        fn = next(n for n in ast.walk(self.tree) if isinstance(n, ast.FunctionDef) and n.name == "highres_runup")
        src = ast.get_source_segment(self.text, fn)
        for needle in ('get_console_variable_float_value("r.TSR.History.SampleCount")',
                       'f"r.HighResScreenshotDelay {frames}"',
                       'get_console_variable_int_value("r.HighResScreenshotDelay")',
                       "RUNUP_PER_HISTORY_SAMPLE * samples"):
            self.assertIn(needle, src)

    def test_the_default_is_auto(self):
        self.assertIn('"runup": "auto"', self.text)


@unittest.skipUnless(CLIENT.is_file(), "the UE 5.8 engine source is not installed")
class Engine(unittest.TestCase):
    def test_highres_shots_run_up_for_the_delay_into_their_own_viewport(self):
        text = collapsed(CLIENT)
        self.assertIn('FindTConsoleVariableDataInt(TEXT("r.HighResScreenshotDelay"));', text)
        self.assertIn("const uint32 DefaultScreenshotDelay = 4;", text)
        self.assertIn("while (FrameDelay) { HighResScreenshotBeginFrame(DummyViewport.Get());", text)

    def test_the_delay_defaults_to_four_frames(self):
        self.assertIn('TEXT("r.HighResScreenshotDelay"), 4,', collapsed(CONSOLE))

    def test_tsr_keeps_sixteen_history_samples_by_default(self):
        self.assertIn('TEXT("r.TSR.History.SampleCount"), 16.0f,', collapsed(TSR))


if __name__ == "__main__":
    unittest.main()
