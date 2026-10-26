# Two-paw grip: anatomy and armour study (measured)

**Status (2026-10-26):** a measured study from the art lane.
- Rounds 1 and 2 (sections 2 and 3), the posed renders of A and B (section 4), and the empty paws and saya carry
  (section 5) are done.
- What is left is root's decisions and the art pass on the paws. Nothing here is an approval.

- **Root's direction:** the original two-paw grip and left-hand closure (`THIRD_PERSON_GRIP_CONTRACT.md` 4.5, 4.7) stay
  binding.
- **What it does:** it measures which changes to the body, the armour, the paws and the pose let the two-paw chūdan
  clear the visible mesh.
- **What it does not do:** nothing here changes the source body or any asset. Each variant is applied in memory, in
  a study run only. Adopting one is root's call and needs its own full build, clearance run and renders.

## 1. Method

**The study runs** are `rig_nyaakoto_runtime.py --study two_paw [--variant ...]`, in Blender 5.2.2.

**Variants** (`nyaakoto_runtime_parts.apply_variant`), applied to the source parts before the arm joints are
measured:

| variant | what changes |
| --- | --- |
| `arm` | each upper arm stretched along its own axis about the shoulder, and each forearm along its axis about the moved elbow. The paw moves with the wrist; the shoulder ball stays rigid. |
| `palm` | the palm scaled about its centre; the grip channel and the curled fingers follow it |
| `chest` | the front half (x > 0) of the haori, kimono, collar, dō, chest kamon and insignia brought toward the body (x scaled about 0) |

A first version moved only the vertices and left the parts' origins behind. The joints are measured from those
origins, so its arm variants are invalid. Their runs are kept as `s73_twopaw_v01-02.invalid_origins_not_moved`.

**Stances:** the two-paw chūdan, blade 30° up, with Grip_L at the contract's (24, 0, 100) and further forward, from
x 28 to x 34. Each is tried with several elbow poles: forward, out, and far forward.

