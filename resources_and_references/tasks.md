# PTCG Agent — Master Task Checklist

## Step -1: Blocking Bugfix & Parser Reconciliation (COMPLETED ✅)
- [x] Fix option index resolution bug: `_opt_index(opt, list_idx)` helper in `main.py`
- [x] Wrap `resolve_card_id()` and `choose()` with defensive `getattr()` attribute access
- [x] Guarantee option selection returns valid wire/array indices (`0 <= idx < len(options)`)
- [x] Update `PTCG_Baseline_Submission v2.ipynb` cell 4 & rebuild `submission.tar.gz` (10.2 KiB)
- [x] Verify: 6/6 unit tests pass clean

## Step 1: Ship Patch 5 (Options Relabeling + Entropy Telemetry)
- [x] Add `MACRO_INTENTS` dict to `main.py`
- [x] Add `macro_intent_for_score()` function
- [x] Add `decision_entropy()` function
- [x] Wire entropy + intent logging into `GameLogger.log()` call in `agent()`
- [x] Fix overlapping score ranges (`STABILIZE` before `POWER_UP`, `DEVELOP` 7000-8499)
- [x] Fix edge case: single-option decisions return 0.0 entropy
- [x] Verify code compilation & unit test suite (6/6 pass)
- [ ] Verify execution: entropy & intent fields appearing in real Kaggle `game_log.jsonl` (Pending Step 0)

## Step 0: Capture One Real Observation (USER-BLOCKED ⏳)
- [ ] User runs `main.py` on Kaggle against a real match
- [ ] Raw observation dict captured from at least one MAIN-phase and one ATTACK decision
- [ ] Confirm: `attackId` is local index or global ID
- [ ] Confirm: `energies` format (raw ints or enum strings)

## Step 2: Populate Real 84-Dimensional State Vector (GATED 🛑)
- [ ] Fill weakness/resistance booleans
- [ ] Fill AttackPlan threat scores
- [ ] Fill bench HP ratios
- [ ] Fill opponent hand size / deck count
- [ ] Fill remaining hand composition slots
- [ ] Verify: `build_state_vector()` returns >30 non-zero dims on real observation

## Step 3: Train Value Net (Approved Subset — GATED 🛑)
- [ ] Swap ReLU → Leaky ReLU ($\alpha=0.01$) in `ValueNet.forward/backward`
- [ ] Implement `AdamWOptimizer` replacing SGD+momentum
- [ ] Implement `bootstrap_game_resample(k=5)` at game level
- [ ] Implement `resolve_with_ensemble()` with uncertainty gate ($\tau=0.1$)
- [ ] Wire ensemble tie-break into `HeuristicEngine.choose()`
- [ ] Verify: existing tests pass
- [ ] Verify: ensemble produces different tie-break results from single-net

## Phase C: Non-Regression Gating & Submission
- [ ] Run $\ge 30$ matches against baseline
- [ ] Verify 95% Wilson score interval lower bound $\ge 0.55$
- [ ] Package final `submission.tar.gz` for Kaggle ladder submission

## Strategy Track Report (Due Sept 13)
- [ ] Outline 2,000-word paper structure
- [ ] Generate ablation figures comparing Heuristic vs. Ensemble tie-breaker
- [ ] Document single-archetype specialist hypothesis (Mega Lucario ex)
- [ ] Submit Strategy Category report on Kaggle
