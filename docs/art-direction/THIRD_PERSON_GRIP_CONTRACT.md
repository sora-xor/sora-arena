# Third-person weapon grip contract (characters on SK_NyaagyuSamurai)

**Status (2026-10-25):** a measured contract from the art lane, for root to
bind. It covers:
- what the characters' rig, paws and weapons are today, measured from their
  files;
- what the assets must become, and which side builds each part;
- the checks that decide each part.

**Amended (2026-10-26):**
- Slice A is built and checked in Blender (section 6).
- The guard is an interim one-paw pose. The two-paw grip and the left paw's closure stay open.
- 4.7's capsule test is withdrawn for the visible-mesh test of 6.2.
- Where section 6 differs from section 4, section 6 is what the build does, and why.

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

**As built (6.1):**
- The joints are the authored joint parts' own: Shoulder_joint's centre, and Fur_forearm's two ends.
- They lie 1.7–6.6 cm from this table's estimates, and the forearm centroid sits 4.4–4.8 cm off its bone because of
  the kote. So both checks above fail as written.
- 6.1 gives the check the build runs instead.

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

**As built (6.1):**
- No paw vertex lies inside the channel, and the breadth is 11.0 cm.
- A triangle check finds the W00 tsuka 1.06 mm clear of the paw.
- The vertex check alone had missed the palm cutting into the tsuka.

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

**As built (6.1):** the planned gear_saya_l fails on the visible mesh. The build uses a measured one, (23, -24, 85.5).

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

**As built (6.1, 6.4):** the guard is an interim one-paw pose. This two-paw target fails on the visible mesh.

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
- **Clearance (withdrawn, 2026-10-26):** ~~no blade or saya vertex inside the body's capsule, sampled at Guard and at
  the strike's raise and hit~~.
  - Hip gear lies inside a movement capsule by design. Root's note: gear_saya_l is at a radius of 30.2 cm, against a
    34 cm capsule.
  - The capsule is not a test of what is seen. The fixture uses the visible-mesh method of 6.2, or reads its results
    from the build record.
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

**As built (6.1):**
- Only the sword set leaves the body.
- The bow, quiver and arrows stay until their gear assets exist. Removing them would drop four of the 23 slots.
- That socket migration stays open.

**Slice B:**
- StrikeMakko;
- the W10 tantō;
- draw and sheathe.

**Root binds 4.6 and 4.7** after slice A's review.

**Not here:**
- finger bones, IK at runtime, cloth;
- Toranosuke's own body (he stays the hero's mesh at 1.08);
- the horse riders.

## 6. Slice A as built (measured, 2026-10-26)

**Status:**
- Built and checked in Blender 5.2.2 by `rig_nyaakoto_runtime.py`, its LODs by `generate_nyaakoto_lods.py`.
- Both validators pass.
- Not yet imported into Unreal. `scripts/unreal/import_nyaakoto_third_person.py` is written and has not run.
- No photoreal, gameplay or root acceptance.

**The evidence** is in `Saved/W18Rebuild/`:
- `s62_sliceA_explore` and `s63_sliceA_explore_v2`: the explorations;
- `s64_sliceA_build`, `s65_sliceA_lods`, `s66_validate_runtime_skin`, `s67_validate_lods`: the final run;
- their `.attempt*` logs.

Failed and superseded outputs are kept in `Saved/NyaakotoRuntime/Archive/`, each with a hash ledger:
- `pre_sliceA`: the originals;
- `sliceA_attempt0_added_parts_removed`;
- `sliceA_attempt1_channel16`;
- `sliceA_attempt2_checker_e70fc043`.

The record is `runtime_skin_manifest.json` "third_person".

### 6.1 What the build does differently from section 4

**The arm joints (4.1)** are the authored joint parts:
- the shoulder at Shoulder_joint's centre;
- the elbow and wrist at Fur_forearm's two ends;
- the hand running to the grip channel.

Every bone head and tail lies on its part's measurement: 0.0 cm, checked at build.

The table in 4.1 was estimated from where the old vertex clusters' axes meet. It differs from these parts:

| joint | apart |
| --- | --- |
| shoulder | 6.6 cm |
| elbow | 4.1 cm |
| wrist | 1.7 cm |
| paw centre | 6.0 cm |

The segment centroids are recorded but not gated:
- upper arm: 7.5 cm off its bone, at 42°;
- forearm: 4.4–4.8 cm off, 2–5°. The bone runs along the fur cone's own axis; the offset is the kote's mass;
- hand: 0.3 cm off, 7°.

**The paw (4.2)** closes round the channel with:
- the channel's palm side 0.5 mm clear of the palm;
- the curled fingers and thumb 0.2 mm outside it along its normal.

Two earlier geometries are kept as evidence:
- The first had the channel sunk 3 mm into the palm. The palm's triangles crossed the W00 tsuka in 28 pairs, though no palm vertex lay inside the channel. That is the vertex check's blind spot.
- The second grew the channel's semi-axes instead of offsetting along its normal. 16 finger vertices a paw sat about 0.1 mm inside it.

Now no paw vertex lies inside the channel, the breadth is 11.0 cm, and the tsuka is 1.06 mm clear of the paw by exact separation.

**gear_saya_l (4.3)** is measured.

The plan, (17, -25, 95) at (0, 180, 0), sits above the obi:
- the saya crosses the haori's skirt and, walking, the tail: up to 1238 visible triangle pairs;
- its hilt crosses the dō's lowest plate.

At the obi's height the saya passes through the obi, its intended tuck. With the koiguchi at x 17 or 21, the tsuba is buried in the obi or the sash band, whose front face is at 21.3.

The build uses (23, -24, 85.5), with the plan's rotation:
- there are no visible crossings at rest and through the walk;
- the neighbouring placements, 1.5 cm out and 1 cm up, also pass;
- the plan's edge-down rotation keeps the authored kurikata on the outer face.

Sheathed, Grip_R sits 6.32 cm behind the Koiguchi along the saya: the front seppa's face, where 64 katana vertices lie. `viewmodels.json` is unchanged; adopting the socket is root's call.

**The guard (4.5)** is an interim one-paw (katate) chūdan:
- Grip_R at (40, 18, 110);
- the blade 30° up and turned 15° in, so the kissaki is near the centreline;
- the elbow out;
- the left paw at the hip, at (20, -34, 92).

It was chosen from `s61_guard_explore.run*` and `s63`, where the contract's first target is kept with its measurements. It does not close the two-paw grip or the left-hand closure (6.4).

**The body (5)** leaves out only the sword set: 41 parts, with the open fingers and thumb. The bow, quiver and arrows stay. Their four slots are M_Hero_BambooArrowShaft, M_Hero_RedArrowFletch, M_Hero_YumiLaminatedBamboo and M_Hero_YumiSilkString. Removing the parts would drop the slots that the PBR manifest and the Unreal binding hold. That socket migration stays open.

**The LODs** carry LOD0's body through the shared part rules (`nyaakoto_runtime_parts.py`). Each LOD is checked against LOD0's bounds, not the editable source's. The LOD generator had kept the mirrored side labels, the sword set and the open paws.

### 6.2 The clearance method (`scripts/art/mesh_clearance.py`)

It runs on the posed, evaluated visible mesh, and on the authored W00 katana and saya meshes placed at their sockets.

**Crossings:**
- Blender's `BVHTree.overlap` runs `isect_tri_tri` on each candidate pair. The CPU reference tests every pair.
- Coplanar pairs are handled apart. Every pair within 1e-7 m that the backend did not report is tested for a coplanar overlap of positive area, which counts as a crossing.
- Calibration shows why: Blender's overlap does not report a coplanar overlap.
- Pairs that only touch (an edge or a vertex) are counted as touching.

**Allowed and hidden crossings:**
- A saya's crossings with the obi's own parts are its tuck, counted as allowed.
- A crossing counts as hidden only if its whole intersection segment lies inside one closed obi island. Both ends must be inside by ray parity, and no triangle of the island may cross the segment. That holds for non-convex volumes.
- Anything less certain counts as visible, and so does every coplanar overlap.
- An island sealed inside an allowed part counts as allowed containment.

