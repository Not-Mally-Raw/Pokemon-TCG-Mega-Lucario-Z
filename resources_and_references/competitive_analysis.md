# PTCG AI Battle — Competitive Intelligence Report

> Last updated: 2026-07-24 | Sources: 5 Kaggle notebooks, 3 research papers, Kaggle forums

---

## 1. Notebook-by-Notebook Breakdown

### 1A. Beginner Guide (ichigoe) — Rule-Based Baseline ⭐ Most Relevant to Us
**Approach:** Pure heuristic, score-based option ranking. Zero ML.

| Component | Implementation |
|-----------|---------------|
| Parser | Uses `cg.api.to_observation_class()` — the engine's own typed parser |
| Card DB | `{c.cardId: c for c in cg.api.all_card_data()}` — engine-provided, not CSV |
| Decision | Score every option → sort descending → return top `maxCount` indices |
| Deck | Mega Lucario ex (14 Pokémon / 33 Trainers / 13 Energy) |

**Critical patterns we're missing:**
- `to_observation_class(obs_dict)` — gives typed `Observation` with real enum `.type` fields
- `all_card_data()` — complete card DB from engine, no CSV parsing needed
- `AttackPlan` pre-computation — decide WHO attacks WHAT before scoring actions
- Score-based multi-select with `maxCount > 1` (ours only returns `[single_idx]`)
- Packs `cg/` into `submission.tar.gz` for Kaggle evaluation
- `get_card(obs, area, index, player_index)` — safe card extraction from any zone
- `prize_count(pokemon)` — 3 for Mega ex, 2 for ex, 1 for basic
- Game-winning KO detection with score **50,000** (highest priority)

---

### 1B. Meta Snapshot (pilkwang) — Current Ladder Landscape

**Top findings:**
- Neuro-symbolic (rules + value net) outperforms pure NN under Kaggle constraints
- Logit masking on legal actions reduces gradient variance ~40%
- IS-MCTS with ~200 rollouts + transposition tables at critical decision points
- CVaR (α=0.1) reward shaping prevents coin-flip reliance
- Recommended: fast 2-layer MLP (128→64→1) as potential function

---

### 1C. Leaderboard Deck Meta (myso1987) — Score-Band Analysis

**Current meta tiers (July 2026):**

| Tier | Archetypes | Strategy |
|------|-----------|----------|
| S | Crustle, Alakazam/Dudunsparce | Damage-block (Crustle) or hand-scaling attack (Alakazam) |
| A | Starmie/Froslass, Typhlosion | Counter-meta: Starmie beats Crustle+Typhlosion |
| B | TR Mewtwo, Grimmsnarl, Garchomp | Niche strategies |
| — | Mega Lucario ex (our deck) | Strong but not dominant; needs refined play to compete |

**Key insight:** The meta is self-correcting — training against a diverse spread of archetypes beats over-optimizing for one matchup.

---

### 1D. Search-Audited Alakazam v9 (prvsiyan) — Top-Tier Search Agent

**Approach:** MCTS with heuristic evaluation, specifically tuned for Alakazam/Dudunsparce deck.

| Component | Implementation |
|-----------|---------------|
| Search | MCTS with custom state evaluation heuristic |
| Deck | Alakazam/Dudunsparce (hand-size scaling attack) |
| Key feature | "Search auditing" — validates search tree integrity across iterations |
| Budget | Truncated rollouts under 2s/decision and 10min/match total |

**What "search-audited" likely means:** The agent audits its own MCTS search tree to ensure consistency — detecting when the game engine's stochastic elements (coin flips, draws) cause tree branches to become invalid, and pruning/rebuilding them. This is a sophistication beyond basic IS-MCTS.

---

### 1E. Custom Engine + Vectorized Env (abiolatti) — 2M Samples/Sec RL Pipeline

**Approach:** Reimplement the game engine from scratch for massive training throughput.

