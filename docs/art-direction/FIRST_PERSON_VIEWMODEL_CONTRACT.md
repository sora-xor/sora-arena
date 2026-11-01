# First-person viewmodel contract (A4), v2

**Status:** contract v2, revised for root's review of `3d01352`
(`viewmodel-contract-3d01352-review`), with the gear truth correction in
`47d81a5`. Guarded first-person runtime now reads the table; this source candidate
has not been built or validated in Unreal. The checker is pinhole math
on socket points. Paw-mesh pixels, near-plane clipping of real geometry and
the look need real first-person captures.

The implementation applies the contract only after a loaded weapon mesh has its
expected package identity, geometry, generated materials, and finite full imported
`Grip_R`, `Grip_L` and `Muzzle` sockets. It recenters the mesh using the anchor's
translation while preserving every socket's rotation and scale for attachment
readback. The approximate katana/bokken/carbine sockets do not qualify. Authored
weapons 18–20 remain disabled pending separate import/original capture admission.
No paw or carried-gear assets are created by this implementation.

The existing primitive bow has a separately labelled presentation fallback. Its
actual `YumiGrip` center `(7,0,-5)` is the pivot; its geometry is unchanged. The
table moves that pivot through rest, drawn and reload states. This does not prove
the fallback matches authored framing or that arrow pixels meet the reticle.
`SoraCapture.BowAim.Live` records that distinction and checks the current native
first-person projected direction independently from the unchanged HUD/shot ray.

Runtime correction reads the actual camera's `FMinimalViewInfo` and calls
`TransformFirstPersonToWorld` rather than assuming the nominal 94°/70° FOV pair.
Only rest/action/anchor transitions blend. The live aim direction remains current
on the first transition frame. The contract's 2–6° aim inputs are stress cases;
gameplay sway is bounded at 0.18° pitch and 0.28° yaw.
The camera snapshot covers the game's explicitly perspective camera component;
XR and custom camera-manager modifications are outside this qualification. UE's
disabled additive transform defaults to identity with zero FOV offset, and
`ClearAdditiveOffset` restores both. Unadmitted meshes recover the gameplay
offset using their attached eye component, so an additive camera rotation cannot
counter-rotate their legacy pose.

Pending engine checks: `SoraArena.Presentation.ViewmodelContract`,
`SoraArena.Presentation.ViewmodelProjection`,
`SoraArena.Presentation.ViewmodelBowTransitions`, the existing `BowAimSway` and
`BowAimCancellation` tests, and fresh 720p/1080p `SoraCapture.BowAim.Live` originals.
Host framing checks remain a source model, not rendered acceptance.

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
  - **Raw playback, two separate results:**
    - **Canonical:** against `_deform_at` at the fixed bound (1e-3 cm,
      1e-5 rad), it FAILS on 8 of 1,148 samples: LimbU_01 from 0.075 to
      0.225 s and LimbL_01 at 0.025 s, at most 5.92e-5 rad and 8.9e-5 cm.
      Every one of them came back as its bone's reference pose exactly.
    - **Snap-aware:** an observed engine rule, modelled. A bone whose
      evaluated local transform `Equals` its reference pose within 1e-4 per
      component comes back as the reference pose. The rule predicts exactly
      the 10 snapped samples. With it, playback agrees within 6.1e-5 cm and
      1.1e-6 rad. The rule's maximum deviation is √3·1e-4 cm and
      4·asin(1e-4) rad.
    - **Source not located:** the take uses `AnimationSequencerDataModel`
      with an FKControlRig in Direct mode (its asset). The one site found
      with the rule, `AnimSequencerDataModel.cpp:1389`, runs only when the
      pose's reference skeleton differs from the model skeleton's. That
      branch does not apply to this AnimPose path, whose skeleton-built
      container shares the skeleton (`BoneContainer.cpp:156-158`).
  - **Compressed playback:** 8.7e-3 cm and 3.3e-3 rad, within the bound of
    0.021 cm and 7.1e-3 rad. The bound is ACL's own at its class defaults
    (0.01 cm error, 3 cm virtual vertices, no stripping) plus the snap's
    maximum.
    - **Those settings are inferred, not read:** every runtime property read
      fails (Python sees only the codec's base class; the errors are kept in
      the readback), and the settings asset serializes no tag for them.
  - **Not yet established:** this is asset readback only, not a capture or a
    gameplay admission.
  - **The bow drew Unreal's default material.** The saved `SK_Weapon_18`
    package binds its slot to `/Engine/EngineMaterials/WorldGridMaterial` and
    never references `MI_W18_Weapon`. That is why the first lit capture shows
    a grey bow. The importer wrote the transient `Materials` array with
    `set_editor_property` while the mesh's async build ran (SkeletalMesh.h
    declares it `transient`; `SetMaterials` waits for the build,
    SkeletalMesh.cpp:733-740).
    - **The fix, not yet run:** finish compilation, bind through
      `SetMaterials`, and check the binding in memory before and after the
      save. The saved package must name the instance and not the default.
      That byte check is supporting evidence only.
    - **Python has no `set_materials`.** A property's `BlueprintSetter` is
      bound to its attribute, never a method, so the importer assigns
      `mesh.materials`, whose setter is `SetMaterials` (`dcb99b1`). The W18
      rebuild's step 7 attempt 0 (2026-10-25) stopped on the missing method,
      after the import and before any binding or readback.
    - **An `unreal.Array` hands out copies.** Indexing and iterating
      Pythonize each struct element as a copy (`PyWrapperArray.cpp:409-426`,
      `EPyConversionMethod::Copy`). So editing the slot a loop yields leaves
      the array unchanged.
      - Attempt 1 wrote the unchanged array back through `SetMaterials`, and
        its binding check read `WorldGridMaterial`.
      - The first imports' loop did the same. That alone accounts for their
        grey package; the async build was not needed to explain it.
      - The importer now keeps each edited copy and writes the copies back
        (not yet run).
    - **The proof:** `scripts/unreal/verify_yumi_rig_materials.py`, in a
      fresh editor before any capture. It reads back every slot of the bow,
      the arrow and the paw from disk, and what spawned components draw. None
      may be an engine default.
    - The arrow was bound correctly all along: its static slot uses
      `set_material`.
