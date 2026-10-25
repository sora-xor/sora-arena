# Third-person weapon grip contract (characters on SK_NyaagyuSamurai)

**Status (2026-10-25):** a measured contract from the art lane, for root to
bind. It covers:
- what the characters' rig, paws and weapons are today, measured from their
  files;
- what the assets must become, and which side builds each part;
- the checks that decide each part.

Root asked for it after the archive reveal's floating katana (root's notes of
23:08 and 23:43 UTC). It covers every world-visible character on the hero's
rig: Toranosuke (at 1.08), companions, dojo pupils, local-body enemies and
villagers. First person keeps its own contract
(`FIRST_PERSON_VIEWMODEL_CONTRACT.md`).

**The evidence** is in `Saved/W18Rebuild/s60_grip_contract/` (read-only):
- `sk_nyaagyusamurai_measure.json`;
- `arms_weapons_measure.json`;
- `arm_fit_measure.json`.

The scripts that wrote them are kept beside them. The diagram is
`data/third_person_rig_fit.png`.

## 1. Frames and units (measured)

All positions here are **Unreal component (mesh) space, centimetres:**
+X forward, +Y the character's right, +Z up, the feet at 0. The capsule adds
-88 in Z: the mesh is at (0, 0, -88) in it (SoraCharacterBase.cpp:151).

**How the files map** (each mapping checked against two independent records):
- **The bones** (SK_NyaagyuSamurai.fbx, `ead9d602…`) match
  rig_nyaakoto_runtime.py's Blender metres turned 180° about Z, times 100.
- **Unreal** imports these Blender (-Y forward, Z up) FBXs as 100 x (x, -y, z)
  of Blender metres. That is `yumi_fp_raster.COMPONENT`, validated against
  the first-person captures' ID passes (paw IoU 0.951).
- **So Unreal = (-x, y, z) of the FBX's global frame.** The authored W00
  katana's sockets, read this way, equal its build record exactly: Grip_L
  -14.242, Muzzle (81.973, 0, 7.59).
- **The mesh's vertices** are model-local, with the model at Lcl Scaling 85,
  Lcl Rotation (0, 0, 180) and Lcl Translation (-0.6, 0, 24.3).

## 2. What the rig is today (measured)

**The bones** (bind heads, Unreal cm): 20 of them, no sockets, idle and walk
only.

| bone | head | bone | head |
| --- | --- | --- | --- |
| pelvis | (0, 0, 65) | spine | (0, 0, 85) |
| neck | (0, 0, 119) | head | (0, 0, 139) |
| upperarm_L | (0, 23, 124) | upperarm_R | (0, -23, 124) |
| forearm_L | (3.5, 34, 101) | forearm_R | (3.5, -34, 101) |
| hand_L | (8.5, 38, 83) | hand_R | (8.5, -38, 83) |

**The sides are mirrored.** The bones named `_L` sit at +Y, the character's
right; `_R` at -Y, its left. Two things confirm it:
- in Blender, with +X forward and +Z up, +Y is the left, and the generator
  puts the `_R` chain at +Y Blender;
- the saya it calls "left hip" (y -0.31 m in Blender) imports on the right.

The planned gear sockets in `viewmodels.json` already use the right
convention: gear_saya_l at (17, -25, 95), on the left.

**The arms' mesh is not on its bones.** Each joint below is where the mesh's
adjacent segments meet:

| joint | where the mesh has it (left arm; the right mirrors it) | where the bone has it | apart |
| --- | --- | --- | --- |
| shoulder | (-0.1, -25.9, 121.2) | upperarm_R head (0, -23, 124) | 4.0 cm |
| elbow | (6.5, -41.5, 108.4) | forearm_R head (3.5, -34, 101) | 10.9 cm |
| wrist | (9.2, -48.1, 89.6) | hand_R head (8.5, -38, 83) | 12.1 cm |
| paw centre | (12.5, -47.2, 79.1) | - | - |

- **The forearm mesh** runs parallel to its bone (4.4-4.7° apart), offset
  11.6-12.2 cm outboard.
- **The upper arm** (sleeve and sode) is 45° off its bone.
- **The mesh's segments:** upper arm 21.2 cm, forearm 20.2 cm, wrist to paw
  centre 11.0 cm.
