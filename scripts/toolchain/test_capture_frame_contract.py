"""Source contract for Canvas-dependent fixture checks and screenshot admission.

These checks prevent the observed between-draw projection regression. They do
not execute Unreal or prove the absence of runtime Canvas warnings.
"""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Source/SoraArena/Private/SoraCaptureAutomation.cpp"
GATES = ("WeaponLayoutFits", "BottomHUDLayoutFits", "StoryTrackerLayoutFits",
         "RhythmCueLayoutFits", "InteractionPromptLayoutFits", "CaptionStoryLayoutFits")


def contract_problems(source):
    problems = []
    try:
        save = source[source.index("void SaveFrame("):source.index("FString BossSeen(")]
        draw = save[save.index("OnReticleDrawn.AddLambda"):save.index("OnScreenshotRequestProcessed().AddLambda")]
        fixture = source[source.index("void QueueWeaponHUDFixture("):source.index("} // namespace SoraCapture")]
        before, validator = fixture.split("SaveFrame(Test,Session,Name,true,[Test]", 1)
        validator, after = validator.split("Queue([Session,Chapter,Beat,English,Name]", 1)
    except ValueError:
        return ["fixture draw validator or guarded screenshot path is absent"]
    if any("SoraHUDPanels::" + gate in before for gate in GATES):
        problems.append("Canvas-dependent geometry is queried before the observed draw")
    if not all(re.search(r"SoraHUDPanels::" + gate + r"\(Frame,(?:\*Hero,)?Why\)", validator) for gate in GATES):
        problems.append("the draw validator no longer retains every fixture layout gate")
    if "UCanvas::ClippedStrLen" not in before or "Text metrics are available between DrawHUD frames" not in before:
        problems.append("the deliberate between-draw font metric regression check was removed")
    if "[Test,Weak,Name,ValidateDraw]" not in draw or "if(Fits&&ValidateDraw) Fits=ValidateDraw(Layout,Why);" not in draw:
        problems.append("fixture validation is not bound to the actual admitted HUD draw")
    required_order = ("SoraCaptureFrameRules::Drawn(State)", "ValidateDraw(Layout,Why)",
                      "if(!Fits)", "Current->GameplayRequestFrame=GFrameCounter;",
                      "FScreenshotRequest::RequestScreenshot(Current->File,true,false);")
    positions = [draw.find(token) for token in required_order]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        problems.append("screenshot request can bypass draw or fixture validation")
    rejected = draw[draw.find("if(!Fits)"):draw.find("Current->GameplayRequestFrame=GFrameCounter;")]
    if "Current->bFrameLayoutRejected=true; return;" not in rejected:
        problems.append("failed fixture geometry does not reject the screenshot")
    fallback = save[save.index("OnScreenshotRequestProcessed().AddLambda"):]
    if not re.search(r"if\(ValidateDraw\)\s*\{[^}]*Session->bFrameLayoutRejected=true;\s*return;\s*\}\s*FScreenshotRequest::RequestScreenshot\(Session->File", fallback):
        problems.append("a fixture outside ordinary gameplay can bypass its draw validator")
    for token in ("SoraCaptureFrameRules::Processed(State,Current->GameplayRequestFrame,GFrameCounter",
                  "GetTimeStamp(*Current->File)!=Current->Previous",
                  "Queue([Session]() { Session->CloseGameplayFrameGuard(); });"):
        if token not in save:
            problems.append("processed-frame identity, fresh-file check or delegate cleanup was removed")
    if "if(!Session->bShotLive||!Session->bFrameWritten) return;" not in after:
        problems.append("fixture can acknowledge an unaccepted original")
    return problems


class CaptureFrameContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text()

    def test_current_fixture_validates_actual_draw_and_retains_all_gates(self):
        self.assertEqual(contract_problems(self.source), [])

    def test_rejects_reintroduced_between_draw_projection(self):
        bad = self.source.replace('const FString Probe=TEXT("SORA HUD 123");',
                                  'SoraHUDPanels::StoryTrackerLayoutFits(Layout,Why);\nconst FString Probe=TEXT("SORA HUD 123");')
        self.assertIn("Canvas-dependent geometry is queried before the observed draw", contract_problems(bad))

    def test_rejects_each_removed_fixture_gate(self):
        for gate in GATES:
            with self.subTest(gate=gate):
                bad = self.source.replace("SoraHUDPanels::" + gate + "(Frame,", "RemovedGate(Frame,")
                self.assertIn("the draw validator no longer retains every fixture layout gate", contract_problems(bad))

    def test_rejects_omitted_validator_invocation(self):
        bad = self.source.replace("if(Fits&&ValidateDraw) Fits=ValidateDraw(Layout,Why);", "")
        self.assertIn("fixture validation is not bound to the actual admitted HUD draw", contract_problems(bad))

    def test_rejects_screenshot_requested_before_validation(self):
        request = "FScreenshotRequest::RequestScreenshot(Current->File,true,false);"
        bad = self.source.replace(request, "").replace("if(Fits&&ValidateDraw)", request + "\nif(Fits&&ValidateDraw)")
        self.assertIn("screenshot request can bypass draw or fixture validation", contract_problems(bad))

    def test_rejects_non_gameplay_fallback_bypass(self):
        bad = self.source.replace("if(ValidateDraw)\n        {", "if(false)\n        {")
        self.assertIn("a fixture outside ordinary gameplay can bypass its draw validator", contract_problems(bad))

    def test_rejects_stale_original_or_missing_delegate_cleanup(self):
        for token in ("GetTimeStamp(*Current->File)!=Current->Previous",
                      "Queue([Session]() { Session->CloseGameplayFrameGuard(); });"):
            with self.subTest(token=token):
                self.assertIn("processed-frame identity, fresh-file check or delegate cleanup was removed",
                              contract_problems(self.source.replace(token, "")))


if __name__ == "__main__":
    unittest.main()
