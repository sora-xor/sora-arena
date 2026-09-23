# Nyaagyu horse quadruped rig study

This isolated Blender study uses the exact project-owned horse geometry from
commit `d319aad` (verified through Git LFS and SHA-256). It adds a 28-bone
quadruped armature, skin weights on the continuous anatomical shell, separate
hoof and tack bindings, and an in-place 36-frame walk loop at 30 fps. The
original static horse, current gameplay, collision, and Unreal imports are not
changed. The source faces +X, with +Z up and meter units. The source's existing
`Left` named anchors are on -Y; that convention is deliberately preserved.

The pose timing follows a four-beat **left hind, left fore, right hind, right
fore** contact order, supported by the [University of Calgary veterinary
faculty's horse gait explanation](https://vet.ucalgary.ca/summercamps/animal-interactions/tuesday/equine).
The joint angles, stance timing, root motion, and foot clearance are our authored
study. They have not been measured against a living horse or reviewed by an
equine animator. The loop is in place and uses no ground-contact IK.

The saddle has its own `saddle_mount` control. Paired `abumi_L/R` and
`tazuna_L/R` controls retain the original hato-mune stirrup and paired rein
meshes, plus separately named rider-seat, foot, and rein-grip attachment
empties. Those controls are a starting point for rider, stirrup and rein
integration; the straps and reins are presently rigid, without simulated
tension or contact. The modeled hato-mune abumi form and approximate size come
from [the Met's Sanemitsu pair](https://www.metmuseum.org/art/collection/search/712927).
The exact user-provided SORA SVG mon remains on both saddlecloths and both
stirrup fronts; [the Met's earlier abumi pair](https://www.metmuseum.org/art/collection/search/35376)
documents the historical location of a mon, though the SORA symbol is fictional.

Regenerate and validate with Blender 5.2 LTS:

```sh
blender -b --factory-startup --python scripts/art/create_nyaagyu_horse_rig_study.py
blender -b Content/SourceArt/Horses/Nyaagyu/RigStudy/Nyaagyu_Horse_RigStudy.blend --python scripts/art/validate_nyaagyu_horse_rig_study.py
```

The generator extracts the pinned `.blend` from Git LFS, so changing the
ongoing horse source cannot silently alter this study. The validator checks
the hashes, all source mesh and mon instances, skinned core, paired tack
controls, independent loop poses, matching first/last pose, and FBX skeletal
round trip. The four rendered review frames are at footfalls 1, 10, 19, 28.

This is **not yet rideable, photoreal, or a historically or biomechanically
verified gait**. The existing horse's visible anatomy, coat and tack finish
remain stylized. A production horse needs a topology and skinning pass based
on equine anatomy, validated hoof trajectories, ground IK, rider-seat and
stirrup interaction, rein dynamics, proper animation transitions, UE skeletal
import and animation blueprint, gameplay/collision work, and in-engine visual
and performance review. This source study makes none of those claims.
