"""Regression tests for scripts/art/analyze_capture_luminance.py.

Run: python3 -m unittest scripts/art/test_analyze_capture_luminance.py

Synthetic PNGs in temporary capture-run folders cover:

* the built-in decoder against every PNG row filter;
* pairing within source groups: two groups with the same frame names give
  two pairs each, where the old basename key silently overwrote them;
* ambiguous duplicates reported and never paired;
* bare ``sm5``/``sm6`` folders and explicit ``LABEL=`` groups;
* ROIs, and the display-stop arithmetic.

Needs numpy only.
"""
from __future__ import annotations

import json
import struct
import sys
import tempfile
import unittest
import zlib
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_capture_luminance as A  # noqa: E402


def paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    return a if pa <= pb and pa <= pc else b if pb <= pc else c


def encode_png(pixels: np.ndarray, filters=(0, 1, 2, 3, 4)) -> bytes:
    """An 8-bit RGB PNG whose rows cycle through the given filter types."""
    h, w, _ = pixels.shape
    bpp, raw, prior = 3, bytearray(), bytes(w * 3)
    for row in range(h):
        line = pixels[row].astype(np.uint8).tobytes()
        kind = filters[row % len(filters)]
        out = bytearray([kind])
        for i, x in enumerate(line):
            a = line[i - bpp] if i >= bpp else 0
            b = prior[i]
            c = prior[i - bpp] if i >= bpp else 0
            pred = (0, a, b, (a + b) >> 1, paeth(a, b, c))[kind]
            out.append((x - pred) & 255)
        raw += out
        prior = line

    def chunk(tag, body):
        return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw))) + chunk(b"IEND", b""))


def frame(value: int, w=12, h=9) -> np.ndarray:
    return np.full((h, w, 3), value, dtype=np.uint8)


class Decoder(unittest.TestCase):
    def test_every_row_filter_round_trips(self):
        rng = np.random.default_rng(7)
        pixels = rng.integers(0, 256, size=(15, 11, 3), dtype=np.uint8)
        for filters in ((0,), (1,), (2,), (3,), (4,), (0, 1, 2, 3, 4)):
            with self.subTest(filters=filters):
                np.testing.assert_array_equal(A.decode_png(encode_png(pixels, filters)), pixels)


class Pairing(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def capture(self, run: str, source: str | None, frames: dict) -> Path:
        folder = self.base / run
        (folder / "frames").mkdir(parents=True)
        if source:
            (folder / "source-commit.txt").write_text(source + "\n")
        for name, value in frames.items():
            (folder / "frames" / name).write_bytes(encode_png(frame(value)))
        return folder

    def run_analyzer(self, *args):
        out_json = self.base / "out.json"
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = A.main([*map(str, args), "--json", str(out_json)])
        return code, json.loads(out_json.read_text()), err.getvalue()

    def test_two_source_groups_keep_all_four_pairs(self):
        runs = [self.capture("20261023T013710Z-sm6-1", "conventional", {"entry-Lit.png": 140, "ceiling-Lit.png": 60}),
                self.capture("20261023T013947Z-sm5-2", "conventional", {"entry-Lit.png": 150, "ceiling-Lit.png": 60}),
                self.capture("20261023T054521Z-sm6-3", "nanite", {"entry-Lit.png": 96, "ceiling-Lit.png": 59}),
                self.capture("20261023T054701Z-sm5-4", "nanite", {"entry-Lit.png": 96, "ceiling-Lit.png": 59})]
        code, result, _ = self.run_analyzer(*runs)
        self.assertEqual(code, 0)
        self.assertEqual(sorted((p["source_group"], p["frame"]) for p in result["pairs"]),
                         [("conventional", "ceiling-Lit.png"), ("conventional", "entry-Lit.png"),
                          ("nanite", "ceiling-Lit.png"), ("nanite", "entry-Lit.png")])
        conventional = next(p for p in result["pairs"] if p["source_group"] == "conventional" and p["frame"] == "entry-Lit.png")
        self.assertEqual((conventional["sm5"]["run"], conventional["sm6"]["run"]),
                         ("20261023T013947Z-sm5-2", "20261023T013710Z-sm6-1"))
        self.assertGreater(conventional["sm5_minus_sm6_display_stops"], 0)
        self.assertEqual(len(conventional["sm5"]["sha256"]), 64)

    def test_same_group_duplicates_are_ambiguous_not_overwritten(self):
        runs = [self.capture("A-sm6-1", "same", {"entry-Lit.png": 140}),
                self.capture("B-sm6-2", "same", {"entry-Lit.png": 120}),
                self.capture("C-sm5-3", "same", {"entry-Lit.png": 150})]
        code, result, err = self.run_analyzer(*runs)
        self.assertEqual(code, 2)
        self.assertEqual(result["pairs"], [])
        self.assertEqual(len(result["ambiguous"]), 1)
        self.assertEqual(len(result["ambiguous"][0]["files"]), 3)
        self.assertIn("AMBIGUOUS", err)

    def test_explicit_labels_and_bare_mode_folders(self):
        sm5 = self.capture("before/sm5", None, {"view.png": 100})
        sm6 = self.capture("before/sm6", None, {"view.png": 110})
        code, result, _ = self.run_analyzer(f"before={sm5}", f"before={sm6}")
        self.assertEqual(code, 0)
        self.assertEqual([(p["source_group"], p["frame"]) for p in result["pairs"]], [("before", "view.png")])
        self.assertEqual({r["mode"] for r in result["frames"]}, {"sm5", "sm6"})

    def test_unlabelled_frames_without_source_never_pair(self):
        code, result, _ = self.run_analyzer(self.capture("X-sm5-1", None, {"v.png": 90}),
                                            self.capture("Y-sm6-2", None, {"v.png": 90}))
        self.assertEqual((code, result["pairs"], result["ambiguous"]), (0, [], []))


class Measures(unittest.TestCase):
    def test_display_stops_and_rois(self):
        pixels = frame(64, w=20, h=10)
        pixels[:, 10:] = 192
        s = A.stats(pixels, {"left": [0.0, 0.0, 0.5, 1.0], "right": [0.5, 0.0, 1.0, 1.0]})
        left, right = s["rois"]["left"], s["rois"]["right"]
        self.assertAlmostEqual(left["luma_p50"], 64 / 255, places=3)
        self.assertAlmostEqual(right["luma_p50"], 192 / 255, places=3)
        expected = np.log2(A.to_linear(np.array(192 / 255)) / A.to_linear(np.array(64 / 255)))
        self.assertAlmostEqual(right["median_display_stops"] - left["median_display_stops"], float(expected), places=2)
        self.assertEqual(s["near_saturated_pct"], 0.0)
        with self.assertRaises(ValueError):
            A.stats(pixels, {"bad": [0.5, 0.0, 0.4, 1.0]})


if __name__ == "__main__":
    unittest.main()
