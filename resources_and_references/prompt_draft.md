# Teamwork Project Prompt — Draft

> Status: Launched
> Goal: Craft prompt → get user approval → delegate to teamwork_preview

Update the PTCG AI Battle Challenge agent notebook (`PTCG_Baseline_Submission v2.ipynb`) by splitting the work into a structured 5-phase execution approach. The final deliverable is a Kaggle-ready `.ipynb` that uses `cg.api` natively and implements score-based multi-select heuristics for the Mega Lucario ex deck.

Working directory: /Users/spandankewte/Downloads/Pokemon TCG/ptcg-agent
Integrity mode: demo

Reference material:
- Competitive analysis: /Users/spandankewte/.gemini/antigravity/brain/b056f6b0-6592-4f58-9980-9996b8bedd9d/competitive_analysis.md
- Current notebook (to be rewritten): /Users/spandankewte/Downloads/Pokemon TCG/ptcg-agent/PTCG_Baseline_Submission v2.ipynb
- Card database: /Users/spandankewte/Downloads/Pokemon TCG/ptcg-agent/data/EN_Card_Data.csv
- Existing deck.csv: /Users/spandankewte/Downloads/Pokemon TCG/ptcg-agent/deck.csv

## Requirements

### R1. Phase 1: Resource Gathering
Collect all necessary dependencies, `cg.api` documentation, and references from the beginner guide notebook. Ensure the `cg/` library directory is ready for packaging into the final submission.

### R2. Phase 2: Comparative Analysis
Compare the manual parsing logic currently in `PTCG_Baseline_Submission v2.ipynb` against the native `to_observation_class()` and `all_card_data()` API approach. Identify all refactoring points required to switch to native engine imports.

### R3. Phase 3: Plan Review
Draft the structural changes required for `main.py`. Specifically outline how the current priority-chain logic will be replaced by numeric scoring, and how `obs.select.maxCount > 1` (multi-select scenarios) will be handled. 

### R4. Phase 4: Enhancement Resource & Web Searching
Search the web/resources for optimal math and logic (e.g., game-winning KO detection, prize-aware target scoring, and energy attachment proximity) to encode into the Mega Lucario ex heuristics. The heuristic quality should match or exceed the beginner guide's scoring system.

### R5. Phase 5: Implementation & Packaging
Update the `PTCG_Baseline_Submission v2.ipynb` to generate the new `main.py`. Add a cell to package `main.py`, `deck.csv`, and the `cg/` folder into `submission.tar.gz`. Retain the inert ML scaffolding (`StateEncoder`, `NeuralWorker`, `GameLogger`).

## Acceptance Criteria

### Execution Structure
- [ ] The team explicitly executed and documented all 5 phases.

### Parser & Engine Integration
- [ ] `main.py` imports from `cg.api` and uses `to_observation_class()` for observation parsing
- [ ] Card database is built via `all_card_data()`, not CSV parsing

### Action Selection & Heuristics
- [ ] Every legal option receives a numeric score, sorted descending for top `maxCount` indices
- [ ] Agent correctly handles `maxCount > 1` scenarios
- [ ] Game-winning KO is detected and prioritized (highest score)
- [ ] Prize count per knockout is calculated (3/2/1)

### Submission Package
- [ ] Running the notebook top-to-bottom produces `submission.tar.gz`
- [ ] Archive contains `main.py` at root level, `deck.csv`, and `cg/` directory
- [ ] Archive is under 197.7 MiB
- [ ] `main.py` compiles without syntax errors on Python 3.9+
