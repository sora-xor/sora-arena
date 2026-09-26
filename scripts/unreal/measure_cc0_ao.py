"""Measure the distributions the CC0 library's height blend and puddles rank against.

Host tool; writes ``scripts/unreal/cc0_ao_ranks.json``. Rerun it when a
measured source changes: ``cc0_environment_library.build_plan`` refuses a file
measured from other bytes.

A height blend puts layer B on a share of the surface and puddles fill the
lowest share of the ground, so both need the rank of a pixel's value, not the
value: scanned AO maps sit in narrow, scan-specific bands (white plaster's AO
is above 0.4 almost everywhere, clay plaster's near 0.97), and an absolute
threshold that shows one scan's crevices covers none or all of another. For
every set whose instance reads its AO rank (``needs_ao_ranks``) this measures
the red (AO) channel of the ARM source at full resolution, as the linear values
Unreal samples (PNG/JPEG through Pillow, OpenEXR through Blender), into
``BINS`` bins, and records the AO value at each of ``cc0_environment_hlsl.RANKS``
(rank 0 and 1 at the ``RANK_TAILS`` quantiles). The Custom HLSL turns a sampled
AO value back into its rank by that piecewise-linear curve.

The macro-variation term is measured the same way from the engine's own
``T_Default_MacroVariation`` (sRGB): its source PNG is read out of the pinned
engine's package, and the finish node averages its red and green channels
sampled at two unrelated scales, so their distribution is the convolution of
the two channels'. Its knots are constants in ``cc0_environment_hlsl``.

    python3 scripts/unreal/measure_cc0_ao.py
"""

from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cc0_environment_library as library  # noqa: E402
from cc0_environment_hlsl import RANKS  # noqa: E402
from sora_engine_pin import PIN, require_engine_root  # noqa: E402

BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")
MACRO_PACKAGE = "Engine/Content/EngineMaterials/T_Default_MacroVariation.uasset"
BINS = library.AO_BINS

# Run inside Blender: the red channel histogram of each EXR (argv after "--": bins, output, paths...).
BLENDER_HISTOGRAM = """
import bpy, json, sys
import numpy as np
args = sys.argv[sys.argv.index("--") + 1:]
bins, output, paths = int(args[0]), args[1], args[2:]
result = {}
for path in paths:
    image = bpy.data.images.load(path)
    image.colorspace_settings.name = "Non-Color"
    width, height = image.size
    pixels = np.empty(width * height * image.channels, dtype=np.float32)
    image.pixels.foreach_get(pixels)
    red = pixels[0::image.channels].astype(np.float64)
    counts = np.bincount(np.clip(np.floor(red * bins), 0, bins - 1).astype(np.int64), minlength=bins)
    result[path] = {"size": [width, height], "counts": counts.tolist(), "float": bool(image.is_float)}
    bpy.data.images.remove(image)
with open(output, "w") as stream:
    json.dump(result, stream)
"""


def bin_counts(values: np.ndarray) -> np.ndarray:
    return np.bincount(np.clip(np.floor(values * BINS), 0, BINS - 1).astype(np.int64), minlength=BINS)


def pillow_red(path: Path) -> tuple[np.ndarray, tuple[int, int]]:
    image = Image.open(path)
    band = image.getchannel(0) if image.mode not in ("I", "I;16", "I;16B", "L") else image
    values = np.asarray(band).astype(np.float64)
    scale = 65535.0 if band.mode.startswith("I") else 255.0
    return values.reshape(-1) / scale, image.size


def exr_histograms(paths: list[Path]) -> dict:
    with tempfile.TemporaryDirectory() as scratch:
        output = Path(scratch, "histograms.json")
        subprocess.run([BLENDER, "--background", "--factory-startup", "--python-expr", BLENDER_HISTOGRAM, "--",
                        str(BINS), str(output), *map(str, paths)], check=True, capture_output=True)
        return json.loads(output.read_text())


