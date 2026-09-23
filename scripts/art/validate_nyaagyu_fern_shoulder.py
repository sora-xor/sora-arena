"""Independently validate the CC0 fern source package and FBX round trips.

Run: blender -b --factory-startup --python scripts/art/validate_nyaagyu_fern_shoulder.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "Content/SourceArt/Environment/PolyHaven/Fern02"
UP = ART / "Upstream"
manifest = json.loads((ART / "manifest.json").read_text())
PINNED_UPSTREAM_SHA = {
    "Upstream/fern_02_4k.gltf": "7d5d458d4be38edceff922586234fa906377db5257e66d7cdde34b37e79788f7",
    "Upstream/fern_02.bin": "fe1abb762bcbbc7ad9e86925c8080437a62add257d9280e9142fdc85c226e64c",
    "Upstream/textures/fern_02_diff_4k.jpg": "f924354b032fcde77830b0c33c4dff80b4b143f793e70126894788f199b61960",
    "Upstream/textures/fern_02_arm_4k.jpg": "0ccfb4d98966c0e69769e9ddd5be872e34bb1d2f8aece3aff6d42fd3e61f8f1c",
    "Upstream/textures/fern_02_nor_gl_4k.jpg": "14125a030e3fab96f52343215a65167ea46bcabae4bdef3444ba8ae22cb05e41",
    "Upstream/textures/fern_02_nor_dx_4k.jpg": "31a427c608b2e0e52a1bd5310b21c6ad9b070a060656f8cb57876a72354b7e3b",
    "Upstream/textures/fern_02_alpha_4k.png": "50dd262282e9787ae8abf4475b5d2071df8a88f5242f480602a0672347bd7ff9",
    "Upstream/textures/fern_02_diff_2k.jpg": "9ee18172170728050871772e2cd6d8d37b52f9138e61b49b04486623f9caf84b",
    "Upstream/textures/fern_02_arm_2k.jpg": "1eaf9bd29e2d83a77ca5d89bdddebcd9216b8b4ba244644580fe5b89bbe713f1",
    "Upstream/textures/fern_02_nor_gl_2k.jpg": "dfe1ac4a428d21f7c134411500177d66b8dd800c8fec6f0040c50f44414a777b",
    "Upstream/textures/fern_02_nor_dx_2k.jpg": "4c6531d4c3b8f7e149bcbaeb4b1ca28e8d50c6ad7bcd8eff228bcfb756aa57f3",
    "Upstream/textures/fern_02_alpha_2k.png": "f51eb9b8f9f4b25a882f8fe12d1ef53ba69448bac7e71396ec1f05b684e9ea75",
}


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


assert manifest["asset_id"] == "fern_02"
assert manifest["license"].startswith("CC0-1.0;")
assert manifest["gameplay_collision"] is False
assert abs(manifest["review_eye_height_m"] - 1.63) < .001
assert len(manifest["preview_placement_m"]) == 8
assert {entry["path"] for entry in manifest["upstream_files"]} == set(PINNED_UPSTREAM_SHA)
for entry in manifest["upstream_files"]:
    path = ART / entry["path"]
    assert path.stat().st_size == entry["bytes"], path
    assert sha(path) == entry["sha256"] == PINNED_UPSTREAM_SHA[entry["path"]], path
    assert entry["official_url"].startswith("https://dl.polyhaven.org/file/ph-assets/Models/")
    assert entry["official_url"].endswith(path.name)
    assert hashlib.md5(path.read_bytes()).hexdigest() == entry["md5"]
for filename, hash_name in (("source_blend", "source_blend_sha256"),
                            ("preview", "preview_sha256"),
                            ("mac_fallback_preview", "mac_fallback_preview_sha256")):
    assert sha(ART / manifest[filename]) == manifest[hash_name]

for tier, resolution in (("4k", 4096), ("2k", 2048)):
    for role in ("diff", "arm", "nor_gl", "nor_dx", "alpha"):
        suffix = "png" if role == "alpha" else "jpg"
        image = bpy.data.images.load(str(UP / "textures" / f"fern_02_{role}_{tier}.{suffix}"))
        assert tuple(image.size) == (resolution, resolution), (role, tier, image.size)

meshes = manifest["meshes"]
assert len(meshes) == 8
by_form = {(entry["variant"], entry["tier"]): entry for entry in meshes}
assert set(by_form) == {(letter, tier) for letter in "abcd" for tier in ("hi", "mac_lod1")}
assert sum(by_form[(letter, "hi")]["triangles"] for letter in "abcd") == 6232
assert sum(by_form[(letter, "mac_lod1")]["triangles"] for letter in "abcd") < 3400

for entry in meshes:
    path = ART / entry["fbx"]
    assert sha(path) == entry["fbx_sha256"]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    found = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    assert len(found) == 1, path
    obj = found[0]
    assert obj.name == path.stem
    assert len(obj.data.polygons) == entry["triangles"]
    assert len(obj.data.uv_layers) == 1
    assert len(obj.data.materials) == 1
    assert obj.data.materials[0].name == entry["material_slot"]
    assert entry["nanite_candidate"] == (entry["tier"] == "hi")
    assert .20 < obj.dimensions.z < .50
    assert max(obj.dimensions.x, obj.dimensions.y) < 1.01
    print("FERN02_FBX_VALID", entry["fbx"], entry["triangles"], flush=True)

bpy.ops.wm.open_mainfile(filepath=str(ART / manifest["source_blend"]))
assert len([obj for obj in bpy.data.objects if obj.name.startswith("PreviewOnly_NorthernShoulder_")]) == 8
assert abs(bpy.context.scene.camera.location.z - 1.63) < .001
for tier in ("4K", "2K"):
    mat = bpy.data.materials[f"M_NyaagyuFern02_{tier}"]
    shader = next(node for node in mat.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
    alpha_link = shader.inputs["Alpha"].links
    assert len(alpha_link) == 1 and alpha_link[0].from_node.type == "TEX_IMAGE"
    assert f"alpha_{tier.lower()}" in alpha_link[0].from_node.image.filepath
    assert not mat.use_backface_culling
    for node in mat.node_tree.nodes:
        if node.type == "TEX_IMAGE" and node.image:
            assert Path(bpy.path.abspath(node.image.filepath)).is_file(), node.image.filepath
print("FERN02_SOURCE_VALID", len(meshes), "FBXs; 4K/2K PBR+alpha; source-only", flush=True)
