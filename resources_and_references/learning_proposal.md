# Learning Proposal: Kaggle Agent Refactoring Workflow

## 1. Identify What to Learn
In our recent interactions, we successfully reverse-engineered and prepared a Kaggle PTCG agent for a competitive rewrite. The key successful steps were:
1. **Accurate Mocking:** We verified the true "wire format" of the Kaggle environment (discovering that `cardId` isn't passed for PLAY actions, only hand `index`) and built accurate local mock fixtures.
2. **Parallel Intelligence Gathering:** We deployed multiple parallel browser subagents to read top public notebooks (Beginner Guide, Meta Snapshot, etc.).
3. **API Discovery:** We discovered that top agents use official engine APIs (`cg.api.to_observation_class`, `cg.api.all_card_data`) instead of manual parsing and CSV reading.
4. **Competitive Analysis Matrix:** We structured the findings into a clear comparative gap analysis.

## 2. Classification
**Type:** Skill
**Name:** `kaggle-agent-refactoring`

## 3. Rationale
This multi-step workflow (Local Mocking → Parallel Scraping → API Discovery → Matrix Analysis → Rewrite) is highly reusable for any Kaggle simulation or code-competition task, not just Pokémon TCG. It prevents wasting time on manual parsing when native APIs exist and ensures the agent actually works in the remote environment.

## 4. Proposed Addition
I propose creating a new skill file `kaggle-agent-refactoring/SKILL.md` with the following workflow:

```markdown
---
name: kaggle-agent-refactoring
description: Workflow for analyzing, mocking, and refactoring Kaggle simulation agents.
---

# Kaggle Agent Refactoring Workflow

When asked to improve or analyze a Kaggle competition agent/notebook, follow this strict methodology:

1. **Wire-Format Verification:** Do not trust user-provided or legacy mock data. Investigate the actual API format (e.g., how the simulation engine passes observations). Build accurate local mock fixtures.
2. **Parallel Intelligence Gathering:** Use `invoke_subagent` with the `browser` type to read 3-5 top public notebooks in parallel.
3. **API Discovery:** Look specifically for official engine/environment APIs being used by top competitors (e.g., native parsers, data loaders) to replace manual implementations.
4. **Competitive Analysis Matrix:** Create an artifact comparing the baseline agent against top public approaches across key dimensions (Parser, Decision Logic, Search, ML, Packaging).
5. **Phase-Based Rewrite:** Structure the rewrite prompt into clear phases (Resource Gathering, Comparative Analysis, Math/Logic Search, Implementation) before executing.
```

*Please approve this proposal, and I will create the skill for future use.*
