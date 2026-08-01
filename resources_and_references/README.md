# 🏆 Pokémon TCG AI Battle — Mega Lucario ex Neuro-Symbolic Agent

Welcome to the central architectural guide and system documentation for the **Pokémon TCG AI Battle Agent**.

---

## 1. Project Architecture (System Design Patterns)

The agent is designed around a **Neuro-Symbolic Hybrid Architecture** combining deterministic domain rules with probabilistic value estimation.

```
                  ┌──────────────────────────────────────────────┐
                  │          Kaggle Match Observation            │
                  └──────────────────────┬───────────────────────┘
                                         │
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │       cg.api.to_observation_class()          │
                  └──────────────────────┬───────────────────────┘
                                         │
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │           compute_attack_plan()              │
                  │   - Weakness/Resistance Damage Calc          │
                  │   - Prize-Aware Target Valuation (3/2/1)     │
                  │   - Game-Winning KO Detection (50,000 pts)    │
                  └──────────────────────┬───────────────────────┘
                                         │
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │               score_option()                 │
                  │   - Macro-Intent Priority Classification     │
                  │   - Integer Priority Scoring Engine          │
                  └──────────────────────┬───────────────────────┘
                                         │
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │          resolve_with_ensemble()             │
                  │   - Heuristic Top Rank (Primary)             │
                  │   - ValueNet Tie-Break (±500 margin)         │
                  │   - Uncertainty Gate (std ≤ τ = 0.1)        │
                  └──────────────────────┬───────────────────────┘
                                         │
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │      Action Index List + Telemetry Log       │
                  └──────────────────────────────────────────────┘
```

### Core Design Patterns Applied:
1. **Neuro-Symbolic Hybrid Pattern**: Symbolic rule engine (`score_option`) executes all structural tactical decisions. Neural value network (`ValueNet`) acts strictly as a tie-breaker when heuristic scores are within ±500 points.
2. **Strategy / Priority Pattern**: Actions are scored numerically using hard-coded priority tiers (e.g. 50,000 for Game-Winning KO down to 100 for End Turn), allowing deterministic sorting and multi-select option selection.
3. **Data Mapper / Parser Pattern**: `to_observation_class()` converts unstructured Kaggle JSON dictionaries into strongly typed dataclasses (`Observation`, `Select`, `Option`, `Pokemon`, `PlayerState`).
4. **Options Framework Pattern** (Sutton, Precup & Singh 1999): Action scores map into 9 macro-intents (`LETHAL`, `AGGRO_KO`, `SETUP`, `ATTACK`, `DEVELOP`, `RESOURCE`, `POWER_UP`, `STABILIZE`, `PASS`) with formal initiation and termination criteria.
5. **Decorator Telemetry Pattern**: `GameLogger` intercepts state, action indices, decision entropy $H$, and macro-intent metadata to produce offline training logs (`game_log.jsonl`).

---

## 2. Stages & Agent Step Definitions

The development roadmap is structured into 4 sequential phases:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│     Phase A     │ ──► │     Phase B     │ ──► │     Phase C     │ ──► │  Report Phase   │
│ Verification &  │     │ Neural Upgrade  │     │ Non-Regression  │     │ Strategy Paper  │
│ Telemetry Setup │     │ & ValueNet Bag  │     │   Elo Gating    │     │   Submission    │
└─────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
```

- **Step 0 (Phase A - User Blocked)**: Capture one real game observation from the Kaggle harness to verify field names (`attackId`, `energies` representation).
- **Step 1 (Phase A - Complete)**: Implement Options Framework macro-intents (`MACRO_INTENTS`) and decision entropy telemetry (`decision_entropy`) in `main.py`.
- **Step 2 (Phase A - Pending Step 0)**: Fill the 75 placeholder dimensions in `StateEncoder` with verified game features.
- **Step 3 (Phase B - Scheduled)**: Upgrade `ValueNet` with Leaky ReLU ($\alpha=0.01$), `AdamWOptimizer`, 5-fold game-level bagging, and uncertainty-gated tie-breaking (`tau=0.1`).
- **Phase C (Validation)**: Execute non-regression matches ($n \ge 30$) requiring 95% Wilson confidence lower bound $\ge 0.55$ before submission promotion.
- **Report Phase (Strategy Track)**: Author 2,000-word strategy report detailing architecture, ablation studies, and decision explainability.

---

## 3. Flow of Data & Execution Cycle

```
Input JSON Dict ──► to_observation_class() ──► Typed Observation ──► compute_attack_plan()
                                                                           │
                                                                           ▼
