import csv
import logging
from dataclasses import dataclass
from typing import Dict, Optional, List
import os

logger = logging.getLogger(__name__)

@dataclass
class AttackData:
    name: str
    cost: str
    damage: int
    effect: str

@dataclass
class CardData:
    card_id: int
    name: str
    category: str  # e.g. "Basic Pokémon", "Stage 1 Pokémon", "Basic Energy", "Item", "Supporter"
    hp: int
    element_type: str
    retreat_cost: int
    attacks: List[AttackData]

class CardDatabase:
    """
    Singleton access to static card data loaded directly from EN_Card_Data.csv.
    Provides fast O(1) lookups for the heuristics and state encoder.
    """
    _instance = None
    _card_data_cache: Dict[int, CardData] = {}

    @classmethod
    def initialize(cls, csv_path: str = "data/EN_Card_Data.csv"):
        if cls._instance is not None:
            return
            
        cls._instance = cls()
        
        search_paths = [
            csv_path,
            "data/EN_Card_Data.csv",
            "/kaggle/input/pokemon-tcg-ai-battle/EN_Card_Data.csv",
            "/kaggle/input/competitions/pokemon-tcg-ai-battle/EN_Card_Data.csv",
            "/kaggle/input/pokemon-tcg-ai-battle/ptcg_engine/EN_Card_Data.csv",
            "/kaggle/input/competitions/pokemon-tcg-ai-battle/ptcg_engine/EN_Card_Data.csv",
            "/kaggle/input/pokemon-tcg-ai-battle-challenge-strategy/EN_Card_Data.csv",
            "/kaggle/input/competitions/pokemon-tcg-ai-battle-challenge-strategy/EN_Card_Data.csv",
            "/kaggle/input/pokemon-tcg-ai-battle-challenge-strategy/ptcg_engine/EN_Card_Data.csv",
            "/kaggle/input/competitions/pokemon-tcg-ai-battle-challenge-strategy/ptcg_engine/EN_Card_Data.csv",
            os.environ.get("CARD_DATA_PATH", ""),
        ]
        
        # Also try relative to this script
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            search_paths.append(os.path.join(script_dir, "..", "data", "EN_Card_Data.csv"))
        except NameError:
            pass

        resolved_path = None
        for p in search_paths:
            if p and os.path.exists(p):
                resolved_path = p
                break

        if resolved_path is None:
            logger.warning("EN_Card_Data.csv not found. Card database will be empty.")
            return

        try:
            with open(resolved_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        c_id_str = row.get("Card ID", "").strip()
                        if not c_id_str:
                            continue
                        card_id = int(c_id_str)
                        
                        # Fuzzy column detection for the Stage/Type column
                        stage = ""
                        for k in row.keys():
                            if k and "Stage" in k and "Type" in k:
                                stage = row[k]
                                break
                        if not stage:
                            stage = row.get("Stage (Pokémon)/Type (Energy and Trainer)", "Unknown")
                            
                        # Only add if we haven't seen it
                        if card_id not in cls._card_data_cache:
                            hp_str = row.get("HP", "0").strip()
                            hp = int(hp_str) if hp_str and hp_str.isdigit() else 0
                            
                            retreat_str = row.get("Retreat", "0").strip()
                            retreat = int(retreat_str) if retreat_str and retreat_str.isdigit() else 0
                            
                            cls._card_data_cache[card_id] = CardData(
                                card_id=card_id,
                                name=row.get("Card Name", "Unknown"),
                                category=stage,
                                hp=hp,
                                element_type=row.get("Type", ""),
                                retreat_cost=retreat,
                                attacks=[]
                            )
                        
                        # Add attacks
                        move_name = row.get("Move Name", "").strip()
                        if move_name and move_name != "n/a" and not move_name.startswith("[Ability]"):
                            dmg_raw = row.get("Damage", "0").strip()
                            dmg_clean = ""
                            for ch in dmg_raw:
                                if ch.isdigit(): dmg_clean += ch
                            dmg = int(dmg_clean) if dmg_clean else 0
                            
                            cls._card_data_cache[card_id].attacks.append(AttackData(
                                name=move_name,
                                cost=row.get("Cost", ""),
                                damage=dmg,
                                effect=row.get("Effect Explanation", "")
                            ))
                            
                    except ValueError:
                        pass
                        
            logger.info(f"Loaded {len(cls._card_data_cache)} unique cards from {resolved_path}")
        except Exception as e:
            logger.error(f"Failed to load card data: {e}")

    @classmethod
    def get_card(cls, card_id: int) -> Optional[CardData]:
        """
        Retrieves the static card metadata for a given card ID.
        """
        if cls._instance is None:
            cls.initialize()
            
        return cls._card_data_cache.get(card_id)
