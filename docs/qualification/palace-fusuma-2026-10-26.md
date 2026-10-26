# Palace fusuma implementation checkpoint

The three quiet-room doorway gaps in ch06.b06 now stage solid sliding leaves.
Mapped Interact reverses the selected door, with Japanese and English prompts.
Each 260 cm leaf travels 264 cm along the room side of its existing partition
in one second. The geometry of the rooms, corridor and openings is unchanged.
The leaves occlude sight and block movement while closed. A swept pawn query
stops a moving leaf before it pushes a character and resumes after the path
clears. Pause and defeat stop its clock; retry recreates closed leaves.

Actual motion emits one stealth noise impulse per operation. Its standard
listener radius is the authored 400 cm, with the existing listener sensitivity
and wall occlusion rules. A blocked restart does not repeat that impulse.
This is a gameplay noise event; an audible slide recording is still needed.

The mapped LedgerRoute fixture now opens all three doors while crossing the
quiet rooms. PalaceFusuma checks closed collision/occlusion, actual leaf travel,
pause, occupied-path stop/resume and checkpoint reset. These fixtures hold the
other guards to isolate interaction and collision; ordinary stealth play is a
separate acceptance gate.

Validation at this checkpoint: all 59 CPU gameplay gates passed against the
unchanged working inputs, including localized resources and 400/401 cm open
and 200/201 cm occluded noise boundaries. The patch and new source file were
frozen with the raw logs at `Saved/Qualification/2026-10-26/fusuma-working-source-attempt1`
and its adjacent `-inputs` folder in the complete-game worktree.

No Unreal build or runtime test has run for this change. The visible slabs are
functional placeholders, not fitted fusuma craft or final art. Sliding sound,
ordinary stealth difficulty, alarm shutter/reinforcements and access to the
authored 20 cm silent edge strip remain open.
