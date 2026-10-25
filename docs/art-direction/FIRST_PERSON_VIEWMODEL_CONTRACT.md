# First-person viewmodel contract (A4), v2

**Status:** contract v2, revised for root's review of `3d01352`
(`viewmodel-contract-3d01352-review`). It is source-only: no runtime code
reads it yet, and nothing is validated in Unreal. The checker is pinhole math
on socket points. Paw-mesh pixels, near-plane clipping of real geometry and
the look need real first-person captures.

## Root's decisions, as applied

1. **Eye-space motion.** The presentation rotation composes right to left,
   all about the WeaponRoot origin (the anchor):

   ```
   Qpresentation = Qaim_presentation * Qaction_eye * Qrest
   ```

   Bob and windup lift translate in eye coordinates. Only the presentation
   rest and state blend. Live gameplay aim (`BowAimOffset`, the shot direction,
   the HUD ray) is never delayed or changed.
2. **The drawn bow replaces the legacy −15° drawing tilt.** Stacked, the
   arrow line misses the reticle at 20 m by 0.659 half-heights (the tolerance
   is 0.02). The checker reproduces that and refuses any `pitch_deg` entry for
   drawing.
3. **Weapons 19 and 20:** their authored meshes are approved once they pass
   import, full socket and material checks, and originals. `Build()`'s
   primitive fallback stays until then. **Weapon 18** is admitted only as a
   package: the bow, its separate arrow `SM_Weapon_18_Ya` (with `Nock` and
   `Tip`), and a string/draw representation (a string bone or a drawn
   variant). Collision, navigation, damage and aim rules don't change.
4. **Sockets on the existing 20-bone rig.** `gear_saya_l` (and the new
   `gear_wakizashi_l`) go on `pelvis`; `gear_ebira` and `gear_yumi_slung` go on
   `spine`, each with its own transform. There are no new bones. Hierarchy,
   bind pose, animation names and Idle/Walk compatibility are preserved.
5. **Gear presence follows the campaign** (below). The lost-gear stretch is
   chapter 3, beats b01–b05, and the recovery is `ch03.b05`, not chapter 1.

**Scope:** first person only. `USoraViewmodelComponent` also serves
world-visible opponents and practice participants. Their `Build()` and
`KernelPose()` transforms stay exactly as today.

## Assumptions the math makes

- **Cameras:** first-person FOV 70°, world FOV 94°, both horizontal at the
  nominal 16:9 aspect. `MaintainYFOV` and effective view rectangles are not
  modelled.
- **Scale:** `FirstPersonScale` 0.6 moves points along their rays, so it never
  moves anything on screen. It matters only for the near plane (10 cm).
- **Mesh scale:** 0.75, as `Build()` uses today.

## Rest poses (`Content/Data/viewmodels.json`)

u and v run from −1 to +1 across the frame. The reticle gap is in
half-heights, against a clear radius of 0.12.

| Pose | Anchor at (cm) | Rotation (°) | Weapons | Anchor on screen | Actions checked |
| --- | --- | --- | --- | --- | --- |
| sword | (40, 10, −10) | (3, −6, 0) | katana, bokken, wakizashi | Grip_R u 0.36, v −0.63; tip gap 0.15–0.22 | strike, windup, sprint |
| dagger | (38, 10, −11) | (10, −10, 0) | tantō | u 0.38, v −0.73 | strike, windup, sprint |
| gun | (32, 11, −10.5) | (−1, −3, 0) | 1, 3, 5, 7, 9, 11, 13–16 | u 0.49, v −0.83, now inside the frame | reload, windup, sprint |
| polearm | (28, 13, −19) | (0, −3, 0) | 12, 17, 19, 20 | forward paw u 0.17, v −0.57 | strike, windup, sprint |
| heavy | (36, 13, −12.5) | (24, 4, 0) | kanabō, forge hammer | u 0.52, v −0.88, was −1.06 (below the frame) | strike, windup, sprint |
| kama | (36, 12, −13) | (20, −8, 0) | kusarigama | u 0.48, v −0.92; chain paw u −0.21 | strike, windup, sprint |
| bow | (45, −15, −12) | (0, 6, −8) | yumi | bow paw u −0.48, v −0.68 | reload (at −10°), sprint |
| bow.drawn | (60, −6, −14) **proposed** | (0.25, 0.1, 0) | yumi while drawing | arrow rest u −0.11, v −0.36 | aim (below) |

