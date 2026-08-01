"""
PTCG AI Agent — Observation Parser (Verified Ground Truth)
==========================================================
Rebuilt exactly to match the cg.api schema output from the live engine.
"""

from dataclasses import dataclass, field
from typing import Any, List, Optional
from enum import Enum

# =============================================================================
# GROUND TRUTH ENUMS (Derived directly from Kaggle introspect)
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

# =============================================================================
# SAFE EXTRACTION UTILS
# =============================================================================

def _safe_get(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None: return default
    if isinstance(obj, dict): return obj.get(key, default)
    return getattr(obj, key, default)

def _safe_int(val: Any, default: int = 0) -> int:
    if val is None: return default
    try: return int(val)
    except (ValueError, TypeError): return default

def _safe_bool(val: Any, default: bool = False) -> bool:
    if val is None: return default
    try: return bool(val)
    except (ValueError, TypeError): return default

def _enum_name(val: Any, enum_class: type) -> Optional[str]:
    """
    Extracts the enum member NAME robustly (e.g. 'MAIN', 'END').
    The raw value from Kaggle might be an Enum object, or its string value (e.g. '14').
    """
    if val is None: return None
    if hasattr(val, 'name'): return val.name
    str_val = str(val)
    for name, member in enum_class.__members__.items():
        if str(member.value) == str_val or name == str_val:
            return name
    return str_val

# =============================================================================
# PARSED DATA STRUCTURES
# =============================================================================

@dataclass
class ParsedOption:
    list_position: int = 0
    option_type: Optional[str] = None
    number: Optional[int] = None
    area: Optional[str] = None
    index: Optional[int] = None
    player_index: Optional[int] = None
    tool_index: Optional[int] = None
    energy_index: Optional[int] = None
    count: Optional[int] = None
    in_play_area: Optional[str] = None
    in_play_index: Optional[int] = None
    attack_id: Optional[int] = None
    card_id: Optional[int] = None
    serial: Optional[int] = None
    special_condition_type: Optional[str] = None

@dataclass
class ParsedSelectData:
    select_type: Optional[str] = None
    context: Optional[str] = None
    min_count: int = 0
    max_count: int = 0
    remain_damage_counter: int = 0
    remain_energy_cost: int = 0
    options: List[ParsedOption] = field(default_factory=list)
    # deck, contextCard, effect omitted for now unless needed

@dataclass
class ParsedPokemon:
    id: int = 0
    serial: int = 0
    hp: int = 0
    max_hp: int = 0
    appear_this_turn: bool = False
    energies: List[int] = field(default_factory=list)
    energy_cards: List[int] = field(default_factory=list)
    tools: List[int] = field(default_factory=list)
    pre_evolution: List[int] = field(default_factory=list)

PokemonState = ParsedPokemon

@dataclass
class ParsedPlayerState:
    active: List[ParsedPokemon] = field(default_factory=list)
    bench: List[ParsedPokemon] = field(default_factory=list)
    bench_max: int = 0
    deck_count: int = 0
    discard: List[int] = field(default_factory=list) # List of Card IDs
    prize_count: int = 0 # Derived from len(prize)
    hand_count: int = 0
    hand: List[int] = field(default_factory=list) # List of Card IDs (visible)
    poisoned: bool = False
    burned: bool = False
    asleep: bool = False
    paralyzed: bool = False
    confused: bool = False

@dataclass
class ParsedObservation:
    is_setup_phase: bool = False
    your_index: int = 0
    turn: int = 0
    my_state: ParsedPlayerState = field(default_factory=ParsedPlayerState)
    opp_state: ParsedPlayerState = field(default_factory=ParsedPlayerState)
    select: Optional[ParsedSelectData] = None
    search_begin_input: Optional[str] = None

# =============================================================================
# PARSER LOGIC
# =============================================================================

def _parse_pokemon(raw: Any) -> ParsedPokemon:
    if raw is None: return ParsedPokemon()
    p = ParsedPokemon()
    p.id = _safe_int(_safe_get(raw, 'id'))
    p.serial = _safe_int(_safe_get(raw, 'serial'))
    p.hp = _safe_int(_safe_get(raw, 'hp'))
    p.max_hp = _safe_int(_safe_get(raw, 'maxHp', _safe_get(raw, 'max_hp')))
    p.appear_this_turn = _safe_bool(_safe_get(raw, 'appearThisTurn', _safe_get(raw, 'appear_this_turn')))
    # Omitting lists extraction for brevity unless strictly needed by heuristics
    return p

def _parse_pokemon_list(raw_list: Any) -> List[ParsedPokemon]:
    if not isinstance(raw_list, (list, tuple)): return []
    return [_parse_pokemon(x) for x in raw_list if x is not None]

def _parse_card_id_list(raw_list: Any) -> List[int]:
    if not isinstance(raw_list, (list, tuple)): return []
    return [_safe_int(_safe_get(c, 'id')) for c in raw_list if c is not None]

def _parse_player_state(raw_player: Any) -> ParsedPlayerState:
    if raw_player is None: return ParsedPlayerState()
    s = ParsedPlayerState()
    s.active = _parse_pokemon_list(_safe_get(raw_player, 'active'))
    s.bench = _parse_pokemon_list(_safe_get(raw_player, 'bench'))
    s.bench_max = _safe_int(_safe_get(raw_player, 'benchMax'))
    s.deck_count = _safe_int(_safe_get(raw_player, 'deckCount'))
    s.discard = _parse_card_id_list(_safe_get(raw_player, 'discard'))
    s.hand_count = _safe_int(_safe_get(raw_player, 'handCount'))
    s.hand = _parse_card_id_list(_safe_get(raw_player, 'hand'))
    
    # Ground truth says prize is list[cg.api.Card | None]. We just need the count.
    raw_prize = _safe_get(raw_player, 'prize')
    if isinstance(raw_prize, (list, tuple)):
        s.prize_count = len([x for x in raw_prize if x is not None])
        
    s.poisoned = _safe_bool(_safe_get(raw_player, 'poisoned'))
    s.burned = _safe_bool(_safe_get(raw_player, 'burned'))
    s.asleep = _safe_bool(_safe_get(raw_player, 'asleep'))
    s.paralyzed = _safe_bool(_safe_get(raw_player, 'paralyzed'))
    s.confused = _safe_bool(_safe_get(raw_player, 'confused'))
    return s

def _parse_option(raw_opt: Any, idx: int) -> ParsedOption:
    if raw_opt is None: return ParsedOption(list_position=idx)
    opt = ParsedOption(list_position=idx)
    opt.option_type = _enum_name(_safe_get(raw_opt, 'type'), OptionType)
    opt.area = _enum_name(_safe_get(raw_opt, 'area'), AreaType)
    opt.in_play_area = _enum_name(_safe_get(raw_opt, 'inPlayArea'), AreaType)
    
    opt.number = _safe_get(raw_opt, 'number')
    opt.index = _safe_get(raw_opt, 'index')
    opt.player_index = _safe_get(raw_opt, 'playerIndex')
    opt.tool_index = _safe_get(raw_opt, 'toolIndex')
    opt.energy_index = _safe_get(raw_opt, 'energyIndex')
    opt.count = _safe_get(raw_opt, 'count')
    opt.in_play_index = _safe_get(raw_opt, 'inPlayIndex')
    opt.attack_id = _safe_get(raw_opt, 'attackId')
    opt.card_id = _safe_get(raw_opt, 'cardId')
    opt.serial = _safe_get(raw_opt, 'serial')
    
    # Cast ints
    for f in ['number', 'index', 'player_index', 'tool_index', 'energy_index', 'count', 'in_play_index', 'attack_id', 'card_id', 'serial']:
        v = getattr(opt, f)
        if v is not None: setattr(opt, f, _safe_int(v))
        
    return opt

def _parse_select_data(raw_select: Any) -> Optional[ParsedSelectData]:
    if raw_select is None: return None
    s = ParsedSelectData()
    s.select_type = _enum_name(_safe_get(raw_select, 'type'), SelectType)
    s.context = _enum_name(_safe_get(raw_select, 'context'), SelectContext)
    s.min_count = _safe_int(_safe_get(raw_select, 'minCount'))
    s.max_count = _safe_int(_safe_get(raw_select, 'maxCount'))
    s.remain_damage_counter = _safe_int(_safe_get(raw_select, 'remainDamageCounter'))
    s.remain_energy_cost = _safe_int(_safe_get(raw_select, 'remainEnergyCost'))
    
    raw_ops = _safe_get(raw_select, 'option')
    if isinstance(raw_ops, (list, tuple)):
        s.options = [_parse_option(o, i) for i, o in enumerate(raw_ops)]
    return s

def parse_observation(raw_obs: Any) -> ParsedObservation:
    obs = ParsedObservation()
    
    raw_current = _safe_get(raw_obs, 'current')
    if raw_current is not None:
        obs.your_index = _safe_int(_safe_get(raw_current, 'yourIndex'))
        obs.turn = _safe_int(_safe_get(raw_current, 'turn'))
        
        raw_players = _safe_get(raw_current, 'players')
        if isinstance(raw_players, (list, tuple)) and len(raw_players) > 0:
            obs.my_state = _parse_player_state(raw_players[obs.your_index] if len(raw_players) > obs.your_index else None)
            opp_idx = 1 - obs.your_index
            obs.opp_state = _parse_player_state(raw_players[opp_idx] if len(raw_players) > opp_idx else None)
    
    obs.select = _parse_select_data(_safe_get(raw_obs, 'select'))
    obs.search_begin_input = _safe_get(raw_obs, 'search_begin_input')
    
    if obs.select is None:
        obs.is_setup_phase = True
        
    return obs
