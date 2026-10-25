"""Tests for measure_fp_fur_cost's engine-free parts: the CSV profile reader and the PNG size.

Run: python3 -m unittest scripts/unreal/test_measure_fp_fur_cost.py

- csv_summary keeps the GPU and thread-time columns, takes their median and
  quartiles over the frames, skips cells that are not numbers, and stops at
  the trailing metadata row (a CSV profile repeats its header after it).
- png_size reads a PNG's IHDR and refuses anything else.
"""
from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import measure_fp_fur_cost as M  # noqa: E402

CSV = ("EVENTS,FrameTime,GameThreadTime,GPU/Total,GPU/Translucency,DrawCall/Opaque,Other\n"
       ",16.0,5.0,4.0,1.0,10,a\n"
       "Exclude,18.0,6.0,5.0,1.5,11,b\n"
       ",17.0,5.5,4.5,,12,c\n"
       ",15.0,4.5,3.5,0.5,13,d\n"
       "[HasHeaderRowAtEnd],1,[platform],Mac\n"
       "EVENTS,FrameTime,GameThreadTime,GPU/Total,GPU/Translucency,DrawCall/Opaque,Other\n")


class Summary(unittest.TestCase):
    def test_gpu_and_thread_columns_by_frame(self):
        s = M.csv_summary(CSV)
        self.assertEqual(s["frames"], 4)
        self.assertEqual(s["columns_total"], 7)
        self.assertEqual(s["columns"], ["FrameTime", "GameThreadTime", "GPU/Total", "GPU/Translucency"])
        self.assertEqual(s["stats"]["GPU/Total"]["median"], 4.25)
        self.assertEqual(s["stats"]["GPU/Total"]["n"], 4)
        self.assertEqual(s["stats"]["GPU/Translucency"]["n"], 3)          # the empty cell is skipped
        self.assertEqual(s["stats"]["GPU/Translucency"]["median"], 1.0)
        self.assertLessEqual(s["stats"]["FrameTime"]["p25"], s["stats"]["FrameTime"]["median"])
        self.assertLessEqual(s["stats"]["FrameTime"]["median"], s["stats"]["FrameTime"]["p75"])
        self.assertNotIn("Other", s["stats"])

    def test_an_empty_profile(self):
        self.assertEqual(M.csv_summary("")["frames"], 0)


class PngSize(unittest.TestCase):
    def test_reads_the_ihdr(self):
        from PIL import Image

        buf = io.BytesIO()
        Image.new("RGB", (37, 21)).save(buf, "PNG")
        self.assertEqual(M.png_size(buf.getvalue()[:32]), (37, 21))
        with self.assertRaises(ValueError):
            M.png_size(b"GIF89a" + bytes(26))


if __name__ == "__main__":
    unittest.main()
