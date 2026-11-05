# Changes needed in phase0/scripts from fee-model v1.1 (from execution-engineer, 2026-11-05)

See docs/fee-model.md v1.1 §7 (T6a/T6b), §9 and §10 for the full specs.

`p0/t6_select.py` (then re-freeze with a new seed):
1. Point `spec_source` at fee-model v1.1 §7, label the run "T6a", and mark which strata are core and which deferrable. Deferrable means only `tier_ge_2`, F-6063 and the multi-hop-between pairs.
2. New stratum `cpi` ≥ 50: trades whose `trade_inner_index` is not None.
3. Stratum F floors: 6004 ≥ 15 and 6040 ≥ 15, plus every 6063 found (≥ 10, deferrable). Stratum N: at least 15 buys and 15 sells within its 50.
4. P5 sub-strata: same-slot ≥ 50 (core), multi-hop-between ≥ 30 (deferrable), boost-between ≥ 30 (core), failed-between ≥ 20 (core). If AR-T1 finds failed transactions carrying events, ≥ 5 of the failed-between pairs must contain one.
5. P6 needs ≥ 20 transactions with no SetComputeUnitLimit.
6. The freeze file must also record the population definition and the SHA-256 of the audit pool list.

`p0/t6.py`:
7. Universe. The audit list is mandatory. Using the withdraw-authority fallback means P7 fails, not just a label, unless the lead and red-team accept that scan as independent. The trading population filter is wSOL only; default-key and Token-2022-native pools go to the exclusion report. SOL_LIKE_QUOTES stays for pricing.
8. Same-slot order. Call getBlock(slot, {transactionDetails:"signatures", maxSupportedTransactionVersion:0, rewards:false}) for every slot with ≥ 2 transactions on a sampled pool. Order by that index, use the balance chain as a witness, and count these pairs in P5. Remove the "reported, not counted" skip.
9. Pair builder (around line 372, which currently skips failed entries). Keep the skipped failed transactions as "between" items and assert they change nothing (P5 d). Allow multi_hop_swap between: the model predicts the pool leg, taking its input from the previous hop's event only when that hop is a bonding curve. Allow boost_buy_and_burn between: apply it from the BOOST transaction's post-balances plus its event, and reduce S by base_amount_burned. Compare the creator bucket and S too. Compare the protocol bucket only where it is known. Count anything not decidable, and never count it as a pass.
10. fail_prediction:
    - build the pre-state from the last successful state change before the failure in block order, same slot included, not "an earlier slot";
    - use the failed transaction's own meta.preTokenBalances as the vault witness (FC10);
    - attribute the failure through PumpSwap's own log line "Program pAMMBay… failed: custom program error: 0x1774 / 0x1798 / 0x17af", never by number alone; skip truncated logs;
    - 6063: evaluate only where the protocol bucket can be rebuilt (never-boosted pools: pf = −vqr − cf, or a full replay); otherwise mark it not decidable and defer it to T6b.
11. New P8: one outcome tally over F, N and every scored success, required at 100%.
12. network_fee_check: stop excluding transactions that set a price but no limit.
    - Default limit = 200,000 × top-level non-builtin instructions + 3,000 × top-level builtin instructions (compute-budget instructions count as builtin), capped at 1,400,000.
    - Migrated builtins count at 200,000 once their gate is active. Take the builtin list from Agave's builtins-default-costs, and report any transaction whose class is unknown.
    - Cap requested limits at 1,400,000.
13. P9(a): continuity() currently returns None on QuoteRefused, which silently drops the pair. Count a refusal on any audit-sampled U0 trade as a failure.
14. Result report: show core and deferred strata separately. T6a can pass with a deferrable stratum short, never with a core one short.

`tests/`:
15. P9(b) hostile fixtures:
    - a failed-transaction JSON with a complete BuyEvent inner instruction: decode_trades returns [], the event is tagged FAILED_TX_EVENT, and state is unchanged;
    - an event-shaped inner instruction from a non-PumpSwap program, and one that isn't a direct child of a PumpSwap instruction: both ignored;
    - unit tests for the default-limit formula and the 6063 "not decidable" path.

`p0/budget.py`:
16. The A09 cap of 5,000 is probably too low now. The extra cost comes from getBlock per busy slot, extra failed-transaction fetches to reach 15 + 15 attributable failures, and the between-pairs. Suggest about 8,000 and measuring; the Helius credit cost of getBlock isn't verified.

Also:
- The test-plan owner should add rows FM-T1, FM-T2, AR-T1 and FC10 (fee-model §10).
- T6b belongs to Phase 1 recorder code, not phase0/scripts.
- tier_a/core.py and trades.py already skip failed transactions before reading events. Keep that rule for every new consumer, because pump.events_in_tx and program_instructions don't check for failure themselves.
