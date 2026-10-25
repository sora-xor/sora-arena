"""The first-person parts' material bindings: serialized expectations, ordered readback, and one check.

Two scripts share this module, so they hold the parts to the same rows:

- verify_yumi_rig_materials.py, in a fresh editor before any capture;
- render_yumi_fp_review.py, as the capture's gate.

The rows are in docs/art-direction/data/fp_material_bindings.json. Each
asset's expectation is its exact slot count and, per slot name, the material
that slot must bind.

The readback is ordered rows:

- the asset: (index, slot name, material path), in its own slot order;
- a component given that asset: (index, material path), as GetMaterials
  resolves them.

Each component index must draw what its asset's slot at that index binds.
That is how a swapped override fails, though its sorted paths would pass
(Codex's review of cf646c2). Engine defaults fail everywhere.

check() is plain Python, tested on the host (scripts/art/test_fp_material_bindings.py).
The readers need Unreal objects and import nothing at module load.
"""
from __future__ import annotations

import json
from pathlib import Path

EXPECTATIONS = Path(__file__).resolve().parents[2] / "docs/art-direction/data/fp_material_bindings.json"


def load(path: Path = EXPECTATIONS) -> dict:
    """{asset path: {"slots": {slot name: material path}}}."""
    return json.loads(Path(path).read_text(encoding="utf-8"))["assets"]


def check(asset: str, slots: list, drawn: list, want: dict) -> list:
    """Problems (an empty list if none) for one asset.

    ``slots``: [(index, slot name, material path)] in the asset's order.
    ``drawn``: [(index, material path)] as a component resolves them.
    ``want``: {"slots": {slot name: material path}}."""
    problems = []
    expect = want["slots"]
    names = [row[1] for row in slots]
    if len(slots) != len(expect):
        problems.append(f"{asset}: {len(slots)} slots, want exactly {len(expect)}")
    if len(set(names)) != len(names) or set(names) != set(expect):
        problems.append(f"{asset}: slot names {names}, want exactly {sorted(expect)}")
    for i, (index, name, path) in enumerate(slots):
        if index != i:
            problems.append(f"{asset}: slot row {i} carries index {index}")
        if name in expect and path != expect[name]:
            problems.append(f"{asset}: slot {index} ({name}) binds {path}, want {expect[name]}")
    if [row[0] for row in drawn] != list(range(len(drawn))):
        problems.append(f"{asset}: component rows are not indexed 0..{len(drawn) - 1}: {[row[0] for row in drawn]}")
    if len(drawn) != len(slots):
        problems.append(f"{asset}: the component draws {len(drawn)} materials for {len(slots)} slots")
    for (index, path), (_, name, slot_path) in zip(drawn, slots):
        if path != slot_path:
            problems.append(f"{asset}: component index {index} draws {path}; its slot {index} ({name}) binds {slot_path}")
    for index, path in drawn:
        if path is None or path.startswith("/Engine/"):
            problems.append(f"{asset}: component index {index} draws an engine default or nothing: {path}")
    return problems


def _path(obj):
    return obj.get_path_name() if obj else None


def asset_rows(mesh) -> list:
    """[(index, slot name, material path)] for a SkeletalMesh or StaticMesh, in slot order."""
    prop = "materials" if mesh.get_class().get_name() == "SkeletalMesh" else "static_materials"
    return [(i, str(s.get_editor_property("material_slot_name")), _path(s.get_editor_property("material_interface")))
            for i, s in enumerate(mesh.get_editor_property(prop))]


def component_rows(component) -> list:
    """[(index, material path)] as a mesh component resolves them (GetMaterials)."""
    return [(i, _path(m)) for i, m in enumerate(component.get_materials())]


def as_json(slots, drawn) -> dict:
    return {"slots": [{"index": i, "slot": n, "material": p} for i, n, p in slots],
            "component": [{"index": i, "material": p} for i, p in drawn]}
