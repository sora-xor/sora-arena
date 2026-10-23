"""macOS-only real signing normalization; no test executable is launched."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import mac_candidate as candidate

@unittest.skipUnless(sys.platform == 'darwin', 'Apple CodeSign comparison requires macOS')
class SignatureIdentityTests(unittest.TestCase):
    def test_resource_signature_changes_preserve_exact_executable_code(self):
        with tempfile.TemporaryDirectory() as temp:
            paths = [Path(temp) / name for name in ('first', 'second')]
            for path in paths:
                shutil.copyfile('/usr/bin/true', path)
                subprocess.run(['/usr/bin/codesign', '--force', '--sign', '-', '--identifier', path.name, str(path)],
                               check=True, capture_output=True)
            self.assertNotEqual(candidate.digest(paths[0]), candidate.digest(paths[1]))
            self.assertEqual(candidate.executable_code(paths[0]), candidate.executable_code(paths[1]))


if __name__ == '__main__': unittest.main()
