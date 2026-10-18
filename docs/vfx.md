# VFX: Niagara systems, materials and particle textures

**Status (2026-09-27), step 1 of the VFX lane (C8):**

- **Step 1 does not meet the binding photoreal AAA directive.** The stills of
  the only verified build show the matchlock's powder cloud as round
  cotton-ball puffs, sparks as frame-filling round blobs, the explosion flash
  and the energy muzzle's star and ring as visible square quads, fire-zone
  flames as vertical sticks and the forge as one solid column, water crowns as
  translucent cones, mist as grey polygons against the sky, and debris as
  scaled basic shapes (section 6). Nothing may be wired into gameplay, or
  called done, on the strength of these stills.
- **Built by `scripts/toolchain/import-mac.sh`** (step `import-vfx`, script
  [`scripts/unreal/create_sora_vfx.py`](../scripts/unreal/create_sora_vfx.py)):
  27 Niagara systems and 3 effect types in `/Game/Generated/VFX`, 12 master
  materials and 27 instances in `/Game/Generated/VFX/Materials`, and 8
  original particle textures in `/Game/Generated/VFX/Textures`. All are
  regenerated from source on every import; nothing under `Content/Generated`
  is committed. Unlike the other import steps this one runs with the Metal RHI
  (`-RenderOffscreen` instead of `-nullrhi`) so that it can compile and check
  the materials' shaders; it refuses to build materials under `-nullrhi`.
