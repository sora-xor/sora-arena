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
