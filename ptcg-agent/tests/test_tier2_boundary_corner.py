import unittest
import os
import sys

# Ensure root ptcg-agent is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import main
import cg.api as cg
from cg.api import to_observation_class, Option, OptionType, SelectContext, Observation, Select


class TestTier2BoundaryCorner(unittest.TestCase):
    """
    Tier 2 Boundary & Corner Case Tests:
    - Malformed / incomplete observation dictionaries
    - Unhandled action states and unknown select_types
    - Max selection bounds (max_count=0, negative max_count, max_count > available options)
    - Invalid card IDs (unmapped cards, missing DB entries)
    """

    # -------------------------------------------------------------------------
    # 1. Malformed / Incomplete Observation Dictionaries
    # -------------------------------------------------------------------------
    def test_malformed_obs_empty_dict(self):
        """Empty observation dict falls back to returning complete 60-card deck list."""
        res = main.agent({})
        self.assertEqual(len(res), 60)

    def test_malformed_obs_missing_players(self):
        """Observation missing players array parses safely and defaults states."""
        obs = {
            "current": {
                "yourIndex": 0
            },
            "select": None
        }
        res = main.agent(obs)
        self.assertEqual(len(res), 60)

    def test_malformed_obs_none_input(self):
        """None observation input does not crash agent and returns safe fallback."""
        res = main.agent(None)
        self.assertIsInstance(res, list)

    def test_malformed_obs_incomplete_player_fields(self):
        """Player dict missing active/bench/hand/prize fields handles default values."""
        obs = {
            "current": {
                "yourIndex": 0,
                "players": [
                    {"handCount": 0},
                    {"handCount": 0}
                ]
            },
            "select": {
                "type": "0",  # MAIN
                "context": "0",
                "option": [
                    {"type": "14", "area": "11", "index": 0}  # END
                ],
                "minCount": 1,
                "maxCount": 1
            }
        }
        parsed = to_observation_class(obs)
        self.assertEqual(len(parsed.my_active), 0)
        self.assertEqual(len(parsed.my_bench), 0)
        self.assertEqual(len(parsed.my_hand), 0)

        res = main.agent(obs)
        self.assertEqual(res, [0])

    def test_malformed_obs_string_or_garbage_types(self):
        """String or unexpected types passed in fields handle fallback gracefully."""
        obs = {
            "current": "invalid_string_current",
            "select": "invalid_string_select"
        }
        res = main.agent(obs)
        self.assertIsInstance(res, list)

    # -------------------------------------------------------------------------
    # 2. Unhandled Action States & Unknown Select Types
    # -------------------------------------------------------------------------
    def test_unknown_select_type(self):
        """Select type with unmapped integer/string falls back safely."""
        obs = {
            "current": {
                "yourIndex": 0,
                "players": [
                    {"active": [{"id": 677, "hp": 80}], "prize": [1, 2, 3, 4, 5, 6]},
                    {"active": [{"id": 677, "hp": 80}], "prize": [1, 2, 3, 4, 5, 6]}
                ]
            },
            "select": {
                "type": "99999",  # Unknown select type
                "context": "0",
                "option": [
                    {"type": "14", "index": 0}
                ],
                "minCount": 1,
                "maxCount": 1
            }
        }
        parsed = to_observation_class(obs)
        self.assertEqual(parsed.select.select_type, "99999")

        res = main.agent(obs)
        self.assertEqual(res, [0])

    def test_unknown_select_context(self):
        """Select context with unmapped string falls back to raw string context and scores safely."""
        obs = {
            "current": {
                "yourIndex": 0,
                "players": [
                    {"active": [{"id": 677, "hp": 80}], "prize": [1, 2, 3, 4, 5, 6]},
                    {"active": [{"id": 677, "hp": 80}], "prize": [1, 2, 3, 4, 5, 6]}
                ]
            },
            "select": {
                "type": "0",
                "context": "NON_EXISTENT_CONTEXT_XYZ",
                "option": [
                    {"type": "14", "index": 0}
                ],
                "minCount": 1,
                "maxCount": 1
            }
        }
        parsed = to_observation_class(obs)
        self.assertEqual(parsed.select.context, "NON_EXISTENT_CONTEXT_XYZ")

        res = main.agent(obs)
        self.assertEqual(res, [0])

    def test_unknown_option_type(self):
        """Option with unmapped option type gets default fallback score (1000 - index)."""
        obs = {
            "current": {
                "yourIndex": 0,
                "players": [
                    {"active": [{"id": 677, "hp": 80}], "prize": [1, 2, 3, 4, 5, 6]},
                    {"active": [{"id": 677, "hp": 80}], "prize": [1, 2, 3, 4, 5, 6]}
                ]
            },
            "select": {
                "type": "0",
                "context": "0",
                "option": [
                    {"type": "9999", "index": 0},
                    {"type": "8888", "index": 1}
                ],
                "minCount": 1,
                "maxCount": 1
            }
        }
        parsed = to_observation_class(obs)
        plan = main.compute_attack_plan(parsed)
        score0 = main.score_option(parsed.select.options[0], parsed, plan)
        score1 = main.score_option(parsed.select.options[1], parsed, plan)

        self.assertEqual(score0, 1000)
        self.assertEqual(score1, 999)

        res = main.agent(obs)
        self.assertEqual(res, [0])

    # -------------------------------------------------------------------------
    # 3. Max Selection Bounds
    # -------------------------------------------------------------------------
    def test_max_count_zero_defaults_to_one(self):
        """max_count = 0 defaults max_c to 1 and returns single top option."""
        obs = {
            "current": {
                "yourIndex": 0,
                "players": [
                    {"active": [{"id": 677, "hp": 80}], "prize": [1, 2, 3, 4, 5, 6]},
                    {"active": [{"id": 677, "hp": 80}], "prize": [1, 2, 3, 4, 5, 6]}
                ]
            },
            "select": {
                "type": "1",
                "context": "8",
                "option": [
                    {"type": "3", "card_id": 678, "index": 0},
                    {"type": "3", "card_id": 677, "index": 1}
                ],
                "minCount": 0,
                "maxCount": 0
            }
        }
        res = main.agent(obs)
        self.assertEqual(len(res), 1)
        self.assertEqual(res, [0])

    def test_negative_max_count_defaults_to_one(self):
        """Negative max_count defaults max_c to 1."""
        obs = {
            "current": {
                "yourIndex": 0,
                "players": [
                    {"active": [{"id": 677, "hp": 80}], "prize": [1, 2, 3, 4, 5, 6]},
                    {"active": [{"id": 677, "hp": 80}], "prize": [1, 2, 3, 4, 5, 6]}
                ]
            },
            "select": {
                "type": "1",
                "context": "8",
                "option": [
                    {"type": "3", "card_id": 678, "index": 0},
                    {"type": "3", "card_id": 677, "index": 1}
                ],
                "minCount": -1,
                "maxCount": -5
            }
        }
        res = main.agent(obs)
        self.assertEqual(len(res), 1)

    def test_max_count_exceeding_available_options(self):
        """max_count exceeding option count safely returns all options without index out of bounds."""
        obs = {
            "current": {
                "yourIndex": 0,
                "players": [
                    {"active": [{"id": 677, "hp": 80}], "prize": [1, 2, 3, 4, 5, 6]},
                    {"active": [{"id": 677, "hp": 80}], "prize": [1, 2, 3, 4, 5, 6]}
                ]
            },
            "select": {
                "type": "1",
                "context": "8",
                "option": [
                    {"type": "3", "card_id": 678, "index": 0},
                    {"type": "3", "card_id": 677, "index": 1}
                ],
                "minCount": 1,
                "maxCount": 10  # Only 2 options available
            }
        }
        res = main.agent(obs)
        self.assertEqual(len(res), 2)
        self.assertEqual(res, [0, 1])

    def test_empty_options_list(self):
        """Empty options list returns fallback [0] or deck list without crash."""
        obs = {
            "current": {
                "yourIndex": 0,
                "players": [
                    {"active": [{"id": 677, "hp": 80}], "prize": [1, 2, 3, 4, 5, 6]},
                    {"active": [{"id": 677, "hp": 80}], "prize": [1, 2, 3, 4, 5, 6]}
                ]
            },
            "select": {
                "type": "0",
                "context": "0",
                "option": [],
                "minCount": 0,
                "maxCount": 1
            }
        }
        res = main.agent(obs)
        self.assertIsInstance(res, list)

    # -------------------------------------------------------------------------
    # 4. Invalid Card IDs
    # -------------------------------------------------------------------------
    def test_unmapped_card_id(self):
        """Card ID not present in DB (e.g. 99999) does not raise KeyError and scores safely."""
        db = main.get_card_db()
        self.assertNotIn(99999, db)

        obs = {
            "current": {
                "yourIndex": 0,
                "players": [
                    {"active": [{"id": 99999, "hp": 80}], "hand": [{"id": 99999}], "prize": [1, 2, 3, 4, 5, 6]},
                    {"active": [{"id": 99999, "hp": 80}], "prize": [1, 2, 3, 4, 5, 6]}
                ]
            },
            "select": {
                "type": "0",
                "context": "0",
                "option": [
                    {"type": "7", "card_id": 99999, "index": 0},  # PLAY unmapped card
                    {"type": "14", "index": 1}  # END
                ],
                "minCount": 1,
                "maxCount": 1
            }
        }
        res = main.agent(obs)
        self.assertIsInstance(res, list)
        self.assertEqual(len(res), 1)

    def test_resolve_card_id_bounds_safety(self):
        """resolve_card_id handles out of bounds hand index safely returning None."""
        parsed = to_observation_class({
            "current": {
                "yourIndex": 0,
                "players": [
                    {"hand": [{"id": 677}], "handCount": 1},
                    {"handCount": 0}
                ]
            }
        })
        opt_out_of_bounds = Option(option_type=OptionType.PLAY, in_play_index=10)
        cid = main.resolve_card_id(opt_out_of_bounds, parsed)
        self.assertIsNone(cid)


if __name__ == "__main__":
    unittest.main()
