"""Source image integrity must reject bad pixels even with plausible headers."""
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

from PIL import Image, ImageFile

SPEC = importlib.util.spec_from_file_location("source_images", Path(__file__).with_name("validate_source_images.py"))
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


def chunk(kind, payload):
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))


class SourceImages(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="sora-source-images-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "Content/SourceArt"
        self.source.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)

    def image(self, name="texture.png", mode="RGB", **options):
        path = self.source / name
        Image.new(mode, (32, 17)).save(path, **options)
        return path

    def broken(self, name, data):
        path = self.source / name
        path.write_bytes(data)
        with self.assertRaises((ValueError, OSError, SyntaxError, struct.error, zlib.error)):
            GATE.check_image(path)
        self.assertEqual(path.read_bytes(), data, "validation must not repair the asset")

    def track(self, *paths):
        subprocess.run(["git", "-C", str(self.root), "add", "--", *map(str, paths)], check=True)

    def test_supported_png_modes_decode_including_alpha_palette_and_16bit(self):
        for mode in ("1", "L", "LA", "P", "RGB", "RGBA", "I;16"):
            with self.subTest(mode=mode):
                path = self.image(f"texture-{mode.replace(';', '-')}.png", mode)
                before = path.read_bytes()
                self.assertEqual(GATE.check_image(path), (32, 17))
                self.assertEqual(path.read_bytes(), before)

    def test_jpeg_baseline_progressive_and_grayscale_decode(self):
        for mode, progressive in (("RGB", False), ("RGB", True), ("L", False), ("CMYK", False)):
            with self.subTest(mode=mode, progressive=progressive):
                self.assertEqual(GATE.check_image(self.image("texture.jpg", mode, progressive=progressive)), (32, 17))
        self.assertEqual(GATE.check_image(self.image("texture.JPEG")), (32, 17))

    def test_header_only_truncated_chunk_and_missing_iend_rejected(self):
        data = self.image().read_bytes()
        for cut in (24, 33, len(data) - 13, len(data) - 12, len(data) - 1):
            with self.subTest(cut=cut):
                self.broken("truncated.png", data[:cut])

    def test_header_without_pixels_is_rejected_even_with_complete_iend(self):
        data = self.image().read_bytes()
        self.broken("no-pixels.png", data[:33] + chunk(b"IEND", b""))

    def test_every_chunk_crc_including_iend_is_checked(self):
        data = self.image().read_bytes()
        offsets = []
        at = 8
        while at < len(data):
            length = struct.unpack_from(">I", data, at)[0]
            offsets.append(at + length + 8)
            at += length + 12
        for crc in offsets:
            corrupted = bytearray(data)
            corrupted[crc] ^= 1
            with self.subTest(crc=crc):
                self.broken("crc.png", corrupted)

    def test_valid_crc_does_not_hide_invalid_or_incomplete_pixel_stream(self):
        header = self.image().read_bytes()[:33]
        for payload in (b"not a zlib stream", zlib.compress(b"\0"), zlib.compress(b"\0" + bytes(32 * 3))[:-2]):
            with self.subTest(payload=payload[:10]):
                self.broken("pixel-stream.png", header + chunk(b"IDAT", payload) + chunk(b"IEND", b""))

    def test_bad_row_filter_and_trailing_bytes_rejected(self):
        data = self.image().read_bytes()
        scanlines = (b"\5" + bytes(32 * 3)) * 17
        self.broken("filter.png", data[:33] + chunk(b"IDAT", zlib.compress(scanlines)) + chunk(b"IEND", b""))
        self.broken("trailing.png", data + b"incomplete extra chunk")

    def test_jpeg_truncation_is_rejected_even_if_caller_allows_it(self):
        data = self.image("texture.jpg").read_bytes()
        previous = ImageFile.LOAD_TRUNCATED_IMAGES
        ImageFile.LOAD_TRUNCATED_IMAGES = True
        try:
            self.broken("truncated.jpg", data[:-2])
            self.assertTrue(ImageFile.LOAD_TRUNCATED_IMAGES)
        finally:
            ImageFile.LOAD_TRUNCATED_IMAGES = previous
        self.broken("header.jpg", data[:100])

    def test_materialization_and_extension_mismatch_fail(self):
        self.broken("pointer.png", b"version https://git-lfs.github.com/spec/v1\noid sha256:123\nsize 100\n")
        self.broken("actually-png.jpg", self.image().read_bytes())

    def test_scan_covers_tracked_png_jpeg_only_and_keeps_all_failures(self):
        good = self.image()
        bad = self.source / "broken.png"
        bad.write_bytes(good.read_bytes()[:33])
        pointer = self.source / "missing.jpg"
        pointer.write_text("version https://git-lfs.github.com/spec/v1\n")
        hdr = self.source / "sky.hdr"
        hdr.write_bytes(b"outside this focused gate")
        untracked = self.source / "draft.png"
        untracked.write_bytes(b"untracked draft")
        self.track(good, bad, pointer, hdr)
        report = GATE.scan(self.root)
        self.assertEqual((report["checked"], report["passed"], report["status"]), (3, 1, "failed"))
        self.assertEqual([e["path"] for e in report["errors"]], ["Content/SourceArt/broken.png", "Content/SourceArt/missing.jpg"])
        self.assertIn("HDR", report["outside_scope"])

    def test_missing_tracked_image_is_an_error(self):
        image = self.image()
        self.track(image)
        image.unlink()
        report = GATE.scan(self.root)
        self.assertEqual(report["status"], "failed")
        self.assertIn("FileNotFoundError", report["errors"][0]["error"])

    def test_cli_returns_failure_and_machine_readable_file_evidence(self):
        image = self.image()
        self.track(image)
        image.write_bytes(image.read_bytes()[:-12])
        result = subprocess.run([sys.executable, str(Path(GATE.__file__)), "--root", str(self.root), "--json"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertEqual(report["errors"][0]["path"], "Content/SourceArt/texture.png")
        self.assertIn("end chunk", report["errors"][0]["error"])


if __name__ == "__main__":
    unittest.main()
