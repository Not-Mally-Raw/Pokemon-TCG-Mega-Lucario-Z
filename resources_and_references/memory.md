# PTCG Agent — System Memory & Conversational Context Archive

> **Purpose**: Single, comprehensive memory repository capturing the full context, user directives, literature reviews, mathematical derivations, architectural history, and lessons learned across the PTCG AI Battle competition project.
> **Note**: Merges insights across Antigravity (Gemini), Claude, and Grok sub-agent passes.

---

## 1. Project Background & Dual-Track Competition Structure

### Parallel Projects Context
- The user is managing three concurrent high-impact engineering projects:
  1. **ARC-AGI 3 Challenge**
  2. **Attention for Long Context Agents** (C++ high-performance engine)
  3. **PTCG AI Battle Challenge** (autonomous game-playing agent)
- PTCG AI Battle was selected due to strong synergy between agentic decision-making, neuro-symbolic reasoning, and real-time execution constraints.

### The Kaggle Pokemon TCG AI Battle Competition
- **Competition Target**: Build an autonomous AI agent for the Pokémon Trading Card Game (PTCG) AI Battle Challenge.
- **Constraints**:
  - Decision latency: < 2.0s per turn on 2 CPU cores.
  - Package size: ≤ 197.7 MiB (root-level `submission.tar.gz`).
  - Memory: CPU-only execution sandbox.
  - Match length: ~10–20 turns per match.

