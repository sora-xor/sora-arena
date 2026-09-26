# Local P2P evidence recovery

`arena_core::recovery::DurableSession` wraps the rollback session in an append-only
first-release version-3 journal. This is local evidence storage, not the Iroha
transaction format, an execution proof or a signed payout. It gives no local
authority to resolve a missing reveal: only a native consensus deadline can,
as described in [pipelined evidence and dropout](p2p-pipeline.md). There are
no legacy decoders.

The caller supplies an independently authenticated admission: network, session,
manifest, permanent ordered gameplay keys, match configuration, exact deposits
and equipment. The header binds those terms, the reference rules version and the
initial deterministic state. Restore compares them byte-for-byte rather than
trusting self-declared terms in a recovered file. The chain adapter that supplies
this authenticated admission is still required.

The journal records these operations:

- commitment certificates;
- individual or grouped reveals;
- consensus deadline resolutions;
- this peer's sealed openings and set endorsements;
- signed checkpoints and signed handshake offers;
- interruption and local finish.

Every record is length bounded, sequenced and hash chained. Certificates and
checkpoints are checked with every original Ed25519 key.

Every player commits exactly `BATCH_TICKS = 2` canonical controls per batch.
This is a fixed protocol contract, including the final batch; shorter batches
are rejected. Up to 16 certified frontiers may be pending at once. A reveal
names its frontier by start tick and must open that frontier's exact certified
input commitment. A frontier advances the confirmed simulation only once every
slot has opened it or a consensus deadline has closed it, and frontiers
execute strictly in tick order. Individual reveals stay durable during
withholding, whichever frontier they open. Retrying an opening the evidence
already retains is idempotent, even after its frontier has closed.

Already-received reveals for any pending frontiers may be grouped into one
durable record and one sync, at most 64 per record. The caller must not wait
for a withholding peer to fill a group. An invalid group is rejected
atomically, so its valid members must be resubmitted individually or in a
valid group. Predicted state is never stored as confirmed evidence and is
discarded on interruption.

A peer journals its own opening (`seal`) before its commitment leaves the
process, and its endorsed set digest (`endorse`) before its signature does.
After a restart it can open every frontier it committed to, and it cannot seal
a second opening or endorse a second set for any tick. Both are refused once
combat has stopped. A consensus `DeadlineResolution` is journaled exactly as
supplied. The chain adapter must authenticate it first, because arena-core
cannot check its attestation.

Suppose every received opening authenticates, but the reference simulation
cannot execute a ready frontier. The openings remain durable, and
`resolution_fault()` exposes the execution error. The session enters
resolution, and its confirmed combat state does not advance past that
frontier. Local finish remains blocked by the unresolved certified frontier. A
native dispute verifier must decide that outcome.

The writer validates a candidate state before writing, appends its record, calls
`sync_all`, and only then acknowledges the operation and adopts that state. An
uncertain write poisons the open handle so it cannot blindly retry. Creation uses
`create_new` and an exclusive advisory file lock; opening a second writer fails.
Unix creation also syncs the parent directory. Torn, oversized, reordered,
altered, unknown or trailing record bytes fail recovery without truncating or
rewriting the original evidence. Recovering damaged storage from authenticated
peer/ledger copies remains an integration task.

