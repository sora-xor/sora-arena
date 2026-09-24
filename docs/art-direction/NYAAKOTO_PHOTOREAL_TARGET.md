# Nyaakoto: photoreal character target

![Nyaakoto photoreal art-direction target](Nyaakoto_Photoreal_Target.png)

This is an AI-generated **modeling reference**, derived from the player's supplied
Nyaakoto image. It is not a mesh, texture, animation, scanned asset, or screenshot
from the game. The supplied image establishes the grey tabby identity, white
muzzle, blue/vermillion armor, yumi, arrows, and katana. The exact project SORA
SVG, rather than a generated approximation, defines all finished kamon.
The earlier [facial study](../../Content/SourceArt/Characters/Hero/Reference/Nyaagyu_Photoreal_Concept_v1.png)
remains a separate anatomy reference; this plate adds full-body armor and weapon
direction.
The newer [four-view photoreal concept](../../Content/SourceArt/Characters/Hero/Reference/Nyaakoto_PhotorealTurnaround_v2.png)
adds front, side and back material/silhouette cues. It is generated art rather
than measured anatomy or a shippable asset; its short yumi and fittings must
not override the separately researched and modeled weapon sources.

The current Blender and packaged UE character remains visibly stylized. Closing
the gap requires original source-asset work, followed by repeatable in-engine
review:

- Sculpt the skull, brow, cheeks, muzzle, lips, and neck as connected feline
  anatomy. Remove the detached-pad silhouette and smooth spherical forehead.
  Preserve Nyaakoto's tabby markings and recognizable expression.
- Add directionally groomed, color-varied fur with clumping and silhouette
  breakup. The first-person and Mac variants need cards and mesh fur; supported
  Windows cinematic/world variants may use strand grooms. Whiskers require
  tapered rooted follicles and plausible asymmetric curvature.
- Rebuild eyes with feline lids, narrow natural scleral exposure, cornea depth,
  iris texture, and restrained catchlights. Test at gameplay camera distances.
- Model lamellar plates, cord lacing, quilting, buckles, leather, lacquer wear,
  stitching, hems, and paw-fit grip seams as distinct materials and geometry.
  Texture with consistent texel density and physically plausible roughness,
  normal, and ambient-occlusion channels; avoid uniformly glossy armor.
- Review yumi asymmetry, arrow carry, katana/saya placement, and historical
  construction against qualified Japanese references. Keep speculative sci-fi
  fittings visibly separable from the historical weapon forms.
- Evaluate the final asset in the **packaged UE 5.8.2** game at portrait,
  first-person, and arena distances under both neutral and campaign lighting.
  Record LOD transitions, shader compilation, and frame cost on the Windows
  and Mac presets. Blender stills and this concept cannot qualify rendering.

The reference was generated on 2026-09-24 from the user's screenshot for
art direction. It has no claim to historical reconstruction or shipped quality.
