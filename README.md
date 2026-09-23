# SORA Arena: Nyaagyu Rebellion

First-release development of a Japanese samurai-cat FPS for Unreal Engine 5.8.2,
with an offline campaign and planned P2P multiplayer settled through native Iroha
execution proofs. Japanese is the primary language for dialogue and interfaces;
English subtitles are enabled by default.

**Current state: foundation prototype, not a finished or qualified game.** The
Rust reference kernel, payout rules, signed input evidence, bounded prediction
and rollback, durable evidence recovery, and Unreal C ABI run locally. Unreal game code, original prototype
models, campaign data and a native Connect subsystem are present. The Unreal
project still requires an actual 5.8.2 build and playtest. Full FPS proofs, live
networking, complete campaign content and photoreal assets remain in development.
Real-value bonding and trading are disabled.
The current native hit-proof layout exceeds Iroha's 4 MiB proof cap before a
kill proof can be generated; [the feasibility record](docs/proof/arena-feasibility.md)
tracks the failed layout and the required staged-proof work.

## Run the deterministic reference

```sh
cargo test --workspace
cargo clippy --workspace --all-targets -- -D warnings
cargo run --release -p arena-cli -- simulate 36000 12
cargo run --release -p arena-cli -- qualification
cargo build --release -p arena-ffi
python3 scripts/unreal/stage_kernel.py
```

The simulation command uses synthetic controls. Its timing is not a rendering or
cryptographic proving benchmark. A state hash or gameplay-key signature is not an
execution proof, and the native ABI reports proof qualification as false.

## Unreal and native integration

Use the project-specific setup and build commands in [toolchain.md](docs/toolchain.md).
Do not substitute the existing UE 5.2 installation for the pinned 5.8.2 engine.
The exact engine revision is recorded after the installation is verified.

- `crates/arena-core`: integer combat, bond allocation, evidence, rollback and recovery.
- `crates/arena-ffi`: versioned native ABI for Unreal presentation.
- `Source/SoraArena`: Unreal offline gameplay, HUD, kernel and wallet subsystems.
- `Content/Data`: Japanese campaign, class, weapon and arena data with English text.
- `scripts/art` and `scripts/unreal`: original asset generation, import and staging.
- [Iroha integration](docs/iroha-integration.md): native changes in the isolated
  sibling `iroha-arena` worktree and outstanding proof/custody gates.
- [Implementation status](docs/implementation-status.md): milestones and release gates.

No backward-compatible formats, aliases or legacy implementations are permitted
for this first release. Development uses an explicitly configured isolated Nexus
network and test XOR. Wallet keys remain in the wallet, and gameplay keys cannot
authorize deposits or purchases. Paid software, assets and services are excluded.
