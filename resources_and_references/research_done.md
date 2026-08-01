# PTCG Agent — Literature Review & Research Summary

> **Purpose**: Complete inventory of scientific literature, academic citations, benchmark analyses, ideas tested & rejected, and design patterns utilized in this project.
> **Note**: Consolidates research across Antigravity (Gemini), Claude, and Grok.

---

## 1. Primary Academic Literature Citations

| # | Paper Citation | Core Contribution / Technique | Application in PTCG Agent |
|---|---|---|---|
| 1 | **Sutton (1988)** — *Learning to Predict by the Methods of Temporal Differences*, Machine Learning 3(1), pp. 9-44. | Temporal Difference (TD) learning for variance reduction in reward prediction. | Foundation for TD($\lambda$) target blending in value network training. |
| 2 | **Schulman, Moritz, Levine, Jordan & Abbeel (2015)** — *High-Dimensional Continuous Control Using Generalized Advantage Estimation*, arXiv:1506.02438. | Generalized Advantage Estimation ($\lambda$-returns). | Multi-step value target formulation. |
| 3 | **Szegedy, Vanhoucke, Ioffe, Shlens & Wojna (2016)** — *Rethinking the Inception Architecture for Computer Vision*, CVPR. | Label smoothing regularization $y'' = y'(1-\epsilon) + 0.5\epsilon$. | Prevents overconfident predictions on small noisy self-play datasets. |
| 4 | **Hendrycks & Gimpel (2016)** — *Gaussian Error Linear Units (GELUs)*, arXiv:1606.08415. | Smooth non-monotonic activation $\text{GELU}(x) = x \Phi(x)$. | Evaluated for 64$\rightarrow$32 layers; Leaky ReLU ($\alpha=0.01$) chosen to ensure exact derivative matching. |
| 5 | **Loshchilov & Hutter (2019)** — *Decoupled Weight Decay Regularization (AdamW)*, ICLR. | Decoupled weight decay from adaptive gradient scaling. | Production optimizer for `ValueNet` parameter updates. |
| 6 | **Loshchilov & Hutter (2016)** — *SGDR: Stochastic Gradient Descent with Warm Restarts*, arXiv:1608.03983. | Cosine learning rate annealing with periodic warm restarts. | Cosine LR schedule for training cycles. |
| 7 | **Huang, Li, Pleiss, Liu, Hopcroft & Weinberger (2017)** — *Snapshot Ensembles: Train 1, Get M for Free*, ICLR. | Capturing model weights at learning rate schedule troughs. | Single-pass ensemble snapshot mechanism. |
| 8 | **Breiman (1996)** — *Bagging Predictors*, Machine Learning 24(2), pp. 123-140. | Bootstrap aggregating across independent dataset resamples. | $k=5$ game-level bagging (`bootstrap_game_resample`). |
| 9 | **Gal & Ghahramani (2016)** — *Dropout as a Bayesian Approximation: Representing Model Uncertainty in Deep Learning*, ICML. | Epistemic uncertainty estimation via model variance. | Uncertainty gate ($\text{std} \le \tau = 0.1$) in `resolve_with_ensemble()`. |
| 10 | **Sutton, Precup & Singh (1999)** — *Between MDPs and Semi-MDPs: A Framework for Temporal Abstraction in Reinforcement Learning*, AI 112(1-2), pp. 181-211. | Options Framework for macro-intent abstraction. | `MACRO_INTENTS` taxonomy (`LETHAL`, `AGGRO_KO`, `SETUP`, `ATTACK`, `DEVELOP`, `RESOURCE`, `STABILIZE`, `POWER_UP`, `PASS`). |
| 11 | **Guo, Pleiss, Sun & Weinberger (2017)** — *On Calibration of Modern Neural Networks*, ICML. | Post-hoc temperature scaling $\hat{y} = \sigma(z/T)$. | Calibrating output probabilities for tie-breaking. |
| 12 | **Silver et al. (2017)** — *Mastering the Game of Go without Human Knowledge (AlphaGo Zero)*, Nature 550, pp. 354-359. | 55% win-rate promotion gating rule against past iterations. | Non-regression promotion gate threshold ($\ge 55\%$). |
| 13 | **Wilson (1927)** — *Probable Inference, the Law of Succession, and Statistical Inference*, JASA 22(158), pp. 209-212. | Binomial score interval for small samples $n \ge 30$. | 95% Wilson confidence lower-bound calculation. |
| 14 | **Shindo, Delfosse, Dhami & Kersting (2024)** — *BlendRL: A Framework for Merging Symbolic and Neural Policy Learning*, ICLR 2025. | Merging hard symbolic rules with soft neural policy feedback. | Neuro-symbolic contract between `score_option` and `ValueNet`. |
| 15 | **Zhang et al. (2026)** — *PTCG-Bench: Benchmarking Reinforcement Learning in Card Games*, arXiv. | 84-dimensional feature state representation. | `StateEncoder` 84-dim architecture layout. |
| 16 | **Perolat et al. (2022)** — *Mastering the Game of Stratego with DeepNash*, Science 378, pp. 990-996. | Imperfect information handling & regularized search. | Hidden-state handling and search substrate inspiration. |
| 17 | **Zha et al. (2020)** — *RLCard: A Toolkit for Reinforcement Learning in Card Games*, IJCAI. | Environment interaction & action masking standards. | Ground-truth parsing & native `cg.api` integration. |
| 18 | **Ng, Harada & Russell (1999)** — *Policy Invariance Under Reward Transformations*, ICML. | Potential-Based Reward Shaping (PBRS). | Theoretical foundation for intermediate score shaping. |
| 19 | **Chow et al. (2022)** — *Efficient Risk-Averse Reinforcement Learning*, NeurIPS. | Conditional Value-at-Risk (CVaR) optimization. | Optional risk-sensitive evaluation metric for tournament play. |

---

## 2. Ideas Tested & Rejected (or Deferred)

| Idea / Architecture | Reason Rejected / Deferred |
|---|---|
| **Full League Training / PBT / Fictitious Self-Play** | Impossible under Kaggle 2-vCPU / memory execution constraints. |
| **MAP-Elites Autonomous Deck Construction** | Out of scope for submission time window; 20% Deck Score satisfied by deliberate manual design. |
| **Heavy IS-MCTS Every Decision** | Exceeds < 2.0s per turn latency budget; restricted to 1-ply lethal lookahead. |
| **Neural Particle Filters for Belief State** | Overkill for prize-card tracking; simple card counting is sufficient and 100% explainable. |
| **End-to-End PPO / DQN from Scratch** | Cold start training too slow; heuristic priority chain achieves immediate baseline Elo (~664). |
| **LLM / Transformer Decision Agents** | Inference latency and package size (>197.7 MiB) prohibit deployment. |
| **GNNs for Board Topology** | High complexity with negligible gain at 84-dim state scale. |

---

## 3. Kaggle Benchmark & Competitor Analysis

- **Sample Rule-Based Agent (Mega Lucario ex)**: Public score ~664.2. Uses fixed priority chain without prize awareness or multi-select scoring.
- **Competitor Notebooks Evaluated**:
  - *Beginner Guide: From Deck List to First Valid Sub*: Demonstrated basic submission packaging.
  - *PTCG Meta A Stable Submit* & *BattleCore Compact Agent*: Confirmed native `cg.api` usage patterns.
- **Rating Trend**: Matchmaking pool median climbed from ~628 to ~1,180 over 38 days. Target is continuous Elo growth clearing Wilson lower-bound $\ge 0.55$.
