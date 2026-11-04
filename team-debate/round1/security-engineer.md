# Round 1: Security engineer proposal (wallets, keys, signer guardrails, hosting)

**In plain English (for Paul)**
- Your main savings stay on a hardware wallet that never touches the bot's server. The bot only ever gets a small "hot" wallet, holding an amount you'd be OK losing completely. You top it up yourself, by hand.
- The bot is never allowed to hold the key that can "send money anywhere". A separate "signer" (the part that approves each transaction) checks every trade against fixed rules: only approved exchanges, a maximum per trade, a maximum per day, and money can only ever go back to *your* savings wallet. The AI cannot change those rules.
- If the server is hacked, the most you can lose is what's in the hot wallet. There's a 10-step checklist below for what you click if that happens.
- While we're paper trading (the default), no real wallet or key exists at all.

Tags: [VERIFIED-DOC] = I read the primary source this session. [VERIFIED-SEARCH] = I only saw it in search results. [UNVERIFIED] = from memory or inference, with a test to confirm it. In this session WebFetch was blocked for `www.turnkey.com`, `docs.turnkey.com` and `aws.amazon.com`. It worked for `raw.githubusercontent.com`.

---

## 1. Wallet structure

| Wallet | Who holds the key | What's in it | Rules |
|---|---|---|---|
| **Cold (savings) wallet** | Paul only, on a hardware wallet. The seed phrase (the master backup words) is written on paper or metal, and is never photographed or typed into a computer. | The bankroll | Never on the server. Never connected to the bot. |
| **Hot trading wallet** | The signer (see section 2). Never a file the bot can read. | **A capped amount**: SOL plus whatever coins the bot currently holds. Paul sets the cap. | Topped up **only by Paul, by hand**, from cold. Nothing is ever automatic from cold to hot, because cold is never online. |
| **Optional profit sweep** | Signer | — | When the hot balance goes above cap + buffer, the extra goes back to cold. The cold address is **fixed inside the signer's policy**, so the server cannot change it. |