Each pose sorts its grips three ways:

- **visible:** inside the frame;
- **partial:** within an edge band down to v −1.35; the sword's left paw on
  the kashira is one;
- **offscreen:** deliberately out of view, with the reason recorded. The
  polearm's rear paw is at the hip; the heavy weapon's second paw is on the
  butt; the drawn bow's string paw is at the cheek.

**Bow reload override.** The yumi reloads at −10°, not the shared −30°. At
−30° the 2.2 m stave's lower limb comes in front of the near plane, and
nocking an arrow tilts the bow only a little. This is presentation only.

**Aim presentation.** The HUD ray lands on screen through the 94° world
camera. Applying the same angle to the bow on the 70° camera puts the arrow
about 1.5× further from the centre. The correction points the drawn arrow at
the screen point (u, v) where the HUD ray lands: the direction
(1, u · tan 35°, v · tan 35° / aspect), with the gameplay ray unchanged.

| BowAimOffset (yaw, pitch) | Same angle on both cameras | Corrected |
| --- | --- | --- |
| (2°, 0°) | 0.027 | 0.013 |
| (0°, 2°) | 0.028 | 0.014 |
| (4°, −3°) | 0.070 | 0.012 |
| (6°, 4°) | 0.101 | 0.018 |

Errors are in half-heights; the tolerance is 0.02. They are measured at the
proposed kai hold below; at the first authored hold they were 0.006–0.011.
At rest the drawn arrow lands 0.001 from the reticle at 20 m.

**The bow's volumes, not only its sockets.** Codex's BowAim originals (720p,
`e237b9f`) showed that the socket checks did not represent the proxy
volumes: a 22 cm grip box and a 13 cm paw cube covered the target.
`scripts/art/yumi_draw.py` checks the authored parts as a **sampled design
envelope** (its `SCOPE`), through this contract's own placement and
projection. The envelope:

- the stave: the generator's own rounded-rectangle section (28 points, tip
  taper), inflated for the nigiri, rattan and hazu;
- the string;
- the nocked arrow and both paws: closed capsules and a sphere;
- each nearest approach less a local sampling margin.

It also checks three things:

- that the stave, arrow and bow paw are visible at full draw;
- that no near-plane crossing (first-person depth × 0.6 beyond 10 cm, so
  16.7 cm before the eye) falls inside the frame;
- the string's length in every frame. The release returns exactly to brace,
  and the string never stretches.

It runs frame by frame through the draw (0.65 s), the hold, the release and
the return, in rest and both bobs. Codex's review of `fa6aa2b` found the first
version passing geometry behind the camera, sampling open cylinders and four
section points, and stretching the string by 1.87 mm in its release
overshoot. Each of those is now a regression test.

It is not the emitted or skinned asset, continuous time or the native camera
path. Rendered poses decide.

**What the envelope found, kept as failing cases in the tests:**

| Hold | Anchor | Result |
| --- | --- | --- |
| The first authored hold | (60, −3, −9.5) | The stave sits inside the 0.12 radius all through the hold. The Grip_L socket alone (0.127) hid it |
| The first candidate | (60, −5, −9.5) | The conservative stave envelope reaches 0.116 in the bob. The **nocked arrow is cut by the near plane inside the frame**, at about (u −0.39, v −0.70), through the draw and the hold |

**Design proposal, for rendered poses to decide: the kai hold (60, −6, −14).**

- **The pose.** At kai the arrow lies at mouth level, under the cheekbone,
  as in kyūdō. Here that puts the arrow 7.75 cm below the eye, rather than
  4.25. The lower hold is what moves the arrow's near-plane crossing below
  the frame. The extra 1 cm left gives the inflated stave margin in the bob.
- **Its screen boxes are widened, and this is a proposal, not a quiet
  relaxation:**
  - Grip_L's v range grows from −0.6 to −0.7, because Grip_L now sits at
    −0.59 and the downward bob would push it out;
  - the Muzzle box becomes u −0.15 to 0 and v −0.45 to −0.1, from −0.12 to 0
    and −0.25 to −0.1. The arrow rest is now at (−0.11, −0.36).
- **Aim:** at rest it lands 0.001 from the reticle at 20 m; the corrected
  offsets miss by 0.012–0.018 (tolerance 0.02).
- **Presentation:** it should follow the draw (`motion.bow_draw_presentation`:
  the target is lerp(bow rest, bow.drawn rest, draw fraction), then blended at
  12/s). Blending to bow.drawn at once cuts the string mid-frame as it passes
  the face.

