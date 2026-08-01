# PTCG Agent — Implementation Plan v5 (Approved & Grounded)

> **Status: Living Technical Document.** Reflected against exact codebase state as of Jul 29, 2026.
> Incorporates parser reconciliation decision and defensive option index resolution fix.

---

## 1. Grounded Codebase Audit vs. Plan Tiers

| Step | Scope | Real Codebase Status | Status |
|---|---|---|---|
| **Step -1 (Blocking Bugfix)** | Option Index & Parser Fallback Fix | **SHIPPED ✅** — `_opt_index(opt, list_idx)` helper and defensive `getattr()` wrappers applied across `main.py` & `choose()`. Prevents invalid array index returns. | ✅ Complete |
| **Step 0 (Blocker)** | Real Observation Wire Capture | **PENDING USER ⏳** — Requires running `agent()` on Kaggle against a live match to print raw JSON and confirm `attackId` and `energies` types. | ⏳ Blocker |
| **Step 1** | Patch 5 (Options Framework + Telemetry) | **CODE COMPLETE 🛠️** — `MACRO_INTENTS`, `macro_intent_for_score()`, `decision_entropy()`, and `GameLogger` kwarg logging implemented in `main.py`. Execution verification pending Step 0. | 🛠️ Code-Complete |
| **Step 2** | StateEncoder 84-Dim Vector | **GATED 🛑** — `StateEncoder.encode()` currently returns zeros stub. Correctly held until Step 0 fields are verified. | 🛑 Gated |
| **Step 3** | ValueNet Upgrade (Leaky ReLU + AdamW + Bagging) | **GATED 🛑** — Correctly held until Step 2 features ship. | 🛑 Gated |

---

## 2. Parser Reconciliation Decision

- **Selected Architecture**: **Native `cg.api` with Fail-Safe Defensive Wrappers**.
- **Rationale**: Direct `cg.api.to_observation_class()` provides engine-native typing, but wire payloads can omit or format attributes unexpectedly. All property accesses (`opt.index`, `opt.card_id`, `in_play_index`) now pass through defensive helpers (`_opt_index`, `getattr`) with `list_idx` fallback to guarantee zero runtime crashes and valid option index returns.

---

## 3. Approved Execution Runbook & Sequence

### Priority 1: Step 0 (USER-BLOCKED)
Run 1 game on Kaggle, print raw `observation` JSON, and verify:
- `attackId` (local 0/1 array index vs global card ID)
- `energies` (raw int list vs enum name strings)

### Priority 2: Step 2 (StateEncoder Population)
Populate 75 placeholder dimensions in `build_state_vector()` using confirmed wire fields from Step 0.

### Priority 3: Step 3 (ValueNet Upgrade — Approved Subset)
- Leaky ReLU ($\alpha=0.01$) activation
- `AdamWOptimizer` decoupled weight decay
- 5-fold game-level bagging (`bootstrap_game_resample`)
- Uncertainty-gated ensemble tie-breaker (`resolve_with_ensemble` with $\tau=0.1$)

### Priority 4: Phase C Non-Regression Gate
Run $n \ge 30$ self-play matches requiring 95% Wilson confidence lower bound $\ge 0.55$.

### Priority 5: Strategy Track Report
Author 2,000-word strategy report covering 4 citable claims.

---

## 4. Explicit Hold List

| Parked Item | Unlock Condition |
|---|---|
| TD($\lambda$) Blended Target | Requires target-network periodic freezing infrastructure |
| SGDR Cosine Restarts | Parked to maintain predictable $k=5$ ensemble size |
| Dual-Axis Snapshot Ensembling | Parked to avoid multi-axis ensemble complexity |
| Temperature Scaling | Requires $>100$ real matches |
| GELU Activation | Replaced by Leaky ReLU due to tanh/exact-CDF gradient mismatch |
