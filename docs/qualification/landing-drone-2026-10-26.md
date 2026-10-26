# Chapter 03 landing drone attack — 2026-10-26

The attack described in `docs/campaign/chapter-03.md`, ch03.b02, is implemented and integrated into the isolated release worktree. Eight directed Unreal fixtures pass at signed `005dfb42`. The landing encounter and complete game remain unfinished.

Both landing guards receive a scoped attack with a 900 ms cyan lock, swept descent to a body-centre height of 250 cm above the floor under the committed drone, a 1500 ms seizure and five damage. Leaving the fixed ring or putting solid cover between the net outlet and the hero prevents the hit. A blocked descent aborts without firing. A positive wakizashi melee contact is lethal while this bound drone is physically low; ordinary drones and other weapons retain their damage rules.

The warning and low recovery use active play time. The warning actor survives pause and dialogue, and is removed on release, interruption, defeat or encounter teardown. The normal campaign difficulty policy still scales the 900 ms base mark to 1170 ms on Easy and 765 ms on Hard. The drone owns movement during its attack; perception continues to update.

The chapter does not specify a low dwell or vertical speed. This implementation uses the existing catalog's five-second net recovery as the low exposure window and its 500 cm/s movement speed for descent and ascent. D1 starts on its authored five-metre plane; D2 provisionally uses the same plane. Neither the required D1 figure-eight/40 s loop nor D2 canal-edge/30 s route is implemented by this change: their existing horizontal paths remain. Final net visuals, drone art, ordinary controls through the full beat, difficulty balance and release qualification remain open.

## Evidence and limits

`scripts/unreal/test_landing_drone.py` compiles and executes the production C++ state machine with assertions, warnings as errors and undefined-behavior traps. The local run passed on 2026-10-26. It exercises timing boundaries, all difficulty durations, fractional frame time, arrival gating, a single release, recovery, interruption and the scoped damage predicate. It does not simulate collision or certify the Unreal code.

All 60 CPU gameplay gates pass on signed `a705c7c655af367762ee5bff2040bb9c3ac28132`, tree `e43250ebbfb5a304fc69d14411e49f623ece1fdd`, with clean, unchanged source before and after. The report and every log were rechecked against the signed check inventory. Evidence in the source-validation worktree: `Saved/Qualification/2026-10-26/landing-drone-cpu-attempt1`; review SHA256 `d28879f0ec959a7fbf5d10bae56b899b59d02ebd3813e15f86f9af0b28227675`. The source runner's 15 failure/scope tests also pass. Subsequent code changes affect only the Unreal test fixtures.

The three new Unreal tests pass:

- `SoraArena.Campaign.LandingDrone.TimingAndStrike`: actual campaign binding, mark/pause, swept arrival, damage and root duration, then one mapped wakizashi attack.
- `SoraArena.Campaign.LandingDrone.ObstructionAndReset`: a real shelf blocks descent; stagger and checkpoint retry remove stale warnings.
- `SoraArena.Campaign.LandingDrone.BaitAndGenericIsolation`: leaving the locked ring, full recovery/ascent, and the unchanged generic drone attack.

The same run passes `Campaign.DroneBody`, `Fieldcraft.DroneCrossing`, `Campaign.LedgerPatrols`, `Campaign.HorseShellClockAndImpact` and `Campaign.Playthrough`. The assisted campaign covers eight chapters, 126 required beats, seven optional caches, 28 pickups, seven rides, 120 checkpoints, 61 reloads, 13 phase reloads and 76 worlds.

Exact runtime source: `005dfb4217d9b6d63e95ac334b0eb4df9e65a9e9`; tree `c5157f5b44b76333cb369c4dea4383e86fb35016`. Evidence in the release worktree: `Saved/Qualification/2026-10-26/landing-drone-005dfb4-runtime-attempt1`. Natural editor/wrapper exits are 0/0, all eight tests have zero errors/warnings, twenty evidence files rehash, and source/native/config/generated inputs remain unchanged. Review SHA256: `77647c0c5e8231b39f6c481fff0af1013216be1efe23be732d3231c2d24e594b`.

These are directed NullRHI fixtures with staged poses and unrelated threats held. The complete campaign fixture is assisted. They do not constitute ordinary-input play, visual acceptance, packaged testing or release qualification. Root returned the engine/Blender lane to Claude after natural EOF and process verification.

## Preserved failed attempts

- `d9cdf0ef`: build failed before any test ran because two unqualified test-helper calls named `Freeze` collided with an engine namespace in a unity translation unit. `3830228e` qualifies those two calls. Evidence: `landing-drone-d9cdf0e-runtime-attempt1`; review `1a5aa18c6cc0b148dff7b9be561196900db4655c73a77d8fa4f91a1439a2916f`.
- `3830228e`: build passed; all three new fixtures and four shared fixtures passed, but Playthrough failed its fallen-guard stationary check after only thirty frames. Natural editor/wrapper exits were 3/1, with zero test warnings and unchanged inputs. Evidence: `landing-drone-3830228-runtime-attempt1`; review `1397dea9d58d6beb3bb559318cbb476c8a4ebdc622c484d11122affeadcdfe66`.
- The test-only `005dfb42` fix waits up to 180 additional frames for real ground contact, checking no horizontal patrol drift throughout, then retains a further thirty-frame stationary check. The passing log measures the old thirty-frame instant: start `(9320,-640,500)`, current `(9320,-640,377.5)`, velocity `(0,0,-490)`, falling true. The old assertion observed a legitimate vertical fall. Production movement, collision and defeat behavior were unchanged by this fixture fix.
