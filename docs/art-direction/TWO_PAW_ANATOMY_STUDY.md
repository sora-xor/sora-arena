# Two-paw grip: anatomy and armour study (measured)

**Status (2026-10-26):** a measured study from the art lane, in progress.

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

## 4. Natural empty paws and the saya carry

(prepared, not yet run: empty-fist shape keys PawEmpty_R and PawEmpty_L, and a carry sweep with the kojiri lowered
10-20° and swung out)