- **The first lit first-person originals** (`scripts/unreal/render_yumi_fp_review.py`,
  `Saved/YumiFP/`, editor review originals only):
  - **Attempt 0:** failed. `update_animation_in_editor` can't be set as a
    property; the script now uses its setter.
  - **Attempt 1:** exit 0, but unusable.
    - It was nearly black: a 9-lux key at EV100 8.5, about six stops under.
    - The paw was missing: a Static component can't attach to the movable
      bow.
    - The arrow sat at full draw on a braced bow: set_position alone never
      re-evaluated the bones.
  - **Attempt 2:** all four holds written and their hashes recorded. Then the
    editor crashed in static teardown at exit (a Slate notification's ICU
    free). Its crash handler hung on the WindowServer, and I terminated it with
    root's authorization (SIGTERM, then SIGKILL; editor 137, wrapper 1). So it
    is a **manually terminated, failed run**.
    - Its gates passed: Grip_R within 6.8e-5 cm of the review's full draw
      (bound 0.0212 cm), and the paw on Grip_L.
    - **What the originals show:** correct exposure and attachment, and a
      clear rest and full-draw distinction. They also show the grey
      default-material bow, stiff spiky fur, a large bald pad strip, glossy
      cloth and splints, and a plastic-looking arrow (root's review agrees).
      None of it is accepted.
  - **Gates the capture now applies:** the take is evaluated on the game
    thread, and the posed Grip_R and Muzzle must match the review. Exposure
    is metered from the sun (the incident-meter equation).
  - **Its material gate** is `fp_material_bindings`, shared with
    `verify_yumi_rig_materials.py`. It reads ordered rows: (index, slot,
    path) for each asset, (index, path) for each component. These are checked
    against the serialized expectations
    (`data/fp_material_bindings.json`):
    - each asset has exactly its expected slot count and names, each bound to
      its own material;
    - each component index draws its asset's slot at that index, so a swapped
      override fails, though its sorted paths would pass (Codex);
    - no engine default anywhere.
    `test_fp_material_bindings.py` tests the check on the host.
- **The right-cheek comparison** (prepared for the next originals; not run):
  - The next capture shoots root's `bow.drawn` control (60, −3, −9.5)
    beside a named `right_cheek` hold. Both are pinned with their sources'
    hashes in `data/yumi_fp_hold_study.json`; root's viewmodels.json stays
    unchanged.
  - `right_cheek` is Codex's construction (`scripts/art/yumi_fp_holds.py`):
    - keep the control's full-draw nock X and Z, mirror its Y to +3.115 cm;
    - roll 0, with the posed nock-to-Muzzle line through (2000, 0, 0);
    - the anchor puts the nock on its target.
  - The closed-form solve reproduces Codex's candidate from the signed
    sockets to machine precision.
  - The capture **re-solves it from the sockets it actually poses**, so
    rebuilt sockets get their own hold. It gates the nock on its target and
    the arrow through the aim point.
  - `test_yumi_fp_holds` requires a candidate for the current sockets
    file's hash, so a rebuilt sockets file forces a recomputed entry.
  - Root's left-side screen boxes do not admit the candidate's grip
    (u > 0). That is recorded and not relaxed.
  - **What the capture records**, socket math only, never a gate:
    - screen points against those boxes;
    - the clear line's distance from the reticle;
    - the arrow's miss at 20 m;
    - how much of the arrow lies nearer than the 10 cm near plane (the
      full-draw nock is 5.8 cm behind the eye);
    - each part's nearest extent.
  - **The ID pass:** after each eye-view shot, each part is drawn unlit in its
    own colour, alpha masks kept, with the set hidden. Then the material gate
    runs again. `scripts/art/analyse_yumi_fp_review.py` counts the real
    pixels:
    - each part's share and screen extent;
    - its frame-edge contact;
    - its pixels inside the reticle's clear disc (0.12 half-heights).
- **W18 source corrections** (Codex-assigned; source only, **not rebuilt**):
  - **The nigiri** (`scripts/art/yumi_nigiri.py`):
    - **The fault:** the grip wraps read as stepped plates. The first
      generator lapped a 19 mm, 1.1 mm strip by shearing its whole section
      (tilt 0.29), so every turn sat about 16° askew: a plate stepping up to
      3.8 mm at each seam.
    - **Now:** a 2.8 mm built-up underlay wound with one 13 mm, 0.6 mm
      skived deerskin strip at 30% overlap. Its section spans one 9.1 mm
      pitch, so the turns butt into one surface. The seam steps only the
      skived edge (0.22 mm), the lap crests at 0.45 mm and drapes flat. The
      strip runs on over the shoulders and covers ±40.4 mm at every angle.
    - **Girth:** the outer leather stands 3.85 mm off the stave, inside the
      4 mm first-person envelope and at the girth the paw is carved to.
    - `wound_strip` now refuses laps.
  - **The ya** (`scripts/art/yumi_ya.py`, `mat_bamboo`):
    - **The fault:** the shaft was lacquered (roughness about 0.25), without
      node bands, its mottling barely varying along its length: uniformly
      yellow plastic.
    - **Now:** polished bare yadake at roughness about 0.42. Four nodes are
      each placed within 12 mm of their kyūdō positions, raised 0.30–0.50 mm,
      with sharper nock-side ridges, finely sampled. The node bands and
      sheath scars sit at the nodes' own places. There is fire-straightening
      scorch (heavier at the nodes, a little rougher) and a tone of its own
      for each internode.
    - The new `mat_bamboo` options are off by default, so the four other
      bamboo weapons bake as before.
  - **Contracts, on the host now:**
    - `test_yumi_nigiri_ya.py`: the seam step and flat turns; both
      envelopes; the paw's girth within its carve gap and its digits inside
      the covered span; the nodes, envelope and ridge sampling; the hash is
      the generator's.
    - `test_nyaakoto_fp_paws.Grip`: the rig's emitted leather (99th
      percentile) within CARVE_GAP of `GRIP_WRAP`. It passes on the current
      rig, and the rebuilt rig must pass it too, or the paw's grip is updated
      and the paw rebuilt.
    - `Rebuild.test_the_rig_was_built_from_the_current_w18_sources` is an
      **expected failure** on purpose. The committed static bow, LODs, atlas
      and rig predate the change. The rig record now pins every W18 source,
      and the rebuild's commit must remove the marker.
  - **The rebuild chain**, in the engine lane, each step's originals archived
    with hashes before it runs:
    1. the static W18 (FBX, LOD1/2, atlas, build record, renders);
    2. the rig (`create_runtime_weapon_yumi_rig.py`, its check geometry and
       record);
    3. its grey review;
    4. the host tests (rig sockets, scale and playback; the grip contract;
       the rebuild marker removed);
    5. the Unreal rig import;
    6. the paws (their grip re-measured if the contract fails);
    7. the fresh-editor material proof;
    8. new first-person originals.
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
