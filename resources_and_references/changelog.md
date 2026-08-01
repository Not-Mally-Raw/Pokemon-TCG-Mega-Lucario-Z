# PTCG Agent — Project Changelog

> **Format**: Semantic versioning & AI-friendly milestone tracking.

---

## [v3.1] - 2026-07-28 (Workspace Reorganization & Documentation Restructure)
### Changed
- Reorganized workspace into two clean production-grade directories:
  1. `ptcg-agent/`: Python scripts, packages (`cg/`), card data (`deck.csv`), packaging (`submission.tar.gz`), self-play logs (`game_log.jsonl`), and submission notebook (`PTCG_Baseline_Submission v2.ipynb`).
  2. `resources_and_references/`: Central repository for all system documentation, conversational memory (`memory.md`), README (`README.md`), roadmap (`next_steps.md`), task tracking (`tasks.md`), changelog (`changelog.md`), research citations (`research_done.md`), and implementation plans.

---

## [v3.0] - 2026-07-27 (Patch 5: Macro-Intents & Decision Entropy Telemetry)
### Added
- `MACRO_INTENTS` dictionary mapping integer score ranges to named intents from the Options framework (Sutton, Precup & Singh 1999):
  - `LETHAL` (50,000)
  - `AGGRO_KO` (10,000 - 13,999)
  - `SETUP` (9,000)
  - `ATTACK` (8,500 - 9,999)
  - `DEVELOP` (7,000 - 8,499)
  - `RESOURCE` (5,500 - 6,999)
  - `STABILIZE` (4,200)
  - `POWER_UP` (4,000 - 5,499)
  - `PASS` (0 - 999)
- `macro_intent_for_score(score)` lookup function.
- `decision_entropy(scores, temperature=1000.0)` calculating per-turn decision contestedness:
  $$H = -\sum p_i \log(p_i + 1e-12)$$
- `GameLogger.log()` extended to accept optional `entropy` and `intent` kwargs.
- Test 6 added to verification test suite verifying macro-intent lookup and entropy edge cases.

### Fixed
- Non-overlapping score ranges for `DEVELOP` (7000-8499) and `RESOURCE` (5500-6999).
- Reordered `STABILIZE` (4200) before `POWER_UP` (4000-5499) to avoid range subsumption.
- Handled single-option decision entropy edge case (`len(scores) <= 1` returns `0.0`).

### Updated
- `main.py` updated to 502 lines.
- `PTCG_Baseline_Submission v2.ipynb` cell 4 (`main.py` generator) and cell 8 (unit test suite) updated.
- `submission.tar.gz` rebuilt (9.7 KiB).

---

## [v2.0] - 2026-07-24 (Native `cg.api` Engine Rewrite)
### Added
- Native `cg.api.to_observation_class()` ground-truth parser replacing string helpers.
- Native `cg.api.all_card_data()` database initialization.
- `AttackPlan` pre-computation featuring weakness ($\times 2$) and resistance ($-20/-30$) damage math.
- Prize-aware target valuation (+3,000 Mega ex, +2,000 ex, +1,000 Basic).
- Game-winning KO detection (50,000 score priority).
- Score-based multi-select action ranking supporting `maxCount > 1`.
- Root-level archive packager (`submission.tar.gz` containing `main.py`, `deck.csv`, `cg/` package).

### Removed
- Manual string parsing functions (`_sg()`, `_pp()`, `_po()`).
- Custom enum redefinitions.

---

## [v1.0] - 2026-07-18 (Initial Baseline Setup)
### Added
- Mega Lucario ex 60-card list (`deck.csv`).
- Basic rule-based priority chain (`main.py`).
- Neural scaffolding stubs (`StateEncoder`, `NeuralWorker`).
