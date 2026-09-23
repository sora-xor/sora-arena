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