Action Output ◄── GameLogger ◄── resolve_with_ensemble() ◄── score_option()
```

1. **Input Ingestion**: Kaggle environment passes raw `observation` dictionary to `agent(observation)`.
2. **Parsing**: `to_observation_class()` parses state into `Observation`. Setup phase returns 60-card deck list (`deck.csv`).
3. **Tactical Computation**: `compute_attack_plan()` computes effective damage considering weakness ($\times 2$) and resistance ($-20/-30$), evaluates KO feasibility, target prize value (3 for Mega ex, 2 for ex, 1 for Basic), and checks for game-winning KO conditions.
4. **Heuristic Scoring**: Each legal `Option` in `Select.options` is assigned an integer score by `score_option()`.
5. **Selection & Ranking**: Options sorted descending by score; top `maxCount` indices selected. Near-ties (within ±500) evaluated by `ValueNet` ensemble if confidence gate passes ($\text{std} \le 0.1$).
6. **Telemetry**: `GameLogger` records `(observation, actions, entropy, intent)` to `game_log.jsonl`.

---

## 4. Notebook Cell Breakdown (`PTCG_Baseline_Submission v2.ipynb`)

| Cell | Type | Purpose & Function |
|---|---|---|
| **Cell 0** | Markdown | Header, submission instructions, architecture summary table, and complete Heuristic Priority & Scoring Table (50,000 to -1,000). |
| **Cell 1** | Markdown | Section header: `1. Generate deck.csv`. |
| **Cell 2** | Code | `%%writefile deck.csv`: Generates the 60-card deck list for Mega Lucario ex (Card IDs: 677, 678, 333, 1121, 1182, 6, etc.). |
| **Cell 3** | Markdown | Section header: `2. Generate main.py`. |
| **Cell 4** | Code | `%%writefile main.py`: Generates the complete 502-line production python agent including `cg.api` imports, `AttackPlan`, `score_option`, `MACRO_INTENTS`, `decision_entropy`, `StateEncoder`, `NeuralWorker`, `GameLogger`, `HeuristicEngine`, and `agent()`. |
| **Cell 5** | Markdown | Section header: `3. Package Submission (submission.tar.gz)`. |
| **Cell 6** | Code | Python script creating `submission.tar.gz` containing `main.py`, `deck.csv`, and `cg/` package. Asserts size < 197.7 MiB. |
| **Cell 7** | Markdown | Section header: `4. Verification & Unit Tests`. |
| **Cell 8** | Code | Comprehensive test suite (Test 1: Deck validation, Test 2: Setup phase, Test 3: Game-winning KO 50k score, Test 4: Multi-select maxCount, Test 5: Tarball structure, Test 6: Patch 5 Macro-Intents & Decision Entropy). |

---

## 5. Summary of Key Algorithms & Design Elements

- **Damage Calculation**: Base damage $\times 2$ for weakness match; subtracts resistance ($-20/-30$).
- **Prize Target Valuation**: Mega ex = 3 prizes, ex = 2 prizes, Basic = 1 prize.
- **Decision Entropy**:
  $$H = -\sum_{i=1}^K p_i \log(p_i + 1e-12), \quad p_i = \text{softmax}(S_i / 1000.0)$$
- **Non-Regression Gate**: 95% Wilson score interval lower bound $\ge 0.55$ over $n \ge 30$ games.
- **Ensemble Tie-Breaker**: 5-fold game-level bagged `ValueNet` instances with Leaky ReLU ($\alpha=0.01$) and AdamW optimizer.

---

## 6. Current Status

- **`main.py`**: Fully operational (502 lines), native `cg.api` integrated, Patch 5 (Macro-Intents + Decision Entropy) live and verified.
- **`submission.tar.gz`**: Rebuilt (9.7 KiB), passes all size and structural checks.
- **`PTCG_Baseline_Submission v2.ipynb`**: 100% updated and verified against `main.py`.
- **Pending Blockers**: Step 0 real observation capture on Kaggle.
