"""Host tests of the combined art/environment/VFX/audio import; never run Unreal.

The import must build every Niagara system: a developer's SORA_VFX_ONLY or
SORA_VFX_REUSE_MATERIALS never reaches the builder, and the step passes only on
`SORA_VFX_READY: <n> systems` with n the length of the builder's SYSTEMS list.
Every lane's source checks and editor steps must run in dependency order, and
neither a failed source check nor a failed editor validation may be ignored.
"""

import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import textwrap
import unittest

TOOLCHAIN = Path(__file__).resolve().parent
UNREAL = TOOLCHAIN.parent / "unreal"
SPEC = importlib.util.spec_from_file_location("sora_vfx_system_count", TOOLCHAIN / "vfx_system_count.py")
counter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(counter)

FAKE_EDITOR = """#!/bin/bash
script=""
rhi="missing"
for arg in "$@"; do
  case "$arg" in
    -ExecutePythonScript=*) script="${arg#*=}" ;;
    -nullrhi|-RenderOffscreen) rhi="$arg" ;;
  esac
done
name="$(basename "$script")"
printf 'editor:%s:%s\\n' "$name" "$rhi" >>"$FAKE_IMPORT_TRACE"
case "$name" in
  import_original_assets.py) marker="SORA_ASSET_IMPORT_COMPLETE: 1 assets" ;;
  import_environment_palette.py) marker="NYAAGYU_PBR_READY: 1 surfaces" ;;
  import_cc0_environment.py) marker="SORA_CC0_ENVIRONMENT_READY: 5 packages" ;;
  create_sora_vfx.py)
    printf 'ONLY=%s\\nREUSE=%s\\n' "${SORA_VFX_ONLY-<unset>}" "${SORA_VFX_REUSE_MATERIALS-<unset>}" >"$FAKE_VFX_ENV"
    marker="$FAKE_VFX_MARKER" ;;
  validate_imported_assets.py) marker="SORA_ASSET_VALIDATION_COMPLETE: 3 packages loaded with expected types" ;;
  validate_cc0_environment.py) marker="SORA_CC0_ENVIRONMENT_VALIDATED: 5 packages loaded with expected types (fixture)" ;;
  import_audio.py) marker="SORA_AUDIO_IMPORT_COMPLETE: 7 packages" ;;
  validate_audio_import.py) marker="SORA_AUDIO_VALIDATION_COMPLETE: 7 packages loaded with expected types and routing" ;;
  *) echo "unexpected script $script" >&2; exit 3 ;;
esac
if [[ "$name" == "${FAKE_EDITOR_MARKER_SCRIPT-}" ]]; then marker="$FAKE_EDITOR_MARKER"; fi
echo "LogPython: $marker"
if [[ "$name" == "${FAKE_PYTHON_ERROR_SCRIPT-}" ]]; then echo "LogPython: Error: fixture exception"; fi
if [[ "$name" == "${FAKE_EDITOR_EXIT_SCRIPT-}" ]]; then exit 4; fi
exit 0
"""

FAKE_DOCTOR = """
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
def inspect():
    return {"engine_root": os.environ["FAKE_ENGINE_ROOT"], "build_ready": True,
            "developer_dir": os.environ["FAKE_DEVELOPER_DIR"], "sdk_root": "/fake/MacOSX.sdk"}
"""

