"""The pinned Unreal Engine identity for every SORA Arena editor script.

``scripts/toolchain/versions.json`` is the only source of the pin; there is no
override. Unreal Python scripts call ``require_running_engine`` before touching
assets. Host-side preflights call ``require_engine_root`` before launching an
editor. Both raise ``RuntimeError`` on any mismatch or unreadable identity.
"""

from __future__ import annotations

import json
from pathlib import Path

PINS_PATH = Path(__file__).resolve().parents[1] / "toolchain" / "versions.json"
PIN = json.loads(PINS_PATH.read_text(encoding="utf-8"))["unreal"]
# FEngineVersion::Current().ToString(), as returned by
# unreal.SystemLibrary.get_engine_version() and logged as "Engine Version:".
ENGINE_VERSION = f'{PIN["version"]}-{PIN["changelist"]}+{PIN["branch"]}'
BUILD_FIELDS = (
    ("unreal_changelist", "Changelist", "changelist"),
    ("unreal_compatible_changelist", "CompatibleChangelist", "compatible_changelist"),
    ("unreal_branch", "BranchName", "branch"),
    ("unreal_promoted_build", "IsPromotedBuild", "is_promoted_build"),
    ("unreal_licensee_version", "IsLicenseeVersion", "is_licensee_version"),
)
INSTALLED_BUILD = "installed build (Engine/Build/InstalledBuild.txt)"


def _check(name, actual, expected, detail=None):
    entry = {"name": name, "actual": actual, "expected": expected, "ok": actual == expected}
    if detail:
        entry["detail"] = detail
    return entry


def _plugin_identity(engine_root: Path, descriptor: str):
    try:
        data = json.loads((engine_root / descriptor).read_text(encoding="utf-8-sig"))
        return f'{data["VersionName"]} (version {data["Version"]})'
    except (OSError, ValueError, KeyError, TypeError):
        return None


def identity_checks(engine_root: Path, plugin_groups=("plugins",)) -> list[dict]:
    """Compare an installed engine's Build.version, distribution and plugins with the pin."""
    engine_root = Path(engine_root)
    version_path = engine_root / "Engine/Build/Build.version"
    try:
        build = json.loads(version_path.read_text(encoding="utf-8-sig"))
        version = ".".join(str(build[key]) for key in ("MajorVersion", "MinorVersion", "PatchVersion"))
        error = None
    except (OSError, ValueError, KeyError, TypeError) as exc:
        build, version, error = {}, None, f"{version_path}: {exc}"
    checks = [_check("unreal", version, PIN["version"], error or str(engine_root))]
    checks += [_check(name, build.get(field), PIN[key]) for name, field, key in BUILD_FIELDS]
    installed = (engine_root / "Engine/Build/InstalledBuild.txt").is_file()
    checks.append(_check("unreal_distribution",
                         INSTALLED_BUILD if installed else "not an installed build",
                         INSTALLED_BUILD, PIN["distribution"]))
    for group in plugin_groups:
        pins = PIN[group]
        actual = {name: _plugin_identity(engine_root, pin["descriptor"]) for name, pin in pins.items()}
        expected = {name: f'{pin["version_name"]} (version {pin["version"]})' for name, pin in pins.items()}
        checks.append(_check(f"unreal_{group}", actual, expected))
    return checks


def require_engine_root(engine_root: Path, plugin_groups=("plugins",)) -> str:
    """Fail closed unless ``engine_root`` is the pinned engine; return its version."""
    failed = [check for check in identity_checks(engine_root, plugin_groups) if not check["ok"]]
    if failed:
        details = "; ".join(f'{c["name"]}: {c["actual"]!r} != {c["expected"]!r}' for c in failed)
        raise RuntimeError(f"{engine_root} is not the pinned Unreal Engine {ENGINE_VERSION}: {details}")
    return PIN["version"]


def require_engine_version(actual: str, purpose: str) -> str:
    """Fail closed unless ``actual`` is exactly the pinned FEngineVersion string."""
    if actual != ENGINE_VERSION:
        raise RuntimeError(f"{purpose} requires pinned Unreal Engine {ENGINE_VERSION}; got {actual}")
    return actual


def require_running_engine(purpose: str) -> str:
    """Call first from an Unreal Python script; raises in any other engine."""
    import unreal

    return require_engine_version(unreal.SystemLibrary.get_engine_version(), purpose)
