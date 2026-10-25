"""Probe how a full editor running a multi-frame -ExecutePythonScript exits, with no level, render or asset.

Run (UE 5.8, full editor, by the holder of the engine lane):
  scripts/toolchain/run-editor-script.sh --editor scripts/unreal/probe_editor_exit.py EDITOR_EXIT_PROBE_DONE \
      Saved/ExitProbe/<mode>.log -- mode=handoff|same_frame_quit [frames=60]

This is the shape of render_yumi_fp_review.py's run, without its work:
keep the script alive, tick a Slate post-tick callback for ``frames``
frames, log the marker, then end in one of two ways.

- **handoff** (the fix): release the keep-alive only. EditorPythonExecuter's
  next tick then completes its "Executing Python Script..." notification
  while the engine still ticks, and defers QUIT_EDITOR a frame.
- **same_frame_quit** (the negative control): release the keep-alive and call
  quit_editor in the same tick, as captures v2 and v3 did. Expected to hang
  in teardown, as they did. Run it only with authorization to sample the
  editor and then end it.

What the run records is the evidence: the wrapper's EDITOR_EXIT and its own
exit, and whether the editor exited by itself with a natural EOF. Nothing
here forces an exit or hides one. docs/art-direction/EDITOR_EXIT_HANG.md has
the plan.
"""
import sys

import unreal

MODES = ("handoff", "same_frame_quit")


def parse(argv):
    opts = {"mode": "handoff", "frames": "60"}
    for a in argv:
        if "=" in a:
            k, v = a.split("=", 1)
            opts[k] = v
    if opts["mode"] not in MODES:
        raise RuntimeError(f"editor exit probe: mode {opts['mode']!r} is not one of {MODES}")
    return opts["mode"], int(opts["frames"])


def main():
    mode, frames = parse(sys.argv[1:])
    state = {"frames": 0}

    def tick(delta):
        state["frames"] += 1
        if state["frames"] < frames:
            return
        unreal.unregister_slate_post_tick_callback(handle)
        unreal.log(f"EDITOR_EXIT_PROBE_DONE mode={mode} frames={state['frames']}")
        unreal.EditorPythonScripting.set_keep_python_script_alive(False)
        if mode == "same_frame_quit":
            unreal.SystemLibrary.quit_editor()          # the negative control: captures v2 and v3's ending

    handle = unreal.register_slate_post_tick_callback(tick)
    unreal.EditorPythonScripting.set_keep_python_script_alive(True)


main()
