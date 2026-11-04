# Round 2b: Security engineer response (wallet, signer, exits, supply chain)

## 0. In plain English (for Paul)
- **Red team found a real hole, and it is now closed.** A hacked bot server could have emptied the trading wallet with one "allowed" trade that paid the proceeds to the hacker. Now the bot can only send short requests ("sell all of coin X, no worse than price Y"). A separate small **guard computer** builds every transaction itself, fixes every payout to *our* wallet, and checks the price itself.
- **Selling can't be used to steal, so selling stays on.** Your STOP button now switches off *buying* at the signing service, and selling back into our own wallet keeps working. A separate KILL lever cuts everything, for when you think the guard itself has been hacked.
- **Cheaper, more reliable signing:** Amazon's key vault (KMS) in Frankfurt, about $1 a month, replaces Turnkey, which would have cost up to 12% of a $5 bet.
- **Don't race other bots at the second a coin graduates.** We'd arrive several blocks late with any key setup, and signing is less than one block of that gap.
- **Worst cases:** if the bot server is hacked, we lose at most about one day's buying limit. If the guard is hacked, we lose the hot wallet. That's why the hot wallet stays small.

Tags: [VERIFIED-DOC] = I read the primary source this session. [VERIFIED-SEARCH] = seen only in search results. [UNVERIFIED] = memory or inference, with a test. [DERIVED] = my arithmetic. **Host notes:** `curl` and WebFetch both worked on `raw.githubusercontent.com` (I downloaded Pump's IDL). WebFetch failed to resolve `docs.turnkey.com` and `docs.privy.io`, so those two hosts must be allowed before the vendor facts below become VERIFIED-DOC.

---

## 1. Answers to attacks

### The reconciling rule: "exits always run" versus "the wallet can't be drained"
**A sell can only turn our coins into SOL in our own wallet, at no worse than the guard's own price limit.** A permission that can only do that can't steal anything. The worst it allows is a bad sale, capped by the slippage limit. So the sell permission can safely stay on through STOP, signer trouble and Pump updates. **Theft-by-trade lives on the buy side**, where SOL leaves the wallet, so buying is what every lever cuts first. Every fix below follows this rule.

### SEC-1 (Critical): drain through an allowed swap route. **FIXED**
**What I checked.** In Pump's official PumpSwap IDL (the program's published list of instructions and the accounts each one takes), every buy and sell instruction (`buy`, `buy_v2`, `buy_exact_quote_in`, `buy_exact_quote_in_v2`, `sell`, `sell_v2`) lists `user_base_token_account` and `user_quote_token_account` as plain writable accounts. No address rule, no ownership rule, and no link to the signer [VERIFIED-DOC [pump_amm.json](https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/idl/pump_amm.json)]. The v2 trade doc only says "User's token account for `base_mint`. **Must exist.**" [VERIFIED-DOC [PUMP_SWAP_TRADE_V2.md](https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/instructions/PUMP_SWAP_TRADE_V2.md)]. The IDL also contains `multi_hop_swap`, whose `user_out_token_account` is just as unconstrained [VERIFIED-DOC same IDL]. The IDL can't show whether the program checks the owner at run time (test P6). **I design as if it doesn't.**

**Fix: the bot sends requests ("intents"), never transactions.** The guard builds each transaction from the official IDL and fills in every account that belongs to us itself. Our token account for a coin is the standard "associated token account": an address computed from our wallet, the token program and the coin, so it can't be swapped for someone else's. Our wrapped-SOL account (SOL in token form, which SOL pools pay out in) is one fixed address.

