"""
Native cg.api Engine module for Pokemon TCG AI Battle.
Provides ground-truth Enums, Dataclasses, to_observation_class(), and all_card_data().
"""

import os
import csv
import functools
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

# =============================================================================
# 1. ENUMS (Ground Truth from Kaggle ptcg_engine)
# =============================================================================

class OptionType(Enum):
    NUMBER = "0"
    YES = "1"
    NO = "2"
    CARD = "3"
    TOOL_CARD = "4"
    ENERGY_CARD = "5"
    ENERGY = "6"
    PLAY = "7"
    ATTACH = "8"
    EVOLVE = "9"
    ABILITY = "10"
    DISCARD = "11"
    RETREAT = "12"
    ATTACK = "13"
    END = "14"
    SKILL = "15"
    SPECIAL_CONDITION = "16"

class SelectType(Enum):
    MAIN = "0"
    CARD = "1"
    ATTACHED_CARD = "2"
    CARD_OR_ATTACHED_CARD = "3"
    ENERGY = "4"
    SKILL = "5"
    ATTACK = "6"
    EVOLVE = "7"
    COUNT = "8"
    YES_NO = "9"
    SPECIAL_CONDITION = "10"
    POKEMON = "11"
    SELECT = "12"
    ABILITY = "13"

class AreaType(Enum):
    DECK = "1"
    HAND = "2"
    DISCARD = "3"
    ACTIVE = "4"
    BENCH = "5"
    PRIZE = "6"
    STADIUM = "7"
    ENERGY = "8"
    TOOL = "9"
    PRE_EVOLUTION = "10"
    PLAYER = "11"
    LOOKING = "12"

class SelectContext(Enum):
    MAIN = "0"
    SETUP_ACTIVE_POKEMON = "1"
    SETUP_BENCH_POKEMON = "2"
    SWITCH = "3"
    TO_ACTIVE = "4"
    TO_BENCH = "5"
    TO_FIELD = "6"
    TO_HAND = "7"
    DISCARD = "8"
    TO_DECK = "9"
    TO_DECK_BOTTOM = "10"
    TO_PRIZE = "11"
    NOT_MOVE = "12"
    DAMAGE_COUNTER = "13"
    DAMAGE_COUNTER_ANY = "14"
    DAMAGE = "15"
    REMOVE_DAMAGE_COUNTER = "16"
    HEAL = "17"
    EVOLVES_FROM = "18"
    EVOLVES_TO = "19"
    DEVOLVE = "20"
    ATTACH_FROM = "21"
    ATTACH_TO = "22"
    DETACH_FROM = "23"
    LOOK = "24"
    EFFECT_TARGET = "25"
    DISCARD_ENERGY_CARD = "26"
    DISCARD_TOOL_CARD = "27"
    SWITCH_ENERGY_CARD = "28"
    DISCARD_CARD_OR_ATTACHED_CARD = "29"
    DISCARD_ENERGY = "30"
    TO_HAND_ENERGY = "31"
    TO_DECK_ENERGY = "32"
    SWITCH_ENERGY = "33"
    SKILL_ORDER = "34"
    ATTACK = "35"
    DISABLE_ATTACK = "36"
    EVOLVE = "37"
    DRAW_COUNT = "38"
    DAMAGE_COUNTER_COUNT = "39"
    REMOVE_DAMAGE_COUNTER_COUNT = "40"
    IS_FIRST = "41"
    MULLIGAN = "42"
    ACTIVATE = "43"
    FIRST_EFFECT = "44"
    MORE_DEVOLVE = "45"
    COIN_HEAD = "46"
    AFFECT_SPECIAL_CONDITION = "47"
    RECOVER_SPECIAL_CONDITION = "48"

class CardType(Enum):
    POKEMON = "POKEMON"
    TRAINER = "TRAINER"
    ENERGY = "ENERGY"

class EnergyType(Enum):
    GRASS = "GRASS"
    FIRE = "FIRE"
    WATER = "WATER"
    LIGHTNING = "LIGHTNING"
    PSYCHIC = "PSYCHIC"
    FIGHTING = "FIGHTING"
    DARKNESS = "DARKNESS"
    METAL = "METAL"
    DRAGON = "DRAGON"
    COLORLESS = "COLORLESS"


