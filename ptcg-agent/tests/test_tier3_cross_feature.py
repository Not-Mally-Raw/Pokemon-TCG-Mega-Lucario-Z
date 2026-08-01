import unittest
import os
import sys

# Ensure root ptcg-agent is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import main
import cg.api as cg
from cg.api import to_observation_class, OptionType, SelectContext


class TestTier3CrossFeature(unittest.TestCase):
    """
    Tier 3 Cross-Feature Interaction Tests:
    - Switch context + attack decision sequence
    - Setup phase -> Energy attach -> Evolution cross-feature transitions
    - Error handling & fallback context switches
    """

    def test_switch_context_then_attack_sequence(self):
        """Sequential transition from SWITCH context select to MAIN phase attack decision."""
        # 1. SWITCH context observation: forced to select active Pokemon from bench
        switch_obs = {
            "current": {
                "yourIndex": 0,
                "players": [
                    {
                        "active": [],  # Active knocked out
                        "bench": [
                            {"id": 3, "serial": 1, "hp": 50, "maxHp": 50},   # HP 50 -> Score 8050
                            {"id": 677, "serial": 2, "hp": 80, "maxHp": 80}  # HP 80 -> Score 8080
                        ],
                        "hand": [{"id": 6}],
                        "prize": [1, 2, 3, 4, 5, 6]
                    },
                    {"active": [{"id": 678, "serial": 3, "hp": 340, "maxHp": 340}], "prize": [1, 2, 3, 4, 5, 6]}
                ]
            },
            "select": {
                "type": "11",  # POKEMON select
                "context": "3",  # SWITCH context
                "option": [
                    {"type": "3", "area": "5", "index": 0, "inPlayIndex": 0},  # Bench idx 0
                    {"type": "3", "area": "5", "index": 1, "inPlayIndex": 1}   # Bench idx 1 (higher HP)
                ],
                "minCount": 1,
                "maxCount": 1
            }
        }

        switch_action = main.agent(switch_obs)
        self.assertEqual(switch_action, [1])  # Selects bench idx 1 with 80 HP

        # 2. MAIN phase observation following successful switch
        main_obs = {
            "current": {
                "yourIndex": 0,
                "players": [
                    {
                        "active": [{"id": 677, "serial": 2, "hp": 80, "maxHp": 80, "energies": [6]}],
                        "bench": [{"id": 3, "serial": 1, "hp": 50, "maxHp": 50}],
                        "hand": [],
                        "prize": [1, 2, 3, 4, 5, 6]
                    },
                    {"active": [{"id": 677, "serial": 4, "hp": 20, "maxHp": 80}], "bench": [], "prize": [1]}
                ]
            },
            "select": {
                "type": "0",  # MAIN
                "context": "0",
                "option": [
                    {"type": "7", "area": "2", "index": 0},  # PLAY
                    {"type": "13", "area": "4", "index": 0, "attack_id": 0},  # ATTACK (KO!)
                    {"type": "14", "area": "11", "index": 1}  # END
                ],
                "minCount": 1,
                "maxCount": 1
            }
        }

        main_action = main.agent(main_obs)
        self.assertEqual(main_action, [1])  # Prioritizes ATTACK action delivering KO

    def test_setup_to_energy_to_evolution_flow(self):
        """Cross-feature transitions: Setup phase -> Energy attach -> Evolution."""
        # Step 1: Setup phase (select is None)
        setup_obs = {"select": None}
        deck_res = main.agent(setup_obs)
        self.assertEqual(len(deck_res), 60)

        # Step 2: Main phase - Energy attach priority (Deficit = 1)
        energy_obs = {
            "current": {
                "yourIndex": 0,
                "players": [
                    {
                        "active": [{"id": 677, "serial": 1, "hp": 80, "maxHp": 80, "energies": []}],
                        "bench": [],
                        "hand": [{"id": 6}],  # Energy in hand
                        "prize": [1, 2, 3, 4, 5, 6]
                    },
                    {"active": [{"id": 678, "serial": 2, "hp": 340}], "prize": [1, 2, 3, 4, 5, 6]}
                ]
            },
            "select": {
                "type": "0",
                "context": "0",
                "option": [
                    {"type": "8", "area": "2", "index": 0, "inPlayArea": 4},  # ATTACH Energy to active (5000)
                    {"type": "14", "area": "11", "index": 1}  # END (100)
                ],
                "minCount": 1,
                "maxCount": 1
            }
        }
        energy_action = main.agent(energy_obs)
        self.assertEqual(energy_action, [0])  # Chooses ATTACH action (score 5000)

        # Step 3: Main phase - Evolution priority (Mega Lucario ex in hand)
        evolution_obs = {
            "current": {
                "yourIndex": 0,
                "players": [
                    {
                        "active": [{"id": 677, "serial": 1, "hp": 80, "maxHp": 80, "energies": [6]}],
                        "bench": [],
                        "hand": [{"id": 678}],  # Mega Lucario ex in hand
                        "prize": [1, 2, 3, 4, 5, 6]
                    },
                    {"active": [{"id": 678, "serial": 2, "hp": 340}], "prize": [1, 2, 3, 4, 5, 6]}
                ]
            },
            "select": {
                "type": "0",
                "context": "0",
                "option": [
                    {"type": "9", "area": "2", "index": 0, "inPlayArea": 4, "inPlayIndex": 0},  # EVOLVE active to Mega Lucario (8000)
                    {"type": "8", "area": "2", "index": 1, "inPlayArea": 4},                    # ATTACH Energy (4000)
                    {"type": "14", "area": "11", "index": 2}                                    # END (100)
                ],
                "minCount": 1,
                "maxCount": 1
            }
        }
        evolution_action = main.agent(evolution_obs)
        self.assertEqual(evolution_action, [0])  # Chooses EVOLVE action (score 8000)

    def test_error_handling_fallback_context_switches(self):
        """Agent catches unexpected observation exceptions and falls back cleanly."""
        # Corrupted select structure where options elements are malformed types
        corrupted_obs = {
            "current": {
                "yourIndex": 0,
                "players": [
                    {"active": [{"id": 677, "hp": 80}]},
                    {"active": [{"id": 677, "hp": 80}]}
                ]
            },
            "select": {
                "type": "0",
                "context": "0",
                "option": "NOT_A_LIST_OBJECT",  # Unexpected type causes internal handling fallback
                "minCount": 1,
                "maxCount": 1
            }
        }

        action_res = main.agent(corrupted_obs)
        self.assertIsInstance(action_res, list)
        self.assertGreater(len(action_res), 0)


if __name__ == "__main__":
    unittest.main()
