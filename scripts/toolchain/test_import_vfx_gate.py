"""Host-only tests of import-mac.sh's VFX gate; a fake editor and fake doctor, never run Unreal.

The import must build every Niagara system: a developer's SORA_VFX_ONLY or
SORA_VFX_REUSE_MATERIALS never reaches the builder, and the step passes only on
`SORA_VFX_READY: <n> systems` with n the length of the builder's SYSTEMS list.
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
for arg in "$@"; do
  case "$arg" in -ExecutePythonScript=*) script="${arg#*=}" ;; esac
done
case "$(basename "$script")" in
  import_original_assets.py) echo "LogPython: SORA_ASSET_IMPORT_COMPLETE: 1 assets" ;;
  import_environment_palette.py) echo "LogPython: NYAAGYU_PBR_READY: 1 surfaces" ;;
  create_sora_vfx.py)
    printf 'ONLY=%s\\nREUSE=%s\\n' "${SORA_VFX_ONLY-<unset>}" "${SORA_VFX_REUSE_MATERIALS-<unset>}" >"$FAKE_VFX_ENV"
    echo "LogPython: $FAKE_VFX_MARKER" ;;
  validate_imported_assets.py) echo "LogPython: SORA_ASSET_VALIDATION_COMPLETE: 3 packages loaded with expected types" ;;
  *) echo "unexpected script $script" >&2; exit 3 ;;
esac
"""

FAKE_DOCTOR = """
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
def inspect():
    return {"engine_root": os.environ["FAKE_ENGINE_ROOT"], "build_ready": True,
            "developer_dir": os.environ["FAKE_DEVELOPER_DIR"], "sdk_root": "/fake/MacOSX.sdk"}
"""

FAKE_SOURCE_CHECK = 'print("SORA_ASSET_SOURCE_CHECK_COMPLETE: 3 expected Unreal packages")\n'


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
        (toolchain / "build-mac.sh").write_text("#!/bin/sh\nexit 0\n")
        (toolchain / "build-mac.sh").chmod(0o755)
        (unreal / "validate_imported_assets.py").write_text(FAKE_SOURCE_CHECK)
        (self.root / "Config").mkdir()
        (self.root / "Config/DefaultEngine.ini").write_text("[Fake]\n")
        (self.root / "Fake.uproject").write_text("{}\n")
        self.engine = Path(temporary.name) / "engine"
        editor = self.engine / "Engine/Binaries/Mac/UnrealEditor-Cmd"
        editor.parent.mkdir(parents=True)
        editor.write_text(FAKE_EDITOR)
        editor.chmod(0o755)
        self.seen = Path(temporary.name) / "vfx-env.txt"

    def run_import(self, marker, **caller_environment):
        # The script exports the doctor's DEVELOPER_DIR, which the python3 shim then needs to be real.
        developer = subprocess.run(["xcode-select", "-p"], capture_output=True, text=True, check=True).stdout.strip()
        environment = dict(os.environ, SORA_MIN_FREE_GIB="0", FAKE_ENGINE_ROOT=str(self.engine), FAKE_DEVELOPER_DIR=developer,
                           FAKE_VFX_ENV=str(self.seen), FAKE_VFX_MARKER=marker, **caller_environment)
        return subprocess.run(["bash", str(self.root / "scripts/toolchain/import-mac.sh"), str(self.root / "logs")],
                              env=environment, capture_output=True, text=True, timeout=120)

    def test_a_complete_build_passes_and_never_sees_the_iteration_switches(self):
        result = self.run_import("SORA_VFX_READY: 27 systems", SORA_VFX_ONLY="rain", SORA_VFX_REUSE_MATERIALS="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS: imported and loaded 3 expected packages", result.stdout)
        self.assertEqual(self.seen.read_text(), "ONLY=<unset>\nREUSE=<unset>\n")

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