def _to_enum(val: Any, enum_cls: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, enum_cls):
        return val
    if hasattr(val, "name") and hasattr(enum_cls, val.name):
        return getattr(enum_cls, val.name)
    s = str(val)
    for member in enum_cls:
        if member.name == s or str(member.value) == s:
            return member
    return val

# =============================================================================
# 2. DATACLASSES
# =============================================================================

@dataclass
class Attack:
    name: str = ""
    cost: str = ""
    damage: int = 0
    effect: str = ""
    energy_count: int = 0

@dataclass
class Card:
    card_id: int = 0
    name: str = ""
    stage: str = ""
    hp: int = 0
    element_type: str = ""
    types: List[str] = field(default_factory=list)
    weakness: str = ""
    resistance: str = ""
    retreat_cost: int = 0
    previous_stage: str = ""
    attacks: List[Attack] = field(default_factory=list)
    card_type: str = ""

    @property
    def id(self) -> int:
        return self.card_id

@dataclass
class Pokemon:
    id: int = 0
    serial: int = 0
    hp: int = 0
    max_hp: int = 0
    appear_this_turn: bool = False
    energies: List[int] = field(default_factory=list)
    energy_cards: List[int] = field(default_factory=list)
    tools: List[int] = field(default_factory=list)
    pre_evolution: List[int] = field(default_factory=list)

    @property
    def card_id(self) -> int:
        return self.id

    @property
    def maxHp(self) -> int:
        return self.max_hp

    @property
    def appearThisTurn(self) -> bool:
        return self.appear_this_turn

@dataclass
class PlayerState:
    active: List[Pokemon] = field(default_factory=list)
    bench: List[Pokemon] = field(default_factory=list)
    bench_max: int = 5
    deck_count: int = 0
    discard: List[int] = field(default_factory=list)
    prize_count: int = 0
    hand_count: int = 0
    hand: List[int] = field(default_factory=list)
    poisoned: bool = False
    burned: bool = False
    asleep: bool = False
    paralyzed: bool = False
    confused: bool = False

@dataclass
class Option:
    index: int = 0
    option_type: Optional[Union[OptionType, str]] = None
    area: Optional[Union[AreaType, str]] = None
    in_play_area: Optional[Union[AreaType, str]] = None
    number: Optional[int] = None
    player_index: Optional[int] = None
    tool_index: Optional[int] = None
    energy_index: Optional[int] = None
    count: Optional[int] = None
    in_play_index: Optional[int] = None
    attack_id: Optional[int] = None
    card_id: Optional[int] = None
    serial: Optional[int] = None

    @property
    def type(self) -> Optional[Union[OptionType, str]]:
        return self.option_type

@dataclass
class Select:
    select_type: Optional[Union[SelectType, str]] = None
    context: Optional[Union[SelectContext, str]] = None
    min_count: int = 0
    max_count: int = 0
    options: List[Option] = field(default_factory=list)

    @property
    def type(self) -> Optional[Union[SelectType, str]]:
        return self.select_type

    @property
    def minCount(self) -> int:
        return self.min_count

    @property
    def maxCount(self) -> int:
        return self.max_count

@dataclass
class Observation:
    is_setup_phase: bool = False
    your_index: int = 0
    turn: int = 0
    my_state: PlayerState = field(default_factory=PlayerState)
    opp_state: PlayerState = field(default_factory=PlayerState)
    select: Optional[Select] = None

    @property
    def yourIndex(self) -> int:
        return self.your_index

    @property
    def my_active(self) -> List[Pokemon]:
        return self.my_state.active

    @property
    def my_bench(self) -> List[Pokemon]:
        return self.my_state.bench

    @property
    def my_hand(self) -> List[int]:
        return self.my_state.hand

    @property
    def my_prize_count(self) -> int:
        return self.my_state.prize_count

    @property
    def opp_active(self) -> List[Pokemon]:
        return self.opp_state.active

    @property
    def opp_bench(self) -> List[Pokemon]:
        return self.opp_state.bench

    @property
    def opp_prize_count(self) -> int:
        return self.opp_state.prize_count

# =============================================================================
# 3. ENGINE FUNCTIONS
# =============================================================================