| Component | Implementation |
|-----------|---------------|
| Engine | C++/Cython, zero-allocation, integer-only state tensors |
| Parallelism | 2,048–4,096 envs synchronous via OpenMP, GIL-released |
| State | `state_tensor[N, feature_dim]` C-contiguous NumPy |
| RL | Masked PPO with invalid action masking |
| Policy | Small MLP (128–256 hidden, ~100–300KB) |
| Throughput | ~2M samples/sec via fast PRNG + bitmask actions |
| Training | 262K transitions/batch, 3–4 PPO epochs |

**Dual-engine paradigm:** Train fast offline on custom engine → deploy `main.py` that translates `cabt` observations → model inference → action.

> [!NOTE]
> Requires C++/Cython compilation infrastructure. Maximum performance ceiling but highest development cost.

---

## 2. Research Papers

| Paper | Venue | Key Finding |
|-------|-------|-------------|
| **PTCG-Bench** (arXiv:2605.29653) | arXiv May 2026 | Agent harness design matters more than model backbone. Modular observation/action management is critical. |
| **PokéAgent Challenge** | NeurIPS 2025 | RL + search (MCTS) significantly outperforms LLMs in adversarial stochastic games. 20M+ trajectories dataset available. |
| **PokéLLMon** | arXiv 2024 | LLM-embodied agent with in-context RL. Not applicable under Kaggle constraints. |

---

## 3. Comparative Architecture Matrix

| | Our Agent (v3) | Beginner Guide | Alakazam v9 | Custom Engine |
|---|---|---|---|---|
| **Parser** | Manual `_sg()` wrappers | `to_observation_class()` | Engine-native | Custom C++ |
| **Card DB** | CSV parsing | `all_card_data()` | Engine-native | Compiled lookup |
| **Decision** | Priority chain → `[single_idx]` | Score all → sort → `[:maxCount]` | MCTS + heuristic eval | Masked PPO policy net |
| **Search** | ❌ None | ❌ None | ✅ MCTS (audited) | ✅ MCTS via compiled engine |
| **ML** | Inert MLP stub | ❌ None | Heuristic (no NN) | ✅ Trained PPO MLP |
| **Multi-select** | ❌ Always `[single]` | ✅ Handles `maxCount > 1` | ✅ Yes | ✅ Action masking |
| **Prize tracking** | ❌ None | ✅ prize_count() | ✅ Yes | ✅ In state vector |
| **Game-win detect** | ❌ None | ✅ Score 50,000 | ✅ Yes | ✅ In reward |
| **Submission pkg** | `main.py` only | `main.py` + `deck.csv` + `cg/` | Full package | `main.py` + `.so` + weights |

---

## 4. Gap Analysis: What We Need

### 🔴 Critical (our agent won't work competitively without these)
1. **Switch to `cg.api` imports** — use `to_observation_class()` and `all_card_data()` instead of manual parsing and CSV
2. **Handle `maxCount > 1`** — current engine only returns `[single_idx]`; many game situations require selecting multiple cards
3. **Pack `cg/` into submission** — required for Kaggle evaluation
4. **Score-based ranking** — replace rigid priority chain with numeric scores (can express same logic + handles ties + multi-select)

### 🟡 Important (competitive edge)
5. **AttackPlan pre-computation** — decide WHO attacks WHAT before scoring options
6. **Game-winning KO detection** — if KO wins enough prizes to end game, score = maximum
7. **Prize-aware target scoring** — 3 for Mega ex, 2 for ex, 1 for basic
8. **Proper Supporter / Item heuristics** — deck-specific play weights (like the beginner guide's 3000–20000 range)

### 🟢 Aspirational (top-10 level)
9. **Value network training** — use GameLogger data to train the MLP
10. **IS-MCTS at critical moments** — shallow search at lethal/prize-taking points
11. **Behavioral cloning** — pre-train policy on high-rated agent replays
12. **Multi-deck training** — train against Crustle, Alakazam, Starmie, Typhlosion archetypes
