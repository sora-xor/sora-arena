#!/usr/bin/env python3
"""Preflight and byte-for-byte archive of Estate renderer diagnostic evidence.

This tool never launches Unreal or changes project assets, lighting, or gameplay.
Visualization captures are made with the engine UI or a disposable diagnostic
package as described in docs/render-qualification/estate-lumen-nanite.md.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import sys


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts/unreal"))
import sora_engine_pin  # noqa: E402

PINS = json.loads((REPO / "scripts/toolchain/versions.json").read_text())
CAMERAS = {
    "Entrance": {"location_cm": [-2696, 0, 154.15], "rotation_deg": [0, 0, 0], "horizontal_fov_deg": 94},
    "ToriiFoot": {"location_cm": [-2500, 235, 90.15], "rotation_deg": [-28, 0, 0], "horizontal_fov_deg": 65},
}
COMMON_CAPTURES = (
    "Estate_Entrance_Lit.png",
    "Estate_Entrance_LumenOverview.png",
    "Estate_Entrance_LumenScene.png",
    "Estate_Entrance_LumenSurfaceCache.png",
    "Estate_Entrance_LumenCardPlacement.png",
    "Estate_ToriiFoot_Lit.png",
    "Estate_ToriiFoot_LumenSurfaceCache.png",
    "Estate_ToriiFoot_LumenCardPlacement.png",
)
MAC_CAPTURES = (
    "Estate_Entrance_MeshDistanceFields.png",
    "Estate_Entrance_GlobalDistanceField.png",
)
WINDOWS_CAPTURES = (
    "Estate_Entrance_NaniteMask.png",
    "Estate_Entrance_NaniteTriangles.png",
    "Estate_Entrance_NaniteClusters.png",
    "Estate_Entrance_NaniteStats.png",
    "Estate_ToriiFoot_NaniteMask.png",
)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as stream:
        header = stream.read(24)
    if len(header) != 24 or header[:8] != PNG_SIGNATURE or header[12:16] != b"IHDR":
        raise ValueError(f"invalid PNG header: {path}")
    return struct.unpack(">II", header[16:24])


def engine_info(engine_root: Path) -> dict:
    try:
        version = sora_engine_pin.require_engine_root(engine_root)
    except RuntimeError as exc:
        raise ValueError(str(exc)) from exc
    version_file = engine_root / "Engine/Build/Build.version"
    return {"version": version, "engine_version": sora_engine_pin.ENGINE_VERSION,
            "build_version": json.loads(version_file.read_text()),
            "build_version_sha256": sha256(version_file), "root": str(engine_root.resolve()),
            "release_source_commit_pin": PINS["unreal"]["source_commit"]}


def git_head(project_root: Path) -> dict:
    def run(*args: str) -> str:
        return subprocess.run(["git", "-C", str(project_root), *args], text=True,
                              check=True, capture_output=True).stdout.strip()
    return {"head": run("rev-parse", "HEAD"), "worktree_dirty": bool(run("status", "--porcelain"))}


def project_info(project_root: Path, system: str) -> dict:
    projects = tuple(project_root.glob("*.uproject"))
    if len(projects) != 1:
        raise ValueError(f"expected exactly one root .uproject, found {len(projects)}")
    project_file = projects[0]
    project = json.loads(project_file.read_text())
    if project.get("EngineAssociation") != "5.8":
        raise ValueError("project EngineAssociation is not 5.8")
    engine_config = (project_root / "Config/DefaultEngine.ini").read_text()
    required = ("r.GenerateMeshDistanceFields=True", "r.DynamicGlobalIlluminationMethod=1",
                "r.ReflectionMethod=1")
    for line in required:
        if line not in engine_config:
            raise ValueError(f"required renderer setting absent: {line}")
    mac_config_sha = None
    if system == "mac":
        mac_file = project_root / "Config/Mac/MacEngine.ini"
        mac_config = mac_file.read_text()
        for line in ("r.RayTracing=False", "r.Nanite.ProxyRenderMode=0"):
            if line not in mac_config:
                raise ValueError(f"required Mac fallback setting absent: {line}")
        mac_config_sha = sha256(mac_file)
    return {"project": project_file.name, "project_sha256": sha256(project_file),
            "default_engine_ini_sha256": sha256(project_root / "Config/DefaultEngine.ini"),
            "mac_engine_ini_sha256": mac_config_sha, **git_head(project_root)}


def expected_captures(system: str) -> tuple[str, ...]:
    return COMMON_CAPTURES + (MAC_CAPTURES if system == "mac" else WINDOWS_CAPTURES)


def preflight(args: argparse.Namespace) -> dict:
    engine = engine_info(args.engine_root.expanduser())
    project = project_info(args.project_root.expanduser(), args.platform)
    return {"schema": 1, "engine": engine, "project": project,
            "host": platform.platform(), "capture_platform": args.platform,
            "cameras": CAMERAS, "required_captures": expected_captures(args.platform),
            "limitations": [
                "The pinned engine is a Launcher binary build; its changelist, not a source commit, identifies it.",
                "M1 Ultra Mac fallback captures cannot qualify Windows Nanite or RTX performance.",
            ]}


def archive(args: argparse.Namespace) -> dict:
    info = preflight(args)
    capture_dir = args.capture_dir.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if output.exists():
        raise ValueError(f"archive destination already exists; refusing to overwrite evidence: {output}")
    if not capture_dir.is_dir():
        raise ValueError(f"capture directory missing: {capture_dir}")
    inputs = {"commands.txt": args.command_log.expanduser().resolve()}
    for index, raw_log in enumerate(args.runtime_log, start=1):
        inputs[f"logs/run-{index:02d}.log"] = raw_log.expanduser().resolve()
    for name, path in inputs.items():
        if not path.is_file() or not path.stat().st_size:
            raise ValueError(f"missing or empty raw {name}: {path}")
    records = []
    for name in expected_captures(args.platform):
        path = capture_dir / name
        if not path.is_file():
            records.append({"filename": name, "status": "missing"})
            continue
        dimensions = png_dimensions(path)
        if dimensions != (args.width, args.height):
            raise ValueError(f"{name}: {dimensions} differs from fixed {args.width}x{args.height} viewport")
        records.append({"filename": name, "status": "captured", "width": dimensions[0],
                        "height": dimensions[1], "sha256": sha256(path), "bytes": path.stat().st_size})
    complete = all(record["status"] == "captured" for record in records)
    if not complete and not args.allow_incomplete:
        missing = ", ".join(r["filename"] for r in records if r["status"] == "missing")
        raise ValueError(f"required raw captures missing: {missing}; use --allow-incomplete only to archive a failed diagnostic")
    output.mkdir(parents=True)
    for record in records:
        if record["status"] == "captured":
            shutil.copy2(capture_dir / record["filename"], output / record["filename"])
    (output / "logs").mkdir()
    for name, path in inputs.items():
        shutil.copy2(path, output / name)
    info.update({"archive_created_utc": datetime.now(timezone.utc).isoformat(),
                 "capture_complete": complete, "captures": records,
                 "hardware_label": args.hardware_label,
                 "viewport_px": [args.width, args.height],
                 "raw_logs": {name: {"sha256": sha256(output / name),
                                       "bytes": (output / name).stat().st_size} for name in inputs}})
    (output / "manifest.json").write_text(json.dumps(info, indent=2, sort_keys=True) + "\n")
    sums = [(sha256(path), path.relative_to(output).as_posix())
            for path in output.rglob("*") if path.is_file()]
    (output / "SHA256SUMS").write_text("".join(f"{digest}  {name}\n" for digest, name in sorted(sums, key=lambda item: item[1])))
    return info


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=REPO)
    parser.add_argument("--engine-root", type=Path,
                        default=Path(PINS["unreal"]["default_macos_root"]))
    parser.add_argument("--platform", choices=("mac", "windows"), required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("preflight")
    archive_parser = sub.add_parser("archive")
    archive_parser.add_argument("--capture-dir", type=Path, required=True)
    archive_parser.add_argument("--runtime-log", type=Path, required=True, action="append",
                                help="Repeat for every unfiltered packaged-game run log")
    archive_parser.add_argument("--command-log", type=Path, required=True)
    archive_parser.add_argument("--output", type=Path, required=True)
    archive_parser.add_argument("--hardware-label", required=True)
    archive_parser.add_argument("--width", type=int, default=1280)
    archive_parser.add_argument("--height", type=int, default=720)
    archive_parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()
    try:
        result = preflight(args) if args.command == "preflight" else archive(args)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"estate-render-evidence: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
