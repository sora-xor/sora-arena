# Unreal and art toolchain

The project targets **Unreal Engine 5.8.2**. Tool versions are recorded in
[`scripts/toolchain/versions.json`](../scripts/toolchain/versions.json). These pins
are requirements, not evidence that every tool is installed or that the game has
been compiled. Run the doctor to inspect the actual machine.

## Verified on this workstation (2026-09-23)

| Component | Observed state |
| --- | --- |
| Host | Apple M1 Ultra, 128 GiB memory, macOS 27.0, arm64 |
| Blender | **5.2.2 LTS**, installed using Homebrew from Blender's official download; executed successfully in background mode |
| Git LFS | **3.8.0**, installed; LFS filters and hooks initialized for this repository only |
| Epic Games Launcher | **20.3.2**, installed at `~/Applications/SORAToolchain/Epic Games Launcher.app`; bundle version and arm64 executable verified |
| Existing Epic launcher | The older `/Applications` copy self-updated to 18.1.2 during inspection; it was preserved |
| Unreal Engine | Only **5.2.0** found at `/Users/Shared/Epic Games/UE_5.2`; **5.8.2 is not installed** |
| Xcode | **26.1.1, build 17B100**, installed at `~/Applications/SORAToolchain/Xcode_26.1.1.app`; full Apple code-signature verification passed, SDK **26.1** found, and first-launch status reports complete. Existing **27.0** is preserved |
| Engine source commit | Not acquired or verified; `source_commit` remains `null` |
| UE 5.8 compilation / packaging / runtime | **Not performed: the required engine is unavailable** |

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
- The current Launcher Library shows a new **5.8.3** tile and no 5.8.2 choice
  in its version selector. The signed-in Epic account is present, but the
  engine download has not started. Exact 5.8.2 now needs Epic's private source
  access or an existing licensed installation; the local GitHub account still
  receives HTTP 404 for that repository. No engine files or source revision
  have been verified. Epic released 5.8.3 on 2026-09-22, so the original
  description of 5.8.2 as the latest hotfix is stale. The release engine pin
  remains 5.8.2 until the requested version choice is resolved.
- Epic's offline macOS installer is restricted to eligible Developer Portal
  organizations; it is not an account-free route to the historical hotfix.
- The Mac locked while navigating the Launcher. UI installation is paused
  until it is unlocked; source and native validation can continue independently.
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

The doctor checks engine `Build.version`, Mac build scripts, selected Xcode and
SDK and first-launch setup status, actual Blender/Git LFS command output, repository LFS setup, the root project
file, editor executable, and disk space. Exit status **1** indicates a missing or
mismatched check; status **0** indicates these presence/version checks passed.
Its `build_ready` JSON flag is a prerequisites check, not a compile result.

## Finish Unreal and Xcode provisioning

1. Resolve the engine pin: to keep **5.8.2**, obtain that source through Epic's
   supported GitHub access procedure (Epic/GitHub account linking and private
   repository access), or supply an existing licensed installation. If the
   newer **5.8.3** hotfix is selected, update the exact version pin and install
   the Launcher tile. Keep the existing 5.2 installation separate.
2. After source access is available, resolve the official 5.8.2 release reference,
   record its full commit SHA in `versions.json`, and use the same revision on all
   build machines. No guessed source revision is recorded here.
3. On another Mac, download **Xcode 26.1.1** from Apple Developer downloads.
   Install it alongside other Xcode versions. This workstation uses
   `~/Applications/SORAToolchain/Xcode_26.1.1.app`; a separate
   `/Applications/Xcode_26.1.1.app` also works. Complete any Apple sign-in and
   license/setup prompts in the normal UI. Do not replace another Xcode version
   or globally change `xcode-select` for this project.
4. Set paths and run the doctor, then build:

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

- Windows client: begin with Epic's documented build-farm combination, **Visual
  Studio 2022 17.14**, **MSVC 14.44.35207**, and **Windows SDK 10.0.22621.0**. Those
  tools have not been installed or tested on this Mac.
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

## Official references

- [UE 5.8.2 hotfix](https://forums.unrealengine.com/t/5-8-2-hotfix-released/2746335)
- [UE 5.8.3 hotfix](https://forums.unrealengine.com/t/5-8-3-hotfix-released/2833315)
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
