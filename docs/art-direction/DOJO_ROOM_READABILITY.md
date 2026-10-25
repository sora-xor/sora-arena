# Dojo room readability: measurements and proposal

**Status:** proposal for root review. None of it is implemented, and none of it
is photoreal acceptance. It builds on A2's per-beat sun and sky
(`SoraWorldBuilderLighting.cpp`, integrated as `e3b8aa5`) and changes nothing
in A2.

Root's independent review of `b8ac8c1` (`dojo-readability-b8ac8c1-review`)
reproduced every table here from the 20 authenticated originals. It also
corrected how I'd read them; this revision follows those corrections.

## What the originals show

I measured the PNGs with `scripts/art/analyze_capture_luminance.py`. Every
number describes the **SDR output image**, after tone mapping, saturation
and bloom. None of it is camera exposure (EV100), pre-tonemap scene luminance
or what the engine's histogram meters.

| Term | Meaning |
| --- | --- |
| Display luma | Rec. 709 luminance of the inverse-sRGB pixels, re-encoded as sRGB, 0–1 |
| Display stops | log2 of the median linear display luminance; a relative brightness, so only differences between frames mean anything |
| Thirds | the medians of the top, middle and bottom pixel bands; they are not surfaces |
| Saturated | any channel at 254 or more, an output proxy |
| R/B | mean linear red over blue, weighted by the view's content; an output proxy, not white balance |

ArtReview at `184a7b6`: the old kit, A2 beat `ch01.b02` (overcast),
1920×1080. All of it is b02, so it isn't evidence about the other beats. SM5
is within ±0.1 display stops of SM6 in every view:

| View | Median luma | p05 | Thirds (top / middle / bottom) | Saturated | R/B |
| --- | --- | --- | --- | --- | --- |
| Entry_East | 0.185 | 0.093 | 0.13 / 0.25 / 0.19 | 3.3% | 3.2 |
| Kamiza | 0.183 | 0.063 | 0.13 / 0.25 / 0.19 | 6.8% | 2.8 |
| South_Shoji | 0.103 | 0.044 | 0.08 / 0.20 / 0.10 | 3.8% | 4.3 |
| Ceiling | 0.063 | 0.033 | 0.04 / 0.06 / 0.09 (almost all ceiling) | 0.7% | 6.3 |
| West_Back | 0.150 | 0.068 | 0.10 / 0.21 / 0.16 | 2.4% | 5.9 |
| Floor_Light | 0.203 | 0.094 | 0.22 / 0.19 / 0.20 | 3.7% | 3.9 |

NaniteDraw entry view (1280×720): conventional kit `6e0e99c` against the
Nanite kit `a8ecee6`, each source group paired separately:

| Mode | Median luma | Bottom third | Median display-stop change |
| --- | --- | --- | --- |
| SM6 | 0.142 → 0.096 | 0.152 → 0.087 | −0.93 |
| SM5 | 0.151 → 0.096 | 0.161 → 0.089 | −1.07 |

In the ceiling view of the same pair, crushed pixels (luma ≤ 0.03) rise from
7–9% to 12–14%.

The output is about one stop darker. **The SDR medians don't say why:** a
lighting or GI change and an exposure change look the same in them. Root's
GI-source experiments point to SDF and card differences, but that is a
separate finding.

## What is known, and what isn't

**Known from source:**

- The project never sets
  `r.DefaultFeature.AutoExposure.ExtendDefaultLuminanceRange`, and the engine
  default is 0 (`SceneView.cpp`).
- So the legacy settings apply (`Scene.cpp`; `PostProcessEyeAdaptation.cpp`):
  `AutoExposureMinBrightness` and `MaxBrightness` 0.03 and 8 (white-point
  luminance), histogram −8 to 4 (log2).
- The global grade overrides only the method, percentiles 12/88, speeds and
  the −0.45 bias.

**Not known:**

- whether the minimum bound is ever reached;
- what the metered average scene luminance is;
- what the target and current exposures were in any original.

The capture timing can't settle that either way:

- ArtReview unpauses 0.4 s, then pauses 3 s, per camera; NaniteDraw stays
  paused.
- Adaptation uses `DeltaWorldTime`. `LevelTick` keeps assigning it while
  paused, and camera cuts and resets can `ForceTarget`.
- So neither "converged" nor "frozen" follows from the pause or the wall
  clock.

