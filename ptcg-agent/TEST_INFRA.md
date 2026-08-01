# E2E Test Infra: PTCG AI Agent Audit & Hackathon Diff (v4)

## Test Philosophy
- Opaque-box, requirement-driven E2E and unit test suite for PTCG AI Agent.
- Derived directly from product specification and user requirements.
- Uses 4-Tier test architecture: Category-Partition, BVA, Pairwise Combinatorial, and Real-World Application Scenarios.

## Feature Inventory
| # | Feature | Requirement Description | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|---|---------|-------------------------|:------:|:------:|:------:|:------:|
| 1 | Deck Loading | Load & parse deck files, validate 60-card decks & Kaggle path mapping | 5 | 5 | ✓ | ✓ |
| 2 | Setup Phase | Initial hand draw, active & bench Pokemon setup, Mulligan handling | 5 | 5 | ✓ | ✓ |
| 3 | Lethal KO Score | Compute state evaluation score, 50,000 points threshold for winning lethal KO | 5 | 5 | ✓ | ✓ |
| 4 | Multi-Select maxCount | Select cards/targets constrained strictly by maxCount bounds | 5 | 5 | ✓ | ✓ |
| 5 | Macro-Intent Telemetry | Track agent decisions, macro-intents, action logs, and intent transitions | 5 | 5 | ✓ | ✓ |
| 6 | Kaggle Path Mapping | Resolve datasets, card databases, and model assets via Kaggle environment paths | 5 | 5 | ✓ | ✓ |

## Test Architecture
- Test Runner: `pytest`
- Location: `/Users/spandankewte/Downloads/Pokemon TCG/ptcg-agent/tests`
- Verification Method: All test modules run with `pytest tests/` and return exit code 0 with 100% pass rate.

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Target Complexity |
|---|----------|--------------------|-------------------|
| 1 | Full Game Flow Simulation | Setup, Energy Attach, Evolution, Switch, Attack, Win Condition | High |
| 2 | Lethal KO 50k Score Verification | Lethal attack calculation triggering >= 50,000 score reward | High |
| 3 | Macro-Intent Telemetry Tracking | E2E decision pipeline logging intents across multi-turn game | High |

## Coverage Thresholds
- Tier 1: ≥5 test cases per feature (Happy path & feature validation)
- Tier 2: ≥5 test cases per feature (Boundary, malformed obs, unhandled states, overflow)
- Tier 3: Pairwise cross-feature interactions (Switch+Attack, Setup+Energy, Error context switches)
- Tier 4: Real-world E2E game flow simulation & telemetry verification
