#!/usr/bin/env python3
"""Decode every tracked source PNG/JPEG; independent of ledger/hash admission.

Pillow is pinned by qualification/source-checks-requirements.txt. PNGs also
use the rendered-capture gate's CRC/IEND and complete DEFLATE/scanline check.
HDR, SVG and other source formats are outside this focused image gate.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageFile

ROOT = Path(__file__).resolve().parents[2]
FORMATS = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG"}
SPEC = importlib.util.spec_from_file_location(
    "sora_capture_png_integrity", ROOT / "scripts/toolchain/verify-capture-report.py")
CAPTURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CAPTURE)


def check_image(path: Path) -> tuple[int, int]:
    """Read only: validate framing/checksums, then decode every image pixel."""
    expected = FORMATS.get(path.suffix.lower())
    if expected is None:
        raise ValueError(f"unsupported source image format: {path.suffix}")
    with path.open("rb") as stream:
        if stream.read(64).startswith(b"version https://git-lfs.github.com/spec/v1"):
            raise ValueError("Git LFS pointer is not materialized")
    size = CAPTURE.png_dimensions(path.read_bytes()) if expected == "PNG" else None
    # Never inherit permissive truncation settings from another Python caller.
    # This gate is sequential; restore the caller's option when it returns.
    previous = ImageFile.LOAD_TRUNCATED_IMAGES
    ImageFile.LOAD_TRUNCATED_IMAGES = False
    try:
        with Image.open(path, formats=[expected]) as image:
            if image.format != expected:
                raise ValueError(f"file extension expects {expected}, found {image.format}")
            image.load()
            if size is not None and image.size != size:
                raise ValueError("decoded dimensions differ from PNG header")
            return image.size
    finally:
        ImageFile.LOAD_TRUNCATED_IMAGES = previous


def scan(root: Path) -> dict:
    """Inspect tracked source files, including missing/unmaterialized images."""
    tracked = subprocess.check_output(
        ["git", "-C", str(root), "ls-files", "-z", "--", "Content/SourceArt"],
        text=True).split("\0")
    images = sorted(p for p in tracked if Path(p).suffix.lower() in FORMATS)
    errors = []
    for relative in images:
        try:
            check_image(root / relative)
        except Exception as error:
            errors.append({"path": relative, "error": f"{type(error).__name__}: {error}"})
    return {
        "scope": "tracked Content/SourceArt PNG/JPEG integrity; no asset provenance or visual-quality approval",
        "outside_scope": "HDR, SVG and other source formats; existing source-content and asset-ledger gates remain independent",
        "checked": len(images), "passed": len(images) - len(errors), "errors": errors,
        "status": "failed" if errors else "passed",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="read-only checkout to inspect")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = scan(args.root.resolve())
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for error in report["errors"]:
            print(f'{error["path"]}: {error["error"]}', file=sys.stderr)
        print(f'Source PNG/JPEG integrity: {report["passed"]}/{report["checked"]} passed; '
              f'{len(report["errors"])} failed. HDR/SVG outside scope.')
    return int(report["status"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
