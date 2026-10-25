# The full editor's exit hang after a first-person capture

**Status:** a source-only study (2026-10-25), done while root held the
engine lane. The fix is in `render_yumi_fp_review.py`.

**Run 1 of the plan, the handoff probe (`0922b47`), passed** at 19:38Z on
root's bounded handback (`Saved/ExitProbe/handoff.*`).
- The full editor logged its marker at frame 61 and `Exiting.` at frame 63,
  then exited by itself 3 s after the marker.
- Editor exit 0, wrapper exit 0, natural EOF. Nothing was sampled or
  signalled.

**What that shows:** the hand-off path exits cleanly in this engine,
consistent with the mechanism below. **The capture itself has not yet run
with the fix,** so its cause stays provisional until it does.

**The negative control was not run;** root judged v2 and v3 sufficient.

## What happened

Captures v2 and v3 (`UE --editor scripts/unreal/render_yumi_fp_review.py`)
wrote every original and their manifest, and logged
`YUMI_FP_REVIEW_COMPLETE`, then `LogExit: Exiting.`. The editor then never
exited.

- v3 was sampled 85 s after `Exiting.`, and the sample matched v2's.
- SIGTERM changed nothing. SIGKILL ended it 30 s later: editor exit 137,
  wrapper exit 1.
- Both runs are recorded as manually terminated failed captures, with no
  natural EOF:
  - `Saved/YumiFP/capture_v2.exit_hang_sample.txt` and
    `capture_v2.termination.txt`;
  - `capture_v3.exit_hang_sample.txt` and `capture_v3.termination.txt`.

**The sampled main thread:** `-[NSApplication terminate:]` → `exit` →
`__cxa_finalize_ranges` → `FTSTicker::~FTSTicker()`. That destroys a
`TBaseStaticDelegateInstance<bool (float), ..., TWeakPtr<FSlateAsyncTaskNotificationImpl>, TSharedPtr<...>>`,
then the `SNotificationExtendable` widget tree, down to
`FSlateTextBlockLayout::~FSlateTextBlockLayout()`. Its leaf frames loop in
`FMacApplicationErrorOutputDevice::HandleErrorRestoreUI()`.

## The cause, in the installed UE 5.8.3 source

1. **The executor's notification.** A full editor started with
   `-ExecutePythonScript` creates an async task notification, "Executing
   Python Script..." (`EditorPythonExecuter.cpp:25-32`). Its
   `FExecuterTickable` ticks until the script releases its keep-alive. Then
   `RequestExit()` completes the notification (`DestroyNotification()`,
   `SetComplete(true)`) and defers `QUIT_EDITOR` a frame (`:58-80`,
   `:119-126`).
2. **The capture quit by itself, in the same tick.** Its `finish()`
   released the keep-alive and called `unreal.SystemLibrary.quit_editor()`.
   - That is `GEngine->Exec(nullptr, TEXT("QUIT_EDITOR"))`
     (`KismetSystemLibrary.cpp:674-677`), which calls `CloseEditor()` at once
     (`EditorServer.cpp:5990-5996`).
   - The engine's own comment there says: "Don't call quit_editor directly
     with slate".
3. **So the executor's next tick returned early,** at
   `if (IsExitRequested()) { return; }` (`:58-63`, `:129-132`), and its
   notification stayed open.
4. **It was completed only at module shutdown.**
   `FEditorPythonExecuter::OnShutdownModule()` calls `DestroyNotification()`
   (`:214-218`). `FSlateAsyncTaskNotificationImpl::UpdateNotification()` then
   queues a one-frame `UpdateNotificationDeferred` on the core `FTSTicker`,
   whose payload holds a `TSharedPtr<SNotificationItem>`
   (`SlateAsyncTaskNotificationImpl.cpp:262-304`). No ticker tick ever runs it.
5. **At process exit,** the static `FTSTicker`'s destructor destroys that
   delegate. Its payload is the last reference to the notification's widget
   tree, so the tree is destroyed after Slate has shut down, and that
   destruction faults.
6. **The Mac error output device then spins.** `HandleErrorRestoreUI()` runs
   `while (!CGCursorIsVisible()) { CGDisplayShowCursor(...); }`
   (`MacApplicationErrorOutputDevice.cpp:7-21`). In this unattended
   offscreen session the cursor never becomes visible, so it never returns,
   which is the sampled loop.

**The commandlet runs.** Steps 7 to 9 ran in UnrealEditor-Cmd (nullrhi) and
exited by themselves. That is consistent with this account, but not shown by
it: there is no Slate UI there for the notification to destroy.

## The fix

- **What changes:** `render_yumi_fp_review.py`'s `finish()` releases the
  keep-alive and no longer calls `quit_editor()`.
- **Why that works:** the executor's next tick completes its notification
  while the engine still ticks, and defers `QUIT_EDITOR` a frame. So the
  one-frame update runs, and the notification unregisters itself before
  shutdown. That is the path the executor's own comment asks for: "we can't
  close the editor on the same frame that we execute the Python script
  because a full tick needs to happen first".
- **What the run records:** the editor's and the wrapper's exits stay as they
  are. Nothing forces an exit or hides one.

**Not fixed: the engine's unbounded loop.** Any other fault in teardown
would still spin in `HandleErrorRestoreUI`. That is an engine defect to
report, not something project code can change. The fix removes the fault
these two captures hit.

**The same quit, not changed here:** `render_sora_lookdev.py` and
`render_cc0_environment_lookdev.py` also call `quit_editor()`. The same fix
applies if they run in a full editor.

## Tests

`scripts/unreal/test_editor_exit_handoff.py` (host, no engine run):
- the capture never calls `quit_editor`;
- `finish()` releases the keep-alive and its tick;
- `main()` keeps the script alive;
- the installed engine source still states each step above. That part is
  skipped where the engine is not installed, and fails if an engine update
  changes it.

These tests are not proof of a clean exit.

## The controlled runs, once the lane is returned

One job at a time. Each start and end is posted, with PIDs, logs and real
exits.

1. **The probe, handoff** (the fix, with no level or render):
   `UE --editor scripts/unreal/probe_editor_exit.py EDITOR_EXIT_PROBE_DONE Saved/ExitProbe/handoff.log -- mode=handoff`
   - **It passes** when the marker is logged and the editor then exits by
     itself, with a natural EOF.
   - Its status is recorded as it is. Earlier self-quitting full editors
     exited 1, which the wrapper accepts only in `--editor`, reported as
     "editor exit 1, wrapper exit 0". The probe exited 0.
   - **If it is still running 60 s after the marker:** sample it, preserve
     everything, ask before any signal, and stop. The fix would be wrong.
2. **The negative control** (`mode=same_frame_quit`), only if root wants the
   mechanism shown and authorizes, in advance, sampling the editor and then
   SIGKILL.
   - The expected result is the hang, with the v2 and v3 stack.
   - This shows the cause, not the fix.
3. **Capture v4,** with the reviewed capture changes of the time:
   `UE --editor scripts/unreal/render_yumi_fp_review.py YUMI_FP_REVIEW_COMPLETE Saved/YumiFP/capture_v4.log -- holds=... res=1920x1080 out=v4`
   - It passes on the same natural exit as the probe, beside its own gates.
