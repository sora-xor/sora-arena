# Reproducible source checks

Run `scripts/qualification/source_checks.py` from a materialized Git checkout.
It executes explicit host checks sequentially, records their exact commands and
logs, and exits nonzero if any check fails or cannot start. It never launches
Unreal, builds Iroha, renders, downloads assets or contacts a chain. Rust checks
compile the game workspace with two build jobs by default into the checkout's
ignored `target/source-checks/` directory.

## Setup and execution

Use Python **3.11**, Git LFS, a C++20 compiler, and the exact Rust toolchain in
`rust-toolchain.toml` with rustfmt and Clippy. Linux CI uses Ubuntu 24.04; the
tooling job uses macOS 15 because the existing fake-import test calls
`xcode-select`. On
macOS, the existing gameplay drivers require the Xcode path recorded in
`scripts/toolchain/versions.json`; `SORA_DEVELOPER_DIR` may select its installed
location. These are host C++ rule tests, not Unreal builds or platform parity.

```sh
git lfs pull
python3.11 -m venv Local/source-checks-venv
Local/source-checks-venv/bin/python -m pip install -r scripts/qualification/source-checks-requirements.txt
Local/source-checks-venv/bin/python scripts/qualification/source_checks.py
```

The runner does not install missing tools or Python packages. Missing tools,
missing packages, absent LFS files and mismatched Rust pins are failures. The
Rust pin check reuses the existing doctor's exact compiler-version/commit
check. The runner removes `PYTHONOPTIMIZE` for children so assertion-based gates
remain active, and sets `RUSTUP_AUTO_INSTALL=0` for all checks.

Select groups for focused local work, or inspect the complete command inventory:

```sh
Local/source-checks-venv/bin/python scripts/qualification/source_checks.py --list
Local/source-checks-venv/bin/python scripts/qualification/source_checks.py --group gameplay --group tooling
Local/source-checks-venv/bin/python scripts/qualification/source_checks.py --group rust --jobs 2
```

| Group | Checked source behavior |
| --- | --- |
| `rust` | Exact compiler pin, workspace formatting, strict Clippy, locked workspace tests |
| `gameplay` | Campaign generation, mutation and maai-contract checks, enemies, localization, input, catalog parity, host C++ campaign/combat/boss/stealth/fieldcraft/arms rules, cancellation/recovery and quote comparison |
| `tooling` | Runner failure handling, engine/Rust pin guards, VFX import/preview and rendered-capture report guards, parity source-identity inventory, environment policy/preset source tests |
| `assets` | Current LFS materialization, authored content and asset hashes, tracked source PNG/JPEG integrity, full existing ledger validator, notices freshness and ledger/acquisition regression tests |
| `audio` | Audio data freshness/routing/localization, import specifications, DSP regressions and measured source WAV quality |

Each run creates a fresh `Saved/SourceChecks/<UTC timestamp>/` with `report.json`
and one log per check. `--output` can choose another **new** directory; an
existing directory is refused without changing its prior evidence. Such a
refused invocation exits nonzero and produces no new report; choose another
directory. Keep outputs under the ignored `Saved/` directory or outside the
checkout so logs do not count as untracked source changes.
The report is updated after each check. An interrupted run retains `running`,
never `passed`. A source change during a run also fails the aggregate result.
The report records Git commit, tracked diff hash, untracked file hashes,
platform, interpreter, installed package versions, selected and omitted groups,
and all commands/results. It does not include a source diff or environment dump.
For release evidence, rerun from a clean committed candidate.

## Scope and failures

There is no expected-failure allowance. The recovered weapon ledger defects
and the new art's missing provenance records must be corrected in their owning
asset work; this runner reports them as failures. It does not regenerate or
bless their hashes. The existing ledger's ordinary policy is retained (legacy
records produce warnings); this is not its stricter schema-migration gate.
The separate LFS gate prevents its pointer warnings from looking like complete
asset-byte verification.

The independent `source-images` check fully decodes every tracked PNG/JPEG
under `Content/SourceArt` with pinned Pillow. PNGs also pass the capture
validator's complete chunk/CRC, IEND, DEFLATE and scanline checks. Missing files,
LFS pointers, truncated images and corrupt pixel streams fail. The check reads
assets without changing bytes or ledger hashes; passing it approves neither
provenance nor visual quality. HDR, SVG and other formats are outside this
focused image gate. The existing `source-content` and `asset-ledger` checks
remain separate.

Six environment-library/preset tests require untracked `Local/ThirdPartyRaw`
files. Their exact test IDs are declared in `RAW_TESTS` in the runner and in
every report. They are outside this source-only suite on **every** machine.
The other tests in those files run, a stale exclusion fails, and any unexpected
unittest skip fails. Run the original two scripts against a fully fetched raw
cache for the complete environment import-plan gate. Similarly,
`scripts/audio/validate_audio.py` requires the private raw-download cache and
is outside this suite; shipped WAVs, data, source records and their hashes are
still checked by the audio and ledger groups.

`cargo test` retains the repository's explicitly ignored long research runs.
The Rust log reports them; no full-duration, live-network or proof claim is
made. Only `SourceIdentityCoverageTests` from the parity guard module is in
this suite; the report records that class selection. The full rejection suite
loads and executes the staged native kernel and must run alongside native
parity qualification. Preview/import guards test script behavior without claiming a
rendered frame or material compilation.

A pass applies only to selected source groups. Every report permanently says
`release_qualified: false` and lists the outstanding classes of evidence:
Unreal/native builds and runtime, actual macOS/Windows parity, packaging and
distribution signing, rendered art and shaders, audio listening, controller
and accessibility playtests, pacing/performance, private raw assets, real P2P
and wallet/validator trials, complete native proofs and economic settlement.

## CI

`.github/workflows/source-checks.yml` runs the five groups independently on
pull requests, pushes to `master`, and manual dispatch. LFS checkout is mandatory
for tooling, asset and audio jobs; Rust and gameplay need only regular Git
source. Pinned Python dependencies are installed for every job. The Rust job installs the repository pin;
the runner then verifies it. Action revisions are pinned to commit IDs. No job
uses `continue-on-error`; one group's failure does not prevent the others
from producing evidence. Logs and partial reports upload even on failure.

CI is a source gate, not a packaged-game or complete-release pipeline. A failed
checkout or dependency installation can occur before a report exists and must
be resolved in the job log, not interpreted as a skipped successful check.