**Hypothesis:** the legacy minimum keeps the interior from opening up. It
fits a dark output that responds fully to GI changes. Nothing above tests it.
I've dropped my earlier inference that a converged view should land at a
median of about 0.40, or rise 2–3 stops: the histogram target sits before
the tone curve and uses its own weights.

**Art findings, which hold whatever the exposure:**

1. **One value everywhere.** Walls, ceiling, floor and the timber frame are
   all a mid-dark reddish brown, so the planes don't separate. Measuring
   that needs material regions per camera (below), not thirds.
2. **Monochrome orange:** R/B is 2.8–6.3 in b02. Warm lamps and reddish
   albedo dominate, and no cool daylight component comes through the shoji.
3. **Near-saturated highlights:** 0.7–6.8% of each frame, mostly the engawa
   doorway, the shoji panes and the lamp heads.
4. **The ceiling repeats** (a mon on every coffer) and is the darkest view.

## What stays fixed: gameplay light

`USoraStealth::LightAt` scans visible components on `ALight` actors:

- the brightest `UDirectionalLightComponent`'s intensity supplies the
  ambient;
- `UPointLightComponent`s (spots included) add by distance against
  `AttenuationRadius`; their intensity isn't read.

Exposure, tonemapping, sky light, rect lights (`ULocalLightComponent`, not
point), emissive surfaces and materials never enter it. Nothing below changes:

- the 25 lux estate key or the A2 table;
- any lamp actor's visibility, location or radius;
- the sky's 0.65, the fog's 0.0045 or the global −0.45 bias.

No point or spot light is added.

An unchanged `LightAt` isn't enough on its own. Bright fill can make a safe
spot *look* exposed. So each step also keeps the fixed `LightAt` probes and
existing tests, and adds image review of lamp pools and one traversal
boundary against the HUD meter, before the treatment spreads.

## Proposal, in order

Each step ships separately and is measured before the next.

### 1. A controlled exposure diagnostic (root lane; capture instrumentation is root's)

Hold everything fixed:

- source, generated assets, camera, FOV and resolution;
- beat, shader model, lighting, tone curve, local exposure and output
  transform.

Start each comparison from a controlled view history, and record the shader
platform and every camera cut or `ForceTarget`.

**Log for each rendered frame:**

- the effective `ExtendDefaultLuminanceRange`;
- the exposure method, show flags and any fixed override;
- min and max brightness, with units;
- histogram bounds, percentiles and weights;
- bias, curve, speeds and local-exposure settings;
- `View.PreExposure`, `DeltaWorldTime` and accumulated delta;
- current and target exposure;
- the un-clamped metered `AverageSceneLuminance`, with its readback frame.

**Settling:** count a frame only after current exposure has held within 0.05
stops of target for 30 rendered frames, and Lumen and streaming have
stabilised.

**Testing the clamp:**

- Show the metered average below `MinBrightness × 0.18` (legacy units), with
  the target pinned at that bound.
- Then lower **only** the minimum, histogram bounds fixed, and watch target
  and current move.
- If the first histogram bucket saturates, vary the histogram floor in a
  separate run.

The `ExtendDefaultLuminanceRange=1` switch is only a broad sensitivity check:
it changes the min/max bounds *and* the histogram bounds and their units, so
neither a brighter nor an unchanged result proves or rules out the clamp.

**Lighting versus exposure:** also run a fixed or manual exposure, or a
matched target, with linear HDR scene samples beside the SDR originals.

### 2. Interior exposure per hall (my file: `SoraWorldBuilderDojoHall.cpp`)

This step waits for step 1, and sits behind a look-dev CVar that defaults
off (like `sora.LookDevVolumetricFog`).

In `HallInterior`, add one actor per hall: a `UBoxComponent` the size of the
hall rect, with a `UPostProcessComponent` child.

- The box has no collision and never affects navigation.
- `bUnbound` false, priority above the global grade, blend radius 150 cm at
  the doorways.
- Only the setting step 1 proves limiting is overridden; the bias stays
  inherited.
- Local exposure: `HighlightContrastScale` 0.6, `ShadowContrastScale` 0.85,
  `DetailStrength` 1.0 (bilateral), to hold the panes and lamp heads.

The project-wide alternative is root's call, since every map and capture
baseline moves with it.

