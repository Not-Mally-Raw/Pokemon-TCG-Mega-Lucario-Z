import unittest
import os
import sys
import tempfile

# Ensure root ptcg-agent is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import main
import cg.api as cg
from cg.api import to_observation_class, Option, Attack, Card


class TestTier1FeatureCoverage(unittest.TestCase):
    """
    Tier 1 Feature Coverage Tests:
    - Deck loading & validation (60 cards, CSV parsing, fallback padding/truncation)
    - Setup phase action handling (returns 60-card list)
    - Lethal KO 50,000 score calculation (weakness x2, resistance -20/-30, game-winning trigger)
    - Multi-select maxCount bounds & option ranking
    - Macro-intent telemetry classification (Sutton Options taxonomy, decision entropy)
    - Kaggle path mapping (fallback resolution of datasets, DBs, models)
    """

    def setUp(self):
        self.engine = main._get_engine()

    # -------------------------------------------------------------------------
    # 1. Deck Loading & Validation
    # -------------------------------------------------------------------------
    def test_deck_loading_valid_60(self):
        """Standard deck.csv loads exactly 60 integer card IDs."""
        deck = self.engine.get_deck()
        self.assertEqual(len(deck), 60)
        self.assertTrue(all(isinstance(c, int) for c in deck))

    def test_deck_csv_parsing(self):
        """CSV parsing logic strips whitespace and parses digit lines."""
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".csv") as tmp:
            tmp.write("677\n  678 \n 6 \n# comment\ninvalid\n1086\n")
            tmp_path = tmp.name

        try:
            loaded = self.engine._load_deck(tmp_path)
            self.assertEqual(len(loaded), 60)
            self.assertEqual(loaded[:4], [677, 678, 6, 1086])
            # Remaining elements padded to 60 with Fighting Energy (6)
            self.assertEqual(loaded[4:], [6] * 56)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_deck_fallback_padding(self):
        """Fewer than 60 cards in file is padded to exactly 60 cards with card ID 6."""
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".csv") as tmp:
            tmp.write("677\n678\n")
            tmp_path = tmp.name

        try:
            loaded = self.engine._load_deck(tmp_path)
            self.assertEqual(len(loaded), 60)
            self.assertEqual(loaded[0], 677)
            self.assertEqual(loaded[1], 678)
            self.assertEqual(loaded[2:], [6] * 58)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_deck_fallback_truncation(self):
        """More than 60 cards in file is truncated to exactly 60 cards."""
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".csv") as tmp:
            for i in range(100):
                tmp.write(f"{i + 1}\n")
            tmp_path = tmp.name

        try:
            loaded = self.engine._load_deck(tmp_path)
            self.assertEqual(len(loaded), 60)
            self.assertEqual(loaded[0], 1)
            self.assertEqual(loaded[59], 60)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_deck_nonexistent_file_fallback(self):
        """Non-existent file falls back to 60 Fighting Energy cards."""
        loaded = self.engine._load_deck("non_existent_file_12345.csv")
        self.assertEqual(len(loaded), 60)
        self.assertEqual(loaded, [6] * 60)

    # -------------------------------------------------------------------------
    # 2. Setup Phase Action Handling
    # -------------------------------------------------------------------------
    def test_setup_phase_obs_select_none(self):
        """obs.select is None triggers setup phase returning 60-card list."""
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
        res = main.agent(obs)
        self.assertEqual(len(res), 60)
        self.assertEqual(res, self.engine.get_deck())

    def test_setup_phase_is_setup_flag_true(self):
        """Explicit is_setup_phase True returns complete 60-card deck list."""
        parsed = to_observation_class({"select": None})
        self.assertTrue(parsed.is_setup_phase)
        res = main.action(parsed)
        self.assertEqual(len(res), 60)

    # -------------------------------------------------------------------------
    # 3. Lethal KO 50,000 Score Calculation
    # -------------------------------------------------------------------------
    def test_lethal_ko_weakness_multiplier(self):
        """Weakness matching doubles base attack damage."""
        atk = Attack(name="Jab", cost=[], damage=30, effect="", energy_count=1)
        attacker = Card(card_id=677, name="Riolu", element_type="FIGHTING")
        defender = Card(card_id=1, name="Def", element_type="COLORLESS", weakness="FIGHTING")

        dmg = main.compute_effective_damage(atk, attacker, defender)
        self.assertEqual(dmg, 60)  # 30 * 2

    def test_lethal_ko_resistance_reduction(self):
        """Resistance matching reduces base damage by 20 or 30."""
        atk = Attack(name="Slash", cost=[], damage=50, effect="", energy_count=1)
        attacker = Card(card_id=677, name="Riolu", element_type="FIGHTING")
        defender_30 = Card(card_id=2, name="Def30", element_type="COLORLESS", resistance="FIGHTING -30")
        defender_20 = Card(card_id=3, name="Def20", element_type="COLORLESS", resistance="FIGHTING -20")

        dmg30 = main.compute_effective_damage(atk, attacker, defender_30)
        self.assertEqual(dmg30, 20)  # 50 - 30

        dmg20 = main.compute_effective_damage(atk, attacker, defender_20)
        self.assertEqual(dmg20, 30)  # 50 - 20

    def test_game_winning_ko_50k_score_trigger(self):
        """Lethal KO delivering the final prize triggers score 50,000."""
        obs = {
            "current": {
                "yourIndex": 0,
                "players": [
                    {
                        "active": [{"id": 677, "serial": 1, "hp": 80, "maxHp": 80}],
                        "bench": [],
                        "prize": [1]  # 1 prize remaining
                    },
                    {
                        "active": [{"id": 677, "serial": 2, "hp": 20, "maxHp": 80}],  # 20 HP left
                        "bench": [],
                        "prize": [1, 2, 3, 4, 5, 6]
                    }
                ]
            },
            "select": {
                "type": "0",  # MAIN
                "context": "0",
                "option": [
                    {"type": "13", "area": "4", "index": 0, "attack_id": 0},  # ATTACK
                    {"type": "14", "area": "11", "index": 1}  # END
                ],
                "minCount": 1,
                "maxCount": 1
            }
        }
        parsed = to_observation_class(obs)
        plan = main.compute_attack_plan(parsed)
        self.assertTrue(plan.is_ko)
        self.assertTrue(plan.is_game_winning_ko)

        score = main.score_option(parsed.select.options[0], parsed, plan)
        self.assertEqual(score, 50000)

    # -------------------------------------------------------------------------
    # 4. Multi-Select maxCount Bounds & Option Ranking
    # -------------------------------------------------------------------------
    def test_multi_select_ranking_descending(self):
        """Options are ranked in descending order by heuristic score."""
        obs = {
            "current": {
                "yourIndex": 0,
                "players": [
                    {
                        "active": [{"id": 677, "hp": 80}],
                        "hand": [{"id": 678}, {"id": 677}, {"id": 6}],  # Mega Lucario, Riolu, Energy
                        "prize": [1, 2, 3, 4, 5, 6]
                    },
                    {"active": [{"id": 677, "hp": 80}], "prize": [1, 2, 3, 4, 5, 6]}
                ]
            },
            "select": {
                "type": "1",  # CARD
                "context": "8",  # DISCARD
                "option": [
                    {"type": "3", "card_id": 6, "index": 0},    # Energy (5000)
                    {"type": "3", "card_id": 678, "index": 1},  # Mega Lucario (8000)
                    {"type": "3", "card_id": 677, "index": 2}   # Riolu (7000)
                ],
                "minCount": 2,
                "maxCount": 2
            }
        }
        res = main.agent(obs)
        self.assertEqual(len(res), 2)
        self.assertEqual(res, [1, 2])  # 8000 score (idx 1), 7000 score (idx 2)

    # -------------------------------------------------------------------------
    # 5. Macro-Intent Telemetry Classification & Entropy
    # -------------------------------------------------------------------------
    def test_macro_intent_taxonomy_mapping(self):
        """Score thresholds correctly map to named Sutton Options taxonomy."""
        self.assertEqual(main.macro_intent_for_score(50000), "LETHAL")
        self.assertEqual(main.macro_intent_for_score(12000), "AGGRO_KO")
        self.assertEqual(main.macro_intent_for_score(9000), "SETUP")
        self.assertEqual(main.macro_intent_for_score(8800), "ATTACK")
        self.assertEqual(main.macro_intent_for_score(7500), "DEVELOP")
        self.assertEqual(main.macro_intent_for_score(6000), "RESOURCE")
        self.assertEqual(main.macro_intent_for_score(4200), "STABILIZE")
        self.assertEqual(main.macro_intent_for_score(5000), "POWER_UP")
        self.assertEqual(main.macro_intent_for_score(100), "PASS")
        self.assertEqual(main.macro_intent_for_score(-999), "UNKNOWN")

    def test_decision_entropy_calculation(self):
        """Decision entropy calculation returns 0.0 for single option and positive float for contested options."""
        self.assertEqual(main.decision_entropy([50000]), 0.0)
        self.assertEqual(main.decision_entropy([]), 0.0)

        # Equal scores produce maximum entropy ln(2) approx 0.6931
        ent_equal = main.decision_entropy([5000, 5000], temperature=1000.0)
        self.assertAlmostEqual(ent_equal, 0.6931, places=3)

        # Dominant score produces low entropy
        ent_dominant = main.decision_entropy([50000, 100], temperature=1000.0)
        self.assertLess(ent_dominant, 0.01)

    # -------------------------------------------------------------------------
    # 6. Kaggle Path Mapping
    # -------------------------------------------------------------------------
    def test_kaggle_path_mapping_fallback(self):
        """Card DB initialization resolves across local and Kaggle paths to load card dataset."""
        db = main.get_card_db()
        self.assertIsInstance(db, dict)
        self.assertGreater(len(db), 0)
        # Check standard card Riolu (677) present
        self.assertIn(677, db)
        self.assertEqual(db[677].name, "Riolu")


if __name__ == "__main__":
    unittest.main()
