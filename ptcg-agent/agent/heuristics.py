import logging
import os
from typing import List, Optional
from agent.observation_parser import ParsedObservation, ParsedPokemon as PokemonState, ParsedPlayerState
from agent.card_database import CardDatabase

logger = logging.getLogger(__name__)

class HeuristicEngine:
    """
    Symbolic rule-based decision engine for the PTCG Agent.
    Implements a strict priority hierarchy for actions.
    """
    def __init__(self, deck_csv_path: str = "deck.csv"):
        self.deck_csv_path = deck_csv_path
        self.deck_card_ids = self._load_deck()

    def _load_deck(self) -> List[int]:
        deck = []
        base_dir = os.path.dirname(os.path.abspath(__file__))
        search_paths = [
            self.deck_csv_path,
            os.path.join(base_dir, "..", self.deck_csv_path),
            "/kaggle/input/pokemon-tcg-ai-battle/deck.csv",
            "/kaggle/input/competitions/pokemon-tcg-ai-battle/deck.csv",
        ]
        resolved = next((p for p in search_paths if p and os.path.exists(p)), None)
        if resolved:
            try:
                with open(resolved, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line.isdigit():
                            deck.append(int(line))
            except Exception as e:
                logger.error(f"Failed to load deck from {resolved}: {e}")
        
        if len(deck) != 60:
            logger.warning(f"Deck loaded has {len(deck)} cards, expected 60.")
            fallback_id = 6
            deck = (deck + [fallback_id] * 60)[:60]
        return deck

    def get_deck_card_ids(self) -> List[int]:
        """Returns the 60 card IDs comprising the deck."""
        return self.deck_card_ids

    def choose_action(self, obs: ParsedObservation) -> List[int]:
        """
        Main logic core. Evaluates the options and picks the best one using
        the priority hierarchy:
        1. Mandatory actions / setup
        2. KO opponent
        3. Evolve
        4. Play Supporter / Item
        5. Attach Energy
        6. Play Bench Pokemon
        7. Retreat
        8. Attack
        9. End / Pass
        """
        if not obs.select or not obs.select.options:
            return []

        # If mandatory select (min_count > 0 and only 1 option available), just take it.
        if len(obs.select.options) == 1:
            return [0]

        options = obs.select.options

        # Helper to find options by type safely
        def get_opts(types: List[str]) -> List[int]:
            matched = []
            types_upper = [t.upper() for t in types]
            for i, opt in enumerate(options):
                opt_type = getattr(opt, "option_type", None)
                opt_str = str(getattr(opt_type, "name", opt_type)).upper()
                if opt_str in types_upper or opt_type in types:
                    matched.append(i)
            return matched

        # PRIORITY 1: Mandatory selections (e.g. YES/NO, selecting target for attack/trainer)
        if any(getattr(opt, "option_type", None) in ["YES", "NO", "CARD", "NUMBER"] or
               str(getattr(getattr(opt, "option_type", None), "name", getattr(opt, "option_type", ""))).upper() in ["YES", "NO", "CARD", "NUMBER"]
               for opt in options):
            yes_opts = get_opts(["YES"])
            if yes_opts:
                return [yes_opts[0]]
            return [0]

        # Look up board state for advanced heuristics
        my_active = obs.my_state.active[0] if obs.my_state.active else None
        opp_active = obs.opp_state.active[0] if obs.opp_state.active else None
        
        my_active_card = CardDatabase.get_card(my_active.id) if (my_active and hasattr(my_active, 'id')) else None
        opp_active_card = CardDatabase.get_card(opp_active.id) if (opp_active and hasattr(opp_active, 'id')) else None

        opp_damage = getattr(opp_active, 'damage', (opp_active.max_hp - opp_active.hp) if (opp_active and opp_active.max_hp > 0) else 0) if opp_active else 0
        opp_hp_remaining = (opp_active_card.hp - opp_damage) if (opp_active and opp_active_card) else 999

        # PRIORITY 2: KO Opponent / Attack if lethal
        attack_opts = get_opts(["ATTACK", "13"])
        best_attack = None
        if attack_opts and opp_hp_remaining < 999:
            best_dmg = -1
            for idx in attack_opts:
                atk_opt = options[idx]
                atk_idx = getattr(atk_opt, 'option_index', getattr(atk_opt, 'attack_id', getattr(atk_opt, 'index', 0)))
                if my_active_card and len(my_active_card.attacks) > atk_idx:
                    dmg = my_active_card.attacks[atk_idx].damage
                    if dmg >= opp_hp_remaining:
                        return [idx]  # Lethal! Take it.
                    if dmg > best_dmg:
                        best_dmg = dmg
                        best_attack = idx
        else:
            best_attack = attack_opts[0] if attack_opts else None

        # PRIORITY 3: Evolve
        evolve_opts = get_opts(["EVOLVE", "9"])
        if evolve_opts:
            return [evolve_opts[0]]

        # PRIORITY 4: Play Trainer (Supporter / Item)
        trainer_opts = get_opts(["PLAY", "PLAY_TRAINER", "PLAY_SUPPORTER", "PLAY_ITEM", "7"])
        if trainer_opts:
            return [trainer_opts[0]]

        # PRIORITY 5: Attach Energy
        energy_opts = get_opts(["ATTACH", "ATTACH_ENERGY", "8"])
        if energy_opts:
            return [energy_opts[0]]

        # PRIORITY 6: Play Bench Pokemon
        bench_opts = get_opts(["PLAY", "PLAY_BASIC_PKMN", "PLAY_BASIC_POKEMON", "7"])
        if bench_opts:
            return [bench_opts[0]]

        # PRIORITY 7: Retreat
        retreat_opts = get_opts(["RETREAT", "12"])
        if retreat_opts and my_active and my_active_card:
            my_damage = getattr(my_active, 'damage', (my_active.max_hp - my_active.hp) if my_active.max_hp > 0 else 0)
            if my_damage >= my_active_card.hp - 50:
                if len(obs.my_state.bench) > 0:
                    return [retreat_opts[0]]

        # PRIORITY 8: Attack (Best available if not lethal)
        if attack_opts:
            if best_attack is not None:
                return [best_attack]
            return [attack_opts[0]]

        # PRIORITY 9: Ability / Stadium / End Turn
        ability_opts = get_opts(["ABILITY", "USE_ABILITY", "10"])
        if ability_opts:
            return [ability_opts[0]]
            
        stadium_opts = get_opts(["PLAY", "PLAY_STADIUM", "7"])
        if stadium_opts:
            return [stadium_opts[0]]

        end_opts = get_opts(["END", "14"])
        if end_opts:
            return [end_opts[0]]

        # Fallback
        return [0]