- The bones were inherited from the old prototype cat (the search's note).

Any pose on these bones swings each segment about an axis 11-12 cm off it,
so a grip pose cannot be authored on the current bind.

**The paws are open:**
- each is rigidly skinned to its hand bone, 20.2 x 13.6 x 9.5 cm along its
  principal axes;
- its four fingers hang straight, 3.3 cm apart (create_nyaagyu_hero_character.py:667-673).

There is nothing a hilt can sit in.

## 3. What the weapons are today (measured)

| asset | origin | sockets | extent (Unreal cm) |
| --- | --- | --- | --- |
| SM_Weapon_00 (the box NPCs carry) | the front of the grip | none | x -25 to 83, y +-6.5, z +-7.5; drawn at x 0.75 |
| W00 katana (authored, not imported) | Grip_R, the right paw's hold | Grip_R (0, 0, 0), Grip_L (-14.242, 0, 0), Muzzle (81.973, 0, 7.59) | x -18.99 to 81.97, 100.97 mounted |
| W00 saya | Koiguchi (0, 0, 0) | Kurikata (10.546, 1.214, -1.47) | 78.4 long |
| W10 tantō (Toranosuke's pledge, b10) | Grip_R | Grip_L (-4.406, 0, 0), Muzzle (29.124, 0, 0.84) | x -6.6 to 29.1 |

**W00's grip (tsuka)** is an oval, 3.12 cm across (Y) and 4.05 cm deep (Z),
from the kashira at -18.99 to the fuchi at +5.5. Its edge faces -Z.

**Where the weapon hangs today:**
- **The NPC weapon root** is the Eye (4, 0, 64 in the capsule) plus
  (40, 18, -18), at zero rotation. That is (44, 18, 134) in mesh space: chest
  height, 18 cm right, while the paws hang at z 71-93 and 39-55 cm out.
- **Campaign NPCs** never re-pose it (SoraViewmodelComponent.cpp:202-204, only
  from practice; pinned by SoraViewmodelPresentationAutomation.cpp:120-128).

## 4. The contract

**Names.** Sides are anatomical: `_r` is the character's right (+Y). Sockets
are named by what holds them.

### 4.1 The rig (art lane)

**Kept:**
- the 20 bones and their hierarchy;
- the names Idle and Walk key, with their channels;
- the pelvis and spine bind, so the planned gear sockets keep their meaning.

**Changed: the arm chain's bind positions only**, fitted to the mesh. Each
bind head is within 1.5 cm of the measured joint:

| bone (right arm; the left mirrors Y) | head | tail |
| --- | --- | --- |
| upperarm | the shoulder (-0.1, 25.9, 121.2) | the elbow (6.5, 41.5, 108.4) |
| forearm | the elbow | the wrist (9.2, 48.1, 89.6) |
| hand | the wrist | the paw centre (12.5, 47.2, 79.1) |

**The side labels:**
- **recommended:** correct them in the same rebuild (`_L` to the character's
  left). No source code reads these bones (the search's note).
- **fallback**, if root keeps the names: the sockets of 4.3 carry the
  anatomical meaning, and their bone names are written in the data.

**The animations:** Idle and Walk are regenerated by the rig script with the
same keys.

**The check** (CPU, at build): each arm segment's skinned vertices lie along
its bone. The centroid is within 3 cm of the bone line, and the principal
axis within 15° for the forearm and hand.

### 4.2 The paws (art lane)

**The shape:** closed around a grip channel, an oval 3.3 x 4.3 cm (W00's
tsuka with 0.1 cm clearance), whose axis runs across the paw's breadth.

**The fit:**
- the paw's breadth along the channel is at most 11.0 cm, so two paws fit
  W00's 14.24 cm between Grip_R and Grip_L with 3.2 cm between them;
- the right paw stays behind the fuchi (+5.5);
- the left paw overhangs the kashira by at most 1 cm.

**The check** (CPU): the channel's axis, centre and size, measured from the
mesh. No paw vertex lies inside the channel; the ones ringing it lie within
0.3 cm of its surface.

### 4.3 Sockets (art lane: the import)

**hand_r_grip** and **hand_l_grip**, on the hand bones:
- **position:** the channel's centre;
- **+X:** along the channel, from the little-finger side to the thumb side,
  which is toward the blade for both paws in a two-handed grip;
- **+Z:** to the back of the paw (the mune side), so the edge (-Z) faces the
  fingertips, as the weapons' convention has it.

**The gear sockets:** gear_saya_l, gear_wakizashi_l, gear_ebira and
gear_yumi_slung, as `viewmodels.json` plans them. They are checked against
this mesh: the obi at z of about 97, the hip's front at x of about 17.

**The check** (in the editor, at import): each socket's component transform
is read back, within 0.1 cm and 0.5° of the build record.

### 4.4 The weapons (art lane: the import)

- **What is imported:** the authored W00 katana and saya, and the W10 tantō
  and saya, with their SOCKET_ empties.
- **Where:** their own namespace, `/Game/Generated/Weapons/Runtime/`.
- **Their scale** is **1.0** in third person, the authored size, which the
  paws' 11 cm fit is set for. 0.75 is first person's.
- SM_Weapon_00 stays for anything not yet covered.

### 4.5 The poses (art lane)

The poses are solved on the re-fitted chains by two-bone IK in the rig
script, and keyed as animations. A target out of reach fails the build.

**The reach envelope** (measured):
- the shoulder at z 121, and the reach to a grip about 49 cm;
- the head fills x -12 to 25 in front of z 147-183.

So the overhead jōdan raise cannot be built. The strike is a compact,
kendō-style raise in front of the face.

**Targets for one stance, in mesh cm.** The left paw is on Grip_L, the right
on Grip_R. The blade's elevation is its +X above horizontal.

| pose | Grip_L | blade elevation | Grip_R (derived) | kissaki (derived) |
| --- | --- | --- | --- | --- |
| guard, chūdan | (24, 0, 100) | 30° | (36.3, 0, 107.1) | (103.5, 0, 154.7) |
| raise (furikaburi, small) | (30, 0, 128) | 80° | (32.5, 0, 142.0) | (39.3, 0, 224) |
| cut end (the hit) | (22, 0, 108) | -5° | (36.2, 0, 106.8) | (118, 0, 107) |

**The animations:**
- **A_NyaagyuSamurai_Guard:** a 4 s loop of the guard with a breath, at most
  1.5 cm of travel.
- **A_NyaagyuSamurai_StrikeMakko:** normalised to 1.0 s:
  - guard to the raise at 0.40;
  - the cut at 0.40-0.55, the hit at 0.55;
  - the follow-through to 0.70;
  - recovery to the guard at 1.0.

  The runtime stretches it to the attack's telegraph.
- **The sheathed carry:** Idle and Walk, the katana in its saya at
  gear_saya_l.

**The checks** (CPU, at build, on the solved poses):
- each paw's grip socket within 1.0 cm of its target;
- the blade's segment, from the habaki to the kissaki, at least 5 cm from
  the head's mesh and 3 cm from the body's;
- the right arm's reach at most 98 % of its length, so no pose locks the
  elbow.

### 4.6 The runtime (root)

- **World-visible characters** with a skeletal body attach their held weapon
  to `hand_r_grip`, with SnapToTarget at scale 1.0, so the weapon's Grip_R is
  the socket. They no longer attach it to WeaponRoot.
- **First person and the practice kernel** keep WeaponRoot and its pinned
  test.
- **The states:**
  - out of combat: Idle and Walk, the katana in its saya at gear_saya_l;
  - in a stance: Guard;
  - an attack: StrikeMakko, timed to the telegraph.

  Draw and sheathe come in the second slice. Until then, the switch happens
  off-camera or on a cut.
- **The archive reveal** uses Guard for Toranosuke in 01, 05 and 06.

### 4.7 The in-engine checks (root's fixture, measured each run)

- **The grip:**
  - in Guard, `hand_l_grip` within 1.5 cm of the weapon's Grip_L, the
    two-paw closure;
  - Grip_R on `hand_r_grip` within 0.1 cm.
- **The stance:**
  - the blade's elevation 25-35° in Guard;
  - the kissaki between z 145 and 165 (times the actor's scale);
  - within ±10 cm of the actor's centreline.
- **The sheathed carry:** the saya's Koiguchi within 0.5 cm of gear_saya_l.
- **Clearance:** no blade or saya vertex inside the body's capsule, sampled
  at Guard and at the strike's raise and hit.
- **Captures:** a side and a front view of each pose, for the art review.

## 5. The slices

**Slice A (this art lane, now):**
- 4.1: the rig re-fit and labels, with Idle and Walk regenerated;
- 4.2: the closed paws;
- 4.3: the sockets at import;
- 4.4: W00 and its saya imported;
- 4.5: the guard pose and its CPU checks;
- an in-editor readback of the sockets and the guard.

The rebuilt body also leaves out the built-in Saya_, Sageo_, Katana_, Ebira_,
Ya_ and Yumi_ parts, as `viewmodels.json` plans. Its gear moves to the
sockets.

**Slice B:**
- StrikeMakko;
- the W10 tantō;
- draw and sheathe.

**Root binds 4.6 and 4.7** after slice A's review.

**Not here:**
- finger bones, IK at runtime, cloth;
- Toranosuke's own body (he stays the hero's mesh at 1.08);
- the horse riders.