**Group commit.** `DurableSession::group_commit` switches a session so that
each operation is still validated and applied at once, but its framed record
is only buffered. `take_staged` hands every buffered record to the returned
`GroupWriter`, which appends them with one write and one `sync_all`, and
`mark_durable` then advances `durable_receipt`. The file format, record chain
and receipts are unchanged. Only one hand-off is in flight at a time, and a
failed group write poisons the handle. Nothing that depends on a record may
leave the process before it is durable: compare `receipt()` with
`durable_receipt()`. A process crash loses at most the buffered records,
which nothing outside the process has relied on, so restore from the last
synced receipt reaches a state every peer can continue from. A group write
torn by power loss still fails restore closed, like any torn record. The
[mesh transport](p2p-localhost.md#n-peer-mesh-transport) runs the writer on its
own thread and hands off at most once per batch interval (33.3 ms at 60 Hz).

`recovery::inspect_prefix` provides a separate read-only dispute inspection path.
It opens the file read-only, acquires a shared advisory lock, bounds reads to the
same file limit, checks the caller's exact admission, and replays the same
canonical record decoder and certificate checks as full restore. A cooperative
active writer prevents inspection. The result contains:

- the last fully verified receipt;
- the exclusive prefix byte end and the observed file size;
- the confirmed session, with its pending frontiers and their openings;
- sealed openings and endorsements;
- accepted handshake offer digests;
- any resolution fault.

It retains no file handle and exposes no writer or repair operation.

An externally retained minimum receipt must occur inside that verified prefix;
otherwise inspection returns an error without exposing an authenticated prefix.
If corruption follows the minimum, `failure()` identifies the failing record's
absolute zero-based start and verification location. A truncated field reports
the exact first missing byte and expected field end. A bad sequence or size
reports that field's start; a hash mismatch reports the digest field; a decode
or semantic failure reports the payload start. Cryptography cannot determine
which original byte was changed from a digest mismatch, so the latter locations
are verification boundaries, not claims to identify a tampered byte. Inspection
does not skip a bad record, silently truncate, or permit writer continuation.
A prefix with no partial final record cannot detect a missing whole suffix
beyond the caller's minimum receipt.

Each successful call yields a receipt with the record count and chain digest.
Restore requires a previously trusted receipt and rejects a file that no longer
contains it. A receipt retained only inside the same file cannot detect removal
of a whole suffix. The transport/chain integration must retain the receipt
independently before relying on a frontier; this is explicit in the API. The
journal contains controls, salts, public signatures and signed ephemeral public
offers, never wallet, gameplay or ephemeral private keys. It is not encrypted at rest.

A match may end during the first tick of a certified two-tick batch. The complete
input batch stays in the transcript, but controls after the first terminal
transition have no gameplay effect. The combat clock records the actual terminal
tick and the evidence clock records the end of the revealed batch. No new batch
is accepted after the combat state becomes terminal.

The current file limit is 64 MiB and the individual record limit is 4 KiB.
The largest 12-player two-tick batch occupies 3,470 bytes:

| Record | Bytes |
| --- | --- |
| Certificate | 1,249 |
| Twelve separate reveals | 12 × 96 |
| Full checkpoint | 897 |
| This peer's seal | 95 |
| This peer's endorsement | 77 |

With a single grouped reveal record, the twelve reveals take 690 bytes. A
signed offer record is 158 bytes, and the full 1,024-offer allowance for all
twelve responder slots adds at most 1,941,504 bytes. A unit test asserts that
the following fit the file bound together: 18,000 worst-case batches,
admission, that offer allowance, sixteen deadline records, an interruption
and a finish. Immutable history uses shared 64-batch chunks, so transactional
candidates do not copy all prior controls and signatures for every append.
The full-clock journal and handshake capacity are not a measured simultaneous
workload.

One measured local diagnostic on the version-3 journal completed 36,000 ticks
with 12 players, using idle controls, grouped reveals and shared history. It ran
on 2026-09-25 as `target/release/examples/recovery_research <new path> 36000 12`
on the Apple M1 Ultra, macOS 27.0, with Rust 1.97.1:

- 36,002 records and 34,903,658 bytes;
- 272,388 ms append time and 38,646 ms restore time;
- a maximum resident set size of 91,471,872 bytes (`/usr/bin/time -l`).

The byte count is exactly 864,000 more than the earlier version-2 run: each
of the 216,000 openings now carries its 4-byte start tick. Restored and
original terminal state hashes matched. The diagnostic seals and endorses
nothing and checkpoints only once. This measures this machine's local idle-input journal
I/O/replay only. It does not qualify combat, network latency, concurrent clients,
STARK proving, or power-loss safety. Windows filesystem durability remains
unqualified. Native dispute resolution, complete network transport and financial
settlement remain gated.

Focused tests exercise restarts with missing reveals, terminal completion without
another final signature, exact admission rejection, duplicate writers, corrupted
and torn records, receipt rollback, and a forged signature whose surrounding
record digest was recomputed. Further tests cover restarts with pipelined
frontiers, out-of-order openings, sealed openings and endorsements, refused
re-endorsement and resealing, and consensus deadlines journaled and replayed
exactly. They also check that a stopped match seals and endorses nothing new. Five additional prefix tests check every cut point
of a final reveal record, preserved pending openings, exact diagnostic offsets,
atomic semantic rejection, external-receipt enforcement, file/record bounds,
admission mismatch and active-writer exclusion. The original bytes are compared
after inspection. These tests do not constitute a native FPS proof.

## Encrypted evidence datagrams

`arena_core::encrypted_wire` wraps a signed `WireFrame` in a versioned,
length-bounded ChaCha20-Poly1305 datagram. It does not change the canonical
inner wire bytes or their Ed25519 checks. Each instance is one pairwise,
unidirectional sender-to-receiver channel. The
`arena_core::handshake` module can establish its key and 32-byte channel
binding after both peers have the same authenticated admission `Context`.
The initiator signs a fixed-length X25519 offer with its admitted Ed25519
gameplay key. The responder verifies it, signs a fixed-length response
including the exact offer digest, and both sides derive separate directional
keys and a channel binding with HKDF-SHA256 over the shared secret and full
signed transcript. The transcript includes the network, session, manifest,
ordered roster and initiator/responder slots. Non-contributory public keys,
malformed lengths, invalid signatures and changed contexts are rejected.
X25519 secrets and channel key buffers use zeroizing types. A key is fresh for this
sender, receiver, channel and direction; it is never shared across directions
or sessions. Associated data binds the protocol version, sender, sequence,
96-bit OS-random nonce, exact ciphertext
length, channel binding and independently authenticated admission context.

The sender refuses a sequence at or below its current floor. The receiver
rejects a replay or reordered sequence, then checks the AEAD tag, the signed
inner frame and exact agreement between the outer and inner sender/sequence.
Failed packets do not advance its floor. The receiver's accepted sequence floor
and the sender's emitted sequence floor must be retained outside the datagram
channel and restored after restart. A fresh key can begin with no floor; callers
must not treat constructing a new channel with an old key and an empty floor as
a new session. The 96-bit nonce is generated independently for each packet by
the operating-system random source, including after restart. The probability
of collision is negligible at match packet counts, but the transport still
needs lifecycle limits and rekeying policy before production qualification.

`EncryptedSender::seal_fragments` divides a sealed packet into canonical
datagrams of at most 1,200 bytes; the largest twelve-player certificate takes
two. Each fragment is independently authenticated with HMAC-SHA256 under a
domain-separated derivative of the pairwise channel key. A receiver accepts
out-of-order fragments, retains at most four incomplete packets per peer,
evicts the oldest incomplete sequence for a newer one, rejects conflicting or
malformed fragments, and checks the complete packet's
SHA-256 digest before the ordinary AEAD and Ed25519 checks. Duplicate fragments
do not advance the replay floor. A receiver must call `open_fragment` on the
same channel instance and persist its accepted sequence floor as above. This
framing by itself does not supply retransmission, congestion control, NAT
traversal, peer discovery or a network transport. The separate test-only
localhost transport adds bounded authenticated ACK/retry for already sealed
fragments; see [its current limits](p2p-localhost.md).

The responder's `OfferReplayGuard` rejects an already accepted signed
offer, including when it could generate a fresh local ephemeral secret. Its
accepted offer digests must be persisted with the match evidence before the
caller sends the returned response or uses the keys, then restored across
reconnects. `DurableSession::accept_handshake_offer` verifies the admitted
signature, syncs the exact public offer to the journal, and only then returns
the response and channel keys. Restore and read-only prefix inspection verify
the signature again and reconstruct the responder's replay set. The caller
must retain the returned journal receipt independently before sending the
response; a missing whole suffix cannot be detected from the journal alone.
The guard retains at most 1,024 accepted offers per responder per match and
rejects further offers when full; recovery must preserve the current channel
or end the match under the certified disconnect rules. A finished journal
still accepts fresh offers under the same guard and bound. A peer that
restarts after this one finished may still need its final checkpoint
signature. The initiator
keeps its one-use secret in memory only; an old response cannot complete a new
local offer. After a restart the initiator generates a new offer. The signed
handshake does not establish that the remote human is honest or that an
admission context was selected correctly; those are separate qualification
requirements.

These primitives implement local key agreement and authenticated datagrams.
The localhost research path implements bounded ACK/retry, but neither path
implements peer discovery, NAT traversal, packet relays, production congestion
control, or a live multi-peer network transport. It is not an execution proof or a substitute for the
certified commitment frontier and durable evidence journal.