**Containment:**
- With no crossing between them, a connected island is wholly inside or wholly outside each closed island of the other set.
- So one vertex per island decides it: ray parity along two directions, against each closed island whose bounds hold it.
- Directions that disagree count as ambiguous.
- Open islands cannot be decided and are counted. The body has 32,737 of them, its fur cards.

**Separation:**
- The exact least distance, up to a limit: every pair whose bounds come within it, by the least of its 6 vertex-face and 9 edge-edge closest-point distances, or 0 if they cross.
- No pair within the limit certifies "at least the limit". The 5 cm and 3 cm minimums are certified this way.
- A least vertex-to-surface distance is only an upper bound, so it certifies nothing and is not used.

**Calibration** runs in every build on the backend in use. Each case is checked against its expected value:
- a crossing pair;
- a tetrahedron in a cube;
- two cubes 2 cm apart: 0.02 m;
- two bars whose edges pass 5 mm apart, their nearest vertices 27 cm apart: 0.005 m, edge-edge;
- a rod through a box inside a hide volume;
- root's two probes. A 1.6 m crossing with only its midpoint in a 10 cm hide cube must be visible; it is. A coplanar overlap must fail; it does.

**CPU tests:** `test_mesh_clearance` 21 run: 21 passed. They include an L-shaped hide volume whose notch a crossing passes through.

**The movement capsule is not used for any gear.**

### 6.3 The build's checks, on the final run

The build keys every clip and checks it before anything is written. A failing gate exits 1 and writes nothing.

It checks 11 frames: Guard 1, 25, 49, 73 (the breath), Idle 1, 49, Walk 1, 9, 17, 25, and the rest pose. Every gate passed.

| check | sets | gate | result |
| --- | --- | --- | --- |
| forearms and paws against the torso | forearm_R/L, hand_R/L against spine and pelvis parts | no crossing, containment or ambiguity | 0, 0, 0; exact separation 1.32-1.56 cm in Guard |
| katana against the body | W00 katana against everything but the holding paw | 0, 0, 0 | 0, 0, 0; nothing within 2 cm |
| katana against the holding paw | W00 katana against hand_R | 0, 0, 0 | 0, 0, 0; 1.06 mm |
| blade against the head | habaki to kissaki against head and neck | at least 5 cm, exact | no pair within 5 cm |
| blade against the body | habaki to kissaki against the body but head and holding paw | at least 3 cm, exact | no pair within 3 cm |
| left paw against the saya | forearm_L and hand_L against W00 saya | 0, 0, 0 | 0, 0, 0; nothing within 2 cm |
| saya against the body | W00 saya at gear_saya_l against all of the body; the obi is its tuck and hide | no visible crossing, containment or ambiguity | 0 visible; 1785-1902 hidden, 504 tuck; 6 islands sealed in the obi; 1 touching pair at 2 frames |
| sheathed hilt against the body | the hilt behind the Koiguchi (Idle, Walk), with no tuck | 0, 0, 0 | 0, 0, 0 |
| upper arms against the torso | reported only | — | 898-936 visible pairs: Shoulder_joint and the sleeves meet the haori at rest too |

**Also at build:**
- the grip sockets lie exactly on their targets at the keyed guard frames;
- the channel: 0 vertices inside, 11.0 cm;
- the arm joints: 0.0 cm from their parts.

**In the validators:**
- **The Guard FBX round trip** re-derives hand_r_grip and hand_l_grip from the FBX's own bones on all 97 frames. They stay within 0.301 cm and 0.015° of the stance's targets, against a 1 cm and 2° bound. The 3 mm is the keyed curves smoothing the 4 mm breath between keys.
- **The LODs:** LOD1 has 65,372 vertices and 89,114 triangles; LOD2 has 28,765 and 50,010. They keep the 23 slots and 20 bones, and LOD0's bounds.

**The hashes:**

| file | sha256 |
| --- | --- |
| SK_NyaagyuSamurai.fbx | bde1a741… |
| A_NyaagyuSamurai_Walk.fbx | 89fd38a8… |
| A_NyaagyuSamurai_Guard.fbx | f82c9c3a… |
| Nyaakoto_RuntimeSkin.blend | cf4acdef… |
| LOD1 | 74b68590… |
| LOD2 | 5523cbc8… |

### 6.4 What the two-paw grip lacks (measured, `s63`)

At the contract's target, Grip_L at (24, 0, 100) at 30°, both arms are within reach (88 % and 75 %). The visible mesh fails in two ways:
- **The paws and forearms** cross the haori, the under-kimono and the dō: 3468 visible pairs, 10 islands contained.
- **The katana's kashira** crosses the haori and the dō's plates: 945 pairs.

**How far each arm must move forward** to clear the torso (no crossing, nothing contained, and 5 mm apart by exact separation):
- **Right forearm and paw:** 13.0 cm. With the grips that far forward, the right arm would need 111.5 % of its length, a 51.3 cm arm against 45.0 cm.
- **Left forearm:** after a 20 cm shift it still crosses the dō's left lacing in 33 pairs. Reaching across the body, it runs along the front of the armour.

So the two-paw chūdan needs a change of proportion or armour, not a pose. These are options to measure, not claims:
- longer arms, about +6 cm;
- a slimmer dō and haori front;
- a different two-paw stance where the chest is narrower, such as a higher hassō.

Each needs its own full clearance run. The decision is root's.

### 6.5 Review of the renders (`Nyaakoto_RuntimeSkin_{Guard,Idle}_*.png`, ortho, Cycles 32 samples)

The guard reads as a one-paw guard: the right paw is closed round the hilt and the blade is raised in front.

**What does not read well:**
- **Empty closed paws read as rings.** This is the guard's left paw and both Idle paws. The 3.3 x 4.3 cm grip channel shows through, most visibly from the side. A pose cannot fix it: it needs an empty-fist paw state or finger bones, a paw revision.
- **The saya sticks out behind like a pole.** It is horizontal and about 50 cm behind the back. A lower kojiri would read better, but the tilts tried at x 17 crossed the hakama.
- **The kissaki projects onto the mouth from the front.** A centreline kissaki does in any ortho front view. A throat-height tip, near 146 with Grip_R at (40, 18, 105) at 25°, is the classical chūdan, and is inside 4.7's ranges.
- **The source's crossed-collar rods** stick out of the chest. They are not slice A's.

### 6.6 Next

- **The Unreal import and readback** (`import_nyaakoto_third_person.py`), when the lane is free:
  - the body, its clips and LODs;
  - the three sockets, read back within 0.1 cm and 0.5°;
  - W00 into `/Game/Generated/Weapons/Runtime/W00_Katana`;
  - the guard's grips at its first frame.

  Then front and side captures in the editor.
- **Root's 4.6 and 4.7 binding**, with 6.2 in place of the capsule.
- **Open:**
  - the two-paw grip (6.4);
  - an empty-fist paw state;
  - the bow, quiver and arrows' socket migration;
  - adopting gear_saya_l in `viewmodels.json`;
  - slice B (StrikeMakko, W10, draw and sheathe).

## 7. The production revision: study A, furred paws, two-paw guard, strike (measured, 2026-10-26)

Root's 05:15 UTC direction: A (arm 1.2, chest 0.85) as the production rig basis and saya 11 as the carry target; a
consistent source, LODs, kamon and rig; furred paws instead of tube fingers; empty and holding states through the
real FBX and Unreal morph import; every final-combination pose and clearance check again. This is a production
direction, not photoreal acceptance.

**Status (2026-10-26 21:40 UTC):**
- **e8d5b587, built and checked in Blender 5.2.2:** the hero source on A (s101, its validator s102), the runtime rig
  (s103), the LODs (s104), and the runtime and LOD validators (s106, s107). Every gate passed.
