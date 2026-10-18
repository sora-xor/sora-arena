# Authored dialogue holds

`SoraInput::Dialogue` uses bit 32. Menu, Card, Play and Result keep their recorded
values. Only the pause menu and subtitle switch act during this state. It does
not pause the world: the director, subtitle cues and audio subsystem continue.

The queue retains each line's originating beat and effective mode. An explicit
line mode overrides its trigger; a null mode inherits the trigger. Consequently
the ambient lines at the end of ch04.b13 restore control even though their
trigger is blocking. Radio and ambient lines do not hold combat. A contiguous
blocking interval releases control at twenty seconds even if dialogue remains;
it does not complete, skip or delete the remaining lines.

Entering and leaving a hold clears the hero's held actions, pending movement,
velocity, jump, interaction work and pressed keys. Character movement components,
horses, projectiles and thrown stones wait during the hold. Combat and fieldcraft already
use `IsPlaying`; the director continues dialogue while suspending task work.
Reset and checkpoint defeat clear the queue and hold.

Dialogue beats enqueue their actual event segments. `lines_done` may enqueue a
new head without shortening or extending its duration. The chapter-one gift
raises `blocking_end` after its authored last blocking line and then plays its
ambient closing line. Completion requires each main line to finish; branch-only
responses are optional. Later volume or interaction lines cannot be consumed by
waiting at the start of the beat.

Run `python3 scripts/unreal/check_input_conflicts.py` for the host binding gate.
The directed Unreal suite is `SoraArena.Campaign.Dialogue`:

- `GiftInputHold`: trigger gating, held input/motion, subtitles, pause, release,
  `blocking_end` and checkpoint reset.
- `AuthoredModes`: the two chapter-two volumes and explicit ambient override.
- `ReentrantSegments`: Iota's crate and Toranosuke's conversation.
- `CombatAndPlaque`: the duel's hold, in-flight projectile, defeat clearing and
  final-plaque event. The final scene must still await its missing main lines.

These are authored tests, not execution evidence until Unreal runs them. The
full campaign route now drives later dialogue volumes and fails explicitly if
required dialogue lacks a tested world interaction. The ch08.b17 sword-return
and plaque-rehang world producers are a separate implementation slice; directed
event injection in the hold test does not qualify those player interactions.
