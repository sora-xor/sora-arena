"""Independent source, channel, periodic-edge and repetition checks for path quilt.

Run: python3 scripts/art/validate_nyaagyu_path_quilt.py
This does not substitute for a packaged eye-height Unreal visual review.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


root = Path(__file__).resolve().parents[2]
terrain = root / "Content/SourceArt/Environment/NyaagyuTerrain"
out = terrain / "QuiltedPath"
manifest = json.loads((out / "manifest.json").read_text())
scan = json.loads((terrain / "manifest.json").read_text())["stone_pathway_scan"]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert manifest["schema_version"] == 1
assert manifest["generator"] == "scripts/art/build_nyaagyu_path_quilt.py"
assert manifest["generator_sha256"] == sha(root / manifest["generator"])
assert manifest["source_asset"] == scan["asset_id"] == "grey_stone_path"
assert manifest["source_url"] == scan["source_url"] == "https://polyhaven.com/a/grey_stone_path"
assert manifest["license"] == scan["license"] == "CC0-1.0"
assert manifest["physical_size_cm"] == [720, 720]
assert manifest["texture_size_px"] == [4096, 4096]
quilt = manifest["quilt"]
assert quilt["grid"] == [8, 8] and quilt["patch_px"] == 640
assert quilt["stride_px"] == 512 and quilt["overlap_px"] == 128
assert "exact same crop and seam mask" in quilt["registration"]
patches = manifest["patches"]
assert len(patches) == 64
assert [(p["row"], p["col"]) for p in patches] == [
    (row, col) for row in range(8) for col in range(8)]
assert len({tuple(p["source_xy_px_at_1024"]) for p in patches}) >= 48
assert all(0 <= x <= 384 and 0 <= y <= 384 for p in patches
           for x, y in [p["source_xy_px_at_1024"]])

arrays = {}
for key in ("Diffuse", "nor_dx", "arm", "disp"):
    original = next(entry for entry in scan["files"] if entry["channel"] == key)
    source = root / manifest["source_files"][key]["repo_path"]
    assert source.resolve().is_relative_to(terrain.resolve())
    assert sha(source) == manifest["source_files"][key]["sha256"] == original["sha256"]
    output = manifest["outputs"][key]
    path = out / output["file"]
    assert path.resolve().is_relative_to(out.resolve())
    assert path.stat().st_size == output["bytes"] and sha(path) == output["sha256"]
    image = Image.open(path)
    assert image.size == (4096, 4096)
    if key == "disp":
        assert image.mode in ("I", "I;16")
        lo, hi = image.getextrema()
        assert 1000 < lo < hi <= 65535 and hi - lo > 40000
    else:
        assert image.mode == "RGB"
    arrays[key] = np.asarray(image)
    values = arrays[key].astype(np.float32)
    edge_x = np.sqrt(np.mean((values[:, 0] - values[:, -1]) ** 2))
    edge_y = np.sqrt(np.mean((values[0] - values[-1]) ** 2))
    assert edge_x < (3.0 if key == "Diffuse" else .01), (key, "x", edge_x)
    assert edge_y < (3.0 if key == "Diffuse" else .01), (key, "y", edge_y)

normals = arrays["nor_dx"].astype(np.float32) / 127.5 - 1.0
normal_length = np.linalg.norm(normals, axis=2)
assert np.percentile(normal_length, 1) > .95
assert np.mean(normals[:, :, 2] <= 0) == 0
assert np.mean(arrays["arm"][:, :, 2] != 0) < .001

# The old 1.8 m map would make all sixteen 1.8 m cells identical (corr=1).
# This checks that the stitched photo atlas actually breaks that exact motif.
albedo = arrays["Diffuse"].astype(np.float32)
cells = [albedo[row * 1024:(row + 1) * 1024,
                col * 1024:(col + 1) * 1024].reshape(-1, 3)[::64]
         for row in range(4) for col in range(4)]
correlations = [np.corrcoef(cells[i].ravel(), cells[j].ravel())[0, 1]
                for i in range(len(cells)) for j in range(i)]
assert max(correlations) < .4 and float(np.mean(correlations)) < .25

review = manifest["review"]
assert sha(out / review["file"]) == review["sha256"]
print("NYAAGYU_PATH_QUILT_VALIDATED", len(patches),
      "max_cell_correlation", round(max(correlations), 4))