**Checks** (`mesh_clearance`, with the triangle-exact method of the contract's 6.2):
- forearms and paws against the torso and armour;
- the katana against the body (both paws excluded) and against both paws;
- the blade's exact separation from the head (5 cm) and the body (3 cm);
- paw against paw;
- the upper arms, reported only.

**Also measured:**
- each arm's reach, which may not exceed 98 %;
- at the contract's target, how far forward each forearm and paw must move to clear the torso by 5 mm.

## 2. Round 1 (`Saved/W18Rebuild/s75_twopaw_v01-05`): one change at a time

| variant | best stance (Grip_L, elbows) | reach R / L | arm crossings | katana crossings | worst |
| --- | --- | --- | --- | --- | --- |
| today's body | x 30, forward | 0.979 / 0.814 | 2023 | 0 | left palm vs haori; x 32 out of reach |
| arm 1.1 (upper 26.6, fore 22.9 cm) | x 32, forward | 0.919 / 0.754 | 1424 | 0 | left forearm vs haori |
| arm 1.2 (upper 29.1, fore 25.0 cm) | x 32, forward | 0.842 / 0.691 | 1404 | 0 | left forearm vs haori |
| palm 0.8 | x 28, forward | 0.971 / 0.828 | 2096 | 0 | left palm vs haori; x 30 out of reach |
| chest 0.85 | x 30, forward | 0.979 / 0.814 | 1167 | 0 | left kote vs dō plates |

**At the contract's own target** (x 24), on today's body:
- the katana crosses the haori and dō: 945 pairs;
- the arms cross the torso: about 3470 pairs;
- the right forearm and paw clear only 13 cm further forward;
- the left forearm still crosses after a 20 cm shift.

With chest 0.85, the katana clears at x 24, and the shifts needed fall to 14.5 cm (left) and 7.5 cm (right).

**What round 1 shows:**
1. **Moving the grip forward**, x 28-30 instead of 24, clears the katana on every variant.
2. **Longer arms** buy reach, so x 32-34 becomes reachable. Alone they do not clear the arms: the forearms converge
   along the haori's front quadrant.
3. **The chest** is the strongest single lever on the arms' crossings.
4. **The elbow pole matters**: bringing the elbows forward and out removes a further third or more (round 2).

## 3. Round 2 (`Saved/W18Rebuild/s76_twopaw_r2_*`): combinations, elbows forward and out

**Elbow poles** (Blender axes, R and L mirrored):

| name | pole |
| --- | --- |
| forward | (0.3, ±0.3, -1.0) |
| out | (0.4, ±1.0, -0.6) |
| far forward | (1.0, ±0.6, -0.5) |

**Passing configurations:** every gate holds; arms and katana have 0 crossings, 0 contained and 0 ambiguous; the
blade keeps 5 cm from the head and 3 cm from the body by exact separation.

| variant | Grip_L (blade 30°) | elbows | reach R / L | arms' exact gap from torso | kissaki (derived) |
| --- | --- | --- | --- | --- | --- |
| arm 1.1, chest 0.85 | (34, 0, 106) | far forward | 0.950 / 0.771 | 0.37 mm (too tight to adopt) | (113.5, 0, 160.7) |
| arm 1.2, chest 0.85 | (32, 0, 104) | far forward | 0.842 / 0.691 | 4.7 mm | (111.5, 0, 158.7) |
| arm 1.2, chest 0.85 | (34, 0, 106) | out | 0.871 / 0.707 | 1.8 mm | (113.5, 0, 160.7) |
| **arm 1.2, chest 0.85** | **(34, 0, 106)** | **far forward** | **0.871 / 0.707** | **17.1 mm** | **(113.5, 0, 160.7)** |
| arm 1.2, palm 0.8, chest 0.85 | (32, 0, 104) | far forward | 0.857 / 0.709 | 6.9 mm | (111.5, 0, 158.7) |
| arm 1.2, palm 0.8, chest 0.85 | (34, 0, 106) | out | 0.885 / 0.724 | 2.3 mm | (113.5, 0, 160.7) |
| arm 1.2, palm 0.8, chest 0.85 | (34, 0, 106) | far forward | 0.885 / 0.724 | 17.3 mm | (113.5, 0, 160.7) |
| arm 1.2, palm 0.8, chest 0.8 | (30, 0, 102) | far forward | 0.832 / 0.698 | 6.2 mm | (109.5, 0, 156.7) |
| arm 1.2, palm 0.8, chest 0.8 | (32, 0, 104) | out | 0.857 / 0.709 | 2.0 mm | (111.5, 0, 158.7) |
| arm 1.2, palm 0.8, chest 0.8 | (32, 0, 104) | far forward | 0.857 / 0.709 | 17.7 mm | (111.5, 0, 158.7) |
| arm 1.2, palm 0.8, chest 0.8 | (34, 0, 106) | out | 0.885 / 0.724 | 12.4 mm | (113.5, 0, 160.7) |
| **arm 1.2, palm 0.8, chest 0.8** | **(34, 0, 106)** | **far forward** | **0.885 / 0.724** | **no pair within 2 cm** | **(113.5, 0, 160.7)** |

**Closest failures, for scale** (arm 1.2, chest 0.85):
- Grip_L x 30, far forward: 86 pairs, the left forearm against a dō rivet;
- x 32, out: 88 pairs, the left forearm against the dō plates.

**At the contract's target** (24, 0, 100), every variant still fails. The shifts needed fall to 12.5 cm (left) and
6.5 cm (right) on arm 1.2 with chest 0.85.

**So the measured route back to the two-paw chūdan is:**
- the grip about 10 cm further forward than the contract's first estimate (Grip_L x 34 instead of 24), with the
  kissaki at about 161, inside 4.7's 145-165;
- the elbows held forward and out;
- arms 20 % longer: upper arm 29.1 cm and forearm 25.0 cm, against 24.2 and 20.8;
- a chest front 15 % slimmer: the haori, kimono and dō.

That is a change of the character's proportions. Adopting it is root's call, from renders of the posed variant, which
need the lane.

**The palm.** arm 1.1, palm 0.8, chest 0.85 passes nowhere: at best 38 pairs remain, where the left forearm itself
meets the dō. With arm 1.2, a palm of 0.8 widens the best gap only from 17.1 to 17.3 mm. The palm can keep its
size.

**The decision this asks of root:**
- **arm 1.2 with chest 0.85**, the palm unchanged, at Grip_L (34, 0, 106) with the elbows far forward: 17.1 mm of
  margin. The least change that passes with margin.
- **arm 1.2, palm 0.8, chest 0.8**: the widest margins (no pair within 2 cm at x 34). Cost: a smaller paw and a flatter
  chest.

Both need renders of the posed variant before either is proposed for adoption. Adopting one changes the hero's
source body (create_nyaagyu_hero_character.py) and every LOD, kamon placement and validator that depends on it.

**Every run** exited naturally with 0. The round-2 grid's last run ended at 02:54:00Z.

## 4. The posed renders of A and B (runs s91 and s92, 2026-10-26)

Both are posed at Grip_L (34, 0, 106), blade 30° up, elbows far forward. Each is rendered Front, SideRight and
SideLeft at the build's review quality (32 samples, 1100 px), with the measured interim saya socket. Runs:
`--study two_paw --variant ... --stance 34,0,106:far_fwd`. The renders are in `Saved/W18Rebuild/s91_twopaw_A/` and
`s92_twopaw_B/`, and the cropped paws side by side are in `Saved/W18Rebuild/s91_s92_twopaw_AB_paws_sheet.png`.

**The measurements repeat round 2 exactly:**

| | A: arm 1.2, chest 0.85 | B: arm 1.2, palm 0.8, chest 0.8 |
| --- | --- | --- |
| every gate | pass | pass |
| arms' exact gap from the torso | 17.12 mm | no pair within 2 cm |
| katana against the paws | 0 crossings, 1.06 mm | 0 crossings, 1.06 mm |
| reach R / L | 0.871 / 0.707 | 0.885 / 0.724 |
| kissaki (cm) | (113.5, 0, 160.7) | (113.5, 0, 160.7) |
| upper arms against the torso (reported only) | 1,322 pairs, 5 contained | 1,329 pairs, 4 contained |

**My look at the originals** (a study, not an approval):
- Both read as a two-handed chūdan: the paws close on the tsuka in front of the dō, the elbows come forward and
  out, and the kissaki rises well forward of the face. At 1.2× the arms no longer look stunted beside the body.
- A and B are nearly indistinguishable at review distance. B's 0.8 palm puts slightly less paw on the hilt, and its
  flatter chest does not show. B buys clearance margin, not a visible change.
- **The weak point is the paw art, in both.** The curled fingers read as stacked white tubes, ribbed cylinders
  round the tsuka, not a cat's furred paw. They need sculpting and fur before any photoreal claim, whichever variant
  is adopted.
- Not from this study: the pale and dark crossed rods at the upper chest are in every render, today's body too.

**A failed first attempt, kept** (s89).
- Variant A's first render run failed katana_vs_paws: 6,557 crossings against the curled fingers.
- The diagnosis (s90, `--diag-keys`): Blender 5.2's `Object.shape_key_add` started the new empty-fist keys
  (section 5) at value 1.0, not 0. So every pose that never sets them showed both paws as empty fists, moving the
  finger vertices up to 3.14 cm.
- Each key is now set to 0 at creation, with an assert. s89's renders show the defect and are not a review of A.

**For root:** A is the least change that passes with margin. B is the fallback if more clearance is wanted. Either
one changes the hero's source body and everything that depends on it (section 3).

## 5. Natural empty paws and the saya carry (runs s93, s94 and s95)

**The empty fists** (`--study empty_paw`, s93) are two shape keys, PawEmpty_R and PawEmpty_L, on the runtime skin.
- Each is a second curled paw built with the grip's topology around a channel shrunk to 30 % of the grip's, its
  palm side kept on the palm, so the fingers close to a fist instead of ringing an empty 3.3 × 4.3 cm hole.
- The runtime drives them by what each paw holds: both empty in Idle and Walk, the left only in the interim Guard.
- **Results:**
  - Idle, both paws empty: every gate passes;
  - the interim Guard, left paw empty: every gate passes. The arms clear the torso by 14.43 mm, the katana clears
    the holding paw by 1.06 mm, and the left paw clears the saya;
  - reported only: the upper arms against the torso, 936 and 900 pairs (the shoulder ball against the haori).
- My look: the empty paws read as small closed fists. Renders: `Saved/W18Rebuild/s93_empty_paw/`.

**The saya carry** (`--study saya`, s94; with the Guard check, s95). There are 12 candidates at the obi placement
(23, y, 85.5) cm: y -24 or -26.5, the kojiri lowered by a pitch of -10, -15 or -20°, yaw 180 or 188 (swung 8° out).
Each is checked at Idle and four walk phases with both paws empty: the saya and the sheathed hilt against the whole
body, paws included.

| candidate | socket (cm), rotation (deg) | Idle and walk | interim Guard, left paw empty |
| --- | --- | --- | --- |
| 07 | (23, -26.5, 85.5), (-10, 188, 0) | pass | pass |
| 09 | (23, -26.5, 85.5), (-15, 188, 0) | pass | pass |
| **11** | **(23, -26.5, 85.5), (-20, 188, 0)** | **pass** | **pass** |
| the other 9 | y -24, or yaw 180 | fail: up to 1,828 crossings with the body | not checked |

- In Guard every gate passes for all three, and the left paw has no pair within 2 cm of the saya.
- My look: all three are natural carries, the tsuka forward and up and the kojiri down behind, far better than the
  interim horizontal saya. **11 (-20°)** is closest to the classic worn angle.
- Renders: `Saved/W18Rebuild/s95_saya_guard/Saya_{07,09,11}_SideLeft.png` and `_Guard_SideLeft.png`.

**For root:** whether to move `gear_saya_l` (viewmodels.json hero_gear, root's) from the interim (23, -24, 85.5),
(0, 180, 0) to candidate 11. Every check here was on today's body. If A or B is adopted, both studies need re-running
on the adopted body.

**Not done:**
- The runtime build has not been run with the empty-paw shape keys.
- Its FBX export keeps `use_mesh_modifiers` at its default, so whether the export carries the two morph targets is
  unverified. So is their UE import (`import_morph_targets` is in the unrun importer).
- The LODs have no shape keys yet.

Every run's command, pid, times, exit and render hash: `data/character_studies_s89_s95.json`. Every run exited
naturally with 0. s89 failed on its own gate.

## 6. Root's choice and the production revision (2026-10-26 05:15 UTC onward)

Root viewed the A/B, empty-Idle and saya 11 renders and chose **A (arm 1.2, chest 0.85)** as the production rig basis
and **saya 11** as the carry target, asking for a complete character revision rather than another study:
- A in the source, the LODs, the kamon and the rig;
- furred paws instead of tube fingers;
- empty and holding states through the actual FBX and Unreal morph import;
- every final-combination pose and clearance check again, the shoulder overlap reported.

What was built, measured and checked is in `THIRD_PERSON_GRIP_CONTRACT.md` section 7. Every run's record is in
`data/character_revision_runs.json`.

The "Not done" list of section 5 is answered there:
- the runtime build runs with the empty-paw shape keys;
- the FBX carries them, and the validator re-derives every morphed vertex;
- the LODs carry their own;
- Unreal's import is read back through its own FBX export, every LOD.

Two things moved from this study's plan:
- **Saya 11 was measured here on the baseline body with the interim guard.** The production build checks it again on A
  through Idle, the walk, the guard and the strike.
- **The empty fist is no longer a second set of tubes round a shrunk channel.** It is a rule on one paw surface that
  keeps the knuckles where they are.

