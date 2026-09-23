# Nyaakoto fur swatch sources

These three project-generated bitmap swatches are authored inputs to
`scripts/art/create_nyaakoto_pbr_textures.py`. They are neither photographs of
a real animal nor scanned displacement. The script makes an exact-wrap tile
and derives a conservative high-frequency normal and roughness estimate. The
photographic-looking fibers improve surface detail but do not replace a
sculpted head, groom, region-specific markings, or engine visual review.

The built-in OpenAI image generation tool produced each square source from a
text-only prompt. No third-party stock texture or separable restricted asset
is used. The project user's right to use the output, including in a commercial
game, rests on the [OpenAI Terms of Use, Content ownership
section](https://openai.com/policies/row-terms-of-use/), subject to those terms.
The manifest pins the exact prompt, generated-output ID, and SHA-256 of each
copied source file. No external source URL exists for these first-party outputs.

| File | Prompt | Role |
| --- | --- | --- |
| `Nyaakoto_GreyFur_ImageGen_v1.png` | Square top-down macro photograph-like swatch of dense short grey tabby cat fur, fine guard hairs and undercoat, warm grey/charcoal/beige agouti variation, even diffused light, no anatomy or background, visually seamless. | Nyaakoto grey coat |
| `Nyaakoto_WhiteFur_ImageGen_v1.png` | Square top-down macro photograph-like swatch of dense short creamy-white cat fur, fine guard hairs and ivory/pale grey variation, even diffused light, no anatomy or background, visually seamless. | Cream muzzle, paws, throat |
| `Nyaakoto_CharcoalFur_ImageGen_v1.png` | Square top-down macro photograph-like swatch of dense short charcoal and smoky-brown cat fur, fine guard hairs and low-contrast dark variation, even diffused light, no anatomy or background, visually seamless. | Dark tabby markings |

The full production prompts are recorded verbatim in `../manifest.json`; they
also specified 4–8 mm fibers where applicable, albedo-safe lighting without
hotspots or vignette, and no text or watermark.
The raw generated edges are only approximately continuous. The generated PBR
outputs are mathematically processed and independently checked for exact edge
texels; the source swatches themselves are not tiled directly in Unreal.
