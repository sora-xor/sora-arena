# First-person viewmodel contract (A4)

**Status:** proposal for root integration. No runtime code reads it yet, and
nothing is validated in Unreal. The numbers come from projection math, which
real first-person captures must confirm.

## The problem

`USoraViewmodelComponent` holds every weapon at one rest offset, (40, 18, −18)
cm from the eye. Three places hard-code that offset:

- `RestLocation()`;
- `Sway()`, which adds a walking bob;
- `KernelPose()`.

At the first-person FOV of 70° (16:9), (40, 18, −18) projects to u = +0.64,
v = −1.14: the grip sits below the frame. That is why the paw studies drew 0
pixels. `FirstPersonScale` moves points along their rays, so no scale value
brings them on screen. The one rest also serves a katana, a 2.2 m yumi and a
1.85 m naginata.

## Source of truth: `Content/Data/viewmodels.json`

The file sits next to `catalog.json`. `Data` is already staged as NonUFS, so
`ReadJson` can load it. It holds:

| Block | Holds |
| --- | --- |
| `camera` | the first-person FOV, aspect, `FirstPersonScale`, near plane and a reticle clear radius |
| `mesh_scale` | 0.75, as `Build()` uses today |
| `motion` | today's bob, pitch, roll and kernel-windup magnitudes, unchanged, now applied about each weapon's rest; plus a proposed `blend_per_s` so poses stop snapping |
| `poses` | eight poses: `sword`, `dagger`, `gun`, `polearm`, `heavy`, `kama`, `bow` and `bow.drawn`. Each has an anchor socket, a rest transform (`anchor_cm` in eye space; `rotation_deg` as FRotator pitch, yaw, roll), screen boxes for its visible sockets, a reticle line, and the paw mesh for each grip socket |
| `weapons` | all 22 first-person weapons: 0–20 plus the dojo bokken. Each gives its pose and first-person mesh, and its sockets: from the runtime build record, or approximate `sockets_m` where the mesh has no authored sockets yet |
| `hero_gear` | the separate gear meshes, body sockets and the presence rule (below) |

The **socket frame** matches the runtime weapon builders
(`create_runtime_weapon_specs.py`):

- Blender metres, +X the line of action, +Z up, +Y the wielder's left (UE's
  FBX import flips Y);
- `Grip_R` is the right paw's hold, and the mesh origin for every runtime
  weapon except the yumi, whose origin is `Grip_L`;
- `Muzzle` is the business end.

## The rest poses

