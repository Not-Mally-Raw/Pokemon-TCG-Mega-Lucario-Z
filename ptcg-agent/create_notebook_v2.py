import json
import os

def create_notebook():
    with open("main.py", "r", encoding="utf-8") as f:
        main_py_content = f.read()

    with open("deck.csv", "r", encoding="utf-8") as f:
        deck_csv_content = f.read()

    cells = [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# 🏆 PTCG AI Battle — Mega Lucario ex Agent (Native `cg.api` Rewrite)\n",
                "\n",
                "**Run All → Submit.** Generates `deck.csv` + `main.py` + `submission.tar.gz`.\n",
                "\n",
                "| Component | Detail |\n",
                "|---|---|\n",
                "| Architecture | Score-based multi-select action ranking engine with neural scaffolding |\n",
                "| Parser | Native `cg.api.to_observation_class()` ground-truth parser |\n",
                "| Database | Engine-native `cg.api.all_card_data()` metadata dictionary |\n",
                "| Tactical Engine | `AttackPlan` pre-computation, prize-aware target scoring, game-winning KO detection |\n",
                "| Mega Lucario Heuristics | Riolu → Mega Lucario ex priority, energy deficit attachment, Supporter > Item > Basic hierarchy, bench-aware retreat |\n",
                "| Neural Scaffolding | 84→64→32→1 MLP stub (`σ(0)=0.5` until trained). Retained & wired for logging. |\n",
                "| Submission Package | `submission.tar.gz` containing `main.py` (root), `deck.csv` (root), `cg/` package (<197.7 MiB) |\n",
                "\n",
                "---\n",
                "\n",
                "## Heuristic Priority & Scoring Table\n",
                "\n",
                "| Action / Situation | Integer Score | Tactical Rationale |\n",
                "|---|---|---|\n",
                "| **Game-Winning KO Attack** | **50,000** | Knockout claims final prize(s) or clears opponent bench to instantly win game |\n",
                "| **Knockout Attack** | **10,000 + Prize Bonus** | KO target (+3,000 Mega ex, +2,000 ex, +1,000 Basic) |\n",
                "| **Non-KO Best Damage Attack** | **8,500 + Prize Bonus + Dmg** | Maximize damage output against highest-value target |\n",
                "| **Evolve Active Riolu → Mega Lucario ex** | **8,000** | Power up active 340 HP main attacker |\n",
                "| **Evolve Bench Riolu → Mega Lucario ex** | **7,000** | Prepare secondary 340 HP attacker on bench |\n",
                "| **Play Supporter (Draw/Search)** | **6,500** | Refill hand resources (Professor's Research, Boss's Orders, etc.) |\n",
                "| **Play Search Item (Ultra Ball/Nest Ball)** | **5,500** | Fetch key Pokémon / evolutionary pieces from deck |\n",
                "| **Attach Energy (Active Deficit = 1)** | **5,000** | Enables immediate attack execution on active turn |\n",
                "| **Attach Energy (Bench Attacker Deficit = 1)** | **4,500** | Charge benched backup attacker for upcoming turns |\n",
                "| **Bench-Aware Retreat** | **4,200** | Active HP < 40% AND healthy bench attacker ready |\n",
                "| **Use Beneficial Ability** | **4,000** | Zero-cost resource generation / search |\n",
                "| **Play Basic Pokémon to Bench** | **3,500** | Expand bench size when bench_len < bench_max |\n",
                "| **Play General Item / Tool Card** | **2,000** | General utility item placement |\n",
                "| **End Turn** | **100** | Fallback when no beneficial actions remain |\n",
                "| **Unsafe Retreat** | **-1,000** | Penalized to prevent retreating into unready/weak bench |\n"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 1. Generate `deck.csv`\n"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "%%writefile deck.csv\n" + deck_csv_content
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 2. Generate `main.py`\n"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "%%writefile main.py\n" + main_py_content
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 3. Package Submission (`submission.tar.gz`)\n",
                "Creates the root-level submission archive containing `main.py`, `deck.csv`, and `cg/` package.\n"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import tarfile\n",
                "import os\n",
                "\n",
                "archive_path = \"submission.tar.gz\"\n",
                "\n",
                "with tarfile.open(archive_path, \"w:gz\") as tar:\n",
                "    tar.add(\"main.py\", arcname=\"main.py\")\n",
                "    tar.add(\"deck.csv\", arcname=\"deck.csv\")\n",
                "    if os.path.exists(\"cg\"):\n",
                "        tar.add(\"cg\", arcname=\"cg\")\n",
                "\n",
                "assert os.path.exists(archive_path), \"submission.tar.gz was not created!\"\n",
                "size_bytes = os.path.getsize(archive_path)\n",
                "size_mb = size_bytes / (1024 * 1024)\n",
                "\n",
                "print(f\"📦 submission.tar.gz created successfully: {size_bytes:,} bytes ({size_mb:.2f} MiB)\")\n",
                "assert size_mb < 197.7, f\"Submission size exceeds Kaggle 197.7 MiB limit: {size_mb:.2f} MiB\"\n",
                "\n",
                "with tarfile.open(archive_path, \"r:gz\") as tar:\n",
                "    members = tar.getnames()\n",
                "    print(\"Archive members (first 10):\", members[:10])\n",
                "    assert \"main.py\" in members, \"main.py missing from archive root!\"\n",
                "    assert \"deck.csv\" in members, \"deck.csv missing from archive root!\"\n",
                "    assert any(m.startswith(\"cg/\") or m == \"cg\" for m in members), \"cg/ missing from archive!\"\n",
                "print(\"✅ Submission packaging verification passed!\")\n"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 4. Verification & Unit Tests\n",
                "Executes comprehensive validation tests on `cg.api` observation parsing, game-winning KO detection, multi-select action ranking, submission archive structure, and `main.py` compilation.\n"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import sys\n",
                "import os\n",
                "import unittest\n",
                "import importlib\n",
                "\n",
                "# Ensure current directory is on sys.path\n",
                "if \".\" not in sys.path:\n",
                "    sys.path.insert(0, \".\")\n",
                "\n",
                "# Clear cached main module if already loaded\n",
                "if \"main\" in sys.modules:\n",
                "    del sys.modules[\"main\"]\n",
                "\n",
                "import main\n",
                "import cg.api as cg\n",
                "from cg.api import to_observation_class, OptionType, SelectType, SelectContext, AreaType\n",
                "\n",
                "print(\"=== Running Verification Test Suite ===\")\n",
                "\n",
                "# Test 1: Verify deck loading & Setup Phase return\n",
                "deck = main._get_engine().get_deck()\n",
                "assert len(deck) == 60, f\"Expected 60 deck cards, got {len(deck)}\"\n",
                "assert all(isinstance(c, int) for c in deck), \"All deck cards must be integers\"\n",
                "print(\"✅ Test 1 Passed: Deck list contains 60 valid integer card IDs\")\n",
                "\n",
                "# Test 2: Verify to_observation_class parsing\n",
                "mock_setup = {\"current\": {\"yourIndex\": 0, \"players\": [{\"handCount\": 7}, {\"handCount\": 7}]}, \"select\": None}\n",
                "parsed_setup = to_observation_class(mock_setup)\n",
                "assert parsed_setup.is_setup_phase is True\n",
                "assert parsed_setup.select is None\n",
                "setup_res = main.agent(mock_setup)\n",
                "assert len(setup_res) == 60\n",
                "print(\"✅ Test 2 Passed: to_observation_class handles Setup Phase (returns 60-card list)\")\n",
                "\n",
                "# Test 3: Game-Winning KO Detection (score = 50,000)\n",
                "mock_lethal = {\n",
                "    \"current\": {\n",
                "        \"yourIndex\": 0,\n",
                "        \"players\": [\n",
                "            {\n",
                "                \"active\": [{\"id\": 677, \"serial\": 1, \"hp\": 80, \"maxHp\": 80, \"energies\": [6]}],\n",
                "                \"bench\": [],\n",
                "                \"hand\": [{\"id\": 1182}],\n",
                "                \"prize\": [1]\n",
                "            },\n",
                "            {\n",
                "                \"active\": [{\"id\": 677, \"serial\": 2, \"hp\": 30, \"maxHp\": 80}],\n",
                "                \"bench\": [],\n",
                "                \"prize\": [1, 2, 3, 4, 5, 6]\n",
                "            }\n",
                "        ]\n",
                "    },\n",
                "    \"select\": {\n",
                "        \"type\": \"0\",\n",
                "        \"context\": \"0\",\n",
                "        \"option\": [\n",
                "            {\"type\": \"7\", \"area\": \"2\", \"index\": 0},\n",
                "            {\"type\": \"13\", \"area\": \"4\", \"index\": 0, \"attack_id\": 0},\n",
                "            {\"type\": \"14\", \"area\": \"11\", \"index\": 0}\n",
                "        ],\n",
                "        \"minCount\": 1,\n",
                "        \"maxCount\": 1\n",
                "    }\n",
                "}\n",
                "parsed_lethal = to_observation_class(mock_lethal)\n",
                "plan = main.compute_attack_plan(parsed_lethal)\n",
                "assert plan.is_ko is True, \"Attack must be KO\"\n",
                "assert plan.is_game_winning_ko is True, \"Attack must be game-winning KO\"\n",
                "\n",
                "attack_opt = parsed_lethal.select.options[1]\n",
                "attack_score = main.score_option(attack_opt, parsed_lethal, plan)\n",
                "assert attack_score == 50000, f\"Expected game-winning KO score 50000, got {attack_score}\"\n",
                "\n",
                "action_res = main.agent(mock_lethal)\n",
                "assert action_res == [1], f\"Expected action [1], got {action_res}\"\n",
                "print(\"✅ Test 3 Passed: Game-winning KO detected with score 50,000 & prioritized over Supporter\")\n",
                "\n",
                "# Test 4: Multi-Select Handling (maxCount > 1)\n",
                "mock_multi = {\n",
                "    \"current\": {\n",
                "        \"yourIndex\": 0,\n",
                "        \"players\": [\n",
                "            {\n",
                "                \"active\": [{\"id\": 677, \"hp\": 80}],\n",
                "                \"hand\": [{\"id\": 678}, {\"id\": 677}, {\"id\": 6}, {\"id\": 1086}],\n",
                "                \"prize\": [1, 2, 3, 4, 5, 6]\n",
                "            },\n",
                "            {\n",
                "                \"active\": [{\"id\": 678, \"hp\": 340}],\n",
                "                \"prize\": [1, 2, 3, 4, 5, 6]\n",
                "            }\n",
                "        ]\n",
                "    },\n",
                "    \"select\": {\n",
                "        \"type\": \"1\",\n",
                "        \"context\": \"8\",\n",
                "        \"option\": [\n",
                "            {\"type\": \"3\", \"card_id\": 678, \"index\": 0},\n",
                "            {\"type\": \"3\", \"card_id\": 677, \"index\": 1},\n",
                "            {\"type\": \"3\", \"card_id\": 6, \"index\": 2},\n",
                "            {\"type\": \"3\", \"card_id\": 1086, \"index\": 3}\n",
                "        ],\n",
                "        \"minCount\": 2,\n",
                "        \"maxCount\": 2\n",
                "    }\n",
                "}\n",
                "multi_res = main.agent(mock_multi)\n",
                "assert len(multi_res) == 2, f\"Expected 2 options for maxCount=2, got {len(multi_res)}\"\n",
                "assert multi_res == [0, 1], f\"Expected top 2 indices [0, 1], got {multi_res}\"\n",
                "print(\"✅ Test 4 Passed: Multi-select ranking returns top maxCount indices [0, 1]\")\n",
                "\n",
                "# Test 5: Archive Structure and Size Verification\n",
                "import tarfile\n",
                "assert os.path.exists(\"submission.tar.gz\"), \"submission.tar.gz missing\"\n",
                "with tarfile.open(\"submission.tar.gz\", \"r:gz\") as tar:\n",
                "    names = tar.getnames()\n",
                "    assert \"main.py\" in names, \"main.py missing from archive\"\n",
                "    assert \"deck.csv\" in names, \"deck.csv missing from archive\"\n",
                "    assert any(n.startswith(\"cg/\") or n == \"cg\" for n in names), \"cg/ directory missing from archive\"\n",
                "    sz_mb = os.path.getsize(\"submission.tar.gz\") / (1024 * 1024)\n",
                "    assert sz_mb < 197.7, f\"Archive size {sz_mb:.2f} MiB exceeds 197.7 MiB\"\n",
                "print(f\"✅ Test 5 Passed: submission.tar.gz valid ({sz_mb:.2f} MiB < 197.7 MiB limit)\")\n",
                "\n",
                "print(\"\\n🎉 ALL VERIFICATION TESTS PASSED 100%!\")\n"
            ]
        }
    ]

    nb_dict = {
        "cells": cells,
        "metadata": {
            "language_info": {
                "name": "python"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 2
    }

    nb_path = "PTCG_Baseline_Submission v2.ipynb"
    with open(nb_path, "w", encoding="utf-8") as f:
        json.dump(nb_dict, f, indent=1)

    print(f"Created updated notebook {nb_path} successfully!")

if __name__ == "__main__":
    create_notebook()