- **e8d5b587, read back in Unreal under --rhi (s110-s114, 7.7):** the sockets, the grips on the clips, every LOD's morph
  deltas, and what each LOD renders. s108, under -nullrhi, crashed in the morph re-export.
- **r3** (7.8): the toes' arc, a slimmer thumb and palm, pads, and outward fur strands.
  - Its first production rig, s117, failed one gate on a ray-counting ambiguity and wrote nothing.
  - s118 and s119 diagnosed it; the tightened parity rule decides such cases only for verified targets.
  - s124 passed every gate and wrote the runtime body and clips.
  - Its LODs (s125), validators (s126, s127) and Unreal import and readbacks under --rhi (s128, s129, and the host
    checks of LOD materials and coat) passed (7.8).
  - Its actual-material Unreal originals are s132's: 27 at 3840x2160 in the game's own material instances (s130).
    s131 failed at its own LOD gate (7.9).
  - The authored-normal candidate (s133) and its three-view comparison (s134) are in 7.10. So is the diagnosis of the
    sawtooth boundaries.
- Fur is still not resolved (7.12). No photoreal, visual, gameplay or root acceptance.

### 7.1 The hero source on A

- `create_nyaagyu_hero_character.py` applies A with `nyaakoto_runtime_parts.apply_variant`, the rule the studies
  applied in memory, and records `manifest.proportions` (127 parts moved).
- **The kamon stay exact.** Each SORA kamon moves rigidly with its lacquer backing by its centre's displacement
  (`kamon_moved_m`): the chest with the dō's front (-3.525 cm in x), each sode with its upper arm (about 2 mm), the
  waist not at all. The arm's stretch would otherwise have stretched the sode kamon along the upper arm. The manifest
  records each placement's centre, diameter and plane (`sora_kamon_marks`), and the hero, runtime and LOD validators
  check every SVG path vertex there to 0.02 mm.
- s98's first run, with the sode kamon stretched, is kept as a failed attempt (`s98_hero_A.outputs`).
- **Not reproducible:** the generator's triangle count differs run to run (128,650 committed, 128,607 at s98, 128,729
  at s101). s100 traced s98's difference to Head_tabby_stripe_fibers and the kamon path order. Both are consistent with
  iterating Python sets in the generator. It predates A and is not fixed here; downstream reads the hash-pinned blend.

### 7.2 The furred paws (`nyaakoto_tp_paws.py`)

One closed surface per side replaces the source palm, open fingers and thumb in the runtime body and every LOD. It is
built in numpy, so it is tested on the CPU (`test_nyaakoto_tp_paws.py`), and placed as a Blender part by
`nyaakoto_runtime_parts.fur_paw`.

**The form,** as a signed distance field from the first-person paws' primitives:
- the source palm's ellipsoid, narrowed to the paw's breadth;
- four digits on the old tubes' paths round the channel (50-200 deg), each a capsule chain that thins from the
  knuckle and swells to a toe bulb, and the dewclaw-thumb the other way round (-40 to -130 deg);
- the digits meet each other by a smooth minimum whose reach runs from 11 mm over the knuckles to 7 mm at the toes, so
  the back of the paw is one furred mass and the toes part toward their tips; they blend into the palm by 8 mm;
- the channel grown by 1 mm is carved out, and a slab keeps the paw, fuzz included, inside 11 cm.

**The mesh:** surface nets with one vertex per patch of each cell (`manifold_surface_nets`), smoothed and projected
back onto the field, then a slight outward fuzz (0.4 + 0.4 mm on 6 and 14 mm scales) where there is free space ahead
and the channel is more than 1 mm away. Naive surface nets left 2-12 edges with four quads a paw, where the thumb's
tip meets the toes and in grooves: the patch vertices and the cut pipes close every paw.

**The coat:** M_Hero_GreyTabbyFur alone, its CoatBlend the digit weight times a ramp round the channel: the back and
the toes' first joints tabby, white from there to the tips. In Unreal only this slot blends to the white coat by
CoatBlend (`import_nyaakoto_pbr.py`). UVs at the body's 2.4 per metre, round and along the channel, planar on the
sides.

**The previews:** s96 (the first form: white rolls; its scene isolation also failed and showed the source's paws)
and s97 (v2: tabby back, white toes, fur between the toes). One defect seen in s97, pinched notches where the toe
grooves deepen, was answered by lengthening the blend's ramp before production.

**CPU checks** (`test_nyaakoto_tp_paws`, 23 run: 23 passed), on the hero's own arms, both sides, every LOD step (3.0,
4.5, 7.0 mm), both states: a closed outward 2-manifold; no self-crossing; no facet within 0.5 mm of the channel and no
vertex within the 1 mm carve; the rig's channel gate (no vertex inside, breadth at most 11 cm); every LOD the same
surface (99 % of vertices within 0.75 step of LOD0's); the mesher on its two ambiguous cases (naive surface nets fails
both); self_crossings on a crossing pair and a cap pushed through a ball. A scratch sweep of 48 meshes (8 random
sub-voxel offsets x both sides x the three steps) found every one closed and uncrossed in both states.

### 7.3 The empty fist

PawEmpty_R and PawEmpty_L are a remap in channel coordinates (`empty_points`): each digit vertex keeps its place along
the channel, its angle round the oval and its offset from it, while the oval closes toward its palm-side edge:
E'(t) = E(0) + k(t)(E(t) - E(0)). k is 1 up to the knuckles (|t| at most 40 deg) and eases to 0.30 by 180 deg in log
scale; the displacement is weighted by the digit weight, so the palm does not move.

- The old fist shrank the whole oval to 0.30. That slid every knuckle about 1 cm along the channel and folded 5-8
  triangles of a single surface.
- A linear ramp to 0.30 over 40-160 deg turns the closed oval back on itself (fold margin -0.042 on this oval). The
  log ramp's margin is +0.076, and no face turns over at any LOD.
- The digits' tips close to 0.32, the thumb's to 0.43.
- The rule is one of position, so every LOD's morph is the same rule on its own vertices.

### 7.4 The poses

**A_NyaagyuSamurai_Guard** is the contract's two-paw chūdan (4.5) on A: Grip_L (34, 0, 106), the blade at 30°, the
elbows far forward (study s91), a 4 s loop with a 0.4 cm breath. It replaces the interim one-paw guard. Both paws hold
(PawEmpty 0, 0).

**A_NyaagyuSamurai_StrikeMakko** (1.0 s, 24 fps, IK at every frame) eases from the guard to the raise at 0.40, the hit
at 0.55 and the follow-through at 0.70, and back to the guard at 1.0. Its keys were searched on this body: the nearest
to the contract's target (whose targets were set for the baseline arms) that passes every gate at the key and at a
third and two thirds of the way from the key before it, over Grip_L offsets and the three elbow pole sets.

| key | contract Grip_L, elevation | built Grip_L, poles | reach R / L | kissaki (cm) |
| --- | --- | --- | --- | --- |
| raise | (30, 0, 128), 80° | (39, 0, 128), far_fwd | 0.763 / 0.660 | (48.2, 0, 224.1) |
| hit | (22, 0, 108), -5° | (26, 0, 108), far_fwd | 0.914 / 0.699 | (122.5, 0, 107.2) |
| follow-through | the hit, 2 cm on and 4 cm down, -12° | (26, 0, 105), -12°, far_fwd | 0.953 / 0.734 | (121.7, 0, 92.4) |

- Every raise candidate nearer the contract crossed the torso (and nearer still, the head too): A's raise sits 9 cm
  forward. The first follow-through tried, (28, 0, 104), was out of reach (0.5345 m against 0.5405 m at 98 %).
- The search measured every rejected candidate in full, about 80 s each: 34 raise, 6 hit, 4 follow-through and 2
  recovery-path rows, all in the log (`Saved/W18Rebuild/s103_rig_production.log`). The accepted keys are also in
  `Saved/W18Rebuild/s103_strike_keys.json`.

