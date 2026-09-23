# Controller input (offline prototype)

The current project keeps Unreal's legacy Action/Axis mappings so the existing keyboard and mouse controls continue to work. The defaults in `Config/DefaultInput.ini` add common gamepad keys supported by Unreal 5.8. They do not alter the Rust combat packet: the character still quantizes the final movement axes, aim angles, and action bits in `ConsumeKernelInput()` at the fixed simulation tick.

| Control | In combat | In the menu |
| --- | --- | --- |
| Left stick | Move | — |
| Right stick | Aim | — |
| Right trigger | Fire | — |
| Left trigger | Block (practice) | — |
| Bottom / right / left / top face buttons | Jump / melee / reload / interact | Continue / — / — / — |
| Left stick click | Sprint | Start a new campaign |
| Right stick click | — | Start offline practice |
| Left / right shoulder | Ability / — | Previous / next class |
| D-pad left / down / right | Main / melee / special weapon | Practice loadout slot 1 / 2 / 3 |
| D-pad up | — | Next map |
| Menu / View buttons | Open menu / — | Close menu / return to saved campaign |

The left stick uses an 0.18 per-axis dead zone. The right stick uses an 0.12 per-axis dead zone and a 1.4 exponent to allow finer small movements. These are applied to each local `UPlayerInput` in `SetupPlayerInputComponent`, as well as declared in the project input config. The right stick is on separate axes so its turn rates can be multiplied by frame delta; the mouse continues to use raw mouse delta. `SetGamepadDeadZones()` clamps both values to 0–0.5, and `SetGamepadLookSensitivity()` clamps its multiplier to 0.25–3.0. They are Blueprint-callable per-session settings. Inverted look and persistent control profiles are not implemented yet.

`ASoraCharacter::GetActionKeys()` exposes current bindings for a future controls screen. `RemapCombatAction()` changes a named combat action on the local `UPlayerInput` while the game menu is open. It replaces that action's binding for the same device category (gamepad, mouse, or keyboard), rejects collisions and invalid/non-action keys, and leaves wallet/menu/campaign commands untouched. Changes are session-scoped: they are not saved to disk, and there is no in-game capture UI yet. The menu's printed keyboard instructions have not been replaced with device-aware prompts.

The deliberate shared buttons are context-gated: the bottom face button is Jump in play and Continue in the menu; left stick click is Sprint in play and New Campaign in the menu; left shoulder is Ability in play and Previous Class in the menu. The wallet's pairing/open/disconnect actions retain their keyboard-only mappings. No wallet transaction can be triggered by these controller bindings.

Before calling this controller feature complete, test on Windows and macOS packaged builds with at least one Xbox-layout controller and one PlayStation-layout controller. Check dead-zone drift, horizontal/vertical aim direction and turn rate at 30/60/120 rendered fps, simultaneous mouse/controller input, menu and practice context changes, remapping conflict rejection, held-button release, Japanese menu readability, and identical canonical replay inputs from equivalent final controls. This check cannot be performed until the pinned UE 5.8 engine is available.

The implementation uses [Epic's UE 5.8 input mapping overview](https://dev.epicgames.com/documentation/unreal-engine/input-overview-in-unreal-engine), [the `UPlayerInput` API](https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/Engine/UPlayerInput), [axis properties](https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/Engine/FInputAxisProperties), and [the gamepad key list](https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/InputCore/EKeys).