### 3. Values and materials (my lane; needs a Blender kit build and the import slot)

| Surface | Now | Proposed (linear albedo) | Why |
| --- | --- | --- | --- |
| Kokabe above the nageshi | dark board/earth | shikkui lime plaster, 0.70–0.80 | the main bounce surface; light walls against a dark frame is the shoin look |
| Columns, rails | dark | fuki-urushi, stays 0.05–0.08 | plane separation through contrast |
| Ceiling | mon on every coffer | plain sugi boards (sao-buchi), 0.25–0.35; a mon only over the kamiza | removes the repeated motif |
| Floor | dark planks | polished hinoki, 0.25–0.35, roughness 0.25–0.35 | it reflects the shoji, which is how a real dojo floor reads |
| Shoji | see-through, clipped | washi, albedo 0.80, two-sided transmission about 0.35 | the panes read as glowing paper |
| Lamp heads | saturate | visible emissive down to paper-lantern luminance | the lamp actors are unchanged |

Albedo alone doesn't bound how bright a window gets, so these are judged at
a controlled exposure (from step 1) before any fill is considered.

### 4. Only if steps 1–3 miss the art criteria

Add fill that stealth cannot see: rect lights across the shoji and renji
bands, facing in, without shadows, coloured by the sky.

- **Calibration:** the intensity needs explicit units, from an area times a
  luminance taken from the beat's measured exterior luminance and the washi's
  transmission. The sky light's 0.65 multiplier is not such a specification.
- **Pools:** lamp pools stay at least 1.5 display stops above the room on the
  per-camera regions (below).
- **Leaking:** Lumen skylight leaking (0.05–0.1) in the hall volume is the
  last resort, since it isn't physical.

## Art criteria (SDR output, not exposure targets)

Each holds per ArtReview view, in SM5 and SM6, on originals:

| Measure | Now (b02 only) | Criterion |
| --- | --- | --- |
| Median display luma | 0.06–0.21 | 0.28–0.45 |
| p05 luma, and crushed pixels | p05 0.03–0.09 | p05 ≥ 0.04 and crushed ≤ 2% |
| Near-saturated pixels | 0.7–6.8% | ≤ 2%, except views through the open engawa or genkan |
| R/B output proxy | 2.8–6.3 | ≤ 2.2 for daylight beats; golden hour b11–b13 may reach about 2.8 |
| SM5 − SM6 median | ≤ 0.15 display stops, same source group | ≤ 0.25 |
| Lamp pools, and wall/frame separation | not measured yet | pools ≥ 1.5 display stops above the room; plaster ≥ 1.5 stops above timber |

The last row needs fixed per-camera regions: material ROIs for plaster,
timber, floor and ceiling, and lamp-pool ROIs. They go in a
`--rois ROIS.json` for the analyzer, drawn on the reviewed originals and
agreed with root before any treatment is scored.

And always:

- CrouchAndCover, Detection, LampsAndFloors and `test_environment_presets.py`
  pass unchanged;
- the fixed `LightAt` probes return identical values;
- the local-exposure GPU cost is measured;
- every original is looked at.

## Analyzer

`scripts/art/analyze_capture_luminance.py` labels each quantity as above.

**Pairing:** an SM5 and an SM6 frame pair only inside one source group,
taken from an explicit `LABEL=` or the run's `source-commit.txt`, with the
same file name.

- Duplicates of one name and mode in a group are reported as ambiguous (exit
  2), never overwritten.
- Every row and pair carries its path, SHA-256 and run folder.
- Run folders are recognised as `<timestamp>-sm5-<pid>`, `...-sm6-...` or a
  bare `sm5`/`sm6`.

**Regions:** `--rois` adds per-camera named rectangles.

**Tests:** `scripts/art/test_analyze_capture_luminance.py`, 6 tests. They
cover every PNG row filter, two source groups that used to overwrite each
other, ambiguity, labels and bare mode folders, and ROIs.

## Files

| Owner | Files |
| --- | --- |
| Mine | `SoraWorldBuilderDojoHall.cpp` (one hall-volume function, step 2), `create_nyaagyu_dojo_kit.py` and `import_nyaagyu_dojo_kit.py` (materials, step 3), the analyzer and the ROI file |
| Root | the diagnostic and its instrumentation, every capture, the stealth tests, any project-wide exposure setting |
