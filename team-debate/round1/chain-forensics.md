# Round 1: Chain forensics (spotting dangerous coins)

**In plain English (for Paul):**
- We can check the "is this coin built safely?" questions ourselves, cheaply and almost perfectly: can more coins be printed, can wallets be frozen, can the liquidity be pulled, is this a genuine Pump.fun coin. On genuine Pump.fun coins these checks almost always pass, so they mostly catch fakes.
- The checks that matter more ("did the dev and friends secretly buy most of the supply?") can only ever be *partly* reliable, because a determined scammer can hide behind many wallets. No tool, ours or a paid one, catches every rug.
- Recommendation: build the core checks ourselves on the same data feed we already need, start the slow checks *before* the coin graduates so the final decision takes well under a second, and run one paid risk service (RugCheck, ~$40/month) as a "second opinion" that gets logged but cannot approve a trade on its own.
- Every check writes one plain line such as `REJECT top10_holders: 41.2% > 30% limit`, so you can tune the numbers.

Jargon: a **slot** is one Solana block, about 0.4 s [UNVERIFIED, common knowledge]. **RPC** is the paid "read the blockchain" service, billed in **credits**. A **PDA** is an address controlled by a program, with no private key. **LP tokens** are the receipts for liquidity in a pool. **Token-2022** is Solana's newer token standard, which allows add-on "extensions". A **Jito bundle** is a group of transactions that land together, all or none. **Sybil wallets** are many wallets secretly run by one person.

Source codes [S1]…[S23] are listed at the bottom with URLs and tags.

## 1. Facts that shape the design
- At migration, Pump.fun **burns the LP tokens** [VERIFIED-DOC S1; VERIFIED-SEARCH S7]. On a genuine migrated pool, the classic rug of pulling the liquidity is not possible. The real danger is insiders **dumping tokens they hold**.
- New coins (`create_v2`) use **Token-2022**. The only extension the docs name is a metadata pointer. The mint authority starts as a Pump PDA [VERIFIED-DOC S2]. *Whether mint and freeze authority end up null is UNVERIFIED*: test T1.
- A genuine migrated pool is the **canonical** PumpSwap pool: index 0, address derived from `["pool", index, creator, baseMint, quoteMint]`. Anyone can create other, non-canonical pools [VERIFIED-DOC S3].
- The bonding-curve account stores `creator`, `complete`, `is_mayhem_mode` and `quote_mint`. The `creator` **can differ from the wallet that signed the create** [VERIFIED-DOC S1]. A Pump admin can set the creator on some coins [VERIFIED-DOC S4], so "creator" does not always mean "dev".
- Coins can now be **paired against another Pump coin instead of SOL** [VERIFIED-DOC S6].
- **Mayhem-mode** coins have **2 billion supply**. An AI agent trades them for 24 h, then burns its unsold tokens [VERIFIED-SEARCH S8]. Its holdings would distort holder maths.
- The curve is marked complete first and the pool opens afterwards. In between, `CompleteEvent` and `PostCompleteBuyEvent` fire [VERIFIED-DOC S5]. **That gap is free time to finish checks.** How long it lasts is UNVERIFIED (test T3).
- Volume is roughly **25–40k launches/day and 80–300 graduations/day** [VERIFIED-SEARCH S21]. Running deep checks only on coins close to graduating keeps the cost small.
- A study of 6.4M Solana tokens found that rugs are driven mainly by **liquidity manipulation and social dynamics, not contract backdoors** [VERIFIED-SEARCH S22]. So the "behaviour" checks matter most, and they are the least reliable.

## 2. Every check

**Timing.** "Pre-arm" means the check runs while the coin is still on its curve, once it passes a progress threshold (placeholder: 70%). "Gate" means the check runs between curve-complete and pool-open. Credits are per coin, assuming 1 credit per standard RPC call [VERIFIED-SEARCH S10]. The cost of `getTokenLargestAccounts` itself is UNVERIFIED (test T2).

**Reliability** describes the *measurement*. A pass never means "safe".

