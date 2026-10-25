# Dojo room readability: diagnosis and proposal

**Status:** proposal for root review. None of it is implemented, and none of it
is photoreal acceptance. It builds on A2's per-beat sun and sky
(`SoraWorldBuilderLighting.cpp`, integrated as `e3b8aa5`) and changes nothing
in A2.

## What the originals show

I measured the original capture PNGs with
`scripts/art/analyze_capture_luminance.py`. Luma means Rec. 709 luminance,
sRGB-encoded, 0–1; 0.18 linear encodes as 0.46. "Clip" is any channel
at 254 or more. R/B is mean linear red over mean linear blue, where 1.0 is
neutral.

ArtReview at `184a7b6` (old kit, A2 beat `ch01.b02`, overcast, 1920×1080).
SM5 is within ±0.1 EV of SM6 in every view:

| View | Median luma | p05 | Ceiling / walls / floor thirds | Clip | R/B |
| --- | --- | --- | --- | --- | --- |
| Entry_East | 0.185 | 0.093 | 0.13 / 0.25 / 0.19 | 3.3% | 3.2 |
| Kamiza | 0.183 | 0.063 | 0.13 / 0.25 / 0.19 | 6.8% | 2.8 |
| South_Shoji | 0.103 | 0.044 | 0.08 / 0.20 / 0.10 | 3.8% | 4.3 |
| Ceiling | 0.063 | 0.033 | 0.04 / 0.06 / 0.09 | 0.7% | 6.3 |
| West_Back | 0.150 | 0.068 | 0.10 / 0.21 / 0.16 | 2.4% | 5.9 |
| Floor_Light | 0.203 | 0.094 | 0.22 / 0.19 / 0.20 | 3.7% | 3.9 |

NaniteDraw entry view (1280×720), conventional kit `6e0e99c` against the
Nanite kit `a8ecee6`:

| Mode | Median luma | Floor third | Median EV change |
| --- | --- | --- | --- |
| SM6 | 0.142 → 0.096 | 0.152 → 0.087 | −0.93 |
| SM5 | 0.151 → 0.096 | 0.161 → 0.089 | −1.07 |

In the ceiling view of the same pair, crushed pixels (luma ≤ 0.03) rise from
7–9% to 12–14%.

## Diagnosis

1. **The eye adaptation probably cannot open up indoors.** This is a strong
   hypothesis, still untested.
   - The project doesn't set
     `r.DefaultFeature.AutoExposure.ExtendDefaultLuminanceRange`, and the
     engine default is 0 (`SceneView.cpp`). So the legacy range applies:
     `AutoExposureMinBrightness` 0.03 and `HistogramLogMin` −8
     (`Scene.cpp`; `PostProcessEyeAdaptation.cpp` clamps the white point to
     the minimum).
   - The global grade overrides only the method, percentiles, speeds and the
     −0.45 bias.
   - What the measurements show fits this:
     - every view's median (0.06–0.21) is far below the roughly 0.40 that
       converged histogram adaptation aims for (0.18 × 2^−0.45, before the
       tone curve), in SM5 and SM6 alike;
     - the Nanite kit's darker GI (Codex's SDF and card findings) comes
       through almost one to one, about 1 EV, with no adaptation absorbing it.
2. **One value for everything.** Walls, ceiling, floor and the timber frame
   are all a mid-dark reddish brown. Little bounce comes back, and the planes
   don't separate; the thirds above differ by 0.12 at most.
3. **Monochrome orange:** R/B is 2.8–6.3 even in the overcast b02 beat. Warm
   lamps and reddish albedo dominate, and no cool daylight component comes
   through the shoji.
4. **Clipped highlights:** 0.7–6.8% of each frame, mostly the engawa doorway,
   the shoji panes and the lamp heads.
5. **The ceiling is a repeated motif** (a mon on every coffer) and the
   darkest plane.

## What stays fixed: gameplay light

`USoraStealth::LightAt` counts only two things:

- the brightest `UDirectionalLightComponent`'s intensity;
- `UPointLightComponent`s (spots included) on `ALight` actors, by distance
  against `AttenuationRadius`.

Exposure, tonemapping, sky light, rect lights, emissive surfaces and materials
never enter it, and the player reads stealth light from the HUD meter.

Nothing below changes any of these:

- the 25 lux estate key or the A2 per-beat table;
- any lamp's position, intensity or radius;
- the sky's 0.65, the fog's 0.0045 or the global −0.45 bias.

No point or spot light is added.

## Proposal, in order

Each step ships on its own and is measured before the next.

### 1. Diagnostic (root lane, no source change)

Rerun `SoraCapture.ArtReview.Dojo` in SM6 and SM5 with the extended range set
at startup:

