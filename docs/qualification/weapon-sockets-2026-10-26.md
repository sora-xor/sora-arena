# Weapon socket source correction, 2026-10-26

Twenty manifest-listed socketed LOD0 FBXs now use the exact bytes from Claude's
staged exports and UE 5.8.3 probe. Their 64 sockets use unit scale and the authored
axes. This is a source correction only: the game importer still uses the older
socketless weapon files, and runtime adoption and visual acceptance remain open.

## Selection and provenance

The selected kits are W00, W01, W02, W04–W10, W12, W14, W15, W17, W19 and W20.
W03/W11/W13/W16 remain held by the root manifest. Both staged W18 files belong
to Claude's separate unintegrated rebuild and were excluded. W19/W20 source
correction does not relax the runtime restriction on IDs 18 and above.

The 20 corrected FBXs total 69,863,104 bytes. Sixteen build records and the OWN
manifest were amended, with exact old/new hashes, the receipt, report hashes
and installer hash. The asset notices were regenerated. No blend, texture,
LOD1/LOD2, collision definition, frozen library or shared-checkout asset changed.

Claude's signed tool/evidence series `091426c4` through `ca096c98` is integrated.
The signed receipt is [runtime_weapon_ue_socket_probe.json](../art-direction/data/runtime_weapon_ue_socket_probe.json),
SHA256 `de97d992cac7dcf353fc695e1d82695935db3552f90b7d7477cbe61753888460`.
Root independently checked all 26 readback rows against the raw editor log,
the report/staged FBX hashes, signed tool sources, process records and natural exits.
Ten original evidence files are archived under
`Saved/Qualification/2026-10-26/weapon-socket-source/evidence/` in the source-validation worktree.
Independent stage review SHA256:
`0d18419fd7fbfd58b778a6a952b5cb9e3f0e69af5e633b899fc17ae9a5d225be`.

The first review assumed both staging runs used the exact `77e35643` exporter.
W14's s84 actually used the read-only Git patch subsequently signed in `2f2cf292`;
its recorded tool hash matches that signed source. The corrected audit binds each
run's actual tool bytes. The second audit initially looked for the editor exit in
the wrapper times file; it is in the wrapper log. Neither audit changed an asset.

## Installation and checks

Root's signed installer `e71476cf` validates the complete selection before writing
and installs the already-probed bytes. It replaces the unsafe in-place re-export
mode, which could change an FBX before its validation failed. It backs up every
destination and rolls back ordinary failures; process death can leave a partial
transaction recoverable from the archive. Eleven installer mutation/rollback
tests pass, with 20 pure export/gate/record tests, eight model tests and 15 source
runner tests. Installed-tool FBX parser tests stay outside source CI explicitly.

The installation journal is
`Saved/Qualification/2026-10-26/weapon-socket-source/install-archive/transaction.json`.
An independent CPython check using the installed Blender FBX parser verified
all 37 installed files against the transaction and all 20 FBX geometry arrays
against archived originals. Vertices differ only by the unit bake; UV/material
arrays and other authored arrays retain the original tolerances. The derived
tangent/basis tolerance remains 1e-4. Worst baked-position difference is
`2.7934223193101896e-05 cm`; all 64 modelled socket frames pass.
Installed CPU review SHA256:
`c07c63ae420355ec95a33bb6c3bafb6b6444474c20266da139b2e24889e32cd0`.
No Blender process, Unreal process, build or render was launched by root here.

Signed source `afd3f806e73a5abcb4361c2bca38a58e2c881e93`, tree
`e51f934cc92028f4d60c679a01a1914e7f9e7896`, then passes all **48 assets/tooling
source gates** (21 assets, 27 tooling). The runner exits 0 with clean unchanged
source; its exact command inventory, report and all 48 raw logs were independently
checked. This includes the asset ledger/notices, framing, complete source images
and the new socket tests. Review SHA256:
`a8c4495e13023637ffa6d506e4dd81f265bdd22ec444957b8197f3760323c4f1`.
Evidence directory: `Saved/Qualification/2026-10-26/weapon-socket-source-checks-attempt1`.
Gameplay, Rust and audio groups were not rerun locally for this source-art/tooling change.

## Evidence limits and next work

The historical s88 probe remains **editor exit 0 / wrapper exit 1**: W11 fails
at two corners with degenerate tangents. It is not relabelled as an all-pass run.
The selected 20 files passed its comparison and socket gates. Its full render
arrays were not retained, so later malformed-array checks cannot be retroactively
run on them. Actual saved import/readback of all selected LODs, PBR binding,
viewmodel admission, first-person framing and gameplay/capture checks remain.
Morph/character production, held weapons and the separate W18 rebuild remain open.

The preceding landing-drone source checkpoint `a5942a6d` separately passes all
114 CI gates in run `40271395969`; tested merge `1145e1360f53c98b6be9b9e5b96460090d34bb58`
has identical tree `cd0d1457145a544376900a08bd1076f5f800bcc6`. All five artifact
digests and raw logs authenticate. Review SHA256:
`21f478f957cc5f63edb81f4a60469d7612a21b0ff743488cec888c0e2b8238b8`.
That CI run predates this socket correction. The full release remains incomplete.
