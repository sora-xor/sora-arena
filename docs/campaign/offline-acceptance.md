# Offline campaign progression acceptance

Run `python3 scripts/unreal/test_campaign_progression.py` from the repository root. It reads the eight authored chapters from `Content/Data/catalog.json`, generates a temporary C++ fixture, and compiles `campaign_progression_driver.cpp` against `SoraCampaignRules.h`. The same rules header gates checkpoints, defeats, production-site interactions, final-boss admission, exits, chapter advance, and liberation in `ASoraGameMode`.

The host driver walks every chapter's defeat count and three production sites. At each milestone it tests prerequisite and defeat gates, copies and validates the local checkpoint value, rejects premature completion and malformed checkpoints, then advances to the next chapter. Chapter one additionally uses `SoraDojoRules.h`: stance must be held for 600 ms, a front-facing guard must survive a pupil strike after 350 ms, a fresh front-facing parry must land within 260 ms of pressing defense, and a wooden-sword swing must complete its recovery before a pupil can be scored. The first training site retains its cataloged zero-bout availability. The driver rejects out-of-order, short, late, backwards, and forged lesson progress, including a checkpoint with bouts before training. The checkpoint mask is stored in `USoraSaveGame` schema 5 and validated before restoration. In the eighth chapter the driver requires the collector spawn gate at 17 of 18 defeats and liberation only after the final site and exit. The Python side checks that every authored Japanese dialogue cue and speaker has a nonempty English counterpart; it does not test subtitle rendering or voice.

This is a **rules and content acceptance test**, not a completed Unreal campaign run. It does not instantiate `UWorld`, call `ASoraWorldBuilder::ActivateNearest`, serialize `USoraSaveGame` with `SaveGameToSlot`, exercise the pupil telegraph/collision and player input, render HUD subtitles, or measure mission duration. The project Mac editor target compiled in an isolated UE 5.8.3 diagnostic worktree; the exact 5.8.2 release editor/runtime is not installed. An in-engine follow-up must script stance, guard, parry, recovery, actual site interaction and enemy defeat, save-slot teardown/reload at chapter and boss milestones, then verify the final liberation state and bilingual HUD cues. Combat readability, 6–8 hour pacing, cinematics, and visual quality require separate playtests and performance captures.

The `SoraArena.Campaign.SaveRoundTrip` Unreal automation case is now in source.
It passed in the isolated UE 5.8.3 Mac editor diagnostic on 2026-09-23:
`USoraSaveGame` serialized to memory and restored the chapter, dojo lesson mask,
production-site mask, defeated-pupil count, completion and English-subtitle
settings. The separate `SoraArena.Campaign.DiskSaveRecovery` automation also
passed in the same 5.8.3 diagnostic. It wrote and reloaded four unique-slot
checkpoint cases (dojo, production sites, pre-boss and completed campaign),
checked subtitle settings and all stored fields, and deleted its test slot.
Neither test tears down and reloads a played world or verifies live chapter
recovery and HUD behavior.
