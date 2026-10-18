"""Evidence gate regressions for isolated rendered startup; no Unreal launch."""
from copy import deepcopy
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from verify_fresh_startup import MARKER, TEST, problems

ROOT = Path(__file__).resolve().parents[2]


def png(width=2, height=2, pixels=None):
    def chunk(kind, payload):
        return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload))
    scanlines = pixels if pixels is not None else (b'\0' + b'\xff\xff\xff\xff' * width) * height
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(scanlines)) + chunk(b'IEND', b''))


class FreshStartupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.frame = self.root / '01_Title.png'
        self.frame.write_bytes(png())
        self.log = f"Found 1 automation tests based on '{TEST}'"
        self.report = {'failed': 0, 'notRun': 0, 'inProcess': 0, 'tests': [{
            'fullTestPath': TEST, 'state': 'Success', 'errors': 0, 'warnings': 0,
            'entries': [{'event': {'type': 'Info', 'message': f'{MARKER} width=2 height=2'}}]}]}

    def check(self, **changes):
        args = dict(report=self.report, log=self.log, status=0, frame=self.frame, width=2, height=2)
        args.update(changes)
        return problems(**args)

    def test_complete_isolated_evidence_passes(self):
        self.assertEqual(self.check(), [])

    def test_missing_wrong_duplicate_or_unfinished_test_fails(self):
        for tests in ([], [dict(self.report['tests'][0], fullTestPath='SoraArena.UIRendered.FrontEndScreens')],
                      self.report['tests'] * 2, [dict(self.report['tests'][0], state='NotRun')]):
            with self.subTest(tests=tests):
                self.assertTrue(self.check(report=dict(self.report, tests=tests)))
        for field in ('failed', 'notRun', 'inProcess'):
            self.assertTrue(self.check(report=dict(self.report, **{field: 1})))

    def test_missing_or_falsified_startup_state_fails(self):
        for message in ('', f'{MARKER} width=1280 height=720',
                        f'{MARKER} width=2 height=2'.replace('title=1', 'title=0'),
                        f'{MARKER} width=2 height=2'.replace('focus=SSoraFrontEnd', 'focus=SViewport')):
            report = deepcopy(self.report)
            report['tests'][0]['entries'][0]['event']['message'] = message
            with self.subTest(message=message):
                self.assertTrue(self.check(report=report))

    def test_errors_warnings_and_exit_fail_even_if_state_says_success(self):
        for field in ('errors', 'warnings'):
            report = deepcopy(self.report); report['tests'][0][field] = 1
            self.assertTrue(self.check(report=report))
        for kind in ('Error', 'Warning'):
            report = deepcopy(self.report)
            report['tests'][0]['entries'].append({'event': {'type': kind, 'message': 'failure'}})
            self.assertTrue(self.check(report=report))
        for status in (1, 137, 142):
            self.assertTrue(self.check(status=status))
        self.assertTrue(self.check(log=self.log + '\nLogOutputDevice: Error: failure'))

    def test_broad_discovery_or_a_second_selection_fails(self):
        for log in ('', self.log.replace(TEST, 'SoraStartup'), self.log * 2,
                    self.log.replace('Found 1', 'Found 2')):
            self.assertTrue(self.check(log=log))

    def test_missing_corrupt_or_incomplete_frame_fails(self):
        self.assertTrue(self.check(frame=self.root / 'missing.png'))
        for data in (b'', png()[:-8], png()[:40] + b'x' + png()[41:], png(pixels=b'\0'), png(3, 2)):
            self.frame.write_bytes(data)
            with self.subTest(length=len(data)):
                self.assertTrue(self.check())

    def test_cli_fails_closed_before_a_runner_can_continue(self):
        report = self.root / 'index.json'; report.write_text(json.dumps(self.report))
        log = self.root / 'startup.log'; log.write_text(self.log)
        command = [sys.executable, str(ROOT / 'scripts/toolchain/verify_fresh_startup.py'),
                   str(report), str(log), '0', str(self.frame), '2', '2']
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
        report.unlink()
        self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)

    def test_both_runners_gate_navigation_in_a_separate_launch(self):
        for filename, navigation in (('test-packaged-mac.sh', 'launch automation '),
                                     ('capture-packaged-mac.sh', 'launch frontend ')):
            source = (ROOT / 'scripts/toolchain' / filename).read_text()
            with self.subTest(runner=filename):
                start = source.index('launch fresh-startup ')
                verify = source.index('verify_fresh_startup.py', start)
                self.assertLess(start, verify)
                self.assertLess(verify, source.index(navigation))
                self.assertIn(TEST, source[start:verify])
                self.assertIn('-UserDir=$APP_DATA/$name-userdir', source)
        # This observational test must not gain the tour's reset/input calls.
        source = (ROOT / 'Source/SoraArena/Private/SoraFreshStartupAutomation.cpp').read_text()
        for mutation in ('ShowTitle(', 'SetMenuOpen(', 'NoteDevice(', 'ProcessKey', 'FocusFrontEnd('):
            self.assertNotIn(mutation, source)


if __name__ == '__main__':
    unittest.main()
