"""Reject incomplete, failed or wrong-renderer capture runs even after exit zero."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

SPEC = importlib.util.spec_from_file_location(
    "capture_report", Path(__file__).with_name("verify-capture-report.py"))
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class CaptureReportTests(unittest.TestCase):
    def setUp(self):
        self.report = {
            "devices": [{"rHI": "Metal", "renderMode": "SM6"}],
            "tests": [{"fullTestPath": "SoraCapture.ArtReview.Dojo", "state": "Success",
                       "errors": 0, "entries": []}],
            "failed": 0, "notRun": 0, "inProcess": 0,
        }
        self.log = "Found 1 automation tests based on 'SoraCapture.ArtReview.Dojo'"

    def check(self, report=None, log=None, status=0, shader="sm6"):
        return VERIFY.problems(self.report if report is None else report,
                               self.log if log is None else log, status, shader)

    def test_finished_run_matches_explicit_shader_model(self):
        self.assertEqual(self.check(), [])
        self.assertTrue(self.check(shader="sm5"))

    def test_exit_zero_with_no_tests_is_not_success(self):
        self.report["tests"] = []
        self.assertTrue(self.check())

    def test_partial_report_and_missing_discovery_are_rejected(self):
        self.assertTrue(self.check(log=self.log.replace("Found 1", "Found 2")))
        self.assertTrue(self.check(log=""))
        self.report["inProcess"] = 1
        self.assertTrue(self.check())

    def test_errors_cannot_hide_behind_success_state(self):
        self.report["tests"][0]["entries"] = [{"event": {"type": "Error", "message": "Screenshot missing"}}]
        self.assertTrue(self.check())
        self.report["tests"][0]["entries"] = []
        self.report["tests"][0]["errors"] = 1
        self.assertTrue(self.check())

    def test_failed_test_and_crash_after_tests_are_rejected(self):
        self.assertTrue(self.check(status=1))
        self.report["tests"][0]["state"] = "Fail"
        self.assertTrue(self.check())

    def test_null_renderer_or_missing_device_cannot_qualify_capture(self):
        for rhi in ("", "Null", "N/A"):
            with self.subTest(rhi=rhi):
                report = copy.deepcopy(self.report)
                report["devices"][0]["rHI"] = rhi
                self.assertTrue(self.check(report=report))
        self.report["devices"] = []
        self.assertTrue(self.check(shader="auto"))


class LogCompletionTests(unittest.TestCase):
    def setUp(self):
        self.data = b"editor\nchild\xff\n"
        self.receipt = {"process_returncode": 0, "runner_status": 0, "stream_eof": True,
                        "failure": None, "log_bytes": len(self.data),
                        "log_sha256": hashlib.sha256(self.data).hexdigest()}

    def check(self, **changes):
        return VERIFY.log_completion_problems(dict(self.receipt, **changes), self.data,
                                               changes.get("runner_status", 0))

    def test_complete_stream_binds_raw_bytes(self):
        self.assertEqual(self.check(), [])
        self.assertTrue(VERIFY.log_completion_problems(self.receipt, self.data + b"late", 0))

    def test_missing_eof_and_collection_deadline_fail_despite_editor_exit_zero(self):
        self.assertTrue(self.check(stream_eof=False))
        failures = self.check(stream_eof=False, runner_status=125, failure="EOF deadline exceeded")
        self.assertIn("capture log collection: EOF deadline exceeded", failures)

    def test_missing_or_inconsistent_exit_status_cannot_pass(self):
        self.assertTrue(self.check(process_returncode=None))
        self.assertTrue(self.check(process_returncode=7))
        self.assertTrue(VERIFY.log_completion_problems(self.receipt, self.data, 7))

    def test_archive_requires_and_retains_completed_log_receipt(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            log = root / "editor.log"
            data = b"Found 1 automation tests based on 'SoraExample'\r\nchild\xff\r\n"
            log.write_bytes(data)
            report = root / "report.json"
            report.write_text(json.dumps({"devices": [{"rHI": "Metal", "renderMode": "SM6"}],
                                         "tests": [{"fullTestPath": "SoraExample", "state": "Success"}]}))
            (root / "source-commit.txt").write_text("test")
            (root / "source-status.txt").write_text("")
            command = [sys.executable, str(Path(VERIFY.__file__)), str(report), str(log), "0", "sm6",
                       "--archive", str(root), str(root), str(root), "0", "2", "1", "SoraExample"]
            missing = subprocess.run(command, capture_output=True)
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn(b"requires a log completion receipt", missing.stderr)
            receipt = root / "completion.json"
            receipt.write_text('["not a receipt"]')
            malformed = subprocess.run(command + ["--log-completion", str(receipt)], capture_output=True)
            self.assertNotEqual(malformed.returncode, 0)
            self.assertIn(b"receipt is not an object", malformed.stderr)
            self.assertNotIn(b"Traceback", malformed.stderr)
            receipt.write_text(json.dumps(dict(self.receipt, log_bytes=len(data),
                                              log_sha256=hashlib.sha256(data).hexdigest())))
            complete = subprocess.run(command + ["--log-completion", str(receipt)], capture_output=True)
            self.assertEqual(complete.returncode, 0, complete.stderr)
            manifest = json.loads((root / "capture.json").read_text())
            self.assertEqual(manifest["log_sha256"], hashlib.sha256(data).hexdigest())
            self.assertEqual(manifest["log_completion"], json.loads(receipt.read_text()))
            self.assertEqual(manifest["log_completion_sha256"], hashlib.sha256(receipt.read_bytes()).hexdigest())
            # Collection failure is distinct from the launched process's status.
            receipt.write_text(json.dumps(dict(self.receipt, stream_eof=False, runner_status=125,
                                              failure="EOF deadline exceeded", log_bytes=len(data),
                                              log_sha256=hashlib.sha256(data).hexdigest())))
            failed_command = command.copy()
            failed_command[4] = "125"
            failed = subprocess.run(failed_command + ["--log-completion", str(receipt)], capture_output=True)
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn(b"EOF deadline exceeded", failed.stderr)
            self.assertNotIn(b"editor exited", failed.stderr)
            # A later append is rejected even if the automation report passed.
            receipt.write_text(json.dumps(dict(self.receipt, log_bytes=len(data),
                                              log_sha256=hashlib.sha256(data).hexdigest())))
            log.write_bytes(data + b"late")
            appended = subprocess.run(command + ["--log-completion", str(receipt)], capture_output=True)
            self.assertNotEqual(appended.returncode, 0)
            self.assertIn(b"log differs from completed stream receipt", appended.stderr)


class CaptureArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.project = self.root / "project with spaces"
        self.engine_base = self.root / "Engine/Binaries/Mac"
        self.engine_base.mkdir(parents=True)
        self.source = self.project / "Saved/Screenshots/SoraArtReview/2x1/DojoEntry.png"
        self.source.parent.mkdir(parents=True)
        def chunk(kind, payload):
            return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))
        self.chunk = chunk
        self.png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 1, 8, 2, 0, 0, 0))
                    + chunk(b"IDAT", zlib.compress(b"\0\xff\0\0\0\xff\0")) + chunk(b"IEND", b""))
        self.source.write_bytes(self.png)
        self.started = self.source.stat().st_mtime_ns - 1
        self.log = "LogTemp: Display: SORA_ART_REVIEW_FRAME " + os.path.relpath(self.source, self.engine_base)
        self.report = {"tests": [{"fullTestPath": "SoraCapture.ArtReview.Dojo"}]}

    def archive(self, output="run-sm6", log=None):
        if hasattr(self,"campaign_commit"):
            folder=self.root/output; folder.mkdir(parents=True,exist_ok=True)
            (folder/'source-commit.txt').write_text(self.campaign_commit+'\n')
        return VERIFY.archive_frames(self.log if log is None else log, self.report, self.project,
                                     self.engine_base, self.root / output, self.started, 2, 1)

    def campaign(self):
        """A real tiny Git repo binds the archive inventory to a fixed commit."""
        source_name='Source/SoraArena/Private/SoraCaptureAutomation.cpp'
        catalog_name='Content/Data/campaign/chapter_04.json'
        repo=Path(__file__).resolve().parents[2]
        for name in (source_name,catalog_name):
            target=self.project/name; target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes((repo/name).read_bytes())
        def git(*args):
            return subprocess.check_output(['git','-C',str(self.project),*args],stderr=subprocess.DEVNULL,text=True).strip()
        git('init','--quiet'); git('add',source_name,catalog_name)
        git('-c','user.name=Archive Test','-c','user.email=archive@example.invalid','-c','commit.gpgsign=false',
            'commit','--quiet','-m','Frozen capture inventory')
        self.campaign_commit=git('rev-parse','HEAD')
        self.report={'tests':[{'fullTestPath':'SoraCapture.Campaign.Chapter4'}]}
        self.campaign_paths=[]; records=[]
        catalog=json.loads((self.project/catalog_name).read_text())
        for name,beat,subject in [('C4_02_BankRoadRide',1,'ride'),
                                  ('C4_11_Waterwheel',10,'task'),
                                  ('C4_16_AssessorTelegraph',15,'boss telegraph')]:
            path=self.project/'Saved/Screenshots/SoraCapture/2x1'/(name+'.png')
            path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(self.png); self.campaign_paths.append(path)
            records.append(f'LogTemp: Display: SORA_CAPTURE {name} chapter 4 {catalog["beats"][beat]["id"]} ({subject}): assisted camera; actual observed state')
        self.log='\n'.join(records)
        return source_name

    def frontend(self):
        source_name = 'Source/SoraArena/Private/SoraFrontEndAutomation.cpp'
        target = self.project / source_name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((Path(__file__).resolve().parents[2] / source_name).read_bytes())
        def git(*args):
            return subprocess.check_output(['git', '-C', str(self.project), *args], stderr=subprocess.DEVNULL, text=True).strip()
        self.frontend_git = git
        git('init', '--quiet'); git('add', source_name)
        git('-c', 'user.name=Archive Test', '-c', 'user.email=archive@example.invalid', '-c', 'commit.gpgsign=false',
            'commit', '--quiet', '-m', 'Frozen menu inventory')
        self.campaign_commit = git('rev-parse', 'HEAD')  # archive() writes this run's source-commit.txt.
        self.report = {'tests': [{'fullTestPath': 'SoraArena.UIRendered.FrontEndScreens'}]}
        names = ['01_Title', '02_MainKeyboard', '03_ChapterSelect', '04_PracticeLobby', '05_Wallet', '06_Settings',
                 '07_Credits', '08_CreditsScrolled', '09_QuitConfirm', '12_Graphics', '13_Audio', '14_Subtitles',
                 '15_Controls', '16_ControlsBindings', '17_Rebind', '18_Accessibility', '10_MainPad', '11_TitlePad', '19_Pause']
        self.frontend_paths = []
        for name in names:
            path = self.project / 'Saved/Screenshots/SoraFrontEnd/2x1' / (name + '.png')
            path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(self.png)
            self.frontend_paths.append(path)
        self.log = '\n'.join(f'[2026.10.27-05.34.17:856][880]LogCore: Display: Tracing Screenshot "{name}" taken with size: 2 x 1'
                             for name in names)
        return source_name

    def test_frontend_archives_all_originals_against_frozen_source(self):
        source_name = self.frontend()
        (self.project / source_name).write_text('Mutable checkout is not the run inventory')
        frames = self.archive()
        self.assertEqual(len(frames), 19)
        self.assertEqual(frames[6]['frontend']['screen'], '07_Credits')
        for frame in frames:
            self.assertEqual((self.root / 'run-sm6' / frame['path']).read_bytes(), self.png)
            self.assertEqual(frame['frontend']['source_commit'], self.campaign_commit)
            self.assertEqual(frame['sha256'], hashlib.sha256(self.png).hexdigest())
            self.assertIn('not visual approval', frame['capture_kind'])

    def test_frontend_rejects_incomplete_duplicate_replayed_and_reordered_acks(self):
        self.frontend(); lines = self.log.splitlines()
        cases = [(lines[:-1], 18), (lines + [lines[-1]], 18), (lines[::-1], 19),
                 (['LogAutomationController: ' + line + ' [log]' for line in lines], 0),
                 ([line + ' [log]' for line in lines], 0),
                 (lines[:-1] + [lines[-1].replace('19_Pause', '20_Unknown')], 18),
                 (lines[:-1] + [lines[-1].replace('2 x 1', '3 x 1')], 18)]
        for index, (records, count) in enumerate(cases):
            with self.subTest(index=index), self.assertRaises(VERIFY.FrontEndCaptureEvidenceError) as failure:
                self.archive(f'bad-menu-acks-{index}', log='\n'.join(records))
            self.assertEqual(len(failure.exception.frames), count)

    def test_frontend_does_not_archive_unacknowledged_images(self):
        self.frontend()
        with self.assertRaises(VERIFY.FrontEndCaptureEvidenceError) as failure:
            self.archive(log='')
        self.assertEqual(failure.exception.frames, [])
        self.report = {'tests': [{'fullTestPath': 'SoraExample'}]}
        self.assertEqual(self.archive('unrelated-report'), [])

    def test_frontend_rejects_bad_originals_and_retains_the_rest(self):
        self.frontend()
        first = self.frontend_paths[0]
        for kind in ('stale', 'missing', 'corrupt', 'wrong-size', 'symlink'):
            with self.subTest(kind=kind):
                first.unlink(missing_ok=True); first.write_bytes(self.png)
                if kind == 'stale': os.utime(first, ns=(self.started - 1, self.started - 1))
                elif kind == 'missing': first.unlink()
                elif kind == 'corrupt': first.write_bytes(self.png[:-5])
                elif kind == 'wrong-size':
                    first.write_bytes(self.png[:8] + self.chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 2, 8, 2, 0, 0, 0))
                                      + self.chunk(b'IDAT', zlib.compress(b'\0\xff\0\0\0\0\xff\0')) + self.chunk(b'IEND', b''))
                else:
                    first.unlink(); first.symlink_to(self.frontend_paths[1])
                with self.assertRaises(VERIFY.FrontEndCaptureEvidenceError) as failure:
                    self.archive('bad-menu-' + kind)
                self.assertEqual(len(failure.exception.frames), 18)

    def test_frontend_requires_supported_report_and_committed_inventory(self):
        source_name = self.frontend()
        self.report['tests'] *= 2
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.archive('duplicate-tour')
        self.report['tests'] = self.report['tests'][:1]
        target = self.project / source_name
        target.write_text(target.read_text().replace('19_Pause', '20_Changed'))
        self.frontend_git('add', source_name)
        self.frontend_git('-c', 'user.name=Archive Test', '-c', 'user.email=archive@example.invalid',
                          '-c', 'commit.gpgsign=false', 'commit', '--quiet', '-m', 'Changed tour inventory')
        self.campaign_commit = self.frontend_git('rev-parse', 'HEAD')
        with self.assertRaisesRegex(ValueError, 'inventory'):
            self.archive('changed-inventory')

    def test_campaign_uses_committed_inventory_and_preserves_original_scope(self):
        source_name=self.campaign()
        # A later mutable source file cannot redefine the frozen run's shots.
        (self.project/source_name).write_text('not the committed inventory')
        frames=self.archive()
        self.assertEqual(len(frames),3)
        for frame in frames:
            self.assertEqual((self.root/'run-sm6'/frame['path']).read_bytes(),self.png)
            self.assertEqual(frame['campaign']['source_commit'],self.campaign_commit)
            self.assertIn('assisted camera',frame['campaign']['observed'])
            self.assertIn('not playthrough',frame['capture_kind'])
        self.assertEqual(frames[-1]['campaign']['subject'],'boss telegraph')

    def test_campaign_stale_or_missing_original_cannot_be_associated(self):
        self.campaign()
        os.utime(self.campaign_paths[0],ns=(self.started-1,self.started-1))
        with self.assertRaisesRegex(VERIFY.CampaignCaptureEvidenceError,'stale') as failure:
            self.archive('stale-campaign')
        self.assertEqual(len(failure.exception.frames),2)
        self.campaign_paths[0].unlink()
        with self.assertRaises(VERIFY.CampaignCaptureEvidenceError) as failure:
            self.archive('missing-campaign')
        self.assertEqual(len(failure.exception.frames),2)

    def test_campaign_requires_complete_inventory_and_rejects_replayed_records(self):
        self.campaign(); records=self.log.splitlines()
        invalid=[records[:2],records+[records[-1]],records[::-1],
                 ['LogAutomationController: '+record+' [log]' for record in records],
                 [record+' [log]' for record in records],
                 ['LogTemp: Display: SORA_CAPTURE_BOSS 5 s: actual state'],
                 records[:2]+['LogTemp: Display: SORA_CAPTURE_REJECTED C4_16_AssessorTelegraph: no accepted fresh original']]
        for index,lines in enumerate(invalid):
            with self.subTest(index=index),self.assertRaises(VERIFY.CampaignCaptureEvidenceError) as failure:
                self.archive(f'incomplete-{index}',log='\n'.join(lines))
            if index==0: self.assertEqual(len(failure.exception.frames),2)
        with self.assertRaises(VERIFY.CampaignCaptureEvidenceError):
            self.archive('wrong-subject',log=self.log.replace('(boss telegraph)','(objective)'))
        with self.assertRaises(VERIFY.CampaignCaptureEvidenceError):
            self.archive('wrong-chapter',log=self.log.replace('chapter 4','chapter 5'))
        with self.assertRaises(VERIFY.CampaignCaptureEvidenceError):
            self.archive('wrong-beat',log=self.log.replace('ch04.b16','ch04.b15'))
        with self.assertRaises(VERIFY.CampaignCaptureEvidenceError):
            self.archive('wrong-name',log=self.log.replace('C4_16_AssessorTelegraph','C4_16_OldImage'))

    def test_campaign_reused_filename_never_associates_final_bytes_with_first_observation(self):
        self.campaign(); first=self.log.splitlines()[-1]
        for index,second in enumerate((first.replace('actual observed state','a later different attack'),
                                      first.replace('chapter 4','chapter 5'))):
            with self.assertRaisesRegex(VERIFY.CampaignCaptureEvidenceError,'ambiguous') as failure:
                self.archive(f'reused-campaign-{index}',log=self.log+'\n'+second)
            self.assertEqual(len(failure.exception.frames),2)
            self.assertTrue(all('AssessorTelegraph' not in frame['source'] for frame in failure.exception.frames))
        # A symlink cannot substitute another basename's bytes either.
        self.campaign_paths[-1].unlink(); self.campaign_paths[-1].symlink_to(self.campaign_paths[0])
        with self.assertRaisesRegex(VERIFY.CampaignCaptureEvidenceError,'symlink') as failure:
            self.archive('aliased-original')
        self.assertEqual(len(failure.exception.frames),2)

    def test_campaign_requires_authentic_inventory_and_requested_chapter(self):
        source_name=self.campaign()
        self.report['tests']=[{'fullTestPath':'SoraCapture.Campaign.Chapter3'}]
        with self.assertRaisesRegex(ValueError,'authenticate'):
            self.archive('uncommitted-chapter')
        self.report['tests']=[{'fullTestPath':'SoraCapture.ArtReview.Dojo'}]
        with self.assertRaisesRegex(ValueError,'no screenshot'):
            self.archive('unrequested')
        self.report['tests']=[{'fullTestPath':'SoraCapture.Campaign.Chapter4'}]*2
        with self.assertRaisesRegex(ValueError,'duplicate'):
            self.archive('duplicate-report')
        self.report['tests']=[{'fullTestPath':'SoraCapture.Campaign.Chapter4'}]
        self.campaign_commit='0'*40
        with self.assertRaisesRegex(ValueError,'authenticate'):
            self.archive('bad-commit')

    def test_original_bytes_survive_later_shader_model_capture(self):
        first = self.archive()
        self.assertEqual(first[0]["sha256"], hashlib.sha256(self.png).hexdigest())
        self.archive("run-sm5")
        self.source.write_bytes(b"a later engine run overwrote this file")
        for run in ("run-sm6", "run-sm5"):
            self.assertEqual((self.root / run / first[0]["path"]).read_bytes(), self.png)

    def test_stale_missing_or_unacknowledged_frames_are_rejected(self):
        os.utime(self.source, ns=(self.started - 1, self.started - 1))
        with self.assertRaisesRegex(ValueError, "stale"):
            self.archive()
        self.source.unlink()
        with self.assertRaises(OSError):
            self.archive()
        with self.assertRaisesRegex(ValueError, "no screenshot"):
            self.archive(log="")

    def test_marker_cannot_archive_files_outside_project_screenshots(self):
        outside = self.root / "private.png"
        outside.write_bytes(self.png)
        with self.assertRaises(ValueError):
            self.archive(log="LogTemp: Display: SORA_ART_REVIEW_FRAME " + str(outside))

    def test_truncated_corrupt_or_wrong_size_png_is_rejected(self):
        missing_pixels = self.png[:33] + self.chunk(b"IDAT", zlib.compress(b"")) + self.chunk(b"IEND", b"")
        for data in (self.png[:-12], self.png[:-1] + b"x", b"not png", missing_pixels):
            with self.subTest(data=data[-12:]):
                self.source.write_bytes(data)
                with self.assertRaises(ValueError):
                    self.archive()
        self.source.write_bytes(self.png)
        with self.assertRaisesRegex(ValueError, "dimensions"):
            VERIFY.archive_frames(self.log, self.report, self.project, self.engine_base,
                                  self.root / "wrong-size", self.started, 1920, 1080)

    def test_duplicate_markers_and_overwriting_an_archive_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.archive(log=self.log + "\n" + self.log)
        with self.assertRaises(FileExistsError):
            self.archive()

    def test_non_capture_render_test_does_not_invent_frames(self):
        frames = VERIFY.archive_frames("", {"tests": [{"fullTestPath": "SoraArena.Rendering.EnvironmentCapability"}]},
                                       self.project, self.engine_base, self.root / "capability", self.started, 2, 1)
        self.assertEqual(frames, [])

    def test_registry_fixture_keeps_original_bytes_and_labels_its_scope(self):
        self.report = {"tests": [{"fullTestPath": "SoraCapture.RegistryFixture.Chapter5"}]}
        frames = self.archive(log="LogTemp: Display: SORA_REGISTRY_FIXTURE_FRAME " + str(self.source))
        self.assertEqual((self.root / "run-sm6" / frames[0]["path"]).read_bytes(), self.png)
        self.assertEqual(frames[0]["sha256"], hashlib.sha256(self.png).hexdigest())
        self.assertEqual(frames[0]["capture_kind"], "completed-save registry UI fixture; not playthrough evidence")

    def test_an_art_frame_cannot_stand_in_for_a_missing_registry_capture(self):
        self.report["tests"].append({"fullTestPath": "SoraCapture.RegistryFixture.Chapter4"})
        with self.assertRaisesRegex(ValueError, "RegistryFixture.*no screenshot"):
            self.archive()

    def test_different_capture_markers_cannot_hide_a_reused_path(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.archive(log=self.log + "\nLogTemp: Display: SORA_REGISTRY_FIXTURE_FRAME " + str(self.source))

    def test_weapon_fixture_keeps_original_bytes_and_labels_its_scope(self):
        self.report = {"tests": [{"fullTestPath": "SoraCapture.WeaponHUDFixture.BowDraw"}]}
        frames = self.archive(log="LogTemp: Display: SORA_WEAPON_HUD_FIXTURE_FRAME " + str(self.source))
        self.assertEqual((self.root / "run-sm6" / frames[0]["path"]).read_bytes(), self.png)
        self.assertEqual(frames[0]["sha256"], hashlib.sha256(self.png).hexdigest())
        self.assertEqual(frames[0]["capture_kind"], "prepared gameplay UI fixture; not playthrough evidence")

    def test_opening_hud_fixture_keeps_original_pixels_and_scope(self):
        self.report = {"tests": [{"fullTestPath": "SoraCapture.OpeningHUD.Live"}]}
        frames = self.archive(log="LogTemp: Display: SORA_OPENING_HUD_FRAME " + str(self.source))
        self.assertEqual((self.root / "run-sm6" / frames[0]["path"]).read_bytes(), self.png)
        self.assertEqual(frames[0]["sha256"], hashlib.sha256(self.png).hexdigest())
        self.assertEqual(frames[0]["capture_kind"], "prepared opening HUD fixture; not playthrough or art acceptance")

    def test_capture_families_require_their_own_markers(self):
        families = (("OpeningHUD.Live", "SORA_OPENING_HUD_FRAME"),
                    ("ArtReview.Dojo", "SORA_ART_REVIEW_FRAME"),
                    ("RegistryFixture.Chapter4", "SORA_REGISTRY_FIXTURE_FRAME"),
                    ("WeaponHUDFixture.Katana", "SORA_WEAPON_HUD_FIXTURE_FRAME"),
                    ("BowAim.Live", "SORA_BOW_AIM_FRAME"),
                    ("Codex.Live", "SORA_CODEX_FRAME"))
        for required, marker in families:
            for other, wrong_marker in families:
                if required == other:
                    continue
                with self.subTest(required=required, wrong_marker=wrong_marker):
                    self.report = {"tests": [{"fullTestPath": "SoraCapture." + required}]}
                    with self.assertRaisesRegex(ValueError, "no screenshot"):
                        self.archive(log="LogTemp: Display: " + wrong_marker + " " + str(self.source))

    def test_weapon_fixture_retains_png_and_duplicate_validation(self):
        self.report = {"tests": [{"fullTestPath": "SoraCapture.WeaponHUDFixture.Katana"}]}
        marker = "LogTemp: Display: SORA_WEAPON_HUD_FIXTURE_FRAME " + str(self.source)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.archive(output="duplicate", log=marker + "\n" + marker)
        self.source.write_bytes(self.png[:-12])
        with self.assertRaisesRegex(ValueError, "PNG"):
            self.archive(output="incomplete", log=marker)

    def test_failed_automation_replay_is_not_a_second_frame(self):
        timestamp = "[2026.10.18-10.33.12:978][704]"
        original = timestamp + self.log
        replay = ("[2026.10.18-10.33.15:062][816]LogAutomationController: LogTemp: "
                  "SORA_ART_REVIEW_FRAME " + str(self.source) + " [log] ")
        log = original + "\n" + replay
        frames = self.archive(log=log)
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0]["sha256"], hashlib.sha256(self.png).hexdigest())
        report = {"devices": [{"rHI": "Metal", "renderMode": "SM6"}],
                  "tests": [{"fullTestPath": "SoraCapture.ArtReview.Dojo", "state": "Fail", "errors": 1}],
                  "failed": 1, "notRun": 0, "inProcess": 0}
        self.assertTrue(VERIFY.problems(report, "Found 1 automation tests based on 'SoraCapture.ArtReview.Dojo'\n" + log, 0, "sm6"))
        with self.assertRaisesRegex(ValueError, "no screenshot"):
            self.archive(output="replay-only", log=replay)

    def test_only_exact_original_log_records_acknowledge_frames(self):
        for malformed in (self.log.replace("LogTemp: Display:", "LogAutomationController: LogTemp:"),
                          self.log + " [log]", self.log.replace("LogTemp: Display: ", ""),
                          self.log.replace("LogTemp: Display:", "LogTemp: Warning:")):
            with self.subTest(log=malformed):
                with self.assertRaisesRegex(ValueError, "no screenshot"):
                    self.archive(log=malformed)


class BowCaptureTests(unittest.TestCase):
    """Synthetic framebuffer unit inputs; never presented as engine evidence."""
    @staticmethod
    def png(cx, cy, blank=False, width=160, height=90):
        rows = [bytearray([32, 32, 32] * width) for _ in range(height)]
        if not blank:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                for length in range(4, 11):
                    x, y = cx + length * dx, cy + length * dy
                    rows[y][x * 3:x * 3 + 3] = bytes((244, 237, 220))
        def chunk(kind, data):
            return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(
            b"IDAT", zlib.compress(b"".join(b"\0" + row for row in rows))) + chunk(b"IEND", b"")

    def observations(self):
        result = []
        for index, phase in enumerate(VERIFY.bow_capture_validation.PHASES):
            center = ([80, 45], [82, 44], [78, 46], [80, 45])[index]
            offset = ([0, 0], [.14, .23], [-.14, -.23], [0, 0])[index]
            meta = dict(phase=phase, viewport=[160, 90], frame=[100, 350, 420, 421][index],
                        draw_age_s=[1, 5.6, 6.8, 6.82][index], wall_elapsed_s=[1.1, 5.7, 6.9, 6.92][index],
                        drawing=index < 3, attack_held=index < 3, ammo=12 if index < 3 else 11,
                        reticle=center, projected=center.copy(), target=[80, 45], camera=[0, 0, 152], rotation=[0, 0, 0],
                        offset_degrees=offset, ray=[1, 0, 0], bow_quat=[0, 0, 0, 1],
                        presentation_schema_version=2, fallback_bow=True,
                        presentation_pose="fallback.bow.drawn" if index < 3 else "fallback.bow",
                        presentation_projected_direction=[1, 0, 0], world_fov=94, first_person_fov=70)
            meta.update(fallback_near_clip_cm=10, fallback_aim_clearance_pixels=160*.07,
                        fallback_component_bounds=[
                            dict(part=name, narrow_arrow=name in ("NockedArrow", "Arrowhead"), corner_count=8,
                                 min_fp_depth_cm=30, projected_rect=rect)
                            for name, rect in (("YumiLower", [35, 40, 41, 100]), ("YumiUpper", [35, -20, 41, 45]),
                                               ("YumiGrip", [32, 40, 42, 60]), ("YumiString", [25, -30, 27, 100]),
                                               ("FurPaw", [15, 55, 40, 80]), ("NockedArrow", [55, 47, 79, 49]),
                                               ("Arrowhead", [78, 47, 80, 49]))])
            if phase == "negative":
                meta["shot_ray"] = meta["ray"].copy()
                meta.update(sample_world_s=100, release_world_s=100, release_delay_s=0,
                            release_wall_elapsed_s=meta["wall_elapsed_s"]+.001, release_frame=meta["frame"],
                            shot_world_s=100, shot_frame=meta["frame"],
                            release_ray=meta["ray"].copy(), release_projected=center.copy(), shot_matches_render_sample=True)
            result.append((meta, self.png(*center)))
        return result

    def test_original_cross_pixels_and_complete_live_sequence(self):
        frames = [(meta, VERIFY.bow_capture_validation.verify_frame(meta, png, 160, 90)) for meta, png in self.observations()]
        VERIFY.bow_capture_validation.verify_sequence(frames)
        for meta, measured in frames:
            self.assertEqual(measured["center"], meta["reticle"])

    def test_unmoved_hidden_or_misprojected_reticle_cannot_pass(self):
        meta, png = self.observations()[1]
        for changed, pixels in ((dict(meta, projected=[80, 45]), png),
                                (meta, self.png(80, 45)), (meta, self.png(82, 44, blank=True)),
                                (dict(meta, draw_age_s=8), png), (dict(meta, attack_held=False), png)):
            with self.subTest(changed=changed):
                with self.assertRaises(ValueError):
                    VERIFY.bow_capture_validation.verify_frame(changed, pixels, 160, 90)

    def test_presentation_requires_current_native_direction_and_explicit_fallback(self):
        meta, png = self.observations()[1]
        for changes in ({"presentation_schema_version": None}, {"fallback_bow": False},
                        {"presentation_pose": "bow"}, {"presentation_projected_direction": [1, .02, 0]},
                        {"presentation_projected_direction": [2, 0, 0]}, {"world_fov": 0},
                        {"first_person_fov": float("nan")}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                VERIFY.bow_capture_validation.verify_frame(dict(meta, **changes), png, 160, 90)
        frames = [(m, VERIFY.bow_capture_validation.verify_frame(m, image, 160, 90)) for m, image in self.observations()]
        frames[1][0]["first_person_fov"] = 80
        with self.assertRaisesRegex(ValueError, "camera FOV"):
            VERIFY.bow_capture_validation.verify_sequence(frames)

    def test_actual_fallback_volumes_must_clear_aim_without_hiding_the_bow(self):
        for mutation in ("missing", "duplicate", "occluding", "hidden_grip", "tiny_grip", "hidden_stave",
                         "near_clip", "relaxed_margin", "wide_arrow", "arrow_as_grip", "missing_corners"):
            meta, png = self.observations()[0]
            rows = meta["fallback_component_bounds"]
            if mutation == "missing": rows.pop()
            elif mutation == "duplicate": rows[0] = rows[1].copy()
            elif mutation == "occluding": rows[2]["projected_rect"] = [72, 40, 82, 60]
            elif mutation == "hidden_grip": rows[2]["projected_rect"] = [-20, 40, -10, 60]
            elif mutation == "tiny_grip": rows[2]["projected_rect"] = [32, 40, 33, 41]
            elif mutation == "hidden_stave":
                rows[0]["projected_rect"] = [-30, 40, -20, 100]
                rows[1]["projected_rect"] = [-30, -20, -20, 45]
            elif mutation == "near_clip": rows[0]["min_fp_depth_cm"] = 11
            elif mutation == "relaxed_margin": meta["fallback_aim_clearance_pixels"] = 1
            elif mutation == "wide_arrow": rows[5]["projected_rect"] = [55, 40, 79, 55]
            elif mutation == "arrow_as_grip": rows[2]["narrow_arrow"] = True
            elif mutation == "missing_corners": rows[2]["corner_count"] = 1
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                VERIFY.bow_capture_validation.verify_frame(meta, png, 160, 90)

    def test_shot_recenter_missing_phase_and_camera_motion_are_rejected(self):
        data = self.observations()
        wrong_shot = dict(data[2][0], shot_ray=[0, 1, 0])
        with self.assertRaisesRegex(ValueError, "released shot"):
            VERIFY.bow_capture_validation.verify_frame(wrong_shot, data[2][1], 160, 90)
        frames = [(meta, VERIFY.bow_capture_validation.verify_frame(meta, png, 160, 90)) for meta, png in data]
        with self.assertRaisesRegex(ValueError, "exactly"):
            VERIFY.bow_capture_validation.verify_sequence(frames[:-1])
        frames[2][0]["camera"] = [100, 0, 152]
        with self.assertRaisesRegex(ValueError, "camera"):
            VERIFY.bow_capture_validation.verify_sequence(frames)

    def test_archive_binds_original_png_and_observation_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project, output = root / "project", root / "out"
            folder = project / "Saved/Screenshots/SoraBowAim/160x90/unique"
            folder.mkdir(parents=True)
            markers = []
            for meta, png in self.observations():
                image = folder / (meta["phase"] + ".png")
                image.write_bytes(png)
                image.with_suffix(".json").write_text(json.dumps(meta))
                markers.append("LogTemp: Display: SORA_BOW_AIM_FRAME " + str(image))
            report = {"tests": [{"fullTestPath": "SoraCapture.BowAim.Live"}]}
            frames = VERIFY.archive_frames("\n".join(markers), report, project, root, output, 0, 160, 90)
            self.assertEqual(len(frames), 4)
            for frame in frames:
                self.assertEqual(hashlib.sha256((output / frame["observations"]).read_bytes()).hexdigest(), frame["observations_sha256"])
                self.assertEqual((output / frame["path"]).read_bytes(), Path(frame["source"]).read_bytes())
                self.assertIn("not playthrough or art acceptance", frame["capture_kind"])
            with self.assertRaisesRegex(ValueError, "exactly"):
                VERIFY.archive_frames("\n".join(markers[:-1]), report, project, root, root / "partial", 0, 160, 90)

    def test_callback_delay_is_measured_without_claiming_same_rendered_ray(self):
        meta, png = self.observations()[2]
        meta.update(release_world_s=100.02, release_delay_s=.02, release_wall_elapsed_s=6.95,
                    release_frame=421, shot_world_s=100.02, shot_frame=421,
                    release_ray=[.999, .001, 0], shot_ray=[.999, .001, 0],
                    release_projected=[78.1, 46], shot_matches_render_sample=False)
        VERIFY.bow_capture_validation.verify_frame(meta, png, 160, 90)
        for changed in (dict(meta, shot_matches_render_sample=True), dict(meta, release_delay_s=0),
                        dict(meta, shot_world_s=100.03)):
            with self.assertRaises(ValueError):
                VERIFY.bow_capture_validation.verify_frame(changed, png, 160, 90)

    def test_all_png_row_filters_preserve_original_rgb(self):
        expected = [bytearray((10, 20, 30, 40, 50, 60)), bytearray((12, 22, 32, 42, 52, 62))]
        encoded = ((expected[0], expected[1]),
                   ([10, 20, 30, 30, 30, 30], [12, 22, 32, 30, 30, 30]),
                   (expected[0], [2]*6),
                   ([10, 20, 30, 35, 40, 45], [7, 12, 17, 16, 16, 16]),
                   ([10, 20, 30, 30, 30, 30], [2]*6))
        def chunk(kind, data):
            return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        for mode, rows in enumerate(encoded):
            png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0)) + chunk(
                b"IDAT", zlib.compress(b"".join(bytes([mode])+bytes(row) for row in rows))) + chunk(b"IEND", b"")
            self.assertEqual(VERIFY.png_dimensions(png), (2, 2))
            self.assertEqual(VERIFY.bow_capture_validation.rgb8(png), (2, 2, 3, expected))


class CodexCaptureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.project = self.root / "project with spaces"
        self.folder = self.project / "Saved/Screenshots/SoraCodex/2x1/unique"
        self.folder.mkdir(parents=True)
        self.output_number = 0
        def chunk(kind, payload):
            return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))
        self.png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 1, 8, 2, 0, 0, 0))
                    + chunk(b"IDAT", zlib.compress(b"\0\xff\0\0\0\xff\0")) + chunk(b"IEND", b""))
        self.paths = [self.folder / (phase + ".png") for phase in VERIFY.codex_capture_validation.PHASES]
        for path in self.paths:
            path.write_bytes(self.png)
        self.started = min(path.stat().st_mtime_ns for path in self.paths) - 1
        self.report = {"tests": [{"fullTestPath": "SoraCapture.Codex.Live"}]}
        self.metadata = {"schema": VERIFY.codex_capture_validation.SCHEMA,
                         "scope": VERIFY.codex_capture_validation.SCOPE,
                         "prepared_discoveries": True, "passed": True, "frame_count": 9,
                         "viewport": [2, 1], "frames": []}
        for index, phase in enumerate(VERIFY.codex_capture_validation.PHASES):
            frame = dict(name=phase, file=phase + ".png", prepared_discoveries=True,
                         screen_name="reader" if index >= 3 else "index",
                         request_frame=100 + 10 * index, screenshot_processed_frame=102 + 10 * index,
                         english=index != 6, text_scale=1 if index < 4 else 1.5,
                         entries=0 if index == 0 else 49, focus=1 if index == 0 else 48 if index == 2 else 0)
            if index >= 3:
                frame.update(entry_id="codex_toshiya" if index >= 7 else "ch04.c06",
                             entry_key=48 if index >= 7 else 23, scroll_offset=80 if index in (5, 8) else 0,
                             scroll_end=80, content_bottom=120 if index in (5, 8) else 200, viewport_height=120)
            self.metadata["frames"].append(frame)
        self.sidecar = self.folder / "capture.json"
        self.write_metadata()

    def write_metadata(self):
        self.sidecar.write_text(json.dumps(self.metadata, indent=2) + "\n")

    def log(self, paths=None):
        return "\n".join("[2026.10.23-01.00.00:000][  1]LogTemp: Display: SORA_CODEX_FRAME " + str(path)
                         for path in (self.paths if paths is None else paths))

    def archive(self, log=None):
        self.output_number += 1
        output = self.root / f"archive-{self.output_number}"
        return output, VERIFY.archive_frames(self.log() if log is None else log, self.report, self.project,
                                              self.root, output, self.started, 2, 1)

    def test_exact_nine_original_frames_and_source_metadata_are_archived(self):
        output, frames = self.archive()
        original = self.sidecar.read_bytes()
        self.assertEqual(len(frames), 9)
        self.assertEqual([frame["codex_phase"] for frame in frames], list(VERIFY.codex_capture_validation.PHASES))
        self.assertEqual(len({frame["observations"] for frame in frames}), 1)
        for frame in frames:
            self.assertEqual((output / frame["path"]).read_bytes(), self.png)
            self.assertEqual(frame["sha256"], hashlib.sha256(self.png).hexdigest())
            self.assertEqual((output / frame["observations"]).read_bytes(), original)
            self.assertEqual(frame["observations_source"], str(self.sidecar))
            self.assertEqual(frame["observations_sha256"], hashlib.sha256(original).hexdigest())
            self.assertEqual(frame["capture_kind"], VERIFY.codex_capture_validation.SCOPE)
        self.sidecar.write_text("overwritten by a later run")
        self.paths[0].write_bytes(b"later frame")
        self.assertEqual((output / frames[0]["observations"]).read_bytes(), original)
        self.assertEqual((output / frames[0]["path"]).read_bytes(), self.png)

    def test_empty_partial_duplicate_and_replayed_acknowledgements_fail(self):
        for log, error in (("", "no screenshot"), (self.log(self.paths[:-1]), "nine unique"),
                           (self.log(self.paths + self.paths[:1]), "duplicate"),
                           (self.log().replace("LogTemp: Display:", "LogAutomationController: Display:") + " [log]", "no screenshot"),
                           (self.log().replace("LogTemp: Display:", "LogAutomationController: Display:"), "no screenshot")):
            with self.subTest(error=error, log=log[:50]), self.assertRaisesRegex(ValueError, error):
                self.archive(log)

    def test_missing_stale_or_external_metadata_cannot_qualify_fresh_pngs(self):
        self.sidecar.unlink()
        with self.assertRaises(OSError):
            self.archive()
        self.write_metadata()
        os.utime(self.sidecar, ns=(self.started - 1, self.started - 1))
        with self.assertRaisesRegex(ValueError, "stale Codex"):
            self.archive()
        # Fresh since run start but older than a later overwritten PNG is also stale.
        self.write_metadata()
        newer = self.sidecar.stat().st_mtime_ns + 10
        os.utime(self.paths[0], ns=(newer, newer))
        with self.assertRaisesRegex(ValueError, "stale Codex"):
            self.archive()
        self.sidecar.unlink()
        outside = self.root / "outside.json"
        outside.write_text(json.dumps(self.metadata))
        self.sidecar.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "escapes"):
            self.archive()

    def test_failed_wrong_schema_scope_count_or_viewport_reports_fail(self):
        for key, bad, error in (("passed", False, "did not pass"), ("passed", 1, "did not pass"),
                                ("schema", "unknown", "schema"), ("prepared_discoveries", False, "scope"),
                                ("scope", "earned all collectibles", "scope"), ("frame_count", 8, "nine"),
                                ("frame_count", True, "frame_count"), ("viewport", [1920, 1080], "viewport"),
                                ("viewport", [2, True], "viewport")):
            with self.subTest(key=key, bad=bad):
                original = self.metadata[key]
                self.metadata[key] = bad
                self.write_metadata()
                with self.assertRaisesRegex(ValueError, error):
                    self.archive()
                self.metadata[key] = original

    def test_missing_duplicate_wrong_filename_and_out_of_order_phases_fail(self):
        original = copy.deepcopy(self.metadata["frames"])
        variants = [original[:-1], original + original[:1], original[:1] + original[:1] + original[2:],
                    [original[1], original[0]] + original[2:]]
        wrong_file = copy.deepcopy(original)
        wrong_file[2]["file"] = "../index-last.png"
        variants.append(wrong_file)
        for rows in variants:
            with self.subTest(names=[row["name"] for row in rows]):
                self.metadata["frames"] = rows
                self.write_metadata()
                with self.assertRaisesRegex(ValueError, "nine|phase/filename"):
                    self.archive()
        self.metadata["frames"] = original
        self.write_metadata()
        with self.assertRaisesRegex(ValueError, "nine unique"):
            self.archive(self.log(list(reversed(self.paths))))

    def test_phase_state_frame_identity_and_actual_tail_must_match(self):
        cases = [(6, "english", True), (4, "text_scale", 1), (2, "focus", 0), (1, "entries", 48),
                 (3, "screen_name", "index"), (7, "entry_id", "ch04.c06"), (3, "entry_key", 0),
                 (6, "entry_id", "ch03.c06"), (3, "request_frame", 1), (3, "screenshot_processed_frame", 1),
                 (4, "request_frame", True), (5, "scroll_end", 0), (5, "scroll_offset", 0),
                 (5, "content_bottom", 200), (4, "scroll_offset", 20), (5, "viewport_height", float("nan")),
                 (0, "prepared_discoveries", False)]
        for index, key, bad in cases:
            with self.subTest(phase=index, key=key):
                original = self.metadata["frames"][index][key]
                self.metadata["frames"][index][key] = bad
                self.write_metadata()
                with self.assertRaises(ValueError):
                    self.archive()
                self.metadata["frames"][index][key] = original

    def test_toshiya_end_requires_its_own_entry_language_and_visible_tail(self):
        cases = [("entry_id", "ch04.c06"), ("entry_key", 23), ("english", False),
                 ("text_scale", 1), ("scroll_offset", 0), ("scroll_end", 0),
                 ("content_bottom", 200), ("content_bottom", -1),
                 ("viewport_height", float("nan")), ("request_frame", 170)]
        original = copy.deepcopy(self.metadata["frames"][-1])
        for key, bad in cases:
            with self.subTest(key=key, bad=bad):
                self.metadata["frames"][-1] = dict(original, **{key: bad})
                self.write_metadata()
                with self.assertRaises(ValueError):
                    self.archive()
        self.metadata["frames"][-1] = original

    def test_toshiya_end_cannot_substitute_a_different_content_extent(self):
        # Each false tail is individually within its declared clip and at its
        # declared end, but no longer belongs to the preceding Toshiya top.
        original = copy.deepcopy(self.metadata["frames"][-1])
        for changes in ({"scroll_offset": 90, "scroll_end": 90},
                        {"viewport_height": 140}, {"content_bottom": 100}):
            with self.subTest(changes=changes):
                self.metadata["frames"][-1] = dict(original, **changes)
                self.write_metadata()
                with self.assertRaisesRegex(ValueError, "top-phase"):
                    self.archive()
        self.metadata["frames"][-1] = original

    def test_former_eight_frame_success_cannot_claim_toshiya_end(self):
        self.metadata["schema"] = "sora-arena.codex-capture.v1"
        self.metadata["frame_count"] = 8
        self.metadata["frames"] = self.metadata["frames"][:-1]
        self.write_metadata()
        with self.assertRaisesRegex(ValueError, "schema"):
            self.archive(self.log(self.paths[:-1]))
        # Relabelling an old receipt with the current schema is insufficient.
        self.metadata["schema"] = VERIFY.codex_capture_validation.SCHEMA
        self.write_metadata()
        with self.assertRaisesRegex(ValueError, "nine"):
            self.archive(self.log(self.paths[:-1]))

    def test_multiple_run_folders_cannot_hide_duplicate_phases(self):
        other = self.folder.parent / "another"
        other.mkdir()
        paths = []
        for path in self.paths:
            target = other / path.name
            target.write_bytes(self.png)
            paths.append(target)
        (other / "capture.json").write_text(json.dumps(self.metadata))
        with self.assertRaisesRegex(ValueError, "one nine-frame"):
            self.archive(self.log(self.paths + paths))

    def test_successful_automation_without_codex_frames_fails_the_cli_archive(self):
        output = self.root / "cli-archive"
        output.mkdir()
        (output / "source-commit.txt").write_text("test source")
        (output / "source-status.txt").write_text("")
        log = self.root / "editor.log"
        data = b"Found 1 automation tests based on 'SoraCapture.Codex.Live'\n"
        log.write_bytes(data)
        report = self.root / "report.json"
        report.write_text(json.dumps({"devices": [{"rHI": "Metal", "renderMode": "SM6"}],
                                      "tests": [{"fullTestPath": "SoraCapture.Codex.Live", "state": "Success"}]}))
        receipt = self.root / "log-completion.json"
        receipt.write_text(json.dumps({"process_returncode": 0, "runner_status": 0, "stream_eof": True,
                                       "failure": None, "log_bytes": len(data), "log_sha256": hashlib.sha256(data).hexdigest()}))
        command = [sys.executable, str(Path(VERIFY.__file__)), str(report), str(log), "0", "sm6",
                   "--archive", str(self.project), str(self.root), str(output), str(self.started), "2", "1", "SoraCapture.Codex.Live",
                   "--log-completion", str(receipt)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        manifest = json.loads((output / "capture.json").read_text())
        self.assertEqual(manifest["frames"], [])
        self.assertTrue(any("Codex." in error and "no screenshot" in error for error in manifest["failures"]))

    def test_verifier_phases_and_scope_match_the_actual_fixture(self):
        import re
        root = Path(__file__).resolve().parents[2]
        source = (root / "Source/SoraArena/Private/SoraCodexCapture.cpp").read_text()
        declaration = re.search(r"const TCHAR\* Names\[\]=\{(.*?)\};", source, re.S).group(1)
        self.assertEqual(tuple(re.findall(r'TEXT\("([^"\n]+)"\)', declaration)), VERIFY.codex_capture_validation.PHASES)
        self.assertIn(VERIFY.codex_capture_validation.SCHEMA, source)
        self.assertIn(VERIFY.codex_capture_validation.SCOPE, source)
        self.assertIn('UE_LOG(LogTemp,Display,TEXT("SORA_CODEX_FRAME %s"),*Pending);', source)


if __name__ == "__main__":
    unittest.main()
