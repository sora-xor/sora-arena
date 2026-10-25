"""Shared rules for the SORA Arena third-party asset ledger (schema 2).

The policy lives in docs/art-research/free-asset-acquisition-plan.md, sections 2.1-2.5.
This module has no network access and never downloads, moves or deletes files.

Ledger documents are JSON files with ``"schema_version": 2`` found in:

* ``scripts/assets/manifests/*.json`` - public (PUB/OWN) records, e.g. CC0 raw
  files fetched into the gitignored ``Local/ThirdPartyRaw`` tree;
* ``Content/SourceArt/**/manifest.ledger.json`` - schema-2 extensions of older
  schema-1 manifests whose bytes are pinned elsewhere and must not change;
* ``Content/SourceArt/**/manifest.json`` with ``"schema_version": 2`` *and* a
  top-level ``tier`` - document-level output manifests. A document-level OWN
  manifest (``tier: OWN``, a generator and a ``files`` list, as the audio lane
  writes) is read as one OWN record; see ``own_document_record``. Older art
  manifests that use their own "schema_version 2" without a ``tier`` are not
  ledger documents;
* ``scripts/assets/restricted/*.json`` - restricted (RST/REF/EXCL) records that
  list hashes and paths, never file contents.

Lane drafts named ``sources_manifest.json`` under ``Content/SourceArt`` are not
ledger documents; the validator requires every third-party file they list to be
recorded in the ledger above (``draft_source_entries``).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = 2

TIERS = ("PUB-CC0", "PUB-PD", "PUB-BY", "OWN", "RST", "REF", "EXCL")
PUBLIC_TIERS = frozenset({"PUB-CC0", "PUB-PD", "PUB-BY", "OWN"})
NEVER_TRACKED_TIERS = frozenset({"RST", "REF", "EXCL"})

# Section 2.5 rule 3. "project-owned" marks OWN records (our own generator output).
LICENSE_ALLOWLIST = frozenset({
    "CC0-1.0", "PDM-1.0", "US-PD", "NASA-media",
    "CC-BY-3.0", "CC-BY-4.0", "OGA-BY-3.0", "OGA-BY-4.0", "JP-GSToU-2.0",
    "project-owned",
})
# Fonts are software-like and ship under their own license text. OFL-1.1 is
# accepted only on records whose kind is "font" (an extension of the plan's list).
FONT_LICENSES = frozenset({"OFL-1.1"})
TIER_LICENSES = {
    "PUB-CC0": frozenset({"CC0-1.0", "PDM-1.0", "US-PD"}),
    "PUB-PD": frozenset({"NASA-media", "US-PD", "PDM-1.0"}),
    "PUB-BY": frozenset({"CC-BY-3.0", "CC-BY-4.0", "OGA-BY-3.0", "OGA-BY-4.0", "JP-GSToU-2.0"}) | FONT_LICENSES,
    "OWN": frozenset({"project-owned"}),
}
_REJECTED_LICENSE = re.compile(r"(^|[-_ .])(NC|ND|SA)([-_ .]|$)|GPL|NonCommercial|NoDeriv|ShareAlike", re.I)

ENUMS = {
    "redistribution": {"unrestricted", "attribution", "no-standalone", "none"},
    "ai_terms": {"none", "no-training", "no-genai-input", "written-permission", "unknown"},
    "agent_handling": {"allowed", "forbidden"},
    "acquired_by": {"agent", "user"},
    # local-raw: CC0/PD source files kept only in gitignored Local/ThirdPartyRaw and
    # reproducible with scripts/assets/fetch_cc0.py (avoids a second LFS copy).
    "storage": {"repo-lfs", "repo", "local-raw", "local-private", "ue-restricted"},
}
ACCESS_PATTERN = re.compile(r"^(direct|api|generated|user-supplied|login:[a-z0-9-]+|registration:[a-z0-9-]+)$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

# Fields every schema-2 record must carry (value may be null where noted in the plan).
REQUIRED_KEYS = (
    "asset_id", "name", "tier", "license", "license_url", "origin_url", "mirror_url",
    "commercial_use", "redistribution", "derivatives", "platform_restriction", "ai_terms",
    "agent_handling", "attribution_text", "changes", "access",
    "acquired_at_utc", "acquired_by", "storage", "used_by", "fallback", "files",
)

RESTRICTED_ROOTS = ("Local/", "Content/ThirdPartyRestricted/", "Content/Fab/")
SOURCE_ART_ROOT = "Content/SourceArt/"
BINARY_EXTENSIONS = frozenset({
    "png", "jpg", "jpeg", "exr", "hdr", "tga", "tif", "tiff", "psd", "fbx", "glb", "gltf", "bin",
    "obj", "blend", "blend1", "usd", "usda", "usdc", "usdz", "abc", "wav", "ogg", "flac", "mp3", "otf",
    "ttf", "svg", "uasset", "umap",
})
# Blender "Save Versions" backups (.blend1, .blend2, ...): an older full copy of the
# scene, never recorded and never committed (gitignored as *.blend[0-9]*).
BLENDER_BACKUP_EXTENSION = re.compile(r"^blend[0-9]+$")
# Section 2.5: formats that must be stored through Git LFS when committed.
LFS_EXTENSIONS = frozenset({
    "uasset", "umap", "blend", "fbx", "glb", "wav", "exr", "png", "tga", "jpg", "jpeg", "hdr",
    "tif", "otf", "ogg", "flac", "bin", "usd", "usdc", "usdz", "abc",
})
# Section 2.5: never commit asset archives or videos (compressed text logs such as *.log.gz are not assets).
NEVER_COMMIT_EXTENSIONS = frozenset({"zip", "7z", "rar", "mp4", "mov", "mkv", "avi", "webm"})
# Schema-1 records: manifests and sidecar JSON, READMEs, NOTICEs, prompts and generator scripts kept beside the art.
LEGACY_RECORD_NAMES = re.compile(r".*\.(json|md|txt|py)$")


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(chunk), b""):
            digest.update(block)
    return digest.hexdigest()


def is_lfs_pointer(path: Path) -> bool:
    header = b"version https://git-lfs.github.com/spec/v1"
    try:
        with open(path, "rb") as handle:
            return handle.read(len(header)) == header
    except OSError:
        return False


def posix(path: str) -> str:
    return path.replace(os.sep, "/")


def extension(path: str) -> str:
    name = path.rsplit("/", 1)[-1]
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def is_blender_backup(path: str) -> bool:
    return bool(BLENDER_BACKUP_EXTENSION.match(extension(path)))


def is_binary(path: str) -> bool:
    """Binary asset formats that need a ledger record (includes Blender backups)."""
    return extension(path) in BINARY_EXTENSIONS or is_blender_backup(path)


def never_commit(path: str) -> Optional[str]:
    """Why a path must never be committed (archive, video, Blender backup), or None."""
    ext = extension(path)
    if ext in NEVER_COMMIT_EXTENSIONS:
        return "archive or video"
    if BLENDER_BACKUP_EXTENSION.match(ext):
        return "Blender backup (.blend1 etc.)"
    return None


# ---------------------------------------------------------------------------
# Git helpers (read-only)
# ---------------------------------------------------------------------------

def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def tracked_files(root: Path) -> List[str]:
    """Paths in the git index (tracked or staged), repo-relative, POSIX style."""
    out = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True)
    if out.returncode != 0:
        raise RuntimeError("git ls-files failed: " + out.stderr.decode(errors="replace"))
    return [p for p in out.stdout.decode("utf-8", errors="surrogateescape").split("\0") if p]


def lfs_oids(root: Path) -> Dict[str, str]:
    """Map of LFS-tracked path -> SHA-256 oid (from the index; no content needed)."""
    result = subprocess.run(["git", "-C", str(root), "lfs", "ls-files", "--long"], capture_output=True, text=True)
    if result.returncode != 0:
        return {}
    oids = {}
    for line in result.stdout.splitlines():
        parts = line.split(" ", 2)
        if len(parts) == 3 and SHA256_PATTERN.match(parts[0]):
            oids[parts[2].strip()] = parts[0]
    return oids


def tracked_content_sha256(root: Path, path: str, oids: Dict[str, str]) -> Optional[str]:
    """SHA-256 of tracked content: the LFS oid when available, else the working file."""
    if path in oids:
        return oids[path]
    full = root / path
    if full.is_file() and not is_lfs_pointer(full):
        return sha256_file(full)
    return None


# ---------------------------------------------------------------------------
# Ledger loading
# ---------------------------------------------------------------------------

def ledger_paths(root: Path) -> List[Path]:
    """Candidate ledger documents; load_ledgers keeps only those with schema_version 2."""
    paths = sorted((root / "scripts/assets/manifests").glob("*.json"))
    paths += sorted((root / "Content/SourceArt").rglob("manifest.ledger.json"))
    paths += sorted((root / "Content/SourceArt").rglob("manifest.json"))
    paths += sorted((root / "scripts/assets/restricted").glob("*.json"))
    return [p for p in paths if p.is_file()]


def draft_source_paths(root: Path) -> List[Path]:
    """Lane drafts that list third-party inputs outside the ledger (e.g. CatBaseV6)."""
    return sorted(p for p in (root / "Content/SourceArt").rglob("sources_manifest.json") if p.is_file())


def draft_source_entries(doc) -> List[Tuple[str, str, Optional[str]]]:
    """(path, sha256, tier) of every file entry in a lane draft, found by walking the JSON."""
    found: List[Tuple[str, str, Optional[str]]] = []

    def walk(node, tier=None):
        if isinstance(node, dict):
            tier = node.get("tier", tier) if isinstance(node.get("tier", tier), str) else tier
            path = node.get("file") or node.get("path")
            digest = str(node.get("sha256", ""))
            if isinstance(path, str) and SHA256_PATTERN.match(digest):
                found.append((path, digest, tier))
            for key, value in node.items():
                if key not in ("license_snapshot", "record_snapshot", "mirror_license", "license_evidence"):
                    walk(value, tier)
        elif isinstance(node, list):
            for value in node:
                walk(value, tier)

    walk(doc)
    return found


def load_json(path: Path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def load_ledgers(root: Path) -> List[Tuple[Path, dict]]:
    ledgers = []
    for path in ledger_paths(root):
        doc = load_json(path)
        if not isinstance(doc, dict) or doc.get("schema_version") != SCHEMA_VERSION:
            continue
        if path.name == "manifest.json" and "tier" not in doc:
            continue  # an art manifest with its own schema, not a ledger document
        ledgers.append((path, doc))
    return ledgers


def own_document_record(doc: dict) -> Optional[dict]:
    """A document-level OWN manifest read as one OWN record.

    The audio lane's output manifests (Content/SourceArt/Audio/*/manifest.json) are
    schema 2 with a top-level ``tier: OWN``, their generator (``generator``,
    ``generator_scripts`` or ``regenerate``) and a ``files`` list. Only documents
    that name a generator qualify; anything else stays unrecorded so the validator
    reports it.
    """
    if doc.get("tier") != "OWN" or not isinstance(doc.get("files"), list):
        return None
    generator = doc.get("generator") or doc.get("generator_scripts") or doc.get("regenerate")
    if not generator:
        return None
    paths = [file_path(entry) for entry in doc["files"] if isinstance(entry, dict) and file_path(entry)]
    folder = os.path.commonpath(paths) if paths else ""
    if folder in paths:  # a single file: use its directory
        folder = folder.rsplit("/", 1)[0]
    if isinstance(generator, list):
        generator = ", ".join(generator)
    return {
        "asset_id": doc.get("asset_id") or folder or "own-document",
        "name": doc.get("name") or doc.get("purpose") or folder,
        "tier": "OWN",
        "license": "project-owned",
        "license_url": None,
        "license_statement": doc.get("license"),
        "origin_url": doc.get("regenerate") or generator,
        "mirror_url": None,
        "commercial_use": True,
        "redistribution": "unrestricted",
        "derivatives": True,
        "platform_restriction": None,
        "ai_terms": "none",
        "agent_handling": "allowed",
        "attribution_text": None,
        "changes": None,
        "access": "generated",
        "acquired_at_utc": doc.get("generated_at_utc"),
        "acquired_by": "agent",
        "storage": doc.get("storage") or "repo-lfs",
        "used_by": list(doc.get("used_by") or []),
        "fallback": None,
        "generator": generator,
        "derived_from": list(doc.get("derived_from") or doc.get("sample_sources") or []),
        "files": doc["files"],
    }


def doc_records(doc: dict) -> List[dict]:
    """Records of a schema-2 document. The audio lane's manifests name the list "assets";
    its output manifests are document-level OWN records (own_document_record)."""
    if "records" in doc:
        return list(doc.get("records") or [])
    if "assets" in doc:
        return list(doc.get("assets") or [])
    own = own_document_record(doc)
    return [own] if own else []


def file_path(entry: dict) -> Optional[str]:
    """Repo-relative path of a ledger file entry ("path"; the audio lane uses "file")."""
    return entry.get("path") or entry.get("file")


def record_files(record: dict) -> List[dict]:
    """Every hashed file entry of a record: ``files`` plus the audio lane's direct
    ``downloads`` and ``archive`` (archives stay in Local/ and are never committed)."""
    entries = list(record.get("files") or []) + list(record.get("downloads") or [])
    if isinstance(record.get("archive"), dict):
        entries.append(record["archive"])
    seen, unique = set(), []
    for entry in entries:
        key = file_path(entry)
        if key not in seen:
            seen.add(key)
            unique.append(entry)
    return unique


def iter_records(ledgers: Iterable[Tuple[Path, dict]]) -> Iterator[Tuple[Path, dict]]:
    for path, doc in ledgers:
        for record in doc_records(doc):
            yield path, record


def _has_hashed_snapshot(node) -> bool:
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "sha256" and SHA256_PATTERN.match(str(value)):
                return True
            if _has_hashed_snapshot(value):
                return True
    elif isinstance(node, list):
        return any(_has_hashed_snapshot(v) for v in node)
    return False


def has_license_evidence(record: dict, doc: Optional[dict] = None) -> bool:
    """A terms snapshot with a SHA-256: license_snapshot {url, sha256}, or a hashed
    snapshot inside license_evidence (record- or document-level)."""
    snapshot = record.get("license_snapshot")
    if isinstance(snapshot, dict) and snapshot.get("url") and SHA256_PATTERN.match(str(snapshot.get("sha256", ""))):
        return True
    if _has_hashed_snapshot(record.get("license_evidence")):
        return True
    return bool(doc) and _has_hashed_snapshot(doc.get("license_evidence"))


# ---------------------------------------------------------------------------
# Record rules (section 2.2 and 2.5 rules 3, 4, 6)
# ---------------------------------------------------------------------------

def license_is_rejected(license_id: str) -> bool:
    return bool(_REJECTED_LICENSE.search(license_id or ""))


def check_record(record: dict, where: str = "", doc: Optional[dict] = None) -> List[str]:
    """Schema-2 structural and license checks for one record. Returns error strings."""
    errors: List[str] = []
    label = f"{where}:{record.get('asset_id', '?')}"
    for key in REQUIRED_KEYS:
        if key not in record:
            errors.append(f"{label}: missing required key '{key}'")
    tier = record.get("tier")
    if tier not in TIERS:
        errors.append(f"{label}: unknown tier {tier!r}")
        return errors
    license_id = record.get("license") or ""
    kind = record.get("kind")
    if tier in PUBLIC_TIERS:
        if license_is_rejected(license_id):
            errors.append(f"{label}: license {license_id!r} is NC/ND/SA/GPL and is rejected for asset content")
        allowed = TIER_LICENSES[tier]
        if license_id in FONT_LICENSES and kind != "font":
            errors.append(f"{label}: {license_id} is accepted only for kind 'font'")
        elif license_id not in allowed:
            errors.append(f"{label}: license {license_id!r} is not allowed for tier {tier} (allowlist {sorted(allowed)})")
    if tier == "PUB-BY":
        for key in ("attribution_text", "changes"):
            if not record.get(key):
                errors.append(f"{label}: PUB-BY record needs a non-empty '{key}'")
    if tier == "RST" and not record.get("fallback"):
        errors.append(f"{label}: RST record needs a 'fallback' (PUB/OWN substitute asset_id)")
    if tier != "OWN" and not has_license_evidence(record, doc):
        errors.append(f"{label}: needs license_snapshot {{url, sha256}} (or a hashed snapshot in license_evidence) "
                      "of the terms read at acquisition")
    for key, allowed in ENUMS.items():
        value = record.get(key)
        if value is not None and value not in allowed:
            errors.append(f"{label}: {key}={value!r} not in {sorted(allowed)}")
    access = record.get("access")
    if access is not None and not ACCESS_PATTERN.match(str(access)):
        errors.append(f"{label}: access={access!r} is not a recognised access code")
    if not isinstance(record.get("used_by", []), list):
        errors.append(f"{label}: used_by must be a list of /Game paths")
    storage = record.get("storage")
    for entry in record_files(record):
        path = file_path(entry)
        if not path or path.startswith("/") or ".." in Path(path).parts:
            errors.append(f"{label}: file path {path!r} must be repo-relative")
            continue
        if not SHA256_PATTERN.match(str(entry.get("sha256", ""))):
            errors.append(f"{label}: {path} lacks a SHA-256")
        if tier in NEVER_TRACKED_TIERS and not path.startswith(("Local/", "Content/ThirdPartyRestricted/")):
            errors.append(f"{label}: {tier} file {path} must live under Local/ or Content/ThirdPartyRestricted/")
        if storage in ("local-raw", "local-private") and not path.startswith("Local/"):
            errors.append(f"{label}: storage {storage} but {path} is outside Local/")
        if storage in ("repo", "repo-lfs") and path.startswith(RESTRICTED_ROOTS):
            errors.append(f"{label}: storage {storage} but {path} is in an untracked root")
    return errors


# ---------------------------------------------------------------------------
# Legacy (schema-1) coverage heuristic
# ---------------------------------------------------------------------------

class LegacyIndex:
    """Finds schema-1 records (manifests, READMEs, NOTICEs) that mention a file.

    A file counts as covered when a legacy record in its directory, or an
    ancestor directory up to Content/SourceArt, mentions its relative path,
    basename, stem, or SHA-256; or when a generator script under scripts/
    names it. Strict mode treats legacy coverage as a failure.
    """

    def __init__(self, root: Path, tracked: Iterable[str]):
        self.root = root
        self.by_dir: Dict[str, List[Tuple[str, str]]] = {}
        self.scripts: List[Tuple[str, str]] = []
        for path in tracked:
            name = path.rsplit("/", 1)[-1]
            if path.startswith(SOURCE_ART_ROOT) and LEGACY_RECORD_NAMES.match(name):
                if name == "manifest.ledger.json":
                    continue
                text = self._read(path)
                if text is not None:
                    self.by_dir.setdefault(path.rsplit("/", 1)[0], []).append((path, text))
            elif path.startswith("scripts/") and path.endswith((".py", ".sh")) and not path.startswith("scripts/assets/"):
                text = self._read(path)
                if text is not None:
                    self.scripts.append((path, text))

    def _read(self, path: str) -> Optional[str]:
        try:
            return (self.root / path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None

    def find(self, path: str, sha256: Optional[str]) -> Optional[str]:
        name = path.rsplit("/", 1)[-1]
        stem = name.rsplit(".", 1)[0]
        stem_re = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(stem) + r"(?![A-Za-z0-9_])")
        directory = path.rsplit("/", 1)[0]
        while True:
            for record_path, text in self.by_dir.get(directory, []):
                relative = posix(os.path.relpath(path, directory))
                if relative in text or name in text or stem_re.search(text) or (sha256 and sha256 in text):
                    return record_path
            if directory + "/" == SOURCE_ART_ROOT or "/" not in directory:
                break
            directory = directory.rsplit("/", 1)[0]
        for script_path, text in self.scripts:
            if name in text:
                return script_path + " (generator)"
        return None