**Idle and Walk** carry the katana in saya 11 with both paws empty (PawEmpty 1, 1).

### 7.5 The checks

The build keys all four clips, then checks every gate at every key and the midpoint after it before anything is
written:
- Idle, Walk and Guard are keyed every 4 frames, so they are checked at every other frame: 48, 16 and 48 frames;
- the strike is keyed at every frame and checked at all 25;
- the rest pose, for 137 + 1 checks.

A failing gate exits 1 and writes nothing. The gates added for two paws and the strike:

| check | sets | gate |
| --- | --- | --- |
| forearms and paws against the head | forearm_R/L, hand_R/L against head and neck | no crossing, containment or ambiguity |
| katana against the body but the holding paws | W00 katana against everything but hand_R and hand_L (both hold) | 0, 0, 0 |
| katana against the holding paws | W00 katana against hand_R and hand_L | 0, 0, 0 |
| blade against the body | habaki to kissaki against the body but head and both paws | at least 3 cm, exact |
| paw against paw | hand_L against hand_R | 0, 0, 0 |
| the left grip's closure (4.7) | hand_l_grip against the katana's Grip_L, the katana placed by hand_r_grip | within 1.0 cm |
| the paws on the tsuka (4.2) | each paw's vertices along the katana's X from Grip_R | the right paw behind the fuchi (5.5 cm), the left within 1 cm of the kashira (-18.99) |

The earlier gates stand: forearms and paws against the torso, the blade against the head (5 cm, exact), the left paw
against the saya, the saya against the body with the obi as its tuck and hide, the sheathed hilt against the body.
**The shoulders against the torso are reported, never gated:** the rigid shoulder joints and sleeves meet the haori by
build, at rest too.

**s103's results** (138 frames, exact, ranges over frames):

| check | result |
| --- | --- |
| forearms and paws against the torso | 0 visible, 0 contained; separation 2.07-19.88 mm |
| forearms and paws against the head | 0, 0, nothing within 2 cm |
| katana against the holding paws | 0, 0; 1.82 mm |
| katana against the body but the holding paws | 0, 0, nothing within 2 cm |
| paw against paw | 0, 0, nothing within 2 cm |
| blade against the head; against the body | nothing within 5 cm; nothing within 3 cm |
| left paw against the saya | 0, 0, nothing within 2 cm |
| saya against the body (obi tuck and hide) | 0 visible; 280 tuck pairs allowed |
| sheathed hilt against the body | 0, 0 |
| the left grip's closure | 0.0 cm at all 73 two-paw frames |
| the paws on the tsuka | the right paw's front at most 5.413 cm (fuchi 5.5); the left paw's back at least -19.661 (kashira -18.99, 1 cm allowed) |
| grip sockets on their targets | within 0.0166 cm |
| upper arms against the torso (reported) | 932-1401 visible pairs, 0-5 contained |

- Guard: the kissaki at z 160.3-161.1 (4.7: 145-165), on the centreline; reach 0.871 right, 0.707 left.
- The run took 3 h 08 min, 1 h 50 min of it the frame checks. mesh_clearance's candidate test is |a| x |b|, and the
  paws are ten times the triangles the curled tubes were. A grid broad-phase with identical results except
  `pairs_measured` is tested on the CPU (25 run: 25 passed) and goes into the next pass.

### 7.6 The LODs and Unreal

**The LODs** (s104): LOD1 76,848 vertices and 112,106 triangles, LOD2 32,489 and 57,578 (LOD0 176,069 and
184,493). Each carries its paws at its own step and both morphs, 0 at bind. The LOD record's `max_move_cm` is in the
joined mesh's local units (3.541 at LOD1); s107 measures 3.01 cm in world at every LOD.

**The validators:**
- s106 (runtime): the morphs re-derived from the exported FBX by the rule: 0.00023 mm (R), 0.00019 mm (L) at most,
  3.01 cm the largest move; nothing else moves. Guard round trip, 97 frames: at most 0.300 cm and 0.018 deg. Strike
  round trip, 25 frames: 0.001 cm and 0.011 deg. Its first run (s105) failed on the validator's own frame numbering:
  Blender's FBX import starts each action a frame later.
- s107 (LODs): both pass, with the four exact kamon; the morph rule within 0.00015 mm (LOD1), 0.00011 mm (LOD2).

**Unreal** (s108, in the art worktree, NullRHI):
- imported SK_NyaagyuSamurai with its coat colours and morph targets, LOD1 and LOD2 (render vertices 186,876, 84,678
  and 36,002), and Idle, Walk, Guard and StrikeMakko; the morph target names read back PawEmpty_L and PawEmpty_R.
- Then crashed in the morph re-export: UE 5.8's skeletal FBX exporter always builds material-baking mesh data from a
  spawned component (FFbxMaterialBakingMeshData, FMeshMergeHelpers::RetrieveMesh,
  USkinnedMeshComponent::GetCPUSkinnedVertices), which asserts on a missing render MeshObject under -nullrhi. The
  editor hung in its crash handler and was terminated (SIGKILL, 137): a failed run, its log, sample and exit kept.
- Next: the same import under `--rhi`, then check_nyaakoto_ue_morph_export.py on Unreal's export (7.7).

### 7.7 The Unreal readback under --rhi (s110-s114, e8d5b587's assets)

**The import** (s110, `run-editor-script.sh --rhi`: UnrealEditor-Cmd with -RenderOffscreen; the art worktree, no
weapons; 61 s, editor exit 0):
- **Why --rhi:** `FApp::CanEverRender()` is false whenever -nullrhi is on the command line
  (Core/Public/Misc/App.h:400-406). So no skinned component gets the render MeshObject that the exporter's
  material-baking data asks for (SkinnedMeshComponent.cpp:1231 and 4987). Under -RenderOffscreen it gets one.
- **Sockets:** hand_r_grip 0.0 cm and 0.0°, hand_l_grip 0.00001 cm, gear_saya_l 0.0 cm.
- **Both grips on the clips**, at the guard's first frame and at the strike's raise (frame 11) and hit (14): within
  0.00005 cm and 0.001° of the two-paw stances' targets.
- **Morph targets:** PawEmpty_L and PawEmpty_R on three LODs; render vertices 186,876, 84,678 and 36,002.

**Every LOD's morph deltas** (s113). check_nyaakoto_ue_morph_export.py reads Unreal's own FBX export of the
imported mesh in Blender. It checks the deltas against the rule of the paw module that built the assets, and refuses
any other module.

| LOD, paw | paw vertices | moved over 0.15 mm by the rule: count, worst error | dropped by Unreal, largest | moved outside the paws |
| --- | ---: | --- | --- | ---: |
| LOD0 R / L | 17,282 / 17,190 | 5,945 / 5,881; 0.0005 / 0.0001 mm | 356 / 366; 0.148 / 0.150 mm | 0 |
| LOD1 R / L | 8,059 / 7,985 | 2,844 / 2,785; 0.0003 / 0.0001 mm | 207 / 197; 0.150 / 0.143 mm | 0 |
| LOD2 R / L | 3,471 / 3,438 | 1,239 / 1,209; 0.0009 / 0.0010 mm | 94 / 91; 0.149 / 0.140 mm | 0 |

- **Unreal's threshold.** A delta is kept only if the vertex moves more than the LOD's MorphThresholdPosition,
  0.015 cm by default (EngineTypes.h:3181), or, when normals are computed, if its normal turns enough
  (LODUtilities.cpp:3132). The import leaves the threshold at the default, and s114 reads 0.015 cm on every LOD.
- **The model.** Below the threshold, the check accepts either outcome (at the rule, or unmoved), each at the same
  0.05 mm. 1-5 such deltas a morph were kept.
- **The failed first check.** s111 held every vertex to the rule alone, and failed at 0.140-0.150 mm on every LOD: the
  dropped deltas. It also counted --factory-startup's default cube as a mesh. s112 passed, but counted palm vertices
  as kept deltas; s113 fixed the count.

