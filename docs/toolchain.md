# Unreal and art toolchain

The project targets **Unreal Engine 5.8.3**, the Epic Games Launcher build with
changelist **58210709**. Tool versions are recorded in
[`scripts/toolchain/versions.json`](../scripts/toolchain/versions.json). These pins
are requirements, not evidence that every tool is installed or that the game has
been compiled. Run the doctor to inspect the actual machine.

## Release engine pin (approved deviation, 2026-09-25)

The approved plan specified **UE 5.8.2**. On **2026-09-25** the user approved
re-pinning the release engine to **UE 5.8.3** because 5.8.2 can no longer be
installed: the Launcher offers only 5.8.3, Epic's offline installer is limited
to eligible Developer Portal organizations, and this account receives HTTP 404
for Epic's private source repository (see the blockers below). The deviation was
reported as the plan required. The pin is the exact installed build:

| Field | Pinned value (from `Engine/Build/Build.version` and the engine's `.uplugin` files) |
| --- | --- |
| Version | **5.8.3** (`MajorVersion` 5, `MinorVersion` 8, `PatchVersion` 3) |
| Changelist | **58210709** |
| CompatibleChangelist | **55116800** |
| BranchName | `++UE5+Release-5.8` |
| IsPromotedBuild / IsLicenseeVersion | **1** / **0** |
| Editor version string | `5.8.3-58210709+++UE5+Release-5.8` (`unreal.SystemLibrary.get_engine_version()`) |
| Distribution | Epic Games Launcher binary (installed build: `Engine/Build/InstalledBuild.txt`); Launcher AppVersion `5.8.3-58210709+++UE5+Release-5.8-Mac` |
| Install path | `/Users/Shared/Epic Games/UE_5.8` (macOS); Windows default `C:\Program Files\Epic Games\UE_5.8` |
| Source commit | none (`source_commit: null`): a Launcher binary carries no Git revision; the changelists, branch and installed-build marker identify it |
| Engine plugins enabled by `SoraArena.uproject` | `PythonScriptPlugin` 1.0 (Version 1, beta), `EditorScriptingUtilities` 1.0 (Version 1, beta), and PythonScriptPlugin's dependency `ContentBrowserFileDataSource` 1.0 (Version 1) |
| Opt-in research plugins | `MeshPartition`, `MeshPartitionWater`, `PCGMeshPartitionInterop`, `MeshTerrainMode`, each 1.0 (Version 1, experimental); enabled only by `Plugins/SoraMeshTerrainResearch` in an isolated worktree |

`scripts/toolchain/doctor.py` (Mac) and `doctor-windows.ps1` compare the
version, both changelists, the branch, the promoted and licensee flags, the
installed-build marker and the project plugin versions with the engine
directory and fail closed on any difference; the Mesh Partition research runner and source audit also check the
research plugins. Editor-side import, validation and diagnostic scripts call
[`scripts/unreal/sora_engine_pin.py`](../scripts/unreal/sora_engine_pin.py),
which reads `versions.json` and requires the exact editor version string; host
preflights use the same module on `Build.version`, the installed-build marker
and plugin descriptors. There is no override flag.

Results recorded before the re-pin (2026-09-23 to 2026-09-24) came from this same
installed 5.8.3 build, run as opt-in "interim diagnostics" in isolated
worktrees. Their records keep that label: they establish what those runs did,
not release qualification. Windows builds, release packaging/signing, played
gameplay, rendered quality and performance still need runs under this pin.

## Rust toolchain pin

The Rust kernel, native parity reference and cargo gates use **Rust 1.97.1**
(commit `8bab26f4f68e0e26f0bb7960be334d5b520ea452`), recorded under `rust` in
`versions.json`. The repository-root `rust-toolchain.toml` selects channel
`1.97.1` (minimal profile with `rustfmt` and `clippy`), so `cargo` in this
checkout uses it. `doctor.py` checks that file's channel and runs `rustc -vV` in
the repository with `RUSTUP_AUTO_INSTALL=0`, requiring the exact release and
commit hash; a missing toolchain fails instead of downloading. Its JSON reports
`rust_ready`. `python3 scripts/toolchain/test_doctor_rust.py` tests this check
with a faked compiler.

## Verified on this workstation (2026-09-23)

| Component | Observed state |
| --- | --- |
| Host | Apple M1 Ultra, 128 GiB memory, macOS 27.0, arm64 |
| Blender | **5.2.2 LTS**, installed using Homebrew from Blender's official download; executed successfully in background mode |
| Git LFS | **3.8.0**, installed; LFS filters and hooks initialized for this repository only |
| Epic Games Launcher | **20.3.2**, installed at `~/Applications/SORAToolchain/Epic Games Launcher.app`; bundle version and arm64 executable verified |
| Existing Epic launcher | The older `/Applications` copy self-updated to 18.1.2 during inspection; it was preserved |
| Unreal Engine | **5.2.0** existed at `/Users/Shared/Epic Games/UE_5.2`; the Launcher installed **5.8.3** at `/Users/Shared/Epic Games/UE_5.8`; **5.8.2 was not installable** (5.8.3 became the pin on 2026-09-25) |
| Xcode | **26.1.1, build 17B100**, installed at `~/Applications/SORAToolchain/Xcode_26.1.1.app`; full Apple code-signature verification passed, SDK **26.1** found, and first-launch status reports complete. Existing **27.0** is preserved |
| Metal Toolchain | Apple's separate **17B54** component was downloaded through the selected Xcode; `xcrun --sdk macosx metal -v` reports compiler **32023.830**. Xcode's SDK and first-launch checks alone did not install this compiler. |
| Engine revision | The installed 5.8.3 `Build.version` reports promoted build changelist **58210709** (compatible changelist **55116800**) on `++UE5+Release-5.8`; as a Launcher binary it has no source commit |
| UE 5.8 compilation / packaging / runtime | The project Mac editor and game targets compile in isolated **5.8.3**. After both original-asset and palette imports, the editor validator loads **207** expected packages, including revised terrain/foliage, the provision storehouse, separate katana/saya and PBR bindings; editor and cooked-game automation load three Nyaakoto LODs and 23 material slots. The latest Mac diagnostic cook completed with **795 packages cooked** and seven platform skips. UAT staged a signed app using pak/IoStore with bundle identifier `org.sora.soraarena`; the headless packaged LOD test exited 0. These were interim diagnostics before the re-pin; a release build under the pin, the Windows build, visual quality and gameplay qualification remain open. |

The machine's global `xcode-select` remains pointed at Command Line Tools. These
scripts select Xcode and its matching `SDKROOT` only for their own process; they
do not change global settings. This avoids mixing the Xcode 26 linker with the
host's inherited Command Line Tools 27 SDK.
Xcode 27 is a pin mismatch, not a claim that every use with UE 5.8 is impossible.

### Installation blockers actually observed

- The currently authenticated GitHub account receives **HTTP 404** for
  `EpicGames/UnrealEngine`; a direct HTTPS Git request cannot authenticate
  noninteractively. The private source repository must become accessible before
  an engine source build can be downloaded or its exact revision pinned.
- The current Launcher Library shows a **5.8.3** tile and no 5.8.2 choice
  in its version selector. The signed-in Epic account installed 5.8.3 and its
  `Build.version` reports changelist 58210709. Exact 5.8.2 needs Epic's
  private source access or an existing licensed installation; the local GitHub
  account still receives HTTP 404 for that repository. Epic released 5.8.3 on 2026-09-22, so the original
  description of 5.8.2 as the latest hotfix is stale. Resolved on 2026-09-25:
  the user approved 5.8.3 as the release pin (see above).
- Epic's offline macOS installer is restricted to eligible Developer Portal
  organizations; it is not an account-free route to the historical hotfix.
- Before the re-pin, the Mac editor target compiled with the exact 5.8.3
  interim opt-in in an isolated worktree, where the source art and palette
  imports were also isolated. A diagnostic game target also compiled and a
  cooked package launched. Those runs did not establish played gameplay,
  rendered art quality, Windows parity, or release packaging/signing.
- Direct command-line expansion of the Apple download was denied by OS file
  permissions. Normal Finder/Archive Utility extraction succeeded, and Apple's
  complete app signature verified. Moving into `/Applications` was also denied,
  so an ordinary copy installed Xcode in the user-owned toolchain directory.
  The copied app's complete signature, version, SDK, and first-launch status
  were verified successfully. No security protection was disabled.

No credentials were extracted, no paid assets/software were purchased, and no
Apple or Epic license agreement was accepted on the user's behalf.

## Install and verify free tools

From the project root:

```sh
scripts/toolchain/install-tools.sh
scripts/toolchain/doctor.py
scripts/toolchain/doctor.py --json
```

The installer uses Homebrew for Git LFS and Blender, verifies that the registry
versions match the project pins before installation, and runs a real headless
Blender check. It stops if the registry has moved to other versions instead of
silently upgrading the project's toolchain. Homebrew must already be installed.
It does not provision Epic/Apple accounts, download Unreal, or change global
Git/Xcode configuration.

The host checks under `scripts/unreal` also import two pinned Python packages,
PyYAML 6.0.3 (the chapter scripts' YAML, for `build_campaign_data.py` and
`validate_content.py`) and fontTools 4.38.0 (the glyph check). Install them with
`pip3 install --user -r scripts/requirements.txt`; the doctor does not check
them yet.

The doctor checks the engine identity in the pin table (exact
`Build.version` version, changelist, compatible changelist, branch and
promoted/licensee flags; the installed-build marker; project plugin descriptor
versions), the Mac `Build.sh`,
an executable UnrealEditor binary (so a partial Launcher download cannot appear
ready), selected Xcode, SDK, first-launch setup and executable Metal compiler,
actual Blender/Git LFS command output, repository LFS setup, the root project
file, disk space and the Rust pin. Exit status **1** indicates a missing or
mismatched check; status **0** indicates these presence/version checks passed.
Its `build_ready` JSON flag checks code-build prerequisites (engine identity,
Xcode/SDK and project); `cook_ready` additionally requires a working Metal
compiler. Neither is a build or cook result. The Mac wrappers read those flags
and the JSON's `engine_root`, `developer_dir` and `sdk_root`. The JSON also
reports `pinned_engine_version` (the editor version string), `rust_ready` and
`all_checks_pass`, which set the doctor's summary and exit status.

### Mac build, cook, stage and editor

```sh
export UE_ROOT='/Users/Shared/Epic Games/UE_5.8'
scripts/toolchain/doctor.py --json
scripts/toolchain/build-mac.sh Development
scripts/toolchain/build-mac.sh Development Game
scripts/toolchain/cook-mac.sh
scripts/toolchain/stage-mac.sh /tmp/sora-arena-mac
scripts/toolchain/test-packaged-mac.sh /tmp/sora-arena-mac
scripts/toolchain/run-editor.sh
```

Every wrapper first requires the doctor's `build_ready` (`cook_ready` for the
cook). There is no engine-selection override. Compile, launch, cook
or stage results do not by themselves qualify a release or prove gameplay or
rendering. `python3 scripts/toolchain/test_doctor_pin.py` runs host-only
fake-engine tests for the exact version/changelist/branch/promoted and licensee
flags/distribution/plugin pin and the Rust wiring; it never invokes Unreal.

