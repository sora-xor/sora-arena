# Front-end input diagnostic

For the next full packaged run, set `SORA_TRACE_FRONTEND_INPUT=1` when invoking
`scripts/toolchain/test-packaged-mac.sh`. The wrapper accepts only `0` or `1`
(default `0`) and adds `-SoraTraceFrontEndInput` only to the automation-suite
launch. Its separate fresh-startup process and assertions are unchanged.
Direct game launches can pass the same switch. The diagnostic is compiled only
with `WITH_DEV_AUTOMATION_TESTS`.

`SORA_FRONTEND_INPUT` records the first eight **Title → Main** transitions on an
actual game viewport, before the menu stack changes. Viewportless test worlds
are excluded. Each entry includes the synchronous route, key/button name and
repeat state, command number, incoming menu/focus/device state, world and model
paths, and current automation test (or `<none>`). Command values use
`SoraUI::ECommand`; Accept is `5` and Start is `7`.

Routes distinguish `slate-key`, `slate-button` (title background),
`slate-prompt-button` (the Begin prompt), `model-key`, `direct-command`, and
`direct-show-main`. A Slate route alone does **not** establish physical input:
automation can inject Slate events. Up to sixteen `SORA_FRONTEND_INPUT_STACK`
entries per transition provide bounded program counters and available symbols
to distinguish those callers. Stripped/missing symbols may limit attribution.
The whole diagnostic emits at most 136 lines per process, with bounded symbol
names; it does not log ordinary navigation, releases or pointer motion.

Scopes unwind on early returns, preserve the outer input route through nested
model calls, and are restricted to the game thread. A logging guard and the
transition limit are set before symbol lookup or output. No input is consumed,
no state/focus is reset, and no error is suppressed. The rendered menu tour
still records its incoming screen before establishing its navigation fixture.

The original `b4a02d1` full-run evidence shows Main before the tour's first
Enter, then Chapter select, while the same package's isolated tour passed.
That establishes a navigation offset, not which earlier input or test caused
it. Keep that historical failure and the untouched startup result separate
from any new diagnostic run. These traces are evidence to locate a transition,
not a replacement for either qualification gate.
