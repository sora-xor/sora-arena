"""Reject stale source/output/native evidence without invoking Unreal or Rust."""
from copy import deepcopy
import contextlib
import io
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import mac_candidate as candidate


class MacCandidateTests(unittest.TestCase):
    def setUp(self):
        quiet = contextlib.redirect_stdout(io.StringIO())
        quiet.__enter__(); self.addCleanup(quiet.__exit__, None, None, None)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'project'
        self.root.mkdir()
        self.put('.gitignore', 'Binaries/\nSaved/\nContent/Generated/\n')
        self.put('Config/DefaultGame.ini', 'culture=ja')
        for name in candidate.CONSUMERS:
            self.put(name, name)
        for name in candidate.NON_UFS:
            self.put(name + '/fixture.json' if name in ('Content/Data', 'ThirdPartyNotices') else name, name)
        self.git('init', '-q'); self.git('config', 'user.name', 'Fixture'); self.git('config', 'user.email', 'fixture@example.invalid')
        self.commit()
        self.put(str(candidate.BRIDGE), 'local fake bridge bytes; never loaded')
        self.put(str(candidate.KERNEL), 'local fake kernel bytes; never loaded')
        self.native = '1' * 40
        sha = candidate.digest(self.root / candidate.BRIDGE)
        self.manifest = {'schema': 'sora.connect.bridge_build.v2', 'platform': 'Mac', 'source_status': 'clean',
                         'source_revision': self.native, 'source_tree': '2' * 40, 'library_sha256': sha,
                         'abi_check': 'Checked 26 dynamic function-pointer types successfully',
                         'native_smoke': {'sha256': sha, 'abi': 30, 'required_symbols': 26,
                                          'native_game_builder': {'canonical_cases': 8, 'canonical_actions': list(range(7))},
                                          'arena_join_terms_inspector': {'fixtures': 1}},
                         'consumer_checks_sha256': {name: candidate.digest(self.root / name) for name in candidate.CONSUMERS}}
        candidate.write(self.root / candidate.SIDECAR, self.manifest)
        # The provenance tests use text fixtures. A separate macOS test below
        # exercises actual signature normalization on copies of a Mach-O.
        self.code = patch.object(candidate, 'executable_code', candidate.digest)
        self.code.start(); self.addCleanup(self.code.stop)

    def put(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], text=True).strip()

    def commit(self):
        self.git('add', '.'); self.git('commit', '-qm', 'fixture')

    def build(self, phase):
        start = self.root / candidate.RECEIPTS / f'{phase}-start.json'
        candidate.begin(self.root, phase, start)
        for name in candidate.artifact_paths(phase):
            if name.endswith('.app'):
                name += '/Contents/MacOS/SoraArena'
            elif name == 'Saved/Cooked/Mac':
                name += '/ue.projectstore'
            self.put(name, 'output at ' + self.git('rev-parse', 'HEAD'))
        candidate.finish(self.root, start)

    def stage(self):
        self.build('editor'); self.build('game'); self.build('cook')
        start = self.root / candidate.RECEIPTS / 'stage-start.json'
        source = self.git('rev-parse', 'HEAD')
        candidate.stage_begin(self.root, start, source, self.native)
        app = Path(self.temp.name) / 'archive/SoraArena.app'
        shutil.copytree(self.root / 'Binaries/Mac/SoraArena.app', app)
        staged = app / 'Contents/UE/SoraArena'
        for name in candidate.NON_UFS + [str(candidate.BRIDGE), str(candidate.KERNEL), str(candidate.SIDECAR)]:
            target = staged / name
            target.parent.mkdir(parents=True, exist_ok=True)
            original = self.root / name
            if original.is_dir(): shutil.copytree(original, target)
            else: shutil.copy2(original, target)
        record = app.parent / 'package-candidate.json'
        candidate.stage_finish(self.root, start, app, record)
        return app, record, source

    def test_end_to_end_preserves_original_sidecar_and_rejects_changed_package(self):
        before = (self.root / candidate.SIDECAR).read_bytes()
        app, record, source = self.stage()
        candidate.verify(app, record, app.parent / 'verified.json', source, self.native)
        self.assertEqual(before, (app / 'Contents/UE/SoraArena' / candidate.SIDECAR).read_bytes())
        (app / 'Contents/MacOS/SoraArena').write_text('replaced after staging')
        with self.assertRaisesRegex(ValueError, 'artifact bytes differ'):
            candidate.verify(app, record, app.parent / 'bad.json', source, self.native)

    def test_stage_rejects_a_different_executable_despite_matching_checkout(self):
        app, record, source = self.stage()
        (app / 'Contents/MacOS/SoraArena').write_text('old cached game executable')
        with self.assertRaisesRegex(ValueError, 'executable code differs'):
            candidate.stage_finish(self.root, self.root / candidate.RECEIPTS / 'stage-start.json', app, record)

    def test_stage_rejects_substituted_native_sidecar(self):
        app, record, source = self.stage()
        staged_manifest = app / 'Contents/UE/SoraArena' / candidate.SIDECAR
        wrong = deepcopy(self.manifest); wrong['source_revision'] = '9' * 40
        candidate.write(staged_manifest, wrong)
        with self.assertRaisesRegex(ValueError, 'Staged bridge/sidecar differs'):
            candidate.stage_finish(self.root, self.root / candidate.RECEIPTS / 'stage-start.json', app, record)

    def test_stage_rejects_changed_or_missing_credit_face_and_text(self):
        self.put('ThirdPartyNotices/CREDITS.md', 'Original source acknowledgements')
        self.commit()
        app, record, source = self.stage()
        start = self.root / candidate.RECEIPTS / 'stage-start.json'
        for name in ('Content/SourceArt/Fonts/NotoNaskhArabicUI-Regular.ttf', 'ThirdPartyNotices/CREDITS.md'):
            with self.subTest(path=name):
                staged = app / 'Contents/UE/SoraArena' / name
                original = staged.read_bytes()
                staged.write_text('Substituted staged credit content')
                with self.assertRaisesRegex(ValueError, 'Staged non-UFS content differs'):
                    candidate.stage_finish(self.root, start, app, record)
                staged.unlink()
                with self.assertRaisesRegex(ValueError, 'Missing artifact|Staged non-UFS content differs'):
                    candidate.stage_finish(self.root, start, app, record)
                staged.write_bytes(original)
        candidate.stage_finish(self.root, start, app, record)
        candidate.verify(app, record, app.parent / 'verified-credits.json', source, self.native)

    def test_stage_records_added_crypto_cache_without_rewriting_cook(self):
        app, record, source = self.stage()
        cook = self.root / candidate.RECEIPTS / 'cook.json'
        before = cook.read_bytes()
        cache = self.put(candidate.STAGE_CRYPTO, '{"bEnablePakSigning":false}')
        # The exception belongs only to the controlled staging comparison.
        with self.assertRaisesRegex(ValueError, 'artifact bytes changed'):
            candidate.receipt(self.root, 'cook')
        candidate.stage_finish(self.root, self.root / candidate.RECEIPTS / 'stage-start.json', app, record)
        self.assertEqual(before, cook.read_bytes())
        evidence = candidate.read(record)
        self.assertEqual(evidence['staging_metadata'][candidate.STAGE_CRYPTO]['sha256'], candidate.digest(cache))

    def test_crypto_addition_does_not_hide_other_cook_changes(self):
        app, record, source = self.stage()
        self.put(candidate.STAGE_CRYPTO, '{}')
        extra = self.put('Saved/Cooked/Mac/SoraArena/Metadata/Other.json', '{}')
        with self.assertRaisesRegex(ValueError, 'artifact bytes changed'):
            candidate.stage_finish(self.root, self.root / candidate.RECEIPTS / 'stage-start.json', app, record)
        extra.unlink()
        store = self.root / 'Saved/Cooked/Mac/ue.projectstore'
        store.write_text('replaced cooked content')
        with self.assertRaisesRegex(ValueError, 'artifact bytes changed'):
            candidate.stage_finish(self.root, self.root / candidate.RECEIPTS / 'stage-start.json', app, record)
        store.unlink()
        with self.assertRaisesRegex(ValueError, 'artifact bytes changed'):
            candidate.stage_finish(self.root, self.root / candidate.RECEIPTS / 'stage-start.json', app, record)

    def test_preexisting_crypto_cache_cannot_be_changed_during_stage(self):
        self.put(candidate.STAGE_CRYPTO, '{"before":true}')
        app, record, source = self.stage()
        self.put(candidate.STAGE_CRYPTO, '{"after":true}')
        with self.assertRaisesRegex(ValueError, 'artifact bytes changed'):
            candidate.stage_finish(self.root, self.root / candidate.RECEIPTS / 'stage-start.json', app, record)

    def test_wrong_declared_source_or_native_rejects(self):
        app, record, source = self.stage()
        for expected_source, expected_native in [('3' * 40, self.native), (source, '4' * 40)]:
            with self.assertRaisesRegex(ValueError, 'differs from declared candidate'):
                candidate.verify(app, record, app.parent / 'bad.json', expected_source, expected_native)

    def test_build_receipt_cannot_be_relabelled_by_checkout_change(self):
        self.build('game')
        self.put('Config/DefaultGame.ini', 'culture=ja\nnew=1'); self.commit()
        with self.assertRaisesRegex(ValueError, 'belongs to another source'):
            candidate.receipt(self.root, 'game')

    def test_replaced_build_or_cooked_bytes_reject(self):
        self.build('editor'); self.build('game'); self.build('cook')
        self.put('Saved/Cooked/Mac/ue.projectstore', 'stale or replaced cook')
        with self.assertRaisesRegex(ValueError, 'artifact bytes changed'):
            candidate.receipt(self.root, 'cook')
        self.put('Binaries/Mac/SoraArena.app/Contents/MacOS/SoraArena', 'stale game')
        with self.assertRaisesRegex(ValueError, 'artifact bytes changed'):
            candidate.receipt(self.root, 'game')

    def test_new_cook_cannot_use_old_editor(self):
        self.build('editor')
        self.put('Config/DefaultGame.ini', 'culture=ja\nnew=1'); self.commit()
        with self.assertRaisesRegex(ValueError, 'belongs to another source'):
            candidate.begin(self.root, 'cook', self.root / candidate.RECEIPTS / 'bad.json')

    def test_mutation_during_build_rejects_and_invalidates_previous_receipt(self):
        self.build('game')
        start = self.root / candidate.RECEIPTS / 'retry.json'
        candidate.begin(self.root, 'game', start)
        self.assertFalse((self.root / candidate.RECEIPTS / 'game.json').exists())
        self.put('Config/DefaultGame.ini', 'changed mid-build')
        with self.assertRaisesRegex(ValueError, 'clean and committed'):
            candidate.finish(self.root, start)

    def test_missing_original_sidecar_and_wrong_library_reject(self):
        (self.root / candidate.SIDECAR).unlink()
        with self.assertRaises(FileNotFoundError): candidate.native(self.root)
        candidate.write(self.root / candidate.SIDECAR, self.manifest)
        self.put(str(candidate.BRIDGE), 'different library')
        with self.assertRaisesRegex(ValueError, 'bytes do not match'):
            candidate.native(self.root)

    def test_missing_required_consumer_or_unknown_path_rejects(self):
        for missing in candidate.CONSUMERS:
            value = deepcopy(self.manifest); value['consumer_checks_sha256'].pop(missing)
            candidate.write(self.root / candidate.SIDECAR, value)
            with self.assertRaisesRegex(ValueError, 'lacks required'):
                candidate.build_inputs(self.root)
        value = deepcopy(self.manifest); value['consumer_checks_sha256']['../outside'] = '0' * 64
        candidate.write(self.root / candidate.SIDECAR, value)
        with self.assertRaisesRegex(ValueError, 'unsupported consumer'):
            candidate.build_inputs(self.root)

    def test_optional_producer_check_is_also_verified(self):
        name = 'scripts/connect/build-bridge.sh'
        self.put(name, 'producer'); self.commit()
        value = deepcopy(self.manifest); value['consumer_checks_sha256'][name] = candidate.digest(self.root / name)
        candidate.write(self.root / candidate.SIDECAR, value)
        candidate.build_inputs(self.root)
        self.put(name, 'changed producer'); self.commit()
        with self.assertRaisesRegex(ValueError, 'consumer files differ'):
            candidate.build_inputs(self.root)

    def test_old_consumer_evidence_is_not_silently_rewritten(self):
        self.put(candidate.CONSUMERS[0], 'changed consumer'); self.commit()
        with self.assertRaisesRegex(ValueError, 'consumer files differ'):
            candidate.build_inputs(self.root)
        self.assertEqual(candidate.read(self.root / candidate.SIDECAR), self.manifest)

    def test_generated_content_change_invalidates_cook(self):
        self.build('editor'); self.build('cook')
        self.put('Content/Generated/changed.uasset', 'changed ignored generated asset')
        with self.assertRaises(ValueError): candidate.receipt(self.root, 'cook')

    def test_external_symlink_is_not_an_unhashed_input(self):
        outside = Path(self.temp.name) / 'external'; outside.mkdir()
        (self.root / 'Content/External').symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'External artifact symlink'):
            candidate.files(self.root, ['Content'])


if __name__ == '__main__': unittest.main()
