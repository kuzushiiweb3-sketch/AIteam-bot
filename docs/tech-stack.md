# Tech stack: languages, libraries, storage format and testing

## In plain English (for Paul)
- The parts that run all day and handle money maths are written in **Rust**, a strict, fast language that catches many mistakes before a program ever runs and does exact maths on Pump.fun's very large whole numbers. **Python** is used only for research and statistics. Pump's own TypeScript toolkit is used **only inside tests**, as an independent referee.
- Recorded market history is kept twice: as the exact bytes we received, so we can re-read them after Pump changes something, and as tidy tables that research can search fast. The recorder saves to disk in small batches every 50 thousandths of a second (milliseconds), so it never falls behind the feed. A crash loses at most that last fraction of a second, and usually nothing, because the feed lets us replay the last minute.
- **The locked test data really is locked.** Data set aside for final exams is stored where research code physically can't open it. Only one frozen scoring program can open it, only on the scheduled day, and every opening is logged. Registration times are proven by the blockchain's own clock and by outside copies, not by dates on our own computer, which anyone could fake.
- **Failed transactions never count as trades.** A failed transaction can still carry a perfect-looking trade receipt, so the decoders file those receipts separately and never let them change a price or a holding.
- **Cost: still $0** in licences. Programs are built on a machine that holds no passwords, then copied to the server and checked by fingerprint. Each job on the server runs as its own user and can read only its own password. The AI jobs get their own keys and spending limits.

**Status: ADOPTED v1.1 (pending red-team check of fixes).** Data engineer, 2026-11-05. v1.0 (PROPOSED, SHA-256 `158dd271da949abc5153b12037dc0561f8ad16daa9b29c557b3f8daa57448c9c`) was reviewed in `team-debate/phase0/red-team-phase0-review.md` §5: SIGN OFF WITH FIXES, with TS-1, TS-2, TS-6 and TS-8 blocking. This version puts all twelve findings in (changelog below). Nothing in this file signs, sends or simulates a transaction.

**Tags.** [VERIFIED-DOC] = I read the primary source this session (for packages: the official registry's own metadata; for code: the project's own source on GitHub), fetched 2026-11-05. [VERIFIED-SEARCH] = search results only. [VERIFIED-LOCAL] = I ran it in this environment today. [UNVERIFIED] = judgment or memory; the settling test is named. [DERIVED] = arithmetic on tagged inputs. Web searches used: 8 in total (6 for v1.0, 2 for v1.1). Reachable from the shell: the registries (npm, crates.io index, PyPI, Go proxy, nodejs.org) and `raw.githubusercontent.com`. Still blocked: `www.helius.dev`, `mainnet.helius-rpc.com`, `api.mainnet-beta.solana.com`.

---

## v1.1 changelog (each red-team finding → what changed, and where)

