# Controller input (offline prototype)

The current project keeps Unreal's legacy Action/Axis mappings so the existing keyboard and mouse controls continue to work. The defaults in `Config/DefaultInput.ini` add common gamepad keys supported by Unreal 5.8. They do not alter the Rust combat packet: the character still quantizes the final movement axes, aim angles, and action bits in `ConsumeKernelInput()` at the fixed simulation tick.

| Control | In combat | In menus (the Slate front end) |
| --- | --- | --- |
| Left stick | Move | Move between rows; left and right change an option |
| Right stick | Aim | — |
| Right trigger | Fire | — |
| Left trigger | Block (practice) | — |
| Bottom / right / left / top face buttons | Jump / melee / reload / interact | Choose / back / — / — |
| Left stick click | Sprint | — |
| Right stick click | — | — |
| Left / right shoulder | Ability / next campaign weapon | Change an option |
| D-pad | Main / melee / special weapon (left / down / right) | Move between rows; left and right change an option |
| Menu button | Open the pause menu | Resume from the pause menu |

The left stick uses an 0.18 per-axis dead zone. The right stick uses an 0.12 per-axis dead zone and a 1.4 exponent to allow finer small movements. These are applied to each local `UPlayerInput` in `SetupPlayerInputComponent`, as well as declared in the project input config. The right stick is on separate axes so its turn rates can be multiplied by frame delta; the mouse uses raw mouse delta times the mouse sensitivity. The Controls screen (**設定 → 操作**) sets both dead zones (0–0.5, in steps of 0.02), pad look sensitivity and mouse sensitivity (0.25–3.0, in steps of 0.25) and inverted look, which flips mouse and pad vertical look. They save with the rebound keys to the local `SoraControlsV1` slot (`USoraControlSaveGame`, schema 2; the class default is 0, so the schema is always written, and a save without it or of another schema is discarded for the defaults), so they never touch campaign checkpoints or wallet state.

**Rebinding.** The Controls screen lists every control in `SoraInput::Remappable` (`Source/SoraArena/Public/SoraInputStates.h`): the four movement halves, which take one keyboard key each, and every play-only action (fire, melee, guard, jump, sprint, reload, interact, crouch, sheathe, ability, the three class weapons, the three campaign weapons, next campaign weapon and the practice scoreboard), which take one keyboard-or-mouse key and one pad button. Each row shows both keys. Choose a row with the device to rebind, then press the new key or button; a mouse click on the row rebinds the keyboard-and-mouse slot. Esc or Start cancels, since they stay the pause keys. `ASoraPlayerCharacter::RemapControl` (and `RemapCombatAction` for one action by name) refuses, with the reason shown in the dialog:

- a keyboard key or mouse button that another action or axis can use in the same game state. A key shared only across states that never overlap is allowed, as `check_input_conflicts.py` allows it: pad A can be Reload in play while it stays Enter on title cards and results. Esc, Start and F10 are always refused, because the pause menu and the subtitle switch act in play. Every pad button has a default job (crouch on R3, sheathe on the d-pad's up, the scoreboard on View), so a pad button another rebindable control holds is not refused: the two controls trade buttons, provided neither then shares a button with a third action, and the banner names both (`ESoraRemapResult::Swapped`);
- a button of the other device, and a pad button or mouse button for a movement half;
- a stick direction, an analog axis, Any Key, touch or gestures.

Menu, Enter and Subtitles cannot be rebound, and nothing can be rebound outside a menu. **既定のキーに戻す** (Reset key bindings) asks first, then restores `Config/DefaultInput.ini` and keeps sensitivity, dead zones and inversion. At load the saved layout is replayed as a whole, so a swap (both slots are saved) survives a restart. A saved layout that is malformed or that has a conflict is refused whole: the default keys apply and a warning is logged.

**Hold or toggle.** The Accessibility screen switches guard and sprint between hold and toggle (`USoraSettings`, the `SoraSettings` slot). With toggle, a press raises the guard or starts the sprint and the next press ends it; firing also ends a toggled sprint, which a held sprint blocks. Opening the pause menu or rebinding a key ends both, as releasing the key would.

`GetActionKeys()` and `ControlKey()` report current bindings. The front end's prompts are device-aware: they show pad or keyboard labels for the device the player last used, and the mouse cursor shows only while the mouse or keyboard is in use. In-game key prompts (the chapter title card, the result screen, the ammunition readouts, the examine prompt and the practice notice) name their keys through `SoraUI::ActionKey`, which reads the hero's live mappings on the device last used, so they follow the pad and every rebind, with the English beside the Japanese while subtitles are on.

Menus take no action mappings at all: while a screen is open, the Slate front end holds keyboard and pad focus, so its keys never reach `UPlayerInput`, and held keys are flushed when it opens and closes. The one shared play button is the bottom face button: Jump in play, and Enter on the chapter title card and result screens. Wallet pairing, opening and disconnecting are rows on the front end's wallet screen. No wallet transaction can be triggered by these controller bindings.

The fire trigger is accepted only during active gameplay. Pressing it while the title menu or a defeat screen is open cannot leave a held-fire state that shoots as soon as the player resumes.

Rebinding, conflict refusal, the restart replay, reset, hold and toggle, and the new keys acting in play are covered by `SoraArena.UI.ControlsRemap` and `SoraArena.Input.HoldOrToggle` (see `docs/unreal.md`), with simulated keys only. Before calling this controller feature complete, test on Windows and macOS packaged builds with at least one Xbox-layout controller and one PlayStation-layout controller. Check dead-zone drift, horizontal/vertical aim direction and turn rate at 30/60/120 rendered fps, simultaneous mouse/controller input, menu and practice context changes, rebinding on the real devices, held-button release, Japanese menu readability, and identical canonical replay inputs from equivalent final controls. No real controller has been tested.

The implementation uses [Epic's UE 5.8 input mapping overview](https://dev.epicgames.com/documentation/unreal-engine/input-overview-in-unreal-engine), [the `UPlayerInput` API](https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/Engine/UPlayerInput), [axis properties](https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/Engine/FInputAxisProperties), and [the gamepad key list](https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/InputCore/EKeys).
