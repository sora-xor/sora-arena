"""Host-side admission checks for scripts/unreal/import_nyaagyu_dojo_timbers.py.

Pure Python, so they run and are tested without Unreal
(scripts/unreal/test_dojo_timber_admission.py):

* **Cache files:** where a cached dense FBX lives when ``SORA_ART_CACHE`` moves
  the art cache, and whether it is the file a clean rebuild wrote for its
  manifest digest. Manifests and evidence keep their canonical
  ``Local/ArtCache/...`` keys, and only the file resolves under the moved
  cache.
* **Campaign binding:** whether ``campaign_binding.json``
  (scripts/art/bind_dojo_timbers.py) still matches the current chapter files,
  the kit manifests and the binder.

A failed check raises AdmissionError, with the reason.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

CACHE_KEY_PREFIX = "Local/ArtCache/"
BINDING_SCHEMA = "sora-dojo-timber-campaign-binding-v1"


class AdmissionError(RuntimeError):
    pass


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cache_root(project_root: Path, environ) -> Path:
    """The art cache: ``SORA_ART_CACHE`` when set, else the project's Local/ArtCache."""
    moved = environ.get("SORA_ART_CACHE")
    return Path(moved) if moved else project_root / "Local/ArtCache"


def resolve(project_root: Path, cache: Path, key: str) -> Path:
    """The file behind a manifest or evidence key. Keys under Local/ArtCache/
    resolve in ``cache``, every other key in the project."""
    if key.startswith(CACHE_KEY_PREFIX):
        return cache / key[len(CACHE_KEY_PREFIX):]
    return project_root / key


def check_evidence(project_root: Path, cache: Path, key: str, digest: str, evidence: dict, label: str) -> Path:
    """The file for ``key`` is the one the generator's build or --verify run
    wrote for ``digest``. Returns its resolved path."""
    entry = (evidence.get("fbx") or {}).get(key)
    if entry is None:
        raise AdmissionError(f"{label}: no rebuild evidence for {key} (run the generator, or its --verify)")
    if entry.get("digest") != digest:
        raise AdmissionError(f"{label}: rebuilt geometry digest differs from the manifest")
    path = resolve(project_root, cache, key)
    if not path.is_file():
        raise AdmissionError(f"{label}: {path} is missing")
    if sha(path) != entry.get("sha256"):
        raise AdmissionError(f"{label}: {path} is not the file that run wrote")
    return path


def check_binding(project_root: Path, binding: dict, manifests) -> dict:
    """``binding`` still holds for the current binder, manifests and chapter files."""
    if binding.get("schema") != BINDING_SCHEMA:
        raise AdmissionError("unknown campaign binding schema")
    binder = project_root / binding.get("binder", "")
    if not binder.is_file() or sha(binder) != binding.get("binder_sha256"):
        raise AdmissionError("the binder changed since the binding")
    bound = binding.get("manifests") or {}
    if sorted(bound) != sorted(manifests):
        raise AdmissionError("the binding covers other manifests")
    for rel, digest in bound.items():
        path = project_root / rel
        if not path.is_file() or sha(path) != digest:
            raise AdmissionError(f"{rel} changed since the binding")
    campaign = binding.get("campaign") or {}
    chapters = sorted(p.relative_to(project_root).as_posix()
                      for p in (project_root / "Content/Data/campaign").glob("chapter_*.json"))
    if not chapters or chapters != sorted(campaign):
        raise AdmissionError("the chapter files are not the ones bound")
    for rel, digest in campaign.items():
        if sha(project_root / rel) != digest:
            raise AdmissionError(f"{rel} changed since the binding (rerun python3 scripts/art/bind_dojo_timbers.py)")
    return binding