- **Max loss if the hot key is stolen:** everything in the hot wallet, meaning its SOL **plus the value of open positions**. Drains like this take seconds, not minutes. In the Bloom bot incident, 48 wallets lost about $953K in 94 seconds [VERIFIED-SEARCH](https://www.cryptometer.io/news/bloom-trading-bot-hack-drains-953k-from-48-solana-wallets-in-just-94-seconds/). So the cap is the real protection. Detecting the attack and reacting comes too late to save that money.
- **Max loss if the server is taken over but the key is NOT stolen** (option C below): the attacker can only make trades the policy allows. Their best move is to make the bot buy a coin *they* created, at an inflated price. A list of approved programs doesn't stop this, so per-trade and per-day caps are enforced in the signer as well as in the bot. Loss ≤ min(hot cap, daily spend cap) until Paul hits STOP.
- When moving money, Paul copies the cold address from a saved contact, **never from transaction history**. In "address poisoning", scammers plant lookalike addresses in your history: Bitquery reports about 4.5M Solana wallets targeted over 11 months [VERIFIED-SEARCH](https://info.solscan.io/address-poisoning-on-solana) [VERIFIED-SEARCH](https://pro.edgex.exchange/en-US/news/article/fake-payment-addresses-4-5-million-solana-wallets).

## 2. Key storage options

| Option | Safety if server is hacked | $/month | Cost per trade (buy+sell = 2 signatures) | Signing speed | Build difficulty |
|---|---|---|---|---|---|
| **A. Encrypted key file, passphrase typed at boot** (key lives in memory) | **Low.** Root access to the running server can read memory and steal the key. With a plain file it's worse: Solana's own key files are *unencrypted* and "anyone with access to this file" controls the funds [VERIFIED-SEARCH](https://docs.anza.xyz/cli/wallets/file-system). No rules exist outside the server. | $0 | $0 | Fastest, under 1 ms [UNVERIFIED: time 1,000 local signatures] | Easy. But after any reboot the bot is down until Paul types the passphrase. |
| **B. Cloud KMS** (a cloud key vault that signs for you: AWS KMS has supported Ed25519, Solana's key type, since Nov 2025 [VERIFIED-SEARCH](https://aws.amazon.com/about-aws/whats-new/2025/11/aws-kms-edwards-curve-digital-signature-algorithm/); Google Cloud has `EC_SIGN_ED25519` [VERIFIED-SEARCH](https://docs.datadoghq.com/infrastructure/resource_catalog/gcp_cloudkms_crypto_key_version)) | **Medium.** The key can't be stolen. But KMS doesn't understand Solana, so a hacked server can still get *any* transaction signed. Every signature is logged (CloudTrail) and the key can be switched off instantly (DisableKey) [VERIFIED-SEARCH](https://docs.aws.amazon.com/kms/latest/developerguide/ct-disablekey.html). | About $1 per key [VERIFIED-SEARCH](https://aws.amazon.com/kms/pricing/) | $0.15 per 10K signatures, so about $0.00003 per trade [VERIFIED-SEARCH](https://aws.amazon.com/kms/pricing/) | One network round trip. A user reported 25–250 ms (anecdote) [VERIFIED-SEARCH](https://repost.aws/questions/QUPEubdAqrSnSLm-38Vjyqpw/kms-signing-performance-with-asymmetric-ecc-nist-p256-key-is-slow). Default limit is 1,000 ECC signs/s [VERIFIED-SEARCH](https://docs.aws.amazon.com/kms/latest/developerguide/requests-per-second.html). | Medium. Needs an AWS account and access rules. The official Solana Keychain library supports it [VERIFIED-SEARCH](https://solana.com/docs/tools/keychain). |
| **C1. Turnkey** (hosted wallet whose keys sit in sealed hardware, AWS Nitro enclaves [VERIFIED-SEARCH](https://docs.turnkey.com/security/secure-enclaves), with a Solana rule engine) | **High.** It reads each Solana transaction and can enforce a list of allowed programs and allowed SOL/token recipients *outside our server* [VERIFIED-SEARCH](https://turnkey.com/blog/introducing-solana-policy-engine) [VERIFIED-SEARCH](https://www.turnkey.com/blog/jupiter-solana-swap-policies). Catch 1: its transfer rules only see *top-level* transfers, not transfers made inside other programs [VERIFIED-SEARCH](https://github.com/tkhq/docs/pull/480/files). Catch 2: "root" users bypass every policy [VERIFIED-SEARCH](https://docs.turnkey.com/concepts/policies/overview), so the server must **never** be a root user. | $0 pay-as-you-go, or $99 Pro [VERIFIED-SEARCH](https://www.turnkey.com/pricing) | **$0.20** ($0.10/signature after 25 free). Pro is $0.05/signature. | Turnkey claims under 100 ms; one listing says 50–100 ms [VERIFIED-SEARCH](https://solanacompass.com/projects/turnkey) | Medium. Official Keychain support [VERIFIED-SEARCH](https://solana.com/docs/tools/keychain). |
| **C2. Privy server wallets** (same idea) | **High (if tests pass).** It has a policy engine with Solana conditions based on the program instruction [VERIFIED-SEARCH](https://docs.privy.io/guide/server-wallets/policies). I could not confirm that it can limit recipients. | $0 Developer plan [VERIFIED-SEARCH](https://www.privy.io/pricing) | **$0** up to 50K signatures/month. The overage rate isn't published ("as low as $0.001" on Enterprise) [VERIFIED-SEARCH](https://www.privy.io/pricing). | Unknown [UNVERIFIED: test below] | Medium. Official Keychain support [VERIFIED-SEARCH](https://solana.com/docs/tools/keychain). |
| **D. Our own signer on a separate small server** | Medium-high. It protects against a hack of the bot, but not a hack of the signer server itself. The rules are code *we* write, so bugs are our risk. | +$5–15 for a second server [VERIFIED-SEARCH, see §6] | $0 | About 1 ms on a private network [UNVERIFIED] | Hardest. The policy code needs careful review. |

At 600 round trips a month, Turnkey costs about $120/month. Privy costs $0, and KMS costs about $1 [UNVERIFIED arithmetic based on the prices above]. Signing adds latency only once per trade. A Solana slot (the network's time step) lasts about 400 ms [UNVERIFIED], so 50–100 ms matters but doesn't decide things.

## 3. Signer guardrails (fixed code, outside the AI; the AI only *suggests* trades)

1. **Approved programs only:** PumpSwap AMM (`pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA`), the Pump bonding curve (`6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P`) [VERIFIED-SEARCH](https://docs.bitquery.io/docs/blockchain/Solana/Pumpfun/pump-swap-api/), Jupiter (copy the ID from Jupiter's official docs, not from memory [UNVERIFIED]), plus the compute-budget, associated-token-account and token programs (for the wallet's *own* accounts only). Pump changes its programs often (see brief), so this list gets updated by hand after Paul reviews the change.
2. **Max SOL per transaction and max per day** (rolling 24 h), plus a cap on trades per day and on open positions. Once the bot is built, the signer measures these from the balance changes it predicts before sending. Nothing gets tested against real transactions during design. It never trusts what the bot *says* the trade is. Hosted policy engines judge one transaction at a time [UNVERIFIED for daily totals], so the daily cap lives in our signer, and the hot-wallet cap is the final backstop.
3. **No SOL or token transfers to anyone** except: the cold wallet (sweep), known Jito tip accounts (a small fee sent to get a transaction included faster) up to a tip cap, and the swap pool itself. **Swap output must land in a token account the hot wallet owns.** This needs our own check, because hosted transfer rules miss transfers made inside other programs (see C1).
4. **Always refuse:** `Approve`/`ApproveChecked` (lets someone else spend our tokens; this is how drainers work [VERIFIED-DOC](https://solana.com/docs/tokens/basics/revoke-delegate)), `SetAuthority`, System `Assign` (changes who owns an account), any "close account" that sends the leftover deposit anywhere but the hot wallet, and durable-nonce instructions (they make a signed transaction usable *later*). Also refuse any transaction with an extra signer or a different fee payer.
5. **Unpack "lookup tables" before checking.** Solana transactions can hide account addresses in lookup tables (address lists stored on-chain), so rules must check the real, resolved list [VERIFIED-SEARCH](https://solana.com/docs/core/transactions/versioned-transactions).
6. **Coin screening before buying** (shared with the risk agent): reject Token-2022 coins (Solana's newer token standard with optional extra features) that have a *permanent delegate*, which lets the creator move or burn your tokens [VERIFIED-SEARCH](https://solana.com/docs/tokens/extensions/permanent-delegate) [VERIFIED-SEARCH](https://cointelegraph.com/news/new-solana-scam-burn-tokens-from-inside-sol-wallets). Also reject *transfer hooks* (can block sells [VERIFIED-SEARCH](https://solana.com/docs/tokens/extensions/transfer-hook-integration.md)), freeze authority, and high transfer fees.
7. **Optional, later:** add a Lighthouse "assertion" instruction, so the transaction fails on-chain if balances end up different from what we expected [VERIFIED-DOC](https://raw.githubusercontent.com/jac0xb/lighthouse/main/README.md). Its README tells users to "conduct thorough testing and auditing" first, so it's not a launch dependency.
8. **One STOP switch** that pauses the bot *and* revokes the server's signing access.

## 4. Server compromise: what happens and Paul's checklist

**What an attacker can do:** steal API keys (and run up bills); read your strategy; ask the signer for trades (up to the caps); force bad buys into their own coin; and, with option A only, steal the key and empty the hot wallet in seconds. The AIXBT AI bot lost 55 ETH after an attacker got into its dashboard and fed it instructions [VERIFIED-SEARCH](https://www.theblock.co/post/346911/). Coin names, descriptions and tweets that reach the AI are attack text too. **The AI can never raise a limit.**

**How we detect it:** the signer alerts Paul on *every* refused transaction. A separate balance watcher (running on another provider) alerts on any outgoing transfer that isn't to cold. We also want alerts for server logins and billing spikes, and a daily summary.

**Paul's response checklist (click by click):**
1. **Cut signing first:** log in to the wallet provider's dashboard with your passkey → API keys → **delete the server's key**. (With KMS: AWS console → KMS → the key → **Disable**.)
2. **Power off** the server in the hosting dashboard (Power → Off). **Do not delete it**; the disk is evidence.
3. **Move funds:** in the wallet dashboard (root access via your passkey) → hot wallet → **Send all SOL** to your cold address, **picked from your saved contacts**. Sell or send any coins it still holds.
4. On your hardware wallet, **confirm the funds arrived.**
5. **Rotate every key:** RPC provider (Helius: dashboard → RPCs → Access Control; create a new key, then delete the old one [VERIFIED-SEARCH](https://www.helius.dev/docs/rpc/protect-your-keys.md)), Anthropic Console → API keys → delete, then the data APIs, X, GitHub, and the hosting password and 2FA.
6. Check the hot wallet for token approvals (should be none). Type the address of a revoke tool by hand; don't click links.
7. **Never reuse the old hot wallet.** Create a new one with fresh policies.
8. Rebuild the server **from scratch**, from a known-good version of the code. Never "clean" the old one.
9. Check every billing page for spending spikes.
10. Write down the times and what you saw, and send the notes to the team.

## 5. Supply chain (fake or poisoned software)

- **Real incidents:** `@solana/web3.js` 1.95.6/1.95.7 were backdoored to steal private keys (Dec 2024, about 5-hour window, about $164K lost) [VERIFIED-SEARCH](https://thehackernews.com/2024/12/researchers-uncover-backdoor-in-solanas.html). In Sept 2025, chalk/debug were hijacked to swap wallet addresses [VERIFIED-SEARCH](https://blog.checkpoint.com/crypto/the-great-npm-heist-september-2025/). Malicious npm/PyPI "Solana" packages emptied wallets (Jan 2025) [VERIFIED-SEARCH](https://thehackernews.com/2025/01/hackers-deploy-malicious-npm-packages.html). JFrog's "Solana FakeFix" found about 20 packages posing as MEV bots that ask for your key [VERIFIED-SEARCH](https://research.jfrog.com/post/solana-fakefix/). Fake "pumpfun bot" GitHub repos with inflated star counts stole keys [VERIFIED-SEARCH](https://cointelegraph.com/news/solana-trading-bot-github-malware-scam).
- **Controls:** a lockfile and exact versions, installed with `npm ci` / `--frozen-lockfile`. A **release-age cooldown** that refuses package versions newer than N days (pnpm 10.16+, npm 11.10+; pnpm 11 defaults to 24 h [VERIFIED-SEARCH](https://dev.to/douglasdemoura/protecting-your-nodejs-project-against-supply-chain-attacks-5984)); use **7 days for the signer**. Install scripts off by default. **The signer gets the smallest possible set of dependencies** and runs in a separate process from data ingestion. Use only official packages (Pump's are `@pump-fun/pump-sdk` and `@pump-fun/pump-swap-sdk` [VERIFIED-DOC](https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/README.md)). Never install "SDKs" from Telegram, forks or DMs. Run a dependency scanner in CI.
- **Malicious coins:** permanent delegate and transfer hooks (§3.6). **Fake metadata links:** fetch with size and time limits, never with credentials, never render them; treat the text as untrusted input to the AI [UNVERIFIED design rule].

## 6. Hosting options

| Option | Latency to RPC | Security | $/month | Reliability |
|---|---|---|---|---|
| **Small VPS / bare metal in Frankfurt or Amsterdam** (Vultr, Cherry Servers…) | Best. Germany and the Netherlands hold the most stake [VERIFIED-SEARCH](https://validators.solutions/en/validators/countries/). Helius has send endpoints in Frankfurt and Amsterdam [VERIFIED-SEARCH](https://www.helius.dev/docs/agents/mcp/skills/sender). | Good once hardened | VPS about $5–6 [VERIFIED-SEARCH](https://serverspace.us/about/blog/best-vps-providers-for-trading-bots-in-the-usa-2026-top-low-latency-vps-hosting/); Cherry dedicated about $53–158 [VERIFIED-SEARCH](https://cybernews.com/best-web-hosting/cherry-servers-review/) | Good. **Avoid Hetzner:** in 2022 it banned crypto nodes, reportedly including trading apps [VERIFIED-SEARCH](https://www.hivelocity.net/blog/cloud-tos-crypto-when-your-validator-is-not-welcome/) |
| **Cloud VM (AWS Frankfurt)** | Good | Best tooling (access rules, logs, KMS, enclaves) | t4g.small about $14, c7g.medium about $30 [VERIFIED-SEARCH](https://cloudprice.net/aws/ec2/instances/t4g.small) [VERIFIED-SEARCH](https://www.doit.com/compute/spot/eu-central-1/c7g.medium) (plus data-transfer fees [UNVERIFIED]) | High |
| **Home machine** | Worst (home internet, wherever you are) [UNVERIFIED] | **Worst.** Shared with your browsing and email, the #1 way keys get stolen; a changing home IP breaks IP-locked keys | $0 extra | Worst. A power or internet cut means the bot can't sell. |

**Basic hardening:** login by SSH key only, a firewall, automatic security updates, no browser or email on the server, separate system users for the bot and the signer, and hardware-key 2FA on the hosting account.

## 7. API keys (data, RPC, AI)

- **Storage:** a secrets file readable only by the service's own system user, or the cloud provider's secret store. Never in git, logs, chat or AI prompts. Logs hide anything that looks like a key.
- **Scope:** one key per service per environment. Lock RPC keys to the server's IP (Helius supports allowed IPs/CIDRs and separate keys per environment [VERIFIED-SEARCH](https://www.helius.dev/docs/rpc/protect-your-keys.md)).
- **Spend caps:** a dedicated Anthropic workspace with a low monthly limit (Anthropic supports organization and workspace monthly limits; setting them through the API is early access [VERIFIED-SEARCH](https://platform.claude.com/docs/en/api/beta/organization/spend_limits.md); the Console UI path is [UNVERIFIED]). Fixed or prepaid data plans with overage switched off, plus cloud billing alerts.
- **Rotation:** every 90 days, and immediately on any suspicion (checklist step 5). Paul's email is the master key to everything, so protect it with a passkey or hardware key.

## 8. Recommendation

**Paper phase:** no key exists. **First live phase:** cold hardware wallet → manual top-ups → a **capped hot wallet in a hosted policy wallet (C)**. Paul holds root (passkey plus a backup hardware key). The server gets a non-root API key whose policy allows only the approved programs and only sends money back to cold. On top of that sits **our own signer guard** (§3: caps, daily limits, output-ownership check, lookup-table unpacking, refusal list) on a **Frankfurt or Amsterdam VPS or AWS VM**. Between Privy (free at our volume) and Turnkey (about $0.20 per trade, best-documented Solana rules), pick after the tests below. Fallback is KMS (B) plus our own guard. **Reject option A** for real money, and reject home hosting.

## 9. Open risks

- A hosted wallet outage means we **can't sell**. Paul's root access is the manual exit; we need a written "manual sell" procedure.
- Approved programs can still be abused with "buy my coin" trades. Only the caps limit this.
- The vendors' policy engines might not see transfers made inside other programs (confirmed for Turnkey), so our own output check is mandatory.
- Prices, latency and policy features are unverified (official pages were blocked this session).
- Pump keeps changing its programs, so the allowlist will break trades until a person updates it. That fails safe, but it's an outage.

## Tests to run once allowed (no funds, after Paul approves a build)

1. **Signing latency:** 100 sign-only calls, test key, dummy message, from a Frankfurt VM to `api.turnkey.com`, `api.privy.io`, `kms.eu-central-1.amazonaws.com`. Record p50/p99 (typical and worst-case times).
2. **Policy refusal (devnet, the test network):** a SOL transfer to a random address, `Approve`, `SetAuthority`, and a swap whose output goes to a foreign account must **all be refused** (`api.devnet.solana.com`, `docs.turnkey.com`, `docs.privy.io`).
3. **Re-verify prices:** `www.turnkey.com/pricing`, `www.privy.io/pricing`, `aws.amazon.com/kms/pricing`.
4. **Program IDs:** confirm against `dev.jup.ag` and Pump's IDL on `github.com/pump-fun/pump-public-docs`.
5. **Does Privy limit recipients?** Read `docs.privy.io/guide/server-wallets/policies` and confirm whether Solana policies can restrict SOL/SPL recipients.
