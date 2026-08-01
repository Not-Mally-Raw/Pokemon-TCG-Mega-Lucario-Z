import logging
from agent.observation_parser import ParsedObservation

logger = logging.getLogger(__name__)

class HeuristicEngine:
    """
    Symbolic rule-based decision engine for the PTCG Agent.
    Evaluates ParsedObservation and returns an action index list.
    """
    def __init__(self, deck_csv_path: str):
        self.deck_csv_path = deck_csv_path
        # In a real scenario, this would load the deck IDs from the CSV
        self.deck_card_ids = [1] * 60  # Placeholder: 60 basic energies

    def get_deck_card_ids(self) -> list[int]:
        """Returns the 60 card IDs comprising the deck."""
        return self.deck_card_ids

    def choose_action(self, obs: ParsedObservation) -> list[int]:
        """
        Main logic core. Evaluates the options and picks the best one.
        """
        if not obs.select or not obs.select.options:
            logger.warning("No legal options found. Returning empty action.")
            return []
            
        # VERY BASIC SKELETON LOGIC:
        # 1. Try to find an attack option
        for i, opt in enumerate(obs.select.options):
            if opt.option_type == "ATTACK":
                return [i]
                
        # 2. Otherwise just pick the first available option (e.g. PASS, DONE, or mandatory choice)
        # We assume returning [0] is the safe fallback if we don't know better yet
        return [0]