`scripts/art/check_viewmodel_framing.py` projects every socket. Run it with
`--table` for each weapon's numbers. It passes all 22 weapons and 68 checks
(screen boxes, reticle clearance, the near plane, and the drawn bow's aim).
u and v run from −1 to +1 across the frame, and the reticle gap is measured in
half-heights against a clear radius of 0.12.

| Pose | Anchor at (cm) | Rotation (°) | Weapons | Where it sits |
| --- | --- | --- | --- | --- |
| sword | (40, 10, −10) | (3, −6, 0) | katana, bokken, wakizashi | chūdan. Right paw at u 0.36, v −0.63; tip just under the reticle (gap 0.15–0.22) |
| dagger | (38, 10, −11) | (10, −10, 0) | tanto | one paw; point forward and up, gap 0.39 |
| gun | (32, 11, −12) | (1, −3, 0) | 1, 3, 5, 7, 9, 11, 13–16 | hip carry. Trigger paw at the bottom edge (v −0.95), bore converging on the reticle |
| polearm | (28, 13, −19) | (0, −3, 0) | 12, 17, 19, 20 | rear paw below the frame, forward paw at u 0.17, v −0.57, point under the reticle |
| heavy | (36, 13, −15) | (26, 4, 0) | kanabō, forge hammer | head raised on the right |
| kama | (36, 12, −13) | (20, −8, 0) | kusarigama | sickle low right, chain paw low left |
| bow | (45, −15, −12) | (0, 6, −8) | yumi | bow paw low left (u −0.48), the stave crossing the left of the frame |
| bow.drawn | (60, −3, −9.5) | (0.25, 0.1, 0) | yumi while drawing | arm extended, stave just left of the reticle; the arrow line hits the reticle at 20 m within 0.006 |

The blade pose matches your approved (40, 10, −10) and pitches the blade 3° up
and 6° in. The yumi has its own left-hand arrangement, as you asked.

## Root integration (your code; I don't touch WeaponRoot)

1. **Load.** `RestLocation()` becomes a per-weapon lookup into
   `viewmodels.json`. `Sway()` and `KernelPose()` add their existing offsets to
   that rest, rotating after the rest rotation, instead of rebuilding
   (40, 18, −18). Blending at `blend_per_s` removes the snaps.
2. **Attach.** `Build()` gives the first-person mesh a relative location of
   −`mesh_scale` × the anchor socket (converted to UE centimetres), so the
   anchor sits on the WeaponRoot origin. Most runtime meshes are already
   origin = `Grip_R`. Each paw mesh in the pose's `paws` attaches to its
   socket on the weapon mesh, as an owner-only FirstPerson primitive. Today's
   `FurPaw` cube goes.
3. **Bow.** While `IsBowDrawing()`, blend from `bow` to `bow.drawn`, and keep
   `BowAimOffset()` on top. The static yumi can't show a drawn string; that
   needs a string bone or a drawn variant (mine, below).
4. **Weapons 18–20.** They still draw primitives in `Build()`, though
   `SM_Weapon_18/19/20` exist and carry sockets. Admitting those is your call.
5. **Gear.**
   - The rule: each carried item is its own component, created while the
     campaign state grants it and destroyed when it's lost. Chapter 1's
     lost-gear opening then contains no gear geometry at all, hidden or
     otherwise.
   - Today, `SetCampaignGearVisible` only toggles visibility, and the body
     mesh has its own saya, ebira, ya and yumi built in (so the saya draws
     twice).
   - The new sockets on the rebuilt body: `gear_saya_l` (pelvis),
     `gear_ebira` (spine_01), `gear_yumi_slung` (spine_03).

## My deliverables

- **Paws:** `SM_NyaakotoFP_Paw{R,L}_*`, one per grip in the poses: Tsuka,
  Tanto, Stock, Fore, Shaft, Chain, Yumi, Yugake.
  - Each mesh's origin is the contact point, with X along the handle, so it
    drops onto the weapon socket.
  - They're built from the existing grip studies (`NyaakotoFirstPersonPaws`,
    `NyaakotoBokutoViewmodel`), which fail admission today.
- **Weapon sockets:** authored `SOCKET_` empties on `SM_Nyaagyu_HeroKatana`,
  `SM_Nyaagyu_DojoBokken` and `SM_Nyaagyu_ArcCarbine`, replacing the
  contract's approximate `sockets_m`.
- **Hero:** `SK_NyaagyuSamurai` rebuilt without gear and with the three body
  sockets.
- **Gear meshes:** `SM_NyaakotoGear_Saya`, `_SayaKatana`, `_Ebira`,
  `_EbiraArrows` (one arrow, instanced per remaining arrow) and `_YumiSlung`.
- **Bow:** a yumi string bone or a drawn variant, plus the yugake draw paw.

All of it needs the shared Blender lane.

## Validation after integration (your lane)

- **Captures:** first-person originals at 720p and 1080p, SM6 and SM5, for
  at least one weapon per pose: katana, bokken, tanto, arc carbine, yari,
  kanabō, kusarigama, and the yumi at rest and drawn. Take each at rest and
  in the bob, strike, reload and windup offsets.
- **Pass criteria:** the paws visible; the tip outside the reticle zone; no
  near-plane clipping; every frame looked at.
- **Gear check:** at chapter 1's lost-gear beat, the hero has no gear
  components.
- **Framing check:** `check_viewmodel_framing.py` is pinhole math, so the
  capture numbers win where they disagree, and the contract is then updated
  to match.

Tests: `python3 -m unittest scripts/art/test_viewmodel_framing.py`. It checks
that the committed contract passes and that three known failures are caught:
today's root putting the grip off-screen, a blade through the reticle, and a
drawn bow that misses.