**Nearest conservative approach with the proposal and the draw-led pose**
(half-heights, in rest and both bobs, through draw, hold and release):

| Part | Nearest approach | Note |
| --- | --- | --- |
| Stave | 0.159 | – |
| Arrow | 0.124 drawing, 0.320 holding | no in-frame cut |
| Bow paw | at least 0.306 | – |
| String | at least 0.60 | – |
| Draw paw | 0.963 | after the release it flies back from the cheek, not with the string |

**Residual, reported plainly:** the draw paw's forearm crosses the near plane
in the frame's bottom-left region (u ≤ −0.82, v ≤ −0.74) for 10 sampled
frames (0.17 s) early in the draw.

**The continuous draw rig.** Production W18 is a skeletal yumi, not a
rest/drawn mesh swap.

- **Bones (28):**
  - one Grip root along +Y, the bow plane's normal. Its rest frame is the
    armature's, and every other bone, lying in the bow's plane, is square to
    it. Along the bow (+Z), the lower limb's bones sat in the singular case of
    Blender's bone-roll matrix, and their rest bases came out up to 9.4e-6 off
    unit length;
  - 12 bones along the upper limb and 8 along the lower;
  - the string's seven (`yumi_draw.string_frames`):
    - Tip_L and Tip_U in the horn hazu, each turning with its straight
      segment;
    - String_Bend_L2, String_Bend_L1, String_Nock, String_Bend_U1 and
      String_Bend_U2, which carry the string round a circular fillet at the
      nock. Its arc length (24 mm) is held at every draw.
- **Draw:** one draw value, 0 to 1, poses them. The limbs follow the solved
  shape at each draw (`yumi_draw.drawn`), the string's unstretched 2.1346 m
  reaching the nock 0.88 m behind the grip. The skinned stave stays within
  1.8 mm of that shape through the draw.
- **The string:** two straight segments and the bend between them. Its
  sections stay square to it, the nakajikake's included, so nothing shears.
  - The v2 rig's translation-only string sheared the serving up to 1.28×.
  - Every island lying on the string, the serving included, rides the string
    bones whole.
  - Every face meets the deformation gate, 25% or 1 mm, with no exception.
- **Release:** the string returns to brace in 0.03 s and holds there. An
  unstretched string can't pass brace. Its few millimetres of vibration are
  not modelled.
- **Sockets:** they keep their committed positions at brace (`Grip_L`,
  `Grip_R`, `Muzzle`, `String_*`, checked to 5 decimals). Grip_R rides
  String_Nock, the apex of the bend. That is where the arrow's nock sits:
  3.4 mm inside the model's sharp V at full draw. The rig record has each socket in both frames, the mesh frame
  and the bone-local offset from that bone's bind matrix. Copy the bone-local
  offset onto the bone, not the mesh-frame point.
- **The take:** `A_Weapon_18_Draw`, 11 keys at 10 fps, so its time in seconds
  is the draw fraction. Between keys, Blender's FBX import and Unreal blend
  each bone's local translation linearly and its rotation by normalised lerp.
  `yumi_draw._deform_at` does the same. Against the exported FBX as Blender
  plays it, at the keys, quarter points and midpoints, it agrees within
  0.71 µm and 8.2e-7 rad (`Rig/Review/W18_rig_playback_blender.npz`).
- **The FBX is in centimetres.** It is an export-only copy of the metre rig:
  the mesh, every bone's head and tail and every location key ×100. No node
  carries a scale, and the header unit is 1 cm. Everything else, the rig
  record included, stays in metres.
  - **Why:** Unreal folds the armature node into the root bone, so a unit
    factor on any node, or Unreal's own unit conversion or import scale, gave
    every bone scale 100 or 10000 (imports 2–6, `data/yumi_rig_ue_imports.json`).
  - **Build checks:** the copy deforms as the metre rig within 0.70 µm. The
    build reads its own FBX back and refuses unless the unit is 1 and the node
    scales, bind and cluster bases are within 1e-5 of 1. The take must be one
    10 fps take of 0–1 s.
  - **Blender's round trip:** the import puts the 0.01 unit on the armature
    object and nothing else.
