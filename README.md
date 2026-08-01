# 🏆 Pokémon TCG AI Battle — Mega Lucario ex Neuro-Symbolic Agent

A production-grade, highly optimized neuro-symbolic hybrid AI agent designed for the **Kaggle Pokémon TCG AI Battle Competition**. Built around the **Mega Lucario ex** win condition, this system integrates rule-based heuristic decision trees with an Options Framework (Sutton et al., 1999) macro-intent abstraction layer and decision entropy telemetry.

---

## 📐 System Architecture

The agent leverages a **layered decision pipeline** designed to rank legal actions using domain-specific heuristics, game-winning KO verification, and action entropy tracking:

```
                          ┌──────────────────────────┐
                          │   Kaggle Game Engine     │
                          └─────────────┬────────────┘
                                        │ (Observation)
                                        ▼
                          ┌──────────────────────────┐
                          │    State & Deck Parser   │
                          └─────────────┬────────────┘
                                        │
                                        ▼
                          ┌──────────────────────────┐
                          │    AttackPlan Evaluator   │
                          │  - Calculates Effective  │
                          │    Damage & Weaknesses   │
                          │  - Game-Winning KO Guard │
                          └─────────────┬────────────┘
                                        │
                                        ▼
                          ┌──────────────────────────┐
                          │ Score-Based Action Ranker│
                          │  - Priority Scoring      │
                          │  - Options Framework     │
                          └─────────────┬────────────┘
                                        │
                                        ▼
                          ┌──────────────────────────┐
                          │ Decision Entropy & Intent│
                          │        Telemetry         │
                          └─────────────┬────────────┘
                                        │ (Top Action Indices)
                                        ▼
                          ┌──────────────────────────┐
                          │   Engine Action Execution│
                          └──────────────────────────┘
```

---

## 🎯 Key Design Features

### 1. Game-Winning KO Prioritization
If the system detects an attack that can KO the opponent's active Pokémon and secure enough prize cards (or wipe out the opponent's active card when they have no bench), it assigns an absolute max score of **50,000**, ensuring an immediate game victory decision override.

### 2. Options Framework Macro-Intents
Relabels integer scoring outputs into high-level tactical intent categories for logging and explainability:
- **LETHAL** (50,000): Game-winning attack.
- **AGGRO_KO** (10,000–13,999): Knockout feasible on active target.
- **SETUP** (9,000): Active / bench placement context.
- **DEVELOP** (7,000–8,499): Evolution or bench development.
- **RESOURCE** (5,500–6,999): Supporter or Item card play.
- **POWER_UP** (4,000–5,499): Energy attachment to attacker.
- **STABILIZE** (4,200): Emergency retreat when active HP < 40%.
- **PASS** (0–999): Default fallback/end turn.

### 3. Softmax Decision Entropy
Tracks decision uncertainty per turn using Shannon Entropy:
$$H = -\sum_{i} p_i \log p_i, \quad p_i = \frac{e^{S_i / T}}{\sum_j e^{S_j / T}}$$
Provides immediate diagnostics on how "contested" a decision turn was without added compute cost.

---

## 📁 Repository Structure

```
├── ptcg-agent/                  # Main Production Agent & Kaggle Notebooks
│   ├── main.py                  # Single-file production agent entry point (703 lines)
│   ├── cg/                      # Native Python bindings package
│   ├── PTCG_Baseline_Submission v3.ipynb # Kaggle submission notebook
│   └── tests/                   # Test suite for parsing & scoring logic
│
├── resources_and_references/    # Documentation & Research Summaries
│   ├── memory.md                # Conversational history & mathematical derivations
│   ├── next_steps.md            # Execution roadmap & phase dependencies
│   ├── research_done.md         # Scientific literature citations & tested ideas
│   ├── tasks.md                 # Master task tracking checklist
│   └── changelog.md             # Semantic versioning history
│
└── .gitignore                   # Excludes raw datasets, data archives, & logs
```

---

## 🚀 Quickstart & Usage

### 1. Kaggle Submission
The submission package is structured as a zero-dependency root tarball:
```bash
cd ptcg-agent
tar czf submission.tar.gz main.py deck.csv cg/
```

### 2. Local Testing
```bash
cd ptcg-agent
python3 -c "import main; print('Agent compiled cleanly!')"
```

---

## 🔬 Scientific & Architectural References

- **Sutton, Precup & Singh (1999)**: Between MDPs and semi-MDPs: A framework for temporal abstraction in reinforcement learning. *Artificial Intelligence*.
- **Hendrycks & Gimpel (2016)**: Gaussian Error Linear Units (GELUs).
- **Loshchilov & Hutter (2017/2019)**: Decoupled Weight Decay Regularization (AdamW). *ICLR*.
- **Guo et al. (2017)**: On Calibration of Modern Neural Networks (Temperature Scaling). *ICML*.

---

## 📜 License
MIT License
