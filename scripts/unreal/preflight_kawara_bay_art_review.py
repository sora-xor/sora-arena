#!/usr/bin/env python3
"""Verify the source-only kawara bay and optionally import it into ArtReview.

The --run path is deliberately gated. It never cooks or edits a playable map.
UE 5.8.3 is diagnostic-only and must run in a separate Git worktree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


SOURCE_REL = Path("Content/SourceArt/Environment/NyaagyuKawaraBay")
LOGO_REL = Path("Content/SourceArt/UI")
MIN_FREE_BYTES = 30 * 1024**3
SUCCESS = "SORA_KAWARA_ART_REVIEW_IMPORT_OK"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    require(path.is_file(), f"Missing source file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def check_source(project: Path) -> None:
    source = project / SOURCE_REL
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    texture = json.loads((source / "texture_manifest.json").read_text(encoding="utf-8"))
    logo = json.loads((project / LOGO_REL / "sora_logo_manifest.json").read_text(encoding="utf-8"))
    require("source-only" in manifest.get("status", ""), "Roof is no longer labeled source-only")
    require(manifest.get("tile_count") == {"pan": 30, "cover": 25},
            "Roof tile population changed")
    require(manifest.get("generator") == "scripts/art/create_nyaagyu_kawara_bay.py",
            "Roof generator identity changed")
    require(texture.get("layout") == "4x4" and texture.get("size") == [2048, 2048]
            and "source-only" in texture.get("status", ""),
            "Roof PBR atlas identity or source-only policy changed")
    require(set(texture.get("files", {})) == {"Albedo", "NormalDX", "ORM"},
            "Roof PBR channels changed")
    for role, item in texture["files"].items():
        require(sha256(source / item["file"]) == item["sha256"],
                f"Roof PBR {role} hash changed")
    require(sha256(source / "SM_Nyaagyu_KawaraBay.fbx") ==
            manifest["outputs"]["SM_Nyaagyu_KawaraBay.fbx"], "Roof FBX hash changed")
    generated = manifest["generated_albedo"]
    require(generated.get("role", "").startswith("source-only"),
            "Generated albedo must remain a source-only reference")
    require(sha256(source / generated["file"]) == generated["sha256"],
            "Generated albedo hash changed")
    require(logo.get("runtime_png") == "SORA_Resistance_Logo.png" and
            logo["runtime_sha256"] == manifest["sora_logo_raster_sha256"] and
            sha256(project / LOGO_REL / logo["runtime_png"]) == logo["runtime_sha256"],
            "Supplied SORA logo identity changed")
    require("r.Nanite=0" in (project / "Config/Mac/MacEngine.ini").read_text(),
            "Mac conventional mesh fallback policy changed")


def check_optional_ibushi(project: Path) -> bool:
    """Accept only a complete, hash-matched coherent PBR set if supplied."""
    source = project / SOURCE_REL
    manifest_path = source / "ibushi_texture_manifest.json"
    if not manifest_path.is_file():
        return False
    record = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(record.get("source_type") == "algorithmically painted; no third-party pixels"
            and "source-only" in record.get("status", "")
            and record.get("size") == [2048, 2048]
            and record.get("layout") == "4x4"
            and set(record.get("files", {})) == {"Albedo", "NormalDX", "ORM"},
            "Optional ibushi PBR atlas identity changed")
    for role, item in record["files"].items():
        require(sha256(source / item["file"]) == item["sha256"],
                f"Optional ibushi {role} hash changed")
    return True


def editor_binary(engine_root: Path) -> tuple[Path, str]:
    version_file = engine_root / "Engine/Build/Build.version"
    require(version_file.is_file(), f"Engine version file missing: {version_file}")
    build = json.loads(version_file.read_text(encoding="utf-8"))
    version = ".".join(str(build[field]) for field in
                       ("MajorVersion", "MinorVersion", "PatchVersion"))
    relative = ("Engine/Binaries/Mac/UnrealEditor-Cmd" if sys.platform == "darwin" else
                "Engine/Binaries/Win64/UnrealEditor-Cmd.exe" if sys.platform == "win32" else
                "Engine/Binaries/Linux/UnrealEditor-Cmd")
    editor = engine_root / relative
    require(editor.is_file(), f"Unreal Editor command binary missing: {editor}")
    return editor, version


def active_heavy_builds() -> list[str]:
    if sys.platform == "win32":
        # Windows task enumeration is not portable from this Python script.
        return []
    result = subprocess.run(["ps", "-axo", "comm="], capture_output=True,
                            text=True, check=False)
    require(result.returncode == 0, "Could not inspect competing build processes")
    heavy = {"cargo", "rustc", "blender", "Blender", "UnrealEditor",
             "UnrealEditor-Cmd", "UnrealBuildTool", "ShaderCompileWorker"}
    return sorted({Path(line.strip()).name for line in result.stdout.splitlines()
                   if Path(line.strip()).name in heavy})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path,
                        default=Path(__file__).resolve().parents[2])
    parser.add_argument("--engine-root", type=Path)
    parser.add_argument("--allow-diagnostic-5.8.3", dest="allow_diagnostic_5_8_3",
                        action="store_true")
    parser.add_argument("--run", action="store_true",
                        help="Run editor import after version/worktree/free-space gates")
    args = parser.parse_args()
    project = args.project_root.expanduser().resolve()
    require((project / "SoraArena.uproject").is_file(), "SoraArena project is missing")
    check_source(project)
    ibushi = check_optional_ibushi(project)
    print("SORA_KAWARA_SOURCE_PREFLIGHT_OK: source hashes, logo, Mac policy "
          f"and ibushi={'validated' if ibushi else 'absent'}")
    if not args.run:
        return
    require(args.engine_root is not None, "--run requires --engine-root")
    editor, version = editor_binary(args.engine_root.expanduser().resolve())
    require(version == "5.8.2" or
            (args.allow_diagnostic_5_8_3 and version == "5.8.3"),
            f"UE {version} is not the pinned release engine; 5.8.3 is diagnostic-only")
    if version == "5.8.3":
        require((project / ".git").is_file(),
                "UE 5.8.3 diagnostic import requires a separate Git worktree")
    available = shutil.disk_usage(project).free
    require(available >= MIN_FREE_BYTES,
            f"Import needs at least 30 GiB free; found {available / 1024**3:.1f} GiB")
    competing = active_heavy_builds()
    require(not competing, f"Competing heavy builds are active: {', '.join(competing)}")
    editor_script = project / "scripts/unreal/import_nyaagyu_kawara_bay_art_review.py"
    require(editor_script.is_file(), f"Editor import script missing: {editor_script}")
    log = project / "Saved/Logs/kawara_art_review_import.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    command = [str(editor), str(project / "SoraArena.uproject"),
               f"-ExecutePythonScript={editor_script}", "-Unattended", "-NullRHI",
               "-NoSplash", "-NoSound", "-stdout", "-FullStdOutLogOutput"]
    environment = dict(os.environ, SORA_KAWARA_ART_REVIEW_ENGINE=version)
    with log.open("w", encoding="utf-8") as stream:
        result = subprocess.run(command, cwd=project, env=environment, stdout=stream,
                                stderr=subprocess.STDOUT, timeout=1800, check=False)
    output = log.read_text(encoding="utf-8", errors="replace")
    require(result.returncode == 0 and SUCCESS in output and
            "SORA_KAWARA_ART_REVIEW_REJECTED" not in output and
            "LogPython: Error" not in output,
            f"UE art-review import failed or emitted no success marker; inspect {log}")
    print(f"{SUCCESS}: UE {version} assets staged; inspect {log}")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, subprocess.TimeoutExpired, KeyError, ValueError) as error:
        print(f"SORA_KAWARA_ART_REVIEW_REJECTED: {error}", file=sys.stderr)
        sys.exit(1)
