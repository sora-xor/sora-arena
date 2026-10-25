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
   arrow line misses the reticle at 20 m by 0.654 half-heights (the tolerance
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
| bow.drawn | (60, −3, −9.5) | (0.25, 0.1, 0) | yumi while drawing | arrow rest u −0.04, v −0.18 | aim (below) |

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
| (2°, 0°) | 0.031 | 0.006 |
| (0°, 2°) | 0.034 | 0.007 |
| (4°, −3°) | 0.069 | 0.006 |
| (6°, 4°) | 0.107 | 0.011 |

Errors are in half-heights; the tolerance is 0.02.

## Sockets

- **Translations:** from each weapon's build record (`assets.<mesh>.sockets`,
  Blender metres, +Y the wielder's left).
- **Rotations:** build records don't store them. Two grips rotate their axes,
  and the contract lists them with the builder call quoted verbatim, which the
  checker re-finds:
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

- **Inputs:** `SoraBeatRules::EquipmentAllows` (the task's equipment mask, or
  `EquipmentRecovered`), the held `WeaponId`, and `AmmoByWeapon[18]`.
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
- the yumi string/draw representation, and the yugake paw.

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
