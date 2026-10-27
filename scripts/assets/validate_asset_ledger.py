#!/usr/bin/env python3
"""Validate the third-party asset ledger against the repository (plan section 2.5).

Fails (exit 1) when:
 1. a tracked binary under Content/SourceArt has neither a PUB/OWN schema-2 record
    nor (outside --strict) a legacy schema-1 record or generator reference;
 2. a tracked path lies under Local/, Content/ThirdPartyRestricted/ or Content/Fab/,
    or a tracked path or tracked content hash matches an RST/REF/EXCL record;
 3. a PUB/OWN record carries a license outside the allowlist (NC/ND/SA/GPL rejected);
 4. a PUB-BY record lacks attribution_text or changes;
 5. a recorded file is an unmaterialized Git LFS pointer, or its size or SHA-256
    differs (missing repo files also fail; missing Local/ raw files fail only
    with --require-local);
 6. an RST record declares no fallback;
 7. an agent-run script names a file or runtime path of an agent_handling:forbidden record.
It also fails on any file under Content/Fab/ (Fab imports belong in
Content/ThirdPartyRestricted/Fab/), on tracked archives, videos or Blender backups
(*.blend1, ...), on a schema-2 extension whose base manifest bytes or historical
hashes drifted, and on a lane draft (Content/SourceArt/**/sources_manifest.json)
that lists a third-party file the ledger does not record with the same SHA-256 and tier.

Read-only: it never downloads, stages, moves or deletes anything.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
import asset_ledger as L  # noqa: E402

AGENT_SCRIPT_GLOBS = ("scripts/unreal/*.py", "scripts/assets/*.py", "scripts/art/*.py", "scripts/toolchain/*.sh")


class Report:
    def __init__(self) -> None:
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.stats: Dict[str, int] = {}

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def count(self, key: str, amount: int = 1) -> None:
        self.stats[key] = self.stats.get(key, 0) + amount


def check_extension(root: Path, ledger_path: Path, doc: dict, report: Report) -> None:
    """A schema-2 extension must not rewrite its schema-1 base (bytes or hashes)."""
    for base in doc.get("extends", []) or []:
        base_path = root / base["manifest"]
        rel = L.posix(str(base_path.relative_to(root)))
        if not base_path.is_file():
            report.error(f"{ledger_path}: extended manifest {rel} is missing")
            continue
        actual = L.sha256_file(base_path)
        if actual != base.get("sha256"):
            report.error(f"{ledger_path}: extended manifest {rel} changed (sha256 {actual}, ledger pins {base.get('sha256')})")
        base_text = base_path.read_text(encoding="utf-8")
        for record in L.doc_records(doc):
            for entry in record.get("files", []):
                if entry.get("hash_source") == rel and entry.get("sha256") not in base_text:
                    report.error(f"{ledger_path}: {L.file_path(entry)} hash is not the historical hash recorded in {rel}")


def check_files(root: Path, ledger_path: Path, record: dict, require_local: bool, report: Report) -> None:
    for entry in L.record_files(record):
        path = L.file_path(entry)
        if not path:
            continue
        full = root / path
        if not full.is_file():
            if path.startswith("Local/") or path.startswith("Content/ThirdPartyRestricted/"):
                report.count("missing_local_files")
                if require_local:
                    report.error(f"{ledger_path.name}:{record.get('asset_id')}: {path} is missing")
            else:
                report.error(f"{ledger_path.name}:{record.get('asset_id')}: recorded repo file {path} is missing")
            continue
        if L.is_lfs_pointer(full):
            report.error(f"{ledger_path.name}:{record.get('asset_id')}: {path} is an unmaterialized Git LFS pointer; "
                         "cannot verify asset bytes (run git lfs checkout, or git lfs pull if the object is not cached)")
            continue
        size = full.stat().st_size
        if entry.get("bytes") is not None and size != entry["bytes"]:
            report.error(f"{ledger_path.name}:{record.get('asset_id')}: {path} is {size} bytes, ledger says {entry['bytes']}")
            continue
        if L.sha256_file(full) != entry.get("sha256"):
            report.error(f"{ledger_path.name}:{record.get('asset_id')}: {path} SHA-256 does not match the ledger")
        else:
            report.count("verified_files")
            report.count("verified_bytes", size)


def validate(root: Path, strict: bool = False, require_local: bool = False) -> Report:
    report = Report()
    tracked = L.tracked_files(root)
    tracked_set = set(tracked)
    oids = L.lfs_oids(root)
    ledgers = L.load_ledgers(root)
    report.count("ledger_documents", len(ledgers))

    recorded_public: Dict[str, str] = {}
    restricted_paths: Dict[str, str] = {}
    restricted_hashes: Dict[str, str] = {}
    forbidden_tokens: Dict[str, str] = {}
    asset_ids: Dict[str, str] = {}

    ledger_files: Dict[str, Dict[str, str]] = {}
    for ledger_path, doc in ledgers:
        rel_ledger = L.posix(str(ledger_path.relative_to(root)))
        in_restricted_dir = rel_ledger.startswith("scripts/assets/restricted/")
        check_extension(root, ledger_path, doc, report)
        for record in L.doc_records(doc):
            report.count("records")
            key = f"{doc.get('source', '?')}:{record.get('asset_id')}:{record.get('tier')}"
            if key in asset_ids:
                report.error(f"{rel_ledger}: duplicate record {key} (also in {asset_ids[key]})")
            asset_ids[key] = rel_ledger
            for problem in L.check_record(record, rel_ledger, doc):
                report.error(problem)
            tier = record.get("tier")
            if tier in L.NEVER_TRACKED_TIERS and not in_restricted_dir:
                report.error(f"{rel_ledger}: {tier} record {record.get('asset_id')} belongs in scripts/assets/restricted/")
            if tier in L.PUBLIC_TIERS and in_restricted_dir:
                report.error(f"{rel_ledger}: public record {record.get('asset_id')} is in the restricted directory")
            for entry in L.record_files(record):
                path = L.file_path(entry)
                if not path:
                    continue
                if entry.get("sha256"):
                    ledger_files.setdefault(path, {})[entry["sha256"]] = str(tier)
                if tier in L.PUBLIC_TIERS:
                    recorded_public[path] = rel_ledger
                else:
                    restricted_paths[path] = f"{rel_ledger}:{record.get('asset_id')}"
                    if entry.get("sha256"):
                        restricted_hashes[entry["sha256"]] = f"{rel_ledger}:{record.get('asset_id')}"
                if record.get("agent_handling") == "forbidden":
                    forbidden_tokens[path] = record.get("asset_id")
                    forbidden_tokens[path.rsplit("/", 1)[-1]] = record.get("asset_id")
            if record.get("agent_handling") == "forbidden":
                for runtime in record.get("used_by", []) or []:
                    forbidden_tokens[runtime] = record.get("asset_id")
            check_files(root, ledger_path, record, require_local, report)

    # Rule 2: nothing restricted or local-only is tracked.
    for path in tracked:
        if path.startswith(L.RESTRICTED_ROOTS):
            report.error(f"tracked path under a never-commit root: {path}")
        if path in restricted_paths:
            report.error(f"tracked path {path} has a restricted record ({restricted_paths[path]})")
        reason = L.never_commit(path)
        if reason:
            report.error(f"tracked {reason} (never commit): {path}")
    if restricted_hashes:
        for path in tracked:
            digest = L.tracked_content_sha256(root, path, oids)
            if digest and digest in restricted_hashes:
                report.error(f"tracked file {path} has the content of restricted item {restricted_hashes[digest]}")

    # Content/Fab guard (section 2.4): any file there fails.
    fab = root / "Content/Fab"
    if fab.exists():
        for item in sorted(fab.rglob("*")):
            if item.is_file():
                report.error(f"Fab content found at {L.posix(str(item.relative_to(root)))}; import Fab items under Content/ThirdPartyRestricted/Fab/")

    # Lane drafts: every third-party file they list must be in the ledger, same hash and tier.
    for draft in L.draft_source_paths(root):
        rel_draft = L.posix(str(draft.relative_to(root)))
        report.count("draft_source_documents")
        try:
            entries = L.draft_source_entries(L.load_json(draft))
        except ValueError as exc:
            report.error(f"{rel_draft}: unreadable JSON ({exc})")
            continue
        for path, digest, tier in entries:
            report.count("draft_source_entries")
            recorded = ledger_files.get(path, {})
            if digest not in recorded:
                report.error(f"{rel_draft}: {path} is not recorded in the ledger with SHA-256 {digest[:12]}... "
                             "(regenerate the lane's schema-2 ledger documents)")
            elif tier and recorded[digest] != tier:
                report.error(f"{rel_draft}: {path} is tier {tier} in the draft but {recorded[digest]} in the ledger")

    # Rule 1: every tracked SourceArt binary has a record.
    legacy = L.LegacyIndex(root, tracked)
    for path in tracked:
        if not path.startswith(L.SOURCE_ART_ROOT) or not L.is_binary(path):
            continue
        report.count("tracked_sourceart_binaries")
        if L.extension(path) in L.LFS_EXTENSIONS and path not in oids and not L.is_lfs_pointer(root / path):
            report.warn(f"{path} is committed as a plain git blob, not through LFS")
        if path in recorded_public:
            report.count("schema2_covered")
            continue
        found = legacy.find(path, oids.get(path))
        if found:
            report.count("legacy_covered")
            if strict:
                report.error(f"{path} is covered only by legacy record {found} (strict mode requires schema 2)")
        else:
            report.error(f"{path} has no ledger record, legacy record or generator reference")

    # Rule 7: agent-run scripts never name forbidden content.
    if forbidden_tokens:
        for pattern in AGENT_SCRIPT_GLOBS:
            for script in sorted(root.glob(pattern)):
                text = script.read_text(encoding="utf-8", errors="replace")
                for token, asset in forbidden_tokens.items():
                    if token and token in text:
                        report.error(f"{L.posix(str(script.relative_to(root)))} references {token} of agent_handling:forbidden record {asset}")
    report.count("tracked_files", len(tracked_set))
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=L.REPO_ROOT)
    parser.add_argument("--strict", action="store_true", help="legacy schema-1 coverage counts as a failure")
    parser.add_argument("--require-local", action="store_true", help="missing Local/ raw files fail")
    parser.add_argument("--json", action="store_true", help="print a JSON report")
    parser.add_argument("--quiet-warnings", action="store_true")
    args = parser.parse_args(argv)
    report = validate(args.root.resolve(), strict=args.strict, require_local=args.require_local)
    if args.json:
        print(json.dumps({"errors": report.errors, "warnings": report.warnings, "stats": report.stats}, indent=2))
    else:
        if not args.quiet_warnings:
            for warning in report.warnings:
                print("WARNING:", warning)
        for error in report.errors:
            print("ERROR:", error)
        stats = ", ".join(f"{k}={v}" for k, v in sorted(report.stats.items()))
        print(("LEDGER_FAIL" if report.errors else "LEDGER_OK") + f": {len(report.errors)} errors, {len(report.warnings)} warnings; {stats}")
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