@functools.lru_cache(maxsize=1)
def all_card_data() -> Dict[int, Card]:
    """Build and return card database from EN_Card_Data.csv."""
    cards: Dict[int, Card] = {}
    base_dir = os.path.dirname(os.path.abspath(__file__))
    search_paths = [
        "data/EN_Card_Data.csv",
        os.path.join(base_dir, "..", "data", "EN_Card_Data.csv"),
        os.path.join(base_dir, "EN_Card_Data.csv"),
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
    resolved = next((p for p in search_paths if p and os.path.exists(p)), None)
    if not resolved:
        return cards

    try:
        with open(resolved, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                try:
                    cid_str = row.get("Card ID", "").strip()
                    if not cid_str or not cid_str.isdigit():
                        continue
                    cid = int(cid_str)
                    stage = row.get("Stage (Pokémon)/Type (Energy and Trainer)", "Unknown").strip()
                    prev_stage = row.get("Previous stage", "n/a").strip()
                    name = row.get("Card Name", "?").strip()
                    hp_s = row.get("HP", "0").strip()
                    hp = int(hp_s) if hp_s.isdigit() else 0
                    ret_s = row.get("Retreat", "0").strip()
                    ret = int(ret_s) if ret_s.isdigit() else 0
                    element_type = row.get("Type", "").strip()
                    weakness = row.get("Weakness", "").strip()
                    resistance = row.get("Resistance (Type)", "").strip()

                    if cid not in cards:
                        c_type = "POKEMON" if hp > 0 or "Basic Pokémon" in stage or "Stage" in stage else ("ENERGY" if "Energy" in stage else "TRAINER")
                        cards[cid] = Card(
                            card_id=cid,
                            name=name,
                            stage=stage,
                            hp=hp,
                            element_type=element_type,
                            types=[element_type] if element_type else [],
                            weakness=weakness,
                            resistance=resistance,
                            retreat_cost=ret,
                            previous_stage=prev_stage,
                            attacks=[],
                            card_type=c_type,
                        )

                    mv = row.get("Move Name", "").strip()
                    if mv and mv != "n/a" and not mv.startswith("[Ability]"):
                        ds = "".join(c for c in row.get("Damage", "0") if c.isdigit())
                        cost_str = row.get("Cost", "").strip()
                        energy_count = cost_str.count("{")
                        cards[cid].attacks.append(
                            Attack(
                                name=mv,
                                cost=cost_str,
                                damage=int(ds) if ds else 0,
                                effect=row.get("Effect Explanation", "").strip(),
                                energy_count=energy_count,
                            )
                        )
                except ValueError:
                    continue
    except Exception:
        pass
    return cards


def _parse_pokemon(raw: Any) -> Pokemon:
    if not raw:
        return Pokemon()
    p = Pokemon()
    if isinstance(raw, dict):
        p.id = int(raw.get("id", 0) or 0)
        p.serial = int(raw.get("serial", 0) or 0)
        p.hp = int(raw.get("hp", 0) or 0)
        p.max_hp = int(raw.get("maxHp", raw.get("max_hp", 0)) or 0)
        p.appear_this_turn = bool(raw.get("appearThisTurn", raw.get("appear_this_turn", False)))
        energies = raw.get("energies", [])
        if isinstance(energies, (list, tuple)):
            p.energies = [int(e) for e in energies if e is not None]
        energy_cards = raw.get("energyCards", raw.get("energy_cards", []))
        if isinstance(energy_cards, (list, tuple)):
            p.energy_cards = [int(c.get("id", 0) if isinstance(c, dict) else c) for c in energy_cards if c]
        tools = raw.get("tools", [])
        if isinstance(tools, (list, tuple)):
            p.tools = [int(c.get("id", 0) if isinstance(c, dict) else c) for c in tools if c]
        pre_ev = raw.get("preEvolution", raw.get("pre_evolution", []))
        if isinstance(pre_ev, (list, tuple)):
            p.pre_evolution = [int(c.get("id", 0) if isinstance(c, dict) else c) for c in pre_ev if c]
    elif hasattr(raw, "id"):
        p.id = getattr(raw, "id", 0)
        p.serial = getattr(raw, "serial", 0)
        p.hp = getattr(raw, "hp", 0)
        p.max_hp = getattr(raw, "max_hp", getattr(raw, "maxHp", 0))
    return p


def _parse_player_state(raw: Any) -> PlayerState:
    if not raw or not isinstance(raw, dict):
        return PlayerState()
    s = PlayerState()
    s.active = [_parse_pokemon(x) for x in raw.get("active", []) or [] if x]
    s.bench = [_parse_pokemon(x) for x in raw.get("bench", []) or [] if x]
    s.bench_max = int(raw.get("benchMax", raw.get("bench_max", 5)) or 5)
    s.deck_count = int(raw.get("deckCount", raw.get("deck_count", 0)) or 0)
    discard = raw.get("discard", []) or []
    s.discard = [int(c.get("id", 0) if isinstance(c, dict) else c) for c in discard if c]
    s.hand_count = int(raw.get("handCount", raw.get("hand_count", 0)) or 0)
    hand = raw.get("hand", []) or []
    s.hand = [int(c.get("id", 0) if isinstance(c, dict) else c) for c in hand if c]
    prize = raw.get("prize", []) or []
    s.prize = prize if isinstance(prize, list) else []
    s.prize_count = len(s.prize) if s.prize else int(raw.get("prizeCount", raw.get("prize_count", 0)) or 0)
    s.poisoned = bool(raw.get("poisoned", False))
    s.burned = bool(raw.get("burned", False))
    s.asleep = bool(raw.get("asleep", False))
    s.paralyzed = bool(raw.get("paralyzed", False))
    s.confused = bool(raw.get("confused", False))
    return s


def _parse_option(raw: Any, idx: int) -> Option:
    o = Option(index=idx)
    if not raw or not isinstance(raw, dict):
        return o
    o.option_type = _to_enum(raw.get("type"), OptionType)
    o.area = _to_enum(raw.get("area"), AreaType)
    o.in_play_area = _to_enum(raw.get("inPlayArea"), AreaType)
    for field_name in ["number", "player_index", "tool_index", "energy_index", "count", "in_play_index", "attack_id", "card_id", "serial"]:
        camel = field_name if "_" not in field_name else field_name.split("_")[0] + "".join(p.capitalize() for p in field_name.split("_")[1:])
        v = raw.get(camel, raw.get(field_name))
        if v is not None:
            try:
                setattr(o, field_name, int(v))
            except Exception:
                pass
    if o.in_play_index is None and raw.get("index") is not None:
        try:
            o.in_play_index = int(raw["index"])
        except Exception:
            pass
    return o


def to_observation_class(obs_dict: Any) -> Observation:
    """Convert raw observation dictionary into a typed Observation instance."""
    if isinstance(obs_dict, Observation):
        return obs_dict
    obs = Observation()
    if not obs_dict or not isinstance(obs_dict, dict):
        obs.is_setup_phase = True
        return obs

    rc = obs_dict.get("current")
    if isinstance(rc, dict):
        obs.your_index = int(rc.get("yourIndex", rc.get("your_index", 0)) or 0)
        obs.turn = int(rc.get("turn", 0) or 0)
        players = rc.get("players", [])
        if isinstance(players, (list, tuple)) and len(players) > 0:
            my_idx = obs.your_index if len(players) > obs.your_index else 0
            opp_idx = 1 - my_idx if len(players) > 1 - my_idx else 1
            obs.my_state = _parse_player_state(players[my_idx] if len(players) > my_idx else None)
            obs.opp_state = _parse_player_state(players[opp_idx] if len(players) > opp_idx else None)

    rs = obs_dict.get("select")
    if isinstance(rs, dict) and rs:
        obs.select = Select()
        obs.select.select_type = _to_enum(rs.get("type"), SelectType)
        obs.select.context = _to_enum(rs.get("context"), SelectContext)
        obs.select.min_count = int(rs.get("minCount", rs.get("min_count", 0)) or 0)
        obs.select.max_count = int(rs.get("maxCount", rs.get("max_count", 0)) or 0)
        raw_opts = rs.get("option", rs.get("options", []))
        if isinstance(raw_opts, (list, tuple)):
            obs.select.options = [_parse_option(o, i) for i, o in enumerate(raw_opts)]
    else:
        obs.select = None
        obs.is_setup_phase = True

    return obs