| Request from the bot | What the guard builds | What the guard fixes or checks itself |
|---|---|---|
| BUY coin, SOL amount, worst price | PumpSwap `buy_exact_quote_in_v2` (v1 for cashback pools, which reject v2 per EXE-7) | Our computed token account receives the coins. Pool address re-derived from the IDL seeds (`pool`, index, creator, base mint, quote mint) [VERIFIED-DOC IDL], so only the canonical pool is accepted. Amount ≤ per-trade cap. Worst price no looser than the guard's **own** quote (from its own two RPCs) minus the max slippage |
| SELL coin, % held, worst price | PumpSwap `sell_v2`/`sell`, or the curve's sell | We pay from our own token account and receive into our wrapped-SOL account. Amount ≤ what we hold on-chain. Same price check |
| CLOSE coin | Token close-account (also added to the last sell) | Rent refund goes to the hot wallet only (recovers the ~0.002 SOL deposit, SEAM-1) |
| SWEEP | One SOL transfer | Destination is the cold address in the guard's config, which only Paul can change. Amount ≤ balance − cap |

**Everything else is refused:** `multi_hop_swap`, Jupiter routes, `Approve`, `SetAuthority`, `Assign`, durable nonces, extra signers, a foreign fee payer and lookup tables. The priority fee and the tip are capped per transaction and per day, and tips may go only to the listed tip accounts (SEAM-12). **Jupiter leaves the signing path.** It stays a read-only price check.

