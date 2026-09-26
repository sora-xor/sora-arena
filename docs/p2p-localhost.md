# Localhost P2P evidence transport research

Two research transports carry signed evidence over real UDP sockets. Neither
is matchmaking, NAT traversal, consensus or settlement, and both refuse any
admission that is not offline with zero bond.

- `arena_core::localhost_transport` connects two peers with stop-and-wait
  delivery (this section).
- `arena_core::mesh_transport` connects every peer of a match, one process
  each. The [N-peer mesh](#n-peer-mesh-transport) below adds selective
  acknowledgement, group-committed journals, restart catch-up, the
  `arena peer` command and a multi-process harness.

## Two-peer transport

`arena_core::localhost_transport` exchanges signed evidence over real UDP sockets bound to loopback addresses. It only accepts an **offline admission** (zero XOR bond) and one exact, pre-admitted peer address. Both peers must already have the same authenticated `Context`, `Config`, ordered participant roster, and separate `DurableSession` journals.

The initiator sends an Ed25519-signed ephemeral X25519 offer. The responder verifies it and syncs the accepted offer into its evidence journal, then syncs a receipt file before sending its signed answer. Each peer derives separate directional AEAD keys. Subsequent `WireFrame` certificates, individual reveals, and checkpoints are signed, encrypted, fragmented into at-most-1,200-byte datagrams, reassembled, authenticated, and journaled before `receive()` returns. Pre-certification commitments and set signatures ([wire v2](p2p-pipeline.md)) travel the same way and are acknowledged, but they are not evidence until a certificate contains them, so the receiver does not journal them. `prepare()` refuses to send one unless `LocalhostPeer::seal` or `LocalhostPeer::endorse` has already journaled this peer's opening or endorsed set digest and persisted the receipt. A reveal is looked up among all of the receiver's certified frontiers by its start tick. `prepare()` journals local evidence and persists its receipt before making a retransmittable datagram set. `transmit_reliably()` uses stop-and-wait: it sends those exact bytes at most four times, each with the admitted timeout (positive and at most five seconds), until it receives a fresh-channel, direction-keyed ACK for that sequence. Re-sealing the same sequence is disallowed.

The receiver sends an ACK only after both the journal append and external receipt sync succeed. It recognizes at most four recent authenticated packet identities and re-ACKs their duplicate fragments without delivering or journaling them twice. An ACK write failure does not suppress a frame that was already made durable; a later retransmission can obtain another ACK. While waiting for an ACK, a peer journals incoming evidence and queues at most eight frames for a later `receive()`. If that queue is full, it still authenticates and re-ACKs a previously persisted packet; a new authenticated fragment returns `InboxFull` before it changes fragment or sequence state, enters the journal, or receives an ACK. The sender can retry its retained exact bytes after the queue drains. Timeout is ambiguous: the remote peer may have accepted the evidence even when all four ACK waits expire. The caller must reconcile retained receipts rather than infer rejection or send a new conflicting packet.

`ReceiptFiles` writes one synced file per journal receipt outside the journal. This is a **test harness artifact**, not an independently trusted rollback anchor: a party able to roll back both files can still hide a complete suffix. Before a real reconnect, an independent peer or ledger must supply the latest trusted receipt to `DurableSession::restore`. The transport never restores an old AEAD channel; it requires a new handshake and fresh keys. A persistence failure closes the transport handle before it sends or returns evidence.

The focused tests exercise a two-peer certificate/reveal exchange through loopback UDP, commitments and set signatures sent only after they are journaled, dropped data and ACKs, exact retransmission, ACK-send failure after persistence, full-queue replay re-ACK without duplicate delivery, full-queue new-evidence rejection without an ACK or state change, out-of-order and duplicate fragments for a twelve-participant certificate, bounded retry exhaustion, and journal restore with fresh keys that reject stale ACKs and ciphertext. This slice has no NAT traversal, peer discovery, deadline consensus, execution proof, or ledger settlement. Real-value admission remains disabled until the full proof and validator qualification gates pass.

A further offline diagnostic now drives two Arc-carbine peers through eight
certified two-tick batches over this encrypted UDP path. After each accepted
batch, both durable journals agree on the next tick, history root and combat
state hash, and match an independently stepped `World` fixture. A corrupted
reveal fragment cannot advance the receipt or combat state; exact retry works,
and replay of an already accepted reveal does not execute twice. This covers
16 local combat ticks with zero bond, not internet transport, adversarial
consensus or a cryptographic execution proof.

## N-peer mesh transport

`arena_core::mesh_transport::MeshPeer` is one peer of an offline match. It
owns one UDP socket, one version-3 journal and one receipt log, and runs a
channel to every other roster slot.

### Admission and addresses

`MeshAdmission` supplies the socket, every slot's admitted address (this
peer's own included), the slot, its Ed25519 key, the journal and the receipt
log. Admission is refused unless:

- the key owns the slot and the socket is bound to exactly that slot's
  address;
- every address is distinct and admitted by the scope;
- the match is offline with zero bond: `Config::offline`, a zero base bond
  and zero deposits for every account;
- the journal has not finished. A new match needs an empty journal and its
  receipt log; a restored one is continued with `MeshPeer::resume`.

`NetworkScope::Loopback` admits loopback addresses only. Non-loopback
addresses need `NetworkScope::ResearchLan` (the `--research-lan` flag), which
admits private, link-local and loopback addresses and still refuses public,
unspecified and multicast ones. Research LAN does not relax the zero-bond
rule.

### Channels

Lower slots offer keys to higher ones with the signed X25519 handshake. A
restored peer offers to everyone. The responder journals the accepted offer
and sends its signed answer only once that record is durable. It holds its
data frames until the answer has gone out, and it answers a retransmitted
offer with the same bytes. When offers cross, the lower slot's offer wins. An
offer that stays unanswered for 20 sends is replaced by a fresh one, in case
the responder accepted it before a crash and now refuses it as a replay. A
fresh, valid offer from a slot that already has a channel means that peer
restarted: the channel is replaced. A peer that has finished still answers
such an offer, so a peer that restarts near the end can collect its final
checkpoint signature.

Each channel is a sliding window with selective acknowledgement:

- at most `SEND_WINDOW = 32` sealed frames are in flight, and each queue holds
  at most `MAX_OUTBOUND = 512` frames;
- the receiver opens frames strictly in sequence order. It holds the
  HMAC-authenticated fragments of up to `REORDER_WINDOW = 64` later frames
  until the gap before them fills;
- its ACK carries three values under an HMAC with the channel's ACK key: the
  sequence below which every frame is durable (or can be obtained again after
  a restart), the sequence below which every frame has been accepted, and a
  64-bit map of the later frames it holds. An ACK naming a frame that was
  never sent, or durable beyond accepted, is rejected;
- the sender drops durable frames. It resends a frame the receiver reports
  missing behind held ones 15 ms after its last send, any other frame the
  receiver lacks after the retransmission timeout (60 ms, doubling to at most
  800 ms), and the oldest accepted frame when its durability ACK is 400 ms
  overdue. That last resend is a probe: its duplicate makes the receiver
  repeat an ACK that may have been lost;
- the map is only the receiver's current view. It counts a frame of which one
  fragment arrived, and the receiver drops a held frame it could not open
  yet. So the sender treats a frame as held only while the newest ACK reports
  it, and a frame the receiver stops reporting is resent after the timeout.
  Frames below the accepted sequence stay accepted, and a delayed ACK with an
  older accepted sequence changes nothing.

A frame that authenticates but cannot be verified yet is not accepted, and
its sender retransmits it. An example is an opening of a frontier this peer
has not assembled. Messages that arrive ahead of this peer are held and
applied once it catches up, at most 128 per remote:

- commitments and endorsements beyond its 64-tick assembly window;
- certificates beyond its next frontier;
- checkpoint signatures for boundaries it has not reached.

An opening of a frontier the peer has assembled but not yet certified is
checked against that assembled set and held until certification.

### Durability

The journal runs in group commit ([recovery](p2p-recovery.md)). A background
writer thread writes and syncs every record accepted since its previous write
at most once per `SYNC_INTERVAL`, one 60 Hz batch (33.3 ms). It then appends
the receipt to the `ReceiptLog` and syncs that. Each queued frame, ACK and
handshake answer names the journal records it depends on, and it leaves the
process only once they are durable:

- a commitment waits for its sealed opening;
- a set signature waits for its endorsement;
- an opening waits for its certificate and reveal records;
- a checkpoint signature waits for the confirmed state it signs;
- an ACK of evidence waits for the records that evidence created.

Commitments and set signatures from others are acknowledged without
journaling, as are early openings and deferred certificates. After a restart
their senders resend them, as described below. The receipt log is a
test-harness artifact like `ReceiptFiles`, not an independently trusted
rollback anchor.

### Protocol on each peer

Each peer:

1. seals its own opening under a fresh OS-random salt and sends the
   commitment;
2. assembles and endorses each complete window with `FrontierAssembler`;
3. certifies each frontier once every slot endorsed exactly its assembled
   set;
4. opens its commitment in every certified frontier. It journals received
   openings in groups of at most 64 per record;
5. executes frontiers in tick order;
6. signs the checkpoint of every 120-tick boundary and of the final tick, and
   gathers the others' signatures ([wire kind 5](p2p-pipeline.md#assembling-certificates)).

A signature over any other root or state is a divergence and stops the peer.
Once the final checkpoint is retained it journals `Finish`. It then stays
until every frame it queued is acknowledged and no datagram has arrived for
the linger time. A complete peer whose last frames go unacknowledged for 10 s
leaves anyway and reports how many were left.

### Restart and catch-up

A restarted process restores its journal against the receipt log's last
entry and resumes. It offers fresh keys to every slot. Each replaced channel
first carries the retained state the other side may have lost with its
process, then every frame not yet acknowledged on the old channel:

- certificates of pending frontiers;
- this peer's openings of the last 16 closed frontiers and of every pending
  one;
- its commitments and endorsements for uncertified windows;
- its last four checkpoint signatures.

The 16 closed frontiers are enough because a remote closes a frontier only
after this peer certified it, so the remote trails at most one full pipeline.
Certificates go first so the remote can verify the openings behind them. A
peer that certifies a frontier from a relayed certificate forwards it to the
others. The restarted peer never endorses that frontier again, so a peer that
never received its endorsement before the crash needs the certificate.
Receivers ignore anything they already hold.

### Dropout

`run_headless` carries out the local part of the
[dropout policy](p2p-pipeline.md#peer-dropout). Progress means a change in the
confirmed tick, the certified tick or the number of openings held for pending
frontiers.

1. **Stop combat.** When live evidence makes no progress for the stall limit
   (`--stall-seconds`, default 60 s, counted from the presentation start),
   the peer journals an interrupt. From then on it seals, endorses and
   predicts nothing new, and a restart from its journal stays stopped.
2. **Share.** The interrupted peer sends every pending certificate and its
   last certified checkpoint to every peer once more. Survivors that gathered
   different evidence before the dropout then hold the same certified
   frontiers, open their own commitments in them, and keep the latest
   checkpoint that any of them retained.
3. **Resolve available openings.** The peer keeps its channels open. A peer
   that returns resends its openings, and they close the frontiers its
   dropout left open, with no deadline.
4. **Finish or report.** Once combat has stopped or ended, the peer waits
   until the evidence makes no progress for the resolve limit
   (`--resolve-seconds`, default 60 s). If no certified frontier awaits an
   opening, it journals `Finish`, and its terminal outcome reports
   `completed=false` with the last certified checkpoint. Otherwise it stops
   with `MeshError::Unresolved`. The journal keeps the interrupt, the
   checkpoint, every pending frontier and every opening received, and only a
   consensus deadline can forfeit the missing openings. This transport has no
   consensus adapter.

The resolve limit also covers a match whose combat ended but whose final
checkpoint some peer never signed, for example one that left before a
restarted peer came back. The peer then finishes with the outcome its evidence
proves and reports the last checkpoint it retained. A missing signature
cannot erase that outcome.

A local timeout only stops combat; it forfeits nothing and settles nothing.
The wire carries only a sender's own openings. So an opening the dropped peer
sent to some survivors but not others closes that frontier only for the
survivors that received it. Which transcript is canonical is then
consensus's decision ([agreement](p2p-pipeline.md#peer-dropout)).

### `arena peer`

`arena peer` runs one headless, scripted peer on the shared presentation
clock:

```sh
arena-cli peer --slot N --peers 127.0.0.1:P0,...,127.0.0.1:P7 --dir DIR \
  [--ticks 7200] [--rate-hz 60] [--start-unix-ms MS] [--session N] [--restore] \
  [--drop N] [--duplicate N] [--reorder N] [--corrupt N] [--impair-seed N] \
  [--research-lan] [--progress TICKS] [--stall-seconds S] [--resolve-seconds S]
```

It plays the eight-peer research script: 4v4 Control on the Nyaagyu Estate,
Samurai with Arc carbines, zero bond. Keys derive from the public session
number, so anyone can sign for any slot. They are research keys and can admit
only offline zero-bond matches.

- `--rate-hz 0` presents as fast as the pipeline allows.
- `--restore` continues from `DIR/peer-N.journal` and `DIR/peer-N.receipts`.
- The four damage flags are per mille and apply to every outgoing datagram:
  data, ACKs and handshake packets. `--reorder` holds a datagram behind the
  next one to the same peer or for 8 ms; `--corrupt` flips one bit.
- `--stall-seconds` and `--resolve-seconds` are the [dropout](#dropout)
  limits.

Controls are committed when their batch is due, `INPUT_DELAY_TICKS` ahead.
The script also commits the lead-in batches with its known controls, where a
human client commits idle. Remote players are predicted with their last
confirmed controls. The command prints `ready`, `restored` (with restore time),
`progress` and one `result` line of key=value fields, then exits 0. After a
dropout the result reports `completed=false`, and `checkpoint_tick=none` if no
checkpoint was certified. When combat stopped with frontiers still pending, it
prints `unresolved slot=N confirmed=T pending=K` and exits 1.

### Multi-process harness

`crates/arena-cli/tests/mesh_processes.rs` starts every peer as its own OS
process and only kills, restarts and reads them. Each final `result` must
report:

- the same state hash, matching a kernel `World` stepped with the same
  script;
- the same transcript root;
- a final checkpoint at the last tick, over that state and root;
- a completed match with no consensus deadline.

The quick test runs in the normal suite. Four processes present 360 ticks as
fast as the pipeline allows, with 2% drop, duplication and reordering and 1%
corruption on every datagram. The harness SIGKILLs slot 2 once it has
confirmed tick 120 and restarts it 300 ms later.

The dropout test also runs in the normal suite. Four processes present 360
ticks as fast as possible with 2 s stall and resolve limits. The harness
SIGKILLs slot 3 once it has confirmed tick 120 and never restarts it. Each
survivor must end with `unresolved`, or with a `completed=false` result if
nothing was pending. The harness then restores every survivor's journal. Each
must be interrupted short of the clock, and every pending frontier must lack
only slot 3's opening. All survivors must hold the same certified frontiers.
Each survivor that confirmed the latest checkpoint any of them retained must
hold it too. A survivor restarted from its journal must then exit without
journaling anything.

Four two-minute tests are opt-in:

```sh
cargo test --locked --release -p arena-cli --test mesh_processes -- --ignored --nocapture --test-threads=1
```

Three run eight processes, 7,200 ticks at 60 Hz, and first check the
pinned final hash `5d000cfd…` of the
[eight-peer research fixture](proof/eight-peer-loopback-research.md):

- **baseline**: no damage;
- **kill-restart**: slot 5 is SIGKILLed once a progress line shows confirmed
  tick 3,600 or later, and restarted 1 s later from its journal;
- **impaired**: 5% drop, 5% duplication, 5% reordering and 1% corruption on
  every datagram of every peer.

The fourth, **six-versus-six**, runs twelve processes as 6v6 Control with
the same script and no damage. Its final state is checked against a kernel
`World` stepped with that script; no hash is pinned for it.

### Measured runs

Recorded runs on 2026-09-25, 23:18–23:25 JST, one test at a time with
`--test-threads=1` in release, on the Apple M1 Ultra (20 cores, 128 GB),
macOS 27.0, Rust 1.97.1. All eight journals and receipt logs were on one APFS
SSD with about 66 GiB free. Other work shared the machine: the load average was
10.6 at the start of the baseline, 27.7 at its end and 10.8 after the
impaired run. The three scenarios are therefore not a controlled comparison,
and every figure is one run on one machine, not a network qualification.
The confirmation run after the table used the code as first reviewed. The
review fixes then changed how a peer runs: the ACK view, the dropout policy
and handshakes after finishing. Runs of the fixed code, and the first 6v6
runs, follow under [after the review fixes](#after-the-review-fixes).

In each run all eight processes exited 0 with the pinned final state
`5d000cfd7b28526bfa55fe0050c0d47872fa6c9831b189f6ea5c602d0af019ea`, one
transcript root and a final checkpoint at tick 7,200. The root changes from
run to run because salts are random. Each peer retained 60 checkpoints, and
none was missed. Each peer sealed 76,020 frames, one per message per remote.
In the kill-restart run the survivors sealed 76,110, including the retained
state they resent. A process started 2.5 s before tick 0 and lingered about
2 s at the end, so each ran about 124.6 s.

Confirmed-timeline lag is `predicted − confirmed` after each presented tick,
in 60 Hz ticks: 14 ticks is 233 ms and includes the 4-tick input delay. A late
tick was presented more than one tick period after its wall-clock slot.
Ranges are over the eight peers.

| | Baseline | Kill-restart (7 survivors) | Impaired |
| --- | --- | --- | --- |
| Lag mean / p50 | 14.2–14.6 / 13 | 14.2–14.4 / 11–12 | 15.7–15.9 / 15–16 |
| Lag p99 / max | 39–41 / 55–59 | 86–87 / 93 | 25–26 / 35–37 |
| Late ticks of 7,200 | 263–345 | 243–259 | 0–3 |
| Latest tick | 95–137 ms | 2.47–2.63 s | 14–35 ms |
| Datagrams sent per peer | 112,849–113,398 | 119,596–120,045 | 124,859–125,851 |
| Bytes sent per peer | 38.7–38.8 MB | 39.2–39.3 MB | 41.3–41.4 MB |
| Datagrams resent, all peers | 2,373 | 2,528 | 39,421 |
| Gap resends / timeout events per peer | 0 / 25–55 | 0 / 72–85 | 4,345–4,533 / 382–426 |
| Journal syncs per peer | 2,719–2,750 | 2,877–2,909 | 2,810–2,835 |
| Journal sync mean / max | 20.7–20.9 / 171–276 ms | 19.6–20.0 / 191–220 ms | 21.1–21.5 / 149–264 ms |
| Receipt sync mean / max | 18.8–19.1 / 138–257 ms | 18.0–18.2 / 169–209 ms | 19.4–19.7 / 156–266 ms |
| Records / bytes synced per peer | 26,671–27,120 / 5.98–6.00 MB | 29,669–30,404 / 6.10–6.13 MB | 26,521–27,271 / 5.97–6.00 MB |

The baseline's delivery is nearly lossless: about 0.26% of datagrams were
resent after a timeout. Those resends and the late ticks follow sync stalls
and machine load. A frame waits for its records to be durable, and sync
latency reached 276 ms.

**Kill and restart.** Slot 5 was SIGKILLed after a progress line at
presented 3,900, confirmed 3,890. It restarted 1 s later and restored 16,512
records in 2,205 ms. It then presented the remaining 3,310 ticks: 295 were
late, the latest by 3.40 s, and its lag was 17.1 mean, 90 p99. The seven
survivors stalled for about 2.5 s while it was away and restoring, then caught
up with it. Each survivor replaced exactly one channel and ended at the same
hash and root.

**Impaired.** Every peer dropped about 6,300 of its outgoing datagrams,
duplicated about 5,650, reordered about 6,000 and corrupted about 1,200. The
receivers rejected 1,218–1,318 datagrams each on authentication or framing,
and 14,284–15,040 fragments arrived ahead of a gap. About 3.9% of datagrams
were resends, nine in ten of them for a reported gap. The outcome did not
change, and presentation stayed on schedule.

**Sync cost.** A writer hands off at most once per 33.3 ms. A group write,
one journal sync and one receipt-log sync, took about 40 ms under eight-way
contention, so each covered more than one batch. The runs averaged 0.76–0.81
journal syncs per batch and about ten records per sync. macOS `sync_all` is
`F_FULLFSYNC`. A separate probe on the same disk, running Python `fcntl`
`F_FULLFSYNC` after 1,500-byte appends with 200 syncs per writer, measured:

| Concurrent writers | Mean per sync |
| --- | --- |
| 1 | 4.97 ms |
| 8 | 18.6 ms |
| 16 | 29.9–32.6 ms |

Sixteen synced files on one disk, eight journals plus eight receipt logs,
overstate what one player's machine pays.

A confirmation run of all three tests on the final code, 23:43–23:49 JST with
a load average of 22–29, also passed with the same final state. Its timing
was different. The baseline had lag p99 22–23 and max 32, with 21–37 late
ticks. The impaired run had lag p99 40–41 and max 52–56, with 10–20 late
ticks. In the kill-restart run, slot 5 was killed at confirmed 3,886 and
restored 13,432 records in 4,269 ms. Its journal reached confirmed 3,884,
because records not yet synced die with the process. The survivors were late
on 1,382–1,423 ticks, by up to 5.4 s.

The quick four-process test finished in 7.8 s in the debug build. It killed
slot 2 at confirmed tick 138, restored 328 records in 211 ms and agreed on the
360-tick reference.

#### After the review fixes

On 2026-09-26, 00:38–00:47 JST, one release run of all four opt-in tests
passed on the fixed code, one test at a time. The load average was 9.0 at its
start, 11.7 after the baseline and 18.0 at its end. A second 6v6 run followed
at 00:47–00:50, with the load rising from 15.5 to 21.5. The same caveats
apply: one machine, other work sharing it, one run per column.

Every 8-process run ended at the pinned state `5d000cfd…`. Both 6v6 runs
ended at `bff2753cc23f277ba9dd29dc66a38f70deddf38e6cc59bfbb28b711fad4f21f9`,
the state of a kernel `World` stepped with the script for twelve players. In
every run each process reported one transcript root and a final checkpoint at
tick 7,200, and retained all 60 checkpoints. A 6v6 peer sealed 119,460
frames, one per message for each of eleven remotes.

| | Baseline | Kill-restart (7 survivors) | Impaired | 6v6, first | 6v6, second |
| --- | --- | --- | --- | --- | --- |
| Lag mean / p50 | 11.3–11.5 / 11 | 14.2–14.4 / 11 | 16.6–16.8 / 16 | 18.6–19.4 / 16–17 | 17.0–17.6 / 16 |
| Lag p99 / max | 22 / 26–27 | 86–88 / 93 | 29 / 37–41 | 56–61 / 72–76 | 41–44 / 57–63 |
| Late ticks of 7,200 | 7–13 | 231–243 | 60–87 | 325–385 | 140–185 |
| Latest tick | 50–170 ms | 2.57–2.74 s | 62–147 ms | 132–315 ms | 70–169 ms |
| Datagrams sent per peer | 121,843–122,232 | 120,047–120,707 | 123,036–123,745 | 173,505–174,163 | 173,005–173,844 |
| Bytes sent per peer | 39.3 MB | 39.3–39.4 MB | 41.2–41.3 MB | 66.5–67.2 MB | 65.6–65.9 MB |
| Datagrams resent, all peers | 56 | 2,452 | 41,431 | 35,404 | 8,325 |
| Gap resends / timeout events per peer | 0 / 0–7 | 0 / 58–73 | 4,342–4,560 / 489–566 | 0 / 254–362 | 0 / 59–106 |
| Journal syncs per peer | 3,005–3,041 | 2,892–2,922 | 2,725–2,768 | 2,392–2,432 | 2,440–2,481 |
| Journal sync mean / max | 19.4–20.0 / 168–212 ms | 19.7–20.3 / 189–211 ms | 21.3–21.8 / 138–209 ms | 23.9–24.6 / 166–259 ms | 24.2–24.6 / 167–219 ms |
| Receipt sync mean / max | 17.3–17.7 / 165–198 ms | 17.8–18.1 / 164–198 ms | 19.3–19.9 / 102–216 ms | 21.1–21.7 / 145–228 ms | 21.2–22.0 / 160–204 ms |

In the kill-restart run slot 5 was killed at confirmed 3,888 and restored
16,909 records in 2,226 ms, at confirmed 3,886. It presented the remaining
3,314 ticks: 302 were late, the latest by 3.48 s, and its lag was 17.5 mean,
91 p99.

**6v6.** Twelve processes agree on the outcome, but they do not hold 60 Hz
presentation on this machine. Of 7,200 ticks, 1.9–5.3% were late, by at most
315 ms, and the lag p99 of 41–61 ticks is 0.7–1.0 s behind presentation. Each
peer resent 0.3–2.1% of its datagrams, all after timeouts, although nothing
was dropped on purpose. A review run of the code before the fixes, as twelve
`arena peer` processes with a load average of 18–20, was late on 4,506–4,614
ticks, with a lag p99 and maximum of 93 and about 15% of datagrams resent.
These runs are not a controlled comparison. The load differed, and the review
run predates the ACK change: before it, a held frame the receiver dropped
waited for the 400 ms probe, and every later frame waited behind it.
Twenty-four synced files on one disk, twelve journals plus twelve receipt
logs, also overstate what one player's machine pays.

### Limits

- One machine, loopback only. There is no real network jitter or bandwidth
  limit, no NAT or relay, and no peer discovery. The damage is injected, not
  measured on a network.
- 6v6 is measured only as twelve processes on one machine, and there it does
  not hold 60 Hz presentation: 1.9–5.3% of ticks were late in two runs.
- A peer that never returns holds every other peer at its prediction horizon
  until the stall limit, then stops combat. Its missing openings leave the
  survivors unresolved: there is still no consensus adapter to publish
  evidence or decide the deadline that forfeits them.
- Keys derive from a public session number, and admission is offline with
  zero bond. The receipt log is a local harness artifact, not an independent
  rollback anchor.
- `ReceiptLog`, the channel sequences and the handshake replay guard assume
  one writer process per slot. A second process for a live slot is refused by
  the journal and receipt-log locks, not by the network.
- There is no execution proof, verifier or settlement. The mesh gives
  evidence agreement, not value transfer.
