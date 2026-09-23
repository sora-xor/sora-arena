# Dojo bokken material study: source and packaged review

The `DojoBokkenPBR` study keeps the playable bokken geometry and changes its UVs
and material treatment. The paired Blender 5.2.2 LTS Cycles source renders use
the same 1,600 × 900 camera, lighting, and exposure. Fine longitudinal oak grain
replaces broad artificial bands, but the smooth profile remains staff-like.
The generator is `scripts/art/render_dojo_bokken_pbr_comparison.py`; it pins the
input Blender source hashes and writes both frames without image edits.

## Packaged UE 5.8.3 A/B, 24 September 2026

These four 1,920 × 1,080 PNGs are unedited screenshots from a staged macOS game
build. Each original/candidate pair used the same first-person camera and
lighting. The candidate was imported only under
`/Game/Generated/ArtReview/DojoBokkenPBR`; the original gameplay mesh was not
replaced. The test used a temporary diagnostic `-SoraBokkenReview` hook, since
the ArtReview asset is deliberately not reachable in normal play.

| Pair | Playable original | PBR study | Observation |
| --- | --- | --- | --- |
| Default first-person pose | [Original](UE583_DojoBokken_Default_Original.png) | [PBR study](UE583_DojoBokken_Default_PBRStudy.png) | The small lower-right weapon has little visible difference. |
| Test-only close pose | [Original](UE583_DojoBokken_Close_Original.png) | [PBR study](UE583_DojoBokken_Close_PBRStudy.png) | Grip and end-grain read more clearly. The blade stays pale, nearly straight, and baton-like. |

The fixed player location was `(-1800, -1050, 90.15)` cm, view yaw `-105°`,
pitch `-2°`, and camera field of view `65°` in the opening dojo. The close pair
used an identical test-only weapon-root pose for both meshes; it is not the
playable pose. The capture log confirms the same two imported meshes each had
8,208 triangles, one UV channel, and the same four material slots. The importer
bound authored 2K albedo, DirectX normal, and ORM maps through a PBR master and
four instances. The full conventional fallback retained 8,208 triangles after
Nanite fallback generation; the early count was 1,176 until that setting was
applied. The importer now checks the count at the correct stage.

**Visual verdict: fail.** The material improves local detail, but the profile
does not read as a convincing bokutō in the packaged first-person view and the
exposed wood is too bright. This does not meet the requested photorealistic AAA
bar. Keep the study source-only; no playable asset, collision, or WorldBuilder
placement was promoted. Rework the silhouette, tip, edge/ridge facets, curvature,
grip proportions, and exposure before another admission test. The [All Japan
Kendo Federation's Jodo manual](https://www.kendo.or.jp/wp/wp-content/uploads/2020/12/jodo_manual.pdf)
gives a **modern Jodo reference**, not a universal Edo specification: 101.5 cm
overall, 24.2 cm grip, 1.5 cm curvature, and defined kissaki, shinogi, ha, and
mune. Its [competition rules](https://www.kendo.or.jp/wp/wp-content/uploads/2023/07/jodo-shiai_regulations.pdf)
repeat those dimensions. The inherited source is 106.7 cm overall with an
approximately 29.5 cm grip. Historical review remains necessary for the game's
specific school and period.

The independent Blender/FBX validator and UV audit passed. The first diagnostic
import caught a bad timing assumption in the strict importer; the corrected
import passed. A first cook attempt stalled during macOS AppKit startup before
engine cooking, and one bounded retry passed. Diagnostic UE revision was
`5.8.3-58210709+++UE5+Release-5.8`; build, cook, stage, and packaged launch
completed. The staged bundle identifier was `org.sora.soraarena`. This does not
qualify the project's pinned UE 5.8.2 release build or measure rendering cost,
Mac/Windows frame rate, or final hand placement. The 100 GiB planning disk
check was unmet during this bounded diagnostic; build/cook readiness still
passed and free space stayed above the 20 GiB stop floor.

Unedited screenshots and compressed raw logs are checksummed in
[`logs/SHA256SUMS.txt`](logs/SHA256SUMS.txt). The diagnostic GameMode and
WorldBuilder sources were restored byte-for-byte after capture to SHA-256
`81e89c34f0040ebd285b8ea7c7ae70c0eb2e5cc94029458824662a1276fa4e86`
and `37cfae6afa1f1e4bdefe94ec89fe80288b53efa6f92c80dcba91dfbfed2c0421`
respectively. Only the unreferenced ArtReview import remains in that isolated
checkout. The staged binary remains a temporary diagnostic artifact and is not
a release package.