HOST_CHECKS = {
    "unreal/validate_imported_assets.py": "SORA_ASSET_SOURCE_CHECK_COMPLETE: 3 expected Unreal packages",
    "unreal/pack_cc0_environment.py": "SORA_CC0_PACK_COMPLETE: 1 ARM maps",
    "unreal/validate_cc0_environment.py": "SORA_CC0_SOURCE_CHECK_COMPLETE: 5 expected Unreal packages",
    "unreal/check_cc0_custom_hlsl.py": "SORA_CC0_HLSL_COMPILED: 1 Custom expressions",
    "audio/validate_audio_data.py": "SORA_AUDIO_DATA_COMPLETE",
    "unreal/validate_audio_import.py": "SORA_AUDIO_SOURCE_CHECK_COMPLETE: 7 expected Unreal packages (fixture)",
}
EDITOR_STEPS = (
    "import_original_assets.py", "import_environment_palette.py", "import_cc0_environment.py",
    "create_sora_vfx.py", "validate_imported_assets.py", "validate_cc0_environment.py",
    "import_audio.py", "validate_audio_import.py",
)
FAKE_HOST_CHECK = """
import os
from pathlib import Path
import sys
name = Path(__file__).name
with Path(os.environ["FAKE_IMPORT_TRACE"]).open("a") as trace:
    trace.write("host:" + name + "\\n")
if name == os.environ.get("FAKE_FAIL_HOST_SCRIPT"):
    sys.exit("fixture host failure: " + name)
if name in ("validate_imported_assets.py", "validate_cc0_environment.py", "validate_audio_import.py"):
    assert sys.argv[1:] == ["--source-only"], sys.argv
if name == os.environ.get("FAKE_HOST_MARKER_SCRIPT"):
    print("fixture missing source count")
else:
    print(MARKER)
"""


class SystemCount(unittest.TestCase):
    def test_counts_the_builders_systems(self):
        self.assertEqual(counter.system_count((UNREAL / "create_sora_vfx.py").read_text(encoding="utf-8")), 27)

    def test_rejects_a_list_it_cannot_trust(self):
        for source in ("SYSTEMS = [rain]\n",                                  # not a function of the module
                       "def rain(mi): pass\nSYSTEMS = [rain, rain]\n",        # listed twice
                       "def rain(mi): pass\nSYSTEMS = []\n",                  # empty
                       "def rain(mi): pass\nSYSTEMS = list((rain,))\n",       # not a literal
                       "def rain(mi): pass\n"):                              # missing
            with self.subTest(source=source), self.assertRaises(ValueError):
                counter.system_count(source)


