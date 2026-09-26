"""Pack the CC0 environment library's separate AO/roughness/metal(/opacity) maps into ARM maps.

Host step run by ``scripts/toolchain/import-mac.sh`` before the editor import.
ambientCG materials, two Poly Haven rock scans and the paper study ship
separate grayscale maps; Unreal samples one ``TC_Masks`` texture instead:
R = ambient occlusion (255 when absent), G = roughness, B = metalness (0 when
absent) and A = opacity when the source has one. Every input is hash-checked
against its ledger or manifest first; outputs go to the gitignored
``Saved/CC0Environment/Packed`` with ``packed.json`` recording input and
output SHA-256, which the importer verifies. An output whose recorded inputs
and bytes still match is left as it is.

Usage: python3 scripts/unreal/pack_cc0_environment.py
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

from PIL import Image
import PIL

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cc0_environment_library as library  # noqa: E402


def pack(plan, job, destination: Path):
    bands, size = {}, None
    for band, source in job.inputs.items():
        if isinstance(source, tuple):
            root, relative, _ = source
            path = (plan.storage if root == "storage" else plan.project_root) / relative
            image = Image.open(path)
            image = image.convert("L") if image.mode != "I" else image.point(lambda value: value / 257).convert("L")
            library.require(size in (None, image.size), f"{job.output}: {path.name} is {image.size}, expected {size}")
            size = image.size
            bands[band] = image
    library.require(size is not None, f"{job.output}: no image input")
    for band, source in job.inputs.items():
        if not isinstance(source, tuple):
            bands[band] = Image.new("L", size, int(source))
    mode = "RGBA" if "A" in bands else "RGB"
    packed = Image.merge(mode, [bands[band] for band in mode])
    destination.parent.mkdir(parents=True, exist_ok=True)
    packed.save(destination, format="PNG", compress_level=6)
    return size, mode


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    plan = library.build_plan(root)  # checks every ledger hash and the period policy
    manifest_path = root / library.PACKED_MANIFEST
    previous = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {}
    outputs = {}
    written = kept = 0
    for job in plan.packs:
        destination = root / library.PACKED_ROOT / job.output
        inputs = library.pack_inputs_record(job)
        old = (previous.get("outputs") or {}).get(job.output)
        if (old and old["inputs"] == inputs and destination.is_file()
                and library.sha256(destination) == old["sha256"]
                and previous.get("library_version") == library.LIBRARY_VERSION):
            outputs[job.output] = old
            kept += 1
            continue
        size, mode = pack(plan, job, destination)
        outputs[job.output] = {"inputs": inputs, "size": list(size), "mode": mode,
                               "sha256": library.sha256(destination)}
        written += 1
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({
        "generator": library.PACK_GENERATOR,
        "library_version": library.LIBRARY_VERSION,
        "pillow": PIL.__version__,
        "outputs": dict(sorted(outputs.items())),
    }, indent=1) + "\n")
    library.verify_packed(plan)
    print(f"SORA_CC0_PACK_COMPLETE: {len(plan.packs)} ARM maps ({written} written, {kept} unchanged)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
