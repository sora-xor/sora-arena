"""Install the exact FBX bytes measured by a reviewed Unreal socket probe, without Blender.

Dry-run by default. Give --assets explicitly; only files already listed in the
runtime manifest qualify. The staged report hashes are pinned by --receipt.
All selected files, socket gates, records and inputs are checked before writing.
--apply --archive Saved/<new-directory> backs up every destination first, then
replaces files individually. An exception rolls back; a killed process leaves
the originals and a transaction journal for recovery. This is source correction,
not runtime import, visual acceptance or an atomic multi-file filesystem commit.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "unreal"))
import fbx_socket_export as X
import weapon_socket_gates as G

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = "Content/SourceArt/Weapons/Runtime"
TOOL = "scripts/art/apply_staged_weapon_sockets.py"
RECEIPT = "docs/art-direction/data/runtime_weapon_ue_socket_probe.json"


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=1, allow_nan=False) + "\n").encode()


def decode(data):
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, f"duplicate JSON key: {key}")
            out[key] = value
        return out
    value = json.loads(data, object_pairs_hook=pairs)
    encode(value)  # Reject NaN/Infinity, including overflow such as 1e999.
    return value


def local_file(root, relative):
    path = root / relative
    require(not Path(relative).is_absolute() and path.resolve().is_relative_to(root),
            f"path escapes worktree: {relative}")
    require(path == path.resolve(), f"noncanonical or symlink destination: {relative}")
    require(path.is_file(), f"missing file: {relative}")
    return path


@dataclass
class Plan:
    root: Path
    before: dict[str, bytes]
    after: dict[str, bytes]
    inputs: dict[Path, str]
    summary: dict


def prepare(root, receipt_path, stage_paths, assets, stamp):
    """Read and validate the whole selection; no filesystem writes."""
    root = Path(root).resolve()
    inputs, before, after = {}, {}, {}

    def read(path):
        path = Path(path).resolve()
        data = path.read_bytes()
        inputs[path] = digest(data)
        return data

    def recorded(relative, expected):
        path = local_file(root, relative)
        data = read(path)
        require(digest(data) == expected, f"changed input: {relative}")
        return data

    manifest_path = RUNTIME + "/manifest.json"
    manifest_bytes = read(local_file(root, manifest_path))
    manifest = decode(manifest_bytes)
    require(encode(manifest) == manifest_bytes, "manifest would be reformatted")
    listed = {e["file"]: e for e in manifest["files"]}
    require(len(listed) == len(manifest["files"]), "duplicate manifest paths")
    receipt_bytes = read(receipt_path)
    receipt = decode(receipt_bytes)
    probe = receipt["readback"]
    require(probe["saved_packages"] is False, "expected an unsaved original/corrected probe")
    require(probe["engine"].startswith("5.8.3-58210709"), "unreviewed engine version")
    pinned = {s["sha256"]: s for s in probe["stage_reports"]}
    require(len(pinned) == len(probe["stage_reports"]), "duplicate stage report pins")
    stages, seen = {}, set()
    for path in stage_paths:
        raw = read(path)
        sha = digest(raw)
        require(sha in pinned and sha not in seen, f"unprobed/duplicate stage report: {path}")
        seen.add(sha)
        report = decode(raw)
        require(report["mode"] == "stage" and report["convention"] == X.SOCKET_FBX,
                "wrong staging convention")
        require(report["source"] == pinned[sha]["source"], "stage source differs from probe")
        for row in report["files"]:
            require(row["asset"] not in stages, f"duplicate staged asset: {row['asset']}")
            stages[row["asset"]] = row
    require(seen == set(pinned), "missing probed stage reports")
    require(assets and len(set(assets)) == len(assets), "select distinct assets explicitly")
    records, rewritten, axes = {}, {}, {}
    selected = []
    for asset in sorted(assets):
        require(re.fullmatch(r"SM_Weapon_\d\d(?:_[A-Za-z0-9]+)*", asset), f"invalid asset: {asset}")
        require(asset in stages and asset in probe["imports"], f"asset not probed: {asset}")
        row, measured = stages[asset], probe["imports"][asset]
        file, kit = row["file"], row["kit"]
        require(re.fullmatch(r"W\d\d_[A-Za-z0-9_]+", kit), f"invalid kit: {kit}")
        require(file == f"{RUNTIME}/{kit}/{asset}.fbx", f"unexpected asset path: {file}")
        recpath = f"{RUNTIME}/{kit}/build_record.json"
        require(file in listed and recpath in listed, f"held/unlisted asset: {asset}")
        require(measured["kit"] == kit and measured["provenance"] == row["provenance"],
                f"probe provenance differs: {asset}")
        require(not measured["same_import_failures"], f"import comparison failed: {asset}")
        for tag, sha_key in (("original", "original_sha256"), ("corrected", "new_sha256")):
            require(measured[tag]["sha256"] == row[sha_key], f"probe bytes differ: {asset} {tag}")
            prediction = row["predicted_original" if tag == "original" else "sockets_in_unreal"]
            require(G.agrees(G.model_agreement(measured[tag]["sockets"], prediction)),
                    f"model disagreement: {asset} {tag}")
        failures = G.socket_failures(measured["corrected"]["sockets"], row["record_sockets"],
                                     row["socket_axes"], re.fullmatch(r"SM_Weapon_\d\d", asset) is not None)
        require(not failures, f"socket failure: {asset}: {failures}")
        require(measured["original"]["materials"] == measured["corrected"]["materials"] and
                measured["original"]["collision"] == measured["corrected"]["collision"],
                f"material/collision change: {asset}")
        if kit not in records:
            raw = recorded(recpath, listed[recpath]["sha256"])
            record = decode(raw)
            require(encode(record) == raw, f"record would be reformatted: {kit}")
            require("socket_fbx" not in record, f"already corrected: {kit}")
            # Preserve every input recorded for the kit, including untouched LODs/maps/blend.
            for entry in [record["blend"], *record["textures"].values(),
                          *(lod for a in record["assets"].values() for lod in a["lods"])]:
                recorded(entry["file"], entry["sha256"])
            records[kit], before[recpath] = record, raw
            rewritten[kit], axes[kit] = {}, {}
        entry = records[kit]["assets"][asset]
        require(entry["sockets"] == row["record_sockets"], f"authored positions changed: {asset}")
        require(entry["lods"][0]["file"] == file and
                entry["lods"][0]["sha256"] == row["original_sha256"] == listed[file]["sha256"],
                f"record/manifest/source mismatch: {asset}")
        before[file] = recorded(file, row["original_sha256"])
        new = read(row["new_path"])
        require(digest(new) == row["new_sha256"], f"staged bytes changed: {asset}")
        after[file] = new
        rewritten[kit][asset] = (file, digest(new), digest(before[file]))
        axes[kit][asset] = row["socket_axes"]
        selected.append({"asset": asset, "file": file, "sha256": digest(new),
                         "replaces_sha256": digest(before[file])})
    for kit, record in records.items():
        after[f"{RUNTIME}/{kit}/build_record.json"] = encode(
            X.amend_record(record, rewritten[kit], axes[kit], TOOL))
    changes = []
    for file, data in sorted(after.items()):
        change = {"file": file, "bytes": len(data), "sha256": digest(data)}
        listed[file].update(change)
        changes.append(change)
    manifest.setdefault("scoped_updates", []).append({
        "key": "socket_fbx", "recorded_at_utc": stamp,
        "scope": "Exact staged LOD0 bytes from the recorded UE probe; no re-export, runtime import or visual approval.",
        "tool": {"path": TOOL, "sha256": digest(Path(__file__).read_bytes())},
        "receipt": {"path": RECEIPT, "sha256": digest(receipt_bytes), "run": receipt["readback_of"]},
        "stage_report_sha256": sorted(seen), "replacements": selected, "files": changes})
    before[manifest_path], after[manifest_path] = manifest_bytes, encode(manifest)
    return Plan(root, before, after, inputs,
                {"assets": sorted(assets), "files_changed": len(after), "fbx_bytes": sum(len(after[r["file"]]) for r in selected),
                 "receipt_sha256": digest(receipt_bytes), "runtime_adopted": False})


def install(plan, archive):
    """Backup all originals, check every precondition again, replace; rollback on exception."""
    archive = Path(archive).resolve()
    require(archive.is_relative_to(plan.root / "Saved") and archive != plan.root / "Saved",
            "archive must be a new directory under this worktree's Saved/")
    require(not archive.exists(), "archive already exists")
    for path, sha in plan.inputs.items():
        require(digest(path.read_bytes()) == sha, f"input changed after planning: {path}")
    archive.mkdir(parents=True)
    journal = {**plan.summary, "state": "prepared", "files": [
        {"file": f, "before_sha256": digest(plan.before[f]), "after_sha256": digest(data)}
        for f, data in sorted(plan.after.items())]}
    for group, entries in (("original", plan.before), ("candidate", plan.after)):
        for relative, data in entries.items():
            path = archive / group / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    report = archive / "transaction.json"
    report.write_bytes(encode(journal))
    changed = []
    try:
        for relative, data in plan.after.items():
            target = local_file(plan.root, relative)
            require(target.read_bytes() == plan.before[relative], f"destination changed: {relative}")
            os.replace(archive / "candidate" / relative, target)
            changed.append(relative)
            require(target.read_bytes() == data, f"installed bytes differ: {relative}")
        journal["state"] = "installed"
        report.write_bytes(encode(journal))
    except BaseException:
        errors = []
        for relative in reversed(changed):
            try:
                source = archive / "original" / relative
                rollback = archive / "candidate" / relative
                shutil.copyfile(source, rollback)
                os.replace(rollback, plan.root / relative)
            except OSError as error:
                errors.append(f"{relative}: {error}")
        journal.update(state="rollback_failed" if errors else "rolled_back", rollback_errors=errors)
        report.write_bytes(encode(journal))
        raise
    return journal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, default=ROOT / RECEIPT)
    parser.add_argument("--stage-report", type=Path, action="append", required=True)
    parser.add_argument("--assets", nargs="+", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    require(not args.apply or args.archive, "--apply requires --archive Saved/<new-directory>")
    plan = prepare(ROOT, args.receipt, args.stage_report, args.assets, datetime.now(timezone.utc).isoformat())
    result = install(plan, ROOT / args.archive) if args.apply else {**plan.summary, "state": "dry_run"}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
