# UI asset provenance

## Nyaagyu title key art

`Nyaagyu_Title_KeyArt.png` is original generated title-screen artwork made with
the built-in image generation tool on 2026-09-22. It is not an Unreal render or
evidence of current gameplay quality. Japanese menu text and the supplied SORA
mark are separate interface elements; no generated lettering is used.

## User-supplied SORA resistance insignia

`sora_logo_NOtext2.svg` is a byte-for-byte copy of the SVG supplied with the
game request. `SORA_Resistance_Logo.png` is a 1024 × 1024 transparent raster of
the same geometry and red fill, made with CairoSVG 2.7.1 and Cairo 1.18.6.
The SVG is the authoritative source. `sora_logo_manifest.json` records both
SHA-256 values and the Unreal asset path. The 5.8.2 editor import script checks
both hashes before importing the PNG as a UI texture, and the campaign HUD
displays it beside `SORA 抵抗軍` in the top bar.

This mark was supplied by the user for this project. It is not part of the
generated key art or the CC0 environment palette; no independent permission to
reuse the mark outside this game is asserted. Any public distribution of source
assets should be checked with the mark owner.

## Title key art generation prompt

> Use case: historical-scene. Asset type: original photoreal cinematic title-screen background for SORA Arena: Nyaagyu Rebellion, a Japanese-language serious samurai-cat first-person action game. Landscape 16:9, ideally 3840x2160. Create extraordinarily realistic live-action-film-quality anthropomorphic feline samurai in an Edo-period Japanese estate at blue hour after rain, subtly invaded by cold alien technology. Main subject to the right of center: a lean adult silver-gray tabby cat with anatomically convincing small feline eyes, natural wet individual fur and whiskers, alert dignified expression, proportionate head (not chibi), articulated feline paws gripping the properly wrapped tsuka of a sheathed Japanese katana at the hip. Weathered indigo haori and silk hakama, restrained dark lacquered samurai armor with fine lacing, worn cloth fibers. Three-quarter mid-thigh portrait, poised but not attacking. A compact original sci-fi matchlock rifle slung across back, subtle ceramic/metal cooling details. Behind: authentic weathered timber dojo, rain-soaked stone courtyard, warm paper lanterns, misty mountains and small hints of distant cold cyan alien machinery. Serious samurai drama, physically plausible materials, subtle lens and atmospheric depth, soft key light on detailed cat face and armor, cinematic muted palette of indigo, warm amber, weathered wood and cool mist. Preserve ample calm dark negative space in the left third for later Japanese menu text; compose image itself with no text, letters, numbers, logos, watermarks or interface. No human face, no toy proportions, no plastic fur, no cartoon, no glossy fantasy armor, no gore. This is generated key art, not a screenshot of an existing game.