### Dual-Track Architecture (Two Tracks, One Agent)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       DUAL-TRACK COMPETITION FLOW                       │
├───────────────────────────────────────┬─────────────────────────────────┤
│          SIMULATION TRACK             │          STRATEGY TRACK         │
│  submission.tar.gz (Aug 16 deadline)  │    2,000-word Report (Sept 13)   │
│   Live matchmaking pool (600 Elo)     │  Human panel judged ($240k pool) │
└───────────────────────────────────────┴─────────────────────────────────┘
```

1. **Simulation Track** (Aug 16 23:59 UTC deadline):
   - Submission: `submission.tar.gz` containing `main.py`, `deck.csv`, and native `cg/` engine package.
   - Evaluated by: Automated matchmaking pool on Kaggle, updating a TrueSkill/Elo Bayesian rating starting at 600.
   - Public Anchors: Baseline sample agent (Mega Lucario ex) sits at ~664.2 rating. Leaderboard median climbed from ~628 to ~1,180. Top agents range from 1,400+.
2. **Strategy Track** (Sept 6 entry / Sept 13 final report deadline):
   - Submission: 2,000-word written strategy & research report.
   - Evaluated by: Human expert panel judging system design, decision explainability, deck construction rationale, and ablation data.
   - Strategy Scoring Breakdown: **Model Score (70%)**, **Deck Score (20%)**, **Report Rationale (10%)**.
   - Gatekeeper: Primary filter to qualify for the live $240K Tokyo finals (8 finalist slots $\times$ $30k).
   - Hard Dependency: Requires empirical ablation data from the Simulation agent before drafting.

---

## 2. Comprehensive Literature Review & 11-Stage Pipeline Synthesis

Below is the full 11-stage architectural review synthesized from domain literature (RLCard, Stratego DeepNash, Mahjong Suphx, StarCraft II AlphaStar, MAP-Elites, BlendRL):

### Stage 1: Perception & Ingestion Layer
- Zero-copy C++ / Cython binding ingestion (`to_observation_class`).
- Enforces strict typing (`OptionType`, `AreaType`, `SelectContext`).

### Stage 2: Belief State & Partial Observability
- Hidden state estimation (opponent hand, remaining prize cards).
- Perfect-Information Monte Carlo (PIMC) vs. Determinization.
- Citable reference: Perolat et al. 2022 (DeepNash Bayesian Belief State).

### Stage 3: Feature Representation
- 84-dimensional dense state vector encoding game state.
- Normalized HP ratios, hand/deck/bench counts, energy breakdown, active weakness/resistance, attack threat ratios.
- Reference: Zhang 2026 (PTCG-Bench state vector).

### Stage 4: Action Space & Action Masking
- Invalid action pruning via environment-provided legal options (`Select.options`).
- Action masking ensures zero probability assigned to illegal moves (Huang et al. 2020).

### Stage 5: Value & Policy Representation
- Lightweight 2-layer MLP (84 → 64 → 32 → 1) (~7.5K parameters).
- CPU-friendly inference (<0.5ms per forward pass).

### Stage 6: Search & Lookahead
- Engine-native `search_begin()` / `search_step()` substrate vs. hand-rolled IS-MCTS.
- 1-ply lookahead for high-leverage lethal checks.

### Stage 7: Neuro-Symbolic Integration (BlendRL Pattern)
- Hard symbolic priority hierarchy (`score_option()`) makes all structural decisions.
- Neural value network acts as a confidence-gated tie-breaker (margin ≤ ±500, uncertainty τ ≤ 0.1).
- Reference: Shindo et al. 2024 / 2025 (*BlendRL*, ICLR).

### Stage 8: Self-Play & Opponent Modeling
- Fictitious Self-Play (NFSP, Heinrich 2016) with game-level logging via `GameLogger`.

### Stage 9: Macro-Intents & Hierarchical Control
- Options Framework (Sutton, Precup & Singh 1999) macro-intents: `LETHAL`, `AGGRO_KO`, `SETUP`, `ATTACK`, `DEVELOP`, `RESOURCE`, `POWER_UP`, `STABILIZE`, `PASS`.

### Stage 10: Deck Strategy Optimization
- Single-archetype specialist hypothesis: Mega Lucario ex 60-card optimized list (`deck.csv`).

### Stage 11: Explainability & Decision Telemetry
- Decision entropy $H = -\sum p_i \log p_i$ computed per turn to measure decision contestedness.

---

## 3. Core Mathematical Foundations

### Binary Cross-Entropy Loss & Gradient
For outcome label $y \in \{0, 1\}$ and predicted probability $\hat{y} = \sigma(z)$:
$$L = -[y \log \hat{y} + (1 - y) \log(1 - \hat{y})]$$
Combined gradient at logit $z$:
$$\frac{\partial L}{\partial z} = \hat{y} - y$$

### Label Smoothing & Bootstrap Blending
$$\tilde{y}_t = \beta \cdot y_{\text{outcome}} + (1 - \beta) \cdot V_\theta(s_{t+1})$$
$$y'' = \tilde{y}_t (1 - \epsilon) + 0.5 \epsilon, \quad \epsilon = 0.05$$

### GELU vs. Leaky ReLU
- **GELU**: $\text{GELU}(x) = x \cdot \Phi(x)$, gradient $\Phi(x) + x \phi(x)$.
- **Leaky ReLU Choice**: $\text{LeakyReLU}(x) = \max(\alpha x, x)$ with $\alpha = 0.01$. Prevents dying units without numerical gradient mismatch.

### AdamW Optimizer
$$\mathbf{m}_t = \beta_1 \mathbf{m}_{t-1} + (1 - \beta_1) \mathbf{g}_t, \quad \mathbf{v}_t = \beta_2 \mathbf{v}_{t-1} + (1 - \beta_2) \mathbf{g}_t^2$$
$$\mathbf{\theta}_t = \mathbf{\theta}_{t-1} - \eta \left( \frac{\hat{\mathbf{m}}_t}{\sqrt{\hat{\mathbf{v}}_t} + \epsilon} + \lambda \mathbf{\theta}_{t-1} \right)$$

### 95% Wilson Score Interval (Non-Regression Gate)
$$\hat{p} = \frac{w}{n}, \quad \text{Center} = \frac{\hat{p} + \frac{z^2}{2n}}{1 + \frac{z^2}{n}}, \quad \text{Margin} = \frac{z \sqrt{\frac{\hat{p}(1-\hat{p})}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}$$
Where $z = 1.96$. Promotion requires $\text{Lower Bound} \ge 0.55$ over $n \ge 30$ matches.

---

## 4. Key Historical Lessons & Workflow Guardrails

1. **Verification Loop Primacy**: Never build complex ML layers on unverified wire-format assumptions. Capture real observations first (Step 0).
2. **Game-Level Data Splitting**: Always split self-play records by `game_id` (`group_train_val_split`), never at the decision level, to prevent temporal data leakage.
3. **Workflow Checkpointing**: Back up `main.py` before any major modification pass to prevent loss from environment restarts.
4. **Honest Framing**: State neuro-symbolic roles clearly (symbolic engine decides today; neural network acts as tie-breaker).
