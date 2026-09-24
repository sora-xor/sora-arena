# Fixed-camera bokutō pose probe

This is a **source-only Blender A/B**, using the existing editable Nyaakoto paw
study and the real scanned-white-oak bokutō study. The camera (70° horizontal
FOV, 1600×900), Cycles lighting, geometry, materials, mesh scale `0.75`, and
rotation are identical. Only the local WeaponRoot translation changes:

| Pose | Root (X,Y,Z) cm | Visible grip pixels | Visible paw pixels | Reticle disc |
| --- | --- | ---: | ---: | --- |
| Current | (40,18,−18) | 0 | 0 | clear |
| Proposed | (40,8,−7) | 28,448 | 94,592 | clear |

The visibility counts come from the raw `GripOnly` and `PawsOnly` renders
compared with `Empty_SameCameraAndLight.png`, requiring an RGB channel change
greater than 8/255. In the full proposed frame, 109,184 of 1,440,000 pixels
contain visible asset content. The 80-pixel-radius disc around reticle center
(800,450) contains **zero** changed pixels, and the nearest changed pixel is
114.2 pixels from center. The full current frame only shows the lower-left
bokutō blade sliver. Its grip and paws are entirely outside this source camera.

`Current_Full.png` and `Proposed_Full.png` are the direct visual comparison;
the remaining unedited PNGs isolate grip, paws, full bokutō, and background so
the metrics can be checked. `manifest.json` pins the source and every raw PNG
SHA-256; `metrics.json` pins the mask results. No image was composited,
retouched, cropped, or color-adjusted after rendering.

**Gate:** The translation succeeds at static source framing while keeping the
centre clear. It **does not pass playable or photoreal admission**. The large
white paw forms and plain kote still read as simplified gloves, the weapon
dominates the lower-left, and the 34-pixel margin outside the tested reticle
disc may disappear under bob, windup, attacks, or a different FOV. Blender
does not reproduce Unreal's `FirstPersonScale=0.6`, world occlusion, near clip,
animation, or true UE viewmodel exposure. A packaged first-person fixed-camera
A/B is required before changing `SoraCharacter` or importing this paw asset.

Reproduce from the repository root:

```sh
blender -b --factory-startup --python scripts/art/probe_nyaakoto_bokuto_idle_pose.py
python3 scripts/art/assess_nyaakoto_bokuto_pose_probe.py
```