- **In Unreal 5.8.3** (`scripts/unreal/import_runtime_weapon_yumi_rig.py`, an
  isolated namespace; `Rig/Review/W18_rig_unreal_readback.json`):
  - **Reference pose:** every bone at scale 1 within 1e-7, heads within 8e-6 cm.
  - **Sockets:** five bow sockets on their bones, and the arrow's two from its
    FBX's `SOCKET_` nodes.
  - **The take:** 1.0 s, 11 keys at 10 fps, linear.
  - **Raw playback:** it agrees with `_deform_at` within 6.1e-5 cm and
    1.1e-6 rad, given one engine rule. A bone whose evaluated local transform
    `Equals` its reference pose within 1e-4 per component comes back as the
    reference pose (`AnimSequencerDataModel.cpp:1389`; LimbU_01 near brace,
    LimbL_01 at 0.025 s). The test models that rule, and asserts it snaps
    exactly the samples the model predicts.
  - **Compressed playback:** ACL at its defaults (0.01 cm error, 3 cm virtual
    vertices) stays within its bound: 8.7e-3 cm and 3.3e-3 rad, against 0.021 cm
    and 7.1e-3 rad.
  - **Not yet established:** this is asset readback only, not a capture or a
    gameplay admission.
- **Check geometry:** only `sora-yumi-rig-check-v3` (bind and per-key pose
  matrices of the 28-bone rig) is accepted. Earlier rigs are archived
  evidence, never admitted:
  - `data/yumi_rig_b55fe81.json`;
  - the schema-2 attempt, with its string-to-stave webs:
    `data/yumi_rig_schema2_attempt.json`;
  - the serving-exception attempt: `data/yumi_rig_schema2b_attempt3.json`.

## Sockets

- **Translations:** from each weapon's build record (`assets.<mesh>.sockets`,
  Blender metres, +Y the wielder's left).
- **Rotations:** build records don't store them. Two grips rotate their axes,
  and the contract lists them with the builder call quoted verbatim, which the
  checker re-finds. Every other *grip* uses the builder default; other sockets
  (several Muzzle tips, the saya Koiguchi) can rotate too and come from the
  imported mesh, since no paw attaches there:
  - the kusarigama's `Grip_L`: x (0, 0, −1), z (1, 0, 0);
  - the micro-mortar's `Grip_R`: x (0, 0, 1), z (−1, 0, 0).

  Every other grip uses the builder default.
- **Paws** attach to the **imported** socket's full transform, with the
  matching local grip frame and the inherited 0.75 scale. A source FBX is not
  an imported or accepted mesh.
- **Approximate sockets:** `SM_Nyaagyu_HeroKatana`, `SM_Nyaagyu_DojoBokken`
  and `SM_Nyaagyu_ArcCarbine` have approximate `sockets_m` until I author
  their `SOCKET_` empties with full transforms.

## Hero gear

**Reconciliation:** one idempotent pass, rebuilding the gear components to
match:

- **Presence:** an item appears only for an active campaign hero, when its
  weapon is both unlocked (`IsWeaponUnlocked(id)`) and allowed by the task
  (`SoraBeatRules::EquipmentAllows`: the equipment mask, or
  `EquipmentRecovered`). Allowance alone would show the wakizashi in
  chapter 2, before its `ch03.b01` unlock.
- **Arrow count:** `WeaponId == 18 ? Equipment->Ammo : AmmoByWeapon[18]`, since
  a held bow spends live `Ammo` and `AmmoByWeapon[18]` only catches up on a
  switch.
- **When it runs:** at beat start and checkpoint restart, chapter select,
  recovery completion, weapon change and ammo change.
- **What it does:** creates each missing item component and destroys each
  absent one. Nothing is hidden by toggling visibility, and nothing is shown
  both held and slung or sheathed.

**Recovery, `ch03.b05`:**

- the hero interacts with `act_b05_dry_well_rope` to raise the
  `sword_bundle` from 700 cm down, and strings the bow for 3,000 ms;
- weapons 0, 4 and 18 are granted, with 12 arrows;
- beforehand, b01–b05 allow only weapon 4.

**Bodies:** `SK_NyaagyuSamurai` and the non-skeletal fallback body are both
rebuilt without their built-in `Saya_`, `Sageo_`, `Katana_`, `Ebira_`, `Ya_`
and `Yumi_` parts, and the primitive quiver fallback goes.

**Sockets:** component-space bind-pose transforms, which the authoring step
converts to bone-relative ones:

