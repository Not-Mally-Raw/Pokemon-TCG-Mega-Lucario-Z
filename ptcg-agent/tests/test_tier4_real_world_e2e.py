import unittest
import os
import sys
import json
import tempfile

# Ensure root ptcg-agent is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import main
import cg.api as cg
from cg.api import to_observation_class


class TestTier4RealWorldE2E(unittest.TestCase):
    """
    Tier 4 Real-World Application Scenario Tests:
    - Full game flow simulation (setup -> turn loop -> energy attach -> evolution -> attack -> win)
    - Lethal KO 50,000 score E2E pipeline verification
    - Multi-turn macro-intent telemetry JSONL logging verification
    """

    # -------------------------------------------------------------------------
    # 1. Full Game Flow Simulation
    # -------------------------------------------------------------------------
    def test_full_game_flow_simulation(self):
        """Simulate a complete game flow sequence from setup to lethal game-winning KO."""
        # Turn 0: Setup Phase Deck Loading
        setup_obs = {
            "current": {
                "yourIndex": 0,
                "players": [
                    {"handCount": 7, "deckCount": 47},
                    {"handCount": 7, "deckCount": 47}
                ]
            },
            "select": None
        }
        deck_res = main.agent(setup_obs)
        self.assertEqual(len(deck_res), 60)

        # Turn 1: Active Pokemon Selection Context
        active_select_obs = {
            "current": {
                "yourIndex": 0,
                "players": [
                    {"hand": [{"id": 677}, {"id": 333}, {"id": 6}], "prize": [1, 2, 3, 4, 5, 6]},
                    {"prize": [1, 2, 3, 4, 5, 6]}
                ]
            },
            "select": {
                "type": "11",  # POKEMON
                "context": "1",  # SETUP_ACTIVE_POKEMON
                "option": [
                    {"type": "3", "card_id": 677, "index": 0},  # Riolu (9000)
                    {"type": "3", "card_id": 333, "index": 1}   # Hawlucha (9000)
                ],
                "minCount": 1,
                "maxCount": 1
            }
        }
        t1_action = main.agent(active_select_obs)
        self.assertEqual(t1_action, [0])  # Selects active Riolu

        # Turn 2: Energy Attachment (Deficit = 1)
        energy_obs = {
            "current": {
                "yourIndex": 0,
                "players": [
                    {
                        "active": [{"id": 677, "serial": 1, "hp": 80, "maxHp": 80, "energies": []}],
                        "bench": [],
                        "hand": [{"id": 6}],
                        "prize": [1, 2, 3, 4, 5, 6]
                    },
                    {"active": [{"id": 678, "serial": 2, "hp": 340}], "prize": [1, 2, 3, 4, 5, 6]}
                ]
            },
            "select": {
                "type": "0",  # MAIN
                "context": "0",
                "option": [
                    {"type": "8", "area": "2", "index": 0, "inPlayArea": 4},  # ATTACH (5000)
                    {"type": "14", "area": "11", "index": 1}  # END (100)
                ],
                "minCount": 1,
                "maxCount": 1
            }
        }
        t2_action = main.agent(energy_obs)
        self.assertEqual(t2_action, [0])  # Attaches energy

        # Turn 3: Mega Evolution
        evolution_obs = {
            "current": {
                "yourIndex": 0,
                "players": [
                    {
                        "active": [{"id": 677, "serial": 1, "hp": 80, "maxHp": 80, "energies": [6]}],
                        "bench": [],
                        "hand": [{"id": 678}],
                        "prize": [1, 2, 3, 4, 5, 6]
                    },
                    {"active": [{"id": 678, "serial": 2, "hp": 340}], "prize": [1, 2, 3, 4, 5, 6]}
                ]
            },
            "select": {
                "type": "0",
                "context": "0",
                "option": [
                    {"type": "9", "area": "2", "index": 0, "inPlayArea": 4, "inPlayIndex": 0},  # EVOLVE (8000)
                    {"type": "14", "area": "11", "index": 1}  # END (100)
                ],
                "minCount": 1,
                "maxCount": 1
            }
        }
        t3_action = main.agent(evolution_obs)
        self.assertEqual(t3_action, [0])  # Evolves to Mega Lucario ex

        # Turn 4: Game-Winning KO Attack
        winning_obs = {
            "current": {
                "yourIndex": 0,
                "players": [
                    {
                        "active": [{"id": 678, "serial": 1, "hp": 340, "maxHp": 340, "energies": [6, 6]}],
                        "bench": [],
                        "hand": [],
                        "prize": [1]  # Final 1 prize remaining
                    },
                    {
                        "active": [{"id": 677, "serial": 2, "hp": 30, "maxHp": 80}],  # 30 HP left
                        "bench": [],
                        "prize": [1, 2, 3, 4, 5, 6]
                    }
                ]
            },
            "select": {
                "type": "0",
                "context": "0",
                "option": [
                    {"type": "14", "area": "11", "index": 0},  # END (100)
                    {"type": "13", "area": "4", "index": 1, "attack_id": 0}  # ATTACK (50000 LETHAL KO!)
                ],
                "minCount": 1,
                "maxCount": 1
            }
        }
        t4_action = main.agent(winning_obs)
        self.assertEqual(t4_action, [1])  # Chooses ATTACK action index 1 delivering game-winning KO

    # -------------------------------------------------------------------------
    # 2. Lethal KO 50,000 Score E2E Pipeline Verification
    # -------------------------------------------------------------------------
    def test_lethal_ko_50k_score_e2e_pipeline(self):
        """E2E pipeline verification of 50,000 score trigger on lethal game-winning KO."""
        obs_raw = {
            "current": {
                "yourIndex": 0,
                "players": [
                    {
                        "active": [{"id": 677, "serial": 10, "hp": 80, "maxHp": 80, "energies": [6]}],
                        "bench": [],
                        "hand": [{"id": 1121}],  # Supporter Professor's Research
                        "prize": [1]  # 1 prize needed to win
                    },
                    {
                        "active": [{"id": 677, "serial": 20, "hp": 25, "maxHp": 80}],  # 25 HP remaining (Riolu Jab 30 kills)
                        "bench": [],
                        "prize": [1, 2, 3, 4, 5, 6]
                    }
                ]
            },
            "select": {
                "type": "0",
                "context": "0",
                "option": [
                    {"type": "7", "area": "2", "index": 0},   # PLAY Supporter (6500)
                    {"type": "13", "area": "4", "index": 1, "attack_id": 0}, # ATTACK (50000 Game-Winning KO)
                    {"type": "14", "area": "11", "index": 2}  # END (100)
                ],
                "minCount": 1,
                "maxCount": 1
            }
        }

        # 1. Verify Observation class parsing
        obs = to_observation_class(obs_raw)
        self.assertEqual(obs.my_prize_count, 1)
        self.assertEqual(obs.opp_active[0].hp, 25)

        # 2. Verify AttackPlan computation
        plan = main.compute_attack_plan(obs)
        self.assertTrue(plan.is_ko)
        self.assertTrue(plan.is_game_winning_ko)

        # 3. Verify Score calculation
        attack_opt = obs.select.options[1]
        supporter_opt = obs.select.options[0]
        end_opt = obs.select.options[2]

        score_attack = main.score_option(attack_opt, obs, plan)
        score_supporter = main.score_option(supporter_opt, obs, plan)
        score_end = main.score_option(end_opt, obs, plan)

        self.assertEqual(score_attack, 50000)
        self.assertEqual(score_supporter, 5500)
        self.assertEqual(score_end, 100)

        # 4. Verify end-to-end agent decision output
        chosen_indices = main.agent(obs_raw)
        self.assertEqual(chosen_indices, [1])

    # -------------------------------------------------------------------------
    # 3. Multi-Turn Macro-Intent Telemetry JSONL Logging Verification
    # -------------------------------------------------------------------------
    def test_macro_intent_jsonl_logging_e2e(self):
        """Verify multi-turn decisions write JSONL telemetry records with raw observation, actions, entropy, and intent."""
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".jsonl") as tmp:
            tmp_path = tmp.name

        try:
            # Re-initialize logger with temp file path
            test_logger = main.GameLogger(tmp_path)
            main._logger = test_logger

            # Turn 1: Power-Up Decision (Energy Attachment)
            turn1_obs = {
                "current": {
                    "yourIndex": 0,
                    "players": [
                        {"active": [{"id": 677, "hp": 80, "energies": []}], "hand": [{"id": 6}], "prize": [1, 2, 3, 4, 5, 6]},
                        {"active": [{"id": 678, "hp": 340}], "prize": [1, 2, 3, 4, 5, 6]}
                    ]
                },
                "select": {
                    "type": "0",
                    "context": "0",
                    "option": [
                        {"type": "8", "area": "2", "index": 0, "inPlayArea": 4},
                        {"type": "14", "area": "11", "index": 1}
                    ],
                    "minCount": 1,
                    "maxCount": 1
                }
            }
            main.agent(turn1_obs)

            # Turn 2: Lethal KO Decision
            turn2_obs = {
                "current": {
                    "yourIndex": 0,
                    "players": [
                        {"active": [{"id": 677, "hp": 80, "energies": [6]}], "prize": [1]},
                        {"active": [{"id": 677, "hp": 20}], "bench": [], "prize": [1, 2, 3, 4, 5, 6]}
                    ]
                },
                "select": {
                    "type": "0",
                    "context": "0",
                    "option": [
                        {"type": "13", "area": "4", "index": 0, "attack_id": 0},
                        {"type": "14", "area": "11", "index": 1}
                    ],
                    "minCount": 1,
                    "maxCount": 1
                }
            }
            main.agent(turn2_obs)

            # Close logger file handle
            if test_logger._f:
                test_logger._f.close()

            # Read and parse JSONL records
            with open(tmp_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]

            self.assertEqual(len(lines), 2)

            rec1 = json.loads(lines[0])
            self.assertIn("o", rec1)
            self.assertIn("a", rec1)
            self.assertIn("entropy", rec1)
            self.assertIn("intent", rec1)
            self.assertEqual(rec1["a"], [0])
            self.assertEqual(rec1["intent"], "POWER_UP")
            self.assertIsInstance(rec1["entropy"], float)

            rec2 = json.loads(lines[1])
            self.assertEqual(rec2["a"], [0])
            self.assertEqual(rec2["intent"], "LETHAL")
            self.assertIsInstance(rec2["entropy"], float)

        finally:
            main._logger = None
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()