**What each LOD renders** (s114, read-only):
- **The question.** In Unreal's export, LOD2's paws are labelled M_Hero_IndigoSilk, and LOD2's triangles per material
  are a permutation of ours by name.
- **The cause.** Our LOD2 FBX lists its 23 materials in another order than LOD0's.
  - Unreal routes an imported LOD's sections through `LODMaterialMap`, built by imported slot name
    (`FLODUtilities::MatchImportedMaterials`, LODUtilities.cpp:3948-3981).
  - The exporter writes each section's raw `MaterialIndex` (FbxSkeletalMeshExport.cpp:226).
- **The check.** readback_nyaakoto_lod_materials.py reads each section through `GetLODMaterialSlot`, which goes via the
  map. check_nyaakoto_lod_materials.py then pairs Unreal's 23 sections per LOD with the export's 23 polygon runs.
- **The result.** On every LOD, the number of triangles Unreal renders with each material equals ours, by name; 17 of
  LOD2's sections are remapped. The permutation is the export's alone. This establishes per-material triangle counts
  and the routing, not that each face keeps its own material (root, 20:37 UTC).

**The coat** (`inspect_fbx_paw_coat.py`, host Python) was read in our three LOD FBXs and in Unreal's export of all
three:
- On both paws, 81.5-82.4% of the paw's corners are tabby and 11.8-12.3% white. All of the back is tabby. Every corner
  is within about one byte of the coat the paw module computes (that reader rounded to 4 decimals; r3's unrounded
  reading, 7.8, finds a few LOD0 corners up to 3.35e-8 past one byte).
- The paws' white look in s103's close renders is the light. The tabby back of `..._IdlePaw_Front.png` measures (171,
  166, 161) against the white toes' (176, 173, 171). In the side view, the hind foot's grey (92) and its white toes
  (212) part clearly.
- r2's `render_close` therefore keeps only the review sun and the world.

### 7.8 r3: fur strands, the toes' arc, a slimmer thumb and palm (s115-s117)

Root's 12:53 UTC review of e8d5b587's original renders (2026-10-26) asked for three things:
- "smooth white parallel finger/ring forms, with no visible tabby contrast on the back";
- "the idle digit row is nearly straight";
- "the thumb/hand mass remains bulky".
Its 07:12 review of s97 asked for credible fur direction, density and silhouette.

**Fur strands** (`nyaakoto_tp_fur.py`):
- **The strands:** single tapered triangles of M_Hero_GreyTabbyFur on the paw's own surface, within the 23 slots, as
  the head's fur cards are. Each leans along the coat's flow: along the toes, and down the back toward the knuckles.
- **Where none grow:** within 6 mm of the grip channel.
- **What is kept:** a strand whose tip is outside the skin and inside the 11 cm breadth, and which crosses the skin in
  neither state.
- **The empty fist:** the strands are vertices of the paw part, so the empty-fist rule moves them with the skin.
- **Per LOD:** LOD0 has the full density (8 per cm², about 5,240 strands a paw on r3), LOD1 35% of it, LOD2 none.

**The toes' arc:**
- `closure_end(s)`: the empty fist's closure ends at EMPTY_CHANNEL + 0.12 over the middle toes, easing to
  EMPTY_CHANNEL by |s| 30 mm.
- DIGIT_END's stagger alone nearly vanishes in the fist, because every tip past 180° closes to the same share of its
  chord. With the arc, the middle toes stand 20.8-21.1 mm proud of the channel in the empty fist and the outer toes
  12.0-12.2 mm.
- The grip is untouched. The fold margin stays 0.0759: the displacement never moves along the channel, and
  fold_margin takes the least over s.

**The thumb and palm:**
- the thumb 15.0 to 10.0 mm (r2 16.5 to 10.6; s97 19.0 to 10.8);
- the palm at 0.82 × 0.80 of the source's x and z radii, shrunk about its point nearest the channel, so it still
  meets the grip;
- grip volume 1,142 cm³ a paw (r2 1,422; r1 1,671).

**The previews** (form only, one sun and a grey world): s115 (r2 with fur) and s116 (r3 with fur). Every paw check
passes, and both empty fists show the arc. Root's review of s116 (14:38 UTC):
- the arc and the grey/white separation now show;
- the surface still reads as sparse stubble with a bright bristled fringe;
- the empty fist's inner view keeps a large C-shaped opening and smooth white patches. Those are the toes' grip-side
  faces, which strands avoid; anatomically they are the pads, so a pad material from an existing slot is proposed;
- the cuff and forearm stay faceted.

**The production rig build, s117** (13:37:44-17:18:50 UTC, exit 1, nothing written):
- **What passed:**
  - s103's strike keys at the first try, their thirds and the recovery path;
  - 136 of the 137 checked frames (48 Idle, 16 Walk, 48 Guard, 25 Strike).
- **What failed:** StrikeMakko@16, katana_vs_holding_paws; frames 15 and 17 pass.
- **The report crashed.** After the checks, the failure report's `brief()` took the held frames' socket errors for
  clearance results (KeyError), so the failure's parts and place were never printed. The rest pose's result was
  lost with it. Fixed: `brief()` handles any entry, and each CHECKED line carries its socket angle errors and the
  detail of any failing gate.
- **The cost** was 3 h 41 min. Not the strands: on the CPU, katana_vs_holding_paws at frame 16 takes the same with or
  without them. It was `mesh_clearance.bbox_pairs`, whose grid cell the coarser set's 99th-percentile triangle set: the
  katana's 15.3 mm against the paws' 6.9 mm, tens of millions of candidates for 69 overlapping pairs.
  - The cell is now the finer set's. A larger triangle gathers only the cells its bounds reach (or takes the pairwise
    test directly when it would reach more cells than the other set has members), and every candidate takes the exact
    test.
  - On frame 16's katana and paws, the answers are identical to s117's module, and 7-12× faster. s124, the whole build,
    took 49 min 44 s.

**The diagnosis** (s118, s119). `--check-frames` rebuilt the body, checked StrikeMakko@15-17 alone and printed them in
full.
- **The failure:** one "ambiguous" containment test, nothing crossing or contained, the separation 1.82 mm.
- **s119's record:** the same frames on s118's own modules, with every parity disagreement saved raw.
  - It is a left-paw point 12.05 mm outside katana part 17.
  - Its first ray grazes an edge of that part, entering and leaving 0.867 µm apart. The Blender backend's
    `ray_hits` casts again from 10 µm past each hit, so it never saw the exit: 3 hits against the other ray's 0.
  - Counted numerically in float64 without the step, the ray has 4 crossings. Root's own replay, with eight more
    directions, agrees (18:49 UTC). float32 is not needed to explain it.
