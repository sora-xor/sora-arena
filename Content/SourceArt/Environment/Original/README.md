# Original Edo environment props

`Edo_Alien_Props.blend` contains editable lantern, Nyaagyu estate gate, and
alien debt kiosk source art. The gate's front lintel now carries the exact two
paths from the user-supplied `Content/SourceArt/UI/sora_logo_NOtext2.svg` as the
resistance kamon. Its `猫柳生` characters are a name plaque, not an invented crest.
The SVG remains unchanged and its SHA-256 is pinned in `manifest.json`.

Regenerate and verify from the repository root with Blender 5.2.2:

```sh
blender -b --factory-startup --python scripts/art/create_edo_environment_props.py
blender -b Content/SourceArt/Environment/Original/Edo_Alien_Props.blend \
  --python scripts/art/validate_edo_environment_props.py
```

These are source meshes and Blender review renders. The generated FBX files
retain material slots and authored UCX collision proxies; they do not establish
photoreal material quality or Unreal 5.8.2 rendering performance.

The gate now has tapered, gently inward-leaning round timber posts instead of
square blocks. Each post has a deliberately irregular hewn profile, separate
aged-iron collars and brass cap, and three small areas of exposed timber under
the vermilion lacquer. The editable gate has 30 parts and the FBX render mesh
has 17,800 source triangles; its three UCX proxies and exact SORA SVG relief
remain unchanged. A narrow UE 5.8.3 Mac diagnostic reimport retained all five
material zones and cooked without shader errors. The Blender group render is
a source inspection only. The [packaged Estate entrance
review](../../../../docs/visual-reviews/UE583_Estate_PathQuilt_Entrance_FailedGate.png)
shows the round posts in gameplay. Their silhouette is an improvement over the
square blockout, while the bright lacquer, sparse surroundings, and overall
composition still fall short of the photoreal target. That diagnostic also
contained a rejected path-atlas candidate; the main game kept its earlier
path. Exact UE 5.8.2, Windows Nanite, and measured performance gates remain.
