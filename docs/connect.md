# Native Iroha Connect integration

`UArenaWalletSubsystem` owns asynchronous pairing and encrypted transaction-signing
requests. It loads the small `connect_norito_bridge` C ABI dynamically; the full
Swift, JavaScript, or wallet SDK is not linked into Unreal. Native cryptographic
verification is mandatory. Missing symbols, a different ABI version, invalid
session bindings, and invalid signatures stop the operation with Japanese UI
status text. Offline play does not require this library.

## Implemented boundary

1. Read a configured public Torii origin and canonical network identity. HTTPS is
   required except for explicit loopback development origins. Network identities
   are checked as canonical `hash:<64 uppercase hexadecimal digits>#<CRC16>`
   literals, including their hash marker and checksum; a network display name is
   insufficient.
2. Generate ephemeral X25519 keys through the native bridge's OS randomness,
   derive a nonce from independent native random key material, and derive the
   session ID from the exact network/key/nonce binding.
3. POST `/v1/connect/session`; validate strict JSON, all ten response fields,
   canonical token encodings, and every field in both app and wallet launch
   links. The Torii response cannot replace the requested session or node.
4. Open `/v1/connect/ws?sid=...&role=app` with the app token in an Authorization
   header. Send the native `Open` frame. `LaunchWallet()` opens the verified
   `iroha://connect` deep link only when explicitly requested by the UI.
5. Accept exactly one matching wallet approval. Verify the account and exact
   requested permissions, then verify the Ed25519 approval signature through the
   native bridge. The signature binds the network, session, app key, nonce,
   wallet key, account, permissions, absent proof, and relay token. Derive the
   direction keys only after this verification.
6. Inspect a canonical detached transaction scaffold through the native bridge,
   require the approved account and configured network, and permit a single
   allowlisted native game/NFT instruction. Send the inspector's canonical
   **payload bytes** in an encrypted `SignRequestTx`, keeping the scaffold for
   finalization. Permit one pending signature request at a time.
7. Decrypt and check the wallet response, its exact sequence, and its Ed25519
   signature. The native finalizer verifies that the supplied signatory is bound
   to the authority and that the signature covers the original canonical payload.
   Emit the resulting signed transaction bytes only after that verification.

The subsystem never fabricates approvals, bond balances, kills, payouts,
transaction inclusion, or chain finality. Signing does not broadcast a
transaction; a separate explicit loopback-only test submission is described
below. An authenticated chain-state/receipt path must verify inclusion, the
relevant funded game session, and finality before enabling value-bearing
multiplayer. The `Signed` state means signature verified, not transaction
submitted or settled.

Supported native instructions are `OpenGameSessionV1`, `JoinGameSessionV1`,
`ClaimGamePayoutV1`, `OfferNftV1`, `BuyNftV1`, and
`CancelNftOfferV1`. Arbitrary batches and unrelated transfers are rejected by
this UI integration. Complete native fee terms and instruction fields are still
required. Arena equipment NFTs are returnable: `StakeGameItemV1` is explicitly
rejected by the Arena wallet allowlist, even if a general-purpose bridge supports
that instruction. Death does not transfer an equipment NFT. No transaction is
sent just by pairing.
Every allowlisted game/NFT signing request now requires an explicitly enabled
isolated loopback test Torii whose origin and canonical network ID exactly match
the approved wallet session. Shipping builds cannot satisfy that gate, including
for `OpenGameSessionV1`, listing, cancellation and payout claims. A signed
transaction can be submitted outside the game, so the submission-only gate was
insufficient to keep real-value operations disabled during research. Pairing
itself does not authorize a signature. A loopback URL and a locally configured
network ID do not attest that the node is an isolated chain or that its assets
are test-value; deployment identity and asset qualification remain separate
release gates.
`JoinGameSessionV1` and `BuyNftV1` are decode-allowlisted but their signing
requests stop before `SignRequestTx`: neither the authenticated game-session
terms nor a verified live NFT offer is available to this UI yet. This applies
to both externally supplied scaffolds and the native transaction builder, even
on the isolated test network.

## Build and configure

