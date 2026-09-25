#!/usr/bin/env python3
"""Extend the existing Poly Haven schema-1 manifests to schema 2 without rewriting them.

Content/SourceArt/Environment/PolyHaven/manifest.json is byte-pinned (by SHA-256) in
seven other manifests and asserted to be schema_version 1 by validate_content.py,
validate_environment_palette.py and validate_imported_assets.py. Editing it in place
would rewrite historical hashes. Instead this script writes a schema-2 *extension*,
Content/SourceArt/Environment/PolyHaven/manifest.ledger.json, that:

* pins every extended schema-1 manifest by its current SHA-256 ("extends");
* copies each file's historical SHA-256 verbatim from its base manifest
  ("hash_source" names the base; the validator checks the hash is still there);
* adds the schema-2 fields (tier, license snapshot, access, storage, used_by, ...);
* re-checks each upstream file against today's Poly Haven API MD5 where the file
  name is in the API listing (--offline skips the network and records nothing new);
* records files that no manifest listed (stone_floor_disp_2k.png) with a hash
  computed now, marked as such.

It never modifies the schema-1 manifests or any asset file.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import asset_ledger as L  # noqa: E402

PH = "Content/SourceArt/Environment/PolyHaven"
OUT = f"{PH}/manifest.ledger.json"
BASES = [
    # (base manifest, derived-art generator when the base names none)
    (f"{PH}/manifest.json", "scripts/art/fetch_polyhaven_palette.py"),
    (f"{PH}/GreyRoofTiles/manifest.json", None),
    (f"{PH}/WhitePlaster02/manifest.json", "scripts/art/fetch_white_plaster_02.py"),
    (f"{PH}/TreeSmall02/manifest.json", None),
    (f"{PH}/PineSaplingSmall/manifest.json", None),
    (f"{PH}/Fern02/manifest.json", None),
    (f"{PH}/Fern02/GroundTransition/manifest.json", None),
]
# Tracked files under the Poly Haven folder that no schema-1 manifest lists.
UNLISTED = [
    {"path": f"{PH}/stone_floor/stone_floor_disp_2k.png", "asset_id": "stone_floor", "channel": "Displacement",
     "format": "png", "resolution": "2k", "note": "Committed in 7ba299e (2026-09-24 terrain macro relief) without a manifest entry."},
]
OWN_UNLISTED = [
    {"path": f"{PH}/Nyaagyu_PBR_Palette_Preview.png", "generator": "scripts/art/render_environment_palette.py",
     "derived_from": ["wood_planks_dirt", "stone_floor", "brown_mud_leaves_01", "rusty_metal_02", "kloofendal_overcast_puresky"]},
]
PALETTE_RUNTIME_ROOT = "/Game/Generated/Environment"
DERIVED_FROM = {f"{PH}/Fern02/GroundTransition/manifest.json": ["fern_02"]}
USER_AGENT = "SORA-Arena-Asset-Authoring/0.2 (scripts/assets/migrate_polyhaven_ledger.py; Powered by Poly Haven; offline game production)"


def sha(path: Path) -> str:
    return L.sha256_file(path)


def md5(path: Path) -> str:
    digest = hashlib.md5()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def first_commit_date(root: Path, rel: str) -> Optional[str]:
    out = subprocess.run(["git", "-C", str(root), "log", "--diff-filter=A", "--format=%aI", "--", rel],
                         capture_output=True, text=True).stdout.split()
    return out[-1] if out else None


def api_listing(asset_id: str, offline: bool) -> Dict[str, dict]:
    """Map file name -> {url, md5, size} from the Poly Haven files API."""
    if offline:
        return {}
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from fetch_cc0 import Http, POLYHAVEN_HOSTS  # noqa: E402
    data = Http(POLYHAVEN_HOSTS, user_agent=USER_AGENT).get_json(f"https://api.polyhaven.com/files/{asset_id}")
    names: Dict[str, dict] = {}

    def walk(node):
        if isinstance(node, dict):
            if "url" in node and "md5" in node:
                names[Path(node["url"]).name] = {"url": node["url"], "md5": node["md5"], "size": node.get("size")}
            for value in node.values():
                walk(value)
    walk(data)
    return names


def file_pairs(node, trail=()) -> List[Tuple[str, str, dict, tuple]]:
    """(relative path, sha256, entry dict, trail) pairs found in a schema-1 manifest."""
    found = []
    if isinstance(node, dict):
        for key in ("file", "path"):
            if isinstance(node.get(key), str) and L.SHA256_PATTERN.match(str(node.get("sha256", ""))):
                found.append((node[key], node["sha256"], node, trail))
        for key, value in node.items():
            # Generator scripts are recorded as metadata, not as art files.
            if key == "generator" or (isinstance(value, str) and value.startswith("scripts/")):
                continue
            if isinstance(value, str) and "." in value and L.SHA256_PATTERN.match(str(node.get(key + "_sha256", ""))):
                found.append((value, node[key + "_sha256"], {}, trail + (key,)))
        for key, value in node.items():
            found += file_pairs(value, trail + (key,))
    elif isinstance(node, list):
        for value in node:
            found += file_pairs(value, trail)
    return found


def runtime_paths(node) -> List[str]:
    paths = []
    if isinstance(node, dict):
        for value in node.values():
            paths += runtime_paths(value)
    elif isinstance(node, list):
        for value in node:
            paths += runtime_paths(value)
    elif isinstance(node, str) and node.startswith("/Game/"):
        paths.append(node)
    return sorted(set(paths))


def public_base(snapshot: dict, acquired: Optional[str]) -> dict:
    return {
        "tier": "PUB-CC0", "license": "CC0-1.0", "license_url": "https://polyhaven.com/license",
        "legal_code_url": "https://creativecommons.org/publicdomain/zero/1.0/legalcode", "mirror_url": None,
        "commercial_use": True, "redistribution": "unrestricted", "derivatives": True, "platform_restriction": None,
        "ai_terms": "none", "agent_handling": "allowed", "attribution_text": None,
        "courtesy_credit": "Powered by Poly Haven - https://polyhaven.com", "changes": None,
        "license_snapshot": snapshot, "access": "api", "acquired_at_utc": acquired, "acquired_by": "agent",
        "storage": "repo-lfs", "fallback": None,
    }


def own_base(generator: Optional[str], acquired: Optional[str]) -> dict:
    return {
        "tier": "OWN", "license": "project-owned", "license_url": None, "mirror_url": None,
        "commercial_use": True, "redistribution": "unrestricted", "derivatives": True, "platform_restriction": None,
        "ai_terms": "none", "agent_handling": "allowed", "attribution_text": None, "changes": None,
        "license_snapshot": None, "access": "generated", "acquired_at_utc": acquired, "acquired_by": "agent",
        "storage": "repo-lfs", "fallback": None, "generator": generator,
    }


def load_snapshot(root: Path) -> dict:
    ledger = root / "scripts/assets/manifests/polyhaven-first-slice.json"
    if ledger.is_file():
        doc = L.load_json(ledger)
        snap = next((s for s in doc.get("license_snapshots", []) if s["name"] == "polyhaven-license"), None)
        if snap:
            return {k: snap[k] for k in ("url", "path", "sha256", "retrieved_at_utc", "via")}
    raise SystemExit("run scripts/assets/fetch_cc0.py first: it snapshots https://polyhaven.com/license")


def build(root: Path, offline: bool) -> dict:
    snapshot = dict(load_snapshot(root))
    snapshot["note"] = ("Retroactive: snapshot taken during the 2026-09-25 schema-2 migration. The original "
                        "acquisitions recorded the license URL and CC0 identifier but kept no terms snapshot.")
    extends, records = [], []
    verified_at = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()
    for base_rel, default_generator in BASES:
        base_path = root / base_rel
        base = L.load_json(base_path)
        base_dir = base_rel.rsplit("/", 1)[0]
        extends.append({"manifest": base_rel, "sha256": sha(base_path), "schema_version": base.get("schema_version")})
        acquired = base.get("license_verified_at_utc") or first_commit_date(root, base_rel)
        pairs = file_pairs(base)
        assets = base.get("assets") or [base]
        for asset in assets:
            asset_id = asset.get("asset_id") or base.get("name") or Path(base_dir).name
            listing = api_listing(asset_id, offline) if asset.get("asset_id") else {}
            upstream, derived = [], []
            asset_pairs = file_pairs(asset) if "assets" in base else pairs
            for rel, digest, entry, trail in asset_pairs:
                path = L.posix(f"{base_dir}/{rel}")
                full = root / path
                record = {"path": path, "sha256": digest, "hash_source": base_rel}
                if entry.get("bytes") is not None:
                    record["bytes"] = entry["bytes"]
                url = entry.get("url") or entry.get("official_url")
                if url:
                    record["url"] = url
                if entry.get("upstream_md5") or entry.get("md5"):
                    record["upstream_md5"] = entry.get("upstream_md5") or entry.get("md5")
                api = listing.get(Path(rel).name)
                is_upstream = bool(url) or "Upstream/" in rel or (trail and trail[-1] in ("texture_files", "upstream_files", "files")) or api is not None
                if api and full.is_file() and not L.is_lfs_pointer(full):
                    record.setdefault("url", api["url"])
                    actual = md5(full)
                    record["upstream_md5_today"] = api["md5"]
                    record["upstream_md5_match"] = actual == api["md5"]
                    record["upstream_checked_at_utc"] = verified_at
                (upstream if is_upstream else derived).append(record)
            if asset.get("asset_id") and upstream:
                used_by = runtime_paths(asset)
                if base_rel == f"{PH}/manifest.json":
                    role = asset["role"]
                    if role == "sky":
                        used_by = [f"{PALETTE_RUNTIME_ROOT}/Textures/T_NyaagyuOvercast.T_NyaagyuOvercast"]
                    else:
                        used_by = [f"{PALETTE_RUNTIME_ROOT}/Textures/T_{role.title()}_{f['channel']}.T_{role.title()}_{f['channel']}" for f in asset["files"]]
                        used_by.append(f"{PALETTE_RUNTIME_ROOT}/MI_Nyaagyu_{role.title()}.MI_Nyaagyu_{role.title()}")
                records.append(dict(public_base(snapshot, acquired), **{
                    "asset_id": asset["asset_id"], "name": asset.get("name") or asset["asset_id"], "kind": "legacy-polyhaven",
                    "origin_url": asset.get("asset_url") or asset.get("upstream_page") or f"https://polyhaven.com/a/{asset['asset_id']}",
                    "metadata_url": asset.get("metadata_url") or asset.get("upstream_api"),
                    "authors": asset.get("authors"), "base_manifest": base_rel,
                    "used_by": used_by, "files": sorted(upstream, key=lambda r: r["path"]),
                }))
            if derived:
                generator = base.get("generator") or default_generator
                records.append(dict(own_base(generator, first_commit_date(root, base_rel) or acquired), **{
                    "asset_id": f"{asset_id}:derived", "name": f"Project-made derivatives of {asset_id}",
                    "kind": "derived-art", "origin_url": generator, "base_manifest": base_rel,
                    "generator_sha256_at_build": base.get("generator_sha256"),
                    "derived_from": DERIVED_FROM.get(base_rel, [asset_id]), "used_by": runtime_paths(base),
                    "files": sorted(derived, key=lambda r: r["path"]),
                }))
    for item in UNLISTED:
        full = root / item["path"]
        listing = api_listing(item["asset_id"], offline)
        api = listing.get(Path(item["path"]).name, {})
        actual_md5 = md5(full)
        files = [{"path": item["path"], "sha256": sha(full), "bytes": full.stat().st_size,
                  "hash_source": f"computed {verified_at[:10]} (no earlier record)", "url": api.get("url"),
                  "upstream_md5_today": api.get("md5"), "upstream_md5_match": (api.get("md5") == actual_md5) if api else None,
                  "upstream_checked_at_utc": verified_at if api else None}]
        records.append(dict(public_base(snapshot, first_commit_date(root, item["path"])), **{
            "asset_id": f"{item['asset_id']}:{item['channel'].lower()}", "name": f"Stone Floor {item['channel']} {item['resolution']}",
            "kind": "legacy-polyhaven", "origin_url": f"https://polyhaven.com/a/{item['asset_id']}",
            "metadata_url": f"https://api.polyhaven.com/files/{item['asset_id']}", "authors": {"Dimitrios Savva": "All"},
            "note": item["note"], "used_by": [], "files": files,
        }))
    for item in OWN_UNLISTED:
        full = root / item["path"]
        records.append(dict(own_base(item["generator"], first_commit_date(root, item["path"])), **{
            "asset_id": Path(item["path"]).stem, "name": "Nyaagyu PBR palette preview render", "kind": "derived-art",
            "origin_url": item["generator"], "derived_from": item["derived_from"], "used_by": [],
            "files": [{"path": item["path"], "sha256": sha(full), "bytes": full.stat().st_size,
                       "hash_source": f"computed {verified_at[:10]} (no earlier record)"}],
        }))
    return {
        "schema_version": L.SCHEMA_VERSION,
        "kind": "asset-ledger",
        "ledger_id": "polyhaven-sourceart-legacy",
        "source": "polyhaven",
        "purpose": "Schema-2 extension of the committed Poly Haven palette and scan manifests (repo LFS copies).",
        "generator": "scripts/assets/migrate_polyhaven_ledger.py",
        "extends": extends,
        "policy": ("The extended schema-1 manifests stay byte-identical because other manifests pin their SHA-256 "
                   "and validators assert schema_version 1. Historical file hashes are copied verbatim."),
        "credit": "Powered by Poly Haven - https://polyhaven.com",
        "records": records,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=L.REPO_ROOT)
    parser.add_argument("--offline", action="store_true", help="skip the Poly Haven API re-check")
    parser.add_argument("--check", action="store_true", help="only report whether the committed extension is current")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    doc = build(root, args.offline)
    out = root / OUT
    if args.check:
        current = L.load_json(out) if out.is_file() else None

        def key(d):
            return d["extends"], sorted((r["asset_id"], f["path"], f["sha256"]) for r in d["records"] for f in r["files"])
        same = current is not None and key(current) == key(doc)
        print("LEDGER_EXTENSION_CURRENT" if same else "LEDGER_EXTENSION_STALE")
        return 0 if same else 1
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    mismatches = [f["path"] for r in doc["records"] for f in r["files"] if f.get("upstream_md5_match") is False]
    print(f"wrote {OUT}: {len(doc['records'])} records, {sum(len(r['files']) for r in doc['records'])} files, "
          f"{len(doc['extends'])} base manifests pinned; upstream MD5 mismatches: {mismatches or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
