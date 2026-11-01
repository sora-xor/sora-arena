"""Archive a finished art generation run: a receipt of every output, then read-only.

Usage:
  python3 scripts/art/archive_art_run.py RUN_DIR --archive ARCHIVE_DIR --label LABEL \
      --log LOG --exit-code CODE [--marker PILOT_] [--copy-to TRACKED.json]

It writes ARCHIVE_DIR/receipt.json and a copy of the run's log. Both are
created exclusively, so an archive is never overwritten. It then removes write
permission from every file and directory in RUN_DIR, so no later generation
can write into the archived run. (To delete it for disk, ``chmod -R u+w``
first.)

The receipt records:
* every file's path, bytes and SHA-256;
* the totals for each top-level folder;
* the log's digest and its marker lines (``PILOT_MEMBER``, ``PILOT_RENDER``,
  ``PILOT_READY``...);
* the exit code;
* ``files_digest``, a SHA-256 over the sorted file list, for a one-line comparison.

``--copy-to`` also writes the receipt to a tracked path, so the evidence
survives the untracked cache.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rel(path: Path) -> str:
    p = Path(path).resolve()
    try:
        return p.relative_to(ROOT).as_posix()
    except ValueError:
        return p.as_posix()


def listing(run_dir: Path):
    files = []
    for p in sorted(run_dir.rglob("*")):
        if p.is_file() and not p.is_symlink():
            files.append({"path": p.relative_to(run_dir).as_posix(), "bytes": p.stat().st_size, "sha256": sha256(p)})
    return files


def files_digest(files) -> str:
    canon = json.dumps([[f["path"], f["bytes"], f["sha256"]] for f in files], separators=(",", ":"))
    return hashlib.sha256(canon.encode()).hexdigest()


def receipt(run_dir: Path, label: str, log: Path, exit_code: int, marker: str):
    files = listing(run_dir)
    totals = {}
    for f in files:
        top = f["path"].split("/", 1)[0] if "/" in f["path"] else "."
        t = totals.setdefault(top, {"files": 0, "bytes": 0})
        t["files"] += 1
        t["bytes"] += f["bytes"]
    lines = [ln.rstrip("\n") for ln in log.read_text(errors="replace").splitlines() if ln.startswith(marker)]
    return {
        "schema_version": 1,
        "kind": "art-run-archive",
        "label": label,
        "run_dir": rel(run_dir),
        "archived_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "exit_code": exit_code,
        "log": {"path": rel(log), "bytes": log.stat().st_size, "sha256": sha256(log), "markers": lines},
        "totals": {"files": len(files), "bytes": sum(f["bytes"] for f in files), "by_folder": totals},
        "files_digest": files_digest(files),
        "files": files,
    }


def write_exclusive(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "x") as f:          # never overwrite an archive
        f.write(text)


def make_read_only(run_dir: Path):
    for p in sorted(run_dir.rglob("*"), key=lambda q: len(q.parts), reverse=True):
        if p.is_symlink():
            continue
        mode = p.stat().st_mode
        p.chmod(mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
    run_dir.chmod(run_dir.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))


def archive(run_dir: Path, archive_dir: Path, label: str, log: Path, exit_code: int, marker: str = "PILOT_",
            copy_to: Path | None = None):
    run_dir, archive_dir, log = Path(run_dir), Path(archive_dir), Path(log)
    if not run_dir.is_dir():
        raise FileNotFoundError(run_dir)
    if archive_dir.resolve() == run_dir.resolve() or run_dir.resolve() in archive_dir.resolve().parents:
        raise ValueError("the archive must live outside the run it archives")
    r = receipt(run_dir, label, log, exit_code, marker)
    text = json.dumps(r, indent=1) + "\n"
    write_exclusive(archive_dir / "receipt.json", text)
    log_copy = archive_dir / log.name
    if log_copy.exists():
        raise FileExistsError(log_copy)
    shutil.copy2(log, log_copy)
    if copy_to is not None:
        write_exclusive(Path(copy_to), text)
    make_read_only(run_dir)
    return r


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--archive", type=Path, required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--log", type=Path, required=True)
    ap.add_argument("--exit-code", type=int, required=True)
    ap.add_argument("--marker", default="PILOT_")
    ap.add_argument("--copy-to", type=Path)
    a = ap.parse_args(argv)
    r = archive(a.run_dir, a.archive, a.label, a.log, a.exit_code, a.marker, a.copy_to)
    print(f"ARCHIVED {r['run_dir']} {r['totals']['files']} files {r['totals']['bytes']} bytes "
          f"files_digest {r['files_digest']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
