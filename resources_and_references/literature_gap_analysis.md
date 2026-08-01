# PTCG Agent: State of Play & Literature Gap Analysis

## Part 1: What the Last 3 Teamwork Runs Actually Produced

All 3 teamwork subagent runs (Agent Rewrite Team, 5-Phase Rewrite Team, v4 Rewrite Team) were **killed by a server restart** on Jul 24. Only the **third run** (v4 Rewrite Team) completed before the restart. Here is an honest inventory of what exists on disk:

### Deliverables Produced ✅
| File | Status | Notes |
|------|--------|-------|
| [main.py](file:///Users/spandankewte/Downloads/Pokemon%20TCG/ptcg-agent/main.py) (444 lines) | ✅ Complete | Native `cg.api` imports, score-based engine, AttackPlan, multi-select |
| [deck.csv](file:///Users/spandankewte/Downloads/Pokemon%20TCG/ptcg-agent/deck.csv) | ✅ Valid | 60 card IDs |
| [submission.tar.gz](file:///Users/spandankewte/Downloads/Pokemon%20TCG/ptcg-agent/submission.tar.gz) | ✅ Valid | 8.4 KiB, contains `main.py`, `deck.csv`, `cg/` |
| [test_observation_parser.py](file:///Users/spandankewte/Downloads/Pokemon%20TCG/ptcg-agent/tests/test_observation_parser.py) | ✅ 5 tests | Setup, main phase, game-winning KO, multi-select, deck validation |

### What the Agent Actually Does (Code-Level Truth)

```
score_option() returns integer scores:
  ├── 50,000  → Game-winning KO (enough prizes to end the game)
  ├── 10,000+ → Regular KO + prize bonus (3000/2000/1000)
  ├──  9,000  → Setup: Riolu active
  ├──  8,500+ → Non-KO attack + prize + damage bonus
  ├──  8,000  → Evolve active → Mega Lucario ex
  ├──  7,000  → Evolve bench → Mega Lucario ex
  ├──  6,500  → Play Supporter
  ├──  5,500  → Play Item/Tool
  ├──  5,000  → Attach energy (active, deficit=1)
  ├──  4,500  → Attach energy (bench)
  ├──  4,200  → Retreat (HP < 40% AND healthy bench ready)
  ├──  4,000  → Ability / Attach default
  ├──  3,500  → Play basic Pokémon (bench < 5)
  ├──    100  → END turn
  └── -1,000  → Retreat (unsafe)
```

### What's Real vs. What's a Stub

| Component | Real? | Detail |
|-----------|-------|--------|
| `cg.api` integration | ✅ Real | `to_observation_class()`, `all_card_data()`, native enums |
| Score-based multi-select | ✅ Real | Sorts descending, returns top `maxCount` indices |
| AttackPlan pre-computation | ✅ Real | Weakness/resistance damage calc, KO detection |
| Game-winning KO (50,000) | ✅ Real | Checks if KO prizes ≥ remaining needed OR bench-out |
| Prize-aware targeting (3/2/1) | ✅ Real | Mega ex=3, ex=2, basic=1 |
| Bench-aware retreat | ✅ Real | HP < 40% AND healthy bench attacker with ≥80 HP |
| `StateEncoder` (84-dim) | 🔶 **Stub** | Returns `np.zeros(84)` — never populated |
| `NeuralWorker` (MLP) | 🔶 **Stub** | Random weights, never called during decisions |
| `GameLogger` | ✅ Real | Writes `game_log.jsonl` (observation + actions) |

> [!IMPORTANT]
> **Bottom line**: The agent is a **pure heuristic** scoring engine. The neural scaffolding is structurally wired but completely inert. All decisions come from hand-crafted integer scores. There is **zero learning, zero search, zero belief tracking**.

---

## Part 2: Literature Review Relevance Analysis

Your Perplexity review covers 11 stages with 27+ papers. Here's what's **directly relevant now**, what's **relevant for the next upgrade**, and what's **aspirational-but-out-of-scope** for this Kaggle competition.

### 🟢 DIRECTLY RELEVANT NOW (Can implement within Kaggle constraints)

| Stage | Paper/Technique | Why It Matters | Effort |
|-------|----------------|----------------|--------|
| **1. Parser** | RLCard zero-copy patterns | Already solved — we use `cg.api` natively | ✅ Done |
| **3. State Representation** | PTCG-Bench 84-dim vectors (Zhang 2026) | Our `StateEncoder` stub is exactly this architecture. Need to **populate** the 84-dim vector | 2-3 hours |
| **4. Action Masking** | Huang et al. 2020 (IAM with PPO) | Our score-based system IS effectively action masking — illegal actions are never presented by the engine. The scoring system ranks legal ones. | ✅ Done (implicitly) |
| **7. Neuro-Symbolic** | BlendRL (Shindo 2024) | **This is exactly our architecture.** Symbolic rule engine (score_option) + neural value network (NeuralWorker). We just need to activate the neural half. | 4-6 hours |
| **11. Explainability** | BlendRL + Integrated Gradients | The `GameLogger` already logs (obs, actions). We need to add feature attribution. | 2 hours |

### 🟡 RELEVANT FOR NEXT UPGRADE (Requires offline training infrastructure)

| Stage | Paper/Technique | What It Enables | Dependency |
|-------|----------------|-----------------|------------|
| **2. Belief State** | DeepNash PBS (Perolat 2022) | Track opponent's hidden hand + prize cards probabilistically | Need self-play data first |
| **5. Value Function** | Auxiliary tasks (Lyle 2021), OS-DistrRL (2023) | Reduce value head saturation, handle top-deck variance | Need `StateEncoder` populated first |
| **6. Search (IS-MCTS)** | GO-MCTS (Rebstock 2024), Batch MCTS (Cazenave 2021) | 200-rollout IS-MCTS within 2s budget on CPU | Need value network first |
| **7. Reward Shaping** | PBRS (Cooke 2023), MCTS reshaping (Li 2024) | Dense credit assignment for 10-20 turn games | Need training loop first |
| **8. Training** | NFSP (Heinrich 2016), MCTS enhancements (Dennis 2024) | 2-3 agent fictitious self-play, tree reuse | Need self-play simulator |

### 🔴 ASPIRATIONAL / OUT OF SCOPE FOR THIS COMPETITION

| Stage | Paper/Technique | Why Not Now |
|-------|----------------|-------------|
| **2. Belief** | Suphx neural particle filters | Requires 100K+ self-play games to train belief network |
| **6. Search** | Deep CFR (Brown 2019) | Model size 2-5 MB is fine, but training requires days of GPU compute |
| **8. Training** | AlphaStar league training (5-10 policies) | Requires massive parallel self-play infrastructure |
| **9. Hierarchical** | RT-H feudal architectures, emergent temporal abstractions | Requires meta-controller training + opponent modeling LSTM |
| **10. Meta-Game** | MAP-Elites deck construction (Zhang 2021) | We have a fixed deck (Mega Lucario ex); deck evolution is out of scope |

---

## Part 3: What Your Literature Review Got Right

### The "Recommended Minimal Stack" table is spot-on for our constraints:

| Their Recommendation | Our Status | Gap |
|---------------------|------------|-----|
| 84-dim feature vector + 2-layer MLP (128→64→32) ~200KB | ✅ Architecture exists (84→64→32→1) | ❌ StateEncoder returns zeros |
| Logit masking with PPO ~50KB | ✅ Engine provides only legal options | N/A (engine handles masking) |
| 1-head value + 2 auxiliary heads ~300KB | 🔶 1-head value exists | ❌ No auxiliary heads |
| IS-MCTS 200 rollouts + transposition table ~400KB | ❌ No search at all | Full implementation needed |
| PBRS with MCTS reshaping + CVaR ~150KB | ❌ No reward shaping | Requires training |
| 2-level hierarchy (Aggro/Control) + opponent LSTM ~400KB | ❌ No hierarchy | Aspirational |
| Symbolic rules + MLP value (BlendRL) ~250KB | 🔶 Rules exist, MLP is a stub | **Closest upgrade path** |
| NFSP with 2-3 agents + MCTS enhancements ~500KB | ❌ No training loop | Requires infrastructure |
| **Total: ~2.25 MB** | **Current: ~14 KB** | |

> [!TIP]
> The total estimated package for the full stack is **~2.25 MB** — well within our 197.7 MiB limit. The constraint is **training compute**, not package size.

---

## Part 4: Concrete Upgrade Roadmap (Priority Order)

### Tier 1: Quick Wins (Can do now, no training needed)

1. **Populate StateEncoder** — Fill the 84-dim vector with real features:
   - My/Opp active HP ratio (2 floats)
   - My/Opp bench count, hand count, deck count, prize count (8 ints)
   - Energy counts by type (12 floats)
   - Active Pokémon type matchup (weakness/resistance) (4 bools)
   - Prize race differential (1 float)
   - Board threat level (computed from AttackPlan) (4 floats)
   
2. **Improve Heuristic Scoring** — Currently missing:
   - Item-specific play weights (Ultra Ball > Potion > Switch)
   - Energy type matching (attach Fighting to Lucario, not random)
   - Bench development priority (when to bench vs. when to attack)

### Tier 2: Short-Term ML (Requires offline self-play data)

3. **Supervised Value Network Training** — Use `game_log.jsonl` data:
   - Feed real 84-dim features through the MLP
   - Label with game outcome (+1 win, -1 loss)
   - Train via SGD on collected games
   - Use value score as tie-breaker in `score_option()` when scores are close

4. **Shallow IS-MCTS** (200 rollouts, depth 3-4):
   - Sample opponent's hidden hand from belief prior
   - Use value network for leaf evaluation
   - Override heuristic when MCTS disagrees by > threshold

### Tier 3: Research-Grade (Competition-winning potential)

5. **BlendRL Integration** — Formalize the neuro-symbolic hybrid:
   - Symbolic rules as hard constraints (always enforced)
   - Neural policy as soft preferences (learned from self-play)
   - Blend via confidence weighting

6. **NFSP Self-Play** — Train against 2-3 historical checkpoints

---

## Open Questions for You

> [!IMPORTANT]
> Before I start implementing, I need to know your priority:

1. **Option A**: Polish the heuristic agent further (Tier 1) — improve scoring weights, add missing card-specific logic, populate the StateEncoder. Safe, incremental, guaranteed to work.

2. **Option B**: Jump to Tier 2 — build the training pipeline, collect self-play data, train the value network. Higher ceiling but needs infrastructure work.

3. **Option C**: Launch a new teamwork run with the literature-informed architecture. Use the "Recommended Minimal Stack" table as the spec.
