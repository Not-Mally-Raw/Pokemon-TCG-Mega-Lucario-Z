# PTCG Agent — Next Steps & Execution Roadmap

> **Status**: Step 1 (Patch 5 Macro-Intents + Decision Entropy) is complete and verified in `main.py`. Step 0 is currently user-blocked on Kaggle.

---

## 1. Hard Dependency Chain (Why Order Matters)

```
Phase A / Step 0 (Capture real observation on Kaggle)
        │
        ├──► Confirms attackId / energies field formats
        │          │
        │          ▼
        ├──► Phase A / Step 2 (Fill StateEncoder 84-dim placeholders:
        │     weakness/resistance, AttackPlan threat, bench HP)
        │
        └──► Unblocks real game_log.jsonl accumulation
                   │
                   ▼
            Phase B / Step 3 (Train ValueNet: Leaky ReLU + AdamW + 5-fold Bagging)
                   │
                   ▼
            Wire tie-breaker into main.py (resolve_with_ensemble)
                   │
                   ▼
            Phase C (Non-regression gate: N>=30 matches, Wilson lower bound >= 0.55)
                   │
                   ▼
            Lock Submission (Aug 16) ──► Report Phase (Draft 2k-word Strategy Paper)
```

Nothing after Step 0 is trustworthy before it — this is why every prior plan repeats it as **the blocker**.

---

## 2. Step 0 (User-Blocked): Real Observation Capture on Kaggle

### Objective
Capture raw observation JSON objects from a live game on the Kaggle harness to verify unconfirmed wire assumptions.

### Unverified Assumptions to Settle:
1. Does `attackId` index locally (`0`, `1`) into the active Pokémon's attack array, or is it a global database ID?
2. Does `energies` arrive as a list of raw integers (e.g. `[1, 1, 6]`) or as enum strings (e.g. `["FIGHTING", "COLORLESS"]`)?
3. Is `EVOLVE` area representation consistently `AreaType.ACTIVE` / `AreaType.HAND`?

### Execution Instructions:
1. Open Kaggle notebook environment with `cg.api` installed.
2. Insert temporary print logging in `agent()`:
   ```python
   print(json.dumps(observation, default=str))
   ```
3. Run 1 match and copy raw JSON outputs for a MAIN-phase turn and an ATTACK-phase turn.
4. Inspect field types against `to_observation_class()`.

---

## 3. Step 2: Populate Real 84-Dimensional State Vector

### Objective
Replace the 75 placeholder dimensions in `StateEncoder.encode()` with verified game features once Step 0 provides wire format confirmation.

### Feature Mapping Table (84 Dimensions):

| Feature Block | Dimensions | Calculation / Source |
|---|---|---|
| Active HP Ratios | 0 - 1 | $\text{HP} / \text{maxHP}$ for self & opponent active Pokémon |
| Board Counts (Normalized) | 2 - 7 | Self & opp bench count (/5), hand size (/10), deck count (/60) |
| Prize Differential | 8 - 10 | Self prizes (/6), opp prizes (/6), prize delta $(\text{opp} - \text{self})/6$ |
| Active Energy Counts | 11 - 16 | Energy counts by type (Fighting, Colorless, Psychic, Fire, Water, Lightning) |
| Type Matchup Booleans | 17 - 20 | Self weakness/resistance vs opp active type, opp weakness/resistance vs self active |
| AttackPlan Threat Level | 21 - 24 | Self best damage / opp HP, KO feasibility (0/1), opp threat / self HP, opp KO threat (0/1) |
| Bench HP Ratios | 25 - 29 | $\text{HP} / \text{maxHP}$ for 5 self bench slots |
| Hand Composition Summary | 30 - 35 | Count of Supporters, Items, Tools, Energies, Evolution cards in hand |
| Reserved / Padding | 36 - 83 | Explicitly set to $0.0$ (no unindexed dimensions) |

---

## 4. Step 3: Train Value Net (Approved Subset)

### Approved Upgrades:
1. **Leaky ReLU Activation**: Replace ReLU with $\text{LeakyReLU}(x) = \max(0.01x, x)$ in `ValueNet.forward()` and `ValueNet.backward()`. Prevents dying units with a trivially correct derivative.
2. **AdamW Optimizer**: Replace SGD+momentum with decoupled weight decay (`AdamWOptimizer` with $\text{lr}=10^{-3}, \text{wd}=10^{-4}$).
3. **5-Fold Game-Level Bagging**: Train 5 separate `ValueNet` instances on bootstrap-resampled sets of games (`bootstrap_game_resample` grouped by `game_id`).
4. **Uncertainty-Gated Ensemble Tie-Breaker**: Implement `resolve_with_ensemble()`:
   ```python
   def resolve_with_ensemble(scored_options, nets, state_fn, tau=0.1):
       # Override heuristic ONLY if:
       # (a) contenders are within ±500 margin, AND
       # (b) ensemble std(ŷ) <= tau (models agree)
       ...
   ```

### Parked Upgrades (Hold List):
- **TD($\lambda$) Blended Target**: Requires target-network freezing infrastructure; parked until self-play volume scales.
- **SGDR Cosine Restarts**: Parked to keep ensemble size predictable ($k=5$ bagged models).
- **Snapshot Ensembling**: Parked to avoid managing dual-axis ensembles.
- **Temperature Scaling**: Parked until $>100$ real self-play matches accumulate.

---

## 5. Phase C: Non-Regression Elo Gate

Before promoting any new model version to Kaggle submission:
1. Run $n \ge 30$ matches against the previous baseline version.
2. Compute 95% Wilson score interval:
   $$\text{Lower Bound} = \frac{\hat{p} + \frac{z^2}{2n} - z \sqrt{\frac{\hat{p}(1-\hat{p})}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}, \quad z=1.96$$
3. Promote **only if** $\text{Lower Bound} \ge 0.55$. (If raw win rate is 60% at $n=30$, lower bound is 42.3% $\rightarrow$ **HOLD**).

---

## 6. Report Phase: Strategy Track Written Report

Draft 2,000-word report for Strategy Category submission (due Sept 13) covering 4 citable research claims:
1. **Neuro-Symbolic Architecture**: Symbolic engine makes all deterministic choices; neural ensemble acts as uncertainty-gated tie-breaker.
2. **Engine-Native Search Substrate**: Utilizing native `cg.search_begin` / `cg.search_step` lookahead primitives.
3. **Adversarially Verified Parser**: Ground-truth validation against primary C++ bindings.
4. **Single-Archetype Specialist Hypothesis**: Proving depth over breadth on a fixed deck (Mega Lucario ex) maximizes Elo per engineering-hour.
