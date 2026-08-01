# Next Steps — Sequenced Plan with Blueprint Logic

> Read `implementation_plan.md` first for current status. This file is the "how do I
> actually move forward from here" companion — each step states not just *what* to do but
> *why it's next* and what it unblocks.

## Dependency Chain (why the order matters)

```
Phase A / Task 1 (capture real observation)
        │
        ├──> confirms attackId / energies field formats
        │           │
        │           v
        ├──> Phase A / Task 2 revision (fill StateEncoder placeholders that depend on
        │     confirmed fields: weakness/resistance, AttackPlan threat, bench HP)
        │
        └──> unblocks real game_log.jsonl accumulation
                    │
                    v
            Phase B retraining (real trajectories replace synthetic smoke-test data)
                    │
                    v
            Wire tie-breaker into main.py's score_option()
                    │
                    v
            Phase C non-regression gate run for real (N>=30 matches vs. current best)
                    │
                    v
            Lock submission (Aug 16) ──> Report Phase (real ablation data required)
```

Nothing after Task 1 is trustworthy before it — this is why every prior plan document
repeats it as "the blocker."

## Step 1 — Capture and inspect a real observation (Phase A / Task 1)

**Blueprint**: run `capture_and_inspect()` against a live game (or Kaggle's validation
step) instead of `mock_observation()`. Manually diff the printed field inventory against
the three open assumptions:
- Does `attackId` index locally into the active Pokémon's attack list?
- Does `energies` arrive as raw ints or as objects?
- What fields are actually present vs. assumed in `mock_observation()`?

**Logic**: this is a pure information-gathering step — zero rating impact, but every
downstream number (StateEncoder correctness, training data validity, ensemble behavior)
is conditional on it. Treat any prior smoke-test result as **illustrative of mechanism
only**, not as evidence the system works.

**Exit condition**: `mock_observation()`'s field names/types are either confirmed or
corrected, and at least one real record exists in `game_log.jsonl`.

## Step 2 — Revise StateEncoder placeholders

**Blueprint**: of the 84 dims, 9 are live; the rest (weakness/resistance booleans,
AttackPlan threat-level floats, bench HP ratios, opponent hand/deck counts) are explicit
zero placeholders pending confirmed fields. Once Step 1 confirms the wire format:
1. Wire weakness/resistance from the card database lookup (already used by `AttackPlan`
   in `main.py` — reuse, don't reimplement).
2. Wire AttackPlan threat-level floats directly from `main.py`'s existing damage/KO
   calculation.
3. Wire bench HP ratios by iterating `observation["bench"]` the same way `active` is handled.

**Logic**: these placeholders were left as zeros *intentionally* — the point was an
auditable vector where every dim's provenance is traceable, not a black box. Filling them
in is mechanical once Step 1 confirms the underlying fields exist as assumed.

## Step 3 — Accumulate real self-play data, retrain the ensemble

**Blueprint**:
1. Run enough real/self-play games to get **at least a few hundred games** logged with
   `game_id` + `turn` index (needed for `flatten_trajectories()` to reconstruct ordered
   per-game state sequences — the TD-blended target requires knowing `state_{t+1}`).
2. Replace `synthesize_trajectories()` with a loader that groups `game_log.jsonl` by
   `game_id`, sorts by `turn`, and produces the same `{"game_id", "states", "outcome"}`
   shape `train_ensemble()` already expects.
3. Re-run `train_ensemble()` unmodified — the bagging, SGDR, TD-target, and calibration
   code doesn't need to change, only the data source.
4. **Expect the 100% validation win-rate to disappear.** That number was an artifact of
   trivially-separable synthetic data; a real number in the 55–70% range on real self-play
   would already be a meaningful result given the ~664-tier ceiling problem.

**Logic**: everything in the addendum patches was built and syntax/execution-verified
against synthetic data specifically so that swapping in real data is a **data-source
change only**, not a rewrite. This was a deliberate design choice — validate mechanism
first, cheaply, before spending real self-play compute.

## Step 4 — Wire the tie-breaker into production `main.py`

**Blueprint**:
1. Import the trained ensemble (serialize `ensemble_nets` params + fitted `temperature`
   to a small file — at ~30KB/model × 5–15 models this fits easily inside the package
   budget).
2. Call `resolve_with_ensemble()` from inside `score_option()`'s option-selection step,
   only when the top-2+ options are within the existing ±500 margin.
3. Merge `ITEM_WEIGHTS`, `energy_type_match_bonus`, `bench_priority_bonus` (Phase A / Task
   3, already written) into the live scoring function at the same time.
4. Relabel the existing `score_option()` priority buckets using the **exact** score
   constants already in production (50000 / 10000+ / 9000 / 8500+ / 8000 / 7000 / 6500 /
   5500 / 5000 / 4500 / 4200 / 4000 / 3500 / 100 / −1000) rather than the approximate
   `MACRO_INTENTS` bands in the notebook — those bands have a known overlap bug (see
   `tasks.md`) and must be tightened before they touch production logic.

**Logic**: keep the symbolic engine as the enforced core the whole time — the neural
ensemble is additive and gated, never a replacement, so this wiring step cannot make the
agent worse than the current heuristic-only baseline by construction (worst case: ties
just get broken arbitrarily instead of by a real signal).

## Step 5 — Run the non-regression gate for real (Phase C)

**Blueprint**: run **N ≥ 30** matches of the newly-wired agent against the current best
submission (the heuristic-only ~664 baseline). Compute the Wilson interval
(`non_regression_gate()` — already implemented and verified to correctly flag borderline
cases). Promote only if the **lower bound** clears 55%.

**Logic**: this is the safety net against "we believe it's better but it isn't" — the
plan explicitly calls this out as a previously-missing component. Don't skip it even
under deadline pressure; a false promotion costs more rating than a delayed one.

## Step 6 — Lock submission, shift fully to the Report

**Blueprint**: once Step 5 promotes a build, lock `submission.tar.gz` by Aug 16 23:59 UTC.
Passive self-play data keeps accumulating through Aug 31 (useful for the ablation study).
Write the 2,000-word Strategy report using `research_done.md` for citations and
`run_ablation()`'s real (not mocked) output for the required ablation table.

**Logic**: the Strategy report is worth only 10% directly but **gates access to the
$240K Tokyo finals** — it cannot be padded with placeholder numbers; every claim in it
should trace to a real, reproducible cell in the notebook.

## What NOT to do

- Don't hand-roll MCTS for B2 — use the engine-native search substrate (see
  `implementation_plan.md` rationale).
- Don't trust any win-rate number produced before Step 1 closes.
- Don't skip the game-level split when real data arrives — it's the single most important
  correctness property standing between this plan and a leaked/optimistic validation score.
- Don't let deadline pressure skip the non-regression gate (Step 5) before a submission.
