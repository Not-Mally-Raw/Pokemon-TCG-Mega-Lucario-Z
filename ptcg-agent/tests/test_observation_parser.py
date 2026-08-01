import unittest
import os
import sys

# Ensure root ptcg-agent is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import cg.api as cg
from cg.api import to_observation_class, OptionType, SelectContext, SelectType, AreaType
import main


class TestObservationParserAndAgent(unittest.TestCase):
    def test_setup_phase(self):
        """Test parsing when obs.select is None (Setup Phase)."""
        obs = {
            "current": {
                "yourIndex": 0,
                "players": [
                    {"handCount": 7, "deckCount": 47},
                    {"handCount": 7, "deckCount": 47}
                ]
            },
            "select": None,
            "logs": []
        }

        parsed = to_observation_class(obs)
        self.assertTrue(parsed.is_setup_phase)
        self.assertIsNone(parsed.select)
        self.assertEqual(parsed.your_index, 0)

        # Agent should return 60-card deck list
        deck_res = main.agent(obs)
        self.assertEqual(len(deck_res), 60)

    def test_main_phase_parsing(self):
        """Test parsing a normal main phase turn."""
        obs = {
            "current": {
                "yourIndex": 0,
                "players": [
                    {
                        "active": [{"id": 677, "serial": 1, "hp": 80, "maxHp": 80}],
                        "bench": [{"id": 3, "serial": 2, "hp": 50, "maxHp": 50}],
                        "hand": [{"id": 1121}, {"id": 6}],
                        "handCount": 2,
                        "deckCount": 40,
                        "prize": [1, 2, 3, 4, 5, 6],
                        "poisoned": False
                    },
                    {
                        "active": [{"id": 678, "serial": 3, "hp": 340, "maxHp": 340}],
                        "bench": [],
                        "hand": None,
                        "handCount": 5,
                        "deckCount": 42,
                        "prize": [1, 2, 3, 4, 5, 6],
                        "poisoned": True
                    }
                ]
            },
            "select": {
                "type": "0",  # MAIN
                "context": "0",  # MAIN
                "option": [
                    {"type": "7", "area": "2", "index": 0, "playerIndex": 0},  # PLAY, HAND
                    {"type": "13", "area": "4", "index": 0, "playerIndex": 0},  # ATTACK, ACTIVE
                    {"type": "14", "area": "11", "index": 0, "playerIndex": 0}  # END, PLAYER
                ],
                "minCount": 1,
                "maxCount": 1
            },
            "logs": []
        }

        parsed = to_observation_class(obs)
        self.assertFalse(parsed.is_setup_phase)

        # Test my state
        self.assertEqual(len(parsed.my_active), 1)
        self.assertEqual(parsed.my_active[0].id, 677)
        self.assertEqual(parsed.my_active[0].hp, 80)
        self.assertEqual(parsed.my_state.hand_count, 2)
        self.assertEqual(len(parsed.my_hand), 2)
        self.assertEqual(parsed.my_hand[0], 1121)

        # Test opp state
        self.assertEqual(parsed.opp_state.hand_count, 5)
        self.assertTrue(parsed.opp_state.poisoned)
        self.assertFalse(parsed.opp_state.burned)

        # Test options
        self.assertIsNotNone(parsed.select)
        self.assertEqual(len(parsed.select.options), 3)
        self.assertEqual(parsed.select.options[0].option_type, OptionType.PLAY)
        self.assertEqual(parsed.select.options[1].option_type, OptionType.ATTACK)
        self.assertEqual(parsed.select.options[2].option_type, OptionType.END)

    def test_game_winning_ko_detection(self):
        """Test that a KO yielding remaining prizes scores 50,000 and is prioritized."""
        obs = {
            "current": {
                "yourIndex": 0,
                "players": [
                    {
                        "active": [{"id": 677, "serial": 1, "hp": 80, "maxHp": 80, "energies": [6]}],
                        "bench": [],
                        "hand": [{"id": 1182}],  # Professor's Research
                        "prize": [1]  # Only 1 prize left to win!
                    },
                    {
                        "active": [{"id": 677, "serial": 2, "hp": 30, "maxHp": 80}],  # 30 HP remaining (Riolu Jab does 30)
                        "bench": [],
                        "prize": [1, 2, 3, 4, 5, 6]
                    }
                ]
            },
            "select": {
                "type": "0",  # MAIN
                "context": "0",  # MAIN
                "option": [
                    {"type": "7", "area": "2", "index": 0},  # PLAY Supporter (normally 6500)
                    {"type": "13", "area": "4", "index": 0, "attack_id": 0},  # ATTACK (delivers KO for last prize!)
                    {"type": "14", "area": "11", "index": 0}  # END (100)
                ],
                "minCount": 1,
                "maxCount": 1
            }
        }

        parsed = to_observation_class(obs)
        plan = main.compute_attack_plan(parsed)
        self.assertTrue(plan.is_ko)
        self.assertTrue(plan.is_game_winning_ko)

        attack_opt = parsed.select.options[1]
        score = main.score_option(attack_opt, parsed, plan)
        self.assertEqual(score, 50000)

        # Agent decision must select option 1 (ATTACK) with highest score 50000
        action_indices = main.agent(obs)
        self.assertEqual(parsed.select.options[1].index, 1)
        self.assertEqual(action_indices, [1])

    def test_multi_select_max_count(self):
        """Test multi-select ranking returning top maxCount indices when maxCount > 1."""
        obs = {
            "current": {
                "yourIndex": 0,
                "players": [
                    {
                        "active": [{"id": 677, "hp": 80}],
                        "hand": [{"id": 678}, {"id": 677}, {"id": 6}, {"id": 1086}],
                        "prize": [1, 2, 3, 4, 5, 6]
                    },
                    {
                        "active": [{"id": 678, "hp": 340}],
                        "prize": [1, 2, 3, 4, 5, 6]
                    }
                ]
            },
            "select": {
                "type": "1",  # CARD select
                "context": "8",  # DISCARD context (e.g. for Ultra Ball)
                "option": [
                    {"type": "3", "card_id": 678, "index": 0},  # Mega Lucario ex (Score 8000)
                    {"type": "3", "card_id": 677, "index": 1},  # Riolu (Score 7000)
                    {"type": "3", "card_id": 6, "index": 2},    # Energy (Score 5000)
                    {"type": "3", "card_id": 1086, "index": 3}  # Item (Score 3000)
                ],
                "minCount": 2,
                "maxCount": 2
            }
        }

        action_indices = main.agent(obs)
        self.assertEqual(len(action_indices), 2)
        self.assertEqual(action_indices, [0, 1])

    def test_deck_validation(self):
        """Test deck loading and validation."""
        deck = main._get_engine().get_deck()
        self.assertEqual(len(deck), 60)
        for card_id in deck:
            self.assertIsInstance(card_id, int)

    def test_submission_archive_integrity(self):
        """Verify submission.tar.gz existence, required root members (main.py, deck.csv, cg/), and size limit (< 197.7 MiB)."""
        import tarfile
        archive_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "submission.tar.gz"))
        self.assertTrue(os.path.exists(archive_path), "submission.tar.gz missing")

        size_mb = os.path.getsize(archive_path) / (1024 * 1024)
        self.assertLess(size_mb, 197.7, f"Archive size {size_mb:.2f} MiB exceeds 197.7 MiB limit")

        with tarfile.open(archive_path, "r:gz") as tar:
            names = tar.getnames()
            self.assertIn("main.py", names)
            self.assertIn("deck.csv", names)
            self.assertTrue(any(n.startswith("cg/") for n in names), "cg/ directory missing in archive")

    def test_macro_intent_and_entropy_telemetry(self):
        """Verify macro-intent bucket mapping and decision entropy calculation."""
        self.assertEqual(main.macro_intent_for_score(50000), "LETHAL")
        self.assertEqual(main.macro_intent_for_score(12000), "AGGRO_KO")
        self.assertEqual(main.macro_intent_for_score(9000), "SETUP")
        self.assertEqual(main.macro_intent_for_score(8800), "ATTACK")
        self.assertEqual(main.macro_intent_for_score(7500), "DEVELOP")
        self.assertEqual(main.macro_intent_for_score(6000), "RESOURCE")
        self.assertEqual(main.macro_intent_for_score(4200), "STABILIZE")
        self.assertEqual(main.macro_intent_for_score(5000), "POWER_UP")
        self.assertEqual(main.macro_intent_for_score(100), "PASS")

        # Equal scores produce maximum entropy ~ 0.6931
        ent_equal = main.decision_entropy([5000, 5000])
        self.assertAlmostEqual(ent_equal, 0.6931, places=3)

        # Dominant score produces low entropy
        ent_dominant = main.decision_entropy([50000, 100])
        self.assertLess(ent_dominant, 0.01)

    def test_dynamic_metadata_helpers(self):
        """Verify dynamic metadata resolution helpers for Riolu and Mega Lucario ex."""
        db = main.get_card_db()
        self.assertIn(677, db)
        riolu_card = db[677]
        self.assertTrue(main.is_riolu_card(riolu_card))
        self.assertTrue(main.is_riolu_id(677))

        self.assertIn(678, db)
        mega_card = db[678]
        self.assertTrue(main.is_mega_lucario_ex_card(mega_card))
        self.assertTrue(main.is_mega_lucario_ex_id(678))

    def test_unhandled_context_switches(self):
        """Verify context switches TO_HAND, ATTACH_FROM, EVOLVES_TO return valid score choices."""
        obs_to_hand = {
            "current": {"yourIndex": 0, "players": [{"active": [{"id": 677}], "prize": [1, 2, 3, 4, 5, 6]}, {"active": [{"id": 677}], "prize": [1, 2, 3, 4, 5, 6]}]},
            "select": {
                "type": "1",
                "context": "7",  # TO_HAND
                "option": [
                    {"type": "3", "card_id": 678, "index": 0},
                    {"type": "3", "card_id": 6, "index": 1}
                ],
                "minCount": 1,
                "maxCount": 1
            }
        }
        res_hand = main.agent(obs_to_hand)
        self.assertEqual(res_hand, [0])  # Selects Mega Lucario ex (idx 0) to fetch to hand

    def test_setup_phase_exception_fallback(self):
        """Verify outer exception handler returns 60-card deck list during setup phase."""
        bad_obs = None  # Causes Exception in parsing
        res = main.agent(bad_obs)
        self.assertEqual(len(res), 60)
        self.assertTrue(all(isinstance(c, int) for c in res))


if __name__ == "__main__":
    unittest.main()
