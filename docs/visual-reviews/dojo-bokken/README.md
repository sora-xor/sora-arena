# Dojo bokken source comparison

These are unedited Blender 5.2.2 LTS Cycles renders of the original and the
PBR/UV0 study at the same close camera, lighting, exposure, and 1,600 × 900
resolution. The new material replaces artificial broad wave bands with finer
longitudinal oak grain. The silhouette still reads as a smooth baton, and the
close image does not establish AAA photorealism. This is a **source-only**
improvement; no gameplay asset or material has been replaced. Packaged UE5.8.2
first-person A/B, collision/hand placement, shader cost, and Mac/Windows
performance remain untested.

The generator is `scripts/art/render_dojo_bokken_pbr_comparison.py`. It pins
the input Blender source hashes and writes both frames without image edits.
