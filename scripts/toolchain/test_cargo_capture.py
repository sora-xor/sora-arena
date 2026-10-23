"""Reject falsified cargo state, clocks, cleanup and original-frame archives."""
import copy
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

SPEC = importlib.util.spec_from_file_location("capture_report", Path(__file__).with_name("verify-capture-report.py"))
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)
CARGO = VERIFY.cargo_capture_validation


def stock(done, rope=True):
    result = dict(deliveries=done, pack_quantity=30-10*done, stand_count=3,
                  stand_quantities=[10 if i < done else 0 for i in range(3)],
                  objective_ja=f"麦 残り {30-10*done}束（配達 {done} / 3）",
                  objective_en=f"Barley: {30-10*done} sheaves left / Delivered {done} of 3")
    if rope:
        result.update(rope_segments=12, rope_collision=False, halter=[0, 0, 110], tie=[280, 0, 160],
                      rendered_halter=[0, 0, 110], rendered_tie=[280, 0, 160])
    return result


def observations():
    data = dict(schema=CARGO.SCHEMA, scope=CARGO.SCOPE, passed=True, viewport=[1280, 720],
                prepared_checkpoint=True, frozen_ai=True, mapped_start_dismount=True, ordinary_clock=True,
                profiles_preserved=True, mappings_preserved=True, inputs_released=True, temporary_slot_deleted=True,
                cargo_completions=1, cinematic_elapsed_ms=90000, cinematic_world_s=90.01, cinematic_wall_s=90.02,
                cinematic_end_world_s=109.01, cinematic_end_wall_s=120.02,
                terminal_before_teardown=stock(3, False), frames=[], holds=[], preparations=[])
    for index, phase in enumerate(CARGO.PHASES):
        row = dict(name=phase, file=phase+".png", request_frame=100+index*100,
                   screenshot_processed_frame=100+index*100, world_s=[10,15,20,114.12][index],
                   wall_s=[13,21,29,126.23][index], paused=True, english=True, hud_drawn=True,
                   interact_held=False, dialogue_active=False, queued_lines=0, beat=13 if index<3 else 15, destination=max(0,index-1), camera=[-450,-1150,480])
        if index<3:
            row.update(stock=stock(index), horse_screen_bounds=[[350,300,550,480],[600,300,900,480]],
                       upper_hud_bounds=[[15,63,626,190],[725,63,1265,280]], projected_subjects=[[200+i*100, 300] for i in range(5)])
        else:
            row.update(pack_count=0, stand_count=0, notice_ja="登録 | 麦 残り 0束", notice_en="Registered / Barley: 0 sheaves left", notice_remaining_s=6.99, notice_count=1, notice_title_retained=True)
        data["frames"].append(row)
    for index in range(3):
        resume_world, resume_wall = data["frames"][index]["world_s"], data["frames"][index]["wall_s"] + .1
        start_world, start_wall = resume_world + 1.1, resume_wall + 1.1
        end_world, end_wall = start_world + 3.01, start_wall + 3.02
        data["holds"].append(dict(destination=index, before=index, after=index+1, mapped_interact=True, paused_during_hold=False,
                                  resume_frame=100+index*100, start_frame=110+index*100, end_frame=180+index*100,
                                  resume_world_s=resume_world, resume_wall_s=resume_wall,
                                  start_world_s=start_world, end_world_s=end_world, world_elapsed_s=end_world-start_world,
                                  start_wall_s=start_wall, end_wall_s=end_wall, wall_elapsed_s=end_wall-start_wall))
        data["preparations"].append(dict(destination=index, dropoff=[index*1000,0,0], hero=[index*1000,-180,98],
                                         steed=[index*1000-80,450,0], pack=[index*1000-380,450,0], camera=[index*1000-450,-1150,480]))
    # b15 starts on the final accepted transfer, before the latent observer releases Interact.
    data["cinematic_end_world_s"] = data["holds"][-1]["end_world_s"] - .01 + data["cinematic_world_s"]
    data["cinematic_end_wall_s"] = data["holds"][-1]["end_wall_s"] - .01 + data["cinematic_wall_s"]
    data["frames"][-1]["world_s"] = data["cinematic_end_world_s"] + .01
    data["frames"][-1]["wall_s"] = data["cinematic_end_wall_s"] + 3
    data["cinematic_start_world_s"] = data["cinematic_end_world_s"] - data["cinematic_world_s"]
    data["cinematic_start_wall_s"] = data["cinematic_end_wall_s"] - data["cinematic_wall_s"]
    return data


class CargoCaptureTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name).resolve(); self.project=self.root/"project with spaces"
        self.folder=self.project/"Saved/Screenshots/SoraCargo/1280x720/unique"; self.folder.mkdir(parents=True)
        def chunk(kind,payload):
            return struct.pack(">I",len(payload))+kind+payload+struct.pack(">I",zlib.crc32(kind+payload))
        self.png=(b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",1280,720,8,2,0,0,0))+
                  chunk(b"IDAT",zlib.compress((b"\0"+b"\x10\x20\x30"*1280)*720))+chunk(b"IEND",b""))
        self.paths=[self.folder/(phase+".png") for phase in CARGO.PHASES]
        for path in self.paths: path.write_bytes(self.png)
        self.started=min(path.stat().st_mtime_ns for path in self.paths)-1
        self.data=observations(); self.sidecar=self.folder/"capture.json"; self.write()
        self.report={"tests":[{"fullTestPath":"SoraCapture.Cargo.Transfer"}]}; self.serial=0

    def write(self):
        self.sidecar.write_text(json.dumps(self.data,ensure_ascii=False,indent=2)+"\n")

    def log(self, paths=None):
        return "\n".join("[2026.10.24-01.00.00:000][  1]LogTemp: Display: SORA_CARGO_FRAME "+str(path)
                         for path in (self.paths if paths is None else paths))

    def archive(self, log=None):
        self.serial+=1; output=self.root/f"archive-{self.serial}"
        return output, VERIFY.archive_frames(self.log() if log is None else log,self.report,self.project,self.root,
                                              output,self.started,1280,720)

    def verify(self):
        CARGO.verify_sequence(self.data,[p.name for p in self.paths],1280,720)

    def test_originals_and_sidecar_are_byte_exact_and_survive_later_overwrites(self):
        output,frames=self.archive(); raw=self.sidecar.read_bytes()
        self.assertEqual(len(frames),4)
        self.assertEqual([f["cargo_phase"] for f in frames],list(CARGO.PHASES))
        for f in frames:
            self.assertEqual((output/f["path"]).read_bytes(),self.png)
            self.assertEqual(f["sha256"],hashlib.sha256(self.png).hexdigest())
            self.assertEqual((output/f["observations"]).read_bytes(),raw)
            self.assertEqual(f["observations_sha256"],hashlib.sha256(raw).hexdigest())
            self.assertEqual(f["capture_kind"],CARGO.SCOPE)
        self.sidecar.write_text("later run"); self.paths[0].write_bytes(b"later run")
        self.assertEqual((output/frames[0]["path"]).read_bytes(),self.png)
        self.assertEqual((output/frames[0]["observations"]).read_bytes(),raw)

    def test_missing_partial_duplicate_reordered_and_replayed_acknowledgements_fail(self):
        for log in ("",self.log(self.paths[:-1]),self.log(self.paths+self.paths[:1]),self.log(list(reversed(self.paths))),
                    self.log().replace("LogTemp: Display:","LogAutomationController: Display:")+" [log]"):
            with self.subTest(log=log[:80]), self.assertRaises(ValueError): self.archive(log)
        self.report={"tests":[{"fullTestPath":"SoraCapture.Cargo.Other"}]}
        with self.assertRaisesRegex(ValueError,"matching"): self.archive()

    def test_stale_external_metadata_and_multi_run_substitution_fail(self):
        os.utime(self.sidecar,ns=(self.started-1,self.started-1))
        with self.assertRaisesRegex(ValueError,"stale"): self.archive()
        self.write(); newer=self.sidecar.stat().st_mtime_ns+10; os.utime(self.paths[0],ns=(newer,newer))
        with self.assertRaisesRegex(ValueError,"stale"): self.archive()
        self.sidecar.unlink(); outside=self.root/"outside.json"; outside.write_text(json.dumps(self.data)); self.sidecar.symlink_to(outside)
        with self.assertRaisesRegex(ValueError,"escapes"): self.archive()
        self.sidecar.unlink(); self.write()
        other=self.folder.parent/"different"; other.mkdir(); replacement=other/self.paths[-1].name; replacement.write_bytes(self.png)
        with self.assertRaisesRegex(ValueError,"one matching"): self.archive(self.log(self.paths[:-1]+[replacement]))

    def test_cleanup_scope_and_real_frame_flags_are_strict_booleans(self):
        original=copy.deepcopy(self.data)
        for key in ("passed","prepared_checkpoint","frozen_ai","mapped_start_dismount","ordinary_clock",
                    "profiles_preserved","mappings_preserved","inputs_released","temporary_slot_deleted"):
            for bad in (False,1,None):
                with self.subTest(key=key,bad=bad):
                    self.data=copy.deepcopy(original); self.data[key]=bad
                    with self.assertRaises(ValueError): self.verify()
        for key,bad in (("schema","unknown"),("scope","playthrough"),("viewport",[True,720]),("viewport",[1920,1080])):
            self.data=copy.deepcopy(original); self.data[key]=bad
            with self.assertRaises(ValueError): self.verify()

    def test_actual_stock_conservation_hud_and_rope_bindings_are_required(self):
        original=copy.deepcopy(self.data)
        cases=[("deliveries",0),("pack_quantity",30),("stand_count",2),("stand_quantities",[0,0,0]),
               ("objective_ja","0"),("objective_en","0"),("rope_segments",0),("rope_collision",True),
               ("halter",[False,0,0]),("rendered_halter",[2,0,110]),("rendered_tie",[float("nan"),0,160])]
        for key,bad in cases:
            with self.subTest(key=key):
                self.data=copy.deepcopy(original); self.data["frames"][1]["stock"][key]=bad
                with self.assertRaises(ValueError): self.verify()
        self.data=copy.deepcopy(original); self.data["terminal_before_teardown"]["stand_quantities"]=[10,10,0]
        with self.assertRaises(ValueError): self.verify()

    def test_final_zero_is_real_post_cinematic_feedback_and_not_surviving_props(self):
        original=copy.deepcopy(self.data)
        cases=[("notice_ja","麦 残り 10束"),("notice_en","Barley: 10 sheaves left"),("notice_remaining_s",0),
               ("notice_remaining_s",8),("notice_count",2),("notice_title_retained",False),("pack_count",1),("stand_count",3),("beat",14),("stock",stock(3)),
               ("world_s",100),("wall_s",100)]
        for key,bad in cases:
            with self.subTest(key=key):
                self.data=copy.deepcopy(original); self.data["frames"][-1][key]=bad
                with self.assertRaises(ValueError): self.verify()
        for key,bad in (("cinematic_elapsed_ms",89999),("cinematic_start_world_s",1),("cinematic_start_wall_s",1),("cinematic_world_s",0),("cinematic_wall_s",3),("cargo_completions",2)):
            self.data=copy.deepcopy(original); self.data[key]=bad
            with self.assertRaises(ValueError): self.verify()

    def test_active_holds_and_projection_cannot_be_forged_by_phase_names(self):
        original=copy.deepcopy(self.data)
        for key,bad in (("world_elapsed_s",2.5),("wall_elapsed_s",2.5),("paused_during_hold",True),("mapped_interact",False),
                        ("before",1),("after",3),("destination",2),("start_world_s",1),("end_world_s",200)):
            self.data=copy.deepcopy(original); self.data["holds"][0][key]=bad
            with self.subTest(key=key),self.assertRaises(ValueError): self.verify()
        for key,bad in (("paused",False),("dialogue_active",True),("queued_lines",1),("english",False),("hud_drawn",False),("interact_held",True),
                        ("request_frame",True),("horse_screen_bounds",[[350,300,550,480],[600,260,900,480]]),("upper_hud_bounds",[]),("screenshot_processed_frame",101),("projected_subjects",[[1,1]]*5)):
            self.data=copy.deepcopy(original); self.data["frames"][0][key]=bad
            with self.subTest(key=key),self.assertRaises(ValueError): self.verify()
        self.data=copy.deepcopy(original); self.data["preparations"][0]["hero"]=[999,999,98]
        with self.assertRaises(ValueError): self.verify()

    def test_semantic_failure_retains_originals_sidecar_and_manifest_entries(self):
        self.data["frames"][-1]["notice_remaining_s"] = 0
        self.write()
        with self.assertRaises(VERIFY.CargoCaptureEvidenceError) as caught:
            self.archive()
        self.assertEqual(len(caught.exception.frames), 4)
        for frame in caught.exception.frames:
            output = self.root/f"archive-{self.serial}"
            self.assertEqual((output/frame["path"]).read_bytes(), self.png)
            self.assertEqual((output/frame["observations"]).read_bytes(), self.sidecar.read_bytes())

    def test_hold_resume_and_press_boundaries_cannot_reuse_a_screenshot_frame(self):
        original = copy.deepcopy(self.data)
        cases = (("resume_frame", 99), ("start_frame", 100), ("start_frame", 180), ("end_frame", 201),
                 ("resume_world_s", 9.9), ("resume_world_s", 11.1), ("resume_wall_s", 12.9),
                 ("resume_wall_s", 13.21), ("start_world_s", 10))
        for key, bad in cases:
            with self.subTest(key=key, bad=bad):
                self.data = copy.deepcopy(original); self.data["holds"][0][key] = bad
                with self.assertRaises(ValueError): self.verify()
        for key in ("resume_frame", "resume_world_s", "resume_wall_s", "start_frame", "end_frame"):
            self.data = copy.deepcopy(original); del self.data["holds"][0][key]
            with self.subTest(missing=key), self.assertRaises(ValueError): self.verify()

    def test_observed_failed_wall_hold_stays_rejected_after_world_time_passes(self):
        # Actual 812d70c run: PNG callback press, 3.00095 world seconds but
        # only 2.89139 wall seconds. New resume metadata must not waive that gate.
        hold = self.data["holds"][0]
        hold["world_elapsed_s"] = 3.0009529180824757
        hold["end_world_s"] = hold["start_world_s"] + hold["world_elapsed_s"]
        hold["wall_elapsed_s"] = 2.891394790261984
        hold["end_wall_s"] = hold["start_wall_s"] + hold["wall_elapsed_s"]
        with self.assertRaisesRegex(ValueError, "three ordinary active seconds"): self.verify()

    def test_capture_source_preserves_the_gameplay_admission_boundary(self):
        source = (Path(__file__).resolve().parents[2]/"Source/SoraArena/Private/SoraCargoCapture.cpp").read_text()
        # The fixture may prepare a scene, but must never manufacture earned
        # stock, advance the cinematic, or dispatch completion itself.
        for forbidden in ("DeliverLoad(", "CompleteActiveBeat(", "SkipCinematic(", "SetGlobalTimeDilation(",
                          "SetTimeDilation(", "->Tick(",
                          "ShowCargo(", "ShowKit(", "OnBeatCompleted.Broadcast("):
            with self.subTest(forbidden=forbidden): self.assertNotIn(forbidden, source)
        self.assertFalse(re.search(r"TaskProgress\(\)\.\w+\s*=(?!=)", source))
        self.assertIn("#if WITH_DEV_AUTOMATION_TESTS", source)
        self.assertIn("OnScreenshotRequestProcessed()", source)
        self.assertIn("SeedCheckpoint(*Save,3,13)", source)
        self.assertEqual(source.count("M->BeginRound()"), 1)

    def test_missing_sidecar_or_corrupt_original_png_fails(self):
        self.sidecar.unlink()
        with self.assertRaises(OSError): self.archive()
        self.write(); self.paths[0].write_bytes(self.png[:-12])
        with self.assertRaises(ValueError): self.archive()


if __name__=="__main__": unittest.main()
