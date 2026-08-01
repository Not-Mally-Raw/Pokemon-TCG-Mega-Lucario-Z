# Tasks — Checklist

> Format: `[x]` done, `[ ]` pending, `[~]` in progress / partially done. Grouped by phase,
> matching `implementation_plan.md`. Update this file whenever a task's status changes —
> it is the single place to check "is X actually done" without re-reading chat history.

## Phase A — Verification Loop

- [ ] **Task 1**: Capture a real game observation and manually inspect it (BLOCKER — everything below depends on this)
  - [ ] Confirm `attackId` indexes locally into the active Pokémon's attack list
  - [ ] Confirm `energies` field format (raw ints vs. objects)
  - [ ] Confirm full field inventory vs. `mock_observation()`'s assumed shape
- [x] **Task 2**: `StateEncoder` implemented — 84 dims, individually indexed and commented
  - [x] HP ratios, bench/hand/deck counts, prize differential, energy counts (9 live dims)
  - [ ] Weakness/resistance booleans (4 dims) — placeholder, needs card DB lookup wired
  - [ ] AttackPlan threat-level floats (4 dims) — placeholder, needs `AttackPlan` output wired
  - [ ] Bench HP ratios (5 dims) — placeholder, needs bench iteration wired
  - [ ] Opponent hand size / deck count (2 dims) — placeholder, hidden-info / unconfirmed field
- [x] **Task 3**: Heuristic quick wins written (`ITEM_WEIGHTS`, `energy_type_match_bonus`, `bench_priority_bonus`)
  - [ ] Merged into production `score_option()` in `main.py`

## Phase B — Value Network + Ensemble (5 Addendum Patches)

- [x] Patch 1 — TD(λ)-blended, label-smoothed target implemented (`make_td_target`)
  - [x] Turn-ordered trajectory data structure (`synthesize_trajectories`, `flatten_trajectories`)
  - [ ] Real trajectory loader from `game_log.jsonl` (currently synthetic only)
- [x] Patch 2 — GELU activation implemented (`gelu`, `gelu_grad`), Leaky ReLU fallback available
- [x] Patch 3 — AdamW optimizer + SGDR cosine schedule implemented (`AdamWOptimizer`, `cosine_lr`)
- [x] Patch 4 — Ensemble implemented
  - [x] Game-level bootstrap resampling (`bootstrap_game_resample`)
  - [x] k=5 bagged models trained (`train_ensemble`)
  - [x] Snapshot capture at SGDR troughs (captured, not all enrolled in live ensemble — only final weights per bagged model used)
  - [x] Uncertainty gate (`resolve_with_ensemble`, τ=0.1)
  - [x] Temperature calibration (`fit_temperature`) — hit grid floor (T=0.5) on synthetic data, needs re-check on real data
- [x] Patch 5 — Macro-intents + decision entropy implemented
  - [x] `decision_entropy()` function
  - [ ] **Known bug**: `MACRO_INTENTS` score bands overlap (DEVELOP 6000–8499 vs. RESOURCE 5500–6499 overlap at 6000–6499) — needs tightening to the exact non-overlapping `score_option()` constants before production use
- [x] Ensemble tie-breaker wiring (`resolve_with_ensemble`) — smoke-tested only
- [ ] Tie-breaker wired into production `main.py` `score_option()`
- [ ] Trained on real self-play data (currently synthetic smoke test only — 100% val win-rate is a toy-data artifact, not a result)
- [x] **B2**: one-ply lookahead scaffold (`one_ply_lookahead`) — mock path only
  - [ ] Real `cg.search_begin`/`search_step` path wired (commented out, unexercised)

## Phase C — Stabilize

- [x] `wilson_interval()` implemented and verified correct
- [x] `non_regression_gate()` implemented and verified against the 60%@n=30 cautionary case (correctly returns HOLD)
- [ ] Gate wired into the actual submission promotion workflow (logic exists, not yet used operationally)
- [ ] First real non-regression run against current best submission

## Report Phase

- [x] Report outline defined (5 sections, matches judging criteria)
- [x] Ablation harness written (`run_ablation`) — 3-way variant (heuristic / single-net / ensemble)
- [ ] Ablation run with real match results (currently mocked random thresholds)
- [ ] Deck construction rationale — not started (20% of Strategy grade)
- [ ] Matchup-spread testing — not started
- [ ] 2,000-word report draft — 0 words written

## Process / Infra

- [x] `backup_before_teamwork_run()` implemented
- [ ] Actually invoked before the next multi-hour teamwork run (process discipline, not code)
- [x] Reference notebook established as unedited structural blueprint
- [x] Patched notebook (`ptcg_agent_plan_v2_patched.ipynb`) built on top of it, all 5 patches applied
- [x] Documentation set reorganized into `docs/` (this file and its siblings)

## Documentation

- [x] `implementation_plan.md` — consolidated current plan
- [x] `next_steps.md` — sequenced steps with blueprint logic
- [x] `tasks.md` — this file
- [x] `changelog.md` — chronological project history
- [x] `research_done.md` — citation ledger (verified / flagged / used)
- [x] `memory.md` — archived long-form session documents
- [x] `README.md` — architecture, data flow, cell-by-cell reference, current status
