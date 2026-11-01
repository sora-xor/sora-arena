"""Host tests: the full-editor capture hands its exit to the Python executor, and the engine still works that way.

Run: python3 -m unittest scripts/unreal/test_editor_exit_handoff.py

Captures v2 and v3 (render_yumi_fp_review.py --editor) wrote every original,
logged their marker and Exiting., then hung until SIGKILL. The two samples
(Saved/YumiFP/capture_v*.exit_hang_sample.txt) show the same stack. The
static FTSTicker's destructor destroys a pending UpdateNotificationDeferred
delegate, whose payload holds the "Executing Python Script..." notification
widget. The widget's destruction after Slate's shutdown faults, and the Mac
error handler's `while (!CGCursorIsVisible())` loop never ends.

The cause is the script's own quit. QUIT_EDITOR closes the editor at once, so
EditorPythonExecuter's tick returned on the exit request. Its notification
was completed only at module shutdown, after the last ticker tick, leaving
that one-frame delegate queued. The fix releases the keep-alive and lets the
executor complete the notification and defer QUIT_EDITOR a frame.

- Script: render_yumi_fp_review.py must never call quit_editor, and its
  finish() must release the keep-alive.
- Engine: the installed UE 5.8 source must still read as the fix assumes
  (skipped where the engine source is not installed). If an engine update
  changes it, this fails and the reasoning must be checked again.

Not proof of a clean exit: only a full-editor run can show that
(docs/art-direction/EDITOR_EXIT_HANG.md, the controlled run plan).
"""
from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAPTURE = HERE / "render_yumi_fp_review.py"
ENGINE = Path("/Users/Shared/Epic Games/UE_5.8/Engine")
EXECUTER = ENGINE / "Plugins/Experimental/PythonScriptPlugin/Source/PythonScriptPlugin/Private/EditorUtilities/EditorPythonExecuter.cpp"
NOTIFICATION = ENGINE / "Source/Runtime/Slate/Private/Framework/Notifications/SlateAsyncTaskNotificationImpl.cpp"
EDITOR_SERVER = ENGINE / "Source/Editor/UnrealEd/Private/EditorServer.cpp"
KISMET = ENGINE / "Source/Runtime/Engine/Private/KismetSystemLibrary.cpp"


def calls(tree, name):
    """Every call whose function is an attribute or name called ``name``."""
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            if (isinstance(f, ast.Attribute) and f.attr == name) or (isinstance(f, ast.Name) and f.id == name):
                out.append(node)
    return out


def function(tree, name):
    found = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name]
    if len(found) != 1:
        raise AssertionError(f"expected one function {name}, found {len(found)}")
    return found[0]


def collapsed(path):
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8", errors="replace"))


class Capture(unittest.TestCase):
    tree = ast.parse(CAPTURE.read_text(encoding="utf-8"))

    def test_the_capture_never_quits_the_editor_itself(self):
        self.assertEqual([c.lineno for c in calls(self.tree, "quit_editor")], [])

    def test_finish_releases_the_keep_alive_and_its_tick(self):
        finish = function(self.tree, "finish")
        released = [c for c in calls(finish, "set_keep_python_script_alive")
                    if len(c.args) == 1 and isinstance(c.args[0], ast.Constant) and c.args[0].value is False]
        self.assertEqual(len(released), 1)
        self.assertEqual(len(calls(finish, "unregister_slate_post_tick_callback")), 1)

    def test_the_script_keeps_itself_alive_for_the_executor_to_wait_on(self):
        main = function(self.tree, "main")
        kept = [c for c in calls(main, "set_keep_python_script_alive")
                if len(c.args) == 1 and isinstance(c.args[0], ast.Constant) and c.args[0].value is True]
        self.assertEqual(len(kept), 1)


@unittest.skipUnless(EXECUTER.is_file(), "the UE 5.8 engine source is not installed")
class Engine(unittest.TestCase):
    """The engine behaviour the fix relies on, as the installed source states it."""

    def test_the_executor_quits_when_the_keep_alive_is_released_and_defers_the_quit(self):
        text = collapsed(EXECUTER)
        self.assertIn("if (bIsRunning) { if (!UEditorPythonScriptingLibrary::GetKeepPythonScriptAlive()) "
                      "{ RequestExit(); return; } }", text)
        self.assertIn("void RequestExit() { bExitRequested = true; DestroyNotification(); if (GEngine) "
                      "{ GEngine->HandleDeferCommand(TEXT(\"QUIT_EDITOR\"), *GLog);", text)

    def test_the_executor_returns_early_once_an_exit_is_requested(self):
        text = collapsed(EXECUTER)
        self.assertIn("virtual void Tick(float DeltaTime) override { if (IsExitRequested()) { return; }", text)
        self.assertIn("return bExitRequested || IsEngineExitRequested();", text)

    def test_module_shutdown_completes_a_notification_still_open(self):
        text = collapsed(EXECUTER)
        self.assertIn("void FEditorPythonExecuter::OnShutdownModule() { InternalEditorPythonRunner::DestroyNotification();",
                      text)
        self.assertIn("Notification->SetComplete(true);", text)

    def test_a_notification_update_queues_a_one_frame_ticker_holding_the_widget(self):
        text = collapsed(NOTIFICATION)
        self.assertIn("FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateStatic("
                      "&FSlateAsyncTaskNotificationImpl::UpdateNotificationDeferred, AsWeak(), OwningNotification,", text)
        self.assertIn("// We only want this function to tick once return false;", text)

    def test_quit_editor_closes_the_editor_at_once(self):
        self.assertIn("GEngine->Exec(nullptr, TEXT(\"QUIT_EDITOR\"), *GLog);", collapsed(KISMET))
        self.assertIn("// Don't call quit_editor directly with slate // else if( FParse::Command(&Str,TEXT(\"QUIT_EDITOR\")) ) "
                      "{ CloseEditor(); return true; }", collapsed(EDITOR_SERVER))


if __name__ == "__main__":
    unittest.main()