Use the matching isolated Iroha source checkout, including the native game/NFT
scaffold changes. ABI number 23 alone does not identify those optional feature
changes. The builder symbol is checked separately.

```sh
scripts/connect/check-abi.py
IROHA_SOURCE_ROOT=../iroha-arena scripts/connect/build-bridge.sh
scripts/connect/verify-bridge.py Binaries/Mac/libconnect_norito_bridge.dylib
scripts/connect/verify-bridge.py Binaries/Mac/libconnect_norito_bridge.dylib --game-fixtures ../iroha-arena/javascript/iroha_js/test/fixtures/game-v1-codec.json
scripts/connect/verify-bridge.py Binaries/Mac/libconnect_norito_bridge.dylib --game-fixtures ../iroha-arena/javascript/iroha_js/test/fixtures/game-v1-codec.json --require-arena-join-inspector
```

If macOS Command Line Tools cannot find C++ standard headers, scope
`DEVELOPER_DIR` to a working Xcode installation for `check-abi.py`. The current
26 function-pointer declarations passed this isolated check with the installed
Xcode 26.1.1 compiler (and separately Xcode 27); this does not compile the Unreal
subsystem or establish engine compatibility.

The build script uses the source checkout's `target/` directory by default to
reuse dependencies; `SORA_CONNECT_TARGET_DIR` selects another build directory.
It builds the actual native library, executes native admission/crypto smoke
checks, and only then stages the library and a source/header/library hash record.
It does not write a placeholder library. The generic script's hash record
identifies tracked changes but does not attest untracked source content. The
current local research build also records a stable pre/post-build fingerprint
of untracked files in [`connect-bridge-local-build.json`](connect-bridge-local-build.json).

The default staged locations are:

| Platform | Library |
| --- | --- |
| macOS | `Binaries/Mac/libconnect_norito_bridge.dylib` |
| Windows | `Binaries/Win64/connect_norito_bridge.dll` |
| Linux | `Binaries/Linux/libconnect_norito_bridge.so` |

On Windows, build the same crate with Cargo/MSVC and run `verify-bridge.py` on the
result before copying it to `Binaries/Win64`. The function declarations use C
`unsigned long` for lengths, which is 32 bits on Windows and 64 bits on macOS.
The ABI checker should be run with that platform's compiler as well. Native
packaging code signs the actual library as part of the platform release process;
that release signing has not been performed here.

On the available Apple Silicon Mac, `python3 scripts/connect/check_windows_bridge_crossbuild.py`
attempts a pinned Rust/MinGW GNU cross-build. It stages a DLL only after checking
that Iroha sources stayed stable during compilation, the file is an x86-64 PE,
its Connect exports match the C header exactly, and the 26 Unreal function
pointer declarations compile against that header with the Windows C++ compiler.
This static check cannot load the DLL or replace the Windows MSVC, Unreal, and
wallet runtime passes.

For local development, `SORA_CONNECT_BRIDGE` can select an explicit native
library path. Keep this environment override under the developer's control.
`SoraArena.Build.cs` stages the default library only if it exists. A package can
therefore launch offline without the bridge, while wallet actions fail closed.

Copy the public configuration keys in
[`scripts/connect/Game.local.ini.example`](../scripts/connect/Game.local.ini.example)
into the local platform `Game.ini`, such as `Saved/Config/MacEditor/Game.ini`.
Use the actual deployed network identity; the example does not contain a network
or preapproved account. `ExpectedAccount` optionally pins the account selected
for pairing. Connect session tokens and private keys do not belong in config.

## UI API

The game-instance subsystem exposes `BeginPairingFromConfig`, `LaunchWallet`, and
`DisconnectWallet`, along with `State`, Japanese `StatusText`, `ApprovedAccount`,
and the `OnStateChanged` event. Pairing controls can stay visible while the bridge
is unavailable so that the reason appears in the UI.

