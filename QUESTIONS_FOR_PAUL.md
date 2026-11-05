# Questions for Paul

## In plain English
- The team now drives the strategy, so these are only the questions nobody else can answer: your money, your limits, your approvals, and a few accounts only you can create.
- **Every question has a safe default.** If you don't answer, we use the default and keep going. Nothing here can make the bot trade real money without your explicit "yes".
- The most important three are **Q1 (approve the design)**, **Q2 (monthly budget)** and **Q4–Q5 (bankroll and the most you'd lose)**.
- At the end is a **Setup checklist**: which accounts to create, where to put each key (never in chat), and which web domains to allow so we can run the tests that were blocked.

**Tags.** [VERIFIED-SEARCH] = seen in search results. [UNVERIFIED] = our estimate. The reasons behind each default are in `DESIGN.md` and `team-debate/round3/rulings.md`.

---

## A. Approvals

**Q1. Do you approve `DESIGN.md`?**
- *What it means:* approval lets the team write the signing code (kept switched off, paper by default). It does **not** switch on real money.
- **Default if you don't answer:** not approved. We build only read-only tools: the recorder, the research tools and a paper bot with no signing code.

**Q2. What is your monthly budget for running costs?** (data feeds, servers, AI)
- *Our estimate:* about **$250 a month** while recording and researching, about **$275** once the paper bot and guard run. The range is $213–604; every line that can grow has a hard cap.
- **Suggested:** a ceiling of **$300 a month**. We'd ask before going above it.
- **Default if you don't answer:** we spend nothing. Paid accounts can only be created by you, so we keep working with free tiers and saved test data until you decide.

**Q3. What is the most you'll spend on research before an edge is shown?**
- **Suggested:** about **$750**, roughly 3 months of expected bills. After that the stop rule applies (DESIGN.md §8).
- **Default:** $750. At the 3-month checkpoint, if no rule has passed the paper gate, we stop all paid services and write a final report.

## B. Money and risk (only matters if you ever want real money)

**Q4. How much SOL would you put in the bankroll for live trading?**
- *Why it matters:* each bet must be at least 0.25 SOL to cover its own fees, and at most 1% of the bankroll for safety. So live trading needs **at least 25 SOL**. 50 SOL lets the sizing ideas work and lowers the break-even (DESIGN.md §5c).
- **Default:** **paper only.** No bankroll and no live trading.

**Q5. What is the most you are willing to lose, in SOL and in dollars (your "tuition budget")?**
- *What a real-money test could cost at 25 SOL:*
  - the drawdown stop halts live trading after a 20% fall (**5 SOL**);
  - plus the optional canary (**1 SOL**);
  - plus bills of about **$275 a month**.

  Theft is bounded separately by the hot wallet (about 3.3 SOL), and only if the guard computer itself is hacked.
- **Suggested, if you want to try live at all:** 6 SOL plus 3 months of bills.
- **Default:** **0**, meaning paper only.

**Q6. Would you allow a small "canary" test with real money once a rule passes on paper?**
- *What it is:* about 50 trades at 0.1 SOL, with a fixed budget (default **1 SOL** including fees). It only *measures* how real fills differ from paper. It's not meant to earn, and it doesn't need the 25 SOL bankroll.
- **Default:** **no canary.** We stay on paper and ask again when a rule passes.

## C. Safety choices only you can make

**Q7. In an emergency where Pump.fun lets people sell only through its own website, should the trading wallet be exportable to a phone wallet?**
- *The trade-off:* Amazon's key vault (our choice) can never export the key, which is safest against theft. But it means that in a "website-only" emergency, open positions wait (at most 3% of the bankroll). An exportable wallet needs a different provider (Privy), the key becomes a standing theft target, and the wallet must be retired after any export.
- **Default:** **no export.** Positions wait.

**Q8. The daily buying limit (only matters for real money).**
- *The trade-off:* the guard stops buying after **10% of the bankroll in 24 hours** (10 small bets). That is enough for the strategy to pay its way. The honest cost: if the bot's main server were hacked, the worst day could lose about that much (10%) on coins an attacker picked. A tighter 6% limit is safer but pushes the break-even from ~7% to ~10% per trade.
- **Default:** **10% of the bankroll per day.**

**Q9. Confirm we must never create a PumpPortal account key.**
- *Why:* their key comes bundled with a wallet key that *they* generate. We'd only use their free, keyless feed as a backup alarm, or not at all.
- **Default:** **never create one.**

**Q10. May we switch on Helius "autoscaling" with a $25 a month cap?** (from Phase 3)
- *Why:* it guarantees the selling side never runs out of data credits in a busy month. The cap means it can never cost more than $25 extra.
- **Default:** **off.** We then use stricter internal limits (optional data jobs stop earlier), and the selling side's reserve stays protected either way.

**Q11. What monthly spending limit should we set on the Claude (Anthropic) API?**
- *Why:* AI is used for overnight research and for reading Pump.fun's rule changes. The expected cost is about $40 a month.
- **Default:** a hard limit of **$75 a month**, set in the Anthropic Console.

**Q12. "Racing" wallet: never, unless the data says so and you agree?**
- *Background:* if the data ever proves that racing at the moment of graduation pays, it would need a separate small wallet (1–2 bets) whose key sits on a fast server. We'd treat that money as already lost if hacked.
- **Default:** **never.**

## D. Your preferences

**Q13. How should urgent alerts reach you, and are there quiet hours?** For example: the guard is down, selling is disabled, or the drawdown stop tripped.
- **Default:** a phone push-notification app, any hour, for money-safety alerts only. Everything else goes in the daily summary file (`reports/daily/`). Before live, we expect at most about one phone alert a week.

**Q14. Do you have any "never do" rules of your own?** For example: never hold overnight, never trade a certain coin type, never trade at certain hours.
- **Default:** none. The team sets and tests the rules.

**Q15. Are there wallets you already track** (influencers, known scammers, traders you trust) that we should add to our watch lists? We use them only as warning signs, never to copy trades.
- **Default:** public seed lists only.

**Q16. Are you happy with the stop checkpoints** in DESIGN.md §8?
- Week 4: recorder-only mode if nothing looks promising.
- Month 3: full stop if no rule passes paper.
- Two drawdown-stop trips end live trading.
- **Default:** yes, as written.

**Q17. May we spend about $10–20 once on an X (Twitter) history test?** It shows whether early posting patterns predict anything. If it passes, ongoing X data would be capped at $1.50 a day (about $45 a month).
- **Default:** **no X data.** Social signals stay on-chain only, at $0.

---

## Setup checklist for Paul
**Golden rules:**
1. **Never paste any key, password or seed phrase into the chat.**
2. **No wallet key or seed phrase ever goes anywhere in this environment.** The trading key will only ever be created inside Amazon's key vault, by you, in Phase 4.
3. **None of the keys below can move money or touch a wallet.** They are data, AI and server-access keys only.

When you've done a step, just tell us "done": no values, no screenshots of keys.

### Step 1: Allow the web domains (so we can run the blocked tests)
1. In this Claude Code session, click the **cloud environment's name in the session's title bar** (the environment menu).
2. Click **Edit**.
3. Open **Network access**.
4. Go to **Allowed domains**.
5. Add the domains from **List 1** below, one per line or one at a time, as the screen allows.
6. Click **Save**, then start a new session or tell us, so the change takes effect.
7. Add **List 2** and **List 3** later, when we ask at the start of each phase. **List 4** is optional.

*Note [UNVERIFIED]: we couldn't see that screen from here, so the button names may differ slightly; pick the closest match. If wildcards such as `*.core.chainstack.com` aren't accepted, add the exact host shown in your Chainstack dashboard instead.*

### Step 2: Create these accounts and put each key in the environment settings
**Where keys go:**
1. Same menu as Step 1: the environment name → **Edit**.
2. Go to the **secrets or environment variables** section (whichever your screen shows).
3. Add the **name** exactly as written below, paste the value into the value box, and click **Save**.
4. Never type the value into the chat.

| When | Account (what you do) | Cost | Name to use in the environment settings |
|---|---|---|---|
| **Now (Phase 0)** | **Helius**: sign up at helius.dev on the free plan, then copy the API key from the dashboard | Free now; Developer $49/month from Phase 1 [VERIFIED-SEARCH helius.dev] | `HELIUS_API_KEY` |
| **Now (Phase 0)** | **Chainstack**: sign up at chainstack.com; choose the **Growth** plan and add the **Yellowstone gRPC** add-on (2 streams); create a Solana mainnet node and copy its gRPC endpoint, gRPC token and RPC URL | $49 + $49 = $98/month [VERIFIED-SEARCH chainstack.com]. We can wait until Phase 1 if you prefer | `CHAINSTACK_GRPC_ENDPOINT`, `CHAINSTACK_GRPC_TOKEN`, `CHAINSTACK_RPC_URL`. **Also add the gRPC host name to Allowed domains** |
| **Phase 1–2** | **Anthropic API**: in the Anthropic Console, create an API key and set a monthly spend limit (Q11, default $75) | ~$40/month expected | `ANTHROPIC_API_KEY` |
| **Phase 1** | **Bot server**: rent a Frankfurt server (about 4 CPUs, 8–16 GB memory, a 200 GB extra disk; **not Hetzner**, which has banned crypto use). We'll send click-by-click steps and the provider choice after test G7. Access works through a narrowly limited provider token, so no private login key ever passes through chat [UNVERIFIED: how narrowly each provider lets tokens be limited] | ~$24–120/month, expected ~$48 [UNVERIFIED] | `BOT_HOST_ADDRESS`, `BOT_HOST_PROVIDER_TOKEN`. Add the server's address to Allowed domains |
| **Phase 3** | **A separate Amazon Web Services (AWS) account** for the guard computer, protected by a **hardware security key** (for example a YubiKey) on the root login. Only you hold the root login. We send click-by-click steps | ~$25/month (guard + standby + alarms) | **None here.** The guard's own keys (including a second Helius key) live inside that AWS account, never in this environment, so the bot side can never reach them |
| **Phase 3** | **Helius**: create a second API key for the guard, and (if Q10 = yes) set autoscaling with a $25 cap in the Helius billing settings | $0–25/month | Put it **only** into the AWS account (steps provided), never here |
| **Phase 3** | **A phone alert app** (we'll name one after test G6) | $0–10/month | The alert address goes on the servers, not here |
| **Phase 4 (only if you approve the canary)** | **Create the trading key inside Amazon's key vault (KMS)** by following our steps; then send the canary budget from *your* wallet to the address it shows | The canary budget (default 1 SOL) | **None.** The key never leaves the key vault |
| **Before live (Phase 5)** | **A hardware wallet** (for example Ledger or Trezor) for the bankroll ("cold wallet"). Write its recovery words on paper only. **Never** type them into any computer or chat | ~$80–150 once [UNVERIFIED] | **None** |
| Optional (Q17 = yes) | **X developer account**, pay-per-use; buy $10–20 of credit; create a bearer token | $10–20 once | `X_BEARER_TOKEN` |
| Optional (only if the X test passes) | **twitterapi.io** and/or **SocialData**, prepaid | Capped at $1.50/day | `TWITTERAPI_IO_KEY`, `SOCIALDATA_API_KEY` |
| Optional (not needed by default) | **Dune** free account | $0 | `DUNE_API_KEY` |
| **Never** | A **PumpPortal** key (Q9), or any wallet private key or seed phrase anywhere | — | — |

### The consolidated list of domains to allow
Gathered from every "Tests to run once allowed" section in rounds 1–3. `raw.githubusercontent.com` already works.

**List 1: needed now (Phase 0 core tests)**
```
api.mainnet-beta.solana.com
mainnet.helius-rpc.com
api.helius.xyz
www.helius.dev
docs.helius.dev
sender.helius-rpc.com
<your Chainstack gRPC host, from the dashboard, e.g. something.core.chainstack.com>
chainstack.com
docs.chainstack.com
github.com
api.github.com
raw.githubusercontent.com
registry.npmjs.org
pumpportal.fun
bundles.jito.wtf
mainnet.block-engine.jito.wtf
docs.jito.wtf
explorer.jito.wtf
api.coingecko.com
solana.com
docs.anza.xyz
```

**List 2: Phase 1–2 (AI research, model download, history cross-checks)**
```
api.anthropic.com
platform.claude.com
artificialanalysis.ai
arxiv.org
huggingface.co
dune.com
api.dune.com
docs.dune.com
onchaindivers.substack.com
<the coin-metadata gateway host(s) - we'll name them after test A8>
<your bot server's address>
```

**List 3: Phase 3 (guard, key vault and sending tests)**
```
kms.eu-central-1.amazonaws.com
ec2.eu-central-1.amazonaws.com
ssm.eu-central-1.amazonaws.com
dynamodb.eu-central-1.amazonaws.com
iam.amazonaws.com
aws.amazon.com
docs.aws.amazon.com
health.aws.amazon.com
api.devnet.solana.com          (only after you approve a build)
use.temporal.xyz
dashboard.nozomi.temporal.xyz
status.helius.dev
status.chainstack.com
www.man7.org
www.vultr.com
www.digitalocean.com
<the alert service host - we'll name it after test G6>
```

**List 4: optional research (add only if you want these comparisons)**
```
# Jupiter (read-only price audits)
api.jup.ag
developers.jup.ag
dev.jup.ag
portal.jup.ag
# Other data vendors and archives
graphql.bitquery.io
bitquery.io
public-api.birdeye.so
docs.birdeye.so
data.solanatracker.io
docs.solanatracker.io
shyft.to
docs.shyft.to
files.old-faithful.net
docs.old-faithful.net
bigquery.googleapis.com
# Coin-safety score vendors
api.rugcheck.xyz
api.gopluslabs.io
gopluslabs.io
# Signer alternatives (comparison only)
api.turnkey.com
docs.turnkey.com
www.turnkey.com
api.privy.io
docs.privy.io
www.privy.io
status.privy.io
docs.bloxroute.com
# What rival trading apps show
gmgn.ai
axiom.trade
photon-sol.tinyastro.io
sharpe.ai
kolscan.io
pump.fun
frontend-api-v3.pump.fun        (research only, after reading the terms)
# Social data (only if Q17 = yes)
api.x.com
docs.x.com
console.x.com
developer.x.com
x.com
docs.x.ai
api.twitterapi.io
docs.twitterapi.io
api.socialdata.tools
docs.socialdata.tools
apify.com
api.apify.com
lunarcrush.com
lunarcrush.ai
kaito.ai
madeonsol.com
core.telegram.org
discord.com
```

*Host notes:* `photon-sol.tinyastro.io` and the Chainstack wildcard are [UNVERIFIED] names; we confirm them in Phase 0.
