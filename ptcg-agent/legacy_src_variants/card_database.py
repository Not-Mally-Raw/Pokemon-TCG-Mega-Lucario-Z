"""
Provides a static database interface for looking up CardData from integer card IDs.
Since the Kaggle agent must be self-contained and we don't have the real ptcg_engine
installed locally yet, this wraps the expected API.
"""

import logging

logger = logging.getLogger(__name__)

# In the real kaggle environment, the ptcg_engine provides api.all_card_data()
# We use a try/except so we can test the parser without the engine installed.
try:
    from ptcg_engine import api
    _REAL_ENGINE_AVAILABLE = True
except ImportError:
    _REAL_ENGINE_AVAILABLE = False
    logger.warning("ptcg_engine not found. Using mocked CardDatabase.")


class CardDatabase:
    """
    Singleton-like access to static card data.
    """
    _instance = None
    _card_data_cache = {}

    @classmethod
    def initialize(cls):
        """Loads the static card data from the engine."""
        if cls._instance is not None:
            return
            
        cls._instance = cls()
        
        if _REAL_ENGINE_AVAILABLE:
            try:
                # Assuming api.all_card_data() returns a dict mapping ID -> CardData object
                cls._card_data_cache = api.all_card_data()
            except Exception as e:
                logger.error(f"Failed to load card data from ptcg_engine: {e}")
        else:
            # Fallback mock for local testing without the dataset
            cls._card_data_cache = {}

    @classmethod
    def get_card(cls, card_id: int) -> dict:
        """
        Retrieves the static card metadata for a given card ID.
        Returns an empty dict if the card isn't found or engine isn't available.
        """
        if cls._instance is None:
            cls.initialize()
            
        # In a fully fleshed out version, this would return a structured dataclass
        # For now, it returns whatever the raw engine gives us (or empty dict)
        return cls._card_data_cache.get(card_id, {"id": card_id, "name": f"UnknownCard_{card_id}"})