| Finding | Severity | What v1.1 does | Where |
|---|---|---|---|
| **TS-1** sealing and scoring need code | High, **blocking** | (1) **One frozen scorer**, `desk-score` (Rust), computes every ticket verdict, bootstrap included. Its source and binary hashes are registered. It is tested against known-answer cases checked with scipy, and it must reproduce PR-9's simulation. (2) **Physical sealing**: sealed days (raw tape, decoded tables *and* every outcome-bearing output) live in a store that only the `scorer` Unix user can read. Research can't open it, so a stray "run on all days" script fails with "permission denied" instead of leaking. (3) **Append-only, hash-chained ledger** of registrations and of every sealed read, with an OS audit watch as a second log. (4) **Timestamps that don't depend on git dates**: each entry carries a Solana slot and blockhash (proves "not before"). The ledger head goes hourly into the write-once archive and daily into Paul's summary, which proves "not after". An RFC 3161 timestamp is added once its domain is allowed. (5) `desk-score` **mechanically refuses** holdout days that start before a registration's outside anchor, so reserve and new-version tickets get fresh days only (PR-3.1). (6) **Python never computes `net_i`**: it reads nets written by `desk-sim`, after checking their hash | §5l, §5g, §5f, §0, §7, §8 |
| **TS-2** a flush after every frame makes the recorder lag | Medium-High, **blocking** | The network task never touches the disk. A bounded memory queue feeds a writer, and a separate syncer runs **group commits** (`fdatasync` when the oldest unsynced frame is 50 ms old or 1 MB is unsynced, whichever comes first). **Crash-loss bound stated**: a process crash loses only what is still queued (normally under 1 ms). A host crash loses ≤ 50 ms or ≤ 1 MB, plus one sync's duration. On restart, `from_slot` replay inside the provider's replay window usually recovers even that. The server's real drop behaviour was read from its source (it disconnects slow clients). Queue, sync-latency and "lagged" alarms. STK-1 is extended to the real disk, the busiest hour and a 10× burst (TS-T1) | §5a, §6b, §12 |
| TS-3 the silent-feed probe needs an independent count | Medium | Once a minute, a signature sample for Pump and PumpSwap from Helius (not our stream) is compared with our tape for the same slots. There is also a daily independent migration audit (PR-1) and the slot-lag check | §5e |
| TS-4 no emergency path for the gRPC client | Medium | A written **fast lane** mirroring SEC-5, plus less exposure in the first place: production uses **our own thin client**, generated once from the pinned `geyser.proto` and committed, so a provider change means a small, reviewable proto diff, not a jump across major versions of a third-party crate. Fallbacks while the lane runs: the Helius narrow streams, a Solana Tracker trial recorder, or the TS-10 fallback | §9b, §5a, §0 |
| TS-5 second source for the IDL | Low | The on-chain IDL accounts (Anchor's legacy account and the Program Metadata `idl` account) are checked against the GitHub pin in Phase 0, then watched hourly with the ProgramData deploy slot | §5e, §12 TS-T2 |
| **TS-6** events inside failed transactions | High, **blocking** | Decoder rule F1: an event from a transaction with `meta.err` set is tagged `FAILED_TX_EVENT`. It is stored for research and **can never change state, price, holdings, labels or two-witness**. Types enforce this at compile time. F2: event provenance (same program, child of that program's instruction, signed by that program's `__event_authority`). F3: events in dead-fork slots are tagged `FORKED` and kept out of outcome prices. F4: `inner_instructions_none` raises `NO_INNER_IX`, never "no trades". Found while fixing: Agave records inner instructions **whatever the result**, so the threat is real at the validator. AR-T1 checks what RPC and the stream deliver. Hostile fixtures cover all four rules | §5b, §8, §12 AR-T1 |
| TS-7 the seller needs a different *method* | Medium (Phase 3) | Conservative constant-product min-out with a fixed fee ceiling, no tier logic, and a real-payout (6063) pre-check. The differential test becomes "seller ≤ guard ≤ chain". Pool state comes from a different provider. Blocking input/output and a different TLS library. Rust kept; Go not required | §5j |
| **TS-8** build scripts run code; the AI key sits with research | Medium-High, **blocking** | (a) **No builds on any host that holds a secret.** Binaries are built in a secret-free builder, hashed and `cargo auditable`, and the bot host installs only hash-checked binaries. It has no compiler toolchain. Python installs are wheels-only (`no-build = true`) under a user with no secrets. Per-service Unix users, one secret each, delivered by systemd credentials (not environment variables), with per-user network allow-lists. Two build scripts removed (the proto crate's vendored `protoc`, the `crc32c` crate). (b) The change reader and the AI desk run as **their own users**, with **zero third-party Python packages** (a small stdlib-only Messages-API client) and **separate Anthropic keys and spend limits** (CO-3). (c) **Exact pins**: pyarrow ==26.0.0 and the others | §5h, §9c, §6b, §0 |
| TS-9 the archive must be undeletable from the bot host | Medium | Put-only credentials, provider-side versioning plus object lock, delete rights only with Paul, a daily list-check and a monthly restore drill | §6c, §12 TS-T5 |
| TS-10 the TypeScript recorder fallback needs review | Low | Own user, only the stream key, strict pnpm settings, built in the secret-free builder, native add-on hash recorded, security and red-team review before first use | §9d, §4.1 |
| TS-11 research reads can starve the recorder's disk | Low-Medium | Open segments on their own volume, which research never reads. Research gets hard bandwidth caps (`io.max`, which works on every device) plus a low `IOWeight` (best effort: it needs iocost or BFQ). Sync-latency alarm | §6b, §5a |
| TS-12 receive times need a disciplined clock | Low | chrony. A `CLOCK` control frame every 60 s with the measured offset. Order by the monotonic clock within a connection, and by corrected wall time plus (slot, index) across connections. Alarm on drift | §5a |
| Red-team §4.2 answer | — | The "bps text scan" is now secondary. The primary control is the hash-checked nets rule (TS-1.6) | §5g |
| Red-team §4.5 answer | — | The SDK referee runs in a throwaway container: network off after install, no secrets, outputs only vector files | §9a |
| Red-team §11.7 answer | — | `cargo vet` audit sources are chosen before Phase 3. Every guard-workspace crate must be "safe-to-deploy" by a named audit or our own review | §9a, §11 |
| Seams | — | CO-3: separate AI keys. PR-13: a guard-feed shadow recorder from day 1. PR-15.7: slot-completion markers on the tape. PR-16: a `gaps` table. PR-1: the migration audit in monitors. CO-5: paused funding lookups are logged as gaps. Prereg §2.4.5: the fork rule matches it. Prereg v1.1 and Phase 0 simulations: the scorer seam (§5l, last item) | §5a, §5b, §5d, §5e, §5l, §6b |

---

## 0. The decision in one table

| Part (DESIGN §2b, §7) | Language | Main libraries (exact pins below are the newest versions that pass the 7-day cooldown on 2026-11-05; the lockfile is the final truth) | Why, in one line |
|---|---|---|---|
| 1 Recorder | **Rust** | **Our own thin gRPC client**: stubs generated once from the pinned `geyser.proto` + `solana-storage.proto` (vendored, hashed, committed, "GENERATED"). Runtime: `tonic` 0.14.8, `prost` 0.14.4, `tokio` 1.54.1 [VERIFIED-DOC crates index]. Our own CRC32C. `yellowstone-grpc-client` is a test-only reference and a fast-lane fallback (16.0.1 passes the cooldown; 17.0.0, published 2026-10-30, doesn't yet) [VERIFIED-DOC crates index] | No garbage-collector pauses. No third-party client churn or build-time `protoc` in production (TS-4, TS-8a). Keeps up with bursts on one core [UNVERIFIED; TS-T1] |
| 2 Decoders | **Rust**, generated by our own `idlgen` tool from Pump's pinned IDL JSON | No third-party decoder. Plain byte-offset code; `borsh` 1.8.1 only if needed | Exact-length decoding, version tables and the failed-transaction rule are ours (NEW-8, TS-6). Exhaustive `match` makes "an unknown event is an alarm" a compile-time rule |
| Fees module (`fees/`) | **Rust** | none beyond `std` | One implementation of the fee maths. Integer-only, overflow-checked, `i128` native |
| 3 Forensics / coin state | **Rust** | same as recorder | No network calls in the decision path (DESIGN §2b.3) |
| Monitors (`monitors/`) | **Rust**, its own process | `reqwest` 0.13.5 (rustls) + `serde_json`, `tokio-tungstenite` 0.30.0, `rusqlite` 0.41.1 | Small, separate, restarts on its own. **Not** `solana-client` (§5e) |
| 4 Strategy engine + 5 paper simulator (`strategy/`, `sim/`) | **Rust** | none heavy | Backtests and the live paper bot run the *same* rule code and the same fill maths |
| **Scorer (`score/`, new in v1.1)** | **Rust**, binary `desk-score` | `rand_chacha` 0.10.0 (raw random stream only), `statrs` 0.19.1 (t quantiles, checked against scipy golden values) [VERIFIED-DOC crates index] | **The only program that decides a ticket's pass or fail**, and the only reader of sealed data (TS-1) |
| 6 Research, exploration, daily report | **Python 3.13** with **uv** | `polars` ==2.1.0, `duckdb` ==2.0.0, `pyarrow` ==26.0.0, `numpy` ==2.5.4, `scipy` ==1.18.1 [VERIFIED-DOC PyPI; pyarrow 26.0.1 was only 2 days old] | The best analysis tools. Python reads open Parquet only, and never computes a fill, a fee or a verdict |
| Nightly AI desk, rule-change reader | **Python, standard library only**, each as its own user | Our own ~150-line Messages-API client (`urllib`, `json`, `ssl`). The official `anthropic` SDK (2.3.0 passes the cooldown) pulls in 8 required packages, including pydantic, httpx2, jiter and opentelemetry-api [VERIFIED-DOC PyPI], so it stays out of the key-holding environments (TS-8b) | Outputs rule *files* in the fixed rule language, which `desk-sim validate` checks. The AI never outputs code that runs |
| 7 Dashboard (Phase 3) | **Rust** (`axum`, server-rendered HTML), decided in Phase 3 | no npm build | Keeps npm off the production hosts. Reads only open data and the scorer's allowed summaries |
| 8–9 Guard and exit guard, 10 safe-mode seller (Phase 3, **provisional**) | **Rust**, separate workspace, vendored dependencies | AWS SDK for Rust [UNVERIFIED versions; Phase 3]. The seller uses blocking input/output and a different TLS library (§5j) | A single static binary with the fewest dependencies. The seller uses a different *method*, not only different code (TS-7) |
| Pump SDK "referee" (test only) | **TypeScript** on Node LTS, pnpm, in a throwaway container | `@pump-fun/pump-swap-sdk` / `@pump-fun/pump-sdk`, exact pins | Golden test numbers from Pump's own quote functions. Never deployed, never on a host with secrets |
| Phase 0 test scripts | **Python, standard library only**, including a small IDL-driven decoder (as built in `phase0/scripts/p0/`); **Rust** for websocket and gRPC probes | zero third-party Python packages | Zero supply-chain risk now. The Python decoder becomes an **independent second decoder** for differential tests (§5k) |
| Recorded tape | Raw **framed segment files** (exact bytes, zstd) + hourly **Parquet** tables, split into an **open** and a **sealed** store; DuckDB / Polars; **SQLite** for small operational state | `parquet`/`arrow` 60.1.0 [VERIFIED-DOC crates index] | Group-committed, so it survives crashes with a stated loss bound. Keeps exact bytes for re-decoding. No server (§6) |

---

## 1. What I checked (evidence for the comparison)

| Fact | Value | Tag |
|---|---|---|
| Official Yellowstone gRPC examples | Go, Rust and TypeScript only. A reconnecting client exists for Rust (`client_with_reconnect`) and TypeScript. The server sends a `Ping` every 15 s | [VERIFIED-DOC github.com/rpcpool/yellowstone-grpc README] |
| **Yellowstone server and slow clients (v1.1)** | Each subscriber has a bounded queue (code default `channel_capacity` 250,000 updates; the example config uses 100,000). Updates are pushed with `try_send`. When the queue is full, the server **disconnects** the client with `"lagged to send an update"` (reason `client_channel_full`). It does not slow down for us. A `from_slot` replay waits at most `client_unresponsive_timeout` (default 60 s) for the client | [VERIFIED-DOC yellowstone-grpc-geyser/src/grpc.rs, src/config.rs, config.json] |
| **Replay window (v1.1)** | `replay_stored_slots` defaults to 150 slots in code (about 1 minute) but is 0 in the example config, so it is **provider-specific**. `SubscribeReplayInfo` returns `first_available`, the oldest slot that can be replayed | [VERIFIED-DOC config.rs, config.json, geyser.proto]; Chainstack's value [UNVERIFIED; C04] |
| **Slot statuses (v1.1)** | `SLOT_PROCESSED`, `CONFIRMED`, `FINALIZED`, `FIRST_SHRED_RECEIVED`, `COMPLETED`, `CREATED_BANK`, `DEAD`. The slots filter has `interslot_updates`, and the request has `from_slot` | [VERIFIED-DOC geyser.proto] |
| **Transaction metadata on the stream (v1.1)** | `TransactionStatusMeta` carries `err`, `inner_instructions` and an `inner_instructions_none` flag | [VERIFIED-DOC yellowstone-grpc-proto/proto/solana-storage.proto] |
| **Failed transactions keep their inner instructions at execution (v1.1)** | Agave's transaction processor builds the inner-instruction list from the instruction trace in `deconstruct_transaction`, which runs **whatever the result**. So a CPI event emitted before the failing instruction is in the failed transaction's execution record | [VERIFIED-DOC github.com/anza-xyz/agave svm/src/transaction_processor.rs]. Whether RPC `getTransaction` and the stream deliver it: [UNVERIFIED; AR-T1] |
| **Event authority (v1.1)** | Both IDLs define `event_authority` as the PDA with seed `"__event_authority"` | [VERIFIED-DOC pinned pump.json, pump_amm.json] |
| **On-chain IDL locations (v1.1)** | Anchor legacy: `create_with_seed(find_program_address([], program), "anchor:idl", program)`; layout = 8-byte tag, authority (32), `data_len` u32, zlib-compressed JSON. It is deprecated in favour of the Program Metadata program `ProgM6JCCvbYkfKqJYHePx4xxSUSqJp7rh8Lyv7nk7S`, whose *canonical* `idl` account is derived from [program, "idl"] and created by the upgrade authority | [VERIFIED-DOC anchor lang/src/idl.rs; solana-program/program-metadata README]. Which one Pump uses: [UNVERIFIED; TS-T2] |
| Rust client `yellowstone-grpc-client` | 17.0.0 published 2026-10-30. **Major versions 13 → 17 between 2026-09-15 and 2026-10-30.** Newest that passes the cooldown today: 16.0.1 (2026-10-27) | [VERIFIED-DOC index.crates.io] |
| **`yellowstone-grpc-proto` build script (v1.1)** | 14.0.1 has build dependencies `protoc-bin-vendored` and `tonic-prost-build`, so building it runs a bundled `protoc` binary at compile time | [VERIFIED-DOC index.crates.io] |
| **`crc32c` crate (v1.1)** | Has a build script (0.6.8 passes the cooldown; 0.6.9 is 3 days old) | [VERIFIED-DOC index.crates.io] |
| TypeScript client `@triton-one/yellowstone-grpc` | 10.0.0, 2026-10-31. Rust engine as a prebuilt native Node add-on (napi). No npm provenance | [VERIFIED-DOC registry.npmjs.org] |
| Why it moved to napi | Triton claims 400% more throughput (its own benchmark) and advises splitting big streams across workers | [VERIFIED-SEARCH blog.triton.one; quicknode.com docs] |
| Python Yellowstone client | **None published** on PyPI | [VERIFIED-DOC pypi.org] |
| Go Yellowstone client | Only the `examples/golang` module, with a pseudo-version | [VERIFIED-DOC proxy.golang.org] |
| Pump's official SDKs | `@pump-fun/pump-sdk` 4.3.1 (140 versions), `@pump-fun/pump-swap-sdk` 2.2.0 (105 versions). Both on legacy `@solana/web3.js` ^1.98 and `@coral-xyz/anchor` ^0.31; `pump-sdk` pulls in `@pump-fun/agent-payments-sdk` 1.0.7. No provenance | [VERIFIED-DOC npm registry; README] |
| Pump's official Rust crate | `pump-rust-client` 0.5.0; requires Anchor ≥ 0.31 and Solana crates < 3 (today's `solana-sdk` is 5.0.0) | [VERIFIED-DOC README; index.crates.io] |
| Python Pump packages | None official. PyPI has unofficial look-alikes `pumpfun`, `pumpswap-sdk` | [VERIFIED-DOC README; pypi.org] |
| Pump IDLs | Anchor's new IDL format. pump.json: 56 instructions, 32 events; pump_amm.json: 38 / 27; pump_fees.json: 31 / 22. SHA-256 `7616681e…`, `b7d8c57a…`, `6b9fa3ec…` | [VERIFIED-DOC raw.githubusercontent.com, computed locally] |
| Wide integers | PumpSwap's `virtual_quote_reserves` is **`i128`** in `Pool`, `BuyEvent`, `SellEvent`, `BoostBuyAndBurnEvent` | [VERIFIED-DOC pump_amm.json] |
| Discriminators collide across programs | `buy_v2` = `b817ee6167c5d33d` in both Pump and PumpSwap | [VERIFIED-DOC, computed from the IDLs] |
| Code generators (Codama) | JS renderer 2.8.0, Rust 3.1.3, Go 2.1.0. No Python renderer. Event support unconfirmed | [VERIFIED-DOC npm; UNVERIFIED for events] |
| Anchor clients | `@coral-xyz/anchor` 0.32.1 (2025-10-10). `anchorpy` 0.21.0 (2025-03-26), pins `solana<1.0` | [VERIFIED-DOC npm, PyPI] |
| Solana core libraries | `@solana/kit` 8.6.0 (provenance). Rust `solana-client` has 30 direct dependencies and needs rustc 1.98.1. Python `solders` 0.29.0. Go `solana-go` v1.26.0 | [VERIFIED-DOC registries] |
| **Python pins (v1.1)** | Newest ≥ 7 days old on 2026-11-05: pyarrow 26.0.0 (2026-10-09), polars 2.1.0 (10-25), duckdb 2.0.0 (10-21), numpy 2.5.4 (10-10), scipy 1.18.1 (08-21), anthropic 2.3.0 (10-23) | [VERIFIED-DOC pypi.org JSON] |
| **uv wheels-only (v1.1)** | `no-build = true`: operations that would build a source distribution exit with an error. Our own workspace packages are still built | [VERIFIED-DOC astral-sh/uv crates/uv-settings/src/settings.rs] |
| **systemd credentials (v1.1)** | `LoadCredential=` / `LoadCredentialEncrypted=` hand a secret to one service as a file under `$CREDENTIALS_DIRECTORY`. Unlike environment variables, it isn't passed down to child processes | [VERIFIED-DOC systemd docs/CREDENTIALS.md, man/systemd.exec.xml] |
| **Disk input/output control (v1.1)** | `IOWeight=` sets `io.weight`, and `IOReadBandwidthMax=` sets `io.max` [VERIFIED-DOC systemd.resource-control.xml]. Absolute limits (`io.max`) work on all devices. Weights work only with the iocost controller or the BFQ scheduler [VERIFIED-DOC kernel Documentation/admin-guide/cgroup-v2.rst] | as cited |
| Node | LTS 22/24/26; `node file.ts` runs directly on 22.23.4 | [VERIFIED-DOC nodejs.org; VERIFIED-LOCAL] |
| Toolchains here | Rust 1.97.0, Python 3.13.18, uv 0.11.32, Node 22.23.4, pnpm 10.28.0, Go, OpenSSL 3.0.13 | [VERIFIED-LOCAL] |

---

## 2. Languages compared (at least 3 options; here 4)

*(Unchanged from v1.0; red-team accepted the split.)*

| Criterion | **Rust** | **TypeScript / Node** | **Python** | **Go** |
|---|---|---|---|---|
| **Speed where it matters** | Native code, no garbage collector. Most headroom [UNVERIFIED size; TS-T1] | Good once the napi engine does the gRPC work. Single main thread [VERIFIED-SEARCH]. GC pauses [UNVERIFIED] | Slowest for byte decoding; the GIL limits parallelism [UNVERIFIED size]. Fine for research | Native; short GC pauses [UNVERIFIED] |
| **Yellowstone gRPC client** | **Best**: reference client, and `tonic` can generate our own stubs from the proto [VERIFIED-DOC] | Rust engine inside a prebuilt npm binary [VERIFIED-DOC] | **None** [VERIFIED-DOC] | Examples only [VERIFIED-DOC] |
| **Pump SDK and IDL code generation** | `pump-rust-client` tied to Solana 2.x and Anchor [VERIFIED-DOC]. Codama Rust 3.1.3 | **Best official support**, but on legacy web3.js v1 + Anchor 0.31, frequent releases, no provenance [VERIFIED-DOC] | No official SDK; `anchorpy` stale [VERIFIED-DOC] | No SDK; Codama Go new [VERIFIED-DOC] |
| **Solana library maturity** | Authoritative but heavy; we need small pieces | `@solana/kit` first-party, but Pump's SDKs use old web3.js types [DERIVED] | community-maintained [VERIFIED-DOC] | one main maintainer [UNVERIFIED] |
| **Supply-chain risk** | Real incidents (`faster_log`/`async_println`, ~4 months online) [VERIFIED-SEARCH blog.rust-lang.org]. Build scripts and macros run at compile time (§9c). Native cooldown in Rust 1.100, 2026-11-12 [VERIFIED-SEARCH]. `pubtime` lets CI enforce a cooldown today [VERIFIED-DOC]. Mature audit tools [VERIFIED-DOC] | **Worst record for Solana** (web3.js backdoor Dec 2024; chalk/debug Sep 2025) [VERIFIED-SEARCH via SEC R1]. **Best controls** (pnpm `minimumReleaseAge` etc.) [VERIFIED-DOC; VERIFIED-LOCAL] | Look-alike Pump packages [VERIFIED-DOC]. uv `exclude-newer = "7 days"` and wheels-only `no-build` [VERIFIED-LOCAL; VERIFIED-DOC] | Checksum DB, minimal versions [UNVERIFIED]; no release-age setting [UNVERIFIED] |
| **Ease for future AI sessions** | Compiler and exhaustive `match` catch AI mistakes; explicit integers. Slower compiles [UNVERIFIED] | Fluent. **Trap:** `number` loses precision above 2^53; `u64`/`i128` in the IDL [DERIVED] | Most fluent. Dynamic types hide byte-layout bugs | Simple; more hand-written Solana code |
| **Testability with fixtures** | `cargo test`, golden files, `proptest` | `node:test` [VERIFIED-LOCAL] | `pytest` | `go test` |
| **$ / month** | $0; likely fits the ~$48 server [UNVERIFIED; TS-T1] | $0; may need more cores [UNVERIFIED] | $0; same risk as Node live | $0 |
| **$ / trade** | $0 | $0 | $0 | $0 |
| **Build difficulty** | Medium-high | Medium-low | Low for research, high for a live recorder | Medium-high |

### Whole-project splits compared

| Option | Speed | $/month | $/trade | Reliability | Build difficulty | Verdict |
|---|---|---|---|---|---|---|
| **S1. Rust core + Python research (TypeScript only as a test referee)** | Most headroom | $0 | $0 | **Highest:** one implementation of the money maths and of the verdicts; static binaries | Medium-high | **Chosen** (red-team agreed) |
| S2. TypeScript core + Python research | Good | $0, maybe a bigger server | $0 | Medium | Medium | **Fallback for the recorder process only**, under §9d |
| S3. All TypeScript | As S2 | $0 | $0 | Medium | Low-medium, weak statistics | Rejected |
| S4. All Python | Weakest live | Maybe a bigger server | $0 | Low-medium | High for the recorder | Rejected |
| S5. Go core + Python research | Good | $0 | $0 | Immature Solana libraries | Medium-high | Rejected. Not needed for the seller either (TS-7) |

---

## 3. Why this split
1. **Priority 1 (no losses to bugs or bad data) decides it.** The two-witness check and T6 demand maths "to the last unit" on `u64` and `i128` [VERIFIED-DOC IDL]. Rust makes those types explicit and refuses to wrap on overflow.
2. **The recorder must never fall behind**, and history can't be rebuilt honestly later (rulings §7). Yellowstone servers cut off slow clients [VERIFIED-DOC grpc.rs], so the write path is built around that fact (§5a).
3. **Our design keeps Pump's SDK out of the money path** (DESIGN decision 4; SEC-5), so TypeScript's one big advantage matters only in tests.
4. **Research needs Python's tools**, but Python never needs a Solana library or the fee maths. Decoding happens in Rust, and Python reads typed Parquet.
5. **The money code and the verdicts are each in one place.** The guard reuses the T6-validated `fees` and `decoders` crates. `desk-score` is the single judge of every ticket. The safe-mode seller deliberately uses a different method (§5j).

---

## 4. Attacks I expected, with red-team's ruling and the v1.1 answer
1. **"Rust will slow you down."** Red-team accepted the fallback. Trigger: if the Rust recorder can't record 24 h with no unexplained gap by the end of Phase 1 week 1, swap **only the recorder process** to the TypeScript napi client. The raw tape format is language-neutral, so nothing else changes. **v1.1:** the fallback runs only under §9d (TS-10).
2. **"Two languages means two fee models."** **v1.1:** the primary control is now TS-1.6. Python never computes `net_i` or any fill. It reads nets written by `desk-sim` and checks the run's output hash. The CI text scan for fee constants stays as a secondary check.
3. **"Rust's Solana dependency trees are huge."** Accepted as answered. `cargo-deny` bans `solana-client`, `solana-sdk`, Anchor and `carbon-*`.
4. **"The Yellowstone client changes major version every ~10 days."** **v1.1:** production no longer depends on the client crate (own stubs from the pinned proto), and there is a written fast lane (§9b, TS-4).
5. **"The referee pulls npm and native binaries onto your machine."** **v1.1:** a throwaway container with the network off after install, no secrets, and only vector files as output (§9a).
6. **"Same language for guard and seller means shared bugs."** Red-team: Rust is fine, and spec diversity matters more. **v1.1:** §5j (TS-7).
7. **"Parquet has no 128-bit integer."** Accepted (`Decimal128(38,0)`, STK-2).
8. **"Research jobs will starve the recorder."** Red-team: CPU and memory limits don't cover disk. **v1.1:** separate volumes, hard input/output caps and a sync-latency alarm (§6b, TS-11), plus group commit (§5a, TS-2).

---

## 5. Component by component

### 5a. Recorder (`crates/recorder`)
- **One process per provider stream.** It does almost nothing: receive, timestamp, frame, append, group-commit and answer the server's ping (every 15 s [VERIFIED-DOC README]). It does **not** decode, so a decoder crash can never stop recording.
- **Subscription:** transactions for Pump, PumpSwap and the fee program with `failed: true` and `vote: false`, plus slot updates with `interslot_updates: true`. The tape then shows when each slot was completed, processed, confirmed or **dead**. The fork rule (§5b F3) and PR-15.7's "slot is complete" timing both need this [VERIFIED-DOC geyser.proto].
- **Control frames:** `CONNECT` (endpoint, client version and the exact subscribe request), `DISCONNECT` (the server's status text, e.g. "lagged to send an update"), `PING`/`PONG`, `CHECKPOINT`, `GAP`, `CLOCK`, `REPLAY_INFO` (`first_available`).
- **Write path (TS-2).** Three parts that never wait on each other:
  1. **Network task** (async): reads each `SubscribeUpdate`, stamps `recv_wall_ns` and `recv_mono_ns`, and pushes the bytes into a **bounded in-memory queue** (256 MB by default, sized by bytes). It never touches the disk.
  2. **Writer thread:** drains the queue continuously and appends whole frames to the open segment with `write()`, into the kernel's page cache.
  3. **Syncer thread:** calls `fdatasync` when the oldest unsynced frame is **50 ms** old or **1 MB** is unsynced, whichever comes first. It notes the file offset first, so when the sync returns, every frame up to that offset is durable. It then publishes `durable_seq` and `durable_slot`, the highest slot whose frames are all durable. A `CHECKPOINT` frame records them every second. At hourly (or 1 GB) rotation, the old file and its directory are `fsync`ed. Writes continue while a sync runs [UNVERIFIED per filesystem; TS-T1 measures it].
- **Crash-loss bound (stated, then tested in §8):**

  | Event | What can be lost | Recovered by |
  |---|---|---|
  | Recorder process crashes or is killed | Only frames still in the memory queue: normally < 1 ms of stream. The `RECORDER_QUEUE` alarm fires above 100 ms' worth | `from_slot` replay (below) |
  | Host crash, kernel panic or power loss | Frames not yet synced: ≤ 50 ms or ≤ 1 MB, **plus the duration of the sync in flight** (normally a few ms on network block storage [UNVERIFIED; TS-T1]). The last frame may be torn; recovery truncates it | `from_slot` replay; otherwise RPC backfill |
  | The disk stalls | Nothing, while the queue has room: 256 MB covers about 17–50 s at 5–15 MB/s [DERIVED from UNVERIFIED rates; C01] | — |
  | The queue fills (disk stalled for longer) | New frames are **dropped and counted**, never waited for, and a `GAP` frame records the first and last dropped `seq` and slots. Blocking instead would make the server disconnect us anyway [VERIFIED-DOC grpc.rs] and lose more | Backfill from Helius `getBlock`; the day turns red |
  | The volume loses acknowledged writes | Outside our bound (the provider's guarantee) | Archive + backfill |

- **Restart:** scan the open segment and truncate after the last valid CRC. Ask `SubscribeReplayInfo` for `first_available`. If `durable_slot − 2 ≥ first_available`, reconnect with `from_slot = durable_slot − 2`. The 2-slot overlap is deduplicated in `tabulate` on (slot, signature, update type). Otherwise, write a `GAP` and queue an RPC backfill (rows from the backfill are tagged `source = backfill`). With the code-default replay window of 150 slots (about 1 minute) [VERIFIED-DOC config.rs], a crash-and-restart under a minute loses **nothing**, provided Chainstack keeps such a window [UNVERIFIED; C04].
- **Recorder alarms:** `RECORDER_QUEUE` (warn at 10% full, class A at 50%); `FSYNC_SLOW` (warn when the p99 `fdatasync` time over 1 min exceeds 20 ms; alarm above 50 ms); `SERVER_LAG_DISCONNECT` (any disconnect whose status text says "lagged"); `DURABILITY_LAG` (durable time minus receive time over 1 slot at p99 over 1 min).
- **Live readers never slow the recorder.** The live forensics and paper engine read a local, read-only, *lossy* fan-out (a Unix socket). A slow reader is disconnected and never waited for. Replays read the tape. So the 50 ms durability window adds no decision delay.
- **Clock (TS-12):** chrony runs on every host. A `CLOCK` frame every 60 s records chrony's measured offset, root delay and dispersion, and sync status. Within one connection, frames are ordered by `recv_mono_ns` (and `seq`). A `CONNECT` frame records a wall/monotonic pair, so monotonic times convert to wall time consistently. Across connections and providers, frames are ordered by wall time corrected by the recorded offset, with ties broken by (slot, index in block). `CLOCK_DRIFT` alarm if |offset| > 2 ms or chrony is unsynchronised for more than 5 minutes [thresholds UNVERIFIED; tuned in Phase 1].
- **Guard-feed shadow recorder (seam PR-13):** from day 1 of Phase 1, a second small recorder subscribes on the guard's data company (Helius) to the test pools, in the same tape format with its own source byte. Simulated exits can then decide on the guard feed's real receive times. Until the guard host exists, this measures the bot host's view of that feed.
- **Its own volume** (§6b), with the 70/85/95% alarms (DAT-8).

### 5b. Decoders (`crates/idlgen` → `crates/decoders`)
- **Input:** the pinned `pump.json`, `pump_amm.json` and `pump_fees.json`, with their SHA-256 and source commit.
- **Generator output** (Rust, committed, marked "GENERATED, do not edit", regenerated in CI, which fails on any difference): account structs with exact-length decoding plus an **allowed-lengths table per version** (missing trailing fields read as 0, per NEW-8); event structs; instruction-argument structs.
- **Dispatch always keys on the program first**, then the discriminator (`buy_v2` collides [VERIFIED-DOC]).
- **Events are read from inner instructions**, never only from logs (logs get cut off). An event call starts with the tag `e4 45 a5 2e 51 cb 9a 1d` [DERIVED; A04 confirms], then sha256("event:<Name>")[..8] [VERIFIED-DOC, computed locally].
- Any unknown discriminator from a watched program raises `UNKNOWN_EVENT`, stores the raw bytes and pauses new buys. It is never skipped.
- **Failed, forged and forked events (TS-6).** These rules hold in every consumer: `tabulate`, forensics, the simulator, the paper bot and, in Phase 3, the guard.
  - **F1, failed transactions.** If `meta.err` is set, every event and instruction in that transaction is decoded (research uses the losers' tape) but emitted **only** into the `failed_txs` and `failed_tx_events` tables, tagged `FAILED_TX_EVENT`. Such an event never touches trades, prices, reserves, reserve continuity, holdings, migrations, the insider ledger, labels, dossiers or the two-witness check. This is enforced by types: the decoder returns `Applied(Vec<StateEvent>)` or `FailedOnly(Vec<FailedEvent>)`, and only `StateEvent` has a path into state code. A failed-transaction event fed into state therefore doesn't compile. Why it matters: Agave keeps the inner instructions of failed transactions at execution [VERIFIED-DOC agave], so a real CPI buy inside a deliberately failed transaction can leave a perfect `BuyEvent` with no trade behind it.
  - **F2, provenance.** An event counts only if: (a) it is an inner instruction of the emitting program; (b) its parent is an instruction of the **same** program, one stack level up; and (c) its first account is that program's `event_authority` PDA (seed `"__event_authority"` [VERIFIED-DOC IDLs]). Anything else raises `EVENT_PROVENANCE`, stores the raw bytes and pauses new buys. In a *successful* transaction a forged self-call should be impossible, because the program checks its own PDA's signature [UNVERIFIED for Pump's exact check; the hostile fixture covers it either way]. The rule is cheap insurance.
  - **F3, forks.** Rows decoded at processed commitment carry `commitment_seen`. When the slot is reported `SLOT_DEAD`, or never confirms, its rows are tagged `FORKED`. They stay in the replay at the time we saw them, but are excluded from outcome prices and from state, as preregistration §2.4.5 says. Live state built at processed keeps per-slot changes for the last 32 slots so a dead slot can be rolled back [UNVERIFIED depth; C03 measures how far back forks go].
  - **F4, missing inner instructions.** If `inner_instructions_none` is true or the field is absent [VERIFIED-DOC solana-storage.proto], the transaction raises `NO_INNER_IX`. That means "can't see events", never "no trades", and the slot's coverage is marked incomplete.
- **Hand-written layer:** the two-witness check (successful transactions only), reserve continuity, and the dormant-field monitor (DAT-1).
- **Why our own generator, not Codama or Anchor's macros:** we need exact-length, version and failed-transaction rules that those tools don't provide. Codama's event support is unconfirmed [UNVERIFIED]. Anchor's macros drag in the whole Anchor and Solana 2.x crate tree [VERIFIED-DOC index]. A Codama-rendered Rust client and the Phase 0 Python decoder (§5k) may be used as **test-only cross-checks**.

### 5c. Fees and pool maths (`crates/fees`)
- Integer-only (`u64`/`u128`/`i128`), checked arithmetic: an overflow is an error, never a wrap. Implements `docs/fee-model.md` §3 exactly.
- Validated by T6 (test-plan A09) and the SDK referee vectors. Property tests check, for example, that output never exceeds the reserves and that fees never go negative. **The T6 verdict comes from this crate**, not from any other implementation (§5k).

### 5d. Forensics and coin state (`crates/forensics`)
- Built from the stream (successful, non-forked transactions only, §5b): dossiers, the insider ledger with plain-transfer following, the holder map, theme waves.
- In-memory state with periodic SQLite snapshots for fast restart.
- Funding lookups are queued RPC calls, never in the decision path. Each result records `known_at` and its provider. **Seam CO-5:** if the queue is paused (for example in recorder-only mode), the paused interval is written to the `gaps` table as `lookup_paused`, so later I2 tests know which days lack `known_at` data.

### 5e. Monitors (`crates/monitors`)
- **Slot-lag check:** Helius `slotSubscribe` vs the Chainstack slot stream, plus a heartbeat.
- **Independent silent-feed probe (TS-3).** Once a minute, `getSignaturesForAddress` (confirmed, limit 1,000) runs for the PumpSwap and Pump programs **on Helius, not on our stream**. For the slots the reply fully covers, the signature set (failed ones included) is compared with our tape's set. A signature still missing after 60 s counts as `SILENT_FEED_MISS`. More than 0.5% missed over 5 minutes turns the day amber. Any missed migration-class transaction is class A. This is a sample of the latest slots each minute, not a full census. That is why it is paired with the daily audit below. Credits: about 86,000 calls a month [DERIVED]; the credit price per call is [UNVERIFIED; TS-T3, CO-7a].
- **Independent migration audit (PR-1)**, daily, also from Helius: new PumpSwap-owned accounts with the `Pool` discriminator, and bonding curves that turned `complete`, reconciled against U0. Misses are classified as PR-1 asks. Comparing only against our own decoder is never enough (TS-3).
- **Admin, program and IDL watch:** a byte-level diff of Pump `Global`, PumpSwap `GlobalConfig`, both FeeConfigs, the incentive accounts and the three ProgramData accounts (FM-6). Plus an **IDL second witness (TS-5):** hourly, the GitHub IDL hash *and* the on-chain IDL account(s) (Anchor legacy account and Program Metadata canonical `idl` account, whichever exist [VERIFIED-DOC derivations, §1]) are decompressed, canonicalised (sorted keys) and hashed. Any change raises `IDL_CHANGE`; a GitHub/on-chain disagreement raises `IDL_WITNESS_MISMATCH`.
- **Replay window watch:** `SubscribeReplayInfo` every 10 minutes. An alarm fires if fewer than 100 slots can be replayed, because the crash-loss bound in §5a depends on it.
- **The Helius credit meter** (SQLite).
- JSON-RPC uses plain `reqwest` + `serde_json`, not `solana-client` [VERIFIED-DOC index].

### 5f. Strategy engine and paper simulator (`crates/strategy`, `crates/sim`)
- **One engine, two callers:** the `desk-sim` command-line tool replays the tape for backtests and pre-registered tests, and the Phase 3 paper bot runs the same engine live.
- Rules are data (TOML/JSON in the fixed rule language). One reason-coded log line per decision (DESIGN §2b.4).
- **Every `desk-sim` run writes a run folder** containing `run.json` and the outputs. `run.json` holds the hashes of the rule file, the tape-manifest range, the decoder, fees and sim versions, the seeds, and every output file. Its own SHA-256 is the run id. Per-trade `net_i` exists **only** in these outputs.
- On sealed days, `desk-sim` runs only as the `scorer` user and writes into the sealed store (§5l).

### 5g. Research and exploration (`research/`, Python)
- `polars` and `duckdb` over the **open** Parquet store; `numpy`/`scipy` for exploration.
- **Python never computes `net_i`, a fill or a fee (TS-1.6).** It reads nets only through `research/lib/nets.py`, which refuses a run folder whose `run.json` hash chain doesn't verify. The secondary check: CI fails if `research/` contains fee constants or basis-point arithmetic.
- **Python never produces a verdict.** It may explore and describe freely, but any number called a ticket metric, LB, pass or fail comes from `desk-score`.
- Each study is a script, not a notebook. It writes into `reports/daily/YYYY-MM-DD.md` only the open data and the scorer's allowed summaries (§5l).

### 5h. AI desk and rule-change reader (TS-8b)
- **Two jobs, two Unix users, two keys.** The `changereader` user (safety-relevant: it runs when the IDL or admin monitors fire) and the `desk` user (optional research) each get **their own Anthropic key in their own Console workspace, with their own spend limit**. The change reader's limit is small and is never shared, so the desk or the labels can't use it up (CO-3). Paul creates the keys and limits with click-by-click steps. They are delivered by `LoadCredentialEncrypted=` [VERIFIED-DOC systemd], never in an environment variable, a repo or a log.
- **Zero third-party Python packages in either environment.** Both use the same small stdlib-only client (`urllib`, `json`, `ssl`; streaming for long requests; retries on 429/529). It is reviewed like guard code. The official SDK would bring 8 required packages and their own dependency trees into a key-holding environment [VERIFIED-DOC PyPI] (comparison below).
- The desk reads its R-half pack as JSON Lines (no pyarrow needed), which the scorer side exports under the sealing policy (§5l). It writes rule files into a drop folder. `desk-sim validate` checks them before shadow testing. A refusal or timeout means "no decision" (brief).
- Label calls (if any) run with thinking off or at the lowest effort, under the desk key's limit (CO-3).

| Option for the key-holding AI jobs | Supply-chain surface | Speed | $/month | Reliability | Build difficulty | Verdict |
|---|---|---|---|---|---|---|
| **Stdlib-only client, own users and keys** | Python standard library only | Same API | $0 | We own retries and streaming (small, testable) | Low (~150 lines + tests) | **Chosen** |
| Official `anthropic` SDK in its own venv, wheels-only | `anthropic` + 8 required packages and their trees [VERIFIED-DOC] | Same | $0 | Mature retries and streaming | Lowest | Fallback, only if the stdlib client proves inadequate, with red-team sign-off |
| Inside the research venv (v1.0) | polars, duckdb, scipy… next to the key | Same | $0 | — | Lowest | **Rejected** (TS-8b) |

### 5i. Dashboard (Phase 3)
- Rust `axum`, server-rendered, no npm build. It reads only open data and the scorer's allowed summaries. Decided in Phase 3.

### 5j. Guard, signer, safe-mode seller (Phase 3; provisional)
- **A separate Cargo workspace** with its own lockfile, vendored dependencies and every vendored diff line reviewed. Built only in the secret-free builder (§9c).
- **The guard** reuses `decoders` + `fees` (T6-validated) and builds every transaction itself from the pinned IDL. It honours F1–F4 (§5b) and checks `Q_real ≥ q_out − lp` before sending (FM-2). Signing is through AWS KMS [VERIFIED-SEARCH via SEC-R]; AWS SDK versions are UNVERIFIED until Phase 3.
- **The safe-mode seller uses a different method (TS-7):**
  1. **Min-out** = constant-product output on the pool's effective reserves × (1 − a **fixed fee ceiling**, e.g. 3% per side, or the maximum row of the live FeeConfig, whichever is higher) × (1 − margin), capped by the real payout reserve `Q_real`. **It never uses tier logic.** If `Q_real` can't pay, it raises a class-A alarm instead of paying for a certain 6063 failure (FM-2).
  2. **The differential test** is an inequality: seller min-out ≤ guard min-out ≤ what the chain actually paid out (from T6 data), on every golden vector. It is no longer "byte-identical, within 1 lamport", so a shared spec error can't hide in agreement.
  3. **Pool state comes from a different provider than the guard's.**
  4. **Blocking input/output, minimal dependencies:** no `tokio`, a blocking HTTP client, and where practical a **different TLS library** from the guard's rustls (for example the OS's OpenSSL, allowed by `deny.toml` in this crate only) [UNVERIFIED crate options; Phase 3].
  5. It shares no code with the guard except the pinned IDL JSON and the golden vectors. It never closes token accounts inside a sell (FM-1).
- **Language:** Rust, as red-team ruled. Go is not required.

### 5k. Phase 0 scripts (`phase0/scripts/`)
- **Network fetchers:** Python **standard library only**. Read-only, rate-limited, never print keys, save raw responses with provenance. They need no install step, so TS-8a's "no builds next to secrets" holds automatically. Run with `python3 -I`.
- **Updated in v1.1 to match what is being built:** the scripts include a small IDL-driven Python decoder (`p0/borsh.py`, `p0/pump.py`, `p0/txparse.py`). That is allowed for Phase 0 fact checks (layouts, discriminators, counts, shapes). It becomes the **independent second decoder** in Phase 1: the Rust decoders must agree with it on every Phase 0 fixture (a free differential test). It never feeds production or the tape tables.
- **The Python decoder must honour §5b F1–F4.** It tags failed-transaction events and excludes them from every trade, price, reserve, migration or T6 sample, and it checks event provenance (changes listed in the v1.1 hand-off).
- **The fee-maths verdict (T6 / A09) comes from the Rust `fees` crate** (§5c), built offline in Phase 0 over the saved fixtures. A Python fee calculation, if any exists, is a referee only.
- **Timing rows** (A12, A13 and similar) use `time.monotonic_ns()` for intervals and record the host's clock-sync status in provenance (TS-12).
- **Websocket and gRPC probes** (A12, A13, A23, tier C) are Rust programs in `crates/feed/examples/`, so they become the recorder's own connection code. The C01 probe also records queue depth and `fdatasync` latency (TS-T1).

### 5l. Scoring and sealed holdouts (`crates/score`, new in v1.1; TS-1)
**Goal:** no person, AI session or stray script can see a sealed holdout's outcomes before its scheduled look without leaving evidence, and nobody can prove a registration "happened earlier" than it did.

1. **One frozen scorer.** `desk-score` computes every ticket verdict: the day-block percentile bootstrap, the m-out-of-n LB, the cluster-t LB (PR-9), the placebo and B-RAND percentiles, the permutation tests for F5, and the pass/kill logic.
   - It reads only `desk-sim` run folders whose hashes verify.
   - Randomness comes from ChaCha20 seeded as the preregistration says. Index sampling is our own documented rejection sampling over the raw stream, so results don't depend on any crate's internal sampling.
   - Summation is in a fixed order, so the same binary on the same inputs gives bit-identical output.
   - **Frozen:** its source-tree SHA-256 and binary SHA-256 are registered (step 4) before the first holdout day begins. Changing it later is a preregistration amendment: class (b) if its output on the known-answer suite *and on every past look* is unchanged, otherwise class (c).
   - **Tested:** known-answer fixtures whose expected numbers come from scipy (test-only, offline). `desk-score simulate-null` must reproduce PR-9's false-pass table within Monte-Carlo error.
2. **Physical sealing.** `sealed.json` (part of the registration) lists, for every registered ticket, its holdout days, its look schedule and its export rules.
   - `tabulate` writes each day's decoded partitions either into `store/open/` (readable by the `research` group) or into `store/sealed/` (mode 0700, owner `scorer`).
   - Raw tape is never readable by research on any day. Re-decoding is done by `tabulate`, which respects the same split.
   - **Default policy until preregistration v1.1 says otherwise:** a day that is a holdout for *any* live ticket is sealed from *all* research until that ticket's final look is logged. The preregistration owns the policy; this stack enforces whatever `sealed.json` says.
3. **Outcome blinding for live processes.** Anything that produces per-trade outcomes on a sealed day writes them only to `store/sealed/`. That covers `desk-sim`, B-NULL, the paper twin, the paper bot and shadow rules. Dashboards and Paul's daily summary read only `store/open/` plus a `summaries/allowed/` file that the scorer writes: data health, counts and whatever preregistration §2.4.7 v1.1 allows. Exports such as the AI desk's R-half pack follow the export rules in `sealed.json`, and each export is logged like a read.
4. **An append-only, hash-chained ledger** (`ledger/registrations.jsonl`, `ledger/access.jsonl`). Each entry holds: the ticket or look id; the full ticket text's SHA-256; the days touched; scheduled or `UNSCHEDULED`; the input and output hashes; the previous entry's SHA-256; and a **chain anchor**, meaning the latest (slot, blockhash) the recorder saw. That anchor proves the entry is *not older* than that slot, and nobody can fake Solana's slot clock.
   - Every registered ticket spends α at registration, even if it is never run. So there are no hidden pre-registrations to reveal selectively later.
   - Only `desk-score` writes the ledger and reads `store/sealed/`. An OS audit rule (`auditd` watch on `store/sealed/`, reads by any user including root) is the second, independent log [UNVERIFIED availability on the rented host; TS-T6].
   - An `UNSCHEDULED` read of a ticket's holdout voids that ticket and spends its α (prereg §15.7).
5. **Proof that an entry is *not newer* than claimed (no git dates).** At least two outside anchors:
   - (a) every hour the ledger head hash goes into the tape manifest, which goes to the **write-once archive** (§6c). The storage provider's upload record and object lock are outside our control, and the hourly manifests chain to one another;
   - (b) the ledger head hash goes into **Paul's daily summary** as delivered to him (the alert app or email server records when it arrived);
   - (c) the **push to GitHub** (GitHub's server-side record, never the commit date; supplementary, because GitHub may not keep push records forever [UNVERIFIED]);
   - (d) once allowed, an **RFC 3161 timestamp token** (`openssl ts`, already installed [VERIFIED-LOCAL; VERIFIED-SEARCH docs.openssl.org]) from a public timestamp authority, and/or OpenTimestamps (TS-T4).

   A local git commit date is never evidence.
6. **Fresh days only, enforced (PR-3.1).** For reserve and new-version tickets, `desk-score register` finds the first archived manifest that contains the registration's hash. Every holdout day must start at a slot **after** that manifest's last slot, plus one full green day as margin. Otherwise registration is refused.
7. **Look scheduling.** `desk-score` refuses to compute a verdict before the slot at which the ticket's last holdout day ends, and refuses a second verdict on the same ticket version.
8. **Who can do what.** No AI session gets root or `sudo` on the bot host during research. Deploys use a separate `ops` account whose every command is logged. Research may also happen in cloud sessions, which only ever receive copies of `store/open/`.
9. **Honest limits.** Sealing stops *our own pipeline* from leaking. It can't stop someone looking at public charts (DEX Screener) for a sealed day. The ledger and the fresh-day rule are the defence there: a ticket shaped by peeking would still have to pass on days that hadn't happened yet when it was anchored. Root on the host can bypass the permission, but not the audit log or the outside anchors without leaving traces.
10. **Seam with preregistration v1.1 and the Gate 0→1 simulations.** The PR-2 and PR-9 offline simulations are due before Gate 0→1, and `desk-score` may not exist yet. If they are first run with a Python prototype, `desk-score simulate-null` must reproduce the same tables (same seeds, within Monte-Carlo error) before the scorer's hash is registered. The preregistration must name `desk-score` as the only verdict program and carry its hashes.

---

## 6. Storage for the recorded tape

### 6a. Options compared

| Option | Survives a crash mid-write | Research query speed | Disk use | Running burden | Keeps exact bytes for re-decoding | Cost | Verdict |
|---|---|---|---|---|---|---|---|
| **A. Raw framed segments (zstd, group-committed) + hourly Parquet (open/sealed) + DuckDB/Polars + a small SQLite index** | Yes: group commit with a stated loss bound (§5a), a CRC per frame, the torn tail cut on restart | Fast columnar scans [UNVERIFIED size; STK-2] | Smallest [UNVERIFIED ratio; C01] | None: just files | **Yes** | $0 + disk | **Chosen** |
| B. SQLite (WAL) for the whole tape | Yes | Slow for 100M+ row scans [UNVERIFIED] | Larger | Low | Only with a blob column | $0 | **Small operational state only** |
| C. ClickHouse server | Yes | Fastest at scale | Very good | A server to run and secure | Possible | $0 software, bigger server | Rejected for now (revisit above ~2 TB). Helius left ClickHouse for slow signature lookups [VERIFIED-SEARCH helius.dev blog] |
| D. PostgreSQL / TimescaleDB | Yes | Medium [UNVERIFIED] | Medium | A server | Possible | $0 | Rejected |
| E. Parquet only (no raw bytes) | Weak | Fast | Smallest | None | **No** (DESIGN risk 10) | $0 | Rejected |
| F. Kafka / Redpanda | Yes | Needs a sink | Medium | Heavy | Yes | $0, bigger server | Rejected |

### 6b. The chosen layout
**Layer 0, the raw tape (immutable):**
- Path: `tape/raw/<provider>-<stream>/<YYYY-MM-DD>/<HH>.seg`. It is written uncompressed while open. At rotation, the separate low-priority `segment-closer` process compresses it to `.seg.zst.tmp`, verifies it by decompressing and comparing the SHA-256, `fsync`s it, renames it, `fsync`s the directory, and only then deletes the `.seg`. The SHA-256 and slot range go into `manifest.jsonl`, together with the ledger head hash (§5l.5). Compression is never on the recorder's hot path.
- **Frame layout** (little-endian): magic `TAPE`, version, source, flags, reserved; `recv_wall_ns` u64, `recv_mono_ns` u64, `conn_id` u32, `seq` u64, `payload_len` u32; payload (the protobuf `SubscribeUpdate` bytes **exactly as received**, which also keeps fields our stubs don't know yet, or the raw JSON of an RPC response); `crc32c` u32 (our own implementation, checked against the RFC 3720 test vectors).
- **Control frame types:** see §5a.
- **Recovery:** truncate after the last valid CRC, then `from_slot` replay (§5a).
- A per-segment SQLite index (`signature → segment, offset`) gives single-transaction lookups.

**Layer 1, decoded tables** (Parquet, zstd, one file per table per hour, written by `tabulate` from closed segments into `store/open/` or `store/sealed/` per `sealed.json`):
- Tables: `slots` (with status history incl. dead), `txs` (incl. failed, position in block, fee, compute used, priority fee, tips, lookup tables, receive times, `commitment_seen`, `forked`), `curve_trades`, `pool_trades`, `migrations`, `boost`, `creates`, `token_balance_changes`, `account_updates`, `admin_changes`, `witness_checks`, `unknowns`, **`failed_tx_events`** (TS-6), **`gaps`** (stream gaps, backfills, queue drops, paused lookups; seam PR-16: trades overlapping a gap are dropped from rule and baselines alike).
- **Column rules:** `u64` → UInt64; `i128` → Decimal128(38, 0) plus a range alarm; public keys → FixedSizeBinary(32); times as UTC nanoseconds; every row carries **regime tags** (program deploy slot, IDL SHA-256, decoder version).
- **Re-decoding never overwrites:** it writes `…/decoded/v<decoder_version>/…`, side by side.
- **Partitioning:** `<store>/<table>/date=YYYY-MM-DD/hour=HH/`.

**Volumes and input/output isolation (TS-11):**
- **Volume R:** open raw segments only. The recorder writes; only `segment-closer` reads closed files. Research never touches it. It is the lowest-latency disk the server offers [UNVERIFIED which; TS-T1].
- **Volume D:** closed segments, Parquet (open and sealed), SQLite, research scratch space.
- systemd limits: research and `segment-closer` get hard caps `IOReadBandwidthMax=` / `IOWriteBandwidthMax=` on both volumes (enforced by `io.max` on every device [VERIFIED-DOC kernel]), plus `IOWeight=10`. The recorder gets `IOWeight=1000`. Weights work only with iocost or BFQ [VERIFIED-DOC kernel], so the caps are the real protection. CPU and memory limits stay as in v1.0. The `FSYNC_SLOW` alarm (§5a) catches anything the caps miss.

**Unix users, secrets and network (TS-8a, TS-1):**

| User | Runs | The only secret it can read | Network it may reach (per-user firewall rule) | Reads | Writes |
|---|---|---|---|---|---|
| `recorder` | recorder (one per stream) | that stream's token | that stream's host | — | Volume R |
| `tabulate` | segment-closer, tabulate | none | none | Volume R (closed files) | store/open, store/sealed (write-only drop) |
| `scorer` | desk-score; desk-sim on sealed days | none | none | store/sealed, store/open, ledger | ledger, verdicts, summaries/allowed |
| `monitors` | monitors, backfill, audits | Helius key | Helius hosts, `raw.githubusercontent.com`, alert app | health tables | alarms DB |
| `research` | Python research; desk-sim on open days | **none** | none at run time | store/open | research outputs |
| `changereader` | IDL change reader | Anthropic key A (small, dedicated limit) | `api.anthropic.com` | IDL diffs | alerts |
| `desk` | AI desk | Anthropic key B (own limit) | `api.anthropic.com` | desk packs | rule drop folder |
| `ops` | installs hash-checked binaries | none kept on the host | GitHub release download | — | `/opt/desk/<version>/` (root-owned, read-only) |

Secrets are delivered by `LoadCredentialEncrypted=` [VERIFIED-DOC systemd]. The per-user network rules use nftables `meta skuid` [UNVERIFIED on the rented host; TS-T6]. Phase 3 adds a `paperbot` user that writes outcomes to `store/sealed/` on sealed days.

**Retention:** recent days stay local (the number of days is set from C01's MB per hour). Expected volume is 15–135 GB a month raw [UNVERIFIED; red-team CO-7e thinks 2–3× higher; C01/CO-T2 settles it before the disk is bought].

### 6c. Archive (TS-9)
- **The bot host holds put-only credentials.** They can upload new objects but can't delete, overwrite or shorten retention. On Backblaze B2, for example, `writeFiles` without `deleteFiles` [VERIFIED-SEARCH backblaze.com capability docs]. B2's `writeFiles` may still "hide" a file by name, which is why versioning is required [VERIFIED-SEARCH].
- **Provider-side versioning plus object lock** (compliance mode where offered, retention ≥ 400 days). A hide or delete marker then never destroys data [UNVERIFIED per provider; PX-7 picks the provider, TS-T5 tests it].
- **Delete rights exist only in Paul's own provider login**, which has a hardware key, never on any server.
- Uploads carry a SHA-256 checksum. The local copy is deleted only after the provider confirms it (DAT-8).
- **Daily list-check:** a list-only key compares the archive with `manifest.jsonl` and alarms on any missing or changed object.
- **Monthly restore drill:** on a machine other than the bot host, with a read-only key, download 3 random closed segments and 1 Parquet hour. Verify SHA-256 against the manifest, decompress, re-decode and compare with the replay fixture's hashes. The result goes into Paul's daily summary.

---

## 7. Project layout
```
aiteam-bot/
  rust-toolchain.toml          exact Rust version (1.97.0 today)
  Cargo.toml, Cargo.lock       bot-host workspace; lockfile committed
  .cargo/config.toml           cooldown (from Rust 1.100), no git sources
  deny.toml                    cargo-deny: bans, licences, sources, build-script allowlist
  Makefile                     `make test` = every offline test
  SHA256SUMS                   release binaries' hashes (committed through review; §9c)
  sealed.json                  holdout days, look schedule, export rules (part of each registration)
  ledger/                      registrations.jsonl, access.jsonl (append-only, hash-chained; copies archived)
  crates/
    pump-idl/                  pinned IDL JSON + SHA-256 + source commit (data only)
    idlgen/                    IDL JSON -> Rust decoders (build-time tool, builder only)
    decoders/                  generated code + version tables + F1-F4 + two-witness
    fees/                      fee + pool maths (integer, checked)
    tape/                      frame reader/writer, CRC32C, Parquet schemas
    feed/                      proto/ (vendored geyser.proto + generated stubs), Helius WSS + JSON-RPC; examples/ = Phase 0 probes
    recorder/  segment-closer/  tabulate/  monitors/  forensics/  strategy/  sim/
    score/                     desk-score: the only verdict program and sealed-store reader
  tools/protogen/              regenerates feed/proto stubs (builder only)
  guard-workspace/             Phase 3 only: separate workspace, own lockfile, vendor/  (guard/  safe-seller/)
  research/                    Python (pyproject.toml, uv.lock, no-build); one folder per study; lib/nets.py
  ai/                          stdlib-only Messages-API client; changereader/; desk/  (no third-party packages)
  tools/sdk-oracle/            TypeScript, test-only, run in a throwaway container
  tools/check_cooldown.py      stdlib-only CI check of crate publish ages (until Rust 1.100)
  fixtures/                    chain/ grpc/ idl/ golden/ hostile/ replay/ score/   (each file has provenance)
  ops/                         systemd units, per-user firewall rules, audit rules, deploy check
  phase0/                      test-plan.md, results.md, scripts/
  docs/  reports/daily/
```

---

## 8. Testing approach: fixtures, no network
**The rule:** `make test` passes with networking switched off. CI runs it in a container with no network. Python tests block sockets in `conftest.py`.

**Fixture kinds** (each file has a `provenance.json`: method, redacted parameters, provider, slot, UTC time fetched, SHA-256):
1. **Real chain data** (`fixtures/chain/`): at least one real transaction for every event and account type, for every curve-completing instruction (`buy`, `buy_v2`, `buy_v3`, `buy_exact_sol_in`, `buy_exact_quote_in_v2/v3`, a `multi_hop_swap` hop), `migrate`, `migrate_v2`, a synthetic migration, a failed 6004 buy, BOOST buy-and-burn, `create_v2` and legacy `create`. **v1.1 adds:** a real failed transaction whose inner instructions contain a Pump or PumpSwap event, if AR-T1 finds one.
2. **Raw gRPC frames** (`fixtures/grpc/`): one captured hour from C01, plus its `CONNECT`, `CHECKPOINT`, `CLOCK` and `GAP` control frames.
3. **Account snapshots**: old and new `Pool` lengths, `GlobalConfig`, `Global`, `BondingCurve`, FeeConfig; **v1.1:** the on-chain IDL account(s) from TS-T2.
4. **Golden vectors**: fee and quote inputs with expected outputs (T6 trades and the SDK referee).
5. **Hostile fixtures** (`fixtures/hostile/`), each of which must raise its named alarm or tag:
   - shifted, cut-short or over-long bytes, an unknown discriminator, extreme negative `i128`, `u64::MAX` → `DECODER_SHAPE`, `UNKNOWN_EVENT`, range;
   - **v1.1 (TS-6):**
     - `failed_tx_full_buyevent`: a failed transaction with a complete, valid `BuyEvent` self-call before the failing instruction → exactly one `failed_tx_events` row, **zero** `pool_trades` rows, no state, price or holding change, no two-witness run;
     - `event_wrong_authority`: a successful transaction with an event-shaped inner instruction under the wrong program, wrong parent or wrong first account → `EVENT_PROVENANCE`;
     - `forked_slot_trade`: a trade in a slot later reported `SLOT_DEAD` → `FORKED`, excluded from outcome prices and rolled back from live state;
     - `no_inner_ix`: `inner_instructions_none = true` → `NO_INNER_IX`, slot coverage incomplete.
6. **IDL-diff fixtures**: the real Sep 2025 change plus the 5 hostile diffs for RC8.
7. **Replay fixtures**: one hour of tape and the expected SHA-256 of every decoded Parquet file. Decoding must be byte-for-byte repeatable.
8. **Scorer fixtures** (`fixtures/score/`, v1.1): nets with known verdicts and scipy-computed expected LBs, plus the PR-9 null-simulation seeds and expected false-pass table.

**Kinds of test:** unit, golden, property (`proptest`), differential (our decoder vs the Codama/SDK referee **and the Phase 0 Python decoder**; Phase 3 seller ≤ guard ≤ chain), replay/repeatability, alarm, schema-evolution. **v1.1 adds:**
- **Recorder crash tests (TS-2):** replay the fixture hour at 10× speed and `kill -9` the recorder at 1,000 random points. After each restart: every frame up to the last `CHECKPOINT` is present, the tail truncates cleanly, and after deduplication the decoded Parquet hashes equal the replay fixture's. A power-cut test on a fault-injecting block device or a VM hard reset follows in Phase 1 [UNVERIFIED tooling].
- **Disk-stall test:** throttle the segment volume until the queue fills → `GAP` frame with exact bounds, no blocking of the network task, and the alarm fires.
- **Sealing tests (TS-1):** the `research` user reading `store/sealed/` gets "permission denied"; `desk-score` refuses an unscheduled look and logs the attempt; editing any ledger entry breaks the chain check; a registration whose holdout starts before its anchor is refused; `nets.py` refuses a run folder with a wrong hash.
- **Deploy test (TS-8a):** a binary whose SHA-256 differs from `SHA256SUMS` is refused by the deploy check.

Python tests use small Parquet fixtures. Statistical routines in research are tested with fixed seeds; verdict routines are tested in `desk-score` only.

**Until the network opens**, synthetic fixtures built from the IDL (labelled `synthetic`) cover decoder shape tests and the TS-6 hostile cases. Real fixtures replace them as soon as A03, A04, A09 and AR-T1 run.

---

## 9. Dependency pinning, builds and supply chain

### 9a. General rules (all ecosystems)
- Exact versions for direct dependencies (`=x.y.z` / `==x.y.z`; **no ranges**, TS-8c), lockfiles committed, installs only from the lockfile (`--locked`, `--frozen`, `--frozen-lockfile`).
- **A 7-day release-age cooldown** (SEC R1/R2). No git or URL dependencies. No unofficial "Pump" or "Solana bot" packages, ever.
- Every new dependency needs a one-line reason in `docs/dependencies.md` and a second reviewer. **Crates with build scripts or procedural macros are allowlisted by name** in `deny.toml`. v1.1 removed two (the proto crate's vendored `protoc`, the `crc32c` crate).
- **Honest limit:** `faster_log` was online for ~4 months [VERIFIED-SEARCH], so a cooldown alone wouldn't have caught it. The real defences are a short allowlist, review, audits, and the per-user isolation in §6b, which limits what a bad package could reach.
- **`cargo vet` (red-team §11.7):** the audit sources to import are chosen before Phase 3. Every guard-workspace crate must be "safe-to-deploy" by a named audit or by our own recorded review.

| Ecosystem | Where it runs | Controls |
|---|---|---|
| **Rust (Cargo)** | Built only in the secret-free builder (§9c); binaries run on the bot host and the guard | `Cargo.lock` + `--locked`. `cargo deny check` (crates.io only; bans `solana-client`, `solana-sdk`, `anchor-*`, `carbon-*`, `pump-rust-client` and `yellowstone-grpc-client` outside tests; OpenSSL banned except in `safe-seller` [proposal, §5j]); `cargo audit` daily; `cargo vet`; `cargo auditable`. **Cooldown:** `tools/check_cooldown.py` reads each locked crate's `pubtime` from `index.crates.io` [VERIFIED-DOC] until Rust 1.100 (2026-11-12 [VERIFIED-SEARCH]); then also `registry.global-min-publish-age = "7 days"` [name UNVERIFIED until release] |
| **Python (uv)** | Bot host, `research` user only (no secrets) | `[tool.uv] exclude-newer = "7 days"` [VERIFIED-LOCAL] and **`no-build = true`** (wheels only; no source package's build code runs at install [VERIFIED-DOC uv source]); `uv.lock` with hashes; `uv sync --frozen`; exact `==` pins (§0); `.python-version` 3.13. **Honest limit:** a wheel can still run code when imported, or at interpreter start through a `.pth` file [UNVERIFIED detail], so the `research` user holds no secrets and has no network at run time. The `desk` and `changereader` environments have **no** third-party packages at all (§5h) |
| **TypeScript (pnpm)** | `tools/sdk-oracle/` only, **in a throwaway container**: install with the network on, then the network off; no secrets; the only output is vector files (red-team §4.5) | `minimumReleaseAge: 10080`, `minimumReleaseAgeStrict: true`, `trustPolicy: no-downgrade`, `blockExoticSubdeps: true`, `strictDepBuilds: true` with no builds allowed [VERIFIED-DOC pnpm docs; cooldown VERIFIED-LOCAL]; `--frozen-lockfile`; `save-exact`. SEC-5's fast lane via `minimumReleaseAgeExclude` with one exact version |

**Toolchains are pinned:** `rust-toolchain.toml`, `.python-version`, and the Node LTS in `.nvmrc` and `packageManager`. Upgrades happen on a monthly "dependency day", one ecosystem at a time. The full offline suite plus the reconnect and replay tests must pass first.

### 9b. Fast lane for the stream client (TS-4)
- **Less exposure first:** production depends on our own stubs generated from the pinned `geyser.proto` (§0). Protobuf is forward-compatible: a server that *adds* fields doesn't break an old client, and the tape keeps the unknown fields anyway [UNVERIFIED general property; the replay test checks it on each update]. Only a breaking RPC change needs the lane.
- **Trigger:** `CONNECT` fails with a protocol or unimplemented error, or `tabulate` reports more than 0.1% unparseable frames in an hour, after a provider change.
- **Within 1 hour:** the day turns red. The Helius narrow streams keep migrations, test pools and the guard data alive (DESIGN decision 3), so we are degraded but not blind. If the fix will take more than 24 h, start the Solana Tracker trial recorder (DESIGN decision 2's switch), or the TS-10 fallback under §9d.
- **The lane (mirrors SEC-5):**
  1. update the vendored proto to an **exact upstream commit**, or the reference client to an **exact version**;
  2. review the full diff (proto plus regenerated code, or the crate diff);
  3. the replay test on the fixture hour, plus the reconnect test (C04) against the provider, both pass;
  4. **red-team sign-off within 24 h**;
  5. a cooldown exception scoped to that one crate and version, with an expiry date, recorded in `docs/dependencies.md`, and reviewed again on the next dependency day.
- Gaps during the lane are recorded in `gaps` and backfilled by RPC where possible.

### 9c. Builds and hosts (TS-8a)
- **No compiling, and no package installs that run code, on any host that holds a secret.** The bot host (provider keys, later tunnel credentials) and the guard host have **no Rust, Node or pnpm toolchain installed**. The deploy check fails if `cargo`, `rustc`, `node` or `pnpm` is on the path.
- **The builder is secret-free.** Primary: a GitHub Actions job with **no repository secrets**, `permissions: contents: read`, and actions pinned by commit SHA [UNVERIFIED cost; free minutes expected]. Second: a clean cloud session, used for the reproducibility comparison. Builds use `--locked`, `--remap-path-prefix`, a fixed `SOURCE_DATE_EPOCH` and `cargo auditable`.
- **Output:** binaries plus `SHA256SUMS`. The sums file is committed to the repo through a reviewed change. The `ops` user downloads the release, checks every hash against `SHA256SUMS` *at the deployed commit*, and installs into a root-owned, read-only `/opt/desk/<version>/`. A mismatch refuses the deploy.
- **Reproducibility check** (TS-T7, not a gate): the two builders' hashes should match. If they don't, we record why. It doesn't block a deploy, but it is flagged.
- **Honest limit:** hash-checking proves the binary is the one we built, not that every crate inside it is honest. A malicious crate would run with that one service's rights: one secret and one allowed host (§6b). `cargo vet`/`deny` and the build-script allowlist reduce that chance.

### 9d. TypeScript recorder fallback (TS-10)
Used only if §4.1's trigger fires. It runs as its own Unix user holding **only the stream token**, with the §9a pnpm settings. `node_modules` is installed in the secret-free builder and shipped as a hashed bundle, never installed on the host. The native add-on's SHA-256 is recorded. **Security and red-team review it before its first run.** It writes the same tape format, so nothing downstream changes.

---

## 10. Conventions that keep this easy for future AI sessions
- **Small crates**, each with a README that says what it does and how to test it offline. One command: `make test`.
- Generated code (decoders, proto stubs) is marked and regenerated in CI, never edited by hand.
- **Rust style:** no `unsafe`, `clippy` with warnings as errors, `rustfmt`, explicit error enums, no clever macros.
- **Units in every name:** `_lamports`, `_slots`, `_bps`, `_ns`. Every config value in TOML with its unit.
- **Python style:** type hints, `ruff` (pinned dev tool), one script per study, no notebooks.
- Every decision and alarm writes a reason code.
- **Never read `store/sealed/`, never compute a verdict in Python, never compute `net_i` outside `desk-sim`** (§5l, §5g).

---

## 11. Risks and open questions (for red-team's re-check)
1. Rust build speed for our team (fallback trigger §4.1, under §9d).
2. Stream-client churn: reduced by our own stubs; the fast lane is untested until the first real use (§9b).
3. Whether `fdatasync` on the rented server's block storage stays under the 20 ms warning at p99, and whether writes really continue during a sync [UNVERIFIED; TS-T1].
4. Chainstack's replay window size; the "usually nothing lost" claim depends on it [UNVERIFIED; C04, monitored in §5e].
5. Sealing depends on Unix permissions on one host. Root can bypass them; detection relies on the audit log and the outside anchors (§5l.9).
6. The scorer must exist and be registered before the first holdout day; the seam with the Gate 0→1 simulations is in §5l.10.
7. Per-user network rules, `auditd` and `LoadCredentialEncrypted=` on the rented host are [UNVERIFIED] until TS-T6.
8. The archive provider's put-only key and object-lock behaviour are [UNVERIFIED] until PX-7 and TS-T5.
9. The exact Rust 1.100 cooldown setting name [UNVERIFIED]; Codama's event support [UNVERIFIED]; `cargo vet` audit sources (before Phase 3).
10. The safe-mode seller's alternative TLS library choice (Phase 3, §5j).

---

## 12. Tests to run once allowed (stack-specific; also to be listed in `phase0/test-plan.md`)

| # | Test | Domain(s) | Pass mark (proposed; freeze in preregistration.md) |
|---|---|---|---|
| **AR-T1** (TS-6) | `getSignaturesForAddress` on the PumpSwap and Pump programs, keeping `err != null`, until there are 20 failed trades from each. Include failures *after* the Pump instruction (a later router slippage check, or a tip/assert instruction), not only 6004. `getTransaction(sig, {encoding: "json", maxSupportedTransactionVersion: 0})`. Record: does `meta.innerInstructions` contain event self-calls (prefix `e445a52e51cb9a1d`) from Pump or PumpSwap? At which instruction index did it fail, relative to the trade? Do `logMessages` show `Program data:` lines? Save each as a fixture. Repeat on 5 of them through the Chainstack stream (C01) | `mainnet.helius-rpc.com` or `api.mainnet-beta.solana.com`; Chainstack gRPC host | Measured, not pass/fail. **If events are present:** the real example replaces the synthetic hostile fixture. **If not:** the rule stays anyway (cheap). Either way, Phase 0 counts must not include failed-transaction events |
| **TS-T1** (STK-1 extended, TS-2) | Recorder throughput with group commit **on the real volume type of the rented server**: replay the busiest captured hour of the first 7 days, plus a synthetic 10× burst, through receive → queue → write → `fdatasync`, and `tabulate`, on 1 vCPU. Record CPU, memory, queue depth, the `fdatasync` latency distribution, durable-minus-receive lag, and whether the provider disconnected us ("lagged…") during a live 1 h burst capture. Also set and record the client's HTTP/2 window sizes [UNVERIFIED tonic option names] | Chainstack gRPC host (capture), then offline on the server | Durable lag ≤ 1 slot at p99; queue never above 10%; zero "lagged" disconnects; `fdatasync` p99 ≤ 20 ms; ≥ 10× CPU headroom at the p99 burst; memory ≤ 1 GB |
| **TS-T2** (TS-5) | For the 3 programs, derive the Anchor legacy IDL address (`create_with_seed(find_program_address([], P), "anchor:idl", P)`) and the Program Metadata canonical `idl` PDA (seeds [P, "idl"], program `ProgM6JC…`). `getAccountInfo` both (base64); for the Anchor account, skip the 8-byte tag, the authority (32) and `data_len` (u32), then zlib-decompress. Canonicalise the JSON (sorted keys) and SHA-256 it; compare with the pinned GitHub IDL (also canonicalised). Record the authority | RPC hosts | A second witness for A-005: match, mismatch (alarm, and we review which one is right), or "absent" (recorded; the ProgramData deploy slot stays the second witness) |
| **TS-T3** (TS-3) | For 1 h: `getSignaturesForAddress(program, limit 1000, confirmed)` every 60 s for PumpSwap and Pump. Record how many slots each reply fully covers, pagination depth, the credits charged per call, and the overlap with the Chainstack tape (tier C) | `mainnet.helius-rpc.com` | Sets the probe's sample window and its credit line (CO-7a). The probe stays if it costs ≤ 5% of the monthly credit budget |
| **TS-T4** (TS-1) | Outside timestamps: (a) `openssl ts -query -sha256 -cert` on a test hash, POST it to a public RFC 3161 authority, and verify the reply with `openssl ts -verify`; (b) the OpenTimestamps calendar stamp and verify; (c) read back the archive object's server-side upload time | the chosen TSA host (e.g. `freetsa.org` [UNVERIFIED endpoint]); `a.pool.opentimestamps.org` [UNVERIFIED]; the archive provider | At least one outside anchor besides the archive and Paul's summary verifies end to end |
| **TS-T5** (TS-9) | With the bot host's put-only key on a test bucket: try delete, overwrite, hide and shorten retention on a test object. Each must fail or create a new version that leaves the original restorable. Then run one full restore drill | the archive provider (chosen in PX-7) | All destructive attempts fail or are versioned; the restore matches the hashes |
| **TS-T6** (TS-8a, TS-11, TS-1) | On the rented server: `research` reading `store/sealed/` or any credential gets "permission denied"; research's network is blocked by the per-user rules; `fio` from research under its caps doesn't raise the recorder's `fdatasync` p99 by more than 5 ms; `auditd` logs a test read of `store/sealed/`; `LoadCredentialEncrypted=` works | none beyond the server | All hold |
| TS-T7 (TS-8a) | Build the same commit in the GitHub Actions builder and in a clean cloud session, then compare the `SHA256SUMS` | `index.crates.io`, `static.crates.io` (reachable today), `github.com` | Identical, or the difference explained (not a gate) |
| STK-2 | `u64::MAX`, `i128` extremes and negative reserves round-trip Rust → Parquet (Decimal128) → DuckDB and Polars exactly | `pypi.org`, `files.pythonhosted.org`, `static.crates.io` (reachable today) | Exact equality |
| STK-3 | Cooldown enforcement in CI: a lockfile with a crate under 7 days old fails `check_cooldown.py`; after Rust 1.100 the native setting also rejects it | `index.crates.io` (reachable today) | Both fail closed |
| (= D8 / C04) | Yellowstone reconnect with `from_slot` using our stubs; also read `SubscribeReplayInfo.first_available` to learn Chainstack's replay window | Chainstack gRPC host | As in the test plan, plus the window size recorded |

---

## Sources
- [VERIFIED-DOC] Pump docs and IDLs: https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/README.md ; …/idl/pump.json ; …/idl/pump_amm.json ; …/idl/pump_fees.json (pinned copies in `phase0/scripts/idl/`, `event_authority` seeds)
- [VERIFIED-DOC] Yellowstone gRPC: https://raw.githubusercontent.com/rpcpool/yellowstone-grpc/master/README.md ; …/yellowstone-grpc-geyser/src/grpc.rs (`try_send`, "lagged to send an update", `client_channel_full`) ; …/yellowstone-grpc-geyser/src/config.rs (`channel_capacity` 250,000, `replay_stored_slots` 150, `client_unresponsive_timeout` 60 s) ; …/yellowstone-grpc-geyser/config.json ; …/yellowstone-grpc-proto/proto/geyser.proto (`SlotStatus`, `from_slot`, `interslot_updates`, `SubscribeReplayInfo`) ; …/yellowstone-grpc-proto/proto/solana-storage.proto (`err`, `inner_instructions`, `inner_instructions_none`)
- [VERIFIED-DOC] Agave SVM: https://raw.githubusercontent.com/anza-xyz/agave/master/svm/src/transaction_processor.rs (`execute_loaded_transaction`, `deconstruct_transaction`)
- [VERIFIED-DOC] Anchor IDL account: https://raw.githubusercontent.com/solana-foundation/anchor/master/lang/src/idl.rs ; Program Metadata: https://raw.githubusercontent.com/solana-program/program-metadata/main/README.md
- [VERIFIED-DOC] uv `no-build`: https://raw.githubusercontent.com/astral-sh/uv/main/crates/uv-settings/src/settings.rs ; systemd credentials and resource control: https://raw.githubusercontent.com/systemd/systemd/main/docs/CREDENTIALS.md ; …/man/systemd.exec.xml ; …/man/systemd.resource-control.xml ; kernel io controller: https://raw.githubusercontent.com/torvalds/linux/master/Documentation/admin-guide/cgroup-v2.rst
- [VERIFIED-DOC] Registry metadata, fetched 2026-11-05: https://registry.npmjs.org/ ; https://index.crates.io/ (incl. `yellowstone-grpc-client`, `yellowstone-grpc-proto` build deps, `tonic`, `prost`, `tokio`, `zstd`, `crc32c`, `parquet`, `rusqlite`, `reqwest`, `tokio-tungstenite`, `rustls`, `rand_chacha`, `statrs`) ; https://pypi.org/pypi/<name>/json (incl. `pyarrow`, `polars`, `duckdb`, `numpy`, `scipy`, `anthropic` and its `requires_dist`) ; https://proxy.golang.org/ ; https://nodejs.org/dist/index.json
- [VERIFIED-DOC] pnpm settings: https://raw.githubusercontent.com/pnpm/pnpm.io/main/docs/settings/dependency-resolution.md ; npm config: https://raw.githubusercontent.com/npm/cli/latest/workspaces/config/lib/definitions/definitions.js ; uv resolution: https://raw.githubusercontent.com/astral-sh/uv/main/docs/concepts/resolution.md ; Codama: https://raw.githubusercontent.com/codama-idl/renderers-rust/main/README.md
- [VERIFIED-SEARCH] Cargo cooldown: https://socket.dev/blog/rust-cargo-cooldowns ; https://rust-lang.github.io/rfcs/3923-cargo-min-publish-age.html ; https://gbhackers.com/rust-1-100-strengthens-cargo/
- [VERIFIED-SEARCH] Malicious crates: https://blog.rust-lang.org/2025/09/24/crates.io-malicious-crates-fasterlog-and-asyncprintln ; https://thehackernews.com/2025/09/malicious-rust-crates-steal-solana-and.html
- [VERIFIED-SEARCH] TypeScript client napi engine: https://blog.triton.one/grpc-js-alternative-napi-rust/ ; https://www.quicknode.com/docs/solana/yellowstone-grpc/overview/typescript
- [VERIFIED-SEARCH] Storage: https://www.helius.dev/blog/migrating-from-clickhouse-to-rocksdb
- [VERIFIED-SEARCH] Backblaze B2 key capabilities: https://backblaze.com/docs/cloud-storage-application-key-capabilities ; https://www.backblaze.com/docs/cloud-storage-s3-compatible-app-keys
- [VERIFIED-SEARCH] OpenSSL `ts` (RFC 3161 client): https://docs.openssl.org/1.1.1/man1/ts
- [VERIFIED-SEARCH] Helius plan limits: https://helius.dev/docs/billing/plans
- Team files: `team-debate/phase0/red-team-phase0-review.md` (§5 and Seams), `DESIGN.md`, `team-debate/round3/rulings.md`, `docs/preregistration.md` (§2.4, §15), `docs/fee-model.md`, `docs/costs.md`, `docs/assumption-register.md`, `phase0/test-plan.md`, `phase0/scripts/p0/` (read only)