- **Not wired into the game yet.** No gameplay code spawns these systems; the
  provisional basic-shape stand-ins described in [unreal.md](unreal.md) remain
  until step 2 (spawning, `User.FlashScale` from the settings, attachment to
  sockets and the kernel's events).
- **Seen rendered:** only as the review stills listed in section 7, made with
  a real Metal RHI in a throwaway editor world. They are not packaged-game
  screenshots and have no Lumen scene, bloom, motion blur or eye adaptation.
- **Verified up to a tuning pass, not after it.** The build passed (27
  systems, no compile errors) and was rendered at 21:20–21:31 JST on
  2026-09-26. Three later change sets are in the scripts but have **not been
  run**. Free disk was 25.9–27.0 GiB that evening and 24–26 GiB during the
  review fixes of 2026-09-27, below the lane's 32 GiB floor for editor work
  (and below `import-mac.sh`'s own 30 GiB check).
  - The tuning pass:
    - flashes, sparks, fire and motes about 3–5 times dimmer;
    - a larger matchlock plume, fireball and smoke;
    - fewer, wider and slower fire-zone and forge flames;
    - denser wood and fur dust, and lower mist banks;
    - a radial mask on the WaterLit cells, and an edge fade with a black
      point on the Flash cells;
    - a per-shot warm-up in the preview script.
  - Two fixes, with their causes found in the engine source (section 6,
    items 1 and 4):
    - the particle lights now write the attributes the light renderer reads;
    - the water mist is drawn without the 8×8 flipbook that showed it a
      sixty-fourth of its texture cell.
  - The preview script now ends with a pass/fail light check (section 7).
  - The review fixes of 2026-09-27:
    - per-particle random values drawn once at spawn, instead of `rand()` in
      update inputs that re-rolled every tick (spin, drag, flame
      temperature; section 1);
    - no template gravity on the pan smoke and the energy vapour;
    - the lantern's halo flickers every frame instead of once per spawn;
    - a 360° cleave telegraph without a seam along its back;
    - `import-mac.sh` builds every system and requires the exact count;
    - the preview script sweeps the blade trail across its path in view,
      renders the forge's three gauge states, the projectile trail, a 360°
      cleave and rain, and refuses two stills with one file name.

  An import must pass, the light check must log `PASS`, and the stills must
  be looked at before this is integrated (section 7).
- **What the verified stills show.** Most show their system working, but
  none reads as photoreal (first bullet), and several show a defect that
  section 6 lists. Some effects are missing from their stills altogether: the
  fire zone at dusk, the energy beam at 0.03 s, the fur impact after 0.1 s and
  the matchlock's smoke after 0.6 s. The Niagara lights light nothing.
  Two systems have never been rendered, rain and the projectile trail, nor
  have a full-circle cleave and the forge's red and yamabuki states.

## 1. How the systems are authored

Python cannot edit a Niagara stack in UE 5.8: the engine's stack editing
(add emitters and modules, set inputs to literals, links, HLSL expressions or
dynamic inputs, add user parameters, compile diagnostics) exists only as plain
C++ in `UNiagaraExternalEditUtilities` (`NiagaraEditor`, marked experimental by
Epic). The editor-only project plugin
[`Plugins/SoraVfxAuthoring`](../Plugins/SoraVfxAuthoring) exposes those calls to
Python as `unreal.SoraNiagaraAuthoring`, one Blueprint-callable function per
operation that returns the engine's errors (empty on success). It is an
`Editor` module, so game targets never build or load it. UnrealBuildTool's
target export confirms this: the `SoraArena` game target has 460 modules
without it, and `SoraArenaEditor` lists it among 968 (section 7).

`create_sora_vfx.py` then:

1. imports the textures, checking every SHA-256 against
   `Content/SourceArt/VFX/manifest.json`;
2. rebuilds each material from nothing (Custom HLSL nodes plus particle
   colour, dynamic parameters, depth fade, SubUV and black-body nodes), and
   **compiles its shaders for the editor's platform, failing the step if the
   pixel shader does not compile** (a Custom-node error is otherwise silent in a
   `-nullrhi` build and the game would fall back to the default material);
3. builds every system from an empty asset: each emitter is a copy of an engine
   template emitter from `/Niagara/DefaultAssets/Templates/Emitters`
   (SimpleSpriteBurst, DirectionalBurst, OmnidirectionalBurst, Fountain,
   SingleLoopingParticle, DynamicBeam, LocationBasedRibbon, UpwardMeshBurst),
   re-parameterised, with engine modules from `/Niagara/Modules` added where
   the template lacks them (curl noise, acceleration, drag, collision, vortex,
   wind, SubUV animation, dynamic material parameters, sprite facing, Set
   Parameters);
4. assigns each system an effect type (below), force-compiles it and fails
   on any compile error or error-level stack issue; warnings are logged. A
   complete build prints `SORA_VFX_READY: 27 systems`.

Effect types (scalability): `ET_SoraVFX_Burst` for one-shot weapon, impact and
ability effects (checked at spawn, not spawned beyond 120 m, at most 64 alive),
`ET_SoraVFX_Ambient` for placed loops (fires, forge, steam, water, lanterns,
rain, mist; asleep beyond 90 m, resumed when near) and `ET_SoraVFX_Gameplay`
for what the player must read (telegraphs, trails, the fire zone, the ward;
never culled).

An existing asset is reset in place (emitters and user parameters removed)
rather than deleted. `SORA_VFX_ONLY=<builder>,<builder>` rebuilds some systems
and `SORA_VFX_REUSE_MATERIALS=1` skips textures and materials while iterating;
an unknown builder name is an error. Such a run ends with `SORA_VFX_PARTIAL`
instead of `SORA_VFX_READY`. `import-mac.sh` unsets both variables and passes
the step only on `SORA_VFX_READY: <n> systems`, with n the length of the
builder's `SYSTEMS` list (27), which
[`scripts/toolchain/vfx_system_count.py`](../scripts/toolchain/vfx_system_count.py)
reads from the source.

Engine behaviour this relies on or works around, found while building or in review:

- The CPU vector VM has no `smoothstep`; expressions use the polynomial
  (`ss()` in the script). `min`, `max`, `pow`, `sin`, `saturate`, `lerp`,
  `sqrt` and `rand()` compile.
- A Niagara compile can be served from the derived-data cache even after the
  system gained the user parameter the cached failure was missing; the plugin
  therefore always requests a forced compile.
- `MaterialEditingLibrary.set_material_instance_*_parameter_value` returns
  false even when it succeeds (UE 5.8), so the script checks each parameter
  name against the parent and reads the value back.
- Material dynamic parameter outputs are named `R`, `G`, `B`, `A`; the plain
  particle-colour output is RGB, so Custom nodes take its `RGBA` output.
- A fresh `ScaleColor` module has an integer scale mode; the templates' older
  copy has an enum.
- **Lights.** The light renderer reads `Particles.Color` and
  `Particles.LightRadius` through its default bindings
  (`NiagaraLightRendererProperties.cpp`). When they are not written, the light
  takes the particle's plain white colour and the 100 cm default radius
  (`NiagaraRendererLights.cpp`, `NiagaraConstants.cpp`). White is 1 in
  inverse-square units, about a thousandth of a lumen, so the light is
  invisible. The first build used `Light_Attributes`, whose Color and Radius
  inputs set to 1 wrote `Particles.Light_Attributes.Color` and `.LightRadius`
  instead. The engine module says: "In the case of writing to a unique
  attribute, you will have to bind that new attribute to your Light Renderer".
  Each light emitter now writes the two default attributes itself with a Set
  Parameters module at the end of its update stack (`light()` in the script).
  It carries no sprite, so `Particles.Color` has no other use.
- **Flipbooks and sheet cells.** A sprite renderer with a `SubImageSize`
  maps each particle's UVs onto one sub-image (`NiagaraSpriteVertexFactory.ush`).
  Materials that pick one cell of a 2×2 sheet themselves (`M_SoraVFX_Flash`,
  `M_SoraVFX_WaterLit`) must therefore be drawn by a 1×1 renderer.
  `puffs(..., frames=None)` does that for the water mist.
- `WindForce` requires the drag module after it in the stack.
- **Random values.** Particle Update runs every tick, and `rand()` there is
  drawn again on each evaluation: the CPU vector VM's `rand` is unseeded, and
  the GPU's is seeded by the emitter's tick counter
  (`NiagaraEmitterInstanceShader.usf`). A random spin rate in the update
  stack made sprites jitter instead of turning, a random drag averaged out,
  and a random flame temperature became per-frame noise (the black-body
  output grows as T⁴). Each emitter that needs per-particle randomness now
  writes `Particles.SoraRandom`, four uniform values, once in its spawn stack
  (`Emitter.random()`), and update inputs read a channel of it
  (`particle_random()`: x spin, y drag, z heat). The builder refuses an
  update input whose expression calls `rand()`.
- **Template forces.** The OmnidirectionalBurst, DirectionalBurst, Fountain
  and UpwardMeshBurst templates contain a `GravityForce` module. Smoke, vapour
  and steam must set it to zero (`gravity()`). The matchlock's cloud had no
  override in the verified build: at 0.6 s it hung low over the floor, and by
  2 s it was gone, which fits a fall.
- **Spawn-time inputs.** InitializeParticle's inputs are evaluated once, at
  spawn, so anything that must animate (the lantern halo's flicker) goes in
  the update stack.

## 2. Conventions the game code must follow

- **Axes.** Local +X is the muzzle direction, the hit surface's normal, the
  beam or trail axis and a telegraph's forward; +Z is up. Impacts, the water
  splash and the explosion are spawned with +X along the surface normal.
- **Units.** Centimetres and seconds. Emissive colours are cd/m²: a white
  surface under the Estate's 25 lux sun is about 8 cd/m². The fire material
  peaks at 250 times its black-body colour, flashes at 60–300 and sparks at
  90–350; the tuning pass lowered these from up to 1600, which bloomed into
  orbs. Lights are given in
  lumens and converted to the engine's inverse-square units
  (lm × 10⁴ / 4π); the project's lanterns are 140–260 lm and its fire zone
  2600 lm, so these effects sit on the same scale.
- **Flash reduction.** Every system has `User.FlashScale` (default 1). It
  scales what flashes: the brightness of flashes, sparks and burning grains,
  the spark counts, the lights of flashes (muzzle, impact, parry, explosion,
  heal), and the amplitude of the flicker of steady lights (lantern, fire
  zone, forge, ward), of the lantern halo and of telegraph pulses. It leaves
  the brightness of steady lights and glows alone: the fire zone's 2600 lm,
  the forge's 2400–4000 lm, the ward's and the lanterns' lights, flames,
  embers and motes. They do not flash, and dimming them would change the
  scene's lighting rather than reduce flashing. When the player turns on
  点滅を抑える (reduce flashing), step 2 should pass about 0.3. Systems without
  a flash ignore it.
- **Telegraph colours** come from the settings palette through
  `User.TelegraphColor` (defaults: cyan for a locked aim or beam, amber for a
  blow or an area, as in `SoraBoss.cpp`).

## 3. Systems

All live in `/Game/Generated/VFX`. "Burst" systems finish by themselves;
"loop" systems run until deactivated.

| System | Kind | User parameters (besides FlashScale) | What it shows |
|---|---|---|---|
| `NS_SoraVFX_Muzzle_Matchlock` | burst | `PanOffset` (flash pan relative to the muzzle) | Side-on powder plume and face flash (black-body orange), 18–40 burning grains, a short fireball of burning gas rolling out of the barrel, a dense white black-powder cloud that drags to a stop and rises for 6 s, the pan (hizara) flash and puff, a 5000 lm flash light |
| `NS_SoraVFX_Muzzle_Energy` | burst | `Tint` | Plasma star, an expanding shock ring facing +X, ionised sparks, vapour, a 2500 lm cyan light |
| `NS_SoraVFX_Beam_Energy` | burst | `BeamEnd` (world), `Tint`, `Width`, `Duration` | Core and halo ribbons with a scrolling ripple; also a sustained beam with a longer `Duration` |
| `NS_SoraVFX_Trail_Projectile` | loop | `Tint`, `Intensity`, `Width` | A ribbon behind a bolt (bright) or an arrow (faint wake) |
| `NS_SoraVFX_BladeTrail` | loop | `Width`, `Tint`, `Intensity` | A faint translucent sheen spanning the blade (ribbon side vector = the component's +X), 0.15 s long; attach at the blade's middle and activate for the swing |
| `NS_SoraVFX_Impact_Wood` | burst | — | Splinters and chips as mesh particles with the Timber PBR surface, bouncing on the world; wood dust; falling fibres |
| `NS_SoraVFX_Impact_Stone` | burst | `SparkAmount` | Stone chips with the Stone PBR surface, grey dust, sparks only for steel (`SparkAmount` 1) |
| `NS_SoraVFX_Impact_Dirt` | burst | — | Soil clods, a brown burst and dust rolling out along the ground |
| `NS_SoraVFX_Impact_Metal` | burst | — | 16–44 bouncing sparks, a pin flash, a smoke wisp, a 600 lm light |
| `NS_SoraVFX_Impact_Fur` | burst | `FurTint` | Blood-free: locks of shed fur (agouti-banded sprites) fluttering down, dander |
| `NS_SoraVFX_ParrySparks` | burst | — | White-hot steel sparks off the contact, a pin flash, a 1500 lm light, a wisp |
| `NS_SoraVFX_Explosion` | burst | — | Flash, 30 000 lm light, a black-body fireball rolling into dark smoke, ground dust ring, stone debris, sparks, embers |
| `NS_SoraVFX_Hanabi_FireZone` | loop | `Radius` | Flames over a disc (count scales with area), embers, smoke, a flickering 2600 lm light |
| `NS_SoraVFX_Kusushi_Heal` | burst | `Radius`, `Tint` | Jade-gold motes rising and swirling from a ring, a ground ring that fills outward, a soft light |
| `NS_SoraVFX_Kusushi_Ward` | loop | `Radius`, `Tint` | Six paper talismans circling the ward, drifting motes, a faint light |
| `NS_SoraVFX_Shinobi_Decoy` | burst | — | A smoke-ball burst, washi talisman scraps and leaves fluttering down with curl noise |
| `NS_SoraVFX_Karakuri_BuildDust` | loop | `Width` | Dust and wood shavings along the barricade footprint, occasional hammer sparks |
| `NS_SoraVFX_Telegraph_Beam` | burst | `TelegraphColor`, `Length`, `Width`, `Duration` | A ground lane along +X that fills over the windup, pulsing edges, a charge glow |
| `NS_SoraVFX_Telegraph_Cleave` | burst | `TelegraphColor`, `Radius`, `ArcDegrees`, `Duration` | A wedge that fills over the windup; at 360° a full disc with no side edges (an area) |
| `NS_SoraVFX_Water_SluiceRise` | loop | `Width`, `Flow` | Foam, spray, crown splashes and mist through an opened sluice (+X downstream) |
| `NS_SoraVFX_Water_Splash` | burst | — | Crown sheets, droplets, mist, a spreading foam ring |
| `NS_SoraVFX_Forge_Fire` | loop | `Temperature`, `Bellows`, `Radius` | Flames whose black-body temperature follows the three gauge states (red, yamabuki, white), sparks with the bellows, soot, a 2400–4000 lm light |
| `NS_SoraVFX_Steam` | loop | `Rate` | Rising steam |
| `NS_SoraVFX_Steam_Burst` | burst | — | A quench burst of steam |
| `NS_SoraVFX_Rain` | loop | `Intensity`, `Wind` | GPU streaks in a 30 m box killed on the depth buffer, and splash flecks at the component's height |
| `NS_SoraVFX_Mist` | loop | `Extent`, `Wind`, `Density` | Large lit mist banks drifting through a box |
| `NS_SoraVFX_Lantern` | loop | `Lumens`, `Radius`, `LightColor` | A flickering candle light (MegaLights allowed) and a soft halo that flickers too |

## 4. Materials

| Material | Blend / shading | Used for |
|---|---|---|
| `M_SoraVFX_SmokeLit` (+ `MI_Smoke`, `MI_Fireball`, `MI_Dust`, `MI_Steam`) | translucent, lit (volumetric directional) | Smoke, dust, steam, vapour, fireballs: flipbook density with self-shadow darkening, dynamic-parameter erosion and a black-body glow while hot, depth-faded |
| `M_SoraVFX_Fire` (+ `MI_Fire`) | alpha composite, unlit | Flames: looping flipbook temperature through the black-body node (900–1950 K), with a little soot occlusion |
| `M_SoraVFX_Flash` (+ four cell instances) | additive | Powder flash face-on and side-on, energy star, shock ring |
| `M_SoraVFX_Glow` (+ `MI_Spark`, `MI_Glow`) | additive | Sparks, embers, motes, halos (procedural falloff) |
| `M_SoraVFX_Beam` | additive | Beam and trail ribbons |
| `M_SoraVFX_Trail` | translucent, unlit | The blade sheen |
| `M_SoraVFX_WaterLit` (+ spray, sheet, foam, mist) | translucent, lit | Water |
| `M_SoraVFX_Rain` | translucent, lit | Rain streaks |
| `M_SoraVFX_DebrisLit` (+ wood, stone, soil, plaster) | opaque, lit, mesh particles | Chips and splinters with the environment palette's CC0 PBR maps at a random offset per chip |
| `M_SoraVFX_ScrapMasked` | masked, two-sided, lit | Paper talismans, leaves, ash |
| `M_SoraVFX_FurLit` | translucent, lit | Shed fur |
| `M_SoraVFX_Telegraph` (+ ring, wedge, lane) | translucent, unlit | Ground telegraphs |

## 5. Textures (project-owned)

[`scripts/art/create_vfx_textures.py`](../scripts/art/create_vfx_textures.py)
writes them deterministically (seeded numpy; a rerun reproduces the bytes) to
`Content/SourceArt/VFX/Textures`, and records sizes and SHA-256 hashes in the
schema-2 OWN manifest `Content/SourceArt/VFX/manifest.json` that
`validate_asset_ledger.py` reads. No third-party image is involved.

| Texture | Content |
|---|---|
| `T_VFX_SmokePuff` | 8×8 flipbook: a puff integrated along the view through a noise-displaced sphere (optical depth → coverage), swelling, eroding from the limb in; R density, G heat, B thickness |
| `T_VFX_Fireball` | The same with a violent warp and a longer-lived hot core |
| `T_VFX_Fire` | 8×8 flipbook that loops seamlessly (noise periodic in rise and time): flame tongues breaking into licks; R temperature, G opacity, B tongue mask |
| `T_VFX_Flash` | 2×2: powder flash face-on, powder plume side-on (muzzle at the bottom), energy star, shock ring |
| `T_VFX_Noise` | Tileable broad and fine fbm, cellular distance, billow |
| `T_VFX_Water` | 2×2: droplet spray, crown sheet, whitewater lace with bubbles, mist |
| `T_VFX_Scraps` | 2×2 colour: torn washi talismans (a vermilion seal corner, sumi strokes), a dry leaf, a charred flake |
| `T_VFX_Fur` | 2×2: locks of agouti-banded hair |

## 6. Limitations and known gaps (step 1)

Items 1–7, 9 and 11 show in the 21:31 stills of the verified build, item 12
is what those stills leave out, and the rest were found in the scripts; the
visible ones come first, most severe first. "Tuned" means the unrun pass of
the status section aims at it; "Fixed, unrun" means a cause was found and the
script changed, but no build has run it. Luminance figures are measured on the
EXRs with `vfx_preview_sheet.read_exr` (0.2126 R + 0.7152 G + 0.0722 B).

1. **Niagara lights light nothing.** A lantern test in the same stage
   compared the lantern with an ordinary 150 lm point light at the same spot,
   at dusk. The floor's median scene colour stayed at 0.0472 with the lantern
   (the same as without it) and rose to 0.1542 with the point light. In the
   stills, the wall and floor next to the explosion (30 000 lm), the matchlock
   (5000 lm), the parry (1500 lm) and the metal impact (600 lm) are identical,
   to four decimals, at the flash frame and at a late frame. Cause: the
   emitters wrote per-module attributes that the renderer does not read, so
   each light kept the particle's white (section 1, "Lights"). **Fixed,
   unrun:** `light()` now writes `Particles.Color` and `Particles.LightRadius`,
   and the preview script's light check repeats this test with a pass
   criterion (section 7). Scene captures might also leave particle lights out,
   so check once in a game viewport too. Until the check passes, treat every
   flash, fire, forge, lantern and ward light in the table above as absent.
2. **Effects missing from their stills.**
   - `Hanabi_FireZone` at dusk has almost no flames: a few specks, peak
     luminance 10.2, 29 pixels above 1. By day the same system at the same
     age (2.5 s, Radius 300) draws a full ring of flames (peak 89, 28 990
     pixels above 10). The flames are unlit, so the light setting cannot
     explain it. The dusk shot was the system's first capture.
   - `Beam_Energy` at 0.03 s renders nothing: peak luminance 0.113, the bare
     stage. At 0.40 s the beam is there (peak 194). With the default
     tracer `Duration` of 0.09 s, a blank first 0.03 s would be a third of a
     tracer's life. This was also the system's first capture.
   - `Impact_Fur` at 0.6 s shows a few grey specks near the floor and at
     1.4 s nothing that reads (peak 1.6 against a 1.06 median): no locks of
     fur fluttering down. The tufts are tinted close to the plaster and
     stone, and they may also be too small or thin at 170 cm.
   - `Muzzle_Matchlock` has no smoke at 2.0 s or 4.5 s (the two stills are
     identical pixel for pixel), although the cloud should last 6 s: template
     gravity, section 1. **Fixed, unrun** for the cloud (tuning pass), the
     pan smoke and the energy vapour.

   Other systems' first captures do show (the energy muzzle at 0.02 s peaks at
   336), so a first-activation dropout is a guess, not a finding. The preview
   script's per-shot throwaway activation (tuning pass, unrun) guards against
   it in the stills. A first spawn waiting on pipeline-state precaching could
   also hide an effect in the game, so step 2 must check the first shot, beam
   and fire zone of a session in a packaged build.
3. **Spark halos.** Parry, metal-impact and explosion sparks at 1000–1600
   cd/m² render as round halos about 10 cm across around their streaks: the
   tail of the glow falloff stays visible over the whole sprite. Tuned: 90–350.
4. **Hard sprite edges.** The explosion flash at 0.03 s and the energy muzzle's
   star and ring show their quads. Mist banks are invisible over the ground but
   show as hard-edged grey quads against an empty sky. The water crown sheets
   read as translucent cones. Measured on `T_VFX_Flash.png`, the flash quads
   have two causes. The sheet has a floor of 1–2/255 over 5–15 % of each
   cell. The side cell's plume also reaches its bottom border (0.35–0.51 in
   the outer 8 px), right above the ring cell, which bilinear filtering pulls
   in at the border. At hundreds of cd/m² both draw the quad.
   **Tuned:** the Flash material subtracts a 2/255 black point and fades the
   outer 5 % of each cell. It keeps 79–98 % of each cell's light. The radial
   mask it replaces kept 23 % of the ring and 55 % of the side plume, and cut
   the plume off at the muzzle. The WaterLit cells have a radial mask (it
   keeps 83–95 %). The mist had a second cause: its banks went through `puffs()`,
   which gave the renderer an 8×8 flipbook. Each sprite's UVs then covered a
   sixty-fourth of the mist cell, so the bank drew as a nearly flat patch cut
   off at the quad (section 1, "Flipbooks and sheet cells"). **Fixed, unrun:**
   the sluice, splash and mist banks draw the whole cell. The mist still needs
   a test against a real sky.
5. **Flames.** By day the fire-zone flames read as bright vertical sticks, and
   the forge as one yellow column. Tuned: wider, slower and fewer flames. The
   photoreal route is a simulated flipbook (a Blender Mantaflow bake).
6. **Smoke shape and scale.** At 0.6 s the matchlock's powder cloud is a
   cluster of round cotton-ball puffs, not a rolling plume. The explosion's
   fireball is about 1 m across and its smoke has thinned away by 5 s, which is
   small for a grenade or rocket. Tuned: a larger matchlock plume, fireball
   and smoke; the shape needs simulated flipbooks (item 9).
7. **Unreadable or unseen.** The Kusushi ward's talismans barely read by day.
   The blade trail's 0.12 s still shows nothing, and the harness explains
   it: it turned the component's +X along the direction of travel, so the
   ribbon, whose side vector is +X, laid its width along its own path, and the
   sweep lay in a plane the camera saw edge-on. It was not "meant to be faint"
   as this document said. **Fixed, unrun:** the harness keeps +X along the
   blade and cuts in the plane facing the camera, by day and at dusk (section
   7). Whether the sheen reads once it is swept properly is still to be seen.
8. **Per-tick random values** (not visible in any still, which are single
   frames). Sprite spin was a zero-mean jitter of up to ±3.7° per frame at
   60 fps (talismans and leaves at 220°/s) instead of a tumble. The fire zone
   and forge re-rolled each flame's black-body temperature every frame, so a
   fire-zone flame's brightness jumped by up to about 1.6–1.8 times between
   frames (less at the forge), unscaled by `FlashScale`. Per-particle drag
   spreads collapsed to their mean. **Fixed, unrun** (section 1, "Random
   values").
9. Smoke and fire flipbooks are 2D procedural approximations of volumes, not
   simulated renders. A Blender Mantaflow bake would be more convincing up
   close.
10. Telegraphs are sprites laid 3 cm above the ground, so they do not conform
    to uneven terrain. Niagara's decal renderer would, and is the next step
    there. At `ArcDegrees` 360 the cleave telegraph drew a bright double seam
    from the centre to the back rim: the wedge's side outline stayed on at a
    half-arc of π. **Fixed, unrun:** a half-arc above 3.13 draws a full disc
    without sides. Evaluated in numpy, the seam's outline went from up to 1.0
    to 0 along the back axis, and the 120° wedge is unchanged. Only 120° has
    been rendered.
11. Debris meshes are engine basic shapes (cube, sphere) scaled into chips and
    splinters, with the real PBR surfaces. Bespoke chip meshes would read
    better at close range.
12. **Never rendered.** `NS_SoraVFX_Rain` (a GPU simulation, which
    `NiagaraComponent.advance_simulation` does not step) and
    `NS_SoraVFX_Trail_Projectile` had no shot, so their table rows describe
    what the builder makes, not what anyone has seen. The forge's red-heat
    and yamabuki states were never seen either: both forge shots were written
    to `Forge_Fire_dusk_2.00s.exr`, so only the white-heat, full-bellows still
    survived. **Fixed, unrun:** the preview script flies the projectile
    trail, runs rain on real ticks, renders all three forge states and a
    360° cleave, and refuses to start when two stills would share a file
    name.
13. Rain splash flecks assume flat ground at the component's height; the
    streaks themselves stop on the depth buffer.
14. The lanterns flicker in unison. Each steady light's flicker is a function
    of `Engine.Time` and the light particle's `UniqueID`, which counts from 0
    in every lantern, so lanterns started together flicker together. The
    particle is renewed every second, so the phase also jumps once a second.
    A per-lantern phase (for example from the owner's position) is still to
    do.
15. There is no heat-haze distortion and no sound. The three effect types of
    section 1 exist, but there are no per-platform scalability overrides yet
    (the chapter asks for Mac spark caps).

## 7. Verification

The review stills are made with
[`scripts/unreal/diagnostics/render_vfx_previews.py`](../scripts/unreal/diagnostics/render_vfx_previews.py)
(real RHI, not `-nullrhi`) and tiled with
[`vfx_preview_sheet.py`](../scripts/unreal/diagnostics/vfx_preview_sheet.py).

What was run on 2026-09-26 (JST, pinned UE 5.8.3):

- **21:20–21:28:** `UnrealEditor-Cmd SoraArena.uproject
  -ExecutePythonScript=scripts/unreal/create_sora_vfx.py -unattended -nopause
  -RenderOffscreen -nosplash -nosound -stdout -FullStdOutLogOutput`, the
  command line of the `import-vfx` step. It exited 0 and logged
  `SORA_VFX_READY: 27 systems`, with every system `status UpToDate, 0
  warnings`. This was the script as it stood before the tuning pass.
- **21:29–21:31:** `render_vfx_previews.py` with the same editor command line
  logged `SORA_VFX_PREVIEW_DONE: 59`, but only 58 EXRs exist: both forge
  shots were written to one file (section 6, item 12). The stills were tiled
  and looked at.
- **21:36:** the lantern light test of section 6.
- **23:36–23:37, UnrealBuildTool only (no compile, no editor):** the target
  export, from the worktree root with the pinned engine and Xcode:
  `"$UE_ROOT/Engine/Build/BatchFiles/Mac/Build.sh" SoraArena Mac Development
  -Project=$PWD/SoraArena.uproject -Mode=JsonExport -OutputFile=<file>
  -WaitMutex -architecture=arm64`. Both exports exited 0.
  - The game target `SoraArena` lists 460 modules, and none of them is
    `SoraVfxAuthoring`, `NiagaraEditor` or `UnrealEd`.
  - The same export of `SoraArenaEditor` lists 968 modules, including
    `SoraVfxAuthoring` from `Plugins/SoraVfxAuthoring`.
- **Later, host only (no editor):**
  - The textures, regenerated into a scratch folder, match the manifest's
    SHA-256 and the files byte for byte.
  - `python3 scripts/assets/validate_asset_ledger.py` reports `LEDGER_OK`
    with 0 errors.
  - `vfx_preview_sheet.py` with the current bloom re-tiled the 21:31 stills
    into 26 sheets.
  - All four Python scripts parse, and `bash -n` passes for `import-mac.sh`.

What was run on 2026-09-27 (JST) for the review fixes, host only. Free disk was
24–26 GiB, so no editor, import or render ran:

- `python3 -m unittest scripts/toolchain/test_import_vfx_gate.py
  scripts/unreal/test_vfx_preview_shots.py`: 13 tests, all pass.
  - The gate tests run `import-mac.sh` in a scratch project with a fake
    editor, doctor and build. With `SORA_VFX_ONLY` and
    `SORA_VFX_REUSE_MATERIALS` exported, the step passes and the fake editor
    sees neither. It fails on `SORA_VFX_READY: 0`, `1` or `2 systems` and on
    `SORA_VFX_PARTIAL`. Against the previous `import-mac.sh` the variable and
    count tests fail.
  - The preview tests load the preview script with a stand-in `unreal`
    module. They check that every system of the builder has a shot, that no
    two stills share a name, the three forge states, the 360° cleave, rain
    and the projectile flight. They also check the blade sweep's geometry: +X
    radial, the edge across each step of the path, a 100° arc, and a plane
    within 10° of facing the camera. Swapped into the new script, the
    previous harness's geometry fails that test, and so do a tangent +X alone
    and a horizontal sweep alone.
- The numpy check of the telegraph wedge in section 6, item 10.
- The luminance figures of section 6, item 2, from the 21:31 EXRs.

The light check. `render_vfx_previews.py` ends by building the dusk stage.
It measures the median luminance of the floor below one spot three times:
bare, under `NS_SoraVFX_Lantern` at 150 lm hanging 150 cm above it, and under
an ordinary 150 lm point light in the same place. It logs
`SORA_VFX_LIGHT_CHECK: PASS` when the lantern adds 0.5 to 2 times what the
point light adds, and the point light adds at least half the bare value.
Otherwise it logs `FAIL` as an error. The captures are saved as
`LightCheck_none/lantern/point.exr`.

Not run yet:

- `import-mac.sh` end to end with the new step.
- The tuned script with the light, mist and review fixes, and the preview
  script with its light check, blade sweep, projectile flight and rain.
- A Game-target build and cook with the editor-only plugin present. The UBT
  export above shows the game target leaves the plugin's module out, but
  nothing was compiled or cooked.
