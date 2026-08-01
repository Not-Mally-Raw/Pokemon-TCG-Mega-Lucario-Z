# PTCG Agent — Implementation Plan (Current, Consolidated)

> **Status: living source of truth.** Supersedes the "Revised Implementation Plan" and
> "Implementation Plan v3" documents — this file merges both, updated to reflect that the
> 5 ML addendum patches are now **implemented and smoke-tested** (not just specified).
> If this file and any other plan doc disagree, **this file wins**.

## Competition Structure (Two Tracks, One Agent)

| Track | Deliverable | Deadline | Weight | Status |
|-------|-------------|----------|--------|--------|
| **Simulation** | `submission.tar.gz` (`main.py` + `deck.csv` + `cg/`) | Aug 16 23:59 UTC | Skill rating via TrueSkill/Elo | ✅ Baseline submitted (heuristic-only, ~664 tier) |
| **Strategy** | 2,000-word report | Sept 6 entry / Sept 13 final | Judged by humans; **gatekeeper to $240K Tokyo finals** | ❌ Does not exist |

Hard dependency chain: **Phase A → Phase B → Phase C → Report.** Not two parallel tracks.

## Current Agent — Honest Assessment

`main.py` (444 lines) is a **pure heuristic scoring engine**. Every decision comes from
hand-crafted integer scores in `score_option()`. The neural stack (`StateEncoder`,
`ValueNet` ensemble, tie-breaker) is now **fully coded and passes a synthetic smoke test**
in `ptcg_agent_plan_v2_patched.ipynb` — but it has **never been trained on a real game**,
and is **not wired into `main.py`**. The production agent today is still capped near the
sample agent's **~664 tier by construction**.

### Unverified Assumptions (High Risk — unchanged, still open)
- `attackId` as a local index into the active Pokémon's attack list — assumed, unconfirmed
- `energies` field format — assumed raw ints, unconfirmed
- No real observation has been captured and manually inspected, despite `GameLogger` being wired

### Missing Components
- No non-regression gate wired into the actual submission flow (logic exists, unused)
- No deck construction rationale written (20% of Strategy grade)
- No matchup-spread testing
- Strategy report: 0 words written (10% of score, gate to finalist tier)

## Phase A: Close the Verification Loop (blocker — still open)

**Goal**: de-risk everything downstream. Zero rating improvement expected.

1. **Task 1 — capture a real observation.** Run one real game (or Kaggle's validation
   step), capture the raw JSON via `GameLogger`, settle the two unverified assumptions
   above. `capture_and_inspect()` is ready in the notebook; it just needs a real
   observation instead of `mock_observation()`.
2. **Task 2 — StateEncoder is populated**, not a stub: 84 dims, every one individually
   indexed and commented, 9 currently live (HP ratios, bench/hand/deck counts, prize
   differential, energy counts), the rest explicit placeholders (weakness/resistance,
   AttackPlan threat level, bench HP) pending Task 1 confirming the relevant fields.
3. **Task 3 — heuristic quick wins** (`ITEM_WEIGHTS`, `energy_type_match_bonus`,
   `bench_priority_bonus`) are written; not yet merged into the production
   `score_option()` in `main.py`.

## Phase B: The Only Phase That Moves Rating — 5 Patches Applied

Goal unchanged: break the ~664 heuristic ceiling. Mechanics revised per the ML/DL
addendum; each patch targets one specific failure mode of "small, correlated, sparse-
reward self-play dataset."

| # | Patch | Failure mode targeted | Status |
|---|---|---|---|
| 1 | TD(λ)-blended, label-smoothed target (replaces plain outcome-only BCE target) | Sparse terminal reward — one signal per 10–20 turn game | ✅ Implemented + smoke-tested |
| 2 | GELU activation (Leaky ReLU fallback available) | Dying units at 64→32 width | ✅ Implemented + smoke-tested |
| 3 | AdamW + SGDR cosine restarts (replaces SGD+momentum) | Sharp-minimum overfitting on tiny noisy data | ✅ Implemented + smoke-tested |
| 4 | Snapshot ensemble + game-level bagging (k=5) + uncertainty gate + temperature calibration | High variance from small correlated data | ✅ Implemented + smoke-tested |
| 5 | Options-framework macro-intents + decision-entropy telemetry | Report needs a citable hierarchy, not an if/elif chain | ✅ Implemented (known bug: overlapping score bands, see `tasks.md`) |

**Data split**: game-level 80/20 (`group_train_val_split`), not decision-level — decisions
within one game are correlated, so decision-level shuffling leaks information.

**Wiring**: the ensemble tie-breaker does **not** replace `score_option()`. It only
resolves ties: if the top heuristic options are within **±500 points**, AND the k=5
ensemble agrees (`std(ŷ) ≤ τ=0.1`), the calibrated ensemble win-probability breaks the
tie. If the ensemble disagrees, defer to the symbolic engine's top pick.

**B2 — one-ply lookahead** (if time remains): use the engine-native
`search_begin`/`search_step` substrate, not hand-rolled MCTS. Scaffold exists
(`one_ply_lookahead()`), mock path only — real harness path is commented, unexercised.

**⚠️ Everything in this phase is currently validated only against synthetic smoke-test
data** (trivially separable, 100% val win-rate — an artifact of the toy data, not a real
result). None of it is trustworthy until re-run against real trajectories from Phase A.

## Phase C: Stabilize, Don't Innovate

**Non-Regression Gate** (mandatory before every submission, logic implemented, not yet
wired into the submission pipeline):
- Run **N ≥ 30** matches against the previous best submission
- Report win-rate with a **Wilson score interval** (Wilson, 1927), not a raw percentage
- Promotion threshold: **≥55% win-rate**, matching AlphaGo Zero's gating rule
  (Silver et al., 2017, *Nature*)
- Verified case: raw 60% at n=30 correctly returns **HOLD** (CI lower bound 42.3% < 55%)

Lock final submission by **Aug 16 23:59 UTC**.

## Report Phase (Aug 17 → Sept 13)

1. **Agent Architecture** — neuro-symbolic hybrid, symbolic decides, neural ensemble is a
   confidence-gated override, honestly framed as untrained-on-real-data until Phase A closes.
2. **Deck Construction Rationale** — why Mega Lucario ex, matchup spread (not started).
3. **Decision Explainability** — trace `score_option()` via named macro-intents +
   decision-entropy telemetry (mechanism built, not yet run on real games).
4. **Ablation Data** — 3-way: heuristic-only vs. single-net tie-breaker vs. ensemble+TD
   tie-breaker. Harness (`run_ablation`) exists; all current numbers are placeholders.
5. **Research Framing** — four honest claims (neuro-symbolic architecture stated as
   inert-until-trained; native search over hand-rolled MCTS; adversarially-verified
   parser via a real captured observation; single-archetype specialist hypothesis).

## Process Fixes

1. Backup `main.py` before every teamwork run (`backup_before_teamwork_run()` — implemented)
2. Teamwork runs write incremental outputs, not one final dump
3. Keep the current working submission as a separate, untouched copy

## Immediate Next Step

**Phase A, Task 1 — still the blocker.** Capture and inspect a real game observation.
Everything in Phase B — however thoroughly coded and smoke-tested — is unusable until
this closes. See `next_steps.md` for the full sequenced plan from here.
