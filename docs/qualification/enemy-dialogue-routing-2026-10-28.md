# Enemy dialogue routing — October 28

An enemy reaction now queues only dialogue authored for that enemy type.
Previously the catalog discarded `ext.source`, so a suspicious marksman,
conscript, enforcer or drone could queue all four notice-square suspicion
lines. Chapter 03 contains 57 source-restricted trigger rows; their data is
unchanged.

The catalog retains and validates these restrictions. The director carries
the enemy archetype through immediate and delayed events and checks it before
consuming a trigger or its cooldown. Unsourced mission events cannot play
restricted guard lines. Generic dialogue, mission events and HUD prompts
retain their existing behavior.

A guard entering Combat directly can now play its authored Alert line;
Alert followed by Combat does not repeat that line. Retreat also matches the
authored `x_ai:withdraw` row. These aliases apply only to restricted dialogue
and do not emit additional mission events or HUD prompts.

## Validation

Signed implementation `c7f1dfe481d99520e625a40bab77bc93c077170b`, tree
`663237311945dd1f8a12429ba180d4b8dcaf5dd5`, passes **18/18** selected native
editor tests with zero selected errors or warnings on M2 Ultra, UE 5.8.3
CL 58210709 and project-scoped Xcode 26.1.1. The run uses NullRHI; it supplies
no rendering, voice-quality or platform-performance evidence.

- Five source cases use actual checkpoint guards and send directed cues
  through the production event bus: marksman, bound conscript, rifle
  enforcer, blade retainer and drone. Each queues its one expected line.
  These synthetic cues do not establish actual AI perception transitions.
- Metadata checks retain the authored restriction and reject malformed,
  empty, duplicate, unknown and incorrectly capitalized sources.
- Context checks cover unsourced events, direct Combat, Alert-to-Combat,
  retreat, Search-to-Unaware, one-shot preservation after a mismatched
  source, and a delayed cue retaining its source. Temporary test rows are
  restored after the isolated world is destroyed.
- Five existing dialogue cases cover input holds, authored modes,
  reentrant segments, combat/plaque dialogue and the blocking limit/reset.
- Four full live notice-square rehearsals retain their normal health,
  active guards, mapped keyboard/controller input, actual work and escape.
  Campaign spaces and the assisted campaign also pass. These remain
  directed tests, not ordinary full-campaign acceptance.

The host campaign validator passes all 133 beats, 1,032 bilingual lines and
937 triggers and rejects 76 malformed variants. Its canonical-case mutant
matches the native regression. The current data has no source-restricted
delayed row; that behavior is covered by the temporary directed test.

## Preserved failures and original evidence

The reproducer at `33973591` failed **5/5** cases: every tested archetype
queued the marksman, conscript, enforcer and drone suspicion lines. The first
fix at `5ed5feef` passed **17/18** cases; the native metadata test caught
Unreal's case-insensitive string comparison accepting `Marksman`. The final
fix uses an explicit case-sensitive comparison. Neither failed run is
reclassified or overwritten.

All three native runs ended naturally. Their independent reviews verify
20 original files each, exact selections, signed source/artifact identity,
and unchanged source, native inputs, Config, Generated and frozen ROOT.
Original build/editor diagnostics remain in the logs; zero selected test
errors/warnings does not describe every startup diagnostic.

Evidence is under isolated SOURCE `Saved/Qualification/2026-10-28/`:

| Review | SHA-256 |
| --- | --- |
| `enemy-dialogue-runtime-33973591-attempt1-review.json` | `c599e4eb3998c5e2ee2df5dc5952eff3b27a5a7bdf3d5c6f293e0ab758adad9b` |
| `enemy-dialogue-runtime-5ed5feef-attempt1-review.json` | `479e104eb846a1eb99057e7de2954adb8a4e50ff325f5e8fbc53678455dfca29` |
| `enemy-dialogue-runtime-c7f1dfe4-attempt1-review.json` | `a7a000d948b1f61d3f15f83255b892f550538bcce8934d8dba2c0a4437f1a92f` |
| `enemy-dialogue-source-c7f1dfe4/review.json` | `f875527065ef982ed0e50cf6a52332c918e6ee534871e86a3f9989209e5fb5d5` |

Correct source routing does not qualify subtitle backlog/telegraph timing,
voice assets, ordinary patrol-cue readability or first-time discoverability.
The narrow rehearsed route timings and retained failures in the
[live encounter record](notice-live-encounter-2026-10-28.md) still apply.
[Final art remains rejected](notice-night-readability-2026-10-28.md).
ROOT stays frozen at `b6ba3c11`, shared master at `610bb975`, and the preserved
package at `1b6dfadc`. No user-game input/restart, new render, image edit,
package, actual-M1, Windows, Nanite or performance result is claimed.
