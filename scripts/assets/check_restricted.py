#!/usr/bin/env python3
"""Check restricted (RST/REF/EXCL) assets without ever committing or downloading them.

Plan section 2.4. Each scripts/assets/restricted/<source>.json is a schema-2 ledger
("kind": "restricted-manifest") whose records list the listing URL, license and
flags, entitlement owner, expected SHA-256 of each local file, and imported package
paths. The manifests hold hashes and paths only, never file contents.

This script:
  * rejects a restricted manifest that embeds content or points at a tracked path;
  * reports each expected local file as present+verified, mismatched or missing,
    and prints the manual user step for anything missing (it never logs in or
    downloads);
  * fails when any restricted root is tracked by git, or when any tracked file
    (LFS oid or working-tree hash) has the content of a restricted file.

Exit status: 1 on a structural or tracking violation or a hash mismatch; missing
files fail only with --require-present.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
import asset_ledger as L  # noqa: E402

CONTENT_KEYS = {"data", "content", "contents", "base64", "bytes_b64", "payload", "blob"}
ALLOWED_FILE_ROOTS = ("Local/", "Content/ThirdPartyRestricted/")

# Manual steps from plan section 4.2, keyed by the record's "user_step".
USER_STEPS = {
    "U1": "Sketchfab (user login): open the listing, confirm the license badge, Download 3D Model (original "
          "archive; glTF if over 500 MB) into Local/ThirdPartyRaw/inbox/sketchfab/<model uid>/ and save the listing "
          "page as PDF beside it; then tell the agent 'Sketchfab batch ready'.",
    "U2": "Freesound (user login + OAuth): create API credentials, store them in ~/.config/sora-arena/freesound.json "
          "(chmod 600), run the agent's authorization helper, or download packs while logged in into "
          "Local/ThirdPartyRaw/inbox/freesound/.",
    "U3": "Epic/Fab (user, only after decision D1): record license type, UE-Only and 'Allows usage with AI' as a PDF "
          "in Local/ThirdPartyRaw/_licenses/fab/; stop if AI use is No; claim, set the Fab import folder to "
          "/Game/ThirdPartyRestricted/Fab/, import, and confirm `git status --porcelain Content` shows nothing new.",
    "U4": "JAXA AW3D30 (user registration): download the Yagyu-area tile into Local/ThirdPartyRaw/inbox/jaxa/.",
    "U5": "Smithsonian api.data.gov key (optional): store it in ~/.config/sora-arena/si.json.",
    "U6": "Restricted license acknowledgement (user): read the license page and confirm in the session before any "
          "agent fetch; each teammate downloads their own copy.",
    "U7": "Sensei Terrain (user, human-only): the $0 checkout is a purchase step; never place it in the repo.",
}


def find_content_keys(node, trail="") -> List[str]:
    hits = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key.lower() in CONTENT_KEYS:
                hits.append(f"{trail}/{key}")
            hits += find_content_keys(value, f"{trail}/{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            hits += find_content_keys(value, f"{trail}[{index}]")
    return hits


def check(root: Path, require_present: bool = False, out=print) -> int:
    failures = 0
    missing = 0
    restricted_hashes: Dict[str, str] = {}
    manifests = sorted((root / "scripts/assets/restricted").glob("*.json"))
    for manifest_path in manifests:
        rel = L.posix(str(manifest_path.relative_to(root)))
        doc = L.load_json(manifest_path)
        if not isinstance(doc, dict) or doc.get("schema_version") != L.SCHEMA_VERSION or doc.get("kind") != "restricted-manifest":
            out(f"FAIL {rel}: not a schema-2 restricted-manifest")
            failures += 1
            continue
        for hit in find_content_keys(doc):
            out(f"FAIL {rel}: embeds file content at {hit}; restricted manifests list hashes, never files")
            failures += 1
        for record in L.doc_records(doc):
            label = f"{rel}:{record.get('asset_id')}"
            for problem in L.check_record(record, rel, doc):
                out("FAIL " + problem)
                failures += 1
            if record.get("tier") not in L.NEVER_TRACKED_TIERS:
                out(f"FAIL {label}: tier {record.get('tier')} does not belong in a restricted manifest")
                failures += 1
            for key in ("listing_url", "entitlement_owner"):
                if not record.get(key):
                    out(f"FAIL {label}: missing '{key}'")
                    failures += 1
            for entry in L.record_files(record):
                path = L.file_path(entry) or ""
                digest = entry.get("sha256", "")
                if not path.startswith(ALLOWED_FILE_ROOTS):
                    out(f"FAIL {label}: {path} must be under {' or '.join(ALLOWED_FILE_ROOTS)}")
                    failures += 1
                if L.SHA256_PATTERN.match(digest):
                    restricted_hashes[digest] = label
                full = root / path
                if not full.is_file():
                    missing += 1
                    step = record.get("user_step")
                    how = record.get("manual_steps") or USER_STEPS.get(step or "", "see docs/art-research/free-asset-acquisition-plan.md section 4.2")
                    out(f"MISSING {label}: {path}\n    manual step {step or '-'}: {how}")
                    continue
                actual = L.sha256_file(full)
                if actual != digest:
                    out(f"FAIL {label}: {path} SHA-256 {actual} does not match {digest}")
                    failures += 1
                else:
                    out(f"OK {label}: {path}")

    tracked = L.tracked_files(root)
    oids = L.lfs_oids(root)
    for path in tracked:
        if path.startswith(L.RESTRICTED_ROOTS):
            out(f"FAIL tracked restricted/local path: {path}")
            failures += 1
    if restricted_hashes:
        for path in tracked:
            digest = L.tracked_content_sha256(root, path, oids)
            if digest in restricted_hashes:
                out(f"FAIL tracked file {path} has the content of restricted item {restricted_hashes[digest]}")
                failures += 1
    if require_present and missing:
        failures += missing
    out(("RESTRICTED_FAIL" if failures else "RESTRICTED_OK")
        + f": {len(manifests)} manifests, {len(restricted_hashes)} pinned hashes, {missing} missing locally, {failures} failures")
    return 1 if failures else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=L.REPO_ROOT)
    parser.add_argument("--require-present", action="store_true", help="missing restricted files fail")
    args = parser.parse_args(argv)
    return check(args.root.resolve(), require_present=args.require_present)


if __name__ == "__main__":
    sys.exit(main())
