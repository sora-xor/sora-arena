"""Exercise rejection paths without editing checked-in parity expectations."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import kernel_abi

DIRECTORY=Path(__file__).resolve().parent
FIXTURE=DIRECTORY/'fixtures/practice-abi3'

class ParityRejectionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='sora-parity-negative-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.fixture=self.root/'fixture'
        shutil.copytree(FIXTURE,self.fixture)
        self.path=self.fixture/'manifest.json'
        self.manifest=json.loads(self.path.read_text())
        self.report=self.root/'rejection-report.json'

    def rejected(self,message):
        self.path.write_text(json.dumps(self.manifest))
        result=subprocess.run([sys.executable,str(DIRECTORY/'verify_parity.py'),'--fixture-dir',str(self.fixture),'--report',str(self.report)],text=True,capture_output=True)
        self.assertNotEqual(result.returncode,0,result.stdout)
        self.assertIn(message,result.stderr)
        if self.report.exists():self.assertEqual(json.loads(self.report.read_text())['status'],'fail','Failure must not leave a pass report')

    def test_control_identity(self):
        path=self.fixture/'exercise.controls';data=bytearray(path.read_bytes());data[2]^=1;path.write_bytes(data)
        self.rejected('canonical control identity mismatch')

    def test_noncanonical_wire_input(self):
        path=self.fixture/'exercise.controls';data=bytearray(path.read_bytes());data[2]=128;path.write_bytes(data)
        self.manifest['controls'][0]['sha256']=hashlib.sha256(data).hexdigest()
        self.rejected('non-canonical controls')

    def test_abi_layout(self):
        self.manifest['abi_layout']['Input']['fields'][0]['offset']=4
        self.rejected('C ABI layout diverges')

    def test_source_identity(self):
        self.manifest['source_identity']['files_sha256']['crates/arena-core/src/simulation.rs']='0'*64
        self.rejected('source identity changed')

    def test_runner_identity(self):
        self.manifest['runner_files_sha256']['scripts/unreal/verify_parity.py']='0'*64
        self.rejected('runner identity changed')

    def test_expected_state_digest(self):
        self.manifest['cases'][0]['expected']['checkpoints'][0]['state_hash']='0'*64
        self.rejected('checkpoint mismatch at tick 60')

    def test_expected_event_digest(self):
        self.manifest['cases'][0]['expected']['checkpoints'][0]['event_stream_sha256']='0'*64
        self.rejected('checkpoint mismatch at tick 60')

    def test_old_success_report_is_invalidated(self):
        self.report.write_text(json.dumps({'status':'pass','scope':'obsolete result'}))
        self.manifest['cases'][0]['expected']['checkpoints'][0]['state_hash']='0'*64
        self.rejected('checkpoint mismatch at tick 60')

    def test_stale_library_is_rejected_before_layout_queries(self):
        old_library=Mock()
        old_library.arena_abi_version.return_value=2
        with patch.object(kernel_abi.ctypes,'CDLL',return_value=old_library):
            with self.assertRaisesRegex(RuntimeError,'exactly ABI 3'):
                kernel_abi.load_kernel('unused-fake-library')
        old_library.arena_create.assert_not_called()
        old_library.arena_player_presentation.assert_not_called()

    def test_optimized_parity_invalidates_old_success_report(self):
        for flag in ['-O','-OO']:
            with self.subTest(flag=flag):
                self.report.write_text(json.dumps({'status':'pass','scope':'obsolete'}))
                result=subprocess.run([sys.executable,flag,str(DIRECTORY/'verify_parity.py'),'--fixture-dir',str(self.fixture),'--report',str(self.report)],text=True,capture_output=True)
                self.assertNotEqual(result.returncode,0)
                self.assertIn('Python optimization is unsupported',result.stderr)
                self.assertEqual(json.loads(self.report.read_text())['status'],'fail')

    def test_optimized_staging_cannot_replace_verified_library(self):
        root=DIRECTORY.parents[1]
        outputs=list((root/'Binaries').glob('*/libarena_ffi.dylib'))+list((root/'Binaries').glob('*/arena_ffi.dll'))
        before={path:hashlib.sha256(path.read_bytes()).hexdigest() for path in outputs}
        result=subprocess.run([sys.executable,'-O',str(DIRECTORY/'stage_kernel.py')],text=True,capture_output=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Python optimization is unsupported',result.stderr)
        self.assertEqual(before,{path:hashlib.sha256(path.read_bytes()).hexdigest() for path in outputs})

class SourceIdentityCoverageTests(unittest.TestCase):
    def test_every_hashed_simulation_source_is_in_the_practice_identity(self):
        # arena_kill_history_v2_parity.rs classifies every arena-core source and
        # hashes the kernel's in KERNEL_SOURCES. Each of those, except the
        # evidence protocol that the practice ABI never calls, must also be in
        # this fixture's source identity, so that a new simulation module cannot
        # change practice behaviour without a reviewed re-record.
        import verify_parity
        rust=(DIRECTORY.parents[1]/'crates/arena-core/tests/arena_kill_history_v2_parity.rs').read_text()
        block=rust.split('kernel_sources![',1)[1].split('];',1)[0]
        names=re.findall(r'"([^"]+)"',block)
        self.assertIn('simulation/respawn.rs',names)
        hashed={f'crates/arena-core/src/{name}' for name in names if name!='protocol.rs'}
        self.assertEqual(hashed-set(verify_parity.SOURCE_FILES),set())

if __name__=='__main__':unittest.main()
