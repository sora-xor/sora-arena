# October 27 Mac package — 1b6 save and dojo restoration

The fresh Development package at signed
`1b6dfadc86a22f779e2096d05d88f71d7042e164`, tree
`a50a26e0ca1b1021897741501e6cd61661dc25aa`, passes all **271 selected client
tests with zero selected errors or warnings**. Smoke and separate rendered
fresh startup also pass. The default-save and four required dojo-rail warnings
seen in the earlier [5b package](mac-package-5b45-2026-10-27.md) are absent from
all three launches. This remains a scoped WIP result, not release acceptance.

The package includes the [first-launch fix and restored dojo modules](first-launch-dojo-restore-2026-10-27.md).
The 46 Generated files were copied from the reviewed source-validation output
only after a verified full backup and Claude's safe-boundary confirmation.
They are ignored local outputs, reproducible through the production importers;
they are not distributed as tracked Git assets.

Editor, Game, cook, stage and client phases finish naturally from 07:11:04 UTC
to 07:41:05 UTC. The Game phase retains the known generated Xcode pre-action
failure and successful exact-scheme recovery. Game/stage logs retain two
missing MetalShaderConverter include-directory warnings each. Each client
startup retains the EnhancedInput initialization warning, with generic exit
warnings in the rendered launches. These are outside the selected-test count;
no claim of completely warning-free logs is made.

UE 5.8.3 / CL 58210709 and project-scoped Xcode 26.1.1 run on the M2 Ultra.
Global Xcode selection is unchanged. The package launcher retains its
3,600-second SIGALRM limit; all launches exit naturally before it. The outer
guards observe without signalling children. Automation takes 1,544.97 seconds
in this run. Earlier and current elapsed times are recorded, but background
workload and generated assets differ; this is not a controlled performance
comparison or performance acceptance.

Independent review verifies 93 original evidence files, all five phase
receipts, unchanged input manifests, 2,689 tracked inputs including 1,417 LFS
payloads, exact discovery/start/completion names, the signed bundle and ABI30
native bridge, and staged credits/Arabic font against source. The bundle has
64 files and 1,617,318,151 bytes. Native producer remains
`10ad7daddf73212e81496620aba628ebf214ab72`.

All 20 original 1280×720 PNGs were displayed directly and authenticated for
hashes, PNG CRCs and dimensions. Title, keyboard/pad menus, settings, selection,
credits and dialogs are legible in these sampled views. Scrolled content is
clipped at its viewport while selected controls and footers remain visible.
The pause background still has repetitive timber/coffers, bright highlights
and proxy props. No validation image was edited or upscaled. Other resolutions,
every scroll position, ordinary input usability and final art remain open.

All 125 source CI gates pass in
[run 40464428877](https://github.com/sora-xor/sora-arena/actions/runs/40464428877).
The five archives, exact commands, reports and raw logs are authenticated;
tested merge `d612f6178992584087e6db4478524c0807c1ab35` has the identical tree.

Local evidence: `Saved/Qualification/2026-10-27/package-1b6dfadc-attempt1` in
the integration worktree. Preserved app: `Local/Packages/mac-1b6dfadc/SoraArena.app`.
All prior packages, failed attempts and reviewer failures remain preserved.

| Record | SHA-256 |
| --- | --- |
| Original status | `d70d7a5dacb59c8447c5043c3fb0c6c964e91eceaaedd1d449ccba7ca585c444` |
| Bundle/test review | `00cceb801bbd77f3b2d40cf99a0571318df47dd6dc0c55197aa18af6ec641833` |
| Original-image review | `369305bd6ab9620fabec8130ce75b00cd12dce4637080a53f894c3c97e4d468b` |
| Startup/timing review | `9f5764083a2088c1fb98a9041453583cc0115b6136b317c5fe2bf4ce05a397f8` |
| Candidate manifest | `2170207330fc130f2d45fedce3ccbf893f2bb0f74eab31293b247cae7a34ece8` |
| Strict source-CI review | `ded12d6bfd5a1a8a89d722a6e06f43aa412409fd55948ad4f3805f8605e2cbf9` |

Workshop paw contact/presenter and working regions, remaining authored spaces,
final art, ordinary campaign play, actual M1, Windows, performance,
clean-machine distribution and network/settlement qualification remain open.