def entry(relative: str, digest: str, size, counts: np.ndarray) -> dict:
    nonzero = np.nonzero(counts)[0]
    first, last = int(nonzero[0]), int(nonzero[-1])
    kept = [int(value) for value in counts[first:last + 1]]
    return {"file": relative, "sha256": digest, "size": list(size), "first_bin": first, "counts": kept,
            "knots": library.histogram_knots(first, kept)}


def srgb_to_linear(values: np.ndarray) -> np.ndarray:
    return np.where(values <= 0.04045, values / 12.92, ((values + 0.055) / 1.055) ** 2.4)


def macro_entry(engine_root: Path) -> dict:
    package = (engine_root / MACRO_PACKAGE).read_bytes()
    start = package.find(b"\x89PNG\r\n\x1a\n")
    library.require(start >= 0 and b"SRGB\x00\x05\x00\x00\x00True" in package[:start],
                    "T_Default_MacroVariation no longer holds an sRGB PNG source")
    image = Image.open(io.BytesIO(package[start:]))
    rgba = np.asarray(image.convert("RGBA"))
    # Two samples at unrelated UVs: the red of one and the green of the other are independent.
    red, green = (np.bincount(rgba[..., channel].reshape(-1), minlength=256) for channel in (0, 1))
    levels = srgb_to_linear(np.arange(256) / 255.0)
    joint = np.outer(red, green).astype(np.float64)
    mean = np.clip(0.5 * (levels[:, None] + levels[None, :]), 0.0, 1.0)
    counts = np.bincount(np.clip(np.floor(mean * BINS), 0, BINS - 1).astype(np.int64).reshape(-1),
                         weights=joint.reshape(-1), minlength=BINS)
    counts = np.rint(counts / joint.sum() * 1e9).astype(np.int64)  # parts per billion
    result = entry(MACRO_PACKAGE, hashlib.sha256(package).hexdigest(), image.size, counts)
    result["file"] = f"{PIN['version']}:{MACRO_PACKAGE}"
    result["sampled"] = "saturate(0.5 * (R + G)) of the sRGB texture sampled at two unrelated scales"
    return result


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    plan = library.build_plan(root, measured=False)
    names = sorted({instance.layers[0] for instance in plan.instances if library.needs_ao_ranks(instance)})
    sources = {name: library.ao_source(root, plan.sets[name], plan.packs) for name in names}
    paths = {name: (plan.storage if base == "storage" else root) / relative
             for name, (base, relative, _) in sources.items()}
    for name, (_, relative, digest) in sources.items():
        library.require(library.sha256(paths[name]) == digest, f"{name}: {relative} does not match its record")
    exr = exr_histograms([path for path in paths.values() if path.suffix.lower() == ".exr"])
    sets = {}
    for name in names:
        _, relative, digest = sources[name]
        path = paths[name]
        if path.suffix.lower() == ".exr":
            measured = exr[str(path)]
            counts, size = np.asarray(measured["counts"], dtype=np.int64), measured["size"]
        else:
            values, size = pillow_red(path)
            counts = bin_counts(values)
        library.require(tuple(size) == library.image_size(path), f"{name}: decoded size differs from its header")
        sets[name] = entry(relative, digest, size, counts)
    engine_root = Path(os.environ.get("UE_ROOT", PIN["default_macos_root"])).expanduser()
    require_engine_root(engine_root)
    document = {"generator": library.AO_RANKS_GENERATOR, "ranks": list(RANKS), "tails": list(library.RANK_TAILS),
                "bins": BINS, "macro": macro_entry(engine_root), "sets": sets}
    text = json.dumps(document, indent=1)
    # One line per list of numbers (a histogram has thousands of bins).
    text = re.sub(r"\[\s*(-?[0-9][^\[\]{}\"]*?)\s*\]", lambda match: "[" + ", ".join(match.group(1).split(",\n"))
                  .replace("\n", "").replace("  ", "") + "]", text)
    (root / library.AO_RANKS).write_text(text + "\n", encoding="utf-8")
    for name, item in sets.items():
        print(f"{name}: AO knots {item['knots']}")
    print(f"macro knots {document['macro']['knots']}")
    print(f"SORA_CC0_AO_MEASURED: {len(sets)} sets and the macro variation in {library.AO_RANKS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