`WalletLaunchUri` is a credential-bearing, validated URI. A native local encoder
turns it into `WalletQrTexture`, a transient black/white texture with medium or
better error correction, nearest filtering, and a four-module quiet zone. The
HUD shows the complete texture at an integer scale only while approval is
pending. It uses the verified URI for the deep-link launch action as well. No
external QR service is called. Do not print the URI, put it in analytics,
persist it, or replicate it to game peers. Both URI and QR are cleared after
approval or disconnect; the QR pixel buffer is overwritten before releasing it.
Private session keys are explicitly zeroed when no longer needed. Exceptionally
long URIs that exceed 2,048 UTF-8 bytes use the deep-link action without a QR.

The small C encoder is [Project Nayuki's QR Code generator](https://www.nayuki.io/page/qr-code-generator-library),
vendored unchanged from revision `3c6d0b3cefb4e049dc337e82237c9644399716a8`.
Its MIT notice is preserved in both source files and staged in
`ThirdPartyNotices/QRCodeGen.txt`. File hashes and immutable upstream URLs are
recorded in `Source/SoraArena/Private/ThirdParty/QrCodeGen/upstream.json`. The C
implementation requires no C++ exceptions or additional runtime package.

`RequestSignTransaction(scaffoldBase64, ed25519PublicKeyHex)` accepts a canonical
native scaffold and the account signatory public key, not a secret key.
`RequestNativeTransactionSignature(exactRequestJson, ed25519PublicKeyHex)` first
uses the optional native builder. Its JSON requires exactly `network_id`,
`authority`, `creation_time_ms`, positive `time_to_live_ms`, complete
`fee_payment`, and `instruction: {name, value}`. The typed native parser rejects
omitted or unknown nested fields. Neither method should be called implicitly
from entering a menu; present the concrete transaction and require the player's
action, then the wallet's approval.

`PendingTransactionSummary` preserves the native inspector's exact JSON string,
including integer quantities, rather than reserializing quantities through
Unreal's floating-point JSON representation. The bridge finalization returns
the signed transaction and entrypoint hashes alongside the verified bytes.
`OnTransactionSigned` exposes those bytes to the local caller; it does not
submit them.

### Exact game-facing review gap

The native inspector returns structured `executable: {kind, name, value}` and
`fee_payment` fields bound to the canonical signing payload. Its
`JoinGameSessionV1.value` includes `session_id`, `expected_manifest_hash`,
`expected_asset_definition`, exact-string `expected_stake`, `resources`, the
input key, and any invitation. The existing native builder smoke check compares
those values and fee intent byte-for-byte after re-inspection. This is useful
transaction evidence, but it is not a complete game admission quote.

The Unreal subsystem checks the inspected authority, network, and allowlisted
instruction name. Open and payout-claim scaffolds retain the isolated-test
signing path; Join and Buy are rejected before any wallet signing request. It
does not render a qualified term sheet or require a separate in-game
confirmation. It also has no certified
session/manifest read to establish the base bond, per-death loss, maximum loss,
equipment reservation, or whether the declared asset is the configured XOR
asset. `fee_payment` is an exact fee intent, not proof of a final network fee.
For a purchase, the UI likewise lacks a verified live offer read tying seller,
NFT identity, price, expiry, and ownership to the inspected `BuyNftV1` payload;
the current builder smoke check does not exercise a Buy fixture.

Before exposing join or purchase approval in the game, add a versioned native
review result that binds those typed terms and the canonical payload hash to a
verified session or offer snapshot. Preserve atomic quantities as strings and
display the exact asset identity, fees, loss rules, and NFT reservations in
Japanese with English explanation. Require a separate player confirmation of
that result before `SignRequestTx`, then keep the wallet approval and finality
checks independent. Until that path is implemented and tested, raw inspection
JSON and the menu's transaction-state text must not be presented as an exact
bond or purchase review.

The matching bridge source now has a bounded,
`sora.arena.join_terms_inspection.v1` result for **canonical scaffold only**.
It re-decodes a single typed Join and binds its complete fields and fee intent
to the payload signing hash and placeholder-scaffold BLAKE3 digest. Its
`authorization_ready` field is always `false`. The placeholder scaffold digest
is not the final signed transaction hash; this endpoint has no authenticated
session read, manifest economics, fee quote, or asset/NFT state and does not
lift the Unreal signing block.
This research FFI symbol is optional for pairing under bridge ABI 23 and must be
negotiated by its exact name, `connect_norito_arena_join_terms_inspect_v1`.
Its absence leaves Join/Buy signing blocked; its presence also leaves signing
blocked until an authenticated session review exists. `check-abi.py` checks its
C declaration and Unreal function-pointer type. With `--game-fixtures`,
`verify-bridge.py` exercises typed Join terms and rejects malformed or non-Join
scaffolds if the symbol is present. Use `--require-arena-join-inspector` to fail
verification when the symbol is missing.
`UArenaWalletSubsystem::InspectJoinScaffold` exposes those canonical typed
terms as read-only JSON for a paired, matching account and network. It checks
the inspector's payload hash against the general native scaffold inspection
and requires `authorization_ready=false`. A successful bounded inspection now
also populates a Japanese-primary, English-secondary menu preview. The preview
labels the requested `expected_stake` and asset identity, requested NFT
reservation IDs, exact metadata and role hashes, return policy, fee payer, and
exact-string fee charge caps as **unverified**.
It is explicitly a **partial** preview: the Join session and manifest hashes,
input key, application data, invitation, transaction time bounds, and the
fee intent's gas limit and sponsor-program details are still only in the raw
inspection result returned to the caller. The UI does not imply those fields
were reviewed. It shows death loss and maximum loss as unavailable, since the native response
has neither rule or an authenticated base bond. The fee caps are intent, not a
final network fee quote. Requested NFT reservations are not verified ownership
or active equipment custody. The preview supports at most one NFT reservation
and two fee charge caps, with field-length bounds matching the canvas; an
inspection exceeding those limits fails rather than hiding a term. No menu
action creates a Join scaffold yet, so the preview appears only after an
explicit caller invokes the read-only inspector. It never requests a wallet
signature or changes the Join/Buy signing block. An authenticated session
quote, exact loss rules, asset/ownership reads, and an Unreal visual/build run
remain prerequisites for a real join review.

`SubmitSignedTestTransaction()` is a separate, explicit operation. It is
disabled in shipping builds and unless `Arena.Connect` explicitly sets
`bEnableIsolatedTestTransactions=true`, `IsolatedTestNetworkId`, and
`IsolatedTestToriiOrigin` to the paired network and a loopback HTTP Torii.
The default configuration contains no such opt-in. The request sends the
versioned signed transaction to `POST /v1/pipeline/transactions` with
`application/x-norito` and `Prefer: return=minimal`. Only HTTP 202 with the
exact signed and entrypoint identity headers and empty minimal response is
treated as accepted for tracking; it is never treated as finality. Every
other or missing response is uncertain. The signed payload is discarded after
the single submission attempt and never automatically resent.

`ReconcileTransaction()` reads the retained identity from
`GET /v1/pipeline/transactions/status?hash=<exact>&scope=global`. Only
`Applied` resolved from `state` becomes `Finalized`; only state-resolved
`Rejected` or `Expired` becomes `Rejected`. A typed global 404 means the
transaction has not yet been observed, not that a new submission is safe.
Polling is bounded to 90 attempts at two-second intervals, and can be
resumed by identity. Cancelling before signature discards any late wallet
signature. Cancelling after submission stops local monitoring but retains the
hash, since cancelling HTTP cannot reverse a chain transaction.

Before the first POST, the subsystem flushes and moves a versioned, bounded
identity record into the project's `Saved/ArenaConnect/Recovery` directory.
Its only fields are the exact loopback Torii origin, canonical network ID,
signed transaction hash, and entrypoint hash. It never writes signed bytes,
wallet keys, Connect session tokens, or the pairing URI. A normal process
restart restores one valid record as **Uncertain**, with no signed payload and
no automatic submission. The user may call `ReconcileTransaction()` to issue
only the exact-hash GET. Every query and response requires the same explicitly
enabled loopback test-network configuration and the same intact identity file.
Malformed, mismatched, or multiple pending records stop submission and status
queries rather than guessing an identity. A record is deleted only after an
exact state-resolved terminal observation; failure to remove it blocks a new
submission. A crash before the POST may leave an uncertain record for a
transaction that was never sent; even a scoped 404 does not authorize a retry.
Staging files from a crash before the final record move are ignored because the
HTTP request has not yet been started. This first subsystem still tracks only
one outstanding identity per game process, so multiple pending files require
manual investigation. Recovery is for a process restart; machine power-loss
durability and multi-process behavior have not been qualified. A public Torii
status observation never by itself unlocks a bond or weapon entitlement.

## Verification and current limits

- `check-abi.py` compiles the dynamic function pointer declarations against the
  actual bridge header without loading Unreal. This is a C type check only.
- `python3 scripts/connect/verify-recovery.py` compiles the exact C++17 record
  codec used by the Unreal subsystem without the engine, runs 23 positive
  and negative format/binding checks, and statically checks that persistence
  and signed-byte erasure precede the POST. It passed on macOS with project-local
  Xcode 26.1.1. This does not validate Unreal's file I/O, a crash/restart in a
  packaged build, or live Torii reconciliation.
- `verify-bridge.py` loads a real library and checks ABI/symbols, OS-random key
  generation, network/key/nonce-bound session IDs, invalid-width rejection,
  matching peer direction keys, authenticated envelope round trips, wrong-key
  and tampered/trailing ciphertext rejection, and
  strict JSON rejection of duplicate keys, trailing junk, and invalid UTF-8.
  With `--game-fixtures`, it also builds and reinspects canonical Open/Join/Claim
  transactions, compares exact authority/network/fees/instruction values, rejects
  21 malformed requests, and rejects unsigned placeholder finalization.
  On 2026-09-23 these native checks **passed** on the staged release-profile
  local research library at `Binaries/Mac/libconnect_norito_bridge.dylib`,
  SHA-256 `f44b6d37d596200c9a3897d17eb9b6f7a919ffcf84e61ef8e3bc126f854fb152`.
  The required Arena Join inspector also matched exact typed fixture terms,
  reported `authorization_ready: false`, and rejected malformed and non-Join
  scaffolds. The ignored sidecar and tracked build manifest record the compiler,
  source snapshot, and library hash. The Iroha checkout still had uncommitted
  source, so this is not a reproducible source archive, product-release signature,
  or live wallet test.
- `SoraArena.Connect.LaunchBindings` contains Unreal automation cases for network
  checksum and origin validation, node/session/role substitution, duplicate URI
  fields, extra fields, fragments, substituted URI schemes, rejection of NFT
  wagering/unrelated transfers, and exact transaction status interpretation.
  These require an
  installed matching engine and have not yet run.
- `scripts/connect/verify-qr.py` checks the vendored encoder's source hashes,
  compiles it as C99 with warnings treated as errors, encodes synthetic local
  launch links, and uses the independent macOS Vision QR decoder to compare the
  recovered payloads byte for byte. It writes only temporary synthetic images
  and removes them afterward. This does not test the Unreal renderer or a live
  wallet scan. On 2026-09-22, all three synthetic fixtures decoded exactly, and
  strict C99 compilation passed with Xcode 26.1.1. The same encoder also passed
  C++17 syntax checking with exceptions disabled.
- HTTP session responses are limited to 32 KiB, frames to 1 MiB, and queued
  WebSocket ingress to 2 MiB/256 fragments. State mutations are dispatched to the
  game thread; generation checks discard callbacks from previous sessions.
  Pairing and signature requests time out. Peer sequences must be contiguous;
  server-event sequences do not establish wallet approval or chain finality.
- Native heartbeat pings are answered without changing wallet approval state.
  Unsupported unsolicited controls fail closed. Reconnection/resumption,
  offline signing queues, multiple simultaneous wallets, non-Ed25519 signing,
  and account proof extensions are outside this initial integration.
- As of this implementation, UE 5.8 compilation, live Torii/wallet pairing,
  wallet transaction approval, test-chain submission/finality, and multi-node
  independent finality are **not yet verified**. Their absence must remain
  visible in product and build claims.

Wire behavior was derived from the local Iroha bridge header/implementation,
`IrohaSwift` Connect session and Torii binding validators, and Torii's Connect
session and relay handlers. Use the matching revision of those components for
interoperability validation; do not substitute a guessed REST or wire format.