class ImportGate(unittest.TestCase):
    """import-mac.sh in a scratch project whose editor, doctor and build are fakes."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="sora-import-vfx-gate-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "project"
        toolchain, unreal = self.root / "scripts/toolchain", self.root / "scripts/unreal"
        toolchain.mkdir(parents=True)
        unreal.mkdir(parents=True)
        for name in ("import-mac.sh", "editor-config-guard.sh", "vfx_system_count.py"):
            shutil.copy2(TOOLCHAIN / name, toolchain / name)
        shutil.copy2(UNREAL / "create_sora_vfx.py", unreal / "create_sora_vfx.py")   # only counted, never run
        (toolchain / "doctor.py").write_text(textwrap.dedent(FAKE_DOCTOR))
        (toolchain / "build-mac.sh").write_text(
            '#!/bin/sh\nprintf "build:%s %s\\n" "$1" "$2" >>"$FAKE_IMPORT_TRACE"\nexit 0\n')
        (toolchain / "build-mac.sh").chmod(0o755)
        for relative, marker in HOST_CHECKS.items():
            source = self.root / "scripts" / relative
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text("MARKER = " + repr(marker) + "\n" + textwrap.dedent(FAKE_HOST_CHECK))
        (self.root / "Config").mkdir()
        (self.root / "Config/DefaultEngine.ini").write_text("[Fake]\n")
        (self.root / "Fake.uproject").write_text("{}\n")
        self.engine = Path(temporary.name) / "engine"
        editor = self.engine / "Engine/Binaries/Mac/UnrealEditor-Cmd"
        editor.parent.mkdir(parents=True)
        editor.write_text(FAKE_EDITOR)
        editor.chmod(0o755)
        self.seen = Path(temporary.name) / "vfx-env.txt"
        self.trace = Path(temporary.name) / "import-trace.txt"

    def run_import(self, marker, **caller_environment):
        # The script exports the doctor's DEVELOPER_DIR, which the python3 shim then needs to be real.
        developer = subprocess.run(["xcode-select", "-p"], capture_output=True, text=True, check=True).stdout.strip()
        self.trace.write_text("")
        environment = dict(os.environ, SORA_MIN_FREE_GIB="0", FAKE_ENGINE_ROOT=str(self.engine), FAKE_DEVELOPER_DIR=developer,
                           FAKE_VFX_ENV=str(self.seen), FAKE_VFX_MARKER=marker,
                           FAKE_IMPORT_TRACE=str(self.trace), **caller_environment)
        return subprocess.run(["bash", str(self.root / "scripts/toolchain/import-mac.sh"), str(self.root / "logs")],
                              env=environment, capture_output=True, text=True, timeout=120)

    def test_a_complete_build_passes_and_never_sees_the_iteration_switches(self):
        result = self.run_import("SORA_VFX_READY: 27 systems", SORA_VFX_ONLY="rain", SORA_VFX_REUSE_MATERIALS="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS: imported and loaded 3 art, 5 CC0 environment and 7 audio packages plus 27 VFX systems",
                      result.stdout)
        self.assertEqual(self.seen.read_text(), "ONLY=<unset>\nREUSE=<unset>\n")
        expected = ["build:Development Editor"] + ["host:" + Path(name).name for name in HOST_CHECKS]
        expected += [f"editor:{name}:{'-RenderOffscreen' if name == 'create_sora_vfx.py' else '-nullrhi'}"
                     for name in EDITOR_STEPS]
        self.assertEqual(self.trace.read_text().splitlines(), expected)

    def test_every_host_failure_stops_before_any_editor_step(self):
        for relative in HOST_CHECKS:
            name = Path(relative).name
            with self.subTest(source=name):
                result = self.run_import("SORA_VFX_READY: 27 systems", FAKE_FAIL_HOST_SCRIPT=name)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("fixture host failure: " + name, result.stderr)
                self.assertNotIn("editor:", self.trace.read_text())
                self.assertNotIn("PASS:", result.stdout)

    def test_each_source_package_count_is_required(self):
        for name in ("validate_imported_assets.py", "validate_cc0_environment.py", "validate_audio_import.py"):
            with self.subTest(source=name):
                result = self.run_import("SORA_VFX_READY: 27 systems", FAKE_HOST_MARKER_SCRIPT=name)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("did not report an expected package count", result.stderr)
                self.assertNotIn("editor:", self.trace.read_text())

    def test_each_validator_requires_its_own_source_count(self):
        for name, marker in (
                ("validate_imported_assets.py", "SORA_ASSET_VALIDATION_COMPLETE: 2 packages loaded with expected types"),
                ("validate_cc0_environment.py", "SORA_CC0_ENVIRONMENT_VALIDATED: 4 packages loaded with expected types"),
                ("validate_audio_import.py", "SORA_AUDIO_VALIDATION_COMPLETE: 6 packages loaded with expected types and routing")):
            with self.subTest(validator=name):
                result = self.run_import("SORA_VFX_READY: 27 systems", FAKE_EDITOR_MARKER_SCRIPT=name,
                                         FAKE_EDITOR_MARKER=marker)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("no completion marker", result.stderr)
                self.assertNotIn("PASS:", result.stdout)
                self.assertTrue(self.trace.read_text().splitlines()[-1].startswith("editor:" + name + ":"))

    def test_a_completion_marker_cannot_hide_editor_errors(self):
        for variable, diagnostic in (("FAKE_PYTHON_ERROR_SCRIPT", "Python error lines"),
                                     ("FAKE_EDITOR_EXIT_SCRIPT", "editor exited 4")):
            with self.subTest(failure=variable):
                result = self.run_import("SORA_VFX_READY: 27 systems", **{variable: "import_audio.py"})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(diagnostic, result.stderr)
                self.assertNotIn("PASS:", result.stdout)
                self.assertTrue(self.trace.read_text().splitlines()[-1].startswith("editor:import_audio.py:"))

    def test_a_short_count_fails(self):
        for marker in ("SORA_VFX_READY: 1 systems", "SORA_VFX_READY: 0 systems", "SORA_VFX_READY: 2 systems"):
            with self.subTest(marker=marker):
                result = self.run_import(marker)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("no completion marker 'SORA_VFX_READY: 27 systems'", result.stderr)
                self.assertNotIn("PASS:", result.stdout)

    def test_an_iteration_run_fails(self):
        result = self.run_import("SORA_VFX_PARTIAL: 1 of 27 systems rebuilt; not a complete build")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FAIL import-vfx.log", result.stderr)


if __name__ == "__main__":
    unittest.main()
