#!/usr/bin/env python3
"""Write a schema-2 OWN ledger record for a folder of project-generated art.

  python3 scripts/assets/write_own_ledger.py Content/SourceArt/<...>/<Asset> \
      --asset-id ID --name NAME --generator scripts/art/<builder>.py [--generator ...] \
      [--derived-from PATH ...] [--used-by /Game/... ...] [--extends <folder>/manifest.json] \
      [--purpose TEXT] [--acquired-at ISO8601]

Writes <folder>/manifest.ledger.json with one OWN record (license project-owned)
that lists every git-tracked binary in the folder (asset_ledger.BINARY_EXTENSIONS)
with its size and SHA-256. ``--extends`` pins an existing schema-1 manifest's
bytes, which must then stay unchanged. ``derived_from`` names the project inputs
the art was built from (for example the pinned SORA SVG). Third-party inputs
belong in their own PUB records, not here.

Read-only apart from the one file it writes; it never stages or deletes anything.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import asset_ledger as L  # noqa: E402

ROOT = L.REPO_ROOT


def tracked_binaries(folder: Path):
    rel = L.posix(str(folder.relative_to(ROOT)))
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z", "--", rel], check=True,
                         stdout=subprocess.PIPE).stdout.decode()
    paths = []
    for p in filter(None, out.split("\0")):
        ext = p.rsplit(".", 1)[-1].lower() if "." in p else ""
        if ext in L.BINARY_EXTENSIONS:
            paths.append(p)
    return sorted(paths)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("folder")
    ap.add_argument("--asset-id", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--generator", action="append", required=True)
    ap.add_argument("--derived-from", action="append", default=[])
    ap.add_argument("--used-by", action="append", default=[])
    ap.add_argument("--extends")
    ap.add_argument("--purpose", default=None)
    ap.add_argument("--acquired-at", default=None, help="when the files were generated (ISO 8601 UTC)")
    a = ap.parse_args(argv)
    folder = (ROOT / a.folder).resolve()
    if not folder.is_dir():
        print(f"no such folder: {a.folder}", file=sys.stderr)
        return 1
    for g in a.generator:
        if not (ROOT / g).is_file():
            print(f"generator {g} not found", file=sys.stderr)
            return 1
    files = []
    for p in tracked_binaries(folder):
        path = ROOT / p
        files.append({"path": p, "bytes": path.stat().st_size, "sha256": L.sha256_file(path)})
    if not files:
        print(f"{a.folder}: no tracked binaries", file=sys.stderr)
        return 1
    derived = []
    for p in a.derived_from:
        path = ROOT / p
        if not path.is_file():
            print(f"derived-from {p} not found", file=sys.stderr)
            return 1
        derived.append({"path": p, "sha256": L.sha256_file(path)})
    doc = {
        "schema_version": 2,
        "kind": "asset-ledger",
        "ledger_id": f"own-{a.asset_id}",
        "source": "project",
        "purpose": a.purpose or f"OWN record for the generated files of {a.name}.",
        "generator": "scripts/assets/write_own_ledger.py",
    }
    if a.extends:
        base = ROOT / a.extends
        doc["extends"] = [{"manifest": a.extends, "sha256": L.sha256_file(base), "schema_version": 1}]
        doc["policy"] = "The extended schema-1 manifest stays byte-identical; regenerate this record after a rebuild."
    doc["records"] = [{
        "asset_id": a.asset_id,
        "name": a.name,
        "kind": "generated-art",
        "tier": "OWN",
        "license": "project-owned",
        "license_url": None,
        "origin_url": ", ".join(a.generator),
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
        "acquired_at_utc": a.acquired_at,
        "acquired_by": "agent",
        "storage": "repo-lfs",
        "used_by": a.used_by,
        "fallback": None,
        "generator": a.generator,
        "derived_from": derived,
        "files": files,
    }]
    errors = L.check_record(doc["records"][0], str(folder.relative_to(ROOT)), doc)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    out = folder / "manifest.ledger.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {L.posix(str(out.relative_to(ROOT)))}: {len(files)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