```
-ini:Engine:[/Script/Engine.RendererSettings]:r.DefaultFeature.AutoExposure.ExtendDefaultLuminanceRange=1
```

The extended range's defaults (min and max EV100 −10 and 20) remove the clamp.

- **If the clamp is the cause:** the medians rise by about 2–3 EV towards
  0.35–0.45, and the windows and lamps clip more.
- **If the medians barely move:** diagnosis 1 is wrong, and I'll revise.

Either way, please log the eye-adaptation exposure at each frame. ArtReview
settles 3.4 s, at adaptation speeds of 1.2 EV/s up and 0.7 EV/s down, so a
large change may not have converged.

### 2. Interior exposure per hall (my file: `SoraWorldBuilderDojoHall.cpp`)

In `HallInterior`, add one actor per hall: a `UBoxComponent` the size of the
hall rect, with a `UPostProcessComponent` child. Settings:

- `bUnbound` false, priority above the global grade, blend radius 150 cm at
  the doorways;
- `AutoExposureMinBrightness` lowered so the eye adapts indoors, with the
  value taken from step 1; the bias is inherited, never overridden;
- local exposure: `HighlightContrastScale` 0.6, `ShadowContrastScale` 0.85,
  `DetailStrength` 1.0 (the default bilateral method). This holds the panes
  and lamp heads without flattening the room.

The alternative to the per-hall override is the extended range project-wide.
That is root's call, since every map and capture baseline moves with it. I'd
put step 2 behind a look-dev CVar that defaults to off, like
`sora.LookDevVolumetricFog`, so one capture slot can A/B it.

### 3. Values and materials (my lane; needs a Blender kit build and the import slot)

| Surface | Now | Proposed (linear albedo) | Why |
| --- | --- | --- | --- |
| Kokabe above the nageshi | dark board/earth | shikkui lime plaster, 0.70–0.80 | the room's main bounce surface; light walls against a dark frame is the shoin look |
| Columns, rails | dark | fuki-urushi, stays 0.05–0.08 | plane separation through contrast |
| Ceiling | mon on every coffer | plain sugi boards (sao-buchi), 0.25–0.35; a mon only over the kamiza | removes the repeated motif, lifts the darkest plane |
| Floor | dark planks | polished hinoki, 0.25–0.35, roughness 0.25–0.35 | it reflects the shoji, which is how a real dojo floor reads |
| Shoji | see-through, clipped | washi, albedo 0.80, two-sided transmission about 0.35 | the panes glow at a bounded luminance instead of clipping |
| Lamp heads | clip | visible emissive down to paper-lantern luminance | the point lights themselves are unchanged |

### 4. Only if steps 1–3 miss the targets, most likely on SM5

Add fill that stealth cannot see:

- rect lights across the shoji and renji bands, facing in, without shadows;
- intensity: the beat's sky luminance times the washi's transmission;
- colour: the sky's, so the room gains a cool component against the warm sun
  and lamps.

The rule is that lamp pools stay at least 1.5 EV above the room median, so the
lit-equals-seen light remains the visibly brightest. Lumen skylight leaking of
0.05–0.1 in the hall volume is the last resort, since it isn't physical.

## Targets

These are for room readability, not photoreal. Each holds per ArtReview view,
in SM5 and in SM6, measured on originals with the analyzer:

| Measure | Now | Target |
| --- | --- | --- |
| Median luma | 0.06–0.21 | 0.28–0.45 |
| p05 luma, and crushed pixels | p05 0.03–0.09 | p05 ≥ 0.04 and crushed ≤ 2% |
| Clipped pixels | 0.7–6.8% | ≤ 2%, except views through the open engawa or genkan |
| R/B, beats b01–b10 | 2.8–6.3 | ≤ 2.2 (golden hour b11–b13 may reach about 2.8) |
| SM5 − SM6 median | ≤ 0.15 EV, same source | ≤ 0.25 EV |
| Lamp pools | — | ≥ 1.5 EV above the room median, on a fixed rect per view |

And always:

- CrouchAndCover, Detection, LampsAndFloors and `test_environment_presets.py`
  pass unchanged;
- a `LightAt` probe at the fixture points returns identical values;
- the local-exposure GPU cost is measured;
- all originals are looked at, since the numbers don't judge an image.

## Files

| Owner | Files |
| --- | --- |
| Mine | `SoraWorldBuilderDojoHall.cpp` (one hall-volume function), `create_nyaagyu_dojo_kit.py` and `import_nyaagyu_dojo_kit.py` (materials), `scripts/art/analyze_capture_luminance.py` |
| Root | the diagnostic and every capture, the stealth tests, any project-wide exposure setting |
