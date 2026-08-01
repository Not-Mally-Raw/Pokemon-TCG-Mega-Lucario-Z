import unittest
from agent.observation_parser import parse_observation, ParsedObservation, SelectContext

class TestObservationParser(unittest.TestCase):
    def test_setup_phase(self):
        """Test parsing when obs.select is None (Setup Phase)."""
        # In setup phase, select is explicitly None
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
        
        parsed = parse_observation(obs)
        self.assertTrue(parsed.is_setup_phase)
        self.assertIsNone(parsed.select)
        self.assertEqual(parsed.your_index, 0)
        self.assertEqual(parsed.my_state.hand_count, 7)

    def test_main_phase(self):
        """Test parsing a normal main phase turn."""
        obs = {
            "current": {
                "yourIndex": 0,
                "players": [
                    {
                        "active": [{"id": 15, "serial": 1, "hp": 120, "maxHp": 120}],
                        "bench": [{"id": 3, "serial": 2, "hp": 50, "maxHp": 50}],
                        "hand": [{"id": 100}, {"id": 101}],
                        "handCount": 2,
                        "deckCount": 40,
                        "poisoned": False
                    },
                    {
                        "active": [{"id": 20, "serial": 3, "hp": 200, "maxHp": 200}],
                        "bench": [],
                        "hand": None,
                        "handCount": 5,
                        "deckCount": 42,
                        "poisoned": True
                    }
                ]
            },
            "select": {
                "type": "MAIN",
                "context": "MAIN",
                "option": [
                    {"type": "PLAY", "area": "HAND", "index": 0, "playerIndex": 0},
                    {"type": "ATTACK", "area": "ACTIVE", "index": 0, "playerIndex": 0},
                    {"type": "END", "area": "PLAYER", "index": 0, "playerIndex": 0}
                ],
                "minCount": 1,
                "maxCount": 1
            },
            "logs": ["Turn started."]
        }
        
        parsed = parse_observation(obs)
        self.assertFalse(parsed.is_setup_phase)
        
        # Test my state
        self.assertEqual(len(parsed.my_state.active), 1)
        self.assertEqual(parsed.my_state.active[0].card_id, 15)
        self.assertEqual(parsed.my_state.active[0].hp, 120)
        self.assertEqual(parsed.my_state.hand_count, 2)
        self.assertEqual(len(parsed.my_state.hand), 2)
        self.assertEqual(parsed.my_state.hand[0], 100)
        
        # Test opp state
        self.assertEqual(parsed.opp_state.hand_count, 5)
        self.assertEqual(len(parsed.opp_state.hand), 0)
        self.assertTrue(parsed.opp_state.poisoned)
        self.assertFalse(parsed.opp_state.burned)
        
        # Test options
        self.assertEqual(len(parsed.select.options), 3)
        self.assertEqual(parsed.select.options[0].option_type, "PLAY")
        self.assertEqual(parsed.select.options[1].option_type, "ATTACK")
        self.assertEqual(parsed.select.options[2].option_type, "END")

    def test_missing_fields_defensive_parsing(self):
        """Test that the parser does not crash on completely empty dicts."""
        parsed = parse_observation({})
        self.assertTrue(parsed.is_setup_phase)  # Select is missing, defaults to None (setup phase)
        self.assertEqual(parsed.my_state.hand_count, 0)
        self.assertEqual(parsed.my_state.deck_count, 0)
        self.assertEqual(len(parsed.my_state.active), 0)

    def test_enum_parsing(self):
        """Test that enum members match string values."""
        # This asserts that the SelectContext.MULLIGAN we fixed is present
        self.assertEqual(SelectContext.MULLIGAN.value, "MULLIGAN")
        self.assertEqual(SelectContext.IS_FIRST.value, "IS_FIRST")

if __name__ == "__main__":
    unittest.main()