| Socket | Bone | Bind position (cm) | Rotation (°) | Source |
| --- | --- | --- | --- | --- |
| gear_saya_l | pelvis | (17, −25, 95) | (0, 180, 0) | today's `BuildHeroSaya` |
| gear_wakizashi_l | pelvis | (13, −19, 98) | (0, 180, −6) | new: inboard and above, as a daishō is worn |
| gear_ebira | spine | (−23, 25, 116) | (−14, 0, 0) | today's primitive quiver |
| gear_yumi_slung | spine | (−16, 2, 122) | (0, 0, 32) | new: diagonal across the back |

**Items:**

| Item | Present when | Held | Not held |
| --- | --- | --- | --- |
| Katana | weapon 0 allowed | empty `SM_Nyaagyu_HeroSaya` | the saya with `SM_Nyaagyu_HeroKatana` seated at a Koiguchi socket (to author) |
| Wakizashi | weapon 4 allowed | empty `SM_Weapon_04_Saya` | the saya with `SM_Weapon_04` at its Koiguchi |
| Ebira | weapon 18 allowed | — | — |
| Yumi, slung | weapon 18 allowed and not held | — | `SM_Weapon_18` |

The ebira is `SM_NyaakotoGear_Ebira` (to author from the body's ebira
parts), plus one `SM_Weapon_18_Ya` instance per arrow in hand. An empty quiver
keeps zero instances.

**Tests for root:**

- recovery at `ch03.b05`;
- checkpoint restart before and after the recovery;
- chapter select into chapter 3 and later;
- no wakizashi in chapter 2, before its `ch03.b01` unlock;
- the held bow's quiver emptying live as arrows are shot;
- no item both held and slung or sheathed;
- an empty quiver.

## Checker

`scripts/art/check_viewmodel_framing.py [--table] [--root DIR]` passes all
22 weapons with 1,177 checks, against both my tree and root's `6e951e5`
(`--root`). The checks by category:

| Category | Checks | What it covers |
| --- | --- | --- |
| schema | 194 | blocks, version, poses and states; drawing tilt not stacked |
| completeness | 24 | exactly the catalog's 0–20 plus the bokken; unique ids and keys; names match |
| reference | 80 | records, keys, mesh assets, needed sockets |
| provenance | 4 | rotated-socket calls and axes |
| screen | 249 | |
| reticle | 66 | |
| envelope | 68 | |
| near-plane | 486 | including the aim-offset placements |
| aim | 6 | |

`--table` also prints each weapon's status from the current tree: socket
source, and whether the runtime manifest lists it. It never establishes
import or visual status.

**Tests:** `scripts/art/test_viewmodel_framing.py`, 11 tests. They cover the
committed contract, plus every reproduced gap:

- empty, short or duplicated tables;
- a wrong mesh or a missing socket;
- stale provenance;
- the heavy grip below the frame;
- a stacked drawing tilt, and a drawn bow that misses;
- the bow reload clipping its stave;
- the same-angle aim error against the corrected one;
- today's (40, 18, −18) root, and a blade through the reticle.

## Root integration (your code; I don't touch WeaponRoot)

1. **Load.** For the first-person hero only, `RestLocation()` becomes a
   per-weapon lookup into `viewmodels.json`. `Sway()` and `KernelPose()` apply
   their offsets in eye space about that rest, and the drawn bow drops the
   −15° tilt.
2. **Attach.** `Build()` hangs the mesh from its anchor socket, and attaches
   the paws to the imported sockets' full transforms.
3. **Aim.** Correct only the drawn arrow's presentation toward the HUD ray's
   screen point.
4. **Gear.** Reconcile gear components as above.

## My deliverables (each needs the shared Blender lane)

- the paw meshes in the pose table;
- `SOCKET_` empties with full transforms on the three original meshes, and a
  Koiguchi socket on the hero saya;
- the body rebuilt without gear, and the four gear sockets;
- `SM_NyaakotoGear_Ebira`;
- the yumi's continuous skeletal draw rig (above), and the yugake paw.

## Validation after integration (your lane)

- **Captures:** first-person originals at 720p and 1080p, SM6 and SM5, for
  each pose at rest and in its actions. The bow needs both its rest and its
  drawn state, against the real HUD ray.
- **Pass criteria:** the paws visible, no near-plane clipping, and every frame
  looked at.
- **Stealth and bow tests:** existing tests stay; only the presentation
  expectations change.
- **Gear checks:** the gear-presence tests above.

The capture numbers win over the pinhole math, and the contract is then
updated to match.