On this Mac, UBT compiled and linked the game target but its nested Xcode
post-build invocation failed at the generated `Touch UBT generated tiles`
pre-action. The game wrapper retries the exact generated scheme only for that
specific failure, verifies the signed `.app`, then invokes Unreal's own
`WriteMetadata` mode for the matching build products and target receipt. A
different build failure still exits nonzero. UAT staging requires that receipt.
Before the re-pin, the isolated 5.8.3 diagnostic completed UAT stage/package/archive in
74 seconds; the archived app passed strict `codesign` verification and a
`-NullRHI -unattended -ExecCmds=Quit` startup smoke. Its pak contains the
Japanese `Game.locmeta` and `ja/Game.locres`. The packaged
`SoraArena.Localization.NativeJapanese` automation also passed, reporting
`native=ja active=ja title=猫柳生 english_subtitle=present`; a visual Japanese
UI and subtitle readability check remains open. That recovery was observed in
the isolated interim worktree; it still has to be exercised from a release
checkout under the pin.

UAT archives the app into `ARCHIVE_DIRECTORY/Mac/` unless a component of that
path already starts with `Mac` (case-insensitive, `DeploymentContext.cs`), in
which case the app lands directly in `ARCHIVE_DIRECTORY`; `stage-mac.sh` and
`test-packaged-mac.sh` both follow that rule. On a restage, Xcode's incremental
package build syncs the newly staged data into the app but skips its CodeSign
step when the executable is unchanged, which left a changed pak outside the
seal. `stage-mac.sh` now verifies the archived app strictly. Only when every
complaint is a staged file under `Contents/UE`, it signs the app again as Xcode
does (ad hoc, with the app's own entitlements). Any other signature failure
stops the script.

The cook commandlet starts the editor, which wrote an AndroidFileServer
`SecurityToken` into `Config/DefaultEngine.ini` during the first cook. That
cook's package was staged with the token in its config. `cook-mac.sh` now uses
the editor runners' Config guard and keeps its log under `Saved/Cook/`. The
token block was removed from the working tree and never committed, and the
package was restaged from the clean Config.

`scripts/toolchain/test-packaged-mac.sh ARCHIVE_DIRECTORY [Filter] [output]`
tests the staged app without the editor. It checks the bundle identifier, a
strict signature and the staged kernel, Connect bridge and data. It runs a
`-NullRHI` startup smoke (default map with `SoraGameMode`, language `ja`, exit
0, no fatal error, assertion or ensure) and then `Automation RunTests <Filter>`
under `-RenderOffscreen`. It fails unless every test reports Success in
Unreal's JSON report and no cooked material falls back to the default material
for a missing usage flag. UE signs the app with the App Sandbox, so every
launch gets an empty `-UserDir` inside
`~/Library/Containers/org.sora.soraarena/Data/tmp/`, copied afterwards to
`<output>/app-data`. The player's saves are never touched. A game lists only
`ClientContext` tests; the four editor-only tests stay with
`run-automation-mac.sh`.

Two UE 5.8.3 engine races in Development builds shape how the script launches
the package:

- **Startup crash (LLM teardown).** A Development or Test Mac build starts
  Unreal's low-level memory tracker (LLM) and, unless `-LLM` is given, turns it
  off and frees its trackers early in the game thread's PreInit
  (`FLLMGlobals::ProcessCommandLineInner`). On the Mac the main thread is at
  that moment still handling AppKit's launch Apple event, and LaunchServices
  allocates inside an `FLLMScope` in `FMallocBinned3::PushNewPoolToFront`.
  `FLLMScope` takes no lock against that teardown, so when the trackers go away
  inside the scope its `PopTag` fails and the app dies with `SIGSEGV` before
  its first log line. That happened in 4 of 26 launches on 2026-09-26 and in
  1 of 30 in a later probe. The script launches with `-LLM`, which leaves the
  tracker on, so nothing is torn down. With `-LLM`, 70 probe launches of the
  staged package gave 0 crashes. Shipping builds compile LLM out
  (`LowLevelMemTrackerDefines.h`). A Development package started without
  `-LLM`, for example from Finder, can still crash this way.
- **Exit ensure (I/O teardown).** During engine exit, `~FIoDispatcherImpl`
  unbinds its file backend's wake-up delegate while a read that completes on
  the backend thread may still be executing it. The Development build's
  delegate race detector then reports up to three ensures under
  `FEngineLoop::Exit`, in `FIoDispatcherImpl` and `FFileIoStore` teardown. The
  smoke quits on its first frame with reads still in flight, and hit this in
  2 of 109 such launches on 2026-09-26. The smoke check names only that exact
  case, with no project frame in the stack, as a known engine race and does
  not fail on it. Any other ensure fails the smoke.

On 2026-09-26 the main checkout (source as of `d70c30b`, kernel
`libarena_ffi.dylib` sha256 `1bd6e8fa…d494`) first packaged into
`Local/Packages/mac-wavec-baseline`: 76 of 79 client-context tests passed,
three failed only in the package, and eight cooked materials drew as the
default material. Fixing them took four changes:

- **`Input.StateGatedKeys`.** In a cooked game the `Block` action FName reads
  back as `bLock`: FNames compare without case, and a game build keeps only
  the first spelling it registered. `SoraInput::StatesFor` and
  `FindRemappable` compared names with case-sensitive `Strcmp`, which gave
  Block no input states. The rebind dialog's conflict check therefore ignored
  Block mappings, and a saved layout that rebinds Block would have been
  rejected. Both functions now compare with `Stricmp`.
- **`Practice.MarksTextScoreboard`.** The test reads the SORA mon's vertex
  positions to prove it stands upright, but a cooked build releases vertex
  data after upload. Under Metal the read saw stale memory; under `-NullRHI`
  it crashed the game thread. `import_sora_kamon_mon.py` now sets
  `allow_cpu_access` on `SM_SoraKamon`, which keeps those positions in the
  cooked game. The validator requires the flag, and the test asserts it before
  it reads.
- **`Boss.Tarifa`.** The root cause is the navigation mesh, not the parry. A
  component that got its static mesh while it still had the default blocking
  collision entered the navigation octree at the origin. In a cooked game,
  where meshes are never still compiling at that point, the entry stayed after
  the builder turned collision off. The estate terrain tiles, trees, props,
  practice parts, bodies and boss-hazard shapes did this. At the next rebuild,
  holes appeared wherever those visual shapes stood. In the package, Tarifa
  walked around her own painted steam zone at the wet slot; the editor sent
  her straight at the hero. That left a loom automaton between her and the
  hero, where it blocked the tether's line, so no strike landed to parry.
  `ASoraWorldBuilder::Shape` now sets collision and navigation before the
  mesh. Every other visual-only mesh sets `SetCanEverAffectNavigation(false)`
  first. After the fix the packaged navigation octree near the wet slot holds
  only the ground, and the path is straight, as in the editor. The new test
  `SoraArena.AI.VisualMeshesOffNavigation` fails if any
  non-navigation-relevant mesh is in the octree or if a painted zone cuts the
  rebuilt mesh. The Tarifa test now prints the boss timeline, with positions,
  whenever a lash is not met.
- **Default materials.** `M_Nyaagyu_PBR`, the parent of every `MI_Nyaagyu_*`
  instance, and `M_ArenaSurface` now carry
  `used_with_instanced_static_meshes`. The practice glow uses the new unlit
  additive `M_ArenaGlow` ("Color" parameter, instanced-mesh usage) in place of
  the engine's `EmissiveMeshMaterial`, which lacks that usage. The validator
  requires all three flags.

After `import-mac.sh` (280 packages), `build-mac.sh Development Game`,
`cook-mac.sh` (919 cooked, 7 skipped by platform, 0 errors, 0 warnings, Config
unchanged) and `stage-mac.sh Local/Packages/mac-capture-green`, the full
packaged run passed (`Saved/PackagedAutomation/green-final1`). The smoke passed,
the package found all 80 client-context tests and **80 passed**, and no
cooked material fell back to the default material. That includes
`Campaign.Playthrough`, `Practice.FullMatches`, `UIRendered.FrontEndScreens`
and the new navigation test. The four editor-only tests passed in
`run-automation-mac.sh`. The fixed materials show in the practice arenas'
instanced dressing; the front-end screenshots (title and pause over the
training arena) look the same before and after.

## Finish Unreal and Xcode provisioning

1. Install **UE 5.8.3** from the Epic Games Launcher into the default
   `/Users/Shared/Epic Games/UE_5.8` (or set `UE_ROOT`). The doctor must report
   changelist 58210709, compatible changelist 55116800, branch
   `++UE5+Release-5.8`, an installed build and the pinned plugin versions. A
   Launcher that serves any other build is a pin change: it needs explicit
   approval, a `versions.json` update and requalification, never a local
   override. Keep other engine installations separate.
2. On another Mac, download **Xcode 26.1.1** from Apple Developer downloads.
   Install it alongside other Xcode versions. This workstation uses
   `~/Applications/SORAToolchain/Xcode_26.1.1.app`; a separate
   `/Applications/Xcode_26.1.1.app` also works. Complete any Apple sign-in and
   license/setup prompts in the normal UI. Do not replace another Xcode version
   or globally change `xcode-select` for this project.
   Install the separate Apple Metal compiler component with
   `DEVELOPER_DIR=/path/to/Xcode_26.1.1.app/Contents/Developer xcodebuild -downloadComponent MetalToolchain`;
   verify `DEVELOPER_DIR=/path/to/Xcode_26.1.1.app/Contents/Developer xcrun --sdk macosx metal -v` succeeds.
3. Set paths and run the doctor, then build:

```sh
export UE_ROOT='/Users/Shared/Epic Games/UE_5.8'
export SORA_DEVELOPER_DIR="$HOME/Applications/SORAToolchain/Xcode_26.1.1.app/Contents/Developer"
scripts/toolchain/doctor.py
scripts/toolchain/build-mac.sh Development
scripts/toolchain/run-editor.sh
```

`UE_ROOT` is the engine directory containing `Engine/`. If `SORA_DEVELOPER_DIR` is
unset, the scripts honor `DEVELOPER_DIR`, then prefer the user-owned Xcode 26.1.1
app, then `/Applications/Xcode_26.1.1.app`, and finally inspect
`/Applications/Xcode.app`. The doctor rejects a different
Xcode version. The build command infers the editor target from the single root
`.uproject`, uses arm64, and preserves the project's engine association. It does
not fall back to UE 5.2.

Epic's Mac requirements page recommends Xcode 26.1.1 for 5.8, while portions of
the release notes retain different older guidance. Treat a successful build,
shader compilation, cook and packaged launch as the compatibility acceptance
checks; the version table alone does not establish compatibility.

## Windows, Linux, and rendering validation

- Windows client: use the pinned MSVC/UE build and diagnostic path below. The
  Rust kernel alone has a GNU cross-build on this Mac; no Windows executable
  has been run and the UE/Connect clients have not been built there.
- Linux server: use an x86-64 Linux builder with **Ubuntu 22.04** and Epic's
  **v26 / clang 20.1.8** toolchain, or Epic's supported Windows-to-Linux
  cross-compilation workflow. Mac-to-Linux cross-compilation is not supported by
  that workflow. A server target does not by itself establish production hosting
  or a trusted outcome-verification system.
- Validate photoreal rendering on actual Windows target hardware. On this M1
  workstation, use software Lumen and mesh/card fur with conventional geometry
  and shadow fallbacks. Epic lists Mac Nanite/Virtual Shadow Maps as M2+ Beta,
  hardware Lumen/MegaLights as M2+ Experimental, and strand grooms as M2+ with
  Shader Model 6. First-person rendering currently does not support groom
  strands; first-person paws/arms need mesh/card fur even when world-space
  characters have optional strand grooming.

### Windows project build and staging

For an early, **static-only** check on this M1 Ultra, Rust 1.93.1 (the toolchain
`check_windows_kernel_crossbuild.py` still selects, not yet the 1.97.1 pin)
Windows GNU target and free MinGW GCC 16.2.0 can cross-build `arena-ffi`:

```sh
rustup target add x86_64-pc-windows-gnu --toolchain 1.93.1
python3 scripts/toolchain/check_windows_kernel_crossbuild.py
```

The script builds offline with `--locked`, checks the PE x86-64 DLL, compiles
Windows C assertions for all eleven ABI struct sizes/alignments, and compares
all fifteen exported functions to the C header. On 2026-09-23 the resulting
DLL SHA-256 was
`24f3a95e51fda5b4c2d01b5987edc90ad667505b0338602f0a7984adf6ed6f5e`.
This GNU cross-build does **not** replace the required Windows MSVC/Unreal
build, execute the DLL, compare simulation replays, or qualify on-chain proofs.

On a 64-bit Windows machine, install **UE 5.8.3** from the Epic Games Launcher
(changelist 58210709), Visual
Studio **2022 17.14** with MSVC **14.44.35207**, Windows SDK
**10.0.22621.0**, native x86-64 Rust MSVC, and Python 3. The scripts never
install or upgrade them. In PowerShell, from the repository root:

```powershell
$env:UE_ROOT = 'C:\Program Files\Epic Games\UE_5.8'
rustup target add x86_64-pc-windows-msvc
.\scripts\toolchain\doctor-windows.ps1
.\scripts\toolchain\doctor-windows.ps1 -Json
.\scripts\toolchain\build-windows.ps1 -Configuration Development
```

`UE_ROOT` can point to another licensed installation; omit it to use the
recorded default. The read-only doctor verifies `Engine/Build/Build.version`
reports **exactly 5.8.3** with the pinned changelist, compatible changelist,
branch and promoted/licensee flags, `InstalledBuild.txt`, the pinned project plugin descriptor versions,
`Build.bat`, a complete nonpreview 17.14 Visual
Studio instance found through `vswhere`, exact MSVC compiler/linker and SDK
headers/libraries/tools, the Rust MSVC host and installed target, Python 3,
project C++/Rust source, and the project-scoped UBT pins. It exits nonzero on
any mismatch and does not claim a successful compilation.

The build script first requires a passing doctor. It copies the pinned
`Config/UnrealBuildTool/BuildConfiguration.xml` into the project's ignored
`Saved/UnrealBuildTool/BuildConfiguration.xml` only if that local file is
absent. An existing local file must specify the same compiler and SDK or the
doctor rejects it. This follows Epic's [project-specific UBT configuration
location](https://dev.epicgames.com/documentation/unreal-engine/build-configuration-for-unreal-engine)
without changing machine-wide Visual Studio settings. The UBT file selects
Visual Studio 2022, exact MSVC, and exact SDK; the build command repeats the
compiler selection explicitly.

It then builds the real Rust FFI DLL with `cargo --locked`, stages it through
`stage_kernel.py --platform Win64` after ABI/execution checks, runs the pinned
94-case native parity fixture and negative guard tests, and invokes the UE
`SoraArenaEditor Win64` target. Each failure stops the sequence. The Windows
parity fixture must pass unchanged against the macOS reference before any
cross-platform parity claim. The script builds an editor diagnostic; it does
not cook, package, sign, visually inspect, measure frame rate, run a live P2P
match, or establish proof-qualified settlement. Neither the Windows toolchain
nor the script has been run on Windows yet.

## Official references

- [UE 5.8.2 hotfix](https://forums.unrealengine.com/t/5-8-2-hotfix-released/2746335) (original plan pin)
- [UE 5.8.3 hotfix](https://forums.unrealengine.com/t/5-8-3-hotfix-released/2833315) (release pin since 2026-09-25)
- [UE 5.8 release notes and platform toolchains](https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-8-release-notes)
- [Epic source access](https://www.unrealengine.com/en-US/ue-on-github)
- [Epic Launcher installation steps](https://dev.epicgames.com/documentation/unreal-engine/install-unreal-engine)
- [Official offline installer access](https://dev.epicgames.com/documentation/unreal-engine/offline-installer-of-unreal-engine)
- [Dedicated-server source build requirements](https://dev.epicgames.com/documentation/unreal-engine/setting-up-dedicated-servers-in-unreal-engine)
- [Mac requirements](https://dev.epicgames.com/documentation/unreal-engine/macos-development-requirements-for-unreal-engine)
- [Linux requirements](https://dev.epicgames.com/documentation/unreal-engine/linux-development-requirements-for-unreal-engine)
- [Apple Xcode downloads](https://developer.apple.com/download/all/?q=Xcode%2026.1.1)
- [Blender downloads](https://www.blender.org/download/)
- [Groom platform support](https://dev.epicgames.com/documentation/unreal-engine/groom-platform-support-in-unreal-engine)
- [First-person rendering](https://dev.epicgames.com/documentation/unreal-engine/first-person-rendering)