| # | Check (default rule, Paul tunes) | How detected | When / speed | Credits | Reliability | How a scammer evades it |
|---|---|---|---|---|---|---|
| 1 | Genuine Pump coin on canonical pool | Derive the bonding-curve PDA and the index-0 pool PDA, then confirm both accounts exist and are owned by the Pump/PumpSwap programs [S1, S3] | Gate, 1 batched read (~ms) | 1–2 | **Reliable** | Fake "graduated" coin on a non-canonical pool or another DEX. This check defeats that. |
| 2 | LP burned / no LP holder | Read the pool `lp_supply` and the LP mint supply/holders [S3]. Expect burned [S1]. | Gate | 1–2 | **Reliable** (canonical pools) | Not possible on canonical pools. Only matters for the fakes caught by #1. |
| 3 | Mint authority null, freeze authority null | Read the mint account (parsed) | Gate | 1 | **Reliable** | Not possible on genuine coins. Fakes get caught. |
| 4 | Token-2022 extensions: allow only metadata pointer/metadata | Same mint read. Reject on permanent delegate, transfer hook, transfer fee, default-frozen, pausable [VERIFIED-SEARCH S19: permanent-delegate "burn from your wallet" scam] | Gate | 0 (same read) | **Reliable** | Not possible on genuine coins. |
| 5 | Quote mint is SOL (else WARN/REJECT) | `quote_mint` on the curve/pool [S1, S6] | Gate | 0 | **Reliable** | A coin quoted in another Pump coin inherits that coin's rug risk. Treat as a separate rule. |
| 6 | Mayhem flag (adjust supply = 2B, exclude agent wallet and agent volume) | `is_mayhem_mode` [S1, S8] | Gate | 0 | **Reliable** flag. Identifying the agent wallet is UNVERIFIED (T9). | n/a (it is Pump's own feature) |
| 7 | Top-10 holder concentration (placeholder: REJECT > 30%) | `getTokenLargestAccounts`, which returns **only the top 20 token accounts** [VERIFIED-SEARCH S9]. Map accounts to owners (1 `getMultipleAccounts`). Exclude the pool vault, the curve account, burn addresses and the Mayhem agent. | Gate, ~2 calls | 2+ | **Partly reliable** | Spread the supply over 50+ wallets each holding under 1%. Top-10 then looks healthy. Fully counting the long tail needs a heavy program-wide scan [UNVERIFIED cost; T2]. |
| 8 | Dev wallet holding / sold (placeholder: REJECT if dev > 5%, WARN if dev sold > 50% into the curve) | Track **both** the create signer and `creator` [S1]. Their buys and sells come from curve trade events. Final balance comes from #7 or 1 call. | Built up from creation (0 credits); gate check 1 | 0–1 | **Partly reliable** | Buy from other wallets, move tokens to fresh wallets with plain transfers (these do not show in trade events), or set `creator` ≠ signer [S1]. |
| 9 | Bundled launch (placeholder: REJECT if same-slot/first-2-slot buyers hold > 20%) | From the feed: buyers in the creation slot and the next 1–2 slots, and whether they are still holding. Optional: ask Jito whether the create tx was in a bundle via `bundles.jito.wtf/api/v1/bundles/transaction/{sig}` [VERIFIED-DOC S12, third-party client code]. Tip transfers to the 8 Jito tip accounts are a weak hint [VERIFIED-SEARCH S12]. | Pre-arm (0 credits from the feed; Jito API is off-chain) | 0 | **Partly reliable** | Spread buys over several slots and use separate transactions. Bundler tools advertise "undetectable" multi-wallet buys [VERIFIED-SEARCH S23]. Legit snipers also buy in slot 0, so this check gives **false positives** [VERIFIED-SEARCH S20]. |
| 10 | Shared funding source (sybil cluster) among top holders and early buyers (placeholder: REJECT if a cluster holds > 20%) | Helius `funded-by`: first incoming SOL transfer. Paid plans only, beta, cache forever, immediate funder only [VERIFIED-SEARCH S11]. DIY alternative: walk each wallet's oldest transactions. | Pre-arm, ~40 wallets in parallel | ~40–150 | **Partly reliable** | Fund through exchange withdrawals (the funder shows as "exchange"), multi-hop chains, swap services, or bought aged wallets. |
| 11 | Fresh-wallet share (wallets < N days old or < M transactions) | `getSignaturesForAddress` (limit small) per holder | Pre-arm | ~20–40 | **Partly reliable** | Pre-aged ("warmed") wallets are cheap. |
| 12 | Wash trading / fake volume | From our own trade history: round trips by the same wallet or cluster, volume per unique trader, same-slot buy+sell. Exclude the Mayhem agent. | Pre-arm, 0 credits | 0 | **Partly reliable → not reliably detectable** at scale | Many unrelated-looking wallets with random sizes. |
| 13 | Creator history: past coins and how they ended | **Our own database**, built from every create event we see (dev → coins → outcome). Cold start: empty. | Instant lookup | 0 | **Partly reliable** (improves over time); on its own **not reliably detectable** | A new wallet per launch costs nothing. Partly countered by #10 (same funder lineage). |
| 14 | Recycled insider wallets (same early buyers across one group's launches) | Our own database of slot-0/early buyers per coin | Instant lookup | 0 | **Partly reliable** (improves over time) | Rotate wallets each launch. |
| 15 | Third-party second opinion (RugCheck score/insiders) | `api.rugcheck.xyz/v1/tokens/{mint}/report` [VERIFIED-SEARCH S13] | Gate, external latency UNVERIFIED (T6) | $ | **Partly reliable**, opaque | Same evasions as above. The vendor's rules can change silently. |

**Fail-closed rule.** If any *required* check (#1–#8) times out, errors or cannot decode an account, the verdict is `REJECT DATA_MISSING:<check>`, never a pass. The Pump programs change often [VERIFIED-DOC S6], so the decoder checks the account size and type marker and refuses anything unknown.

**Log line per check.** It records the check id, verdict (PASS/WARN/REJECT/DATA_MISSING), measured value, limit, what was excluded, data source, slot, milliseconds and decoder version. Examples:
- `REJECT top10_holders: 41.2% > 30% (excl. pool vault, burn, mayhem agent) src=getTokenLargestAccounts slot=… 140ms`
- `WARN bundle_slot0: 6 wallets bought 14.0% in creation slot; 4 still hold 9.1% (limit 20%)`

## 3. Doing it ourselves vs third-party risk APIs

| Option | Speed for a just-graduated coin | $/month | $/check (≈9k graduations/mo) | Reliability / if it's down | Build difficulty |
|---|---|---|---|---|---|
| **DIY on our RPC + feed** | Gate checks are a few parallel reads, likely < 0.5 s [UNVERIFIED, T2]. Slow checks are pre-armed. | Rides on the RPC plan the data team picks. E.g. Helius Developer is **$49 for 10M credits**, Free is 1M [VERIFIED-SEARCH S10]. Est. 1–5M credits/mo for forensics, including pre-arm on ~3–5× more coins than graduate [UNVERIFIED estimate]. | ~$0.0005–0.001 [UNVERIFIED estimate] | Transparent, and we own the rules. RPC outage → fail closed. | **Medium–hard.** We must decode Pump accounts and keep up with program changes. |
| **RugCheck** | Free tier serves **cached reports only**. Paid tiers can request fresh reports [VERIFIED-SEARCH S13]. Fresh-report latency UNVERIFIED (T6). | Free $0 (3 req/s); Basic **$40** (10 req/s); Business **$100** (100 req/s + insider websocket); Pro $500 [VERIFIED-SEARCH S13] | ~$0.004 (Basic) | Opaque score. Outage → we lose the second opinion only. | Easy |
| **GoPlus (Solana, beta)** | UNVERIFIED for coins seconds old (T7) | Free **150K CU/mo**; paid **$199–$3,499** [VERIFIED-SEARCH S14] | CU per call UNVERIFIED | Mainly contract flags (#3–4). Weak on behaviour checks. | Easy |
| **Birdeye `token_security`** | UNVERIFIED (T8) | Lite ~$39 (2.5M CU) … Business ~$499 [VERIFIED-SEARCH S15, secondary table, low confidence] | CU per call UNVERIFIED | Gives top-10 %, creator %, authorities, transfer fee [S15] | Easy |
| **Solana Tracker risk** | UNVERIFIED (T9) | Free 2,500 requests; ~€50–€397/mo [VERIFIED-SEARCH S16, secondhand] | ~€0.005+ | Has sniper/insider/bundler/dev scores [S16]. Sources conflict on which direction the score scale runs. | Easy |
| Bubblemaps / SolSniffer | Unknown | Pricing UNVERIFIED [S17, S18] | ? | Cluster views and a 0–100 score with known false positives [S18] | Easy |

## 4. Recommendation
1. **DIY for every gate check (#1–#8)** and for the cheap behaviour checks that come straight from the feed (#9, #12–#14). These are deterministic, cost close to zero per coin, are fast, and every reason is explainable.
2. **Pre-arm** the slow checks (#10, #11, Jito lookup) once a coin is ~70% up its curve. The gate then only re-reads balances and authorities during the complete → pool-open gap.
3. **Funding-source lookups via Helius `funded-by`** if the data team picks a paid Helius plan (cache results forever). Otherwise, our own wallet walk limited to the top-20 holders and early buyers.
4. **RugCheck Basic ($40/mo) as a logged second opinion**, advisory only for the first month of paper trading. We log every disagreement with our verdict, then decide with Paul whether it earns a veto. It can never approve a trade by itself.
5. Start the creator/insider database **on day 1 of paper trading**. It is worthless on day 1 and valuable by month 2.

## 5. Open risks
- **Program changes** (S6) can silently break decoding. Mitigations: fail closed, keep fixture tests per program version, and alert on unknown account sizes.
- **Top-20 cap** (S9): concentration spread across many small wallets is under-counted. Counting the full holder list is heavy; its cost and speed are UNVERIFIED.
- **Bundles are not labelled on-chain.** The Jito lookup is an off-chain API with unknown limits. Slot-0 heuristics produce false positives (S20).
- **Sybil detection is an arms race.** Exchange-funded wallets hide their links. Expect misses.
- **Admin-set creators** (S4) and the Mayhem agent (S8) can confuse the dev and holder checks.
- **Cost watch:** the pre-arm threshold drives credit spend. If it fires on too many coins, credits jump. Log the spend per check.
- **Placeholder thresholds** are guesses until they are backtested (T10).

## 6. Tests to run once allowed (exact domains)
- **T1** `mainnet.helius-rpc.com` (or `api.mainnet-beta.solana.com`): parsed `getAccountInfo` on 20 recent `create_v2` mints. Confirm the mint and freeze authorities are null and the extensions are only metadata pointer/metadata.
- **T2** `mainnet.helius-rpc.com` plus `www.helius.dev/docs/billing/credits`: credit cost and p50/p95 latency of `getTokenLargestAccounts`, `getMultipleAccounts` and `getSignaturesForAddress` on 50 migrated coins. Also the cost of a full holder scan.
- **T3** The data feed's host: measure the gap between `CompleteEvent` and the pool opening on 100 graduations.
- **T4** `mainnet.helius-rpc.com`: decode 20 canonical PumpSwap pools. Confirm index 0, `lp_supply`, and that the LP is burned.
- **T5** `api.helius.xyz` (Wallet API host; UNVERIFIED, check the docs): `/v1/wallet/{w}/funded-by` on 100 early buyers. Measure hit rate, latency and credits.
- **T6** `api.rugcheck.xyz` (including `/swagger`): fetch a report at migration +0 s, +5 s and +30 s. Check availability, staleness, latency, and the insider fields.
- **T7** `api.gopluslabs.io` and `gopluslabs.io`: `/api/v1/solana/token_security?contract_addresses=<mint>` on brand-new coins. Check coverage and CU cost.
- **T8** `public-api.birdeye.so` and `docs.birdeye.so` (compute-unit cost page): `token_security` latency and CU cost.
- **T9** `data.solanatracker.io` and `pump.fun/docs/mayhem-mode`: the risk object and its scale direction on new coins; how to identify the Mayhem agent wallet.
- **T10** Historical data (provider chosen by the data team): replay one week of graduations, compute every check at the gate, label outcomes (e.g. −90% within 1 h), and report each check's catch rate and false-alarm rate, ours vs each vendor's.
- **T11** `bundles.jito.wtf`: run the bundle lookup on 50 create transactions. Check hit rate and rate limits.

Research limits this session: WebFetch failed for api.rugcheck.xyz, gopluslabs.io, docs.birdeye.so, www.helius.dev, arxiv.org and zazza123.github.io. Only raw.githubusercontent.com loaded. The web-search budget ran out before checking whether legacy `create` coins have null authorities (folded into T1).

## Sources
- S1 [VERIFIED-DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/PUMP_PROGRAM_README.md
- S2 [VERIFIED-DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/instructions/COIN_CREATION.md
- S3 [VERIFIED-DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/PUMP_SWAP_README.md
- S4 [VERIFIED-DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/PUMP_CREATOR_FEE_README.md
- S5 [VERIFIED-DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/SYNTHETIC_MIGRATION.md
- S6 [VERIFIED-DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/README.md
- S7 [VERIFIED-SEARCH] https://intercom.help/pumpfun-web/en/articles/11002417-liquidity-on-pumpswap
- S8 [VERIFIED-SEARCH] https://pump.fun/docs/mayhem-mode ; https://www.theblock.co/post/379285/pump-funs-new-mayhem-mode-fails-boost-token-launches-revenue
- S9 [VERIFIED-SEARCH] https://www.helius.dev/docs/rpc/guides/gettokenlargestaccounts
- S10 [VERIFIED-SEARCH] https://www.helius.dev/pricing ; https://www.helius.dev/docs/billing/plans ; https://dappatlas.com/projects/helius/
- S11 [VERIFIED-SEARCH] https://www.helius.dev/docs/wallet-api/funded-by
- S12 [VERIFIED-DOC, third-party client] https://raw.githubusercontent.com/weeaa/jito-go/main/api/api.go ; [VERIFIED-SEARCH] https://www.quicknode.com/docs/solana/lil-jit-jito-bundles
- S13 [VERIFIED-SEARCH] https://rugcheck.xyz/api ; https://fluxrpc.com/rugcheck/ ; https://zazza123.github.io/cyhole/interactions/rugcheck/index.html
- S14 [VERIFIED-SEARCH] https://gopluslabs.io/en/security-api ; https://docs.gopluslabs.io/ ; https://pkg.go.dev/github.com/GoPlusSecurity/goplus-sdk-go/pkg/gen/client/token_security_api_for_solana_beta
- S15 [VERIFIED-SEARCH] https://docs.birdeye.so/docs/security-data ; https://docs.birdeye.so/reference/birdeye-api-getting-started
- S16 [VERIFIED-SEARCH] https://docs.solanatracker.io/data-api/risk ; https://www.zshare.net/best-solana-api-2026-the-top-data-apis-for-builders/
- S17 [VERIFIED-SEARCH] https://docs.bubblemaps.io/
- S18 [VERIFIED-SEARCH] https://solsniffer.gitbook.io/solsniffer-user-guide/product-snif-tokens/token-sniffer
- S19 [VERIFIED-SEARCH] https://docs.raydium.io/raydium/build/resources/token-2022-support ; https://cointelegraph.com/news/new-solana-scam-burn-tokens-from-inside-sol-wallets
- S20 [VERIFIED-SEARCH] https://docs.webacy.com/reference/what-is-bundling ; https://www.solanatracker.io/blog/bundlers
- S21 [VERIFIED-SEARCH] https://pumpfundata.com/blog/pumpfun-graduation-rate-analysis ; https://solanacompass.com/news/pumpfun-launched-42000-tokens-in-one-day-fewer-than-2-will-ever-reach-a-dex
- S22 [VERIFIED-SEARCH] https://arxiv.org/pdf/2608.20271
- S23 [VERIFIED-SEARCH] https://github.com/topics/solanabot
