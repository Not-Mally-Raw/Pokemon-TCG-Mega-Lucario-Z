# Walkthrough — Patch 5 Shipped (Jul 27)

## What Changed

Patch 5 (Options framework relabeling + decision entropy telemetry) was applied to
[main.py](file:///Users/spandankewte/Downloads/Pokemon%20TCG/ptcg-agent/main.py).
Three additions, zero changes to game logic:

### 1. `MACRO_INTENTS` dict (lines 286-296)
Maps `score_option()` output ranges to named intents from the Options framework
(Sutton, Precup & Singh 1999). Provides the Strategy report's "Agent Architecture"
section with a citable hierarchy instead of an implicit priority list.

### 2. `decision_entropy()` (lines 306-317)
Computes H = -Σ p_i log p_i over softmax-normalized scores with temperature=1000.
Provides a per-turn "how contested was this decision" signal. Edge case: single-option
decisions return 0.0 (no uncertainty by definition).

### 3. `GameLogger.log()` extended (line 371)
Now accepts optional `entropy` and `intent` kwargs. The `agent()` function computes
both per turn and logs them alongside the observation and action indices.

## Bugs Found and Fixed During Implementation

1. **Overlapping score ranges**: DEVELOP (6000-8499) overlapped RESOURCE (5500-6999),
   and POWER_UP (4000-5499) contained STABILIZE (4200). Fixed by tightening DEVELOP
   to (7000-8499) and reordering STABILIZE before POWER_UP.

2. **Entropy edge case**: `decision_entropy([50000])` returned `-1e-12` instead of `0.0`
   due to the `log(p + 1e-12)` epsilon. Fixed by returning `0.0` for `len(scores) <= 1`.

## Verification

- `main.py` compiles clean
- 11/11 intent mapping assertions pass
- Entropy: uniform (1.386) > dominated (~0.000), empty=0.0, single=0.0
- submission.tar.gz rebuilt: 9.7 KiB, correct structure (main.py + deck.csv + cg/)

## What's Next

**Step 0 (user-blocked)**: Capture one real observation on Kaggle. This gates Steps 2 and 3.

The agent now logs `entropy` and `intent` per turn, so once real games run, the
`game_log.jsonl` will contain the data needed for the Strategy report's explainability
section — before any ML training is needed.