**Second layer at the signing service (only if we pick a hosted wallet).** Its own policy repeats the sell pin. Turnkey policies can check an account by position (`accounts[i].account_key`). After an IDL upload they can also check named accounts and argument values (`parsed_instruction_data.named_accounts`, `program_call_args`) [VERIFIED-SEARCH [docs.turnkey.com](https://docs.turnkey.com/concepts/policies/smart-contract-interfaces)]. Privy offers named-account checks through an uploaded IDL, but warns these checks fail when accounts come from lookup tables [VERIFIED-SEARCH [docs.privy.io](https://docs.privy.io/controls/policies/example-policies/solana-idls)]. Since our wrapped-SOL account is a fixed address, both vendors pass red-team's test for **sells**. A buy's output account is different for every coin, so no fixed rule can pin it. The vendor can only cap the buy size.

**What a hacked bot server can still do (honest):** make us buy coins the attacker controls, churn our money through fees, or sell into the attacker's sandwich at the worst allowed slippage. These limits therefore move **into the guard**, where the bot can't loosen them: max SOL per trade, buys per hour and per day, total SOL bought per rolling 24 h, max open positions, the re-entry cooldown, and the fee and tip budget. Illustration with placeholder numbers [DERIVED]: hot wallet 5 SOL, 0.25 SOL per trade, 1.5 SOL of buys a day, 3 positions, 5% slippage. The worst day is about 1.5 SOL (attacker coins) + 0.04 SOL (bad sells of 0.75 SOL open) + 0.05 SOL (fees) ≈ **1.6 SOL, not 5**. When the daily buy cap is reached, buying pauses automatically (L1) and Paul gets an alert. The guard also alerts on every refused request.

### SEC-2 (Critical): the guard is bypassable on the same server. **FIXED**
Two machines on **different provider accounts**:
- The **bot host** (data, AI, strategy, many packages) holds **no** signing access.
- The **guard host** runs the exit guard plus the signer guard, and holds the only signing credential. It has **no public inbound ports.** The bot reaches it over a private encrypted tunnel that carries one message type (intents). It runs no AI, fetches no metadata and takes no social feeds. Its only outside connections are its own two RPC providers and the senders.

Proposed guard host: a small AWS instance in Frankfurt (t4g.small about $14/month [VERIFIED-SEARCH [cloudprice.net](https://cloudprice.net/aws/ec2/instances/t4g.small), Round 1]). It authenticates to KMS through the machine's own AWS role, so **no secret is stored on disk** [UNVERIFIED design: confirm with test S3].

**Remaining risk (ACCEPTED):** if the guard host itself is hacked, the hot wallet is lost. That's true even with a vendor policy: an attacker can send many capped buys in parallel, each paying out to their own token account, all within about a second [DERIVED]. **The hot-wallet cap is the backstop.** An on-chain tripwire on a third provider watches the wallet. If value leaves to any address not on the list, it calls KMS `DisableKey` using a credential that can **only** disable that one key [UNVERIFIED: test S3]. That stops a slow bleed. It doesn't stop a one-second drain.

### SEC-3 / SEAM-3.1: a hosted-signer outage stops sells. **FIXED by choice + ACCEPTED residual**
- **Primary signer:** AWS KMS Ed25519 (Solana's key type) in the same region as the guard. AWS publishes a 99.999% monthly uptime target per region [VERIFIED-SEARCH [aws.amazon.com/kms/sla](https://aws.amazon.com/kms/sla), seen via translated pages]. That's roughly 26 seconds of downtime a month [DERIVED]. It's a target backed by service credits, not a guarantee. Compare Privy: 8 outages since Feb 2026, including "wallet actions and transaction finality delayed" [VERIFIED-SEARCH [isdown.app](https://isdown.app/status/privy-io/outage-history), via red team]. I found no incident history for Turnkey (test S6).
- **The guard host dies:** Paul launches a pre-built standby guard in a second Frankfurt data centre from a saved template (one click: *EC2 → Launch templates → "guard-standby" → Launch*). It uses the same role and the same KMS key, and it rebuilds positions from the chain. The standby stays off until launched, so only one guard ever runs and double sells can't happen (unlike risk-manager's always-on standby, option C).
- **KMS itself is down in Frankfurt:** a "multi-Region replica" (the same key copied to a second region) would cover this. AWS says multi-Region keys can be asymmetric [VERIFIED-SEARCH [docs.aws.amazon.com](https://docs.aws.amazon.com/kms/latest/developerguide/multi-region-keys-overview.md)], but I couldn't confirm that Ed25519 is supported (test S2). Until it is, **ACCEPTED RISK:** positions wait. Open exposure is ≤3% of the bankroll by risk-manager's default.

### SEC-4 / SEAM-3.2: STOP revokes the sell path. **FIXED: three levers instead of one**
| Lever | What it does | Sells? | When |
|---|---|---|---|
| **PAUSE BUYS** | The guard refuses buy requests (software, instant, reversible) | Yes | Anything looks odd |
| **STOP** | Revokes buying **at the signer level**. With Privy or Turnkey, the guard holds two API keys: a *trade* key and a *sell-only* key, whose policy allows only sells that pay into our wrapped-SOL account, plus close-account. STOP deletes the trade key. With KMS (which can't read Solana transactions), STOP flips the guard to sell-only. That switch is software, but it lives on the trusted host and the bot can't reverse it | Yes | Bot host suspected |
| **KILL** | Disables every signing credential, then Paul follows the Round 1 checklist (move funds, rotate keys) | No | Guard host suspected |

### SEC-5 / SEAM-3.5: the 7-day package cooldown versus urgent Pump fixes. **FIXED**
- **The guard doesn't run Pump's npm SDK at all.** Its small builder reads the official IDL file (a data file, pinned to a reviewed commit of `github.com/pump-fun/pump-public-docs`). A Pump update means reading a diff of a JSON file, not trusting a new code package. The bot host may use the SDK for quotes only.
- **Fast lane if code is really needed:** pnpm can exempt one exact version (for example `@pump-fun/pump-swap-sdk@x.y.z`) from the cooldown via `minimumReleaseAgeExclude` (exact versions since v10.20) [VERIFIED-SEARCH [pnpm.io/settings](https://pnpm.io/settings)]. It's allowed only if (1) the version is published by the official `@pump-fun` account and matches a tag in Pump's GitHub repo, (2) it adds no new dependencies or install scripts, (3) a second reviewer reads the diff, (4) Paul approves in one line, and (5) the exemption is removed after 7 days. **The cooldown is never switched off wholesale.**

### SEC-6 / SEAM-3.3: the allowlist blocks sells after a Pump update. **FIXED**
The allowlist works at the level of "program + instruction name from the IDL", not the exact byte layout. Pump's updates so far add new instructions next to the old ones (`sell` and `sell_v2` both exist; v1 "still works") [VERIFIED-DOC IDL; EXE §1]. **Buys** need the exact reviewed version and fail closed. **Sells** are tolerant. Any sell instruction in the new official IDL is accepted if the signer is us, our token account pays, our wrapped-SOL account or wallet receives, and the amount ≤ what we hold. New accounts appended by Pump are allowed if the new IDL names them.

### SEAM-3.4: Pump's own sell switch. **ACCEPTED RISK (not a security control)**
If Pump disables selling, nobody's bot can sell. In Aug 2025 traders were told to sell through Pump's website only [VERIFIED-SEARCH [protos.com](https://protos.com/axiom-traders-panic-as-pump-fun-temporarily-bans-selling-memecoins/), via red team]. A KMS key can't be loaded into a phone wallet. **QUESTION (for QUESTIONS_FOR_PAUL):** "In a 'website-only' event, may the hot wallet be exportable to a phone wallet for emergencies?" **Default: no.** Positions wait, because an exportable key is a standing theft target. Choosing yes means Privy instead of KMS (Turnkey supports export too [VERIFIED-SEARCH [docs.turnkey.com](https://docs.turnkey.com/features/wallets)]), and the hot wallet is retired after any export.

### SEC-7: lying lookup tables. **FIXED**
Guard-built transactions use **no lookup tables** (lists of account addresses stored on-chain), so nothing is hidden. If a lookup table ever appears in a request, it's refused.

### SEC-8: Turnkey's cost at our bet size. **FIXED: Turnkey rejected for Phase 1**
| Signer | Cost per trade (2–6 signatures with ladder and retries) | At a $5 stake |
|---|---|---|
| Turnkey pay-as-you-go ($0.10/signature) [VERIFIED-SEARCH [turnkey.com/pricing](https://www.turnkey.com/pricing), Round 1] | $0.20–0.60 | **4–12%** |
| Privy (free to 50K signatures/month) [VERIFIED-SEARCH [privy.io/pricing](https://www.privy.io/pricing), Round 1] | $0 | 0% |
| AWS KMS ($0.15 per 10K) [VERIFIED-SEARCH [aws.amazon.com/kms/pricing](https://aws.amazon.com/kms/pricing/), Round 1] | ≈ $0.0001 | ≈ 0% |

Turnkey only fits once its fee is ≤1% of a stake, meaning stakes of about $40–60 or more [DERIVED].

### Linked seams. **FIXED**
- **SEAM-12:** one joint table of tip accounts per sender (Jito, Helius Sender, Nozomi), copied by a person from each sender's official docs, with a cap per transaction and per day. A path whose tip account isn't on the list gets refused in **paper** first, so we find out before real money.
- **SEAM-13 / RSK-6:** sells Paul makes himself don't trigger L4. L4 fires only when value leaves to an address that isn't on the list.
- **RSK-5:** the guard sells only coins in the buy journal. Spam airdrops are ignored, never adopted, and never touched.
- **DAT-7:** we won't accept an API that hands us a wallet key to store. If PumpPortal's prepaid data needs a funded wallet, Paul creates a separate prepaid wallet (≤0.05 SOL), and its key is never on our servers.

---

## 2. The big fork: race at graduation or not?
**Signing cost in time:** Turnkey claims under 100 ms [VERIFIED-SEARCH [solanacompass.com](https://solanacompass.com/projects/turnkey), Round 1]. One user saw KMS take 25–250 ms (a different key type, region unknown) [VERIFIED-SEARCH [repost.aws](https://repost.aws/questions/QUPEubdAqrSnSLm-38Vjyqpw/kms-signing-performance-with-asymmetric-ecc-nist-p256-key-is-slow), Round 1]. Same-region KMS should be tens of ms [UNVERIFIED: test S1]. A local key takes under 1 ms [UNVERIFIED]. With slots (blocks) of about 350 ms [VERIFIED-SEARCH [thedefiant.io](https://thedefiant.io/news/blockchains/solana-activates-350-millisecond-slots-on-mainnet), via risk-manager], remote signing costs **about 0.1–0.7 blocks** of red-team's **3–10 block** gap (PREMISE-1) [DERIVED].

| | Race at graduation | Event-based entry after the opening window (**recommended**) |
|---|---|---|
| Key setup needed | Key in memory on an internet-facing box next to the RPC; any remote call is too slow | KMS (or Privy) behind the guard |
| Loss if that box is hacked | The whole wallet in seconds, and the key is stolen for good | Bot host: ≤ daily buy cap. Guard: the hot wallet |
| Still behind the leaders by | 2–9 blocks even with a local key, since leaders complete, migrate and buy in one transaction [DERIVED; data-engineer §6] | Doesn't matter at entry. Tens of ms on exits |
| Extra $/month | Co-located server plus paid feeds (others' estimates) | ≈ $15 (guard host + KMS) [DERIVED] |

**Verdict: don't race in v1. Remote signing is worth its latency,** because the race is lost anyway and racing needs the least safe key setup. If test P1 later proves a profitable window that needs <1 block, the only acceptable design is a separate **racing wallet** with a local key and a cap of 1–2 bets: money we treat as already lost if hacked. That's Paul's decision, and it's off by default.

## 3. Challenges to other areas
1. **Risk-manager:** the exit guard and every limit that bounds theft (caps, pace, daily totals, fee budget) must live **on the guard host**. The bot or the AI may tighten a limit but never loosen one. Paul's "loosen" path goes only to the guard, with the 10-minute delay and an alert. A dashboard on the bot host must not be able to raise limits.
2. **Execution-engineer:** (a) Jupiter `/build` is quote-only, never signed (SEC-1, and EXE-4 already says it must never gate sells). (b) The last sell and the account close go in one guard-built transaction. (c) Every sender path must pass the tip-account table in paper. (d) Helius Sender Max's 0.001 SOL minimum tip [VERIFIED-SEARCH [helius.dev](https://www.helius.dev/docs/sending-transactions/sender), via EXE] is 2% of a 0.05 SOL stake, so it must be costed against the guard's daily fee budget.
3. **Data-engineer and social-intel:** **no public inbound endpoints** on either host. No Helius webhooks (use outbound streams, as SOC-6 demands), and no public dashboard (Paul reaches it through a login-protected tunnel). Coin metadata links are fetched by a sandboxed fetcher with size and time limits and no credentials, and the fetched text is treated as attack text before it reaches the AI.

## 4. Edge hunt (short: security is mostly "lose less", not an edge)
- **E1. First to work after a Pump update.** *Why we'd win:* bots that depend on SDK releases or vendor patches stall after breaking changes (Aug 2025: hours of broken bot selling [VERIFIED-SEARCH protos.com]). Our IDL-driven builder can update from Pump's official repo within about an hour, because the change is one reviewed JSON diff [UNVERIFIED speed]. Thin competition in that window could improve our exits and fills. *Why they can't copy it quickly:* most retail bot vendors ship app updates on their own release schedule [UNVERIFIED]. *Cost:* ≈ $0. *Kill test (decided now):* for the last 5 Pump changes in the README changelog, count distinct non-Pump-frontend signers trading PumpSwap in the 6 h after versus the 6 h before. **Pass only if** the count falls by ≥30% for ≥2 h after at least 2 of the 5 changes. Otherwise kill it. Buys stay paused until DAT-1's live price check passes, so this mainly helps exits.
- **E2. Cost parity, not an edge.** KMS signing (≈ $0.0001 a trade) instead of Turnkey removes 4–12% of fixed cost per $5 trade (SEC-8). That doesn't beat anyone. It only stops us losing to our own bills (PREMISE-7).

## 5. Revised recommendation (5 bullets)
1. **Two hosts:** the bot host (data, AI, strategy) has **no** signing access. A tiny guard host (exit guard + signer guard) on a separate AWS account in Frankfurt holds the only credential. No public inbound ports on either.
2. **Intents, not transactions:** the guard builds every transaction from the official IDL, computes our own accounts, re-derives the canonical pool, checks the price itself, and enforces every per-trade, per-day and fee limit. No Jupiter in the signing path, no lookup tables, no multi-hop.
3. **Signer:** AWS KMS Ed25519 (≈ $1/month), reached through the guard's machine role. Privy is the measured alternative (and the only choice if Paul wants an exportable emergency key). Turnkey is rejected at Phase 1 stakes. Plain key files are rejected for real money.
4. **Three levers:** PAUSE BUYS, STOP (buying revoked, sells continue) and KILL (everything revoked, then the checklist). Add an on-chain tripwire on a third provider that can only disable the key, plus a standby guard template.
5. **Don't race at graduation.** The hot-wallet cap stays the final backstop. Max loss is about one day's buy cap if the bot host is hacked, or the hot wallet if the guard host is hacked.

## Tests to run once allowed (no funds; devnet only after Paul approves a build)
| # | Test | Domain(s) |
|---|---|---|
| S1 | 1,000 KMS Ed25519 signs of a 1,232-byte dummy message from a t4g instance in Frankfurt with a test key. Record p50/p99 | `kms.eu-central-1.amazonaws.com` |
| S2 | Does Ed25519 support multi-Region replicas? What message size limit applies to raw signing? | `docs.aws.amazon.com` |
| S3 | An IAM policy that allows only `kms:DisableKey` on one key, and machine-role access with no stored secret (sandbox account) | `docs.aws.amazon.com`, `iam.amazonaws.com` |
| S4 | P6 on mainnet history, then on devnet: a sell whose payout account belongs to another wallet. If it succeeds, the guard's pinning is the only defence (it already is) | RPC host, `api.devnet.solana.com` |
| S5 | P8 on the primary docs: Turnkey `named_accounts`/`program_call_args`, Privy `solana_instruction_data` named accounts, and a sell-only key policy | `docs.turnkey.com`, `docs.privy.io` (both failed to resolve this session) |
| S6 | P9: 12-month incident history | `status.privy.io`, Turnkey status page, `health.aws.amazon.com` |
| S7 | Official tip-account lists per sender | `docs.jito.wtf`, `www.helius.dev`, Nozomi docs host |
| S8 | Paper drill (no network): with 3 open paper positions, cut each exit path in turn (signer down, STOP, a new IDL version, a sell switch, a cooldown block, a dead guard plus standby launch). Record time-to-flat | none |

**Sources:** [pump_amm.json](https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/idl/pump_amm.json) · [PUMP_SWAP_TRADE_V2.md](https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/instructions/PUMP_SWAP_TRADE_V2.md) · [Turnkey smart-contract interfaces](https://docs.turnkey.com/concepts/policies/smart-contract-interfaces) · [Turnkey Solana policy examples](https://docs.turnkey.com/concepts/policies/examples/solana) · [Turnkey wallets/export](https://docs.turnkey.com/features/wallets) · [Privy Solana IDL policies](https://docs.privy.io/controls/policies/example-policies/solana-idls) · [Privy Solana policies](https://docs.privy.io/controls/policies/example-policies/solana) · [AWS KMS SLA](https://aws.amazon.com/kms/sla) · [AWS multi-Region keys](https://docs.aws.amazon.com/kms/latest/developerguide/multi-region-keys-overview.md) · [pnpm settings](https://pnpm.io/settings) · [Privy outage history](https://isdown.app/status/privy-io/outage-history) · [Protos, Aug 2025 sell outage](https://protos.com/axiom-traders-panic-as-pump-fun-temporarily-bans-selling-memecoins/) · Round 1 sources as cited in `team-debate/round1/security-engineer.md`.
