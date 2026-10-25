"""Host-side slot checks for cloth craft props (scripts/unreal/import_sora_craft.py).

Pure Python, so they run and are tested without Unreal
(scripts/unreal/test_sora_cloth_admission.py). A cloth's build record
(create_sora_maku.py) declares its material slots. The importer has a material
for each role it knows. The imported mesh must carry exactly the declared
slots: every one, once each, and nothing else. Only then are any material
instances made or bound.

A failed check raises AdmissionError, with the reason.
"""
from __future__ import annotations


class AdmissionError(RuntimeError):
    pass


def repeated(names) -> list:
    seen, twice = set(), set()
    for name in names:
        (twice if name in seen else seen).add(name)
    return sorted(twice)


def check_declared(declared, roles, cloth_slot: str) -> list:
    """The build record's slots: a non-empty list of distinct names, each a known
    role, including ``cloth_slot``."""
    if not isinstance(declared, list) or not declared or not all(isinstance(n, str) and n for n in declared):
        raise AdmissionError(f"build record material_slots must be a non-empty list of names, got {declared!r}")
    twice = repeated(declared)
    if twice:
        raise AdmissionError(f"build record declares {twice} more than once")
    unknown = sorted(set(declared) - set(roles))
    if unknown:
        raise AdmissionError(f"build record declares {unknown}, which the importer has no material for")
    if cloth_slot not in declared:
        raise AdmissionError(f"build record does not declare the cloth slot {cloth_slot}")
    return list(declared)


def check_imported(declared, imported) -> list:
    """The imported mesh's slot names, in mesh order, once they are exactly the declared ones."""
    imported = list(imported)
    if not imported:
        raise AdmissionError("the imported mesh has no material slots")
    twice = repeated(imported)
    if twice:
        raise AdmissionError(f"the imported mesh repeats slots {twice}")
    missing = sorted(set(declared) - set(imported))
    extra = sorted(set(imported) - set(declared))
    if missing or extra:
        raise AdmissionError(f"the imported mesh's slots {imported} differ from the declared {sorted(declared)}"
                             f" (missing {missing}, undeclared {extra})")
    return imported
