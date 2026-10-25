"""Read-only verification of a finished timber pilot run, with its own receipt.

The Blender driver (create_nyaagyu_dojo_timbers_pilot.py ``--verify``)
rebuilds each member and its canonical digest. Everything else is here,
without bpy, so it can be tested:

* **The run is only read.** Its ``manifest.json``, ``evidence.json``,
  ``checks.json``, FBX and Shared textures are opened for reading; nothing in
  the run is written, rewritten or regenerated.
* **What is compared:**
  - each FBX's SHA-256 and bytes on disk against the original evidence;
  - the rebuilt canonical digests against the manifest and the evidence;
  - the rebuilt check reports against the original ``checks.json``;
  - the Shared textures on disk, and as rebuilt in a temporary directory,
    against the manifest;
  - the current generator and inputs against the manifest;
  - every file of the run against its archive receipt, when one is given.
* **A new, unique receipt** is written outside the run, under
  ``Local/ArtCache/Verification/<namespace>/``. Its name carries the UTC time
  and the process id, and it is created exclusively, so a receipt is never
  overwritten.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERIFY_ROOT = ROOT / "Local/ArtCache/Verification"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_run(run_dir: Path):
    """The run's manifest, evidence and checks, read-only."""
    run_dir = Path(run_dir)
    read = lambda name: json.loads((run_dir / name).read_text())  # noqa: E731
    return read("manifest.json"), read("evidence.json"), read("checks.json")


def compare_fbx(root: Path, evidence: dict):
    """Each FBX the original evidence lists, against its file on disk now."""
    out = []
    for rel, want in sorted(evidence.get("fbx", {}).items()):
        path = Path(root) / rel
        have = {"sha256": sha256(path), "bytes": path.stat().st_size} if path.is_file() else {"sha256": None, "bytes": None}
        out.append({"file": rel, "expected_sha256": want.get("sha256"), "expected_bytes": want.get("bytes"),
                    "sha256": have["sha256"], "bytes": have["bytes"],
                    "ok": have["sha256"] == want.get("sha256") and have["bytes"] == want.get("bytes")})
    return out


def compare_digests(manifest: dict, evidence: dict, rebuilt: dict):
    """Rebuilt canonical digests ({asset: (dense, fallback)}) against the
    manifest's records and the original evidence's."""
    by_file = {Path(rel).name: e.get("digest") for rel, e in evidence.get("fbx", {}).items()}
    out = []
    for rec in manifest.get("members", []):
        name = rec["asset"]
        got = rebuilt.get(name)
        for label, want, fbx in (("dense", rec.get("digest"), Path(rec.get("cache_fbx", "")).name),
                                 ("fallback", rec.get("fallback_digest"), Path(rec.get("fallback_fbx", "")).name)):
            have = None if got is None else got[0 if label == "dense" else 1]
            out.append({"asset": name, "mesh": label, "expected_manifest": want, "expected_evidence": by_file.get(fbx),
                        "rebuilt": have, "ok": have is not None and have == want == by_file.get(fbx)})
    for name in sorted(set(rebuilt) - {r["asset"] for r in manifest.get("members", [])}):
        out.append({"asset": name, "mesh": "dense", "expected_manifest": None, "expected_evidence": None,
                    "rebuilt": rebuilt[name][0], "ok": False})
    return out


def compare_checks(original: dict, rebuilt: dict):
    """Rebuilt check reports against the original checks.json, entry by entry."""
    canon = lambda v: json.dumps(v, sort_keys=True)  # noqa: E731
    out = []
    for key in sorted(set(original) | set(rebuilt)):
        a, b = original.get(key), rebuilt.get(key)
        out.append({"entry": key, "present": [a is not None, b is not None],
                    "ok_flag": [None if a is None else a.get("ok"), None if b is None else b.get("ok")],
                    "identical": a is not None and b is not None and canon(a) == canon(json.loads(json.dumps(b)))})
    return out


def compare_shared(root: Path, manifest: dict, rebuilt_dir: Path):
    """Each shared texture: the manifest's SHA, the file on disk now, and the
    texture as rebuilt into ``rebuilt_dir`` (never into the run)."""
    out = []
    for key, want in sorted(manifest.get("shared_textures", {}).items()):
        on_disk = Path(root) / want["file"]
        rebuilt = Path(rebuilt_dir) / on_disk.name
        have = sha256(on_disk) if on_disk.is_file() else None
        again = sha256(rebuilt) if rebuilt.is_file() else None
        out.append({"texture": key, "file": want["file"], "expected_sha256": want["sha256"], "sha256": have,
                    "rebuilt_sha256": again, "ok": have == want["sha256"] == again})
    return out


def compare_inputs(root: Path, manifest: dict):
    """The generator and every input now, against the manifest."""
    def entry(rel, want):
        path = Path(root) / rel
        have = sha256(path) if path.is_file() else None
        return {"file": rel, "expected_sha256": want, "sha256": have, "same": have == want}
    gen = entry(manifest["generator"], manifest["generator_sha256"])
    inputs = [entry(rel, want) for rel, want in sorted(manifest.get("inputs", {}).items())]
    return {"generator": gen, "inputs": inputs, "changed_inputs": [e["file"] for e in inputs if not e["same"]]}


def compare_archive(run_dir: Path, receipt: Path):
    """Every file of the run against its archive receipt (archive_art_run.py)."""
    import archive_art_run as A
    want = json.loads(Path(receipt).read_text())
    files = A.listing(Path(run_dir))
    have = {f["path"]: f for f in files}
    expected = {f["path"]: f for f in want["files"]}
    changed = sorted(p for p in expected if p in have and have[p]["sha256"] != expected[p]["sha256"])
    return {"receipt": str(receipt), "expected_files_digest": want["files_digest"], "files_digest": A.files_digest(files),
            "missing": sorted(set(expected) - set(have)), "added": sorted(set(have) - set(expected)), "changed": changed,
            "ok": A.files_digest(files) == want["files_digest"]}


def receipt_path(namespace: str, base: Path = VERIFY_ROOT, now: dt.datetime | None = None, pid: int | None = None):
    now = now or dt.datetime.now(dt.timezone.utc)
    return Path(base) / namespace / f"verify_{now.strftime('%Y%m%dT%H%M%S%fZ')}_{pid or os.getpid()}.json"


def write_receipt(path: Path, run_dir: Path, data: dict, frozen=()):
    """Create the receipt exclusively, refusing any path inside the run or a frozen tree."""
    p = Path(path).resolve()
    for keep in (Path(run_dir), *frozen):
        k = Path(keep).resolve()
        if p == k or k in p.parents:
            raise ValueError(f"verify: refusing to write a receipt inside {k}: {p}")
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "x") as f:
        f.write(json.dumps(data, indent=1) + "\n")
    return p


def verdict(fbx, digests, checks, shared, inputs, archive=None):
    """VERIFIED only if everything matches. INPUTS_CHANGED when an input
    differs from the manifest, since a rebuild can't then reproduce the run. Else MISMATCH."""
    problems = ([f"fbx {e['file']}" for e in fbx if not e["ok"]]
                + [f"digest {e['asset']}:{e['mesh']}" for e in digests if not e["ok"]]
                + [f"checks {e['entry']}" for e in checks if not e["identical"]]
                + [f"shared {e['texture']}" for e in shared if not e["ok"]]
                + ([] if archive is None or archive["ok"] else ["archive files_digest"]))
    if inputs["changed_inputs"]:
        return "INPUTS_CHANGED", problems + [f"input {p}" for p in inputs["changed_inputs"]]
    return ("VERIFIED" if not problems else "MISMATCH"), problems
