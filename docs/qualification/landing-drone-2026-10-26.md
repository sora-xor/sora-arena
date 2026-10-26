# Chapter 03 landing drone candidate — 2026-10-26

This is an isolated source candidate for the attack described in `docs/campaign/chapter-03.md`, ch03.b02. It is not an Unreal runtime qualification or completion of the landing encounter.

Both landing guards receive a scoped attack with a 900 ms cyan lock, swept descent to a body-centre height of 250 cm above the floor under the committed drone, a 1500 ms seizure and five damage. Leaving the fixed ring or putting solid cover between the net outlet and the hero prevents the hit. A blocked descent aborts without firing. A positive wakizashi melee contact is lethal while this bound drone is physically low; ordinary drones and other weapons retain their damage rules.

The warning and low recovery use active play time. The warning actor survives pause and dialogue, and is removed on release, interruption, defeat or encounter teardown. The normal campaign difficulty policy still scales the 900 ms base mark to 1170 ms on Easy and 765 ms on Hard. The drone owns movement during its attack; perception continues to update.

The chapter does not specify a low dwell or vertical speed. This implementation uses the existing catalog's five-second net recovery as the low exposure window and its 500 cm/s movement speed for descent and ascent. D1 starts on its authored five-metre plane; D2 provisionally uses the same plane. Neither the required D1 figure-eight/40 s loop nor D2 canal-edge/30 s route is implemented by this change: their existing horizontal paths remain. Final net visuals, drone art, ordinary controls through the full beat, difficulty balance and release qualification remain open.

## Evidence and pending checks

`scripts/unreal/test_landing_drone.py` compiles and executes the production C++ state machine with assertions, warnings as errors and undefined-behavior traps. The local run passed on 2026-10-26. It exercises timing boundaries, all difficulty durations, fractional frame time, arrival gating, a single release, recovery, interruption and the scoped damage predicate. It does not simulate collision or certify the Unreal code.

Three Unreal tests are prepared but **unbuilt and unrun**:

- `SoraArena.Campaign.LandingDrone.TimingAndStrike`: actual campaign binding, mark/pause, swept arrival, damage and root duration, then one mapped wakizashi attack.
- `SoraArena.Campaign.LandingDrone.ObstructionAndReset`: a real shelf blocks descent; stagger and checkpoint retry remove stale warnings.
- `SoraArena.Campaign.LandingDrone.BaitAndGenericIsolation`: leaving the locked ring, full recovery/ascent, and the unchanged generic drone attack.

These are directed fixtures with staged poses and unrelated threats held. They do not constitute an ordinary-input campaign playthrough. Root is keeping the Unreal/Blender lane free for Claude's weapon socket staging and probes; runtime validation follows an explicit lane handback.