- **The measurement now** (`mesh_clearance._inside`, only with `--resolve-parity`, which needs `--parity-evidence`).
  A disagreement is decided by the target's winding number, computed numerically in float64, only when all of these
  hold:
  - the target is a closed, coherently oriented manifold: every directed edge once with its reverse, and each
    vertex's faces one fan (`oriented_manifold`);
  - the point and the target are finite;
  - no target face is under 1e-14 m², and the enclosed volume is at least 1e-12 m³;
  - the point is at least 1 µm away;
  - the winding number is within 1e-6 of 0 (outside) or of the volume's sign (inside, which still counts as
    contained).

  Anything else stays ambiguous and fails, and hide tests are never resolved.
  - Root found the first version's 0.25-wide bands passing a tetrahedron with two faces turned (18:28 UTC). The
    tests cover that, a reversed tetrahedron, bowties and opposed shells, non-manifold and open targets, non-finite
    and degenerate data, and points on the surface.
  - Every disagreement is saved raw (point, target vertices and triangles, both rays' hits, SHA-256-indexed).
    `replay_parity_evidence.py` replays each from the files alone.

**The visual corrections** (s120-s123, previews):
- **The pads:** `pad_faces`, M_Hero_RoseNose, on the grip side within 4 mm of the channel. Four toe beans, the
  dewclaw's pad and a palm pad: six separate pads at LOD0, the same area (38-39.5 cm²) on every LOD.
- **The strands:**
  - they were all wound to face into the skin (face · root normal about -0.97). Cycles shaded them as backfaces, and
    a one-sided Unreal material would cull them. They now face outward and carry their root's skin normal;
  - they lie flatter and shorter (8-18°, 2.8-5.5 mm; the guard hairs 12-24°, 5.5-8 mm);
  - they grow from 4.5 mm of the channel, so the fur meets the pads, with every tip still 2 mm off it;
  - their tips clear the fuzz by 0.1 mm, giving about 5,280 a paw.
- **Still open** (root, 19:00 UTC): s123's originals still show sparse dark stubble lines over the grey and a broad
  pale band on the empty toes. They are kept for the actual-material Unreal review; whether they come from the
  preview's procedural material, its one hard sun and Cycles, or from the coat itself is not separated.

**The production rig, s124** (18:57:18-19:47:02 UTC, exit 0), with `--strike-keys --resolve-parity --parity-evidence`:
- **Gates:** s103's strike keys and all 137 checked frames pass every gate, and the rest pose does too.
- **The paws:**
  - 201,632 vertices in all;
  - strands, 5,277 and 5,278 a paw, none crossing the skin in either state;
  - the katana against the holding paws at 1.82 mm, the forearms and paws against the torso at 2.07-19.88 mm.
- **Parity:** five disagreements (the strike path's second recovery check, StrikeMakko@14, 18, 19 and 22), each decided
  outside at 10.1-13.8 mm. The replay reproduces every record: merged within 1e-9 m every count is even, and the 10 µm
  step gives Blender's own counts.
- **The close renders** now keep only the review sun and the world. IdlePaw_Front shows the grey tabby back and the
  white toes, and the toes' arc.

**The LODs, validators and Unreal, s125-s129** (19:58:02-20:06:22 UTC, each exit 0; the ledger has every command, PID
and hash):
- **s125, the LODs** from s124's blend: LOD1 84,988 vertices and 110,228 triangles, LOD2 31,391 and 55,374, each with
  its own paws, pads and morphs. LOD1 has 35% of the strand density (1,801 and 1,829 strands), LOD2 none. The LODs it
  replaced are archived in `s125_lods.originals/`.
- **s126 and s127, the validators:**
  - LOD0: 201,632 vertices, 23 materials and 20 bones. The morphs re-derived from the FBX are at the rule within
    0.00024 mm, with a largest move of 3.01 cm.
  - The guard's 97 frames round trip within 0.3 cm and 0.018° (as in s106; the gate is 1 cm and 2°), and the strike's
    25 frames within 0.001 cm and 0.011°.
  - LOD1's and LOD2's morphs are at the rule within 0.00015 mm and 0.00011 mm.
- **s128, the Unreal import under --rhi** (wrapper 80093, editor 80155, 19:59:01-20:00:52):
  - **Sockets:** hand_r_grip 0.0 cm, hand_l_grip 0.00001 cm and gear_saya_l 0.0 cm, all at 0.0°.
  - **Clip grips:** both grips at the guard's first frame and at the strike's raise (11) and hit (14), within 0.00005 cm
    and 0.001°.
  - **Morphs:** PawEmpty_L and PawEmpty_R on 3 LODs. Unreal's runtime vertices are [212573, 92966, 35078].
  - **Each LOD's saved build settings:** MorphThresholdPosition 0.015 cm, recompute normals on.
  - **Materials:** 23 slots, M_Hero_RoseNose among them, and 23 sections on every LOD.
  - **The log** has s110's five Interchange warnings, one HTTP probe timeout and the engine's 19 startup self-test
    lines, and nothing else at Warning or Error. UnrealTraceServer and zenserver exited on their own.
- **s129, Unreal's morph deltas** against each LOD's threshold as saved (0.015 cm on all three):
  - Every vertex the rule moves more than 0.15 mm is at the rule within 0.00075 mm (LOD0 9,932/9,869, LOD1
    4,158/4,123, LOD2 1,275/1,266).
  - Unreal dropped 618/621, 245/277 and 82/82 smaller deltas (the largest 0.139-0.150 mm) and kept 0-3 under the
    threshold.
  - Nothing outside the paws moved.
- **What Unreal renders per material** (`check_nyaakoto_lod_materials.py`): on every LOD, the number of triangles per
  material equals ours, by name, through LODMaterialMap's routing; 17 of LOD2's sections are remapped, as in s114.
  This establishes per-material triangle counts and routing, not per-face identity.
- **The coat** (`inspect_fbx_paw_coat.py` v3, in our three FBXs and in Unreal's export of each):
  - **Matching counts.** The paws' skin corners and strands are equal in both. Every strand survives the import:
    5,277/5,278 on LOD0, 1,801/1,829 on LOD1.
  - **The skin.** 78.88-79.46% is tabby and 13.35-13.72% white, and all of the back is tabby.
  - **The largest difference from the module's coat** is one byte plus at most 3.35e-8 (reader v4, unrounded):
    - Unreal's export, LOD0: R 0.003921602052800788, with 19 corners beyond 1/255 + 1e-9; L 0.003921595975464487,
      with 31.
    - Our LOD0: R 0.003921590599359259 (19 corners) and L 0.003921595975464487 (31).
    - LOD1 and LOD2, in either file: none beyond.
    - v3 rounded this to 0.0039, which root's precision probe (20:37 UTC) showed understates it.
  - **Telling strands from skin.** Unreal's export also isolates 34-122 skin triangles a paw at seams and section
    edges. A strand is told apart by its reach: 0.9005 mm and more off the skin, against those triangles' 0.6707 mm at
    most.
  - **Reader versions.** v1 and v2 classified strands by topology alone; v4 adds the unrounded error. All the reports
    are kept.
- **Not shown by any of this:** how the fur looks in Unreal's actual materials and light. That is 7.9's capture.

### 7.9 The actual-material Unreal review (s130-s132)

Root asked (20:31 and 20:37 UTC) for the actual saved Unreal materials at original full resolution: both paws empty
and holding, from their pads and their backs; the cuffs; the full guard and strike; each shot's LOD stated. The current
state was to be captured before any change to the normals.

**s130, the game's materials** (`import_nyaakoto_pbr.py`, 20:39:02-49 UTC, exit 0):
- **Why it was needed:** the game draws each `M_Hero_X` slot with `/Game/Generated/Characters/Nyaakoto/MI_Nyaakoto_X`,
  bound at runtime (SoraCharacterBase.cpp:155-166). The art tree had never made those instances.
- **What it made:** the master M_Nyaakoto_PBR, 23 instances, 18 PBR maps and the painted iris, all new. Only
  MI_Nyaakoto_GreyTabbyFur blends the white fur by the CoatBlend vertex colour.

**The capture** (`render_nyaakoto_tp_review.py`, in the full editor):
- **Materials:** the slots are bound as the game binds them, and all 23 are gated before every shot.
- **Pose and LOD:** each pose is a clip held at its time. Both PawEmpty morphs are 0 for holding and 1 for empty.
  Each shot's LOD is forced and read back, both the forced value and the predicted LOD.
- **Gates:** before and after each image, the grips against the stance's targets and the morph weights.
- **Light:** the yumi review's metered daylight, a 20,000 lux sun 50 deg up from the front left, with its sky light
  and fixed exposure.
- **Image:** 3840x2160 at r.ScreenPercentage 100, TSR with a 32-frame run-up, and texture streaming off.

**The paw cameras** are measured, not placed by eye (`plan_nyaakoto_tp_review.py`, host numpy):
- **The paws:** both are rebuilt to the record's exact skin counts and posed by their grip sockets.
- **The ranking:** about 1,700 view directions are ranked by the pad or back area each actually sees, taking the
  lower score of the holding and empty states.
- **The choice:** Unreal takes the best-ranked view whose sight line clears the posed body. The body is 4,864 voxels
  of LOD0's skin, each moved by its bone; the plan's 19 bind bones are within 1.35e-5 cm of Unreal's reference pose.
- **Earlier plans:**
  - Attempt 1 read the bones in metres against centimetre vertices.
  - Attempt 2's body capsules were dominated by the bow, quiver and saya, which gave the torso capsule an 89.5 cm
    radius.
  - Both are kept.

**s131 failed** (20:59:36-21:04:31) at its own LOD gate: "LOD1 reads forced 2, predicted 0".
- **The cause:** SetForcedLOD only stores the value. UpdateLODStatus applies it, and outside a tick it runs only when
  the mesh asset is set. This editor-world component never ticks.
- **What was kept:** 14 originals, whose recorded gates all passed, and manifest.partial.json.

**s132 passed** (21:10:08-21:13:53, exit 0; `Saved/NyaakotoThirdPerson/Review/s132/`, manifest e01aac98...):
- **The fix:** when the LOD changes, the mesh asset is cleared and set again, and the materials, morphs and clip are
  set again after it. LOD1 and LOD2 then read forced 2 and 3, predicted 1 and 2.
- **27 originals:**
  - **The guard's paws**, holding and empty, pads and back. In the guard the pads face into the curl, and the rear
    left paw's better views pass through the body: the right pads' view sees 47% of them holding and 33% empty, the
    left's 36% and 19%.
  - **The same views in the reference pose** ("rest", not a game pose), where the paws hang clear. The pads' views
    are the planner's best, seeing 48-49% holding and 35-36% empty; that is as much as the curl shows.
  - **The cuffs** from outside and below.
  - **The full body:** the guard front at LOD0, LOD1 and LOD2, the guard side, the strike raise front and side, and
    the hit side.
- **Gates:**
  - **Grips:** the guard's within 0.0021 cm, the rest pose's 0.00001 cm, the raise 0.00055 cm, the hit 0.0059 cm.
  - **Morphs and LODs:** as set, before and after every image.
  - **Views:** every one clear of the body.
- **The host check** (`check_nyaakoto_tp_review.py`): all 27 are at their hashes, PNG at 3840x2160, none blank or
  clipped. Each holding/empty pair shares one camera, and 0.68-7.9% of its pixels change with the morph.
- **Recorded, unchanged:**
  - Every LOD recomputes normals and tangents, Interchange's default (`bRecomputeNormals = true`) since s128. The
    strands therefore shade by their own faces, within their 8-24 deg lift of the skin normal, not by the root normals
    they carry.
  - The master is opaque, default-lit and one-sided.

**What the images show** (described, not judged; the review is root's):
- **The coat:** the grey tabby and the white coat blend as the game's material blends them.
- **Strands:** fine dark strand marks lie over the grey, and the silhouettes are bristled.
- **Coat edges:** where the coat turns white, the edge is jagged. This is unverified, but consistent with strands
  carrying their root's colour across it. The pads' edges are jagged too, against uniform rose pads.
- **The empty state:** the curl closes tighter.
- **The cuffs:** they end in flat discs with hard rims at the wrist.
- **LOD2:** it visibly drops the head's fibre cards.

### 7.10 The authored-normal comparison (s133-s134) and the sawtooth boundaries

Root reviewed s132's originals and rejected them visually: sparse dark stubble, broad sawtooth coat and pad
boundaries, smooth pale toes, hard faceted cuff discs, and dark broken lines on the LOD0 face that LOD2 loses along
with its fibre detail. Root then asked for a controlled comparison: the same mesh source, pose, material, camera and
light; recompute normals disabled on a separate candidate; the imported normals verified; the tangents explicit; the
s132 baseline preserved.

**How far Unreal's recomputed normals are from ours** (`compare_fbx_normals.py`). It compares s128's export of the
baseline with our LOD0 FBX, corner by corner:
- **Paw strands:** 13.4 deg median, 22.3 at p99, 24.0 at most. These are exactly the strands' own face angles: Unreal
  shades each strand by its face.
- **Paw skin:** 0.16 deg median, 2.8 at p99.
- **The head's fur cards:** 0.007 deg median. Their authored normals already are their face normals.
- **The forearms (the cuffs), pelvis, spine and legs:** 15-24% of corners more than 10 deg off, 39-62 deg at p99.

**s133, the candidate** (`prepare_nyaakoto_authored_normals.py`, 21:27:50-21:28:38 UTC, exit 0):
- **The asset:** the baseline duplicated to `/Game/Generated/Candidates/AuthoredNormals/SK_NyaagyuSamurai_AuthoredNormals`,
  with LOD0 recompute_normals set from true to false.
- **Settings:** every other build field is read back equal on every LOD. The tangents are explicit and the same on
  both: recomputed, MikkTSpace, 8-bit basis.
- **The baseline package:** unchanged before and after.
- **Verified:** the candidate's built LOD0 normals equal ours to 0.0011 deg at most, over all 488,528 corners.

**s134, the comparison** (`render_nyaakoto_normals_comparison.py`, 21:29:36-21:32:15 UTC, exit 0):
- **The shots:** guard_front_LOD0, paw_R_back_empty_LOD0 and cuff_R_outside_LOD0, each as the baseline and then the
  candidate, in one level and light. s132's cameras are replayed, and every gate passes before and after each image.
- **Repeat noise:** the baseline re-shot against s132 changes 0.05-0.08% of the pixels.
- **The candidate's effect:**
  - 0.88% of the pixels on the guard front, 14 times the repeat;
  - 10.0% on the paw's back, 213 times;
  - 17.5% on the cuff, 227 times.
- **Where it changes:** the sleeves', forearms' and armour's smooth shading, and the paw strands, as a fine speckle.
- **The head:** 2.2% of its pixels change, against a repeat of 0.16%. Its dark broken lines, the fur cards, are
  unchanged.
- **Adoption:** whether to adopt authored normals is root's.

**The sawtooth boundaries are not the coat and not the normals** (`diagnose_nyaakoto_paw_boundaries.py`):
- **The coat:** on the right paw's LOD0 skin the CoatBlend is continuous. Its largest step across any edge is 0.
- **The UV projection:** `corner_uvs` maps a face planar in the channel's cross-section when it looks along the channel
  (|n . Y| > 0.75), and round the channel otherwise.
  - 6,950 of the 24,396 faces are planar.
  - The two mappings are unrelated, so their 873-edge, 2.32 m boundary jumps the fur texture by a median 17.6 cm of
    texture space, along a triangle staircase.
- **The pads:** `pad_faces` gives whole faces M_Hero_RoseNose, a 292-edge, 0.81 m staircase.
- **Rendered from s132's own cameras**, the planar region and the pad faces fall exactly on the originals' sharp light
  patches and jagged pad outlines.
- **Possible fixes, for root to choose; none is made:**
  - **For the UVs:** one continuous mapping, or two UV sets cross-faded in the material by a smooth per-vertex weight.
  - **For the pads:** cut the faces along a smooth contour of a per-vertex pad field, or blend the pad colour in the
    fur's material by such a field.

### 7.11 The r4 repaired-paw candidate (s135-s143)

Root (21:53 UTC) gave the lane for a CPU prototype of a continuous paw UV mapping and of pads cut along a smooth
contour of a per-vertex field. The pads' geometric separation and the PBR material's semantics were to be kept. Once
the topology, morph and weight, foldover and stretch checks justified it, a separate candidate could be built,
imported with authored normals and captured in matched views. s132, s133 and s134 were to be preserved.

**The prototypes** (`nyaakoto_tp_paw_surface.py`, measured by `measure_paw_surface_prototypes.py`):
- **The surface.** The paw is a torus round the grip channel (V - F/2 = 0). Its area is about 0.24 of one fur tile at
  the body's density, so a seamless map with whole tiles must be denser on average.
- **The mappings tried:**
  - **round:** the baseline's round mapping everywhere. It folds where it shears (about 10,700 faces).
  - **torus_arc:** arc length round the cross-section. It shears more than the baseline.
  - **torus_tiles:** whole tiles by arc fraction. It folds on 8% of the faces, on the toes.
  - **The periodic harmonic map:** fold-free by construction (Gortler, Gotsman and Thurston). Its density runs from
    0.24x on the back to 2.9x on the inner wall.
  - **A free-boundary ARAP unwrap:** it squashes the back. Cut along the inner wall, the paw is a strip whose middle is
    three times longer than its edges.
  - **The choice:** the periodic map at 2x1 tiles, refined as rigidly as possible toward one uniform scale, and
    untangled locally.
- **The chosen map's seams:** the shortest longitude (the inner wall, about 140 mm) and the thumb and toes' junction.
  Both jumps are whole tiles, and the fur maps tile exactly.
- **The pads:** pad_field is a smooth margin built from pad_faces' own criteria (smooth minimum and maximum, 0.8 mm
  rounding).
  - cut_exact puts each crossing at the field's root.
  - Within 15% of an edge's end, the contour runs through the vertex, so no vertex moves.
  - Quads split along their better diagonal.

**s136, the paws prepared on the host** (`prepare_nyaakoto_r4_paws.py`; per paw, right then left):
- **The cut:** 25,004 and 24,988 faces, with 304 and 302 new vertices on baseline edges.
  - Closed, oriented manifolds, Euler 0.
  - Pads: 38.70 and 38.76 cm2, against the field's true 38.89 and 38.99, and the baseline staircase's 39.55 and 39.42.
- **UVs:** 0 faces folded after untangling (5 and 2 before), and 0 visible seams (the baseline has 2.74 m and 2.89 m).
- **Anisotropy, median and p90:**
  - the back: 1.25 and 1.58 (baseline 2.60 and 6.2);
  - the toes: 1.61 and 2.65 (baseline 3.0 and 19.4);
  - the sides: 1.86 and 3.6 (baseline 1.12 and 1.28).
- **Density against the body's:** about 1.2x on the back, 1.3x on the sides, 2.1x on the toes, and denser on the
  hidden inner wall.
- **Slivers:** 29 and 31 faces between 5 and 10 deg (the baseline has none). The 2 faces under 5 deg in each paw are the
  baseline's own, untouched.
- **The contour's error, three measures, none of them a Hausdorff distance:**
  - the field's margin |f| along the cut: p99 0.26 mm, at most 1.15 and 1.24 mm;
  - the first-order estimate |f| / |grad f|: p99 0.36 mm, at most 1.48 and 55.39 mm. It is ill-conditioned where the
    gradient nearly vanishes (0.0224 at the left paw's sample);
  - root's independent nearest field-zero vertex bounds: 1.56130 mm (right) and 1.76256 mm (left).
  The baseline staircase's first-order error is p99 1.61 and 1.66 mm.
- **Coat:** by rule, equal to mesh_paw's at baseline vertices; it differs from interpolation by at most 0.022 at new
  vertices.
- **The empty fist** turns 0 faces over. New vertices sit at most 0.098 mm off their edge's interpolated rule.
- **The strands:** the built ones are replayed exactly (5,277 and 5,278), each root is located in its cut piece, and
  none is on a pad. They take their roots' new UVs and keep their coat and normals.

**s137-s141, the assembly in Blender** (`assemble_nyaakoto_r4_paws.py`). It loads the runtime blend in memory, swaps
only the two paw skins, exports, and never saves.
- **s137 to s140 failed safely.** Each stopped at its own check, wrote only a control FBX and saved nothing:
  - s137: float32 arccos read equal normals as 0.024 deg apart;
  - s138: an outdated BMesh index table;
  - s139: a tuple sort key;
  - s140: whole-mesh normal re-encoding moved 9.25% of the kept corners by up to 0.238 deg.
- **s141 passed.** The mesh has 202,238 vertices and 154,058 faces: the kept faces in their order, then the cut faces.
  - **Read back:** keys, positions, UVs, coat bytes, groups and materials.
  - **Kept corners' normals:** bit-identical. Their INT16 codes are restored, and the mesh is rebuilt through BMesh.
  - **The cut skin's normals:** its parent faces' old corner normals, interpolated at new vertices, within 0.0232 deg.
    Blender's own bisector there would be 2.3 deg off at the median, and up to 12.2.
- **The host check** (`check_nyaakoto_r4_fbx.py`):
  - **Control:** equal to the production SK FBX outside the header. UIDs are compared by the object they name; Blender's
    exporter hashes strings with a per-process seed, and the first report counted them as 822 differences.
  - **Candidate against the control:** 21 elements differ, all the paws': the mesh arrays, the hand clusters, and the
    PawEmpty shapes and their channel weights.
  - **The paws' semantics:** all as prepared, with the new vertices' morph at empty_points within 1.01e-7 m.

**s142, the Unreal import** (`import_nyaakoto_r4_candidate.py`):
- **The asset:** the separate `/Game/Generated/Candidates/R4Paws/SK_NyaagyuSamurai_R4Paws`, on the baseline's
  skeleton, with the sockets copied. It has LOD0 only; LOD1 and LOD2 are not part of the candidate.
- **LOD0's build settings:** s133's candidate's, field for field (authored normals, explicit MikkTSpace tangents).
- **Normals:** its built LOD0 normals equal ours, 0.0 deg on the paw skin and strands, over all 492,164 corners.
- **Render vertices:** 210,307, against the baseline's 212,573. The continuous UVs need fewer seam splits.
- **Preserved:** the baseline, its skeleton and s133's packages are unchanged.

**s143, the matched views** (`render_nyaakoto_r4_comparison.py`):
- **The shots:** nine LOD0 views, each as the baseline, s133's candidate and r4, in one level and light, with s132's
  cameras replayed and every gate kept.
- **The host check** (`check_nyaakoto_r4_comparison.py`) finds no problems.
  - r4 against s133 changes pixels on the projected paws. paw_R_back_empty, for one: 788,814 inside the mask, and 579
    outside against a repeat of 681.
- **Seen in the originals** (root's reading at Coordination 228 agrees):
  - the planar light patches with jagged edges, the paw backs' concentric banding and the sawtooth pad outlines no
    longer appear;
  - new in r4: the fur pattern is finer than the body's, and stretched and streaked on the toes, thumb and inner digits;
  - remaining: the stubble is sparse, the toes are smooth and pale, the pads are flat, and the face's strokes are
    unchanged.
- **Adoption:** none. Adopting r4 is root's decision, and root has rejected the remaining defects.

### 7.12 What remains

- **Fur.**
  - Sparse dark stubble lines and a pale band on the empty toes remain in the previews and renders (root, 19:00). The
    actual-material originals are s132's (7.9), and the authored-normal comparison is s134's (7.10), for root's review.
  - **The sawtooth boundaries** were the paws' per-face UV projection switch and per-face pads (7.10). The separate r4
    candidate removes them in s143's views (7.11), but finer, streaked fur on the toes and inner digits comes with it.
    Adopting it is root's decision. LOD1 and LOD2 would need the same cut and map.
  - **The face's dark broken lines** at LOD0 are its fur cards, whose normals authored normals do not change.
  - Whether to adopt authored normals is root's decision.
  - Root's review of s124's full Guard Front and GuardPaws Below originals (with its 19:48 acceptance of the lane)
    also saw smooth toe surfaces and cuff faceting.
  - The empty fist's C-shaped opening remains: a closure tight enough to shut it fails the fold margin (below 0.22).
  - The body's fur (forearms, tail, feet) and the fur material's response are open.
- **The faceted body and wardrobe** (root, 05:15) are the hero source's blockout primitives. This revision does not
  address them.
- **The generator's nondeterminism** (7.1).
- **The bow, quiver and arrows' socket migration**, and adopting gear_saya_l (candidate 11) in viewmodels.json, are
  root's.
- **No photoreal, visual or runtime acceptance** is claimed for any of this.
